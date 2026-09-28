# Handoff 043 — PR-19 **não homologado**: o primeiro CI do servidor está vermelho em 4/4 jobs; despacho do PR-19a

**Data/Hora:** 2026-09-27T19:00:00Z
**Instância:** Revisor sênior
**Branch:** `claude/code-review-technical-analysis-kfwcdl`
**Commit revisado:** `dbf470d` (PR-19)
**Antecessor:** [Handoff 042](./handoff-042-encerramento-onda-3-release-despacho-pr19.md)

---

## 1. Veredito: **NÃO HOMOLOGADO**

**Execução no servidor** ([run 36326581624](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36326581624), `OBSERVED` via API do GitHub Actions):

| Job | Passo 12 "One-Liner Pipe Install (Real Git Clone via file://)" | Passos 13–20 (suíte canônica, adversarial, install, evals, doc-audit, E2E) |
|---|---|---|
| ubuntu / 3.9 | **failure** | **skipped** |
| ubuntu / 3.12 | **failure** | **skipped** |
| macos / 3.9 | **failure** | **skipped** |
| macos / 3.12 | **failure** | **skipped** |

Os passos 1–11 passaram nos 4 jobs: sintaxe, compileall, shellcheck (informativo) e one-liner com `git` falso. **A suíte canônica nunca rodou no servidor**, então a compatibilidade com o macOS continua **desconhecida**.

**O que está correto:**
- o CI dispara em `claude/**` e em `workflow_dispatch`;
- a matriz 2 SO × 2 Python;
- o `CEH_REPO_URL`;
- o `mktemp` POSIX;
- o `date` portável;
- o shellcheck informativo, com artefato.

## 2. Achados

### AQ1 — ALTO: o passo `file://` está ligado errado, e o clone real vai para o GitHub

```yaml
(cd "$OUTSIDE_DIR" && CEH_REPO_URL="file://$GITHUB_WORKSPACE" cat "$GITHUB_WORKSPACE/install.sh" | HOME="$TMP_HOME" bash)
```

- A atribuição `CEH_REPO_URL=…` vale para o `cat`, **não** para o `bash` do outro lado do pipe. O instalador usa a URL padrão, clona a **`main` do GitHub** (que ainda não tem `profiles/`) e falha, **honestamente**:
  ```
  [INFO] Fetching latest CEH release from GitHub...
  [ERROR] Agent profile source not found at /tmp/ceh-install-…/clearer-engineering/profiles/clearer-harness.agent.md
  ```
- **Reproduzido localmente** com a mesma linha: o mesmo erro. Com `cat install.sh | CEH_REPO_URL="file://$R" HOME=… bash`, o resultado é exit 0 e o perfil é instalado.
- O passo também não verifica **de onde** veio a árvore: `test -f plugin.json` passaria com qualquer versão do repositório.

### AQ2 — MÉDIO: a decisão sobre o bash 3.2 não tem evidência no bash 3.2

- A decisão (exigir bash ≥ 4 no `install.sh`, por causa do `declare -A` em `conselho-seniores.sh:313–315`) está registrada, mas **nada roda no `/bin/bash` 3.2**. O job do macOS põe o bash do Homebrew na frente do `PATH`.
- A guarda nova (`BASH_VERSINFO[0] -lt 4`) só funciona se o `install.sh` inteiro **for lido pelo bash 3.2** até chegar ao `check_prerequisites`. Isso não foi observado.
- Observação de proporcionalidade, **sem exigência**: o `declare -A` está num único script opcional (`conselho-seniores.sh`). Exigir bash 4 só nele, com falha cedo, liberaria o install no macOS padrão. A decisão é de vocês, mas precisa de evidência em qualquer um dos dois caminhos.

### AQ3 — ALTO (processo): entrega declarada sem o resultado do servidor

