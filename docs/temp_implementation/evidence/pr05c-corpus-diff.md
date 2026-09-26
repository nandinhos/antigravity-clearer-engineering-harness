# Evidência de Justificativa de Diff do Golden Corpus (PR-05c)

Este documento registra e justifica formalmente a evolução observada no Golden Corpus Snapshot (`gate_corpus.expected.jsonl`) no **PR-05c**, atendendo às especificações do **Handoff 019** e **Handoff 020** (endosso com deliberação plenária do Conselho de Seniores). O PR-05c substitui regras regex de `checkout`, `restore` e `switch` por um analisador léxico determinístico por tokens (`ceh_core/git.py`), sanando as vulnerabilidades V1 a V5 sem causar regressões nas decisões pré-existentes.

## Resumo Executivo das Alterações
- Total de avaliações no Golden Corpus anterior (PR-05b): **787**
- Registros preexistentes alterados: **0** (100% das 787 avaliações antigas permanecem idênticas)
- Novos comandos adicionados ao corpus: **38 comandos** (26 destrutivos e 12 controles seguros)
- Novas avaliações geradas (38 × 3 ambientes): **114 avaliações**
- Total consolidado pós-PR-05c: **901 avaliações**

---

## 1. Intactabilidade das Decisões Preexistentes (Auditoria de Regressão Zero)
Uma verificação automatizada comparou as 787 primeiras linhas do novo `gate_corpus.expected.jsonl` com o snapshot de referência:
- Total de divergências em decisões antigas: **0**
- Relaxamentos em comandos antigos: **0**
- Veredito: **NENHUMA decisão pré-existente foi alterada ou enfraquecida.**

---

## 2. Incorporação dos Casos de H019 e H020 (38 Novos Comandos / 114 Avaliações)

### 2.1 Variantes Destrutivas de Git (`GIT_HISTORY`): DEV allow / STAGING ask / PROD deny (26 comandos / 78 avaliações)

Cobrem todas as formas de evasão, opções compostas e flags identificadas nas revisões H019 e H020:
- **V1 (Pathspecs relativos e magias Git amplas):**
  - `git checkout src/..`
  - `git checkout -- app/..`
  - `git restore src/..`
  - `git restore -- app/..`
  - `git checkout ':(top)'`
  - `git checkout ':(top).'`
  - `git restore ':(top)'`
  - `git restore ':(top).'`
  - `git checkout ':!x'`
  - `git checkout ':^x'`
  - `git checkout ':(exclude)x'`
  - `git restore ':!x'`
  - `git checkout HEAD src/..` (H020: tree-ish com pathspec relativo que colapsa para raiz)
  - `git restore -s HEAD src/..` (H020: opção com valor `-s <tree-ish>` e pathspec relativo)
  - `git checkout ':/app/../..'` (H020: magia top-level `:/` com escape relativo)
  - `git restore ':/app/../..'` (H020: magia top-level `:/` com escape relativo)
  - *Comportamento:* Bloqueado em produção (`deny / GIT_HISTORY`), confirmação em staging (`ask / GIT_HISTORY`), liberado com salvaguarda em dev (`allow / GIT_HISTORY`).
- **V2 (Redefinição forçada de branch):**
  - `git switch -C main`
  - `git switch -C feature-x origin/main`
  - `git checkout -B main`
  - `git checkout -B release/1.0`
  - *Comportamento:* Equiparado a `git branch -D`, bloqueado em produção (`deny / GIT_HISTORY`).
- **V3 com `--worktree` (Descarte de modificações de arquivo de trabalho):**
  - `git restore --staged --worktree .`
  - `git restore -S -W .`
  - `git restore -W -S .`
  - `git restore --worktree --staged :/`
  - *Comportamento:* Bloqueado em produção (`deny / GIT_HISTORY`).
- **V5 (Pathspec opaco via arquivo - fail-closed):**
  - `git restore --pathspec-from-file=list.txt`
  - `git checkout --pathspec-from-file=list.txt`
  - `git restore --pathspec-file-nul`
  - *Comportamento:* Bloqueado em produção (`deny / GIT_HISTORY`), pois o gate não inspeciona o conteúdo do arquivo externo.

### 2.2 Controles Seguros de Git: DEV allow / STAGING allow / PROD allow (12 comandos / 36 avaliações)

Garantem que apenas os dois tipos de liberação aceitos no corpus (V3 e V4) sejam aplicados:
- **V3 (`--staged` isolado):**
  - `git restore --staged .`
  - `git restore -S .`
  - `git restore --staged :`
  - `git restore --staged :(`
  - `git restore --staged :!x`
  - *Comportamento:* Como afeta unicamente a staging area (índice) sem descartar modificações locais no worktree, é seguro (`allow / GENERAL`).
- **V4 (Falso positivo de `-f` eliminado em nomes com hífen):**
  - `git checkout feature/add-pdf`
  - `git checkout fix-leaf`
  - `git switch hotfix-ref`
  - `git checkout -- app/self-ref`
  - `git checkout -b fix-leaf`
  - `git switch -c hotfix-ref`
  - *Comportamento:* O analisador de tokens distingue nomes de branch/arquivos de flags como `-f`, permitindo a operação normalmente (`allow / FILESYSTEM_SAFE` ou `GENERAL`).
