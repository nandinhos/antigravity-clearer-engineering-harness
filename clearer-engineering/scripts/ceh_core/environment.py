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

ENV_KEY_SEGMENTS = {"env", "environment", "stage", "profile", "context", "target"}
TARGET_OPTS = {"env", "environment", "stage", "profile", "context", "kube-context", "target"}


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
    Extrai sinais de ambiente na linha de comando por forma (Handoff 031 §3.1):
    1. Atribuição KEY=VAL (qualquer que seja o nome) na cabeça, após export ou após env.
    2. Argumento chave=valor sem hífen ou com -var/--set quando a chave contiver env/stage/target...
    3. Opções --X=valor, --X valor, -X=valor, -X valor (X in TARGET_OPTS).
    4. cd ou pushd: o diretório de contexto conta como sinal de ambiente.
    Retorna (env, evidence) do sinal mais severo, ou (None, None).
    """
    if not cmd_line:
        return None, None

    try:
        tokens = shlex.split(cmd_line, posix=True, comments=True)
    except Exception:
        tokens = cmd_line.split()

    found_envs: list[tuple[str, str]] = []
    n, idx = len(tokens), 0

    while idx < n:
        tok = tokens[idx]
        if tok == "export":
            idx += 1
            continue

        # 1. Atribuições KEY=VAL na cabeça ou após env
        if "=" in tok and not tok.startswith("-") and not tok.startswith("="):
            k, v = tok.split("=", 1)
            v_env = normalize_env(v)
            if v_env in ("production", "staging"):
                found_envs.append((v_env, f"Explicit assignment {k}={v}"))
            else:
                k_segs = set(s for s in re.split(r'[^\w]+', k.lower()) if s)
                if any(s in ENV_KEY_SEGMENTS for s in k_segs) and v_env != "development":
                    found_envs.append((v_env, f"Explicit key=value argument {k}={v}"))
            idx += 1
            continue

        # 2. Comando transparente 'env'
        if tok == "env":
            idx += 1
            while idx < n:
                c = tokens[idx]
                if c.startswith("-"):
                    idx += 1
                elif "=" in c and not c.startswith("="):
                    k, v = c.split("=", 1)
                    v_env = normalize_env(v)
                    if v_env in ("production", "staging"):
                        found_envs.append((v_env, f"Explicit env assignment {k}={v}"))
                    idx += 1
                else:
                    break
            continue

        # 3. Flags de variáveis: -var chave=valor ou --set chave=valor
        if tok in ("-var", "--set") and idx + 1 < n:
            arg = tokens[idx + 1]
            if "=" in arg and not arg.startswith("="):
                k, v = arg.split("=", 1)
                k_segs = set(s for s in re.split(r'[^\w]+', k.lower()) if s)
                if any(s in ENV_KEY_SEGMENTS for s in k_segs):
                    v_env = normalize_env(v)
                    if v_env in ("production", "staging"):
                        found_envs.append((v_env, f"Explicit variable flag {tok} {arg}"))
            idx += 2
            continue

        # 4. Opções com valor: --X=valor, --X valor, -X=valor, -X valor (X in TARGET_OPTS)
        opt_name, opt_val = None, None
        if tok.startswith("--") and len(tok) > 2:
            clean = tok[2:]
            opt_name, opt_val = clean.split("=", 1) if "=" in clean else (clean, tokens[idx + 1] if idx + 1 < n else None)
        elif tok.startswith("-") and len(tok) > 1 and not tok.startswith("--"):
            clean = tok[1:]
            opt_name, opt_val = clean.split("=", 1) if "=" in clean else (clean, tokens[idx + 1] if idx + 1 < n else None)

        if opt_name and opt_name.lower() in TARGET_OPTS and opt_val is not None:
            v_env = normalize_env(opt_val)
            if v_env in ("production", "staging"):
                found_envs.append((v_env, f"Explicit option {tok} {opt_val}"))
                if "=" not in tok:
                    idx += 2
                    continue

        # 5. cd / pushd: diretório de trabalho conta como contexto que só escala
        if tok in ("cd", "pushd") and idx + 1 < n:
            cd_env = normalize_env(tokens[idx + 1])
            if cd_env in ("production", "staging"):
                found_envs.append((cd_env, f"Working directory context {tok} {tokens[idx + 1]}"))
            idx += 2
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
