#!/usr/bin/env python3
"""
test_environment_differential.py - Rede diferencial da detecção de ambiente sem explicit_env (PR-07c).

Especificação (Handoff 032 §2):
1. B1: Execução hermética da linha de base em subprocesso separado, evitando reaproveitamento
   de módulos ceh_core carregados em memória. sys.path aponta apenas para o scripts/ da baseline.
2. B2: Removido teste tautológico de falsificabilidade. Prova feita por mutação real documentada.
3. B3: Arquivo exclusivo tests/fixtures/relaxamentos_deteccao.txt com branch na chave (branch|comando|de->para|ID).
4. B4: Entradas da rede cobrem corpus decodificado, baterias, tabela do Handoff 031 e gramática de sinais.
5. Avaliado nas branches dev, release/qa-1, main e feature/evaluation sem explicit_env.
"""
from __future__ import annotations

import base64
import json
import os
import random
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

BASELINE_FILE = FIXTURES_DIR / "gate_baseline.txt"
RELAXATIONS_FILE = FIXTURES_DIR / "relaxamentos_deteccao.txt"
CORPUS_FILE = FIXTURES_DIR / "gate_corpus.txt"
BATTERY_FILE = FIXTURES_DIR / "review_batteries.txt"


def load_corpus_commands(corpus_path: Path) -> list[str]:
    """Carrega comandos do corpus decodificando RAW: e B64: (ignora HOOK e INTEGRATION)."""
    cmds = []
    if not corpus_path.exists():
        return cmds
    for line in corpus_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("HOOK:") or line.startswith("INTEGRATION:"):
            continue
        if line.startswith("RAW:"):
            cmds.append(line[4:].strip())
        elif line.startswith("B64:"):
            try:
                decoded = base64.b64decode(line[4:]).decode("utf-8").strip()
                cmds.append(decoded)
            except Exception:
                pass
        else:
            cmds.append(line)
    return cmds


def load_battery_commands(battery_path: Path) -> list[str]:
    """Carrega comandos das baterias adversariais de revisão."""
    cmds = []
    if not battery_path.exists():
        return cmds
    for line in battery_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("|", 3)
        if len(parts) >= 4:
            cmds.append(parts[3].strip())
    return cmds


def get_handoff_commands() -> list[str]:
    """Tabela de comandos dos Handoffs 030, 031 e 032."""
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
        # Handoff 032 AG1 e AG2
        'cd "$PROD_DIR" && git reset --hard',
        'cd - && git reset --hard',
        'cd "$DIR" && npm test',
        '(cd /srv/production && git reset --hard)',
        '(cd /srv/dev && git reset --hard)',
        '(cd /srv/production && npm test)',
        'cd ~nonexistent_user_xyz && git reset --hard',
    ]


def generate_signal_grammar(seed: int = 42, count: int = 300) -> list[str]:
    """Gera comandos por gramática determinística de sinais de ambiente (B4)."""
    rng = random.Random(seed)
    cmds: set[str] = set()

    env_names_prod = ["production", "prod"]
    env_names_stage = ["staging", "stage", "hml"]
    env_names_dev = ["development", "dev", "local", "test"]
    all_envs = env_names_prod + env_names_stage + env_names_dev

    keys = ["env", "environment", "stage", "profile", "target"]
    var_prefixes = ["APP_ENV", "NODE_ENV", "ENVIRONMENT", "STAGE", "CEH_ENV", "MIX_ENV", "ENV", "TARGET_ENV"]

    dest_cmds = [
        "git reset --hard",
        "php artisan migrate:fresh",
        "php artisan db:wipe",
        "terraform destroy",
        "git clean -fdx",
        "npm test",
        "git status",
        "echo ok",
    ]

    cd_targets = [
        "/srv/production", "/srv/staging", "/srv/dev", "/srv/local",
        "config/production", "config/staging", "build/production-assets",
        '"$PROD_DIR"', '"$DIR"', "'-'", "~/production", "~/dev",
    ]

    while len(cmds) < count:
        pattern = rng.randint(1, 6)
        c = rng.choice(dest_cmds)
        v = rng.choice(all_envs)
        k = rng.choice(keys)

        if pattern == 1:
            var = rng.choice(var_prefixes)
            cmds.add(f"{var}={v} {c}")
        elif pattern == 2:
            cmds.add(f"terraform destroy -var {k}={v}")
            cmds.add(f"terraform apply -var {k}={v}")
        elif pattern == 3:
            cmds.add(f"helm upgrade --set {k}={v} my-app ./chart")
        elif pattern == 4:
            opt = rng.choice(["--env", "--environment", "--stage", "--profile"])
            cmds.add(f"{c} {opt}={v}")
            cmds.add(f"{c} {opt} {v}")
        elif pattern == 5:
            cd_t = rng.choice(cd_targets)
            cmds.add(f"cd {cd_t} && {c}")
        elif pattern == 6:
            # Subshell
            inner_var = rng.choice(var_prefixes)
            cmds.add(f"({inner_var}={v} {c})")
            cd_t = rng.choice(cd_targets)
            cmds.add(f"(cd {cd_t} && {c})")

    return sorted(list(cmds))


