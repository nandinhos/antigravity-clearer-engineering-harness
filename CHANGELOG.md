# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.1.0] - 2026-10-01

### Fixed
- **Remediação Integral da Auditoria Hermes (16/16 Achados F01 a F16)**:
  - **F01 (Gate Core)**: Resolução de bypass de tokenização por whitespace e regex ingênuo em subshells (`ceh_core/engine.py`).
  - **F02 (Gate Core)**: Validação canônica estrita de saída em `evaluate_command` garantindo retorno de 4-tupla tipada `(decision, reason, environment, use_case)`.
  - **F03 (Prevenção Catastrófica)**: Inclusão de `rm -rf /*` e `rm -rf ./*` nas regras canônicas de deleção catastrófica (`ceh_core/rules.py`).
  - **F04 (Branch Protection)**: Isolamento de regras de proteção de branch em `ceh_core/rules.py` mitigando race condition no Git Gate.
  - **F05 (Pre-Push Gate)**: Interceptação e bloqueio mandatório de `git pull --rebase` e `git push -f` em branches protegidas de produção (`ceh_core/push.py`).
  - **F06 (Bash Runner)**: Tratamento resiliente de loops em subshells sob `set -e` em `test-runner.sh` (orçamento mantido em 186 linhas).
  - **F07 (Bash Runner)**: Quoting defensivo estrito contra expansões inesperadas no Bash em `test-runner.sh`.
  - **F08 (Bash Runner)**: Isolamento de trap handlers evitando vazamento de códigos de saída em falhas de asserção.
  - **F09 (Empacotador)**: Resolução de caminhos relativos em `tools/package.py` para execuções fora da raiz do repositório.
  - **F10 (Filesystem)**: Normalização canônica de caminhos em `ceh_core/rm.py` com detecção de escape por traversal e wildcards.
  - **F11 (Relatório de Evidências)**: Tratamento defensivo de dependências opcionais no `ceh-evidence-auditor` e `evidence_report.py`.
  - **F12 (Aliases Shell)**: Normalização de aliases em `rc_aliases.py` prevenindo shadowing de binários nativos do sistema operacional.
  - **F13 (Subcomandos)**: Validação estrita de exit code em subcomandos encadeados via `ceh_core/subcommand.py`.
  - **F14 (Instalador)**: Compatibilidade aprimorada com shells Zsh e POSIX/Bash no instalador `install.sh`.
  - **F15 (Baseline Onda 4)**: Validação determinística de integridade de empacotamento contra o manifesto `A2_install_manifest.json`.
  - **F16 (Differential Fuzzing)**: Isolamento hermético de repositório e `HOME` temporários no worker subprocess do teste diferencial.

### Added
- **Bateria de Testes Hermes (`test_hermes_remediation.py`)**: 16 casos de teste unitários e de integração validando individualmente cada achado da auditoria, integrado como Teste 76 da suíte canônica (76/76 PASS).
- **Handoff Técnico de Engenharia (`HANDOFF-HERMES-REMEDIACAO-v2.1.0.md`)**: Registro formal e auditável de remediação para contra-prova pelo agente auditor independente Hermes.
- **Pareceres do Conselho de Seniores**: Atas e pareceres de 5 IAs especialistas (*Claude Code, Codex, Muse, AGY SDK, Agent*) homologando as correções em `docs/temp_implementation/conselho/20261001_auditoria_hermes/`.
- **Compatibilidade CI GitHub Actions**: Validação e aprovação em matriz de 9/9 jobs em Ubuntu e macOS (Python 3.9 a 3.12).


### Changed
- **Arquitetura Multi-Host Desacoplada (Onda 4)**: A lógica de regras e avaliação do Safety Gate foi completamente isolada em `ceh_core.engine`, enquanto o tratamento de I/O, parsing de payloads e renderização de saída foram encapsulados no pacote `adapters/` (`AntigravityAdapter`, `ClaudeAdapter`, `MuseAdapter`).
- **Despachante Minimalista (`safety-gate.py`)**: Reduzido de 630 para 94 linhas de código, eliminando todo acoplamento a formatos de host fora de `adapters/` (de 55 referências para 0).
- **Tipagem Canônica de Hooks**: Normalização do fluxo de execução através de `hook_context.py` com estruturas de dados imutáveis (`HookRequest`, `HookDecision`, `EvaluationContext`).

