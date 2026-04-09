# Guia de Geracao HTML — WBR Narrativo Visual

> Referencia para o agente analyst ao gerar o output HTML do WBR Narrativo.
> O analyst NAO usa template engine. Ele escreve o HTML diretamente via Write tool,
> seguindo este guia como receita de construcao.

---

## Visao Geral

O WBR Narrativo HTML e o terceiro output de E6, complementando o WBR Estruturado (.md) e o WBR Narrativo (.md). Ele apresenta os mesmos dados com visualizacoes SVG inline, cards KPI e layout visual M7-2026.

**Fonte de verdade**: Sempre o WBR Estruturado (`wbr/wbr-{vertical}-{data}.md`). Nenhum numero pode ser inventado ou arredondado diferentemente.

**Output**: `wbr/wbr-narrativo-{vertical}-{data}.html`

---

## Estrutura do Documento

O HTML segue esta arquitetura fixa:

```
<!DOCTYPE html> + <head> (CSS pre-baked do template)
<body>
  <div class="page">
    COVER              — Logo, titulo, periodo, coordenador
    PARTE 1: PANORAMA  — Manchete, KPI Cards, Semaforo
    PARTE 2: DESVIOS   — N secoes com SVG charts + tabelas + callouts
    PARTE 3: PROJECOES — Chart de cenarios + callout
    PARTE 4: ACOES     — Timeline + Destaques positivos
    CONCLUSAO          — Manchete final, KPI resumo, Decisao Critica, Anomalias
    FOOTER             — Metadata
  </div>
</body>
```

---

## Processo de Geracao

### Passo 1 — Copiar CSS do Template

O analyst deve usar Read tool para ler `templates/wbr-narrativo.tmpl.html` e copiar TODO o bloco `<head>...</head>` (incluindo `<style>` com ~500 linhas de CSS). Este CSS ja esta validado pelo design system M7-2026 e NAO deve ser alterado.

O CSS inclui:
- `@font-face` para TWK Everett (Regular 400, Medium 500, Bold 700)
- CSS variables em `:root` com todos os design tokens M7-2026
- Classes para todos os componentes: `.cover`, `.manchete`, `.kpi-row`, `.semaforo-grid`, `.chart-container`, `.callout`, `.timeline`, `.highlight-grid`, `.decisao-critica`, etc.
- `@media print` para impressao

### Passo 2 — Montar o HTML com Dados Reais

Substituir cada `{{placeholder}}` do template com dados reais do WBR Estruturado. Nao usar Handlebars/Mustache — escrever HTML final diretamente.

### Passo 3 — Gerar SVGs Inline

Para cada analise visual, gerar SVG inline seguindo as receitas abaixo.

### Passo 4 — Validar Numeros

Conferir que TODOS os numeros no HTML correspondem exatamente ao WBR Estruturado.

---

## Mapeamento de Dados

### Cover

| Placeholder | Fonte |
|-------------|-------|
| `{{vertical}}` | Nome da vertical (ex: "Consorcios") |
| `{{semana_label}}` | Label do checkpoint (ex: "Marco 2026, semana 4 (MTD)") |
| `{{periodo_range}}` | Periodo de dados (ex: "01/03 a 23/03/2026") |
| `{{coordenador}}` | Coordenador da vertical |

### Manchete

| Placeholder | Fonte |
|-------------|-------|
| `{{manchete_status_tag}}` | Classificacao geral: "META SUPERADA", "EM RISCO", "ATENCAO NECESSARIA" |
| `{{manchete_texto}}` | Texto da manchete do WBR Narrativo (secao Manchete) |

### KPI Cards

Repetir 3-5 cards com os indicadores-chave. Cada card tem:

| Campo | Descricao | Exemplo |
|-------|-----------|---------|
| `class` | `kpi-card verde` / `vermelho` / `amarelo` / `azul` / `neutro` | `kpi-card verde` |
| `.kpi-value` | Valor principal formatado | `R$ 6,85M` |
| `.kpi-label` | Nome do indicador (uppercase) | `VOLUME REALIZADO` |
| `.kpi-sub` | Contexto comparativo | `Meta: R$ 6,5M (+5%)` |

