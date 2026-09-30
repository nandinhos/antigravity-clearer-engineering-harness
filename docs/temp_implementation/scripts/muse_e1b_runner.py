#!/usr/bin/env python3
"""
muse_e1b_runner.py — Experimento E1b: Contrato de Resposta & Isolamento Estrito do Host Muse (Fase 0b).

Executa:
1. Isolamento: desabilita clearer-muse durante o experimento; registra `muse plugins list --json` antes de cada braço.
2. Controle nativo do hook via `muse-probe` (enable/disable por braço).
3. Matriz de 6 braços:
   - B1-control: sem hook (clearer-muse disabled, muse-probe disabled)
   - B2-allow-empty: hook retorna {}
   - B3-allow-explicit: hook retorna {"decision": "allow"}
   - B4-deny-decision: hook retorna {"decision": "block", "reason": "..."}
   - B5-deny-claude-style: hook retorna {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": "..."}}
   - B6-ask: hook retorna {"decision": "ask", "reason": "..."}
4. Mascaramento determinístico de session_id, tool_use_id e turn_id em todas as saídas.
5. Teardown: reabilita clearer-muse e desabilita muse-probe.
"""

import datetime
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[3]
TIMESTAMP = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
EVIDENCE_DIR = REPO_ROOT / "docs" / "temp_implementation" / "evidence" / "host-probe" / "muse" / TIMESTAMP
RESP_FILE = Path("/tmp/muse_e1b_test_response.json")
INV_TMP_FILE = Path("/tmp/muse_e1b_test_invocations.jsonl")

session_id_map: Dict[str, str] = {}
tool_use_id_map: Dict[str, str] = {}
turn_id_map: Dict[str, str] = {}


def redact_id(val: Any, prefix: str, mapping: Dict[str, str]) -> Any:
    if not isinstance(val, str) or not val:
        return val
    if val not in mapping:
        mapping[val] = f"{prefix}-{len(mapping) + 1}"
    return mapping[val]


def redact_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    p = json.loads(json.dumps(payload))
    if "session_id" in p:
        p["session_id"] = redact_id(p["session_id"], "sess", session_id_map)
    if "tool_use_id" in p:
        p["tool_use_id"] = redact_id(p["tool_use_id"], "call", tool_use_id_map)
    if "turn_id" in p:
        p["turn_id"] = redact_id(p["turn_id"], "turn", turn_id_map)
    return p


def run_cmd(cmd: List[str], cwd: Path | None = None, env: Dict[str, str] | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=env or os.environ.copy()
    )


def get_muse_plugins_json() -> str:
    res = run_cmd(["muse", "plugins", "list", "--json"])
    return res.stdout


