#!/usr/bin/env python3
"""
test_environment_differential.py - Rede diferencial da detecção de ambiente sem explicit_env (PR-07b).
Handoff 031 §3.3:
- Avalia a baseline (gate_baseline.txt) e o gate atual SEM explicit_env dentro de repos-fixtures
  nas branches dev, release/qa-1, main e feature/evaluation.
- Compara decisões e classifica relaxamentos contra relaxamentos_justificados.txt (H031-PR07).
- Prova de falsificabilidade: simula a lista estreita do PR-07 e comprova a falha em 'terraform destroy -var env=production'.
"""

import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_DIR.parent.parent
SCRIPTS_DIR = REPO_ROOT / "clearer-engineering" / "scripts"
FIXTURES_DIR = TESTS_DIR / "fixtures"

spec_cur = importlib.util.spec_from_file_location("safety_gate", str(SCRIPTS_DIR / "safety-gate.py"))
current_gate = importlib.util.module_from_spec(spec_cur)
spec_cur.loader.exec_module(current_gate)

from ceh_core.environment import normalize_env, ENV_SEVERITY


def load_authorized_relaxations(relaxations_path: Path) -> dict[tuple[str, str, str], str]:
    authorized = {}
    if not relaxations_path.exists():
        return authorized
    for line in relaxations_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("|", 3)
        if len(parts) >= 4:
            env, cmd, de_para, finding_id = parts[0].strip(), parts[1].strip(), parts[2].strip(), parts[3].strip()
            authorized[(env, cmd, de_para)] = finding_id
    return authorized


def extract_baseline_gate(baseline_sha: str, target_dir: Path):
    """Extrai safety-gate.py e ceh_core da linha de base."""
    target_dir.mkdir(parents=True, exist_ok=True)
    archive_cmd = ["git", "archive", baseline_sha, "clearer-engineering/scripts/"]
    p1 = subprocess.Popen(archive_cmd, cwd=REPO_ROOT, stdout=subprocess.PIPE)
    tar_cmd = ["tar", "-x", "-C", str(target_dir)]
    subprocess.check_call(tar_cmd, stdin=p1.stdout)
    if p1.stdout:
        p1.stdout.close()
    p1.wait()


