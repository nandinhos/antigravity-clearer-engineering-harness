# Evidência Técnica de Implementação — PR-19a

**Data:** 2026-09-27  
**PR:** PR-19a — `fix(ci): clone real via file://, prova no bash 3.2 e CI verde nos 4 jobs`  
**Branch:** `claude/code-review-technical-analysis-kfwcdl`  
**Commit Base:** `8c5f676` (Handoff 043 — Revisão PR-19 e Despacho PR-19a)  
**Status:** IMPLEMENTADO E EM MONITORAMENTO NO CI DO SERVIDOR  

---

## 1. Resumo Executivo das Resoluções

O PR-19a resolve em definitivo todos os apontamentos do [Handoff 043](../handoffs/handoff-043-revisao-pr19-ci-vermelho-despacho-pr19a.md) e as incompatibilidades multiplataforma identificadas na primeira execução do servidor:

1. **AQ1 (Correção de `CEH_REPO_URL` no One-Liner Pipe `file://`)**:
   - **Causa Raiz Identificada**: No PR-19 (`dbf470d`), a atribuição `CEH_REPO_URL="file://$GITHUB_WORKSPACE"` prefixava o comando `cat` em vez do interpretador `bash`. Por não ser repassada ao subshell do `bash`, o instalador recorreu ao repositório remoto padrão do GitHub (`main`), que não possuía `profiles/clearer-harness.agent.md`.
   - **Controle Negativo**: A execução remota [run 36326581624](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36326581624) comprova formalmente a falha honesta do instalador (exit code 1 com `Agent profile source not found`).
   - **Correção Aplicada**: A variável foi movida para o interpretador `bash`: `(cd "$OUTSIDE_DIR" && cat "$GITHUB_WORKSPACE/install.sh" | CEH_REPO_URL="file://$GITHUB_WORKSPACE" HOME="$TMP_HOME" bash)`.
   - **Verificação de Origem da Árvore**: Adicionadas checagens estritas via `cmp -s`:
     - `cmp -s "$TMP_HOME/.gemini/config/plugins/clearer-engineering/profiles/clearer-harness.agent.md" "$GITHUB_WORKSPACE/clearer-engineering/profiles/clearer-harness.agent.md"`
     - `cmp -s "$TMP_HOME/.gemini/config/plugins/clearer-engineering/plugin.json" "$GITHUB_WORKSPACE/clearer-engineering/plugin.json"`
     Comprovado com **success** em todos os 4 jobs do servidor ([run 36327885792](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36327885792)).

2. **AQ2 (Prova Formal no Apple Legacy Bash 3.2 do macOS)**:
   - Adicionado step específico `Verify Apple Legacy Bash 3.2 Behavior (macOS)` no workflow do GitHub Actions (`if: runner.os == 'macOS'`), executado com o interpretador nativo `/bin/bash` antes de qualquer alteração de `PATH`:
     1. Log explícito de `/bin/bash --version` (comprovando versão 3.2.57 da Apple).
     2. Verificação sintática via `/bin/bash -n install.sh` e `/bin/bash -n uninstall.sh`.
     3. Teste fail-closed via pipe: `cat install.sh | HOME="$TMP_HOME" /bin/bash` assegurando código de saída não-zero e presença de `"Bash 4.0+ is required"`.
     4. Teste fail-closed direto: `HOME="$TMP_HOME" /bin/bash install.sh` assegurando código de saída não-zero e presença de `"Bash 4.0+ is required"`.
   - Comprovado com **success** em ambos os jobs de macOS ([run 36327885792](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36327885792)).

3. **Compatibilidade Python 3.9 (PEP 604 Union Syntax)**:
   - **Causa Raiz**: No Python 3.9 (Ubuntu e macOS), o Teste 41 (`cluster1_acceptance.py`) falhou com `TypeError: unsupported operand type(s) for |: 'type' and 'NoneType'` na linha 27 (`cmd: str | None = None`) por ausência de `from __future__ import annotations`.
   - **Correção**: Inserido `from __future__ import annotations` no topo de `clearer-engineering/tests/cluster1_acceptance.py`.

4. **Preservação de Checkout Limpo no CI (Higiene de Permissões)**:
   - **Causa Raiz**: O Step 7 do CI executava `chmod +x clearer-engineering/scripts/*` e `chmod +x clearer-engineering/tests/*`. Isso converteu mais de 18 scripts Python de `100644` para `100755`, deixando a working tree do Git suja e disparando `[FAIL] INFRA-FAIL: baseline Git não está limpa` no Step 19 (`evals/run.sh`).
   - **Correção**: Restringido o `chmod +x` estritamente a scripts shell (`*.sh`), preservando as permissões originais dos arquivos Python versionados.
   - Adicionada exibição diagnóstica de arquivos modificados/untracked em `evals/run.sh`.

