#!/usr/bin/env python3
"""
test_hook_failclosed.py — Validação de Fail-Closed estrito em falhas de importação no shim (PR-13 / D1).

Comprova formalmente que falhas de import no hook_context ou no ceh_core não quebram o contrato
de fail-closed do Safety Gate:
- Para payloads do Antigravity: retorna JSON com 'deny' e exit code 0 (evitando fail-open na IDE).
- Para ambiente Claude (CLAUDECODE=1): retorna JSON com 'deny' e exit code 2.
- A validação ocorre hermeticamente em diretório temporário sem tocar no working tree real.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "clearer-engineering" / "scripts"


class TestHookFailClosed(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="ceh_failclosed_test_")
        self.tmp_path = Path(self.tmp_dir)

        # Copia scripts do CEH para o ambiente temporário isolado
        shutil.copy(SCRIPTS_DIR / "safety-gate.py", self.tmp_path / "safety-gate.py")
        shutil.copy(SCRIPTS_DIR / "hook_context.py", self.tmp_path / "hook_context.py")
        shutil.copytree(SCRIPTS_DIR / "ceh_core", self.tmp_path / "ceh_core")

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _run_gate_with_stdin(self, stdin_text: str, env_overrides: dict[str, str] | None = None) -> tuple[int, str, str]:
        env = os.environ.copy()
        env.pop("CEH_EXPLICIT_ENV", None)
        env.pop("APP_ENV", None)
        if env_overrides:
            env.update(env_overrides)

        cmd = [sys.executable, str(self.tmp_path / "safety-gate.py")]
        res = subprocess.run(
            cmd,
            input=stdin_text,
            capture_output=True,
            text=True,
            cwd=str(self.tmp_path),
            env=env,
        )
        return res.returncode, res.stdout, res.stderr

    def test_syntax_error_in_hook_context_yields_deny_exit_0(self):
        """Erro de sintaxe em hook_context.py deve retornar deny com exit 0 (Antigravity fail-closed)."""
        hook_ctx = self.tmp_path / "hook_context.py"
        hook_ctx.write_text("def syntax_error_breaking_import(: parse error\n", encoding="utf-8")

        payload = {
            "toolCall": {
                "name": "run_command",
                "args": {"CommandLine": "rm -rf /"}
            }
        }
        ec, stdout, stderr = self._run_gate_with_stdin(json.dumps(payload))

        self.assertEqual(ec, 0, f"Esperado exit 0 para Antigravity em erro de import, obteve {ec}. Stderr: {stderr}")
        self.assertTrue(stdout.strip(), "Esperava JSON de saída, obteve stdout vazio")
        data = json.loads(stdout)
        self.assertEqual(data.get("decision"), "deny")
        self.assertIn("Falha crítica de importação", data.get("reason", ""))

    def test_import_error_in_ceh_core_yields_deny_exit_0(self):
        """Falha de importação em ceh_core/engine.py deve retornar deny com exit 0."""
        engine_py = self.tmp_path / "ceh_core" / "engine.py"
        engine_py.write_text("raise ImportError('Simulated core engine import failure')\n", encoding="utf-8")

        payload = {
            "toolCall": {
                "name": "run_command",
                "args": {"CommandLine": "rm -rf /"}
            }
        }
        ec, stdout, stderr = self._run_gate_with_stdin(json.dumps(payload))

        self.assertEqual(ec, 0, f"Esperado exit 0 para Antigravity em erro de import, obteve {ec}. Stderr: {stderr}")
        data = json.loads(stdout)
        self.assertEqual(data.get("decision"), "deny")
        self.assertIn("Falha crítica de importação", data.get("reason", ""))

    def test_import_error_with_claude_env_yields_deny_exit_2(self):
        """Com CLAUDECODE=1 no ambiente, falha de import deve retornar deny com exit 2."""
        hook_ctx = self.tmp_path / "hook_context.py"
        hook_ctx.write_text("raise RuntimeError('Simulated failure')\n", encoding="utf-8")

        payload = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "rm -rf /"}
        }
        ec, stdout, stderr = self._run_gate_with_stdin(
            json.dumps(payload),
            env_overrides={"CLAUDECODE": "1"}
        )

        self.assertEqual(ec, 2, f"Esperado exit 2 para Claude em erro de import, obteve {ec}. Stderr: {stderr}")
        data = json.loads(stdout)
        self.assertEqual(data.get("decision"), "deny")
        self.assertIn("Falha crítica de importação", data.get("reason", ""))


if __name__ == "__main__":
    unittest.main()
