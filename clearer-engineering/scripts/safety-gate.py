#!/usr/bin/env python3
"""
safety-gate.py - PreToolUse Safety Guard for CLEARER Engineering Harness (CEH).
Repasse fino (shim): le entrada do terminal ou hook, invoca o hook_context e o motor
ceh_core.engine, e devolve a resposta com o codigo de saida padronizado.
ZERO referencias a formatos de host.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SCRIPTS_DIR = str(Path(__file__).resolve().parent)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from ceh_core.engine import Request, Decision, evaluate, evaluate_command
from hook_context import handle_hook_lifecycle, get_exit_code


def handle_hook():
    """Processes PreToolUse hook JSON from stdin."""
    raw_input = sys.stdin.read()
    response_dict, exit_code = handle_hook_lifecycle(raw_input, evaluate)
    print(json.dumps(response_dict, ensure_ascii=False))
    sys.exit(exit_code)


def main():
    parser = argparse.ArgumentParser(description="CEH Safety Gate Command Checker")
    parser.add_argument("--check", "--command", dest="check", type=str, help="Directly check a command string and output decision")
    parser.add_argument("--cwd", type=str, default=None, help="Base working directory for environment and path resolution")
    parser.add_argument("--env", type=str, default=None, help="Explicit environment override (development|staging|production)")
    args = parser.parse_args()

    if args.check is not None:
        base_cwd = Path(args.cwd).resolve() if args.cwd else None
        req = Request(command=args.check, cwd=base_cwd, explicit_env=args.env)
        dec = evaluate(req)
        result = {
            "decision": dec.decision,
            "reason": dec.reason,
            "environment": dec.environment,
            "use_case": dec.use_case,
            "command": args.check
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
        if dec.decision == "deny":
            sys.exit(2)
        elif dec.decision == "ask":
            sys.exit(1)
        else:
            sys.exit(0)
    else:
        handle_hook()


if __name__ == "__main__":
    main()