### Added
- **Suporte Nativo ao Muse Code (`MuseAdapter`)**: Expansão do suporte de hosts de 2 para 3 (Antigravity IDE/CLI, Claude Code e Muse Code).
- **Empacotador Multi-Host (`package.py`)**: Geração determinística de bundles específicos para cada ambiente suportado.
- **Suíte de Conformidade Cross-Host (`test_cross_host_conformance.py`)**: Teste automatizado validando a paridade estrita de decisões entre todos os hosts sobre o corpus canônico (1.016 comandos × 3 hosts) e amostra em subprocesso via shim real.
- **Guia de Integração de Novos Hosts**: Documentação canônica em `docs/adapters/novo-host.md`.
- **Testes de Mutação Estrutural**: Incorporação de `test_mutation_p16.py` e `test_mutation_p17.py` à suíte canônica oficial.

### Security
- **Reserva Emergencial por Host (`adapters/fallback.py`)**: Implementação de resposta de bloqueio estritamente adaptada ao dialeto de cada host diante de falhas de carregamento ou exceções internas. No Muse Code, a reserva emite `{"decision": "block"}`, eliminando a condição de fail-open observada onde a chave `deny` não impedia a execução de comandos.

## [1.4.1] - 2026-09-30

### Security
- **Correção de Bloqueio Fail-Open de Hooks na IDE do Antigravity (E13 / Handoff 067)**: Na IDE do Antigravity, o executor de hooks adota semântica fail-open diante de qualquer código de saída `!= 0`, tratando erros e negações com exit 2 como falha de infraestrutura do hook e permitindo a execução de comandos bloqueados. O `safety-gate.py` passa a responder a negações e erros tratáveis no Antigravity com o JSON de negação e **exit 0**, garantindo o bloqueio efetivo de ferramentas na IDE e no CLI. Para o Claude Code, o contrato com exit 2 e `hookSpecificOutput` permanece estritamente preservado. **Atenção:** Instalações anteriores na tag `v1.4.0` não bloqueavam ferramentas na IDE do Antigravity e devem atualizar imediatamente para a `v1.4.1`.

## [1.4.0] - 2026-09-29

### Security
- **Conserto Crítico de Fork Bomb na Linha Completa**: Descoberto na integração com o Muse que comandos catastróficos compostos (contendo `;`, `|`, `&`) podiam escapar de validações preliminares se fatiados prematuramente. A verificação catastrófica passa a avaliar a linha bruta integral antes de qualquer fatiamento léxico. **Atenção:** Instalações fixadas na tag `v1.3.0` não contêm essa correção e devem atualizar imediatamente para a `v1.4.0`.
- **Prevenção de Vazamento de Segredos e Credenciais Externas (PR-21 / Handoff 062)**: Implementado mascaramento preventivo no Conselho de Seniores (`ceh_core/redact.py`) antes do envio de payloads e geração de prompts para modelos externos. Cobre tokens de Git (`ghp_`, `github_pat_`), AWS (`AKIA...`), Google (`AIza...`), Anthropic/OpenAI (`sk-ant-`, `sk-proj-`), blocos PEM (`BEGIN PRIVATE KEY`), tokens Bearer e caminhos de usuário no SO (`/home/<u>/` e `/Users/<u>/` normalizados para `~`). Exclusão mandatória de arquivos sensíveis (`.env*`, `*.key`, `*.pem`, `*secret*`, `id_rsa*`) em diffs avaliados pelo Conselho.
- **Proteção do Safety Gate contra Evasão por Links Simbólicos (D04 / Handoff 059)**: Resolução de caminhos simbólicos para seu destino canônico real (`os.path.realpath`) antes da avaliação de diretórios protegidos e ancestrais no Safety Gate, impedindo contornos por symlinks.

