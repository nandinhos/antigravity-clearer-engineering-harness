#!/usr/bin/env python3
"""
ceh_core/subcommand.py — Subcommand-level evaluation.
Nucleo agnostico de host: ZERO referencias a formatos de host.
"""
from __future__ import annotations

import os
import re
import shlex
from pathlib import Path
from typing import Any, Callable

from ceh_core.rules import (
    CATASTROPHIC_PATTERNS,
    SAFE_DEV_PATTERNS,
    USE_CASE_DESTRUCTIVE_PATTERNS,
    is_cert_tampering,
)
from ceh_core.lexer import (
    normalize_command_for_evaluation,
    resolve_command_head,
    substitute_positional_args,
)
from ceh_core.normalize import tokenize_command
from ceh_core.environment import (
    detect_environment,
    ENV_SEVERITY,
)
from ceh_core.rm import evaluate_rm_command
from ceh_core.push import check_pre_push_ci_gate, is_remote_deletion, parse_git_push_tokens
from ceh_core.git import evaluate_git_subcommand
from ceh_core.git_invocation import resolve_git_invocation
from ceh_core.find import evaluate_find_command
from ceh_core.interpreters import evaluate_interpreter_command


def extract_shell_c_command(cmd_line: str) -> str | None:
    """Extrai o comando executado via flag -c em shells conhecidos (AD2, Handoff 028)."""
    tokens = tokenize_command(cmd_line, posix=True)
    if not tokens:
        return None

    idx, _ = resolve_command_head(tokens)
    if idx >= len(tokens):
        return None

    base = os.path.basename(tokens[idx])
    SHELL_NAMES = {
        "sh", "bash", "zsh", "dash", "ksh", "mksh", "ash", "fish", "csh", "tcsh"
    }
    if base == "busybox" and idx + 1 < len(tokens) and os.path.basename(tokens[idx + 1]) in SHELL_NAMES:
        idx += 1
        base = os.path.basename(tokens[idx])

    if base in SHELL_NAMES:
        i = idx + 1
        while i < len(tokens):
            tok = tokens[i]
            if (tok == "-c" or (base == "fish" and tok == "--command")) and i + 1 < len(tokens):
                script = tokens[i + 1]
                extra_args = tokens[i + 2:]
                return substitute_positional_args(script, extra_args)
            if base == "fish" and tok.startswith("--command="):
                script = tok.split("=", 1)[1]
                extra_args = tokens[i + 1:]
                return substitute_positional_args(script, extra_args)
            if tok.startswith("-") and not tok.startswith("--") and "c" in tok:
                pos = tok.rfind("c")
                if pos == len(tok) - 1 and i + 1 < len(tokens):
                    script = tokens[i + 1]
                    extra_args = tokens[i + 2:]
                    return substitute_positional_args(script, extra_args)
                elif pos < len(tok) - 1:
                    script = tok[pos + 1:]
                    extra_args = tokens[i + 1:]
                    return substitute_positional_args(script, extra_args)
            i += 1
    return None


