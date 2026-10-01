#!/usr/bin/env python3
"""
test_adapters.py — Testes formais dos adaptadores de host (PR-14/15).
Valida o contrato HostAdapter, detecção, parsing, renderização e resolução
de diretório para AntigravityAdapter e ClaudeCodeAdapter.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from adapters.base import HostAdapter
from adapters.antigravity import AntigravityAdapter
from adapters.muse import MuseAdapter
from adapters.claude_code import ClaudeCodeAdapter
from ceh_core.engine import Request, Decision
from hook_context import find_adapter, ADAPTERS

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "adapters"


class TestHostAdapters(unittest.TestCase):
    """Testes unitários dos adaptadores de host isolados e em matriz de fixtures."""

    def setUp(self):
        self.agy_adapter = AntigravityAdapter()
        self.muse_adapter = MuseAdapter()
        self.claude_adapter = ClaudeCodeAdapter()

    def test_adapter_contracts(self):
        """Verifica se os adaptadores herdam de HostAdapter e expõem propriedades canônicas."""
        self.assertIsInstance(self.agy_adapter, HostAdapter)
        self.assertIsInstance(self.muse_adapter, HostAdapter)
        self.assertIsInstance(self.claude_adapter, HostAdapter)
        self.assertEqual(self.agy_adapter.name, "antigravity")
        self.assertEqual(self.muse_adapter.name, "muse")
        self.assertEqual(self.claude_adapter.name, "claude_code")

    def test_antigravity_detect_independent_of_claude_env(self):
        """Critério B1: Antigravity detecta payload com toolCall mesmo sob variáveis CLAUDE* no ambiente."""
        payload = {"toolCall": {"name": "run_command", "args": {"CommandLine": "ls"}}}
        with patch.dict(os.environ, {"CLAUDECODE": "1", "CLAUDE_PROJECT_DIR": "/tmp"}):
            self.assertTrue(self.agy_adapter.detect(payload))
            self.assertFalse(self.claude_adapter.detect(payload), "ClaudeAdapter não deve roubar payload com toolCall")

    def test_claude_detect_native_payload(self):
        """ClaudeAdapter detecta payloads nativos com hook_event_name ou tool_name."""
        payload = {"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": "ls"}}
        self.assertTrue(self.claude_adapter.detect(payload))
        self.assertFalse(self.agy_adapter.detect(payload))

    def test_antigravity_fixtures_matrix(self):
        """Executa a matriz completa de fixtures do Antigravity."""
        fixture_file = FIXTURES_DIR / "antigravity" / "cases.jsonl"
        self.assertTrue(fixture_file.is_file(), f"Fixture não encontrada: {fixture_file}")

        with open(fixture_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                case = json.loads(line)
                name = case["name"]
                payload = case["payload"]

                with self.subTest(case=name):
                    self.assertTrue(self.agy_adapter.detect(payload))

                    if "error_pattern" in case:
                        with self.assertRaises(ValueError) as ctx:
                            self.agy_adapter.parse(payload)
                        self.assertIn(case["error_pattern"], str(ctx.exception))
                        res, exit_code = self.agy_adapter.render_error(str(ctx.exception), payload)
                        self.assertEqual(exit_code, case["expected_exit_code"])
                        self.assertEqual(res["decision"], "deny")
                        self.assertIn(case["error_pattern"], res["reason"])
                    else:
                        req = self.agy_adapter.parse(payload)
                        self.assertEqual(req.command, case["expected_command"])
                        self.assertEqual(req.target_paths, case["expected_target_paths"])
                        dec = Decision(decision=case["expected_decision"], reason="Teste")
                        res, exit_code = self.agy_adapter.render(dec, payload)
                        self.assertEqual(exit_code, case["expected_exit_code"])
                        self.assertEqual(res["decision"], case["expected_decision"])

    def test_claude_fixtures_matrix(self):
        """Executa a matriz completa de fixtures do Claude Code."""
        fixture_file = FIXTURES_DIR / "claude_code" / "cases.jsonl"
        self.assertTrue(fixture_file.is_file(), f"Fixture não encontrada: {fixture_file}")

        with open(fixture_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                case = json.loads(line)
                name = case["name"]
                payload = case["payload"]

                with self.subTest(case=name):
                    self.assertTrue(self.claude_adapter.detect(payload))

                    if "error_pattern" in case:
                        with self.assertRaises(ValueError) as ctx:
                            self.claude_adapter.parse(payload)
                        self.assertIn(case["error_pattern"], str(ctx.exception))
                        res, exit_code = self.claude_adapter.render_error(str(ctx.exception), payload)
                        self.assertEqual(exit_code, case["expected_exit_code"])
                        hso = res["hookSpecificOutput"]
                        self.assertEqual(hso["permissionDecision"], "deny")
                        self.assertIn(case["error_pattern"], hso["permissionDecisionReason"])
                    else:
                        req = self.claude_adapter.parse(payload)
                        self.assertEqual(req.command, case["expected_command"])
                        self.assertEqual(req.target_paths, case["expected_target_paths"])
                        dec = Decision(decision=case["expected_decision"], reason="Teste")
                        res, exit_code = self.claude_adapter.render(dec, payload)
                        self.assertEqual(exit_code, case["expected_exit_code"])
                        if case["expected_decision"] == "allow":
                            self.assertEqual(res, {})
                        else:
                            hso = res["hookSpecificOutput"]
                            self.assertEqual(hso["permissionDecision"], case["expected_decision"])

    def test_antigravity_ask_converts_to_deny_exit_0(self):
        """Garante que 'ask' no Antigravity converte para 'deny' com exit 0 (H1, Handoff 006)."""
        dec = Decision(decision="ask", reason="Confirmação necessária")
        res, exit_code = self.agy_adapter.render(dec)
        self.assertEqual(exit_code, 0)
        self.assertEqual(res["decision"], "deny")
        self.assertIn("[CEH CONTEXT LOCK]", res["reason"])

    def test_claude_ask_preserves_ask_exit_0(self):
        """Critério B2: No Claude Code, 'ask' é preservado e sai com exit 0."""
        dec = Decision(decision="ask", reason="Confirmação necessária")
        res, exit_code = self.claude_adapter.render(dec)
        self.assertEqual(exit_code, 0)
        self.assertIn("hookSpecificOutput", res)
        hso = res["hookSpecificOutput"]
        self.assertEqual(hso["permissionDecision"], "ask")
        self.assertEqual(hso["permissionDecisionReason"], "Confirmação necessária")

    def test_antigravity_target_resolution(self):
        """Valida a resolução de diretório alvo no Antigravity via Cwd e workspacePaths."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir).resolve()
            sub_path = tmp_path / "sub"
            sub_path.mkdir()

            # Caso 1: Cwd absoluto
            p1 = {"toolCall": {"name": "run_command", "args": {"Cwd": str(sub_path)}}}
            target, env, force_deny = self.agy_adapter.resolve_target(p1)
            self.assertEqual(target, sub_path)
            self.assertFalse(force_deny)

            # Caso 2: Cwd relativo via workspacePaths
            p2 = {"workspacePaths": [str(tmp_path)], "toolCall": {"name": "run_command", "args": {"Cwd": "sub"}}}
            target, env, force_deny = self.agy_adapter.resolve_target(p2)
            self.assertEqual(target, sub_path)
            self.assertFalse(force_deny)

            # Caso 3: Cwd inexistente -> force_deny_push
            p3 = {"toolCall": {"name": "run_command", "args": {"Cwd": "/caminho/inexistente/xyz"}}}
            target, env, force_deny = self.agy_adapter.resolve_target(p3)
            self.assertIsNone(target)
            self.assertTrue(force_deny)

    def test_claude_target_resolution(self):
        """Valida a resolução de diretório alvo no Claude Code via payload.cwd ou tool_input.Cwd."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir).resolve()

            # Caso 1: payload.cwd
            p1 = {"hook_event_name": "PreToolUse", "tool_name": "Bash", "cwd": str(tmp_path), "tool_input": {}}
            target, env, force_deny = self.claude_adapter.resolve_target(p1)
            self.assertEqual(target, tmp_path)
            self.assertFalse(force_deny)

            # Caso 2: tool_input.Cwd
            p2 = {"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"Cwd": str(tmp_path)}}
            target, env, force_deny = self.claude_adapter.resolve_target(p2)
            self.assertEqual(target, tmp_path)
            self.assertFalse(force_deny)

            # Caso 3: inexistente
            p3 = {"hook_event_name": "PreToolUse", "tool_name": "Bash", "cwd": "/caminho/nao/existe"}
            target, env, force_deny = self.claude_adapter.resolve_target(p3)
            self.assertIsNone(target)
            self.assertTrue(force_deny)

    def test_claude_parse_populates_cwd(self):
        """Valida que o parse do Claude Code preenche req.cwd a partir do diretório resolvido."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir).resolve()
            payload = {"hook_event_name": "PreToolUse", "tool_name": "Bash", "cwd": str(tmp_path), "tool_input": {"command": "ls -la"}}
            req = self.claude_adapter.parse(payload)
            self.assertEqual(req.cwd, tmp_path)

    def test_antigravity_parse_populates_cwd(self):
        """Valida que o parse do Antigravity preenche req.cwd a partir do Cwd resolvido."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir).resolve()
            payload = {"toolCall": {"name": "run_command", "args": {"CommandLine": "ls -la", "Cwd": str(tmp_path)}}}
            req = self.agy_adapter.parse(payload)
            self.assertEqual(req.cwd, tmp_path)

    def test_muse_detect_unambiguous(self):
        """Critério PR-15b: MuseAdapter detecta 41/41 Muse, 0/14 Claude e 0/93 Antigravity."""
        def load_payloads(rel_path: str):
            fpath = FIXTURES_DIR / rel_path
            with open(fpath, "r", encoding="utf-8") as f:
                return [json.loads(line)["payload"] for line in f if line.strip()]

        muse_payloads = load_payloads("muse/recorded.jsonl")
        claude_payloads = load_payloads("claude_code/recorded.jsonl")
        agy_payloads = load_payloads("antigravity/recorded.jsonl")

        self.assertEqual(len(muse_payloads), 41)
        self.assertEqual(len(claude_payloads), 14)
        self.assertEqual(len(agy_payloads), 93)

        # Muse detecta 41/41 do Muse, 0 do Claude, 0 do Antigravity
        self.assertEqual(sum(1 for p in muse_payloads if self.muse_adapter.detect(p)), 41)
        self.assertEqual(sum(1 for p in claude_payloads if self.muse_adapter.detect(p)), 0)
        self.assertEqual(sum(1 for p in agy_payloads if self.muse_adapter.detect(p)), 0)

        # Despachante: ordem explícita roteia cada conjunto ao adaptador correto
        self.assertEqual(sum(1 for p in muse_payloads if find_adapter(p) and find_adapter(p).name == "muse"), 41)
        self.assertEqual(sum(1 for p in claude_payloads if find_adapter(p) and find_adapter(p).name == "claude_code"), 14)
        self.assertEqual(sum(1 for p in agy_payloads if find_adapter(p) and find_adapter(p).name == "antigravity"), 93)

    def test_muse_fixtures_matrix(self):
        """Executa a matriz de fixtures manuais do Muse (cases.jsonl)."""
        fixture_file = FIXTURES_DIR / "muse" / "cases.jsonl"
        self.assertTrue(fixture_file.is_file(), f"Fixture não encontrada: {fixture_file}")

        with open(fixture_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                case = json.loads(line)
                name = case["name"]
                payload = case["payload"]

                with self.subTest(case=name):
                    self.assertTrue(self.muse_adapter.detect(payload))

                    if "error_pattern" in case:
                        with self.assertRaises(ValueError) as ctx:
                            self.muse_adapter.parse(payload)
                        self.assertIn(case["error_pattern"], str(ctx.exception))
                        res, exit_code = self.muse_adapter.render_error(str(ctx.exception), payload)
                        self.assertEqual(exit_code, case["expected_exit_code"])
                        self.assertEqual(res["decision"], "block")
                        self.assertIn(case["error_pattern"], res["reason"])
                    else:
                        req = self.muse_adapter.parse(payload)
                        self.assertEqual(req.command, case["expected_command"])
                        self.assertEqual(req.target_paths, case["expected_target_paths"])
                        dec = Decision(decision=case["expected_decision"], reason="Teste")
                        res, exit_code = self.muse_adapter.render(dec, payload)
                        self.assertEqual(exit_code, case["expected_exit_code"])
                        if case["expected_decision"] == "allow":
                            self.assertEqual(res, {})
                        else:
                            self.assertEqual(res["decision"], "block")

    def test_muse_recorded_fixtures_matrix(self):
        """Executa a matriz dos 41 payloads reais gravados do Muse (recorded.jsonl)."""
        fixture_file = FIXTURES_DIR / "muse" / "recorded.jsonl"
        self.assertTrue(fixture_file.is_file(), f"Fixture não encontrada: {fixture_file}")

        with open(fixture_file, "r", encoding="utf-8") as f:
            lines = [ln.strip() for ln in f if ln.strip()]

        self.assertEqual(len(lines), 41)
        for idx, line in enumerate(lines):
            case = json.loads(line)
            payload = case["payload"]
            with self.subTest(index=idx, tool=payload.get("tool_name")):
                self.assertTrue(self.muse_adapter.detect(payload))
                req = self.muse_adapter.parse(payload)
                self.assertIsInstance(req, Request)
                dec = Decision(decision="allow", reason="OK")
                res, exit_code = self.muse_adapter.render(dec, payload)
                self.assertEqual(exit_code, 0)
                self.assertEqual(res, {})

                # Teste com bloqueio: sempre exit 0 e {"decision": "block"}
                dec_block = Decision(decision="deny", reason="Bloqueio CEH")
                res_block, exit_block = self.muse_adapter.render(dec_block, payload)
                self.assertEqual(exit_block, 0)
                self.assertEqual(res_block["decision"], "block")
                self.assertEqual(res_block["reason"], "Bloqueio CEH")

    def test_antigravity_recorded_fixtures_matrix(self):
        """Valida detecção dos 93 payloads reais gravados do Antigravity."""
        fixture_file = FIXTURES_DIR / "antigravity" / "recorded.jsonl"
        self.assertTrue(fixture_file.is_file(), f"Fixture não encontrada: {fixture_file}")
        with open(fixture_file, "r", encoding="utf-8") as f:
            lines = [ln.strip() for ln in f if ln.strip()]
        self.assertEqual(len(lines), 93)
        for idx, line in enumerate(lines):
            case = json.loads(line)
            self.assertTrue(self.agy_adapter.detect(case["payload"]))

    def test_claude_recorded_fixtures_matrix(self):
        """Valida detecção dos 14 payloads reais gravados do Claude Code."""
        fixture_file = FIXTURES_DIR / "claude_code" / "recorded.jsonl"
        self.assertTrue(fixture_file.is_file(), f"Fixture não encontrada: {fixture_file}")
        with open(fixture_file, "r", encoding="utf-8") as f:
            lines = [ln.strip() for ln in f if ln.strip()]
        self.assertEqual(len(lines), 14)
        for idx, line in enumerate(lines):
            case = json.loads(line)
            self.assertTrue(self.claude_adapter.detect(case["payload"]))

    def test_muse_render_decisions(self):
        """Garante que o Muse sempre responde com exit 0 ({} para allow, block para deny/ask)."""
        dec_allow = Decision(decision="allow", reason="")
        res, ec = self.muse_adapter.render(dec_allow)
        self.assertEqual(ec, 0)
        self.assertEqual(res, {})

        dec_deny = Decision(decision="deny", reason="Comando bloqueado")
        res, ec = self.muse_adapter.render(dec_deny)
        self.assertEqual(ec, 0)
        self.assertEqual(res, {"decision": "block", "reason": "Comando bloqueado"})

        dec_ask = Decision(decision="ask", reason="Confirmação solicitada")
        res, ec = self.muse_adapter.render(dec_ask)
        self.assertEqual(ec, 0)
        self.assertEqual(res, {"decision": "block", "reason": "Confirmação solicitada"})

        res, ec = self.muse_adapter.render_error("Erro de sintaxe")
        self.assertEqual(ec, 0)
        self.assertEqual(res, {"decision": "block", "reason": "Erro de sintaxe"})

    def test_muse_target_resolution(self):
        """Valida resolução de diretório no Muse com symlinks reais resolvidos via Path.resolve()."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir).resolve()
            sub_path = tmp_path / "subdir"
            sub_path.mkdir()

            # Caso 1: tool_input.workdir absoluto
            p1 = {"tool_name": "bash", "tool_input": {"workdir": str(sub_path), "command": "ls"}}
            target, env, force_deny = self.muse_adapter.resolve_target(p1)
            self.assertEqual(target, sub_path)
            self.assertFalse(force_deny)

            # Caso 2: payload.cwd absoluto
            p2 = {"tool_name": "bash", "cwd": str(sub_path), "tool_input": {"command": "ls"}}
            target, env, force_deny = self.muse_adapter.resolve_target(p2)
            self.assertEqual(target, sub_path)
            self.assertFalse(force_deny)

            # Caso 3: caminho inexistente -> force_deny
            p3 = {"tool_name": "bash", "cwd": "/caminho/inexistente/muse/xyz", "tool_input": {"command": "ls"}}
            target, env, force_deny = self.muse_adapter.resolve_target(p3)
            self.assertIsNone(target)
            self.assertTrue(force_deny)

    def test_gate_decision_independent_of_claude_env(self):
        """D4 item 5 / H10: Prova que a decisão avaliada pelo gate não se altera pela presença de variáveis CLAUDE*."""
        from ceh_core.engine import evaluate

        commands = [
            ("ls -la", "allow"),
            ("rm -rf /", "deny"),
            ("git status", "allow"),
        ]
        claude_vars = {
            "CLAUDECODE": "1",
            "CLAUDE_PROJECT_DIR": "/tmp",
            "CLAUDE_CODE_ENTRYPOINT": "cli",
            "CLAUDE_PID": "12345",
        }

        for cmd, expected_decision in commands:
            with patch.dict(os.environ, {}, clear=True):
                req_clean = Request(command=cmd, cwd="/tmp", explicit_env="development")
                dec_clean = evaluate(req_clean)
                self.assertEqual(dec_clean.decision, expected_decision)

            with patch.dict(os.environ, claude_vars, clear=False):
                req_claude = Request(command=cmd, cwd="/tmp", explicit_env="development")
                dec_claude = evaluate(req_claude)
                self.assertEqual(dec_claude.decision, expected_decision)
                self.assertEqual(dec_clean.decision, dec_claude.decision)


if __name__ == "__main__":
    unittest.main()
