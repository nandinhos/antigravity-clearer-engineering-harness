# Handoff 014 — Revisão do PR-04 (G1 + G4) e despacho do PR-04b

**Data/Hora:** 2026-09-25T23:15:00Z
**Instância:** Revisor sênior (auditoria independente em container sem `agy`)
**Branch:** `claude/code-review-technical-analysis-kfwcdl` · **Revisado:** `9260a50..eb3e43e`
**Antecessor:** [Handoff 013](./handoff-013-homologacao-pr03-e-despacho-pr04.md) · **Plano:** [`plano-implementacao-elevacao-ceh.md`](../../plano-implementacao-elevacao-ceh.md), seção 0.13
**Decisão soberana:** do desenvolvedor (`nandodev`).

---

## 1. Veredito: PR-04 **RESSALVAS BLOQUEANTES** — corrigir no PR-04b antes do PR-05

**O que está certo (`OBSERVED`):**
- As 39 decisões alteradas no corpus são todas de comandos `rm`, sem remoções nem entradas novas.
- **Nenhuma** decisão `FILESYSTEM_SAFE` de alvo único mudou (a opção A foi respeitada).
- Os 6 casos G1/G4 estão verdes; os 9 RED restantes seguem RED; há 4 controles novos.
- Flags em qualquer forma e prefixos (`\rm`, `command rm`, `/bin/rm`), além de `--no-preserve-root`, `rm -rf /tmp/ /` e `rm -rf dist/ /`, são negados corretamente.

**O que bloqueia (bateria adversarial e de falso positivo, `safety-gate.py --check`):**

- **R1 — HIGH (regressão de uso) — descendentes de diretórios do sistema viram CATASTROPHIC.** `rm.py:83` usa `norm.startswith(root + "/")`. Em **DEV**:

  | Comando | Hoje | Esperado |
  |---|---|---|
  | `rm -rf /home/user/projeto/build` | **deny CATASTROPHIC** | allow (DEV) |
  | `rm -rf /home/user/projeto/src/old` | **deny CATASTROPHIC** | allow (DEV) |
  | `rm -rf /opt/myapp/cache` · `rm -rf /var/tmp/ceh-x` · `rm -rf /usr/local/lib/node_modules/foo` | **deny CATASTROPHIC** | allow (DEV) |

  Agentes usam caminho absoluto o tempo todo (o `agy` passa `Cwd` absoluto). O Handoff 013 definia como catastrófico só o **diretório de primeiro nível** (com ou sem `/` final ou `/*`), não os descendentes. Por isso o **CMD-095** (`/var/lib/postgresql`) não deveria ter virado CATASTROPHIC. O corpus não pegou porque não tinha nenhum caso de caminho absoluto legítimo.

- **R2 — MEDIUM (bypass) — falta normalização de caminho.** `rm.py:70` compara com literais. Em DEV, respondem **allow**:
  - `rm -rf //` e `rm -rf /./` (raiz);
  - `rm -rf ../..` (ancestral do diretório de trabalho), enquanto `..` é negado;
  - `rm -rf ./*`, enquanto `*` é negado;
  - `rm -rf ~root`.

- **R3 — MEDIUM (integridade de evidência) — o motivo declara uma fonte falsa.** `rm.py:160` devolve o texto fixo `"Safe development operation permitted (Explicit parameter (--env development))."`. Com a branch `main` (produção detectada), a resposta é `environment: production` com motivo **"--env development"**. O código anterior usava o `env_evidence` real (`safety-gate.py@9260a50:199`). O snapshot não grava o motivo, por isso não pegou.

- **R4 — LOW — o relatório do agente descreve errado o PR-05.** "Git hooks, commit com quebra de linha, aliases" **não** é o escopo. O G2 é `checkout`/`restore` com pathspec amplo (o regex `\.\b` nunca casa); o G3 são as opções globais do git (`-C`, `--no-pager`) só normalizadas para `push`.

**Anteriores ao PR-04, para o backlog (não bloqueiam):**
- `echo "rm -rf /"` → deny, porque o regex catastrófico corre sobre a string crua.
- `git rm -r --cached .` casa com o regex de `rm` em produção.

## 2. Despacho — PR-04b `fix(gate): alvos de rm normalizados e só o próprio diretório é catastrófico`

1. **Normalização de cada alvo:**
   - expandir `~` e `~usuario` com `expanduser`, e `$HOME`/`${HOME}` para o `HOME`;
   - colapsar barras repetidas e aplicar `normpath`;
   - separar o sufixo glob (`/*` ou `*`) e avaliar o diretório-base;
   - tornar absolutos os caminhos relativos, contra o diretório de trabalho da avaliação (no hook, o alvo já resolvido pelo PR-00).
2. **Catastrófico** (em qualquer ambiente) quando o caminho normalizado, ou a base de um glob, é:
   - `/`;
   - **exatamente** um diretório de sistema de primeiro nível (`SYSTEM_ROOTS`);
   - **exatamente** `/home/<nome>` ou o `HOME` resolvido;
   - um **ancestral ou o próprio** diretório de trabalho (cobre `.`, `..`, `../..`, `./*` e `*`).

   **Descendentes não são catastróficos**: seguem as regras de `FILESYSTEM` por ambiente.
3. **R3:** o motivo usa o `env_evidence` que o gate já calcula; nenhum texto de evidência fixo.
4. **Testes:** tabela `tests/test_rm_targets.py` com **toda** a bateria da seção 1, incluindo os casos de falso positivo como controles verdes, mais um teste de que o motivo em produção **não** contém `--env development`.
5. **Corpus:** acrescentar os controles de caminho absoluto legítimo e as variantes de bypass. O diff é justificado linha a linha em `pr04b-corpus-diff.md`: o CMD-095 volta a `FILESYSTEM` (dev allow / sta ask / pro deny).

## 3. Critérios de aceite do PR-04b

- [ ] Bateria da seção 1: os 13 falsos positivos voltam ao esperado e as 5 variantes de bypass viram `deny CATASTROPHIC`.
- [ ] Nenhum motivo com fonte de evidência fixa; o teste de produção prova isso.
- [ ] Os 6 casos G1/G4 e os 4 controles seguem verdes; os 9 RED seguem RED.
- [ ] Diff do corpus justificado linha a linha; suíte, evals, `doc-audit` e Python 3.9 verdes.
- [ ] Relatório de fechamento citando **todas** as execuções (N1 do Handoff 013) e o arquivo de diff como prova.

Depois do PR-04b: **PR-05** (G2 + G3, com o escopo da seção 1, R4).
