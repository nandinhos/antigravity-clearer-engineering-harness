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


class NormalizationAstVisitor(ast.NodeVisitor):
    """Analisador de AST que resolve imports e rastreia chamadas a shlex.split e normpath por aliases (PR-QA-D3)."""

    def __init__(self, filename: str):
        self.filename = filename
        self.current_function: str | None = None
        self.module_aliases: dict[str, str] = {}
        self.callable_aliases: dict[str, str] = {}
        self.shlex_calls: list[tuple[int, str | None, str]] = []
        self.normpath_calls: list[tuple[int, str | None, str]] = []

    def collect_imports(self, tree: ast.AST) -> None:
        """Primeira passada: cataloga todos os imports e aliases do módulo."""
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.name
                    asname = alias.asname or name
                    if name in ("shlex", "posixpath", "ntpath", "os"):
                        self.module_aliases[asname] = name
                    elif name == "os.path":
                        self.module_aliases[asname] = "os.path"
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                for alias in node.names:
                    name = alias.name
                    asname = alias.asname or name
                    # from shlex import split [as ...]
                    if mod == "shlex" and name == "split":
                        self.callable_aliases[asname] = "shlex.split"
                    # from os.path / posixpath / ntpath import normpath [as ...]
                    elif mod in ("os.path", "posixpath", "ntpath") and name == "normpath":
                        self.callable_aliases[asname] = f"{mod}.normpath"
                    # from os import path [as ...]
                    elif mod == "os" and name == "path":
                        self.module_aliases[asname] = "os.path"

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

    def _unparse_call(self, node: ast.Call) -> str:
        if hasattr(ast, "unparse"):
            try:
                return ast.unparse(node)
            except Exception:
                pass
        return "call(...)"

    def is_shlex_split_call(self, node: ast.Call) -> bool:
        if isinstance(node.func, ast.Name):
            if self.callable_aliases.get(node.func.id) == "shlex.split":
                return True
            if node.func.id == "shlex_split":
                return True
        elif isinstance(node.func, ast.Attribute) and node.func.attr == "split":
            val = node.func.value
            if isinstance(val, ast.Name):
                resolved = self.module_aliases.get(val.id, val.id)
                if resolved == "shlex":
                    return True
        return False

    def is_normpath_call(self, node: ast.Call) -> bool:
        if isinstance(node.func, ast.Name):
            target = self.callable_aliases.get(node.func.id)
            if target and target.endswith(".normpath"):
                return True
            if node.func.id == "normpath":
                return True
        elif isinstance(node.func, ast.Attribute) and node.func.attr == "normpath":
            val = node.func.value
            if isinstance(val, ast.Name):
                resolved = self.module_aliases.get(val.id, val.id)
                if resolved in ("os.path", "posixpath", "ntpath", "path", "osp"):
                    return True
            elif isinstance(val, ast.Attribute) and val.attr == "path":
                root = val.value
                if isinstance(root, ast.Name):
                    resolved_root = self.module_aliases.get(root.id, root.id)
                    if resolved_root == "os":
                        return True
            # Qualquer invocação de atributo .normpath em módulos core
            return True
        return False

    def visit_Call(self, node: ast.Call):
        if self.is_shlex_split_call(node):
            self.shlex_calls.append((node.lineno, self.current_function, self._unparse_call(node)))
        if self.is_normpath_call(node):
            self.normpath_calls.append((node.lineno, self.current_function, self._unparse_call(node)))
        self.generic_visit(node)


def parse_and_analyze_ast(content: str, filename: str) -> NormalizationAstVisitor:
    tree = ast.parse(content, filename=filename)
    visitor = NormalizationAstVisitor(filename)
    visitor.collect_imports(tree)
    visitor.visit(tree)
    return visitor


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
        """Chamadas a os.path.normpath, posixpath.normpath e aliases são restritas a normalize.py (D02 / PR-QA-D3)."""
        violations = []

        for py_file in sorted(CORE_DIR.glob("*.py")):
            if py_file.name in ("__init__.py", "normalize.py"):
                continue
            if py_file.name in NORMPATH_EXCEPTIONS:
                continue

            content = py_file.read_text(encoding="utf-8")
            try:
                visitor = parse_and_analyze_ast(content, filename=str(py_file))
            except SyntaxError as e:
                self.fail(f"Erro de sintaxe em {py_file.name}: {e}")

            for lineno, func_name, call_repr in visitor.normpath_calls:
                scope = func_name or "<module>"
                violations.append(
                    f"{py_file.name}:{lineno} invoca normpath diretamente na função '{scope}': {call_repr}"
                )

        self.assertFalse(
            violations,
            "Usos diretos de normpath encontrados fora de normalize.py:\n" + "\n".join(f"  • {v}" for v in violations)
        )

    def test_shlex_split_restricted_to_normalize_py_or_justified_exceptions(self):
        """Chamadas a shlex.split e seus aliases são restritas a normalize.py ou ao call-site is_cert_tampering (D01/D02 / PR-QA-D3)."""
        violations = []
        observed_call_counts: dict[tuple[str, str], int] = {}

        for py_file in sorted(CORE_DIR.glob("*.py")):
            if py_file.name in ("__init__.py", "normalize.py"):
                continue

            content = py_file.read_text(encoding="utf-8")
            try:
                visitor = parse_and_analyze_ast(content, filename=str(py_file))
            except SyntaxError as e:
                self.fail(f"Erro de sintaxe em {py_file.name}: {e}")

            for lineno, func_name, call_repr in visitor.shlex_calls:
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

    def test_ast_analyzer_resolves_shlex_split_aliases(self):
        """Garante permanentemente que o analisador AST detecta todos os formatos e aliases de shlex.split (PR-QA-D3)."""
        test_cases = [
            ("from shlex import split as shell_lexer\nshell_lexer('cmd')", "shell_lexer"),
            ("from shlex import split\nsplit('cmd')", "split"),
            ("import shlex as sx\nsx.split('cmd')", "sx.split"),
            ("import shlex\nshlex.split('cmd')", "shlex.split"),
        ]
        for snippet, label in test_cases:
            visitor = parse_and_analyze_ast(snippet, filename="test_snippet.py")
            self.assertEqual(
                len(visitor.shlex_calls), 1,
                f"Falha ao detectar chamada de shlex.split no snippet com alias '{label}': {snippet}"
            )

    def test_ast_analyzer_resolves_normpath_aliases(self):
        """Garante permanentemente que o analisador AST detecta todos os formatos e aliases de normpath (PR-QA-D3)."""
        test_cases = [
            ("from os.path import normpath as path_normalizer\npath_normalizer('a/b')", "path_normalizer"),
            ("from posixpath import normpath as pnorm\npnorm('a/b')", "pnorm"),
            ("from posixpath import normpath\nnormpath('a/b')", "posixpath.normpath"),
            ("import posixpath as ppath\nppath.normpath('a/b')", "ppath.normpath"),
            ("import os.path as osp\nosp.normpath('a/b')", "osp.normpath"),
            ("from os import path as osp\nosp.normpath('a/b')", "osp.normpath from os"),
            ("import os\nos.path.normpath('a/b')", "os.path.normpath"),
        ]
        for snippet, label in test_cases:
            visitor = parse_and_analyze_ast(snippet, filename="test_snippet.py")
            self.assertEqual(
                len(visitor.normpath_calls), 1,
                f"Falha ao detectar chamada de normpath no snippet com alias '{label}': {snippet}"
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
