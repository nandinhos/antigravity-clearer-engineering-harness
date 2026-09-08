---
name: learned-lesson
description: >
  Motor agnóstico de extração determinística, estruturação e persistência de lições aprendidas,
  erros superados e boas práticas técnicas. Compatível nativamente com o hub dev-memory
  (MCP/JSON payload) e com operação local para Antigravity, Claude Code, DSH e Hermes.
  Use sempre que resolver um bug complexo, descobrir um comportamento inesperado de ferramenta/stack,
  superar uma falha de ambiente ou consolidar uma regra que deva prevenir erros futuros.
version: 2.0.0
compatibility:
  - dev-memory (Hub MCP / API)
  - Antigravity CLI (agy)
  - DeepSeek Harness (DSH)
  - Claude Code
  - Hermes Agent
---

# Learned Lesson Engine v2.0
### Motor Agnóstico de Memória Técnica & Prevenção de Regressão

Esta skill define o processo determinístico para **extrair, estruturar, padronizar e persistir** lições aprendidas, resoluções de problemas e boas práticas. 
Seu objetivo é transformar atritos superados em ativos permanentes de inteligência, eliminando a reincidência de erros.

---

## 1. Princípios Inegociáveis (RFC 2119 & Ponytail Mode)

1. **Causa Raiz Comprovada (DEVE):** Nenhuma lição pode ser registrada com base em suposição. O problema DEVE ter sido diagnosticado na causa raiz (Gate 3 do Systematic Debugging).
2. **Solução Determinística (DEVE):** A solução registrada DEVE ter sido validada por teste, execução de comando ou compilação bem-sucedida.
3. **Agnosticismo de Plataforma (DEVE):** O formato gerado DEVE ser portável entre qualquer agente ou ferramenta (Antigravity, Claude, DSH, Hermes).
4. **Sem Prolixidade (NÃO DEVE):** Evite narrações longas ou linguagem corporativa vazia. Registre apenas o contexto mínimo suficiente para reproduzir e prevenir o problema.
5. **Invariante Preventivo (DEVE):** Toda lição DEVE conter uma regra de ouro acionável ("Da próxima vez, faça X antes de Y").

---

## 2. Quando Ativar

Ative esta skill diante de qualquer um destes gatilhos:
- Após resolver um bug crítico, intermitente ou não-óbvio (especialmente após o Gate 4 do `systematic-debugging` / `clearer-bugfix`).
- Ao descobrir particularidades ou incompatibilidades de dependências, containers, CLI ou flags.
- Ao identificar uma convenção arquitetural ou boa prática que a equipe/agentes devem respeitar.
- Comandos explícitos: `/lesson`, `aprendizado`, `lição aprendida`, `salvar memória`, `persistir lição`.

---

## 3. Classificação Canônica de Memória

Toda lição pertence estritamente a um dos 3 tipos canônicos (alinhados ao schema `dev-memory`):

| Tipo (`type`) | Quando Utilizar | Exemplo |
|---|---|---|
| **`error`** | Resolução de falha, exceção, crash, deadlock, bug em biblioteca ou conflito de ambiente. | Conflito de portas Docker, erro de sintaxe SQL em versão específica, bug de concorrência. |
| **`lesson`** | Descoberta técnica, atalho de eficiência, comportamento não documentado ou lição operacional. | Otimização de busca AST via Graphify vs Grep, configuração correta de volumes Sail. |
| **`best_practice`** | Padrão arquitetural estabelecido, convenção de código, invariante de segurança ou regra de design. | Tipagem estrita de DTOs, uso de anonymous migrations no Laravel, menor diff funcional. |

---

## 4. O Contrato Canônico de Memória

A estrutura interna de toda lição segue este contrato rigoroso:

### Metadados Obrigatórios:
- **`title`**: Resumo cirúrgico do aprendizado em até 80 caracteres (imperativo ou declarativo).
- **`type`**: `error` | `lesson` | `best_practice`
- **`stack`**: Stack técnica afetada em minúsculas (ex: `laravel`, `php`, `docker`, `gemini`, `python`, `node`, `postgres`).
- **`scope`**: `project` (específico deste repositório) ou `global` (aplicável a qualquer projeto).
- **`official_reference`**: URL de documentação oficial, RFC, issue upstream ou commit que comprove a resolução.

### Estrutura do Conteúdo (`description`):
```markdown
### 1. Sintoma / Contexto
[Descrição objetiva do erro, comando executado ou situação observada]

### 2. Causa Raiz
[O mecanismo real que gerou a falha — o PORQUÊ aconteceu, não o sintoma]

### 3. Solução Canônica
[Comando exato, diff mínimo ou configuração que corrigiu o problema de forma definitiva]

### 4. Regra de Prevenção (Invariante)
[Diretriz prática para nunca mais cair no mesmo problema]
```

---

## 5. Modos de Saída e Persistência

A skill opera em dois modos, com transição transparente:

### Modo A: Conectado ao `dev-memory` (Hub MCP / API)
Se as ferramentas do `dev-memory` estiverem disponíveis na sessão (`mcp__dev-memory__memory_create` ou comando de API):

Dispare a chamada com o payload JSON canônico:
```json
{
  "title": "[Título Conciso da Lição]",
  "type": "error|lesson|best_practice",
  "stack": "laravel|docker|gemini|...",
  "scope": "project|global",
  "official_reference": "https://...",
  "description": "### 1. Sintoma / Contexto\n...\n\n### 2. Causa Raiz\n...\n\n### 3. Solução Canônica\n...\n\n### 4. Regra de Prevenção\n..."
}
```

### Modo B: Operação Local / Offline (Sem Hub Ativo)
Se o MCP remoto não estiver ativo no momento:
1. Exiba o bloco canônico formatado em Markdown na resposta para conferência do usuário.
2. Persista o aprendizado no arquivo local do repositório em `.agents/rules/` ou `.dev-memory/learned-lessons.jsonl`.

---

## 6. Checklist de Qualidade (Definição de Pronto)

Antes de considerar a lição concluída, valide internamente:
- [ ] O título descreve a solução ou o aprendizado, e não apenas o problema?
- [ ] A causa raiz foi isolada sem "achismos"?
- [ ] A solução apresenta código/comando real e testado?
- [ ] A regra de prevenção é direta e acionável?
- [ ] O payload JSON gerado é 100% válido contra o schema do `dev-memory`?
