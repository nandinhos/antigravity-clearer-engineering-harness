# Análise aprofundada — CLEARER Engineering Harness (CEH)

**Autor da análise:** Hermes. **Coleta:** 30/09/2026, horário do Brasil; alguns logs usam 01/10/2026 UTC. **Snapshot:** `main`, commit `b9a72b6b6dbd898dd737609bada8036866e56646`. A release pública v2.0.0 foi publicada em 30/09/2026, às 21:13:02 UTC; a tag aponta para `9385bf7d846af4253e019de776227f60d0a28f2e`. As conclusões são sobre o snapshot auditado, não sobre futuras alterações de main.

## 1. Parecer executivo

O CEH não é apenas uma coleção de prompts. Ele contém um motor real de classificação de operações, adaptadores de protocolos de hooks, runner de testes com certificado por commit, empacotador multi-host, testes diferenciais, mutações e extensa documentação de evidências. A separação `Request → Decision` representa um avanço concreto na arquitetura.

Entretanto, não recomendaria depender da versão auditada como barreira exclusiva de segurança em produção. Reproduzi decisões `allow` para operações que contradizem as próprias políticas: escrita explícita no certificado, perda de ambiente produtivo ao desembrulhar shell, Git absoluto fora do gate, variantes válidas de flags destrutivas e seleção de refs não certificados. O runner também consegue certificar testes diferentes da suíte declarada ou conteúdo de worktree diferente do commit.

**Diagnóstico:** boa base de engenharia e rastreabilidade; fronteiras de segurança e certificação ainda inconsistentes. A prioridade é corrigir contratos existentes e acrescentar os contraexemplos à suíte, não adicionar mais agentes, slogans ou camadas de arquitetura.

Não houve push, alteração de configuração remota ou instalação no HOME real. Os payloads destrutivos foram somente classificados como strings. Certificados sintéticos aparecem apenas em fixtures unitárias de análise do validador e NÃO são evidência de CI executada.

## 2. Método e evidências

- Clone isolado do repositório e leitura de código, manifests, ADRs, CI, testes e documentação.
- Revisões independentes em três frentes: segurança, instalação/empacotamento e arquitetura/testes. Os achados prioritários foram reproduzidos novamente pelo revisor principal.
- Python 3.14.7 no Windows para classificações e empacotamento isolado; WSL Ubuntu 24.04, Python 3.12.3 e Bash 5.2.21 para scripts shell.
- O primeiro checkout Windows converteu arquivos para CRLF. Os testes Linux passaram a usar um segundo checkout do MESMO commit, com `core.autocrlf=false`. A falha inicial de parsing CRLF não foi atribuída ao código de origem.
- Consulta somente leitura à API pública do GitHub para releases, runs, branches e rulesets.
- Conferência dos arquivos principais com a origem raw do commit: conteúdo idêntico, normalizados apenas os terminadores de linha.

Os caminhos de código neste relatório são relativos ao repositório. Quando abreviados como `scripts/`, `tests/` e `tools/`, o prefixo é `clearer-engineering/`.

### Artefatos da revisão

- `ceh-review-independent.py` e `ceh-review-independent-results.json`: reprodução principal dos achados do gate, aliases e destino do empacotador.
- `ceh-review-probes.py` e `ceh-review-probes.json`: três provas reais do runner em fixtures Git isoladas.
- `ceh-review-api.json`, `ceh-review-branch-protection.json`: respostas públicas da API, inclusive limitações de autenticação.
- `ceh-review-metrics.json`: inventário calculado via `git ls-files`, sem dependências/builds não versionados.
- `ceh-review-verification-results.json`: exit codes reais capturados por supervisor Python para evals, adversarial e auditoria documental.
- Logs `ceh-review-verified-*.log`, `ceh-review-shellcheck.log`, `ceh-review-canonical-linux.log`.
- `ceh-security-findings.md`: revisão independente de segurança, com condições e ressalvas adicionais.

## 3. Inventário e arquitetura

