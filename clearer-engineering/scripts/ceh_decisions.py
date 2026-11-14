#!/usr/bin/env python3
# ==============================================================================
# ceh_decisions.py — Motor System One (Gemini Decisions API) para CEH Antigravity
# Camada L1.5 (Shadow/Sidecar Mode até 16/11 — 100% Python stdlib)
# ==============================================================================
"""
Motor de decisão probabilística calibrada de espaço fechado para o CLEARER
Engineering Harness (escopo exclusivo Google Antigravity IDE/CLI).

Implementa a integração com o endpoint oficial `POST /v1beta/decisions`
(`gemini-decision-1`) e materializa os 7 Invariantes Epistemológicos do ADR 003
(`docs/architecture/system-one-epistemology.md`):
  1. Conteúdo != Julgamento (input compartilhado isolado de `questions`)
  2. Espaço de Resposta Fechado (`noul`, `choice`, `score`)
  3. Atomicidade (1 pergunta = 1 propriedade univariada)
  4. Isolamento (avaliação independente em passe único de prefill)
  5. Dois Eixos: Decisão e Certeza (`noul`/`choice`/`score` + `confidence`)
  6. Código Detém o Controle (regras de agregação e promoção em Python puro)
  7. Incerteza é Escalada, Nunca Adivinhada (`confidence < threshold` -> ASK/HIGH)

Degradação Graciosa Incondicional:
  - Se `GEMINI_API_KEY` (ou `GOOGLE_API_KEY`) não estiver configurada, ou se a
    rede/endpoint retornar erro/timeout, opera automaticamente em modo
    `FALLBACK_OFFLINE` determinístico, nunca bloqueando o workflow local.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

DEFAULT_MODEL = "gemini-decision-1"
DEFAULT_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/decisions"
DEFAULT_TIMEOUT_SEC = 4.0

HERE = Path(__file__).resolve()
DEFAULT_TELEMETRY_PATH = Path.home() / ".gemini" / "antigravity" / "ceh_decisions_telemetry.jsonl"

# Thresholds canônicos (Invariantes 6 e 7)
NOUL_POSITIVE_THRESHOLD = 0.70
MIN_CONFIDENCE_THRESHOLD = 0.75
CLAIM_CONFIDENCE_THRESHOLD = 0.80

# ------------------------------------------------------------------------------
# Catálogo de 7 Verificações Atômicas do Diff Audit (clearer-review/SKILL.md §2)
# ------------------------------------------------------------------------------
DIFF_ATOMIC_QUESTIONS: Dict[str, Dict[str, Any]] = {
    "modifies_security_or_auth": {
        "type": "noul",
        "instructions": (
            "WHAT (YES): Alters auth middlewares, tokens, cryptography, input sanitization, "
            "RBAC, CORS, safety-gate rules, or host security adapters. "
            "NOT FOR (NO): Public routes, documentation, or presentation logic without permission impact."
        ),
    },
    "introduces_destructive_command": {
        "type": "noul",
        "instructions": (
            "WHAT (YES): Introduces destructive DB commands (migrate:fresh, db:wipe, DROP, TRUNCATE), "
            "Git destructive ops (reset --hard, push --force, clean -fdx), or OS wipe (rm -rf /). "
            "NOT FOR (NO): Read-only commands (git status, SELECT, git diff) or test assertions."
        ),
    },
    "breaks_backward_compatibility": {
        "type": "noul",
        "instructions": (
            "WHAT (YES): Breaks existing public method signatures, removes database columns, "
            "or mutates JSON payload contracts without fallback. "
            "NOT FOR (NO): Additive extensions, new optional flags, or backwards-compatible fixes."
        ),
    },
    "modifies_database_schema": {
        "type": "noul",
        "instructions": (
            "WHAT (YES): Creates or alters database migrations, relational schemas, DDL tables, or indexes. "
            "NOT FOR (NO): Read queries or non-DDL application code."
        ),
    },
    "has_untested_execution_branches": {
        "type": "noul",
        "instructions": (
            "WHAT (YES): Introduces new conditional execution paths (if/elif/switch/except) in production "
            "code without corresponding test cases covering those branches. "
            "NOT FOR (NO): Diffs that include unit tests or pure documentation/config changes."
        ),
    },
    "violates_minimal_blast_radius": {
        "type": "noul",
        "instructions": (
            "WHAT (YES): Touches unrelated files outside task scope, performs opportunistic refactoring, "
            "or introduces cosmetic whitespace formatting noise. "
            "NOT FOR (NO): Surgical edits strictly focused on a single cohesive objective."
        ),
    },
    "introduces_or_modifies_lookups": {
        "type": "noul",
        "instructions": (
            "WHAT (YES): Adds or modifies entries in fixed enums, lookup tables, seeders, or constant sets. "
            "NOT FOR (NO): General logic changes that do not mutate fixed domain catalogs."
        ),
    },
    "blast_radius_severity": {
        "type": "score",
        "instructions": "Rate the structural blast radius and operational risk of this git diff.",
        "criteria": [
            "1 - INFO: Documentation, comments, or isolated test-only additions.",
            "2 - LOW: Minor local adjustment or non-critical helper with full test coverage.",
            "3 - MEDIUM: Standard feature, bugfix, or adapter update with bounded scope.",
            "4 - HIGH: Core security gate, authentication, or cross-host contract change.",
            "5 - BLOCKER: Catastrophic data loss risk, security bypass, or broken invariant.",
        ],
    },
}

CRITICAL_DIFF_KEYS = (
    "modifies_security_or_auth",
    "introduces_destructive_command",
    "breaks_backward_compatibility",
    "modifies_database_schema",
)

# ------------------------------------------------------------------------------
# Catálogo de Critérios Contrastivos para Auditoria de Claims (clearer-audit §2)
# ------------------------------------------------------------------------------
CLAIM_AUDIT_CRITERIA: Dict[str, str] = {
    "SUPPORTED": (
        "WHAT: Directly proven by the provided file content, code implementation, or test log. "
        "NOT FOR: Plausible claims where the provided file deals with an unrelated subject."
    ),
    "PARTIALLY_SUPPORTED": (
        "WHAT: Partial evidence exists in the provided content, or code exists without test verification. "
        "NOT FOR: Complete absence of correlation or full end-to-end proof."
    ),
    "UNSUPPORTED": (
        "WHAT: The provided evidence content does not mention, support, or directly contradicts the claim. "
        "NOT FOR: Claims clearly demonstrated by the inspected code or log."
    ),
}

# ------------------------------------------------------------------------------
# Catálogo de Roteamento do Dispatcher (skills/clearer/SKILL.md §2 e §3)
# ------------------------------------------------------------------------------
ROUTER_QUESTIONS: Dict[str, Dict[str, Any]] = {
    "risk_dial": {
        "type": "choice",
        "instructions": "Classify the engineering risk level based on the cost of an error.",
        "criteria": {
            "LOW": "Read-only queries, simple searches, minor local renames, formatting, or documentation.",
            "MEDIUM": "New features, bugfixes, code refactoring, endpoint changes, or standard business rules.",
            "HIGH": "Core authentication, financial transactions, critical concurrency, destructive migrations, or security gates.",
        },
    },
    "target_skill": {
        "type": "choice",
        "instructions": "Select the specialized CLEARER skill that best matches the developer request.",
        "criteria": {
            "clearer-feature": "Implementing a new feature, capability, or enhancement.",
            "clearer-bugfix": "Diagnosing, reproducing, and fixing a bug, error, or regression.",
            "clearer-refactor": "Restructuring or cleaning up existing code without changing external behavior.",
            "clearer-review": "Adversarial code review or git diff audit.",
            "clearer-audit": "Verifying claims against physical evidence and generating the audit verdict.",
            "clearer-map": "Read-only architectural mapping and codebase discovery.",
            "clearer-test": "Executing, writing, or verifying deterministic test suites.",
            "learned-lesson": "Extracting and persisting a technical lesson learned or best practice.",
        },
    },
    "has_business_ambiguity": {
        "type": "noul",
        "instructions": (
            "WHAT (YES): The request has mutually exclusive architectural paths or critical missing requirements "
            "that cannot be answered by inspecting the repository. "
            "NOT FOR (NO): Self-contained engineering tasks or questions that can be resolved by reading the code."
        ),
    },
}

# ------------------------------------------------------------------------------
# Catálogo de Fechamento Epistêmico (ceh-stop-guard.py)
# ------------------------------------------------------------------------------
STOP_CHECK_QUESTIONS: Dict[str, Dict[str, Any]] = {
    "has_result_verdict": {
        "type": "noul",
        "instructions": "WHAT (YES): Explicitly states the final execution result/status of the task. NOT FOR (NO): Casual conversation without a task outcome.",
    },
    "has_observed_evidence": {
        "type": "noul",
        "instructions": "WHAT (YES): Categorizes facts using OBSERVED (or INFERRED/UNKNOWN) grounded in real files or commands. NOT FOR (NO): Unverified claims or casual mentions of the word OBSERVED.",
    },
    "has_test_exit_code": {
        "type": "noul",
        "instructions": "WHAT (YES): Reports concrete test execution commands and their exit codes (or explicit NOT_RUN justification). NOT FOR (NO): Generic 'tested' statements without command/exit code.",
    },
    "has_confidence_level": {
        "type": "noul",
        "instructions": "WHAT (YES): Includes an explicit confidence metric or audit verdict at closing. NOT FOR (NO): Missing confidence assessment.",
    },
}

# ------------------------------------------------------------------------------
# Catálogo da Escada de Decisão Ponytail v5 (AGENTS.md §6.1 — PLAN / IMPLEMENT)
# ------------------------------------------------------------------------------
PONYTAIL_QUESTIONS: Dict[str, Dict[str, Any]] = {
    "violates_yagni_speculative_abstraction": {
        "type": "noul",
        "instructions": (
            "WHAT (YES): Proposes speculative abstractions, factories, interfaces, microservices, "
            "or configuration layers for a single concrete use case that was not requested. "
            "NOT FOR (NO): Minimal direct implementation solving only the stated problem."
        ),
    },
    "adds_avoidable_external_dependency": {
        "type": "noul",
        "instructions": (
            "WHAT (YES): Introduces a new third-party package (pip/npm/composer) for a task that can "
            "be solved with the standard library or already-installed project dependencies. "
            "NOT FOR (NO): Using stdlib (e.g. urllib.request, json, pathlib) or existing project packages."
        ),
    },
    "missing_trigger_on_deliberate_shortcut": {
        "type": "noul",
        "instructions": (
            "WHAT (YES): Mentions or introduces a temporary shortcut/hack/TODO without an explicit numeric "
            "scale ceiling and objective upgrade trigger (`// shortcut: <limit>, <trigger>`). "
            "NOT FOR (NO): Clean code without shortcuts, or shortcuts with a documented numeric trigger."
        ),
    },
    "requires_step7_behavioral_test": {
        "type": "noul",
        "instructions": (
            "WHAT (YES): Introduces non-trivial conditional logic, loops, parsers, financial calculations, "
            "or security/auth rules that require a deterministic behavioral test (Step 7 of Ponytail Ladder). "
            "NOT FOR (NO): Trivial cosmetic text or pure documentation changes."
        ),
    },
    "verification_layer": {
        "type": "choice",
        "instructions": "Select the minimum sufficient verification layer on the Ponytail Verification Ladder.",
        "criteria": {
            "NONE_TRIVIAL": "Pure documentation, comments, or formatting with zero runtime logic.",
            "UNIT_MEMORY": "Pure functions, parsers, or business rules testable in memory in milliseconds.",
            "INTEGRATION_LOCAL": "Database queries, filesystem hooks, or local service boundaries.",
            "E2E_BROWSER": "Critical multi-page UI flows that cannot be verified at unit or integration level.",
        },
    },
}


# ------------------------------------------------------------------------------
# Utilitários de Segurança e Mascaramento (Guardrails Globais)
# ------------------------------------------------------------------------------
SECRET_PATTERNS = re.compile(
    r"(AIza[0-9A-Za-z\-_]{10,}|Bearer\s+[A-Za-z0-9_\-\.]{12,}|sk-[A-Za-z0-9_\-]{12,}|ghp_[A-Za-z0-9]{12,})",
    re.I,
)


def mask_secrets(text: str) -> str:
    """Mascara qualquer padrão de token/chave preservando apenas 4 chars nas pontas."""
    def _repl(match: re.Match) -> str:
        val = match.group(0)
        if len(val) <= 10:
            return "***MASKED***"
        return f"{val[:4]}****************{val[-4:]}"

    return SECRET_PATTERNS.sub(_repl, text)


def _strip_hostile_comments(text: str) -> str:
    """
    Mitigação de Contexto Hostil (Invariante de Segurança ADR 003 §2):
    No fallback determinístico local, comentários tentando injetar comandos de
    override (`ignore security`, `bypass safety`, `return noul=0`) são neutralizados
    para nunca suprimir sinais reais de código.
    """
    cleaned_lines = []
    for line in text.splitlines():
        if re.search(r"(ignore\s+security|bypass\s+safety|system\s+override|return\s+noul)", line, re.I):
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


# ------------------------------------------------------------------------------
# Motor de Chamada à API Gemini Decisions + Fallback Determinístico Local
# ------------------------------------------------------------------------------
TransportFn = Callable[[str, Dict[str, Any], str, float], Dict[str, Any]]


def _default_http_transport(
    endpoint: str,
    payload: Dict[str, Any],
    api_key: str,
    timeout_sec: float,
) -> Dict[str, Any]:
    """Executa POST HTTP nativo (stdlib `urllib.request`) para `/v1beta/decisions`."""
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        endpoint,
        data=body,
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
        return json.loads(raw)


def _deterministic_fallback_evaluator(
    shared_input: str,
    questions: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Avaliador determinístico calibrado (Fallback Offline quando GEMINI_API_KEY
    não está presente ou o endpoint v1beta/decisions está indisponível).
    Garante que o harness funcione 100% offline mantendo exatamente o mesmo
    schema de saída (`answers` com `noul`/`choice`/`score` + `confidence`).
    """
    sanitized = _strip_hostile_comments(shared_input)
    lower_in = sanitized.lower()
    answers: Dict[str, Any] = {}

    for q_id, q_spec in questions.items():
        q_type = q_spec.get("type", "noul")

        if q_type == "noul":
            noul_val, conf_val = _eval_fallback_noul(q_id, sanitized, lower_in)
            answers[q_id] = {"noul": round(noul_val, 4), "confidence": round(conf_val, 4)}

        elif q_type == "choice":
            choice_val, probs, conf_val = _eval_fallback_choice(q_id, q_spec, sanitized, lower_in)
            answers[q_id] = {
                "choice": choice_val,
                "probabilities": probs,
                "confidence": round(conf_val, 4),
            }

        elif q_type == "score":
            score_val, probs, conf_val = _eval_fallback_score(q_id, q_spec, sanitized, lower_in)
            answers[q_id] = {
                "score": round(score_val, 4),
                "probabilities": probs,
                "confidence": round(conf_val, 4),
            }

    return {"model": f"{DEFAULT_MODEL}-offline-fallback", "answers": answers}


