#!/bin/sh
# ==============================================================================
# ceh-doctor.sh — Diagnóstico de Integridade, Verificação e Evidência do CEH (D3/D4)
# ==============================================================================
# Script estritamente POSIX 'sh' (compatível com /bin/bash 3.2 do macOS).
# Sem dependência de 'readlink -f' ou 'date --iso'.
# stdlib-only: calcula SHA-256 via sha256sum -> shasum -a 256 -> python3/python.
#
# LIMITES FORMAIS DE AUDITORIA (D3 / Handoff 090):
# 1. O hash prova INTEGRIDADE estrutural de arquivos, NÃO autenticidade criptográfica.
#    Quem gera o pacote pode gerar outro.
# 2. O canário de release deve ser executado pelo DESENVOLVEDOR, no seu terminal,
#    fora da sessão do agente.
# 3. Ninguém deve tratar este pacote como prova de que o agente não interferiu.
# ==============================================================================
set -e

calc_sha256() {
    _target="$1"
    if [ ! -f "$_target" ]; then
        echo "NOT_FOUND"
        return 1
    fi
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$_target" | awk '{print $1}'
    elif command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "$_target" | awk '{print $1}'
    elif command -v python3 >/dev/null 2>&1; then
        python3 -c "import hashlib, sys; print(hashlib.sha256(open(sys.argv[1], 'rb').read()).hexdigest())" "$_target"
    elif command -v python >/dev/null 2>&1; then
        python -c "import hashlib, sys; print(hashlib.sha256(open(sys.argv[1], 'rb').read()).hexdigest())" "$_target"
    else
        echo "NO_SHA256_TOOL"
        return 1
    fi
}

resolve_dir() {
    _d="$1"
    (cd "$_d" 2>/dev/null && pwd -P)
}

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd -P)
REPO_ROOT=$(cd "$SCRIPT_DIR/../.." 2>/dev/null && pwd -P || echo "")
INSTALLED_PLUGIN_DIR="${CEH_PLUGIN_DIR:-$HOME/.gemini/config/plugins/clearer-engineering}"

print_limits() {
    echo "=============================================================================="
    echo "LIMITES FORMAIS DE AUDITORIA (D3 / Handoff 090):"
    echo "• O hash prova integridade estrutural, NÃO autenticidade criptográfica."
    echo "  Quem gera o pacote de evidência pode gerar outro."
    echo "• O canário de release DEVE ser rodado pelo desenvolvedor, no terminal dele,"
    echo "  fora da sessão do agente."
    echo "• Ninguém deve tratar o pacote como prova de que o agente não interferiu."
    echo "=============================================================================="
}

run_self_check() {
    echo "=== [CEH DOCTOR: Self-Check de Ambiente e Dependências] ==="
    _errors=0

    # 1. Shell e comandos básicos
    for cmd in sh git; do
        if command -v "$cmd" >/dev/null 2>&1; then
            echo "  ✔ $cmd: $(command -v "$cmd")"
        else
            echo "  ✖ $cmd: NÃO ENCONTRADO"
            _errors=$((_errors + 1))
        fi
    done

    # 2. Ferramenta SHA-256
    _sha_tool=""
    if command -v sha256sum >/dev/null 2>&1; then
        _sha_tool="sha256sum"
    elif command -v shasum >/dev/null 2>&1; then
        _sha_tool="shasum -a 256"
    elif command -v python3 >/dev/null 2>&1; then
        _sha_tool="python3 (hashlib)"
    elif command -v python >/dev/null 2>&1; then
        _sha_tool="python (hashlib)"
    fi

    if [ -n "$_sha_tool" ]; then
        echo "  ✔ Ferramenta SHA-256: $_sha_tool"
    else
        echo "  ✖ Ferramenta SHA-256: NENHUMA DISPONÍVEL"
        _errors=$((_errors + 1))
    fi

    # 3. Python 3.9+ (runtime do gate)
    if command -v python3 >/dev/null 2>&1; then
        _py_ver=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')" 2>/dev/null || echo "desconhecido")
        if python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" 2>/dev/null; then
            echo "  ✔ Python 3: $_py_ver (compatível >= 3.9)"
        else
            echo "  ✖ Python 3: $_py_ver (incompatível, exige >= 3.9)"
            _errors=$((_errors + 1))
        fi
    else
        echo "  ✖ Python 3: NÃO ENCONTRADO"
        _errors=$((_errors + 1))
    fi

    # 4. Verificação funcional do Safety Gate (--check)
    _gate_script=""
    if [ -f "$INSTALLED_PLUGIN_DIR/scripts/safety-gate.py" ]; then
        _gate_script="$INSTALLED_PLUGIN_DIR/scripts/safety-gate.py"
    elif [ -n "$REPO_ROOT" ] && [ -f "$REPO_ROOT/clearer-engineering/scripts/safety-gate.py" ]; then
        _gate_script="$REPO_ROOT/clearer-engineering/scripts/safety-gate.py"
    fi

    if [ -n "$_gate_script" ]; then
        _check_out=$(python3 "$_gate_script" --check "echo test" 2>&1 || true)
        if echo "$_check_out" | grep -q '"decision"[[:space:]]*:[[:space:]]*"allow"'; then
            echo "  ✔ Safety Gate (--check): operacional (allow, exit 0)"
        else
            echo "  ✖ Safety Gate (--check): falhou ou resposta inesperada: $_check_out"
            _errors=$((_errors + 1))
        fi
    else
        echo "  ✖ Safety Gate: safety-gate.py não localizado"
        _errors=$((_errors + 1))
    fi

    if [ "$_errors" -eq 0 ]; then
        echo "✔ Self-Check: SUCESSO (ambiente 100% operacional)"
        return 0
    else
        echo "✖ Self-Check: FALHA ($_errors erro(s) detectado(s))"
        return 1
    fi
}

