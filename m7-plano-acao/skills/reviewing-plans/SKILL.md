---
name: reviewing-plans
description: >-
  Analisa os Planos de Acao M7 em dois modos: briefing diario (o que fazer hoje)
  e relatorio de KPIs (saude geral do periodo).
  Use when the user asks to review action plans, check what's due today, or see KPI reports.

  <example>
  Context: usuario quer saber o que fazer hoje
  user: "o que tenho pra hoje?"
  assistant: gera briefing do dia com itens criticos e follow-ups
  </example>

  <example>
  Context: usuario pede relatorio mensal
  user: "me da os KPIs de marco"
  assistant: calcula metricas de melhorias para 2026-03
  </example>
user-invocable: true
---

# Reviewing Plans

Leitura e analise do CSV de acoes de melhoria (`plano-de-acao.csv`). Dois modos de operacao:

| Modo | Trigger | Periodo default | Leitura/Escrita |
|------|---------|-----------------|-----------------|
| **Plano do dia** | `dia`, data especifica, "o que fazer hoje" | Hoje (`YYYY-MM-DD`) | Read-only |
| **KPIs do periodo** | `kpis`, "relatorio", "saude" | Mes corrente (`YYYY-MM`) | Read-only |

Se o usuario fornece apenas uma data sem modo explicito, inferir pelo formato:
- `YYYY-MM-DD` → Plano do dia
- `YYYY-MM` → KPIs do periodo

## Pre-requisitos

1. Ler [../managing-plans/references/csv-schemas.md](../managing-plans/references/csv-schemas.md) para schema, enums e o **caminho base** do CSV
2. Localizar `plano-de-acao.csv` via Glob no caminho base definido em csv-schemas.md
3. Ler o CSV completo
4. Computar status derivado em runtime (NUNCA armazenado):
   - `atrasada` = `data_limite < hoje AND status IN (pendente, em_andamento)`

---

## Modo 1 — Plano do dia

**Input**: data de referencia (default: hoje)

### Passo 1: Classificar itens em 3 secoes

Filtrar itens do CSV e agrupar nas secoes abaixo. Excluir itens com status terminal (`concluida`, `cancelada`).

**Secao 1 — Criticos e atrasados**
- Melhorias com `prioridade = critica` E status ativo (`pendente`, `em_andamento`)
- Tudo que esta atrasado (status derivado)
- Ordenar: criticos primeiro, depois por data mais antiga

**Secao 2 — Follow-ups de hoje**
- Melhorias com `data_followup = {data_referencia}`

**Secao 3 — Proximos 7 dias**
- Itens com datas entre `data_referencia + 1` e `data_referencia + 7`
- Agrupar por dia
- Incluir: follow-ups e prazos de melhorias (`data_limite`)

### Passo 2: Calcular KPIs rapidos

Exibir no topo do briefing:

| KPI | Calculo |
|-----|---------|
| Abertas | Melhorias com status ativo (nao terminal) |
| Atrasadas | Total de itens com status derivado `atrasada` |

### Passo 3: Formatar output

```markdown
# Plano do Dia — {data_referencia}

> Abertas: {N} | Atrasadas: {N}

## 1. Criticos e Atrasados

{lista ou "Nenhum item."}

## 2. Follow-ups de Hoje

{lista ou "Nenhum item."}

## 3. Proximos 7 Dias

### {dia_semana}, {data}
{lista}

### {dia_semana}, {data}
{lista}
```

**Regras de exibicao**:
- Secoes vazias: mostrar "Nenhum item." (NUNCA omitir a secao)
- Cada item mostra: `[ID] Titulo — Responsavel (status, prioridade)`
- Melhorias com `volume` ou `receita`: incluir valor

---

## Modo 2 — KPIs do periodo

**Input**: periodo `YYYY-MM` (default: mes corrente)

### Passo 1: Calcular metricas

| KPI | Calculo |
|-----|---------|
| Total abertas | status IN (backlog, pendente, em_andamento) |
| Concluidas no periodo | `data_conclusao` dentro do `YYYY-MM` |
| Taxa de conclusao | concluidas / (concluidas + abertas) |
| Atrasadas | status derivado `atrasada` |
| Aging medio (dias) | media de `hoje - data_cadastro` para abertas |
| Criticas abertas | `prioridade = critica` E status ativo |
| Volume em risco | soma de `volume` das atrasadas (parsear numeros) |
| Receita em risco | soma de `receita` das atrasadas (parsear `R$ NNN`) |

### Passo 2: Regras de calculo

- Percentuais: sempre exibir com denominador — ex: `75% (3/4)`
- Divisao por zero: exibir `N/A (0 itens)` em vez de erro
- Volume/receita: parsear `R$ NNN`, `R$ NNk/mes`, `R$ NN-NNk/mes` (usar media do range)

### Passo 3: Formatar output

```markdown
# KPIs — {YYYY-MM}

## Melhorias
| KPI | Valor |
|-----|-------|
| ... | ... |

**Detalhamento atrasadas:**
{lista de atrasadas com ID, titulo, responsavel, dias de atraso}
```

---

## Anti-Patterns

- NUNCA escrever no CSV — esta skill e 100% read-only
- NUNCA omitir itens atrasados do briefing
- NUNCA incluir concluidos/cancelados no plano do dia
- NUNCA armazenar `atrasada` como status — e computado em runtime

## References

- [../managing-plans/references/csv-schemas.md](../managing-plans/references/csv-schemas.md) — schema completo, enums, convencoes
