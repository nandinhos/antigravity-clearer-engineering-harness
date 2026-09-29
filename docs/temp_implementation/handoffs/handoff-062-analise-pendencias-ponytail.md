# Handoff 062 — Análise completa de pendências e plano Ponytail de fechamento da Onda 5

**Data/Hora:** 2026-09-29T12:00:00Z
**Instância:** Revisor sênior (Claude)
**Branch:** `claude/code-review-technical-analysis-kfwcdl` (alinhada com `main` em `6fc5a07`)
**Antecessores:** [Handoff 050](./handoff-050-revisao-prqa-c-despacho-prqa-b-d.md) (Claude); Handoffs 051–058 (revisão independente pelo Codex); Handoffs 059–061 (autoria do agente)

---

## 1. Estado real (`OBSERVED` em `6fc5a07`)

| Item | Estado |
|---|---|
| Suíte canônica | **64/64 PASS** |
| Redes diferenciais contra `c247c79` | 0 relaxamentos (só apertos desde a última base) |
| Bateria | **0** linhas `PENDENTE` |
| `cluster4_acceptance.py` | nenhum `@expectedFailure` ativo |
| CI da `main` | verde nos merges #3 ([run 36508646438](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36508646438)) e #4 ([run 36513393894](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36513393894)) |
| One-liner `curl …/main/install.sh \| bash` | **funciona** (guarda nova do `BASH_SOURCE` na `main`) |
| Tag publicada | `v1.3.0` em `14510c7`; **37 commits** na `main` depois dela |

**Ondas:** 0, 1, 2 e 3 encerradas. Da Onda 5: PR-18, PR-19 (a/b/c), PR-20 (a/b), PR-22 (b), PR-QA-B, PR-QA-C e PR-QA-D concluídos. **Falta o PR-21.** A Onda 4 (núcleo portável, v2.0.0) é uma decisão estratégica, não pendência.

## 2. Revisão dos commits que entraram na `main` sem homologação independente

A trilha 051–058 teve revisão independente (Codex). Depois do Handoff 058, que **mantinha o D04 aberto e bloqueante**, dois commits de código foram para a `main` com a homologação declarada pelo próprio agente (Handoffs 059 e 061).

### 11081aa — D04 (symlinks): **HOMOLOGADO nesta revisão**

- `environment.py` resolve o caminho físico antes de consultar a branch; `rm.py` ganhou a proteção física (alvo cujo caminho real é `/`, diretório de sistema, `~`, o cwd ou um ancestral do cwd → protegido) e trata symlink que escapa do cwd como inseguro.
- `test_symlink_environment.py` (145 linhas) na suíte; suíte 64/64; redes diferenciais sem relaxamento.
- **Ressalva de processo (baixa):** o commit editou `docs/plano-implementacao-elevacao-ceh.md`, e o Handoff 059 se declarou "homologação geral pronta". As duas coisas são da revisão.

### 2654e64 — P2 (fork bomb) + `--command`/`--cwd`: **HOMOLOGADO nesta revisão**

- **Achado real, vindo da integração do Muse:** os `CATASTROPHIC_PATTERNS` só eram avaliados **depois** do fatiamento léxico; um padrão catastrófico que contém `;`, `|` e `&` era partido e escapava. Estava presente desde antes da v1.3.0, e nenhuma revisão (minha incluída) pegou.
- Correção: checagem catastrófica na **linha bruta**, antes do `split_shell_pipeline` (os padrões de `rm` continuam no analisador semântico). Corpus: 6 linhas, só apertos. Teste acrescentado em `test_rules_data_infra.py`.
- `--command` (alias de `--check`) e `--cwd` só existem no CLI; o caminho do hook continua lendo o `Cwd` do payload. Sem efeito na decisão do hook.
- **Lição:** a checagem que depende de ver o comando **inteiro** tem de rodar antes de qualquer decomposição. Vale como regra de desenho para os próximos analisadores.

**Linha de base avançada** para `6fc5a07`.

## 3. Inventário de pendências, classificado pelo princípio Ponytail

Critério: fazer só o que reduz risco real ou custa pouco; o que é limite inerente de um gate estático **não se persegue — documenta-se uma vez**, com teste que fixa o comportamento atual.

### 3.1 FAZER (risco real ou custo baixo)

| ID | Pendência | Por quê | Custo |
|---|---|---|---|
| **R1** | **Release v1.4.0** | a tag `v1.3.0` **não tem** o conserto do fork bomb; quem instala fixado em `CEH_VERSION=1.3.0` fica exposto. PR-22 e PR-QA-C acrescentaram regras (SemVer: *minor*) | pequeno |
| **R2** | CHANGELOG `[Unreleased]` **vazio** | o conserto de segurança do fork bomb e o D04 não estão registrados | pequeno |
| **P21** | **PR-21** (último item planejado da Onda 5) | o Conselho envia diff e contexto a modelos externos; os `prompt_*.txt` já vazaram o caminho local (AT4/AU1) | médio |
| **B1** | `docker --context X volume rm`, `docker -H … volume prune` = allow em produção | opções globais antes do subcomando escapam da regra do AT3 | pequeno |
| **B2** | AU1: o `doc-audit` só casa `/home/<u>/projects/` | há **7** caminhos `/home/<u>/…` nas atas do Conselho | pequeno |
| **D1** | Limites conhecidos **não documentados** | `curl \| bash`, `ssh`/`docker exec`, código vindo de arquivo/stdin, comando montado em tempo de execução, alvos opacos (`make -C`, `npm --prefix`, `npm run <script>`), conteúdo de arquivos compactados (`tar -x`, `unzip`) — **0 menções** no ADR 007; hoje só existem espalhados nos handoffs | pequeno |

