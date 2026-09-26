"""
git.py - Analisador por tokens de comandos Git sensíveis para o Safety Gate do CEH.
Módulo normativo do PR-05c e PR-05d (Handoffs 019, 020 e 021).
Substitui regex de checkout, restore e switch, eliminando fontes duplas de verdade.
Fundamentação: gitglossary (pathspec), git 2.43 (git checkout|restore|switch --help).
"""
from __future__ import annotations

import posixpath

# Opções longas canônicas extraídas de git 2.43 (git checkout|restore|switch --help)
CHECKOUT_LONG_OPTS = (
    "--conflict", "--detach", "--force", "--guess", "--ignore-other-worktrees",
    "--ignore-skip-worktree-bits", "--merge", "--no-guess", "--no-overlay",
    "--no-overwrite-ignore", "--no-progress", "--no-recurse-submodules",
    "--no-track", "--orphan", "--ours", "--overlay", "--overwrite-ignore",
    "--patch", "--pathspec-file-nul", "--pathspec-from-file", "--progress",
    "--quiet", "--theirs", "--track"
)

RESTORE_LONG_OPTS = (
    "--conflict", "--ignore-skip-worktree-bits", "--ignore-unmerged", "--merge",
    "--no-overlay", "--no-progress", "--no-recurse-submodules", "--ours",
    "--overlay", "--patch", "--pathspec-file-nul", "--pathspec-from-file",
    "--progress", "--quiet", "--source", "--staged", "--theirs", "--worktree"
)

SWITCH_LONG_OPTS = (
    "--conflict", "--create", "--detach", "--discard-changes", "--force",
    "--force-create", "--guess", "--ignore-other-worktrees", "--merge",
    "--no-guess", "--no-progress", "--no-recurse-submodules", "--no-track",
    "--orphan", "--progress", "--quiet", "--track"
)

CHECKOUT_VAL_OPTS = ("--conflict", "--orphan", "--pathspec-from-file")
RESTORE_VAL_OPTS = ("--conflict", "--source", "--pathspec-from-file")
SWITCH_VAL_OPTS = ("--conflict", "--create", "--orphan", "--force-create")


def strip_quotes(s: str) -> str:
    """Remove aspas simples ou duplas externas de um token."""
    s = s.strip()
    if len(s) >= 2 and (
        (s.startswith('"') and s.endswith('"')) or
        (s.startswith("'") and s.endswith("'"))
    ):
        return s[1:-1]
    return s


def _is_broad_subpath(sub: str) -> bool:
    """Valida se um subcaminho normalizado alcança além ou possui glob/variável."""
    if not sub or sub in (".", "") or "$" in sub or sub.startswith("~"):
        return True
    norm = posixpath.normpath(sub)
    if norm in (".", "..") or norm.startswith("../"):
        return True
    return any(c in norm.split("/")[0] for c in ("*", "?", "["))


def is_broad_pathspec(pathspec: str) -> bool:
    """
    Determina se um pathspec individual possui amplitude destrutiva (V1, W3, W4, X1).
    Retorna True se o pathspec afetar todo o repositório, diretório atual ou além dele.
    Conforme gitglossary (pathspec short/long magic).
    """
    p = strip_quotes(pathspec)
    if not p:
        return False

    # W4: Variável ($) ou til (~) no pathspec é incerteza -> amplo / fail-closed
    if "$" in p or p.startswith("~"):
        return True

    # Pathspec com magia (iniciado por ':')
    if p.startswith(":"):
        # 1. Magia longa iniciada por ':('
        if p.startswith(":("):
            if any(p.startswith(m) for m in (":(exclude)", ":(top,exclude)", ":(exclude,top)")):
                return True
            if p.startswith(":(top)"):
                return _is_broad_subpath(p[len(":(top)"):].lstrip("/"))
            return True  # Qualquer outra magia longa -> fail-closed

        # 2. Magia curta (gitglossary): ':' seguido de mnemônicos ('/', '!', '^')
        idx = 1
        magic_chars = set()
        while idx < len(p) and p[idx] in ("/", "!", "^"):
            magic_chars.add(p[idx])
            idx += 1

        if idx < len(p) and p[idx] == ":":
            idx += 1

        # X1: Se contiver '!' ou '^' (exclusão/negação) -> amplo
        if "!" in magic_chars or "^" in magic_chars:
            return True

        # Se contiver '/' -> raiz do repositório (top)
        if "/" in magic_chars:
            return _is_broad_subpath(p[idx:].lstrip("/"))

        # Sem '/' nem exclusão, mas iniciado com ':'
        if _is_broad_subpath(p[idx:]):
            return True
        return idx == 1 and not (p[1:].startswith("/") or p[1:].isalnum() or p[1:2] in (".", "_", "-"))

    # Pathspec sem magia: absoluto -> amplo (fail-closed)
    if p.startswith("/") or posixpath.isabs(p) or p in ("*", "/*"):
        return True

    return _is_broad_subpath(p)


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
                opt_name = tok.split("=")[0]
                matches = [o for o in CHECKOUT_LONG_OPTS if o.startswith(opt_name)]
                # W2: abreviação só aperta
                if any(m == "--force" for m in matches):
                    has_force = True
                if any(m in ("--pathspec-from-file", "--pathspec-file-nul") for m in matches):
                    has_pathspec_file = True

                if "=" not in tok and any(m in CHECKOUT_VAL_OPTS for m in matches):
                    i = i + 2 if i + 1 < len(args) else i + 1
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

        # W1: Avaliar TODOS os posicionais, com ou sem '--'
        if any(is_broad_pathspec(p) for p in positionals):
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
                # W2: --staged só relaxa se for nome EXATO
                if tok == "--staged":
                    has_staged = True

                opt_name = tok.split("=")[0]
                matches = [o for o in RESTORE_LONG_OPTS if o.startswith(opt_name)]
                # W2: abreviação só aperta
                if any(m == "--worktree" for m in matches):
                    has_worktree = True
                if any(m in ("--pathspec-from-file", "--pathspec-file-nul") for m in matches):
                    has_pathspec_file = True

                if "=" not in tok and any(m in RESTORE_VAL_OPTS for m in matches):
                    i = i + 2 if i + 1 < len(args) else i + 1
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
                opt_name = tok.split("=")[0]
                matches = [o for o in SWITCH_LONG_OPTS if o.startswith(opt_name)]
                # W2: abreviação só aperta
                if any(m == "--force" for m in matches):
                    has_force = True
                if any(m == "--discard-changes" for m in matches):
                    has_discard = True
                if any(m == "--force-create" for m in matches):
                    has_force_create = True

                if "=" not in tok and any(m in SWITCH_VAL_OPTS for m in matches):
                    i = i + 2 if i + 1 < len(args) else i + 1
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
