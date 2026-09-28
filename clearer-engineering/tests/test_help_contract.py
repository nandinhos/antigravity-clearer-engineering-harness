#!/usr/bin/env python3
"""
test_help_contract.py - Validação formal do contrato de opções de escrita a partir do --help (PR-QA-C2).

Garante que:
1. O contrato write_options.json DIRIGE a execução dos testes de ponta a ponta (sem listas hardcoded soltas).
2. Todo comando em listas de leitura possui entrada auditada no contrato.
3. Cada opção declarada cita linha e snippet verificados contra o --help real versionado.
4. Cada opção declarada no contrato possui comandos de teste que são obrigatoriamente bloqueados
   (DENY/CERTIFICATE_INTEGRITY) nos três ambientes (DEV, STAGING, PROD).
5. Leituras puras declaradas no contrato são permitidas (ALLOW/GENERAL) nos três ambientes.
"""
from __future__ import annotations

import json
import os
import re
import sys
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_DIR.parent.parent
SCRIPTS_DIR = REPO_ROOT / "clearer-engineering" / "scripts"
CONFIG_DIR = REPO_ROOT / "clearer-engineering" / "config"
sys.path.insert(0, str(SCRIPTS_DIR))

import importlib
safety_gate = importlib.import_module("safety-gate")
from ceh_core.rules import ALLOWED_READ_CMDS, ALLOWED_GIT_READ_SUBCMDS

CONTRACT_FILE = CONFIG_DIR / "write_options.json"


def clean_help_line(raw_line: str) -> str:
    """Normaliza linha de help removendo sequências de backspace de terminal (ex: _\\b para sublinhado)."""
    return re.sub(r"_\x08", "", raw_line)


