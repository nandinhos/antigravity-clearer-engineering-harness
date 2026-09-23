#!/usr/bin/env python3
import subprocess
import json
import tempfile
import shutil
from pathlib import Path

repo = Path("/home/nandodev/projects/clearer-engineering-harness")
evidence_dir = repo / "docs/temp_implementation/evidence"
evidence_dir.mkdir(parents=True, exist_ok=True)

tmp_dir = Path(tempfile.mkdtemp(prefix="ceh_r4_fixture_"))
diff_dir = tmp_dir / "review-diff"
diff_dir.mkdir(parents=True, exist_ok=True)

# 1. Preparar fixture Git
subprocess.run(["git", "init"], cwd=diff_dir, check=True, capture_output=True)
subprocess.run(["git", "config", "user.name", "CEH Review Fixture"], cwd=diff_dir, check=True, capture_output=True)
subprocess.run(["git", "config", "user.email", "ceh-review@example.invalid"], cwd=diff_dir, check=True, capture_output=True)

(diff_dir / "base.txt").write_text("base\n")
(diff_dir / "unstaged.txt").write_text("initial\n")
subprocess.run(["git", "add", "base.txt", "unstaged.txt"], cwd=diff_dir, check=True, capture_output=True)
subprocess.run(["git", "commit", "-m", "fixture: first commit"], cwd=diff_dir, check=True, capture_output=True)

(diff_dir / "base.txt").write_text("base\nsecond commit\n")
subprocess.run(["git", "add", "base.txt"], cwd=diff_dir, check=True, capture_output=True)
subprocess.run(["git", "commit", "-m", "fixture: second commit"], cwd=diff_dir, check=True, capture_output=True)

(diff_dir / "staged.txt").write_text("staged change\n")
subprocess.run(["git", "add", "staged.txt"], cwd=diff_dir, check=True, capture_output=True)

with open(diff_dir / "unstaged.txt", "a") as f:
    f.write("unstaged change\n")

# 2. Executar os comandos
cmd_skill = "git diff HEAD~1..HEAD 2>/dev/null || git diff"
p_skill = subprocess.run(cmd_skill, shell=True, cwd=diff_dir, capture_output=True, text=True)

p_head = subprocess.run(["git", "diff", "HEAD~1..HEAD"], cwd=diff_dir, capture_output=True, text=True)
p_unstaged = subprocess.run(["git", "diff"], cwd=diff_dir, capture_output=True, text=True)
p_staged = subprocess.run(["git", "diff", "--cached"], cwd=diff_dir, capture_output=True, text=True)

evidence = {
    "skill_command": cmd_skill,
    "skill_output": p_skill.stdout,
    "diff_head_to_head_minus_1": p_head.stdout,
    "diff_unstaged": p_unstaged.stdout,
    "diff_staged": p_staged.stdout,
    "unstaged_present_in_skill_output": "unstaged change" in p_skill.stdout,
    "staged_present_in_skill_output": "staged change" in p_skill.stdout
}

evidence_file = evidence_dir / "r4_review_diff_evidence.json"
evidence_file.write_text(json.dumps(evidence, indent=2))
print(f"R4 evidence saved to {evidence_file}")
print(f"Unstaged present in skill output: {evidence['unstaged_present_in_skill_output']}")
print(f"Staged present in skill output: {evidence['staged_present_in_skill_output']}")

shutil.rmtree(tmp_dir)
