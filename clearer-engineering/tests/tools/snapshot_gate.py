#!/usr/bin/env python3
"""
snapshot_gate.py - Golden Corpus Snapshot Tool for CEH Safety Gate
Manages recording and deterministic regression testing of safety-gate decisions.
Evaluates all commands and hooks inside hermetic temporary fixtures (O1 / Handoff 011).

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
import tempfile
import shutil
import subprocess
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
        if line.startswith("INTEGRATION:"):
            parts = line.split(":", 2)
            name = parts[1]
            cmd = base64.b64decode(parts[2]).decode("utf-8")
            items.append({
                "kind": "integration",
                "name": name,
                "command": cmd,
                "raw_desc": f"integration:{name}"
            })
        elif line.startswith("HOOK:"):
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

    # 1. Cria repositório-fixture temporário isolado (O1)
    # Permite avaliar git push e comandos git sem depender do .ceh/ do repo real
    tmp_repo = tempfile.mkdtemp(prefix="ceh_corpus_sandbox_")
    original_cwd = os.getcwd()

    try:
        subprocess.run(["git", "init", "-b", "dev"], cwd=tmp_repo, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "CorpusTest"], cwd=tmp_repo, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "corpus@test.local"], cwd=tmp_repo, check=True, capture_output=True)
        ci_dir = Path(tmp_repo) / ".github" / "workflows"
        ci_dir.mkdir(parents=True, exist_ok=True)
        (ci_dir / "ci.yml").write_text("name: CI\n")
        (Path(tmp_repo) / "README.md").write_text("Corpus Sandbox\n")
        subprocess.run(["git", "add", "."], cwd=tmp_repo, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_repo, check=True, capture_output=True)
        head_commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=tmp_repo, check=True, capture_output=True, text=True).stdout.strip()

        os.chdir(tmp_repo)

        # Avaliação de comandos e hooks em ambiente hermético (sem certificado)
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
            elif item["kind"] == "integration":
                # Casos de integração do G7 (Handoff 011)
                name = item["name"]
                cmd = item["command"]
                
                # Prepara certificado para head_commit em dev
                ceh_dir = Path(tmp_repo) / ".ceh"
                ceh_dir.mkdir(parents=True, exist_ok=True)
                (ceh_dir / "last-ci-run.json").write_text(
                    f'{{"commit_hash": "{head_commit}", "status": "PASS", "exit_code": 0, "canonical_verified": true}}'
                )

                if name == "G7_CONTROL":
                    # Controle: git push origin dev:main com commit certificado
                    subprocess.run(["git", "checkout", "-q", "dev"], cwd=tmp_repo, check=True)
                    decision, reason, _, use_case = evaluate_command(cmd, explicit_env="development")
                    records.append({
                        "id": f"INT-{name}",
                        "type": "integration",
                        "name": name,
                        "command": cmd,
                        "decision": decision,
                        "use_case": use_case
                    })
                elif name == "G7_RED":
                    # RED: git push origin outro:main onde 'outro' tem commit a mais sem certificado
                    subprocess.run(["git", "checkout", "-q", "-b", "outro_branch_tmp"], cwd=tmp_repo, check=True)
                    (Path(tmp_repo) / "extra_file.txt").write_text("extra\n")
                    subprocess.run(["git", "add", "extra_file.txt"], cwd=tmp_repo, check=True)
                    subprocess.run(["git", "commit", "-m", "extra commit"], cwd=tmp_repo, check=True)
                    subprocess.run(["git", "checkout", "-q", "dev"], cwd=tmp_repo, check=True)
                    
                    decision, reason, _, use_case = evaluate_command(cmd, explicit_env="development")
                    records.append({
                        "id": f"INT-{name}",
                        "type": "integration",
                        "name": name,
                        "command": cmd,
                        "decision": decision,
                        "use_case": use_case
                    })

                # Limpa .ceh/ para manter o sandbox limpo
                shutil.rmtree(ceh_dir, ignore_errors=True)

    finally:
        os.chdir(original_cwd)
        shutil.rmtree(tmp_repo, ignore_errors=True)

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
