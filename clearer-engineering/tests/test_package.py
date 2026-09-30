#!/usr/bin/env python3
# ==============================================================================
# test_package.py — Testes do Empacotador Multi-Host (PR-16)
# ==============================================================================
"""
Testes de determinismo, completude por host e controle negativo do empacotador CEH.
Valida os requisitos do Handoff 077:
  1. Empacotamento determinístico (mesmos hashes reproduzíveis);
  2. Manifestos restritos aos formatos observados por host;
  3. Completude por host: safety-gate empacotado avaliando recorded.jsonl de cada host;
  4. Controle negativo: pacote do Muse sem adapters/muse.py reprova e bloqueia (fail-closed / deny).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_TOOL = REPO_ROOT / "clearer-engineering" / "tools" / "package.py"
FIXTURES_DIR = REPO_ROOT / "clearer-engineering" / "tests" / "fixtures" / "adapters"


class TestPackage(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="ceh_test_package_")

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_package_determinism(self):
        """Verifica que empacotamentos sucessivos geram hashes e arquivos idênticos."""
        out1 = Path(self.tmp_dir) / "run1"
        out2 = Path(self.tmp_dir) / "run2"

        proc1 = subprocess.run([sys.executable, str(PACKAGE_TOOL), "--all", "--out", str(out1), "--json"], capture_output=True, text=True)
        self.assertEqual(proc1.returncode, 0, f"package.py run1 falhou: {proc1.stderr}")
        data1 = json.loads(proc1.stdout)

        proc2 = subprocess.run([sys.executable, str(PACKAGE_TOOL), "--all", "--out", str(out2), "--json"], capture_output=True, text=True)
        self.assertEqual(proc2.returncode, 0, f"package.py run2 falhou: {proc2.stderr}")
        data2 = json.loads(proc2.stdout)

        for host in ["antigravity", "muse", "claude-code"]:
            self.assertEqual(data1[host]["hash"], data2[host]["hash"], f"Hash divergente para {host}")
            self.assertEqual(data1[host]["file_count"], data2[host]["file_count"], f"Contagem de arquivos divergente para {host}")

    def test_package_manifests_observed(self):
        """Valida que os manifestos gerados seguem apenas formatos estritamente observados."""
        pkg_base = Path(self.tmp_dir) / "manifests"
        subprocess.run([sys.executable, str(PACKAGE_TOOL), "--all", "--out", str(pkg_base)], check=True, capture_output=True)

        # 1. Antigravity
        agy_hooks = json.loads((pkg_base / "antigravity" / "hooks.json").read_text(encoding="utf-8"))
        self.assertIn("ceh-safety-gate", agy_hooks)
        self.assertTrue(agy_hooks["ceh-safety-gate"]["enabled"])

        # 2. Muse
        muse_manifest = json.loads((pkg_base / "muse" / ".muse-plugin" / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(muse_manifest["name"], "clearer-muse")
        self.assertEqual(muse_manifest["compat"]["manifestDir"], ".muse-plugin")
        hooks = muse_manifest["capabilities"]["hooks"]
        self.assertEqual(hooks[0]["command"], ["python3", "hooks/safety-gate.py"])

        # 3. Claude Code
        claude_settings = json.loads((pkg_base / "claude-code" / ".claude" / "settings.json").read_text(encoding="utf-8"))
        self.assertIn("hooks", claude_settings)
        self.assertIn("PreToolUse", claude_settings["hooks"])

    def test_completeness_antigravity(self):
        """Testa safety-gate empacotado do Antigravity contra recorded.jsonl (93 payloads)."""
        pkg_dir = Path(self.tmp_dir) / "pkg_agy"
        subprocess.run([sys.executable, str(PACKAGE_TOOL), "--host", "antigravity", "--out", str(pkg_dir)], check=True, capture_output=True)

        gate_py = pkg_dir / "scripts" / "safety-gate.py"
        fixture_file = FIXTURES_DIR / "antigravity" / "recorded.jsonl"
        self.assertTrue(fixture_file.is_file(), f"Fixture não encontrada: {fixture_file}")

        lines = [ln.strip() for ln in fixture_file.read_text(encoding="utf-8").splitlines() if ln.strip()]
        self.assertEqual(len(lines), 93)

        env = os.environ.copy()
        env["HOME"] = self.tmp_dir
        env.pop("CLAUDECODE", None)

        for idx, line in enumerate(lines):
            entry = json.loads(line)
            proc = subprocess.run(
                [sys.executable, str(gate_py)],
                input=json.dumps(entry["payload"]),
                text=True,
                capture_output=True,
                cwd=str(REPO_ROOT),
                env=env,
            )
            self.assertEqual(proc.returncode, 0, f"Payload Agy #{idx} falhou com exit code {proc.returncode}: {proc.stderr}")
            resp = json.loads(proc.stdout)
            self.assertIn("decision", resp)

    def test_completeness_muse(self):
        """Testa safety-gate empacotado do Muse contra recorded.jsonl (41 payloads)."""
        pkg_dir = Path(self.tmp_dir) / "pkg_muse"
        subprocess.run([sys.executable, str(PACKAGE_TOOL), "--host", "muse", "--out", str(pkg_dir)], check=True, capture_output=True)

        gate_py = pkg_dir / "hooks" / "safety-gate.py"
        fixture_file = FIXTURES_DIR / "muse" / "recorded.jsonl"
        self.assertTrue(fixture_file.is_file(), f"Fixture não encontrada: {fixture_file}")

        lines = [ln.strip() for ln in fixture_file.read_text(encoding="utf-8").splitlines() if ln.strip()]
        self.assertEqual(len(lines), 41)

        env = os.environ.copy()
        env["HOME"] = self.tmp_dir

        for idx, line in enumerate(lines):
            entry = json.loads(line)
            proc = subprocess.run(
                [sys.executable, str(gate_py)],
                input=json.dumps(entry["payload"]),
                text=True,
                capture_output=True,
                cwd=str(REPO_ROOT),
                env=env,
            )
            self.assertEqual(proc.returncode, 0, f"Payload Muse #{idx} falhou com exit {proc.returncode}: {proc.stderr}")
            # No Muse, payloads inofensivos observados devem responder com {}
            resp = json.loads(proc.stdout)
            self.assertEqual(resp, {}, f"Payload Muse #{idx} esperado {{}}, obteve: {resp}")

    def test_completeness_claude_code(self):
        """Testa safety-gate empacotado do Claude Code contra recorded.jsonl (14 payloads)."""
        pkg_dir = Path(self.tmp_dir) / "pkg_claude"
        subprocess.run([sys.executable, str(PACKAGE_TOOL), "--host", "claude-code", "--out", str(pkg_dir)], check=True, capture_output=True)

        gate_py = pkg_dir / "scripts" / "safety-gate.py"
        fixture_file = FIXTURES_DIR / "claude_code" / "recorded.jsonl"
        self.assertTrue(fixture_file.is_file(), f"Fixture não encontrada: {fixture_file}")

        lines = [ln.strip() for ln in fixture_file.read_text(encoding="utf-8").splitlines() if ln.strip()]
        self.assertEqual(len(lines), 14)

        env = os.environ.copy()
        env["HOME"] = self.tmp_dir
        env["CLAUDECODE"] = "1"

        for idx, line in enumerate(lines):
            entry = json.loads(line)
            proc = subprocess.run(
                [sys.executable, str(gate_py)],
                input=json.dumps(entry["payload"]),
                text=True,
                capture_output=True,
                cwd=str(REPO_ROOT),
                env=env,
            )
            self.assertEqual(proc.returncode, 0, f"Payload Claude #{idx} falhou com exit {proc.returncode}: {proc.stderr}")
            resp = json.loads(proc.stdout)
            self.assertEqual(resp, {}, f"Payload Claude #{idx} esperado {{}}, obteve: {resp}")

    def test_negative_control_muse_adapter_missing(self):
        """
        Controle Negativo:
        Remove adapters/muse.py do pacote temporário do Muse.
        O teste de completude DEVE reprovar E o gate NÃO DEVE falhar aberto (responde deny).
        """
        pkg_dir = Path(self.tmp_dir) / "pkg_muse_corrupted"
        subprocess.run([sys.executable, str(PACKAGE_TOOL), "--host", "muse", "--out", str(pkg_dir)], check=True, capture_output=True)

        muse_adapter_file = pkg_dir / "hooks" / "adapters" / "muse.py"
        self.assertTrue(muse_adapter_file.is_file())
        muse_adapter_file.unlink()

        gate_py = pkg_dir / "hooks" / "safety-gate.py"
        fixture_file = FIXTURES_DIR / "muse" / "recorded.jsonl"
        first_line = fixture_file.read_text(encoding="utf-8").splitlines()[0]
        first_payload = json.loads(first_line)["payload"]

        env = os.environ.copy()
        env["HOME"] = self.tmp_dir

        proc = subprocess.run(
            [sys.executable, str(gate_py)],
            input=json.dumps(first_payload),
            text=True,
            capture_output=True,
            cwd=str(REPO_ROOT),
            env=env,
        )

        resp = json.loads(proc.stdout)
        # 1. Reprovou no teste de completude (não retornou {})
        self.assertNotEqual(resp, {}, "Controle negativo FALHOU: o pacote corrompido permitiu a execução!")
        # 2. Respondeu block (fail-closed garantido pelo fallback nativo do Muse com exit 0 — BI1)
        self.assertEqual(resp.get("decision"), "block", f"Controle negativo: esperado 'block', obteve {resp}")
        self.assertEqual(proc.returncode, 0, f"Esperado exit 0 para Muse no fallback, obteve {proc.returncode}")
        self.assertIn("Falha crítica de importação", resp.get("reason", ""))


if __name__ == "__main__":
    unittest.main()
