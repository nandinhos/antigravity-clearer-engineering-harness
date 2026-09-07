#!/usr/bin/env bash
# ==============================================================================
# ceh-help.sh - Interactive CLI Quick Help & Guide for CLEARER Harness
# ==============================================================================
set -euo pipefail

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

cat << "EOF"
  ╔═══════════════════════════════════════════════════════════════════╗
  ║    🛡️  CLEARER Engineering Harness (CEH) — CLI Quick Guide        ║
  ║         Evidence-Driven Engineering for Google Antigravity        ║
  ╚═══════════════════════════════════════════════════════════════════╝
EOF

echo ""
echo -e "${BOLD}${CYAN}▶ COMANDOS RÁPIDOS NO TERMINAL:${NC}"
echo -e "  ${GREEN}ceh${NC}             : Iniciar o Antigravity CLI com o perfil do harness (atalho de agy-ceh)"
echo -e "  ${GREEN}agy-ceh${NC}         : Iniciar o Antigravity com profile 'clearer-harness'"
echo -e "  ${GREEN}agy-ceh-yolo${NC}    : Iniciar com auto-aprovação de edições seguras (modo contínuo)"
echo -e "  ${GREEN}ceh-env${NC}         : Identificar o ambiente atual (DEV/HOMOLOGAÇÃO/PRODUÇÃO) e branch ativa"
echo -e "  ${GREEN}ceh-branches${NC}    : Auditar e configurar topologia de branches (Modo Enterprise ou Clássico)"
echo -e "  ${GREEN}ceh-preflight${NC}   : Executar diagnóstico de prontidão e integridade do projeto"
echo -e "  ${GREEN}ceh-help${NC}        : Exibir este guia rápido"

echo ""
echo -e "${BOLD}${CYAN}▶ NÍVEIS DE RIGOR POR AMBIENTE (SAFETY GATE):${NC}"
echo -e "  ${GREEN}● DEV (branch dev)${NC}       : ${BOLD}ALLOW${NC} — Liberdade total para testes e correções (com backup local)."
echo -e "  ${YELLOW}● STAGING (homolog)${NC}      : ${BOLD}ASK (2 Alertas)${NC} — Exige confirmação humana de blast radius e rollback."
echo -e "  ${RED}● PRODUÇÃO (main)${NC}        : ${BOLD}DENY${NC} — Comandos destrutivos são sumariamente bloqueados (fora de cogitação)."
echo -e "  ${RED}● CATASTRÓFICO${NC}          : ${BOLD}DENY Absoluto${NC} — 'rm -rf /', fork bombs e deleção de SO bloqueados em qualquer ambiente."

echo ""
echo -e "${BOLD}${CYAN}▶ TOPOLOGIAS DE BRANCHES SUPORTADAS:${NC}"
echo -e "  ${BOLD}1. Modo Enterprise (3 branches)${NC}: dev ➔ staging ➔ main (recomendado para esteiras formais)"
echo -e "  ${BOLD}2. Modo Clássico (2 branches)${NC}  : dev ➔ main (ágil para MVPs e squads enxutas)"
echo -e "  ${BLUE}Derivações${NC}                       : Partem sempre de dev/ (ex: dev/auth-token, dev/feature-x)"

echo ""
echo -e "${BOLD}${CYAN}▶ FILOSOFIA PONYTAIL MODE & AST FIRST:${NC}"
echo -e "  - ${BOLD}Escada de Decisão${NC}  : Precisa existir? > Já existe na base? > stdlib resolve? > Menor diff funcional."
echo -e "  - ${BOLD}AST First${NC}          : Se houver Graphify (graphify-out/graph.json), usa o grafo a custo zero de tokens."
echo -e "  - ${BOLD}Fallback Nativo${NC}    : Se não houver Graphify, usa grep cirúrgico e leitura fatiada. Proibido dumps cegos."
echo -e "  - ${BOLD}Anti-Over-Orch${NC}     : Tarefas contidas (1 a 3 arquivos) são resolvidas em turno único sem subagentes."

echo ""
echo -e "${BOLD}${CYAN}▶ SKILLS NATIVAS DISPONÍVEIS NO ANTIGRAVITY:${NC}"
echo -e "  ${BLUE}/clearer${NC}          : Dispatcher geral e seletor de Risk Dial (LOW, MEDIUM, HIGH)"
echo -e "  ${BLUE}/clearer-feature${NC}  : Implementação de features orientada a evidências"
echo -e "  ${BLUE}/clearer-bugfix${NC}   : Workflow Root-Cause First para correção de bugs"
echo -e "  ${BLUE}/clearer-refactor${NC} : Refatoração segura com baseline de comportamento"
echo -e "  ${BLUE}/clearer-review${NC}   : Revisão adversarial de diff"
echo -e "  ${BLUE}/clearer-test${NC}     : Execução determinística de testes com evidências não-mascaradas"
echo -e "  ${BLUE}/clearer-audit${NC}    : Auditoria formal de claims (SUPPORTED / PARTIALLY / UNSUPPORTED)"
echo -e "  ${BLUE}/clearer-map${NC}      : Mapeamento arquitetural read-only do repositório"

echo ""
echo -e "Documentação completa: ${BLUE}https://github.com/nandinhos/antigravity-clearer-engineering-harness${NC}"
echo ""
