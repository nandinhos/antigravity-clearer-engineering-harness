#!/usr/bin/env python3
"""
ceh_core/engine.py — Core agnostic evaluation engine for CLEARER Engineering Harness (CEH).
Decide estritamente a partir de Request -> Decision sem conhecimento de nenhum formato de host.
ZERO referencias a formatos de host.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from ceh_core.rules import CATASTROPHIC_PATTERNS
from ceh_core.lexer import split_shell_pipeline, extract_subshell_command
from ceh_core.normalize import normalize_path, tokenize_command
from ceh_core.environment import (
    detect_environment,
    ENV_SEVERITY,
    resolve_target_context,
)
from ceh_core.subcommand import evaluate_subcommand


@dataclass
class Request:
    command: str = ""
    cwd: Path | str | None = None
    explicit_env: str | None = None
    target_paths: list[str] = field(default_factory=list)


@dataclass
class Decision:
    decision: str
    reason: str = ""
    environment: str = "development"
    use_case: str = "GENERAL"


def build_destructive_decision(
    env: str,
    env_evidence: str,
    desc: str,
    use_case_code: str,
    use_case_label: str,
) -> tuple[str, str, str, str]:
    """
    W5: Helper unificado para montagem da decisao por ambiente
    (PROD deny, STAGING ask com 2 alertas, DEV allow).
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


def max_severity_decision(
    d1: tuple[str, str, str, str],
    d2: tuple[str, str, str, str]
) -> tuple[str, str, str, str]:
    """Retorna a decisao de maior severidade: CATASTROPHIC > deny > ask > allow."""
    def rank(d: tuple[str, str, str, str]) -> int:
        dec, _, _, uc = d
        return 4 if uc == "CATASTROPHIC" else {"deny": 3, "ask": 2}.get(dec, 1)

    r1, r2 = rank(d1), rank(d2)
    if r1 > r2: return d1
    if r2 > r1: return d2
    return d2 if (d1[3] == "GENERAL" and d2[3] != "GENERAL") else d1


def is_protected_target(target_path: str, resolved_target_dir: Path | None = None) -> bool:
    """Verifica se o caminho alvo e um certificado de CI protegido (.ceh/)."""
    if not target_path:
        return False
    clean = target_path.replace("\\", "/").strip("'\"")
    if any(name in clean.lower() for name in ("last-ci-run.json", "last-ci-run.log", "last-evals-run.json", "config.json")):
        return True
    if re.search(r"(?:^|/)\.ceh(?:/|$)", clean, re.I):
        return True
    try:
        norm = os.path.normpath(clean)
        if re.search(r"(?:^|/)\.ceh(?:/|$)", norm, re.I):
            return True
        if resolved_target_dir is not None:
            full = (resolved_target_dir / Path(norm)).resolve()
            ceh_dir = (resolved_target_dir / ".ceh").resolve()
            if ceh_dir == full or ceh_dir in full.parents or any(p.lower() == ".ceh" for p in full.parts):
                return True
        else:
            full = Path(norm).resolve()
            if any(p.lower() == ".ceh" for p in full.parts):
                return True
    except Exception:
        pass
    return False


