#!/usr/bin/env python3
"""
Teste de prova por mutação do P3 / checagem [4/7] do doc-audit.py (AZ3).
Regra AT5 (Handoff 046 / Handoff 072): mutação estritamente em clone/cópia temporária.
Copia a árvore necessária para um diretório temporário, injeta a violação na cópia,
comprova determinística e hermeticamente que o doc-audit.py rejeita com exit 1,
e descarta a cópia temporária sem jamais alterar o checkout de trabalho.
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def main():
    repo_root = Path(__file__).resolve().parents[3]

    with tempfile.TemporaryDirectory(prefix="ceh_mut_p3_") as tmp_dir:
        tmp_repo = Path(tmp_dir)

        # Copia docs/ e clearer-engineering/scripts/ para a sandbox
        shutil.copytree(repo_root / "docs", tmp_repo / "docs")
        shutil.copytree(repo_root / "clearer-engineering", tmp_repo / "clearer-engineering")

        # Injetar evidência com caminho absoluto local NA CÓPIA TEMPORÁRIA
        mutated_file = tmp_repo / "docs" / "temp_implementation" / "evidence" / "mutated_az3_sentinel.json"
        mutated_file.write_text('{"leaked_home": "/home/fakeuser/.local/share/sentinel.txt"}\n', encoding="utf-8")

        # Executar doc-audit.py dentro da cópia temporária
        doc_audit = tmp_repo / "clearer-engineering" / "scripts" / "doc-audit.py"
        res = subprocess.run([sys.executable, str(doc_audit)], capture_output=True, text=True, cwd=str(tmp_repo))

        if res.returncode == 0:
            print("FALHA: doc-audit.py aprovou arquivo com caminho absoluto vazado!", file=sys.stderr)
            sys.exit(1)

        expected_pattern = "/home/fakeuser/.local/share/sentinel.txt"
        if expected_pattern not in res.stdout and expected_pattern not in res.stderr:
            print(f"FALHA: doc-audit.py falhou sem relatar o padrão esperado '{expected_pattern}'!", file=sys.stderr)
            sys.exit(1)

        print("✔ Prova por mutação do P3 [AZ3]: doc-audit.py detectou caminho absoluto em evidência com exit 1 (em clone temporário).")
        sys.exit(0)


if __name__ == "__main__":
    main()
