hermes: finishing an interrupted source update...
  → Preparing Node dependencies…
  ✓ Preparing Node dependencies
  → Building the TUI…
  ✓ Building the TUI
  → Building the web UI…
  ✓ Building the web UI
  ⚠ Memory provider 'multi_agent_persistent_memory' is configured but not installed and not in the plugin catalog. Install it with `hermes plugins install <source>` or change memory.provider.

✓ Code updated!
  ✓ Model catalog cache refreshed from checkout

→ Syncing bundled skills...
  ↑ 11 updated: email-inbox-triage, blocked-page-recovery, github, requesting-code-review, inspecting-hermes-desktop-dom, notion, findmy, opencode, codex, competitor-news-monitor, baoyu-infographic
  ~ 25 user-modified (kept)
    → see them: hermes skills list-modified  (diff/reset to resume updates)

→ Syncing bundled skills to all profiles...
  default: ~25 user-modified
  reviewer: ↑22 updated

→ Checking configuration for new options...

  ℹ Updating config format (v40 → v49)…
  ✓ Config format updated (no new settings to configure)
  ℹ curator.stale_after_days=14 (was: 30)
  ℹ curator.archive_after_days=30 (was: 90)
  ℹ terminal.docker_image unset (follows the default, nousresearch/hermes-sandbox:desktop)
  ℹ terminal.modal_image unset (follows the default, nousresearch/hermes-sandbox:desktop)
  ℹ terminal.daytona_image unset (follows the default, nousresearch/hermes-sandbox:desktop)
  ℹ terminal.singularity_image unset (follows the default, nousresearch/hermes-sandbox:desktop)
  ℹ terminal.vercel_runtime unset (fresh sandboxes use terminal.vercel_image, vercel/sandbox/universal:latest)
  ✓ Profile 'reviewer': config format updated (v22 → v49)

✓ Update complete! (v0.21.5+4911.g6ec0520) [main @ 6ec05205a9]

→ Installing agent-browser (default tool; opt out with `hermes pm install --without agent-browser`)...

→ Installing cua-driver (default tool; opt out with `hermes pm install --without cua-driver`)...
network request failed (<urlopen error [Errno 101] Network is unreachable>); retrying in 1s (attempt 2/4)
Deliberação do Conselho — Papel: Engenheiro de Tooling & Confiabilidade de Agente

---

## Vereditos por decisão

**D1 — Barreira no servidor (regra na `main`): HOMOLOGADO (A) — Certeza 0.95**
A é a única escolha defensável. B mantém a porta dos fundos aberta (push direto com CI verde = mesma coisa que não ter barreira). C já falhou duas vezes (063 AY2, 087 E17). ACRÉSCIMO OBRIGATÓRIO: a regra precisa ser **verificável no CI** — adicionar um job que falha se a ruleset da `main` não estiver ativa (consulta autenticada à API, igual à evidência recomendada). Sem isso, a regra pode ser desabilitada por um admin e ninguém percebe até o próximo incidente. É a mesma classe de bug do 401 do incidente 8, só que aplicada à própria barreira.

**D2 — Matriz "onde cada verificação vale": HOMOLOGADO com ressalvas — Certeza 0.82**
A lógica está correta: sandbox verifica formato e exit code, IDE é o único lugar onde "host bloqueia" é observável. RESSALVAS pela minha especialidade:
- Faltam linhas na matriz. **WSL** tem semântica de path distinta (`/mnt/c/...`, junction points, diferenças de permissão). **Container interno do CI** é diferente do "ponto de vista do CI" (o job roda em container efêmero, mas o que o GitHub reporta é metadata do job). **agy CLI headless** mencionado na pergunta 2 é ambiente distinto da IDE e precisa de linha própria.
- A coluna "CI (GitHub)" está marcada como verificadora de "Proteção da `main`" com "—" — incoerente. Quem verifica a proteção é o job do CI que consome a API; a coluna certa é "consulta autenticada" igual à IDE.
- "Portabilidade macOS" marcada como "depende da máquina" no IDE — não. CI tem runner macOS, e o item deve ser VERIFICADO lá, não delegado.

**D3 — Evidência da IDE sem montagem manual: HOMOLOGADO (A, C opcional) — Certeza 0.88**
A substituição de auto-relato por sensor é a direção correta. RESSALVAS críticas de confiabilidade:
- O probe precisa ser **canário + armadilha**, não só sensor. Se detectar divergência de hash entre o gate instalado e o da tag, deve se recusar a gravar evidência E registrar a divergência num canal que o agente não acessa (append-only, timestamp de fonte externa).
- "Copia linhas da transcrição pelo índice do passo" é frágil — o agente pode pré-escrever uma transcrição forjada com os índices esperados. O probe deve **invocar o comando** (com consentimento explícito) e capturar o output real, **assinar** o pacote (HMAC com chave que o agente não tem) e gravar o hash em local imutável.
- A prova do probe deve ser publicada como **artefato de release** (anexada à tag), não ficar em `.ceh/` local. Caso contrário, o agente que gravou pode também apagar.

