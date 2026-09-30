#!/usr/bin/env python3
# ==============================================================================
# claude_code.py — Claude Code Host Adapter (PR-14/15)
# ==============================================================================
"""
Adapter for Claude Code (PreToolUse Hook).
Detects 'hook_event_name' / 'tool_name' payloads or environment variables,
parses Bash / Write / Edit tools, and renders hookSpecificOutput responses with exit codes.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from adapters.base import HostAdapter
from ceh_core.engine import Request, Decision


class ClaudeCodeAdapter(HostAdapter):
    """Adaptador de integração para Claude Code."""

    TERMINAL_TOOLS = {"Bash"}
    FILE_WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}

    @property
    def name(self) -> str:
        return "claude_code"

    def detect(self, payload: Any) -> bool:
        """
        Detecta payload emitido pelo Claude Code.
        Critério 1: chaves específicas no payload (hook_event_name ou tool_name) sem toolCall.
        Critério 2: variáveis de ambiente características caso o payload seja vazio/genérico.
        """
        if isinstance(payload, dict):
            if "toolCall" in payload:
                return False
            if "hook_event_name" in payload or "tool_name" in payload:
                return True
        return any(k in os.environ for k in ("CLAUDECODE", "CLAUDE_PROJECT_DIR", "CLAUDE_PID"))

    def resolve_target(self, payload: dict[str, Any]) -> tuple[Path | None, str | None, bool]:
        """
        Resolve o diretório de trabalho a partir de payload.cwd ou tool_input.Cwd.
        Retorna: (target_path, explicit_env, force_deny_push)
        """
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
            return None, "production", True

        if not resolved.is_dir():
            return None, "production", True

        return resolved, None, False

    def parse(self, payload: dict[str, Any]) -> Request:
        """Converte payload do Claude Code em um Request agnóstico."""
        if not isinstance(payload, dict):
            raise ValueError("Invalid hook payload: expected JSON object.")

        tool_name = str(payload.get("tool_name", "")).strip()
        if not tool_name:
            raise ValueError("Nenhuma ferramenta identificável no payload do hook.")

        ti = payload.get("tool_input")
        if ti is not None and not isinstance(ti, dict):
            raise ValueError("Invalid tool_input format: expected JSON object.")
        ti = ti or {}

        target_dir, explicit_env, force_deny_push = self.resolve_target(payload)

        if tool_name in self.TERMINAL_TOOLS:
            cmd_line = str(ti.get("command") or ti.get("CommandLine") or "")
            if not cmd_line.strip():
                raise ValueError(f"Comando vazio ou ausente para ferramenta de terminal '{tool_name}'.")

            if force_deny_push and bool(re.search(r"\bgit\s+push\b", cmd_line)):
                raise ValueError("[CEH PRE-PUSH CI GATE] ⛔ Push bloqueado: repositório de destino não resolvido a partir do hook.")

            return Request(
                command=cmd_line,
                cwd=target_dir,
                explicit_env=explicit_env,
            )

        elif tool_name in self.FILE_WRITE_TOOLS:
            target_file = str(ti.get("file_path") or ti.get("notebook_path") or ti.get("TargetFile") or "").strip()
            if not target_file:
                raise ValueError(f"Caminho de arquivo alvo ausente para ferramenta '{tool_name}'.")

            return Request(
                command="",
                cwd=target_dir,
                explicit_env=explicit_env,
                target_paths=[target_file],
            )

        raise ValueError(f"Ferramenta desconhecida '{tool_name}': fail-closed ativado.")

    def render(self, decision: Decision, payload: dict[str, Any] | None = None) -> tuple[dict[str, Any], int]:
        """
        Renderiza resposta hookSpecificOutput para o Claude Code:
        - allow: {} com exit 0
        - ask: hookSpecificOutput com permissionDecision: ask e exit 0
        - deny: hookSpecificOutput com permissionDecision: deny e exit 2
        """
        dec_val = decision.decision
        reason_val = decision.reason

        if dec_val == "allow":
            return {}, 0

        res: dict[str, Any] = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": dec_val,
            }
        }
        if reason_val:
            res["hookSpecificOutput"]["permissionDecisionReason"] = reason_val

        exit_code = 2 if dec_val == "deny" else 0
        return res, exit_code

    def render_error(self, message: str, payload: dict[str, Any] | None = None) -> tuple[dict[str, Any], int]:
        """Renderiza erro crítico/exceção como deny com exit 2."""
        prefix = "" if message.startswith("[CEH") else "[CEH HOOK ERROR] "
        is_native_claude = False
        if isinstance(payload, dict):
            if payload.get("hook_event_name") == "PreToolUse":
                is_native_claude = True
            tool_name = payload.get("tool_name")
            if tool_name in self.TERMINAL_TOOLS or tool_name in self.FILE_WRITE_TOOLS:
                is_native_claude = True

        if is_native_claude:
            res: dict[str, Any] = {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": f"{prefix}{message}",
                }
            }
            return res, 2

        return {
            "decision": "deny",
            "reason": f"{prefix}{message}"
        }, 2
