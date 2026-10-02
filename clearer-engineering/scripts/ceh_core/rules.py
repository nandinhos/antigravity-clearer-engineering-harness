"""
rules.py - Padrões de segurança declarativos do Safety Gate do CEH.
Contém:
- CATASTROPHIC_PATTERNS: Hard blocks incondicionais em qualquer ambiente.
- SAFE_DEV_PATTERNS: Atalhos seguros de desenvolvimento (ALLOW).
- USE_CASE_DESTRUCTIVE_PATTERNS: Padrões destrutivos categorizados por Caso de Uso.

Regra de desenho do P2 (Invariante de Padrões Catastróficos Globais):
Padrões que dependem da análise da linha bruta inteira (como fork bombs ou comandos
catastróficos contendo separadores ;, |, &) DEVEM rodar compulsoriamente antes de
qualquer decomposição léxica (split_shell_pipeline).
"""
from __future__ import annotations

# Catastrophic patterns that MUST be BLOCKED in ANY environment (including dev)
CATASTROPHIC_PATTERNS = [
    (r"\brm\s+-[rRfF]*[rR][rRfF]*\s+/(?:\s|$)", "Hard block: Attempting recursive deletion of root directory '/'."),
    (r"\brm\s+-[rRfF]*[rR][rRfF]*\s+~(?:\s|/|$)", "Hard block: Attempting recursive deletion of home directory '~'."),
    (r"\brm\s+-[rRfF]*[rR][rRfF]*\s+\.\.(?:\s|/|$)", "Hard block: Attempting recursive deletion of parent directory '..'."),
    (r"\brm\s+-[rRfF]*[rR][rRfF]*\s+\*(?:\s|$)", "Hard block: Blind wildcard recursive deletion 'rm -rf *'."),
    (r"\bmkfs\b", "Hard block: Filesystem formatting command detected."),
    (r"\bdd\s+if=.*of=/dev/", "Hard block: Direct disk writing via dd detected."),
    (r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:", "Hard block: Fork bomb detected."),
    (r"\bgcloud\s+projects\s+delete\b", "Hard block: Deleting GCP project detected."),
]

# Safe development patterns explicitly allowed (ALLOW bypass over generic checks)
SAFE_DEV_PATTERNS = [
    # Safe temporary/scratch cleanup
    r"\brm\s+-[rRfF]+\s+(?:/tmp/|tmp/|\.tmp/|scratch/|\.cache/|dist/|build/|storage/framework/cache/|coverage/)",
    # Safe single file removal
    r"\brm\s+-[rRfF]*[fF][rRfF]*\s+[a-zA-Z0-9_\-\.\/]+\.[a-zA-Z0-9]+(?:\s|$)",
]

# Destructive patterns categorized by Use Case
# Tuple format: (pattern, description, use_case_code, use_case_label)
USE_CASE_DESTRUCTIVE_PATTERNS = [
    # Database / Migrations
    (r"\bDROP\s+DATABASE\b", "DROP DATABASE statement", "DATABASE", "Banco de Dados"),
    (r"\bDROP\s+SCHEMA\b", "DROP SCHEMA statement", "DATABASE", "Banco de Dados"),
    (r"\bDROP\s+TABLE\b", "Destructive SQL: DROP TABLE", "DATABASE", "Banco de Dados"),
    (r"\bDROP\s+VIEW\b", "Destructive SQL: DROP VIEW", "DATABASE", "Banco de Dados"),
    (r"\bTRUNCATE(?:\s+TABLE)?\b", "Destructive SQL: TRUNCATE TABLE", "DATABASE", "Banco de Dados"),
    (r"\bDELETE\s+FROM\s+\w+\s*(?:;\s*$|$)", "Destructive SQL: Unconditional DELETE without WHERE clause", "DATABASE", "Banco de Dados"),
    (r"\bDELETE\s+FROM\s+\w+\s+WHERE\s+1\s*=\s*1", "Destructive SQL: DELETE with always-true WHERE 1=1", "DATABASE", "Banco de Dados"),
    (r"\b(?:artisan|php\s+artisan)\s+migrate:(?:fresh|reset)\b", "Destructive Laravel migration (migrate:fresh / migrate:reset)", "DATABASE", "Banco de Dados"),
    (r"\b(?:artisan|php\s+artisan)\s+db:wipe\b", "Destructive database wipe (artisan db:wipe)", "DATABASE", "Banco de Dados"),
    (r"\bredis-cli\b.*?\b(?:flushall|flushdb)\b", "Destructive Redis operation (redis-cli flushall/flushdb)", "DATABASE", "Banco de Dados"),
    (r"\b(?:npx\s+)?prisma\s+migrate\s+reset\b", "Destructive Prisma database reset (prisma migrate reset)", "DATABASE", "Banco de Dados"),

    # Git Version Control / History
    (r"\bgit\s+reset\s+--hard\b", "Destructive Git reset discarding uncommitted changes (git reset --hard)", "GIT_HISTORY", "Controle de Versão (Git)"),
    (r"\bgit\s+clean\s+-[a-zA-Z]*f", "Git clean discarding untracked files (git clean -f)", "GIT_HISTORY", "Controle de Versão (Git)"),
    (r"\bgit\s+branch\s+-[dD]\b", "Force deleting a Git branch", "GIT_HISTORY", "Controle de Versão (Git)"),
    (r"\bgit\s+push\s+.*--force\b", "Force pushing to remote repository (git push --force)", "GIT_HISTORY", "Controle de Versão (Git)"),
    (r"\bgit\s+push\s+.*-f\b", "Force pushing to remote repository (git push -f)", "GIT_HISTORY", "Controle de Versão (Git)"),
    (r"\bgit\s+push\s+.*\+[a-zA-Z0-9_\-\/]+", "Force pushing with refspec '+'", "GIT_HISTORY", "Controle de Versão (Git)"),
    (r"\bgit\s+stash\s+(?:clear|drop)\b", "Destructive Git stash operation (git stash clear/drop)", "GIT_HISTORY", "Controle de Versão (Git)"),

    # Infrastructure & Cloud Resources
    (r"\bterraform\s+destroy\b", "Destroying cloud infrastructure via Terraform", "INFRASTRUCTURE", "Infraestrutura e Nuvem"),
    (r"\bkubectl\s+delete\s+(?:namespace|ns|deployment|statefulset|svc|all)\b", "Deleting Kubernetes infrastructure resources", "INFRASTRUCTURE", "Infraestrutura e Nuvem"),
    (r"\bdocker\s+(?:--?[a-zA-Z0-9_\-]+(?:[=\s][^\s;]+)?\s+)*system\s+prune\s+-a\b", "Pruning all unused Docker images, volumes and containers", "INFRASTRUCTURE", "Infraestrutura e Nuvem"),
    (r"\bdocker\s+(?:--?[a-zA-Z0-9_\-]+(?:[=\s][^\s;]+)?\s+)*volume\s+(?:rm|prune)\b", "Destructive Docker volume operation (docker volume rm/prune)", "INFRASTRUCTURE", "Infraestrutura e Nuvem"),
    (r"\b(?:docker-compose|docker(?:\s+--?[a-zA-Z0-9_\-]+(?:[=\s][^\s;]+)?)*\s+compose)\b.*?\bdown\b.*?(?:^|\s)(?:-v|--volumes)\b", "Destructive Docker Compose teardown removing volumes (docker compose down -v)", "INFRASTRUCTURE", "Infraestrutura e Nuvem"),
    (r"\bgsutil\s+rm\s+-r\b", "Recursive deletion in Google Cloud Storage", "INFRASTRUCTURE", "Infraestrutura e Nuvem"),

    # Filesystem / Bulk Deletion
    (r"\brm\s+-[rRfF]+", "Recursive or forced file deletion (rm -rf)", "FILESYSTEM", "Sistema de Arquivos"),
    (r"\bdd\b.*?\bof=(?!/dev/)[^\s]+", "Destructive file overwrite via dd", "FILESYSTEM", "Sistema de Arquivos"),

    # Packages & Registries
    (r"\b(?:npm|pnpm|yarn)\s+publish\b", "Publishing packages to public registry", "PACKAGE", "Pacotes e Registros"),
]

import os
import re
import shlex
from pathlib import Path

from ceh_core.normalize import strip_all_quotes, tokenize_command, normalize_path

CERT_FILES_REGEX = re.compile(
    r"(?:^|[\s\"'/])(?:\.ceh/)?(last-ci-run\.json|last-ci-run\.log|last-evals-run\.json)(?:[\s\"';&|]|$)"
)

ALLOWED_READ_CMDS = {
    "cat", "less", "more", "head", "tail", "jq", "grep", "egrep", "fgrep", "ls", "stat", "wc", "du", "diff"
}

ALLOWED_GIT_READ_SUBCMDS = {"status", "log", "diff", "show"}
EXCLUDE_SUPPORTED_CMDS = {"tar", "rsync", "grep", "rg"}

def _extract_base_command(cmd: str) -> str:
    """Extrai o comando executável base desconsiderando wrappers transparentes e variáveis de ambiente."""
    tokens = tokenize_command(cmd, posix=True)
    idx = 0
    while idx < len(tokens):
        tok = os.path.basename(tokens[idx])
        if tok in ("sudo", "env", "nohup", "time", "nice", "doas", "command", "builtin", "exec"):
            idx += 1
            continue
        if tok == "rtk":
            idx += 2 if (idx + 1 < len(tokens) and tokens[idx + 1] == "proxy") else 1
            continue
        if tok.startswith("-") and "=" in tok:
            idx += 1
            continue
        if "=" in tok and not tok.startswith("-"):
            idx += 1
            continue
        break
    if idx < len(tokens):
        return os.path.basename(tokens[idx])
    return ""

def strip_ceh_exclusions(cmd: str) -> str:
    """
    Remove argumentos de exclusão benignos onde .ceh/ é explicitamente ignorado (AM2 / AV2 / AW1).
    Restringe estritamente a comandos que suportam exclusão sintática:
    - --exclude para tar, rsync, grep, rg
    - -path ... -prune para find
    """
    base_cmd = _extract_base_command(cmd)
    s = cmd
    if base_cmd in EXCLUDE_SUPPORTED_CMDS:
        s = re.sub(r"--exclude(?:=|\s+)['\"]?(?:\./)?\.ceh/?['\"]?", " ", s)
    if base_cmd == "find":
        s = re.sub(r"-path\s+['\"]?(?:\./)?\.ceh/?['\"]?\s+-prune", " ", s)
    return s

def is_git_read_subcommand(args: list[str]) -> bool:
    """
    Verifica se os argumentos de invocação do git constituem subcomando de leitura pura (AM2 / AV1 / PR-QA-C).
    Fail-closed: se qualquer token for flag de escrita ou execução (-o, -O, --output, --output=, --output-*,
    --ext-diff, --textconv), não é leitura pura, retornando False para barrar gravação ou execução externa (G9).
    """
    for arg in args:
        if arg in ("-o", "-O", "--output", "--ext-diff", "--textconv"):
            return False
        if arg.startswith(("--output=", "--output-", "--ext-diff", "--textconv")):
            return False
        if (arg.startswith("-o") or arg.startswith("-O")) and len(arg) > 2:
            return False

    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ("-C", "--git-dir", "--work-tree"):
            i += 2
            continue
        if arg.startswith("-"):
            i += 1
            continue
        return arg in ALLOWED_GIT_READ_SUBCMDS
    return False

def mentions_ceh_or_certs(cmd: str) -> bool:
    """Detecta se o comando menciona arquivos de certificado ou o próprio diretório .ceh/ (AL1/CA1)."""
    clean_target = strip_ceh_exclusions(cmd)
    if CERT_FILES_REGEX.search(clean_target):
        return True
    clean = strip_all_quotes(clean_target)
    return bool(re.search(r"(?:^|[\s/=>|&<>])(?:[^\s/]+/)*\.ceh(?:[/\s;&|*]|$)", clean, re.I))


def is_ceh_target(target: str, base_cwd: Path | str | None = None) -> bool:
    """Verifica se um caminho alvo resolve para dentro de .ceh/ ou certificado protegido (CA1)."""
    if not target:
        return False
    clean = strip_all_quotes(target).replace("\\", "/")
    if any(name in clean.lower() for name in ("last-ci-run.json", "last-ci-run.log", "last-evals-run.json")):
        return True
    if re.search(r"(?:^|/)\.ceh(?:/|$)", clean, re.I):
        return True
    try:
        norm = normalize_path(clean, cwd=base_cwd)
        if re.search(r"(?:^|/)\.ceh(?:/|$)", norm, re.I):
            return True
        full = Path(norm).resolve()
        if base_cwd is not None:
            ceh_dir = (Path(base_cwd).resolve() / ".ceh").resolve()
            if full == ceh_dir or ceh_dir in full.parents or any(part.lower() == ".ceh" for part in full.parts):
                return True
        else:
            if any(part.lower() == ".ceh" for part in full.parts):
                return True
    except (OSError, ValueError):
        pass
    return False


def extract_write_redirect_targets(cmd: str) -> list[str]:
    """Extrai alvos de redirecionamento de escrita em arquivo: >, >>, >|, &>, &>>, N>, N>>, <> (CA1)."""
    targets, i, n = [], 0, len(cmd)
    in_quote, escaped = None, False
    while i < n:
        c = cmd[i]
        if escaped: escaped = False; i += 1; continue
        if c == "\\":
            if in_quote != "'": escaped = True
            i += 1; continue
        if in_quote:
            if c == in_quote: in_quote = None
            i += 1; continue
        if c in ("'", '"'): in_quote = c; i += 1; continue

        is_redir, op_len = False, 0
        if cmd.startswith(("&>>",), i): is_redir, op_len = True, 3
        elif cmd.startswith(("&>", "<>", ">>", ">|"), i): is_redir, op_len = True, 2
        elif c == ">": is_redir, op_len = True, 1
        elif c.isdigit():
            j = i
            while j < n and cmd[j].isdigit(): j += 1
            if j < n and cmd.startswith(">>", j): is_redir, op_len = True, (j - i) + 2
            elif j < n and cmd[j] == ">": is_redir, op_len = True, (j - i) + 1

        if is_redir:
            k = i + op_len
            while k < n and cmd[k] in (" ", "\t"): k += 1
            if k < n and cmd[k] == "&" and k + 1 < n and (cmd[k + 1].isdigit() or cmd[k + 1] == "-"):
                i = k + 2; continue
            tgt_chars, tgt_q, tgt_esc = [], None, False
            while k < n:
                tc = cmd[k]
                if tgt_esc: tgt_chars.append(tc); tgt_esc = False; k += 1; continue
                if tc == "\\":
                    if tgt_q != "'": tgt_esc = True
                    k += 1; continue
                if tgt_q:
                    if tc == tgt_q: tgt_q = None
                    else: tgt_chars.append(tc)
                    k += 1; continue
                if tc in ("'", '"'): tgt_q = tc; k += 1; continue
                if tc in (" ", "\t", ";", "&", "|", "<", ">"): break
                tgt_chars.append(tc); k += 1
            if tgt_chars: targets.append("".join(tgt_chars))
            i = k; continue
        i += 1
    return targets


def is_cert_tampering(cmd: str, base_cwd: Path | str | None = None) -> tuple[bool, str]:
    """Detecta tentativas de alteração ou escrita nos certificados de CI ou .ceh/ (G9/CA1)."""
    write_targets = extract_write_redirect_targets(cmd)
    if any(is_ceh_target(t, base_cwd=base_cwd) for t in write_targets):
        return True, "[CEH CERTIFICATE INTEGRITY - G9/AL1] ⛔ Redirecionamento de escrita para .ceh/ ou certificado de CI."

    if not mentions_ceh_or_certs(cmd):
        return False, ""

    clean_cmd = cmd.strip()
    try:
        tokens = shlex.split(clean_cmd)
    except ValueError:
        return True, "[CEH CERTIFICATE INTEGRITY - G9/AL1] ⛔ Erro de sintaxe em comando mencionando .ceh/ ou certificado de CI."

    if not tokens:
        return False, ""

    idx = 0
    while idx < len(tokens):
        tok = tokens[idx]
        if tok in ("sudo", "env", "nohup", "time"): idx += 1; continue
        if tok.startswith("-") and "=" in tok: idx += 1; continue
        break

    if idx >= len(tokens):
        return True, "[CEH CERTIFICATE INTEGRITY - G9/AL1] ⛔ Comando inválido mencionando .ceh/ ou certificado de CI."

    base_cmd = os.path.basename(tokens[idx]).lower()
    args = tokens[idx + 1:]

    # Leituras puras permitidas (ls .ceh, cat .ceh/last-ci-run.json, du -sh .ceh, diff ...)
    if base_cmd in ALLOWED_READ_CMDS:
        if base_cmd == "less" and any(a in ("-o", "-O") or a.startswith(("--log-file", "--LOG-FILE")) or ((a.startswith("-o") or a.startswith("-O")) and len(a) > 2) for a in args):
            return True, "[CEH CERTIFICATE INTEGRITY - G9/AL1] ⛔ less com opção de escrita de log (-o/--log-file) mencionando .ceh/ ou certificado de CI."
        return False, ""

    if base_cmd == "git" and is_git_read_subcommand(args):
        return False, ""
    if base_cmd == "rtk" and args and args[0] == "git" and is_git_read_subcommand(args[1:]):
        return False, ""

    if base_cmd in ("python", "python3") and len(args) >= 2 and args[0] == "-m" and args[1] == "json.tool":
        if len([a for a in args[2:] if not a.startswith("-")]) <= 1:
            return False, ""

    return True, f"[CEH CERTIFICATE INTEGRITY - G9/AL1] ⛔ Tentativa de escrita/modificação de .ceh/ ou certificado de CI ({base_cmd}). Apenas leituras puras são permitidas."


