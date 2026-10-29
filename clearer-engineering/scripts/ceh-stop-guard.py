#!/usr/bin/env python3
# ==============================================================================
# ceh-stop-guard.py — Stop Hook de Fechamento Epistêmico (CEH / PROTOCOLO.md)
# ==============================================================================
"""
Intercepta o encerramento do agente (evento Stop do Antigravity 2.0 / CLI).
Garante de forma determinística que tarefas de engenharia que tocaram o git
ou arquivos de trabalho não encerrem sem apresentar o Response Contract formal
ou justificativa explícita de evidência OBSERVED.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict


def _check_uncommitted_changes(cwd: Path) -> bool:
    """Verifica de forma rápida e silenciosa se há alterações no git do workspace."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(cwd), "status", "--porcelain"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=3,
        )
        return bool(proc.stdout.strip())
    except Exception:
        return False


def evaluate_stop(payload: Dict[str, Any]) -> Dict[str, str]:
    """
    Avalia se a parada deve ser permitida ou se deve exigir o Response Contract.
    """
    termination_reason = payload.get("terminationReason", "")
    
    # Se parou por erro, cancelamento do usuário ou limite de tokens, permitir saída imediata
    if termination_reason in ("ERROR", "USER_CANCELED", "MAX_TOKEN_BUDGET_EXCEEDED"):
        return {"decision": "allow"}

    workspaces = payload.get("workspacePaths", [])
    cwd = Path(workspaces[0]) if workspaces else Path.cwd()

    # 1. Verifica se houve modificações ativas no workspace
    has_changes = _check_uncommitted_changes(cwd)

    # 2. Se não houve modificações no git (apenas leitura ou conversa efêmera), liberar
    if not has_changes:
        return {"decision": "allow"}

    # 3. Se houve modificação de código/arquivos, verificar se a última entrada continha o contrato
    last_user_input = payload.get("lastUserInput", "").lower()
    transcript_path = payload.get("transcriptPath")
    has_contract_in_transcript = False

    if transcript_path and os.path.isfile(transcript_path):
        try:
            # Lê as últimas 10 linhas do transcript para verificar a emissão do contrato
            with open(transcript_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
                tail = "".join(lines[-15:])
                if "Response Contract" in tail or "Resultado:" in tail or "OBSERVED:" in tail:
                    has_contract_in_transcript = True
        except Exception:
            pass

    # Se já tem o contrato ou o usuário pediu explicitamente para ignorar
    if has_contract_in_transcript or "sem contrato" in last_user_input:
        return {"decision": "allow"}

    # Caso contrário, instruir o agente a emitir o contrato de evidências antes de fechar o turno
    return {
        "decision": "continue",
        "reason": (
            "CEH Stop Gate: Foram detectadas alterações em arquivos no workspace, "
            "mas o encerramento da resposta não incluiu o Response Contract auditável exigido pelo protocolo CLEARER.\n"
            "Por favor, apresente o bloco final de fechamento contendo: Resultado, Evidências (OBSERVED / INFERRED / UNKNOWN) "
            "e Nível de Confiança antes de finalizar o turno."
        ),
    }


def main():
    try:
        raw_input = sys.stdin.read()
        if not raw_input.strip():
            print(json.dumps({"decision": "allow"}))
            return

        payload = json.loads(raw_input)
        result = evaluate_stop(payload)
        print(json.dumps(result, ensure_ascii=False))
    except Exception:
        # Fail-safe permissivo no hook de stop para nunca travar a IDE em caso de erro interno
        print(json.dumps({"decision": "allow"}))


if __name__ == "__main__":
    main()
