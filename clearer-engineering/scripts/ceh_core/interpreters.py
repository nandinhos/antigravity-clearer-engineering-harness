"""
interpreters.py - Análise léxica e avaliação de segurança de scripts inline em interpretadores (G5, PR-06).
Cobre python, node, perl e ruby com execução de código inline (-c, -e, --eval).
"""
from __future__ import annotations

import os
import re
import shlex
from pathlib import Path

from .rm import is_target_catastrophic


DESTRUCTIVE_APIS = {
    "python": re.compile(
        r"\bshutil\.rmtree\b"
        r"|\bos\.(remove|unlink|rmdir|removedirs)\b"
        r"|\b(pathlib\.)?Path\([^)]*\)\.(unlink|rmdir)\b"
        r"|\.(unlink|rmdir)\s*\("
    ),
    "node": re.compile(
        r"\b(fs|promises)\.(rmSync|rmdirSync|unlinkSync|rm|unlink|rmdir)\b"
        r"|require\(['\"]fs['\"]\)\.(rmSync|rmdirSync|unlinkSync|rm|unlink|rmdir)\b"
    ),
    "perl": re.compile(
        r"\b(unlink|rmdir)\b"
        r"|(File::Path::)?(rmtree|remove_tree)\b"
    ),
    "ruby": re.compile(
        r"\bFileUtils\.(rm_rf|rm_r|rm|remove_dir|remove_entry)\b"
        r"|\bFile\.(unlink|delete)\b"
        r"|\bDir\.(rmdir|unlink)\b"
    ),
}

INLINE_CODE_FLAGS = {
    "python": {"-c"},
    "node": {"-e", "--eval", "-p", "--print"},
    "perl": {"-e", "-E"},
    "ruby": {"-e"},
}

STRING_LITERAL_RE = re.compile(r"""['"]([^'"]+)['"]""")


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


def extract_inline_code(tokens: list[str], interp_family: str) -> str | None:
    """Extrai o código inline passado via flag para o interpretador."""
    valid_flags = INLINE_CODE_FLAGS.get(interp_family, set())
    i = 1
    n = len(tokens)
    while i < n:
        tok = tokens[i]
        if tok in valid_flags and i + 1 < n:
            return tokens[i + 1]
        for f in valid_flags:
            if tok.startswith(f + "="):
                return tok[len(f) + 1:]
        i += 1
    return None


def evaluate_interpreter_command(
    cmd_line: str,
    env: str,
    env_evidence: str = "",
    base_cwd: Path | str | None = None
) -> tuple[str, str, str, str] | None:
    """Avalia comandos de interpretadores inline com potencial destrutivo."""
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
    code = extract_inline_code(interp_tokens, interp_family)
    if code is None:
        return None

    pattern = DESTRUCTIVE_APIS.get(interp_family)
    if not pattern or not pattern.search(code):
        return None

    # Verifica se algum literal de string é um alvo catastrófico
    for match in STRING_LITERAL_RE.finditer(code):
        literal = match.group(1).strip()
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
