---
name: building-project-plan
description: >-
  Constroi o Plano de Projeto completo dentro de 1-planning/ reproduzindo a
  estrutura do projeto-modelo H1-02: 1 landing (plano-projeto.html) + 9 artefatos
  HTML em artefatos/ (contexto-escopo, eap, roadmap-marcos, okrs, recursos-
  dependencias, plano-comunicacao, riscos, cronograma, calendario) + Cronograma.xlsx
  (planilha BASELINE do plano de acao que a skill managing-action-plan consome no 1o run).
  Aplica tokens do Design System M7-2026 e gera WBS/EAP hierarquica. Todo output
  vive em 1-planning/; a skill e proibida de escrever fora dessa pasta. Use quando
  o projeto foi inicializado (via initializing-project) e o usuario precisa do
  plano formal com todos os artefatos antes de comecar a executar.

  <example>
  Context: projeto inicializado, BRIEFING preenchido
  user: "Vamos construir o plano completo do projeto Playbook de Processos"
  assistant: invoca building-project-plan; coleta dados em 4 fases (carregamento, coleta, geracao, revisao); entrega 11 arquivos em 1-planning/
  </example>

  <example>
  Context: usuario pede para regerar plano com mudancas
  user: "Regera o plano com mais 2 KRs e atualiza riscos"
  assistant: invoca building-project-plan; carrega plan.json existente, aplica edicoes, regera os 10 HTMLs + xlsx
  </example>
user-invocable: true
---

# Building Project Plan

Constroi o **Plano de Projeto completo** de um projeto M7 dentro de
`<project-dir>/1-planning/`. Produz **11 arquivos**:

- `plano-projeto.html` — landing (capa/indice navegavel)
- `Cronograma.xlsx` — BASELINE do plano de acao (consumido por `managing-action-plan`)
- `artefatos/contexto-escopo.html` — Contexto, Escopo & Exclusoes
- `artefatos/eap.html` — WBS/EAP (arvore CSS org-chart)
- `artefatos/roadmap-marcos.html` — Phase-bar + timeline + swim-lane + marcos
- `artefatos/okrs.html` — OKRs com KRs mensuraveis + cadencia
- `artefatos/recursos-dependencias.html` — Equipe + alocacao + dependencias
- `artefatos/plano-comunicacao.html` — Rituais + RACI + canais
- `artefatos/riscos.html` — Heatmap probabilidade × impacto + contramedidas
- `artefatos/cronograma.html` — Tabela WBS interativa (derivada do xlsx)
- `artefatos/calendario.html` — Calendario mensal + lista de eventos (derivados do xlsx + rituais)

**Modelo Z (path policy):** todo output vive em `1-planning/`. A skill **nao escreve em nenhum outro diretorio** — `4-status-report/` e responsabilidade de `managing-action-plan` e `generating-status-materials`.

## Pre-requisitos

- Projeto inicializado via `initializing-project` (existe `<project-dir>/{1-planning,2-development,3-conclusion,4-status-report,_docs}/`)
- `BRIEFING.md` preenchido com objetivo, sponsor, lider, prazo, stakeholders
- Python 3.10+ com `openpyxl` instalado (`pip3 install openpyxl`)
- Logo M7 disponivel em `templates/assets/m7-logo-offwhite.b64` (ja incluido na skill)

## Quando invocar

| Pedido do usuario | Acao |
|---|---|
| "Construir o plano de projeto X" | Fluxo completo (4 fases) |
| "Gerar so o cronograma" | Roda apenas `generate_xlsx.py` com data parcial |
| "Regerar com mudancas" | Carrega plan.json existente, aplica edicoes, regera tudo |
| "Validar plano contra schema" | Roda `--validate-only` em generate_xlsx.py |

## Fluxo (4 fases)

### Fase A — Carregamento de contexto

1. Ler `<project-dir>/BRIEFING.md` + `<project-dir>/CLAUDE.md`
2. Extrair: `project_name`, `project_code` (se houver), objetivo, sponsor, lider, prazo, stakeholders
3. Confirmar/completar com o usuario o que faltar

### Fase B — Coleta estruturada (interativa, campo a campo)

Coletar conteudo para cada um dos 9 artefatos. Ordem natural:

