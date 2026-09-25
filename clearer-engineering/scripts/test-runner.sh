#!/usr/bin/env bash
# ==============================================================================
# test-runner.sh - Evidence-Capturing Test Runner for CLEARER Harness
# ==============================================================================
set -u

echo "=== [CEH Deterministic Test Runner] ==="
echo "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "Working Directory: $(pwd)"
echo ""

# Auto-detect the canonical test runner based on files
DETECTED_CMD=""
if [[ -f "composer.json" ]]; then
    if [[ -f "vendor/bin/pest" ]] || grep -q '"pestphp/pest"' composer.json 2>/dev/null; then
        DETECTED_CMD="./vendor/bin/pest"
    elif [[ -f "vendor/bin/phpunit" ]] || [[ -f "phpunit.xml" ]]; then
        DETECTED_CMD="./vendor/bin/phpunit"
    elif [[ -f "artisan" ]]; then
        DETECTED_CMD="php artisan test"
    fi
elif [[ -f "package.json" ]]; then
    if grep -q '"test"' package.json 2>/dev/null; then
        if [[ -f "pnpm-lock.yaml" ]]; then
            DETECTED_CMD="pnpm test"
        elif [[ -f "yarn.lock" ]]; then
            DETECTED_CMD="yarn test"
        elif [[ -f "bun.lockb" ]] || [[ -f "bun.lock" ]]; then
            DETECTED_CMD="bun test"
        else
            DETECTED_CMD="npm test"
        fi
    fi
elif [[ -f "pytest.ini" ]] || [[ -f "conftest.py" ]] || [[ -d "tests" && ( -f "pyproject.toml" || -f "requirements.txt" ) ]]; then
    if command -v pytest >/dev/null 2>&1; then
        DETECTED_CMD="pytest"
    else
        DETECTED_CMD="python3 -m unittest"
    fi
elif [[ -f "go.mod" ]]; then
    DETECTED_CMD="go test ./..."
elif [[ -f "Cargo.toml" ]]; then
    DETECTED_CMD="cargo test"
fi

# Canonical command declared by the project overrides auto-detection
CONFIG_CMD=""
CONFIG_OK=1
REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    if [[ -f "$REPO_ROOT/.ceh/config.json" ]]; then
        if git cat-file -e "HEAD:.ceh/config.json" 2>/dev/null && git -C "$REPO_ROOT" diff --quiet HEAD -- .ceh/config.json 2>/dev/null; then
            CONFIG_CMD=$(git -C "$REPO_ROOT" show "HEAD:.ceh/config.json" 2>/dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin).get("canonical_test_command",""))' 2>/dev/null) || CONFIG_OK=0
        else
            CONFIG_OK=0
        fi
    elif git cat-file -e "HEAD:.ceh/config.json" 2>/dev/null; then
        CONFIG_OK=0
    fi
elif [[ -f "$REPO_ROOT/.ceh/config.json" ]]; then
    CONFIG_CMD=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("canonical_test_command",""))' "$REPO_ROOT/.ceh/config.json" 2>/dev/null) || CONFIG_OK=0
fi

