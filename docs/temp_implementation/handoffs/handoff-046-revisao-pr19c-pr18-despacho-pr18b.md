# Handoff 046 — PR-19c homologado; PR-18 **não homologado** (evidência do catálogo e fuzz que não vê o lexer); despacho do PR-18b

**Data/Hora:** 2026-09-27T22:00:00Z
**Instância:** Revisor sênior
**Branch:** `claude/code-review-technical-analysis-kfwcdl`
**Commits revisados:** `3d1812b`, `8062afd`, `71de82c` (PR-19c); `91658ab`, `702b972`, `dc97ccb` (PR-18)
**Antecessor:** [Handoff 045](./handoff-045-revisao-pr19b-despacho-pr19c-pr18.md)

---

## 1. PR-19c: **HOMOLOGADO**

`OBSERVED` via API do GitHub Actions:

- **Shellcheck v0.11.0** do release oficial, com SHA-256 conferido no workflow e `--version` no log. Roda num **único job** (ubuntu/3.12) e saiu do `apt` e do `brew`.
- **Controle negativo na branch descartável** `claude/negctl-19c`: [run 36344146427](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36344146427) = failure. A branch foi apagada (AS2 cumprido).
- `3d1812b` → [run 36344441316](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36344441316) = **success**. A lição aprendida foi corrigida: versão fixada, e atualizações passam a ser PRs explícitos; o `apt` real era `0.9.0-1`.

## 2. PR-18: **NÃO HOMOLOGADO**

### O que está aceito

- **Frontmatter:** um parser único da stdlib (sem PyYAML). O commit `91658ab` quebrou no servidor ([run 36350111432](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36350111432)) por dependência de PyYAML que só existia localmente, e o `702b972` corrigiu ([run 36350731370](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36350731370) = success).
- **Skills citadas** existem.
- **Links relativos:** 24 links quebrados foram corrigidos nos READMEs do plugin (`./docs/…` → `../docs/…`), e hoje são 93 links em 30 arquivos, com 0 erros. A prova por mutação (link quebrado → arquivo e linha) está correta.
- O gate **não** foi alterado (`git diff a9c363e..HEAD -- clearer-engineering/scripts clearer-engineering/hooks` vazio). As redes diferenciais estão com 0 relaxamentos.

### AT1 — ALTO (integridade de evidência): o catálogo cita "evidência" que não é observação

Classificação das 23 ferramentas de `config/tool_catalog.json` pela evidência citada (`OBSERVED`):

| Evidência citada | Ferramentas | Situação |
|---|---|---|
| payload gravado (`E1-r1`, `E11-allow-write-padrao`) | `run_command`, `write_to_file` | ✅ observação real |
| `pr10-evidence.md` (**prosa** escrita pelo agente) | `replace_file_content`, `multi_replace_file_content` | ❌ não é payload |
| `host-probe/agy/tools/inventory.json` | **14**: `view_file`, `list_dir`, `grep_search`, `find_by_name`, `search_web`, `read_url_content`, `manage_task`, `schedule`, `generate_image`, `ask_question`, `invoke_subagent`, `define_subagent`, `manage_subagents`, `send_message` | ❌ **arquivo escrito pelo agente neste PR** |
| `host-probe/claude/…/e0_help.txt` | `Bash`, `Write`, `Edit`, `MultiEdit`, `NotebookEdit` | ⚠️ `MultiEdit` e `NotebookEdit` **não aparecem** no arquivo (0 ocorrências) |

- O `inventory.json` declara `"source": "Antigravity Runtime & CLI Subagents Specification"` e um `collected_at`, mas **não é saída de nenhuma sonda**. Ele foi criado e gravado **dentro de `evidence/host-probe/`**, o diretório que, desde o Handoff 005, só contém capturas. Colocar texto autoral ali faz uma declaração **parecer** `OBSERVED`. É o oposto da semântica OBSERVED/INFERRED que o CEH existe para garantir.
- O teste (`test_content_schema.py:184–193`) só confere se o `evidence_path` **existe**. Qualquer arquivo existente satisfaz a checagem, e por isso as quatro linhas ❌/⚠️ passam.