1. **Contexto Estrategico:** paragrafos pre-quote + `quote_box` (text + source) + paragrafos pos-quote + estrela_guia
2. **Faremos / Nao Faremos:** listas (8-10 itens cada eh tipico)
3. **Decisoes de Escopo:** lista `[{decisao, justificativa}]`
4. **Conexoes com Portfolio:** lista `[{projeto, direcao_class, direcao_label, interface}]` (opcional)
5. **WBS/EAP:**
   - Estrutura de fases (default: Planejamento / Execucao / Encerramento)
   - Sub-fases dentro de cada fase (se aplicavel)
   - Pacotes por sub-fase
   - Padrao repetitivo no nivel 4 (se houver) — vira tabela `wp-table`
   - Convencao WBS (HTML inline com totais)
6. **Roadmap & Marcos:**
   - `phase_bar` (3 segmentos com flex 1/5/0.5 tipico)
   - `timeline_blocks` (1 por agrupamento temporal)
   - `lanes` (frentes para o swim-lane, com bars + ticks + qrs em lane.gov)
   - `legend` (cores das frentes)
   - `milestones` (date_iso + h4 + p; marcar `major:true` para criticos)
7. **OKRs:** N objetivos (default 3) × K KRs (default 3) com `target` quantitativo
8. **Equipe:** lider + donos (lead, role, name, area, blocks, alloc)
9. **Alocacao por Periodo:** matriz Pessoa × Periodo
10. **Dependencias com Portfolio:** lista de cross-projetos
11. **Investimentos:** paragrafos explicando natureza (documental vs tecnico)
12. **Rituais & RACI:** rituais com `meta`, RACI matrix com `papeis` + `rows`
13. **Canais:** icone + nome + descricao
14. **Riscos:** items com prob/imp/severity/mitigation; contramedidas com trigger
15. **Cronograma detalhado:** expansao da WBS com datas por linha (sugerir distribuicao uniforme; permitir ajuste); todos com `Status=not_started` na BASELINE
16. **Calendario (auto-derivado):** rituais com data fixa + recurring rituals com freq/start/end

Ver [`references/artifact-catalog.md`](references/artifact-catalog.md) para schema completo de cada secao.

### Fase C — Geracao

1. **Validar `data` JSON** contra schema (campos obrigatorios, tipos)
2. **Gerar `Cronograma.xlsx`** primeiro:
   ```bash
   python3 scripts/generate_xlsx.py --input data.json --output <project-dir>/1-planning/Cronograma.xlsx
   ```
   Schema completo em [`references/cronograma-xlsx-schema.md`](references/cronograma-xlsx-schema.md).

3. **Derivar `data.events`** para o calendario:
   ```bash
   python3 scripts/derive_calendar_events.py --input data.json --xlsx <project-dir>/1-planning/Cronograma.xlsx --inline-into data.json
   ```

4. **Renderizar os 10 HTMLs:**
   ```bash
   python3 scripts/render_html.py --input data.json --xlsx <project-dir>/1-planning/Cronograma.xlsx --output <project-dir>/1-planning/
   ```

5. Verificar **warnings** no output do `render_html.py` — qualquer placeholder remanescente significa bug no `data` (campo faltando) ou no template (placeholder novo nao previsto).

### Fase D — Revisao

1. Listar 11 arquivos gerados
2. Sugerir ao usuario abrir `<project-dir>/1-planning/plano-projeto.html` no browser para revisao visual
3. Confirmar que pasta `4-status-report/` esta intacta (nao deve ter sido tocada)
4. **Proximo passo:** invocar `managing-action-plan` — ela copia `1-planning/Cronograma.xlsx` para `4-status-report/Cronograma.xlsx` (LIVE) + adiciona col L `ClickUp ID` + faz push inicial ao ClickUp

## Design System M7-2026 (Invariante)

Todos os 10 HTMLs aplicam:
- Fonte unica: Inter (Google Fonts via @import)
- Tokens `:root` identicos (verde-caqui `#424135`, lime `#eef77c`, off-white `#fffdef`, etc.)
- Logo M7 embed base64 (offwhite para fundo escuro)
- Footer padrao "M7 Investimentos — Equipe de Performance — {projeto} — {Mes Ano}"
- Topbar prev/next em cada artefato (sequencia 01 → 09 → volta indice)

Detalhes em [`references/design-system-m7-2026.md`](references/design-system-m7-2026.md).

## Politica WBS

