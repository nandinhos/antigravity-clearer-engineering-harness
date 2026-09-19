---
name: clearer-review
description: >-
  Adversarial diff-centric code review. Analyzes git diffs to uncover bugs, regressions,
  security flaws, and edge case failures, classifying findings by severity (BLOCKER, HIGH, MEDIUM, LOW, INFO).
---

# CLEARER Adversarial Code Review

Esta skill realiza uma revisão técnica minuciosa e adversarial, tendo o Git diff como objeto primordial de inspeção.

> [!IMPORTANT]
> **Postura Adversarial**: O objetivo do revisor é ativamente buscar falhas, quebras de contrato, regressões silenciosas, concorrência desprotegida e edge cases esquecidos.

---

## 1. Obtenção do Diff

Obtenha o diff do repositório:
```bash
git diff HEAD~1..HEAD 2>/dev/null || git diff
```
Ou execute a ferramenta de auditoria:
```bash
bash scripts/diff-audit.sh
```

---

## 2. Bateria de Verificação Atômica (Speculative Fan-out - System One)

Antes de redigir apontamentos descritivos, o revisor DEVE avaliar o diff contra **6 verificações atômicas independentes de espaço fechado** (`[SIM / NÃO]`), com critérios contrastivos:

| # | Checagem Atômica | `what` (SIM) | `not_for` (NÃO) |
|---|---|---|---|
| 1 | `modifies_security_or_auth` | Altera middlewares de auth, tokens, criptografia, sanitização de input, RBAC ou CORS. | Alterações em rotas públicas ou lógica de apresentação sem impacto em credenciais/permissões. |
| 2 | `introduces_destructive_command` | Comandos destrutivos de banco (`migrate:fresh`, `db:wipe`), Git (`reset --hard`, `force push`) ou SO (`rm -rf`). | Comandos atômicos de leitura (`git status`, queries `SELECT`, `git diff`). |
| 3 | `breaks_backward_compatibility` | Altera assinaturas de métodos públicos, remove colunas de banco, muta contratos de payload JSON sem fallback. | Adição de novos métodos/rotas ou extensão aditiva não destrutiva. |
| 4 | `modifies_database_schema` | Cria ou altera migrations, esquemas relacionais, tabelas ou índices. | Consultas ou queries existentes sem alteração estrutural de DDL. |
| 5 | `has_untested_execution_branches` | Introduz novos condicionais (`if`, `switch`, `catch`) sem teste cobrindo o caminho alternativo. | Refatoração estrutural com suíte existente cobrindo 100% dos caminhos. |
| 6 | `violates_minimal_blast_radius` | Toca em arquivos fora do escopo estrito da tarefa, inclui reformatadores cosméticos ou refatores não solicitados. | Alteração cirúrgica restrita aos arquivos essenciais da demanda. |

> [!CRITICAL]
> **Controle em Código**: Se qualquer checagem 1 a 4 retornar **`SIM`**, o Risk Dial do harness é automaticamente promovido para **`HIGH`**, disparando a exigência de testes determinísticos antes de qualquer promoção.

---

## 3. Critérios de Classificação de Achados (Findings)

Classifique cada apontamento em um dos seguintes níveis:

- **`BLOCKER`**: Quebra direta de compilação/execução, falha de segurança crítica (ex: injeção, auth bypass), perda irreversível de dados ou teste quebrado.
- **`HIGH`**: Regressão de funcionalidade existente, quebra de contrato de API pública, vazamento de memória ou race condition em concorrência.
- **`MEDIUM`**: Tratamento inadequado de edge cases (null, empty, timeouts), falta de validação de input ou acoplamento excessivo.
- **`LOW`**: Oportunidade de melhoria de legibilidade, inconsistência menor de estilo ou duplicação pontual.
- **`INFO`**: Observação de design, nota informativa ou recomendação futura fora do escopo.

---

## 4. Formato Estruturado de Cada Finding

Para cada problema identificado, estruture:

```text
### [SEVERIDADE] Título do Problema
- Arquivo: path/to/file.ext:linha
- Problema: Descrição precisa do defeito.
- Impacto: Consequência para o sistema ou usuário.
- Evidência: Linha do diff ou cenário de falha.
- Correção Recomendada: Como corrigir de forma cirúrgica.
```

---

## 5. Checklist de Inspeção Adversarial

- [ ] Há tratamento de `null`, `empty`, `zero` e tipos incorretos?
- [ ] Há risco de SQL injection, XSS, CSRF ou command injection?
- [ ] Contratos de métodos e APIs públicas foram mantidos?
- [ ] Há markers de conflito do Git (`<<<<<<<`, `=======`)?
- [ ] Foram deixados `console.log`, `var_dump`, `print` ou credenciais no código?
- [ ] Os testes cobrem os novos caminhos de execução?
