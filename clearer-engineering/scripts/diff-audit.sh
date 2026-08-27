#!/usr/bin/env bash
# ==============================================================================
# diff-audit.sh - Diff & Blast Radius Auditor for CLEARER Harness
# ==============================================================================
set -euo pipefail

echo "=== [CEH Diff & Blast Radius Audit] ==="
echo "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo ""

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "ERROR: Not a git repository. Cannot perform diff audit."
    exit 1
fi

BRANCH=$(git branch --show-current 2>/dev/null || echo "detached")
echo "Branch: $BRANCH"
echo ""

# Check for uncommitted changes
CHANGED_FILES=$(git status --porcelain | awk '{print $2}')
if [[ -z "$CHANGED_FILES" ]]; then
    echo "Status: CLEAN (No working tree modifications found)."
    exit 0
fi

echo "--- 1. Modified & Untracked Files ---"
git status --short
echo ""

echo "--- 2. Diff Statistics ---"
git diff --stat HEAD 2>/dev/null || git diff --stat
echo ""

echo "--- 3. Whitespace & Conflict Markers Check ---"
CONFLICT_MARKERS=$(git diff | grep -E '^\+?(<<<<<<<|=======|>>>>>>>)' || true)
if [[ -n "$CONFLICT_MARKERS" ]]; then
    echo "🚨 WARNING: Merge conflict markers detected in diff!"
    echo "$CONFLICT_MARKERS"
else
    echo "✔ No conflict markers found."
fi

# Secret / sensitive token scanning
echo ""
echo "--- 4. Secret & Token Heuristics Scan ---"
SUSPICIOUS_TOKENS=$(git diff | grep -E -i '(\b(bearer\s+[a-zA-Z0-9_\-\.]{20,}|api[_-]?key\s*[:=]\s*["\x27][a-zA-Z0-9_\-]{16,}["\x27]|ghp_[a-zA-Z0-9]{36}|AIza[0-9A-Za-z\-_]{35}|-----BEGIN\s+PRIVATE\s+KEY-----))' || true)

if [[ -n "$SUSPICIOUS_TOKENS" ]]; then
    echo "🚨 ALERT: Suspicious credential / secret patterns detected in diff!"
    echo "$SUSPICIOUS_TOKENS"
else
    echo "✔ No raw secrets or private key tokens detected in diff."
fi

echo ""
echo "=== Diff Audit Completed ==="
