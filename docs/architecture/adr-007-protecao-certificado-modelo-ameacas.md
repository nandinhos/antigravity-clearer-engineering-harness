# ADR 007: Proteção de Integridade do Certificado de CI Local e Modelo de Ameaças

## Status
Aprovado (PR-10)

## Contexto
O CLEARER Engineering Harness (CEH) adota a salvaguarda de CI local (Gate 7.1 / Pre-Push CI Gate): nenhum `git push` é autorizado pelo `safety-gate` a menos que exista um certificado válido (`.ceh/last-ci-run.json`) atestando a execução com sucesso (exit code 0) da suíte canônica no mesmo commit hash local que está sendo enviado.

Entretanto, uma auditoria de segurança (identificada no Handoff 037 e classe G9) evidenciou que o arquivo de certificado ficava exposto no sistema de arquivos local. Um agente de IA com permissões de shell ou de manipulação de arquivos poderia inadvertidamente forjar o certificado através de comandos diretos de escrita (`echo ... > .ceh/last-ci-run.json`, `cp`, `tee`, `sed -i`, scripts `python3 -c`) ou por meio de ferramentas nativas de edição de arquivos (`write_to_file`, `replace_file_content` no Antigravity; `Write`, `Edit`, `MultiEdit` no Claude Code), burlando a obrigatoriedade da execução real dos testes.

## Modelo de Ameaças & Fronteiras de Confiança

### 1. Ameaça Mitigada (O Agente Cooperativo com Alucinação ou Oportunismo)
- **Vetor**: O modelo de linguagem (LLM), tentando cumprir a meta de fazer o `git push` a qualquer custo, decide criar ou sobrescrever manualmente `.ceh/last-ci-run.json` simulando uma suíte verde sem ter executado os testes.
- **Mitigação**: O `safety-gate` intercepta tanto chamadas de shell quanto chamadas de ferramentas de edição de arquivos que tenham como destino o diretório protegido `.ceh/` ou seus arquivos de integridade (`last-ci-run.json`, `last-ci-run.log`, `last-evals-run.json`), retornando `deny` incondicional.
- **Leituras Permitidas**: Comandos estritamente de leitura (`cat`, `head`, `tail`, `jq`, `grep`, `stat`, `ls`, `wc`, `python3 -m json.tool`) permanecem `allow`, permitindo que o desenvolvedor ou o agente inspecione o certificado gerado.
- **Gravação Autorizada**: Apenas o script oficial canônico (`test-runner.sh`) possui a prerrogativa operacional de gerar o certificado a partir da execução efetiva da suíte canônica.

### 2. Defesa em Profundidade e Limitações Inerentes
- **O Gate Local Não é um Cofre Criptográfico**: O `safety-gate` e os hooks rodam no espaço de usuário do host com os mesmos privilégios do próprio agente. Um processo arbitrário com acesso irrestrito ao sistema operacional pode tecnicamente manipular arquivos se os hooks forem contornados externamente.
- **A Garantia Real Vem do Servidor**: A garantia inegociável de integridade da base de código em ambientes compartilhados e de produção decorre da **Proteção de Branch no Servidor** (GitHub Branch Protection Rules / GitLab Protected Branches / CI Pipeline Remota obrigatória com status checks bloqueantes). O gate local atua como uma barreira rápida (shift-left) de prevenção e disciplina operacional para o desenvolvedor e para o agente local, evitando pipeline red remota e retrabalho.

## Decisões Arquiteturais (Filosofia Ponytail)

### Decisão 1: Lista Positiva de Leituras para `.ceh/`
Em vez de tentar listar todos os utilitários de escrita possíveis do Linux (tarefa propensa a lacunas), a regra adota abordagem em lista permitida: comandos que mencionam `.ceh/` são `deny`, a menos que o comando inicial pertença à lista explícita de utilitários de leitura segura (`ALLOWED_READ_CMDS`).

