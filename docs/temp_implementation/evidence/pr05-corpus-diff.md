# Evidência de Justificativa de Diff do Golden Corpus (PR-05)

Este documento registra e justifica formalmente cada uma das alterações observadas no Golden Corpus Snapshot (`gate_corpus.expected.jsonl`) no **PR-05**, atendendo às especificações do **Handoff 016** para resolução das falhas G2 (descarte amplo da árvore de trabalho via `checkout`/`restore`) e G3 (canonicalização de opções globais do Git em qualquer subcomando).

## Resumo Executivo das Alterações
- Total de avaliações no Golden Corpus: **655** (inalterado em contagem total)
- Registros preexistentes alterados: **15** (exclusivamente os 5 comandos Git dos bypasses G2 e G3 em dev, staging e production)
- Novos registros adicionados ao corpus: **0**
- Total consolidado pós-PR-05: **655 avaliações**

---

## 1. Falha G2 — Descarte Amplo de Arquivos (`checkout` e `restore`) (9 avaliações alteradas)

No estado anterior à correção, comandos como `git checkout .`, `git restore .` e `git checkout -- .` escapavam do bloqueio de `GIT_HISTORY` devido à presença do token `\.\b` no regex de regras, sendo liberados como `GENERAL` ou `FILESYSTEM_SAFE`. Com a eliminação do `\.\b` e a criação de padrões robustos de pathspec amplo, esses comandos passam a ser corretamente reconhecidos como operações destrutivas da árvore de trabalho (`GIT_HISTORY`):

| ID | Comando | Ambiente | Antes (PR-04d) | Depois (PR-05) | Justificativa |
|---|---|---|---|---|---|
| `CMD-050-dev` | `git checkout .` | dev | allow / GENERAL | **allow / GIT_HISTORY** | [G2] Reconhecido como operação destrutiva de Git, liberada em dev com salvaguarda. |
| `CMD-050-sta` | `git checkout .` | staging | allow / GENERAL | **ask / GIT_HISTORY** | [G2] Bloqueio preventivo em homologação com Alertas 1/2 e 2/2 obrigatórios. |
| `CMD-050-pro` | `git checkout .` | prod | allow / GENERAL | **deny / GIT_HISTORY** | [G2] Production Lock: bloqueia descarte indiscriminado de arquivos em produção. |
| `CMD-051-dev` | `git restore .` | dev | allow / GENERAL | **allow / GIT_HISTORY** | [G2] Reconhecido como operação destrutiva de Git, liberada em dev. |
| `CMD-051-sta` | `git restore .` | staging | allow / GENERAL | **ask / GIT_HISTORY** | [G2] Alertas 1/2 e 2/2 em homologação. |
| `CMD-051-pro` | `git restore .` | prod | allow / GENERAL | **deny / GIT_HISTORY** | [G2] Production Lock: bloqueia restore amplo em produção. |
| `CMD-052-dev` | `git checkout -- .` | dev | allow / FILESYSTEM_SAFE | **allow / GIT_HISTORY** | [G2] Reconhecido como descarte amplo de árvore de trabalho. |
| `CMD-052-sta` | `git checkout -- .` | staging | allow / FILESYSTEM_SAFE | **ask / GIT_HISTORY** | [G2] Alertas 1/2 e 2/2 em homologação. |
| `CMD-052-pro` | `git checkout -- .` | prod | allow / FILESYSTEM_SAFE | **deny / GIT_HISTORY** | [G2] Production Lock: bloqueia descarte forçado via `-- .` em produção. |

---

## 2. Falha G3 — Opções Globais do Git Precedendo Subcomandos (6 avaliações alteradas)

No estado anterior, `resolve_git_invocation` restringia a remoção de opções globais (`-C`, `--no-pager`) exclusivamente ao subcomando `push`. Com a generalização para qualquer subcomando, opções inócuas são removidas na canonicalização, permitindo que regras de `GIT_HISTORY` analisem a intenção real (`git reset --hard`):

| ID | Comando | Ambiente | Antes (PR-04d) | Depois (PR-05) | Justificativa |
|---|---|---|---|---|---|
| `CMD-053-dev` | `git -C . reset --hard` | dev | allow / GENERAL | **allow / GIT_HISTORY** | [G3] Canonicalizado para `git reset --hard`; liberado em dev. |
| `CMD-053-sta` | `git -C . reset --hard` | staging | allow / GENERAL | **ask / GIT_HISTORY** | [G3] Alertas 1/2 e 2/2 em homologação para reset destrutivo. |
| `CMD-053-pro` | `git -C . reset --hard` | prod | allow / GENERAL | **deny / GIT_HISTORY** | [G3] Production Lock: bloqueia reset hard disfarçado com `-C .`. |
| `CMD-054-dev` | `git --no-pager reset --hard` | dev | allow / GENERAL | **allow / GIT_HISTORY** | [G3] Canonicalizado para `git reset --hard`; liberado em dev. |
| `CMD-054-sta` | `git --no-pager reset --hard` | staging | allow / GENERAL | **ask / GIT_HISTORY** | [G3] Alertas 1/2 e 2/2 em homologação. |
| `CMD-054-pro` | `git --no-pager reset --hard` | prod | allow / GENERAL | **deny / GIT_HISTORY** | [G3] Production Lock: bloqueia reset hard disfarçado com `--no-pager`. |
