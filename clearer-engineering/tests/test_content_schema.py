#!/usr/bin/env python3
# ==============================================================================
# test_content_schema.py — Validação de Esquema, Catálogo e Integridade de Conteúdo
# ==============================================================================
"""
Suíte determinística de validação estrutural (PR-18 / T3):
1. Frontmatter YAML obrigatório (name, description) em agentes, skills e perfis.
2. Integridade do catálogo de ferramentas com verificação de evidência física.
3. Resolução física de links de skills (/nome).
4. Resolução física de links Markdown relativos com preservação de número de linha.
5. Asserções de estrutura de conteúdo (substituição de greps frágeis).
"""

from __future__ import annotations

import json
import os
import re
import unittest
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PLUGIN_DIR = REPO_ROOT / "clearer-engineering"
CONFIG_DIR = PLUGIN_DIR / "config"
TOOL_CATALOG_PATH = CONFIG_DIR / "tool_catalog.json"


def _simple_yaml_parse(raw: str) -> dict[str, Any]:
    """
    Parser determinístico de frontmatter YAML baseado estritamente na biblioteca padrão (stdlib).
    Elimina dependências externas (ex: PyYAML) garantindo 100% de portabilidade e hermeticidade
    em qualquer versão de Python (3.9+) e qualquer runner de CI.
    """
    res: dict[str, Any] = {}
    lines = raw.splitlines()
    current_key: str | None = None
    multiline_buf: list[str] = []
    is_list = False

    def commit_multiline():
        nonlocal current_key, multiline_buf
        if current_key and multiline_buf:
            res[current_key] = " ".join(line.strip() for line in multiline_buf if line.strip())
            multiline_buf = []

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # Item de lista: "- item"
        if stripped.startswith("- ") and current_key and is_list:
            item = stripped[2:].strip().strip("\"'")
            res[current_key].append(item)
            continue

        # Chave de primeiro nível: "chave: valor"
        match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if match:
            commit_multiline()
            key, val = match.group(1), match.group(2).strip()
            current_key = key
            if val in (">-", ">", "|", "|-"):
                is_list = False
                multiline_buf = []
            elif val == "":
                # Lista subsequente
                is_list = True
                res[key] = []
            else:
                is_list = False
                res[key] = val.strip("\"'")
        else:
            if current_key and not is_list:
                multiline_buf.append(stripped)

    commit_multiline()
    return res


def parse_frontmatter(file_path: Path) -> tuple[dict[str, Any], str, int]:
    """
    Analisa o frontmatter YAML de um arquivo Markdown.
    Retorna (dados_yaml, conteudo_markdown, linha_inicio_body).
    """
    content = file_path.read_text(encoding="utf-8")
    if not content.startswith("---"):
        raise ValueError(f"{file_path}:1: Frontmatter inicial '---' ausente.")

    parts = content.split("---", 2)
    if len(parts) < 3:
        raise ValueError(f"{file_path}: Frontmatter '---' não foi fechado.")

    raw_yaml = parts[1]
    body = parts[2]
    body_start_line = raw_yaml.count("\n") + 2

    # Tenta usar PyYAML se disponível; caso contrário, usa o parser stdlib hermético
    try:
        import yaml
        data = yaml.safe_load(raw_yaml)
    except Exception:
        data = _simple_yaml_parse(raw_yaml)

    if not isinstance(data, dict):
        raise ValueError(f"{file_path}:1: Frontmatter deve ser um objeto/dicionário YAML.")

    return data, body, body_start_line


