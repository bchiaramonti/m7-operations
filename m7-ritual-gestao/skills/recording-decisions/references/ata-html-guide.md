# Guia de Geracao HTML — Ata de Ritual N2

> Referencia para o agente `decision-recorder` ao gerar a versao visual (HTML) da ata de ritual.

## Principio Geral

O CSS do template `ata-ritual.tmpl.html` e **imutavel** — ja validado como M7-2026 Design System Score A. O agente deve:

1. **Copiar o bloco `<head>` inteiro** (CSS + font-faces + design tokens) sem alteracao
2. **Substituir os placeholders `{{...}}`** no `<body>` com dados reais da ata MD
3. **Montar os componentes visuais** conforme o mapeamento abaixo
4. **Validar** que todos os numeros no HTML sao identicos a ata MD

> **NAO gerar graficos SVG.** A ata e dados estruturados (decisoes, tabelas, timelines), nao dados analiticos. Charts sao exclusivos do WBR.

## Mapeamento de Secoes da Ata para Componentes HTML

| Secao da Ata MD | Componente HTML | Classes CSS |
|-----------------|-----------------|-------------|
| Informacoes Gerais | Cover | `.cover`, `.logo`, `.meta` |
| Decisoes | Timeline | `.timeline`, `.timeline-item`, `.timeline-dot`, `.timeline-date`, `.timeline-content` |
| Contramedidas Definidas | Tabela + Badges | `table`, `th`, `td`, `.badge`, `.badge-{cor}` |
| Acoes Atualizadas | Tabela | `table`, `th`, `td` |
| Duplicatas Detectadas | Callout | `.callout` (omitir secao se nenhuma) |
| Escalonamentos para N1 | Callout Alert | `.callout-alert`, `.decisao-critica` |
| Proximos Passos | Timeline | `.timeline`, `.timeline-item` |
| Resumo Quantitativo | KPI Cards | `.kpi-row`, `.kpi-card` |

## Regras de Cores

### Badges de Prioridade (Contramedidas)

| Prioridade | Classe CSS | Cor |
|------------|-----------|-----|
| Critica | `.badge-vermelho` | `var(--vermelho)` bg `var(--vermelho-bg)` |
| Alta | `.badge-amarelo` | `var(--amarelo)` bg `var(--amarelo-bg)` |
| Media | `.badge-azul` | `var(--azul)` bg `var(--azul-bg)` |
| Baixa | `.badge-cinza` | `#757575` bg `#f0f0ea` |

### Timeline Dots

| Tipo | Cor do dot | Uso |
|------|-----------|-----|
| Decisao (D-001...) | `var(--azul)` | Secao Decisoes |
| Proximo Passo | `var(--caqui)` | Secao Proximos Passos |
| Escalonamento | `var(--vermelho)` | Itens escalados para N1 |

### KPI Cards (Resumo Quantitativo)

| Metrica | Classe de cor |
|---------|--------------|
| Decisoes registradas | `.neutro` (caqui) |
| Contramedidas novas | `.verde` |
| Acoes atualizadas | `.azul` |
| Duplicatas detectadas | `.amarelo` se > 0, `.neutro` se 0 |
| Escalonamentos | `.vermelho` se > 0, `.neutro` se 0 |

## Estrutura do HTML

### Cover

```html
<div class="cover">
  <div class="logo"><img src="data:image/png;base64,..." alt="M7"></div>
  <h1>Ata do Ritual N2</h1>
  <h2>{{vertical}} — {{data}}</h2>
  <div class="meta">
    <strong>M7 Investimentos</strong> — Equipe de Performance<br>
    Participantes: {{participantes}}<br>
    Duracao: {{duracao}} &nbsp;|&nbsp; WBR: {{wbr_referencia}}
  </div>
</div>
```

### Decisoes (Timeline)

```html
<div class="timeline">
  <div class="timeline-item">
    <div class="timeline-date">D-001</div>
    <div class="timeline-dot" style="background:var(--azul);"></div>
    <div class="timeline-content">
      <strong>{{decisao_titulo}}</strong>
      <p>Responsavel: {{responsavel}} &nbsp;|&nbsp; Prazo: {{prazo}}</p>
    </div>
  </div>
  <!-- repetir para cada decisao -->
</div>
```

### Contramedidas (Tabela com Badges)

```html
<table>
  <tr>
    <th>ID</th><th>Titulo</th><th>Indicador</th>
    <th>Responsavel</th><th>Prazo</th><th>Prioridade</th>
    <th>Volume</th><th>Receita</th><th>Status</th>
  </tr>
  <tr>
    <td>{{id}}</td>
    <td>{{titulo}}</td>
    <td>{{indicador}}</td>
    <td>{{responsavel}}</td>
    <td>{{prazo}}</td>
    <td><span class="badge badge-{{prioridade_class}}">{{prioridade}}</span></td>
    <td>{{volume}}</td>
    <td>{{receita}}</td>
    <td><span class="badge badge-azul">{{status}}</span></td>
  </tr>
</table>
```

### Escalonamentos (Callout Alert + Decisao Critica)

Se houver escalonamentos para N1:

```html
<div class="callout callout-alert">
  <div class="callout-title">Escalonamentos para N1</div>
  <p>{{item_escalonamento}}</p>
</div>
```

Se houver decisao critica que demanda acao urgente:

```html
<div class="decisao-critica">
  <div class="decisao-tag">Escalonamento Critico</div>
  <p>{{descricao}}</p>
  <p class="decisao-meta">
    <strong>Responsavel:</strong> {{owner}} &nbsp;|&nbsp; <strong>Prazo:</strong> {{prazo}}
  </p>
</div>
```

### KPI Cards (Resumo Quantitativo)

```html
<div class="kpi-row">
  <div class="kpi-card neutro">
    <div class="kpi-value">{{total_decisoes}}</div>
    <div class="kpi-label">Decisoes</div>
  </div>
  <div class="kpi-card verde">
    <div class="kpi-value">{{total_novas}}</div>
    <div class="kpi-label">Contramedidas Novas</div>
  </div>
  <div class="kpi-card azul">
    <div class="kpi-value">{{total_atualizadas}}</div>
    <div class="kpi-label">Acoes Atualizadas</div>
  </div>
  <!-- duplicatas e escalonamentos: usar .amarelo/.vermelho se > 0 -->
</div>
```

### Footer

```html
<div class="footer">
  <strong>Ata do Ritual N2 — {{vertical}} — {{data}}</strong><br>
  M7 Investimentos &nbsp;|&nbsp; Equipe de Performance &nbsp;|&nbsp; Pipeline G2.3 (E5)<br>
  Referencia: {{wbr_referencia}}<br>
  Gerado em {{timestamp}} pelo agente decision-recorder
</div>
```

## Checklist de Validacao (obrigatorio antes de salvar HTML)

- [ ] Bloco `<head>` copiado integralmente do template (CSS imutavel)
- [ ] Logo M7 presente como base64 no cover
- [ ] Todas as decisoes da ata MD presentes no HTML
- [ ] Todas as contramedidas com badges de prioridade corretos
- [ ] Numeros do resumo quantitativo identicos a ata MD
- [ ] Nenhum placeholder `{{...}}` remanescente no HTML final
- [ ] Font-family = "twkEverett" em todo o documento
- [ ] Escalonamentos com `.callout-alert` ou `.decisao-critica` (se houver)
- [ ] Secoes vazias omitidas ou com texto "Nenhum item nesta secao"
