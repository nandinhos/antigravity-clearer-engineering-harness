# Guia do Safety Gate & Políticas de Proteção por Ambiente

O **Safety Gate** é a barreira ativa de proteção do *CLEARER Engineering Harness (CEH)*. Ele intercepta comandos de shell no estágio `PreToolUse` antes de sua execução real, identificando previamente o ambiente alvo (`DEV`, `HOMOLOGAÇÃO` ou `PRODUÇÃO`) e aplicando **rigores granulares conforme os casos de uso**.

---

## 1. Identificação Prévia de Ambiente (Environment Awareness)

Antes de avaliar qualquer comando destrutivo, o Safety Gate determina o ambiente ativo seguindo uma ordem estrita de precedência:

1. **Parâmetro Explícito**: Flag `--env <development|staging|production>` via CLI.
2. **Contexto no Comando**: Menções explícitas a targets de produção/homologação na linha de comando (`--env=production`, `target=prod`, etc.).
3. **Variáveis de Ambiente**: `CEH_ENV`, `APP_ENV`, `NODE_ENV`, `ENVIRONMENT`, `ENV`, `STAGE`.
4. **Arquivos de Configuração**: `.env.production`, `.env.staging`, `.env.homolog`, `.env.local`, `.env`.
5. **Branch Git Ativa**: Se a branch for `main`, `master` ou `production` sem `.env` local declarando explicitamente dev, o rigor é preventivamente escalado para **PRODUÇÃO**.
6. **Fallback Seguro**: `development`.

---

## 2. Matriz de Rigores Granulares por Caso de Uso

| Caso de Uso | Exemplos de Comandos | Desenvolvimento (`DEV`) | Homologação (`STAGING`) | Produção (`PRODUÇÃO`) |
|---|---|---|---|---|
| **1. Banco de Dados / Migrações** | `migrate:fresh`, `db:wipe`, `DROP DATABASE`, `DROP TABLE`, `TRUNCATE`, `DELETE` sem `WHERE` | **ALLOW** (com aviso de backup/rollback local) | **ASK** (2 Alertas: Impacto HML + Backup/Rollback obrigatórios) | **DENY** (Fora de cogitação) |
| **2. Controle de Versão (Git)** | `git reset --hard`, `git clean -fdx`, `git push --force`, `git branch -D` | **ALLOW** (descarte local liberado para correções/spikes) | **ASK** (2 Alertas: Impacto branch compartilhada + backup de branch) | **DENY** (Bloqueio em branches protegidas: `main`, `prod`) |
| **3. Sistema de Arquivos (Filesystem)** | `rm -rf <dir>`, remoção em massa | **ALLOW** (para pastas do workspace, build, cache, scratch) | **ASK** (2 Alertas: impacto storage compartilhado) | **DENY** (Proibido apagar diretórios fora de temp/logs) |
| **4. Infraestrutura & Nuvem** | `terraform destroy`, `kubectl delete ns`, `docker system prune -a` | **ALLOW** (para containers/volumes locais dev) | **ASK** (2 Alertas: impacto de infraestrutura compartilhada) | **DENY** (Fora de cogitação) |
| **5. Execução Segura (Build/Test)** | `npm test`, `pest`, `phpunit`, `npm run build`, `git status` | **ALLOW** | **ALLOW** | **ALLOW** |
| **6. Catastrófico de Sistema Operacional** | `rm -rf /`, `rm -rf ~`, `mkfs`, fork bombs, `gcloud projects delete` | **DENY** | **DENY** | **DENY** |

---

## 3. Comportamento Detalhado por Nível de Ambiente

### A. Desenvolvimento & Teste (`DEV` / `TEST` / `LOCAL`)
- **Regra**: Destrutivos de desenvolvimento são **PERMITIDOS (`ALLOW`)**.
- **Justificativa**: O desenvolvedor e o agente precisam de agilidade para iterar em schemas, resetar banco local, rodar fixtures de teste e descartar código de spike para correções.
- **Salvaguarda**: O Safety Gate emite aviso de prontidão de backup/rollback prévio para permitir recuperação imediata em caso de erro.
- **Exceção**: Comandos catastróficos de sistema operacional (`rm -rf /`, `mkfs`) mantêm **`DENY`**.

### B. Homologação (`HOMOLOGAÇÃO` / `STAGING` / `UAT`)
- **Regra**: Comandos destrutivos exigem **CONFIRMAÇÃO OBRIGATÓRIA (`ASK`)** com **dois alertas explícitos**:
  - **⚠️ ALERTA 1/2 [IMPACTO DE HOMOLOGAÇÃO]**: Alerta sobre o caso de uso e blast radius no ambiente compartilhado de validação.
  - **⚠️ ALERTA 2/2 [BACKUP & ROLLBACK MANDATÓRIOS]**: Exige comprovação de que o comando de BACKUP prévio foi executado e que a estratégia de ROLLBACK imediato está disponível e testada antes de prosseguir.

### C. Produção (`PRODUÇÃO` / `PROD`)
- **Regra**: Comandos destrutivos estão **FORA DE COGITAÇÃO (`DENY` Absoluto)**.
- **Justificativa**: O agente de IA nunca deve executar operações destrutivas em banco produtivo, force-push em branches principais ou remoção massiva de infraestrutura em ambiente de produção.

---

## 4. Como Funciona a Interceptação

O script [`scripts/safety-gate.py`](file:///home/nandodev/projects/clearer-engineering-harness/clearer-engineering/scripts/safety-gate.py) recebe a chamada da ferramenta em formato JSON via hook `PreToolUse`:

```json
{
  "toolCall": {
    "name": "run_command",
    "args": {
      "CommandLine": "php artisan migrate:fresh"
    }
  }
}
```

E retorna a resposta em JSON auditável consumida nativamente pelo Google Antigravity:

```json
{
  "decision": "ask",
  "reason": "[CEH HOMOLOGAÇÃO / STAGING SAFETY GATE - Caso de Uso: Banco de Dados]\n⚠️ ALERTA 1/2 [IMPACTO DE HOMOLOGAÇÃO]: O comando possui potencial destrutivo/estrutural (Destructive Laravel migration).\n   Ambiente detectado: STAGING (Evidência: Environment variable APP_ENV=staging).\n⚠️ ALERTA 2/2 [BACKUP & ROLLBACK MANDATÓRIOS]: É obrigatório certificar-se de que o comando de BACKUP prévio foi executado e que a estratégia de ROLLBACK imediato está disponível e testada antes de prosseguir.\nConfirma a execução com rollback assegurado?",
  "environment": "staging",
  "use_case": "DATABASE"
}
```