**Regra de cor**: Verde se >=95% meta, Amarelo se 80-94%, Vermelho se <80%, Azul para informativo, Neutro para contexto.

### Semaforo Grid

Grid de 3 colunas com todos os indicadores. Cada card:

| Campo | Descricao |
|-------|-----------|
| `class` | `semaforo-card card-verde` / `card-vermelho` / `card-amarelo` |
| `.indicator-name` | Nome curto (uppercase) |
| `.indicator-value` | Valor principal com `style="color:var(--verde)"` etc. |
| `.indicator-meta` | "Meta: X \| Y%" |
| `.indicator-status` | `<span class="badge badge-verde">Verde</span>` |

**Exemplo concreto (copiar e adaptar)**:

```html
<div class="semaforo-grid">
  <!-- Card Verde (KPI >=95% meta) -->
  <div class="semaforo-card card-verde">
    <div class="indicator-name">VOLUME</div>
    <div class="indicator-value" style="color:var(--verde);">R$ 6,85M</div>
    <div class="indicator-meta">Meta: R$ 6,5M | 105,31%</div>
    <div class="indicator-status"><span class="badge badge-verde">Verde</span></div>
  </div>
  <!-- Card Vermelho (KPI <80% meta) -->
  <div class="semaforo-card card-vermelho">
    <div class="indicator-name">RECEITA</div>
    <div class="indicator-value" style="color:var(--vermelho);">R$ 52,1K</div>
    <div class="indicator-meta">Meta: R$ 89,3K | 58,3%</div>
    <div class="indicator-status"><span class="badge badge-vermelho">Vermelho</span></div>
  </div>
  <!-- Card Amarelo (KPI 80-94% meta) -->
  <div class="semaforo-card card-amarelo">
    <div class="indicator-name">CONVERSAO</div>
    <div class="indicator-value" style="color:var(--amarelo);">25,0%</div>
    <div class="indicator-meta">Meta: 30,0% | 83,3%</div>
    <div class="indicator-status"><span class="badge badge-amarelo">Atencao</span></div>
  </div>
  <!-- Card Cinza (PPI sem meta formal) -->
  <div class="semaforo-card card-cinza">
    <div class="indicator-name">PIPELINE</div>
    <div class="indicator-value" style="color:var(--text-muted);">45 ops</div>
    <div class="indicator-meta">PPI — sem meta formal</div>
    <div class="indicator-status"><span class="badge badge-cinza">Contexto</span></div>
  </div>
</div>
```

**Regras obrigatorias do semaforo**:
- Um `semaforo-card` por indicador do Painel (Secao 1.5)
- Classe do card DEVE corresponder ao status: `card-verde` (>=95%), `card-amarelo` (80-94%), `card-vermelho` (<80%), `card-cinza` (PPI sem meta)
- O `style="color:var(--X);"` no `.indicator-value` DEVE usar a mesma cor do status do card (ex: `card-verde` → `color:var(--verde)`)
- Formato de `.indicator-meta`: `Meta: {valor} | {pct}%` para KPIs, `PPI — sem meta formal` para PPIs
- Texto do badge: "Verde", "Vermelho", "Atencao", "Contexto"
- Grid adapta automaticamente: 3 colunas. Se >6 indicadores, os cards quebram em linhas adicionais

### Desvios (Repetiveis)

Para cada indicador com desvio relevante (Vermelho obrigatorio, Amarelo se relevante), criar uma secao com:
1. `.section-title` numerada
2. Paragrafo de contexto (`.content p`)
3. `.chart-container` com SVG inline
4. `<table>` de dados
5. `.callout` com interpretacao + `.insight`

### Projecoes

Secao unica com chart de cenarios (P10/Base/P90) e callout interpretativo.

### Acoes

Timeline de acoes + highlight grid de destaques positivos.

### Conclusao

Manchete final + KPI cards resumo + Decisao Critica + tabela de anomalias.

---

## Receitas de Graficos — D3.js Inline

O template inclui `<script src="https://d3js.org/d3.v7.min.js"></script>` no `<head>`. Cada grafico e um `<div class="chart-container">` com um `<div id="...">` unico, seguido de um `<script>` que usa D3 para criar o SVG dentro do container.

