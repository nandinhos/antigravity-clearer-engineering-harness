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

    if [[ -n "${BASH_VERSINFO[0]:-}" && "${BASH_VERSINFO[0]}" -lt 4 ]]; then
        log_error "Bash 4.0+ is required. Detected: Bash ${BASH_VERSION}."
        if [[ "$(uname -s)" == "Darwin" ]]; then
            log_error "macOS includes outdated Bash 3.2 by default. Install modern Bash via Homebrew: 'brew install bash' and ensure it takes precedence in your PATH."
        fi
        missing=1
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
    local local_candidate=""

    if [[ ${#BASH_SOURCE[@]} -gt 0 && -n "${BASH_SOURCE[0]:-}" && -f "${BASH_SOURCE[0]}" ]]; then
        local script_dir
        script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
        if [[ -d "$script_dir/clearer-engineering" && -f "$script_dir/clearer-engineering/plugin.json" ]]; then
            local_candidate="$script_dir"
        fi
    fi

    if [[ -n "$local_candidate" ]]; then
        if [[ -n "${CEH_VERSION:-}" ]]; then
            log_warn "CEH_VERSION='${CEH_VERSION}' foi informada, mas o script está rodando diretamente de um arquivo local ($local_candidate). A versão fixada será ignorada em favor da árvore local."
        fi
        SOURCE_DIR="$local_candidate"
        log_info "Using local source directory: $SOURCE_DIR"
    else
        INSTALL_TMP_DIR=$(mktemp -d "${TMPDIR:-/tmp}/ceh-install-XXXXXX")
        local repo_url="${CEH_REPO_URL:-https://github.com/nandinhos/antigravity-clearer-engineering-harness.git}"
        if [[ -n "${CEH_VERSION:-}" ]]; then
            local TARGET_REF="v${CEH_VERSION#v}"
            log_info "Fetching CEH version $TARGET_REF from GitHub..."
            git clone --depth 1 --branch "$TARGET_REF" "$repo_url" "$INSTALL_TMP_DIR" -q
        else
            log_info "Fetching latest CEH release from GitHub..."
            git clone --depth 1 "$repo_url" "$INSTALL_TMP_DIR" -q
        fi
        SOURCE_DIR="$INSTALL_TMP_DIR"
        log_success "Repository cloned to temporary directory."
    fi
}

# shellcheck disable=SC2317,SC2329 # Invocado indiretamente via trap cleanup EXIT
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

    # 3.1 Generate fresh Antigravity package on the fly (PR-16)
    local PKG_TMP_DIR
    PKG_TMP_DIR=$(mktemp -d "${TMPDIR:-/tmp}/ceh-pkg-antigravity-XXXXXX")
    local PACKAGE_PY="$SOURCE_DIR/clearer-engineering/tools/package.py"
    if [[ ! -f "$PACKAGE_PY" ]]; then
        log_error "Packager tool not found at $PACKAGE_PY"
        exit 1
    fi
    python3 "$PACKAGE_PY" --host antigravity --out "$PKG_TMP_DIR"

    # 3.2 Staging & Transactional Deployment (F13)
    local STAGING_DIR
    STAGING_DIR=$(mktemp -d "${TMPDIR:-/tmp}/ceh-staging-XXXXXX")
    cp -r "$PKG_TMP_DIR/." "$STAGING_DIR/"
    rm -f "$STAGING_DIR/.ceh-package-managed"
    rm -rf "$PKG_TMP_DIR"

    if [[ -d "$SOURCE_DIR/evals" ]]; then
        cp -r "$SOURCE_DIR/evals" "$STAGING_DIR/"
        chmod +x "$STAGING_DIR/evals"/* 2>/dev/null || true
    fi
    chmod +x "$STAGING_DIR/scripts"/*
    chmod +x "$STAGING_DIR/tests"/*

    # Backup existing installation if present
    local BACKUP_DIR=""
    if [[ -d "$TARGET_PLUGIN_DIR" ]]; then
        BACKUP_DIR=$(mktemp -d "${TMPDIR:-/tmp}/ceh-backup-plugin-XXXXXX")
        cp -r "$TARGET_PLUGIN_DIR/." "$BACKUP_DIR/"
    fi

    # Validate staging plugin via agy CLI if available before committing to active dir
    if command -v agy >/dev/null 2>&1; then
        log_info "Validating staging plugin with Antigravity CLI..."
        local validate_output
        local validate_status=0
        validate_output=$(agy plugin validate "$STAGING_DIR" 2>&1) || validate_status=$?
        echo "$validate_output"
        if [[ $validate_status -ne 0 && "${SKIP_DIAGNOSTICS:-0}" -ne 1 ]]; then
            log_error "Plugin validation failed on staging (exit $validate_status). Aborting without modifying active install."
            rm -rf "$STAGING_DIR"
            [[ -n "$BACKUP_DIR" ]] && rm -rf "$BACKUP_DIR"
            exit "$validate_status"
        fi
    fi

    # Commit deployment atomically
    rm -rf "$TARGET_PLUGIN_DIR"
    mkdir -p "$TARGET_PLUGIN_DIR"
    cp -r "$STAGING_DIR/." "$TARGET_PLUGIN_DIR/"
    rm -rf "$STAGING_DIR"
    [[ -n "$BACKUP_DIR" ]] && rm -rf "$BACKUP_DIR"

    # Copy Agent Profile from canonical source
    local AGENT_PROFILE_SRC="$SOURCE_DIR/clearer-engineering/profiles/clearer-harness.agent.md"
    if [[ -f "$AGENT_PROFILE_SRC" ]]; then
        cp "$AGENT_PROFILE_SRC" "$TARGET_AGENT_DIR/agent.md"
    else
        log_error "Agent profile source not found at $AGENT_PROFILE_SRC"
        exit 1
    fi

    log_success "Assets installed to $GEMINI_CONFIG_DIR"
}


# 4. Configure Shell Aliases Idempotently
configure_shell_aliases() {
    log_info "Configuring shell aliases from config/aliases.sh..."

    local ALIAS_CONF="$HOME/.gemini/config/plugins/clearer-engineering/config/aliases.sh"
    local RC_ALIASES_PY="$HOME/.gemini/config/plugins/clearer-engineering/scripts/rc_aliases.py"

    local script_dir=""
    if [[ ${#BASH_SOURCE[@]} -gt 0 && -n "${BASH_SOURCE[0]:-}" && -f "${BASH_SOURCE[0]}" ]]; then
        script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    fi
    local base_src="${SOURCE_DIR:-$script_dir}"

    if [[ ! -f "$ALIAS_CONF" && -n "$base_src" ]]; then
        ALIAS_CONF="$base_src/clearer-engineering/config/aliases.sh"
    fi
    if [[ ! -f "$RC_ALIASES_PY" && -n "$base_src" ]]; then
        RC_ALIASES_PY="$base_src/clearer-engineering/scripts/rc_aliases.py"
    fi

    if [[ ! -f "$ALIAS_CONF" ]]; then
        log_error "Aliases configuration not found at $ALIAS_CONF"
        exit 1
    fi
    if [[ ! -f "$RC_ALIASES_PY" ]]; then
        log_error "rc_aliases.py not found at $RC_ALIASES_PY"
        exit 1
    fi

    local ALIAS_BODY
    ALIAS_BODY=$(grep '^alias ' "$ALIAS_CONF")

    for rc_file in "$HOME/.bashrc" "$HOME/.zshrc"; do
        if [[ -f "$rc_file" ]]; then
            python3 "$RC_ALIASES_PY" install-rc "$rc_file" "$ALIAS_CONF" "$ALIAS_BODY"
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

    # 3. Test hook fail-closed on empty stdin (v1.4.1: exit 2 no Claude; exit 0 com deny no Antigravity)
    log_info "Diagnosing hook fail-closed: empty payload handling..."
    local hook_exit=0
    local hook_out
    hook_out=$(echo "" | python3 "$GATE_SCRIPT" 2>&1) || hook_exit=$?
    local hook_blocked=0
    if [[ "$hook_exit" -eq 2 ]]; then
        hook_blocked=1
    elif [[ "$hook_exit" -eq 0 ]] && echo "$hook_out" | grep -qi '"decision"[[:space:]]*:[[:space:]]*"deny"'; then
        hook_blocked=1
    fi
    if [[ "$hook_blocked" -ne 1 ]]; then
        log_error "Self-diagnostic failed: empty stdin was not blocked (exit $hook_exit, output: $hook_out)"
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

if [[ ${#BASH_SOURCE[@]} -eq 0 || "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
