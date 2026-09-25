# Handoff 016 — Revisão do PR-04c, despacho do PR-04d (normalização + fuzz) e do PR-05 (G2 + G3)

**Data/Hora:** 2026-09-26T00:15:00Z
**Instância:** Revisor sênior (auditoria independente em container sem `agy`)
**Branch:** `claude/code-review-technical-analysis-kfwcdl` · **Revisado:** `b73092f..4c38d09`
**Antecessor:** [Handoff 015](./handoff-015-revisao-pr04b-e-despacho-pr04c.md) · **Plano:** [`plano-implementacao-elevacao-ceh.md`](../../plano-implementacao-elevacao-ceh.md), seção 0.15
**Decisão soberana:** do desenvolvedor (`nandodev`).

---

## 1. Veredito: PR-04c **RESSALVA BLOQUEANTE** (T1, correção pequena)

**Resolvido (`OBSERVED`):**
- S1: a tabela de produção do Handoff 015 inteira voltou a `deny`; os controles `dist/`, `./build`, `/tmp/ceh-x`, `a.txt`, `node_modules/.cache` e `dist/assets` = `allow FILESYSTEM_SAFE`.
- S2: `$PWD`, `"$PWD"` e `"$PWD"/*` = `deny CATASTROPHIC`; `$OLDPWD` e `$BUILD_DIR` = `ask`; com `PWD=/etc` forjado no ambiente, `$PWD` continua resolvendo para o diretório de trabalho.
- Os escapes para fora do diretório de trabalho estão corretos: `dist/../../etc`, `/tmp/../etc`, `/tmp/../home/user`, `../a.txt` e `/etc/passwd.bak` não são seguros.
- Diff do corpus exato: só o CMD-202 mudou (o alargamento do PR-04b desfeito), mais 27 casos novos; a bateria dos Handoffs 014 e 015 entrou no corpus (faltam 2 variantes opcionais: `/home/user/..` e `/usr/local/../..`).
- Corpus portável (643/643 com `TMPDIR`/`HOME` alternativos); Python 3.9; suíte 49/49; evals verdes.

**T1 — HIGH — o atalho seguro olha o caminho cru, não o normalizado.** `rm.py:135` calcula o normalizado `norm_full`, mas `rm.py:140` tira o primeiro segmento de `t_clean` (cru). Em **produção**:

| Comando | Normalizado | Hoje | Esperado |
|---|---|---|---|
| `rm -rf build/../src` | `src` | **allow FILESYSTEM_SAFE** | deny |
| `rm -rf coverage/../.git` | `.git` | **allow FILESYSTEM_SAFE** (apaga o repositório) | deny |

## 2. Despacho — PR-04d `fix(gate): atalho seguro avaliado sobre o caminho normalizado`

1. A decisão de "seguro" usa **só** o caminho normalizado, relativo ao diretório de trabalho (`os.path.relpath(norm_full, cwd)`): o primeiro segmento **desse** caminho tem de estar no conjunto seguro, e o caminho não pode começar com `..`.
2. **Teste de propriedade com fuzz** (`tests/test_rm_fuzz.py`, `random.Random(20260926)`, ≥ 2000 casos, stdlib):
   - Gerar alvos combinando prefixos seguros e não seguros, `.`, `..`, `//`, nomes comuns (`src`, `.git`, `app`, `etc`), `*`, absolutos e relativos.
   - **Invariante 1:** se a decisão é `FILESYSTEM_SAFE`, então `relpath(normpath(alvo))` não começa com `..`, e o seu primeiro segmento está no conjunto seguro (ou o alvo está sob `/tmp/`, ou é arquivo único com extensão dentro do diretório de trabalho).
   - **Invariante 2:** se o normalizado é `/`, um `SYSTEM_ROOT`, o `HOME`, `/home/<x>`, ou um ancestral ou o próprio diretório de trabalho, então a decisão é `deny CATASTROPHIC` em qualquer ambiente.
   - Em falha, o teste imprime o alvo mínimo que viola a invariante.
3. Corpus: acrescentar `build/../src`, `coverage/../.git` e as 2 variantes opcionais; o diff é justificado em `pr04d-corpus-diff.md`.

## 3. Despacho — PR-05 `fix(gate): canonicalizar invocações git (G2 + G3)`

Inicia depois que o PR-04d passar nos seus critérios. **Commit separado.**

- **G3 — opções globais para qualquer subcomando.** Generalizar `resolve_git_invocation` para devolver `(subcomando, args, repo_alvo)` para **todo** subcomando, não só `push`, removendo as opções globais inócuas (`-C <dir>`, `-C<dir>`, `--no-pager`, `-p`, `--paginate`, `--no-replace-objects`, `--literal-pathspecs`, `--bare`); `--git-dir`, `--work-tree` e `-c` seguem em fail-closed. As regras de git são avaliadas sobre `git <subcomando> <args>` canônico. **O ambiente é detectado no repositório de `-C`**: `git -C /repo-na-main reset --hard` com o cwd num repositório `dev` → produção.
- **G2 — `checkout`/`restore` com pathspec amplo.** Remover os regex com `\.\b` (`rules.py`). São destrutivos: `git checkout .`, `git checkout -- .`, `git checkout HEAD -- .`, `git checkout -f`, `git checkout :/`, `git checkout -- '*'`, `git restore .`, `git restore --staged --worktree .`, `git restore --source=HEAD .`, `git restore :/`. **Não são destrutivos** (controles verdes): `git checkout app/Model.php` (teste 14), `git checkout main`, `git checkout -b feature`, `git restore --staged app/Model.php`.
- **Aceite:**
  - Os 5 RED G2/G3 viram verdes; restam 4 RED (G5 × 3 e G7).
  - Controles verdes.
  - Bateria completa no corpus, com o diff justificado em `pr05-corpus-diff.md`: só linhas git, cada uma com o ID G2 ou G3.

## 4. Critérios de aceite

- [ ] PR-04d: tabela T1 = `deny` em produção; fuzz ≥ 2000 casos verde com as 2 invariantes; diff do corpus justificado.
- [ ] PR-05: 5 RED → verde; controles verdes; `-C` define o ambiente pelo repositório alvo; diff justificado.
- [ ] Os dois PRs: suíte, evals, `doc-audit`, Python 3.9, corpus portável e protocolo 7.1 com `evidence-report.sh --strict` citando os arquivos de diff.
