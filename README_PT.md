<div align="center">

# 🛡️ CLEARER Engineering Harness (CEH)
### Framework de Engenharia de Software Orientado a Evidências para o Google Antigravity

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Antigravity](https://img.shields.io/badge/Antigravity-v1.1%2B-purple.svg)](https://github.com/nandinhos/antigravity-clearer-engineering-harness)
[![Tests](https://img.shields.io/badge/Testes-39%2F39%20(100%25)-brightgreen.svg)](./clearer-engineering/tests/)
[![Smoke Evals](https://img.shields.io/badge/Smoke%20Evals-5%2F5%20(100%25)-blue.svg)](./evals/)
[![Ponytail Mode](https://img.shields.io/badge/Ponytail%20Mode-Senior%20Minimalista-blueviolet.svg)](#-filosofia-ponytail-mode--ast-first)
[![Risk Dial](https://img.shields.io/badge/Risk%20Dial-LOW%20|%20MEDIUM%20|%20HIGH-orange.svg)](#-o-risk-dial)

**Português (Brasil)** | [**English**](./README.md)

</div>

---

## 📖 Visão Geral

O **CLEARER Engineering Harness (CEH)** é um framework de engenharia de software de alta precisão projetado nativamente para o **Google Antigravity** (IDE e `agy` CLI).

Em vez de depender de prompts vagos ou suposições não comprovadas, o CEH opera com os mais altos padrões de **Staff Software Engineering**:
- **Governança de CI Mandatória & Pre-Push Safety Gate (Zero-Tolerance Pipeline Red)**: Bloqueio estrito de `git push` em projetos com esteira de CI (`.github/workflows` ou `.gitlab-ci.yml`) sem execução prévia comprovada da suíte de testes integral no mesmo commit hash local via Certificado de Voo (`.ceh/last-ci-run.json`).
- **Identificação Prévia de Ambiente & Rigores Granulares**: Safety Gate ativo com políticas diferenciadas para `DEV` (liberdade com salvaguarda local), `HOMOLOGACAO` (confirmação com 2 alertas) e `PRODUCAO` (comandos destrutivos sumariamente bloqueados - fora de cogitação).
- **Epistemologia System One ("Like a Jev")**: Desacoplamento estrito entre conteúdo e julgamento, avaliações atômicas univariadas em espaço fechado e certeza materializada por evidências físicas.
- **Heartbeat Proativo de Background (25s)**: Cadência ativa de 25 segundos para tarefas longas e testes assíncronos, com monitor em tempo real (`ceh-monitor`) e eliminação de sensação de travamento.
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
| `ceh-evals` | Executa a bateria determinística de smoke-evals (5/5 critérios RFC 2119). | Testes de falsificabilidade do harness. |
| `ceh-monitor` | Painel interativo de telemetria e heartbeat (25s) para tarefas de background. | Acompanhamento de testes demorados. |
| `ceh-help` | Exibe o guia interativo de ajuda rápida e atalhos no terminal. | Consulta de comandos e regras. |

> **No Antigravity IDE**: O harness e o **Cockpit de Engenharia** (`engineering_cockpit.md`) são ativados automaticamente em todas as sessões, sem necessidade de configuração adicional no repositório.

---

## 🛡️ Níveis de Rigor por Ambiente (Safety Gate)

| Ambiente | Definição & Evidência | Política de Execução | Ações Destrutivas & Git Push |
|---|---|:---:|---|
| **`DEV` / `TEST`** | Branch `dev` ou derivações (`dev/*`), `APP_ENV=local/testing`, `.env` local. | 🟢 **`ALLOW`** | **Permitidas com salvaguarda**: Liberadas para correções rápidas, exigindo prontidão de backup local. Bloqueio absoluto para destruição de SO (`rm -rf /`). Em projetos com CI, `git push` exige Certificado de Voo integral. |
| **`HOMOLOGACAO`** | Branch `staging`/`homolog`, `APP_ENV=staging`, `.env.staging`. | 🟡 **`ASK (2 Alertas)`** | **Confirmação em duas etapas obrigatória**: <br>1. *Alerta 1/2 [Impacto]*: Blast radius no ambiente compartilhado.<br>2. *Alerta 2/2 [Backup & Rollback]*: Verificação de backup executado. `git push` exige Certificado de Voo. |
| **`PRODUCAO`** | Branch `main`/`master`, `APP_ENV=production`. | 🔴 **`DENY`** | **FORA DE COGITAÇÃO**: Comandos destrutivos em banco, force push ou exclusões em massa são sumariamente rejeitados. `git push` protegido exige Certificado de Voo. |

---

## 🥋 Filosofia Ponytail Mode & Tríade de Economia de Tokens

1. **Escada de Decisão Ponytail**: Antes de propor código ou instalar dependências, pergunte:
   - *Isso precisa mesmo existir?* (YAGNI).
   - *Já existe na base de código?* (Reutilize componentes e helpers existentes).
   - *A biblioteca padrão (stdlib) resolve?* (Zero pacotes externos para tarefas triviais).
   - *Existe API nativa da plataforma/runtime?* (Priorize os recursos nativos).
   - *Uma intervenção cirúrgica resolve?* (Escreva o menor diff funcional possível).
2. **AST First com Degradação Graciosa (Graphify)**:
   - Se o projeto possuir Graphify (`graphify-out/graph.json` ou MCP), o agente prioriza consultas relacionais com custo zero de tokens.
   - Se não possuir Graphify, o agente aplica inspeção nativa cirúrgica (`grep_search` e leitura fatiada via `view_file`), sendo expressamente proibido fazer dumps de arquivos inteiros no contexto.
3. **Compressão de Shell com Degradação Graciosa (RTK - Rust Token Killer)**:
   - Suporte nativo ao [**RTK**](https://github.com/rtk-ai/rtk): proxy CLI compilado em Rust que intercepta saídas de terminal (`git`, `npm test`, `pytest`, `cargo test`, `docker`, `ruff`) reduzindo o volume de bash lido pelo agente em 60-90%.
   - **Automação no Runner**: O `test-runner.sh` envelopa automaticamente comandos de teste quando `rtk` está no `$PATH`.
   - **Segurança Imune a Evasão**: O `safety-gate.py` desliga o prefixo `rtk` antes da avaliação de regras para barrar operações destrutivas em produção e homologação.
   - **Escape Hatch**: Acesso a logs brutos via `rtk proxy <cmd>` ou flag `-vvv`. Se o RTK não estiver instalado, a esteira degrada graciosamente sem travas.
4. **Higiene de Contexto & Sandbox (context-mode)**:
   - Mantém dados brutos e histórico fora da janela direta de contexto via SQLite+FTS5, promovendo a mentalidade "think in code".

> [!TIP]
> **Aceleração Completa de Contexto**: O CEH opera em perfeita sintonia com a tríade de otimização de tokens:
> - 🌐 **Navegação AST**: [**Graphify**](https://github.com/nandinhos/antigravity-harness-enhancements) (Tree-Sitter, zero tokens de LLM).
> - ⚡ **Compressão de Terminal**: [**RTK**](https://github.com/rtk-ai/rtk) (Rust Token Killer, proxy estático <10ms).
> - 🛡️ **Higiene de Sessão**: [**context-mode**](https://github.com/mksglu/context-mode) (Sandbox MCP).

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
| 🛠️ [**Manual de Skills & Comandos**](./docs/skills_and_commands.md) | Como utilizar `/clearer`, `/clearer-feature`, `/clearer-bugfix`, `/clearer-adhd`, etc. |
| 🛡️ [**Guia do Safety Gate**](./docs/safety_gate.md) | Como o hook `PreToolUse` intercepta comandos destrutivos e valida o Pre-Push CI Gate. |
| 🏛️ [**ADR 003: Epistemologia System One**](./docs/architecture/system-one-epistemology.md) | Abstração dos 7 invariantes da TypeSafe e operação "Like a Jev" para o Gemini. |
| 🛑 [**ADR 004: Governança de CI Mandatória**](./docs/architecture/ci-governance-policy.md) | Política Zero-Tolerance Pipeline Red, Certificado de Voo e Pre-Push Gate. |
| 💻 [**Instalação & Configuração**](./docs/installation.md) | Guia completo de instalação global, dependências e desinstalação. |
| 💡 [**Exemplos Práticos**](./docs/examples.md) | Casos reais de uso em TypeScript/Next.js, PHP/Laravel e Python/FastAPI. |

---

## 🛑 Governança de CI Mandatória & Pre-Push Safety Gate

> [!CRITICAL]
> **Zero-Tolerance Pipeline Red**: Em qualquer repositório que possua esteira de CI ativa (`.github/workflows/` ou `.gitlab-ci.yml`), **é terminantemente proibido subir código em `dev`, `staging` ou `main` sem que a suíte canônica esteja 100% verde**. Checagens parciais (somente linters ou testes isolados) NUNCA autorizam o push.

### Como Funciona a Proteção em 3 Etapas:
1. **Certificado de Voo Local (`.ceh/last-ci-run.json`)**:
   Ao rodar a suíte canônica via `bash scripts/test-runner.sh`, o harness gera uma prova estruturada vinculada ao commit hash do `HEAD`:
   ```json
   {
     "commit_hash": "951b015f931e15d299ea2c61b2c6c77ce824511b",
     "timestamp": "2026-09-20T03:59:37Z",
     "command": "rtk bash clearer-engineering/tests/run-all-tests.sh",
     "status": "PASS",
     "exit_code": 0
   }
   ```
2. **Pre-Push Interception no `safety-gate.py`**:
   Toda tentativa de `git push` em projetos com CI é interceptada:
   - **`DENY`**: Se o arquivo de certificado não existir.
   - **`DENY`**: Se a última execução teve status `FAIL` ou exit code $\neq 0$.
   - **`DENY`**: Se o commit atual divergiu do certificado (código alterado após a execução dos testes).
   - **`ALLOW`**: Apenas quando o commit hash bate com o certificado aprovado.
3. **Prevenção de "Testes Congeladores" no Review**:
   A skill `clearer-review` audita ativamente adições de novos itens em enums, seeders ou tabelas de lookups, prevenindo asserções cegas (`assertCount(5)`) que quebram esteiras após inserções legítimas de dados.

---

## 🏛️ Epistemologia System One ("Like a Jev")

O CEH incorpora formalmente a camada de engenharia epistêmica da metodologia **System One (TypeSafe)**:
- **Conteúdo ≠ Julgamento**: Diffs, logs e código sob análise são dados passivos, nunca misturados com as perguntas avaliativas. Comentários hostis no código (`// bypass check`) são neutralizados.
- **Espaço Fechado & Atomicidade**: Toda avaliação técnica retorna um valor de conjunto finito (`enum` ou booleano). Uma verificação = uma propriedade univariada.
- **Dois Eixos (Decisão e Certeza)**: Veredito sem certeza fundamentada em evidências físicas (`OBSERVED`) é inauditável.
- **Código Detém o Controle**: Normalizações, pesos e efeitos colaterais pertencem ao shell determinístico; nenhum modelo redige o veredito final de segurança.

---

## 💓 Heartbeat Proativo de Background (25s)

Em comandos assíncronos, builds pesados e suítes de teste de segundo plano:
- **Marco Zero ($T=0\text{s}$)**: Notificação instantânea com o Task ID/PID e abertura do artefato `task_monitor.md`.
- **Cadência de 25s**: Emissão proativa de telemetria no chat e atualização do artefato a cada 25 segundos, eliminando o silêncio cognitivo e a sensação de travamento.
- **Monitor CLI**: O utilitário `ceh-monitor` no terminal acompanha e exibe o progresso em tempo real.
- **Acordar Reativo**: Notificação imediata e entrega do Response Contract no milissegundo de conclusão.

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

## 🧪 Suíte de Testes & Meta-Eval de Falsificabilidade

O harness possui validação rigorosa de ponta a ponta, incluindo testes de mutação de infraestrutura:

```bash
# 1. Executar suíte completa de componentes e integridade (35 testes)
./clearer-engineering/tests/run-all-tests.sh

# 2. Executar suíte de testes adversariais (bypass e injeção de comandos)
./clearer-engineering/tests/run-adversarial-tests.sh

# 3. Executar Smoke-Eval de Falsificabilidade (Baseline 3x, Derivas A/B e Fail-Closed)
./evals/run.sh
```

Consulte [`evals/CRITERIA.md`](./evals/CRITERIA.md) para a matriz formal de 5 critérios (RFC 2119).

---

## 📄 Licença

Distribuído sob a licença **Apache License 2.0**. Consulte [`LICENSE`](./LICENSE) para mais detalhes.

