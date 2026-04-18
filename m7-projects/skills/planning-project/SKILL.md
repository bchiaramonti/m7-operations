---
name: planning-project
description: >-
  Conduz elaboração iterativa do Plano de Projeto em Markdown (PLANEJAMENTO.md
  em 1-planning/), aplicando boas práticas PMBOK + mindset ágil. Fluxo em
  incrementos: um artefato por vez, com aceite explícito antes de avançar.
  Codifica critérios de aceite e push-backs para cada um dos 9 artefatos
  (Contexto/Escopo, OKRs, WBS, Cronograma, Roadmap, Recursos, Comunicação,
  Riscos, Calendário). Output é snapshot estático — não é mantido em sync
  com os HTMLs depois gerados por building-project-plan.

  Use quando o usuário quer estruturar o pensamento do projeto ANTES de
  gerar os artefatos visuais — especialmente em projetos complexos onde
  o planejamento merece sessão dedicada.

  <example>
  Context: projeto recém inicializado, usuário quer pensar o plano com calma
  user: "Vamos planejar o projeto H1-02 com cuidado antes de gerar o plano visual"
  assistant: invoca planning-project; conduz os 9 incrementos iterativamente
  </example>

  <example>
  Context: usuário retomando sessão anterior
  user: "Continue o planejamento de onde paramos"
  assistant: invoca planning-project; lê status dos markers; retoma no primeiro artefato não-ACCEPTED
  </example>
user-invocable: true
---

# Planning Project

Conduz a elaboração iterativa de `1-planning/PLANEJAMENTO.md` — documento-fonte denso com 9 seções correspondentes aos artefatos visuais que `building-project-plan` depois gera. A skill é **interlocutora especializada**: aplica push-backs codificados de PMBOK + ágil para impedir que o pensamento passe para o visual sem antes ser filtrado.

**Output é estático.** Após `FINAL`, o MD não é mais mantido em sync com os HTMLs ou ClickUp — é história de como o projeto foi pensado, não estado operacional.

## Posicionamento no Ciclo de Vida

```
initializing-project  →  planning-project  →  building-project-plan  →  managing-action-plan  →  generating-status-materials
(scaffold obrigatório)   (MD opcional)         (10 HTMLs + xlsx)         (ClickUp sync)            (OPR + PPTX)
```

Esta skill é **opcional**. Quem já tem o plano claro pode pular direto para `building-project-plan` em modo interativo. Quem quer um MD denso como memória canônica passa por aqui.

## Pré-requisitos

- Plugin `m7-projects` instalado
- Projeto inicializado (`initializing-project` já rodou) — `<project-dir>/CLAUDE.md` e `BRIEFING.md` existem
- `1-planning/` vazia ou contendo apenas um `PLANEJAMENTO.md` parcial de sessão anterior

## Princípios de Operação

1. **Um artefato por incremento** — não avança para o próximo sem aceite explícito do atual
2. **Retrabalho permitido** — qualquer artefato já `ACCEPTED` pode ser reaberto sem derrubar os demais
3. **Estado persistente** — markers `<!-- STATUS: ... -->` permitem pausar e retomar em dias diferentes
4. **Push-back calibrado** — aplica critérios codificados para sinalizar incremento raso demais
5. **Output estático** — após aceite final, carimba "snapshot de planejamento inicial"
6. **Mindset ágil, não Scrum ritual** — entregáveis pequenos com aceite por incremento; sem sprint, retro, timebox

## Fluxo da Skill — 3 Fases

### Fase 1 — Setup

1. Ler `BRIEFING.md` e `CLAUDE.md` para contexto (nome, objetivo inicial, prazo, stakeholders iniciais)
2. Verificar `1-planning/PLANEJAMENTO.md`:
   - **Não existe:** criar do [template](templates/PLANEJAMENTO.tmpl.md) com 9 seções e marker `STATUS: PENDING` em todas
   - **Existe parcial:** ler markers; identificar primeiro artefato com status ≠ `ACCEPTED`; retomar dali
   - **Existe totalmente `ACCEPTED`:** perguntar se quer revisar artefato específico ou finalizar (Fase 3)

