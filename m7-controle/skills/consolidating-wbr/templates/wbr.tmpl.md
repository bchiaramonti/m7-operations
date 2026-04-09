# WBR - {vertical} - {YYYY-MM-DD}

> **Periodo**: {periodo_display} ({data_inicio} a {data_fim})
> **Checkpoint**: {checkpoint_label}
> **Gerado em**: {timestamp}
> **Agente**: analyst
> **Qualidade dos dados**: {status_qualidade}

---

## 1. Resumo Executivo

<!-- <=150 palavras. Estrutura: semaforo geral, destaque positivo, risco principal, projecao consolidada -->

{resumo_executivo}

---

## 1.5 Painel de Indicadores

<!-- Tabela UNICA com TODOS os indicadores do Card de Performance. Derivada de kpi_references[].
     Esta tabela e a fonte de dados para o Slide 2 (Matriz) do m7-ritual-gestao.
     NUNCA omitir um indicador do Card. Se sem dados, exibir "—". -->

| Tipo | Indicador | Meta | Realizado | Gap | % Ating. | Status | N2: {esp1_nome} | N2: {esp2_nome} |
|------|-----------|------|-----------|-----|----------|--------|-----------------|-----------------|
| {KPI/PPI} | {nome_legivel} | {meta} | {realizado} | {gap_abs} | {pct}% | {status_emoji} | {val_esp1} | {val_esp2} |

<!-- Regras:
     - Tipo: KPI para papel=kpi_principal, PPI para papel=ppi_*
     - Colunas N2: uma por especialista em metadata.responsaveis do Card
     - Ordenacao: KPIs primeiro (vermelhos por gap, amarelos, verdes), depois PPIs
     - PPIs sem meta: "—" em Meta, Gap, % Ating., status cinza
     - Nomes legiveis: "Receita Seguros" nao "receita_seguros_mensal"
     - Unidades: BRL → R$ K/M, ratio → %, count → inteiro -->

---

## 2. Desvios e Causa-Raiz

### Semaforo

| Indicador | Realizado | Meta | % Ating. | Status |
|-----------|-----------|------|----------|--------|
| {nome} | {realizado} | {meta} | {pct}% | {Verde/Amarelo/Vermelho} |

### Desvios Criticos (Vermelho)

#### {nome_indicador}

- **Realizado**: {realizado} | **Meta**: {meta} | **Gap**: {gap_abs} ({gap_pct}%)
- **Fenomeno**: {o_que} | {quando} | {onde} | {quem} | {tendencia}
- **Causa-raiz provavel**: {hipotese} (confianca: {nivel})
- **Indicadores correlacionados**: {lista}

<!-- Repetir para cada Vermelho, ordenado por gap absoluto -->

### Desvios de Atencao (Amarelo)

- **{nome}**: {realizado} vs {meta} ({pct}%) — Tendencia: {tendencia}

### Destaques Positivos (Verde)

| Indicador | % Ating. | Destaque |
|-----------|----------|----------|
| {nome} | {pct}% | {destaque_se_aplicavel} |

---

## 3. Acoes

### Metricas Agregadas

| Metrica | Valor |
|---------|-------|
| Total acoes ativas | {total} |
| Taxa de conclusao | {pct_conclusao}% |
| Aging medio | {aging_medio} dias |
| Acoes atrasadas | {n_atrasadas} |

### Acoes Criticas e Atrasadas

| ID | Acao | Responsavel | Prazo | Status | Aging |
|----|------|-------------|-------|--------|-------|
| {id} | {descricao} | {responsavel} | {prazo} | {status} | {aging}d |

<!-- Max 10 acoes. Se houver mais: "Alem destas, N acoes adicionais estao em andamento." -->

### Top Acoes por Impacto

- **{acao}**: Impacto estimado de {valor} em {indicador}

---

## 4. Projecoes

| Indicador | Meta Periodo | Projecao Base | Projecao Otimista | Projecao Pessimista | Classificacao |
|-----------|-------------|---------------|-------------------|---------------------|---------------|
| {nome} | {meta} | {base} | {otimista} | {pessimista} | {classificacao} |

### Indicadores em Risco

<!-- Detalhar apenas "Improvavel" e "Em risco" -->

- **{nome}** ({classificacao}): Gap de {gap} para atingir meta. Ritmo necessario: {ritmo}

### Tendencia Consolidada

- No ritmo: {n} indicadores ({pct}%)
- Recuperavel: {n} indicadores ({pct}%)
- Em risco: {n} indicadores ({pct}%)
- Improvavel: {n} indicadores ({pct}%)

---

## 5. Recomendacoes

### Contramedidas Novas

1. **{recomendacao}** — {justificativa} — Prioridade: {Alta/Media/Baixa}
   - Responsavel sugerido: {nome} | Prazo: {prazo}

### Escalonamentos para N1

1. **Escalonar {tema} para {decisor}**: {justificativa}

### Ajustes de Meta

1. **{indicador}**: Meta atual {meta}, projecao {projecao}. Causa: {causa_estrutural}

<!-- Se nao ha recomendacoes em uma categoria: "Nenhum item nesta categoria." -->

---

**Fonte**: ClickHouse + Bitrix24 | **Vertical**: {vertical} | **Periodo**: {data_inicio} a {data_fim}
**Qualidade dos dados**: {status_qualidade}
<!-- Se houver alertas de atencao de E2: -->
**Ressalvas**: {lista_alertas_atencao}

*Gerado automaticamente pela skill consolidating-wbr (G2.2-E6) | m7-controle*
