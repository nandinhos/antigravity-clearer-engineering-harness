# Handoff 017 — Revisão do PR-04d e do PR-05; despacho do PR-05b e do PR-06 (G5)

**Data/Hora:** 2026-09-26T00:45:00Z
**Instância:** Revisor sênior (auditoria independente em container sem `agy`)
**Branch:** `claude/code-review-technical-analysis-kfwcdl` · **Revisado:** `9ce3410..6a86aff`
**Antecessor:** [Handoff 016](./handoff-016-revisao-pr04c-despacho-pr04d-e-pr05.md) · **Plano:** [`plano-implementacao-elevacao-ceh.md`](../../plano-implementacao-elevacao-ceh.md), seção 0.16
**Decisão soberana:** do desenvolvedor (`nandodev`).

---

## 1. Vereditos

| Entrega | Veredito | Base (`OBSERVED`, reproduzido aqui) |
|---|---|---|
| **PR-04d** (`5a791e4`) | **HOMOLOGADO** | T1 fechado (`build/../src` e `coverage/../.git` = deny em produção). O fuzz é **falsificável**: com o T1 reintroduzido numa cópia (`first_seg` do caminho cru), `test_rm_fuzz.py` **falha**. Corpus só com adições (+12). |
| **PR-05** (`6a86aff`) | **HOMOLOGADO COM RESSALVAS** (U1–U4) | Os 5 RED → verdes; restam 4 RED (G5 × 3, G7). As 15 decisões alteradas são exatamente os 5 comandos G2/G3. **G3 correto nas duas direções:** cwd `dev` + `-C` para a `main` → deny/produção; cwd `main` + `-C` para `dev` → allow/desenvolvimento; também pelo hook (`Cwd` + `-C ../mainrepo`). A lista do handoff e as variantes `HEAD .`, `@ -- .`, `--force`, `-- *`, `-W -S .`, `-s HEAD .` = deny. |

Os dois: Python 3.9 verde; corpus 655/655 portável; suíte 51/51; evals verdes.

**Ressalvas do PR-05:**
- **U1 — MEDIUM (bypass do G2):** `git checkout -- ./` → **`allow FILESYSTEM_SAFE` em produção**. `./` é o diretório inteiro, igual a `.`. O atalho seguro de `git checkout <arquivo>` (`rules.py`) aceita `./`.
- **U2 — MEDIUM (falso positivo; falha da especificação do revisor):** `git -P diff` e `git -P log` → **deny `GIT_DESTRUCTIVE`**. `-P` é a forma curta de `--no-pager`; a lista do Handoff 016 tinha `-p` (`--paginate`) mas esqueceu o `-P`, e ele caiu no fail-closed.
- **U3 — LOW (fora do escopo do G2, destrutivo):** `git switch -f <branch>` e `git switch --discard-changes <branch>` → `allow`; os dois descartam alterações locais.
- **U4 — processo:** o PR-05 **não acrescentou nenhum caso ao corpus**. O Handoff 016 §3 pedia a bateria completa, e o Handoff 015 fixou que toda bateria de revisão entra no corpus.

**Nota sobre o relatório:** "G5: Pipeline Red Universal / G7: Push Branch Match" **não** é o escopo. O G5 são **deleções indiretas** (`find -delete`, `find -exec rm`, one-liners de interpretador); o G7 é o **refspec contra o commit certificado** (PR-08, Onda 2).

## 2. Despacho — PR-05b `fix(gate): pathspec ./, opção -P e switch destrutivo` (pequeno)

1. **U1:** no atalho seguro de `git checkout`/`git restore`, normalizar o pathspec (`./`, `.//`, `./.`) e tratá-lo como `.`, portanto amplo.
2. **U2:** `-P` entra na lista de opções globais inócuas.
3. **U3:** `git switch -f`, `--force` e `--discard-changes` → `GIT_HISTORY`. Controles verdes: `git switch main` e `git switch -c feature`.
4. **U4:** **todas** as linhas das duas tabelas desta revisão (26 variantes e 11 controles) entram no corpus; o diff é justificado em `pr05b-corpus-diff.md`.

## 3. Despacho — PR-06 `fix(gate): deleções indiretas (G5)`

- **`find` com `-delete` ou `-exec rm`/`-execdir rm`/`-ok rm`:** separar os caminhos iniciais (tokens antes da primeira expressão: `-…`, `(`, `!`).
  - **Catastrófico** se algum caminho inicial for `/`, um `SYSTEM_ROOT` exato, o `HOME` ou `/home/<x>` (reusar a normalização do `rm.py`). **Não** tratar o diretório de trabalho como catastrófico aqui: `find . -name '*.pyc' -delete` apaga só o que casa com o filtro.
  - Caso contrário, é uma nova linha `FILESYSTEM` na tabela: DEV allow / HML ask / PROD deny (Q1).
- **One-liners de interpretador com API destrutiva:** linhas em `rules.py` **ancoradas na invocação do interpretador**: `(python3?|node|perl|ruby)\s+(-c|-e)\s+…(shutil\.rmtree|os\.(remove|unlink|rmdir)|Path\(.*\)\.(unlink|rmdir)|fs\.(rm|rmSync|rmdirSync|unlinkSync)|rimraf|FileUtils\.rm_rf|unlink)`. DEV allow / HML ask / PROD deny.
  - A âncora é obrigatória para **não** negar `grep -r "shutil.rmtree" .` nem `cat script.py` (controles).
- **Remover `@expectedFailure`** dos 3 casos G5; o único RED que resta é o G7.
- **Bateria obrigatória no corpus**, com o diff justificado em `pr06-corpus-diff.md`:
  - `find / -delete`, `find /etc -delete`, `find ~ -delete`, `find . -name '*.pyc' -delete`, `find . -exec rm -rf {} +`, `find build -delete`;
  - `python3 -c 'import shutil; shutil.rmtree("/srv")'`, `node -e 'require("fs").rmSync("db",{recursive:true})'`, `perl -e 'unlink glob "*"'`;
  - controles: `find . -name '*.log'`, `grep -r "shutil.rmtree" .`, `python3 -c 'print(1)'`, `node -e 'console.log(1)'`.

## 4. Critérios de aceite

- [ ] PR-05b: U1 = deny em produção; `git -P diff`/`git -P log` = allow; U3 = `GIT_HISTORY`; controles verdes; corpus com as 37 linhas desta revisão.
- [ ] PR-06: 3 RED G5 → verdes (resta só o G7); `find /` = CATASTROPHIC em qualquer ambiente; `find . … -delete` = allow em DEV e deny em PROD; os controles de `grep`/`print` seguem `allow`.
- [ ] Os dois: diff justificado; suíte, evals, `doc-audit`, Python 3.9, corpus portável e protocolo 7.1.

Com o PR-06 fecha a **Onda 1** (G1–G6). Depois: **Onda 2** (PR-08 G7, PR-09 payload vazio, PR-10 G9 escrita de arquivo e certificado).