def evaluate_subcommand(
    subcmd: str,
    env: str,
    env_evidence: str,
    base_cwd: Path | str | None = None,
    explicit_env: str | None = None,
    depth: int = 0,
    scan_suffixes: bool = True,
    eval_command_fn: Callable[..., tuple[str, str, str, str]] | None = None,
    build_destructive_fn: Callable[..., tuple[str, str, str, str]] | None = None,
    max_severity_fn: Callable[..., tuple[str, str, str, str]] | None = None,
) -> tuple[str, str, str, str]:
    """
    Avalia um subcomando atomico contra as politicas de seguranca do CEH.
    Retorna (decision, reason, detected_env, use_case).
    """
    if depth > 3:
        return (
            "deny",
            f"[CEH SAFETY GATE - FAIL-CLOSED] Limite de profundidade de recursão excedido (depth={depth} > 3).",
            env,
            "CATASTROPHIC",
        )

    sub_raw = subcmd.strip()
    sub_eval = re.sub(r"^\s*rtk(?:\s+proxy)?\s+", "", sub_raw)
    sub_norm = normalize_command_for_evaluation(sub_eval)

    candidate: tuple[str, str, str, str] | None = None
    sub_tokens = tokenize_command(sub_raw, posix=True)

    if sub_tokens and eval_command_fn is not None:
        h_idx, string_exec = resolve_command_head(sub_tokens)
        if string_exec is not None:
            return eval_command_fn(
                string_exec,
                explicit_env=explicit_env,
                base_cwd=base_cwd,
                depth=depth + 1
            )

        if scan_suffixes:
            ANALYZED_HEADS = {
                "rm", "git", "find",
                "sh", "bash", "zsh", "dash", "ksh", "mksh", "ash", "fish", "csh", "tcsh",
                "node", "nodejs", "perl", "ruby", "php", "awk", "gawk", "mawk", "nawk",
                "deno", "bun", "eval", "su", "watch"
            }
            for j in range(1, len(sub_tokens)):
                base_t = os.path.basename(sub_tokens[j])
                if (
                    base_t in ANALYZED_HEADS
                    or base_t.startswith("python")
                    or base_t.startswith("php")
                ):
                    suffix_cmd = shlex.join(sub_tokens[j:])
                    s_res = eval_command_fn(
                        suffix_cmd,
                        explicit_env=explicit_env,
                        base_cwd=base_cwd,
                        depth=depth,
                        scan_suffixes=False,
                    )
                    if s_res[3] == "CATASTROPHIC":
                        return s_res
                    if max_severity_fn is not None:
                        candidate = max_severity_fn(candidate, s_res) if candidate else s_res
                    else:
                        candidate = s_res

    # 0. Protecao de Integridade do Certificado de CI (G9, PR-10) — executa ANTES de qualquer desembrulho
    is_tampering, cert_reason = is_cert_tampering(sub_eval)
    if is_tampering:
        return ("deny", cert_reason, env, "CERTIFICATE_INTEGRITY")

    shell_inner = extract_shell_c_command(sub_raw)
    if shell_inner and eval_command_fn is not None:
        return eval_command_fn(
            shell_inner,
            explicit_env=explicit_env,
            base_cwd=base_cwd,
            depth=depth + 1,
            env_floor=env,
        )

    # 0. Avaliacao Estrita de 'rm' por tokens (G1, G4 e PR-04b)
    rm_res = evaluate_rm_command(sub_norm, env, env_evidence=env_evidence, base_cwd=base_cwd)
    if rm_res is not None:
        return rm_res

    # 0.1 Avaliacao Estrita de 'find' por tokens com desembrulho de -exec (G5, PR-06/PR-06b)
    if eval_command_fn is not None:
        find_res = evaluate_find_command(
            sub_eval, env, env_evidence=env_evidence, base_cwd=base_cwd, eval_fn=eval_command_fn, depth=depth
        )
        if find_res is not None:
            if find_res[3] == "CATASTROPHIC":
                return find_res
            candidate = find_res

        # 0.2 Avaliacao Estrita de interpretadores por tokens com desembrulho recursivo (G5, PR-06/PR-06b)
        interp_res = evaluate_interpreter_command(
            sub_eval, env, env_evidence=env_evidence, base_cwd=base_cwd, eval_fn=eval_command_fn, depth=depth
        )
        if interp_res is not None:
            if interp_res[3] == "CATASTROPHIC":
                return interp_res
            if max_severity_fn is not None:
                candidate = max_severity_fn(candidate, interp_res) if candidate else interp_res
            else:
                candidate = interp_res

    def finalize(decision: tuple[str, str, str, str]) -> tuple[str, str, str, str]:
        if candidate is not None and max_severity_fn is not None:
            return max_severity_fn(decision, candidate)
        return decision

    # 1. Catastrophic Blocks: DENY has absolute priority in ANY environment
    for pattern, reason in CATASTROPHIC_PATTERNS:
        if (
            re.search(pattern, sub_eval, re.IGNORECASE)
            or re.search(pattern, sub_norm, re.IGNORECASE)
            or re.search(pattern, sub_raw, re.IGNORECASE)
        ):
            return "deny", f"[CEH CATASTROPHIC BLOCK] {reason}", env, "CATASTROPHIC"

    # 2. Resolucao Canonica de Git (R5 + G3)
    is_git, git_subcmd, git_args, target_repo, canonical_cmd, git_err = resolve_git_invocation(sub_eval, base_cwd)
    if git_err:
        return finalize(("deny", f"[CEH SAFETY GATE - GIT] ⛔ {git_err}", env, "GIT_DESTRUCTIVE"))

    is_git_push = (is_git and git_subcmd == "push")
    if is_git:
        sub_eval = canonical_cmd
        sub_norm = normalize_command_for_evaluation(canonical_cmd)

        if target_repo and explicit_env is None:
            sub_env, sub_env_evidence = detect_environment(explicit_env=None, target_dir=target_repo)
            if ENV_SEVERITY.get(sub_env, 0) > ENV_SEVERITY.get(env, 0):
                env, env_evidence = sub_env, sub_env_evidence

        if git_subcmd == "reset":
            if any(a == "--hard" or a.startswith("--hard=") for a in git_args):
                desc = "Destructive Git reset discarding uncommitted changes (git reset --hard)"
                use_case_code = "GIT_HISTORY"
                if build_destructive_fn is not None:
                    return finalize(build_destructive_fn(env, env_evidence, desc, use_case_code, "Controle de Versão (Git)"))
                return finalize(("deny", desc, env, use_case_code))
            else:
                return finalize(("allow", f"Safe Git operation permitted ({env_evidence}).", env, "GENERAL"))

        if git_subcmd in ("checkout", "restore", "switch"):
            is_dest, desc, use_case_code = evaluate_git_subcommand(git_subcmd, git_args)
            if is_dest:
                if build_destructive_fn is not None:
                    return finalize(build_destructive_fn(env, env_evidence, desc, use_case_code, "Controle de Versão (Git)"))
                return finalize(("deny", desc, env, use_case_code))
            else:
                safe_uc = "GENERAL" if git_subcmd == "switch" else "FILESYSTEM_SAFE"
                return finalize(("allow", f"Safe Git operation permitted ({env_evidence}).", env, safe_uc))

    # 3. Safe Development Bypasses: allow cache/scratch cleanup and selective checkout
    is_safe_dev = False
    for pattern in SAFE_DEV_PATTERNS:
        if re.search(pattern, sub_eval, re.IGNORECASE) or re.search(pattern, sub_norm, re.IGNORECASE):
            is_safe_dev = True
            break
    if is_safe_dev:
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
            return finalize(("allow", f"Safe development operation permitted ({env_evidence}).", env, "FILESYSTEM_SAFE"))

    # 4. Evaluate Destructive Patterns by Use Case and Environment
    for pattern, desc, use_case_code, use_case_label in USE_CASE_DESTRUCTIVE_PATTERNS:
        if (
            re.search(pattern, sub_eval, re.IGNORECASE)
            or re.search(pattern, sub_norm, re.IGNORECASE)
            or re.search(pattern, sub_raw, re.IGNORECASE)
        ):
            if is_git_push and env == "development":
                break
            if build_destructive_fn is not None:
                return finalize(build_destructive_fn(env, env_evidence, desc, use_case_code, use_case_label))
            return finalize(("deny", desc, env, use_case_code))

    # AJ2: Delecao remota de branch no push ou force push graduado como GIT_HISTORY (DEV allow, HML ask, PROD deny)
    if is_git_push and env in ("production", "staging"):
        _, _, p_flags = parse_git_push_tokens(git_args)
        if p_flags.get("force"):
            force_desc = "Force pushing to remote repository (git push --force)"
            if build_destructive_fn is not None:
                return finalize(build_destructive_fn(env, env_evidence, force_desc, "GIT_HISTORY", "Controle de Versão (Git)"))
            return finalize(("deny", force_desc, env, "GIT_HISTORY"))

        is_del, del_desc = is_remote_deletion(git_args)
        if is_del:
            if build_destructive_fn is not None:
                return finalize(build_destructive_fn(env, env_evidence, del_desc, "GIT_HISTORY", "Controle de Versão (Git)"))
            return finalize(("deny", del_desc, env, "GIT_HISTORY"))

    # 5. Pre-Push CI Clearance Gate (todo git push, inclusive force push)
    if is_git_push:
        ci_gate_result = check_pre_push_ci_gate(sub_eval, target_dir=target_repo, git_args=git_args)
        if ci_gate_result is not None:
            ci_decision, ci_reason = ci_gate_result
            return finalize((ci_decision, ci_reason, env, "PRE_PUSH_CI"))

    return finalize(("allow", f"Command complies with CEH safety policy (Env: {env.upper()}, Source: {env_evidence}).", env, "GENERAL"))
