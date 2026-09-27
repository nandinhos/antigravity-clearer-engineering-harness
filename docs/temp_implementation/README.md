# Workbench Temporário de Implementação (CEH Staging)

Esta pasta é o **ambiente temporário de engenharia por branch/feature** do **CLEARER Engineering Harness (CEH)**.
Ela fornece um *scaffold* padronizado e isolado para suportar o ciclo de vida de desenvolvimento, testes, pareceres do Conselho de Seniores e handoffs entre agentes e o desenvolvedor.

---

## 1. Estrutura do Scaffold Padronizado

Em uma branch limpa, esta pasta inicia vazia, preservando apenas este `README.md` instrucional e a seguinte topologia de trabalho:

```text
docs/temp_implementation/
├── README.md        # Guia canônico do ciclo de vida e regras de destilação
├── evidence/        # Registros brutos, outputs JSON, diffs e provas de falsificabilidade
├── handoffs/        # Relatórios de handoff sequenciais do ciclo in-flight
├── scripts/         # Harnesses de reprodução, dry-runs e scripts de teste descartáveis
└── conselho/        # Atas e deliberações multi-agente geradas pelo ceh-conselho
```

---

## 2. Ciclo de Vida do Workbench (Lifecycle)

O uso do workbench segue três fases obrigatórias:

### Fase 1: Scaffold Inicial (Branch Checkout)
- Ao derivar uma nova branch de desenvolvimento (`dev/slug` ou `dev-[slug]-referencia`), o workbench inicia no estado limpo.
- Subdiretórios transitórios (`evidence/`, `handoffs/`, `scripts/`, `conselho/`) são criados sob demanda conforme a necessidade da tarefa.

### Fase 2: Execução & Auditoria In-Flight (Desenvolvimento Ativo)
- Todos os testes empíricos, controles negativos, relatórios de handoff e consultas ao Conselho de Seniores são salvos exclusivamente nesta pasta.
- Garante blast radius zero na documentação canônica enquanto a solução estiver sendo iterada ou sujeita a refatorações.

### Fase 3: Destilação & Consolidação (Pós-Homologação / Pré-Merge)
Após a feature estar **100% pronta, com testes herméticos verdes, CI comprovado no servidor e homologação concluída**, executa-se o processo de **Destilação & Consolidação**:

1. **Promoção de Lições Aprendidas**:
   - Falhas superadas, armadilhas de ambiente e boas práticas permanentes são extraídas e persistidas na estrutura de memória canônica do projeto (`docs/lessons/`, `.ceh/`, KIs da IDE ou no hub MCP `dev-memory`).
2. **Consolidação na Documentação Canônica**:
   - Decisões estruturais, novos contratos e especificações são consolidados nos documentos definitivos em `docs/` (`architecture.md`, `safety_gate.md`, `CHANGELOG.md`, ADRs).
3. **Arquivamento ou Descarte de Auditoria**:
   - Se o projeto ou a organização exigir retenção formal de trilha de auditoria para fins de compliance ou marcos de release, os handoffs e relatórios da branch podem ser arquivados em pasta histórica de release ou anexados ao Pull Request / issue tracking.
   - Em fluxos rotineiros ou ágeis, com as lições e decisões devidamente destiladas nos passos 1 e 2, os arquivos intermediários de trabalho podem ser descartados com segurança.
4. **Reset do Scaffold**:
   - A pasta `temp_implementation/` é restaurada ao seu scaffold limpo padrão, contendo apenas este `README.md`, pronta para ser utilizada pela próxima branch ou feature.