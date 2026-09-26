#!/usr/bin/env python3
"""
test_environment_tokens.py - Testes de detecção de ambiente por token explícito (PR-07)
Cobre as seções 3 e 4 do Handoff 030:
- Detecção por tokens explícitos (--env, APP_ENV, NODE_ENV, --context, etc.)
- Invariante de não rebaixamento de severidade
- Segmentação estrita em normalize_env e branch names (anti falsos-positivos delivery/evaluation)
"""

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

from ceh_core.environment import (
    detect_environment,
    normalize_env,
    ENV_SEVERITY,
)


class TestEnvironmentTokens(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="ceh-test-env-tokens-"))
        self.orig_cwd = os.getcwd()

    def tearDown(self):
        os.chdir(self.orig_cwd)
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _init_repo(self, name: str, branch: str = "main") -> Path:
        repo = self.tmp_dir / name
        repo.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "init", "-q", "-b", branch, str(repo)], check=True)
        subprocess.run(["git", "-C", str(repo), "config", "user.name", "CEH Test"], check=True)
        subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@ceh.local"], check=True)
        (repo / "README.md").write_text("initial\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(repo), "add", "README.md"], check=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "init"], check=True)
        return repo

    def test_normalize_env_segments(self):
        """Casamento por segmento estrito: delivery e evaluation deixam de casar."""
        self.assertEqual(normalize_env("production"), "production")
        self.assertEqual(normalize_env("prod"), "production")
        self.assertEqual(normalize_env("live"), "production")
        self.assertEqual(normalize_env("preprod"), "production")
        self.assertEqual(normalize_env("staging"), "staging")
        self.assertEqual(normalize_env("stage"), "staging")
        self.assertEqual(normalize_env("homolog"), "staging")
        self.assertEqual(normalize_env("homologação"), "staging")
        self.assertEqual(normalize_env("uat"), "staging")
        self.assertEqual(normalize_env("qa"), "staging")

        # Casos que antes eram falsos positivos por substring
        self.assertEqual(normalize_env("delivery"), "development")
        self.assertEqual(normalize_env("feature/evaluation"), "development")
        self.assertEqual(normalize_env("evaluation"), "development")
        self.assertEqual(normalize_env("local"), "development")

    def test_handoff_030_section_3_table_on_main(self):
        """Tabela da Seção 3.1: Comandos na main NUNCA são rebaixados."""
        repo = self._init_repo("repo_main", branch="main")

        cases = [
            ("php artisan migrate:fresh", "production", "deny"),
            ("php artisan db:wipe # staging", "production", "deny"),
            ("php artisan migrate:fresh --env=staging", "production", "deny"),
            ("terraform destroy -var env=staging", "production", "deny"),
        ]

        for cmd, expected_env, expected_decision in cases:
            env, _ = detect_environment(cmd_line=cmd, target_dir=repo)
            self.assertEqual(env, expected_env, f"Falha no ambiente para '{cmd}' na branch main")
            decision, reason, evaluated_env, use_case = safety_gate.evaluate_command(cmd, base_cwd=repo)
            self.assertEqual(decision, expected_decision, f"Falha na decisão para '{cmd}' na branch main: reason={reason}")

    def test_handoff_030_section_3_word_segments(self):
        """Seção 3.2: Casamento por segmento em branch e caminhos."""
        repo_eval = self._init_repo("repo_eval", branch="feature/evaluation")
        env_eval, _ = detect_environment(cmd_line="git reset --hard", target_dir=repo_eval)
        self.assertEqual(env_eval, "development")

        repo_dev = self._init_repo("repo_dev", branch="dev")
        # Caminho contendo production não vira produção
        env_path, _ = detect_environment(cmd_line="rm -rf build/production-assets", target_dir=repo_dev)
        self.assertEqual(env_path, "development")

        # Nome de arquivo contendo staging não vira staging
        env_compose, _ = detect_environment(cmd_line="docker compose -f docker-compose.staging.yml ps", target_dir=repo_dev)
        self.assertEqual(env_compose, "development")

    def test_handoff_030_section_4_table(self):
        """Tabela completa da Seção 4: Escalonamento estrito e não rebaixamento."""
        repo_dev = self._init_repo("r_dev", branch="dev")
        repo_main = self._init_repo("r_main", branch="main")
        repo_qa = self._init_repo("r_qa", branch="release/qa-1")

        cases = [
            (repo_dev, "APP_ENV=production php artisan migrate:fresh", "production"),
            (repo_dev, "kubectl --context prod-cluster delete pod x", "production"),
            (repo_dev, "NODE_ENV=staging npm run deploy", "staging"),
            (repo_dev, "git log --grep=production", "development"),
            (repo_dev, "cat docs/staging-notes.md", "development"),
            (repo_qa, "git reset --hard", "staging"),
            (repo_main, "APP_ENV=local git reset --hard", "production"),
            (repo_main, "env CEH_ENV=staging git reset --hard", "production"),
        ]

        for repo, cmd, expected_env in cases:
            env, _ = detect_environment(cmd_line=cmd, target_dir=repo)
            self.assertEqual(env, expected_env, f"Falha para comando '{cmd}' no repo {repo.name}")

    def test_non_downgrade_invariant(self):
        """
        Invariante 7: Sinais do comando NUNCA reduzem a severidade do ambiente.
        Para cada branch (main, release/qa-1, dev) e comandos destrutivos da bateria,
        acrescentar # staging, --env=staging ou APP_ENV=local nunca reduz a severidade.
        """
        repo_dev = self._init_repo("inv_dev", branch="dev")
        repo_qa = self._init_repo("inv_qa", branch="release/qa-1")
        repo_main = self._init_repo("inv_main", branch="main")

        destructive_commands = [
            "git reset --hard HEAD~1",
            "git clean -fdx",
            "rm -rf /",
            "php artisan migrate:fresh",
            "git push origin main --force",
        ]

        downgrade_attempts = [
            lambda c: f"{c} # staging",
            lambda c: f"{c} --env=staging",
            lambda c: f"APP_ENV=local {c}",
        ]

        repos = [repo_dev, repo_qa, repo_main]

        for repo in repos:
            for base_cmd in destructive_commands:
                base_env, _ = detect_environment(cmd_line=base_cmd, target_dir=repo)
                base_sev = ENV_SEVERITY[base_env]

                for attempt in downgrade_attempts:
                    mod_cmd = attempt(base_cmd)
                    mod_env, _ = detect_environment(cmd_line=mod_cmd, target_dir=repo)
                    mod_sev = ENV_SEVERITY[mod_env]

                    self.assertGreaterEqual(
                        mod_sev,
                        base_sev,
                        f"Violação da Invariante: '{mod_cmd}' rebaixou severidade de {base_env} ({base_sev}) para {mod_env} ({mod_sev}) no repo {repo.name}"
                    )


if __name__ == "__main__":
    unittest.main()
