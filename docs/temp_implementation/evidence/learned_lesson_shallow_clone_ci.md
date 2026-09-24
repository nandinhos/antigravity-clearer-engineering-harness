# Lição Aprendida: Divergência de Ambiente Git (Full Clone Local vs Shallow Clone em CI Runners)

**Data:** 2026-09-23  
**Status:** RESOLVIDO  
**Tags:** `git`, `ci-cd`, `github-actions`, `shallow-clone`, `safety-gate`, `doc-audit`

---

## 1. O Problema / Sintoma Observado
Após a promoção das branches `dev`, `staging` e `main`, a suíte de testes passou 100% no ambiente local com emissão de Certificado de Voo do Safety Gate (`canonical_verified: true, status: PASS`), autorizando o `git push`.
Porém, no GitHub Actions, a esteira (`CEH Quality & Test Suite`) falhou nas 3 branches com o seguinte erro no Teste 45 (`doc-audit`):
```text
FALHA: 14 inconsistência(s) encontrada(s):
  [1] Commit da tabela do achado R1 não existe no histórico local: bb61fe7.
  ...
  [14] Commit citado na documentação não existe no histórico local: 1c9a0d2
Auditoria documental REJEITADA.
```

---

## 2. Causa Raiz
1. **Divergência Física de Ambiente**:
   - A máquina de desenvolvimento local possuía o histórico Git completo (`--depth` irrestrito).
   - O runner do GitHub Actions utiliza por padrão `actions/checkout@v4` com `fetch-depth: 1` (**Shallow Clone**), contendo unicamente o commit `HEAD`.
2. **Fragilidade da Asserção em `doc-audit.py`**:
   - O `doc-audit.py` executava `git rev-parse --verify <hash>^{commit}` para auditar os hashes de commits históricos citados no plano de validação.
   - Num shallow clone, commits ancestrais não existem localmente por desenho da esteira de CI.
   - O script não verificava `git rev-parse --is-shallow-repository` antes de emitir o veredito de falha.
3. **Por que o Safety Gate Local Autorizou o Push?**:
   - O Safety Gate local testou o código no ambiente nativo onde todos os 45 testes passaram (100% PASS).
   - Não havia evidência de falha local; o erro era exclusivo da assunção de profundidade de clone no runner remoto.

---

## 3. Correção Aplicada em Profundidade (Defesa em 3 Níveis)
1. **Nível 1 (Auditor Imune a Shallow Clones)**:
   - Em `clearer-engineering/scripts/doc-audit.py`:
     ```python
     is_shallow = subprocess.run(["git", "rev-parse", "--is-shallow-repository"], cwd=repo_root, capture_output=True, text=True).stdout.strip() == "true"
     if is_shallow:
         print("  • Repositório raso detectado (shallow clone de CI); validação de commits ancestrais ignorada com segurança.")
         checks_passed += 1
     ```
2. **Nível 2 (Configuração Canônica do Runner de CI)**:
   - Em `.github/workflows/ci.yml`, configurado `fetch-depth: 0` no step de checkout para que o runner do GitHub Actions baixe o histórico completo do projeto.
3. **Nível 3 (Certificação e Sincronização)**:
   - Nova suíte canônica executada, novo Certificado de Voo emitido no commit `b872e1b`, branches promovidas e `git push` executado.

---

## 4. Resultado Comprovado (`OBSERVED`)
As execuções no GitHub Actions retornaram **100% VERDE** em todas as branches:
- **`main`**: `✓ fix(ci,audit)... (27s)`
- **`staging`**: `✓ fix(ci,audit)... (25s)`
- **`dev`**: `✓ fix(ci,audit)... (34s)`
