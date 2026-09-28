# Evidência de Justificativa de Diff do Golden Corpus (PR-04c)

Este documento registra e justifica formalmente cada uma das alterações observadas no Golden Corpus Snapshot (`gate_corpus.expected.jsonl`) no **PR-04c**, atendendo estritamente às correções solicitadas no **Handoff 015** para resolução dos achados S1 (atalho seguro restrito ao repositório local e `/tmp/`) e S2 (resolução de `$PWD` contra o diretório de trabalho da avaliação e isolamento de variáveis incertas).

## Resumo Executivo das Alterações
- Total anterior de avaliações no Golden Corpus: 616
- Registros preexistentes alterados: **3** (`CMD-202` dev, sta, pro: reversão do alargamento indevido de `FILESYSTEM_SAFE` em caminho absoluto)
- Novos registros adicionados ao corpus: **27** (9 novos comandos × 3 ambientes)
  - 15 registros da tabela S1 (caminhos absolutos e fora do cwd negados em produção)
  - 3 registros de controle seguro (`/tmp/ceh-x` mantido seguro em todos os ambientes)
  - 9 registros das variantes de variáveis S2 (`$PWD`, `"$PWD"/*` e `$OLDPWD`)
- Total consolidado pós-PR-04c: **643 avaliações**

---

## 1. Reversão do Alargamento do Atalho Seguro (S1: 3 registros alterados)

No PR-04b, `CMD-202` (`rm -rf /home/user/projeto/build`) havia sido classificado como `FILESYSTEM_SAFE` em produção por terminar com o segmento `build`. Conforme especificado no Handoff 015, caminhos absolutos genéricos fora de `/tmp/` não ganham atalho em produção e seguem a regra normal de `FILESYSTEM`:

| ID | Comando | Ambiente | Antes (PR-04b) | Depois (PR-04c) | Justificativa |
|---|---|---|---|---|---|
| `CMD-202-dev` | `rm -rf /home/user/projeto/build` | dev | allow / FILESYSTEM_SAFE | **allow / FILESYSTEM** | [S1] Caminho absoluto em DEV segue a regra normal de FILESYSTEM permitida com salvaguarda local. |
| `CMD-202-sta` | `rm -rf /home/user/projeto/build` | staging | allow / FILESYSTEM_SAFE | **ask / FILESYSTEM** (com alertas 1/2 e 2/2) | [S1] Bloqueia bypass em staging; exige confirmação com alerta de rollback. |
| `CMD-202-pro` | `rm -rf /home/user/projeto/build` | prod | allow / FILESYSTEM_SAFE | **deny / FILESYSTEM** | [S1] Bloqueia bypass em produção; Production Lock impede deleção acidental na branch principal. |

---

## 2. Tabela S1: Caminhos Absolutos Bloqueados em Produção (15 novos registros)

Caminhos absolutos fora de `/tmp/` e caminhos relativos que saem do diretório de trabalho são tratados pelas regras gerais de `FILESYSTEM` e **terminantemente bloqueados em produção**:

