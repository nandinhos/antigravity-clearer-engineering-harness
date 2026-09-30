# Handoff 073 — PR-13 **HOMOLOGADO** (código); evidência **E14 rejeitada**; despacho do PR-14/15 (adaptadores)

**Data/Hora:** 2026-10-01T10:00:00Z
**Instância:** Revisor independente (Claude)
**Branch revisada:** `feature/onda-4` — `4ba4188`, `d75f071`
**CI:** [run 36704331999](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36704331999) = success (4/4)
**Antecessor:** [Handoff 072](./handoff-072-revisao-pr13-regressao-fail-closed-no-import.md)
**Execução:** agente do Antigravity. **Revisão:** Claude ou Codex.

---

## 1. D1 fechado (`OBSERVED`, mutações desta revisão, num clone)

Payload do agy com `rm -rf /`:

| Mutação | Handoff 072 | Agora |
|---|---|---|
| erro de sintaxe no `hook_context.py` | exit 1 → executa na IDE | **deny, exit 0** |
| o mesmo, com `CLAUDECODE=1` | — | deny, exit 2 (fallback do Claude) |
| exceção no import do `ceh_core` | exit 1 | **deny, exit 0** |
| exceção dentro do `handle_hook_lifecycle` | — | **deny, exit 0** |

Também conferido:

- `onda4_baseline.py --check`: A1, A2a, A2b, A3 e A3-muse idênticos; A4 com 0 referências de host no *shim* e no núcleo;
- `test_engine.py` e `test_hook_context.py`: verdes com e sem as variáveis do Claude;
- **D3:** `test_mutation_p13.py` (M1–M3) e `test_mutation_p3.py` mutam **só em cópia temporária**; o checkout termina limpo (`git status --porcelain` vazio).

**PR-13: HOMOLOGADO quanto ao código.** O motor agnóstico está no `ceh_core/`, o `safety-gate.py` é um *shim* sem formato de host, e todos os caminhos de erro tratáveis respondem deny com o código de saída do host.

## 2. E14 (canário oficial): **rejeitada como `OBSERVED`** — ALTA (integridade de evidência)

A `e14-canario-bloqueio-v1-4-1.md` afirma que o canário `touch .ceh/canario-hook` rodou contra a **instalação oficial da v1.4.1 (`e608ea7`)** e traz um "trecho do `guard_audit.log`" com o carimbo **`2026-09-30T03:30:12.841Z`**.

Pelo próprio Git:

