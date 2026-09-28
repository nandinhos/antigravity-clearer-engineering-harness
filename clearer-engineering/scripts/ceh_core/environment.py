"""environment.py - Detecção e normalização de ambientes de execução do CEH."""
from __future__ import annotations
import os, re, shlex, subprocess
from pathlib import Path

from ceh_core.normalize import (
    STAGING_SEGMENTS,
    normalize_env,
    normalize_path,
    classify_branch_name,
    strip_quotes,
    strip_all_quotes,
    tokenize_command,
)

PROD_SEGMENTS = set(["prod", "production", "prd", "live"]) | {"preprod"}

ENV_SEVERITY = {"development": 0, "staging": 1, "production": 2}
ENV_KEY_SEGMENTS = {"env", "environment", "stage", "profile", "context", "target"}
TARGET_OPTS = {"env", "environment", "stage", "profile", "context", "kube-context", "target"}

_BRANCH_CACHE: dict[str, str | None] = {}
_REPO_ROOT_CACHE: dict[str, Path | None] = {}

def clear_environment_caches() -> None:
    _BRANCH_CACHE.clear(); _REPO_ROOT_CACHE.clear()

def is_unresolved_cd_target(target: str) -> bool:
    """Verifica se o alvo de cd/pushd é não resolvível/dinâmico (Invariante 7)."""
    t = target.strip().strip('"').strip("'")
    if t in ("-", "~", ""): return True
    return bool(re.search(r'\$[\w{]|~', t.replace("${PWD}", "").replace("$PWD", "")))

def _parse_target_path(raw: str, cwd: Path) -> tuple[Path | None, bool]:
    clean = raw.strip("'\"")
    if is_unresolved_cd_target(clean): return None, True
    p = Path(clean) if Path(clean).is_absolute() else Path(normalize_path(cwd / Path(clean), resolve_home=False))
    return (p.parent if p.name == ".git" else p), False

def _extract_git_branch_arg(args: list[str]) -> str | None:
    for i, a in enumerate(args):
        if a in ("-b", "-B", "-c", "-C", "--orphan") and i + 1 < len(args): return args[i + 1]
        if any(a.startswith(p) for p in ("-b=", "-B=", "-c=", "-C=")): return a.split("=", 1)[1]
        if not a.startswith("-") and a != "--": return a
    return None

