#!/usr/bin/env python3
# ==============================================================================
# base.py — Host Adapter Contract (PR-14/15)
# ==============================================================================
"""
Abstract contract for host-specific hook adapters.
Each host (Google Antigravity, Claude Code, Muse) implements detect, parse, and render.
Isolates host-specific schemas and exit codes from the agnostic CEH core engine.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
from pathlib import Path

from ceh_core.engine import Request, Decision


class HostAdapter(ABC):
    """Contrato abstrato de adaptador de host sob o protocolo CLEARER."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Nome canônico do host (ex: 'antigravity', 'claude_code', 'muse')."""
        ...

    @abstractmethod
    def detect(self, payload: Any) -> bool:
        """
        Retorna True se o payload pertence a este host.
        A detecção deve ser puramente baseada no payload sempre que possível.
        """
        ...

    @abstractmethod
    def parse(self, payload: dict[str, Any]) -> Request:
        """
        Converte o payload de hook específico do host em um objeto Request do CEH Core.
        Lança ValueError em caso de payload estruturalmente inválido ou ferramenta desconhecida.
        """
        ...

    @abstractmethod
    def resolve_target(self, payload: dict[str, Any]) -> tuple[Path | None, str | None, bool]:
        """
        Resolve o diretório alvo de execução a partir do payload do host.
        Retorna: (target_path, explicit_env, force_deny_push)
        """
        ...

    @abstractmethod
    def render(self, decision: Decision, payload: dict[str, Any] | None = None) -> tuple[dict[str, Any], int]:
        """
        Converte a decisão agnóstica do CEH Core no formato de resposta e código de saída exigidos pelo host.
        Retorna: (response_dict, exit_code)
        """
        ...

    @abstractmethod
    def render_error(self, message: str, payload: dict[str, Any] | None = None) -> tuple[dict[str, Any], int]:
        """
        Renderiza uma resposta de negação/erro em formato nativo do host com código de saída de segurança.
        Retorna: (response_dict, exit_code)
        """
        ...