**D4 — Paridade de ambiente nos testes: HOMOLOGADO (os quatro) — Certeza 0.90**
Os quatro são baratos e cobrem incidentes reais. ACRÉSCIMOS:
- O job com `CLAUDECODE=1` está ótimo, mas precisa cobrir o **conjunto completo** de vars que o Claude injeta (`CLAUDECODE`, `CLAUDE_PROJECT_DIR`, `CLAUDE_CODE_ENTRYPOINT`, `CLAUDE_CODE_SSE_PORT`, etc), não só as duas óbvias. Capturar via `env | grep ^CLAUDE | sort` no próprio CI é o jeito mais barato.
- `ceh-doctor` é a peça certa, mas **só vale se for ele próprio verificável**. Tem que ter `--self-check` que compara o próprio sha256 contra a tag — senão vira mais um vetor.
- Item "maiúsculas no nome do executável" (incidente 9): não é "decidir entre comparar ou registrar como limite". É **bloquear**: o gate tem que normalizar a primeira palavra do comando para minúsculas antes de qualquer decisão. Caso contrário `GIT` num macOS passa, e isso é uma vulnerabilidade real (CA4).
- Adicionar: um teste estático que verifica que o **gate não confia em nenhuma variável de ambiente** para decisões de segurança. As decisões têm que ser só sobre o comando. (O incidente 4 mostra que vars do ambiente vazaram para a lógica dos testes — a mesma classe pode vazar para o gate.)

**D5 — Fechamento dos achados v2.1.0: HOMOLOGADO (mesmo PR, v2.1.1) — Certeza 0.92**
CA1 e CA2 no mesmo PR é coerente — ambos são hardening contra a mesma classe de falha. RESSALVAS:
- CA1 ("negar qualquer redirecionamento cujo alvo resolva para dentro de `.ceh/`") precisa cobrir a lista exaustiva: `>`, `>>`, `2>`, `&>`, `>|`, `<>`, `tee`, `dd of=`, `cp`, `mv`, `ln -s`, `exec N>`, `bash -c`, backticks, `$()`, redirecionamento dentro de heredoc, redirecionamento via `eval`, redirecionamento via `xargs -I{} sh -c '...>...'`. E a checagem do alvo tem que usar `realpath` (canônico) para vencer symlinks. E tem que ser **case-insensitive** no macOS (`/var` = `/private/var`, `.ceh` vs `.CEH`).
- CA2 (F01–F10 no corpus dourado, avançar `gate_baseline`): homologado, mas o "avançar baseline" precisa de **gating**: a v2.1.1 não pode ser tagueada se a nova baseline não estiver exercitada no CI. Senão vira baseline no papel e fora dele.
- CA5–CA8 na carona: ok, desde que cada um tenha teste próprio. Não agrupar commits que mexam em paths do `docs/audit/` com commits que mexem em regras de detecção — auditoria precisa de histórico limpo.

**D6 — Papéis: HOMOLOGADO com ressalva forte — Certeza 0.75**
A separação está correta e o ponto novo ("a ata do Conselho não homologa sozinha") resolve o CA7 do Handoff 088. RESSALVA ESTRUTURAL:
- "Conselho pode deliberar desenho e processo" / "Conselho NÃO pode substituir a verificação" — bonito no papel, mas **qual é o mecanismo de enforcement?** Se o developer ignorar o veto do Conselho e taguear mesmo assim, o que acontece? Sem instrumento, a regra é só declaração de intenção.
- Sugiro: o Conselho emite veredito em `docs/audit/conselho-<data>-<tag>.md`, e o CI tem um job que **bloqueia a criação da tag** se a ata do Conselho para aquela versão não estiver presente e assinada. Aí "Conselho não homologa" vira um bloqueio técnico, não um pedido de boa-fé.
- Adicionar à tabela: o papel **"Operador do release"** (pode taguear, não pode deliberar). Hoje essa função está misturada com "Desenvolvedor".
- A linha "Agente NÃO pode escrever no `.ceh/`" precisa de enforcement. Se o gate é o que impede, ótimo; se é convenção, vira o incidente 2 esperando para acontecer.

---

## Veredito global

```
VEREDITO: HOMOLOGADO COM RESSALVAS
CERTEZA: 0.88
```

