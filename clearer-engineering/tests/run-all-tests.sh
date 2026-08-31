#!/usr/bin/env bash
# ==============================================================================
# run-all-tests.sh - Comprehensive Test Suite for CLEARER Engineering Harness
# ==============================================================================
set -u

PLUGIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PLUGIN_DIR"

TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

log_pass() {
    echo -e "\033[0;32m[PASS]\033[0m $1"
    PASSED_TESTS=$((PASSED_TESTS + 1))
}

log_fail() {
    echo -e "\033[0;31m[FAIL]\033[0m $1"
    FAILED_TESTS=$((FAILED_TESTS + 1))
}

run_test() {
    local name="$1"
    local cmd="$2"
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo "------------------------------------------------------------"
    echo "Running Test $TOTAL_TESTS: $name"
    if eval "$cmd"; then
        log_pass "$name"
    else
        log_fail "$name"
    fi
}

echo "============================================================"
echo "    CLEARER Engineering Harness (CEH) - Test Suite"
echo "============================================================"
echo "Plugin Directory: $PLUGIN_DIR"
echo "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo ""

# 1. Plugin Validation Test via Antigravity CLI
run_test "Antigravity CLI plugin validation" \
    "agy plugin validate '$PLUGIN_DIR' >/dev/null"

# 2. Safety Gate Unit Tests (Deny / Ask / Allow)
run_test "Safety Gate: Hard block 'rm -rf /' (DENY)" \
    "python3 '$PLUGIN_DIR/scripts/safety-gate.py' --check 'rm -rf /' | grep -q '\"decision\": \"deny\"'"

run_test "Safety Gate: Hard block 'DROP DATABASE prod' (DENY)" \
    "python3 '$PLUGIN_DIR/scripts/safety-gate.py' --check 'DROP DATABASE production' | grep -q '\"decision\": \"deny\"'"

run_test "Safety Gate: Ask confirmation for 'git reset --hard' (ASK)" \
    "python3 '$PLUGIN_DIR/scripts/safety-gate.py' --check 'git reset --hard HEAD~1' | grep -q '\"decision\": \"ask\"'"

run_test "Safety Gate: Ask confirmation for 'git clean -fdx' (ASK)" \
    "python3 '$PLUGIN_DIR/scripts/safety-gate.py' --check 'git clean -fdx' | grep -q '\"decision\": \"ask\"'"

run_test "Safety Gate: Ask confirmation for 'git push --force' (ASK)" \
    "python3 '$PLUGIN_DIR/scripts/safety-gate.py' --check 'git push origin main --force' | grep -q '\"decision\": \"ask\"'"

run_test "Safety Gate: Ask confirmation for 'artisan migrate:fresh' (ASK)" \
    "python3 '$PLUGIN_DIR/scripts/safety-gate.py' --check 'php artisan migrate:fresh' | grep -q '\"decision\": \"ask\"'"

run_test "Safety Gate: Allow safe command 'npm test' (ALLOW)" \
    "python3 '$PLUGIN_DIR/scripts/safety-gate.py' --check 'npm test' | grep -q '\"decision\": \"allow\"'"

run_test "Safety Gate: Allow safe command 'git status' (ALLOW)" \
    "python3 '$PLUGIN_DIR/scripts/safety-gate.py' --check 'git status' | grep -q '\"decision\": \"allow\"'"

run_test "Safety Gate: Allow safe scratch cleanup 'rm -rf scratch/temp' (ALLOW)" \
    "python3 '$PLUGIN_DIR/scripts/safety-gate.py' --check 'rm -rf scratch/temp' | grep -q '\"decision\": \"allow\"'"

run_test "Safety Gate: Allow safe single file checkout 'git checkout app/Model.php' (ALLOW)" \
    "python3 '$PLUGIN_DIR/scripts/safety-gate.py' --check 'git checkout app/Model.php' | grep -q '\"decision\": \"allow\"'"


# 3. Preflight & Stack Awareness Scripts
run_test "Script: detect-project.sh execution" \
    "bash '$PLUGIN_DIR/scripts/detect-project.sh' . | grep -q 'CEH Stack Awareness Report'"

run_test "Script: preflight.sh execution" \
    "bash '$PLUGIN_DIR/scripts/preflight.sh' | grep -q 'CEH Preflight Inspection'"

# 4. Diff & Evidence Reporting
run_test "Script: diff-audit.sh execution" \
    "bash '$PLUGIN_DIR/scripts/diff-audit.sh' | grep -q 'CEH Diff & Blast Radius Audit'"

run_test "Script: evidence-report.sh output format" \
    "bash '$PLUGIN_DIR/scripts/evidence-report.sh' | grep -q '## RESULT' && bash '$PLUGIN_DIR/scripts/evidence-report.sh' | grep -q '## CONFIDENCE'"

# 5. Deterministic Test Runner & Non-Masking Tests
run_test "Test Runner: Success scenario returns exit code 0" \
    "bash '$PLUGIN_DIR/scripts/test-runner.sh' 'true' | grep -q 'STATUS:    PASS'"

run_test "Test Runner: Failing test correctly reports FAIL without masking" \
    "bash '$PLUGIN_DIR/scripts/test-runner.sh' 'false' | grep -q 'STATUS:    FAIL'"

# 6. Global Agent Profile Availability
run_test "Antigravity Agent Profile 'clearer-harness' is recognized" \
    "agy agent | grep -q 'clearer-harness'"

# 7. Shell Aliases Configuration
run_test "Shell alias 'agy-ceh' configured in ~/.bashrc and ~/.zshrc" \
    "grep -q 'alias agy-ceh=' ~/.bashrc && grep -q 'alias agy-ceh=' ~/.zshrc"

echo ""
echo "============================================================"
echo "TEST RESULTS SUMMARY:"
echo "Total Tests:   $TOTAL_TESTS"
echo "Passed Tests:  $PASSED_TESTS"
echo "Failed Tests:  $FAILED_TESTS"
echo "============================================================"

if [[ $FAILED_TESTS -eq 0 ]]; then
    echo -e "\033[0;32mALL CEH HARNESS TESTS PASSED SUCCESSFULLY (100%)\033[0m"
    exit 0
else
    echo -e "\033[0;31mSOME TESTS FAILED\033[0m"
    exit 1
fi
