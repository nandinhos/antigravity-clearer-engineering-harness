#!/usr/bin/env python3
"""
test_doctor_verify.py — Bateria de testes de integridade para ceh-doctor --verify (CB11 / CB12).

Comprova:
1. Instalação oficial limpa via install.sh passa 100% no ceh-doctor --verify (exit 0, zero divergências).
2. Adulteração em hook_context.py é detectada com exit 1 e mensagem de divergência.
3. Adulteração em hooks.json é detectada com exit 1 e mensagem de divergência.
4. Remoção de arquivo essencial (ceh_core/engine.py) é detectada com exit 1 e mensagem determinística.
5. Inclusão de arquivo estranho (scripts/extra_hook.py) é detectada com exit 1.
6. Inclusão de arquivo estranho com 'tests' no nome (scripts/tests_evil.py) é detectada com exit 1 (CB12).
7. Inclusão de arquivo estranho dentro de tests/ (tests/conftest.py) é detectada com exit 1 (CB12).
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "clearer-engineering" / "scripts"
DOCTOR_SH = SCRIPTS_DIR / "ceh-doctor.sh"
INSTALL_SH = REPO_ROOT / "install.sh"

_TOOLS_DIR = Path(__file__).resolve().parent / "tools"
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))
from test_helpers import mkdtemp_resolved


class TestDoctorVerify(unittest.TestCase):
    def setUp(self):
        self.tmp_home = mkdtemp_resolved(prefix="ceh_doc_verify_home_")
        self.plugin_dir = self.tmp_home / ".gemini" / "config" / "plugins" / "clearer-engineering"

        # Executa install.sh limpo apontando HOME para tmp_home
        env = os.environ.copy()
        env["HOME"] = str(self.tmp_home)
        env["SKIP_DIAGNOSTICS"] = "1"
        proc = subprocess.run(
            ["bash", str(INSTALL_SH)],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(proc.returncode, 0, f"install.sh falhou: {proc.stderr}\nstdout: {proc.stdout}")
        self.assertTrue(self.plugin_dir.is_dir(), f"Plugin não instalado em: {self.plugin_dir}")

    def tearDown(self):
        shutil.rmtree(self.tmp_home, ignore_errors=True)

    def _run_verify(self) -> subprocess.CompletedProcess:
        env = os.environ.copy()
        env["HOME"] = str(self.tmp_home)
        env["CEH_PLUGIN_DIR"] = str(self.plugin_dir)
        return subprocess.run(
            ["bash", str(DOCTOR_SH), "--verify", str(REPO_ROOT)],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=20,
        )

    def test_clean_installation_passes_verify(self):
        """CB11: Uma instalação oficial recém-feita por install.sh passa 100% no --verify."""
        proc = self._run_verify()
        self.assertEqual(
            proc.returncode, 0,
            f"--verify reprovou instalação limpa!\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
        self.assertIn("✔ Verificação: SUCESSO", proc.stdout)
        self.assertNotIn("FALHA", proc.stdout)

    def test_tampered_hook_context_fails_verify(self):
        """CB1: Adulteração no hook_context.py na instalação deve ser detectada."""
        hc_file = self.plugin_dir / "scripts" / "hook_context.py"
        self.assertTrue(hc_file.is_file())
        with open(hc_file, "a", encoding="utf-8") as f:
            f.write("\n# BACKDOOR_HOOK_TAMPER = True\n")

        proc = self._run_verify()
        self.assertEqual(proc.returncode, 1, "Esperado exit 1 para hook_context.py adulterado")
        self.assertIn("Divergência de hash em scripts/hook_context.py", proc.stdout)
        self.assertIn("✖ Verificação: FALHA", proc.stdout)

    def test_tampered_hooks_json_fails_verify(self):
        """CB1: Modificação de hooks.json na instalação deve ser detectada."""
        hooks_file = self.plugin_dir / "hooks.json"
        self.assertTrue(hooks_file.is_file())
        content = hooks_file.read_text(encoding="utf-8")
        hooks_file.write_text(content.replace('"enabled": true', '"enabled": false'), encoding="utf-8")

        proc = self._run_verify()
        self.assertEqual(proc.returncode, 1, "Esperado exit 1 para hooks.json desativado")
        self.assertIn("Divergência de hash em hooks.json", proc.stdout)

    def test_missing_ceh_core_engine_fails_verify(self):
        """CB2: Remoção de scripts/ceh_core/engine.py deve ser detectada com mensagem clara."""
        engine_file = self.plugin_dir / "scripts" / "ceh_core" / "engine.py"
        self.assertTrue(engine_file.is_file())
        engine_file.unlink()

        proc = self._run_verify()
        self.assertEqual(proc.returncode, 1, "Esperado exit 1 para engine.py ausente")
        self.assertIn("✖ Ausente no instalado: scripts/ceh_core/engine.py", proc.stdout)

    def test_unauthorized_extra_file_fails_verify(self):
        """CB1: Arquivo estranho em scripts/extra_hook.py deve ser acusado."""
        extra_file = self.plugin_dir / "scripts" / "extra_hook.py"
        extra_file.write_text("# Malicious script\n", encoding="utf-8")

        proc = self._run_verify()
        self.assertEqual(proc.returncode, 1, "Esperado exit 1 para arquivo não autorizado")
        self.assertIn("✖ Arquivo não autorizado / estranho na instalação: scripts/extra_hook.py", proc.stdout)

    def test_unauthorized_file_with_tests_in_name_fails_verify_cb12(self):
        """CB12: Arquivo estranho com 'tests' no nome em scripts/tests_evil.py NÃO pode ser ignorado."""
        evil_file = self.plugin_dir / "scripts" / "tests_evil.py"
        evil_file.write_text("# Evil tests fake\n", encoding="utf-8")

        proc = self._run_verify()
        self.assertEqual(proc.returncode, 1, "Esperado exit 1 para scripts/tests_evil.py")
        self.assertIn("✖ Arquivo não autorizado / estranho na instalação: scripts/tests_evil.py", proc.stdout)

    def test_unauthorized_file_inside_tests_dir_fails_verify_cb12(self):
        """CB12: Arquivo estranho colocado dentro de tests/ (tests/conftest.py) deve ser detectado."""
        conftest_file = self.plugin_dir / "tests" / "conftest.py"
        conftest_file.write_text("# Rogue conftest\n", encoding="utf-8")

        proc = self._run_verify()
        self.assertEqual(proc.returncode, 1, "Esperado exit 1 para tests/conftest.py")
        self.assertIn("✖ Arquivo não autorizado / estranho na instalação: tests/conftest.py", proc.stdout)
    def test_unauthorized_file_starting_with_dotgit_fails_verify_cb17(self):
        """CB17: Arquivo estranho com prefixo .git (scripts/.gitevil.py) deve ser detectado."""
        dotgit_file = self.plugin_dir / "scripts" / ".gitevil.py"
        dotgit_file.write_text("# Rogue git prefix script\n", encoding="utf-8")

        proc = self._run_verify()
        self.assertEqual(proc.returncode, 1, "Esperado exit 1 para scripts/.gitevil.py")
        self.assertIn("✖ Arquivo não autorizado / estranho na instalação: scripts/.gitevil.py", proc.stdout)


if __name__ == "__main__":
    unittest.main()
