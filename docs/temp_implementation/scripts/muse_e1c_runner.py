#!/usr/bin/env python3
"""
muse_e1c_runner.py — Experimento E1c: Teste da Resposta de Reserva do Shim ({"decision": "deny"}) no Muse.
Referência: Handoff 077 (Ressalva BH2).

Testa empiricamente se o formato de reserva do shim do CEH safety-gate.py:
  {"decision": "deny", "reason": "..."} com exit code 0
bloqueia ou não uma execução de ferramenta no runtime do Muse Code 1.4.1.

Grava os artefatos brutos em:
  docs/temp_implementation/evidence/host-probe/muse/e1c/
  - runner.py (cópia deste script)
  - manifest.json (manifesto do plugin de sonda)
  - cli_output.txt (saída bruta do CLI do Muse)
  - invocations.jsonl (payloads interceptados)
  - summary.md (relatório formal de evidência)
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
EVIDENCE_DIR = REPO_ROOT / "docs" / "temp_implementation" / "evidence" / "host-probe" / "muse" / "e1c"


def redact_home(text: str) -> str:
    home = str(Path.home())
    return text.replace(home, "~") if len(home) > 1 else text


def main() -> int:
    print("=== [Experimento E1c: Caracterização de 'decision: deny' no Muse] ===")
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    muse_bin = shutil.which("muse")
    if not muse_bin:
        print("ERRO: Binário 'muse' não encontrado no PATH.", file=sys.stderr)
        return 1

    tmp_base = Path(tempfile.mkdtemp(prefix="ceh_e1c_muse_")).resolve()
    plugin_dir = tmp_base / "e1c_plugin"
    work_dir = tmp_base / "workspace"
    work_dir.mkdir(parents=True, exist_ok=True)

    plugin_id = "ceh-probe-e1c"
    hook_id = "probe-hook-e1c"

    invocations_file = EVIDENCE_DIR / "invocations.jsonl"
    if invocations_file.exists():
        invocations_file.unlink()

    try:
        # 1. Configura a sonda de plugin do Muse
        manifest_dir = plugin_dir / ".muse-plugin"
        manifest_dir.mkdir(parents=True, exist_ok=True)
        hooks_dir = plugin_dir / "hooks"
        hooks_dir.mkdir(parents=True, exist_ok=True)

        manifest = {
            "name": plugin_id,
            "version": "0.1.0",
            "displayName": "CEH E1c Probe",
            "description": "Sonda E1c para teste de decision: deny no Muse",
            "schemaVersion": 1,
            "compat": {
                "manifestDir": ".muse-plugin",
                "source": "native"
            },
            "capabilities": {
                "commands": [],
                "hooks": [
                    {
                        "id": hook_id,
                        "event": "PreToolUse",
                        "command": [sys.executable, str(plugin_dir / "hooks" / "probe.py")],
                        "timeoutMs": 5000,
                        "statusMessage": "Sonda CEH E1c (decision: deny)"
                    }
                ],
                "skills": []
            }
        }
        (manifest_dir / "plugin.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        (EVIDENCE_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

        # Hook script que responde exatamente {"decision": "deny", ...} com exit 0
        hook_code = f"""#!/usr/bin/env python3
import sys, os, json, datetime

raw_input = sys.stdin.read()
payload = None
if raw_input.strip():
    try:
        payload = json.loads(raw_input)
    except Exception:
        payload = {{"_raw": raw_input[:2000]}}

record = {{
    "ts": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "host": "muse",
    "behavior": "deny-decision",
    "payload": payload
}}

with open("{str(invocations_file)}", "a", encoding="utf-8") as f:
    f.write(json.dumps(record, ensure_ascii=False) + "\\n")

