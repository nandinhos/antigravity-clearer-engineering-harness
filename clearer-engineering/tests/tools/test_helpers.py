"""
test_helpers.py — Funções auxiliares herméticas para os testes do CEH.
Garante que diretórios temporários criados em testes sejam resolvidos fisicamente
(evitando divergências de symlinks como /var -> /private/var no macOS).
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path


def mkdtemp_resolved(prefix: str = "ceh_tmp_", **kwargs) -> Path:
    """Cria e retorna um diretório temporário com caminho absoluto resolvido (canonical realpath)."""
    raw_path = tempfile.mkdtemp(prefix=prefix, **kwargs)
    return Path(raw_path).resolve()
