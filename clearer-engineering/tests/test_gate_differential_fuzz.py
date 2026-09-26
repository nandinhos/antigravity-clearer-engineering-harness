#!/usr/bin/env python3
"""
test_gate_differential_fuzz.py - Fuzz diferencial contra a linha de base homologada (PR-QA-A2).

Especificação (Handoffs 022 e 023):
1. Linha de base: lê o SHA em tests/fixtures/gate_baseline.txt (avançado exclusivamente pela revisão).
2. Extração hermética: extrai o gate da linha de base via git archive para diretório temporário.
3. Hermeticidade (Y3): avalia ambos os gates dentro de um repositório git temporário (git init -b dev)
   e um HOME temporário isolado.
4. Entradas completas (Y1):
   - Corpus decodificado (RAW: literal, B64: base64 decodificado; HOOK/INTEGRATION ignorados).
   - Baterias de testes adversariais (review_batteries.txt).
   - ≥ 3000 comandos gerados deterministicamente por gramática com semente fixa (random.Random(42)),
     cobrindo abreviações (--forc, --work, --discard, --pathspec-from), checkout -B, switch --force-create,
     pathspec de variáveis e til, find com -delete catastrófico e one-liners de interpretador.
5. Comparação em 3 ambientes: DEVELOPMENT, HOMOLOGACAO (STAGING), PRODUCTION.
6. Detecção estrita de relaxamentos:
   - Transições de severidade decrescente (deny -> ask, deny -> allow, ask -> allow).
   - Saída de estado CATASTROPHIC.
   - Qualquer relaxamento não autorizado em tests/fixtures/relaxamentos_justificados.txt REPROVA o teste.
7. Orçamento de tempo (Y2): impresso no log como meta (< 20s), sem asserção de TimeoutError.
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
import time
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
FIXTURES_DIR = TESTS_DIR / "fixtures"


def get_git_repo_root() -> Path:
    cur = Path(__file__).resolve()
    for parent in [cur] + list(cur.parents):
        if (parent / ".git").exists():
            return parent
    return cur.parents[2]


REPO_ROOT = get_git_repo_root()
SCRIPTS_DIR = REPO_ROOT / "clearer-engineering" / "scripts"

BASELINE_FILE = FIXTURES_DIR / "gate_baseline.txt"
RELAXATIONS_FILE = FIXTURES_DIR / "relaxamentos_justificados.txt"
CORPUS_FILE = FIXTURES_DIR / "gate_corpus.txt"
BATTERY_FILE = FIXTURES_DIR / "review_batteries.txt"

sys.path.insert(0, str(SCRIPTS_DIR))


def load_corpus_commands(corpus_path: Path) -> list[str]:
    """Carrega comandos do corpus decodificando RAW: e B64: (ignora HOOK e INTEGRATION)."""
    cmds = []
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
    for line in battery_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("|", 3)
        if len(parts) >= 4:
            cmds.append(parts[3].strip())
    return cmds


def generate_grammar_commands(seed: int = 42, target_unique: int = 3500) -> list[str]:
    """
    Gera >= 3000 comandos únicos por gramática determinística com semente fixa (Y1).
    Cobre:
    - abreviações de opção longa (--forc, --discard, --work, --pathspec-from, --stage, --sourc);
    - checkout -B, switch --force-create, --pathspec-from-file/--pathspec-file-nul;
    - $VAR / ${VAR} sem aspas e ~/x como pathspec do git;
    - find com -delete e com caminho inicial catastrófico (/, ~, /etc, ..);
    - one-liners de interpretador (python3 -c, node -e, perl -e, ruby -e) inócuos e destrutivos.
    """
    rng = random.Random(seed)
    cmds: set[str] = set()

    rm_flags = [
        "-rf", "-fr", "-r", "-f", "-i", "-I", "-v", "--recursive", "--force",
        "-r -f", "-rf --", "-f -r", "-r --force", "-v -r -f", "--no-preserve-root -rf"
    ]
    rm_targets = [
        ".", "..", "...", "/", "//", "///", "/etc", "/etc/hosts", "/var/log", "/tmp", "/tmp/foo",
        "/home", "/home/user", "/home/user/project", "/home/user/project/build",
        "src", "src/", "src/*", "src/app", "src/../app", "src/../../etc",
        "dist", "dist/", "build", "build/bundle.js", "coverage", "scratch",
        "node_modules/.cache", ".cache", "$PWD", "$OLDPWD", "$HOME", "${PWD}", "${HOME}",
        "~", "~/project", "~/.bashrc", "*.py", "test_*.py", "app.py", "file with space.txt",
        "./dist/../src", "./build/../.git", "dist/../../etc", "/tmp/../etc"
    ]
    rm_prefixes = ["rm", "rtk rm", "/bin/rm", "rm -v", "sudo rm"]

    git_prefixes = ["git", "rtk git", "git -C /tmp", "git -P", "git --no-pager"]
    git_treeish = ["HEAD", "HEAD~1", "HEAD~2", "main", "master", "dev", "staging", "v1.0", "origin/main", "origin/dev", "."]
    
    pathspecs = [
        "app/User.php", "src/index.ts", "config/app.php", "README.md", "package.json",
        ".", "./", "../", "..", "src/", "src/*", "src/..", "*", "'*'", "\"*\"",
        "':/!x'", "':/^x'", "':/!:x'", "':/app/x'", "':/:app/x'", "':!app'", "':^src'",
        "':/src'", "':/.'", "':/!*.py'", "':^/tests'", "':(top)app'", "':(exclude)tests'",
        "':(top,exclude)dist'", "':(glob)src/*.py'", "':(icase)readme.md'",
        "'$PWD'", "'$HOME'", "'~'", "app/*.py", "tests/unit/*.py", "docs/**/*.md",
        # Variáveis e til sem aspas (Y1)
        "$FILE", "${FILE}", "$PWD", "${PWD}", "$DIR", "~/app/x", "~", "~/config.php"
    ]

    # Opções e abreviações para checkout (Y1)
    checkout_opts = [
        "--", "-f", "--force", "--forc", "-q", "--quiet", "-p", "--patch",
        "--ours", "--theirs", "--detach", "-B new-branch", "-B force-branch",
        "--pathspec-from-file=list.txt", "--pathspec-from-file list.txt",
        "--pathspec-from=list.txt"
    ]

    # Opções e abreviações para restore (Y1)
    restore_opts = [
        "--staged", "--worktree", "--staged --worktree", "-s HEAD", "--source=HEAD",
        "-s main", "--source=main", "-s dev", "--source=dev", "-p", "-q", "-W", "-S",
        # Abreviações longas (Y1)
        "--work", "--staged --work", "--stage", "--sourc=HEAD",
        "--pathspec-from-file=list.txt", "--pathspec-from=list.txt", "--pathspec-file-nul"
    ]

    # Opções e abreviações para switch (Y1)
    switch_opts = [
        "-c new-b", "-C force-b", "--force-create new-b", "--force-c new-b",
        "--detach", "-d", "-f", "--force", "--forc", "--discard-changes", "--discard",
        "-m", "--merge"
    ]
    branches = ["dev", "main", "staging", "feature/x", "bugfix/y", "HEAD~1", "v2.0"]
    reset_opts = ["--hard", "--soft", "--mixed", "--merge", "--keep"]
    clean_opts = ["-f", "-fd", "-fx", "-fxd", "-n", "-nd", "-f -d", "--force"]

    # Comandos find (Y1)
    find_catastrophic_roots = ["/", "~", "/etc", "..", "/var", "/usr", "/home"]
    find_safe_roots = [".", "src", "build", "dist", "/tmp"]

    # One-liners de interpretador (Y1)
    interpreter_destructive = [
        "python3 -c \"import shutil; shutil.rmtree('/')\"",
        "python3 -c \"import os; os.system('rm -rf /')\"",
        "node -e \"fs.rmSync('/', {recursive: true})\"",
        "node -e \"child_process.execSync('rm -rf *')\"",
        "perl -e \"system('rm -rf /')\"",
        "ruby -e \"require 'fileutils'; FileUtils.rm_rf('/')\"",
        "sh -c \"rm -rf /\"",
        "bash -c \"rm -rf *\""
    ]
    interpreter_safe = [
        "python3 -c \"print('hello')\"",
        "python3 -c \"import sys; sys.exit(0)\"",
        "node -e \"console.log(1+1)\"",
        "perl -e \"print 42\"",
        "ruby -e \"puts 'hello'\"",
        "sh -c \"echo safe\"",
        "bash -c \"echo safe\""
    ]

    while len(cmds) < target_unique:
        cat = rng.randint(1, 10)
        if cat == 1:  # rm
            p = rng.choice(rm_prefixes)
            f = rng.choice(rm_flags)
            t = rng.choice(rm_targets)
            if rng.random() < 0.2:
                t2 = rng.choice(rm_targets)
                cmds.add(f"{p} {f} {t} {t2}")
            else:
                cmds.add(f"{p} {f} {t}")
        elif cat == 2:  # checkout
            parts = [rng.choice(git_prefixes), "checkout"]
            if rng.random() < 0.4:
                parts.append(rng.choice(checkout_opts))
            if rng.random() < 0.4:
                parts.append(rng.choice(git_treeish))
            if rng.random() < 0.3:
                parts.append("--")
            parts.append(rng.choice(pathspecs))
            if rng.random() < 0.2:
                parts.append(rng.choice(pathspecs))
            cmds.add(" ".join(parts))
        elif cat == 3:  # restore
            parts = [rng.choice(git_prefixes), "restore"]
            parts.append(rng.choice(restore_opts))
            if rng.random() < 0.3:
                parts.append("--")
            parts.append(rng.choice(pathspecs))
            cmds.add(" ".join(parts))
        elif cat == 4:  # switch
            parts = [rng.choice(git_prefixes), "switch"]
            if rng.random() < 0.6:
                parts.append(rng.choice(switch_opts))
            parts.append(rng.choice(branches))
            cmds.add(" ".join(parts))
        elif cat == 5:  # reset
            parts = [rng.choice(git_prefixes), "reset", rng.choice(reset_opts), rng.choice(git_treeish)]
            if rng.random() < 0.3:
                parts.extend(["--", rng.choice(pathspecs)])
            cmds.add(" ".join(parts))
        elif cat == 6:  # clean
            cmds.add(f"{rng.choice(git_prefixes)} clean {rng.choice(clean_opts)}")
        elif cat == 7:  # branch / push
            if rng.random() < 0.5:
                cmds.add(f"{rng.choice(git_prefixes)} push origin {rng.choice(branches)} {rng.choice(['', '--force', '-f', '--force-with-lease'])}".strip())
            else:
                cmds.add(f"{rng.choice(git_prefixes)} branch {rng.choice(['-d', '-D', '-m', '-a'])} {rng.choice(branches)}")
        elif cat == 8:  # find com -delete catastrófico e seguro (Y1)
            r = rng.random()
            if r < 0.3:
                root = rng.choice(find_catastrophic_roots)
                cmds.add(f"find {root} -delete")
            elif r < 0.6:
                root = rng.choice(find_catastrophic_roots)
                cmds.add(f"find {root} -name '*.log' -delete")
            elif r < 0.8:
                root = rng.choice(find_safe_roots)
                cmds.add(f"find {root} -name '*.pyc' -delete")
            else:
                root = rng.choice(find_catastrophic_roots)
                cmds.add(f"find {root} -exec rm -rf {{}} +")
        elif cat == 9:  # one-liners de interpretador inócuos e destrutivos (Y1)
            if rng.random() < 0.5:
                cmds.add(rng.choice(interpreter_destructive))
            else:
                cmds.add(rng.choice(interpreter_safe))
        elif cat == 10:  # pipelines e comandos encadeados
            r = rng.random()
            if r < 0.4:
                cmds.add(f"find {rng.choice(['.', 'src', '/tmp', 'build'])} -name '*.pyc' -exec rm -rf {{}} +")
            elif r < 0.7:
                cmds.add(f"{rng.choice(['git status', 'git diff', 'echo test'])} && git checkout {rng.choice(pathspecs)}")
            else:
                cmds.add(f"rm -rf {rng.choice(['build', 'dist', 'node_modules'])} && npm run build")

    return sorted(list(cmds))


def load_authorized_relaxations(relaxations_path: Path) -> dict[tuple[str, str, str], str]:
    """Carrega lista de relaxamentos autorizados no formato env|comando|de->para|ID-do-achado."""
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


class TestGateDifferentialFuzz(unittest.TestCase):
    """Suíte de fuzzing diferencial contra a linha de base homologada."""

    baseline_dir: str | None = None
    diff_repo: str | None = None
    diff_home: str | None = None
    baseline_results: dict[str, list] = {}
    current_results: dict[str, list] = {}
    all_commands: list[str] = []
    baseline_sha: str = ""

    @classmethod
    def setUpClass(cls):
        start_time = time.time()
        if not BASELINE_FILE.exists():
            raise FileNotFoundError(f"Arquivo de linha de base não encontrado: {BASELINE_FILE}")
        cls.baseline_sha = BASELINE_FILE.read_text(encoding="utf-8").strip()
        if not cls.baseline_sha:
            raise ValueError("Linha de base está vazia em gate_baseline.txt")

        # 1. Cria repositório git temporário e HOME isolado para hermeticidade (Y3)
        cls.diff_repo = tempfile.mkdtemp(prefix="ceh_diff_repo_")
        subprocess.run(["git", "init", "-q", "-b", "dev", cls.diff_repo], check=True)
        cls.diff_home = tempfile.mkdtemp(prefix="ceh_diff_home_")

        # 2. Carrega todas as fontes de comandos (Y1)
        corpus_cmds = load_corpus_commands(CORPUS_FILE)
        battery_cmds = load_battery_commands(BATTERY_FILE)
        fuzz_cmds = generate_grammar_commands(seed=42, target_unique=3500)

        cls.all_commands = sorted(list(set(corpus_cmds + battery_cmds + fuzz_cmds)))
        if len(cls.all_commands) < 3000:
            raise ValueError(f"Menos de 3000 comandos únicos a avaliar: {len(cls.all_commands)}")

        # 3. Extrai scripts da linha de base hermeticamente via git archive
        cls.baseline_dir = tempfile.mkdtemp(prefix="ceh_diff_baseline_")
        archive_cmd = f"git archive {cls.baseline_sha} clearer-engineering/scripts | tar -x -C '{cls.baseline_dir}'"
        proc = subprocess.run(["bash", "-c", archive_cmd], cwd=REPO_ROOT, capture_output=True, text=True)
        if proc.returncode != 0:
            shutil.rmtree(cls.baseline_dir, ignore_errors=True)
            raise RuntimeError(f"Falha ao extrair baseline {cls.baseline_sha}: {proc.stderr}")

        baseline_scripts = str(Path(cls.baseline_dir) / "clearer-engineering" / "scripts")

        # 4. Avalia baseline e gate atual em workers isolados com cwd e HOME temporários (Y3)
        worker_code = """