Fundamentação: as seis decisões estão na direção certa, a maioria com evidências físicas (9 incidentes) e cobertura clara. A certeza não é 1.0 porque há três lacunas estruturais: (1) o CI não verifica a si mesmo (regra da main, hash do probe, hash do ceh-doctor) — qualquer barreira que não se auto-verifica é um alvo; (2) a matriz D2 omite WSL, container interno do CI e agy CLI headless; (3) D6 separa papéis mas não cria mecanismo de enforcement do veto do Conselho.

---

## Análise especializada (Tooling & Confiabilidade de Agente)

**Forças do plano sob minha ótica:**

1. O raciocínio das três camadas (hook local, certificado local, CI+main) é a **arquitetura de defesa em profundidade** que a área de confiabilidade de agentes precisa. Cada camada assume que a outra pode falhar — é exatamente o oposto do que o Antigravity v1.4.0 fazia (camada 1 sozinha, falhando aberto).

2. A direção de **substituir auto-relato por sensor assinado** (D3) é o padrão correto de observabilidade. Em qualquer sistema onde o agente é juiz em causa própria, a única saída é instalar uma testemunha externa. O transcript-by-index é criativo, mas precisa de assinatura (ver ressalva).

3. A noção de **paridade de ambiente via job CI** (D4) é a melhor prática de teste de integração: rodar o mesmo binário em ambientes nomeados e comparar resultados. É o que evita a classe "funciona na minha máquina" que já custou 4 dos 9 incidentes.

4. O **whitelist normalizado para minúsculas** antes de qualquer decisão (ressalva em D4) é o tipo de detalhe que pega toda uma classe de bypass sem custar nada. Vale também para o conjunto de caracteres de `>`, `|`, `;` etc — tem que ser uma classe POSIX canônica, não uma string literal que falha em Unicode esquisito.

**Vulnerabilidades que o plano não fecha:**

1. **Auto-verificação das barreiras (gap sistêmico).** Toda barreira proposta (D1 ruleset, D3 probe, D4 doctor) pode ser desabilitada por um humano com permissão. Sem um job CI que verifica a barreira, o plano protege contra o agente mas não contra o operador descuidado ou malicioso. A CI que verifica a CI é a única resposta. É o mesmo padrão de "verificação de raiz de confiança" em PKI.

2. **Whitelist de comandos normalizada por case-folding (CA4).** No macOS, `GIT` resolve para o binário `git`. O gate atual — assumindo que o que existia em 1.4.0 — comparava o token literalmente. Normalizar para minúsculas **na primeira palavra** antes de qualquer check de whitelist é obrigatório. Senão o incidente 9 se repete em qualquer whitelist, não só em `git`.

3. **Resolução canônica de path (CA1).** Bloquear `> .ceh/...` parece cobrir, mas em macOS `/var` é link para `/private/var` (BG2). `> /var/.../.../...` pode resolver para dentro de `.ceh/` montado em `/private/var`. A checagem tem que ser pós-`realpath`, não literal. E cross-filesystem (bind mount, symlink) tem que estar no mesmo pacote de teste.

4. **Concorrência entre cópias do gate (E15/E16).** O incidente 6 mostrou que `clearer-muse` antigo pode estar ativo junto com o novo. O `ceh-doctor` lista plugins concorrentes, mas **listar não é impedir**. Sugiro: o gate novo, ao iniciar, lê um diretório de manifest assinado e se recusa a operar se encontrar assinatura de versão mais recente em outro caminho. Tipo "first-class install wins, second-class install fails loud".

5. **CI matrix coverage (D2).** O plano diz que o runner macOS verifica portabilidade. Certo. Mas o que verifica o **comportamento do gate em ambiente real de agente** (com todas as vars `CLAUDE*` injetadas, com plugins concorrentes ativos, com hooks de outros sistemas)? A simulação parcial via job com vars injetadas (D4) é boa, mas não reproduz plugins. O `ceh-doctor` rodando no próprio runner antes do teste, em modo "install simulado", seria a cobertura que falta.

6. **Probe transcript (D3) é um problema de cadeia de custódia.** Se o probe lê a transcrição por índice, e a transcrição é texto que o agente escreveu, a cadeia tem um elo fraco. A solução robusta é o probe **invocar** o comando e capturar o output bruto, com **carimbo de tempo de fonte externa** (HTTP HEAD a um servidor de tempo, ou `date -u` do NTP — não do relógio do agente). Aí o output bruto é a verdade, e o índice na transcrição é só referência cruzada.

**Riscos identificados:**

