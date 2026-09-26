"""
interpreters.py - Análise léxica e avaliação de segurança de scripts inline em interpretadores (G5, PR-06/PR-06b).
Cobre python, node, perl e ruby com execução de código inline (-c, -e, --eval, flags agrupadas)
e desembrulho recursivo de chamadas a comandos do sistema.
"""
from __future__ import annotations

import ast
import os
import re
import shlex
from pathlib import Path
from typing import Callable, Any

from .rm import is_target_catastrophic


# Detecção de APIs destrutivas pelo nome, sem exigir o prefixo do módulo (AA3)
DESTRUCTIVE_APIS = {
    "python": re.compile(
        r"\b(rmtree|removedirs|unlink|rmdir|remove)\b"
    ),
    "node": re.compile(
        r"\b(rmSync|rmdirSync|unlinkSync|rm|rmdir|unlink|rimraf)\b"
    ),
    "perl": re.compile(
        r"\b(unlink|rmdir|rmtree|remove_tree)\b"
    ),
    "ruby": re.compile(
        r"\b(rm_rf|rm_r|remove_dir|remove_entry|unlink|delete)\b|\brm\b"
    ),
}

_STR_PAT = r"""(?:"((?:[^"\\]|\\.)*)"|'((?:[^'\\]|\\.)*)')"""

SHELL_INVOCATION_PATTERNS = re.compile(
    r"""(?:\b(?:os\.)?(?:system|popen)\s*\(\s*""" + _STR_PAT + r"""\s*\)"""
    r"""|\bsubprocess\.(?:run|call|check_call|check_output|Popen)\s*\(\s*(?:\[\s*""" + _STR_PAT + r"""|""" + _STR_PAT + r""")"""
    r"""|(?:\bchild_process\.)?(?:execSync|exec|spawnSync|spawn)\s*\(\s*""" + _STR_PAT + r"""\s*\)"""
    r"""|\bsystem\s*\(\s*""" + _STR_PAT + r"""\s*\)"""
    r"""|`([^`]+)`)""",
    re.VERBOSE
)

STRING_LITERAL_RE = re.compile(_STR_PAT)


def extract_shell_commands_from_code(code: str, interp_family: str) -> list[str]:
    """Extrai comandos de shell invocados dentro do código do interpretador (AA2)."""
    cmds: list[str] = []

    # 1. Se for Python, usa AST da biblioteca padrão para precisão absoluta (Ponytail Mode)
    if interp_family == "python":
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    func_name = ""
                    if isinstance(node.func, ast.Attribute):
                        mod_name = getattr(node.func.value, "id", "")
                        func_name = f"{mod_name}.{node.func.attr}"
                    elif isinstance(node.func, ast.Name):
                        func_name = node.func.id

                    if func_name in (
                        "os.system", "os.popen", "system",
                        "subprocess.run", "subprocess.call", "subprocess.check_call",
                        "subprocess.check_output", "subprocess.Popen"
                    ):
                        if node.args:
                            first_arg = node.args[0]
                            if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                                if first_arg.value not in cmds:
                                    cmds.append(first_arg.value)
                            elif isinstance(first_arg, (ast.List, ast.Tuple)) and first_arg.elts:
                                cmd_parts = [e.value for e in first_arg.elts if isinstance(e, ast.Constant) and isinstance(e.value, str)]
                                if cmd_parts:
                                    rebuilt = " ".join(cmd_parts)
                                    if rebuilt not in cmds:
                                        cmds.append(rebuilt)
        except Exception:
            pass

    # 2. Regex robusta para Node, Perl, Ruby ou fallback de Python
    for match in SHELL_INVOCATION_PATTERNS.finditer(code):
        for g in match.groups():
            if g is not None:
                unescaped = g.replace('\\"', '"').replace("\\'", "'").replace("\\\\", "\\")
                if unescaped not in cmds:
                    cmds.append(unescaped)

    return cmds


def resolve_interpreter_head(cmd_token: str) -> str | None:
    """Resolve o executável para uma família de interpretador conhecida."""
    base = os.path.basename(cmd_token)
    if base.startswith("python") or base == "pypy":
        return "python"
    if base in ("node", "nodejs"):
        return "node"
    if base.startswith("perl"):
        return "perl"
    if base.startswith("ruby"):
        return "ruby"
    return None


