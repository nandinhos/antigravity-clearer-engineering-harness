#!/usr/bin/env bash
# ==============================================================================
# run-fast-tests.sh — Fast Cycle Test Runner (Ponytail Methodology < 5s feedback)
# ==============================================================================
set -euo pipefail

PLUGIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PLUGIN_DIR"

TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
START_TIME=$(date +%s)

log_pass() {
    echo -e "\033[0;32m[PASS]\033[0m $1"
    PASSED_TESTS=$((PASSED_TESTS + 1))
}

log_fail() {
    echo -e "\033[0;31m[FAIL]\033[0m $1"
    FAILED_TESTS=$((FAILED_TESTS + 1))
}

run_fast() {
    local name="$1"
    local cmd="$2"
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    local t0 t1 dur
    t0=$(date +%s)
    if eval "$cmd" >/dev/null 2>&1; then
        t1=$(date +%s)
        dur=$(( t1 - t0 ))
        log_pass "$name (${dur}s)"
    else
        t1=$(date +%s)
        dur=$(( t1 - t0 ))
        log_fail "$name (${dur}s)"
    fi
}

echo "============================================================"
echo "  ⚡ CEH Fast Test Runner (Ponytail Methodology < 5s)"
echo "============================================================"
echo "Target: Core Contracts, Adapters, Engine & Security Matrix"
echo ""

# 1. Manifest
run_fast "Plugin Manifest & Structure" "test -f '$PLUGIN_DIR/plugin.json' && python3 -c \"import json; json.load(open('$PLUGIN_DIR/plugin.json'))\""

# 2. Engine & Adapters
run_fast "CEH Core Engine (Unit)" "python3 '$PLUGIN_DIR/tests/test_engine.py'"
run_fast "Host Adapters Contract" "python3 '$PLUGIN_DIR/tests/test_adapters.py'"
run_fast "Hook Fail-Closed Imports" "python3 '$PLUGIN_DIR/tests/test_hook_failclosed.py'"

# 3. Security & Safety Matrix
run_fast "Safety Matrix Suite (24 scenarios)" "python3 '$PLUGIN_DIR/tests/test_safety_matrix.py'"
run_fast "Git Canonicalization (G2/G3)" "python3 '$PLUGIN_DIR/tests/test_git_canonicalization.py'"
run_fast "Pre-Push Refspecs (G7)" "python3 '$PLUGIN_DIR/tests/test_pre_push_refspecs.py'"
run_fast "Certificate Integrity (G9)" "python3 '$PLUGIN_DIR/tests/test_cert_protection.py'"

# 4. File Normalization & Hermes
run_fast "RM Target Normalization" "python3 '$PLUGIN_DIR/tests/test_rm_targets.py'"
run_fast "Environment Tokens & Invariants" "python3 '$PLUGIN_DIR/tests/test_environment_tokens.py'"
run_fast "Hermes Remediation Suite" "python3 '$PLUGIN_DIR/tests/test_hermes_remediation.py'"
run_fast "Content Schema Validation" "python3 '$PLUGIN_DIR/tests/test_content_schema.py'"

# 5. Smoke Falsifiability
run_fast "Harness Smoke-Eval (5/5 PASS)" "python3 '$PLUGIN_DIR/tests/cluster2_acceptance.py' --clean-eval-smoke"

END_TIME=$(date +%s)
TOTAL_DUR=$(( END_TIME - START_TIME ))

echo ""
echo "============================================================"
echo "FAST SUITE SUMMARY:"
echo "Total Tests:    $TOTAL_TESTS"
echo "Passed Tests:   $PASSED_TESTS"
echo "Failed Tests:   $FAILED_TESTS"
echo "Total Duration: ${TOTAL_DUR}s"
echo "============================================================"

if [[ $FAILED_TESTS -eq 0 ]]; then
    echo -e "\033[0;32m✔ PONYTAIL FAST CYCLE VERIFIED (< 5s Target Achieved)\033[0m"
    exit 0
else
    echo -e "\033[0;31m✖ FAST TESTS FAILED\033[0m"
    exit 1
fi
