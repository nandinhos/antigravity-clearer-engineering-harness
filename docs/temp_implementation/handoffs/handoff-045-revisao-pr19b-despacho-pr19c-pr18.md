# Handoff 045 — PR-19b homologado (shellcheck bloqueante, CI verde); despacho do PR-19c (shellcheck fixado) e do PR-18

**Data/Hora:** 2026-09-27T21:00:00Z
**Instância:** Revisor sênior
**Branch:** `claude/code-review-technical-analysis-kfwcdl`
**Commits revisados:** `1893cd6`, `6d565f1`, `d2b0a26`, `dadcc72`, `6e0e8de` (PR-19b)
**Antecessor:** [Handoff 044](./handoff-044-revisao-pr19a-ci-verde-despacho-pr19b.md)

---

## 1. Veredito: **HOMOLOGADO COM RESSALVA** (AS1)

**Servidor** (`OBSERVED` via API do GitHub Actions):

| Commit | Run | Conclusão | Papel |
|---|---|---|---|
| `1893cd6` | [36333967018](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36333967018) | failure | **controle negativo**: `task-monitor.sh:93:6 [SC2086]` reprova o passo do shellcheck **nos 4 jobs** |
| `6d565f1` | [36334302895](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36334302895) | failure | divergência de versão: só o macOS acusa `SC2329` em `run-all-tests.sh:11` |
| `d2b0a26` | [36334627564](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36334627564) | **success** | traps inline + `disable` justificado |
| `dadcc72` | [36335965350](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36335965350) | **success** | evidência |
| `6e0e8de` (HEAD) | [36340617938](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36340617938) | **success** | lição aprendida |

**Conferido no diff e localmente:**

- **Shellcheck bloqueante:** sem `continue-on-error` e sem `|| true`, com `set -o pipefail` antes do `tee`. O controle negativo prova que o passo reprova.
- **Linha de base** por código e por arquivo na evidência. As correções são semânticas:
  - `=~ " x "` virou `== *" x "*`, que é equivalente (casamento literal de substring);
  - `cd … || exit 1`;
  - `A && B || C` virou `if`;
  - variáveis mortas removidas.
- **Correção real de um defeito latente (SC2251):** no E2E, `! git show-ref --verify … refs/heads/staging` **nunca reprovava**, porque `!` desliga o `errexit`. Agora é um `if` que chama `log_error`.
- **Os 6 `disable`** têm justificativa na mesma linha:
  - `SC2009` ×1, para o `ps` formatado;
  - `SC2002` ×4, para o pipe de teste `cat install.sh | bash`, que é intencional;
  - `SC2317,SC2329` ×1, no `cleanup()` do `install.sh`, chamado via trap.
- **AR1:** `test_safety_hook` virou `test_gate_check`. O `test_actual_hook` novo manda o payload real via stdin, com `Cwd` no sandbox, e confere a decisão **e** o exit (0 para allow e 2 para deny, em dev e em main).
- **AP1/AP2/AP3:**
  - o cabeçalho legado é removido no install, com o Teste 6;
  - `pattern.sub(lambda _: block, …)`;
  - a linha do CHANGELOG ficou concreta.
- Local: `run-install-verification.sh` (6/6) e suíte certificada, os dois verdes.

**Linha de base avançada** para `6e0e8de`.

## 2. Ressalvas

### AS1 — MÉDIO (determinismo): o shellcheck bloqueante roda em versões diferentes por SO

- O Ubuntu usa o pacote do `apt` (versão não registrada; a lição aprendida diz "0.8.0 / 0.9.0"), e o macOS usa o `brew` (0.11.x, rolling release).
- Com o passo agora **bloqueante**, qualquer atualização do Homebrew pode deixar o CI **vermelho sem mudança de código**, exatamente o que aconteceu em `6d565f1`.
- A mitigação da lição aprendida (inlinar traps) resolve **esta** regra. Ela não torna o código "imune em qualquer versão", como o documento afirma. Uma regra nova da 0.12 reabre o problema.
- **Correção:** fixar uma única versão do shellcheck e rodá-lo em um único job.

### AS2 — BAIXO (processo): o controle negativo entrou na branch misturado com a limpeza

- O commit `1893cd6` ("test(ci): teste de falsificabilidade…") contém **a limpeza inteira do PR-19b** mais a injeção. O commit `6d565f1` ("chore(shell): limpeza … (PR-19b)") só remove a injeção.
- As mensagens invertem o conteúdo, e a branch ganhou dois commits vermelhos.
- **Regra daqui em diante:** o controle negativo vai para uma **branch descartável** `claude/negctl-<pr>`, que o gatilho `claude/**` já cobre. Faça o push, espere a execução vermelha, cite o link e apague a branch remota. A branch de trabalho só recebe commits que se pretendem verdes.

## 3. Trilha de CI da Onda 5: **encerrada** (PR-19, 19a, 19b)

| Antes | Agora |
|---|---|
| O CI só rodava em `main`/`staging`/`dev`; nesta branch, nunca | roda em cada push em `claude/**` |
| Só Ubuntu | Ubuntu e macOS × Python 3.9 e 3.12 |
| O one-liner `curl \| bash` estava quebrado havia dias, sem sinal | passo dedicado com `git` falso e `file://` + `cmp` |
| O bash 3.2 do macOS não era testado | guarda testada no `/bin/bash` real |
| Shellcheck ausente | bloqueante, com 0 avisos e controle negativo |
| Quatro defeitos latentes invisíveis (py3.9, E2E desatualizado, `chmod` sujando os evals, `! git show-ref` sem efeito) | corrigidos |

## 4. Despacho — dois commits, **cada um com a execução do servidor verde antes do próximo**

