# Evidência de Justificativa de Diff do Golden Corpus (PR-04b)

Este documento registra e justifica formalmente cada uma das alterações observadas no Golden Corpus Snapshot (`gate_corpus.expected.jsonl`) no **PR-04b**, atendendo às correções solicitadas no **Handoff 014** para resolução dos achados R1 (falsos positivos em DEV), R2 (variantes de bypass) e R3 (integridade de evidência de ambiente).

## Resumo Executivo das Alterações
- Total anterior de avaliações no Golden Corpus: 586
- Registros preexistentes alterados: **3** (CMD-095 dev, sta, pro: reversão de CATASTROPHIC para FILESYSTEM)
- Novos registros adicionados ao corpus: **30** (10 novos comandos × 3 ambientes)
  - 15 registros de controles de caminho absoluto legítimo (R1)
  - 15 registros de variantes de bypass de raiz e ancestrais normalizados (R2)
- Total consolidado pós-PR-04b: **616 avaliações**

---

## 1. Correção do R1 no CMD-095 (3 registros alterados)

No PR-04, `CMD-095` (`rm -rf a.txt /var/lib/postgresql`) havia sido incorretamente classificado como `CATASTROPHIC` por tratar qualquer descendente sob `/var` como diretório do sistema. Conforme especificado no Handoff 014, descendentes de diretórios protegidos não são catastróficos e seguem as regras de `FILESYSTEM` normais por ambiente:

| ID | Comando | Ambiente | Antes (PR-04) | Depois (PR-04b) | Justificativa |
|---|---|---|---|---|---|
| `CMD-095-dev` | `rm -rf a.txt /var/lib/postgresql` | dev | deny / CATASTROPHIC | **allow / FILESYSTEM** | [R1] `/var/lib/postgresql` é descendente, não raiz do sistema; permitido em dev com salvaguarda local. |
| `CMD-095-sta` | `rm -rf a.txt /var/lib/postgresql` | staging | deny / CATASTROPHIC | **ask / FILESYSTEM** (com alertas 1/2 e 2/2) | [R1] Volta ao comportamento canônico de homologação para sistema de arquivos. |
| `CMD-095-pro` | `rm -rf a.txt /var/lib/postgresql` | prod | deny / CATASTROPHIC | **deny / FILESYSTEM** | [R1 + G1] Bloqueado pelo Production Lock de FILESYSTEM (alvo inseguro impede atalho de limpeza). |

---

## 2. Controles de Caminho Absoluto Legítimo (R1: 15 novos registros)

Caminhos absolutos dentro de `/home`, `/opt`, `/var` ou `/usr` utilizados legitimamente por agentes ou usuários em desenvolvimento não sofrem falso positivo de bloqueio catastrófico:

| ID | Comando | Ambiente | Decisão | Use Case | Justificativa |
|---|---|---|---|---|---|
| `CMD-202-dev` | `rm -rf /home/user/projeto/build` | dev | **allow** | FILESYSTEM_SAFE | [R1] Atalho de build em caminho absoluto permitido em dev. |
| `CMD-202-sta` | `rm -rf /home/user/projeto/build` | staging | **allow** | FILESYSTEM_SAFE | [R1] Atalho de build em caminho absoluto permitido em staging. |
| `CMD-202-pro` | `rm -rf /home/user/projeto/build` | prod | **allow** | FILESYSTEM_SAFE | [R1] Atalho de build em caminho absoluto permitido em produção. |
| `CMD-203-dev` | `rm -rf /home/user/projeto/src/old` | dev | **allow** | FILESYSTEM | [R1] Descendente sob home permitido em dev. |
| `CMD-203-sta` | `rm -rf /home/user/projeto/src/old` | staging | **ask** | FILESYSTEM | [R1] Exige confirmação em staging. |
| `CMD-203-pro` | `rm -rf /home/user/projeto/src/old` | prod | **deny** | FILESYSTEM | [R1] Bloqueado em produção pelo lock de arquivos. |
| `CMD-204-dev` | `rm -rf /opt/myapp/cache` | dev | **allow** | FILESYSTEM | [R1] Descendente sob `/opt` permitido em dev. |
| `CMD-204-sta` | `rm -rf /opt/myapp/cache` | staging | **ask** | FILESYSTEM | [R1] Exige confirmação em staging. |
| `CMD-204-pro` | `rm -rf /opt/myapp/cache` | prod | **deny** | FILESYSTEM | [R1] Bloqueado em produção pelo lock de arquivos. |
| `CMD-205-dev` | `rm -rf /var/tmp/ceh-x` | dev | **allow** | FILESYSTEM | [R1] Descendente sob `/var` permitido em dev. |
| `CMD-205-sta` | `rm -rf /var/tmp/ceh-x` | staging | **ask** | FILESYSTEM | [R1] Exige confirmação em staging. |
| `CMD-205-pro` | `rm -rf /var/tmp/ceh-x` | prod | **deny** | FILESYSTEM | [R1] Bloqueado em produção pelo lock de arquivos. |
| `CMD-206-dev` | `rm -rf /usr/local/lib/node_modules/foo` | dev | **allow** | FILESYSTEM | [R1] Descendente sob `/usr` permitido em dev. |
| `CMD-206-sta` | `rm -rf /usr/local/lib/node_modules/foo` | staging | **ask** | FILESYSTEM | [R1] Exige confirmação em staging. |
| `CMD-206-pro` | `rm -rf /usr/local/lib/node_modules/foo` | prod | **deny** | FILESYSTEM | [R1] Bloqueado em produção pelo lock de arquivos. |

