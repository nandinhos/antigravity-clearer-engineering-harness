#!/usr/bin/env python3
"""
safety-gate.py - PreToolUse Safety Guard for CLEARER Engineering Harness (CEH).
Enforces environment-aware safety policy across 3 tiers:
- Development / Test: Destructive commands permitted with backup & rollback readiness.
- Homologação / Staging: Confirmation required (ASK) with 2 explicit alerts + backup & rollback mandate.
- Produção: Destructive commands strictly prohibited (DENY - fora de cogitação).
"""
from __future__ import annotations

import sys
import os
import json
import re
import argparse
import subprocess
import shlex
from pathlib import Path

_SCRIPTS_DIR = str(Path(__file__).resolve().parent)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from ceh_core.rules import (
    CATASTROPHIC_PATTERNS,
    SAFE_DEV_PATTERNS,
    USE_CASE_DESTRUCTIVE_PATTERNS,
)
from ceh_core.lexer import (
    split_shell_pipeline,
    normalize_command_for_evaluation,
    resolve_command_head,
    substitute_positional_args,
)
from ceh_core.environment import (
    normalize_env,
    detect_environment,
    get_git_branch,
    find_repo_root,
)
from ceh_core.rm import evaluate_rm_command
from ceh_core.git import evaluate_git_subcommand
from ceh_core.find import evaluate_find_command
from ceh_core.interpreters import evaluate_interpreter_command


def resolve_git_invocation(
    cmd_line: str,
    base_cwd: Path | str | None = None
) -> tuple[bool, str | None, list[str], Path | None, str, str | None]:
    """
    Analisa e canonicaliza a invocação do Git para qualquer subcomando (G3 / R5):
    1. Identifica se é comando git (com suporte opcional a prefixos rtk / proxy).
    2. Acumula iterativamente flags -C <path> e -C<path>, resolvendo caminhos.
    3. Remove opções globais inócuas (--no-pager, -p, --paginate, --no-replace-objects, --literal-pathspecs, --bare).
    4. Rejeita em Fail-Closed opções não homologadas (--git-dir, --work-tree, -c e variantes).
    5. Localiza a raiz do repositório via find_repo_root() a partir do diretório resultante de -C.
    6. Reconstrói o comando de forma canônica: 'git <subcomando> <args restantes>'.
    Retorna: (is_git, subcommand, remaining_args, target_repo_root, canonical_cmd, error_reason)
    """
    import shlex
    try:
        tokens = shlex.split(cmd_line, posix=True)
    except Exception as e:
        return False, None, [], None, cmd_line, f"Erro de parsing na linha git: {e}"

    idx, _ = resolve_command_head(tokens)
    tokens = tokens[idx:]

    if not tokens or tokens[0] != "git":
        return False, None, [], None, cmd_line, None

    current_dir = Path.cwd().resolve() if base_cwd is None else Path(base_cwd).resolve()
    subcommand = None
    remaining_args = []
    i = 1

    INNOCUOUS_GLOBAL_FLAGS = {
        "--no-pager", "-p", "-P", "--paginate",
        "--no-replace-objects", "--literal-pathspecs", "--bare"
    }

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
        elif token.startswith("--git-dir") or token.startswith("--work-tree") or token == "-c" or token.startswith("-c="):
            return True, None, [], None, cmd_line, f"Opção global do Git não homologada no Safety Gate ({token})"
        elif token in INNOCUOUS_GLOBAL_FLAGS:
            i += 1
            continue
        elif token.startswith("-"):
            # Qualquer outra opção global não explicitamente homologada gera fail-closed
            return True, None, [], None, cmd_line, f"Opção global do Git não homologada no Safety Gate ({token})"
        else:
            subcommand = token
            remaining_args = tokens[i+1:]
            break

    # U1: normalização de pathspecs equivalentes ao diretório atual (./, .//, ./.) para .
    if subcommand in ("checkout", "restore"):
        norm_args = []
        for arg in remaining_args:
            if arg in ("./", ".//", "./.") or (arg.startswith("./") and all(c in "./" for c in arg)):
                norm_args.append(".")
            else:
                norm_args.append(arg)
        remaining_args = norm_args

    repo_root = find_repo_root(current_dir) if current_dir.exists() else current_dir
    if subcommand is None:
        return True, None, [], repo_root, "git", None

    canonical_cmd = "git " + subcommand + (" " + " ".join(remaining_args) if remaining_args else "")
    return True, subcommand, remaining_args, repo_root, canonical_cmd, None