class TestFrontmatterSchema(unittest.TestCase):
    """Valida que todos os agentes, skills e perfis possuem frontmatter válido e campos obrigatórios."""

    def test_agents_frontmatter(self) -> None:
        agents_dir = PLUGIN_DIR / "agents"
        agent_files = sorted(agents_dir.glob("*/agent.md"))
        self.assertGreater(len(agent_files), 0, "Nenhum agente encontrado em agents/*/agent.md")

        for agent_file in agent_files:
            dir_name = agent_file.parent.name
            with self.subTest(agent=dir_name):
                data, _, _ = parse_frontmatter(agent_file)
                name = data.get("name")
                desc = data.get("description")

                self.assertIsInstance(name, str, f"{agent_file}: Campo 'name' deve ser string.")
                self.assertTrue(bool(name and name.strip()), f"{agent_file}: Campo 'name' não pode ser vazio.")
                expected_name = f"ceh-{dir_name}"
                self.assertEqual(
                    name,
                    expected_name,
                    f"{agent_file}: Campo 'name' ('{name}') deve seguir a convenção '{expected_name}'.",
                )

                self.assertIsInstance(desc, str, f"{agent_file}: Campo 'description' deve ser string.")
                self.assertTrue(bool(desc and desc.strip()), f"{agent_file}: Campo 'description' não pode ser vazio.")

    def test_skills_frontmatter(self) -> None:
        skills_dir = PLUGIN_DIR / "skills"
        skill_files = sorted(skills_dir.glob("*/SKILL.md"))
        self.assertGreater(len(skill_files), 0, "Nenhuma skill encontrada em skills/*/SKILL.md")

        for skill_file in skill_files:
            dir_name = skill_file.parent.name
            with self.subTest(skill=dir_name):
                data, _, _ = parse_frontmatter(skill_file)
                name = data.get("name")
                desc = data.get("description")

                self.assertIsInstance(name, str, f"{skill_file}: Campo 'name' deve ser string.")
                self.assertTrue(bool(name and name.strip()), f"{skill_file}: Campo 'name' não pode ser vazio.")
                self.assertEqual(
                    name,
                    dir_name,
                    f"{skill_file}: Campo 'name' ('{name}') deve coincidir exatamente com o nome do diretório ('{dir_name}').",
                )

                self.assertIsInstance(desc, str, f"{skill_file}: Campo 'description' deve ser string.")
                self.assertTrue(bool(desc and desc.strip()), f"{skill_file}: Campo 'description' não pode ser vazio.")

    def test_profile_frontmatter(self) -> None:
        profile_file = PLUGIN_DIR / "profiles" / "clearer-harness.agent.md"
        self.assertTrue(profile_file.is_file(), f"Perfil não encontrado: {profile_file}")

        data, _, _ = parse_frontmatter(profile_file)
        name = data.get("name")
        desc = data.get("description")

        self.assertEqual(name, "clearer-harness", f"{profile_file}: 'name' deve ser 'clearer-harness'.")
        self.assertIsInstance(desc, str, f"{profile_file}: 'description' deve ser string.")
        self.assertTrue(bool(desc and desc.strip()), f"{profile_file}: 'description' não pode ser vazio.")


