#!/usr/bin/env python3
"""
test_mutation_p13.py — Provas de falsificabilidade por mutação do PR-13.

Comprova determinística e hermeticamente que a rede de verificação do PR-13 falha se:
1. M1: Uma referência a formato de host ('toolCall') for inserida em ceh_core/ (violação do desacoplamento A4).
2. M2: O código de saída do deny do Antigravity for alterado para exit 2 em hook_context.py (violação de não-regressão A3).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def run_mutation_1(repo_root: Path) -> None:
    engine_file = repo_root / "clearer-engineering" / "scripts" / "ceh_core" / "engine.py"
    baseline_tool = repo_root / "clearer-engineering" / "tests" / "tools" / "onda4_baseline.py"

    original_code = engine_file.read_text(encoding="utf-8")
    try:
        # Injeta referência proibida de host em ceh_core/
        engine_file.write_text(original_code + "\n# Prova de mutacao M1: toolCall reference\n", encoding="utf-8")

        res = subprocess.run([sys.executable, str(baseline_tool), "--check"], capture_output=True, text=True)
        if res.returncode == 0:
            print("FALHA M1: onda4_baseline.py aprovou referência de host 'toolCall' dentro de ceh_core/!", file=sys.stderr)
            sys.exit(1)

        if "ceh_core possui" not in res.stderr and "ceh_core possui" not in res.stdout:
            print(f"FALHA M1: erro esperado não encontrado na saída do baseline:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}", file=sys.stderr)
            sys.exit(1)

        print("✔ Prova por mutação M1 aprovada: onda4_baseline.py rejeitou 'toolCall' em ceh_core/ com exit 1.")
    finally:
        engine_file.write_text(original_code, encoding="utf-8")


def run_mutation_2(repo_root: Path) -> None:
    hook_ctx_file = repo_root / "clearer-engineering" / "scripts" / "hook_context.py"
    baseline_tool = repo_root / "clearer-engineering" / "tests" / "tools" / "onda4_baseline.py"

    original_code = hook_ctx_file.read_text(encoding="utf-8")
    try:
        # Muta código de saída de deny do Antigravity para exit 2
        # Em hook_context.py: return 2 if is_claude_host(payload) else 0 -> muta para return 2
        target_str = "return 2 if is_claude_host(payload) else 0"
        if target_str not in original_code:
            raise RuntimeError(f"Não foi possível encontrar '{target_str}' em hook_context.py")
        mutated_code = original_code.replace(target_str, "return 2")
        hook_ctx_file.write_text(mutated_code, encoding="utf-8")

        res = subprocess.run([sys.executable, str(baseline_tool), "--check"], capture_output=True, text=True)
        if res.returncode == 0:
            print("FALHA M2: onda4_baseline.py aprovou alteração de exit code de deny para exit 2 no Antigravity!", file=sys.stderr)
            sys.exit(1)

        if "A3 divergências em respostas do hook" not in res.stderr and "A3 divergências em respostas do hook" not in res.stdout:
            print(f"FALHA M2: erro esperado em A3 não encontrado:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}", file=sys.stderr)
            sys.exit(1)

        print("✔ Prova por mutação M2 aprovada: onda4_baseline.py detectou quebra do hook do Antigravity em A3 com exit 1.")
    finally:
        hook_ctx_file.write_text(original_code, encoding="utf-8")


def main():
    repo_root = Path(__file__).resolve().parents[3]
    print("=== Executando Provas de Mutação do PR-13 (Falsificabilidade) ===")
    run_mutation_1(repo_root)
    run_mutation_2(repo_root)
    print("=== Todas as 2 Provas de Mutação do PR-13 passaram com sucesso! ===")


if __name__ == "__main__":
    main()
