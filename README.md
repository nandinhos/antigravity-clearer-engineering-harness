# CLEARER Engineering Harness (CEH) para Google Antigravity

O **CLEARER Engineering Harness (CEH)** é um framework de engenharia de software de alta precisão projetado nativamente para o **Google Antigravity**. Ele transforma o agente de IA em um **engenheiro de software orientado por evidências**, eliminando comportamentos especulativos, alucinações de código (*hallucination coding*) e aprovações cegas (*fake pass*).

---

## 1. Instalação e Ativação

### Instalação via Antigravity CLI
```bash
# Validar estrutura do plugin
agy plugin validate ./clearer-engineering

# Instalar o plugin no Antigravity
agy plugin install ./clearer-engineering

# Listar plugins instalados
agy plugin list
```

### Verificação do Perfil de Agente
```bash
# Listar perfis de agentes disponíveis
agy agent
```
Você verá:
- `bc-harness` (Beer and Code Harness)
- `clearer-harness` (CLEARER Engineering Harness)
- `gemini-orchestrator` (Gemini Orchestrator)

### Aliases de Shell Configurados (`~/.bashrc` e `~/.zshrc`)
```bash
# Iniciar sessão Antigravity com o perfil CLEARER Harness
agy-ceh

# Iniciar sessão com auto-aprovação de edições controladas
agy-ceh-yolo
```

---

## 2. Arquitetura do Harness

```text
clearer-engineering/
├── plugin.json                 # Manifesto do plugin Antigravity
├── hooks.json                  # Integração do Safety Gate no PreToolUse
├── rules/                      # Regras ativas e políticas de engenharia
│   ├── AGENTS.md               # Regras consolidadas do CLEARER
│   ├── core-engineering.md     # Princípios de ciclo de vida e modulação
│   ├── evidence-policy.md      # Semântica OBSERVED, INFERRED, UNKNOWN e Claims
│   ├── coding-policy.md        # Inspect before edit e blast radius mínimo
│   ├── testing-policy.md       # Verificação determinística e proibição de fake pass
│   ├── security-policy.md      # Security by default e vetores de risco
│   └── git-safety.md           # Proteção de repositório e auditoria de diff
├── skills/                     # Habilidades invocáveis sob demanda
│   ├── clearer/                # Dispatcher e classificador de risco
│   ├── clearer-feature/        # Workflow de implementação de features
│   ├── clearer-bugfix/         # Workflow Root-Cause First para bugs
│   ├── clearer-refactor/       # Refatoração com baseline e preservação de contratos
│   ├── clearer-review/         # Revisão adversarial baseada no Git diff
│   ├── clearer-audit/          # Auditoria formal de claims vs evidências
│   ├── clearer-map/            # Mapeamento técnico read-only do codebase
│   └── clearer-test/           # Execução determinística de testes e captura de logs
├── agents/                     # Subagentes especializados do harness
│   ├── investigator/           # Descoberta de contexto e Evidence Pack (Read-only)
│   ├── architect/              # Análise de blast radius e Implementation Plan
│   ├── implementer/            # Implementação precisa sem refatorações fora de escopo
│   ├── test-engineer/          # Execução de testes e criação de casos de regressão
│   ├── reviewer/               # Revisão adversarial do diff (BLOCKER, HIGH, MEDIUM...)
│   └── evidence-auditor/       # Auditoria de claims e relatório final
├── scripts/                    # Utilitários executáveis de suporte
│   ├── detect-project.sh       # Detector agnóstico de stack, frameworks e ferramentas
│   ├── preflight.sh            # Inspeção de sanidade prévia do repositório
│   ├── safety-gate.py          # Safety Gate interceptador de comandos perigosos
│   ├── test-runner.sh          # Executor determinístico com saída padronizada
│   ├── diff-audit.sh           # Auditor de diff, markers de conflito e blast radius
│   └── evidence-report.sh      # Gerador de relatório no formato padrão CEH
└── tests/                      # Suíte de testes automatizados e adversariais
    ├── run-all-tests.sh        # Suíte de testes de integração e componentes
    └── run-adversarial-tests.sh# Validação dos 5 casos adversariais do PRD
```

---

## 3. O Protocolo CLEARER

Toda ação de engenharia passa pelas 7 etapas fundamentais:

- **C — Concrete Goal**: Objetivo concreto, arquivos envolvidos, restrições e condição de parada.
- **L — Load Context**: *Inspect before edit*. Detecção agnóstica de stack, convenções e testes existentes.
- **E — Explicit Boundaries**: Delimitação estrita de escopo e blast radius mínimo.
- **A — Anchors and Examples**: Código real, schemas e testes como única fonte da verdade.
- **R — Response Contract**: Toda execução gera um contrato verificável de saída.
- **E — Enable Evidence and Tools**: Observação direta sobre suposição; captura de saídas e logs reais.
- **R — Review and Validate**: Ciclo `INSPECT → PLAN → IMPLEMENT → TEST → REVIEW → AUDIT → REPORT`.

---

## 4. O Risk Dial

| Nível | Cenário de Aplicação | Requisitos do Processo |
|---|---|---|
| **LOW** | Extrações, leituras, renomeações locais, consultas. | Baixa sobrecarga, execução ágil, sem orquestração desnecessária. |
| **MEDIUM** | Features novas, correções de bugs, refatores, alterações em APIs ou banco. | Inspeção → Plano → Implementação → Testes → Diff Audit → Relatório. |
| **HIGH** | Autenticação, autorização, transações de pagamento, concorrência, migrações destrutivas, segurança. | Investigação profunda, subagentes especializados, revisão adversarial e auditoria formal. |