if [[ $# -gt 0 ]]; then
    TEST_CMD="$*"
elif [[ -n "$CONFIG_CMD" ]]; then
    TEST_CMD="$CONFIG_CMD"
else
    TEST_CMD="$DETECTED_CMD"
fi

if [[ -z "$TEST_CMD" ]]; then
    echo "STATUS: NOT RUN"
    echo "REASON: No test suite or command detected in this workspace."
    echo "EXIT CODE: 1"
    exit 1
fi

RAW_TEST_CMD="$TEST_CMD"
CLEAN_RUNNER=$(echo "$TEST_CMD" | sed -E 's/^[[:space:]]*rtk([[:space:]]+proxy)?[[:space:]]+//')
CANONICAL_CMD="${CONFIG_CMD:-$DETECTED_CMD}"

# Only the canonical command grants a push certificate; comparison, not inspection
CANONICAL_VERIFIED=false
if [[ $CONFIG_OK -eq 0 ]]; then
    echo "[CEH WARNING] ⚠️ .ceh/config.json é inválido. Este comando NÃO concederá certificado válido para git push."
elif [[ -n "$CANONICAL_CMD" && "$CLEAN_RUNNER" == "$CANONICAL_CMD" ]]; then
    CANONICAL_VERIFIED=true
else
    echo "[CEH WARNING] ⚠️ O comando '$TEST_CMD' difere da suíte canônica ('${CANONICAL_CMD:-não detectada}')."
    echo "[CEH WARNING] Este comando NÃO concederá certificado válido de liberação para git push."
fi

# A certificate must describe the commit, so the worktree must match HEAD
WORKTREE_DIRTY=0
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    DIRTY_FILES=$(git -C "$REPO_ROOT" status --porcelain -- ':(top)' ':(top,exclude).ceh/last-ci-run.json' ':(top,exclude).ceh/last-ci-run.log' 2>/dev/null)
    if [[ -n "$DIRTY_FILES" ]]; then
        WORKTREE_DIRTY=1
        echo "[CEH WARNING] ⚠️ Worktree com alterações não commitadas. Os testes rodam, mas o certificado NÃO será emitido."
        echo "[CEH WARNING] Commite, descarte ou adicione ao .gitignore:"
        echo "$DIRTY_FILES" | head -n 5 | sed 's/^/    /'
    fi
fi

# Runtime Adapter: Detect if test command needs container dispatch
DOCKER_RUNNING=0
ACTIVE_COMPOSE_SERVICES=()
if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
    DOCKER_RUNNING=1
    if [[ -f "docker-compose.yml" || -f "docker-compose.yaml" || -f "compose.yaml" || -f "compose.yml" ]]; then
        ACTIVE_COMPOSE=$(docker compose ps --services --filter "status=running" 2>/dev/null || true)
        while IFS= read -r s; do
            [[ -n "$s" ]] && ACTIVE_COMPOSE_SERVICES+=("$s")
        done <<< "$ACTIVE_COMPOSE"
    fi
fi

# If containers are actively running and the command is a bare host command, adapt it
if [[ ${#ACTIVE_COMPOSE_SERVICES[@]} -gt 0 && ! "$TEST_CMD" =~ (docker|docker-compose|sail) ]]; then
    if [[ " ${ACTIVE_COMPOSE_SERVICES[*]} " =~ " laravel.test " ]]; then
        if [[ -f "vendor/bin/sail" ]]; then
            echo "[CEH RUNTIME ADAPTER] 🐳 Containers Laravel Sail ativos detectados. Despachando via Sail..."
            TEST_CMD="./vendor/bin/sail test"
        else
            echo "[CEH RUNTIME ADAPTER] 🐳 Containers Compose ativos detectados. Despachando via 'laravel.test'..."
            TEST_CMD="docker compose exec -T laravel.test $TEST_CMD"
        fi
    elif [[ " ${ACTIVE_COMPOSE_SERVICES[*]} " =~ " app " ]]; then
        echo "[CEH RUNTIME ADAPTER] 🐳 Container 'app' ativo detectado. Despachando via container..."
        TEST_CMD="docker compose exec -T app $TEST_CMD"
    fi
elif [[ -f "docker-compose.yml" || -f "docker-compose.yaml" || -f "compose.yaml" || -f "compose.yml" ]]; then
    [[ ! "$TEST_CMD" =~ (docker|docker-compose|sail) ]] && echo "[CEH RUNTIME ADAPTER] ℹ️ Containers desligados. Executando diretamente no Host Nativo..."
fi

# Token economy proxy: if rtk is available, wrap test command to cut output by up to 80%
if command -v rtk >/dev/null 2>&1; then
    if [[ ! "$TEST_CMD" =~ ^[[:space:]]*rtk[[:space:]] ]]; then
        TEST_CMD="rtk $TEST_CMD"
    fi
fi

echo "=========================================="
echo "COMMAND:   $TEST_CMD"
echo "=========================================="
echo ""

# Execute command and capture output and exit code
OUTPUT_FILE=$(mktemp)
START_TIME=$(date +%s%N 2>/dev/null || date +%s)

set +e
eval "$TEST_CMD" > "$OUTPUT_FILE" 2>&1
EXIT_CODE=$?
set -e

END_TIME=$(date +%s%N 2>/dev/null || date +%s)

cat "$OUTPUT_FILE"
echo ""
echo "=========================================="
echo "EXIT CODE: $EXIT_CODE"
if [[ $EXIT_CODE -eq 0 ]]; then
    echo "STATUS:    PASS"
else
    echo "STATUS:    FAIL"
fi
echo "=========================================="

# Emit Pre-Push CI Clearance Certificate
CEH_DIR="$REPO_ROOT/.ceh"
if [[ $WORKTREE_DIRTY -eq 0 ]]; then
    mkdir -p "$CEH_DIR" 2>/dev/null || true
    if [[ -d "$CEH_DIR" ]]; then
        CURRENT_COMMIT=$(git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null || echo "untracked")
        NOW_ISO=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
        STATUS_STR="FAIL"
        [[ $EXIT_CODE -eq 0 ]] && STATUS_STR="PASS"

        python3 -c '
import json, os, sys
p, c, t, cmd, raw, v, s, code = sys.argv[1:]
with open(p + ".tmp", "w", encoding="utf-8") as f:
    json.dump({"commit_hash": c, "timestamp": t, "command": cmd, "normalized_runner": raw, "canonical_verified": v == "true", "status": s, "exit_code": int(code)}, f, indent=2, ensure_ascii=False)
os.replace(p + ".tmp", p)
' "$CEH_DIR/last-ci-run.json" "$CURRENT_COMMIT" "$NOW_ISO" "$TEST_CMD" "$RAW_TEST_CMD" "$CANONICAL_VERIFIED" "$STATUS_STR" "$EXIT_CODE"
        cp "$OUTPUT_FILE" "$CEH_DIR/last-ci-run.log"  # saída bruta citada pelo evidence-report
    fi
fi

rm -f "$OUTPUT_FILE"
exit $EXIT_CODE
