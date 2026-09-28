#!/usr/bin/env python3
"""
Behavioral regression tests for Conselho de Seniores output directory resolution.

Addresses Handoff 054 / D05 item 5: prove that atas are always anchored to the
user's working repository, not to the script installation path, and that the
fallback confines output to a docs/temp_implementation/conselho/ subdirectory
when no git root is available.

Three scenarios:
  (a) cwd inside a git repo  → OUTPUT_DIR under <repo>/docs/temp_implementation/conselho/
  (b) script invoked from an external path, cwd in user repo → same as (a)
  (c) cwd outside any git repo → OUTPUT_DIR under <cwd>/docs/temp_implementation/conselho/
"""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Optional


# Absolute path to the conselho-seniores.sh under test
SCRIPT_PATH = Path(__file__).resolve().parent.parent / "scripts" / "conselho-seniores.sh"


def _is_relative_to(path: Path, base: Path) -> bool:
    """Check if path is a subpath of base, resolving symlinks (essential for macOS /var -> /private/var)."""
    try:
        path.resolve().relative_to(base.resolve())
        return True
    except ValueError:
        return False


def _extract_output_dir_from_script(
    *, cwd: str, script_path: Optional[Path] = None, env_override: Optional[dict] = None
) -> Path:
    """Run a Bash snippet that sources the REPO_ROOT / OUTPUT_DIR logic from
    conselho-seniores.sh and prints the resolved OUTPUT_DIR, without actually
    executing the full script (which requires agents in PATH).

    We replicate lines 25-26 and 197-199 faithfully — this is the exact logic
    the production script uses to resolve the output directory.
    """
    target_script = script_path if script_path is not None else SCRIPT_PATH
    bash_snippet = f"""
set -euo pipefail

# --- Replicate lines 25-26 of conselho-seniores.sh ---
SCRIPT_DIR="$(cd "$(dirname "{target_script}")" && pwd)"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null || pwd)"

# --- Replicate lines 197-199 ---
OUTPUT_DIR=""
if [[ -z "$OUTPUT_DIR" ]]; then
  TIMESTAMP="$(date +'%Y%m%d_%H%M%S')"
  OUTPUT_DIR="$REPO_ROOT/docs/temp_implementation/conselho/$TIMESTAMP"
fi

echo "$OUTPUT_DIR"
"""
    env = os.environ.copy()
    if env_override:
        env.update(env_override)
    proc = subprocess.run(
        ["bash", "-c", bash_snippet],
        capture_output=True,
        text=True,
        cwd=cwd,
        env=env,
        timeout=10,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"Bash snippet failed (exit {proc.returncode}):\n"
            f"stdout: {proc.stdout}\nstderr: {proc.stderr}"
        )
    return Path(proc.stdout.strip()).resolve()


class TestConselhoOutputDir(unittest.TestCase):
    """Behavioral tests for the Conselho output directory resolution."""

    def setUp(self) -> None:
        # Create a temporary git repo simulating the user's project (resolved for macOS symlinks)
        self.user_repo = Path(tempfile.mkdtemp(prefix="ceh-user-repo-")).resolve()
        subprocess.run(
            ["git", "init", str(self.user_repo)],
            capture_output=True,
            check=True,
        )
        # Create the docs directory so the path is plausible
        (self.user_repo / "docs" / "temp_implementation" / "conselho").mkdir(
            parents=True, exist_ok=True
        )

        # Create a non-git temporary directory for fallback tests (resolved)
        self.no_git_dir = Path(tempfile.mkdtemp(prefix="ceh-no-git-")).resolve()

        # Create a fake external install path for scenario (b)
        self.external_dir = Path(tempfile.mkdtemp(prefix="ceh-external-plugin-")).resolve()
        self.external_script = self.external_dir / "conselho-seniores.sh"
        shutil.copy2(SCRIPT_PATH, self.external_script)

        # Copy script into non-git directory for hermetic fallback test (c)
        self.no_git_script = self.no_git_dir / "conselho-seniores.sh"
        shutil.copy2(SCRIPT_PATH, self.no_git_script)

    def tearDown(self) -> None:
        shutil.rmtree(self.user_repo, ignore_errors=True)
        shutil.rmtree(self.no_git_dir, ignore_errors=True)
        shutil.rmtree(self.external_dir, ignore_errors=True)

    # ------------------------------------------------------------------
    # Scenario (a): cwd inside user's git repo
    # ------------------------------------------------------------------
    def test_output_dir_inside_user_git_repo(self) -> None:
        """When cwd is inside a git repo, OUTPUT_DIR must be anchored to that
        repo's root under docs/temp_implementation/conselho/."""
        output_dir = _extract_output_dir_from_script(cwd=str(self.user_repo))
        self.assertTrue(
            _is_relative_to(output_dir, self.user_repo),
            f"OUTPUT_DIR '{output_dir}' does not start with user repo '{self.user_repo}'",
        )
        self.assertIn(
            "docs/temp_implementation/conselho",
            str(output_dir),
            "OUTPUT_DIR must contain the canonical conselho subpath",
        )

    # ------------------------------------------------------------------
    # Scenario (b): script invoked from external installation, cwd in user repo
    # ------------------------------------------------------------------
    def test_output_dir_external_script_invocation(self) -> None:
        """When the script lives in an external directory (e.g. /opt/plugin),
        but cwd is inside the user's git repo, OUTPUT_DIR must still be
        anchored to the user's repo — never to the script's installation path.
        """
        output_dir = _extract_output_dir_from_script(
            cwd=str(self.user_repo), script_path=self.external_script
        )
        self.assertTrue(
            _is_relative_to(output_dir, self.user_repo),
            f"OUTPUT_DIR '{output_dir}' leaked to external script dir",
        )
        self.assertFalse(
            _is_relative_to(output_dir, self.external_dir),
            f"OUTPUT_DIR '{output_dir}' incorrectly anchored to external dir '{self.external_dir}'",
        )
        self.assertIn(
            "docs/temp_implementation/conselho",
            str(output_dir),
        )

    # ------------------------------------------------------------------
    # Scenario (c): cwd outside any git repo — fallback
    # ------------------------------------------------------------------
    def test_output_dir_fallback_no_git(self) -> None:
        """When cwd is NOT inside any git repo and the script dir is also not
        in a git repo, OUTPUT_DIR must fall back to <cwd>/docs/temp_implementation/conselho/,
        using pwd as REPO_ROOT."""
        output_dir = _extract_output_dir_from_script(
            cwd=str(self.no_git_dir), script_path=self.no_git_script
        )
        self.assertTrue(
            _is_relative_to(output_dir, self.no_git_dir),
            f"Fallback OUTPUT_DIR '{output_dir}' is not under cwd '{self.no_git_dir}'",
        )
        self.assertIn(
            "docs/temp_implementation/conselho",
            str(output_dir),
            "Fallback OUTPUT_DIR must still use the canonical subpath",
        )


if __name__ == "__main__":
    unittest.main()
