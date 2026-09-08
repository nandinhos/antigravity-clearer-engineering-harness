<div align="center">

# 🛡️ CLEARER Engineering Harness (CEH)
### Evidence-Driven Software Engineering Framework for Google Antigravity

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Antigravity](https://img.shields.io/badge/Antigravity-v1.1%2B-purple.svg)](https://github.com/nandinhos/antigravity-clearer-engineering-harness)
[![Tests](https://img.shields.io/badge/Tests-25%2F25%20(100%25)-brightgreen.svg)](./clearer-engineering/tests/)
[![Ponytail Mode](https://img.shields.io/badge/Ponytail%20Mode-Senior%20Minimalist-blueviolet.svg)](#-ponytail-mode--ast-first-philosophy)
[![Risk Dial](https://img.shields.io/badge/Risk%20Dial-LOW%20|%20MEDIUM%20|%20HIGH-orange.svg)](#-the-risk-dial--execution-autonomy)

[**Português (Brasil)**](./README_PT.md) | **English**

</div>

---

## 📖 Overview

The **CLEARER Engineering Harness (CEH)** is a production-grade software engineering harness natively engineered for **Google Antigravity** (IDE and `agy` CLI).

Rather than relying on vague prompts or unverified model assumptions, CEH operates under the highest standards of **Staff Software Engineering**:
- **Environment Awareness & Granular Safety Gate**: Proactive safety policies tailored to `DEV` (freedom with local safety), `HOMOLOGACAO` (2-step explicit alerts), and `PRODUCAO` (destructive actions strictly denied).
- **Ponytail Mode & AST First Philosophy**: "Understand deeply, build concisely, deliver correctly". 5-step decision ladder, minimal functional diffs, and relational AST navigation with graceful fallback.
- **Flexible Canonical Topologies**: Native support for **Enterprise Mode (3 branches: `dev` ➔ `staging` ➔ `main`)** and **Classic Mode (2 branches: `dev` ➔ `main`)**, with interactive `ceh-branches` helper.
- **Continuous Execution for MEDIUM Risk**: The complete `INSPECT → PLAN → IMPLEMENT → TEST → REVIEW → AUDIT` cycle is conducted end-to-end in a **Single-Turn**.
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
| `ceh-help` | Interactive quick guide and command cheat sheet in terminal. | Fast reference manual. |

> **In Antigravity IDE**: Global rules, skills, hooks, and the **Engineering Cockpit** (`engineering_cockpit.md`) are active automatically across all workspaces.

---

## 🛡️ Environment Safety Tiers (Safety Gate)

| Environment | Definition & Evidence | Execution Policy | Destructive Commands |
|---|---|:---:|---|
| **`DEV` / `TEST`** | Branch `dev` or derivations (`dev/*`), `APP_ENV=local/testing`, local `.env`. | 🟢 **`ALLOW`** | **Permitted with safeguards**: Allowed for rapid bugfixes, requiring local backup readiness. Absolute block for OS destruction (`rm -rf /`). |
| **`HOMOLOGACAO`** | Branch `staging`/`homolog`, `APP_ENV=staging`, `.env.staging`. | 🟡 **`ASK (2 Alerts)`** | **Mandatory two-stage confirmation**: <br>1. *Alert 1/2 [Impact]*: Shared environment blast radius.<br>2. *Alert 2/2 [Backup & Rollback]*: Verified backup readiness. |
| **`PRODUCAO`** | Branch `main`/`master`, `APP_ENV=production`. | 🔴 **`DENY`** | **STRICTLY PROHIBITED**: Destructive database commands, force push, or bulk deletions are immediately rejected. |

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
| 🛠️ [**Skills & Commands Manual**](./docs/skills_and_commands.md) | How to use `/clearer`, `/clearer-feature`, `/clearer-bugfix`, `/clearer-refactor`, etc. |
| 🛡️ [**Safety Gate Guide**](./docs/safety_gate.md) | How `PreToolUse` hooks intercept destructive commands with `DENY > ASK > ALLOW`. |
| 💻 [**Installation & Troubleshooting**](./docs/installation.md) | Global installation, environment prerequisites, and uninstallation. |
| 💡 [**Practical Examples**](./docs/examples.md) | Real-world workflows across TypeScript, PHP/Laravel, and Python/FastAPI. |

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

## 🧪 Automated Testing & Verification

```bash
# 1. Run Component & Integration Suite (19 tests)
./clearer-engineering/tests/run-all-tests.sh

# 2. Run Adversarial Verification Suite (5 cases)
./clearer-engineering/tests/run-adversarial-tests.sh
```

---

## 📄 License

Distributed under the **Apache License 2.0**. See [`LICENSE`](./LICENSE) for details.

