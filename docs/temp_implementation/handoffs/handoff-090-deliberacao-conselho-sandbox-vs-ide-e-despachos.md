# Handoff 090 — Deliberação do Conselho sobre o Handoff 089: decisões finais e ordem dos PRs

**Data/Hora:** 2026-10-01T22:00:00Z
**Instância:** Revisor independente (Claude)
**Estado:** **CONFORME**. As decisões D1–D6 estão fechadas e os despachos podem ser executados na ordem da seção 6.
**Entrada:**
- [Handoff 089](./handoff-089-plano-deliberacao-sandbox-vs-ide.md), commit `bfa3654`;
- sessão do Conselho [`20261001_090830`](../conselho/20261001_090830/ata_conselho.md), commit `8a4898e`.

**Antecessor:** [Handoff 089](./handoff-089-plano-deliberacao-sandbox-vs-ide.md)
**Substitui:** o rascunho deste arquivo publicado no `8a4898e` (ver a seção 7).

---

## 1. Reclassificação dos votos

A ata registrou **3/3** votos com ressalvas e dois **INDEFINIDO**. Isso foi falha de extração do `conselho-seniores.sh`, não abstenção. O voto abaixo foi lido no texto de cada parecer:

| Conselheiro | Ata | Voto no parecer | Onde está | Certeza |
|---|---|---|---|---|
| claude | RESSALVAS | RESSALVAS | `parecer_claude.md` | 0.78 |
| codex | INDEFINIDO | **RESSALVAS** | `parecer_codex.md`, linhas 181 e 204 | 0.86 |
| muse | RESSALVAS | RESSALVAS | `parecer_muse.md` | 0.86 |
| hermes | INDEFINIDO | **HOMOLOGADO COM RESSALVAS** (equivale a RESSALVAS) | `parecer_hermes.md`, linha 87 | 0.88 |
| agy | RESSALVAS | RESSALVAS | `parecer_agy.md` | 0.95 |
| agent | ERRO_EXECUCAO | **não votou** | `parecer_agent.md` | — |

**Resultado formal: 5/5 com ressalvas, 0 rejeições.** Certeza média de 0.87 (0.866 sem arredondar).

### Por que a extração falhou

- **Codex:** o parecer começa com o eco do prompt, que contém o modelo `VEREDITO: [HOMOLOGADO | RESSALVAS | REJEITADO]` (linha 171). O extrator pegou essa primeira ocorrência, não o veredito real.
- **Hermes:** o voto global é `HOMOLOGADO COM RESSALVAS`, que não está entre os três valores aceitos.
- **Agent:** o CLI do Cursor parou no prompt "Workspace Trust Required" e precisa de `--trust`. O rascunho falava em "erro de conexão RPC"; o artefato bruto mostra que não foi isso.

### Correções sugeridas para o `conselho-seniores.sh`, como carona do PR de infraestrutura

1. Extrair a **última** linha `VEREDITO:` do parecer, ignorando as que contêm `[`.
2. Normalizar `HOMOLOGADO COM RESSALVAS` para `RESSALVAS`.
3. Passar `--trust` ao `agent` (ou registrar o erro como "não votou", em vez de "inconclusivo").
4. Calcular o placar sobre os votos válidos e mostrar os não votantes à parte.

**Lembrete (D6):** a ata registra opinião. Esta reclassificação corrige a contagem, mas não transforma o Conselho em homologação de código.

## 2. Correção do Handoff 088: CA1 rebaixado de MÉDIA para BAIXA

O 088 justificou a gravidade do CA1 assim: "um agente pode reescrever o `.ceh/config.json` e obter um certificado canônico de um comando trivial". **Isso não se sustenta na v2.1.0.** As linhas 57–58 do `test-runner.sh` citadas no 088 só valem **fora** de um repositório git. Dentro de um repositório, um `config.json` não versionado ou alterado vira `CONFIG_OK=0` (linhas 48–55).

Verificação (`OBSERVED`, cópia temporária, `test-runner.sh` da `origin/main`): repositório git com `.ceh/config.json` local `{"canonical_test_command":"true"}`, seguido de `bash test-runner.sh true`:

```
[CEH WARNING] ⚠️ .ceh/config.json é inválido. Este comando NÃO concederá certificado válido para git push.
[CEH WARNING] ⚠️ Worktree com alterações não commitadas. Os testes rodam, mas o certificado NÃO será emitido.
```

Nenhum `last-ci-run.json` foi gerado.

**Nova classificação do CA1:** **BAIXA**.
- Continua sendo uma lacuna da invariante documentada ("o agente não escreve no `.ceh/`", A1.6), e escrever no `.ceh/` por redirecionamento colado continua dando allow.
- O efeito comprovado é só invalidar o selo, ou seja, falha fechada. Não há caminho de forja comprovado.
- A D5 continua valendo, porque a correção é pequena e pina a invariante, mas deixa de ser urgente.

