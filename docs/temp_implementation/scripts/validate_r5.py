#!/usr/bin/env python3
import subprocess
import json
import tempfile
import shutil
from pathlib import Path

repo = Path("/home/nandodev/projects/clearer-engineering-harness")
evidence_dir = repo / "docs/temp_implementation/evidence"
evidence_dir.mkdir(parents=True, exist_ok=True)

gate_script = repo / "clearer-engineering/scripts/safety-gate.py"

tmp_dir = Path(tempfile.mkdtemp(prefix="ceh_r5_fixture_"))
ci_dir = tmp_dir / "ci"
ci_dir.mkdir(parents=True, exist_ok=True)

# Fixture Git com CI sem certificado
subprocess.run(["git", "init"], cwd=ci_dir, check=True, capture_output=True)
subprocess.run(["git", "branch", "-M", "dev"], cwd=ci_dir, check=True, capture_output=True)
subprocess.run(["git", "config", "user.name", "CEH Review Fixture"], cwd=ci_dir, check=True, capture_output=True)
subprocess.run(["git", "config", "user.email", "ceh-review@example.invalid"], cwd=ci_dir, check=True, capture_output=True)

wf_dir = ci_dir / ".github" / "workflows"
wf_dir.mkdir(parents=True, exist_ok=True)
(wf_dir / "ci.yml").write_text("name: fixture\non: push\n")
(ci_dir / "sentinel.txt").write_text("fixture\n")
subprocess.run(["git", "add", "."], cwd=ci_dir, check=True, capture_output=True)
subprocess.run(["git", "commit", "-m", "fixture: CI gate review"], cwd=ci_dir, check=True, capture_output=True)

commands = [
    ("standard_dev", "git push origin dev", "development"),
    ("custom_c_dev", f"git -C {ci_dir} push origin dev", "development"),
    ("standard_prod", "git push origin dev", "production"),
    ("custom_c_prod", f"git -C {ci_dir} push origin dev", "production"),
]

runs = []
for label, cmd, env_val in commands:
    p = subprocess.run(
        ["python3", str(gate_script), "--check", cmd, "--env", env_val],
        cwd=ci_dir, capture_output=True, text=True
    )
    data = None
    try:
        data = json.loads(p.stdout)
    except Exception:
        data = p.stdout
    runs.append({
        "label": label,
        "command": cmd,
        "env": env_val,
        "exit_code": p.returncode,
        "output": data
    })

evidence = {
    "fixture_dir": str(ci_dir),
    "runs": runs
}

evidence_file = evidence_dir / "r5_git_c_flag_evidence.json"
evidence_file.write_text(json.dumps(evidence, indent=2))
print(f"R5 evidence saved to {evidence_file}")
for r in runs:
    dec = r["output"].get("decision") if isinstance(r["output"], dict) else "raw"
    print(f"[{r['label']}] Exit: {r['exit_code']} | Decision: {dec} | Cmd: {r['command']}")

shutil.rmtree(tmp_dir)
