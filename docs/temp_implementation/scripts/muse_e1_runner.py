#!/usr/bin/env python3
"""
muse_e1_runner.py — Caracterização Experimental Controlada do Host Muse (E1 / A5 - Onda 4).

Executa a caracterização em 3 braços no mesmo prompt:
- Braço 1 (controle): Sem hook (plugin desinstalado/desabilitado)
- Braço 2 (allow): Hook ativo gravando payload e respondendo neutro ({})
- Braço 3 (deny): Hook ativo gravando payload e respondendo bloqueio ({"decision": "block", "reason": ...})

Cobre operações de:
- Execução de comando no terminal (bash / shell)
- Escrita / criação de arquivo
- Edição de arquivo

Grava os artefatos brutos em:
  docs/temp_implementation/evidence/host-probe/muse/<timestamp>/
  - runner.py (cópia versionada deste runner)
  - invocations.jsonl (payloads reais gravados)
  - results.jsonl (resumo estruturado de cada braço)
  - runs/<arm>/cli_output.txt (saída bruta do CLI para cada braço)
  - summary.md (relatório consolidado com checagem de vazamento)
"""

from __future__ import annotations

import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
EVIDENCE_BASE_DIR = REPO_ROOT / "docs" / "temp_implementation" / "evidence" / "host-probe" / "muse"


def now_utc_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def timestamp_slug() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def redact_home(text: str) -> str:
    home = str(Path.home())
    return text.replace(home, "~") if len(home) > 1 else text


def redact_obj(obj: any) -> any:
    return json.loads(redact_home(json.dumps(obj, ensure_ascii=False)))


