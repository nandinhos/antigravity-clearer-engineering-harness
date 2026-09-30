#!/usr/bin/env python3
# ==============================================================================
# hook_context.py — PreToolUse Hook Context & Host Dispatcher (PR-14/15)
# ==============================================================================
"""
Agnostic hook context dispatcher for PreToolUse hooks.
Dispatches hook payloads to host-specific adapters (Antigravity, Claude Code)
in explicit order. Isolates all host-specific payload schemas and exit codes into adapters/.
Zero host coupling terms allowed in this module (PR-14/15).
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Callable

from adapters.base import HostAdapter
from adapters.antigravity import AntigravityAdapter
from adapters.claude_code import ClaudeCodeAdapter
from ceh_core.engine import Request, Decision

# Ordem explícita de resolução de adaptadores de host.
# Observação arquitetural: o PR-15b inserirá o MuseAdapter antes do ClaudeCodeAdapter (Handoff 068, §4).
ADAPTERS: list[HostAdapter] = [
    AntigravityAdapter(),
    ClaudeCodeAdapter(),
]


def find_adapter(payload: Any) -> HostAdapter | None:
    """Retorna o primeiro adaptador da lista ordenada que reconhecer o payload."""
    for adapter in ADAPTERS:
        if adapter.detect(payload):
            return adapter
    return None


def _fallback_exit_code() -> int:
    """Fallback determinístico de código de saída na ausência de payload/adaptador reconhecido."""
    is_claude_env = any(k in os.environ for k in ("CLAUDECODE", "CLAUDE_PROJECT_DIR", "CLAUDE_PID"))
    return 2 if is_claude_env else 0


def get_exit_code(decision: str, payload: Any = None) -> int:
    """
    Retorna o código de saída padronizado para o host:
    - Se houver adaptador reconhecido, consulta sua renderização.
    - Caso contrário, adota fallback determinístico (exit 2 para Claude, exit 0 para Antigravity).
    """
    adapter = find_adapter(payload)
    if adapter is not None:
        dec_obj = Decision(decision=decision, reason="")
        _, exit_code = adapter.render(dec_obj, payload if isinstance(payload, dict) else None)
        return exit_code

    if decision == "deny":
        return _fallback_exit_code()
    return 0


def resolve_hook_target(payload: dict[str, Any]) -> tuple[Path | None, str | None, bool]:
    """
    Delega a resolução do diretório alvo ao adaptador correspondente.
    Retorna: (target_path, explicit_env, force_deny_push)
    """
    adapter = find_adapter(payload)
    if adapter is not None:
        return adapter.resolve_target(payload)
    return None, "production", True


def format_host_response(payload: dict[str, Any], decision: str, reason: str = "") -> dict[str, Any]:
    """Formata a resposta do host via adaptador detectado."""
    adapter = find_adapter(payload)
    dec_obj = Decision(decision=decision, reason=reason)
    if adapter is not None:
        return adapter.render(dec_obj, payload)[0]
    res: dict[str, Any] = {"decision": decision}
    if reason:
        res["reason"] = reason
    return res


def _invoke_engine_eval(engine_eval_fn: Callable[..., Any], req: Request) -> Decision:
    """Executa a função de avaliação do motor (suporta evaluate(Request) ou evaluate_command)."""
    if req.target_paths:
        from ceh_core.engine import evaluate as core_evaluate
        return core_evaluate(req)

    try:
        res = engine_eval_fn(req)
    except TypeError:
        res = engine_eval_fn(req.command, explicit_env=req.explicit_env, base_cwd=req.cwd)

    if isinstance(res, Decision):
        return res
    if isinstance(res, tuple):
        dec_val = res[0]
        reason_val = res[1] if len(res) > 1 else ""
        return Decision(decision=dec_val, reason=reason_val)
    return Decision(decision=getattr(res, "decision", "allow"), reason=getattr(res, "reason", ""))


def evaluate_hook_payload(
    payload: dict[str, Any],
    engine_eval_fn: Callable[[Request], Decision],
) -> dict[str, Any]:
    """
    Avalia payload de hook através do adaptador de host e do motor agnóstico CEH Core.
    Retorna a resposta renderizada nativa do host (dicionário).
    """
    if not isinstance(payload, dict):
        raise ValueError("Invalid hook payload: expected JSON object.")

    adapter = find_adapter(payload)
    if adapter is None:
        return {
            "decision": "deny",
            "reason": "[CEH HOOK ERROR] Nenhuma ferramenta identificável no payload do hook."
        }

    try:
        req = adapter.parse(payload)
    except ValueError as ve:
        return adapter.render_error(str(ve), payload)[0]
    except Exception as e:
        return adapter.render_error(f"Falha ao avaliar payload do hook: {str(e)}", payload)[0]

    original_cwd = os.getcwd()
    try:
        if req.cwd is not None:
            os.chdir(req.cwd)

        dec = _invoke_engine_eval(engine_eval_fn, req)
        return adapter.render(dec, payload)[0]
    finally:
        try:
            os.chdir(original_cwd)
        except OSError:
            pass


def handle_hook_lifecycle(
    raw_input: str,
    engine_eval_fn: Callable[[Request], Decision]
) -> tuple[dict[str, Any], int]:
    """
    Ciclo de vida completo do hook a partir de string bruta do stdin:
    1. Parse e validação do JSON (fail-closed com fallback seguro).
    2. Identificação do adaptador do host em ordem explícita.
    3. Conversão de payload em Request agnóstico via adapter.parse().
    4. Execução protegida sob chdir com avaliação contra o motor CEH Core.
    5. Renderização nativa da decisão e código de saída via adapter.render().
    Retorna: (response_dict, exit_code)
    """
    if not raw_input.strip():
        resp = {
            "decision": "deny",
            "reason": "[CEH SAFETY GATE ERROR] Payload vazio recebido no hook."
        }
        return resp, _fallback_exit_code()

    try:
        payload = json.loads(raw_input)
    except Exception as e:
        resp = {
            "decision": "deny",
            "reason": f"[CEH SAFETY GATE ERROR] Hook execution failed: JSON inválido ({str(e)})"
        }
        return resp, _fallback_exit_code()

    if not isinstance(payload, dict):
        resp = {
            "decision": "deny",
            "reason": "[CEH SAFETY GATE ERROR] Invalid hook payload: expected JSON object."
        }
        return resp, _fallback_exit_code()

    adapter = find_adapter(payload)
    if adapter is None:
        resp = {
            "decision": "deny",
            "reason": "[CEH HOOK ERROR] Nenhuma ferramenta identificável no payload do hook."
        }
        return resp, _fallback_exit_code()

    try:
        req = adapter.parse(payload)
    except ValueError as ve:
        return adapter.render_error(str(ve), payload)
    except Exception as e:
        return adapter.render_error(f"Falha ao avaliar payload do hook: {str(e)}", payload)

    original_cwd = os.getcwd()
    try:
        if req.cwd is not None:
            os.chdir(req.cwd)

        dec = _invoke_engine_eval(engine_eval_fn, req)
        return adapter.render(dec, payload)
    finally:
        try:
            os.chdir(original_cwd)
        except OSError:
            pass
