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
from adapters.claude_code import ClaudeCodeAdapter
from ceh_core.engine import Request, Decision

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "adapters"


class TestHostAdapters(unittest.TestCase):
    """Testes unitários dos adaptadores de host isolados e em matriz de fixtures."""

    def setUp(self):
        self.agy_adapter = AntigravityAdapter()
        self.claude_adapter = ClaudeCodeAdapter()

    def test_adapter_contracts(self):
        """Verifica se os adaptadores herdam de HostAdapter e expõem propriedades canônicas."""
        self.assertIsInstance(self.agy_adapter, HostAdapter)
        self.assertIsInstance(self.claude_adapter, HostAdapter)
        self.assertEqual(self.agy_adapter.name, "antigravity")
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


if __name__ == "__main__":
    unittest.main()
