"""
lexer.py - Analisador léxico e normalizador de pipelines de shell do CEH.
Contém:
- split_shell_pipeline: Decompõe pipelines em comandos atômicos com parser caractere a caractere (FSM).
- normalize_command_for_evaluation: Remove aspas superficiais de comandos (quote-removal).
"""
from __future__ import annotations

import os
import re
import shlex


def split_shell_pipeline(cmd_line: str) -> tuple[list[str] | None, str | None]:
    """
    Decompõe uma linha de comando em subcomandos atômicos, respeitando aspas simples e duplas,
    escapes e operadores de controle de shell (;, &&, ||, |, &).
    Rejeita construções que impeçam inspeção determinística de segurança em Fail-Closed:
    - ANSI-C quoting ($'...') e locale quoting ($"...")
    - Subshells ($(...) ou `...`)
    - Process substitution (<(...) ou >(...))
    - Aspas ou escapes não balanceados
    """
    tokens = []
    buf = []
    i = 0
    n = len(cmd_line)
    quote = None
    escaped = False

    while i < n:
        c = cmd_line[i]
        if escaped:
            buf.append(c)
            escaped = False
            i += 1
            continue

        if c == "\\":
            if quote == "'":  # Em bash, aspas simples não admitem escape
                buf.append(c)
            else:
                # Rejeição Fail-Closed de continuação de linha (\ seguido de newline)
                if i + 1 < n and cmd_line[i+1] in ("\n", "\r"):
                    return None, "Continuação de linha por barra invertida (line continuation) detectada"
                escaped = True
                buf.append(c)
            i += 1
            continue

        if quote:
            if c == quote:
                quote = None
                buf.append(c)
                i += 1
                continue

            # Dentro de aspas duplas, o shell avalia subshells e expansões de parâmetros
            if quote == '"':
                if c == "`":
                    return None, "Backtick subshell (`...`) detectada dentro de aspas duplas"
                if c == "$" and i + 1 < n and cmd_line[i+1] == "(":
                    return None, "Subshell ($(...)) detectada dentro de aspas duplas"
                if c == "$" and i + 1 < n and cmd_line[i+1] == "{":
                    return None, "Expansão de parâmetro (${...}) detectada dentro de aspas duplas"

            buf.append(c)
            i += 1
            continue

        if c in ("'", '"'):
            # Detecta ANSI-C ou locale quoting ($'...' ou $"...")
            if i > 0 and cmd_line[i-1] == "$":
                return None, "ANSI-C ($'...') ou locale ($\"...\") quoting detectado"
            quote = c
            buf.append(c)
            i += 1
            continue

        # Detecta subshells ou substituições de processo fora de aspas
        if c == "`":
            return None, "Backtick subshell (`...`) detectada"
        if c == "$" and i + 1 < n and cmd_line[i+1] == "(":
            return None, "Subshell ($(...)) detectada"
        if c == "$" and i + 1 < n and cmd_line[i+1] == "{":
            return None, "Expansão de parâmetro (${...}) detectada"
        if c in ("<", ">") and i + 1 < n and cmd_line[i+1] == "(":
            return None, "Process substitution (<(...) ou >(...)) detectada"

        # Operadores de controle e terminadores de instrução (;, \n, \r\n)
        if c in (";", "\n", "\r"):
            sub = "".join(buf).strip()
            if sub:
                tokens.append(sub)
            buf = []
            if c == "\r" and i + 1 < n and cmd_line[i+1] == "\n":
                i += 2
            else:
                i += 1
            continue

        if c == "&":
            if i + 1 < n and cmd_line[i+1] == "&":
                sub = "".join(buf).strip()
                if sub:
                    tokens.append(sub)
                buf = []
                i += 2
                continue
            # Verifica se é redirecionamento de descritores: >&, &>, 2>&1, 1>&2
            prev_char = cmd_line[i-1] if i > 0 else ""
            next_char = cmd_line[i+1] if i + 1 < n else ""
            if prev_char == ">" or next_char == ">" or (prev_char in ("1", "2") and i > 1 and cmd_line[i-2] == ">"):
                buf.append(c)
                i += 1
                continue
            # & isolado é separador de comando em background
            sub = "".join(buf).strip()
            if sub:
                tokens.append(sub)
            buf = []
            i += 1
            continue

        if c == "|":
            if i + 1 < n and cmd_line[i+1] == "|":
                sub = "".join(buf).strip()
                if sub:
                    tokens.append(sub)
                buf = []
                i += 2
                continue
            sub = "".join(buf).strip()
            if sub:
                tokens.append(sub)
            buf = []
            i += 1
            continue

        buf.append(c)
        i += 1

    if quote:
        return None, "Aspas não fechadas na linha de comando"
    if escaped:
        return None, "Caractere de escape pendente no final da linha"

    last_sub = "".join(buf).strip()
    if last_sub:
        tokens.append(last_sub)
    return tokens, None


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


