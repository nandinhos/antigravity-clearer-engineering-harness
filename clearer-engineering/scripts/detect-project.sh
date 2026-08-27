#!/usr/bin/env bash
# ==============================================================================
# detect-project.sh - Stack and Tooling Detector for CLEARER Engineering Harness
# ==============================================================================
set -euo pipefail

TARGET_DIR="${1:-$(pwd)}"
cd "$TARGET_DIR"

echo "=== [CEH Stack Awareness Report] ==="
echo "Target Directory: $TARGET_DIR"
echo "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
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

# Format Output
join_by() { local d=${1-} f=${2-}; if shift 2; then printf %s "$f" "${@/#/$d}"; fi; }

echo "Stacks:            ${STACKS[*]:-None detected}"
echo "Frameworks:        ${FRAMEWORKS[*]:-None detected}"
echo "Package Managers:  ${PACKAGE_MANAGERS[*]:-None detected}"
echo "Test Runners:      ${TEST_RUNNERS[*]:-None detected}"
echo "Linters/Checkers:  ${LINTERS[*]:-None detected}"
echo "Infra/Containers:  ${INFRA[*]:-None detected}"
echo ""

# Git status overview
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "detached")
    UNCOMMITTED=$(git status --porcelain | wc -l | tr -d ' ')
    echo "Git Branch:        $CURRENT_BRANCH"
    echo "Uncommitted Files: $UNCOMMITTED"
else
    echo "Git:               Not a git repository"
fi
echo "========================================"
