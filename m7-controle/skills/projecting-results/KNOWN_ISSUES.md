# KNOWN ISSUES — projecting-results (m7-controle)

> Documento de issues conhecidos da skill `projecting-results`. Use para
> rastrear problemas estruturais que precisam de correcao antes do uso em
> producao confiar na projecao.

---

## ISSUE #6 — stage_probability degenerava a 0 (v2 zerava o funil)

**Status:** ✅ **RESOLVIDO 2026-06-19** (validado ao vivo no Bitrix + retroativo Cons 06-17).

**Eram 2 bugs sobrepostos em `stage_metrics_vigentes`** (lib `m7_extract_utils.compute_stage_metrics_vigentes`):
1. **Entry-cohort:** ancorava em mes de ENTRADA → mes corrente degenera a ~0 (quem
   entrou ainda nao ganhou) → `pipeline_conversion_extended_v2` zerava M0/M+1
   (por isso Cons 06-17 usou v1).
2. **Won-detection por `SEMANTIC_ID='S'`:** perdia os 6 fake-closed stages do Cons
   (pegava ~3 wons em 959 deals).

**Fix:** EXIT-BASED — `stage_probability = won_passers / resolved_passers` ancorado
no mes de RESOLUCAO (coorte won∪lost madura); won-detection via `won_stage_ids`
(Cons usa os 6 fake-closed; Seg usa fallback 'S' pois C156:WON e SEMANTIC='S').
Aplicado a Cons + Seg WL/RE + PJ2 (PJ2 mapeia won_stage_ids por pipeline).

**Selector dia-15 CORRIGIDO junto:** a regra "dia 15 troca p/ mes corrente" era de
entry-cohort. Com exit-based, a coorte do mes corrente so amadurece no FIM do mes →
usar SEMPRE o mes anterior COMPLETO. Validacao retroativa (funil real Cons 06-17):
componente_funil = R$ 0 (mes corrente Jun) vs **R$ 12,84M (mes anterior Mai)**.

**Pendente:** Gaps 1/2/5 do roadmap (data_competencia, historico 3m, declaracao Card);
validar num run-weekly real. NOTA: a Biblioteca (lib+scripts+YAMLs) fica na pasta de
dados (NAO git); so os docs desta skill (methodology + SKILL) estao versionados.

---

## ISSUE #1 — `lagging_indicator` matematicamente quebrado para receita

**Status:** ✅ **RESOLVIDO 2026-05-04** — substituido por novo metodo
`installment_amortization` (Cards CON v2.4.0, SEG WL v2.10.0, SEG RE v1.2.0;
indicadores `receita_consorcio_mensal` e `receita_seguros_mensal` atualizados;
SKILL.md `projecting-results` documenta o novo metodo). Volume tambem
formalizado via `pipeline_conversion_extended` (resolve KNOWN_ISSUES Volume
em paralelo). Ambos metodos suportam horizons `[mes_corrente, mes_seguinte]`.

**Identificado em:** 2026-04-29 (auditoria pos-deck Ritual SEG v6)
**Severidade:** CRITICA — afetava toda projecao de receita CON e SEG
**Origem:** `references/projection-methodology.md` linhas 270-314
**Resolucao:** ver Solucao proposta (abaixo) — implementada na integra em 2026-05-04

### Problema

O metodo `lagging_indicator` aplicado a receita usa a formula:

```
projecao_receita = Σ(volume_leading[mes_atual - lag_months[i]] × lag_weights[i])
```

Com parametros atuais nos YAMLs `receita_consorcio_mensal.yaml` e
`receita_seguros_mensal.yaml`:

```yaml
lag_months:  [1, 2, 3]
lag_weights: [0.5, 0.3, 0.2]   ← soma = 1.0
```

Isso produz `receita_proj ≈ media_ponderada(volume) × 1.0`, ou seja, o resultado
e essencialmente o proprio volume. **Receita projetada = ~90-100% do volume**,
o que e MATEMATICAMENTE IMPOSSIVEL para comissao real:

