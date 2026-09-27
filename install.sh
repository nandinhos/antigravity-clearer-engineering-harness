#!/usr/bin/env bash
# ==============================================================================
# 🛡️ CLEARER Engineering Harness (CEH) - Global Universal Installer
# ==============================================================================
# Supports local execution (./install.sh) or one-line curl installation:
# curl -fsSL https://raw.githubusercontent.com/nandinhos/antigravity-clearer-engineering-harness/main/install.sh | bash
# ==============================================================================
set -euo pipefail

# Visual Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'

print_banner() {
    echo -e "${CYAN}${BOLD}"
    cat << "EOF"
  ╔═══════════════════════════════════════════════════════════════════╗
  ║    🛡️  CLEARER Engineering Harness (CEH) — Global Installer       ║
  ║         Evidence-Driven Engineering for Google Antigravity        ║
  ╚═══════════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✔ SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 1. Environment & Prerequisites Check
check_prerequisites() {
    log_info "Verifying system prerequisites..."
    local missing=0

    for cmd in git python3 bash; do
        if ! command -v "$cmd" >/dev/null 2>&1; then
            log_error "Missing required command: $cmd"
            missing=1
        fi
    done

    if command -v python3 >/dev/null 2>&1; then
        if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' >/dev/null 2>&1; then
            log_error "Python 3.9+ is required. Found: $(python3 -V 2>&1)"
            missing=1
        fi
    fi

    if ! command -v agy >/dev/null 2>&1; then
        log_warn "'agy' (Antigravity CLI) was not found in PATH."
        log_warn "If Antigravity is installed in a non-standard location, ensure ~/.local/bin is in your PATH."
    fi

    # Token economy advisory (RTK)
    if command -v rtk >/dev/null 2>&1; then
        log_success "'rtk' (Rust Token Killer) detected. Shell token economy active."
    else
        log_info "Optional: 'rtk' not found in PATH. Install RTK (https://github.com/rtk-ai/rtk) for 60-90% shell token savings."
    fi

    if [[ "$missing" -eq 1 ]]; then
        log_error "Please install missing dependencies before proceeding."
        exit 1
    fi
    log_success "Prerequisites verified."
}

# 2. Locate or Fetch Source Assets
setup_source_directory() {
    INSTALL_TMP_DIR=""
    # Check if run locally within cloned repo
    if [[ -d "$(dirname "$0")/clearer-engineering" && -f "$(dirname "$0")/clearer-engineering/plugin.json" ]]; then
        SOURCE_DIR="$(cd "$(dirname "$0")" && pwd)"
        log_info "Using local source directory: $SOURCE_DIR"
    else
        log_info "Fetching latest CEH release from GitHub..."
        INSTALL_TMP_DIR=$(mktemp -d -t ceh-install-XXXXXX)
        git clone --depth 1 https://github.com/nandinhos/antigravity-clearer-engineering-harness.git "$INSTALL_TMP_DIR" -q
        SOURCE_DIR="$INSTALL_TMP_DIR"
        log_success "Repository cloned to temporary directory."
    fi
}

cleanup() {
    if [[ -n "${INSTALL_TMP_DIR:-}" && -d "$INSTALL_TMP_DIR" ]]; then
        rm -rf "$INSTALL_TMP_DIR"
    fi
}
trap cleanup EXIT

# 3. Deploy Customizations to ~/.gemini/config
deploy_harness() {
    log_info "Deploying CLEARER Harness to Antigravity global configurations..."

    local GEMINI_CONFIG_DIR="$HOME/.gemini/config"
    local TARGET_PLUGIN_DIR="$GEMINI_CONFIG_DIR/plugins/clearer-engineering"
    local TARGET_AGENT_DIR="$GEMINI_CONFIG_DIR/agents/clearer-harness"

    mkdir -p "$GEMINI_CONFIG_DIR/plugins"
    mkdir -p "$GEMINI_CONFIG_DIR/agents"
    mkdir -p "$TARGET_AGENT_DIR"

    # Copy Plugin Assets
    rm -rf "$TARGET_PLUGIN_DIR"
    mkdir -p "$TARGET_PLUGIN_DIR"
    cp -r "$SOURCE_DIR/clearer-engineering/." "$TARGET_PLUGIN_DIR/"
    if [[ -d "$SOURCE_DIR/evals" ]]; then
        cp -r "$SOURCE_DIR/evals" "$TARGET_PLUGIN_DIR/"
        chmod +x "$TARGET_PLUGIN_DIR/evals"/* 2>/dev/null || true
    fi
    chmod +x "$TARGET_PLUGIN_DIR/scripts"/*
    chmod +x "$TARGET_PLUGIN_DIR/tests"/*


    # Copy Agent Profile
    cat << "AGENT_EOF" > "$TARGET_AGENT_DIR/agent.md"
---
name: clearer-harness
description: >-
  CLEARER Engineering Harness (CEH) Orchestrator para Google Antigravity. Conduz o ciclo de
  engenharia orientado a evidências com Risk Dial (LOW, MEDIUM, HIGH), semântica OBSERVED/INFERRED/UNKNOWN,
  revisão adversarial de diffs e auditoria estrita de claims.
tools:
  - run_command
  - write_to_file
  - replace_file_content
  - multi_replace_file_content
  - view_file
  - list_dir
  - grep_search
  - find_by_name
  - search_web
  - read_url_content
  - manage_task
  - schedule
  - generate_image
  - ask_question
  - invoke_subagent
  - define_subagent
  - manage_subagents
  - send_message
---

# CLEARER Engineering Harness (Antigravity Profile)

Você é o perfil oficial **CLEARER Engineering Harness (`clearer-harness`)** para o **Google Antigravity**.
Seu papel é atuar como **Engineering Orchestrator** orientado por evidências, garantindo precisão, blast radius mínimo, testes determinísticos e auditoria rigorosa de claims.

---

## 1. O Protocolo CLEARER
- **C — Concrete Goal**: Objetivo concreto, arquivos envolvidos, restrições e condição de parada.
- **L — Load Context**: *Inspect before edit*. Descobrir a stack, entrypoints e testes antes de editar.
- **E — Explicit Boundaries**: Delimitar escopo rígido e blast radius mínimo.
- **A — Anchors and Examples**: Código real, schemas e testes como única fonte da verdade.
- **R — Response Contract**: Toda entrega gera um contrato verificável de saída.
- **E — Enable Evidence and Tools**: Observação direta sobre suposição.
- **R — Review and Validate**: Seguir o ciclo `INSPECT → PLAN → IMPLEMENT → TEST → REVIEW → AUDIT → REPORT`.

## 2. Risk Dial & Automação de Execução
- **LOW**: Baixa sobrecarga, execução ágil.
- **MEDIUM**: Execução Contínua em Turno Único (Inspeção → Plano → Implementação → Testes → Diff Audit → Response Contract).
- **HIGH**: Investigação profunda, subagentes especializados, revisão adversarial, auditoria formal e aprovação humana.


## 3. Subagentes Especializados
1. `ceh-investigator`: Exploração read-only e Evidence Pack.
2. `ceh-architect`: Análise de blast radius e Implementation Plan.
3. `ceh-implementer`: Edição precisa e cirúrgica do código.
4. `ceh-test-engineer`: Execução de testes determinísticos e evidência não-mascarada.
5. `ceh-reviewer`: Revisão adversarial do Git diff.
6. `ceh-evidence-auditor`: Confronto final `CLAIM ↔ EVIDENCE`.

## 4. Skills Integradas
`/clearer`, `/clearer-feature`, `/clearer-bugfix`, `/clearer-refactor`, `/clearer-review`, `/clearer-audit`, `/clearer-map`, `/clearer-test`, `/clearer-adhd`, `/conselho-seniores`.
AGENT_EOF

    log_success "Assets installed to $GEMINI_CONFIG_DIR"

    # Register and validate via agy CLI if available
    if command -v agy >/dev/null 2>&1; then
        log_info "Validating plugin with Antigravity CLI..."
        local validate_output
        local validate_status=0
        validate_output=$(agy plugin validate "$TARGET_PLUGIN_DIR" 2>&1) || validate_status=$?
        echo "$validate_output"
        if [[ $validate_status -eq 0 ]]; then
            log_success "Plugin validated and active in Antigravity."
        else
            log_error "Plugin validation failed with exit code $validate_status."
            if [[ "${SKIP_DIAGNOSTICS:-0}" -eq 1 ]]; then
                log_warn "Proceeding despite validation failure because --skip-diagnostics is active."
            else
                log_error "Aborting installation due to plugin validation failure. (Pass --skip-diagnostics to bypass)."
                exit "$validate_status"
            fi
        fi
    fi
}


# 4. Configure Shell Aliases Idempotently
configure_shell_aliases() {
    log_info "Configuring shell aliases from config/aliases.sh..."

    local SCRIPT_DIR
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local ALIAS_CONF="$HOME/.gemini/config/plugins/clearer-engineering/config/aliases.sh"
    if [[ ! -f "$ALIAS_CONF" ]]; then
        ALIAS_CONF="${SOURCE_DIR:-$SCRIPT_DIR}/clearer-engineering/config/aliases.sh"
    fi

    if [[ ! -f "$ALIAS_CONF" ]]; then
        log_error "Aliases configuration not found at $ALIAS_CONF"
        exit 1
    fi

    local ALIAS_BODY
    ALIAS_BODY=$(grep '^alias ' "$ALIAS_CONF")

    for rc_file in "$HOME/.bashrc" "$HOME/.zshrc"; do
        if [[ -f "$rc_file" ]]; then
            python3 -c "
import sys, re

rc_path = sys.argv[1]
aliases_body = sys.argv[2].strip()
start_m = '# BEGIN CLEARER ENGINEERING HARNESS (CEH) ALIASES'
end_m = '# END CLEARER ENGINEERING HARNESS (CEH) ALIASES'

try:
    with open(rc_path, 'r', encoding='utf-8') as f:
        content = f.read()
except Exception:
    sys.exit(0)

# Remove legacy comment if present
content = re.sub(r'# === CLEARER Engineering Harness \(CEH\) ===\n?', '', content)

if content.endswith('\n\n'):
    prefix = ''
elif content.endswith('\n'):
    prefix = '\n'
elif len(content) == 0:
    prefix = ''
else:
    prefix = '\n\n'

prefix_len = len(prefix)
block = f'{start_m}\n# CEH_RC_PREFIX_LEN: {prefix_len}\n{aliases_body}\n{end_m}\n'

pattern = re.compile(rf'{re.escape(start_m)}.*?{re.escape(end_m)}\n?', re.DOTALL)
m = pattern.search(content)
if m:
    pm = re.search(r'# CEH_RC_PREFIX_LEN: (\d+)', m.group(0))
    p_len = int(pm.group(1)) if pm else 0
    block = f'{start_m}\n# CEH_RC_PREFIX_LEN: {p_len}\n{aliases_body}\n{end_m}\n'
    updated = pattern.sub(block, content)
else:
    # Remove orphan aliases if any, anchored strictly at line start
    exact_ceh_lines = {l.strip() for l in aliases_body.splitlines() if l.strip().startswith('alias ')}
    known_names = set()
    for l in aliases_body.splitlines():
        am = re.match(r'alias\s+([a-zA-Z0-9_-]+)=', l.strip())
        if am:
            known_names.add(am.group(1))

    lines = content.splitlines(keepends=True)
    filtered = []
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
            filtered.append(line)
    content = ''.join(filtered)
    updated = content + prefix + block

with open(rc_path, 'w', encoding='utf-8') as f:
    f.write(updated)
" "$rc_file" "$ALIAS_BODY"
            log_success "Aliases configured in $rc_file"
        fi
    done
}

# 5. Run Post-Installation Self-Diagnostics
run_self_diagnostics() {
    log_info "Running post-installation self-diagnostics from installed harness..."
    local TARGET_PLUGIN_DIR="$HOME/.gemini/config/plugins/clearer-engineering"
    local GATE_SCRIPT="$TARGET_PLUGIN_DIR/scripts/safety-gate.py"

    if [[ ! -f "$GATE_SCRIPT" ]]; then
        log_error "Installed safety-gate.py not found at $GATE_SCRIPT"
        if [[ "${SKIP_DIAGNOSTICS:-0}" -eq 1 ]]; then
            log_warn "Proceeding because --skip-diagnostics is active."
            return 0
        else
            exit 1
        fi
    fi

    # 1. Test catastrophic deny
    log_info "Diagnosing safety-gate: catastrophic command check (rm -rf /)..."
    local out1
    out1=$(python3 "$GATE_SCRIPT" --check "rm -rf /" 2>&1 || true)
    if ! echo "$out1" | grep -qi "deny" || ! echo "$out1" | grep -qi "CATASTROPHIC"; then
        log_error "Self-diagnostic failed: 'rm -rf /' did not trigger deny/CATASTROPHIC. Output: $out1"
        if [[ "${SKIP_DIAGNOSTICS:-0}" -eq 1 ]]; then
            log_warn "Proceeding because --skip-diagnostics is active."
        else
            exit 1
        fi
    fi

    # 2. Test benign allow
    log_info "Diagnosing safety-gate: benign command check (ls)..."
    local out2
    out2=$(python3 "$GATE_SCRIPT" --check "ls" 2>&1 || true)
    if ! echo "$out2" | grep -qi "allow"; then
        log_error "Self-diagnostic failed: 'ls' did not evaluate to allow. Output: $out2"
        if [[ "${SKIP_DIAGNOSTICS:-0}" -eq 1 ]]; then
            log_warn "Proceeding because --skip-diagnostics is active."
        else
            exit 1
        fi
    fi

    # 3. Test hook fail-closed on empty stdin (PR-09: exit code 2)
    log_info "Diagnosing hook fail-closed: empty payload handling..."
    local hook_exit=0
    echo "" | python3 "$GATE_SCRIPT" >/dev/null 2>&1 || hook_exit=$?
    if [[ "$hook_exit" -ne 2 ]]; then
        log_error "Self-diagnostic failed: empty stdin did not return exit code 2 (got $hook_exit)"
        if [[ "${SKIP_DIAGNOSTICS:-0}" -eq 1 ]]; then
            log_warn "Proceeding because --skip-diagnostics is active."
        else
            exit 1
        fi
    fi

    log_success "Post-installation self-diagnostics passed (3/3 checks verified)."
}

# Main Execution Flow
main() {
    local skip_diag=0
    for arg in "$@"; do
        if [[ "$arg" == "--skip-diagnostics" ]]; then
            skip_diag=1
        fi
    done
    export SKIP_DIAGNOSTICS="$skip_diag"
    if [[ "$SKIP_DIAGNOSTICS" -eq 1 ]]; then
        log_info "Flag --skip-diagnostics detected: strict validation and diagnostics will not abort on failure."
    fi

    print_banner
    check_prerequisites
    setup_source_directory
    deploy_harness
    configure_shell_aliases
    run_self_diagnostics

    echo ""
    echo -e "${GREEN}${BOLD}=====================================================================${NC}"
    echo -e "${GREEN}${BOLD}  🎉 CLEARER Engineering Harness installed successfully!${NC}"
    echo -e "${GREEN}${BOLD}=====================================================================${NC}"
    echo ""
    echo -e "  To start using the harness immediately, reload your shell or run:"
    echo -e "  ${CYAN}${BOLD}source ~/.bashrc${NC} (or ${CYAN}${BOLD}source ~/.zshrc${NC})"
    echo ""
    echo -e "  Available commands:"
    echo -e "  - ${BOLD}ceh / agy-ceh${NC}     : Launch Antigravity with CLEARER Harness profile"
    echo -e "  - ${BOLD}agy-ceh-yolo${NC}      : Launch with auto-approved safe edits"
    echo -e "  - ${BOLD}ceh-env${NC}           : Detect active environment (DEV/STAGING/PROD) & branch"
    echo -e "  - ${BOLD}ceh-branches${NC}      : Audit & configure branch topology (Enterprise/Classic)"
    echo -e "  - ${BOLD}ceh-preflight${NC}     : Run full project engineering readiness check"
    echo -e "  - ${BOLD}ceh-evals${NC}         : Run deterministic falsifiability smoke-eval (5/5 PASS)"
    echo -e "  - ${BOLD}ceh-monitor${NC}       : Real-time background tasks & test monitor (25s cadence)"
    echo -e "  - ${BOLD}ceh-help${NC}          : Interactive quick guide & command cheat sheet"
    echo ""
    echo -e "  Documentation & Guides: ${BLUE}https://github.com/nandinhos/antigravity-clearer-engineering-harness${NC}"
    echo ""
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
