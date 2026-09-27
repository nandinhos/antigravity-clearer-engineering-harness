#!/usr/bin/env bash
# ==============================================================================
# run-install-verification.sh - Installation, Idempotency, Symmetry & Honesty Suite
# ==============================================================================
set -euo pipefail

PLUGIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_ROOT="$(cd "$PLUGIN_DIR/.." && pwd)"

echo "============================================================"
echo "    CEH Installation Verification: Idempotency, Symmetry & Honesty"
echo "============================================================"

TMP_BASE="$(mktemp -d -t ceh-verify-XXXXXX)"
cleanup() {
    rm -rf "$TMP_BASE"
}
trap cleanup EXIT

TMP_HOME="$TMP_BASE/home"
mkdir -p "$TMP_HOME"

# Setup initial rc files with realistic content
cat << 'EOF' > "$TMP_HOME/.bashrc"
# ~/.bashrc: default mock configuration
export PATH="/usr/local/bin:$PATH"
alias ll='ls -al'
EOF

cat << 'EOF' > "$TMP_HOME/.zshrc"
# ~/.zshrc: default mock configuration
export ZSH_THEME="robbyrussell"
EOF

BASHRC_ORIG_HASH=$(sha256sum "$TMP_HOME/.bashrc" | awk '{print $1}')
ZSHRC_ORIG_HASH=$(sha256sum "$TMP_HOME/.zshrc" | awk '{print $1}')

# ------------------------------------------------------------------------------
# Teste 1: Idempotência de Instalação (1 bloco após 2 instalações)
# ------------------------------------------------------------------------------
echo "[1/4] Teste 1: Idempotência de Instalação (instalar 2x gera exatamente 1 bloco)..."

# 1.1 Primeira instalação
HOME="$TMP_HOME" bash "$REPO_ROOT/install.sh" >/dev/null

if [[ ! -f "$TMP_HOME/.gemini/config/plugins/clearer-engineering/plugin.json" ]]; then
    echo "ERRO: plugin.json não foi instalado em ~/.gemini/config/plugins/clearer-engineering"
    exit 1
fi

if [[ ! -f "$TMP_HOME/.gemini/config/agents/clearer-harness/agent.md" ]]; then
    echo "ERRO: agent.md não foi instalado em ~/.gemini/config/agents/clearer-harness"
    exit 1
fi

if [[ ! -f "$TMP_HOME/.gemini/config/plugins/clearer-engineering/config/aliases.sh" ]]; then
    echo "ERRO: config/aliases.sh não foi copiado para a árvore instalada"
    exit 1
fi

# 1.2 Segunda instalação (idempotência)
HOME="$TMP_HOME" bash "$REPO_ROOT/install.sh" >/dev/null

for rc in "$TMP_HOME/.bashrc" "$TMP_HOME/.zshrc"; do
    rc_name=$(basename "$rc")
    start_count=$(grep -c "# BEGIN CLEARER ENGINEERING HARNESS (CEH) ALIASES" "$rc" || true)
    if [[ "$start_count" -ne 1 ]]; then
        echo "ERRO DE IDEMPOTÊNCIA: '$rc_name' tem $start_count blocos START (esperado 1)"
        exit 1
    fi

    end_count=$(grep -c "# END CLEARER ENGINEERING HARNESS (CEH) ALIASES" "$rc" || true)
    if [[ "$end_count" -ne 1 ]]; then
        echo "ERRO DE IDEMPOTÊNCIA: '$rc_name' tem $end_count blocos END (esperado 1)"
        exit 1
    fi

    alias_count=$(grep -c "alias agy-ceh=" "$rc" || true)
    if [[ "$alias_count" -ne 1 ]]; then
        echo "ERRO DE IDEMPOTÊNCIA: '$rc_name' tem $alias_count ocorrências de 'alias agy-ceh=' (esperado 1)"
        exit 1
    fi
done

echo "✔ Teste 1 PASS: Idempotência comprovada (1 único bloco preservado após re-instalação)."