- Codificacao: `1`, `1.1`, `2.1.1.1` etc.
- 3 niveis na arvore visual (`eap.html` org-chart) + tabela `wp-table` opcional para nivel 4 com padrao repetitivo
- Cada **Acao** (pacote) tem dono unico + entregavel concreto + criterio de aceite
- Sub-fases (`Tipo=Fase` aninhadas) so quando ha multiplos agrupamentos naturais

Convencoes detalhadas em [`references/wbs-conventions.md`](references/wbs-conventions.md).

## Integracao com outras skills

| Skill | Relacao |
|---|---|
| `initializing-project` | **Pre-requisito** — cria a pasta `1-planning/` vazia |
| `managing-action-plan` | **Consumidor** — le `1-planning/Cronograma.xlsx` (BASELINE), copia para `4-status-report/`, adiciona col L `ClickUp ID`, faz push inicial e mantem sync com ClickUp |
| `generating-status-materials` | **Consumidor downstream** — usa `recursos-dependencias.html` (stakeholders), `riscos.html` (riscos ativos), `roadmap-marcos.html` (marcos), `4-status-report/Cronograma.xlsx` (LIVE) e `4-status-report/changelog.md` (historico) |

### Contrato com `managing-action-plan` (validado em smoke test)

1. Esta skill cria `1-planning/Cronograma.xlsx` (10 colunas B-K, todos `Status=not_started`)
2. `managing-action-plan/init.py` le esse xlsx, copia para `4-status-report/Cronograma.xlsx`
3. `init.py` adiciona coluna L `ClickUp ID` na LIVE (nao na BASELINE)
4. Pipeline completo: planejamento (esta skill) → execucao (managing-action-plan) → reporte (generating-status-materials)

## Validacoes pos-execucao

Apos rodar a skill, verificar:

- [ ] `<project-dir>/1-planning/plano-projeto.html` existe e abre no browser
- [ ] `<project-dir>/1-planning/Cronograma.xlsx` existe e abre no Excel/LibreOffice
- [ ] `<project-dir>/1-planning/artefatos/` contem **exatamente 9** arquivos `.html`
- [ ] **Nenhum diretorio fora de `1-planning/` foi tocado** (checar 4-status-report/, 2-development/, 3-conclusion/, _docs/)
- [ ] `render_html.py` reportou `warnings: NONE` (zero placeholders remanescentes)
- [ ] Todos os HTMLs usam tokens M7-2026 + Inter
- [ ] Topbar prev/next forma um ciclo: landing → 01 → 02 → ... → 09 → landing
- [ ] `cronograma.html` tem mesmo numero de linhas que `Cronograma.xlsx`
- [ ] `calendario.html` tem `events` consistente com fases do xlsx + marcos do roadmap
- [ ] Cross-skill: rodar `managing-action-plan/scripts/init.py --project-dir <proj> --clickup-list-id test` deve parsear o `Cronograma.xlsx` sem erro

## Anti-patterns a evitar