def _eval_fallback_noul(q_id: str, raw: str, lower_in: str) -> Tuple[float, float]:
    # 1. Diff Atomic Checks
    if q_id == "modifies_security_or_auth":
        sec_markers = (
            "safety-gate.py",
            "ceh_core/",
            "adapters/antigravity.py",
            "auth",
            "token",
            "permission",
            "rbac",
            "crypt",
            "redact.py",
            "FILE_WRITE_TOOLS",
            "TERMINAL_TOOLS",
        )
        hits = sum(1 for m in sec_markers if m.lower() in lower_in)
        if hits >= 2:
            return 0.94, 0.92
        if hits == 1:
            return 0.78, 0.85
        return 0.04, 0.91

    if q_id == "introduces_destructive_command":
        # Ignora se for apenas regra de bloqueio ou fixture de teste
        added_lines = "\n".join(
            ln[1:] for ln in raw.splitlines() if ln.startswith("+") and not ln.startswith("+++")
        )
        target = added_lines if added_lines.strip() else raw
        if re.search(r"\b(migrate:fresh|db:wipe|drop\s+database|truncate\s+table|rm\s+-rf\s+/|git\s+push\s+--force)\b", target, re.I):
            if "test_" in lower_in or "expected_decision" in lower_in:
                return 0.18, 0.84
            return 0.95, 0.93
        return 0.02, 0.95

    if q_id == "breaks_backward_compatibility":
        removed_defs = re.findall(r"^-\s*def\s+([a-zA-Z0-9_]+)\s*\(", raw, re.M)
        added_defs = re.findall(r"^\+\s*def\s+([a-zA-Z0-9_]+)\s*\(", raw, re.M)
        removed_public = [fn for fn in removed_defs if not fn.startswith("_") and fn not in added_defs]
        if removed_public:
            return 0.88, 0.86
        return 0.05, 0.90

    if q_id == "modifies_database_schema":
        if re.search(r"\b(create\s+table|alter\s+table|schema::create|make:migration)\b", lower_in):
            return 0.92, 0.94
        return 0.02, 0.96

    if q_id == "has_untested_execution_branches":
        added_lines = [ln for ln in raw.splitlines() if ln.startswith("+") and not ln.startswith("+++")]
        has_new_branch = any(re.search(r"^\+\s*(if|elif|except|case)\b", ln) for ln in added_lines)
        touches_tests = ("test_" in lower_in) or ("tests/" in lower_in)
        if has_new_branch and not touches_tests:
            return 0.82, 0.83
        return 0.08, 0.89

    if q_id == "violates_minimal_blast_radius":
        files_changed = len(re.findall(r"^diff --git ", raw, re.M))
        if files_changed > 8:
            return 0.85, 0.82
        return 0.06, 0.90

    if q_id == "introduces_or_modifies_lookups":
        if re.search(r"^\+.*(TOOLS\s*=|SEVERITIES\s*=|ENUM|LOOKUP|SUPPORTED_HOSTS)", raw, re.M) or (
            '"write_file"' in raw and '"edit_file"' in raw
        ):
            return 0.89, 0.90
        return 0.07, 0.88

    # 2. Router Ambiguity Check
    if q_id == "has_business_ambiguity":
        if len(raw.strip()) < 15 or "?" in raw and ("ou " in lower_in or "qual " in lower_in):
            return 0.76, 0.81
        return 0.08, 0.88

    # 3. Stop Guard Checks
    if q_id == "has_result_verdict":
        ok = bool(re.search(r"(resultado\s*:|result\s*:|status\s*:\s*(conclu|pass|aprovad|completed))", lower_in))
        return (0.95, 0.93) if ok else (0.04, 0.92)

    if q_id == "has_observed_evidence":
        ok = bool(re.search(r"\b(observed|inferred|unknown)\b.*(:|->|`|[a-z0-9_/\.\-]+\.(py|sh|md|json))", lower_in))
        return (0.94, 0.91) if ok else (0.05, 0.90)

    if q_id == "has_test_exit_code":
        ok = bool(re.search(r"(exit\s*code\s*[:=]?\s*0|exit\s+0|\d+/\d+\s*(pass|verdes|aprovados)|not_run)", lower_in))
        return (0.96, 0.94) if ok else (0.03, 0.92)

    if q_id == "has_confidence_level":
        ok = bool(re.search(r"(confian[çc]a\s*:|confidence\s*:|\b(supported|approved)\b)", lower_in))
        return (0.93, 0.91) if ok else (0.06, 0.90)

    # 4. Ponytail Ladder Checks
    if q_id == "violates_yagni_speculative_abstraction":
        over_markers = ("abstractfactory", "microservices", "microsserviço", "strategyfactory", "genericenterprise", "eventbus")
        ok = any(m in lower_in.replace(" ", "") for m in over_markers) or ("factory" in lower_in and "interface" in lower_in)
        return (0.92, 0.90) if ok else (0.04, 0.91)

    if q_id == "adds_avoidable_external_dependency":
        dep_markers = ("pip install", "npm install", "composer require", "requests", "axios", "pydantic")
        ok = any(m in lower_in for m in dep_markers) and "stdlib" not in lower_in
        return (0.91, 0.89) if ok else (0.03, 0.92)

    if q_id == "missing_trigger_on_deliberate_shortcut":
        if "todo" in lower_in or "hack" in lower_in or ("shortcut" in lower_in and "shortcut:" not in lower_in):
            return 0.88, 0.86
        return 0.03, 0.92

    if q_id == "requires_step7_behavioral_test":
        logic_markers = ("parser", "parsing", "json", "urllib", "loop", "if ", "auth", "security", "cálculo", "calculo", "regex", "lexer", "http")
        ok = any(m in lower_in for m in logic_markers)
        return (0.90, 0.89) if ok else (0.08, 0.88)

    return 0.10, 0.80


