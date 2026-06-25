---
name: summarizing-actions
description: >-
  G2.2-E4: Le clickup-tasks-{vertical}.json (gerado em E2 Fase 1.5 a partir do
  ClickUp pa-resultado), classifica acoes por urgencia (Em dia / Atrasada / Critica),
  avalia eficacia das concluidas cruzando com dados de E2, e gera Relatorio de
  Acompanhamento de Acoes com metricas agregadas. Use when the pipeline advances to
  E4 after deviation analysis (E3), when /m7-controle:next reaches E4, or when
  /m7-controle:run-weekly executes the action tracking step.

  <example>
  Context: E3 concluido, pipeline avanca para acompanhamento de acoes
  user: "/m7-controle:next"
  assistant: Invoca analyst para ler clickup-tasks-{vertical}.json (gerado em E2 Fase 1.5), calcular aging e gerar relatorio de acoes
  </example>

  <example>
  Context: Usuario quer ver o status das acoes de uma vertical
  user: "Como estao as acoes de Investimentos?"
  assistant: Le o JSON ClickUp coletado em E2, classifica por urgencia e gera relatorio com metricas
  </example>
user-invocable: false
---

# Summarizing Actions — Acompanhamento de Acoes (E4)

> "Acao sem prazo e intencao. Acao atrasada sem escalonamento e negligencia."

Esta skill le o JSON `clickup-tasks-{vertical}.json` (gerado em E2 Fase 1.5 a partir do ClickUp `pa-resultado`), calcula aging e dias restantes, classifica por urgencia, avalia eficacia das concluidas e gera relatorio de acompanhamento com metricas agregadas. E a quarta etapa do pipeline semanal (E4).

> **SoT do Plano de Acao = ClickUp** (lista `pa-resultado` id `901326795742`). O legado `plano-de-acao.csv` foi descontinuado em 2026-04-30 — o snapshot vivo e gerado via ClickUp MCP em E2 Fase 1.5.

> **REGRA DE HANDOFF**: Ao invocar o agente analyst, NAO passe valores de dados no texto do prompt. Passe APENAS caminhos de arquivos (vertical, cycle folder, paths dos artefatos). O analyst deve usar Read tool para carregar os dados dos arquivos em disco.

## Dependencias Internas

- [templates/action-report.tmpl.md](templates/action-report.tmpl.md) — Template do Relatorio de Acompanhamento de Acoes
- Agent `analyst` — Executor da analise (invocado automaticamente)
- **Output de E2 Fase 1.5**: `dados/raw/clickup-tasks-{vertical}.json` — SoT do Plano de Acao (substitui CSV)
- Output de E2 (consolidacao): `dados/dados-consolidados-{vertical}.json` (cruzamento de eficacia)
- Output de E3: `analise/deviation-cause-report.md` (contexto de desvios)

> **Resolucao de caminhos**: o JSON ClickUp esta em `{cycle_folder}/dados/raw/clickup-tasks-{vertical}.json`, gerado em E2 Fase 1.5. NAO leia mais `plano-de-acao.csv` local. Parametros do ciclo vem de `CICLO.md`.

## Pre-requisitos (Entry Criteria)

- E3 concluido (verificar `analise/deviation-cause-report.md` na pasta do ciclo)
- **`dados/raw/clickup-tasks-{vertical}.json` existe** (gerado em E2 Fase 1.5). Se ausente, retornar a E2 antes de E4
- CICLO.md com `vertical` e `data_referencia` definidos

## Workflow

### Fase 1 — Ler JSON do ClickUp

> **Filtros ja aplicados em E2 Fase 1.5** (via ClickUp MCP):
> filtro por custom field `Vertical`, exclusao de subtasks, resolucao do
> `Responsavel Externo`. **Filter composto de escopo (v3.x — 2026-05-12)** aplica
> particionamento adicional em 2 chaves: `escopo_ritual_passado` + `ad_hoc_pos_ritual`
> + `metadata.escopo_modo`. Esta fase apenas le o JSON pronto e enriquece com
> aging/urgencia.