**Regras gerais**:
- Cada `<script>` e envolvido em IIFE `(function(){ ... })()` para evitar poluicao de escopo global
- Excecao: `renderProjectionChart()` e funcao nomeada compartilhada entre graficos de projecao
- Cada container DEVE ter um `id` unico (ex: `chart-volume`, `chart-receita-1`, `chart-funnel`)
- Cores usam hex direto no JS (nao `var()`) — a regra CSS `svg text { font-family: ... }` aplica tipografia automaticamente
- Formatacao brasileira: usar `.replace(".",",")` para separador decimal
- Barras com valor zero: `Math.max(x(d.realizado), 3)` garante traco visual minimo

### 1. Horizontal Bar Chart (Volume/Receita por Pessoa)

**Uso**: Comparar realizado vs meta por especialista/assessor. Usar sempre que houver breakdown por pessoa (>=2 pessoas).

```html
<div class="chart-container">
  <div class="chart-title">Comparativo de Volume por Especialista</div>
  <div id="chart-volume"></div>
  <div class="chart-caption">Meta individual: R$ 3.250M</div>
</div>
<script>
(function() {
  // DADOS: substituir com valores reais do WBR Estruturado
  const data = [
    { nome: "Douglas Silva", realizado: 6845000, meta: 3250000, pct: 210.6, status: "verde" },
    { nome: "Tereza Bernardo", realizado: 0, meta: 3250000, pct: 0, status: "vermelho" }
  ];
  const colors = { verde: "#006600", amarelo: "#d4a017", vermelho: "#b8000f" };
  const margin = { top: 20, right: 120, bottom: 40, left: 140 };
  const width = 760 - margin.left - margin.right;
  const height = data.length * 60 + margin.top + margin.bottom;

  const svg = d3.select("#chart-volume").append("svg")
    .attr("width", "100%")
    .attr("viewBox", `0 0 760 ${height}`)
    .append("g").attr("transform", `translate(${margin.left},${margin.top})`);

  const x = d3.scaleLinear()
    .domain([0, d3.max(data, d => Math.max(d.realizado, d.meta) * 1.15)])
    .range([0, width]);

  const y = d3.scaleBand()
    .domain(data.map(d => d.nome))
    .range([0, data.length * 60])
    .padding(0.35);

  // Grid lines verticais
  svg.selectAll(".grid-line")
    .data(x.ticks(5)).enter().append("line")
    .attr("x1", d => x(d)).attr("x2", d => x(d))
    .attr("y1", 0).attr("y2", data.length * 60)
    .attr("stroke", "#d0d0cc").attr("stroke-width", 1);

  // Barras
  svg.selectAll(".bar").data(data).enter().append("rect")
    .attr("x", 0).attr("y", d => y(d.nome))
    .attr("width", d => Math.max(x(d.realizado), 3))
    .attr("height", y.bandwidth())
    .attr("rx", 4).attr("fill", d => colors[d.status]).attr("opacity", 0.85);

  // Labels de valor nas barras
  svg.selectAll(".bar-label").data(data).enter().append("text")
    .attr("x", d => Math.max(x(d.realizado), 3) + 8)
    .attr("y", d => y(d.nome) + y.bandwidth() / 2 + 5)
    .attr("font-size", "13px").attr("font-weight", 700)
    .attr("fill", d => colors[d.status])
    .text(d => `R$ ${(d.realizado/1e6).toFixed(3).replace(".",",")}M (${d.pct.toFixed(1).replace(".",",")}%)`);

  // Linhas de meta (tracejadas)
  svg.selectAll(".meta-line").data(data).enter().append("line")
    .attr("x1", d => x(d.meta)).attr("x2", d => x(d.meta))
    .attr("y1", d => y(d.nome) - 4).attr("y2", d => y(d.nome) + y.bandwidth() + 4)
    .attr("stroke", "#424135").attr("stroke-width", 2.5)
    .attr("stroke-dasharray", "6,3");

  // Labels do eixo Y (nomes)
  svg.selectAll(".y-label").data(data).enter().append("text")
    .attr("x", -8).attr("y", d => y(d.nome) + y.bandwidth() / 2 + 5)
    .attr("text-anchor", "end").attr("font-size", "13px")
    .attr("font-weight", 600).attr("fill", "#2d2d24")
    .text(d => d.nome);

  // Eixo X (valores)
  svg.append("g")
    .attr("transform", `translate(0,${data.length * 60})`)
    .call(d3.axisBottom(x).ticks(5).tickFormat(d => `R$ ${(d/1e6).toFixed(1).replace(".",",")}M`))
    .selectAll("text").attr("fill", "#79755c").attr("font-size", "11px");
})();
</script>
```

