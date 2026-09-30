#!/usr/bin/env python3
"""
test_mutation_p13.py — Provas de falsificabilidade por mutação do PR-13.
Regra AT5 (Handoff 046 / Handoff 072): mutação estritamente em clone/cópia temporária.

Comprova determinística e hermeticamente que a rede de verificação do PR-13 falha se:
1. M1: Uma referência a formato de host ('toolCall') for inserida em ceh_core/ (violação do desacoplamento A4).
2. M2: O código de saída do deny do Antigravity for alterado para exit 2 em hook_context.py (violação de não-regressão A3).
3. M3: O bloco try dos imports em safety-gate.py for removido (violação do fail-closed em quebra de módulo).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def _create_temp_clone(repo_root: Path, tmp_dir: str) -> Path:
    tmp_repo = Path(tmp_dir)
    # Copia as árvores e scripts necessários para a execução hermética
    shutil.copytree(repo_root / "clearer-engineering", tmp_repo / "clearer-engineering")
    shutil.copytree(repo_root / "docs", tmp_repo / "docs")
    if (repo_root / ".ceh").is_dir():
        shutil.copytree(repo_root / ".ceh", tmp_repo / ".ceh")
    shutil.copy(repo_root / "install.sh", tmp_repo / "install.sh")
    shutil.copy(repo_root / "uninstall.sh", tmp_repo / "uninstall.sh")
    return tmp_repo


def run_mutation_1(repo_root: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="ceh_mut1_") as tmp_dir:
        tmp_repo = _create_temp_clone(repo_root, tmp_dir)
        engine_file = tmp_repo / "clearer-engineering" / "scripts" / "ceh_core" / "engine.py"
        baseline_tool = tmp_repo / "clearer-engineering" / "tests" / "tools" / "onda4_baseline.py"

        # Injeta referência proibida de host em ceh_core/ NA CÓPIA TEMPORÁRIA
        engine_file.write_text(
            engine_file.read_text(encoding="utf-8") + "\n# Prova de mutacao M1: toolCall reference\n",
            encoding="utf-8"
        )

        res = subprocess.run([sys.executable, str(baseline_tool), "--check"], capture_output=True, text=True, cwd=str(tmp_repo))
        if res.returncode == 0:
            print("FALHA M1: onda4_baseline.py aprovou referência de host 'toolCall' dentro de ceh_core/!", file=sys.stderr)
            sys.exit(1)

        if "ceh_core possui" not in res.stderr and "ceh_core possui" not in res.stdout:
            print(f"FALHA M1: erro esperado não encontrado na saída do baseline:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}", file=sys.stderr)
            sys.exit(1)

        print("✔ Prova por mutação M1 aprovada: onda4_baseline.py rejeitou 'toolCall' em ceh_core/ com exit 1 (em clone temporário).")


def run_mutation_2(repo_root: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="ceh_mut2_") as tmp_dir:
        tmp_repo = _create_temp_clone(repo_root, tmp_dir)
        hook_ctx_file = tmp_repo / "clearer-engineering" / "scripts" / "hook_context.py"
        baseline_tool = tmp_repo / "clearer-engineering" / "tests" / "tools" / "onda4_baseline.py"

        # Muta código de saída de deny do Antigravity para exit 2 NA CÓPIA TEMPORÁRIA
        original_code = hook_ctx_file.read_text(encoding="utf-8")
        target_str = "return 2 if is_claude_host(payload) else 0"
        if target_str not in original_code:
            raise RuntimeError(f"Não foi possível encontrar '{target_str}' em hook_context.py")
        mutated_code = original_code.replace(target_str, "return 2")
        hook_ctx_file.write_text(mutated_code, encoding="utf-8")

        res = subprocess.run([sys.executable, str(baseline_tool), "--check"], capture_output=True, text=True, cwd=str(tmp_repo))
        if res.returncode == 0:
            print("FALHA M2: onda4_baseline.py aprovou alteração de exit code de deny para exit 2 no Antigravity!", file=sys.stderr)
            sys.exit(1)

        if "A3 divergências em respostas do hook" not in res.stderr and "A3 divergências em respostas do hook" not in res.stdout:
            print(f"FALHA M2: erro esperado em A3 não encontrado:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}", file=sys.stderr)
            sys.exit(1)

        print("✔ Prova por mutação M2 aprovada: onda4_baseline.py detectou quebra do hook do Antigravity em A3 com exit 1 (em clone temporário).")


def run_mutation_3(repo_root: Path) -> None:
    """Mutação M3: desproteger imports de safety-gate.py deve fazer test_hook_failclosed.py falhar."""
    with tempfile.TemporaryDirectory(prefix="ceh_mut3_") as tmp_dir:
        tmp_repo = _create_temp_clone(repo_root, tmp_dir)
        gate_file = tmp_repo / "clearer-engineering" / "scripts" / "safety-gate.py"
        failclosed_test = tmp_repo / "clearer-engineering" / "tests" / "test_hook_failclosed.py"

        # Remove o try dos imports de safety-gate.py NA CÓPIA TEMPORÁRIA (reintroduz a regressão)
        gate_text = gate_file.read_text(encoding="utf-8")
        unprotected_imports = (
            "from ceh_core.engine import Request, Decision, evaluate, evaluate_command\n"
            "from hook_context import handle_hook_lifecycle, get_exit_code\n"
            "_IMPORT_ERROR = None\n"
        )
        # Substitui o bloco try...except por imports diretos
        start_idx = gate_text.find("_IMPORT_ERROR: Exception | None = None")
        end_idx = gate_text.find("def _fallback_exit_code")
        if start_idx == -1 or end_idx == -1:
            raise RuntimeError("Não foi possível localizar bloco de imports em safety-gate.py para M3")

        mutated_gate = gate_text[:start_idx] + unprotected_imports + "\n\n" + gate_text[end_idx:]
        gate_file.write_text(mutated_gate, encoding="utf-8")

        res = subprocess.run([sys.executable, str(failclosed_test)], capture_output=True, text=True, cwd=str(tmp_repo))
        if res.returncode == 0:
            print("FALHA M3: test_hook_failclosed.py aprovou safety-gate.py sem tratamento de erro nos imports!", file=sys.stderr)
            sys.exit(1)

        print("✔ Prova por mutação M3 aprovada: desproteger imports fez test_hook_failclosed.py reprovar com exit 1 (em clone temporário).")


def main():
    repo_root = Path(__file__).resolve().parents[3]
    print("=== Executando Provas de Mutação do PR-13 em Clones Temporários (Regra AT5) ===")
    run_mutation_1(repo_root)
    run_mutation_2(repo_root)
    run_mutation_3(repo_root)
    print("=== Todas as 3 Provas de Mutação do PR-13 passaram com sucesso! ===")


if __name__ == "__main__":
    main()
