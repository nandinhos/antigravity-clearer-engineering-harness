# Evidência de Justificativa de Diff do Golden Corpus (PR-04)

Este documento registra e justifica formalmente cada uma das 39 alterações observadas no Golden Corpus Snapshot (`gate_corpus.expected.jsonl`) após a implementação da análise de `rm` por tokens (`ceh_core/rm.py`), cobrindo os defeitos **G1** (bypass de alvos múltiplos com alvo seguro misto) e **G4** (deleções catastróficas não detectadas).

## Resumo Executivo das Alterações
- Total de avaliações no Golden Corpus: 586
- Decisões idênticas preservadas: 547 (93.3%)
- Decisões alteradas justificadas: 39 (6.7%)
  - **G4 (Catastrophic Deletions & System Roots)**: 33 registros (11 comandos × 3 ambientes)
  - **G1 (Mixed Safe/Unsafe Targets)**: 6 registros (2 comandos × 3 ambientes)
- Comandos `FILESYSTEM_SAFE` de alvo único legítimo alterados: **0** (todos preservados intactos: `dist/`, `tmp/`, `build/`, `scratch/`, etc.)

---

## 1. Defeito G4: Bloqueio Incondicional de Alvos Catastróficos (33 registros)

Alvos catastróficos (`/`, `/*`, `$HOME`, `.`, e diretórios de sistema como `/etc`, `/usr`, `/var`, `/bin`, `/srv`, `/opt`) agora são detectados independentemente do formato das flags (`-r -f`, `--recursive --force`, etc.) e bloqueados com `decision: "deny"`, `use_case: "CATASTROPHIC"` em todos os ambientes (`development`, `staging`, `production`).

