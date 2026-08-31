#!/usr/bin/env python3
"""
safety-gate.py - PreToolUse Safety Guard for CLEARER Engineering Harness (CEH).
Enforces the safety policy: DENY > ASK > ALLOW
Analyzes commands for destructive patterns, data loss, Git destruction, and production hazards.
"""

import sys
import json
import re
import argparse

# High-risk patterns that MUST be BLOCKED (DENY)
HARD_BLOCK_PATTERNS = [
    (r"\brm\s+-[rRfF]*[rR][rRfF]*\s+/(?:\s|$)", "Hard block: Attempting recursive deletion of root directory '/'."),
    (r"\brm\s+-[rRfF]*[rR][rRfF]*\s+~(?:\s|/|$)", "Hard block: Attempting recursive deletion of home directory '~'."),
    (r"\brm\s+-[rRfF]*[rR][rRfF]*\s+\.\.(?:\s|/|$)", "Hard block: Attempting recursive deletion of parent directory '..'."),
    (r"\brm\s+-[rRfF]*[rR][rRfF]*\s+\*(?:\s|$)", "Hard block: Blind wildcard recursive deletion 'rm -rf *'."),
    (r"\bmkfs\b", "Hard block: Filesystem formatting command detected."),
    (r"\bdd\s+if=.*of=/dev/", "Hard block: Direct disk writing via dd detected."),
    (r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:", "Hard block: Fork bomb detected."),
    (r"\bDROP\s+DATABASE\b", "Hard block: DROP DATABASE statement detected."),
    (r"\bDROP\s+SCHEMA\b", "Hard block: DROP SCHEMA statement detected."),
    (r"\bgcloud\s+projects\s+delete\b", "Hard block: Deleting GCP project detected."),
]

# Safe development patterns explicitly allowed (ALLOW bypass over generic ASK)
SAFE_DEV_PATTERNS = [
    # Safe temporary/scratch cleanup
    r"\brm\s+-[rRfF]+\s+(?:/tmp/|tmp/|\.tmp/|scratch/|\.cache/|dist/|build/|storage/framework/cache/|coverage/)",
    # Safe single file removal
    r"\brm\s+-[rRfF]*[fF][rRfF]*\s+[a-zA-Z0-9_\-\.\/]+\.[a-zA-Z0-9]+(?:\s|$)",
    # Safe git checkout/restore of specific files (not '.' or whole tree)
    r"\bgit\s+checkout\s+(?![\.\-]\s*$)[a-zA-Z0-9_\-\.\/]+(?:\s|$)",
    r"\bgit\s+restore\s+(?![\.\-]\s*$)[a-zA-Z0-9_\-\.\/]+(?:\s|$)",
]

# Destructive patterns that REQUIRE USER CONFIRMATION (ASK)
ASK_PATTERNS = [
    (r"\brm\s+-[rRfF]+", "Recursive or forced file deletion (rm -rf)."),
    (r"\bgit\s+reset\s+--hard\b", "Destructive Git reset discarding uncommitted changes (git reset --hard)."),
    (r"\bgit\s+clean\s+-[a-zA-Z]*f", "Git clean discarding untracked files (git clean -f)."),
    (r"\bgit\s+restore\s+(?:\.|\s+--staged\s+\.)\b", "Git restore discarding all working tree changes."),
    (r"\bgit\s+checkout\s+--\s+\.\b", "Git checkout discarding all modified files."),
    (r"\bgit\s+checkout\s+\.\b", "Git checkout discarding all working tree files."),
    (r"\bgit\s+branch\s+-[dD]\b", "Deleting a Git branch."),
    (r"\bgit\s+push\s+.*--force\b", "Force pushing to remote repository (git push --force)."),
    (r"\bgit\s+push\s+.*-f\b", "Force pushing to remote repository (git push -f)."),
    (r"\bgit\s+push\s+.*\+[a-zA-Z0-9_\-\/]+", "Force pushing with refspec '+'."),
    (r"\bDROP\s+TABLE\b", "Destructive SQL: DROP TABLE."),
    (r"\bDROP\s+VIEW\b", "Destructive SQL: DROP VIEW."),
    (r"\bTRUNCATE(?:\s+TABLE)?\b", "Destructive SQL: TRUNCATE TABLE."),
    (r"\bDELETE\s+FROM\s+\w+\s*(?:;\s*$|$)", "Destructive SQL: Unconditional DELETE without WHERE clause."),
    (r"\bDELETE\s+FROM\s+\w+\s+WHERE\s+1\s*=\s*1", "Destructive SQL: DELETE with always-true WHERE 1=1."),
    (r"\b(?:artisan|php\s+artisan)\s+migrate:(?:fresh|reset)\b", "Destructive Laravel migration (migrate:fresh / migrate:reset)."),
    (r"\b(?:artisan|php\s+artisan)\s+db:wipe\b", "Destructive database wipe (artisan db:wipe)."),
    (r"\b(?:npm|pnpm|yarn)\s+publish\b", "Publishing packages to registry."),
    (r"\bterraform\s+destroy\b", "Destroying cloud infrastructure via Terraform."),
    (r"\bkubectl\s+delete\s+(?:namespace|ns|deployment|statefulset|svc|all)\b", "Deleting Kubernetes infrastructure resources."),
    (r"\bdocker\s+system\s+prune\s+-a\b", "Pruning all unused Docker images and containers."),
    (r"\bgsutil\s+rm\s+-r\b", "Recursive deletion in Google Cloud Storage."),
]

def evaluate_command(cmd_line: str) -> tuple[str, str]:
    """
    Evaluates a command line string against safety rules.
    Returns (decision, reason) where decision is 'deny', 'ask', or 'allow'.
    """
    if not cmd_line or not cmd_line.strip():
        return "allow", "Empty command"

    cmd_normalized = cmd_line.strip()

    # 1. Check Hard Blocks (DENY has absolute priority)
    for pattern, reason in HARD_BLOCK_PATTERNS:
        if re.search(pattern, cmd_normalized, re.IGNORECASE):
            return "deny", f"[CEH SAFETY BLOCK] {reason}"

    # 2. Check Safe Development Bypasses (ALLOW safe scratch/cache and single-file operations)
    for pattern in SAFE_DEV_PATTERNS:
        if re.search(pattern, cmd_normalized, re.IGNORECASE):
            return "allow", "Command matches safe development operation pattern."

    # 3. Check Confirmation Required (ASK)
    for pattern, reason in ASK_PATTERNS:
        if re.search(pattern, cmd_normalized, re.IGNORECASE):
            return "ask", f"[CEH SAFETY WARNING] {reason} Please confirm execution."

    return "allow", "Command complies with CEH safety policy."


def handle_hook():
    """Processes Antigravity PreToolUse hook JSON from stdin."""
    try:
        raw_input = sys.stdin.read()
        if not raw_input.strip():
            # If stdin is empty, fallback to allow
            print(json.dumps({"decision": "allow"}))
            return

        payload = json.loads(raw_input)
        tool_call = payload.get("toolCall", {})
        tool_name = tool_call.get("name", "")
        args = tool_call.get("args", {})

        if tool_name == "run_command":
            cmd_line = args.get("CommandLine", "")
            decision, reason = evaluate_command(cmd_line)
            output = {
                "decision": decision,
                "reason": reason
            }
            print(json.dumps(output))
            return

        # Default for non-command tools
        print(json.dumps({"decision": "allow"}))

    except Exception as e:
        # Fail-closed on parser errors if suspicious, or report error
        print(json.dumps({
            "decision": "ask",
            "reason": f"[CEH SAFETY GATE ERROR] Failed to parse hook payload: {str(e)}"
        }))

def main():
    parser = argparse.ArgumentParser(description="CEH Safety Gate Command Checker")
    parser.add_argument("--check", type=str, help="Directly check a command string and output decision")
    args = parser.parse_args()

    if args.check is not None:
        decision, reason = evaluate_command(args.check)
        result = {"decision": decision, "reason": reason, "command": args.check}
        print(json.dumps(result, indent=2))
        if decision == "deny":
            sys.exit(2)
        elif decision == "ask":
            sys.exit(1)
        else:
            sys.exit(0)
    else:
        handle_hook()

if __name__ == "__main__":
    main()