### Fase 2 — Loop de Incrementos

Para cada artefato do backlog ordenado (default abaixo; usuário pode pular/reordenar):

1. **Anunciar o incremento** — "Agora vamos trabalhar o artefato X. Propósito PMBOK: [...]. Vou validar contra: [lista curta dos critérios principais]."
2. **Coletar** — usuário escreve em prosa livre; skill faz perguntas pontuais, aplica frameworks, sugere exemplos
3. **Aplicar push-back** — confrontar conteúdo com [critérios codificados](references/acceptance-criteria.md). Se falhar em ≥1 critério, **não aceitar automaticamente**; apresentar push-back conforme [playbook](references/pushback-playbook.md) e perguntar se usuário quer ajustar ou sobrescrever com justificativa
4. **Marcar status** — usuário decide:
   - `ACCEPTED` — incremento validado, segue para o próximo
   - `DRAFT` — salva estado atual mas não considera pronto; skill pode retomar depois
   - `SKIPPED` — artefato não se aplica a este projeto (razão registrada no MD)
5. **Escrever a seção no MD** com conteúdo + marker atualizado + timestamp

### Fase 3 — Revisão Consolidada

Quando todos os artefatos estão `ACCEPTED` ou `SKIPPED`:

1. Rodar as [7 verificações cross-artefato](references/consistency-checks.md)
2. Apresentar relatório de consistência ao usuário (sem corrigir automaticamente — usuário decide)
3. Após confirmação: carimbar cabeçalho com `FINAL`, `finalizado_em: YYYY-MM-DD` e nota "snapshot estático"
4. Sugerir próximo passo: invocar `building-project-plan` que lerá este MD

## Backlog Ordenado (Default)

| # | Artefato | Por que nesta ordem |
|---|---|---|
| 01 | Contexto & Escopo | Tudo flui daqui; sem escopo, não há o que planejar |
| 02 | OKRs | Define sucesso; alinha com a estrela guia antes de decompor |
| 03 | WBS/EAP | Decomposição do escopo em pacotes verificáveis |
| 04 | Cronograma | Expansão temporal do WBS |
| 05 | Roadmap & Marcos | Projeção visual com marcos-chave |
| 06 | Recursos & Dependências | Precisa do WBS para saber quem faz o quê |
| 07 | Plano de Comunicação | Precisa do time definido para montar RACI e rituais |
| 08 | Riscos | Mid-late: precisa de escopo + time + cronograma para riscos reais |
| 09 | Calendário | Último: deriva de cronograma + rituais já definidos |

Usuário pode pular ou reordenar — a skill **sinaliza** se a mudança viola uma dependência lógica (ex.: Riscos antes de Escopo → warn, mas permite).

## Critérios de Aceite e Push-Backs

Esta skill é uma **interlocutora informada**. Os critérios e push-backs são o **valor real** — sem eles, a skill é um simples template-filler.

- Para **critérios de aceite** por artefato (checklist): ver [acceptance-criteria.md](references/acceptance-criteria.md)
- Para **push-backs** (como confrontar conteúdo raso): ver [pushback-playbook.md](references/pushback-playbook.md)
- Para **racional PMBOK/ágil** de cada critério: ver [pmbok-artifact-best-practices.md](references/pmbok-artifact-best-practices.md)

**Regra firme:** a skill sugere, explica, push-backa — mas **nunca aceita um incremento sem ok explícito do usuário**. Sobrescrever push-back requer justificativa registrada no MD.

## Schema do PLANEJAMENTO.md

Arquivo fixo: `<project-dir>/1-planning/PLANEJAMENTO.md`.

Estrutura obrigatória (headers de nível 2 são âncoras fixas; skill `building-project-plan` parseia por eles):