def extract_inline_code_and_args(tokens: list[str], interp_family: str) -> tuple[str | None, list[str]]:
    """
    Extrai o código inline e os argumentos passados após o código (sys.argv).
    Suporta flags agrupadas (ex: python3 -Bc, perl -le, node -pe) e -c'código'.
    """
    target_letters = {
        "python": ("c",),
        "node": ("e", "p"),
        "perl": ("e", "E"),
        "ruby": ("e",),
    }.get(interp_family, ())

    i = 1
    n = len(tokens)
    while i < n:
        tok = tokens[i]

        # Flags longas como --eval ou --eval=código (Node)
        if interp_family == "node":
            if tok.startswith("--eval="):
                return tok[len("--eval="):], tokens[i + 1:]
            if tok == "--eval" and i + 1 < n:
                return tokens[i + 1], tokens[i + 2:]

        # Flags curtas começando com - (mas não --)
        if tok.startswith("-") and not tok.startswith("--") and len(tok) > 1:
            for letter in target_letters:
                if letter in tok:
                    pos = tok.rfind(letter)
                    # Se a letra é a última do token (ex: -c, -Bc, -le, -pe)
                    if pos == len(tok) - 1:
                        if i + 1 < n:
                            return tokens[i + 1], tokens[i + 2:]
                    else:
                        # Código colado no mesmo token (ex: -c'import os')
                        code_part = tok[pos + 1:]
                        return code_part, tokens[i + 1:]
        i += 1

    return None, []


def evaluate_interpreter_command(
    cmd_line: str,
    env: str,
    env_evidence: str = "",
    base_cwd: Path | str | None = None,
    eval_fn: Callable[..., tuple[str, str, str, str]] | None = None,
    depth: int = 0
) -> tuple[str, str, str, str] | None:
    """Avalia comandos de interpretadores inline com potencial destrutivo e desembrulho recursivo."""
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

    interp_family = resolve_interpreter_head(tokens[idx])
    if interp_family is None:
        return None

    interp_tokens = [tokens[idx]] + tokens[idx + 1:]
    code, extra_args = extract_inline_code_and_args(interp_tokens, interp_family)
    if code is None:
        return None

    # AA2: Desembrulho recursivo de comandos do sistema (os.system, subprocess, child_process, system, `...`)
    if eval_fn is not None:
        shell_cmds = extract_shell_commands_from_code(code, interp_family)
        for cmd in shell_cmds:
            sub_res = eval_fn(cmd, explicit_env=env, base_cwd=base_cwd, depth=depth + 1)
            if sub_res[3] == "CATASTROPHIC":
                return sub_res
            if sub_res[0] in ("deny", "ask"):
                return sub_res

    # AA3: Argumentos passados após o código (sys.argv)
    for arg in extra_args:
        is_cat, cat_desc = is_target_catastrophic(arg, base_cwd)
        if is_cat:
            return "deny", f"[CEH CATASTROPHIC BLOCK] Hard block: {cat_desc}", env, "CATASTROPHIC"

    # Verificação de APIs destrutivas da linguagem
    pattern = DESTRUCTIVE_APIS.get(interp_family)
    if not pattern or not pattern.search(code):
        return None

    # Verifica se algum literal de string no código é um alvo catastrófico
    for match in STRING_LITERAL_RE.finditer(code):
        raw_val = match.group(1) if match.group(1) is not None else match.group(2)
        if raw_val is not None:
            literal = raw_val.replace('\\"', '"').replace("\\'", "'").replace("\\\\", "\\").strip()
            is_cat, cat_desc = is_target_catastrophic(literal, base_cwd)
            if is_cat:
                return "deny", f"[CEH CATASTROPHIC BLOCK] Hard block: {cat_desc}", env, "CATASTROPHIC"

    desc = f"script inline destrutivo ({interp_family})"
    if env == "production":
        reason = (
            f"[CEH PRODUCTION LOCK] Comandos destrutivos são TERMINANTEMENTE PROIBIDOS em PRODUÇÃO "
            f"(Caso de Uso: Sistema de Arquivos (Interpretador de Comandos)): {desc}.\n"
            f"Ambiente detectado: {env.upper()} (Evidência: {env_evidence}).\n"
            f"Execução bloqueada para prevenir perda de dados e indisponibilidade."
        )
        return "deny", reason, env, "FILESYSTEM"

    if env == "staging":
        reason = (
            f"[CEH HOMOLOGAÇÃO / STAGING SAFETY GATE - Caso de Uso: Sistema de Arquivos (Interpretador de Comandos)]\n"
            f"⚠️ ALERTA 1/2 [IMPACTO DE HOMOLOGAÇÃO]: O comando possui potencial destrutivo/estrutural ({desc}).\n"
            f"   Ambiente detectado: {env.upper()} (Evidência: {env_evidence}).\n"
            f"⚠️ ALERTA 2/2 [BACKUP & ROLLBACK MANDATÓRIOS]: É obrigatório certificar-se de que o comando de BACKUP prévio "
            f"foi executado e que a estratégia de ROLLBACK imediato está disponível e testada antes de prosseguir.\n"
            f"Confirma a execução com rollback assegurado?"
        )
        return "ask", reason, env, "FILESYSTEM"

    reason = (
        f"[CEH DEV PERMITTED - Caso de Uso: Sistema de Arquivos (Interpretador de Comandos)] "
        f"Comando destrutivo liberado para ambiente de DESENVOLVIMENTO/TESTE ({desc}). "
        f"Ambiente: {env.upper()} (Evidência: {env_evidence}).\n"
        f"Assegure a disponibilidade de backup e rollback para fins de correção."
    )
    return "allow", reason, env, "FILESYSTEM"