1. **Localizar o JSON** em `{cycle_folder}/dados/raw/clickup-tasks-{vertical}.json` (gerado por E2 Fase 1.5)
2. **Validar existencia**: se ausente, registrar em CICLO.md > Anomalias e PARAR — pedir para o usuario re-rodar E2 Fase 1.5 antes de prosseguir
3. **Read JSON** com schema novo:
   - Quando `metadata.escopo_modo == "filtrado"`: usar `escopo_ritual_passado` ∪ `ad_hoc_pos_ritual` (concatenacao) como `data[]`. Atribuir flag `origem_escopo: "ritual_passado"` ou `"ad_hoc"` por task.
   - Quando `metadata.escopo_modo == "primeiro_ciclo"`: usar `escopo_ritual_passado` como `data[]` (fallback sem filtro de escopo); flag `origem_escopo: "primeiro_ciclo"`.
   - **Frase de escopo (v3.x)**: relatorio E4 abre com:
     ```
     ## Escopo do ciclo

     Escopo: **{N}** tasks do ritual de {last_ritual_date} (E5 anterior)
     + **{M}** tasks ad-hoc criadas apos o ritual (status=open).

     Tasks pendentes antigas que NAO foram discutidas no ultimo ritual ficam
     **fora deste escopo** (politica G2.2 desde 2026-05-12).
     ```
     Quando `escopo_modo == "primeiro_ciclo"`, substituir por:
     ```
     ## Escopo do ciclo

     **Primeiro ciclo da vertical** (sem ata anterior). Escopo = todas as
     {N} tasks ativas. Escopo filtrado por ritual passa a aplicar a partir
     do proximo ciclo.
     ```
4. **Cruz-validar com Card** (opcional, para acoes cross-vertical):
   - Ler Card de Performance via `Glob('**/cards/{vertical}/*.yaml')`
   - Extrair `indicator_ids` de `kpi_references[]` e `kpis_analisar_como_contexto[]`
   - Marcar tasks cujo campo `indicador_impactado` aparece nesta lista (campo derivado `indicador_no_card: bool`)
5. **Validar**: se `data[]` vazio, gerar relatorio vazio com metricas zeradas e nota "Nenhuma acao ativa para a vertical no ClickUp"

**Campos-chave do JSON (saida da Fase 1.5 de E2, schema documentado em `collecting-data/SKILL.md` Fase 1.5):**

| Campo | Tipo | Origem |
|-------|------|--------|
| `id` | string | task.id |
| `name` | string | task.name (substitui `titulo` do CSV legado) |
| `status` | string | task.status.status |
| `priority` | string | `urgent\|high\|normal\|low` |
| `due_date` | YYYY-MM-DD | substitui `data_limite` |
| `vertical` | string | custom field `Vertical` |
| `responsavel_externo` | string | custom field `Responsavel Externo` (substitui `responsavel` do CSV) |
| `assignees` | array | executor operacional (referencia cruzada — nao usar como owner) |
| `indicador_impactado` | string | custom field auto-descoberto |
| `origem` | string | custom field auto-descoberto |
| `receita_impacto` | number | custom field auto-descoberto |
| `volume_impacto` | number | custom field auto-descoberto |
| `subtasks_pendentes` | array | derivado por E2 (subtasks abertas anexadas a parent) |
| `date_created`, `date_updated` | YYYY-MM-DD | metadados |
| `url` | string | link direto pra task |

**Mapeamento legacy CSV → JSON ClickUp** (para o template/relatorio que ainda usa nomes antigos):

| CSV (descontinuado) | JSON ClickUp |
|---|---|
| `titulo` | `name` |
| `responsavel` | `responsavel_externo` |
| `data_cadastro` | `date_created` |
| `data_limite` | `due_date` |
| `volume` | `volume_impacto` |
| `receita` | `receita_impacto` |
| `parent_id` | sempre null (subtasks excluidas em E2) |
| `percentual` | nao existe — usar `status` mais granular do ClickUp |
| `comentarios` | nao mais inline; consultar `url` da task se necessario |

**Output Fase 1:** Lista de tasks ja filtrada (mesma da Fase 1.5 de E2), enriquecida com flag `indicador_no_card`.

### Fase 2 — Separar por Status e Calcular Aging

Separar acoes pelo campo `status` (valores possiveis variam pela configuracao do ClickUp da lista — exemplos: `to do`, `in progress`, `complete`, `closed`, `cancelled`). Mapeie para 3 buckets:

| Bucket interno | Statuses ClickUp tipicos |
|---|---|
| `ativa` (pendente + em_andamento) | `to do`, `in progress`, `open`, `pending` |
| `concluida` | `complete`, `closed`, `done` |
| `cancelada` | `cancelled`, `archived` |

> Quando o status retornado nao casar com nenhum dos buckets, default para `ativa` e logar warning. Status case-insensitive.

Para acoes **ativas**:

1. **Aging** = `data_referencia` - `date_created` (dias corridos)
2. **Dias restantes** = `due_date` - `data_referencia` (dias corridos). Se `due_date` for `null`, classificar como `Sem prazo` (warning ao usuario).
3. **Classificar urgencia:**