## 3. Decisões finais

### D1 — Barreira no servidor: **opção A**

Ruleset na `main` com:
- PR obrigatório, com **0 aprovações**. Com um único mantenedor, exigir aprovação trava o merge e acaba forçando o bypass;
- **bypass list vazia**, sem exceção para administradores;
- sem force push e sem apagar a branch;
- check obrigatório, em duas fases:
  1. **agora:** os quatro jobs que existem hoje:
     - `Validate (ubuntu-latest - Python 3.9)`
     - `Validate (ubuntu-latest - Python 3.12)`
     - `Validate (macos-latest - Python 3.9)`
     - `Validate (macos-latest - Python 3.12)`
  2. **depois do merge do PR de infraestrutura:** trocar pelo job agregador `ci-ok`. O `ci-ok` **ainda não existe**; exigi-lo antes trava todo merge.

Prova, colhida pelo **desenvolvedor**:
1. **positiva:** consulta **autenticada** que retorne o ruleset ativo (`gh api repos/<owner>/<repo>/rulesets` e o detalhe do ruleset), com a saída bruta. Um print de *Settings → Rules* serve como complemento;
2. **negativa:** um push direto para a `main` rejeitado, com o stderr bruto. Use um commit descartável numa branch local e não o mantenha depois.

### D2 — Matriz "onde cada verificação vale": **aprovada, com colunas novas**

- **Colunas:** sandbox da revisão, CI Linux, CI macOS, IDE-Linux, IDE-macOS, **agy CLI headless** e Claude Code CLI local.
- **Formato de cada evidência:** a tupla do Codex, (alegação, ambiente, versão, entrada, observação, método). Uma afirmação `OBSERVED` sem o ambiente certo vira `INFERRED`.
- **Proteção da `main`:** no sandbox, só vale como `OBSERVED` se a consulta autenticada retornar o ruleset. O revisor não tem `gh`, então essa prova é do desenvolvedor.
- **Onde fica:** `docs/adapters/novo-host.md` e o guia de contribuição.

### D3 — Evidência da IDE: **opção A, fundida no `ceh-doctor --evidence`**

Um script só, em vez de dois com o mesmo núcleo:
- **POSIX `sh`**, compatível com o bash 3.2 do macOS;
- sem `readlink -f` e sem `date --iso`;
- hash com `sha256sum`, ou `shasum -a 256`, ou Python, nessa ordem;
- Python opcional.

O que ele registra:
- `date -u`;
- o hash do gate instalado contra o da tag;
- a lista de plugins concorrentes;
- os índices dos passos da transcrição da chamada e da resposta, que são a ressalva BK1;
- um manifesto com o hash de cada arquivo.

Limites declarados no próprio script:
- **O hash prova integridade, não autenticidade.** Quem gera o pacote pode gerar outro.
- O **canário de release** é rodado pelo **desenvolvedor**, no terminal dele, fora da sessão do agente.
- Ninguém deve tratar o pacote como prova de que o agente não interferiu.

Gravação de tela (opção C): descartada.

### D4 — Paridade de ambiente: **aprovada, com o casefold restrito** (seção 4)

1. **Job no CI** com as variáveis `CLAUDE*` capturadas de uma sessão real (não só `CLAUDECODE` e `CLAUDE_PROJECT_DIR`), rodando a suíte canônica. Fica dentro do `ci-ok`.
2. **Helper de diretório temporário** já resolvido, usado pelos testes no lugar de `tempfile.mkdtemp()` puro. Sem teste estático por grep.
3. **Casefold** só onde a seção 4 define.
4. **`ceh-doctor`**, que também cobre a D3:
   - `--verify` compara o **conjunto** de arquivos instalados, não só o hash do gate;
   - acrescentar `--self-check`.
5. **Teste de independência de ambiente:** a **decisão** do gate não muda com as variáveis `CLAUDE*` presentes ou ausentes, quando o payload identifica o host.
   - A detecção de host por variável na reserva (`adapters/fallback.py`) é exceção documentada.
   - Não é "o gate nunca lê o ambiente".

### D5 — PR `v2.1.1`: **CA1 + CA2 num PR só**

**CA1 (correção no processo do gate):** negar quando o **alvo** de qualquer redirecionamento resolver para dentro de `.ceh/`.
- Formas de redirecionamento: `>`, `>>`, `>|`, `&>`, `&>>`, `N>`, `N>>`, `<>`, coladas ou com espaço.
- Excluir as duplicações de descritor (`2>&1`, `>&2`).
- Resolução do alvo: `..`, symlink, o alias `/var` → `/private/var` e o casefold do componente `.ceh`.
- Cobrir também `tee`, `dd of=`, `cp`, `mv`, `install` e `ln` com destino no `.ceh/`.

