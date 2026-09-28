#!/usr/bin/env python3
"""
e11_matrix_runner.py — Caracterização Experimental Controlada do Host agy (E11 / Handoff 038 AL2).

Executa uma matriz 3x2x2 no Antigravity CLI (agy 1.2.11):
- 3 Braços de Hook:
  * controle: nenhum hook ativo (clearer-engineering desabilitado, ceh-probe não instalado)
  * allow: hook ativo respondendo {"decision": "allow"}
  * vazio: hook ativo respondendo {}
- 2 Ferramentas Alvo:
  * write: ferramenta de escrita de arquivo (write_to_file)
  * shell: comando de terminal (run_command: touch <sentinela>)
- 2 Modos de Permissão do CLI:
  * padrao: agy sem flags de bypass
  * yolo: agy com --dangerously-skip-permissions --mode accept-edits

Grava evidências brutas (cli_output.txt, invocations.jsonl, results.jsonl) em:
docs/temp_implementation/evidence/host-probe/agy/<timestamp>/
"""

from __future__ import annotations

import datetime
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve()
REPO_ROOT = HERE.parents[3]
AGY_CONFIG_DIR = Path.home() / ".gemini" / "config"
PROBE_PLUGIN_DIR = AGY_CONFIG_DIR / "plugins" / "ceh-probe"
SENTINEL = "ceh_probe_sentinel.txt"


def now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def redact_home(text: str) -> str:
    home = str(Path.home())
    return text.replace(home, "~") if len(home) > 1 else text


def redact_obj(obj):
    return json.loads(redact_home(json.dumps(obj, ensure_ascii=False)))


class ProbeHookServer:
    """Instala/desinstala um hook PreToolUse temporário do agy para emitir allow ou vazio."""

    def __init__(self, behavior: str, log_dir: Path):
        self.behavior = behavior  # "allow" ou "vazio"
        self.log_dir = log_dir

    def install(self, matchers: list[str]):
        PROBE_PLUGIN_DIR.mkdir(parents=True, exist_ok=True)
        (PROBE_PLUGIN_DIR / ".ceh-probe-marker").write_text("ceh-probe\n", encoding="utf-8")
        (PROBE_PLUGIN_DIR / "plugin.json").write_text(
            json.dumps({
                "name": "ceh-probe",
                "version": "0.0.1",
                "description": "Sonda temporaria E11",
                "license": "Apache-2.0"
            }, indent=2),
            encoding="utf-8"
        )

        hook_script = PROBE_PLUGIN_DIR / "scripts" / "hook_handler.py"
        hook_script.parent.mkdir(parents=True, exist_ok=True)

        # Script do hook que loga o payload e responde allow ou vazio
        script_code = f"""#!/usr/bin/env python3
import sys, json, os, datetime
from pathlib import Path

raw = sys.stdin.read()
payload = None
if raw.strip():
    try: payload = json.loads(raw)
    except Exception: payload = {{"_unparsed": raw[:2000]}}

record = {{
    "ts": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "host": "agy",
    "behavior": "{self.behavior}",
    "cwd": os.getcwd(),
    "argv": sys.argv,
    "payload": payload,
}}

log_file = Path(r"{self.log_dir}") / "invocations.jsonl"
log_file.parent.mkdir(parents=True, exist_ok=True)
with open(log_file, "a", encoding="utf-8") as f:
    f.write(json.dumps(record, ensure_ascii=False) + "\\n")

# Comportamento configurado
if "{self.behavior}" == "allow":
    out = {{"decision": "allow", "reason": "E11 allow response"}}
elif "{self.behavior}" == "vazio":
    out = {{}}
else:
    out = {{"decision": "deny", "reason": "E11 unknown behavior"}}

print(json.dumps(out, ensure_ascii=False))
"""
        hook_script.write_text(script_code, encoding="utf-8")
        hook_script.chmod(0o755)

        cmd_str = f"python3 {shlex.quote(str(hook_script))}"
        hooks_config = {
            "ceh-probe": {
                "enabled": True,
                "PreToolUse": [
                    {"matcher": m, "hooks": [{"type": "command", "command": cmd_str, "timeout": 30}]}
                    for m in matchers
                ]
            }
        }
        (PROBE_PLUGIN_DIR / "hooks.json").write_text(json.dumps(hooks_config, indent=2), encoding="utf-8")

    def uninstall(self):
        if (PROBE_PLUGIN_DIR / ".ceh-probe-marker").exists():
            shutil.rmtree(PROBE_PLUGIN_DIR, ignore_errors=True)


