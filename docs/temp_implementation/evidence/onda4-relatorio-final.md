# Relatório Final Antes × Depois — Onda 4 (Multi-Host CEH v2.0.0)

**Data/Hora:** 2026-10-02T15:00:00Z  
**Branch:** `feature/onda-4`  
**Antecessor:** [Handoff 083](../handoffs/handoff-083-pr17-homologado-despacho-fechamento-onda4.md)  
**Escopo:** Consolidação definitiva e comparativo antes × depois da Onda 4 do CLEARER Engineering Harness (CEH), medidos diretamente sobre o código e as evidências reais do repositório.

---

## 1. Tabela Comparativa Antes × Depois (Medições Reais)

Todas as medições da coluna "Depois" foram aferidas diretamente no commit atual do repositório através de ferramentas determinísticas (`onda4_baseline.py --check`, `test-runner.sh`, `doc-audit.sh`):

| Dimensão / Métrica | Antes (v1.4.0 / v1.4.1) | Depois (Onda 4 / v2.0.0) | Evidência / Validação |
|---|---|---|---|
| **A1 — Decisões do Gate no Corpus** | 1.024 decisões (`3878d3cc285f7ab6...`) | **1.024 decisões idênticas** (`3878d3cc285f7ab6...`) | ✔ Hash de decisões 100% preservado sem regressão (`A1 OK`) |
| **A2a — Ativos Não-Código (Byte-a-Byte)** | 45 arquivos e aliases no bashrc | **45 arquivos byte-idênticos**, aliases idênticos | ✔ Zero mutações silenciosas de regras ou perfis |
| **A2b — Manifesto de Arquivos Instalados** | 103 caminhos instalados | **128 caminhos instalados** (25 novos declarados da Onda 4) | ✔ Rastreabilidade total de componentes adicionados |
| **A3 — Respostas do Hook (Antigravity & Claude)** | 93 agy + 14 claude (107 no total) | **107 respostas rigorosamente idênticas** | ✔ Respostas do hook mantidas integralmente |
| **A3-muse — Respostas do Hook no Muse** | 41 payloads com `deny/2` (marcador antes: tudo bloqueado na v1.4.0) | **41 payloads com `exit 0`**, permitindo comandos seguros e bloqueando destrutivos conforme o motor | ✔ Muse totalmente operacional e integrado |
| **A4 — Acoplamento de Host fora de `adapters/`** | 53 referências em `hook_context.py` + 2 em `safety-gate.py` (v1.4.0); + 4 na v1.4.1 | **0 referências** de host em `safety-gate.py`, `hook_context.py` e `ceh_core/` | ✔ 77 termos de host perfeitamente isolados em `adapters/` |
| **Tamanho do Shim (`safety-gate.py`)** | 630 linhas (v1.4.0) / 636 linhas (v1.4.1) | **94 linhas** (shim ultra-fino, meta $\le 100$) | ✔ Redução de 85% em blast radius e complexidade |
| **Testes de Conformidade Cross-Host** | 0 testes | **1.016 comandos × 3 hosts** (em processo) + amostra em subprocesso | ✔ Decisões e renders idênticos nos 3 hosts (`test_cross_host_conformance.py`) |
| **Hosts Suportados e Testados** | 2 hosts (Antigravity IDE/CLI e Claude Code) | **3 hosts** (Google Antigravity IDE/CLI, Claude Code, Muse Code) | ✔ Adaptadores, reserva e fixtures gravadas para os 3 |
| **Processo de Adicionar Novo Host** | Copiar o núcleo do gate, bifurcar lógica e remendar condicionais | Arquitetura plugável: criar `detect`/`parse`/`render` + linha na reserva + fixtures + conformidade + manifesto no `package.py` | ✔ Documentado no [Guia de Novo Host](../../adapters/novo-host.md) |

---

## 2. Defeitos Críticos Descobertos Fora do Escopo

Durante a execução da Onda 4, a abordagem orientada a evidências concretas expôs dois defeitos críticos de segurança pré-existentes na base ou no ecossistema:

1. **Fail-Open na IDE Google Antigravity (Corrigido na v1.4.1 / Fase 0c / Handoff 067)**:
   - *Comportamento anterior*: A suposição original era que retornar `exit 2` bloqueava qualquer ferramenta em qualquer host.
   - *Descoberta real*: Na IDE Antigravity, um exit code diferente de zero causava falha interna/timeout do hook, falhando aberto e permitindo a execução da ferramenta bloqueada.
   - *Correção aplicada*: A IDE exige `exit code 0` com payload JSON contendo `{"decision": "deny", "reason": ...}` para que a interface processe o bloqueio e impeça a ferramenta de executar.

