#!/usr/bin/env python3
"""
safety-gate.py - PreToolUse Safety Guard for CLEARER Engineering Harness (CEH).
Enforces environment-aware safety policy across 3 tiers:
- Development / Test: Destructive commands permitted with backup & rollback readiness.
- Homologação / Staging: Confirmation required (ASK) with 2 explicit alerts + backup & rollback mandate.
- Produção: Destructive commands strictly prohibited (DENY - fora de cogitação).
"""

import sys
import os
import json
import re
import argparse
import subprocess
import shlex
from pathlib import Path

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
    # Safe git checkout/restore of specific files (not '.' or whole tree)
    r"\bgit\s+checkout\s+(?![\.\-]\s*$)[a-zA-Z0-9_\-\.\/]+(?:\s|$)",
    r"\bgit\s+restore\s+(?![\.\-]\s*$)[a-zA-Z0-9_\-\.\/]+(?:\s|$)",
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
    (r"\bgit\s+restore\s+(?:\.|\s+--staged\s+\.)\b", "Git restore discarding all working tree changes", "GIT_HISTORY", "Controle de Versão (Git)"),
    (r"\bgit\s+checkout\s+--\s+\.\b", "Git checkout discarding all modified files", "GIT_HISTORY", "Controle de Versão (Git)"),
    (r"\bgit\s+checkout\s+\.\b", "Git checkout discarding all working tree files", "GIT_HISTORY", "Controle de Versão (Git)"),
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

def normalize_env(val: str) -> str:
    """Normalizes environment string to: 'production', 'staging', or 'development'."""
    val_clean = val.strip().lower()
    if any(term in val_clean for term in ["prod", "production", "prd", "live"]):
        return "production"
    if any(term in val_clean for term in ["stage", "staging", "homolog", "homologacao", "homologação", "uat", "qa"]):
        return "staging"
    return "development"

def get_git_branch() -> str | None:
    """Attempts to get current git branch name."""
    try:
        res = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            timeout=2
        )
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()
    except Exception:
        pass
    return None

def find_repo_root(start_dir: Path) -> Path | None:
    """Finds git repository root directory traversing upwards."""
    current = start_dir.resolve()
    for parent in [current] + list(current.parents):
        if (parent / ".git").exists():
            return parent
    return None

def resolve_git_invocation(cmd_line: str, base_cwd: Path) -> tuple[bool, Path | None, str, str | None]:
    """
    Analisa a invocação do Git:
    1. Identifica se é comando git.
    2. Acumula iterativamente flags -C <path> e -C<path>, resolvendo espaços.
    3. Rejeita em Fail-Closed opções não homologadas que alterem o repositório (--git-dir, --work-tree).
    4. Localiza a raiz do repositório via find_repo_root().
    5. Reconstrói o comando de forma canônica: 'git push <args restantes>'.
    Retorna: (is_git_push, target_repo_root, canonical_cmd, error_reason)
    """
    import shlex
    try:
        tokens = shlex.split(cmd_line, posix=True)
    except Exception as e:
        return False, None, cmd_line, f"Erro de parsing na linha git: {e}"

    # Remove prefixo de RTK se presente
    if tokens and tokens[0] == "rtk":
        tokens = tokens[1:]
    if tokens and tokens[0] == "proxy":
        tokens = tokens[1:]

    if not tokens or tokens[0] != "git":
        return False, None, cmd_line, None

    current_dir = base_cwd
    subcommand = None
    remaining_args = []
    i = 1

    while i < len(tokens):
        token = tokens[i]
        if token == "-C" and i + 1 < len(tokens):
            current_dir = (current_dir / tokens[i+1]).resolve()
            i += 2
            continue
        elif token.startswith("-C") and len(token) > 2:
            path_part = token[2:]
            current_dir = (current_dir / path_part).resolve()
            i += 1
            continue
        elif token.startswith("--git-dir") or token.startswith("--work-tree") or token == "-c":
            return False, None, cmd_line, f"Opção global do Git não homologada no Safety Gate ({token})"
        elif token.startswith("-"):
            # Outras opções globais inócuas para diretório
            i += 1
            continue
        else:
            subcommand = token
            remaining_args = tokens[i+1:]
            break

    if subcommand != "push":
        return False, None, cmd_line, None

    repo_root = find_repo_root(current_dir) if current_dir.exists() else None
    canonical_cmd = "git push" + (" " + " ".join(remaining_args) if remaining_args else "")
    return True, repo_root, canonical_cmd, None

