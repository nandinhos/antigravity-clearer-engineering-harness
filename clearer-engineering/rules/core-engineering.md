---
trigger: always_on
---

# CLEARER Protocol & Core Engineering Principles

## 1. Ciclo Contínuo (Risk `MEDIUM`)
Toda alteração percorre `Inspect → Plan → Implement → Test → Review (diff-audit.sh) → Validate → Report (Response Contract)`:
- **Zero-Decision Rule (SDD 2.0)**: o `Plan` congela previamente arquivos exatos, schemas, rotas e bordas, não delegando decisões arquiteturais à implementação; desvios imprevisíveis acionam exceção em vez de improviso.

## 2. Risk Dial & Exceções
- **`LOW`**: alterações simples ou leituras em fluxo direto.
- **`MEDIUM`**: execução contínua em turno único (*Single-Turn End-to-End*) com escopo delimitado.
- **`HIGH`**: componentes críticos (auth core, pagamentos, concorrência, migrações destrutivas) — exige subagentes isolados, revisão adversarial e checkpoint humano.
- Só transfira controle ao usuário por ambiguidade de requisitos, Safety Gate, falha persistente após 1 auto-reparo ou escopo `HIGH`.
