---
name: clearer-refactor
description: >-
  Safe code refactoring workflow: establish behavioral baseline and tests,
  apply structural improvements, compare behavior, and audit diffs without breaking contracts.
---

# CLEARER Safe Refactoring Workflow

Esta skill conduz refatorações com segurança garantida através de baseline prévio de testes, preservação estrita de contratos e execução contínua de alto nível.

---

## Fluxo de Execução Contínua (Single-Turn End-to-End)

```text
BASELINE & CONTRACTS → TESTS BASELINE → REFACTOR → TESTS RE-RUN → DIFF AUDIT → REPORT
```

---

### Passo 1: Estabelecer Baseline e Contratos
1. Localize a área do código a ser refatorada.
2. Identifique os contratos públicos (assinaturas de métodos, interfaces, retorno de APIs, schemas).
3. Verifique a cobertura de testes existente cobrindo o comportamento atual.

### Passo 2: Execução de Testes Baseline
- Execute a suíte de testes antes de qualquer edição:
  ```bash
  bash scripts/test-runner.sh
  ```
- Garanta que a suíte esteja 100% verde antes de iniciar as modificações.

### Passo 3: Refatoração Estrutural de Alto Nível (Refactor)
- Aplique princípios de Clean Code e SOLID: reduza duplicação, melhore a coesão, extraia responsabilidades e fortaleça a tipagem.
- Não altere o comportamento externo e não misture novas features durante o refactor.

### Passo 4: Re-execução de Testes & Verificação de Invariantes
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
- Confirme que nenhuma alteração não intencional, quebra de tipagem ou conflito foi introduzido.

### Passo 6: Relatório Final de Evidências (Report)
- Emita o Response Contract no padrão CEH comprovando a paridade comportamental antes e depois da refatoração.

