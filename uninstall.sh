#!/usr/bin/env bash
# ==============================================================================
# 🛡️ CLEARER Engineering Harness (CEH) - Uninstaller
# ==============================================================================
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${RED}${BOLD}Uninstalling CLEARER Engineering Harness (CEH)...${NC}"

# 1. Unregister from agy CLI if available
if command -v agy >/dev/null 2>&1; then
    echo -e "${BLUE}[INFO]${NC} Unregistering plugin from Antigravity CLI..."
    agy plugin uninstall clearer-engineering >/dev/null 2>&1 || true
fi

# 2. Clean up aliases from rc files (using canonical aliases.sh and rc_aliases.py)
echo -e "${BLUE}[INFO]${NC} Cleaning up shell aliases..."
ALIAS_CONF="$HOME/.gemini/config/plugins/clearer-engineering/config/aliases.sh"
RC_ALIASES_PY="$HOME/.gemini/config/plugins/clearer-engineering/scripts/rc_aliases.py"

if [[ ! -f "$ALIAS_CONF" || ! -f "$RC_ALIASES_PY" ]]; then
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    if [[ ! -f "$ALIAS_CONF" && -f "$SCRIPT_DIR/clearer-engineering/config/aliases.sh" ]]; then
        ALIAS_CONF="$SCRIPT_DIR/clearer-engineering/config/aliases.sh"
    fi
    if [[ ! -f "$RC_ALIASES_PY" && -f "$SCRIPT_DIR/clearer-engineering/scripts/rc_aliases.py" ]]; then
        RC_ALIASES_PY="$SCRIPT_DIR/clearer-engineering/scripts/rc_aliases.py"
    fi
fi

for rc_file in "$HOME/.bashrc" "$HOME/.zshrc"; do
    if [[ -f "$rc_file" ]]; then
        if [[ -f "$RC_ALIASES_PY" ]]; then
            python3 "$RC_ALIASES_PY" clean-rc "$rc_file" "$ALIAS_CONF"
        else
            echo -e "${RED}[ERROR]${NC} rc_aliases.py not found at $RC_ALIASES_PY" >&2
            exit 1
        fi
    fi
done

# 3. Remove configuration directories
echo -e "${BLUE}[INFO]${NC} Removing files from ~/.gemini/config/..."
rm -rf "$HOME/.gemini/config/plugins/clearer-engineering"
rm -rf "$HOME/.gemini/config/agents/clearer-harness"

echo -e "${GREEN}${BOLD}✔ CLEARER Engineering Harness uninstalled successfully.${NC}"