858 arquivos versionados, distribuídos por escopo:

| Escopo | Arquivos | Linhas físicas, incluindo comentários e vazias |
|---|---:|---:|
| Runtime, scripts, empacotador, install/uninstall | 39 | 7.253 |
| Testes e evals | 59 | 14.199 |
| Conteúdo distribuído: regras, skills, agentes, manifests | 32 | 2.616 |
| Documentação e demais arquivos | 31 | 5.693 |
| Histórico/evidências em `docs/temp_implementation/` | 697 | 41.067 |

Essas contagens NÃO são LOC executáveis, cobertura de testes nem medidas de complexidade. O histórico de evidências domina a árvore, mas isso não significa que seja lixo: os experimentos e canários são parte importante da rastreabilidade. Convém separar melhor documentação operacional atual de arquivo histórico para reduzir ruído de navegação e contexto de agentes.

### Fluxo central

```text
Host: Antigravity / Claude Code / Muse
    → shim safety-gate.py
    → hook_context + detecção do adaptador
    → payload do host convertido em Request
    → ceh_core.engine
        → lexer / normalização / resolução de contexto
        → regras de domínio / Git / rm / interpretadores
        → pre-push CI gate
    → Decision
    → renderização específica do adaptador
    → decisão observada pelo host
```

Ferramentas paralelas: `test-runner.sh` gera evidência, `evidence_report.py` calcula relatório, `tools/package.py` distribui bundles, suites/evals verificam regressões. Skills e agentes Markdown dão orientação metodológica; não são, por si só, enforcement determinístico da qualidade de todo trabalho produzido.

### Pontos fortes

1. O motor não depende dos schemas JSON de cada host (`engine.py:24–37,249–275`; `adapters/base.py`).
2. Os hosts têm semânticas próprias de retorno, e os adaptadores reconhecem essa diferença em vez de presumir que todo host entende o mesmo JSON.
3. A reserva é independente do motor, útil para falhas tratáveis de importação/execução.
4. O certificado verifica commit e comando canônico e procura impedir emissão inicial em worktree sujo. A intenção é correta; os achados abaixo mostram onde o contrato ainda se rompe.
5. A suíte inclui golden corpus, fuzzing, testes diferenciais e mutações. Isso é mais valioso que verificar apenas a existência de palavras em policies.
6. ADR007 reconhece explicitamente que o gate local não é sandbox nem cofre criptográfico e depende de proteção remota de branches.
7. CI Linux/macOS × Python 3.9/3.12, checkout com histórico e ShellCheck fixado com SHA-256.

### Dívida estrutural

O núcleo é agnóstico de HOST, mas não puro: lê filesystem, ambiente e Git. `hook_context.py` altera CWD global e `environment.py` mantém caches globais por caminho. Isso não prova um bug no hook de processo curto atual, mas exige revisão antes de reutilizar o motor em serviço persistente/concorrente.

Há duplicação de identificação/resolução entre adaptadores, fallback e shim. Parte dos problemas observados nasce de contextos semânticos perdidos nessas transições, não da falta de mais regras isoladas.

## 4. Achados de alta prioridade — corrigir antes de confiar em produção

### F01 — Integridade do certificado burlada por redirecionamento visível

**Prioridade P1. Reproduzido no motor e lifecycle Antigravity.**

Fontes: `scripts/ceh_core/rules.py:185–188,207–213`; `subcommand.py:152–164`; `engine.py:174–181`.[2][3]

| String somente classificada | Resultado |
|---|---|
| `cat sample.txt > .ceh/last-ci-run.json` | deny |
| `cat sample.txt>.ceh/last-ci-run.json` | allow |
| `bash -c 'echo ok' > .ceh/last-ci-run.json` | allow |
| `(echo ok) > .ceh/last-ci-run.json` | allow |

O teste de redirecionamento depende de operadores no início de tokens; o redirecionamento adjacente fica dentro de outro token. O desembrulho de shell/subshell descarta a operação de redirecionamento externa.

