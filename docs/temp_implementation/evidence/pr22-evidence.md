# PR-22 — Evidência de Implementação e Verificação (`OBSERVED`)

**Data/Hora:** 2026-09-27T21:17:30-03:00  
**PR:** PR-22 (`feat(gate): cobertura de regras de dados e infraestrutura (AT3) e leituras de .ceh (AM2)`)  
**Branch:** `claude/code-review-technical-analysis-kfwcdl`  
**Linha de Base Homologada:** `d6bf922` (Handoff 047)  
**Status da Suíte Canônica Local:** **59/59 testes aprovados (100% PASS)**  
**Certificado de CI:** Emitido em `.ceh/last-ci-run.json`  

---

## 1. Escopo e Objetivos do PR-22

Conforme despachado no [Handoff 047](../handoffs/handoff-047-revisao-pr18b-despacho-pr22.md), o PR-22 fecha as seguintes lacunas:
1. **AT3 (Dados e Infraestrutura):** Interceptação graduada (DEV allow / HML ask / PROD deny) de comandos destrutivos de:
   - Git Stash: `git stash clear`, `git stash drop`;
   - Docker Volumes & Compose: `docker volume rm`, `docker volume prune`, `docker compose down -v` (e `--volumes`);
   - Redis: `redis-cli flushall`, `redis-cli flushdb` (case-insensitive, com flags anteriores como `-h db`);
   - Prisma: `prisma migrate reset` (inclusive com `--force`);
   - Sistema de Arquivos via `dd`: sobrescrita de arquivo comum via `dd if=... of=<arquivo>`, mantendo escrita direta em disco cru (`of=/dev/sda`, `of=/dev/nvme*`) como incondicionalmente `CATASTROPHIC`.
2. **AM2 (Integridade de `.ceh` e Relaxamentos Conscientes):**
   - Permitir leituras puras sem redirecionamento (`du -sh .ceh`, `diff .ceh/...`, `git status|log|diff|show .ceh`);
   - Desconsiderar argumentos de exclusão benignos (`--exclude=.ceh`, `--exclude .ceh`, `-path ./.ceh -prune`), evitando que `.ceh` seja erroneamente considerado alvo de adulteração;
   - Manter bloqueio incondicional (`DENY`) contra tentativas reais de escrita (`tar xf evil.tar -C .ceh`, `rsync .ceh/`, `cp -r .ceh`, `diff > .ceh/...`, `find .ceh -delete`).
3. **Decisão sobre `php artisan migrate --force`:**
   - **Decisão:** Mantido como `ALLOW` em produção (`GENERAL`).
   - **Justificativa Técnica:** `php artisan migrate --force` é o comando canônico padrão executado por pipelines de deploy do Laravel para aplicar novas migrações incrementais de forma não interativa. Diferente de `migrate:fresh`, `migrate:reset` e `db:wipe` (que destroem schemas e tabelas existentes e já são bloqueados pelo gate), o `migrate --force` é idempotente e operacionalmente necessário em deploys normais de produção.

---

## 2. Matriz de Decisões (`OBSERVED`)