# Formato exato do shim de reserva do CEH:
response = {{
    "decision": "deny",
    "reason": "CEH Safety Gate (reserva do shim): acao bloqueada preventivamente (E1c)."
}}
print(json.dumps(response))
sys.exit(0)
"""
        probe_py = hooks_dir / "probe.py"
        probe_py.write_text(hook_code, encoding="utf-8")
        probe_py.chmod(0o755)

        # 2. Instala e aprova a sonda
        print("Instalando e aprovando plugin de sonda no Muse...")
        subprocess.run(["muse", "plugins", "remove", plugin_id, "--json"], capture_output=True, text=True)
        res_inst = subprocess.run(["muse", "plugins", "install", str(plugin_dir), "--scope", "user", "--json"], capture_output=True, text=True)
        if res_inst.returncode != 0:
            print(f"ERRO: muse plugins install failed: {res_inst.stderr}", file=sys.stderr)
            return 1

        res_appr = subprocess.run(["muse", "plugins", "approve", f"plugin:{plugin_id}:hook:{hook_id}", "--json"], capture_output=True, text=True)
        if res_appr.returncode != 0:
            print(f"ERRO: muse plugins approve failed: {res_appr.stderr}", file=sys.stderr)
            return 1
        print("✔ Plugin de sonda instalado e hook aprovado.")

        # 3. Executa teste no workspace temporário confinado
        sentinel_file = work_dir / "sentinel_e1c.txt"
        prompt = f"Execute no terminal: echo 'E1C_EXECUTED' > '{sentinel_file}' e termine."

        print("Executando sessão do Muse com a sonda ativa...")
        t0 = time.time()
        proc = subprocess.run(
            ["muse", "exec", prompt, "--yolo", "--workspace", str(work_dir)],
            capture_output=True,
            text=True,
            cwd=str(work_dir),
            timeout=120,
        )
        duration = round(time.time() - t0, 2)
        cli_out = redact_home(proc.stdout + "\n" + proc.stderr)
        (EVIDENCE_DIR / "cli_output.txt").write_text(cli_out, encoding="utf-8")

        # 4. Avalia resultado
        sentinel_created = sentinel_file.is_file()
        blocked = not sentinel_created
        hook_intervened = "CEH Safety Gate (reserva do shim)" in cli_out or "deny" in cli_out.lower() or "block" in cli_out.lower() or "bloque" in cli_out.lower()

        print(f"\n--- [Resultado Observado] ---")
        print(f"Arquivo sentinela criado? {sentinel_created}")
        print(f"Ação bloqueada pelo Muse? {blocked}")
        print(f"Intervenção do hook visível? {hook_intervened}")
        print(f"Duração: {duration}s")

        # 5. Gera Relatório summary.md
        summary_md = f"""# Relatório de Evidência: Experimento E1c (Reserva do Shim no Muse)

**Data/Hora:** {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}  
**Host:** Muse Code 1.4.1 (1.4.1-R4503.1)  
**Referência:** Handoff 077 (Ressalva BH2)  
**Formato Testado:** `{{"decision": "deny", "reason": "..."}}` com **exit code 0**  

---

## 1. Tabela Comparativa de Bloqueios no Muse (E1b + E1c)

| Experimento | Formato Retornado pelo Hook | Exit Code | Sentinela Criado? | Bloqueado pelo Muse? | Comportamento Observado |
|---|---|---|---|---|---|
| **E1b (B4)** | `{{"decision": "block", "reason": "..."}}` | 0 | False | **SIM** | Bloqueio nativo do Muse |
| **E1b (B5)** | `{{"hookSpecificOutput": {{"permissionDecision": "deny", ...}}}}` | 0 | False | **SIM** | Reconhecido pelo parser Claude do Muse |
| **E1c (Novo)** | `{{"decision": "deny", "reason": "..."}}` | 0 | {sentinel_created} | **{'SIM' if blocked else 'NÃO'}** | {'Bloqueou com sucesso no runtime do Muse' if blocked else 'FALHA: Nao bloqueou; executou a ferramenta'} |

## 2. Diagnóstico Técnico

- **Sentinela criado:** `{sentinel_created}`
- **Bloqueio efetivo:** `{'BLOQUEOU COM SUCESSO' if blocked else 'FALHOU EM BLOQUEAR (fail-open)'}`
- **Saída bruta do CLI:** Arquivo [`cli_output.txt`](./cli_output.txt)
- **Payloads registrados:** Arquivo [`invocations.jsonl`](./invocations.jsonl)

## 3. Conclusão e Veredito para o Handoff 077 / BH2

{'O formato de reserva do shim `{"decision": "deny"}` com exit 0 BLOQUEIA efetivamente no Muse Code 1.4.1. A ressalva BH2 está sanada empiricamente com o formato atual.' if blocked else 'O formato `{"decision": "deny"}` NÃO bloqueia no Muse. O shim precisará adotar formato universal compatível nos 3 hosts conforme deliberação da revisão.'}
"""
        (EVIDENCE_DIR / "summary.md").write_text(summary_md, encoding="utf-8")
        shutil.copy2(__file__, EVIDENCE_DIR / "runner.py")

        print(f"\n✔ [E1C CONCLUÍDO] Artefatos salvos em: {EVIDENCE_DIR}")
        return 0

    finally:
        print("Limpando plugin de sonda do Muse...")
        subprocess.run(["muse", "plugins", "remove", plugin_id, "--json"], capture_output=True, text=True)
        shutil.rmtree(tmp_base, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
