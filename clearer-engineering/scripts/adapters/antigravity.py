#!/usr/bin/env python3
# ==============================================================================
# antigravity.py — Google Antigravity Host Adapter (PR-14/15)
# ==============================================================================
"""
Adapter for Google Antigravity IDE and CLI (PreToolUse Hook).
Detects 'toolCall' payloads, parses run_command / file-write tools,
converts non-blocking 'ask' to 'deny' (H1/Handoff 006), and guarantees exit code 0.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from adapters.base import HostAdapter
from ceh_core.engine import Request, Decision


class AntigravityAdapter(HostAdapter):
    """Adaptador de integração para Google Antigravity (IDE e CLI)."""

    TERMINAL_TOOLS = {"run_command"}
    FILE_WRITE_TOOLS = {
        "write_to_file",
        "replace_file_content",
        "multi_replace_file_content",
    }

    @property
    def name(self) -> str:
        return "antigravity"

    def detect(self, payload: Any) -> bool:
        """Identifica payload emitido pelo Antigravity através da chave 'toolCall'."""
        return isinstance(payload, dict) and "toolCall" in payload

    def resolve_target(self, payload: dict[str, Any]) -> tuple[Path | None, str | None, bool]:
        """
        Resolve o diretório de trabalho a partir de toolCall.args.Cwd e workspacePaths.
        Retorna: (target_path, explicit_env, force_deny_push)
        """
        ws_paths = payload.get("workspacePaths") or []
        ws_root: Path | None = None
        if ws_paths:
            first_ws = os.path.expanduser(str(ws_paths[0]))
            if os.path.isabs(first_ws):
                ws_root = Path(first_ws).resolve()

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

    def parse(self, payload: dict[str, Any]) -> Request:
        """Converte payload do Antigravity em um Request agnóstico."""
        if not isinstance(payload, dict):
            raise ValueError("Invalid hook payload: expected JSON object.")

        tc = payload.get("toolCall")
        if not isinstance(tc, dict):
            raise ValueError("Invalid toolCall format: expected JSON object.")

        tool_name = str(tc.get("name", "")).strip()
        if not tool_name:
            raise ValueError("Nenhuma ferramenta identificável no payload do hook.")

        args = tc.get("args")
        if args is not None and not isinstance(args, dict):
            raise ValueError("Invalid toolCall.args format: expected JSON object.")
        args = args or {}

        target_dir, explicit_env, force_deny_push = self.resolve_target(payload)

        if tool_name in self.TERMINAL_TOOLS:
            cmd_line = str(args.get("CommandLine", ""))
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
            target_file = str(args.get("TargetFile", "")).strip()
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
        Renderiza resposta JSON para a IDE Antigravity.
        - Converte 'ask' para 'deny' pois ask não suspende execução no Antigravity.
        - Sempre retorna exit code 0 para que a IDE processe o JSON e bloqueie a ferramenta.
        """
        dec_val = decision.decision
        reason_val = decision.reason

        if dec_val == "ask":
            dec_val = "deny"
            suffix = "[CEH CONTEXT LOCK] Decisão 'ask' convertida para 'deny': ask não suspende a execução neste host (H1, Handoff 006)."
            reason_val = f"{reason_val}\n{suffix}" if reason_val else suffix

        res: dict[str, Any] = {"decision": dec_val}
        if reason_val:
            res["reason"] = reason_val

        return res, 0

    def render_error(self, message: str, payload: dict[str, Any] | None = None) -> tuple[dict[str, Any], int]:
        """Renderiza erro crítico/exceção como deny com exit 0."""
        prefix = "" if message.startswith("[CEH") else "[CEH SAFETY GATE ERROR] "
        return {
            "decision": "deny",
            "reason": f"{prefix}{message}"
        }, 0
