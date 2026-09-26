"""
interpreters_extra.py - Avaliação de segurança especializada para PHP, awk, deno e bun (AD4, Handoff 028).
Fornece suporte a código inline, APIs destrutivas de filesystem e desembrulho recursivo de comandos shell.
"""
from __future__ import annotations

import os
import re
import shlex
from pathlib import Path
from typing import Callable, Any

from .rm import is_target_catastrophic

_STR_PAT = r"""(?:"((?:[^"\\]|\\.)*)"|'((?:[^'\\]|\\.)*)')"""
STRING_LITERAL_RE = re.compile(_STR_PAT)

PHP_SHELL_PATTERNS = re.compile(
    r"""(?:\b(?:system|exec|shell_exec|passthru|popen|proc_open)\s*\(\s*""" + _STR_PAT + r"""\s*[\),]|`([^`]+)`)""",
    re.VERBOSE
)

PHP_DESTRUCTIVE_APIS = re.compile(
    r"""\b(unlink|rmdir)\b|array_map\s*\(\s*['"]unlink['"]""",
    re.IGNORECASE
)

AWK_SYSTEM_PATTERNS = re.compile(
    r"""\bsystem\s*\(\s*""" + _STR_PAT + r"""\s*\)""",
    re.VERBOSE
)

AWK_PRINT_PIPE_PATTERNS = re.compile(
    r"""\b(?:print|printf)\b\s*(.+?)\s*\|\s*["'](?:sh|bash|zsh|dash|ksh|ash|fish|csh|tcsh)["']""",
    re.IGNORECASE
)

DENO_DESTRUCTIVE_APIS = re.compile(
    r"""\bDeno\.(remove|removeSync)\b""",
    re.IGNORECASE
)

BUN_DESTRUCTIVE_APIS = re.compile(
    r"""\b(rmSync|rmdirSync|unlinkSync|rm|rmdir|unlink|rimraf)\b"""
)


def _format_env_decision(family: str, desc: str, env: str, env_evidence: str) -> tuple[str, str, str, str]:
    if env == "production":
        reason = (
            f"[CEH PRODUCTION LOCK] Comandos destrutivos são TERMINANTEMENTE PROIBIDOS em PRODUÇÃO "
            f"(Caso de Uso: Sistema de Arquivos (Interpretador de Comandos - {family})): {desc}.\n"
            f"Ambiente detectado: {env.upper()} (Evidência: {env_evidence}).\n"
            f"Execução bloqueada para prevenir perda de dados e indisponibilidade."
        )
        return "deny", reason, env, "FILESYSTEM"
    if env == "staging":
        reason = (
            f"[CEH HOMOLOGAÇÃO / STAGING SAFETY GATE - Caso de Uso: Sistema de Arquivos (Interpretador - {family})]\n"
            f"⚠️ ALERTA 1/2 [IMPACTO DE HOMOLOGAÇÃO]: O comando possui potencial destrutivo/estrutural ({desc}).\n"
            f"   Ambiente detectado: {env.upper()} (Evidência: {env_evidence}).\n"
            f"⚠️ ALERTA 2/2 [BACKUP & ROLLBACK MANDATÓRIOS]: É obrigatório certificar-se de que o comando de BACKUP prévio "
            f"foi executado e que a estratégia de ROLLBACK imediato está disponível e testada antes de prosseguir.\n"
            f"Confirma a execução com rollback assegurado?"
        )
        return "ask", reason, env, "FILESYSTEM"
    reason = (
        f"[CEH DEV PERMITTED - Caso de Uso: Sistema de Arquivos (Interpretador - {family})] "
        f"Comando destrutivo liberado para ambiente de DESENVOLVIMENTO/TESTE ({desc}). "
        f"Ambiente: {env.upper()} (Evidência: {env_evidence}).\n"
        f"Assegure a disponibilidade de backup e rollback para fins de correção."
    )
    return "allow", reason, env, "FILESYSTEM"


def evaluate_php_command(
    tokens: list[str],
    env: str,
    env_evidence: str,
    base_cwd: Path | str | None,
    eval_fn: Callable[..., tuple[str, str, str, str]] | None,
    depth: int = 0
) -> tuple[str, str, str, str] | None:
    code: str | None = None
    extra_args: list[str] = []
    i = 1
    n = len(tokens)
    while i < n:
        tok = tokens[i]
        if tok == "--":
            extra_args = tokens[i + 1:]
            break
        if tok.startswith("-d") or tok.startswith("-c") or tok.startswith("-z"):
            if tok in ("-d", "-c", "-z") and i + 1 < n:
                i += 2
                continue
            i += 1
            continue
        if tok == "-r" and i + 1 < n:
            code = tokens[i + 1]
            extra_args = tokens[i + 2:]
            break
        if tok.startswith("-r") and len(tok) > 2:
            code = tok[2:]
            extra_args = tokens[i + 1:]
            break
        i += 1

    if code is None:
        return None

    if eval_fn is not None:
        for match in PHP_SHELL_PATTERNS.finditer(code):
            for g in match.groups():
                if g is not None:
                    unescaped = g.replace('\\"', '"').replace("\\'", "'").replace("\\\\", "\\")
                    sub_res = eval_fn(unescaped, explicit_env=env, base_cwd=base_cwd, depth=depth + 1)
                    if sub_res[3] == "CATASTROPHIC":
                        return sub_res
                    if sub_res[0] in ("deny", "ask"):
                        return sub_res

    for arg in extra_args:
        is_cat, cat_desc = is_target_catastrophic(arg, base_cwd)
        if is_cat:
            return "deny", f"[CEH CATASTROPHIC BLOCK] Hard block: {cat_desc}", env, "CATASTROPHIC"

    if not PHP_DESTRUCTIVE_APIS.search(code):
        return None

    for match in STRING_LITERAL_RE.finditer(code):
        raw_val = match.group(1) if match.group(1) is not None else match.group(2)
        if raw_val is not None:
            literal = raw_val.replace('\\"', '"').replace("\\'", "'").replace("\\\\", "\\").strip()
            is_cat, cat_desc = is_target_catastrophic(literal, base_cwd)
            if is_cat:
                return "deny", f"[CEH CATASTROPHIC BLOCK] Hard block: {cat_desc}", env, "CATASTROPHIC"

    return _format_env_decision("PHP", "script inline destrutivo (php -r)", env, env_evidence)


