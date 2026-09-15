#!/usr/bin/env bash
# ==============================================================================
# evals/run.sh - Deterministic Smoke-Eval Runner for CEH Safety Gate
# Protocolo de Avaliação de Falsificabilidade e Robustez de Infraestrutura
# ==============================================================================
set -u

EVALS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$EVALS_DIR/.." && pwd)"
GATE_SCRIPT="$REPO_ROOT/clearer-engineering/scripts/safety-gate.py"

CRITERIA_FILE="$EVALS_DIR/CRITERIA.md"
START_TIME=$(date +%s)
MAX_WALL_SECONDS=60

CRITERIA_PASSED=0
TOTAL_CRITERIA=5

COLOR_RESET="\033[0m"
COLOR_GREEN="\033[0;32m"
COLOR_RED="\033[0;31m"
COLOR_YELLOW="\033[0;33m"
COLOR_CYAN="\033[0;36m"
COLOR_BOLD="\033[1m"

log_info()  { echo -e "${COLOR_CYAN}[INFO]${COLOR_RESET} $1"; }
log_pass()  { echo -e "${COLOR_GREEN}[PASS]${COLOR_RESET} $1"; }
log_fail()  { echo -e "${COLOR_RED}[FAIL]${COLOR_RESET} $1"; }
log_warn()  { echo -e "${COLOR_YELLOW}[WARN]${COLOR_RESET} $1"; }

# ------------------------------------------------------------------------------
# 0. Verificação Prévia de Integridade
# ------------------------------------------------------------------------------
if [ ! -f "$CRITERIA_FILE" ]; then
    log_fail "INFRA-FAIL: Arquivo de critérios obrigatório não encontrado: $CRITERIA_FILE"
    exit 1
fi

echo "======================================================================"
echo -e "${COLOR_BOLD}   CLEARER Engineering Harness (CEH) — Smoke-Eval Runner${COLOR_RESET}"
echo "======================================================================"
echo "Repositório:   $REPO_ROOT"
echo "Safety Gate:   $GATE_SCRIPT"
echo "Critérios:     $CRITERIA_FILE"
echo "Timestamp:     $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "----------------------------------------------------------------------"

# ------------------------------------------------------------------------------
# Função para rodar uma fixture contra um script alvo sob ambiente isolado
# ------------------------------------------------------------------------------
execute_fixture() {
    local target_script="$1"
    local env_name="$2"
    local command_str="$3"
    local expected_decision="$4"
    local expected_exit="$5"

    if [ ! -f "$target_script" ]; then
        echo "INFRA-FAIL: Script alvo ausente: $target_script"
        return 127
    fi

    # Execução sob ambiente isolado (env -i) preservando apenas PATH e HOME mínimos
    local output
    local status=0
    output=$(env -i PATH="$PATH" HOME="$HOME" python3 "$target_script" --check "$command_str" --env "$env_name" 2>&1) || status=$?

    local decision
    decision=$(echo "$output" | grep -o '"decision": "[^"]*"' | head -n 1 | cut -d'"' -f4 || true)

    if [ "$decision" = "$expected_decision" ] && [ "$status" -eq "$expected_exit" ]; then
        return 0
    else
        return 1
    fi
}

# ------------------------------------------------------------------------------
# Execução da Bateria Completa de Fixtures Canônicas
# ------------------------------------------------------------------------------
run_suite() {
    local target_script="$1"
    local label="$2"
    local suite_failed=0

    # 1. Benigno
    execute_fixture "$target_script" "development" "git status" "allow" 0 || suite_failed=$((suite_failed + 1))
    
    # 2. Destrutivo em DEV (permitido com aviso)
    execute_fixture "$target_script" "development" "php artisan migrate:fresh" "allow" 0 || suite_failed=$((suite_failed + 1))
    
    # 3. Destrutivo em STAGING (exige confirmação com 2 alertas)
    execute_fixture "$target_script" "staging" "php artisan migrate:fresh" "ask" 1 || suite_failed=$((suite_failed + 1))
    
    # 4. Destrutivo em PRODUÇÃO (bloqueado incondicionalmente)
    execute_fixture "$target_script" "production" "php artisan migrate:fresh" "deny" 2 || suite_failed=$((suite_failed + 1))
    
    # 5. Push force forma longa em PRODUÇÃO
    execute_fixture "$target_script" "production" "git push origin main --force" "deny" 2 || suite_failed=$((suite_failed + 1))
    
    # 6. Push force forma curta (-f) em PRODUÇÃO (par de equivalência)
    execute_fixture "$target_script" "production" "git push origin main -f" "deny" 2 || suite_failed=$((suite_failed + 1))
    
    # 7. Catastrófico em DEV (deve ser bloqueado sempre)
    execute_fixture "$target_script" "development" "rm -rf /" "deny" 2 || suite_failed=$((suite_failed + 1))

    return $suite_failed
}

