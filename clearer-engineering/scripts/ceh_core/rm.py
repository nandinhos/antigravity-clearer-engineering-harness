"""
rm.py - Análise léxica e avaliação de segurança de comandos 'rm' do CEH (G1, G4, PR-04b, PR-04c).
"""
from __future__ import annotations

import os
import re
import shlex
from pathlib import Path

SYSTEM_ROOTS = {
    "/etc", "/usr", "/var", "/bin", "/sbin", "/boot",
    "/home", "/lib", "/lib64", "/opt", "/root", "/srv",
    "/sys", "/proc", "/dev"
}

SAFE_DIR_PREFIXES = (
    "tmp/", ".tmp/", "/tmp/", "scratch/", ".cache/",
    "dist/", "build/", "coverage/", "storage/framework/cache/",
    "node_modules/.cache"
)


def parse_rm_tokens(tokens: list[str]) -> tuple[bool, bool, list[str]]:
    """Decompõe argumentos do comando rm em (is_recursive, is_force, targets)."""
    is_recursive, is_force, targets = False, False, []
    parsing_options = True

    for token in tokens[1:]:
        if parsing_options and token == "--":
            parsing_options = False
            continue
        if parsing_options and token.startswith("-") and len(token) > 1:
            if token.startswith("--"):
                flag_name = token[2:].split("=", 1)[0]
                if flag_name in ("recursive", "no-preserve-root"):
                    is_recursive = True
                elif flag_name == "force":
                    is_force = True
            else:
                chars = token[1:]
                if any(c in chars for c in ("r", "R")):
                    is_recursive = True
                if "f" in chars or "F" in chars:
                    is_force = True
            continue
        targets.append(token)

    return is_recursive, is_force, targets


def has_unresolved_env_var(target: str) -> bool:
    """Verifica se o alvo contém variáveis de ambiente não resolvíveis com segurança."""
    t_clean = target.replace("${PWD}", "").replace("$PWD", "").replace("${HOME}", "").replace("$HOME", "")
    return bool(re.search(r"\$[a-zA-Z_]\w*|\$\{[a-zA-Z_]\w*\}", t_clean))


def is_target_catastrophic(target: str, cwd: Path | str | None = None) -> tuple[bool, str]:
    """Verifica se um alvo é catastrófico (bloqueado incondicionalmente em qualquer ambiente)."""
    cwd_path = Path.cwd().resolve() if cwd is None else Path(cwd).resolve()
    cwd_str = str(cwd_path)

    t = target.replace('"', "").replace("'", "").strip()
    if not t:
        return False, ""

    # S2: $PWD e ${PWD} resolvem para o cwd da avaliação, NUNCA os.environ['PWD']
    t = t.replace("${PWD}", cwd_str).replace("$PWD", cwd_str)
    home_dir = os.environ.get("HOME", "/home/user")
    t = t.replace("${HOME}", home_dir).replace("$HOME", home_dir)

    if t.startswith("~"):
        if t in ("~", "~/") or t.startswith("~/"):
            t = home_dir + t[1:]
        elif t.startswith("~root"):
            t = "/root" + t[5:]
        else:
            t = os.path.expanduser(t)

    is_glob = False
    if t in ("*", "./*"):
        is_glob, base = True, "."
    elif t.endswith("/*"):
        is_glob, base = True, (t[:-2] or "/")
    elif t.endswith("/*/"):
        is_glob, base = True, (t[:-3] or "/")
    else:
        base = t

    base = re.sub(r"/+", "/", base)
    norm = os.path.normpath(base) if os.path.isabs(base) else os.path.normpath(os.path.join(cwd_str, base))

    # (a) Raiz /
    if norm == "/":
        return True, "Attempting recursive deletion of root directory '/'."
    # (b) Exatamente um diretório de sistema de primeiro nível (SYSTEM_ROOTS)
    if norm in SYSTEM_ROOTS:
        return True, f"Attempting recursive deletion of protected directory '{target}'."
    # (c) Exatamente /home/<nome> ou o HOME resolvido
    resolved_home = os.path.normpath(home_dir)
    if norm == resolved_home:
        return True, "Attempting recursive deletion of home directory '~'."
    if norm.startswith("/home/") and norm.count("/") == 2:
        return True, f"Attempting recursive deletion of protected directory '{target}'."
    # (d) Um ancestral ou o próprio diretório de trabalho
    if norm == cwd_str:
        if is_glob or target in ("*", "./*") or target.endswith("/*"):
            return True, "Attempting recursive deletion of wildcard '*'."
        return True, f"Attempting recursive deletion of protected directory '{target}'."
    if cwd_str.startswith(norm + "/"):
        if target in ("..", "../"):
            return True, "Attempting recursive deletion of parent directory '..'."
        return True, f"Attempting recursive deletion of protected directory '{target}'."

    return False, ""


