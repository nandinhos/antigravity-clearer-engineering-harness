#!/usr/bin/env python3
import subprocess
import json
import platform
from pathlib import Path

repo = Path("/home/nandodev/projects/clearer-engineering-harness")
evidence_dir = repo / "docs/temp_implementation/evidence"
evidence_dir.mkdir(parents=True, exist_ok=True)

install_sh = repo / "install.sh"
uninstall_sh = repo / "uninstall.sh"

sed_version = subprocess.check_output(["sed", "--version"], text=True).splitlines()[0]
system_os = platform.system()

evidence = {
    "system_os": system_os,
    "sed_version": sed_version,
    "install_sed_invocations": [
        "line 222: sed -i '/alias ceh-help=/i alias ceh-evals=...' \"$rc_file\"",
        "line 226: sed -i '/alias ceh-help=/i alias ceh-monitor=...' \"$rc_file\""
    ],
    "uninstall_sed_invocations": [
        "line 30: sed -i '/# === CLEARER Engineering Harness (CEH) ===/,+3d' \"$rc_file\"",
        "line 31: sed -i '/alias agy-ceh=/d' \"$rc_file\"",
        "line 32: sed -i '/alias agy-ceh-yolo=/d' \"$rc_file\"",
        "line 33: sed -i '/alias ceh=/d' \"$rc_file\""
    ],
    "analysis": "No Linux com GNU sed, sed -i sem sufixo funciona. No macOS/BSD, sed -i sem extensão requer obrigatoriamente um argumento extra vazio ('') como sufixo de backup (ex: sed -i '' '...'). Sem esse argumento, o BSD sed interpreta o comando sed como a extensão do arquivo de backup e falha com erro de sintaxe. No ambiente local Linux (Ubuntu), a execução do GNU sed é suportada, tornando a reprodução direta de falha em runtime inconclusiva localmente sem um host macOS/FreeBSD, mas a incompatibilidade estática do GNU sed vs BSD sed é universalmente conhecida.",
    "status": "Inconclusivo (Requer host macOS/BSD para reprodução física de falha em tempo de execução)"
}

evidence_file = evidence_dir / "r9_sed_portability_evidence.json"
evidence_file.write_text(json.dumps(evidence, indent=2))
print(f"R9 evidence saved to {evidence_file}")
print(f"OS: {system_os} | SED: {sed_version} | Status: {evidence['status']}")
