# Handoff 040 — PR-11 homologado com ressalvas; despacho do PR-11b (uninstall seguro) e do PR-12

**Data/Hora:** 2026-09-27T16:00:00Z
**Instância:** Revisor sênior
**Branch:** `claude/code-review-technical-analysis-kfwcdl`
**Commit revisado:** `d59c943` (PR-11)
**Antecessor:** [Handoff 039](./handoff-039-encerramento-onda-2-despacho-onda-3.md)

---

## 1. Veredito: **HOMOLOGADO COM RESSALVAS**

Reproduzido de forma independente (`OBSERVED`):

- **Validação honesta:** o `install.sh:201` captura o exit real do `agy plugin validate`. Falha → exit ≠ 0, exceto com `--skip-diagnostics` (aviso registrado no log).
- **Autodiagnóstico:** 3 checagens a partir da árvore instalada (`rm -rf /` = deny, `ls` = allow, hook com stdin vazio = exit 2). Qualquer divergência aborta, salvo com `--skip-diagnostics`.
- **Fonte única de aliases:** `clearer-engineering/config/aliases.sh` (11 aliases), lido pelo `install.sh` e pelo `uninstall.sh`.
- **Testes:** `run-install-verification.sh` com os 4 testes, registrado no `run-all-tests.sh:250`. Suíte certificada verde (58 testes).
- **Falsificabilidade:** num clone, troquei a linha 201 por `validate_output=$(agy plugin validate … 2>&1 || true)`, que restaura o comportamento antigo (a falha é engolida e `validate_status` fica 0). O Teste 4 reprova e o script sai com exit 1.
  - **Observação:** acrescentar `|| true` **ao fim** da linha atual (`… || validate_status=$? || true`) **não** é uma mutação válida, porque o status continua sendo capturado. Numa prova por mutação, descreva a linha mutada exatamente.
- O commit não tocou o gate, o plano nem as fixtures. Um único commit certificado e enviado (AK1 cumprido).

**Linha de base avançada** para `d59c943` (sem mudança no gate).

## 2. Ressalvas

Instalação feita num `HOME` temporário, com `agy` falso no `PATH`.

### AN1 — ALTO: o uninstall apaga caracteres do usuário quando o prefixo foi editado

O `install.sh` grava `# CEH_RC_PREFIX_LEN: <N>`, e o `uninstall.sh` apaga **cegamente** os `N` caracteres anteriores ao bloco.

| Passo | Conteúdo do `~/.bashrc` |
|---|---|
| original | `export A=1` (sem `\n` final) |
| depois do install | `export A=1\n\n# BEGIN … # CEH_RC_PREFIX_LEN: 2 …` |
| o usuário apaga a linha em branco antes do bloco | `export A=1\n# BEGIN …` |
| depois do uninstall | **`export A=`** |

O `1` do usuário foi apagado. O uninstall pode corromper qualquer configuração cuja última linha antes do bloco tenha sido editada (formatadores de dotfiles fazem isso sozinhos).

### AN2 — ALTO: a remoção de aliases órfãos não é ancorada e comenta linhas do usuário

`uninstall.sh` usa `re.sub(rf'alias {nome}=.*?\n', '', content)`, sem `^` e sem `re.MULTILINE`. Casa **no meio** de uma linha.

| Passo | Conteúdo do `~/.zshrc` |
|---|---|
| original | `# alias ceh=antigo\nexport B=2\n` |
| depois de install + uninstall | **`# export B=2\n`** |

O `export B=2` do usuário foi **desativado**, sem aviso. A mesma regex também apaga um `alias ceh='…'` que o próprio usuário tenha definido, apontando para outra coisa.

### AN3 — BAIXO: o uninstall engole os próprios erros

O bloco Python termina em `2>/dev/null || true`, e o script sempre anuncia "uninstalled successfully". É o mesmo defeito que o PR-11 corrigiu no install.

## 3. Despacho — dois commits nesta rodada, **um push por commit certificado** (AK1)

### Commit 1 — PR-11b `fix(uninstall): remoção sem efeito colateral no rc do usuário`

1. **AN1:** remova **apenas** os `\n` que de fato estão imediatamente antes do bloco, até o limite `N` do marcador. Nunca remova outro caractere. Sem o marcador (bloco legado), `N = 0`.
2. **AN2:** a remoção fora do bloco passa a ser **por linha inteira**, com `re.MULTILINE` e âncora `^alias <nome>=`. Só sai a linha cujo valor é uma definição CEH: ou é idêntica a uma linha do `aliases.sh`, ou contém a assinatura `--agent clearer-harness` ou `plugins/clearer-engineering/`. Linhas comentadas e aliases do usuário com outro valor ficam intactos.
3. **AN3:** falha do bloco Python → mensagem de erro e exit ≠ 0. Nada de `2>/dev/null || true`.
4. **Testes** no `run-install-verification.sh`:
   - **AN1:** rc sem `\n` final; install; o teste apaga a linha em branco antes do bloco; uninstall → o conteúdo do usuário (`export A=1`) está intacto. Critério: **nenhum caractere diferente de `\n` é removido fora do bloco**;
   - **AN2:** rc com `# alias ceh=antigo`, `alias ceh='meu-script'` e `export B=2`; install + uninstall → as três linhas estão idênticas às originais;
   - **AN2 (órfão legítimo):** rc com uma linha legada `alias ceh-help='bash ~/.gemini/config/plugins/clearer-engineering/scripts/ceh-help.sh'`, fora de qualquer bloco → é removida;
   - **AN3:** um `python3` falso no `PATH` que sai com exit 1 faz o uninstall sair com exit ≠ 0, sem anunciar sucesso. Não use `chmod 444`, porque como root a escrita passa. Um rc que não é UTF-8 válido também não pode cair num `sys.exit(0)` silencioso.
   - **Falsificabilidade:** num clone, restaure a remoção cega (`start_idx - prefix_len`) e a regex sem âncora, e mostre os testes reprovando. Descreva as linhas mutadas exatamente.

### Commit 2 — PR-12 `build(release): SemVer, CHANGELOG e instalação fixada por versão`

Sem mudanças em relação ao [Handoff 039 §3](./handoff-039-encerramento-onda-2-despacho-onda-3.md):

- versão única `1.3.0` no `plugin.json`;
- `CHANGELOG.md` no formato Keep a Changelog, com a seção 1.3.0 incluindo o PR-11/11b;
- `CEH_VERSION` no one-liner, clonando `--branch v<versão>`;
- perfil extraído para `clearer-engineering/profiles/clearer-harness.agent.md`, com teste de identidade.

**A tag `v1.3.0` não é criada pelo agente.**

### Critérios de aceite da rodada

- [ ] PR-11b: os 4 casos novos estão verdes no `run-install-verification.sh`, com a prova por mutação.
- [ ] PR-12: conforme o Handoff 039 §3.
- [ ] Cada commit certificado e enviado **separadamente** (AK1).
- [ ] As duas redes diferenciais contra `d59c943` registram 0 relaxamentos.
- [ ] O plano não é editado pelo agente, e a homologação não é declarada pelo agente.

## 4. Sequência

PR-11b + PR-12 → **Onda 3 encerrada** → merge e tag `v1.3.0` (decisão do desenvolvedor) → Onda 5 (qualidade: PR-QA B–D, AM2, shellcheck, matriz macOS) → Onda 4 quando houver evidência de um 3º host.