### Decisão 2: Interceptação Dual (Shell e Ferramentas de Arquivo)
O hook de pre-tool interception protege simultaneamente:
- O canal de terminal (`run_command` / `Bash`).
- O canal de ferramentas de escrita de arquivos (`write_to_file`, `replace_file_content`, `multi_replace_file_content` no Antigravity IDE; `Write`, `Edit`, `MultiEdit`, `NotebookEdit` no Claude Code).

### Decisão 3: Rejeição de `tree_hash` e `runner_version` (Anti-Over-Engineering)
Foi deliberadamente descartada a inclusão de metadados complexos como `tree_hash` ou `runner_version` no schema do certificado.
- **Justificativa**: O hash do commit (`commit_hash`) já amarra deterministicamente o certificado à árvore Git correspondente. Num ambiente local onde o agente tem privilégios de execução, calcular e validar um `tree_hash` não adiciona barreira de segurança real contra adulteração intencional, introduzindo apenas complexidade acidental, fragilidade em branches transitórias e quebra de ergonomia. A simplicidade cirúrgica é a melhor salvaguarda.

### Decisão 4: Proteção do Diretório `.ceh/` Inteiro (Handoff 038 / AL1)
A proteção não se restringe aos nomes específicos dos arquivos de certificado (`last-ci-run.json`, etc.). Toda manipulação do diretório `.ceh/` como um todo (`cp -r`, `mv`, `rsync`, `rm -rf .ceh`) é bloqueada compulsoriamente como `deny`, impedindo a substituição em bloco de certificados. Leituras puras do diretório (`ls .ceh`, `ls -la ./.ceh`) permanecem liberadas como `allow`.

### Decisão 5: Contratos de Retorno de Hook Específicos por Host (E11 Controlado / AL2)
A caracterização experimental rigorosa 3x2x2 (documentada em `docs/temp_implementation/evidence/host-probe/agy/20260927T034219Z/`) comprovou com dados observados (`OBSERVED`):
- No Antigravity CLI (`agy` 1.2.11), o braço de controle (**sem hook**) executa normalmente tanto escrita quanto comandos de shell em modo não interativo. O retorno de `{"decision": "allow"}` é 100% neutro e equivalente ao controle, enquanto retornar `{}` bloqueia compulsoriamente qualquer ferramenta. Portanto, o agy exige `{"decision": "allow"}` afirmativo.
- No Claude Code, a regra F6 mantém o retorno `{}` vazio para allow, preservando a disciplina de permissões nativa do host.

### Decisão 6: Regra de Desenho do P2 — Invariante de Padrões Catastróficos Globais (Handoff 062)
Padrões que dependem da análise da linha bruta inteira (como fork bombs ou comandos catastróficos contendo separadores `;`, `|`, `&`) DEVEM rodar compulsoriamente antes de qualquer decomposição léxica (`split_shell_pipeline`). O analisador semântico pós-decomposição continua responsável pela resolução de alvos e canonicalização de caminhos (ex: `rm.py`), mas a integridade contra comandos catastróficos globais é avaliada no marco zero da linha bruta.

## Limites Conhecidos do Gate Estático & Fronteira de Sandboxing

O gate estático do CEH atua como **defesa em profundidade e disciplina operacional (shift-left)**, operando no espaço de usuário do host. Por definição arquitetural, um analisador estático **não é uma sandbox de isolamento do kernel nem um emulador de execução**. Os limites inerentes abaixo são formalmente reconhecidos e documentados:

### 1. Comandos com Conteúdo Opaco ou Dinâmico
- **Pipes de Download/Execução**: `curl ... | bash`, `wget -O - ... | sh`. O payload remoto não é observável antes da execução.
- **Execução Remota ou em Contêineres**: `ssh user@remote ...`, `docker exec ...`. O ambiente e binários de destino são isolados do host local.
- **Código Proveniente de Arquivo ou Redirecionamento de Stdin**: `python script.py`, `bash file.sh`, `mysql < dump.sql`. O script interno não é interpretado pelo gate de shell.
- **Comandos Montados Dinamicamente**: `eval "$CMD"`, `find ... | xargs rm`. A resolução final ocorre apenas no runtime do shell.
- **Alvos Opacos de Automação**: `make -C /path target`, `npm --prefix /path run build`, `npm run <script>`. A receita interna de execução reside em arquivos de build (`Makefile`, `package.json`).
- **Extração de Arquivos Compactados**: `tar -xzf archive.tar.gz`, `unzip archive.zip`. O gate não inspeciona árvores empacotadas no momento da descompactação.

