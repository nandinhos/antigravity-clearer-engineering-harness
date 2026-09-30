#!/usr/bin/env python3
# ==============================================================================
# muse.py — Muse Host Adapter (PR-15b)
# ==============================================================================
"""
Adapter for Muse (PreToolUse Hook).
Detects Muse-specific payloads from recorded probe evidence (E1/E1b),
parses bash / write_file / edit_file / submit_reminder_decision tools,
and renders native responses: {} for allow, {"decision": "block"} for block/deny, always with exit code 0.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from adapters.base import HostAdapter
from ceh_core.engine import Request, Decision


class MuseAdapter(HostAdapter):
    """Adaptador de integração para Muse a partir do contrato observado no E1/E1b."""

    TERMINAL_TOOLS = {"bash"}
    FILE_WRITE_TOOLS = {"write_file", "edit_file"}
    INTERNAL_ALLOW_TOOLS = {"submit_reminder_decision"}
    SUPPORTED_TOOLS = TERMINAL_TOOLS | FILE_WRITE_TOOLS | INTERNAL_ALLOW_TOOLS

    @property
    def name(self) -> str:
        return "muse"

    def detect(self, payload: Any) -> bool:
        """
        Detecta payload emitido pelo Muse sem ambiguidade contra Antigravity e Claude Code.
        Critério 1: Rejeita payloads com toolCall (exclusivo do Antigravity).
        Critério 2: Presença de marcadores exclusivos observados no E1/E1b ('model_provider', 'turn_id').
        Critério 3: Nomes de ferramentas exclusivos em minúsculas ('bash', 'write_file', etc.).
        """
        if not isinstance(payload, dict):
            return False
        if "toolCall" in payload:
            return False
        if "model_provider" in payload or "turn_id" in payload:
            return True
        tool_name = str(payload.get("tool_name", "")).strip()
        if tool_name in self.SUPPORTED_TOOLS:
            return True
        return False

    def resolve_target(self, payload: dict[str, Any]) -> tuple[Path | None, str | None, bool]:
        """
        Resolve o diretório de trabalho a partir de tool_input.workdir ou payload.cwd.
        Retorna: (target_path, explicit_env, force_deny_push)
        """
        ti = payload.get("tool_input")
        if ti is not None and not isinstance(ti, dict):
            raise ValueError("Invalid tool_input format: expected JSON object.")

        raw_cwd = (ti or {}).get("workdir") or payload.get("cwd")
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
        """Converte payload do Muse em um Request agnóstico do CEH Core."""
        if not isinstance(payload, dict):
            raise ValueError("Invalid hook payload: expected JSON object.")

        tool_name = str(payload.get("tool_name", "")).strip()
        if not tool_name:
            raise ValueError("Nenhuma ferramenta identificável no payload do hook.")

        if tool_name not in self.SUPPORTED_TOOLS:
            raise ValueError(f"[CEH HOOK ERROR] Ferramenta desconhecida '{tool_name}': fail-closed ativado.")

        ti = payload.get("tool_input")
        if ti is not None and not isinstance(ti, dict):
            raise ValueError("Invalid tool_input format: expected JSON object.")
        ti = ti or {}

        target_dir, explicit_env, force_deny_push = self.resolve_target(payload)

        if tool_name in self.INTERNAL_ALLOW_TOOLS:
            # submit_reminder_decision é ferramenta interna do Muse sem comando nem escrita.
            # Decisão explícita e justificada: avaliada como allow com comando vazio.
            return Request(
                command="",
                cwd=target_dir,
                explicit_env=explicit_env,
            )

        if tool_name in self.TERMINAL_TOOLS:
            cmd_line = str(ti.get("command") or "")
            if not cmd_line.strip():
                raise ValueError(f"Comando vazio ou ausente para ferramenta de terminal '{tool_name}'.")

            if force_deny_push and bool(re.search(r"\bgit\s+push\b", cmd_line)):
                raise ValueError("[CEH PRE-PUSH CI GATE] ⛔ Push bloqueado: repositório de destino não resolvido a partir do hook.")

            return Request(
                command=cmd_line,
                cwd=target_dir,
                explicit_env=explicit_env,
            )

        if tool_name in self.FILE_WRITE_TOOLS:
            target_file = str(ti.get("path") or "").strip()
            if not target_file:
                raise ValueError(f"Caminho do arquivo ausente na ferramenta de escrita '{tool_name}'.")

            return Request(
                command="",
                cwd=target_dir,
                explicit_env=explicit_env,
                target_paths=[target_file],
            )

        raise ValueError(f"[CEH HOOK ERROR] Ferramenta desconhecida '{tool_name}': fail-closed ativado.")

    def render(self, decision: Decision, payload: dict[str, Any] | None = None) -> tuple[dict[str, Any], int]:
        """
        Renderiza resposta nativa para o Muse conforme observado no E1b:
        - permitida: {} (JSON vazio) com exit 0
        - bloqueada / ask: {"decision": "block", "reason": reason} com exit 0
        """
        if decision.decision == "allow":
            return {}, 0

        # No Muse (E1b B4/B6), tanto deny quanto ask bloqueiam com {"decision": "block"} e exit 0
        return {
            "decision": "block",
            "reason": decision.reason,
        }, 0

    def render_error(self, message: str, payload: dict[str, Any] | None = None) -> tuple[dict[str, Any], int]:
        """Renderiza erro de hook em formato nativo de bloqueio com exit 0."""
        return {
            "decision": "block",
            "reason": message,
        }, 0