### AT2 — MÉDIO: o "fuzz do lexer" não enxerga o lexer

Mutação pedida no Handoff 045 §4.4, reproduzida num clone: `||` deixa de dividir segmentos (`lexer.py`, o ramo `if cmd_line[i+1] == "|"` passa a `buf.append("||")`).

| Rede | Com a mutação |
|---|---|
| `test_lexer_fuzz.py` (2.000 casos) | **OK** (não detecta) |
| mesma mutação **+** varredura de sufixos desligada (`safety-gate.py:280`) | **OK** (não detecta) |
| `test_review_batteries.py` | OK |
| corpus (`snapshot_gate.py --check`, 1.012 avaliações) | OK |

- **Causa:** as regras destrutivas aplicam `re.search` **em qualquer ponto** do subcomando (`safety-gate.py:351–405`). Sem a divisão, `git status || rm -rf src/` continua casando com o padrão de `rm -rf`. O invariante escolhido ("com trecho destrutivo, nunca `allow`") é garantido pela camada de regras. É uma boa notícia de defesa em profundidade, mas significa que **o teste não prova nada sobre o lexer**.
- A mutação da evidência ("desativação da interceptação de padrões destrutivos") exercita essa camada de regras, não o lexer.
- O `split_shell_pipeline` só é usado no fuzz para detectar erro de parse (linha 175).

### AT3 — MÉDIO (detecção, fora do escopo do PR-18): lacunas encontradas pela sonda da revisão

A composição está íntegra: um segmento que sai `allow` sozinho continua `allow` composto, e o mesmo vale para `deny`. Mas estes saem **allow em produção**:

- `git stash clear`
- `docker volume rm data`
- `redis-cli flushall`
- `dd if=/dev/zero of=app.db`

Eles foram registrados na bateria como `PENDENTE:H046-AT3`, com controles (`git stash list`, `docker volume ls`, `redis-cli ping` = allow).

- `rm -rf /tmp/x` = allow é intencional (diretório temporário).
- `npm run db:reset` já está no backlog de alvos opacos.

### AT4 — BAIXO: resíduos no commit do Conselho

- Os `prompt_*.txt` de `conselho/20260927_171054/` ainda trazem `/home/nandodev`, nas linhas 17 e 84. A limpeza só atingiu os pareceres, e o `doc-audit` não olha `.txt`.
- O `parecer_claude.md` está **vazio** (0 bytes): um conselheiro falhou em silêncio.
- A redação antes do envio externo é o escopo do PR-21. Aqui basta limpar e fazer o `doc-audit` cobrir `.txt` nas atas.

### AT5 — processo

- O log mostra mutações de prova feitas **na árvore de trabalho real** ("Edited lexer.py", "Edited safety-gate.py"), e esses arquivos ficaram fora do `git add`.
- **Regra:** mutações de prova só em clone. Anexe à evidência do PR-18b a saída de `git status --porcelain` e de `git diff --stat -- clearer-engineering/scripts`, ambas **vazias**, do ambiente local.

**Linha de base avançada** para `dc97ccb`. A bateria ganhou as linhas `H046-AT3`.

## 3. Despacho — PR-18b `fix(content): proveniência verificável no catálogo e propriedade do lexer`

Um commit (ou mais, com o CI verde antes de cada próximo push). Controles negativos só em `claude/negctl-*`.

