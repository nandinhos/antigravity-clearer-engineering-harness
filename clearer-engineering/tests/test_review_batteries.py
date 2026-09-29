#!/usr/bin/env python3
"""
test_review_batteries.py - Executa as baterias adversariais das revisões (fixtures/review_batteries.txt).

Cada linha é um contrato: <env>|<esperado>|<referência>|<comando>.
- Linhas normais têm de passar.
- Linhas "PENDENTE:<ID>" são defeitos conhecidos: têm de CONTINUAR falhando (xfail estrito).
  Se uma pendente passar, o teste falha pedindo a remoção do prefixo, para que a correção
  fique registrada no mesmo PR que a fez.
Avaliação num repositório temporário sem certificado (hermético, como o snapshot do corpus).
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from importlib import import_module
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS_DIR.parent / "scripts"))
safety_gate = import_module("safety-gate")
BATTERY = TESTS_DIR / "fixtures" / "review_batteries.txt"


def load_battery():
    rows = []
    for n, raw in enumerate(BATTERY.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        env, expected, ref, command = line.split("|", 3)
        rows.append((n, env, expected, ref, command))
    return rows


def matches(expected: str, decision: str, use_case: str) -> bool:
    exp_decision, _, exp_use_case = expected.partition("/")
    return decision == exp_decision and (not exp_use_case or use_case == exp_use_case)


class ReviewBatteries(unittest.TestCase):
    def setUp(self):
        self.orig = os.getcwd()
        self.tmp = tempfile.mkdtemp(prefix="ceh-battery-")
        subprocess.run(["git", "init", "-q", "-b", "dev", self.tmp], check=True)
        os.chdir(self.tmp)

    def tearDown(self):
        os.chdir(self.orig)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_batteries(self):
        rows = load_battery()
        self.assertGreater(len(rows), 0)
        failures, fixed_pending = [], []
        for n, env, expected, ref, command in rows:
            decision, _reason, _env, use_case = safety_gate.evaluate_command(command, explicit_env=env)
            ok = matches(expected, decision, use_case)
            if ref.startswith("PENDENTE:"):
                if ok:
                    fixed_pending.append(f"linha {n} [{ref}] já passa: remova o prefixo PENDENTE — {command}")
            elif not ok:
                failures.append(f"linha {n} [{ref}] {env}: esperado {expected}, obtido {decision}/{use_case} — {command}")
        msg = "\n".join(failures + fixed_pending)
        self.assertFalse(failures or fixed_pending, "\n" + msg)


if __name__ == "__main__":
    unittest.main(verbosity=1)
