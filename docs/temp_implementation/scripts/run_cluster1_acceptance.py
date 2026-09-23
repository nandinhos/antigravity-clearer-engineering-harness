#!/usr/bin/env python3
"""
Validador Automatizado de Aceite do Cluster 1 (P0: R1, R2, R5)
Executa os 58 dry-runs formais do Handoff 002 e reporta o resultado de cada um.
"""
import subprocess
import json
import tempfile
import shutil
from pathlib import Path

repo_root = Path("/home/nandodev/projects/clearer-engineering-harness")
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
    print("INICIANDO VALIDAÇÃO DOS 58 CENÁRIOS DO CLUSTER 1 (P0)")
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

    # R2.7: E2E Runner -> Gate com aprovacao real (Zero edicao manual)
    test_dir = fix_dir / "tests"
    test_dir.mkdir(parents=True, exist_ok=True)
    (test_dir / "__init__.py").write_text("")
    (test_dir / "test_smoke.py").write_text("""import unittest
class SmokeTest(unittest.TestCase):
    def test_ok(self):
        self.assertTrue(True)
""")
    subprocess.run(["git", "add", "."], cwd=fix_dir, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "add real unittest test"], cwd=fix_dir, check=True, capture_output=True)

    # Executa o runner real com python3 -m unittest
    run_proc = subprocess.run(
        ["bash", str(runner_script), "python3 -m unittest discover tests"],
        cwd=fix_dir, capture_output=True, text=True
    )
    # Lemos o certificado gerado de forma 100% autêntica pelo runner
    cert_e2e = json.loads((ceh_dir / "last-ci-run.json").read_text())
    runner_ok = (run_proc.returncode == 0 and cert_e2e.get("status") == "PASS" and cert_e2e.get("canonical_verified") is True)

    ret, out = run_gate("git push origin dev", env="development", cwd=fix_dir)
    passed = (runner_ok and ret == 0 and out.get("decision") == "allow")
    results.append(("R2.7", "E2E Runner -> Gate real sem edição manual", passed, ret, out.get("decision")))

    # R2.8: Push bloqueado por suíte parcial em CI multi-job
    shutil.rmtree(fix_dir.parent)
    fix_mj, head_mj = create_git_fixture(with_ci=True, multi_job=True)
    ceh_mj = fix_mj / ".ceh"

    # Executa a suíte parcial (apenas unit tests)
    run_partial = subprocess.run(
        ["bash", str(runner_script), "npm run test:unit"],
        cwd=fix_mj, capture_output=True, text=True
    )
    ret, out = run_gate("git push origin dev", env="development", cwd=fix_mj)
    passed = (
        ret == 2
        and out.get("decision") == "deny"
        and ("parcial" in out.get("reason", "").lower() or "não cobre os jobs" in out.get("reason", "").lower())
    )
    results.append(("R2.8", "Push bloqueado por suíte parcial em CI multi-job", passed, ret, out.get("decision")))

    # R2.9: E2E Runner -> Gate com suíte agregadora demonstrando correspondência com os jobs da CI (Zero edição manual)
    # 1. Comprova que os jobs declarados na CI (unit-test e lint-check) são mapeados pelo agregador
    ci_yaml = (fix_mj / ".github" / "workflows" / "ci.yml").read_text()
    assert "npm run test:unit" in ci_yaml and "npm run test:lint" in ci_yaml, "CI deve declarar test:unit e test:lint"
    pkg_json = json.loads((fix_mj / "package.json").read_text())
    assert "test:unit" in pkg_json["scripts"]["test"] and "test:lint" in pkg_json["scripts"]["test"], "Agregador deve invocar ambos os jobs"

    # 2. Contraexemplo / Falsificação: Se um job individual da CI falhar no agregador, o gate DEVE bloquear o push
    import copy
    (fix_mj / "test_lint.js").write_text('require("assert").strictEqual(1, 2);\n')
    run_fail_proc = subprocess.run(
        ["bash", str(runner_script), "npm test"],
        cwd=fix_mj, capture_output=True, text=True
    )
    cert_fail = json.loads((ceh_mj / "last-ci-run.json").read_text())
    ret_fail, out_fail = run_gate("git push origin dev", env="development", cwd=fix_mj)
    falsification_ok = (run_fail_proc.returncode != 0 and cert_fail.get("status") == "FAIL" and ret_fail == 2 and out_fail.get("decision") == "deny")

    # 3. Restaura o job e executa a suíte agregadora com ambos os jobs verdes
    (fix_mj / "test_lint.js").write_text('require("assert").strictEqual(typeof 42, "number");\n')
    run_mj_proc = subprocess.run(
        ["bash", str(runner_script), "npm test"],
        cwd=fix_mj, capture_output=True, text=True
    )
    cert_mj = json.loads((ceh_mj / "last-ci-run.json").read_text())
    runner_mj_ok = (run_mj_proc.returncode == 0 and cert_mj.get("status") == "PASS" and cert_mj.get("canonical_verified") is True)

    ret, out = run_gate("git push origin dev", env="development", cwd=fix_mj)
    passed = (falsification_ok and runner_mj_ok and ret == 0 and out.get("decision") == "allow")
    results.append(("R2.9", "E2E Runner -> Gate agregador cobrindo todos os jobs da CI", passed, ret, out.get("decision")))

    # R2.10: Fail-Closed para .ceh/config.json corrompido / JSON inválido
    (ceh_mj / "config.json").write_text("{ malformed json invalid syntax ...")
    ret, out = run_gate("git push origin dev", env="development", cwd=fix_mj)
    passed = (ret == 2 and out.get("decision") == "deny" and "fail-closed" in out.get("reason", "").lower())
    results.append(("R2.10", "Fail-Closed para .ceh/config.json corrompido", passed, ret, out.get("decision")))

    # R2.11: Push bloqueado por tentativa de mascarar falha com operador composto (npm test || true)
    (ceh_mj / "config.json").write_text(json.dumps({"canonical_test_command": "npm test"}))
    run_mask = subprocess.run(
        ["bash", str(runner_script), "npm test || true"],
        cwd=fix_mj, capture_output=True, text=True
    )
    cert_mask = json.loads((ceh_mj / "last-ci-run.json").read_text())
    mask_blocked = (cert_mask.get("canonical_verified") is False)
    ret, out = run_gate("git push origin dev", env="development", cwd=fix_mj)
    passed = (mask_blocked and ret == 2 and out.get("decision") == "deny")
    results.append(("R2.11", "Push bloqueado por mascaramento de erro (npm test || true)", passed, ret, out.get("decision")))

    # R2.12: Push bloqueado por execução parcial de testes (pytest com arquivo específico)
    (fix_mj / "test_one.py").write_text("def test_dummy(): pass\n")
    run_partial_target = subprocess.run(
        ["bash", str(runner_script), "pytest test_one.py"],
        cwd=fix_mj, capture_output=True, text=True
    )
    cert_partial = json.loads((ceh_mj / "last-ci-run.json").read_text())
    partial_blocked = (cert_partial.get("canonical_verified") is False)
    ret, out = run_gate("git push origin dev", env="development", cwd=fix_mj)
    passed = (partial_blocked and ret == 2 and out.get("decision") == "deny")
    results.append(("R2.12", "Push bloqueado por execução parcial (pytest test_one.py)", passed, ret, out.get("decision")))

    # R2.13: Push bloqueado por script de pacote com mascaramento (package.json com || true)
    pkg_masked = copy.deepcopy(pkg_json)
    pkg_masked["scripts"]["test"] = "node test_unit.js || true"
    (fix_mj / "package.json").write_text(json.dumps(pkg_masked))
    (ceh_mj / "config.json").write_text(json.dumps({"canonical_test_command": "npm test"}))
    run_pkg_mask = subprocess.run(
        ["bash", str(runner_script), "npm test"],
        cwd=fix_mj, capture_output=True, text=True
    )
    cert_pkg_mask = json.loads((ceh_mj / "last-ci-run.json").read_text())
    pkg_mask_blocked = (cert_pkg_mask.get("canonical_verified") is False)
    ret, out = run_gate("git push origin dev", env="development", cwd=fix_mj)
    passed = (pkg_mask_blocked and ret == 2 and out.get("decision") == "deny")
    results.append(("R2.13", "Push bloqueado por mascaramento em script de pacote (package.json com || true)", passed, ret, out.get("decision")))

    # R2.14: Push bloqueado em Fail-Closed por comando arbitrário não canônico
    run_arbitrary = subprocess.run(
        ["bash", str(runner_script), "echo test"],
        cwd=fix_mj, capture_output=True, text=True
    )
    cert_arbitrary = json.loads((ceh_mj / "last-ci-run.json").read_text())
    arbitrary_blocked = (cert_arbitrary.get("canonical_verified") is False)
    ret, out = run_gate("git push origin dev", env="development", cwd=fix_mj)
    passed = (arbitrary_blocked and ret == 2 and out.get("decision") == "deny")
    results.append(("R2.14", "Push bloqueado em Fail-Closed por comando arbitrário", passed, ret, out.get("decision")))

    # R2.15: Push bloqueado por mascaramento via operador de negação (! false)
    pkg_neg = copy.deepcopy(pkg_json)
    pkg_neg["scripts"]["test"] = "! false"
    (fix_mj / "package.json").write_text(json.dumps(pkg_neg))
    run_neg = subprocess.run(
        ["bash", str(runner_script), "npm test"],
        cwd=fix_mj, capture_output=True, text=True
    )
    cert_neg = json.loads((ceh_mj / "last-ci-run.json").read_text())
    neg_blocked = (cert_neg.get("canonical_verified") is False)
    ret, out = run_gate("git push origin dev", env="development", cwd=fix_mj)
    passed = (neg_blocked and ret == 2 and out.get("decision") == "deny")
    results.append(("R2.15", "Push bloqueado por negação de exit code (! false)", passed, ret, out.get("decision")))

    # R2.16: Push bloqueado por mascaramento via hooks de lifecycle (pretest / posttest com ! false)
    pkg_pre = copy.deepcopy(pkg_json)
    pkg_pre["scripts"]["pretest"] = "! false"
    pkg_pre["scripts"]["test"] = "node test_unit.js"
    (fix_mj / "package.json").write_text(json.dumps(pkg_pre))
    run_pre = subprocess.run(
        ["bash", str(runner_script), "npm test"],
        cwd=fix_mj, capture_output=True, text=True
    )
    cert_pre = json.loads((ceh_mj / "last-ci-run.json").read_text())
    pre_blocked = (cert_pre.get("canonical_verified") is False)
    ret, out = run_gate("git push origin dev", env="development", cwd=fix_mj)
    passed = (pre_blocked and ret == 2 and out.get("decision") == "deny")
    results.append(("R2.16", "Push bloqueado por bypass em lifecycle hook (pretest: '! false')", passed, ret, out.get("decision")))

    # R2.17: Push bloqueado por substituição de comando/subshell no manifesto (printf com $(false))
    pkg_sub = copy.deepcopy(pkg_json)
    pkg_sub["scripts"]["test"] = "printf '%s' \"$(false)\""
    (fix_mj / "package.json").write_text(json.dumps(pkg_sub))
    run_sub = subprocess.run(
        ["bash", str(runner_script), "npm test"],
        cwd=fix_mj, capture_output=True, text=True
    )
    cert_sub = json.loads((ceh_mj / "last-ci-run.json").read_text())
    sub_blocked = (cert_sub.get("canonical_verified") is False)
    ret, out = run_gate("git push origin dev", env="development", cwd=fix_mj)
    passed = (sub_blocked and ret == 2 and out.get("decision") == "deny")
    results.append(("R2.17", "Push bloqueado por subshell no manifesto (printf $(false))", passed, ret, out.get("decision")))

    # R2.18: Push bloqueado por substituição de processo <() no manifesto
    pkg_p1 = copy.deepcopy(pkg_json)
    pkg_p1["scripts"]["test"] = "bash -c 'cat <(false)'"
    (fix_mj / "package.json").write_text(json.dumps(pkg_p1))
    run_p1 = subprocess.run(["bash", str(runner_script), "npm test"], cwd=fix_mj, capture_output=True, text=True)
    cert_p1 = json.loads((ceh_mj / "last-ci-run.json").read_text())
    p1_blocked = (cert_p1.get("canonical_verified") is False)
    ret, out = run_gate("git push origin dev", env="development", cwd=fix_mj)
    passed = (p1_blocked and ret == 2 and out.get("decision") == "deny")
    results.append(("R2.18", "Push bloqueado por substituição de processo <()", passed, ret, out.get("decision")))

    # R2.19: Push bloqueado por substituição de processo >() no manifesto
    pkg_p2 = copy.deepcopy(pkg_json)
    pkg_p2["scripts"]["test"] = "bash -c 'printf x >(false)'"
    (fix_mj / "package.json").write_text(json.dumps(pkg_p2))
    run_p2 = subprocess.run(["bash", str(runner_script), "npm test"], cwd=fix_mj, capture_output=True, text=True)
    cert_p2 = json.loads((ceh_mj / "last-ci-run.json").read_text())
    p2_blocked = (cert_p2.get("canonical_verified") is False)
    ret, out = run_gate("git push origin dev", env="development", cwd=fix_mj)
    passed = (p2_blocked and ret == 2 and out.get("decision") == "deny")
    results.append(("R2.19", "Push bloqueado por substituição de processo >()", passed, ret, out.get("decision")))

    # R2.20: Push bloqueado por substituição de processo em hook de lifecycle (pretest)
    pkg_p3 = copy.deepcopy(pkg_json)
    pkg_p3["scripts"]["pretest"] = "cat <(false)"
    pkg_p3["scripts"]["test"] = "node test_unit.js"
    (fix_mj / "package.json").write_text(json.dumps(pkg_p3))
    run_p3 = subprocess.run(["bash", str(runner_script), "npm test"], cwd=fix_mj, capture_output=True, text=True)
    cert_p3 = json.loads((ceh_mj / "last-ci-run.json").read_text())
    p3_blocked = (cert_p3.get("canonical_verified") is False)
    ret, out = run_gate("git push origin dev", env="development", cwd=fix_mj)
    passed = (p3_blocked and ret == 2 and out.get("decision") == "deny")
    results.append(("R2.20", "Push bloqueado por substituição de processo em hook pretest", passed, ret, out.get("decision")))

    # R2.21: Agregador legítimo unit && lint com testes reais e falha induzida
    # 1. Indução de falha: se o script 'test:unit' falhar em asserção real, runner e gate DEVEM bloquear
    (fix_mj / "test_unit.js").write_text('require("assert").strictEqual(1 + 1, 3);')
    (fix_mj / "test_lint.js").write_text('require("assert").strictEqual(typeof "ceh", "string");')
    pkg_p4 = copy.deepcopy(pkg_json)
    pkg_p4["scripts"] = {
        "test:unit": "node test_unit.js",
        "test:lint": "node test_lint.js",
        "test": "npm run test:unit && npm run test:lint"
    }
    (fix_mj / "package.json").write_text(json.dumps(pkg_p4))
    run_p4_fail = subprocess.run(["bash", str(runner_script), "npm test"], cwd=fix_mj, capture_output=True, text=True)
    cert_p4_fail = json.loads((ceh_mj / "last-ci-run.json").read_text())
    ret_fail, out_fail = run_gate("git push origin dev", env="development", cwd=fix_mj)
    falsification_p4 = (
        run_p4_fail.returncode != 0
        and cert_p4_fail.get("status") == "FAIL"
        and ret_fail == 2
        and out_fail.get("decision") == "deny"
    )

    # 2. Caminho feliz com testes reais passando: ambos os jobs executam asserções válidas
    (fix_mj / "test_unit.js").write_text('require("assert").strictEqual(1 + 1, 2);')
    run_p4 = subprocess.run(["bash", str(runner_script), "npm test"], cwd=fix_mj, capture_output=True, text=True)
    cert_p4 = json.loads((ceh_mj / "last-ci-run.json").read_text())
    p4_ok = (run_p4.returncode == 0 and cert_p4.get("canonical_verified") is True and cert_p4.get("status") == "PASS")
    ret, out = run_gate("git push origin dev", env="development", cwd=fix_mj)
    passed = (falsification_p4 and p4_ok and ret == 0 and out.get("decision") == "allow")
    results.append(("R2.21", "Agregador legítimo unit && lint com testes reais e falha induzida", passed, ret, out.get("decision")))

    # R2.22: Falha do validador auxiliar -> Fail-closed sem emissão de certificado canônico
    (fix_mj / "package.json").write_text('{"scripts": {"test": malformed_json_unquoted}}')
    run_aux_fail = subprocess.run(["bash", str(runner_script), "npm test"], cwd=fix_mj, capture_output=True, text=True)
    cert_aux_fail = json.loads((ceh_mj / "last-ci-run.json").read_text())
    aux_blocked = (cert_aux_fail.get("canonical_verified") is False)
    ret, out = run_gate("git push origin dev", env="development", cwd=fix_mj)
    passed = (aux_blocked and ret == 2 and out.get("decision") == "deny")
    results.append(("R2.22", "Falha do validador auxiliar -> Fail-closed sem certificado canônico", passed, ret, out.get("decision")))

    # R2.23: Push bloqueado por execução opaca de shell com wrapper (command bash -c)
    pkg_wrap = copy.deepcopy(pkg_json)
    pkg_wrap["scripts"]["test"] = "command bash -c 'exit 0'"
    (fix_mj / "package.json").write_text(json.dumps(pkg_wrap))
    run_wrap = subprocess.run(["bash", str(runner_script), "npm test"], cwd=fix_mj, capture_output=True, text=True)
    cert_wrap = json.loads((ceh_mj / "last-ci-run.json").read_text())
    wrap_blocked = (cert_wrap.get("canonical_verified") is False)
    ret, out = run_gate("git push origin dev", env="development", cwd=fix_mj)
    passed = (wrap_blocked and ret == 2 and out.get("decision") == "deny")
    results.append(("R2.23", "Push bloqueado por shell opaco com wrapper (command bash -c)", passed, ret, out.get("decision")))

    shutil.rmtree(fix_mj.parent)

    # R2.24: Bypass de alias no Composer (@test:unit -> command bash -c) bloqueado
    fix_comp, head_comp = create_git_fixture(with_ci=True)
    ceh_comp = fix_comp / ".ceh"
    ceh_comp.mkdir(parents=True, exist_ok=True)
    comp_wf = fix_comp / ".github" / "workflows"
    (comp_wf / "ci.yml").write_text("""name: CI Composer
on: push
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: composer test
""")
    (fix_comp / "composer.json").write_text(json.dumps({
        "name": "ceh/composer-alias-test",
        "scripts": {
            "test": ["@test:unit"],
            "test:unit": ["command bash -c 'exit 0'"]
        }
    }))
    run_comp = subprocess.run(["bash", str(runner_script), "composer test"], cwd=fix_comp, capture_output=True, text=True)
    cert_comp = json.loads((ceh_comp / "last-ci-run.json").read_text())
    comp_blocked_runner = (cert_comp.get("canonical_verified") is False)
    ret_comp, out_comp = run_gate("git push origin dev", env="development", cwd=fix_comp)
    # Defesa em profundidade: adulterar certificado para true e verificar se gate ainda bloqueia
    cert_comp["canonical_verified"] = True
    (ceh_comp / "last-ci-run.json").write_text(json.dumps(cert_comp))
    ret_comp_tampered, out_comp_tampered = run_gate("git push origin dev", env="development", cwd=fix_comp)
    passed = (
        comp_blocked_runner
        and ret_comp == 2 and out_comp.get("decision") == "deny"
        and ret_comp_tampered == 2 and out_comp_tampered.get("decision") == "deny"
    )
    results.append(("R2.24", "Bypass de alias no Composer (@test:unit -> command bash -c) bloqueado", passed, ret_comp, out_comp.get("decision")))
    shutil.rmtree(fix_comp.parent)

    # R2.25: Confronto CI vs Agregador: jobs da esteira não cobertos barram certificado e push
    fix_mismatch, head_mismatch = create_git_fixture(with_ci=True)
    ceh_mismatch = fix_mismatch / ".ceh"
    ceh_mismatch.mkdir(parents=True, exist_ok=True)
    mis_wf = fix_mismatch / ".github" / "workflows"
    (mis_wf / "ci.yml").write_text("""name: CI Multi-Job
on: push
jobs:
  unit:
    runs-on: ubuntu-latest
    steps:
      - run: npm run test:unit
  lint:
    runs-on: ubuntu-latest
    steps:
      - run: npm run test:lint
""")
    (fix_mismatch / "test.js").write_text('require("assert").strictEqual(1 + 1, 2);')
    (fix_mismatch / "package.json").write_text(json.dumps({
        "name": "mismatch-fixture",
        "scripts": {
            "test:unit": "node -e 'process.exit(1)'",
            "test:lint": "node -e 'process.exit(1)'",
            "test": "node test.js"
        }
    }))
    run_mis = subprocess.run(["bash", str(runner_script), "npm test"], cwd=fix_mismatch, capture_output=True, text=True)
    cert_mis = json.loads((ceh_mismatch / "last-ci-run.json").read_text())
    mis_blocked_runner = (cert_mis.get("canonical_verified") is False)
    ret_mis, out_mis = run_gate("git push origin dev", env="development", cwd=fix_mismatch)
    # Defesa em profundidade: forçar canonical_verified: true e testar se gate confronta e barra
    cert_mis["canonical_verified"] = True
    (ceh_mismatch / "last-ci-run.json").write_text(json.dumps(cert_mis))
    ret_mis_tampered, out_mis_tampered = run_gate("git push origin dev", env="development", cwd=fix_mismatch)
    passed = (
        mis_blocked_runner
        and ret_mis == 2 and out_mis.get("decision") == "deny"
        and ret_mis_tampered == 2 and out_mis_tampered.get("decision") == "deny"
    )
    results.append(("R2.25", "Confronto CI vs Agregador: jobs não cobertos barram certificado e push", passed, ret_mis, out_mis.get("decision")))
    shutil.rmtree(fix_mismatch.parent)

    # R2.26: Workflow com prefixos de ambiente em CI steps (env CI=1) interceptado
    fix_env, head_env = create_git_fixture(with_ci=True)
    ceh_env = fix_env / ".ceh"
    ceh_env.mkdir(parents=True, exist_ok=True)
    env_wf = fix_env / ".github" / "workflows"
    (env_wf / "ci.yml").write_text("""name: CI Env Prefix
on: push
jobs:
  unit:
    runs-on: ubuntu-latest
    steps:
      - run: env CI=1 npm run test:unit
  lint:
    runs-on: ubuntu-latest
    steps:
      - run: CI=true npm run test:lint
""")
    (fix_env / "test.js").write_text('require("assert").strictEqual(1 + 1, 2);')
    (fix_env / "package.json").write_text(json.dumps({
        "name": "env-prefix-fixture",
        "scripts": {
            "test:unit": "node -e 'process.exit(1)'",
            "test:lint": "node -e 'process.exit(1)'",
            "test": "node test.js"
        }
    }))
    run_env = subprocess.run(["bash", str(runner_script), "npm test"], cwd=fix_env, capture_output=True, text=True)
    cert_env = json.loads((ceh_env / "last-ci-run.json").read_text())
    env_blocked_runner = (cert_env.get("canonical_verified") is False)
    ret_env, out_env = run_gate("git push origin dev", env="development", cwd=fix_env)
    cert_env["canonical_verified"] = True
    (ceh_env / "last-ci-run.json").write_text(json.dumps(cert_env))
    ret_env_tampered, out_env_tampered = run_gate("git push origin dev", env="development", cwd=fix_env)
    passed = (
        env_blocked_runner
        and ret_env == 2 and out_env.get("decision") == "deny"
        and ret_env_tampered == 2 and out_env_tampered.get("decision") == "deny"
    )
    results.append(("R2.26", "CI step com prefixo de ambiente (env CI=1) confrontado com agregador", passed, ret_env, out_env.get("decision")))
    shutil.rmtree(fix_env.parent)

    # R2.27: Composite Actions locais chamadas por uses: (./.github/actions/...) mapeadas e exigidas
    fix_comp_act, head_comp_act = create_git_fixture(with_ci=True)
    ceh_comp_act = fix_comp_act / ".ceh"
    ceh_comp_act.mkdir(parents=True, exist_ok=True)
    act_wf = fix_comp_act / ".github" / "workflows"
    (act_wf / "ci.yml").write_text("""name: CI Composite
on: push
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: ./.github/actions/test-unit
""")
    local_act_dir = fix_comp_act / ".github" / "actions" / "test-unit"
    local_act_dir.mkdir(parents=True, exist_ok=True)
    (local_act_dir / "action.yml").write_text("""name: Test Unit Action
runs:
  using: composite
  steps:
    - run: npm run test:unit
""")
    (fix_comp_act / "test.js").write_text('require("assert").strictEqual(1 + 1, 2);')
    (fix_comp_act / "package.json").write_text(json.dumps({
        "name": "composite-action-fixture",
        "scripts": {
            "test:unit": "node -e 'process.exit(1)'",
            "test": "node test.js"
        }
    }))
    run_comp_act = subprocess.run(["bash", str(runner_script), "npm test"], cwd=fix_comp_act, capture_output=True, text=True)
    cert_comp_act = json.loads((ceh_comp_act / "last-ci-run.json").read_text())
    comp_act_blocked_runner = (cert_comp_act.get("canonical_verified") is False)
    ret_comp_act, out_comp_act = run_gate("git push origin dev", env="development", cwd=fix_comp_act)
    cert_comp_act["canonical_verified"] = True
    (ceh_comp_act / "last-ci-run.json").write_text(json.dumps(cert_comp_act))
    ret_comp_act_tampered, out_comp_act_tampered = run_gate("git push origin dev", env="development", cwd=fix_comp_act)
    passed = (
        comp_act_blocked_runner
        and ret_comp_act == 2 and out_comp_act.get("decision") == "deny"
        and ret_comp_act_tampered == 2 and out_comp_act_tampered.get("decision") == "deny"
    )
    results.append(("R2.27", "Composite Action local (uses: ./) mapeada e exigida na esteira", passed, ret_comp_act, out_comp_act.get("decision")))
    shutil.rmtree(fix_comp_act.parent)

    # R2.28: Fake-pass / no-op (node -e 'process.exit(0)') barrado no runner e no gate
    fix_fake, head_fake = create_git_fixture(with_ci=True)
    ceh_fake = fix_fake / ".ceh"
    ceh_fake.mkdir(parents=True, exist_ok=True)
    fake_wf = fix_fake / ".github" / "workflows"
    (fake_wf / "ci.yml").write_text("""name: CI Fake Pass
on: push
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: npm test
""")
    (fix_fake / "package.json").write_text(json.dumps({
        "name": "fake-pass-fixture",
        "scripts": {
            "test": "node -e 'process.exit(0)'"
        }
    }))
    run_fake = subprocess.run(["bash", str(runner_script), "npm test"], cwd=fix_fake, capture_output=True, text=True)
    cert_fake = json.loads((ceh_fake / "last-ci-run.json").read_text())
    fake_blocked_runner = (cert_fake.get("canonical_verified") is False)
    ret_fake, out_fake = run_gate("git push origin dev", env="development", cwd=fix_fake)
    cert_fake["canonical_verified"] = True
    (ceh_fake / "last-ci-run.json").write_text(json.dumps(cert_fake))
    ret_fake_tampered, out_fake_tampered = run_gate("git push origin dev", env="development", cwd=fix_fake)
    passed = (
        fake_blocked_runner
        and ret_fake == 2 and out_fake.get("decision") == "deny"
        and ret_fake_tampered == 2 and out_fake_tampered.get("decision") == "deny"
    )
    results.append(("R2.28", "Comando no-op / fake-pass (node -e 'process.exit(0)') barrado", passed, ret_fake, out_fake.get("decision")))
    shutil.rmtree(fix_fake.parent)

    # R2.29: Fake-pass via declaração com palavra-chave assert (node -e 'const assert=1') barrado
    fix_r229, head_r229 = create_git_fixture(with_ci=True)
    ceh_r229 = fix_r229 / ".ceh"
    ceh_r229.mkdir(parents=True, exist_ok=True)
    r229_wf = fix_r229 / ".github" / "workflows"
    (r229_wf / "ci.yml").write_text("""name: CI Fake Pass Assert Const
on: push
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: npm test
""")
    (fix_r229 / "package.json").write_text(json.dumps({
        "name": "fake-pass-assert-const-fixture",
        "scripts": {
            "test": "node -e 'const assert=1'"
        }
    }))
    run_r229 = subprocess.run(["bash", str(runner_script), "npm test"], cwd=fix_r229, capture_output=True, text=True)
    cert_r229 = json.loads((ceh_r229 / "last-ci-run.json").read_text())
    r229_blocked_runner = (cert_r229.get("canonical_verified") is False)
    ret_r229, out_r229 = run_gate("git push origin dev", env="development", cwd=fix_r229)
    cert_r229["canonical_verified"] = True
    (ceh_r229 / "last-ci-run.json").write_text(json.dumps(cert_r229))
    ret_r229_tampered, out_r229_tampered = run_gate("git push origin dev", env="development", cwd=fix_r229)
    passed = (
        r229_blocked_runner
        and ret_r229 == 2 and out_r229.get("decision") == "deny"
        and ret_r229_tampered == 2 and out_r229_tampered.get("decision") == "deny"
    )
    results.append(("R2.29", "Fake-pass via declaração (node -e 'const assert=1') barrado", passed, ret_r229, out_r229.get("decision")))
    shutil.rmtree(fix_r229.parent)

    # R2.30: Fake-pass via saída prematura antes de asserção (node -e 'process.exit(0), require(\"assert\").fail()') barrado
    fix_r230, head_r230 = create_git_fixture(with_ci=True)
    ceh_r230 = fix_r230 / ".ceh"
    ceh_r230.mkdir(parents=True, exist_ok=True)
    r230_wf = fix_r230 / ".github" / "workflows"
    (r230_wf / "ci.yml").write_text("""name: CI Fake Pass Early Exit
on: push
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: npm test
""")
    (fix_r230 / "package.json").write_text(json.dumps({
        "name": "fake-pass-early-exit-fixture",
        "scripts": {
            "test": "node -e 'process.exit(0), require(\"assert\").fail(\"unreachable\")'"
        }
    }))
    run_r230 = subprocess.run(["bash", str(runner_script), "npm test"], cwd=fix_r230, capture_output=True, text=True)
    cert_r230 = json.loads((ceh_r230 / "last-ci-run.json").read_text())
    r230_blocked_runner = (cert_r230.get("canonical_verified") is False)
    ret_r230, out_r230 = run_gate("git push origin dev", env="development", cwd=fix_r230)
    cert_r230["canonical_verified"] = True
    (ceh_r230 / "last-ci-run.json").write_text(json.dumps(cert_r230))
    ret_r230_tampered, out_r230_tampered = run_gate("git push origin dev", env="development", cwd=fix_r230)
    passed = (
        r230_blocked_runner
        and ret_r230 == 2 and out_r230.get("decision") == "deny"
        and ret_r230_tampered == 2 and out_r230_tampered.get("decision") == "deny"
    )
    results.append(("R2.30", "Fake-pass com saída prematura antes de asserção barrado", passed, ret_r230, out_r230.get("decision")))
    shutil.rmtree(fix_r230.parent)

    # R2.31: Execução inline opaca em Python (python3 -c 'import sys; sys.exit(0)') barrada
    fix_r231, head_r231 = create_git_fixture(with_ci=True)
    ceh_r231 = fix_r231 / ".ceh"
    ceh_r231.mkdir(parents=True, exist_ok=True)
    r231_wf = fix_r231 / ".github" / "workflows"
    (r231_wf / "ci.yml").write_text("""name: CI Fake Pass Python Inline
on: push
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: npm test
""")
    (fix_r231 / "package.json").write_text(json.dumps({
        "name": "fake-pass-python-inline-fixture",
        "scripts": {
            "test": "python3 -c 'import sys; sys.exit(0)'"
        }
    }))
    run_r231 = subprocess.run(["bash", str(runner_script), "npm test"], cwd=fix_r231, capture_output=True, text=True)
    cert_r231 = json.loads((ceh_r231 / "last-ci-run.json").read_text())
    r231_blocked_runner = (cert_r231.get("canonical_verified") is False)
    ret_r231, out_r231 = run_gate("git push origin dev", env="development", cwd=fix_r231)
    cert_r231["canonical_verified"] = True
    (ceh_r231 / "last-ci-run.json").write_text(json.dumps(cert_r231))
    ret_r231_tampered, out_r231_tampered = run_gate("git push origin dev", env="development", cwd=fix_r231)
    passed = (
        r231_blocked_runner
        and ret_r231 == 2 and out_r231.get("decision") == "deny"
        and ret_r231_tampered == 2 and out_r231_tampered.get("decision") == "deny"
    )
    results.append(("R2.31", "Execução inline opaca em Python (python3 -c) barrada", passed, ret_r231, out_r231.get("decision")))
    shutil.rmtree(fix_r231.parent)

    # R2.32: Execução inline opaca via flag curta de print (node -p 'process.exit(0)') barrada
    fix_r232, head_r232 = create_git_fixture(with_ci=True)
    ceh_r232 = fix_r232 / ".ceh"
    ceh_r232.mkdir(parents=True, exist_ok=True)
    r232_wf = fix_r232 / ".github" / "workflows"
    (r232_wf / "ci.yml").write_text("""name: CI Fake Pass Node -p
on: push
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: npm test
""")
    (fix_r232 / "package.json").write_text(json.dumps({
        "name": "fake-pass-node-p-fixture",
        "scripts": {
            "test": "node -p 'process.exit(0)'"
        }
    }))
    run_r232 = subprocess.run(["bash", str(runner_script), "npm test"], cwd=fix_r232, capture_output=True, text=True)
    cert_r232 = json.loads((ceh_r232 / "last-ci-run.json").read_text())
    r232_blocked_runner = (cert_r232.get("canonical_verified") is False)
    ret_r232, out_r232 = run_gate("git push origin dev", env="development", cwd=fix_r232)
    cert_r232["canonical_verified"] = True
    (ceh_r232 / "last-ci-run.json").write_text(json.dumps(cert_r232))
    ret_r232_tampered, out_r232_tampered = run_gate("git push origin dev", env="development", cwd=fix_r232)
    passed = (
        r232_blocked_runner
        and ret_r232 == 2 and out_r232.get("decision") == "deny"
        and ret_r232_tampered == 2 and out_r232_tampered.get("decision") == "deny"
    )
    results.append(("R2.32", "Execução inline opaca via node -p barrada", passed, ret_r232, out_r232.get("decision")))
    shutil.rmtree(fix_r232.parent)

    # R2.33: Execução inline opaca via flag longa de print (node --print 'process.exit(0)') barrada
    fix_r233, head_r233 = create_git_fixture(with_ci=True)
    ceh_r233 = fix_r233 / ".ceh"
    ceh_r233.mkdir(parents=True, exist_ok=True)
    r233_wf = fix_r233 / ".github" / "workflows"
    (r233_wf / "ci.yml").write_text("""name: CI Fake Pass Node --print
on: push
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: npm test
""")
    (fix_r233 / "package.json").write_text(json.dumps({
        "name": "fake-pass-node-print-fixture",
        "scripts": {
            "test": "node --print 'process.exit(0)'"
        }
    }))
    run_r233 = subprocess.run(["bash", str(runner_script), "npm test"], cwd=fix_r233, capture_output=True, text=True)
    cert_r233 = json.loads((ceh_r233 / "last-ci-run.json").read_text())
    r233_blocked_runner = (cert_r233.get("canonical_verified") is False)
    ret_r233, out_r233 = run_gate("git push origin dev", env="development", cwd=fix_r233)
    cert_r233["canonical_verified"] = True
    (ceh_r233 / "last-ci-run.json").write_text(json.dumps(cert_r233))
    ret_r233_tampered, out_r233_tampered = run_gate("git push origin dev", env="development", cwd=fix_r233)
    passed = (
        r233_blocked_runner
        and ret_r233 == 2 and out_r233.get("decision") == "deny"
        and ret_r233_tampered == 2 and out_r233_tampered.get("decision") == "deny"
    )
    results.append(("R2.33", "Execução inline opaca via node --print barrada", passed, ret_r233, out_r233.get("decision")))
    shutil.rmtree(fix_r233.parent)

    # R2.34: Execução inline opaca em Perl com flag de features avançadas (perl -E 'exit 0') barrada
    fix_r234, head_r234 = create_git_fixture(with_ci=True)
    ceh_r234 = fix_r234 / ".ceh"
    ceh_r234.mkdir(parents=True, exist_ok=True)
    r234_wf = fix_r234 / ".github" / "workflows"
    (r234_wf / "ci.yml").write_text("""name: CI Fake Pass Perl -E
on: push
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: npm test
""")
    (fix_r234 / "package.json").write_text(json.dumps({
        "name": "fake-pass-perl-e-fixture",
        "scripts": {
            "test": "perl -E 'exit 0'"
        }
    }))
    run_r234 = subprocess.run(["bash", str(runner_script), "npm test"], cwd=fix_r234, capture_output=True, text=True)
    cert_r234 = json.loads((ceh_r234 / "last-ci-run.json").read_text())
    r234_blocked_runner = (cert_r234.get("canonical_verified") is False)
    ret_r234, out_r234 = run_gate("git push origin dev", env="development", cwd=fix_r234)
    cert_r234["canonical_verified"] = True
    (ceh_r234 / "last-ci-run.json").write_text(json.dumps(cert_r234))
    ret_r234_tampered, out_r234_tampered = run_gate("git push origin dev", env="development", cwd=fix_r234)
    passed = (
        r234_blocked_runner
        and ret_r234 == 2 and out_r234.get("decision") == "deny"
        and ret_r234_tampered == 2 and out_r234_tampered.get("decision") == "deny"
    )
    results.append(("R2.34", "Execução inline opaca via perl -E barrada", passed, ret_r234, out_r234.get("decision")))
    shutil.rmtree(fix_r234.parent)

    # R2.35: Execução inline opaca em Perl com flags agrupadas (perl -pE 'exit 0') barrada
    fix_r235, head_r235 = create_git_fixture(with_ci=True)
    ceh_r235 = fix_r235 / ".ceh"
    ceh_r235.mkdir(parents=True, exist_ok=True)
    r235_wf = fix_r235 / ".github" / "workflows"
    (r235_wf / "ci.yml").write_text("""name: CI Fake Pass Perl -pE
on: push
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: npm test
""")
    (fix_r235 / "package.json").write_text(json.dumps({
        "name": "fake-pass-perl-pe-fixture",
        "scripts": {
            "test": "perl -pE 'exit 0'"
        }
    }))
    run_r235 = subprocess.run(["bash", str(runner_script), "npm test"], cwd=fix_r235, capture_output=True, text=True)
    cert_r235 = json.loads((ceh_r235 / "last-ci-run.json").read_text())
    r235_blocked_runner = (cert_r235.get("canonical_verified") is False)
    ret_r235, out_r235 = run_gate("git push origin dev", env="development", cwd=fix_r235)
    cert_r235["canonical_verified"] = True
    (ceh_r235 / "last-ci-run.json").write_text(json.dumps(cert_r235))
    ret_r235_tampered, out_r235_tampered = run_gate("git push origin dev", env="development", cwd=fix_r235)
    passed = (
        r235_blocked_runner
        and ret_r235 == 2 and out_r235.get("decision") == "deny"
        and ret_r235_tampered == 2 and out_r235_tampered.get("decision") == "deny"
    )
    results.append(("R2.35", "Execução inline opaca via perl -pE barrada", passed, ret_r235, out_r235.get("decision")))
    shutil.rmtree(fix_r235.parent)

    # R2.36: Controle positivo para Perl: arquivo de teste dedicado (perl test.t) com falha induzida e caminho feliz
    fix_r236, head_r236 = create_git_fixture(with_ci=True)
    ceh_r236 = fix_r236 / ".ceh"
    ceh_r236.mkdir(parents=True, exist_ok=True)
    r236_wf = fix_r236 / ".github" / "workflows"
    (r236_wf / "ci.yml").write_text("""name: CI Perl Test File
on: push
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: npm test
""")
    (fix_r236 / "package.json").write_text(json.dumps({
        "name": "perl-test-file-fixture",
        "scripts": {
            "test": "perl test.t"
        }
    }))
    # 1. Indução de falha: test.t falha
    (fix_r236 / "test.t").write_text("print \"1..1\\nnot ok 1 - fail\\n\"; exit 1;\n")
    run_r236_fail = subprocess.run(["bash", str(runner_script), "npm test"], cwd=fix_r236, capture_output=True, text=True)
    cert_r236_fail = json.loads((ceh_r236 / "last-ci-run.json").read_text())
    ret_r236_fail, out_r236_fail = run_gate("git push origin dev", env="development", cwd=fix_r236)
    falsification_r236 = (
        run_r236_fail.returncode != 0
        and cert_r236_fail.get("status") == "FAIL"
        and ret_r236_fail == 2
        and out_r236_fail.get("decision") == "deny"
    )

    # 2. Caminho feliz: test.t passa com asserção real
    (fix_r236 / "test.t").write_text("print \"1..1\\nok 1 - pass\\n\"; exit 0;\n")
    run_r236 = subprocess.run(["bash", str(runner_script), "npm test"], cwd=fix_r236, capture_output=True, text=True)
    cert_r236 = json.loads((ceh_r236 / "last-ci-run.json").read_text())
    r236_ok = (run_r236.returncode == 0 and cert_r236.get("canonical_verified") is True and cert_r236.get("status") == "PASS")
    ret_r236, out_r236 = run_gate("git push origin dev", env="development", cwd=fix_r236)
    passed = (falsification_r236 and r236_ok and ret_r236 == 0 and out_r236.get("decision") == "allow")
    results.append(("R2.36", "Controle positivo Perl: arquivo dedicado (perl test.t) com falha induzida", passed, ret_r236, out_r236.get("decision")))
    shutil.rmtree(fix_r236.parent)

    # R2.37: Controle positivo para Perl com opção de módulo (perl -Mfeature=say test.t) com falha induzida e caminho feliz
    fix_r237, head_r237 = create_git_fixture(with_ci=True)
    ceh_r237 = fix_r237 / ".ceh"
    ceh_r237.mkdir(parents=True, exist_ok=True)
    r237_wf = fix_r237 / ".github" / "workflows"
    (r237_wf / "ci.yml").write_text("""name: CI Perl Module Option
on: push
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: npm test
""")
    (fix_r237 / "package.json").write_text(json.dumps({
        "name": "perl-module-option-fixture",
        "scripts": {
            "test": "perl -Mfeature=say test.t"
        }
    }))
    # 1. Indução de falha: test.t falha
    (fix_r237 / "test.t").write_text("say \"1..1\\nnot ok 1 - fail\"; exit 1;\n")
    run_r237_fail = subprocess.run(["bash", str(runner_script), "npm test"], cwd=fix_r237, capture_output=True, text=True)
    cert_r237_fail = json.loads((ceh_r237 / "last-ci-run.json").read_text())
    ret_r237_fail, out_r237_fail = run_gate("git push origin dev", env="development", cwd=fix_r237)
    falsification_r237 = (
        run_r237_fail.returncode != 0
        and cert_r237_fail.get("status") == "FAIL"
        and ret_r237_fail == 2
        and out_r237_fail.get("decision") == "deny"
    )

    # 2. Caminho feliz: test.t passa com asserção real
    (fix_r237 / "test.t").write_text("say \"1..1\\nok 1 - pass\"; exit 0;\n")
    run_r237 = subprocess.run(["bash", str(runner_script), "npm test"], cwd=fix_r237, capture_output=True, text=True)
    cert_r237 = json.loads((ceh_r237 / "last-ci-run.json").read_text())
    r237_ok = (run_r237.returncode == 0 and cert_r237.get("canonical_verified") is True and cert_r237.get("status") == "PASS")
    ret_r237, out_r237 = run_gate("git push origin dev", env="development", cwd=fix_r237)
    passed = (falsification_r237 and r237_ok and ret_r237 == 0 and out_r237.get("decision") == "allow")
    results.append(("R2.37", "Controle positivo Perl: opção de módulo (-Mfeature) com falha induzida", passed, ret_r237, out_r237.get("decision")))
    shutil.rmtree(fix_r237.parent)

    # R2.38: Execução inline opaca em Perl com flag de startup (-fe 'exit 0') barrada
    fix_r238, head_r238 = create_git_fixture(with_ci=True)
    ceh_r238 = fix_r238 / ".ceh"
    ceh_r238.mkdir(parents=True, exist_ok=True)
    r238_wf = fix_r238 / ".github" / "workflows"
    (r238_wf / "ci.yml").write_text("""name: CI Fake Pass Perl -fe
on: push
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: npm test
""")
    (fix_r238 / "package.json").write_text(json.dumps({
        "name": "fake-pass-perl-fe-fixture",
        "scripts": {
            "test": "perl -fe 'exit 0'"
        }
    }))
    run_r238 = subprocess.run(["bash", str(runner_script), "npm test"], cwd=fix_r238, capture_output=True, text=True)
    cert_r238 = json.loads((ceh_r238 / "last-ci-run.json").read_text())
    r238_blocked_runner = (cert_r238.get("canonical_verified") is False)
    ret_r238, out_r238 = run_gate("git push origin dev", env="development", cwd=fix_r238)
    cert_r238["canonical_verified"] = True
    (ceh_r238 / "last-ci-run.json").write_text(json.dumps(cert_r238))
    ret_r238_tampered, out_r238_tampered = run_gate("git push origin dev", env="development", cwd=fix_r238)
    passed = (
        r238_blocked_runner
        and ret_r238 == 2 and out_r238.get("decision") == "deny"
        and ret_r238_tampered == 2 and out_r238_tampered.get("decision") == "deny"
    )
    results.append(("R2.38", "Execução inline opaca via perl -fe barrada", passed, ret_r238, out_r238.get("decision")))
    shutil.rmtree(fix_r238.parent)

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

    EXPECTED_TOTAL_SCENARIOS = 58

    assert len(results) == EXPECTED_TOTAL_SCENARIOS, f"Matriz deve conter exatamente {EXPECTED_TOTAL_SCENARIOS} cenários, mas contém {len(results)}."
    assert total_passed == EXPECTED_TOTAL_SCENARIOS, f"Esperado {EXPECTED_TOTAL_SCENARIOS} aprovados, mas obtido {total_passed}."

    print(f"TODOS OS {EXPECTED_TOTAL_SCENARIOS} CENÁRIOS FORAM VALIDADOS COM SUCESSO!")
    return 0

if __name__ == "__main__":
    exit(main())
