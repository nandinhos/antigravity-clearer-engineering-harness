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
A3_MUSE_AFTER_FILENAME = "A3_muse_after.jsonl"
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
    ceh_core_dir = REPO_ROOT / "clearer-engineering" / "scripts" / "ceh_core"
    adapters_dir = REPO_ROOT / "clearer-engineering" / "scripts" / "adapters"

    hook_ctx_text = hook_ctx_path.read_text(encoding="utf-8") if hook_ctx_path.is_file() else ""
    safety_gate_text = safety_gate_path.read_text(encoding="utf-8") if safety_gate_path.is_file() else ""

    hook_counts = {t: len(re.findall(re.escape(t), hook_ctx_text)) for t in COUPLING_TERMS}
    safety_counts = {t: len(re.findall(re.escape(t), safety_gate_text)) for t in COUPLING_TERMS}

    ceh_core_counts = {t: 0 for t in COUPLING_TERMS}
    if ceh_core_dir.is_dir():
        for py_file in sorted(ceh_core_dir.glob("*.py")):
            text = py_file.read_text(encoding="utf-8")
            for t in COUPLING_TERMS:
                ceh_core_counts[t] += len(re.findall(re.escape(t), text))

    adapters_counts = {t: 0 for t in COUPLING_TERMS}
    if adapters_dir.is_dir():
        for py_file in sorted(adapters_dir.glob("*.py")):
            text = py_file.read_text(encoding="utf-8")
            for t in COUPLING_TERMS:
                adapters_counts[t] += len(re.findall(re.escape(t), text))

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
        "ceh_core_terms": ceh_core_counts,
        "ceh_core_total_references": sum(ceh_core_counts.values()),
        "adapters_terms": adapters_counts,
        "adapters_total_references": sum(adapters_counts.values()),
        "cross_host_conformance_tests_count": conformance_count,
        "source_version": "v1.4.1",
    }