| Classificacao | Criterio (dias_restantes) | Acao |
|---------------|---------------------------|------|
| **Em dia** | > 0 | Monitoramento normal |
| **Atrasada** | 0 a -7 | Alerta ao responsavel_externo |
| **Critica** | < -7 | Requer escalonamento imediato |
| **Sem prazo** | `due_date == null` | Warning — exigir owner+prazo no proximo ritual |

**Tratamento de campos monetarios:** `volume_impacto` e `receita_impacto` ja vem como `number` (ou `null`) do JSON — nao precisa parsear strings com R$. Tratar `null` como 0 nas agregacoes.

**Output Fase 2:** Acoes ativas classificadas com aging e dias_restantes calculados.

### Fase 2.5 — Flag `criada_em_ritual_anterior` (v6.1.0+)

> **NOVO 2026-05-06**: marca tasks criadas no intervalo `[data_ultimo_ritual, data_ritual_atual)`
> para o slide Status PAs do m7-ritual-gestao (tweak C3) destacar contramedidas
> recem-decididas vs herdadas de ciclos anteriores.

1. **Ler datas do CICLO.md atual**:
   - `data_ritual_atual` = `data_referencia` do ciclo corrente
   - `data_ultimo_ritual` = `data_referencia` do CICLO.md mais recente da MESMA vertical (ciclo anterior)
2. **Localizar ciclo anterior**: `Glob('02-Controle/**/{Vertical-cap}[-{subnivel}]/????-??/????-??-??/CICLO.md')` ordenado por data desc, pegar o segundo (o primeiro e o atual). O `**/` tolera o nivel level-first (`N{N}/`); inclui o month-wrapper; ignorar `_Historico/`.
3. **Para cada task** em `data[]` (todos os status, nao apenas ativas):
   - `criada_em_ritual_anterior = data_ultimo_ritual <= date_created < data_ritual_atual`
   - Anexar campo `criada_em_ritual_anterior: bool` ao record da task
4. **Edge cases**:
   - Se nao ha ciclo anterior (1o ciclo da vertical): `criada_em_ritual_anterior: false` em todas
   - Se `date_created > data_ritual_atual` (rara — task criada apos o snapshot): `criada_em_ritual_anterior: false` + warning
   - Se `is_first_ritual_of_month: true` no CICLO.md (Fase 0 do run-weekly): janela ainda funciona normal — pegar ultimo ciclo independente do mes

**Output Fase 2.5:** Tasks com flag `criada_em_ritual_anterior` populada para todos os records.

### Fase 3 — Avaliar Eficacia das Concluidas

Para acoes com status `concluida` no periodo do ciclo:

1. **Identificar** o `indicador_impactado` de cada acao (campo direto do JSON ClickUp)
2. **Cruzar** com dados consolidados de E2 (`dados/dados-consolidados-{vertical}.json` na pasta do ciclo)
3. **Verificar** se o indicador voltou a meta apos a conclusao da acao (`date_updated` como proxy de quando foi marcada concluida)
4. **Classificar eficacia:**

| Eficacia | Criterio |
|----------|----------|
| **Eficaz** | Indicador voltou a >= 95% da meta |
| **Parcial** | Indicador melhorou mas permanece < 95% da meta |
| **Sem efeito** | Indicador nao melhorou ou piorou |

Se dados de E2 nao estao disponiveis para o indicador OU o `indicador_impactado` esta `null` no ClickUp, registrar como "Dados insuficientes" (e sinalizar como warning ao usuario — preencher o campo no ClickUp para o proximo ciclo).

**Output Fase 3:** Tabela de eficacia das acoes concluidas.

### Fase 4 — Identificar Hierarquia e Impacto

1. **Hierarquia**: ja resolvida em E2 — todas as tasks no JSON sao parent (`parent: null` garantido). Subtasks pendentes aparecem como notas em `subtasks_pendentes[]` da parent
2. **Impacto**: Ordenar acoes por `volume_impacto` + `receita_impacto` projetados (decrescente, tratando `null` como 0)
3. **Top 5**: Selecionar as 5 acoes com maior impacto financeiro (independente de status)

**Output Fase 4:** Ranking de impacto + lista de subtasks pendentes anotadas.

### Fase 5 — Calcular Metricas Agregadas