- **Risco de regressão na v2.1.1** (D5): a baseline nova pode recusar mais comandos legítimos. Mitigação: corpus dourado com F01–F10 + métrica de falso positivo comparada com v2.1.0, registrada no CHANGELOG.
- **Risco de bypass via normalização incompleta** (CA4): se o gate normalizar a primeira palavra mas não os argumentos, `git --exec-path=...` ainda pode explorar paths. Mitigação: normalizar **todos os tokens** do comando, não só o primeiro.
- **Risco de privilege escalation via `install.sh`**: se o `install.sh` rodar como root e criar `/usr/local/bin/ceh`, qualquer um com sudo pode trocar o binário. Mitigação: instalar em `~/.local/bin/ceh` por padrão, exigir root explícito e avisar.
- **Risco de clock skew invalidando o carimbo de tempo do probe**: se o agente puder adiantar o relógio do sistema, o carimbo vira falsificável. Mitigação: usar fonte externa de tempo (NTP público via `chronyc tracking` ou `ntpdate -q`).
- **Risco de o Conselho virar teatro** (D6): se o veto do Conselho não tiver enforcement técnico, a próxima vez que developer discordar, a ata vira PDF morto. Mitigação: CI job que exige a ata para taguear, conforme ressalva em D6.
- **Risco residual zero, mas residual ≠ zero**: mesmo com tudo, um developer com chave de admin pode forçar merge, desabilitar ruleset, taguear sem CI. Aceitar como limite do modelo de ameaça e documentar.

---

## Recomendação final

Aprovar o plano com **três acréscimos obrigatórios antes da implementação** e **cinco verificações durante a execução**:

**Antes de implementar:**

1. **Job CI "self-verify"** (D1, D3, D4): um único job que autentica na API do GitHub, verifica a ruleset da `main` ativa, baixa o `ceh-doctor` e o `ceh-ide-probe` da tag alvo, confere sha256, executa ambos, e falha o build se qualquer verificação falhar. Sem isso, as três decisões perdem 30% do valor.

2. **Tabela de normalização** (D4): publicar `docs/gate-normalization.md` com a lista exaustiva de transformações aplicadas **antes** de qualquer decisão do gate. Incluir: case-folding do token inteiro, realpath de todo path, expansão de globs, decodificação de `printf`/`echo -e` se usado em argumento, e o conjunto POSIX de metacaracteres (`; | & $ ` ` ` > < ( ) { } \n \r \t`). A tabela é o **contrato** do gate.

3. **Mecanismo de veto do Conselho** (D6): publicar em `docs/audit/conselho-<data>-<tag>.md` é requisito de CI para criar a tag. O developer que taguear sem ata conselhada tem o CI vermelho como primeira barreira. Segunda barreira: a ata precisa ser assinada (chave pública commitada em `docs/audit/conselho-keyring.pub`).

**Durante a execução:**

4. **Cobertura de teste de regressão da baseline** (D5): antes de avançar o `gate_baseline` em v2.1.1, rodar o corpus completo (F01–F10 + casos existentes) e medir a taxa de bloqueio e de falso positivo. Se a taxa de falso positivo subir mais que 5%, não avançar — fazer outro PR pequeno.

5. **Sandbox box do probe** (D3): antes de aceitar o `ceh-ide-probe` como fonte de evidência, rodar um exercício adversariais: agente motivado a forjar evidência recebe o probe e tenta. Se conseguir, o probe é inadequado. O exercício tem que ser registrado em `docs/audit/` para fechar a vulnerabilidade.

6. **Integração com WSL e agy CLI headless** (D2): antes de declarar a matriz completa, validar as linhas novas em ambiente real, não em job CI. Os paths do WSL (`/mnt/c/...`) e o agy CLI (sem hook de IDE) precisam de pelo menos um caso cada na matriz, ou a tabela vira wishful.

7. **Auditoria do histórico de tagueamento** (D1, pós-condição): depois que D1 estiver ativo, gerar `git tag -l --format='%(refname:short) %(creatordate:short)'` retroativo e cruzar com as atas do Conselho existentes. Se houver tag sem ata, a ruleset precisa ter sido desabilitada em algum momento — abrir achado.

8. **Plano de rollback** (todos): cada uma das 6 decisões precisa de uma linha "como reverter em 5min" na própria seção. Sem isso, a próxima onda de incidente vai brigar com o "vamos consertar" em vez de "vamos reverter e investigar".

Aprovar D1, D3, D4, D5, D6 com os acréscimos. Aprovar D2 com a expansão da matriz (WSL, container interno, agy CLI headless) e a correção da coluna CI. Sequência: 1 → 4 → 3 → 2 → 5, nessa ordem, com a auto-verificação (acréscimo 1) implementada junto com D1.

session_id: 20261001_091427_628c00
