#!/usr/bin/env python3
from __future__ import annotations
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
from typing import Any, Optional

# Add scripts directory to sys.path
import sys
SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import importlib.util
spec = importlib.util.spec_from_file_location("safety_gate", str(SCRIPTS_DIR / "safety-gate.py"))
safety_gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(safety_gate)

from hook_context import resolve_hook_target, evaluate_hook_payload

_TOOLS_DIR = Path(__file__).resolve().parent / "tools"
sys.path.insert(0, str(_TOOLS_DIR))
from test_helpers import mkdtemp_resolved


class TestHookContext(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = mkdtemp_resolved(prefix="ceh-test-hook-ctx-")
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

    def _run_gate_hook(self, stdin_payload: str, env_extra: Optional[dict[str, str]] = None) -> tuple[int, dict[str, Any]]:
        env = os.environ.copy()
        for k in ("CLAUDECODE", "CLAUDE_PROJECT_DIR", "CLAUDE_PID"):
            env.pop(k, None)
        if env_extra:
            env.update(env_extra)
        proc = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "safety-gate.py")],
            input=stdin_payload,
            capture_output=True,
            text=True,
            env=env,
        )
        try:
            data = json.loads(proc.stdout)
        except Exception:
            data = {}
        return proc.returncode, data

    def test_case_9_pr00b_malformed_toolcall_fails_closed(self):
        """PR-00b: Malformed toolCall ('x') must exit 0 with deny on Antigravity host."""
        code, res = self._run_gate_hook('{"toolCall": "x"}')
        self.assertEqual(code, 0, "Antigravity host must exit 0 to block in IDE")
        self.assertEqual(res.get("decision"), "deny")
        self.assertIn("[CEH SAFETY GATE ERROR]", res.get("reason", ""))

    def test_case_10_pr00b_list_payload_fails_closed(self):
        """PR-00b: Non-object JSON payload ([]) must exit 0 with deny on default/Antigravity host."""
        code, res = self._run_gate_hook("[]")
        self.assertEqual(code, 0, "Default host must exit 0 to prevent fail-open in IDE")
        self.assertEqual(res.get("decision"), "deny")
        self.assertIn("[CEH SAFETY GATE ERROR] Invalid hook payload: expected JSON object.", res.get("reason", ""))

    def test_case_11_pr00b_string_payload_fails_closed(self):
        """PR-00b: Non-object string JSON payload (\"texto\") must exit 0 with deny on default/Antigravity host."""
        code, res = self._run_gate_hook('"texto"')
        self.assertEqual(code, 0, "Default host must exit 0 to prevent fail-open in IDE")
        self.assertEqual(res.get("decision"), "deny")
        self.assertIn("[CEH SAFETY GATE ERROR] Invalid hook payload: expected JSON object.", res.get("reason", ""))

    def test_case_12_pr00b_invalid_json_text_fails_closed(self):
        """PR-00b: Invalid JSON text (raw text) must exit 0 with deny on default/Antigravity host."""
        code, res = self._run_gate_hook("texto_invalido_sem_aspas")
        self.assertEqual(code, 0, "Default host must exit 0 to prevent fail-open in IDE")
        self.assertEqual(res.get("decision"), "deny")
        self.assertIn("[CEH SAFETY GATE ERROR] Hook execution failed:", res.get("reason", ""))

    def test_case_13_pr00d_claude_stdin_returns_claude_format(self):
        """PR-00d / PR-09: Claude payload via stdin returns hookSpecificOutput JSON format with exit 2 on deny."""
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
        self.assertEqual(code, 2)
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

    def test_case_17_pr09_seven_table_rows_fail_closed_exit_2(self):
        """
        PR-09: Verifies all 7 rows from Handoff 036 table fail-closed with exit code 2 and explicit deny reason.
        Row 1: "" (vazio)
        Row 2: "{}"
        Row 3: '{"toolCall":{}}'
        Row 4: '{"toolCall":{"name":"run_command","args":{}}}'
        Row 5: '{"tool_name":"Bash","tool_input":{}}'
        Row 1: "" (vazio) -> deny (exit 0 default / Antigravity; exit 2 no Claude)
        Row 2: "{}" -> deny (exit 0 default / Antigravity; exit 2 no Claude)
        Row 3: '{"toolCall":{}}' -> deny, exit 0
        Row 4: '{"toolCall":{"name":"run_command","args":{}}}' -> deny, exit 0
        Row 5: '{"tool_name":"Bash","tool_input":{}}' -> deny (Claude format), exit 2
        Row 6: '{"tool_name":"Bash","tool_input":{"command":""}}' -> deny (Claude format), exit 2
        Row 7: "nao-json" -> deny (exit 0 default / Antigravity; exit 2 no Claude)
        """
        # Row 1: "" (vazio) -> deny, exit 0 no Antigravity/default (evita fail-open na IDE)
        code, res = self._run_gate_hook("")
        self.assertEqual(code, 0, "Row 1 ('') must exit 0 in default/Antigravity host")
        self.assertEqual(res.get("decision"), "deny")
        self.assertIn("Payload vazio", res.get("reason", ""))

        # Row 2: "{}" -> deny, exit 0 no Antigravity/default
        code, res = self._run_gate_hook("{}")
        self.assertEqual(code, 0, "Row 2 ('{}') must exit 0 in default/Antigravity host")
        self.assertEqual(res.get("decision"), "deny")
        self.assertIn("Nenhuma ferramenta identificável", res.get("reason", ""))

        # Row 3: '{"toolCall":{}}' -> deny, exit 0 (Antigravity host)
        code, res = self._run_gate_hook('{"toolCall":{}}')
        self.assertEqual(code, 0, "Row 3 ('{\"toolCall\":{}}') must exit 0")
        self.assertEqual(res.get("decision"), "deny")
        self.assertIn("Nenhuma ferramenta identificável", res.get("reason", ""))

        # Row 4: '{"toolCall":{"name":"run_command","args":{}}}' -> deny, exit 0 (Antigravity host)
        code, res = self._run_gate_hook('{"toolCall":{"name":"run_command","args":{}}}')
        self.assertEqual(code, 0, "Row 4 must exit 0")
        self.assertEqual(res.get("decision"), "deny")
        self.assertIn("Comando vazio ou ausente", res.get("reason", ""))

        # Row 5: '{"tool_name":"Bash","tool_input":{}}' -> deny (Claude format), exit 2
        code, res = self._run_gate_hook('{"tool_name":"Bash","tool_input":{}}')
        self.assertEqual(code, 2, "Row 5 must exit 2")
        self.assertIn("hookSpecificOutput", res)
        hso = res["hookSpecificOutput"]
        self.assertEqual(hso.get("permissionDecision"), "deny")
        self.assertIn("Comando vazio ou ausente", hso.get("permissionDecisionReason", ""))

        # Row 6: '{"tool_name":"Bash","tool_input":{"command":""}}' -> deny (Claude format), exit 2
        code, res = self._run_gate_hook('{"tool_name":"Bash","tool_input":{"command":""}}')
        self.assertEqual(code, 2, "Row 6 must exit 2")
        self.assertIn("hookSpecificOutput", res)
        hso = res["hookSpecificOutput"]
        self.assertEqual(hso.get("permissionDecision"), "deny")
        self.assertIn("Comando vazio ou ausente", hso.get("permissionDecisionReason", ""))

        # Row 7: "nao-json" -> deny, exit 0 no Antigravity/default
        code, res = self._run_gate_hook("nao-json")
        self.assertEqual(code, 0, "Row 7 ('nao-json') must exit 0 in default/Antigravity host")
        self.assertEqual(res.get("decision"), "deny")
        self.assertIn("Hook execution failed", res.get("reason", ""))

    def test_case_18_pr09_unknown_tools_fail_closed_exit_codes(self):
        """PR-09: Unrecognized tool names fail-closed with host-specific exit code (0 for agy, 2 for claude)."""
        # Agy format -> exit 0 com JSON de deny (bloqueia na IDE e no CLI)
        code, res = self._run_gate_hook('{"toolCall":{"name":"ferramenta_desconhecida","args":{"CommandLine":"ls"}}}')
        self.assertEqual(code, 0)
        self.assertEqual(res.get("decision"), "deny")
        self.assertIn("Ferramenta desconhecida 'ferramenta_desconhecida'", res.get("reason", ""))

        # Claude format -> exit 2 com hookSpecificOutput
        code, res = self._run_gate_hook('{"hook_event_name":"PreToolUse","tool_name":"UnknownClaudeTool","tool_input":{"command":"ls"}}')
        self.assertEqual(code, 2)
        self.assertIn("hookSpecificOutput", res)
        hso = res["hookSpecificOutput"]
        self.assertEqual(hso.get("permissionDecision"), "deny")
        self.assertIn("Ferramenta desconhecida 'UnknownClaudeTool'", hso.get("permissionDecisionReason", ""))

    def test_case_19_claude_environment_detection_for_unidentifiable_payload(self):
        """Para payload não identificável sob ambiente Claude Code, sai com exit 2."""
        env_claude = {"CLAUDECODE": "1"}
        code, res = self._run_gate_hook("nao-json", env_extra=env_claude)
        self.assertEqual(code, 2, "Payload inválido com CLAUDECODE no env deve sair com exit 2")
        self.assertEqual(res.get("decision"), "deny")

    def test_case_20_agy_deny_exit_0(self):
        """No agy, negação sai estritamente com exit 0 para bloquear comandos na IDE."""
        code, res = self._run_gate_hook('{"toolCall":{"name":"run_command","args":{"CommandLine":"rm -rf /"}}}')
        self.assertEqual(code, 0, "Agy deny deve sair com exit 0 para bloquear na IDE")
        self.assertEqual(res.get("decision"), "deny")

    def test_case_21_agy_payload_with_claudecode_env_still_exits_0(self):
        """B1: Payload do Antigravity (com toolCall) deve sair com exit 0 mesmo com CLAUDECODE=1 no ambiente."""
        payload = json.dumps({"toolCall": {"name": "run_command", "args": {"CommandLine": "rm -rf /"}}})
        code, res = self._run_gate_hook(payload, env_extra={"CLAUDECODE": "1", "CLAUDE_PROJECT_DIR": "/tmp"})
        self.assertEqual(code, 0, "Payload com toolCall deve sair com exit 0 independente de variáveis CLAUDE* no ambiente")
        self.assertEqual(res.get("decision"), "deny")

    def test_case_22_claude_ask_decision_exits_0(self):
        """B2: No Claude Code, decisão de 'ask' deve sair com exit 0 para permitir leitura do hookSpecificOutput."""
        repo = self._init_repo("repo_staging_claude_e2e", branch="staging")
        payload = json.dumps({
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "cwd": str(repo),
            "tool_input": {"command": "git reset --hard HEAD~1"}
        })
        code, res = self._run_gate_hook(payload)
        self.assertEqual(code, 0, "No Claude Code, 'ask' deve sair com exit 0")
        self.assertIn("hookSpecificOutput", res)
        hso = res.get("hookSpecificOutput", {})
        self.assertEqual(hso.get("permissionDecision"), "ask")

    def test_case_23_ask_decision_exit_0(self):
        """B2 Asserção do ask no Claude Code: confirma que o ask sai com exit 0 para permitir leitura do hookSpecificOutput."""
        repo = self._init_repo("repo_staging_claude_mut", branch="staging")
        payload = json.dumps({
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "cwd": str(repo),
            "tool_input": {"command": "git reset --hard HEAD~1"}
        })
        code, res = self._run_gate_hook(payload)
        self.assertNotEqual(code, 1, "Exit 1 no Claude ignora o JSON de ask e reabre fail-open")
        self.assertEqual(code, 0, "Contrato estrito exige exit 0")


if __name__ == "__main__":
    unittest.main()


