#!/usr/bin/env python3
import sys
import os
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
INVOCATIONS_FILE = HERE / "invocations.jsonl"
CONFIG_FILE = Path("/tmp/probe_e13_mode.json")

def redact(text):
    if not isinstance(text, str):
        return text
    home = os.path.expanduser("~")
    return text.replace(home, "~")

def redact_obj(obj):
    if isinstance(obj, str):
        return redact(obj)
    if isinstance(obj, list):
        return [redact_obj(x) for x in obj]
    if isinstance(obj, dict):
        return {k: redact_obj(v) for k, v in obj.items()}
    return obj

def main():
    raw_input = sys.stdin.read()
    payload = None
    try:
        payload = json.loads(raw_input) if raw_input.strip() else {}
    except Exception as e:
        payload = {"_raw": raw_input, "_parse_error": str(e)}

    mode = "ceh_current"
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as fp:
                cfg = json.load(fp)
                mode = cfg.get("mode", "ceh_current")
        except Exception:
            mode = "ceh_current"

    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "payload": redact_obj(payload),
    }

    with open(INVOCATIONS_FILE, "a", encoding="utf-8") as fp:
        fp.write(json.dumps(record, ensure_ascii=False) + "\n")

    if mode == "deny0":
        out = {"decision": "deny", "reason": "[E13 TEST] deny bloqueante com exit 0"}
        print(json.dumps(out, ensure_ascii=False))
        sys.stdout.flush()
        sys.exit(0)

    elif mode == "deny2":
        out = {"decision": "deny", "reason": "[E13 TEST] deny com exit 2"}
        print(json.dumps(out, ensure_ascii=False))
        sys.stdout.flush()
        sys.exit(2)

    elif mode == "exit2":
        sys.stderr.write("[E13 TEST] exit 2 sem JSON\n")
        sys.stderr.flush()
        sys.exit(2)

    elif mode == "crash":
        raise RuntimeError("[E13 TEST] crash simulado do hook com excecao")

    elif mode == "sleep":
        import time
        time.sleep(20)
        out = {"decision": "deny", "reason": "[E13 TEST] deny apos sleep"}
        print(json.dumps(out, ensure_ascii=False))
        sys.exit(0)

    elif mode == "allow":
        out = {"decision": "allow", "reason": "[E13 TEST] allow explicito"}
        print(json.dumps(out, ensure_ascii=False))
        sys.stdout.flush()
        sys.exit(0)

    elif mode == "ceh_v140":
        # Executa o safety-gate da v1.4.0 puro (sem a edição local)
        script_v140 = Path("/tmp/safety_gate_v140_official.py")
        p = subprocess.run([sys.executable, str(script_v140)], input=raw_input, text=True, capture_output=True)
        sys.stdout.write(p.stdout)
        sys.stderr.write(p.stderr)
        sys.stdout.flush()
        sys.stderr.flush()
        sys.exit(p.returncode)

    else:
        # ceh_current: executa o safety-gate instalado atualmente
        gate_path = Path.home() / ".gemini/config/plugins/clearer-engineering/scripts/safety-gate.py"
        p = subprocess.run([sys.executable, str(gate_path)], input=raw_input, text=True, capture_output=True)
        sys.stdout.write(p.stdout)
        sys.stderr.write(p.stderr)
        sys.stdout.flush()
        sys.stderr.flush()
        sys.exit(p.returncode)

if __name__ == "__main__":
    main()
