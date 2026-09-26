# Evidência de Justificativa de Diff do Golden Corpus (PR-05b)

Este documento registra e justifica formalmente a evolução observada no Golden Corpus Snapshot (`gate_corpus.expected.jsonl`) no **PR-05b**, atendendo às especificações do **Handoff 017** e **Handoff 018** para incorporação mandatória da bateria de testes das revisões (U4), fechamento do bypass de pathspec relativo amplo (U1: `git checkout -- ./`), liberação da opção global curta inócua (U2: `git -P`) e classificação destrutiva do `git switch` com flags forçadas (U3: `-f`, `--force`, `--discard-changes`).

## Resumo Executivo das Alterações
- Total de avaliações no Golden Corpus anterior: **655**
- Registros preexistentes alterados: **0** (100% das 655 avaliações antigas permanecem idênticas)
- Novos comandos adicionados ao corpus: **44 comandos** (32 destrutivos variantes e 12 controles seguros)
- Novas avaliações geradas (44 × 3 ambientes): **132 avaliações**
- Total consolidado pós-PR-05b: **787 avaliações**

---

## 1. Intactabilidade das Decisões Preexistentes (Auditoria de Regressão Zero)
Uma verificação de integridade automatizada comparou as 655 primeiras linhas do novo `gate_corpus.expected.jsonl` com o snapshot de referência:
- Total de divergências em decisões antigas: **0**
- Veredito: **NENHUMA decisão pré-existente foi alterada ou relaxada.**

---

## 2. Incorporação da Bateria de Revisão H017 / H018 (44 Novos Comandos / 132 Avaliações)

### 2.1 Variantes Destrutivas de Git (`GIT_HISTORY`): DEV allow / STAGING ask / PROD deny (32 comandos / 96 avaliações)

Cobrem todas as formas de evasão e opções testadas nas revisões dos Handoffs 016 e 017:
- **U1 (Pathspec relativo amplo):** `git checkout -- ./`, `git checkout ./`, `git checkout .//`, `git checkout ./.`, `git restore ./`, `git restore -- ./`.
  - *Comportamento:* Bloqueado em produção (`deny / GIT_HISTORY`), confirmação em staging (`ask / GIT_HISTORY`), liberado com salvaguarda em dev (`allow / GIT_HISTORY`).
- **G2 (Variantes de descarte amplo):** `git restore .`, `git restore --staged --worktree .`, `git restore --source=HEAD .`, `git restore :/`, `git restore -W -S .`, `git restore --worktree -- .`, `git restore -s HEAD .`, `git checkout .`, `git checkout -- .`, `git checkout HEAD .`, `git checkout HEAD -- .`, `git checkout @ -- .`, `git checkout --force main`, `git checkout -f`, `git checkout :/`, `git checkout -- '*'`, `git checkout -- *`, `git checkout -f -- app/x.php`.
- **U3 (Git switch destrutivo com descarte):** `git switch -f main`, `git switch --discard-changes main`, `git switch --force main`.
  - *Comportamento:* Classificado como `GIT_HISTORY`. Previne perda de código não commitado em produção e staging.
- **G3 (Opções globais combinadas com comandos destrutivos):** `git -C . reset --hard`, `git --no-pager reset --hard`, `git -P reset --hard`, `git --paginate reset --hard`, `git --no-pager -C . reset --hard`.
  - *Comportamento:* Canonicalizado para `git reset --hard` e bloqueado em produção.

### 2.2 Controles Seguros de Git (`GENERAL` / Não Destrutivo): DEV allow / STAGING allow / PROD allow (12 comandos / 36 avaliações)

Garantem a ausência de falsos positivos no fluxo de desenvolvimento diário:
- **U2 (Opção global inócua -P curta):** `git -P diff`, `git -P log -5`.
  - *Comportamento:* Permite execução sem pager (`allow / GENERAL`) em qualquer ambiente sem cair no fail-closed de opções globais.
- **Controles de checkout e restore pontual:** `git checkout app/Model.php`, `git checkout feature/login`, `git checkout -- app/Model.php`, `git checkout v1.2.0`, `git restore --staged app/Model.php`.
- **Controles de navegação e inspeção:** `git -C sub status`, `git --no-pager log -5`.
- **Controles de switch seguro:** `git switch main`, `git switch -c feature`, `git switch -b feature`.
