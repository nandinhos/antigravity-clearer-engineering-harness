"""
normalize.py - Ponto Único de Normalização do CLEARER Engineering Harness (PR-QA-D).

Consolida todas as operações canônicas de normalização de:
- Tokens e aspas (strip_quotes, strip_all_quotes, quote-removal de shell)
- Comandos e decomposição em tokens (normalize_command_for_evaluation, tokenize_command)
- Ambientes e branches (normalize_env, classify_branch_name)
- Caminhos do sistema de arquivos e POSIX (normalize_path, normalize_posix_path, expand_home_prefix)
- Opções longas do Git com resolução por prefixo (resolve_long_options)
"""
from __future__ import annotations

import os
import posixpath
import re
import shlex
from pathlib import Path

# Constantes canônicas de classificação de ambientes
PROD_SEGMENTS = frozenset(["prod", "production", "prd", "live", "preprod"])
STAGING_SEGMENTS = frozenset(["stage", "staging", "homolog", "homologacao", "homologação", "uat", "qa"])


def _get_active_prod_segments() -> frozenset[str] | set[str]:
    """Retorna segmentos de produção ativos, respeitando overrides dinâmicos em environment.py (evals)."""
    try:
        import sys
        env_mod = sys.modules.get("ceh_core.environment")
        if env_mod is not None and hasattr(env_mod, "PROD_SEGMENTS"):
            return env_mod.PROD_SEGMENTS
    except Exception:
        pass
    return PROD_SEGMENTS


def strip_quotes(s: str) -> str:
    """Remove aspas simples ou duplas externas de um token (PR-05 / W1 / PR-QA-D)."""
    s = s.strip()
    if len(s) >= 2 and (
        (s.startswith('"') and s.endswith('"')) or
        (s.startswith("'") and s.endswith("'"))
    ):
        return s[1:-1]
    return s


def strip_all_quotes(s: str) -> str:
    """Remove todas as ocorrências de aspas simples e duplas de um caminho/token."""
    return s.replace('"', "").replace("'", "").strip()


def normalize_command_for_evaluation(subcmd: str) -> str:
    """
    Remove aspas superficiais de palavras de comando (quote-removal) para prevenir evasões
    como p''hp artisan migrate:fresh. Se shlex falhar, retorna o subcomando original.
    """
    try:
        tokens = shlex.split(subcmd, posix=True)
        if tokens:
            return " ".join(tokens)
    except Exception:
        pass
    return subcmd


def tokenize_command(cmd_line: str, posix: bool = True, comments: bool = False) -> list[str]:
    """Tokeniza uma linha de comando via shlex de forma padronizada e segura."""
    if not cmd_line:
        return []
    try:
        return shlex.split(cmd_line, posix=posix, comments=comments)
    except Exception:
        return cmd_line.split()


def normalize_env(val: str) -> str:
    """Normaliza string de ambiente para: 'production', 'staging' ou 'development'."""
    if not val:
        return "development"
    p_segs = _get_active_prod_segments()
    segments = set(s for s in re.split(r'[^\w]+', val.strip().lower()) if s)
    if any(t in segments for t in p_segs):
        return "production"
    if any(t in segments for t in STAGING_SEGMENTS):
        return "staging"
    return "development"


def classify_branch_name(b: str) -> str | None:
    """Classifica se o nome de branch representa ambiente de produção ou staging (AI1)."""
    if not b:
        return None
    cleaned = strip_quotes(b).lower()
    p_segs = _get_active_prod_segments()
    segments = set(s for s in re.split(r'[^\w]+', cleaned) if s)
    if any(s in ("main", "master", "production", "prod") for s in segments) or any(s in p_segs for s in segments):
        return "production"
    if any(s in STAGING_SEGMENTS for s in segments):
        return "staging"
    return None


def expand_home_prefix(target: str, home_dir: str | None = None) -> str:
    """
    Expande prefixos de diretório home (~, ~/, ~root) de forma determinística e segura.
    Não expande til no meio de palavras.
    """
    if not target or not target.startswith("~"):
        return target

    resolved_home = home_dir or str(Path.home())
    if target == "~":
        return resolved_home
    if target.startswith("~/"):
        return resolved_home + target[1:]
    if target == "~root":
        return "/root"
    if target.startswith("~root/"):
        return "/root" + target[5:]

    try:
        return os.path.expanduser(target)
    except Exception:
        return target


def normalize_path(
    path: str | Path,
    cwd: str | Path | None = None,
    resolve_home: bool = True,
    home_dir: str | None = None
) -> str:
    """
    Normaliza caminhos do sistema de arquivos resolvendo barras duplicadas,
    variáveis de ambiente locais comuns (${PWD}, $PWD), til e caminhos relativos ao cwd.
    """
    p_str = str(path).strip()
    if not p_str:
        return ""

    cwd_str = os.path.normpath(str(cwd)) if cwd is not None else str(Path.cwd().resolve())

    # Substituição de $PWD e ${PWD}
    p_str = p_str.replace("${PWD}", cwd_str).replace("$PWD", cwd_str)

    if resolve_home and p_str.startswith("~"):
        p_str = expand_home_prefix(p_str, home_dir=home_dir)

    # Compressão de barras consecutivas
    p_str = re.sub(r"/+", "/", p_str)

    # Resolução de caminho absoluto vs relativo
    if os.path.isabs(p_str):
        return os.path.normpath(p_str)
    return os.path.normpath(os.path.join(cwd_str, p_str))


def normalize_posix_path(path: str) -> str:
    """Normaliza caminhos puramente no formato POSIX (utilizado para git pathspecs e refs)."""
    p_str = str(path).strip()
    if not p_str:
        return ""
    p_str = re.sub(r"/+", "/", p_str)
    return posixpath.normpath(p_str)


def resolve_long_options(token: str, known_options: tuple[str, ...] | list[str]) -> list[str]:
    """
    Resolve opções longas que aceitam abreviação por prefixo (W2 - Git parse-options).
    Regra inegociável: abreviação só pode apertar, nunca relaxar restrições de segurança.
    Retorna a lista de opções conhecidas que iniciam com o token/prefixo.
    """
    if not token.startswith("--"):
        return []
    opt_name = token.split("=")[0]
    return [o for o in known_options if o.startswith(opt_name)]
