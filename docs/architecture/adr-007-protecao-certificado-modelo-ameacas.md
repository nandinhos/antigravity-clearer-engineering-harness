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

## Consequências
- **Positivas**: Falsificação de certificados por parte de LLMs ou scripts acidentais é bloqueada em todos os ambientes (`development`, `staging`, `production`).
- **Ergonomia Preservada**: Comandos normais de auditoria e leitura (`cat .ceh/last-ci-run.json`, `jq . .ceh/last-ci-run.json`) continuam funcionando com resposta `allow`.
- **Alinhamento**: Total aderência às regras de processo e segurança estabelecidas no Handoff 037.