- O Handoff 042 §4.5 pedia o link da execução com os 4 jobs e o resultado de cada passo.
- O relatório diz "O pipeline remoto … já foi acionado" e transfere a verificação para o usuário ("Próximo passo: acompanhar a aba Actions"). O CI terminou **vermelho um minuto depois** do push.
- **Regra daqui em diante:** com o CI do servidor ligado nesta branch, **a entrega só é declarada depois que a execução do servidor no commit enviado termina**. O relatório traz o link e a conclusão de cada job. Se estiver vermelha, não é uma entrega: é diagnóstico, correção e novo push.

## 3. Despacho — PR-19a `fix(ci): clone real via file://, prova no bash 3.2 e CI verde nos 4 jobs`

Um commit (ou mais, se o CI exigir iterações), sempre com um push por commit certificado.

1. **AQ1:**
   - a variável vai para o lado do `bash`: `cat "$GITHUB_WORKSPACE/install.sh" | CEH_REPO_URL="file://$GITHUB_WORKSPACE" HOME="$TMP_HOME" bash`;
   - o passo prova a **origem** da árvore: `cmp` entre o `agent.md` instalado e o `clearer-engineering/profiles/clearer-harness.agent.md` do workspace, e o `plugin.json` instalado com a versão do workspace.
   - **Controle negativo:** a execução [36326581624](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36326581624), com a ligação errada, já é a prova de que o passo reprova quando a árvore não vem do commit. Cite-a na evidência.
2. **AQ2:** no job do macOS, **antes** de pôr o bash do Homebrew no `PATH` (ou chamando `/bin/bash` explicitamente):
   - `/bin/bash --version` registrado no log (deve ser 3.2);
   - `/bin/bash -n install.sh` e `/bin/bash -n uninstall.sh`;
   - com a decisão atual: `cat install.sh | /bin/bash` num `HOME` temporário sai com exit ≠ 0 e contém `Bash 4.0+ is required`. O mesmo vale para `/bin/bash install.sh`;
   - se a decisão mudar para exigir bash 4 só no `conselho-seniores.sh`: o `install-verification` roda inteiro sob `/bin/bash` 3.2, e o `conselho-seniores.sh` sob 3.2 sai cedo com mensagem clara. Atualize o CHANGELOG.
3. **Macos por inteiro:** com o passo 12 corrigido, os passos 13–20 rodam pela primeira vez no macOS. Qualquer falha é diagnosticada com a linha do log e corrigida **neste PR**, com correção mínima de portabilidade (BSD `sed`, `stat`, `readlink`, `cp`, `date`, `find`). Nenhum `continue-on-error` fora do shellcheck.
4. **Shellcheck:** a contagem de linha de base por código SC vem do **artefato do servidor** (ubuntu/3.12), não de uma execução local. O relatório mostra os dois números, se forem diferentes.
5. **Evidência (AQ3):** o link da execução no commit final, com a conclusão dos 4 jobs **success** e a lista dos passos. Ela só é escrita depois que o servidor termina.

### Critérios de aceite do PR-19a

- [ ] O CI do servidor está **verde nos 4 jobs** no commit enviado, com link na evidência.
- [ ] O passo `file://` prova a origem da árvore (`cmp`), e a execução vermelha anterior está citada como controle negativo.
- [ ] Há evidência no `/bin/bash` 3.2 real do macOS para a decisão registrada.
- [ ] As falhas de macOS nos passos 13–20, se houver, estão diagnosticadas e corrigidas.
- [ ] As duas redes diferenciais contra `dbf470d` registram 0 relaxamentos. O plano não é editado pelo agente, e a homologação não é declarada pelo agente.

## 4. Nota para o desenvolvedor

- Este commit de revisão também dispara o CI em `claude/**` e vai sair **vermelho pelo mesmo AQ1**. É esperado até o PR-19a.
- A partir do PR-19a, a revisão confere o CI do servidor em cada entrega.
- **A release v1.3.0 (Handoff 042 §3) deve esperar o PR-19a verde:** é o primeiro sinal de servidor de toda a Onda 0–3.

## 5. Sequência

PR-19a (CI verde) → release v1.3.0 (desenvolvedor) → PR-19b (limpeza do shellcheck, que passa a bloquear) → PR-18, PR-QA B–D, AM2, AP1–AP3 → PR-20/21.
