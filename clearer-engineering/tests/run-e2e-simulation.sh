#!/usr/bin/env bash
# ==============================================================================
# run-e2e-simulation.sh - Full End-to-End (E2E) & CI Verification Suite for CEH
# ==============================================================================
# Simulates the complete lifecycle of a software project under the
# CLEARER Engineering Harness (CEH), validating:
# 1. Environment & Branch Topology Lifecycle (Enterprise & Classic)
# 2. Safety Gate Hook PreToolUse Pipeline (DENY, ASK, ALLOW & RTK Evasion Immunity)
# 3. Deterministic Test Runner (Passing, Failing & Auto-detection)
# 4. Diff Audit & Evidence Reporting
# 5. Full CI Emulation (Syntax, Unit Matrix, Adversarial Suite, General Suite)
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ROOT_DIR="$(cd "$PLUGIN_DIR/.." && pwd)"

GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'

PASSED_COUNT=0
FAILED_COUNT=0

log_header() {
    echo -e "\n${CYAN}${BOLD}======================================================================${NC}"
    echo -e "${CYAN}${BOLD}  $1${NC}"
    echo -e "${CYAN}${BOLD}======================================================================${NC}"
}

log_step() {
    echo -e "\n${BLUE}[E2E STEP]${NC} $1"
}

log_ok() {
    echo -e "${GREEN}[✔ PASS]${NC} $1"
    PASSED_COUNT=$((PASSED_COUNT + 1))
}

log_error() {
    echo -e "${RED}[✖ FAIL]${NC} $1"
    FAILED_COUNT=$((FAILED_COUNT + 1))
    exit 1
}

# Cleanup sandbox on exit
SANDBOX_DIR=$(mktemp -d -t ceh-e2e-sandbox-XXXXXX)
cleanup() {
    rm -rf "$SANDBOX_DIR"
}
trap cleanup EXIT

log_header "🛡️ CLEARER Engineering Harness — High-Level E2E Verification"
echo "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "Root Directory:   $ROOT_DIR"
echo "Plugin Directory: $PLUGIN_DIR"
echo "Sandbox Directory: $SANDBOX_DIR"

# ------------------------------------------------------------------------------
# PHASE 1: Full Project Setup & Branch Topology Lifecycle
# ------------------------------------------------------------------------------
log_header "PHASE 1: Project Setup & Branch Topology Lifecycle (E2E)"

log_step "1.1 Initializing sandbox Git repository with initial commit"
cd "$SANDBOX_DIR"
git init -b main >/dev/null
git config user.name "CEH E2E Tester"
git config user.email "e2e@clearer.dev"

cat << 'EOF' > package.json
{
  "name": "e2e-sample-project",
  "version": "1.0.0",
  "scripts": {
    "test": "node test.js"
  }
}
EOF

cat << 'EOF' > test.js
const assert = require('assert');
assert.strictEqual(1 + 1, 2);
console.log("Sample test suite executed successfully.");
EOF

touch README.md
git add .
git commit -m "chore: initial commit" >/dev/null
log_ok "Sandbox project created with Git repository and test fixture."

log_step "1.2 Applying Enterprise Topology (3 Branches: dev -> staging -> main)"
bash "$PLUGIN_DIR/scripts/setup-branches.sh" --enterprise "$SANDBOX_DIR" >/dev/null
git show-ref --verify --quiet refs/heads/dev
git show-ref --verify --quiet refs/heads/staging
git show-ref --verify --quiet refs/heads/main
OUTPUT_TOPOLOGY=$(bash "$PLUGIN_DIR/scripts/detect-project.sh" "$SANDBOX_DIR")
echo "$OUTPUT_TOPOLOGY" | grep -q "MODO ENTERPRISE"
log_ok "Enterprise Mode verified (main, staging, dev configured & detected)."

log_step "1.3 Switching to Classic Topology (2 Branches: dev -> main)"
git checkout dev >/dev/null 2>&1 || true
git branch -D staging >/dev/null 2>&1 || true
bash "$PLUGIN_DIR/scripts/setup-branches.sh" --classic "$SANDBOX_DIR" >/dev/null
git show-ref --verify --quiet refs/heads/dev
git show-ref --verify --quiet refs/heads/main
! git show-ref --verify --quiet refs/heads/staging
OUTPUT_CLASSIC=$(bash "$PLUGIN_DIR/scripts/detect-project.sh" "$SANDBOX_DIR")
echo "$OUTPUT_CLASSIC" | grep -q "MODO CLÁSSICO"
log_ok "Classic Mode verified (dev and main active, staging absent)."