def evaluate_command(
    cmd_line: str,
    explicit_env: str | None = None,
    base_cwd: Path | str | None = None,
    depth: int = 0,
    scan_suffixes: bool = True,
    env_floor: str | None = None,
) -> tuple[str, str, str, str]:
    """
    Avalia uma linha de comando contra regras de seguranca por ambiente.
    Executa Early Catastrophic Check sobre a linha bruta antes da decomposicao (P2, Handoff 062).
    """
    if isinstance(cmd_line, Request):
        req = cmd_line
        cmd_line = req.command
        if explicit_env is None:
            explicit_env = req.explicit_env
        if base_cwd is None:
            base_cwd = req.cwd

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
    env, env_evidence = detect_environment(explicit_env, cmd_normalized, target_dir=base_cwd)
    if env_floor and ENV_SEVERITY.get(env_floor, 0) > ENV_SEVERITY.get(env, 0):
        env = env_floor
        env_evidence = f"Inherited environment floor ({env_floor.upper()}) from outer wrapper"

    # 0. Early Catastrophic Check sobre a linha completa antes de decomposicao lexica (P2, Handoff 062)
    for pattern, reason in CATASTROPHIC_PATTERNS:
        if pattern.startswith(r"\brm"):
            continue
        if re.search(pattern, cmd_normalized, re.IGNORECASE) or re.search(pattern, cmd_line, re.IGNORECASE):
            return "deny", f"[CEH CATASTROPHIC BLOCK] {reason}", env, "CATASTROPHIC"

    # Decompoe linha em subcomandos atomicos via FSM Lexer
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
    current_cwd = Path(normalize_path(base_cwd, resolve_home=False)) if base_cwd else Path.cwd().resolve()
    current_env, current_env_ev = env, env_evidence
    persistent_repo: Path | None = None
    unresolved_cd = False

    for sub in subcommands:
        sub_inner = extract_subshell_command(sub)
        if sub_inner is not None:
            evaluations.append(evaluate_command(
                sub_inner, explicit_env=explicit_env, base_cwd=current_cwd,
                depth=depth + 1, scan_suffixes=scan_suffixes, env_floor=current_env
            ))
            continue

        sub_tokens = tokenize_command(sub, posix=True, comments=True)

        eff_cwd, tgt_repo, is_unres, is_persist, ctx_env, clean_toks = resolve_target_context(
            sub_tokens, current_cwd, persistent_repo
        )
        if not clean_toks: continue

        if is_unres:
            unresolved_cd = True
        if is_persist:
            if eff_cwd and eff_cwd.is_dir(): current_cwd = eff_cwd
            if tgt_repo: persistent_repo = tgt_repo
            new_env, new_ev = detect_environment(explicit_env=explicit_env, target_dir=current_cwd)
            if ENV_SEVERITY.get(new_env, 0) > ENV_SEVERITY.get(current_env, 0):
                current_env, current_env_ev = new_env, new_ev

        eval_cwd = eff_cwd if (eff_cwd and eff_cwd.is_dir()) else current_cwd
        sub_eval_env, sub_eval_ev = detect_environment(explicit_env=explicit_env, cmd_line=sub, target_dir=eval_cwd)
        if tgt_repo:
            repo_env, repo_ev = detect_environment(explicit_env=None, target_dir=tgt_repo)
            if ENV_SEVERITY.get(repo_env, 0) > ENV_SEVERITY.get(sub_eval_env, 0):
                sub_eval_env, sub_eval_ev = repo_env, repo_ev

        effective_env, effective_ev = current_env, current_env_ev
        if ENV_SEVERITY.get(sub_eval_env, 0) > ENV_SEVERITY.get(effective_env, 0):
            effective_env, effective_ev = sub_eval_env, sub_eval_ev

        if (unresolved_cd or is_unres) and ENV_SEVERITY.get(effective_env, 0) < ENV_SEVERITY.get("production", 0):
            effective_env, effective_ev = "production", "Incerteza: destino não resolvível (Invariante 7)"

        sub_to_eval = sub.strip()
        while sub_to_eval.startswith("{ ") or sub_to_eval == "{":
            sub_to_eval = sub_to_eval[1:].strip()
        while sub_to_eval.endswith(" }") or sub_to_eval.endswith(";}") or sub_to_eval.endswith("; }") or sub_to_eval == "}":
            if sub_to_eval.endswith("; }"): sub_to_eval = sub_to_eval[:-3].strip()
            elif sub_to_eval.endswith((";}", " }")): sub_to_eval = sub_to_eval[:-2].strip()
            elif sub_to_eval == "}": sub_to_eval = ""
        if not sub_to_eval: continue

        evaluations.append(
            evaluate_subcommand(
                sub_to_eval,
                effective_env,
                effective_ev,
                base_cwd=eval_cwd,
                explicit_env=explicit_env,
                depth=depth,
                scan_suffixes=scan_suffixes,
                eval_command_fn=evaluate_command,
                build_destructive_fn=build_destructive_decision,
                max_severity_fn=max_severity_decision,
            )
        )

        if ctx_env and ENV_SEVERITY.get(ctx_env, 0) > ENV_SEVERITY.get(current_env, 0):
            current_env, current_env_ev = ctx_env, f"Context modification: {ctx_env} detected in pipeline"

    # Precedencia estrita: CATASTROPHIC > DENY > ASK > ALLOW
    for e in evaluations:
        if e[0] == "deny" and e[3] == "CATASTROPHIC": return e
    for dec in ("deny", "ask"):
        for e in evaluations:
            if e[0] == dec: return e
    return evaluations[0]


def evaluate(request: Request) -> Decision:
    """
    Ponto unico de entrada do motor agnostico: evaluate(Request) -> Decision.
    """
    if request.target_paths:
        target_dir = Path(request.cwd).resolve() if request.cwd else None
        for p in request.target_paths:
            if is_protected_target(p, target_dir):
                return Decision(
                    decision="deny",
                    reason=f"[CEH CERTIFICATE INTEGRITY - G9] ⛔ Tentativa de escrita/modificação de certificado de CI ({p}). Arquivos sob .ceh/ são imutáveis via ferramentas de escrita.",
                    environment="development" if request.explicit_env is None else request.explicit_env,
                    use_case="CERTIFICATE_INTEGRITY",
                )
        return Decision(
            decision="allow",
            reason="",
            environment="development" if request.explicit_env is None else request.explicit_env,
            use_case="GENERAL",
        )

    dec, reason, env, uc = evaluate_command(
        request.command,
        explicit_env=request.explicit_env,
        base_cwd=request.cwd,
    )
    return Decision(decision=dec, reason=reason, environment=env, use_case=uc)
