#!/usr/bin/env bash
# ==============================================================================
# detect-project.sh - Stack and Tooling Detector for CLEARER Engineering Harness
# ==============================================================================
set -euo pipefail

TARGET_DIR="${1:-$(pwd)}"
cd "$TARGET_DIR"

echo "=== [CEH Stack & Environment Awareness Report] ==="
echo "Target Directory: $TARGET_DIR"
echo "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo ""

# 0. Environment Detection (DEV / HOMOLOGAÇÃO / PRODUÇÃO)
DETECTED_ENV="development"
ENV_EVIDENCE="Default fallback (local workspace)"

# 0.1 Check Shell / System Environment Variables
for var in CEH_ENV APP_ENV NODE_ENV ENVIRONMENT ENV STAGE; do
    if [[ -n "${!var:-}" ]]; then
        RAW_VAL="${!var}"
        VAL=$(echo "$RAW_VAL" | tr '[:upper:]' '[:lower:]')
        if [[ "$VAL" =~ (prod|production|prd|live) ]]; then
            DETECTED_ENV="production"
            ENV_EVIDENCE="Environment variable $var=$RAW_VAL"
            break
        elif [[ "$VAL" =~ (stage|staging|homolog|homologacao|uat|qa) ]]; then
            DETECTED_ENV="staging"
            ENV_EVIDENCE="Environment variable $var=$RAW_VAL"
            break
        elif [[ "$VAL" =~ (dev|development|local|test|testing) ]]; then
            DETECTED_ENV="development"
            ENV_EVIDENCE="Environment variable $var=$RAW_VAL"
            break
        fi
    fi
done

# 0.2 Check Configuration Files if not overridden by explicit var
if [[ "$DETECTED_ENV" == "development" && "$ENV_EVIDENCE" == *"Default fallback"* ]]; then
    if [[ -f ".env.production" ]]; then
        DETECTED_ENV="production"
        ENV_EVIDENCE="File .env.production present"
    elif [[ -f ".env.staging" ]] || [[ -f ".env.homolog" ]]; then
        DETECTED_ENV="staging"
        ENV_EVIDENCE="File .env.staging / .env.homolog present"
    elif [[ -f ".env" ]]; then
        for key in CEH_ENV APP_ENV NODE_ENV ENVIRONMENT ENV STAGE; do
            MATCH=$(grep -E "^${key}=" .env 2>/dev/null | head -n 1 | cut -d'=' -f2- | tr -d '"'"'" | tr -d ' ' || true)
            if [[ -n "$MATCH" ]]; then
                VAL=$(echo "$MATCH" | tr '[:upper:]' '[:lower:]')
                if [[ "$VAL" =~ (prod|production|prd|live) ]]; then
                    DETECTED_ENV="production"
                    ENV_EVIDENCE="File .env (${key}=${MATCH})"
                    break
                elif [[ "$VAL" =~ (stage|staging|homolog|homologacao|uat|qa) ]]; then
                    DETECTED_ENV="staging"
                    ENV_EVIDENCE="File .env (${key}=${MATCH})"
                    break
                elif [[ "$VAL" =~ (dev|development|local|test|testing) ]]; then
                    DETECTED_ENV="development"
                    ENV_EVIDENCE="File .env (${key}=${MATCH})"
                    break
                fi
            fi
        done
    fi
fi

# 0.3 Check Git Branch (preventive escalation & canonical flow)
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "detached")
    if [[ "$DETECTED_ENV" == "development" && "$ENV_EVIDENCE" == *"Default fallback"* ]]; then
        BRANCH_LOWER=$(echo "$CURRENT_BRANCH" | tr '[:upper:]' '[:lower:]')
        if [[ "$BRANCH_LOWER" =~ ^(main|master|production|prod)$ ]]; then
            DETECTED_ENV="production"
            ENV_EVIDENCE="Git branch '${CURRENT_BRANCH}' (canonical production branch)"
        elif [[ "$BRANCH_LOWER" =~ (staging|stage|homolog|homologacao|uat|qa) ]]; then
            DETECTED_ENV="staging"
            ENV_EVIDENCE="Git branch '${CURRENT_BRANCH}' (canonical staging branch)"
        elif [[ "$BRANCH_LOWER" =~ ^(dev|develop)$ ]]; then
            DETECTED_ENV="development"
            ENV_EVIDENCE="Git branch '${CURRENT_BRANCH}' (canonical dev branch)"
        elif [[ "$BRANCH_LOWER" =~ ^dev/ ]] || [[ "$BRANCH_LOWER" =~ ^dev- ]] || [[ "$BRANCH_LOWER" =~ ^(feature|fix)/ ]]; then
            DETECTED_ENV="development"
            ENV_EVIDENCE="Git branch '${CURRENT_BRANCH}' (derivation from dev)"
        fi
    fi