# ------------------------------------------------------------------------------
# Teste 2: Simetria Byte a Byte (Uninstall restaura estado original exato)
# ------------------------------------------------------------------------------
echo "[2/4] Teste 2: Simetria Byte a Byte (instalar seguido de uninstall restaura rc files idênticos)..."

HOME="$TMP_HOME" bash "$REPO_ROOT/uninstall.sh" >/dev/null

if [[ -d "$TMP_HOME/.gemini/config/plugins/clearer-engineering" ]]; then
    echo "ERRO: diretório do plugin ainda existe após uninstall: $TMP_HOME/.gemini/config/plugins/clearer-engineering"
    exit 1
fi

if [[ -d "$TMP_HOME/.gemini/config/agents/clearer-harness" ]]; then
    echo "ERRO: diretório do agent ainda existe após uninstall: $TMP_HOME/.gemini/config/agents/clearer-harness"
    exit 1
fi

BASHRC_POST_HASH=$(sha256sum "$TMP_HOME/.bashrc" | awk '{print $1}')
ZSHRC_POST_HASH=$(sha256sum "$TMP_HOME/.zshrc" | awk '{print $1}')

if [[ "$BASHRC_POST_HASH" != "$BASHRC_ORIG_HASH" ]]; then
    echo "ERRO DE SIMETRIA: .bashrc divergiu após uninstall!"
    echo "Original: $BASHRC_ORIG_HASH | Pós-uninstall: $BASHRC_POST_HASH"
    diff -u <(echo "Original") "$TMP_HOME/.bashrc" || true
    exit 1
fi

if [[ "$ZSHRC_POST_HASH" != "$ZSHRC_ORIG_HASH" ]]; then
    echo "ERRO DE SIMETRIA: .zshrc divergiu após uninstall!"
    echo "Original: $ZSHRC_ORIG_HASH | Pós-uninstall: $ZSHRC_POST_HASH"
    exit 1
fi

# Teste adicional de simetria com arquivo vazio (0 bytes)
EMPTY_HOME="$TMP_BASE/empty_home"
mkdir -p "$EMPTY_HOME"
touch "$EMPTY_HOME/.bashrc"

HOME="$EMPTY_HOME" bash "$REPO_ROOT/install.sh" >/dev/null
HOME="$EMPTY_HOME" bash "$REPO_ROOT/uninstall.sh" >/dev/null

EMPTY_POST_SIZE=$(wc -c < "$EMPTY_HOME/.bashrc")
if [[ "$EMPTY_POST_SIZE" -ne 0 ]]; then
    echo "ERRO DE SIMETRIA: arquivo originalmente vazio ficou com $EMPTY_POST_SIZE bytes após uninstall!"
    exit 1
fi

echo "✔ Teste 2 PASS: Simetria byte a byte comprovada (hashes idênticos e 0 resíduos)."

# ------------------------------------------------------------------------------
# Teste 3: Todo alias aponta para arquivo existente na árvore instalada
# ------------------------------------------------------------------------------
echo "[3/4] Teste 3: Todo alias aponta para script existente na árvore instalada..."

# Reinstala para inspecionar os alvos instalados
HOME="$TMP_HOME" bash "$REPO_ROOT/install.sh" >/dev/null

INSTALLED_PLUGIN_DIR="$TMP_HOME/.gemini/config/plugins/clearer-engineering"
ALIAS_CONF="$INSTALLED_PLUGIN_DIR/config/aliases.sh"

if [[ ! -f "$ALIAS_CONF" ]]; then
    echo "ERRO: $ALIAS_CONF não encontrado na árvore instalada"
    exit 1
fi

missing_targets=0
checked_count=0

