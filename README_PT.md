<div align="center">

# 🛡️ CLEARER Engineering Harness (CEH)
### Framework de Engenharia de Software Orientado a Evidências para o Google Antigravity

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Antigravity](https://img.shields.io/badge/Antigravity-v1.1%2B-purple.svg)](https://github.com/nandinhos/antigravity-clearer-engineering-harness)
[![Tests](https://img.shields.io/badge/Testes-25%2F25%20(100%25)-brightgreen.svg)](./clearer-engineering/tests/)
[![Ponytail Mode](https://img.shields.io/badge/Ponytail%20Mode-Senior%20Minimalista-blueviolet.svg)](#-filosofia-ponytail-mode--ast-first)
[![Risk Dial](https://img.shields.io/badge/Risk%20Dial-LOW%20|%20MEDIUM%20|%20HIGH-orange.svg)](#-o-risk-dial)

**Português (Brasil)** | [**English**](./README.md)

</div>

---

## 📖 Visão Geral

O **CLEARER Engineering Harness (CEH)** é um framework de engenharia de software de alta precisão projetado nativamente para o **Google Antigravity** (IDE e `agy` CLI).

Em vez de depender de prompts vagos ou suposições não comprovadas, o CEH opera com os mais altos padrões de **Staff Software Engineering**:
- **Identificação Prévia de Ambiente & Rigores Granulares**: Safety Gate ativo com políticas diferenciadas para `DEV` (liberdade com salvaguarda local), `HOMOLOGACAO` (confirmação com 2 alertas) e `PRODUCAO` (comandos destrutivos sumariamente bloqueados - fora de cogitação).
- **Filosofia Ponytail Mode & AST First**: "Entender muito, construir pouco e entregar certo". Escada de decisão anti-over-engineering, menor diff funcional e priorização de AST relacional com degradação graciosa.
- **Topologias Canônicas Flexíveis**: Suporte nativo a **Modo Enterprise (3 branches: `dev` ➔ `staging` ➔ `main`)** e **Modo Clássico (2 branches: `dev` ➔ `main`)**, com assistente interativo `ceh-branches`.
- **Execução Contínua em Nível MEDIUM**: Ciclo completo `INSPECT → PLAN → IMPLEMENT → TEST → REVIEW → AUDIT` conduzido de ponta a ponta em **turno único (Single-Turn End-to-End)**.
- **Zero Hallucination & Zero Fake Pass**: Proíbe a criação de código especulativo e garante que toda alegação de sucesso seja sustentada por comandos reais e logs executados em `OBSERVED`.

---

## ⚡ Instalação Global em Um Comando (One-Liner)

Instale ou atualize o CEH no Linux, macOS ou WSL executando no terminal:

```bash
curl -fsSL https://raw.githubusercontent.com/nandinhos/antigravity-clearer-engineering-harness/main/install.sh | bash
```

---

## 🚀 Como Utilizar no Terminal & CLI

Após a instalação, recarregue o shell com `source ~/.bashrc` (ou `source ~/.zshrc`) para acessar o kit de ferramentas:

| Comando | O que faz | Contexto / Exemplo |
|---|---|---|
| `ceh` / `agy-ceh` | Inicia o Antigravity CLI sob o perfil `clearer-harness`. | Uso diário no terminal. |
| `agy-ceh-yolo` | Inicia o Antigravity com auto-aprovação de edições seguras. | Modo ágil em desenvolvimento. |
| `ceh-env` | Identifica instantaneamente o ambiente (`DEV`/`STAGING`/`PROD`), branch e rigores ativos. | Checagem rápida antes de codificar. |
| `ceh-branches` | Audita e configura as branches do projeto (Modo Enterprise ou Clássico). | Setup de novos repositórios. |
| `ceh-preflight` | Executa a verificação completa de prontidão e integridade do projeto. | Validação antes de releases. |
| `ceh-help` | Exibe o guia interativo de ajuda rápida e atalhos no terminal. | Consulta de comandos e regras. |

> **No Antigravity IDE**: O harness e o **Cockpit de Engenharia** (`engineering_cockpit.md`) são ativados automaticamente em todas as sessões, sem necessidade de configuração adicional no repositório.

---

## 🛡️ Níveis de Rigor por Ambiente (Safety Gate)

| Ambiente | Definição & Evidência | Política de Execução | Ações Destrutivas |
|---|---|:---:|---|
| **`DEV` / `TEST`** | Branch `dev` ou derivações (`dev/*`), `APP_ENV=local/testing`, `.env` local. | 🟢 **`ALLOW`** | **Permitidas com salvaguarda**: Liberadas para correções rápidas, exigindo prontidão de backup local. Bloqueio absoluto para destruição de SO (`rm -rf /`). |
| **`HOMOLOGACAO`** | Branch `staging`/`homolog`, `APP_ENV=staging`, `.env.staging`. | 🟡 **`ASK (2 Alertas)`** | **Confirmação em duas etapas obrigatória**: <br>1. *Alerta 1/2 [Impacto]*: Blast radius no ambiente compartilhado.<br>2. *Alerta 2/2 [Backup & Rollback]*: Verificação de backup executado. |
| **`PRODUCAO`** | Branch `main`/`master`, `APP_ENV=production`. | 🔴 **`DENY`** | **FORA DE COGITAÇÃO**: Comandos destrutivos em banco, force push ou exclusões em massa são sumariamente rejeitados. |

---

## 🥋 Filosofia Ponytail Mode & AST First

1. **Escada de Decisão Ponytail**: Antes de propor código ou instalar dependências, pergunte:
   - *Isso precisa mesmo existir?* (YAGNI).
   - *Já existe na base de código?* (Reutilize componentes e helpers existentes).
   - *A biblioteca padrão (stdlib) resolve?* (Zero pacotes externos para tarefas triviais).
   - *Existe API nativa da plataforma/runtime?* (Priorize os recursos nativos).
   - *Uma intervenção cirúrgica resolve?* (Escreva o menor diff funcional possível).
2. **AST First com Degradação Graciosa**:
   - Se o projeto possuir Graphify (`graphify-out/graph.json` ou MCP), o agente prioriza consultas relacionais com custo zero de tokens.
   - Se não possuir Graphify, o agente aplica inspeção nativa cirúrgica (`grep_search` e leitura fatiada via `view_file`), sendo expressamente proibido fazer dumps de arquivos inteiros no contexto.

---

## 📚 Documentação Técnica Completa (`docs/`)

Explore as diretrizes aprofundadas do CEH:

| Documento | Descrição |
|---|---|
| 📜 [**Guia do Protocolo CLEARER**](./docs/clearer_protocol.md) | Explicação completa das 7 etapas do ciclo de engenharia (*Concrete Goal*, *Load Context*, etc.). |
| 💎 [**Padrões de Código & Craftsmanship**](./docs/coding_standards.md) | Diretrizes de alto nível de engenharia: Clean Code, SOLID, tipagem estrita, resiliência e testes. |
| 🎚️ [**Especificação do Risk Dial**](./docs/risk_dial.md) | Dinâmica de **Execução Contínua** para MEDIUM e os 4 gates de checkpoint por exceção. |
| ⚖️ [**Semântica de Evidências & Claims**](./docs/evidence_semantics.md) | Classificação epistêmica (`OBSERVED`, `INFERRED`, `UNKNOWN`) e auditoria de claims (`SUPPORTED`). |
| 🏗️ [**Arquitetura do Sistema**](./docs/architecture.md) | Topologia, pipelines unificados, contratos entre subagentes e integração de hooks. |
| 🤖 [**Guia de Subagentes Especializados**](./docs/agents_guide.md) | Papéis de Investigator, Architect, Implementer, Test Engineer, Reviewer e Auditor. |
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

## 🎚️ O Risk Dial & Automação de Execução

| Nível | Tarefas Indicadas | Dinâmica Operacional |
|---|---|---|
| **`LOW`** | Consultas, formatações, renomeações locais simples, extrações pontuais. | Execução rápida, contexto enxuto, zero sobrecarga. |
| **`MEDIUM`** | Features novas, correção de bugs, refatorações, endpoints, regras de negócio. | **Execução Contínua em Turno Único**: Inspeciona → Planeja → Implementa com Alto Padrão → Roda Testes com Auto-Reparo → Diff Audit → Response Contract. |
| **`HIGH`** | Autenticação core, permissões, pagamentos, concorrência, migrações destrutivas, segurança. | Investigação Profunda → Subagentes Especializados → Revisão Adversarial → Auditoria Estrita → Checkpoint Humano. |

---

## 🛡️ Checkpoints por Exceção (Fail-Closed on Real Hazards)

O fluxo contínuo do agente só é interrompido diante de **4 condições de parada estritas**:
1. **Ambiguidade Real de Negócio**: Decisões de arquitetura/negócio excludentes sem especificação clara.
2. **Risco Destrutivo (Safety Gate Granular por Ambiente)**:
   - Em `PRODUÇÃO`: Comandos destrutivos são terminantemente proibidos (`DENY` - "fora de cogitação").
   - Em `HOMOLOGAÇÃO`: Exige confirmação humana obrigatória (`ASK`) com **2 Alertas Explícitos** (Impacto HML e Salvaguardas de Backup/Rollback).
   - Em `DEV / TEST`: Comandos destrutivos liberados para fins de correção ágil com aviso de salvaguarda local (`ALLOW`), mantendo `DENY` para suicídios de SO (`rm -rf /`, etc.).
3. **Falha Persistente de Testes**: Quebra de suíte de testes após 1 iteração de auto-reparo fundamentada.
4. **Nível HIGH Explícito**: Tarefas classificadas expressamente como de alto risco.

## 🌿 Estratégias de Branches & Modos de Desenvolvimento

O CEH apoia o desenvolvedor com **2 modos de topologia Git**, identificados proativamente no carregamento do projeto:

1. **Modo Enterprise (3 Branches: `dev` ➔ `staging` ➔ `main`)**:
   - `dev`: Desenvolvimento core, testes e movimentações livres (`ALLOW` com salvaguardas).
   - `staging`: Homologação com dados reais e validação (`ASK` com 2 alertas e backup obrigatório).
   - `main`: Produção protegida para deploy (`DENY` incondicional).
   - *Ideal para equipes, esteiras de CI/CD e sistemas corporativos.*

2. **Modo Clássico (2 Branches: `dev` ➔ `main`)**:
   - `dev`: Onde todas as tarefas, spikes e correções ocorrem (`ALLOW`).
   - `main`: Produção protegida para release direto (`DENY`).
   - *Ideal para projetos ágeis, MVPs e desenvolvedores solo.*

> **Assistente Automatizado**: Execute `bash clearer-engineering/scripts/setup-branches.sh --classic` (ou `--enterprise`) para configurar a topologia do seu repositório em 1 clique.

---

## 🧪 Suíte de Testes Automatizada

```bash
# 1. Executar testes de integração e componentes (19 testes)
./clearer-engineering/tests/run-all-tests.sh

# 2. Executar suíte de testes adversariais (5 cenários)
./clearer-engineering/tests/run-adversarial-tests.sh
```

---

## 📄 Licença

Distribuído sob a licença **Apache License 2.0**. Consulte [`LICENSE`](./LICENSE) para mais detalhes.

