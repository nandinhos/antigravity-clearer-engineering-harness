# HANDOFF — Dinâmica de Execução, Bloqueios e Handoffs no CLEARER Engineering Harness (CEH)

> **Data:** 2026-08-30
> **Origem da Discussão:** Alinhamento operacional com o usuário sobre comportamento autônomo vs. handoffs
> **Objetivo:** Contextualizar o agente sobre as razões pelas quais o harness entra em modo de handoff/planejamento, o comportamento no modo YOLO e como operar/ajustar essa dinâmica.

---

## 1. Contexto do Problema / Dúvida do Usuário

O usuário questionou o motivo de o agente interromper a execução de comandos e emitir *handoffs* ou pedidos de autorização, mesmo quando a sessão é iniciada em **modo YOLO** (`agy-ceh-yolo` / `--auto-approve`).

Este documento registra a anatomia completa das travas arquiteturais e cognitivas para que qualquer agente que assuma o projeto do CEH compreenda a intenção e saiba como responder, debugar ou refinar o harness.

---

## 2. Anatomia das Travas: Por que o agente para e gera Handoff?

O comportamento de parada/handoff decorre de uma sobreposição de 4 camadas distintas:

```
┌────────────────────────────────────────────────────────┐
│ 1. Antigravity Runtime (Planning Mode & Cwd Sandbox)  │
└──────────────────────────┬─────────────────────────────┘
                           ▼
┌────────────────────────────────────────────────────────┐
│ 2. CEH Safety Gate Hook (PreToolUse / safety-gate.py) │
└──────────────────────────┬─────────────────────────────┘
                           ▼
┌────────────────────────────────────────────────────────┐
│ 3. CEH Prompt & Risk Dial (Fail-Closed Engineering)    │
└──────────────────────────┬─────────────────────────────┘
                           ▼
┌────────────────────────────────────────────────────────┐
│ 4. Ralph Method / BC Harness (Gate 5 - Curation)       │
└────────────────────────────────────────────────────────┘
```

### A. O papel e o limite do Modo YOLO (`agy-ceh-yolo`)
* **O que o modo YOLO faz:** Desativa a confirmação interativa do usuário na interface para chamadas de ferramentas comuns (auto-approve das tool calls no cliente Antigravity).
* **O que o modo YOLO NÃO faz:**
  1. Não altera os prompts cognitivos do modelo (as regras de engenharia e prevenção de alucinações continuam ativas).
  2. Não desativa os hooks em nível de sistema (`PreToolUse` em `hooks.json`).
  3. Não transforma subagentes analíticos (read-only) em executores.

---

### B. As 4 Camadas de Bloqueio em Detalhes

#### 1. Topologia de Subagentes Read-Only (CEH)
* **`ceh-investigator`**, **`ceh-architect`**, **`ceh-reviewer`**: têm no seu system prompt a proibição expressa de executar alterações ou comandos modificadores. O contrato deles é gerar um *Evidence Pack* ou um *Implementation Plan*.
* **Efeito:** Se a orquestração parar nesses subagentes sem transferir a execução para o `ceh-implementer`, a resposta final visível para o usuário será apenas o relatório/handoff.

#### 2. Princípio *Fail-Closed* e o *Risk Dial* (CEH Rules)
* **Regra Fundamental:** *"Diante de ausência de evidência, ambiguidade crítica ou falha de teste: BLOQUEIE, PERGUNTE OU REPORTE UNKNOWN. NUNCA PRESUMA SUCESSO."*
* **Risk Dial (`MEDIUM` / `HIGH`):** Tarefas com risco médio/alto (banco de dados, infraestrutura, Docker, credenciais, VPS) forçam o agente a planejar antes de executar. O agente não assume premissas não evidenciadas.

#### 3. Safety Gate em Nível de Hook (`hooks.json` → `safety-gate.py`)
* O hook `PreToolUse` monitora todas as chamadas a `run_command`.
* Padrões de bloqueio rígido (ex: remoção de diretório raiz, exclusão estrutural de banco de dados, formatação de disco) retornam `deny`.
* Padrões de confirmação (ex: comandos destrutivos de git, migrações com wipe, prune geral de docker) retornam `ask`, interceptando o comando mesmo em sessões automatizadas.

#### 4. Planning Mode do Antigravity Runtime
* Em tarefas não triviais, o runtime do Antigravity instrui o agente a criar o `implementation_plan.md` e parar aguardando autorização expressa do desenvolvedor antes de modificar arquivos.

#### 5. Gate de Curadoria do Ralph Method / BC Harness
* Quando um workflow via Ralph é concluído ou atinge dependências externas (DNS, troca de senhas mestras, SSH externo fora da sandbox), o **Gate 5 (`curation`)** gera um `HANDOFF.md` formal e encerra o ciclo autônomo.

---

## 3. Diretrizes para Futuras Interações com o Usuário (Guia do Agente)

Ao interagir com o usuário no contexto do projeto CEH:

1. **Reconhecer a intenção:** O usuário busca agilidade máxima com excelência técnica, esperando que o agente opere de forma contínua em tarefas de nível `MEDIUM` sem burocracia, mantendo os guardrails de segurança ativos.
2. **Como operar a autonomia:**
   * Tarefas **`LOW`** e **`MEDIUM`**: Executar o ciclo CLEARER completo em turno único (`Single-Turn End-to-End`). Inspecionar, planejar, codificar com alto nível (Clean Code/SOLID/tipagem estrita), testar, auditar diff e entregar o Response Contract.
   * **Gestão por Exceção**: Parar e emitir handoff **apenas** diante de: (1) ambiguidade de requisitos sem resposta no repositório, (2) disparo do Safety Gate (`DENY`/`ASK`), (3) falha persistente de testes após 1 iteração de auto-reparo, ou (4) risco `HIGH` explícito.
3. **Comunicação:** Manter o padrão em **Português do Brasil (pt-BR)** e fornecer diagnósticos com evidências reais de código/execução.

---

## 4. Estratégia Implementada: Automação Controlada por Evidências (2026-08-31)

Para resolver a fricção entre autonomia e governança, a seguinte arquitetura foi implementada no harness:
1. **Regras Globais (`AGENTS.md` e `rules/`)**: Formalização da execução contínua em nível MEDIUM e padrões de craftsmanship de Staff Engineering.
2. **Skills (`clearer-feature`, `clearer-bugfix`, `clearer-refactor`, `clearer`)**: Ajustadas para conduzir o ciclo completo sem paradas intermediárias artificiais.
3. **Safety Gate Inteligente (`safety-gate.py`)**: Suporte a limpezas de cache/scratch/build de desenvolvimento e operações atômicas no Git, preservando bloqueios rígidos contra perda de dados.
4. **Padrões de Código (`docs/coding_standards.md`)**: Diretrizes explícitas de Clean Code, tipagem estrita, resiliência defensiva e testes comportamentais.

