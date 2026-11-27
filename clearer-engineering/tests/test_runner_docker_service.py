#!/usr/bin/env python3
"""Testes comportamentais do Runtime Adapter para docker_service em test-runner.sh."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


RUNNER_SCRIPT = (
    Path(__file__).resolve().parents[1] / "scripts" / "test-runner.sh"
)


class TestRunnerDockerService(unittest.TestCase):
    """Valida docker_service='host'|'none'|null|omitido no test-runner.sh."""

    def setUp(self) -> None:
        self.base_dir = Path(tempfile.mkdtemp(prefix="ceh_docker_svc_")).resolve()
        self.repo_dir = self.base_dir / "repo"
        self.repo_dir.mkdir(parents=True, exist_ok=True)
        self.fake_bin = self.base_dir / "fake_bin"
        self.fake_bin.mkdir(parents=True, exist_ok=True)

        self.host_marker = self.base_dir / "host_ran.txt"
        self.docker_calls_log = self.base_dir / "docker_calls.log"
        self.docker_exec_log = self.base_dir / "docker_exec.log"

        self._init_fake_bin()
        self._init_git_repo()

    def tearDown(self) -> None:
        shutil.rmtree(self.base_dir, ignore_errors=True)

    def _init_fake_bin(self) -> None:
        mock_timeout = self.fake_bin / "timeout"
        mock_timeout.write_text("#!/bin/sh\nshift\nexec \"$@\"\n", encoding="utf-8")
        mock_timeout.chmod(0o755)

        mock_docker = self.fake_bin / "docker"
        mock_docker.write_text(
            "#!/bin/sh\n"
            f"printf '%s\\n' \"$*\" >> '{self.docker_calls_log}'\n"
            "if [ \"$1\" = \"info\" ]; then\n"
            "    exit 0\n"
            "fi\n"
            "if [ \"$1\" = \"compose\" ] && [ \"$2\" = \"ps\" ]; then\n"
            "    echo 'web'\n"
            "    exit 0\n"
            "fi\n"
            "if [ \"$1\" = \"compose\" ] && [ \"$2\" = \"exec\" ]; then\n"
            f"    printf 'DOCKER_EXEC:%s\\n' \"$*\" >> '{self.docker_exec_log}'\n"
            "    exit 0\n"
            "fi\n"
            "exit 0\n",
            encoding="utf-8",
        )
        mock_docker.chmod(0o755)

    def _init_git_repo(self) -> None:
        subprocess.run(
            ["git", "init", "-b", "dev"],
            cwd=self.repo_dir,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Tester"],
            cwd=self.repo_dir,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "tester@clearer.local"],
            cwd=self.repo_dir,
            check=True,
            capture_output=True,
        )

        (self.repo_dir / "docker-compose.yml").write_text(
            "services:\n  web:\n    image: alpine:latest\n",
            encoding="utf-8",
        )
        scripts_dir = self.repo_dir / "scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        ci_local = scripts_dir / "ci-local.sh"
        ci_local.write_text(
            "#!/bin/sh\n"
            f"printf 'HOST_RAN:%s\\n' \"${{CI_RUNTIME:-unset}}\" > '{self.host_marker}'\n"
            "echo 'ci-local host ok'\n"
            "exit 0\n",
            encoding="utf-8",
        )
        ci_local.chmod(0o755)

        subprocess.run(["git", "add", "."], cwd=self.repo_dir, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "chore (repo): inicializar projeto fixture"],
            cwd=self.repo_dir,
            check=True,
            capture_output=True,
        )

    def _commit_ceh_config(self, config_payload: dict) -> None:
        ceh_dir = self.repo_dir / ".ceh"
        ceh_dir.mkdir(parents=True, exist_ok=True)
        (ceh_dir / "config.json").write_text(
            json.dumps(config_payload, indent=2),
            encoding="utf-8",
        )
        subprocess.run(["git", "add", ".ceh/config.json"], cwd=self.repo_dir, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "chore (ceh): configurar runner canonico"],
            cwd=self.repo_dir,
            check=True,
            capture_output=True,
        )

    def _build_env(self) -> dict:
        env = os.environ.copy()
        orig_parts = [p for p in env.get("PATH", "").split(os.pathsep) if p]
        filtered_parts = [
            p
            for p in orig_parts
            if p in ("/bin", "/usr/bin") or not (Path(p) / "rtk").exists()
        ]
        env["PATH"] = os.pathsep.join([str(self.fake_bin)] + filtered_parts)
        return env

    def _run_runner(self) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["bash", str(RUNNER_SCRIPT)],
            cwd=self.repo_dir,
            env=self._build_env(),
            capture_output=True,
            text=True,
        )

    def _read_cert(self) -> dict:
        cert_file = self.repo_dir / ".ceh" / "last-ci-run.json"
        self.assertTrue(cert_file.exists(), "Certificado .ceh/last-ci-run.json não foi gerado.")
        return json.loads(cert_file.read_text(encoding="utf-8"))

    def test_docker_service_host_runs_on_native_host_and_emits_canonical_cert(self) -> None:
        """Happy path: docker_service='host' executa no host sem docker compose exec."""
        self._commit_ceh_config(
            {
                "canonical_test_command": "./scripts/ci-local.sh",
                "docker_service": "host",
            }
        )
        res = self._run_runner()
        self.assertEqual(res.returncode, 0, f"Stdout:\n{res.stdout}\nStderr:\n{res.stderr}")
        self.assertTrue(self.host_marker.exists(), "Script ./scripts/ci-local.sh deveria ter rodado no host.")
        self.assertFalse(self.docker_exec_log.exists(), "Não deveria invocar docker compose exec.")
        self.assertFalse(self.docker_calls_log.exists(), "Não deveria sondar docker info/compose ps em modo host.")
        self.assertIn("docker_service='host'", res.stdout)

        cert = self._read_cert()
        self.assertIs(cert.get("canonical_verified"), True)
        self.assertEqual(cert.get("status"), "PASS")
        self.assertEqual(cert.get("exit_code"), 0)
        self.assertEqual(cert.get("normalized_runner"), "./scripts/ci-local.sh")

    def test_docker_service_none_runs_on_native_host_and_emits_canonical_cert(self) -> None:
        """Edge path: docker_service='none' executa no host sem docker compose exec."""
        self._commit_ceh_config(
            {
                "canonical_test_command": "./scripts/ci-local.sh",
                "docker_service": "none",
            }
        )
        res = self._run_runner()
        self.assertEqual(res.returncode, 0, f"Stdout:\n{res.stdout}\nStderr:\n{res.stderr}")
        self.assertTrue(self.host_marker.exists(), "Script ./scripts/ci-local.sh deveria ter rodado no host.")
        self.assertFalse(self.docker_exec_log.exists(), "Não deveria invocar docker compose exec.")
        self.assertFalse(self.docker_calls_log.exists(), "Não deveria sondar docker info/compose ps em modo none.")
        self.assertIn("docker_service='none'", res.stdout)

        cert = self._read_cert()
        self.assertIs(cert.get("canonical_verified"), True)
        self.assertEqual(cert.get("status"), "PASS")
        self.assertEqual(cert.get("exit_code"), 0)
        self.assertEqual(cert.get("normalized_runner"), "./scripts/ci-local.sh")

    def test_omitted_docker_service_keeps_container_dispatch_regression(self) -> None:
        """Regressão: sem docker_service continua despachando via container web."""
        self._commit_ceh_config({"canonical_test_command": "./scripts/ci-local.sh"})
        res = self._run_runner()
        self.assertEqual(res.returncode, 0, f"Stdout:\n{res.stdout}\nStderr:\n{res.stderr}")
        self.assertFalse(self.host_marker.exists(), "Não deveria rodar direto no host quando web está ativo.")
        self.assertTrue(self.docker_exec_log.exists(), "Deveria invocar docker compose exec.")
        exec_log = self.docker_exec_log.read_text(encoding="utf-8")
        self.assertIn("compose exec -T web ./scripts/ci-local.sh", exec_log)
        self.assertIn("Container 'web' ativo detectado", res.stdout)

        cert = self._read_cert()
        self.assertIs(cert.get("canonical_verified"), True)
        self.assertEqual(cert.get("status"), "PASS")
        self.assertEqual(cert.get("exit_code"), 0)

    def test_null_docker_service_treated_as_omitted(self) -> None:
        """Edge path: docker_service=null deve se comportar como omitido (sem tratar 'None' como serviço)."""
        self._commit_ceh_config(
            {
                "canonical_test_command": "./scripts/ci-local.sh",
                "docker_service": None,
            }
        )
        res = self._run_runner()
        self.assertEqual(res.returncode, 0, f"Stdout:\n{res.stdout}\nStderr:\n{res.stderr}")
        self.assertTrue(self.docker_exec_log.exists(), "Deveria despachar via container web quando null.")
        exec_log = self.docker_exec_log.read_text(encoding="utf-8")
        self.assertIn("compose exec -T web ./scripts/ci-local.sh", exec_log)

    def _install_mock_rtk(self) -> Path:
        rtk_log = self.base_dir / "rtk_calls.log"
        mock_rtk = self.fake_bin / "rtk"
        mock_rtk.write_text(
            "#!/bin/sh\n"
            f"printf '%s\\n' \"$*\" >> '{rtk_log}'\n"
            "case \"$1\" in\n"
            "  *=*)\n"
            "    echo '[rtk: No such file or directory (os error 2)]' >&2\n"
            "    exit 127\n"
            "    ;;\n"
            "esac\n"
            "exec \"$@\"\n",
            encoding="utf-8",
        )
        mock_rtk.chmod(0o755)
        return rtk_log

    def test_env_prefix_command_skips_rtk_wrap_and_emits_canonical_cert(self) -> None:
        """Regressão: VAR=val cmd não deve ser embrulhado em 'rtk VAR=val cmd'."""
        rtk_log = self._install_mock_rtk()
        self._commit_ceh_config(
            {"canonical_test_command": "CI_RUNTIME=docker ./scripts/ci-local.sh"}
        )
        res = self._run_runner()
        self.assertEqual(res.returncode, 0, f"Stdout:\n{res.stdout}\nStderr:\n{res.stderr}")
        self.assertFalse(rtk_log.exists(), "rtk não deve embrulhar comando com prefixo VAR=val.")
        self.assertTrue(self.host_marker.exists(), "Script ./scripts/ci-local.sh deveria ter executado.")
        self.assertEqual(self.host_marker.read_text(encoding="utf-8").strip(), "HOST_RAN:docker")

        cert = self._read_cert()
        self.assertIs(cert.get("canonical_verified"), True)
        self.assertEqual(cert.get("status"), "PASS")
        self.assertEqual(cert.get("exit_code"), 0)
        self.assertEqual(cert.get("normalized_runner"), "CI_RUNTIME=docker ./scripts/ci-local.sh")

    def test_plain_command_keeps_rtk_wrap_when_rtk_present(self) -> None:
        """Preservação: comando simples sem VAR=val continua usando rtk quando disponível."""
        rtk_log = self._install_mock_rtk()
        self._commit_ceh_config(
            {
                "canonical_test_command": "./scripts/ci-local.sh",
                "docker_service": "host",
            }
        )
        res = self._run_runner()
        self.assertEqual(res.returncode, 0, f"Stdout:\n{res.stdout}\nStderr:\n{res.stderr}")
        self.assertTrue(rtk_log.exists(), "rtk deveria envolver comando simples sem prefixo VAR=val.")
        self.assertIn("./scripts/ci-local.sh", rtk_log.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
