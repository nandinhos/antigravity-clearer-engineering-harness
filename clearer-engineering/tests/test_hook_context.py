#!/usr/bin/env python3
"""
Unit tests for hook_context.py covering the 6 mandatory cases in Handoff 007 Section 4.
"""

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Any

# Add scripts directory to sys.path
import sys
SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import importlib.util
spec = importlib.util.spec_from_file_location("safety_gate", str(SCRIPTS_DIR / "safety-gate.py"))
safety_gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(safety_gate)

from hook_context import resolve_hook_target, evaluate_hook_payload


class TestHookContext(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="ceh-test-hook-ctx-"))
        self.orig_cwd = os.getcwd()

    def tearDown(self):
        os.chdir(self.orig_cwd)
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _init_repo(self, name: str, branch: str = "main", with_ci: bool = False) -> Path:
        repo = self.tmp_dir / name
        repo.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "init", "-q", "-b", branch, str(repo)], check=True)
        subprocess.run(["git", "-C", str(repo), "config", "user.name", "CEH Test"], check=True)
        subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@ceh.local"], check=True)
        (repo / "README.md").write_text("initial\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(repo), "add", "README.md"], check=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "init"], check=True)

        if with_ci:
            ci_dir = repo / ".github" / "workflows"
            ci_dir.mkdir(parents=True, exist_ok=True)
            (ci_dir / "ci.yml").write_text("name: CI\non: push\njobs:\n  test:\n    runs-on: ubuntu-latest\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", ".github"], check=True)
            subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "add ci"], check=True)

        return repo

    def test_case_1_absolute_cwd_on_main_blocks_reset(self):
        """Case 1: Hook running in plugin dir; absolute Cwd in repo on 'main'; git reset --hard -> deny."""
        repo = self._init_repo("repo_main", branch="main")
        fake_plugin_dir = self.tmp_dir / "fake_plugin"
        fake_plugin_dir.mkdir(parents=True, exist_ok=True)
        os.chdir(fake_plugin_dir)

        payload = {
            "toolCall": {
                "name": "run_command",
                "args": {
                    "CommandLine": "git reset --hard",
                    "Cwd": str(repo),
                },
            },
            "workspacePaths": [str(repo)],
        }
        res = evaluate_hook_payload(payload, safety_gate.evaluate_command)
        self.assertEqual(res["decision"], "deny")
        self.assertIn("CEH PRODUCTION LOCK", res["reason"])

    def test_case_2_absolute_cwd_on_ci_repo_blocks_push_without_cert(self):
        """Case 2: Absolute Cwd in repo with CI; git push without certificate -> deny."""
        repo = self._init_repo("repo_ci", branch="dev", with_ci=True)
        fake_plugin_dir = self.tmp_dir / "fake_plugin"
        fake_plugin_dir.mkdir(parents=True, exist_ok=True)
        os.chdir(fake_plugin_dir)

        payload = {
            "toolCall": {
                "name": "run_command",
                "args": {
                    "CommandLine": "git push origin dev",
                    "Cwd": str(repo),
                },
            },
            "workspacePaths": [str(repo)],
        }
        res = evaluate_hook_payload(payload, safety_gate.evaluate_command)
        self.assertEqual(res["decision"], "deny")
        self.assertIn("CEH PRE-PUSH CI GATE", res["reason"])

    def test_case_3_relative_cwd_with_workspace_on_dev_allows_reset(self):
        """Case 3: Cwd: '.' with workspacePaths[0] = repo on 'dev'; git reset --hard -> allow."""
        repo = self._init_repo("repo_dev", branch="dev")
        fake_plugin_dir = self.tmp_dir / "fake_plugin"
        fake_plugin_dir.mkdir(parents=True, exist_ok=True)
        os.chdir(fake_plugin_dir)

        payload = {
            "toolCall": {
                "name": "run_command",
                "args": {
                    "CommandLine": "git reset --hard",
                    "Cwd": ".",
                },
            },
            "workspacePaths": [str(repo)],
        }
        res = evaluate_hook_payload(payload, safety_gate.evaluate_command)
        self.assertEqual(res["decision"], "allow")
        self.assertIn("DEV PERMITTED", res["reason"])

    def test_case_4_relative_cwd_without_workspace_escalates_to_production(self):
        """Case 4: Cwd: '.' without workspacePaths: destructive -> deny; safe -> allow; git push -> deny."""
        fake_plugin_dir = self.tmp_dir / "fake_plugin"
        fake_plugin_dir.mkdir(parents=True, exist_ok=True)
        os.chdir(fake_plugin_dir)

        # Destructive command -> deny (escalated to production)
        payload_reset = {
            "toolCall": {
                "name": "run_command",
                "args": {
                    "CommandLine": "git reset --hard",
                    "Cwd": ".",
                },
            },
            "workspacePaths": [],
        }
        res_reset = evaluate_hook_payload(payload_reset, safety_gate.evaluate_command)
        self.assertEqual(res_reset["decision"], "deny")
        self.assertIn("CEH PRODUCTION LOCK", res_reset["reason"])

        # Safe command -> allow
        payload_status = {
            "toolCall": {
                "name": "run_command",
                "args": {
                    "CommandLine": "git status",
                    "Cwd": ".",
                },
            },
            "workspacePaths": [],
        }
        res_status = evaluate_hook_payload(payload_status, safety_gate.evaluate_command)
        self.assertEqual(res_status["decision"], "allow")

        # git push -> deny
        payload_push = {
            "toolCall": {
                "name": "run_command",
                "args": {
                    "CommandLine": "git push origin main",
                    "Cwd": ".",
                },
            },
            "workspacePaths": [],
        }
        res_push = evaluate_hook_payload(payload_push, safety_gate.evaluate_command)
        self.assertEqual(res_push["decision"], "deny")
        self.assertIn("PRE-PUSH CI GATE", res_push["reason"])

    def test_case_5_tilde_cwd_resolves_home_without_crash(self):
        """Case 5: Cwd: '~' resolves to home directory safely without crashing."""
        payload = {
            "toolCall": {
                "name": "run_command",
                "args": {
                    "CommandLine": "echo test",
                    "Cwd": "~",
                },
            },
            "workspacePaths": [],
        }
        target_path, explicit_env, force_deny_push = resolve_hook_target(payload)
        self.assertIsNotNone(target_path)
        self.assertEqual(target_path, Path.home().resolve())
        self.assertIsNone(explicit_env)
        self.assertFalse(force_deny_push)

        res = evaluate_hook_payload(payload, safety_gate.evaluate_command)
        self.assertEqual(res["decision"], "allow")

    def test_case_6_claude_payload_with_cwd(self):
        """Case 6: Claude payload with cwd: resolves, evaluates in cwd and returns Claude format."""
        repo = self._init_repo("repo_claude", branch="main")
        payload = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "cwd": str(repo),
            "tool_input": {
                "command": "git reset --hard",
            },
        }
        res = evaluate_hook_payload(payload, safety_gate.evaluate_command)
        self.assertIn("hookSpecificOutput", res)
        hook_out = res["hookSpecificOutput"]
        self.assertEqual(hook_out["hookEventName"], "PreToolUse")
        self.assertEqual(hook_out["permissionDecision"], "deny")
        self.assertIn("CEH PRODUCTION LOCK", hook_out["permissionDecisionReason"])

    def test_case_7_pr00c_agy_payload_converts_ask_to_deny_on_staging(self):
        """PR-00c: On staging, destructive command in agy payload converts 'ask' to 'deny'."""
        repo = self._init_repo("repo_staging_agy", branch="staging")
        payload = {
            "toolCall": {
                "name": "run_command",
                "args": {
                    "CommandLine": "git reset --hard",
                    "Cwd": str(repo),
                },
            },
            "workspacePaths": [str(repo)],
        }
        res = evaluate_hook_payload(payload, safety_gate.evaluate_command)
        self.assertEqual(res["decision"], "deny")
        self.assertIn("Decisão 'ask' convertida para 'deny'", res["reason"])

    def test_case_8_pr00c_claude_payload_preserves_ask_on_staging(self):
        """PR-00c: On staging, destructive command in Claude payload preserves 'ask' in Claude format."""
        repo = self._init_repo("repo_staging_claude", branch="staging")
        payload = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "cwd": str(repo),
            "tool_input": {
                "command": "git reset --hard",
            },
        }
        res = evaluate_hook_payload(payload, safety_gate.evaluate_command)
        self.assertIn("hookSpecificOutput", res)
        hook_out = res["hookSpecificOutput"]
        self.assertEqual(hook_out["hookEventName"], "PreToolUse")
        self.assertEqual(hook_out["permissionDecision"], "ask")
        self.assertIn("CEH HOMOLOGAÇÃO / STAGING SAFETY GATE", hook_out["permissionDecisionReason"])

    def _run_gate_hook(self, stdin_payload: str) -> tuple[int, dict[str, Any]]:
        proc = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "safety-gate.py")],
            input=stdin_payload,
            capture_output=True,
            text=True,
        )
        try:
            data = json.loads(proc.stdout)
        except Exception:
            data = {}
        return proc.returncode, data

    def test_case_9_pr00b_malformed_toolcall_fails_closed(self):
        """PR-00b: Malformed toolCall ('x') must exit 2 with deny."""
        code, res = self._run_gate_hook('{"toolCall": "x"}')
        self.assertEqual(code, 2)
        self.assertEqual(res.get("decision"), "deny")
        self.assertIn("[CEH SAFETY GATE ERROR]", res.get("reason", ""))

    def test_case_10_pr00b_list_payload_fails_closed(self):
        """PR-00b: Non-object JSON payload ([]) must exit 2 with deny."""
        code, res = self._run_gate_hook("[]")
        self.assertEqual(code, 2)
        self.assertEqual(res.get("decision"), "deny")
        self.assertIn("[CEH SAFETY GATE ERROR] Invalid hook payload: expected JSON object.", res.get("reason", ""))

    def test_case_11_pr00b_string_payload_fails_closed(self):
        """PR-00b: Non-object string JSON payload (\"texto\") must exit 2 with deny."""
        code, res = self._run_gate_hook('"texto"')
        self.assertEqual(code, 2)
        self.assertEqual(res.get("decision"), "deny")
        self.assertIn("[CEH SAFETY GATE ERROR] Invalid hook payload: expected JSON object.", res.get("reason", ""))

    def test_case_12_pr00b_invalid_json_text_fails_closed(self):
        """PR-00b: Invalid JSON text (raw text) must exit 2 with deny."""
        code, res = self._run_gate_hook("texto_invalido_sem_aspas")
        self.assertEqual(code, 2)
        self.assertEqual(res.get("decision"), "deny")
        self.assertIn("[CEH SAFETY GATE ERROR] Hook execution failed:", res.get("reason", ""))

    def test_case_13_pr00d_claude_stdin_returns_claude_format(self):
        """PR-00d: Claude payload via stdin returns hookSpecificOutput JSON format."""
        repo = self._init_repo("repo_claude_stdin", branch="main")
        payload = json.dumps({
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "cwd": str(repo),
            "tool_input": {
                "command": "git reset --hard",
            },
        })
        code, res = self._run_gate_hook(payload)
        self.assertEqual(code, 0)
        self.assertIn("hookSpecificOutput", res)
        self.assertEqual(res["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertIn("CEH PRODUCTION LOCK", res["hookSpecificOutput"]["permissionDecisionReason"])

    def test_case_14_pr00e_claude_allow_returns_empty_dict(self):
        """PR-00e: On Claude, allow decision must return {} to preserve native permission flow."""
        repo = self._init_repo("repo_claude_allow", branch="dev")
        payload = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "cwd": str(repo),
            "tool_input": {
                "command": "echo ok",
            },
        }
        res = evaluate_hook_payload(payload, safety_gate.evaluate_command)
        self.assertEqual(res, {})
        self.assertNotIn("permissionDecision", str(res))

    def test_case_15_pr00e_claude_stdin_allow_returns_empty_json(self):
        """PR-00e: On Claude, allow via stdin outputs empty JSON object {} with exit 0."""
        repo = self._init_repo("repo_claude_stdin_allow", branch="dev")
        payload = json.dumps({
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "cwd": str(repo),
            "tool_input": {
                "command": "touch file.txt",
            },
        })
        code, res = self._run_gate_hook(payload)
        self.assertEqual(code, 0)
        self.assertEqual(res, {})

    def test_case_16_pr00e_agy_allow_preserves_decision_allow(self):
        """PR-00e: On Antigravity (agy), allow decision preserves {'decision': 'allow'}."""
        repo = self._init_repo("repo_agy_allow", branch="dev")
        payload = {
            "toolCall": {
                "name": "run_command",
                "args": {
                    "CommandLine": "echo ok",
                    "Cwd": str(repo),
                },
            },
            "workspacePaths": [str(repo)],
        }
        res = evaluate_hook_payload(payload, safety_gate.evaluate_command)
        self.assertEqual(res.get("decision"), "allow")


if __name__ == "__main__":
    unittest.main()
