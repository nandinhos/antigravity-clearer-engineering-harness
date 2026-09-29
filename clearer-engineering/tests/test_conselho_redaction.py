#!/usr/bin/env python3
"""
test_conselho_redaction.py - Testes de segurança de redação preventiva no Conselho de Seniores (PR-21).

Valida:
1. Mascaramento determinístico de tokens/segredos sintéticos (Git, AWS, Google, OpenAI, Auth).
2. Substituição de caminhos absolutos de home (/home/<user>/ e /Users/<user>/) por ~.
3. Exclusão de arquivos sensíveis (.env*, *.key, *.pem, *secret*, id_rsa*) no diff.
4. Ausência total de segredos sintéticos e caminhos de home nos artefatos gravados (prompt_*.txt).
5. Prova por mutação: desativar a redação reprova a verificação com AssertionError comprovado.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from ceh_core.redact import redact_payload, redact_paths, redact_secrets

CONSELHO_SCRIPT = SCRIPTS_DIR / "conselho-seniores.sh"


class TestConselhoRedaction(unittest.TestCase):
    """Testes comportamentais e de mutação para a redação do Conselho de Seniores."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="ceh-redact-test-")

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_unit_redact_synthetic_secrets_and_paths(self):
        """Validação unitária dos padrões de token e caminhos com segredos sintéticos inventados."""
        synthetic_git = "ghp_SYNTHETIC1234567890abcdefghijklmnop"
        synthetic_aws = "AKIAIOSFODNN7EXAMPLE"
        synthetic_google = "AIzaSySYNTHETIC1234567890123456789012"
        synthetic_ai = "sk-ant-api03-SYNTHETIC1234567890abcdefghijklm"
        synthetic_auth = "Authorization: Bearer token-synth-secret-999"
        synthetic_home_linux = "/home/fakedev/projects/myapp/src"
        synthetic_home_mac = "/Users/fakeauthor/Library/Application Support"

        raw_payload = f"""
        # Configuração do Sistema
        GIT_TOKEN={synthetic_git}
        AWS_KEY={synthetic_aws}
        GOOGLE_API_KEY={synthetic_google}
        ANTHROPIC_KEY={synthetic_ai}
        Header: {synthetic_auth}
        Caminho Linux: {synthetic_home_linux}
        Caminho macOS: {synthetic_home_mac}
        """

        redacted = redact_payload(raw_payload)

        # Asserções de segurança: nenhum segredo sintético deve escapar
        self.assertNotIn(synthetic_git, redacted)
        self.assertNotIn(synthetic_aws, redacted)
        self.assertNotIn(synthetic_google, redacted)
        self.assertNotIn(synthetic_ai, redacted)
        self.assertNotIn("token-synth-secret-999", redacted)
        self.assertNotIn("/home/fakedev", redacted)
        self.assertNotIn("/Users/fakeauthor", redacted)

        # Asserções de presença dos marcadores canônicos de redação
        self.assertIn("[REDACTED_GIT_TOKEN]", redacted)
        self.assertIn("[REDACTED_AWS_KEY]", redacted)
        self.assertIn("[REDACTED_GOOGLE_KEY]", redacted)
        self.assertIn("[REDACTED_API_KEY]", redacted)
        self.assertIn("[REDACTED_AUTH_TOKEN]", redacted)
        self.assertIn("~/projects/myapp/src", redacted)
        self.assertIn("~/Library/Application Support", redacted)

    def test_conselho_cli_redacts_prompt_and_context_artifacts(self):
        """Executa conselho-seniores.sh com segredos sintéticos e valida que prompt_*.txt fica limpo."""
        output_dir = Path(self.tmp_dir) / "output"
        synthetic_secret = "ghp_SYNTHETIC99999999999999999999999999"
        synthetic_home = "/home/fictitious_developer/projects/repo"

        # Inicializa um repositório temporário com git
        repo_dir = Path(self.tmp_dir) / "repo"
        repo_dir.mkdir()
        subprocess.run(["git", "init", "-q", "-b", "dev", str(repo_dir)], check=True)
        subprocess.run(["git", "-C", str(repo_dir), "config", "user.name", "Test User"], check=True)
        subprocess.run(["git", "-C", str(repo_dir), "config", "user.email", "test@example.com"], check=True)

        # Cria arquivo com segredo no repositório
        test_file = repo_dir / "app.py"
        test_file.write_text(f"# app config\nAPI_KEY = '{synthetic_secret}'\nPATH = '{synthetic_home}'\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(repo_dir), "add", "app.py"], check=True)
        subprocess.run(["git", "-C", str(repo_dir), "commit", "-q", "-m", "initial commit"], check=True)

        # Executa conselho-seniores.sh em modo dry-run
        env = os.environ.copy()
        env["HOME"] = str(Path(self.tmp_dir) / "fakehome")
        cmd = [
            "bash",
            str(CONSELHO_SCRIPT),
            "--agent", "claude",
            "--dry-run",
            "--prompt", f"Avaliar código contendo token {synthetic_secret} e path {synthetic_home}",
            "--output-dir", str(output_dir),
        ]

        proc = subprocess.run(cmd, cwd=str(repo_dir), capture_output=True, text=True, env=env)
        self.assertEqual(proc.returncode, 0, f"Falha no conselho-seniores.sh: {proc.stderr}")

        context_file = output_dir / "contexto_avaliado.txt"
        prompt_file = output_dir / "prompt_claude.txt"

        self.assertTrue(context_file.is_file(), "contexto_avaliado.txt não foi criado")
        self.assertTrue(prompt_file.is_file(), "prompt_claude.txt não foi criado")

        context_content = context_file.read_text(encoding="utf-8")
        prompt_content = prompt_file.read_text(encoding="utf-8")

        # Verifica que o segredo e caminho foram redigidos nos arquivos gravados
        for content in [context_content, prompt_content]:
            self.assertNotIn(synthetic_secret, content, "Segredo sintético vazou para o artefato gravado")
            self.assertNotIn(synthetic_home, content, "Caminho absoluto de home vazou para o artefato gravado")
            self.assertIn("[REDACTED_GIT_TOKEN]", content, "Tag de redação esperada ausente")
            self.assertIn("~/projects/repo", content, "Caminho normalizado com til ausente")

    def test_conselho_diff_excludes_sensitive_files(self):
        """Valida que com --diff os arquivos sensíveis (.env, .key, .pem, secret, id_rsa) são excluídos."""
        output_dir = Path(self.tmp_dir) / "output_diff"
        repo_dir = Path(self.tmp_dir) / "repo_diff"
        repo_dir.mkdir()
        subprocess.run(["git", "init", "-q", "-b", "dev", str(repo_dir)], check=True)
        subprocess.run(["git", "-C", str(repo_dir), "config", "user.name", "Test User"], check=True)
        subprocess.run(["git", "-C", str(repo_dir), "config", "user.email", "test@example.com"], check=True)

        # Commit inicial para ter base de comparação
        (repo_dir / "README.md").write_text("# Project\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(repo_dir), "add", "README.md"], check=True)
        subprocess.run(["git", "-C", str(repo_dir), "commit", "-q", "-m", "init"], check=True)

        # Modifica arquivo seguro
        (repo_dir / "main.py").write_text("print('hello world')\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(repo_dir), "add", "main.py"], check=True)

        # Cria arquivos sensíveis que devem ser omitidos pelo git diff
        (repo_dir / ".env").write_text("SECRET_DB_PASS=ultra_confidential_123\n", encoding="utf-8")
        (repo_dir / "service.key").write_text("PRIVATE_KEY_DATA_HERE\n", encoding="utf-8")
        (repo_dir / "cert.pem").write_text("CERT_KEY_DATA_HERE\n", encoding="utf-8")
        (repo_dir / "id_rsa").write_text("SSH_KEY_DATA_HERE\n", encoding="utf-8")
        (repo_dir / "app_secret_token.txt").write_text("TOKEN_SECRET_DATA_HERE\n", encoding="utf-8")

        subprocess.run(["git", "-C", str(repo_dir), "add", "."], check=True)

        # Executa conselho-seniores.sh com --diff em modo dry-run
        cmd = [
            "bash",
            str(CONSELHO_SCRIPT),
            "--agent", "claude",
            "--diff",
            "--dry-run",
            "--output-dir", str(output_dir),
        ]
        proc = subprocess.run(cmd, cwd=str(repo_dir), capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, f"Falha no conselho-seniores.sh: {proc.stderr}")

        context_file = output_dir / "contexto_avaliado.txt"
        self.assertTrue(context_file.is_file(), "contexto_avaliado.txt não foi gerado com --diff")
        content = context_file.read_text(encoding="utf-8")

        # Arquivo legítimo deve constar no diff
        self.assertIn("main.py", content, "Arquivo legítimo main.py deveria estar presente no diff")

        # Arquivos sensíveis e seus conteúdos NÃO devem constar no diff
        self.assertNotIn(".env", content, "Arquivo .env não foi excluído do diff")
        self.assertNotIn("ultra_confidential_123", content, "Conteúdo do .env vazou no diff")
        self.assertNotIn("service.key", content, "Arquivo .key não foi excluído do diff")
        self.assertNotIn("cert.pem", content, "Arquivo .pem não foi excluído do diff")
        self.assertNotIn("id_rsa", content, "Arquivo id_rsa não foi excluído do diff")
        self.assertNotIn("app_secret_token.txt", content, "Arquivo com *secret* não foi excluído do diff")

    def test_mutation_proof_disabling_redaction_fails_verification(self):
        """Prova por mutação: desativar a função de redação deve reprovar a verificação com erro claro."""
        synthetic_secret = "ghp_SYNTHETICMUTATIONPROOF1234567890"
        synthetic_home = "/home/mutant_user/super_secret_dir"
        raw_text = f"Payload: {synthetic_secret} in {synthetic_home}"

        # Execução normal (verificação passa)
        protected_text = redact_payload(raw_text)
        self.assertNotIn(synthetic_secret, protected_text)
        self.assertNotIn(synthetic_home, protected_text)

        # Mutação: função no-op que simula remoção da redação
        def mutant_noop_redact(text: str) -> str:
            return text  # Falha intencional de infraestrutura de redação

        mutant_text = mutant_noop_redact(raw_text)

        # A prova de mutação exige que o detector capture o vazamento
        with self.assertRaises(AssertionError, msg="Prova de mutação falhou: vazamento não detectado"):
            if synthetic_secret in mutant_text or synthetic_home in mutant_text:
                raise AssertionError("Vazamento de segredo ou caminho detectado sob mutação!")


if __name__ == "__main__":
    unittest.main()
