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
        python3 -c "
import sys, re

rc_path = sys.argv[1]
start_m = '# BEGIN CLEARER ENGINEERING HARNESS (CEH) ALIASES'
end_m = '# END CLEARER ENGINEERING HARNESS (CEH) ALIASES'

try:
    with open(rc_path, 'r', encoding='utf-8') as f:
        content = f.read()
except Exception:
    sys.exit(0)

# 1. Remove delimited CEH block
pattern = re.compile(rf'{re.escape(start_m)}.*?{re.escape(end_m)}\n?', re.DOTALL)
content = pattern.sub('', content)

# 2. Remove legacy header and all known CEH aliases (including orphans)
content = re.sub(r'# === CLEARER Engineering Harness \(CEH\) ===\n?', '', content)
for a in ['agy-ceh', 'agy-ceh-yolo', 'ceh', 'ceh-env', 'ceh-branches', 'ceh-preflight', 'ceh-evals', 'ceh-monitor', 'ceh-doc-audit', 'ceh-help']:
    content = re.sub(rf'alias {a}=.*?\n', '', content)

# 3. Normalize whitespace
content = re.sub(r'\n{3,}', '\n\n', content)

with open(rc_path, 'w', encoding='utf-8') as f:
    f.write(content)
" "$rc_file" 2>/dev/null || true
    fi
done

echo -e "${GREEN}${BOLD}✔ CLEARER Engineering Harness uninstalled successfully.${NC}"
