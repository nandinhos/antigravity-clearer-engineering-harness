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

rm -f "$OUTPUT_FILE"
exit $EXIT_CODE
