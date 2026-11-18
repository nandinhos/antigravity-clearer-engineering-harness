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
from ceh_core.environment import find_repo_root
from ceh_core.git_invocation import resolve_git_invocation
from ceh_core.lexer import split_shell_pipeline


class AntigravityAdapter(HostAdapter):
    """Adaptador de integração para Google Antigravity (IDE e CLI)."""

    TERMINAL_TOOLS = {"run_command"}
    FILE_WRITE_TOOLS = {
        "write_to_file",
        "replace_file_content",
        "multi_replace_file_content",
        "write_file",
        "edit_file",
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
        from_payload_cwd = False
        if raw_cwd is None and ws_root is not None:
            raw_cwd = str(ws_root)
        if raw_cwd is None:
            payload_cwd = payload.get("cwd")
            if isinstance(payload_cwd, str) and payload_cwd.strip():
                expanded_payload_cwd = os.path.expanduser(payload_cwd.strip())
                if os.path.isabs(expanded_payload_cwd):
                    raw_cwd = payload_cwd.strip()
                    from_payload_cwd = True

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

        if from_payload_cwd and find_repo_root(resolved) is None:
            return resolved, None, True

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

            effective_cwd = target_dir
            effective_env = explicit_env
            if force_deny_push:
                probe_base = target_dir if target_dir is not None else Path("/__ceh_unresolved_cwd__")
                segments, split_err = split_shell_pipeline(cmd_line)
                if split_err or segments is None:
                    if re.search(r"\bgit\s+push\b", cmd_line):
                        raise ValueError("[CEH PRE-PUSH CI GATE] ⛔ Push bloqueado: repositório de destino não resolvido a partir do hook.")
                    segments = []
                for seg in segments:
                    is_git, subcmd, _, repo_root, _, git_err = resolve_git_invocation(seg, base_cwd=probe_base)
                    if git_err and re.search(r"\bpush\b", seg):
                        raise ValueError("[CEH PRE-PUSH CI GATE] ⛔ Push bloqueado: repositório de destino não resolvido a partir do hook.")
                    if is_git and subcmd == "push":
                        if repo_root is None or not (repo_root / ".git").exists():
                            raise ValueError("[CEH PRE-PUSH CI GATE] ⛔ Push bloqueado: repositório de destino não resolvido a partir do hook.")
                        effective_cwd = repo_root
                        effective_env = None

            return Request(
                command=cmd_line,
                cwd=effective_cwd,
                explicit_env=effective_env,
            )

        elif tool_name in self.FILE_WRITE_TOOLS:
            target_file = str(args.get("Path") or args.get("TargetFile") or "").strip()
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
            suffix = (
                "[CEH CONTEXT LOCK] Decisão 'ask' convertida para 'deny': ask não suspende a execução neste host (H1, Handoff 006). "
                "AÇÃO REQUERIDA NA IDE/CLI: Utilize a tool 'ask_question' apresentando os 2 Alertas Explícitos de HOMOLOGAÇÃO "
                "(1. Impacto e Blast Radius; 2. Backup Prévio e Rollback Verificado) e forneça o comando exato para execução segura pelo desenvolvedor no terminal."
            )
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
