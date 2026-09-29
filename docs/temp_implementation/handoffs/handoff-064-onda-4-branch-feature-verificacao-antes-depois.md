# Handoff 064 — Abertura controlada da Onda 4 na branch `feature/onda-4`, com verificação antes e depois

**Data/Hora:** 2026-09-29T17:00:00Z
**Instância:** Revisor sênior (Claude)
**Ponto de partida:** tag `v1.4.0` (`8bb38c0`), linha de base homologada no [Handoff 063](./handoff-063-encerramento-onda-5-v1-4-0.md)
**Decisão do desenvolvedor:** abrir a Onda 4 em branch separada, medindo antes e depois, sem tocar na `main` até a homologação.

---

## 0. Por que e com que limite

**Diferencial esperado da Onda 4** (plano, seção "Onda 4"):

1. **Mesma decisão em todos os harnesses, garantida por teste** (suíte de conformidade). Hoje nenhum teste roda o mesmo corpus pelos formatos de host.
2. **Integrar um host novo = `parse` + `render` + fixtures gravadas**, em vez de copiar o `ceh_core/` e reescrever o adaptador (Handoff 060, passos 1–2).
3. **Distribuição por host a partir de uma fonte versionada** (empacotador), acabando com cópias vendorizadas que envelhecem (quem copiou o núcleo antes da v1.4.0 continua sem o conserto do fork bomb).

**Limite (Ponytail):** a onda só continua se houver um **3º host com payload de hook real gravado** (E1). Hoje o Muse, o Codex, o Gemini e o Hermes só têm E0 (`help`, `version`). O Muse tem hooks de plugin (`muse plugins hook test … --fixture`, em `host-probe/muse/plugins_help.txt:14`), então a gravação é viável.

## 1. Regras da branch

- **Criação:** `git checkout -b feature/onda-4 v1.4.0` e push para `origin/feature/onda-4`.
- **A `main` não recebe nada** desta branch até a homologação final. A entrada é **por PR**, com os 4 jobs `Validate` verdes (ressalva AY2 do Handoff 063).
- Um push por commit certificado (`test-runner.sh`); **CI do servidor verde (4/4)** em cada commit antes do seguinte; evidência com o link da execução versionado.
- Controles negativos só em branches descartáveis `claude/negctl-*`.
- Redes diferenciais contra `8bb38c0` com **0 relaxamentos** em todos os commits.
- O plano não é editado pelo agente, e a homologação não é declarada pelo agente (é da revisão: Claude ou Codex).

## 2. Fase 0 — Verificação ANTES (nenhuma mudança de comportamento)

### Commit 0.1 — `ci: disparar o CI em feature/**`

O `ci.yml` só dispara em `main`, `staging`, `dev` e `claude/**`. Acrescente `'feature/**'` aos gatilhos de `push`. Sem isso, nada nesta branch roda no servidor. A execução desse próprio commit já comprova o gatilho.

### Commit 0.2 — `test(onda4): retrato de referência da v1.4.0`

Crie `clearer-engineering/tests/tools/onda4_baseline.py` com dois modos:

- `--generate` grava o retrato em `docs/temp_implementation/evidence/onda4/baseline-v1.4.0/`;
- `--check` refaz tudo e compara com o retrato. **Qualquer diferença = exit ≠ 0**, com a lista do que mudou.

O retrato contém:

| ID | Medição | Como |
|---|---|---|
| **A1** | Decisões do gate | cópia do `gate_corpus.expected.jsonl` (1.024 avaliações, sha256 começando por `3878d3cc285f`) |
| **A2** | Instalação de referência | `install.sh` num `HOME` temporário, com `agy` falso no `PATH`; sha256 de **cada** arquivo sob `~/.gemini/config/plugins/clearer-engineering/` e `~/.gemini/config/agents/clearer-harness/`, mais o bloco de aliases do rc |
| **A3** | Respostas do hook | para **cada** payload gravado (`invocations.jsonl` do agy: 93; do Claude: 14), enviar o payload via stdin ao `safety-gate.py` e gravar `stdout` + exit code. Execução determinística: mesmo `cwd`, mesmo ambiente, sem rede |
| **A4** | Acoplamento | contagem de referências de formato de host (`toolCall`, `tool_name`, `tool_input`, `hookSpecificOutput`, `CommandLine`) por arquivo; hoje **51** no `hook_context.py` e **2** no `safety-gate.py`; linhas do `safety-gate.py` (630); testes de conformidade entre hosts (**0**) |

Registre o `onda4_baseline.py --check` na suíte (`run-all-tests.sh`). Nesta fase ele passa trivialmente, e daí em diante vira a **rede de não-regressão da Onda 4**.

**Falsificabilidade:** numa branch `claude/negctl-onda4`, altere o texto de um motivo de deny ou um arquivo instalado; o `--check` reprova no servidor. Cite o link e apague a branch.

### Commit 0.3 — `evidence(muse): E1 — payload real de hook gravado (A5)`

