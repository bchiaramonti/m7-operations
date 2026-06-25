# Estrutura dos Slides do Deck — v3.0 (Editorial M7-2026)

Referência canônica para o agente `material-generator` montar o deck HTML do ritual de gestão. Vigente para qualquer vertical (CON, INV, SEG, CRE, UNI), qualquer nível (N1-N5) e qualquer subnível (WL/RE/etc).

> **Princípio fundador:** o ritual é organizado **por especialista**, não por KPI. O WBR é a única fonte de verdade — nenhum número é calculado ou inventado nesta etapa. O deck visual é editorial (TWK Everett, 1920×1080, deck-stage web component) e autocontido (CSS+fonts+JS+logos inline em base64).

## Sumário

1. [Estrutura geral](#1-estrutura-geral)
2. [Tokens M7-2026 e tipografia](#2-tokens-m7-2026-e-tipografia)
3. [Asset bundle e placeholders globais](#3-asset-bundle-e-placeholders-globais)
4. [Slide 1 · Capa](#slide-1--capa)
5. [Slide 2 · Agenda](#slide-2--agenda)
6. [Slide 3 · Matriz](#slide-3--matriz)
7. [Slide 4 · PA Status](#slide-4--pa-status)
8. [Slide 5 · PA Vencendo](#slide-5--pa-vencendo)
9. [Bloco por especialista (3 slides)](#bloco-por-especialista-3-slides)
   - [Slide N · Dashboard](#slide-n--dashboard)
   - [Slide N+1 · Análise (ranking)](#slide-n1--análise-ranking)
   - [Slide N+2 · Pipeline (funil)](#slide-n2--pipeline-funil)
10. [Slide pré-último · Consolidado](#slide-pré-último--consolidado)
11. [Slide último · Encerramento](#slide-último--encerramento)
12. [Regra de cor 3-tier (semáforo aplicado ao valor)](#12-regra-de-cor-3-tier-semáforo-aplicado-ao-valor)
13. [Renumeração e composição da agenda](#13-renumeração-e-composição-da-agenda)
14. [Anti-patterns](#14-anti-patterns)

---

## 1. Estrutura geral

| Posição | Slide | Quantidade |
|---------|-------|------------|
| 1 | Capa | 1 (fixo) |
| 2 | Agenda | 1 (fixo) |
| 3 | Matriz {NIVEL} | 1 (fixo) |
| 4 | PA Status | 1 (fixo) |
| 5 | PA Vencendo | 1 (fixo) |
| 6..(5+3N) | Bloco por especialista (Dashboard + Análise + Pipeline) | 3 × N |
| (6+3N) | Consolidado {NIVEL} | 1 (fixo) |
| (7+3N) | Encerramento | 1 (fixo) |

**Fórmula:** `total_slides = 7 + 3 × N`, onde `N = len(Card.apresentacao.responsaveis)`.

Exemplos:
- N=1 (CON N3 · Douglas): 10 slides
- N=2 (SEG WL · Claudia + Tarcísio): 13 slides
- N=3 (INV N1 expandido): 16 slides
- N=6 (vertical hipotética): 25 slides

> **Mudança v3:** o slide histórico "Agenda Especialista" (transição) foi removido. O avatar de iniciais (`<div class="avatar">XX</div>`) no header dos slides Dashboard/Análise/Pipeline sinaliza visualmente a troca de especialista. Os 3 slides do bloco compartilham o mesmo eyebrow `Bloco K · …` (K = posição na agenda, contado de 03 em diante).

---

## 2. Tokens M7-2026 e tipografia

Paleta canônica (qualquer hex fora desta lista é violação):

| Token | Hex | Uso |
|-------|-----|-----|
| `--verde-caqui` | `#424135` | Fundo dark, headings, headers |
| `--verde-medio` | `#4f4e3c` | Headers secundários, card-head |
| `--verde-claro` | `#79755c` | Subtítulos, footnotes, muted text |
| `--off-white` | `#fffdef` | Fundo light, texto sobre dark |
| `--lime` | `#eef77c` | Accent (tags, eyebrows, lime card-head) — NUNCA texto sobre fundo light |
| `--vc-50/100/200/300/400` | `#f6f6f5..#66655b` | Linhas alternadas, bordas, separadores |
| `--success` | `#4caf50` | Dot/seg verde, won bars |
| `--warning` | `#ffc107` | Dot/seg amarelo |
| `--error` | `#e40014` | Dot/seg vermelho, lose bars, riscos |
| `--success-text` | `#2e7d32` | Texto verde (legibilidade WCAG) |
| `--warning-text` | `#8a6d00` ou `#d18000` | Texto amarelo |
| `--error-text` | `#b8000f` | Texto vermelho secundário |

**Tipografia:**
- Família única `var(--font-sans)` = `"twkEverett", "twkEverett Fallback", Arial, Helvetica, sans-serif`.
- Pesos disponíveis: 200 (Ultralight, p/ donut-num e h1 capa), 300 (Light, p/ headings grandes), 400 (Regular, body), 500 (Medium, headers/labels), 700 (Bold, valores destacados).
- **NUNCA usar** `font-weight: bold` (use o numérico 700).
- **Mínimo absoluto** 8px. Body padrão 13-15px.

**Dimensões:**
- Canvas autoral 1920 × 1080 (16:9).
- Slides são `<section>` direct children de `<deck-stage width="1920" height="1080">`.
- Print: 1 slide por página em landscape via `@media print` do `deck-stage.js`.

---

## 3. Asset bundle e placeholders globais

O agente substitui os placeholders de asset lendo `templates/assets/`:

| Placeholder | Origem | Conteúdo |
|-------------|--------|----------|
| `{{ASSET_FONT_ULTRALIGHT_B64}}` | `assets/twk-everett-ultralight.b64` | Base64 do `.otf` weight 200 |
| `{{ASSET_FONT_LIGHT_B64}}` | `assets/twk-everett-light.b64` | Base64 weight 300 |
| `{{ASSET_FONT_REGULAR_B64}}` | `assets/twk-everett-regular.b64` | Base64 weight 400 |
| `{{ASSET_FONT_MEDIUM_B64}}` | `assets/twk-everett-medium.b64` | Base64 weight 500 |
| `{{ASSET_FONT_BOLD_B64}}` | `assets/twk-everett-bold.b64` | Base64 weight 700 |
| `{{ASSET_LOGO_OFFWHITE_B64}}` | `assets/m7-logo-offwhite.b64` | Logo claro (fundo escuro) |
| `{{ASSET_LOGO_DARK_B64}}` | `assets/m7-logo-dark.b64` | Logo escuro (fundo claro) |
| `{{ASSET_DECK_STAGE_JS}}` | `assets/deck-stage.js` | Conteúdo JS literal (não base64) |

**Placeholders globais** (substituídos uma vez no documento):

| Placeholder | Exemplo | Origem |
|-------------|---------|--------|
| `{{VERTICAL}}` | `Seguros` | parâmetro skill, capitalizado |
| `{{NIVEL}}` | `N3` | `Card.metadata.nivel` |
| `{{SUBNIVEL_SUFFIX}}` | ` · WL` ou string vazia | sufixo formatado quando subnivel ativo |
| `{{NIVEL_TOTAL_LABEL}}` | `N3 Total` | `{NIVEL} Total` (escopo da matriz) |
| `{{MES_ANO}}` | `Abril 2026` | Mês e ano de fechamento |
| `{{CICLO_LABEL}}` | `S18` (semanal) ou `04/2026` (mensal) | Período do ciclo |
| `{{DATA_FECHAMENTO}}` | `29/Abr/2026` | Data formato longo |
| `{{DATA_FECHAMENTO_CURTA}}` | `29/04` | Data formato curto |
| `{{ESPECIALISTAS_LISTA}}` | `Claudia Moraes · Tarcisio Catunda` | Diretos separados por `·` |
| `{{COORDENADOR}}` | `Joel Freitas` | `Card.apresentacao.coordenador` |
| `{{N3_SLIDE_NUM}}` | `12` | Posição do Consolidado = `6 + 3N` |
| `{{N3_BLOCO_NUM}}` | `05` | Eyebrow do Consolidado (zerofill 2-dig) |
| `{{N3_FNUM}}` | `12` | Numeração footer Consolidado (zerofill 2-dig) |
| `{{ENC_SLIDE_NUM}}` | `13` | Posição do Encerramento |
| `{{NIVEL_TOTAL_LABEL}}` | `N3 Total` | Label da última coluna da Matriz |

---

## Slide 1 · Capa

Estrutura editorial em 2 colunas, fundo `var(--verde-caqui)` com grid-bg sutil.

**Coluna esquerda (1fr)**: eyebrow `Ritual de Gestão · {NIVEL}` + bar lime; H1 `Resultados {VERTICAL}{SUBNIVEL_SUFFIX} {MES_ANO}` (font-size 116px, weight 300, lime no nome da vertical via `<em>`).

**Coluna direita (1fr)**: 4 meta-blocks empilhados (Ciclo, Área·Nível, Diretos, Coordenador). Cada bloco tem `.k` em verde-claro 13px uppercase + `.v` 22px off-white com strong em lime.

**Footer absoluto**: logo M7 (offwhite, 56px) à esquerda + stamp `M7 Investimentos · Ritual de Gestão` à direita.

Placeholders: `{{VERTICAL}}`, `{{NIVEL}}`, `{{SUBNIVEL_SUFFIX}}`, `{{MES_ANO}}`, `{{CICLO_LABEL}}`, `{{DATA_FECHAMENTO}}`, `{{ESPECIALISTAS_LISTA}}`, `{{COORDENADOR}}`, `{{ASSET_LOGO_OFFWHITE_B64}}`.

---

## Slide 2 · Agenda

Layout grid 320px (aside) + 1fr (timeline).

**Aside**: eyebrow `Estrutura do ritual` + headline `{{AGENDA_HEADLINE}}` (44px weight 300). Default headline:
- N≥2 especialistas: `Visão consolidada<br>+ gestão direta`
- N=1 especialista: `Visão consolidada<br>+ direto único`

**Timeline editorial** (`.agenda-tl`): linha vertical à esquerda + dots em cada `.tl-row`. Estrutura sequencial:

1. **`01 — Visão · Matriz de Indicadores`** — `{{AGENDA_T_VISAO}} min` (default 8)
2. **`02 — Operação · Plano de Ação · status das PAs`** — `{{AGENDA_T_OPERACAO}} min` (default 10)
3. **(feature rows · 1 por especialista)** — geradas pelo agente em `{{AGENDA_TL_FEATURE_ROWS}}`. Cada row tem fundo `var(--verde-caqui)` + dot lime + `tl-num` lime + `tl-title` off-white com `<em>` lime no nome do especialista. Default 15 min/cada.
4. **`{{AGENDA_NUM_SINTESE}} — Síntese · Consolidado {NIVEL} · sinais`** — `{{AGENDA_T_SINTESE}} min` (default 4)
5. **`{{AGENDA_NUM_FECHAMENTO}} — Fechamento · Encerramento · Próximos passos`** — `{{AGENDA_T_FECHAMENTO}} min` (default 3)

**Numeração dinâmica de tl-num**: Visão=01, Operação=02, especialistas=03..(02+N), Síntese=03+N, Fechamento=04+N.

**Fórmula de tempo total** (gatekeeper SSoT #12 — coerência com Roteiro do briefing):
```
T_total = T_VISAO + T_OPERACAO + Σ(T_ESP_K) + T_SINTESE + T_FECHAMENTO
       = 8 + 10 + 15*N + 4 + 3 = 25 + 15*N  (default)
```
Ajustável conforme briefing — o agente garante igualdade entre Slide 2 e Roteiro.

Placeholders adicionais: `{{AGENDA_HEADLINE}}`, `{{AGENDA_T_VISAO}}`, `{{AGENDA_T_OPERACAO}}`, `{{AGENDA_TL_FEATURE_ROWS}}`, `{{AGENDA_NUM_SINTESE}}`, `{{AGENDA_NUM_FECHAMENTO}}`, `{{AGENDA_T_SINTESE}}`, `{{AGENDA_T_FECHAMENTO}}`.

---

## Slide 3 · Matriz

Tabela única consolidando KPIs e PPIs por especialista. Colunas dinâmicas conforme `Card.apresentacao.responsaveis[]`.

### Cabeçalho (mx-row.head)

```
| Indicador | Sem Especialista | {Esp1} | {Esp2} | … | {NIVEL_TOTAL_LABEL} |
```

- `col-ind`: fundo `var(--off-white)`, texto `var(--verde-caqui)`.
- `col-noesp`: fundo `#353530`, texto off-white.
- `col-esp`: fundo `var(--verde-caqui)`. Para 2º especialista, classe `.tone-2` (`--verde-medio`); 3º `.tone-3` (`#5a5945`); 4º `.tone-4` (`#6c6b54`); 5º+ usar tom incremental ou repetir.
- `col-tot`: fundo `#5f5e4c`, font-weight 500, label `{NIVEL_TOTAL_LABEL}` (ex: `N3 Total`, `N2 Total`, `WL Total` se preferir o subnível).

### Grid de colunas dinâmico

O placeholder `{{MX_COLS_SPEC_FRACTIONS}}` recebe a string de fractions para `grid-template-columns`. Exemplo para N=2:
```
1.4fr 1fr 1fr 1fr 1fr   →   Indicador + Sem Esp + Esp1 + Esp2 + Total
```

Fórmula geral: `1.4fr` + `(N+2)` × `1fr` (Sem Esp + N Esps + Total).

### Seções

Duas seções obrigatórias com bandas coloridas:

```html
<div class="mx-section kpi">KPI · Indicadores de Resultado</div>
{{MX_ROWS_KPI}}
<div class="mx-section ppi">PPI · Indicadores de Funil</div>
{{MX_ROWS_PPI}}
```

> **Renames v3:** `KPI · Resultado` → **`KPI · Indicadores de Resultado`**; `PPI · Resultado` → **`PPI · Indicadores de Funil`**. **Leitura canônica da seção PPI:** "O que preciso ter no meu funil para atingir minhas metas de KPI?" — PPIs trazem suas metas dos Cards (`metas_ppi[*]` top-level + `kpi_references[*].regras_meta`).

### Linhas de dados (mx-row.data)

Cada linha tem 1 `col-ind` + (N+2) `cell`s. Cada cell:

```html
<div class="cell {{COLOR_CLASS}}">
  <div class="v">
    <div class="num">{{VALOR_REALIZADO}}</div>
    <div class="meta">{{PCT_ATINGIMENTO}}% meta · {{VALOR_META}}</div>
  </div>
</div>
```

- `{{VALOR_REALIZADO}}`: realizado formatado pela unidade (ex: `R$ 12K`, `8`, `28%`).
- `{{PCT_ATINGIMENTO}}`: % de atingimento calculado conforme `direction`:
  - `maior_melhor`: `(realizado / meta) × 100`
  - `menor_melhor`: `(meta / max(realizado, 1)) × 100`, capado a 200%
  - **special-case meta=0 + menor_melhor**: `100%` se `realizado==0`, `0%` se `realizado>=1`
- `{{VALOR_META}}`: valor da meta formatado pela mesma unidade.
- `{{COLOR_CLASS}}`: regra 3-tier (ver §12). Aplicada ao `.cell` (afeta `.num` via cascata):
  - `.good` → ≥100%
  - `.warn` → 70–99,9%
  - `.bad` → <70%
  - `.mute` → meta ausente
- Sub-line opcional `<div class="sub">{{CONTEXTO}}</div>` quando o indicador tem contexto (ex: `8 deals` ao lado de `R$ 138K`). Vai abaixo do `.meta`.

> **Sem dot semáforo na Matriz.** A coloração reside no `.num` via classe da `.cell`. Não há `<div class="dot">` aqui (o Slide 7 Dashboard mantém a coluna emoji 🔴🟡 como exceção visual).

### Total = soma das colunas

A coluna `col-tot` (`{NIVEL_TOTAL_LABEL}`) é renderizada como **soma** das células anteriores (Sem Esp + Esp1 + Esp2 + …). Para indicadores com unidade aditiva (BRL, count): soma direta. Para taxas (%, ticket médio): média ponderada ou recálculo a partir dos componentes — o agente lê `regras_meta.tipo_agregacao` no Card para decidir (`sum`, `weighted_avg`, `ratio`).

> **Mudança v3:** anteriormente esta coluna era `M7 Total = N1 bruto`. Agora é estritamente a soma/agregação das demais colunas. Diferença vs N1 bruto representa "deals não mapeados" e fica fora do quadro (movida para `.sub` opcional ou para o callout).

### Indicador "Estagnadas" — composição refatorada (TODO-MIGRACAO Item 5)

Para indicadores `oportunidades_estagnadas_funil_*` (CON e SEG WL desde 2026-05-04), o agent renderiza:

- **Linha principal (com semáforo 3-tier):** `% das ativas` lido de `oportunidades_estagnadas_funil_*_pct_ativas` no canonical JSON (entrada derivada gerada pelo `consolidating-wbr` Fase 4.5.a). Meta = `pct_ativas_max`. `direction: menor_melhor`.
- **Sub-linha contextual (sem semáforo):** `qty estagnadas`.
- **Sub-linha adicional:** `R$ volume estagnado` + `Xd média de aging` em `<div class="sub">…</div>`.

Formato HTML:
```html
<div class="cell {{COLOR_CLASS_PCT}}">
  <div class="v">
    <div class="num">{{PCT_ESTAGNADAS_ATIVAS}}%</div>
    <div class="meta">{{PCT_ATINGIMENTO}}% meta · {{PCT_ATIVAS_MAX}}% máx</div>
    <div class="sub">{{QTY}} deals · R$ {{VOL}} · {{DIAS}}d média</div>
  </div>
</div>
```

**Fallback (Cards sem `pct_ativas_max` ou ciclos antigos sem entrada derivada):** render legado com `qty` como linha principal e semáforo regra a sobre `qty / meta`.

### Callout final

Abaixo da matriz, callout `<div class="callout {{MX_CALLOUT_CLASS}}">` com label `Leitura` e corpo curto narrando a conclusão central do ciclo. Classe `.bad` quando situação geral crítica (≥1 KPI em vermelho); default lime border.

Placeholders: `{{MX_COLS_SPEC_FRACTIONS}}`, `{{MX_HEADERS}}`, `{{MX_ROWS_KPI}}`, `{{MX_ROWS_PPI}}`, `{{MX_CALLOUT_CLASS}}`, `{{MX_CALLOUT_BODY}}`, `{{NIVEL_TOTAL_LABEL}}`.

---

## Slide 4 · PA Status

Layout 460px (donut card) + 1fr (bars + callout). Fonte: ClickUp lista `pa-resultado` (901326795742) com filtros canônicos (custom field Vertical + Responsável Externo + parent only).

### Donut

`{{PA_DONUT_SVG}}` é gerado pelo agente como SVG inline 200×200 com 3 segmentos (verde no prazo / amarelo atenção / vermelho atrasada). Valor central `{{PA_TOTAL}}` em weight 200 96px.

Lógica de classificação por aging:
- **No prazo**: deadline > hoje + 7d (ou sem prazo mas status ativo).
- **Atenção**: deadline ∈ [hoje, hoje+7d].
- **Atrasada**: deadline < hoje OU status `atrasada`/`bloqueada`.

### Distribuição por owner

`{{PA_BARS_BY_OWNER}}` é gerado pelo agente — uma `.bar-row` por `Responsável Externo` único, com 3 segments (verde/amarelo/vermelho) proporcionais. Cada row: `lbl` (nome), `track` (3 segs), `total` (soma).

### Callout

`{{PA_CALLOUT_CLASS}}` (`.bad` ou default), `{{PA_CALLOUT_LABEL}}` (`Atenção` ou `Foco`), `{{PA_CALLOUT_BODY}}` (narrativa curta extraída do `analise/action-report.md`).

Placeholders: `{{PA_TOTAL}}`, `{{PA_NO_PRAZO}}`, `{{PA_NO_PRAZO_PCT}}`, `{{PA_ATENCAO}}`, `{{PA_ATENCAO_PCT}}`, `{{PA_ATRASADAS}}`, `{{PA_ATRASADAS_PCT}}`, `{{PA_DONUT_SVG}}`, `{{PA_BARS_BY_OWNER}}`, `{{PA_CALLOUT_CLASS}}`, `{{PA_CALLOUT_LABEL}}`, `{{PA_CALLOUT_BODY}}`.

---

## Slide 5 · PA Vencendo

Tabela das PAs com prazo nos próximos 7 dias (priorização por aging crescente, top 5).

### Schema da tabela

```
# | Ação | Causa raiz | Responsável | Prazo | Status
60px | 1fr | 220px | 180px | 120px | 160px
```

### Renderização de cada linha (`{{PA_TABLE_ROWS}}`)

```html
<div class="pa-row">
  <div class="num"><span>{{N}}</span></div>
  <div class="acao">{{TITULO_ACAO}}</div>
  <div class="causa">{{CAUSA_RAIZ}}</div>
  <div class="resp">{{RESPONSAVEL}}</div>
  <div class="prazo {{PRAZO_CLASS}}">{{DATA}}<span class="sub">{{ETIQUETA_AGING}}</span></div>
  <div><span class="pill {{PILL_CLASS}}">{{STATUS_LABEL}}</span></div>
</div>
```

- `{{PRAZO_CLASS}}`: `.bad` quando aging < 0 (atrasada); default sem classe.
- `{{ETIQUETA_AGING}}`: `D-{N}` ou `D+{N}` ou `D-1 · DECISÃO` quando crítica.
- `{{PILL_CLASS}}`: `pill-bad` (Atrasada/Bloqueada), `pill-warn` (Em curso), `pill-good` (No prazo).

### Callout `Foco da semana`

`{{PA_VENCENDO_FOCO}}` é narrativa curta apontando 1-3 PAs que precisam decisão imediata, citando ID/owner.

---

## Bloco por especialista (3 slides)

O agente gera, para cada especialista K em `Card.apresentacao.responsaveis[]`, uma sequência de 3 `<section>`s consecutivos. Numeração:
- Slide N = `5 + 3*(K-1) + 1` (Dashboard)
- Slide N+1 = `5 + 3*(K-1) + 2` (Análise)
- Slide N+2 = `5 + 3*(K-1) + 3` (Pipeline)
- Bloco eyebrow K = `03..02+N` (zerofill 2-dig)

Todos os 3 slides do bloco compartilham o `<div class="avatar">{{ESP_INICIAIS}}</div>` no `.h-left` como sinalizador visual.

### Slide N · Dashboard

Layout grid `1.4fr 1fr` — tabela à esquerda, riscos-card à direita (**leitura horizontal**, não empilhada).

**Tabela 6-col:**
```
Indicador | Meta | Real | Desvio | Δ vs {{PREV_CICLO_LABEL}} | (stat)
2fr | 1fr | 1fr | 1.4fr | 1.2fr | 60px
```

Bandas KPI (lime) e PPI (verde-claro) dividem as linhas.

**Renderização de cada linha** (`{{ESP_DASHBOARD_ROWS_KPI}}`/`{{ESP_DASHBOARD_ROWS_PPI}}`):
```html
<div class="dt-row">
  <div class="ind">{{INDICADOR}}</div>
  <div>{{META_N2}}</div>
  <div class="real">{{REAL_N2}}</div>
  <div class="desv {{DESV_CLASS}}">{{DESV_FORMATTED}}</div>
  <div class="delta">
    <span class="arrow">{{DELTA_ARROW}}</span>
    <span class="{{DELTA_TONE}}">{{DELTA_VAL}}</span>
  </div>
  <div class="stat">{{STAT_EMOJI}}</div>
</div>
```

- `{{META_N2}}` é a meta N2 individual: agente lê `n2.{especialista}.meta` do canonical JSON `dados/dados-consolidados-{vertical}.json` quando presente (TODO-MIGRACAO Item 6 — Cards com `metas_ppi.{indicador}.por_especialista`). Fallback: meta N1 agregada.
- `{{DESV_CLASS}}`: regra 3-tier sobre desvio relativo (`.good` ≥100%, `.warn` 70-99,9%, `.bad` <70%).
- `{{DESV_FORMATTED}}`: `±X% · ±R$ Y` ou `±N pp` para %, ou `±N` para counts. Usar pontos percentuais (pp) para indicadores em %.
- `{{DELTA_ARROW}}`: `▲`, `▼`, `→` (literal, cor cinza via classe `.arrow`).
- `{{DELTA_TONE}}`: `up`/`down`/`flat` define cor (verde/vermelho/cinza) baseado em `direction` do indicador. `up` quando o delta foi favorável.
- `{{DELTA_VAL}}`: valor literal (ex: `+12%`, `-6pp`, `+R$ 2,8M`).
- `{{STAT_EMOJI}}`: 🔴 / 🟡 / 🟢 / ⚪ por % atingimento (3-tier do §12). **Mantido nesta coluna** como exceção visual da Matriz.

**Indicador "Estagnadas" no Dashboard** (Item 5): mesma lógica da Matriz — linha principal `% das ativas`, sub-line `qty + R$ + dias`. A coluna stat usa o emoji baseado em `% das ativas` vs `pct_ativas_max`.

**Riscos card** (`{{ESP_RISCOS}}`):
- 3-4 itens `<div class="risk-item"><strong>{{TITULO_CURTO}}</strong> {{NARRATIVA}}.</div>`
- Cada item destaca 1 risco do WBR para esse especialista (concentração, queda de conv., subutilização etc.).

Placeholders por especialista: `{{ESP_NOME}}`, `{{ESP_INICIAIS}}`, `{{ESP_BLOCO_NUM}}`, `{{ESP_FNUM_DASH}}`, `{{ESP_DASHBOARD_ROWS_KPI}}`, `{{ESP_DASHBOARD_ROWS_PPI}}`, `{{ESP_RISCOS}}`, `{{PREV_CICLO_LABEL}}`.

### Slide N+1 · Análise (ranking)

Layout grid `1.4fr 1fr` — rank-card à esquerda, side-cards à direita.

**Rank-card** (`.rank-card`): cabeçalho 5-col `Assessor | Ativas | Criadas | Fechadas | Estagnadas`.

Bloco 1 — `<div class="rank-section squad">Squad {{ESP_PRIMEIRO_NOME}} · {{ESP_SQUAD_SIZE}} assessores</div>` em lime/preto.

Cada `.rank-row` da squad:
```html
<div class="rank-row">
  <div class="rname{{ESP_FLAG}}">{{NOME_ASSESSOR}}{{ESP_TAG}}</div>
  <div class="rcell{{EMPTY}}"><div class="mini"><div class="fb fb-good" style="width:{{W}}%"></div></div><div class="vlbl">{{QTY}} · R$ {{VOL}}</div></div>
  …
</div>
```
- `.rname.esp` (italic + bold) quando o assessor é o próprio especialista (label `(esp)` adicionado).
- `.rname.outside` (cinza muted) na seção `Fora da squad`.
- `.rcell.empty` quando sem dado (mini track vazio + vlbl `—`).
- Larguras das bars são percentuais relativos ao máximo daquela coluna.

**Linhas verticais entre rcells:** `border-left: 1px solid var(--vc-100)` (versão escurecida vs `--vc-50` antigo).

**Coluna "Fechadas" — bars duplas (won + lose):**
```html
<div class="rcell">
  <div class="mini dual">
    <div class="fb fb-won"  style="width:{{W_WON}}%">  </div>
    <div class="fb fb-lose" style="width:{{W_LOSE}}%"> </div>
  </div>
  <div class="vlbl">{{WON}} won · {{LOSE}} lose</div>
</div>
```
Larguras proporcionais ao total de oportunidades fechadas (won+lose) do mês. Fonte: `taxa_conversao_funil_*` (Bitrix won/lose), não ClickHouse.

Bloco 2 — `<div class="rank-section outside">Fora da squad · referência</div>` (cinza/muted) + linhas com `.outside`.

**Side cards** (`{{ESP_SUMMARY_CARDS}}`): até 5 `.summary-card`s seguidos de 1 `.callout`:

1. **Concentração de receita** — `sv` mostra `X / Y` (top contribuintes / total squad). `sd` aponta single-point-of-failure.
2. **Cobertura** — `sv.bad` quando <50%; mostra `assessores_com_deal_ativo / total_squad`.
3. **Estagnação · alerta** — `sv.bad`; mostra dias médios ou `qty estagnados`.
4. **Assessores com opp criada no mês (NOVO)** — `sv` mostra `X / Y` (assessores com ≥1 `oportunidades_criadas_funil_*` no mês / total_squad). Calculado pelo agente sobre o canonical JSON agrupando por `responsavel_id` distinct dentro do mês.
5. **Oportunidades sem atividade planejada — variante LISTA (NOVO)** (`.summary-card.list`) — fonte: indicador `oportunidades_sem_atividade_planejada_funil[_seg]` (canonical JSON, `nivel='Detalhe'` filtrado por `especialista=ESP_NOME`).

   **Layout 2-linhas por item** (atualizado 2026-05-05):
   ```
   ┌─────────────────────────────────────────────────────┐
   │ Marina Bonelli — Vida 500K                          │  ← linha 1: dl-name
   │ Bruna Fontes · COTAÇÃO                              │  ← linha 2: dl-resp · dl-stage
   │ ─────────────                                        │
   │ Carlos Tinoco — Patrimônio                          │
   │ Tarcisio Catunda (esp) · PROPOSTA  ← classe .esp    │  italic+muted quando não há assessor
   │ ─────────────                                        │
   │ Empresa XYZ — Empresarial                           │
   │ Pedro Ramos · APRESENT.                             │
   └─────────────────────────────────────────────────────┘
   ```

   **HTML por item:**
   ```html
   <li>
     <div class="dl-name">{nome_deal}</div>
     <div class="dl-meta">
       <span class="dl-resp{| esp if assessor null/vazio}">{assessor_ou_esp_label}</span>
       <span class="dl-stage{| late if dias_sem_atividade > 14}">{estagio}</span>
     </div>
   </li>
   ```

   **Regras de renderização:**
   - Top 5 deals ordenados por `dias_sem_atividade DESC` (mais críticos primeiro).
   - **Coluna responsável** (linha 2 esquerda):
     - `assessor` populado no JSON → texto normal (`Bruna Fontes`).
     - `assessor` null/vazio → italic muted com sufixo `(esp)` (`Tarcisio Catunda (esp)`).
   - Estágio em uppercase pequeno; classe `.late` (vermelho + bold) quando `dias_sem_atividade > 14`.
   - Header `<div class="sh">Sem atividade planejada<span class="sh-count">{N} deals</span></div>`.
   - Se total > 5: `<div class="more-note">+{total-5} restante(s)</div>`.
   - Se 0 deals (ideal): render `<div class="sd">Sem deals nesta condição.</div>` em verde-claro.

   **Filtro de pipeline:**
   - SEG: `STAGE_SEMANTIC_ID='P'` (inclui On Hold C156:UC_1SS9EP por design — ver YAML).
   - CON: whitelist por NOME `STAGES_ATIVO = {Prospecção, Investigação, Apresentação, Proposta, Emissão de Contrato, Cotas Alocadas}` (exclui "Cotas Fechadas/Vencidas/Contempladas/Finalizadas" que têm semantic_id='P' mas são deals já ganhos).
   - Card sem o indicador (verticais ainda não migradas) → pular este card silenciosamente (degradação graciosa).

   **Aparição também na Matriz (Slide 3) e Dashboard (Slide N por especialista) — NOVO 2026-05-05:**
   - Após ser declarado com `papel: ppi_funil` no Card e `metas_ppi.qty: pendente`, o indicador aparece como linha de **PPI · Indicadores de Funil** na Matriz consolidada e no Dashboard de cada especialista.
   - Renderização: realizado normal (qty + sub-label "Meta pendente"); dot/cor cinza no semáforo (regra de meta ausente).
   - Quando meta for definida (3-6 ciclos de baseline), o card transita para semáforo 3-tier normal sem mudança no agente.
6. **Callout `Comparativo`** (apenas quando N≥2) — compara métrica do especialista vs outro(s) do squad. Classe `.bad` se este está pior.

### Slide N+2 · Pipeline (funil)

Layout: kpi-row (6 tiles fixos) + grid `1fr 1fr` (funnel + cards laterais).

**KPI tiles** (`{{ESP_KPI_TILES}}` — agente compõe 6):
```
Deals ativos · Volume ativo · Ticket médio · Estagnados · Squad c/ opp · Conv. mês
```
Cada `.kpi-tile`: valor `.v` (com classe `.bad`/`.warn`/`.good` por status) + label `.l`. Agent computa estagnados em vermelho se 100%; conversão em verde se ≥40%; etc.

**Funil SVG** (`{{ESP_FUNNEL_SVG}}`): SVG inline 720×380 com N estágios do pipeline (lê `Card.kpi_references` ou cabeçalho do indicador `oportunidades_*_funil_*`). Cada estágio é um polygon centralizado, decrescente em largura proporcional ao volume relativo. Cores interpoladas linear de `var(--vc-500)` (topo) a `#2e7d32` (último, quando há volume) ou `var(--error)` (acúmulo terminal). Anotações:
- Lateral esquerda: `% conversão entre estágios` (cinza ou vermelho/verde se crítico).
- Lateral direita: `qty deals · R$ valor`.
- Footer: diagnóstico curto (gargalo principal, em vermelho).

**Cards laterais** (3 vertical):
1. **Destaque** (success) — pontos positivos (top-deals, conversão).
2. **Estagnação** (error) — bloqueios, deals parados.
3. **Projeção · `{{ESP_PROJECAO_LABEL}}`** (muted) — projeção de fechamento.

**Card Projeção (v3.2.0 — 2026-05-04):** card EXPANDIDO para Receita E Volume com 6 bars total (3 por métrica × Realizado MTD + Proj. mês corrente + Proj. mês seguinte).

Lê `{cycle_folder}/analise/projection-by-especialista.json` (gerado por E5 v6.2.0+ via método `installment_amortization` para receita + `pipeline_conversion_extended` para volume — resolve KNOWN_ISSUES.md ISSUE #1).

**Estrutura visual:**
```
┌─ Projeção · {Provável|Possível|Improvável} ─────────────┐
│ RECEITA                                                  │
│   Realizado MTD          [████░░░░░] R$ 56,8K            │
│   Proj. Mai              [██████░░░] R$ 59,8K            │
│   Proj. Jun              [█████████] R$ 62,0K            │
│ ─────────────────────                                     │
│ VOLUME                                                   │
│   Realizado MTD          [██████░░░] R$ 14,5M            │
│   Proj. Mai              [█████████] R$ 15,3M            │
│   Proj. Jun              [████░░░░░] R$ 13,7M            │
│ Meta Mai: R$ 110K · gap proj. -R$ 50K. {comentário}     │
└──────────────────────────────────────────────────────────┘
```

**Placeholders:**
- `{{ESP_PROJECAO_LABEL}}`: classificação consolidada (pega o pior dos dois — se Receita=Provável e Volume=Improvável, label = Improvável).
- `{{ESP_PROJECAO_RECEITA_BARS}}`: 3 `.proj-row` consecutivos (Realizado MTD + Proj. {MES_CORR} + Proj. {MES_SEG}). Cada bar: `.fill` largura proporcional à `meta_mes` (cap 100%); cor 3-tier sobre `pct_atingimento_proj` (verde ≥100%, amarelo 80-99%, vermelho <80%).
- `{{ESP_PROJECAO_VOLUME_BARS}}`: idem para Volume. Quando `Card.regras_meta.meta=0` (ex: SEG WL/RE Volume), cor neutra `var(--verde-caqui)` proporcional ao maior valor (sem comparação).
- `{{ESP_PROJECAO_NOTA}}`: `Meta {MES_CORR}: R$ X · gap proj. {±} R$ Y. {comentário curto}`. Sufixar `(confiança baixa em {Receita|Volume})` quando aplicável.

**Source data por especialista (no JSON):**
```json
{
  "receita_*_mensal": {
    "realizado_mtd": <num>, "meta_mes": <num>,
    "projecao_mes_corrente": <num>, "projecao_mes_seguinte": <num>,
    "classificacao": "Provavel|Possivel|Improvavel",
    "confianca": "high|medium|low",
    "comentario": "..."
  },
  "volume_*_mensal": { ...mesma estrutura... }
}
```

**Métodos (resumo, detalhe em `m7-controle/skills/projecting-results/SKILL.md`):**
- **Receita** (`installment_amortization`): LAGGING (parcelas das vendas dos N-1 meses anteriores caindo no mês alvo, lidas do ledger ClickHouse) + NOVA (1ª parcela do volume projetado × commission_rate / 12).
- **Volume** (`pipeline_conversion_extended`):
  - Mês corrente: `Vol_Oport_Ativas × Taxa_Conversao_Mes`
  - Mês seguinte: `(pipeline_residual + entradas_novas_3m_média) × Taxa_Conversao`

**Quando renderizar o card:**
- 2 sections (default): Card tem `kpi_references[].projecao.obrigatoria == true` para Receita E Volume (CON v2.4.0+, SEG WL v2.10.0+, SEG RE v1.2.0+).
- 1 section: só uma das métricas com obrigatoria=true.
- Sem card: nenhuma das duas (raro — só se Card explicitamente desabilita).

**Fallback gracioso:**
- `projecao_mes_seguinte` ausente no JSON → bar vazia + vlbl `—` + classe `.confidence-low` (italic muted).
- `confianca == "low"` → mesma classe no `.v` (sinal visual de incerteza).
- JSON ausente (E5 não rodou ou falhou) → toda section em `.confidence-low` com vlbls `—`. Não bloqueia o slide.

---

## Slide pré-último · Consolidado

Sempre gerado, independente de N. Posição = `6 + 3*N`.

Layout grid `1fr 1fr` — esquerda (KPIs + Receita por direto), direita (Top riscos + Sinais positivos).

**KPI tiles N3** (`{{N3_KPI_TILES}}` — 3 tiles):
- `Receita {NIVEL} · X% meta` (em vermelho quando <70%, amarelo 70-99,9%, verde ≥100%)
- `Volume · X% meta`
- `Deals · Y estagn.` (warn quando estagnação >40%)

**Card "Receita por direto · MTD vs meta"** (`{{N3_BARRAS_POR_DIRETO}}` — 1 `.bar-row` por especialista + 1 row consolidado):
```html
<div class="bar-row" style="grid-template-columns: 200px 1fr 110px;">
  <div class="lbl">{{ESP_NOME}}</div>
  <div class="track" style="height:32px;"><div class="seg fill-{{TONE}}" style="width:{{PCT}}%;{{COLOR}}">{{PCT}}%</div></div>
  <div class="total">R$ {{REAL}} / {{META}}</div>
</div>
```
Última row é `{NIVEL} consolidado` (soma agregada). `.fill-lime` para 70-100%, `.fill-bad` para <70%, verde sólido para ≥100%.

**Card "Top 3 riscos {NIVEL}"** (`{{N3_TOP_RISCOS}}` — 3 `.risk-item`s): priorização por impacto (volume × probabilidade). Origem: WBR Riscos + análise de desvios E3.

**Card "Sinais positivos"** (`{{N3_SINAIS_POSITIVOS}}` — 3 `.risk-item`s com `border-left-color:#4caf50`): WBR Recomendações executadas + ações concluídas no ciclo.

**Quando N=1** (1 especialista): omitir o card `Receita por direto` (trivial) e reorganizar layout: mover "Top riscos" + "Sinais positivos" para 2 colunas largas. Manter os 3 KPI tiles à esquerda + 1 callout adicional (síntese da operação) embaixo.

---

## Slide último · Encerramento

Posição = `7 + 3*N`. Fundo dark `var(--verde-caqui)`, layout editorial com 3 next-cards em grid.

**Head row**: bar lime + eyebrow `Encerramento · {{CICLO_LABEL}}` (lime); H2 `Próximos <em>passos</em>` (lime no `<em>`); intro `{{ENC_INTRO}}` (default `Decisões que precisam sair do ritual antes do fechamento de {{PROX_PERIODO}}.`); logo offwhite à direita.

**Next-grid 3-col** (`{{NEXT_CARDS}}`): 1 a 4 `.next-card`s. Cada decisão da Seção 4 do briefing vira um card:
```html
<div class="next-card">
  <div class="nc-num">{{NN}}</div>
  <div class="nc-title">{{TITULO_DECISAO}}</div>
  <div class="nc-meta">
    <div><div class="k">Formato</div><div class="v">{{FORMATO_BINARIO}}</div></div>
    <div><div class="k">Owner</div><div class="v">{{OWNER}}</div></div>
    <div><div class="k">Prazo</div><div class="v">{{PRAZO}}</div></div>
  </div>
  <div class="nc-risk">
    <div class="k">Sem decisão</div>
    <div class="v">{{CONSEQUENCIA}}</div>
  </div>
</div>
```

**Layout adaptativo:**
- D=1: 1 card centralizado (60% width).
- D=2: 2 cards lado a lado (cada 1fr).
- D=3: 3 cards 1fr cada (default visual).
- D=4: 4 cards (grid passa a `repeat(4, 1fr)` ou empilha 2x2 se viewport apertar).

**Coerência crítica (gatekeeper SSoT #10):** `count(NEXT_CARDS) == count(briefing.decisoes)` e títulos idênticos.

**Closing-foot**: rodapé com `<strong>Ritual de Gestão {NIVEL} {VERTICAL}{SUBNIVEL_SUFFIX}</strong>` à esquerda + `{CICLO_LABEL} · {DATA_FECHAMENTO} · Fechamento` à direita.

---

## 12. Regra de cor 3-tier (semáforo aplicado ao valor)

Para QUALQUER indicador com meta, o agente computa `pct_atingimento` e mapeia em uma de 4 classes:

| % atingimento | Classe CSS | Cor primária | Significado |
|---------------|------------|--------------|-------------|
| ≥ 100% | `.good` | `#2e7d32` (`--success-text`) | Atingiu/superou |
| 70 – 99,9% | `.warn` | `#d18000` (warning-text) | Atenção |
| < 70% | `.bad` | `#e40014` (`--error`) | Crítico |
| meta ausente / null | `.mute` | `#aeada8` (`--vc-200`) | Sem comparação |

**Fórmula:**
- `direction: maior_melhor` (default KPIs/PPIs de volume/criadas/conversão): `pct = (real / meta) × 100`
- `direction: menor_melhor` (estagnadas, lose rate): `pct = (meta / max(real, 1)) × 100`, capado a 200%

**Special-case `meta=0` + `direction: menor_melhor`** (zero-target, ex: `oportunidades_sem_atividade_planejada_funil[_seg]`):
- `real = 0` → `pct = 100%` → `.good` (verde — atingiu o ideal)
- `real >= 1` → `pct = 0%` → `.bad` (vermelho — qualquer valor >0 é desvio)

> A fórmula padrão `meta/max(real,1) × 100` produziria `0%` mesmo com `real=0` quando `meta=0` (matematicamente quebrado). O agente DEVE detectar `meta=0 AND direction=menor_melhor` e aplicar a regra special-case acima antes de cair na fórmula padrão.

**Aplicação por slide:**
- Slide 3 (Matriz): classe na `.cell` afeta `.num`. Sem dot.
- Slide 6/9/… Dashboard: classe em `.desv` (coluna Desvio). Coluna stat usa emoji 🟢🟡🔴⚪ pelo mesmo % atingimento.
- Slide 8/11/… Pipeline KPI tiles: classe em `.v`.
- Slide 12 Consolidado: classe em `.v` dos KPI tiles + `.fill-{tone}` nos bars de Receita por direto.

---

## 13. Renumeração e composição da agenda

O agente computa, em ordem:

1. `N = len(Card.apresentacao.responsaveis)`
2. `total_slides = 7 + 3*N`
3. Numerar `<section>`s sequencialmente; `data-label` recebe sufixo curto.
4. `f-num` no footer = posição zerofill 2-dig (`01`..`NN`).
5. Eyebrows dos blocos por especialista K = `Bloco {03..02+N} · …`. Slide 12 = `Bloco {03+N}`. Slide 13 (Encerramento) sem eyebrow numerado.
6. Tempo total = T_VISAO (8) + T_OPERACAO (10) + Σ T_ESP_K (15 default) + T_SINTESE (4) + T_FECHAMENTO (3) = **25 + 15*N min** (default; ajustável).

---

## 14. Anti-patterns

- **NUNCA** usar cor fora da paleta M7-2026 documentada.
- **NUNCA** organizar slides por KPI — o ritual é por especialista.
- **NUNCA** pular um especialista do Card.
- **NUNCA** calcular números — todos vêm do WBR/canonical JSON.
- **NUNCA** usar `font-weight: bold` (use 700 numérico).
- **NUNCA** usar dot/emoji de semáforo na **Matriz** (Slide 3) — apenas no Dashboard (Slide 6/9/…) na coluna stat.
- **NUNCA** quebrar a fórmula `total_slides = 7 + 3*N` — falha automática do gatekeeper de contagem.
- **NUNCA** renderizar Total da Matriz como N1 bruto — sempre soma das colunas.
- **NUNCA** ignorar `n2.{esp}.meta` quando presente no canonical JSON — usar como meta individual no Dashboard.
- **NUNCA** ignorar `oportunidades_estagnadas_funil_*_pct_ativas` quando presente — render como linha principal.
- **NUNCA** mergear cards de subníveis distintos numa mesma execução — 1 ritual = 1 card.
- **NUNCA** publicar com gatekeeper SSoT falhando (#7 rastreabilidade armadilha→WBR; #10 decisões briefing==slide encerramento; #12 tempo briefing==agenda; #15 replicação 03-Rituais byte-equal).
