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

# 2. Clean up aliases from rc files (using canonical aliases.sh)
echo -e "${BLUE}[INFO]${NC} Cleaning up shell aliases..."
ALIAS_CONF="$HOME/.gemini/config/plugins/clearer-engineering/config/aliases.sh"
if [[ ! -f "$ALIAS_CONF" ]]; then
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    if [[ -f "$SCRIPT_DIR/clearer-engineering/config/aliases.sh" ]]; then
        ALIAS_CONF="$SCRIPT_DIR/clearer-engineering/config/aliases.sh"
    else
        ALIAS_CONF=""
    fi
fi

for rc_file in "$HOME/.bashrc" "$HOME/.zshrc"; do
    if [[ -f "$rc_file" ]]; then
        python3 -c "
import sys, re

rc_path = sys.argv[1]
alias_conf_path = sys.argv[2]
start_m = '# BEGIN CLEARER ENGINEERING HARNESS (CEH) ALIASES'
end_m = '# END CLEARER ENGINEERING HARNESS (CEH) ALIASES'

try:
    with open(rc_path, 'r', encoding='utf-8') as f:
        content = f.read()
except Exception:
    sys.exit(0)

# 1. Remove delimited CEH block symmetrically
pattern = re.compile(rf'{re.escape(start_m)}.*?{re.escape(end_m)}\n?', re.DOTALL)
m = pattern.search(content)
if m:
    pm = re.search(r'# CEH_RC_PREFIX_LEN: (\d+)', m.group(0))
    prefix_len = int(pm.group(1)) if pm else 0
    start_idx = m.start()
    end_idx = m.end()
    remove_start = max(0, start_idx - prefix_len)
    content = content[:remove_start] + content[end_idx:]

# 2. Remove legacy header and all known CEH aliases (including orphans)
content = re.sub(r'# === CLEARER Engineering Harness \(CEH\) ===\n?', '', content)

known_aliases = [
    'agy-ceh', 'agy-ceh-yolo', 'ceh', 'ceh-env', 'ceh-branches',
    'ceh-preflight', 'ceh-evals', 'ceh-monitor', 'ceh-doc-audit',
    'ceh-conselho', 'ceh-help'
]

if alias_conf_path:
    try:
        with open(alias_conf_path, 'r', encoding='utf-8') as af:
            for line in af:
                am = re.match(r'alias\s+([a-zA-Z0-9_-]+)=', line.strip())
                if am:
                    known_aliases.append(am.group(1))
    except Exception:
        pass

for a in set(known_aliases):
    content = re.sub(rf'alias {re.escape(a)}=.*?\n', '', content)

with open(rc_path, 'w', encoding='utf-8') as f:
    f.write(content)
" "$rc_file" "$ALIAS_CONF" 2>/dev/null || true
    fi
done

# 3. Remove configuration directories
echo -e "${BLUE}[INFO]${NC} Removing files from ~/.gemini/config/..."
rm -rf "$HOME/.gemini/config/plugins/clearer-engineering"
rm -rf "$HOME/.gemini/config/agents/clearer-harness"

echo -e "${GREEN}${BOLD}✔ CLEARER Engineering Harness uninstalled successfully.${NC}"
