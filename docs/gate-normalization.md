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

### 2.2 Os Pontos Canônicos de Aplicação do Casefold

1. **No basename do executável (`argv[0]`) — Vigente (PR #9)**:
   - Após a remoção do caminho de diretório (`os.path.basename`), o identificador da ferramenta é normalizado para minúsculas:
     - `GIT`, `Git`, `/usr/bin/GIT`, `GIT -C .` ➔ `git`
     - `RM`, `Rm`, `/bin/RM` ➔ `rm`
     - `FIND`, `Find` ➔ `find`
     - `PYTHON`, `Python3`, `NODE`, `Node` ➔ interpretadores reconhecidos
   - Os argumentos e opções subsequentes do comando permanecem **rigorosamente intactos** (preservando `-B`, `-C`, `-S`, variáveis `$HOME`, etc.).

2. **No componente `.ceh` em alvos de escrita — Vigente vs Planejado**:
   - *Vigente (PR #9 e versões anteriores)*: Em comandos com argumento de arquivo separado (ex: `echo x > .ceh/config.json`, `cp f .ceh/config.json`, `rm -rf .ceh`), caminhos com `.ceh/` ou `.CEH/` já são interceptados.
   - *Planejado para v2.1.1 (CA1)*: O suporte a operadores de redirecionamento colados sem espaço (`echo x >.ceh/a`, `printf x >.CEH/a`, `&>.ceh/a`) e com file descriptors (`1>.ceh/a`) está formalmente mapeado para a entrega da versão `v2.1.1` (Issue/Handoff CA1).

---

## 3. Resolução Canônica de Caminhos — Vigente (PR #9)

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

### 4.1 Comportamento Vigente (PR #9)
O Safety Gate monitora ferramentas de escrita e redirecionamentos padrão com separação de espaço:
- **Comandos com Destino Explícito**:
  - `tee`, `dd of=...`, `cp ... dest`, `mv ... dest`, `install ... dest` e `ln -s ... dest` são avaliados contra destinos protegidos (`.ceh/`).
- **Redirecionamento com Espaço**:
  - Operadores `>` e `>>` seguidos de espaço e caminho de destino protegido são bloqueados.

### 4.2 Comportamento Planejado (Alvo da Versão v2.1.1 / CA1)
A expansão da cobertura de lexer para redirecionamentos avançados faz parte da esteira **v2.1.1**:
- **Operadores Sintáticos Adicionais**: `>`, `>>`, `>|`, `&>`, `&>>`, `N>`, `N>>`, `<>` colados diretamente ao alvo (ex: `echo x >.ceh/a`, `echo x &>.ceh/a`).
- **Exclusão de Descritores de Arquivo Puros**:
  - Garantia de que `2>&1` ou `>&2` continuem categorizados como duplicações de file descriptor sem gerar falsos positivos de escrita.
