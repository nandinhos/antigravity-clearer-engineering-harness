# Handoff 036 — PR-08 homologado com ressalvas; despacho do PR-08b e do PR-09

**Data/Hora:** 2026-09-27T12:00:00Z
**Instância:** Revisor sênior
**Branch:** `claude/code-review-technical-analysis-kfwcdl`
**Commit revisado:** `921a649` (PR-08)
**Antecessor:** [Handoff 035](./handoff-035-encerramento-onda-1-despacho-pr08.md)

---

## 1. Veredito: **HOMOLOGADO COM RESSALVAS**

Reproduzido de forma independente (`OBSERVED`), num repositório-fixture com CI, certificado do HEAD e a branch `outro` não certificada:

| Resultado | Comandos |
|---|---|
| **deny** | `outro:main`, `outro`, `+outro:main`, `refs/heads/outro:refs/heads/main`, `main~1:main`, `outro^{commit}:main`, a tag `v-new` (em `outro`), `--all`, `--mirror`, `--tags`, `--force-with-lease … outro:main`, `--repo=origin outro:main`, `-o ci.skip …`, `--push-option=x …`, push para uma URL, `main outro:dev` |
| **allow** | `origin main`, `HEAD:main`, `HEAD~0:main`, a tag `v-old` (no HEAD certificado), `--follow-tags origin main`, `git push`, `git push origin` |
| **fail-closed** | `"$(git rev-parse outro)":main` → PARSER_FAIL_CLOSED |

- **Falsificabilidade:** num clone, desliguei a comparação em `push.py:242`. O `test_pre_push_refspecs.py` reprova 3 testes, a mesma saída da evidência, e o `cluster4_acceptance.py` também reprova.
- **G7:** o `cluster4_acceptance.py` não tem mais nenhum `@expectedFailure`. A única mudança no corpus é `INT-G7_RED` allow→deny, um aperto esperado.
- **Módulo novo:** `push.py` com 256 linhas; o `safety-gate.py` caiu para 584.

**Linha de base avançada** para `921a649`.

## 2. Ressalvas

### AJ1 — ALTO (processo): o teste novo não roda na suíte oficial

O `test_pre_push_refspecs.py` **não está registrado** no `run-all-tests.sh` (o log mostra edições nesse arquivo que não entraram no commit). A suíte que emite o certificado e roda no CI **não executa** o teste. Na suíte oficial, só o caso `outro:main` (do `cluster4`) protege o G7. `--all`, `--forc`, `git -C` e `cd` ficam sem rede. A evidência "55/55" é verdadeira, mas não cobre o PR-08.

### AJ2 — MÉDIO (preexistente, área do push): apagar a branch remota passa em produção

`git push origin :main`, `git push origin --delete main` e `git push -d origin main` saem **allow em produção** e em staging, iguais em `9dfc85a`. Já o `git branch -D` local sai deny em produção. Apagar a `main` remota é pelo menos tão destrutivo quanto isso.

## 3. Despacho — dois commits nesta rodada

### Commit 1 — PR-08b `fix(gate): suíte oficial com os testes de push e deleção remota graduada`

1. **AJ1:** registre `test_pre_push_refspecs.py` no `run-all-tests.sh` e atualize a contagem no `plano-validacao-revisao-conselho-seniors.md`, que o `doc-audit` confere.
   - **Regra daqui em diante:** todo arquivo `tests/test_*.py` novo entra no `run-all-tests.sh` no mesmo commit.
   - Acrescente ao `doc-audit` uma checagem que falha se algum `tests/test_*.py` ou `tests/cluster*_acceptance.py` **não** for citado no `run-all-tests.sh`. Isso fecha a classe de "teste órfão".
2. **AJ2:** deleção remota (`:dst`, `+:dst`, `--delete dst`, `-d dst`, e as abreviações de `--delete`) passa a ser `GIT_HISTORY`, com a mesma graduação do `git branch -D`: DEV allow, HML ask, PROD deny. Casos no `test_pre_push_refspecs.py`.
   - **Falsificabilidade:** mostre a checagem nova do `doc-audit` reprovando quando o teste é removido do `run-all-tests.sh`.

### Commit 2 — PR-09 `fix(hook): fail-closed em payload vazio ou sem comando`

**Estado atual (`OBSERVED`, `safety-gate.py` em modo hook via stdin):**

| Payload | Hoje |
|---|---|
| vazio | `{"decision": "allow"}`, exit 0 |
| `{}` | allow, exit 0 |
| `{"toolCall":{}}` / `{"toolCall":{"name":"run_command","args":{}}}` | allow, exit 0 |
| `{"tool_name":"Bash","tool_input":{}}` / `…{"command":""}` | `{}` (allow no Claude), exit 0 |
| `nao-json` | deny, exit 2 (correto) |

O `hooks.json` só aciona o hook para `run_command`. Portanto, **toda** chamada sem comando é anômala.

1. **Regra:**
   - payload vazio, não objeto, sem ferramenta identificável, ou de ferramenta de terminal (`run_command` no agy, `Bash` no Claude) **sem comando não vazio** → deny, com motivo explícito, e **exit 2**;
   - sem host identificável, o formato é `{"decision": "deny", "reason": …}`. O exit 2 bloqueia nos dois hosts (`OBSERVED` nos Handoffs 005/006).
2. **Extensibilidade para o PR-10:**
   - o `evaluate_hook_payload` passa a despachar **por nome de ferramenta**;
   - ferramenta **desconhecida** → deny (fail-closed);
   - o PR-10 acrescenta as ferramentas de escrita a essa tabela.
3. **Testes:** as 7 linhas da tabela acima no `test_hook_context.py`, com decisão e código de saída conferidos por subprocesso (stdin real). O `nao-json` segue deny/2.
   - **Falsificabilidade:** num clone, restaure o `if not raw_input.strip(): allow` e mostre o teste reprovando.

### Critérios de aceite da rodada

- [ ] `test_pre_push_refspecs.py` roda na suíte oficial, e a checagem de teste órfão está no `doc-audit` (com prova).
- [ ] AJ2 graduado por ambiente, com casos nos testes.
- [ ] PR-09: as 7 linhas verdes, com prova por mutação.
- [ ] As redes diferenciais contra `921a649` registram 0 relaxamentos. Protocolo 7.1 **em cada commit**. O plano não é editado pelo agente.

## 4. Sequência

PR-08b + PR-09 → PR-10 (proteção do certificado e escrita de arquivo) → PR-11 e PR-12 → **tag v1.3.0**.