# Snapshot do estado do git antes de qualquer manipulação ou deriva
GIT_STATE_INITIAL=$(git -C "$REPO_ROOT" status --porcelain)

# ------------------------------------------------------------------------------
# CRITÉRIO 1: Baseline 3x Verde Consecutivo
# ------------------------------------------------------------------------------
echo -e "\n${COLOR_BOLD}[1/5] Avaliando Critério 1: Baseline 3x Verde Consecutivo...${COLOR_RESET}"
BASELINE_PASSED=true

for iter in 1 2 3; do
    ITER_START=$(date +%s%N)
    if run_suite "$GATE_SCRIPT" "baseline-$iter"; then
        ITER_END=$(date +%s%N)
        ELAPSED_MS=$(( (ITER_END - ITER_START) / 1000000 ))
        echo "  • Corrida $iter/3: PASS (${ELAPSED_MS}ms)"
    else
        echo "  • Corrida $iter/3: FAIL"
        BASELINE_PASSED=false
        break
    fi
done

if [ "$BASELINE_PASSED" = true ]; then
    log_pass "Critério 1: Baseline 3x consecutivo aprovado."
    CRITERIA_PASSED=$((CRITERIA_PASSED + 1))
else
    log_fail "Critério 1: Falha no baseline das fixtures canônicas."
fi

# ------------------------------------------------------------------------------
# CRITÉRIO 2: Deriva A — Falha de Infraestrutura (Fail-Closed)
# ------------------------------------------------------------------------------
echo -e "\n${COLOR_BOLD}[2/5] Avaliando Critério 2: Deriva A (Fail-Closed por Infra Ausente)...${COLOR_RESET}"
MISSING_GATE_PATH="/tmp/ceh-nonexistent-safety-gate-$$.py"

# Tentativa de executar com script ausente
DERIVA_A_STATUS=0
execute_fixture "$MISSING_GATE_PATH" "production" "git push origin main --force" "deny" 2 || DERIVA_A_STATUS=$?

if [ "$DERIVA_A_STATUS" -ne 0 ]; then
    log_pass "Critério 2: Deriva A aprovada (INFRA-FAIL detectado com saída não-zero, fail-closed)."
    CRITERIA_PASSED=$((CRITERIA_PASSED + 1))
else
    log_fail "Critério 2: Deriva A reprovada (Falso positivo emitido quando infraestrutura estava ausente!)."
fi

# ------------------------------------------------------------------------------
# CRITÉRIO 3: Deriva B — Mutação Semântica Silenciosa
# ------------------------------------------------------------------------------
echo -e "\n${COLOR_BOLD}[3/5] Avaliando Critério 3: Deriva B (Detecção de Mutação Semântica)...${COLOR_RESET}"
MUTANT_TMP_DIR=$(mktemp -d /tmp/ceh-eval-mutant-XXXXXX)
MUTANT_SCRIPT="$MUTANT_TMP_DIR/safety-gate-mutant.py"

# Criar mutação cirúrgica: remover o reconhecimento de 'prod' e 'production' no normalize_env
# Substitui '["prod", "production", "prd", "live"]' por '["live_only_token"]'
sed 's/\["prod", "production", "prd", "live"\]/\["live_only_token"\]/g' "$GATE_SCRIPT" > "$MUTANT_SCRIPT"