def build_destructive_decision(
    env: str,
    env_evidence: str,
    desc: str,
    use_case_code: str,
    use_case_label: str,
) -> tuple[str, str, str, str]:
    """
    W5: Helper unificado para montagem da decisão por ambiente (texto e use_case)
    para comandos destrutivos (PROD deny, STAGING ask com 2 alertas, DEV allow).
    """
    if env == "production":
        reason = (
            f"[CEH PRODUCTION LOCK] Comandos destrutivos são TERMINANTEMENTE PROIBIDOS em PRODUÇÃO "
            f"(Caso de Uso: {use_case_label}): {desc}.\n"
            f"Ambiente detectado: {env.upper()} (Evidência: {env_evidence}).\n"
            f"Execução bloqueada para prevenir perda de dados e indisponibilidade."
        )
        return "deny", reason, env, use_case_code

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

    reason = (
        f"[CEH DEV PERMITTED - Caso de Uso: {use_case_label}] Comando destrutivo liberado para ambiente de "
        f"DESENVOLVIMENTO/TESTE ({desc}). Ambiente: {env.upper()} (Evidência: {env_evidence}).\n"
        f"Assegure a disponibilidade de backup e rollback para fins de correção."
    )
    return "allow", reason, env, use_case_code


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
        return "deny", "[CEH PRE-PUSH CI GATE] ⛔ Push bloqueado: NENHUMA execução prévia comprovada em '.github/workflows'."

    try:
        data = json.loads(cert_file.read_text(encoding="utf-8"))
        exit_code, status, cert_commit = data.get("exit_code"), data.get("status", "FAIL"), data.get("commit_hash", "")
        cmd_executed = str(data.get("command", "")).strip()

        if not cert_commit or cert_commit == "untracked":
            return "deny", "[CEH PRE-PUSH CI GATE] ⛔ Push bloqueado: Certificado inválido (commit_hash ausente ou não rastreado)."

        if exit_code != 0 or status != "PASS":
            return "deny", f"[CEH PRE-PUSH CI GATE] ⛔ Push bloqueado: suíte FALHOU (Exit Code: {exit_code}, Status: {status}). Comando: {cmd_executed}"

        if data.get("canonical_verified") is not True:
            return "deny", f"[CEH PRE-PUSH CI GATE] ⛔ Push bloqueado: O certificado não comprova execução da suíte canônica. Comando: '{cmd_executed}'"

        head_res = subprocess.run(["git", "-C", str(repo_root), "rev-parse", "HEAD"], capture_output=True, text=True, timeout=3)
        if head_res.returncode == 0:
            current_head = head_res.stdout.strip()
            if cert_commit != current_head:
                return "deny", f"[CEH PRE-PUSH CI GATE] ⛔ Push bloqueado por desatualização de testes: HEAD ({current_head[:7]}) != Cert ({cert_commit[:7]})."

    except Exception as e:
        return "deny", f"[CEH PRE-PUSH CI GATE] ⛔ Push bloqueado: Certificado de CI ilegível ({str(e)})."

    return "allow", "Pre-Push CI Gate validado: suíte canônica aprovada para o commit atual."

def max_severity_decision(
    d1: tuple[str, str, str, str],
    d2: tuple[str, str, str, str]
) -> tuple[str, str, str, str]:
    """
    Retorna a decisão de maior severidade: CATASTROPHIC > deny > ask > allow.
    Em caso de empate em allow, prefere a decisão mais específica sobre GENERAL.
    """
    def rank(d: tuple[str, str, str, str]) -> int:
        dec, _, _, uc = d
        if uc == "CATASTROPHIC":
            return 4
        if dec == "deny":
            return 3
        if dec == "ask":
            return 2
        return 1

    r1, r2 = rank(d1), rank(d2)
    if r1 > r2:
        return d1
    if r2 > r1:
        return d2
    # Empate: se d1 é GENERAL e d2 não é GENERAL, prefere d2
    if d1[3] == "GENERAL" and d2[3] != "GENERAL":
        return d2
    return d1


