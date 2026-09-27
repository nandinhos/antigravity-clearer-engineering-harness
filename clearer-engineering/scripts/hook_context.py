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
        raw_cwd = payload.get("cwd") or (ti or {}).get("Cwd")

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


def extract_tool_name(payload: dict[str, Any]) -> str:
    """Extracts the tool name from either Antigravity (toolCall) or Claude hook payloads."""
    if "toolCall" in payload:
        tc = payload.get("toolCall")
        if not isinstance(tc, dict):
            raise ValueError("Invalid toolCall format: expected JSON object.")
        return str(tc.get("name", "")).strip()
    if "tool_name" in payload:
        return str(payload.get("tool_name", "")).strip()
    return ""


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
        return str(tc.get("name", "")).strip(), str(args.get("CommandLine", ""))
    if "tool_input" in payload or "tool_name" in payload:
        tool_name = str(payload.get("tool_name", "")).strip()
        ti = payload.get("tool_input")
        if ti is not None and not isinstance(ti, dict):
            raise ValueError("Invalid tool_input format: expected JSON object.")
        cmd = str((ti or {}).get("command") or (ti or {}).get("CommandLine") or "")
        return tool_name, cmd
    return "", ""


def is_git_push_command(cmd_line: str) -> bool:
    """Detects if a command line executes git push."""
    return bool(re.search(r"\bgit\s+push\b", cmd_line))


def format_host_response(payload: dict[str, Any], decision: str, reason: str = "") -> dict[str, Any]:
    """Formats decision response according to host contract (Antigravity or Claude Code)."""
    # Host Claude: identificado por hook_event_name 'PreToolUse' ou ferramentas nativas do Claude
    tool_name = extract_tool_name(payload)
    is_claude = (
        payload.get("hook_event_name") == "PreToolUse"
        or tool_name in ("Bash", "Write", "Edit", "MultiEdit", "NotebookEdit")
    ) and "toolCall" not in payload

    if is_claude:
        # PR-00e: No Claude Code, o gate nunca aprova — só nega ou pede confirmação (F6).
        # Retornar objeto vazio para allow devolve o fluxo normal de permissões ao Claude.
        if decision == "allow":
            return {}

        res: dict[str, Any] = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": decision,
            }
        }
        if reason:
            res["hookSpecificOutput"]["permissionDecisionReason"] = reason
        return res

    # Antigravity ou sem host identificável (Handoff 036 §3)
    res: dict[str, Any] = {"decision": decision}
    if reason:
        res["reason"] = reason
    return res


def handle_terminal_tool(
    tool_name: str,
    payload: dict[str, Any],
    evaluate_command_fn: Callable[[str, str | None], tuple[str, str, str, str]],
) -> dict[str, Any]:
    """Handles safety evaluation for terminal commands (run_command, Bash)."""
    _, cmd_line = extract_hook_command(payload)
    if not cmd_line.strip():
        return format_host_response(
            payload,
            "deny",
            f"[CEH HOOK ERROR] Comando vazio ou ausente para ferramenta de terminal '{tool_name}'.",
        )

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


def extract_file_write_target(tool_name: str, payload: dict[str, Any]) -> str:
    """Extrai o caminho do arquivo alvo de ferramentas de escrita/edição de arquivo."""
    if "toolCall" in payload:
        tc = payload.get("toolCall")
        if isinstance(tc, dict):
            args = tc.get("args") or {}
            if isinstance(args, dict):
                return str(args.get("TargetFile", "")).strip()
    if "tool_input" in payload:
        ti = payload.get("tool_input") or {}
        if isinstance(ti, dict):
            return str(ti.get("file_path") or ti.get("notebook_path") or ti.get("TargetFile") or "").strip()
    return ""


def is_protected_cert_file(target_file: str, resolved_target_dir: Path | None = None) -> bool:
    """Verifica se o arquivo alvo é um certificado de CI protegido (.ceh/)."""
    if not target_file:
        return False
    clean = target_file.replace("\\", "/").strip("'\"")
    if any(name in clean for name in ("last-ci-run.json", "last-ci-run.log", "last-evals-run.json")):
        return True
    if re.search(r"(?:^|/)\.ceh(?:/|$)", clean):
        return True
    if resolved_target_dir is not None:
        try:
            full = (resolved_target_dir / Path(clean)).resolve()
            ceh_dir = (resolved_target_dir / ".ceh").resolve()
            if ceh_dir == full or ceh_dir in full.parents:
                return True
        except Exception:
            pass
    return False


def handle_file_write_tool(
    tool_name: str,
    payload: dict[str, Any],
    evaluate_command_fn: Callable[[str, str | None], tuple[str, str, str, str]],
) -> dict[str, Any]:
    """Handles safety evaluation for file write/edit tools (PR-10 / G9)."""
    target_file = extract_file_write_target(tool_name, payload)
    if not target_file:
        return format_host_response(
            payload,
            "deny",
            f"[CEH HOOK ERROR] Caminho de arquivo alvo ausente para ferramenta '{tool_name}'.",
        )

    target_dir, explicit_env, _ = resolve_hook_target(payload)
    if is_protected_cert_file(target_file, target_dir):
        return format_host_response(
            payload,
            "deny",
            f"[CEH CERTIFICATE INTEGRITY - G9] ⛔ Tentativa de escrita/modificação de certificado de CI ({target_file}). Arquivos sob .ceh/ são imutáveis via ferramentas de escrita.",
        )

    return format_host_response(payload, "allow")


# Despacho extensível por ferramenta (PR-09 / PR-10)
TOOL_DISPATCH: dict[str, Callable[[str, dict[str, Any], Callable[[str, str | None], tuple[str, str, str, str]]], dict[str, Any]]] = {
    # Terminal
    "run_command": handle_terminal_tool,
    "Bash": handle_terminal_tool,
    # Escrita / Edição de arquivo (PR-10 / G9)
    "write_to_file": handle_file_write_tool,
    "replace_file_content": handle_file_write_tool,
    "multi_replace_file_content": handle_file_write_tool,
    "Write": handle_file_write_tool,
    "Edit": handle_file_write_tool,
    "MultiEdit": handle_file_write_tool,
    "NotebookEdit": handle_file_write_tool,
}


def evaluate_hook_payload(
    payload: dict[str, Any],
    evaluate_command_fn: Callable[[str, str | None], tuple[str, str, str, str]],
) -> dict[str, Any]:
    """
    Processes PreToolUse hook payload, safely resolving target directory before evaluation.
    Enforces fail-closed on empty, missing, or unrecognized tools.
    """
    if not isinstance(payload, dict):
        raise ValueError("Invalid hook payload: expected JSON object.")

    tool_name = extract_tool_name(payload)
    if not tool_name:
        return format_host_response(
            payload,
            "deny",
            "[CEH HOOK ERROR] Nenhuma ferramenta identificável no payload do hook.",
        )

    handler = TOOL_DISPATCH.get(tool_name)
    if handler is None:
        return format_host_response(
            payload,
            "deny",
            f"[CEH HOOK ERROR] Ferramenta desconhecida '{tool_name}': fail-closed ativado.",
        )

    return handler(tool_name, payload, evaluate_command_fn)