class TestHelpContract(unittest.TestCase):
    def setUp(self):
        self.assertTrue(CONTRACT_FILE.is_file(), f"Arquivo de contrato {CONTRACT_FILE} deve existir.")
        self.contract = json.loads(CONTRACT_FILE.read_text(encoding="utf-8"))
        self.commands_contract = self.contract.get("commands", {})

    def test_all_allowed_read_commands_have_contracts(self):
        """Todo comando em ALLOWED_READ_CMDS deve possuir entrada auditada no contrato (PR-QA-C2)."""
        missing = []
        for cmd in sorted(ALLOWED_READ_CMDS):
            if cmd not in self.commands_contract:
                missing.append(cmd)
        self.assertFalse(
            missing,
            f"Comandos em ALLOWED_READ_CMDS sem contrato formal em write_options.json: {missing}"
        )

    def test_all_allowed_git_read_subcommands_have_contracts(self):
        """Todo subcomando em ALLOWED_GIT_READ_SUBCMDS deve possuir entrada git-<subcmd> no contrato (PR-QA-C2)."""
        missing = []
        for subcmd in sorted(ALLOWED_GIT_READ_SUBCMDS):
            key = f"git-{subcmd}"
            if key not in self.commands_contract:
                missing.append(key)
        self.assertFalse(
            missing,
            f"Subcomandos em ALLOWED_GIT_READ_SUBCMDS sem contrato formal em write_options.json: {missing}"
        )

    def test_help_files_exist_and_snippets_match_accurately(self):
        """Todo snippet citado deve existir na linha exata do help versionado correspondente (C01 / PR-QA-C2)."""
        for name, data in self.commands_contract.items():
            help_rel = data.get("help_file")
            self.assertTrue(help_rel, f"Comando {name} deve declarar help_file.")
            help_path = REPO_ROOT / help_rel
            self.assertTrue(
                help_path.is_file(),
                f"Arquivo de help {help_path} citado em {name} não foi encontrado."
            )
            help_lines = help_path.read_text(encoding="utf-8").splitlines()

            for opt in data.get("write_options", []):
                flag = opt.get("flag")
                line_no = opt.get("help_line")
                snippet = opt.get("help_snippet")
                opt_type = opt.get("type")

                self.assertTrue(flag, f"Opção em {name} sem flag definida.")
                self.assertIn(opt_type, ("file_write", "external_exec"), f"Tipo inválido em {name}/{flag}: {opt_type}")
                self.assertIsInstance(line_no, int, f"help_line deve ser inteiro em {name}/{flag}")
                self.assertTrue(1 <= line_no <= len(help_lines), f"help_line {line_no} fora de alcance em {name} (total {len(help_lines)})")

                actual_line = clean_help_line(help_lines[line_no - 1])
                self.assertTrue(
                    snippet in actual_line,
                    f"Divergência na fonte em {name} ({help_rel}:{line_no}) para flag '{flag}'.\n"
                    f"  Snippet esperado: {snippet!r}\n"
                    f"  Linha real:       {actual_line!r}"
                )

                test_cmds = opt.get("test_commands", [])
                self.assertTrue(
                    len(test_cmds) > 0,
                    f"Opção {flag} do comando {name} não possui test_commands declarados no contrato."
                )

    def test_all_write_options_from_contract_denied_for_protected_targets(self):
        """Toda opção de escrita/execução do contrato é testada dinamicamente e bloqueada (C01 / PR-QA-C2)."""
        envs = ["development", "staging", "production"]
        evaluated_cases = 0

        for name, data in self.commands_contract.items():
            has_write = data.get("has_write_options", False)
            write_options = data.get("write_options", [])

            if has_write:
                self.assertTrue(len(write_options) > 0, f"Comando {name} marcado com has_write_options=True mas sem opções listadas.")
            else:
                self.assertEqual(len(write_options), 0, f"Comando {name} marcado com has_write_options=False não deve ter opções.")

            for opt in write_options:
                flag = opt["flag"]
                test_cmds = opt.get("test_commands", [])
                self.assertTrue(len(test_cmds) > 0, f"Opção {name}/{flag} deve possuir test_commands.")

                for cmd in test_cmds:
                    for env in envs:
                        dec, reason, _, uc = safety_gate.evaluate_command(cmd, explicit_env=env)
                        self.assertEqual(
                            dec, "deny",
                            f"Opção de escrita '{flag}' ({name}) em '{cmd}' DEVE ser deny no ambiente {env}. Obtido: {dec} ({reason})"
                        )
                        self.assertEqual(
                            uc, "CERTIFICATE_INTEGRITY",
                            f"Opção de escrita '{flag}' ({name}) em '{cmd}' deve ser CERTIFICATE_INTEGRITY no ambiente {env}. Obtido: {uc}"
                        )
                        evaluated_cases += 1

        self.assertGreaterEqual(evaluated_cases, 30, f"Deve haver cobertura robusta de opções de escrita testadas (avaliados: {evaluated_cases})")

    def test_pure_reads_from_contract_allowed_by_gate(self):
        """Toda leitura pura declarada no contrato é permitida (ALLOW/GENERAL) em todos os ambientes."""
        envs = ["development", "staging", "production"]
        evaluated_reads = 0

        for name, data in self.commands_contract.items():
            pure_cmds = data.get("pure_read_test_commands", [])
            self.assertTrue(len(pure_cmds) > 0, f"Comando {name} deve declarar pure_read_test_commands no contrato.")

            for cmd in pure_cmds:
                for env in envs:
                    dec, reason, _, uc = safety_gate.evaluate_command(cmd, explicit_env=env)
                    self.assertEqual(
                        dec, "allow",
                        f"Leitura pura '{cmd}' ({name}) deve ser allow no ambiente {env}. Obtido: {dec} ({reason})"
                    )
                    self.assertEqual(
                        uc, "GENERAL",
                        f"Leitura pura '{cmd}' ({name}) deve ser GENERAL no ambiente {env}. Obtido: {uc}"
                    )
                    evaluated_reads += 1

        self.assertGreaterEqual(evaluated_reads, 50, f"Deve haver cobertura robusta de leituras puras testadas (avaliados: {evaluated_reads})")


if __name__ == "__main__":
    unittest.main()