def extract_shell_c_command(cmd_line: str) -> str | None:
    """Extrai o comando executado via flag -c em shells conhecidos (AD2, Handoff 028)."""
    try:
        tokens = shlex.split(cmd_line, posix=True)
    except Exception:
        return None
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
) -> tuple[str, str, str, str]:
    """
    Avalia um subcomando atômico contra as políticas de segurança do CEH.
    Retorna (decision, reason, detected_env, use_case).
    Composição estrita (AA1): analisadores só apertam; a decisão final é a mais severa.
    """
    if depth > 3:
        return (
            "deny",
            f"[CEH SAFETY GATE - FAIL-CLOSED] Limite de profundidade de recursão excedido (depth={depth} > 3).",
            env,
            "CATASTROPHIC",
        )

    sub_raw = subcmd.strip()
    # Strip CLI proxy prefix (RTK / RTK proxy)
    sub_eval = re.sub(r"^\s*rtk(?:\s+proxy)?\s+", "", sub_raw)
    sub_norm = normalize_command_for_evaluation(sub_eval)

    candidate: tuple[str, str, str, str] | None = None

    # AA2/AB1: Desembrulho recursivo de shells (sh -c, bash -c) e executores de string (eval, su -c, watch)
    try:
        sub_tokens = shlex.split(sub_raw, posix=True)
    except Exception:
        sub_tokens = []

    if sub_tokens:
        h_idx, string_exec = resolve_command_head(sub_tokens)
        if string_exec is not None:
            return evaluate_command(
                string_exec,
                explicit_env=explicit_env,
                base_cwd=base_cwd,
                depth=depth + 1
            )

        # AD1/AE1 (Handoff 029 §3.1): Varredura fail-closed de sufixos em um único nível por subcomando
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
                    s_res = evaluate_command(
                        suffix_cmd,
                        explicit_env=explicit_env,
                        base_cwd=base_cwd,
                        depth=depth,
                        scan_suffixes=False,
                    )
                    if s_res[3] == "CATASTROPHIC":
                        return s_res
                    candidate = max_severity_decision(candidate, s_res) if candidate else s_res

    shell_inner = extract_shell_c_command(sub_raw)
    if shell_inner:
        return evaluate_command(
            shell_inner,
            explicit_env=explicit_env,
            base_cwd=base_cwd,
            depth=depth + 1
        )

    # 0. Avaliação Estrita de 'rm' por tokens (G1, G4 e PR-04b)
    rm_res = evaluate_rm_command(sub_norm, env, env_evidence=env_evidence, base_cwd=base_cwd)
    if rm_res is not None:
        return rm_res

    # 0.1 Avaliação Estrita de 'find' por tokens com desembrulho de -exec (G5, PR-06/PR-06b)
    find_res = evaluate_find_command(
        sub_eval, env, env_evidence=env_evidence, base_cwd=base_cwd, eval_fn=evaluate_command, depth=depth
    )
    if find_res is not None:
        if find_res[3] == "CATASTROPHIC":
            return find_res
        candidate = find_res

    # 0.2 Avaliação Estrita de interpretadores por tokens com desembrulho recursivo (G5, PR-06/PR-06b)
    interp_res = evaluate_interpreter_command(
        sub_eval, env, env_evidence=env_evidence, base_cwd=base_cwd, eval_fn=evaluate_command, depth=depth
    )
    if interp_res is not None:
        if interp_res[3] == "CATASTROPHIC":
            return interp_res
        candidate = max_severity_decision(candidate, interp_res) if candidate else interp_res

    def finalize(decision: tuple[str, str, str, str]) -> tuple[str, str, str, str]:
        if candidate is not None:
            return max_severity_decision(decision, candidate)
        return decision

    # 1. Catastrophic Blocks: DENY has absolute priority in ANY environment
    for pattern, reason in CATASTROPHIC_PATTERNS:
        if (
            re.search(pattern, sub_eval, re.IGNORECASE)
            or re.search(pattern, sub_norm, re.IGNORECASE)
            or re.search(pattern, sub_raw, re.IGNORECASE)
        ):
            return "deny", f"[CEH CATASTROPHIC BLOCK] {reason}", env, "CATASTROPHIC"

    # 2. Resolução Canônica de Git (R5 + G3)
    is_git, git_subcmd, git_args, target_repo, canonical_cmd, git_err = resolve_git_invocation(sub_eval, base_cwd)
    if git_err:
        return finalize(("deny", f"[CEH SAFETY GATE - GIT] ⛔ {git_err}", env, "GIT_DESTRUCTIVE"))

    is_git_push = (is_git and git_subcmd == "push")
    if is_git:
        sub_eval = canonical_cmd
        sub_norm = normalize_command_for_evaluation(canonical_cmd)

        if target_repo and explicit_env is None:
            sub_env, sub_env_evidence = detect_environment(explicit_env=None, target_dir=target_repo)
            env = sub_env
            env_evidence = sub_env_evidence

        if git_subcmd in ("checkout", "restore", "switch"):
            is_dest, desc, use_case_code = evaluate_git_subcommand(git_subcmd, git_args)
            if is_dest:
                return finalize(build_destructive_decision(env, env_evidence, desc, use_case_code, "Controle de Versão (Git)"))
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
            return finalize(build_destructive_decision(env, env_evidence, desc, use_case_code, use_case_label))

    # 5. Pre-Push CI Clearance Gate (todo git push, inclusive force push)
    if is_git_push:
        ci_gate_result = check_pre_push_ci_gate(sub_eval, target_dir=target_repo)
        if ci_gate_result is not None:
            ci_decision, ci_reason = ci_gate_result
            return finalize((ci_decision, ci_reason, env, "PRE_PUSH_CI"))

    return finalize(("allow", f"Command complies with CEH safety policy (Env: {env.upper()}, Source: {env_evidence}).", env, "GENERAL"))


