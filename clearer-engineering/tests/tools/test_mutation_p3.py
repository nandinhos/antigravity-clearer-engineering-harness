#!/usr/bin/env python3
"""
Teste de prova por mutação do P3 / checagem [4/7] do doc-audit.py (AZ3).
Injeta temporariamente um arquivo de evidência com caminho absoluto local,
comprova determinística e hermeticamente que o doc-audit.sh rejeita com exit 1,
e remove o artefato ao final sem resíduos.
"""

import sys
import subprocess
from pathlib import Path

def main():
    repo_root = Path(__file__).resolve().parents[3]
    evidence_dir = repo_root / "docs" / "temp_implementation" / "evidence"
    mutated_file = evidence_dir / "mutated_az3_sentinel.json"

    try:
        # Injetar evidência com caminho absoluto local
        mutated_file.write_text('{"leaked_home": "/home/fakeuser/.local/share/sentinel.txt"}\n', encoding="utf-8")

        # Executar doc-audit.py
        doc_audit = repo_root / "clearer-engineering" / "scripts" / "doc-audit.py"
        res = subprocess.run([sys.executable, str(doc_audit)], capture_output=True, text=True)

        if res.returncode == 0:
            print("FALHA: doc-audit.py aprovou arquivo com caminho absoluto vazado!", file=sys.stderr)
            sys.exit(1)

        expected_pattern = "/home/fakeuser/.local/share/sentinel.txt"
        if expected_pattern not in res.stdout:
            print(f"FALHA: doc-audit.py falhou sem relatar o padrão esperado '{expected_pattern}'!", file=sys.stderr)
            sys.exit(1)

        print("✔ Prova por mutação do P3 [AZ3]: doc-audit.py detectou caminho absoluto em evidência com exit 1.")
        sys.exit(0)
    finally:
        if mutated_file.exists():
            mutated_file.unlink()

if __name__ == "__main__":
    main()
