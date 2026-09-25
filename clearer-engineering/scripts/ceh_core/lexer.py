"""
lexer.py - Analisador léxico e normalizador de pipelines de shell do CEH.
Contém:
- split_shell_pipeline: Decompõe pipelines em comandos atômicos com parser caractere a caractere (FSM).
- normalize_command_for_evaluation: Remove aspas superficiais de comandos (quote-removal).
"""
from __future__ import annotations

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