def check_pre_push_ci_gate(cmd: str, target_dir: Path | None = None) -> tuple[str, str] | None:
    """
    Zero-Tolerance Pipeline Red Pre-Push Gate:
    If repository has CI workflows (.github/workflows), enforces that the current HEAD
    commit has a successful canonical test certificate in .ceh/last-ci-run.json.
    Applies to every push, force included: force is restricted further by GIT_HISTORY rules.
    """
    base_dir = target_dir or Path.cwd()
    repo_root = find_repo_root(base_dir)
    if not repo_root:
        return None

    # Check if repo has CI workflows
    ci_workflows_dir = repo_root / ".github" / "workflows"
    has_github_ci = ci_workflows_dir.is_dir() and any(
        list(ci_workflows_dir.glob("*.yml")) + list(ci_workflows_dir.glob("*.yaml"))
    )
    has_gitlab_ci = (repo_root / ".gitlab-ci.yml").is_file()

    if not (has_github_ci or has_gitlab_ci):
        return None  # No CI pipeline defined; allow standard git push

    # Repo has CI pipeline. Verify last-ci-run.json
    cert_file = repo_root / ".ceh" / "last-ci-run.json"
    if not cert_file.is_file():
        reason = (
            "[CEH PRE-PUSH CI GATE] ⛔ Push bloqueado!\n"
            "O repositório possui esteira de CI ativa em '.github/workflows', mas NENHUMA execução "
            "da suíte de testes foi registrada localmente para validar o código.\n"
            "Diretriz de Governança: Zero-Tolerance Pipeline Red (Regra 2 - Git & CI).\n"
            "Ação requerida: Execute a suíte de testes com 'bash clearer-engineering/scripts/test-runner.sh' "
            "e obtenha exit code 0 antes de realizar o push."
        )
        return "deny", reason

    try:
        data = json.loads(cert_file.read_text(encoding="utf-8"))
        exit_code = data.get("exit_code")
        status = data.get("status", "FAIL")
        cert_commit = data.get("commit_hash", "")
        cmd_executed = str(data.get("command", "")).strip()

        if not cert_commit or cert_commit == "untracked":
            reason = (
                "[CEH PRE-PUSH CI GATE] ⛔ Push bloqueado: Certificado inválido (commit_hash ausente ou não rastreado).\n"
                "Ação requerida: Execute a suíte de testes em um commit Git válido antes do push."
            )
            return "deny", reason

        if exit_code != 0 or status != "PASS":
            reason = (
                f"[CEH PRE-PUSH CI GATE] ⛔ Push bloqueado!\n"
                f"A última execução da suíte de testes FALHOU (Exit Code: {exit_code}, Status: {status}).\n"
                f"Comando executado: {cmd_executed}\n"
                f"Diretriz de Governança: Proibido subir código com CI quebrado.\n"
                f"Ação requerida: Corrija as falhas e execute a suíte de testes com 100% de aprovação antes do push."
            )
            return "deny", reason

        if data.get("canonical_verified") is not True:
            reason = (
                f"[CEH PRE-PUSH CI GATE] ⛔ Push bloqueado: O certificado não comprova execução da suíte canônica.\n"
                f"Comando registrado: '{cmd_executed}'. Apenas o comando declarado em .ceh/config.json "
                f"(ou o auto-detectado, sem config) concede certificado.\n"
                f"Ação requerida: Execute 'bash clearer-engineering/scripts/test-runner.sh' sem argumentos."
            )
            return "deny", reason

        head_res = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=3
        )
        if head_res.returncode == 0:
            current_head = head_res.stdout.strip()
            if cert_commit != current_head:
                reason = (
                    f"[CEH PRE-PUSH CI GATE] ⛔ Push bloqueado por desatualização de testes!\n"
                    f"O commit atual ({current_head[:7]}) não foi testado após as alterações mais recentes.\n"
                    f"O último certificado válido foi emitido para o commit {cert_commit[:7]}.\n"
                    f"Ação requerida: Execute a suíte de testes integral novamente para revalidar o commit atual antes do push."
                )
                return "deny", reason

    except Exception as e:
        reason = (
            f"[CEH PRE-PUSH CI GATE] ⛔ Push bloqueado: Certificado de CI ilegível ({str(e)}).\n"
            f"Ação requerida: Execute a suíte de testes novamente para gerar um novo certificado válido."
        )
        return "deny", reason

    return "allow", "Pre-Push CI Gate validado: suíte canônica aprovada para o commit atual."

