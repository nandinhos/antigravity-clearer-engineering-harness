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
import re
import shlex
import subprocess
from pathlib import Path

PROD_SEGMENTS = set(["prod", "production", "prd", "live"]) | {"preprod"}
STAGING_SEGMENTS = {"stage", "staging", "homolog", "homologacao", "homologação", "uat", "qa"}

ENV_SEVERITY = {
    "development": 0,
    "staging": 1,
    "production": 2,
}

EXPLICIT_ENV_VARS = {"APP_ENV", "NODE_ENV", "RAILS_ENV", "CEH_ENV"}
CONTEXT_FLAGS = {"--context", "--kube-context"}


def normalize_env(val: str) -> str:
    """Normalizes environment string to: 'production', 'staging', or 'development'."""
    val_clean = val.strip().lower()
    segments = set(s for s in re.split(r'[^\w]+', val_clean) if s)
    if any(term in segments for term in PROD_SEGMENTS):
        return "production"
    if any(term in segments for term in STAGING_SEGMENTS):
        return "staging"
    return "development"


def extract_command_environment_tokens(cmd_line: str) -> tuple[str | None, str | None]:
    """
    Extrai sinais explícitos de ambiente na linha de comando:
    1. Atribuições APP_ENV=X, NODE_ENV=X, RAILS_ENV=X, CEH_ENV=X no início ou após 'env'.
    2. Flags --env=X ou --env X.
    3. Flags --context=X, --context X, --kube-context=X, --kube-context X.
    Ignora comentários (# ...), caminhos de arquivo, mensagens (--grep=..., -m "...") e texto livre.
    Retorna (env, evidence) do sinal mais severo encontrado, ou (None, None).
    """
    if not cmd_line:
        return None, None

    try:
        tokens = shlex.split(cmd_line, posix=True, comments=True)
    except Exception:
        tokens = cmd_line.split()

    found_envs: list[tuple[str, str]] = []
    n = len(tokens)
    idx = 0

    while idx < n:
        tok = tokens[idx]

        # 1. Atribuições KEY=VAL na cabeça do comando ou após 'env'
        if "=" in tok and not tok.startswith("-") and not tok.startswith("="):
            k, v = tok.split("=", 1)
            if k in EXPLICIT_ENV_VARS:
                target_env = normalize_env(v)
                found_envs.append((target_env, f"Explicit command assignment {k}={v}"))
            idx += 1
            continue

        # 2. Comando transparente 'env': processa flags e atribuições seguintes
        if tok == "env":
            idx += 1
            while idx < n:
                c = tokens[idx]
                if c.startswith("-"):
                    idx += 1
                elif "=" in c and not c.startswith("="):
                    k, v = c.split("=", 1)
                    if k in EXPLICIT_ENV_VARS:
                        target_env = normalize_env(v)
                        found_envs.append((target_env, f"Explicit env command assignment {k}={v}"))
                    idx += 1
                else:
                    break
            continue

        # 3. Flags --env=X ou --env X
        if tok == "--env" and idx + 1 < n:
            val = tokens[idx + 1]
            target_env = normalize_env(val)
            found_envs.append((target_env, f"Explicit command flag --env {val}"))
            idx += 2
            continue
        if tok.startswith("--env="):
            val = tok.split("=", 1)[1]
            target_env = normalize_env(val)
            found_envs.append((target_env, f"Explicit command flag --env={val}"))
            idx += 1
            continue

        # 4. Flags --context / --kube-context
        if tok in CONTEXT_FLAGS and idx + 1 < n:
            val = tokens[idx + 1]
            target_env = normalize_env(val)
            found_envs.append((target_env, f"Explicit context flag {tok} {val}"))
            idx += 2
            continue
        if any(tok.startswith(f"{cf}=") for cf in CONTEXT_FLAGS):
            flag, val = tok.split("=", 1)
            target_env = normalize_env(val)
            found_envs.append((target_env, f"Explicit context flag {flag}={val}"))
            idx += 1
            continue

        idx += 1

    if not found_envs:
        return None, None

    return max(found_envs, key=lambda item: ENV_SEVERITY.get(item[0], 0))


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
    2. Context environment from environment variables, configuration files, and Git branch.
    3. Explicit command-line tokens (which only ESCALATE severity, never downgrade).
    Returns (environment, evidence_source).
    """
    # 1. Explicit override
    if explicit_env:
        return normalize_env(explicit_env), f"Explicit parameter (--env {explicit_env})"

    # 2. Context detection (env vars, .env files, git branch, fallback)
    context_env = "development"
    context_evidence = "Default workspace fallback (development/local)"

    # 2.1 Environment variables
    found_var = False
    for var in ["CEH_ENV", "APP_ENV", "NODE_ENV", "ENVIRONMENT", "ENV", "STAGE"]:
        val = os.environ.get(var)
        if val:
            context_env = normalize_env(val)
            context_evidence = f"Environment variable {var}={val}"
            found_var = True
            break

    # 2.2 Project .env inspection
    if not found_var:
        try:
            current = Path(target_dir).resolve() if target_dir else Path.cwd()
            for directory in [current, *current.parents]:
                if (directory / ".env.production").is_file():
                    context_env = "production"
                    context_evidence = f"Configuration file {directory / '.env.production'}"
                    break
                if (directory / ".env.staging").is_file() or (directory / ".env.homolog").is_file():
                    context_env = "staging"
                    context_evidence = f"Configuration file in {directory}"
                    break

                env_file = directory / ".env"
                if env_file.is_file():
                    content = env_file.read_text(encoding="utf-8", errors="ignore")
                    found_env_line = False
                    for line in content.splitlines():
                        line = line.strip()
                        if line.startswith("#") or "=" not in line:
                            continue
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("\"'")
                        if k in ["CEH_ENV", "APP_ENV", "NODE_ENV", "ENVIRONMENT", "ENV", "STAGE"]:
                            context_env = normalize_env(v)
                            context_evidence = f"File .env ({k}={v})"
                            found_env_line = True
                            break
                    if found_env_line:
                        break
                if (directory / ".git").exists():
                    break
        except Exception:
            pass

    # 2.3 Git branch inspection (preventive escalation & canonical flow)
    branch = get_git_branch(target_dir)
    if branch:
        branch_lower = branch.lower()
        segments = set(s for s in re.split(r'[^\w]+', branch_lower) if s)
        branch_env = None
        branch_ev = None
        if any(s in ["main", "master", "production", "prod"] for s in segments) or any(s in PROD_SEGMENTS for s in segments):
            branch_env = "production"
            branch_ev = f"Git branch '{branch}' (canonical production branch)"
        elif any(s in STAGING_SEGMENTS for s in segments):
            branch_env = "staging"
            branch_ev = f"Git branch '{branch}' (canonical staging branch)"
        elif any(s in ["dev", "develop"] for s in segments) or branch_lower.startswith(("dev/", "dev-", "feature/", "fix/")):
            branch_env = "development"
            branch_ev = f"Git branch '{branch}' (canonical dev branch)"

        if branch_env:
            if ENV_SEVERITY.get(branch_env, 0) >= ENV_SEVERITY.get(context_env, 0):
                context_env = branch_env
                context_evidence = branch_ev

    # 3. Explicit command-line tokens (SÓ ESCALAM, NUNCA REBAIXAM)
    if cmd_line:
        cmd_env, cmd_evidence = extract_command_environment_tokens(cmd_line)
        if cmd_env and ENV_SEVERITY.get(cmd_env, 0) > ENV_SEVERITY.get(context_env, 0):
            return cmd_env, cmd_evidence

    return context_env, context_evidence