| Vertical | Comissao M7 real | Receita_proj atual |
|----------|------------------|---------------------|
| Consorcios | ~3,5% sobre valor da carta | ~100% (errado por ~30x) |
| Seguros | ~50% no 1o ano (vida) ou 5-25% (outros) sobre premio anualizado | ~100% (errado por ~2-20x) |

### Evidencia

A propria methodology.md (linha 313-314) admite:

> "Este valor e a RECEITA DERIVADA do volume com lag. A taxa de conversao
> volume→receita (comissao rate) ja esta **implicita nos lag_weights calibrados**."

Mas os pesos `[0.5, 0.3, 0.2]` somam 1.0 — sao apenas distribuicao temporal,
**NAO foram calibrados empiricamente** com dados historicos volume↔receita.

### Mitigacao temporal (em uso)

- Skill aplica `consolidation: median_confident` com `min_methods: 1` ou 2.
- Quando `run_rate_linear` (high confidence) tambem roda, mediana dos 2 metodos
  puxa para um meio-termo defensavel.
- No fim-de-ciclo (DU restante = 1), analyst tem aplicado override manual para
  usar so `run_rate_linear` quando `lagging_indicator` diverge >2x do MTD
  observado (decisao registrada em CICLO.md de cada ciclo).

### Solucao proposta — Novo metodo `installment_amortization`

Definida com o coordenador de Seguros em 2026-04-29 (apos discussao com BC).

**Formula:**

```
Receita_Mes_TOTAL = Receita_NOVA + Receita_LAGGING

NOVA    = (Vol_Oportunidades_Ativas × Taxa_Conversao_Mes) × commission_rate / installments
LAGGING = Σ_(k=1..installments-1) ClickHouse.parcelas_a_pagar[mes][venda_M-k]
```

**Parametros por vertical:**

| Vertical | commission_rate | installments | source ledger |
|----------|----------------|--------------|----------------|
| Consorcios | 0.035 | 12 | `m7Bronze.consorcio_receita` |
| Seguros | 0.50 (1o ano) | 12 | `m7Prata.seguro_comissao_assessor_fuzzy` |

**Fontes:**
- NOVA → Bitrix24 (funil snapshot + taxa conversao)
- LAGGING → ClickHouse (ledger oficial das comissoes contratadas)

### Volume — formula simplificada (em paralelo)

A metodologia atual `pipeline_conversion` para volume usa modelo de stages
detalhado (com `stage_conversion_rates` e `stage_duration_days` por estagio),
mas os scripts de coleta atuais NAO retornam stage breakdown por deal — entao
a formula complexa nao consegue ser aplicada com fidelidade.

**Simplificar para:** `Vol_proj = Vol_Oportunidades_Ativas × Taxa_Conversao_Mes`

Este e o que o coordenador de Seguros tambem confirmou. E aproximacao razoavel
quando stage breakdown nao esta disponivel.

### Plano de implementacao

Tracking via ClickUp PA (a criar em pa-resultado 901326795742).

Itens criticos:
1. Investigar ClickHouse: `MAX(competencia)` em `consorcio_receita` e
   `seguro_comissao_assessor_fuzzy` — confirmar se ledger ja tem cronograma
   futuro das vendas passadas (simplifica drasticamente o calc do LAGGING)
2. Atualizar 4 YAMLs (volume + receita × CON + SEG)
3. Atualizar Cards CON N3 e SEG N3
4. Atualizar `references/projection-methodology.md` (adicionar metodo 7
   `installment_amortization`)
5. Atualizar logica de calculo na skill `projecting-results`
6. Calibrar commission_rate com 6-12m de dados historicos antes de marcar
   metodo como `confidence: high`

### Workaround atual (ate fix)

- Mes corrente (Abr): usar `run_rate_linear` (e o que a skill atual ja faz no
  fim-de-ciclo via override do analyst — defensavel)
- Mes+1 (Maio): NAO renderizar projecao no deck do ritual ate metodologia
  estar implementada. Atualmente removido do Slide 9 (v7 do deck SEG ritual
  2026-04-29).

### Refs

- WBR Seguros 2026-04-29 (Anomalias): documenta override manual
- CICLO.md Seguros/2026-04-29: log das versoes v1-v7 do deck
- Card SEG N3 e Card CON N3: notas inline sobre metodologia em revisao
- Discussao com coordenador Seguros: 2026-04-29 (definiu formulas finais)