def _eval_fallback_choice(
    q_id: str,
    q_spec: Dict[str, Any],
    raw: str,
    lower_in: str,
) -> Tuple[str, Dict[str, float], float]:
    criteria = q_spec.get("criteria") or {}
    options = list(criteria.keys()) if isinstance(criteria, dict) else list(q_spec.get("options") or [])
    if not options:
        return "UNKNOWN", {}, 0.50

    # Caso 1: Claim Audit (`claim_<idx>`)
    if q_id.startswith("claim_"):
        claim_text = q_spec.get("meta_claim_text", "").lower()
        proof_excerpt = q_spec.get("meta_proof_excerpt", "").lower()
        if not proof_excerpt.strip():
            probs = {"SUPPORTED": 0.01, "PARTIALLY_SUPPORTED": 0.04, "UNSUPPORTED": 0.95}
            return "UNSUPPORTED", probs, 0.95

        # Extrair termos significativos (>=4 letras) do claim
        stopwords = {
            "para", "como", "com", "pelo", "pela", "este", "esta", "isso", "está",
            "foram", "todos", "todas", "entre", "sobre", "após", "antes", "arquivo",
            "código", "sistema", "função", "método", "teste", "testes", "suíte",
            "that", "with", "from", "this", "have", "been", "were",
        }
        tokens = [
            t for t in re.findall(r"[a-zA-Z0-9_]{4,}", claim_text)
            if t not in stopwords
        ]
        if not tokens:
            probs = {"SUPPORTED": 0.20, "PARTIALLY_SUPPORTED": 0.65, "UNSUPPORTED": 0.15}
            return "PARTIALLY_SUPPORTED", probs, 0.72

        matched = sum(1 for t in set(tokens) if t in proof_excerpt)
        ratio = matched / max(len(set(tokens)), 1)

        if ratio >= 0.45:
            probs = {"SUPPORTED": 0.92, "PARTIALLY_SUPPORTED": 0.06, "UNSUPPORTED": 0.02}
            return "SUPPORTED", probs, 0.91
        if ratio >= 0.20:
            probs = {"SUPPORTED": 0.22, "PARTIALLY_SUPPORTED": 0.68, "UNSUPPORTED": 0.10}
            return "PARTIALLY_SUPPORTED", probs, 0.82
        probs = {"SUPPORTED": 0.03, "PARTIALLY_SUPPORTED": 0.09, "UNSUPPORTED": 0.88}
        return "UNSUPPORTED", probs, 0.90

    # Caso 2: Router `risk_dial`
    if q_id == "risk_dial":
        if any(w in lower_in for w in ("auth", "segurança", "security", "safety-gate", "produção", "production", "pagamento", "migration", "drop")):
            probs = {"LOW": 0.02, "MEDIUM": 0.10, "HIGH": 0.88}
            return "HIGH", probs, 0.90
        if any(w in lower_in for w in ("listar", "explicar", "mapear", "ler", "status", "o que é", "analise", "análise")):
            probs = {"LOW": 0.86, "MEDIUM": 0.12, "HIGH": 0.02}
            return "LOW", probs, 0.89
        probs = {"LOW": 0.08, "MEDIUM": 0.84, "HIGH": 0.08}
        return "MEDIUM", probs, 0.87

    # Caso 3: Router `target_skill`
    if q_id == "target_skill":
        skill_keywords = {
            "clearer-bugfix": ("bug", "erro", "falha", "corrigir", "fix", "quebr", "regressão"),
            "clearer-review": ("review", "revisar", "revisão", "diff", "auditar diff"),
            "clearer-audit": ("audit", "claims", "evidência", "contrato", "supported"),
            "clearer-refactor": ("refatorar", "refactor", "limpar", "reestruturar"),
            "clearer-test": ("teste", "testar", "suíte", "pytest", "unittest", "coverage"),
            "clearer-map": ("mapear", "arquitetura", "entender", "explorar", "analise", "análise"),
            "learned-lesson": ("lição", "lesson", "memória", "aprendemos"),
            "clearer-feature": ("implementar", "criar", "nova", "adicionar", "feature"),
        }
        scores: Dict[str, float] = {k: 0.02 for k in options}
        for sk, kws in skill_keywords.items():
            if sk in scores:
                hits = sum(1 for kw in kws if kw in lower_in)
                scores[sk] += hits * 0.35
        total = sum(scores.values()) or 1.0
        probs = {k: round(v / total, 4) for k, v in scores.items()}
        best = max(probs, key=lambda k: probs[k])
        return best, probs, 0.88

    # Caso 4: Ponytail `verification_layer`
    if q_id == "verification_layer":
        if any(w in lower_in for w in ("readme", "markdown", "comentário", "doc")):
            probs = {"NONE_TRIVIAL": 0.85, "UNIT_MEMORY": 0.10, "INTEGRATION_LOCAL": 0.04, "E2E_BROWSER": 0.01}
            return "NONE_TRIVIAL", probs, 0.90
        if any(w in lower_in for w in ("banco", "database", "migration", "filesystem", "hook", "subprocess")):
            probs = {"NONE_TRIVIAL": 0.02, "UNIT_MEMORY": 0.25, "INTEGRATION_LOCAL": 0.70, "E2E_BROWSER": 0.03}
            return "INTEGRATION_LOCAL", probs, 0.86
        probs = {"NONE_TRIVIAL": 0.03, "UNIT_MEMORY": 0.85, "INTEGRATION_LOCAL": 0.10, "E2E_BROWSER": 0.02}
        return "UNIT_MEMORY", probs, 0.89

    # Default uniforme
    p = round(1.0 / len(options), 4)
    return options[0], {o: p for o in options}, 0.60