# A fixture de produção (php artisan migrate:fresh com env=production) deve falhar na checagem
# pois o mutante não a classifica mais como produção e degrada para development (allow/exit 0)
DERIVA_B_CAPTURED=false
if ! execute_fixture "$MUTANT_SCRIPT" "production" "php artisan migrate:fresh" "deny" 2; then
    DERIVA_B_CAPTURED=true
fi

# Limpar o mutante temporário
rm -rf "$MUTANT_TMP_DIR"

if [ "$DERIVA_B_CAPTURED" = true ]; then
    log_pass "Critério 3: Deriva B aprovada (Erosão de regra capturada pelo runner sem crash)."
    CRITERIA_PASSED=$((CRITERIA_PASSED + 1))
else
    log_fail "Critério 3: Deriva B reprovada (Mutação semântica passou despercebida!)."
fi

# ------------------------------------------------------------------------------
# CRITÉRIO 4: Restauração Limpa (Byte-a-Byte)
# ------------------------------------------------------------------------------
echo -e "\n${COLOR_BOLD}[4/5] Avaliando Critério 4: Restauração Limpa (Byte-a-Byte)...${COLOR_RESET}"

# Verifica se o estado do repositório é exatamente o mesmo de antes das derivas
GIT_STATE_FINAL=$(git -C "$REPO_ROOT" status --porcelain)

RESTORATION_RUN_OK=false
if run_suite "$GATE_SCRIPT" "restoration-check"; then
    RESTORATION_RUN_OK=true
fi

if [ "$GIT_STATE_INITIAL" = "$GIT_STATE_FINAL" ] && [ "$RESTORATION_RUN_OK" = true ]; then
    log_pass "Critério 4: Restauração limpa aprovada (Zero resíduos de eval, suíte 100% verde)."
    CRITERIA_PASSED=$((CRITERIA_PASSED + 1))
else
    log_fail "Critério 4: Falha na restauração limpa (Resíduos pós-deriva detectados ou suíte quebrada)."
fi

# ------------------------------------------------------------------------------
# CRITÉRIO 5: Teto de Tempo de Parede (< 60s)
# ------------------------------------------------------------------------------
echo -e "\n${COLOR_BOLD}[5/5] Avaliando Critério 5: Teto de Tempo de Parede (< ${MAX_WALL_SECONDS}s)...${COLOR_RESET}"
END_TIME=$(date +%s)
TOTAL_WALL_TIME=$((END_TIME - START_TIME))

if [ "$TOTAL_WALL_TIME" -lt "$MAX_WALL_SECONDS" ]; then
    log_pass "Critério 5: Tempo de parede aprovado (${TOTAL_WALL_TIME}s < ${MAX_WALL_SECONDS}s)."
    CRITERIA_PASSED=$((CRITERIA_PASSED + 1))
else
    log_fail "Critério 5: Teto de tempo excedido (${TOTAL_WALL_TIME}s >= ${MAX_WALL_SECONDS}s)."
fi

# ------------------------------------------------------------------------------
# Tabela de Veredito Final
# ------------------------------------------------------------------------------
echo "----------------------------------------------------------------------"
echo -e "${COLOR_BOLD}RESUMO DA AVALIAÇÃO DE CRITÉRIOS (CEH SMOKE-EVAL):${COLOR_RESET}"
echo "  Critérios Atendidos: $CRITERIA_PASSED de $TOTAL_CRITERIA"
echo "  Tempo Total:         ${TOTAL_WALL_TIME}s"
echo "----------------------------------------------------------------------"

if [ "$CRITERIA_PASSED" -eq "$TOTAL_CRITERIA" ]; then
    echo -e "${COLOR_GREEN}${COLOR_BOLD}VEREDITO FINAL: APROVA (5/5 Critérios Atendidos)${COLOR_RESET}"
    echo "Harness validado contra falsificação e degradação de infraestrutura."
    exit 0
else
    echo -e "${COLOR_RED}${COLOR_BOLD}VEREDITO FINAL: DESCARTA ($CRITERIA_PASSED/$TOTAL_CRITERIA Critérios Atendidos)${COLOR_RESET}"
    echo "Harness falhou no protocolo de falsificabilidade. Exige ADR de descarte."
    exit 1
fi
