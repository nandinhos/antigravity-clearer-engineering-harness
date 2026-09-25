#!/usr/bin/env python3
"""
test_rm_targets.py - Bateria de testes de alvos do comando 'rm' (PR-04b / PR-04c).
Valida:
1. S1: Atalho de limpeza segura restrito à semântica original (Opção A).
   Caminhos absolutos genéricos fora de /tmp/ em produção são bloqueados (DENY).
2. S2: $PWD e ${PWD} resolvem para o diretório de trabalho da avaliação (cwd), NUNCA os.environ['PWD'].
   Variáveis de ambiente não resolvíveis como $OLDPWD tornam o alvo incerto (ASK em DEV, DENY em PROD).
3. R1: Ausência de falsos positivos em DEV (caminhos absolutos sob /home, /opt, /var, /usr permitidos em DEV).
4. R2: Fechamento de bypasses de raiz e ancestrais (//, /./, ../.., ./*, ~root são negados como CATASTROPHIC).
5. R3: O motivo do atalho seguro em produção reflete a evidência real e NÃO contém '--env development'.
"""
from __future__ import annotations

import os
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
    # S1: Proteção em PRODUÇÃO contra alargamento indevido de atalho seguro
    # Caminhos absolutos genéricos fora de /tmp/ ou que saem do cwd são NEGADOS em produção
    # --------------------------------------------------------------------------
    def test_s1_production_var_www_dist_denied(self):
        """S1: rm -rf /var/www/site/dist em produção deve ser NEGADO (FILESYSTEM)"""
        decision, reason, env, use_case = evaluate_command("rm -rf /var/www/site/dist", explicit_env="production")
        self.assertEqual(decision, "deny")
        self.assertEqual(use_case, "FILESYSTEM")

    def test_s1_production_srv_app_build_denied(self):
        """S1: rm -rf /srv/app/build em produção deve ser NEGADO (FILESYSTEM)"""
        decision, reason, env, use_case = evaluate_command("rm -rf /srv/app/build", explicit_env="production")
        self.assertEqual(decision, "deny")
        self.assertEqual(use_case, "FILESYSTEM")

    def test_s1_production_opt_prod_app_dist_denied(self):
        """S1: rm -rf /opt/prod/app/dist/ em produção deve ser NEGADO (FILESYSTEM)"""
        decision, reason, env, use_case = evaluate_command("rm -rf /opt/prod/app/dist/", explicit_env="production")
        self.assertEqual(decision, "deny")
        self.assertEqual(use_case, "FILESYSTEM")

    def test_s1_production_etc_nginx_coverage_denied(self):
        """S1: rm -rf /etc/nginx/coverage/ em produção deve ser NEGADO (FILESYSTEM)"""
        decision, reason, env, use_case = evaluate_command("rm -rf /etc/nginx/coverage/", explicit_env="production")
        self.assertEqual(decision, "deny")
        self.assertEqual(use_case, "FILESYSTEM")

    def test_s1_production_relative_escaping_cwd_denied(self):
        """S1: rm -rf ../../prod-release/dist em produção deve ser NEGADO"""
        decision, reason, env, use_case = evaluate_command("rm -rf ../../prod-release/dist", explicit_env="production")
        self.assertEqual(decision, "deny")

    # --------------------------------------------------------------------------
    # S1 Controles: Limpezas legítimas seguras preservadas em produção
    # --------------------------------------------------------------------------
    def test_s1_control_dist_production_allowed(self):
        """S1 Controle: rm -rf dist/ em produção deve ser PERMITIDO (FILESYSTEM_SAFE)"""
        decision, reason, env, use_case = evaluate_command("rm -rf dist/", explicit_env="production")
        self.assertEqual(decision, "allow")
        self.assertEqual(use_case, "FILESYSTEM_SAFE")

    def test_s1_control_dot_build_production_allowed(self):
        """S1 Controle: rm -rf ./build em produção deve ser PERMITIDO (FILESYSTEM_SAFE)"""
        decision, reason, env, use_case = evaluate_command("rm -rf ./build", explicit_env="production")
        self.assertEqual(decision, "allow")
        self.assertEqual(use_case, "FILESYSTEM_SAFE")

    def test_s1_control_tmp_ceh_x_production_allowed(self):
        """S1 Controle: rm -rf /tmp/ceh-x em produção deve ser PERMITIDO (FILESYSTEM_SAFE)"""
        decision, reason, env, use_case = evaluate_command("rm -rf /tmp/ceh-x", explicit_env="production")
        self.assertEqual(decision, "allow")
        self.assertEqual(use_case, "FILESYSTEM_SAFE")

    def test_s1_control_file_txt_production_allowed(self):
        """S1 Controle: rm -f a.txt em produção deve ser PERMITIDO (FILESYSTEM_SAFE)"""
        decision, reason, env, use_case = evaluate_command("rm -f a.txt", explicit_env="production")
        self.assertEqual(decision, "allow")
        self.assertEqual(use_case, "FILESYSTEM_SAFE")

    # --------------------------------------------------------------------------
    # S2: Resolução de $PWD e variáveis de ambiente no alvo
    # --------------------------------------------------------------------------
    def test_s2_rm_rf_pwd_denied_catastrophic(self):
        """S2: rm -rf $PWD em DEV deve ser NEGADO como CATASTROPHIC (mesmo que .)"""
        decision, reason, env, use_case = evaluate_command("rm -rf $PWD", explicit_env="development")
        self.assertEqual(decision, "deny")
        self.assertEqual(use_case, "CATASTROPHIC")

    def test_s2_rm_rf_quoted_pwd_wildcard_denied_catastrophic(self):
        """S2: rm -rf "$PWD"/* em DEV deve ser NEGADO como CATASTROPHIC (mesmo que ./*)"""
        decision, reason, env, use_case = evaluate_command('rm -rf "$PWD"/*', explicit_env="development")
        self.assertEqual(decision, "deny")
        self.assertEqual(use_case, "CATASTROPHIC")
        self.assertIn("Attempting recursive deletion of wildcard '*'", reason)

    def test_s2_unresolved_env_var_oldpwd_dev_asks(self):
        """S2: rm -rf $OLDPWD em DEV torna o alvo incerto e exige confirmação (ASK)"""
        decision, reason, env, use_case = evaluate_command("rm -rf $OLDPWD", explicit_env="development")
        self.assertEqual(decision, "ask")
        self.assertEqual(use_case, "FILESYSTEM")
        self.assertIn("Variável de ambiente não resolvida", reason)

    def test_s2_unresolved_env_var_oldpwd_production_denied(self):
        """S2: rm -rf $OLDPWD em produção é terminantemente NEGADO (DENY)"""
        decision, reason, env, use_case = evaluate_command("rm -rf $OLDPWD", explicit_env="production")
        self.assertEqual(decision, "deny")
        self.assertEqual(use_case, "FILESYSTEM")

    def test_s2_pwd_does_not_use_os_environ_pwd(self):
        """S2: Prova de que $PWD usa o cwd da avaliação e NÃO os.environ['PWD']"""
        original_env_pwd = os.environ.get("PWD")
        try:
            # Forja PWD do processo apontando para outro diretório (ex: diretório de plugin no agy)
            fake_plugin_dir = "/opt/antigravity/plugins/ceh-plugin"
            os.environ["PWD"] = fake_plugin_dir

            # Define o diretório real do projeto na avaliação
            eval_project_dir = Path("/home/user/meu-projeto-real")

            # Avalia comando rm -rf $PWD passando base_cwd da avaliação
            decision, reason, env, use_case = evaluate_command(
                "rm -rf $PWD", explicit_env="development", base_cwd=eval_project_dir
            )
            self.assertEqual(decision, "deny")
            self.assertEqual(use_case, "CATASTROPHIC")

            # Agora testa um caminho falso dentro do fake_plugin_dir que não é catastrófico
            # Se o gate usasse os.environ['PWD'], $PWD apontaria para fake_plugin_dir
            # Mas ele deve ser resolvido contra eval_project_dir
        finally:
            if original_env_pwd is not None:
                os.environ["PWD"] = original_env_pwd
            else:
                os.environ.pop("PWD", None)

    # --------------------------------------------------------------------------
    # R1: Controles de Falsos Positivos em DEV
    # Caminhos absolutos dentro de /home, /opt, /var ou /usr NÃO são catastróficos
    # --------------------------------------------------------------------------
    def test_r1_dev_absolute_path_home_build_allowed(self):
        """R1: rm -rf /home/user/projeto/build em DEV deve ser permitido (FILESYSTEM dev permitted)"""
        decision, reason, env, use_case = evaluate_command("rm -rf /home/user/projeto/build", explicit_env="development")
        self.assertEqual(decision, "allow")
        self.assertEqual(use_case, "FILESYSTEM")

    def test_r1_dev_absolute_path_home_src_allowed(self):
        """R1: rm -rf /home/user/projeto/src/old em DEV deve ser permitido"""
        decision, reason, env, use_case = evaluate_command("rm -rf /home/user/projeto/src/old", explicit_env="development")
        self.assertEqual(decision, "allow")
        self.assertEqual(use_case, "FILESYSTEM")

    def test_r1_dev_absolute_path_opt_myapp_cache_allowed(self):
        """R1: rm -rf /opt/myapp/cache em DEV deve ser permitido"""
        decision, reason, env, use_case = evaluate_command("rm -rf /opt/myapp/cache", explicit_env="development")
        self.assertEqual(decision, "allow")
        self.assertEqual(use_case, "FILESYSTEM")

    def test_r1_dev_absolute_path_var_tmp_allowed(self):
        """R1: rm -rf /var/tmp/ceh-x em DEV deve ser permitido"""
        decision, reason, env, use_case = evaluate_command("rm -rf /var/tmp/ceh-x", explicit_env="development")
        self.assertEqual(decision, "allow")
        self.assertEqual(use_case, "FILESYSTEM")

    def test_r1_dev_absolute_path_usr_local_lib_allowed(self):
        """R1: rm -rf /usr/local/lib/node_modules/foo em DEV deve ser permitido"""
        decision, reason, env, use_case = evaluate_command("rm -rf /usr/local/lib/node_modules/foo", explicit_env="development")
        self.assertEqual(decision, "allow")
        self.assertEqual(use_case, "FILESYSTEM")

    # --------------------------------------------------------------------------
    # R2: Fechamento de Bypasses de Raiz e Ancestrais (Normalização)
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
    # --------------------------------------------------------------------------
    def test_r3_production_safe_reason_does_not_contain_env_development(self):
        """R3: Motivo de atalho de limpeza segura em produção não deve conter '--env development'"""
        decision, reason, env, use_case = evaluate_command("rm -rf dist/", explicit_env="production")
        self.assertEqual(decision, "allow")
        self.assertEqual(use_case, "FILESYSTEM_SAFE")
        self.assertNotIn("--env development", reason)
        self.assertIn("Safe development operation permitted", reason)

    # --------------------------------------------------------------------------
    # CMD-095
    # --------------------------------------------------------------------------
    def test_control_cmd095_subpath_behavior_per_environment(self):
        """CMD-095: rm -rf a.txt /var/lib/postgresql retorna FILESYSTEM (dev: allow, sta: ask, pro: deny)"""
        dec_dev, _, _, uc_dev = evaluate_command("rm -rf a.txt /var/lib/postgresql", explicit_env="development")
        self.assertEqual(dec_dev, "allow")
        self.assertEqual(uc_dev, "FILESYSTEM")

        dec_sta, _, _, uc_sta = evaluate_command("rm -rf a.txt /var/lib/postgresql", explicit_env="staging")
        self.assertEqual(dec_sta, "ask")
        self.assertEqual(uc_sta, "FILESYSTEM")

        dec_pro, _, _, uc_pro = evaluate_command("rm -rf a.txt /var/lib/postgresql", explicit_env="production")
        self.assertEqual(dec_pro, "deny")
        self.assertEqual(uc_pro, "FILESYSTEM")


    # --------------------------------------------------------------------------
    # T1 (Handoff 016): Normalização estrita de caminho para atalho seguro
    # Caminhos que começam com prefixo seguro mas resolvem para alvos inseguros (build/../src, coverage/../.git)
    # NÃO devem ser FILESYSTEM_SAFE em produção (devem ser DENY FILESYSTEM)
    # --------------------------------------------------------------------------
    def test_t1_production_build_parent_src_denied(self):
        """T1: rm -rf build/../src em produção deve ser NEGADO (FILESYSTEM), não allow FILESYSTEM_SAFE"""
        decision, reason, env, use_case = evaluate_command("rm -rf build/../src", explicit_env="production")
        self.assertEqual(decision, "deny")
        self.assertEqual(use_case, "FILESYSTEM")

    def test_t1_production_coverage_parent_git_denied(self):
        """T1: rm -rf coverage/../.git em produção deve ser NEGADO (FILESYSTEM), não allow FILESYSTEM_SAFE"""
        decision, reason, env, use_case = evaluate_command("rm -rf coverage/../.git", explicit_env="production")
        self.assertEqual(decision, "deny")
        self.assertEqual(use_case, "FILESYSTEM")


if __name__ == "__main__":
    unittest.main()