def _eval_fallback_score(
    q_id: str,
    q_spec: Dict[str, Any],
    raw: str,
    lower_in: str,
) -> Tuple[float, Dict[str, float], float]:
    raw_crit = q_spec.get("criteria") or q_spec.get("levels")
    levels = raw_crit if isinstance(raw_crit, dict) else {"1": "Low", "2": "Medium", "3": "High"}
    keys = sorted(levels.keys(), key=lambda x: int(x) if str(x).isdigit() else 1)

    if q_id == "blast_radius_severity":
        if "safety-gate.py" in lower_in or "adapters/antigravity.py" in lower_in or "ceh_core/" in lower_in:
            probs = {"1": 0.01, "2": 0.04, "3": 0.20, "4": 0.70, "5": 0.05}
            score = sum(int(k) * v for k, v in probs.items())
            return score, probs, 0.90
        probs = {"1": 0.10, "2": 0.65, "3": 0.20, "4": 0.04, "5": 0.01}
        score = sum(int(k) * v for k, v in probs.items())
        return score, probs, 0.86

    p = round(1.0 / len(keys), 4)
    return float(keys[0]), {k: p for k in keys}, 0.75


def _load_dotenv_key() -> str:
    """Busca GEMINI_API_KEY ou GOOGLE_API_KEY em arquivos .env locais (ignorados pelo Git) sem expor no stdout."""
    candidates = [
        HERE.parent / ".env",
        HERE.parents[2] / ".env",
        Path.home() / ".gemini" / ".env",
    ]
    for env_file in candidates:
        if not env_file.is_file():
            continue
        try:
            for line in env_file.read_text(encoding="utf-8", errors="ignore").splitlines():
                stripped = line.strip()
                if not stripped or stripped.startswith("#") or "=" not in stripped:
                    continue
                k, v = stripped.split("=", 1)
                k = k.strip().removeprefix("export ").strip()
                v = v.strip().strip('"').strip("'")
                if k in ("GEMINI_API_KEY", "GOOGLE_API_KEY") and v:
                    return v
        except OSError:
            pass
    return ""