### Added
- **Onda 5 (PR-23 — Fechamento da Onda 5 e Limites Conhecidos do Gate Estático)**:
  - Cobertura de opções globais do Docker (`--context`, `-H`, `--config`) antes de subcomandos de volume (`volume rm/prune`) e compose (`compose down -v`), bloqueando tentativas de bypass em produção (`H062-B1`).
  - Documentação formal no ADR 007 da seção "Limites conhecidos do gate estático" (Regra P2): explicitação dos limites físicos de análise estática (`curl | bash`, conexões remotas `ssh`, código dinâmico vindo de arquivo ou eval) fixados por testes de controle (`H062-LIMITE`), onde a proteção real reside na esteira de CI do servidor e branch protection.
  - Auditoria documental expandida em `doc-audit.py`: detecção e bloqueio de qualquer caminho absoluto de home (`/home/<u>/` e `/Users/<u>/`) e sanitização integral de atas do Conselho.
- **Onda 5 (PR-22 — Cobertura Abrangente de Regras de Dados, Infraestrutura e Integridade .ceh)**:
  - Proteção de banco de dados e migrações contra comandos destrutivos (`migrate:fresh`, `db:wipe`, `DROP/TRUNCATE`).
  - Proteção para ferramentas de infraestrutura como código e cloud (`terraform destroy`, `kubectl delete`).
  - Bateria formal de regras de infraestrutura e dados em `test_rules_data_infra.py`.
- **Onda 5 (PR-20 — Ancoragem Dinâmica de Atas do Conselho e Fallback sem Git)**:
  - Ancoragem determinística de relatórios do Conselho de Seniores (`docs/temp_implementation/conselho/`) ao repositório do usuário (`$REPO_ROOT`), com fallback seguro em diretório de execução e flag `--output-dir`.
  - Conformidade com o critério AU4: atas registram status de ausência de conselheiros sem injetar texto nos arquivos brutos de parecer.
- **Onda 5 (PR-QA-B, PR-QA-C, PR-QA-D — Invariantes Estruturais de Regras e Normalização)**:
  - `PR-QA-B`: Invariante do motivo da decisão preservado sobre todo o corpus e bateria de testes.
  - `PR-QA-C`: Contrato de opções de escrita derivado automaticamente de `--help`.
  - `PR-QA-D`: Ponto único e estrito de normalização léxica de comandos no Safety Gate.
- **Expansão da Suíte Canônica**: Suíte de testes expandida para 65/65 testes automatizados (100% PASS), cobrindo hermetismo em ambientes CI sem CLIs de IA instalados.

### Changed
- URLs de instalação fixada atualizadas de `v1.3.0` para `v1.4.0` na documentação.
- Metadados do plugin atualizados para a versão `1.4.0` em `clearer-engineering/plugin.json`.

## [1.3.0] - 2026-09-27

### Added
- **Onda 5 (PR-19 & PR-19a — CI Multiplataforma, Shellcheck, Prova no Bash 3.2 e Branch de Trabalho)**:
  - CI workflow triggers expanded in [`.github/workflows/ci.yml`](./.github/workflows/ci.yml) to run on `push` to `claude/**` branches and `workflow_dispatch`, enabling server-side CI verification during active development without requiring PR opening.
  - Multiplatform test matrix across `os: [ubuntu-latest, macos-latest]` and `python-version: ['3.9', '3.12']` (4 matrix jobs total).
  - Informative `shellcheck` step analyzing all 19 `.sh` repository scripts plus `install.sh` and `uninstall.sh` with `continue-on-error: true`, automated baseline SCxxxx counting, and artifact upload (`shellcheck-report.txt`).
  - Automated one-liner pipe installation test steps in CI: offline execution with mock git and local clone execution via `CEH_REPO_URL="file://$GITHUB_WORKSPACE"`.
  - Fix variable placement in one-liner pipe CI step (`cat ... | CEH_REPO_URL=... bash`), verifying installed assets identity byte-by-byte (`cmp -s`) against the commit workspace (AQ1).
  - Explicit macOS CI test step validating fail-closed behavior, syntax, and user remediation guidance under native Apple Legacy Bash 3.2 (AQ2).
  - Pinned repository URL support in [`install.sh`](./install.sh) via `CEH_REPO_URL` (defaults to canonical GitHub repo), enabling network-isolated local integration testing.
