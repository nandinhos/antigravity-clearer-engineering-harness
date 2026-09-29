# Handoff 041 — PR-11b homologado com ressalva, PR-12 **não homologado** (one-liner quebrado); despacho do PR-12b

**Data/Hora:** 2026-09-27T17:00:00Z
**Instância:** Revisor sênior
**Branch:** `claude/code-review-technical-analysis-kfwcdl`
**Commits revisados:** `74fdd12` (PR-11b), `0e14a09` (PR-12)
**Antecessor:** [Handoff 040](./handoff-040-revisao-pr11-despacho-pr11b-pr12.md)

---

## 1. Vereditos

### PR-11b: **HOMOLOGADO COM RESSALVA** (AO1)

Reproduzido num `HOME` temporário, com `agy` falso no `PATH` (`OBSERVED`):

- **AN1:** `export A=1` (sem `\n` final) → install → o usuário apaga a linha em branco antes do bloco → uninstall → `export A=1` intacto.
- **AN2:** `# alias ceh=antigo`, `alias ceh='meu-script'` e `export B=2` saem intactos do install + uninstall.
- **AN3:**
  - `python3` falso que sai com 1 → uninstall com **exit 1**, sem anunciar sucesso;
  - rc que não é UTF-8 → `Erro ao ler …`, exit 1.
- **Falsificabilidade, reproduzida em dois clones independentes:**
  - com a remoção cega `remove_start = max(0, start_idx - prefix_len)` restaurada, aparece `ERRO AN1` (exit 1);
  - com o laço por linha trocado pelo `re.sub(rf'alias {nome}=.*?\n', …)` sem âncora, aparece `ERRO AN2` (exit 1).
- **Processo:** um `--amend` local antes do primeiro push não reescreveu nada que já estivesse publicado. AK1 cumprido: cada commit foi certificado e enviado separadamente.

### PR-12: **NÃO HOMOLOGADO** (AO2)

**O que está correto:**
- `plugin.json` = `1.3.0`, e não há outra versão do CEH no código (o `1.0.0` do `run-e2e-simulation.sh` é do projeto de exemplo).
- O perfil foi extraído e é idêntico ao heredoc antigo, exceto por uma linha em branco final.
- Há teste de identidade `cmp -s`.
- A tag não foi criada.

**O que bloqueia:** a funcionalidade principal (instalar uma versão fixada pelo one-liner) **não funciona pelo caminho documentado**, e nenhum teste passa por esse caminho.

**Linha de base avançada** para `0e14a09`. O gate não mudou, e a suíte certificada está verde no HEAD.

## 2. Achados

### AO2 — ALTO (preexistente desde `b7df47d`; bloqueia o PR-12): o `curl … | bash` documentado não instala nada

```
$ cat install.sh | HOME=<tmp> bash
bash: line 391: BASH_SOURCE[0]: unbound variable      # exit 1
```

- **Causa:** `install.sh:360`, `if [[ "${BASH_SOURCE[0]}" == "${0}" ]]`, sob `set -u`. Via stdin, o `BASH_SOURCE` fica vazio.
- **O mesmo erro aparece em `dbeaad5` e `d59c943`.** O one-liner do README está quebrado desde 23/09, e o `CEH_VERSION` do PR-12 só é lido nesse caminho.
- **Armadilha na correção:** trocar por `${BASH_SOURCE[0]:-}` sozinho **não basta**. A comparação `"" == "bash"` dá falso, e o script sai com exit 0 **sem instalar nada**, uma falha silenciosa pior que a atual.
- Os testes (`run-install-verification.sh`, `cluster3`) só rodam `bash install.sh` a partir da árvore local. Por isso nenhum deles viu o problema.

### AO3 — MÉDIO: a versão fixada pode ser ignorada em silêncio

- `setup_source_directory` decide se usa a árvore local por `dirname "$0"`. Via pipe, `$0` é `bash`, e `dirname` dá `.`. Se o usuário rodar o one-liner **de dentro** de um clone do CEH, o instalador usa a árvore do diretório atual e **ignora o `CEH_VERSION`** sem aviso.
- O README fixado baixa o `install.sh` da `main` (`…/main/install.sh | CEH_VERSION=1.3.0 bash`). A lógica de instalação vem da `main`, e só os arquivos vêm da tag. A URL fixada é `…/v1.3.0/install.sh`.

### AO1 — MÉDIO: a heurística `\.sh` apaga aliases do próprio usuário (install **e** uninstall)

O filtro de órfão aceita, além das assinaturas pedidas, qualquer valor que case com `(detect|setup-branches|preflight|evals|monitor|task-monitor|doc-audit|conselho-seniores|ceh-help|help)\.sh`.

| rc original | Depois do **install** |
|---|---|
| `alias ceh-help='bash ~/bin/help.sh'`, `alias ceh-monitor='bash ~/tools/monitor.sh'` | **as duas linhas somem** |

- **Origem:** a heurística existe só para satisfazer a fixture sintética do `cluster3_acceptance.py:92–95` (`bash legacy/detect.sh`, `legacy/monitor.sh`, `legacy/help.sh`).
- O `git log -p install.sh` mostra que **todo** valor real já instalado contém `plugins/clearer-engineering/` ou `--agent clearer-harness`. A fixture descreve uma instalação que nunca existiu.
- A regra também está **duplicada** no `install.sh:276–298` e no `uninstall.sh:95–110`, e a mesma falha aparece nos dois lugares.