def extract_command_environment_tokens(cmd_line: str) -> tuple[str | None, str | None]:
    """Extrai sinais de ambiente na linha de comando por forma (Handoff 031 §3.1, Handoff 034)."""
    if not cmd_line: return None, None
    tokens = tokenize_command(cmd_line, posix=True, comments=True)

    found: list[tuple[str, str]] = []
    n, idx, paren_depth = len(tokens), 0, 0
    while idx < n:
        tok = tokens[idx]
        if tok == "export": idx += 1; continue
        if "(" in tok and not tok.startswith(":( "): paren_depth += tok.count("(")
        if ")" in tok: paren_depth = max(0, paren_depth - tok.count(")")) ; idx += 1; continue
        if paren_depth > 0: idx += 1; continue
        if "=" in tok and not tok.startswith(("-", "=")):
            k, v = tok.split("=", 1)
            v_env = normalize_env(v)
            if v_env in ("production", "staging"): found.append((v_env, f"Explicit assignment {k}={v}"))
            elif k.lower() in ("git_dir", "git_work_tree") and (is_unresolved_cd_target(v) or normalize_env(v) == "production"):
                found.append(("production", f"Explicit git target {k}={v}"))
            elif any(s in ENV_KEY_SEGMENTS for s in re.split(r'[^\w]+', k.lower()) if s) and v_env != "development":
                found.append((v_env, f"Explicit key=value argument {k}={v}"))
            idx += 1; continue
        if tok == "env":
            idx += 1
            while idx < n:
                c = tokens[idx]
                if c in ("-C", "--chdir") and idx + 1 < n:
                    arg_c = tokens[idx + 1]; idx += 2
                    if is_unresolved_cd_target(arg_c) or normalize_env(arg_c) == "production": found.append(("production", f"Explicit env {c}"))
                elif any(c.startswith(opt) for opt in ("-C", "--chdir=")):
                    arg_c = c.split("=", 1)[1] if "=" in c else c[2:]; idx += 1
                    if is_unresolved_cd_target(arg_c) or normalize_env(arg_c) == "production": found.append(("production", f"Explicit env {c}"))
                elif "=" in c and not c.startswith("="):
                    k, v = c.split("=", 1)
                    v_env = normalize_env(v)
                    if v_env in ("production", "staging"): found.append((v_env, f"Explicit env assignment {k}={v}"))
                    elif k.lower() in ("git_dir", "git_work_tree") and (is_unresolved_cd_target(v) or normalize_env(v) == "production"):
                        found.append(("production", f"Explicit env git target {k}={v}"))
                    idx += 1
                elif c.startswith("-"): idx += 1
                else: break
            continue
        if tok in ("-var", "--set") and idx + 1 < n:
            arg = tokens[idx + 1]
            if "=" in arg and not arg.startswith("="):
                k, v = arg.split("=", 1)
                if any(s in ENV_KEY_SEGMENTS for s in re.split(r'[^\w]+', k.lower()) if s):
                    v_env = normalize_env(v)
                    if v_env in ("production", "staging"): found.append((v_env, f"Explicit variable flag {tok} {arg}"))
            idx += 2; continue
        opt_name, opt_val = None, None
        if tok.startswith("-") and len(tok) > 1:
            clean = tok[2:] if tok.startswith("--") else tok[1:]
            opt_name, opt_val = clean.split("=", 1) if "=" in clean else (clean, tokens[idx + 1] if idx + 1 < n else None)
        if opt_name and opt_name.lower() in TARGET_OPTS and opt_val is not None:
            v_env = normalize_env(opt_val)
            if v_env in ("production", "staging"):
                found.append((v_env, f"Explicit option {tok} {opt_val}"))
                if "=" not in tok: idx += 2; continue
        if tok in ("cd", "pushd"):
            target = tokens[idx + 1] if (idx + 1 < n and not tokens[idx + 1].startswith(("-", ";", "&", "|"))) else "~"
            cd_env = normalize_env(target)
            if cd_env in ("production", "staging"): found.append((cd_env, f"Working directory context {tok} {target}"))
            elif is_unresolved_cd_target(target): found.append(("production", f"Unresolved cd target {tok} {target} (Invariante 7)"))
            idx += 2 if (idx + 1 < n and not tokens[idx + 1].startswith(("-", ";", "&", "|"))) else 1; continue
        idx += 1

    return max(found, key=lambda item: ENV_SEVERITY.get(item[0], 0)) if found else (None, None)

def get_git_branch(target_dir: Path | str | None = None) -> str | None:
    key = normalize_path(target_dir, resolve_home=False) if target_dir else str(Path.cwd().resolve())
    if key in _BRANCH_CACHE: return _BRANCH_CACHE[key]
    try:
        p = Path(key)
        cwd_p = p.resolve() if p.exists() else p
        res = subprocess.run(["git", "branch", "--show-current"], cwd=cwd_p, capture_output=True, text=True, timeout=2)
        if res.returncode == 0 and res.stdout.strip():
            _BRANCH_CACHE[key] = res.stdout.strip(); return _BRANCH_CACHE[key]
    except Exception: pass
    _BRANCH_CACHE[key] = None; return None

def find_repo_root(start_dir: Path) -> Path | None:
    key = normalize_path(start_dir, resolve_home=False)
    if key in _REPO_ROOT_CACHE: return _REPO_ROOT_CACHE[key]
    current = Path(key)
    try:
        if current.exists():
            current = current.resolve()
    except Exception:
        pass
    for parent in [current] + list(current.parents):
        if (parent / ".git").exists():
            _REPO_ROOT_CACHE[key] = parent; return parent
    _REPO_ROOT_CACHE[key] = None; return None

