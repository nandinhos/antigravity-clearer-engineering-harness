<div align="center">

# 🛡️ CLEARER Engineering Harness (CEH)
### Framework de Engenharia de Software Orientado a Evidências para o Google Antigravity

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Antigravity](https://img.shields.io/badge/Antigravity-v1.1%2B-purple.svg)](https://github.com/nandinhos/antigravity-clearer-engineering-harness)
[![Tests](https://img.shields.io/badge/Testes-100%25%20Aprovados-brightgreen.svg)](./clearer-engineering/tests/)
[![Risk Dial](https://img.shields.io/badge/Risk%20Dial-LOW%20|%20MEDIUM%20|%20HIGH-orange.svg)](#-o-risk-dial)

**Português (Brasil)** | [**English**](./README.md)

</div>

---

## 📖 Visão Geral

O **CLEARER Engineering Harness (CEH)** é um framework de engenharia de software de alta precisão projetado nativamente para o **Google Antigravity**.

Em vez de depender de prompts vagos ou suposições não comprovadas, o CEH força o agente a trabalhar como um **engenheiro orientado a evidências**. Ele elimina o *hallucination coding*, proíbe relatórios falsos de testes (*fake pass*), minimiza o blast radius das modificações e executa revisões de código adversariais antes de consolidar qualquer entrega.

```mermaid
flowchart TD
    A[🎯 Concrete Goal - Objetivo Concreto] --> B[🔍 Load Context - Inspect Before Edit]
    B --> C[🚧 Explicit Boundaries - Blast Radius Mínimo]
    C --> D[⚓ Anchors - Evidências no Código Real]
    D --> E[📋 Implementação e Testes Determinísticos]
    E --> F[🕵️ Revisão Adversarial de Código]
    F --> G[⚖️ Auditoria de Claims e Evidências]
    G --> H[📊 Contrato Verificável Final]
```

---

## ⚡ Instalação Global em Um Comando (One-Liner)

Instale o CEH no Linux, macOS ou WSL executando no terminal:

```bash
curl -fsSL https://raw.githubusercontent.com/nandinhos/antigravity-clearer-engineering-harness/main/install.sh | bash
```

### Instalação Manual

```bash
# Clonar o repositório
git clone https://github.com/nandinhos/antigravity-clearer-engineering-harness.git
cd antigravity-clearer-engineering-harness

# Executar o instalador
chmod +x install.sh
./install.sh
```

---

## 🚀 Como Utilizar

Após a instalação, recarregue o shell com `source ~/.bashrc` (ou `source ~/.zshrc`) e execute:

```bash
# Iniciar o Antigravity com o perfil CLEARER Engineering Harness
agy-ceh

# Iniciar em modo YOLO (auto-aprovação de edições com Safety Gate ativo)
agy-ceh-yolo
```

---

## 📚 Documentação Técnica Completa (`docs/`)

Explore as diretrizes aprofundadas do CEH:

| Documento | Descrição |
|---|---|
| 📜 [**Guia do Protocolo CLEARER**](./docs/clearer_protocol.md) | Explicação completa das 7 etapas do ciclo de engenharia (*Concrete Goal*, *Load Context*, etc.). |
| 🎚️ [**Especificação do Risk Dial**](./docs/risk_dial.md) | Como o CEH modula o esforço entre os níveis **LOW**, **MEDIUM** e **HIGH**. |
| ⚖️ [**Semântica de Evidências & Claims**](./docs/evidence_semantics.md) | Classificação epistêmica (`OBSERVED`, `INFERRED`, `UNKNOWN`) e auditoria de claims (`SUPPORTED`). |
| 🏗️ [**Arquitetura do Sistema**](./docs/architecture.md) | Topologia, contratos de dados entre subagentes e integração de hooks do Antigravity. |
| 🤖 [**Guia de Subagentes Especializados**](./docs/agents_guide.md) | Papéis e contratos de entrada/saída de Investigator, Architect, Implementer, Test Engineer, Reviewer e Auditor. |
| 🛠️ [**Manual de Skills & Comandos**](./docs/skills_and_commands.md) | Como utilizar `/clearer`, `/clearer-feature`, `/clearer-bugfix`, `/clearer-refactor`, etc. |
| 🛡️ [**Guia do Safety Gate**](./docs/safety_gate.md) | Como o hook `PreToolUse` intercepta comandos destrutivos com `DENY > ASK > ALLOW`. |
| 💻 [**Instalação & Configuração**](./docs/installation.md) | Guia completo de instalação global, dependências e desinstalação. |
| 💡 [**Exemplos Práticos**](./docs/examples.md) | Casos reais de uso em TypeScript/Next.js, PHP/Laravel e Python/FastAPI. |

---

## 🧠 O Protocolo CLEARER em 7 Etapas

| Etapa | Princípio | Descrição |
|---|---|---|
| **C** | **Concrete Goal** | Definir requisitos precisos, critérios de aceite, escopo e condição de parada. |
| **L** | **Load Context** | *Inspect before edit*. Detectar a stack, entrypoints, testes e dependências antes de editar. |
| **E** | **Explicit Boundaries** | Delimitar o blast radius. Deixar explícito o que está dentro e o que fica fora do escopo. |
| **A** | **Anchors & Examples** | Fundamentar decisões no código existente, schemas, migrations e convenções do projeto. |
| **R** | **Response Contract** | Emitir saídas estruturadas e auditáveis (Alterações, Evidências, Testes, Review, Confiança). |
| **E** | **Enable Evidence & Tools** | Observação direta sobre suposição. Registrar saídas reais e exit codes das ferramentas. |
| **R** | **Review & Validate** | Executar o ciclo: `INSPECT → PLAN → IMPLEMENT → TEST → REVIEW → AUDIT`. |

---

## 🎚️ O Risk Dial

| Nível | Tarefas Indicadas | Procedimento Obrigatório |
|---|---|---|
| **`LOW`** | Consultas, formatações, renomeações locais simples, extrações pontuais. | Execução rápida, contexto enxuto, zero sobrecarga de subagentes. |
| **`MEDIUM`** | Features novas, correção de bugs, refatorações controladas, endpoints, schemas. | Inspeção → Plano Conciso → Implementação Cirúrgica → Testes Reais → Diff Audit → Relatório. |
| **`HIGH`** | Autenticação, permissões, pagamentos, concorrência, migrações destrutivas, segurança. | Investigação Profunda → Subagentes Especializados → Testes Red/Green → Revisão Adversarial → Auditoria Estrita. |

---

## 🤖 Topologia de Subagentes Especializados

```mermaid
graph TD
    ORCH[👑 CEH Orchestrator] --> INV[🔎 ceh-investigator<br/>Descoberta Read-Only de Contexto]
    INV -->|Evidence Pack| ARC[📐 ceh-architect<br/>Blast Radius e Plano]
    ARC -->|Implementation Plan| IMP[🔨 ceh-implementer<br/>Implementação Cirúrgica]
    IMP -->|Git Diff| TST[🧪 ceh-test-engineer<br/>Testes Determinísticos]
    IMP -->|Git Diff| REV[⚔️ ceh-reviewer<br/>Revisão Adversarial]
    TST --> AUD[⚖️ ceh-evidence-auditor<br/>Auditoria Claim ↔ Evidence]
    REV --> AUD
    AUD --> REP[📄 Relatório Verificável Final]
```

---

## 🧪 Suíte de Testes Automatizada

```bash
# 1. Executar testes de integração e componentes (17 testes)
./clearer-engineering/tests/run-all-tests.sh

# 2. Executar suíte de testes adversariais (5 cenários)
./clearer-engineering/tests/run-adversarial-tests.sh
```

---

## 📄 Licença

Distribuído sob a licença **Apache License 2.0**. Consulte [`LICENSE`](./LICENSE) para mais detalhes.
