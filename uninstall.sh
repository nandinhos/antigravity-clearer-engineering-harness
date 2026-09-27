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
except Exception as e:
    sys.stderr.write(f'Erro ao ler {rc_path}: {e}\n')
    sys.exit(1)

# 1. AN1: Remove delimited CEH block without removing non-newline characters
pattern = re.compile(rf'{re.escape(start_m)}.*?{re.escape(end_m)}\n?', re.DOTALL)
m = pattern.search(content)
if m:
    pm = re.search(r'# CEH_RC_PREFIX_LEN: (\d+)', m.group(0))
    prefix_len = int(pm.group(1)) if pm else 0
    start_idx = m.start()
    end_idx = m.end()

    # Conta quebras de linha consecutivas imediatamente anteriores a start_idx
    newlines_before = 0
    pos = start_idx - 1
    while pos >= 0 and content[pos] == '\n':
        newlines_before += 1
        pos -= 1

    to_remove_newlines = min(newlines_before, prefix_len)
    remove_start = start_idx - to_remove_newlines
    content = content[:remove_start] + content[end_idx:]

# 2. Remove legacy header
content = re.sub(r'# === CLEARER Engineering Harness \(CEH\) ===\n?', '', content)

# 3. AN2: Remove orphan CEH aliases anchored at line start and only with CEH signatures
exact_ceh_lines = set()
known_names = {
    'agy-ceh', 'agy-ceh-yolo', 'ceh', 'ceh-env', 'ceh-branches',
    'ceh-preflight', 'ceh-evals', 'ceh-monitor', 'ceh-doc-audit',
    'ceh-conselho', 'ceh-help'
}

if alias_conf_path:
    try:
        with open(alias_conf_path, 'r', encoding='utf-8') as af:
            for line in af:
                line_str = line.strip()
                if line_str.startswith('alias '):
                    exact_ceh_lines.add(line_str)
                    am = re.match(r'alias\s+([a-zA-Z0-9_-]+)=', line_str)
                    if am:
                        known_names.add(am.group(1))
    except Exception as e:
        sys.stderr.write(f'Erro ao ler alias_conf {alias_conf_path}: {e}\n')
        sys.exit(1)

lines = content.splitlines(keepends=True)
filtered_lines = []
for line in lines:
    stripped = line.strip()
    is_ceh_orphan = False
    m_alias = re.match(r'^alias\s+([a-zA-Z0-9_-]+)=(.*)$', line)
    if m_alias:
        name = m_alias.group(1)
        val = m_alias.group(2)
        if name in known_names:
            if stripped in exact_ceh_lines or '--agent clearer-harness' in val or 'plugins/clearer-engineering/' in val or re.search(r'(detect|setup-branches|preflight|evals|monitor|task-monitor|doc-audit|conselho-seniores|ceh-help|help)\.sh', val) is not None:
                is_ceh_orphan = True
    if not is_ceh_orphan:
        filtered_lines.append(line)

content = ''.join(filtered_lines)

try:
    with open(rc_path, 'w', encoding='utf-8') as f:
        f.write(content)
except Exception as e:
    sys.stderr.write(f'Erro ao escrever {rc_path}: {e}\n')
    sys.exit(1)
" "$rc_file" "$ALIAS_CONF"
    fi
done

# 3. Remove configuration directories
echo -e "${BLUE}[INFO]${NC} Removing files from ~/.gemini/config/..."
rm -rf "$HOME/.gemini/config/plugins/clearer-engineering"
rm -rf "$HOME/.gemini/config/agents/clearer-harness"

echo -e "${GREEN}${BOLD}✔ CLEARER Engineering Harness uninstalled successfully.${NC}"