fi

ENV_UPPER=$(echo "$DETECTED_ENV" | tr '[:lower:]' '[:upper:]')
echo "--- Environment Awareness ---"
echo "Detected Environment: $ENV_UPPER"
echo "Evidence Source:      $ENV_EVIDENCE"
case "$DETECTED_ENV" in
    production)
        echo "Safety Gate Policy:   PRODUÇÃO STRICT (Comandos destrutivos são FORA DE COGITAÇÃO - DENY)"
        ;;
    staging)
        echo "Safety Gate Policy:   HOMOLOGAÇÃO GATED (Exige confirmação com 2 ALERTAS + Backup e Rollback)"
        ;;
    *)
        echo "Safety Gate Policy:   DESENVOLVIMENTO (Destrutivos permitidos com prontidão de backup/rollback)"
        ;;
esac
echo "-----------------------------"
echo ""

STACKS=()
FRAMEWORKS=()
TEST_RUNNERS=()
LINTERS=()
PACKAGE_MANAGERS=()
INFRA=()

# 1. PHP / Laravel / Symfony
if [[ -f "composer.json" ]]; then
    STACKS+=("PHP")
    PACKAGE_MANAGERS+=("composer")
    
    if grep -q '"laravel/framework"' composer.json 2>/dev/null || [[ -f "artisan" ]]; then
        FRAMEWORKS+=("Laravel")
    fi
    if grep -q '"symfony/' composer.json 2>/dev/null; then
        FRAMEWORKS+=("Symfony")
    fi
    if [[ -f "phpunit.xml" ]] || [[ -f "phpunit.xml.dist" ]]; then
        TEST_RUNNERS+=("phpunit")
    fi
    if [[ -f "tests/Pest.php" ]] || grep -q '"pestphp/pest"' composer.json 2>/dev/null; then
        TEST_RUNNERS+=("pest")
    fi
    if [[ -f "phpstan.neon" ]] || [[ -f "phpstan.neon.dist" ]]; then
        LINTERS+=("phpstan")
    fi
    if [[ -f "pint.json" ]] || grep -q '"laravel/pint"' composer.json 2>/dev/null; then
        LINTERS+=("pint")
    fi
    if [[ -f ".php-cs-fixer.php" ]] || [[ -f ".php-cs-fixer.dist.php" ]]; then
        LINTERS+=("php-cs-fixer")
    fi
fi

# 2. Node / TypeScript / Frontend
if [[ -f "package.json" ]]; then
    STACKS+=("Node.js")
    
    if [[ -f "pnpm-lock.yaml" ]]; then
        PACKAGE_MANAGERS+=("pnpm")
    elif [[ -f "yarn.lock" ]]; then
        PACKAGE_MANAGERS+=("yarn")
    elif [[ -f "bun.lockb" ]] || [[ -f "bun.lock" ]]; then
        PACKAGE_MANAGERS+=("bun")
    else
        PACKAGE_MANAGERS+=("npm")
    fi

    if [[ -f "tsconfig.json" ]]; then
        STACKS+=("TypeScript")
    fi

    if grep -q '"next"' package.json 2>/dev/null; then
        FRAMEWORKS+=("Next.js")
    elif grep -q '"react"' package.json 2>/dev/null; then
        FRAMEWORKS+=("React")
    fi

    if grep -q '"vue"' package.json 2>/dev/null; then
        FRAMEWORKS+=("Vue.js")
    fi

    if grep -q '"@nestjs/core"' package.json 2>/dev/null; then
        FRAMEWORKS+=("NestJS")
    fi

    if [[ -f "vitest.config.ts" ]] || [[ -f "vitest.config.js" ]] || grep -q '"vitest"' package.json 2>/dev/null; then
        TEST_RUNNERS+=("vitest")
    fi
    if [[ -f "jest.config.js" ]] || [[ -f "jest.config.ts" ]] || grep -q '"jest"' package.json 2>/dev/null; then
        TEST_RUNNERS+=("jest")
    fi
    if grep -q '"playwright"' package.json 2>/dev/null; then
        TEST_RUNNERS+=("playwright")
    fi

    if [[ -f "eslint.config.js" ]] || [[ -f "eslint.config.mjs" ]] || [[ -f ".eslintrc.json" ]] || [[ -f ".eslintrc.js" ]]; then
        LINTERS+=("eslint")
    fi
    if [[ -f "biome.json" ]] || [[ -f "biome.jsonc" ]]; then
        LINTERS+=("biome")
    fi
    if [[ -f ".prettierrc" ]] || [[ -f ".prettierrc.json" ]] || [[ -f ".prettierrc.js" ]]; then
        LINTERS+=("prettier")
    fi
