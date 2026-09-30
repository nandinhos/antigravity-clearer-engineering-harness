#!/usr/bin/env python3
# ==============================================================================
# fallback.py — Host-Specific Fallback Hook Responder (PR-16 / BI1)
# ==============================================================================
"""
Fallback deterministico de resposta de reserva do Safety Gate por host.
Utiliza estritamente a biblioteca padrao do Python (stdlib-only).
Avalia o payload bruto sem depender do motor (ceh_core) nem dos adaptadores.

Ordem estrita de avaliacao:
1. Tem 'toolCall' -> Antigravity: {"decision": "deny", ...}, exit 0
2. Tem 'model_provider' ou 'turn_id' -> Muse: {"decision": "block", ...}, exit 0
3. Tem 'hook_event_name' ou 'tool_name' -> Claude: hookSpecificOutput (deny), exit 2
4. Vazio, nao-JSON, nao-objeto ou sem marcador -> regra generica do ambiente
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any, Tuple

DEFAULT_FAIL_CLOSED_REASON = (
    "[CEH SAFETY GATE ERROR] Falha interna ou erro crítico de segurança. "
    "Execução bloqueada (fail-closed)."
)


def get_fallback_response(raw_input: str, reason: str | None = None) -> Tuple[dict[str, Any], int]:
    """
    Retorna o dicionario de resposta e o exit code correspondente ao formato
    observado de cada host, avaliando marcadores na ordem estrita de precedencia.
    """
    effective_reason = reason or DEFAULT_FAIL_CLOSED_REASON

    payload: Any = None
    if raw_input and isinstance(raw_input, str):
        try:
            payload = json.loads(raw_input)
        except Exception:
            payload = None

    if isinstance(payload, dict):
        # 1. Antigravity (E5, E13): exclusivo 'toolCall'
        if "toolCall" in payload:
            return {
                "decision": "deny",
                "reason": effective_reason,
            }, 0

        # 2. Muse (E1b B4, E1c): marcadores observados 'model_provider' ou 'turn_id'
        if "model_provider" in payload or "turn_id" in payload:
            return {
                "decision": "block",
                "reason": effective_reason,
            }, 0

        # 3. Claude Code (E5, E9): 'hook_event_name' ou 'tool_name'
        if "hook_event_name" in payload or "tool_name" in payload:
            return {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": effective_reason,
                }
            }, 2

    # 4. Vazio, nao-JSON, nao-objeto ou sem marcador: fallback generico
    is_claude_env = any(k in os.environ for k in ("CLAUDECODE", "CLAUDE_PROJECT_DIR", "CLAUDE_PID"))
    exit_code = 2 if is_claude_env else 0
    return {
        "decision": "deny",
        "reason": effective_reason,
    }, exit_code


def respond(raw_input: str, reason: str | None = None) -> None:
    """Emite a resposta JSON do fallback no stdout e finaliza o processo com o exit code apropriado."""
    resp_dict, exit_code = get_fallback_response(raw_input, reason)
    print(json.dumps(resp_dict, ensure_ascii=False))
    sys.exit(exit_code)
