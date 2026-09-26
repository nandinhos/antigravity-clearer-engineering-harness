"""
find.py - Análise por tokens e avaliação de segurança de comandos 'find' do CEH (G5, PR-06/PR-06b).
Analisa tokens estruturalmente com desembrulho recursivo e sem introduzir regex em rules.py.
"""
from __future__ import annotations

import os
import shlex
from pathlib import Path
from typing import Callable, Any

from .rm import is_target_catastrophic
from .lexer import resolve_command_head


EXEC_FLAGS = {"-exec", "-execdir", "-ok", "-okdir"}
DESTRUCTIVE_CMDS = {"rm", "unlink", "shred", "rmdir"}
SHELL_CMDS = {"sh", "bash", "zsh", "dash"}


def is_cwd_subpath(target: str, cwd: Path | str | None = None) -> bool:
    """Verifica se o alvo é o próprio diretório de trabalho atual (cwd)."""
    t = target.replace('"', "").replace("'", "").strip()
    if t in (".", "./", ".//", ""):
        return True
    cwd_path = Path.cwd().resolve() if cwd is None else Path(cwd).resolve()
    cwd_str = str(cwd_path)
    if ".." in t.split(os.sep) or t.startswith("/") or t.startswith("~"):
        return False
    norm = os.path.normpath(os.path.join(cwd_str, t))
    return norm == cwd_str


def parse_find_tokens(
    tokens: list[str],
    env: str,
    base_cwd: Path | str | None = None,
    eval_fn: Callable[..., tuple[str, str, str, str]] | None = None,
    depth: int = 0
) -> tuple[list[str], bool, str, tuple[str, str, str, str] | None]:
    """
    Decompõe argumentos de 'find' em:
    (paths, is_destructive, action_desc, worst_subcmd_decision)
    """
    paths: list[str] = []
    is_destructive = False
    action_desc = ""
    worst_subcmd_decision: tuple[str, str, str, str] | None = None

    i = 1
    n = len(tokens)

    # Pula opções globais de find antes dos caminhos
    while i < n:
        tok = tokens[i]
        if tok in ("-H", "-L", "-P"):
            i += 1
            continue
        if tok in ("-D", "-O") and i + 1 < n:
            i += 2
            continue
        if tok.startswith("-O"):
            i += 1
            continue
        break

    # Coleta de caminhos: tudo antes do primeiro operador/expressão (-..., (, ), !)
    while i < n:
        tok = tokens[i]
        if tok.startswith("-") or tok in ("(", ")", "!"):
            break
        paths.append(tok)
        i += 1

    if not paths:
        paths = ["."]

    # Análise de expressões procurando ações destrutivas
    while i < n:
        tok = tokens[i]
        if tok == "-delete":
            is_destructive = True
            action_desc = "-delete"
            i += 1
            continue

        if tok in EXEC_FLAGS:
            exec_flag = tok
            i += 1
            exec_args: list[str] = []
            while i < n:
                arg = tokens[i]
                if arg in (";", "\\;", "+"):
                    i += 1
                    break
                exec_args.append(arg)
                i += 1

            if exec_args:
                cmd_raw = exec_args[0]
                cmd_base = os.path.basename(cmd_raw)
                if cmd_base in DESTRUCTIVE_CMDS or cmd_base in SHELL_CMDS:
                    is_destructive = True
                    action_desc = f"{exec_flag} {cmd_base}"

                # Desembrulho recursivo com o gate inteiro (AA1 e AA2)
                if eval_fn is not None:
                    # Substitui {} por um placeholder inócuo
                    norm_args = ["safe_placeholder.tmp" if a == "{}" else a for a in exec_args]
                    sub_cmd_str = " ".join(shlex.quote(a) for a in norm_args)
                    sub_res = eval_fn(sub_cmd_str, explicit_env=env, base_cwd=base_cwd, depth=depth + 1)
                    dec, _, _, uc = sub_res
                    if uc == "CATASTROPHIC" or dec in ("deny", "ask"):
                        is_destructive = True
                        worst_subcmd_decision = sub_res
            continue

        i += 1

    return paths, is_destructive, action_desc, worst_subcmd_decision