**Cores da barra** (campo `status` no array `data`):
- `"verde"` (>=95% meta): `#006600`
- `"amarelo"` (80-94% meta): `#d4a017`
- `"vermelho"` (<80% meta): `#b8000f`

### 2. Donut Chart (Composicao %)

**Uso**: Mostrar participacao percentual (composicao de receita, concentracao de volume, etc.).

```html
<div class="chart-container">
  <div class="chart-title">Composicao de Volume por Especialista</div>
  <div id="chart-donut" style="text-align:center;"></div>
  <div class="chart-caption">Participacao percentual no volume total</div>
</div>
<script>
(function() {
  // DADOS: substituir com valores reais
  const data = [
    { nome: "Douglas Silva", valor: 6845000, pct: 100 },
    { nome: "Tereza Bernardo", valor: 0, pct: 0 }
  ];
  const colors = ["#006600", "#b8000f", "#d4a017", "#004db3", "#79755c"];
  const width = 280, height = 280, radius = 110, innerRadius = 60;

  const svg = d3.select("#chart-donut").append("svg")
    .attr("viewBox", `0 0 ${width} ${height}`)
    .style("max-width", "280px").style("display", "block").style("margin", "0 auto")
    .append("g").attr("transform", `translate(${width/2},${height/2})`);

  const pie = d3.pie().value(d => d.valor).sort(null);
  const arc = d3.arc().innerRadius(innerRadius).outerRadius(radius);

  // Fatias (filtra zeros para evitar arcos vazios)
  svg.selectAll("path").data(pie(data.filter(d => d.valor > 0))).enter()
    .append("path").attr("d", arc)
    .attr("fill", (d, i) => colors[i]).attr("opacity", 0.85);

  // Texto central
  svg.append("text").attr("text-anchor", "middle").attr("y", -6)
    .attr("font-size", "24px").attr("font-weight", 700).attr("fill", "#424135")
    .text("105%");
  svg.append("text").attr("text-anchor", "middle").attr("y", 14)
    .attr("font-size", "12px").attr("fill", "#79755c")
    .text("da meta");

  // Legenda abaixo
  const legend = d3.select("#chart-donut").append("div")
    .style("display", "flex").style("justify-content", "center")
    .style("gap", "16px").style("margin-top", "12px").style("font-size", "12px");
  data.forEach((d, i) => {
    legend.append("span").html(
      `<span style="display:inline-block;width:10px;height:10px;background:${colors[i]};border-radius:2px;margin-right:4px;vertical-align:middle;"></span> ${d.nome} (${d.pct}%)`
    );
  });
})();
</script>
```

### 3. Horizontal Bar Chart Simples (Atingimento %)

**Uso**: Comparar % de atingimento entre pessoas/itens com barras de progresso.