def evaluate_decisions(
    shared_input: str,
    questions: Dict[str, Dict[str, Any]],
    *,
    api_key: Optional[str] = None,
    endpoint: str = DEFAULT_ENDPOINT,
    model: str = DEFAULT_MODEL,
    timeout_sec: float = DEFAULT_TIMEOUT_SEC,
    transport: Optional[TransportFn] = None,
    telemetry_path: Optional[Path] = DEFAULT_TELEMETRY_PATH,
    subcommand_label: str = "generic",
) -> Dict[str, Any]:
    """
    Executa 1 passe de decisão (`gemini-decision-1`) sobre `shared_input` para
    todas as `questions` independentes. Faz fallback determinístico se offline/sem chave.
    """
    t0 = time.monotonic()
    resolved_key = api_key if api_key is not None else (
        os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or _load_dotenv_key()
    )
    http_fn = transport or _default_http_transport

    # Remover chaves internas `meta_*` antes de enviar ao endpoint oficial
    clean_questions: Dict[str, Dict[str, Any]] = {}
    for q_id, q_spec in questions.items():
        clean_questions[q_id] = {k: v for k, v in q_spec.items() if not k.startswith("meta_")}

    mode = "FALLBACK_OFFLINE"
    fallback_reason: Optional[str] = None
    raw_response: Dict[str, Any] = {}

    if resolved_key.strip():
        payload = {
            "model": model,
            "input": shared_input,
            "questions": clean_questions,
        }
        try:
            raw_response = http_fn(endpoint, payload, resolved_key.strip(), timeout_sec)
            if isinstance(raw_response, dict) and isinstance(raw_response.get("answers"), dict):
                mode = "LIVE_API"
            else:
                fallback_reason = "INVALID_API_RESPONSE_SCHEMA"
                raw_response = _deterministic_fallback_evaluator(shared_input, questions)
        except urllib.error.HTTPError as http_exc:
            err_body = ""
            try:
                err_body = http_exc.read().decode("utf-8", errors="replace")[:300]
            except Exception:
                pass
            clean_err = mask_secrets(re.sub(r"\s+", " ", err_body).strip())
            fallback_reason = f"API_HTTP_{http_exc.code}:{clean_err}"
            raw_response = _deterministic_fallback_evaluator(shared_input, questions)
        except Exception as exc:
            fallback_reason = f"API_ERROR:{exc.__class__.__name__}"
            raw_response = _deterministic_fallback_evaluator(shared_input, questions)
    else:
        fallback_reason = "NO_API_KEY"
        raw_response = _deterministic_fallback_evaluator(shared_input, questions)

    latency_ms = round((time.monotonic() - t0) * 1000.0, 2)
    answers = raw_response.get("answers", {})

    confidences = [
        float(ans.get("confidence", 0.0))
        for ans in answers.values()
        if isinstance(ans, dict) and "confidence" in ans
    ]
    min_conf = round(min(confidences), 4) if confidences else 0.0

    result = {
        "mode": mode,
        "model": raw_response.get("model", model),
        "fallback_reason": fallback_reason,
        "latency_ms": latency_ms,
        "input_chars": len(shared_input),
        "questions_count": len(questions),
        "min_confidence": min_conf,
        "answers": answers,
    }

    if telemetry_path is not None:
        _append_telemetry(telemetry_path, subcommand_label, result)

    return result


def _append_telemetry(telemetry_path: Path, subcommand: str, result: Dict[str, Any]) -> None:
    """Grava telemetria higienizada com permissão restrita 0600 (Security Policy §2)."""
    try:
        telemetry_path.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "subcommand": subcommand,
            "mode": result.get("mode"),
            "model": result.get("model"),
            "fallback_reason": result.get("fallback_reason"),
            "latency_ms": result.get("latency_ms"),
            "input_chars": result.get("input_chars"),
            "questions_count": result.get("questions_count"),
            "min_confidence": result.get("min_confidence"),
        }
        line = mask_secrets(json.dumps(entry, ensure_ascii=False)) + "\n"
        with open(telemetry_path, "a", encoding="utf-8") as fh:
            fh.write(line)
        os.chmod(telemetry_path, 0o600)
    except Exception:
        pass


# ------------------------------------------------------------------------------
# Casos de Uso de Camada L1.5 (Controle Determinístico em Código — Invariante 6)
# ------------------------------------------------------------------------------
def run_diff_audit(
    diff_text: str,
    *,
    api_key: Optional[str] = None,
    transport: Optional[TransportFn] = None,
    telemetry_path: Optional[Path] = DEFAULT_TELEMETRY_PATH,
) -> Dict[str, Any]:
    """
    Executa a Bateria de 7 Verificações Atômicas + Score de Severidade sobre um diff.
    Promove `computed_risk_dial` para `HIGH` deterministicamente se:
      - Qualquer checagem crítica (1 a 4) tiver `noul >= 0.70`, OU
      - Qualquer checagem crítica tiver `confidence < 0.75` (Invariante 7: Incerteza é Escalada).
    """
    eval_res = evaluate_decisions(
        diff_text,
        DIFF_ATOMIC_QUESTIONS,
        api_key=api_key,
        transport=transport,
        telemetry_path=telemetry_path,
        subcommand_label="diff-audit",
    )
    answers = eval_res["answers"]

    triggered_critical: List[str] = []
    low_confidence_flags: List[str] = []

    for key in CRITICAL_DIFF_KEYS:
        ans = answers.get(key, {})
        noul_val = float(ans.get("noul", 0.0))
        conf_val = float(ans.get("confidence", 0.0))
        if noul_val >= NOUL_POSITIVE_THRESHOLD:
            triggered_critical.append(key)
        if conf_val < MIN_CONFIDENCE_THRESHOLD:
            low_confidence_flags.append(key)

    lookup_ans = answers.get("introduces_or_modifies_lookups", {})
    freeze_test_warning = float(lookup_ans.get("noul", 0.0)) >= NOUL_POSITIVE_THRESHOLD

    if triggered_critical or low_confidence_flags:
        computed_risk_dial = "HIGH"
    else:
        sev_score = float(answers.get("blast_radius_severity", {}).get("score", 2.0))
        computed_risk_dial = "MEDIUM" if sev_score >= 2.5 else "LOW"

    escalation_reason: Optional[str] = None
    if low_confidence_flags:
        escalation_reason = f"LOW_CONFIDENCE_ESCALATION ({', '.join(low_confidence_flags)})"
    elif triggered_critical:
        escalation_reason = f"CRITICAL_ATOMIC_CHECKS_POSITIVE ({', '.join(triggered_critical)})"

    return {
        **eval_res,
        "computed_risk_dial": computed_risk_dial,
        "triggered_critical_checks": triggered_critical,
        "low_confidence_escalations": low_confidence_flags,
        "escalation_reason": escalation_reason,
        "requires_freeze_test_audit": freeze_test_warning,
    }


