# Evidência de Justificativa de Diff do Golden Corpus (PR-04d)

Este documento registra e justifica formalmente cada uma das alterações observadas no Golden Corpus Snapshot (`gate_corpus.expected.jsonl`) no **PR-04d**, atendendo às especificações do **Handoff 016** para resolução do achado T1 (bloqueio de escape intermediário via normalização em produção) e variantes de ancestrais catastróficos.

## Resumo Executivo das Alterações
- Total anterior de avaliações no Golden Corpus: **643**
- Registros preexistentes alterados: **0** (ZERO decisões alteradas)
- Registros preexistentes removidos: **0**
- Novos registros adicionados ao corpus: **12** (4 novos comandos × 3 ambientes)
  - 6 registros de proteção contra escape intermediário em produção (T1)
  - 6 registros de variantes opcionais de ancestrais catastróficos
- Total consolidado pós-PR-04d: **655 avaliações**

---

## 1. Proteção T1 — Normalização Estrita de Atalho Seguro (6 novos registros)

Caminhos como `rm -rf build/../src` e `rm -rf coverage/../.git` iniciam com prefixos seguros (`build/`, `coverage/`), mas resolvem para alvos inseguros fora do atalho de limpeza (`src`, `.git`). No PR-04c, eram indevidamente liberados em produção como `FILESYSTEM_SAFE` porque o gate inspecionava o primeiro segmento cru. No PR-04d, a avaliação baseia-se estritamente no `relpath` do caminho normalizado, impedindo a concessão do atalho seguro e aplicando o `deny` de `FILESYSTEM` em produção:

| ID | Comando | Ambiente | Decisão | Use Case | Justificativa |
|---|---|---|---|---|---|
| `CMD-221-dev` | `rm -rf build/../src` | dev | **allow** | FILESYSTEM | [T1] Resolve para `src`; permitido em dev com salvaguarda local de backup. |
| `CMD-221-sta` | `rm -rf build/../src` | staging | **ask** | FILESYSTEM | [T1] Alertas 1/2 e 2/2 mandatórios para exclusão em homologação. |
| `CMD-221-pro` | `rm -rf build/../src` | prod | **deny** | FILESYSTEM | [T1] Bloqueado pelo Production Lock: alvo não é atalho seguro após normalização. |
| `CMD-222-dev` | `rm -rf coverage/../.git` | dev | **allow** | FILESYSTEM | [T1] Resolve para `.git`; liberado sob regra dev condicionado a rollback. |
| `CMD-222-sta` | `rm -rf coverage/../.git` | staging | **ask** | FILESYSTEM | [T1] Alertas 1/2 e 2/2 mandatórios em staging. |
| `CMD-222-pro` | `rm -rf coverage/../.git` | prod | **deny** | FILESYSTEM | [T1] Bloqueado pelo Production Lock: impede destruição do repositório em produção. |

---

## 2. Variantes de Ancestrais Catastróficos (6 novos registros)

Variantes de caminhos absolutos com escape relativo intermediário que resolvem para `/home` (`SYSTEM_ROOTS`) ou `/` (raiz) são canonicamente detectadas como `CATASTROPHIC` em qualquer ambiente:

| ID | Comando | Ambiente | Decisão | Use Case | Justificativa |
|---|---|---|---|---|---|
| `CMD-223-dev` | `rm -rf /home/user/..` | dev | **deny** | CATASTROPHIC | Normaliza para `/home`, pertencente a `SYSTEM_ROOTS`. |
| `CMD-223-sta` | `rm -rf /home/user/..` | staging | **deny** | CATASTROPHIC | Bloqueio incondicional em homologação. |
| `CMD-223-pro` | `rm -rf /home/user/..` | prod | **deny** | CATASTROPHIC | Bloqueio incondicional em produção. |
| `CMD-224-dev` | `rm -rf /usr/local/../..` | dev | **deny** | CATASTROPHIC | Normaliza para `/`, raiz absoluta do sistema de arquivos. |
| `CMD-224-sta` | `rm -rf /usr/local/../..` | staging | **deny** | CATASTROPHIC | Bloqueio incondicional em homologação. |
| `CMD-224-pro` | `rm -rf /usr/local/../..` | prod | **deny** | CATASTROPHIC | Bloqueio incondicional em produção. |
