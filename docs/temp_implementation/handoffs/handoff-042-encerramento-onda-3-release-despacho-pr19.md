# Handoff 042 — PR-12b homologado, **Onda 3 encerrada**; roteiro da v1.3.0 e despacho do PR-19 (Onda 5)

**Data/Hora:** 2026-09-27T18:00:00Z
**Instância:** Revisor sênior
**Branch:** `claude/code-review-technical-analysis-kfwcdl`
**Commit revisado:** `88ac217` (PR-12b)
**Antecessor:** [Handoff 041](./handoff-041-revisao-pr11b-pr12-despacho-pr12b.md)

---

## 1. PR-12b: **HOMOLOGADO**

Reproduzido de forma independente, com `git` e `agy` falsos no `PATH` e sem rede (`OBSERVED`).

| Cenário | Clone pedido | Resultado |
|---|---|---|
| `cat install.sh \| bash` fora do repositório | sem `--branch` | exit 0, instalado |
| idem com `CEH_VERSION=1.3.0` | `--branch v1.3.0` | exit 0, instalado |
| idem com `CEH_VERSION=v1.3.0` | `--branch v1.3.0` | exit 0, instalado |
| pipe **dentro** de um clone com `CEH_VERSION=1.3.0` | `--branch v1.3.0` (não usa a árvore local) | exit 0, instalado |
| `bash install.sh` (arquivo) com `CEH_VERSION` | usa a árvore local | exit 0 + **aviso** "versão fixada será ignorada" |
| clone que falha (`v9.9.9` inexistente) | — | **exit 128**, sem anunciar sucesso |
| `source install.sh` | — | o `main` não roda |

- **AO1:** `alias ceh-help='bash ~/bin/help.sh'` e `alias ceh-monitor='bash ~/tools/monitor.sh'` saem **byte a byte** idênticos do install + uninstall (`cmp`). Um órfão legado real (`…/plugins/clearer-engineering/scripts/detect-project.sh .`) é removido. A regra está num único lugar, o `scripts/rc_aliases.py`.
- **AO4:** o CHANGELOG fala em "defense-in-depth", remete ao ADR 007 e não usa mais "inviolable", "non-tamperable" nem "zero-tolerance".
- **AO5:** o teste do AN1 compara com `cmp -s`.
- **Falsificabilidade, reproduzida em clones:**
  - **AO2:** com a guarda antiga restaurada (`if [[ "${BASH_SOURCE[0]}" == "${0}" ]]`), aparece `ERRO AO2`;
  - **AO3:** com a detecção local voltando para `dirname "$0"`, sem exigir arquivo, aparece `ERRO AO3`. Essa mutação **não** constava da evidência, e a revisão a acrescentou;
  - **AO1:** com a heurística `(help|monitor|detect)\.sh` reintroduzida no `rc_aliases.py`, aparece `ERRO AO1`.
- A suíte certificada está verde no HEAD. Um commit, certificado e enviado. O `--amend` foi feito antes do push.

**Linha de base avançada** para `88ac217`.

### Ressalvas baixas (backlog da Onda 5, sem ação agora)

- **AP1:** o install não remove mais o cabeçalho legado `# === CLEARER Engineering Harness (CEH) ===`, como o PR-11 fazia. Ele fica como comentário órfão até o uninstall. É cosmético.
- **AP2:** `rc_aliases.py` usa `pattern.sub(block, content)`, com o bloco como **string de substituição**. Uma barra invertida futura no `aliases.sh` (`\1`, `\n`) seria interpretada. Use `pattern.sub(lambda _: block, content)`.
- **AP3:** a linha "Removed tautological assertions in differential testing mock fixtures", do CHANGELOG, ainda não diz o que mudou.

## 2. **ONDA 3 ENCERRADA** (instalador honesto e release)

| PR | O que fecha |
|---|---|
| PR-11 | validação honesta do `agy plugin validate`, autodiagnóstico pós-instalação, fonte única de aliases |
| PR-11b | uninstall sem efeito colateral: AN1 (prefixo), AN2 (âncora), AN3 (erros visíveis) |
| PR-12 | versão única 1.3.0, CHANGELOG, perfil do agente extraído e com teste de identidade |
| PR-12b | one-liner `curl \| bash` funcional (**quebrado desde `b7df47d`**), versão fixada que nunca é ignorada em silêncio, helper único de aliases |

Com as Ondas 0 a 3 fechadas, o conteúdo planejado para a **v1.3.0** está completo.

## 3. Roteiro da v1.3.0: **decisão e execução do desenvolvedor** (não do agente)

**Achado de processo (`OBSERVED` em `.github/workflows/ci.yml`):** o CI do servidor só dispara em push ou PR para `main`, `staging` e `dev`. **Ele nunca rodou nesta branch.** Toda a certificação até aqui é local (`.ceh/last-ci-run.json`). O ADR 007 diz que a garantia real é o **status check do servidor**, e ele ainda não existiu para este trabalho.