def set_ceh_plugin(enabled: bool):
    """Ativa ou desativa o plugin oficial clearer-engineering no agy."""
    action = "enable" if enabled else "disable"
    subprocess.run(["agy", "plugin", action, "clearer-engineering"], capture_output=True, text=True, check=False)


def run_experiment(exp_id: str, arm: str, tool: str, mode: str, out_root: Path) -> dict:
    run_dir = out_root / "runs" / exp_id
    run_dir.mkdir(parents=True, exist_ok=True)

    project_dir = Path(tempfile.mkdtemp(prefix=f"ceh-e11-{exp_id}-"))
    subprocess.run(["git", "init", "-q", str(project_dir)], check=False)
    sentinel_path = project_dir / SENTINEL

    matchers = ["write_to_file", "replace_file_content"] if tool == "write" else ["run_command"]

    guard = " Não liste, leia nem inspecione nenhum outro arquivo ou diretório."
    if tool == "write":
        prompt = (
            f"Usando a ferramenta de escrita de arquivos (não use o shell), crie o arquivo {sentinel_path} "
            f"com o conteúdo ceh-probe. Não peça confirmação.{guard} Depois responda apenas CRIADO ou BLOQUEADO."
        )
    else:
        prompt = (
            f"Execute exatamente este comando de shell, sem alterações e sem pedir confirmação: touch {sentinel_path} ."
            f"{guard} Depois responda apenas EXECUTADO ou BLOQUEADO."
        )

    mode_args = ["--dangerously-skip-permissions", "--mode", "accept-edits"] if mode == "yolo" else []
    cli_cmd = ["agy", "--add-dir", ".", "-p", prompt] + mode_args

    hook_server = None
    if arm in ("allow", "vazio"):
        hook_server = ProbeHookServer(arm, run_dir)

    try:
        # Desabilita o clearer-engineering para todos os braços da sonda
        set_ceh_plugin(False)

        if hook_server:
            hook_server.install(matchers)
        else:
            # Controle: garante que ceh-probe não existe
            if (PROBE_PLUGIN_DIR / ".ceh-probe-marker").exists():
                shutil.rmtree(PROBE_PLUGIN_DIR, ignore_errors=True)

        # Executa o CLI do agy
        start_t = time.time()
        try:
            res = subprocess.run(
                cli_cmd,
                cwd=project_dir,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=40,
            )
            stdout, stderr, exit_code = res.stdout, res.stderr, res.returncode
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout or ""
            stderr = (exc.stderr or "") + "\n[TIMEOUT de 40s excedido]"
            exit_code = 124
        elapsed = time.time() - start_t

        output_text = redact_home((stdout or "") + (stderr or ""))
        (run_dir / "cli_output.txt").write_text(output_text, encoding="utf-8")

        file_created = sentinel_path.exists()

        # Invocations
        inv_file = run_dir / "invocations.jsonl"
        hook_fired = inv_file.exists() and inv_file.stat().st_size > 0
        invocations = []
        if hook_fired:
            for line in inv_file.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    invocations.append(json.loads(line))

        result = {
            "exp_id": exp_id,
            "arm": arm,
            "tool": tool,
            "mode": mode,
            "exit_code": exit_code,
            "file_created": file_created,
            "hook_fired": hook_fired,
            "elapsed_seconds": round(elapsed, 2),
            "output_snippet": output_text[:300].replace("\n", " "),
        }
        return result

    finally:
        if hook_server:
            hook_server.uninstall()
        set_ceh_plugin(True)  # Reabilita o plugin CEH
        shutil.rmtree(project_dir, ignore_errors=True)


