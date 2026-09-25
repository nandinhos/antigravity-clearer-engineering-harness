#!/usr/bin/env bash
# ==============================================================================
# CLEARER Engineering Harness (CEH) — Conselho de Seniores (Add-on Opcional)
# ==============================================================================
# Orquestrador dinâmico multi-modelo para apoiar a deliberação técnica,
# auditoria adversarial e homologação através de CLIs de IA instalados.
#
# NOTA DE ESCOPO:
#   Este script é um ADD-ON OPCIONAL DE PRODUTIVIDADE DO DESENVOLVEDOR.
#   Não é requisito obrigatório para a conformidade do harness CEH.
#   O quórum é formado dinamicamente a partir dos CLIs que estiverem
#   efetivamente presentes e configurados na máquina do desenvolvedor.
#
# Modelos Candidatos Suportados:
#   - claude (Anthropic)    -> Ponytail Lead & Análise Semântica
#   - codex  (OpenAI)       -> Lógica Formal, Algoritmos & Concorrência
#   - muse   (Meta)         -> POSIX, Sistemas & Portabilidade de Runtime
#   - hermes (Hermes Agent) -> Tooling, MCPs & Automação de Agentes
#   - agy    (Antigravity)  -> Harness, Safety Gate & Invariantes de Ambiente
#   - agent  (Cursor)       -> Diff Review Cirúrgico & Ergonomia de Código
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null || (cd "$SCRIPT_DIR/../.." && pwd))"

# Configurações padrão
TIMEOUT_SECS=90
REQUESTED_AGENTS=()
USER_PROMPT=""
PROMPT_FILE=""
USE_DIFF=false
DRY_RUN=false
OUTPUT_DIR=""

# Paleta ANSI
BOLD='\033[1m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
RESET='\033[0m'

# Todos os modelos conhecidos pelo add-on
ALL_KNOWN_AGENTS=("claude" "codex" "muse" "hermes" "agy" "agent")

usage() {
  cat <<EOF
${BOLD}CLEARER Engineering Harness — Conselho de Seniores (Add-on Opcional)${RESET}

Uso:
  $0 [opções]

Opções de Agentes:
  --all                 Convoca todos os conselheiros ativos detectados (padrão)
  --agent <nome>        Convoca apenas o agente especificado:
                        (claude | codex | muse | hermes | agy | agent)
                        Pode ser repetido: --agent claude --agent codex
  --list-available      Lista quais CLIs de conselheiros estão instalados e prontos

Opções de Contexto:
  --diff                Extrai e anexa o tripé de Git diff (unstaged, staged e HEAD~1)
  --prompt <texto>      Prompt ou objeto específico para deliberação do conselho
  --file <caminho>      Arquivo contendo especificação, plano ou código a avaliar
  --timeout <segundos>  Timeout máximo por agente em segundos (padrão: 90s)
  --output-dir <dir>    Diretório para salvar a ata e os pareceres individuais
  --dry-run             Exibe os prompts e comandos montados sem disparar os CLIs
  -h, --help            Exibe esta ajuda

Exemplos:
  $0 --all --diff
  $0 --agent claude --agent agy --diff --prompt "Auditar rigorosamente o FSM Lexer"
  $0 --list-available
EOF
  exit 0
}

# Auto-descoberta de CLIs disponíveis no sistema
detect_available_agents() {
  local -n out_arr=$1
  out_arr=()
  for cand in "${ALL_KNOWN_AGENTS[@]}"; do
    if command -v "$cand" >/dev/null 2>&1; then
      out_arr+=("$cand")
    fi
  done
}

