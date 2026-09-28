#!/usr/bin/env python3
"""
test_normalization_structural.py - Validação estrutural do Ponto Único de Normalização (PR-QA-D).

Garante formalmente que:
1. Funções de normalização (prefixo 'normalize_', 'strip_quotes', 'strip_all_quotes', 'resolve_long_options')
   são implementadas exclusivamente no módulo canônico 'ceh_core/normalize.py'.
2. Analisadores de segurança em 'ceh_core/' não implementam normalização própria nem duplicam lógica.
3. Usos de 'os.path.normpath' e 'posixpath.normpath' residem estritamente dentro de 'ceh_core/normalize.py'.
4. Usos de 'shlex.split' fora de 'normalize.py' são restritos a exceções documentadas e justificadas.
"""
from __future__ import annotations

import ast
import re
import sys
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_DIR.parent.parent
CORE_DIR = REPO_ROOT / "clearer-engineering" / "scripts" / "ceh_core"

NORMALIZATION_MODULE = CORE_DIR / "normalize.py"

# Nomes de funções reservadas à API única de normalização
NORMALIZATION_FUNCTION_NAMES = {
    "normalize_command_for_evaluation",
    "normalize_env",
    "normalize_path",
    "normalize_posix_path",
    "strip_quotes",
    "strip_all_quotes",
    "resolve_long_options",
    "expand_home_prefix",
    "tokenize_command",
}

# Exceções estritas e justificadas para shlex.split fora de normalize.py:
# - rules.py: captura proposital de ValueError para Fail-Closed por erro de sintaxe em cert_tampering (G9)
SHLEX_EXCEPTIONS = {
    "rules.py": "G9 / AL1: captura de ValueError com mensagem de erro dedicada para fail-closed de certificado."
}

# Exceções estritas para normpath fora de normalize.py: NENHUMA permitida em ceh_core
NORMPATH_EXCEPTIONS = set()


class TestNormalizationStructural(unittest.TestCase):
    def setUp(self):
        self.assertTrue(NORMALIZATION_MODULE.is_file(), f"Módulo {NORMALIZATION_MODULE} deve existir.")

    def test_normalization_functions_implemented_only_in_normalize_py(self):
        """Funções de normalização devem ser implementadas (def) apenas em ceh_core/normalize.py."""
        violations = []

        for py_file in sorted(CORE_DIR.glob("*.py")):
            if py_file.name == "__init__.py" or py_file.name == "normalize.py":
                continue

            content = py_file.read_text(encoding="utf-8")
            try:
                tree = ast.parse(content, filename=str(py_file))
            except SyntaxError as e:
                self.fail(f"Erro de sintaxe em {py_file.name}: {e}")

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Checa por nomes reservados
                    if node.name in NORMALIZATION_FUNCTION_NAMES:
                        violations.append(
                            f"{py_file.name}:{node.lineno} define função reservada '{node.name}' "
                            f"(deve ser importada de ceh_core.normalize)."
                        )
                    # Checa por qualquer nova função com prefixo 'normalize_'
                    elif node.name.startswith("normalize_"):
                        violations.append(
                            f"{py_file.name}:{node.lineno} define nova função de normalização '{node.name}' "
                            f"fora de normalize.py."
                        )

        self.assertFalse(
            violations,
            "Violações de ponto único de normalização encontradas:\n" + "\n".join(f"  • {v}" for v in violations)
        )

    def test_normpath_usage_restricted_to_normalize_py(self):
        """Chamadas a os.path.normpath ou posixpath.normpath são restritas a ceh_core/normalize.py."""
        violations = []

        for py_file in sorted(CORE_DIR.glob("*.py")):
            if py_file.name in ("__init__.py", "normalize.py"):
                continue
            if py_file.name in NORMPATH_EXCEPTIONS:
                continue

            content = py_file.read_text(encoding="utf-8")
            for lineno, line in enumerate(content.splitlines(), start=1):
                # Ignora comentários
                clean = line.split("#")[0]
                if re.search(r"\b(?:os\.path|posixpath)\.normpath\b", clean):
                    violations.append(
                        f"{py_file.name}:{lineno} invoca normpath diretamente: {line.strip()}"
                    )

        self.assertFalse(
            violations,
            "Usos diretos de normpath encontrados fora de normalize.py:\n" + "\n".join(f"  • {v}" for v in violations)
        )

    def test_shlex_split_restricted_to_normalize_py_or_justified_exceptions(self):
        """Chamadas a shlex.split são restritas a normalize.py ou exceções justificadas."""
        violations = []

        for py_file in sorted(CORE_DIR.glob("*.py")):
            if py_file.name in ("__init__.py", "normalize.py"):
                continue

            content = py_file.read_text(encoding="utf-8")
            for lineno, line in enumerate(content.splitlines(), start=1):
                clean = line.split("#")[0]
                if re.search(r"\bshlex\.split\b", clean):
                    if py_file.name not in SHLEX_EXCEPTIONS:
                        violations.append(
                            f"{py_file.name}:{lineno} invoca shlex.split sem justificativa no contrato: {line.strip()}"
                        )

        self.assertFalse(
            violations,
            "Usos não autorizados de shlex.split encontrados fora de normalize.py:\n" + "\n".join(f"  • {v}" for v in violations)
        )

    def test_all_normalization_api_symbols_exported(self):
        """Todos os símbolos da API canônica de normalização devem existir em ceh_core.normalize."""
        import importlib
        sys.path.insert(0, str(REPO_ROOT / "clearer-engineering" / "scripts"))
        try:
            norm_mod = importlib.import_module("ceh_core.normalize")
        except ImportError as e:
            self.fail(f"Não foi possível importar ceh_core.normalize: {e}")

        missing = []
        for name in NORMALIZATION_FUNCTION_NAMES:
            if not hasattr(norm_mod, name) or not callable(getattr(norm_mod, name)):
                missing.append(name)

        self.assertFalse(
            missing,
            f"Símbolos ausentes ou não executáveis em ceh_core.normalize: {missing}"
        )


if __name__ == "__main__":
    unittest.main()