```html
<div class="chart-container">
  <div class="chart-title">Atingimento por Especialista</div>
  <div id="chart-atingimento"></div>
</div>
<script>
(function() {
  // DADOS: substituir com valores reais
  const data = [
    { nome: "Douglas Silva", pct: 210.6, status: "verde" },
    { nome: "Tereza Bernardo", pct: 0, status: "vermelho" }
  ];
  const colors = { verde: "#006600", amarelo: "#d4a017", vermelho: "#b8000f" };
  const margin = { top: 10, right: 80, bottom: 10, left: 120 };
  const barH = 20, gap = 30;
  const width = 400, height = data.length * (barH + gap) + margin.top + margin.bottom;
  const trackW = 200;

  const svg = d3.select("#chart-atingimento").append("svg")
    .attr("viewBox", `0 0 ${width} ${height}`)
    .attr("width", "100%")
    .append("g").attr("transform", `translate(${margin.left},${margin.top})`);

  data.forEach((d, i) => {
    const yPos = i * (barH + gap);
    // Nome
    svg.append("text").attr("x", -8).attr("y", yPos + barH/2 + 5)
      .attr("text-anchor", "end").attr("font-size", "11px")
      .attr("font-weight", 600).attr("fill", "#2d2d2d").text(d.nome);
    // Track (fundo cinza)
    svg.append("rect").attr("x", 0).attr("y", yPos)
      .attr("width", trackW).attr("height", barH).attr("rx", 4).attr("fill", "#f0f0ea");
    // Barra de progresso
    svg.append("rect").attr("x", 0).attr("y", yPos)
      .attr("width", Math.min(d.pct / 100 * trackW, trackW))
      .attr("height", barH).attr("rx", 4).attr("fill", colors[d.status]);
    // Valor percentual
    svg.append("text").attr("x", trackW + 10).attr("y", yPos + barH/2 + 4)
      .attr("font-size", "11px").attr("font-weight", 700).attr("fill", colors[d.status])
      .text(`${d.pct.toFixed(1).replace(".",",")}%`);
  });
})();
</script>
```

### 4. Funnel / Pipeline Chart

**Uso**: Mostrar fluxo do pipeline CRM com gargalos destacados.

```html
<div class="chart-container">
  <div class="chart-title">Saude do Pipeline — Funil CRM</div>
  <div id="chart-funnel"></div>
</div>
<script>
(function() {
  // DADOS: substituir com valores reais do pipeline
  const stages = [
    { label: "CRIADAS", count: 50, valor: "R$ 44,5M", cor: "#004db3", bg: "#e3f2fd" },
    { label: "ATIVAS", count: 45, valor: "R$ 46,7M", cor: "#004db3", bg: "#e3f2fd" },
    { label: "ESTAGNADAS", count: 20, valor: "R$ 12,3M", cor: "#b8000f", bg: "#ffebee", risco: true },
    { label: "CONVERTIDAS", count: 12, valor: "R$ 6,8M", cor: "#006600", bg: "#e8f5e9" }
  ];
  const boxW = 160, boxH = 80, gapX = 30, arrowW = 20;
  const totalW = stages.length * boxW + (stages.length - 1) * (gapX + arrowW);
  const height = 120;

  const svg = d3.select("#chart-funnel").append("svg")
    .attr("viewBox", `0 0 ${totalW + 40} ${height}`)
    .attr("width", "100%")
    .append("g").attr("transform", "translate(20,10)");

  // Marker de seta
  svg.append("defs").append("marker")
    .attr("id", "arrow-funnel").attr("viewBox", "0 0 10 10")
    .attr("refX", 9).attr("refY", 5)
    .attr("markerWidth", 8).attr("markerHeight", 8).attr("orient", "auto")
    .append("path").attr("d", "M 0 0 L 10 5 L 0 10 z").attr("fill", "#d0d0cc");

  stages.forEach((s, i) => {
    const xOff = i * (boxW + gapX + arrowW);
    // Box
    svg.append("rect").attr("x", xOff).attr("y", 0)
      .attr("width", boxW).attr("height", boxH).attr("rx", 8)
      .attr("fill", s.bg).attr("stroke", s.cor)
      .attr("stroke-width", s.risco ? 2.5 : 1.5);
    // Contagem
    svg.append("text").attr("x", xOff + boxW/2).attr("y", 30)
      .attr("text-anchor", "middle").attr("font-size", "28px")
      .attr("font-weight", 700).attr("fill", s.cor).text(s.count);
    // Label
    svg.append("text").attr("x", xOff + boxW/2).attr("y", 48)
      .attr("text-anchor", "middle").attr("font-size", "11px")
      .attr("font-weight", 600).attr("fill", s.cor).text(s.label);
    // Valor
    svg.append("text").attr("x", xOff + boxW/2).attr("y", 66)
      .attr("text-anchor", "middle").attr("font-size", "10px")
      .attr("fill", "#79755c").text(s.valor);
    // Seta para o proximo estagio
    if (i < stages.length - 1) {
      const ax = xOff + boxW + 4;
      svg.append("line").attr("x1", ax).attr("x2", ax + gapX + arrowW - 8)
        .attr("y1", boxH/2).attr("y2", boxH/2)
        .attr("stroke", "#d0d0cc").attr("stroke-width", 2)
        .attr("marker-end", "url(#arrow-funnel)");
    }
  });
})();
</script>
```

