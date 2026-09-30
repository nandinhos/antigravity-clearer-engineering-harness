#!/usr/bin/env python3
# ==============================================================================
# hook_context.py — PreToolUse Hook Context & Host Adapters
# ==============================================================================
"""
Resolves target working directory and environment from PreToolUse hook payloads
(Antigravity and Claude Code), preventing cwd leakage to plugin directories (P0/G6).
Isolates host-specific contracts and exit codes outside of ceh_core and safety-gate.
Enforces Invariant 7 (fail-closed on ambiguity): unresolved context escalates to production.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Callable

from ceh_core.engine import Request, Decision


def is_claude_host(payload: Any = None) -> bool:
    """Detecta se o host em execucao e o Claude Code via payload prioritario ou variaveis de ambiente."""
    if isinstance(payload, dict):
        if "toolCall" in payload:
            return False
        if "hook_event_name" in payload or "tool_name" in payload:
            return True
    return any(k in os.environ for k in ("CLAUDECODE", "CLAUDE_PROJECT_DIR", "CLAUDE_PID"))


def get_exit_code(decision: str, payload: Any = None) -> int:
    """
    Retorna o codigo de saida padronizado para o host:
    - No Antigravity (IDE e CLI): SEMPRE exit 0 com JSON de decisao (v1.4.1).
    - No Claude Code: exit 2 para deny; exit 0 para ask ou allow.
    """
    if decision == "deny":
        return 2 if is_claude_host(payload) else 0
    return 0


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
    tool_name = extract_tool_name(payload)
    is_claude = (
        payload.get("hook_event_name") == "PreToolUse"
        or tool_name in ("Bash", "Write", "Edit", "MultiEdit", "NotebookEdit")
    ) and "toolCall" not in payload

    if is_claude:
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

    res: dict[str, Any] = {"decision": decision}
    if reason:
        res["reason"] = reason
    return res


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


def handle_terminal_tool(
    tool_name: str,
    payload: dict[str, Any],
    engine_eval_fn: Callable[[Request], Decision],
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

        req = Request(command=cmd_line, cwd=target_dir, explicit_env=explicit_env)
        res = engine_eval_fn(req)
        if isinstance(res, tuple):
            decision, reason = res[0], res[1]
        elif hasattr(res, "decision"):
            decision, reason = res.decision, res.reason
        else:
            decision, reason = "allow", ""

        if decision == "ask" and "toolCall" in payload:
            decision = "deny"
            reason = f"{reason}\n[CEH CONTEXT LOCK] Decisão 'ask' convertida para 'deny': ask não suspende a execução neste host (H1, Handoff 006)."

        return format_host_response(payload, decision, reason)
    finally:
        try:
            os.chdir(original_cwd)
        except OSError:
            pass


def handle_file_write_tool(
    tool_name: str,
    payload: dict[str, Any],
    engine_eval_fn: Callable[[Request], Decision],
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
    req = Request(command="", cwd=target_dir, explicit_env=explicit_env, target_paths=[target_file])
    res = engine_eval_fn(req)
    if isinstance(res, tuple):
        dec_val, reason_val = res[0], res[1]
    elif hasattr(res, "decision"):
        dec_val, reason_val = res.decision, res.reason
    else:
        dec_val, reason_val = "allow", ""

    if dec_val == "allow":
        reason_val = ""

    return format_host_response(payload, dec_val, reason_val)


TOOL_DISPATCH: dict[str, Callable[[str, dict[str, Any], Callable[[Request], Decision]], dict[str, Any]]] = {
    "run_command": handle_terminal_tool,
    "Bash": handle_terminal_tool,
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
    engine_eval_fn: Callable[[Request], Decision],
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

    return handler(tool_name, payload, engine_eval_fn)


def handle_hook_lifecycle(
    raw_input: str,
    engine_eval_fn: Callable[[Request], Decision]
) -> tuple[dict[str, Any], int]:
    """
    Ciclo de vida completo do hook a partir de string bruta do stdin:
    1. Parse e validacao do JSON (fail-closed seguro com saida do host).
    2. Avaliacao do payload contra o motor.
    3. Mapeamento de decisao em codigo de saida especifico do host.
    Retorna: (response_dict, exit_code)
    """
    payload = None
    if not raw_input.strip():
        resp = {"decision": "deny", "reason": "[CEH SAFETY GATE ERROR] Payload vazio recebido no hook."}
        return resp, get_exit_code("deny", None)

    try:
        payload = json.loads(raw_input)
    except Exception as e:
        resp = {"decision": "deny", "reason": f"[CEH SAFETY GATE ERROR] Hook execution failed: JSON inválido ({str(e)})"}
        return resp, get_exit_code("deny", None)

    if not isinstance(payload, dict):
        resp = {"decision": "deny", "reason": "[CEH SAFETY GATE ERROR] Invalid hook payload: expected JSON object."}
        return resp, get_exit_code("deny", None)

    try:
        result = evaluate_hook_payload(payload, engine_eval_fn)
    except Exception as e:
        resp = {"decision": "deny", "reason": f"[CEH SAFETY GATE ERROR] Falha ao avaliar payload do hook: {str(e)}"}
        return resp, get_exit_code("deny", payload)

    decision = "allow"
    if "decision" in result:
        decision = result.get("decision", "allow")
    elif "hookSpecificOutput" in result:
        hso = result.get("hookSpecificOutput")
        if isinstance(hso, dict):
            decision = hso.get("permissionDecision", "allow")

    exit_code = get_exit_code(decision, payload)
    return result, exit_code
