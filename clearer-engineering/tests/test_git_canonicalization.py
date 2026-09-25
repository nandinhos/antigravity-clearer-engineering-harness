#!/usr/bin/env python3
"""
test_git_canonicalization.py - Bateria de testes para canonicalização do Git (PR-05: G2 + G3).
Valida:
1. G2: Descarte amplo da árvore de trabalho (git checkout . / git restore .) é destrutivo (GIT_HISTORY).
2. G2: Controles seguros de checkout de arquivo único, criação ou troca de branch permanecem liberados.
3. G3: Opções globais inócuas (-C, --no-pager, -p, etc.) são removidas na canonicalização para qualquer subcomando.
4. G3: O ambiente é detectado no repositório de destino da flag -C.
5. G3: Opções não homologadas (--git-dir, --work-tree, -c) geram fail-closed imediato.
"""
from __future__ import annotations

import os
import sys
import tempfile
import subprocess
import unittest
from pathlib import Path
from importlib import import_module

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

safety_gate = import_module("safety-gate")
evaluate_command = safety_gate.evaluate_command


class TestGitCanonicalization(unittest.TestCase):
    """Testes unitários normativos para G2 e G3."""

    # --------------------------------------------------------------------------
    # G2: Checkout e Restore com pathspec amplo são destrutivos (GIT_HISTORY)
    # --------------------------------------------------------------------------
    def test_g2_destructive_checkout_variants_in_production(self):
        destructive_cmds = [
            "git checkout .",
            "git checkout -- .",
            "git checkout HEAD -- .",
            "git checkout -f",
            "git checkout :/",
            "git checkout -- '*'",
        ]
        for cmd in destructive_cmds:
            decision, reason, env, use_case = evaluate_command(cmd, explicit_env="production")
            self.assertEqual(decision, "deny", f"Esperado 'deny' para '{cmd}', obtido '{decision}'")
            self.assertEqual(use_case, "GIT_HISTORY", f"Esperado 'GIT_HISTORY' para '{cmd}', obtido '{use_case}'")

    def test_g2_destructive_restore_variants_in_production(self):
        destructive_cmds = [
            "git restore .",
            "git restore --staged --worktree .",
            "git restore --source=HEAD .",
            "git restore :/",
            "git restore -- .",
        ]
        for cmd in destructive_cmds:
            decision, reason, env, use_case = evaluate_command(cmd, explicit_env="production")
            self.assertEqual(decision, "deny", f"Esperado 'deny' para '{cmd}', obtido '{decision}'")
            self.assertEqual(use_case, "GIT_HISTORY", f"Esperado 'GIT_HISTORY' para '{cmd}', obtido '{use_case}'")

    def test_g2_destructive_checkout_in_staging_requires_alerts(self):
        decision, reason, env, use_case = evaluate_command("git checkout .", explicit_env="staging")
        self.assertEqual(decision, "ask")
        self.assertEqual(use_case, "GIT_HISTORY")
        self.assertIn("ALERTA 1/2", reason)
        self.assertIn("ALERTA 2/2", reason)

    def test_g2_destructive_checkout_in_development_permitted(self):
        decision, reason, env, use_case = evaluate_command("git checkout .", explicit_env="development")
        self.assertEqual(decision, "allow")
        self.assertEqual(use_case, "GIT_HISTORY")

    # --------------------------------------------------------------------------
    # G2: Controles seguros de checkout e restore permanecem liberados
    # --------------------------------------------------------------------------
    def test_g2_safe_controls_permitted_in_all_environments(self):
        safe_cmds = [
            "git checkout app/Model.php",
            "git checkout dev",
            "git checkout -b feature/new-flow",
            "git checkout main",
            "git restore --staged app/Model.php",
            "git restore app/Services/PaymentService.php",
        ]
        for cmd in safe_cmds:
            for env in ["development", "staging", "production"]:
                decision, reason, _, use_case = evaluate_command(cmd, explicit_env=env)
                self.assertEqual(decision, "allow", f"Controle '{cmd}' em '{env}' deve ser allow, obtido '{decision}'")

    # --------------------------------------------------------------------------
    # G3: Opções globais inócuas canonicalizadas em qualquer subcomando
    # --------------------------------------------------------------------------
    def test_g3_innocuous_options_canonicalized(self):
        test_cases = [
            ("git -C . reset --hard", "deny", "GIT_HISTORY"),
            ("git --no-pager reset --hard", "deny", "GIT_HISTORY"),
            ("git -p reset --hard", "deny", "GIT_HISTORY"),
            ("git --paginate reset --hard", "deny", "GIT_HISTORY"),
            ("git --no-replace-objects reset --hard", "deny", "GIT_HISTORY"),
            ("git --literal-pathspecs reset --hard", "deny", "GIT_HISTORY"),
            ("git --no-pager status", "allow", "GENERAL"),
        ]
        for cmd, expected_decision, expected_use_case in test_cases:
            decision, reason, env, use_case = evaluate_command(cmd, explicit_env="production")
            self.assertEqual(decision, expected_decision, f"Comando '{cmd}' falhou: {reason}")
            self.assertEqual(use_case, expected_use_case, f"Comando '{cmd}' obteve use_case incorreto")

    # --------------------------------------------------------------------------
    # G3: Detecção de ambiente no repositório de destino da flag -C
    # --------------------------------------------------------------------------
    def test_g3_environment_detected_from_target_repo_in_dash_C(self):
        tmp_dir = tempfile.mkdtemp(prefix="ceh_test_c_env_")
        orig_cwd = os.getcwd()
        try:
            # Cria repositório fixture em branch 'main' (produção)
            subprocess.run(["git", "init", "-b", "main"], cwd=tmp_dir, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Tester"], cwd=tmp_dir, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.local"], cwd=tmp_dir, check=True, capture_output=True)
            (Path(tmp_dir) / "f.txt").write_text("hello\n")
            subprocess.run(["git", "add", "."], cwd=tmp_dir, check=True, capture_output=True)
            subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_dir, check=True, capture_output=True)

            # CWD de execução é neutro/dev, mas o comando aponta -C para o repo na main
            cmd = f"git -C {tmp_dir} reset --hard"
            # Sem explicit_env: detecta a partir do repositório em tmp_dir (main -> production)
            decision, reason, env, use_case = evaluate_command(cmd, explicit_env=None)
            self.assertEqual(env, "production", f"Esperado ambiente 'production' detectado em -C, mas obteve '{env}'")
            self.assertEqual(decision, "deny", f"Esperado bloqueio de produção em -C repo na main, mas obteve '{decision}'")
            self.assertEqual(use_case, "GIT_HISTORY")
        finally:
            os.chdir(orig_cwd)
            subprocess.run(["rm", "-rf", tmp_dir], capture_output=True)

    # --------------------------------------------------------------------------
    # G3: Opções globais não homologadas geram Fail-Closed imediato
    # --------------------------------------------------------------------------
    def test_g3_unhomologated_options_fail_closed(self):
        fail_closed_cmds = [
            "git --git-dir=/etc reset --hard",
            "git --work-tree=/var status",
            "git -c user.name=hacker commit",
        ]
        for cmd in fail_closed_cmds:
            decision, reason, env, use_case = evaluate_command(cmd, explicit_env="development")
            self.assertEqual(decision, "deny", f"Esperado fail-closed (deny) para '{cmd}'")
            self.assertIn("Opção global do Git não homologada", reason)


if __name__ == "__main__":
    unittest.main()
