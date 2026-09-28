# Evidência Técnica de Implementação — PR-19b

**Data:** 2026-09-27  
**PR:** PR-19b — `chore(shell): limpeza de avisos do shellcheck e shellcheck bloqueante`  
**Branch:** `claude/code-review-technical-analysis-kfwcdl`  
**Commit Base:** `0884873` (Handoff 044 — Revisão PR-19a e Despacho PR-19b)  
**Commit de Falsificabilidade:** [`1893cd6`](https://github.com/nandinhos/antigravity-clearer-engineering-harness/commit/1893cd6053bb3daaa22ff4dc1ea34db72cbc2416) (Falsificação comprovada no servidor)  
**Commit Final Aprovado:** [`d2b0a26`](https://github.com/nandinhos/antigravity-clearer-engineering-harness/commit/d2b0a26758714962ebf20206417bfb36956220fe)  
**Status:** IMPLEMENTADO E CERTIFICADO VERDE NO CI DO SERVIDOR (4/4 JOBS SUCCESS)  

---

## 1. Resumo Executivo das Resoluções

O PR-19b cumpre integralmente os requisitos normativos do [Handoff 044](../handoffs/handoff-044-revisao-pr19a-ci-verde-despacho-pr19b.md):

1. **Linha de Base do Shellcheck & Limpeza Semântica (26 avisos eliminados)**:
   - Os 26 avisos mapeados no servidor foram categorizados e corrigidos semanticamente em todos os scripts shell:
     - `clearer-engineering/config/aliases.sh`: Adicionado `# shellcheck shell=sh` (elimina SC2148).
     - `clearer-engineering/scripts/detect-project.sh`: Corrigidos 3 avisos SC2076 substituindo regex literal por matching glob `== *" ... "*`.
     - `clearer-engineering/scripts/task-monitor.sh`: Corrigido SC2009 via disable justificado inline para `ps -eo pid,etime,args` formatado em tabela.
     - `clearer-engineering/scripts/test-runner.sh`: Corrigido SC2076 e removidas variáveis não utilizadas `DOCKER_RUNNING`, `START_TIME` e `END_TIME` (elimina SC2034).
     - `clearer-engineering/tests/run-adversarial-tests.sh`: Corrigido SC2164 (`cd || exit 1`) e refatorado subshell condicional eliminando padrão `A && B || C` (SC2015).
     - `clearer-engineering/tests/run-all-tests.sh`: Corrigido SC2164 e substituída função de trap por comando inline `trap 'rm -rf "$TMP_HOME"' EXIT` (elimina SC2317 e previne SC2329).
     - `clearer-engineering/tests/run-e2e-simulation.sh`: Removida variável `YELLOW` não utilizada (SC2034), substituído `! git show-ref` por condicional `if` idiomático (SC2251) e inlinado o trap.
     - `clearer-engineering/tests/run-install-verification.sh`: Corrigidos redirecionamentos sem comando `: > "$MOCK_GIT_LOG"` (SC2188), documentados pipes de teste via disable inline explicativo (SC2002) e inlinado o trap.
     - `evals/run.sh`: Removidas funções mortas `log_info`/`log_warn` e cores associadas (SC2317, SC2034) e removido parâmetro `label` não utilizado em `run_suite` (SC2034).
     - `install.sh`: Adicionada anotação defensiva `# shellcheck disable=SC2317,SC2329` em `cleanup()`.

2. **Shellcheck Bloqueante no GitHub Actions**:
   - Em `.github/workflows/ci.yml`, removido `continue-on-error: true` e `|| true`.
   - Adicionado `set -o pipefail` para garantir falha estrita caso o `shellcheck` emita qualquer aviso.

3. **Prova Formal de Falsificabilidade no Servidor**:
   - No commit temporário [`1893cd6`](https://github.com/nandinhos/antigravity-clearer-engineering-harness/commit/1893cd6053bb3daaa22ff4dc1ea34db72cbc2416), introduzida variável não cotada em `task-monitor.sh`.
   - **Resultado no CI**: A esteira no GitHub Actions barrou a execução no Step 10 (`Run Shellcheck (Strict Zero Warnings Gate)`) com exit code 1, abortando todos os 11 steps subsequentes.
   - **Evidência Remota do Bloqueio**: [Job 108661143441](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36333967018/job/108661143441).

4. **Itens de Carona Autorizados (AR1, AP1, AP2, AP3)**:
   - **AR1**: Em `run-e2e-simulation.sh`, renomeada função `test_safety_hook` para `test_gate_check` e adicionada a função `test_actual_hook` enviando payload JSON via stdin com `Cwd` apontando para `$SANDBOX_DIR`, testando e comprovando exit code 0 para allow e exit code 2 para deny (em dev e em main).
   - **AP1 & AP2**: Em `rc_aliases.py`, adicionada remoção preventiva do cabeçalho legado `# === CLEARER Engineering Harness (CEH) ===` via `re.sub(LEGACY_HEADER_REGEX, '', content)` tanto antes da busca do bloco quanto na inserção, utilizando `pattern.sub(lambda _: block, content)`. Adicionado o Teste 6 em `run-install-verification.sh` comprovando a remoção no install e a simetria total no uninstall.
   - **AP3**: No `CHANGELOG.md`, substituída a linha vaga sobre asserções tautológicas por descrição factual explícita da substituição de checagens de constantes em `test_gate_differential_fuzz.py`.

---

## 2. Tabela de Contagem do Shellcheck por Código SC e por Arquivo

### Contagem por Código SC:
| Código SC | Severidade | Descrição / Padrão Corrigido | Ocorrências Resolvidas |
|---|---|---|:---:|
| **SC2002** | style | Useless cat (em testes de one-liner pipe `cat install.sh \| bash`) | 4 |
| **SC2009** | style | Consider using pgrep instead of ps \| grep (tabela com tempo/pid) | 1 |
| **SC2015** | info | Operador `A && B \|\| C` não é if-then-else (refatorado para `if`) | 1 |
| **SC2034** | warning | Variáveis declaradas e não utilizadas (`YELLOW`, `START_TIME`, etc.) | 5 |
| **SC2076** | warning | Don't quote RHS of `=~` / matching literal | 4 |
| **SC2148** | error | Tips depend on target shell (adicionado `# shellcheck shell=sh`) | 1 |
| **SC2164** | warning | Use `cd ... \|\| exit` in case cd fails | 2 |
| **SC2188** | warning | Redirection without command (trocado `> file` por `: > file`) | 4 |
| **SC2251** | info | `!` skips errexit (trocado por `if git show-ref; then ... fi`) | 1 |
| **SC2317** / **SC2329** | note | Command/function unreachable or never invoked (funções de trap) | 3 |
| **Total** | | | **26** |

### Contagem por Arquivo:
| Arquivo | Avisos Originais | Status Atual |
|---|:---:|:---:|
| `clearer-engineering/config/aliases.sh` | 1 | 🟢 0 (Clean) |
| `clearer-engineering/scripts/detect-project.sh` | 3 | 🟢 0 (Clean) |
| `clearer-engineering/scripts/task-monitor.sh` | 1 | 🟢 0 (Clean) |
| `clearer-engineering/scripts/test-runner.sh` | 4 | 🟢 0 (Clean) |
| `clearer-engineering/tests/run-adversarial-tests.sh` | 2 | 🟢 0 (Clean) |
| `clearer-engineering/tests/run-all-tests.sh` | 2 | 🟢 0 (Clean) |
| `clearer-engineering/tests/run-e2e-simulation.sh` | 2 | 🟢 0 (Clean) |
| `clearer-engineering/tests/run-install-verification.sh` | 8 | 🟢 0 (Clean) |
| `evals/run.sh` | 3 | 🟢 0 (Clean) |
| `install.sh` | 0 | 🟢 0 (Clean) |
| `uninstall.sh` | 0 | 🟢 0 (Clean) |
| **Total Global** | **26** | 🟢 **0 AVISOS** |

---

## 3. Validação Local Pré-Push (`OBSERVED`)

| Verificação | Comando | Resultado Observado | Status |
|---|---|---|---|
| **ShellCheck Global** | `find clearer-engineering/ evals/ -name "*.sh" -exec shellcheck -f gcc {} + && shellcheck -f gcc install.sh uninstall.sh` | 0 avisos (exit code 0) | **PASS** |
| **Suíte Canônica Oficial** | `bash clearer-engineering/scripts/test-runner.sh` | 58/58 testes herméticos aprovados (100%) | **PASS** |
| **Full E2E Simulation (AR1)** | `bash clearer-engineering/tests/run-e2e-simulation.sh` | 30/30 checagens aprovadas (incluindo stdin com Cwd e exit codes 0/2) | **PASS** |
| **Install Verification (AP1)** | `bash clearer-engineering/tests/run-install-verification.sh` | 6/6 testes aprovados (incluindo remoção de cabeçalho legado e simetria) | **PASS** |
| **Doc Audit** | `bash clearer-engineering/scripts/doc-audit.sh` | 7/7 checagens estruturais aprovadas | **PASS** |

---

## 4. Certificação Remota no GitHub Actions (`OBSERVED`)

- **Workflow Run**: [GitHub Actions Run 36334627564](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36334627564)
- **Commit**: [`d2b0a26`](https://github.com/nandinhos/antigravity-clearer-engineering-harness/commit/d2b0a26758714962ebf20206417bfb36956220fe)
- **Veredito Geral**: **SUCCESS (4/4 Jobs Verdes, 21/21 Steps em cada Job)**

### Matriz de Execução Multiplataforma

| Job | OS Runner | Python | Steps Concluídos | Conclusão | URL Exata do Job |
|---|---|---|---|---|---|
| **Validate (ubuntu-latest - Python 3.9)** | `ubuntu-latest` | `3.9` | 21/21 | **`success`** | [Job 108663006123](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36334627564/job/108663006123) |
| **Validate (ubuntu-latest - Python 3.12)** | `ubuntu-latest` | `3.12` | 21/21 | **`success`** | [Job 108663006081](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36334627564/job/108663006081) |
| **Validate (macos-latest - Python 3.9)** | `macos-latest` | `3.9` | 21/21 | **`success`** | [Job 108663005968](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36334627564/job/108663005968) |
| **Validate (macos-latest - Python 3.12)** | `macos-latest` | `3.12` | 21/21 | **`success`** | [Job 108663006112](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36334627564/job/108663006112) |