1. Abrir um PR de `claude/code-review-technical-analysis-kfwcdl` para `main`. O `pull_request` para `main` dispara o CI: a primeira execução no servidor.
2. Esperar o CI **verde** no PR. Se ficar vermelho, a correção volta como handoff antes do merge.
3. Configurar a **branch protection** da `main` com o status check do CI obrigatório (ADR 007).
4. Fazer o merge.
5. Criar e publicar a tag **no commit de merge**:
   ```bash
   git checkout main && git pull
   git tag -a v1.3.0 -m "CEH v1.3.0 — Ondas 0 a 3"
   git push origin v1.3.0
   ```
   O gate (G7) confere se a tag aponta para um commit certificado. Rode a suíte (`test-runner.sh`) na `main` antes do push da tag.
6. **Verificação pós-tag:** num `HOME` temporário, rode `curl -fsSL …/v1.3.0/install.sh | CEH_VERSION=1.3.0 bash`. É a primeira instalação real pelo caminho fixado.
7. Depois da tag, o `CHANGELOG.md` ganha uma seção `## [Unreleased]` para a Onda 5.

## 4. Despacho — Onda 5, PR-19 `ci: matriz de plataformas, shellcheck e CI na branch de trabalho`

É o primeiro PR da Onda 5, escolhido porque o AO2 era exatamente o tipo de defeito que um CI de servidor com o caminho `curl | bash` teria pegado há quatro dias. Pode ser feito **antes ou depois** da tag. Se vier depois, ele entra em `[Unreleased]`.

1. **CI na branch de trabalho:** o `ci.yml` passa a disparar também em `push` para `claude/**` e em `workflow_dispatch`. A partir daí, cada entrega do agente tem uma execução no servidor que a revisão consegue consultar.
2. **Matriz:** `os: [ubuntu-latest, macos-latest]` × `python: ['3.9', '3.12']`.
   - **No macOS, o `/bin/bash` padrão é o 3.2.** Os scripts são chamados como `bash …`. Decida, com evidência:
     - ou os scripts suportam o bash 3.2 (sem `declare -A`, sem `${var,,}`, sem `mapfile`/`readarray`, e com `${arr[@]}` vazio seguro sob `set -u`);
     - ou o `install.sh` exige bash ≥ 4 e falha cedo com uma mensagem clara (e o CI do macOS instala o bash via Homebrew).

     Registre a decisão no CHANGELOG.
   - Diferenças BSD a conferir: `sed -i` sem sufixo, `mktemp -t`, `readlink -f`, `stat`, `date`, `cp -r` com `/.`.
3. **Passo do one-liner no CI:** `cat install.sh | bash` num `HOME` temporário, a partir de um diretório fora do repositório. Use o `git` falso do `run-install-verification.sh` (sem rede) **e** um passo real contra o próprio checkout (`file://`), que prova que o `git clone` verdadeiro funciona.
4. **shellcheck:**
   - roda em todos os `*.sh` versionados (19 hoje), mais o `install.sh` e o `uninstall.sh`. Começa **informativo** (`continue-on-error: true`), com o relatório publicado como artefato;
   - a evidência traz a contagem por código (SCxxxx) como linha de base;
   - **não** corrija avisos em massa neste PR. A limpeza é o PR-19b, e o shellcheck passa a bloquear depois dela.
5. **Evidência:** link para a execução do CI no servidor, com os 4 jobs (2 SO × 2 Python), e o resultado de cada passo. Se o macOS falhar, o PR entrega o diagnóstico e a correção mínima, ou o motivo, com a linha do log. Não marque o job como `continue-on-error` para esconder a falha.
6. **Falsificabilidade:** num commit temporário que **não** vai para a branch, ou num `workflow_dispatch` contra um ref de teste, reintroduza a guarda antiga do `BASH_SOURCE` e mostre o passo do one-liner reprovando no servidor. Se isso não for viável, mostre o mesmo passo reprovando localmente com `act` ou com a linha exata do workflow.

### Critérios de aceite do PR-19

- [ ] O CI dispara em `claude/**` e roda verde nos 4 jobs, ou o macOS tem diagnóstico e correção com evidência do servidor.
- [ ] A decisão sobre o bash 3.2 está registrada.
- [ ] O passo do one-liner está no CI, com o `git` falso e com `file://`.
- [ ] O shellcheck é informativo, com a contagem de linha de base na evidência.
- [ ] As duas redes diferenciais contra `88ac217` registram 0 relaxamentos. Um push por commit certificado. O plano não é editado pelo agente, e a homologação não é declarada pelo agente.

## 5. Sequência

v1.3.0 (desenvolvedor, §3) ∥ PR-19 → PR-19b (limpeza do shellcheck, que passa a bloquear) → PR-18 (validação de esquema + fuzz do lexer), PR-QA B–D, AM2 e AP1–AP3 → PR-20/21 → Onda 4 quando houver evidência de um 3º host.
