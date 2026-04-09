# Relatorio de Projecao - {vertical} - {data}

> **Periodo**: {periodo_display} ({data_inicio} a {data_fim})
> **Checkpoint**: {checkpoint_label}
> **Gerado em**: {timestamp}
> **Agente**: analyst
> **Dados de entrada**: dados-consolidados-{vertical}.json (E2)

---

## Resumo de Projecoes

| Indicador | Obrigatoria | Meta | Realizado | % Ating. | Projecao Base | % Meta Proj. | Classificacao |
|-----------|-------------|------|-----------|----------|---------------|-------------|---------------|
| {nome_indicador} | {sim/nao} | {meta} | {realizado} | {pct_ating}% | {projecao_base} | {pct_meta_proj}% | {classificacao} |

**Legenda**: Provavel (>=90%) | Possivel (70-89%) | Improvavel (<70%)

<!-- Apenas indicadores com projectable: true. Ordenar: obrigatoria=true primeiro -->

---

## Detalhamento por Indicador

### {nome_indicador}

- **Meta periodo**: {meta}
- **Realizado acumulado**: {realizado} ({pct_ating}% da meta)
- **Dias uteis**: {dias_decorridos}/{dias_totais} ({dias_restantes} restantes)

#### Metodos Aplicados (conforme YAML)

| Metodo | Valor Projetado | % Meta | Confianca (YAML) | Nota |
|--------|----------------|--------|-------------------|------|
| {metodo_1_do_yaml} | {valor} | {pct}% | {high/medium/low} | {nota_se_houver} |
| {metodo_2_do_yaml} | {valor} | {pct}% | {high/medium/low} | {nota_se_houver} |

<!-- Listar APENAS os metodos de projection.methods do YAML deste indicador -->
<!-- Se um metodo nao foi aplicavel: mostrar na tabela com nota explicativa -->

- **Consolidacao**: {projection.consolidation} → {projecao_final} ({pct_meta_proj}% da meta)
- **Classificacao**: {Provavel/Possivel/Improvavel}
- **Metodos utilizados**: {n_aplicados} de {n_configurados}
<!-- Se baixa_confianca: -->
- **Atencao**: Metodos aplicados ({n_aplicados}) < min_methods ({min_methods}) — baixa confianca

<!-- Se pipeline_conversion: detalhar contribuicao por estagio -->
#### Detalhe Pipeline Conversion

| Estagio | Deals | Valor Total | Rate (YAML) | P(timing) | Contribuicao |
|---------|-------|-------------|-------------|-----------|-------------|
| {estagio} | {n_deals} | {valor} | {rate} | {p_timing} | {contribuicao} |

Pipeline projetado: {soma_contribuicoes}
Realizado + Pipeline: {projecao_total}

<!-- Se lagging_indicator: detalhar lags -->
#### Detalhe Lagging Indicator

| Lag | Mes Referencia | Valor Leading | Peso (YAML) | Contribuicao |
|-----|---------------|---------------|-------------|-------------|
| {lag_months[i]}m | {mes} | {valor_ou_projecao} | {lag_weights[i]} | {contribuicao} |

Projecao derivada: {soma_contribuicoes}

#### Gap para Meta

- **Gap absoluto**: {gap_abs}
- **Gap percentual**: {gap_pct}%
- **Ritmo necessario**: {ritmo_necessario}/dia util
- **Ritmo atual**: {ritmo_atual}/dia util
- **Fator de aceleracao**: {fator_aceleracao}x
<!-- Se fator > 2: -->
- **Alerta**: Aceleracao significativa necessaria para atingir meta

#### Cenarios

<!-- Gerar APENAS se Card define projecao.cenarios para este indicador -->

| Cenario | Valor | % Meta |
|---------|-------|--------|
| Otimista (P90) | {p90} | {pct_p90}% |
| Base (mediana) | {base} | {pct_base}% |
| Pessimista (P10) | {p10} | {pct_p10}% |

<!-- Se Card NAO define cenarios: omitir esta secao -->

<!-- Repetir bloco ### para cada indicador com projectable: true -->

---

## Indicadores com Risco de Nao Atingimento

| Indicador | Projecao Base | % Meta | Gap | Ritmo Necessario | Fator Aceleracao |
|-----------|--------------|--------|-----|-----------------|-----------------|
| {nome} | {projecao} | {pct}% | {gap} | {ritmo}/dia util | {fator}x |

<!-- Lista apenas indicadores classificados como "Improvavel" -->
<!-- Se nenhum indicador Improvavel: "Nenhum indicador com risco de nao atingimento identificado." -->

---

## Dependencias Cruzadas

| Indicador | Depende De | Via Metodo | Status |
|-----------|-----------|-----------|--------|
| {receita} | {volume} | lagging_indicator | {projecao usada / historico usado} |
| {volume} | {oportunidades_ativas} | pipeline_conversion | {dados E2 carregados} |

<!-- Documentar a cadeia de dependencias e como foram resolvidas -->

---

## Anomalias e Observacoes

| Indicador | Flag | Descricao |
|-----------|------|-----------|
| {nome} | {flag} | {descricao_anomalia} |

<!-- Flags possiveis: projecao_negativa, projecao_excessiva, baixa_confianca, alta_dispersao, metodo_nao_aplicavel -->
<!-- Se nenhuma anomalia: "Nenhuma anomalia detectada." -->

---

*Gerado automaticamente pela skill projecting-results (G2.2-E5) | m7-controle v5.0.0*
