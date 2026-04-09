---
name: projecting-results
description: >-
  G2.2-E5: Projeta atingimento de meta usando metodos configurados por indicador
  (definidos nos YAMLs da Biblioteca de Indicadores). Resolve dependencias cruzadas
  (ex: receita depende da projecao de volume), aplica pipeline_conversion com stage
  rates do YAML, lagging_indicator com lag weights, e consolida projecao via regras
  do YAML. Classifica probabilidade de atingimento (Provavel/Possivel/Improvavel)
  e calcula gap para meta. Use when the pipeline advances to E5 after action tracking
  (E4), when /m7-controle:next reaches E5, or when /m7-controle:run-weekly executes
  the projection step.

  <example>
  Context: E4 concluido, pipeline avanca para projecao
  user: "/m7-controle:next"
  assistant: Invoca analyst para calcular projecoes YAML-driven e classificar probabilidade de atingimento
  </example>

  <example>
  Context: Usuario quer projetar resultados de uma vertical
  user: "Projeta os resultados de Investimentos para esse mes"
  assistant: Le Card + YAMLs de indicadores, resolve dependencias, aplica metodos configurados e gera relatorio
  </example>
user-invocable: false
---

# Projecting Results — Projecao de Resultados (E5)

> "Nao basta saber onde estamos. Precisa saber onde vamos chegar."

Esta skill calcula projecoes de atingimento de meta usando **metodos configurados por indicador** nos YAMLs da Biblioteca de Indicadores. Os metodos NAO sao hardcoded — cada YAML define quais metodos aplicar, seus parametros e regras de consolidacao. O Card define quais projecoes sao obrigatorias e quais geram cenarios.

> **REGRA DE HANDOFF**: Ao invocar o agente analyst, NAO passe valores de dados no texto do prompt. Passe APENAS caminhos de arquivos (vertical, cycle folder, paths dos artefatos). O analyst deve usar Read tool para carregar os dados dos arquivos em disco.

## Dependencias Internas

- [references/projection-methodology.md](references/projection-methodology.md) — Detalhamento dos metodos, formulas, resolucao de dependencias e regras de consolidacao
- [templates/projection-report.tmpl.md](templates/projection-report.tmpl.md) — Template do Relatorio de Projecao
- Agent `analyst` — Executor da projecao (invocado automaticamente)
- Output de E2: `dados/dados-consolidados-{vertical}.json` (na pasta do ciclo)

> **Resolucao de caminhos**: Os campos `projection`, `meta`, `frequency` e `analysis_guide` vem dos YAMLs da Biblioteca de Indicadores no repositorio do usuario. Localizar via `Glob('**/indicators/_index.yaml')` ou `Glob('**/{vertical}/*.yaml')` na Biblioteca. O campo `projecao` (obrigatoria, metodo_preferido, cenarios) vem do Card de Performance da vertical.

## Pre-requisitos (Entry Criteria)

- E4 concluido (verificar CICLO.md)
- Dados consolidados disponiveis em `dados/dados-consolidados-{vertical}.json` (na pasta do ciclo)
- Biblioteca de Indicadores acessivel com campo `projection` nos YAMLs
- Card de Performance acessivel com campo `projecao` nos kpi_references

## Workflow

### Fase 1 — Preparar: Ler Configuracao e Resolver Dependencias

1. **Ler Card de Performance** da vertical → campo `kpi_references[]`
2. **Identificar indicadores projetaveis**:
   - Para cada kpi_reference, ler o YAML do indicador na Biblioteca de Indicadores
   - Verificar campo `projection.projectable`: se `false` → pular (snapshot/contexto)
   - Verificar campo `projecao.obrigatoria` no Card: `true` = DEVE aparecer no WBR
3. **Carregar configuracao de metodos** de cada indicador projetavel:
   - `projection.methods[]` — lista de metodos com parametros
   - `projection.consolidation` — regra de consolidacao (ex: `median_confident`)
   - `projection.min_methods` — minimo de metodos para consolidacao confiavel
4. **Resolver ordem de execucao por dependencia**:
   - Se um metodo referencia `parameters.source_indicator` ou `parameters.leading_indicator` de outro indicador projetavel → projetar o dependido PRIMEIRO
   - Exemplo tipico: `volume` (usa `pipeline_conversion` com source=`oportunidades_ativas`) → depois `receita` (usa `lagging_indicator` com leading=`volume`)
   - Se o source_indicator tem `projectable: false`, usar dados de E2 diretamente (nao precisa projetar)
