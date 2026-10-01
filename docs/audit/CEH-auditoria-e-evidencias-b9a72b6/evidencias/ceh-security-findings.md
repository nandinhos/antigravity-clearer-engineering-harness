# CEH: revisão de segurança somente leitura

HEAD auditado: b9a72b6b6dbd898dd737609bada8036866e56646. Prefixo de caminhos abaixo: `clearer-engineering/scripts/`.

## Método e fronteira
Leitura da arquitetura, ADR007, fluxo shim -> hook_context -> adapters -> Request -> engine -> lexer/context -> subcommand -> rm/git/interpreters/push. Nenhuma linha de comando destrutiva foi executada; payloads abaixo são STRINGS para `evaluate(Request(...))`. Nenhum push, dry-run de push ou acesso a remoto foi executado. Fixtures criadas fora do repo, com git init/add/commit/branch/tag/config locais. O certificado da fixture é deliberadamente sintético, NÃO evidencia execução real de CI; serve exclusivamente para testar o contrato do validador.

Evidência: `ceh-security-proof-results.json`, `ceh-security-extra-results.json`, `ceh-security-push-extra-results.json`, no mesmo scratch deste relatório. Scripts reproduzíveis: `ceh-security-proof.py`, `ceh-security-extra.py`, `ceh-security-push-extra.py` (o segundo e terceiro referenciam a fixture gerada na execução original). Fixture original: `ceh-security-fixture-er61_ejv`.

## 1. P1 — Redirecionamentos visíveis escapam da proteção de certificado
Caminhos: `ceh_core/rules.py:185-188,207-213`; `ceh_core/subcommand.py:152-164`; `ceh_core/engine.py:174-181`; `ceh_core/lexer.py:157-178`.

`cat sample.txt > .ceh/last-ci-run.json` => deny CERTIFICATE_INTEGRITY; sem espaços, `cat sample.txt>.ceh/last-ci-run.json` => allow GENERAL. shlex mantém o token `sample.txt>.ceh/...`; o teste só reconhece redirecionamento no INÍCIO do token e cat é autorizado como leitura. Além disso, `bash -c 'echo ok' > .ceh/last-ci-run.json` e `(echo ok) > .ceh/last-ci-run.json` => allow: desembrulho retorna antecipadamente e joga fora o redirecionamento externo antes de verificar integridade. Payload Antigravity realista passou por handle_hook_lifecycle e retornou allow/exit 0 nos dois primeiros bypasses.

Impacto: sobrescrita/truncamento do certificado e possível falsificação para liberar push. Não é opacidade de arquivo/script remoto: o destino e a operação estão explícitos na string interceptada. Basta agente controlando CommandLine dentro do modelo oportunista do ADR007. Prova segura adicional executou somente `printf fixture>arquivo-inofensivo` em scratch, confirmando a gramática adjacente; o certificado NÃO foi sobrescrito.

## 2. P1 — Desembrulho de shell perde ambiente explicitamente produtivo
Caminho: `ceh_core/subcommand.py:152-159` (recursão com explicit_env original, não env efetivo); controles em `ceh_core/interpreters.py:202-207`.

Fixture branch dev, sem variável de ambiente externa produtiva. `env APP_ENV=production php artisan migrate:fresh` => deny DATABASE/production. `env APP_ENV=production bash -c 'php artisan migrate:fresh'` => allow DATABASE/development. handle_hook_lifecycle, com Cwd válido e CommandLine do segundo comando, também retorna allow/exit 0. A avaliação externa reconhece production; a recursão redetecta apenas branch dev porque a atribuição env foi descartada. `export APP_ENV=production; bash -c 'php artisan migrate:fresh'` também => allow (a decisão agregada descreve GENERAL/production, mas não bloqueia o comando destrutivo interno).

Impacto: migrate:fresh efetivamente herda APP_ENV=production no Bash real, porém é autorizado como operação de desenvolvimento. Exige ambiente produtivo comunicado por prefixo/comando, não branch/config/variável de processo já produtiva, pois nesse segundo caso a redetecção pode continuar bloqueando. Controle equivalente com env + python os.system foi deny; portanto não é uma limitação universal de opacidade inline.

## 3. P1 — Caminho absoluto do executável Git ignora inteiramente o gate de push
Caminho: `ceh_core/git_invocation.py:28-34`; integração `ceh_core/subcommand.py:208-215,273-280`.

Na fixture com CI e certificado temporariamente estacionado: `git push origin HEAD:dev` => deny PRE_PUSH_CI (nenhum certificado). `/mingw64/bin/git push origin HEAD:dev` => allow GENERAL. `command -v git` confirmou `/mingw64/bin/git` no Git Bash desta máquina. `/usr/bin/git push origin HEAD:dev` apresenta o mesmo comportamento classificatório e é aplicável onde esse binário exista. O parser exige token exatamente `git`, apesar de resolve_command_head usar basename para wrappers.

Impacto: push sem CI comprovada por mera troca de nome relativo por caminho absoluto válido. Nenhum push foi executado; o certificado da fixture foi restaurado em finally. Limite: não provamos a interação end-to-end com agy instalado (agy ausente); o resultado do motor e a existência do binário local são observados, não presumidos.

