#!/usr/bin/env python3
import subprocess
import json
import tempfile
import shutil
from pathlib import Path

repo = Path("/home/nandodev/projects/clearer-engineering-harness")
evidence_dir = repo / "docs/temp_implementation/evidence"
evidence_dir.mkdir(parents=True, exist_ok=True)

uninstall_script = repo / "uninstall.sh"
install_script = repo / "install.sh"

tmp_dir = Path(tempfile.mkdtemp(prefix="ceh_r3_fixture_"))
home_dir = tmp_dir / "home"

plugin_dir = home_dir / ".gemini/config/plugins/clearer-engineering"
agent_dir = home_dir / ".gemini/config/agents/clearer-harness"
plugin_dir.mkdir(parents=True, exist_ok=True)
agent_dir.mkdir(parents=True, exist_ok=True)

(plugin_dir / "sentinel").write_text("plugin sentinel\n")
(agent_dir / "sentinel").write_text("agent sentinel\n")

# Extrair bloco de aliases do install.sh
install_content = install_script.read_text().splitlines()
# Linhas 203 a 213 (1-indexed: 202 a 213 em 0-indexed)
alias_block = "\n".join(install_content[202:213]) + "\n"
bashrc = home_dir / ".bashrc"
bashrc.write_text(alias_block)

before_bashrc = bashrc.read_text()

# Executar desinstalador com HOME temporário
proc = subprocess.run(
    ["bash", str(uninstall_script)],
    env={**subprocess.os.environ, "HOME": str(home_dir)},
    capture_output=True, text=True
)

after_bashrc = bashrc.read_text()
plugin_exists = plugin_dir.exists()
agent_exists = agent_dir.exists()

remaining_aliases = [line.strip() for line in after_bashrc.splitlines() if line.strip().startswith("alias")]

evidence = {
    "exit_code": proc.returncode,
    "stdout": proc.stdout,
    "stderr": proc.stderr,
    "bashrc_before": before_bashrc,
    "bashrc_after": after_bashrc,
    "plugin_dir_exists": plugin_exists,
    "agent_dir_exists": agent_exists,
    "remaining_aliases": remaining_aliases
}

evidence_file = evidence_dir / "r3_uninstall_aliases_evidence.json"
evidence_file.write_text(json.dumps(evidence, indent=2))
print(f"R3 evidence saved to {evidence_file}")
print(f"Uninstall Exit Code: {proc.returncode}")
print(f"Plugin dir removed: {not plugin_exists}")
print(f"Agent dir removed: {not agent_exists}")
print(f"Remaining aliases count: {len(remaining_aliases)}")
print("Remaining aliases:")
for a in remaining_aliases:
    print(f"  {a}")

shutil.rmtree(tmp_dir)