def evaluate_awk_command(
    tokens: list[str],
    env: str,
    env_evidence: str,
    base_cwd: Path | str | None,
    eval_fn: Callable[..., tuple[str, str, str, str]] | None,
    depth: int = 0
) -> tuple[str, str, str, str] | None:
    i = 1
    n = len(tokens)
    prog: str | None = None
    while i < n:
        tok = tokens[i]
        if tok == "--":
            if i + 1 < n:
                prog = tokens[i + 1]
            break
        if tok in ("-f", "--file"):
            return None
        if tok.startswith("-f") or tok.startswith("--file="):
            return None
        if tok in ("-F", "-v", "-W") and i + 1 < n:
            i += 2
            continue
        if tok.startswith("-"):
            i += 1
            continue
        prog = tok
        break

    if prog is None:
        return None

    if eval_fn is not None:
        for match in AWK_SYSTEM_PATTERNS.finditer(prog):
            for g in match.groups():
                if g is not None:
                    unescaped = g.replace('\\"', '"').replace("\\'", "'").replace("\\\\", "\\")
                    sub_res = eval_fn(unescaped, explicit_env=env, base_cwd=base_cwd, depth=depth + 1)
                    if sub_res[3] == "CATASTROPHIC" or sub_res[0] in ("deny", "ask"):
                        return sub_res

        for match in AWK_PRINT_PIPE_PATTERNS.finditer(prog):
            expr = match.group(1)
            for s_match in STRING_LITERAL_RE.finditer(expr):
                raw_val = s_match.group(1) if s_match.group(1) is not None else s_match.group(2)
                if raw_val is not None:
                    unescaped = raw_val.replace('\\"', '"').replace("\\'", "'").replace("\\\\", "\\")
                    sub_res = eval_fn(unescaped, explicit_env=env, base_cwd=base_cwd, depth=depth + 1)
                    if sub_res[3] == "CATASTROPHIC" or sub_res[0] in ("deny", "ask"):
                        return sub_res

    return None


def evaluate_deno_bun_command(
    tokens: list[str],
    family: str,
    env: str,
    env_evidence: str,
    base_cwd: Path | str | None,
    eval_fn: Callable[..., tuple[str, str, str, str]] | None,
    depth: int = 0
) -> tuple[str, str, str, str] | None:
    code: str | None = None
    extra_args: list[str] = []
    i = 1
    n = len(tokens)

    if family == "deno":
        while i < n:
            tok = tokens[i]
            if tok == "eval":
                j = i + 1
                while j < n:
                    if tokens[j].startswith("-"):
                        j += 1
                        continue
                    code = tokens[j]
                    extra_args = tokens[j + 1:]
                    break
                break
            i += 1
    elif family == "bun":
        while i < n:
            tok = tokens[i]
            if tok in ("-e", "--eval") and i + 1 < n:
                code = tokens[i + 1]
                extra_args = tokens[i + 2:]
                break
            if tok.startswith(("-e=", "--eval=")):
                code = tok.split("=", 1)[1]
                extra_args = tokens[i + 1:]
                break
            if tok.startswith("-e") and len(tok) > 2:
                code = tok[2:]
                extra_args = tokens[i + 1:]
                break
            i += 1

    if code is None:
        return None

    pattern = DENO_DESTRUCTIVE_APIS if family == "deno" else BUN_DESTRUCTIVE_APIS
    if not pattern.search(code):
        return None

    for match in STRING_LITERAL_RE.finditer(code):
        raw_val = match.group(1) if match.group(1) is not None else match.group(2)
        if raw_val is not None:
            literal = raw_val.replace('\\"', '"').replace("\\'", "'").replace("\\\\", "\\").strip()
            is_cat, cat_desc = is_target_catastrophic(literal, base_cwd)
            if is_cat:
                return "deny", f"[CEH CATASTROPHIC BLOCK] Hard block: {cat_desc}", env, "CATASTROPHIC"

    for arg in extra_args:
        is_cat, cat_desc = is_target_catastrophic(arg, base_cwd)
        if is_cat:
            return "deny", f"[CEH CATASTROPHIC BLOCK] Hard block: {cat_desc}", env, "CATASTROPHIC"

    desc = f"script inline destrutivo ({family})"
    return _format_env_decision(family.upper(), desc, env, env_evidence)