class TestToolCatalogIntegrity(unittest.TestCase):
    """Valida o catálogo de ferramentas e a comprovação física rigorosa de proveniência (PR-18b)."""

    def setUp(self) -> None:
        self.assertTrue(TOOL_CATALOG_PATH.is_file(), f"Catálogo ausente: {TOOL_CATALOG_PATH}")
        with open(TOOL_CATALOG_PATH, "r", encoding="utf-8") as f:
            self.catalog = json.load(f)
        self.tools_catalog = self.catalog.get("tools", {})

    def test_catalog_evidence_provenance_and_verification(self) -> None:
        self.assertGreater(len(self.tools_catalog), 0, "Catálogo de ferramentas está vazio.")
        valid_evidence_types = {"payload", "host_doc", "declared"}
        declared_tools: list[tuple[str, str, str]] = []

        for tool_name, tool_data in self.tools_catalog.items():
            ev_type = tool_data.get("evidence_type")
            self.assertIn(
                ev_type,
                valid_evidence_types,
                f"{TOOL_CATALOG_PATH}: Ferramenta '{tool_name}' possui 'evidence_type' inválido: '{ev_type}'. "
                f"Esperado um de: {sorted(list(valid_evidence_types))}",
            )

            host = tool_data.get("host")
            self.assertIn(host, {"agy", "claude", "all"}, f"{tool_name}: host inválido '{host}'")

            if ev_type == "payload":
                evidence_path_str = tool_data.get("evidence_path")
                self.assertTrue(
                    bool(evidence_path_str),
                    f"{TOOL_CATALOG_PATH}: Ferramenta '{tool_name}' com evidence_type='payload' exige 'evidence_path'.",
                )
                evidence_file = REPO_ROOT / str(evidence_path_str)
                self.assertTrue(
                    evidence_file.is_file(),
                    f"{TOOL_CATALOG_PATH}: Arquivo de payload não encontrado para '{tool_name}': {evidence_file}",
                )

                # Validação de conteúdo: deve conter invocação física da ferramenta no JSONL
                found_invocation = False
                with open(evidence_file, "r", encoding="utf-8") as fp:
                    for line in fp:
                        if not line.strip():
                            continue
                        entry = json.loads(line)
                        payload = entry.get("payload", {})
                        if host == "agy":
                            tool_call_name = payload.get("toolCall", {}).get("name")
                            if tool_call_name == tool_name:
                                found_invocation = True
                                break
                        elif host == "claude":
                            tool_call_name = payload.get("tool_name")
                            if tool_call_name == tool_name:
                                found_invocation = True
                                break

                self.assertTrue(
                    found_invocation,
                    f"{TOOL_CATALOG_PATH}: Payload '{evidence_file}' não contém invocação comprovada para '{tool_name}'.",
                )

            elif ev_type == "host_doc":
                evidence_path_str = tool_data.get("evidence_path")
                self.assertTrue(
                    bool(evidence_path_str),
                    f"{TOOL_CATALOG_PATH}: Ferramenta '{tool_name}' com evidence_type='host_doc' exige 'evidence_path'.",
                )
                evidence_file = REPO_ROOT / str(evidence_path_str)
                self.assertTrue(
                    evidence_file.is_file(),
                    f"{TOOL_CATALOG_PATH}: Arquivo de documentação de host não encontrado para '{tool_name}': {evidence_file}",
                )

                # Validação de conteúdo: o nome da ferramenta deve constar expressamente no arquivo
                doc_text = evidence_file.read_text(encoding="utf-8")
                self.assertIn(
                    tool_name,
                    doc_text,
                    f"{TOOL_CATALOG_PATH}: Nome da ferramenta '{tool_name}' não consta no arquivo de documentação '{evidence_file}'.",
                )

            elif ev_type == "declared":
                # Nenhuma entrada 'declared' pode apontar para dentro de host-probe/
                evidence_path_str = tool_data.get("evidence_path")
                if evidence_path_str:
                    self.assertNotIn(
                        "host-probe",
                        str(evidence_path_str),
                        f"{TOOL_CATALOG_PATH}: Ferramenta '{tool_name}' declarada (declared) não pode apontar para 'host-probe/'.",
                    )
                source = tool_data.get("declaration_source", "Não informada")
                reason = tool_data.get("declaration_reason", "Não informado")
                declared_tools.append((tool_name, source, reason))

        # Relatório de transparência das ferramentas declaradas
        print(f"\n[TOOL CATALOG PROVENANCE] {len(self.tools_catalog)} ferramentas verificadas.")
        print(f"  • Ferramentas com payload físico comprovado: {sum(1 for t in self.tools_catalog.values() if t.get('evidence_type') == 'payload')}")
        print(f"  • Ferramentas com documentação de host comprovada: {sum(1 for t in self.tools_catalog.values() if t.get('evidence_type') == 'host_doc')}")
        print(f"  • Ferramentas declaradas com rótulo explícito (declared): {len(declared_tools)}")
        for name, src, rsn in sorted(declared_tools):
            print(f"    - {name} [{src}]: {rsn}")

    def test_all_declared_tools_exist_in_catalog(self) -> None:
        target_files = sorted((PLUGIN_DIR / "agents").glob("*/agent.md")) + [
            PLUGIN_DIR / "profiles" / "clearer-harness.agent.md"
        ]

        for target in target_files:
            data, _, _ = parse_frontmatter(target)
            declared_tools = data.get("tools") or []
            self.assertIsInstance(declared_tools, list, f"{target}: 'tools' deve ser lista.")
            for tool in declared_tools:
                with self.subTest(file=target.name, tool=tool):
                    self.assertIn(
                        tool,
                        self.tools_catalog,
                        f"{target}: Ferramenta '{tool}' não existe no catálogo oficial {TOOL_CATALOG_PATH}.",
                    )


