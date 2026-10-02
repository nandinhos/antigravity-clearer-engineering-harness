#!/usr/bin/env python3
"""
test_engine.py — Testes unitarios do motor agnostico de avaliacao (ceh_core.engine).
Valida contratos Request -> Decision sem passagem por stdin ou formatos de host,
em sandbox hermetico isolado de ambiente e certificado.
"""
import os
import json
import shutil
import tempfile
import unittest
import subprocess
from pathlib import Path

_SCRIPTS_DIR = str(Path(__file__).resolve().parents[1] / "scripts")
import sys
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from ceh_core.engine import Request, Decision, evaluate

_TOOLS_DIR = Path(__file__).resolve().parent / "tools"
sys.path.insert(0, str(_TOOLS_DIR))
from test_helpers import mkdtemp_resolved


class TestEngineAgnostic(unittest.TestCase):
    def setUp(self):
        self.repo_root = Path(__file__).resolve().parents[2]
        self.corpus_path = self.repo_root / "clearer-engineering" / "tests" / "fixtures" / "gate_corpus.expected.jsonl"
        self.tmp_repo = str(mkdtemp_resolved(prefix="ceh_engine_sandbox_"))
        self.original_cwd = os.getcwd()

        subprocess.run(["git", "init", "-b", "dev"], cwd=self.tmp_repo, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "EngineTest"], cwd=self.tmp_repo, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "engine@test.local"], cwd=self.tmp_repo, check=True, capture_output=True)
        ci_dir = Path(self.tmp_repo) / ".github" / "workflows"
        ci_dir.mkdir(parents=True, exist_ok=True)
        (ci_dir / "ci.yml").write_text("name: CI\n")
        (Path(self.tmp_repo) / "README.md").write_text("Engine Sandbox\n")
        subprocess.run(["git", "add", "."], cwd=self.tmp_repo, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=self.tmp_repo, check=True, capture_output=True)
        os.chdir(self.tmp_repo)

    def tearDown(self):
        os.chdir(self.original_cwd)
        shutil.rmtree(self.tmp_repo, ignore_errors=True)

    def test_engine_corpus_evaluation(self):
        """Verifica a avaliacao de evaluate(Request) contra amostra de todas as 1.171 decisoes do corpus."""
        self.assertTrue(self.corpus_path.is_file(), "Arquivo de corpus de referencia nao encontrado.")
        lines = [json.loads(ln) for ln in self.corpus_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        self.assertEqual(len(lines), 1171, "Corpus de teste deve conter 1.171 avaliacoes de referencia.")

        command_lines = [l for l in lines if l.get("type") == "command"]
        self.assertGreater(len(command_lines), 1000, "Deve haver mais de 1000 comandos de avaliacao no corpus.")

        # Amostra uniforme cobrindo todos os tipos de comandos do corpus (a cada 8 casos)
        sample = command_lines[::8]
        self.assertGreaterEqual(len(sample), 120)

        for entry in sample:
            cmd = entry["command"]
            env = entry["env"]
            expected_dec = entry["decision"]
            expected_uc = entry["use_case"]

            req = Request(command=cmd, cwd=self.tmp_repo, explicit_env=env)
            res = evaluate(req)

            self.assertIsInstance(res, Decision)
            self.assertEqual(
                res.decision, expected_dec,
                f"Decisao divergente para '{cmd}' em {env}: esperado {expected_dec}, obtido {res.decision}"
            )
            self.assertEqual(
                res.use_case, expected_uc,
                f"Use case divergente para '{cmd}' em {env}: esperado {expected_uc}, obtido {res.use_case}"
            )

    def test_engine_target_paths_protection(self):
        """Verifica que evaluate(Request) com target_paths protege certificados .ceh/."""
        # Alvo protegido em .ceh
        req_blocked = Request(target_paths=[".ceh/last-ci-run.json"], cwd=self.tmp_repo)
        res_blocked = evaluate(req_blocked)
        self.assertEqual(res_blocked.decision, "deny")
        self.assertEqual(res_blocked.use_case, "CERTIFICATE_INTEGRITY")
        self.assertIn("G9", res_blocked.reason)

        # Alvo seguro fora de .ceh
        req_allowed = Request(target_paths=["src/components/button.tsx"], cwd=self.tmp_repo)
        res_allowed = evaluate(req_allowed)
        self.assertEqual(res_allowed.decision, "allow")
        self.assertEqual(res_allowed.use_case, "GENERAL")

    def test_engine_catastrophic_priority(self):
        """Verifica que comandos catastroficos sofrem Early Catastrophic Check com prioridade absoluta."""
        req = Request(command="rm -rf / --no-preserve-root", cwd=self.tmp_repo, explicit_env="development")
        res = evaluate(req)
        self.assertEqual(res.decision, "deny")
        self.assertEqual(res.use_case, "CATASTROPHIC")


if __name__ == "__main__":
    unittest.main()
