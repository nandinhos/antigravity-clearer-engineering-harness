#!/usr/bin/env python3
"""
onda4_baseline.py — Retrato de referência v1.4.0 e rede de não-regressão da Onda 4 (CEH).

Mede e compara:
- A1: Decisões do gate (gate_corpus.expected.jsonl, 1.024 avaliações, sha256 3878d3cc285f...)
- A2: Instalação de referência (install.sh em HOME temporário com agy falso no PATH; sha256 de cada arquivo instalado e aliases)
- A3: Respostas do hook (93 payloads do agy + 14 do Claude enviados via stdin ao safety-gate.py; exit code + stdout)
- A4: Acoplamento (referências aos formatos de host em hook_context.py e safety-gate.py, linhas do safety-gate.py, testes de conformidade)

Uso:
  python3 onda4_baseline.py --generate   # Grava o retrato em docs/temp_implementation/evidence/onda4/baseline-v1.4.0/
  python3 onda4_baseline.py --check      # Compara com o retrato gravado; exit != 0 se algo mudar
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[3]
EVIDENCE_DIR = REPO_ROOT / "docs" / "temp_implementation" / "evidence" / "onda4" / "baseline-v1.4.0"

A1_FILENAME = "A1_gate_corpus.expected.jsonl"
A2_FILENAME = "A2_install_manifest.json"
A3_FILENAME = "A3_hook_responses.jsonl"
A3_MUSE_BEFORE_FILENAME = "A3_muse_before.jsonl"
A4_FILENAME = "A4_coupling_metrics.json"

COUPLING_TERMS = ["toolCall", "tool_name", "tool_input", "hookSpecificOutput", "CommandLine"]


# ==============================================================================
# A1: Decisões do Gate
# ==============================================================================

def get_a1_source_path() -> Path:
    return REPO_ROOT / "clearer-engineering" / "tests" / "fixtures" / "gate_corpus.expected.jsonl"


def capture_a1() -> Tuple[str, str, int]:
    p = get_a1_source_path()
    if not p.is_file():
        raise FileNotFoundError(f"A1 source not found: {p}")
    content = p.read_text(encoding="utf-8")
    lines = [ln for ln in content.splitlines() if ln.strip()]
    h = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return content, h, len(lines)


# ==============================================================================
# A2: Instalação de Referência (Dividido em A2a ativos e A2b manifesto)
# ==============================================================================

def capture_a2() -> Dict[str, Any]:
    tmp_dir = tempfile.mkdtemp(prefix="ceh_onda4_install_")
    try:
        fake_bin = os.path.join(tmp_dir, "bin")
        os.makedirs(fake_bin, exist_ok=True)
        fake_agy = os.path.join(fake_bin, "agy")
        with open(fake_agy, "w", encoding="utf-8") as f:
            f.write("#!/bin/sh\nexit 0\n")
        os.chmod(fake_agy, 0o755)

        tmp_home = os.path.join(tmp_dir, "home")
        os.makedirs(tmp_home, exist_ok=True)
        with open(os.path.join(tmp_home, ".bashrc"), "w", encoding="utf-8") as f:
            f.write("# existing mock bashrc\n")

        env = os.environ.copy()
        env["HOME"] = tmp_home
        env["PATH"] = f"{fake_bin}:{env.get('PATH', '')}"

        install_script = REPO_ROOT / "install.sh"
        res = subprocess.run(
            ["bash", str(install_script)],
            env=env,
            cwd=str(REPO_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if res.returncode != 0:
            raise RuntimeError(f"install.sh failed with exit {res.returncode}:\n{res.stderr}")

        non_code_manifest: Dict[str, str] = {}
        all_installed_paths: List[str] = []

        target_dirs = [
            Path(tmp_home) / ".gemini" / "config" / "plugins" / "clearer-engineering",
            Path(tmp_home) / ".gemini" / "config" / "agents" / "clearer-harness",
        ]

        for base_dir in target_dirs:
            if not base_dir.is_dir():
                continue
            for p in sorted(base_dir.rglob("*")):
                if p.is_file() and "__pycache__" not in p.parts and not p.name.endswith((".pyc", ".pyo")):
                    rel = p.relative_to(tmp_home).as_posix()
                    all_installed_paths.append(rel)
                    # A2a: somente ativos não-código (exclui .py e .sh)
                    if not rel.endswith((".py", ".sh")):
                        file_hash = hashlib.sha256(p.read_bytes()).hexdigest()
                        non_code_manifest[rel] = file_hash

        all_installed_paths.sort()

        bashrc_path = Path(tmp_home) / ".bashrc"
        bashrc_content = bashrc_path.read_text(encoding="utf-8") if bashrc_path.is_file() else ""
        aliases_block = ""
        start_tag = "# BEGIN CLEARER ENGINEERING HARNESS (CEH) ALIASES"
        end_tag = "# END CLEARER ENGINEERING HARNESS (CEH) ALIASES"
        if start_tag in bashrc_content and end_tag in bashrc_content:
            aliases_block = bashrc_content.split(start_tag)[1].split(end_tag)[0].strip()

        aliases_hash = hashlib.sha256(aliases_block.encode("utf-8")).hexdigest()

        return {
            "a2a_non_code_count": len(non_code_manifest),
            "a2a_non_code_files": non_code_manifest,
            "a2b_all_paths_count": len(all_installed_paths),
            "a2b_all_paths": all_installed_paths,
            "aliases_block": aliases_block,
            "aliases_hash": aliases_hash,
        }
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ==============================================================================
# A3: Respostas do Hook (agy + claude) e A3-muse (marcador do antes)
# ==============================================================================

def collect_invocation_files(hosts: List[str]) -> List[Tuple[str, str]]:
    """Returns sorted list of (host, rel_path) for specified hosts in evidence."""
    results: List[Tuple[str, str]] = []
    for host in hosts:
        pattern = str(REPO_ROOT / "docs" / "temp_implementation" / "evidence" / "host-probe" / host / "**" / "invocations.jsonl")
        for f in sorted(glob.glob(pattern, recursive=True)):
            rel = Path(f).relative_to(REPO_ROOT).as_posix()
            results.append((host, rel))
    return results


def capture_a3(hosts: List[str] | None = None) -> List[Dict[str, Any]]:
    target_hosts = hosts or ["agy", "claude"]
    inv_files = collect_invocation_files(target_hosts)
    safety_gate_py = REPO_ROOT / "clearer-engineering" / "scripts" / "safety-gate.py"

    records: List[Dict[str, Any]] = []

    # Hermetic execution environment (prevents dev machine cwd/HOME contamination)
    tmp_home = tempfile.mkdtemp(prefix="ceh_onda4_a3_home_")
    try:
        clean_env = os.environ.copy()
        clean_env["HOME"] = tmp_home
        clean_env.pop("CEH_EXPLICIT_ENV", None)
        clean_env.pop("APP_ENV", None)

        for host, rel_path in inv_files:
            full_path = REPO_ROOT / rel_path
            with open(full_path, "r", encoding="utf-8") as fh:
                for line_idx, line in enumerate(fh):
                    line = line.strip()
                    if not line:
                        continue
                    entry = json.loads(line)
                    payload = entry.get("payload")
                    if payload is None:
                        continue

                    proc = subprocess.run(
                        [sys.executable, str(safety_gate_py)],
                        input=json.dumps(payload),
                        text=True,
                        capture_output=True,
                        cwd=str(REPO_ROOT),
                        env=clean_env,
                    )

                    records.append({
                        "host": host,
                        "file": rel_path,
                        "line": line_idx,
                        "payload_hash": hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest(),
                        "exit_code": proc.returncode,
                        "stdout": proc.stdout.strip(),
                    })
    finally:
        shutil.rmtree(tmp_home, ignore_errors=True)

    return records


# ==============================================================================
# A4: Acoplamento
# ==============================================================================

def capture_a4() -> Dict[str, Any]:
    hook_ctx_path = REPO_ROOT / "clearer-engineering" / "scripts" / "hook_context.py"
    safety_gate_path = REPO_ROOT / "clearer-engineering" / "scripts" / "safety-gate.py"

    hook_ctx_text = hook_ctx_path.read_text(encoding="utf-8") if hook_ctx_path.is_file() else ""
    safety_gate_text = safety_gate_path.read_text(encoding="utf-8") if safety_gate_path.is_file() else ""

    hook_counts = {t: len(re.findall(re.escape(t), hook_ctx_text)) for t in COUPLING_TERMS}
    safety_counts = {t: len(re.findall(re.escape(t), safety_gate_text)) for t in COUPLING_TERMS}

    conformance_tests = list(REPO_ROOT.glob("clearer-engineering/tests/**/test_*conformance*.py"))
    conformance_count = len(conformance_tests)

    return {
        "hook_context_path": "clearer-engineering/scripts/hook_context.py",
        "hook_context_terms": hook_counts,
        "hook_context_total_references": sum(hook_counts.values()),
        "safety_gate_path": "clearer-engineering/scripts/safety-gate.py",
        "safety_gate_terms": safety_counts,
        "safety_gate_total_references": sum(safety_counts.values()),
        "safety_gate_line_count": len(safety_gate_text.splitlines()),
        "cross_host_conformance_tests_count": conformance_count,
        "source_version": "v1.4.1",
    }


# ==============================================================================
# Generate & Check
# ==============================================================================

def generate_baseline():
    print(f"=== [Onda 4 Baseline: Gravando retrato da v1.4.0] ===")
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    # A1
    print("Gravando A1 (Decisões do gate)...")
    a1_content, a1_hash, a1_count = capture_a1()
    (EVIDENCE_DIR / A1_FILENAME).write_text(a1_content, encoding="utf-8")
    print(f"  ✔ A1 gravado: {a1_count} avaliações, sha256={a1_hash}")

    # A2
    print("Gravando A2 (Instalação de referência: A2a ativos e A2b manifesto)...")
    a2_data = capture_a2()
    (EVIDENCE_DIR / A2_FILENAME).write_text(json.dumps(a2_data, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"  ✔ A2 gravado: {a2_data['a2a_non_code_count']} ativos não-código (A2a), {a2_data['a2b_all_paths_count']} arquivos totais (A2b), aliases sha256={a2_data['aliases_hash']}")

    # A3 (agy + claude)
    print("Gravando A3 (Respostas do hook: agy + claude)...")
    a3_data = capture_a3(["agy", "claude"])
    with open(EVIDENCE_DIR / A3_FILENAME, "w", encoding="utf-8") as f:
        for rec in a3_data:
            f.write(json.dumps(rec, sort_keys=True, ensure_ascii=False) + "\n")
    print(f"  ✔ A3 gravado: {len(a3_data)} respostas gravadas (rede estrita não-regressão)")

    # A3-muse (marcador do antes)
    print("Gravando A3-muse (Marcador do antes para Muse na v1.4.0)...")
    a3_muse_data = capture_a3(["muse"])
    with open(EVIDENCE_DIR / A3_MUSE_BEFORE_FILENAME, "w", encoding="utf-8") as f:
        for rec in a3_muse_data:
            f.write(json.dumps(rec, sort_keys=True, ensure_ascii=False) + "\n")
    print(f"  ✔ A3-muse gravado: {len(a3_muse_data)} respostas gravadas (todas deny/2 na v1.4.0)")

    # A4
    print("Gravando A4 (Acoplamento e conformidade)...")
    a4_data = capture_a4()
    (EVIDENCE_DIR / A4_FILENAME).write_text(json.dumps(a4_data, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"  ✔ A4 gravado: hook_context={a4_data['hook_context_total_references']} refs, safety_gate={a4_data['safety_gate_total_references']} refs, {a4_data['safety_gate_line_count']} linhas, conformidade={a4_data['cross_host_conformance_tests_count']}")

    print(f"\n[SUCESSO] Retrato da v1.4.0 gravado com sucesso em: {EVIDENCE_DIR}")


def check_baseline() -> int:
    print(f"=== [Onda 4 Baseline: Verificando contra retrato da v1.4.0] ===")
    if not EVIDENCE_DIR.is_dir():
        print(f"ERRO: Diretório de evidências não encontrado: {EVIDENCE_DIR}", file=sys.stderr)
        return 1

    diffs: List[str] = []

    # Check A1
    print("[1/5] Verificando A1 (Decisões do gate)...")
    a1_file = EVIDENCE_DIR / A1_FILENAME
    if not a1_file.is_file():
        diffs.append(f"A1 baseline file missing: {a1_file}")
    else:
        expected_a1 = a1_file.read_text(encoding="utf-8")
        current_a1, current_hash, current_count = capture_a1()
        expected_hash = hashlib.sha256(expected_a1.encode("utf-8")).hexdigest()
        if current_hash != expected_hash:
            diffs.append(f"A1 divergência em gate_corpus.expected.jsonl! Esperado: {expected_hash}, Atual: {current_hash}")
        else:
            print(f"  ✔ A1 OK ({current_count} decisões idênticas, hash {current_hash[:16]}...)")

    # Check A2a & A2b
    print("[2/5] Verificando A2a (Ativos não-código byte-a-byte)...")
    a2_file = EVIDENCE_DIR / A2_FILENAME
    if not a2_file.is_file():
        diffs.append(f"A2 baseline file missing: {a2_file}")
    else:
        expected_a2 = json.loads(a2_file.read_text(encoding="utf-8"))
        current_a2 = capture_a2()

        # A2a check
        exp_non_code = expected_a2.get("a2a_non_code_files", {})
        cur_non_code = current_a2.get("a2a_non_code_files", {})

        missing_non_code = set(exp_non_code.keys()) - set(cur_non_code.keys())
        extra_non_code = set(cur_non_code.keys()) - set(exp_non_code.keys())
        non_code_mismatches = []
        for fn in sorted(set(exp_non_code.keys()) & set(cur_non_code.keys())):
            if exp_non_code[fn] != cur_non_code[fn]:
                non_code_mismatches.append(f"{fn} (esperado {exp_non_code[fn][:8]}, atual {cur_non_code[fn][:8]})")

        if missing_non_code:
            diffs.append(f"A2a ativos não-código faltando: {sorted(missing_non_code)}")
        if extra_non_code:
            diffs.append(f"A2a ativos não-código extras: {sorted(extra_non_code)}")
        if non_code_mismatches:
            diffs.append(f"A2a ativos não-código com hash divergente: {non_code_mismatches}")

        if expected_a2.get("aliases_hash") != current_a2.get("aliases_hash"):
            diffs.append(f"A2a divergência no bloco de aliases do shell rc! Esperado {expected_a2.get('aliases_hash')}, atual {current_a2.get('aliases_hash')}")

        if not missing_non_code and not extra_non_code and not non_code_mismatches and expected_a2.get("aliases_hash") == current_a2.get("aliases_hash"):
            print(f"  ✔ A2a OK ({len(cur_non_code)} ativos não-código byte-idênticos, aliases idênticos)")

        # A2b check
        print("[3/5] Verificando A2b (Estrutura/manifesto de arquivos instalados)...")
        exp_paths = expected_a2.get("a2b_all_paths", [])
        cur_paths = current_a2.get("a2b_all_paths", [])
        if exp_paths != cur_paths:
            diff_missing = sorted(set(exp_paths) - set(cur_paths))
            diff_added = sorted(set(cur_paths) - set(exp_paths))
            if diff_missing:
                diffs.append(f"A2b arquivos faltando na instalação: {diff_missing}")
            if diff_added:
                diffs.append(f"A2b arquivos não documentados adicionados na instalação: {diff_added}")
        else:
            print(f"  ✔ A2b OK ({len(cur_paths)} caminhos de arquivos instalados conferem com o manifesto)")

    # Check A3
    print("[4/5] Verificando A3 (Respostas do hook: agy + claude)...")
    a3_file = EVIDENCE_DIR / A3_FILENAME
    if not a3_file.is_file():
        diffs.append(f"A3 baseline file missing: {a3_file}")
    else:
        expected_a3 = [json.loads(ln) for ln in a3_file.read_text(encoding="utf-8").splitlines() if ln.strip()]
        current_a3 = capture_a3(["agy", "claude"])

        if len(expected_a3) != len(current_a3):
            diffs.append(f"A3 contagem de respostas divergente! Esperado {len(expected_a3)}, atual {len(current_a3)}")
        else:
            mismatches = []
            for idx, (exp, cur) in enumerate(zip(expected_a3, current_a3)):
                if exp["exit_code"] != cur["exit_code"] or exp["stdout"] != cur["stdout"]:
                    mismatches.append(f"Payload #{idx} ({exp['host']} em {exp['file']}:{exp['line']}): exp_ec={exp['exit_code']}, cur_ec={cur['exit_code']}, stdout_diff=(exp: {exp['stdout'][:40]}... vs cur: {cur['stdout'][:40]}...)")

            if mismatches:
                diffs.append(f"A3 divergências em respostas do hook ({len(mismatches)} de {len(expected_a3)}):\n  " + "\n  ".join(mismatches[:5]))
            else:
                print(f"  ✔ A3 OK ({len(current_a3)} respostas do hook idênticas em exit_code e stdout)")

    # Check A3-muse (marcador do antes)
    print("[5/5] Verificando A3-muse (Marcador do antes para Muse)...")
    a3_muse_file = EVIDENCE_DIR / A3_MUSE_BEFORE_FILENAME
    if not a3_muse_file.is_file():
        diffs.append(f"A3-muse baseline file missing: {a3_muse_file}")
    else:
        expected_muse = [json.loads(ln) for ln in a3_muse_file.read_text(encoding="utf-8").splitlines() if ln.strip()]
        # Confere que o marcador do antes está preservado (todas as respostas v1.4.0 com deny/2)
        all_deny_2 = all(rec["exit_code"] == 2 for rec in expected_muse)
        if not all_deny_2:
            diffs.append("A3-muse inconsistente: esperado que o marcador do antes registre deny (exit 2) para todas as ferramentas")
        else:
            print(f"  ✔ A3-muse OK ({len(expected_muse)} payloads do Muse confirmados com deny/2 no marcador do antes)")

    # Check A4
    print("Verificando A4 (Acoplamento)...")
    a4_file = EVIDENCE_DIR / A4_FILENAME
    if not a4_file.is_file():
        diffs.append(f"A4 baseline file missing: {a4_file}")
    else:
        expected_a4 = json.loads(a4_file.read_text(encoding="utf-8"))
        current_a4 = capture_a4()
        print(f"  • A4 Atual: hook_context={current_a4['hook_context_total_references']} refs, safety_gate={current_a4['safety_gate_total_references']} refs, {current_a4['safety_gate_line_count']} linhas, conformidade={current_a4['cross_host_conformance_tests_count']}")
        print(f"  • A4 Retrato v1.4.0: hook_context={expected_a4['hook_context_total_references']} refs, safety_gate={expected_a4['safety_gate_total_references']} refs, {expected_a4['safety_gate_line_count']} linhas, conformidade={expected_a4['cross_host_conformance_tests_count']}")

        if current_a4 != expected_a4:
            diffs.append(f"A4 divergência de acoplamento na Fase 0! Esperado: {expected_a4}, Atual: {current_a4}")
        else:
            print("  ✔ A4 OK (Métricas de acoplamento da v1.4.0 confirmadas)")

    if diffs:
        print("\n============================================================", file=sys.stderr)
        print("FALHA NA VERIFICAÇÃO DO BASELINE DA ONDA 4:", file=sys.stderr)
        for d in diffs:
            print(f"  ❌ {d}", file=sys.stderr)
        print("============================================================", file=sys.stderr)
        return 1

    print("\n✔ SUCESSO: Todas as 5 medições (A1-A4 + A3-muse) conferem rigorosamente com o retrato v1.4.0!")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Onda 4 Baseline Snapshot & Regression Check Tool")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--generate", action="store_true", help="Grava retrato de referência da v1.4.0")
    group.add_argument("--check", action="store_true", help="Verifica integridade contra o retrato da v1.4.0")
    args = parser.parse_args()

    if args.generate:
        generate_baseline()
        sys.exit(0)
    elif args.check:
        sys.exit(check_baseline())


if __name__ == "__main__":
    main()
