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


    # --------------------------------------------------------------------------
    # U1 (PR-05b): Pathspec ./ e variantes são amplos / destrutivos
    # --------------------------------------------------------------------------
    def test_u1_checkout_restore_dot_slash_pathspec(self):
        u1_destructive = [
            "git checkout -- ./",
            "git checkout ./",
            "git checkout .//",
            "git checkout .//.",
            "git restore ./",
            "git restore -- ./",
        ]
        for cmd in u1_destructive:
            decision, reason, env, use_case = evaluate_command(cmd, explicit_env="production")
            self.assertEqual(decision, "deny", f"Esperado deny para '{cmd}', obteve '{decision}' ({use_case})")
            self.assertEqual(use_case, "GIT_HISTORY")

    # --------------------------------------------------------------------------
    # U2 (PR-05b): Opção global -P (--no-pager) inócua
    # --------------------------------------------------------------------------
    def test_u2_dash_p_innocuous_flag(self):
        u2_cases = [
            ("git -P diff", "allow", "GENERAL"),
            ("git -P log -5", "allow", "GENERAL"),
            ("git -P reset --hard", "deny", "GIT_HISTORY"),
        ]
        for cmd, exp_dec, exp_uc in u2_cases:
            decision, reason, env, use_case = evaluate_command(cmd, explicit_env="production")
            self.assertEqual(decision, exp_dec, f"Comando '{cmd}' falhou: {reason}")
            self.assertEqual(use_case, exp_uc)

    # --------------------------------------------------------------------------
    # U3 (PR-05b): Git switch com flags destrutivas (-f, --force, --discard-changes)
    # --------------------------------------------------------------------------
    def test_u3_git_switch_destructive(self):
        destructive = [
            "git switch -f main",
            "git switch --force main",
            "git switch --discard-changes main",
        ]
        for cmd in destructive:
            decision, reason, env, use_case = evaluate_command(cmd, explicit_env="production")
            self.assertEqual(decision, "deny", f"Esperado deny para '{cmd}', obteve '{decision}'")
            self.assertEqual(use_case, "GIT_HISTORY")

        controls = [
            "git switch main",
            "git switch -c feature",
            "git switch -b feature",
            "git switch --create feature",
        ]
        for cmd in controls:
            decision, reason, env, use_case = evaluate_command(cmd, explicit_env="production")
            self.assertEqual(decision, "allow", f"Esperado allow para '{cmd}', obteve '{decision}'")


    # --------------------------------------------------------------------------
    # V1 (PR-05c): Pathspecs relativos/mágicos amplos
    # --------------------------------------------------------------------------
    def test_v1_broad_relative_and_magic_pathspecs(self):
        v1_destructive = [
            "git checkout HEAD src/..",
            "git checkout app/..",
            "git restore -s HEAD src/..",
            "git restore -s HEAD app/..",
            "git checkout ':(top)'",
            "git checkout ':(top).'",
            "git checkout ':!x'",
            "git checkout ':^x'",
            "git checkout ':(exclude)x'",
            "git checkout ':/app/../..'",
            "git restore ':/app/../..'",
        ]
        for cmd in v1_destructive:
            decision, reason, env, use_case = evaluate_command(cmd, explicit_env="production")
            self.assertEqual(decision, "deny", f"Esperado 'deny' para '{cmd}', obtido '{decision}' ({reason})")
            self.assertEqual(use_case, "GIT_HISTORY")

    # --------------------------------------------------------------------------
    # V2 (PR-05c): Redefinição forçada de branch (-C e -B)
    # --------------------------------------------------------------------------
    def test_v2_forced_branch_reset_switch_and_checkout(self):
        v2_cases = [
            "git switch -C main",
            "git switch -C feature-x origin/main",
            "git checkout -B main",
            "git checkout -B release/1.0",
        ]
        for cmd in v2_cases:
            dec_prod, _, _, uc_prod = evaluate_command(cmd, explicit_env="production")
            self.assertEqual(dec_prod, "deny", f"Esperado deny em PROD para '{cmd}', obteve '{dec_prod}'")
            self.assertEqual(uc_prod, "GIT_HISTORY")

            dec_sta, reason_sta, _, _ = evaluate_command(cmd, explicit_env="staging")
            self.assertEqual(dec_sta, "ask", f"Esperado ask em STA para '{cmd}', obteve '{dec_sta}'")
            self.assertIn("ALERTA 1/2", reason_sta)
            self.assertIn("ALERTA 2/2", reason_sta)

            dec_dev, _, _, _ = evaluate_command(cmd, explicit_env="development")
            self.assertEqual(dec_dev, "allow", f"Esperado allow em DEV para '{cmd}', obteve '{dec_dev}'")

    # --------------------------------------------------------------------------
    # V3 (PR-05c): git restore --staged isolado vs com --worktree
    # --------------------------------------------------------------------------
    def test_v3_restore_staged_isolated_vs_with_worktree(self):
        # --staged isolado altera apenas o index (não descarta worktree) -> allow
        staged_safe = [
            "git restore --staged .",
            "git restore -S .",
            "git restore --staged :/",
            "git restore --staged src/..",
        ]
        for cmd in staged_safe:
            for env in ["development", "staging", "production"]:
                decision, reason, _, use_case = evaluate_command(cmd, explicit_env=env)
                self.assertEqual(decision, "allow", f"Esperado allow para '{cmd}' em '{env}', obteve '{decision}'")
                self.assertEqual(use_case, "FILESYSTEM_SAFE")

        # Com --worktree / -W presente e pathspec amplo -> deny em PROD
        staged_with_worktree = [
            "git restore --staged --worktree .",
            "git restore -S -W .",
            "git restore -W -S .",
            "git restore --worktree --staged :/",
        ]
        for cmd in staged_with_worktree:
            decision, reason, _, use_case = evaluate_command(cmd, explicit_env="production")
            self.assertEqual(decision, "deny", f"Esperado deny para '{cmd}' com worktree, obteve '{decision}'")
            self.assertEqual(use_case, "GIT_HISTORY")

    # --------------------------------------------------------------------------
    # V4 (PR-05c): Falso positivo de nomes com hífen
    # --------------------------------------------------------------------------
    def test_v4_hyphenated_names_not_confused_with_flags(self):
        v4_controls = [
            "git checkout feature/add-pdf",
            "git checkout fix-leaf",
            "git checkout -b fix-leaf",
            "git switch hotfix-ref",
            "git switch -c hotfix-ref",
            "git checkout -- app/self-ref",
            "git checkout app/self-ref",
        ]
        for cmd in v4_controls:
            for env in ["development", "staging", "production"]:
                decision, reason, _, use_case = evaluate_command(cmd, explicit_env=env)
                self.assertEqual(decision, "allow", f"Esperado allow para '{cmd}' em '{env}', obteve '{decision}'")

    # --------------------------------------------------------------------------
    # V5 (PR-05c): Pathspec opaco (--pathspec-from-file) fail-closed
    # --------------------------------------------------------------------------
    def test_v5_opaque_pathspec_fail_closed(self):
        v5_cases = [
            "git restore --pathspec-from-file=list.txt",
            "git restore --pathspec-from-file=-",
            "git restore --pathspec-file-nul",
            "git checkout --pathspec-from-file=list.txt",
        ]
        for cmd in v5_cases:
            decision, reason, _, use_case = evaluate_command(cmd, explicit_env="production")
            self.assertEqual(decision, "deny", f"Esperado deny para '{cmd}', obteve '{decision}' ({reason})")
            self.assertEqual(use_case, "GIT_HISTORY")


    # --------------------------------------------------------------------------
    # W1 (PR-05d): Avaliação de todos os posicionais em checkout
    # --------------------------------------------------------------------------
    def test_w1_all_positionals_evaluated_in_checkout(self):
        w1_destructive = [
            "git checkout . app/x",
            "git checkout src/.. app/x",
            "git checkout app/x .",
            "git checkout ./src/.. app/Model.php",
        ]
        for cmd in w1_destructive:
            decision, reason, _, use_case = evaluate_command(cmd, explicit_env="production")
            self.assertEqual(decision, "deny", f"Esperado deny para '{cmd}', obteve '{decision}'")
            self.assertEqual(use_case, "GIT_HISTORY")

        w1_controls = [
            "git checkout main app/x",
            "git checkout dev config/app.php",
        ]
        for cmd in w1_controls:
            for env in ["development", "staging", "production"]:
                decision, _, _, _ = evaluate_command(cmd, explicit_env=env)
                self.assertEqual(decision, "allow", f"Esperado allow para '{cmd}' em '{env}', obteve '{decision}'")

    # --------------------------------------------------------------------------
    # W2 (PR-05d): Abreviações de opções longas (prefixos únicos)
    # --------------------------------------------------------------------------
    def test_w2_long_option_abbreviations(self):
        w2_destructive = [
            "git checkout --forc main",
            "git switch --discard main",
            "git switch --force-c main",
            "git switch --discard-c main",
            "git restore --staged --work .",
            "git restore --pathspec-from=list.txt",
            "git restore --stag --work .",
        ]
        for cmd in w2_destructive:
            decision, reason, _, use_case = evaluate_command(cmd, explicit_env="production")
            self.assertEqual(decision, "deny", f"Esperado deny para '{cmd}', obteve '{decision}'")
            self.assertEqual(use_case, "GIT_HISTORY")

        w2_controls = [
            "git checkout --quiet main",
            "git switch --detach HEAD~1",
            "git switch --guess main",
        ]
        for cmd in w2_controls:
            for env in ["development", "staging", "production"]:
                decision, _, _, _ = evaluate_command(cmd, explicit_env=env)
                self.assertEqual(decision, "allow", f"Esperado allow para '{cmd}' em '{env}', obteve '{decision}'")

    # --------------------------------------------------------------------------
    # W3 (PR-05d): Glob no primeiro segmento alcança o repositório inteiro
    # --------------------------------------------------------------------------
    def test_w3_first_segment_glob_broad(self):
        w3_destructive = [
            "git checkout -- '*.php'",
            "git restore '*.php'",
            "git checkout -- ./*",
            "git checkout -- '**'",
            "git restore -- '[a-z]*'",
            "git checkout -- '?*.js'",
        ]
        for cmd in w3_destructive:
            decision, reason, _, use_case = evaluate_command(cmd, explicit_env="production")
            self.assertEqual(decision, "deny", f"Esperado deny para '{cmd}', obteve '{decision}'")
            self.assertEqual(use_case, "GIT_HISTORY")

        w3_controls = [
            "git checkout -- src/*",
            "git checkout -- 'src/*.php'",
            "git checkout -- tests/*",
        ]
        for cmd in w3_controls:
            for env in ["development", "staging", "production"]:
                decision, _, _, _ = evaluate_command(cmd, explicit_env=env)
                self.assertEqual(decision, "allow", f"Esperado allow para '{cmd}' em '{env}', obteve '{decision}'")

    # --------------------------------------------------------------------------
    # W4 (PR-05d): Variável ($) ou til (~) no pathspec é incerteza (amplo)
    # --------------------------------------------------------------------------
    def test_w4_variable_or_tilde_pathspec(self):
        w4_destructive = [
            "git checkout -- \"$PWD\"",
            "git restore $DIR",
            "git checkout -- ~",
            "git checkout -- ~/projects/repo",
        ]
        for cmd in w4_destructive:
            decision, reason, _, use_case = evaluate_command(cmd, explicit_env="production")
            self.assertEqual(decision, "deny", f"Esperado deny para '{cmd}', obteve '{decision}'")
            self.assertEqual(use_case, "GIT_HISTORY")


if __name__ == "__main__":
    unittest.main()