5. **Calcular parametros temporais** usando o periodo e granularidade do CICLO.md:
   - `dias_uteis_totais`: total de dias uteis do PERIODO COMPLETO (ex: 22 dias uteis em marco)
   - `dias_uteis_decorridos`: dias uteis do 1o dia do periodo ate a data do checkpoint (inclusive)
   - `dias_uteis_restantes`: dias_uteis_totais - dias_uteis_decorridos
   - `dias_calendario_restantes`: ultimo dia do periodo - data do checkpoint
   - NOTA: Estes parametros sao do PERIODO, nao da semana. O checkpoint (granularidade) define apenas quando o pipeline roda, nao o horizonte de projecao.
6. **Ler dados consolidados** de E2 para cada indicador

**Output Fase 1:** Lista ordenada de indicadores com metodos configurados, parametros do YAML e dados carregados.

### Fase 2 — Calcular Projecoes (Metodos do YAML)

Para cada indicador **na ordem resolvida na Fase 1**, aplicar APENAS os metodos listados em `projection.methods`:

#### Metodo: `run_rate_linear`

```
projecao = (realizado_acumulado / dias_uteis_decorridos) x dias_uteis_totais
```

- **Aplicabilidade**: serie temporal com pelo menos 1 ponto no periodo
- **Confianca**: usar `confidence` do YAML (tipicamente `high`)
- Se `dias_uteis_decorridos < 5`: flag `baixa_confianca` (amostra insuficiente)

#### Metodo: `trend_exponential`

Holt-Winters com suavizacao exponencial dupla (nivel + tendencia):

```
nivel_t = alpha * Y_t + (1 - alpha) * (nivel_{t-1} + tendencia_{t-1})
tendencia_t = beta * (nivel_t - nivel_{t-1}) + (1 - beta) * tendencia_{t-1}
projecao_{t+h} = nivel_t + h * tendencia_t
```

- **Parametros do YAML**: `parameters.min_periods` (minimo de periodos historicos), `parameters.alpha` (default 0.3 se ausente)
- `beta` default: 0.1
- **Aplicabilidade**: serie com >= `min_periods` periodos historicos
- Se `analysis_guide` do indicador indica sazonalidade: ajustar pelo fator sazonal

#### Metodo: `pipeline_conversion`

Projeta valor futuro com base nos deals ativos do pipeline CRM, usando taxas de conversao e timing por estagio definidas no YAML:

```
Para cada deal ativo (dados de E2, source_indicator):
  prob_conversao = stage_conversion_rates[estagio_atual]
  dias_restantes_mes = dias_calendario_restantes_no_periodo
  prob_timing = max(0, 1 - stage_duration_days[estagio_atual] / dias_restantes_mes)
  contribuicao = deal.valor × prob_conversao × prob_timing

pipeline_projetado = sum(contribuicao de todos deals ativos)
projecao_total = realizado_acumulado + pipeline_projetado
```

- **Parametros do YAML**:
  - `parameters.source_indicator` — indicador de E2 com dados de deals ativos (ex: `oportunidades_ativas_funil`)
  - `parameters.stage_conversion_rates` — dict {estagio: probabilidade 0-1}
  - `parameters.stage_duration_days` — dict {estagio: dias medios para fechar}
- **P(timing)**: penaliza deals em estagios iniciais que provavelmente nao fecham no periodo. Um deal em "prospeccao" (45 dias) com 8 dias restantes tem P(timing) = max(0, 1 - 45/8) = 0 (nao contribui). Um deal em "cotas_alocadas" (3 dias) com 8 dias restantes tem P(timing) = max(0, 1 - 3/8) = 0.625.
- **NUNCA invente rates** — usar APENAS os valores do YAML. Sao estimativas iniciais calibraveis apos 2-3 ciclos.
- Se source_indicator nao tem dados em E2: metodo nao aplicavel, registrar justificativa

#### Metodo: `lagging_indicator`

Projeta indicador derivado (ex: receita) com base na projecao de um indicador lider (ex: volume) e pesos de defasagem:

```
projecao = sum(
  valor_leading_mes_N × lag_weights[i]
  para i in range(len(lag_months))
)
```

Onde `valor_leading_mes_N`:
- Para `lag_months[0]` (mes atual): usar a PROJECAO calculada no passo anterior (dependencia cruzada)
- Para `lag_months[i]` (meses anteriores): usar o REALIZADO HISTORICO do mes (current_month - lag_months[i])

- **Parametros do YAML**:
  - `parameters.leading_indicator` — indicador lider cuja projecao/historico e usado
  - `parameters.lag_months` — lista de defasagens em meses (ex: [1, 2, 3])
  - `parameters.lag_weights` — pesos correspondentes (ex: [0.5, 0.3, 0.2], soma = 1.0)
- Se historico de meses anteriores nao disponivel: reduzir para lags disponiveis, normalizar pesos
- **Dependencia critica**: o leading_indicator DEVE ser projetado antes deste indicador (Fase 1 resolve ordem)

Para detalhes adicionais das formulas e casos especiais, consultar [projection-methodology.md](references/projection-methodology.md).

