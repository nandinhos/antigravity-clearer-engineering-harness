---
name: clearer-bugfix
description: >-
  Root-Cause First bug fixing workflow: SYMPTOM -> REPRODUCTION -> OBSERVATION ->
  HYPOTHESIS -> EVIDENCE -> ROOT CAUSE -> REGRESSION TEST -> MINIMAL FIX -> TEST -> REVIEW.
---

# CLEARER Root-Cause First Bugfix Workflow

Esta skill assegura que nenhuma correção de bug seja aplicada às cegas ou trate apenas sintomas superficiais.

> [!IMPORTANT]
> **No reproduction / evidence, no confident root-cause claim.**
> Nunca proponha um patch sem antes entender e evidenciar a causa raiz do problema.

---

## Fluxo de Execução

```text
SYMPTOM → REPRODUCTION → OBSERVATION → HYPOTHESIS → EVIDENCE → ROOT CAUSE → REGRESSION TEST → MINIMAL FIX → TEST → REVIEW
```

### Passo 1: Captura do Sintoma (Symptom)
- Qual é o comportamento incorreto observado?
- Qual é o comportamento esperado?
- Quais são os logs de erro, stack traces ou mensagens reportadas?

### Passo 2: Reprodução do Erro (Reproduction)
- Reproduza o erro através de um teste automatizado, comando CLI ou chamada controlada.
- Se o erro for intermitente ou depender de estado externo, documente o cenário de reprodução.

### Passo 3: Levantamento de Hipóteses e Evidências (Hypothesis & Evidence)
- Formule hipóteses e teste-as contra o código real e dados observados.
- Separe fatos (`OBSERVED`) de suposições (`INFERRED`).

### Passo 4: Identificação da Causa Raiz (Root Cause)
- Localize a linha, lógica ou condição exata que gera a falha.
- Se a causa não for conclusivamente demonstrada, marque o diagnóstico como preliminar.

### Passo 5: Teste de Regressão (Regression Test)
- Escreva ou adapte um teste que falhe comprovadamente antes do fix (Red).

### Passo 6: Correção Mínima (Minimal Fix)
- Aplique o menor patch possível para resolver a causa raiz com blast radius mínimo.

### Passo 7: Validação e Testes (Test)
- Execute o teste de regressão e toda a suíte afetada:
  ```bash
  bash scripts/test-runner.sh
  ```
- Confirme que o teste agora passa (Green) sem quebrar testes existentes.

### Passo 8: Revisão do Diff e Auditoria (Review & Report)
- Execute a auditoria do diff:
  ```bash
  bash scripts/diff-audit.sh
  ```
- Emita o relatório final de evidências no padrão CEH.
