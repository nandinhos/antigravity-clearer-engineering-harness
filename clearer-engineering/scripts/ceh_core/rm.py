"""
rm.py - Análise léxica e avaliação de segurança de comandos 'rm' do CEH (G1 e G4).
Aplica tokenização via shlex para parsing estrito de flags e alvos:
- G4: Bloqueio incondicional (DENY) de alvos catastróficos em qualquer ambiente (/, /*, ~, $HOME, etc.).
- G1 (Opção A): Atalho de limpeza segura só é concedido se TODOS os alvos forem seguros.
"""
from __future__ import annotations

import shlex

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
    """
    Decompõe argumentos do comando rm:
    Retorna (is_recursive, is_force, targets).
    Reconhece flags curtas (-r, -f, -rf, -fr, -R, etc.), longas (--recursive, --force, etc.)
    e o terminador de opções '--'.
    """
    is_recursive = False
    is_force = False
    targets = []
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
                # Flags curtas combinadas: ex -rf, -fr, -r, -f, -R, -v
                chars = token[1:]
                if any(c in chars for c in ("r", "R")):
                    is_recursive = True
                if "f" in chars or "F" in chars:
                    is_force = True
            continue

        # Se não é opção ou já passou do '--', é alvo
        targets.append(token)

    return is_recursive, is_force, targets


def is_target_catastrophic(target: str) -> bool:
    """Verifica se um alvo é catastrófico (bloqueado em qualquer ambiente)."""
    t = target.strip().strip("'\"")
    if not t:
        return False

    # Raiz, wildcards cegos, home, parent dir, current dir
    if t in ("/", "/*", "///", "/.", "/..", "~", "~/", "~/*", "$HOME", "${HOME}", "..", "../", "*", "."):
        return True

    # Padrões que referenciam $HOME ou ~
    if t in ("$HOME/", "${HOME}/", "~/", "$HOME/*", "${HOME}/*", "~/*"):
        return True

    # Diretórios de sistema de primeiro nível
    norm = "/" + t.lstrip("/").rstrip("/")
    if norm in SYSTEM_ROOTS:
        return True

    for root in SYSTEM_ROOTS:
        if norm == root or norm.startswith(root + "/") or norm.startswith(root + "/*"):
            return True

    return False


def is_target_safe(target: str, is_force: bool) -> bool:
    """Verifica se um alvo é considerado inequivocamente seguro para deleção/limpeza."""
    t = target.strip().strip("'\"")
    if t.startswith("./"):
        t = t[2:]

    if not t or is_target_catastrophic(t):
        return False

    # Diretórios seguros
    if t in ("build", "dist", "node_modules/.cache"):
        return True

    if any(t.startswith(p) for p in SAFE_DIR_PREFIXES):
        return True

    # Arquivo único com extensão e flag -f (conforme SAFE_DEV_PATTERNS original: rm -f file.txt)
    if is_force and not t.endswith("/"):
        parts = t.split("/")
        first, last = parts[0], parts[-1]
        norm_first = "/" + first.lstrip("/")
        if "." in last and not last.startswith(".") and "*" not in last and norm_first not in SYSTEM_ROOTS:
            return True

    return False


def evaluate_rm_command(cmd_line: str, env: str) -> tuple[str, str, str, str] | None:
    """
    Avalia a segurança de comandos 'rm' por tokens:
    Retorna (decision, reason, detected_env, use_case) ou None se não for comando rm.
    """
    try:
        tokens = shlex.split(cmd_line, posix=True)
    except Exception:
        return None

    if not tokens or tokens[0] != "rm":
        return None

    is_recursive, is_force, targets = parse_rm_tokens(tokens)

    # 1. G4: Bloqueio Catastrófico incondicional (qualquer ambiente)
    for target in targets:
        if is_target_catastrophic(target):
            t_clean = target.strip().strip("'\"")
            if t_clean in ("/", "///", "/."):
                desc = "Attempting recursive deletion of root directory '/'."
            elif t_clean in ("~", "~/"):
                desc = "Attempting recursive deletion of home directory '~'."
            elif t_clean in ("..", "../"):
                desc = "Attempting recursive deletion of parent directory '..'."
            elif t_clean == "*":
                desc = "Attempting recursive deletion of wildcard '*'."
            else:
                desc = f"Attempting recursive deletion of protected directory '{target}'."
            reason = f"[CEH CATASTROPHIC BLOCK] Hard block: {desc}"
            return "deny", reason, env, "CATASTROPHIC"

    # Se não há alvos especificados, deixa o gate padrão
    if not targets:
        return None

    # Se não é recursivo nem forçado, é remoção simples sem flag de risco (ex: rm app/test.txt)
    if not is_recursive and not is_force:
        return "allow", "Comando geral seguro.", env, "GENERAL"

    # 2. G1 (Opção A): Atalho de limpeza segura em qualquer ambiente
    # Só concede se TODOS os alvos forem seguros
    is_all_safe = all(is_target_safe(t, is_force) for t in targets)
    if is_all_safe:
        return "allow", "Safe development operation permitted (Explicit parameter (--env development)).", env, "FILESYSTEM_SAFE"

    # 3. Se nem todos os alvos são seguros e é exclusão recursiva ou forçada:
    if is_recursive or is_force:
        if env == "production":
            reason = (
                f"[CEH PRODUCTION LOCK] Comandos destrutivos são TERMINANTEMENTE PROIBIDOS em PRODUÇÃO "
                f"(Caso de Uso: Sistema de Arquivos): Recursive or forced file deletion (rm -rf).\n"
                f"Ambiente detectado: PRODUCTION.\n"
                f"Execução bloqueada para prevenir perda de dados e indisponibilidade."
            )
            return "deny", reason, env, "FILESYSTEM"

        if env == "staging":
            reason = (
                f"[CEH HOMOLOGAÇÃO / STAGING SAFETY GATE - Caso de Uso: Sistema de Arquivos]\n"
                f"⚠️ ALERTA 1/2 [IMPACTO DE HOMOLOGAÇÃO]: O comando possui potencial destrutivo/estrutural (Recursive or forced file deletion (rm -rf)).\n"
                f"   Ambiente detectado: STAGING.\n"
                f"⚠️ ALERTA 2/2 [BACKUP & ROLLBACK MANDATÓRIOS]: É obrigatório certificar-se de que o comando de BACKUP prévio "
                f"foi executado e que a estratégia de ROLLBACK imediato está disponível e testada antes de prosseguir.\n"
                f"Confirma a execução com rollback assegurado?"
            )
            return "ask", reason, env, "FILESYSTEM"

        # Development
        reason = (
            f"[CEH DEV PERMITTED - Caso de Uso: Sistema de Arquivos] Comando destrutivo liberado para ambiente de "
            f"desenvolvimento/teste, condicionado à prontidão de backup e estratégia de rollback."
        )
        return "allow", reason, env, "FILESYSTEM"

    return None