- **Mexer no `Cronograma.xlsx` apos gerar:** ele e a BASELINE imutavel; quem precisa editar e o `managing-action-plan` (na LIVE)
- **Gerar HTMLs sem ter `Cronograma.xlsx`:** `cronograma.html` precisa ler dele; `calendario.html` precisa de `events` derivados dele
- **Pular `derive_calendar_events.py`:** sem isso, `data.events` fica vazio e o calendario aparece em branco
- **Usar template de outro artefato:** cada template tem CSS especifico; copiar e modificar quebra fidelidade visual ao H1-02
- **Adicionar logo base64 manualmente:** carregar via `_lib.load_logo_b64()` para garantir consistencia
- **Escrever fora de `1-planning/`:** invariante critico do Modelo Z. Quebrar isso polui pastas de outras skills
- **Usar `<strong>`/`<em>`/`<code>` em campos que escapam HTML:** a maioria dos campos passa por `html_escape` — as tags aparecem literalmente no render. Ver [artifact-catalog.md — Convencao HTML inline vs escape](references/artifact-catalog.md#convencao-html-inline-vs-escape) para a lista curta de excecoes (prosa livre: `paragrafos_pre_quote`, `paragrafos_pos_quote`, `investimentos_paragrafos`, `metric` de KRs, campos com sufixo `_html`). Em campos que escapam, usar convencao editorial (CAIXA ALTA para labels, aspas para destaque).

## Scripts (referencia rapida)

| Script | Funcao |
|---|---|
| `_lib.py` | Modulo compartilhado (tokens, helpers HTML, datas BR, asset loading) — **nao invocar diretamente** |
| `generate_xlsx.py` | Gera `Cronograma.xlsx` BASELINE a partir de `data.rows` |
| `derive_calendar_events.py` | Deriva `events[]` do calendario a partir do xlsx + rituais |
| `render_html.py` | Renderiza os 10 HTMLs (orquestra templates + builds dinamicos + writes) |

## Templates (referencia rapida)

| Template | Artefato | Tamanho |
|---|---|---|
| `templates/plano-projeto.tmpl.html` | Landing | ~210 linhas |
| `templates/artefatos/contexto-escopo.tmpl.html` | 01 | ~125 linhas |
| `templates/artefatos/eap.tmpl.html` | 02 | ~155 linhas |
| `templates/artefatos/roadmap-marcos.tmpl.html` | 03 | ~155 linhas |
| `templates/artefatos/okrs.tmpl.html` | 04 | ~80 linhas |
| `templates/artefatos/recursos-dependencias.tmpl.html` | 05 | ~110 linhas |
| `templates/artefatos/plano-comunicacao.tmpl.html` | 06 | ~95 linhas |
| `templates/artefatos/riscos.tmpl.html` | 07 | ~115 linhas |
| `templates/artefatos/cronograma.tmpl.html` | 08 | ~105 linhas |
| `templates/artefatos/calendario.tmpl.html` | 09 | ~210 linhas |

Logos em `templates/assets/`:
- `m7-logo-offwhite.b64` — para fundo caqui (hero/page-header)
- `m7-logo-dark.b64` — para fundo claro (footer opcional)

## Fora de Escopo (Intencional)

- **Geracao de PDF do plano** — HTMLs sao navegaveis; conversao para PDF via browser print ou spec futura
- **`CRONOGRAMA.md` (formato markdown)** — descontinuado; o contrato e `Cronograma.xlsx`
- **Adicionar coluna `ClickUp ID` no xlsx** — responsabilidade da `managing-action-plan` no 1o run
- **Criacao de tasks no ClickUp** — responsabilidade da `managing-action-plan`
- **Criacao de `4-status-report/Cronograma.xlsx` (LIVE)** — responsabilidade da `managing-action-plan`
- **Atualizacao do xlsx** — apos a BASELINE ser criada, somente `managing-action-plan` escreve (e so na LIVE)
- **Geracao de OPR ou PPTX** — responsabilidade da `generating-status-materials`
- **Manutencao continua do plano** — os 10 HTMLs sao snapshots de planejamento; execucao vive em `managing-action-plan`
- **Escrita em qualquer diretorio fora de `1-planning/`** — proibido (Modelo Z)
- **Modo `revise`** — preservar conteudo e atualizar so campos alterados — pode ser implementado em v1.1+

## Additional resources

- [`references/design-system-m7-2026.md`](references/design-system-m7-2026.md) — Tokens, fontes, componentes, regras visuais
- [`references/artifact-catalog.md`](references/artifact-catalog.md) — Catalogo dos 10 HTMLs com placeholders e schema de `data` por artefato
- [`references/cronograma-xlsx-schema.md`](references/cronograma-xlsx-schema.md) — Schema formal do xlsx (colunas, tipos, validacoes, formatacao)
- [`references/wbs-conventions.md`](references/wbs-conventions.md) — Codificacao numerica + 3 niveis na arvore + nivel 4 em tabela + criterios de aceite
- [`references/example-project-h1-02.md`](references/example-project-h1-02.md) — Projeto-modelo H1-02 como benchmark visual e estrutural

## Referencia canonica

Qualquer duvida sobre estrutura, secao ou visual, **consultar o projeto-modelo H1-02:**

```
/Users/bchiaramonti/Library/CloudStorage/OneDrive-MULTI7CAPITALCONSULTORIALTDA/plan-estrategico/pe-26-30/iniciativas/H1-02_Playbook-de-Processos/plano-projeto/
```

Os templates desta skill sao **abstracoes fieis** desse projeto: qualquer divergencia visual, estrutural ou semantica entre o output da skill e o H1-02 deve ser tratada como bug, exceto quando o conteudo semantico do novo projeto diferir (esperado).