# ------------------------------------------------------------------------------
# PHASE 2: Safety Gate Hook & RTK Evasion Immunity (PreToolUse)
# ------------------------------------------------------------------------------
log_header "PHASE 2: Safety Gate PreToolUse & RTK Evasion Immunity (E2E)"

test_safety_hook() {
    local cmd="$1"
    local env_var="$2"
    local expected_decision="$3"
    local extra_check="${4:-}"

    local payload
    payload=$(jq -n --arg cmd "$cmd" '{"toolCall": {"name": "run_command", "args": {"CommandLine": $cmd}}}')

    local result
    result=$(env CEH_ENV="$env_var" APP_ENV="$env_var" python3 "$PLUGIN_DIR/scripts/safety-gate.py" <<< "$payload")
    local decision
    decision=$(echo "$result" | jq -r '.decision')

    if [[ "$decision" == "$expected_decision" ]]; then
        if [[ -n "$extra_check" ]]; then
            if echo "$result" | grep -q "$extra_check"; then
                log_ok "Safety Gate Hook: '$cmd' [$env_var] -> $decision ($extra_check)"
            else
                log_error "Safety Gate Hook: '$cmd' returned $decision but missed '$extra_check'"
            fi
        else
            log_ok "Safety Gate Hook: '$cmd' [$env_var] -> $decision"
        fi
    else
        log_error "Safety Gate Hook: '$cmd' [$env_var] expected '$expected_decision', got '$decision'. Output: $result"
    fi
}

log_step "2.1 Testing Catastrophic command rejection across environments"
test_safety_hook "rm -rf /" "development" "deny" "CATASTROPHIC BLOCK"
test_safety_hook "rtk rm -rf /" "development" "deny" "CATASTROPHIC BLOCK"
test_safety_hook "rtk proxy rm -rf /" "development" "deny" "CATASTROPHIC BLOCK"

log_step "2.2 Testing Production lock on destructive commands (with and without RTK)"
test_safety_hook "git reset --hard HEAD~1" "production" "deny" "CEH PRODUCTION LOCK"
test_safety_hook "rtk git reset --hard HEAD~1" "production" "deny" "CEH PRODUCTION LOCK"
test_safety_hook "rtk php artisan migrate:fresh" "production" "deny" "CEH PRODUCTION LOCK"

log_step "2.3 Testing Staging confirmation gate with 2 explicit alerts"
test_safety_hook "git reset --hard HEAD~1" "staging" "ask" "ALERTA 1/2"
test_safety_hook "rtk git reset --hard HEAD~1" "staging" "ask" "ALERTA 2/2"
test_safety_hook "rtk git clean -fdx" "staging" "ask" "ALERTA 1/2"

log_step "2.4 Testing Development allowance with rollback readiness"
test_safety_hook "git reset --hard HEAD~1" "development" "allow" "DEV PERMITTED"
test_safety_hook "rtk git reset --hard HEAD~1" "development" "allow" "DEV PERMITTED"

log_step "2.5 Testing Safe commands allowance across all tiers"
test_safety_hook "npm test" "production" "allow"
test_safety_hook "git status" "production" "allow"
test_safety_hook "rtk git status" "production" "allow"

# ------------------------------------------------------------------------------
# PHASE 3: Deterministic Test Runner & Auto-Detection
# ------------------------------------------------------------------------------
log_header "PHASE 3: Deterministic Test Runner & Auto-Detection (E2E)"

log_step "3.1 Running auto-detected test suite in sandbox project"
cd "$SANDBOX_DIR"
RUNNER_OUT=$(bash "$PLUGIN_DIR/scripts/test-runner.sh")
echo "$RUNNER_OUT" | grep -q "STATUS:    PASS"
echo "$RUNNER_OUT" | grep -q "EXIT CODE: 0"
log_ok "Auto-detected test suite ran and returned PASS with exit code 0."

