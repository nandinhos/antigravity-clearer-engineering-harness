#!/usr/bin/env bash
# ==============================================================================
# doc-audit.sh - Documentation Consistency & Normative Audit for CEH
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="$(command -v python3 || echo "python")"

exec "$PYTHON_BIN" "$SCRIPT_DIR/doc-audit.py" "$@"