| Metrica | Formula |
|---------|---------|
| Total de acoes ativas | Count(bucket == 'ativa') |
| Taxa de conclusao (30d) | Count(concluidas com `date_updated` nos ultimos 30d) / Count(total criadas nos ultimos 30d via `date_created`) × 100 |
| Acoes criticas | Count(dias_restantes < -7) |
| Acoes sem prazo | Count(due_date == null E bucket == 'ativa') |
| % de acoes criticas | Acoes criticas / Total ativas × 100 |
| Aging medio | Avg(aging) das ativas |
| Volume em risco | Sum(volume_impacto) das acoes criticas |
| Receita em risco | Sum(receita_impacto) das acoes criticas |
| Acoes criadas no ritual anterior | Count(criada_em_ritual_anterior == true) — tweak C3 |
| Acoes criadas no ritual anterior por owner | Count(criada_em_ritual_anterior == true) GROUP BY responsavel_externo |

### Fase 6 — Gerar Output

Gerar `analise/action-report.md` (na pasta do ciclo) seguindo o [template](templates/action-report.tmpl.md).

O relatorio deve ser **auto-contido** — legivel sem necessidade de consultar o CSV original.

### Fase 6.5 — Emissão canonical: 4 categorias `acoes.*` (sidecar JSON) — NOVO em v6.2.0 (S2a B4.18, 2026-05-18)

**Motivo:** O `action-report.md` (Fase 6) e narrativo. Downstream (E6 `consolidating-wbr` → build_deck Slide 4 PA Status + Slide 5 PA Vencendo + donut) precisa de **arrays JSON estruturados** com as 4 categorias canonicas. Hoje build_deck reconstroi as categorias dinamicamente a partir de clickup-tasks-{vertical}.json (fallback); v6.2.0 formaliza a emissao em sidecar para E6 consumir.

**Output:** `{cycle_folder}/analise/e4-acoes-{vertical}.json`

**Schema:**

```json
{
  "_schema": "e4-acoes v1.0",
  "_generated_at": "2026-05-19T08:30:00",
  "vertical": "consorcios",
  "data_referencia": "2026-05-19",
  "escopo_fonte": "escopo_ritual_passado + ad_hoc_pos_ritual (memory reference_g2_2_action_scope_filter)",
  "filtros_aplicados": ["status != cancelada", "status != archived"],
  "acoes": {
    "criticas":            [<task_item>, ...],
    "atrasadas":           [<task_item>, ...],
    "em_dia_priorizadas":  [<task_item>, ...],
    "concluidas_eficazes": [<task_item>, ...]
  },
  "metricas_agregadas": {
    "total_escopo": <int>,
    "total_criticas": <int>,
    "total_atrasadas": <int>,
    "total_em_dia": <int>,
    "total_concluidas_periodo": <int>,
    "volume_em_risco": <float>,
    "receita_em_risco": <float>,
    "taxa_conclusao_30d_pct": <float>,
    "aging_medio_dias": <float>
  }
}
```

**Schema de `<task_item>`** (uniforme nas 4 categorias):

```json
{
  "id": "86agymn2w",
  "name": "Reuniao intervencao Nisa",
  "status": "in progress",
  "priority": "high",
  "due_date": "2026-05-15",
  "date_created": "2026-04-22",
  "date_updated": "2026-04-29",
  "date_closed": null,
  "responsavel_externo": "Bruno Chiaramonti",
  "indicador_impactado": "receita_seguros_mensal",
  "origem": "ritual_2026-04-22",
  "receita_impacto": 11000,
  "volume_impacto": null,
  "subtasks_pendentes": ["86agymmyx (Briefing Nisa)"],
  "criada_em_ritual_anterior": true,
  "aging_dias": 27,
  "dias_restantes": -4,
  "eficacia": null,
  "url": "https://app.clickup.com/t/86agymn2w"
}
```

**Mapeamento categoria → criterio:**

| Categoria | Criterio | Inclui |
|---|---|---|
| `criticas` | bucket == ativa AND dias_restantes < -7 | tasks abertas atrasadas em mais de 7 dias |
| `atrasadas` | bucket == ativa AND -7 <= dias_restantes <= 0 | tasks abertas atrasadas ate 7 dias |
| `em_dia_priorizadas` | bucket == ativa AND dias_restantes > 0 | tasks abertas no prazo |
| `concluidas_eficazes` | bucket == concluida AND date_closed in [data_ultimo_ritual, data_ritual_atual] | tasks que foram concluidas no periodo do ciclo |

**Regras de emissão:**

