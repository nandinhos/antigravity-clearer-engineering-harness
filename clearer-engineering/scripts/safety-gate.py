#!/usr/bin/env python3
"""safety-gate.py - PreToolUse Safety Guard shim for CEH. ZERO host references."""
from __future__ import annotations
import argparse, json, os, sys
from pathlib import Path

_SCRIPTS_DIR = str(Path(__file__).resolve().parent)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

_IMPORT_ERROR: Exception | None = None
try:
    from ceh_core.engine import Request, Decision, evaluate, evaluate_command
    from hook_context import handle_hook_lifecycle, get_exit_code
except Exception as _err:
    _IMPORT_ERROR = _err
    Request = Decision = evaluate = evaluate_command = handle_hook_lifecycle = get_exit_code = None

_FALLBACK = None
try:
    from adapters import fallback as _FALLBACK
except Exception:
    _FALLBACK = None


def _fallback_exit_code() -> int:
    return 2 if any(k in os.environ for k in ("CLAUDECODE", "CLAUDE_PROJECT_DIR", "CLAUDE_PID")) else 0


def _emergency_deny(raw_input: str, reason: str):
    if _FALLBACK is not None:
        try:
            _FALLBACK.respond(raw_input, reason)
        except Exception:
            pass
    print(json.dumps({"decision": "deny", "reason": reason}, ensure_ascii=False))
    sys.exit(_fallback_exit_code())


def handle_hook():
    """Processes PreToolUse hook JSON from stdin with fail-closed guarantee."""
    try:
        raw_input = sys.stdin.read()
    except Exception:
        raw_input = ""

    if _IMPORT_ERROR is not None:
        _emergency_deny(raw_input, f"[CEH SAFETY GATE ERROR] Falha crítica de importação dos módulos de segurança ({_IMPORT_ERROR}). Execução bloqueada (fail-closed).")

    try:
        response_dict, exit_code = handle_hook_lifecycle(raw_input, evaluate)
        print(json.dumps(response_dict, ensure_ascii=False))
        sys.exit(exit_code)
    except Exception as e:
        _emergency_deny(raw_input, f"[CEH SAFETY GATE ERROR] Exceção não tratada na execução do hook ({e}). Execução bloqueada (fail-closed).")


def main():
    parser = argparse.ArgumentParser(description="CEH Safety Gate Command Checker")
    parser.add_argument("--check", "--command", dest="check", type=str, help="Directly check a command string and output decision")
    parser.add_argument("--cwd", type=str, default=None, help="Base working directory for environment and path resolution")
    parser.add_argument("--env", type=str, default=None, help="Explicit environment override (development|staging|production)")
    args = parser.parse_args()

    if args.check is not None:
        if _IMPORT_ERROR is not None:
            result = {
                "decision": "deny",
                "reason": f"[CEH SAFETY GATE ERROR] Falha de importação ({_IMPORT_ERROR})",
                "environment": "development",
                "use_case": "SYSTEM_FAIL_CLOSED",
                "command": args.check
            }
            print(json.dumps(result, indent=2, ensure_ascii=False))
            sys.exit(2)

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
        sys.exit(2 if dec.decision == "deny" else (1 if dec.decision == "ask" else 0))
    else:
        handle_hook()


if __name__ == "__main__":
    main()