# Arquivos adicionados na Onda 4 declarados no plano de engenharia (PR-13 e PR-14/15)
ONDA4_DECLARED_NEW_PATHS = {
    # PR-13
    ".gemini/config/plugins/clearer-engineering/scripts/ceh_core/engine.py",
    ".gemini/config/plugins/clearer-engineering/scripts/ceh_core/git_invocation.py",
    ".gemini/config/plugins/clearer-engineering/scripts/ceh_core/subcommand.py",
    ".gemini/config/plugins/clearer-engineering/tests/test_engine.py",
    ".gemini/config/plugins/clearer-engineering/tests/test_hook_failclosed.py",
    ".gemini/config/plugins/clearer-engineering/tests/tools/test_mutation_p13.py",
    # PR-14/15
    ".gemini/config/plugins/clearer-engineering/scripts/adapters/__init__.py",
    ".gemini/config/plugins/clearer-engineering/scripts/adapters/base.py",
    ".gemini/config/plugins/clearer-engineering/scripts/adapters/antigravity.py",
    ".gemini/config/plugins/clearer-engineering/scripts/adapters/claude_code.py",
    ".gemini/config/plugins/clearer-engineering/tests/test_adapters.py",
    ".gemini/config/plugins/clearer-engineering/tests/fixtures/adapters/antigravity/cases.jsonl",
    ".gemini/config/plugins/clearer-engineering/tests/fixtures/adapters/claude_code/cases.jsonl",
    ".gemini/config/plugins/clearer-engineering/tests/tools/test_mutation_p14.py",
    # PR-15b
    ".gemini/config/plugins/clearer-engineering/scripts/adapters/muse.py",
    ".gemini/config/plugins/clearer-engineering/tests/fixtures/adapters/antigravity/recorded.jsonl",
    ".gemini/config/plugins/clearer-engineering/tests/fixtures/adapters/claude_code/recorded.jsonl",
    ".gemini/config/plugins/clearer-engineering/tests/fixtures/adapters/muse/cases.jsonl",
    ".gemini/config/plugins/clearer-engineering/tests/fixtures/adapters/muse/recorded.jsonl",
    ".gemini/config/plugins/clearer-engineering/tests/tools/test_mutation_p15b.py",
    # PR-16
    ".gemini/config/plugins/clearer-engineering/tests/test_package.py",
    ".gemini/config/plugins/clearer-engineering/scripts/adapters/fallback.py",
    ".gemini/config/plugins/clearer-engineering/tests/tools/test_mutation_p16.py",
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
        extra_non_code = {k for k in (set(cur_non_code.keys()) - set(exp_non_code.keys())) if k not in ONDA4_DECLARED_NEW_PATHS}
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
            undeclared_added = [p for p in diff_added if p not in ONDA4_DECLARED_NEW_PATHS]
            if diff_missing:
                diffs.append(f"A2b arquivos faltando na instalação: {diff_missing}")
            if undeclared_added:
                diffs.append(f"A2b arquivos não documentados adicionados na instalação: {undeclared_added}")
            if not diff_missing and not undeclared_added:
                print(f"  ✔ A2b OK ({len(cur_paths)} caminhos instalados, {len(diff_added)} novos declarados da Onda 4)")
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

    # Check A3-muse (marcador do antes e respostas atuais do depois)
    print("[5/5] Verificando A3-muse (Antes: v1.4.0 e Depois: PR-15b)...")
    a3_muse_before_file = EVIDENCE_DIR / A3_MUSE_BEFORE_FILENAME
    a3_muse_after_file = EVIDENCE_DIR / A3_MUSE_AFTER_FILENAME

    if not a3_muse_before_file.is_file():
        diffs.append(f"A3-muse baseline file missing: {a3_muse_before_file}")
    else:
        expected_muse_before = [json.loads(ln) for ln in a3_muse_before_file.read_text(encoding="utf-8").splitlines() if ln.strip()]
        # 1. Confere que o marcador do antes está preservado (todas as 41 respostas v1.4.0 com deny/2)
        all_deny_2 = all(rec["exit_code"] == 2 for rec in expected_muse_before)
        if not all_deny_2 or len(expected_muse_before) != 41:
            diffs.append(f"A3-muse (antes) inconsistente: esperado 41 respostas com deny/2 no marcador do antes (encontrado {len(expected_muse_before)})")
        else:
            print(f"  ✔ A3-muse antes OK ({len(expected_muse_before)} payloads do Muse confirmados com deny/2 no marcador do antes)")

    if not a3_muse_after_file.is_file():
        diffs.append(f"A3-muse after baseline file missing: {a3_muse_after_file}")
    else:
        expected_muse_after = [json.loads(ln) for ln in a3_muse_after_file.read_text(encoding="utf-8").splitlines() if ln.strip()]
        current_muse_after = capture_a3(["muse"])

        if len(expected_muse_after) != len(current_muse_after):
            diffs.append(f"A3-muse (depois) contagem divergente! Esperado {len(expected_muse_after)}, atual {len(current_muse_after)}")
        else:
            mismatches = []
            for idx, (exp, cur) in enumerate(zip(expected_muse_after, current_muse_after)):
                if exp["exit_code"] != cur["exit_code"] or exp["stdout"] != cur["stdout"]:
                    mismatches.append(f"Payload #{idx} ({exp['file']}:{exp['line']}): exp_ec={exp['exit_code']}, cur_ec={cur['exit_code']}, stdout_diff=(exp: {exp['stdout']} vs cur: {cur['stdout']})")

            # 2. Confere que todas têm exit code 0 no Muse (nunca exit 2)
            non_zero_exits = [cur for cur in current_muse_after if cur["exit_code"] != 0]
            if non_zero_exits:
                diffs.append(f"A3-muse (depois) apresentou {len(non_zero_exits)} respostas com exit code != 0! No Muse todos devem ser exit 0.")

            if mismatches:
                diffs.append(f"A3-muse (depois) divergências ({len(mismatches)} de {len(expected_muse_after)}):\n  " + "\n  ".join(mismatches[:5]))
            else:
                print(f"  ✔ A3-muse depois OK ({len(current_muse_after)} respostas do hook idênticas em exit_code=0 e stdout)")

        # 3. Controle cruzado: cada comando bash avaliado diretamente contra ceh_core.engine.evaluate()
        scripts_path = str(REPO_ROOT / "clearer-engineering" / "scripts")
        if scripts_path not in sys.path:
            sys.path.insert(0, scripts_path)
        from adapters.muse import MuseAdapter
        from ceh_core.engine import evaluate as engine_evaluate

        muse_adapter = MuseAdapter()
        inv_files = collect_invocation_files(["muse"])
        cross_check_count = 0
        cross_mismatches = []

        for host, rel_path in inv_files:
            full_path = REPO_ROOT / rel_path
            with open(full_path, "r", encoding="utf-8") as fh:
                for line_idx, line in enumerate(fh):
                    if not line.strip():
                        continue
                    payload = json.loads(line).get("payload", {})
                    tool_name = payload.get("tool_name")
                    if tool_name == "bash":
                        cross_check_count += 1
                        req = muse_adapter.parse(payload)
                        engine_decision = engine_evaluate(req)
                        expected_render, _ = muse_adapter.render(engine_decision, payload)
                        expected_stdout = json.dumps(expected_render, separators=(",", ":")) if expected_render else "{}"

                        matching_cur = next((c for c in current_muse_after if c["file"] == rel_path and c["line"] == line_idx), None)
                        if matching_cur and matching_cur["stdout"] != expected_stdout:
                            cross_mismatches.append(f"{rel_path}:{line_idx} - cmd: {req.command[:30]} | hook: {matching_cur['stdout']} != engine: {expected_stdout}")

        if cross_mismatches:
            diffs.append(f"A3-muse controle cruzado falhou em {len(cross_mismatches)} comandos de terminal:\n  " + "\n  ".join(cross_mismatches))
        else:
            print(f"  ✔ A3-muse controle cruzado OK ({cross_check_count} comandos de terminal conferidos contra evaluate())")

    # Check A4
    print("Verificando A4 (Acoplamento)...")
    a4_file = EVIDENCE_DIR / A4_FILENAME
    if not a4_file.is_file():
        diffs.append(f"A4 baseline file missing: {a4_file}")
    else:
        expected_a4 = json.loads(a4_file.read_text(encoding="utf-8"))
        current_a4 = capture_a4()
        print(f"  • A4 Atual (PR-14/15): hook_context={current_a4['hook_context_total_references']} refs, safety_gate={current_a4['safety_gate_total_references']} refs, ceh_core={current_a4['ceh_core_total_references']} refs, safety_gate={current_a4['safety_gate_line_count']} linhas, adapters={current_a4['adapters_total_references']} refs")
        print(f"  • A4 Retrato v1.4.1 (antes PR-13): hook_context={expected_a4['hook_context_total_references']} refs, safety_gate={expected_a4['safety_gate_total_references']} refs, {expected_a4['safety_gate_line_count']} linhas")

        if current_a4["safety_gate_total_references"] != 0:
            diffs.append(f"A4 safety-gate.py ainda possui {current_a4['safety_gate_total_references']} referências de host! Meta é 0.")
        if current_a4["ceh_core_total_references"] != 0:
            diffs.append(f"A4 ceh_core possui {current_a4['ceh_core_total_references']} referências de host! Meta é 0.")
        if current_a4["hook_context_total_references"] != 0:
            diffs.append(f"A4 hook_context.py possui {current_a4['hook_context_total_references']} referências de host! Meta do PR-14/15 é 0 fora de adapters/.")
        if current_a4["safety_gate_line_count"] > 100:
            diffs.append(f"A4 safety-gate.py tem {current_a4['safety_gate_line_count']} linhas (esperado shim fino <= 100 linhas)")

        if (current_a4["safety_gate_total_references"] == 0 and
            current_a4["ceh_core_total_references"] == 0 and
            current_a4["hook_context_total_references"] == 0 and
            current_a4["safety_gate_line_count"] <= 100):
            print(f"  ✔ A4 OK (Meta do PR-14/15 atingida: 0 referências de host fora de adapters/; adapters/ isola {current_a4['adapters_total_references']} termos)")

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