run_verify() {
    echo "=== [CEH DOCTOR: Verificação de Integridade dos Arquivos Instalados] ==="
    _ref_dir="${1:-$REPO_ROOT}"
    if [ -z "$_ref_dir" ] || [ ! -d "$_ref_dir/clearer-engineering" ]; then
        echo "  ✖ Diretório de referência não encontrado. Especifique o caminho do repositório CEH."
        return 1
    fi

    if [ ! -d "$INSTALLED_PLUGIN_DIR" ]; then
        echo "  ✖ Diretório instalado não encontrado: $INSTALLED_PLUGIN_DIR"
        return 1
    fi

    _ref_tmp=""
    _source_core="$_ref_dir/clearer-engineering"
    _ref_mode="crua"
    # CB11: Derivação canônica da referência fiel ao install.sh (pacote antigravity + evals)
    if [ -f "$_ref_dir/clearer-engineering/tools/package.py" ] && command -v python3 >/dev/null 2>&1; then
        _ref_tmp=$(mktemp -d "${TMPDIR:-/tmp}/ceh-verify-ref-XXXXXX")
        if python3 "$_ref_dir/clearer-engineering/tools/package.py" --host antigravity --out "$_ref_tmp" >/dev/null 2>&1; then
            rm -f "$_ref_tmp/.ceh-package-managed"
            if [ -d "$_ref_dir/evals" ]; then
                cp -r "$_ref_dir/evals" "$_ref_tmp/"
            fi
            _source_core="$_ref_tmp"
            _ref_mode="pacote"
        else
            rm -rf "$_ref_tmp"
            _ref_tmp=""
        fi
    fi

    # CB18: Impressão da referência utilizada e aviso explícito em caso de fallback
    if [ "$_ref_mode" = "pacote" ]; then
        echo "  • Referência: Pacote oficial gerado via tools/package.py"
    else
        echo "  • Referência: Árvore crua do repositório ($_source_core)"
        echo "  ⚠️ AVISO: Falha ao gerar pacote canônico. A verificação pode conter falsos positivos e o resultado é INCONCLUSIVO."
    fi

    _target_core="$INSTALLED_PLUGIN_DIR"
    _divergences=0
    _checked=0

    # 1. Compara todos os arquivos da árvore de referência contra o instalado (excluindo cache e metadados)
    # CB12 / CB17: Exclusão estrita apenas de diretório .git e arquivos canônicos (.gitignore, .gitkeep)
    _source_files=$(find "$_source_core" -type f \
        ! -path "*/__pycache__*" \
        ! -name "*.pyc" \
        ! -name "*.pyo" \
        ! -path "*/.git/*" \
        ! -name ".git" \
        ! -name ".gitignore" \
        ! -name ".gitkeep" \
        ! -name ".ceh-package-managed" 2>/dev/null | sort)

    for _src_file in $_source_files; do
        _rel=$(echo "$_src_file" | sed "s|^$_source_core/||")
        _tgt_file="$_target_core/$_rel"
        _checked=$((_checked + 1))

        if [ ! -f "$_tgt_file" ]; then
            echo "  ✖ Ausente no instalado: $_rel"
            _divergences=$((_divergences + 1))
            continue
        fi

        _src_hash=$(calc_sha256 "$_src_file")
        _tgt_hash=$(calc_sha256 "$_tgt_file")
        if [ "$_src_hash" != "$_tgt_hash" ]; then
            echo "  ✖ Divergência de hash em $_rel:"
            echo "      Referência: $_src_hash"
            echo "      Instalado:  $_tgt_hash"
            _divergences=$((_divergences + 1))
        fi
    done

    # 2. Sentido inverso: detecta arquivos estranhos ou não autorizados na instalação
    # CB12 / CB17: Não permite arquivos estranhos com prefixo .git (ex: scripts/.gitevil.py)
    _target_files=$(find "$_target_core" -type f \
        ! -path "*/__pycache__*" \
        ! -name "*.pyc" \
        ! -name "*.pyo" \
        ! -path "*/.git/*" \
        ! -name ".git" \
        ! -name ".gitignore" \
        ! -name ".gitkeep" \
        ! -name ".ceh-package-managed" 2>/dev/null | sort)

    for _tgt_file in $_target_files; do
        _rel=$(echo "$_tgt_file" | sed "s|^$_target_core/||")
        _src_file="$_source_core/$_rel"
        if [ ! -f "$_src_file" ]; then
            echo "  ✖ Arquivo não autorizado / estranho na instalação: $_rel"
            _divergences=$((_divergences + 1))
        fi
    done

    [ -n "$_ref_tmp" ] && rm -rf "$_ref_tmp"

    echo "  • Total de arquivos verificados: $_checked"
    if [ "$_divergences" -eq 0 ]; then
        echo "✔ Verificação: SUCESSO (todos os $_checked arquivos conferem byte-a-byte)"
        return 0
    else
        echo "✖ Verificação: FALHA ($_divergences arquivo(s) com divergência)"
        return 1
    fi
}

