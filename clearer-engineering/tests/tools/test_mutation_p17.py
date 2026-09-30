#!/usr/bin/env python3
# ==============================================================================
# test_mutation_p17.py — Provas de falsificabilidade por mutação do PR-17
# Regra AT5: mutações executadas estritamente em clone temporário hermético.
#
# Comprova determinística e hermeticamente que:
# M1: Se o parse do Muse ignorar workdir/cwd, test_cross_host_conformance.py REPROVA.
# M2: Se o render do Claude mapear 'ask' para allow ({}, 0), test_cross_host_conformance.py REPROVA.
# ==============================================================================
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


def run_mutation_muse_ignore_workdir(repo_root: Path) -> None:
    """M1: Muse ignorando workdir/cwd deve quebrar o teste de conformidade cross-host."""
    with tempfile.TemporaryDirectory(prefix="ceh_mut17_m1_") as tmp_dir:
        tmp_repo = _create_temp_clone(repo_root, tmp_dir)
        muse_adapter_py = tmp_repo / "clearer-engineering" / "scripts" / "adapters" / "muse.py"
        test_conformance_py = tmp_repo / "clearer-engineering" / "tests" / "test_cross_host_conformance.py"

        code = muse_adapter_py.read_text(encoding="utf-8")
        target = 'raw_cwd = (ti or {}).get("workdir") or payload.get("cwd")'
        replacement = 'raw_cwd = None'
        if target not in code:
            raise RuntimeError(f"Alvo da mutação M1 não encontrado em {muse_adapter_py}")

        mutated = code.replace(target, replacement)
        muse_adapter_py.write_text(mutated, encoding="utf-8")

        res = subprocess.run(
            [sys.executable, str(test_conformance_py)],
            capture_output=True,
            text=True,
            cwd=str(tmp_repo),
        )
        if res.returncode == 0:
            print("FALHA M1: test_cross_host_conformance.py aprovou Muse ignorando workdir/cwd!", file=sys.stderr)
            sys.exit(1)

        print("✔ M1 aprovada: Muse ignorando workdir/cwd quebra a conformidade como esperado.")


def run_mutation_claude_ask_as_allow(repo_root: Path) -> None:
    """M2: Claude mapeando 'ask' para allow ({}, 0) deve quebrar o teste de conformidade."""
    with tempfile.TemporaryDirectory(prefix="ceh_mut17_m2_") as tmp_dir:
        tmp_repo = _create_temp_clone(repo_root, tmp_dir)
        claude_adapter_py = tmp_repo / "clearer-engineering" / "scripts" / "adapters" / "claude_code.py"
        test_conformance_py = tmp_repo / "clearer-engineering" / "tests" / "test_cross_host_conformance.py"

        code = claude_adapter_py.read_text(encoding="utf-8")
        target = 'if dec_val == "allow":'
        replacement = 'if dec_val in ("allow", "ask"):'
        if target not in code:
            raise RuntimeError(f"Alvo da mutação M2 não encontrado em {claude_adapter_py}")

        mutated = code.replace(target, replacement)
        claude_adapter_py.write_text(mutated, encoding="utf-8")

        res = subprocess.run(
            [sys.executable, str(test_conformance_py)],
            capture_output=True,
            text=True,
            cwd=str(tmp_repo),
        )
        if res.returncode == 0:
            print("FALHA M2: test_cross_host_conformance.py aprovou Claude mapeando 'ask' como allow!", file=sys.stderr)
            sys.exit(1)

        print("✔ M2 aprovada: Claude mapeando 'ask' para allow quebra a conformidade como esperado.")


def main() -> int:
    repo_root = Path(__file__).resolve().parents[3]
    print("=== [Executando Mutações de Falsificabilidade PR-17 (Conformidade Cross-Host)] ===")
    run_mutation_muse_ignore_workdir(repo_root)
    run_mutation_claude_ask_as_allow(repo_root)
    print("✔ Todas as mutações do PR-17 foram rejeitadas com sucesso pela rede de verificação.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
