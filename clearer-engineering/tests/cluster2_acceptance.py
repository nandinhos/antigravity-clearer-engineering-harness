#!/usr/bin/env python3
"""Regressões determinísticas do Cluster 2 (R6–R8)."""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PLUGIN_ROOT = REPO_ROOT / "clearer-engineering"
RUN_ALL_TESTS = PLUGIN_ROOT / "tests" / "run-all-tests.sh"
TEST_RUNNER = PLUGIN_ROOT / "scripts" / "test-runner.sh"
SAFETY_GATE = PLUGIN_ROOT / "scripts" / "safety-gate.py"
EVALS_DIR = REPO_ROOT / "evals"


class Cluster2Acceptance(unittest.TestCase):
    def make_eval_fixture(self, root: Path) -> Path:
        repo = root / "fixture"
        (repo / "evals").mkdir(parents=True)
        (repo / "clearer-engineering" / "scripts").mkdir(parents=True)
        shutil.copy2(EVALS_DIR / "run.sh", repo / "evals" / "run.sh")
        shutil.copy2(EVALS_DIR / "CRITERIA.md", repo / "evals" / "CRITERIA.md")
        shutil.copytree(SAFETY_GATE.parent, repo / "clearer-engineering" / "scripts", dirs_exist_ok=True)
        subprocess.run(["git", "init", "-q", "-b", "dev"], cwd=repo, check=True)
        subprocess.run(["git", "config", "user.name", "CEH Cluster2 Test"], cwd=repo, check=True)
        subprocess.run(["git", "config", "user.email", "cluster2@example.invalid"], cwd=repo, check=True)
        subprocess.run(["git", "add", "."], cwd=repo, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "fixture limpa"], cwd=repo, check=True)
        return repo

    @staticmethod
    def run_evals(repo: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(repo / "evals" / "run.sh")],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )

    def test_r6_run_test_checks_exit_and_failure_text(self) -> None:
        source = RUN_ALL_TESTS.read_text(encoding="utf-8")
        function_start = source.index("run_test() {")
        function_end = source.index("\n}\n", function_start) + 3
        test_start = source.index(
            'run_test "Test Runner: Failing test correctly reports FAIL without masking"'
        )
        test_end = source.index("\n\n", test_start)
        run_test_function = source[function_start:function_end]
        r6_invocation = source[test_start:test_end]

        for mutant, expected_failed_tests in ((False, "0"), (True, "1")):
            with self.subTest(mutant=mutant), tempfile.TemporaryDirectory(prefix="ceh-r6-") as tmp:
                plugin = Path(tmp) / "plugin"
                scripts = plugin / "scripts"
                scripts.mkdir(parents=True)
                runner = scripts / "test-runner.sh"
                if mutant:
                    runner.write_text("#!/usr/bin/env bash\necho 'STATUS:    FAIL'\nexit 0\n", encoding="utf-8")
                    runner.chmod(0o755)
                else:
                    shutil.copy2(TEST_RUNNER, runner)

                shell = (
                    f"PLUGIN_DIR={shlex.quote(str(plugin))}\n"
                    "TOTAL_TESTS=0\nFAILED_TESTS=0\n"
                    "log_pass() { echo TEST_PASS; }\n"
                    "log_fail() { echo TEST_FAIL; FAILED_TESTS=$((FAILED_TESTS + 1)); }\n"
                    f"{run_test_function}\n{r6_invocation}\n"
                    "printf 'FAILED_TESTS=%s\\n' \"$FAILED_TESTS\"\n"
                )
                result = subprocess.run(["bash", "-c", shell], cwd=tmp, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(f"FAILED_TESTS={expected_failed_tests}", result.stdout)
                self.assertIn("TEST_PASS" if not mutant else "TEST_FAIL", result.stdout)

    def test_r7_syntax_or_noop_mutation_is_infrastructure_failure(self) -> None:
        fake_sed_cases = {
            "sintaxe": "#!/bin/sh\nprintf 'def broken(:\\n'\n",
            "sem_mudanca": "#!/bin/sh\ncat \"$2\"\n",
        }
        for case, fake_sed_body in fake_sed_cases.items():
            with self.subTest(case=case), tempfile.TemporaryDirectory(prefix="ceh-r7-") as tmp:
                repo = self.make_eval_fixture(Path(tmp))
                fake_bin = Path(tmp) / "bin"
                fake_bin.mkdir()
                fake_sed = fake_bin / "sed"
                fake_sed.write_text(fake_sed_body, encoding="utf-8")
                fake_sed.chmod(0o755)
                env = os.environ.copy()
                env["PATH"] = f"{fake_bin}{os.pathsep}{env.get('PATH', '')}"

                result = self.run_evals(repo, env)
                output = result.stdout + result.stderr
                self.assertNotEqual(result.returncode, 0, output)
                self.assertIn("INFRA-FAIL: Deriva B", output)
                self.assertNotIn("VEREDITO FINAL: APROVA", output)

    def test_r8_dirty_tracked_or_untracked_baseline_fails_before_eval(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ceh-r8-clean-") as tmp:
            repo = self.make_eval_fixture(Path(tmp))
            clean_result = self.run_evals(repo)
            clean_output = clean_result.stdout + clean_result.stderr
            self.assertEqual(clean_result.returncode, 0, clean_output)
            self.assertIn("Critérios Atendidos: 5 de 5", clean_output)

        for dirty_kind in ("tracked", "untracked"):
            with self.subTest(dirty_kind=dirty_kind), tempfile.TemporaryDirectory(prefix="ceh-r8-") as tmp:
                repo = self.make_eval_fixture(Path(tmp))
                if dirty_kind == "tracked":
                    (repo / "evals" / "CRITERIA.md").write_text(
                        (repo / "evals" / "CRITERIA.md").read_text(encoding="utf-8") + "\n",
                        encoding="utf-8",
                    )
                else:
                    (repo / "nao-commitado.txt").write_text("residuo de fixture\n", encoding="utf-8")

                before = subprocess.check_output(["git", "status", "--porcelain"], cwd=repo, text=True)
                result = self.run_evals(repo)
                after = subprocess.check_output(["git", "status", "--porcelain"], cwd=repo, text=True)
                output = result.stdout + result.stderr
                self.assertNotEqual(result.returncode, 0, output)
                self.assertIn("INFRA-FAIL: baseline Git não está limpa", output)
                self.assertNotIn("Avaliando Critério 1", output)
                self.assertEqual(before, after)


if __name__ == "__main__":
    if sys.argv[1:] == ["--clean-eval-smoke"]:
        with tempfile.TemporaryDirectory(prefix="ceh-clean-eval-") as tmp:
            repo = Cluster2Acceptance().make_eval_fixture(Path(tmp))
            result = Cluster2Acceptance.run_evals(repo)
            sys.stdout.write(result.stdout)
            sys.stderr.write(result.stderr)
            if result.returncode != 0 or "Critérios Atendidos: 5 de 5" not in result.stdout:
                raise SystemExit(result.returncode or 1)
        raise SystemExit(0)
    unittest.main(verbosity=2)