## 4. P1 — Formas válidas de flags Git passam como não destrutivas
Caminhos: `ceh_core/rules.py:52-57`; `ceh_core/push.py:106-109,138-145`; `ceh_core/subcommand.py:252-278`.

Produção explícita: `git reset --hard HEAD` => deny GIT_HISTORY; `git reset HEAD --hard` => allow GENERAL. Com certificado aprovado para HEAD na fixture, `git push --force origin HEAD:dev` => deny GIT_HISTORY; `git push -vf origin HEAD:dev` => allow PRE_PUSH_CI. O parser de push reconhece `f` em flags agrupadas, mas essa informação não alimenta a decisão de destrutividade; a regex exige a forma textual -f/--force. reset ainda depende da ordem textual imediata.

Impacto: descarte de worktree ou force-push em produção apesar das políticas específicas. Formas estáticas visíveis, sem eval/scripts opacos. Não usar `--for` como prova de exploração: o classificador permitiu essa abreviação, mas ela pode ser ambígua para Git (force/force-with-lease/force-if-includes), então foi excluída deste achado.

## 5. P1 — Gate de push não valida os refs realmente selecionados pelo Git
Caminho: `ceh_core/push.py:217-249`, especialmente `229-234` e `243-249`; flags em `17-25,77-103`.

Fixture: HEAD certificado `99b4d2be89d3109a46c1f10c4c82c1963657c744`; branch unchecked `94188b3fd246d7da36877ad00533983a1e43eb58`. `git push origin unchecked:dev` => deny por hash divergente. Configuração local efetivamente gravada/lida `remote.origin.push=unchecked:refs/heads/dev`; `git push origin` => allow PRE_PUSH_CI, pois confere apenas HEAD e ignora a configuração. Também foi observado allow para push.default=matching e `git push origin :`. O refspec especial ':' significa matching, mas `clean.startswith(':')` o descarta como deleção; com refspecs não vazios, nem HEAD é conferido. A transmissão dependeria dos refs do remoto; não houve conexão remota para prová-la.

`git push --follow-tags origin HEAD:dev` => allow com annotated tag em commit antigo alcançável; follow-tags está no catálogo mas não é fiscalizado. Limite importante: tags seguidas são alcançáveis pelos refs enviados, portanto essa variante não prova por si só introdução de commit fora da história enviada; demonstra ausência de validação por ref e inconsistência com a restrição de --tags. O bypass mais forte e independente é remote.origin.push não-HEAD; matching exige branches homônimas existentes no remoto.

## 6. P2 — Diretório com ponto é classificado como arquivo único seguro
Caminho: `ceh_core/rm.py:176-182,235-237`.

Na fixture, customer.db é DIRETÓRIO real com data.txt. Em produção explícita, `rm -rf customer.db` => allow FILESYSTEM_SAFE; `rm -rf customer` => deny FILESYSTEM. A regra infere 'arquivo único com extensão' pelo ponto no basename e flag force, sem rejeitar is_recursive nem verificar tipo. O conteúdo permaneceu intacto; só classificamos strings.

Impacto: exclusão recursiva de diretórios de dados no workspace liberada em produção/staging, embora o atalho documentado seja para um arquivo único ou diretórios de cache/scratch. Não confundir com limpeza legítima de dist/build, que é política deliberada. Exige diretório relativo ao cwd e com nome pontuado, não alvo catastrófico (cwd/ancestral/raiz), que tem verificações anteriores.

## Cobertura e limites documentados
Adapters Antigravity/Muse/Claude foram lidos, assim como shim e fallback. Conversão ask->deny/block e erros nativos não mostraram novo defeito prioritário nesta rodada. Há divergência secundária a investigar: Muse detect aceita payload apenas com tool_name=bash, enquanto fallback só reconhece Muse com model_provider/turn_id e classifica esse payload sem marcadores como Claude. Essa forma é aceita pelo código, mas não demonstramos que um runtime Muse real a emite; portanto NÃO promovida a vulnerabilidade comprovada.

ADR007:48-87 já documenta scripts de arquivo, execução remota/contêiner, conteúdo dinâmico, extração, host fail-open por timeout/processo e obrigação de proteção remota de branch. Não apresentados como achados novos. Nenhum destes seis achados depende de contornar o hook externamente ou de ter privilégios para editar o gate; são inconsistências sobre strings/refs estáticos visíveis no canal que o projeto pretende proteger. Certificado local não é atestado criptográfico. Branch protection/checks remotos continuam necessários.

## Estado final
Nenhum arquivo do repo alterado; git status --porcelain vazio após os testes, HEAD preservado. Somente scripts/resultados/relatório e fixture isolada foram criados em scratch. Um primeiro lançamento de ceh-security-extra.py retornou exit 15 sem diagnóstico; repetição concluiu exit 0. Um probe auxiliar de Bash via subprocess perdeu argumento posicional e falhou; substituído por redirecionamento benigno direto via terminal, com leitura confirmando conteúdo 'fixture'. Não se substituiu falha por evidência inventada.