---

## ISSUE #2 — Componente "Deals ja em andamento" (LAGGING) nao implementado

**Identificado em:** 2026-04-29 (refinamento metodologico apos Issue #1)
**Severidade:** ALTA — sem este componente, projecao de receita TOTAL fica incompleta
**Origem:** discussao com coordenador Seguros 2026-04-29

### Problema

A formula nova `installment_amortization` (proposta em Issue #1) tem 2 componentes:

```
Receita_Mes_TOTAL = Receita_NOVA + Receita_LAGGING

NOVA    = (Vol_Ativas × Taxa_Conv) × commission_rate / installments       ← Bitrix
LAGGING = Σ parcelas correntes 2..12 das vendas dos 11 meses anteriores   ← ClickHouse
```

O componente NOVA e relativamente simples — funil Bitrix tem todos os inputs.

O componente LAGGING e a feature pendente: precisa puxar do **ClickHouse ledger**
(consorcio_receita / seguro_comissao_assessor_fuzzy) as parcelas que estao
"vivas" no mes-alvo das vendas anteriores. Cada venda contribui com 1/12 da
comissao por 12 meses.

### Implementacao

**Caminho A (preferido — se ClickHouse ja tem cronograma futuro):**
```sql
SELECT SUM(valor_comissao)
FROM m7Bronze.consorcio_receita
WHERE competencia = '<mes_alvo>'
  AND data_venda < '<mes_alvo>';  -- parcela de venda anterior
```

**Caminho B (fallback — se nao tem cronograma futuro):**
Calcular manualmente: para cada venda dos ultimos 11 meses, dividir comissao
total por 12 e atribuir ao mes correspondente da parcela.

### Investigacao pendente

```sql
-- Confirmar se ledger ja tem competencia futura
SELECT MAX(competencia) FROM m7Bronze.consorcio_receita;
SELECT MAX(competencia) FROM m7Prata.seguro_comissao_assessor_fuzzy;
```

Se MAX(competencia) > hoje → Caminho A (simples)
Se MAX(competencia) <= hoje → Caminho B (precisa calcular cronograma)

### Onde viver

- YAML do indicador (`receita_*_mensal.yaml`): novo parametro
  `lagging_source: clickhouse` no metodo `installment_amortization`
- Card de Performance (`card_*_n3_001.yaml`): nota explicativa em
  `projecao.nota` (item 3 da lista)
- Skill `projecting-results`: implementar logica de query ClickHouse + soma
- KNOWN_ISSUES (este doc): este item

### Status atual no deck do ritual

Para o ritual SEG 2026-04-29 (deck v7), a projecao mostrada NAO inclui LAGGING
explicitamente — usa `run_rate_linear` que captura o LAGGING IMPLICITAMENTE
(ja que receita MTD ja inclui parcelas correntes que chegaram este mes). Mas
isso e workaround, nao decomposicao explicita.

---

## ISSUE #3 — Slide 9 funil deveria mostrar etapas Bitrix; SEG nao retornava stage (corrigido 2026-04-29; CON ja retornava)

**Identificado em:** 2026-04-29 (questionamento usuario apos deck v7)
**Severidade:** MEDIA — afeta legibilidade do Slide 9 mas nao bloqueia uso
**Origem:** `slide-structure.md` Secao Slide 9 (m7-ritual-gestao)
**Status:** SEG **REESCRITO 2026-04-29** (pendente validacao em runtime); CON
ja estava OK desde sempre.

### Problema (estado pre-correcao)

Per slide-structure.md do plugin `m7-ritual-gestao` Secao Slide 9:

> "Numero de estagios e variavel por vertical (definido pelos pipeline_stages
> do Card). Cores progressivas do mais escuro ao mais claro: primeira
> #424135, ultima #4CAF50."

A intencao e mostrar barras representando os estagios reais do funil Bitrix
(Prospeccao -> Apresentacao -> Formalizacao -> Cotacao -> Proposta -> Emissao
-> Onboarding em SEG; Prospeccao -> Investigacao -> Apresentacao -> Proposta
-> Emissao Contrato -> Cotas Alocadas em CON) com qty/volume por estagio.

### Estado por vertical (apos correcao 2026-04-29)

| Vertical | Script | Stage breakdown? | Output schema |
|----------|--------|------------------|----------------|
| **Consorcios** (`oportunidades_ativas_funil.py`) | OK desde sempre | SIM | Coluna `estagio` em N1×N5 (totais com estagio=NULL + breakdown por estagio) |
| **Seguros** (`oportunidades_ativas_funil_seg.py`) | **REESCRITO 2026-04-29** | SIM (apos rewrite) | Mesma estrutura — coluna `estagio` em todos os niveis |

### Acao executada para SEG (2026-04-29)

Reescrito `oportunidades_ativas_funil_seg.py` espelhando o padrao do CON:

1. Adicionado import `bitrix24_get_deal_stages`
2. `extract_data` agora puxa `stages` do pipeline 156 alem de deals
3. `transform_data` faz duas agregacoes:
   - `result_total` (estagio=NULL): hierarquia consolidada
   - `result_stage`: breakdown por estagio em cada nivel N1-N5
4. Output combinado tem coluna `estagio`
5. Checksum atualizado no YAML, marcado `rewritten_pending_runtime_validation`

### Acao pendente

1. **Validar SEG em runtime** — proxima execucao de
   `m7-controle:run-weekly seguros` deve gerar JSON com stage breakdown
2. **Atualizar material-generator** (m7-ritual-gestao/preparing-materials):
   - Preferir stage breakdown quando disponivel no JSON consolidado
   - Aging-buckets continua como fallback se script ainda nao foi atualizado
3. **Atualizar slide-structure.md** com regra: "se `data[].estagio != null`
   existe → renderizar estagios reais; senao fallback aging-buckets"

### Estado no deck atual (Ritual SEG 2026-04-29 v7)

Deck atual ainda usa aging-buckets workaround porque a re-execucao do script
SEG (com novo codigo) requer ambiente com MCP Bitrix24 + ClickHouse — nao
disponivel nesta sessao. Proxima execucao automatica do `run-weekly` vai
regenerar JSON com stage breakdown. A partir dai material-generator pode
mostrar etapas reais.

---

## ISSUE #4 — Campo "Valor do Premio Anualizado" Bitrix nao identificado (SEG)

**Status:** ✅ **RESOLVIDO/APOSENTADO 2026-06-19** (decisao do usuario). A premissa
estava errada: a formula receita NOVA Seg NAO precisa de um "premio anualizado". O
`valor da oportunidade` do Card (campo OPPORTUNITY do funil Seg = VALOR DE ACEITACAO
≈ comissao estimada, ver `reference_seguros_receita_potencial`) JA E a receita. Formula
correta: **Receita_Seg = valor_da_oportunidade / 12** (sem rate de comissao — aplicar
0,5 dobrava-descontava). Volume_Seg_WL = Receita × 2; Seg RE projeta Receita (opp/12)
mas nao Volume. NAO ha mais campo de premio a caçar nem taxa RE a calibrar. Ver
references/projection-methodology.md "Formula de Receita projetada — CORRIGIDA" + SKILL.md.

**Identificado em:** 2026-04-29 (definicao da formula receita SEG)
**Severidade:** ~~MEDIA~~ resolvido
**Origem:** discussao com coordenador Seguros 2026-04-29

### Problema (historico — premissa incorreta)

Formula receita NOVA SEG: `Valor_Premio_Anualizado × 50% / 12`

Mas qual campo do Bitrix24 representa o "Valor do Premio Anualizado"?
Hipoteses:

| Hipotese | Campo | Pro/Contra |
|----------|-------|-----------|
| (a) Campo dedicado | `UF_CRM_premio_anual` ou similar | Direto se existir; investigar |
| (b) OPPORTUNITY × 12 | OPPORTUNITY tratado como mensal | Simples; assumir errado se OPPORTUNITY for anual |
| (c) Campo custom Seguros | `UF_CRM_<id>` especifico criado pra SEG | Mais provavel; precisa achar id |

### Investigacao pendente

1. Listar custom fields do funil 156 (Seguros): `crm.deal.fields` ou
   `crm.userfield.list` filtrado por entityId DEAL
2. Confirmar com coordenador qual campo usar
3. Documentar em `01-Metas/Biblioteca-de-Indicadores/Seguros/receita_seguros_mensal.yaml`
   no `dependencies` e nos parametros do `installment_amortization`

Ate confirmar, formula receita NOVA SEG fica como **PENDENTE** no Card SEG.

---

## ISSUE #3 — Double-count em `installment_amortization` quando Vol_proj inclui lagging volume

**Status:** ⚠️ **ATIVO** — descoberto 2026-05-06 via auditoria do deck S19 Consorcios.
Workaround aplicado via `Card.apresentacao.projection_overrides` (metodo "a-fix")
no ciclo Consorcios 2026-05-04. Skill `projecting-results` precisa ser atualizada
para nao repetir em ciclos/verticais futuros.

**Identificado em:** 2026-05-06 (revisao matematica das projecoes Receita Consorcios S19)
**Severidade:** ALTA — afeta projecao de receita em todos os ciclos onde Vol_proj_M0 inclui lagging volume

### Problema

Formula `installment_amortization` documentada na SKILL.md:

```
projecao_mes_alvo = lagging_parcelas + novas_vendas_funil
novas_vendas_funil = Vol_proj_mes_alvo × commission_rate / installments
```

A formula **assume** que `Vol_proj_mes_alvo` representa **apenas o componente
funil (vendas novas esperadas)** — pipeline_conversion_extended puro:

```
projecao_mes_corrente = Vol_Oport_Ativas × Taxa_Conversao_Mes
```

Mas no metodo "a" interim aplicado (2026-05-04, Consorcios + Seguros), o
`Vol_proj_M0` foi calculado como:

```
Vol_proj_M0 = realizado_competencia_atual + stage_probability_componente
              └── lagging volume (contratos JA formalizados) +
                  └── pipeline expectation (novas vendas esperadas)
```

E para M+1 interim:

```
Vol_proj_M+1 = realizado_competencia_seguinte    [apenas lagging, ZERO funil]
```

**Consequencia matematica:** quando `installment_amortization` aplica
`(Vol_proj × commission/installments)` sobre um Vol_proj que **inclui lagging
volume**, esta gerando uma "1a-parcela-teorica" para vendas **cuja receita ja
esta no `realizado_mtd` (M0) ou `lagging_parcelas` (M+1)**. **Double count.**

**Exemplo concreto (Consorcios Maio 2026, Douglas):**

| Componente | Valor |
|---|---|
| Realizado MTD receita Maio | R$ 32.687 (parcelas competencia=Maio de vendas anteriores) |
| Realizado_competencia volume Maio | R$ 6.497.397 (MESMOS contratos cuja receita esta acima) |
| Stage probability Maio | R$ 10.310.354 (pipeline expectation × taxa conv) |
| Vol_proj_M0 (formula atual) | R$ 16.807.751 (lagging + stage) ← INCLUI lagging volume |
| Receita proj_M0 (formula atual) | R$ 32.687 + (16.807.751 × 0.035/12) = R$ 81.710 |
| **Double count detectado** | **(6.497.397 × 0.035/12) = R$ 18.951** ← contado 2x (uma como realizado_mtd, outra como pseudo-1a-parcela) |
| Receita proj_M0 SEM double count | R$ 32.687 + (10.310.354 × 0.035/12) = **R$ 62.759** |

Para Junho M+1, e ainda PIOR: `Vol_proj_M+1 = lagging_volume only`, entao
`(lagging_volume × 0.035/12)` e 100% sobre o mesmo conjunto de parcelas que ja
estao em `lagging_parcelas`. **Adicao errada por construcao.**

### Solucao correta (metodo "a-fix")

```
projecao_M0_receita  = realizado_mtd     + (stage_probability_M0 × 0.035/12)
                                            └── SO componente funil (novas)
projecao_M+1_receita = lagging_M+1       + (componente_funil_M+1 × 0.035/12)
                                            └── = 0 no metodo "a" interim
                                                  (componente funil M+1 ainda nao implementado)
```

**Mudanca chave:** a parcela "novas vendas" deve receber **APENAS** o
`stage_probability` (M0) ou `componente_funil_M+1` (quando implementado),
NUNCA o `realizado_competencia` ou `lagging_volume`.

### Impacto numerico (Consorcios Maio/Junho 2026)

| | Antes (com double count) | Depois (a-fix) |
|---|---|---|
| Douglas Receita Maio | R$ 81.710 (81% Possivel) | R$ 62.759 (62% Improvavel) |
| Douglas Receita Junho | R$ 109.040 (90% Possivel) | R$ 59.552 (49% Improvavel) |
| Tereza Receita Maio | R$ 55.791 (55% Improvavel) | R$ 36.719 (36% Improvavel) |
| Tereza Receita Junho | R$ 49.808 (41% Improvavel) | R$ 21.505 (18% Improvavel) |
| N1 Receita Maio | R$ 229.565 (114% Provavel) | R$ 153.703 (76% Possivel) |
| N1 Receita Junho | R$ 227.915 (94% Possivel) | R$ 113.153 (46% Improvavel) |

A versao "a-fix" e **mais conservadora e matematicamente correta**.

### Acoes pendentes

1. **Atualizar `installment_amortization.consolidacao` na SKILL.md** para:
   - M0: `realizado + (stage_probability_M0 × commission/installments)` — **NAO** `realizado + (Vol_proj_M0 × commission/installments)` quando Vol_proj inclui lagging.
   - M+1: `lagging_M+1 + (componente_funil_M+1 × commission/installments)` — quando componente funil M+1 nao existe (interim "a"), termo vai a zero, NAO `+(lagging_volume × commission/installments)`.

2. **Atualizar `pipeline_conversion_extended`** para retornar componentes
   separadamente: `vol_lagging` + `vol_componente_funil`. A formula receita
   usa apenas `vol_componente_funil`, nunca `vol_total`.

3. **Workaround atual (S19 Consorcios):** `Card.apresentacao.projection_overrides`
   com `metodo: "a-fix"` declara projecoes recalculadas manualmente. Ver
   `card_con_n3_001.yaml` v2.7.0 para exemplo.

4. **Backfill ciclos passados** (Consorcios + Seguros): re-rodar com formula
   correta para baseline historica comparativa antes de migrar para metodo "b".

5. **Garantir no metodo "b" futuro** (sessao planejada): que `Vol_proj` retornado
   tenha decomposicao explicita `{lagging, componente_funil}` para evitar repetir
   este bug.

---

## ISSUE #5 — M+1 Volume Lagging gap (cycle-time-aware projection)

**Status:** ⚠️ **ATIVO** — workaround metodo "a" interim em producao; correcao
via metodo "b" target. Ver [M+1-PROJECTION-ROADMAP.md](references/M+1-PROJECTION-ROADMAP.md)
para roadmap completo (5 gaps + algoritmo cycle-time-aware + selector dia 15).

**Identificado em:** 2026-05-05 (sessao de revisao metodologica com usuario)
**Severidade:** ALTA — afeta projecao Volume M+1 em todos os ciclos (CON, SEG WL, SEG RE)
**Trigger para resolucao:** implementacao das tarefas 5-12 do cleanup
2026-05-06 (ver plan-of-record)

### Problema

Query `volume_consorcio_mensal.py` (e equivalente em SEG) usa `data_venda`
em vez de `data_competencia` na tabela `consorcio_contratos` ao filtrar
contratos. Resultado:

- M+1 Volume captura **apenas contratos cujo `data_venda` ja caiu em M+1**
  — que e ZERO ou muito pouco no inicio do mes corrente (ja que `data_venda`
  representa quando o contrato foi formalizado, nao quando ele tem efeito
  contabil/competencia).
- Consequencia: M+1 Volume = ~zero no inicio do mes, subestimando
  drasticamente a projecao.

A coluna `data_competencia` representa o mes em que o contrato e atribuido
contabilmente (ledger oficial) — esse e o filtro correto para "contratos
com competencia em M+1".

### Workaround interim (metodo "a")

```
Vol_proj_M+1 = realizado_competencia_M+1   [APENAS lagging — sem componente funil]
```

- Conservador: nao adiciona expectativa de novas vendas em M+1.
- Aplicado em S19 Consorcios via `Card.apresentacao.projection_overrides`
  metodo "a-fix".
- Limita projecao M+1 ao que ja esta no ledger com competencia futura.

### Solucao target (metodo "b" — cycle-time-aware)

Implementacao via `pipeline_conversion_extended_v2`:

1. **Iterar deals do funil ativos** com `tempo_estimado_fechamento` por estagio.
2. **Calcular dias restantes:**
   - `dias_restantes_M0` = dias uteis (DU) restantes no mes corrente.
   - `dias_restantes_M+1` = `DU_M0_restantes + DU_M+1`.
3. **Classificar deal por horizonte:**
   - Se `tempo_ciclo_estagio < dias_restantes_M0` → contribui para M0
     (× `stage_probability`).
   - Senao se `tempo_ciclo_estagio < dias_restantes_M+1` → contribui para M+1
     (× `stage_probability`).
   - Senao (M+2 ou alem) → fora do horizonte.
4. **Stage source — regra dia 15:**
   - Antes do dia 15 do mes atual: usar medianas do **mes ANTERIOR** (mais
     estavel, baseline confirmado).
   - A partir do dia 15: usar medianas do **mes ATUAL** (vigente, mais real).
5. **Ponderar:** `Vol_componente_M+1 = Σ(deal_volume × stage_probability)`
   sobre deals classificados em M+1.

**Exemplo concreto:** deal em estagio "Prospeccao" entrou no funil dia 20 do
mes corrente. Cycle medio Prospeccao = 45d. DU restantes M0 = 7d. Como
`45d > 7d`, o deal nao fecha em M0. Mas `45d < (7d + 22d_DU_M+1) = 29d` ...
recalcular para o caso real. Se cycle ≤ 29d: entra em M+1, ponderado por
`stage_prob(Prospeccao) ≈ 0.05`. Caso contrario, fora do horizonte.

### Outputs esperados (metodo "b")

`pipeline_conversion_extended_v2` retorna:

```python
{
  "vol_lagging_competencia": float,    # do ledger (data_competencia ∈ horizonte)
  "vol_componente_M0": float,           # deals do funil que fecham em M0
  "vol_componente_M+1": float,          # deals do funil que fecham em M+1
  "stage_breakdown": {...}              # detalhe por estagio para auditoria
}
```

A formula `installment_amortization` para receita usa **APENAS**
`vol_componente_M0` (em M0) e `vol_componente_M+1` (em M+1) — NUNCA
`vol_lagging_competencia` (que ja e contado em `realizado_mtd` ou
`lagging_parcelas`).

### Acoes pendentes (cleanup 2026-05-06)

1. Adicionar nova secao `pipeline_conversion_extended_v2` em
   `references/projection-methodology.md`.
2. Atualizar `01-Metas/Biblioteca-de-Indicadores/Consorcios/volume_consorcio_mensal.yaml`
   declarando v2 como `preferred: true`.
3. Trocar `data_venda` → `data_competencia` em
   `01-Metas/Biblioteca-de-Indicadores/Consorcios/scripts/volume_consorcio_mensal.py`.
4. Adicionar coleta de `historico_3m` em
   `oportunidades_criadas_funil.py` (CON + SEG).
5. Criar script novo `stage_metrics_vigentes.py` (CON + SEG) para gerar
   `stage_probability_vigente` + `stage_duration_vigente` por estagio×mes.
6. Atualizar SKILL.md projecting-results com algoritmo dia-a-dia metodo "b".
7. Bump Card Consorcios v2.7.0 → v2.8.0 com componentes formais
   `lagging_competencia_M0/M+1`, `pipeline_funil_M0/M+1`, `entradas_novas_M+1`.
8. Replicar componentes formais nos Cards SEG WL e RE.

### Refs

- `references/M+1-PROJECTION-ROADMAP.md` — roadmap completo + 5 gaps
- ISSUE #3 (este doc) — double-count receita (relacionado; resolvido pelos
  mesmos componentes formais)
- CICLO.md Consorcios 2026-05-04 — log das 7 rodadas de fixes interim
