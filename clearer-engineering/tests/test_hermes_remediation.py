#!/usr/bin/env python3
"""
test_hermes_remediation.py — Bateria de testes de falsificabilidade (RED-GREEN)
para os achados da Fase A1 da Auditoria do Hermes (F02, F03, F04, F05, F10, F01).
"""
import json
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


class TestHermesRemediationPhaseA2(unittest.TestCase):
    """Bateria de testes para a Fase A2 (Runner Bash: F06, F07, F08)."""
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="ceh_runner_test_")
        self.runner_script = str(Path(_SCRIPTS_DIR) / "test-runner.sh")
        self.original_cwd = os.getcwd()
        self.original_path = os.environ.get("PATH", "")

        # Inicializar repo Git limpo
        subprocess.run(["git", "init", "-b", "dev"], cwd=self.tmp_dir, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Tester"], cwd=self.tmp_dir, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "t@t.l"], cwd=self.tmp_dir, check=True, capture_output=True)
        (Path(self.tmp_dir) / "tracked.txt").write_text("initial content\n")
        subprocess.run(["git", "add", "."], cwd=self.tmp_dir, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=self.tmp_dir, check=True, capture_output=True)
        os.chdir(self.tmp_dir)

    def tearDown(self):
        os.chdir(self.original_cwd)
        os.environ["PATH"] = self.original_path
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_f06_sail_adaptation_revokes_canonical_verification_when_command_differs(self):
        """F06: Se o adapter de runtime trocar o comando para Sail, canonical_verified DEVE ser false se diferir da suíte canônica."""
        import json
        # Configurar comando canonico explícito
        ceh_dir = Path(self.tmp_dir) / ".ceh"
        ceh_dir.mkdir(parents=True, exist_ok=True)
        config_file = ceh_dir / "config.json"
        config_file.write_text(json.dumps({"canonical_test_command": "bash canonical.sh"}))
        subprocess.run(["git", "add", "."], cwd=self.tmp_dir, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "add config"], cwd=self.tmp_dir, check=True, capture_output=True)

        # Criar mock docker e mock sail
        bin_dir = Path(self.tmp_dir) / "fake_bin"
        bin_dir.mkdir()
        mock_docker = bin_dir / "docker"
        mock_docker.write_text("#!/bin/sh\nif [ \"$1\" = \"info\" ]; then exit 0; fi\nif [ \"$1\" = \"compose\" ] && [ \"$2\" = \"ps\" ]; then echo 'laravel.test'; exit 0; fi\nexit 0\n")
        mock_docker.chmod(0o755)

        vendor_bin = Path(self.tmp_dir) / "vendor" / "bin"
        vendor_bin.mkdir(parents=True)
        mock_sail = vendor_bin / "sail"
        mock_sail.write_text("#!/bin/sh\necho 'Sail mock ran'\nexit 0\n")
        mock_sail.chmod(0o755)

        (Path(self.tmp_dir) / "docker-compose.yml").write_text("version: '3'\n")
        (Path(self.tmp_dir) / ".gitignore").write_text("fake_bin/\n")
        subprocess.run(["git", "add", "."], cwd=self.tmp_dir, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "add mocks and sail"], cwd=self.tmp_dir, check=True, capture_output=True)

        os.environ["PATH"] = f"{bin_dir}:{self.original_path}"

        res = subprocess.run(["bash", self.runner_script], cwd=self.tmp_dir, capture_output=True, text=True)
        cert_file = ceh_dir / "last-ci-run.json"
        self.assertTrue(cert_file.exists(), f"F06: Certificado deveria ser emitido pelo mock. Out: {res.stdout}\nErr: {res.stderr}")
        cert = json.loads(cert_file.read_text())
        self.assertFalse(
            cert.get("canonical_verified", False),
            f"F06 RED: canonical_verified deveria ser False quando o runtime adapter troca a suíte canônica por Sail! Cert: {cert}"
        )

    def test_f07_missing_pytest_does_not_silently_fallback_to_unittest(self):
        """F07: Projeto com pytest.ini sem pytest no PATH não pode rodar unittest silenciosamente e emitir PASS."""
        (Path(self.tmp_dir) / "pytest.ini").write_text("[pytest]\n")
        # Criar um teste que passaria no unittest
        test_file = Path(self.tmp_dir) / "test_sample.py"
        test_file.write_text("import unittest\nclass T(unittest.TestCase):\n    def test_ok(self):\n        pass\n")
        subprocess.run(["git", "add", "."], cwd=self.tmp_dir, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "add pytest.ini and test"], cwd=self.tmp_dir, check=True, capture_output=True)

        # Mascarar pytest do PATH
        fake_bin = Path(self.tmp_dir) / "no_pytest_bin"
        fake_bin.mkdir()
        # Copiar executáveis essenciais exceto pytest
        os.environ["PATH"] = "/usr/bin:/bin"

        # Se pytest for chamado via command -v pytest, simular ausência
        res = subprocess.run(
            ["bash", "-c", f"PATH='/bin:/usr/bin' which pytest 2>/dev/null || true"],
            capture_output=True, text=True
        )
        if not res.stdout.strip():
            # Executar test-runner
            res_runner = subprocess.run(["bash", self.runner_script], cwd=self.tmp_dir, capture_output=True, text=True)
            self.assertNotEqual(res_runner.returncode, 0, "F07: Runner deveria falhar quando pytest está ausente em projeto pytest.")
            self.assertIn("pytest", res_runner.stdout.lower() + res_runner.stderr.lower())

    def test_f08_dirty_worktree_after_tests_revokes_certificate(self):
        """F08: Se a execução do teste sujar a worktree (modificar arquivo rastreado ou criar não commitado), o certificado NÃO pode ser emitido."""
        dirty_test_cmd = 'python3 -c "open(\\"tracked.txt\\", \\"a\\").write(\\"dirty\\\\n\\")"'
        res = subprocess.run(["bash", self.runner_script, dirty_test_cmd], cwd=self.tmp_dir, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"O comando de teste em si teve sucesso (exit 0). Output: {res.stdout}\nErr: {res.stderr}")
        cert_file = Path(self.tmp_dir) / ".ceh" / "last-ci-run.json"
        self.assertFalse(
            cert_file.exists(),
            f"F08: Certificado NÃO deveria ser emitido quando a worktree é modificada durante os testes! Cert: {cert_file.read_text() if cert_file.exists() else ''}"
        )


