VEREDITO: RESSALVAS
CERTEZA: 0.78

ANALISE_ESPECIALIZADA:

**O que conferi no repositório (OBSERVED, neste checkout de `dev`)**
- `.github/workflows/ci.yml:20-26`: o job `validate` usa a matriz `os: [ubuntu-latest, macos-latest]` × `python-version: ['3.9','3.12']`. Isso dá exatamente 4 checks `Validate (...)`, então a frase "os 4 jobs `Validate`" confere. O job macOS também existe, como a D2 supõe.
- `docs/adapters/novo-host.md` e `docs/architecture/adr-007-protecao-certificado-modelo-ameacas.md` existem, então os destinos da D2 e da D6 são reais.
- Não existe `ceh-doctor`, `ceh-ide-probe` nem `install.sh --verify` em `clearer-engineering/scripts/`. A D3 e a D4 são código novo, não reuso.
- Os handoffs 086–089 não estão na árvore de `dev`. O 088 só aparece no histórico (`5310c59`), em outro ramo. Por isso os incidentes 7, 8 e 9 e os achados CA1–CA8 ficam como INFERRED para mim: não os reproduzi.

**Por decisão**

- **D1, opção A (certeza 0.9).** É a única camada que não depende da máquina do agente, e o argumento do plano está certo. Faltam três coisas no contrato:
  1. **Bypass list vazia.** O desenvolvedor é admin. Se o admin puder contornar a regra, ela vira aviso de novo.
  2. **Aprovações obrigatórias = 0.** Com um único mantenedor, exigir 1 aprovação trava todo merge, porque ninguém aprova o próprio PR. Isso empurra para o bypass, que anula o item 1.
  3. **Os checks obrigatórios são casados pelo nome, e o nome inclui a matriz.** Se alguém mudar `python-version` ou `os`, o check exigido nunca chega e o merge trava em silêncio, ou alguém afrouxa a regra para destravar. Recomendo um job agregador estável (`ci-ok`, com `needs: validate`) como único check obrigatório.

  Prova de ativação: a consulta autenticada à API só vale se a resposta mostrar a regra. Um 200 sem regras não prova nada. Melhor ainda é a prova negativa: um push direto na `main` rejeitado, com o stderr registrado.

- **D2, aceitar com ressalvas (certeza 0.8).** Faltam colunas. Hoje "IDE" mistura três coisas que se comportam diferente:
  - o agy CLI headless (outro processo e outro payload);
  - o CI macOS (já existe e não está na tabela);
  - o hook do Claude Code CLI na máquina do desenvolvedor, onde o exit 2 bloqueia (incidente 1).

  A linha "Proteção da `main`, Sandbox ✅" contradiz o próprio plano, que diz que o sandbox não tem `gh` e usa um conector MCP com escopo desconhecido. A célula deve ser "✅ só se a resposta trouxer a regra; senão INFERRED".

  A regra "OBSERVED sem ambiente vira INFERRED" é a contribuição mais valiosa do plano, e não custa código.

- **D3, opção A, mas fundida na D4 (certeza 0.7).** Um hash de arquivos gerados pelo próprio agente prova integridade, não autenticidade. É autoatestado: quem montou evidência à mão no incidente 7 também consegue gerar o pacote com os hashes certos. O plano descreve isso como "reduz o espaço para erro", e essa frase está correta. Mas nenhum texto pode dizer que a D3 fecha o incidente 7. O fechamento real é a revisão reproduzir o canário pela D2 ou a gravação de tela (C) nas releases.

  Do ponto de vista do minimalismo, `ceh-ide-probe` e `ceh-doctor` repetem 80% do trabalho: o hash do gate instalado e a lista de plugins. Recomendo um único script, `ceh-doctor`, com `--evidence` para empacotar.

- **D4, três de quatro itens (certeza 0.8).**
  - O job com `CLAUDECODE=1`/`CLAUDE_PROJECT_DIR`: sim. Ele só vira barreira se entrar no `ci-ok` da D1. Se não entrar, é um aviso a mais.
  - O teste estático de `Path(...).resolve()`: rejeito. É uma heurística de grep frágil, com falso positivo e falso negativo. O melhor é um helper único de tmpdir nos testes, que já resolve o caminho, e o job macOS existente pega a regressão.
  - Maiúsculas no executável: não condicionar à plataforma. Um `casefold()` incondicional no basename do executável custa uma linha e não traz falso positivo relevante no Linux. "Registrar como limite" deixa o bypass `GIT push` aberto no macOS.
  - `ceh-doctor`: sim, já fundido com a D3.

- **D5, CA1 e CA2 no mesmo PR, CA5–CA8 fora (certeza 0.75).**
  - O `gate_baseline` só pode avançar depois da correção do CA1. Avançar antes congela o comportamento vulnerável como "dourado". A ordem dos commits dentro do PR precisa ser explícita: CA1, depois os controles, depois o baseline.
  - O CA1 deve ser testado na forma canônica do alvo (resolução de caminho, symlink e caixa), não só na sintaxe do redirecionamento. Senão ele reabre exatamente pelo vetor do incidente 9.
  - As caronas só de documentação diluem o diff de segurança da `v2.1.1`. Devem ir em outro PR.

- **D6, aprovar (certeza 0.9).** A ata do Conselho, incluindo este parecer, é opinião e não verificação. Concordo integralmente. Proponho uma regra a mais: um "homologado" sem comando reproduzível e saída capturada é inválido, venha de quem vier.

RISCOS_IDENTIFICADOS:
- O bypass de admin no ruleset anula a D1 sem que ninguém perceba.
- Exigir aprovação com um único mantenedor leva ao bypass habitual.
- O check obrigatório preso ao nome da matriz trava merges ou incentiva afrouxar a regra.
- O pacote da D3 pode ser tratado como prova de autenticidade, quando é autoatestado (o incidente 7 continua possível).
- Se o baseline avançar antes do CA1, a regressão vira corpus dourado.
- Se o job com `CLAUDE*` ficar fora dos checks obrigatórios, a D4 vira aviso.
- O `casefold` condicionado à plataforma deixa o incidente 9 aberto.
- Os claims dos Handoffs 087/088 não foram reproduzidos neste checkout (`dev`), então a base factual dos incidentes 7–9 é INFERRED.

RECOMENDACAO_FINAL:
1. **D1-A**, já: ruleset na `main` com PR obrigatório, 0 aprovações, bypass list vazia, sem force push e sem deleção, e como único check obrigatório um job agregador `ci-ok` (`needs: validate`, e depois o job da D4). Validar com um `git push origin main` direto rejeitado, com o stderr anexado ao handoff.
2. **D4 + D3** num PR:
   - `ceh-doctor`, com `--evidence`, compara o sha256 do gate instalado com a tag, lista plugins concorrentes e roda o canário;
   - job Ubuntu com `CLAUDECODE=1` dentro do `ci-ok`;
   - `casefold()` incondicional no basename;
   - helper de tmpdir resolvido, sem teste estático.
3. **D5** num PR `v2.1.1` só com CA1 e CA2, nesta ordem de commits: correção, controles (incluindo o alvo via symlink e com caixa trocada) e, por último, o avanço do `gate_baseline`.
4. **D2** com as colunas "agy CLI headless", "Claude Code CLI local" e "CI macOS". **D6** com a regra "homologado exige comando + saída reproduzíveis". As duas só em documentação, e CA5–CA8 num PR de documentação separado.