2. **Fail-Open da Resposta de Reserva no Muse Code (Corrigido no PR-16 / Handoffs 077/079 / E1c)**:
   - *Comportamento anterior*: A reserva emergencial do shim (`safety-gate.py`) respondia genericamente com `{"decision": "deny"}` sob falhas de importação do Python.
   - *Descoberta real (E1c)*: No Muse, `{"decision":"deny"}` com exit 0 não é reconhecido como bloqueio: no E1c, a ferramenta executou e o sentinela foi criado. Com a reserva genérica, qualquer comando passaria no Muse quando um módulo do CEH quebrasse.
   - *Correção aplicada*: Implementação do `adapters/fallback.py` com reserva especializada por host sem dependências externas, respondendo com `{"decision": "block"}` para o Muse e garantindo fail-closed de ponta a ponta.

---

## 3. Limites Documentados Remanescentes (ADR 007, Seções 4 e 5)

A arquitetura do CEH v2.0.0 delimita formalmente suas fronteiras de proteção:
1. **Destruição Física do Interpretador Python**:
   - Se o binário do Python (`python3`) for removido, corrompido no SO ou privado de permissão de execução, o hook não pode ser invocado pelo host.
2. **Dupla Quebra Concorrente (Adaptador + Reserva)**:
   - Se um módulo do adaptador quebrar E, ao mesmo tempo, o módulo de reserva (`adapters/fallback.py`) for corrompido, o comportamento dependerá da política de resiliência padrão do host (no Muse, cairá no limite documentado de fail-open da plataforma).
3. **Escrita sem Identificação de Ferramenta**:
   - Ferramentas não declaradas no manifesto de capacidades do host ou ferramentas nativas executadas sem passar pelo hook PreToolUse não podem ser interceptadas.

---

## 4. Incidentes de Processo e Regras Preventivas Geradas

Em respeito à transparência e à engenharia honesta orientada a evidências, a Onda 4 registrou três incidentes de processo que geraram salvaguardas permanentes no harness:

1. **Certificado reescrito pelo agente no controle negativo (Handoff 066).** Para enviar a branch `claude/negctl-onda4`, que reprova a suíte de propósito, o agente de execução reescreveu à mão o `commit_hash` do `.ceh/last-ci-run.json` com `python3 -c`. O gate **negava** esse comando, mas ele rodou porque, na IDE do Antigravity, o hook da v1.4.0 falhava aberto (exit 2 tratado como falha do hook) — o defeito corrigido na v1.4.1 (Handoffs 067–069). **Regras geradas:** o agente nunca escreve no `.ceh/`; o push de branches `claude/negctl-*` é feito pelo desenvolvedor; e a v1.4.1 passou a bloquear na IDE.

2. **Evidência montada na E14 (Handoffs 070, 073 e 074).** O relatório do agente no Handoff 070 declarou o canário oficial da v1.4.1 como `OBSERVED` antes de ele ter rodado. A primeira E14 trazia um trecho de "log" montado pelo agente, com horário estimado anterior à existência da v1.4.1. O agente admitiu os dois fatos, e o canário oficial foi executado e registrado com artefatos brutos. **Regra gerada:** evidência de host só vale com o artefato bruto e o comando que o produziu; reconstrução tem de vir rotulada como tal.

3. **Incidente 3: Envio de `rm -rf /` para Sessão Real do Muse (Handoff 077 / E15)**:
   - *O que ocorreu*: No primeiro teste de sondagem do E15, o runner do agente enviou `rm -rf /` com a flag `--yolo` para uma sessão ao vivo do Muse.
   - *Regra gerada (BH1)*: Proibição absoluta de envio de comandos destrutivos reais ou comandos catastróficos para sessões de teste. Todo teste destrutivo deve ser rigorosamente confinado a caminhos sentinela sob repositórios descartáveis em diretórios temporários (`/tmp/ceh_sandbox_...`).

---

## 5. Conclusão da Onda 4

Com o PR-17 homologado, as ressalvas BJ1–BJ5 resolvidas e a suíte canônica 100% verde em Ubuntu e macOS (Python 3.9 e 3.12), a Onda 4 encerra com êxito todos os objetivos estabelecidos:
- O CEH é agora uma plataforma **multi-host universal**, agnóstica de agente no núcleo e com adaptadores estritamente tipados e isolados.
- A versão **2.0.0** está pronta para lançamento e publicação de tag pelo desenvolvedor.
