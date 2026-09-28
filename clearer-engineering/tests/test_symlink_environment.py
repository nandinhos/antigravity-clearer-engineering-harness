#!/usr/bin/env python3
"""
test_symlink_environment.py - Prova hermética e determinística de D04.

Demonstra conjuntamente:
(a) Classificação de ambiente em ancestral físico acessado por symlink;
(b) Ancoragem de repositório Git e branch através de symlink;
(c) Efeito de proteção em comandos 'rm' pelo Safety Gate sem deleção real;
(d) Preservação da normalização lexical para caminhos puramente sintéticos.
"""
from __future__ import annotations
import os
import sys
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from ceh_core.environment import (
    clear_environment_caches,
    detect_environment,
    find_repo_root,
    get_git_branch,
)
from ceh_core.rm import evaluate_rm_command, is_target_catastrophic, is_target_safe
from ceh_core.normalize import normalize_path


class TestSymlinkEnvironmentD04(unittest.TestCase):
    def setUp(self) -> None:
        clear_environment_caches()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base = Path(self.temp_dir.name).resolve()

        # Cria estrutura real do repositório
        self.real_root = self.base / "real_production_repo"
        self.real_root.mkdir(parents=True, exist_ok=True)
        self.subapp = self.real_root / "services" / "api"
        self.subapp.mkdir(parents=True, exist_ok=True)

        # Configura ambiente de produção no ancestral físico
        self.prod_env_file = self.real_root / ".env.production"
        self.prod_env_file.write_text("APP_ENV=production\n", encoding="utf-8")

        # Cria diretório externo com symlink apontando para o subapp
        self.external_dir = self.base / "workspace_links"
        self.external_dir.mkdir(parents=True, exist_ok=True)
        self.symlink_dir = self.external_dir / "linked_api"
        self.symlink_dir.symlink_to(self.subapp, target_is_directory=True)

    def tearDown(self) -> None:
        clear_environment_caches()
        self.temp_dir.cleanup()

    def test_a_environment_detection_through_symlink_physical_ancestor(self) -> None:
        """(a) O ambiente é classificado como 'production' ao inspecionar o ancestral físico do symlink."""
        old_env = {}
        for var in ["CEH_ENV", "APP_ENV", "NODE_ENV", "ENVIRONMENT", "ENV", "STAGE"]:
            if var in os.environ:
                old_env[var] = os.environ.pop(var)

        try:
            env, evidence = detect_environment(target_dir=str(self.symlink_dir))
            self.assertEqual(env, "production")
            self.assertIn(".env.production", evidence)
            self.assertTrue(Path(evidence.split("Configuration file ")[-1]).is_file())
        finally:
            os.environ.update(old_env)

    def test_b_git_repo_and_branch_resolution_through_symlink(self) -> None:
        """(b) Identificação de raiz de repositório Git e branch corrente através de symlink."""
        subprocess.run(
            ["git", "init", "-b", "main"],
            cwd=self.real_root,
            capture_output=True,
            check=True,
        )

        clear_environment_caches()

        repo_root = find_repo_root(self.symlink_dir)
        self.assertIsNotNone(repo_root)
        self.assertEqual(repo_root.resolve(), self.real_root.resolve())

        branch = get_git_branch(self.symlink_dir)
        self.assertEqual(branch, "main")

    def test_c_safety_gate_rm_evaluation_under_symlink_context(self) -> None:
        """(c) O Safety Gate bloqueia 'rm -rf' em produção sob o symlink sem executar exclusão."""
        old_env = {}
        for var in ["CEH_ENV", "APP_ENV", "NODE_ENV", "ENVIRONMENT", "ENV", "STAGE"]:
            if var in os.environ:
                old_env[var] = os.environ.pop(var)

        try:
            env, evidence = detect_environment(target_dir=str(self.symlink_dir))
            self.assertEqual(env, "production")

            res = evaluate_rm_command(
                "rm -rf config/",
                env=env,
                env_evidence=evidence,
                base_cwd=self.symlink_dir,
            )
            self.assertIsNotNone(res)
            decision, reason, evaluated_env, severity = res
            self.assertEqual(decision, "deny")
            self.assertEqual(evaluated_env, "production")
            self.assertEqual(severity, "FILESYSTEM")
            self.assertIn("[CEH PRODUCTION LOCK]", reason)

            cat_symlink = self.subapp / "link_to_parent"
            cat_symlink.symlink_to(self.real_root, target_is_directory=True)

            is_cat, cat_desc = is_target_catastrophic("link_to_parent", str(self.subapp))
            self.assertTrue(is_cat)
            self.assertIn("protected directory", cat_desc)

            escape_link = self.subapp / "scratch_link"
            escape_link.symlink_to(self.base, target_is_directory=True)
            self.assertFalse(is_target_safe("scratch_link", is_force=True, cwd=self.subapp))

        finally:
            os.environ.update(old_env)

    def test_d_synthetic_paths_preservation(self) -> None:
        """(d) Caminhos sintéticos que não existem em disco continuam sendo normalizados lexicalmente."""
        synthetic_path = "/nonexistent/fake/dev/workspace/app"
        self.assertFalse(Path(synthetic_path).exists())

        env, evidence = detect_environment(target_dir=synthetic_path)
        self.assertEqual(env, "development")

        norm = normalize_path(synthetic_path, resolve_home=False)
        self.assertEqual(norm, synthetic_path)

        is_cat, _ = is_target_catastrophic("..", "/fake/a/b/c")
        self.assertTrue(is_cat)


if __name__ == "__main__":
    unittest.main()