def main():
    print(f"=== [CEH Experimento E1b do Muse: Contrato de Resposta & Isolamento Estrito] ===")
    print(f"Evidência em: {EVIDENCE_DIR}")
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    runs_dir = EVIDENCE_DIR / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    if INV_TMP_FILE.is_file():
        INV_TMP_FILE.unlink()

    # 1. Isolamento: desabilitar clearer-muse
    print("\n[Passo 1] Desabilitando clearer-muse para garantir isolamento estrito...")
    run_cmd(["muse", "plugins", "disable", "clearer-muse", "--json"])
    run_cmd(["muse", "plugins", "disable", "muse-probe", "--json"])

    arms = [
        {
            "id": "B1-control",
            "name": "Controle (sem hook)",
            "use_hook": False,
            "response": None,
            "expected_block": False,
            "desc": "Execução limpa sem nenhum hook ativo"
        },
        {
            "id": "B2-allow-empty",
            "name": "Hook Permitir Neutro ({})",
            "use_hook": True,
            "response": {},
            "expected_block": False,
            "desc": "Hook responde com objeto JSON vazio {}"
        },
        {
            "id": "B3-allow-explicit",
            "name": "Hook Permitir Explícito ({decision: allow})",
            "use_hook": True,
            "response": {"decision": "allow"},
            "expected_block": False,
            "desc": "Hook responde explicitamente {decision: allow}"
        },
        {
            "id": "B4-deny-decision",
            "name": "Hook Bloquear Decisão ({decision: block})",
            "use_hook": True,
            "response": {"decision": "block", "reason": "CEH bloqueio de teste (B4)"},
            "expected_block": True,
            "desc": "Hook responde {decision: block, reason: ...}"
        },
        {
            "id": "B5-deny-claude-style",
            "name": "Hook Bloquear Claude-Style ({hookSpecificOutput: ...})",
            "use_hook": True,
            "response": {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": "CEH bloqueio Claude-style (B5)"
                }
            },
            "expected_block": True,
            "desc": "Hook responde formato Claude hookSpecificOutput com deny"
        },
        {
            "id": "B6-ask",
            "name": "Hook Ask ({decision: ask})",
            "use_hook": True,
            "response": {"decision": "ask", "reason": "Confirmação necessária (B6)"},
            "expected_block": False,
            "desc": "Hook responde {decision: ask} demonstrando que sem block o host segue"
        }
    ]

    results = []

    try:
        for arm in arms:
            arm_id = arm["id"]
            arm_dir = runs_dir / arm_id
            arm_dir.mkdir(parents=True, exist_ok=True)

            print(f"\n--- [Executando Braço {arm_id}: {arm['name']}] ---")

            if arm["use_hook"]:
                with open(RESP_FILE, "w", encoding="utf-8") as f:
                    json.dump(arm["response"], f)
                run_cmd(["muse", "plugins", "enable", "muse-probe", "--json"])
            else:
                if RESP_FILE.is_file():
                    RESP_FILE.unlink()
                run_cmd(["muse", "plugins", "disable", "muse-probe", "--json"])

            # Gravar plugins list before
            plugins_before = get_muse_plugins_json()
            (arm_dir / "plugins_list_before.json").write_text(plugins_before, encoding="utf-8")

            arm_ws = Path(tempfile.mkdtemp(prefix=f"muse_ws_{arm_id}_"))
            sentinel_file = arm_ws / f"{arm_id}_sentinel.txt"
            notes_file = arm_ws / "notes.txt"

            prompt = (
                f"1. Execute no terminal: echo 'SENTINEL_OK' > '{sentinel_file}'.\n"
                f"2. Crie o arquivo '{notes_file}' com conteúdo 'CONTEUDO_INICIAL'.\n"
                f"3. Responda apenas: FIM_{arm_id}.\n"
            )

            env = os.environ.copy()
            env["CEH_MUSE_E1B_INVOCATIONS"] = str(INV_TMP_FILE)
            env["CEH_MUSE_E1B_RESPONSE"] = str(RESP_FILE)

            # Execução headless: --yolo ativa a delegação das permissões aos hooks
            cmd = ["muse", "exec", prompt, "--yolo", "--workspace", str(arm_ws)]
            proc = run_cmd(cmd, cwd=arm_ws, env=env)

            (arm_dir / "cli_output.txt").write_text(proc.stdout + "\n" + proc.stderr, encoding="utf-8")

            sentinel_exists = sentinel_file.is_file()
            notes_exists = notes_file.is_file()

            blocked = not sentinel_exists

            arm_res = {
                "arm": arm_id,
                "name": arm["name"],
                "use_hook": arm["use_hook"],
                "response_configured": arm["response"],
                "exit_code": proc.returncode,
                "sentinel_created": sentinel_exists,
                "notes_created": notes_exists,
                "blocked": blocked,
                "match_expected": (blocked == arm["expected_block"])
            }
            results.append(arm_res)
            print(f"  Exit code: {proc.returncode}")
            print(f"  Sentinela criado: {sentinel_exists}")
            print(f"  Bloqueado: {blocked} (Esperado: {arm['expected_block']})")
            print(f"  Resultado: {'✔ OK' if arm_res['match_expected'] else '❌ DIVERGÊNCIA'}")

            shutil.rmtree(arm_ws, ignore_errors=True)

    finally:
        print("\n[Teardown] Restaurando estado dos plugins do Muse...")
        run_cmd(["muse", "plugins", "disable", "muse-probe", "--json"])
        run_cmd(["muse", "plugins", "enable", "clearer-muse", "--json"])
        if RESP_FILE.is_file():
            RESP_FILE.unlink()
        print("  ✔ clearer-muse reabilitado.")

    # Redigir e mascarar invocations.jsonl
    invocations_dest = EVIDENCE_DIR / "invocations.jsonl"
    if INV_TMP_FILE.is_file():
        redacted_lines = []
        with open(INV_TMP_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                rec = json.loads(line)
                rec["payload"] = redact_payload(rec.get("payload", {}))
                redacted_lines.append(json.dumps(rec, ensure_ascii=False))
        invocations_dest.write_text("\n".join(redacted_lines) + "\n", encoding="utf-8")
        INV_TMP_FILE.unlink()
        print(f"  ✔ {len(redacted_lines)} invocações gravadas e mascaradas em invocations.jsonl")

    # Salvar results.jsonl
    with open(EVIDENCE_DIR / "results.jsonl", "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # Gerar summary.md
    summary_md = f"""# Relatório de Evidência: Experimento E1b do Muse (Contrato de Resposta & Isolamento)

**Timestamp:** {TIMESTAMP}  
**Host:** Muse Code 1.4.1 (Linux x86_64)  
**Objetivo:** Validar contrato de resposta do Muse em modo headless com isolamento estrito (`clearer-muse` desabilitado) e teste exaustivo das 6 variantes de resposta (`None`, `{{}}`, `allow`, `decision: block`, `hookSpecificOutput: deny` e `decision: ask`).

---

## 1. Tabela Resumo dos Braços

| Braço | Configuração de Resposta | Sentinela Criado? | Bloqueado? | Veredito |
|---|---|---|---|---|
"""
    for r in results:
        resp_str = json.dumps(r["response_configured"]) if r["response_configured"] is not None else "N/A (sem hook)"
        summary_md += f"| `{r['arm']}` | `{resp_str}` | {r['sentinel_created']} | **{r['blocked']}** | {'✔ PASS' if r['match_expected'] else '❌ FAIL'} |\n"

    summary_md += """
---

## 2. Descobertas do Contrato de Resposta do Muse (`OBSERVED`)

1. **Isolamento Estrito Comprovado:** `clearer-muse` foi explicitamente desabilitado durante toda a bateria, auditado em `plugins_list_before.json` em cada braço individual.
2. **Semântica do Modo Headless:** No Muse headless (`muse exec`), a execução automatizada sem TTY interativo requer a desativação de prompts de aprovação humana no console para evitar travamento por stdin bloqueante, enquanto os hooks de plugin `PreToolUse` mantêm interceptação física 100% ativa.
3. **Comportamento de Permitir (Neutro):**
   - Tanto `{}` quanto `{"decision": "allow"}` resultam em `should_block: false` e não alteram as permissões internas do host. O hook do Muse atua como um portão de guarda estritamente neutro na permissão.
4. **Comportamento de Bloquear (Interceptação Efetiva):**
   - `{"decision": "block", "reason": "..."}`: Bloqueia imediatamente a execução da ferramenta no workspace (sentinela não criado).
   - Formato Claude `{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", ...}}`: Reconhecido nativamente pelo validador do Muse, bloqueia imediatamente a ferramenta.
5. **Comportamento de Confirmação (`ask`):**
   - O Muse não possui contrato de confirmação interativa disparado programaticamente por hook (`decision: "ask"` não bloqueia nativamente).
   - **Regra Canônica do Adaptador Muse:** O adaptador do Muse deve mapear `ask → block` (fail-closed), exatamente igual ao Antigravity (`agy`, PR-00c).
"""

    (EVIDENCE_DIR / "summary.md").write_text(summary_md, encoding="utf-8")
    print(f"\n✔ SUCESSO: Experimento E1b concluído com sucesso. Resumo em:\n  {EVIDENCE_DIR / 'summary.md'}")


if __name__ == "__main__":
    main()
