# Relatorio de Acompanhamento de Acoes — {vertical} — {data_referencia}

> Gerado automaticamente por m7-controle (E4 — summarizing-actions)

## Metricas Gerais

| Metrica | Valor |
|---------|-------|
| Total de acoes ativas | {total_ativas} |
| Taxa de conclusao (ultimos 30d) | {taxa_conclusao}% |
| Acoes criticas (>7d atrasadas) | {total_criticas} |
| % de acoes criticas | {pct_criticas}% |
| Aging medio | {aging_medio}d |
| Volume em risco | R$ {volume_risco} |
| Receita em risco | R$ {receita_risco} |

---

## Acoes Criticas (requerem escalonamento)

<!-- Acoes com dias_restantes < -7. Ordenar por aging decrescente. -->

| ID | Titulo | Responsavel | Prazo | Aging | Volume | Receita |
|----|--------|-------------|-------|-------|--------|---------|
| {id} | {titulo} | {responsavel} | {data_limite} | {aging}d | R$ {volume} | R$ {receita} |

<!-- Se 0 acoes criticas: "Nenhuma acao critica neste ciclo." -->

---

## Acoes Atrasadas

<!-- Acoes com dias_restantes entre 0 e -7. Ordenar por dias_restantes crescente. -->

| ID | Titulo | Responsavel | Prazo | Aging |
|----|--------|-------------|-------|-------|
| {id} | {titulo} | {responsavel} | {data_limite} | {aging}d |

<!-- Se 0 acoes atrasadas: "Nenhuma acao atrasada neste ciclo." -->

---

## Acoes Em Dia

<!-- Acoes com dias_restantes > 0. Ordenar por dias_restantes crescente (mais proximas do prazo primeiro). -->

| ID | Titulo | Responsavel | Prazo | Dias restantes |
|----|--------|-------------|-------|----------------|
| {id} | {titulo} | {responsavel} | {data_limite} | {dias_restantes}d |

<!-- Se 0 acoes em dia: "Nenhuma acao em andamento neste ciclo." -->

---

## Eficacia das Acoes Concluidas

<!-- Acoes com status=concluida no periodo do ciclo. Cruzar com dados E2 para verificar se indicador voltou a meta. -->

| ID | Titulo | Indicador | Resultado | Eficacia |
|----|--------|-----------|-----------|----------|
| {id} | {titulo} | {indicador_impactado} | {resultado_indicador} | {eficacia} |

<!-- Eficacia: Eficaz / Parcial / Sem efeito / Dados insuficientes -->
<!-- Se 0 acoes concluidas no periodo: "Nenhuma acao concluida neste ciclo." -->

---

## Top 5 por Impacto (Volume + Receita)

<!-- As 5 acoes com maior volume + receita projetados, independente de status. -->

| ID | Titulo | Volume | Receita | Status |
|----|--------|--------|---------|--------|
| {id} | {titulo} | R$ {volume} | R$ {receita} | {status} |

---

## Hierarquia de Hotlists

<!-- Acoes com parent_id preenchido, agrupadas sob acao-pai. Omitir secao se nenhuma acao tem parent_id. -->

### {parent_id} — {titulo_pai}

| ID | Sub-acao | Responsavel | Status | Prazo |
|----|----------|-------------|--------|-------|
| {id} | {titulo} | {responsavel} | {status} | {data_limite} |

---

*Fonte: plano-de-acao.csv | Ciclo: {data_referencia} | Vertical: {vertical}*