Isso não é uma limitação de scripts opacos: o alvo protegido e a escrita estão visíveis. O lifecycle Antigravity devolveu `allow` com exit 0 para a forma adjacente. Nenhum certificado real foi sobrescrito.

**Correção:** preservar operadores/alvos de redirecionamento na representação léxica e verificar seus efeitos antes de autorizar a execução interna. Acrescentar invariantes de equivalência com/sem espaços e com wrappers.

### F02 — Desembrulho de shell rebaixa produção para desenvolvimento

**P1. Reproduzido no motor e lifecycle Antigravity.**

Fonte: `scripts/ceh_core/subcommand.py:152–159`.[2]

Fixture branch dev, sem configuração produtiva persistente:

- `env APP_ENV=production php artisan migrate:fresh` → deny/production.
- `env APP_ENV=production bash -c 'php artisan migrate:fresh'` → allow/development.

O comando real herdaria a variável produtiva, mas a recursão recebe o override original, não o ambiente efetivo já detectado. O contexto produtivo do prefixo é perdido.

**Condição:** produção indicada no comando/prefixo. Uma branch/configuração de processo já produtiva pode impedir essa variante.

**Correção:** transportar contexto efetivo monotônico pela recursão; desembrulhar não pode reduzir a severidade do ambiente.

### F03 — Git absoluto não passa pela proteção de push

**P1. Reproduzido classificando strings; sem push real.**

Fonte: `scripts/ceh_core/git_invocation.py:28–34`; `subcommand.py:208–215,273–280`.

Fixture com CI, sem certificado:

- `git push origin HEAD:dev` → deny PRE_PUSH_CI.
- `/usr/bin/git push origin HEAD:dev` → allow GENERAL.

A revisão independente também comprovou `/mingw64/bin/git` como executável real no Git Bash local. O parser exige o token exatamente `git`.

**Correção:** identidade consistente do executável em parser/regras; incluir formas absolutas reais e wrappers suportados na mesma política. Não normalizar cegamente executáveis arbitrários apenas pelo basename sem declarar o contrato.

### F04 — Formas válidas de opções Git deixam de ser destrutivas

**P1. Reproduzido por classificação.**

Fontes: `scripts/ceh_core/rules.py:52–57`; `push.py:106–109,138–145`; `subcommand.py:252–278`.[3][4]

Em produção:

- `git reset --hard HEAD` → deny; `git reset HEAD --hard` → allow.
- Com certificado sintético válido: `git push --force origin HEAD:dev` → deny; `git push -vf origin HEAD:dev` → allow PRE_PUSH_CI.

O parser reconhece a flag agrupada `f`, mas sua informação não determina a destrutividade. Regex continuam sensíveis à apresentação textual.

**Correção:** consumir as flags semânticas do parser existente, em vez de reclassificar por regex; testar permutações e agrupamentos equivalentes. Abreviações ambíguas como `--for` NÃO foram usadas como prova válida.

### F05 — Push sem refspec valida HEAD, não necessariamente o ref enviado

**P1. Reproduzido em fixture com configuração Git local lida de volta; sem acesso remoto.**

Fonte: `scripts/ceh_core/push.py:217–249`.[4]

Uma branch `unchecked` aponta para commit diferente do HEAD certificado:

- `git push origin unchecked:dev` → deny.
- Após `remote.origin.push=unchecked:refs/heads/dev`, `git push origin` → allow.
- `git push origin :` → allow, embora `:` seja matching, não uma exclusão remota simples.

A documentação oficial de `git push` estabelece a precedência de argumentos, `remote.<repository>.push` e `push.default`, e define `:` como matching. A prova não fez transmissão real: matching dependeria das branches do remoto.

**Correção:** resolver refs efetivos usando o contexto/configuração Git ou negar conservadoramente formas não determináveis. Não alegar certificação de HEAD quando Git seleciona outro ref.

### F06 — Runtime Sail pode executar outra suíte e manter certificado canônico

