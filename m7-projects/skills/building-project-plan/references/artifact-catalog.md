# Artifact Catalog

Catalogo dos 10 HTMLs (1 landing + 9 artefatos) gerados pela skill.
Para cada artefato: secoes, placeholders esperados no template, e quais
campos do `data` JSON alimentam cada secao.

## Indice

1. [Landing — `plano-projeto.html`](#landing--plano-projeto-html)
2. [01 — `contexto-escopo.html`](#01--contexto-escopo-html)
3. [02 — `eap.html`](#02--eap-html)
4. [03 — `roadmap-marcos.html`](#03--roadmap-marcos-html)
5. [04 — `okrs.html`](#04--okrs-html)
6. [05 — `recursos-dependencias.html`](#05--recursos-dependencias-html)
7. [06 — `plano-comunicacao.html`](#06--plano-comunicacao-html)
8. [07 — `riscos.html`](#07--riscos-html)
9. [08 — `cronograma.html`](#08--cronograma-html)
10. [09 — `calendario.html`](#09--calendario-html)

---

## Landing — `plano-projeto.html`

**Secoes:** `.hero` (gradiente caqui + logo + badge + h1 + subtitle + 5 meta-items) → `.estrela` (caixa caqui destacada) → `.section-title "Documentos do Projeto"` → `.nav-grid` com 9 `.nav-card` → `.footer`.

**Placeholders no template:**

| Placeholder | Origem em `data` |
|---|---|
| `{{logo_b64}}` | `load_logo_b64("offwhite")` |
| `{{project_name}}` | `data.project_name` |
| `{{project_code}}` | `data.project_code` |
| `{{project_subtitle}}` | `data.project_subtitle` |
| `{{lider}}` | `data.lider` |
| `{{sponsor}}` | `data.sponsor` |
| `{{dias}}` | `data.dias` ou calculado de `period_start`/`period_end` |
| `{{periodo}}` | `data.periodo` ou formatado de `period_start`/`period_end` |
| `{{estrela_guia}}` | `data.estrela_guia` |
| `{{nav_cards_html}}` | Constante `ARTIFACT_NAV` em `render_html.py` (9 cards fixos) |
| `{{footer_text}}` | Auto-construido |

---

## 01 — `contexto-escopo.html`

**Secoes:** `.estrela-box` → `.card "Contexto Estrategico"` (paragrafos + `.quote-box` + `<h3>` pos-quote) → `.scope-grid` (.scope-yes / .scope-no) → `.card "Decisoes de Escopo"` (`.dep-table`) → `.card "Conexoes com Portfolio"` (opcional, `.dep-table` com `.badge-in` / `.badge-out`).

**Placeholders + origem (`data.contexto`):**

| Placeholder | Origem |
|---|---|
| `{{estrela_guia}}` | `data.estrela_guia` |
| `{{contexto_paragrafos_html}}` | `data.contexto.paragrafos_pre_quote: list[str]` |
| `{{quote_box_html}}` | `data.contexto.quote: {text, source}` (opcional) |
| `{{contexto_pos_quote_html}}` | `data.contexto.pos_quote_h3: str` + `paragrafos_pos_quote: list[str]` |
| `{{scope_yes_html}}` | `data.contexto.scope_yes: list[str]` |
| `{{scope_no_html}}` | `data.contexto.scope_no: list[str]` |
| `{{decisoes_html}}` | `data.contexto.decisoes: list[{decisao, justificativa}]` |
| `{{conexoes_card_html}}` | `data.contexto.conexoes: list[{projeto, direcao_class, direcao_label, interface}]` (opcional; bloco inteiro condicional) |

---

## 02 — `eap.html`

**Secoes:** `.legend` (4 swatches) → `.wbs` (arvore CSS org-chart com `<ul>/<li>` aninhados) → `.section-title "Nivel 4 ..."` opcional → `.wp-table` opcional → `.note-box` com convencao WBS.

**Placeholders + origem (`data.eap`):**

| Placeholder | Origem |
|---|---|
| `{{wbs_tree_html}}` | Construido recursivamente de `data.eap.fases` (com `code`, `label`, `count`, `owner`, `trans`, `children`) |
| `{{nivel_4_section_html}}` | `data.eap.nivel_4: {title?, intro_html?, rows: [{wbs, nome, nivel, descricao, formato}]}` (opcional) |
| `{{convencao_wbs_html}}` | `data.eap.convencao_html` (HTML inline) |

**Estrutura de `data.eap.fases` (recursiva):**

```json
{
  "code": "1",
  "label": "Planejamento",
  "count": "5 pacotes",
  "owner": "Bruno",
  "trans": false,
  "children": [
    {"code": "1.1", "label": "TAP"},
    {"code": "1.2", "label": "Cronograma", "children": [...]}
  ]
}
```

`level` e inferido automaticamente pela profundidade na arvore (root → 0, fase → 1, subfase/processo → 2, pacote → 3+).

---

## 03 — `roadmap-marcos.html`

**Secoes:** `.phase-bar` → `.timeline-wrapper` com `.timeline` e `.block`s → `.section-title "Roadmap por Frente"` → `.roadmap` swim-lane (`.months-row` + `.lane`s + `.lane.gov`) → `.roadmap-legend` → `.section-title "Marcos do Projeto"` → `.milestone-grid`.

**Placeholders + origem (`data.roadmap`):**

| Placeholder | Origem |
|---|---|
| `{{phase_bar_html}}` | `data.roadmap.phase_bar: [{class, label, dates}]` |
| `{{timeline_blocks_html}}` | `data.roadmap.timeline_blocks: [{class, phase_label, label_top, process, dates, owner, parallel}]` |
| `{{n_months}}` | Calculado de `data.period_start`/`period_end` (numero de meses no intervalo) |
| `{{months_row_html}}` | Mesma fonte (gera 1 cell por mes) |
| `{{lanes_html}}` | `data.roadmap.lanes: [{is_gov?, code, name, owner, bars: [{start, end, class, title, range}], ticks: [{date, lbl, gate?, desc}], qrs: [{date, label}]}]` |
| `{{roadmap_legend_html}}` | `data.roadmap.legend: [{color, label}]` |
| `{{milestones_html}}` | `data.roadmap.milestones: [{date, date_iso, wbs, h4, p, major}]` |

**Posicionamento no swim-lane:** `_percent_position(start, end)` calcula `left%` e `width%` proporcionais ao `period_start..period_end` total. Marcos (`.tick`) usam `_percent_anchor(date)` para `left%` apenas.

---

## 04 — `okrs.html`

**Secoes:** N `.okr-block` (cada um `.obj-card` + `.kr-list` com Ks `.kr`) → `.cadence-box` com `.cadence-grid`.

**Placeholders + origem:**

| Placeholder | Origem |
|---|---|
| `{{okr_blocks_html}}` | `data.okrs: [{num, descricao, krs: [{num, h4, metric, target, unit}]}]` |
| `{{cadence_items_html}}` | `data.okrs_cadence: [{freq, desc}]` |

`metric` aceita HTML inline (para `<strong>`).

---

## 05 — `recursos-dependencias.html`

**Secoes:** `.section-title "Equipe do Projeto"` → `.team-grid` com `.team-card` (`.lead` para lider) → `.section-title "Alocacao por Periodo"` → `.alloc-table` (cruzando Pessoa × Periodo) → `.section-title "Dependencias com Portfolio"` → `.dep-table` → `.section-title "Investimentos"` → card de texto.

**Placeholders + origem (`data.recursos`):**

| Placeholder | Origem |
|---|---|
| `{{team_cards_html}}` | `data.recursos.team: [{lead, role, name, area, blocks: [{label, trans?}], alloc}]` |
| `{{alloc_period_headers_html}}` | `data.recursos.alloc.periods: list[str]` |
| `{{alloc_rows_html}}` | `data.recursos.alloc.rows: [{name, cells: {<period>: {label, class}}}]` (`class` = `active`/`trans`/`plan`/`close`) |
| `{{dependencias_rows_html}}` | `data.recursos.dependencias: [{projeto, tipo_class, tipo_label, interface, risco}]` |
| `{{investimentos_html}}` | `data.recursos.investimentos_paragrafos: list[str]` (cada item vira `<p>`; aceita HTML inline) |

---

## 06 — `plano-comunicacao.html`

**Secoes:** `.section-title "Rituais"` → `.ritual-grid` → `.section-title "Matriz RACI"` → `.raci-table` + legenda → `.section-title "Canais"` → `.channel-grid`.

**Placeholders + origem (`data.comunicacao`):**

| Placeholder | Origem |
|---|---|
| `{{ritual_cards_html}}` | `data.comunicacao.rituais: [{highlight?, freq, h3, p, meta: [{label, value}]}]` |
| `{{raci_papel_headers_html}}` | `data.comunicacao.raci.papeis: list[str]` |
| `{{raci_rows_html}}` | `data.comunicacao.raci.rows: [{atividade, atribuicoes: {<papel>: "R"|"A"|"C"|"I"}}]` |
| `{{channels_html}}` | `data.comunicacao.channels: [{icon, h4, p}]` |

---

## 07 — `riscos.html`

**Secoes:** `.section-title "Matriz Probabilidade × Impacto"` → `.matrix-container` com `.heat-map` (3x3 + axis labels) e `.risk-legend` (lista de risk-items) → `.section-title "Contramedidas"` → `.risk-detail` table.

**Placeholders + origem (`data.riscos`):**

| Placeholder | Origem |
|---|---|
| `{{heatmap_cells_html}}` | Construido a partir de `data.riscos.items[].prob` + `.imp` (ambos: `Alta`/`Media`/`Baixa` ou `high`/`med`/`low`); 9 cells na ordem fixa `(prob, imp)` = (high,low), (high,med), (high,high), ... |
| `{{risk_items_html}}` | `data.riscos.items: [{id, h4, prob, imp, p, severity, mitigation?}]` (severity: `crit`/`high`/`med`) |
| `{{contramedidas_rows_html}}` | `data.riscos.contramedidas: [{id, risco, severity, contramedida, acao_mitigacao, trigger}]` (default: usa `items` se `contramedidas` ausente) |

---

## 08 — `cronograma.html`

**Secoes:** `.stats` (4 stat-card) → `.filter-bar` → `.wh-table` (sticky header, com `.phase-row` / `.phase-row.close` / `.acao-row` / `.etapa-row` por linha do xlsx) → JS `filterRows()`.

**Placeholders + origem:**

| Placeholder | Origem |
|---|---|
| `{{stat_fases}}`, `{{stat_acoes}}`, `{{stat_etapas}}` | Contagem por `Tipo` ao iterar o xlsx |
| `{{stat_dias}}` | `data.dias` ou calculado de `period_start`/`period_end` |
| `{{cronograma_rows_html}}` | Iteracao das linhas do `Cronograma.xlsx` (passado via `--xlsx`); aplica classe `.phase-row.close` na ultima Fase raiz; entregavel vai em `.entreg` (acao) ou `.entreg-etapa` (etapa) |

**Important:** este artefato e o unico que NAO consome `data.<nome>` — ele consome diretamente o `Cronograma.xlsx`. Garante consistencia 1:1 entre xlsx e HTML.

---

## 09 — `calendario.html`

**Secoes:** `.stats` (counts por tipo) → `.legend` → `.filter-bar` → `#calendar-root` (renderizado por JS) → `.section-title "Lista Completa"` → `.summary-table` (renderizada por JS) → `<script>` com `events`, `MONTHS`, `DOW`, `renderCalendars()`, `renderSummary()`, `filterEvts()`.

**Placeholders + origem:**

| Placeholder | Origem |
|---|---|
| `{{stats_cards_html}}` | Counts por `type` em `data.events` |
| `{{events_json}}` | `data.events` (gerado por `derive_calendar_events.py`) — array de `{d, type, label, who, dur, out}` |
| `{{months_json}}` | Calculado de `period_start`/`period_end` — array de `{year, month, name, phases}` (`month` e 0-indexed para JS) |

**Eventos esperados (data.events):**

| Type | Cor | Origem |
|---|---|---|
| `fase` | `--verde-caqui` | Linhas Fase raiz do xlsx (inicio + fim) |
| `marco` | `--lime` | `data.roadmap.milestones` |
| `discovery` | `--discovery` (#5a8f5a) | Rituais de discovery (manual ou recorrente) |
| `validacao` | `--validacao` (#8b6914) | Rituais de validacao |
| `checkin` | `--checkin` (#7a8a9a) | Check-ins recorrentes (semanais por padrao) |
| `status-report` | `--status` (#b8860b) | Status reports mensais |
| `handoff` | `--handoff` (#c45d3e) | Reunioes de handoff (final de processo) |

`derive_calendar_events.py` automatiza a geracao a partir do xlsx + `data.comunicacao.rituais_calendar` (com data fixa) + `data.comunicacao.recurring_rituals` (com freq/start/end).

---

## Schema completo do `data` JSON

Para um exemplo end-to-end funcional, veja:
- `/tmp/sample-full-plan.json` (gerado durante smoke test desta skill)
- O projeto-modelo H1-02 (referencia visual canonica)
