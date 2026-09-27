#!/usr/bin/env python3
# ==============================================================================
# test_lexer_fuzz.py — Propriedades Formais do Lexer e Decisão do Safety Gate
# ==============================================================================
"""
Bateria determinística de validação do analisador léxico e do gate (PR-18b / Handoff 046):
1. Propriedade matemática de ida e volta (roundtrip):
   - Para segmentos atômicos sorteados unidos por ;, &&, ||, | e \\n:
     split_shell_pipeline(join(segs)) == (segs, None).
   - Falsificabilidade estrita: se || deixar de dividir (mutação no lexer), esta
     propriedade REPROVA deterministicamente.
2. Preservação de separadores dentro de aspas (aspas simples e duplas):
   - Operadores dentro de aspas ('a;b', "x || y") não provocam divisão.
3. Tratamento de subshell ( ... ):
   - Conforme especificação em lexer.py:85–99, o subshell acumula operadores
     internos preservando a expressão como unidade atômica.
4. Invariante formal de decisão do Safety Gate (2.000 permutações com semente 1337):
   - Sob --env production, nenhum comando com trecho destrutivo pode receber 'allow'.
   - Demonstra a defesa em profundidade da camada de regras com re.search.
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


ATOMIC_SAFE_SEGMENTS = [
    "ls -la",
    "pwd",
    "git status",
    "cat README.md",
    "git log -n 5",
    "head -n 10 file.txt",
    "python3 test.py",
    "npm test",
    "cargo check",
    "git diff",
    "date",
    "whoami",
    "git rev-parse HEAD",
    "wc -l file.txt",
    "uname -a",
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


class TestLexerPropertiesAndFuzz(unittest.TestCase):
    """Bateria de propriedades formais do lexer e fuzzing determinístico (PR-18b)."""

    def test_lexer_roundtrip_property_and_delimiters(self) -> None:
        """
        AT2 (Handoff 046 §3.2): Propriedade de ida e volta (roundtrip) sobre split_shell_pipeline:
        1. Para segmentos atômicos sorteados unidos por ;, &&, ||, | e \\n:
           split(join(segs)) == segs.
        2. Segmentos com separadores dentro de aspas continuam um único segmento.
        3. Expressões em subshell ( ... ) preservam seu conteúdo como uma unidade.
        """
        rng = random.Random(1337)
        total_roundtrip_cases = 500
        start_time = time.perf_counter()

        # --- Parte 1: Propriedade de Ida e Volta (Roundtrip) ---
        # Garante falsificabilidade estrita: se || deixar de dividir, falha imediatamente.
        for case_idx in range(1, total_roundtrip_cases + 1):
            num_segs = rng.randint(2, 5)
            selected_segs = [rng.choice(ATOMIC_SAFE_SEGMENTS) for _ in range(num_segs)]

            # Conectar os segmentos com operadores sorteados
            parts = [selected_segs[0]]
            for seg in selected_segs[1:]:
                op = rng.choice(CONNECTORS)
                space = " " if op != "\n" else ""
                parts.append(f"{space}{op}{space}")
                parts.append(seg)
            cmd_line = "".join(parts)

            split_res, err = split_shell_pipeline(cmd_line)
            self.assertIsNone(
                err,
                f"Caso #{case_idx}: Erro inesperado no split_shell_pipeline para:\n{cmd_line!r}\nErro: {err}",
            )
            self.assertEqual(
                split_res,
                selected_segs,
                f"Caso #{case_idx} VIOLOU PROPRIEDADE DE IDA E VOLTA DO LEXER:\n"
                f"  Comando original composto: {cmd_line!r}\n"
                f"  Segmentos esperados: {selected_segs}\n"
                f"  Segmentos obtidos pelo split: {split_res}",
            )

        # --- Parte 2: Separadores dentro de aspas simples e duplas ---
        quoted_test_cases = [
            ("echo 'a;b'", ["echo 'a;b'"]),
            ("echo 'x || y'", ["echo 'x || y'"]),
            ("echo 'foo && bar | baz'", ["echo 'foo && bar | baz'"]),
            ('echo "a;b"', ['echo "a;b"']),
            ('echo "x || y"', ['echo "x || y"']),
            ('git commit -m "feat: login && auth || fix"', ['git commit -m "feat: login && auth || fix"']),
            ('grep -E "pattern_a|pattern_b" file.txt', ['grep -E "pattern_a|pattern_b" file.txt']),
            ("awk '{print $1; print $2}' data.tsv", ["awk '{print $1; print $2}' data.tsv"]),
            ("sed 's/foo/bar/g; s/alpha/beta/g' file.txt", ["sed 's/foo/bar/g; s/alpha/beta/g' file.txt"]),
            ('printf "%s\\n" "one;two&&three"', ['printf "%s\\n" "one;two&&three"']),
        ]
        for cmd, expected in quoted_test_cases:
            res, err = split_shell_pipeline(cmd)
            self.assertIsNone(err, f"Erro inesperado no comando com aspas: {cmd!r}")
            self.assertEqual(
                res,
                expected,
                f"Separador dentro de aspas não deve dividir segmento: {cmd!r} -> obtido {res}",
            )

        # --- Parte 3: Subshell ( ... ) preserva conteúdo como uma unidade ---
        # Conforme especificação em lexer.py:85-99, paren_depth impede que operadores
        # internos dividam o pipeline antes do fechamento do parêntese.
        subshell_test_cases = [
            ("(cd src && cargo test)", ["(cd src && cargo test)"]),
            ("(git status; git diff)", ["(git status; git diff)"]),
            ("ls -la && (cd src && cargo test) || pwd", ["ls -la", "(cd src && cargo test)", "pwd"]),
            ("(date; whoami) | cat", ["(date; whoami)", "cat"]),
        ]
        for cmd, expected in subshell_test_cases:
            res, err = split_shell_pipeline(cmd)
            self.assertIsNone(err, f"Erro inesperado no subshell: {cmd!r}")
            self.assertEqual(
                res,
                expected,
                f"Expressão em subshell deve ser preservada como unidade: {cmd!r} -> obtido {res}",
            )

        elapsed = time.perf_counter() - start_time
        print(
            f"\n[LEXER ROUNDTRIP PROPERTY] {total_roundtrip_cases} permutações determinísticas "
            f"+ casos de aspas e subshells validados com sucesso em {elapsed:.3f}s."
        )

    def test_safety_gate_decision_invariant_2000_cases(self) -> None:
        """
        Invariante de Decisão do Safety Gate (2.000 casos determinísticos com semente 1337):
        Em ambiente 'production', nenhuma cadeia contendo qualquer segmento destrutivo
        pode receber a decisão 'allow' (deve ser != 'allow').
        Graças à defesa em profundidade da camada de regras com re.search, este invariante
        se mantém mesmo sob mutações parciais do pipeline.
        """
        rng = random.Random(1337)
        total_cases_target = 2000
        generated_cases: list[tuple[str, bool]] = []

        # Fase 1: Cobertura Determinística Obrigatória de Operadores
        for op in CONNECTORS:
            for d in DESTRUCTIVE_SEGMENTS:
                s = rng.choice(ATOMIC_SAFE_SEGMENTS)
                generated_cases.append((f"{s} {op} {d}", True))
                generated_cases.append((f"{d} {op} {s}", True))
                generated_cases.append((f"{s} {op} {d} {op} {s}", True))
                generated_cases.append((f"({s} {op} {d})", True))

        # Fase 2: Geração Pseudo-Aleatória com Semente 1337 até atingir 2000 casos
        while len(generated_cases) < total_cases_target:
            num_segments = rng.randint(1, 4)
            has_destructive = rng.random() < 0.85

            segments: list[str] = []
            if has_destructive:
                dest_idx = rng.randint(0, num_segments - 1)
                for i in range(num_segments):
                    if i == dest_idx:
                        segments.append(rng.choice(DESTRUCTIVE_SEGMENTS))
                    else:
                        segments.append(rng.choice(ATOMIC_SAFE_SEGMENTS))
            else:
                for _ in range(num_segments):
                    segments.append(rng.choice(ATOMIC_SAFE_SEGMENTS))

            # Conectar os segmentos com operadores sorteados
            if len(segments) == 1:
                cmd = segments[0]
            else:
                parts = [segments[0]]
                for seg in segments[1:]:
                    op = rng.choice(CONNECTORS)
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

        if violations:
            msg = (
                f"Safety Gate FALHOU com {len(violations)} violação(ões) no teste in-process:\n\n"
                + "\n\n".join(violations)
            )
            self.fail(msg)

        print(
            f"[SAFETY GATE INVARIANT] {total_cases_target} casos determinísticos "
            f"({destructive_count} com segmentos destrutivos) em {elapsed:.3f}s. "
            f"Invariante formal (decision != 'allow') 100% preservado."
        )


if __name__ == "__main__":
    unittest.main()
