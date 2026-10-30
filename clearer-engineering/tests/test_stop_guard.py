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

    def test_allow_when_no_feature_file(self):
        """Sem .ceh/feature.json, paradas e comandos intermediários são sempre permitidos."""
        (self.repo / "arquivo.txt").write_text("modificacao", encoding="utf-8")
        payload = {
            "terminationReason": "NO_TOOL_CALL",
            "workspacePaths": [str(self.repo)],
            "lastUserInput": "execute o linter ou git status",
        }
        res = self._run_stop_guard(payload)
        self.assertEqual(res["decision"], "allow")

    def test_allow_during_feature_in_progress(self):
        """Com .ceh/feature.json em status in_progress, comandos intermediários são liberados."""
        ceh_dir = self.repo / ".ceh"
        ceh_dir.mkdir(parents=True, exist_ok=True)
        (ceh_dir / "feature.json").write_text(
            json.dumps({"name": "minha-feature", "status": "in_progress"}),
            encoding="utf-8",
        )
        (self.repo / "arquivo.txt").write_text("modificacao", encoding="utf-8")
        payload = {
            "terminationReason": "NO_TOOL_CALL",
            "workspacePaths": [str(self.repo)],
            "lastUserInput": "adicione a rota /api/v1/auth",
        }
        res = self._run_stop_guard(payload)
        self.assertEqual(res["decision"], "allow")

    def test_continue_when_feature_completing_without_contract(self):
        """No término da feature (status completing) sem Response Contract, deve exigir contrato."""
        ceh_dir = self.repo / ".ceh"
        ceh_dir.mkdir(parents=True, exist_ok=True)
        (ceh_dir / "feature.json").write_text(
            json.dumps({"name": "minha-feature", "status": "completing"}),
            encoding="utf-8",
        )
        payload = {
            "terminationReason": "NO_TOOL_CALL",
            "workspacePaths": [str(self.repo)],
            "lastUserInput": "concluir feature",
        }
        res = self._run_stop_guard(payload)
        self.assertEqual(res["decision"], "continue")
        self.assertIn("CEH Stop Gate", res["reason"])
        self.assertIn("minha-feature", res["reason"])

    def test_continue_when_completion_requested_in_prompt_without_contract(self):
        """Quando o prompt do usuário pede 'finalizar feature', ativa o gate de conclusão."""
        ceh_dir = self.repo / ".ceh"
        ceh_dir.mkdir(parents=True, exist_ok=True)
        (ceh_dir / "feature.json").write_text(
            json.dumps({"name": "auth-core", "status": "in_progress"}),
            encoding="utf-8",
        )
        payload = {
            "terminationReason": "NO_TOOL_CALL",
            "workspacePaths": [str(self.repo)],
            "lastUserInput": "por favor finalizar feature e auditar",
        }
        res = self._run_stop_guard(payload)
        self.assertEqual(res["decision"], "continue")
        self.assertIn("auth-core", res["reason"])

    def test_allow_and_mark_completed_when_contract_present(self):
        """Com status completing e Response Contract no transcript, permite parada e conclui."""
        ceh_dir = self.repo / ".ceh"
        ceh_dir.mkdir(parents=True, exist_ok=True)
        feat_file = ceh_dir / "feature.json"
        feat_file.write_text(
            json.dumps({"name": "minha-feature", "status": "completing"}),
            encoding="utf-8",
        )
        transcript = self.repo / "transcript.jsonl"
        transcript.write_text(
            "bloco final...\nResponse Contract\nResultado: Sucesso\nOBSERVED: Testes verdes\n",
            encoding="utf-8",
        )
        payload = {
            "terminationReason": "NO_TOOL_CALL",
            "workspacePaths": [str(self.repo)],
            "transcriptPath": str(transcript),
            "lastUserInput": "concluir feature",
        }
        res = self._run_stop_guard(payload)
        self.assertEqual(res["decision"], "allow")
        
        # Verifica se atualizou o status para completed
        updated = json.loads(feat_file.read_text(encoding="utf-8"))
        self.assertEqual(updated["status"], "completed")
        self.assertIn("completed_at", updated)

    def test_allow_when_user_bypasses(self):
        """Com 'sem contrato' no prompt, libera a conclusão."""
        ceh_dir = self.repo / ".ceh"
        ceh_dir.mkdir(parents=True, exist_ok=True)
        (ceh_dir / "feature.json").write_text(
            json.dumps({"name": "minha-feature", "status": "completing"}),
            encoding="utf-8",
        )
        payload = {
            "terminationReason": "NO_TOOL_CALL",
            "workspacePaths": [str(self.repo)],
            "lastUserInput": "concluir feature sem contrato por favor",
        }
        res = self._run_stop_guard(payload)
        self.assertEqual(res["decision"], "allow")

    def test_allow_on_error_or_user_canceled(self):
        """Cancelamento do usuário ou erro permite encerramento imediato."""
        ceh_dir = self.repo / ".ceh"
        ceh_dir.mkdir(parents=True, exist_ok=True)
        (ceh_dir / "feature.json").write_text(
            json.dumps({"name": "minha-feature", "status": "completing"}),
            encoding="utf-8",
        )
        payload = {
            "terminationReason": "USER_CANCELED",
            "workspacePaths": [str(self.repo)],
        }
        res = self._run_stop_guard(payload)
        self.assertEqual(res["decision"], "allow")

    def test_cli_lifecycle(self):
        """Testa o ciclo de vida via subcomandos CLI (start, status, complete, cancel)."""
        cwd_orig = os.getcwd()
        try:
            os.chdir(self.repo)
            # start
            proc = subprocess.run(["python3", str(STOP_GUARD), "start", "feat-auth"], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0)
            feat_file = self.repo / ".ceh" / "feature.json"
            self.assertTrue(feat_file.is_file())
            
            # status
            proc = subprocess.run(["python3", str(STOP_GUARD), "status"], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0)
            self.assertIn("feat-auth", proc.stdout)
            
            # complete
            proc = subprocess.run(["python3", str(STOP_GUARD), "complete"], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0)
            data = json.loads(feat_file.read_text(encoding="utf-8"))
            self.assertEqual(data["status"], "completing")
            
            # cancel
            proc = subprocess.run(["python3", str(STOP_GUARD), "cancel"], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0)
            self.assertFalse(feat_file.is_file())
        finally:
            os.chdir(cwd_orig)


if __name__ == "__main__":
    unittest.main()
