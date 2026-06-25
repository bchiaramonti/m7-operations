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
   - [5.1 pipeline_conversion_extended (v1 — current/interim)](#51-pipeline_conversion_extended-v1--current-interim)
   - [5.2 pipeline_conversion_extended_v2 (target, preferred futuro)](#52-pipeline_conversion_extended_v2-target-preferred-futuro)
6. [lagging_indicator](#6-lagging_indicator)
   - [6.1 Receita derivada de Volume + Real_competencia (formula universal)](#61-receita-derivada-de-volume--real_competencia-formula-universal)
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

> **MIGRACAO 2026-05-04:** indicadores antigos com `pipeline_conversion`
> (stage_probability complexo, modelo P×timing acima) ainda existem nos
> YAMLs mas estao marcados `applicable: false, deprecated: true`. Skill
> IGNORA-os e usa `pipeline_conversion_extended` (5.1/5.2 abaixo) quando
> disponivel.

---

## 5.1 pipeline_conversion_extended (v1 — current/interim)

> **Status:** v1 atualmente em producao. **deprecated_reason:** "M+1 sem
> componente funil; atualizacao one-shot pendente — ver v2 (5.2)".
> Substitui `pipeline_conversion` (5) para CON e SEG.

### Conceito

Substitui `pipeline_conversion` (modelo stage-aware complexo) por
formula simplificada `Vol × Taxa_Conversao` acordada com coordenador
de Seguros em 2026-04-29 e estendida para Consorcios em 2026-05-04.

Modelo simplificado e mais robusto quando scripts de coleta nao
retornam stage breakdown por deal — cobre o 80/20 dos cenarios.

### Formula

**Mes corrente (M0):**
```
projecao_mes_corrente = Vol_Oport_Ativas × Taxa_Conversao_Mes
                         (snapshot atual × taxa do mes)
```

**Mes seguinte (M+1):**
```
pipeline_residual_M0  = Vol_Oport_Ativas - projecao_mes_corrente
entradas_novas_M+1    = Media_oport_criadas_3m × DU_M+1 / DU_mes_padrao
projecao_mes_seguinte = (pipeline_residual_M0 + entradas_novas_M+1) × Taxa_Conversao
```

### Parametros do YAML

```yaml
parameters:
  source_funil:
    indicador: "oportunidades_ativas_funil"
    campo_volume: volume
    campo_qty: quantidade
    filtro_squad: null              # opcional ('wl' | 're') para Cards split
  source_taxa:
    indicador: "taxa_conversao_funil_con"
    campo: taxa_conversao
    fallback_se_ausente: 0.30
  source_criadas:
    indicador: "oportunidades_criadas_funil"
    horizonte_historico_meses: 3    # janela da media movel (default 3)
  componentes_mes_corrente:
    formula: "Vol_Oport_Ativas × Taxa_Conversao_Mes"
  componentes_mes_seguinte:
    formula: "(Pipeline_residual_M0 + Entradas_novas_M+1) × Taxa_Conversao"
    fallback_se_historico_insuficiente: run_rate_linear
```

### Aplicabilidade

- **Mes corrente:** confidence high (snapshot direto do funil).
- **Mes seguinte:** confidence medium (requer historico de criadas; cair
  em `run_rate_linear` se historico < 3 meses).

### Gap conhecido (motivo da v2)

A formula M+1 em v1 **NAO incorpora cycle-time por estagio**. Trata
todo deal do funil como capaz de fechar em M0 (subtraindo) ou M+1
(usando residual). Mas deals em estagios iniciais (ex: Prospeccao com
cycle 45 dias) **nao deveriam** contribuir para M+1 se faltam mais que
DU_M+1 + DU_M0_restantes.

Resultado pratico em metodo "a" interim: `componente_funil_M+1` = 0
(workaround conservador), e M+1 e calculado como **lagging only**.
Subestima projecao M+1.

Ver [KNOWN_ISSUES.md](../KNOWN_ISSUES.md) ISSUE #5 para detalhes.

---

## 5.2 pipeline_conversion_extended_v2 (target, preferred futuro)

> **Status:** target — implementacao agendada para "sessao posterior"
> (ver [M+1-PROJECTION-ROADMAP.md](M+1-PROJECTION-ROADMAP.md)).
> Quando disponivel, marcar `preferred: true` no YAML do indicador
> e v1 vira fallback `preferred: false`.

### Conceito

Cycle-time-aware: cada deal do funil e classificado em horizonte (M0,
M+1, ou fora) baseado em **`tempo_estimado_fechamento`** do estagio
atual e **`stage_probability`** vigente.

**Volume_M+1 e SEMPRE 100% Bitrix funil** — nao ha componente lagging de
competencia futura para volume. Aplica-se a todas as verticais (Cons,
Seg WL, Seg RE, PJ2).

> **CORRECAO 2026-05-13:** versao anterior desta secao mencionava
> `vol_lagging_competencia` proveniente de `m7Bronze.consorcio_contratos.data_competencia`.
> ISSO ESTAVA ERRADO. Esse ledger so existe em Cons e refere-se a
> **Receita Real de competencia futura** (parcelas dos contratos
> antigos), nao a Volume. Volume M+1 e exclusivamente componente
> funil em todas as verticais. Ver nota na secao 6.1 abaixo.

Resolve o gap da v1 separando:
- `vol_componente_M0` (deals do funil que fecham em M0)
- `vol_componente_M+1` (deals do funil que fecham em M+1)

A formula de receita derivada (`(Vol × rate) / installments`, secao 6)
consome `vol_componente_M0` ou `vol_componente_M+1`. Em Cons, somar
ainda `lagging_receita_competencia` separadamente (parcelas ja cravadas
em `consorcio_receita.competencia=M`) — esse ledger e de **receita**,
nao de volume. Ver secao 6.1.

### Algoritmo

1. Iterar deals do funil ativos (snapshot Bitrix `oportunidades_ativas_funil`).
2. Para cada deal:
   - Identificar estagio atual.
   - Calcular `dias_restantes_M0` = DU restantes do mes corrente.
   - Calcular `dias_restantes_M+1` = `DU_M0_restantes + DU_M+1`.
   - Buscar `stage_duration_vigente` (mediana real do estagio) e
     `stage_probability_vigente` (pct deals que avancaram para "won")
     do estagio×mes (ver "Stage source — regra dia 15" abaixo).
3. Classificar deal por horizonte:
   - Se `stage_duration_vigente < dias_restantes_M0` →
     `vol_componente_M0 += deal_volume × stage_probability_vigente`.
   - Senao se `stage_duration_vigente < dias_restantes_M+1` →
     `vol_componente_M+1 += deal_volume × stage_probability_vigente`.
   - Senao → fora de horizonte (M+2 nao implementado).
4. Estimar `vol_entradas_novas_M+1` = `media_movel_criadas_3m × DU_M+1
   / DU_mes_padrao × stage_prob_inicial` (ainda exige pelo menos 3 meses
   historico — fallback p/ run_rate se ausente).

### Stage source — SEMPRE mes anterior completo (exit-based, 2026-06-19)

| stage_metrics | Stage_probability + stage_duration source |
|---------------|-------------------------------------------|
| EXIT-BASED (atual) | **SEMPRE o mes ANTERIOR COMPLETO** (coorte resolvida) |

> **CORRECAO 2026-06-19 (valida retroativamente no Cons 06-17):** a regra antiga
> "dia 1-14 mes anterior; 15-fim mes atual" foi desenhada para o stage_metrics
> ENTRY-cohort. O stage_metrics agora e EXIT-BASED (probabilidade = won_passers/
> resolved_passers ancorada no mes de RESOLUCAO). Nesse modelo, a coorte resolvida
> do mes CORRENTE so amadurece no FIM do mes — no meio do mes (ex: dia 17) poucos
> deals resolveram, entao o stage_probability do mes corrente DEGENERA a ~0 e o v2
> volta a zerar o funil.
>
> **Validacao retroativa (funil real Cons 06-17):** componente_funil projetado =
> R$ 0 com mes corrente (Junho dia 17) vs **R$ 12,84M com mes anterior (Maio
> completo)**. Por isso: usar SEMPRE o mes anterior completo como referencia
> estavel. So trocar para o mes corrente quando ELE estiver completo (ou seja,
> ele vira "mes anterior" no ciclo seguinte). NAO ha mais switch no dia 15.

Razao: a coorte EXIT-based precisa de deals RESOLVIDOS; o ultimo mes completo e a
amostra madura mais recente. O mes corrente parcial sub-conta resolucoes.

### Exemplo concreto

```
Cenario: Maio 2026, hoje = dia 20. DU_M0_restantes = 7. DU_M+1 = 22.
Deal D1: estagio "Prospeccao", entrou no funil dia 20. cycle_vigente_prospeccao = 45 dias.

  dias_restantes_M0 = 7
  dias_restantes_M+1 = 7 + 22 = 29

  stage_duration_vigente(Prospeccao) = 45 → 45 > 7 → NAO entra em M0.
                                          45 > 29 → NAO entra em M+1.
                                          → fora de horizonte (M+2 ou alem).

Deal D2: estagio "Cotas Alocadas", entrou dia 14.
  cycle_vigente_cotas_alocadas = 3 → 3 < 7 → entra em M0.
  stage_probability_vigente(Cotas Alocadas) = 0.92.
  vol_componente_M0 += deal_volume × 0.92.

Deal D3: estagio "Apresentacao", entrou dia 5.
  cycle_vigente_apresentacao = 21 → 21 > 7 → NAO entra em M0.
                                     21 < 29 → entra em M+1.
  stage_probability_vigente(Apresentacao) = 0.20.
  vol_componente_M+1 += deal_volume × 0.20.
```

### Parametros do YAML

```yaml
- id: pipeline_conversion_extended_v2
  applicable: true
  preferred: true
  confidence: high
  parameters:
    stage_durations_source: prior_month_complete   # EXIT-BASED: sempre mes anterior completo
    transition_day: null                           # APOSENTADO 2026-06-19 (era 15, p/ entry-cohort)
    source_stage_metrics:
      indicador: "stage_metrics_vigentes"          # EXIT-BASED (won_passers/resolved_passers)
    source_funil:
      indicador: "oportunidades_ativas_funil"
    source_criadas:
      indicador: "oportunidades_criadas_funil"
      historico_meses: 3
```

> **NAO** declarar `source_lagging` em volume — Volume M+1 e exclusivamente
> Bitrix funil. O ledger `m7Bronze.consorcio_contratos.data_competencia`
> NAO entra em Volume; ele e referente a Receita lagging (ver secao 6.1).

### Output

```python
{
  "vol_componente_M0":      float,    # via stage classification (funil Bitrix)
  "vol_componente_M+1":     float,    # via stage classification (funil Bitrix)
  "vol_entradas_novas_M+1": float,    # via media movel criadas
  "stage_breakdown": {                 # detalhe por estagio para auditoria
    "prospeccao":        {"M0": 0, "M+1": 0, "fora": float},
    "investigacao":      {"M0": 0, "M+1": float, "fora": float},
    "apresentacao":      {"M0": 0, "M+1": float, "fora": 0},
    "proposta":          {"M0": float, "M+1": float, "fora": 0},
    "emissao_contrato":  {"M0": float, "M+1": float, "fora": 0},
    "cotas_alocadas":    {"M0": float, "M+1": 0, "fora": 0}
  }
}
```

### Consolidacao final por horizonte

```
Vol_proj_M0  = realizado_acumulado_MTD + vol_componente_M0
Vol_proj_M+1 = vol_componente_M+1 + vol_entradas_novas_M+1
```

Onde `realizado_acumulado_MTD` vem do indicador `volume_consorcio_mensal`
(ou `volume_seguros_mensal`) ja extraido em E2 — refere-se ao mes corrente
ate a data do checkpoint. **NAO existe `realizado_M+1` para Volume** em
nenhuma vertical (so para Receita Cons via lagging — ver secao 6.1).

### Refs

- [M+1-PROJECTION-ROADMAP.md](M+1-PROJECTION-ROADMAP.md) — roadmap completo
- [KNOWN_ISSUES.md](../KNOWN_ISSUES.md) ISSUE #3 (double-count) e ISSUE #5 (M+1 gap)

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

## 6.1 Receita derivada de Volume + Real_competencia (formula universal)

> **Esclarecimento 2026-05-13:** distinguir **3 conceitos** que estavam
> sendo confundidos:
>
> 1. `lagging_indicator` (secao 6) — metodo matematico que usa
>    historico passado de um leading (volume) ponderado por
>    `lag_weights` para projetar receita. **Nao** se usa em
>    M+1 de Receita no slide Pipeline.
> 2. `volume_componente_funil` — projecao de volume a partir do funil
>    Bitrix (cycle-time-aware). Fonte de `Vol_M+1` na formula abaixo.
> 3. `lagging_receita_competencia` — ledger de parcelas mensais ja
>    cravadas para competencia futura (`consorcio_receita.competencia=M+1`).
>    So existe em Cons. Equivalente conceitual a "Receita Real M+1".

### Formula de Receita projetada — CORRIGIDA 2026-06-19

> **CORRECAO (decisao do usuario 2026-06-19):** o `valor da oportunidade` do Card
> JA carrega a receita. A formula antiga `(Vol × rate)/installments` estava
> **conceitualmente errada para Seguros** — o campo OPPORTUNITY do Bitrix em Seg e
> o VALOR DE ACEITACAO ≈ comissao estimada (NAO premio bruto, ver memory
> `reference_seguros_receita_potencial`), entao aplicar o rate 0,5 de novo
> DOBRA-descontava. Em Cons, a oportunidade = valor da carta (Volume), e o rate
> 3,5% e legitimo. Formula por vertical (opp = valor da oportunidade projetado pelo
> funil = Σ opp_estagio × stage_probability):

| Vertical | Volume projetado | Receita projetada |
|----------|------------------|-------------------|
| **Cons** | = opp (valor da carta) | = opp × 0,035 / 12 |
| **Seg WL** | = Receita × 2 | = opp / 12 |
| **Seg RE** | nao projeta | = opp / 12 |

NOTA: Seg NAO usa mais rate de comissao na projecao (a oportunidade ja e a comissao).
Isso APOSENTA o ISSUE #4 (caca ao "campo de premio anualizado") e o bloqueio da
taxa RE nao-calibrada — RE projeta receita igual ao WL (opp/12), so nao projeta Volume.

### Aplicacao no slide Pipeline (M+1)

```python
# opp_proj_M = Σ(funil.opportunity_estagio × stage_probability_estagio) p/ horizonte M
# (componente de funil; Real_competencia adicionado so onde ha ledger)

# Cons (e PJ2 subset Cons): opp = valor da carta = Volume
real_receita_m1_cons = sum(consorcio_receita.valor_comissao WHERE competencia = M+1)
receita_proj_M1_cons = real_receita_m1_cons + (opp_proj_M1_cons × 0.035) / 12

# Seg WL/RE (e PJ2 subset Seg): opp = valor de aceitacao ≈ comissao anual
real_receita_m1_seg = 0  # nao existe ledger de competencia futura p/ comissao Seg
receita_proj_M1_seg = real_receita_m1_seg + opp_proj_M1_seg / 12   # SEM rate ×0,5
volume_proj_M1_seg_wl = receita_proj_M1_seg × 2                    # so WL; RE nao projeta volume
```

### M0 vs M+1 — disponibilidade de Real

| Horizonte | Real Cons | Real Seg WL |
|-----------|-----------|-------------|
| M0 (mes corrente, MTD) | `consorcio_receita.competencia=M0` (parcelas cravadas + pagas) | tabela comissao Seg MTD |
| M+1 (proximo mes) | `consorcio_receita.competencia=M+1` (parcelas futuras de contratos antigos) | **0** (nao ha comissao Seg cravada para competencia futura) |

Implicacao para Receita M+1: Cons soma Real + componente; Seg = `opp_M+1 / 12`
(componente de funil apenas — sem ledger Real futuro).

### Quando NAO projetar Receita (M0 nem M+1)

- ~~**Seg RE**~~ **CORRIGIDO 2026-06-19:** RE AGORA PROJETA receita normalmente via
  `opp / 12` — a antiga ressalva (rate 0,5 superestimava RE) NAO se aplica mais,
  porque a nova formula NAO usa rate de comissao (a oportunidade ja e a comissao).
  Nao depende mais de calibrar taxa RE com coordenadores. **So Volume RE nao e
  projetado** (decisao do usuario). Slide Pipeline Seg RE Receita = Realizado MTD
  + componente de funil `opp/12`.
- **PJ2 subset Seg M+1**: M0 e M+1 seguem `opp / 12` (sem rate).
- **PJ2 Total Receita**: nao calcular separado; **somar** Proj_Cons +
  Proj_Seg para velocimetro #21 (Total PJ2 Receita). Meta tambem e
  soma.

### Como o Card declara

```yaml
apresentacao:
  proj_periodos_por_indicador:
    receita_seguros_mensal: []        # Seg RE: nao projetar nada
    receita_seguros_mensal: ["M0"]    # PJ2-Seg: so M0
    receita_seguros_mensal: ["M0","M+1"]  # Seg WL: ambos
```

Builder le esse campo:
```python
proj_periodos = card.apresentacao.proj_periodos_por_indicador.get(rec_id, ["M0"])
if not proj_periodos:
    # render apenas Realizado MTD + Meta (sem pbars de projecao)
elif "M+1" in proj_periodos:
    # render Realizado + M0 + M+1
else:
    # render Realizado + M0
```

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
