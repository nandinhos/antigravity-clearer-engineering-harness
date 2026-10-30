#!/usr/bin/env python3
"""
Testes comportamentais e determinísticos para o ceh-drift.sh (SDD 2.0 / Ponytail).

Testa:
  (1) Happy Path: Doc referencia arquivos existentes e código sincronizado -> Exit 0
  (2) Unhappy Path 1: Doc referencia arquivo de código inexistente -> Quebra de Referência -> Exit 1
  (3) Unhappy Path 2: Código citado é modificado no Git, mas o doc não -> Drift Detectado -> Exit 1
  (4) Resolução segura de caminhos e portabilidade Linux + macOS
"""

import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

_TOOLS_DIR = Path(__file__).resolve().parent / "tools"
sys.path.insert(0, str(_TOOLS_DIR))
from test_helpers import mkdtemp_resolved

SCRIPT_PATH = Path(__file__).resolve().parent.parent / "scripts" / "ceh-drift.sh"


class TestCehDrift(unittest.TestCase):
    """Suíte de testes de regressão comportamental para o utilitário ceh-drift."""

    def setUp(self) -> None:
        self.repo_dir = mkdtemp_resolved(prefix="ceh-drift-test-")
        # Inicializa repositório git temporário hermético
        subprocess.run(["git", "init", str(self.repo_dir)], capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Tester"], cwd=str(self.repo_dir), check=True)
        subprocess.run(["git", "config", "user.email", "tester@test.local"], cwd=str(self.repo_dir), check=True)

        # Estrutura inicial
        (self.repo_dir / "src").mkdir(parents=True, exist_ok=True)
        (self.repo_dir / "docs" / "designs").mkdir(parents=True, exist_ok=True)

        # Cria arquivo de código base
        self.code_file = self.repo_dir / "src" / "service.py"
        self.code_file.write_text("def execute():\n    return True\n", encoding="utf-8")

        # Cria documento de design que referencia o arquivo
        self.doc_file = self.repo_dir / "docs" / "designs" / "feature.md"
        self.doc_file.write_text(
            "# Design de Serviço\n\nImplementado em `src/service.py`.\n",
            encoding="utf-8",
        )

        subprocess.run(["git", "add", "."], cwd=str(self.repo_dir), check=True)
        subprocess.run(["git", "commit", "-m", "chore: setup inicial"], cwd=str(self.repo_dir), check=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.repo_dir, ignore_errors=True)

    def _run_drift(self, *args: str) -> subprocess.CompletedProcess:
        cmd = ["bash", str(SCRIPT_PATH), *args]
        return subprocess.run(
            cmd,
            cwd=str(self.repo_dir),
            capture_output=True,
            text=True,
        )

    def test_happy_path_no_drift(self) -> None:
        """Cenário 1: Tudo sincronizado e referências válidas -> Exit 0."""
        res = self._run_drift("--strict")
        self.assertEqual(res.returncode, 0, f"Falha inesperada:\n{res.stdout}\n{res.stderr}")
        self.assertIn("Nenhum drift ou quebra de especificação detectados", res.stdout)

    def test_broken_reference_detection(self) -> None:
        """Cenário 2: Doc cita arquivo que não existe no filesystem -> Exit 1."""
        broken_doc = self.repo_dir / "docs" / "designs" / "quebrado.md"
        broken_doc.write_text(
            "# Spec Quebrado\n\nReferência fantasma em `src/fantasma.py`.\n",
            encoding="utf-8",
        )
        res = self._run_drift("--strict")
        self.assertEqual(res.returncode, 1)
        self.assertIn("[QUEBRA DE REFERÊNCIA]", res.stdout)
        self.assertIn("src/fantasma.py", res.stdout)

    def test_code_drift_detection(self) -> None:
        """Cenário 3: Código é alterado sem atualizar a especificação -> Exit 1 em --strict."""
        # Altera o código
        self.code_file.write_text("def execute():\n    return False # modificado\n", encoding="utf-8")
        
        res = self._run_drift("--strict")
        self.assertEqual(res.returncode, 1)
        self.assertIn("[DRIFT DETECTADO]", res.stdout)
        self.assertIn("src/service.py", res.stdout)

    def test_synchronized_update_no_drift(self) -> None:
        """Cenário 4: Tanto o código quanto o documento são atualizados juntos -> Exit 0."""
        self.code_file.write_text("def execute():\n    return 'novo'\n", encoding="utf-8")
        self.doc_file.write_text(
            "# Design de Serviço Atualizado\n\nImplementado em `src/service.py` com retorno novo.\n",
            encoding="utf-8",
        )
        res = self._run_drift("--strict")
        self.assertEqual(res.returncode, 0, f"Falha inesperada:\n{res.stdout}\n{res.stderr}")


if __name__ == "__main__":
    unittest.main()