---

## 3. Variantes de Bypass de Raiz e Ancestrais (R2: 15 novos registros)

Caminhos com barras repetidas, dot-slashes, referências a ancestrais do diretório de trabalho ou home de root são canonicamente normalizados e bloqueados incondicionalmente como `CATASTROPHIC` em qualquer ambiente:

| ID | Comando | Ambiente | Decisão | Use Case | Justificativa |
|---|---|---|---|---|---|
| `CMD-207-dev` | `rm -rf //` | dev | **deny** | CATASTROPHIC | [R2] Barras repetidas colapsadas para raiz `/`. |
| `CMD-207-sta` | `rm -rf //` | staging | **deny** | CATASTROPHIC | [R2] Bloqueio incondicional em staging. |
| `CMD-207-pro` | `rm -rf //` | prod | **deny** | CATASTROPHIC | [R2] Bloqueio incondicional em produção. |
| `CMD-208-dev` | `rm -rf /./` | dev | **deny** | CATASTROPHIC | [R2] `/./` normalizado para raiz `/`. |
| `CMD-208-sta` | `rm -rf /./` | staging | **deny** | CATASTROPHIC | [R2] Bloqueio incondicional em staging. |
| `CMD-208-pro` | `rm -rf /./` | prod | **deny** | CATASTROPHIC | [R2] Bloqueio incondicional em produção. |
| `CMD-209-dev` | `rm -rf ../..` | dev | **deny** | CATASTROPHIC | [R2] Ancestral do diretório de trabalho normalizado. |
| `CMD-209-sta` | `rm -rf ../..` | staging | **deny** | CATASTROPHIC | [R2] Bloqueio incondicional em staging. |
| `CMD-209-pro` | `rm -rf ../..` | prod | **deny** | CATASTROPHIC | [R2] Bloqueio incondicional em produção. |
| `CMD-210-dev` | `rm -rf ./*` | dev | **deny** | CATASTROPHIC | [R2] Glob sobre o próprio diretório de trabalho. |
| `CMD-210-sta` | `rm -rf ./*` | staging | **deny** | CATASTROPHIC | [R2] Bloqueio incondicional em staging. |
| `CMD-210-pro` | `rm -rf ./*` | prod | **deny** | CATASTROPHIC | [R2] Bloqueio incondicional em produção. |
| `CMD-211-dev` | `rm -rf ~root` | dev | **deny** | CATASTROPHIC | [R2] Expansão de home de root protegida. |
| `CMD-211-sta` | `rm -rf ~root` | staging | **deny** | CATASTROPHIC | [R2] Bloqueio incondicional em staging. |
| `CMD-211-pro` | `rm -rf ~root` | prod | **deny** | CATASTROPHIC | [R2] Bloqueio incondicional em produção. |
