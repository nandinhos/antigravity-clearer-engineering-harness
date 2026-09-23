#!/usr/bin/env python3
import subprocess
import json
import tempfile
import shutil
from pathlib import Path

repo = Path("/home/nandodev/projects/clearer-engineering-harness")
evidence_dir = repo / "docs/temp_implementation/evidence"
evidence_dir.mkdir(parents=True, exist_ok=True)

tmp_dir = Path(tempfile.mkdtemp(prefix="ceh_r8_fixture_"))
git_dir = tmp_dir / "repo"
git_dir.mkdir(parents=True, exist_ok=True)

# 1. Preparar repositório Git
subprocess.run(["git", "init"], cwd=git_dir, check=True, capture_output=True)
subprocess.run(["git", "config", "user.name", "CEH Review Fixture"], cwd=git_dir, check=True, capture_output=True)
subprocess.run(["git", "config", "user.email", "ceh-review@example.invalid"], cwd=git_dir, check=True, capture_output=True)

(git_dir / "clearer-engineering/scripts").mkdir(parents=True, exist_ok=True)
shutil.copytree(repo / "evals", git_dir / "evals")
shutil.copy(repo / "clearer-engineering/scripts/safety-gate.py", git_dir / "clearer-engineering/scripts/safety-gate.py")

subprocess.run(["git", "add", "."], cwd=git_dir, check=True, capture_output=True)
subprocess.run(["git", "commit", "-m", "initial commit"], cwd=git_dir, check=True, capture_output=True)

# 2. Criar alteração não commitada antes de iniciar o eval
(git_dir / "dirty_uncommitted_file.txt").write_text("arquivo sujo pré-existente\n")
status_before = subprocess.check_output(["git", "status", "--porcelain"], cwd=git_dir, text=True).strip()

# 3. Rodar evals/run.sh
proc = subprocess.run(["bash", "evals/run.sh"], cwd=git_dir, capture_output=True, text=True)
status_after = subprocess.check_output(["git", "status", "--porcelain"], cwd=git_dir, text=True).strip()

criterio_4_passed = "Critério 4: Restauração limpa aprovada" in proc.stdout

evidence = {
    "status_before": status_before,
    "status_after": status_after,
    "criterio_4_passed": criterio_4_passed,
    "stdout": proc.stdout
}

evidence_file = evidence_dir / "r8_eval_dirty_repo_evidence.json"
evidence_file.write_text(json.dumps(evidence, indent=2))
print(f"R8 evidence saved to {evidence_file}")
print(f"Status before: '{status_before}'")
print(f"Status after: '{status_after}'")
print(f"Critério 4 aprovado com repositório sujo: {criterio_4_passed}")

shutil.rmtree(tmp_dir)