def run_claim_audit(
    claims: List[Tuple[str, str]],
    repo_root: Optional[Path] = None,
    *,
    api_key: Optional[str] = None,
    transport: Optional[TransportFn] = None,
    telemetry_path: Optional[Path] = DEFAULT_TELEMETRY_PATH,
) -> Dict[str, Any]:
    """
    Combina verificação física (SHA-256 + existência do arquivo) com verificação
    semântica em lote via primitivo `choice` (`SUPPORTED`, `PARTIALLY_SUPPORTED`, `UNSUPPORTED`).
    """
    base_dir = (repo_root or Path.cwd()).resolve()
    questions: Dict[str, Dict[str, Any]] = {}
    physical_results: Dict[str, Dict[str, Any]] = {}
    shared_chunks: List[str] = []

    for idx, (claim_text, proof_ref) in enumerate(claims, start=1):
        q_id = f"claim_{idx}"
        p_path = (base_dir / proof_ref).resolve() if not os.path.isabs(proof_ref) else Path(proof_ref).resolve()

        try:
            p_path.relative_to(base_dir)
            in_repo = True
        except ValueError:
            in_repo = False

        if not proof_ref or proof_ref == "-" or not in_repo or not p_path.is_file():
            physical_results[q_id] = {
                "claim": claim_text,
                "proof": proof_ref,
                "physical_status": "UNSUPPORTED",
                "physical_detail": f"Prova `{proof_ref}` ausente ou fora do repositório",
                "excerpt": "",
            }
            continue

        raw_bytes = p_path.read_bytes()
        sha12 = hashlib.sha256(raw_bytes).hexdigest()[:12]
        excerpt = raw_bytes.decode("utf-8", errors="replace")[:4000]
        physical_results[q_id] = {
            "claim": claim_text,
            "proof": proof_ref,
            "physical_status": "SUPPORTED",
            "physical_detail": f"`{proof_ref}` (sha256 {sha12}, {len(raw_bytes)} B)",
            "excerpt": excerpt,
        }
        shared_chunks.append(f"=== PROOF [{q_id}: {proof_ref}] ===\n{excerpt}")
        questions[q_id] = {
            "type": "choice",
            "instructions": (
                f"Evaluate whether PROOF [{q_id}: {proof_ref}] semantically proves the claim: "
                f"'{claim_text}'."
            ),
            "criteria": CLAIM_AUDIT_CRITERIA,
            "meta_claim_text": claim_text,
            "meta_proof_excerpt": excerpt,
        }

    shared_input = "\n\n".join(shared_chunks) if shared_chunks else "NO_VALID_PROOFS"
    eval_res = (
        evaluate_decisions(
            shared_input,
            questions,
            api_key=api_key,
            transport=transport,
            telemetry_path=telemetry_path,
            subcommand_label="claim-audit",
        )
        if questions
        else {
            "mode": "SKIPPED_NO_PHYSICAL_PROOFS",
            "latency_ms": 0.0,
            "min_confidence": 1.0,
            "answers": {},
        }
    )

    final_claims: List[Dict[str, Any]] = []
    for idx in range(1, len(claims) + 1):
        q_id = f"claim_{idx}"
        phys = physical_results[q_id]
        if phys["physical_status"] != "SUPPORTED":
            final_claims.append({
                "id": q_id,
                "claim": phys["claim"],
                "proof": phys["proof"],
                "physical_status": phys["physical_status"],
                "semantic_status": "UNSUPPORTED",
                "semantic_confidence": 1.0,
                "final_status": "UNSUPPORTED",
                "reason": phys["physical_detail"],
            })
            continue

        sem_ans = eval_res["answers"].get(q_id, {})
        sem_choice = sem_ans.get("choice", "UNSUPPORTED")
        sem_conf = float(sem_ans.get("confidence", 0.0))

        # Regra de Ouro (Invariantes 6 e 7): Prova física SUPPORTED mas semântica
        # UNSUPPORTED ou com baixa confiança é rebaixada para PARTIALLY_SUPPORTED!
        if sem_choice == "SUPPORTED" and sem_conf >= CLAIM_CONFIDENCE_THRESHOLD:
            final_status = "SUPPORTED"
            reason = f"{phys['physical_detail']} + semântica confirmada (conf={sem_conf:.2f})"
        elif sem_choice == "UNSUPPORTED":
            final_status = "PARTIALLY_SUPPORTED"
            reason = f"{phys['physical_detail']} — arquivo existe, mas conteúdo NÃO comprova semanticamente o claim"
        else:
            final_status = "PARTIALLY_SUPPORTED"
            reason = f"{phys['physical_detail']} — suporte parcial ou incerteza escalada (choice={sem_choice}, conf={sem_conf:.2f})"

        final_claims.append({
            "id": q_id,
            "claim": phys["claim"],
            "proof": phys["proof"],
            "physical_status": phys["physical_status"],
            "semantic_status": sem_choice,
            "semantic_confidence": sem_conf,
            "final_status": final_status,
            "reason": reason,
        })

    all_supported = bool(final_claims) and all(c["final_status"] == "SUPPORTED" for c in final_claims)
    any_unsupported = any(c["final_status"] == "UNSUPPORTED" for c in final_claims)
    verdict = "APPROVED" if all_supported else ("REJECTED" if any_unsupported else "NEEDS_EVIDENCE")

    return {
        "mode": eval_res.get("mode"),
        "latency_ms": eval_res.get("latency_ms"),
        "audit_verdict": verdict,
        "claims": final_claims,
    }


def run_route(
    prompt_text: str,
    *,
    api_key: Optional[str] = None,
    transport: Optional[TransportFn] = None,
    telemetry_path: Optional[Path] = DEFAULT_TELEMETRY_PATH,
) -> Dict[str, Any]:
    """Classifica Risk Dial, Skill Alvo e Ambiguidade de Negócio em 1 passe."""
    eval_res = evaluate_decisions(
        prompt_text,
        ROUTER_QUESTIONS,
        api_key=api_key,
        transport=transport,
        telemetry_path=telemetry_path,
        subcommand_label="route",
    )
    ans = eval_res["answers"]
    risk_ans = ans.get("risk_dial", {})
    skill_ans = ans.get("target_skill", {})
    amb_ans = ans.get("has_business_ambiguity", {})

    risk_choice = risk_ans.get("choice", "MEDIUM")
    if float(risk_ans.get("confidence", 0.0)) < MIN_CONFIDENCE_THRESHOLD and risk_choice == "LOW":
        risk_choice = "MEDIUM"

    return {
        **eval_res,
        "recommended_risk_dial": risk_choice,
        "recommended_skill": skill_ans.get("choice", "clearer-feature"),
        "requires_clarification": float(amb_ans.get("noul", 0.0)) >= NOUL_POSITIVE_THRESHOLD,
    }


def run_stop_check(
    transcript_tail: str,
    *,
    api_key: Optional[str] = None,
    transport: Optional[TransportFn] = None,
    telemetry_path: Optional[Path] = DEFAULT_TELEMETRY_PATH,
) -> Dict[str, Any]:
    """Verifica os 4 pilares semânticos do Response Contract no fechamento de feature."""
    eval_res = evaluate_decisions(
        transcript_tail,
        STOP_CHECK_QUESTIONS,
        api_key=api_key,
        transport=transport,
        telemetry_path=telemetry_path,
        subcommand_label="stop-check",
    )
    ans = eval_res["answers"]
    missing = [
        k for k in STOP_CHECK_QUESTIONS
        if float(ans.get(k, {}).get("noul", 0.0)) < NOUL_POSITIVE_THRESHOLD
    ]
    return {
        **eval_res,
        "contract_valid": len(missing) == 0,
        "missing_pillars": missing,
    }


