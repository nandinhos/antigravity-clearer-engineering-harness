#!/usr/bin/env python3
"""
ceh_core/git_invocation.py — Git invocation canonicalization and pathspec resolution.
Nucleo agnostico de host: ZERO referencias a formatos de host.
"""
from __future__ import annotations

from pathlib import Path

from ceh_core.lexer import resolve_command_head
from ceh_core.normalize import normalize_path, tokenize_command
from ceh_core.environment import find_repo_root


def resolve_git_invocation(
    cmd_line: str,
    base_cwd: Path | str | None = None
) -> tuple[bool, str | None, list[str], Path | None, str, str | None]:
    """
    Analisa e canonicaliza a invocacao do Git para qualquer subcomando (G3 / R5).
    Retorna: (is_git, subcommand, remaining_args, target_repo_root, canonical_cmd, error_reason)
    """
    try:
        tokens = tokenize_command(cmd_line, posix=True)
    except Exception as e:
        return False, None, [], None, cmd_line, f"Erro de parsing na linha git: {e}"

    idx, _ = resolve_command_head(tokens)
    tokens = tokens[idx:]
    while tokens and "=" in tokens[0] and not tokens[0].startswith(("-", "=")):
        tokens = tokens[1:]

    import os
    if not tokens or os.path.basename(tokens[0]) not in ("git", "git.exe"):
        return False, None, [], None, cmd_line, None

    current_dir = Path.cwd().resolve() if base_cwd is None else Path(normalize_path(base_cwd, resolve_home=False))
    subcommand = None
    remaining_args = []
    i = 1

    INNOCUOUS_GLOBAL_FLAGS = {
        "--no-pager", "-p", "-P", "--paginate",
        "--no-replace-objects", "--literal-pathspecs", "--bare"
    }

    while i < len(tokens):
        token = tokens[i]
        if token == "-C" and i + 1 < len(tokens):
            current_dir = Path(normalize_path(current_dir / tokens[i+1], resolve_home=False))
            i += 2
            continue
        elif token.startswith("-C") and len(token) > 2:
            path_part = token[2:]
            current_dir = Path(normalize_path(current_dir / path_part, resolve_home=False))
            i += 1
            continue
        elif token.startswith("--git-dir") or token.startswith("--work-tree") or token == "-c" or token.startswith("-c="):
            return True, None, [], None, cmd_line, f"Opção global do Git não homologada no Safety Gate ({token})"
        elif token in INNOCUOUS_GLOBAL_FLAGS:
            i += 1
            continue
        elif token.startswith("-"):
            return True, None, [], None, cmd_line, f"Opção global do Git não homologada no Safety Gate ({token})"
        else:
            subcommand = token
            remaining_args = tokens[i+1:]
            break

    if subcommand in ("checkout", "restore"):
        norm_args = []
        for arg in remaining_args:
            if arg in ("./", ".//", "./.") or (arg.startswith("./") and all(c in "./" for c in arg)):
                norm_args.append(".")
            else:
                norm_args.append(arg)
        remaining_args = norm_args

    repo_root = find_repo_root(current_dir) if current_dir.exists() else current_dir
    if subcommand is None:
        return True, None, [], repo_root, "git", None

    canonical_cmd = "git " + subcommand + (" " + " ".join(remaining_args) if remaining_args else "")
    return True, subcommand, remaining_args, repo_root, canonical_cmd, None
