# ADR 005: Desacoplamento entre Estratégia de CI e Runtime Local (Host Nativo vs. Docker/Sail)

## Status
**APROVADO** (Implementado na branch `dev-runtime-ci-adapter`)

---

## Contexto & Problema

Com a introdução da **Governança de CI Mandatória (ADR 004)**, o CLEARER Engineering Harness exige a execução integral da suíte canônica de testes do projeto antes de qualquer `git push`.

Entretanto, observou-se uma assimetria física comum nos projetos de software reais:
1. **Ambiente de CI (GitHub Actions / GitLab CI)**:
   - Frequentemente roda em **Runners de VM nativos** (`runs-on: ubuntu-latest`) utilizando ferramentas como `setup-php` ou `setup-node` e declarando serviços de banco/cache via `services: postgres, redis`.
   - O comando executado no step é nativo (ex: `vendor/bin/pest` ou `php artisan test`).
2. **Ambiente Local do Desenvolvedor / Agente**:
   - Pode ser **Host Nativo**: Desenvolvedor possui PHP/Node/Python instalado diretamente na máquina e roda comandos locais sem Docker.
   - Pode ser **Dockerizado (Laravel Sail / Docker Compose)**: O projeto possui serviços e interpretadores isolados dentro de containers (`docker compose exec -T laravel.test ...` ou `./vendor/bin/sail test`).
   - Pode estar com **Containers Parados**: O repositório tem `docker-compose.yml`, mas o Docker daemon não está rodando ou os containers estão desligados.

### O Risco de Engenharia:
Se o agente ou o runner assumir cegamente que deve rodar via Docker (porque encontrou um `docker-compose.yml`), mas o Docker não estiver ativo no host, os testes quebram por falha de infraestrutura. Similarmente, se o projeto rodar exclusivamente em Docker ativo e o comando for disparado no host sem as extensões ou banco necessários, ocorre falha indevida.

---

## Decisão Arquitetural

Adotamos a **Identificação de Runtime com Despacho Inteligente e Degradação Graciosa**:

### 1. Auditoria de Runtime no `detect-project.sh`
O detector de projetos passa a inspecionar 4 dimensões determinísticas:
- **Disponibilidade do Daemon**: Verifica se `docker` está instalado e se o daemon responde (`docker info`).
- **Estado dos Containers**: Consulta `docker compose ps --services --filter "status=running"` para identificar se os serviços do projeto estão rodando.
- **Contexto de Execução**: Detecta se o próprio agente já está dentro de um container Docker (`/.dockerenv`).
- **Classificação de Runtime Mode**:
  - **`NATIVE_HOST`**: Host nativo puro sem Docker local.
  - **`DOCKER_ACTIVE`**: Containers do projeto em execução.
  - **`DOCKER_STOPPED`**: Docker Compose presente, mas containers desligados.
  - **`IN_CONTAINER`**: Execução direta dentro de container.

### 2. Mapeamento de Estratégia de CI
O `detect-project.sh` analisa os workflows em `.github/workflows/*.yml` para extrair:
- Tipo de Runner (`GitHub Actions Runner`).
- Serviços auxiliares necessários (`postgres`, `mysql`, `redis`).
- Steps canônicos de teste (`pest`, `phpunit`, `npm test`, `pytest`).
- Recomendação explícita de **Local Execution Bridge**.

### 3. Adaptador Inteligente no `test-runner.sh`
Ao receber ou auto-detectar um comando canônico (ex: `vendor/bin/pest` ou `php artisan test`):
- **Se `DOCKER_ACTIVE`**: O runner detecta que os containers (`laravel.test` ou `app`) estão ativos e despacha o comando automaticamente para dentro do container (`docker compose exec -T <service> <cmd>` ou `./vendor/bin/sail test`), sem exigir que o desenvolvedor redija o prefixo.
- **Se `NATIVE_HOST`**: Executa diretamente no host via binários locais sem falhar nem tentar invocar Docker.
- **Se `DOCKER_STOPPED`**: Emite aviso informativo de que os containers estão desligados e executa no host nativo se os binários locais existirem, ou instrui `docker compose up -d`.

---

## Consequências e Princípio Ponytail (Zero Overengineering)

- **Zero Dependências Novas**: A solução opera exclusivamente via `bash`, `docker info` (com timeout seguro) e inspeção estática de arquivos.
- **Fim dos Falsos Positivos de Infraestrutura**: O agente não quebra testes legítimos tentando adivinhar onde eles devem rodar.
- **Compatibilidade Bidirecional**: Projetos com Docker Sail e projetos puramente nativos coexistem sob a mesma governança estrita de CI.