**P1. Reprodução real com Docker/Sail simulados em fixture isolada — não teste em container real.**

Fonte: `scripts/test-runner.sh:83–88,117–129,176–182`.[1]

Configuração versionada: `canonical_test_command = bash canonical.sh`. Sua execução direta retorna exit 9. O mock Docker comunica serviço `laravel.test` ativo; existe `vendor/bin/sail` na fixture, que retorna 0.

O runner troca o comando por `./vendor/bin/sail test` e emite:

```json
{
  "command": "./vendor/bin/sail test",
  "normalized_runner": "bash canonical.sh",
  "canonical_verified": true,
  "status": "PASS",
  "exit_code": 0
}
```

O gate permite push. O mock não inventa uma resposta de produção: ele é um estímulo controlado que exerce o ramo real do runner. A falha é a substituição do comando mantendo a verificação canônica anterior.

**Correção:** adaptar transporte sem substituir a suíte; quando a semântica da suíte mudar, invalidar `canonical_verified` ou exigir declaração canônica explícita adequada ao runtime.

### F07 — Ausência de pytest transforma suíte parcial em suíte canônica

**P1. Reprodução real do runner.**

Fonte: `scripts/test-runner.sh:34–39,81–88`.[1]

Fixture sem comando canônico explícito na configuração, com `pytest.ini`, uma função pytest que necessariamente falha e um smoke test unittest que passa. Na autodetecção, sem `pytest` no PATH, o runner escolhe `python3 -m unittest`. Resultado observado: `Ran 1 test`, `OK`, `canonical_verified=true`, `PASS`, push autorizado. A função pytest falha não foi executada.

Não reportei um falso verde de zero testes: no Python 3.12.3 local, a primeira tentativa com zero testes retornou exit 5 e foi bloqueada. O contraexemplo confirmado usa uma suíte parcial real com um teste unittest.

**Correção:** se a suíte declarada/detectada exige pytest, ausência do runner deve ser falha de infraestrutura. Não usar outro framework como equivalente silencioso; preferir `python -m pytest` do interpretador definido pelo projeto.

### F08 — Certificado emitido após testar worktree diferente do commit

**P1. Reprodução real do runner.**

Fonte: `scripts/test-runner.sh:94–104,150–152,166–182`.[1]

O worktree é verificado apenas antes de executar. A suíte da fixture muda `source.txt` e testa o conteúdo gerado. Termina verde, deixa ` M source.txt`, mas o certificado declara PASS para o HEAD antigo e o gate autoriza push.

Condição semelhante pode ocorrer por geradores, formatadores, fixtures que alteram fonte ou edição concorrente. Não é necessário forjar certificado manualmente.

**Correção:** capturar HEAD inicial; revalidar HEAD, configuração e estado versionado após a execução; não emitir certificado válido caso mudem. Um checkout/worktree de teste isolado fortalece a correspondência sem introduzir falsa promessa criptográfica.

### F09 — Integração do pacote Claude não cobre todas as ferramentas do adaptador

**P1 de integração; inspeção estática, não prova end-to-end no Claude instalado.**

Fontes: `scripts/adapters/claude_code.py:25–26,99–109`; `tools/package.py:165–193`.[5]

Adaptador contempla `Write`, `Edit`, `MultiEdit`, `NotebookEdit`. Settings gerados interceptam apenas `Bash` e `Write|Edit`. O código capaz de negar uma edição não ajuda se o matcher não aciona o hook.

**Correção:** contrato único de capacidades e matchers; verificar cada ferramenta efetivamente oferecida pelo host. O comando relativo `python3 scripts/safety-gate.py` também precisa de testes com CWDs variados. Não assumi que a resolução relativa necessariamente falha no runtime real: falta essa validação.

## 5. Achados operacionais e de manutenção

### F10 — Diretório pontuado classificado como arquivo único seguro

**P2, reproduzido.** `scripts/ceh_core/rm.py:176–182,235–237`.