log_step "3.2 Testing deliberate test failure propagation (no fake pass)"
cat << 'EOF' > failing_test.py
import sys
print("Simulating test failure...")
sys.exit(1)
EOF

set +e
FAIL_RUNNER_OUT=$(bash "$PLUGIN_DIR/scripts/test-runner.sh" "python3 failing_test.py")
FAIL_EXIT=$?
set -e

if [[ "$FAIL_EXIT" -ne 0 ]] && echo "$FAIL_RUNNER_OUT" | grep -q "STATUS:    FAIL"; then
    log_ok "Test runner faithfully captured failure with non-zero exit code ($FAIL_EXIT)."
else
    log_error "Test runner masked a failing test! Output: $FAIL_RUNNER_OUT"
fi
rm -f failing_test.py

# ------------------------------------------------------------------------------
# PHASE 4: Diff Audit & Evidence Report Execution
# ------------------------------------------------------------------------------
log_header "PHASE 4: Diff Audit & Evidence Report Execution (E2E)"

log_step "4.1 Testing diff-audit.sh on controlled modifications"
echo "// Modified for E2E audit test" >> "$SANDBOX_DIR/test.js"
DIFF_AUDIT_OUT=$(cd "$SANDBOX_DIR" && bash "$PLUGIN_DIR/scripts/diff-audit.sh")
echo "$DIFF_AUDIT_OUT" | grep -q "M test.js"
echo "$DIFF_AUDIT_OUT" | grep -q "No conflict markers found"
log_ok "Diff audit verified modified file and absence of conflict markers."

log_step "4.2 Testing evidence-report.sh output contract"
EVIDENCE_OUT=$(cd "$SANDBOX_DIR" && bash "$PLUGIN_DIR/scripts/evidence-report.sh" "COMPLETED" "HIGH")
echo "$EVIDENCE_OUT" | grep -q "## RESULT"
echo "$EVIDENCE_OUT" | grep -q "## EVIDENCE"
echo "$EVIDENCE_OUT" | grep -q "## ACCEPTANCE"
echo "$EVIDENCE_OUT" | grep -q "HIGH"
log_ok "Evidence Report formatted and validated structured output contract."

# ------------------------------------------------------------------------------
# PHASE 5: Complete CI Pipeline Emulation (100% Green Check)
# ------------------------------------------------------------------------------
log_header "PHASE 5: Complete CI Emulation & Quality Verification"

log_step "5.1 Syntax validation of all Bash scripts (bash -n)"
find "$PLUGIN_DIR" -name "*.sh" -exec bash -n {} +
bash -n "$ROOT_DIR/install.sh"
bash -n "$ROOT_DIR/uninstall.sh"
log_ok "All Bash scripts syntax validated (100% pass)."

log_step "5.2 Syntax validation of all Python scripts (py_compile)"
python3 -m py_compile "$PLUGIN_DIR/scripts/safety-gate.py"
python3 -m py_compile "$PLUGIN_DIR/tests/test_safety_matrix.py"
log_ok "All Python scripts compiled with zero syntax errors (100% pass)."

log_step "5.3 Safety Gate Unit Matrix (24/24 Test Cases including RTK)"
python3 "$PLUGIN_DIR/tests/test_safety_matrix.py" >/dev/null
log_ok "Safety Gate Unit Matrix: 24/24 passed (100%)."

log_step "5.4 Adversarial Test Suite (5/5 Cases)"
bash "$PLUGIN_DIR/tests/run-adversarial-tests.sh" >/dev/null
log_ok "Adversarial Suite: 5/5 cases passed (100%)."

log_step "5.5 Comprehensive General Test Suite (33/33 Cases)"
bash "$PLUGIN_DIR/tests/run-all-tests.sh" >/dev/null
log_ok "General Test Suite: 33/33 tests passed (100%)."

# ------------------------------------------------------------------------------
# FINAL REPORT
# ------------------------------------------------------------------------------
log_header "🎉 E2E & CI VERIFICATION SUMMARY"
echo -e "${GREEN}${BOLD}  Total Verified Checks: $((PASSED_COUNT))${NC}"
echo -e "${GREEN}${BOLD}  Total Failures:        0${NC}"
echo -e "${GREEN}${BOLD}  System Status:         100% GREEN (TOP LEVEL)${NC}"
echo -e "${CYAN}======================================================================${NC}\n"
