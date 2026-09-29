# Handoff 015 — Revisão do PR-04b e despacho do PR-04c

**Data/Hora:** 2026-09-25T23:45:00Z
**Instância:** Revisor sênior (auditoria independente em container sem `agy`)
**Branch:** `claude/code-review-technical-analysis-kfwcdl` · **Revisado:** `de1a26e..131a6ca`
**Antecessor:** [Handoff 014](./handoff-014-revisao-pr04-e-despacho-pr04b.md) · **Plano:** [`plano-implementacao-elevacao-ceh.md`](../../plano-implementacao-elevacao-ceh.md), seção 0.14
**Decisão soberana:** do desenvolvedor (`nandodev`).

---

## 1. Veredito: PR-04b **RESSALVAS BLOQUEANTES** (nova regressão em produção)

**R1, R2 e R3 do Handoff 014: resolvidos (`OBSERVED`):**
- Os 8 falsos positivos em DEV voltaram a `allow`.
- Os 5 bypasses (`//`, `/./`, `../..`, `./*`, `~root`) agora dão `deny CATASTROPHIC`, e novas variantes também são pegas (`/home/user/`, `/home/user/..`, `/usr/local/../..`, `~/.`, `./..`, `"$HOME"`).
- O motivo em produção mostra `Explicit parameter (--env production)`.
- Diff do corpus exato: só o CMD-095 mudou (volta a `FILESYSTEM`), mais 30 casos novos.
- O corpus é portável (616/616 com `TMPDIR`/`HOME` alternativos e em Python 3.9); suíte 49/49; evals verdes.

**O que bloqueia:**

- **S1 — HIGH — o atalho seguro passou a aceitar caminhos absolutos e fora do diretório de trabalho, o que libera deleções em produção.** `rm.py:176-180` aceita como seguro **qualquer** caminho cujo último segmento seja `build`, `dist`, `coverage` ou `scratch`:

  | Em **produção** | Antes do PR-04 (`9260a50`) | Agora (`131a6ca`) |
  |---|---|---|
  | `rm -rf /var/www/site/dist` | deny | **allow FILESYSTEM_SAFE** |
  | `rm -rf /srv/app/build` | deny | **allow** |
  | `rm -rf /opt/prod/app/dist/` | deny | **allow** |
  | `rm -rf /etc/nginx/coverage/` | deny | **allow** |
  | `rm -rf ../../prod-release/dist` | deny CATASTROPHIC | **allow** |
  | `rm -rf dist/` | allow | allow (correto) |

  Isso não era necessário para o R1: em DEV, a regra normal de `FILESYSTEM` já libera `/home/user/projeto/build`. O atalho foi **alargado sem motivo**, contra a opção A (Q5), que manteve o conjunto seguro original. O corpus não pegou porque não tem caminho absoluto de artefato em produção.

- **S2 — MEDIUM — `$PWD` escapa do catastrófico.** Em DEV, `rm -rf $PWD`, `rm -rf "$PWD"/*` e `rm -rf $OLDPWD` dão `allow FILESYSTEM`. `$PWD` é o próprio diretório de trabalho, ou seja, a mesma coisa que `.`, que é negado.
  - **Atenção:** no hook do `agy`, a variável de ambiente `PWD` do processo é o **diretório do plugin** (`OBSERVED`, Handoff 006). Expandir `$PWD` via `os.environ` estaria **errado**; o valor certo é o diretório de trabalho da avaliação (o alvo resolvido pelo PR-00).

## 2. Despacho — PR-04c `fix(gate): atalho seguro só dentro do diretório de trabalho; $PWD resolvido`

1. **S1 — conjunto seguro com a semântica original (opção A):** um alvo só é "seguro" se, **depois de normalizado**:
   - (a) é **relativo e continua dentro** do diretório de trabalho (sem subir por `..`) e seu **primeiro segmento** está em `tmp`, `.tmp`, `scratch`, `.cache`, `dist`, `build`, `coverage`, `storage/framework/cache`, `node_modules/.cache`; **ou**
   - (b) é um **arquivo único com extensão** dentro do diretório de trabalho; **ou**
   - (c) está sob `/tmp/` (o único prefixo absoluto seguro do conjunto original).

   Qualquer outro caminho absoluto, ou que saia do diretório de trabalho, **nunca** é seguro e segue as regras de `FILESYSTEM` por ambiente. O critério de "último segmento" (`rm.py:176-180`) é removido.
2. **S2:** `$PWD` e `${PWD}` resolvem para o **diretório de trabalho da avaliação**, nunca para `os.environ["PWD"]`. Com isso, `rm -rf $PWD` e `rm -rf "$PWD"/*` viram `deny CATASTROPHIC`. `$OLDPWD`, e qualquer outra variável que não possa ser resolvida com segurança, torna o alvo **incerto**: nunca é seguro e, em DEV, vira `ask` (Invariante 7), que no `agy` o PR-00c já converte em `deny`.
3. **Testes** (`test_rm_targets.py`): a tabela S1 inteira (produção → `deny`), e `dist/`, `./build`, `/tmp/ceh-x` e `a.txt` como controles seguros; os casos S2; um teste de que `$PWD` **não** usa `os.environ["PWD"]` (rodar com `PWD` apontando para outro diretório).
4. **Corpus:** acrescentar a tabela S1, as variantes S2 e os controles; o diff é justificado em `pr04c-corpus-diff.md`. Esperado: **nenhuma** decisão existente muda, exceto as que o próprio PR-04b alargou.

## 3. Critérios de aceite do PR-04c

- [ ] Tabela S1 em produção = `deny` (e o `../../prod-release/dist` volta a `CATASTROPHIC` ou `deny`); controles seguros = `allow FILESYSTEM_SAFE`.
- [ ] S2: `$PWD`/`"$PWD"/*` = `deny CATASTROPHIC`; `$OLDPWD` = não seguro (`ask` em DEV); o teste com `PWD` falso passa.
- [ ] A bateria dos Handoffs 014 e 015 continua verde; os 9 RED seguem RED; os controles do G7 seguem verdes.
- [ ] Diff do corpus justificado; suíte, evals, `doc-audit` e Python 3.9 verdes; corpus portável (`TMPDIR`/`HOME` alternativos).
- [ ] Relatório de fechamento citando o arquivo de diff e todas as execuções.

**Nota de processo:** duas rodadas seguidas (PR-04 e PR-04b) passaram no corpus e reprovaram na bateria adversarial, porque o corpus só cobre o que alguém já imaginou. A partir do PR-04c, **toda linha de bateria adversarial usada em revisão entra no corpus** no PR que a corrige, e o corpus cresce a cada ciclo.