| ID | Comando | Ambiente | Decisão | Use Case | Justificativa |
|---|---|---|---|---|---|
| `CMD-212-dev` | `rm -rf /var/www/site/dist` | dev | **allow** | FILESYSTEM | [S1] Permitido em dev com salvaguarda. |
| `CMD-212-sta` | `rm -rf /var/www/site/dist` | staging | **ask** | FILESYSTEM | [S1] Exige confirmação em staging. |
| `CMD-212-pro` | `rm -rf /var/www/site/dist` | prod | **deny** | FILESYSTEM | [S1] Bloqueado pelo Production Lock. |
| `CMD-213-dev` | `rm -rf /srv/app/build` | dev | **allow** | FILESYSTEM | [S1] Permitido em dev com salvaguarda. |
| `CMD-213-sta` | `rm -rf /srv/app/build` | staging | **ask** | FILESYSTEM | [S1] Exige confirmação em staging. |
| `CMD-213-pro` | `rm -rf /srv/app/build` | prod | **deny** | FILESYSTEM | [S1] Bloqueado pelo Production Lock. |
| `CMD-214-dev` | `rm -rf /opt/prod/app/dist/` | dev | **allow** | FILESYSTEM | [S1] Permitido em dev com salvaguarda. |
| `CMD-214-sta` | `rm -rf /opt/prod/app/dist/` | staging | **ask** | FILESYSTEM | [S1] Exige confirmação em staging. |
| `CMD-214-pro` | `rm -rf /opt/prod/app/dist/` | prod | **deny** | FILESYSTEM | [S1] Bloqueado pelo Production Lock. |
| `CMD-215-dev` | `rm -rf /etc/nginx/coverage/` | dev | **allow** | FILESYSTEM | [S1] Permitido em dev com salvaguarda. |
| `CMD-215-sta` | `rm -rf /etc/nginx/coverage/` | staging | **ask** | FILESYSTEM | [S1] Exige confirmação em staging. |
| `CMD-215-pro` | `rm -rf /etc/nginx/coverage/` | prod | **deny** | FILESYSTEM | [S1] Bloqueado pelo Production Lock. |
| `CMD-216-dev` | `rm -rf ../../prod-release/dist` | dev | **allow** | FILESYSTEM | [S1] Caminho que sai do cwd segue regra geral em dev. |
| `CMD-216-sta` | `rm -rf ../../prod-release/dist` | staging | **ask** | FILESYSTEM | [S1] Exige confirmação em staging. |
| `CMD-216-pro` | `rm -rf ../../prod-release/dist` | prod | **deny** | FILESYSTEM | [S1] Bloqueado pelo Production Lock. |

---

## 3. Controles Seguros Canônicos (3 novos registros)

Caminhos sob `/tmp/` mantêm a semântica original do CEH de atalho de limpeza segura:

| ID | Comando | Ambiente | Decisão | Use Case | Justificativa |
|---|---|---|---|---|---|
| `CMD-217-dev` | `rm -rf /tmp/ceh-x` | dev | **allow** | FILESYSTEM_SAFE | [S1 Controle] Prefixo `/tmp/` preservado como seguro em dev. |
| `CMD-217-sta` | `rm -rf /tmp/ceh-x` | staging | **allow** | FILESYSTEM_SAFE | [S1 Controle] Prefixo `/tmp/` preservado como seguro em staging. |
| `CMD-217-pro` | `rm -rf /tmp/ceh-x` | prod | **allow** | FILESYSTEM_SAFE | [S1 Controle] Prefixo `/tmp/` preservado como seguro em produção. |

---

## 4. Variantes de Variáveis de Ambiente (S2: 9 novos registros)

`$PWD` e `${PWD}` resolvem para o diretório de trabalho da avaliação (nunca `os.environ["PWD"]`), bloqueando deleções catastróficas. Variáveis não resolvidas tornam o alvo incerto:

| ID | Comando | Ambiente | Decisão | Use Case | Justificativa |
|---|---|---|---|---|---|
| `CMD-218-dev` | `rm -rf $PWD` | dev | **deny** | CATASTROPHIC | [S2] `$PWD` resolvido contra cwd equivale a deleção de `.`. |
| `CMD-218-sta` | `rm -rf $PWD` | staging | **deny** | CATASTROPHIC | [S2] Bloqueio incondicional em staging. |
| `CMD-218-pro` | `rm -rf $PWD` | prod | **deny** | CATASTROPHIC | [S2] Bloqueio incondicional em produção. |
| `CMD-219-dev` | `rm -rf "$PWD"/*` | dev | **deny** | CATASTROPHIC | [S2] Wildcard sobre o cwd equivale a `rm -rf *` ou `rm -rf ./*`. |
| `CMD-219-sta` | `rm -rf "$PWD"/*` | staging | **deny** | CATASTROPHIC | [S2] Bloqueio incondicional em staging. |
| `CMD-219-pro` | `rm -rf "$PWD"/*` | prod | **deny** | CATASTROPHIC | [S2] Bloqueio incondicional em produção. |
| `CMD-220-dev` | `rm -rf $OLDPWD` | dev | **ask** | FILESYSTEM | [S2] Variável não resolvida torna o alvo incerto (Invariante 7). |
| `CMD-220-sta` | `rm -rf $OLDPWD` | staging | **ask** | FILESYSTEM | [S2] Exige confirmação em staging. |
| `CMD-220-pro` | `rm -rf $OLDPWD` | prod | **deny** | FILESYSTEM | [S2] Alvo incerto com potencial destrutivo bloqueado em produção. |
