#!/usr/bin/env python3
"""
test_reason_invariant.py - Validação determinística do invariante do motivo (PR-QA-B).

Garante que o texto do motivo ('reason') retornado pelo Safety Gate seja estritamente
coerente com a decisão ('decision') e com o caso de uso ('use_case'):
1. 'deny'  -> O motivo contém um marcador de bloqueio reconhecido de lista fechada versionada.
2. 'allow' -> O motivo NÃO contém nenhum marcador de bloqueio nem marcador de confirmação.
3. 'ask'   -> O motivo contém o marcador de confirmação ('ALERTA').
4. 'use_case' consistente com o motivo (CERTIFICATE_INTEGRITY, CATASTROPHIC, PRE_PUSH_CI, PARSER_FAIL_CLOSED).
5. Todo motivo menciona o ambiente detectado e a evidência quando o ambiente influenciou a decisão.
6. Falsificabilidade: mutação de motivo para texto neutro ou incoerente reprova imediatamente o teste.
"""
from __future__ import annotations

import base64
import os
import sys
import unittest
from importlib import import_module
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_DIR.parents[1]
SCRIPTS_DIR = TESTS_DIR.parent / "scripts"
FIXTURES_DIR = TESTS_DIR / "fixtures"

sys.path.insert(0, str(SCRIPTS_DIR))
safety_gate = import_module("safety-gate")

# Lista fechada e versionada de marcadores de bloqueio para decisões 'deny'
DENY_MARKERS: tuple[str, ...] = (
    "[CEH PRODUCTION LOCK]",
    "[CEH CATASTROPHIC BLOCK]",
    "[CEH CERTIFICATE INTEGRITY",
    "[CEH PRE-PUSH CI GATE]",
    "[CEH SAFETY GATE - FAIL-CLOSED]",
    "[CEH SAFETY GATE - GIT]",
    "[CEH SAFETY GATE ERROR]",
    "[CEH HOOK ERROR]",
    "[CEH CONTEXT LOCK]",
)

# Casos de uso onde a regra é condicionada ao ambiente de execução
ENVIRONMENT_DEPENDENT_USE_CASES: frozenset[str] = frozenset({
    "FILESYSTEM",
    "GIT_HISTORY",
    "GIT_DESTRUCTIVE",
    "DATABASE",
    "INFRASTRUCTURE",
})


def load_corpus_commands(corpus_path: Path) -> list[str]:
    """Carrega comandos do corpus decodificando RAW: e B64: (ignora HOOK e INTEGRATION)."""
    cmds = []
    for line in corpus_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("HOOK:") or line.startswith("INTEGRATION:"):
            continue
        if line.startswith("RAW:"):
            cmds.append(line[4:].strip())
        elif line.startswith("B64:"):
            try:
                decoded = base64.b64decode(line[4:]).decode("utf-8").strip()
                cmds.append(decoded)
            except Exception:
                pass
        else:
            cmds.append(line)
    return cmds


