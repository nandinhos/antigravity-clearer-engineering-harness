# Handoff 059 — Resolução e Prova Hermética de D04 (Symlink vs Lexical)

- **Data/Hora:** 2026-09-28T18:18:00-03:00
- **Instância:** Implementação CEH (orientada a evidências)
- **Branch:** `claude/code-review-technical-analysis-kfwcdl`
- **Ambiente:** `DEV` (`OBSERVED`)
- **Risco da alteração:** MÉDIO — resolução de caminhos, integridade do Safety Gate e normalização de alvos.

---

## 1. Veredito

- **D04: RESOLVIDO E COMPROVADO DINAMICAMENTE.** A divergência entre caminhos lexicais e físicos sob symlinks foi eliminada através de uma abordagem híbrida robusta.
- **Homologação Geral da Branch:** **PRONTA.** Com o fechamento de D04 (o último gate em aberto apontado nos Handoffs 056 e 058), todas as pendências da branch foram resolvidas, testadas e auditadas.

---

## 2. A Causa Raiz e a Solução Híbrida

1. **A Brecha de Segurança Prévia (D04):**
   - Ao adotar normalização estritamente lexical (`normalize_path(..., resolve_home=False)`), a inspeção de ancestrais (`curr.parents`) para um `target_dir` acessado via symlink percorria apenas os pais do symlink (ex: `/tmp`, `/`), ignorando os ancestrais físicos reais onde residem `.env.production` ou o repositório Git com branch `main`.
   - Isso provocava o rebaixamento silencioso da detecção de ambiente para `development`, contornando bloqueios de segurança (`[CEH PRODUCTION LOCK]`) em comandos como `rm -rf`.

2. **A Solução Canônica Híbrida Implementada:**
   - Em `ceh_core/environment.py`:
     - `detect_environment`: se `target_dir` existir fisicamente no disco (`p.exists()`), resolve com `.resolve()` antes de inspecionar os ancestrais (`[curr, *curr.parents]`). Se for caminho puramente sintético (não existe em disco), mantém a normalização lexical original.
     - `find_repo_root`: resolve fisicamente se existir em disco para encontrar a raiz `.git` em diretórios acessados por symlink.
     - `get_git_branch`: resolve o caminho para executar `git branch --show-current` no repositório físico real.
   - Em `ceh_core/rm.py`:
     - `is_target_catastrophic`: quando o alvo e o `cwd` existem fisicamente no filesystem, compara adicionalmente suas resoluções físicas (`.resolve()`), impedindo a exclusão acidental do diretório de trabalho ou seus ancestrais quando disfarçados por symlinks.
     - `is_target_safe`: bloqueia symlinks de escape dentro de diretórios como `tmp/` ou `scratch/` que apontem para fora do `cwd`.

---

## 3. Matriz de Requisitos do Despacho D04 Atendidos

| Requisito D04 (Handoffs 056/058) | Implementação | Evidência / Teste |
|---|---|---|
| **(a) Classificação de ambiente em ancestral físico via symlink** | `detect_environment` resolve caminho existente com `.resolve()`. | `test_symlink_environment.py::test_a` $\to$ Detecta `production` e aponta `.env.production` no diretório físico real pai do symlink. |
| **(b) Ancoragem de repositório Git e branch através de symlink** | `find_repo_root` e `get_git_branch` resolvem symlinks existentes. | `test_symlink_environment.py::test_b` $\to$ Identifica a raiz do repo real e a branch `main`. |
| **(c) Efeito em comando `rm` pelo Safety Gate sem exclusão real** | Avaliação in-process via `evaluate_rm_command` e `is_target_catastrophic`. | `test_symlink_environment.py::test_c` $\to$ Retorna `decision='deny'`, `severity='FILESYSTEM'`, motivo `[CEH PRODUCTION LOCK]`, e bloqueia symlinks catastróficos. Zero deleção em disco. |
| **(d) Preservação de caminhos sintéticos (não existentes)** | Fallback gracioso para normalização puramente lexical quando `exists() == False`. | `test_symlink_environment.py::test_d` $\to$ Caminhos virtuais normalizados sem quebras; suíte de fuzzing (2000+ casos) 100% verde. |

---

## 4. Prova de Falsificabilidade (Mutação)

- **Mutação:** Reversão de `detect_environment` para a versão puramente lexical anterior (removendo `raw_p.resolve()`).
- **Resultado:** A suíte falhou imediatamente com 2 falhas determinísticas (`AssertionError: 'development' != 'production'` nos testes `test_a` e `test_c`), comprovando que o teste é sensível e reprova regressões na resolução física.
- **Restauração:** Código de produção restaurado e suíte retornou a 100% PASS.

---

## 5. Auditorias e Validação

- **Suíte Canônica Local:** `bash clearer-engineering/scripts/test-runner.sh` $\to$ **PASS (64/64 testes, 100% verde, exit code 0)**.
- **Auditoria Documental:** `python3 clearer-engineering/scripts/doc-audit.py` $\to$ **SUCESSO (7/7 checagens aprovadas, orçamentos respeitados)**.
- **Higiene de Diff:** `git diff --check` $\to$ **Exit code 0 (zero whitespace errors)**.