- **Onda 5 (PR-19b — Limpeza Semântica do Shellcheck e Shellcheck Bloqueante)**:
  - Eliminated all 26 warnings across 9 repository shell scripts, establishing a zero-warning clean baseline.
  - Shellcheck converted to a strict blocking gate in CI workflow without `continue-on-error` or suppressed pipelines.
  - End-to-end integration test (`run-e2e-simulation.sh`) updated to test safety gates (`test_gate_check`) and actual stdin hook execution (`test_actual_hook`) with sandbox `Cwd`, checking both decision and exit code.
  - Safe alias substitution in `rc_aliases.py` using lambda replacement (`pattern.sub(lambda _: block, content)`) and legacy header removal in `install.sh`.
- **Onda 5 (PR-19c — Shellcheck Fixado por Versão e SHA-256 em Job Único)**:
  - Shellcheck pinned strictly to official upstream binary release `v0.11.0` (Linux x86_64) with cryptographic SHA-256 checksum verification (`8c3be12b05d5c177a04c29e3c78ce89ac86f1595681cab149b65b97c4e227198`).
  - Linter step scoped to execute exclusively in a single matrix job (`ubuntu-latest` / Python 3.12), removing `shellcheck` package dependencies from `apt` and `brew` to eliminate cross-platform linter drift and rolling-release regressions.
- **Onda 5 (PR-18 & PR-18b — Validação de Esquema no Lugar de Grep em Markdown, Catálogo Verificado e Fuzzing do Lexer / T3)**:
  - Formal schema validation in `clearer-engineering/tests/test_content_schema.py` replacing brittle grep assertions for agent profiles, subagents, and YAML frontmatter (`name`, `description`).
  - Versioned tool catalog [`clearer-engineering/config/tool_catalog.json`](./clearer-engineering/config/tool_catalog.json) (v1.1.0) with strict evidence provenance taxonomy: 4 payload-backed (`run_command`, `write_to_file`, `Bash`, `Write`), 1 host-doc-backed (`Edit`), and 18 declared tools transparently labeled with origin and rationale.
  - Resolution check for all `/skill` invocations ensuring every referenced skill resolves to an existing physical `skills/<name>/SKILL.md`.
  - Relative link validator ensuring all relative Markdown links in plugin documentation resolve to valid target files, with fixes for 24 broken relative links in [`clearer-engineering/README_PT.md`](./clearer-engineering/README_PT.md) and [`clearer-engineering/README.md`](./clearer-engineering/README.md).
  - Mathematical roundtrip property test for the shell lexer (`split(join(segs)) == segs`) in `clearer-engineering/tests/test_lexer_fuzz.py`, supporting delimiters in quotes and subshells as atomic units with strict falsifiability proof.
  - Deterministic property-based in-process safety gate fuzzing with fixed seed 1337, executing 2,000 composite command permutations in ~0.58s to verify the formal invariant that no destructive command chain can yield an `allow` decision in production.
  - Integration of `test_content_schema.py` and `test_lexer_fuzz.py` directly into `run-all-tests.sh` with physical falsifiability proofs documented.
- **Onda 3 (PR-12 & PR-12b)**:
  - Canonical agent profile extracted from heredoc to [`clearer-engineering/profiles/clearer-harness.agent.md`](./clearer-engineering/profiles/clearer-harness.agent.md) with byte-by-byte identity verification (`cmp -s`) during installation ([Handoff 040](./docs/temp_implementation/handoffs/handoff-040-revisao-pr11-despacho-pr11b-pr12.md)).
  - Pipe-aware one-liner execution in [`install.sh`](./install.sh) (`cat install.sh | bash`) fixing `BASH_SOURCE[0]: unbound variable` (AO2) and ensuring non-zero exit codes on failure ([Handoff 041](./docs/temp_implementation/handoffs/handoff-041-revisao-pr11b-pr12-despacho-pr12b.md)).
  - Single canonical rc alias manager in [`clearer-engineering/scripts/rc_aliases.py`](./clearer-engineering/scripts/rc_aliases.py) eliminating regex heuristics and preserving user custom aliases byte by byte (AO1).
  - Pinned version installation support via `CEH_VERSION=1.3.0` in [`install.sh`](./install.sh) using `--depth 1 --branch "v${CEH_VERSION#v}"` with explicit warnings when local tree is used (AO3).
  - Comprehensive `CHANGELOG.md` in Keep a Changelog format tracking complete project evolution.
