"""
push.py - Analisador por tokens de git push e validação do Pre-Push CI Gate.
Normativo do PR-08 (Handoff 035, Onda 2 - G7).
"""
from __future__ import annotations

import json
import shlex
import subprocess
from pathlib import Path
from typing import Any

from ceh_core.environment import find_repo_root
from ceh_core.normalize import normalize_path, resolve_long_options, tokenize_command

# Opções canônicas de git push extraídas de git push --help
PUSH_LONG_OPTS = (
    "--all", "--mirror", "--tags", "--follow-tags", "--atomic",
    "--dry-run", "--porcelain", "--progress", "--prune", "--quiet",
    "--verbose", "--force", "--force-with-lease", "--force-if-includes",
    "--delete", "--set-upstream", "--no-verify", "--push-option",
    "--receive-pack", "--exec", "--repo", "--signed", "--no-signed"
)

PUSH_VAL_LONG_OPTS = ("--push-option", "--receive-pack", "--exec", "--repo")


def extract_push_args_from_cmd(cmd_line: str, base_cwd: Path | None = None) -> tuple[Path | None, list[str]]:
    """Extrai diretório alvo (via -C) e argumentos do subcomando push a partir de cmd_line."""
    tokens = tokenize_command(cmd_line, posix=True)

    cwd = Path(normalize_path(base_cwd, resolve_home=False)) if base_cwd else Path.cwd().resolve()
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t == "git":
            i += 1
            continue
        if t == "-C" and i + 1 < len(tokens):
            cwd = Path(normalize_path(cwd / tokens[i + 1], resolve_home=False))
            i += 2
            continue
        if t.startswith("-C") and len(t) > 2:
            cwd = Path(normalize_path(cwd / t[2:], resolve_home=False))
            i += 1
            continue
        if t == "push":
            return cwd, tokens[i + 1:]
        i += 1
    return cwd, []


def parse_git_push_tokens(args: list[str]) -> tuple[str | None, list[str], dict[str, Any]]:
    """
    Analisa argumentos de git push por tokens e resolução de opções longas por prefixo.
    Retorna (remote, refspecs, flags).
    """
    has_all, has_mirror, has_tags = False, False, False
    has_delete, has_force = False, False
    blocked_opt: str | None = None
    explicit_repo: str | None = None

    positionals: list[str] = []
    i = 0
    after_double_dash = False

    while i < len(args):
        tok = args[i]
        if after_double_dash:
            positionals.append(tok)
            i += 1
            continue
        if tok == "--":
            after_double_dash = True
            i += 1
            continue
        if tok.startswith("--"):
            opt_name = tok.split("=")[0]
            matches = resolve_long_options(tok, PUSH_LONG_OPTS)
            if any(m == "--all" for m in matches):
                has_all = True
                blocked_opt = opt_name
            if any(m == "--mirror" for m in matches):
                has_mirror = True
                blocked_opt = opt_name
            if any(m == "--tags" for m in matches):
                has_tags = True
                blocked_opt = opt_name
            if any(m == "--delete" for m in matches):
                has_delete = True
            if any(m in ("--force", "--force-with-lease", "--force-if-includes") for m in matches):
                has_force = True
            if any(m == "--repo" for m in matches):
                if "=" in tok:
                    explicit_repo = tok.split("=", 1)[1]
                elif i + 1 < len(args):
                    explicit_repo = args[i + 1]
                    i += 2
                    continue
            if "=" not in tok and any(m in PUSH_VAL_LONG_OPTS for m in matches):
                i = i + 2 if i + 1 < len(args) else i + 1
                continue
            i += 1
            continue

        if tok.startswith("-") and len(tok) > 1:
            flags_str = tok[1:]
            if "f" in flags_str:
                has_force = True
            if "d" in flags_str:
                has_delete = True
            if tok.startswith("-o") and tok != "-o":
                i += 1
                continue
            elif tok == "-o":
                i = i + 2 if i + 1 < len(args) else i + 1
                continue
            i += 1
            continue

        positionals.append(tok)
        i += 1

    if explicit_repo:
        remote = explicit_repo
        refspecs = positionals
    else:
        if not positionals:
            remote = None
            refspecs = []
        elif len(positionals) == 1:
            remote = positionals[0]
            refspecs = []
        else:
            remote = positionals[0]
            refspecs = positionals[1:]

    flags = {
        "all": has_all,
        "mirror": has_mirror,
        "tags": has_tags,
        "delete": has_delete,
        "force": has_force,
        "blocked_opt": blocked_opt,
    }
    return remote, refspecs, flags


def resolve_commit_hash(repo_root: Path, rev: str) -> str | None:
    """Resolve uma revisão para commit hash no repositório alvo via git rev-parse."""
    try:
        res = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "--verify", f"{rev}^{{commit}}"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        if res.returncode == 0:
            return res.stdout.strip()
    except Exception:
        pass
    return None


