#!/usr/bin/env python3
"""
Unit tests for Conselho de Seniores verdict and confidence extraction (D4b).
Tests 3 mandatory fixtures from Handoff 008.
"""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


class TestConselhoExtraction(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="ceh-test-conselho-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _extract_verdict_confidence(self, file_content: str) -> tuple[str, str]:
        resp_file = self.tmp / "parecer_test.md"
        resp_file.write_text(file_content, encoding="utf-8")

        # Reproduces the exact extraction logic from conselho-seniores.sh
        bash_script = f"""
        resp_file="{resp_file}"
        verd="$(grep -E '^VEREDITO:' "$resp_file" | tail -n1 | sed -E 's/VEREDITO:[[:space:]]*//' | tr -d '\\r' || true)"
        cert="$(grep -E '^CERTEZA:' "$resp_file" | tail -n1 | sed -E 's/CERTEZA:[[:space:]]*//' | tr -d '\\r' || true)"

        if [[ "$verd" =~ [\\[\\|] ]]; then
          verd=""
        fi
        if [[ "$cert" =~ [\\[\\|] ]]; then
          cert=""
        fi

        case "$verd" in
          "HOMOLOGADO"|"RESSALVAS"|"REJEITADO") ;;
          *) verd="INDEFINIDO" ;;
        esac

        [[ -z "$cert" ]] && cert="N/D"

        echo "$verd|$cert"
        """
        proc = subprocess.run(["bash", "-c", bash_script], capture_output=True, text=True, check=True)
        parts = proc.stdout.strip().split("|")
        return parts[0], parts[1]

    def test_fixture_1_template_only_yields_indefinido_and_nd(self):
        """Fixture 1: Response only repeating template yields INDEFINIDO and N/D."""
        content = """
# Parecer Técnico
Aqui está minha análise baseada nos dados.
O modelo deve responder no formato:
VEREDITO: [HOMOLOGADO | RESSALVAS | REJEITADO]
CERTEZA: [0.00 a 1.00]
"""
        verd, cert = self._extract_verdict_confidence(content)
        self.assertEqual(verd, "INDEFINIDO")
        self.assertEqual(cert, "N/D")

    def test_fixture_2_template_followed_by_ressalvas_yields_ressalvas(self):
        """Fixture 2: Template followed by real verdict yields RESSALVAS and confidence."""
        content = """
# Parecer Técnico
Instruções recebidas:
VEREDITO: [HOMOLOGADO | RESSALVAS | REJEITADO]
CERTEZA: [0.00 a 1.00]

Após análise detalhada dos pontos apresentados:
VEREDITO: RESSALVAS
CERTEZA: 0.90
"""
        verd, cert = self._extract_verdict_confidence(content)
        self.assertEqual(verd, "RESSALVAS")
        self.assertEqual(cert, "0.90")

    def test_fixture_3_homologado_without_confidence_yields_nd(self):
        """Fixture 3: VEREDITO: HOMOLOGADO without CERTEZA line yields HOMOLOGADO and N/D."""
        content = """
# Parecer Técnico
O plano atende plenamente aos critérios.
VEREDITO: HOMOLOGADO
"""
        verd, cert = self._extract_verdict_confidence(content)
        self.assertEqual(verd, "HOMOLOGADO")
        self.assertEqual(cert, "N/D")


if __name__ == "__main__":
    unittest.main()
