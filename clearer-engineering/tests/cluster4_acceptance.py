#!/usr/bin/env python3
"""
cluster4_acceptance.py - Acceptance Test Suite for Cluster 4 (Bypasses G1–G5, G7)
Every test is initialized in RED state using @unittest.expectedFailure.
When each fix PR (PR-04 to PR-08) resolves a specific vulnerability group,
the corresponding @unittest.expectedFailure decorator will be removed, turning the test GREEN.
"""

import sys
import os
import unittest
import base64
import tempfile
import shutil
import subprocess
from pathlib import Path
from importlib import import_module

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

safety_gate = import_module("safety-gate")
evaluate_command = safety_gate.evaluate_command


def b64(s: str) -> str:
    return base64.b64decode(s).decode("utf-8")


class Cluster4Acceptance(unittest.TestCase):
    """
    Acceptance test suite corresponding strictly to Handoff 010 baseline table.
    """

    # --------------------------------------------------------------------------
    # G1: Filesystem Scope / Multi-target bypasses
    # --------------------------------------------------------------------------
    @unittest.expectedFailure
    def test_g1_multitarget_build_and_src_production(self):
        """G1: rm -rf build/ src/ in production must be denied (today: allow)"""
        cmd = b64("cm0gLXJmIGJ1aWxkLyBzcmMv") # rm -rf build/ src/
        decision, reason, env, use_case = evaluate_command(cmd, explicit_env="production")
        self.assertEqual(decision, "deny", f"Esperado 'deny', mas obtido '{decision}' com razão: {reason}")

    @unittest.expectedFailure
    def test_g1_multitarget_safe_and_system_dir_production(self):
        """G1: rm -rf a.txt /var/lib/postgresql in production must be denied (today: allow)"""
        cmd = b64("cm0gLXJmIGEudHh0IC92YXIvbGliL3Bvc3RncmVzcWw=") # rm -rf a.txt /var/lib/postgresql
        decision, reason, env, use_case = evaluate_command(cmd, explicit_env="production")
        self.assertEqual(decision, "deny", f"Esperado 'deny', mas obtido '{decision}' com razão: {reason}")

    # --------------------------------------------------------------------------
    # G2: Git Working Tree Discard bypasses
    # --------------------------------------------------------------------------
    @unittest.expectedFailure
    def test_g2_git_checkout_dot_production(self):
        """G2: git checkout . in production must be denied (today: allow)"""
        cmd = b64("Z2l0IGNoZWNrb3V0IC4=") # git checkout .
        decision, reason, env, use_case = evaluate_command(cmd, explicit_env="production")
        self.assertEqual(decision, "deny", f"Esperado 'deny', mas obtido '{decision}' com razão: {reason}")

    @unittest.expectedFailure
    def test_g2_git_restore_dot_production(self):
        """G2: git restore . in production must be denied (today: allow)"""
        cmd = b64("Z2l0IHJlc3RvcmUgLg==") # git restore .
        decision, reason, env, use_case = evaluate_command(cmd, explicit_env="production")
        self.assertEqual(decision, "deny", f"Esperado 'deny', mas obtido '{decision}' com razão: {reason}")

    @unittest.expectedFailure
    def test_g2_git_checkout_dashdash_dot_production(self):
        """G2: git checkout -- . in production must be denied (today: allow)"""
        cmd = b64("Z2l0IGNoZWNrb3V0IC0tIC4=") # git checkout -- .
        decision, reason, env, use_case = evaluate_command(cmd, explicit_env="production")
        self.assertEqual(decision, "deny", f"Esperado 'deny', mas obtido '{decision}' com razão: {reason}")

    # --------------------------------------------------------------------------
    # G3: Git Flags & Options Preceding Subcommand
    # --------------------------------------------------------------------------
    @unittest.expectedFailure
    def test_g3_git_C_reset_hard_production(self):
        """G3: git -C . reset --hard in production must be denied (today: allow)"""
        cmd = b64("Z2l0IC1DIC4gcmVzZXQgLS1oYXJk") # git -C . reset --hard
        decision, reason, env, use_case = evaluate_command(cmd, explicit_env="production")
        self.assertEqual(decision, "deny", f"Esperado 'deny', mas obtido '{decision}' com razão: {reason}")

    @unittest.expectedFailure
    def test_g3_git_no_pager_reset_hard_production(self):
        """G3: git --no-pager reset --hard in production must be denied (today: allow)"""
        cmd = b64("Z2l0IC0tbm8tcGFnZXIgcmVzZXQgLS1oYXJk") # git --no-pager reset --hard
        decision, reason, env, use_case = evaluate_command(cmd, explicit_env="production")
        self.assertEqual(decision, "deny", f"Esperado 'deny', mas obtido '{decision}' com razão: {reason}")

    # --------------------------------------------------------------------------
    # G4: Catastrophic Root & Home Directory Deletions
    # --------------------------------------------------------------------------
    @unittest.expectedFailure
    def test_g4_rm_split_flags_root_development(self):
        """G4: rm -r -f / in development must be denied (catastrophic) (today: allow)"""
        cmd = b64("cm0gLXIgLWYgLw==") # rm -r -f /
        decision, reason, env, use_case = evaluate_command(cmd, explicit_env="development")
        self.assertEqual(decision, "deny", f"Esperado 'deny', mas obtido '{decision}' com razão: {reason}")

    @unittest.expectedFailure
    def test_g4_rm_wildcard_root_development(self):
        """G4: rm -rf /* in development must be denied (catastrophic) (today: allow)"""
        cmd = b64("cm0gLXJmIC8q") # rm -rf /*
        decision, reason, env, use_case = evaluate_command(cmd, explicit_env="development")
        self.assertEqual(decision, "deny", f"Esperado 'deny', mas obtido '{decision}' com razão: {reason}")

    @unittest.expectedFailure
    def test_g4_rm_home_env_var_development(self):
        """G4: rm -rf $HOME in development must be denied (catastrophic) (today: allow)"""
        cmd = b64("cm0gLXJmICRIT01F") # rm -rf $HOME
        decision, reason, env, use_case = evaluate_command(cmd, explicit_env="development")
        self.assertEqual(decision, "deny", f"Esperado 'deny', mas obtido '{decision}' com razão: {reason}")

    @unittest.expectedFailure
    def test_g4_rm_long_flags_root_production(self):
        """G4: rm --recursive --force / in production must be denied (today: allow)"""
        cmd = b64("cm0gLS1yZWN1cnNpdmUgLS1mb3JjZSAv") # rm --recursive --force /
        decision, reason, env, use_case = evaluate_command(cmd, explicit_env="production")
        self.assertEqual(decision, "deny", f"Esperado 'deny', mas obtido '{decision}' com razão: {reason}")

    # --------------------------------------------------------------------------
    # G5: Alternative Deletion Tools (find, python shutil)
    # --------------------------------------------------------------------------
    @unittest.expectedFailure
    def test_g5_find_delete_root_production(self):
        """G5: find / -delete in production must be denied (today: allow)"""
        cmd = b64("ZmluZCAvIC1kZWxldGU=") # find / -delete
        decision, reason, env, use_case = evaluate_command(cmd, explicit_env="production")
        self.assertEqual(decision, "deny", f"Esperado 'deny', mas obtido '{decision}' com razão: {reason}")

    @unittest.expectedFailure
    def test_g5_find_exec_rm_production(self):
        """G5: find . -name x -exec rm {} + in production must be denied (today: allow)"""
        cmd = b64("ZmluZCAuIC1uYW1lIHggLWV4ZWMgcm0ge30gKw==") # find . -name x -exec rm {} +
        decision, reason, env, use_case = evaluate_command(cmd, explicit_env="production")
        self.assertEqual(decision, "deny", f"Esperado 'deny', mas obtido '{decision}' com razão: {reason}")

    @unittest.expectedFailure
    def test_g5_python_shutil_rmtree_production(self):
        """G5: python3 -c 'import shutil; shutil.rmtree("/srv")' in production must be denied (today: allow)"""
        cmd = b64("cHl0aG9uMyAtYyAnaW1wb3J0IHNodXRpbDsgc2h1dGlsLnJtdHJlZSgiL3NydiIpJw==") # python3 shutil.rmtree
        decision, reason, env, use_case = evaluate_command(cmd, explicit_env="production")
        self.assertEqual(decision, "deny", f"Esperado 'deny', mas obtido '{decision}' com razão: {reason}")

    # --------------------------------------------------------------------------
    # G7: Pre-Push CI Refspec Source & Destination Audit (Handoff 011)
    # --------------------------------------------------------------------------
    @unittest.expectedFailure
    def test_g7_pre_push_ci_refspec_untested_commit_red(self):
        """G7 RED: git push origin outro:main with uncertified commit on 'outro' must be denied (today: allow)"""
        tmp_dir = tempfile.mkdtemp()
        original_cwd = os.getcwd()
        try:
            subprocess.run(["git", "init", "-b", "dev"], cwd=tmp_dir, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_dir, check=True)
            subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=tmp_dir, check=True)
            ci_dir = Path(tmp_dir) / ".github" / "workflows"
            ci_dir.mkdir(parents=True, exist_ok=True)
            (ci_dir / "ci.yml").write_text("name: CI\n")
            (Path(tmp_dir) / ".gitignore").write_text(".ceh/\n")
            (Path(tmp_dir) / "f").write_text("f\n")
            subprocess.run(["git", "add", "."], cwd=tmp_dir, check=True, capture_output=True)
            subprocess.run(["git", "commit", "-m", "init commit A"], cwd=tmp_dir, check=True, capture_output=True)
            
            # Branch outro com commit B a mais sem certificado
            subprocess.run(["git", "checkout", "-b", "outro"], cwd=tmp_dir, check=True, capture_output=True)
            (Path(tmp_dir) / "f2").write_text("f2\n")
            subprocess.run(["git", "add", "."], cwd=tmp_dir, check=True, capture_output=True)
            subprocess.run(["git", "commit", "-m", "commit B sem cert"], cwd=tmp_dir, check=True, capture_output=True)

            # Volta para dev onde o HEAD atual é o commit A certificado
            subprocess.run(["git", "checkout", "dev"], cwd=tmp_dir, check=True, capture_output=True)
            head_a = subprocess.run(["git", "rev-parse", "HEAD"], cwd=tmp_dir, check=True, capture_output=True, text=True).stdout.strip()
            ceh_dir = Path(tmp_dir) / ".ceh"
            ceh_dir.mkdir(parents=True, exist_ok=True)
            (ceh_dir / "last-ci-run.json").write_text(f'{{"commit_hash": "{head_a}", "status": "PASS", "exit_code": 0, "canonical_verified": true, "command": "npm test"}}')

            # git push origin outro:main tenta enviar commit B (não certificado)
            cmd = "git push origin outro:main"
            os.chdir(tmp_dir)
            decision, reason, env, use_case = evaluate_command(cmd, explicit_env="development")
            self.assertEqual(decision, "deny", f"Esperado 'deny' ao enviar commit não certificado via refspec, obtido '{decision}'")
        finally:
            os.chdir(original_cwd)
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_g7_pre_push_ci_refspec_certified_commit_control(self):
        """G7 CONTROLE (verde): git push origin dev:main with dev == HEAD certified must be allowed (legitimate promotion)"""
        tmp_dir = tempfile.mkdtemp()
        original_cwd = os.getcwd()
        try:
            subprocess.run(["git", "init", "-b", "dev"], cwd=tmp_dir, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_dir, check=True)
            subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=tmp_dir, check=True)
            ci_dir = Path(tmp_dir) / ".github" / "workflows"
            ci_dir.mkdir(parents=True, exist_ok=True)
            (ci_dir / "ci.yml").write_text("name: CI\n")
            (Path(tmp_dir) / "f").write_text("f\n")
            subprocess.run(["git", "add", "."], cwd=tmp_dir, check=True, capture_output=True)
            subprocess.run(["git", "commit", "-m", "init commit A"], cwd=tmp_dir, check=True, capture_output=True)
            
            # Commit A em dev está certificado
            head_a = subprocess.run(["git", "rev-parse", "HEAD"], cwd=tmp_dir, check=True, capture_output=True, text=True).stdout.strip()
            ceh_dir = Path(tmp_dir) / ".ceh"
            ceh_dir.mkdir(parents=True, exist_ok=True)
            (ceh_dir / "last-ci-run.json").write_text(f'{{"commit_hash": "{head_a}", "status": "PASS", "exit_code": 0, "canonical_verified": true}}')

            # git push origin dev:main envia commit A devidamente certificado
            cmd = "git push origin dev:main"
            os.chdir(tmp_dir)
            decision, reason, env, use_case = evaluate_command(cmd, explicit_env="development")
            self.assertEqual(decision, "allow", f"Esperado 'allow' ao promover commit certificado para main, obtido '{decision}'")
        finally:
            os.chdir(original_cwd)
            shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