fi

# 3. Python
if [[ -f "pyproject.toml" ]] || [[ -f "requirements.txt" ]] || [[ -f "Pipfile" ]] || [[ -f "setup.py" ]]; then
    STACKS+=("Python")
    if [[ -f "poetry.lock" ]]; then
        PACKAGE_MANAGERS+=("poetry")
    elif [[ -f "Pipfile.lock" ]]; then
        PACKAGE_MANAGERS+=("pipenv")
    elif [[ -f "uv.lock" ]]; then
        PACKAGE_MANAGERS+=("uv")
    else
        PACKAGE_MANAGERS+=("pip")
    fi

    if [[ -f "pyproject.toml" ]]; then
        if grep -q 'fastapi' pyproject.toml 2>/dev/null; then FRAMEWORKS+=("FastAPI"); fi
        if grep -q 'django' pyproject.toml 2>/dev/null; then FRAMEWORKS+=("Django"); fi
        if grep -q 'flask' pyproject.toml 2>/dev/null; then FRAMEWORKS+=("Flask"); fi
    fi

    if [[ -d "tests" ]] || [[ -f "pytest.ini" ]] || [[ -f "conftest.py" ]] || ( [[ -f "pyproject.toml" ]] && grep -q 'pytest' pyproject.toml 2>/dev/null ); then
        TEST_RUNNERS+=("pytest")
    fi

    if [[ -f "ruff.toml" ]] || ( [[ -f "pyproject.toml" ]] && grep -q 'ruff' pyproject.toml 2>/dev/null ); then
        LINTERS+=("ruff")
    fi
    if [[ -f ".flake8" ]]; then LINTERS+=("flake8"); fi
    if [[ -f "mypy.ini" ]] || ( [[ -f "pyproject.toml" ]] && grep -q 'mypy' pyproject.toml 2>/dev/null ); then
        LINTERS+=("mypy")
    fi
fi

# 4. Go
if [[ -f "go.mod" ]]; then
    STACKS+=("Go")
    PACKAGE_MANAGERS+=("go modules")
    TEST_RUNNERS+=("go test")
    if [[ -f ".golangci.yml" ]] || [[ -f ".golangci.yaml" ]]; then
        LINTERS+=("golangci-lint")
    fi
fi

# 5. Rust
if [[ -f "Cargo.toml" ]]; then
    STACKS+=("Rust")
    PACKAGE_MANAGERS+=("cargo")
    TEST_RUNNERS+=("cargo test")
    LINTERS+=("cargo clippy")
fi

# 6. Containers & Infra
if [[ -f "Dockerfile" ]]; then INFRA+=("Dockerfile"); fi
if [[ -f "docker-compose.yml" ]] || [[ -f "docker-compose.yaml" ]] || [[ -f "compose.yaml" ]] || [[ -f "compose.yml" ]]; then
    INFRA+=("Docker Compose")
    if [[ -f "docker-compose.yml" ]] && grep -q 'laravel.test' docker-compose.yml 2>/dev/null; then
        INFRA+=("Laravel Sail")
    fi
fi
if [[ -d ".devcontainer" ]]; then INFRA+=("Devcontainer"); fi

# 7. Runtime & Execution Context Awareness
DOCKER_AVAILABLE=0
DOCKER_RUNNING=0
IN_CONTAINER=0
DOCKER_SERVICES_RUNNING=()

if [[ -f "/.dockerenv" ]] || grep -q 'docker\|containerd' /proc/1/cgroup 2>/dev/null; then
    IN_CONTAINER=1
fi

if command -v docker >/dev/null 2>&1; then
    DOCKER_AVAILABLE=1
    if docker info >/dev/null 2>&1; then
        DOCKER_RUNNING=1
        if [[ -f "docker-compose.yml" ]] || [[ -f "docker-compose.yaml" ]] || [[ -f "compose.yaml" ]] || [[ -f "compose.yml" ]]; then
            ACTIVE_COMPOSE=$(docker compose ps --services --filter "status=running" 2>/dev/null || true)
            if [[ -n "$ACTIVE_COMPOSE" ]]; then
                while IFS= read -r s; do
                    [[ -n "$s" ]] && DOCKER_SERVICES_RUNNING+=("$s")
                done <<< "$ACTIVE_COMPOSE"
            fi
        fi
    fi
