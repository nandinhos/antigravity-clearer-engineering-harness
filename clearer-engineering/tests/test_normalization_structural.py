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

# Exceções estritas e justificadas para chamadas a shlex.split fora de normalize.py (D01 / PR-QA-D2).
# Restritas ao call-site/contexto de função específico (não liberam o arquivo inteiro):
# Chave: (arquivo, função_ou_escopo)
# Valor: dict com teto máximo de chamadas permitidas (max_calls) e justificativa formal
SHLEX_EXCEPTIONS = {
    ("rules.py", "is_cert_tampering"): {
        "max_calls": 1,
        "justification": "G9 / AL1: captura de ValueError com mensagem de erro dedicada para fail-closed de certificado.",
    }
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
        """Chamadas a shlex.split são restritas a normalize.py ou ao call-site is_cert_tampering (D01 / PR-QA-D2)."""
        violations = []
        observed_call_counts: dict[tuple[str, str], int] = {}

        class ShlexCallVisitor(ast.NodeVisitor):
            def __init__(self, filename: str):
                self.filename = filename
                self.current_function: str | None = None
                self.calls: list[tuple[int, str | None, str]] = []

            def visit_FunctionDef(self, node: ast.FunctionDef):
                prev = self.current_function
                self.current_function = node.name
                self.generic_visit(node)
                self.current_function = prev

            def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
                prev = self.current_function
                self.current_function = node.name
                self.generic_visit(node)
                self.current_function = prev

            def visit_Call(self, node: ast.Call):
                is_shlex_split = False
                if isinstance(node.func, ast.Attribute) and node.func.attr == "split":
                    if isinstance(node.func.value, ast.Name) and node.func.value.id == "shlex":
                        is_shlex_split = True
                elif isinstance(node.func, ast.Name) and node.func.id == "shlex_split":
                    is_shlex_split = True

                if is_shlex_split:
                    repr_str = "shlex.split(...)"
                    if hasattr(ast, "unparse"):
                        try:
                            repr_str = ast.unparse(node)
                        except Exception:
                            pass
                    self.calls.append((node.lineno, self.current_function, repr_str))
                self.generic_visit(node)

        for py_file in sorted(CORE_DIR.glob("*.py")):
            if py_file.name in ("__init__.py", "normalize.py"):
                continue

            content = py_file.read_text(encoding="utf-8")
            try:
                tree = ast.parse(content, filename=str(py_file))
            except SyntaxError as e:
                self.fail(f"Erro de sintaxe em {py_file.name}: {e}")

            visitor = ShlexCallVisitor(py_file.name)
            visitor.visit(tree)

            for lineno, func_name, call_repr in visitor.calls:
                site_key = (py_file.name, func_name or "<module>")
                if site_key in SHLEX_EXCEPTIONS:
                    observed_call_counts[site_key] = observed_call_counts.get(site_key, 0) + 1
                    max_allowed = SHLEX_EXCEPTIONS[site_key]["max_calls"]
                    if observed_call_counts[site_key] > max_allowed:
                        violations.append(
                            f"{py_file.name}:{lineno} excede o limite de chamadas ({observed_call_counts[site_key]} > {max_allowed}) "
                            f"para shlex.split na função '{func_name or '<module>'}': {call_repr}"
                        )
                else:
                    violations.append(
                        f"{py_file.name}:{lineno} invoca shlex.split fora do módulo canônico e sem exceção de call-site: "
                        f"função '{func_name or '<module>'}': {call_repr}"
                    )

        # Garante que nenhuma exceção declarada virou órfã
        for site_key, spec in SHLEX_EXCEPTIONS.items():
            if site_key not in observed_call_counts:
                violations.append(
                    f"Exceção órfã {site_key}: chamada autorizada a shlex.split não foi encontrada no AST."
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
