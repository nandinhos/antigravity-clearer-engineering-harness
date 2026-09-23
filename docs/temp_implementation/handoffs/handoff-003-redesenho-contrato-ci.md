# Handoff 003 — Correção mínima do contrato de CI do Cluster 1 (R2/R5)

**Data:** 2026-09-23
**Estado:** Proposta. Nada aqui está aprovado até o owner responder às decisões da seção 9.
**Supera:** [Handoff 002 (Revisão v22)](handoff-002-proposta-desenho-correcoes.md) para R2 e para o force push de R5. O R1 e o `resolve_git_invocation()` de R5 continuam valendo.
**Aprovador:** owner do repositório (nandodev).
**Executor:** agente designado pelo owner, somente depois da aprovação.
**Princípio regente:** Ponytail Mode ([`rules/AGENTS.md`](../../../clearer-engineering/rules/AGENTS.md), seção 6): entender muito, construir pouco, entregar certo.
**Plano vinculado:** [`docs/plano-validacao-revisao-conselho-seniors.md`](../../plano-validacao-revisao-conselho-seniors.md) v0.24.0

---

## 1. Diagnóstico

Da v13 à v22, cada rodada do Handoff 002 acrescentou uma flag proibida (`node -e`, `-p`, `python -c`, `perl -E`, `-pE`, `-fe`). O `safety-gate.py` foi de 391 para 1.209 linhas, e o `test-runner.sh` de 154 para 671. Isso é over-engineering pela própria regra do projeto: o código cresce a cada rodada e o problema não fecha.

O probe abaixo mostra que os defeitos reais eram outros, e que eles cabem em poucas linhas.

## 2. Evidência (G1–G5)

- **Procedimento:** [`scripts/probe_cluster1_contract_gaps.sh`](../scripts/probe_cluster1_contract_gaps.sh).
- **Saída:** [`evidence/cluster1_contract_gaps_probe.txt`](../evidence/cluster1_contract_gaps_probe.txt).
- **Ambiente:** CEH em HEAD `7da7ae2` mais o diff não commitado, Linux 6.18 (WSL2), Python 3.12.3, 2026-09-23T11:46-03:00. Fixtures em `mktemp -d`, sem push.

| ID | Observado | Dentro do modelo? | Tratamento |
|---|---|---|---|
| G1 | Certificado escrito à mão com `echo` → `allow` | Não (exige intenção) | Documentar na ADR. |
| G2 | HEAD quebrado com correção só no worktree → certificado do HEAD e `allow` | **Sim, P0** | Corrigir (3.2). |
| G3 | `git push -f`, `--force-with-lease` e `+ref` sem certificado → `allow` | **Sim, P0** | Corrigir (3.3). |
| G4 | Comando com aspas → certificado com JSON inválido | **Sim** | Corrigir (3.2). |
| G5 | `"test": "python3 -Ic 'exit(0)'"` → `allow` | Não (exige intenção) | Documentar na ADR. |

## 3. Correção

### 3.1 Modelo de ameaça e regra de parada (texto para a ADR 004)

> O certificado local protege contra **erro e atalho de um agente cooperativo**: rodar só parte da suíte, mascarar uma falha com `|| true`, testar um worktree diferente do commit, esquecer de rodar. Contra um agente que decidiu enganar, a autoridade é o **CI remoto**.
>
> **Regra de parada:** um bypass só vira código se um agente apressado puder produzi-lo sem intenção de burlar. Os demais bypasses viram uma linha em "Fora do modelo" e não geram código nem cenário.

### 3.2 `test-runner.sh`: três mudanças cirúrgicas

1. **Canonicidade por igualdade, não por inspeção.** O bloco de auto-detecção que já existe passa a rodar sempre, gerando `DETECTED_CMD`. Assim:
   - `CANONICAL_CMD` é o `canonical_test_command` de `.ceh/config.json`, se existir; senão, é o `DETECTED_CMD`;
   - `CANONICAL_VERIFIED` vale `true` se, e somente se, `RAW_TEST_CMD == CANONICAL_CMD`, comparando o comando antes dos prefixos `rtk` e Sail/Compose;
   - o heredoc `PYEOF` de cerca de 480 linhas é removido por inteiro;
   - a leitura do config troca `grep`/`cut` por um `python3 -c` com `json.load`. JSON inválido resulta em `CANONICAL_VERIFIED=false`.

   Com isso, execução parcial (`pytest tests/test_x.py`), mascaramento (`npm test || true`) e comando arbitrário (`true`) deixam de ser canônicos sem nenhuma heurística: nenhum deles é igual ao comando canônico.
