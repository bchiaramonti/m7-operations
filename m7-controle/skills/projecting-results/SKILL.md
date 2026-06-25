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

#### Metodo: `lagging_indicator` (DEPRECADO 2026-05-04)

> **DEPRECADO** — substituido por `installment_amortization` para receita
> (CON, SEG WL, SEG RE). Bug matematico documentado em
> [KNOWN_ISSUES.md](KNOWN_ISSUES.md) ISSUE #1: lag_weights somando 1.0 sem
> commission_rate produz `receita ≈ volume`. Mantido nos YAMLs com
> `applicable: false` e `deprecated: true` por rastreabilidade historica.
> Quando encontrado em projection.methods, IGNORAR e usar metodo `preferred`.

Projetava indicador derivado com base em pesos de defasagem (formula no
projection-methodology.md). NAO USAR.

#### Metodo: `installment_amortization` (NOVO 2026-05-04)

Resolve KNOWN_ISSUES.md ISSUE #1. Projeta receita decomposta em LAGGING
(parcelas das vendas dos N-1 meses anteriores caindo no mes alvo) + NOVA
(1a parcela das vendas que fecharao no mes alvo). Para CON, SEG WL, SEG RE.

**Formula consolidada (CORRETA — pos-correcao ISSUE #3):**
```
M0  (mes corrente):
projecao_M0  = realizado_mtd + (stage_probability_M0 × commission_rate / installments)
                                  └── APENAS componente funil novas vendas
                                      (NUNCA realizado_competencia ou lagging_volume)

M+1 (mes seguinte):
projecao_M+1 = lagging_parcelas_M+1 + (componente_funil_M+1 × commission_rate / installments)
                                          └── = 0 no metodo "a" interim
                                              (componente funil M+1 nao implementado;
                                               metodo "b" target adiciona — ver ISSUE #5)

  lagging_parcelas_M+1 = SUM(valor_comissao) FROM source_ledger
                         WHERE competencia = mes_M+1
                           AND data_venda < mes_M+1
                           [AND filtro_squad opcional]

  stage_probability_M0 / componente_funil_M+1 = vol_componente_funil retornado por
                          pipeline_conversion_extended (NUNCA vol_lagging — esse ja
                          esta contado em realizado_mtd / lagging_parcelas_M+1).
```

**Exemplo numerico (Consorcios Maio 2026, Douglas — pos-correcao):**
- realizado_mtd_M0 = R$ 32.687 (parcelas competencia=Maio de vendas anteriores)
- stage_probability_M0 = R$ 10.310.354 (pipeline expectation × taxa conv) — SO componente funil
- projecao_M0 = 32.687 + (10.310.354 × 0.035/12) = **R$ 62.759** (62% Improvavel)
- VERSAO ANTIGA com double-count: 32.687 + (16.807.751 × 0.035/12) = R$ 81.710 — **errada**.

Detalhes + impacto N1/N2: ver [KNOWN_ISSUES.md](KNOWN_ISSUES.md) ISSUE #3 secao "Impacto numerico".

**Inputs por vertical:**

| Vertical | commission_rate | installments | source_ledger |
|----------|----------------|--------------|----------------|
| Consorcios | 0.035 | 12 | `m7Bronze.consorcio_receita` |
| Seguros (WL+RE) | **n/a — sem rate** | 12 | `m7Prata.seguro_comissao_assessor_fuzzy` (so M0 Real) |

> **CORRECAO 2026-06-19 (usuario):** Seguros NAO usa `commission_rate`. O `valor da
> oportunidade` do funil Seg JA e a comissao (valor de aceitacao ≈ comissao estimada),
> entao **Receita_Seg = oportunidade / 12** direto (aplicar 0,5 dobrava-descontava).
> Volume_Seg_WL = Receita × 2. Seg RE projeta Receita (opp/12) mas NAO Volume. Cons
> mantem `× 0,035 / 12` (la a oportunidade = valor da carta = Volume). Ver
> references/projection-methodology.md "Formula de Receita projetada — CORRIGIDA".
> Isso aposenta o ISSUE #4 (campo de premio) e o bloqueio da taxa RE.

**Parametros do YAML (`parameters.*`):**
- `commission_rate` — fracao da comissao sobre valor do funil (CON 0.035; **SEG: n/a**,
  a oportunidade ja e a comissao -> Receita = opp/installments)
- `installments` — numero de parcelas mensais da comissao (default 12)
- `source_ledger.tabela` — tabela ClickHouse com cronograma das parcelas
  - CON: `m7Bronze.consorcio_receita`
  - SEG: `m7Prata.seguro_comissao_assessor_fuzzy`
- `source_ledger.campo_competencia` — coluna que indica o mes da parcela (default `competencia`)
- `source_ledger.campo_valor` — coluna do valor da parcela (default `valor_comissao`)
- `source_funil.indicador` — indicador volume_* a usar (deve estar projetado antes)
- `source_funil.horizon_aware: true` — quando true, le `projecao_mes_corrente` ou
  `projecao_mes_seguinte` do indicador conforme o horizon que esta sendo
  calculado (essencial para projetar M+1 corretamente)
- `commission_rate_by_produto` — opcional, override por mix (vida/patrimonial/auto/saude)

**Dependencia critica:** o indicador volume_* (leading) DEVE ter
`pipeline_conversion_extended` aplicado em ambos horizontes (mes_corrente E
mes_seguinte) ANTES deste indicador rodar. Fase 1 resolve a ordem.

**Aplicabilidade:**
- Quando `source_ledger` esta acessivel (ClickHouse online) → confidence high
- Quando ledger indisponivel → cair em `run_rate_linear` (fallback automatico)
- Quando `source_funil.indicador` nao tem projecao_mes_seguinte (ex: indicador
  sem `pipeline_conversion_extended` configurado) → calcular so mes_corrente
  e flag `mes_seguinte_unavailable: true`

**Como projetar M+1 (mes seguinte):**
- `lagging_parcelas` para M+1: SAME query mas `competencia = mes_M+1`. O ledger
  ja tem cronograma das parcelas das vendas existentes — basta WHERE
- `novas_vendas_funil` para M+1: usa `volume.componente_funil_M+1` × rate / 12.
  - Metodo "a" interim: `componente_funil_M+1 = 0` (nao implementado).
  - Metodo "b" target: `pipeline_conversion_extended_v2` retorna
    `vol_componente_M+1` decomposto (cycle-time-aware). Ver
    [M+1-PROJECTION-ROADMAP.md](references/M+1-PROJECTION-ROADMAP.md) e
    [KNOWN_ISSUES.md](KNOWN_ISSUES.md) ISSUE #5.
  - **NUNCA** usar `volume.projecao_mes_seguinte` direto se inclui
    `lagging_volume_M+1` — gera double-count contra `lagging_parcelas`.

> ⚠️ **CRITICAL — ISSUE #3 (KNOWN_ISSUES.md):** double-count quando `Vol_proj`
> inclui lagging volume.
>
> A formula `novas_vendas_funil = Vol_proj × commission/installments` ASSUME
> que `Vol_proj` representa **apenas o componente funil (vendas novas)**. Se
> `Vol_proj` incluir `realizado_competencia` (lagging volume — contratos ja
> formalizados), o termo se sobrepoe ao `lagging_parcelas` ja contado em
> `realizado_mtd` (M0) ou `lagging_parcelas` (M+1) — DOUBLE COUNT.
>
> **Formula correta:**
> - M0:  `realizado_mtd + (stage_probability_M0 × commission/installments)`
> - M+1: `lagging_M+1 + (componente_funil_M+1 × commission/installments)` —
>   onde `componente_funil_M+1` e ZERO no metodo "a" interim (sem componente
>   funil M+1 implementado), NAO `lagging_volume_M+1`.
>
> Workaround atual: `Card.apresentacao.projection_overrides` com `metodo: "a-fix"`.
> Detalhes + impacto numerico: ver [KNOWN_ISSUES.md](KNOWN_ISSUES.md) ISSUE #3.
>
> Ao implementar metodo "b" futuro, garantir que `pipeline_conversion_extended`
> retorne componentes separados (`vol_lagging` + `vol_componente_funil`); a
> formula receita usa **apenas** `vol_componente_funil`.

#### Metodo: `pipeline_conversion_extended` (v1 — fallback)

> **Status:** v1 e fallback de v2 desde 2026-05-06. Aplicado quando inputs
> de v2 indisponiveis (stage_metrics_vigentes ausente, historico_3m vazio,
> ou ledger inacessivel). Marcado `preferred: false` em Cards v2.5.0+.
> **Gap conhecido:** M+1 sem decomposicao componente funil — gera workaround
> "componente_funil_M+1=0" (interim conservador). v2 resolve este gap.

Substitui `pipeline_conversion` (stage_probability complexo) pelo modelo
simplificado `Vol × Taxa_Conversao` acordado com coordenador e documentado
em KNOWN_ISSUES.md (Volume).

**Formula mes corrente:**
```
projecao_mes_corrente = Vol_Oport_Ativas × Taxa_Conversao_Mes
                         (snapshot atual × taxa do mes)
```

**Formula mes seguinte:**
```
pipeline_residual_M0 = Vol_Oport_Ativas - projecao_mes_corrente

entradas_novas_M+1 = Media_oport_criadas_3m_meses × DU_M+1 / DU_mes_padrao

projecao_mes_seguinte = (pipeline_residual_M0 + entradas_novas_M+1) × Taxa_Conversao
```

**Parametros do YAML (`parameters.*`):**
- `source_funil.indicador` — indicador de oportunidades ativas (volume + qty)
- `source_funil.filtro_squad` — opcional (`wl`/`re`) para Cards split
- `source_taxa.indicador` — taxa de conversao (com fallback se ausente)
- `source_criadas.indicador` — oportunidades criadas para estimar M+1
- `source_criadas.horizonte_historico_meses` — janela da media movel (default 3)
- `componentes_mes_corrente.formula` — string descritiva
- `componentes_mes_seguinte.formula` — string descritiva
- `componentes_mes_seguinte.fallback_se_historico_insuficiente: run_rate_linear`

**Aplicabilidade:**
- Mes corrente: confidence high (snapshot direto do funil)
- Mes seguinte: confidence medium (requer historico de criadas; cair em
  `run_rate_linear` se historico < 3 meses)

> **MIGRACAO:** indicadores antigos com `pipeline_conversion` (stage_probability)
> ainda existem nos YAMLs mas estao marcados `applicable: false, deprecated: true`.
> Skill IGNORA-os e usa `pipeline_conversion_extended` quando disponivel.

#### Metodo: `pipeline_conversion_extended_v2` (PREFERRED — cycle-time-aware)

> **Status:** ✅ **ATIVO** desde 2026-05-06 para Consorcios e Seguros (WL+RE).
>
> **Pre-requisitos atendidos:**
>   - `stage_metrics_vigentes.yaml` (Cons) e `stage_metrics_vigentes_seg.yaml` (Seg) criados.
>   - Scripts `stage_metrics_vigentes.py` (Cons) e `stage_metrics_vigentes_seg.py` (Seg) existentes.
>   - `compute_historico_3m` integrado em `oportunidades_criadas_funil*.py` (campo `extras.historico_3m`).
>   - `volume_consorcio_mensal.py` usa `data_competencia` (Gap 1 Cons resolvido 2026-05-06).
>   - `volume_seguros_mensal.py` mantem todos os registros ate coluna `parcela_comissao` ser criada (Gap 1 Seg pendente schema).
>
> **Comportamento:** quando os 4 inputs estao disponiveis (snapshot funil +
> stage_metrics + historico_3m + ledger lagging), aplicar v2. Se algum input
> indisponivel, fallback graceful para v1 com flag `v2_fallback_to_v1: true`
> + razao registrada no output.
>
> **Migracao concluida em 2026-05-06:**
>   - v1 → `applicable: true` mas `preferred: false` (mantido como fallback)
>   - v2 → `applicable: true` + `preferred: true` (default em Cards v2.5.0+)

**Inputs obrigatorios:**
- Snapshot do funil: `oportunidades_ativas_funil` (campos `volume`, `quantidade`,
  `estagio`, `data_entrada_estagio` por deal — se disponivel).
- Stage metrics vigentes: `stage_metrics_vigentes` (script novo —
  `stage_probability` + `stage_duration_dias` por estagio×mes).
- Historico de criadas: `oportunidades_criadas_funil.historico_3m` (campo
  extras do output, populado por `compute_historico_3m`).
- Query lagging: usa `data_competencia` (NAO `data_venda`) na tabela
  `m7Bronze.consorcio_contratos`.

**Algoritmo dia-a-dia (executar quando o analyst processa o indicador):**

```
1. Calcular dias uteis (DU):
     DU_M0_restantes = DU restantes do mes corrente
     DU_M+1          = DU total do mes seguinte
     dias_M0  = DU_M0_restantes
     dias_M+1 = DU_M0_restantes + DU_M+1

2. Stage source — SEMPRE mes anterior completo (exit-based, 2026-06-19):
     stage_source_mes = mes_anterior_COMPLETO   # coorte resolvida madura
     # CORRECAO 2026-06-19: removido o switch do dia 15. stage_metrics agora e
     # EXIT-BASED (won_passers/resolved_passers por mes de RESOLUCAO) — a coorte
     # do mes corrente so amadurece no FIM do mes, entao no meio do mes degenera
     # a ~0 e zera o funil (validado retroativo Cons 06-17: corrente=R$0 vs
     # anterior=R$12,84M). Usar SEMPRE o ultimo mes COMPLETO. Ver
     # references/projection-methodology.md "Stage source".

3. Para cada deal D no funil ativo:
     estagio    = D.estagio_atual
     duration   = stage_metrics_vigentes[stage_source_mes][estagio].duration_dias
     probability = stage_metrics_vigentes[stage_source_mes][estagio].stage_probability

     IF duration < dias_M0:
         vol_componente_M0   += D.volume × probability
         qty_componente_M0   += probability
     ELSIF duration < dias_M+1:
         vol_componente_M+1  += D.volume × probability
         qty_componente_M+1  += probability
     ELSE:
         (deal fora do horizonte M0+M+1 — descartado)

4. Lagging do Volume (so M0 — Cons especifico):
     # CORRECAO 2026-05-13: lagging de Volume SO se aplica a M0 (Realizado MTD).
     # NAO ha lagging de Volume M+1 em nenhuma vertical — volume futuro nao existe
     # cravado em nenhum ledger. O `consorcio_contratos.data_competencia=M+1` e
     # fonte de Receita Lagging (parcelas), nao de Volume.
     vol_lagging_M0  = SUM(valor_base) FROM consorcio_contratos
                       WHERE data_competencia ∈ M0  AND situacao='ATIVO'
     vol_lagging_M+1 = 0  # NAO existe registro de volume futuro cravado

5. Entradas novas estimadas (apenas M+1):
     media_movel = MEAN(historico_3m[mes].qty)   # ultimos 3 meses
     vol_entradas_M+1 = media_movel × DU_M+1 / DU_mes_padrao
                                    × stage_prob_inicial  # estagio "Prospeccao"

6. Consolidacao final:
     Vol_proj_M0  = vol_lagging_M0  + vol_componente_M0
     Vol_proj_M+1 = vol_componente_M+1 + vol_entradas_M+1    # SEM lagging
```

**Output decomposto (OBRIGATORIO):**

```python
{
  "vol_lagging_competencia_M0":   float,    # so M0; nao existe M+1
  "vol_componente_M0":            float,    # via stage classification
  "vol_componente_M+1":           float,    # via stage classification
  "vol_entradas_novas_M+1":       float,    # via media movel
  "stage_breakdown_M0":   {...},  # detalhe para auditoria
  "stage_breakdown_M+1":  {...},
}
```

> **REVISAO 2026-05-13:** removido `vol_lagging_competencia_M+1` do output
> obrigatorio. Volume M+1 e exclusivamente derivado do funil Bitrix + entradas
> novas estimadas. Ver [projection-methodology.md](references/projection-methodology.md)
> secao 6.1 para a separacao entre **lagging de Volume** (so M0) e **lagging
> de Receita competencia** (M0 + M+1 via `consorcio_receita.competencia=M+1`).

**⚠️ AVISO — uso por receita formula `installment_amortization`:**

A formula receita consome **APENAS** o componente funil de **Volume**
(M0 ou M+1), NUNCA o vol_lagging:

- **Cons** (e PJ2 subset Cons):
  - M0:  `Real_competencia_M0  + (vol_componente_M0  × 0,035 / 12)`
  - M+1: `Real_competencia_M+1 + (vol_componente_M+1 × 0,035 / 12)`
  - onde `Real_competencia_M` = SUM(valor_comissao) FROM `consorcio_receita`
    WHERE competencia = M (parcelas ja cravadas)
- **Seg WL** (e PJ2 subset Seg, quando habilitar):
  - M0:  `Real_MTD_seg + (vol_componente_M0  × 0,5 / 12)`
  - M+1:                `(vol_componente_M+1 × 0,5 / 12)`   # Real_M+1 Seg = 0
- **Seg RE**: nao projetar receita (sem rate calibrada — `Card.proj_periodos_por_indicador.receita_seguros_mensal: []`).

Adicionar `vol_lagging_*` (volume de competencia) no calculo de receita
gera **DOUBLE COUNT** (parcelas ja contadas em `Real_competencia_M`).
Ver [KNOWN_ISSUES.md](KNOWN_ISSUES.md) ISSUE #3 para impacto numerico.

**Aplicabilidade:**
- Confidence: high quando todos os inputs disponiveis.
- Fallback: v1 (interim) quando `stage_metrics_vigentes` ainda nao gerado
  ou `historico_3m` vazio.

Para detalhes adicionais das formulas e casos especiais, consultar
[projection-methodology.md](references/projection-methodology.md) secoes
5.1 (v1) e 5.2 (v2), e [M+1-PROJECTION-ROADMAP.md](references/M+1-PROJECTION-ROADMAP.md).

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

### Fase 6.5 — Desagregacao por Especialista — v5.5.0

> **Nota de nomenclatura**: na hierarquia M7 oficial, **especialista = N3** (Douglas, Tereza, Claudia, Tarcisio); coordenador = N2 (Joel).
>
> **Tratamento de N2 no schema atual**: Joel e modelado como ator transversal (deals proprios via `ASSIGNED_BY_ID`), NAO como agregador dos N3. Deals do Joel aparecem como "Sem Especialista" no consumo do m7-ritual-gestao. Esta Fase 6.5 desagrega projecao apenas pelos especialistas listados em `apresentacao.responsaveis[]` do Card (N3) + linha "Sem Especialista" capturando o resto.
>
> **Schemas legacy** (incluindo `dados-consolidados-{vertical}.json` e codigo Python existente) usam o label `N2-Especialista` por legado historico. Esta secao usa "especialista" sem amarrar a numero de nivel; o consumo dos dados continua nas colunas/campos `N2` ou `especialista` que existem hoje. Renomeacao do schema esta fora do escopo desta versao.

Apos consolidar projecoes N1 (Fase 3), gerar projecoes por especialista aplicando os mesmos metodos do YAML em subsets de dados:

**Para cada especialista identificado em `apresentacao.responsaveis[]` (ou nas colunas de especialista dos dados consolidados):**

1. **Filtrar dados do especialista** em `dados-consolidados-{vertical}.json`:
   - Realizado MTD do indicador no especialista
   - Pipeline ativo do especialista (para `pipeline_conversion`)
   - Historico mensal do especialista nos N meses anteriores (para `lagging_indicator`)

2. **Aplicar mesmos `projection.methods[]`** do YAML, usando os dados do especialista como input. Resolver dependencias cruzadas tambem em nivel de especialista (ex: receita do Douglas usa volume projetado do Douglas).

3. **Consolidar via `projection.consolidation`** (mesma regra do N1).

4. **Calcular projecao do MES SEGUINTE** alem do mes corrente:
   - Para `run_rate_linear`: aplicar a mesma formula assumindo dias uteis cheios do proximo mes
   - Para `pipeline_conversion`: re-projetar com pipeline atual + entradas esperadas (criadas medias historicas) — output e estimativa nao garantida
   - Para `lagging_indicator`: usar projecoes de volume corrente + N-1 meses anteriores

**Output Fase 6.5: `analise/projection-by-especialista.json`** (na pasta do ciclo):

```json
{
  "vertical": "consorcios",
  "data_referencia": "YYYY-MM-DD",
  "especialistas": {
    "Douglas Silva": {
      "bitrix_id": "936",
      "volume_consorcio_mensal": {
        "realizado_mtd": 2380000,
        "meta_mes": 3250000,
        "projecao_mes_corrente": 6610000,
        "projecao_mes_seguinte": 6500000,
        "metodos_aplicados": ["pipeline_conversion", "run_rate_linear"],
        "classificacao": "Provavel",
        "confianca": "high"
      },
      "receita_consorcio_mensal": {
        "realizado_mtd": 138520,
        "meta_mes": 100000,
        "projecao_mes_corrente": 165000,
        "projecao_mes_seguinte": 150000,
        "metodos_aplicados": ["lagging_indicator", "run_rate_linear"],
        "classificacao": "Provavel",
        "confianca": "medium"
      }
    },
    "Tereza Bernardo": { ... },
    "Sem Especialista": {
      "bitrix_id": null,
      "volume_consorcio_mensal": {
        "realizado_mtd": 2510000,
        "meta_mes": null,
        "projecao_mes_corrente": 0,
        "projecao_mes_seguinte": 0,
        "nota": "Bridge gap — sem meta atribuida; projecao nao calculada"
      }
    }
  }
}
```

**Quando E5 NAO consegue desagregar (fallback graceful):**
- Indicador sem dados N2 no JSON consolidado: registrar `projecao_mes_corrente: null` + `nota: "dados N2 indisponiveis"`
- Especialista sem realizado historico (>= 2 meses): aplicar apenas `run_rate_linear`, marcar `baixa_confianca: true`
- "Sem Especialista" (bridge gap): incluir SEMPRE no JSON com realizado_mtd, mas projecao_mes_corrente = 0 (sem meta atribuida) e nota explicando

**Importante:** este output e **complementar** ao `projection-report.md` (que continua focado em N1). Material-generator do m7-ritual-gestao consome `projection-by-especialista.json` para renderizar mini-graficos no Slide 9 (Projecao) por especialista.

### Fase 6.6 — Consolidacao N1 (vertical inteira) — v6.1.0

> **NOVO 2026-05-06**: bloco `consolidado_n1` no `projection-by-especialista.json`
> consumido pelo material-generator do m7-ritual-gestao para renderizar
> projecao consolidada da vertical no Slide Consolidado N{N3} (tweak C7).

Apos gerar o dict `especialistas` (Fase 6.5), agregar para nivel N1 da vertical
para os indicadores `volume_*` e `receita_*` (KPIs principais):

**Algoritmo de consolidacao** (executar pelo analyst):

1. **Para cada KPI principal** (volume + receita da vertical):
   - Identificar quais especialistas tem o indicador projetado
   - Aplicar regra de consolidacao do `projection.consolidation` do YAML do indicador:
     - `sum`: somar campos `realizado_mtd`, `projecao_mes_corrente`, `projecao_mes_seguinte`, `meta_mes`, `gap_meta` de TODOS especialistas (incluindo "Sem Especialista" se tem realizado_mtd > 0)
     - `median_confident`: usar mediana dos campos de especialistas com `confianca >= medium`
     - `weighted_avg`: usar media ponderada por meta_mes
   - Default: `sum` (apropriado para volume e receita, que sao aditivos N5→N1)

2. **Calcular `gap_meta`**: `meta_mes - projecao_mes_corrente` (negativo = gap; positivo = projecao acima da meta)

3. **Calcular `classificacao_consolidada`**:
   - Provavel: projecao_mes_corrente >= 90% × meta_mes
   - Possivel: 70% <= projecao_mes_corrente < 90%
   - Improvavel: projecao_mes_corrente < 70%
   - Se `meta_mes == null` ou `meta_mes == 0`: classificacao = "sem_meta"

4. **Identificar `metodo_consolidacao_aplicado`**: registrar regra usada (sum/median/etc.)

**Output (adicionar ao projection-by-especialista.json):**

```json
{
  "vertical": "consorcios",
  "data_referencia": "YYYY-MM-DD",
  "especialistas": { ... },
  "consolidado_n1": {
    "receita_consolidada_mensal": {
      "realizado_mtd": float,
      "projecao_mes_corrente": float,
      "projecao_mes_seguinte": float,
      "meta_mes": float,
      "gap_meta": float,
      "classificacao": "Provavel|Possivel|Improvavel|sem_meta",
      "metodo_consolidacao": "sum|median_confident|...",
      "fonte": "agregado de N3 (Douglas + Tereza + Sem Especialista)"
    },
    "volume_consolidada_mensal": {
      "realizado_mtd": float,
      "projecao_mes_corrente": float,
      "projecao_mes_seguinte": float,
      "meta_mes": float,
      "gap_meta": float,
      "classificacao": "Provavel|Possivel|Improvavel|sem_meta",
      "metodo_consolidacao": "sum",
      "fonte": "agregado de N3"
    }
  }
}
```

**Quando E5 NAO consegue consolidar (fallback graceful):**
- Se `especialistas` esta vazio: omitir `consolidado_n1` + flag `consolidated_unavailable: true` na raiz do JSON
- Se algum especialista tem `projecao_mes_corrente: null`: nao incluir no `sum` (a soma e dos disponiveis); registrar lista `especialistas_excluidos` no bloco

**Consumo downstream**:
- Material-generator do m7-ritual-gestao consome `consolidado_n1` para renderizar:
  - Card de projecao consolidada da vertical no Slide N3 Consolidado (tweak C7 do plano de ritual 2026-05-06)
  - Comparativo Realizado vs Meta vs Projecao do nivel N1 alem dos N3 individuais

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
- [ ] **`projection-by-especialista.json` gerado** (Fase 6.5) com projecoes mes corrente + mes seguinte por especialista, incluindo "Sem Especialista" (v5.5.0+)
- [ ] **`consolidado_n1` populado** (Fase 6.6, v6.1.0+) com projecao agregada da vertical para volume e receita

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
