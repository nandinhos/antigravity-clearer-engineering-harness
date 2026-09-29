# Handoff 053 — PR-QA-D3 e otimização CI homologados; despacho do PR-20

- **Data/Hora:** 2026-09-28T18:14:39Z
- **Instância:** Revisor sênior independente do CEH
- **Branch:** `claude/code-review-technical-analysis-kfwcdl`
- **HEAD inspecionado:** `9fd4c72185d1e355e21f4da5186f999b036655c4`
- **CI remoto:** Run [36457271311](https://github.com/nandinhos/antigravity-clearer-engineering-harness/actions/runs/36457271311)
- **Risco da revisão:** MÉDIO — barreiras arquiteturais de segurança e normalização de caminhos.

## 1. Veredito

- **PR-QA-D3: HOMOLOGADO.** O AST resolve aliases nomeados e aliases de módulo para `shlex.split` e funções `normpath`; as chamadas não autorizadas são rejeitadas, mantendo a única exceção com limite de uma chamada em `rules.py:is_cert_tampering`.
- **Otimização de CI: HOMOLOGADA.** O workflow executa a suíte canônica e a adversarial em etapas próprias antes do E2E. Sob `CI`, o script E2E pula essas duas execuções repetidas e segue com as etapas restantes.
- **PR-20: DESPACHADO.** Pode tratar o índice de ADRs e as promessas verificáveis descritas na sequência anterior. O despacho é para trabalho documental e não aprova integração final da branch.
- **D04 (médio, INFERRED):** o commit `9fd4c72` alterou a semântica de caminhos para evitar resolução física de cwd sintético. A homologação deste ajuste específico fica pendente de uma prova segura sobre caminhos reais via symlink. Não considero D04 uma falha de D3 nem da otimização E2E; ela precisa ser resolvida antes da homologação geral/merge da branch.

## 2. Evidência de D3

**OBSERVED — mudanças:** `NormalizationAstVisitor` resolve aliases em `Import` e `ImportFrom`; detecta chamadas a `shlex.split` e aliases em qualquer escopo; detecta chamadas `normpath` e aliases de `os.path`, `posixpath` e `ntpath`; mantém a regra estrutural de exceção por call-site e teto.

**OBSERVED — mutações reproduzidas pelo revisor em clones isolados:**

| Mutação em cópia temporária | Resultado do teste estrutural |
|---|---|
| `from shlex import split as shell_lexer; shell_lexer(...)` | detectada; exit 1 |
| `import shlex as sx; sx.split(...)` | detectada; exit 1 |
| `from os.path import normpath as path_normalizer; path_normalizer(...)` | detectada; exit 1 |
| `import posixpath as ppath; ppath.normpath(...)` | detectada; exit 1 |

A suíte dedicada do HEAD executou os testes permanentes para 11 variantes sintáticas. A evidência de implementação registra 10/10 mutações D01/D02 reprovadas. A falsificação original de D02 foi fechada.

## 3. Evidência da otimização CI

- **OBSERVED:** `.github/workflows/ci.yml` executa `run-all-tests.sh` e `run-adversarial-tests.sh` antes de `run-e2e-simulation.sh` como etapas independentes.
- **OBSERVED:** `run-e2e-simulation.sh` executa as suítes canônica e adversarial quando `CI` não está definido; em CI, informa que elas já foram executadas e não as repete.
- **OBSERVED:** a Run 36457271311 corresponde ao HEAD `9fd4c72` e terminou `success`, com 4/4 jobs Ubuntu/macOS × Python 3.9/3.12.
- **OBSERVED:** metadados da run indicam início em `17:19:10Z` e conclusão em `17:22:25Z` (3m15s de tempo decorrido).

## 4. D04 — semântica física versus lexical de cwd

**OBSERVED — diff:** antes de `9fd4c72`, `detect_environment` aplicava `Path(target_dir).resolve()` e as regras de `rm` resolviam o `cwd` recebido. Agora `normalize_path` usa `os.path.normpath(str(cwd))`, `detect_environment` percorre os pais desse caminho lexical e `rm.is_target_catastrophic` / `rm.is_target_safe` conservam o cwd textual.

**INFERRED — risco:** se `target_dir` for um alias por symlink cuja configuração de ambiente esteja somente em um ancestral do destino físico (fora da cadeia de pais lexical), o detector pode deixar de encontrá-la e cair no fallback `development`. A normalização lexical usada pelo gate também pode não corresponder ao cwd físico usado pelo processo ao interpretar `..`. Em contexto de `rm`, essa diferença merece uma prova dedicada antes da integração.

**Tentativa de reprodução:** um comando local de prova isolada foi bloqueado pelo PreToolUse porque continha referência explícita a ambiente de produção. O bloqueio não foi contornado. Portanto, o impacto permanece `INFERRED`; a execução normal da suíte não cobre esta topologia de symlink.

**Despacho D04:** separar cwd sintético de cwd real sem enfraquecer a resolução física de caminhos existentes; adicionar caso temporário com symlink e configuração de ambiente no ancestral físico, além de alvos relativos de `rm`. A prova deve seguir as regras de autorização do hook; se permanecer bloqueada, solicitar ao responsável a rota aprovada para esse teste, sem alterar o comando para contornar o hook.

## 5. Validação local e estado

- **OBSERVED:** `bash clearer-engineering/scripts/test-runner.sh` — 62/62, `STATUS: PASS`, certificado no HEAD `9fd4c72`.
- **OBSERVED:** `bash evals/run.sh` — 5/5, veredito `APROVA`.
- **OBSERVED:** `bash clearer-engineering/scripts/doc-audit.sh` — 7/7 verificações estruturais.
- **OBSERVED:** branch limpa e sincronizada com `origin` no início da revisão. Nenhum código foi alterado pelo revisor; a prova de alias ocorreu somente em clones temporários.
- **Condição antes de integração final:** encerrar D04 com evidência autorizada, preservar `gate_baseline.txt` em `c247c79` e repetir suíte/evals/CI no HEAD que será integrado.
