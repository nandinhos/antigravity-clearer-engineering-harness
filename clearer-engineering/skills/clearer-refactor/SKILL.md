---
name: clearer-refactor
description: >-
  Safe code refactoring workflow: establish behavioral baseline and tests,
  apply structural improvements, compare behavior, and audit diffs without breaking contracts.
---

# CLEARER Safe Refactoring Workflow

Esta skill conduz refatorações com segurança garantida através de baseline prévio de testes e preservação estrita de contratos.

---

## Fluxo de Execução

```text
BASELINE & CONTRACTS → TESTS BASELINE → REFACTOR → TESTS RE-RUN → BEHAVIOR COMPARISON → DIFF AUDIT
```

### Passo 1: Estabelecer Baseline e Contratos
1. Localize a área do código a ser refatorada.
2. Identifique os contratos públicos (assinaturas de métodos, interfaces, retorno de APIs, tabelas).
3. Verifique se há cobertura de testes existente cobrindo o comportamento atual.

### Passo 2: Execução de Testes Baseline
- Execute a suíte de testes antes de qualquer edição:
  ```bash
  bash scripts/test-runner.sh
  ```
- Garanta que a suíte esteja 100% verde antes de iniciar as modificações.

### Passo 3: Refatoração Estrutural (Refactor)
- Aplique melhorias de legibilidade, desacoplamento ou desempenho sem alterar o comportamento externo.
- Não misture novas features ou mudanças de regra de negócio durante o refactor.

### Passo 4: Re-execução de Testes e Comparação
- Execute novamente a suíte de testes:
  ```bash
  bash scripts/test-runner.sh
  ```
- Confirme que todos os testes continuam passando exatamente como no baseline.

### Passo 5: Auditoria do Diff (Diff Audit)
- Execute a verificação de integridade:
  ```bash
  bash scripts/diff-audit.sh
  ```
- Confirme que nenhuma alteração não intencional ou quebra de contrato foi introduzida.

### Passo 6: Relatório Final
- Emita o relatório no padrão CEH.
