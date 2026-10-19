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

    def cert(self, status="PASS", commit=None, canonical=True, evals="APROVA", evals_commit=None):
        (self.repo / ".ceh").mkdir(exist_ok=True)
        (self.repo / ".ceh" / "last-ci-run.json").write_text(json.dumps({
            "commit_hash": commit or self.head, "timestamp": "2026-09-25T00:00:00Z", "command": "make test",
            "normalized_runner": "make test", "canonical_verified": canonical, "status": status,
            "exit_code": 0 if status == "PASS" else 1}))
        if evals is not None:
            (self.repo / ".ceh" / "last-evals-run.json").write_text(json.dumps({
                "commit": evals_commit or commit or self.head, "verdict": evals,
                "passed": 5 if evals == "APROVA" else 4, "total": 5,
                "timestamp": "2026-09-25T00:00:00Z"}))

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

    def test_forbidden_claim_rejected_in_strict(self):
        self.cert()
        # Afirmações proibidas com palavras de suíte/evals e estado são recusadas sob --strict
        self.run_report("--strict", "--claim", "Suíte 53/53 PASS", "proof.json", expect_code=1)
        self.run_report("--strict", "--claim", "Suíte canônica 53/53 PASS", "proof.json", expect_code=1)
        self.run_report("--strict", "--criterion", "Smoke-evals 5/5 aprovado", "proof.json", expect_code=1)

    def test_legitimate_phrases_accepted_in_strict(self):
        self.cert()
        # Z1: Frases legítimas contendo 'evaluates' ou 'bypass' não devem ser falsamente recusadas
        out = self.run_report("--strict",
                              "--claim", "Gate evaluates bypass de find -delete", "proof.json",
                              "--claim", "Contrato de evaluate_command cobre 12/12 variantes", "proof.json")
        self.assertIn("**VERIFICADO**", out)

    def test_evals_certificate_observed(self):
        self.cert()
        out = self.run_report()
        self.assertIn("Smoke-evals: **PASS** (`OBSERVED`)", out)
        self.assertIn("5/5 critérios (APROVA)", out)

    def test_evals_stale_certificate(self):
        self.cert(evals_commit="0" * 40)
        out = self.run_report()
        self.assertIn("Smoke-evals: **STALE** (`OBSERVED`)", out)
        self.assertIn("[DESATUALIZADO]", out)
        self.assertIn("**NAO_VERIFICADO**", out)

    def test_integrations_absent_is_silent_and_not_penalized(self):
        # M2 (degradação graciosa): sem integrações declaradas, sem seção e sem penalidade
        self.cert()
        out = self.run_report()
        self.assertNotIn("## INTEGRATIONS", out)
        self.assertIn("**VERIFICADO**", out)

    def test_integrations_validated_when_tests_pass(self):
        # M2: Repositório com hook configurado e script existente alcança validated se testes PASS
        (self.repo / "gate.py").write_text("#!/usr/bin/env python3\n")
        (self.repo / "hooks.json").write_text(json.dumps({
            "test-hook": {
                "enabled": True,
                "PreToolUse": [{"matcher": "run_command", "hooks": [{"command": "python3 gate.py"}]}]
            }
        }))
        sh(self.repo, "git", "add", ".")
        sh(self.repo, "git", "commit", "-qm", "feat: add hook")
        new_head = sh(self.repo, "git", "rev-parse", "HEAD")
        self.cert(commit=new_head)
        out = self.run_report()
        self.assertIn("## INTEGRATIONS", out)
        self.assertIn("[validated] test-hook (hook)", out)
        self.assertIn("**VERIFICADO**", out)

    def test_integrations_configured_without_execution_blocks_verification(self):
        # M2: Hook configurado sem execução de testes fica configured without execution e impede VERIFICADO
        (self.repo / "gate.py").write_text("#!/usr/bin/env python3\n")
        (self.repo / "hooks.json").write_text(json.dumps({
            "test-hook": {
                "enabled": True,
                "PreToolUse": [{"matcher": "run_command", "hooks": [{"command": "python3 gate.py"}]}]
            }
        }))
        sh(self.repo, "git", "add", ".")
        sh(self.repo, "git", "commit", "-qm", "feat: add hook without tests")
        out = self.run_report()
        self.assertIn("## INTEGRATIONS", out)
        self.assertIn("[configured without execution] test-hook (hook)", out)
        self.assertIn("**NAO_VERIFICADO**", out)

    def test_integrations_pending_when_script_missing_fails_verification(self):
        # M2: Hook com script ausente fica pending e leva a FALHOU
        (self.repo / "hooks.json").write_text(json.dumps({
            "broken-hook": {
                "enabled": True,
                "PreToolUse": [{"matcher": "run_command", "hooks": [{"command": "python3 nonexistent_script.py"}]}]
            }
        }))
        sh(self.repo, "git", "add", ".")
        sh(self.repo, "git", "commit", "-qm", "feat: broken hook")
        new_head = sh(self.repo, "git", "rev-parse", "HEAD")
        self.cert(commit=new_head)
        out = self.run_report()
        self.assertIn("## INTEGRATIONS", out)
        self.assertIn("[pending] broken-hook (hook)", out)
        self.assertIn("**FALHOU**", out)

    def test_integrations_mcp_validated_when_command_in_path_and_tests_pass(self):
        # M2: Servidor MCP com comando existente no PATH alcança validated se testes PASS
        (self.repo / ".mcp.json").write_text(json.dumps({
            "mcpServers": {
                "test-mcp": {"command": "python3"}
            }
        }))
        sh(self.repo, "git", "add", ".")
        sh(self.repo, "git", "commit", "-qm", "feat: add mcp")
        new_head = sh(self.repo, "git", "rev-parse", "HEAD")
        self.cert(commit=new_head)
        out = self.run_report()
        self.assertIn("## INTEGRATIONS", out)
        self.assertIn("[validated] test-mcp (mcp)", out)
        self.assertIn("**VERIFICADO**", out)

    def test_integrations_mcp_pending_when_command_missing_fails_verification(self):
        # M2: Servidor MCP com comando ausente no PATH fica pending e leva a FALHOU
        (self.repo / ".mcp.json").write_text(json.dumps({
            "mcpServers": {
                "broken-mcp": {"command": "nonexistent_binary_xyz_12345"}
            }
        }))
        sh(self.repo, "git", "add", ".")
        sh(self.repo, "git", "commit", "-qm", "feat: broken mcp")
        new_head = sh(self.repo, "git", "rev-parse", "HEAD")
        self.cert(commit=new_head)
        out = self.run_report()
        self.assertIn("## INTEGRATIONS", out)
        self.assertIn("[pending] broken-mcp (mcp)", out)
        self.assertIn("**FALHOU**", out)

    def test_integrations_mcp_pending_when_file_corrupt(self):
        # M2: Arquivo .mcp.json com JSON corrompido fica pending e leva a FALHOU
        (self.repo / ".mcp.json").write_text("{ broken json: true")
        sh(self.repo, "git", "add", ".")
        sh(self.repo, "git", "commit", "-qm", "feat: corrupt mcp")
        new_head = sh(self.repo, "git", "rev-parse", "HEAD")
        self.cert(commit=new_head)
        out = self.run_report()
        self.assertIn("## INTEGRATIONS", out)
        self.assertIn("[pending] .mcp.json (mcp)", out)
        self.assertIn("**FALHOU**", out)

    def test_integrations_pending_when_direct_executable_missing_fails_verification(self):
        # M2: Hook com executável direto ausente (parts[0]) fica pending e leva a FALHOU
        (self.repo / "hooks.json").write_text(json.dumps({
            "broken-direct-hook": {
                "enabled": True,
                "PreToolUse": [{"matcher": "run_command", "hooks": [{"command": "./nonexistent_gate.sh --check"}]}]
            }
        }))
        sh(self.repo, "git", "add", ".")
        sh(self.repo, "git", "commit", "-qm", "feat: broken direct hook")
        new_head = sh(self.repo, "git", "rev-parse", "HEAD")
        self.cert(commit=new_head)
        out = self.run_report()
        self.assertIn("## INTEGRATIONS", out)
        self.assertIn("[pending] broken-direct-hook (hook)", out)
        self.assertIn("executável local `./nonexistent_gate.sh` não encontrado", out)
        self.assertIn("**FALHOU**", out)

    def test_integrations_pending_when_system_binary_missing_fails_verification(self):
        # M2: Hook com comando ausente no PATH (parts[0]) fica pending e leva a FALHOU
        (self.repo / "hooks.json").write_text(json.dumps({
            "broken-binary-hook": {
                "enabled": True,
                "PreToolUse": [{"matcher": "run_command", "hooks": [{"command": "nonexistent_binary_xyz_98765"}]}]
            }
        }))
        sh(self.repo, "git", "add", ".")
        sh(self.repo, "git", "commit", "-qm", "feat: broken binary hook")
        new_head = sh(self.repo, "git", "rev-parse", "HEAD")
        self.cert(commit=new_head)
        out = self.run_report()
        self.assertIn("## INTEGRATIONS", out)
        self.assertIn("[pending] broken-binary-hook (hook)", out)
        self.assertIn("comando `nonexistent_binary_xyz_98765` ausente no PATH", out)
        self.assertIn("**FALHOU**", out)

    def test_integrations_pending_when_hooks_json_is_list(self):
        # M2: hooks.json com lista [] em vez de dict fica pending e leva a FALHOU
        (self.repo / "hooks.json").write_text("[]\n")
        sh(self.repo, "git", "add", ".")
        sh(self.repo, "git", "commit", "-qm", "feat: list hooks.json")
        new_head = sh(self.repo, "git", "rev-parse", "HEAD")
        self.cert(commit=new_head)
        out = self.run_report()
        self.assertIn("## INTEGRATIONS", out)
        self.assertIn("[pending] hooks.json (hook)", out)
        self.assertIn("estrutura inválida (esperado objeto/dicionário)", out)
        self.assertIn("**FALHOU**", out)

    def test_integrations_mcp_pending_when_mcp_json_is_list(self):
        # M2: .mcp.json com lista [] em vez de dict fica pending e leva a FALHOU
        (self.repo / ".mcp.json").write_text("[]\n")
        sh(self.repo, "git", "add", ".")
        sh(self.repo, "git", "commit", "-qm", "feat: list .mcp.json")
        new_head = sh(self.repo, "git", "rev-parse", "HEAD")
        self.cert(commit=new_head)
        out = self.run_report()
        self.assertIn("## INTEGRATIONS", out)
        self.assertIn("[pending] .mcp.json (mcp)", out)
        self.assertIn("estrutura inválida (esperado objeto/dicionário)", out)
        self.assertIn("**FALHOU**", out)

    def test_integrations_mcp_pending_when_command_field_missing(self):
        # M2: servidor MCP sem campo 'command' fica pending e leva a FALHOU
        (self.repo / ".mcp.json").write_text(json.dumps({
            "mcpServers": {
                "server-without-command": {"args": ["run"]}
            }
        }))
        sh(self.repo, "git", "add", ".")
        sh(self.repo, "git", "commit", "-qm", "feat: mcp without command")
        new_head = sh(self.repo, "git", "rev-parse", "HEAD")
        self.cert(commit=new_head)
        out = self.run_report()
        self.assertIn("## INTEGRATIONS", out)
        self.assertIn("[pending] server-without-command (mcp)", out)
        self.assertIn("servidor MCP `server-without-command` sem comando declarado", out)
        self.assertIn("**FALHOU**", out)

    def test_integrations_pending_when_direct_executable_lacks_x_bit(self):
        # PR-17: Executável direto sem permissão de execução (+x) fica pending e leva a FALHOU
        gate = self.repo / "gate.sh"
        gate.write_text("#!/bin/sh\necho ok\n")
        gate.chmod(0o644)
        (self.repo / "hooks.json").write_text(json.dumps({
            "no-x-hook": {
                "enabled": True,
                "PreToolUse": [{"matcher": "run_command", "hooks": [{"command": "./gate.sh"}]}]
            }
        }))
        sh(self.repo, "git", "add", ".")
        sh(self.repo, "git", "commit", "-qm", "feat: non executable gate")
        new_head = sh(self.repo, "git", "rev-parse", "HEAD")
        self.cert(commit=new_head)
        out = self.run_report()
        self.assertIn("## INTEGRATIONS", out)
        self.assertIn("[pending] no-x-hook (hook)", out)
        self.assertIn("sem permissão de execução", out)
        self.assertIn("**FALHOU**", out)

    def test_integrations_validated_when_env_prefix_present_and_tests_pass(self):
        # PR-17: Atribuições de variáveis de ambiente no comando (ex: PYTHONPATH=lib python3 gate.py) são ignoradas no parse do binário
        (self.repo / "gate.py").write_text("#!/usr/bin/env python3\n")
        (self.repo / "hooks.json").write_text(json.dumps({
            "env-prefix-hook": {
                "enabled": True,
                "PreToolUse": [{"matcher": "run_command", "hooks": [{"command": "PYTHONPATH=. FOO=bar python3 gate.py"}]}]
            }
        }))
        sh(self.repo, "git", "add", ".")
        sh(self.repo, "git", "commit", "-qm", "feat: env prefix hook")
        new_head = sh(self.repo, "git", "rev-parse", "HEAD")
        self.cert(commit=new_head)
        out = self.run_report()
        self.assertIn("## INTEGRATIONS", out)
        self.assertIn("[validated] env-prefix-hook (hook)", out)
        self.assertIn("**VERIFICADO**", out)

    def test_integrations_mcp_pending_when_direct_executable_lacks_x_bit(self):
        # PR-17: Executável MCP local sem permissão de execução (+x) fica pending e leva a FALHOU
        mcp_bin = self.repo / "mcp_server"
        mcp_bin.write_text("#!/bin/sh\necho ok\n")
        mcp_bin.chmod(0o644)
        (self.repo / ".mcp.json").write_text(json.dumps({
            "mcpServers": {
                "no-x-mcp": {"command": "./mcp_server"}
            }
        }))
        sh(self.repo, "git", "add", ".")
        sh(self.repo, "git", "commit", "-qm", "feat: non executable mcp")
        new_head = sh(self.repo, "git", "rev-parse", "HEAD")
        self.cert(commit=new_head)
        out = self.run_report()
        self.assertIn("## INTEGRATIONS", out)
        self.assertIn("[pending] no-x-mcp (mcp)", out)
        self.assertIn("sem permissão de execução", out)
        self.assertIn("**FALHOU**", out)


if __name__ == "__main__":
    unittest.main(verbosity=1)

