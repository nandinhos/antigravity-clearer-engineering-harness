---
name: conselho-seniores
description: >-
  Add-on opcional do desenvolvedor: convoca a banca multi-agente do Conselho de Seniores
  (auto-descoberta dinâmica de CLIs como claude, codex, muse, hermes, agy, agent)
  para oferecer visão analítica 360º e apoio à decisão sob o protocolo CLEARER.
---

# Conselho de Seniores (Banca Multi-Modelo — Add-on Opcional)

> [!NOTE]
> **Add-on Opcional do Desenvolvedor (Visão Ampliada 360º)**:
> O Conselho de Seniores **NÃO é um requisito obrigatório** para o funcionamento ou conformidade do CLEARER Engineering Harness (CEH).
> Trata-se de uma dinâmica avançada de uso pessoal do desenvolvedor para colher pareceres especializados de diferentes modelos CLI de fronteira, elevando o nível de análise e subsidiando decisões complexas.

---

## 1. Princípio do Quórum Dinâmico & Degradação Graciosa

Nem todo desenvolvedor ou ambiente dispõe de todos os modelos instalados. O Conselho opera com **detecção automática de quórum**:
- Ao ser acionado, o comando inspeciona o `PATH` do sistema e identifica quais CLIs estão realmente presentes e configurados.
- Se houver apenas 1 ou 2 CLIs (ex: `claude` e `agy`), o Conselho é formado exclusivamente por eles.
- Se todos estiverem disponíveis, a banca é plenária.
- Se nenhum CLI externo for detectado, o comando encerra graciosamente sem emitir erros e sem bloquear o harness.

---

## 2. Modelos Candidatos e Suas Perspectivas

| Membro / CLI | Provedor / Ecossistema | Perspectiva Analítica | Foco de Avaliação |
|---|---|---|---|
| **`claude`** | Anthropic (Claude Code) | **Audit & Ponytail Lead** | Minimalismo (*anti-overengineering*), verificação de claims contra evidências (`OBSERVED`), clareza semântica e caça de edge cases. |
| **`codex`** | OpenAI (Codex CLI) | **Lógica Formal & Algoritmos** | Raciocínio lógico dedutivo profundo, invariantes matemáticos, estruturas de dados, tipagem estrita e concorrência. |
| **`muse`** | Meta (Muse Code) | **Sistemas & Portabilidade** | Arquitetura POSIX, portabilidade Linux/macOS/BSD, segurança de shell e performance de baixo nível. |
| **`hermes`** | Hermes Agent | **Tooling & Agentes** | Conectores MCP, gateways, confiabilidade de ferramentas externas e isolamento de dependências. |
| **`agy`** | Google Antigravity | **Harness & Safety Gate** | Integridade das regras do CEH, governança de ambientes (`DEV`/`HML`/`PRD`), blast radius mínimo e bloqueio de comandos destrutivos. |
| **`agent`** | Cursor Agent | **Diff Review Cirúrgico & DX** | Higiene de Git diff, ergonomia de código na IDE e consistência com os padrões existentes. |

---

## 3. Formas de Acionamento

### Diagnóstico de CLIs Disponíveis:
```bash
ceh-conselho --list-available
```

### Convocação Dinâmica com Inspeção de Git Diff:
Convoca automaticamente todos os CLIs ativos na máquina:
```bash
ceh-conselho --all --diff
```

### Convocação Focada por Especialidade:
Convoca apenas modelos específicos para uma dúvida pontual:
```bash
# Consultar apenas Claude e Codex para validar uma regra crítica:
ceh-conselho --agent claude --agent codex --diff --prompt "Avaliar se a FSM cobre todos os delimitadores POSIX"
```

### Simulação Prévia (Dry-Run):
```bash
ceh-conselho --all --diff --dry-run
```

---

## 4. Contrato de Saída e Despacho Soberano

Cada membro emite sua deliberação sob o contrato padronizado:
- **`VEREDITO`**: `HOMOLOGADO` | `RESSALVAS` | `REJEITADO`
- **`CERTEZA`**: Nível quantitativo (`0.0` a `1.0`) amparado em evidências
- **`ANALISE_ESPECIALIZADA`**: Diagnóstico sob a perspectiva do modelo
- **`RISCOS_IDENTIFICADOS`**: Pontos cegos detectados

A **Ata Consolidada** é gerada em `docs/temp_implementation/conselho/<TIMESTAMP>/ata_conselho.md`.  
A soberania técnica e a palavra final pertencem sempre ao **Desenvolvedor** no comando.
