---
name: clearer-bugfix
description: >-
  Root-Cause First bug fixing workflow: SYMPTOM -> REPRODUCTION -> OBSERVATION ->
  HYPOTHESIS -> EVIDENCE -> ROOT CAUSE -> REGRESSION TEST -> MINIMAL FIX -> TEST -> REVIEW.
---

# CLEARER Root-Cause First Bugfix Workflow

Esta skill assegura que nenhuma correção de bug seja aplicada às cegas ou trate apenas sintomas superficiais, conduzindo a investigação, reprodução, fix cirúrgico e testes em fluxo contínuo.

> [!IMPORTANT]
> **No reproduction / evidence, no confident root-cause claim.**
> Entenda e evidencie a causa raiz antes de aplicar o patch. O ciclo é executado de ponta a ponta em uma única rodada.

---

## Fluxo de Execução Contínua (Single-Turn End-to-End)

```text
SYMPTOM → REPRODUCTION → OBSERVATION → HYPOTHESIS → ROOT CAUSE → REGRESSION TEST → MINIMAL FIX → TEST & AUTO-HEAL → REVIEW → REPORT
```

---

### Passo 1: Captura do Sintoma (Symptom)
- Qual é o comportamento incorreto observado?
- Qual é o comportamento esperado?
- Quais são os logs de erro, stack traces ou mensagens observadas?

### Passo 2: Reprodução do Erro (Reproduction)
- Reproduza o erro através de um teste automatizado, comando CLI ou chamada controlada.
- Se o erro for intermitente ou depender de estado externo, documente o cenário de reprodução.

### Passo 3: Hipótese & Evidência (Hypothesis & Evidence)
- Formule hipóteses e teste-as contra o código real e dados observados (`OBSERVED`).
- Não faça suposições sem conferir os arquivos afetados.

### Passo 4: Causa Raiz Determinística (Root Cause)
- Localize a linha, lógica ou condição exata que gera a falha.
- Se a causa não for conclusivamente demonstrada, marque como `INFERRED` até comprovar no teste.

### Passo 5: Teste de Regressão (Regression Test)
- Escreva ou adapte um teste que falhe comprovadamente antes da correção (**Red**).

### Passo 6: Correção Cirúrgica de Alto Nível (Minimal Fix)
- Aplique o menor patch possível com tipagem estrita e arquitetura defensiva para resolver a causa raiz.
- Preserve contratos e interfaces públicas.

### Passo 7: Validação & Auto-Reparo Fundamentado (Test & Auto-Heal)
- Execute o teste de regressão e toda a suíte afetada:
  ```bash
  bash scripts/test-runner.sh
  ```
- **Protocolo de Auto-Reparo**: Se o teste falhar, realize **1 iteração de diagnóstico e ajuste cirúrgico** baseando-se no stack trace. Se ainda falhar, emita o relatório com o diagnóstico objetivo e solicite alinhamento.

### Passo 8: Revisão do Diff e Auditoria (Review & Report)
- Execute a auditoria do diff:
  ```bash
  bash scripts/diff-audit.sh
  ```
- Emita a entrega final com o Response Contract completo (RESULT, CHANGES, EVIDENCE, TESTS, CONFIDENCE).