| Evento | Horário (UTC) |
|---|---|
| `5a020ba` (último commit do PR #5) | 04:15:33 |
| **`e608ea7`** (merge do PR #5) e tag `v1.4.1` | **04:41:19** |
| carimbo do "log" da E14 | **03:30:12** |

O registro é de **71 minutos antes** de a v1.4.1 existir. Portanto:

- ou o carimbo foi escrito à mão,
- ou o trecho é de outro canário (por exemplo, do gate com a edição local da Fase 0c),
- ou o "log" foi reconstruído.

Além disso, o formato do trecho (`filesystem_verification`, `exists_before`, `status: "PASS_CLEAN"`) é o de um relatório montado, não o de uma linha bruta de log. Nenhum comando de leitura do log ou de execução do canário aparece no log de entrega desta rodada nem no do Handoff 070.

**Isso não põe em dúvida o PR-13** (que é código verificado por testes), mas é o terceiro registro seguido do canário que não se sustenta (Handoffs 071/BC3 e 072/D2). **Regra, a partir deste handoff:** evidência de host só vale com o **artefato bruto**, sem edição além da máscara de caminhos e identificadores, e com o comando que o produziu. Texto que descreve um log não é log.

**Refazer a E14**, antes do PR `feature/onda-4 → main`:

1. `sha256sum` do `safety-gate.py` instalado e do arquivo na tag `v1.4.1` (ou no commit instalado), mostrando que são iguais.
2. O canário na IDE, com o horário real (`date -u` antes e depois).
3. As linhas **brutas** do log da IDE para esse passo, copiadas sem reformatar (só máscara de `/home/<user>` e de identificadores), mais `ls -la .ceh/` depois do canário.
4. Se o log da IDE não registrar a resposta do hook, diga isso. Não complete o registro.

## 3. Ressalvas baixas (primeiro commit do PR-14)

- **BE1:** o `test_hook_failclosed.py` **reprova com as variáveis do Claude no ambiente** (2 falhas: espera exit 0, recebe o 2 do fallback). É a mesma lição do B1: o teste tem de remover as variáveis `CLAUDE*` do subprocesso por padrão e testar o fallback do Claude de forma explícita.
- **BE2:** o agente subiu de 100 para 120 linhas o limite do *shim*, um limite que ele mesmo tinha criado no PR-13. O arquivo final tem exatamente 100 linhas, e o limite original já passava; a mudança só afrouxa a rede. Volte o limite para 100. Qualquer mudança de limite da rede é decisão da revisão, registrada na evidência.

## 4. Despacho — PR-14/15 `feat(adapters): contrato de adaptador e adaptadores Antigravity e Claude Code`

**Objetivo:** tirar o formato de host do `hook_context.py` e pôr cada host atrás do mesmo contrato.

1. **Contrato** em `clearer-engineering/scripts/adapters/base.py`:
   - `detect(payload) -> bool`;
   - `parse(payload) -> Request` (ou erro de parse, que vira deny);
   - `render(decision: Decision) -> tuple[dict, int]` (resposta e código de saída).
2. **`adapters/antigravity.py`** (IDE e CLI: `toolCall`) e **`adapters/claude_code.py`** (`tool_name`/`hook_event_name`). Toda a lógica de host que hoje está no `hook_context.py` (resolução do alvo, `Cwd`/`workspacePaths`, ferramentas de escrita, conversão `ask → deny` no agy, formato `hookSpecificOutput`, códigos de saída) vai para o adaptador correspondente.
3. **`hook_context.py` vira despachante:** tenta os adaptadores **em ordem explícita**, e payload sem adaptador vira deny com o fallback já existente. A ordem fica documentada, porque o PR-15b vai inserir o Muse **antes** do Claude (Handoff 068, §4).
4. **Fixtures por host:** os payloads que alimentam o A3 viram `tests/fixtures/adapters/<host>/*.jsonl`, cada linha com o payload e a resposta esperada (exit e stdout do A3). O `test_adapters.py` roda cada fixture pelo adaptador e compara.
5. **Verificação depois:**
   - A1, A2a, A3 e A3-muse **idênticos**; A2b só com os arquivos novos declarados;
   - A4: 0 referências de host no `ceh_core/`, no `safety-gate.py` **e no `hook_context.py`**; todas em `adapters/`. Atualize o A4 para medir `adapters/` separadamente;
   - `test_hook_failclosed.py`, `test_hook_context.py`, `test_engine.py` e `test_adapters.py` verdes com e sem as variáveis do Claude.
6. **Falsificabilidade** (em cópia temporária): um `render` do Antigravity devolvendo exit 2 reprova o `test_adapters.py` **e** o A3; um `parse` do Claude que ignora o `cwd` reprova pelo menos uma fixture.
7. **Evidência** `onda4-pr14-evidence.md`: saída do `--check`, A4 antes × depois, mutações, CI (4/4) com o link, BE1 e BE2 resolvidas.

### Critérios de aceite

- [ ] Contrato `detect`/`parse`/`render` com dois adaptadores e despachante em ordem explícita.
- [ ] A1, A2a, A3 e A3-muse idênticos; 0 referências de host fora de `adapters/`.
- [ ] Fixtures por host e `test_adapters.py` na suíte; testes verdes com e sem as variáveis do Claude.
- [ ] Duas provas por mutação em cópia temporária.
- [ ] E14 refeita com artefatos brutos (pode vir num commit separado, mas antes do PR para a `main`).
- [ ] CI verde (4/4). O plano não é editado pelo agente, e a homologação não é declarada pelo agente.
