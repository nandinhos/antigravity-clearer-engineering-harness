"""
rm.py - Análise léxica e avaliação de segurança de comandos 'rm' do CEH (G1, G4 e PR-04b).
Aplica tokenização via shlex e normalização canônica de caminhos:
- G4 / PR-04b: Bloqueio incondicional (DENY CATASTROPHIC) de:
  - Raiz '/' (incluindo variantes //, /./, /*)
  - Exatamente um diretório de sistema de primeiro nível (SYSTEM_ROOTS) ou seu glob direto
  - Exatamente /home/<nome>, o HOME resolvido ou ~root
  - O próprio diretório de trabalho ou seus ancestrais (., .., ../.., ./*, *)
  Descendentes NÃO são catastróficos e seguem as regras de FILESYSTEM do ambiente.
- G1 (Opção A): Atalho de limpeza segura só é concedido se TODOS os alvos forem seguros.
- R3: A razão utiliza a evidência de ambiente real (env_evidence).
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
                chars = token[1:]
                if any(c in chars for c in ("r", "R")):
                    is_recursive = True
                if "f" in chars or "F" in chars:
                    is_force = True
            continue

        targets.append(token)

    return is_recursive, is_force, targets


def is_target_catastrophic(target: str, cwd: Path | str | None = None) -> tuple[bool, str]:
    """
    Verifica se um alvo é catastrófico (bloqueado em qualquer ambiente).
    Aplica normalização estrita de caminho (PR-04b):
    1. Expansão de ~ e $HOME
    2. Separação de globs (* ou /*)
    3. Colapso de barras repetidas e normpath
    4. Resolução de caminhos relativos contra o diretório de trabalho
    """
    if cwd is None:
        cwd_path = Path.cwd().resolve()
    else:
        cwd_path = Path(cwd).resolve()
    cwd_str = str(cwd_path)

    t = target.strip().strip("'\"")
    if not t:
        return False, ""

    # 1. Expansão de variáveis $HOME e ${HOME}
    home_dir = os.environ.get("HOME", "/home/user")
    t = t.replace("${HOME}", home_dir).replace("$HOME", home_dir)

    # 2. Expansão de tilde (~ e ~usuario)
    if t.startswith("~"):
        if t in ("~", "~/") or t.startswith("~/"):
            t = home_dir + t[1:]
        elif t.startswith("~root"):
            t = "/root" + t[5:]
        else:
            t = os.path.expanduser(t)

    # 3. Tratamento de glob (* ou /*)
    is_glob = False
    if t in ("*", "./*"):
        is_glob = True
        base = "."
    elif t.endswith("/*"):
        is_glob = True
        base = t[:-2]
        if not base:
            base = "/"
    elif "/*" in t:
        is_glob = True
        base = t[:t.rfind("/*")]
        if not base:
            base = "/"
    else:
        base = t

    # 4. Colapso de barras repetidas e resolução para caminho absoluto normalizado
    base = re.sub(r"/+", "/", base)
    if os.path.isabs(base):
        norm = os.path.normpath(base)
    else:
        norm = os.path.normpath(os.path.join(cwd_str, base))

    # 5. Avaliação das 4 categorias de Catastrófico (Handoff 014):
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
        if is_glob or target in ("*", "./*"):
            return True, "Attempting recursive deletion of wildcard '*'."
        return True, f"Attempting recursive deletion of protected directory '{target}'."

    if cwd_str.startswith(norm + "/"):
        if target in ("..", "../"):
            return True, "Attempting recursive deletion of parent directory '..'."
        return True, f"Attempting recursive deletion of protected directory '{target}'."

    return False, ""


def is_target_safe(target: str, is_force: bool, cwd: Path | str | None = None) -> bool:
    """Verifica se um alvo é considerado inequivocamente seguro para deleção/limpeza."""
    is_cat, _ = is_target_catastrophic(target, cwd)
    if is_cat:
        return False

    t = target.strip().strip("'\"")
    t = re.sub(r"/+", "/", t)
    if t.startswith("./"):
        t = t[2:]

    # Diretórios seguros canônicos de build/dist
    if t in ("build", "build/", "dist", "dist/"):
        return True

    if any(t.startswith(p) for p in SAFE_DIR_PREFIXES):
        return True

    # Se for caminho absoluto ou relativo que termina em diretório seguro legítimo
    parts = t.rstrip("/").split("/")
    if parts:
        last_seg = parts[-1]
        if last_seg in ("build", "dist", "coverage", "scratch"):
            return True
        if len(parts) >= 2 and parts[-2] == "node_modules" and last_seg == ".cache":
            return True

    # Arquivo único com extensão e flag -f
    if is_force and not t.endswith("/"):
        parts = t.split("/")
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

    # 1. G4 / PR-04b: Bloqueio Catastrófico incondicional (qualquer ambiente)
    for target in targets:
        is_cat, desc = is_target_catastrophic(target, base_cwd)
        if is_cat:
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
    is_all_safe = all(is_target_safe(t, is_force, base_cwd) for t in targets)
    if is_all_safe:
        return "allow", f"Safe development operation permitted ({env_evidence}).", env, "FILESYSTEM_SAFE"

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
