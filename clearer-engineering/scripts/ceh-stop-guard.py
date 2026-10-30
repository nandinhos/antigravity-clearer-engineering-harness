#!/usr/bin/env python3
# ==============================================================================
# ceh-stop-guard.py — Stop Hook de Fechamento Epistêmico (CEH / PROTOCOLO.md)
# ==============================================================================
"""
Intercepta o encerramento do agente (evento Stop do Antigravity 2.0 / CLI).
Garante de forma determinística que tarefas de feature ativamente registradas
em .ceh/feature.json não encerrem sem apresentar o Response Contract formal
ou justificativa explícita de evidência OBSERVED no término real da feature,
enquanto libera comandos intermediários do dia a dia sem fricção.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional

FEATURE_FILE_REL = Path(".ceh") / "feature.json"

COMPLETION_KEYWORDS = (
    "finalizar feature",
    "concluir feature",
    "encerrar feature",
    "entregar feature",
    "fechar feature",
    "terminar feature",
    "finish feature",
    "complete feature",
)


def _get_feature_file(cwd: Path) -> Path:
    return cwd / FEATURE_FILE_REL


def _load_feature_state(cwd: Path) -> Optional[Dict[str, Any]]:
    feat_path = _get_feature_file(cwd)
    if not feat_path.is_file():
        return None
    try:
        with open(feat_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else None
    except Exception:
        return None


def _save_feature_state(cwd: Path, data: Dict[str, Any]) -> bool:
    feat_path = _get_feature_file(cwd)
    try:
        feat_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = feat_path.with_suffix(".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, feat_path)
        return True
    except Exception:
        return False


def _is_completion_requested(last_user_input: str) -> bool:
    lowered = last_user_input.lower().strip()
    return any(keyword in lowered for keyword in COMPLETION_KEYWORDS)


def _has_contract_in_transcript(transcript_path: Optional[str]) -> bool:
    if not transcript_path or not os.path.isfile(transcript_path):
        return False
    try:
        with open(transcript_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
            tail = "".join(lines[-20:])
            # Reconhece blocos canônicos de Response Contract do CEH
            if any(marker in tail for marker in ("Response Contract", "Resultado:", "OBSERVED:", "CONFIDENCE:")):
                return True
    except Exception:
        pass
    return False


def evaluate_stop(payload: Dict[str, Any]) -> Dict[str, str]:
    """
    Avalia se a parada do agente deve ser permitida ou se deve exigir o Response Contract.
    Regra de Ouro: Comandos intermediários e sessões sem feature ativa são liberados (allow).
    A exigência do contrato ocorre exclusivamente no término real da feature (.ceh/feature.json).
    """
    termination_reason = payload.get("terminationReason", "")
    
    # Se parou por erro, cancelamento do usuário ou limite de tokens, permitir saída imediata
    if termination_reason in ("ERROR", "USER_CANCELED", "MAX_TOKEN_BUDGET_EXCEEDED"):
        return {"decision": "allow"}

    workspaces = payload.get("workspacePaths", [])
    cwd = Path(workspaces[0]) if workspaces else Path.cwd()

    # 1. Verifica se existe arquivo de estado de feature ativa (.ceh/feature.json)
    state = _load_feature_state(cwd)
    if not state:
        # Sem feature registrada: comandos avulsos e rotinas do dia a dia encerram livremente
        return {"decision": "allow"}

    status = state.get("status", "in_progress")

    # 2. Se a feature já foi concluída anteriormente, liberar
    if status == "completed":
        return {"decision": "allow"}

    last_user_input = payload.get("lastUserInput", "")
    transcript_path = payload.get("transcriptPath")

    # 3. Determina se esta invocação representa o término da feature
    is_finishing = (status == "completing") or _is_completion_requested(last_user_input)

    # Se a feature ainda está em andamento (in_progress) e o usuário não pediu encerramento explícito,
    # permite paradas intermediárias normais sem forçar relatório a cada comando
    if not is_finishing:
        return {"decision": "allow"}

    # 4. No término da feature: valida se o Response Contract já foi emitido
    has_contract = _has_contract_in_transcript(transcript_path)
    user_bypassed = "sem contrato" in last_user_input.lower()

    if has_contract or user_bypassed:
        # Marca a feature como concluída com timestamp
        state["status"] = "completed"
        state["completed_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        _save_feature_state(cwd, state)
        return {"decision": "allow"}

    # 5. Caso contrário, exige o Response Contract formal no fechamento real da feature
    feature_name = state.get("name") or state.get("slug") or "ativa"
    return {
        "decision": "continue",
        "reason": (
            f"CEH Stop Gate: A feature '{feature_name}' está em fase de encerramento, "
            "mas a resposta final não incluiu o Response Contract auditável exigido pelo protocolo CLEARER.\n"
            "Por favor, apresente o bloco final de fechamento contendo: Resultado, Evidências (OBSERVED / INFERRED / UNKNOWN) "
            "e Nível de Confiança antes de concluir a feature."
        ),
    }


def _cli_start(cwd: Path, name: str) -> int:
    state = {
        "name": name,
        "status": "in_progress",
        "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "requires_contract": True,
    }
    if _save_feature_state(cwd, state):
        print(f"[CEH Feature] Feature '{name}' registrada com status 'in_progress' em .ceh/feature.json")
        return 0
    print("[CEH Feature] Erro ao gravar .ceh/feature.json", file=sys.stderr)
    return 1


def _cli_complete(cwd: Path) -> int:
    state = _load_feature_state(cwd)
    if not state:
        print("[CEH Feature] Nenhuma feature ativa encontrada em .ceh/feature.json", file=sys.stderr)
        return 1
    state["status"] = "completing"
    _save_feature_state(cwd, state)
    print(f"[CEH Feature] Feature '{state.get('name')}' marcada como 'completing'. Stop Guard exigirá Response Contract.")
    return 0


def _cli_status(cwd: Path) -> int:
    state = _load_feature_state(cwd)
    if not state:
        print("[CEH Feature] Nenhuma feature ativa no momento.")
        return 0
    print(json.dumps(state, indent=2, ensure_ascii=False))
    return 0


def _cli_cancel(cwd: Path) -> int:
    feat_path = _get_feature_file(cwd)
    if feat_path.is_file():
        feat_path.unlink()
        print("[CEH Feature] Feature cancelada. .ceh/feature.json removido.")
        return 0
    print("[CEH Feature] Nenhuma feature ativa para cancelar.")
    return 0


def main():
    # Suporte a subcomandos CLI manuais (start, complete, status, cancel)
    if len(sys.argv) > 1 and sys.argv[1] in ("start", "complete", "status", "cancel"):
        cwd = Path.cwd()
        subcmd = sys.argv[1]
        if subcmd == "start":
            name = sys.argv[2] if len(sys.argv) > 2 else "feature-unnamed"
            sys.exit(_cli_start(cwd, name))
        elif subcmd == "complete":
            sys.exit(_cli_complete(cwd))
        elif subcmd == "status":
            sys.exit(_cli_status(cwd))
        elif subcmd == "cancel":
            sys.exit(_cli_cancel(cwd))

    # Operação padrão como Hook JSON (stdin -> stdout)
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
