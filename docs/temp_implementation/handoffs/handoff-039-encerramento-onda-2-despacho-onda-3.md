# Handoff 039 — PR-10b homologado, encerramento da Onda 2 e despacho da Onda 3 (PR-11 e PR-12)

**Data/Hora:** 2026-09-27T15:00:00Z
**Instância:** Revisor sênior
**Branch:** `claude/code-review-technical-analysis-kfwcdl`
**Commit revisado:** `dbeaad5` (PR-10b)
**Antecessor:** [Handoff 038](./handoff-038-revisao-pr10-despacho-pr10b.md)

---

## 1. PR-10b: **HOMOLOGADO**

### AL1: diretório `.ceh` protegido (`OBSERVED`)

- **deny:** `cp -r /tmp/fakeceh/. .ceh`, `mv /tmp/fakeceh .ceh`, `rsync -a /tmp/fakeceh/ .ceh/`, `rm -rf .ceh` e `tar -xf … -C .ceh`.
- **allow:** `ls -la .ceh/`, `cat docs/.ceh-notes.md` e `grep -r --exclude-dir=.ceh …`.
- As 5 linhas `PENDENTE:H038-AL1` estão verdes.

### AL2: o E11 agora tem controle, e a conclusão é **sustentada**

Os artefatos brutos estão em `evidence/host-probe/agy/20260927T034219Z/`: 12 execuções (3 braços × escrita/terminal × padrão/YOLO), com o runner versionado. O "padrão" roda **sem nenhuma flag** de bypass (`e11_matrix_runner.py:161`).

| Braço | Escrita | Terminal (`touch`) |
|---|---|---|
| controle (sem hook) | criado | executado |
| `{"decision":"allow"}` | criado | executado |
| `{}` | **bloqueado** | **bloqueado** |

**Leitura da revisão:**

- Para ações que o agy **já permite** sozinho, o allow explícito é igual ao controle.
- Para ações que o agy **nega** sozinho, o E10 no modo padrão (Handoffs 006/007) já tinha mostrado o CEH respondendo allow (cego, antes do PR-00) para `git reset --hard`, e o **agy negou mesmo assim**.
- Os dois experimentos juntos mostram que **o allow explícito é neutro no agy**: não autoaprova, ao contrário do F6 do Claude. No agy, `{}` significa bloqueio, não "sem decisão".
- A implementação atual está correta. Isso fica registrado como `OBSERVED` (E11 + E10) no ADR 007.

**Linha de base avançada** para `dbeaad5`.

### Ressalvas (baixas, sem ação imediata)

- **AM1 (processo):** a execução `20260927T033814Z` foi **apagada** antes do commit, sem registro do motivo. **Regra:** nenhuma execução de sonda é descartada em silêncio. Ou ela fica versionada, ou a evidência registra por que foi descartada (erro do runner, configuração errada etc.). Descarte sem registro abre espaço para escolher o resultado conveniente.
- **AM2 (falsos positivos, fail-closed, backlog):** a proteção do `.ceh` nega leituras e exclusões legítimas: `find . -path ./.ceh -prune …`, `tar czf … --exclude=.ceh .`, `rsync --exclude .ceh …`, `du -sh .ceh`, `diff .ceh/… …` e `git status --ignored .ceh`.
  - **Correção futura:** acrescentar `du`, `diff` e `git status|log|diff` à lista de leitura, e tratar argumentos de exclusão (`--exclude[=]`, `-path … -prune`) como não-alvo.

## 2. **ONDA 2 ENCERRADA** (integridade do push e do hook)

| PR | O que fecha |
|---|---|
| PR-08/08b | G7: cada refspec do push é conferido contra o certificado; `--all`/`--mirror`/`--tags` = deny sob CI; deleção remota graduada; checagem de teste órfão no `doc-audit` |
| PR-09 | Hook fail-closed: payload vazio, sem ferramenta, sem comando ou com ferramenta desconhecida = deny/exit 2 |
| PR-10/10b | G9: certificado e diretório `.ceh` protegidos no terminal e nas ferramentas de escrita; contrato de resposta do agy observado com controle; ADR 007 |

## 3. Despacho — Onda 3 (dois PRs, **um push por commit certificado**)

### PR-11 `fix(install): resultado honesto e simetria com o uninstall`

**Estado atual (`OBSERVED`):**
- `install.sh:199`: `agy plugin validate … >/dev/null 2>&1 || true`, seguido **sempre** de "Plugin validated and active in Antigravity." A falha é engolida, e o sucesso é anunciado.
- A lista de aliases está **duplicada** (`install.sh:212–222` e `:249`; `uninstall.sh:50`).

1. **Validação honesta:**
   - o resultado real do `agy plugin validate` é mostrado;
   - a falha resulta em **exit ≠ 0**, a menos que o usuário passe `--skip-diagnostics` (saída consciente, registrada no log).
2. **Autodiagnóstico pós-instalação**, a partir do diretório instalado:
   - `safety-gate.py --check "rm -rf /"` = deny/CATASTROPHIC;
   - `--check "ls"` = allow;
   - hook com stdin vazio = exit 2 (PR-09).

   Qualquer divergência → exit ≠ 0.
3. **Fonte única de aliases:** um arquivo `clearer-engineering/config/aliases.sh`, lido pelo `install.sh` e pelo `uninstall.sh`.
4. **Testes** no `run-install-verification.sh` (com `HOME` temporário):
   - instalar duas vezes gera **um único** bloco de aliases (idempotência);
   - instalar e depois desinstalar deixa o `~/.bashrc` **idêntico byte a byte** ao original (simetria);
   - **todo** alias aponta para um arquivo que existe na árvore instalada;
   - um `agy` falso (script no `PATH`) que falha na validação faz o `install.sh` sair com exit ≠ 0.
   - **Falsificabilidade:** restaure o `|| true` num clone e mostre o teste reprovando.

### PR-12 `build(release): SemVer, CHANGELOG e instalação fixada por versão`

1. O `plugin.json` passa a ser a **fonte única de versão**: `1.3.0` (as tags `v1.0.0`–`v1.2.0` já existem).
2. `CHANGELOG.md` no formato Keep a Changelog, com a seção 1.3.0 resumindo P0, Onda 0, Onda 1 (G1–G6), Onda 2 (G7, hook, G9) e Onda 3, com links para os handoffs.
3. O one-liner de instalação aceita `CEH_VERSION` e clona `--branch v<versão>`. A documentação publica a URL fixada.
4. O perfil do agente sai do heredoc (`install.sh`, `AGENT_EOF`) para `clearer-engineering/profiles/clearer-harness.agent.md`. Um teste garante que o arquivo instalado é idêntico ao da fonte.
5. **A tag `v1.3.0` não é criada pelo agente.** Ela depende do merge na branch principal, que é decisão do desenvolvedor. O PR-12 só deixa tudo pronto e documenta o comando.

### Critérios de aceite da Onda 3

- [ ] PR-11: os 4 testes do item 4 estão no `run-install-verification.sh` (e este na suíte), com a prova por mutação.
- [ ] PR-12: versão única 1.3.0, `CHANGELOG.md`, `CEH_VERSION` e perfil extraído com teste de identidade.
- [ ] Cada PR num commit próprio, certificado e enviado separadamente (AK1). Redes diferenciais contra `dbeaad5` com 0 relaxamentos. O plano não é editado pelo agente, e a homologação não é declarada pelo agente.

## 4. Depois da v1.3.0

Onda 5 (qualidade: PR-QA B–D, AM2, shellcheck, matriz macOS) e, quando houver evidência de um 3º host, a Onda 4 (núcleo portável → v2.0.0).
