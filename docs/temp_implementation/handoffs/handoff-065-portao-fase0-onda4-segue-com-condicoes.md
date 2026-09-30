# Handoff 065 — Portão da Fase 0 da Onda 4: **SEGUE COM CONDIÇÕES** (Fase 0b antes do PR-13)

**Data/Hora:** 2026-09-30T12:00:00Z
**Instância:** Revisor independente (Claude)
**Branch revisada:** `feature/onda-4` — commits `5f6809a`, `d875da5`, `252e2bd`
**Antecessor:** [Handoff 064](./handoff-064-onda-4-branch-feature-verificacao-antes-depois.md)
**Execução:** agente do Antigravity. **Revisão:** Claude ou Codex.

---

## 1. Veredito do portão: **SEGUE**, com quatro condições a cumprir antes do PR-13

A condição central do Handoff 064 está atendida: há um **3º host (Muse Code 1.4.1) com payload real de hook gravado** e com bloqueio observado. Mas a Fase 0 tem lacunas que, se não forem fechadas agora, contaminam as Fases 1–5.

### Verificado de forma independente (`OBSERVED`)

| Item | Resultado |
|---|---|
| CI nos 3 commits | verde: [run 36646529673](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36646529673), [run 36647560599](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36647560599), [run 36650284266](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36650284266) |
| Gatilho `feature/**` | ativo (o próprio commit 0.1 rodou no servidor) |
| `onda4_baseline.py --check` | exit 0 num worktree limpo da branch; A1 (1.024, sha `3878d3cc…`), A2 (102 arquivos), A3 (107 respostas: 93 agy + 14 Claude), A4 (53 refs no `hook_context.py`, 2 no `safety-gate.py`, 630 linhas, 0 testes de conformidade) |
| Base da branch | `63752df` em vez de `v1.4.0`; a diferença de código é **zero** (só cabeçalhos de fixtures). Aceito |
| E1 do Muse | 10 payloads reais; formato `tool_name` + `tool_input.command` + `cwd` + `hook_event_name`; ferramentas **em minúsculas** (`bash`, `write_file`, `edit_file`) e internas (`submit_reminder_decision`); bloqueio com `{"decision":"block","reason":…}` observado (sentinela não criado) |
| Vazamento na evidência do Muse | 0 caminhos de home no conteúdo |

### Achado que justifica a Onda 4 (`OBSERVED`, antes)

Os payloads reais do Muse, enviados ao gate da **v1.4.0**:

| Ferramenta do Muse | Resposta atual |
|---|---|
| `bash` | **deny**, exit 2 |
| `write_file` | **deny**, exit 2 |
| `edit_file` | **deny**, exit 2 |
| `submit_reminder_decision` | **deny**, exit 2 |

Os nomes são desconhecidos para o `TOOL_DISPATCH`, e o gate é fail-closed. **Sem adaptador, o CEH ligado como hook no Muse bloqueia tudo.** Esse é o "antes" medido da integração; o "depois" esperado é a decisão real por comando.

## 2. Condições (Fase 0b), antes de qualquer código da Fase 1

### C1 — Corrigir o A2 (erro de especificação **do Handoff 064**)

O A2 exige que **cada** arquivo instalado fique byte a byte igual. O manifesto tem **47 `.py` e 16 `.sh`** — justamente o código que a Onda 4 vai refatorar. Do jeito que está, o A2 reprova no PR-13 por construção, e a tentação seria regenerar o retrato, o que anula a rede.

- **A2a (identidade byte a byte):** só os ativos que **não** são código: `*.md` (perfil, skills, agentes, regras), `*.json` (`plugin.json`, `hooks.json`, catálogos), `*.txt`, `*.jsonl`, o bloco de aliases do rc.
- **A2b (estrutura):** a **lista de caminhos** instalados (incluindo `.py`/`.sh`) é idêntica, salvo os arquivos novos que cada PR declarar explicitamente.
- O **comportamento** do código fica garantido pelo A1 (decisões) e pelo A3 (respostas do hook).
- Regenere o retrato **uma única vez**, neste commit, a partir da mesma `v1.4.0`, e registre na evidência que A1/A3/A4 não mudaram.

### C2 — E1b do Muse: completar o contrato de resposta

1. **Isolamento:** o Muse já tinha o plugin `clearer-muse` com o hook `safety-gate` aprovado. O runner só desinstalou a sonda; o `clearer-muse` **não foi desligado**. Desabilite-o durante o experimento e grave `muse plugins list --json` **antes de cada braço**.
2. **Modo de permissão:** as 10 invocações têm `permission_mode = bypassPermissions` (`--yolo`). Repita os braços **no modo padrão** (a lição do E11/E10: o controle precisa mostrar o fluxo nativo do host).
3. **Braço "allow explícito":** acrescente um braço com `{"decision":"allow"}` (ou o equivalente do Muse), para saber se ele **pula** a confirmação nativa (como o F6 do Claude). O adaptador só pode responder allow com o formato que se provar **neutro**.
4. A variante `hookSpecificOutput`/`permissionDecision: "deny"` só foi tentada em `hook test`; ou ela é observada numa sessão real, ou fica registrada como `INFERRED`.
5. **`ask`:** registre como o Muse trata um pedido de confirmação. Se não houver formato observado, o mapeamento fica `ask → block` (fail-closed, como no agy, PR-00c).

### C3 — Prova de falsificabilidade do retrato, do jeito pedido

- O Handoff 064 pedia o controle negativo **no servidor**, numa branch descartável `claude/negctl-onda4`. Não foi feito.
- A mutação local (comentário no `environment.py`) foi feita **na árvore real**, não num clone (regra AT5, Handoff 046), e só exercita o A2 — que, pelo C1, deixa de cobrir `.py`.
- Faça, em `claude/negctl-onda4`, uma **mutação de comportamento** que só o A3 pega: por exemplo, trocar a chave de resposta do Claude no `render` (`hookSpecificOutput` → outra). O `--check` tem de reprovar no servidor, citando o A3. Cite o link e apague a branch.

### C4 — Muse no retrato "antes"

Acrescente os 10 payloads do Muse ao **A3** como `A3-muse`, com a resposta atual (deny/2 para os quatro nomes de ferramenta). Ele **não** entra na regra "idêntico em cada PR": é o marcador do antes, e o PR-15b (adaptador do Muse) o transforma no depois esperado, documentado lado a lado.

### Ressalva baixa

- **C5:** a evidência do Muse versiona `session_id` e `tool_use_id` reais. Não são segredos, mas o projeto já redige identificadores de sessão (atas do Conselho). Mascare-os com um marcador estável (por exemplo, `sess-1`, `sess-2`).

## 3. Depois da Fase 0b

Nova revisão curta (Claude ou Codex). Se C1–C4 estiverem fechados, a Fase 1 (PR-13, motor agnóstico) está liberada, com a regra: **A1, A2a, A2b e A3 (agy/Claude) idênticos em cada PR.**

### Critérios de aceite da Fase 0b

- [ ] A2 dividido em A2a (ativos, byte a byte) e A2b (lista de caminhos), com o retrato regenerado uma única vez a partir da `v1.4.0`.
- [ ] E1b do Muse: `clearer-muse` desabilitado, `plugins list` por braço, modo padrão, braço allow explícito, `ask` registrado.
- [ ] Controle negativo do A3 no servidor, em `claude/negctl-onda4`, com link.
- [ ] `A3-muse` no retrato como marcador do antes.
- [ ] CI verde (4/4) em cada commit. Mutações só em clone ou em `claude/negctl-*`. O plano não é editado pelo agente, e a homologação não é declarada pelo agente.