| Grupo | Comando | Decisão Anterior (`d6bf922`) | Nova Decisão (PR-22) | Caso de Uso |
|---|---|---|---|---|
| **AT3** | `git stash clear` | `allow` | `deny` (prod) / `ask` (hml) / `allow` (dev) | `GIT_HISTORY` |
| **AT3** | `git stash drop` | `allow` | `deny` (prod) / `ask` (hml) / `allow` (dev) | `GIT_HISTORY` |
| **AT3** | `docker volume rm data` | `allow` | `deny` (prod) / `ask` (hml) / `allow` (dev) | `INFRASTRUCTURE` |
| **AT3** | `docker volume prune -f` | `allow` | `deny` (prod) / `ask` (hml) / `allow` (dev) | `INFRASTRUCTURE` |
| **AT3** | `docker compose down -v` | `allow` | `deny` (prod) / `ask` (hml) / `allow` (dev) | `INFRASTRUCTURE` |
| **AT3** | `redis-cli flushall` | `allow` | `deny` (prod) / `ask` (hml) / `allow` (dev) | `DATABASE` |
| **AT3** | `redis-cli -h db FLUSHDB` | `allow` | `deny` (prod) / `ask` (hml) / `allow` (dev) | `DATABASE` |
| **AT3** | `prisma migrate reset --force` | `allow` | `deny` (prod) / `ask` (hml) / `allow` (dev) | `DATABASE` |
| **AT3** | `dd if=/dev/zero of=app.db` | `allow` | `deny` (prod) / `ask` (hml) / `allow` (dev) | `FILESYSTEM` |
| **Controle** | `dd if=x of=/dev/sda` | `deny/CATASTROPHIC` | `deny/CATASTROPHIC` (todos os envs) | `CATASTROPHIC` |
| **Controle** | `git stash list` | `allow` | `allow` | `GENERAL` |
| **Controle** | `docker volume ls` | `allow` | `allow` | `GENERAL` |
| **Controle** | `docker compose down` (sem -v) | `allow` | `allow` | `GENERAL` |
| **Controle** | `redis-cli ping` | `allow` | `allow` | `GENERAL` |
| **AM2** | `find . -path ./.ceh -prune -o -name '*.py' -print` | `deny` | `allow` (todos os envs) | `GENERAL` |
| **AM2** | `tar czf out.tgz --exclude=.ceh .` | `deny` | `allow` (todos os envs) | `GENERAL` |
| **AM2** | `du -sh .ceh` | `deny` | `allow` (todos os envs) | `GENERAL` |
| **AM2** | `diff .ceh/last-ci-run.json /tmp/x` | `deny` | `allow` (todos os envs) | `GENERAL` |
| **AM2** | `git status --ignored .ceh` | `deny` | `allow` (todos os envs) | `GENERAL` |
| **Controle AM2** | `tar xf evil.tar -C .ceh` | `deny` | `deny` (todos os envs) | `CERTIFICATE_INTEGRITY` |
| **Controle AM2** | `rsync -a /tmp/fake/ .ceh/` | `deny` | `deny` (todos os envs) | `CERTIFICATE_INTEGRITY` |
| **Controle AM2** | `cp -r /tmp/fakeceh/. .ceh` | `deny` | `deny` (todos os envs) | `CERTIFICATE_INTEGRITY` |
| **Controle AM2** | `diff a b > .ceh/last-ci-run.json` | `deny` | `deny` (todos os envs) | `CERTIFICATE_INTEGRITY` |
| **Controle AM2** | `find .ceh -delete` | `deny` | `deny` (todos os envs) | `CERTIFICATE_INTEGRITY` |

---

## 3. Saída das Redes Diferenciais (`OBSERVED`)

### 3.1 `test_gate_differential_fuzz.py` (Fuzz Diferencial contra Baseline `d6bf922`)
- **Total de Comandos Avaliados:** 4.029 comandos únicos avaliados nos 3 ambientes (`development`, `staging`, `production`), totalizando **12.087 casos**.
- **Resultado:** 4/4 testes aprovados (`OK`), 20.82s.
- **Relaxamentos Detectados:** Exatamente os 15 relaxamentos autorizados em `relaxamentos_justificados.txt` com ID `H039-AM2` (5 comandos em 3 ambientes).
- **Relaxamentos Não Autorizados:** **0 (zero)**.

### 3.2 `test_environment_differential.py` (Rede Diferencial de Detecção sem `explicit_env`)
- **Total de Casos Avaliados:** 4 branches (`dev`, `release/qa-1`, `main`, `feature/evaluation`).
- **Resultado:** 1/1 teste aprovado (`OK`), 1.63s.
- **Relaxamentos Detectados:** Exatamente os 20 relaxamentos autorizados em `relaxamentos_deteccao.txt` com ID `H039-AM2` (5 comandos nas 4 branches).
- **Relaxamentos Não Autorizados:** **0 (zero)**.

---

## 4. Provas de Falsificabilidade por Mutação em Clone Isolado (`/tmp`)

Ambas as provas foram executadas exclusivamente em clones temporários criados em `/tmp`, mantendo a árvore de trabalho principal limpa e imutável.

