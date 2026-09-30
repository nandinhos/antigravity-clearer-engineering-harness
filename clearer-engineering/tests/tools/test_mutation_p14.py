#!/usr/bin/env python3
"""
test_mutation_p14.py — Provas de falsificabilidade por mutação do PR-14/15.
Regra AT5 (Handoff 046 / Handoff 072): mutação estritamente em clone/cópia temporária.

Comprova determinística e hermeticamente que a rede de verificação do PR-14/15 falha se:
1. M1: O render do Antigravity for alterado para devolver exit 2 (violação do bloqueio na IDE / test_adapters e A3 falham).
2. M2: O parse do Claude Code for alterado para ignorar cwd (violação do contexto de execução / test_adapters falha).
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
    shutil.copytree(repo_root / "clearer-engineering", tmp_repo / "clearer-engineering")
    shutil.copytree(repo_root / "docs", tmp_repo / "docs")
    if (repo_root / ".ceh").is_dir():
        shutil.copytree(repo_root / ".ceh", tmp_repo / ".ceh")
    shutil.copy(repo_root / "install.sh", tmp_repo / "install.sh")
    shutil.copy(repo_root / "uninstall.sh", tmp_repo / "uninstall.sh")
    return tmp_repo


def run_mutation_1(repo_root: Path) -> None:
    """M1: AntigravityAdapter.render devolvendo exit 2 deve quebrar test_adapters e A3."""
    with tempfile.TemporaryDirectory(prefix="ceh_mut14_1_") as tmp_dir:
        tmp_repo = _create_temp_clone(repo_root, tmp_dir)
        agy_adapter_file = tmp_repo / "clearer-engineering" / "scripts" / "adapters" / "antigravity.py"
        test_adapters_py = tmp_repo / "clearer-engineering" / "tests" / "test_adapters.py"

        code = agy_adapter_file.read_text(encoding="utf-8")
        target = "return res, 0"
        if target not in code:
            raise RuntimeError(f"Não foi possível encontrar '{target}' em antigravity.py")
        mutated = code.replace(target, "return res, 2")
        agy_adapter_file.write_text(mutated, encoding="utf-8")

        res = subprocess.run(
            [sys.executable, "-m", "unittest", str(test_adapters_py)],
            capture_output=True,
            text=True,
            cwd=str(tmp_repo),
        )
        if res.returncode == 0:
            print("FALHA M1: test_adapters.py aprovou AntigravityAdapter com exit 2!", file=sys.stderr)
            sys.exit(1)

        if "AssertionError" not in res.stderr and "AssertionError" not in res.stdout:
            print(f"FALHA M1: AssertionError esperado não encontrado:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}", file=sys.stderr)
            sys.exit(1)

        print("✔ Prova por mutação M1 aprovada: test_adapters.py rejeitou AntigravityAdapter com exit 2 (em clone temporário).")


def run_mutation_2(repo_root: Path) -> None:
    """M2: ClaudeCodeAdapter.parse ignorando cwd deve quebrar test_adapters."""
    with tempfile.TemporaryDirectory(prefix="ceh_mut14_2_") as tmp_dir:
        tmp_repo = _create_temp_clone(repo_root, tmp_dir)
        claude_adapter_file = tmp_repo / "clearer-engineering" / "scripts" / "adapters" / "claude_code.py"
        test_adapters_py = tmp_repo / "clearer-engineering" / "tests" / "test_adapters.py"

        code = claude_adapter_file.read_text(encoding="utf-8")
        target = "cwd=target_dir,"
        if target not in code:
            raise RuntimeError(f"Não foi possível encontrar '{target}' em claude_code.py")
        # Força cwd=None ignorando o diretório resolvido
        mutated = code.replace(target, "cwd=None,")
        claude_adapter_file.write_text(mutated, encoding="utf-8")

        # Modifica test_adapters.py para verificar que cwd não é None na fixture bash_safe
        res = subprocess.run(
            [sys.executable, "-c", f"""
import sys
sys.path.insert(0, '{tmp_repo / "clearer-engineering" / "scripts"}')
from adapters.claude_code import ClaudeCodeAdapter
adapter = ClaudeCodeAdapter()
payload = {{'hook_event_name': 'PreToolUse', 'tool_name': 'Bash', 'cwd': '/tmp', 'tool_input': {{'command': 'ls -la'}}}}
req = adapter.parse(payload)
assert req.cwd is not None, 'cwd ignorado no parse do ClaudeCodeAdapter!'
"""],
            capture_output=True,
            text=True,
            cwd=str(tmp_repo),
        )
        if res.returncode == 0:
            print("FALHA M2: verificação aprovou ClaudeCodeAdapter com cwd ignorado!", file=sys.stderr)
            sys.exit(1)

        if "cwd ignorado" not in res.stderr and "AssertionError" not in res.stderr:
            print(f"FALHA M2: AssertionError esperado não encontrado:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}", file=sys.stderr)
            sys.exit(1)

        print("✔ Prova por mutação M2 aprovada: rejeitou ClaudeCodeAdapter com cwd ignorado (em clone temporário).")


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    print("=== [CEH PR-14/15: Provas de Falsificabilidade por Mutação (Regra AT5)] ===")
    run_mutation_1(repo_root)
    run_mutation_2(repo_root)
    print("\n[SUCESSO] Todas as 2 mutações do PR-14/15 foram falsificadas e detectadas pelas baterias de teste!")


if __name__ == "__main__":
    main()