**Commits na ordem:**
1. a correção;
2. os controles no corpus dourado: F01–F10, as formas do CA1 com os controles negativos e as variantes de caixa e de `/var`;
3. o avanço do `gate_baseline`.

**Métrica de falso positivo**, critério do Hermes adaptado:
- diff linha a linha do corpus contra a v2.1.0;
- toda decisão antiga que mudar tem que estar na lista de apertos declarados no PR;
- qualquer mudança fora da lista reprova;
- leituras do `.ceh/` (CA5) não podem passar a ser negadas por um caminho novo.

**Limite declarado:** o gate é estático e não fecha TOCTOU, isto é, o alvo trocado entre a verificação e a execução. Fica registrado no ADR 007.

**CA5–CA8** vão num PR de documentação separado.

### D6 — Papéis: **aprovada**

- "Homologado" exige o comando e a saída reproduzíveis. Sem isso, não vale como homologação.
- A geração do certificado pelo `test-runner.sh` é **autorizada**. A edição manual do `.ceh/` é proibida. O gate precisa distinguir as duas, e a regra fica escrita no guia.
- Papel novo: **operador do release**, que cria a tag e a release e roda o canário. É o desenvolvedor, ou quem ele designar por escrito.
- A tabela de papéis do Handoff 089, §D6, entra no guia de contribuição.

## 4. D4 — por que o casefold é restrito

O rascunho propunha `lower()` incondicional no parser. **Isso não foi adotado.** Esta revisão mediu o efeito sobre o corpus dourado. O teste aplicou `evaluate_command(cmd.lower())` contra `evaluate_command(cmd)`, nos três ambientes, num repositório temporário na branch `dev`, aos 46 comandos do corpus que têm maiúsculas, num total de 331:

| | Decisões |
|---|---|
| alteradas | **23** |
| afrouxadas (deny → ask/allow ou ask → allow) | **16** |
| apertadas (falso positivo novo) | 7 |

Exemplos `OBSERVED`:

| Comando | Ambiente | Hoje | Com `lower()` |
|---|---|---|---|
| `rm -rf $HOME` | development | deny | **ask** |
| `rm -rf $PWD` | staging | deny | **ask** |
| `git checkout -B main` | production | deny | **allow** |
| `git switch -C main` | production | deny | **allow** |
| `git restore -W -S .` | production | deny | **allow** |
| `git -C sub status` | production | allow | deny |

Variáveis de ambiente (`$HOME`), opções (`-B` ≠ `-b`, `-C` ≠ `-c`) e nomes de branch diferenciam maiúsculas no shell e no git. Aplicar `lower()` no comando inteiro abriria bypasses. Por isso o casefold vale **só** em dois pontos:

1. **No basename do executável** (`argv[0]`, depois de tirar o caminho), para identificar a ferramenta: `GIT`, `Git` e `/usr/bin/GIT` são tratados como `git`. Os argumentos ficam intactos.
2. **No componente `.ceh`** dos alvos de escrita e de redirecionamento: `.CEH/x` e `.Ceh/x` são tratados como `.ceh/x`.

Aplicar sempre, não só no Darwin, porque o custo de falso positivo é desprezível nesses dois pontos. O PR tem que provar que **nenhuma** decisão do corpus atual muda, exceto as variantes de caixa novas declaradas.

## 5. Ressalvas do Hermes: o que foi acolhido

| # | Proposta | Destino | Motivo |
|---|---|---|---|
| H1 | Job de CI que verifica o próprio ruleset | **adiada** | exige um token com permissão administrativa como segredo do CI, o que é uma superfície nova; a prova autenticada da D1 cobre o objetivo por agora |
| H2 | `docs/gate-normalization.md` | **acolhida** | carona do PR de infraestrutura: documenta o casefold restrito da seção 4 e a resolução de caminhos da D5 |
| H3 | CI que bloqueia a tag sem ata do Conselho | **rejeitada** | contraria a D6 (o Conselho não homologa) e o Conselho é um add-on opcional |
| H4 | Limite de falso positivo antes de avançar o baseline | **acolhida, adaptada** | virou o critério de diff do corpus da D5: zero mudanças fora dos apertos declarados, em vez de 5% |
| H5 | Exercício adversarial do `ceh-doctor --evidence` | **adiada** | depois que o script existir |
| H6 | Auditoria retroativa das tags | **rejeitada** | as tags v2.0.0 e v2.1.0 já foram revisadas (Handoffs 086 e 088); o custo não traz informação nova |
| H7 | HMAC, fonte de tempo externa e evidência anexada à release | **rejeitada** (HMAC e tempo externo); **adiada** (anexo) | o agente teria acesso à chave, e o tempo externo depende de rede; anexar o pacote à release fica para depois do H5 |
| H8 | Cobrir todas as variáveis `CLAUDE*` | **acolhida** | D4, item 1 |
| H9 | `--self-check` no `ceh-doctor` | **acolhida** | D4, item 4 |
| H10 | Teste de que o gate não usa o ambiente nas decisões | **acolhida, restrita** | D4, item 5, com a exceção da reserva |
| H11 | Papel "operador do release" | **acolhida** | D6 |
| H12 | WSL na matriz | **adiada** | o WSL não é host suportado hoje; entra na D2 quando for |

