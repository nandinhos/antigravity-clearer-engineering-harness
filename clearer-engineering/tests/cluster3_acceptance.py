#!/usr/bin/env python3
"""
Suíte de Testes de Aceitação do Cluster 3 (R3, R4, R9, R10).
CLEARER Engineering Harness (CEH).

Testa:
- R3/R9: Instalação e desinstalação atômica de aliases via bloco delimitado com Python inline (sem sed -i).
- R4: Contrato de diff na skill clearer-review cobrindo o tripé (working tree, staging e commit base).
- R10: Portabilidade de links na documentação oficial (eliminação de caminhos absolutos locais).
"""

import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


class Cluster3Acceptance(unittest.TestCase):

    def test_r3_and_r9_atomic_aliases_install_and_uninstall(self):
        """R3/R9: Aliases devem ser instalados e removidos atomicamente sem sed -i."""
        tmp_home = Path(tempfile.mkdtemp(prefix="ceh-cluster3-r3-"))
        try:
            bashrc = tmp_home / ".bashrc"
            zshrc = tmp_home / ".zshrc"
            bashrc.write_text("# Initial user bashrc\nexport FOO=1\n", encoding="utf-8")
            zshrc.write_text("# Initial user zshrc\nexport BAR=2\n", encoding="utf-8")

            install_script = REPO_ROOT / "install.sh"
            uninstall_script = REPO_ROOT / "uninstall.sh"

            # 1. Verifica ausência de sed -i para aliases nos scripts
            install_content = install_script.read_text(encoding="utf-8")
            uninstall_content = uninstall_script.read_text(encoding="utf-8")
            self.assertNotIn("sed -i", uninstall_content, "uninstall.sh não deve usar sed -i para aliases")
            
            # 2. Testa instalação via subshell invocando configure_shell_aliases
            env = os.environ.copy()
            env["HOME"] = str(tmp_home)
            # Stub de agy para acelerar o teste de desinstalação na fixture
            bin_dir = tmp_home / "bin"
            bin_dir.mkdir(parents=True, exist_ok=True)
            agy_stub = bin_dir / "agy"
            agy_stub.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            agy_stub.chmod(0o755)
            env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"

            cmd_install = f"bash -c 'source {install_script} >/dev/null 2>&1; configure_shell_aliases'"
            res_install = subprocess.run(cmd_install, shell=True, env=env, capture_output=True, text=True)
            self.assertEqual(res_install.returncode, 0, f"Falha na instalação de aliases: {res_install.stderr}")

            expected_aliases = [
                "agy-ceh", "agy-ceh-yolo", "ceh", "ceh-env", "ceh-branches",
                "ceh-preflight", "ceh-evals", "ceh-monitor", "ceh-help"
            ]

            for rc in (bashrc, zshrc):
                content = rc.read_text(encoding="utf-8")
                self.assertIn("# BEGIN CLEARER ENGINEERING HARNESS (CEH) ALIASES", content)
                self.assertIn("# END CLEARER ENGINEERING HARNESS (CEH) ALIASES", content)
                for a in expected_aliases:
                    self.assertIn(f"alias {a}=", content, f"Alias {a} ausente em {rc.name}")
                self.assertEqual(content.count("# BEGIN CLEARER ENGINEERING HARNESS (CEH) ALIASES"), 1)

            # 3. Testa Idempotência (re-execução não duplica bloco)
            subprocess.run(cmd_install, shell=True, env=env, check=True)
            for rc in (bashrc, zshrc):
                content = rc.read_text(encoding="utf-8")
                self.assertEqual(content.count("# BEGIN CLEARER ENGINEERING HARNESS (CEH) ALIASES"), 1)
                self.assertEqual(content.count("alias ceh="), 1)

            # 4. Testa desinstalação atômica
            res_uninstall = subprocess.run(f"bash {uninstall_script}", shell=True, env=env, capture_output=True, text=True)
            self.assertEqual(res_uninstall.returncode, 0, f"Falha na desinstalação: {res_uninstall.stderr}")

            for rc in (bashrc, zshrc):
                content = rc.read_text(encoding="utf-8")
                self.assertNotIn("# BEGIN CLEARER ENGINEERING HARNESS (CEH) ALIASES", content)
                self.assertNotIn("# END CLEARER ENGINEERING HARNESS (CEH) ALIASES", content)
                for a in expected_aliases:
                    self.assertNotIn(f"alias {a}=", content, f"Alias {a} não foi removido de {rc.name}")

            # 5. Testa limpeza de aliases legados/órfãos
            legacy_content = (
                "# === CLEARER Engineering Harness (CEH) ===\n"
                "alias ceh-env='bash legacy/detect.sh'\n"
                "alias ceh-monitor='bash legacy/monitor.sh'\n"
                "alias ceh-help='bash legacy/help.sh'\n"
            )
            bashrc.write_text(legacy_content, encoding="utf-8")
            subprocess.run(f"bash {uninstall_script}", shell=True, env=env, check=True)
            cleaned = bashrc.read_text(encoding="utf-8").strip()
            self.assertEqual(cleaned, "", f"Aliases órfãos legados não foram removidos: {cleaned}")

        finally:
            shutil.rmtree(tmp_home, ignore_errors=True)

    def test_r4_review_diff_tripod_contract(self):
        """R4: Skill clearer-review deve instruir explicitamente o tripé de inspeção de diff."""
        skill_path = REPO_ROOT / "clearer-engineering" / "skills" / "clearer-review" / "SKILL.md"
        self.assertTrue(skill_path.is_file(), "SKILL.md de clearer-review não encontrado")
        content = skill_path.read_text(encoding="utf-8")

        # Verifica se o tripé está formalizado
        self.assertIn("git diff", content)
        self.assertIn("git diff --cached", content)
        self.assertIn("HEAD~1..HEAD", content)
        self.assertIn("Tripé de Inspeção", content)

        # Garante que o fallback falho antigo não está presente como comando único
        self.assertNotIn("git diff HEAD~1..HEAD 2>/dev/null || git diff\n```", content)

    def test_r10_documentation_links_portability(self):
        """R10: Documentação oficial não deve conter caminhos absolutos hardcoded locais."""
        docs_to_check = [
            REPO_ROOT / "docs" / "safety_gate.md",
            REPO_ROOT / "docs" / "architecture.md",
        ]
        for doc in docs_to_check:
            self.assertTrue(doc.is_file(), f"{doc.name} não encontrado")
            content = doc.read_text(encoding="utf-8")
            self.assertNotIn("file:///home/nandodev", content, f"Link absoluto local encontrado em {doc.name}")


if __name__ == "__main__":
    unittest.main()
