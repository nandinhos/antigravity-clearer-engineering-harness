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
2. Validar a integridade do plugin com `agy plugin validate`.
3. Instalar o plugin no Antigravity CLI com `agy plugin install`.
4. Registrar o perfil global `clearer-harness` em `~/.gemini/config/agents/clearer-harness/agent.md`.
5. Configurar os aliases `agy-ceh` e `agy-ceh-yolo` nos seus arquivos de shell (`~/.bashrc`, `~/.zshrc`, etc.).
6. Executar a suíte de auto-diagnóstico pós-instalação.

---

## 3. Verificação Pós-Instalação

### Verificar Plugins Ativos
```bash
agy plugin list
```

### Verificar Perfis de Agente
```bash
agy agent
```
Deverá exibir:
```text
Available agents:
bc-harness
clearer-harness
gemini-orchestrator
```

### Iniciar uma Sessão
```bash
# Via alias rápido
agy-ceh

# Ou via comando agy padrão
agy --agent clearer-harness
```

---

## 4. Desinstalação

Para remover completamente o harness e seus aliases:

```bash
curl -fsSL https://raw.githubusercontent.com/nandinhos/antigravity-clearer-engineering-harness/main/uninstall.sh | bash
```
Ou executando localmente:
```bash
./uninstall.sh
```
