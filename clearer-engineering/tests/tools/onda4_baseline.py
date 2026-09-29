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
# A2: Instalação de Referência
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

        files_manifest: Dict[str, str] = {}
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
                    file_hash = hashlib.sha256(p.read_bytes()).hexdigest()
                    files_manifest[rel] = file_hash

        bashrc_path = Path(tmp_home) / ".bashrc"
        bashrc_content = bashrc_path.read_text(encoding="utf-8") if bashrc_path.is_file() else ""
        aliases_block = ""
        start_tag = "# BEGIN CLEARER ENGINEERING HARNESS (CEH) ALIASES"
        end_tag = "# END CLEARER ENGINEERING HARNESS (CEH) ALIASES"
        if start_tag in bashrc_content and end_tag in bashrc_content:
            aliases_block = bashrc_content.split(start_tag)[1].split(end_tag)[0].strip()

        aliases_hash = hashlib.sha256(aliases_block.encode("utf-8")).hexdigest()

        return {
            "files_count": len(files_manifest),
            "files": files_manifest,
            "aliases_block": aliases_block,
            "aliases_hash": aliases_hash,
        }
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ==============================================================================
# A3: Respostas do Hook
# ==============================================================================

def collect_invocation_files() -> List[Tuple[str, str]]:
    """Returns sorted list of (host, rel_path) for all invocations.jsonl in evidence."""
    results: List[Tuple[str, str]] = []
    for host in ["agy", "claude"]:
        pattern = str(REPO_ROOT / "docs" / "temp_implementation" / "evidence" / "host-probe" / host / "**" / "invocations.jsonl")
        for f in sorted(glob.glob(pattern, recursive=True)):
            rel = Path(f).relative_to(REPO_ROOT).as_posix()
            results.append((host, rel))
    return results


def capture_a3() -> List[Dict[str, Any]]:
    inv_files = collect_invocation_files()
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

    # Count cross-host conformance tests (PR-17 introduces tests/test_host_conformance*.py or similar)
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
    print("Gravando A2 (Instalação de referência)...")
    a2_data = capture_a2()
    (EVIDENCE_DIR / A2_FILENAME).write_text(json.dumps(a2_data, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"  ✔ A2 gravado: {a2_data['files_count']} arquivos instalados, aliases sha256={a2_data['aliases_hash']}")

    # A3
    print("Gravando A3 (Respostas do hook: agy + claude)...")
    a3_data = capture_a3()
    with open(EVIDENCE_DIR / A3_FILENAME, "w", encoding="utf-8") as f:
        for rec in a3_data:
            f.write(json.dumps(rec, sort_keys=True, ensure_ascii=False) + "\n")
    print(f"  ✔ A3 gravado: {len(a3_data)} respostas gravadas")

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
    print("[1/4] Verificando A1 (Decisões do gate)...")
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

    # Check A2
    print("[2/4] Verificando A2 (Instalação de referência)...")
    a2_file = EVIDENCE_DIR / A2_FILENAME
    if not a2_file.is_file():
        diffs.append(f"A2 baseline file missing: {a2_file}")
    else:
        expected_a2 = json.loads(a2_file.read_text(encoding="utf-8"))
        current_a2 = capture_a2()

        # Compare files
        exp_files = expected_a2.get("files", {})
        cur_files = current_a2.get("files", {})

        missing_files = set(exp_files.keys()) - set(cur_files.keys())
        extra_files = set(cur_files.keys()) - set(exp_files.keys())
        hash_mismatches = []
        for fn in sorted(set(exp_files.keys()) & set(cur_files.keys())):
            if exp_files[fn] != cur_files[fn]:
                hash_mismatches.append(f"{fn} (esperado {exp_files[fn][:8]}, atual {cur_files[fn][:8]})")

        if missing_files:
            diffs.append(f"A2 arquivos faltando na instalação: {sorted(missing_files)}")
        if extra_files:
            diffs.append(f"A2 arquivos extras na instalação: {sorted(extra_files)}")
        if hash_mismatches:
            diffs.append(f"A2 arquivos com hash divergente: {hash_mismatches}")

        if expected_a2.get("aliases_hash") != current_a2.get("aliases_hash"):
            diffs.append(f"A2 divergência no bloco de aliases do shell rc! Esperado {expected_a2.get('aliases_hash')}, atual {current_a2.get('aliases_hash')}")

        if not missing_files and not extra_files and not hash_mismatches and expected_a2.get("aliases_hash") == current_a2.get("aliases_hash"):
            print(f"  ✔ A2 OK ({current_a2['files_count']} arquivos byte-idênticos, aliases idênticos)")

    # Check A3
    print("[3/4] Verificando A3 (Respostas do hook: agy + claude)...")
    a3_file = EVIDENCE_DIR / A3_FILENAME
    if not a3_file.is_file():
        diffs.append(f"A3 baseline file missing: {a3_file}")
    else:
        expected_a3 = [json.loads(ln) for ln in a3_file.read_text(encoding="utf-8").splitlines() if ln.strip()]
        current_a3 = capture_a3()

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

    # Check A4
    print("[4/4] Verificando A4 (Acoplamento)...")
    a4_file = EVIDENCE_DIR / A4_FILENAME
    if not a4_file.is_file():
        diffs.append(f"A4 baseline file missing: {a4_file}")
    else:
        expected_a4 = json.loads(a4_file.read_text(encoding="utf-8"))
        current_a4 = capture_a4()
        print(f"  • A4 Atual: hook_context={current_a4['hook_context_total_references']} refs, safety_gate={current_a4['safety_gate_total_references']} refs, {current_a4['safety_gate_line_count']} linhas, conformidade={current_a4['cross_host_conformance_tests_count']}")
        print(f"  • A4 Retrato v1.4.0: hook_context={expected_a4['hook_context_total_references']} refs, safety_gate={expected_a4['safety_gate_total_references']} refs, {expected_a4['safety_gate_line_count']} linhas, conformidade={expected_a4['cross_host_conformance_tests_count']}")

        # Na Fase 0, A4 deve ser idêntico à v1.4.0
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

    print("\n✔ SUCESSO: Todas as 4 medições (A1-A4) conferem rigorosamente com o retrato v1.4.0!")
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