- **Onda 3 (PR-11 & PR-11b)**:
  - Honest CLI validation and post-installation self-diagnosis (3-point check) in [`install.sh`](./install.sh) ([Handoff 040](./docs/temp_implementation/handoffs/handoff-040-revisao-pr11-despacho-pr11b-pr12.md)).
  - Single source of truth for shell aliases in [`clearer-engineering/config/aliases.sh`](./clearer-engineering/config/aliases.sh).
  - Automated installation verification suite in [`clearer-engineering/tests/run-install-verification.sh`](./clearer-engineering/tests/run-install-verification.sh) covering idempotency, symmetry, file identity, honesty, pipe execution, and safe uninstallation.
  - Safe uninstallation engine in [`uninstall.sh`](./uninstall.sh) fixing AN1 (prefix length newline preservation), AN2 (anchored line matching for orphan aliases, preventing corruption of user comments and custom aliases), and AN3 (fail-closed Python block with explicit exit code propagation).
- **Onda 2 (G7, Hook Fail-Closed & G9 / PR-08 a PR-10b)**:
  - Pre-Push CI Gate (G7) checking local canonical test suite execution (`.ceh/last-ci-run.json`) prior to `git push` on repositories with active CI workflows ([Handoff 035](./docs/temp_implementation/handoffs/handoff-035-encerramento-onda-1-despacho-pr08.md), [Handoff 036](./docs/temp_implementation/handoffs/handoff-036-revisao-pr08-despacho-pr08b-pr09.md), [Handoff 037](./docs/temp_implementation/handoffs/handoff-037-revisao-pr08b-pr09-despacho-pr10.md)).
  - Defense-in-depth protection for `.ceh/` directory preventing terminal commands and agent write tools from overwriting or forging test certificates (ADR 007 — with primary enforcement residing in server branch protection and required status checks) ([Handoff 038](./docs/temp_implementation/handoffs/handoff-038-revisao-pr10-despacho-pr10b.md), [Handoff 039](./docs/temp_implementation/handoffs/handoff-039-encerramento-onda-2-despacho-onda-3.md)).
  - Fail-closed hook evaluation in `agy` pre-execution hook, rejecting malformed, empty, or unparseable payloads.
  - Granular Git refspec parser identifying destructive deletions (`:main`, `--delete main`, `-d origin main`) and branch tracking discrepancies.
- **Onda 1 (G1–G6 / PR-04 a PR-07e)**:
  - AST-aware lexical parsing, environment context classification (`DEV`/`HOMOLOGACAO`/`PRODUCAO`), and destructive command detection (`rm -rf`, `DROP TABLE`, `migrate:fresh`) across diverse shell syntax patterns ([Handoff 013](./docs/temp_implementation/handoffs/handoff-013-homologacao-pr03-e-despacho-pr04.md) to [Handoff 035](./docs/temp_implementation/handoffs/handoff-035-encerramento-onda-1-despacho-pr08.md)).
  - Context shift protections (G6): block compounds `{ cd X; ...; }`, `env -C`, `sudo -D`, `GIT_DIR`/`GIT_WORK_TREE`, and in-command branch switching (`git checkout main && ...`).
  - Strict line-count and architectural budgets across core modules (`ceh_core/*.py` <= 300, `safety-gate.py` <= 650, `test-runner.sh` <= 200).