2. **Worktree limpo para certificar (G2).** Se `git status --porcelain -- . ':!.ceh'` não estiver vazio (decisão **D2**), o runner roda os testes normalmente, avisa que o worktree está sujo e **não grava nem altera** o certificado.
3. **Certificado com serialização correta (G4).** O certificado é gravado com `python3 -c 'import json,sys; json.dump(...)'` recebendo os valores como argumentos, no lugar do heredoc `cat << EOF`. Os campos são os mesmos de hoje.

O `eval`, o adaptador de runtime e o `rtk` ficam como estão.

### 3.3 `safety-gate.py`: voltar ao gate do HEAD mais duas regras

- `check_pre_push_ci_gate` volta a ser a versão do HEAD `7da7ae2` (cerca de 80 linhas), com a resolução de `-C` de R5, mais duas regras:
  1. **Gate em todo push (G3):** remover o `return None` quando há `--force`, `-f` ou `+`. A regra de força de `GIT_HISTORY` continua valendo por cima, com precedência `DENY > ASK > ALLOW`.
  2. **Certificado canônico obrigatório:** `deny` quando `commit_hash` estiver ausente ou vazio, ou quando `canonical_verified` for diferente de `True`. O diff atual já faz isso; basta manter.
- Removem-se `check_trivial_or_fake_pass`, `extract_ci_required_scripts`, `_parse_cmd_for_scripts`, toda a inspeção de `package.json`/`composer.json` e o regex de operadores aplicado ao certificado.
- R1 (`split_shell_pipeline`, `normalize_command_for_evaluation` e precedência) e R5 (`resolve_git_invocation`, `find_repo_root`) ficam **sem alteração**.

### 3.4 ADR 004, seção 5

Substituir o texto atual (veto a execução inline, Teorema de Rice, composite actions, wrappers) por três itens:
- o modelo de ameaça e a regra de parada da seção 3.1;
- a lista "Fora do modelo": certificado forjado, código inline de interpretador (família `-e`, `-c`, `-p`, `-E`), conteúdo dos scripts de teste, cobertura dos jobs da CI pelo comando canônico, refspec cuja origem não é o HEAD e testes que alteram arquivos durante a execução;
- a regra de uso: o comando canônico é o que o humano declara em `.ceh/config.json`. Se a CI tem vários jobs, o humano declara um agregador que cubra todos.

## 4. Escada Ponytail aplicada à primeira versão deste handoff

A primeira versão do Handoff 003 (na mesma sessão, nunca executada) propunha mais do que o necessário. Cada item passou pela escada:

| Item proposto | Precisa existir? | Decisão |
|---|---|---|
| Módulo novo `ceh_ci.py` | Não. Sem a denylist, não sobra lógica duplicada entre runner e gate. | Cortado |
| Certificado v2 com `tree_hash`, `config_hash` e `test_definition_hash` | Não. `commit_hash` já fixa a árvore, e o config é commitado. | Cortado |
| Modos exploratório e `--certify` | Não. A igualdade com o comando canônico já decide se certifica. | Cortado |
| Troca do `eval` por `subprocess` sem shell | Não. Um comando diferente do canônico não certifica, então o `eval` não abre brecha. | Cortado |
| Mudança de definição de teste → `ask` | Não. G5 está fora do modelo. | Adiado com gatilho (seção 8) |
| Tripwire de escrita no certificado | Não. G1 está fora do modelo. | Adiado com gatilho (seção 8) |
| Checagem de worktree limpo | **Sim**: G2 é P0 dentro do modelo. | Mantido: uma linha de `git status`. |
| Gate em todo push | **Sim**: G3 é P0. | Mantido: remoção de um `return`. |
| JSON do certificado com `json.dump` | **Sim**: G4 corrompe o certificado. | Mantido: troca do heredoc. |

## 5. Destino dos 58 cenários

