# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.3.0] - 2026-09-27

### Added
- **Onda 3 (PR-12)**:
  - Canonical agent profile extracted from heredoc to [`clearer-engineering/profiles/clearer-harness.agent.md`](./clearer-engineering/profiles/clearer-harness.agent.md) with byte-by-byte identity verification (`cmp -s`) during installation ([Handoff 040](./docs/temp_implementation/handoffs/handoff-040-revisao-pr11-despacho-pr11b-pr12.md)).
  - Pinned version installation support via `CEH_VERSION=1.3.0` in [`install.sh`](./install.sh) using `--depth 1 --branch "v${CEH_VERSION#v}"`.
  - Comprehensive `CHANGELOG.md` in Keep a Changelog format tracking complete project evolution.
- **Onda 3 (PR-11 & PR-11b)**:
  - Honest CLI validation and post-installation self-diagnosis (3-point check) in [`install.sh`](./install.sh) ([Handoff 040](./docs/temp_implementation/handoffs/handoff-040-revisao-pr11-despacho-pr11b-pr12.md)).
  - Single source of truth for shell aliases in [`clearer-engineering/config/aliases.sh`](./clearer-engineering/config/aliases.sh).
  - Automated installation verification suite in [`clearer-engineering/tests/run-install-verification.sh`](./clearer-engineering/tests/run-install-verification.sh) covering idempotency, symmetry, file identity, honesty, and safe uninstallation.
  - Safe uninstallation engine in [`uninstall.sh`](./uninstall.sh) fixing AN1 (prefix length newline preservation), AN2 (anchored line matching for orphan aliases, preventing corruption of user comments and custom aliases), and AN3 (fail-closed Python block with explicit exit code propagation).
- **Onda 2 (G7, Hook Fail-Closed & G9 / PR-08 a PR-10b)**:
  - Pre-Push CI Gate (G7) blocking `git push` on repositories with CI workflows unless full canonical test suite passed on the exact local commit hash (`.ceh/last-ci-run.json`) ([Handoff 035](./docs/temp_implementation/handoffs/handoff-035-encerramento-onda-1-despacho-pr08.md), [Handoff 036](./docs/temp_implementation/handoffs/handoff-036-revisao-pr08-despacho-pr08b-pr09.md), [Handoff 037](./docs/temp_implementation/handoffs/handoff-037-revisao-pr08b-pr09-despacho-pr10.md)).
  - Non-tamperable certificate protection (G9/AL1) preventing command lines and file operations from fabricating, modifying, or copying certificates into `.ceh/` ([Handoff 038](./docs/temp_implementation/handoffs/handoff-038-revisao-pr10-despacho-pr10b.md), [Handoff 039](./docs/temp_implementation/handoffs/handoff-039-encerramento-onda-2-despacho-onda-3.md)).
  - Fail-closed hook evaluation in `agy` pre-execution hook, rejecting malformed, empty, or unparseable payloads.
  - Granular Git refspec parser identifying destructive deletions (`:main`, `--delete main`, `-d origin main`) and branch tracking discrepancies.
- **Onda 1 (G1–G6 / PR-04 a PR-07e)**:
  - AST-aware lexical parsing, environment context classification (`DEV`/`HOMOLOGACAO`/`PRODUCAO`), and destructive command detection (`rm -rf`, `DROP TABLE`, `migrate:fresh`) across diverse shell syntax patterns ([Handoff 013](./docs/temp_implementation/handoffs/handoff-013-homologacao-pr03-e-despacho-pr04.md) to [Handoff 035](./docs/temp_implementation/handoffs/handoff-035-encerramento-onda-1-despacho-pr08.md)).
  - Context shift protections (G6): block compounds `{ cd X; ...; }`, `env -C`, `sudo -D`, `GIT_DIR`/`GIT_WORK_TREE`, and in-command branch switching (`git checkout main && ...`).
  - Strict line-count and architectural budgets across core modules (`ceh_core/*.py` <= 300, `safety-gate.py` <= 650, `test-runner.sh` <= 200).
- **Onda 0 & P0 (PR-00 a PR-03)**:
  - Initial foundation, evidence-driven test runner adapter (`NATIVE_HOST` vs `DOCKER_ACTIVE`/`SAIL`), and deterministic smoke-eval suite ([Handoff 001](./docs/temp_implementation/handoffs/handoff-001-reproducao-evidencias-seniors.md) to [Handoff 012](./docs/temp_implementation/handoffs/handoff-012-homologacao-pr02b-e-despacho-pr03.md)).

### Changed
- `clearer-engineering/plugin.json`: Version updated to `1.3.0` as single canonical source of version.
- `install.sh`: Refactored to eliminate agent profile heredoc in favor of copying from `clearer-engineering/profiles/clearer-harness.agent.md`.
- `install.sh`: Added support for pinned version clone via `CEH_VERSION`.
- `clearer-engineering/tests/run-all-tests.sh`: Updated Test 30 to inspect canonical profile at `clearer-engineering/profiles/clearer-harness.agent.md`.

### Fixed
- Fixed uninstaller regression (AN1) where trailing newline stripping caused deletion of user's characters prior to the marker block.
- Fixed uninstaller regression (AN2) where unanchored regexes commented out user configurations and deleted user-defined custom aliases.
- Fixed uninstaller error suppression (AN3) ensuring Python errors are surfaced and cause immediate non-zero exit codes.
- Fixed mock runner tautologies in differential testing networks.

### Security
- Inviolable integrity guarantee for `.ceh/` directory preventing forged certificates.
- Zero-tolerance pipeline red on repositories with active CI workflows.