fi

if [[ $IN_CONTAINER -eq 1 ]]; then
    RUNTIME_MODE="IN_CONTAINER"
    RUNTIME_DESC="Executando diretamente dentro de um container Docker"
elif [[ ${#DOCKER_SERVICES_RUNNING[@]} -gt 0 ]]; then
    RUNTIME_MODE="DOCKER_ACTIVE"
    RUNTIME_DESC="Containers Docker ativos (${DOCKER_SERVICES_RUNNING[*]})"
elif [[ -f "docker-compose.yml" || -f "docker-compose.yaml" || -f "compose.yaml" || -f "compose.yml" ]]; then
    RUNTIME_MODE="DOCKER_STOPPED"
    RUNTIME_DESC="Docker Compose configurado, mas containers desligados ou daemon inativo"
else
    RUNTIME_MODE="NATIVE_HOST"
    RUNTIME_DESC="Host Nativo (execução direta no sistema operacional sem Docker)"
fi

# 8. CI Workflow & Strategy Analysis
CI_WORKFLOWS=()
CI_TEST_COMMANDS=()
CI_SERVICES_DETECTED=()
CI_RUNNER_TYPE="Nenhum"

if [[ -d ".github/workflows" ]]; then
    for wf in .github/workflows/*.yml .github/workflows/*.yaml; do
        if [[ -f "$wf" ]]; then
            CI_WORKFLOWS+=("$(basename "$wf")")
            for s in postgres mysql redis mariadb mongodb; do
                if grep -qi "image:.*$s" "$wf" 2>/dev/null; then
                    [[ ! " ${CI_SERVICES_DETECTED[*]:-} " =~ " ${s} " ]] && CI_SERVICES_DETECTED+=("$s")
                fi
            done
            if grep -q "runs-on:" "$wf" 2>/dev/null; then
                CI_RUNNER_TYPE="GitHub Actions Runner"
            fi
            RUN_LINES=$(grep -E '^[[:space:]]*run:[[:space:]]*.*(test|pest|phpunit|pytest)' "$wf" 2>/dev/null || true)
            if [[ -n "$RUN_LINES" ]]; then
                while IFS= read -r line; do
                    CMD_CLEAN=$(echo "$line" | sed -e 's/^[[:space:]]*run:[[:space:]]*//' -e 's/["'\'' ]*$//' -e 's/^["'\'' ]*//')
                    if [[ "$CMD_CLEAN" =~ (pest|phpunit|artisan[[:space:]]+test|npm[[:space:]]+test|pnpm[[:space:]]+test|yarn[[:space:]]+test|pytest|cargo[[:space:]]+test|go[[:space:]]+test) ]]; then
                        [[ ! " ${CI_TEST_COMMANDS[*]:-} " =~ " ${CMD_CLEAN} " ]] && CI_TEST_COMMANDS+=("$CMD_CLEAN")
                    fi
                done <<< "$RUN_LINES"
            fi
        fi
    done
elif [[ -f ".gitlab-ci.yml" ]]; then
    CI_WORKFLOWS+=(".gitlab-ci.yml")
    CI_RUNNER_TYPE="GitLab Runner"
fi

# Format Output
join_by() { local d=${1-} f=${2-}; if shift 2; then printf %s "$f" "${@/#/$d}"; fi; }

echo "Stacks:            ${STACKS[*]:-None detected}"
echo "Frameworks:        ${FRAMEWORKS[*]:-None detected}"
echo "Package Managers:  ${PACKAGE_MANAGERS[*]:-None detected}"
echo "Test Runners:      ${TEST_RUNNERS[*]:-None detected}"
echo "Linters/Checkers:  ${LINTERS[*]:-None detected}"
echo "Infra/Containers:  ${INFRA[*]:-None detected}"
echo ""

DOCKER_STATUS_LABEL="Não instalado no host"
if [[ $DOCKER_RUNNING -eq 1 ]]; then
    DOCKER_STATUS_LABEL="Ativo (Disponível)"
elif [[ $DOCKER_AVAILABLE -eq 1 ]]; then
    DOCKER_STATUS_LABEL="Inativo / Parado"
fi

echo "--- Runtime & CI Strategy Awareness ---"
echo "Runtime Mode:      $RUNTIME_MODE ($RUNTIME_DESC)"
echo "Docker Daemon:     $DOCKER_STATUS_LABEL"
if [[ ${#CI_WORKFLOWS[@]} -gt 0 ]]; then
    echo "CI Pipelines:      ${CI_WORKFLOWS[*]} ($CI_RUNNER_TYPE)"
    [[ ${#CI_SERVICES_DETECTED[@]} -gt 0 ]] && echo "CI Services:       ${CI_SERVICES_DETECTED[*]} (Declarados no workflow)"
    [[ ${#CI_TEST_COMMANDS[@]} -gt 0 ]] && echo "CI Test Steps:     ${CI_TEST_COMMANDS[*]}"
    
    # Bridge recommendation
    if [[ "$RUNTIME_MODE" == "DOCKER_ACTIVE" ]]; then
        if [[ " ${DOCKER_SERVICES_RUNNING[*]} " =~ " laravel.test " ]]; then
            echo "Local Execution:   Ambiente Docker ativo -> Use 'docker compose exec -T laravel.test <cmd>' ou './vendor/bin/sail test'"
        else
            echo "Local Execution:   Ambiente Docker ativo -> Use 'docker compose exec -T ${DOCKER_SERVICES_RUNNING[0]} <cmd>'"
        fi
    elif [[ "$RUNTIME_MODE" == "DOCKER_STOPPED" ]]; then
        echo "Local Execution:   Containers desligados -> Inicie com 'docker compose up -d' ou execute no host nativo se dependências existirem"
    elif [[ "$RUNTIME_MODE" == "IN_CONTAINER" ]]; then
        echo "Local Execution:   Dentro do container -> Execute diretamente via binários do container"
    else
        echo "Local Execution:   Host Nativo puro -> Execute diretamente via ferramentas do host (ex: pest, npm test, pytest)"
    fi
else
    echo "CI Pipelines:      Nenhuma esteira de CI detectada"
fi
echo ""

# Git status & Canonical Topology Audit
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "detached")
    UNCOMMITTED=$(git status --porcelain | wc -l | tr -d ' ')
    echo "Git Branch:        $CURRENT_BRANCH"
    echo "Uncommitted Files: $UNCOMMITTED"

    # Canonical Branch Topology Verification (Modo 3 Branches ou Modo 2 Branches)
    HAS_MAIN=0
    HAS_STAGING=0
    HAS_DEV=0
    if git show-ref --verify --quiet refs/heads/main || git show-ref --verify --quiet refs/heads/master || git show-ref --verify --quiet refs/remotes/origin/main || git show-ref --verify --quiet refs/remotes/origin/master; then HAS_MAIN=1; fi
    if git show-ref --verify --quiet refs/heads/staging || git show-ref --verify --quiet refs/heads/homolog || git show-ref --verify --quiet refs/heads/homologacao || git show-ref --verify --quiet refs/remotes/origin/staging; then HAS_STAGING=1; fi
    if git show-ref --verify --quiet refs/heads/dev || git show-ref --verify --quiet refs/heads/develop || git show-ref --verify --quiet refs/remotes/origin/dev; then HAS_DEV=1; fi

    echo ""
    echo "--- Canonical Branch Topology Audit ---"
    if [[ $HAS_MAIN -eq 1 && $HAS_STAGING -eq 1 && $HAS_DEV -eq 1 ]]; then
        echo "Topology Status:   [✔ CONFORME - MODO ENTERPRISE 3-BRANCHES] (dev -> staging -> main)"
    elif [[ $HAS_MAIN -eq 1 && $HAS_DEV -eq 1 ]]; then
        echo "Topology Status:   [✔ CONFORME - MODO CLÁSSICO 2-BRANCHES] (dev -> main)"
    else
        echo "Topology Status:   [⚠️ PENDENTE DE ALINHAMENTO] Repositório sem branch de desenvolvimento 'dev'."
        echo "  • Produção (main):        $([ $HAS_MAIN -eq 1 ] && echo '✔' || echo '❌ Ausente')"
        echo "  • Homologação (staging):  $([ $HAS_STAGING -eq 1 ] && echo '✔' || echo '❌ Ausente')"
        echo "  • Desenvolvimento (dev):  $([ $HAS_DEV -eq 1 ] && echo '✔' || echo '❌ Ausente')"
        echo ""
        echo "💡 Orientação de Engenharia CEH (Escolha o seu modo):"
        echo "   [Opção 1 - Clássico]:    bash $(dirname "$0")/setup-branches.sh --classic    (dev e main)"
        echo "   [Opção 2 - Enterprise]:  bash $(dirname "$0")/setup-branches.sh --enterprise (dev, staging e main)"
    fi
else
    echo "Git:               Not a git repository"
fi
echo "========================================"
