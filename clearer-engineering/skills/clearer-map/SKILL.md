---
name: clearer-map
description: >-
  Read-only technical codebase mapping. Generates a comprehensive architectural overview
  covering stack, modules, entrypoints, database models, tests, dependencies, and risk hotspots.
---

# CLEARER Codebase Technical Map

Esta skill executa uma análise puramente **read-only** para produzir um mapa arquitetural do repositório.

> [!NOTE]
> **Modo Estritamente Leitura**: Esta skill não modifica arquivos de código.

---

## 1. Coleta de Informações Estruturadas

Execute a ferramenta de detecção de stack:
```bash
bash scripts/detect-project.sh
```

---

## 2. Elementos do Mapa Técnico

Produza o documento cobrindo os tópicos:

1. **Stack & Tooling**:
   - Linguagens e versões identificadas nos manifestos (`package.json`, `composer.json`, `pyproject.toml`, etc.).
   - Frameworks e bibliotecas principais.
   - Ferramentas de teste, formatação e análise estática.

2. **Entrypoints & Rotas**:
   - Pontos de entrada da aplicação (ex: `index.ts`, `server.js`, `public/index.php`, `main.go`, `app/main.py`).
   - Definições de rotas HTTP, comandos CLI ou workers em segundo plano.

3. **Módulos & Arquitetura**:
   - Organização de pastas (Domain, Application, Infrastructure, Controllers, Services, Repositories).
   - Fluxo principal de dados e regras de negócio.

4. **Modelagem de Dados & Persistência**:
   - Schemas, migrations, ORM / modelos de banco de dados.
   - Conexões e dialetos suportados (PostgreSQL, MySQL, SQLite, MongoDB, etc.).

5. **Dependências Críticas & Integrações**:
   - APIs de terceiros, gateways de pagamento, filas (Redis, RabbitMQ, Kafka).

6. **Infraestrutura & Ambientes**:
   - Configurações Docker, Docker Compose, Kubernetes, variáveis de ambiente necessárias.

7. **Matriz de Riscos & Hotspots**:
   - Áreas legadas, baixa cobertura de testes, complexidade ciclomática elevada ou pontos críticos de segurança.