### 5. Cenarios de Projecao (P10 / Base / P90)

**Uso**: Comparar cenarios pessimista, base e otimista para cada indicador. Sempre usar para todos os indicadores com projecao.

**Layout**: Usar `.chart-grid` (CSS `grid-template-columns: 1fr 1fr`) para colocar 2 indicadores lado a lado. Se >2, empilhar em linhas adicionais.

```html
<div class="chart-container">
  <div class="chart-grid">
    <div>
      <div class="chart-title">Volume Consorcio Mensal</div>
      <div id="chart-proj-volume"></div>
      <p style="text-align:center; font-size:12px; color:#79755c; margin:4px 0 0;">Meta: R$ 6,5M</p>
    </div>
    <div>
      <div class="chart-title">Receita Consorcio Mensal</div>
      <div id="chart-proj-receita"></div>
      <p style="text-align:center; font-size:12px; color:#79755c; margin:4px 0 0;">Meta: R$ 89,3K</p>
    </div>
  </div>
  <div class="chart-caption">Cenarios P10 (Pessimista), Base (Mediana), P90 (Otimista)</div>
</div>
<script>
// Funcao reutilizavel para graficos de projecao (compartilhada entre indicadores)
function renderProjectionChart(containerId, scenarios, meta, formatFn) {
  const margin = { top: 30, right: 20, bottom: 50, left: 50 };
  const width = 350, height = 220;
  const innerW = width - margin.left - margin.right;
  const innerH = height - margin.top - margin.bottom;
  const barColors = { P10: "#004db3", Base: "#006600", P90: "#006600" };
  const barOpacities = { P10: 0.9, Base: 1, P90: 0.7 };

  const svg = d3.select(containerId).append("svg")
    .attr("viewBox", `0 0 ${width} ${height}`)
    .attr("width", "100%")
    .append("g").attr("transform", `translate(${margin.left},${margin.top})`);

  const maxVal = d3.max(scenarios, d => d.valor) * 1.15;
  const y = d3.scaleLinear().domain([0, maxVal]).range([innerH, 0]);
  const x = d3.scaleBand().domain(scenarios.map(d => d.label))
    .range([0, innerW]).padding(0.4);

  // Linha de meta (tracejada)
  svg.append("line").attr("x1", 0).attr("x2", innerW)
    .attr("y1", y(meta)).attr("y2", y(meta))
    .attr("stroke", "#8a6d00").attr("stroke-width", 2).attr("stroke-dasharray", "4,4");
  svg.append("text").attr("x", innerW + 4).attr("y", y(meta) + 4)
    .attr("font-size", "10px").attr("fill", "#8a6d00").attr("font-weight", 700).text("META");

  // Barras verticais
  svg.selectAll(".bar").data(scenarios).enter().append("rect")
    .attr("x", d => x(d.label)).attr("y", d => y(d.valor))
    .attr("width", x.bandwidth())
    .attr("height", d => innerH - y(d.valor))
    .attr("rx", 3).attr("fill", d => barColors[d.label])
    .attr("opacity", d => barOpacities[d.label]);

  // Valores nas barras
  svg.selectAll(".val").data(scenarios).enter().append("text")
    .attr("x", d => x(d.label) + x.bandwidth()/2)
    .attr("y", d => {
      const barH = innerH - y(d.valor);
      return barH > 30 ? y(d.valor) + barH/2 + 5 : y(d.valor) - 8;
    })
    .attr("text-anchor", "middle").attr("font-size", "12px")
    .attr("font-weight", 700)
    .attr("fill", d => (innerH - y(d.valor)) > 30 ? "white" : barColors[d.label])
    .text(d => formatFn(d.valor));

  // Labels do eixo X (cenario)
  svg.selectAll(".x-label").data(scenarios).enter().append("text")
    .attr("x", d => x(d.label) + x.bandwidth()/2)
    .attr("y", innerH + 18).attr("text-anchor", "middle")
    .attr("font-size", "11px").attr("font-weight", 700).attr("fill", "#2d2d24")
    .text(d => d.label);

  // Labels de percentual
  svg.selectAll(".pct").data(scenarios).enter().append("text")
    .attr("x", d => x(d.label) + x.bandwidth()/2)
    .attr("y", innerH + 32).attr("text-anchor", "middle")
    .attr("font-size", "10px").attr("fill", "#79755c")
    .text(d => `${d.pct.toFixed(1).replace(".",",")}%`);
}

// DADOS: substituir com valores reais das projecoes (E5)
renderProjectionChart("#chart-proj-volume",
  [{ label: "P10", valor: 7990000, pct: 122.9 },
   { label: "Base", valor: 9554000, pct: 147.0 },
   { label: "P90", valor: 11120000, pct: 171.1 }],
  6500000, v => `R$ ${(v/1e6).toFixed(2).replace(".",",")}M`
);

renderProjectionChart("#chart-proj-receita",
  [{ label: "P10", valor: 88400, pct: 98.9 },
   { label: "Base", valor: 109900, pct: 123.1 },
   { label: "P90", valor: 124900, pct: 139.9 }],
  89300, v => `R$ ${(v/1e3).toFixed(1).replace(".",",")}K`
);
</script>
```

