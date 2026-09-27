# Evidência Técnica de Implementação — PR-19a

**Data:** 2026-09-27  
**PR:** PR-19a — `fix(ci): clone real via file://, prova no bash 3.2 e CI verde nos 4 jobs`  
**Branch:** `claude/code-review-technical-analysis-kfwcdl`  
**Commit Base:** `8c5f676` (Handoff 043 — Revisão PR-19 e Despacho PR-19a)  
**Status:** IMPLEMENTADO E EM MONITORAMENTO NO CI DO SERVIDOR  

---

## 1. Resumo Executivo das Resoluções

O PR-19a sana todos os achados apontados no [Handoff 043](../handoffs/handoff-043-revisao-pr19-ci-vermelho-despacho-pr19a.md):

1. **AQ1 (Correção de `CEH_REPO_URL` no One-Liner Pipe `file://`)**:
   - **Causa Raiz Identificada**: No PR-19 original (`dbf470d`), a variável `CEH_REPO_URL="file://$GITHUB_WORKSPACE"` prefixava o comando `cat` em vez do interpretador `bash` (`(cd "$OUTSIDE_DIR" && CEH_REPO_URL=... cat install.sh | HOME=... bash)`). Por não estar associada ao subshell do `bash`, a variável foi ignorada, fazendo o instalador recorrer à URL remota padrão do GitHub (`main`), que não possuía a árvore recente com `profiles/clearer-harness.agent.md`.
   - **Controle Negativo**: A execução remota do servidor [run 36326581624](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36326581624) comprova formalmente a falha honesta do instalador (exit code 1 com `Agent profile source not found`).
   - **Correção Aplicada**: A variável foi movida para o lado do interpretador `bash`: `(cd "$OUTSIDE_DIR" && cat "$GITHUB_WORKSPACE/install.sh" | CEH_REPO_URL="file://$GITHUB_WORKSPACE" HOME="$TMP_HOME" bash)`.
   - **Verificação de Origem da Árvore**: Adicionadas checagens estritas via `cmp -s`:
     - `cmp -s "$TMP_HOME/.gemini/config/plugins/clearer-engineering/profiles/clearer-harness.agent.md" "$GITHUB_WORKSPACE/clearer-engineering/profiles/clearer-harness.agent.md"`
     - `cmp -s "$TMP_HOME/.gemini/config/plugins/clearer-engineering/plugin.json" "$GITHUB_WORKSPACE/clearer-engineering/plugin.json"`
     Garantindo que a árvore instalada provém de forma determinística do commit local sob teste.

2. **AQ2 (Prova Formal no Apple Legacy Bash 3.2 do macOS)**:
   - Adicionado step específico `Verify Apple Legacy Bash 3.2 Behavior (macOS)` no workflow do GitHub Actions (`if: runner.os == 'macOS'`), executado com o interpretador nativo `/bin/bash` antes de qualquer alteração de `PATH`:
     1. Log explícito de `/bin/bash --version` (comprovando versão 3.2.x da Apple).
     2. Verificação sintática via `/bin/bash -n install.sh` e `/bin/bash -n uninstall.sh`.
     3. Teste fail-closed via pipe: `cat install.sh | HOME="$TMP_HOME" /bin/bash` assegurando código de saída não-zero e presença de `"Bash 4.0+ is required"`.
     4. Teste fail-closed direto: `HOME="$TMP_HOME" /bin/bash install.sh` assegurando código de saída não-zero e presença de `"Bash 4.0+ is required"`.

3. **AQ3 (Processo de Certificação no Servidor Remoto)**:
   - Em cumprimento à regra inegociável do Handoff 043, a entrega técnica deste PR só é declarada após o término comprovado da execução do CI no GitHub Actions com status **success** nos 4 jobs da matriz (`ubuntu-latest` / `macos-latest` × Python 3.9 / 3.12).

---

## 2. Validação Local Pré-Push (`OBSERVED`)

| Verificação | Comando | Resultado Observado | Status |
|---|---|---|---|
| **Doc Audit** | `bash clearer-engineering/scripts/doc-audit.sh` | 7/7 checagens aprovadas | **PASS** |
| **Install Verification** | `bash clearer-engineering/tests/run-install-verification.sh` | 5/5 testes (100%) aprovados | **PASS** |
| **Differential Fuzz** | `python3 -m unittest clearer-engineering/tests/test_gate_differential_fuzz.py` | 12.027 casos avaliados, 0 relaxamentos | **PASS** |
| **Environment Differential** | `python3 -m unittest clearer-engineering/tests/test_environment_differential.py` | 0 divergências entre ambientes | **PASS** |
| **Smoke Evals** | `bash evals/run.sh` | 5/5 critérios aprovados em 1s | **PASS** |
