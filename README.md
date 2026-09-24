<div align="center">

# 🛡️ CLEARER Engineering Harness (CEH)
### Evidence-Driven Software Engineering Framework for Google Antigravity

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Antigravity](https://img.shields.io/badge/Antigravity-v1.1%2B-purple.svg)](https://github.com/nandinhos/antigravity-clearer-engineering-harness)
[![Tests](https://img.shields.io/badge/Tests-45%2F45%20(100%25)-brightgreen.svg)](./clearer-engineering/tests/)
[![Smoke Evals](https://img.shields.io/badge/Smoke%20Evals-5%2F5%20(100%25)-blue.svg)](./evals/)
[![Ponytail Mode](https://img.shields.io/badge/Ponytail%20Mode-Senior%20Minimalist-blueviolet.svg)](#-ponytail-mode--ast-first-philosophy)
[![Risk Dial](https://img.shields.io/badge/Risk%20Dial-LOW%20|%20MEDIUM%20|%20HIGH-orange.svg)](#-the-risk-dial--execution-autonomy)

[**Português (Brasil)**](./README_PT.md) | **English**

</div>

---

## 📖 Overview

The **CLEARER Engineering Harness (CEH)** is a production-grade software engineering harness natively engineered for **Google Antigravity** (IDE and `agy` CLI).

Rather than relying on vague prompts or unverified model assumptions, CEH operates under the highest standards of **Staff Software Engineering**:
- **Mandatory CI Governance & Pre-Push Safety Gate (Zero-Tolerance Pipeline Red)**: Strict enforcement barring `git push` on repositories with active CI pipelines (`.github/workflows` or `.gitlab-ci.yml`) unless the full test suite passed with exit code 0 on the exact local commit hash via local Flight Certificate (`.ceh/last-ci-run.json`).
- **Runtime & CI Strategy Adapter (`NATIVE_HOST` vs `DOCKER_ACTIVE`/`SAIL`)**: Deterministic dispatch of canonical test suites identifying whether Docker containers are active or native host execution should run directly without disruption.
- **Environment Awareness & Granular Safety Gate**: Proactive safety policies tailored to `DEV` (freedom with local safety), `HOMOLOGACAO` (2-step explicit alerts), and `PRODUCAO` (destructive actions strictly denied).
- **System One Epistemology ("Like a Jev")**: Strict decoupling between content and evaluation, closed-space univariate atomic judgments, and evidence-grounded certainty.
- **Proactive Background Heartbeat (25s)**: 25-second telemetry heartbeat for long async commands and builds, real-time tracking via `ceh-monitor`, eliminating UI freeze perception.
- **Ponytail Mode & AST First Philosophy**: "Understand deeply, build concisely, deliver correctly". 5-step decision ladder, minimal functional diffs, and relational AST navigation with graceful fallback.
- **Flexible Canonical Topologies**: Native support for **Enterprise Mode (3 branches: `dev` ➔ `staging` ➔ `main`)** and **Classic Mode (2 branches: `dev` ➔ `main`)**, with interactive `ceh-branches` helper.
- **Continuous Execution for MEDIUM Risk**: The complete `INSPECT → PLAN → IMPLEMENT → TEST → REVIEW → AUDIT` cycle is conducted end-to-end in a **Single-Turn**.
- **Multi-Model Deliberation (Conselho de Seniores Add-on)**: Dynamic multi-agent review council dispatching headless checks to available frontier CLIs (`claude`, `codex`, `muse`, `hermes`, `agy`, `agent`) for 360º decision support.
- **Zero Hallucination & Zero Fake Pass**: Prohibits speculative code creation and guarantees every claim is backed by real execution logs in `OBSERVED`.

---

## ⚡ Global One-Line Installation

Install or update CEH across Linux, macOS, or WSL with a single command:

```bash
curl -fsSL https://raw.githubusercontent.com/nandinhos/antigravity-clearer-engineering-harness/main/install.sh | bash
```

---

## 🚀 Terminal & CLI Command Suite

Reload your shell with `source ~/.bashrc` (or `source ~/.zshrc`) to access the complete CLI toolkit:

| Command | What it does | Context / Example |
|---|---|---|
| `ceh` / `agy-ceh` | Starts Antigravity CLI under the `clearer-harness` profile. | Daily terminal workflow. |
| `agy-ceh-yolo` | Starts Antigravity with auto-approved safe edits. | Continuous agile dev mode. |
| `ceh-env` | Instant detection of active environment (`DEV`/`STAGING`/`PROD`), branch, and safety policy. | Pre-coding sanity check. |
| `ceh-branches` | Audits and sets up canonical project branches (Enterprise or Classic). | New repository setup. |
| `ceh-preflight` | Runs the full engineering readiness and project integrity check. | Pre-release validation. |
| `ceh-evals` | Runs deterministic smoke-eval suite (5/5 RFC 2119 criteria). | Harness falsifiability tests. |
| `ceh-doc-audit` | Audits documentation structure, allowed states, and link portability. | Pre-release documentation hygiene. |
| `ceh-conselho` | Invokes the dynamic multi-model Council of Seniors (optional add-on). | 360º multi-agent deliberation. |
| `ceh-monitor` | Real-time interactive telemetry dashboard & 25s heartbeat. | Background task tracker. |
| `ceh-help` | Interactive quick guide and command cheat sheet in terminal. | Fast reference manual. |

> **In Antigravity IDE**: Global rules, skills, hooks, and the **Engineering Cockpit** (`engineering_cockpit.md`) are active automatically across all workspaces.

---

## 🛡️ Environment Safety Tiers (Safety Gate)

| Environment | Definition & Evidence | Execution Policy | Destructive Commands & Git Push |
|---|---|:---:|---|
| **`DEV` / `TEST`** | Branch `dev` or derivations (`dev/*`), `APP_ENV=local/testing`, local `.env`. | 🟢 **`ALLOW`** | **Permitted with safeguards**: Allowed for rapid bugfixes, requiring local backup readiness. Absolute block for OS destruction (`rm -rf /`). On CI projects, `git push` requires valid Flight Certificate. |
| **`HOMOLOGACAO`** | Branch `staging`/`homolog`, `APP_ENV=staging`, `.env.staging`. | 🟡 **`ASK (2 Alerts)`** | **Mandatory two-stage confirmation**: <br>1. *Alert 1/2 [Impact]*: Shared environment blast radius.<br>2. *Alert 2/2 [Backup & Rollback]*: Verified backup readiness. `git push` requires Flight Certificate. |
| **`PRODUCAO`** | Branch `main`/`master`, `APP_ENV=production`. | 🔴 **`DENY`** | **STRICTLY PROHIBITED**: Destructive database commands, force push, or bulk deletions are immediately rejected. `git push` requires Flight Certificate. |

---

## 🥋 Ponytail Mode & Token Economy Triad

1. **Ponytail Decision Ladder**: Before proposing code or adding dependencies, ask:
   - *Does this strictly need to exist?* (YAGNI).
   - *Does it already exist in the codebase?* (Reuse existing traits, helpers, and components).
   - *Does the standard library (stdlib) solve it?* (Zero external packages for trivial tasks).
   - *Does a native platform API exist?* (Priorize framework and runtime native features).
   - *Does a surgical intervention suffice?* (Write the smallest functional diff possible).
2. **AST First with Graceful Fallback (Graphify)**:
   - If the project has Graphify (`graphify-out/graph.json` or MCP), the agent prioritizes zero-cost relational AST queries.
   - If Graphify is not present, the agent gracefully falls back to native surgical search (`grep_search` and sliced `view_file`), strictly prohibiting full file context dumps.
3. **Shell Output Compression with Graceful Fallback (RTK - Rust Token Killer)**:
   - Native integration with [**RTK**](https://github.com/rtk-ai/rtk): high-performance Rust proxy CLI that compresses bash output (`git`, `npm test`, `pytest`, `cargo test`, `docker`, `ruff`) by 60-90% before the agent reads it.
   - **Runner Automation**: `test-runner.sh` automatically wraps detected test suites with `rtk` when present in `$PATH`.
   - **Evasion-Immune Safety Gate**: `safety-gate.py` strips `rtk` prefixes before evaluating rules to enforce strict protection across production and staging.
   - **Escape Hatch**: Full raw logs remain accessible via `rtk proxy <cmd>` or `-vvv`. If RTK is not installed, the harness gracefully executes standard commands without friction.
4. **Context Hygiene & Sandbox (context-mode)**:
   - Keeps heavy tool output and history out of the direct LLM context window via SQLite+FTS5, promoting a "think in code" approach.

> [!TIP]
> **Complete Context Acceleration**: CEH operates seamlessly alongside the token optimization triad:
> - 🌐 **AST Navigation**: [**Graphify**](https://github.com/nandinhos/antigravity-harness-enhancements) (Tree-Sitter, zero LLM tokens).
> - ⚡ **Terminal Compression**: [**RTK**](https://github.com/rtk-ai/rtk) (Rust Token Killer, static proxy <10ms).
> - 🛡️ **Session Hygiene**: [**context-mode**](https://github.com/mksglu/context-mode) (MCP Sandbox).

---

## 📚 Complete Technical Documentation (`docs/`)

Deep dive into CEH principles, architectures, and guidelines:

| Document | Description |
|---|---|
| 📜 [**CLEARER Protocol Guide**](./docs/clearer_protocol.md) | Complete explanation of the 7-step engineering cycle (*Concrete Goal*, *Load Context*, etc.). |
| 💎 [**Coding Standards & Craftsmanship**](./docs/coding_standards.md) | Staff engineering standards: Clean Code, SOLID, strict typing, resilience, and tests. |
| 🎚️ [**Risk Dial Specification**](./docs/risk_dial.md) | **Continuous Execution** dynamics for MEDIUM and the 4 exception checkpoint gates. |
| ⚖️ [**Evidence Semantics & Claims**](./docs/evidence_semantics.md) | Epistemic classification (`OBSERVED`, `INFERRED`, `UNKNOWN`) and claim auditing (`SUPPORTED`). |
| 🏗️ [**System Architecture**](./docs/architecture.md) | Unified pipelines, topologies, data contracts, and Antigravity hook integration. |
| 🤖 [**Specialized Agents Guide**](./docs/agents_guide.md) | Role descriptions and I/O contracts for Investigator, Architect, Implementer, Test Engineer, Reviewer, and Auditor. |
| 🛠️ [**Skills & Commands Manual**](./docs/skills_and_commands.md) | How to use `/clearer`, `/clearer-feature`, `/clearer-bugfix`, `/clearer-adhd`, etc. |
| 🛡️ [**Safety Gate Guide**](./docs/safety_gate.md) | Hook `PreToolUse` architecture, destructive command tiers, and Pre-Push CI Gate. |
| 🏛️ [**ADR 003: System One Epistemology**](./docs/architecture/system-one-epistemology.md) | Abstraction of TypeSafe 7 epistemological invariants & "Like a Jev" operation. |
| 🛑 [**ADR 004: Mandatory CI Governance**](./docs/architecture/ci-governance-policy.md) | Zero-Tolerance Pipeline Red policy, Flight Certificate, and Pre-Push Gate. |
| 🐳 [**ADR 005: Runtime & CI Strategy Decoupling**](./docs/architecture/runtime-and-ci-adapters.md) | Detection of Native Host vs. Docker/Sail and dynamic CI test adaptation. |
| 💻 [**Installation & Configuration**](./docs/installation.md) | Complete global setup guide, dependencies, and clean uninstallation. |
| 💡 [**Practical Examples**](./docs/examples.md) | Real-world blueprints across TypeScript/Next.js, PHP/Laravel, and Python/FastAPI. |

---

## 🛑 Mandatory CI Governance & Pre-Push Safety Gate

> [!CRITICAL]
> **Zero-Tolerance Pipeline Red**: On any repository with an active CI pipeline (`.github/workflows/` or `.gitlab-ci.yml`), **pushing code to `dev`, `staging`, or `main` without a 100% green canonical test suite is strictly prohibited**. Partial checks (linters or isolated test subsets) NEVER authorize a push.

### The 3-Layer Protection Mechanism:
1. **Local Flight Certificate (`.ceh/last-ci-run.json`)**:
   Running the test suite via `bash scripts/test-runner.sh` automatically signs and persists a structured proof anchored to `git rev-parse HEAD`:
   ```json
   {
     "commit_hash": "951b015f931e15d299ea2c61b2c6c77ce824511b",
     "timestamp": "2026-09-20T03:59:37Z",
     "command": "rtk bash clearer-engineering/tests/run-all-tests.sh",
     "status": "PASS",
     "exit_code": 0
   }
   ```
2. **Pre-Push Gate Interception (`safety-gate.py`)**:
   Every `git push` on a CI project is intercepted before execution:
   - **`DENY`**: If no flight certificate exists.
   - **`DENY`**: If the last test status was `FAIL` or exit code $\neq 0$.
   - **`DENY`**: If current HEAD diverged from the tested commit hash (code mutated after tests).
   - **`ALLOW`**: Only when commit hash matches verified green certificate.
3. **Prevention of "Freezing Tests" during Review**:
   The `clearer-review` skill actively flags new entries in enums, seeders, or lookup catalogs, preventing blind count assertions (`assertCount(5)`) from breaking CI pipelines on valid additions.

---

## 🏛️ System One Epistemology ("Like a Jev")

CEH formally abstracts TypeSafe's **System One** engineering layer:
- **Content ≠ Judgment**: Code, diffs, and logs are passive data. Hostile injection comments (`// bypass check`) cannot dictate evaluative verdicts.
- **Closed Space & Atomicity**: Every evaluation yields a finite set (`enum` or boolean). One check = one univariate property.
- **Two Axes (Decision & Certainty)**: Verdicts without measurement of certainty grounded in physical evidence (`OBSERVED`) are rejected.
- **Code Retains Control**: Aggregations, weights, and thresholds live strictly in deterministic shell/code; no LLM authors final safety verdicts.

---

## 💓 Proactive Background Heartbeat (25s)

For asynchronous commands, heavy builds, and background test suites:
- **Ground Zero ($T=0\text{s}$)**: Instant notification with Task ID/PID and creation of `task_monitor.md`.
- **25s Cadence**: Active telemetry updates in chat and artifact every 25 seconds, eliminating perceived freezing and cognitive friction.
- **CLI Monitor**: Interactive real-time tracking via `ceh-monitor`.
- **Reactive Wakeup**: Millisecond resumption and Response Contract presentation upon task completion.

---

## 🧠 The 7-Step CLEARER Protocol

| Step | Principle | Description |
|---|---|---|
| **C** | **Concrete Goal** | Define precise requirements, acceptance criteria, boundaries, and stop conditions. |
| **L** | **Load Context** | *Inspect before edit*. Detect stack, locate entrypoints, tests, and dependencies. Never guess. |
| **E** | **Explicit Boundaries** | Confine blast radius. State what is in-scope, out-of-scope, and invariant contracts. |
| **A** | **Anchors & Examples** | Ground every decision in real code, schemas, migrations, and existing patterns. |
| **R** | **Response Contract** | Emit structured, auditable outputs (Changes, Evidence, Tests, Review, Confidence). |
| **E** | **Enable Evidence & Tools** | Direct observation over speculation. Capture raw command outputs and exit codes. |
| **R** | **Review & Validate** | Run the complete verification loop: `INSPECT → PLAN → IMPLEMENT → TEST → REVIEW → AUDIT`. |

---

## 🎚️ The Risk Dial & Execution Autonomy

| Level | Suitable Tasks | Operational Dynamic |
|---|---|---|
| **`LOW`** | Read-only queries, formatting, simple symbol renames, local documentation. | Fast execution, lean context, zero unnecessary overhead. |
| **`MEDIUM`** | Features, bug fixes, refactorings, API endpoints, business logic. | **Single-Turn Continuous Execution**: Inspect → Plan → High-Standard Implement → Tests with Auto-Heal → Diff Audit → Response Contract. |
| **`HIGH`** | Core auth, permissions, payments, concurrency, destructive migrations, production scripts. | Deep Investigation → Specialized Subagents → Adversarial Review → Formal Audit → Human Checkpoint. |

---

## 🛡️ Exception Checkpoints (Fail-Closed on Real Hazards)

The continuous agent stream is only halted upon encountering **4 strict exception conditions**:
1. **Real Business Ambiguity**: Mutually exclusive architectural/business decisions lacking specification.
2. **Destructive Risk (Environment-Aware Safety Gate)**:
   - In `PRODUCTION`: Destructive commands strictly forbidden (`DENY` - completely off limits).
   - In `HOMOLOGAÇÃO / STAGING`: Mandatory human confirmation (`ASK`) with **2 Explicit Alerts** (HML blast radius and Backup & Rollback readiness).
   - In `DEV / TEST`: Destructive commands permitted for rapid corrective iteration (`ALLOW` with local safeguard notice), preserving `DENY` for catastrophic OS commands (`rm -rf /`, fork bombs).
3. **Persistent Test Failure**: Test suite failing after 1 evidence-grounded auto-heal iteration.
4. **Explicit HIGH Level**: Tasks formally classified as high risk.

## 🌿 Branching Strategies & Development Modes

CEH natively supports **2 Git topology modes**, proactively identified upon loading the project:

1. **Enterprise Mode (3 Branches: `dev` ➔ `staging` ➔ `main`)**:
   - `dev`: Core development, free movement and tests (`ALLOW` with safeguards).
   - `staging`: Homologation with real data and verification (`ASK` with 2 alerts and mandatory backup).
   - `main`: Protected production for stable deploy (`DENY` - off limits).
   - *Ideal for teams, CI/CD pipelines, and corporate environments.*

2. **Classic Mode (2 Branches: `dev` ➔ `main`)**:
   - `dev`: Where all features, spikes and bugfixes occur (`ALLOW`).
   - `main`: Protected production for direct releases (`DENY`).
   - *Ideal for agile projects, MVPs, and solo developers.*

> **Automated Assistant**: Run `bash clearer-engineering/scripts/setup-branches.sh --classic` (or `--enterprise`) to configure your repository topology in 1 command.

---

## 🧪 Automated Testing & Falsifiability Meta-Eval

CEH provides rigorous end-to-end verification, including infrastructure mutation testing:

```bash
# 1. Run Complete Component & Integrity Suite (45 tests)
./clearer-engineering/tests/run-all-tests.sh

# 2. Run Adversarial Verification Suite (bypass & injection detection)
./clearer-engineering/tests/run-adversarial-tests.sh

# 3. Run Falsifiability Smoke-Eval (Baseline 3x, Drifts A/B & Fail-Closed)
./evals/run.sh
```

See [`evals/CRITERIA.md`](./evals/CRITERIA.md) for the formal 5-criteria matrix (RFC 2119).

---

## 🏛️ Architecture Decision Records (ADRs)

- [ADR 003 — System One Epistemology ("Like a Jev")](./docs/architecture/system-one-epistemology.md)
- [ADR 004 — Mandatory CI Governance & Pre-Push Safety Gate](./docs/architecture/ci-governance-policy.md)
- [ADR 005 — Runtime Adapter & CI Testing Strategy](./docs/architecture/runtime-and-ci-adapters.md)

---

## 📄 License

Distributed under the **Apache License 2.0**. See [`LICENSE`](./LICENSE) for details.