def is_target_safe(target: str, is_force: bool, cwd: Path | str | None = None) -> bool:
    """S1: Atalho seguro restrito a diretórios no cwd, arquivo único ou /tmp/."""
    cwd_path = Path.cwd().resolve() if cwd is None else Path(cwd).resolve()
    cwd_str = str(cwd_path)

    if has_unresolved_env_var(target) or is_target_catastrophic(target, cwd_path)[0]:
        return False

    t = target.replace('"', "").replace("'", "").strip()
    t = re.sub(r"/+", "/", t.replace("${PWD}", cwd_str).replace("$PWD", cwd_str))

    norm_full = os.path.normpath(t if os.path.isabs(t) else os.path.join(cwd_str, t))

    # (c) Caminhos absolutos: apenas sob /tmp/ normalizado é permitido como atalho seguro
    if os.path.isabs(t):
        if norm_full == "/tmp" or norm_full.startswith("/tmp/"):
            return True
        return False

    rel = os.path.relpath(norm_full, cwd_str)
    if rel.startswith("..") or rel == ".":
        return False

    first_seg = rel.split(os.sep)[0]
    if first_seg in {"tmp", ".tmp", "scratch", ".cache", "dist", "build", "coverage"}:
        return False if rel == ".cache" else True
    if rel.startswith("storage/framework/cache/"):
        return True
    if rel.startswith("node_modules/.cache") or rel == "node_modules/.cache":
        return True

    # (b) Arquivo único com extensão dentro do cwd
    if is_force and not rel.endswith("/"):
        parts = rel.split(os.sep)
        first, last = parts[0], parts[-1]
        norm_first = "/" + first.lstrip("/")
        if "." in last and not last.startswith(".") and "*" not in last and norm_first not in SYSTEM_ROOTS:
            return True

    return False


def evaluate_rm_command(
    cmd_line: str,
    env: str,
    env_evidence: str = "",
    base_cwd: Path | str | None = None
) -> tuple[str, str, str, str] | None:
    """Avalia a segurança de comandos 'rm' por tokens."""
    try:
        tokens = shlex.split(cmd_line, posix=True)
    except Exception:
        return None

    if not tokens or tokens[0] != "rm":
        return None

    is_recursive, is_force, targets = parse_rm_tokens(tokens)

    # 1. G4 / PR-04b / PR-04c: Bloqueio Catastrófico incondicional
    for target in targets:
        is_cat, desc = is_target_catastrophic(target, base_cwd)
        if is_cat:
            return "deny", f"[CEH CATASTROPHIC BLOCK] Hard block: {desc}", env, "CATASTROPHIC"

    if not targets:
        return None

    # S2: Variáveis não resolvíveis tornam o alvo incerto (Invariante 7)
    unresolved_targets = [t for t in targets if has_unresolved_env_var(t)]
    if unresolved_targets:
        if env == "production":
            reason = f"[CEH PRODUCTION LOCK] Alvo incerto com variável não resolvida: '{unresolved_targets[0]}'."
            return "deny", reason, env, "FILESYSTEM"
        if env == "staging":
            reason = f"[CEH HOMOLOGAÇÃO / STAGING SAFETY GATE]\n⚠️ ALERTA 1/2: Alvo incerto '{unresolved_targets[0]}'.\n⚠️ ALERTA 2/2: Confirmar rollback."
            return "ask", reason, env, "FILESYSTEM"
        reason = f"[CEH UNCERTAIN TARGET] Variável de ambiente não resolvida no alvo ('{unresolved_targets[0]}')."
        return "ask", reason, env, "FILESYSTEM"

    if not is_recursive and not is_force:
        return "allow", "Comando geral seguro.", env, "GENERAL"

    # 2. G1 / S1: Atalho de limpeza segura
    if all(is_target_safe(t, is_force, base_cwd) for t in targets):
        return "allow", f"Safe development operation permitted ({env_evidence}).", env, "FILESYSTEM_SAFE"

    # 3. Exclusão recursiva ou forçada fora do atalho seguro
    if is_recursive or is_force:
        if env == "production":
            reason = (
                "[CEH PRODUCTION LOCK] Comandos destrutivos são TERMINANTEMENTE PROIBIDOS em PRODUÇÃO "
                "(Caso de Uso: Sistema de Arquivos): Recursive or forced file deletion (rm -rf).\n"
                "Ambiente detectado: PRODUCTION.\n"
                "Execução bloqueada para prevenir perda de dados e indisponibilidade."
            )
            return "deny", reason, env, "FILESYSTEM"

        if env == "staging":
            reason = (
                "[CEH HOMOLOGAÇÃO / STAGING SAFETY GATE - Caso de Uso: Sistema de Arquivos]\n"
                "⚠️ ALERTA 1/2 [IMPACTO DE HOMOLOGAÇÃO]: O comando possui potencial destrutivo/estrutural (Recursive or forced file deletion (rm -rf)).\n"
                f"   Ambiente detectado: STAGING.\n"
                "⚠️ ALERTA 2/2 [BACKUP & ROLLBACK MANDATÓRIOS]: É obrigatório certificar-se de que o comando de BACKUP prévio "
                "foi executado e que a estratégia de ROLLBACK imediato está disponível e testada antes de prosseguir.\n"
                "Confirma a execução com rollback assegurado?"
            )
            return "ask", reason, env, "FILESYSTEM"

        reason = (
            "[CEH DEV PERMITTED - Caso de Uso: Sistema de Arquivos] Comando destrutivo liberado para ambiente de "
            "desenvolvimento/teste, condicionado à prontidão de backup e estratégia de rollback."
        )
        return "allow", reason, env, "FILESYSTEM"

    return None