`customer.db/` era um diretório real com sentinela: `rm -rf customer.db` → allow FILESYSTEM_SAFE em produção. `rm -rf customer` → deny. O atalho usa ponto no basename para inferir arquivo único e não exclui recursão nem verifica tipo.

Correção: não inferir tipo pela extensão; distinguir explicitamente diretórios recursivos, arquivos únicos e limpeza deliberadamente permitida de caches/builds. Nenhum diretório de dados foi apagado na prova.

### F11 — Destino do empacotador apagado sem verificar propriedade

**P2 operacional, reproduzido.** `tools/package.py:255–263,278–281`.[5]

Uma pasta de saída exclusiva em scratch continha `user-sentinel.txt`. `--host muse --out ...` retornou 0 e removeu a sentinela. O CLI aplica `shutil.rmtree()` ao destino resolvido sem marker de propriedade, proteção de HOME/source/repo ou geração transacional.

A limpeza de saída pode ser intencional, mas aceitar qualquer diretório não gerenciado cria um risco desnecessário para uma ferramenta de segurança.

Correção: recusar destinos perigosos/não gerenciados; gerar em staging e substituir somente após sucesso. Nenhum caminho real do usuário foi usado como destino na prova.

### F12 — Marcadores de aliases dentro de strings apagam configuração legítima

**P2 operacional, reproduzido.** `scripts/rc_aliases.py:78–104,120–132`.

Um arquivo descartável com `echo "# BEGIN ..."`, uma linha `export USER_SETTING=keep` e `echo "# END ..."` foi reduzido a `echo ""`. Marcadores são buscados por substring, não comentários completos em linhas próprias.

Correção: reconhecimento ancorado em linhas completas; validar sequência/quantidade; preservar arquivo em estado ambíguo. A revisão independente encontrou também duplicação residual e normalização LF→CRLF no roundtrip Windows; os dois casos são problemas de preservação, não compromissos de autenticação.

### F13 — Upgrade do plugin não é transacional

**P2, inspeção estática.** `install.sh:147–177,181–197,324–326`.

Instalação anterior é removida e perfil substituído antes da validação final. Erro de cópia ou validação deixa estado alterado, sem recuperação automática. Não rodei upgrade real no HOME do usuário.

Correção: validar árvore em staging e só então trocar a instalação ativa, com recuperação da versão anterior em caso de erro. Isso é tratamento de transação de instalação, não oferta de backup de produção.

### F14 — Manifesto Muse permanece em 1.4.1 no pacote da fonte 2.0.0

**P2 de distribuição, reproduzido.** `tools/package.py:138`; `plugin.json:3`.[5]

O manifesto Muse gerado declara 1.4.1; o plugin Antigravity declara 2.0.0. Corrigir fonte canônica única de versão e assert de equivalência entre todos os hosts.

### F15 — Relatório sempre perde detecção de ambiente após refatoração

**P2, reproduzido.** `scripts/evidence_report.py:121–129`.

O relatório importa o shim e chama `gate.detect_environment()`, que não existe mais no shim. Resultado real: `UNKNOWN (AttributeError)`. Chamando `ceh_core.environment.detect_environment()` no mesmo checkout: production por branch main.

Correção: importar API atual do core. Adicionar teste que exija ambiente correto, não apenas a seção textual do relatório.

### F16 — Pacote Antigravity inclui testes que dependem de arquivos não distribuídos

**P2 de contrato; revisão independente reproduziu falha na árvore gerada.** `tools/package.py:88–102`; `tests/test_package.py`; `tests/run-all-tests.sh:245–247,313–315`.

Bundle copia `tests/`, mas não `tools/package.py`, `install.sh`, `uninstall.sh` do repo pai. Alias `ceh-evals` também aponta para `evals/run.sh` ausente no bundle isolado. O instalador completo compensa evals, mas isso não torna o pacote isolado autônomo.

Correção: definir pacote runtime versus pacote de desenvolvimento, evitando distribuir suites/aliases que dependem de arquivos ausentes. Testar a árvore final sem acesso ao checkout de origem.

