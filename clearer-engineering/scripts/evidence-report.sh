#!/usr/bin/env bash
# ==============================================================================
# evidence-report.sh - Relatório canônico de evidências do CEH (Response Contract)
# ==============================================================================
# Wrapper estável de evidence_report.py: RESULT e CONFIDENCE são calculados a
# partir de git, do certificado de testes e das provas informadas; nunca declarados.
set -euo pipefail
exec python3 "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/evidence_report.py" "$@"
