# Contributing to CLEARER Engineering Harness (CEH)

Thank you for your interest in contributing to the **CLEARER Engineering Harness**!

CEH is built on strict software engineering principles: **evidence-driven development**, minimal blast radius, deterministic test verification, and adversarial code reviews.

---

## 1. Principles for Contributions

When proposing changes, skills, or rules to CEH, ensure that:

1. **Concrete Evidence First**: Do not add heuristic checks without clear, verifiable outputs.
2. **Minimal Blast Radius**: Changes should be surgical, modular, and backwards-compatible with Antigravity 1.1+.
3. **Safety Gate Compliance**: Any new tool or script must respect the `DENY > ASK > ALLOW` safety hierarchy.
4. **All Tests Pass**: Never bypass tests or introduce unverified assumptions.

---

## 2. Development Workflow

1. **Fork and Clone**:
   ```bash
   git clone https://github.com/nandinhos/antigravity-clearer-engineering-harness.git
   cd antigravity-clearer-engineering-harness
   ```

2. **Validate the Plugin**:
   ```bash
   agy plugin validate ./clearer-engineering
   ```

3. **Run the Full Test Suite**:
   ```bash
   ./clearer-engineering/tests/run-all-tests.sh
   ```

4. **Run Adversarial Validation**:
   ```bash
   ./clearer-engineering/tests/run-adversarial-tests.sh
   ```

---

## 3. Submitting Pull Requests

- Keep PRs focused on a single responsibility.
- Include regression tests for bugfixes or validation tests for new skills.
- Ensure the commit message follows Conventional Commits format (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`).
