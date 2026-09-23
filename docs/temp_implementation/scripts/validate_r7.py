#!/usr/bin/env python3
import subprocess
import json
import tempfile
import shutil
from pathlib import Path

repo = Path("/home/nandodev/projects/clearer-engineering-harness")
evidence_dir = repo / "docs/temp_implementation/evidence"
evidence_dir.mkdir(parents=True, exist_ok=True)

tmp_dir = Path(tempfile.mkdtemp(prefix="ceh_r7_fixture_"))

# Preparar cópias
r7_dir = tmp_dir / "r7"
r7_syntax_dir = tmp_dir / "r7-syntax"

for d in (r7_dir, r7_syntax_dir):
    (d / "clearer-engineering/scripts").mkdir(parents=True, exist_ok=True)
    shutil.copytree(repo / "evals", d / "evals")
    shutil.copy(repo / "clearer-engineering/scripts/safety-gate.py", d / "clearer-engineering/scripts/safety-gate.py")

# 1. Executar controle
p_control = subprocess.run(["bash", "evals/run.sh"], cwd=r7_dir, capture_output=True, text=True)

# 2. Injetar mutação de sintaxe em r7-syntax/evals/run.sh
run_sh = r7_syntax_dir / "evals/run.sh"
text = run_sh.read_text()
needle = 'sed \'s/\\["prod", "production", "prd", "live"\\]/\\["live_only_token"\\]/g\' "$GATE_SCRIPT" > "$MUTANT_SCRIPT"\n'
replacement = needle + 'printf \'def =\\n\' > "$MUTANT_SCRIPT"\n'
assert needle in text, "Needle não encontrada no run.sh"
run_sh.write_text(text.replace(needle, replacement, 1))

# 3. Executar variante com sintaxe inválida
p_syntax = subprocess.run(["bash", "evals/run.sh"], cwd=r7_syntax_dir, capture_output=True, text=True)

syntax_deriva_b_passed = "Critério 3: Deriva B aprovada" in p_syntax.stdout

evidence = {
    "control_stdout": p_control.stdout,
    "syntax_stdout": p_syntax.stdout,
    "syntax_deriva_b_approved": syntax_deriva_b_passed
}

evidence_file = evidence_dir / "r7_eval_deriva_b_evidence.json"
evidence_file.write_text(json.dumps(evidence, indent=2))
print(f"R7 evidence saved to {evidence_file}")
print(f"Deriva B aprovada no teste com erro de sintaxe (SyntaxError): {syntax_deriva_b_passed}")

shutil.rmtree(tmp_dir)
