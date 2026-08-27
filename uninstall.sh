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

# 2. Remove configuration directories
echo -e "${BLUE}[INFO]${NC} Removing files from ~/.gemini/config/..."
rm -rf "$HOME/.gemini/config/plugins/clearer-engineering"
rm -rf "$HOME/.gemini/config/agents/clearer-harness"

# 3. Clean up aliases from rc files
echo -e "${BLUE}[INFO]${NC} Cleaning up shell aliases..."
for rc_file in "$HOME/.bashrc" "$HOME/.zshrc"; do
    if [[ -f "$rc_file" ]]; then
        sed -i '/# === CLEARER Engineering Harness (CEH) ===/,+3d' "$rc_file" 2>/dev/null || true
        sed -i '/alias agy-ceh=/d' "$rc_file" 2>/dev/null || true
        sed -i '/alias agy-ceh-yolo=/d' "$rc_file" 2>/dev/null || true
        sed -i '/alias ceh=/d' "$rc_file" 2>/dev/null || true
    fi
done

echo -e "${GREEN}${BOLD}✔ CLEARER Engineering Harness uninstalled successfully.${NC}"