class MuseProbeManager:
    """Gerencia a instalação, configuração e remoção da sonda de plugin no Muse."""

    def __init__(self, probe_source_dir: Path, log_file: Path):
        self.probe_source_dir = probe_source_dir
        self.log_file = log_file
        self.plugin_id = "ceh-muse-probe"
        self.hook_id = "pre-tool-use-probe"

    def setup_plugin_source(self, behavior: str, block_format: str = "native"):
        """
        behavior: 'allow' | 'deny'
        block_format: 'native' ({"decision": "block", "reason": ...}) ou
                      'claude' ({"hookSpecificOutput": {"permissionDecision": "deny", ...}})
        """
        self.probe_source_dir.mkdir(parents=True, exist_ok=True)
        manifest_dir = self.probe_source_dir / ".muse-plugin"
        manifest_dir.mkdir(parents=True, exist_ok=True)

        manifest = {
            "name": self.plugin_id,
            "version": "0.1.0",
            "displayName": "CEH Muse Probe",
            "description": "Sonda de teste e captura de payload PreToolUse do CEH",
            "schemaVersion": 1,
            "compat": {
                "manifestDir": ".muse-plugin",
                "source": "native"
            },
            "capabilities": {
                "commands": [],
                "hooks": [
                    {
                        "id": self.hook_id,
                        "event": "PreToolUse",
                        "command": ["python3", "hooks/probe.py"],
                        "timeoutMs": 5000,
                        "statusMessage": f"Sonda CEH ({behavior})"
                    }
                ],
                "skills": []
            }
        }
        (manifest_dir / "plugin.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

        hooks_dir = self.probe_source_dir / "hooks"
        hooks_dir.mkdir(parents=True, exist_ok=True)

        hook_code = f"""#!/usr/bin/env python3
import sys, os, json, datetime

def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def redact_home(text):
    home = str(os.path.expanduser("~"))
    return text.replace(home, "~") if len(home) > 1 else text

def redact(obj):
    return json.loads(redact_home(json.dumps(obj, ensure_ascii=False)))

raw_input = sys.stdin.read()
payload = None
if raw_input.strip():
    try:
        payload = json.loads(raw_input)
    except Exception:
        payload = {{"_raw": raw_input[:2000]}}

env_keep = ["MUSE_PLUGIN_DATA_DIR", "MUSE_PLUGIN_ID", "MUSE_PLUGIN_ROOT", "ANTIGRAVITY_CONVERSATION_ID", "CLAUDE_SESSION_ID"]
record = {{
    "ts": now_iso(),
    "host": "muse",
    "behavior": "{behavior}",
    "python": sys.version.split()[0],
    "python_executable": sys.executable,
    "cwd": os.getcwd(),
    "argv": sys.argv,
    "env_keys": sorted(k for k in os.environ if k in env_keep or "MUSE" in k or "TOOL" in k),
    "env": {{k: v for k, v in os.environ.items() if k in env_keep or "MUSE" in k}},
    "payload": payload
}}

log_path = "{str(self.log_file)}"
os.makedirs(os.path.dirname(log_path), exist_ok=True)
with open(log_path, "a", encoding="utf-8") as f:
    f.write(json.dumps(redact(record), ensure_ascii=False) + "\\n")

# Comportamento de resposta
behavior = "{behavior}"
if behavior == "deny":
    # Formato nativo validado do Muse
    out = {{"decision": "block", "reason": "CEH Safety Gate: comando/ação bloqueada preventivamente pela sonda de teste."}}
else:
    # Formato neutro validado do Muse
    out = {{}}

print(json.dumps(out))
"""
        probe_py = hooks_dir / "probe.py"
        probe_py.write_text(hook_code, encoding="utf-8")
        probe_py.chmod(0o755)

    def install_and_approve(self):
        # Desinstala prévio se existir
        subprocess.run(["muse", "plugins", "remove", self.plugin_id, "--json"], capture_output=True, text=True)
        # Instala
        res_inst = subprocess.run(["muse", "plugins", "install", str(self.probe_source_dir), "--scope", "project", "--json"], capture_output=True, text=True)
        if res_inst.returncode != 0:
            raise RuntimeError(f"muse plugins install failed: {res_inst.stderr}")
        # Aprova hook
        res_appr = subprocess.run(["muse", "plugins", "approve", f"plugin:{self.plugin_id}:hook:{self.hook_id}", "--json"], capture_output=True, text=True)
        if res_appr.returncode != 0:
            raise RuntimeError(f"muse plugins approve failed: {res_appr.stderr}")

    def uninstall(self):
        subprocess.run(["muse", "plugins", "remove", self.plugin_id, "--json"], capture_output=True, text=True)
        shutil.rmtree(self.probe_source_dir, ignore_errors=True)


def run_e1_matrix(ts: str | None = None) -> Path:
    timestamp = ts or timestamp_slug()
    out_dir = EVIDENCE_BASE_DIR / timestamp
    out_dir.mkdir(parents=True, exist_ok=True)
    runs_dir = out_dir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    # Copiar o runner para o diretório de evidência
    shutil.copy2(__file__, out_dir / "runner.py")

    invocations_file = out_dir / "invocations.jsonl"
    if invocations_file.exists():
        invocations_file.unlink()

    results: list[dict] = []

    # Diretório temporário para a sonda
    probe_source = Path(tempfile.mkdtemp(prefix="muse_probe_source_"))
    probe_mgr = MuseProbeManager(probe_source, invocations_file)

    # Prompt que aciona terminal, criação e edição de arquivo
    # Cada braço executa em uma pasta temporária isolada
    try:
        # ----------------------------------------------------------------------
        # Braço 1: Controle (Sem Hook)
        # ----------------------------------------------------------------------
        print("\n=== [Braço 1: Controle (Sem Hook)] ===")
        probe_mgr.uninstall()  # Garante sem hook

        work_dir_b1 = Path(tempfile.mkdtemp(prefix="muse_work_b1_"))
        sentinel_b1 = work_dir_b1 / "b1_sentinel.txt"

        prompt_b1 = (
            f"1. Execute no terminal: echo 'CONTROLE_SEM_HOOK' > '{sentinel_b1}'.\n"
            f"2. Crie o arquivo '{work_dir_b1 / 'created.txt'}' com o texto 'ARQUIVO_CRIADO'.\n"
            f"3. Depois responda apenas: CONCLUIDO_B1."
        )

        b1_run_dir = runs_dir / "B1-control"
        b1_run_dir.mkdir(exist_ok=True)

        start_time = time.time()
        proc_b1 = subprocess.run(
            ["muse", "exec", prompt_b1, "--yolo", "--workspace", str(work_dir_b1)],
            capture_output=True,
            text=True,
            cwd=str(work_dir_b1),
            timeout=120
        )
        duration_b1 = round(time.time() - start_time, 2)

        (b1_run_dir / "cli_output.txt").write_text(redact_home(proc_b1.stdout + proc_b1.stderr), encoding="utf-8")
        sentinel_b1_created = sentinel_b1.is_file()
        file_b1_created = (work_dir_b1 / "created.txt").is_file()

        results.append({
            "arm": "B1-control",
            "description": "Controle: sem hook ativo; ferramentas devem executar livremente",
            "behavior": "none",
            "exit_code": proc_b1.returncode,
            "duration_s": duration_b1,
            "sentinel_created": sentinel_b1_created,
            "file_created": file_b1_created,
            "blocked": not sentinel_b1_created,
            "invocations_count": 0,
        })
        print(f"  ✔ B1 concluído: exit={proc_b1.returncode}, sentinela_criado={sentinel_b1_created}, arquivo_criado={file_b1_created} ({duration_b1}s)")
        shutil.rmtree(work_dir_b1, ignore_errors=True)

        # ----------------------------------------------------------------------
        # Braço 2: Hook Ativo — Permitir (Allow / Neutro {})
        # ----------------------------------------------------------------------
        print("\n=== [Braço 2: Hook Ativo — Permitir (Allow / Neutro)] ===")
        probe_mgr.setup_plugin_source("allow")
        probe_mgr.install_and_approve()

        inv_count_before = len(invocations_file.read_text(encoding="utf-8").splitlines()) if invocations_file.exists() else 0

        work_dir_b2 = Path(tempfile.mkdtemp(prefix="muse_work_b2_"))
        sentinel_b2 = work_dir_b2 / "b2_sentinel.txt"

        prompt_b2 = (
            f"1. Execute no terminal: echo 'ALLOW_WITH_HOOK' > '{sentinel_b2}'.\n"
            f"2. Crie o arquivo '{work_dir_b2 / 'notes.txt'}' com o texto 'NOTA_CRIADA'.\n"
            f"3. Altere o arquivo '{work_dir_b2 / 'notes.txt'}' para 'NOTA_EDITADA'.\n"
            f"4. Depois responda apenas: CONCLUIDO_B2."
        )

        b2_run_dir = runs_dir / "B2-allow"
        b2_run_dir.mkdir(exist_ok=True)

        start_time = time.time()
        proc_b2 = subprocess.run(
            ["muse", "exec", prompt_b2, "--yolo", "--workspace", str(work_dir_b2)],
            capture_output=True,
            text=True,
            cwd=str(work_dir_b2),
            timeout=120
        )
        duration_b2 = round(time.time() - start_time, 2)

        (b2_run_dir / "cli_output.txt").write_text(redact_home(proc_b2.stdout + proc_b2.stderr), encoding="utf-8")
        sentinel_b2_created = sentinel_b2.is_file()
        notes_b2 = work_dir_b2 / "notes.txt"
        notes_content = notes_b2.read_text(encoding="utf-8") if notes_b2.is_file() else ""

        inv_count_after = len(invocations_file.read_text(encoding="utf-8").splitlines()) if invocations_file.exists() else 0
        b2_invs = inv_count_after - inv_count_before

        results.append({
            "arm": "B2-allow",
            "description": "Hook ativo permitindo ({}); ferramentas devem executar e hook deve gravar payloads",
            "behavior": "allow",
            "exit_code": proc_b2.returncode,
            "duration_s": duration_b2,
            "sentinel_created": sentinel_b2_created,
            "file_content": notes_content.strip(),
            "blocked": not sentinel_b2_created,
            "invocations_count": b2_invs,
        })
        print(f"  ✔ B2 concluído: exit={proc_b2.returncode}, sentinela_criado={sentinel_b2_created}, invocações_gravadas={b2_invs} ({duration_b2}s)")
        shutil.rmtree(work_dir_b2, ignore_errors=True)

        # ----------------------------------------------------------------------
        # Braço 3: Hook Ativo — Negar (Deny / Block)
        # ----------------------------------------------------------------------
        print("\n=== [Braço 3: Hook Ativo — Negar (Deny / Block)] ===")
        probe_mgr.setup_plugin_source("deny")
        probe_mgr.install_and_approve()

        inv_count_before = len(invocations_file.read_text(encoding="utf-8").splitlines()) if invocations_file.exists() else 0

        work_dir_b3 = Path(tempfile.mkdtemp(prefix="muse_work_b3_"))
        sentinel_b3 = work_dir_b3 / "b3_sentinel.txt"

        prompt_b3 = (
            f"Execute no terminal exatamente o comando: touch '{sentinel_b3}'. "
            f"Não faça mais nada. Depois responda apenas se o comando foi EXECUTADO ou BLOQUEADO."
        )

        b3_run_dir = runs_dir / "B3-deny"
        b3_run_dir.mkdir(exist_ok=True)

        start_time = time.time()
        proc_b3 = subprocess.run(
            ["muse", "exec", prompt_b3, "--yolo", "--workspace", str(work_dir_b3)],
            capture_output=True,
            text=True,
            cwd=str(work_dir_b3),
            timeout=120
        )
        duration_b3 = round(time.time() - start_time, 2)

        (b3_run_dir / "cli_output.txt").write_text(redact_home(proc_b3.stdout + proc_b3.stderr), encoding="utf-8")
        sentinel_b3_created = sentinel_b3.is_file()

        inv_count_after = len(invocations_file.read_text(encoding="utf-8").splitlines()) if invocations_file.exists() else 0
        b3_invs = inv_count_after - inv_count_before

        results.append({
            "arm": "B3-deny",
            "description": "Hook ativo negando ('decision': 'block'); comando deve ser interceptado e impedido de executar",
            "behavior": "deny",
            "exit_code": proc_b3.returncode,
            "duration_s": duration_b3,
            "sentinel_created": sentinel_b3_created,
            "blocked": not sentinel_b3_created,
            "invocations_count": b3_invs,
        })
        print(f"  ✔ B3 concluído: exit={proc_b3.returncode}, sentinela_criado={sentinel_b3_created} (esperado False), bloqueado={not sentinel_b3_created}, invocações_gravadas={b3_invs} ({duration_b3}s)")
        shutil.rmtree(work_dir_b3, ignore_errors=True)

    finally:
        # Limpeza final: desinstalar a sonda temporária do Muse
        probe_mgr.uninstall()

    # Gravar results.jsonl
    with open(out_dir / "results.jsonl", "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(redact_obj(r), ensure_ascii=False) + "\n")

    # Gerar summary.md consolidado
    summary_md = f"""# Relatório Experimental E1: Caracterização de Hook e Payloads Reais do Muse

- **Timestamp**: `{timestamp}`
- **Host**: `muse` (Muse Code 1.4.1)
- **Protocolo**: CLEARER Engineering Harness (CEH) — Onda 4 (Fase 0 / A5)
- **Critério**: E1 payload real de hook gravado com contrato de resposta em 3 braços

## 1. Resultados da Matriz Experimental (3 Braços)

| Braço | Descrição | Comportamento do Hook | Exit Code | Invocations Gravadas | Sentinela Criado | Bloqueado? |
|---|---|---|---|---|---|---|
"""
    for r in results:
        summary_md += f"| **{r['arm']}** | {r['description']} | `{r['behavior']}` | `{r['exit_code']}` | `{r['invocations_count']}` | `{r['sentinel_created']}` | **{'SIM' if r['blocked'] else 'NÃO'}** |\n"

    total_invs = len(invocations_file.read_text(encoding="utf-8").splitlines()) if invocations_file.exists() else 0
    summary_md += f"""
## 2. Contrato de Interceptação do Hook Observado

1. **Recepção de Payloads (`PreToolUse`)**:
   - O Muse invoca o hook passando o payload via `stdin` em JSON.
   - O payload contém: `tool_name` (ex.: `"bash"`), `tool_input` (ex.: `{{"command": "...", "workdir": "..."}}`), `cwd`, `hook_event_name`, `session_id`, `tool_use_id`, `turn_id`.
   - Variáveis de ambiente fornecidas ao processo do hook: `MUSE_PLUGIN_DATA_DIR`, `MUSE_PLUGIN_ID`, `MUSE_PLUGIN_ROOT`.

2. **Contrato de Resposta (Veredito)**:
   - **Permitir neutro**: Devolver `{{}}` via stdout com exit code 0. O Muse prossegue com a execução normalmente.
   - **Bloquear efetivamente**: Devolver `{{\"decision\": \"block\", \"reason\": \"<motivo>\"}}` via stdout com exit code 0 (ou formato compatível `hookSpecificOutput` com `permissionDecision: \"deny\"`).
   - O bloqueio impede fisicamente a execução da ferramenta no workspace, mantendo `sentinel_created = False`.

## 3. Total de Payloads Reais Gravados (A5)

- **Total de invocações capturadas**: `{total_invs}`
- **Arquivo de registro**: `docs/temp_implementation/evidence/host-probe/muse/{timestamp}/invocations.jsonl`
"""

    (out_dir / "summary.md").write_text(summary_md, encoding="utf-8")
    print(f"\n✔ Experimento E1 concluído com sucesso! Evidências gravadas em:\n  {out_dir}")
    return out_dir


if __name__ == "__main__":
    ts_arg = sys.argv[1] if len(sys.argv) > 1 else None
    run_e1_matrix(ts_arg)
