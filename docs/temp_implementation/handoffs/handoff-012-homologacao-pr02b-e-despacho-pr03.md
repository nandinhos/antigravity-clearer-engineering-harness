# Handoff 012 — Homologação do PR-02b e despacho do PR-03

**Data/Hora:** 2026-09-25T21:30:00Z
**Instância:** Revisor sênior (auditoria independente em container sem `agy`)
**Branch:** `claude/code-review-technical-analysis-kfwcdl` · **Revisado:** `d1f9a20..1d43eb6`
**Antecessor:** [Handoff 011](./handoff-011-revisao-onda-0.md) · **Plano:** [`plano-implementacao-elevacao-ceh.md`](../../plano-implementacao-elevacao-ceh.md), seção 0.11
**Decisão soberana:** do desenvolvedor (`nandodev`).

---

## 1. Veredito: PR-02b **HOMOLOGADO** — Onda 0 concluída

| Critério | Verificado aqui | Resultado |
|---|---|---|
| O1 — corpus hermético | `snapshot_gate.py --check` com certificado real, canônico PASS no `HEAD`, não canônico e ausente; e ausente em Python 3.9 | **5/5 verdes** |
| O2 — a suíte não altera o certificado real | sha256 de `.ceh/last-ci-run.json` antes e depois de `run-all-tests.sh` (48/48) | **Idêntico** (`1ac61ebb13e73131`) |
| O3 — G7 correto | Rodados sem o decorador: RED `outro:main` → `AssertionError: 'allow' != 'deny'`; controle `dev:main` certificado → **passa** | **Correto** |
| Integridade do snapshot regenerado | Diff por `id` entre `9264e6f` e `1d43eb6` | **584 antigas intactas** (0 alteradas, 0 removidas); +2 (G7 RED e controle) |

**Estado da rede de segurança:** corpus de 586 avaliações, hermético e portável (3.9/3.12, com e sem `agy`), mais **15 RED** (G1–G5 e G7) que falham pela asserção certa. É a base obrigatória para o PR-03.

## 2. Despacho — PR-03 `refactor(gate): extrair regras, lexer e ambiente sem mudar decisões`

**Objetivo único:** abrir espaço no `safety-gate.py` (641/650) para as correções G1–G5 **sem alterar nenhuma decisão**.

**Escopo (Ponytail: o menor corte útil):**
- Novo pacote **`clearer-engineering/scripts/ceh_core/`**, ao lado do gate. O plano sugeria `core/`; a mudança evita manipulação de `sys.path`, porque o diretório do script já está no path quando o gate roda.
  - `rules.py` — `CATASTROPHIC_PATTERNS`, `SAFE_DEV_PATTERNS`, `USE_CASE_DESTRUCTIVE_PATTERNS` (movidos sem edição).
  - `lexer.py` — `split_shell_pipeline`, `normalize_command_for_evaluation`.
  - `environment.py` — `normalize_env`, `detect_environment`, `get_git_branch`, `find_repo_root`.
- `safety-gate.py` importa de `ceh_core` e **reexporta os mesmos nomes**: `test_safety_matrix`, `cluster*_acceptance`, `hook_context` e `snapshot_gate` importam do gate e não podem quebrar.
- **Fica no gate:** `evaluate_subcommand`, `evaluate_command`, `resolve_git_invocation`, `check_pre_push_ci_gate` e `handle_hook`. Mover esses é para depois das correções, não agora.
- `doc-audit` check 7: teto de 650 linhas para o gate e de **300 por módulo** de `ceh_core/`.

**Armadilha 1 — eval Deriva B.** `evals/run.sh` aplica `sed` na lista `["prod", "production", "prd", "live"]` **dentro de `safety-gate.py`**. Com `normalize_env` em `ceh_core/environment.py`, o `sed` não encontra nada: a mutação vira no-op e o eval acusa `INFRA-FAIL`, o que é correto, mas quebra o critério.
- Ajuste: a Deriva B copia **o diretório `scripts/` inteiro** para um temporário, muta `ceh_core/environment.py` na cópia e roda o gate da cópia.
- Os critérios não mudam: a mutação tem de ser efetiva (`cmp`), compilável, e produzir a divergência `deny/production/2` → `allow/development/0`; e a restauração tem de ser limpa.

**Armadilha 2 — import quebrado no hook é fail-closed silencioso.** Com o PR-00b, qualquer exceção no hook (inclusive `ImportError` de `ceh_core`) vira `deny`. No `agy`, isso bloquearia **todo** comando e pareceria "gate funcionando".
- Por isso o aceite tem um **controle positivo no host real** (ver o item 5 da seção 3).

## 3. Critérios de aceite do PR-03

1. **`snapshot_gate.py --check` com diff vazio** (586/586). Este é o critério principal: nenhuma decisão muda.
2. Matriz 24/24; `cluster4_acceptance` = 15 xfail **e o controle G7 verde**; suíte canônica verde; testes em Python 3.9.
3. Evals 5/5 com a Deriva B **efetiva** no módulo movido (o log mostra a mutação aplicada em `ceh_core/environment.py`).
4. `doc-audit` 7/7 com os tetos por módulo; `install.sh` instala `ceh_core/` (conferir com `run-install-verification.sh`).
5. **Smoke no `agy` real depois de `install.sh`:**
   - **E1 = EXECUTADO** (controle positivo: o gate não está negando tudo);
   - **E10-YOLO = BLOQUEADO** (o G6 continua corrigido).
   ```bash
   PROBE=docs/temp_implementation/scripts/host_probe.py
   python3 "$PROBE" run --host agy --isolar-ceh --experiments E1
   python3 "$PROBE" run --host agy --experiments E10 --args-padrao "--dangerously-skip-permissions --mode accept-edits"
   ```
   A pré-condição de segurança do E10 continua valendo: repositórios locais limpos e com push feito.
6. Protocolo 7.1, com `evidence-report.sh --strict` = VERIFICADO, citando o diff vazio do snapshot e as evidências do smoke.

Depois do PR-03: **PR-04** (G1 + G4, análise de `rm` por token), **PR-05** (G2 + G3, canonicalização de git), **PR-06** (G5). Cada um remove o `@expectedFailure` dos seus casos e deixa no diff do corpus **apenas** linhas justificadas pelo ID corrigido.
