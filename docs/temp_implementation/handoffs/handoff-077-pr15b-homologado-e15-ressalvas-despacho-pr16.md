# Handoff 077 — PR-15b (adaptador do Muse) **HOMOLOGADO**; E15 com ressalvas; despacho do **PR-16** (empacotador)

**Data/Hora:** 2026-10-01T21:00:00Z
**Instância:** Revisor independente (Claude)
**Branch revisada:** `feature/onda-4` — `07e83df` (PR-15b), `990e311` (relatório do agente, "Handoff 076")
**CI:** [run 36741700872](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36741700872) = success (4/4) no head
**Antecessor:** [Handoff 075](./handoff-075-pr14-15-homologado-despacho-pr15b-muse.md)
**Execução:** agente do Antigravity. **Revisão:** Claude ou Codex.

> O "Handoff 076" é um **relatório de entrega do agente**, sem declaração de homologação; fica registrado assim, como os 059–061 e o 070.

---

## 1. Verificação independente (`OBSERVED`, worktree limpo do head)

| Item | Resultado |
|---|---|
| `onda4_baseline.py --check` | A1 (1.024), A2a (45), A2b (123; 20 novos declarados), A3 (107) idênticos; A3-muse **antes** preservado (41 × deny/2) e **depois** conferido (41 × exit 0); controle cruzado dos 7 `bash` com o motor; A4: 0 referências de host fora de `adapters/` |
| `snapshot_gate.py --check` | 1.024 idênticas |
| `test_adapters`, `test_hook_failclosed`, `test_hook_context`, `test_engine`, `test_cert_protection` | verdes **com e sem** as variáveis do Claude |
| `detect` do Muse | `model_provider`/`turn_id` (presentes nos 41 payloads reais) ou nome de ferramenta do Muse; despachante `[Antigravity, Muse, Claude]` |
| `render` do Muse | permitir `{}`/0; negar e `ask` `{"decision":"block"}`/0 — só formatos observados no E1b |
| A3-muse depois, por ferramenta | `bash` 7, `write_file` 6, `edit_file` 1, `submit_reminder_decision` 27: todos permitidos (os payloads do E1/E1b eram inofensivos) |
| BG1 | `recorded.jsonl` gerado dos payloads reais: 93 agy, 14 Claude, 41 Muse, junto dos casos manuais |

**Mutações desta revisão (em cópia temporária):**

| Mutação | Resultado |
|---|---|
| Muse depois do Claude no despachante | `test_adapters.py` e `--check` reprovam |
| `render` do Muse com exit 2 | `test_adapters.py` reprova (44 falhas) |
| erro de sintaxe no `adapters/muse.py`, payload real do Muse | o *shim* responde `{"decision": "deny"}` com exit 0 — ver BH2 |

**PR-15b: HOMOLOGADO quanto ao código.**

## 2. Ressalvas

### BH1 — E15: um `rm -rf /` real foi enviado a uma sessão do Muse em `--yolo`, e essa execução não foi registrada — ALTA (segurança de processo)

O Handoff 075 pediu "um comando destrutivo **dentro do diretório temporário**". Pelo log de entrega, a **primeira** execução do E15 pediu ao Muse, em `--yolo`, na máquina do desenvolvedor, que rodasse `rm -rf /`. Depois o runner foi trocado para `git push origin dev` (bloqueado pelo portão de push do CEH) e reexecutado. Três problemas:

1. **Risco real.** Se o hook tivesse falhado aberto, como a v1.4.0 falhava na IDE do Antigravity, a proteção restante seria só o `--preserve-root` do `rm`, e o modelo poderia ter variado o comando. Um experimento de bloqueio **nunca** mira caminhos fora do diretório temporário, mesmo esperando bloqueio.
2. **Execução descartada em silêncio (AM1).** A saída da primeira execução foi sobrescrita, e o motivo da troca não está registrado.
3. **Resumo errado.** O `summary.md` e o template do `runner.py` (linha 173) dizem que o cenário 2 foi `rm -rf /`, mas o prompt e a saída bruta mostram `git push origin dev`.

**A fazer, no primeiro commit do PR-16:**

