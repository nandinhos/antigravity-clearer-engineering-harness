#!/usr/bin/env python3
# ==============================================================================
# test_lexer_fuzz.py — Fuzzing Determinístico In-Process do Lexer e Safety Gate
# ==============================================================================
"""
Fuzzing determinístico baseado em propriedades (PR-18 / T3 / Pareceres do Conselho):
- Semente determinística fixa: random.Random(1337).
- 2.000 composições determinísticas de comandos seguros e destrutivos.
- Execução 100% in-process / in-memory (sem forks de subprocesso) para velocidade e segurança.
- Cobertura garantida de classes de operadores (;, &&, ||, |, \n, subshell).
- Invariante formal inegociável: sob --env production, nenhuma composição com segmento
  destrutivo pode receber a decisão 'allow' (decision != 'allow').
- Erros de parsing ou sintaxe malformada devem escalar compulsoriamente para fail-closed (deny).
"""

from __future__ import annotations

import os
import random
import sys
import time
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = REPO_ROOT / "clearer-engineering" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import importlib.util

spec = importlib.util.spec_from_file_location("safety_gate", SCRIPTS_DIR / "safety-gate.py")
if spec is None or spec.loader is None:
    raise ImportError(f"Não foi possível carregar safety-gate.py de {SCRIPTS_DIR}")
safety_gate = importlib.util.module_from_spec(spec)
sys.modules["safety_gate"] = safety_gate
spec.loader.exec_module(safety_gate)

evaluate_command = safety_gate.evaluate_command
from ceh_core.lexer import split_shell_pipeline


SAFE_SEGMENTS = [
    "ls -la",
    "pwd",
    "git status",
    "cat README.md",
    "echo 'hello world'",
    "git log -n 5",
    "head -n 10 file.txt",
    "python3 test.py",
    "npm test",
    "cargo check",
    "git diff",
    "date",
    "whoami",
    "git rev-parse HEAD",
]

DESTRUCTIVE_SEGMENTS = [
    "git reset --hard",
    "git reset --hard HEAD~1",
    "git clean -fd",
    "git clean -f -d",
    "rm -rf src/",
    "rm -rf app/",
    "git push --force",
    "git push origin main --force",
    "drop database test_db",
    "drop table users",
    "truncate table audit_logs",
    "terraform destroy",
    "kubectl delete namespace prod",
    "kubectl delete all",
    "docker system prune -a",
]

CONNECTORS = [";", "&&", "||", "|", "\n"]


class TestLexerFuzz(unittest.TestCase):
    """Bateria de fuzzing determinístico in-process com semente fixa 1337."""

    def test_lexer_destructive_invariant_2000_cases(self) -> None:
        """
        Invariante: Em ambiente 'production', nenhuma cadeia contendo qualquer
        segmento destrutivo pode receber a decisão 'allow' (deve ser != 'allow').
        """
        rng = random.Random(1337)
        total_cases_target = 2000
        generated_cases: list[tuple[str, bool]] = []

        # Fase 1: Cobertura Determinística Obrigatória de Operadores (Garantia Codex)
        # Assegura que todo conector (inclusive ||) e posições de destruição sejam testados
        for op in CONNECTORS:
            for d in DESTRUCTIVE_SEGMENTS:
                s = rng.choice(SAFE_SEGMENTS)
                generated_cases.append((f"{s} {op} {d}", True))
                generated_cases.append((f"{d} {op} {s}", True))
                generated_cases.append((f"{s} {op} {d} {op} {s}", True))
                generated_cases.append((f"({s} {op} {d})", True))

        # Fase 2: Geração Pseudo-Aleatória com Semente 1337 até atingir 2000 casos
        while len(generated_cases) < total_cases_target:
            num_segments = rng.randint(1, 4)
            # 85% de chance de conter pelo menos um segmento destrutivo
            has_destructive = rng.random() < 0.85

            segments: list[str] = []
            if has_destructive:
                dest_idx = rng.randint(0, num_segments - 1)
                for i in range(num_segments):
                    if i == dest_idx:
                        segments.append(rng.choice(DESTRUCTIVE_SEGMENTS))
                    else:
                        segments.append(rng.choice(SAFE_SEGMENTS))
            else:
                for _ in range(num_segments):
                    segments.append(rng.choice(SAFE_SEGMENTS))

            # Conectar os segmentos com operadores sorteados
            if len(segments) == 1:
                cmd = segments[0]
            else:
                parts = [segments[0]]
                for seg in segments[1:]:
                    op = rng.choice(CONNECTORS)
                    # Variação com espaçamento
                    space = " " if op != "\n" else ""
                    parts.append(f"{space}{op}{space}")
                    parts.append(seg)
                cmd = "".join(parts)

            # 20% de chance de envolver em subshell
            if rng.random() < 0.20:
                cmd = f"({cmd})"

            # 15% de chance de adicionar argumentos com aspas adicionais
            if rng.random() < 0.15:
                cmd = cmd.replace("HEAD~1", "'HEAD~1'").replace("src/", '"src/"')

            generated_cases.append((cmd, has_destructive))

        cases_to_run = generated_cases[:total_cases_target]
        self.assertEqual(len(cases_to_run), total_cases_target)

        # Execução In-Process de Alta Performance
        start_time = time.perf_counter()
        violations: list[str] = []
        destructive_count = 0

        for idx, (cmd, has_dest) in enumerate(cases_to_run, 1):
            if has_dest:
                destructive_count += 1

            # Invocação in-memory com explícito env="production"
            decision, reason, evaluated_env, severity = evaluate_command(
                cmd,
                explicit_env="production",
            )

            # Invariante 1: Se contém segmento destrutivo, JAMAIS pode ser allow em produção
            if has_dest and decision == "allow":
                violations.append(
                    f"Caso #{idx} VIOLOU INVARIANTE:\n"
                    f"  Comando: {cmd!r}\n"
                    f"  Decisão recebida: {decision} (esperado != 'allow')\n"
                    f"  Motivo: {reason}\n"
                    f"  Ambiente avaliado: {evaluated_env}"
                )
                if len(violations) >= 5:
                    break

            # Invariante 2: Erros de parsing devem resultar em fail-closed (deny)
            _, parse_err = split_shell_pipeline(cmd.strip())
            if parse_err and decision != "deny":
                violations.append(
                    f"Caso #{idx} VIOLOU FAIL-CLOSED DE PARSER:\n"
                    f"  Comando: {cmd!r}\n"
                    f"  Erro de parse: {parse_err}\n"
                    f"  Decisão recebida: {decision} (esperado 'deny')"
                )
                if len(violations) >= 5:
                    break

        elapsed = time.perf_counter() - start_time

        # Diagnóstico e Relatório de Execução
        if violations:
            msg = (
                f"Fuzzing do Lexer FALHOU com {len(violations)} violação(ões) no teste in-process:\n\n"
                + "\n\n".join(violations)
            )
            self.fail(msg)

        # Registro de sucesso com estatísticas
        print(
            f"\n[LEXER FUZZ SUCCESS] Executados {total_cases_target} casos determinísticos "
            f"({destructive_count} com segmentos destrutivos) em {elapsed:.3f}s. "
            f"Invariante formal (decision != 'allow') 100% preservado."
        )


if __name__ == "__main__":
    unittest.main()
