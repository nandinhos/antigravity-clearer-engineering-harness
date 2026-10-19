---
trigger: always_on
---

# Security Policy & Defensive Engineering

## 1. Security by Default
- Toda entrada de usuário, upload, parâmetro de URL ou consulta de banco deve ser tratada como não confiável.
- Em tarefas envolvendo autenticação, permissões, sessões ou criptografia, a classificação de risco é automaticamente `HIGH`.

## 2. Vetores Críticos de Inspeção
- **Injeções**: SQL Injection (use queries parametrizadas), Command Injection (evite shell strings dinâmicas), XSS (escape de saída).
- **Controle de Acesso**: Validação de autorização no backend (não confiar apenas em proteções de UI).
- **Proteção de Segredos**: Nunca comitar credenciais, chaves de API, senhas ou tokens privados.
- **Permissões de Relatórios e Artefatos Sensíveis**: Relatórios contendo credenciais, varreduras de segurança, auditorias ou inventários de vulnerabilidade exigem permissão restrita explícita pós-escrita (`chmod 0600`), comprovada fisicamente via `stat`; modo ou umask de criação padrão isolado não constitui evidência.
