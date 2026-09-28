# Evidência Técnica de Implementação — PR-19

**Data:** 2026-09-27  
**PR:** PR-19 — `ci: matriz de plataformas, shellcheck e CI na branch de trabalho`  
**Branch:** `claude/code-review-technical-analysis-kfwcdl`  
**Commit Base:** `fd32568` (Handoff 042 — Encerramento da Onda 3, Instruções de Release v1.3.0 e Despacho PR-19)  
**Status:** IMPLEMENTADO E SUBMETIDO PARA REVISÃO  

---

## 1. Resumo Executivo das Implementações

O PR-19 abre formalmente a **Onda 5** do CEH, conforme despachado no [Handoff 042](../handoffs/handoff-042-encerramento-onda-3-release-despacho-pr19.md):

1. **Gatilhos de CI Expandidos para Branch de Trabalho (`claude/**`)**:
   - Atualizado `.github/workflows/ci.yml` para disparar em eventos `push` nas branches `claude/**`, `main`, `staging` e `dev`.
   - Adicionado gatilho `workflow_dispatch` para permitir disparos manuais sob demanda no GitHub Actions.
   - Permite verificar a conformidade dos testes e auditorias diretamente no servidor de CI durante o desenvolvimento, sem depender da abertura de Pull Request para acionar o pipeline.

2. **Matriz de Execução Multiplataforma (2x2 = 4 Jobs)**:
   - Configurada matriz combinatória em `.github/workflows/ci.yml`:
     - Sistemas Operacionais: `os: [ubuntu-latest, macos-latest]`
     - Versões do Python: `python-version: ['3.9', '3.12']`
   - O CI do `macos-latest` provisiona GNU Bash moderno, Coreutils e Shellcheck via Homebrew (`brew install bash coreutils shellcheck`), configurando o `PATH` para priorizar `/opt/homebrew/bin` ou `/usr/local/bin`.

3. **Decisão Arquitetural Formal: Bash 3.2 vs. Bash 4+**:
   - **Contexto**: O ecossistema macOS traz por padrão o `/bin/bash` 3.2 (versão legada de 2006, devido à licença GPLv3 adotada a partir do Bash 4.0).
   - **Causa Raiz Técnica**: O CEH utiliza arrays associativos (`declare -A`) em seus componentes analíticos (ex: [`conselho-seniores.sh`](../../../clearer-engineering/scripts/conselho-seniores.sh)), funcionalidade introduzida no Bash 4.0.
   - **Decisão**: Em vez de degradar ou tentar criar polyfills frágeis para arrays associativos, [`install.sh`](../../../install.sh) implementa checagem formal em `check_prerequisites`, exigindo Bash >= 4. Em sistemas com Bash legado (macOS padrão), o instalador falha com código 1 e orienta o desenvolvedor de forma amigável a instalar o GNU Bash atualizado via Homebrew (`brew install bash`).
   - Registrado formalmente no [`CHANGELOG.md`](../../../CHANGELOG.md) na seção `## [Unreleased]`.

4. **Portabilidade BSD / macOS em Scripts Shell**:
   - **Date POSIX**: Substituído o argumento GNU `date -Iseconds` por `date +"%Y-%m-%dT%H:%M:%S%z"` em [`conselho-seniores.sh`](../../../clearer-engineering/scripts/conselho-seniores.sh), compatível nativamente tanto com GNU `date` quanto com BSD `date` do macOS.
   - **Mktemp POSIX**: Padronizada a criação de diretórios temporários substituindo a sintaxe não-portável `mktemp -d -t` por `mktemp -d "${TMPDIR:-/tmp}/..."` em [`install.sh`](../../../install.sh), [`run-adversarial-tests.sh`](../../../clearer-engineering/tests/run-adversarial-tests.sh), [`run-install-verification.sh`](../../../clearer-engineering/tests/run-install-verification.sh) e [`run-e2e-simulation.sh`](../../../clearer-engineering/tests/run-e2e-simulation.sh).
   - **Suporte a `CEH_REPO_URL` em `install.sh`**: Permite sobrepor a URL canônica remota (`https://github.com/...`) por um caminho local (`file://$GITHUB_WORKSPACE`) em cenários de teste automatizado offline.

5. **Passo Automatizado do One-Liner Pipe no CI**:
   - Integrados 2 novos steps no workflow de CI:
     1. **One-Liner Pipe (Offline Mock Git)**: Valida `cat install.sh | bash` em ambiente isolado sem rede, usando mock do `git` para testar fluxo de fallback e argumentos.
     2. **One-Liner Pipe (Local File Clone)**: Valida `cat install.sh | CEH_REPO_URL="file://$GITHUB_WORKSPACE" bash`, executando um clone real do binário `git` do sistema operacional a partir do workspace local sem requisição HTTP externa.

