# Handoff 075 — PR-14/15 **HOMOLOGADO** (adaptadores); despacho do **PR-15b** (adaptador do Muse)

**Data/Hora:** 2026-10-01T17:00:00Z
**Instância:** Revisor independente (Claude)
**Branch revisada:** `feature/onda-4` — `d014598` (BE1, BE2, BF1), `db9c1c3` (PR-14/15), `c4ef0f1`, `793884f`
**CI:** [run 36731527964](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36731527964) = success (4/4) no head
**Antecessor:** [Handoff 074](./handoff-074-e14-refeita-aceita-registro-da-evidencia-montada.md)
**Execução:** agente do Antigravity. **Revisão:** Claude ou Codex.

---

## 1. Verificação independente (`OBSERVED`, worktree limpo do head)

| Item | Resultado |
|---|---|
| `onda4_baseline.py --check` | A1 (1.024, `3878d3cc…`), A2a (41, com as 2 fixtures novas declaradas), A2b (117; 14 novos declarados), A3 (107), A3-muse (41) idênticos; A4: **0** referências de host no `safety-gate.py`, no `ceh_core/` e no `hook_context.py`; 48 em `adapters/` |
| `snapshot_gate.py --check` | 1.024 idênticas |
| `test_adapters`, `test_hook_failclosed`, `test_hook_context`, `test_engine`, `test_cert_protection` | verdes **com e sem** as variáveis do Claude no ambiente |
| Despachante | `ADAPTERS = [AntigravityAdapter(), ClaudeCodeAdapter()]`, ordem explícita, com a nota de que o Muse entra antes do Claude |
| Mudanças na rede | A2a/A2b aceitam só os arquivos declarados; A4 passa a exigir 0 no `hook_context.py`; limite do *shim* de volta a **100** (BE2) |
| BE1 / BF1 | `test_hook_failclosed.py` hermético; E14 com a seção "Histórico" registrando a versão montada |

**Mutações desta revisão (em cópia temporária):**

| Mutação | Resultado |
|---|---|
| `render` do Antigravity devolvendo exit 2 | `test_adapters.py` reprova (6 falhas) **e** o `--check` reprova (A3) |
| `parse` do Claude ignorando o `cwd` | `test_adapters.py` reprova (2 falhas); **o A3 não pega** |
| erro de sintaxe no `adapters/antigravity.py` | o gate responde deny com **exit 0** (fail-closed preservado) |

**PR-14/15: HOMOLOGADO.**

### Ressalvas

- **BG1 (média):** o Handoff 073 (§4, item 4) pedia fixtures geradas **a partir dos payloads gravados que alimentam o A3**. As fixtures entregues são **15 casos escritos à mão** (7 agy, 8 Claude). Elas têm valor: a segunda mutação acima mostra que pegam um defeito que o A3 não pega. Mas não substituem os payloads reais. No PR-15b, acrescente `tests/fixtures/adapters/<host>/recorded.jsonl`, **gerado** dos 93 + 14 payloads de origem do A3, com a resposta do A3 como esperado, e rode as duas coleções no `test_adapters.py`.
- **BG2 (baixa):** o `db9c1c3` foi para o servidor e reprovou no macOS ([run 36728848762](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36728848762)): o diretório temporário do macOS é um link simbólico (`/var` → `/private/var`). O conserto (`Path(...).resolve()`) veio no commit seguinte. Adote isso como convenção em todo teste que compara caminhos de diretório temporário.

## 2. Despacho — PR-15b `feat(adapters): adaptador do Muse a partir do E1/E1b`

Fonte **única** do contrato: o que foi **observado** no E1 e no E1b (Handoffs 065 e 066). Nada de documentação suposta.

1. **`adapters/muse.py`:**
   - **`detect`:** compare os payloads reais do Muse (E1/E1b, 41) com os do Claude gravados (14) e escolha um critério que os **separe sem ambiguidade**. Por exemplo, os nomes de ferramenta do Muse são minúsculos (`bash`, `write_file`, `edit_file`, `submit_reminder_decision`), e os do Claude, capitalizados (`Bash`, `Write`, …). Justifique o critério na evidência com a contagem: 41/41 Muse detectados, 0/14 Claude, 0/93 agy.
   - **`parse`:** `bash` → comando (`tool_input.command`, `cwd`); `write_file`/`edit_file` → alvos de escrita (proteção do `.ceh/` igual à dos outros hosts).
   - **`submit_reminder_decision`** é ferramenta interna do Muse, sem comando nem caminho. Hoje recebe deny (fail-closed). Se o adaptador passar a permiti-la, é **decisão explícita**: lista fechada no adaptador, justificada na evidência com o payload real. Qualquer outra ferramenta desconhecida continua deny.
   - **`render`:** permitir → `{}` com **exit 0**; negar → `{"decision": "block", "reason": …}` com **exit 0**; `ask` → block. São os formatos observados no E1b (B2, B4, B6). O comportamento do Muse com exit 2 **não** foi observado, então não use exit 2.
2. **Ordem no despachante:** `[Antigravity, Muse, Claude]`.
3. **A3-muse, do "antes" ao "depois":**
   - mantenha o `A3_muse_before.jsonl` intacto;
   - gere uma única vez o `A3_muse_after.jsonl` com a resposta nova de cada um dos 41 payloads;
   - o `--check` passa a comparar o **depois**;
   - na evidência, tabela lado a lado por ferramenta. Esperado: `bash` com a decisão real do motor para aquele comando e `cwd`; escrita em `.ceh/` negada; o resto conforme a regra do item 1.
   - **Controle cruzado:** para cada payload `bash`, a decisão do adaptador tem de ser igual a `evaluate(Request(comando, cwd))` direto no motor.
4. **Fixtures:** `tests/fixtures/adapters/muse/recorded.jsonl` com os 41 payloads reais e o "depois" como esperado, mais os `recorded.jsonl` do agy e do Claude (BG1).
5. **A1, A2a, A3 (agy/Claude) idênticos**; A2b com os arquivos novos declarados; A4 com 0 referências de host fora de `adapters/`.
6. **Ponta a ponta no Muse (E15), com artefatos brutos:** num diretório temporário, uma sessão real do Muse com o gate da branch ligado como hook, sem o `clearer-muse` antigo. Um `ls` roda, e um comando destrutivo dentro do diretório temporário é **bloqueado**, com a mensagem do CEH. Grave `muse plugins list --json` antes, a saída bruta do CLI e a listagem do diretório depois. Se o Muse não aceitar o hook dessa forma, registre isso e **não** complete o registro.
7. **Falsificabilidade** (em cópia temporária):
   - Muse depois do Claude no despachante → as fixtures do Muse reprovam;
   - `render` do Muse devolvendo exit 2 → reprova.
8. **Evidência** `onda4-pr15b-evidence.md`: critério do `detect` com as contagens, tabela antes × depois do A3-muse, controle cruzado, mutações, E15 e CI (4/4) com o link.

### Critérios de aceite

- [ ] `detect` do Muse sem ambiguidade (41/0/0), com o critério justificado.
- [ ] `render` só com os formatos observados no E1b (exit 0).
- [ ] A3-muse: "antes" preservado, "depois" gerado uma vez, controle cruzado com o motor.
- [ ] Fixtures reais do Muse, do agy e do Claude (`recorded.jsonl`) na suíte.
- [ ] E15 com artefatos brutos, ou o registro honesto de que não foi possível.
- [ ] Duas mutações em cópia temporária.
- [ ] CI verde (4/4). O plano não é editado pelo agente, e a homologação não é declarada pelo agente.