| ID | Comando | Ambiente | Antes (Decisão / UC) | Depois (Decisão / UC) | Justificativa |
|---|---|---|---|---|---|
| `CMD-083-dev` | `rm -rf /*` | dev | allow / FILESYSTEM | **deny / CATASTROPHIC** | [G4] Wildcard na raiz bloqueado incondicionalmente em qualquer ambiente. |
| `CMD-083-sta` | `rm -rf /*` | staging | ask / FILESYSTEM | **deny / CATASTROPHIC** | [G4] Não permite ask/bypass em staging para destruição de SO. |
| `CMD-083-pro` | `rm -rf /*` | prod | deny / FILESYSTEM | **deny / CATASTROPHIC** | [G4] Reclassificado como CATASTROPHIC incondicional. |
| `CMD-084-dev` | `rm -r -f /` | dev | allow / FILESYSTEM | **deny / CATASTROPHIC** | [G4] Flags curtas separadas (`-r -f`) sobre raiz agora bloqueadas em dev. |
| `CMD-084-sta` | `rm -r -f /` | staging | ask / FILESYSTEM | **deny / CATASTROPHIC** | [G4] Flags curtas separadas sobre raiz bloqueadas incondicionalmente. |
| `CMD-084-pro` | `rm -r -f /` | prod | deny / FILESYSTEM | **deny / CATASTROPHIC** | [G4] Reclassificado como CATASTROPHIC incondicional. |
| `CMD-085-dev` | `rm --recursive --force /` | dev | allow / GENERAL | **deny / CATASTROPHIC** | [G4] Flags longas `--recursive --force` não caem mais em GENERAL; bloqueio CATASTROPHIC. |
| `CMD-085-sta` | `rm --recursive --force /` | staging | allow / GENERAL | **deny / CATASTROPHIC** | [G4] Bloqueio incondicional em staging. |
| `CMD-085-pro` | `rm --recursive --force /` | prod | allow / GENERAL | **deny / CATASTROPHIC** | [G4] Bypass crítico fechado em produção. |
| `CMD-086-dev` | `rm -rf $HOME` | dev | allow / FILESYSTEM | **deny / CATASTROPHIC** | [G4] `$HOME` bloqueado incondicionalmente em qualquer ambiente. |
| `CMD-086-sta` | `rm -rf $HOME` | staging | ask / FILESYSTEM | **deny / CATASTROPHIC** | [G4] `$HOME` bloqueado incondicionalmente em staging. |
| `CMD-086-pro` | `rm -rf $HOME` | prod | deny / FILESYSTEM | **deny / CATASTROPHIC** | [G4] Reclassificado como CATASTROPHIC incondicional. |
| `CMD-088-dev` | `rm -rf /etc` | dev | allow / FILESYSTEM | **deny / CATASTROPHIC** | [G4] Diretório de sistema `/etc` bloqueado incondicionalmente. |
| `CMD-088-sta` | `rm -rf /etc` | staging | ask / FILESYSTEM | **deny / CATASTROPHIC** | [G4] Diretório de sistema `/etc` bloqueado incondicionalmente. |
| `CMD-088-pro` | `rm -rf /etc` | prod | deny / FILESYSTEM | **deny / CATASTROPHIC** | [G4] Reclassificado como CATASTROPHIC incondicional. |
| `CMD-089-dev` | `rm -rf /usr` | dev | allow / FILESYSTEM | **deny / CATASTROPHIC** | [G4] Diretório de sistema `/usr` bloqueado incondicionalmente. |
| `CMD-089-sta` | `rm -rf /usr` | staging | ask / FILESYSTEM | **deny / CATASTROPHIC** | [G4] Diretório de sistema `/usr` bloqueado incondicionalmente. |
| `CMD-089-pro` | `rm -rf /usr` | prod | deny / FILESYSTEM | **deny / CATASTROPHIC** | [G4] Reclassificado como CATASTROPHIC incondicional. |
| `CMD-090-dev` | `rm -rf /var` | dev | allow / FILESYSTEM | **deny / CATASTROPHIC** | [G4] Diretório de sistema `/var` bloqueado incondicionalmente. |
| `CMD-090-sta` | `rm -rf /var` | staging | ask / FILESYSTEM | **deny / CATASTROPHIC** | [G4] Diretório de sistema `/var` bloqueado incondicionalmente. |
| `CMD-090-pro` | `rm -rf /var` | prod | deny / FILESYSTEM | **deny / CATASTROPHIC** | [G4] Reclassificado como CATASTROPHIC incondicional. |
| `CMD-091-dev` | `rm -rf /bin` | dev | allow / FILESYSTEM | **deny / CATASTROPHIC** | [G4] Diretório de sistema `/bin` bloqueado incondicionalmente. |
| `CMD-091-sta` | `rm -rf /bin` | staging | ask / FILESYSTEM | **deny / CATASTROPHIC** | [G4] Diretório de sistema `/bin` bloqueado incondicionalmente. |
| `CMD-091-pro` | `rm -rf /bin` | prod | deny / FILESYSTEM | **deny / CATASTROPHIC** | [G4] Reclassificado como CATASTROPHIC incondicional. |
| `CMD-092-dev` | `rm -rf .` | dev | allow / FILESYSTEM | **deny / CATASTROPHIC** | [G4] Ponto `.` (diretório atual) bloqueado incondicionalmente. |
| `CMD-092-sta` | `rm -rf .` | staging | ask / FILESYSTEM | **deny / CATASTROPHIC** | [G4] Ponto `.` bloqueado incondicionalmente. |
| `CMD-092-pro` | `rm -rf .` | prod | deny / FILESYSTEM | **deny / CATASTROPHIC** | [G4] Reclassificado como CATASTROPHIC incondicional. |
| `CMD-096-dev` | `rm -rf /srv` | dev | allow / FILESYSTEM | **deny / CATASTROPHIC** | [G4] Diretório de sistema `/srv` bloqueado incondicionalmente. |
| `CMD-096-sta` | `rm -rf /srv` | staging | ask / FILESYSTEM | **deny / CATASTROPHIC** | [G4] Diretório de sistema `/srv` bloqueado incondicionalmente. |
| `CMD-096-pro` | `rm -rf /srv` | prod | deny / FILESYSTEM | **deny / CATASTROPHIC** | [G4] Reclassificado como CATASTROPHIC incondicional. |
| `CMD-097-dev` | `rm -rf /opt` | dev | allow / FILESYSTEM | **deny / CATASTROPHIC** | [G4] Diretório de sistema `/opt` bloqueado incondicionalmente. |
| `CMD-097-sta` | `rm -rf /opt` | staging | ask / FILESYSTEM | **deny / CATASTROPHIC** | [G4] Diretório de sistema `/opt` bloqueado incondicionalmente. |
| `CMD-097-pro` | `rm -rf /opt` | prod | deny / FILESYSTEM | **deny / CATASTROPHIC** | [G4] Reclassificado como CATASTROPHIC incondicional. |

