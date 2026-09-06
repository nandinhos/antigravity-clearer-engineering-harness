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

def evaluate_command(cmd_line: str, explicit_env: str | None = None) -> tuple[str, str, str, str]:
    """
    Evaluates a command line string against environment safety rules.
    Returns (decision, reason, detected_env, use_case) where decision is 'deny', 'ask', or 'allow'.
    """
    if not cmd_line or not cmd_line.strip():
        return "allow", "Empty command", "development", "GENERAL"

    cmd_normalized = cmd_line.strip()
    env, env_evidence = detect_environment(explicit_env, cmd_normalized)

    # 1. Catastrophic Blocks: DENY has absolute priority in ANY environment
    for pattern, reason in CATASTROPHIC_PATTERNS:
        if re.search(pattern, cmd_normalized, re.IGNORECASE):
            return "deny", f"[CEH CATASTROPHIC BLOCK] {reason}", env, "CATASTROPHIC"

    # 2. Safe Development Bypasses: allow cache/scratch cleanup and selective checkout
    for pattern in SAFE_DEV_PATTERNS:
        if re.search(pattern, cmd_normalized, re.IGNORECASE):
            return "allow", f"Safe development operation permitted ({env_evidence}).", env, "FILESYSTEM_SAFE"

    # 3. Evaluate Destructive Patterns by Use Case and Environment
    for pattern, desc, use_case_code, use_case_label in USE_CASE_DESTRUCTIVE_PATTERNS:
        if re.search(pattern, cmd_normalized, re.IGNORECASE):
            # -------------------------------------------------------------
            # PRODUÇÃO: Fora de cogitação (DENY incondicional)
            # -------------------------------------------------------------
            if env == "production":
                reason = (
                    f"[CEH PRODUCTION LOCK] Comandos destrutivos são TERMINANTEMENTE PROIBIDOS em PRODUÇÃO "
                    f"(Caso de Uso: {use_case_label}): {desc}.\n"
                    f"Ambiente detectado: {env.upper()} (Evidência: {env_evidence}).\n"
                    f"Execução bloqueada para prevenir perda de dados e indisponibilidade."
                )
                return "deny", reason, env, use_case_code

            # -------------------------------------------------------------
            # HOMOLOGAÇÃO: Confirmação obrigatória com 2 ALERTAS explícitos
            # -------------------------------------------------------------
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

            # -------------------------------------------------------------
            # DESENVOLVIMENTO / TESTE: Permitido com prontidão de backup/rollback
            # -------------------------------------------------------------
            reason = (
                f"[CEH DEV PERMITTED - Caso de Uso: {use_case_label}] Comando destrutivo liberado para ambiente de "
                f"DESENVOLVIMENTO/TESTE ({desc}). Ambiente: {env.upper()} (Evidência: {env_evidence}).\n"
                f"Assegure a disponibilidade de backup e rollback para fins de correção."
            )
            return "allow", reason, env, use_case_code

    return "allow", f"Command complies with CEH safety policy (Env: {env.upper()}, Source: {env_evidence}).", env, "GENERAL"

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
