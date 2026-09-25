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
        tc = payload.get("toolCall")
        if not isinstance(tc, dict):
            raise ValueError("Invalid toolCall format: expected JSON object.")
        args = tc.get("args")
        if args is not None and not isinstance(args, dict):
            raise ValueError("Invalid toolCall.args format: expected JSON object.")
        args = args or {}
        raw_cwd = args.get("Cwd")
        if raw_cwd is None and ws_root is not None:
            raw_cwd = str(ws_root)
    elif "tool_input" in payload or "cwd" in payload:
        ti = payload.get("tool_input")
        if ti is not None and not isinstance(ti, dict):
            raise ValueError("Invalid tool_input format: expected JSON object.")
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
        tc = payload.get("toolCall")
        if not isinstance(tc, dict):
            raise ValueError("Invalid toolCall format: expected JSON object.")
        args = tc.get("args")
        if args is not None and not isinstance(args, dict):
            raise ValueError("Invalid toolCall.args format: expected JSON object.")
        args = args or {}
        return str(tc.get("name", "")), str(args.get("CommandLine", ""))
    if "tool_input" in payload or "tool_name" in payload:
        tool_name = str(payload.get("tool_name", ""))
        ti = payload.get("tool_input")
        if ti is not None and not isinstance(ti, dict):
            raise ValueError("Invalid tool_input format: expected JSON object.")
        cmd = str((ti or {}).get("command", ""))
        return tool_name, cmd
    return "", ""


def is_git_push_command(cmd_line: str) -> bool:
    """Detects if a command line executes git push."""
    return bool(re.search(r"\bgit\s+push\b", cmd_line))


def format_host_response(payload: dict[str, Any], decision: str, reason: str = "") -> dict[str, Any]:
    """Formats decision response according to host contract (Antigravity or Claude Code)."""
    if "tool_input" in payload or "tool_name" in payload or payload.get("hook_event_name") == "PreToolUse":
        res: dict[str, Any] = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": decision,
            }
        }
        if reason:
            res["hookSpecificOutput"]["permissionDecisionReason"] = reason
        return res

    res: dict[str, Any] = {"decision": decision}
    if reason:
        res["reason"] = reason
    return res


def evaluate_hook_payload(
    payload: dict[str, Any],
    evaluate_command_fn: Callable[[str, str | None], tuple[str, str, str, str]],
) -> dict[str, Any]:
    """
    Processes PreToolUse hook payload, safely resolving target directory before evaluation.
    """
    if not isinstance(payload, dict):
        raise ValueError("Invalid hook payload: expected JSON object.")

    tool_name, cmd_line = extract_hook_command(payload)
    if tool_name not in ("run_command", "Bash") or not cmd_line.strip():
        return format_host_response(payload, "allow")

    target_dir, explicit_env, force_deny_push = resolve_hook_target(payload)
    original_cwd = os.getcwd()

    try:
        if target_dir is not None:
            os.chdir(target_dir)

        if force_deny_push and is_git_push_command(cmd_line):
            return format_host_response(
                payload,
                "deny",
                "[CEH PRE-PUSH CI GATE] ⛔ Push bloqueado: repositório de destino não resolvido a partir do hook.",
            )

        decision, reason, _, _ = evaluate_command_fn(cmd_line, explicit_env)
        # PR-00c: No host agy (toolCall presente), ask falha aberto (fail-open / H1); converter compulsoriamente para deny
        if decision == "ask" and "toolCall" in payload:
            decision = "deny"
            reason = f"{reason}\n[CEH CONTEXT LOCK] Decisão 'ask' convertida para 'deny': ask não suspende a execução neste host (H1, Handoff 006)."

        return format_host_response(payload, decision, reason)
    finally:
        try:
            os.chdir(original_cwd)
        except OSError:
            pass
