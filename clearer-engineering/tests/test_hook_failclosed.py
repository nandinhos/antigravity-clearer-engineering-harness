#!/usr/bin/env python3
"""
test_hook_failclosed.py — Validação de Fail-Closed estrito em falhas de importação no shim (PR-13 / PR-16 / BI1).

Comprova formalmente que falhas de import no hook_context, ceh_core ou adaptadores específicos
não quebram o contrato de fail-closed do Safety Gate, respondendo no formato observado de cada host:
- Payloads do Antigravity: retorna JSON com 'deny' e exit code 0.
- Payloads do Muse: retorna JSON com 'block' e exit code 0 (evitando fail-open comprovado no E1c).
- Payloads do Claude Code: retorna hookSpecificOutput com permissionDecision 'deny' e exit code 2.
- Cenário degradado (fallback.py quebrado + ceh_core quebrado): cai no fallback genérico documentado no ADR 007.
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
FIXTURES_DIR = REPO_ROOT / "clearer-engineering" / "tests" / "fixtures" / "adapters"


class TestHookFailClosed(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="ceh_failclosed_test_")
        self.tmp_path = Path(self.tmp_dir)

        # Copia scripts do CEH para o ambiente temporário isolado
        shutil.copy(SCRIPTS_DIR / "safety-gate.py", self.tmp_path / "safety-gate.py")
        shutil.copy(SCRIPTS_DIR / "hook_context.py", self.tmp_path / "hook_context.py")
        shutil.copytree(SCRIPTS_DIR / "ceh_core", self.tmp_path / "ceh_core")
        shutil.copytree(SCRIPTS_DIR / "adapters", self.tmp_path / "adapters")

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _get_recorded_payload(self, host: str) -> dict:
        fixture_file = FIXTURES_DIR / host / "recorded.jsonl"
        line = fixture_file.read_text(encoding="utf-8").splitlines()[0]
        return json.loads(line)["payload"]

    def _run_gate_with_stdin(self, stdin_text: str, env_overrides: dict[str, str] | None = None) -> tuple[int, str, str]:
        env = os.environ.copy()
        env.pop("CEH_EXPLICIT_ENV", None)
        env.pop("APP_ENV", None)
        for key in list(env.keys()):
            if key.startswith("CLAUDE"):
                env.pop(key, None)
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

    def test_muse_adapter_syntax_error_yields_block_exit_0(self):
        """Quando muse.py tem erro de sintaxe, o fallback reconhece o payload do Muse e responde 'block' com exit 0."""
        muse_py = self.tmp_path / "adapters" / "muse.py"
        muse_py.write_text("def broken_muse_syntax(: syntax error\n", encoding="utf-8")

        payload = self._get_recorded_payload("muse")

        # 1. Sem variáveis do Claude no ambiente
        ec, stdout, stderr = self._run_gate_with_stdin(json.dumps(payload))
        self.assertEqual(ec, 0, f"Esperado exit 0 para Muse com muse.py quebrado, obteve {ec}. Stderr: {stderr}")
        data = json.loads(stdout)
        self.assertEqual(data.get("decision"), "block", f"Esperado 'block' para Muse, obteve {data}")

        # 2. Mesmo com variáveis do Claude no ambiente, o payload do Muse tem precedência
        ec2, stdout2, stderr2 = self._run_gate_with_stdin(json.dumps(payload), env_overrides={"CLAUDECODE": "1"})
        self.assertEqual(ec2, 0, f"Esperado exit 0 para Muse mesmo sob CLAUDECODE=1, obteve {ec2}. Stderr: {stderr2}")
        data2 = json.loads(stdout2)
        self.assertEqual(data2.get("decision"), "block", f"Esperado 'block' para Muse sob CLAUDECODE=1, obteve {data2}")

    def test_ceh_core_broken_yields_table_format_for_each_host(self):
        """Quando ceh_core quebra, a reserva responde no formato exato da tabela observada para cada host."""
        engine_py = self.tmp_path / "ceh_core" / "engine.py"
        engine_py.write_text("raise RuntimeError('Simulated ceh_core failure')\n", encoding="utf-8")

        # 1. Host Antigravity -> {"decision": "deny"}, exit 0
        agy_payload = self._get_recorded_payload("antigravity")
        ec_agy, out_agy, _ = self._run_gate_with_stdin(json.dumps(agy_payload))
        self.assertEqual(ec_agy, 0)
        data_agy = json.loads(out_agy)
        self.assertEqual(data_agy.get("decision"), "deny")

        # 2. Host Muse -> {"decision": "block"}, exit 0
        muse_payload = self._get_recorded_payload("muse")
        ec_muse, out_muse, _ = self._run_gate_with_stdin(json.dumps(muse_payload))
        self.assertEqual(ec_muse, 0)
        data_muse = json.loads(out_muse)
        self.assertEqual(data_muse.get("decision"), "block")

        # 3. Host Claude Code -> hookSpecificOutput com deny, exit 2
        claude_payload = self._get_recorded_payload("claude_code")
        ec_claude, out_claude, _ = self._run_gate_with_stdin(json.dumps(claude_payload))
        self.assertEqual(ec_claude, 2)
        data_claude = json.loads(out_claude)
        self.assertIn("hookSpecificOutput", data_claude)
        self.assertEqual(data_claude["hookSpecificOutput"].get("permissionDecision"), "deny")

    def test_fallback_broken_and_core_broken_yields_generic_response(self):
        """
        Quando adapters/fallback.py E ceh_core estão quebrados:
        Cai na resposta de emergência pura (limite documentado no ADR 007).
        """
        engine_py = self.tmp_path / "ceh_core" / "engine.py"
        engine_py.write_text("raise RuntimeError('Core broken')\n", encoding="utf-8")

        fallback_py = self.tmp_path / "adapters" / "fallback.py"
        fallback_py.write_text("def syntax_error_in_fallback(: syntax error\n", encoding="utf-8")

        payload = self._get_recorded_payload("antigravity")

        # Sem variáveis do Claude -> exit 0, {"decision": "deny"}
        ec, stdout, _ = self._run_gate_with_stdin(json.dumps(payload))
        self.assertEqual(ec, 0)
        data = json.loads(stdout)
        self.assertEqual(data.get("decision"), "deny")

        # Com variáveis do Claude -> exit 2, {"decision": "deny"}
        ec_c, stdout_c, _ = self._run_gate_with_stdin(json.dumps(payload), env_overrides={"CLAUDECODE": "1"})
        self.assertEqual(ec_c, 2)
        data_c = json.loads(stdout_c)
        self.assertEqual(data_c.get("decision"), "deny")


if __name__ == "__main__":
    unittest.main()
