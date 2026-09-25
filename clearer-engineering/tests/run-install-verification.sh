#!/usr/bin/env bash
# ==============================================================================
# run-install-verification.sh - Installation, Idempotency & Clean Uninstall Suite
# ==============================================================================
set -euo pipefail

PLUGIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_ROOT="$(cd "$PLUGIN_DIR/.." && pwd)"

echo "============================================================"
echo "    CEH Installation, Idempotency & Uninstall Verification"
echo "============================================================"

TMP_HOME="$(mktemp -d)"
cleanup() {
    rm -rf "$TMP_HOME"
}
trap cleanup EXIT

# Setup mock home with clean rc files
touch "$TMP_HOME/.bashrc" "$TMP_HOME/.zshrc"

echo "[1/3] Primeira instalação (clean install)..."
HOME="$TMP_HOME" bash "$REPO_ROOT/install.sh" >/dev/null

# 1.1 Verificar plugin
if [[ ! -f "$TMP_HOME/.gemini/config/plugins/clearer-engineering/plugin.json" ]]; then
    echo "ERRO: plugin.json não foi instalado em ~/.gemini/config/plugins/clearer-engineering"
    exit 1
fi

# 1.2 Verificar agent profile
if [[ ! -f "$TMP_HOME/.gemini/config/agents/clearer-harness/agent.md" ]]; then
    echo "ERRO: agent.md não foi instalado em ~/.gemini/config/agents/clearer-harness"
    exit 1
fi

# 1.3 Verificar se agy reconhece o agente quando agy está disponível
if command -v agy >/dev/null 2>&1; then
    if ! HOME="$TMP_HOME" agy agent 2>/dev/null | grep -q 'clearer-harness'; then
        echo "AVISO/INFO: agy agent não listou clearer-harness no HOME temporário (pode depender de config global do agy)"
    fi
fi

# 1.4 Verificar aliases no .bashrc e .zshrc
for rc in "$TMP_HOME/.bashrc" "$TMP_HOME/.zshrc"; do
    if ! grep -q "alias agy-ceh=" "$rc"; then
        echo "ERRO: alias agy-ceh não encontrado em $rc"
        exit 1
    fi
    count=$(grep -c "# BEGIN CLEARER ENGINEERING HARNESS (CEH) ALIASES" "$rc" || true)
    if [[ "$count" -ne 1 ]]; then
        echo "ERRO: contagem do bloco de aliases em $rc é $count (esperado 1)"
        exit 1
    fi
done
echo "✔ Primeira instalação verificada com sucesso."

echo "[2/3] Segunda instalação (idempotência)..."
HOME="$TMP_HOME" bash "$REPO_ROOT/install.sh" >/dev/null

for rc in "$TMP_HOME/.bashrc" "$TMP_HOME/.zshrc"; do
    count=$(grep -c "# BEGIN CLEARER ENGINEERING HARNESS (CEH) ALIASES" "$rc" || true)
    if [[ "$count" -ne 1 ]]; then
        echo "ERRO DE IDEMPOTÊNCIA: bloco de aliases duplicado em $rc (encontradas $count ocorrências, esperado 1)"
        exit 1
    fi
    alias_count=$(grep -c "alias agy-ceh=" "$rc" || true)
    if [[ "$alias_count" -ne 1 ]]; then
        echo "ERRO DE IDEMPOTÊNCIA: alias agy-ceh duplicado em $rc (encontradas $alias_count ocorrências, esperado 1)"
        exit 1
    fi
done
echo "✔ Idempotência verificada: nenhum bloco duplicado após re-instalação."

echo "[3/3] Desinstalação limpa (uninstall.sh)..."
HOME="$TMP_HOME" bash "$REPO_ROOT/uninstall.sh" >/dev/null

if [[ -d "$TMP_HOME/.gemini/config/plugins/clearer-engineering" ]]; then
    echo "ERRO: diretório do plugin ainda existe após uninstall: $TMP_HOME/.gemini/config/plugins/clearer-engineering"
    exit 1
fi

if [[ -d "$TMP_HOME/.gemini/config/agents/clearer-harness" ]]; then
    echo "ERRO: diretório do agent ainda existe após uninstall: $TMP_HOME/.gemini/config/agents/clearer-harness"
    exit 1
fi

for rc in "$TMP_HOME/.bashrc" "$TMP_HOME/.zshrc"; do
    if grep -q "alias agy-ceh=" "$rc"; then
        echo "ERRO: alias agy-ceh ainda presente em $rc após uninstall"
        exit 1
    fi
    if grep -q "# BEGIN CLEARER ENGINEERING HARNESS" "$rc"; then
        echo "ERRO: marcador CEH ainda presente em $rc após uninstall"
        exit 1
    fi
done
echo "✔ Desinstalação limpa verificada: nenhum resíduo em ~/.gemini ou rc files."

echo "============================================================"
echo "✔ TODOS OS TESTES DE INSTALAÇÃO E DESINSTALAÇÃO PASSARAM (100%)"
echo "============================================================"
