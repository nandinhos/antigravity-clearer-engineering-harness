# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

### Changed

### Fixed

### Security

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
