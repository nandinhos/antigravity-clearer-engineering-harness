"""
interpreters.py - Análise léxica e avaliação de segurança de scripts inline em interpretadores (G5, PR-06/PR-06b/PR-06e).
Cobre python, node, perl, ruby, php, awk, deno e bun com execução de código inline (-c, -e, --eval, flags agrupadas)
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
from .lexer import resolve_command_head
from .interpreters_extra import (
    evaluate_php_command,
    evaluate_awk_command,
    evaluate_deno_bun_command,
)

DESTRUCTIVE_APIS = {
    "python": re.compile(r"\b(rmtree|removedirs|unlink|rmdir|remove)\b"),
    "node": re.compile(r"\b(rmSync|rmdirSync|unlinkSync|rm|rmdir|unlink|rimraf)\b"),
    "perl": re.compile(r"\b(unlink|rmdir|rmtree|remove_tree)\b"),
    "ruby": re.compile(r"\b(rm_rf|rm_r|remove_dir|remove_entry|unlink|delete)\b|\brm\b"),
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
    cmds: list[str] = []
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
                                parts = [e.value for e in first_arg.elts if isinstance(e, ast.Constant) and isinstance(e.value, str)]
                                if parts:
                                    rebuilt = " ".join(parts)
                                    if rebuilt not in cmds:
                                        cmds.append(rebuilt)
        except Exception:
            pass

    for match in SHELL_INVOCATION_PATTERNS.finditer(code):
        for g in match.groups():
            if g is not None:
                unescaped = g.replace('\\"', '"').replace("\\'", "'").replace("\\\\", "\\")
                if unescaped not in cmds:
                    cmds.append(unescaped)
    return cmds


def resolve_interpreter_head(cmd_token: str) -> str | None:
    base = os.path.basename(cmd_token)
    if base.startswith("python") or base == "pypy":
        return "python"
    if base in ("node", "nodejs"):
        return "node"
    if base.startswith("perl"):
        return "perl"
    if base.startswith("ruby"):
        return "ruby"
    if base.startswith("php") or base == "hhvm":
        return "php"
    if base in ("awk", "gawk", "mawk", "nawk"):
        return "awk"
    if base == "deno":
        return "deno"
    if base == "bun":
        return "bun"
    return None


def extract_inline_code_and_args(tokens: list[str], interp_family: str) -> tuple[str | None, list[str]]:
    """Extrai código inline e args respeitando os flags que consomem argumentos (AD3, Handoff 028)."""
    code_letters: set[str] = set()
    arg_letters: set[str] = set()
    if interp_family == "python":
        code_letters, arg_letters = {"c"}, {"W", "X", "m"}
    elif interp_family == "node":
        code_letters, arg_letters = {"e", "p"}, {"r"}
    elif interp_family == "perl":
        code_letters, arg_letters = {"e", "E"}, {"M", "m", "I"}
    elif interp_family == "ruby":
        code_letters, arg_letters = {"e"}, {"r", "I", "E", "x"}

    i, n = 1, len(tokens)
    while i < n:
        tok = tokens[i]
        if tok == "--":
            break
        if interp_family == "node":
            if tok.startswith("--eval="):
                return tok[len("--eval="):], tokens[i + 1:]
            if tok == "--eval" and i + 1 < n:
                return tokens[i + 1], tokens[i + 2:]
            if tok == "--require" and i + 1 < n:
                i += 2; continue
            if tok.startswith("--require="):
                i += 1; continue

        if tok.startswith("-") and not tok.startswith("--") and len(tok) > 1:
            j, tok_len, consumed = 1, len(tok), False
            while j < tok_len:
                ch = tok[j]
                if ch in arg_letters:
                    if j + 1 < tok_len:
                        consumed = True; break
                    else:
                        if i + 1 < n:
                            i += 1
                        consumed = True; break
                if interp_family == "node" and ch == "p" and "e" in tok[j + 1:]:
                    j += 1
                    continue
                if ch in code_letters:
                    if j + 1 < tok_len:
                        return tok[j + 1:], tokens[i + 1:]
                    else:
                        if i + 1 < n:
                            return tokens[i + 1], tokens[i + 2:]
                        return None, []
                if interp_family == "perl" and ch in ("l", "0"):
                    k = j + 1
                    valid_chars = "01234567" if ch == "l" else "01234567xXabcdefABCDEF"
                    while k < tok_len and tok[k] in valid_chars:
                        k += 1
                    j = k; continue
                j += 1
            if consumed:
                i += 1; continue
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
    try:
        tokens = shlex.split(cmd_line, posix=True)
    except Exception:
        return None
    if not tokens:
        return None

    idx, _ = resolve_command_head(tokens)
    if idx >= len(tokens):
        return None

    interp_family = resolve_interpreter_head(tokens[idx])
    if interp_family is None:
        return None

    interp_tokens = [tokens[idx]] + tokens[idx + 1:]

    # AD4: Famílias especializadas
    if interp_family == "php":
        return evaluate_php_command(interp_tokens, env, env_evidence, base_cwd, eval_fn, depth)
    if interp_family == "awk":
        return evaluate_awk_command(interp_tokens, env, env_evidence, base_cwd, eval_fn, depth)
    if interp_family in ("deno", "bun"):
        return evaluate_deno_bun_command(interp_tokens, interp_family, env, env_evidence, base_cwd, eval_fn, depth)

    code, extra_args = extract_inline_code_and_args(interp_tokens, interp_family)
    if code is None:
        return None

    if eval_fn is not None:
        shell_cmds = extract_shell_commands_from_code(code, interp_family)
        for cmd in shell_cmds:
            sub_res = eval_fn(cmd, explicit_env=env, base_cwd=base_cwd, depth=depth + 1)
            if sub_res[3] == "CATASTROPHIC" or sub_res[0] in ("deny", "ask"):
                return sub_res

    for arg in extra_args:
        is_cat, cat_desc = is_target_catastrophic(arg, base_cwd)
        if is_cat:
            return "deny", f"[CEH CATASTROPHIC BLOCK] Hard block: {cat_desc}", env, "CATASTROPHIC"

    pattern = DESTRUCTIVE_APIS.get(interp_family)
    if not pattern or not pattern.search(code):
        return None

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
