#!/usr/bin/env python3
import subprocess
import json
from pathlib import Path

repo = Path("/home/nandodev/projects/clearer-engineering-harness")
evidence_dir = repo / "docs/temp_implementation/evidence"
evidence_dir.mkdir(parents=True, exist_ok=True)

gate_script = repo / "clearer-engineering/scripts/safety-gate.py"
commands_file = repo / "docs/temp_implementation/r1_commands.txt"

lines = [line.strip() for line in commands_file.read_text().splitlines() if line.strip() and not line.startswith("#")]

results = []
for cmd in lines:
    proc = subprocess.run(
        ["python3", str(gate_script), "--check", cmd],
        capture_output=True, text=True
    )
    results.append({
        "command": cmd,
        "exit_code": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip()
    })

evidence_file = evidence_dir / "r1_compound_commands_evidence.json"
evidence_file.write_text(json.dumps(results, indent=2))
print(f"R1 evidence saved to {evidence_file}")
for r in results:
    try:
        data = json.loads(r["stdout"])
        print(f"CMD: {r['command']}")
        print(f"  EXIT: {r['exit_code']} | DECISION: {data.get('decision')} | ENV: {data.get('environment')} | USE_CASE: {data.get('use_case')}")
    except Exception as e:
        print(f"CMD: {r['command']} -> raw stdout: {r['stdout']}")
