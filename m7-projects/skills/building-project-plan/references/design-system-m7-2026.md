# Design System M7-2026

Tokens, fontes, componentes visuais e regras de uso aplicados em todos os
10 HTMLs gerados pela skill. Fonte canonica: o projeto-modelo H1-02
em [plano-projeto/](file:///Users/bchiaramonti/Library/CloudStorage/OneDrive-MULTI7CAPITALCONSULTORIALTDA/plan-estrategico/pe-26-30/iniciativas/H1-02_Playbook-de-Processos/plano-projeto/).

## Indice

1. [Tokens de cor](#tokens-de-cor)
2. [Tipografia](#tipografia)
3. [Logo](#logo)
4. [Componentes compartilhados](#componentes-compartilhados)
5. [Componentes especificos por artefato](#componentes-especificos-por-artefato)
6. [Regras de aplicacao](#regras-de-aplicacao)

---

## Tokens de cor

CSS `:root` aplicado em todos os 10 HTMLs:

```css
:root {
  --verde-caqui: #424135;     /* Cor primaria — fundos hero, page-header, fase rows */
  --lime: #eef77c;            /* Accent decorativo — NUNCA usar em texto sobre fundo claro */
  --off-white: #fffdef;       /* Background base + texto sobre caqui */
  --cinza-700: #3d3d3d;       /* Texto principal sobre fundo claro */
  --cinza-400: #9a9a8e;       /* Texto secundario / labels / metadata */
  --cinza-200: #d9d9c8;       /* Borders, separadores, fundos suaves */
  --cinza-100: #f0f0e4;       /* Backgrounds neutros, chips */
  --accent-green: #7ab648;    /* Scope yes, mitigation positive */
  --accent-red: #c0392b;      /* Scope no, riscos criticos */
  --radius: 12px;             /* Border-radius padrao */
}
```

**Tokens estendidos (apenas em alguns artefatos):**

| Token | Uso | Artefato |
|---|---|---|
| `--verde-medio: #4f4e3c` | Variant em swim-lane bars | roadmap-marcos |
| `--verde-claro: #79755c` | Texto secundario em swim-lane | roadmap-marcos |
| `--verde-caqui-200/100/50` | Scale de variantes | roadmap-marcos |
| `--blue: #0066ff`, `--purple: #8B5CF6`, `--amber: #F59E0B`, `--teal: #14B8A6` | Cores de frente no swim-lane (.bar.v-blue, .bar.v-purple, etc.) | roadmap-marcos |
| `--red: #c0392b`, `--orange: #e67e22`, `--yellow: #f1c40f`, `--green: #7ab648` | Heatmap de riscos | riscos |
| `--discovery: #5a8f5a`, `--validacao: #8b6914`, `--checkin: #7a8a9a`, `--status: #b8860b`, `--handoff: #c45d3e` | Cores por tipo de evento no calendario | calendario |

## Tipografia

```css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

body {
  font-family: 'Inter', sans-serif;
  background: var(--off-white);
  color: var(--verde-caqui);
}
```

**Pesos usados:**
- `300` — subtitle, paragrafos extensos (estrela-guia)
- `400` — h1, h2 (titulos)
- `500` — values em meta, labels destacados
- `600` — section-titles, badges, h3 menores
- `700` — page-header `.num`, stat-card `.val`, riscos `.risk-id`

**Hierarquia tipografica observada (H1-02):**

| Elemento | Tamanho | Peso |
|---|---|---|
| Hero h1 | 42px | 400 |
| Page-header h1 | 32px | 400 |
| Page-header `.num` | 60px | 700 |
| h2 (cards) | 18-19px | 400 |
| h3 (section-title) | 13-14px | 600 (uppercase) |
| h4 (sub-itens) | 14px | 400 |
| Body text | 13-15px | 400 |
| Metadata / labels | 10-12px | 600 (uppercase 1.5px letter-spacing) |

## Logo

Dois assets disponiveis em `templates/assets/`:

| Asset | Uso | Quando |
|---|---|---|
| `m7-logo-offwhite.b64` (4KB) | Logo claro | Fundo escuro/caqui (hero, page-header) |
| `m7-logo-dark.b64` (5KB) | Logo escuro | Fundo claro (footer opcional) |

Os arquivos `.b64` contem string base64 puro (sem cabecalho `data:image`).
A skill embute o logo inline:

```html
<img src="data:image/png;base64,{LOGO_B64}" alt="M7" class="hero-logo">
```

Tamanhos padrao:
- Hero (landing): height 72px, opacity 0.92
- Page-header (artefatos): height 56px, opacity 0.85

## Componentes compartilhados

Presentes em **todos** os 9 artefatos:

### Topbar de navegacao
```html
<div class="topbar">
  <a href="prev.html">← Prev Label</a>
  <span class="title">{project_label}</span>
  <a href="next.html">Next Label →</a>
</div>
```
Background `--verde-caqui`, links `--cinza-200`, hover `--lime`.

### Page-header
```html
<div class="page-header">
  <div class="page-header-left">
    <div class="num">01</div>
    <h1>Titulo do Artefato</h1>
  </div>
  <img src="..." class="logo">
</div>
```
Background `--verde-caqui`, num em `rgba(238,247,124,0.2)` (lime suave), logo a direita.

### Footer
```html
<div class="footer">
  M7 Investimentos — Equipe de Performance — {project_label} — {Mes Ano}
</div>
```
Background transparente, border-top `--cinza-200`, texto `--cinza-400`.

### Container
```html
<div class="container">
  <!-- conteudo -->
</div>
```
Width maximo varia por artefato (960px - 1400px), padding 48px 32px 80px.

## Componentes especificos por artefato

| Artefato | Componentes principais |
|---|---|
| **Landing** | `.hero` (gradiente caqui), `.estrela`, `.nav-grid` com `.nav-card` |
| **01 Contexto** | `.estrela-box`, `.card`, `.scope-grid` (`.scope-yes` / `.scope-no`), `.quote-box`, `.dep-table`, `.badge-in` / `.badge-out` |
| **02 EAP** | `.legend` com `.legend-swatch`, `.wbs` (org-chart CSS com pseudo-elements `::before`/`::after`), `.node.l0/l1/l2/l3`, `.wp-table`, `.note-box` |
| **03 Roadmap** | `.roadmap` swim-lane com `.months-row`, `.lane.milestones` no topo (ticks alternados `.tick.top`/`.tick.bottom` sobre `.rail` central, `.tick.gate` para majors), `.lane`s de frente com `.bar` (chevron via clip-path, apenas `.title`), `.lane.gov` com `.qr` badges, `.marcos-table` (colunas `.col-tipo`/`.col-marco`/`.col-data`/`.col-wbs`/`.col-desc`) com `.tipo-dot.gate` para majors |
| **04 OKRs** | `.okr-block` com `.obj-card` (caqui) + `.kr-list` com `.kr` (`.kr-num` / `.kr-content` / `.kr-target`), `.cadence-box` |
| **05 Recursos** | `.team-grid` com `.team-card.lead`, `.role-badge .badge-lider/.badge-dono`, `.block-chip.trans`, `.alloc-table` com `.cell-active/.cell-trans/.cell-plan/.cell-close`, `.dep-table`, `.invest-card` |
| **06 Comunicacao** | `.ritual-grid` com `.ritual-card.highlight`, `.raci-table` com `.raci-r/.raci-a/.raci-c/.raci-i`, `.channel-grid` |
| **07 Riscos** | `.matrix-container`, `.heat-map` com `.heat-grid` 3x3 (`.heat-{prob}-{imp}` 9 variants), `.risk-dot`, `.risk-legend` com `.risk-item` (`.risk-id.crit/.high/.medium`), `.mitigation`, `.risk-detail` table com `.sev-crit/.sev-high/.sev-med` |
| **08 Cronograma** | `.stats` (4 stat-card), `.filter-bar` com `.filter-btn`, `.wh-table` com `.phase-row/.phase-row.close/.acao-row/.etapa-row`, `.wbs-code/.wbs-code.sub`, `.entreg/.entreg-etapa`, JS `filterRows()` |
| **09 Calendario** | `.stats`, `.legend`, `.filter-bar`, `.cal-grid` 7-col mensal com `.cal-day/.weekend/.empty/.today`, `.evt.{type}` (7 type variants), `.summary-table` com `.type-badge`, JS `renderCalendars()/renderSummary()/filterEvts()` |

## Regras de aplicacao

### Invariantes
1. **Fonte unica:** Inter (com fallback sans-serif)
2. **Background base:** `--off-white` (nunca branco puro `#fff` no body — apenas em cards)
3. **Texto principal:** `--verde-caqui` em fundos claros, `--off-white` em fundos caqui
4. **Lime nunca em texto sobre fundo claro:** apenas decorativo (estrela ::before, dot, gradient suave em hero ::after)
5. **Border-radius:** sempre `var(--radius)` = 12px para cards e tabelas
6. **Font-weight 700:** apenas para `.num` (page-header), `.val` (stats), badges/IDs criticos

### Anti-patterns a evitar
- Usar lime como cor de texto em fundo claro (baixo contraste)
- Misturar fontes (Inter so)
- Border-radius < 8px ou > 14px (quebra ritmo visual)
- Text-align justify (Inter nao trabalha bem com isso em viewport pequeno)
- Mais de 3 niveis de heading por artefato

### Acessibilidade
- Contraste WCAG AA garantido para texto principal (caqui em off-white = 9.5:1)
- Lime nunca isolado como info critica (sempre acompanhado de texto/icone)
- Todos os interativos (botoes, links) tem hover state visivel
- Logo tem alt="M7"

## Convenção: HTML self-contained

Cada um dos 10 HTMLs e **completamente auto-suficiente** — todo o CSS vive
inline dentro de `<style>` no `<head>`. Nada de CSS externo, nada de JS
externo (exceto Google Fonts via @import). Isso garante:

- Funciona offline
- Pode ser enviado por email/Slack como anexo unico
- Imprime corretamente
- Sem dependencia de servidor

A duplicacao de CSS entre artefatos e **intencional** — cada arquivo
declara seus proprios tokens + componentes. Maintainability vem de:
- Templates centralizados em `templates/`
- Tokens documentados aqui
- Renderer (`render_html.py`) coordenando substituicoes
