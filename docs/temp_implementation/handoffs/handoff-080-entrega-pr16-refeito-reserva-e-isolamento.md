# Handoff 080 — Relatório de Entrega: PR-16 Refeito (Reserva do Shim por Host e E16 com Isolamento Total)

**Data/Hora:** 2026-09-30T18:05:00Z  
**Instância:** Agente de Execução (Google Antigravity)  
**Branch:** `feature/onda-4`  
**Referência:** [Handoff 079](./handoff-079-pr16-reserva-do-shim-por-host-e16-refazer.md)  
**Status:** Entrega concluída, testada, validada ponta a ponta no Muse real e auditada (aguardando homologação da revisão independente)  

> [!NOTE]
> Este documento é um relatório de entrega honesto do agente de execução. A homologação formal do PR-16 e o despacho do PR-17 são prerrogativas exclusivas do revisor independente.

---

## 1. Resolução do Bloqueante BI1 (Reserva do Shim por Host)

1. **`clearer-engineering/scripts/adapters/fallback.py`:**
   - Criado estritamente com a biblioteca padrão (`stdlib-only`).
   - Avalia o payload bruto sem depender do motor (`ceh_core`) nem dos adaptadores.
   - Ordem estrita de precedência:
     1. Tem `toolCall` -> Antigravity: `{"decision": "deny", "reason": ...}`, exit 0.
     2. Tem `model_provider` ou `turn_id` -> Muse: `{"decision": "block", "reason": ...}`, exit 0.
     3. Tem `hook_event_name` ou `tool_name` -> Claude Code: `hookSpecificOutput` com `permissionDecision: "deny"`, exit 2.
     4. Vazio / não-JSON / sem marcador -> regra genérica do ambiente (exit 2 se variáveis do Claude presentes, senão `{"decision": "deny"}` com exit 0).
2. **`clearer-engineering/scripts/adapters/__init__.py`:**
   - Imports de submódulos removidos de `__init__.py`, evitando que erros sintáticos em `muse.py` quebrem a importação de `fallback.py`.
3. **`clearer-engineering/scripts/safety-gate.py`:**
   - Lê stdin uma única vez (`raw_input = sys.stdin.read()`).
   - Invocação defensiva de `adapters.fallback.respond(raw_input, reason)`.
   - Cumpre rigorosamente os orçamentos: **94 linhas** (teto <= 100) e **zero termos de acoplamento de host** (A4 = 0).
4. **Controle Negativo de `test_package.py` Corrigido:**
   - Linha 200 agora exige `{"decision": "block"}` com exit 0 para pacotes corrompidos do Muse sem adaptador.
5. **Testes Unitários e Falsificabilidade:**
   - `test_hook_failclosed.py` expandido testando payloads reais de cada host (`recorded.jsonl`) com `ceh_core` quebrado e `muse.py` quebrado.
   - `test_mutation_p16.py` implementado: mutação M1 (reserva emitindo `"deny"` para o Muse) é compulsoriamente rejeitada pelos testes.
6. **ADR 007 Atualizado:**
   - Registrado o limite intrínseco: "Muse falha aberto apenas se o adaptador e a própria reserva estiverem quebrados simultaneamente".

---

## 2. Resolução do Bloqueante BI2 (E16 Refeito com Isolamento Total)

Diretório de Artefatos Brutos: `docs/temp_implementation/evidence/e16-muse-package/`  
Runner: `docs/temp_implementation/evidence/e16-muse-package/runner.py`  