5. **Compatibilidade E2E sob `set -e` (`run-e2e-simulation.sh`)**:
   - **Causa Raiz**: O Step 21 (`run-e2e-simulation.sh`) falhava com exit code 2 no step 2.1 porque o subshell de atribuição em bash com `set -e` abortava imediatamente quando `safety-gate.py` retornava exit code 2 (código de saída normativo para a decisão `deny`). Além disso, o teste chamava o gate com stdin payload genérico sem `Cwd`, ativando o isolamento de contexto para `production` (Invariante 7).
   - **Correção**: Ajustada a função `test_safety_hook` em `run-e2e-simulation.sh` para invocar a verificação canônica via `--check "$cmd" --env "$env_var" || true`, capturando determininisticamente decisões (`allow`, `ask`, `deny`), razões e alertas de confirmação em todos os 3 tiers sem abortar o interpretador.

6. **AQ3 (Processo de Certificação no Servidor Remoto — 100% GREEN nos 4 Jobs)**:
   - Em cumprimento à regra inegociável do Handoff 043, a entrega técnica deste PR só é declarada após o término comprovado da execução do CI no GitHub Actions com status **success** nos 4 jobs da matriz (`ubuntu-latest` / `macos-latest` × Python 3.9 / 3.12).

---

## 2. Validação Local Pré-Push (`OBSERVED`)

| Verificação | Comando | Resultado Observado | Status |
|---|---|---|---|
| **Suíte Canônica Oficial** | `bash clearer-engineering/tests/run-all-tests.sh` | 58/58 testes herméticos aprovados (100%) | **PASS** |
| **Full E2E Simulation** | `bash clearer-engineering/tests/run-e2e-simulation.sh` | 26/26 checagens verificadas, 0 falhas | **PASS** |
| **Doc Audit** | `bash clearer-engineering/scripts/doc-audit.sh` | 7/7 checagens estruturais aprovadas | **PASS** |
| **Install Verification** | `bash clearer-engineering/tests/run-install-verification.sh` | 5/5 testes (100%) aprovados | **PASS** |
| **Cluster 1 Acceptance** | `python3 clearer-engineering/tests/cluster1_acceptance.py` | 38/38 cenários aprovados | **PASS** |
| **Cluster 2 Acceptance** | `python3 clearer-engineering/tests/cluster2_acceptance.py` | 3/3 testes aprovados em 4.4s | **PASS** |
| **Differential Fuzz** | `python3 -m unittest clearer-engineering/tests/test_gate_differential_fuzz.py` | 12.027 casos avaliados em 4.39s, 0 relaxamentos | **PASS** |
| **Environment Differential** | `python3 -m unittest clearer-engineering/tests/test_environment_differential.py` | 0 divergências entre ambientes | **PASS** |
| **Smoke Evals** | `bash evals/run.sh` | 5/5 critérios aprovados em 1s | **PASS** |

---

## 3. Certificação Remota no GitHub Actions (`OBSERVED`)

- **Execução Oficial**: [GitHub Actions Run 36329793650](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36329793650)
- **Commit**: [`1bb0bf6`](https://github.com/nandinhos/antigravity-clearer-engineering-harness/commit/1bb0bf69722dca98dac9324efcd61eb895e3ca09)
- **Veredito Geral**: **SUCCESS (4/4 Jobs Verdes, 24/24 Steps em cada Job)**

### Matriz de Execução Multiplataforma

| Job | OS Runner | Python | Steps Concluídos | Conclusão | URL do Job |
|---|---|---|---|---|---|
| **Validate (ubuntu-latest - Python 3.9)** | `ubuntu-latest` | `3.9` | 24/24 | **`success`** | [Job 108649419098](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36329793650/job/108649419098) |
| **Validate (ubuntu-latest - Python 3.12)** | `ubuntu-latest` | `3.12` | 24/24 | **`success`** | [Job 108649419114](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36329793650/job/108649419114) |
| **Validate (macos-latest - Python 3.9)** | `macos-latest` | `3.9` | 24/24 | **`success`** | [Job 108649419047](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36329793650/job/108649419047) |
| **Validate (macos-latest - Python 3.12)** | `macos-latest` | `3.12` | 24/24 | **`success`** | [Job 108649419060](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36329793650/job/108649419060) |

### Resumo de Evidências Chave no Servidor
1. **AQ1 (One-Liner Pipe `file://`)**: Aprovado nos 4 jobs com `cmp -s` idêntico ao workspace do commit.
2. **AQ2 (Apple Legacy Bash 3.2)**: Aprovado nos 2 jobs de macOS com versão nativa 3.2.57 e mensagem `"Bash 4.0+ is required"`.
3. **Suíte Canônica Hermética (58 testes)**: 100% PASS em Ubuntu e macOS (Python 3.9 e 3.12).
4. **Shellcheck Summary**: 26 avisos informacionais no baseline, relatório carregado como artefato do workflow.
5. **E2E Simulation Lifecycle**: 26/26 verificações aprovadas nos 4 ambientes.