def load_authorized_relaxations(relaxations_path: Path) -> dict[tuple[str, str, str], str]:
    """Carrega lista de relaxamentos autorizados no formato branch|comando|de->para|ID-do-achado."""
    authorized = {}
    if not relaxations_path.exists():
        return authorized
    for line in relaxations_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("|", 3)
        if len(parts) >= 4:
            branch, cmd, de_para, finding_id = parts[0].strip(), parts[1].strip(), parts[2].strip(), parts[3].strip()
            authorized[(branch, cmd, de_para)] = finding_id
    return authorized


def extract_baseline_gate(baseline_sha: str, target_dir: Path):
    """Extrai safety-gate.py e ceh_core da linha de base de forma hermética."""
    target_dir.mkdir(parents=True, exist_ok=True)
    archive_cmd = f"git archive {baseline_sha} clearer-engineering/scripts | tar -x -C '{target_dir}'"
    proc = subprocess.run(["bash", "-c", archive_cmd], cwd=REPO_ROOT, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"Falha ao extrair baseline {baseline_sha}: {proc.stderr}")


class TestEnvironmentDifferential(unittest.TestCase):
    """Rede diferencial hermética de detecção de ambiente contra baseline isolada."""

    tmp_dir: Path | None = None
    baseline_dir: Path | None = None
    repos: dict[str, Path] = {}
    baseline_results: dict[str, dict[str, list]] = {}
    current_results: dict[str, dict[str, list]] = {}
    all_commands: list[str] = []

    @classmethod
    def setUpClass(cls):
        cls.tmp_dir = Path(tempfile.mkdtemp(prefix="ceh-env-diff-"))
        baseline_file = FIXTURES_DIR / "gate_baseline.txt"
        if not baseline_file.exists():
            raise FileNotFoundError(f"Arquivo de baseline ausente: {baseline_file}")
        baseline_sha = baseline_file.read_text(encoding="utf-8").strip()

        cls.baseline_dir = cls.tmp_dir / "baseline"
        extract_baseline_gate(baseline_sha, cls.baseline_dir)
        baseline_scripts = str(cls.baseline_dir / "clearer-engineering" / "scripts")

        # 1. Carrega comandos de todas as fontes (B4)
        corpus_cmds = load_corpus_commands(CORPUS_FILE)
        battery_cmds = load_battery_commands(BATTERY_FILE)
        handoff_cmds = get_handoff_commands()
        grammar_cmds = generate_signal_grammar(seed=42, count=300)

        cls.all_commands = sorted(list(set(corpus_cmds + battery_cmds + handoff_cmds + grammar_cmds)))

        # 2. Cria repositórios git fixtures nas 4 branches
        cls.repos = {}
        branches = ["dev", "release/qa-1", "main", "feature/evaluation"]
        for branch in branches:
            r_path = cls.tmp_dir / f"repo_{branch.replace('/', '_')}"
            r_path.mkdir(parents=True, exist_ok=True)
            subprocess.run(["git", "init", "-q", "-b", branch, str(r_path)], check=True)
            subprocess.run(["git", "-C", str(r_path), "config", "user.name", "CEH Diff"], check=True)
            subprocess.run(["git", "-C", str(r_path), "config", "user.email", "diff@ceh.local"], check=True)
            (r_path / "README.md").write_text(f"branch: {branch}\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(r_path), "add", "README.md"], check=True)
            subprocess.run(["git", "-C", str(r_path), "commit", "-q", "-m", "init"], check=True)
            cls.repos[branch] = r_path

        # 3. Código do worker isolado (B1)
        worker_code = """
import sys, json
sys.path.insert(0, sys.argv[1])
from importlib import import_module
gate = import_module('safety-gate')
cmds = json.load(sys.stdin)
results = {}
for cmd in cmds:
    dec, reason, env_res, uc = gate.evaluate_command(cmd)
    is_cat = (uc == 'CATASTROPHIC') or ('CATASTROPHIC' in reason)
    results[cmd] = [dec, is_cat, uc, env_res]
json.dump(results, sys.stdout)
"""

        cls.baseline_results = {}
        cls.current_results = {}

        # Executa workers isolados por repositório
        for branch, r_path in cls.repos.items():
            # Baseline worker (subprocesso isolado com sys.path da baseline)
            p_base = subprocess.Popen(
                [sys.executable, "-c", worker_code, baseline_scripts],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(r_path),
            )
            out_base, err_base = p_base.communicate(input=json.dumps(cls.all_commands))
            if p_base.returncode != 0:
                raise RuntimeError(f"Falha no worker da baseline ({branch}): {err_base}")
            cls.baseline_results[branch] = json.loads(out_base)

            # Current gate worker (subprocesso isolado com scripts_dir atual)
            p_cur = subprocess.Popen(
                [sys.executable, "-c", worker_code, str(SCRIPTS_DIR)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(r_path),
            )
            out_cur, err_cur = p_cur.communicate(input=json.dumps(cls.all_commands))
            if p_cur.returncode != 0:
                raise RuntimeError(f"Falha no worker do gate atual ({branch}): {err_cur}")
            cls.current_results[branch] = json.loads(out_cur)

    @classmethod
    def tearDownClass(cls):
        if cls.tmp_dir and cls.tmp_dir.exists():
            shutil.rmtree(cls.tmp_dir, ignore_errors=True)

    def test_environment_differential_matrix(self):
        """Avalia baseline vs gate atual sem explicit_env em múltiplos repositórios."""
        authorized = load_authorized_relaxations(RELAXATIONS_FILE)
        rank = {"deny": 3, "ask": 2, "allow": 1}
        unauthorized_relaxations: list[str] = []

        for branch in self.repos:
            b_res = self.baseline_results[branch]
            c_res = self.current_results[branch]

            for cmd in self.all_commands:
                old_dec, old_is_cat, old_uc, old_env = b_res[cmd]
                cur_dec, cur_is_cat, cur_uc, cur_env = c_res[cmd]

                old_rank = 4 if old_is_cat else rank.get(old_dec, 1)
                cur_rank = 4 if cur_is_cat else rank.get(cur_dec, 1)

                if cur_rank < old_rank:
                    de_para = f"{old_dec}->{cur_dec}"
                    auth_key = (branch, cmd, de_para)
                    if auth_key not in authorized:
                        unauthorized_relaxations.append(
                            f"[{branch}] {cmd}: old={old_dec}({old_env}) -> cur={cur_dec}({cur_env}) [{de_para}]"
                        )

        if unauthorized_relaxations:
            msg = f"\n[REPROVADO - Handoff 032 §2] {len(unauthorized_relaxations)} relaxamentos não autorizados de detecção:\n"
            for r in unauthorized_relaxations:
                msg += f"  • {r}\n"
            self.fail(msg)


if __name__ == "__main__":
    unittest.main()
