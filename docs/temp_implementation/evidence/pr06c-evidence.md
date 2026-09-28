# Relatório de Evidências — PR-06c (Fechamento Oficial e Definitivo da Onda 1: G1–G6)

**Data/Hora:** 2026-09-26T01:15:00-03:00  
**Branch:** `claude/code-review-technical-analysis-kfwcdl`  
**Referência / Baseline:** `75a763a` (PR-06b homologado com ressalvas no Handoff 026)  
**Handoff de Origem:** Handoff 026 (`f7e1316`)  
**Ambiente:** `development` (detectado: Default workspace fallback)  

---

## 1. Sumário Executivo do PR-06c

O **PR-06c** fecha oficialmente e definitivamente a **Onda 1 (G1–G6)** do CEH, resolvendo integralmente os achados **AB1** (alto) e **AB3** (baixo) do Handoff 026:

1. **AB1 — Resolução Única da Cabeça do Comando (`resolve_command_head`)**:
   - Criada a função canônica única `resolve_command_head(tokens: list[str]) -> tuple[int, str | None]` em `ceh_core/lexer.py`.
   - Eliminadas todas as 4 cópias locais de laços de prefixos que existiam em `find.py`, `interpreters.py`, `git.py` e `safety-gate.py`.
   - Consome prefixos transparentes com suas opções e argumentos:
     - `rtk`, `rtk proxy`
     - `nohup`, `builtin`
     - `command`
     - `exec` (incluindo `-a`, `-c`, `-l`)
     - `nice` (incluindo `-n N`, `--adjustment=N`, e sintaxe abreviada `-10`)
     - `timeout` (incluindo `-k time`, `-s sig` e o argumento obrigatório de duração)
     - `sudo` / `doas` (incluindo `-u user`, `-g group`, flags e `--`)
     - `env` (incluindo `-u`, `-C` e atribuições `VAR=val`)
     - `time` (incluindo `-o`, `-f`, `-p`)
     - `stdbuf`, `ionice`, `chrt`, `taskset`
     - `xargs` (incluindo `-n`, `-P`, `-d`, `-s`, `-E`, `-L`, `-I{}`)
   - Desembrulha e extrai executores de string para reavaliação recursiva completa com o gate inteiro (`depth + 1`):
     - `eval <cmd>`
     - `su -c <cmd>` (incluindo `-c=`, `--command=`, `--command`)
     - `watch -n N <cmd>`

2. **AB3 — Substituição de Parâmetros Posicionais em `sh -c` / `bash -c` (`substitute_positional_args`)**:
   - Criada a função `substitute_positional_args(script: str, args: list[str]) -> str` em `ceh_core/lexer.py`.
   - Quando `sh -c`, `bash -c`, `zsh -c` ou `dash -c` recebe argumentos posicionais adicionais (ex: `bash -c 'rm -rf "$0"' /`), substitui `$0`, `$1`..., `${0}` e `"$@"` / `$@` pelos respectivos valores antes da avaliação recursiva com o gate inteiro.
   - Corrige o tratamento de alvos literais posicionais que antes eram classificados como desconhecidos.

3. **Invariante de Prefixos no Fuzz Diferencial & Prova de Falsificabilidade**:
   - Implementado o método `test_prefix_invariants` em `clearer-engineering/tests/test_gate_differential_fuzz.py`.
   - Garante que para qualquer comando gerado $X$, a execução com prefixo (`nice X`, `timeout 5 X`, `sudo -u x X`, `nohup X`, `exec X`, `eval "X"`, `watch -n1 "X"`) nunca tenha decisão menos severa que $X$ em nenhum ambiente.
   - Prova física de falsificabilidade gerada em `scratch/verify_prefix_falsifiability_ab1.py`: ao simular a omissão de `nice` de `resolve_command_head`, o teste reprova com **527 violações** detectadas exclusivamente pela gramática determinística (sem bateria e sem corpus).

---

## 2. Critérios de Aceite Atendidos (`OBSERVED`)

| Critério (Handoff 026) | Estado | Evidência Física |
|---|---|---|
| As 15 linhas `PENDENTE:H026-*` ficam verdes na bateria e controles seguem verdes | **ATENDIDO** | `python3 -m unittest clearer-engineering/tests/test_review_batteries.py` -> 1/1 **OK** (todas as 15 pendências H026 desmarcadas). |
| grep por `"sudo", "rtk", "command"` nos 4 módulos retorna 0 ocorrências duplicadas | **ATENDIDO** | `grep -n '"sudo", "rtk", "command"' ...` -> **0 ocorrências** (apenas 1 definição canônica em `ceh_core/lexer.py`). |
| Fuzz diferencial contra `75a763a` com 0 relaxamentos | **ATENDIDO** | `test_gate_differential_fuzz.py` -> 3/3 **OK** (0 relaxamentos não autorizados). |
| Invariante de prefixos implementada no fuzz | **ATENDIDO** | `test_prefix_invariants` executado com 8.400 avaliações -> **OK** (0 violações). |
| Prova de falsificabilidade do AB1 comprovada sem bateria/corpus | **ATENDIDO** | `scratch/verify_prefix_falsifiability_ab1.py` acusa **527 violações** ao omitir `nice`. |
| Justificativa linha a linha do corpus em `pr06c-corpus-diff.md` | **ATENDIDO** | `docs/temp_implementation/evidence/pr06c-corpus-diff.md` comprova snapshot 100% conforme (diff vazio). |
| Suíte canônica de testes | **ATENDIDO** | `test-runner.sh` -> **53/53 PASS** (100%). |
| Orçamento de linhas respeitado em todos os módulos | **ATENDIDO** | `doc-audit.sh` -> **7/7 checks PASS** (`lexer.py`: 271 linhas ≤ 300). |
| Plano de implementação mantido intacto sem edição pelo agente | **ATENDIDO** | `git status` comprova zero alterações em `docs/plano-implementacao-elevacao-ceh.md`. |

---

## 3. Prova Física de Falsificabilidade (AB1)

Execução do script `scratch/verify_prefix_falsifiability_ab1.py`:
- **Condições:** `gate_corpus.txt` e `review_batteries.txt` completamente esvaziados. Apenas comandos gerados pela gramática determinística (`seed=42`).
- **Defeito simulado:** omissão do prefixo `nice` de `resolve_command_head`.
- **Resultado (`OBSERVED`):**
  - Comandos gerados por gramática (alvo de analisadores): 2.316.
  - Execução com PR-06c íntegro: **0 violações**.
  - Execução com `nice` omitido: **527 violações detectadas**.
  - Exemplos de violações capturadas:
    - `[production] nice: base=deny > prefix=allow para: git --no-pager restore --staged --worktree ./`
    - `[production] nice: base=deny > prefix=allow para: git --no-pager checkout .. src/..`
    - `[production] nice: base=deny(cat=True) > prefix=allow para: perl -e "use File::Path; rmtree('~')"`
    - `[development] nice: base=deny > prefix=allow para: git --no-pager push origin main`

---

## 4. Estado da Suíte de Testes e Snapshot

- **Suíte Canônica (`test-runner.sh`):** 53/53 PASS.
  - Test 52 (`Review Batteries`): PASS (343 casos validados, 0 pendências abertas).
  - Test 53 (`Differential Fuzz`): PASS (11.850 casos validados contra `75a763a`).
  - Test 46 (`Documentation Audit`): PASS (7/7 checagens aprovadas).
  - Test 47 (`Golden Corpus Snapshot`): PASS (diff vazio, 1.012 avaliações idênticas).