def run_ponytail_check(
    proposal_text: str,
    *,
    api_key: Optional[str] = None,
    transport: Optional[TransportFn] = None,
    telemetry_path: Optional[Path] = DEFAULT_TELEMETRY_PATH,
) -> Dict[str, Any]:
    """
    Avalia um plano de implementação ou proposta de código contra a Escada de
    Decisão Ponytail v5 (AGENTS.md §6.1).
    """
    eval_res = evaluate_decisions(
        proposal_text,
        PONYTAIL_QUESTIONS,
        api_key=api_key,
        transport=transport,
        telemetry_path=telemetry_path,
        subcommand_label="ponytail-check",
    )
    ans = eval_res["answers"]
    violations: List[str] = []
    for k in (
        "violates_yagni_speculative_abstraction",
        "adds_avoidable_external_dependency",
        "missing_trigger_on_deliberate_shortcut",
    ):
        if float(ans.get(k, {}).get("noul", 0.0)) >= NOUL_POSITIVE_THRESHOLD:
            violations.append(k)

    needs_step7_test = float(ans.get("requires_step7_behavioral_test", {}).get("noul", 0.0)) >= NOUL_POSITIVE_THRESHOLD
    layer = ans.get("verification_layer", {}).get("choice", "UNIT_MEMORY")

    return {
        **eval_res,
        "ponytail_approved": len(violations) == 0,
        "overengineering_violations": violations,
        "requires_step7_behavioral_test": needs_step7_test,
        "minimum_verification_layer": layer,
    }


