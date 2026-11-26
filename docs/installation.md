# Guia Completo de Instalação & Configuração Global

Este documento orienta sobre a instalação do **CLEARER Engineering Harness (CEH)** no **Google Antigravity**, tanto localmente quanto através do instalador global.

---

## 1. Instalação Global Automática (One-Liner)

Para instalar o CEH com um único comando em qualquer máquina com Linux/macOS/WSL:

```bash
curl -fsSL https://raw.githubusercontent.com/nandinhos/antigravity-clearer-engineering-harness/main/install.sh | bash
```

---

## 2. Instalação Manual a Partir do Repositório

### Passo 1: Clonar o Repositório
```bash
git clone https://github.com/nandinhos/antigravity-clearer-engineering-harness.git
cd antigravity-clearer-engineering-harness
```

### Passo 2: Executar o Script de Instalação Local
```bash
chmod +x install.sh
./install.sh
```

O instalador irá:
1. Validar pré-requisitos (`agy`, `python3`, `git`, `bash`).
2. Validar a integridade do plugin com `agy plugin validate` (quando o CLI estiver disponível).
3. Instalar o plugin no Antigravity em `~/.gemini/config/plugins/clearer-engineering` (removendo resíduos legados de cópia duplicada em `~/.gemini/config/agents/clearer-harness/` para respeitar o orçamento de 12 subagentes do Antigravity 2.0).
4. Configurar os aliases canônicos (`ceh`, `agy-ceh`, `agy-ceh-yolo`, `ceh-doctor`, etc.) nos seus arquivos de shell (`~/.bashrc`, `~/.zshrc`, etc.).
5. Executar a suíte de auto-diagnóstico pós-instalação.

---

## 3. Verificação Pós-Instalação & Configuração por Projeto

### Verificar Plugins Ativos e Integridade
```bash
agy plugin list
ceh-doctor --verify
```

### Iniciar uma Sessão

```bash
# Modo padrão (com aprovação interativa de comandos)
agy-ceh
# ou
ceh

# Modo autônomo seguro / YOLO (auto-aprova edições seguras e comandos validados pelo Safety Gate)
agy-ceh-yolo
# ou
agy --dangerously-skip-permissions --mode accept-edits
```

> [!NOTE]
> A partir da `v2.3.1`, as regras (`rules/*.md`), skills, hooks (`hooks.json`) e subagentes (`ceh-*`) são carregados diretamente do plugin `clearer-engineering` no Antigravity 2.0, sem duplicar perfis em `~/.gemini/config/agents/clearer-harness/` e preservando o subagente nativo `browser`.

### Configuração Opcional do Projeto (`.ceh/config.json`)
Para projetos com esteira de CI ou ambiente híbrido host/Docker, crie e versione `.ceh/config.json` na raiz do repositório:

```json
{
  "canonical_test_command": "bash clearer-engineering/tests/run-all-tests.sh",
  "docker_service": "host"
}
```

- `canonical_test_command`: comando integral de testes executado pelo `test-runner.sh` para emissão do Certificado de Voo (`.ceh/last-ci-run.json`).
- `docker_service` *(opcional)*:
  - `"host"` ou `"none"`: força execução no host nativo, pulando sondagens `docker info` / `docker compose ps` mesmo quando há containers ativos no workspace.
  - `"<nome-do-serviço>"`: despacha o comando via `docker compose exec -T <nome-do-serviço>`.
  - Omitido ou `null`: mantém a autodetecção padrão (`laravel.test`, `app`, `web`, `php`, `backend`).

---

## 4. Otimização Opcional de Tokens de Terminal (RTK)

O CEH suporta nativamente o [**RTK (Rust Token Killer)**](https://github.com/rtk-ai/rtk) para reduzir o consumo de tokens de comandos de shell (`run_command`) em até 90%.

### Como Instalar o RTK:
```bash
# Opção A: Homebrew (macOS / Linux)
brew install rtk

# Opção B: Script Oficial One-Liner (Linux / WSL / macOS)
curl -fsSL https://raw.githubusercontent.com/rtk-ai/rtk/refs/heads/master/install.sh | sh

# Opção C: Cargo (Rust)
cargo install --git https://github.com/rtk-ai/rtk
```

### Como o CEH Utiliza o RTK:
- **Detecção Automática**: O instalador (`install.sh`) e o runner de testes (`test-runner.sh`) checam se o comando `rtk` está presente no `$PATH`.
- **Envelopamento Transparente**: Comandos de teste executados via `test-runner.sh` são automaticamente envelopados com `rtk`, preservando o código de saída original.
- **Degradação Graciosa**: Se o RTK não estiver instalado, nenhuma ação é exigida; o harness opera com comandos convencionais sem erros.

---

## 5. Desinstalação

Para remover completamente o harness e seus aliases:

```bash
curl -fsSL https://raw.githubusercontent.com/nandinhos/antigravity-clearer-engineering-harness/main/uninstall.sh | bash
```
Ou executando localmente:
```bash
./uninstall.sh
```

---

## 6. Troubleshooting: Latência ("Working / Generating") & Higiene de Frontmatter

### 6.1. Diagnóstico de Lentidão por Saturação de Pool (`HTTP 503 No Capacity Available`)
Quando servidores upstream retornam `HTTP 503 UNAVAILABLE` para um pool de modelo específico (ex: `gemini-3.8-flash-high` ou `gemini-3.8-flash-medium`), o Antigravity IDE/CLI realiza retentativas com backoff exponencial sem exibir o erro 503 na tela principal. Para diagnosticar instantaneamente:

```bash
grep -iE "503|UNAVAILABLE|capacity|timeout" ~/.gemini/antigravity-cli/log/*.log ~/.antigravity-ide-server/data/logs/*/*/google.antigravity/*.log
```

- **Ação Recomendada**: Alterne imediatamente o seletor de modelo para **`Gemini 4 Argon (Medium)`**, que opera em pool dedicado de baixa latência.

### 6.2. Verificação de Frontmatter YAML em Rules e Skills
O parser interno em Go do Antigravity (`rules.go` e `skills.go`) exige que toda rule em `rules/*.md` comece na linha 1 com `---\ntrigger: always_on\n---` e toda skill em `skills/*/SKILL.md` comece com `---\nname: ...\ndescription: ...\n---`. Execute `ceh-doc-audit` para validar automaticamente a integridade estrutural.
