# Security Policy & Defensive Engineering

## 1. Security by Default
- Toda entrada de usuário, upload, parâmetro de URL ou consulta de banco deve ser tratada como não confiável.
- Em tarefas envolvendo autenticação, permissões, sessões ou criptografia, a classificação de risco é automaticamente `HIGH`.

## 2. Vetores Críticos de Inspeção
- **Injeções**: SQL Injection (use queries parametrizadas), Command Injection (evite shell strings dinâmicas), XSS (escape de saída).
- **Controle de Acesso**: Validação de autorização no backend (não confiar apenas em proteções de UI).
- **Proteção de Segredos**: Nunca comitar credenciais, chaves de API, senhas ou tokens privados.