## 6. Proteção remota e modelo de ameaças

ADR007 é uma parte forte do projeto: reconhece que hooks locais não impedem um processo arbitrário com os mesmos privilégios, que scripts/remotos/containers são opacos, e que a IDE pode executar fail-open se Python faltar, o shim tiver erro sintático ou o host abortar por timeout.[6]

Esses limites documentados NÃO foram apresentados como descobertas novas. Os achados F01–F08 diferem deles porque envolvem comandos/efeitos/configurações visíveis dentro do canal que o harness pretende controlar.

### Estado público consultado

API de branches retornou `protected: false` para main, dev e staging. `GET /rulesets` e `GET /rules/branches/main` retornaram arrays vazios. O endpoint clássico `/branches/<branch>/protection` retornou 401 sem autenticação.

Portanto, os sinais públicos consultados não comprovam a proteção remota que o ADR007 exige; eles indicam branches sem proteção na resposta pública. Não tive acesso privilegiado ao painel para auditar configuração interna. Confirmar/configurar rulesets e checks obrigatórios deve preceder confiança produtiva no gate.

A proteção remota protege a integração de commits; não torna impossível destruir worktree ou banco local. Mesmo CI obrigatória não substitui isolamento e controle de acesso das credenciais de produção.

### Reserva Muse

`muse.py` aceita detecção por ferramenta minúscula sem `model_provider/turn_id`; `fallback.py` precisa desses marcadores e pode classificar esse payload como Claude. Há divergência de contrato, mas não foi demonstrado que um runtime Muse real emita esse payload mínimo. Deve ser testada e documentada, não anunciada como exploração confirmada.

## 7. Avaliação dos testes e claims

### O que está bem feito

Testes diferenciais contra baseline, corpus, fuzzing e mutações fornecem proteção real contra relaxamentos inadvertidos. Os experimentos por host com controle são mais úteis que apenas testar a existência de um hook JSON.

### O que eles não provam

1. **Conformidade entre hosts não é oráculo de segurança.** `test_cross_host_conformance.py:279–318` compara o core com fluxos que chamam o MESMO core. Um defeito compartilhado pode deixar todos conformes.
2. **Golden baseline conserva também bugs antigos.** Ausência de diferença é estabilidade, não correção universal.
3. **Muitos casos da mesma gramática não substituem equivalência semântica.** Os contraexemplos de espaços, ordem, wrapper e configuração exigem propriedades explícitas.
4. **Testes textuais de skills não provam comportamento de LLM.** Presença de palavras como investigar/falsificar não mede tarefa executada sob essas instruções.
5. **Prova versionada é rastreabilidade, não implicação semântica.** `evidence_report.py:58–78` comprova existência/integridade/ancestralidade. Não demonstra sozinho que o conteúdo da prova sustenta a afirmação. Os valores de confiança não são probabilidades calibradas.
6. **Auditoria de estrutura não é auditoria completa.** O próprio doc-audit declara seu limite; ainda assim, pode passar com README/ADR/changelog divergentes.

### Cobertura que deve ser acrescentada

- Propriedades de não rebaixamento do contexto durante desembrulho.
- Equivalência de redirecionamentos com/sem espaços e wrappers.
- Identidade de executável Git e ordenação/agrupamento de flags.
- Seleção real de refs por configuração; refspec especial matching.
- Suites Python mistas/runner ausente.
- Runtime adapter preservando a suíte canônica.
- HEAD/worktree antes E depois dos testes.
- Manifestos, matchers e comandos executados desde a árvore distribuída, em CWDs diferentes.
- Canários reais por host em sandboxes sentinela, com controle sem hook, safe/deny/ask e erro de processo.

### Fragilidades da execução

