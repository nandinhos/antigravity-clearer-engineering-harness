"""ceh_core - Módulos internos reutilizáveis do Safety Gate do CEH."""
from .lexer import resolve_command_head, substitute_positional_args

__all__ = ["resolve_command_head", "substitute_positional_args"]