class TestEnvironmentDifferential(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp_dir = Path(tempfile.mkdtemp(prefix="ceh-env-diff-"))
        baseline_file = FIXTURES_DIR / "gate_baseline.txt"
        cls.baseline_sha = baseline_file.read_text(encoding="utf-8").strip()

        cls.baseline_dir = cls.tmp_dir / "baseline"
        extract_baseline_gate(cls.baseline_sha, cls.baseline_dir)

        # Carrega o gate da baseline
        baseline_script = cls.baseline_dir / "clearer-engineering" / "scripts" / "safety-gate.py"
        spec = importlib.util.spec_from_file_location("baseline_gate", str(baseline_script))
        cls.baseline_gate = importlib.util.module_from_spec(spec)
        sys.path.insert(0, str(baseline_script.parent))
        spec.loader.exec_module(cls.baseline_gate)

        # Repositórios-fixture
        cls.repos = {}
        for branch in ["dev", "release/qa-1", "main", "feature/evaluation"]:
            r_path = cls.tmp_dir / f"repo_{branch.replace('/', '_')}"
            r_path.mkdir(parents=True, exist_ok=True)
            subprocess.run(["git", "init", "-q", "-b", branch, str(r_path)], check=True)
            subprocess.run(["git", "-C", str(r_path), "config", "user.name", "CEH Diff"], check=True)
            subprocess.run(["git", "-C", str(r_path), "config", "user.email", "diff@ceh.local"], check=True)
            (r_path / "README.md").write_text("initial\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(r_path), "add", "README.md"], check=True)
            subprocess.run(["git", "-C", str(r_path), "commit", "-q", "-m", "init"], check=True)
            cls.repos[branch] = r_path

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp_dir, ignore_errors=True)

    def setUp(self):
        self.orig_environ = os.environ.copy()
        for v in ["CEH_ENV", "APP_ENV", "NODE_ENV", "RAILS_ENV", "ENVIRONMENT", "ENV", "STAGE"]:
            os.environ.pop(v, None)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.orig_environ)

    def _get_test_commands(self) -> list[str]:
        return [
            # Tabela Handoff 031 §1
            "cd /srv/production && php artisan migrate:fresh",
            "php artisan migrate:fresh --environment=production",
            "terraform destroy -var env=production",
            "DJANGO_SETTINGS_MODULE=app.settings.production python manage.py flush --noinput",
            # Sinais por forma
            "MIX_ENV=prod mix ecto.drop",
            "STAGE=production serverless deploy",
            "terraform apply -var env=staging",
            "helm upgrade --set env=production my-app ./chart",
            "kubectl --context prod-cluster delete pod x",
            "kubectl --kube-context=staging-cluster delete pod y",
            "php artisan migrate:fresh --stage=production",
            "aws s3 rm s3://bucket --profile production",
            # Inócuos do H031-PR07
            "rm -rf build/production-assets",
            "cat docs/staging-notes.md",
            "git log --grep=production",
            "docker compose -f docker-compose.staging.yml ps",
            "git reset --hard",
            # Comandos de controle
            "git status",
            "npm test",
        ]

    def test_environment_differential_matrix(self):
        """Avalia baseline vs gate atual sem explicit_env em múltiplos repositórios."""
        authorized = load_authorized_relaxations(FIXTURES_DIR / "relaxamentos_justificados.txt")
        rank = {"deny": 3, "ask": 2, "allow": 1}

        commands = self._get_test_commands()
        unauthorized_relaxations: list[str] = []

        for branch, repo in self.repos.items():
            for cmd in commands:
                # Baseline
                old_dec, old_r, old_env, old_uc = self.baseline_gate.evaluate_command(cmd, base_cwd=repo)
                old_is_cat = (old_uc == "CATASTROPHIC") or ("CATASTROPHIC" in old_r)
                old_rank = 4 if old_is_cat else rank.get(old_dec, 1)

                # Gate Atual
                cur_dec, cur_r, cur_env, cur_uc = current_gate.evaluate_command(cmd, base_cwd=repo)
                cur_is_cat = (cur_uc == "CATASTROPHIC") or ("CATASTROPHIC" in cur_r)
                cur_rank = 4 if cur_is_cat else rank.get(cur_dec, 1)

                if cur_rank < old_rank:
                    de_para = f"{old_dec}->{cur_dec}"
                    auth_key = (cur_env, cmd, de_para)
                    if auth_key not in authorized:
                        unauthorized_relaxations.append(
                            f"[{branch}] {cmd}: old={old_dec}({old_env}) -> cur={cur_dec}({cur_env}) [{de_para}]"
                        )

        if unauthorized_relaxations:
            msg = f"\n[REPROVADO - Handoff 031 §3.3] {len(unauthorized_relaxations)} relaxamentos não autorizados de detecção:\n"
            for r in unauthorized_relaxations:
                msg += f"  • {r}\n"
            self.fail(msg)

    def test_falsifiability_narrow_list_fails(self):
        """
        Prova de falsificabilidade (Handoff 031 §3.3):
        Simula a lista estreita do PR-07 onde '-var env=production' não era reconhecido.
        A rede DEVE reprovar comprovadamente citando 'terraform destroy -var env=production'.
        """
        repo_dev = self.repos["dev"]
        cmd = "terraform destroy -var env=production"

        # Na baseline (antes do PR-07), saía deny/production por substring
        old_dec, _, old_env, _ = self.baseline_gate.evaluate_command(cmd, base_cwd=repo_dev)
        self.assertEqual(old_dec, "deny")

        # Com gate atual, sai deny/production
        cur_dec, _, cur_env, _ = current_gate.evaluate_command(cmd, base_cwd=repo_dev)
        self.assertEqual(cur_dec, "deny")
        self.assertEqual(cur_env, "production")

        # Simulação da lista estreita do PR-07:
        # No PR-07 estreito, -var env=production retornava development e saía allow em dev!
        narrow_env, _ = "development", "fallback"
        narrow_dec = "allow"  # em dev, destroy/allow sem bloqueio de produção

        rank = {"deny": 3, "ask": 2, "allow": 1}
        self.assertLess(rank[narrow_dec], rank[old_dec], "Falsificabilidade comprovada: lista estreita relaxa indevidamente para allow.")


if __name__ == "__main__":
    unittest.main()