def resolve_target_context(
    tokens: list[str],
    current_cwd: Path,
    persistent_repo: Path | None = None,
) -> tuple[Path, Path | None, bool, bool, str | None, list[str]]:
    """Identifica diretório, repositório alvo e modificadores de ambiente unificados (H033/H034)."""
    if not tokens: return current_cwd, persistent_repo, False, False, None, tokens
    is_unresolved, is_persistent, context_env = False, False, None
    target_dir, target_repo = None, persistent_repo
    rem = list(tokens)

    while rem and rem[0] == "{": rem.pop(0)
    while rem and rem[-1] == "}": rem.pop()
    if not rem: return current_cwd, persistent_repo, False, False, None, []

    first = rem[0]
    if first in ("cd", "pushd"):
        is_persistent = True
        raw = rem[1] if (len(rem) > 1 and not rem[1].startswith(("-", ";", "&", "|"))) else "~"
        p, unres = _parse_target_path(raw, current_cwd)
        if unres: is_unresolved = True
        elif p and p.is_dir(): target_dir = p
        return target_dir or current_cwd, target_repo, is_unresolved, is_persistent, None, rem

    if first == "export":
        for tok in rem[1:]:
            if tok.startswith(("GIT_DIR=", "GIT_WORK_TREE=")):
                is_persistent = True
                p, unres = _parse_target_path(tok.split("=", 1)[1], current_cwd)
                if unres: is_unresolved = True
                elif p: target_repo = target_dir = find_repo_root(p) or p
        return target_dir or current_cwd, target_repo, is_unresolved, is_persistent, None, rem

    if first == "git" and len(rem) > 1 and rem[1] in ("switch", "checkout"):
        b_cand = _extract_git_branch_arg(rem[2:])
        b_env = classify_branch_name(b_cand) if b_cand else None
        if b_env: context_env, is_persistent = b_env, True
        return current_cwd, target_repo, is_unresolved, is_persistent, context_env, rem

    if first in ("source", ".") and len(rem) > 1:
        f_env = normalize_env(Path(rem[1].strip("'\"")).name)
        if f_env in ("production", "staging"): context_env, is_persistent = f_env, True
        return current_cwd, target_repo, is_unresolved, is_persistent, context_env, rem

    if first in ("cp", "mv", "ln") and len(rem) > 2:
        dest = rem[-1].strip("'\"")
        if dest == ".env" or dest.endswith(("/.env", ".env")):
            for orig in rem[1:-1]:
                f_env = normalize_env(Path(orig.strip("'\"")).name)
                if f_env in ("production", "staging"): context_env, is_persistent = f_env, True; break
        return current_cwd, target_repo, is_unresolved, is_persistent, context_env, rem

    idx, n = 0, len(rem)
    while idx < n:
        tok = rem[idx]
        if "=" in tok and not tok.startswith(("-", "=")):
            k, v = tok.split("=", 1)
            if k in ("GIT_DIR", "GIT_WORK_TREE"):
                p, unres = _parse_target_path(v, current_cwd)
                if unres: is_unresolved = True
                elif p: target_repo = target_dir = find_repo_root(p) or p
            idx += 1; continue
        if tok in ("env", "sudo", "doas"):
            idx += 1
            while idx < n:
                c = rem[idx]
                if c in ("-C", "-D", "--chdir") and idx + 1 < n:
                    p, unres = _parse_target_path(rem[idx + 1], current_cwd)
                    if unres: is_unresolved = True
                    elif p: target_dir = p
                    idx += 2
                elif any(c.startswith(opt) for opt in ("-C", "-D", "--chdir=")):
                    val = c.split("=", 1)[1] if "=" in c else c[2:]
                    p, unres = _parse_target_path(val, current_cwd)
                    if unres: is_unresolved = True
                    elif p: target_dir = p
                    idx += 1
                elif c.startswith(("GIT_DIR=", "GIT_WORK_TREE=")):
                    p, unres = _parse_target_path(c.split("=", 1)[1], current_cwd)
                    if unres: is_unresolved = True
                    elif p: target_repo = target_dir = find_repo_root(p) or p
                    idx += 1
                elif c.startswith("-") or ("=" in c and not c.startswith("=")): idx += 1
                else: break
            continue
        break

    clean_tokens = rem[idx:] if idx > 0 and idx < n else rem
    eff_cwd = target_dir or (target_repo if target_repo else current_cwd)
    return eff_cwd, target_repo, is_unresolved, is_persistent, context_env, clean_tokens

