#!/usr/bin/env python3
"""
evidence_report.py - Relatório canônico de evidências do CEH (Response Contract).

O relatório só afirma o que consegue provar:
  - RESULT e CONFIDENCE são CALCULADOS (git + certificado + provas); nunca aceitos
    como argumento (Invariante 6: código detém o veredito).
  - Cada afirmação (--claim) e critério de aceite (--criterion) exige uma prova:
    um arquivo do repositório (fixado por sha256) ou `commit:<sha>` na história do HEAD.
    SUPPORTED = prova versionada e intacta; PARTIALLY_SUPPORTED = prova existe mas
    não é auditável por terceiros (não versionada/modificada/fora do HEAD);
    UNSUPPORTED = prova ausente.
  - Achados de revisão (--finding) e riscos (--risk) são DECLARADOS e rotulados como tal;
    as contagens são feitas pelo código.

Uso:
  evidence-report.sh [--base REF] [--claim TEXTO PROVA]... [--criterion TEXTO PROVA]...
                     [--finding SEVERIDADE TEXTO]... [--risk TEXTO]... [--json ARQ] [--strict]
Somente stdlib; Python 3.8+.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
SEVERITIES = ("BLOCKER", "HIGH", "MEDIUM", "LOW", "INFO")
BASE_CANDIDATES = ("origin/dev", "origin/main", "dev", "main", "master")
# Mesmos padrões de diff-audit.sh (seções 3 e 4), aplicados só às linhas adicionadas.
SECRET_RE = re.compile(
    r"\b(bearer\s+[a-zA-Z0-9_\-\.]{20,}|api[_-]?key\s*[:=]\s*[\"'][a-zA-Z0-9_\-]{16,}[\"']"
    r"|ghp_[a-zA-Z0-9]{36}|AIza[0-9A-Za-z\-_]{35}|-----BEGIN\s+PRIVATE\s+KEY-----)", re.I)
CONFLICT_RE = re.compile(r"^(<<<<<<< |>>>>>>> |=======$)")


def git(*args: str) -> tuple[int, str]:
    res = subprocess.run(["git", *args], capture_output=True, text=True)
    return res.returncode, res.stdout.strip()


def resolve_base(requested: str | None, head: str) -> tuple[str | None, str]:
    candidates = [requested] if requested else list(BASE_CANDIDATES)
    for ref in candidates:
        code, sha = git("rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
        if code == 0:
            code, mb = git("merge-base", sha, head)
            if code == 0:
                return mb, f"{ref} ({'informada' if requested else 'auto'}; merge-base {mb[:7]})"
    return None, f"{requested} não encontrada" if requested else "nenhuma base encontrada (apenas alterações locais)"


def verify_proof(proof: str, head: str) -> tuple[str, str]:
    if proof in ("", "-"):
        return "UNSUPPORTED", "sem prova"
    if proof.startswith("commit:"):
        ref = proof.split(":", 1)[1]
        code, sha = git("rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
        if code != 0:
            return "UNSUPPORTED", f"commit `{ref}` não encontrado"
        if subprocess.run(["git", "merge-base", "--is-ancestor", sha, head]).returncode == 0:
            return "SUPPORTED", f"commit `{sha[:7]}` na história do HEAD"
        return "PARTIALLY_SUPPORTED", f"commit `{sha[:7]}` existe, mas fora da história do HEAD"
    path = Path(proof)
    if path.is_absolute() or ".." in path.parts or not path.is_file():
        return "UNSUPPORTED", f"`{proof}` inexistente ou fora do repositório"
    digest = hashlib.sha256(path.read_bytes()).hexdigest()[:12]
    where = f"`{proof}` (sha256 {digest}, {path.stat().st_size} B)"
    tracked = git("ls-files", "--error-unmatch", proof)[0] == 0
    changed = git("status", "--porcelain", "--", proof)[1] != ""
    if tracked and not changed:
        return "SUPPORTED", where
    return "PARTIALLY_SUPPORTED", where + (" — não versionada" if not tracked else " — modificada após o HEAD")


def load_certificate(head: str) -> dict:
    cert_path = Path(".ceh/last-ci-run.json")
    if not cert_path.is_file():
        return {"state": "NOT_RUN", "detail": "sem `.ceh/last-ci-run.json`: a suíte canônica não foi executada pelo test-runner"}
    try:
        cert = json.loads(cert_path.read_text(encoding="utf-8"))
    except ValueError as exc:
        return {"state": "INVALID", "detail": f"certificado ilegível ({exc})"}
    state = "PASS" if cert.get("status") == "PASS" and cert.get("exit_code") == 0 else "FAIL"
    if cert.get("commit_hash") != head:
        state = "STALE"
    elif state == "PASS" and cert.get("canonical_verified") is not True:
        state = "NOT_CANONICAL"
    log = Path(".ceh/last-ci-run.log")
    tail = [ln for ln in log.read_text(encoding="utf-8", errors="replace").splitlines() if ln.strip()][-4:] if log.is_file() else []
    return {"state": state, "cert": cert, "log_tail": tail,
            "detail": f"`{cert.get('normalized_runner') or cert.get('command')}` → exit {cert.get('exit_code')} "
                      f"em `{str(cert.get('commit_hash'))[:7]}` ({cert.get('timestamp')})"}


def load_evals_certificate(head: str) -> dict:
    eval_path = Path(".ceh/last-evals-run.json")
    if not eval_path.is_file():
        return {"state": "NOT_RUN", "detail": "sem `.ceh/last-evals-run.json`: os smoke-evals não foram executados"}
    try:
        ev = json.loads(eval_path.read_text(encoding="utf-8"))
    except ValueError as exc:
        return {"state": "INVALID", "detail": f"certificado de evals ilegível ({exc})"}
    state = "PASS" if ev.get("verdict") == "APROVA" and ev.get("passed") == ev.get("total") else "FAIL"
    if ev.get("commit") != head:
        state = "STALE"
    detail = f"{ev.get('passed')}/{ev.get('total')} critérios ({ev.get('verdict')}) em `{str(ev.get('commit'))[:7]}` ({ev.get('timestamp')})"
    if state == "STALE":
        detail += " [DESATUALIZADO]"
    return {"state": state, "cert": ev, "detail": detail}


FORBIDDEN_EXEC_STATE_RE = re.compile(r"\b(su[íi]tes?|evals?|smoke)\b.*\b(pass(ed|a)?|aprovad[oa]s?|verde|\d+/\d+)\b", re.I)


def detect_env() -> str:
    try:
        spec = importlib.util.spec_from_file_location("ceh_safety_gate", HERE.with_name("safety-gate.py"))
        gate = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gate)
        env, evidence = gate.detect_environment()
        return f"{env.upper()} (evidência: {evidence})"
    except Exception as exc:  # o relatório nunca inventa ambiente
        return f"UNKNOWN ({exc.__class__.__name__})"


def build(args) -> dict:
    code, head = git("rev-parse", "HEAD")
    if code != 0:
        sys.exit("ERRO: evidence-report precisa de um repositório git com ao menos um commit.")

    if args.strict:
        for t, _ in args.claim + args.criterion:
            if FORBIDDEN_EXEC_STATE_RE.search(t):
                sys.exit(
                    f"ERRO: Afirmação proibida com --strict: '{t}'. "
                    f"O estado da suíte e dos evals é calculado automaticamente a partir dos certificados em .ceh/, "
                    f"e não deve ser declarado manualmente como --claim ou --criterion."
                )

    base, base_desc = resolve_base(args.base, head)
    _, branch = git("branch", "--show-current")
    _, porcelain = git("status", "--porcelain")
    dirty = [ln for ln in porcelain.splitlines() if ln.strip()]
    commits = git("log", "--oneline", f"{base}..HEAD")[1].splitlines() if base else []
    files = git("diff", "--name-status", f"{base}...HEAD")[1].splitlines() if base else []
    stat = git("diff", "--shortstat", f"{base}...HEAD")[1] if base else ""
    diff_text = (git("diff", f"{base}...HEAD")[1] if base else "") + "\n" + git("diff", "HEAD")[1]
    added = [ln[1:] for ln in diff_text.splitlines() if ln.startswith("+") and not ln.startswith("+++")]
    secrets = sum(1 for ln in added if SECRET_RE.search(ln))
    conflicts = sum(1 for ln in added if CONFLICT_RE.match(ln))

    tests = load_certificate(head)
    evals = load_evals_certificate(head)
    claims = [{"text": t, "proof": p, **dict(zip(("status", "where"), verify_proof(p, head)))} for t, p in args.claim]
    criteria = [{"text": t, "proof": p, **dict(zip(("status", "where"), verify_proof(p, head)))} for t, p in args.criterion]
    findings = [{"severity": s.upper(), "text": t} for s, t in args.finding]
    bad_sev = [f["severity"] for f in findings if f["severity"] not in SEVERITIES]
    if bad_sev:
        sys.exit(f"ERRO: severidade inválida {bad_sev}; use {', '.join(SEVERITIES)}.")
    counts = {s: sum(1 for f in findings if f["severity"] == s) for s in SEVERITIES}

    pending = []
    if dirty:
        pending.append(f"Worktree com {len(dirty)} alteração(ões) não commitada(s): o certificado não as cobre.")
    if tests["state"] != "PASS":
        pending.append(f"Testes: {tests['state']} — {tests['detail']}.")
    if evals["state"] != "PASS":
        pending.append(f"Evals: {evals['state']} — {evals['detail']}.")
    for item in claims + criteria:
        if item["status"] != "SUPPORTED":
            pending.append(f"{item['status']}: \"{item['text']}\" ({item['where']}).")
    if secrets or conflicts:
        pending.append(f"Diff com {secrets} padrão(ões) de segredo e {conflicts} marcador(es) de conflito.")

    # Veredito e confiança: regras fechadas, calculadas (nunca declaradas).
    if tests["state"] == "FAIL" or evals["state"] == "FAIL" or counts["BLOCKER"] or secrets or conflicts:
        result = "FALHOU"
    elif tests["state"] == "PASS" and evals["state"] == "PASS" and not dirty and all(i["status"] == "SUPPORTED" for i in claims + criteria):
        result = "VERIFICADO"
    else:
        result = "NAO_VERIFICADO"
    if result == "VERIFICADO" and claims + criteria:
        confidence = ("ALTA", "1.0", "suíte e evals PASS no HEAD, worktree limpo e todas as afirmações com prova versionada")
    elif result == "VERIFICADO":
        confidence = ("MEDIA", "0.60", "suíte e evals PASS no HEAD, mas nenhuma afirmação ou critério foi amarrado a prova")
    elif result == "NAO_VERIFICADO" and tests["state"] == "PASS":
        confidence = ("MEDIA", "0.60", "testes PASS no HEAD, mas há pendências de evals, prova ou alterações não cobertas")
    else:
        confidence = ("BAIXA", "0.30", "sem evidência de testes/evals válida no HEAD ou com falha comprovada")

    return {"result": result, "branch": branch or "(detached)", "head": head, "base": base_desc,
            "environment": detect_env(), "commits": commits, "files": files, "shortstat": stat,
            "dirty": dirty, "tests": tests, "evals": evals, "claims": claims, "criteria": criteria,
            "findings": findings, "finding_counts": counts, "secrets": secrets, "conflicts": conflicts,
            "risks": list(args.risk), "pending": pending,
            "confidence": {"level": confidence[0], "score": confidence[1], "rule": confidence[2]}}


def render(r: dict) -> str:
    out = ["# Relatório de Evidências (CEH Response Contract)", "",
           "> Legenda: `OBSERVED` = obtido pelo código (git, certificado, hash); `DECLARADO` = texto informado "
           "pelo agente, só aceito com prova.", "", "## RESULT", "", f"**{r['result']}** (`OBSERVED`, calculado)", "",
           "## ENVIRONMENT", "", f"- Branch: `{r['branch']}` · HEAD: `{r['head'][:7]}` · Base: {r['base']}",
           f"- Ambiente: {r['environment']}", "", "## CHANGES", ""]
    if r["commits"]:
        out.append(f"Commits na branch ({len(r['commits'])}):")
        out += [f"- `{c}`" for c in r["commits"][:30]]
        out.append("")
    if r["files"]:
        out.append(f"Arquivos ({len(r['files'])}; {r['shortstat'] or 'sem estatística'}):")
        out += [f"- `{f.split(chr(9), 1)[0]}` {f.split(chr(9), 1)[-1]}" for f in r["files"][:40]]
        if len(r["files"]) > 40:
            out.append(f"- … e mais {len(r['files']) - 40} arquivo(s) (lista completa em `--json`).")
        out.append("")
    out += [f"- Não commitado: `{d}`" for d in r["dirty"]] or ["- Worktree limpo (`git status --porcelain` vazio)."]
    out += ["", "## EVIDENCE", ""]
    out += [f"- [{c['status']}] {c['text']} — {c['where']}" for c in r["claims"]] or \
           ["- Nenhuma afirmação registrada (use `--claim TEXTO PROVA`)."]
    t = r["tests"]
    ev = r.get("evals", {})
    out += ["", "## TESTS", "", f"- Suíte canônica: **{t['state']}** (`OBSERVED`) — {t['detail']}"]
    out += [f"  > {ln}" for ln in t.get("log_tail", [])]
    if ev:
        out += [f"- Smoke-evals: **{ev.get('state', 'UNKNOWN')}** (`OBSERVED`) — {ev.get('detail', '')}"]
    c = r["finding_counts"]
    out += ["", "## REVIEW", "", f"- Achados declarados: BLOCKER {c['BLOCKER']} · HIGH {c['HIGH']} · MEDIUM {c['MEDIUM']} · "
            f"LOW {c['LOW']} · INFO {c['INFO']}"]
    out += [f"  - [{f['severity']}] {f['text']} (`DECLARADO`)" for f in r["findings"]]
    out += [f"- Varredura do diff (`OBSERVED`): {r['secrets']} padrão(ões) de segredo, {r['conflicts']} marcador(es) de conflito.",
            "", "## ACCEPTANCE", ""]
    out += [f"- [{'x' if k['status'] == 'SUPPORTED' else ' '}] {k['text']} — {k['status']}: {k['where']}" for k in r["criteria"]] or \
           ["- Nenhum critério registrado (use `--criterion TEXTO PROVA`)."]
    out += ["", "## REMAINING RISKS", ""]
    out += [f"- {p} (`OBSERVED`)" for p in r["pending"]] + [f"- {k} (`DECLARADO`)" for k in r["risks"]] or \
           ["- Nenhuma pendência detectada e nenhum risco declarado."]
    k = r["confidence"]
    out += ["", "## CONFIDENCE", "", f"**{k['level']}** ({k['score']}) — regra: {k['rule']}."]
    return "\n".join(out) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Relatório canônico de evidências do CEH (veredito calculado)")
    parser.add_argument("--base", help="ref base da branch (padrão: " + ", ".join(BASE_CANDIDATES) + ")")
    parser.add_argument("--claim", nargs=2, action="append", default=[], metavar=("TEXTO", "PROVA"))
    parser.add_argument("--criterion", nargs=2, action="append", default=[], metavar=("TEXTO", "PROVA"))
    parser.add_argument("--finding", nargs=2, action="append", default=[], metavar=("SEVERIDADE", "TEXTO"))
    parser.add_argument("--risk", action="append", default=[], metavar="TEXTO")
    parser.add_argument("--json", metavar="ARQ", help="grava também o relatório em JSON")
    parser.add_argument("--strict", action="store_true", help="exit 1 se o RESULT não for VERIFICADO")
    args, extra = parser.parse_known_args()
    if extra:
        parser.error(f"argumentos não aceitos {extra}: RESULT e CONFIDENCE são calculados, não declarados.")
    top = git("rev-parse", "--show-toplevel")
    if top[0] != 0:
        sys.exit("ERRO: evidence-report precisa ser executado dentro de um repositório git.")
    import os
    os.chdir(top[1])
    report = build(args)
    print(render(report), end="")
    if args.json:
        Path(args.json).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return 1 if args.strict and report["result"] != "VERIFICADO" else 0


if __name__ == "__main__":
    sys.exit(main())
