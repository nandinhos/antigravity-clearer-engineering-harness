"""
environment.py - Detecção e normalização de ambientes de execução do CEH.
Contém:
- normalize_env: Normaliza strings de ambiente para production, staging ou development.
- get_git_branch: Obtém o nome da branch Git ativa.
- find_repo_root: Localiza a raiz do repositório Git subindo a árvore de diretórios.
- detect_environment: Identifica o ambiente com evidência rastreável (flag, comando, env var, .env, git branch).
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path


def normalize_env(val: str) -> str:
    """Normalizes environment string to: 'production', 'staging', or 'development'."""
    val_clean = val.strip().lower()
    if any(term in val_clean for term in ["prod", "production", "prd", "live"]):
        return "production"
    if any(term in val_clean for term in ["stage", "staging", "homolog", "homologacao", "homologação", "uat", "qa"]):
        return "staging"
    return "development"


def get_git_branch(target_dir: Path | str | None = None) -> str | None:
    """Attempts to get current git branch name, optionally in target_dir."""
    try:
        cmd = ["git", "branch", "--show-current"]
        cwd = Path(target_dir).resolve() if target_dir else None
        res = subprocess.run(
            cmd,
            cwd=cwd,
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


def detect_environment(
    explicit_env: str | None = None,
    cmd_line: str = "",
    target_dir: Path | str | None = None,
) -> tuple[str, str]:
    """
    Detects the current target environment with verifiable evidence:
    1. Explicit parameter / CLI argument (--env).
    2. Explicit target indicators inside the command string itself.
    3. Shell environment variables (CEH_ENV, APP_ENV, NODE_ENV, ENVIRONMENT, ENV, STAGE).
    4. Project .env / .env.production / .env.staging inspection (optionally in target_dir).
    5. Active Git branch (main/master/production -> safety escalation) (optionally in target_dir).
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
        current = Path(target_dir).resolve() if target_dir else Path.cwd()
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
    branch = get_git_branch(target_dir)
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
