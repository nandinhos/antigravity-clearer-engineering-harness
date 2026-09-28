#!/usr/bin/env python3
"""
test_help_contract.py - Validação formal do contrato de opções de escrita a partir do --help (PR-QA-C).

Garante que:
1. Nenhum comando seja admitido em listas de leitura do Safety Gate sem contrato formal em write_options.json.
2. Cada opção que grava em arquivo ou executa helpers externos identificada nos contratos seja
   categoricamente bloqueada (DENY/CERTIFICATE_INTEGRITY) quando apontar para .ceh/ ou arquivos protegidos.
3. Leituras puras sem flags de escrita permaneçam permitidas (ALLOW).
"""
from __future__ import annotations

import json
import os
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


class TestHelpContract(unittest.TestCase):
    def setUp(self):
        self.assertTrue(CONTRACT_FILE.is_file(), f"Arquivo de contrato {CONTRACT_FILE} deve existir.")
        self.contract = json.loads(CONTRACT_FILE.read_text(encoding="utf-8"))
        self.commands_contract = self.contract.get("commands", {})

    def test_all_allowed_read_commands_have_contracts(self):
        """Todo comando em ALLOWED_READ_CMDS deve possuir entrada auditada no contrato (PR-QA-C)."""
        missing = []
        for cmd in sorted(ALLOWED_READ_CMDS):
            if cmd not in self.commands_contract:
                missing.append(cmd)
        self.assertFalse(
            missing,
            f"Comandos em ALLOWED_READ_CMDS sem contrato formal em write_options.json: {missing}"
        )

    def test_all_allowed_git_read_subcommands_have_contracts(self):
        """Todo subcomando em ALLOWED_GIT_READ_SUBCMDS deve possuir entrada git-<subcmd> no contrato (PR-QA-C)."""
        missing = []
        for subcmd in sorted(ALLOWED_GIT_READ_SUBCMDS):
            key = f"git-{subcmd}"
            if key not in self.commands_contract:
                missing.append(key)
        self.assertFalse(
            missing,
            f"Subcomandos em ALLOWED_GIT_READ_SUBCMDS sem contrato formal em write_options.json: {missing}"
        )

    def test_help_files_exist_physically(self):
        """Todo arquivo de help citado no contrato deve existir fisicamente no repositório."""
        for name, data in self.commands_contract.items():
            help_rel = data.get("help_file")
            self.assertTrue(help_rel, f"Comando {name} deve declarar help_file.")
            help_path = REPO_ROOT / help_rel
            self.assertTrue(
                help_path.is_file(),
                f"Arquivo de help {help_path} citado em {name} não foi encontrado."
            )

    def test_write_options_denied_for_ceh_all_envs(self):
        """Toda opção de escrita ou execução registrada no contrato é DENY em DEV, STAGING e PROD quando visa .ceh/."""
        envs = ["development", "staging", "production"]

        # 1. less flags (-o, -O, --log-file, --LOG-FILE)
        less_cmds = [
            "less -o .ceh/last-ci-run.json input.txt",
            "less -O .ceh/last-ci-run.json input.txt",
            "less --log-file=.ceh/last-ci-run.json input.txt",
            "less --LOG-FILE=.ceh/last-ci-run.json input.txt",
            "less -o.ceh/last-ci-run.json input.txt",
        ]
        for cmd in less_cmds:
            for env in envs:
                dec, reason, _, uc = safety_gate.evaluate_command(cmd, explicit_env=env)
                self.assertEqual(dec, "deny", f"'{cmd}' deve ser deny no ambiente {env}")
                self.assertEqual(uc, "CERTIFICATE_INTEGRITY")

        # 2. git diff flags (--output, --output-directory, --ext-diff, --textconv)
        git_diff_cmds = [
            "git diff --output=.ceh/last-ci-run.json",
            "git diff --output-directory=.ceh/",
            "git diff --ext-diff .ceh/last-ci-run.json",
            "git diff --textconv .ceh/last-ci-run.json",
        ]
        for cmd in git_diff_cmds:
            for env in envs:
                dec, reason, _, uc = safety_gate.evaluate_command(cmd, explicit_env=env)
                self.assertEqual(dec, "deny", f"'{cmd}' deve ser deny no ambiente {env}")
                self.assertEqual(uc, "CERTIFICATE_INTEGRITY")

        # 3. git log flags (--output, -o, --ext-diff, --textconv)
        git_log_cmds = [
            "git log -1 --output=.ceh/last-ci-run.json",
            "git log -1 -o .ceh/last-ci-run.json",
            "git log -1 --ext-diff .ceh/last-ci-run.json",
            "git log -1 --textconv .ceh/last-ci-run.json",
        ]
        for cmd in git_log_cmds:
            for env in envs:
                dec, reason, _, uc = safety_gate.evaluate_command(cmd, explicit_env=env)
                self.assertEqual(dec, "deny", f"'{cmd}' deve ser deny no ambiente {env}")
                self.assertEqual(uc, "CERTIFICATE_INTEGRITY")

        # 4. git show flags (--output, --ext-diff, --textconv)
        git_show_cmds = [
            "git show --output=.ceh/last-ci-run.json HEAD",
            "git show --ext-diff .ceh/last-ci-run.json HEAD",
            "git show --textconv .ceh/last-ci-run.json HEAD",
        ]
        for cmd in git_show_cmds:
            for env in envs:
                dec, reason, _, uc = safety_gate.evaluate_command(cmd, explicit_env=env)
                self.assertEqual(dec, "deny", f"'{cmd}' deve ser deny no ambiente {env}")
                self.assertEqual(uc, "CERTIFICATE_INTEGRITY")

        # 5. python3 -m json.tool com segundo posicional (outfile)
        py_json_cmds = [
            "python3 -m json.tool /tmp/input.json .ceh/last-ci-run.json",
            "python -m json.tool /tmp/input.json .ceh/last-ci-run.json",
            "python3 -m json.tool --sort-keys /tmp/input.json .ceh/last-ci-run.json",
        ]
        for cmd in py_json_cmds:
            for env in envs:
                dec, reason, _, uc = safety_gate.evaluate_command(cmd, explicit_env=env)
                self.assertEqual(dec, "deny", f"'{cmd}' deve ser deny no ambiente {env}")
                self.assertEqual(uc, "CERTIFICATE_INTEGRITY")

    def test_pure_reads_continue_allowed(self):
        """Leituras puras dos comandos autorizados sem opções de escrita continuam allow em produção."""
        pure_read_cmds = [
            "cat .ceh/last-ci-run.json",
            "less .ceh/last-ci-run.json",
            "more .ceh/last-ci-run.json",
            "head -n 5 .ceh/last-ci-run.json",
            "tail -n 5 .ceh/last-ci-run.json",
            "jq .status .ceh/last-ci-run.json",
            "grep PASS .ceh/last-ci-run.json",
            "egrep 'PASS|FAIL' .ceh/last-ci-run.json",
            "fgrep PASS .ceh/last-ci-run.json",
            "ls .ceh",
            "stat .ceh/last-ci-run.json",
            "wc -l .ceh/last-ci-run.log",
            "du -sh .ceh",
            "diff .ceh/last-ci-run.json /tmp/x",
            "git status --ignored .ceh",
            "git log -n 5 .ceh/last-ci-run.json",
            "git diff .ceh/last-ci-run.json",
            "git show HEAD:.ceh/last-ci-run.json",
            "python3 -m json.tool .ceh/last-ci-run.json",
        ]
        for cmd in pure_read_cmds:
            dec, reason, _, uc = safety_gate.evaluate_command(cmd, explicit_env="production")
            self.assertEqual(
                dec, "allow",
                f"Leitura pura legítima '{cmd}' deve ser ALLOW, obteve '{dec}' ({reason})"
            )


if __name__ == "__main__":
    unittest.main()
