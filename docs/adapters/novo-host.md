# Guia de Integração de Novo Host no CLEARER Engineering Harness (CEH)

Este guia sintetiza as lições aprendidas e os padrões consolidados ao longo da **Onda 4** (multi-host) para integrar novos hosts/agentes (como Antigravity, Claude Code, Muse Code ou futuros agentes) ao CEH de forma hermética, determinística e com zero regressão.

---

## 1. Sondagem e Evidência Real de Payloads (E0 / E1)

1. **Nunca assuma o payload a partir de documentação teórica**:
   - A documentação de plugins ou hooks de agentes frequentemente difere da implementação em runtime.
   - Crie um hook sentinela (sonda mínima, ex: `probe.py`) que apenas registra o `stdin` bruto e as variáveis de ambiente recebidas em um arquivo `.jsonl`.
2. **Grave payloads reais com comandos de controle**:
   - Comandos de leitura permitidos (`git status`, `ls`).
   - Comandos destrutivos em ambiente de desenvolvimento (`git reset --hard`).
   - Comandos destrutivos em produção / staging.
   - Comandos catastróficos (`rm -rf /`).
   - Ferramentas de escrita e edição de arquivos.
3. **Persista os payloads gravados**:
   - Salve os payloads em `fixtures/adapters/<host>/recorded.jsonl`.
   - Eles servirão como âncoras para testes unitários de detecção, parse e fidelidade de chaves.

---

## 2. Contrato de Resposta e Contexto de Execução Real (E13)

1. **Testar no contexto real em que o agente roda**:
   - O comportamento de hooks difere substancialmente entre execução via CLI e IDE (descoberto na transição Antigravity IDE × CLI no E13).
   - O fato observado é que o tratamento de códigos de saída (`exit code`) e formato de bloqueio varia entre ambientes (ex: CLI pode exigir exit 2, enquanto IDEs frequentemente exigem exit 0 com JSON para evitar crash ou fail-open).
2. **Mapear todos os braços do contrato**:
   - `allow`: qual JSON o host espera para liberar? (Ex: `{"decision":"allow"}` no Antigravity vs `{}` no Claude Code e Muse).
   - `deny`: qual formato realmente bloqueia? (Ex: no Muse, `{"decision":"deny"}` falha aberto; o formato real de bloqueio é `{"decision":"block"}`).
   - `ask`: se o host não suportar suspensão interativa, o adaptador **deve** converter `ask` para `deny` (H1, Handoff 006).
   - Códigos de saída (`exit code`): no Claude Code, `deny` exige exit code 2; no Antigravity e Muse, a saída DEVE ser exit code 0 para que o host processe o JSON e não entre em crash.

---

## 3. Formato de Reserva e Isolamento de Falhas (E1c / BI1)

1. **A reserva do shim deve ser especializada por host**:
   - O shim fino (`safety-gate.py`) atua como fail-closed sob falhas de importação ou sintaxe.
   - Se o motor ou o adaptador do host quebrar, a reserva em `adapters/fallback.py` deve responder com o formato nativo que **efetivamente bloqueia** naquele host (descoberta do E1c: fallback genérico com `deny` deixava o Muse executar comandos catastróficos).
2. **Biblioteca padrão estrita na reserva**:
   - O módulo de reserva (`adapters/fallback.py`) deve usar **apenas** a stdlib do Python (`sys`, `os`, `json`, `re`), sem imports internos que possam falhar.
3. **Leitura única do stdin**:
   - O buffer do `sys.stdin` só pode ser consumido uma vez; passe o payload lido para o despachante e para a reserva.

---

## 4. Isolamento em Testes e Confinamento de Risco (E15 / E16 / BH1)

1. **Desligar plugins pré-existentes durante os testes**:
   - Se uma versão anterior do plugin estiver ativa no ambiente do usuário (ex: `~/.config/` ou `~/.gemini/config/`), os testes ponta a ponta podem mascarar resultados ou bloquear comandos pela versão antiga (lição do E15/E16).
   - Antes de rodar testes ponta a ponta, registre a lista de plugins instalados, desative plugins concorrentes e restaure o estado no tearDown.
2. **Confinamento estrito de comandos de teste**:
   - **Nunca** envie comandos destrutivos reais como `rm -rf /` para sessões vivas de agentes (lição do BH1 / E15).
   - Utilize caminhos de teste confinados e sentinelas seguras sob diretórios temporários descartáveis (`/tmp/ceh_sandbox_...`).

---

## 5. Passos Práticos para Implementar o Novo Host

