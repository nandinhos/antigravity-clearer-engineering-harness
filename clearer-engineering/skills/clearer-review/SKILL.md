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

## 2. Critérios de Classificação de Achados (Findings)

Classifique cada apontamento em um dos seguintes níveis:

- **`BLOCKER`**: Quebra direta de compilação/execução, falha de segurança crítica (ex: injeção, auth bypass), perda irreversível de dados ou teste quebrado.
- **`HIGH`**: Regressão de funcionalidade existente, quebra de contrato de API pública, vazamento de memória ou race condition em concorrência.
- **`MEDIUM`**: Tratamento inadequado de edge cases (null, empty, timeouts), falta de validação de input ou acoplamento excessivo.
- **`LOW`**: Oportunidade de melhoria de legibilidade, inconsistência menor de estilo ou duplicação pontual.
- **`INFO`**: Observação de design, nota informativa ou recomendação futura fora do escopo.

---

## 3. Formato Estruturado de Cada Finding

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

## 4. Checklist de Inspeção Adversarial

- [ ] Há tratamento de `null`, `empty`, `zero` e tipos incorretos?
- [ ] Há risco de SQL injection, XSS, CSRF ou command injection?
- [ ] Contratos de métodos e APIs públicas foram mantidos?
- [ ] Há markers de conflito do Git (`<<<<<<<`, `=======`)?
- [ ] Foram deixados `console.log`, `var_dump`, `print` ou credenciais no código?
- [ ] Os testes cobrem os novos caminhos de execução?