### 3.2 DOCUMENTAR COMO LIMITE (não perseguir)

Entram na seção nova do ADR 007 (D1), cada um com uma linha de **controle** na bateria que fixa o comportamento atual (assim qualquer mudança aparece na rede):

- os alvos opacos e dinâmicos da lista do D1;
- `php artisan migrate --force` = allow (decisão do PR-22: ação normal de deploy);
- falso positivo conhecido `echo find / -delete` = deny (fail-closed; texto que imita comando);
- 18 ferramentas `declared` no catálogo (E12 opcional, sem prazo);
- `--help` capturado no ambiente local (AX1): registrar a origem no cabeçalho.

### 3.3 NÃO FAZER AGORA

- **Tempo do macOS no CI** (≈15 min por job contra ≈2,5 min no Ubuntu): custo de runner, não de risco. Só revisitar se o custo incomodar.
- **Onda 4** (núcleo portável + adaptadores + conformidade, v2.0.0): o gatilho do plano era "evidência de um 3º host". O Muse agora é um consumidor real (achou o P2), então o gatilho **pode** estar satisfeito — mas é decisão do desenvolvedor, com o playbook do Handoff 060 como ponto de partida.

## 4. Despacho — dois commits, cada um com o CI do servidor verde antes do seguinte

### Commit 1 — PR-23 `chore(gate): fechamento da Onda 5 — limites documentados e ajustes finos`

1. **B1:** a regra do AT3 para `docker volume rm|prune` e `docker compose … down -v` aceita **opções globais** do `docker` antes do subcomando (`--context X`, `-H X`, `--host X`, `-c X`, `--config X`, `--log-level X`). Linhas na bateria como `deny`, com controle `docker --context prod volume ls` = allow.
2. **B2:** `doc-audit.py:186` passa a casar qualquer `/home/<u>/` e `/Users/<u>/` (não só `/projects/`); limpe as 7 ocorrências das atas.
3. **D1:** seção **"Limites conhecidos do gate estático"** no ADR 007, com a lista do §3.2, o motivo (conteúdo opaco ou montado em tempo de execução) e a mitigação real (status check obrigatório no servidor). Uma linha de **controle** na bateria por item, com o comportamento **atual** (seja allow ou deny), referência `H062-LIMITE`.
4. **Regra de desenho do P2** no ADR (ou no `rules.py` como comentário de módulo): padrões que dependem da linha inteira rodam antes do fatiamento.
5. Redes diferenciais contra `6fc5a07`: só os apertos do B1.

### Commit 2 — PR-21 `feat(conselho): redação de segredos e caminhos antes do envio externo`

1. Com `--diff`, excluir caminhos sensíveis (`.env*`, `*.pem`, `*.key`, `*secret*`, `id_rsa*`) e mascarar padrões de token conhecidos (chaves de nuvem, tokens de Git, cabeçalhos `Authorization`). Ligado por padrão.
2. Substituir caminhos absolutos de home (`/home/<u>/`, `/Users/<u>/`) por `~/` no contexto enviado e nos `prompt_*.txt` gravados (causa raiz do AT4/AU1).
3. **AU4:** conselheiro sem resposta vira uma linha na **ata**, escrita pelo `conselho-seniores.sh`; o arquivo de parecer bruto fica intocado.
4. Teste com segredo **sintético** (um valor inventado no formato de token) e um caminho de home fictício: nada disso aparece no prompt gravado. Prova por mutação: desligar a redação num clone reprova o teste.

### Depois dos dois commits — Release (desenvolvedor)

- O agente sobe `plugin.json` para **1.4.0**, preenche o CHANGELOG (P2 em **Security**, D04 em **Fixed**, PR-22/QA-B/C/D/20/21/23 em **Added/Changed**) e atualiza a URL fixada no README para `v1.4.0`. Tudo no commit do PR-21 ou num commit de release.
- O desenvolvedor faz o merge para `main` e cria a tag `v1.4.0`.
- Nota de segurança no CHANGELOG: quem estiver fixado em `v1.3.0` deve atualizar (fork bomb).

### Critérios de aceite

- [ ] B1, B2 e D1 fechados; cada limite com controle na bateria.
- [ ] PR-21 com redação ligada por padrão, teste com segredo sintético e prova por mutação.
- [ ] CHANGELOG e versão 1.4.0 prontos para a tag.
- [ ] CI do servidor verde (4/4) em cada commit, com link versionado. O plano não é editado pelo agente, e a homologação não é declarada pelo agente.

## 5. Depois disso

**Onda 5 encerrada** e v1.4.0 publicada. O que resta é estratégico: decidir se o Muse (e o Codex, pelo playbook do Handoff 060) justificam abrir a Onda 4.