`run-all-tests.sh` possui 75 chamadas de alto nível `run_test`; não são 75 asserções nem 75 cenários internos. O badge do README ainda mostra 65/65. A matriz CI não inclui Windows nativo, e a instalação oficial é Linux/macOS/WSL; isso não autoriza chamar falhas específicas Windows de regressões da matriz suportada sem separar escopos.

O runner de smoke-eval verifica o limite de 60s somente ao final, embora CRITERIA exija interrupção imediata. A norma também descreve mais fixtures/avaliações do que o runner efetivamente executa. Convém separar protocolo implementado e proposta futura.

O `run_test` usa eval e pipelines de grep; capturar JSON e exit code separadamente é mais robusto. Adicionar `pipefail` indiscriminadamente não basta, pois o gate retorna legitimamente exit 2 ao negar comandos.

## 8. Higiene documental e distribuição

- README badge 65/65, contra 75 grupos presentes no runner.
- ADR006 ainda descreve partes implementadas como planejadas e menciona Bash 3.2, enquanto install exige Bash 4.0; o conselho usa `local -n`, que exige requisito maior.
- Changelog menciona tipos imutáveis `HookRequest`, `HookDecision`, `EvaluationContext`; o código usa dataclasses mutáveis `Request` e `Decision`.
- Changelog/revisão de release contêm data de 02/10/2026, enquanto tag/merge/release/E17 são de 30/09/2026. É inconsistência documental; não há inferência de fraude.
- O JSON de certificado do README omite `canonical_verified`, embora o gate exija true.
- “Latest stable” usa main no one-liner. O instalador não seleciona automaticamente a release estável nem autentica o commit por assinatura/hash esperado. Isso é risco de fornecimento, não evidência de comprometimento.
- Redução de linhas e buscas lexicais por termos de host não comprovam redução percentual de complexidade/blast radius ou universalidade multi-host.

Sugestão: documentação de garantia em formato **claim → mecanismo → teste → limite**, gerada ou verificada a partir de contratos do código. Índice curto de operação atual e arquivo histórico separado, sem apagar evidências úteis.

## 9. Resultados de execução

### Resultados concluídos e capturados

- CI remoto do HEAD auditado: run `36799738443`, completed/success, conforme API pública.
- Bash syntax: 19 arquivos .sh versionados, nenhum erro.
- ShellCheck local 0.9.0: exit 0. Não é a versão 0.11.0 fixada no CI; não aleguei paridade total de versão.
- Smoke-evals diretos: 5/5, exit 0; nova captura 55,82s.
- Adversarial: 5/5, exit 0.
- Doc-audit: 7/7, exit 0; valida estrutura, não semântica integral.
- Três provas do runner: PASS/canonical_verified=true e gate allow, apesar dos contraexemplos descritos em F06–F08.
- Reclassificações de F01–F05/F10 e reproduções de F11/F12 confirmadas pelo revisor principal.

### Observação da suíte completa e hermeticidade

A execução integral foi iniciada com `PYTHONDONTWRITEBYTECODE=1` para evitar resíduos. Dois grupos ligados às fixtures do Cluster 2 falharam: o gate chamado sob `env -i` não conserva esse flag, cria `__pycache__` numa fixture sem .gitignore e a verificação de restauração acusa resíduos. A fixture copia a árvore scripts e commita seu conteúdo, de modo que a presença prévia de caches influencia o resultado.

Uma reexecução do Cluster 2 após compileall do checkout isolado, sem suprimir bytecode, passou: 3/3, exit 0. O CI faz compileall antes da suíte. Logo, os primeiros dois vermelhos locais NÃO demonstram isoladamente que o CI público verde seja incorreto; demonstram dependência da preparação/caches na alegação de hermeticidade.

A execução integral foi interrompida pelo revisor após tempo local elevado, durante o grupo 58 (verificação de instalação). O log registra **55 grupos PASS e 2 grupos FAIL**, de **75 grupos definidos**. Os grupos restantes não foram concluídos nessa execução. O estado foi contado programaticamente em `ceh-review-canonical-state.json`; não é resultado 75/75 nem cobertura integral. Os processos Linux da execução interrompida foram verificados como encerrados. O runner externo também expandiu indevidamente variáveis de captura de exit code no comando WSL; por isso a revisão não usa seu status como resultado da suíte e baseia esse resumo nos registros de grupos do log.

