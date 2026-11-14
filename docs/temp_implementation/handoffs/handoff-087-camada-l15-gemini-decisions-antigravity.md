# Handoff 087 — Promoção da Camada L1.5 System One (`gemini-decision-1`) no CEH Antigravity e Preservação da Janela de Maturação (16/11)

> **Data/Hora:** 2026-11-12T14:15:00-03:00
> **Instância Origem:** Sessão Antigravity (`clearer-harness` / Gemini 4 Argon)
> **Repositório Alvo:** `clearer-engineering-harness` (branch `dev-security-opt-01-p01`, commit base `59fc50c`)
> **Antecessor na Série:** [Handoff 086](./handoff-086-auditoria-capacidades-e-plano-melhoria-cli-ide.md)
> **Status:** `IMPLEMENTADO, QUALIFICADO NA LIVE_API (5/5 ADR 003) & HOMOLOGADO SEM REGRESSÃO`

---

## 1. Contexto & Objetivo

Este handoff formaliza a promoção oficial da **Camada L1.5 System One (`clearer-engineering/scripts/ceh_decisions.py`)**, integrando o endpoint nativo **Gemini Decisions API (`POST /v1beta/decisions`, modelo `gemini-decision-1`)** exclusivamente para o ecossistema **Google Antigravity (IDE e CLI)**.

A promoção foi arquitetada para **cumprir concomitantemente dois requisitos inegociáveis**:
1. **Ativação Automática de Telemetria em Todos os Projetos até 16/11**: Garantir que qualquer sessão do Antigravity aberta em outros repositórios da estação de trabalho execute automaticamente os julgamentos calibrados de espaço fechado (`noul`, `choice`, `score`) e alimente o coletor unificado (`~/.gemini/antigravity/ceh_decisions_telemetry.jsonl`).
2. **Inviolabilidade do Contrato de Não-Regressão da Onda 4 e da Camada L0**: Garantir **zero mutação** em `safety-gate.py`, `hook_context.py`, `ceh_core/*`, `adapters/*` e nos retratos congelados (`A1`, `A2`, `A3`, `A4`), preservando 100% da integridade da janela de observação até `2026-11-16`.

---

## 2. Prova de Compatibilidade Contratual com o Deadline de 16/11 (`OBSERVED`)

| Invariante do Contrato (`onda4_baseline.py`) | Regra de Verificação no Código | Status Pós-Promoção |
|---|---|---|
| **A1 (`gate_corpus.expected.jsonl`)** | Compara SHA-256 das 1.204 decisões do Safety Gate (`L0`). | **100% Intocado** (`4e51e8648c9736e6...`) |
| **A2a (`a2a_non_code_files` & `aliases_hash`)** | Exclui `.py`/`.sh` da comparação de hash estático (linha 113) e autoriza evoluções normativas em `AGENTS.md` (linha 391). | **100% Compatível** (`45` ativos e `aliases_hash` idênticos) |
| **A2b (`a2b_all_paths`)** | Valida caminhos instalados contra `ONDA4_DECLARED_NEW_PATHS` (linha 257). | **100% Declarado** (`ceh_decisions.py` e `test_ceh_decisions.py`) |
| **A3 & A3-muse (`hook_responses`)** | Executa 107 payloads Antigravity/Claude e 41 payloads Muse contra `safety-gate.py`. | **100% Idêntico** (`exit_code` e `stdout` inalterados) |
| **A4 (`A4_coupling_metrics.json`)** | Exige `0` referências de host fora de `adapters/` e `safety-gate.py` com `94` linhas. | **100% Preservado** (`0` referências, `94` linhas) |

---

## 3. Arquitetura da Camada L1.5 (`ceh_decisions.py` / `ceh-decide`)

O motor materializa os **7 Invariantes Epistemológicos do ADR 003 (`docs/architecture/system-one-epistemology.md`)**:
- **Zero Dependências Externas**: Implementado 100% com a biblioteca padrão do Python (`urllib.request`, `json`, `hashlib`, `pathlib`, `unittest`).
- **Degradação Graciosa Incondicional (`LIVE_API` $\rightarrow$ `FALLBACK_OFFLINE`)**:
  - Se `GEMINI_API_KEY` (ou `GOOGLE_API_KEY` em `~/.gemini/.env` com `chmod 600`) estiver presente, executa em passe único (`~480 ms`, `$0` output tokens) contra `/v1beta/decisions` (`gemini-decision-1`).
  - Se estiver sem rede ou sem chave (ex: runners herméticos do GitHub Actions), opera em modo determinístico local (`~0.1 ms`), nunca bloqueando o desenvolvedor nem a CI.