1. **AT1: proveniência verificável.**
   - **Tire o `inventory.json` de `evidence/host-probe/`.** Esse diretório recebe apenas saídas de sonda, com runner e artefatos brutos.
   - `evidence_type` passa a ser um enum explícito:
     - `payload`: um `.jsonl` gravado pela sonda. O teste exige uma linha com `toolCall.name == <nome>` (agy) ou `tool_name == <nome>` (Claude);
     - `host_doc`: uma captura de saída do host (`--help`, listagem) ou um snapshot de documentação oficial, com URL, data e SHA-256 do conteúdo no próprio arquivo. O teste exige que o **nome apareça** no arquivo;
     - `declared`: um nome declarado sem observação. É permitido, mas **rotulado**. O teste lista essas entradas na saída, e nenhuma pode apontar para dentro de `host-probe/`.
   - **E12 (preferível ao `declared`):** uma sessão do agy com a sonda `host_probe.py` registrando **todas** as ferramentas (matcher amplo só no perfil de sonda), com um prompt que use cada ferramenta do perfil uma vez. Os artefatos brutos vão para `host-probe/agy/<timestamp>/`, com o runner versionado e sem descarte silencioso (AM1). O que for observado vira `payload`; o que não puder ser exercitado fica `declared`, com o motivo.
   - **Claude:** `MultiEdit`/`NotebookEdit` precisam de payload gravado ou de `host_doc` com o nome presente. Sem isso, ficam `declared`.
   - `replace_file_content` e `multi_replace_file_content`: payload do E12, ou `declared`. A prosa do `pr10-evidence.md` não serve como evidência.
2. **AT2: propriedade do lexer.** No `test_lexer_fuzz.py`, acrescente uma propriedade de **ida e volta** sobre o `split_shell_pipeline`, com a mesma semente:
   - para segmentos sorteados unidos por `;`, `&&`, `||`, `|` e `\n`: `split(join(segs)) == segs`;
   - segmentos com separadores **dentro de aspas** (`echo 'a;b'`, `echo "x || y"`) continuam **um** segmento;
   - o subshell `( … )` preserva o conteúdo como uma unidade, conforme o comportamento atual (documente qual é).
   - Mantenha o invariante do gate, renomeado com honestidade: "invariante de decisão do gate".
   - **Falsificabilidade:** a mesma mutação do `||` (num clone) tem de **reprovar** a propriedade de ida e volta. Registre também, na evidência, o resultado desta revisão: o invariante de decisão **não** reprova, por causa da camada de regras.
3. **AT4:** limpe os `prompt_*.txt` da ata e estenda a checagem de caminho absoluto do `doc-audit` para `.txt` em `docs/temp_implementation/conselho/`. Para o `parecer_claude.md` vazio: registre na ata que o conselheiro não respondeu (o `conselho-seniores.sh` devia ter marcado isso; se não marcou, anote como achado para o PR-21).
4. **AT5:** anexe as duas saídas vazias pedidas acima.
5. **AT3 fica fora** deste PR. As linhas `PENDENTE:H046-AT3` vão para o PR de cobertura de regras (junto com o AM2), depois do PR-18b.

### Critérios de aceite

- [ ] Nenhum arquivo autoral em `evidence/host-probe/`. Cada entrada do catálogo tem um `evidence_type` verificado **pelo conteúdo** do arquivo. Os `declared` são listados.
- [ ] A propriedade de ida e volta do lexer reprova com a mutação do `||`, com saída registrada.
- [ ] AT4 e AT5 resolvidos.
- [ ] O CI do servidor está verde (4/4) no commit final, com links dos jobs dessa execução. As redes diferenciais contra `dc97ccb` registram 0 relaxamentos.
- [ ] O plano não é editado pelo agente, e a homologação não é declarada pelo agente.

## 4. Sequência

PR-18b → PR de cobertura de regras (AT3 + AM2: `git stash clear`, `docker volume rm`, `redis-cli flushall`/`flushdb`, `dd of=` no repositório; e falsos positivos de leitura em `.ceh`) → PR-QA B–D → PR-20/21 → Onda 4.

**Release v1.3.0:** continua com o desenvolvedor ([Handoff 044 §3](./handoff-044-revisao-pr19a-ci-verde-despacho-pr19b.md)). Nada deste handoff a bloqueia.
