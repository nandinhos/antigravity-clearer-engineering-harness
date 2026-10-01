#!/usr/bin/env python3
"""
test_hermes_remediation.py — Bateria de testes de falsificabilidade (RED-GREEN)
para os achados da Fase A1 da Auditoria do Hermes (F02, F03, F04, F05, F10, F01).
"""
import os
import shutil
import tempfile
import unittest
import subprocess
from pathlib import Path

_SCRIPTS_DIR = str(Path(__file__).resolve().parents[1] / "scripts")
import sys
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from ceh_core.engine import Request, evaluate


class TestHermesRemediationPhaseA1(unittest.TestCase):
    def setUp(self):
        self.tmp_repo = tempfile.mkdtemp(prefix="ceh_hermes_sandbox_")
        self.original_cwd = os.getcwd()

        # Configurar repo com branch dev e CI workflow
        subprocess.run(["git", "init", "-b", "dev"], cwd=self.tmp_repo, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "HermesTest"], cwd=self.tmp_repo, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "hermes@test.local"], cwd=self.tmp_repo, check=True, capture_output=True)
        ci_dir = Path(self.tmp_repo) / ".github" / "workflows"
        ci_dir.mkdir(parents=True, exist_ok=True)
        (ci_dir / "ci.yml").write_text("name: CI\non: push\n")
        (Path(self.tmp_repo) / "README.md").write_text("Hermes Sandbox\n")
        subprocess.run(["git", "add", "."], cwd=self.tmp_repo, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=self.tmp_repo, check=True, capture_output=True)
        os.chdir(self.tmp_repo)

    def tearDown(self):
        os.chdir(self.original_cwd)
        shutil.rmtree(self.tmp_repo, ignore_errors=True)

    # -------------------------------------------------------------
    # A1.1 (F02) - Monotonicidade de Ambiente no Desembrulho de Shell
    # -------------------------------------------------------------
    def test_f02_shell_unwrap_env_floor_positive(self):
        """F02: env APP_ENV=production bash -c 'php artisan migrate:fresh' nao pode ser rebaixado para dev."""
        req = Request(
            command="env APP_ENV=production bash -c 'php artisan migrate:fresh'",
            cwd=self.tmp_repo
        )
        dec = evaluate(req)
        # Em producao, migrate:fresh DEVE ser deny absoluto
        self.assertEqual(dec.decision, "deny", f"Esperado 'deny' em producao herdada, obteve: {dec}")
        self.assertEqual(dec.environment, "production", f"Ambiente efetivo deveria ser 'production', obteve: {dec.environment}")

    def test_f02_shell_unwrap_env_floor_negative(self):
        """F02 (Negativo): comando benigno em dev sob bash -c permanece allow em dev."""
        req = Request(
            command="bash -c 'ls -la'",
            cwd=self.tmp_repo
        )
        dec = evaluate(req)
        self.assertEqual(dec.decision, "allow")

    # -------------------------------------------------------------
    # A1.2 (F03) - Invocação Canônica de Git por Basename Exato
    # -------------------------------------------------------------
    def test_f03_absolute_git_invocation_positive(self):
        """F03: /usr/bin/git push origin dev sem certificado deve ser interceptado pelo PRE_PUSH_CI gate."""
        req = Request(
            command="/usr/bin/git push origin HEAD:dev",
            cwd=self.tmp_repo
        )
        dec = evaluate(req)
        self.assertEqual(dec.decision, "deny", f"Esperado 'deny' de pre-push CI, obteve: {dec}")
        self.assertEqual(dec.use_case, "PRE_PUSH_CI", f"Esperado use_case 'PRE_PUSH_CI', obteve: {dec.use_case}")

    def test_f03_absolute_git_invocation_negative(self):
        """F03 (Negativo): /usr/bin/git status continua sendo leitura pura permitida."""
        req = Request(
            command="/usr/bin/git status",
            cwd=self.tmp_repo
        )
        dec = evaluate(req)
        self.assertEqual(dec.decision, "allow")

    # -------------------------------------------------------------
    # A1.3 (F04) - Flags Estruturadas em Git Reset e Git Push
    # -------------------------------------------------------------
    def test_f04_git_reset_flag_permutations(self):
        """F04: git reset HEAD --hard deve ser classificado como destrutivo GIT_HISTORY."""
        req = Request(
            command="git reset HEAD --hard",
            cwd=self.tmp_repo,
            explicit_env="production"
        )
        dec = evaluate(req)
        self.assertEqual(dec.decision, "deny", f"git reset HEAD --hard em producao deve ser deny, obteve: {dec}")

    def test_f04_git_push_grouped_flags(self):
        """F04: git push -vf origin HEAD:dev deve ser reconhecido como force push destrutivo."""
        req = Request(
            command="git push -vf origin HEAD:dev",
            cwd=self.tmp_repo,
            explicit_env="production"
        )
        dec = evaluate(req)
        # Force push em producao deve ser deny
        self.assertEqual(dec.decision, "deny", f"git push -vf em producao deve ser deny, obteve: {dec}")

    def test_f04_git_reset_unstage_negative(self):
        """F04 (Negativo): git reset HEAD file.txt (unstage simples) e seguro e permitido."""
        req = Request(
            command="git reset HEAD README.md",
            cwd=self.tmp_repo,
            explicit_env="production"
        )
        dec = evaluate(req)
        self.assertEqual(dec.decision, "allow")

    # -------------------------------------------------------------
    # A1.4 (F05) - Fail-Closed em Push Indireto sem Refspec
    # -------------------------------------------------------------
    def test_f05_push_non_standard_config_fail_closed(self):
        """F05: git push origin com remote.origin.push configurado para ref diferente de HEAD deve ser fail-closed."""
        subprocess.run(
            ["git", "config", "remote.origin.push", "unchecked:refs/heads/dev"],
            cwd=self.tmp_repo,
            check=True,
            capture_output=True
        )
        req = Request(
            command="git push origin",
            cwd=self.tmp_repo
        )
        dec = evaluate(req)
        # Deve bloquear por fail-closed pois nao certifica a ref alvo
        self.assertEqual(dec.decision, "deny", f"Push indireto sem refspec e com config customizada deve ser deny, obteve: {dec}")

    # -------------------------------------------------------------
    # A1.5 (F10) - Regra Sintática para rm com Flags Recursivas (-r/-R)
    # -------------------------------------------------------------
    def test_f10_dotted_directory_rm_recursive_rejection(self):
        """F10: rm -rf customer.db (com flag -r) nao pode usar atalho de arquivo unico, mesmo com ponto."""
        req = Request(
            command="rm -rf customer.db",
            cwd=self.tmp_repo,
            explicit_env="production"
        )
        dec = evaluate(req)
        self.assertEqual(dec.decision, "deny", f"rm -rf com flag recursiva em producao deve ser deny, obteve: {dec}")

    def test_f10_single_file_rm_negative(self):
        """F10 (Negativo): rm -f build.log (sem flag -r) permanece permitido pelo atalho de arquivo unico."""
        req = Request(
            command="rm -f build.log",
            cwd=self.tmp_repo,
            explicit_env="production"
        )
        dec = evaluate(req)
        self.assertEqual(dec.decision, "allow")

    # -------------------------------------------------------------
    # A1.6 (F01) - Redirecionamento Adjacente e Wrappers com .ceh/
    # -------------------------------------------------------------
    def test_f01a_adjacent_redirection_tampering(self):
        """F01a: cat f>.ceh/last-ci-run.json deve ser classificado como CERTIFICATE_INTEGRITY (G9)."""
        req = Request(
            command="cat sample.txt>.ceh/last-ci-run.json",
            cwd=self.tmp_repo
        )
        dec = evaluate(req)
        self.assertEqual(dec.decision, "deny", f"Redirecionamento adjacente para .ceh deve ser deny, obteve: {dec}")
        self.assertEqual(dec.use_case, "CERTIFICATE_INTEGRITY")

    def test_f01b_wrapper_tail_redirection_tampering(self):
        """F01b: bash -c 'echo ok' > .ceh/last-ci-run.json deve ser classificado como CERTIFICATE_INTEGRITY (G9)."""
        req = Request(
            command="bash -c 'echo ok' > .ceh/last-ci-run.json",
            cwd=self.tmp_repo
        )
        dec = evaluate(req)
        self.assertEqual(dec.decision, "deny", f"Redirecionamento externo de wrapper para .ceh deve ser deny, obteve: {dec}")
        self.assertEqual(dec.use_case, "CERTIFICATE_INTEGRITY")

    def test_f01_safe_string_negative(self):
        """F01 (Negativo): echo 'a>b' ou leitura de .ceh/ permanecem permitidos."""
        req1 = Request(
            command='echo "a>b"',
            cwd=self.tmp_repo
        )
        self.assertEqual(evaluate(req1).decision, "allow")

        req2 = Request(
            command="cat .ceh/last-ci-run.json",
            cwd=self.tmp_repo
        )
        self.assertEqual(evaluate(req2).decision, "allow")


if __name__ == "__main__":
    unittest.main()
