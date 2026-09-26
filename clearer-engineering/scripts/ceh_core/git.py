"""
git.py - Analisador por tokens de comandos Git sensíveis para o Safety Gate do CEH.
Módulo normativo do PR-05c (Handoffs 019 e 020).
Substitui regex de checkout, restore e switch, eliminando fontes duplas de verdade.
Fundamentação: gitglossary (pathspec), git restore --help, git checkout/switch --help.
"""
from __future__ import annotations

import posixpath


def strip_quotes(s: str) -> str:
    """Remove aspas simples ou duplas externas de um token."""
    s = s.strip()
    if len(s) >= 2 and (
        (s.startswith('"') and s.endswith('"')) or
        (s.startswith("'") and s.endswith("'"))
    ):
        return s[1:-1]
    return s


def is_broad_pathspec(pathspec: str) -> bool:
    """
    Determina se um pathspec individual possui amplitude destrutiva (V1).
    Retorna True se o pathspec afetar todo o repositório, diretório atual ou além dele.
    """
    p = strip_quotes(pathspec)
    if not p:
        return False

    # Pathspec com magia (iniciado por ':')
    if p.startswith(":"):
        # Exclusão / negação (:!, :^, :(exclude)) -> amplo
        if p.startswith(":!") or p.startswith(":^") or p.startswith(":(exclude)"):
            return True

        # Raiz via :(top) ou :/
        for prefix in (":(top)", ":/"):
            if p.startswith(prefix):
                sub = p[len(prefix):].lstrip("/")
                if not sub or sub in (".", ""):
                    return True
                norm_sub = posixpath.normpath(sub)
                return norm_sub == "." or norm_sub == ".." or norm_sub.startswith("../")

        # Qualquer outra magia (glob, attr, icase, literal, desconhecida) -> fail-closed
        return True

    # Pathspec sem magia: absoluto -> amplo (fail-closed)
    if p.startswith("/") or posixpath.isabs(p) or p in ("*", "/*"):
        return True

    norm = posixpath.normpath(p)
    return norm == "." or norm == ".." or norm.startswith("../")


def _consume_opt_value(args: list[str], i: int, opt: str) -> int:
    """Avança o ponteiro consumindo a opção e seu valor se separado por espaço."""
    tok = args[i]
    if tok == opt and i + 1 < len(args):
        return i + 2
    return i + 1


def evaluate_git_subcommand(subcmd: str, args: list[str]) -> tuple[bool, str | None, str | None]:
    """
    Analisa checkout, restore e switch palavra por palavra (por tokens).
    Retorna (is_destructive, description, use_case_code).
    """
    if subcmd == "checkout":
        i, after_double_dash = 0, False
        positionals: list[str] = []
        has_force, has_dash_B, has_pathspec_file = False, False, False

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
                if tok == "--force":
                    has_force = True
                elif tok.startswith("--pathspec-from-file") or tok == "--pathspec-file-nul":
                    has_pathspec_file = True
                elif tok in ("--orphan", "--source", "--conflict"):
                    i = _consume_opt_value(args, i, tok)
                    continue
                i += 1
                continue
            if tok.startswith("-") and len(tok) > 1:
                if tok.startswith("-B"):
                    has_dash_B = True
                    i = _consume_opt_value(args, i, "-B") if tok == "-B" else i + 1
                    continue
                if tok.startswith("-b") or tok.startswith("-s"):
                    lead = tok[:2]
                    i = _consume_opt_value(args, i, lead) if tok == lead else i + 1
                    continue
                flags = tok[1:]
                if "f" in flags:
                    has_force = True
                if "B" in flags:
                    has_dash_B = True
                i += 1
                continue
            positionals.append(tok)
            i += 1

        if has_dash_B:
            return True, "Git checkout -B force recreating branch (equivalent to branch -D)", "GIT_HISTORY"
        if has_force:
            return True, "Git checkout with force flag discarding modifications", "GIT_HISTORY"
        if has_pathspec_file:
            return True, "Git checkout with --pathspec-from-file (opaque pathspec)", "GIT_HISTORY"

        target_specs = positionals if after_double_dash else (positionals[1:] if len(positionals) >= 2 else positionals)
        if target_specs and any(is_broad_pathspec(p) for p in target_specs):
            return True, "Git checkout discarding working tree files with broad pathspec", "GIT_HISTORY"
        return False, None, None

    elif subcmd == "restore":
        i, after_double_dash = 0, False
        positionals = []
        has_staged, has_worktree, has_pathspec_file = False, False, False

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
                if tok == "--staged":
                    has_staged = True
                elif tok == "--worktree":
                    has_worktree = True
                elif tok.startswith("--pathspec-from-file") or tok == "--pathspec-file-nul":
                    has_pathspec_file = True
                elif tok in ("--source", "--conflict"):
                    i = _consume_opt_value(args, i, tok)
                    continue
                i += 1
                continue
            if tok.startswith("-") and len(tok) > 1:
                if tok.startswith("-s"):
                    i = _consume_opt_value(args, i, "-s") if tok == "-s" else i + 1
                    continue
                flags = tok[1:]
                if "S" in flags:
                    has_staged = True
                if "W" in flags:
                    has_worktree = True
                i += 1
                continue
            positionals.append(tok)
            i += 1

        # V3: --staged isolado atua somente no índice e não afeta o worktree
        if has_staged and not has_worktree:
            return False, None, None
        if has_pathspec_file:
            return True, "Git restore with --pathspec-from-file (opaque pathspec)", "GIT_HISTORY"
        if any(is_broad_pathspec(p) for p in positionals):
            return True, "Git restore discarding working tree changes with broad pathspec", "GIT_HISTORY"
        return False, None, None

    elif subcmd == "switch":
        i = 0
        has_force, has_discard, has_force_create = False, False, False

        while i < len(args):
            tok = args[i]
            if tok == "--":
                break
            if tok.startswith("--"):
                if tok == "--force":
                    has_force = True
                elif tok == "--discard-changes":
                    has_discard = True
                elif tok == "--force-create" or tok.startswith("--force-create="):
                    has_force_create = True
                    i = _consume_opt_value(args, i, "--force-create") if tok == "--force-create" else i + 1
                    continue
                elif tok in ("--create", "--orphan"):
                    i = _consume_opt_value(args, i, tok)
                    continue
                i += 1
                continue
            if tok.startswith("-") and len(tok) > 1:
                if tok.startswith("-C"):
                    has_force_create = True
                    i = _consume_opt_value(args, i, "-C") if tok == "-C" else i + 1
                    continue
                if tok.startswith("-c"):
                    i = _consume_opt_value(args, i, "-c") if tok == "-c" else i + 1
                    continue
                flags = tok[1:]
                if "f" in flags:
                    has_force = True
                if "C" in flags:
                    has_force_create = True
                i += 1
                continue
            i += 1

        if has_force_create:
            return True, "Git switch -C force recreating branch (equivalent to branch -D)", "GIT_HISTORY"
        if has_force or has_discard:
            return True, "Git switch discarding uncommitted changes", "GIT_HISTORY"
        return False, None, None

    return False, None, None
