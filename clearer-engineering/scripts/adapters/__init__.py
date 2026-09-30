#!/usr/bin/env python3
# ==============================================================================
# adapters/__init__.py — Host Adapters Package (PR-14/15)
# ==============================================================================
"""Package containing host-specific hook adapters for CEH."""

from adapters.base import HostAdapter
from adapters.antigravity import AntigravityAdapter
from adapters.claude_code import ClaudeCodeAdapter
from adapters.muse import MuseAdapter

__all__ = [
    "HostAdapter",
    "AntigravityAdapter",
    "ClaudeCodeAdapter",
    "MuseAdapter",
]
