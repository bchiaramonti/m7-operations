# Metodologia de Projecao — Metodos YAML-Driven + Consolidacao

> Referencia para o agente analyst e a skill projecting-results.
> Define formulas, parametros, resolucao de dependencias e regras de consolidacao.
>
> **IMPORTANTE**: Os metodos NAO sao hardcoded. Cada indicador define em seu YAML quais metodos usar.
> Esta referencia documenta TODOS os metodos possiveis — o analyst aplica apenas os listados no YAML.

---

## Indice

1. [Leitura do YAML](#1-leitura-do-yaml)
2. [Resolucao de Dependencias](#2-resolucao-de-dependencias)
3. [run_rate_linear](#3-run_rate_linear)
4. [trend_exponential](#4-trend_exponential)
5. [pipeline_conversion](#5-pipeline_conversion)
6. [lagging_indicator](#6-lagging_indicator)
7. [Consolidacao e Projecao Final](#7-consolidacao-e-projecao-final)
8. [Cenarios P10/P90](#8-cenarios-p10p90)
9. [Classificacao de Probabilidade](#9-classificacao-de-probabilidade)
10. [Calculo de Gap e Ritmo](#10-calculo-de-gap-e-ritmo)
11. [Validacao e Anomalias](#11-validacao-e-anomalias)
12. [Regras de Redacao](#12-regras-de-redacao)

---

## 1. Leitura do YAML

### Estrutura do bloco `projection` no YAML do indicador

```yaml
projection:
  projectable: true|false
  methods:
    - method: run_rate_linear|trend_exponential|pipeline_conversion|lagging_indicator
      applicable: true|false
      confidence: high|medium|low
      parameters:           # varia por metodo
        min_periods: 8      # trend_exponential
        alpha: 0.3           # trend_exponential
        source_indicator: "oportunidades_ativas_funil"  # pipeline_conversion
        stage_conversion_rates: {...}                    # pipeline_conversion
        stage_duration_days: {...}                       # pipeline_conversion
        leading_indicator: "volume_consorcio_mensal"     # lagging_indicator
        lag_months: [1, 2, 3]                            # lagging_indicator
        lag_weights: [0.5, 0.3, 0.2]                     # lagging_indicator
  consolidation: median_confident|weighted_average|best_method
  min_methods: 1|2|3
  nota: "texto explicativo"
```

### Estrutura do campo `projecao` no Card (kpi_references[])

```yaml
projecao:
  obrigatoria: true|false    # true = DEVE aparecer no WBR
  metodo_preferido: "pipeline_conversion"  # metodo preferido (informativo)
  cenarios: [otimista, base, pessimista]   # se definido, gerar cenarios
```

### Regra de leitura

1. Ler Card → para cada `kpi_reference`, verificar `projecao.obrigatoria`
2. Ler YAML do indicador → verificar `projection.projectable`
3. Se `projectable: false`: NAO projetar, independente do Card
4. Se `projectable: true` e `projecao.obrigatoria: false`: projetar se possivel, mas nao obrigatorio no WBR
5. Aplicar APENAS metodos de `projection.methods` — nunca adicionar metodos extras

---

## 2. Resolucao de Dependencias

Alguns metodos dependem da projecao ou dados de outro indicador:

| Metodo | Campo de dependencia | Tipo |
|--------|---------------------|------|
| `pipeline_conversion` | `parameters.source_indicator` | Dados de E2 (deals ativos) |
| `lagging_indicator` | `parameters.leading_indicator` | Projecao do indicador lider |

### Algoritmo de resolucao

1. Construir grafo de dependencias:
   - Para cada indicador projetavel, verificar se algum metodo referencia outro indicador
   - Se o indicador referenciado tem `projectable: true` → dependencia de projecao
   - Se o indicador referenciado tem `projectable: false` → dependencia de dados E2 (resolve imediatamente)

2. Ordenar por topologia (dependencias primeiro):
   ```
   Exemplo Consorcios:
   1. oportunidades_ativas_funil (projectable: false) → dados E2 direto
   2. volume_consorcio_mensal (pipeline_conversion.source = oportunidades_ativas) → projetar
   3. receita_consorcio_mensal (lagging_indicator.leading = volume) → projetar DEPOIS de volume
   4. taxa_conversao_funil_con (sem dependencia) → qualquer ordem
   5. quantidade_consorcio_mensal (sem dependencia) → qualquer ordem
   ```

3. Se dependencia circular detectada: reportar anomalia e projetar com metodos independentes apenas

---

## 3. run_rate_linear

### Formula

```
projecao = (realizado_acumulado / dias_uteis_decorridos) × dias_uteis_totais
```

### Aplicabilidade

- **Requisito**: serie temporal com pelo menos 1 ponto no periodo atual
- **Melhor para**: indicadores com comportamento estavel e sem sazonalidade forte
- **Limitacao**: assume ritmo constante — nao captura aceleracao, desaceleracao ou sazonalidade

### Parametros Temporais

| Parametro | Calculo |
|-----------|---------|
| `dias_uteis_decorridos` | Dias uteis do 1o dia do periodo ate a data do checkpoint (inclusive) |
| `dias_uteis_totais` | Total de dias uteis do periodo completo |
| `dias_uteis_restantes` | `dias_uteis_totais - dias_uteis_decorridos` |

**Feriados**: considerar feriados nacionais (BR) se disponiveis. Caso contrario, usar calendario padrao seg-sex.

### Flag de baixa confianca

Se `dias_uteis_decorridos < 5`: projecao altamente sensivel a variacao diaria. Flag `baixa_confianca`.

### Exemplo

```
Realizado acumulado: R$ 6.845.000
Dias uteis decorridos: 17
Dias uteis totais: 22

Projecao = (6.845.000 / 17) × 22 = R$ 8.858.235
```

---

## 4. trend_exponential

### Formula (Suavizacao Exponencial Dupla — Holt)

```
nivel_t = alpha × Y_t + (1 - alpha) × (nivel_{t-1} + tendencia_{t-1})
tendencia_t = beta × (nivel_t - nivel_{t-1}) + (1 - beta) × tendencia_{t-1}
projecao_{t+h} = nivel_t + h × tendencia_t
```

### Parametros

| Parametro | Fonte | Default |
|-----------|-------|---------|
| `alpha` | `parameters.alpha` do YAML | 0.3 |
| `beta` | fixo | 0.1 |
| `min_periods` | `parameters.min_periods` do YAML | 8 |

### Aplicabilidade

- **Requisito**: >= `min_periods` periodos de historico
- **Melhor para**: indicadores com tendencia clara (crescimento ou queda consistente)
- **Limitacao**: requer serie mais longa; pode ser instavel com poucos pontos

### Inicializacao

- `nivel_0` = primeiro valor da serie
- `tendencia_0` = diferenca entre os 2 primeiros valores

### Componente Sazonal

Se o campo `analysis_guide` do YAML indicar sazonalidade conhecida:
- Ajustar projecao pelo fator sazonal historico do periodo
- Documentar o ajuste sazonal no relatorio

### Exemplo

```
Serie mensal: [85K, 88K, 92K, 87K, 95K, 98K, 94K, 101K, 89K]
alpha=0.3, beta=0.1, min_periods=8

Apos suavizacao:
nivel_9 = 95.2K, tendencia_9 = +1.8K/mes

Projecao fim do mes: 95.2K + 1 × 1.8K = R$ 97.0K
```

---

## 5. pipeline_conversion

### Conceito

Projeta valor futuro com base em **deals ativos no pipeline CRM**, multiplicando cada deal por sua probabilidade de conversao (baseada no estagio) e probabilidade de timing (fechar dentro do periodo).

### Formula

```
Para cada deal ativo do source_indicator:
  prob_conversao = stage_conversion_rates[estagio_atual]
  prob_timing = max(0, 1 - stage_duration_days[estagio_atual] / dias_calendario_restantes)
  contribuicao = deal.valor × prob_conversao × prob_timing

pipeline_projetado = sum(contribuicao)
projecao_total = realizado_acumulado + pipeline_projetado
```

### Parametros do YAML

```yaml
parameters:
  source_indicator: "oportunidades_ativas_funil"
  conversion_model: stage_probability
  timing_model: stage_duration
  stage_conversion_rates:
    prospeccao: 0.05
    investigacao: 0.10
    apresentacao: 0.20
    proposta: 0.40
    emissao_de_contrato: 0.70
    cotas_alocadas: 0.90
  stage_duration_days:
    prospeccao: 45
    investigacao: 30
    apresentacao: 21
    proposta: 14
    emissao_de_contrato: 7
    cotas_alocadas: 3
```

### P(timing) — Probabilidade de Fechar no Periodo

O fator `P(timing)` penaliza deals cujo estagio requer mais dias do que os restantes no periodo:

| Estagio | Duration (dias) | Com 8 dias restantes | Com 30 dias restantes |
|---------|----------------|---------------------|----------------------|
| prospeccao | 45 | max(0, 1-45/8) = **0.00** | max(0, 1-45/30) = **0.00** |
| investigacao | 30 | max(0, 1-30/8) = **0.00** | max(0, 1-30/30) = **0.00** |
| apresentacao | 21 | max(0, 1-21/8) = **0.00** | max(0, 1-21/30) = **0.30** |
| proposta | 14 | max(0, 1-14/8) = **0.00** | max(0, 1-14/30) = **0.53** |
| emissao_contrato | 7 | max(0, 1-7/8) = **0.13** | max(0, 1-7/30) = **0.77** |
| cotas_alocadas | 3 | max(0, 1-3/8) = **0.63** | max(0, 1-3/30) = **0.90** |

### Exemplo Completo

```
Realizado acumulado: R$ 6.845.000
Dias calendario restantes: 8

Pipeline ativo (source: oportunidades_ativas_funil):
| Deal | Estagio | Valor | Rate | P(timing) | Contribuicao |
|------|---------|-------|------|-----------|-------------|
| D1 | cotas_alocadas | R$ 500K | 0.90 | 0.63 | R$ 283.500 |
| D2 | emissao_contrato | R$ 1.2M | 0.70 | 0.13 | R$ 109.200 |
| D3 | proposta | R$ 800K | 0.40 | 0.00 | R$ 0 |
| D4 | prospeccao | R$ 2M | 0.05 | 0.00 | R$ 0 |

Pipeline projetado = R$ 392.700
Projecao = R$ 6.845.000 + R$ 392.700 = R$ 7.237.700
```

### Regras Criticas

- **NUNCA invente rates** — usar APENAS `stage_conversion_rates` do YAML
- Rates iniciais sao estimativas. Apos 2-3 ciclos, calibrar contra dados reais do `taxa_conversao_funil_con`
- Se `source_indicator` nao tem dados em E2: metodo nao aplicavel
- Se estagio do deal nao esta no dict de rates: usar rate = 0 e registrar anomalia

---

## 6. lagging_indicator

### Conceito

Indicadores derivados (ex: receita) sao funcao defasada de um indicador lider (ex: volume). A receita de marco reflete parcialmente o volume de fevereiro, janeiro e dezembro, com pesos decrescentes.

### Formula

```
projecao = sum(valor_leading[mes_atual - lag_months[i]] × lag_weights[i])
```

Onde:
- Para `lag_months[0]` (menor lag, tipicamente 1 mes): se o `leading_indicator` foi projetado neste ciclo, usar a **projecao** como `valor_leading`
- Para lags maiores: usar **realizado historico** do `leading_indicator`

### Parametros do YAML

```yaml
parameters:
  leading_indicator: "volume_consorcio_mensal"
  lag_months: [1, 2, 3]
  lag_weights: [0.5, 0.3, 0.2]
```

### Exemplo

```
Leading indicator: volume_consorcio_mensal
Periodo atual: marco 2026

Projecao volume marco (calculada no passo anterior): R$ 7.762.650

Historico volume:
- Fevereiro 2026: R$ 6.500.000
- Janeiro 2026: R$ 5.800.000

Projecao receita = (7.762.650 × 0.5) + (6.500.000 × 0.3) + (5.800.000 × 0.2)
                 = 3.881.325 + 1.950.000 + 1.160.000
                 = R$ 6.991.325

Nota: Este valor e a RECEITA DERIVADA do volume com lag. A taxa de conversao
volume→receita (comissao rate) ja esta implicita nos lag_weights calibrados.
```

### Tratamento de Historico Incompleto

Se historico de meses anteriores nao disponivel:
1. Reduzir para lags disponiveis
2. Normalizar pesos para somar 1.0
3. Flag `baixa_confianca` se menos de 2 lags disponiveis

```
Se apenas fevereiro disponivel (lag_months[0]=1, peso original=0.5):
  peso_normalizado = 0.5 / 0.5 = 1.0
  projecao = volume_fev × 1.0
  Flag: baixa_confianca (apenas 1 lag disponivel)
```

### Dependencia Critica

O `leading_indicator` DEVE ser projetado ANTES deste indicador. A Fase 1 da skill resolve a ordem de execucao.

---

## 7. Consolidacao e Projecao Final

### Regras por tipo de consolidacao

**`median_confident`** (padrao para todos indicadores de Consorcios):
1. Filtrar metodos aplicados com `confidence >= medium` (campo do YAML)
2. Calcular mediana dos valores projetados
3. Se metodos filtrados < `min_methods`: flag `baixa_confianca: true`

**`weighted_average`** (reservado para uso futuro):
1. Ponderar valores por `confidence`: high=3, medium=2, low=1
2. Media ponderada

**`best_method`** (reservado para uso futuro):
1. Usar `projecao.metodo_preferido` do Card
2. Se preferido nao aplicavel: fallback para mediana

### Justificativa da Mediana

A mediana e mais robusta que a media para consolidacao porque:
- Resiste a outliers (ex: pipeline_conversion pode gerar projecoes extremas com poucos deals grandes)
- Equilibra metodos conservadores (run-rate) e agressivos (pipeline)
- Mantem interpretabilidade (um dos valores reais projetados)

---

## 8. Cenarios P10/P90

### Requisito

Cenarios so sao calculados se o Card define `projecao.cenarios` para o indicador.

### Calculo

Com os N valores projetados pelos metodos aplicaveis (ordenados):

| Cenario | Calculo | Interpretacao |
|---------|---------|---------------|
| **Otimista (P90)** | Valor maximo dos metodos (se N=2) ou percentil 90 (se N>=3) | Melhor cenario plausivel |
| **Base (mediana)** | Mediana dos valores | Cenario mais provavel |
| **Pessimista (P10)** | Valor minimo dos metodos (se N=2) ou percentil 10 (se N>=3) | Pior cenario plausivel |

### Quando nao calcular

Se Card NAO define `projecao.cenarios` para o indicador:
- Registrar apenas cenario Base (projecao final)
- NAO gerar secao de cenarios no relatorio

---

## 9. Classificacao de Probabilidade

### Thresholds

| Classificacao | Criterio | Significado |
|---------------|----------|------------|
| **Provavel** | Projecao >= 90% da meta | Alta probabilidade de atingimento |
| **Possivel** | Projecao entre 70-89% da meta | Atingimento depende de aceleracao |
| **Improvavel** | Projecao < 70% da meta | Risco alto de nao atingimento |

### Regras de Aplicacao

- Usar `projecao_base` (mediana consolidada) para classificacao
- Se projecao >= 100% da meta: classificar como "Provavel" e destacar que meta esta projetada para ser atingida
- Se classificacao e "Improvavel": obrigatorio calcular gap e ritmo necessario
- Aplicar APENAS a indicadores com `projectable: true`

---

## 10. Calculo de Gap e Ritmo

### Formulas

```
gap_absoluto = meta - projecao_base
gap_percentual = (gap_absoluto / meta) × 100
ritmo_necessario = gap_absoluto / dias_uteis_restantes
ritmo_atual = realizado_acumulado / dias_uteis_decorridos
fator_aceleracao = ritmo_necessario / ritmo_atual
```

### Regras

- Se `gap_absoluto <= 0`: meta projetada para ser atingida — nao calcular ritmo
- Se `dias_uteis_restantes = 0`: ultimo dia do periodo — ritmo_necessario = gap_absoluto
- Se `fator_aceleracao > 2`: flag "aceleracao significativa necessaria"

---

## 11. Validacao e Anomalias

### Validacoes Obrigatorias

| Validacao | Regra | Acao |
|-----------|-------|------|
| Projecao negativa | `projecao < 0` | Ajustar para 0, flag `anomalia: projecao_negativa` |
| Projecao excessiva | `projecao > 200% da meta` | Manter valor, flag `anomalia: projecao_excessiva` |
| Baixa confianca | Metodos < `min_methods` | Flag `baixa_confianca: true` |
| Alta dispersao | Desvio padrao > 50% da mediana | Flag `alta_dispersao: true`, investigar |
| Metodo nao aplicavel | Requisito minimo nao atendido | Flag `metodo_nao_aplicavel`, registrar justificativa |
| Estagio desconhecido | Deal em estagio nao mapeado em rates | Usar rate=0, flag anomalia |
| Dependencia circular | Indicador A depende de B que depende de A | Flag anomalia critica |

---

## 12. Regras de Redacao

### O que DEVE conter o relatorio

- Todos os metodos do YAML com seus valores (ou justificativa de nao-aplicabilidade)
- Projecao final (consolidada) com classificacao de probabilidade
- Gap absoluto E percentual para meta
- Ritmo necessario vs ritmo atual (com fator de aceleracao)
- Cenarios quando Card define `projecao.cenarios`
- Detalhe de pipeline_conversion (tabela por estagio) quando aplicavel
- Detalhe de lagging_indicator (tabela por lag) quando aplicavel
- Cadeia de dependencias documentada
- Flags de anomalia e baixa confianca quando aplicaveis
- Numeros em formato brasileiro (R$ X.XXX,XX ou R$ XM)

### O que NAO deve conter

- Metodos nao listados no YAML do indicador
- Recomendacoes de acoes (isso e E4)
- Causas dos desvios (isso e E3)
- Julgamentos sobre performance de pessoas
- Projecoes baseadas em dados inventados
- Cenarios se Card nao define `projecao.cenarios`
