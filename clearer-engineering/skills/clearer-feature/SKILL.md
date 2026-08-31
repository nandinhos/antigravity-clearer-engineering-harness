---
name: clearer-feature
description: >-
  Evidence-driven feature implementation workflow following the CLEARER protocol:
  INSPECT -> REQUIREMENTS -> IMPACT -> PLAN -> IMPLEMENT -> TEST -> REVIEW -> AUDIT.
---

# CLEARER Feature Engineering Workflow

Esta skill conduz a especificação, implementação de alto nível e validação de uma nova funcionalidade com controle estrito de blast radius, evidências de teste e execução contínua.

---

## Fluxo de Execução Contínua (Single-Turn End-to-End)

```text
INSPECT → REQUIREMENTS → IMPACT → PLAN → IMPLEMENT → TEST → REVIEW → AUDIT & REPORT
```

> **Diretriz de Autonomia:** Conduza os 8 passos em uma única invocação fluida quando os requisitos estiverem definidos. Apenas pause o fluxo caso ocorra ambiguidade de requisitos sem resposta no repositório ou comando bloqueado pelo Safety Gate.

---

### Passo 1: Inspeção Inicial (Inspect)
1. Detecte a stack e ferramentas do repositório:
   ```bash
   bash scripts/detect-project.sh
   ```
2. Inspecione o estado do Git com `git status --short`.
3. Localize os arquivos e testes relacionados à área onde a nova funcionalidade atuará.

### Passo 2: Requisitos e Limites (Requirements & Boundaries)
- **Concrete Goal**: O que exatamente a funcionalidade deve fazer?
- **Explicit Boundaries**: O que está no escopo e o que fica expressamente fora?
- **Contratos**: Quais APIs, interfaces, tipos ou tabelas precisam ser mantidos intactos?

### Passo 3: Mapeamento de Impacto (Impact Map)
- Identifique os arquivos que serão criados ou editados.
- Avalie o blast radius e dependências afetadas.

### Passo 4: Plano Interno de Implementação (Implementation Plan)
Estruture mentalmente e valide os seguintes pontos:
1. Objetivo técnico e fluxo de dados.
2. Arquivos envolvidos e novos símbolos.
3. Tipagem estrita e arquitetura defensiva (tratamento de erros, nulos, limites).
4. Estratégia de testes automatizados.

### Passo 5: Implementação Cirúrgica de Alto Nível (Implement)
- Aplique o código com excelência (Clean Code, SOLID, tipagem estrita).
- Evite atalhos frágeis (`any`, patches cegos) e refatorações oportunistas fora do escopo.
- Escreva código auto-documentado e modular.

### Passo 6: Criação e Execução de Testes (Test)
- Crie ou atualize os testes comportamentais que cobrem a funcionalidade.
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
- Verifique se não foram introduzidas regressões, markers de conflito, console.logs soltos ou quebras de contrato.

### Passo 8: Relatório Final de Evidências (Audit & Report)
Emita a entrega final com o Response Contract completo:
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

