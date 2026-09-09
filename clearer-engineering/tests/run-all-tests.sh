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

# 1. Plugin Validation Test via Antigravity CLI or Native JSON Spec
if command -v agy >/dev/null 2>&1; then
    run_test "Antigravity CLI plugin validation" \
        "agy plugin validate '$PLUGIN_DIR' >/dev/null"
else
    run_test "Plugin Manifest & Structure validation (Native CI fallback)" \
        "test -f '$PLUGIN_DIR/plugin.json' && python3 -c \"import json; json.load(open('$PLUGIN_DIR/plugin.json'))\""
fi

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

run_test "Safety Gate: Comprehensive Safety Matrix Suite (24 test cases including RTK)" \
    "python3 '$PLUGIN_DIR/tests/test_safety_matrix.py' >/dev/null"

run_test "Safety Gate: Allow safe command 'npm test' (ALLOW)" \
    "python3 '$PLUGIN_DIR/scripts/safety-gate.py' --check 'npm test' | grep -q '\"decision\": \"allow\"'"

run_test "Safety Gate: Allow safe command 'git status' (ALLOW)" \
    "python3 '$PLUGIN_DIR/scripts/safety-gate.py' --check 'git status' | grep -q '\"decision\": \"allow\"'"

run_test "Safety Gate: Allow safe RTK command 'rtk git status' (ALLOW)" \
    "python3 '$PLUGIN_DIR/scripts/safety-gate.py' --check 'rtk git status' | grep -q '\"decision\": \"allow\"'"

run_test "Safety Gate: Block destructive RTK command in production (DENY)" \
    "python3 '$PLUGIN_DIR/scripts/safety-gate.py' --check 'rtk php artisan migrate:fresh' --env production | grep -q '\"decision\": \"deny\"'"

run_test "Safety Gate: Staging tier asks for RTK destructive command with 2 alerts (ASK)" \
    "python3 '$PLUGIN_DIR/scripts/safety-gate.py' --check 'rtk git reset --hard HEAD~1' --env staging | grep -q '\"decision\": \"ask\"' && python3 '$PLUGIN_DIR/scripts/safety-gate.py' --check 'rtk git reset --hard HEAD~1' --env staging | grep -q 'ALERTA 1/2' && python3 '$PLUGIN_DIR/scripts/safety-gate.py' --check 'rtk git reset --hard HEAD~1' --env staging | grep -q 'ALERTA 2/2'"

run_test "Safety Gate: Hard block catastrophic RTK 'rtk rm -rf /' (DENY in any env)" \
    "python3 '$PLUGIN_DIR/scripts/safety-gate.py' --check 'rtk rm -rf /' | grep -q '\"decision\": \"deny\"'"

run_test "Safety Gate: Allow safe scratch cleanup 'rm -rf scratch/temp' (ALLOW)" \
    "python3 '$PLUGIN_DIR/scripts/safety-gate.py' --check 'rm -rf scratch/temp' | grep -q '\"decision\": \"allow\"'"

run_test "Safety Gate: Allow safe single file checkout 'git checkout app/Model.php' (ALLOW)" \
    "python3 '$PLUGIN_DIR/scripts/safety-gate.py' --check 'git checkout app/Model.php' | grep -q '\"decision\": \"allow\"'"


# 3. Preflight & Stack Awareness Scripts
run_test "Script: detect-project.sh execution & environment awareness" \
    "bash '$PLUGIN_DIR/scripts/detect-project.sh' . | grep 'CEH Stack & Environment Awareness Report' >/dev/null"

run_test "Script: detect-project.sh reports Canonical Branch Topology" \
    "bash -c 'TMP=\$(mktemp -d); git -C \"\$TMP\" init -b main >/dev/null; git -C \"\$TMP\" config user.name T; git -C \"\$TMP\" config user.email t@t.l; touch \"\$TMP/f\"; git -C \"\$TMP\" add f; git -C \"\$TMP\" commit -m i >/dev/null; bash \"$PLUGIN_DIR/scripts/detect-project.sh\" \"\$TMP\" | grep \"Canonical Branch Topology Audit\" >/dev/null && rm -rf \"\$TMP\"'"

run_test "Script: setup-branches.sh --enterprise (Modo 3 Branches)" \
    "bash -c 'TMP=\$(mktemp -d); git -C \"\$TMP\" init -b main >/dev/null; git -C \"\$TMP\" config user.name T; git -C \"\$TMP\" config user.email t@t.l; touch \"\$TMP/f\"; git -C \"\$TMP\" add f; git -C \"\$TMP\" commit -m i >/dev/null; bash \"$PLUGIN_DIR/scripts/setup-branches.sh\" --enterprise \"\$TMP\" >/dev/null; git -C \"\$TMP\" show-ref --verify --quiet refs/heads/dev && git -C \"\$TMP\" show-ref --verify --quiet refs/heads/staging && bash \"$PLUGIN_DIR/scripts/detect-project.sh\" \"\$TMP\" | grep 'MODO ENTERPRISE' >/dev/null && rm -rf \"\$TMP\"'"

run_test "Script: setup-branches.sh --classic (Modo 2 Branches)" \
    "bash -c 'TMP=\$(mktemp -d); git -C \"\$TMP\" init -b main >/dev/null; git -C \"\$TMP\" config user.name T; git -C \"\$TMP\" config user.email t@t.l; touch \"\$TMP/f\"; git -C \"\$TMP\" add f; git -C \"\$TMP\" commit -m i >/dev/null; bash \"$PLUGIN_DIR/scripts/setup-branches.sh\" --classic \"\$TMP\" >/dev/null; git -C \"\$TMP\" show-ref --verify --quiet refs/heads/dev && ! git -C \"\$TMP\" show-ref --verify --quiet refs/heads/staging && bash \"$PLUGIN_DIR/scripts/detect-project.sh\" \"\$TMP\" | grep 'MODO CLÁSSICO' >/dev/null && rm -rf \"\$TMP\"'"

