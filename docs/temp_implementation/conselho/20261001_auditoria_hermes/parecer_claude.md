VEREDITO: RESSALVAS
CERTEZA: 0.82. Conferi no código as causas raiz de F02, F03, F04, F06, F07, F08, F09, F10, F11, F14 e F15. Não reproduzi nenhum dos testes RED, e as Fases C e D estão só no plano, não neste documento.

ANALISE_ESPECIALIZADA:

**As causas raiz se confirmam no código, mas há erros de linha e de nome:**
- **F03:** confirmado. `git_invocation.py` testa `tokens[0] != "git"`.
- **F04:** confirmado. As regras estão em `rules.py:52` e `:56`, e o padrão `-f\b` não pega `-vf`.
- **F06/F07:** confirmados. `test-runner.sh` grava `CANONICAL_VERIFIED=true` na linha 88, troca o comando por `sail test` na linha 122 e cai para `unittest` na linha 38.
- **F09:** confirmado. O adaptador declara `MultiEdit` e `NotebookEdit` em `claude_code.py:26`, mas `package.py` só gera os matchers `Bash` e `Write|Edit`.
- **F14 e F15:** confirmados (`package.py:138` e `evidence_report.py:126`).
- **F11:** o documento cita a linha 255, mas os `rmtree` estão nas linhas 262 e 279. São dois pontos a corrigir, não um.
- **F04:** o documento fala em `is_force`, mas `parse_push_args` devolve a chave `"force"` (`push.py:143`). É um contrato com nome errado.

**Invariantes com defeito:**
- **Invariante 2 / F02:** o snippet proposto quebra a regra que ele mesmo declara. `subcommand.py:217` só detecta o ambiente pelo repositório quando `explicit_env is None`. Se a correção passar `explicit_env="staging"` para o nível `depth+1`, essa detecção é desligada. Um `bash -c 'git -C /repo-prod push'` passaria a ser avaliado como staging, e não como production. A correção certa é passar o ambiente como *piso*: o comando interno continua detectando e no fim fica com o maior dos dois. O snippet também usa `is_higher_severity`, que não existe; o que existe é `ENV_SEVERITY`.
- **Invariante 3:** se contradiz. Fala em uma lista fixa de caminhos (`/usr/bin/git`…), mas o código proposto usa `basename` mais `endswith("/git")`, que é redundante. Basta usar `os.path.basename`, como `extract_shell_c_command` (linha 48) já faz.
- **Invariante 6:** mistura três coisas sem relação: staging atômico, marcadores de propriedade e checagem de tipo de arquivo. A "inspeção física" (`os.path.isdir`) dentro do gate cria duas fragilidades. Uma é TOCTOU: o arquivo verificado pode ser trocado antes do comando rodar. A outra é que o caminho precisa ser resolvido a partir de `base_cwd`. Para F10, uma regra sintática basta: com `-r`/`-R`, o atalho de arquivo único em `rm.py:177` deixa de valer, sem consultar o disco.

**Sobre-engenharia (Ponytail):**
- **F01:** normalizar o lexer inteiro tem o maior alcance possível, porque todas as regras dependem da tokenização. O defeito está em `is_cert_tampering`, que usa `shlex.split` cru em `rules.py:178`. A correção cabe ali: tratar como escrita qualquer `>` fora de aspas em comando que mencione `.ceh`, sem FSM nova.
- **F06:** dispensa o transporte novo via `docker compose exec`. Se `TEST_CMD` foi trocado, basta fazer `CANONICAL_VERIFIED=false`.
- **F07:** o fallback para `unittest` deve desmarcar `CANONICAL_VERIFIED`, ou abortar só quando existir `pytest.ini` ou `conftest.py`. Sem ler `pyproject` nem `setup.cfg`.
- **F11:** a flag `--force-clean` não é necessária. Basta recusar diretório que não esteja vazio e não tenha o marcador.
- **F05:** reimplementar a resolução de refs do Git (`push.default`, `remote.*.push`, `pushRemote`) é uma lista que nunca fecha. Mais simples: push sem refspec só passa se não houver `remote.<r>.push` e se `push.default` estiver ausente ou valer `simple`/`current`. Qualquer outro caso cai em FAIL_CLOSED.

