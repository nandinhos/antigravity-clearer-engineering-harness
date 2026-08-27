# Git Safety Policy & Repository Protection

## 1. Proteção de Trabalho Existente
- Antes de iniciar modificações, inspecione o estado com `git status --short` e `git branch --show-current`.
- Nunca reverta alterações não relacionadas ou descarte arquivos modificados pelo desenvolvedor sem autorização expressa.

## 2. Comandos Perigosos e Bloqueios
- **Proibido**: `git reset --hard`, `git clean -fdx`, `git push --force` e comandos destrutivos sem aprovação.
- Sempre revise o diff final com `git diff --stat` e `git diff --check` antes de finalizar uma tarefa.