import sys, json
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from importlib import import_module
gate = import_module('safety-gate')
cmds = json.load(sys.stdin)
results = {}
for cmd in cmds:
    for env in ('development', 'staging', 'production'):
        dec, reason, env_res, uc = gate.evaluate_command(cmd, explicit_env=env)
        is_cat = (uc == 'CATASTROPHIC') or ('CATASTROPHIC' in reason)
        results[f'{env}|{cmd}'] = [dec, is_cat, uc]
json.dump(results, sys.stdout)
"""
        worker_env = dict(os.environ)
        worker_env["HOME"] = cls.diff_home

        # Avaliação da baseline
        b_proc = subprocess.Popen(
            [sys.executable, "-c", worker_code, baseline_scripts],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=cls.diff_repo,
            env=worker_env,
        )
        b_stdout, b_stderr = b_proc.communicate(input=json.dumps(cls.all_commands))
        if b_proc.returncode != 0:
            shutil.rmtree(cls.baseline_dir, ignore_errors=True)
            raise RuntimeError(f"Falha na execução do worker da baseline: {b_stderr}")
        cls.baseline_results = json.loads(b_stdout)

        # Avaliação do gate atual
        c_proc = subprocess.Popen(
            [sys.executable, "-c", worker_code, str(SCRIPTS_DIR)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=cls.diff_repo,
            env=worker_env,
        )
        c_stdout, c_stderr = c_proc.communicate(input=json.dumps(cls.all_commands))
        if c_proc.returncode != 0:
            raise RuntimeError(f"Falha na execução do worker do gate atual: {c_stderr}")
        cls.current_results = json.loads(c_stdout)

        elapsed = time.time() - start_time
        # Orçamento de tempo informativo (Y2)
        print(f"[differential-fuzz] Preparação e avaliação ({len(cls.all_commands) * 3} casos) concluídas em {elapsed:.2f}s (meta < 20s)")

    @classmethod
    def tearDownClass(cls):
        if cls.baseline_dir and os.path.exists(cls.baseline_dir):
            shutil.rmtree(cls.baseline_dir, ignore_errors=True)
        if cls.diff_repo and os.path.exists(cls.diff_repo):
            shutil.rmtree(cls.diff_repo, ignore_errors=True)
        if cls.diff_home and os.path.exists(cls.diff_home):
            shutil.rmtree(cls.diff_home, ignore_errors=True)

    def test_differential_fuzz_against_baseline(self):
        """Compara todas as decisões contra a linha de base e falha em relaxamento não listado."""
        authorized = load_authorized_relaxations(RELAXATIONS_FILE)
        rank = {"deny": 3, "ask": 2, "allow": 1}

        unauthorized_relaxations: list[str] = []
        authorized_count = 0
        tightenings_count = 0
        identical_count = 0

        for key, (cur_dec, cur_cat, cur_uc) in self.current_results.items():
            old_dec, old_cat, old_uc = self.baseline_results[key]
            env, cmd = key.split("|", 1)

            is_relax = False
            de_para = ""
            if rank[cur_dec] < rank[old_dec]:
                is_relax = True
                de_para = f"{old_dec}->{cur_dec}"
            elif old_cat and not cur_cat:
                is_relax = True
                de_para = f"deny(catastrophic)->{cur_dec}" if old_dec == cur_dec else f"{old_dec}->{cur_dec}"

            if is_relax:
                if (env, cmd, de_para) in authorized:
                    authorized_count += 1
                else:
                    unauthorized_relaxations.append(f"{env}|{cmd}|{de_para}")
            elif rank[cur_dec] > rank[old_dec] or (not old_cat and cur_cat):
                tightenings_count += 1
            else:
                identical_count += 1

        if unauthorized_relaxations:
            msg = (
                f"\n[REPROVADO - PR-QA-A] {len(unauthorized_relaxations)} relaxamento(s) NÃO autorizados detectados "
                f"contra a linha de base {self.baseline_sha}!\n"
                f"Para autorizar um relaxamento decorrente de correção homologada, adicione a(s) linha(s) abaixo em "
                f"tests/fixtures/relaxamentos_justificados.txt com o respectivo ID do achado:\n\n"
            )
            for r in unauthorized_relaxations[:20]:
                msg += f"  {r}|<ID-DO-ACHADO>\n"
            if len(unauthorized_relaxations) > 20:
                msg += f"  ... e mais {len(unauthorized_relaxations) - 20} relaxamento(s).\n"
            self.fail(msg)

        total_evals = len(self.current_results)
        self.assertEqual(identical_count + tightenings_count + authorized_count, total_evals)


if __name__ == "__main__":
    unittest.main()
