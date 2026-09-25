#!/usr/bin/env python3
# ==============================================================================
# hook_context.py — PreToolUse Hook Context & Target Directory Resolver
# ==============================================================================
"""
Resolves target working directory and environment from PreToolUse hook payloads
(Antigravity and Claude Code), preventing cwd leakage to plugin directories (P0/G6).
Enforces Invariant 7 (fail-closed on ambiguity): unresolved context escalates to production.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Callable


def resolve_hook_target(payload: dict[str, Any]) -> tuple[Path | None, str | None, bool]:
    """
    Resolves the target working directory from Antigravity (toolCall) or Claude payloads.

    Returns:
        (target_path, explicit_env, force_deny_push)
        - target_path: Path to chdir to, or None if unresolved/non-existent.
        - explicit_env: 'production' if unresolved or non-existent, otherwise None.
        - force_deny_push: True if git push must be blocked due to missing/invalid target repo.
    """
    raw_cwd: str | None = None
    ws_paths = payload.get("workspacePaths") or []
    ws_root: Path | None = None

    if ws_paths:
        first_ws = os.path.expanduser(str(ws_paths[0]))
        if os.path.isabs(first_ws):
            ws_root = Path(first_ws).resolve()

    if "toolCall" in payload:
        args = (payload.get("toolCall") or {}).get("args") or {}
        raw_cwd = args.get("Cwd")
        if raw_cwd is None and ws_root is not None:
            raw_cwd = str(ws_root)
    elif "tool_input" in payload or "cwd" in payload:
        raw_cwd = payload.get("cwd")

    if not raw_cwd:
        return None, "production", True

    expanded = os.path.expanduser(str(raw_cwd))
    if os.path.isabs(expanded):
        resolved = Path(expanded).resolve()
    else:
        # Relative path (e.g. "." or "subdir"): must anchor exclusively to workspacePaths[0]
        if ws_root is not None and ws_root.is_absolute():
            resolved = (ws_root / expanded).resolve()
        else:
            return None, "production", True

    if not resolved.is_dir():
        return None, "production", True

    return resolved, None, False


def extract_hook_command(payload: dict[str, Any]) -> tuple[str, str]:
    """
    Extracts (tool_name, command_line) from Antigravity or Claude hook payloads.
    """
    if "toolCall" in payload:
        tc = payload.get("toolCall") or {}
        return str(tc.get("name", "")), str((tc.get("args") or {}).get("CommandLine", ""))
    if "tool_input" in payload or "tool_name" in payload:
        tool_name = str(payload.get("tool_name", ""))
        cmd = str((payload.get("tool_input") or {}).get("command", ""))
        return tool_name, cmd
    return "", ""


def is_git_push_command(cmd_line: str) -> bool:
    """Detects if a command line executes git push."""
    return bool(re.search(r"\bgit\s+push\b", cmd_line))


def evaluate_hook_payload(
    payload: dict[str, Any],
    evaluate_command_fn: Callable[[str, str | None], tuple[str, str, str, str]],
) -> dict[str, str]:
    """
    Processes PreToolUse hook payload, safely resolving target directory before evaluation.
    """
    tool_name, cmd_line = extract_hook_command(payload)
    if tool_name not in ("run_command", "Bash") or not cmd_line.strip():
        return {"decision": "allow"}

    target_dir, explicit_env, force_deny_push = resolve_hook_target(payload)
    original_cwd = os.getcwd()

    try:
        if target_dir is not None:
            os.chdir(target_dir)

        if force_deny_push and is_git_push_command(cmd_line):
            return {
                "decision": "deny",
                "reason": "[CEH PRE-PUSH CI GATE] ⛔ Push bloqueado: repositório de destino não resolvido a partir do hook.",
            }

        decision, reason, _, _ = evaluate_command_fn(cmd_line, explicit_env)
        return {"decision": decision, "reason": reason}
    finally:
        try:
            os.chdir(original_cwd)
        except OSError:
            pass