- Frontmatter YAML com metadados (projeto, código, líder, sponsor, início, fim, status, finalizado_em)
- 9 seções `## 01 · Contexto & Escopo` ... `## 09 · Calendário` com marker `<!-- STATUS: ... -->` imediatamente após cada header
- Sub-headers (`###`) podem variar conforme conteúdo

Detalhes completos: ver [planning-md-schema.md](references/planning-md-schema.md).

**Regras dos markers:**
- Valores: `PENDING | DRAFT | ACCEPTED | SKIPPED`
- Format: `<!-- STATUS: ACCEPTED | 2026-04-18 -->` (status + data ISO)
- Para `SKIPPED`: incluir sub-bloco `<!-- REASON: ... -->` logo depois
- Para push-back sobrescrito: incluir `<!-- OVERRIDE: justificativa -->` logo depois

## Revisão Cross-Artefato (Fase 3)

Antes de carimbar `FINAL`, skill valida 7 pontos. Inconsistências listadas para o usuário resolver — **skill não corrige automaticamente** (respeita autonomia).

Detalhes: ver [consistency-checks.md](references/consistency-checks.md).

## Contrato com `building-project-plan`

- Campos do frontmatter → hero da landing (`plano-projeto.html`)
- Cada seção `## NN · ...` → artefato HTML correspondente (mapeamento em [planning-md-schema.md](references/planning-md-schema.md))
- Seções `SKIPPED` → skill 03 decide entre placeholder ou omissão do nav-grid

**Fronteira:** quality gate é responsabilidade de `planning-project`; transformação é de `building-project-plan`. A skill 03 **não re-aplica** push-backs em modo `read-md`.

## Fora de Escopo (Intencional)

- **Geração de HTML, xlsx ou visual** — responsabilidade de `building-project-plan`
- **Sync com ClickUp** — responsabilidade de `managing-action-plan`
- **Manutenção contínua do MD** — é snapshot estático; mudanças em execução vivem no xlsx LIVE e no changelog
- **Timeboxes de sprint / cerimônias ágeis** — mindset ágil aqui é só "incrementos pequenos + aceite"
- **Decisões automáticas sem usuário** — skill push-backa, sugere, mas nunca aceita sem ok explícito
- **Projetos não-M7** — template assume contexto M7 (sponsor, líder, código H1-XX); adaptar seria modo futuro

## Validação pós-execução

Antes de declarar `FINAL`:

- [ ] Todos os 9 artefatos com status `ACCEPTED` ou `SKIPPED`
- [ ] Nenhum marker `PENDING` ou `DRAFT` remanescente
- [ ] Frontmatter YAML completo com `planejamento_status: FINAL` e `finalizado_em: YYYY-MM-DD`
- [ ] Cabeçalho com aviso "snapshot estático" adicionado
- [ ] 7 verificações de consistência executadas e inconsistências reportadas
- [ ] Próximo passo sugerido (invocar `building-project-plan`)

Se qualquer item falhar, **avise explicitamente** — não declare sucesso silencioso.

## Filosofia (uma linha)

A skill não substitui o raciocínio do usuário sobre o projeto — ela **força esse raciocínio a passar por filtros que PMBOK e décadas de prática ágil comprovaram que importam**, antes de deixar o pensamento virar visual.

## Additional resources

- [references/pmbok-artifact-best-practices.md](references/pmbok-artifact-best-practices.md) — racional PMBOK 7e + Doerr + ISO 31000 por artefato
- [references/planning-md-schema.md](references/planning-md-schema.md) — schema formal do MD (frontmatter + 9 seções + markers)
- [references/pushback-playbook.md](references/pushback-playbook.md) — catálogo de push-backs por artefato com exemplos
- [references/acceptance-criteria.md](references/acceptance-criteria.md) — checklist de `ACCEPTED` por artefato
- [references/consistency-checks.md](references/consistency-checks.md) — 7 verificações cross-artefato da Fase 3
- [templates/PLANEJAMENTO.tmpl.md](templates/PLANEJAMENTO.tmpl.md) — template com frontmatter + 9 seções pre-stubbed