1. Um plugin de **sonda** para o Muse, com um hook de pré-execução de ferramenta que só **grava o payload recebido** (stdin, variáveis de ambiente relevantes, argumentos) e responde neutro. Nada de decisão nesta etapa.
2. Uma sessão real do Muse em que o agente usa pelo menos: execução de comando no terminal, escrita de arquivo e edição de arquivo.
3. Artefatos brutos em `docs/temp_implementation/evidence/host-probe/muse/<timestamp>/` (runner versionado, `invocations.jsonl`, saída do CLI), com checagem de vazamento. **Nenhuma execução descartada em silêncio** (regra AM1).
4. **Contrato de resposta com controle** (lição do E11): três braços no mesmo prompt — sem hook, hook respondendo "permitir", hook respondendo "negar". Registre o que o Muse faz em cada um, e qual formato de resposta **bloqueia** de fato.
5. Se o Muse não permitir interceptar a execução de comandos, registre isso como evidência. Não force.

### Portão de decisão (revisão, não o agente)

Depois dos três commits, a revisão emite o veredito:

- **SEGUE** se o A5 tiver payload real de comando e o contrato de resposta com controle observado → Fase 1.
- **PARA** se não houver E1 do Muse (ou de outro 3º host). A branch fica arquivada com o retrato versionado, e a v1.4.0 segue como está. É um resultado válido.

## 3. Fases 1–4 — Implementação, com verificação DEPOIS em cada PR

Escopo do plano (seção "Onda 4"), com os critérios de verificação explícitos:

| Fase | PR | Entrega | Verificação depois (obrigatória) |
|---|---|---|---|
| 1 | **PR-13** motor agnóstico | `engine.evaluate(Request) -> Decision`; `safety-gate.py` vira um *shim* fino sobre os adaptadores | `onda4_baseline.py --check` **idêntico** em A1, A2 e A3; A4: formato de host fora do núcleo |
| 2 | **PR-14 + PR-15** adaptadores | contrato de adaptador (`parse`/`render`) + Antigravity + CLI + Claude Code, com os payloads gravados como fixtures | A1–A3 **idênticos**; cada fixture de host produz a resposta que o A3 gravou |
| 3 | **PR-15b** adaptador Muse | `parse`/`render` do Muse a partir do E1 (Commit 0.3), nunca de documentação suposta | fixtures do Muse com resposta esperada; conformidade (Fase 4) já cobrindo o Muse |
| 4 | **PR-16** empacotador | `tools/package.py --host <host> --out dist/<host>`; `install.sh` instala a partir de `dist/antigravity` | **A2 byte-idêntico** ao retrato (o pacote do Antigravity não muda) |
| 5 | **PR-17** conformidade | o corpus inteiro (1.024) passa por **todos** os adaptadores; a `Decision` é idêntica por comando e ambiente, só o `render` varia; guia `docs/adapters/novo-host.md` | 0 divergências entre hosts; controle negativo: um adaptador com `parse` defeituoso reprova a conformidade (em `claude/negctl-*`) |

Regras em todas as fases:

- **Nenhuma decisão muda.** A1 idêntico é inegociável; se precisar mudar decisão, é outro PR, fora da Onda 4.
- Orçamentos de linhas do `doc-audit` valem para os arquivos novos.
- Cada PR com evidência (`onda4-prNN-evidence.md`) trazendo a saída do `--check`.

## 4. Relatório final ANTES × DEPOIS

Antes do PR para a `main`, a evidência `onda4-relatorio-final.md` traz, lado a lado:

| Medição | Antes (v1.4.0) | Depois (esperado) |
|---|---|---|
| A1 decisões | 1.024, sha `3878d3cc285f` | idêntico |
| A2 instalação Antigravity | manifesto de referência | byte-idêntico |
| A3 respostas do hook (agy/Claude) | 93 + 14 | idênticas |
| A4 formato de host no núcleo | 51 + 2 referências | 0 (só em `adapters/`) |
| Testes de conformidade | 0 | corpus × todos os hosts |
| Hosts com adaptador + fixtures reais | 2 (agy, Claude) | 3+ (com Muse) |
| Passos para integrar um host novo | copiar núcleo + escrever adaptador (Handoff 060) | `parse` + `render` + fixtures + conformidade |

Depois disso: PR `feature/onda-4 → main`, homologação da revisão, e tag **`v2.0.0`** pelo desenvolvedor (a API de integração muda, então é *major*).

## 5. Critérios de aceite desta etapa (só a Fase 0)

- [ ] `feature/onda-4` criada a partir de `v1.4.0`; CI disparando nela.
- [ ] Retrato A1–A4 versionado, com `onda4_baseline.py --check` na suíte e controle negativo no servidor.
- [ ] E1 do Muse gravado com os três braços do contrato de resposta, ou o registro de que não é possível.
- [ ] Nenhum arquivo de produção alterado além do `ci.yml`. CI verde (4/4) em cada commit, com link versionado.
- [ ] Aguardar o portão de decisão da revisão antes da Fase 1.