### AO4 — MÉDIO (honestidade documental): o CHANGELOG promete mais do que o ADR 007

- "Non-tamperable certificate protection" e "**Inviolable integrity guarantee** for `.ceh/`" contradizem o ADR 007 §2 ("Defesa em Profundidade e Limitações Inerentes"). O gate não é sandbox, e a garantia real vem da branch protection no servidor.
- "Zero-tolerance pipeline red" e "Fixed mock runner tautologies" não dizem o que mudou.

### AO5 — BAIXO: o teste do AN1 não vê `\n` a mais

`AN1_RESULT=$(cat …)` remove as quebras de linha finais, então `export A=1\n\n` passaria como `export A=1`. Compare byte a byte com `cmp` contra um arquivo esperado.

## 3. Despacho — PR-12b `fix(install): one-liner funcional, versão fixada honesta e remoção de órfãos sem heurística`

Um commit, certificado e enviado (AK1).

1. **AO2:** o `main` é executado quando o script é **executado** (arquivo ou stdin) e não quando é carregado com `source`.
   - Por exemplo: `if [[ ${#BASH_SOURCE[@]} -eq 0 || "${BASH_SOURCE[0]}" == "$0" ]]`. Confira o comportamento no bash real, sem supor.
   - Via stdin, nunca sair com exit 0 sem ter instalado.
2. **AO3:**
   - a árvore local só é usada quando o script roda **de um arquivo** (`BASH_SOURCE[0]` não vazio), resolvida pelo diretório do `BASH_SOURCE[0]`, e não pelo `$0` nem pelo diretório atual;
   - com `CEH_VERSION` definido e a árvore local em uso, emita um aviso explícito de que a versão foi ignorada, ou aborte. Nunca ignore em silêncio;
   - o README (EN e PT) publica a URL fixada: `…/v1.3.0/install.sh | CEH_VERSION=1.3.0 bash`, avisando que ela só funciona depois da tag.
3. **AO1:**
   - a regra de órfão passa a morar num **único** helper (por exemplo, `clearer-engineering/scripts/rc_aliases.py`), chamado pelo `install.sh` e pelo `uninstall.sh`;
   - um órfão é removido só quando `^alias <nome>=`, com nome conhecido, e o valor é **idêntico** a uma linha do `aliases.sh` ou contém `plugins/clearer-engineering/` ou `--agent clearer-harness`. **Sem** a heurística `\.sh`;
   - a fixture do `cluster3_acceptance.py:92–95` passa a usar valores **reais** do histórico (por exemplo, `bash ~/.gemini/config/plugins/clearer-engineering/scripts/detect-project.sh .`).
4. **AO4:** reescreva as linhas do CHANGELOG em termos verificáveis. Por exemplo: "gate bloqueia escrita em `.ceh/` pelo terminal e pelas ferramentas de escrita (defesa em profundidade; ver ADR 007 — a garantia real é o status check obrigatório no servidor)". Tire "inviolable", "non-tamperable" e "zero-tolerance", e descreva concretamente o que mudou nas redes diferenciais.
5. **Testes** no `run-install-verification.sh`, **sem rede**, com um `git` falso no `PATH` que registra os argumentos e copia a árvore local para o destino do clone:
   - **pipe:** `cat install.sh | bash`, a partir de um diretório **fora** do repositório → exit 0, plugin instalado e o `git` falso chamado **sem** `--branch`;
   - **pipe fixado:** `cat install.sh | CEH_VERSION=1.3.0 bash` → o `git` falso recebeu `--branch v1.3.0`. `CEH_VERSION=v1.3.0` também resulta em `v1.3.0`;
   - **pipe dentro de um clone** com `CEH_VERSION` → usa a versão pedida ou avisa/aborta, conforme o item 2. Nunca instala a árvore local em silêncio;
   - **AO1:** `alias ceh-help='bash ~/bin/help.sh'` e `alias ceh-monitor='bash ~/tools/monitor.sh'` sobrevivem ao install e ao uninstall, **byte a byte**;
   - **AO5:** o teste do AN1 compara com `cmp`.
   - **Falsificabilidade:** num clone, restaure a linha 360 original e mostre o teste de pipe reprovando. Restaure a heurística `\.sh` e mostre o teste do AO1 reprovando. Descreva exatamente as linhas mutadas.

### Critérios de aceite

- [ ] O one-liner (pipe) instala, com e sem `CEH_VERSION`, coberto por teste sem rede.
- [ ] A versão fixada nunca é ignorada em silêncio. O README publica a URL da tag.
- [ ] A regra de órfão está num único lugar, sem heurística, e os aliases do usuário sobrevivem byte a byte.
- [ ] O CHANGELOG é coerente com o ADR 007.
- [ ] Prova por mutação para o AO2 e o AO1.
- [ ] As duas redes diferenciais contra `0e14a09` registram 0 relaxamentos. Protocolo 7.1. O plano não é editado pelo agente, e a homologação não é declarada pelo agente.

## 4. Sequência

PR-12b → **Onda 3 encerrada** → merge e tag `v1.3.0` (decisão do desenvolvedor) → Onda 5 → Onda 4.
