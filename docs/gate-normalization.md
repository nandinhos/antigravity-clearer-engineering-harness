# Contrato de Normalização do Safety Gate (H2 / D4)

Este documento estabelece o contrato normativo e as garantias determinísticas de **normalização léxica, casefold e resolução de caminhos** aplicadas pelo Safety Gate do CLEARER Engineering Harness (CEH).

---

## 1. Princípio Fundamental de Normalização

A normalização léxica do CEH tem como objetivo prevenir bypasses de segurança causados por variações sintáticas triviais (ex: maiúsculas no executável, barras duplicadas ou aliases de sistema de arquivos), **sem nunca alterar o significado semântico dos argumentos de linha de comando**.

---

## 2. Casefold Restrito (D4 / Handoff 090)

### 2.1 O Risco da Caixa Baixa Incondicional (`lower()` Global)
Uma abordagem ingênua de converter todo o comando para minúsculas (`cmd.lower()`) introduz afrouxamentos graves de segurança. 
A medição empírica realizada sobre o corpus dourado de decisões do CEH (331 comandos avaliados em DEV, STAGING e PRODUÇÃO) comprovou que `cmd.lower()` incondicional alteraria 23 decisões, **afrouxando 16 regras críticas de segurança**:

| Comando | Ambiente | Comportamento CEH | Com `lower()` Global | Impacto de Segurança |
|---|---|---|---|---|
| `rm -rf $HOME` | development | **deny** (catastrófico) | **ask** | ✖ Afrouxamento: variável perde valor no parser |
| `rm -rf $PWD` | staging | **deny** (catastrófico) | **ask** | ✖ Afrouxamento: variável perde valor no parser |
| `git checkout -B main` | production | **deny** (branch protegida) | **allow** | ✖ Afrouxamento grave: `-B` vira `-b` |
| `git switch -C main` | production | **deny** (branch protegida) | **allow** | ✖ Afrouxamento grave: `-C` vira `-c` |
| `git restore -W -S .` | production | **deny** | **allow** | ✖ Afrouxamento: flags de working-tree perdem semântica |
| `git -C sub status` | production | **allow** | **deny** | ✖ Falso positivo: `-C` vira `-c` de configuração |

No shell e no Git, variáveis de ambiente (`$HOME`), switches de opção (`-B` ≠ `-b`, `-C` ≠ `-c`) e nomes de branches diferenciam rigorosamente maiúsculas de minúsculas.

### 2.2 Os Dois Pontos Canônicos de Aplicação do Casefold
O casefold é restrito estritamente a dois pontos onde a tolerância à caixa não causa colisão semântica:

1. **No basename do executável (`argv[0]`)**:
   - Após a remoção do caminho de diretório (`os.path.basename`), o identificador da ferramenta é normalizado para minúsculas:
     - `GIT`, `Git`, `/usr/bin/GIT` ➔ `git`
     - `RM`, `Rm`, `/bin/RM` ➔ `rm`
     - `FIND`, `Find` ➔ `find`
     - `PYTHON`, `Python3`, `NODE`, `Node` ➔ interpretadores reconhecidos
   - Os argumentos e opções subsequentes do comando permanecem **rigorosamente intactos**.

2. **No componente `.ceh` em alvos de escrita e redirecionamento**:
   - Em operações que afetam arquivos internos do harness, os componentes de caminho `.CEH/`, `.Ceh/` ou `.ceh/` são tratados de forma insensível à caixa:
     - `> .CEH/config.json` ➔ interceptado como tentativa de mutação de integridade.

---

## 3. Resolução Canônica de Caminhos

1. **Symlinks e Ancestrais Reais**:
   - Caminhos de diretório e repositório são inspecionados com resolução canônica física (`Path.resolve()` / `os.path.realpath`).
   - Garante que atalhos e symlinks de sistema operacional (como o alias `/var` ➔ `/private/var` no macOS) não mascarem a identidade do repositório ou o pertencimento a `.ceh/`.
2. **Normalização de Pontos e Barras**:
   - Sequências como `.` e `..` são colapsadas para evitar evasões de diretório (`path/../.ceh`).
   - Múltiplas barras consecutivas (`//`) são reduzidas a uma única barra canônica.
3. **Isolamento de Ambiente em Árvore Fisiológica (D04)**:
   - A detecção de ambiente inspeciona a árvore ancestral física resolvida do diretório de destino, garantindo que symlinks apontando para fora do workspace mantenham as salvaguardas adequadas.

---

## 4. Normalização de Redirecionamentos e Destinos de Escrita

O Safety Gate monitora operadores de redirecionamento de shell para proteger artefatos de integridade:
- **Operadores Monitorados**: `>`, `>>`, `>|`, `&>`, `&>>`, `N>`, `N>>`, `<>` (unidos ao alvo ou separados por espaço).
- **Exclusão de Descritores de Arquivo Puros**:
  - Construções como `2>&1` ou `>&2` são duplicações de file descriptor e não alvos em disco, sendo categorizadas adequadamente sem falsos positivos.
- **Comandos com Destino Explícito**:
  - `tee`, `dd of=...`, `cp ... dest`, `mv ... dest`, `install ... dest` e `ln -s ... dest` são avaliados contra destinos protegidos (`.ceh/`).
