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

# 2. Safety Gate Unit & Environment Tests
run_test "Safety Gate: Hard block catastrophic 'rm -rf /' (DENY in any env)" \
    "python3 '$PLUGIN_DIR/scripts/safety-gate.py' --check 'rm -rf /' | grep -q '\"decision\": \"deny\"'"

run_test "Safety Gate: Production tier strictly blocks destructive commands (DENY)" \
    "python3 '$PLUGIN_DIR/scripts/safety-gate.py' --check 'git push origin main --force' --env production | grep -q '\"decision\": \"deny\"'"

run_test "Safety Gate: Staging tier requires confirmation with 2 explicit alerts (ASK)" \
    "python3 '$PLUGIN_DIR/scripts/safety-gate.py' --check 'git reset --hard HEAD~1' --env staging | grep -q '\"decision\": \"ask\"' && python3 '$PLUGIN_DIR/scripts/safety-gate.py' --check 'git reset --hard HEAD~1' --env staging | grep -q 'ALERTA 1/2' && python3 '$PLUGIN_DIR/scripts/safety-gate.py' --check 'git reset --hard HEAD~1' --env staging | grep -q 'ALERTA 2/2'"

run_test "Safety Gate: Staging tier asks for git clean -fdx (ASK)" \
    "python3 '$PLUGIN_DIR/scripts/safety-gate.py' --check 'git clean -fdx' --env staging | grep -q '\"decision\": \"ask\"'"

run_test "Safety Gate: Development tier permits destructive actions with rollback notice (ALLOW)" \
    "python3 '$PLUGIN_DIR/scripts/safety-gate.py' --check 'git reset --hard HEAD~1' --env development | grep -q '\"decision\": \"allow\"'"

run_test "Safety Gate: Comprehensive Safety Matrix Suite (18 test cases)" \
    "python3 '$PLUGIN_DIR/tests/test_safety_matrix.py' >/dev/null"

run_test "Safety Gate: Allow safe command 'npm test' (ALLOW)" \
    "python3 '$PLUGIN_DIR/scripts/safety-gate.py' --check 'npm test' | grep -q '\"decision\": \"allow\"'"

run_test "Safety Gate: Allow safe command 'git status' (ALLOW)" \
    "python3 '$PLUGIN_DIR/scripts/safety-gate.py' --check 'git status' | grep -q '\"decision\": \"allow\"'"

run_test "Safety Gate: Allow safe scratch cleanup 'rm -rf scratch/temp' (ALLOW)" \
    "python3 '$PLUGIN_DIR/scripts/safety-gate.py' --check 'rm -rf scratch/temp' | grep -q '\"decision\": \"allow\"'"

run_test "Safety Gate: Allow safe single file checkout 'git checkout app/Model.php' (ALLOW)" \
    "python3 '$PLUGIN_DIR/scripts/safety-gate.py' --check 'git checkout app/Model.php' | grep -q '\"decision\": \"allow\"'"


# 3. Preflight & Stack Awareness Scripts
run_test "Script: detect-project.sh execution & environment awareness" \
    "bash '$PLUGIN_DIR/scripts/detect-project.sh' . | grep -q 'CEH Stack & Environment Awareness Report'"

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

# 6. Global Agent Profile Availability & Tools Configuration
run_test "Antigravity Agent Profile 'clearer-harness' is recognized" \
    "agy agent | grep -q 'clearer-harness'"

run_test "Agent Profile 'clearer-harness' has write and execution tools declared" \
    "grep -q 'write_to_file' '$HOME/.gemini/config/agents/clearer-harness/agent.md' && grep -q 'run_command' '$HOME/.gemini/config/agents/clearer-harness/agent.md'"

run_test "Plugin Subagent 'ceh-implementer' has code editing tools" \
    "grep -q 'write_to_file' '$PLUGIN_DIR/agents/implementer/agent.md' && grep -q 'replace_file_content' '$PLUGIN_DIR/agents/implementer/agent.md'"

run_test "Plugin Subagent 'ceh-test-engineer' has execution and editing tools" \
    "grep -q 'run_command' '$PLUGIN_DIR/agents/test-engineer/agent.md' && grep -q 'write_to_file' '$PLUGIN_DIR/agents/test-engineer/agent.md'"

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