class TestHermesRemediationPhaseB(unittest.TestCase):
    """Bateria de testes para a Fase B (Empacotador, Aliases, Manifestos: F09, F11, F12, F14, F15)."""
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="ceh_phase_b_")
        self.package_tool = str(Path(_SCRIPTS_DIR).parents[0] / "tools" / "package.py")
        self.source_dir = Path(_SCRIPTS_DIR).parents[0]

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_f15_evidence_report_detect_env_valid(self):
        """F15: evidence_report.detect_env() detecta o ambiente real sem falha de AttributeError."""
        import evidence_report
        res = evidence_report.detect_env()
        self.assertNotIn("AttributeError", res, f"F15: detect_env() retornou AttributeError: {res}")
        self.assertTrue(res.startswith(("DEVELOPMENT", "PRODUCTION", "STAGING")), f"Formato de ambiente inesperado: {res}")

    def test_f14_muse_manifest_version_matches_plugin_json(self):
        """F14: O manifesto do Muse empacotado reflete a versão canônica de plugin.json."""
        out_muse = Path(self.tmp_dir) / "muse_pkg"
        res = subprocess.run([sys.executable, self.package_tool, "--host", "muse", "--out", str(out_muse)], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"package.py falhou: {res.stderr}")

        plugin_json = json.loads((self.source_dir / "plugin.json").read_text(encoding="utf-8"))
        canonical_ver = plugin_json["version"]

        manifest = json.loads((out_muse / ".muse-plugin" / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["version"], canonical_ver, f"F14: Versão do Muse ({manifest['version']}) difere de plugin.json ({canonical_ver})")

    def test_f09_claude_settings_matcher_includes_all_edit_tools(self):
        """F09: A configuração do Claude Code gerada pelo empacotador intercepta Write, Edit, MultiEdit e NotebookEdit."""
        out_claude = Path(self.tmp_dir) / "claude_pkg"
        res = subprocess.run([sys.executable, self.package_tool, "--host", "claude-code", "--out", str(out_claude)], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"package.py falhou: {res.stderr}")

        settings = json.loads((out_claude / ".claude" / "settings.json").read_text(encoding="utf-8"))
        matchers = [hook["matcher"] for hook in settings["hooks"]["PreToolUse"]]
        combined = "|".join(matchers)
        for expected in ["Write", "Edit", "MultiEdit", "NotebookEdit"]:
            self.assertIn(expected, combined, f"F09: Matcher PreToolUse do Claude não cobre {expected}: {combined}")

    def test_f11_package_refuses_unmanaged_nonempty_directory(self):
        """F11: package.py se recusa a apagar e sobrescrever diretório não vazio sem o marcador .ceh-package-managed."""
        unsafe_dir = Path(self.tmp_dir) / "user_data"
        unsafe_dir.mkdir()
        sentinel = unsafe_dir / "user_sentinel.txt"
        sentinel.write_text("critical user content\n")

        res = subprocess.run([sys.executable, self.package_tool, "--host", "muse", "--out", str(unsafe_dir)], capture_output=True, text=True)
        self.assertNotEqual(res.returncode, 0, "F11: package.py deveria abortar ao receber diretório não vazio não gerenciado!")
        self.assertTrue(sentinel.exists(), "F11: Arquivo do usuário FOI APAGADO pelo package.py!")

    def test_f12_rc_aliases_line_anchoring(self):
        """F12: rc_aliases.remove_ceh_block não apaga linhas válidas de configuração que contêm marcadores como strings em echo."""
        import rc_aliases
        user_rc = (
            '# Mock .bashrc\n'
            f'echo "{rc_aliases.START_MARKER}"\n'
            'export USER_SETTING=keep\n'
            f'echo "{rc_aliases.END_MARKER}"\n'
        )
        cleaned = rc_aliases.remove_ceh_block(user_rc)
        self.assertIn("export USER_SETTING=keep", cleaned, "F12 RED: remove_ceh_block removeu configuração legítima do usuário!")
class TestCA1WriteRedirectionControls(unittest.TestCase):
    """Bateria de testes para CA1/CA2: integridade estrita de .ceh/ sob todas as formas de redirecionamento."""
    def setUp(self):
        self.tmp_repo = tempfile.mkdtemp(prefix="ceh_ca1_sandbox_")
        self.original_cwd = os.getcwd()
        os.chdir(self.tmp_repo)

    def tearDown(self):
        os.chdir(self.original_cwd)
        shutil.rmtree(self.tmp_repo, ignore_errors=True)

    def test_all_write_redirect_operators_against_ceh(self):
        """CA1: >, >>, >|, &>, &>>, 2>, 2>>, <> colados e separados com casefold, arquivos genéricos e .. devem dar deny."""
        targets = [
            ".ceh/a",
            ".ceh/config.json",
            ".ceh/last-ci-run.json",
            ".CEH/a",
            ".Ceh/sub/file.txt",
            "./subdir/../.ceh/a",
        ]
        operators = [">", ">>", ">|", "&>", "&>>", "2>", "2>>", "<>"]
        for tgt in targets:
            for op in operators:
                for glued in (True, False):
                    cmd = f"echo payload{op}{tgt}" if glued else f"echo payload {op} {tgt}"
                    req = Request(command=cmd, cwd=self.tmp_repo)
                    dec = evaluate(req)
                    self.assertEqual(dec.decision, "deny", f"Esperado deny para: {cmd}")
                    self.assertEqual(dec.use_case, "CERTIFICATE_INTEGRITY", f"Esperado CERTIFICATE_INTEGRITY para: {cmd}")

    def test_ca1_symlink_redirection_blocked(self):
        """CC2: Redirecionamento de escrita via symlink apontando para .ceh deve dar deny."""
        ceh_dir = Path(self.tmp_repo) / ".ceh"
        ceh_dir.mkdir(exist_ok=True)
        link_dir = Path(self.tmp_repo) / "link_to_ceh"
        if not link_dir.exists():
            os.symlink(ceh_dir, link_dir)

        sym_cmds = [
            f"echo payload > {link_dir}/a",
            f"echo payload > {link_dir}/config.json",
            "echo payload > link_to_ceh/a",
            "echo payload > link_to_ceh/config.json",
            "echo payload >.ceh/a",
            "printf payload >.ceh/config.json",
            "echo payload &>.ceh/a",
        ]
        for cmd in sym_cmds:
            req = Request(command=cmd, cwd=self.tmp_repo)
            dec = evaluate(req)
            self.assertEqual(dec.decision, "deny", f"Esperado deny para symlink/alvo ceh: {cmd}")
            self.assertEqual(dec.use_case, "CERTIFICATE_INTEGRITY")

    def test_ca1_negative_controls_allowed(self):
        """CA1 (Controles Negativos): Leituras puras, redirecionamento para fora, tsconfig.json e 2>&1 permanecem allow."""
        allowed_cmds = [
            "cat .ceh/last-ci-run.json > /tmp/output.json",
            "cat .ceh/last-ci-run.json > output.json",
            "echo test 2>&1",
            "echo test >&2",
            "cat .ceh/last-ci-run.json | grep commit_hash",
            'echo "a>b"',
            "cat .ceh/last-ci-run.json",
            "echo {} > tsconfig.json",
            "echo x > src/app/config.json",
            "echo x > jsconfig.json",
            "cat tsconfig.json",
        ]
        for cmd in allowed_cmds:
            req = Request(command=cmd, cwd=self.tmp_repo)
            dec = evaluate(req)
            self.assertEqual(dec.decision, "allow", f"Esperado allow para: {cmd} (obteve {dec.decision} - {dec.reason})")

    def test_cc1_ide_file_write_tools_tsconfig_allowed(self):
        """CC1: write_to_file / replace_file_content em tsconfig.json e config.json fora de .ceh deve ser allow."""
        req1 = Request(target_paths=["tsconfig.json", "src/config.json", "jsconfig.json"], cwd=self.tmp_repo)
        self.assertEqual(evaluate(req1).decision, "allow")

        req2 = Request(target_paths=[".ceh/config.json", ".ceh/a"], cwd=self.tmp_repo)
        self.assertEqual(evaluate(req2).decision, "deny")


if __name__ == "__main__":
    unittest.main()
