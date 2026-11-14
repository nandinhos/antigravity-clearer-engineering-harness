---
trigger: always_on
---

# Coding Policy & Staff Engineering Craftsmanship

## 1. Inspect Before Edit & Context Grounding
- Leia os arquivos alvo, chamadores e testes antes de editar; siga os padrões e injeção existentes.
- A única fonte da verdade é o código e schema `OBSERVED`.

## 2. Blast Radius Mínimo & Precisão Cirúrgica
- Limite edições ao escopo da tarefa; proibido reformatar arquivos inteiros ou gerar ruído cosmético.
- Preserve contratos públicos, interfaces, schemas e invariantes de tipos.
- Atalhos temporários exigem `// shortcut: <teto de escala>, <gatilho de refatoração>`; proibido `no-trigger`.

## 3. Tipagem Estrita & Engenharia Defensiva
- Tipagem forte explícita em assinaturas; evite `any`/`mixed`/`dynamic` sem *type narrowing* na borda.
- Trate nulos, listas vazias, timeouts e desconexões com *fail-fast* e mensagens contextuais.
- Isole regras de negócio da persistência/transporte (Clean Architecture / SOLID); recursos externos só conectam no primeiro uso operacional (nunca em import, build ou testes unitários sem I/O).

## 4. Root-Cause First para Bugs
- Nunca mascare sintomas: Sintoma → Reprodução → Observação → Hipótese → Causa Raiz → Teste de Regressão → Correção Mínima.

## 5. Execução Segura de Subprocessos & Inline (`run_command`)
- Proibido `python3 -c`, `php -r` ou `node -e` com `\n` literal (corrompe `permission_grant_store.go`); use one-liners ou `<artifactDir>/scratch/`.
- Proibido varredura global (`find /`, `find ~`, `grep -r /`); imponha timeout $\le 30\text{s}$ com `os.killpg` e use `git_inspect.py` para históricos/diffs extensos.