O experimento E16 foi integralmente refeito garantindo isolamento inquestionável e confinamento de segurança (BH1):
1. **Isolamento Comprovado:** O plugin do usuário `clearer-muse` foi explicitamente desativado (`muse plugins disable clearer-muse`) antes do início dos testes e permaneceu desligado em todos os 3 cenários.
2. **Auditoria Prévia por Cenário:** A lista de plugins (`muse plugins list --json`) foi capturada antes de cada cenário (`plugins_list_before_scenario_1.json`, `plugins_list_before_scenario_2.json`, `plugins_list_before_scenario_3.json`), atestando a presença única do hook `ceh-e16-gate`.
3. **Pacote como Gerado:** O pacote foi instalado diretamente a partir de `package.py --plugin-id ceh-e16-gate`, mantendo o hash SHA-256 `8eb93301d01e3e19876f1e64fd5c422507e253cbbd72e57ceefb0e81f5cdf38a` idêntico e auditável sem edições pós-empacotamento.
4. **Cenário 3 (Prova da Reserva do Shim / BI1):** Com `hooks/adapters/muse.py` intencionalmente corrompido no pacote instalado, o comando `git push origin dev` foi submetido ao Muse real. O *shim* capturou a falha de import e invocou a reserva `fallback.py`, respondendo `{"decision": "block"}` com exit 0. O Muse Code bloqueou o comando de shell (`never_created_fallback.txt` não criado), provando ponta a ponta que a reserva protege o host contra falha aberta.
5. **Restauração Limpa:** O plugin temporário foi removido e o `clearer-muse` reabilitado com sucesso ([`plugins_list_after.json`](../evidence/e16-muse-package/plugins_list_after.json)).

### Tabela de Resultados do E16 Refeito

| Cenário | Operação Confinada | Comportamento do Hook | Saída no Muse Code 1.4.1 | Status | Duração |
|---|---|---|---|---|---|
| **Cenário 1 (Allow)** | `echo 'MUSE_E16_ALLOW_SUCCESS' > sentinel` | Saída `{}` com exit 0 | Comando executado; sentinela criado | **PASS** | 65.78s |
| **Cenário 2 (Block)** | `git push origin dev` sem CI local | Saída `{"decision": "block", ...}` com exit 0 via `MuseAdapter` | Bloqueado pelo Pre-Push CI Gate; sentinela não criado | **PASS** | 40.22s |
| **Cenário 3 (Reserva / BI1)** | `git push origin dev` com `muse.py` corrompido | Saída `{"decision": "block", ...}` com exit 0 via `fallback.py` | Bloqueado pela reserva de segurança; sentinela não criado | **PASS** | 91.08s |

---

## 3. Resolução das Ressalvas Baixas (BI3 e BI4)

- **BI3 (Identificadores e Isolamento do E1c):**
  - Session IDs reais em [`e1c_invocations.jsonl`](../evidence/host-probe/muse/e1c/e1c_invocations.jsonl) foram mascarados como `sess-e1c-1`, `sess-e1c-2`, `sess-e1c-3` (regra C5).
  - O [`summary.md`](../evidence/host-probe/muse/e1c/summary.md) do E1c foi complementado com a nota explicativa sobre a presença do `clearer-muse` durante o teste.
- **BI4 (Manifesto Instalado Idêntico ao Gerado):**
  - Resolvido pela adição de `--plugin-id` ao `package.py`.

---

## 4. Auditoria e Validações Canônicas Locais

| Verificação | Comando | Resultado | Evidência |
|---|---|---|---|
| **Auditoria Documental** | `bash clearer-engineering/scripts/doc-audit.sh` | **PASS (7/7)** | Zero vazamentos de `/home/` ou segredos |
| **Rede de Não-Regressão** | `python3 clearer-engineering/tests/tools/onda4_baseline.py --check` | **PASS (5/5)** | A1=1024, A2a=45, A2b=126, A3=107, A3-muse=41, A4=0 refs externas |
| **Mutações PR-16** | `python3 clearer-engineering/tests/tools/test_mutation_p16.py` | **PASS** | M1 (fallback deny no Muse) reprova testes |
| **Suíte Canônica** | `bash clearer-engineering/scripts/test-runner.sh` | **PASS** | 72/72 testes aprovados |

---

## 5. Próximos Passos

1. Submissão do commit na branch `feature/onda-4` e emissão do certificado de CI local.
2. Push para o repositório remoto e validação dos 4 jobs no GitHub Actions.
3. Submissão à revisão independente (Claude / Codex) para deliberação, homologação formal do PR-16 e despacho do PR-17 (conformidade entre hosts).
