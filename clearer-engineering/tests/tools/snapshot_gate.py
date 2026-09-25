#!/usr/bin/env python3
"""
snapshot_gate.py - Golden Corpus Snapshot Tool for CEH Safety Gate
Manages recording and deterministic regression testing of safety-gate decisions.

Usage:
  python3 snapshot_gate.py --generate   # Record decisions to gate_corpus.expected.jsonl
  python3 snapshot_gate.py --check      # Verify current decisions match snapshot (exit 0 on match)
"""

import sys
import os
import json
import base64
import argparse
import difflib
from pathlib import Path
from importlib import import_module

SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"
sys.path.insert(0, str(SCRIPTS_DIR))

safety_gate = import_module("safety-gate")
evaluate_command = safety_gate.evaluate_command

hook_context = import_module("hook_context")
evaluate_hook_payload = hook_context.evaluate_hook_payload


def load_corpus(corpus_path: Path):
    items = []
    lines = corpus_path.read_text(encoding="utf-8").splitlines()
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("HOOK:"):
            parts = line.split(":", 2)
            host = parts[1]
            payload_str = base64.b64decode(parts[2]).decode("utf-8")
            items.append({
                "kind": "hook",
                "host": host,
                "payload": json.loads(payload_str),
                "raw_desc": f"hook:{host}"
            })
        elif line.startswith("B64:"):
            cmd = base64.b64decode(line[4:]).decode("utf-8")
            items.append({
                "kind": "command",
                "command": cmd,
                "raw_desc": cmd
            })
        elif line.startswith("RAW:"):
            cmd = line[4:]
            items.append({
                "kind": "command",
                "command": cmd,
                "raw_desc": cmd
            })
        else:
            items.append({
                "kind": "command",
                "command": line,
                "raw_desc": line
            })
    return items


def run_evaluations(corpus_items):
    records = []
    environments = ["development", "staging", "production"]

    for idx, item in enumerate(corpus_items):
        if item["kind"] == "command":
            cmd = item["command"]
            for env in environments:
                decision, reason, _, use_case = evaluate_command(cmd, explicit_env=env)
                has_alerts = ("ALERTA 1/2" in reason and "ALERTA 2/2" in reason)
                records.append({
                    "id": f"CMD-{idx:03d}-{env[:3]}",
                    "type": "command",
                    "command": cmd,
                    "env": env,
                    "decision": decision,
                    "use_case": use_case,
                    "has_alerts": has_alerts
                })
        elif item["kind"] == "hook":
            payload = item["payload"]
            host = item["host"]
            res = evaluate_hook_payload(payload, evaluate_command)
            records.append({
                "id": f"HOOK-{idx:03d}-{host}",
                "type": "hook",
                "host": host,
                "response": res
            })

    return records


def generate_snapshot(corpus_path: Path, output_path: Path):
    items = load_corpus(corpus_path)
    records = run_evaluations(items)
    with open(output_path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    print(f"✔ Golden Corpus Snapshot gerado: {len(records)} avaliações gravadas em {output_path.name}")


def check_snapshot(corpus_path: Path, expected_path: Path) -> bool:
    if not expected_path.exists():
        print(f"ERRO: Snapshot esperado não encontrado: {expected_path}")
        return False

    items = load_corpus(corpus_path)
    current_records = run_evaluations(items)

    current_lines = [json.dumps(r, ensure_ascii=False, sort_keys=True) for r in current_records]
    expected_lines = [line.strip() for line in expected_path.read_text(encoding="utf-8").splitlines() if line.strip()]

    if current_lines == expected_lines:
        print(f"✔ Golden Corpus Snapshot 100% CONFORME ({len(current_lines)} avaliações idênticas, diff vazio)")
        return True

    print("❌ DIVERGÊNCIA DETECTADA NO GOLDEN CORPUS SNAPSHOT:")
    diff = list(difflib.unified_diff(
        expected_lines,
        current_lines,
        fromfile="expected.jsonl",
        tofile="current_evaluation",
        lineterm=""
    ))
    for d in diff[:50]:
        print(d)
    if len(diff) > 50:
        print(f"... e mais {len(diff) - 50} linhas de divergência")
    return False


def main():
    parser = argparse.ArgumentParser(description="CEH Safety Gate Snapshot Tool")
    parser.add_argument("--generate", action="store_true", help="Gera o snapshot atual como novo gabarito")
    parser.add_argument("--check", action="store_true", help="Verifica se o gate atual diverge do gabarito")
    args = parser.parse_args()

    corpus_file = FIXTURES_DIR / "gate_corpus.txt"
    expected_file = FIXTURES_DIR / "gate_corpus.expected.jsonl"

    if not corpus_file.exists():
        print(f"ERRO: Arquivo do corpus não encontrado: {corpus_file}")
        sys.exit(1)

    if args.generate:
        generate_snapshot(corpus_file, expected_file)
        sys.exit(0)
    elif args.check:
        ok = check_snapshot(corpus_file, expected_file)
        sys.exit(0 if ok else 1)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
