#!/usr/bin/env python3
"""
test_cert_protection.py — Validação da proteção contra alteração/forja do certificado de CI (G9 / PR-10).
Cobre:
1. Comandos de terminal que tentam escrever em .ceh/ (echo, cp, tee, sed, python3 -c, rm, touch, mv, redirecionamentos).
2. Leituras puras permitidas (cat, head, tail, jq, grep, ls, stat, wc, python3 -m json.tool).
3. Comandos desembrulhados via interpretadores (bash -c, sh -c, eval).
4. Payloads de hook para ferramentas de escrita (agy: write_to_file, replace_file_content; claude: Write, Edit).
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import importlib.util
spec = importlib.util.spec_from_file_location("safety_gate", str(SCRIPTS_DIR / "safety-gate.py"))
safety_gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(safety_gate)

from hook_context import evaluate_hook_payload


class TestCertProtection(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="ceh-test-cert-"))
        self.orig_cwd = os.getcwd()
        os.chdir(self.tmp_dir)

    def tearDown(self):
        os.chdir(self.orig_cwd)
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _run_gate_stdin(self, payload_str: str) -> tuple[int, dict]:
        proc = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "safety-gate.py")],
            input=payload_str,
            capture_output=True,
            text=True,
        )
        try:
            data = json.loads(proc.stdout)
        except Exception:
            data = {}
        return proc.returncode, data

    def test_terminal_cert_write_commands_denied_all_envs(self):
        """As 5 escritas citadas no Handoff 037 mais variantes são deny em DEV, HML e PROD."""
        write_cmds = [
            "echo '{\"status\": \"PASS\"}' > .ceh/last-ci-run.json",
            "cp /tmp/fake.json .ceh/last-ci-run.json",
            "tee .ceh/last-ci-run.json < /tmp/fake.json",
            "sed -i s/FAIL/PASS/ .ceh/last-ci-run.json",
            "python3 -c \"open('.ceh/last-ci-run.json', 'w').write('fake')\"",
            "rm .ceh/last-ci-run.json",
            "touch .ceh/last-ci-run.json",
            "mv /tmp/x .ceh/last-ci-run.json",
            "cat /tmp/data > .ceh/last-ci-run.log",
            "echo x >> .ceh/last-evals-run.json",
        ]
        envs = ["development", "staging", "production"]
        for cmd in write_cmds:
            for env in envs:
                dec, reason, _, uc = safety_gate.evaluate_command(cmd, explicit_env=env)
                self.assertEqual(
                    dec, "deny",
                    f"Comando de escrita em certificado '{cmd}' deve ser DENY no ambiente '{env}'"
                )
                self.assertEqual(uc, "CERTIFICATE_INTEGRITY")
                self.assertIn("CERTIFICATE INTEGRITY", reason)

    def test_terminal_ceh_directory_manipulation_denied(self):
        """Manipulações no diretório .ceh/ inteiro (cp, mv, rsync, rm, etc.) são deny (AL1)."""
        dir_cmds = [
            "cp -r /tmp/fakeceh/. .ceh",
            "rm -rf .ceh && cp -r /tmp/fakeceh .ceh",
            "mv /tmp/fakeceh .ceh",
            "cp -r /tmp/fakeceh/* .ceh/",
            "rsync -a /tmp/fakeceh/ .ceh/",
            "rm -rf .ceh",
            "rm -rf ./.ceh",
            "rm -rf .ceh/",
            "mkdir -p .ceh",
            "ln -sf /tmp/fake .ceh",
        ]
        for cmd in dir_cmds:
            dec, reason, _, uc = safety_gate.evaluate_command(cmd, explicit_env="development")
            self.assertEqual(
                dec, "deny",
                f"Manipulação de diretório .ceh '{cmd}' deve ser DENY no ambiente development"
            )
            self.assertEqual(uc, "CERTIFICATE_INTEGRITY")
            self.assertIn("CERTIFICATE INTEGRITY", reason)

    def test_terminal_wrapped_cert_writes_denied(self):
        """Comandos embrulhados em bash -c, sh -c, eval que tentam forjar certificado são deny."""
        wrapped_cmds = [
            'bash -c "echo x > .ceh/last-ci-run.json"',
            'sh -c "cp /tmp/f.json .ceh/last-ci-run.json"',
            'bash -c "tee .ceh/last-ci-run.json"',
            'eval "cat foo > .ceh/last-ci-run.json"',
        ]
        for cmd in wrapped_cmds:
            dec, reason, _, _ = safety_gate.evaluate_command(cmd, explicit_env="development")
            self.assertEqual(
                dec, "deny",
                f"Comando embrulhado '{cmd}' deve ser DENY"
            )

    def test_terminal_pure_reads_allowed(self):
        """Leituras puras de arquivos de certificado são permitidas (allow)."""
        read_cmds = [
            "cat .ceh/last-ci-run.json",
            "head -n 5 .ceh/last-ci-run.json",
            "tail -n 20 .ceh/last-ci-run.log",
            "jq . .ceh/last-ci-run.json",
            "grep 'commit_hash' .ceh/last-ci-run.json",
            "ls -la .ceh/last-ci-run.json",
            "stat .ceh/last-ci-run.json",
            "wc -l .ceh/last-ci-run.log",
            "python3 -m json.tool .ceh/last-ci-run.json",
        ]
        for cmd in read_cmds:
            dec, reason, _, uc = safety_gate.evaluate_command(cmd, explicit_env="development")
            self.assertEqual(
                dec, "allow",
                f"Leitura pura '{cmd}' deve ser ALLOW, obteve '{dec}' ({reason})"
            )
            self.assertEqual(uc, "GENERAL")

    def test_hook_agy_write_to_ceh_denied_exit_2(self):
        """No agy, ferramentas de escrita para .ceh/ são bloqueadas com exit 2."""
        payload_write = json.dumps({
            "toolCall": {
                "name": "write_to_file",
                "args": {
                    "TargetFile": ".ceh/last-ci-run.json",
                    "CodeContent": '{"status": "PASS"}',
                },
            },
            "workspacePaths": [str(self.tmp_dir)],
        })
        code, res = self._run_gate_stdin(payload_write)
        self.assertEqual(code, 2)
        self.assertEqual(res.get("decision"), "deny")
        self.assertIn("CERTIFICATE INTEGRITY", res.get("reason", ""))

        payload_replace = json.dumps({
            "toolCall": {
                "name": "replace_file_content",
                "args": {
                    "TargetFile": str(self.tmp_dir / ".ceh" / "last-ci-run.json"),
                    "ReplacementContent": "fake",
                },
            },
            "workspacePaths": [str(self.tmp_dir)],
        })
        code, res = self._run_gate_stdin(payload_replace)
        self.assertEqual(code, 2)
        self.assertEqual(res.get("decision"), "deny")

    def test_hook_agy_write_normal_file_allowed_exit_0(self):
        """No agy, escrita em arquivo normal de projeto segue permitida com exit 0 e allow."""
        payload = json.dumps({
            "toolCall": {
                "name": "write_to_file",
                "args": {
                    "TargetFile": "app/Services/UserService.php",
                    "CodeContent": "<?php\n",
                },
            },
            "workspacePaths": [str(self.tmp_dir)],
        })
        code, res = self._run_gate_stdin(payload)
        self.assertEqual(code, 0)
        self.assertEqual(res.get("decision"), "allow")

    def test_hook_claude_write_to_ceh_denied_exit_2(self):
        """No Claude, ferramentas de escrita (Write, Edit) para .ceh/ retornam hookSpecificOutput deny com exit 2."""
        payload_write = json.dumps({
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "cwd": str(self.tmp_dir),
            "tool_input": {
                "file_path": ".ceh/last-ci-run.json",
                "content": '{"status": "PASS"}',
            },
        })
        code, res = self._run_gate_stdin(payload_write)
        self.assertEqual(code, 2)
        self.assertIn("hookSpecificOutput", res)
        hso = res["hookSpecificOutput"]
        self.assertEqual(hso.get("permissionDecision"), "deny")
        self.assertIn("CERTIFICATE INTEGRITY", hso.get("permissionDecisionReason", ""))

        payload_edit = json.dumps({
            "hook_event_name": "PreToolUse",
            "tool_name": "Edit",
            "cwd": str(self.tmp_dir),
            "tool_input": {
                "file_path": ".ceh/last-evals-run.json",
                "old_string": "FAIL",
                "new_string": "PASS",
            },
        })
        code, res = self._run_gate_stdin(payload_edit)
        self.assertEqual(code, 2)
        self.assertIn("hookSpecificOutput", res)
        self.assertEqual(res["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_hook_claude_write_normal_file_returns_empty_dict(self):
        """No Claude, escrita em arquivo normal retorna {} com exit 0 (preserva confirmação nativa / F6)."""
        payload = json.dumps({
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "cwd": str(self.tmp_dir),
            "tool_input": {
                "file_path": "app/Models/User.php",
                "content": "<?php\n",
            },
        })
        code, res = self._run_gate_stdin(payload)
        self.assertEqual(code, 0)
        self.assertEqual(res, {})


if __name__ == "__main__":
    unittest.main()