### Prova 1: Mutação da Regra de `redis-cli` (AT3)
- **Procedimento:** Clonagem em `/tmp/ceh-mut-redis-XXXXXX` e remoção da regra `redis-cli` de `ceh_core/rules.py`.
- **Resultado `OBSERVED`:**
  - `test_rules_data_infra.py` FALHOU (`exit code: 1`):
    - `test_redis_cli_flush_graduation_and_case_insensitivity`: falha de use_case (`GENERAL != DATABASE`).
    - `test_composition_pipelines`: falha de decisão (`allow != ask` em staging para `ls && redis-cli flushall`).
  - `test_review_batteries.py` FALHOU (`exit code: 1`):
    - `linha 425 [H046-AT3] production: esperado deny, obtido allow/GENERAL — redis-cli flushall`
    - `linha 436 [H047-AT3] production: esperado deny, obtido allow/GENERAL — redis-cli -h db FLUSHDB`
- **Veredito:** Falsificabilidade comprovada para AT3.

### Prova 2: Mutação da Regra de `du` na Proteção de `.ceh` (AM2)
- **Procedimento:** Clonagem em `/tmp/ceh-mut-du-XXXXXX` e remoção do comando `"du"` de `ALLOWED_READ_CMDS` em `ceh_core/rules.py`.
- **Resultado `OBSERVED`:**
  - `test_rules_data_infra.py` FALHOU (`exit code: 1`):
    - `test_am2_allowed_reads_and_exclusions`: falha de decisão (`deny != allow` para `du -sh .ceh`).
  - `test_review_batteries.py` FALHOU (`exit code: 1`):
    - `linha 446 [H039-AM2] production: esperado allow, obtido deny/CERTIFICATE_INTEGRITY — du -sh .ceh`
- **Veredito:** Falsificabilidade comprovada para AM2.

---

## 5. Auditoria Documental e Orçamento de Código (`doc-audit.sh`)

Resultado da execução direta de `bash clearer-engineering/scripts/doc-audit.sh`:
```text
=== [CEH Bounded Document Structure Audit] ===
Repositório: .../clearer-engineering-harness
Alvo principal: docs/plano-validacao-revisao-conselho-seniors.md
--------------------------------------------------
[1/7] Verificando taxonomia de estados permitidos...
  • Estados permitidos normativos identificados: ['Inconclusivo', 'Inspeção estática', 'Pendente', 'Refutado', 'Reproduzido', 'Reproduzido e corrigido']
[2/7] Verificando consistência da tabela de achados (R1 a R10)...
  • Todos os 10 achados (R1 a R10) possuem estados normativos válidos e consistentes com o claim global.
[3/7] Verificando existência física de arquivos de evidência citados...
  • Todos os 20 links de evidências apontam para arquivos físicos existentes.
[4/7] Verificando portabilidade de links e ausência de session IDs na documentação...
  • Zero caminhos absolutos locais ou session IDs recentes detectados em docs/.
[5/7] Verificando existência de commits citados no Git local...
  • Todos os commits citados (1c9a0d2, bb61fe7, 8fbb318, b7df47d) foram confirmados no Git local.
[6/7] Verificando consistência em handoffs...
  • Handoffs devidamente sincronizados com as autorizações e commits consolidados.
[7/7] Verificando orçamento de linhas dos componentes core...
  • safety-gate.py: 624 linhas (Teto: 650)
  • test-runner.sh: 188 linhas (Teto: 200)
  • ceh_core/environment.py: 281 linhas (Teto: 300)
  • ceh_core/find.py: 200 linhas (Teto: 300)
  • ceh_core/git.py: 294 linhas (Teto: 300)
  • ceh_core/interpreters.py: 254 linhas (Teto: 300)
  • ceh_core/interpreters_extra.py: 263 linhas (Teto: 300)
  • ceh_core/lexer.py: 297 linhas (Teto: 300)
  • ceh_core/push.py: 273 linhas (Teto: 300)
  • ceh_core/rm.py: 233 linhas (Teto: 300)
  • ceh_core/rules.py: 172 linhas (Teto: 300)
--------------------------------------------------
SUCESSO: 7/7 checagens estruturais documentais passaram.
```

---

## 6. Resultado da Suíte Canônica Completa (59/59 PASS)

A suíte geral foi executada via `test-runner.sh`, gerando o certificado assinado:
- **Total de Testes:** 59
- **Aprovados:** 59 (100%)
- **Falhas:** 0
- **Exit Code:** 0
