#!/usr/bin/env python3
"""
test_rules_data_infra.py - Testes de cobertura de regras de dados, infraestrutura (AT3)
e integridade de leitura/exclusão de .ceh (AM2) do Safety Gate (PR-22).

Especificação (Handoff 047):
1. AT3: Git stash (clear/drop), Docker volumes/prune/compose down -v, Redis flushall/flushdb,
   Prisma migrate reset, e sobrescrita de arquivo comum via dd.
   Graduação completa por Caso de Uso:
   - DEV: allow
   - HML (staging): ask (com 2 alertas explícitos)
   - PROD: deny
2. AM2: Leituras puras de .ceh (du, diff, git status/log/diff/show) e cláusulas de exclusão
   (--exclude=.ceh, -path ./.ceh -prune) permitidas (allow) sem comprometer o bloqueio fail-closed
   contra tentativas reais de escrita (tar -C .ceh, rsync .ceh/, diff > .ceh/..., find .ceh -delete).
3. Variações de caixa, opções intermediárias, prefixos e composição em pipelines (&&, ;).
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from importlib import import_module
safety_gate = import_module("safety-gate")


class TestRulesDataInfra(unittest.TestCase):
    """Bateria de testes de dados, infraestrutura e leituras de .ceh."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="ceh-data-infra-")
        subprocess.run(["git", "init", "-q", "-b", "dev", self.tmp], check=True)
        self.orig_cwd = os.getcwd()
        os.chdir(self.tmp)

    def tearDown(self):
        os.chdir(self.orig_cwd)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def assert_decision(self, cmd: str, env: str, expected_dec: str, expected_uc: str | None = None):
        dec, reason, env_res, uc = safety_gate.evaluate_command(cmd, explicit_env=env)
        self.assertEqual(
            dec, expected_dec,
            f"Falha na decisão para '{cmd}' em {env}: esperado {expected_dec}, obtido {dec} (uc={uc}, reason={reason})"
        )
        if expected_uc is not None:
            self.assertEqual(
                uc, expected_uc,
                f"Falha no Caso de Uso para '{cmd}' em {env}: esperado {expected_uc}, obtido {uc}"
            )

    # -------------------------------------------------------------------------
    # 1. AT3: Git Stash (clear / drop) -> GIT_HISTORY
    # -------------------------------------------------------------------------
    def test_git_stash_graduation(self):
        commands = [
            "git stash clear",
            "git stash drop",
            "git stash drop stash@{0}",
            "git stash drop -q",
        ]
        for cmd in commands:
            self.assert_decision(cmd, "development", "allow", "GIT_HISTORY")
            self.assert_decision(cmd, "staging", "ask", "GIT_HISTORY")
            self.assert_decision(cmd, "production", "deny", "GIT_HISTORY")

    def test_git_stash_benign_controls(self):
        safe_commands = [
            "git stash list",
            "git stash show",
            "git stash show -p",
        ]
        for cmd in safe_commands:
            self.assert_decision(cmd, "production", "allow")

    # -------------------------------------------------------------------------
    # 2. AT3: Docker Volumes & Compose Down -v -> INFRASTRUCTURE
    # -------------------------------------------------------------------------
    def test_docker_volume_graduation(self):
        commands = [
            "docker volume rm data",
            "docker volume rm -f my_vol",
            "docker volume prune",
            "docker volume prune -f",
        ]
        for cmd in commands:
            self.assert_decision(cmd, "development", "allow", "INFRASTRUCTURE")
            self.assert_decision(cmd, "staging", "ask", "INFRASTRUCTURE")
            self.assert_decision(cmd, "production", "deny", "INFRASTRUCTURE")

    def test_docker_compose_down_volumes_graduation(self):
        commands = [
            "docker compose down -v",
            "docker-compose down -v",
            "docker compose down --volumes",
            "docker-compose down --volumes",
            "docker compose -f docker-compose.prod.yml down -v",
            "docker compose down -v --remove-orphans",
        ]
        for cmd in commands:
            self.assert_decision(cmd, "development", "allow", "INFRASTRUCTURE")
            self.assert_decision(cmd, "staging", "ask", "INFRASTRUCTURE")
            self.assert_decision(cmd, "production", "deny", "INFRASTRUCTURE")

    def test_docker_benign_controls(self):
        safe_commands = [
            "docker volume ls",
            "docker compose down",
            "docker compose ps",
            "docker compose logs",
        ]
        for cmd in safe_commands:
            self.assert_decision(cmd, "production", "allow")

    # -------------------------------------------------------------------------
    # 3. AT3: Redis (flushall / flushdb) -> DATABASE
    # -------------------------------------------------------------------------
    def test_redis_cli_flush_graduation_and_case_insensitivity(self):
        commands = [
            "redis-cli flushall",
            "redis-cli flushdb",
            "redis-cli FLUSHALL",
            "redis-cli -h db FLUSHDB",
            "redis-cli -h 127.0.0.1 -p 6379 flushall async",
            "redis-cli --cluster call 127.0.0.1:7000 flushall",
        ]
        for cmd in commands:
            self.assert_decision(cmd, "development", "allow", "DATABASE")
            self.assert_decision(cmd, "staging", "ask", "DATABASE")
            self.assert_decision(cmd, "production", "deny", "DATABASE")

    def test_redis_cli_benign_controls(self):
        safe_commands = [
            "redis-cli ping",
            "redis-cli info",
            "redis-cli get user:123",
            "redis-cli dbsize",
        ]
        for cmd in safe_commands:
            self.assert_decision(cmd, "production", "allow")

    # -------------------------------------------------------------------------
    # 4. AT3: Prisma (migrate reset) -> DATABASE
    # -------------------------------------------------------------------------
    def test_prisma_migrate_reset_graduation(self):
        commands = [
            "prisma migrate reset",
            "prisma migrate reset --force",
            "npx prisma migrate reset",
            "npx prisma migrate reset --skip-seed",
        ]
        for cmd in commands:
            self.assert_decision(cmd, "development", "allow", "DATABASE")
            self.assert_decision(cmd, "staging", "ask", "DATABASE")
            self.assert_decision(cmd, "production", "deny", "DATABASE")

    def test_prisma_benign_controls(self):
        safe_commands = [
            "prisma migrate deploy",
            "prisma migrate status",
            "npx prisma generate",
        ]
        for cmd in safe_commands:
            self.assert_decision(cmd, "production", "allow")

    # -------------------------------------------------------------------------
    # 5. AT3: dd (sobrescrita de arquivo vs disco cru)
    # -------------------------------------------------------------------------
    def test_dd_file_overwrite_graduation(self):
        file_commands = [
            "dd if=/dev/zero of=app.db",
            "dd if=/dev/zero of=data.raw bs=1M count=10",
            "dd if=/tmp/seed.img of=/var/lib/mysql/ibdata1",
        ]
        for cmd in file_commands:
            self.assert_decision(cmd, "development", "allow", "FILESYSTEM")
            self.assert_decision(cmd, "staging", "ask", "FILESYSTEM")
            self.assert_decision(cmd, "production", "deny", "FILESYSTEM")

    def test_dd_disk_writing_catastrophic_invariant(self):
        raw_disk_commands = [
            "dd if=x of=/dev/sda",
            "dd if=/dev/zero of=/dev/nvme0n1",
            "dd if=boot.img of=/dev/sdb bs=4M",
        ]
        for cmd in raw_disk_commands:
            for env in ("development", "staging", "production"):
                self.assert_decision(cmd, env, "deny", "CATASTROPHIC")

    # -------------------------------------------------------------------------
    # 6. AM2: Leituras puras de .ceh e argumentos de exclusão (allow)
    # -------------------------------------------------------------------------
    def test_am2_allowed_reads_and_exclusions(self):
        allowed_commands = [
            "find . -path ./.ceh -prune -o -name '*.py' -print",
            "tar czf out.tgz --exclude=.ceh .",
            "tar czf out.tgz --exclude .ceh .",
            "du -sh .ceh",
            "du -k .ceh/last-ci-run.json",
            "diff .ceh/last-ci-run.json /tmp/x",
            "diff -u .ceh/last-ci-run.json /tmp/x",
            "git status --ignored .ceh",
            "git log -n 1 -- .ceh",
            "git diff HEAD -- .ceh",
            "git show HEAD:.ceh/last-ci-run.json",
        ]
        for cmd in allowed_commands:
            for env in ("development", "staging", "production"):
                self.assert_decision(cmd, env, "allow")

    def test_am2_tampering_controls_remain_denied(self):
        tampering_commands = [
            "tar xf evil.tar -C .ceh",
            "rsync -a /tmp/fake/ .ceh/",
            "cp -r /tmp/fakeceh/. .ceh",
            "diff a b > .ceh/last-ci-run.json",
            "find .ceh -delete",
            "git checkout -- .ceh",
            "git restore .ceh",
            "git clean -f .ceh",
        ]
        for cmd in tampering_commands:
            for env in ("development", "staging", "production"):
                self.assert_decision(cmd, env, "deny")

    # -------------------------------------------------------------------------
    # 7. Composição e Pipelines
    # -------------------------------------------------------------------------
    def test_composition_pipelines(self):
        pipeline_commands = [
            ("ls && redis-cli flushall", "DATABASE"),
            ("git status && docker compose down -v", "INFRASTRUCTURE"),
            ("echo 'clean' ; git stash drop", "GIT_HISTORY"),
            ("dd if=/dev/zero of=test.bin && ls -la", "FILESYSTEM"),
        ]
        for cmd, expected_uc in pipeline_commands:
            self.assert_decision(cmd, "development", "allow")
            self.assert_decision(cmd, "staging", "ask", expected_uc)
            self.assert_decision(cmd, "production", "deny", expected_uc)


if __name__ == "__main__":
    unittest.main()
