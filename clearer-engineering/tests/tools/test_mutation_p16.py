#!/usr/bin/env python3
"""
test_mutation_p16.py — Provas de falsificabilidade por mutação do PR-16 (Handoff 079 / BI1).
Regra AT5: mutação estritamente em clone temporário hermético.

Comprova determinística e hermeticamente que:
M1: Se a reserva (adapters/fallback.py) responder "deny" para o payload do Muse,
    test_hook_failclosed.py E test_package.py REPROVAM.
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


def run_mutation_fallback_muse_deny(repo_root: Path) -> None:
    """M1: Fallback respondendo 'deny' para o Muse deve quebrar test_hook_failclosed e test_package."""
    with tempfile.TemporaryDirectory(prefix="ceh_mut16_1_") as tmp_dir:
        tmp_repo = _create_temp_clone(repo_root, tmp_dir)
        fallback_file = tmp_repo / "clearer-engineering" / "scripts" / "adapters" / "fallback.py"
        test_failclosed_py = tmp_repo / "clearer-engineering" / "tests" / "test_hook_failclosed.py"
        test_package_py = tmp_repo / "clearer-engineering" / "tests" / "test_package.py"

        code = fallback_file.read_text(encoding="utf-8")
        target = '"decision": "block",'
        replacement = '"decision": "deny",'
        if target not in code:
            raise RuntimeError("Não foi possível encontrar a resposta 'block' em fallback.py")
        mutated = code.replace(target, replacement)
        fallback_file.write_text(mutated, encoding="utf-8")

        # 1. Deve quebrar test_hook_failclosed.py
        res1 = subprocess.run(
            [sys.executable, str(test_failclosed_py)],
            capture_output=True,
            text=True,
            cwd=str(tmp_repo),
        )
        if res1.returncode == 0:
            print("FALHA M1: test_hook_failclosed.py aprovou fallback com 'deny' para o Muse!", file=sys.stderr)
            sys.exit(1)

        # 2. Deve quebrar test_package.py
        res2 = subprocess.run(
            [sys.executable, str(test_package_py)],
            capture_output=True,
            text=True,
            cwd=str(tmp_repo),
        )
        if res2.returncode == 0:
            print("FALHA M1: test_package.py aprovou pacote corrompido com 'deny' para o Muse!", file=sys.stderr)
            sys.exit(1)

        print("✔ M1 aprovada: a reserva respondendo 'deny' para o Muse quebra os testes como esperado.")


def main() -> int:
    repo_root = Path(__file__).resolve().parents[3]
    print("=== [Executando Mutações de Falsificabilidade PR-16 / BI1] ===")
    run_mutation_fallback_muse_deny(repo_root)
    print("✔ Todas as mutações do PR-16 foram rejeitadas com sucesso pela rede de verificação.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
