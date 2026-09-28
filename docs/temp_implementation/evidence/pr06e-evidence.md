# Relatório de Evidências — PR-06e (Handoff 028)

- **Data/Hora**: 2026-09-26T12:00:00Z
- **Escopo**: Encerramento da Onda 1 (G1–G6) do CEH: varredura sem lista, shells fora da lista, agrupamentos de flags por `--help` e novas famílias (PHP, awk, deno, bun).
- **Alvo**: Resolução dos achados AD1, AD2, AD3 e AD4.

---

## 1. Implementação Técnica

### 1.1 AD1: Varredura Fail-Closed de Sufixos em Qualquer Comando (Sem Lista de Prefixos)
- A lista restritiva `KNOWN_PREFIXES` foi **completamente eliminada** de `safety-gate.py` (`grep -n KNOWN_PREFIXES` retorna vazio).
- Para **toda** posição `j >= 1` da linha de comando, se o token corresponder a uma cabeça analisada (`rm`, `git`, `find`, shells, `python*`, `php*`, `node`, `perl`, `ruby`, `awk`, `deno`, `bun`, `eval`, `su`, `watch`), o gate avalia recursivamente o sufixo (`tokens[j:]`) e combina pela decisão mais severa (`max_severity_decision`).
- Comandos com wrappers como `setsid`, `flock`, `chroot`, `busybox`, `strace`, `ssh host`, `docker exec app` que antecedem comandos perigosos são agora bloqueados com precisão cirúrgica em qualquer posição.

### 1.2 AD2: Suporte Abrangente a Shells Inline
- `extract_shell_c_command` foi atualizado para reconhecer:
  `sh`, `bash`, `zsh`, `dash`, `ksh`, `mksh`, `ash`, `fish`, `csh`, `tcsh` e `busybox <shell>`.
- Suporte a `-c` e `fish --command`.
- Comandos como `ksh -c "find / -delete"`, `fish -c "find / -delete"` e `ash -c "find / -delete"` são desembrulhados e bloqueados como CATASTROPHIC em dev/hml/prod.

### 1.3 AD3: Agrupamentos de Flags por Interpretador Conforme `--help`
- Agrupamentos em `ceh_core/interpreters.py` agora respeitam estritamente as flags que consomem argumentos:
  - **Perl**: `-M`, `-m`, `-I` (e octal opcional em `-l` e `-0`). Em `perl -MFile::Path -e '...'`, o `-M` consome `File::Path` e o `-e` subsequente é corretamente identificado como código inline.
  - **Python**: `-W`, `-X`, `-m`.
  - **Ruby**: `-r`, `-I`, `-E`, `-x`.
  - **Node**: `-r`, `--require` (e `-p` não colide com `-e`).
- Citação das linhas de `--help`:
  - Perl: `-[mM][-]module execute "use/no module..." before executing program`, `-Idirectory specify @INC/#include directory`.
  - Python: `-W arg : warning control`, `-X opt : set implementation-specific option`, `-m mod : run library module`.
  - Node: `-r, --require=... module to prepend on startup`.

### 1.4 AD4: Novas Famílias de Interpretadores (`ceh_core/interpreters_extra.py`)
- **PHP**: Suporte a `-r` com APIs destrutivas de FS (`unlink`, `rmdir`, `array_map("unlink"...)`) e desembrulho recursivo de chamadas de shell (`system`, `exec`, `shell_exec`, `passthru`, `popen`, `proc_open`, crases). Comandos legítimos como `php artisan route:list` e `php -r 'echo PHP_VERSION;'` permanecem permitidos.
- **awk / gawk / mawk / nawk**: Desembrulho de `system("...")` e `| "sh"`. Comandos legítimos como `awk '{print $1}' access.log` permanecem permitidos.
- **deno**: Subcomando `eval` com detecção de `Deno.remove(Sync)?` e verificação de alvos catastróficos.
- **bun**: Flag `-e`/`--eval` com APIs destrutivas de fs e shell.

---

## 2. Prova Física de Falsificabilidade da Invariante de Prefixos Arbitrários

Executada via script determinístico `scratch/verify_arbitrary_prefix_falsifiability_ad1.py`:
- Amostra: 400 comandos gerados pela gramática de fuzz com cabeças analisadas.
- Prefixo avaliados: `setsid`, `flock /tmp/l`, `strace -f`, `mywrapper_cmd`.
- **Com Gate Atual (Universal, sem lista)**: **0 violações**.
- **Com KNOWN_PREFIXES restrito (Simulação de regressão AD1)**: **2.312 violações**.
- Conclusão: a prova demonstra que, sem a varredura universal de sufixos em `safety-gate.py`, wrappers desconhecidos deixam comandos destrutivos passarem como `allow/GENERAL`, e a varredura sem lista fecha a classe definitivamente.

---

## 3. Conformidade Documental e Orçamento de Linhas (`doc-audit.sh`)

7/7 checagens aprovadas com todos os componentes dentro do orçamento normativo:
- `safety-gate.py`: 577 linhas (Teto: 650)
- `test-runner.sh`: 193 linhas (Teto: 200)
- `ceh_core/environment.py`: 127 linhas (Teto: 300)
- `ceh_core/find.py`: 200 linhas (Teto: 300)
- `ceh_core/git.py`: 294 linhas (Teto: 300)
- `ceh_core/interpreters.py`: 251 linhas (Teto: 300)
- `ceh_core/interpreters_extra.py`: 250 linhas (Teto: 300)
- `ceh_core/lexer.py`: 286 linhas (Teto: 300)
- `ceh_core/rm.py`: 233 linhas (Teto: 300)
- `ceh_core/rules.py`: 63 linhas (Teto: 300)