6. **Shellcheck Informativo no CI e Mapeamento de Baseline**:
   - Step `Run ShellCheck (informative)` adicionado ao CI com `continue-on-error: true`.
   - Analisa todos os 19 scripts `.sh` do repositório mais `install.sh` e `uninstall.sh`.
   - Salva e publica o relatório detalhado como artefato de workflow (`shellcheck-report.txt`).
   - Mapeado baseline estático com distribuição dos códigos SCxxxx.

7. **Aviso Normativo de Release**:
   - A tag `v1.3.0` **NÃO** foi criada pelo agente (decisão e prerrogativa do desenvolvedor pós-merge da Onda 3).

---

## 2. Shellcheck Baseline Mapeado (`OBSERVED`)

Varredura executada em todos os 21 scripts shell versionados:
- `clearer-engineering/scripts/test-runner.sh`
- `clearer-engineering/scripts/detect-runtime.sh`
- `clearer-engineering/scripts/preflight-check.sh`
- `clearer-engineering/scripts/ceh-status.sh`
- `clearer-engineering/scripts/ceh-branches.sh`
- `clearer-engineering/scripts/setup-branches.sh`
- `clearer-engineering/scripts/setup-github-protection.sh`
- `clearer-engineering/scripts/diff-audit.sh`
- `clearer-engineering/scripts/doc-audit.sh`
- `clearer-engineering/scripts/conselho-seniores.sh`
- `clearer-engineering/tests/run-all-tests.sh`
- `clearer-engineering/tests/run-e2e-simulation.sh`
- `clearer-engineering/tests/run-evals.sh`
- `clearer-engineering/tests/run-evals-fast.sh`
- `clearer-engineering/tests/run-evals-medium.sh`
- `clearer-engineering/tests/run-adversarial-tests.sh`
- `clearer-engineering/tests/run-install-verification.sh`
- `clearer-engineering/config/aliases.sh`
- `evals/run.sh`
- `install.sh`
- `uninstall.sh`

### Tabela de Códigos ShellCheck (`OBSERVED`)

| Código SC | Ocorrências | Severidade | Descrição / Contexto no CEH |
|---|---|---|---|
| **SC2034** | 6 | warning | Variáveis atribuídas mas aparentemente não usadas (flags de controle / mock helpers). |
| **SC2002** | 4 | style | Uso redundante de `cat file \| cmd` (legibilidade intencional em testes de pipe). |
| **SC2076** | 4 | warning | Aspas literais dentro de `[[ $a =~ "regex" ]]` (comportamento de correspondência exata). |
| **SC2188** | 4 | warning | Redirecionamento sem comando (`> file` para truncamento atômico). |
| **SC2317** | 3 | info | Comandos reachability (código de fallback/trap intencional). |
| **SC2164** | 2 | warning | Uso de `cd` sem checagem de falha explícita (`|| exit`). |
| **SC2009** | 1 | style | Uso de `ps \| grep` em vez de `pgrep`. |
| **SC2015** | 1 | info | Estrutura `A && B \|\| C` condicional. |
| **SC2148** | 1 | error | Script de aliases sem shebang (`aliases.sh` é desenhado para `source`). |
| **SC2251** | 1 | style | Sintaxe de `! cmd` fora de pipeline. |
| **TOTAL** | **27** | — | **Baseline informativo registrado. Nenhum bloqueio no CI (`continue-on-error: true`).** |

---

## 3. Matriz de Testes e Validação Local (`OBSERVED`)

| Teste / Verificação | Comando Executado | Resultado Observado (`OBSERVED`) | Status |
|---|---|---|---|
| **Doc Audit** | `bash clearer-engineering/scripts/doc-audit.sh` | 7/7 checagens aprovadas com conformidade total. | **PASS** |
| **Install Verification** | `bash clearer-engineering/tests/run-install-verification.sh` | Testes 1, 2, 2b (AN1, AO1, AN2, AN3), 3, 4, 5 (5.1-5.5) aprovados. | **PASS** |
| **Gate Differential Fuzz** | `python3 -m unittest clearer-engineering/tests/test_gate_differential_fuzz.py` | 0 relaxamentos observados vs base canônica. | **PASS** |
| **Environment Differential** | `python3 -m unittest clearer-engineering/tests/test_environment_differential.py` | 0 divergências entre ambientes. | **PASS** |
| **Adversarial Safety Matrix**| `python3 -m unittest clearer-engineering/tests/test_safety_matrix.py` | 100% de cenários adversários barrados. | **PASS** |
| **Workflow Syntax Validation**| Validação de esquema YAML de `.github/workflows/ci.yml` | Sintaxe válida, jobs, triggers e steps estruturados. | **PASS** |