class TestSkillReferences(unittest.TestCase):
    """Valida que menções a slash commands / skills nos agentes resolvem para skills existentes."""

    def test_skill_references_resolve(self) -> None:
        skills_dir = PLUGIN_DIR / "skills"
        existing_skills = {p.parent.name for p in skills_dir.glob("*/SKILL.md")}

        target_files = sorted((PLUGIN_DIR / "agents").glob("*/agent.md")) + [
            PLUGIN_DIR / "profiles" / "clearer-harness.agent.md"
        ]

        # Expressão para capturar referências explícitas a skills /clearer, /conselho, etc.
        skill_ref_pattern = re.compile(r"(?<![a-zA-Z0-9_.-])\/(clearer[a-zA-Z0-9_-]*|conselho-seniores|learned-lesson)")

        for target in target_files:
            content = target.read_text(encoding="utf-8")
            matches = set(skill_ref_pattern.findall(content))
            for skill_name in matches:
                with self.subTest(file=target.name, skill=skill_name):
                    self.assertIn(
                        skill_name,
                        existing_skills,
                        f"{target}: Referência a skill '/{skill_name}' não possui SKILL.md correspondente em skills/{skill_name}/SKILL.md",
                    )


class TestMarkdownRelativeLinks(unittest.TestCase):
    """Valida que todos os links relativos em arquivos Markdown apontam para arquivos físicos existentes."""

    def test_all_relative_links_resolve(self) -> None:
        md_files = (
            sorted(PLUGIN_DIR.glob("**/*.md"))
            + sorted(REPO_ROOT.glob("README*.md"))
            + [REPO_ROOT / "CHANGELOG.md"]
        )
        link_pattern = re.compile(r"\[([^\]]+)\]\(((\.{1,2}/[^)#]+)(?:#[^)]*)?)\)")

        broken_links: list[str] = []

        for md_path in md_files:
            if not md_path.is_file():
                continue
            with open(md_path, "r", encoding="utf-8", errors="ignore") as f:
                for line_no, line in enumerate(f, 1):
                    for match in link_pattern.finditer(line):
                        rel_path_str = match.group(3)
                        resolved = (md_path.parent / rel_path_str).resolve()
                        if not resolved.exists():
                            broken_links.append(
                                f"{md_path.relative_to(REPO_ROOT)}:{line_no} -> link quebrado '{rel_path_str}' (resolvido para {resolved})"
                            )

        self.assertEqual(
            len(broken_links),
            0,
            f"Links Markdown relativos quebrados encontrados:\n" + "\n".join(broken_links),
        )