---

## 5. Semântica de Evidência e Auditoria de Claims

### Semântica de Fatos
- **`OBSERVED`**: Fato comprovado diretamente por arquivo lido, schema ou comando executado.
- **`INFERRED`**: Conclusão técnica deduzida a partir de dados observados (pendente de validação).
- **`UNKNOWN`**: Informação não encontrada no repositório.

> [!CRITICAL]
> **UNKNOWN nunca pode silenciosamente virar OBSERVED.**
> Se um método, tabela ou classe não for encontrado, registre como `UNKNOWN` ou `NOT FOUND`. Proibido inventar código inexistente (*hallucination coding*).

### Auditoria de Claims
Toda alegação é classificada como:
- **`SUPPORTED`**: Amparada por teste com exit code 0 ou linha de código inspecionada.
- **`PARTIALLY_SUPPORTED`**: Parcialmente comprovada com ressalvas explícitas.
- **`UNSUPPORTED`**: Rejeitada ou sem evidência verificável.

---

## 6. Papéis dos Agentes Especializados

```text
                    ┌─────────────────────────┐
                    │ CEH ORCHESTRATOR        │
                    └────────────┬────────────┘
                                 │
                     ┌───────────▼────────────┐
                     │ ceh-investigator       │ (Read-Only Context Discovery)
                     └───────────┬────────────┘
                                 │ Evidence Pack
                     ┌───────────▼────────────┐
                     │ ceh-architect          │ (Blast Radius & Plan)
                     └───────────┬────────────┘
                                 │ Implementation Plan
                     ┌───────────▼────────────┐
                     │ ceh-implementer        │ (Precision Coding)
                     └───────────┬────────────┘
                                 │ Diff
                  ┌──────────────┴──────────────┐
                  │                             │
         ┌────────▼────────┐           ┌────────▼────────┐
         │ceh-test-engineer│           │  ceh-reviewer   │ (Adversarial Review)
         └────────┬────────┘           └────────┬────────┘
                  │                             │
                  └──────────────┬──────────────┘
                                 │
                        ┌────────▼─────────┐
                        │ceh-evidence-audit│ (Claim ↔ Evidence Verification)
                        └────────┬─────────┘
                                 │
                           FINAL REPORT
```

---

## 7. Comandos e Exemplos de Uso

### Comandos de Terminal
```bash
# Iniciar Antigravity com o perfil CLEARER Harness
agy-ceh

# Iniciar em modo YOLO (auto-aprovando edições controladas)
agy-ceh-yolo

# Executar prompt direto com saída não-interativa
agy --agent clearer-harness -p "Mapeie a arquitetura deste projeto"
```

### Skills Invocáveis no Chat
- **`/clearer`**: Dispatcher inteligente que avalia a solicitação e define o Risk Dial.
- **`/clearer-feature`**: Fluxo estruturado para implementação de novas funcionalidades.
  ```text
  /clearer-feature "Implementar autenticação JWT no endpoint de login"
  ```
- **`/clearer-bugfix`**: Correção de bug Root-Cause First (Sintoma → Reprodução → Causa → Teste Red → Fix Green).
  ```text
  /clearer-bugfix "Corrigir cálculo de desconto quando o cupom expira às 23:59"
  ```
- **`/clearer-refactor`**: Refatoração segura com baseline de testes e preservação de contratos.
  ```text
  /clearer-refactor "Extrair lógica de cálculo fiscal para o serviço TaxCalculator"
  ```
- **`/clearer-review`**: Revisão adversarial do Git diff classificando findings em BLOCKER, HIGH, MEDIUM, LOW, INFO.
  ```text
  /clearer-review
  ```
- **`/clearer-map`**: Mapeamento técnico read-only do repositório (Stack, rotas, banco, testes e riscos).
  ```text
  /clearer-map
  ```
- **`/clearer-audit`**: Auditoria formal de claims vs evidências na entrega.
  ```text
  /clearer-audit
  ```
- **`/clearer-test`**: Execução determinística de testes e registro de evidências brutas.
  ```text
  /clearer-test
  ```

---

## 8. Segurança e Safety Gate

O CEH inclui um interceptador de segurança (`scripts/safety-gate.py`) acionado pelo hook `PreToolUse`:

- **`DENY` (Bloqueio Total)**: `rm -rf /`, `rm -rf ~`, `DROP DATABASE`, `mkfs`, `gcloud projects delete`, fork bombs.
- **`ASK` (Requer Confirmação)**: `rm -rf <dir>`, `git reset --hard`, `git clean -fdx`, `git push --force`, `migrate:fresh`, `db:wipe`, `terraform destroy`.
- **`ALLOW` (Permitido)**: Comandos de inspeção, testes (`npm test`, `pest`, `pytest`), linters e operações não destrutivas.

---

## 9. Testes e Validação do Harness

O harness inclui duas suítes de testes completas:

```bash
# 1. Executar testes de componentes e integração
./clearer-engineering/tests/run-all-tests.sh

# 2. Executar testes adversariais dos 5 casos do PRD
./clearer-engineering/tests/run-adversarial-tests.sh
```

Ambas as suítes rodam com **100% de aprovação**.

---

## 10. Desinstalação

Caso deseje remover o plugin e os perfis:
```bash
# Desinstalar via Antigravity CLI
agy plugin uninstall clearer-engineering

# Remover arquivos de configuração
rm -rf ~/.gemini/config/plugins/clearer-engineering
rm -rf ~/.gemini/config/agents/clearer-harness
```