run_test "Script: preflight.sh execution" \
    "bash '$PLUGIN_DIR/scripts/preflight.sh' | grep 'CEH Preflight Inspection' >/dev/null"

# 4. Diff & Evidence Reporting
run_test "Script: diff-audit.sh execution" \
    "bash '$PLUGIN_DIR/scripts/diff-audit.sh' | grep 'CEH Diff & Blast Radius Audit' >/dev/null"

run_test "Script: evidence-report.sh output format" \
    "bash '$PLUGIN_DIR/scripts/evidence-report.sh' | grep '## RESULT' >/dev/null && bash '$PLUGIN_DIR/scripts/evidence-report.sh' | grep '## CONFIDENCE' >/dev/null"

# 5. Deterministic Test Runner & Non-Masking Tests
run_test "Test Runner: Success scenario returns exit code 0" \
    "bash '$PLUGIN_DIR/scripts/test-runner.sh' 'true' | grep 'STATUS:    PASS' >/dev/null"

run_test "Test Runner: Failing test correctly reports FAIL without masking" \
    "bash '$PLUGIN_DIR/scripts/test-runner.sh' 'false' | grep 'STATUS:    FAIL' >/dev/null"

# 6. Global Agent Profile Availability & Tools Configuration
if command -v agy >/dev/null 2>&1; then
    run_test "Antigravity Agent Profile 'clearer-harness' is recognized" \
        "agy agent | grep 'clearer-harness' >/dev/null"
fi

if [[ -f "$HOME/.gemini/config/agents/clearer-harness/agent.md" ]]; then
    run_test "Agent Profile 'clearer-harness' has write and execution tools declared" \
        "grep -q 'write_to_file' '$HOME/.gemini/config/agents/clearer-harness/agent.md' && grep -q 'run_command' '$HOME/.gemini/config/agents/clearer-harness/agent.md'"
else
    run_test "Agent Profile template in install.sh has write and execution tools declared" \
        "grep -q 'write_to_file' '$PLUGIN_DIR/../install.sh' && grep -q 'run_command' '$PLUGIN_DIR/../install.sh'"
fi

run_test "Plugin Subagent 'ceh-implementer' has code editing tools" \
    "grep -q 'write_to_file' '$PLUGIN_DIR/agents/implementer/agent.md' && grep -q 'replace_file_content' '$PLUGIN_DIR/agents/implementer/agent.md'"

run_test "Plugin Subagent 'ceh-test-engineer' has execution and editing tools" \
    "grep -q 'run_command' '$PLUGIN_DIR/agents/test-engineer/agent.md' && grep -q 'write_to_file' '$PLUGIN_DIR/agents/test-engineer/agent.md'"

run_test "Skill: clearer-bugfix implements Systematic Debugging 5 Blocking Gates" \
    "grep -q 'Gate 0 — TRIAGE' '$PLUGIN_DIR/skills/clearer-bugfix/SKILL.md' && grep -q 'Gate 1 — REPRODUCE' '$PLUGIN_DIR/skills/clearer-bugfix/SKILL.md' && grep -q 'Gate 2 — ISOLATE' '$PLUGIN_DIR/skills/clearer-bugfix/SKILL.md' && grep -q 'Gate 3 — ROOT CAUSE' '$PLUGIN_DIR/skills/clearer-bugfix/SKILL.md' && grep -q 'Gate 4 — FIX & HARDEN' '$PLUGIN_DIR/skills/clearer-bugfix/SKILL.md'"

run_test "Skill: native learned-lesson skill packaged with dev-memory support" \
    "test -f '$PLUGIN_DIR/skills/learned-lesson/SKILL.md' && grep -q 'Learned Lesson Engine v2.0' '$PLUGIN_DIR/skills/learned-lesson/SKILL.md' && grep -q 'dev-memory' '$PLUGIN_DIR/skills/learned-lesson/SKILL.md'"

run_test "Subagent: ceh-investigator includes Falsifiable Hypotheses Matrix guidance" \
    "grep -q 'Matriz de Hipóteses Falsificáveis' '$PLUGIN_DIR/agents/investigator/agent.md'"

run_test "Subagent: ceh-reviewer verifies regression detector and anti-opportunistic refactoring" \
    "grep -q 'clearer-bugfix' '$PLUGIN_DIR/agents/reviewer/agent.md' && grep -q 'Detector' '$PLUGIN_DIR/agents/reviewer/agent.md'"

run_test "Skill: clearer-adhd packaged with Ponytail UX 10 Heuristics & Break-Rules" \
    "test -f '$PLUGIN_DIR/skills/clearer-adhd/SKILL.md' && grep -q 'Lead with Action' '$PLUGIN_DIR/skills/clearer-adhd/SKILL.md' && grep -q 'Break-Rules' '$PLUGIN_DIR/skills/clearer-adhd/SKILL.md' && grep -q 'Ponytail UX' '$PLUGIN_DIR/rules/AGENTS.md'"

# 7. Shell Aliases Configuration
run_test "Shell alias 'agy-ceh' configured in shell rc" \
    "(test -f ~/.bashrc && grep -q 'alias agy-ceh=' ~/.bashrc) || (test -f ~/.zshrc && grep -q 'alias agy-ceh=' ~/.zshrc)"

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
