# Data Quality Report - {vertical} - {data}

> **Ciclo**: {YYYY-MM-DD} ({data_inicio} a {data_fim})
> **Coletado em**: {timestamp}
> **Agente**: data-collector

---

## Resumo

- **Indicadores coletados**: {coletados}/{total}
- **Qualidade geral**: {qualidade_geral}
- **Defasagem maxima**: {defasagem_max}h
- **Alertas criticos**: {n_criticos}
- **Alertas atencao**: {n_atencao}

---

## Alertas

### Criticos

<!-- Se nenhum alerta critico: "Nenhum alerta critico." -->
- **{indicator_id}**: {descricao_problema} (valor: {valor}, threshold: {threshold})

### Atencao

<!-- Se nenhum alerta atencao: "Nenhum alerta de atencao." -->
- **{indicator_id}**: {descricao} (valor: {valor}, threshold: {threshold})

### Informativos

<!-- Se nenhum informativo: "Nenhum alerta informativo." -->
- **{indicator_id}**: {descricao}

---

## Dados Coletados

| Indicador | Realizado | Meta | % Ating. | Qualidade |
|-----------|-----------|------|----------|-----------|
| {nome} | {realizado} | {meta} | {pct}% | {quality_status} |

---

## Quality Checks Executados

| Indicador | Check | Resultado | Detalhes |
|-----------|-------|-----------|----------|
| {indicator_id} | {rule} | {pass/fail} | {detalhes} |

---

## Decisao do Pipeline

<!-- Preenchido automaticamente com base na qualidade geral -->

**{qualidade_geral}**: {decisao}

- **OK**: Pipeline prossegue para E3 (analyzing-deviations)
- **Atencao**: Pipeline prossegue com ressalvas registradas acima
- **Critico**: Pipeline BLOQUEADO — resolver alertas criticos antes de avancar

---

*Gerado automaticamente pela skill collecting-data (G2.2-E2) | m7-controle*