## 10. Ordem de correção sugerida

### Etapa A — Contratos de segurança existentes

1. F01/F02: preservação de redirecionamentos e contexto efetivo.
2. F03/F04/F05: normalização Git, flags semânticas e refs reais.
3. F06/F07/F08: certificado representa comando e commit efetivamente testados.
4. F09/F10: cobertura de ferramentas e distinção arquivo/diretório.
5. Confirmar a proteção remota exigida pelo modelo de ameaças.

Critério de aceite: os contraexemplos viram testes vermelhos antes dos fixes; correção preserva controles seguros e não é aplicada só às strings literais desta revisão.

### Etapa B — Pacotes e instalação

Destinos gerenciados e geração transacional; upgrade validado antes da troca; limpeza de rc files com marcadores estritos; mesma versão em todos os hosts; bundle testado sem checkout de origem e com matchers completos.

### Etapa C — Evidência e comunicação

Corrigir API do relatório, badges, datas, tipos, requisitos Bash e exemplos. Distinguir estabilidade, conformidade de adaptadores, teste do host e garantia de segurança. Confidence numérica deve ter semântica claramente definida, não parecer probabilidade estatística.

### Etapa D — Evolução, somente depois

Isolar dependências de Git/filesystem quando houver uso persistente/concorrente real; expandir oráculos semânticos e testes reais por host; reorganizar CI para remover repetição sem enfraquecer comando canônico. Não há necessidade demonstrada de reescrever o CEH inteiro.

## Conclusão

**Vale continuar investindo no CEH.** A infraestrutura existente fornece pontos de intervenção claros, e as provas são reproduzíveis. A versão auditada, entretanto, não sustenta uma promessa irrestrita de bloqueio de operações destrutivas e certificação integral do commit em todos os casos.

Minha recomendação é usar o projeto como disciplina de engenharia e defesa adicional, restringindo confiança produtiva até fechar os achados P1 e comprovar os controles remotos. A evolução mais valiosa agora é transformar as boas intenções já documentadas em invariantes executáveis e verificadas nos pacotes reais.

## Sources

[1] https://raw.githubusercontent.com/nandinhos/antigravity-clearer-engineering-harness/b9a72b6b6dbd898dd737609bada8036866e56646/clearer-engineering/scripts/test-runner.sh — clearer-engineering/scripts/test-runner.sh
[2] https://raw.githubusercontent.com/nandinhos/antigravity-clearer-engineering-harness/b9a72b6b6dbd898dd737609bada8036866e56646/clearer-engineering/scripts/ceh_core/subcommand.py — clearer-engineering/scripts/ceh_core/subcommand.py
[3] https://raw.githubusercontent.com/nandinhos/antigravity-clearer-engineering-harness/b9a72b6b6dbd898dd737609bada8036866e56646/clearer-engineering/scripts/ceh_core/rules.py — clearer-engineering/scripts/ceh_core/rules.py
[4] https://raw.githubusercontent.com/nandinhos/antigravity-clearer-engineering-harness/b9a72b6b6dbd898dd737609bada8036866e56646/clearer-engineering/scripts/ceh_core/push.py — clearer-engineering/scripts/ceh_core/push.py
[5] https://raw.githubusercontent.com/nandinhos/antigravity-clearer-engineering-harness/b9a72b6b6dbd898dd737609bada8036866e56646/clearer-engineering/tools/package.py — clearer-engineering/tools/package.py
[6] https://raw.githubusercontent.com/nandinhos/antigravity-clearer-engineering-harness/b9a72b6b6dbd898dd737609bada8036866e56646/docs/architecture/adr-007-protecao-certificado-modelo-ameacas.md — docs/architecture/adr-007-protecao-certificado-modelo-ameacas.md