def detect_environment(explicit_env: str | None = None, cmd_line: str = "") -> tuple[str, str]:
    """
    Detects the current target environment with verifiable evidence:
    1. Explicit parameter / CLI argument (--env).
    2. Explicit target indicators inside the command string itself.
    3. Shell environment variables (CEH_ENV, APP_ENV, NODE_ENV, ENVIRONMENT, ENV, STAGE).
    4. Project .env / .env.production / .env.staging inspection.
    5. Active Git branch (main/master/production -> safety escalation).
    Returns (environment, evidence_source).
    """
    # 1. Explicit override
    if explicit_env:
        return normalize_env(explicit_env), f"Explicit parameter (--env {explicit_env})"

    # 2. Contextual indicators in command line
    if cmd_line:
        cmd_lower = cmd_line.lower()
        if any(term in cmd_lower for term in ["--env=production", "--env=prod", "production", "target=prod"]):
            return "production", "Command context explicitly references production target"
        if any(term in cmd_lower for term in ["--env=staging", "--env=stage", "--env=homolog", "staging", "homolog"]):
            return "staging", "Command context explicitly references staging target"

    # 3. Environment variables
    for var in ["CEH_ENV", "APP_ENV", "NODE_ENV", "ENVIRONMENT", "ENV", "STAGE"]:
        val = os.environ.get(var)
        if val:
            return normalize_env(val), f"Environment variable {var}={val}"

    # 4. Project .env inspection
    try:
        current = Path.cwd()
        for directory in [current, *current.parents]:
            # Priority to specific env files
            if (directory / ".env.production").is_file():
                return "production", f"Configuration file {directory / '.env.production'}"
            if (directory / ".env.staging").is_file() or (directory / ".env.homolog").is_file():
                return "staging", f"Configuration file in {directory}"

            env_file = directory / ".env"
            if env_file.is_file():
                content = env_file.read_text(encoding="utf-8", errors="ignore")
                for line in content.splitlines():
                    line = line.strip()
                    if line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip("\"'")
                    if k in ["CEH_ENV", "APP_ENV", "NODE_ENV", "ENVIRONMENT", "ENV", "STAGE"]:
                        return normalize_env(v), f"File .env ({k}={v})"
            if (directory / ".git").exists():
                break
    except Exception:
        pass

    # 5. Git branch inspection (preventive escalation & canonical flow)
    branch = get_git_branch()
    if branch:
        branch_lower = branch.lower()
        if branch_lower in ["main", "master", "production", "prod"]:
            return "production", f"Git branch '{branch}' (canonical production branch)"
        if any(term in branch_lower for term in ["staging", "stage", "homolog", "homologacao", "uat", "qa"]):
            return "staging", f"Git branch '{branch}' (canonical staging branch)"
        if branch_lower in ["dev", "develop"]:
            return "development", f"Git branch '{branch}' (canonical dev branch)"
        if branch_lower.startswith("dev/") or branch_lower.startswith("dev-") or branch_lower.startswith("feature/") or branch_lower.startswith("fix/"):
            return "development", f"Git branch '{branch}' (derivation from dev)"

    # Default fallback: safe local development
    return "development", "Default workspace fallback (development/local)"

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
    import shlex
    try:
        tokens = shlex.split(subcmd, posix=True)
        if tokens:
            return " ".join(tokens)
    except Exception:
        pass
    return subcmd


