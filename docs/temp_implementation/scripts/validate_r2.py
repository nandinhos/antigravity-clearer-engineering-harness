#!/usr/bin/env python3
import subprocess
import json
import tempfile
import shutil
from pathlib import Path

repo = Path("/home/nandodev/projects/clearer-engineering-harness")
evidence_dir = repo / "docs/temp_implementation/evidence"
evidence_dir.mkdir(parents=True, exist_ok=True)

test_runner_script = repo / "clearer-engineering/scripts/test-runner.sh"
gate_script = repo / "clearer-engineering/scripts/safety-gate.py"

tmp_dir = Path(tempfile.mkdtemp(prefix="ceh_r2_fixture_"))
ci_dir = tmp_dir / "ci"
bin_dir = ci_dir / "bin"
bin_dir.mkdir(parents=True, exist_ok=True)

# 1. Configurar fixture Git
subprocess.run(["git", "init"], cwd=ci_dir, check=True, capture_output=True)
subprocess.run(["git", "branch", "-M", "dev"], cwd=ci_dir, check=True, capture_output=True)
subprocess.run(["git", "config", "user.name", "CEH Review Fixture"], cwd=ci_dir, check=True, capture_output=True)
subprocess.run(["git", "config", "user.email", "ceh-review@example.invalid"], cwd=ci_dir, check=True, capture_output=True)

# 2. Criar workflow marcador de CI
wf_dir = ci_dir / ".github" / "workflows"
wf_dir.mkdir(parents=True, exist_ok=True)
(wf_dir / "ci.yml").write_text("name: fixture\non: push\n")
(ci_dir / "sentinel.txt").write_text("fixture\n")
subprocess.run(["git", "add", "."], cwd=ci_dir, check=True, capture_output=True)
subprocess.run(["git", "commit", "-m", "fixture: CI gate review"], cwd=ci_dir, check=True, capture_output=True)
fixture_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ci_dir, text=True).strip()

# 3. Wrapper de RTK controlado
rtk_wrapper = bin_dir / "rtk"
rtk_wrapper.write_text('#!/bin/sh\nexec "$@"\n')
rtk_wrapper.chmod(0o755)

# 4. Executar test-runner.sh true dentro da fixture
env = {**subprocess.os.environ, "PATH": f"{bin_dir}:{subprocess.os.environ.get('PATH', '')}"}
runner_proc = subprocess.run(
    ["bash", str(test_runner_script), "true"],
    cwd=ci_dir, env=env, capture_output=True, text=True
)

cert_path = ci_dir / ".ceh" / "last-ci-run.json"
cert_data = None
if cert_path.exists():
    cert_data = json.loads(cert_path.read_text())

# 5. Avaliar sem push o safety gate
gate_proc = subprocess.run(
    ["python3", str(gate_script), "--check", "git push origin dev", "--env", "development"],
    cwd=ci_dir, capture_output=True, text=True
)

gate_data = None
try:
    gate_data = json.loads(gate_proc.stdout)
except Exception:
    gate_data = gate_proc.stdout

evidence = {
    "fixture_commit": fixture_commit,
    "runner_exit_code": runner_proc.returncode,
    "runner_stdout": runner_proc.stdout,
    "certificate_file_exists": cert_path.exists(),
    "certificate_content": cert_data,
    "gate_exit_code": gate_proc.returncode,
    "gate_output": gate_data
}

evidence_file = evidence_dir / "r2_ci_certificate_evidence.json"
evidence_file.write_text(json.dumps(evidence, indent=2))
print(f"R2 evidence saved to {evidence_file}")
print(f"Fixture Commit: {fixture_commit}")
print(f"Runner Exit Code: {runner_proc.returncode}")
print(f"Certificate Status: {cert_data.get('status') if cert_data else 'None'}")
print(f"Gate Exit Code: {gate_proc.returncode}")
print(f"Gate Decision: {gate_data.get('decision') if isinstance(gate_data, dict) else 'None'}")

# Limpar fixture temporária
shutil.rmtree(tmp_dir)