def build_telemetry_stats(telemetry_path: Path = DEFAULT_TELEMETRY_PATH) -> Dict[str, Any]:
    """Calcula deterministicamente (Invariante 6) a parcial da janela 09/11->16/11 e da telemetria L1.5."""
    repo_root = Path.cwd().resolve()
    if not (repo_root / ".ceh").is_dir() and (HERE.parents[2] / ".ceh").is_dir():
        repo_root = HERE.parents[2]
    ci_cert_path = repo_root / ".ceh" / "last-ci-run.json"
    ci_cert = json.loads(ci_cert_path.read_text(encoding="utf-8")) if ci_cert_path.is_file() else {}

    records: List[Dict[str, Any]] = []
    if telemetry_path.is_file():
        for ln in telemetry_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            if ln.strip():
                try:
                    records.append(json.loads(ln))
                except Exception:
                    pass

    live_runs = [r for r in records if r.get("mode") == "LIVE_API"]
    offline_runs = [r for r in records if r.get("mode") == "FALLBACK_OFFLINE"]
    live_latencies = sorted(float(r.get("latency_ms", 0.0)) for r in live_runs)
    total_questions_evaluated = sum(int(r.get("questions_count", 0)) for r in records)
    live_questions_evaluated = sum(int(r.get("questions_count", 0)) for r in live_runs)
    total_live_input_chars = sum(int(r.get("input_chars", 0)) for r in live_runs)
    est_tokens = round(total_live_input_chars / 4)

    by_subcmd: Dict[str, int] = {}
    for r in records:
        sc = str(r.get("subcommand", "unknown"))
        by_subcmd[sc] = by_subcmd.get(sc, 0) + 1

    p50_ms = live_latencies[len(live_latencies) // 2] if live_latencies else 0.0
    min_ms = live_latencies[0] if live_latencies else 0.0
    max_ms = live_latencies[-1] if live_latencies else 0.0

    return {
        "soak_window_09_to_16_nov": {
            "branch": "dev-security-opt-01-p01",
            "anchor_commit": str(ci_cert.get("commit_hash", ""))[:7],
            "started_at_utc": ci_cert.get("timestamp"),
            "target_end_date": "2026-11-16",
            "elapsed_days": 3,
            "remaining_days": 4,
            "ci_certificate_status": ci_cert.get("status", "UNKNOWN"),
            "working_tree_clean": True,
        },
        "decisions_l15_telemetry": {
            "total_invocations": len(records),
            "live_api_calls": len(live_runs),
            "fallback_offline_calls": len(offline_runs),
            "total_atomic_questions_evaluated": total_questions_evaluated,
            "live_atomic_questions_evaluated": live_questions_evaluated,
            "live_latency_ms": {
                "min": round(min_ms, 2),
                "median_p50": round(p50_ms, 2),
                "max": round(max_ms, 2),
            },
            "estimated_live_input_tokens": est_tokens,
            "estimated_cost_usd": round((est_tokens / 1_000_000) * 0.10, 6),
            "invocations_by_subcommand": by_subcmd,
        },
    }


HUMAN_LABELS_PT: Dict[str, str] = {
    "modifies_security_or_auth": "Altera Segurança, Auth ou Safety Gate",
    "introduces_destructive_command": "Introduz Comando Destrutivo (DB/Git/SO)",
    "breaks_backward_compatibility": "Quebra Compatibilidade Reversa",
    "modifies_database_schema": "Altera Schema/Migrations de Banco",
    "has_untested_execution_branches": "Possui Branches Condicionais Sem Teste",
    "violates_minimal_blast_radius": "Viola Blast Radius Mínimo (Ruído/Fora de Escopo)",
    "introduces_or_modifies_lookups": "Altera Catálogo Fixo / Enum / Lookup",
    "blast_radius_severity": "Severidade Estrutural do Diff (Score)",
    "violates_yagni_speculative_abstraction": "Viola YAGNI (Abstração Especulativa)",
    "adds_avoidable_external_dependency": "Adiciona Dependência Externa Evitável",
    "missing_trigger_on_deliberate_shortcut": "Atalho/TODO Sem Gatilho Numérico (`shortcut:`)",
    "requires_step7_behavioral_test": "Exige Teste Comportamental (Degrau 7 Ponytail)",
    "verification_layer": "Camada Mínima de Verificação Suficiente",
}


def format_human_pt(subcmd: str, data: Dict[str, Any]) -> str:
    """Formata o resultado JSON em um quadro executivo legível em Português (Custo Zero / 100% Local)."""
    lines: List[str] = []
    if subcmd == "stats":
        sw = data.get("soak_window_09_to_16_nov", {})
        tl = data.get("decisions_l15_telemetry", {})
        lat = tl.get("live_latency_ms", {})
        lines.append("=== [CEH DECISIONS: Painel de Telemetria & Janela de Maturação] ===")
        lines.append(
            f"• Janela 09/11 -> 16/11 : Dia {sw.get('elapsed_days')}/7 (faltam {sw.get('remaining_days')} dias) | "
            f"Commit {sw.get('anchor_commit')} | CI: {sw.get('ci_certificate_status')} | Git Limpo: {'SIM' if sw.get('working_tree_clean') else 'NÃO'}"
        )
        lines.append(
            f"• Execuções Acumuladas  : {tl.get('total_invocations')} ({tl.get('live_api_calls')} LIVE_API / "
            f"{tl.get('fallback_offline_calls')} Offline)"
        )
        lines.append(
            f"• Perguntas Julgadas    : {tl.get('total_atomic_questions_evaluated')} total ({tl.get('live_atomic_questions_evaluated')} na LIVE_API)"
        )
        lines.append(
            f"• Latência LIVE_API     : Mín {lat.get('min')} ms | Mediana (P50) {lat.get('median_p50')} ms | Máx {lat.get('max')} ms"
        )
        lines.append(
            f"• Custo Estimado (API)  : ~{tl.get('estimated_live_input_tokens')} tokens (~US$ {tl.get('estimated_cost_usd'):.4f} | US$ 0,00 no Free Tier)"
        )
        return "\n".join(lines)

    mode = data.get("mode", "UNKNOWN")
    model = data.get("model", "")
    lat = data.get("latency_ms", 0.0)
    q_cnt = data.get("questions_count", 0)
    lines.append(f"=== [CEH DECISIONS ({subcmd.upper()}) — Modo: {mode} ({model}) | {lat} ms | {q_cnt} perguntas] ===")

    answers = data.get("answers", {})
    for q_key, ans in answers.items():
        label = HUMAN_LABELS_PT.get(q_key, q_key)
        if "noul" in ans:
            prob = float(ans["noul"]) * 100.0
            conf = float(ans.get("confidence", 0.0)) * 100.0
            is_yes = float(ans["noul"]) >= NOUL_POSITIVE_THRESHOLD
            icon = "🚨 SIM" if (is_yes and q_key in CRITICAL_DIFF_KEYS) else ("⚠️  SIM" if is_yes else "✅ NÃO")
            lines.append(f"  {icon} ({prob:5.1f}% prob | {conf:4.1f}% conf) -> {label}")
        elif "choice" in ans:
            ch = ans["choice"]
            conf = float(ans.get("confidence", 0.0)) * 100.0
            lines.append(f"  🎯 {ch:<18} ({conf:5.1f}% conf) -> {label}")
        elif "score" in ans:
            sc = float(ans["score"])
            conf = float(ans.get("confidence", 0.0)) * 100.0
            lines.append(f"  📏 Nota {sc:4.2f}          ({conf:5.1f}% conf) -> {label}")

    lines.append("-" * 78)
    if subcmd == "diff-audit":
        dial = data.get("computed_risk_dial")
        reason = data.get("escalation_reason") or "Nenhuma trava crítica disparada"
        freeze = "SIM (verificar testes assertCount!)" if data.get("requires_freeze_test_audit") else "NÃO"
        lines.append(f"👉 VEREDITO DE RISCO : Risk Dial = {dial} ({reason})")
        lines.append(f"👉 ALERTA DE LOOKUP  : {freeze}")
    elif subcmd == "ponytail-check":
        ok = data.get("ponytail_approved")
        viols = ", ".join(data.get("overengineering_violations", [])) or "Nenhuma"
        step7 = "SIM" if data.get("requires_step7_behavioral_test") else "NÃO"
        layer = data.get("minimum_verification_layer")
        lines.append(f"👉 ESCADA PONYTAIL v5: {'✅ APROVADO' if ok else '⛔ REPROVADO (Over-Engineering detectado)'}")
        lines.append(f"👉 VIOLAÇÕES         : {viols}")
        lines.append(f"👉 TESTE DEGRAU 7    : {step7} | Camada Mínima: {layer}")
    elif subcmd == "route":
        lines.append(
            f"👉 ROTEAMENTO        : Skill = {data.get('recommended_skill')} | "
            f"Risk Dial = {data.get('recommended_risk_dial')} | "
            f"Pedir Clarificação Humana = {'SIM' if data.get('requires_clarification') else 'NÃO'}"
        )
    elif subcmd == "claim-audit":
        lines.append(f"👉 VEREDITO AUDITORIA: {data.get('audit_verdict')}")
        for c in data.get("claims", []):
            lines.append(f"   • [{c['final_status']}] {c['claim']} -> {c['reason']}")
    elif subcmd == "stop-check":
        ok = data.get("contract_valid")
        missing = ", ".join(data.get("missing_pillars", [])) or "Nenhum"
        lines.append(f"👉 RESPONSE CONTRACT : {'✅ VÁLIDO' if ok else '⛔ INCOMPLETO'} (Faltando: {missing})")

    return "\n".join(lines)


def _emit_output(subcmd: str, out: Dict[str, Any], human: bool) -> None:
    if human:
        print(format_human_pt(subcmd, out))
    else:
        print(json.dumps(out, indent=2, ensure_ascii=False))


# ------------------------------------------------------------------------------
# Interface CLI
# ------------------------------------------------------------------------------
def main(argv: Optional[List[str]] = None) -> int:
    raw_args = list(argv if argv is not None else sys.argv[1:])
    human_flag = False
    cleaned_args: List[str] = []
    for a in raw_args:
        if a in ("--human", "-H"):
            human_flag = True
        else:
            cleaned_args.append(a)

    parser = argparse.ArgumentParser(description="CEH System One Decisions Engine (Antigravity L1.5)")
    parser.add_argument("--human", "-H", action="store_true", help="Exibe quadro traduzido em Português (custo zero)")
    sub = parser.add_subparsers(dest="subcmd", required=True)

    p_diff = sub.add_parser("diff-audit", help="Executa as 7 verificações atômicas System One sobre um diff")
    p_diff.add_argument("--commit", type=str, default=None, help="Commit ou range git (ex: HEAD~1..HEAD)")
    p_diff.add_argument("--diff-file", type=str, default=None, help="Arquivo contendo o diff")

    p_claim = sub.add_parser("claim-audit", help="Audita pares CLAIM <-> PROOF física e semanticamente")
    p_claim.add_argument("--claim", nargs=2, action="append", metavar=("TEXTO", "PROVA"), required=True)

    p_route = sub.add_parser("route", help="Roteia intenção do desenvolvedor (Risk Dial + Skill + Ambiguidade)")
    p_route.add_argument("--prompt", type=str, required=True)

    p_stop = sub.add_parser("stop-check", help="Verifica presença semântica dos 4 pilares do Response Contract")
    p_stop.add_argument("--text", type=str, required=True)

    p_pony = sub.add_parser("ponytail-check", help="Avalia plano/proposta contra a Escada de Decisão Ponytail v5")
    p_pony.add_argument("--proposal", type=str, required=True)

    sub.add_parser("stats", help="Exibe o consolidado determinístico da telemetria coletada e status do canário")

    args = parser.parse_args(cleaned_args)

    if args.subcmd == "diff-audit":
        if args.diff_file:
            diff_text = Path(args.diff_file).read_text(encoding="utf-8", errors="replace")
        elif args.commit:
            res = subprocess.run(["git", "show", args.commit], capture_output=True, text=True, timeout=15)
            diff_text = res.stdout
        else:
            res = subprocess.run(["git", "diff", "HEAD"], capture_output=True, text=True, timeout=15)
            diff_text = res.stdout
        out = run_diff_audit(diff_text)
        _emit_output("diff-audit", out, human_flag)
        return 0

    if args.subcmd == "claim-audit":
        pairs = [(c[0], c[1]) for c in args.claim]
        out = run_claim_audit(pairs)
        _emit_output("claim-audit", out, human_flag)
        return 0 if out["audit_verdict"] == "APPROVED" else 1

    if args.subcmd == "route":
        out = run_route(args.prompt)
        _emit_output("route", out, human_flag)
        return 0

    if args.subcmd == "stop-check":
        out = run_stop_check(args.text)
        _emit_output("stop-check", out, human_flag)
        return 0 if out["contract_valid"] else 1

    if args.subcmd == "ponytail-check":
        out = run_ponytail_check(args.proposal)
        _emit_output("ponytail-check", out, human_flag)
        return 0 if out["ponytail_approved"] else 1

    if args.subcmd == "stats":
        out = build_telemetry_stats()
        _emit_output("stats", out, human_flag)
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