*Comportamento do Gate*: Todos os comandos acima são avaliados conforme seu binário e argumentos visíveis (gerando `allow` por padrão caso não contenham alvos explícitos bloqueados, conforme controles `H062-LIMITE` na bateria).

### 2. Decisões Específicas de Domínio e Falsos Positivos Conhecidos
- **`php artisan migrate --force`**: Mantido como `allow` em produção (PR-22) por constituir o procedimento canônico operacional de migração automatizada em esteiras de deploy.
- **`echo find / -delete`**: Bloqueado como `deny CATASTROPHIC`. O gate adota postura determinística *fail-closed*: strings literais que reproduzam sintaxe de comandos catastróficos disparam o bloqueio preventivo para evitar evasões de aspas complexas.

### 3. Origem de Captura e Catálogo de Ferramentas
- **18 Ferramentas Declaradas (E12)**: Ferramentas autorizadas no catálogo de ferramentas constam como `declared` com evidência comprovada, com promoção para `payload` sob demanda (E12).
- **Opções de Escrita (`--help` / AX1)**: Opções derivadas de `--help` refletem as ferramentas capturadas no ambiente local de referência, registradas no cabeçalho dos artefatos.

### 4. Limites Intrínsecos do Runtime de Hooks na IDE do Antigravity (E13 / Handoff 067)
A caracterização experimental formal na IDE do Antigravity (E13, Handoff 067) comprovou que o executor de hooks da IDE opera com política fail-open diante de encerramentos anormais ou códigos de saída diferentes de zero:
- **Python Ausente no PATH**: Se o interpretador Python configurado no hook não puder ser executado pelo SO, a IDE deixa o comando rodar sem validação.
- **Erro de Sintaxe no Próprio Gate**: Erros sintáticos que impeçam o Python de iniciar a execução do gate impedem o envio da resposta JSON e resultam em fail-open.
- **Estouro de Timeout (SIGKILL)**: Conforme comprovado no braço `timeout` do E13, processos de hook que excedam o tempo limite configurado em `hooks.json` (ex: 15s) são abortados pelo host e a ferramenta do agente é executada sem bloqueio.

*Mitigação*: O código do gate trata defensivamente todos os caminhos de erro previsíveis emitindo `{"decision": "deny", ...}` com exit 0 (v1.4.1). Para as falhas intransponíveis de infraestrutura no host local (timeout forçado, binário ausente), a salvaguarda primária e inegociável permanece na garantia do servidor remoto.

### 5. A Mitigação Real: Garantia no Servidor
Diante de alvos opacos, falhas de host local e comandos montados dinamicamente, a salvaguarda primária e inegociável do CEH é a **Proteção de Branch no Servidor com Status Checks Obrigatórios de CI**. Nenhuma alteração alcança branches protegidas (`main`, `staging`) sem a execução integral da suíte canônica em runner efêmero e auditado no servidor remoto.

## Consequências
- **Positivas**: Falsificação de certificados por parte de LLMs ou scripts acidentais é bloqueada em todos os ambientes (`development`, `staging`, `production`), inclusive contra a substituição inteira da pasta `.ceh`.
- **Ergonomia Preservada**: Comandos normais de auditoria e leitura (`cat .ceh/last-ci-run.json`, `jq . .ceh/last-ci-run.json`, `ls .ceh`) continuam funcionando com resposta `allow`.
- **Transparência e Rastreabilidade**: Fronteiras do gate estático declaradas explicitamente, com testes de controle na bateria garantindo que nenhum comportamento mude silenciosamente.
- **Alinhamento**: Total aderência às regras de processo e segurança estabelecidas nos Handoffs 037, 038 e 062.