def _consume_flags(tokens: list[str], idx: int, arg_opts: set[str]) -> int:
    n = len(tokens)
    while idx < n and tokens[idx].startswith("-"):
        tok = tokens[idx]
        if tok == "--":
            return idx + 1
        if tok in arg_opts and idx + 1 < n:
            idx += 2
        elif any(tok.startswith(opt + "=") for opt in arg_opts):
            idx += 1
        else:
            idx += 1
    return idx


def resolve_command_head(tokens: list[str]) -> tuple[int, str | None]:
    """
    Identifica o comando executável real consumindo prefixos transparentes ou
    identificando executores de string (Handoff 026 §3, AB1).
    """
    n, idx = len(tokens), 0
    while idx < n:
        tok = os.path.basename(tokens[idx])
        if tok == "rtk":
            idx += 2 if (idx + 1 < n and tokens[idx + 1] == "proxy") else 1
            continue
        if tok in ("nohup", "builtin"):
            idx += 2 if (idx + 1 < n and tokens[idx + 1] == "--") else 1
            continue
        if tok == "command":
            idx = _consume_flags(tokens, idx + 1, set())
            continue
        if tok == "exec":
            idx = _consume_flags(tokens, idx + 1, {"-a"})
            continue
        if tok == "nice":
            idx = _consume_flags(tokens, idx + 1, {"-n", "--adjustment"})
            if idx < n and re.match(r"^-\d+$", tokens[idx]):
                idx += 1
            continue
        if tok == "timeout":
            idx = _consume_flags(tokens, idx + 1, {"-k", "--kill-after", "-s", "--signal"})
            if idx < n and not tokens[idx].startswith("-"):
                idx += 1
            continue
        if tok in ("sudo", "doas"):
            idx = _consume_flags(tokens, idx + 1, {"-u", "-g", "-h", "-p", "-r", "-t", "-T", "-C"})
            continue
        if tok == "env":
            idx += 1
            while idx < n:
                c = tokens[idx]
                if c in ("-u", "--unset", "-C", "--chdir") and idx + 1 < n:
                    idx += 2
                elif c == "--":
                    idx += 1; break
                elif c.startswith("-") or ("=" in c and not c.startswith("=")):
                    idx += 1
                else:
                    break
            continue
        if tok == "time":
            idx = _consume_flags(tokens, idx + 1, {"-o", "--output", "-f", "--format"})
            continue
        if tok in ("stdbuf", "ionice", "chrt", "taskset"):
            idx = _consume_flags(tokens, idx + 1, {"-i", "-o", "-e", "-c", "-n", "-p", "-P", "-u"})
            if tok in ("chrt", "taskset") and idx < n and not tokens[idx].startswith("-"):
                idx += 1
            continue
        if tok == "xargs":
            idx = _consume_flags(tokens, idx + 1, {"-n", "-P", "-d", "-s", "-E", "-L", "-I"})
            continue
        if tok == "eval":
            return idx, " ".join(tokens[idx + 1:])
        if tok == "su":
            for i in range(idx + 1, n):
                t = tokens[i]
                if t in ("-c", "--command") and i + 1 < n: return idx, tokens[i + 1]
                if t.startswith("-c="): return idx, t[3:]
                if t.startswith("--command="): return idx, t[10:]
            break
        if tok == "watch":
            i = _consume_flags(tokens, idx + 1, {"-n", "--interval"})
            if i < n:
                return idx, " ".join(tokens[i:])
            break
        break
    return idx, None


def substitute_positional_args(script: str, args: list[str]) -> str:
    """Substitui argumentos posicionais ($0, $1..., ${0}, "$@") em scripts de shell (AB3)."""
    if not args:
        return script
    res = script
    if len(args) > 1:
        res = res.replace('"$@"', " ".join(f'"{a}"' for a in args[1:])).replace('$@', " ".join(args[1:]))
    elif len(args) == 1:
        res = res.replace('"$@"', '').replace('$@', '')
    for idx, val in enumerate(args):
        pat = r'\$\{' + str(idx) + r'\}|\$' + str(idx) + r'(?!\d)'
        res = re.sub(pat, val, res)
    return res

