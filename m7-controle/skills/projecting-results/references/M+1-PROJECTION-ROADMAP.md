# M+1 Projection Roadmap — Volume + Receita

> Roadmap de evolucao da projecao de Volume e Receita para horizonte M+1 (mes seguinte) na vertical Consorcios. Replicavel para Seguros WL/RE.

**Status atual** (2026-05-05): metodologia option (a) interim em producao. Option (b) target documentado abaixo, pendente implementacao post-ritual.

> **⚠️ CORRECAO DE RECEITA 2026-06-19 (supersede as formulas Seg deste roadmap):**
> a formula de receita Seg `(Vol × 0,5)/12` esta ERRADA. O `valor da oportunidade`
> do funil Seg JA e a comissao (valor de aceitacao), entao **Receita_Seg = oportunidade
> / 12** (sem rate). Volume_Seg_WL = Receita × 2; Seg RE projeta Receita (opp/12) mas
> nao Volume. Cons mantem Volume = oportunidade (carta) e Receita = Volume × 0,035/12.
> Isso APOSENTA o ISSUE #4 (campo de premio) e o bloqueio da taxa RE. Fonte de verdade:
> `projection-methodology.md` secao "Formula de Receita projetada — CORRIGIDA".
>
> **Gaps:** Gap 2 (historico 3m) e Gap 5 (proj_periodos nos Cards) JA FEITOS (auditados
> 2026-06-19). Gap 1 (data_competencia no volume) = NAO-PROBLEMA (volume usa data_venda,
> correto; nao existe coluna de competencia p/ contratos e nao precisa). Gap 3 (stage
> metrics) RESOLVIDO via exit-based + selector mes-anterior (ver KNOWN_ISSUES #6).

---

## Decisao do usuario (2026-05-05)

Em sessao com o usuario foi definida a seguinte estrategia:

### Option (a) — INTERIM (em producao no ciclo 2026-05-04)

> **CORRECAO 2026-05-13:** Volume M+1 e exclusivamente componente Bitrix
> funil (nao ha lagging de competencia futura para Volume). Versao
> anterior desta secao misturava `consorcio_contratos.data_competencia`
> como "Realizado_M+1" do Volume — ISSO ESTAVA ERRADO. Esse ledger
> refere-se a **Receita Real M+1** (parcelas de comissao ja cravadas),
> nao a Volume.

**VOLUME** (todas verticais — Cons, Seg WL, Seg RE, PJ2):
- `Realizado_MTD` (M0): SUM(`valor_base`) de `consorcio_contratos` filtrado por `situacao='ATIVO'` e agrupado por `data_competencia=M0` (so Cons). Em Seg, fonte equivalente da tabela de premio MTD.
- `Projecao M0` = `Realizado_MTD` + `componente_funil_M0` (deals do funil que fecham em M0)
- `Projecao M+1` = `componente_funil_M+1` (deals do funil que fecham em M+1)
  - **Sem componente "Real_M+1"** — nao ha registro de volume futuro cravado.
  - Aplica-se igualmente a todas as verticais.

**RECEITA**:
- **Cons** `Realizado_competencia_M+1`: SUM(`valor_comissao`) de `consorcio_receita` filtrado por `competencia=M+1` (ja funciona — coleta inclui M+1 nativamente). **Parcelas dos contratos ja formalizados** que vencem em M+1.
- **Seg WL/RE/PJ2-Seg** `Realizado_competencia_M+1`: **0** (sem ledger de competencia futura para comissao Seg).
- **Cons** `Projecao M0` = `Real_competencia_M0` + (`Vol_Projecao_M0` × 0,035 / 12)
- **Cons** `Projecao M+1` = `Real_competencia_M+1` + (`Vol_Projecao_M+1` × 0,035 / 12)
- **Seg WL** `Projecao M0` = `Real_MTD_seg` + (`Vol_Projecao_M0` × 0,5 / 12)
- **Seg WL** `Projecao M+1` = (`Vol_Projecao_M+1` × 0,5 / 12)  # sem Real
- **Seg RE / PJ2-Seg**: nao projetar Receita M+1.

**Caracteristica do gap interim**: como `componente_funil_M+1` esta hard-coded a 0 (Gap 4 pendente), na pratica:
- Volume M+1 Cons hoje = 0 (so apareceria pelo funil; lagging nao existe)
- Receita M+1 Cons hoje = `Real_competencia_M+1` apenas (componente funil colapsa)
- Receita M+1 Seg WL hoje = 0 (sem Real, sem funil)

Quando Gap 4 for implementado, `componente_funil_M+1` passa a ter valor real e Volume M+1 + Receita M+1 deixam de subestimar.

---

### Option (b) — TARGET (post-ritual, especificacao aqui)

#### VOLUME (todas verticais — sempre Bitrix funil, sem lagging)

```
Realizado_MTD: SUM(valor_base) WHERE data_competencia = M0 (so M0; sem M+1)
  - Cons: m7Bronze.consorcio_contratos.data_competencia
  - Seg WL/RE: tabela equivalente de premio liquido MTD

Projecao M0 = Realizado_MTD + Σ [Volume_estagio × stage_probability_estagio]
  onde:
    Σ aplica APENAS a estagios cujo `tempo_ciclo_atual` cabe dentro
    de `dias_uteis_restantes_no_mes_corrente` (verificacao dia-a-dia)

Projecao M+1 = Σ [Volume_estagio_M0 × stage_probability_estagio]
  onde:
    Σ aplica APENAS a estagios cujo `tempo_ciclo_atual` EXCEDE
    `dias_uteis_restantes_no_mes_corrente` E cabe dentro de
    `dias_uteis_restantes_M0 + dias_uteis_M+1`
  NOTA: NAO somar nenhum "Realizado_M+1" — volume futuro nao existe cravado.
```

#### RECEITA — por vertical

**Cons** (e PJ2 subset Cons):
```
Realizado_competencia_M = SUM(valor_comissao)
                          FROM m7Bronze.consorcio_receita
                          WHERE competencia = M           # M = M0 ou M+1

Projecao M0  = Real_competencia_M0  + (Vol_Projecao_M0  × 0,035 / 12)
Projecao M+1 = Real_competencia_M+1 + (Vol_Projecao_M+1 × 0,035 / 12)
```

**Seg WL** (e PJ2 subset Seg, quando habilitar):
```
Realizado_MTD = SUM(valor_comissao) FROM tabela_comissao_seg WHERE mes = M0
                # so existe para M0 (sem competencia futura cravada)

Projecao M0  = Real_MTD + (Vol_Projecao_M0  × 0,5 / 12)
Projecao M+1 =            (Vol_Projecao_M+1 × 0,5 / 12)   # sem Real, colapsa
```

**Seg RE / PJ2 (Total)**: nao projetar Receita M+1.

#### Regra de calibracao do `stage_probability` e `tempo_ciclo`

> "Implementar com que o G2.2 sempre use o `stage_probability` de cada estagio e tempo de cada estagio do mes anterior ate metade do mes; quando passar metade do mes ele passa a usar ja os valores do mes atual."

**Algoritmo de selecao da fonte**:

```python
if dia_atual <= dia_15_do_mes:
  stage_probability_vigente = MEDIANA(stage_probability_mes_anterior_completo)
  stage_duration_vigente = MEDIANA(stage_duration_mes_anterior_completo)
else:
  # >= dia 16: ja temos amostra suficiente do mes corrente
  stage_probability_vigente = MEDIANA(stage_probability_mes_corrente_MTD)
  stage_duration_vigente = MEDIANA(stage_duration_mes_corrente_MTD)
```

**Calculo das taxas reais** (substitui defaults YAML):

```sql
-- stage_probability por estagio (% deals nesse estagio que viraram WON no mes)
SELECT
  estagio_origem,
  COUNT(deals_que_avancaram_para_WON) / COUNT(deals_que_passaram_pelo_estagio) AS rate_real
FROM stagehistory_completo
WHERE data BETWEEN inicio_mes_anterior AND fim_mes_anterior
GROUP BY estagio_origem;

-- stage_duration por estagio (mediana de dias parados nesse estagio antes de avancar)
SELECT
  estagio,
  MEDIAN(data_saida - data_entrada) AS duration_real_dias
FROM stagehistory_completo
WHERE data BETWEEN inicio_mes_anterior AND fim_mes_anterior
GROUP BY estagio;
```

#### Exemplo concreto

> Cenario: dia 20 de Maio, deal em estagio "Prospeccao" com `tempo_ciclo_atual_Prospeccao = 45 dias`.
> `dias_uteis_restantes_no_mes_corrente_Maio` = 7 dias.
>
> `45 > 7` → o deal NAO conseguira avancar pra WON em Maio.
> → entra em `Projecao_M+1`.
> → contribuicao = `valor_base_deal × stage_probability_Prospeccao_vigente`.

---

## Gaps de implementacao (acoes pendentes)

### Gap 1 — Adicionar `data_competencia` no script de Volume

**Arquivo**: `01-Metas/Biblioteca-de-Indicadores/Consorcios/scripts/volume_consorcio_mensal.py`

**Mudanca necessaria**: o `WHERE` clause deve incluir `OR data_competencia >= 'data_inicio'` (ou trocar `data_venda` por `data_competencia` se o produto/dominio usar `data_competencia` como ground truth).

**Validacao prerequisita**: confirmar via `DESCRIBE TABLE m7Bronze.consorcio_contratos` que a coluna `data_competencia` existe e e distinta de `data_venda`. (Em 2026-05-05 o ClickHouse caiu na hora da verificacao; o user confirmou manualmente que a coluna devolve R$ 25,7M Maio + R$ 39,8M Junho).

**Output esperado**: o JSON consolidado passa a ter linhas N1/N2/N3/N4/N5 com `mes >= 2026-06` populadas (atualmente todas R$ 0 por filtro `data_venda`).

**Replicar em**: `volume_seguros_mensal.py` (vertical Seguros WL e RE).

### Gap 2 — Coleta historica de oportunidades_criadas_funil

**Arquivo**: `01-Metas/Biblioteca-de-Indicadores/Consorcios/scripts/oportunidades_criadas_funil.py`

**Mudanca necessaria**: o script atualmente filtra apenas o mes corrente. Precisa retornar minimo 3 meses de historico (Mar/Abr/Mai 2026 no caso) para alimentar a calibracao de `stage_probability_mes_anterior` e `stage_duration_mes_anterior`.

**Replicar em**: outras verticais que adotem option (b).

### Gap 3 — Criar query de stage_probability + stage_duration vigentes

**Arquivo novo sugerido**: `01-Metas/Biblioteca-de-Indicadores/Consorcios/scripts/stage_metrics_vigentes.py`

**Output esperado**: JSON com 6 estagios × 2 metricas (probabilidade + duracao mediana), com regra de selecao (mes_anterior ate dia 15, mes_corrente apos dia 15).

**Consumido por**: `projecting-results/SKILL.md` Fase 2 (substitui defaults do YAML).

### Gap 4 — Atualizar pipeline_conversion_extended para v6.4.0 stage_aware

**Status:** ✅ **CONCLUIDO 2026-05-13**.

**Implementacao:**
- SKILL.md `projecting-results` Fase 2 ja documenta `pipeline_conversion_extended_v2` como **PREFERRED** (linhas 291-400). Documentacao foi feita em 2026-05-06.
- Indicators YAMLs Cons N3 (`volume_consorcio_mensal.yaml`) e Seg N3 (`volume_seguros_mensal.yaml`) ja tem `pipeline_conversion_extended_v2` com `preferred: true` desde 2026-05-06.
- Indicator PJ2 `volume_consorcio_mensal_pj2.yaml` atualizado 2026-05-13 (Gap 4 oficial) — antes usava `pipeline_conversion` legado.
- v1 (interim) mantido como **fallback** com `preferred: false` para casos em que `stage_metrics_vigentes` ou `historico_3m` ausentes.

**Mudanca conceitual 2026-05-13 (alinhada com nova spec):**
- Volume M+1 e **componente funil apenas** (Bitrix) em todas as verticais. Output decomposto:
  ```
  Vol_proj_M0  = Realizado_MTD + vol_componente_M0    # Realizado vem do indicator base, nao do v2
  Vol_proj_M+1 = vol_componente_M+1 + vol_entradas_novas_M+1   # SEM lagging
  ```
- A linha "Vol_proj_M+1 = vol_lagging_competencia_M+1 + ..." do SKILL.md (linha 364) foi reinterpretada: `vol_lagging_M+1` para Volume = 0 (nao existe registro de volume futuro cravado). O ledger `consorcio_contratos.data_competencia=M+1` e fonte de Receita Lagging (parcelas), nao de Volume.

**Parametros base (ja documentados em SKILL.md):**
- `parameters.stage_durations_source`: `prior_month_actuals_until_day_15_then_current_month`
- `parameters.transition_day`: 15
- `parameters.source_stage_metrics.indicador`: `stage_metrics_vigentes`
- `parameters.source_funil.indicador`: `oportunidades_ativas_funil` (com variante `_pj2` para PJ2 canal)
- `parameters.source_criadas.indicador`: `oportunidades_criadas_funil` + `historico_meses: 3`

**O que NAO mudou:**
- v1 (interim) continua disponivel como fallback graceful.
- Cards declaram `apresentacao.proj_periodos_por_indicador` por indicador (decisao 2026-05-13).

### Gap 5 — Card v2.5.0 declaracao formal

**Arquivo**: `02-Controle/Cards-de-Performance/Consorcios/card_con_n3_001.yaml`

**Mudancas**:
- Bump `version: 2.5.0`
- Bloco `kpi_references[volume_consorcio_mensal].projecao.componentes_mes_corrente`: declarar Realizado_MTD + Σ stage_probability × volume_estagio (com filtro temporal)
- Bloco `kpi_references[volume_consorcio_mensal].projecao.componentes_mes_seguinte`: declarar Σ stage_probability × volume_estagio_que_excede_M0 (SEM Realizado_M+1; volume futuro nao existe cravado)
- Bloco `kpi_references[receita_consorcio_mensal].projecao.componentes_mes_seguinte`: confirmar formula `Real_competencia_M+1 + (Vol_Projecao_M+1 × 0,035 / 12)`
- Adicionar `apresentacao.proj_periodos_por_indicador`:
  ```yaml
  apresentacao:
    proj_periodos_por_indicador:
      volume_consorcio_mensal:  ["M0", "M+1"]
      receita_consorcio_mensal: ["M0", "M+1"]
  ```

**Replicar em**:
- `card_seg_wl_n3_001.yaml` (v2.11.0 target):
  - `volume_seguros_mensal: ["M0", "M+1"]` (Bitrix funil; sem Real_M+1)
  - `receita_seguros_mensal: ["M0", "M+1"]` (formula `(Vol × 0,5)/12`, sem Real)
- `card_seg_re_n3_001.yaml` (v1.3.0 target):
  - `volume_seguros_mensal: ["M0", "M+1"]`
  - `receita_seguros_mensal: []` (NAO PROJETAR — indicator generico tem rate WL 0,5; aplicar a RE superestima. Re-habilitar quando rate RE for calibrada pelos coordenadores Emmanuel+Samuel).
- `card_pj2_n2_001.yaml`:
  - `volume_*_pj2: ["M0", "M+1"]` (todos canais)
  - `receita_consorcio_mensal_pj2: ["M0", "M+1"]`
  - `receita_seguros_mensal_pj2: ["M0"]` (M+1 OMITIDO em PJ2-Seg)
  - PJ2 Total Receita: soma das verticais (sem declaracao propria)

---

## Quando aplicar option (b)

Ordem sugerida:

1. **Gap 1** primeiro — sem ele, M+1 Volume Realizado fica em R$ 0 (option a interim usa override manual)
2. **Gap 2 + Gap 3** em paralelo — sem eles, stage_probability fica YAML default (5%/10%/20%/40%/70%/90%, defasada)
3. **Gap 4** consumindo o output de Gap 3 — modificacao do plugin
4. **Gap 5** declarando formalmente no Card

**Estimativa**: 2-3 dias uteis se priorizar; pode aproveitar ciclo 2026-05-13 para validar com dados reais.

---

## Referencias cruzadas

- Decisao do usuario: `02-Controle/Consorcios/2026-05/2026-05-04/CICLO.md` > Decisoes (entrada `[2026-05-05T08:??] USUARIO — Definida metodologia option (a) interim + option (b) target`)
- Implementacao option (a) interim: `02-Controle/Consorcios/2026-05/2026-05-04/wbr/wbr-consorcios-2026-05-04.data.json` (canonical SoT v6.3.0-option-a)
- Backups das outras versoes:
  - v6.1.0 (lagging_indicator): `backup_*` na pasta do ciclo
  - v6.2.0 uniforme (pipeline_conversion_extended uniform 0,30): `interim_v62uniform_*` na pasta do ciclo
- KNOWN_ISSUES (a criar quando relevante): `m7-operations/m7-controle/KNOWN_ISSUES.md`