def check_pre_push_ci_gate(
    cmd: str,
    target_dir: Path | None = None,
    git_args: list[str] | None = None,
) -> tuple[str, str] | None:
    """
    Zero-Tolerance Pipeline Red Pre-Push Gate (PR-08 / G7):
    Em repositórios com CI (.github/workflows ou .gitlab-ci.yml), valida que todos
    os commits associados aos refspecs de envio possuem certificado aprovado em .ceh/last-ci-run.json.
    """
    if target_dir is None or git_args is None:
        extracted_cwd, extracted_args = extract_push_args_from_cmd(cmd, base_cwd=target_dir)
        base_dir = target_dir or extracted_cwd
        push_args = git_args if git_args is not None else extracted_args
    else:
        base_dir = target_dir
        push_args = git_args

    repo_root = find_repo_root(base_dir) if base_dir.exists() else base_dir
    if not repo_root or not repo_root.exists():
        return None

    # Verifica se o repositório possui fluxos de CI
    ci_workflows_dir = repo_root / ".github" / "workflows"
    has_github_ci = ci_workflows_dir.is_dir() and any(
        list(ci_workflows_dir.glob("*.yml")) + list(ci_workflows_dir.glob("*.yaml"))
    )
    has_gitlab_ci = (repo_root / ".gitlab-ci.yml").is_file()

    if not (has_github_ci or has_gitlab_ci):
        return None  # Sem CI configurada; permite fluxo normal

    cert_file = repo_root / ".ceh" / "last-ci-run.json"
    if not cert_file.is_file():
        return "deny", "[CEH PRE-PUSH CI GATE] ⛔ Push bloqueado: NENHUMA execução prévia comprovada em '.github/workflows'."

    try:
        data = json.loads(cert_file.read_text(encoding="utf-8"))
        exit_code = data.get("exit_code")
        status = data.get("status", "FAIL")
        cert_commit = data.get("commit_hash", "")
        cmd_executed = str(data.get("command", "")).strip()

        if not cert_commit or cert_commit == "untracked":
            return "deny", "[CEH PRE-PUSH CI GATE] ⛔ Push bloqueado: Certificado inválido (commit_hash ausente ou não rastreado)."

        if exit_code != 0 or status != "PASS":
            return "deny", f"[CEH PRE-PUSH CI GATE] ⛔ Push bloqueado: suíte FALHOU (Exit Code: {exit_code}, Status: {status}). Comando: {cmd_executed}"

        if data.get("canonical_verified") is not True:
            return "deny", f"[CEH PRE-PUSH CI GATE] ⛔ Push bloqueado: O certificado não comprova execução da suíte canônica. Comando: '{cmd_executed}'"

        remote, refspecs, flags = parse_git_push_tokens(push_args)

        if flags.get("all") or flags.get("mirror") or flags.get("tags"):
            opt = flags.get("blocked_opt") or "--all/--mirror/--tags"
            return "deny", f"[CEH PRE-PUSH CI GATE] ⛔ Push bloqueado: opção '{opt}' não permitida em repositório com CI (não é possível certificar commits individuais)."

        if flags.get("delete"):
            return "allow", "Pre-Push CI Gate validado: deleção remota não envia novos commits."

        # Se refspecs foram especificados
        src_checked = False
        for ref in refspecs:
            clean = ref.lstrip("+")
            if clean.startswith(":"):
                continue  # Deleção remota (:dst), não envia commit
            src = clean.split(":", 1)[0] if ":" in clean else clean
            if not src:
                continue

            src_checked = True
            resolved = resolve_commit_hash(repo_root, src)
            if resolved is None:
                return "deny", f"[CEH PRE-PUSH CI GATE] ⛔ Push bloqueado: refspec '{ref}' não pôde ser resolvido para um commit válido."
            if resolved != cert_commit:
                return "deny", f"[CEH PRE-PUSH CI GATE] ⛔ Push bloqueado por desatualização de testes: refspec '{ref}' ({resolved[:7]}) != Cert ({cert_commit[:7]})."

        # Sem refspec ou apenas deleções: valida HEAD atual
        if not src_checked and not refspecs:
            head_commit = resolve_commit_hash(repo_root, "HEAD")
            if head_commit is None:
                return "deny", "[CEH PRE-PUSH CI GATE] ⛔ Push bloqueado: HEAD não pôde ser resolvido para um commit válido."
            if head_commit != cert_commit:
                return "deny", f"[CEH PRE-PUSH CI GATE] ⛔ Push bloqueado por desatualização de testes: HEAD ({head_commit[:7]}) != Cert ({cert_commit[:7]})."

    except Exception as e:
        return "deny", f"[CEH PRE-PUSH CI GATE] ⛔ Push bloqueado: Certificado de CI ilegível ({str(e)})."

    return "allow", "Pre-Push CI Gate validado: suíte canônica aprovada para o commit atual."


def is_remote_deletion(push_args: list[str]) -> tuple[bool, str | None]:
    """
    Verifica se a invocação de git push é uma deleção remota (:dst, +:dst, --delete dst, -d dst).
    Retorna (is_deletion, description).
    """
    remote, refspecs, flags = parse_git_push_tokens(push_args)
    if flags.get("delete"):
        target_branch = refspecs[0] if refspecs else (remote if remote and remote != "origin" else "branch")
        return True, f"Deleting remote Git branch via delete flag ({target_branch})"
    for ref in refspecs:
        clean = ref.lstrip("+")
        if clean.startswith(":") and len(clean) > 1:
            dst = clean[1:]
            return True, f"Deleting remote Git branch via refspec '{ref}' ({dst})"
    return False, None
