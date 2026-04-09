# Licoes Aprendidas — Processo G2.2 — {periodo}

> Gerado automaticamente por m7-controle (E7 — recording-lessons)
> **Periodo**: {periodo} ({data_inicio} a {data_fim})
> **Verticais analisadas**: {lista_verticais}
> **Ciclos analisados**: {n_ciclos} ({lista_datas_ciclos})
> **Rituais analisados**: {n_rituais}
> **Gerado em**: {timestamp}

---

## Resumo Executivo

<!-- 3-5 frases: principal aprendizado do mes, tendencia geral do processo G2.2, destaque positivo e negativo. Foco no PROCESSO, nao nos resultados de negocio. -->

---

## Cobertura de Fontes

| Vertical | Ciclos (E6) | Action Reports (E4) | DQ Reports (E2) | Atas (G2.3) |
|----------|-------------|---------------------|------------------|-------------|
| {vertical} | {n_ciclos} | {n_action_reports} | {n_dq_reports} | {n_atas} |

<!-- Repetir linha para cada vertical. -->

**Total**: {n_total_ciclos} ciclos, {n_total_atas} rituais, {n_gestores_n2} gestores N2 identificados nas atas

<!-- Se n_atas = 0: "⚠ Nenhuma ata de ritual encontrada para o periodo. Criterio de qualidade 'min 2 gestores N2' nao atendido." -->
<!-- Se n_gestores_n2 < 2: "⚠ Apenas {n_gestores_n2} gestor(es) N2 identificado(s) nas atas. Criterio de qualidade 'min 2 gestores N2' nao atendido." -->

---

## Licoes Aprendidas

### L1: {titulo_licao}

- **Categoria**: {O que funcionou / O que nao funcionou / O que surpreendeu / O que faltou}
- **Vertical(is)**: {verticais onde foi observada}
- **Ciclo(s)**: {datas dos ciclos com evidencia}
- **Etapa impactada**: {E2/E3/E4/E5/E6/G2.3}
- **Descricao**: {descricao detalhada do fenomeno observado}
- **Evidencia**: {artefatos especificos com dados concretos — numeros, gaps, tendencias}
- **Recorrencia**: {em quantos ciclos/rituais apareceu, ou justificativa se impacto unico}
- **Acao proposta**: {o que mudar no processo}

<!-- Repetir bloco ### para cada licao. Minimo 2 licoes. -->

---

## Propostas de Melhoria

| # | Titulo | Etapa | Tipo | Prioridade | Esforco | Origem |
|---|--------|-------|------|------------|---------|--------|
| P1 | {titulo} | {etapa} | {processo/dados/ritual/ferramenta} | {Alta/Media/Baixa} | {Baixo/Medio/Alto} | L{n} |

<!-- Repetir linha para cada proposta. -->

### P1: {titulo_proposta}

- **Descricao**: {o que mudar e por que}
- **Impacto esperado**: {qual metrica ou qualidade do processo melhora}
- **Esforco**: {Baixo/Medio/Alto} — {justificativa}
- **Responsavel sugerido**: {Performance / Gestores N2 / TI / Cowork}
- **Prazo sugerido**: {proximo ciclo / proximo mes / proximo trimestre}

<!-- Repetir bloco ### para cada proposta. -->

---

## Tendencias do Mes por Vertical

### {vertical}

#### Evolucao de Semaforo

| Indicador | {sem_1_data} | {sem_2_data} | {sem_3_data} | {sem_4_data} | Tendencia |
|-----------|--------------|--------------|--------------|--------------|-----------|
| {nome_indicador} | {cor} | {cor} | {cor} | {cor} | {Recuperacao/Deterioracao/Persistente/Oscilacao/Estavel} |

<!-- Repetir tabela para cada vertical. Ajustar numero de colunas conforme ciclos no mes. -->

#### Eficacia de Acoes

| Metrica | {sem_1_data} | {sem_2_data} | {sem_3_data} | {sem_4_data} |
|---------|--------------|--------------|--------------|--------------|
| Acoes ativas | {n} | {n} | {n} | {n} |
| % criticas | {pct}% | {pct}% | {pct}% | {pct}% |
| Taxa conclusao 30d | {pct}% | {pct}% | {pct}% | {pct}% |
| Aging medio | {n}d | {n}d | {n}d | {n}d |

#### Qualidade de Dados

| Metrica | {sem_1_data} | {sem_2_data} | {sem_3_data} | {sem_4_data} |
|---------|--------------|--------------|--------------|--------------|
| Alertas criticos | {n} | {n} | {n} | {n} |
| Indicadores com dados | {n}/{total} | {n}/{total} | {n}/{total} | {n}/{total} |

<!-- Repetir bloco ### {vertical} para cada vertical analisada. -->

---

## Feedback dos Gestores N2

<!-- Extraido das atas de rituais (G2.3). Minimo 2 gestores para atender criterio de qualidade. -->

| Gestor | Vertical | Ritual (data) | Feedback / Decisao |
|--------|----------|---------------|--------------------|
| {nome} | {vertical} | {data_ritual} | {resumo do feedback ou decisao relevante para o processo} |

<!-- Se nenhuma ata disponivel: "Nenhuma ata de ritual registrada para o periodo." -->

---

## Decisoes de Rituais — Acompanhamento

<!-- Decisoes tomadas em rituais do mes e se foram implementadas nos ciclos seguintes. -->

| Decisao | Ritual | Responsavel | Prazo | Status | Verificacao |
|---------|--------|-------------|-------|--------|-------------|
| {descricao} | {data_ritual} | {nome} | {prazo} | {implementada/pendente/parcial} | {como verificou — qual artefato/ciclo} |

<!-- Se nenhuma decisao registrada: omitir secao. -->

---

*Gerado automaticamente pela skill recording-lessons (G2.2-E7) | m7-controle*
