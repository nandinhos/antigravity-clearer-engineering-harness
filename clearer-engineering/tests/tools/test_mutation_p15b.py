#!/usr/bin/env python3
"""
test_mutation_p15b.py — Provas de falsificabilidade por mutação do PR-15b.
Regra AT5 (Handoff 046 / Handoff 072 / Handoff 075): mutação estritamente em clone temporário.

Comprova determinística e hermeticamente que a rede de verificação do PR-15b falha se:
1. M1: Muse for posicionado depois do Claude no despachante (violação da ordem de resolução / test_adapters falha).
2. M2: O render do Muse for alterado para devolver exit 2 (violação do contrato de saída do Muse / test_adapters falha).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def _create_temp_clone(repo_root: Path, tmp_dir: str) -> Path:
    tmp_repo = Path(tmp_dir).resolve()
    shutil.copytree(repo_root / "clearer-engineering", tmp_repo / "clearer-engineering")
    shutil.copytree(repo_root / "docs", tmp_repo / "docs")
    if (repo_root / ".ceh").is_dir():
        shutil.copytree(repo_root / ".ceh", tmp_repo / ".ceh")
    shutil.copy(repo_root / "install.sh", tmp_repo / "install.sh")
    shutil.copy(repo_root / "uninstall.sh", tmp_repo / "uninstall.sh")
    return tmp_repo


def run_mutation_1(repo_root: Path) -> None:
    """M1: Muse posicionado depois do Claude no despachante hook_context.py deve quebrar test_adapters."""
    with tempfile.TemporaryDirectory(prefix="ceh_mut15b_1_") as tmp_dir:
        tmp_repo = _create_temp_clone(repo_root, tmp_dir)
        hook_ctx_file = tmp_repo / "clearer-engineering" / "scripts" / "hook_context.py"
        test_adapters_py = tmp_repo / "clearer-engineering" / "tests" / "test_adapters.py"

        code = hook_ctx_file.read_text(encoding="utf-8")
        target = "    AntigravityAdapter(),\n    MuseAdapter(),\n    ClaudeCodeAdapter(),"
        replacement = "    AntigravityAdapter(),\n    ClaudeCodeAdapter(),\n    MuseAdapter(),"
        if target not in code:
            raise RuntimeError("Não foi possível encontrar a ordem de adaptadores em hook_context.py")
        mutated = code.replace(target, replacement)
        hook_ctx_file.write_text(mutated, encoding="utf-8")

        res = subprocess.run(
            [sys.executable, str(test_adapters_py)],
            capture_output=True,
            text=True,
            cwd=str(tmp_repo),
        )
        if res.returncode == 0:
            print("FALHA M1: test_adapters.py aprovou Muse posicionado depois do Claude!", file=sys.stderr)
            sys.exit(1)

        err_out = res.stderr + "\n" + res.stdout
        if "FAIL" not in err_out and "AssertionError" not in err_out:
            print(f"FALHA M1: falha de teste esperada não encontrada:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}", file=sys.stderr)
            sys.exit(1)

        print("✔ Prova por mutação M1 aprovada: test_adapters.py rejeitou Muse posicionado depois do Claude (em clone temporário).")


def run_mutation_2(repo_root: Path) -> None:
    """M2: MuseAdapter.render devolvendo exit 2 deve quebrar test_adapters."""
    with tempfile.TemporaryDirectory(prefix="ceh_mut15b_2_") as tmp_dir:
        tmp_repo = _create_temp_clone(repo_root, tmp_dir)
        muse_adapter_file = tmp_repo / "clearer-engineering" / "scripts" / "adapters" / "muse.py"
        test_adapters_py = tmp_repo / "clearer-engineering" / "tests" / "test_adapters.py"

        code = muse_adapter_file.read_text(encoding="utf-8")
        target = "return {}, 0"
        if target not in code:
            raise RuntimeError(f"Não foi possível encontrar '{target}' em muse.py")
        mutated = code.replace(target, "return {}, 2")
        muse_adapter_file.write_text(mutated, encoding="utf-8")

        res = subprocess.run(
            [sys.executable, str(test_adapters_py)],
            capture_output=True,
            text=True,
            cwd=str(tmp_repo),
        )
        if res.returncode == 0:
            print("FALHA M2: test_adapters.py aprovou MuseAdapter com exit 2 no allow!", file=sys.stderr)
            sys.exit(1)

        err_out = res.stderr + "\n" + res.stdout
        if "FAIL" not in err_out and "AssertionError" not in err_out:
            print(f"FALHA M2: falha de teste esperada não encontrada:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}", file=sys.stderr)
            sys.exit(1)

        print("✔ Prova por mutação M2 aprovada: test_adapters.py rejeitou MuseAdapter com exit 2 (em clone temporário).")


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    print("=== [CEH PR-15b: Provas de Falsificabilidade por Mutação (Regra AT5)] ===")
    run_mutation_1(repo_root)
    run_mutation_2(repo_root)
    print("\n[SUCESSO] Todas as 2 mutações do PR-15b foram falsificadas e detectadas pelas baterias de teste!")


if __name__ == "__main__":
    main()
