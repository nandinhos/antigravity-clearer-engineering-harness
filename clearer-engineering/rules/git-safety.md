---
trigger: always_on
---

# Git Safety Policy & Repository Protection

## 1. Proteção de Trabalho Existente
- Antes de iniciar modificações, inspecione o estado com `git status --short` e `git branch --show-current`.
- Nunca reverta alterações não relacionadas ou descarte arquivos modificados pelo desenvolvedor sem autorização expressa.

## 2. Comandos Perigosos e Bloqueios
- **Proibido**: `git reset --hard`, `git clean -fdx`, `git push --force` e comandos destrutivos sem aprovação.
- Sempre revise o diff final com `git diff --stat` e `git diff --check` antes de finalizar uma tarefa.

## 3. Padrão Obrigatório de Mensagens de Commit
- **Idioma**: Exclusivamente **Português do Brasil (pt-BR)** em todos os projetos.
- **Formato da 1ª Linha**: `<prefixo> (<escopo>): <descrição objetiva>` (mínimo 3 palavras, máximo **72 caracteres**; prefixos: `feat`, `fix`, `refactor`, `docs`, `test`, `style`, `perf`, `chore`).
- **Corpo Detalhado**: Incluir descrição detalhada em tópicos (`- ...`) explicando o que foi alterado e o porquê.
- **Estritamente Proibido**: Uso de emojis na mensagem de commit e adição de rodapés de co-autoria ou sessão (`Co-Authored-By`, `Claude-Session` ou similares).
