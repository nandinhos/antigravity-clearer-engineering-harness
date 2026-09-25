#!/usr/bin/env python3
"""
test_rm_targets.py - Bateria de testes de alvos do comando 'rm' (PR-04b).
Valida:
1. R1: Ausência de falsos positivos em DEV (caminhos absolutos legítimos sob /home, /opt, /var, /usr são permitidos).
2. R2: Fechamento de bypasses de raiz e ancestrais (//, /./, ../.., ./*, ~root são negados como CATASTROPHIC).
3. R3: O motivo do atalho seguro em produção reflete a evidência real e NÃO contém '--env development'.
4. G1 + G4: Alvos mistos e limpezas legítimas preservadas.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from importlib import import_module

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

safety_gate = import_module("safety-gate")
evaluate_command = safety_gate.evaluate_command


class TestRmTargets(unittest.TestCase):
    """Bateria de testes de precisão para análise e normalização de alvos de rm."""

    # --------------------------------------------------------------------------
    # R1: Controles de Falsos Positivos em DEV
    # Caminhos absolutos dentro de /home, /opt, /var ou /usr NÃO são catastróficos
    # --------------------------------------------------------------------------
    def test_r1_dev_absolute_path_home_build_allowed(self):
        """R1: rm -rf /home/user/projeto/build em DEV deve ser permitido (não catastrófico)"""
        decision, reason, env, use_case = evaluate_command("rm -rf /home/user/projeto/build", explicit_env="development")
        self.assertEqual(decision, "allow")
        self.assertNotEqual(use_case, "CATASTROPHIC")

    def test_r1_dev_absolute_path_home_src_allowed(self):
        """R1: rm -rf /home/user/projeto/src/old em DEV deve ser permitido"""
        decision, reason, env, use_case = evaluate_command("rm -rf /home/user/projeto/src/old", explicit_env="development")
        self.assertEqual(decision, "allow")
        self.assertNotEqual(use_case, "CATASTROPHIC")

    def test_r1_dev_absolute_path_opt_myapp_cache_allowed(self):
        """R1: rm -rf /opt/myapp/cache em DEV deve ser permitido"""
        decision, reason, env, use_case = evaluate_command("rm -rf /opt/myapp/cache", explicit_env="development")
        self.assertEqual(decision, "allow")
        self.assertNotEqual(use_case, "CATASTROPHIC")

    def test_r1_dev_absolute_path_var_tmp_allowed(self):
        """R1: rm -rf /var/tmp/ceh-x em DEV deve ser permitido"""
        decision, reason, env, use_case = evaluate_command("rm -rf /var/tmp/ceh-x", explicit_env="development")
        self.assertEqual(decision, "allow")
        self.assertNotEqual(use_case, "CATASTROPHIC")

    def test_r1_dev_absolute_path_usr_local_lib_allowed(self):
        """R1: rm -rf /usr/local/lib/node_modules/foo em DEV deve ser permitido"""
        decision, reason, env, use_case = evaluate_command("rm -rf /usr/local/lib/node_modules/foo", explicit_env="development")
        self.assertEqual(decision, "allow")
        self.assertNotEqual(use_case, "CATASTROPHIC")

    # --------------------------------------------------------------------------
    # R2: Fechamento de Bypasses de Raiz e Ancestrais (Normalização)
    # Variantes como //, /./, ../.., ./* e ~root devem ser bloqueadas incondicionalmente
    # --------------------------------------------------------------------------
    def test_r2_bypass_double_slash_root(self):
        """R2: rm -rf // em DEV deve ser bloqueado como CATASTROPHIC"""
        decision, reason, env, use_case = evaluate_command("rm -rf //", explicit_env="development")
        self.assertEqual(decision, "deny")
        self.assertEqual(use_case, "CATASTROPHIC")
        self.assertIn("Attempting recursive deletion of root directory '/'", reason)

    def test_r2_bypass_slash_dot_slash_root(self):
        """R2: rm -rf /./ em DEV deve ser bloqueado como CATASTROPHIC"""
        decision, reason, env, use_case = evaluate_command("rm -rf /./", explicit_env="development")
        self.assertEqual(decision, "deny")
        self.assertEqual(use_case, "CATASTROPHIC")
        self.assertIn("Attempting recursive deletion of root directory '/'", reason)

    def test_r2_bypass_parent_of_parent(self):
        """R2: rm -rf ../.. em DEV deve ser bloqueado como CATASTROPHIC"""
        decision, reason, env, use_case = evaluate_command("rm -rf ../..", explicit_env="development")
        self.assertEqual(decision, "deny")
        self.assertEqual(use_case, "CATASTROPHIC")

    def test_r2_bypass_dot_slash_wildcard(self):
        """R2: rm -rf ./* em DEV deve ser bloqueado como CATASTROPHIC"""
        decision, reason, env, use_case = evaluate_command("rm -rf ./*", explicit_env="development")
        self.assertEqual(decision, "deny")
        self.assertEqual(use_case, "CATASTROPHIC")
        self.assertIn("Attempting recursive deletion of wildcard '*'", reason)

    def test_r2_bypass_tilde_root(self):
        """R2: rm -rf ~root em DEV deve ser bloqueado como CATASTROPHIC"""
        decision, reason, env, use_case = evaluate_command("rm -rf ~root", explicit_env="development")
        self.assertEqual(decision, "deny")
        self.assertEqual(use_case, "CATASTROPHIC")

    # --------------------------------------------------------------------------
    # R3: Integridade da Evidência de Ambiente no Motivo
    # O motivo em produção deve refletir a evidência real e NÃO conter '--env development'
    # --------------------------------------------------------------------------
    def test_r3_production_safe_reason_does_not_contain_env_development(self):
        """R3: Motivo de atalho de limpeza segura em produção não deve conter '--env development'"""
        decision, reason, env, use_case = evaluate_command("rm -rf dist/", explicit_env="production")
        self.assertEqual(decision, "allow")
        self.assertEqual(use_case, "FILESYSTEM_SAFE")
        self.assertNotIn("--env development", reason, "Motivo não deve citar '--env development' em produção")
        self.assertIn("Safe development operation permitted", reason)

    # --------------------------------------------------------------------------
    # Casos de Controle e Regras do Handoff 014
    # --------------------------------------------------------------------------
    def test_control_cmd095_subpath_behavior_per_environment(self):
        """CMD-095: rm -rf a.txt /var/lib/postgresql retorna FILESYSTEM (dev: allow, sta: ask, pro: deny)"""
        # DEV: allow
        dec_dev, _, _, uc_dev = evaluate_command("rm -rf a.txt /var/lib/postgresql", explicit_env="development")
        self.assertEqual(dec_dev, "allow")
        self.assertEqual(uc_dev, "FILESYSTEM")

        # STA: ask
        dec_sta, _, _, uc_sta = evaluate_command("rm -rf a.txt /var/lib/postgresql", explicit_env="staging")
        self.assertEqual(dec_sta, "ask")
        self.assertEqual(uc_sta, "FILESYSTEM")

        # PRO: deny
        dec_pro, _, _, uc_pro = evaluate_command("rm -rf a.txt /var/lib/postgresql", explicit_env="production")
        self.assertEqual(dec_pro, "deny")
        self.assertEqual(uc_pro, "FILESYSTEM")


if __name__ == "__main__":
    unittest.main()
