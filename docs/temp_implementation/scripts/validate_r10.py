#!/usr/bin/env python3
import json
import re
from pathlib import Path

repo = Path("/home/nandodev/projects/clearer-engineering-harness")
evidence_dir = repo / "docs/temp_implementation/evidence"
evidence_dir.mkdir(parents=True, exist_ok=True)

doc_file = repo / "docs/safety_gate.md"
lines = doc_file.read_text().splitlines()

target_line = None
target_line_num = None
for i, line in enumerate(lines, 1):
    if "file:///home/nandodev" in line:
        target_line = line
        target_line_num = i
        break

evidence = {
    "file": str(doc_file),
    "line_number": target_line_num,
    "line_content": target_line,
    "has_absolute_user_path": target_line is not None,
    "hardcoded_user": "/home/nandodev",
    "status": "Reproduzido"
}

evidence_file = evidence_dir / "r10_doc_link_evidence.json"
evidence_file.write_text(json.dumps(evidence, indent=2))
print(f"R10 evidence saved to {evidence_file}")
print(f"Line {target_line_num}: {target_line}")