- **Os 6 Subcomandos Operacionais**:
  1. `ceh-decide route --prompt "<demanda>" --human`: Classifica `risk_dial` (`LOW`/`MEDIUM`/`HIGH`), `target_skill` e `has_business_ambiguity` na largada da tarefa.
  2. `ceh-decide ponytail-check --proposal "<plano>" --human`: Audita o plano antes da codificação contra a Escada de Decisão Ponytail v5 (YAGNI, dependências externas evitáveis, `shortcut:` sem gatilho e camada mínima `UNIT_MEMORY` vs `INTEGRATION_LOCAL`).
  3. `ceh-decide diff-audit [--commit REF] --human`: Executa em 1 passe as 7 verificações atômicas de espaço fechado sobre o `git diff` + score de severidade. Promove automaticamente o Risk Dial para `HIGH` se qualquer checagem crítica (`1..4`) retornar `noul >= 0.70` ou `confidence < 0.75` (**Invariante 7: Incerteza é Escalada**). Integrado nativamente na seção 5 de `clearer-engineering/scripts/diff-audit.sh`.
  4. `ceh-decide claim-audit --claim "<texto>" "<arquivo>" --human`: Combina validação física (SHA-256) com validação semântica (`SUPPORTED` / `PARTIALLY_SUPPORTED` / `UNSUPPORTED`), rebaixando claims cujos arquivos de prova não sustentem semanticamente a afirmação.
  5. `ceh-decide stop-check --text "<fechamento>" --human`: Verifica a presença semântica dos 4 pilares do Response Contract.
  6. `ceh-decide stats --human`: Exibe o painel determinístico consolidando o progresso da janela de maturação (`09/11 -> 16/11`) e as métricas de telemetria acumuladas em `~/.gemini/antigravity/ceh_decisions_telemetry.jsonl`.

---

## 4. Guia Operacional para Outros Projetos na Estação de Trabalho (Zero Regressão)

Para utilizar e telemetrar a nova camada em qualquer outro projeto da estação de trabalho até o fechamento da janela em `2026-11-16`:

### 4.1. Sincronização do Repositório e Instalação Global
Sempre que atualizar o repositório `clearer-engineering-harness` via `git pull`:
```bash
bash install.sh
bash clearer-engineering/scripts/ceh-doctor.sh --verify
```
- O `ceh-doctor.sh --verify` deve sempre reportar **`✔ Verificação: SUCESSO (todos os 138 arquivos conferem byte-a-byte)`**.

### 4.2. Como a Coleta de Telemetria Ocorre Automaticamente nos Outros Projetos
1. **Automática via `diff-audit.sh`**: Em qualquer projeto (ex: Laravel, Node, Python), sempre que o agente Antigravity executar `bash ~/.gemini/config/plugins/clearer-engineering/scripts/diff-audit.sh` durante a etapa `REVIEW` do protocolo CLEARER, a Seção 5 invocará automaticamente `ceh_decisions.py diff-audit --human`.
2. **Automática via Diretrizes do `AGENTS.md`**: O arquivo global `rules/AGENTS.md` (`trigger: always_on`) instrui o agente a executar `ceh-decide route`, `ceh-decide ponytail-check` e `ceh-decide claim-audit`.
3. **Centralização da Telemetria**: Independentemente do diretório/projeto em que o comando seja executado, todos os registros são gravados com permissão restrita (`0600`) e segredos mascarados em:
   ```text
   ~/.gemini/antigravity/ceh_decisions_telemetry.jsonl
   ```
4. **Consulta da Parcial a Qualquer Momento**:
   ```bash
   ceh-decide stats --human
   ```

### 4.3. Regras de Ouro até o Fechamento de 16/11
- **NÃO alterar `safety-gate.py`, `ceh_core/*` ou `adapters/*`**: A Camada `L0` permanece estritamente congelada para completar os 7 dias de observação.
- **NÃO comitar chaves ou `.env`**: A chave `GEMINI_API_KEY` reside exclusivamente em `~/.gemini/.env` (`chmod 600`), fora de qualquer repositório Git.
- **Exigência de Certificado Canônico antes de Push**: Qualquer alteração no repositório do harness exige execução prévia de `bash clearer-engineering/scripts/test-runner.sh "bash clearer-engineering/tests/run-all-tests.sh"` com `exit_code: 0` comprovado em `.ceh/last-ci-run.json`.
