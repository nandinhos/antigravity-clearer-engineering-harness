#!/usr/bin/env python3
# ==============================================================================
# package.py — Multi-Host Package Generator for CLEARER Engineering Harness (CEH)
# PR-16: Uma única fonte versionada gerando pacotes para Antigravity, Muse e Claude Code
# ==============================================================================
"""
Empacotador por host a partir de uma fonte canônica versionada.
Gera pacotes isolados e autônomos para:
  - antigravity: plugin global para Google Antigravity (com hooks.json e plugin.json)
  - muse: plugin compatível com Muse Code (com .muse-plugin/plugin.json e manifest.json)
  - claude-code: configuração de hooks e scripts para Claude Code (.claude/settings.json)

Garante determinismo estrito de empacotamento (mesmo conteúdo e hashes reproduzíveis).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Caminho raiz do repositório
REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = REPO_ROOT / "clearer-engineering"

SUPPORTED_HOSTS = ["antigravity", "muse", "claude-code"]

# Arquivos core que devem ser copiados para qualquer host
CORE_FILES: List[str] = [
    "safety-gate.py",
    "hook_context.py",
]

CORE_DIRS: List[str] = [
    "ceh_core",
    "adapters",
]


def _normalize_permissions(path: Path, is_executable: bool = False) -> None:
    mode = 0o755 if is_executable else 0o644
    os.chmod(path, mode)


def _copy_file_deterministic(src: Path, dst: Path, is_executable: bool = False) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    content = src.read_bytes()
    dst.write_bytes(content)
    _normalize_permissions(dst, is_executable)


def _copy_dir_deterministic(src_dir: Path, dst_dir: Path, exclude_patterns: Tuple[str, ...] = ("__pycache__", ".pyc", ".pyo", ".DS_Store")) -> None:
    dst_dir.mkdir(parents=True, exist_ok=True)
    for root, dirs, files in os.walk(src_dir):
        # Ordenação determinística de travessia
        dirs.sort()
        files.sort()
        rel_root = Path(root).relative_to(src_dir)
        target_root = dst_dir / rel_root
        target_root.mkdir(parents=True, exist_ok=True)

        for f in files:
            if any(pat in f for pat in exclude_patterns):
                continue
            src_file = Path(root) / f
            dst_file = target_root / f
            is_exec = src_file.name.endswith((".sh", ".py")) and (os.stat(src_file).st_mode & 0o111 != 0)
            _copy_file_deterministic(src_file, dst_file, is_exec)


def _write_json_deterministic(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    formatted = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    path.write_text(formatted, encoding="utf-8")
    _normalize_permissions(path, False)


def package_antigravity(out_dir: Path) -> None:
    """Empacota o plugin completo para Google Antigravity."""
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Copiar manifestos e metadados
    for f in ["plugin.json", "hooks.json", "README.md", "README_PT.md"]:
        src = SOURCE_DIR / f
        if src.is_file():
            _copy_file_deterministic(src, out_dir / f)

    # 2. Copiar diretórios de regras, perfis, agentes, config, skills, tests
    for d in ["agents", "config", "profiles", "rules", "skills", "tests"]:
        src_d = SOURCE_DIR / d
        if src_d.is_dir():
            _copy_dir_deterministic(src_d, out_dir / d)

    # 3. Copiar scripts (incluindo safety-gate.py, hook_context.py, ceh_core/, adapters/)
    scripts_src = SOURCE_DIR / "scripts"
    scripts_dst = out_dir / "scripts"
    _copy_dir_deterministic(scripts_src, scripts_dst)


def package_muse(out_dir: Path) -> None:
    """Empacota o plugin para Muse Code a partir da estrutura observada em E1b/E15."""
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Manifesto de plugin nativo (.muse-plugin/plugin.json e manifest.json)
    manifest_data = {
        "capabilities": {
            "commands": [],
            "hooks": [
                {
                    "command": [
                        "python3",
                        "hooks/safety-gate.py"
                    ],
                    "event": "PreToolUse",
                    "id": "safety-gate",
                    "statusMessage": "CEH Safety Gate (PreToolUse)",
                    "timeoutMs": 10000
                }
            ],
            "mcpServers": [],
            "reminders": [],
            "skills": []
        },
        "compat": {
            "manifestDir": ".muse-plugin",
            "source": "native"
        },
        "description": "CLEARER Engineering Harness (CEH) PreToolUse Safety Gate for Muse",
        "displayName": "CLEARER Muse Harness",
        "name": "clearer-muse",
        "schemaVersion": 1,
        "version": "1.4.1"
    }

    _write_json_deterministic(out_dir / ".muse-plugin" / "plugin.json", manifest_data)
    _write_json_deterministic(out_dir / "manifest.json", manifest_data)

    # 2. Hooks directory: safety-gate.py, hook_context.py, ceh_core/, adapters/
    hooks_dst = out_dir / "hooks"
    hooks_dst.mkdir(parents=True, exist_ok=True)

    scripts_src = SOURCE_DIR / "scripts"
    for core_file in CORE_FILES:
        _copy_file_deterministic(scripts_src / core_file, hooks_dst / core_file, is_executable=True)

    for core_dir in CORE_DIRS:
        _copy_dir_deterministic(scripts_src / core_dir, hooks_dst / core_dir)

    # 3. Documentação
    readme_content = "# CLEARER Engineering Harness (CEH) — Plugin para Muse Code\n\nPacote gerado deterministicamente a partir da fonte canonica do CEH.\n"
    (out_dir / "README.md").write_text(readme_content, encoding="utf-8")
    _normalize_permissions(out_dir / "README.md", False)


def package_claude_code(out_dir: Path) -> None:
    """Empacota a configuração e scripts para Claude Code conforme observado no Handoff 005."""
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Configuração de hooks em .claude/settings.json
    settings_data = {
        "hooks": {
            "PreToolUse": [
                {
                    "hooks": [
                        {
                            "command": "python3 scripts/safety-gate.py",
                            "timeout": 15,
                            "type": "command"
                        }
                    ],
                    "matcher": "Bash"
                },
                {
                    "hooks": [
                        {
                            "command": "python3 scripts/safety-gate.py",
                            "timeout": 15,
                            "type": "command"
                        }
                    ],
                    "matcher": "Write|Edit"
                }
            ]
        }
    }

    _write_json_deterministic(out_dir / ".claude" / "settings.json", settings_data)

    # 2. Scripts directory: safety-gate.py, hook_context.py, ceh_core/, adapters/
    scripts_dst = out_dir / "scripts"
    scripts_dst.mkdir(parents=True, exist_ok=True)

    scripts_src = SOURCE_DIR / "scripts"
    for core_file in CORE_FILES:
        _copy_file_deterministic(scripts_src / core_file, scripts_dst / core_file, is_executable=True)

    for core_dir in CORE_DIRS:
        _copy_dir_deterministic(scripts_src / core_dir, scripts_dst / core_dir)

    # 3. Documentação
    readme_content = "# CLEARER Engineering Harness (CEH) — Pacote para Claude Code\n\nPacote gerado deterministicamente a partir da fonte canonica do CEH.\n"
    (out_dir / "README.md").write_text(readme_content, encoding="utf-8")
    _normalize_permissions(out_dir / "README.md", False)


def calculate_package_hash(pkg_dir: Path) -> Tuple[str, Dict[str, str]]:
    """Calcula hashes SHA-256 de todos os arquivos do pacote em ordem lexicográfica estrita."""
    file_hashes: Dict[str, str] = {}
    hasher = hashlib.sha256()

    for root, dirs, files in os.walk(pkg_dir):
        dirs.sort()
        files.sort()
        for f in files:
            p = Path(root) / f
            rel = p.relative_to(pkg_dir).as_posix()
            content = p.read_bytes()
            f_hash = hashlib.sha256(content).hexdigest()
            file_hashes[rel] = f_hash
            hasher.update(f"{rel}:{f_hash}\n".encode("utf-8"))

    return hasher.hexdigest(), file_hashes


def package_host(host: str, out_dir: Path) -> Tuple[str, int]:
    """Executa o empacotamento para o host informado."""
    if host == "antigravity":
        package_antigravity(out_dir)
    elif host == "muse":
        package_muse(out_dir)
    elif host in ("claude-code", "claude"):
        package_claude_code(out_dir)
    else:
        raise ValueError(f"Host '{host}' nao suportado. Opcoes: {SUPPORTED_HOSTS}")

    pkg_hash, files = calculate_package_hash(out_dir)
    return pkg_hash, len(files)


def main() -> int:
    parser = argparse.ArgumentParser(description="CEH Multi-Host Deterministic Package Generator")
    parser.add_argument("--host", choices=SUPPORTED_HOSTS + ["claude"], help="Host alvo a empacotar")
    parser.add_argument("--out", required=True, help="Diretório de destino do pacote")
    parser.add_argument("--all", action="store_true", help="Gera pacotes para todos os hosts em subdiretórios de --out")
    parser.add_argument("--json", action="store_true", help="Emite sumário em JSON")

    args = parser.parse_args()
    out_base = Path(args.out).resolve()

    if args.all:
        results = {}
        for h in SUPPORTED_HOSTS:
            host_out = out_base / h
            if host_out.exists():
                shutil.rmtree(host_out)
            pkg_hash, count = package_host(h, host_out)
            results[h] = {"hash": pkg_hash, "file_count": count, "out_dir": str(host_out)}

        if args.json:
            print(json.dumps(results, indent=2, sort_keys=True))
        else:
            print(f"✔ Empacotados todos os {len(SUPPORTED_HOSTS)} hosts com sucesso em: {out_base}")
            for h, info in results.items():
                print(f"  • {h}: {info['file_count']} arquivos, hash={info['hash'][:16]}...")
        return 0

    if not args.host:
        parser.error("Informe --host <host> ou utilize --all.")

    target_host = "claude-code" if args.host == "claude" else args.host
    if out_base.exists():
        shutil.rmtree(out_base)

    pkg_hash, count = package_host(target_host, out_base)

    if args.json:
        print(json.dumps({"host": target_host, "hash": pkg_hash, "file_count": count, "out_dir": str(out_base)}, indent=2))
    else:
        print(f"✔ Pacote '{target_host}' gerado com sucesso em: {out_base}")
        print(f"  • Total de arquivos: {count}")
        print(f"  • Hash SHA-256 do pacote: {pkg_hash}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
