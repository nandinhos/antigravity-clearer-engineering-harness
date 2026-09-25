#!/usr/bin/env python3
"""Contrato do relatório canônico de evidências (evidence-report.sh / evidence_report.py).

Cada caso roda em um repositório git descartável; o veredito tem de ser calculado
pelas evidências, nunca aceito por declaração.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPORT = Path(__file__).resolve().parents[1] / "scripts" / "evidence-report.sh"
SECTIONS = ["## RESULT", "## ENVIRONMENT", "## CHANGES", "## EVIDENCE", "## TESTS",
            "## REVIEW", "## ACCEPTANCE", "## REMAINING RISKS", "## CONFIDENCE"]


def sh(cwd: Path, *cmd: str) -> str:
    return subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


class EvidenceReportContract(unittest.TestCase):
    def setUp(self):
        self.repo = Path(tempfile.mkdtemp(prefix="ceh-report-"))
        sh(self.repo, "git", "init", "-q", "-b", "main")
        sh(self.repo, "git", "config", "user.email", "t@t.invalid")
        sh(self.repo, "git", "config", "user.name", "t")
        (self.repo / ".gitignore").write_text(".ceh/\n")
        (self.repo / "app.txt").write_text("v1\n")
        sh(self.repo, "git", "add", ".")
        sh(self.repo, "git", "commit", "-qm", "base")
        sh(self.repo, "git", "checkout", "-qb", "feature")
        (self.repo / "app.txt").write_text("v2\n")
        (self.repo / "proof.json").write_text('{"ok": true}\n')
        sh(self.repo, "git", "add", ".")
        sh(self.repo, "git", "commit", "-qm", "feat: v2")
        self.head = sh(self.repo, "git", "rev-parse", "HEAD")

    def tearDown(self):
        shutil.rmtree(self.repo, ignore_errors=True)

    def cert(self, status="PASS", commit=None, canonical=True):
        (self.repo / ".ceh").mkdir(exist_ok=True)
        (self.repo / ".ceh" / "last-ci-run.json").write_text(json.dumps({
            "commit_hash": commit or self.head, "timestamp": "2026-09-25T00:00:00Z", "command": "make test",
            "normalized_runner": "make test", "canonical_verified": canonical, "status": status,
            "exit_code": 0 if status == "PASS" else 1}))

    def run_report(self, *args, expect_code=0):
        env = dict(os.environ, CEH_ENV="development")
        res = subprocess.run(["bash", str(REPORT), "--base", "main", *args], cwd=self.repo,
                             capture_output=True, text=True, env=env)
        self.assertEqual(res.returncode, expect_code, res.stderr)
        return res.stdout

    def test_sections_and_no_certificate_is_not_verified(self):
        out = self.run_report()
        for section in SECTIONS:
            self.assertIn(section, out)
        self.assertIn("**NAO_VERIFICADO**", out)
        self.assertIn("**NOT_RUN**", out)
        self.assertIn("**BAIXA**", out)
        self.assertIn("feat: v2", out)          # o que foi realizado: commits da branch
        self.assertIn("app.txt", out)           # e arquivos alterados

    def test_verified_requires_pass_on_head_clean_tree_and_supported_claims(self):
        self.cert()
        out = self.run_report("--claim", "Versão 2 publicada", "proof.json",
                              "--criterion", "Commit da feature", f"commit:{self.head}")
        self.assertIn("**VERIFICADO**", out)
        self.assertIn("**ALTA**", out)
        self.assertIn("[SUPPORTED] Versão 2 publicada — `proof.json` (sha256", out)
        self.assertIn("- [x] Commit da feature", out)

    def test_pass_without_claims_is_medium_confidence(self):
        self.cert()
        out = self.run_report()
        self.assertIn("**VERIFICADO**", out)
        self.assertIn("**MEDIA**", out)

    def test_stale_certificate_is_not_verified(self):
        self.cert(commit="0" * 40)
        out = self.run_report()
        self.assertIn("**STALE**", out)
        self.assertIn("**NAO_VERIFICADO**", out)

    def test_failed_suite_is_failed(self):
        self.cert(status="FAIL")
        self.assertIn("**FALHOU**", self.run_report())

    def test_non_canonical_pass_is_not_verified(self):
        self.cert(canonical=False)
        out = self.run_report()
        self.assertIn("**NOT_CANONICAL**", out)
        self.assertIn("**NAO_VERIFICADO**", out)

    def test_missing_and_unversioned_proofs(self):
        self.cert()
        (self.repo / "loose.log").write_text("x\n")
        out = self.run_report("--claim", "Sem prova", "nao-existe.json", "--claim", "Prova solta", "loose.log")
        self.assertIn("[UNSUPPORTED] Sem prova", out)
        self.assertIn("[PARTIALLY_SUPPORTED] Prova solta", out)
        self.assertIn("**NAO_VERIFICADO**", out)

    def test_blocker_finding_fails_and_counts_are_computed(self):
        self.cert()
        out = self.run_report("--finding", "BLOCKER", "Quebra de contrato", "--finding", "low", "Nome ruim")
        self.assertIn("BLOCKER 1 · HIGH 0 · MEDIUM 0 · LOW 1", out)
        self.assertIn("**FALHOU**", out)

    def test_secret_in_diff_fails(self):
        fake_key = "abcdefghijklmnop" + "1234"  # montada em runtime: o literal não aparece no diff do repositório
        (self.repo / "cfg.txt").write_text("api_key = '" + fake_key + "'\n")
        sh(self.repo, "git", "add", ".")
        sh(self.repo, "git", "commit", "-qm", "cfg")
        self.head = sh(self.repo, "git", "rev-parse", "HEAD")
        self.cert()
        out = self.run_report()
        self.assertIn("1 padrão(ões) de segredo", out)
        self.assertIn("**FALHOU**", out)

    def test_declared_status_is_rejected_and_strict_exit(self):
        self.run_report("COMPLETED", "HIGH", expect_code=2)
        self.run_report("--strict", expect_code=1)


if __name__ == "__main__":
    unittest.main(verbosity=1)
