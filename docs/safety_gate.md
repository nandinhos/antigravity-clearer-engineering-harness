# Guia do Safety Gate & Políticas de Proteção

O **Safety Gate** é a barreira ativa de proteção do *CLEARER Engineering Harness*. Ele intercepta comandos de shell no estágio `PreToolUse` antes de sua execução real, garantindo a integridade do sistema de arquivos, do Git e dos bancos de dados.

---

## 1. Hierarquia de Decisão

O Safety Gate opera sob a regra fundamental:

```text
DENY (Bloqueio Total)  >  ASK (Requer Confirmação)  >  ALLOW (Execução Automática)
```

---

## 2. Categorias de Comandos

### A. `DENY` — Bloqueio Incondicional
Comandos com potencial de destruição catastrófica ou irreversível de ambiente:
- `rm -rf /` ou deleção recursiva a partir da raiz.
- `rm -rf ~` ou deleção recursiva da home do usuário.
- `rm -rf ..` ou deleção cega com wildcard `rm -rf *`.
- Formatação de disco (`mkfs`, `dd of=/dev/sd*`).
- Fork bombs e scripts de auto-destruição.
- `DROP DATABASE` / `DROP SCHEMA` em bancos relacionais.
- `gcloud projects delete` ou comandos de deleção de infraestrutura primária em nuvem.

### B. `ASK` — Confirmação Explícita Obrigatória
Comandos que descartam dados, branches ou estado não commitado:
- `rm -rf <diretorio_especifico>` (deleção de diretórios locais).
- `git reset --hard` (descarte de código não salvo).
- `git clean -fdx` (remoção forçada de arquivos não rastreados).
- `git push --force` ou `git push -f` (sobrescrita de histórico remoto).
- `DROP TABLE` e `TRUNCATE TABLE`.
- `DELETE FROM tabela` sem cláusula `WHERE` ou com `WHERE 1=1`.
- `php artisan migrate:fresh` ou `artisan db:wipe`.
- `terraform destroy` ou `kubectl delete namespace`.

### C. `ALLOW` — Execução Automática Permitida
Operações seguras e sem efeito destrutivo:
- Inspeções: `git status`, `git diff`, `git log`, `ls`, `find`, `cat`.
- Test runners: `npm test`, `pest`, `phpunit`, `pytest`, `go test`, `cargo test`.
- Linters & Type Checkers: `eslint`, `phpstan`, `pint`, `ruff`, `mypy`.
- Compilação & Builds locais: `npm run build`, `go build`, `cargo check`.

---

## 3. Como Funciona a Interceptação

O script [`scripts/safety-gate.py`](file:///home/nandodev/projects/clearer-engineering-harness/clearer-engineering/scripts/safety-gate.py) recebe a chamada da ferramenta em formato JSON:

```json
{
  "toolCall": {
    "name": "run_command",
    "args": {
      "CommandLine": "rm -rf /"
    }
  }
}
```

E retorna a resposta em JSON consumida nativamente pelo Antigravity:

```json
{
  "decision": "deny",
  "reason": "[CEH SAFETY BLOCK] Hard block: Attempting recursive deletion of root directory '/'."
}
```