def load_battery(battery_path: Path) -> list[tuple[int, str, str, str, str]]:
    """Carrega linhas da bateria de revisão: (linha, env, esperado, ref, comando)."""
    rows = []
    for n, raw in enumerate(battery_path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        env, expected, ref, command = line.split("|", 3)
        rows.append((n, env, expected, ref, command))
    return rows


def validate_reason_contract(
    command: str,
    env: str,
    decision: str,
    reason: str,
    use_case: str,
    source: str = "",
) -> list[str]:
    """Valida o contrato do motivo de forma pura e determinística."""
    errors: list[str] = []

    # 1. Regras de Deny
    if decision == "deny":
        if not any(marker in reason for marker in DENY_MARKERS):
            errors.append(
                f"[{source}] Decisão 'deny' sem marcador de bloqueio reconhecido.\n"
                f"  Comando: {command}\n"
                f"  Ambiente: {env}\n"
                f"  Motivo obtido: {reason}"
            )

    # 2. Regras de Allow
    elif decision == "allow":
        for marker in DENY_MARKERS:
            if marker in reason:
                errors.append(
                    f"[{source}] Decisão 'allow' contém marcador de bloqueio ('{marker}').\n"
                    f"  Comando: {command}\n"
                    f"  Ambiente: {env}\n"
                    f"  Motivo obtido: {reason}"
                )
        if "ALERTA" in reason:
            errors.append(
                f"[{source}] Decisão 'allow' contém marcador de confirmação 'ALERTA'.\n"
                f"  Comando: {command}\n"
                f"  Ambiente: {env}\n"
                f"  Motivo obtido: {reason}"
            )

    # 3. Regras de Ask
    elif decision == "ask":
        if "ALERTA" not in reason:
            errors.append(
                f"[{source}] Decisão 'ask' sem marcador de confirmação 'ALERTA'.\n"
                f"  Comando: {command}\n"
                f"  Ambiente: {env}\n"
                f"  Motivo obtido: {reason}"
            )

    # 4. Consistência entre use_case e motivo
    reason_upper = reason.upper()
    if use_case == "CERTIFICATE_INTEGRITY":
        if "CERTIFICATE INTEGRITY" not in reason_upper:
            errors.append(
                f"[{source}] use_case 'CERTIFICATE_INTEGRITY' sem menção correspondente no motivo.\n"
                f"  Comando: {command}\n"
                f"  Motivo: {reason}"
            )
    elif use_case == "CATASTROPHIC":
        if "CATASTROPHIC" not in reason_upper:
            errors.append(
                f"[{source}] use_case 'CATASTROPHIC' sem menção correspondente no motivo.\n"
                f"  Comando: {command}\n"
                f"  Motivo: {reason}"
            )
    elif use_case == "PRE_PUSH_CI":
        if "PRE-PUSH CI GATE" not in reason_upper:
            errors.append(
                f"[{source}] use_case 'PRE_PUSH_CI' sem menção a 'PRE-PUSH CI GATE' no motivo.\n"
                f"  Comando: {command}\n"
                f"  Motivo: {reason}"
            )
    elif use_case == "PARSER_FAIL_CLOSED":
        if "FAIL-CLOSED" not in reason_upper and "PARSER_FAIL_CLOSED" not in reason_upper:
            errors.append(
                f"[{source}] use_case 'PARSER_FAIL_CLOSED' sem menção a 'FAIL-CLOSED' no motivo.\n"
                f"  Comando: {command}\n"
                f"  Motivo: {reason}"
            )

    # 5. Ambiente e Evidência quando o ambiente influenciou a decisão
    if use_case in ENVIRONMENT_DEPENDENT_USE_CASES:
        if env.upper() not in reason_upper:
            errors.append(
                f"[{source}] Regra dependente de ambiente ({use_case}) não menciona o ambiente detectado ('{env.upper()}').\n"
                f"  Comando: {command}\n"
                f"  Motivo: {reason}"
            )
        if not any(w in reason_upper for w in ("EVIDÊNCIA", "EVIDENCIA", "SOURCE:")):
            errors.append(
                f"[{source}] Regra dependente de ambiente ({use_case}) não menciona a evidência de detecção.\n"
                f"  Comando: {command}\n"
                f"  Motivo: {reason}"
            )

    return errors


class ReasonInvariantTests(unittest.TestCase):
    """Suíte de verificação do invariante do motivo sobre corpus e baterias."""

    @classmethod
    def setUpClass(cls):
        cls.corpus_path = FIXTURES_DIR / "gate_corpus.txt"
        cls.battery_path = FIXTURES_DIR / "review_batteries.txt"
        cls.corpus_commands = load_corpus_commands(cls.corpus_path)
        cls.battery_rows = load_battery(cls.battery_path)

    def test_corpus_invariants_across_all_environments(self):
        """Valida invariantes do motivo para todos os comandos do corpus nos 3 ambientes."""
        self.assertGreater(len(self.corpus_commands), 0)
        failures: list[str] = []

        for cmd in self.corpus_commands:
            for env in ("development", "staging", "production"):
                dec, reason, det_env, uc = safety_gate.evaluate_command(cmd, explicit_env=env)
                errs = validate_reason_contract(cmd, env, dec, reason, uc, source=f"corpus:{env}")
                failures.extend(errs)

        self.assertEqual(
            len(failures),
            0,
            f"Falhas no invariante do motivo no corpus ({len(failures)} violações):\n" + "\n".join(failures[:10]),
        )

    def test_battery_invariants(self):
        """Valida invariantes do motivo para todos os casos da bateria adversarial de revisão."""
        self.assertGreater(len(self.battery_rows), 0)
        failures: list[str] = []

        for n, env, exp, ref, cmd in self.battery_rows:
            dec, reason, det_env, uc = safety_gate.evaluate_command(cmd, explicit_env=env)
            errs = validate_reason_contract(cmd, env, dec, reason, uc, source=f"battery:L{n}:{ref}")
            failures.extend(errs)

        self.assertEqual(
            len(failures),
            0,
            f"Falhas no invariante do motivo na bateria ({len(failures)} violações):\n" + "\n".join(failures[:10]),
        )

    def test_falsifiability_on_neutral_deny_reason(self):
        """Prova por mutação: um motivo de deny neutro (sem marcador reconhecido) deve reprovar citando o comando."""
        cmd = "rm -rf /production/data"
        fake_reason = "Operação rejeitada pelas políticas internas do sistema."
        errs = validate_reason_contract(cmd, "production", "deny", fake_reason, "FILESYSTEM", source="falsifiability_test")
        self.assertGreater(len(errs), 0)
        self.assertIn("sem marcador de bloqueio reconhecido", errs[0])
        self.assertIn(cmd, errs[0])

    def test_falsifiability_on_ask_without_alert(self):
        """Prova por mutação: um motivo de ask sem marcador ALERTA deve reprovar."""
        cmd = "git clean -fdx"
        fake_reason = "Confirmação necessária antes de executar limpeza."
        errs = validate_reason_contract(cmd, "staging", "ask", fake_reason, "GIT_DESTRUCTIVE", source="falsifiability_test")
        self.assertGreater(len(errs), 0)
        self.assertIn("sem marcador de confirmação 'ALERTA'", errs[0])

    def test_falsifiability_on_allow_with_deny_marker(self):
        """Prova por mutação: um motivo de allow com marcador de bloqueio espúrio deve reprovar."""
        cmd = "git status"
        fake_reason = "[CEH PRODUCTION LOCK] Leitura normal de status autorizada."
        errs = validate_reason_contract(cmd, "development", "allow", fake_reason, "GENERAL", source="falsifiability_test")
        self.assertGreater(len(errs), 0)
        self.assertIn("contém marcador de bloqueio", errs[0])

    def test_falsifiability_on_inconsistent_use_case(self):
        """Prova por mutação: use_case CERTIFICATE_INTEGRITY sem menção a CERTIFICATE INTEGRITY no motivo deve reprovar."""
        cmd = "echo foo > .ceh/last-ci-run.json"
        fake_reason = "[CEH CATASTROPHIC BLOCK] Arquivo bloqueado generico."
        errs = validate_reason_contract(cmd, "development", "deny", fake_reason, "CERTIFICATE_INTEGRITY", source="falsifiability_test")
        self.assertGreater(len(errs), 0)
        self.assertIn("use_case 'CERTIFICATE_INTEGRITY' sem menção correspondente", errs[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
