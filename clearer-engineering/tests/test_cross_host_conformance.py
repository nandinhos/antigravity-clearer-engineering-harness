#!/usr/bin/env python3
# ==============================================================================
# test_cross_host_conformance.py — Suíte de Conformidade de Decisão Cross-Host (PR-17)
# Prova in-process que todos os hosts tomam a mesma decisão que o motor CEH Core
# e que a renderização obedece à tabela observada do Handoff 081.
# ==============================================================================
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

# Inclusão do diretório scripts no sys.path
_SCRIPTS_DIR = str(Path(__file__).resolve().parents[1] / "scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from ceh_core.engine import Request, Decision, evaluate
from hook_context import find_adapter


def build_synthetic_terminal_payload(host: str, command: str, target_dir: Path | str) -> dict[str, Any]:
    """Gera payload sintético fiel de comando com as mesmas chaves dos payloads gravados."""
    t_str = str(target_dir)
    if host == "antigravity":
        return {
            "artifactDirectoryPath": "/tmp/agy_artifact",
            "conversationId": "conv-cross-host-test",
            "modelName": "gemini-3.8-flash-medium",
            "stepIdx": 1,
            "toolCall": {
                "name": "run_command",
                "args": {
                    "CommandLine": command,
                    "Cwd": t_str,
                    "WaitMsBeforeAsync": 2000,
                    "toolAction": "Running command",
                    "toolSummary": "Command execution"
                }
            },
            "transcriptPath": "/tmp/agy_transcript.jsonl",
            "workspacePaths": [t_str]
        }
    elif host == "claude_code":
        return {
            "cwd": t_str,
            "effort": {"level": "high"},
            "hook_event_name": "PreToolUse",
            "permission_mode": "default",
            "prompt_id": "prompt-cross-host-test",
            "scratchpad_dir": "/tmp/claude_scratchpad",
            "session_id": "sess-cross-host-test",
            "tool_input": {
                "command": command,
                "description": "Running bash command"
            },
            "tool_name": "Bash",
            "tool_use_id": "call-claude-test",
            "transcript_path": "/tmp/claude_transcript.jsonl"
        }
    elif host == "muse":
        return {
            "cwd": t_str,
            "hook_event_name": "PreToolUse",
            "model": "muse-spark-1.3-contributor",
            "model_provider": "meta",
            "permission_mode": "bypassPermissions",
            "session_id": "sess-cross-host-test",
            "tool_input": {
                "command": command,
                "description": "Running bash command",
                "workdir": t_str
            },
            "tool_name": "bash",
            "tool_use_id": "call-muse-test",
            "transcript_path": None,
            "turn_id": "turn-cross-host-test"
        }
    raise ValueError(f"Host desconhecido: {host}")


def build_synthetic_write_payload(host: str, target_file: str, target_dir: Path | str) -> dict[str, Any]:
    """Gera payload sintético fiel de escrita com as mesmas chaves dos payloads gravados."""
    t_str = str(target_dir)
    if host == "antigravity":
        return {
            "artifactDirectoryPath": "/tmp/agy_artifact",
            "conversationId": "conv-cross-host-test",
            "modelName": "gemini-3.8-flash-medium",
            "stepIdx": 1,
            "toolCall": {
                "name": "write_to_file",
                "args": {
                    "CodeContent": "ceh-conformance-content",
                    "Description": "Writing test file",
                    "Overwrite": True,
                    "TargetFile": str(target_file),
                    "toolAction": "Writing file",
                    "toolSummary": "Write file"
                }
            },
            "transcriptPath": "/tmp/agy_transcript.jsonl",
            "workspacePaths": [t_str]
        }
    elif host == "claude_code":
        return {
            "cwd": t_str,
            "effort": {"level": "high"},
            "hook_event_name": "PreToolUse",
            "permission_mode": "default",
            "prompt_id": "prompt-cross-host-test",
            "scratchpad_dir": "/tmp/claude_scratchpad",
            "session_id": "sess-cross-host-test",
            "tool_input": {
                "content": "ceh-conformance-content",
                "file_path": str(target_file)
            },
            "tool_name": "Write",
            "tool_use_id": "call-claude-test",
            "transcript_path": "/tmp/claude_transcript.jsonl"
        }
    elif host == "muse":
        return {
            "cwd": t_str,
            "hook_event_name": "PreToolUse",
            "model": "muse-spark-1.3-contributor",
            "model_provider": "meta",
            "permission_mode": "bypassPermissions",
            "session_id": "sess-cross-host-test",
            "tool_input": {
                "content": "ceh-conformance-content",
                "path": str(target_file)
            },
            "tool_name": "write_file",
            "tool_use_id": "call-muse-test",
            "transcript_path": None,
            "turn_id": "turn-cross-host-test"
        }
    raise ValueError(f"Host desconhecido: {host}")


class TestCrossHostConformance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo_root = Path(__file__).resolve().parents[2]
        cls.fixtures_dir = cls.repo_root / "clearer-engineering" / "tests" / "fixtures"
        cls.corpus_file = cls.fixtures_dir / "gate_corpus.expected.jsonl"
        cls.adapters_fixtures = cls.fixtures_dir / "adapters"

        # Criar repositórios git herméticos para simular os 3 ambientes canônicos
        cls.sandbox_dir = tempfile.mkdtemp(prefix="ceh_cross_conformance_")
        cls.repos = {}
        for b in ["dev", "staging", "main"]:
            r_path = Path(cls.sandbox_dir) / b
            r_path.mkdir(parents=True, exist_ok=True)
            subprocess.run(["git", "init", "-b", b], cwd=r_path, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Tester"], cwd=r_path, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.local"], cwd=r_path, check=True, capture_output=True)
            ci_dir = r_path / ".github" / "workflows"
            ci_dir.mkdir(parents=True, exist_ok=True)
            (ci_dir / "ci.yml").write_text("name: CI\n")
            (r_path / "README.md").write_text(f"Repo {b}\n")
            subprocess.run(["git", "add", "."], cwd=r_path, check=True, capture_output=True)
            subprocess.run(["git", "commit", "-m", "init"], cwd=r_path, check=True, capture_output=True)
            cls.repos[b] = r_path

        cls.env_to_dir = {
            "development": cls.repos["dev"],
            "staging": cls.repos["staging"],
            "production": cls.repos["main"],
        }

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.sandbox_dir, ignore_errors=True)

    def _find_recorded_ref(self, host: str, tool_name: str) -> dict[str, Any] | None:
        rec_file = self.adapters_fixtures / host / "recorded.jsonl"
        if not rec_file.is_file():
            return None
        with open(rec_file, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                p = json.loads(line).get("payload", {})
                t_name = p.get("tool_name") or p.get("toolCall", {}).get("name")
                if t_name == tool_name:
                    return p
        return None

    def test_synthetic_payload_fidelity(self):
        """
        Garante que os payloads sintéticos possuem exatamente o mesmo conjunto de chaves
        que os payloads reais gravados em recorded.jsonl de cada host.
        """
        hosts_and_tools = [
            ("antigravity", "run_command", "write_to_file"),
            ("claude_code", "Bash", "Write"),
            ("muse", "bash", "write_file"),
        ]

        for host, cmd_tool, write_tool in hosts_and_tools:
            # 1. Comando de terminal
            ref_cmd = self._find_recorded_ref(host, cmd_tool)
            self.assertIsNotNone(ref_cmd, f"Payload gravado de referência não encontrado para {host}/{cmd_tool}")
            synth_cmd = build_synthetic_terminal_payload(host, "ls -la", "/tmp")

            self.assertEqual(
                set(synth_cmd.keys()),
                set(ref_cmd.keys()),
                f"Chaves de topo divergentes em {host}/{cmd_tool}: {set(synth_cmd.keys())} != {set(ref_cmd.keys())}"
            )
            if host == "antigravity":
                self.assertEqual(
                    set(synth_cmd["toolCall"]["args"].keys()),
                    set(ref_cmd["toolCall"]["args"].keys()),
                    f"Chaves de toolCall.args divergentes em {host}/{cmd_tool}"
                )
            else:
                self.assertEqual(
                    set(synth_cmd["tool_input"].keys()),
                    set(ref_cmd["tool_input"].keys()),
                    f"Chaves de tool_input divergentes em {host}/{cmd_tool}"
                )

            # 2. Ferramenta de escrita
            ref_write = self._find_recorded_ref(host, write_tool)
            self.assertIsNotNone(ref_write, f"Payload gravado de referência não encontrado para {host}/{write_tool}")
            synth_write = build_synthetic_write_payload(host, "/tmp/out.txt", "/tmp")

            self.assertEqual(
                set(synth_write.keys()),
                set(ref_write.keys()),
                f"Chaves de topo divergentes em {host}/{write_tool}: {set(synth_write.keys())} != {set(ref_write.keys())}"
            )
            if host == "antigravity":
                self.assertEqual(
                    set(synth_write["toolCall"]["args"].keys()),
                    set(ref_write["toolCall"]["args"].keys()),
                    f"Chaves de toolCall.args divergentes em {host}/{write_tool}"
                )
            else:
                self.assertEqual(
                    set(synth_write["tool_input"].keys()),
                    set(ref_write["tool_input"].keys()),
                    f"Chaves de tool_input divergentes em {host}/{write_tool}"
                )

    def test_cross_host_conformance_corpus(self):
        """
        Executa em processo todos os comandos do gate_corpus (1.016 comandos e integrações) nos 3 hosts:
        - Decisão e use_case rigorosamente iguais entre Antigravity, Claude Code, Muse e CEH Core engine.
        - Respostas de renderização e exit codes rigorosamente de acordo com a tabela observada.
        - Total: 1.016 comandos × 3 hosts = 3.048 avaliações (BJ2).
        """
        self.assertTrue(self.corpus_file.is_file(), f"Arquivo de corpus não encontrado: {self.corpus_file}")
        entries = [json.loads(line) for line in self.corpus_file.read_text(encoding="utf-8").splitlines() if line.strip()]

        # BJ2: Filtra estritamente os comandos e integrações reais (1.014 command + 2 integration = 1.016)
        command_entries = [e for e in entries if e.get("type") in ("command", "integration")]
        self.assertEqual(len(command_entries), 1016, "Corpus deve conter exatamente 1.016 entradas de comando e integração.")

        evaluated_count = 0
        divergences: list[str] = []

        for idx, entry in enumerate(command_entries):
            etype = entry.get("type")
            cmd = entry["command"]
            env = entry.get("env", "development")

            target_dir = self.env_to_dir[env]

            # 1. Avaliação direta no motor CEH Core
            engine_dec = evaluate(Request(command=cmd, cwd=target_dir))

            # 2. Montagem dos payloads sintéticos fiéis para cada host
            payloads = {
                "antigravity": build_synthetic_terminal_payload("antigravity", cmd, target_dir),
                "claude_code": build_synthetic_terminal_payload("claude_code", cmd, target_dir),
                "muse": build_synthetic_terminal_payload("muse", cmd, target_dir),
            }

            # 3. Processamento através dos adaptadores
            host_decisions: dict[str, Decision] = {}
            host_renders: dict[str, tuple[dict[str, Any], int]] = {}

            for hname in ["antigravity", "claude_code", "muse"]:
                p = payloads[hname]
                adapter = find_adapter(p)
                self.assertIsNotNone(adapter, f"Adaptador não encontrado para {hname}")
                req = adapter.parse(p)
                dec = evaluate(req)
                render_res, exit_code = adapter.render(dec, p)
                host_decisions[hname] = dec
                host_renders[hname] = (render_res, exit_code)

            dec_agy = host_decisions["antigravity"]
            dec_claude = host_decisions["claude_code"]
            dec_muse = host_decisions["muse"]

            # Veredito de Decisão e Use Case: Idênticos nos 3 hosts e no motor
            if not (dec_agy.decision == dec_claude.decision == dec_muse.decision == engine_dec.decision):
                divergences.append(
                    f"DIVERGÊNCIA DE DECISÃO em #{idx} ('{cmd}', env={env}): "
                    f"agy={dec_agy.decision}, claude={dec_claude.decision}, muse={dec_muse.decision}, engine={engine_dec.decision}"
                )

            if not (dec_agy.use_case == dec_claude.use_case == dec_muse.use_case == engine_dec.use_case):
                divergences.append(
                    f"DIVERGÊNCIA DE USE_CASE em #{idx} ('{cmd}', env={env}): "
                    f"agy={dec_agy.use_case}, claude={dec_claude.use_case}, muse={dec_muse.use_case}, engine={engine_dec.use_case}"
                )

            # Validação da Tabela de Render Observada (Handoff 081)
            # Antigravity: allow -> {"decision":"allow"}/0; deny/ask -> {"decision":"deny"}/0
            resp_agy, ec_agy = host_renders["antigravity"]
            if dec_agy.decision == "allow":
                if resp_agy.get("decision") != "allow" or ec_agy != 0:
                    divergences.append(f"Render Antigravity allow inválido em #{idx}: {resp_agy}, ec={ec_agy}")
            else:
                if resp_agy.get("decision") != "deny" or ec_agy != 0:
                    divergences.append(f"Render Antigravity deny/ask inválido em #{idx}: {resp_agy}, ec={ec_agy}")

            # Claude Code: allow -> {}/0; deny -> hookSpecificOutput deny/2; ask -> hookSpecificOutput ask/0
            resp_claude, ec_claude = host_renders["claude_code"]
            if dec_claude.decision == "allow":
                if resp_claude != {} or ec_claude != 0:
                    divergences.append(f"Render Claude allow inválido em #{idx}: {resp_claude}, ec={ec_claude}")
            elif dec_claude.decision == "deny":
                hso = resp_claude.get("hookSpecificOutput", {})
                if hso.get("permissionDecision") != "deny" or ec_claude != 2:
                    divergences.append(f"Render Claude deny inválido em #{idx}: {resp_claude}, ec={ec_claude}")
            elif dec_claude.decision == "ask":
                hso = resp_claude.get("hookSpecificOutput", {})
                if hso.get("permissionDecision") != "ask" or ec_claude != 0:
                    divergences.append(f"Render Claude ask inválido em #{idx}: {resp_claude}, ec={ec_claude}")

            # Muse: allow -> {}/0; deny/ask -> {"decision":"block"}/0
            resp_muse, ec_muse = host_renders["muse"]
            if dec_muse.decision == "allow":
                if resp_muse != {} or ec_muse != 0:
                    divergences.append(f"Render Muse allow inválido em #{idx}: {resp_muse}, ec={ec_muse}")
            else:
                if resp_muse.get("decision") != "block" or ec_muse != 0:
                    divergences.append(f"Render Muse deny/ask inválido em #{idx}: {resp_muse}, ec={ec_muse}")

            evaluated_count += 1

        self.assertEqual(evaluated_count, 1016, "Devem ser avaliadas exatamente 1.016 entradas de comando.")
        self.assertEqual(
            len(divergences), 0,
            f"Encontrada(s) {len(divergences)} divergência(s) de conformidade cross-host:\n" + "\n".join(divergences[:15])
        )

    def test_cross_host_conformance_subprocess_sample(self):
        """
        BJ1: Valida o caminho real de produção (safety-gate.py via subprocesso e handle_hook_lifecycle)
        em uma amostra uniforme de 1 a cada 20 comandos do corpus (51 comandos × 3 hosts = 153 execuções).
        Comprova que os exit codes e saídas JSON do processo filho conferem rigorosamente com a tabela observada.
        """
        safety_gate_py = self.repo_root / "clearer-engineering" / "scripts" / "safety-gate.py"
        self.assertTrue(safety_gate_py.is_file(), f"safety-gate.py não encontrado: {safety_gate_py}")

        entries = [json.loads(line) for line in self.corpus_file.read_text(encoding="utf-8").splitlines() if line.strip()]
        command_entries = [e for e in entries if e.get("type") in ("command", "integration")]
        sample = command_entries[::20]  # 51 comandos
        self.assertGreaterEqual(len(sample), 50)

        clean_env = os.environ.copy()
        clean_env.pop("CLAUDECODE", None)
        clean_env.pop("CLAUDE_PROJECT_DIR", None)
        clean_env.pop("CLAUDE_PID", None)
        clean_env.pop("CEH_EXPLICIT_ENV", None)
        clean_env.pop("APP_ENV", None)

        subprocess_divergences: list[str] = []

        for idx, entry in enumerate(sample):
            cmd = entry["command"]
            env = entry.get("env", "development")
            target_dir = self.env_to_dir[env]

            engine_dec = evaluate(Request(command=cmd, cwd=target_dir))

            for host in ["antigravity", "claude_code", "muse"]:
                payload = build_synthetic_terminal_payload(host, cmd, target_dir)

                proc = subprocess.run(
                    [sys.executable, str(safety_gate_py)],
                    input=json.dumps(payload),
                    capture_output=True,
                    text=True,
                    cwd=str(target_dir),
                    env=clean_env,
                )

                stdout_text = proc.stdout.strip()
                out_json: dict[str, Any] = {}
                if stdout_text:
                    try:
                        out_json = json.loads(stdout_text)
                    except Exception as e:
                        subprocess_divergences.append(
                            f"Falha ao parsear JSON de saída em {host} para '{cmd}': {stdout_text} ({e})"
                        )
                        continue

                # Conferência de saída e exit code conforme o motor e a tabela
                if host == "antigravity":
                    if engine_dec.decision == "allow":
                        if out_json.get("decision") != "allow" or proc.returncode != 0:
                            subprocess_divergences.append(f"Subprocess Antigravity allow falhou em '{cmd}': {stdout_text} (exit {proc.returncode})")
                    else:
                        if out_json.get("decision") != "deny" or proc.returncode != 0:
                            subprocess_divergences.append(f"Subprocess Antigravity deny falhou em '{cmd}': {stdout_text} (exit {proc.returncode})")

                elif host == "claude_code":
                    if engine_dec.decision == "allow":
                        if out_json != {} or proc.returncode != 0:
                            subprocess_divergences.append(f"Subprocess Claude allow falhou em '{cmd}': {stdout_text} (exit {proc.returncode})")
                    elif engine_dec.decision == "deny":
                        hso = out_json.get("hookSpecificOutput", {})
                        if hso.get("permissionDecision") != "deny" or proc.returncode != 2:
                            subprocess_divergences.append(f"Subprocess Claude deny falhou em '{cmd}': {stdout_text} (exit {proc.returncode})")
                    elif engine_dec.decision == "ask":
                        hso = out_json.get("hookSpecificOutput", {})
                        if hso.get("permissionDecision") != "ask" or proc.returncode != 0:
                            subprocess_divergences.append(f"Subprocess Claude ask falhou em '{cmd}': {stdout_text} (exit {proc.returncode})")

                elif host == "muse":
                    if engine_dec.decision == "allow":
                        if out_json != {} or proc.returncode != 0:
                            subprocess_divergences.append(f"Subprocess Muse allow falhou em '{cmd}': {stdout_text} (exit {proc.returncode})")
                    else:
                        if out_json.get("decision") != "block" or proc.returncode != 0:
                            subprocess_divergences.append(f"Subprocess Muse block falhou em '{cmd}': {stdout_text} (exit {proc.returncode})")

        self.assertEqual(
            len(subprocess_divergences), 0,
            f"Divergência(s) encontrada(s) no caminho de produção (subprocesso):\n" + "\n".join(subprocess_divergences[:10])
        )

    def test_cross_host_conformance_file_tools(self):
        """
        Valida que ferramentas de escrita (write_to_file, Write, write_file) possuem a mesma
        decisão e conformidade de resposta para alvos protegidos em .ceh/ e arquivos comuns.
        """
        sandbox = self.repos["dev"]
        targets = [
            (".ceh/last-ci-run.json", "deny", "CERTIFICATE_INTEGRITY"),
            (".ceh/last-evals-run.json", "deny", "CERTIFICATE_INTEGRITY"),
            (".ceh/sub/cert.json", "deny", "CERTIFICATE_INTEGRITY"),
            ("src/index.ts", "allow", "GENERAL"),
            ("README.md", "allow", "GENERAL"),
        ]

        for target_rel, exp_dec, exp_uc in targets:
            # 1. Motor direto
            req_eng = Request(target_paths=[target_rel], cwd=sandbox)
            eng_dec = evaluate(req_eng)
            self.assertEqual(eng_dec.decision, exp_dec)
            self.assertEqual(eng_dec.use_case, exp_uc)

            # 2. Payloads para cada host
            p_agy = build_synthetic_write_payload("antigravity", target_rel, sandbox)
            p_claude = build_synthetic_write_payload("claude_code", target_rel, sandbox)
            p_muse = build_synthetic_write_payload("muse", target_rel, sandbox)

            for hname, p in [("antigravity", p_agy), ("claude_code", p_claude), ("muse", p_muse)]:
                adapter = find_adapter(p)
                self.assertIsNotNone(adapter, f"Adaptador para {hname} ausente")
                req = adapter.parse(p)
                dec = evaluate(req)
                resp, ec = adapter.render(dec, p)

                self.assertEqual(
                    dec.decision, exp_dec,
                    f"Decisão de escrita divergente em {hname} para {target_rel}: {dec.decision} != {exp_dec}"
                )
                self.assertEqual(
                    dec.use_case, exp_uc,
                    f"Use case de escrita divergente em {hname} para {target_rel}: {dec.use_case} != {exp_uc}"
                )

                if exp_dec == "allow":
                    if hname == "antigravity":
                        self.assertEqual(resp.get("decision"), "allow")
                        self.assertEqual(ec, 0)
                    elif hname == "claude_code":
                        self.assertEqual(resp, {})
                        self.assertEqual(ec, 0)
                    elif hname == "muse":
                        self.assertEqual(resp, {})
                        self.assertEqual(ec, 0)
                else:
                    if hname == "antigravity":
                        self.assertEqual(resp.get("decision"), "deny")
                        self.assertEqual(ec, 0)
                    elif hname == "claude_code":
                        self.assertEqual(resp.get("hookSpecificOutput", {}).get("permissionDecision"), "deny")
                        self.assertEqual(ec, 2)
                    elif hname == "muse":
                        self.assertEqual(resp.get("decision"), "block")
                        self.assertEqual(ec, 0)


if __name__ == "__main__":
    unittest.main()
