#!/usr/bin/env bash
# ==============================================================================
# setup-branches.sh - Canonical Branch Topology Setup for CLEARER Harness
# ==============================================================================
# Supports 2 engineering topologies:
# 1. Modo 3 Branches (Enterprise):  dev -> staging -> main
# 2. Modo 2 Branches (Clássico):    dev -> main
# ==============================================================================
set -euo pipefail

MODE=""
TARGET_DIR="."

# Parse CLI arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --mode|-m)
            MODE="$2"
            shift 2
            ;;
        --classic|-2|--modo-2)
            MODE="2"
            shift
            ;;
        --enterprise|-3|--modo-3)
            MODE="3"
            shift
            ;;
        *)
            if [[ -d "$1" ]]; then
                TARGET_DIR="$1"
            fi
            shift
            ;;
    esac
done

cd "$TARGET_DIR"

echo "=== [CEH Canonical Branch Topology Setup] ==="
echo "Target Directory: $(pwd)"
echo ""

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "❌ Erro: O diretório atual não é um repositório Git."
    echo "   Execute 'git init' antes de configurar as branches."
    exit 1
fi

CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "")
if [[ -z "$CURRENT_BRANCH" ]]; then
    echo "❌ Erro: Não há commits ou branch ativa no repositório."
    echo "   Crie um commit inicial antes de gerar a topologia de branches."
    exit 1
fi

# Detect existing canonical branches
HAS_MAIN=0
HAS_STAGING=0
HAS_DEV=0

if git show-ref --verify --quiet refs/heads/main || git show-ref --verify --quiet refs/heads/master; then
    HAS_MAIN=1
fi
if git show-ref --verify --quiet refs/heads/staging || git show-ref --verify --quiet refs/heads/homolog || git show-ref --verify --quiet refs/heads/homologacao; then
    HAS_STAGING=1
fi
if git show-ref --verify --quiet refs/heads/dev || git show-ref --verify --quiet refs/heads/develop; then
    HAS_DEV=1
fi

MAIN_REF="main"
if ! git show-ref --verify --quiet refs/heads/main && git show-ref --verify --quiet refs/heads/master; then
    MAIN_REF="master"
fi

echo "🔍 Estado Atual das Branches no Repositório:"
echo "  • Produção (main/master):             $([ $HAS_MAIN -eq 1 ] && echo '✔ Presente' || echo '❌ Ausente')"
echo "  • Homologação (staging/homolog):      $([ $HAS_STAGING -eq 1 ] && echo '✔ Presente' || echo '❌ Ausente')"
echo "  • Desenvolvimento (dev/develop):      $([ $HAS_DEV -eq 1 ] && echo '✔ Presente' || echo '❌ Ausente')"
echo ""

# Resolve Mode if not provided via CLI
if [[ -z "$MODE" ]]; then
    # If staging already exists, assume 3-branches mode by default
    if [[ $HAS_STAGING -eq 1 ]]; then
        MODE="3"
    elif [[ -t 0 ]]; then
        # Interactive prompt
        echo "Selecione o modo de desenvolvimento desejado para o projeto:"
        echo "  [1] Modo Clássico (2 Branches: dev e main) -> Ideal para projetos ágeis e MVPs"
        echo "  [2] Modo Enterprise (3 Branches: dev, staging e main) -> Com esteira de homologação"
        read -rp "Opção [1/2] (padrão 1): " USER_CHOICE
        if [[ "$USER_CHOICE" == "2" ]]; then
            MODE="3"
        else
            MODE="2"
        fi
    else
        # Non-interactive default: Modo 2 (Clássico)
        MODE="2"
    fi
fi

# Ensure Main exists
if [[ $HAS_MAIN -eq 0 ]]; then
    echo "⚙️ Criando branch principal 'main' a partir de '$CURRENT_BRANCH'..."
    git branch -M main
    MAIN_REF="main"
    HAS_MAIN=1
fi

case "$MODE" in
    3|enterprise)
        echo "🚀 Configurando Modo Enterprise (3 Branches: dev -> staging -> main)..."
        # 1. Ensure Staging exists
        if [[ $HAS_STAGING -eq 0 ]]; then
            echo "⚙️ Criando branch 'staging' a partir de '$MAIN_REF'..."
            git branch staging "$MAIN_REF"
            echo "✔ Branch 'staging' criada com sucesso."
            HAS_STAGING=1
        fi

        # 2. Ensure Dev exists
        if [[ $HAS_DEV -eq 0 ]]; then
            echo "⚙️ Criando branch 'dev' a partir de 'staging'..."
            git branch dev staging
            echo "✔ Branch 'dev' criada com sucesso."
            HAS_DEV=1
        fi

        # 3. Switch to dev
        if [[ "$(git branch --show-current 2>/dev/null || echo '')" != "dev" ]]; then
            echo "🔄 Alternando working tree para a branch de desenvolvimento 'dev'..."
            git checkout dev
        fi

        echo ""
        echo "====================================================================="
        echo "  🎉 TOPOLOGIA MODO 3-BRANCHES (ENTERPRISE) CONFIGURADA!"
        echo "====================================================================="
        echo "  • dev      [ATIVO] -> Onde todo o desenvolvimento e testes ocorrem (ALLOW)"
        echo "  • staging  [HML]   -> Homologação com dados reais e dupla confirmação (ASK)"
        echo "  • main     [PROD]  -> Produção protegida contra comandos destrutivos (DENY)"
        echo ""
        echo "  Para publicar as branches no repositório remoto, execute:"
        echo "  git push -u origin staging && git push -u origin dev"
        echo "====================================================================="
        ;;

    2|classic|*)
        echo "🚀 Configurando Modo Clássico (2 Branches: dev -> main)..."
        # 1. Ensure Dev exists from main
        if [[ $HAS_DEV -eq 0 ]]; then
            echo "⚙️ Criando branch 'dev' a partir de '$MAIN_REF'..."
            git branch dev "$MAIN_REF"
            echo "✔ Branch 'dev' criada com sucesso."
            HAS_DEV=1
        fi

        # 2. Switch to dev
        if [[ "$(git branch --show-current 2>/dev/null || echo '')" != "dev" ]]; then
            echo "🔄 Alternando working tree para a branch de desenvolvimento 'dev'..."
            git checkout dev
        fi

        echo ""
        echo "====================================================================="
        echo "  🎉 TOPOLOGIA MODO 2-BRANCHES (CLÁSSICO) CONFIGURADA!"
        echo "====================================================================="
        echo "  • dev   [ATIVO] -> Onde todo o desenvolvimento e testes ocorrem (ALLOW)"
        echo "  • main  [PROD]  -> Produção protegida contra comandos destrutivos (DENY)"
        echo ""
        echo "  Para publicar a branch no repositório remoto, execute:"
        echo "  git push -u origin dev"
        echo "====================================================================="
        ;;
esac
