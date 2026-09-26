"""
find.py - Análise por tokens e avaliação de segurança de comandos 'find' do CEH (G5, PR-06).
Analisa tokens estruturalmente sem introduzir regex em rules.py.
"""
from __future__ import annotations

import os
import shlex
from pathlib import Path

from .rm import is_target_catastrophic


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


def parse_find_tokens(tokens: list[str]) -> tuple[list[str], bool, str]:
    """
    Decompõe argumentos de 'find' em (paths, is_destructive, action_desc).
    """
    paths: list[str] = []
    is_destructive = False
    action_desc = ""

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
                if cmd_base in DESTRUCTIVE_CMDS:
                    is_destructive = True
                    action_desc = f"{exec_flag} {cmd_base}"
                elif cmd_base in SHELL_CMDS:
                    for idx, s_arg in enumerate(exec_args[1:], start=1):
                        if s_arg == "-c" and idx + 1 < len(exec_args):
                            script = exec_args[idx + 1]
                            try:
                                s_tokens = shlex.split(script, posix=True)
                                if any(os.path.basename(t) in DESTRUCTIVE_CMDS for t in s_tokens):
                                    is_destructive = True
                                    action_desc = f"{exec_flag} {cmd_base} -c {s_tokens[0]}"
                            except Exception:
                                pass
            continue

        i += 1

    return paths, is_destructive, action_desc


def evaluate_find_command(
    cmd_line: str,
    env: str,
    env_evidence: str = "",
    base_cwd: Path | str | None = None
) -> tuple[str, str, str, str] | None:
    """Avalia a segurança de comandos 'find' por tokens."""
    try:
        tokens = shlex.split(cmd_line, posix=True)
    except Exception:
        return None

    if not tokens:
        return None

    idx = 0
    while idx < len(tokens):
        tok = tokens[idx]
        if tok in ("sudo", "rtk", "command"):
            idx += 1
            continue
        if tok == "env":
            idx += 1
            while idx < len(tokens) and ("=" in tokens[idx] or tokens[idx].startswith("-")):
                idx += 1
            continue
        break

    if idx >= len(tokens):
        return None

    cmd_base = os.path.basename(tokens[idx])
    if cmd_base != "find":
        return None

    find_tokens = [tokens[idx]] + tokens[idx + 1:]
    paths, is_destructive, action_desc = parse_find_tokens(find_tokens)

    if not is_destructive:
        return None

    for p in paths:
        if is_cwd_subpath(p, base_cwd):
            continue
        is_cat, cat_desc = is_target_catastrophic(p, base_cwd)
        if is_cat:
            return "deny", f"[CEH CATASTROPHIC BLOCK] Hard block: {cat_desc}", env, "CATASTROPHIC"

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