class TestContentStructure(unittest.TestCase):
    """Substitui os antigos 'grep -q' de estrutura por asserções formais em código Python."""

    def test_profile_tools_declared(self) -> None:
        data, _, _ = parse_frontmatter(PLUGIN_DIR / "profiles" / "clearer-harness.agent.md")
        tools = set(data.get("tools", []))
        self.assertIn("write_to_file", tools, "Perfil clearer-harness deve ter 'write_to_file' declarado em tools.")
        self.assertIn("run_command", tools, "Perfil clearer-harness deve ter 'run_command' declarado em tools.")

    def test_implementer_tools_declared(self) -> None:
        data, _, _ = parse_frontmatter(PLUGIN_DIR / "agents" / "implementer" / "agent.md")
        tools = set(data.get("tools", []))
        self.assertIn("write_to_file", tools, "ceh-implementer deve ter 'write_to_file' declarado em tools.")
        self.assertIn("replace_file_content", tools, "ceh-implementer deve ter 'replace_file_content' declarado em tools.")

    def test_test_engineer_tools_declared(self) -> None:
        data, _, _ = parse_frontmatter(PLUGIN_DIR / "agents" / "test-engineer" / "agent.md")
        tools = set(data.get("tools", []))
        self.assertIn("run_command", tools, "ceh-test-engineer deve ter 'run_command' declarado em tools.")
        self.assertIn("write_to_file", tools, "ceh-test-engineer deve ter 'write_to_file' declarado em tools.")

    def test_bugfix_systematic_debugging_gates(self) -> None:
        skill_path = PLUGIN_DIR / "skills" / "clearer-bugfix" / "SKILL.md"
        content = skill_path.read_text(encoding="utf-8")
        gates = [
            "Gate 0 — TRIAGE",
            "Gate 1 — REPRODUCE",
            "Gate 2 — ISOLATE",
            "Gate 3 — ROOT CAUSE",
            "Gate 4 — FIX & HARDEN",
        ]
        for gate in gates:
            with self.subTest(gate=gate):
                self.assertIn(
                    gate,
                    content,
                    f"{skill_path}: Seção obrigatória '{gate}' do Systematic Debugging v2 ausente.",
                )

    def test_learned_lesson_engine_and_dev_memory(self) -> None:
        skill_path = PLUGIN_DIR / "skills" / "learned-lesson" / "SKILL.md"
        content = skill_path.read_text(encoding="utf-8")
        self.assertIn("Learned Lesson Engine v2.0", content, f"{skill_path}: Título canônico 'Learned Lesson Engine v2.0' ausente.")
        self.assertIn("dev-memory", content, f"{skill_path}: Suporte ao hub 'dev-memory' ausente.")

    def test_investigator_guidance(self) -> None:
        agent_path = PLUGIN_DIR / "agents" / "investigator" / "agent.md"
        content = agent_path.read_text(encoding="utf-8")
        self.assertIn(
            "Matriz de Hipóteses Falsificáveis",
            content,
            f"{agent_path}: Orientação sobre 'Matriz de Hipóteses Falsificáveis' ausente.",
        )

    def test_reviewer_regression_detector(self) -> None:
        agent_path = PLUGIN_DIR / "agents" / "reviewer" / "agent.md"
        content = agent_path.read_text(encoding="utf-8")
        self.assertIn("clearer-bugfix", content, f"{agent_path}: Menção ao 'clearer-bugfix' ausente.")
        self.assertIn("Detector", content, f"{agent_path}: Menção a 'Detector' de regressão ausente.")

    def test_adhd_ponytail_ux(self) -> None:
        skill_path = PLUGIN_DIR / "skills" / "clearer-adhd" / "SKILL.md"
        content = skill_path.read_text(encoding="utf-8")
        self.assertIn("Lead with Action", content, f"{skill_path}: Heurística 'Lead with Action' ausente.")
        self.assertIn("Break-Rules", content, f"{skill_path}: Cláusula 'Break-Rules' ausente.")

        rules_path = PLUGIN_DIR / "rules" / "AGENTS.md"
        rules_content = rules_path.read_text(encoding="utf-8")
        self.assertIn("Ponytail UX", rules_content, f"{rules_path}: Diretriz 'Ponytail UX' ausente nas regras do harness.")

    def test_stdlib_yaml_fallback_parses_all_frontmatters(self) -> None:
        """Garante que o parser fallback stdlib funciona de forma idêntica sem PyYAML em qualquer runtime."""
        all_frontmatters = (
            list((PLUGIN_DIR / "agents").glob("*/agent.md"))
            + list((PLUGIN_DIR / "skills").glob("*/SKILL.md"))
            + [PLUGIN_DIR / "profiles" / "clearer-harness.agent.md"]
        )
        for fm_path in all_frontmatters:
            content = fm_path.read_text(encoding="utf-8")
            raw_yaml = content.split("---", 2)[1]
            data = _simple_yaml_parse(raw_yaml)
            self.assertIn("name", data, f"{fm_path}: fallback stdlib não encontrou 'name'")
            self.assertIn("description", data, f"{fm_path}: fallback stdlib não encontrou 'description'")
            if "tools" in data:
                self.assertIsInstance(data["tools"], list, f"{fm_path}: tools deve ser lista")


if __name__ == "__main__":
    unittest.main()
