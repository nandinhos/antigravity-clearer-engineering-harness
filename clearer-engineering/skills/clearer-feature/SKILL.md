---
name: clearer-feature
description: >-
  Evidence-driven feature implementation workflow following the CLEARER protocol:
  INSPECT -> REQUIREMENTS -> IMPACT -> PLAN -> IMPLEMENT -> TEST -> REVIEW -> AUDIT.
---

# CLEARER Feature Engineering Workflow

Esta skill conduz a especificação e implementação de uma nova funcionalidade com controle estrito de blast radius, evidências de teste e validação de critérios de aceitação.

---

## Fluxo de Execução

```text
INSPECT → REQUIREMENTS → IMPACT → PLAN → IMPLEMENT → TEST → REVIEW → AUDIT
```

### Passo 1: Inspeção Inicial (Inspect)
1. Detecte a stack e ferramentas do repositório:
   ```bash
   bash scripts/detect-project.sh
   ```
2. Inspecione o estado do Git com `git status --short`.
3. Localize os arquivos relacionados à área onde a nova funcionalidade atuará.

### Passo 2: Definição de Requisitos e Limites (Requirements & Boundaries)
- **Concrete Goal**: O que exatamente a funcionalidade deve fazer?
- **Explicit Boundaries**: O que está no escopo e o que fica expressamente fora?
- **Contratos**: Quais APIs, rotas, tipos ou tabelas precisam ser mantidos intactos?

### Passo 3: Mapeamento de Impacto (Impact Map)
- Identifique os arquivos que serão criados ou editados.
- Avalie o blast radius e dependências afetadas.

### Passo 4: Plano de Implementação (Implementation Plan)
Produza um plano conciso:
1. Objetivo técnico.
2. Arquivos envolvidos.
3. Mudanças propostas.
4. Contratos preservados.
5. Estratégia de testes.
6. Critérios de aceite.

### Passo 5: Implementação Cirúrgica (Implement)
- Aplique o código respeitando os padrões de estilo e convenções existentes.
- Evite refatorações oportunistas fora do escopo.

### Passo 6: Execução de Testes (Test)
- Execute a suíte de testes do projeto:
  ```bash
  bash scripts/test-runner.sh
  ```
- Registre o `COMMAND`, `EXIT CODE` e `RESULT`.

### Passo 7: Revisão do Diff (Review)
- Execute a auditoria do diff:
  ```bash
  bash scripts/diff-audit.sh
  ```
- Verifique se não foram introduzidas regressões, markers de conflito ou quebras de tipagem.

### Passo 8: Relatório Final de Evidências (Audit & Report)
Emita o relatório no padrão CEH:
```text
## RESULT
## CHANGES
## EVIDENCE
## TESTS
## REVIEW
## ACCEPTANCE
## REMAINING RISKS
## CONFIDENCE
```
