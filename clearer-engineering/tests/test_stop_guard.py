#!/usr/bin/env python3
# ==============================================================================
# test_stop_guard.py — Testes Unitários do CEH Stop Guard Hook
# ==============================================================================
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
import os

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
STOP_GUARD = SCRIPTS_DIR / "ceh-stop-guard.py"


class TestCEHStopGuard(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp_dir.name)
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        subprocess.run(["git", "-C", str(self.repo), "config", "user.name", "CEH Test"], check=True)
        subprocess.run(["git", "-C", str(self.repo), "config", "user.email", "test@ceh.local"], check=True)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def _run_stop_guard(self, payload: dict) -> dict:
        proc = subprocess.run(
            ["python3", str(STOP_GUARD)],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
        )
        self.assertEqual(proc.returncode, 0)
        return json.loads(proc.stdout)

    def test_allow_when_no_git_changes(self):
        """Sem alterações de git, parada normal é permitida."""
        payload = {
            "terminationReason": "NO_TOOL_CALL",
            "workspacePaths": [str(self.repo)],
        }
        res = self._run_stop_guard(payload)
        self.assertEqual(res["decision"], "allow")

    def test_continue_when_git_changes_without_contract(self):
        """Com alterações no workspace mas sem contrato emitido, deve forçar continuação."""
        (self.repo / "novo_arquivo.txt").write_text("modificacao", encoding="utf-8")
        payload = {
            "terminationReason": "NO_TOOL_CALL",
            "workspacePaths": [str(self.repo)],
            "lastUserInput": "Implementar funcionalidade",
        }
        res = self._run_stop_guard(payload)
        self.assertEqual(res["decision"], "continue")
        self.assertIn("CEH Stop Gate", res["reason"])

    def test_allow_when_contract_present_in_transcript(self):
        """Com alterações no workspace e contrato no transcript, parada é permitida."""
        (self.repo / "novo_arquivo.txt").write_text("modificacao", encoding="utf-8")
        transcript = self.repo / "transcript.jsonl"
        transcript.write_text("bloco final...\nResponse Contract\nResultado: Sucesso\nOBSERVED: Testes verdes\n", encoding="utf-8")
        
        payload = {
            "terminationReason": "NO_TOOL_CALL",
            "workspacePaths": [str(self.repo)],
            "transcriptPath": str(transcript),
            "lastUserInput": "Implementar funcionalidade",
        }
        res = self._run_stop_guard(payload)
        self.assertEqual(res["decision"], "allow")

    def test_allow_on_error_or_user_canceled(self):
        """Cancelamento do usuário ou erro de execução deve permitir saída imediata."""
        (self.repo / "novo_arquivo.txt").write_text("modificacao", encoding="utf-8")
        payload = {
            "terminationReason": "USER_CANCELED",
            "workspacePaths": [str(self.repo)],
        }
        res = self._run_stop_guard(payload)
        self.assertEqual(res["decision"], "allow")


if __name__ == "__main__":
    unittest.main()
