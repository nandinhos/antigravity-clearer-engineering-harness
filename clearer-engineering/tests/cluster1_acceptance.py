#!/usr/bin/env python3
"""
Suíte de aceite do Cluster 1 (R1, R2, R5) e dos contratos T1–T5 do Handoff 003.
Roda apenas em fixtures descartáveis; nunca executa push.
"""
import subprocess
import json
import tempfile
import shutil
from pathlib import Path

repo_root = Path(__file__).resolve().parents[2]
gate_script = repo_root / "clearer-engineering/scripts/safety-gate.py"
runner_script = repo_root / "clearer-engineering/scripts/test-runner.sh"

def run_gate(cmd: str, env: str = "development", cwd: Path = repo_root) -> tuple[int, dict]:
    proc = subprocess.run(
        ["python3", str(gate_script), "--check", cmd, "--env", env],
        cwd=cwd, capture_output=True, text=True
    )
    try:
        data = json.loads(proc.stdout)
    except Exception:
        data = {"raw": proc.stdout, "stderr": proc.stderr}
    return proc.returncode, data

def run_runner(cwd: Path, cmd: str | None = None) -> subprocess.CompletedProcess:
    args = ["bash", str(runner_script)] + ([cmd] if cmd else [])
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True)

def read_cert(cwd: Path) -> dict:
    return json.loads((cwd / ".ceh" / "last-ci-run.json").read_text())