| Cenários | Destino |
|---|---|
| R1.1–R1.12 | **Manter** sem mudança. |
| R5.1–R5.8 | **Manter**. R5.7 fica complementado por T2. |
| R2.1–R2.7, R2.9 | **Manter**. Já cobrem certificado ausente, commit divergente e caminho feliz. |
| R2.10 | **Adaptar**. O gate deixa de ler o config, então o cenário passa a ser: runner com `.ceh/config.json` inválido não certifica (`canonical_verified: false`), e o gate responde `deny`. |
| R2.8, R2.11, R2.12 | **Manter**, porque passam pela nova regra de igualdade (suíte parcial, `\|\| true` e alvo parcial não são canônicos). |
| R2.13–R2.38 | **Remover**. Testam conteúdo de script, que está fora do modelo. Os controles positivos (R2.21, R2.36, R2.37) ficam cobertos por R2.7 e R2.9. |

A suíte migra de `docs/temp_implementation/scripts/run_cluster1_acceptance.py` para `clearer-engineering/tests/`, só com os cenários mantidos.

## 6. Testes novos

Os testes entram em `clearer-engineering/tests/run-all-tests.sh`, no formato `run_test` que já existe, e são escritos antes da correção (RED).

| ID | Cenário | Esperado |
|---|---|---|
| T1 | `test-runner.sh` com arquivo rastreado modificado (G2) | nenhum certificado gravado; gate `deny` |
| T2 | `git push -f origin dev` sem certificado, em development (G3) | `deny`, use case `PRE_PUSH_CI` |
| T3 | Comando com aspas (G4) | `.ceh/last-ci-run.json` com JSON válido |
| T4 | `python3 -m unittest tests.test_a` num repositório auto-detectado como `python3 -m unittest` | `canonical_verified: false`; gate `deny` |
| T5 | Config declara `npm test` e o runner roda `npm run test:unit` | `canonical_verified: false`; gate `deny` |
| T6 | Probe G1–G5 reexecutado | G2 sem certificado, G3 `deny`, G4 JSON válido; G1 e G5 com `allow`, documentados como fora do modelo |

## 7. Critérios de aceite

1. `bash clearer-engineering/tests/run-all-tests.sh` e `bash evals/run.sh` terminam com exit 0. Colar as saídas no relatório.
2. `run-all-tests.sh` não referencia `docs/temp_implementation/`.
3. `grep -nE "check_trivial|PYEOF|perl|ruby|--eval|--print|composite|extract_ci_required" clearer-engineering/scripts/` não retorna nada.
4. Orçamento com `wc -l`: `safety-gate.py` ≤ 650 linhas e `test-runner.sh` ≤ 200. Se estourar, parar e levar o motivo ao owner.
5. Nenhum `git push` durante a execução.

## 8. Adiado, com gatilho explícito

| Item | Gatilho para reabrir |
|---|---|
| Mudança de definição de teste → `ask` | Um incidente real em que a definição de teste foi alterada sem intenção e o CI remoto não pegou. |
| Tripwire de escrita em `.ceh/last-ci-run.json` | Um caso real de agente que escreveu o certificado à mão. |
| Execução sem shell | Um comando canônico declarado que precise de quoting que o `eval` quebre. |

## 9. Decisões do owner

| ID | Pergunta | Recomendação |
|---|---|---|
| D1 | O que fazer com as ~1.400 linhas não commitadas | Commit de snapshot no branch `wip/cluster1-denylist` e trabalho a partir dele em `fix/cluster1-contrato-ci`. Isso preserva o R1 e o R5 prontos. |
| D2 | "Worktree limpo" inclui arquivos untracked não ignorados? | Sim: um teste novo não commitado muda o resultado. O custo é o mesmo, porque é o mesmo `git status`. |

## 10. Sequência e proibições

1. D1: `chore (spec): preserva implementação v22 do Cluster 1 antes da correção`
2. T1–T5 em RED: `test (tests): adiciona testes de contrato do certificado de CI`
3. Runner (3.2): `fix (services): certifica só comando canônico em worktree limpo`
4. Gate (3.3): `fix (security): aplica gate de CI em todo push e remove denylist`
5. Migração dos cenários (seção 5): `test (tests): migra cenários R1 e R5 para a suíte permanente`
6. ADR e plano (3.4): `docs (adr): define modelo de ameaça do certificado local de CI`
7. T6: reexecutar o probe e anexar a saída como evidência.

**Proibido:**
- acrescentar flag, padrão ou operador a qualquer lista;
- criar módulo, schema ou modo novo;
- tocar no Cluster 2 (R6–R8) ou em R3, R4, R9 e R10;
- declarar concluído sem as saídas coladas;
- usar links `file:///`.

Um bypass novo passa primeiro pela regra de parada da seção 3.1.