run_evidence() {
    print_limits
    echo ""
    echo "=== [CEH DOCTOR: Pacote de Evidência de Ambiente e Integridade] ==="
    _utc_date=$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date -u)
    echo "Data UTC: $_utc_date"
    echo "Host OS: $(uname -s 2>/dev/null) $(uname -r 2>/dev/null) ($(uname -m 2>/dev/null))"
    echo "Hostname: [REDACTED_HOSTNAME]"
    echo "Shell: $SHELL ($($SHELL --version 2>&1 | head -n 1 || echo 'sh'))"

    echo ""
    echo "--- [1. Integridade do Safety Gate] ---"
    _gate_installed="$INSTALLED_PLUGIN_DIR/scripts/safety-gate.py"
    _gate_ref=""
    if [ -n "$REPO_ROOT" ] && [ -f "$REPO_ROOT/clearer-engineering/scripts/safety-gate.py" ]; then
        _gate_ref="$REPO_ROOT/clearer-engineering/scripts/safety-gate.py"
    fi

    _exact_tag=""
    if [ -n "$REPO_ROOT" ] && [ -d "$REPO_ROOT/.git" ]; then
        _exact_tag=$(git -C "$REPO_ROOT" describe --tags --exact-match 2>/dev/null || echo "")
    fi

    if [ -f "$_gate_installed" ]; then
        _hash_inst=$(calc_sha256 "$_gate_installed")
        echo "Caminho: $(echo "$_gate_installed" | sed "s|$HOME|~|g")"
        echo "SHA-256 instalado:  $_hash_inst"
        if [ -n "$_gate_ref" ]; then
            _hash_ref=$(calc_sha256 "$_gate_ref")
            echo "SHA-256 referência: $_hash_ref"
            if [ -n "$_exact_tag" ]; then
                echo "Origem da referência: Tag oficial '$_exact_tag'"
                if [ "$_hash_inst" = "$_hash_ref" ]; then
                    echo "Comparação com tag: ✔ IDÊNTICO"
                else
                    echo "Comparação com tag: ✖ DIVERGENTE"
                fi
            else
                echo "Origem da referência: Workspace local (não é tag oficial)"
                if [ "$_hash_inst" = "$_hash_ref" ]; then
                    echo "Comparação com workspace: ✔ IDÊNTICO"
                else
                    echo "Comparação com workspace: ✖ DIVERGENTE"
                fi
            fi
        fi
    fi


    if [ -n "$REPO_ROOT" ] && [ -d "$REPO_ROOT/.git" ]; then
        _commit=$(git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null || echo "desconhecido")
        _branch=$(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "desconhecido")
        _tag=$(git -C "$REPO_ROOT" describe --tags --always 2>/dev/null || echo "sem tag")
        echo "Git Commit Workspace: $_commit"
        echo "Git Branch Workspace: $_branch"
        echo "Git Describe/Tag:     $_tag"
    fi

    echo ""
    echo "--- [2. Plugins Instalados e Concorrentes] ---"
    _plugins_dir="$HOME/.gemini/config/plugins"
    if [ -d "$_plugins_dir" ]; then
        for _plugin_entry in "$_plugins_dir"/*; do
            if [ -d "$_plugin_entry" ]; then
                echo "  • $(basename "$_plugin_entry")"
            fi
        done
    else
        echo "  (Diretório de plugins $_plugins_dir não encontrado)"
    fi

    echo ""
    echo "--- [3. Índices de Transcrição da Sessão (Ressalva BK1)] ---"
    if [ -n "$STEP_CALL" ] && [ -n "$STEP_RESP" ]; then
        echo "Passo de chamada do canário (BK1):  $STEP_CALL"
        echo "Passo de resposta do canário (BK1): $STEP_RESP"
    fi

    _brain_dir="$HOME/.gemini/antigravity-ide/brain"
    _found_transcript=""
    if [ -d "$_brain_dir" ]; then
        _found_transcript=$(find "$_brain_dir" -type f -name "transcript.jsonl" -exec ls -t {} + 2>/dev/null | head -n 1 || true)
    fi

    if [ -n "$_found_transcript" ] && [ -f "$_found_transcript" ]; then
        echo "Transcrição ativa mais recente: $(echo "$_found_transcript" | sed "s|$HOME|~|g")"
        _total_steps=$(wc -l < "$_found_transcript" 2>/dev/null | tr -d ' ' || echo "0")
        echo "Total de passos registrados: $_total_steps"
        echo "Últimos 3 passos (amostra de índices):"
        tail -n 3 "$_found_transcript" | awk -F',' '{for(i=1;i<=NF;i++) if($i ~ /"step_index":/ || $i ~ /"type":/ || $i ~ /"status":/) printf "%s ", $i; print ""}' 2>/dev/null || true
    else
        echo "Nenhuma transcrição ativa localizada (execução direta via CLI/terminal)."
    fi

    echo ""
    echo "--- [4. Manifesto SHA-256 de Componentes Críticos] ---"
    _ref_dir="${1:-$REPO_ARG}"
    _target_dir="$INSTALLED_PLUGIN_DIR"
    if [ ! -d "$_target_dir" ] && [ -n "$_ref_dir" ] && [ -d "$_ref_dir/clearer-engineering" ]; then
        _target_dir="$_ref_dir/clearer-engineering"
    fi

    if [ -d "$_target_dir" ]; then
        echo "Raiz de leitura: $(echo "$_target_dir" | sed "s|$HOME|~|g")"
        find "$_target_dir/scripts" "$_target_dir/rules" "$_target_dir/profiles" -type f 2>/dev/null | sort | while IFS= read -r f; do
            _h=$(calc_sha256 "$f")
            _rel=$(echo "$f" | sed "s|^$_target_dir/||")
            printf "  %s  %s\n" "$_h" "$_rel"
        done
    else
        echo "Diretório de componentes não localizado para emissão de manifesto."
    fi

    echo ""
    echo "=== FIM DO PACOTE DE EVIDÊNCIA ==="
}

show_help() {
    echo "Uso: $0 [OPÇÕES]"
    echo ""
    echo "Opções:"
    echo "  --self-check                  Executa auto-teste rápido de dependências do host (Python, sh, gate)"
    echo "  --verify [REPO]               Verifica a integridade do conjunto completo de arquivos instalados contra o repositório"
    echo "  --evidence [REPO]             Gera pacote consolidado de evidência de host e integridade (D3 / BK1)"
    echo "  --step-call <N>               Registra índice do passo da chamada do canário na evidência (BK1)"
    echo "  --step-resp <M>               Registra índice do passo da resposta do canário na evidência (BK1)"
    echo "  --help                        Exibe esta mensagem de ajuda"
    echo ""
    echo "Se nenhuma opção for fornecida, executa --self-check e --verify."
}

STEP_CALL=""
STEP_RESP=""
REPO_ARG="$REPO_ROOT"
ACTION=""

if [ $# -eq 0 ]; then
    run_self_check
    echo ""
    run_verify "$REPO_ROOT"
    exit $?
fi

while [ $# -gt 0 ]; do
    case "$1" in
        --self-check)
            ACTION="self-check"
            shift
            ;;
        --verify)
            ACTION="verify"
            shift
            if [ $# -gt 0 ] && [ "${1#--}" = "$1" ]; then
                REPO_ARG="$1"
                shift
            fi
            ;;
        --evidence)
            ACTION="evidence"
            shift
            if [ $# -gt 0 ] && [ "${1#--}" = "$1" ]; then
                REPO_ARG="$1"
                shift
            fi
            ;;
        --step-call)
            shift
            STEP_CALL="$1"
            shift
            ;;
        --step-resp)
            shift
            STEP_RESP="$1"
            shift
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        *)
            echo "Opção desconhecida: $1"
            show_help
            exit 1
            ;;
    esac
done

case "$ACTION" in
    self-check)
        run_self_check
        ;;
    verify)
        run_verify "$REPO_ARG"
        ;;
    evidence)
        run_evidence "$REPO_ARG"
        ;;
    *)
        show_help
        exit 1
        ;;
esac