def evaluate_find_command(
    cmd_line: str,
    env: str,
    env_evidence: str = "",
    base_cwd: Path | str | None = None,
    eval_fn: Callable[..., tuple[str, str, str, str]] | None = None,
    depth: int = 0
) -> tuple[str, str, str, str] | None:
    """Avalia a segurança de comandos 'find' por tokens."""
    try:
        tokens = shlex.split(cmd_line, posix=True)
    except Exception:
        return None

    if not tokens:
        return None

    idx, _ = resolve_command_head(tokens)
    if idx >= len(tokens):
        return None

    cmd_base = os.path.basename(tokens[idx])
    if cmd_base != "find":
        return None

    find_tokens = [tokens[idx]] + tokens[idx + 1:]
    paths, is_destructive, action_desc, sub_res = parse_find_tokens(
        find_tokens, env=env, base_cwd=base_cwd, eval_fn=eval_fn, depth=depth
    )

    # Se um subcomando executado pelo -exec resultou em CATASTROPHIC, bloqueia imediatamente
    if sub_res is not None and sub_res[3] == "CATASTROPHIC":
        return sub_res

    if not is_destructive:
        return None

    # Verifica se algum caminho inicial do find é catastrófico
    for p in paths:
        if is_cwd_subpath(p, base_cwd):
            continue
        is_cat, cat_desc = is_target_catastrophic(p, base_cwd)
        if is_cat:
            return "deny", f"[CEH CATASTROPHIC BLOCK] Hard block: {cat_desc}", env, "CATASTROPHIC"

    # Se o subcomando executado pelo -exec tiver restrição em prod/staging
    if sub_res is not None and sub_res[0] in ("deny", "ask"):
        if env in ("production", "staging"):
            return sub_res

    desc = f"find com ação destrutiva ({action_desc})"
    if env == "production":
        reason = (
            f"[CEH PRODUCTION LOCK] Comandos destrutivos são TERMINANTEMENTE PROIBIDOS em PRODUÇÃO "
            f"(Caso de Uso: Sistema de Arquivos (Deleção Indireta com find)): {desc}.\n"
            f"Ambiente detectado: {env.upper()} (Evidência: {env_evidence}).\n"
            f"Execução bloqueada para prevenir perda de dados e indisponibilidade."
        )
        return "deny", reason, env, "FILESYSTEM"

    if env == "staging":
        reason = (
            f"[CEH HOMOLOGAÇÃO / STAGING SAFETY GATE - Caso de Uso: Sistema de Arquivos (Deleção Indireta com find)]\n"
            f"⚠️ ALERTA 1/2 [IMPACTO DE HOMOLOGAÇÃO]: O comando possui potencial destrutivo/estrutural ({desc}).\n"
            f"   Ambiente detectado: {env.upper()} (Evidência: {env_evidence}).\n"
            f"⚠️ ALERTA 2/2 [BACKUP & ROLLBACK MANDATÓRIOS]: É obrigatório certificar-se de que o comando de BACKUP prévio "
            f"foi executado e que a estratégia de ROLLBACK imediato está disponível e testada antes de prosseguir.\n"
            f"Confirma a execução com rollback assegurado?"
        )
        return "ask", reason, env, "FILESYSTEM"

    reason = (
        f"[CEH DEV PERMITTED - Caso de Uso: Sistema de Arquivos (Deleção Indireta com find)] "
        f"Comando destrutivo liberado para ambiente de DESENVOLVIMENTO/TESTE ({desc}). "
        f"Ambiente: {env.upper()} (Evidência: {env_evidence}).\n"
        f"Assegure a disponibilidade de backup e rollback para fins de correção."
    )
    return "allow", reason, env, "FILESYSTEM"