# Parsing de argumentos
while [[ $# -gt 0 ]]; do
  case "$1" in
    --list-available)
      declare -a installed=()
      detect_available_agents installed
      echo -e "${BOLD}Status dos CLIs do Conselho de Seniores nesta máquina:${RESET}"
      for cand in "${ALL_KNOWN_AGENTS[@]}"; do
        if command -v "$cand" >/dev/null 2>&1; then
          echo -e "  ${GREEN}● $cand${RESET} -> $(command -v "$cand")"
        else
          echo -e "  ${YELLOW}○ $cand${RESET} -> não encontrado no PATH (opcional)"
        fi
      done
      echo -e "\n${BOLD}Quórum disponível:${RESET} ${#installed[@]} de ${#ALL_KNOWN_AGENTS[@]} modelos ativos."
      exit 0
      ;;
    --all)
      # Será populado dinamicamente pelos instalados
      REQUESTED_AGENTS=()
      shift
      ;;
    --agent)
      if [[ -z "${2:-}" ]]; then
        echo -e "${RED}Erro: --agent requer um nome de agente.${RESET}" >&2
        exit 1
      fi
      REQUESTED_AGENTS+=("$2")
      shift 2
      ;;
    --diff)
      USE_DIFF=true
      shift
      ;;
    --prompt)
      if [[ -z "${2:-}" ]]; then
        echo -e "${RED}Erro: --prompt requer um argumento de texto.${RESET}" >&2
        exit 1
      fi
      USER_PROMPT="$2"
      shift 2
      ;;
    --file)
      if [[ -z "${2:-}" || ! -f "$2" ]]; then
        echo -e "${RED}Erro: --file requer um arquivo existente.${RESET}" >&2
        exit 1
      fi
      PROMPT_FILE="$2"
      shift 2
      ;;
    --timeout)
      TIMEOUT_SECS="${2:-90}"
      shift 2
      ;;
    --output-dir)
      OUTPUT_DIR="$2"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    -h|--help)
      usage
      ;;
    *)
      echo -e "${RED}Opção desconhecida: $1${RESET}" >&2
      usage
      ;;
  esac
done

# 1. Detecção dinâmica de quórum
declare -a DETECTED_AGENTS=()
detect_available_agents DETECTED_AGENTS

