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

tmp_dir = Path(tempfile.mkdtemp(prefix="ceh_r6_fixture_"))

# Executar script bash exatamente como descrito no roteiro R6 do plano
bash_script = f"""
cd "{tmp_dir}"
set +e
set +o pipefail
bash "{test_runner_script}" false | grep 'STATUS:    FAIL' >/dev/null
statuses=("${{PIPESTATUS[@]}}")
echo "PIPESTATUS_RUNNER=${{statuses[0]}}"
echo "PIPESTATUS_GREP=${{statuses[1]}}"

if eval "bash '{test_runner_script}' false | grep 'STATUS:    FAIL' >/dev/null"; then
    echo "EVAL_RESULT=PASS"
else
    echo "EVAL_RESULT=FAIL"
fi
"""

proc = subprocess.run(["bash", "-c", bash_script], capture_output=True, text=True)

evidence = {
    "stdout": proc.stdout,
    "stderr": proc.stderr,
    "exit_code": proc.returncode,
}

evidence_file = evidence_dir / "r6_pipeline_exit_evidence.json"
evidence_file.write_text(json.dumps(evidence, indent=2))
print(f"R6 evidence saved to {evidence_file}")
print(proc.stdout.strip())

shutil.rmtree(tmp_dir)
