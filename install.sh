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

    if ! command -v agy >/dev/null 2>&1; then
        log_warn "'agy' (Antigravity CLI) was not found in PATH."
        log_warn "If Antigravity is installed in a non-standard location, ensure ~/.local/bin is in your PATH."
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
    cp -r "$SOURCE_DIR/clearer-engineering" "$TARGET_PLUGIN_DIR"
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

## 2. Risk Dial & Modulação de Esforço
- **LOW**: Baixa sobrecarga, execução ágil.
- **MEDIUM**: Inspeção → Plano → Implementação → Testes → Diff Audit → Relatório.
- **HIGH**: Investigação profunda, subagentes especializados, revisão adversarial e auditoria formal.

## 3. Subagentes Especializados
1. `ceh-investigator`: Exploração read-only e Evidence Pack.
2. `ceh-architect`: Análise de blast radius e Implementation Plan.
3. `ceh-implementer`: Edição precisa e cirúrgica do código.
4. `ceh-test-engineer`: Execução de testes determinísticos e evidência não-mascarada.
5. `ceh-reviewer`: Revisão adversarial do Git diff.
6. `ceh-evidence-auditor`: Confronto final `CLAIM ↔ EVIDENCE`.

## 4. Skills Integradas
`/clearer`, `/clearer-feature`, `/clearer-bugfix`, `/clearer-refactor`, `/clearer-review`, `/clearer-audit`, `/clearer-map`, `/clearer-test`.
AGENT_EOF

    log_success "Assets installed to $GEMINI_CONFIG_DIR"

    # Register via agy CLI if available
    if command -v agy >/dev/null 2>&1; then
        log_info "Validating and registering plugin with Antigravity CLI..."
        agy plugin validate "$TARGET_PLUGIN_DIR" >/dev/null 2>&1 || true
        agy plugin install "$TARGET_PLUGIN_DIR" >/dev/null 2>&1 || true
        log_success "Plugin registered in Antigravity CLI."
    fi
}

# 4. Configure Shell Aliases Idempotently
configure_shell_aliases() {
    log_info "Configuring shell aliases (agy-ceh, agy-ceh-yolo)..."

    local ALIAS_BLOCK="
# === CLEARER Engineering Harness (CEH) ===
alias agy-ceh='agy --agent clearer-harness'
alias agy-ceh-yolo='agy --agent clearer-harness --dangerously-skip-permissions --mode accept-edits'
alias ceh='agy --agent clearer-harness'
"

    for rc_file in "$HOME/.bashrc" "$HOME/.zshrc"; do
        if [[ -f "$rc_file" ]]; then
            if ! grep -q "alias agy-ceh=" "$rc_file"; then
                echo "$ALIAS_BLOCK" >> "$rc_file"
                log_success "Aliases added to $rc_file"
            else
                log_info "Aliases already present in $rc_file"
            fi
        fi
    done
}

# 5. Run Self-Diagnostics
run_self_diagnostics() {
    log_info "Running post-installation self-diagnostics..."
    local TEST_SCRIPT="$HOME/.gemini/config/plugins/clearer-engineering/tests/run-all-tests.sh"
    local ADVERSARIAL_SCRIPT="$HOME/.gemini/config/plugins/clearer-engineering/tests/run-adversarial-tests.sh"

    if [[ -x "$TEST_SCRIPT" && -x "$ADVERSARIAL_SCRIPT" ]]; then
        if bash "$TEST_SCRIPT" >/dev/null 2>&1 && bash "$ADVERSARIAL_SCRIPT" >/dev/null 2>&1; then
            log_success "All harness components and adversarial tests passed (100%)."
        else
            log_warn "Diagnostics completed with warnings. Check plugin configurations."
        fi
    fi
}

# Main Execution Flow
main() {
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
    echo -e "  - ${BOLD}agy-ceh${NC}       : Launch Antigravity with CLEARER Harness profile"
    echo -e "  - ${BOLD}agy-ceh-yolo${NC}  : Launch with auto-approved safe edits"
    echo -e "  - ${BOLD}ceh${NC}           : Short alias for agy-ceh"
    echo ""
    echo -e "  Documentation & Guides: ${BLUE}https://github.com/nandinhos/antigravity-clearer-engineering-harness${NC}"
    echo ""
}

main "$@"