1. **Origem do escopo**: `escopo_ritual_passado + ad_hoc_pos_ritual` (do JSON `clickup-tasks-{vertical}-scoped.json` gerado em E2 Fase 1.5.7). NAO emitir tasks orfas antigas (fora do escopo do ritual passado e nao ad_hoc).
2. **Excluir** status `cancelada` e `archived` (não entram em nenhuma categoria)
3. **`em_dia_priorizadas`**: nome legacy `em_dia_proximas` permitido por compatibilidade (build_deck.py aplica alias). NOVO sempre emitir `em_dia_priorizadas`.
4. **`concluidas_eficazes`**: NAO confundir com "todas concluidas". Filtrar por `date_closed in periodo do ciclo`. Tasks concluidas em ciclos anteriores (mesmo que ainda no escopo) NAO entram aqui.
5. **`date_closed`**: vem do JSON ClickUp (v6.4.2 do collecting-data adicionou esse campo). Para tasks `concluida` SEM `date_closed` (legacy), usar `date_updated` como fallback.
6. **`eficacia`**: campo populado APENAS para `concluidas_eficazes` (eficaz/parcial/sem_efeito/dados_insuficientes — calculado em Fase 3). Demais categorias: `null`.
7. **`aging_dias` e `dias_restantes`**: calculados em Fase 2.
8. **`criada_em_ritual_anterior`**: vindo de Fase 2.5.

**Consumo downstream:**

- E6 (`consolidating-wbr`) Fase 4.5.e le este sidecar e injeta em `acoes.{categoria}` no canonical WBR
- build_deck.py Slide 4 (donut + barras owner) + Slide 5 (PA Vencendo) consome do canonical (fallback graceful S1 mantido para retrocompatibilidade)

**Coerencia com E3:** se `indicador_impactado` de uma critica/atrasada coincide com um indicador Vermelho do `e3-causa-raiz-{vertical}.json`, a task entra como **evidencia** da causa-raiz (cross-link). Documentar esse cross-link na narrativa MD (Fase 6) — JSON apenas captura os ids.

**Validacao opcional contra JSON Schema (S2a B6.25):**

Apos emitir o sidecar, agente PODE validar contra `m7-operations/_schema/v1.2/e4-acoes.schema.json`:

```bash
python3 -c "
import json
from jsonschema import validate, ValidationError
try:
    schema = json.load(open('m7-operations/_schema/v1.2/e4-acoes.schema.json'))
    data = json.load(open('{cycle_folder}/analise/e4-acoes-{vertical}.json'))
    validate(data, schema)
    print('OK')
except ValidationError as e:
    print(f'SCHEMA VIOLATION: {e.message}')
    raise SystemExit(1)
"
```

Se schema violation, NAO commitar e investigar.

## Exit Criteria

- [ ] Relatorio de Acompanhamento de Acoes gerado em `analise/action-report.md` (na pasta do ciclo)
- [ ] Metricas agregadas calculadas (taxa conclusao, aging medio, % criticas, volume/receita em risco, sem prazo)
- [ ] Todas as acoes ativas classificadas (Em dia / Atrasada / Critica / Sem prazo)
- [ ] Eficacia avaliada para acoes concluidas no periodo (quando dados de E2 disponiveis E `indicador_impactado` preenchido no ClickUp)
- [ ] Subtasks pendentes anotadas como notas dentro das parents (campo `subtasks_pendentes[]`)
- [ ] Relatorio usa `responsavel_externo` (nao `assignees`) como dono da decisao
- [ ] **Flag `criada_em_ritual_anterior` populada** em todas as tasks (Fase 2.5, v6.1.0+) com janela `[data_ultimo_ritual, data_ritual_atual)`
- [ ] **Sidecar JSON `analise/e4-acoes-{vertical}.json` emitido** (Fase 6.5 — NOVO v6.2.0 S2a B4.18) — 4 categorias canonicas (criticas/atrasadas/em_dia_priorizadas/concluidas_eficazes) com `<task_item>` uniforme, fonte = escopo_ritual_passado + ad_hoc_pos_ritual, excluindo cancelada/archived

## Anti-Patterns

- NUNCA sugira contramedidas ou novas acoes — isso e responsabilidade de E6 (consolidating-wbr)
- NUNCA ignore acoes com `volume_impacto`/`receita_impacto` `null` — tratar como 0 nas agregacoes, nao excluir
- NUNCA leia `plano-de-acao.csv` local — descontinuado em 2026-04-30. SoT e o JSON `clickup-tasks-{vertical}.json` gerado em E2 Fase 1.5
- NUNCA chame a API ClickUp (MCP ou HTTP) diretamente desta skill — a coleta e responsabilidade de E2 Fase 1.5. Esta skill e read-only sobre o JSON ja coletado
- NUNCA gere relatorio sem calcular aging — mesmo que todas as acoes estejam em dia
- NUNCA confunda `responsavel_externo` (stakeholder) com `assignees[]` (executor) — relatorios mostram Responsavel Externo. Assignees so vai como contexto secundario
- NUNCA inclua subtasks como linha independente — elas estao em `subtasks_pendentes[]` da parent (filtro aplicado em E2)
