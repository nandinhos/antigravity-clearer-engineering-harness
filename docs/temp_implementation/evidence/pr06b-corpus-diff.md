# Justificativa Linha a Linha do Diff do Corpus (PR-06 / PR-06b)

**Data:** 2026-09-26  
**Referência:** Handoff 025 (AA4)  
**Arquivo auditado:** `clearer-engineering/tests/fixtures/gate_corpus.expected.jsonl`  
**Linha de Base:** `2820dad`  
**Total de alterações:** 15 decisões (todas constituem **apertos de segurança**, 0 relaxamentos).

---

## Tabela Consolidada de Decisões Alteradas

| ID | Comando | Ambiente | De (`2820dad`) | Para (`PR-06b`) | Natureza | Justificativa Técnica (RFC 2119 / CEH G5) |
|---|---|---|---|---|---|---|
| `CMD-098-dev` | `find / -delete` | development | allow (GENERAL) | **deny (CATASTROPHIC)** | Aperto | Deleção direta da raiz do sistema operacional (`/`). G5 proíbe incondicionalmente em qualquer ambiente. |
| `CMD-098-sta` | `find / -delete` | staging | allow (GENERAL) | **deny (CATASTROPHIC)** | Aperto | Deleção direta da raiz do sistema operacional (`/`). G5 proíbe incondicionalmente em qualquer ambiente. |
| `CMD-098-pro` | `find / -delete` | production | allow (GENERAL) | **deny (CATASTROPHIC)** | Aperto | Deleção direta da raiz do sistema operacional (`/`). G5 proíbe incondicionalmente em qualquer ambiente. |
| `CMD-099-dev` | `find . -name x -exec rm {} +` | development | allow (GENERAL) | **allow (FILESYSTEM)** | Aperto | Remoção de arquivos via `-exec rm`. Enquadrado como caso de uso `FILESYSTEM` (liberado em DEV com salvaguarda). |
| `CMD-099-sta` | `find . -name x -exec rm {} +` | staging | allow (GENERAL) | **ask (FILESYSTEM)** | Aperto | Remoção em homologação exige confirmação de 2 etapas (Alerta 1: Impacto HML; Alerta 2: Backup & Rollback). |
| `CMD-099-pro` | `find . -name x -exec rm {} +` | production | allow (GENERAL) | **deny (FILESYSTEM)** | Aperto | Remoção de arquivos em produção é terminantemente proibida (`DENY`). |
| `CMD-100-dev` | `find /var -type f -delete` | development | allow (GENERAL) | **deny (CATASTROPHIC)** | Aperto | `/var` pertence a `SYSTEM_ROOTS`. Deleção incondicional em diretório de sistema é CATASTROPHIC. |
| `CMD-100-sta` | `find /var -type f -delete` | staging | allow (GENERAL) | **deny (CATASTROPHIC)** | Aperto | `/var` pertence a `SYSTEM_ROOTS`. Deleção incondicional em diretório de sistema é CATASTROPHIC. |
| `CMD-100-pro` | `find /var -type f -delete` | production | allow (GENERAL) | **deny (CATASTROPHIC)** | Aperto | `/var` pertence a `SYSTEM_ROOTS`. Deleção incondicional em diretório de sistema é CATASTROPHIC. |
| `CMD-101-dev` | `python3 -c "import shutil; shutil.rmtree(\"/srv\")"` | development | allow (GENERAL) | **deny (CATASTROPHIC)** | Aperto | `/srv` pertence a `SYSTEM_ROOTS`. Destruição recursiva de raiz de sistema via interpretador inline é CATASTROPHIC. |
| `CMD-101-sta` | `python3 -c "import shutil; shutil.rmtree(\"/srv\")"` | staging | allow (GENERAL) | **deny (CATASTROPHIC)** | Aperto | `/srv` pertence a `SYSTEM_ROOTS`. Destruição recursiva de raiz de sistema via interpretador inline é CATASTROPHIC. |
| `CMD-101-pro` | `python3 -c "import shutil; shutil.rmtree(\"/srv\")"` | production | allow (GENERAL) | **deny (CATASTROPHIC)** | Aperto | `/srv` pertence a `SYSTEM_ROOTS`. Destruição recursiva de raiz de sistema via interpretador inline é CATASTROPHIC. |
| `CMD-102-dev` | `python3 -c "import os; os.remove(\"/etc/passwd\")"` | development | allow (GENERAL) | **allow (FILESYSTEM)** | Aperto | Remoção de arquivo individual sensível. Enquadrado como caso de uso `FILESYSTEM` (permitido em DEV). |
| `CMD-102-sta` | `python3 -c "import os; os.remove(\"/etc/passwd\")"` | staging | allow (GENERAL) | **ask (FILESYSTEM)** | Aperto | Remoção de arquivo sensível em homologação exige confirmação em 2 etapas. |
| `CMD-102-pro` | `python3 -c "import os; os.remove(\"/etc/passwd\")"` | production | allow (GENERAL) | **deny (FILESYSTEM)** | Aperto | Remoção de arquivo em produção é estritamente proibida (`DENY`). |

---

## Auditoria de Conformidade
- **Relaxamentos introduzidos:** 0 (zero).
- **Linhas adicionadas a `relaxamentos_justificados.txt`:** 0 (nenhuma).
- **Compatibilidade:** O teste diferencial hermético (`test_gate_differential_fuzz.py`) valida as 11.787 combinações e confirma 0 relaxamentos não autorizados contra `2820dad`.