def evaluate_subcommand(subcmd: str, env: str, env_evidence: str) -> tuple[str, str, str, str]:
    """
    Avalia um subcomando atômico contra as políticas de segurança do CEH.
    Retorna (decision, reason, detected_env, use_case).
    """
    sub_raw = subcmd.strip()
    # Strip CLI proxy prefix (RTK / RTK proxy)
    sub_eval = re.sub(r"^\s*rtk(?:\s+proxy)?\s+", "", sub_raw)
    sub_norm = normalize_command_for_evaluation(sub_eval)

    # 1. Catastrophic Blocks: DENY has absolute priority in ANY environment
    for pattern, reason in CATASTROPHIC_PATTERNS:
        if (
            re.search(pattern, sub_eval, re.IGNORECASE)
            or re.search(pattern, sub_norm, re.IGNORECASE)
            or re.search(pattern, sub_raw, re.IGNORECASE)
        ):
            return "deny", f"[CEH CATASTROPHIC BLOCK] {reason}", env, "CATASTROPHIC"

    # 2. Resolução Canônica de Git (R5)
    is_git_push, target_repo, canonical_cmd, git_err = resolve_git_invocation(sub_eval, Path.cwd())
    if git_err:
        return "deny", f"[CEH SAFETY GATE - GIT] ⛔ {git_err}", env, "GIT_DESTRUCTIVE"

    if is_git_push:
        sub_eval = canonical_cmd
        sub_norm = normalize_command_for_evaluation(canonical_cmd)

    # 3. Safe Development Bypasses: allow cache/scratch cleanup and selective checkout (sem outros padrões destrutivos)
    is_safe_dev = False
    for pattern in SAFE_DEV_PATTERNS:
        if re.search(pattern, sub_eval, re.IGNORECASE) or re.search(pattern, sub_norm, re.IGNORECASE):
            is_safe_dev = True
            break
    if is_safe_dev:
        # Confirma que não contém padrões destrutivos de Banco de Dados, Git History ou Infraestrutura
        has_other_destructive = False
        for pattern, desc, use_case_code, use_case_label in USE_CASE_DESTRUCTIVE_PATTERNS:
            if use_case_code != "FILESYSTEM":
                if (
                    re.search(pattern, sub_eval, re.IGNORECASE)
                    or re.search(pattern, sub_norm, re.IGNORECASE)
                    or re.search(pattern, sub_raw, re.IGNORECASE)
                ):
                    has_other_destructive = True
                    break
        if not has_other_destructive:
            return "allow", f"Safe development operation permitted ({env_evidence}).", env, "FILESYSTEM_SAFE"

    # 4. Evaluate Destructive Patterns by Use Case and Environment
    for pattern, desc, use_case_code, use_case_label in USE_CASE_DESTRUCTIVE_PATTERNS:
        if (
            re.search(pattern, sub_eval, re.IGNORECASE)
            or re.search(pattern, sub_norm, re.IGNORECASE)
            or re.search(pattern, sub_raw, re.IGNORECASE)
        ):
            # PRODUÇÃO: Fora de cogitação (DENY incondicional)
            if env == "production":
                reason = (
                    f"[CEH PRODUCTION LOCK] Comandos destrutivos são TERMINANTEMENTE PROIBIDOS em PRODUÇÃO "
                    f"(Caso de Uso: {use_case_label}): {desc}.\n"
                    f"Ambiente detectado: {env.upper()} (Evidência: {env_evidence}).\n"
                    f"Execução bloqueada para prevenir perda de dados e indisponibilidade."
                )
                return "deny", reason, env, use_case_code

            # HOMOLOGAÇÃO: Confirmação obrigatória com 2 ALERTAS explícitos
            if env == "staging":
                reason = (
                    f"[CEH HOMOLOGAÇÃO / STAGING SAFETY GATE - Caso de Uso: {use_case_label}]\n"
                    f"⚠️ ALERTA 1/2 [IMPACTO DE HOMOLOGAÇÃO]: O comando possui potencial destrutivo/estrutural ({desc}).\n"
                    f"   Ambiente detectado: {env.upper()} (Evidência: {env_evidence}).\n"
                    f"⚠️ ALERTA 2/2 [BACKUP & ROLLBACK MANDATÓRIOS]: É obrigatório certificar-se de que o comando de BACKUP prévio "
                    f"foi executado e que a estratégia de ROLLBACK imediato está disponível e testada antes de prosseguir.\n"
                    f"Confirma a execução com rollback assegurado?"
                )
                return "ask", reason, env, use_case_code

            # DESENVOLVIMENTO / TESTE: Permitido com prontidão de backup/rollback
            if is_git_push:
                break  # Force push segue para o gate de CI (passo 5): força não isenta de certificado
            reason = (
                f"[CEH DEV PERMITTED - Caso de Uso: {use_case_label}] Comando destrutivo liberado para ambiente de "
                f"DESENVOLVIMENTO/TESTE ({desc}). Ambiente: {env.upper()} (Evidência: {env_evidence}).\n"
                f"Assegure a disponibilidade de backup e rollback para fins de correção."
            )
            return "allow", reason, env, use_case_code

    # 5. Pre-Push CI Clearance Gate (todo git push, inclusive force push)
    if is_git_push:
        ci_gate_result = check_pre_push_ci_gate(sub_eval, target_dir=target_repo)
        if ci_gate_result is not None:
            ci_decision, ci_reason = ci_gate_result
            return ci_decision, ci_reason, env, "PRE_PUSH_CI"

    return "allow", f"Command complies with CEH safety policy (Env: {env.upper()}, Source: {env_evidence}).", env, "GENERAL"


