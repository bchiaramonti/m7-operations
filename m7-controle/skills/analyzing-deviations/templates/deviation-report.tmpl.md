# Relatorio de Desvios e Causa-Raiz - {vertical} - {data}

> **Ciclo**: {YYYY-MM-DD} ({data_inicio} a {data_fim})
> **Gerado em**: {timestamp}
> **Agente**: analyst
> **Dados de entrada**: dados-consolidados-{vertical}.json (E2)

---

## Semaforo Geral

| Status | Qtd | Indicadores |
|--------|-----|-------------|
| Verde (>=95%) | {n_verde} | {lista_verdes} |
| Amarelo (80-94%) | {n_amarelo} | {lista_amarelos} |
| Vermelho (<80%) | {n_vermelho} | {lista_vermelhos} |

---

## Desvios Criticos (Vermelho)

### {nome_indicador}

**Realizado**: {realizado} | **Meta**: {meta} | **Gap**: {gap_abs} ({gap_pct}%)

#### Analise de Fenomeno

| Dimensao | Analise |
|----------|---------|
| **O QUE** | {descricao_desvio} |
| **QUANDO** | {evolucao_temporal} |
| **ONDE** | {segmento_concentrado} |
| **QUEM** | {responsaveis_concentrados} |
| **TENDENCIA** | {direcao_tendencia} |

#### Estratificacao — {dimensao_principal}

| {dimensao} | Realizado | Meta | Gap | % do Gap Total |
|------------|-----------|------|-----|----------------|
| {segmento_1} | {real} | {meta} | {gap} | {pct_gap}% |
| {segmento_2} | {real} | {meta} | {gap} | {pct_gap}% |
| Outros | {real} | {meta} | {gap} | {pct_gap}% |

#### Causa-Raiz

**Causa-raiz provavel**: {hipotese}
- **Confianca**: {alta/media/baixa}
- **Evidencias**: {lista_evidencias}
- **Indicadores correlacionados**: {lista_correlacionados_com_status}

<!-- Repetir bloco ### para cada indicador Vermelho -->

---

## Desvios de Atencao (Amarelo)

### {nome_indicador}

- **Realizado**: {realizado} | **Meta**: {meta} | **% Ating.**: {pct_ating}%
- **Tendencia**: {melhorando/piorando/estavel}
- **Contexto**: {analysis_guide_resumo}
<!-- Se estava Verde no ciclo anterior: -->
- **Alerta**: Indicador era Verde no ciclo anterior — monitorar piora

<!-- Repetir bloco ### para cada indicador Amarelo -->

---

## Destaques Positivos (Verde)

| Indicador | % Ating. | Destaque |
|-----------|----------|----------|
| {nome} | {pct}% | {destaque_se_aplicavel} |

<!-- Destaques: "Recuperou de Vermelho", "Superou meta em >10%", etc. -->

---

## Mapa de Correlacoes

| Indicador Vermelho | Indicadores Correlacionados | Status | Hipotese Compartilhada |
|--------------------|---------------------------|--------|------------------------|
| {ind_vermelho} | {ind_correlacionado} | {Verde/Amarelo/Vermelho} | {hipotese_se_aplicavel} |

---

*Gerado automaticamente pela skill analyzing-deviations (G2.2-E3) | m7-controle*