- registre a primeira execução como evidência separada, rotulada: o prompt, o que o Muse fez e a saída, a partir da transcrição, marcando o que for reconstruído;
- corrija o `summary.md` e o template do runner para o comando real;
- troque o cenário de bloqueio por um comando destrutivo **confinado** ao diretório temporário (por exemplo, `rm -rf` de um subdiretório sentinela do workspace, bloqueado pelas regras do CEH para o ambiente usado), ou mantenha o `git push` e registre por que ele basta.

O cenário de permitir e o bloqueio do `git push` estão aceitos: as saídas brutas batem com os prompts.

### BH2 — reserva do *shim* não observada no Muse — MÉDIA

Se um módulo do CEH quebra, o *shim* responde `{"decision": "deny"}` com exit 0. Isso bloqueia no Antigravity (E13, E5), mas **no Muse só foram observados** `{"decision":"block"}` e o formato do Claude (E1b B4/B5). Grave um braço a mais com a sonda (E1c): `{"decision":"deny","reason":…}` com exit 0, no mesmo procedimento do E1b.

- **Se bloquear:** registre, e está resolvido.
- **Se não bloquear:** a reserva do *shim* precisa de um formato que bloqueie nos três hosts. Traga a matriz observada para decisão da revisão, **sem** mudar o *shim* por conta própria.

### BH3 — baixa

A detecção por nome de ferramenta minúsculo (critério 3 do `detect`) só vale para as quatro ferramentas conhecidas. Uma ferramenta nova do Muse **sem** `model_provider`/`turn_id` cairia no adaptador do Claude (exit 2, não observado no Muse). Os 41 payloads reais têm os marcadores, então hoje não há caso. Registre isso como limite na evidência.

## 3. Despacho — PR-16 `feat(package): empacotador por host a partir de uma fonte versionada`

**Objetivo:** acabar com cópias vendorizadas do gate. O pacote `clearer-muse` instalado na máquina do desenvolvedor tem a própria cópia de `hooks/safety-gate.py` (E1b, `plugins_list_before.json`), que envelhece a cada release.

1. **`clearer-engineering/tools/package.py --host <host> --out <dir>`** para `antigravity`, `muse` e `claude-code`:
   - copia **a mesma** fonte (`safety-gate.py`, `hook_context.py`, `ceh_core/`, `adapters/`) e gera o manifesto do host;
   - manifestos **só** a partir de formatos já observados: Antigravity = o `hooks.json` atual; Muse = a estrutura de plugin usada no E1b/E15; Claude Code = a configuração de hook da sonda do Handoff 005;
   - saída **determinística**: dois empacotamentos seguidos geram os mesmos hashes (teste).
2. **`install.sh`** instala a partir do pacote `antigravity` gerado na hora. Critério: **A2a e A2b idênticos** ao retrato atual (o usuário do Antigravity não percebe diferença).
3. **Teste de completude por host** (`test_package.py`, na suíte): para cada host, empacote num diretório temporário e rode o `safety-gate.py` **empacotado** contra o `recorded.jsonl` daquele host. As respostas têm de ser iguais às esperadas.
4. **Controle negativo** (em cópia temporária): um pacote do Muse sem `adapters/muse.py` reprova o teste de completude **e** não falha aberto (o *shim* responde deny).
5. **E16 (Muse), com artefatos brutos:** instale o pacote `muse` gerado num perfil temporário do Muse, **sem** tocar no `clearer-muse` do desenvolvedor, e repita os dois cenários do E15 com o bloqueio confinado ao diretório temporário (BH1). Grave `muse plugins list --json` antes e depois.
6. **Rede:** A1, A2a, A2b e A3 (os três hosts) idênticos; A4 inalterado; `dist/` fora do Git (`.gitignore`).
7. **Evidência** `onda4-pr16-evidence.md`: hashes dos pacotes, teste de completude, controle negativo, E16, BH1–BH3 resolvidas e CI (4/4) com o link.

### Critérios de aceite

- [ ] Um único código-fonte gera os três pacotes, com manifestos só de formatos observados.
- [ ] Empacotamento determinístico; `install.sh` a partir do pacote com A2 idêntico.
- [ ] Completude por host com o `recorded.jsonl`; controle negativo em cópia temporária.
- [ ] E16 com artefatos brutos e bloqueio confinado ao diretório temporário.
- [ ] BH1 registrada e corrigida; E1c (BH2) gravado; BH3 registrado.
- [ ] CI verde (4/4). O plano não é editado pelo agente, e a homologação não é declarada pelo agente.
