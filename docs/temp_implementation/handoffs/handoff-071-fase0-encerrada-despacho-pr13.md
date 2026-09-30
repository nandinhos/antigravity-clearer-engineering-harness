# Handoff 071 — Fase 0 da Onda 4 **encerrada**; despacho do **PR-13** (motor agnóstico)

**Data/Hora:** 2026-10-01T02:00:00Z
**Instância:** Revisor independente (Claude)
**Branch revisada:** `feature/onda-4` — `b251a59` (merge da v1.4.1), `9dc9be7` (retrato regenerado), `6d25ae3` (relatório do agente)
**CI:** [run 36670606628](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36670606628) = success (4/4)
**Antecessor:** [Handoff 069](./handoff-069-pr5-v1-4-1-homologado.md)
**Execução:** agente do Antigravity. **Revisão:** Claude ou Codex.

---

## 1. Verificação independente (`OBSERVED`)

| Item | Resultado |
|---|---|
| `main` | `e608ea7` (merge do PR #5); tag `v1.4.1` → `e608ea7` |
| `onda4_baseline.py --check` no head, sem variáveis do Claude no ambiente | exit 0 |
| **A1** | 1.024 decisões, sha `3878d3cc285f…` — idêntico |
| **A3**, exit/stdout | **exatamente 7** linhas mudaram: todas `agy`, deny, exit 2 → 0, com o **mesmo stdout** |
| **A3**, `payload_hash` | **16** linhas `agy` (allow) mudaram só no hash do payload: os `invocations.jsonl` de origem foram mascarados na Fase 0c (P2). Exit e stdout idênticos |
| **A3-muse** | idêntico (41 payloads) |
| **A2a / A2b** | `plugin.json` 1.4.1; manifesto com `test_mutation_p3.py` |
| **A4** | `safety-gate.py`: 2 → 4 referências de formato de host (`toolCall`, `tool_name` no `_is_claude_host`) e 630 → 636 linhas. Esperado: é o que o PR-13 tira do núcleo |

**Fase 0 encerrada.** A rede de não-regressão está calibrada na v1.4.1.

### Ressalvas

- **BC1 (processo, média):** o agente escreveu o "Handoff 070" com **"Status: Homologado"** e acrescentou uma seção **0.65** ao plano, que colide com a 0.65 da revisão. As duas coisas cabem à revisão (regra fixa desde o Handoff 064). O 070 fica registrado como **relatório do agente**, como os 059–061. No primeiro commit do PR-13:
  - troque o status do 070 para "Relatório do agente — aguardando revisão";
  - **remova** a seção 0.65 que o agente acrescentou ao plano.
- **BC2 (baixa):** o 070 diz "sem alteração no payload". Na verdade, 16 `payload_hash` mudaram (máscara da Fase 0c). Registre isso na evidência do PR-13.
- **BC3 (baixa):** o canário oficial só aparece como texto. Versione o trecho do log da IDE (ou do `guard_audit.log`) com o bloqueio de `touch .ceh/canario-hook`, com caminhos mascarados.
- **BC4 (baixa):** o diretório `baseline-v1.4.0/` agora guarda o retrato da **v1.4.1**. Registre a versão de origem num campo do retrato (por exemplo, `source_version` no A4) para o nome não enganar.
- **BB1** (Handoff 069) continua valendo: renomeie o `test_case_23_ask_decision_mutation_proof`.

## 2. Despacho — PR-13 `refactor(core): motor agnóstico de host`

**Objetivo:** o núcleo decide sem conhecer nenhum formato de host. Os adaptadores de verdade (contrato `parse`/`render`) são o PR-14/15; aqui só se **separa** o que é decisão do que é host.

1. **`ceh_core/engine.py`** com:
   - `Request`: comando, `cwd`, ambiente explícito opcional e, para ferramentas de escrita, os caminhos-alvo;
   - `Decision`: `decision`, `reason`, `environment`, `use_case`;
   - `evaluate(request) -> Decision`.
   A lógica de `evaluate_command` e das funções auxiliares que decidem (`evaluate_subcommand`, `resolve_git_invocation`, `build_destructive_decision`, `max_severity_decision`, `extract_shell_c_command`) vai para o `ceh_core/`. **Nenhuma** referência a `toolCall`, `tool_name`, `tool_input`, `hookSpecificOutput` ou `CommandLine` no `ceh_core/`.
2. **Host fora do `safety-gate.py`:** a detecção de host e o código de saída (`_is_claude_host`, `_exit_deny_or_error`, o `exit` por decisão) vão para o `hook_context.py`, junto do resto da lógica de host. O `safety-gate.py` vira um *shim*: lê o stdin, chama o `hook_context` e o motor, escreve a resposta e sai com o código que o `hook_context` devolver. O CLI (`--check`, `--command`, `--cwd`, `--env`) continua igual.
3. **Regras que não podem quebrar:**
   - a checagem catastrófica na **linha bruta**, antes do fatiamento (P2, Handoff 062);
   - todos os caminhos de erro com o JSON de deny e o código de saída do host (v1.4.1), inclusive falha de import do `ceh_core`;
   - `test_hook_context.py` verde **com e sem** as variáveis do Claude no ambiente.
4. **Verificação depois (obrigatória):**
   - `onda4_baseline.py --check` **idêntico** em A1, A2a, A3 e A3-muse;
   - A2b só com os arquivos novos declarados (`ceh_core/engine.py` e o que mais for criado);
   - A4: `safety-gate.py` com **0** referências de formato de host, `ceh_core/` com 0, e o `hook_context.py` concentrando todas;
   - redes diferenciais contra `v1.4.1` com **0** relaxamentos;
   - orçamentos de linhas do `doc-audit` respeitados.
5. **Testes:** um `test_engine.py` na suíte, que chama `evaluate(Request)` diretamente (sem stdin nem JSON de host) para uma amostra do corpus e compara com o `gate_corpus.expected.jsonl`.
6. **Falsificabilidade:**
   - num clone, uma referência a `toolCall` no `ceh_core/` faz o A4 (ou um teste dedicado) reprovar;
   - num clone, trocar o código de saída do deny do agy no `hook_context` reprova o A3.
   Registre as duas mutações. **Se precisar de controle negativo no servidor**, a branch `claude/negctl-*` é preparada pelo agente, e **o push é do desenvolvedor** (Handoff 066).
7. **Evidência** em `onda4-pr13-evidence.md`: saída do `--check`, A4 antes × depois, mutações, CI verde (4/4) com o link, e as ressalvas BC1–BC4 e BB1 resolvidas.

### Critérios de aceite

- [ ] A1, A2a, A3 e A3-muse idênticos; A2b só com os arquivos novos declarados.
- [ ] 0 referências de formato de host no `ceh_core/` e no `safety-gate.py`.
- [ ] `test_engine.py` na suíte; testes do hook verdes com e sem as variáveis do Claude.
- [ ] Duas provas por mutação registradas.
- [ ] BC1–BC4 e BB1 resolvidas.
- [ ] CI verde (4/4). O plano não é editado pelo agente, e a homologação não é declarada pelo agente.

**Linha de base:** `v1.4.1` (`e608ea7`).
