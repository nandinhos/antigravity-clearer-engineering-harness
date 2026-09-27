"""
rules.py - Padrões de segurança declarativos do Safety Gate do CEH.
Contém:
- CATASTROPHIC_PATTERNS: Hard blocks incondicionais em qualquer ambiente.
- SAFE_DEV_PATTERNS: Atalhos seguros de desenvolvimento (ALLOW).
- USE_CASE_DESTRUCTIVE_PATTERNS: Padrões destrutivos categorizados por Caso de Uso.
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

    # Git Version Control / History
    (r"\bgit\s+reset\s+--hard\b", "Destructive Git reset discarding uncommitted changes (git reset --hard)", "GIT_HISTORY", "Controle de Versão (Git)"),
    (r"\bgit\s+clean\s+-[a-zA-Z]*f", "Git clean discarding untracked files (git clean -f)", "GIT_HISTORY", "Controle de Versão (Git)"),
    (r"\bgit\s+branch\s+-[dD]\b", "Force deleting a Git branch", "GIT_HISTORY", "Controle de Versão (Git)"),
    (r"\bgit\s+push\s+.*--force\b", "Force pushing to remote repository (git push --force)", "GIT_HISTORY", "Controle de Versão (Git)"),
    (r"\bgit\s+push\s+.*-f\b", "Force pushing to remote repository (git push -f)", "GIT_HISTORY", "Controle de Versão (Git)"),
    (r"\bgit\s+push\s+.*\+[a-zA-Z0-9_\-\/]+", "Force pushing with refspec '+'", "GIT_HISTORY", "Controle de Versão (Git)"),

    # Filesystem / Bulk Deletion
    (r"\brm\s+-[rRfF]+", "Recursive or forced file deletion (rm -rf)", "FILESYSTEM", "Sistema de Arquivos"),

    # Infrastructure & Cloud Resources
    (r"\bterraform\s+destroy\b", "Destroying cloud infrastructure via Terraform", "INFRASTRUCTURE", "Infraestrutura e Nuvem"),
    (r"\bkubectl\s+delete\s+(?:namespace|ns|deployment|statefulset|svc|all)\b", "Deleting Kubernetes infrastructure resources", "INFRASTRUCTURE", "Infraestrutura e Nuvem"),
    (r"\bdocker\s+system\s+prune\s+-a\b", "Pruning all unused Docker images, volumes and containers", "INFRASTRUCTURE", "Infraestrutura e Nuvem"),
    (r"\bgsutil\s+rm\s+-r\b", "Recursive deletion in Google Cloud Storage", "INFRASTRUCTURE", "Infraestrutura e Nuvem"),

    # Packages & Registries
    (r"\b(?:npm|pnpm|yarn)\s+publish\b", "Publishing packages to public registry", "PACKAGE", "Pacotes e Registros"),
]

import os
import re
import shlex

CERT_FILES_REGEX = re.compile(
    r"(?:^|[\s\"'/])(?:\.ceh/)?(last-ci-run\.json|last-ci-run\.log|last-evals-run\.json)(?:[\s\"';&|]|$)"
)

ALLOWED_READ_CMDS = {
    "cat", "less", "more", "head", "tail", "jq", "grep", "egrep", "fgrep", "ls", "stat", "wc"
}

def is_cert_tampering(cmd: str) -> tuple[bool, str]:
    """
    Detecta tentativas de alteração ou escrita nos certificados de CI (.ceh/).
    Regra fail-closed: qualquer menção aos arquivos protegidos é bloqueada (DENY),
    EXCETO leituras puras sem redirecionamento de escrita (Handoff 037 G9).
    """
    if not CERT_FILES_REGEX.search(cmd):
        return False, ""

    clean_cmd = cmd.strip()
    try:
        tokens = shlex.split(clean_cmd)
    except ValueError:
        return True, "[CEH CERTIFICATE INTEGRITY - G9] ⛔ Erro de sintaxe em comando mencionando certificado de CI (.ceh/)."

    if not tokens:
        return False, ""

    # Verifica redirecionamentos de escrita para qualquer arquivo
    for tok in tokens:
        if any(tok.startswith(r) for r in (">", ">>", "1>", "2>", "&>")):
            return True, "[CEH CERTIFICATE INTEGRITY - G9] ⛔ Redirecionamento de escrita para certificado de CI (.ceh/)."

    idx = 0
    while idx < len(tokens):
        tok = tokens[idx]
        if tok in ("sudo", "env", "nohup", "time"):
            idx += 1
            continue
        if tok.startswith("-") and "=" in tok:
            idx += 1
            continue
        break

    if idx >= len(tokens):
        return True, "[CEH CERTIFICATE INTEGRITY - G9] ⛔ Comando inválido mencionando certificado de CI (.ceh/)."

    base_cmd = os.path.basename(tokens[idx])
    args = tokens[idx + 1:]

    # Leituras puras permitidas
    if base_cmd in ALLOWED_READ_CMDS:
        return False, ""

    # python3 -m json.tool .ceh/last-ci-run.json (leitura pura)
    if base_cmd in ("python", "python3") and len(args) >= 2:
        if args[0] == "-m" and args[1] == "json.tool":
            return False, ""

    return True, f"[CEH CERTIFICATE INTEGRITY - G9] ⛔ Tentativa de escrita/modificação de certificado de CI ({base_cmd}). Apenas leituras puras são permitidas."

