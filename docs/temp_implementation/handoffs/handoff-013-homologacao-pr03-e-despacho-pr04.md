# Handoff 013 — Homologação do PR-03 e despacho do PR-04 (G1 + G4)

**Data/Hora:** 2026-09-25T22:45:00Z
**Instância:** Revisor sênior (auditoria independente em container sem `agy`)
**Branch:** `claude/code-review-technical-analysis-kfwcdl` · **Revisado:** `7d1bae4..fc7bcc8`
**Antecessor:** [Handoff 012](./handoff-012-homologacao-pr02b-e-despacho-pr03.md) · **Plano:** [`plano-implementacao-elevacao-ceh.md`](../../plano-implementacao-elevacao-ceh.md), seção 0.12
**Decisão soberana:** do desenvolvedor (`nandodev`). **Há uma decisão pendente na seção 3.**

---

## 1. Veredito: PR-03 **HOMOLOGADO**

| Critério | Verificado aqui | Resultado |
|---|---|---|
| Só movimentação de código | AST de todas as definições do gate antigo × gate + `ceh_core/` | **14/15 idênticas.** A única diferença, `normalize_command_for_evaluation`, perdeu um `import shlex` local redundante (`lexer.py:9` importa no topo): equivalente |
| Snapshot | `--check` em 3.12 e em 3.9 | **586/586, diff vazio** |
| Testes | matriz, `cluster4` (15 xfail + controle), `hook_context` e `cluster2` em **Python 3.9** | Verdes |
| Deriva B efetiva | eval (5/5) **e** mutante manual independente | Original `deny/production`; mutante `allow/development` |
| `cluster2_acceptance` alterado | `copy2(gate)` → `copytree(scripts/)` | **Necessário** (o gate importa `ceh_core`); o teste não ficou mais fraco |
| Instalação | `run-install-verification.sh` | Verde |
| Smoke no `agy` real | [`222036Z`](../evidence/host-probe/agy/20260925T222036Z/summary.md), [`222116Z`](../evidence/host-probe/agy/20260925T222116Z/summary.md), [`222340Z`](../evidence/host-probe/agy/20260925T222340Z/summary.md) | E1 EXECUTADO (controle positivo); E10 BLOQUEADO 2/2, com o motivo `[CEH PRODUCTION LOCK]`, que só o gate emite |

**Notas (sem bloqueio):**
- **N1:** a primeira execução do E10 (`222116Z`) foi **INCONCLUSIVA**: o hook não disparou porque o modelo recusou antes de chamar a ferramenta. Ela está commitada (correto), mas o relatório de fechamento citou só "2/2". Relatórios devem citar **todas** as execuções.
- **N2:** a mensagem "Mutação aplicada em `ceh_core/environment.py`" do eval é impressa também no ramo de fallback (mutação no gate). É cosmético.
- **N3:** a afirmação "Snapshot 586/586" do relatório apontava para o **script** `snapshot_gate.py`, que não prova o resultado. Salve a saída do `--check` como arquivo de evidência, ou cite o `TESTS`, que já inclui o snapshot.

## 2. Despacho — PR-04 `fix(gate): análise de rm por token (G1 + G4)`

- **Onde:** `clearer-engineering/scripts/ceh_core/rm.py` (≤ 300 linhas); o gate só chama.
- **Tokenização:** `shlex` sobre o subcomando já normalizado. Reconhecer `rm` e flags em **qualquer forma**: `-rf`, `-fr`, `-r -f`, `-R`, `--recursive`, `--force`, `--no-preserve-root`, e o separador `--`. Coletar **todos** os alvos.
- **G4 — alvo catastrófico → `deny` em qualquer ambiente:** `/`, `/*`, `~`, `~/`, `$HOME`, `..`, `*`, `.`, e diretórios de sistema de primeiro nível (`/etc`, `/usr`, `/var`, `/bin`, `/sbin`, `/boot`, `/home`, `/lib`, `/lib64`, `/opt`, `/root`, `/srv`, `/sys`, `/proc`, `/dev`), com ou sem `/` final ou `/*`.
- **G1 — atalho de limpeza segura:** só vale se **todos** os alvos forem seguros (`tmp/`, `.tmp/`, `scratch/`, `.cache/`, `dist/`, `build/`, `coverage/`, `storage/framework/cache/`, ou arquivo único com extensão). Um alvo não seguro invalida o atalho, e o comando segue para as regras por ambiente.
- **Remover `@expectedFailure`** dos 6 casos G1/G4 do `cluster4_acceptance.py`.

## 3. Decisão pendente do desenvolvedor — escopo por ambiente do atalho seguro

Hoje `rm -rf dist/` e `rm -rf a.txt` saem **`allow` nos 3 ambientes** (`FILESYSTEM_SAFE`). A `main` conta como produção.

| Opção | Efeito | Recomendação |
|---|---|---|
| **A — "todos os alvos seguros", em qualquer ambiente** | Fecha o G1 (o atalho não libera mais alvos perigosos); `rm -rf dist/` continua liberado na `main` | **Recomendada** (Ponytail: a menor mudança que fecha o achado; sem regressão de uso) |
| B — atalho só em DEV (texto original do plano) | Fecha o G1 e, além disso, nega `rm -rf dist/` em produção (e na `main`) e pede confirmação em HML | Endurecimento extra, com impacto em quem trabalha na `main` |

**O agente deve implementar a opção A**, a menos que o desenvolvedor escolha B. A escolha fica registrada na seção 9 do plano.

## 4. Critérios de aceite do PR-04

1. Os 6 casos G1/G4 **passam** sem `expectedFailure`; os outros 9 RED continuam RED; o controle do G7 continua verde.
2. **Diff do snapshot justificado linha a linha:** `snapshot_gate.py` gera o diff e o PR anexa um arquivo `docs/temp_implementation/evidence/pr04-corpus-diff.md` listando **cada linha alterada com o ID que a justifica** (G1 ou G4). Qualquer linha sem justificativa reprova o PR. Na opção A, **nenhuma** linha `FILESYSTEM_SAFE` de alvo único seguro pode mudar.
3. **Sem falso positivo:** novos casos de controle verdes, `rm -rf dist/`, `rm -rf node_modules/.cache`, `rm -f a.txt`, `rm -rf ./build` → decisão atual preservada.
4. Matriz 24/24, suíte canônica, evals 5/5, `doc-audit` 7/7, testes em Python 3.9.
5. Protocolo 7.1, com `evidence-report.sh --strict` citando o arquivo de diff do corpus (N3).
