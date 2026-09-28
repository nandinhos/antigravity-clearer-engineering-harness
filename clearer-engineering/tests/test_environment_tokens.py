#!/usr/bin/env python3
"""
test_environment_tokens.py - Testes de detecção de ambiente por token explícito (PR-07b)
Cobre os Handoffs 030 e 031:
- Detecção por tokens explícitos e por forma (atribuições NOME=valor, -var k=v, --opt=val)
- Invariante de não rebaixamento de severidade
- Segmentação estrita em normalize_env e branch names (anti falsos-positivos delivery/evaluation)
- AF1: cd/pushd definindo contexto dos subcomandos seguintes
- Hermeticidade com isolamento do os.environ
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
        # Handoff 031 §3.4: Hermeticidade contra variáveis do host/CI
        self.orig_environ = os.environ.copy()
        for var in ["CEH_ENV", "APP_ENV", "NODE_ENV", "RAILS_ENV", "ENVIRONMENT", "ENV", "STAGE"]:
            os.environ.pop(var, None)

    def tearDown(self):
        os.chdir(self.orig_cwd)
        os.environ.clear()
        os.environ.update(self.orig_environ)
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
            decision, reason, _, _ = safety_gate.evaluate_command(cmd, base_cwd=repo)
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

    def test_handoff_031_section_1_table(self):
        """Handoff 031 §1: Sinais por forma reconhecidos em contexto de dev."""
        repo_dev = self._init_repo("r_dev_h31", branch="dev")

        cases = [
            ("cd /srv/production && php artisan migrate:fresh", "production", "deny"),
            ("php artisan migrate:fresh --environment=production", "production", "deny"),
            ("terraform destroy -var env=production", "production", "deny"),
            ("DJANGO_SETTINGS_MODULE=app.settings.production python manage.py flush --noinput", "production", None),
        ]

        for cmd, expected_env, expected_decision in cases:
            env, _ = detect_environment(cmd_line=cmd, target_dir=repo_dev)
            self.assertEqual(env, expected_env, f"Falha no ambiente para '{cmd}' em dev")
            decision, reason, eval_env, _ = safety_gate.evaluate_command(cmd, base_cwd=repo_dev)
            self.assertEqual(eval_env, expected_env, f"Falha no ambiente avaliado pelo gate para '{cmd}' em dev")
            if expected_decision is not None:
                self.assertEqual(decision, expected_decision, f"Falha na decisão para '{cmd}' em dev: reason={reason}")

    def test_handoff_031_af1_cd_updates_context(self):
        """Handoff 031 AF1: cd <repo-main> && git reset --hard -> deny/production."""
        repo_dev = self._init_repo("repo_af1_dev", branch="dev")
        repo_main = self._init_repo("repo_af1_main", branch="main")

        cmd = f"cd {repo_main} && git reset --hard"
        decision, reason, eval_env, _ = safety_gate.evaluate_command(cmd, base_cwd=repo_dev)
        self.assertEqual(decision, "deny", f"AF1 falhou: {cmd} deveria ser deny/production, mas foi {decision} ({reason})")
        self.assertEqual(eval_env, "production", f"AF1 falhou: ambiente deveria ser production, mas foi {eval_env}")

    def test_handoff_032_ag1_subshell_context(self):
        """Handoff 032 AG1: (cd <repo-main> && git reset --hard) -> deny/production sem vazamento."""
        repo_dev = self._init_repo("repo_ag1_dev", branch="dev")
        repo_main = self._init_repo("repo_ag1_main", branch="main")

        # Subshell isolado com comando destrutivo no repo em main -> deny/production
        cmd = f"(cd {repo_main} && git reset --hard)"
        decision, reason, eval_env, _ = safety_gate.evaluate_command(cmd, base_cwd=repo_dev)
        self.assertEqual(decision, "deny", f"AG1 falhou: {cmd} deveria ser deny/production, mas foi {decision} ({reason})")
        self.assertEqual(eval_env, "production", f"AG1 falhou: ambiente deveria ser production, mas foi {eval_env}")

        # Contexto não vaza para fora dos parênteses: se vazasse para repo_main, git reset --hard seria deny
        cmd_no_leak = f"(cd {repo_main} && git status) && git reset --hard"
        decision, reason, _, _ = safety_gate.evaluate_command(cmd_no_leak, base_cwd=repo_dev)
        self.assertEqual(decision, "allow", f"AG1 não vazamento falhou: {cmd_no_leak} deveria ser allow em dev, mas foi {decision} ({reason})")

    def test_handoff_032_ag2_unresolved_cd_escalates(self):
        """Handoff 032 AG2: cd para destino incerto/dinâmico resulta em contexto production (Invariante 7)."""
        repo_dev = self._init_repo("repo_ag2_dev", branch="dev")

        # Destino não resolvível seguido de comando destrutivo -> deny / production
        destructive_cases = [
            'cd "$PROD_DIR" && git reset --hard',
            'cd - && git reset --hard',
            'cd ~nonexistent_user_12345 && git reset --hard',
            'cd ${PROD_PATH} && git reset --hard',
        ]
        for cmd in destructive_cases:
            decision, reason, eval_env, _ = safety_gate.evaluate_command(cmd, base_cwd=repo_dev)
            self.assertEqual(decision, "deny", f"AG2 falhou: {cmd} deveria ser deny, mas foi {decision} ({reason})")
            self.assertEqual(eval_env, "production", f"AG2 falhou: {cmd} deveria ser production, mas foi {eval_env}")

        # Custo aceito: comando não destrutivo segue allow
        cmd_safe = 'cd "$DIR" && npm test'
        decision, reason, eval_env, _ = safety_gate.evaluate_command(cmd_safe, base_cwd=repo_dev)
        self.assertEqual(decision, "allow", f"AG2 custo aceito falhou: {cmd_safe} deveria ser allow, mas foi {decision} ({reason})")
        self.assertEqual(eval_env, "production", f"AG2 custo aceito falhou: ambiente deveria ser production, mas foi {eval_env}")

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

    def test_handoff_033_ah1_and_ah2_context_equivalence(self):
        """Handoff 033 AH1 e AH2: formas alternativas de contexto produzem mesmo efeito que cd X &&."""
        repo_dev = self._init_repo("repo_ah1_dev", branch="dev")
        repo_main = self._init_repo("repo_ah1_main", branch="main")

        cases_destructive = [
            (f"{{ cd {repo_main}; git checkout -- .; }}", "deny", "production"),
            (f"env -C {repo_main} git reset --hard", "deny", "production"),
            (f"env --chdir={repo_main} git reset --hard", "deny", "production"),
            (f"sudo -D {repo_main} git reset --hard", "deny", "production"),
            (f"sudo --chdir={repo_main} git reset --hard", "deny", "production"),
            (f"GIT_DIR={repo_main}/.git GIT_WORK_TREE={repo_main} git reset --hard", "deny", "production"),
            (f"export GIT_DIR={repo_main}/.git && git reset --hard", "deny", "production"),
            ("cd && git reset --hard", "deny", "production"),
            ("cd ~ && git reset --hard", "deny", "production"),
            (f"(cd {repo_main} && git reset --hard)", "deny", "production"),
        ]
        for cmd, exp_dec, exp_env in cases_destructive:
            dec, reason, eval_env, _ = safety_gate.evaluate_command(cmd, base_cwd=repo_dev)
            self.assertEqual(dec, exp_dec, f"AH1/AH2 falhou: {cmd} deveria ser {exp_dec}, mas foi {dec} ({reason})")
            self.assertEqual(eval_env, exp_env, f"AH1/AH2 falhou: {cmd} deveria ser {exp_env}, mas foi {eval_env}")

        # Controles inócuos e não-vazamento (Handoff 033: controles do subshell sem vazamento seguem allow)
        cases_safe = [
            (f"(cd {repo_main}) && git reset --hard", "allow"),
            ('cd "$DIR" && npm test', "allow"),
            (f"env -C {repo_main} npm test", "allow"),
            (f"sudo -D {repo_main} npm test", "allow"),
        ]
        for cmd, exp_dec in cases_safe:
            dec, reason, eval_env, _ = safety_gate.evaluate_command(cmd, base_cwd=repo_dev)
            self.assertEqual(dec, exp_dec, f"Controle falhou: {cmd} deveria ser {exp_dec}, mas foi {dec} ({reason})")

    def test_handoff_034_ai1_and_ai2_context_modification(self):
        """Handoff 034 AI1 e AI2: troca de branch e arquivo de ambiente como mudança de contexto."""
        repo_dev = self._init_repo("repo_ai_dev", branch="dev")

        cases_destructive = [
            ("git switch main && git reset --hard", "deny", "production"),
            ("git checkout main && git reset --hard", "deny", "production"),
            ("source .env.production && php artisan migrate:fresh", "deny", "production"),
            (". ./prod.env && php artisan migrate:fresh", "deny", "production"),
            ("cp .env.production .env && php artisan migrate:fresh", "deny", "production"),
            ("echo APP_ENV=production > .env && php artisan db:wipe", "deny", "production"),
        ]
        for cmd, exp_dec, exp_env in cases_destructive:
            dec, reason, eval_env, _ = safety_gate.evaluate_command(cmd, base_cwd=repo_dev)
            self.assertEqual(dec, exp_dec, f"AI1/AI2 falhou: {cmd} deveria ser {exp_dec}, mas foi {dec} ({reason})")
            self.assertEqual(eval_env, exp_env, f"AI1/AI2 falhou: {cmd} deveria ser {exp_env}, mas foi {eval_env}")

        # Controles
        cases_safe = [
            ("git checkout -b hotfix && git reset --hard", "allow"),
            ("git checkout app/Model.php && git reset --hard", "allow"),
            ("(git checkout main) && git reset --hard", "allow"),
        ]
        for cmd, exp_dec in cases_safe:
            dec, reason, eval_env, _ = safety_gate.evaluate_command(cmd, base_cwd=repo_dev)
            self.assertEqual(dec, exp_dec, f"Controle AI1 falhou: {cmd} deveria ser {exp_dec}, mas foi {dec} ({reason})")

    def test_context_equivalence_invariant(self):
        """
        Handoff 033 / 034 Invariante de equivalência de contexto estendida:
        Para cada comando destrutivo C e forma F, severidade F(<main>, C) >= severidade(cd <main> && C).
        """
        repo_dev = self._init_repo("repo_eq_dev", branch="dev")
        repo_main = self._init_repo("repo_eq_main", branch="main")

        destructive_commands = [
            "git reset --hard HEAD~1",
            "git checkout -- .",
            "git clean -fdx",
            "php artisan migrate:fresh",
        ]

        forms = [
            ("brace_block", lambda d, c: f"{{ cd {d}; {c}; }}"),
            ("env_C", lambda d, c: f"env -C {d} {c}"),
            ("env_chdir", lambda d, c: f"env --chdir={d} {c}"),
            ("sudo_D", lambda d, c: f"sudo -D {d} {c}"),
            ("sudo_chdir", lambda d, c: f"sudo --chdir={d} {c}"),
            ("git_dir_env", lambda d, c: f"GIT_DIR={d}/.git GIT_WORK_TREE={d} {c}"),
            ("export_git_dir", lambda d, c: f"export GIT_DIR={d}/.git && {c}"),
            ("git_switch_main", lambda d, c: f"git switch main && {c}"),
            ("git_checkout_main", lambda d, c: f"git checkout main && {c}"),
            ("source_env_prod", lambda d, c: f"source .env.production && {c}"),
            ("cp_env_prod", lambda d, c: f"cp .env.production .env && {c}"),
        ]

        dec_sev = {"allow": 0, "ask": 1, "deny": 2}

        for cmd in destructive_commands:
            baseline_cmd = f"cd {repo_main} && {cmd}"
            base_dec, base_reas, base_env, _ = safety_gate.evaluate_command(baseline_cmd, base_cwd=repo_dev)
            base_d_sev = dec_sev.get(base_dec, 0)

            for form_name, form_fn in forms:
                mod_cmd = form_fn(repo_main, cmd)
                mod_dec, mod_reas, mod_env, _ = safety_gate.evaluate_command(mod_cmd, base_cwd=repo_dev)
                mod_d_sev = dec_sev.get(mod_dec, 0)

                self.assertGreaterEqual(
                    mod_d_sev,
                    base_d_sev,
                    f"Invariante de equivalência violada por {form_name}: '{mod_cmd}' ({mod_dec}) < '{baseline_cmd}' ({base_dec})"
                )
                self.assertEqual(
                    mod_env,
                    "production",
                    f"Invariante de equivalência violada: {form_name} não detectou production para {mod_cmd} (obteve {mod_env})"
                )


if __name__ == "__main__":
    unittest.main()