def evaluate_command(cmd_line: str, explicit_env: str | None = None) -> tuple[str, str, str, str]:
    """
    Evaluates a command line string against environment safety rules, decomposing
    compound commands and aggregating decisions with priority: DENY > ASK > ALLOW.
    """
    if not cmd_line or not cmd_line.strip():
        return "allow", "Empty command", "development", "GENERAL"

    cmd_normalized = cmd_line.strip()
    env, env_evidence = detect_environment(explicit_env, cmd_normalized)

    # Decompõe linha em subcomandos atômicos via FSM Lexer
    subcommands, parse_err = split_shell_pipeline(cmd_normalized)
    if parse_err:
        return (
            "deny",
            f"[CEH SAFETY GATE - FAIL-CLOSED] Sintaxe complexa ou quoting não suportado rejeitado: {parse_err}.\n"
            f"Ambiente: {env.upper()}. Para segurança estrita, use comandos atômicos sem subshells ou construções não homologadas.",
            env,
            "PARSER_FAIL_CLOSED",
        )

    if not subcommands:
        return "allow", "Empty command after decomposition", env, "GENERAL"

    evaluations = []
    for sub in subcommands:
        evaluations.append(evaluate_subcommand(sub, env, env_evidence))

    # Precedência estrita: DENY > ASK > ALLOW
    denies = [e for e in evaluations if e[0] == "deny"]
    if denies:
        return denies[0]

    asks = [e for e in evaluations if e[0] == "ask"]
    if asks:
        return asks[0]

    return evaluations[0]

def handle_hook():
    """Processes Antigravity PreToolUse hook JSON from stdin."""
    try:
        raw_input = sys.stdin.read()
        if not raw_input.strip():
            print(json.dumps({"decision": "allow"}))
            return

        payload = json.loads(raw_input)
        tool_call = payload.get("toolCall", {})
        tool_name = tool_call.get("name", "")
        args = tool_call.get("args", {})

        if tool_name == "run_command":
            cmd_line = args.get("CommandLine", "")
            decision, reason, env, use_case = evaluate_command(cmd_line)
            output = {
                "decision": decision,
                "reason": reason
            }
            print(json.dumps(output, ensure_ascii=False))
            return

        # Default for non-command tools
        print(json.dumps({"decision": "allow"}))

    except Exception as e:
        print(json.dumps({
            "decision": "ask",
            "reason": f"[CEH SAFETY GATE ERROR] Failed to parse hook payload: {str(e)}"
        }, ensure_ascii=False))

def main():
    parser = argparse.ArgumentParser(description="CEH Safety Gate Command Checker")
    parser.add_argument("--check", type=str, help="Directly check a command string and output decision")
    parser.add_argument("--env", type=str, default=None, help="Explicit environment override (development|staging|production)")
    args = parser.parse_args()

    if args.check is not None:
        decision, reason, env, use_case = evaluate_command(args.check, explicit_env=args.env)
        result = {
            "decision": decision,
            "reason": reason,
            "environment": env,
            "use_case": use_case,
            "command": args.check
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
        if decision == "deny":
            sys.exit(2)
        elif decision == "ask":
            sys.exit(1)
        else:
            sys.exit(0)
    else:
        handle_hook()

if __name__ == "__main__":
    main()
