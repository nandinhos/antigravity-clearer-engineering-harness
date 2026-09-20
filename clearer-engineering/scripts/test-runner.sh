#!/usr/bin/env bash
# ==============================================================================
# test-runner.sh - Evidence-Capturing Test Runner for CLEARER Harness
# ==============================================================================
set -u

echo "=== [CEH Deterministic Test Runner] ==="
echo "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "Working Directory: $(pwd)"
echo ""

TEST_CMD=""

if [[ $# -gt 0 ]]; then
    TEST_CMD="$*"
else
    # Auto-detect test runner based on files
    if [[ -f "composer.json" ]]; then
        if [[ -f "vendor/bin/pest" ]] || grep -q '"pestphp/pest"' composer.json 2>/dev/null; then
            TEST_CMD="./vendor/bin/pest"
        elif [[ -f "vendor/bin/phpunit" ]] || [[ -f "phpunit.xml" ]]; then
            TEST_CMD="./vendor/bin/phpunit"
        elif [[ -f "artisan" ]]; then
            TEST_CMD="php artisan test"
        fi
    elif [[ -f "package.json" ]]; then
        if grep -q '"test"' package.json 2>/dev/null; then
            if [[ -f "pnpm-lock.yaml" ]]; then
                TEST_CMD="pnpm test"
            elif [[ -f "yarn.lock" ]]; then
                TEST_CMD="yarn test"
            elif [[ -f "bun.lockb" ]] || [[ -f "bun.lock" ]]; then
                TEST_CMD="bun test"
            else
                TEST_CMD="npm test"
            fi
        fi
    elif [[ -f "pytest.ini" ]] || [[ -f "conftest.py" ]] || [[ -d "tests" && ( -f "pyproject.toml" || -f "requirements.txt" ) ]]; then
        if command -v pytest >/dev/null 2>&1; then
            TEST_CMD="pytest"
        else
            TEST_CMD="python3 -m unittest"
        fi
    elif [[ -f "go.mod" ]]; then
        TEST_CMD="go test ./..."
    elif [[ -f "Cargo.toml" ]]; then
        TEST_CMD="cargo test"
    fi
fi

if [[ -z "$TEST_CMD" ]]; then
    echo "STATUS: NOT RUN"
    echo "REASON: No test suite or command detected in this workspace."
    echo "EXIT CODE: 1"
    exit 1
fi

# Runtime Adapter: Detect if test command needs container dispatch
DOCKER_RUNNING=0
ACTIVE_COMPOSE_SERVICES=()

if command -v docker >/dev/null 2>&1; then
    if docker info >/dev/null 2>&1; then
        DOCKER_RUNNING=1
        if [[ -f "docker-compose.yml" || -f "docker-compose.yaml" || -f "compose.yaml" || -f "compose.yml" ]]; then
            ACTIVE_COMPOSE=$(docker compose ps --services --filter "status=running" 2>/dev/null || true)
            if [[ -n "$ACTIVE_COMPOSE" ]]; then
                while IFS= read -r s; do
                    [[ -n "$s" ]] && ACTIVE_COMPOSE_SERVICES+=("$s")
                done <<< "$ACTIVE_COMPOSE"
            fi
        fi
    fi
fi

# If containers are actively running and the command is a bare host command, adapt it
if [[ ${#ACTIVE_COMPOSE_SERVICES[@]} -gt 0 ]]; then
    if [[ ! "$TEST_CMD" =~ (docker|docker-compose|sail) ]]; then
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
    fi
elif [[ -f "docker-compose.yml" || -f "docker-compose.yaml" || -f "compose.yaml" || -f "compose.yml" ]]; then
    if [[ ! "$TEST_CMD" =~ (docker|docker-compose|sail) ]]; then
        echo "[CEH RUNTIME ADAPTER] ℹ️ Projeto possui Docker configurado, mas os containers estão desligados."
        echo "[CEH RUNTIME ADAPTER] Executando diretamente no Host Nativo..."
    fi
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
CEH_DIR=".ceh"
mkdir -p "$CEH_DIR" 2>/dev/null || true
if [[ -d "$CEH_DIR" ]]; then
    CURRENT_COMMIT=$(git rev-parse HEAD 2>/dev/null || echo "untracked")
    NOW_ISO=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    STATUS_STR="FAIL"
    [[ $EXIT_CODE -eq 0 ]] && STATUS_STR="PASS"

    cat << EOF > "$CEH_DIR/last-ci-run.json"
{
  "commit_hash": "$CURRENT_COMMIT",
  "timestamp": "$NOW_ISO",
  "command": "$TEST_CMD",
  "status": "$STATUS_STR",
  "exit_code": $EXIT_CODE
}
EOF
fi

rm -f "$OUTPUT_FILE"
exit $EXIT_CODE
