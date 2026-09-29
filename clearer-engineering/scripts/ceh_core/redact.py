"""
ceh_core/redact.py - Redação preventiva de segredos, tokens e caminhos absolutos de home.

Módulo de segurança para o Conselho de Seniores (PR-21).
Garante que nenhum caminho de host ou token sensível vaze para modelos externos
ou para os artefatos prompt_*.txt e contexto_avaliado.txt.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

# Padrões de segredos, tokens e credenciais
SECRET_PATTERNS = [
    # Git Tokens (GitHub Personal Access Tokens, OAuth, Fine-grained PATs)
    (re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"), "[REDACTED_GIT_TOKEN]"),
    # AWS Access Key IDs
    (re.compile(r"\b(?:AKIA|ABIA|ACCA|ASIA)[0-9A-Z]{16}\b"), "[REDACTED_AWS_KEY]"),
    # Google API Keys
    (re.compile(r"\bAIza[0-9A-Za-z\-_]{30,45}\b"), "[REDACTED_GOOGLE_KEY]"),
    # OpenAI & Anthropic API Keys
    (re.compile(r"\bsk-(?:ant-)?(?:live-)?[a-zA-Z0-9_\-]{20,}\b"), "[REDACTED_API_KEY]"),
    # Authorization Headers (Bearer, Basic, etc.)
    (re.compile(r"(?i)\b(authorization:\s*(?:bearer|basic)\s+)[^\r\n\s]+"), r"\1[REDACTED_AUTH_TOKEN]"),
    # Private Key PEM blocks
    (re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----[\s\S]*?-----END (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"), "[REDACTED_PRIVATE_KEY]"),
]

# Caminhos absolutos de sistema (Linux e macOS)
HOME_PATHS_REGEX = re.compile(r"/(?:home|Users)/[a-zA-Z0-9_\-\.]+")


def redact_paths(text: str, custom_home: str | None = None) -> str:
    """Substitui caminhos absolutos de home de usuário (/home/<u>/ ou /Users/<u>/) por ~."""
    if not text:
        return ""

    result = text
    # Se um diretório de home específico for informado ou obtido do ambiente
    home_dir = custom_home or os.environ.get("HOME")
    if home_dir and len(home_dir) > 1 and home_dir in result:
        result = result.replace(home_dir, "~")

    # Substituição genérica de qualquer /home/<user> ou /Users/<user>
    result = HOME_PATHS_REGEX.sub("~", result)
    return result


def redact_secrets(text: str) -> str:
    """Mascara padrões de credenciais, chaves de API e tokens conhecidos."""
    if not text:
        return ""

    result = text
    for pattern, replacement in SECRET_PATTERNS:
        result = pattern.sub(replacement, result)
    return result


def redact_payload(text: str, custom_home: str | None = None) -> str:
    """Executa a redação integral: segredos/tokens e caminhos absolutos de home."""
    if not text:
        return ""
    text_no_secrets = redact_secrets(text)
    return redact_paths(text_no_secrets, custom_home=custom_home)


def main() -> None:
    """CLI para uso em pipelines e shell scripts."""
    if "--help" in sys.argv or "-h" in sys.argv:
        print("Uso: python3 -m ceh_core.redact < arquivo_entrada")
        sys.exit(0)

    input_text = sys.stdin.read()
    output_text = redact_payload(input_text)
    sys.stdout.write(output_text)


if __name__ == "__main__":
    main()