def evaluate_command(
    cmd_line: str,
    explicit_env: str | None = None,
    base_cwd: Path | str | None = None,
    depth: int = 0,
    scan_suffixes: bool = True,
) -> tuple[str, str, str, str]:
    """
    Evaluates a command line string against environment safety rules, decomposing
    compound commands and aggregating decisions with priority: CATASTROPHIC > DENY > ASK > ALLOW.
    """
    if depth > 3:
        return (
            "deny",
            f"[CEH SAFETY GATE - FAIL-CLOSED] Limite de profundidade de recursão/desembrulho excedido (depth={depth} > 3).",
            "development" if explicit_env is None else explicit_env,
            "CATASTROPHIC",
        )

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
        evaluations.append(
            evaluate_subcommand(
                sub,
                env,
                env_evidence,
                base_cwd=base_cwd,
                explicit_env=explicit_env,
                depth=depth,
                scan_suffixes=scan_suffixes,
            )
        )

    # Precedência estrita: CATASTROPHIC > DENY > ASK > ALLOW
    catastrophics = [e for e in evaluations if e[0] == "deny" and e[3] == "CATASTROPHIC"]
    if catastrophics:
        return catastrophics[0]

    denies = [e for e in evaluations if e[0] == "deny"]
    if denies:
        return denies[0]

    asks = [e for e in evaluations if e[0] == "ask"]
    if asks:
        return asks[0]

    return evaluations[0]

def handle_hook():
    """Processes PreToolUse hook JSON from stdin."""
    try:
        raw_input = sys.stdin.read()
        if not raw_input.strip():
            print(json.dumps({"decision": "allow"}))
            return

        payload = json.loads(raw_input)
        if not isinstance(payload, dict):
            print(json.dumps({
                "decision": "deny",
                "reason": "[CEH SAFETY GATE ERROR] Invalid hook payload: expected JSON object."
            }, ensure_ascii=False))
            sys.exit(2)

        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from hook_context import evaluate_hook_payload
        result = evaluate_hook_payload(payload, evaluate_command)
        print(json.dumps(result, ensure_ascii=False))
    except Exception as e:
        print(json.dumps({
            "decision": "deny",
            "reason": f"[CEH SAFETY GATE ERROR] Hook execution failed: {str(e)}"
        }, ensure_ascii=False))
        sys.exit(2)

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