## 6. Ordem dos PRs e despachos

| # | Despacho | Quem | Critério de aceite |
|---|---|---|---|
| **1** | **D1** — ruleset na `main` (seção 3, com os quatro `Validate` como check) | desenvolvedor, no GitHub | consulta autenticada com o ruleset ativo + push direto rejeitado, ambos com a saída bruta, registrados num arquivo de evidência **por PR** (não mais direto na `main`) |
| **2** | **PR de infraestrutura** (D4 + D3 + docs D2/D6 + H2): <ul><li>job `ci-ok` (`needs: validate`, falha se algum `Validate` falhar)</li><li>job com as `CLAUDE*` dentro do `ci-ok`</li><li>helper de diretório temporário</li><li>casefold restrito (seção 4) com controles no corpus</li><li>`ceh-doctor` (`--verify`, `--self-check`, `--evidence`) em POSIX `sh`</li><li>`docs/gate-normalization.md`</li><li>matriz D2 e papéis D6 no guia</li><li>correções do extrator do Conselho (seção 1)</li></ul> | agente, na IDE; revisão no sandbox | CI verde nos quatro `Validate` e no `ci-ok`; diff do corpus só com as variantes de caixa declaradas; `ceh-doctor` executado no CI macOS (bash 3.2); `ceh-doctor --evidence` executado na IDE com o pacote bruto |
| **3** | Trocar o check obrigatório para `ci-ok` | desenvolvedor | consulta autenticada mostrando o `ci-ok` no ruleset |
| **4** | **PR `v2.1.1`** (D5: CA1 + CA2, três commits na ordem) | agente, na IDE; revisão no sandbox | CI verde; diff do corpus contra a v2.1.0 só com os apertos declarados; canário da IDE pelo `ceh-doctor --evidence`, rodado pelo desenvolvedor |
| **5** | PR de documentação (CA5–CA8; CA6 com a ampliação do `doc-audit` para `docs/audit/`) | agente | `doc-audit` sem caminhos de home em `docs/audit/` |

O casefold fica no PR 2, e não no `v2.1.1`, porque o PR 2 é que muda o parser. O `v2.1.1` só reutiliza a normalização para os alvos do `.ceh`.

Se o desenvolvedor preferir um PR menor, o casefold pode descer para o `v2.1.1`. Nesse caso, o PR 2 fica só com infraestrutura e documentação.

## 7. Registro de processo

- O rascunho deste Handoff e a seção 0.81 do plano foram escritos pelo agente de execução no `8a4898e`, na branch da revisão, a pedido do desenvolvedor. Isso foge da D6, porque o agente não edita o plano. Os dois foram **substituídos** por esta versão.
- **Divergências do rascunho corrigidas aqui:**
  - "5/5, unânime" sem a ata mostrar isso: a ata registra 3/3 e dois indefinidos (seção 1);
  - "erro de conexão RPC": foi o prompt de *workspace trust*;
  - `lower()` incondicional no parser: abriria bypasses (seção 4);
  - check obrigatório "`ci-ok` (após PR de D4)" no despacho da D1: o check não existe ainda (seção 3, D1);
  - "despacho soberano" com base em "deliberação unânime": os despachos estão na seção 6 e decorrem desta revisão, com a decisão final do desenvolvedor.
- Os artefatos da sessão do Conselho (`docs/temp_implementation/conselho/20261001_090830/`) ficam como estão. Eles são o registro bruto.

## 8. Pendências que continuam abertas

- **CA3 / AY2:** a proteção da `main` só será considerada feita com a prova do despacho 1.
- **BK1:** os índices dos passos da transcrição na evidência da IDE. Passam a ser gerados pelo `ceh-doctor --evidence`.
- Codex CLI como 4º host e a troca do `clearer-muse` vendorizado (Handoff 086, §4) continuam fora desta sequência.