if [[ ${#DETECTED_AGENTS[@]} -eq 0 ]]; then
  echo -e "${YELLOW}Aviso: Nenhum dos 6 CLIs do Conselho (${ALL_KNOWN_AGENTS[*]}) foi encontrado no PATH.${RESET}"
  echo -e "O Conselho de Seniores é um add-on opcional de visão ampliada do desenvolvedor."
  echo -e "O harness CEH continua operando normalmente com suas verificações nativas e linters."
  exit 0
fi

# Formação da bancada ativa
TARGET_AGENTS=()
if [[ ${#REQUESTED_AGENTS[@]} -eq 0 ]]; then
  # Modo padrão: usa todos os que estiverem disponíveis na máquina
  TARGET_AGENTS=("${DETECTED_AGENTS[@]}")
else
  # O usuário pediu agentes específicos: valida se estão instalados
  for req in "${REQUESTED_AGENTS[@]}"; do
    if command -v "$req" >/dev/null 2>&1; then
      TARGET_AGENTS+=("$req")
    else
      echo -e "${YELLOW}Aviso: Agente solicitado '$req' não está instalado nesta máquina. Pulando.${RESET}"
    fi
  done
fi

if [[ ${#TARGET_AGENTS[@]} -eq 0 ]]; then
  echo -e "${RED}Erro: Nenhum dos agentes solicitados está disponível no PATH.${RESET}"
  echo -e "Modelos ativos nesta máquina: ${GREEN}${DETECTED_AGENTS[*]}${RESET}"
  exit 1
fi

# Diretório de saída padrão
if [[ -z "$OUTPUT_DIR" ]]; then
  TIMESTAMP="$(date +'%Y%m%d_%H%M%S')"
  OUTPUT_DIR="$REPO_ROOT/docs/temp_implementation/conselho/$TIMESTAMP"
fi
mkdir -p "$OUTPUT_DIR"

# Coleta de contexto
CONTEXT_PAYLOAD=""

if [[ -n "$PROMPT_FILE" ]]; then
  CONTEXT_PAYLOAD+="=== DOCUMENTO SOB AVALIAÇÃO ($(basename "$PROMPT_FILE")) ===\n"
  CONTEXT_PAYLOAD+="$(cat "$PROMPT_FILE")\n\n"
fi

if [[ -n "$USER_PROMPT" ]]; then
  CONTEXT_PAYLOAD+="=== INSTRUÇÃO ESPECÍFICA DO DEVELOPER ===\n"
  CONTEXT_PAYLOAD+="$USER_PROMPT\n\n"
fi

if [[ "$USE_DIFF" == true ]]; then
  CONTEXT_PAYLOAD+="=== TRIPÉ DE GIT DIFF (INSPEÇÃO ADVERSARIAL) ===\n"
  
  DIFF_UNSTAGED="$(git -C "$REPO_ROOT" diff 2>/dev/null || true)"
  DIFF_STAGED="$(git -C "$REPO_ROOT" diff --cached 2>/dev/null || true)"
  DIFF_HEAD="$(git -C "$REPO_ROOT" diff HEAD~1..HEAD 2>/dev/null || true)"

  if [[ -n "$DIFF_UNSTAGED" ]]; then
    CONTEXT_PAYLOAD+="--- [1/3] WORKING TREE (UNSTAGED) ---\n$DIFF_UNSTAGED\n\n"
  fi
  if [[ -n "$DIFF_STAGED" ]]; then
    CONTEXT_PAYLOAD+="--- [2/3] STAGING (CACHED) ---\n$DIFF_STAGED\n\n"
  fi
  if [[ -n "$DIFF_HEAD" ]]; then
    CONTEXT_PAYLOAD+="--- [3/3] ÚLTIMO COMMIT (HEAD~1..HEAD) ---\n$DIFF_HEAD\n\n"
  fi

  if [[ -z "$DIFF_UNSTAGED" && -z "$DIFF_STAGED" && -z "$DIFF_HEAD" ]]; then
    CONTEXT_PAYLOAD+="--- WORKING TREE TOTALMENTE LIMPO (ZERO DIFFS OBSERVADOS) ---\n\n"
  fi
fi

if [[ -z "$CONTEXT_PAYLOAD" ]]; then
  CONTEXT_PAYLOAD="Avaliar o estado atual da branch $(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'desconhecida') e o último commit $(git -C "$REPO_ROOT" rev-parse --short HEAD 2>/dev/null || echo 'desconhecido')."
fi

get_agent_role() {
  local agent="$1"
  case "$agent" in
    claude)
      echo "REVISOR SENIOR (Audit, Ponytail Lead & Semântica) — Especialista em minimalismo (anti-overengineering), auditar claims contra evidências (OBSERVED), clareza de contratos e caça de regressões e edge cases."
      ;;
    codex)
      echo "ARQUITETO DE LÓGICA FORMAL & ALGORITMOS — Especialista em raciocínio formal profundo, tipagem estrita, invariantes matemáticos, estruturas de dados e análise de concorrência/deadlocks."
      ;;
    muse)
      echo "ENGENHEIRO DE SISTEMAS & PORTABILIDADE — Especialista em arquitetura POSIX, portabilidade entre Linux/macOS/BSD, segurança de runtime de shell e performance de baixo nível."
      ;;
    hermes)
      echo "ENGENHEIRO DE TOOLING & CONFIABILIDADE DE AGENTE — Especialista em integrações MCP, ecossistemas de agentes, confiabilidade de gateways e automação determinística de tarefas."
      ;;
    agy)
      echo "GUARDIÃO DO HARNESS & SAFETY GATE — Especialista nas regras do CEH, integridade da matriz de ambientes (DEV/HML/PRD), blast radius mínimo e invariantes de comandos destrutivos."
      ;;
    agent)
      echo "REVISOR CIRÚRGICO DE DIFF & ERGONOMIA — Especialista em usabilidade prática de código, higiene de diff, aderência a convenções da IDE e ergonomia para o desenvolvedor."
      ;;
    *)
      echo "CONSELHEIRO TÉCNICO SÊNIOR"
      ;;
  esac
}

build_agent_prompt() {
  local agent="$1"
  local role="$2"
  
  cat <<EOF
Você está deliberando como integrante do CONSELHO DE SENIORES do CLEARER Engineering Harness (CEH).
Sua identidade e delegação nesta sessão:
$role

OBJETO DE AVALIAÇÃO:
$CONTEXT_PAYLOAD

INSTRUÇÕES DO PROTOCOLO SYSTEM ONE:
1. Avalie o material estritamente sob o ponto de vista da sua delegação técnica.
2. Não produza enrolação, preâmbulos protocolares ou elogios.
3. Responda obrigatoriamente preenchendo o contrato de saída abaixo:

--- CONTRATO DE SAÍDA MANDATÓRIO ---
VEREDITO: [HOMOLOGADO | RESSALVAS | REJEITADO]
CERTEZA: [número entre 0.0 e 1.0 fundamentado em evidência física]
ANALISE_ESPECIALIZADA:
<análise técnica cirúrgica detalhando pontos fortes ou vulnerabilidades sob sua ótica>
RISCOS_IDENTIFICADOS:
<lista de riscos reais ou 'Nenhum risco observado'>
RECOMENDACAO_FINAL:
<ação prática direta e verificável recomendada>
------------------------------------
EOF
}

echo -e "${BOLD}${CYAN}======================================================================${RESET}"
echo -e "${BOLD}${CYAN}   CLEARER ENGINEERING HARNESS — CONSELHO DE SENIORES                 ${RESET}"
echo -e "${BOLD}${CYAN}   (Add-on Opcional de Apoio à Decisão Multi-Modelo)                  ${RESET}"
echo -e "${BOLD}${CYAN}======================================================================${RESET}"
echo -e "Data/Hora:       $(date -Iseconds)"
echo -e "Repositório:     $(basename "$REPO_ROOT")"
echo -e "Branch:          $(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'N/A')"
echo -e "Commit:          $(git -C "$REPO_ROOT" rev-parse --short HEAD 2>/dev/null || echo 'N/A')"
echo -e "Quórum Ativo:    ${GREEN}${#TARGET_AGENTS[@]} de ${#ALL_KNOWN_AGENTS[@]} modelos disponíveis${RESET} (${TARGET_AGENTS[*]})"
echo -e "Ata de Saída:    $OUTPUT_DIR/ata_conselho.md"
echo -e "${CYAN}----------------------------------------------------------------------${RESET}"

printf "%b" "$CONTEXT_PAYLOAD" > "$OUTPUT_DIR/contexto_avaliado.txt"

declare -A AGENT_VERDICTS
declare -A AGENT_CONFIDENCE
declare -A AGENT_STATUS

for agent in "${TARGET_AGENTS[@]}"; do
  role="$(get_agent_role "$agent")"
  prompt="$(build_agent_prompt "$agent" "$role")"
  prompt_file="$OUTPUT_DIR/prompt_${agent}.txt"
  resp_file="$OUTPUT_DIR/parecer_${agent}.md"
  
  printf "%s\n" "$prompt" > "$prompt_file"

  echo -e "\n${BOLD}[CONSELHEIRO ATIVO] $agent${RESET}"
  echo -e "Delegação: $role"

  if [[ "$DRY_RUN" == true ]]; then
    echo -e "${BLUE}[DRY-RUN] Comando que seria executado para $agent:${RESET}"
    case "$agent" in
      claude) echo "claude -p \"<prompt>\" --permission-mode plan" ;;
      codex)  echo "codex exec \"<prompt>\"" ;;
      muse)   echo "muse exec \"<prompt>\"" ;;
      hermes) echo "hermes chat -q \"<prompt>\" --oneshot -Q" ;;
      agy)    echo "agy -p \"<prompt>\" --mode plan" ;;
      agent)  echo "agent -p \"<prompt>\" --mode plan" ;;
    esac
    AGENT_STATUS["$agent"]="DRY_RUN"
    AGENT_VERDICTS["$agent"]="SIMULADO"
    AGENT_CONFIDENCE["$agent"]="1.0"
    continue
  fi

  echo -e "Disparando consulta não-interativa (timeout: ${TIMEOUT_SECS}s)..."
  AGENT_STATUS["$agent"]="OK"

  set +e
  case "$agent" in
    claude)
      timeout "$TIMEOUT_SECS" claude -p "$prompt" --permission-mode plan > "$resp_file" 2>&1
      exit_code=$?
      ;;
    codex)
      timeout "$TIMEOUT_SECS" codex exec "$prompt" > "$resp_file" 2>&1
      exit_code=$?
      ;;
    muse)
      timeout "$TIMEOUT_SECS" muse exec "$prompt" > "$resp_file" 2>&1
      exit_code=$?
      ;;
    hermes)
      timeout "$TIMEOUT_SECS" hermes chat -q "$prompt" --oneshot -Q > "$resp_file" 2>&1
      exit_code=$?
      ;;
    agy)
      timeout "$TIMEOUT_SECS" agy -p "$prompt" --mode plan > "$resp_file" 2>&1
      exit_code=$?
      ;;
    agent)
      timeout "$TIMEOUT_SECS" agent -p "$prompt" --mode plan > "$resp_file" 2>&1
      exit_code=$?
      ;;
    *)
      echo "Agente desconhecido: $agent" > "$resp_file"
      exit_code=1
      ;;
  esac
  set -e

  if [[ $exit_code -eq 124 ]]; then
    echo -e "${RED}Falha: $agent excedeu o timeout de ${TIMEOUT_SECS}s.${RESET}"
    AGENT_STATUS["$agent"]="TIMEOUT"
    AGENT_VERDICTS["$agent"]="TIMEOUT"
    AGENT_CONFIDENCE["$agent"]="0.0"
  elif [[ $exit_code -ne 0 ]]; then
    echo -e "${YELLOW}Aviso: $agent finalizou com código $exit_code (verifique $resp_file).${RESET}"
    AGENT_STATUS["$agent"]="ERRO_EXECUCAO"
    AGENT_VERDICTS["$agent"]="INCONCLUSIVO"
    AGENT_CONFIDENCE["$agent"]="0.0"
  else
    # Extrai a última linha de veredito/certeza (evitando capturar o template do prompt repetido pelo modelo)
    verd="$(grep -E '^VEREDITO:' "$resp_file" | tail -n1 | sed -E 's/VEREDITO:[[:space:]]*//' | tr -d '\r' || true)"
    cert="$(grep -E '^CERTEZA:' "$resp_file" | tail -n1 | sed -E 's/CERTEZA:[[:space:]]*//' | tr -d '\r' || true)"

    # Se contiver colchetes ou pipe (template de formulário), invalida
    if [[ "$verd" =~ [\[\|] ]]; then
      verd=""
    fi
    if [[ "$cert" =~ [\[\|] ]]; then
      cert=""
    fi

    if [[ -z "$verd" ]]; then
      if grep -qi "HOMOLOGADO" "$resp_file"; then verd="HOMOLOGADO";
      elif grep -qi "RESSALVAS" "$resp_file"; then verd="RESSALVAS";
      elif grep -qi "REJEITADO" "$resp_file"; then verd="REJEITADO";
      else verd="INDEFINIDO"; fi
    fi

    [[ -z "$cert" ]] && cert="0.80"

    AGENT_VERDICTS["$agent"]="$verd"
    AGENT_CONFIDENCE["$agent"]="$cert"
    echo -e "${GREEN}Concluído: Veredito: $verd | Certeza: $cert${RESET}"
  fi
done

ATA_FILE="$OUTPUT_DIR/ata_conselho.md"

cat <<EOF > "$ATA_FILE"
# Ata de Deliberação do Conselho de Seniores (CEH)
> *Add-on Opcional de Apoio à Decisão Multi-Modelo*

**Data/Hora:** $(date -Iseconds)  
**Repositório:** \`$(basename "$REPO_ROOT")\`  
**Branch:** \`$(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'N/A')\`  
**Commit:** \`$(git -C "$REPO_ROOT" rev-parse --short HEAD 2>/dev/null || echo 'N/A')\`  
**Quórum Ativo da Sessão:** ${#TARGET_AGENTS[@]} membro(s) (${TARGET_AGENTS[*]})

---

## 1. Quadro Geral de Deliberação

| Conselheiro | Ecossistema / Especialidade | Status | Veredito Emitido | Nível de Certeza | Parecer Detalhado |
|---|---|---|---|---|---|
EOF

TOTAL_HOMOLOGADO=0
TOTAL_RESSALVAS=0
TOTAL_REJEITADO=0
TOTAL_VOTANTES=0

for agent in "${TARGET_AGENTS[@]}"; do
  status="${AGENT_STATUS[$agent]:-UNKNOWN}"
  verdict="${AGENT_VERDICTS[$agent]:-N/A}"
  cert="${AGENT_CONFIDENCE[$agent]:-0.0}"
  role="$(get_agent_role "$agent")"

  clean_verdict="$verdict"
  if [[ "$clean_verdict" =~ [\[\|] ]]; then
    clean_verdict="INDEFINIDO"
  fi

  case "$clean_verdict" in
    *RESSALVAS*)  ((TOTAL_RESSALVAS++)) || true; ((TOTAL_VOTANTES++)) || true ;;
    *HOMOLOGADO*) ((TOTAL_HOMOLOGADO++)) || true; ((TOTAL_VOTANTES++)) || true ;;
    *REJEITADO*)  ((TOTAL_REJEITADO++)) || true; ((TOTAL_VOTANTES++)) || true ;;
  esac

  echo "| **\`$agent\`** | $role | \`$status\` | **$verdict** | $cert | [Ver Parecer](parecer_${agent}.md) |" >> "$ATA_FILE"
done

VEREDITO_COLETIVO="HOMOLOGADO"
if [[ $TOTAL_REJEITADO -gt 0 ]]; then
  VEREDITO_COLETIVO="REJEITADO"
elif [[ $TOTAL_RESSALVAS -gt 0 ]]; then
  VEREDITO_COLETIVO="HOMOLOGADO COM RESSALVAS"
elif [[ $TOTAL_VOTANTES -eq 0 ]]; then
  VEREDITO_COLETIVO="INCONCLUSIVO (NENHUM VOTO COMPUTADO)"
fi

cat <<EOF >> "$ATA_FILE"

---

## 2. Veredito Coletivo da Banca

### **Resultado da Deliberação: $VEREDITO_COLETIVO**

- **Votos Favoráveis (Homologado):** $TOTAL_HOMOLOGADO / $TOTAL_VOTANTES
- **Votos com Ressalvas:** $TOTAL_RESSALVAS / $TOTAL_VOTANTES
- **Votos Desfavoráveis (Rejeitado):** $TOTAL_REJEITADO / $TOTAL_VOTANTES

---

## 3. Despacho Soberano do Desenvolvedor

Esta ata consolida pareceres técnicos de apoio para oferecer uma perspectiva 360º de alto nível. A decisão final, aprovação de handoffs e direção da arquitetura pertencem exclusivamente ao Desenvolvedor (\`nandodev\`).
EOF

echo -e "\n${BOLD}${GREEN}======================================================================${RESET}"
echo -e "${BOLD}${GREEN}   DELIBERAÇÃO CONCLUÍDA — RESULTADO: $VEREDITO_COLETIVO              ${RESET}"
echo -e "${BOLD}${GREEN}======================================================================${RESET}"
echo -e "Ata consolidada gerada em:"
echo -e "${BOLD}$ATA_FILE${RESET}\n"