**Casos de borda que faltam:**
- **F08:** `CURRENT_COMMIT` é lido em `test-runner.sh:171`, depois da suíte. Se a suíte fizer um `git commit`, o certificado vai para um HEAD que não foi testado e com a worktree limpa, então a re-checagem proposta não pega. É preciso fixar o HEAD antes e exigir que seja o mesmo depois.
- **F13:** a pasta temporária proposta, `plugins/.clearer-engineering.tmp`, fica dentro do diretório que o host varre e pode ser carregada como plugin. Além disso, `mv` sobre um diretório que já existe põe um dentro do outro em vez de substituir. "3/3" não está definido. O `install.sh` já usa `INSTALL_TMP_DIR`/`PKG_TMP_DIR`; o `rm -rf` que destrói está na linha 158.
- **F04:** a proposta inclui `--merge` como destrutivo, mas `reset --merge` aborta quando há risco. Isso amplia o escopo e gera falsos positivos sem evidência.

**Matriz de testes:**
- O resultado esperado de F04, "deny / ask conforme ambiente", não permite falsificar o teste. Cada caso precisa fixar o ambiente e um resultado único.
- F01 junta dois vetores diferentes (redirecionamento colado e cauda depois do `bash -c`) num teste só. Precisam ser testes separados.
- F14 trava o valor `2.0.0` no teste. O certo é comparar com a fonte canônica.
- Não há nenhum teste negativo contra falso positivo, por exemplo:
  - `echo "a>b"` entre aspas;
  - `cat .ceh/x` só leitura;
  - `rm -f build.log` sem `-r`;
  - `git push` com a configuração padrão.
- O documento promete preservar os 75 testes e as 5 medições, mas não define nenhum portão para comprovar isso.

**Fases:**
- A Fase A junta o gate em Python (F01–F05) e o runner em Bash (F06–F08). São riscos de natureza diferente e a reversão deveria ser independente.
- F09 é P1 (Bloco A) na abstração, mas fica na Fase B do plano. É uma incoerência de prioridade.
- As Fases C e D não aparecem no documento avaliado, então não dá para auditar se são viáveis.

RISCOS_IDENTIFICADOS:
1. **F02:** se o snippet for aplicado como está, um push em repositório de produção feito dentro de `bash -c` passa a ser avaliado com uma severidade menor.
2. **F08:** certificado emitido para um commit criado durante a suíte, que não foi testado.
3. **F01:** alterar o lexer global pode causar regressões espalhadas por todas as regras.
4. **F10:** `isdir` no gate cria uma janela TOCTOU e o resultado depende de `cwd`/`base_cwd`.
5. **F13:** a pasta temporária pode ser carregada como plugin, e um `mv` não atômico pode deixar a instalação aninhada ou pela metade.
6. **F05:** resolver toda a configuração de refs do Git vira uma denylist sem fim, o mesmo erro que o Conselho já rejeitou no Cluster 1.
7. **F11:** se corrigir só um dos dois `rmtree`, o defeito continua aberto.
8. Sem testes negativos, um GREEN pode esconder falsos positivos que bloqueiam o uso legítimo.

RECOMENDACAO_FINAL:
Aprovar condicionado a uma revisão do documento com estes itens:
- **(a) F02:** reescrever como "piso de ambiente" e incluir no teste o caso de `explicit_env=staging` com o repositório-alvo em produção, que deve resultar em production.
- **(b) F08:** fixar `HEAD_BEFORE` antes da suíte e exigir `HEAD_AFTER == HEAD_BEFORE` com a worktree limpa.
- **(c) Cortes de Ponytail:**
  - F06/F07: só invalidar `CANONICAL_VERIFIED`;
  - F01: corrigir restrito a `is_cert_tampering`;
  - F10: regra sintática com `-r`;
  - F11: sem `--force-clean`, cobrindo as linhas 262 e 279;
  - F05: fail-closed para qualquer configuração que não seja `simple`/`current`.
- **(d) Matriz:**
  - separar F01a e F01b;
  - fixar o resultado de F04 por ambiente;
  - F14 comparando com a fonte canônica;
  - pelo menos um teste negativo por achado do Bloco A;
  - portão de baseline: suíte completa mais 5/5 evals antes e depois de cada fase.
- **(e) Fases:** dividir a Fase A em A1 (gate Python, F01–F05, F01 por último) e A2 (runner Bash, F06–F08), com commits que possam ser revertidos de forma independente. Também alinhar F09 como P1 ou rebaixá-lo de forma explícita.
- **(f) Corrigir a factualidade:** linha do `rmtree`, chave `force` em vez de `is_force`, função `is_higher_severity` inexistente.

O parecer também foi salvo no arquivo de plano em `/home/<user>/.claude/plans/voc-est-deliberando-como-immutable-boole.md`.