1. **Criar o adaptador `clearer-engineering/scripts/adapters/<host>.py`**:
   - Herdar de `HostAdapter` (`adapters/base.py`).
   - Implementar `detect(payload)`: identificação inequívoca via chaves exclusivas.
   - Implementar `resolve_target(payload)`: extração hermética do diretório de trabalho (`Cwd`, `cwd`, `workdir`).
   - Implementar `parse(payload)`: conversão do payload do host para `Request(command=..., cwd=...)` agnóstico.
   - Implementar `render(decision, payload)` e `render_error(message, payload)`: resposta nativa e exit code.
2. **Registrar o adaptador na lista canônica**:
   - Adicionar a classe em `clearer-engineering/scripts/hook_context.py` na lista `ADAPTERS`.
   - Adicionar o host na regra de detecção e resposta da reserva em `adapters/fallback.py`.
3. **Adicionar suporte no empacotador (`package.py`)**:
   - Implementar `package_<host>(out_dir)` em `clearer-engineering/tools/package.py`.
   - Gerar manifestos nativos correspondentes (ex: `manifest.json`, `.muse-plugin/plugin.json`, `.claude/settings.json`).
4. **Validar a Conformidade Cross-Host**:
   - Adicionar os geradores de payload sintéticos fiéis em `tests/test_cross_host_conformance.py`.
   - Garantir que a fidelidade de chaves, os 1.024 casos do corpus e as ferramentas de escrita passam com zero divergências.
5. **Comprovar Falsificabilidade por Mutação**:
   - Adicionar testes de mutação em clone temporário comprovando que quebras no novo adaptador reprovam os testes.

---

## 6. Matriz "Onde Cada Verificação Vale" (D2 / Handoff 090)

Toda afirmação técnica sob o CEH exige rigor epistêmico. A semântica `OBSERVED` só é válida no ambiente em que a observação física de fato ocorreu. Fora dele, a conclusão é estritamente `INFERRED`.

| Verificação / Prova | Sandbox de Revisão | CI Linux (Ubuntu) | CI macOS (Bash 3.2) | IDE-Linux | IDE-macOS | agy CLI Headless | Claude Code CLI Local |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Suíte Canônica (`run-all-tests.sh`)** | `OBSERVED` | `OBSERVED` | `OBSERVED` | `OBSERVED` | `OBSERVED` | `OBSERVED` | `OBSERVED` |
| **Paridade Claude (`claude-env`)** | `OBSERVED` | `OBSERVED` | `INFERRED` | `OBSERVED` | `INFERRED` | `INFERRED` | `OBSERVED` |
| **Compatibilidade macOS Bash 3.2** | N/A | N/A | `OBSERVED` | N/A | `OBSERVED` | N/A | N/A |
| **Transmissão/Bloqueio Real na IDE** | `INFERRED` | `INFERRED` | `INFERRED` | `OBSERVED` | `OBSERVED` | N/A | N/A |
| **Integridade de Instalação (`ceh-doctor --verify`)** | `OBSERVED` | `OBSERVED` | `OBSERVED` | `OBSERVED` | `OBSERVED` | `OBSERVED` | `OBSERVED` |
| **Ruleset GitHub (`gh api` autenticado)** | N/A (sem token) | N/A | N/A | `OBSERVED` (Dev) | `OBSERVED` (Dev) | `OBSERVED` (Dev) | `OBSERVED` (Dev) |

### 6.1 A Tupla de Evidência Canônica (Codex)
Toda evidência formalizada em relatórios deve ser estruturada pela tupla de 6 elementos:
$$\text{Tupla} = (\text{alegação}, \text{ambiente}, \text{versão}, \text{entrada}, \text{observação}, \text{método})$$

Uma afirmação alegando funcionamento em IDE sem teste real na IDE é categorizada compulsoriamente como `INFERRED`.

---

## 7. Papéis Canônicos de Engenharia e Release (D6 / Handoff 090)

1. **Agente de Execução (IDE / Antigravity)**:
   - Implementa o código cirúrgico seguindo o plano e as restrições arquiteturais.
   - Executa a suíte canônica local e gera certificados de voo (`test-runner.sh`).
   - Abre os Pull Requests correspondentes para a branch `dev`.
2. **Revisor Independente (Sandbox Isolado)**:
   - Realiza revisão adversarial de diff linha a linha.
   - Executa auditoria formal de falsificabilidade e não-regressão.
   - Homologa despachos com base em comandos e saídas reproduzíveis.
3. **Operador do Release (Desenvolvedor)**:
   - Papel exclusivo e soberano do desenvolvedor humano.
   - Executa canários de release no terminal do host (fora da sessão do agente).
   - Gerencia a proteção de branches no GitHub e realiza as publicações de tag.