while IFS= read -r line || [[ -n "$line" ]]; do
    # Extrai comando dentro de alias nome='comando'
    if [[ "$line" =~ ^alias[[:space:]]+([a-zA-Z0-9_-]+)=\'([^\']+)\' ]]; then
        alias_name="${BASH_REMATCH[1]}"
        alias_cmd="${BASH_REMATCH[2]}"
        
        # Se o alias faz referência a um script no plugin (.gemini/config/plugins/clearer-engineering/...)
        if [[ "$alias_cmd" =~ \.gemini/config/plugins/clearer-engineering/([^[:space:]]+) ]]; then
            rel_path="${BASH_REMATCH[1]}"
            target_file="$INSTALLED_PLUGIN_DIR/$rel_path"
            checked_count=$((checked_count + 1))
            
            if [[ ! -f "$target_file" ]]; then
                echo "ERRO: Alias '$alias_name' aponta para arquivo inexistente: $target_file"
                missing_targets=$((missing_targets + 1))
            elif [[ ! -x "$target_file" ]]; then
                echo "ERRO: Arquivo do alias '$alias_name' não é executável: $target_file"
                missing_targets=$((missing_targets + 1))
            fi
        fi
    fi
done < "$ALIAS_CONF"

if [[ "$missing_targets" -gt 0 ]]; then
    echo "ERRO: $missing_targets alvos de aliases estão ausentes ou sem permissão de execução."
    exit 1
fi

if [[ "$checked_count" -lt 7 ]]; then
    echo "ERRO: Menos de 7 scripts de aliases foram verificados (verificados: $checked_count)"
    exit 1
fi

echo "✔ Teste 3 PASS: Todos os $checked_count aliases que apontam para scripts foram verificados e existem."

# ------------------------------------------------------------------------------
# Teste 4: Validação Honesta de Plugin (Mock de agy com falha sai com exit ≠ 0)
# ------------------------------------------------------------------------------
echo "[4/4] Teste 4: Validação honesta (falha de agy plugin validate sai com exit ≠ 0)..."

MOCK_BIN_DIR="$TMP_BASE/mock_bin"
mkdir -p "$MOCK_BIN_DIR"

# Cria mock agy que falha com exit code 42
cat << 'EOF' > "$MOCK_BIN_DIR/agy"
#!/usr/bin/env bash
if [[ "$1" == "plugin" && "$2" == "validate" ]]; then
    echo "MOCK ERROR: Schema validation failed for plugin.json (simulated corruption)" >&2
    exit 42
fi
exit 0
EOF
chmod +x "$MOCK_BIN_DIR/agy"

mock_exit=0
mock_output=$(HOME="$TMP_HOME" PATH="$MOCK_BIN_DIR:$PATH" bash "$REPO_ROOT/install.sh" 2>&1) || mock_exit=$?

if [[ "$mock_exit" -ne 42 ]]; then
    echo "ERRO: install.sh com agy mock falho deveria retornar exit code 42, mas retornou $mock_exit"
    echo "Output: $mock_output"
    exit 1
fi

if ! echo "$mock_output" | grep -q "MOCK ERROR: Schema validation failed"; then
    echo "ERRO: Mensagem de erro real do agy validate não foi exibida pelo install.sh!"
    echo "Output: $mock_output"
    exit 1
fi

# Agora testa o escape hatch consciente com --skip-diagnostics
skip_exit=0
skip_output=$(HOME="$TMP_HOME" PATH="$MOCK_BIN_DIR:$PATH" bash "$REPO_ROOT/install.sh" --skip-diagnostics 2>&1) || skip_exit=$?

if [[ "$skip_exit" -ne 0 ]]; then
    echo "ERRO: install.sh com --skip-diagnostics deveria ter sucesso (exit 0), mas retornou $skip_exit"
    echo "Output: $skip_output"
    exit 1
fi

if ! echo "$skip_output" | grep -q -- "--skip-diagnostics"; then
    echo "ERRO: Aviso de --skip-diagnostics não registrado no log!"
    exit 1
fi

echo "✔ Teste 4 PASS: Validação honesta verificada (exit 42 na falha e exit 0 com --skip-diagnostics)."

echo "============================================================"
echo "✔ TODOS OS 4 TESTES DE INSTALAÇÃO/DESINSTALAÇÃO PASSARAM (100%)"
echo "============================================================"