### Fase 3 — Consolidar Projecao Final

Para cada indicador, consolidar usando `projection.consolidation` do YAML:

**`median_confident`** (padrao):
1. Filtrar metodos com `confidence >= medium` (do YAML)
2. Projecao final = **mediana** dos valores filtrados
3. Se metodos aplicados < `projection.min_methods` → flag `baixa_confianca: true`

**Validar projecoes:**
- Projecao nao pode ser negativa — se negativa, ajustar para 0 com flag de anomalia
- Se projecao > 200% da meta — flag de anomalia para revisao manual
- Se desvio padrao entre metodos > 50% da mediana — flag `alta_dispersao: true`

**Output Fase 3:** Projecao final por indicador com metodos utilizados e consolidacao.

### Fase 4 — Classificar Probabilidade

Para cada indicador com `projection.projectable: true`, classificar com base na projecao final vs meta:

| Classificacao | Criterio |
|---------------|----------|
| **Provavel** | Projecao >= 90% da meta |
| **Possivel** | Projecao entre 70-89% da meta |
| **Improvavel** | Projecao < 70% da meta |

Indicadores com `projectable: false` NAO recebem classificacao.

### Fase 5 — Calcular Cenarios e Gap

**Cenarios** — gerar APENAS se o Card define `projecao.cenarios` para o indicador:
- **Otimista (P90)**: percentil 90 dos valores projetados pelos metodos (ou max se 2 metodos)
- **Base (mediana)**: mediana dos metodos (= projecao final)
- **Pessimista (P10)**: percentil 10 dos valores projetados (ou min se 2 metodos)

Se Card nao define `projecao.cenarios`: registrar apenas cenario Base.

**Gap para meta:**
```
gap_absoluto = meta - projecao_base
gap_percentual = (gap_absoluto / meta) × 100
ritmo_necessario = gap_absoluto / dias_uteis_restantes
fator_aceleracao = ritmo_necessario / ritmo_atual
```

Se `gap_absoluto <= 0` (meta projetada para ser atingida): registrar como "meta projetada" sem calculo de ritmo.
Se `fator_aceleracao > 2`: flag "aceleracao significativa necessaria".

### Fase 6 — Gerar Output

Gerar `analise/projection-report.md` (na pasta do ciclo) seguindo o [template](templates/projection-report.tmpl.md).

**Secoes obrigatorias:**
1. Resumo de projecoes (tabela com indicadores projetaveis — `projectable: true`)
2. Detalhamento por indicador (metodos do YAML, cenarios se Card define, gap)
3. Indicadores com risco de nao atingimento (lista dos "Improvavel")
4. Anomalias e observacoes (flags, dependencias, metodos nao aplicaveis)

**Ordem de apresentacao:**
1. Indicadores com `projecao.obrigatoria: true` primeiro
2. Depois indicadores com `projectable: true` e `projecao.obrigatoria: false`
3. Indicadores com `projectable: false` NAO aparecem no relatorio de projecao

## Exit Criteria

- [ ] Relatorio de Projecao gerado em `analise/projection-report.md` (na pasta do ciclo)
- [ ] Metodos aplicados conforme `projection.methods` de cada YAML (nao hardcoded)
- [ ] Dependencias cruzadas resolvidas (ex: volume antes de receita)
- [ ] `stage_conversion_rates` e `lag_weights` lidos do YAML, nao inventados
- [ ] Consolidacao via `projection.consolidation` do YAML
- [ ] `min_methods` respeitado — flag `baixa_confianca` se insuficiente
- [ ] Cenarios gerados apenas onde Card define `projecao.cenarios`
- [ ] `projecao.obrigatoria: true` = aparece no WBR; `false` = opcional
- [ ] Classificacao Provavel/Possivel/Improvavel consistente com thresholds
- [ ] Projecoes nao negativas e com flag se >200% da meta

## Anti-Patterns

- NUNCA aplique metodos nao listados em `projection.methods` do YAML — se media movel nao esta no YAML, nao use
- NUNCA hardcode `stage_conversion_rates` ou `lag_weights` — SEMPRE leia do YAML
- NUNCA projete indicador com `projectable: false` — sao snapshots ou contexto
- NUNCA projete receita antes de volume quando ha dependencia `lagging_indicator` → respeitar ordem da Fase 1
- NUNCA invente taxas de conversao de funil — usar APENAS valores do YAML (calibraveis apos 2-3 ciclos)
- NUNCA apresente projecao negativa — ajustar para 0 com flag de anomalia
- NUNCA omita o metodo com menor confianca — identificar e justificar
- NUNCA sugira acoes corretivas — isso e responsabilidade de E4 (summarizing-actions)
- NUNCA gere cenarios P10/P90 se Card nao define `projecao.cenarios` para o indicador
