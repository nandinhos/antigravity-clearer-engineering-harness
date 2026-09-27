"""
test_pre_push_refspecs.py - Bateria de testes do Pre-Push CI Gate com validação de refspecs (PR-08 / G7).
Normativo do Handoff 035 (Onda 2).
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import sys
_TESTS_DIR = Path(__file__).resolve().parent
_SCRIPTS_DIR = _TESTS_DIR.parent / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import importlib.util
_spec = importlib.util.spec_from_file_location("safety_gate", _SCRIPTS_DIR / "safety-gate.py")
_sg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_sg)
evaluate_command = _sg.evaluate_command


class TestPrePushRefspecs(unittest.TestCase):
    """Bateria de testes para validação de refspecs contra o certificado da CI."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="ceh-test-push-")
        self.fixture_path = Path(self.tmp_dir).resolve()
        self.original_cwd = os.getcwd()

        # Inicializa repositório git em branch dev
        subprocess.run(["git", "init", "-b", "dev"], cwd=self.fixture_path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "CEH Test"], cwd=self.fixture_path, check=True)
        subprocess.run(["git", "config", "user.email", "test@ceh.local"], cwd=self.fixture_path, check=True)

        # Adiciona workflow de CI
        ci_dir = self.fixture_path / ".github" / "workflows"
        ci_dir.mkdir(parents=True, exist_ok=True)
        (ci_dir / "ci.yml").write_text("name: CI\njobs:\n  test:\n    runs-on: ubuntu-latest\n")
        (self.fixture_path / ".gitignore").write_text(".ceh/\n")
        (self.fixture_path / "app.txt").write_text("v1\n")
        subprocess.run(["git", "add", "."], cwd=self.fixture_path, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Commit A (certificado)"], cwd=self.fixture_path, check=True, capture_output=True)

        # Commit A é o HEAD certificado
        self.head_a = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=self.fixture_path, check=True, capture_output=True, text=True
        ).stdout.strip()

        # Cria branch outro com Commit B a mais (não certificado)
        subprocess.run(["git", "checkout", "-b", "outro"], cwd=self.fixture_path, check=True, capture_output=True)
        (self.fixture_path / "extra.txt").write_text("v2\n")
        subprocess.run(["git", "add", "."], cwd=self.fixture_path, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Commit B (não certificado)"], cwd=self.fixture_path, check=True, capture_output=True)
        self.head_b = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=self.fixture_path, check=True, capture_output=True, text=True
        ).stdout.strip()

        # Retorna para dev (HEAD == Commit A)
        subprocess.run(["git", "checkout", "dev"], cwd=self.fixture_path, check=True, capture_output=True)

        # Emite certificado aprovado apontando para Commit A
        ceh_dir = self.fixture_path / ".ceh"
        ceh_dir.mkdir(parents=True, exist_ok=True)
        cert_data = (
            f'{{"commit_hash": "{self.head_a}", "status": "PASS", "exit_code": 0, '
            f'"canonical_verified": true, "command": "npm test"}}\n'
        )
        (ceh_dir / "last-ci-run.json").write_text(cert_data, encoding="utf-8")

        os.chdir(self.fixture_path)

    def tearDown(self):
        os.chdir(self.original_cwd)
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_uncertified_refspecs_denied(self):
        """Casos outro:main, +outro:main e outro devem ser bloqueados (deny)."""
        for cmd in (
            "git push origin outro:main",
            "git push origin +outro:main",
            "git push origin outro",
        ):
            dec, reason, env, uc = evaluate_command(cmd, explicit_env="development")
            self.assertEqual(dec, "deny", f"Comando '{cmd}' deveria ser deny, obtido '{dec}' ({reason})")
            self.assertEqual(uc, "PRE_PUSH_CI", f"Use case deveria ser PRE_PUSH_CI, obtido '{uc}'")
            self.assertIn("outro", reason, f"Motivo deveria nomear o refspec 'outro': {reason}")

    def test_certified_refspecs_allowed(self):
        """Casos HEAD:main e dev:main com commit certificado devem ser permitidos (allow)."""
        for cmd in (
            "git push origin HEAD:main",
            "git push origin dev:main",
            "git push origin HEAD",
        ):
            dec, reason, env, uc = evaluate_command(cmd, explicit_env="development")
            self.assertEqual(dec, "allow", f"Comando '{cmd}' deveria ser allow, obtido '{dec}' ({reason})")

    def test_aggregate_push_flags_denied(self):
        """Opções agregadoras --all, --mirror e --tags não podem ser certificadas e devem dar deny."""
        for cmd in (
            "git push --all origin",
            "git push --mirror origin",
            "git push --tags origin",
            "git push --al origin",
        ):
            dec, reason, env, uc = evaluate_command(cmd, explicit_env="development")
            self.assertEqual(dec, "deny", f"Opção em '{cmd}' deveria ser deny, obtido '{dec}' ({reason})")
            self.assertIn("não permitida em repositório com CI", reason)

    def test_remote_deletion_refspec_and_flag(self):
        """Deleção remota (:dst, +:dst, --delete dst, -d dst) graduada como GIT_HISTORY (DEV allow, HML ask, PROD deny)."""
        cmds = (
            "git push origin :main",
            "git push origin +:main",
            "git push origin --delete main",
            "git push origin -d main",
            "git push -d origin main",
            "git push origin --del main",
        )
        for cmd in cmds:
            # Em development: allow
            dec_dev, _, _, uc_dev = evaluate_command(cmd, explicit_env="development")
            self.assertEqual(dec_dev, "allow", f"Deleção '{cmd}' deveria ser allow em dev, obtido '{dec_dev}'")

            # Em staging: ask (com use_case GIT_HISTORY)
            dec_sta, _, _, uc_sta = evaluate_command(cmd, explicit_env="staging")
            self.assertEqual(dec_sta, "ask", f"Deleção '{cmd}' deveria ser ask em staging, obtido '{dec_sta}'")
            self.assertEqual(uc_sta, "GIT_HISTORY")

            # Em production: deny (com use_case GIT_HISTORY)
            dec_prod, _, _, uc_prod = evaluate_command(cmd, explicit_env="production")
            self.assertEqual(dec_prod, "deny", f"Deleção '{cmd}' deveria ser deny em production, obtido '{dec_prod}'")
            self.assertEqual(uc_prod, "GIT_HISTORY")

    def test_abbreviated_force_flag_matches_force(self):
        """--forc tem o mesmo comportamento de --force (allow se commit certificado, deny se não)."""
        # Com refspec certificado (HEAD:main): permitido em dev
        dec_cert, _, _, _ = evaluate_command("git push --forc origin HEAD:main", explicit_env="development")
        self.assertEqual(dec_cert, "allow")

        # Com refspec não certificado (outro:main): bloqueado pelo CI gate
        dec_uncert, reason, _, uc = evaluate_command("git push --forc origin outro:main", explicit_env="development")
        self.assertEqual(dec_uncert, "deny")
        self.assertEqual(uc, "PRE_PUSH_CI")

    def test_context_git_dash_c_and_cd_block_uncertified_push(self):
        """Verifica se git -C <fixture> e cd <fixture> && git push são bloqueados fora do cwd da fixture."""
        os.chdir(self.original_cwd)  # Volta para fora da fixture

        cmd_dash_c = f"git -C {self.fixture_path} push origin outro:main"
        dec, reason, env, uc = evaluate_command(cmd_dash_c, explicit_env="development")
        self.assertEqual(dec, "deny", f"git -C falhou: esperado deny, obtido '{dec}' ({reason})")
        self.assertIn("outro:main", reason)

        cmd_cd = f"cd {self.fixture_path} && git push origin outro:main"
        dec_cd, reason_cd, env_cd, uc_cd = evaluate_command(cmd_cd, explicit_env="development")
        self.assertEqual(dec_cd, "deny", f"cd && push falhou: esperado deny, obtido '{dec_cd}' ({reason_cd})")
        self.assertIn("outro:main", reason_cd)


if __name__ == "__main__":
    unittest.main()