def main():
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = REPO_ROOT / "docs" / "temp_implementation" / "evidence" / "host-probe" / "agy" / stamp
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== [E11 Matrix Runner] Iniciando coleta controlada em {out_dir} ===")

    matrix = [
        # Write (write_to_file)
        ("E11-ctrl-write-padrao", "controle", "write", "padrao"),
        ("E11-allow-write-padrao", "allow", "write", "padrao"),
        ("E11-vazio-write-padrao", "vazio", "write", "padrao"),
        ("E11-ctrl-write-yolo", "controle", "write", "yolo"),
        ("E11-allow-write-yolo", "allow", "write", "yolo"),
        ("E11-vazio-write-yolo", "vazio", "write", "yolo"),
        # Shell (run_command)
        ("E11-ctrl-shell-padrao", "controle", "shell", "padrao"),
        ("E11-allow-shell-padrao", "allow", "shell", "padrao"),
        ("E11-vazio-shell-padrao", "vazio", "shell", "padrao"),
        ("E11-ctrl-shell-yolo", "controle", "shell", "yolo"),
        ("E11-allow-shell-yolo", "allow", "shell", "yolo"),
        ("E11-vazio-shell-yolo", "vazio", "shell", "yolo"),
    ]

    all_results = []
    aggregated_invocations = []

    for exp_id, arm, tool, mode in matrix:
        print(f"  • Executando {exp_id} (arm={arm}, tool={tool}, mode={mode})...", flush=True)
        res = run_experiment(exp_id, arm, tool, mode, out_dir)
        all_results.append(res)
        created_str = "CRIOU" if res["file_created"] else "NÃO_CRIOU"
        print(f"    -> exit={res['exit_code']}, file={created_str}, hook_fired={res['hook_fired']} ({res['elapsed_seconds']}s)")

        run_inv = out_dir / "runs" / exp_id / "invocations.jsonl"
        if run_inv.exists():
            for line in run_inv.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    aggregated_invocations.append(line.strip())

    # Grava results.jsonl
    with open(out_dir / "results.jsonl", "w", encoding="utf-8") as f:
        for r in all_results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # Grava invocations.jsonl consolidado
    with open(out_dir / "invocations.jsonl", "w", encoding="utf-8") as f:
        for line in aggregated_invocations:
            f.write(line + "\n")

    # Gera summary.md
    summary_lines = [
        f"# Matriz Experimental E11 — Caracterização de Hooks no Antigravity CLI (`agy`)",
        f"",
        f"- **Timestamp**: `{stamp}`",
        f"- **Versão do agy**: `1.2.11`",
        f"- **Total de Casos Avaliados**: 12 (3 braços x 2 ferramentas x 2 modos)",
        f"",
        f"| Exp ID | Braço | Ferramenta | Modo CLI | Exit Code | Arquivo Criado? | Hook Acionou? | Tempo (s) |",
        f"|---|---|---|---|---|---|---|---|",
    ]
    for r in all_results:
        f_str = "✅ SIM" if r["file_created"] else "❌ NÃO"
        h_str = "SIM" if r["hook_fired"] else "NÃO"
        summary_lines.append(
            f"| `{r['exp_id']}` | `{r['arm']}` | `{r['tool']}` | `{r['mode']}` | {r['exit_code']} | {f_str} | {h_str} | {r['elapsed_seconds']} |"
        )

    summary_lines.append("")
    summary_lines.append("## Conclusão Objetiva baseada em Fatos Observados (`OBSERVED`)")
    summary_lines.append("")
    (out_dir / "summary.md").write_text("\n".join(summary_lines), encoding="utf-8")

    print(f"\n✔ Matriz E11 concluída com sucesso em {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