def commit_all(cwd: Path, msg: str) -> None:
    subprocess.run(["git", "add", "-A", "--", ".", ":!.ceh/last-ci-run.json"], cwd=cwd, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-q", "-m", msg], cwd=cwd, check=True, capture_output=True)

def write_unittest_suite(cwd: Path, passing: bool) -> None:
    (cwd / ".gitignore").write_text("__pycache__/\n")
    test_dir = cwd / "tests"
    test_dir.mkdir(parents=True, exist_ok=True)
    (test_dir / "__init__.py").write_text("")
    (test_dir / "test_smoke.py").write_text(
        "import unittest\nclass SmokeTest(unittest.TestCase):\n    def test_ok(self):\n        self.assertTrue(%s)\n" % passing
    )


def create_git_fixture(with_ci: bool = True, multi_job: bool = False) -> tuple[Path, str]:
    tmp = Path(tempfile.mkdtemp(prefix="ceh_accept_fix_"))
    ci_dir = tmp / "repo"
    ci_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init"], cwd=ci_dir, check=True, capture_output=True)
    subprocess.run(["git", "branch", "-M", "dev"], cwd=ci_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Acceptance Tester"], cwd=ci_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "tester@example.invalid"], cwd=ci_dir, check=True, capture_output=True)

    wf = ci_dir / ".github" / "workflows"
    if multi_job:
        wf.mkdir(parents=True, exist_ok=True)
        (wf / "ci.yml").write_text("""name: CI Multi-Job
on: push
jobs:
  unit-test:
    runs-on: ubuntu-latest
    steps:
      - run: npm run test:unit
  lint-check:
    runs-on: ubuntu-latest
    steps:
      - run: npm run test:lint
""")
        ceh_cfg = ci_dir / ".ceh"
        ceh_cfg.mkdir(parents=True, exist_ok=True)
        (ceh_cfg / "config.json").write_text(json.dumps({
            "canonical_test_command": "npm test"
        }))
        (ci_dir / "test_unit.js").write_text('require("assert").strictEqual(1+1, 2);\n')
        (ci_dir / "test_lint.js").write_text('require("assert").strictEqual(typeof 42, "number");\n')
        (ci_dir / "package.json").write_text(json.dumps({
            "name": "multi-job-fixture",
            "scripts": {
                "test:unit": "node test_unit.js",
                "test:lint": "node test_lint.js",
                "test": "npm run test:unit && npm run test:lint"
            }
        }))
    elif with_ci:
        wf.mkdir(parents=True, exist_ok=True)
        (wf / "ci.yml").write_text("name: ci\non: push\n")

    (ci_dir / "README.md").write_text("# Test Repo\n")
    subprocess.run(["git", "add", "."], cwd=ci_dir, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=ci_dir, check=True, capture_output=True)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ci_dir, text=True).strip()
    return ci_dir, head

def main():
    print("=" * 60)
    print("VALIDAÇÃO DO CLUSTER 1 (R1, R2, R5) E CONTRATOS T1–T5")
    print("=" * 60)

    results = []

    # -------------------------------------------------------------
    # R1: Operadores Compostos e Lexer FSM
    # -------------------------------------------------------------
    # R1.1
    c1 = "rm -rf scratch/cache; php artisan " + "migrate:fresh" + " --env=production"
    ret, out = run_gate(c1, env="production")
    passed = (ret == 2 and out.get("decision") == "deny" and out.get("use_case") in ("DATABASE", "FILESYSTEM"))
    results.append(("R1.1", "Composto com ;", passed, ret, out.get("decision")))

    # R1.2
    c2 = "rm -rf scratch/cache && php artisan " + "migrate:fresh" + " --env=production"
    ret, out = run_gate(c2, env="production")
    passed = (ret == 2 and out.get("decision") == "deny" and out.get("use_case") in ("DATABASE", "FILESYSTEM"))
    results.append(("R1.2", "Composto com &&", passed, ret, out.get("decision")))

    # R1.3
    c3 = "false || rm -rf scratch/cache; php artisan " + "migrate:fresh" + " --env=production"
    ret, out = run_gate(c3, env="production")
    passed = (ret == 2 and out.get("decision") == "deny" and out.get("use_case") in ("DATABASE", "FILESYSTEM"))
    results.append(("R1.3", "Composto com ||", passed, ret, out.get("decision")))

    # R1.4
    c4 = "rm -rf scratch/cache & php artisan " + "migrate:fresh" + " --env=production"
    ret, out = run_gate(c4, env="production")
    passed = (ret == 2 and out.get("decision") == "deny" and out.get("use_case") in ("DATABASE", "FILESYSTEM"))
    results.append(("R1.4", "Composto com & isolado", passed, ret, out.get("decision")))

    # R1.5
    c5 = "rm -rf scratch/cache; ph''p artisan " + "migrate:fresh" + " --env=production"
    ret, out = run_gate(c5, env="production")
    passed = (ret == 2 and out.get("decision") == "deny" and out.get("use_case") in ("DATABASE", "FILESYSTEM"))
    results.append(("R1.5", "Ofuscação com aspas vazias", passed, ret, out.get("decision")))

    # R1.6
    c6 = "p$'h'p artisan " + "migrate:fresh" + " --env=production"
    ret, out = run_gate(c6, env="production")
    passed = (ret == 2 and out.get("decision") == "deny")
    results.append(("R1.6", "Fail-Closed ANSI-C quoting", passed, ret, out.get("decision")))

    # R1.7
    c7 = "rm -rf scratch/cache; rm -rf tmp/cache"
    ret, out = run_gate(c7, env="development")
    passed = (ret == 0 and out.get("decision") == "allow" and out.get("use_case") == "FILESYSTEM_SAFE")
    results.append(("R1.7", "Composto 100% seguro em dev", passed, ret, out.get("decision")))

    # R1.8
    c8 = 'rm -rf scratch/cache; "php artisan ' + 'migrate:fresh' + ' --env=production'
    ret, out = run_gate(c8, env="production")
    passed = (ret == 2 and out.get("decision") == "deny")
    results.append(("R1.8", "Fail-Closed aspas não balanceadas", passed, ret, out.get("decision")))

    # R1.9: Quebra de linha (\n) como separador de instrução
    c9 = "rm -rf scratch/cache\nphp artisan " + "migrate:fresh" + " --env=production"
    ret, out = run_gate(c9, env="production")
    passed = (ret == 2 and out.get("decision") == "deny" and out.get("use_case") in ("DATABASE", "FILESYSTEM"))
    results.append(("R1.9", "Composto com quebra de linha \\n", passed, ret, out.get("decision")))

    # R1.10: Subshell dentro de aspas duplas (Fail-Closed)
    c10 = 'rm -rf scratch/cache "$(php artisan ' + 'migrate:fresh' + ' --env=production)"'
    ret, out = run_gate(c10, env="production")
    passed = (ret == 2 and out.get("decision") == "deny")
    results.append(("R1.10", "Fail-Closed subshell em aspas duplas", passed, ret, out.get("decision")))

    # R1.11: Expansão de parâmetro ${} dentro de aspas duplas (Fail-Closed)
    c11 = 'rm -rf scratch/cache "${VAR}"'
    ret, out = run_gate(c11, env="production")
    passed = (ret == 2 and out.get("decision") == "deny")
    results.append(("R1.11", "Fail-Closed expansão de parâmetro ${}", passed, ret, out.get("decision")))

    # R1.12: Continuação de linha (line continuation \ + newline)
    c12 = "php artis\\\nan " + "migrate:fresh" + " --env=production"
    ret, out = run_gate(c12, env="production")
    passed = (ret == 2 and out.get("decision") == "deny" and out.get("use_case") == "PARSER_FAIL_CLOSED")
    results.append(("R1.12", "Fail-Closed line continuation (\\ + LF)", passed, ret, out.get("decision")))

    # -------------------------------------------------------------
    # R2: Governança de CI e Pre-Push CI Gate
    # -------------------------------------------------------------
    fix_dir, head = create_git_fixture(with_ci=True)
    ceh_dir = fix_dir / ".ceh"
    ceh_dir.mkdir(parents=True, exist_ok=True)

    # R2.1: Comando arbitrário true
    (ceh_dir / "last-ci-run.json").write_text(json.dumps({
        "commit_hash": head, "status": "PASS", "exit_code": 0,
        "command": "true", "normalized_runner": "true", "canonical_verified": False
    }))
    ret, out = run_gate("git push origin dev", env="development", cwd=fix_dir)
    passed = (ret == 2 and out.get("decision") == "deny")
    results.append(("R2.1", "Push bloqueado por comando arbitrário", passed, ret, out.get("decision")))

    # R2.2: Wrapper rtk com comando arbitrário
    (ceh_dir / "last-ci-run.json").write_text(json.dumps({
        "commit_hash": head, "status": "PASS", "exit_code": 0,
        "command": "rtk true", "normalized_runner": "rtk true", "canonical_verified": False
    }))
    ret, out = run_gate("git push origin dev", env="development", cwd=fix_dir)
    passed = (ret == 2 and out.get("decision") == "deny")
    results.append(("R2.2", "Push bloqueado por wrapper rtk arbitrário", passed, ret, out.get("decision")))

    # R2.3: Certificado inexistente
    (ceh_dir / "last-ci-run.json").unlink(missing_ok=True)
    ret, out = run_gate("git push origin dev", env="development", cwd=fix_dir)
    passed = (ret == 2 and out.get("decision") == "deny")
    results.append(("R2.3", "Push bloqueado por certificado inexistente", passed, ret, out.get("decision")))

    # R2.4: Certificado sem commit_hash
    (ceh_dir / "last-ci-run.json").write_text(json.dumps({
        "status": "PASS", "exit_code": 0, "command": "phpunit", "canonical_verified": True
    }))
    ret, out = run_gate("git push origin dev", env="development", cwd=fix_dir)
    passed = (ret == 2 and out.get("decision") == "deny")
    results.append(("R2.4", "Push bloqueado por falta de commit_hash", passed, ret, out.get("decision")))

    # R2.5: Descompasso de commit hash
    (ceh_dir / "last-ci-run.json").write_text(json.dumps({
        "commit_hash": "deadbeef1234567890abcdef1234567890abcdef",
        "status": "PASS", "exit_code": 0, "command": "phpunit", "canonical_verified": True
    }))
    ret, out = run_gate("git push origin dev", env="development", cwd=fix_dir)
    passed = (ret == 2 and out.get("decision") == "deny")
    results.append(("R2.5", "Push bloqueado por descompasso de commit", passed, ret, out.get("decision")))

    # R2.6: Push liberado por suíte canônica aprovada
    (ceh_dir / "last-ci-run.json").write_text(json.dumps({
        "commit_hash": head, "status": "PASS", "exit_code": 0,
        "command": "phpunit", "normalized_runner": "phpunit", "canonical_verified": True
    }))
    ret, out = run_gate("git push origin dev", env="development", cwd=fix_dir)
    passed = (ret == 0 and out.get("decision") == "allow")
    results.append(("R2.6", "Push liberado por suíte canônica aprovada", passed, ret, out.get("decision")))

    # R2.7: E2E Runner -> Gate com aprovação real, comando canônico declarado no config
    write_unittest_suite(fix_dir, passing=True)
    (ceh_dir / "config.json").write_text(json.dumps({"canonical_test_command": "python3 -m unittest discover tests"}))
    commit_all(fix_dir, "add real unittest test")
    run_proc = run_runner(fix_dir, "python3 -m unittest discover tests")
    cert_e2e = read_cert(fix_dir)
    runner_ok = (run_proc.returncode == 0 and cert_e2e.get("status") == "PASS" and cert_e2e.get("canonical_verified") is True)
    ret, out = run_gate("git push origin dev", env="development", cwd=fix_dir)
    passed = (runner_ok and ret == 0 and out.get("decision") == "allow")
    results.append(("R2.7", "E2E Runner -> Gate real sem edição manual", passed, ret, out.get("decision")))

    # T1 (G2): worktree sujo não certifica, nem com arquivo rastreado nem com untracked
    (ceh_dir / "last-ci-run.json").unlink(missing_ok=True)
    (fix_dir / "README.md").write_text("# Alterado sem commit\n")
    run_dirty = run_runner(fix_dir)
    tracked_ok = (run_dirty.returncode == 0 and not (ceh_dir / "last-ci-run.json").exists())
    subprocess.run(["git", "checkout", "-q", "README.md"], cwd=fix_dir, check=True)
    (fix_dir / "tests" / "test_novo.py").write_text("import unittest\n")
    run_untracked = run_runner(fix_dir)
    untracked_ok = (run_untracked.returncode == 0 and not (ceh_dir / "last-ci-run.json").exists())
    (fix_dir / "tests" / "test_novo.py").unlink()
    ret, out = run_gate("git push origin dev", env="development", cwd=fix_dir)
    passed = (tracked_ok and untracked_ok and ret == 2 and out.get("decision") == "deny")
    results.append(("T1", "Worktree sujo (rastreado e untracked) não certifica", passed, ret, out.get("decision")))

    # T2 (G3): force push sem certificado não pula o gate de CI em development
    t2_ok = True
    for force_cmd in ("git push -f origin dev", "git push --force-with-lease origin dev", "git push origin +dev"):
        ret, out = run_gate(force_cmd, env="development", cwd=fix_dir)
        t2_ok = t2_ok and ret == 2 and out.get("decision") == "deny" and out.get("use_case") == "PRE_PUSH_CI"
    results.append(("T2", "Force push sem certificado bloqueado pelo gate de CI", t2_ok, ret, out.get("decision")))

    # T3 (G4): comando canônico com aspas gera certificado JSON válido
    quoted_cmd = """python3 -c 'print("ok \\"aspas\\" $HOME")'"""
    (ceh_dir / "config.json").write_text(json.dumps({"canonical_test_command": quoted_cmd}))
    commit_all(fix_dir, "config com aspas")
    run_quoted = run_runner(fix_dir)
    try:
        cert_q = read_cert(fix_dir)
        json_ok = (cert_q.get("normalized_runner") == quoted_cmd and cert_q.get("canonical_verified") is True)
    except Exception:
        json_ok = False
    passed = (run_quoted.returncode == 0 and json_ok)
    results.append(("T3", "Comando com aspas gera certificado JSON válido", passed, run_quoted.returncode, "cert-json" if json_ok else "invalido"))

    # T4: sem config, alvo parcial difere do comando auto-detectado e não certifica
    (ceh_dir / "config.json").unlink()
    (fix_dir / "pytest.ini").write_text("[pytest]\n")
    (fix_dir / "requirements.txt").write_text("")
    commit_all(fix_dir, "auto-detecção python sem config")
    run_partial_py = run_runner(fix_dir, "python3 -m unittest tests.test_smoke")
    cert_p = read_cert(fix_dir)
    ret, out = run_gate("git push origin dev", env="development", cwd=fix_dir)
    passed = (run_partial_py.returncode == 0 and cert_p.get("canonical_verified") is False and ret == 2 and out.get("decision") == "deny")
    results.append(("T4", "Alvo parcial sem config não certifica", passed, ret, out.get("decision")))

    # T5: sem argumentos, o comando auto-detectado certifica
    run_auto = run_runner(fix_dir)
    cert_a = read_cert(fix_dir)
    ret, out = run_gate("git push origin dev", env="development", cwd=fix_dir)
    passed = (run_auto.returncode == 0 and cert_a.get("canonical_verified") is True and ret == 0 and out.get("decision") == "allow")
    results.append(("T5", "Comando auto-detectado certifica", passed, ret, out.get("decision")))

    # R2.8: Push bloqueado por suíte parcial em CI multi-job
    shutil.rmtree(fix_dir.parent)
    fix_mj, head_mj = create_git_fixture(with_ci=True, multi_job=True)
    ceh_mj = fix_mj / ".ceh"
    run_partial = run_runner(fix_mj, "npm run test:unit")
    cert_part = read_cert(fix_mj)
    ret, out = run_gate("git push origin dev", env="development", cwd=fix_mj)
    passed = (cert_part.get("canonical_verified") is False and ret == 2 and out.get("decision") == "deny")
    results.append(("R2.8", "Push bloqueado por suíte parcial em CI multi-job", passed, ret, out.get("decision")))

    # R2.9: E2E agregador; falha real em um job bloqueia, correção commitada libera
    (fix_mj / "test_lint.js").write_text('require("assert").strictEqual(1, 2);\n')
    commit_all(fix_mj, "quebra lint")
    run_fail_proc = run_runner(fix_mj, "npm test")
    cert_fail = read_cert(fix_mj)
    ret_fail, out_fail = run_gate("git push origin dev", env="development", cwd=fix_mj)
    falsification_ok = (run_fail_proc.returncode != 0 and cert_fail.get("status") == "FAIL" and ret_fail == 2 and out_fail.get("decision") == "deny")
    (fix_mj / "test_lint.js").write_text('require("assert").strictEqual(typeof 42, "number");\n')
    commit_all(fix_mj, "corrige lint")
    run_mj_proc = run_runner(fix_mj, "npm test")
    cert_mj = read_cert(fix_mj)
    runner_mj_ok = (run_mj_proc.returncode == 0 and cert_mj.get("status") == "PASS" and cert_mj.get("canonical_verified") is True)
    ret, out = run_gate("git push origin dev", env="development", cwd=fix_mj)
    passed = (falsification_ok and runner_mj_ok and ret == 0 and out.get("decision") == "allow")
    results.append(("R2.9", "E2E Runner -> Gate agregador com falha induzida", passed, ret, out.get("decision")))

    # R2.10: config corrompido faz o runner não certificar e o gate negar
    (ceh_mj / "config.json").write_text("{ malformed json invalid syntax ...")
    commit_all(fix_mj, "config corrompido")
    run_runner(fix_mj, "npm test")
    cert_bad = read_cert(fix_mj)
    ret, out = run_gate("git push origin dev", env="development", cwd=fix_mj)
    passed = (cert_bad.get("canonical_verified") is False and ret == 2 and out.get("decision") == "deny")
    results.append(("R2.10", "Config corrompido não certifica", passed, ret, out.get("decision")))

    # R2.11: Push bloqueado por tentativa de mascarar falha com operador composto (npm test || true)
    (ceh_mj / "config.json").write_text(json.dumps({"canonical_test_command": "npm test"}))
    commit_all(fix_mj, "restaura config")
    run_runner(fix_mj, "npm test || true")
    cert_mask = read_cert(fix_mj)
    ret, out = run_gate("git push origin dev", env="development", cwd=fix_mj)
    passed = (cert_mask.get("canonical_verified") is False and ret == 2 and out.get("decision") == "deny")
    results.append(("R2.11", "Push bloqueado por mascaramento de erro (npm test || true)", passed, ret, out.get("decision")))

    # R2.12: Push bloqueado por execução parcial de testes (pytest com arquivo específico)
    (fix_mj / "test_one.py").write_text("def test_dummy(): pass\n")
    commit_all(fix_mj, "adiciona test_one")
    run_runner(fix_mj, "pytest test_one.py")
    cert_partial = read_cert(fix_mj)
    ret, out = run_gate("git push origin dev", env="development", cwd=fix_mj)
    passed = (cert_partial.get("canonical_verified") is False and ret == 2 and out.get("decision") == "deny")
    results.append(("R2.12", "Push bloqueado por execução parcial (pytest test_one.py)", passed, ret, out.get("decision")))
    shutil.rmtree(fix_mj.parent)

    # -------------------------------------------------------------
    # R5: Flags do Git (-C) e Resolução de Repositório Alvo
    # -------------------------------------------------------------
    fix_r5, head_r5 = create_git_fixture(with_ci=True)
    sub_dir = fix_r5 / "src" / "deep"
    sub_dir.mkdir(parents=True, exist_ok=True)
    ceh_r5 = fix_r5 / ".ceh"
    ceh_r5.mkdir(parents=True, exist_ok=True)
    (ceh_r5 / "last-ci-run.json").unlink(missing_ok=True)

    # R5.1: git -C sem cert bloqueado
    cmd = f"git -C {fix_r5} push origin dev"
    ret, out = run_gate(cmd, env="development", cwd=repo_root)
    passed = (ret == 2 and out.get("decision") == "deny")
    results.append(("R5.1", "git -C sem cert bloqueado no repo alvo", passed, ret, out.get("decision")))

    # R5.2: git -C com espaços
    space_tmp = Path(tempfile.mkdtemp(prefix="ceh space dir"))
    space_repo = space_tmp / "my repo"
    shutil.copytree(fix_r5, space_repo)
    cmd = f'git -C "{space_repo}" push origin dev'
    ret, out = run_gate(cmd, env="development", cwd=repo_root)
    passed = (ret == 2 and out.get("decision") == "deny")
    results.append(("R5.2", "git -C com caminho contendo espaços", passed, ret, out.get("decision")))
    shutil.rmtree(space_tmp)

    # R5.3: múltiplos -C cumulativos
    parent_p = fix_r5.parent
    rel_p = fix_r5.name
    cmd = f"git -C {parent_p} -C {rel_p} push origin dev"
    ret, out = run_gate(cmd, env="development", cwd=repo_root)
    passed = (ret == 2 and out.get("decision") == "deny")
    results.append(("R5.3", "git -C múltiplos caminhos cumulativos", passed, ret, out.get("decision")))

    # R5.4: git -C apontando para subdiretório sem cert
    cmd = f"git -C {sub_dir} push origin dev"
    ret, out = run_gate(cmd, env="development", cwd=repo_root)
    passed = (ret == 2 and out.get("decision") == "deny")
    results.append(("R5.4", "git -C para subdiretório sem cert", passed, ret, out.get("decision")))

    # R5.5: git -C apontando para subdiretório com cert válido na raiz
    (ceh_r5 / "last-ci-run.json").write_text(json.dumps({
        "commit_hash": head_r5, "status": "PASS", "exit_code": 0,
        "command": "pytest", "normalized_runner": "pytest", "canonical_verified": True
    }))
    cmd = f"git -C {sub_dir} push origin dev"
    ret, out = run_gate(cmd, env="development", cwd=repo_root)
    passed = (ret == 0 and out.get("decision") == "allow")
    results.append(("R5.5", "git -C para subdiretório com cert válido na raiz", passed, ret, out.get("decision")))

    # R5.6: git -C com cert válido na raiz
    cmd = f"git -C {fix_r5} push origin dev"
    ret, out = run_gate(cmd, env="development", cwd=repo_root)
    passed = (ret == 0 and out.get("decision") == "allow")
    results.append(("R5.6", "git -C com cert válido na raiz", passed, ret, out.get("decision")))

    # R5.7: git -C com force push bloqueado em produção
    force_flag = "--" + "force"
    cmd = f"git -C {fix_r5} push origin dev {force_flag}"
    ret, out = run_gate(cmd, env="production", cwd=repo_root)
    passed = (ret == 2 and out.get("decision") == "deny" and out.get("use_case") == "GIT_HISTORY")
    results.append(("R5.7", "git -C com force push bloqueado em produção", passed, ret, out.get("decision")))

    # R5.8: Fail-Closed para opção global Git não homologada
    cmd = "git --git-dir=/tmp/outro.git push origin dev"
    ret, out = run_gate(cmd, env="development", cwd=repo_root)
    passed = (ret == 2 and out.get("decision") == "deny" and out.get("use_case") == "GIT_DESTRUCTIVE")
    results.append(("R5.8", "Opção global Git não homologada (--git-dir)", passed, ret, out.get("decision")))

    shutil.rmtree(fix_r5.parent)

    print("\nRESULTADOS DETALHADOS:")
    total_passed = 0
    for cid, desc, p, ret, dec in results:
        status_label = "PASS" if p else "FAIL"
        if p: total_passed += 1
        print(f"[{status_label}] {cid}: {desc:45} -> Exit: {ret} | Decision: {dec}")

    print("=" * 60)
    print(f"TOTAL: {total_passed}/{len(results)} PASSARAM")
    print("=" * 60)

    EXPECTED_TOTAL_SCENARIOS = 37

    assert len(results) == EXPECTED_TOTAL_SCENARIOS, f"Matriz deve conter exatamente {EXPECTED_TOTAL_SCENARIOS} cenários, mas contém {len(results)}."
    assert total_passed == EXPECTED_TOTAL_SCENARIOS, f"Esperado {EXPECTED_TOTAL_SCENARIOS} aprovados, mas obtido {total_passed}."

    print(f"TODOS OS {EXPECTED_TOTAL_SCENARIOS} CENÁRIOS FORAM VALIDADOS COM SUCESSO!")
    return 0

if __name__ == "__main__":
    exit(main())