**Classificacao dos badges** (usar como callout abaixo do grafico, nao dentro do SVG):

| Classificacao | Badge class |
|---------------|-------------|
| PROVAVEL | `badge-verde` |
| POSSIVEL | `badge-amarelo` |
| IMPROVAVEL | `badge-vermelho` |

---

## Design Tokens (NAO Alterar)

Estas cores e valores ja estao no CSS do template. D3 gera SVGs no DOM e a regra CSS `svg text { font-family: "twkEverett", Arial, Helvetica, sans-serif }` aplica a tipografia automaticamente — nao e necessario declarar font-family no codigo D3.

### Cores de Status (usar hex direto no JS)
| Uso | CSS var | Hex (usar em D3) |
|-----|---------|-----------------|
| Verde texto/borda | `--verde` | `#006600` |
| Verde fundo | `--verde-bg` | `#e8f5e9` |
| Vermelho texto/borda | `--vermelho` | `#b8000f` |
| Vermelho fundo | `--vermelho-bg` | `#ffebee` |
| Amarelo texto | `--amarelo` | `#8a6d00` |
| Amarelo fill (barras) | — | `#d4a017` |
| Amarelo fundo | `--amarelo-bg` | `#fff8e1` |
| Azul texto/borda | `--azul` | `#004db3` |
| Azul fundo | `--azul-bg` | `#e3f2fd` |

### Cores Neutras
| Uso | Hex |
|-----|-----|
| Texto primario | `#2d2d24` |
| Texto muted | `#79755c` |
| Bordas/grid | `#d0d0cc` |
| Background track | `#f0f0ea` |
| Caqui (headings) | `#424135` |

### Tipografia (aplicada automaticamente pelo CSS)
| Elemento | font-size | font-weight | fill |
|----------|-----------|-------------|------|
| Axis labels | 11px | 400 | `#79755c` |
| Bar labels (nome) | 13px | 600 | `#2d2d24` |
| Bar values | 13px | 700 | cor do status |
| Meta labels | 10px | 600-700 | `#424135` ou `#8a6d00` |
| Annotations | 10px | 400 | `#79755c` |
| Chart section title | 14px | 700 | `#424135` |
| Center donut value | 24px | 700 | `#424135` |
| Center donut label | 12px | 400 | `#79755c` |

---

## Componentes HTML — Receitas Rapidas

### Callout Padrao
```html
<div class="callout">
  <div class="callout-title">{titulo}</div>
  <p>{texto}</p>
  <div class="insight">
    <p><strong>{label}:</strong> {texto_insight}</p>
  </div>
</div>
```

