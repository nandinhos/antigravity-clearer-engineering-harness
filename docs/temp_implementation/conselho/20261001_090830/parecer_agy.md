--- CONTRATO DE SAÍDA MANDATÓRIO ---
VEREDITO: RESSALVAS
CERTEZA: 0.95 (Fundamentada nas regras centrais do CEH, integridade da matriz DEV/HML/PRD e histórico de incidentes 063 a 088)
ANALISE_ESPECIALIZADA:
Sob a ótica estrita de **Guardião do Harness & Safety Gate**, a premissa de que *"um controle só vale no ambiente em que foi observado"* é um alinhamento direto e inegociável com a regra nuclear do CEH: `UNKNOWN nunca pode silenciosamente virar OBSERVED`. Controles puramente locais (hooks client-side) são salvaguardas de conveniência em `DEV`, mas falham como barreira absoluta em `PRODUCAO` se não houver enforcing físico no servidor.

Deliberação analítica decisão a decisão:

1. **D1 — Barreira no servidor (Opção A — APROVADA / Certeza: 1.0)**:
   - *Fundamento de Safety Gate*: A regra canônica do CEH define que a branch `main` é `PRODUCAO` com rigor `DENY` Absoluto. Sem ruleset remoto que exija os jobs de `Validate` com exit code 0 e bloqueie force-push e push direto, a matriz de ambiente fica violada por omissão da Camada 3. O enforcement no GitHub transforma o gate de "orientação de boa fé" em bloqueio físico imutável.

2. **D2 — Matriz "onde cada verificação vale" (APROVADA COM RESSALVA / Certeza: 0.95)**:
   - *Ressalva Bloqueante*: A matriz proposta é excelente ao segregar Sandbox, CI e IDE, mas omite um ambiente de execução real: o **`agy` CLI headless** (modo terminal desacompanhado de UI). O CLI do Antigravity possui ciclo de vida de processo e tratamento de `stderr`/`exit code` diferente do webview/IDE RPC (vide Incidente 1 — exit 2 bloqueia no CLI, mas falha aberto na IDE). O ambiente `CLI Headless` DEVE constar explicitamente na taxonomia da matriz.

3. **D3 — Evidência da IDE sem montagem manual (Opção A — APROVADA / Certeza: 0.95)**:
   - *Fundamento*: Elimina a farsa de transcrição manual (Incidente 7). O script `ceh-ide-probe` deve selar o pacote de evidência com hash SHA-256 de todos os artefatos locais contra a tag de release. Gravação de tela (Opção C) deve ser descartada como regra por ser não-determinística, de alto atrito e inauditável por máquina; só faz sentido como exceção forense.

4. **D4 — Paridade de ambiente nos testes (APROVADA COM ADENDO / Certeza: 0.95)**:
   - *Adendo de Segurança (Incidente 9)*: No caso do macOS e filesystems case-insensitive, não se trata de documentar como limitação. O hook do Safety Gate DEVE obrigatoriamente canonicalizar o comando (`cmd.lower()` ou normalização do binário invocado) antes de avaliar a árvore de sintaxe destrutiva. Permitir que `GIT push` burle a regex de pré-push CI por divergência de caixa é uma falha primária do gate local.

5. **D5 — Fechamento dos achados da v2.1.0 (APROVADA em PR ÚNICO / Certeza: 1.0)**:
   - *Fundamento de Blast Radius*: CA1 (bloqueio de redirecionamento `>` contra `.ceh/`) é a correção da brecha de integridade da evidência. CA2 (corpus dourado F01–F10) é o teste de ancoragem que garante não-regressão. Devem tramitar **juntos no mesmo PR `v2.1.1`**, pois correção sem teste dourado viola a invariante do CLEARER (`TEST` e `REVIEW` atrelados à implementação).

6. **D6 — Formalização de Papéis (APROVADA / Certeza: 1.0)**:
   - *Fundamento de Governança*: O Conselho de Seniores é órgão consultivo e deliberativo de arquitetura e processo. A ata registra julgamento e consenso conceitual, mas **NUNCA substitui evidência física de teste (`OBSERVED`) com exit code 0**. A homologação técnica exige o certificado emitido pela revisão independente com suíte íntegra.

RISCOS_IDENTIFICADOS:
1. **Falso sentimento de segurança no macOS**: Permitir comandos com variação de caixa (`GIT`, `Rm`, `Drop`) escapar da inspeção do hook local se o parser não canonicalizar em minúsculas antes da checagem.
2. **Omissão do Antigravity CLI headless**: Tratar "IDE" e "CLI" como equivalentes locais, ignorando diferenças na captura de streams e códigos de saída entre o terminal puro e a interface gráfica.
3. **Fadiga de atrito humano em D3**: Tentar introduzir gravação de tela em releases, gerando sobrecarga manual desnecessária em vez de focar na criptografia dos hashes do `ceh-ide-probe`.

RECOMENDACAO_FINAL:
1. Adotar imediatamente a **Opção A em D1** (Ruleset restrito na branch `main` no GitHub).
2. Aprovar a sequência proposta no item 4 do Handoff 089, incluindo no PR de D4 a canonicalização obrigatória de caixa (`lower()`) no parser de comandos do gate e a inclusão da coluna `CLI Headless` na matriz de D2.
3. Unificar CA1 e CA2 no PR `v2.1.1` acompanhados da geração do pacote do canário emitido pelo `ceh-ide-probe`.
------------------------------------