def detect_environment(
    explicit_env: str | None = None,
    cmd_line: str = "",
    target_dir: Path | str | None = None,
) -> tuple[str, str]:
    """Detects target environment with verifiable evidence (parameter, context, tokens)."""
    if explicit_env: return normalize_env(explicit_env), f"Explicit parameter (--env {explicit_env})"

    context_env = "development"
    context_evidence = "Default workspace fallback (development/local)"
    found_var = False
    for var in ["CEH_ENV", "APP_ENV", "NODE_ENV", "ENVIRONMENT", "ENV", "STAGE"]:
        val = os.environ.get(var)
        if val:
            context_env, context_evidence = normalize_env(val), f"Environment variable {var}={val}"
            found_var = True; break

    if not found_var:
        try:
            if target_dir:
                raw_p = Path(normalize_path(target_dir, resolve_home=False))
                try:
                    curr = raw_p.resolve() if raw_p.exists() else raw_p
                except Exception:
                    curr = raw_p
            else:
                curr = Path.cwd().resolve()
            for d in [curr, *curr.parents]:
                if (d / ".env.production").is_file(): context_env, context_evidence = "production", f"Configuration file {d / '.env.production'}"; break
                if (d / ".env.staging").is_file() or (d / ".env.homolog").is_file(): context_env, context_evidence = "staging", f"Configuration file in {d}"; break
                f = d / ".env"
                if f.is_file():
                    for l in f.read_text(encoding="utf-8", errors="ignore").splitlines():
                        if "=" in l and not l.strip().startswith("#"):
                            k, v = [x.strip().strip("\"'") for x in l.split("=", 1)]
                            if k in ["CEH_ENV", "APP_ENV", "NODE_ENV", "ENVIRONMENT", "ENV", "STAGE"]:
                                context_env, context_evidence = normalize_env(v), f"File .env ({k}={v})"; found_var = True; break
                    if found_var: break
                if (d / ".git").exists(): break
        except Exception: pass

    branch = get_git_branch(target_dir)
    if branch:
        segments = set(s for s in re.split(r'[^\w]+', branch.lower()) if s)
        b_env, b_ev = None, None
        if any(s in ["main", "master", "production", "prod"] for s in segments) or any(s in PROD_SEGMENTS for s in segments):
            b_env, b_ev = "production", f"Git branch '{branch}' (canonical production branch)"
        elif any(s in STAGING_SEGMENTS for s in segments): b_env, b_ev = "staging", f"Git branch '{branch}' (canonical staging branch)"
        elif any(s in ["dev", "develop"] for s in segments) or branch.lower().startswith(("dev/", "dev-", "feature/", "fix/")):
            b_env, b_ev = "development", f"Git branch '{branch}' (canonical dev branch)"
        if b_env and ENV_SEVERITY.get(b_env, 0) >= ENV_SEVERITY.get(context_env, 0):
            context_env, context_evidence = b_env, b_ev

    if cmd_line:
        cmd_env, cmd_evidence = extract_command_environment_tokens(cmd_line)
        if cmd_env and ENV_SEVERITY.get(cmd_env, 0) > ENV_SEVERITY.get(context_env, 0):
            return cmd_env, cmd_evidence

    return context_env, context_evidence