---

## 2. Defeito G1: Fechamento de Bypass por Alvos Múltiplos (6 registros)

Conforme a **Opção A** aprovada (Decisão Q5 do Handoff 013), o atalho de limpeza segura (`FILESYSTEM_SAFE`) exige que **todos** os alvos sejam seguros. Quando um alvo seguro (`build/`, `a.txt`) é misturado com um alvo inseguro (`src/`) ou catastrófico (`/var/lib/postgresql`), o atalho é negado.

| ID | Comando | Ambiente | Antes (Decisão / UC) | Depois (Decisão / UC) | Justificativa |
|---|---|---|---|---|---|
| `CMD-094-dev` | `rm -rf build/ src/` | dev | allow / FILESYSTEM_SAFE | **allow / FILESYSTEM** | [G1] Perdeu o atalho safe porque `src/` não é seguro. Permanece `allow` pelas regras normais de dev para FILESYSTEM. |
| `CMD-094-sta` | `rm -rf build/ src/` | staging | allow / FILESYSTEM_SAFE | **ask / FILESYSTEM** | [G1] Bypass fechado em staging: exige confirmação com alertas de rollback. |
| `CMD-094-pro` | `rm -rf build/ src/` | prod | allow / FILESYSTEM_SAFE | **deny / FILESYSTEM** | [G1] Bypass fechado em produção: `src/` impede liberação acidental na `main`. |
| `CMD-095-dev` | `rm -rf a.txt /var/lib/postgresql` | dev | allow / FILESYSTEM_SAFE | **deny / CATASTROPHIC** | [G1 + G4] Alvo `/var/lib/postgresql` é raiz de sistema/banco. Bloqueio incondicional em dev. |
| `CMD-095-sta` | `rm -rf a.txt /var/lib/postgresql` | staging | allow / FILESYSTEM_SAFE | **deny / CATASTROPHIC** | [G1 + G4] Bloqueio incondicional em staging. |
| `CMD-095-pro` | `rm -rf a.txt /var/lib/postgresql` | prod | allow / FILESYSTEM_SAFE | **deny / CATASTROPHIC** | [G1 + G4] Bloqueio incondicional em produção. |

---

## 3. Preservação Estrita de Limpezas Legítimas (Casos de Controle)

Os seguintes comandos de limpeza segura de alvo único permanecem **100% inalterados**:
- `CMD-067`: `rm -rf dist/` -> `allow` em dev, staging e production (`FILESYSTEM_SAFE`).
- `CMD-068`: `rm -rf tmp/` -> `allow` em dev, staging e production (`FILESYSTEM_SAFE`).
- `CMD-070`: `rm -rf build/` -> `allow` em dev, staging e production (`FILESYSTEM_SAFE`).
- `CMD-072`: `rm -rf scratch/` -> `allow` em dev, staging e production (`FILESYSTEM_SAFE`).
- `CMD-073`: `rm -rf coverage/` -> `allow` em dev, staging e production (`FILESYSTEM_SAFE`).
- `CMD-074`: `rm -rf .tmp/` -> `allow` em dev, staging e production (`FILESYSTEM_SAFE`).
- `CMD-075`: `rm -rf /tmp/` -> `allow` em dev, staging e production (`FILESYSTEM_SAFE`).

E novos controles comportamentais adicionados em `cluster4_acceptance.py`:
- `rm -rf dist/`: Preservado como `allow` em production.
- `rm -rf node_modules/.cache`: Preservado como `allow` em production.
- `rm -f a.txt`: Preservado como `allow` em development.
- `rm -rf ./build`: Preservado como `allow` em production.
