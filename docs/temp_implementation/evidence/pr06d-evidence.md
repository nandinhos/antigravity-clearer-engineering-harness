# Relatório de Evidências — PR-06d (Varredura de Sufixos após Prefixo / Fail-Closed)

**Data/Hora:** 2026-09-26T01:38:00-03:00  
**Branch:** `claude/code-review-technical-analysis-kfwcdl`  
**Referência / Baseline:** `3ac81b0` (PR-06c homologado com ressalvas no Handoff 027)  
**Handoff de Origem:** Handoff 027 (`6ff77b3`)  
**Ambiente:** `development` (detectado: Default workspace fallback)  

---

## 1. Sumário Executivo do PR-06d

O **PR-06d** resolve de forma definitiva o achado **AC1** (médio) do Handoff 027, fechando a classe de prefixos com a estratégia fail-closed de **varredura de sufixos após prefixo conhecido**, eliminando a dependência de tabelas exaustivas de opções escritas de memória:

1. **AC1 — Varredura Fail-Closed de Sufixos em `safety-gate.py`**:
   - Quando o token inicial do comando (`tokens[0]`, pelo `os.path.basename`) for um prefixo conhecido (`KNOWN_PREFIXES`), o gate varre todos os tokens subsequentes procurando qualquer ocorrência cujo nome base seja uma cabeça analisada (`ANALYZED_HEADS`: `rm`, `git`, `find`, `sh`, `bash`, `zsh`, `dash`, `node`, `perl`, `ruby`, `eval`, `su`, `watch` ou iniciando com `python`).
   - Para cada sufixo detectado, avalia recursivamente via `evaluate_command(suffix_cmd, depth=depth+1)` e aplica a regra de composição do PR-06b (`max_severity_decision`), ficando sempre com a decisão mais severa.
   - Assim, comandos como `sudo --user deploy find / -delete`, `sudo -iu root find / -delete`, `taskset -c 0 find / -delete`, `xargs --max-args 1 find / -delete` ou `sudo --user deploy git checkout -- .` são bloqueados de forma determinística e incondicional, independentemente de qual opção desconhecida anteceda o comando.
   - **Custo aceito e documentado:** se o valor de uma opção coincidir com o nome de uma cabeça analisada (ex: `sudo -u git …`), o gate pode gerar falso positivo sempre na direção de maior segurança (fail-closed).
2. **`env -S` / `--split-string` como Executor de String**:
   - Em `ceh_core/lexer.py`, `resolve_command_head` trata `env -S <cmd>` e `env --split-string=<cmd>` como executores de string, extraindo a string interna para reavaliação recursiva completa pelo gate.
3. **Semântica de `taskset` e Agrupamentos de Opções**:
   - Em `ceh_core/lexer.py`, `taskset` só consome máscara posicional se **não** houver a flag `-c` ou `--cpu-list`, evitando que `find` ou outro comando seja tomado como máscara de CPU.
   - Em `_consume_flags`, agrupamentos de flags que terminam em opção que recebe valor (ex: `-iu root`) consomem o próximo token como argumento.
4. **Invariante de Prefixos Expandida & Falsificabilidade**:
   - No `test_gate_differential_fuzz.py`, a lista da invariante foi estendida com `sudo --user x`, `sudo -iu x`, `taskset -c 0`, `xargs --max-args 1`, `nice --adjustment 5`, `timeout --signal KILL 5` e `env -S`.
   - Prova física de falsificabilidade documentada em `scratch/verify_suffix_scan_falsifiability_ac1.py`: com corpus e bateria vazios, ao desligar exclusivamente a varredura de sufixos, o teste reprova com **527 violações** detectadas puramente pela gramática determinística para `sudo --user x`.

---

## 2. Critérios de Aceite Atendidos (`OBSERVED`)

| Critério (Handoff 027 §3) | Estado | Evidência Física |
|---|---|---|
| As 6 linhas `PENDENTE:H027-AC1` ficam verdes e controles seguem verdes | **ATENDIDO** | `python3 -m unittest clearer-engineering/tests/test_review_batteries.py` -> 1/1 **OK** (todas as 6 pendências H027 desmarcadas). |
| Diferencial contra `3ac81b0` com 0 relaxamentos | **ATENDIDO** | `test_gate_differential_fuzz.py` -> 3/3 **OK** (11.877 casos avaliados com 0 relaxamentos). |
| Invariante de prefixo com opções com valor ativa | **ATENDIDO** | `test_prefix_invariants` cobre os 14 prefixos e formas longas/agrupadas com 0 violações. |
| Prova de falsificabilidade da varredura de sufixos sem bateria/corpus | **ATENDIDO** | `scratch/verify_suffix_scan_falsifiability_ac1.py` acusa **527 violações** para `sudo --user x` ao desligar a varredura. |
| Justificativa linha a linha do corpus em `pr06d-corpus-diff.md` | **ATENDIDO** | `docs/temp_implementation/evidence/pr06d-corpus-diff.md` comprova snapshot 100% conforme (diff vazio). |
| Suíte canônica de testes | **ATENDIDO** | `test-runner.sh` -> **53/53 PASS** (100%). |
| Orçamento de linhas de código respeitado | **ATENDIDO** | `doc-audit.sh` -> **7/7 checks PASS** (`lexer.py`: 286 linhas ≤ 300; `safety-gate.py`: 571 linhas ≤ 650). |
| Plano de implementação mantido intacto sem edição pelo agente | **ATENDIDO** | `git status` comprova zero alterações em `docs/plano-implementacao-elevacao-ceh.md`. |

---

## 3. Prova Física de Falsificabilidade (AC1)

Execução do script `scratch/verify_suffix_scan_falsifiability_ac1.py`:
- **Condições:** `gate_corpus.txt` e `review_batteries.txt` completamente esvaziados. Apenas comandos gerados pela gramática determinística (`seed=42`).
- **Defeito simulado:** desligamento exclusivo da varredura de sufixos em `safety-gate.py`.
- **Resultado (`OBSERVED`):**
  - Comandos gerados por gramática (alvo de analisadores): 2.316.
  - Execução com PR-06d íntegro (varredura ativa): **0 violações**.
  - Execução com varredura desligada: **527 violações detectadas**.
  - Exemplos de violações capturadas:
    - `[production] sudo --user x: base=deny > prefix=allow para: git --no-pager restore --staged --worktree ./`
    - `[production] sudo --user x: base=deny > prefix=allow para: git --no-pager checkout .. src/..`
    - `[production] sudo --user x: base=deny(cat=True) > prefix=allow para: perl -e "use File::Path; rmtree('~')"`
    - `[development] sudo --user x: base=deny > prefix=allow para: git --no-pager push origin main`