### Callout de Alerta (vermelho)
```html
<div class="callout callout-alert">
  <div class="callout-title">{titulo}</div>
  <p>{texto}</p>
</div>
```

### Callout Positivo (verde)
```html
<div class="callout callout-verde">
  <div class="callout-title">{titulo}</div>
  <p>{texto}</p>
</div>
```

### Badge de Status
```html
<span class="badge badge-verde">Verde</span>
<span class="badge badge-vermelho">Vermelho</span>
<span class="badge badge-amarelo">Atencao</span>
```

### Timeline Item
```html
<div class="timeline-item">
  <div class="timeline-date">{data}<br><span style="font-size:12px;color:var(--text-muted);font-weight:400;">{sublabel}</span></div>
  <div class="timeline-dot" style="background:var(--{cor});"></div>
  <div class="timeline-content">
    <strong>{titulo_acao}</strong>
    <p>{descricao}</p>
  </div>
</div>
```

**Cores do dot**: `vermelho` = urgente, `amarelo` = proximo prazo, `azul` = planejado, `insight-border` = continuo.

### Decisao Critica
```html
<div class="decisao-critica">
  <div class="decisao-tag">Decisao Critica</div>
  <p>{texto}</p>
  <p class="decisao-meta">
    <strong>Proprietario:</strong> {owner} &nbsp;&nbsp;|&nbsp;&nbsp; <strong>Prazo:</strong> {prazo}
  </p>
</div>
```

---

## Decisoes de Conteudo

### Quais graficos gerar?

O analyst deve decidir quais graficos sao relevantes com base nos dados disponiveis:

| Situacao | Tipo de Chart (D3) | Quando usar |
|----------|-------------------|-------------|
| Indicador por assessor/especialista | Horizontal Bar Chart | Sempre que houver breakdown por pessoa (>=2 pessoas) |
| Composicao percentual | Donut Chart | Quando a composicao revela insight (concentracao, dependencia) |
| Atingimento comparativo | Bar Simples com track | Para comparar % entre itens |
| Pipeline CRM | Funnel Chart | Quando ha dados de pipeline (criadas — ativas — estagnadas) |
| Projecoes de meta | Cenarios P10/Base/P90 | Sempre (para todos os indicadores com projecao) |

**Regra**: Pelo menos 2 graficos, maximo 5. Priorizar os que revelam a causa-raiz dos desvios.

### Quantas secoes de desvio?

- **Obrigatorio**: Uma secao para cada indicador Vermelho
- **Recomendado**: Uma secao para pipeline/funil se dados de PPI disponiveis
- **Opcional**: Secao para Amarelo relevante (se tendencia de piora)

### Numeracao de secoes

Sequencial continua: 1 (Manchete), 2 (Semaforo), 3+ (Desvios), N (Projecoes), N+1 (Acoes), N+2 (Destaques).

---

## Checklist de Validacao Final

Antes de salvar o HTML, o analyst deve verificar:

- [ ] CSS copiado integralmente do template (nenhuma alteracao)
- [ ] `<script src="https://d3js.org/d3.v7.min.js"></script>` presente no `<head>`
- [ ] Logo base64 presente no cover (copiado do template)
- [ ] TODOS os numeros conferem com WBR Estruturado
- [ ] Classificacoes de semaforo identicas ao estruturado
- [ ] Semaforo segue exemplo concreto (card-verde/vermelho/amarelo/cinza com badge)
- [ ] Projecoes e cenarios identicos ao E5
- [ ] Nenhuma cor fora da paleta M7-2026
- [ ] Cada chart container `<div>` tem `id` unico
- [ ] Cada `<script>` de chart usa IIFE (exceto `renderProjectionChart`)
- [ ] Callouts com insights conectando dados — acao
- [ ] Decisao critica com owner + prazo definidos
- [ ] Footer com timestamp e sources corretos
- [ ] Arquivo salvo como `wbr/wbr-narrativo-{vertical}-{data}.html`

---

*Referencia criada em 2026-03-24 | Skill: consolidating-wbr (E6) | Plugin: m7-controle*