### Commit 1 — PR-19c `ci(shellcheck): versão fixada e job único`

1. Um passo (ou job) de shellcheck **só em `ubuntu-latest` / 3.12**. A análise estática não depende de SO. Tire o `shellcheck` do `brew install` e do `apt-get install`.
2. Instalação **fixada por versão e verificada por hash**: baixe o binário oficial de uma release específica (por exemplo, `v0.11.0`, `linux.x86_64`) do GitHub Releases do projeto `koalaman/shellcheck` e confira o SHA-256 contra um valor versionado no workflow. Registre `shellcheck --version` no log.
3. A versão fixada fica documentada no CHANGELOG, e a atualização passa a ser uma mudança consciente, num PR próprio.
4. **Corrija a lição aprendida:** troque "imune a SC2329 em qualquer versão" por "versão fixada; atualizações são PRs explícitos". Informe a versão real do `apt` que estava em uso, tirada do log de uma execução anterior, em vez de "0.8.0 / 0.9.0".
5. **Controle negativo, na branch descartável (AS2):** em `claude/negctl-19c`, injete um aviso e mostre o job do shellcheck reprovando. Cite o link e apague a branch.

### Commit 2 — PR-18 `test(content): validação de esquema no lugar de grep em Markdown` (resolve T3)

**Estado atual (`OBSERVED`, `run-all-tests.sh:143–165`):** os testes de conteúdo são `grep -q '<texto>'` em `agent.md`/`SKILL.md`. Eles passam com o texto em qualquer lugar (inclusive num comentário) e não validam estrutura.

1. **`tests/test_content_schema.py`**, registrado no `run-all-tests.sh`:
   - todo `agents/*/agent.md`, `skills/*/SKILL.md` e o `profiles/clearer-harness.agent.md` tem frontmatter YAML **válido**, com `name` e `description` não vazios. O `name` bate com o diretório (quando for a convenção);
   - toda ferramenta citada em `tools:` existe num **catálogo** versionado (`clearer-engineering/config/tool_catalog.json`). Cada entrada do catálogo cita a **evidência** de onde vem o nome: payload gravado em `docs/temp_implementation/evidence/host-probe/…` para o agy, ou a documentação vigente para o Claude. Ferramenta sem evidência não entra;
   - toda skill citada com `/nome` nos perfis e agentes existe em `skills/<nome>/SKILL.md`;
   - todo link Markdown relativo (`](./…)`, `](../…)`) em `clearer-engineering/**/*.md`, `README*.md` e `CHANGELOG.md` resolve para um arquivo existente. Âncoras (`#…`) e URLs externas ficam de fora.
2. **Os `grep -q` de estrutura** (Gates do `clearer-bugfix`, ferramentas dos agentes) passam a ser asserções do teste novo sobre o **conteúdo analisado**: seções pelo cabeçalho Markdown, ferramentas pelo frontmatter. Os `grep` que conferem **frases de política** podem ficar, mas cada um que permanecer ganha um comentário dizendo por que texto é o contrato.
3. **Fuzz do lexer com semente fixa** (`random.Random(1337)`), em `tests/test_lexer_fuzz.py`:
   - composições de 1 a 4 segmentos, tirados de listas de segmentos **seguros** e **destrutivos** (reaproveite as da bateria e do corpus), com separadores `;`, `&&`, `||`, `|`, quebra de linha e subshell `( … )`, e com aspas simples ou duplas em volta de argumentos;
   - **invariante:** com `--env production` e qualquer segmento destrutivo, a decisão **nunca** é `allow`;
   - N fixo (por exemplo, 2.000 casos), com tempo registrado. Uma falha imprime o comando mínimo que reproduz.
4. **Falsificabilidade:**
   - esquema: num clone, apague o `description` de uma skill e aponte um link para um arquivo inexistente; o teste reprova, citando **o arquivo e a linha**;
   - fuzz: num clone, faça o separador `||` deixar de dividir segmentos (ou desligue a varredura de sufixos); o fuzz reprova com o comando mínimo.
5. **Achados do próprio teste:** se o teste novo encontrar links quebrados ou frontmatter inválido **hoje**, corrija neste commit e liste cada correção na evidência. Não afrouxe o teste para passar.

### Critérios de aceite

- [ ] PR-19c: shellcheck fixado por versão e hash, num job, com a lição corrigida e o controle negativo numa branch descartável.
- [ ] PR-18: o teste de esquema e o fuzz do lexer estão na suíte, com prova por mutação para os dois. Os achados estão corrigidos e listados.
- [ ] Cada commit tem a **sua** execução do servidor verde (4/4) antes do próximo push. A evidência vem depois do servidor, com links dos jobs da execução citada.
- [ ] As redes diferenciais contra `6e0e8de` registram 0 relaxamentos. O plano não é editado pelo agente, e a homologação não é declarada pelo agente.

## 5. Release v1.3.0

Continua desbloqueada e com o desenvolvedor ([Handoff 044 §3](./handoff-044-revisao-pr19a-ci-verde-despacho-pr19b.md)). Com o PR-19b, o CI exige **shellcheck limpo**. Antes da tag, o bloco `[Unreleased]` do CHANGELOG (PR-19, 19a e 19b) vai para `[1.3.0]` ou para uma `[1.3.1]`. Decisão do desenvolvedor.

## 6. Sequência

PR-19c + PR-18 → PR-QA B–D (invariante do motivo, contrato com `--help`, normalização única) e AM2 → PR-20 (índice de ADRs e promessas verificáveis) → PR-21 (redação de segredos no Conselho) → Onda 4 quando houver evidência de um 3º host.