- **Onda 0 & P0 (PR-00 a PR-03)**:
  - Initial foundation, evidence-driven test runner adapter (`NATIVE_HOST` vs `DOCKER_ACTIVE`/`SAIL`), and deterministic smoke-eval suite ([Handoff 001](./docs/temp_implementation/handoffs/handoff-001-reproducao-evidencias-seniors.md) to [Handoff 012](./docs/temp_implementation/handoffs/handoff-012-homologacao-pr02b-e-despacho-pr03.md)).

### Changed
- **Bash 3.2 vs Bash 4+ Decision (Formal Architectural Decision)**:
  - The CEH core suite utilizes associative arrays (`declare -A`) in analytical components ([`conselho-seniores.sh`](./clearer-engineering/scripts/conselho-seniores.sh)), requiring Bash 4.0+.
  - macOS ships with legacy Bash 3.2 by default due to GPLv3 licensing.
  - Decision: Rather than polyfilling or degrading associative array semantics, [`install.sh`](./install.sh) enforces Bash >= 4 in `check_prerequisites`, providing clear, friendly remediation instructions for macOS users (`brew install bash`).
  - In CI, the macOS runner installs modern GNU Bash via Homebrew (`brew install bash coreutils shellcheck`), ensuring full compatibility.
- Replaced non-POSIX `date -Iseconds` with POSIX-compliant `date +"%Y-%m-%dT%H:%M:%S%z"` in [`conselho-seniores.sh`](./clearer-engineering/scripts/conselho-seniores.sh) for macOS/BSD compatibility.
- Replaced `mktemp -d -t` with standard POSIX syntax `mktemp -d "${TMPDIR:-/tmp}/..."` in [`install.sh`](./install.sh), [`run-adversarial-tests.sh`](./clearer-engineering/tests/run-adversarial-tests.sh), [`run-install-verification.sh`](./clearer-engineering/tests/run-install-verification.sh), and [`run-e2e-simulation.sh`](./clearer-engineering/tests/run-e2e-simulation.sh).
- `clearer-engineering/plugin.json`: Version updated to `1.3.0` as single canonical source of version.
- `install.sh`: Refactored to eliminate agent profile heredoc in favor of copying from `clearer-engineering/profiles/clearer-harness.agent.md`.
- `install.sh`: Added support for pinned version clone via `CEH_VERSION` with explicit warnings when local tree is used.
- `install.sh` & `uninstall.sh`: Unified alias management through `clearer-engineering/scripts/rc_aliases.py`.
- `clearer-engineering/tests/run-all-tests.sh`: Updated Test 30 to inspect canonical profile at `clearer-engineering/profiles/clearer-harness.agent.md`.

### Fixed
- Corrected 24 broken relative Markdown links in [`clearer-engineering/README_PT.md`](./clearer-engineering/README_PT.md) and [`clearer-engineering/README.md`](./clearer-engineering/README.md).
- Eliminated all 26 warnings across repository shell scripts, securing a zero-warning blocking Shellcheck gate.
- Fixed uninstaller regression (AN1) where trailing newline stripping caused deletion of user's characters prior to the marker block.
- Fixed uninstaller regression (AN2) where unanchored regexes commented out user configurations and deleted user-defined custom aliases.
- Fixed uninstaller error suppression (AN3) ensuring Python errors are surfaced and cause immediate non-zero exit codes.
- Fixed pipe invocation regression in `install.sh` (AO2) where execution under `set -u` raised `BASH_SOURCE[0]: unbound variable`.
- Fixed heuristic alias removal (AO1) by strictly scoping cleanup to canonical names and CEH signatures, preventing deletion of user aliases ending in `.sh`.
- Replaced tautological constant checks in differential testing (`test_gate_differential_fuzz.py`) with real behavioral mutations executing against the evaluation engine.

### Security
- Defense-in-depth protection for `.ceh/` directory preventing local certificate tampering (ADR 007).
- Pre-push local verification gate for repositories with active CI pipelines.
- Hermetic fixed-version Shellcheck v0.11.0 with SHA-256 integrity verification.
- Deterministic property-based lexer fuzzing and invariant enforcement in production mode.
- Formal tool catalog with physical evidence provenance verification.
