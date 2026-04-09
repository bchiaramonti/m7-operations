# ESP-PERF-001 — Resumo da Especificacao Tecnica

> Referencia: ESP-PERF-001 v1.0 — Especificacao Tecnica da Biblioteca de Indicadores M7

Este resumo extrai as regras de validacao, campos e ciclo de maturidade da ESP-PERF-001 para uso pela skill `creating-indicators`.

---

## Indice

1. [Campos Obrigatorios](#1-campos-obrigatorios)
2. [Campos Opcionais](#2-campos-opcionais)
3. [Explanatory Context](#3-explanatory-context)
4. [Ciclo de Maturidade](#4-ciclo-de-maturidade)
5. [Regras de Negocio Tecnicas](#5-regras-de-negocio-tecnicas)
6. [Validacao](#6-validacao)

---

## 1. Campos Obrigatorios

Devem estar presentes em todo indicador, independente do status.

| Campo | Tipo | Formato/Valores | Descricao |
|-------|------|-----------------|-----------|
| `id` | string | snake_case, sem acentos | Identificador unico, corresponde ao nome do arquivo |
| `name` | string | Portugues, autoexplicativo | Nome legivel do indicador |
| `description` | text | 2-4 frases | O que mede, como calcula, qual decisao suporta |
| `domain` | enum | comercial, receita, clientes, operacional, risco, pessoas | Determina subdiretorio |
| `source_type` | enum | sql, mcp, hybrid | Define qual bloco de dados preencher |
| `unit` | enum | BRL, pct, count, ratio, days, score | Unidade de medida |
| `granularity` | string | "dimensao / periodo" | Ex: assessor / mes |
| `source_layer` | enum | bronze, silver, gold, api | Camada de dados |
| `owner` | string | nome.sobrenome | Responsavel pela manutencao |
| `updated_at` | date | YYYY-MM-DD | Ultima atualizacao do arquivo |

### Campos condicionais por source_type

| Campo | sql | mcp | hybrid |
|-------|-----|-----|--------|
| `query` | Obrigatorio | Ausente/null | Ausente/null |
| `extraction` | Ausente | Obrigatorio | Obrigatorio |
| `extraction.bridge` | N/A | N/A | Obrigatorio |

---

## 2. Campos Opcionais

| Campo | Tipo | required_for | Descricao |
|-------|------|--------------|-----------|
| `parameters` | list | — | Parametros dinamicos (@param_name) |
| `analysis_guide` | text | validated | Benchmarks, faixas, sazonalidade, caveats |
| `quality_checks` | list[string] | validated | Validacoes verificaveis |
| `dependencies` | list[string] | — | Tabelas e tools usados |
| `tags` | list[string] | — | Tags para busca (min 3, lowercase, sem acentos) |
| `status` | enum | — | draft, validated, promoted_to_gold (default: draft) |
| `refresh_frequency` | enum | — | realtime, daily, weekly, monthly |
| `explanatory_context` | object | validated (parcial) | Rede de inteligencia investigativa |

### Formato de parameters

```yaml
parameters:
  - name: data_inicio       # snake_case
    type: date               # date, string, integer, float
    default: "2025-01-01"    # valor default para execucao autonoma
    description: Data minima do filtro
```

### Formato de dependencies

```yaml
# Para sql:
dependencies:
  - m7Bronze.vw_investimento_tb_captacao
  - m7Bronze.vw_investimento_tb_colaborador

# Para mcp:
dependencies:
  - mcp: bitrix24_get_deals_from_date_range
  - mcp: bitrix24_get_all_users

# Para hybrid (prefixos obrigatorios):
dependencies:
  - mcp: bitrix24_get_deals_from_date_range
  - sql: m7Bronze.vw_investimento_tb_colaborador
```

---

## 3. Explanatory Context

Transforma indicadores isolados em rede de inteligencia investigativa.

### 3.1 related_indicators (obrigatorio para validated)

```yaml
related_indicators:
  - indicator_id: outro_indicador    # ID existente na biblioteca
    relationship: leading | lagging | correlated | inverse | component
    explanation: >
      Mecanismo da relacao em linguagem natural (nao apenas "sao correlacionados").
```

- Minimo 2 indicadores relacionados
- `indicator_id` deve referenciar indicador existente
- `explanation` deve descrever o mecanismo causal

**Tipos de relacao:**

| Tipo | Significado | Exemplo |
|------|-------------|---------|
| `leading` | Se move antes | Tarefas CRM precedem captacao |
| `lagging` | Afetado depois | AuM e consequencia da captacao |
| `correlated` | Movem-se juntos | ROA e captacao tendem a caminhar juntos |
| `inverse` | Direcoes opostas | Churn sobe, captacao cai |
| `component` | Faz parte do calculo | NNM e componente da captacao |

### 3.2 segmentation_dimensions (obrigatorio para validated)

```yaml
segmentation_dimensions:
  - dimension: Equipe
    source_column: equipe          # coluna real no banco
    typical_segments: [B2B, B2C, Outros]
    diagnostic_value: high | medium | low
    rationale: >
      Por que esse corte importa para diagnostico.
```

- Minimo 3 dimensoes (tipicamente: Equipe, Squad, Assessor)
- `diagnostic_value`: high = primeiro corte, medium = segundo nivel, low = investigacao profunda
- `source_column` deve ser a coluna real (permite query automatica)

### 3.3 external_factors

```yaml
external_factors:
  - factor: Taxa Selic
    impact_direction: >
      Selic alta favorece captacao em renda fixa...
    data_source: "web_search: 'Selic taxa hoje Banco Central COPOM'"
```

- Minimo 1 fator externo
- `data_source` deve ser acionavel (web_search, URL, relatorio)

### 3.4 investigation_playbook

```yaml
investigation_playbook:
  - step: 1
    action: "Comparar N1 MoM e YoY"
    expected_insight: "Tendencia geral do escritorio"
    tools:
      - "query: indicador com filtro nivel='N1'"
```

- Minimo 5 steps, do mais obvio ao mais profundo
- Cada step usa insights dos anteriores (sequencia importa)
- `tools` lista recursos concretos (query, indicator_id, web_search, extraction)

---

## 4. Ciclo de Maturidade

### Transicoes validas

```
draft ──→ validated ──→ promoted_to_gold
```

Transicoes inversas nao sao permitidas via skill (apenas edicao manual).

### Requisitos por status

| Requisito | draft | validated | promoted_to_gold |
|-----------|-------|-----------|------------------|
| Campos obrigatorios | Sim | Sim | Sim |
| Query/extraction funciona | Sim | Sim | Sim |
| quality_checks presentes | — | Sim | Sim |
| analysis_guide com benchmarks | — | Sim | Sim |
| explanatory_context (related + segmentation) | — | Sim | Sim |
| source_layer = gold | — | — | Sim |
| View homologada pela TI | — | — | Sim |

### Ao promover

1. Executar validacao completa sem issues CRITICO
2. Atualizar `status` e `updated_at`
3. Copiar versao anterior para `_Historico/{id}_ate-{YYYY-MM-DD}.yaml`

---

## 5. Regras de Negocio Tecnicas

### Arredondamento
- `pct_atingimento`: round(valor, 4) — 4 casas decimais
- Valores monetarios (BRL): sem arredondamento na query, formatar na apresentacao

### Nulos
- `pct_atingimento = NULL` quando `meta = 0` (divisao por zero)
- Usar `COALESCE` para LEFT JOINs (default 0 para realizado sem match)

### Aditividade entre niveis
- Meta: N1 = Sum(N2) = Sum(N3) via GROUPING SETS
- Meta N4 (assessor): independente — Sum(N4) pode diferir de N3
- Realizado: aditivo em todos os niveis (N1 = Sum(N2) = Sum(N3) = Sum(N4))

### Equipes M7 (hardcoded)
- B2B: id_equipe IN (350, 352)
- B2C: id_equipe IN (349, 351)
- Outros: id_equipe IN (348, 353)
- Todas: IN (348, 349, 350, 351, 352, 353)

### Assessores sem meta
- Incluir com meta = 0, pct_atingimento = NULL
- Identificar via anti-join (NOT IN na tabela de metas)

---

## 6. Validacao

### Regras estruturais

1. `id` snake_case, sem acentos, corresponde ao nome do arquivo
2. `domain` corresponde ao subdiretorio
3. `source_type` valido: sql, mcp, hybrid
4. `unit` valido: BRL, pct, count, ratio, days, score
5. `updated_at` formato YYYY-MM-DD
6. `description` presente e informativa (>= 20 caracteres)
7. `parameters` referenciados na query/steps existem na lista
8. `dependencies` listam todas as tabelas e tools usados

### Regras condicionais

**sql:**
- `query` presente e nao vazio
- `extraction` ausente
- Query usa @param_name para parametros
- Query retorna colunas-padrao: mes, nivel, escritorio, equipe, squad, assessor, codigo_xp, meta, realizado, pct_atingimento

**mcp:**
- `extraction` presente com description, steps, transform, output_schema
- `query` ausente ou null
- Todos os steps tem source: mcp e tool preenchido
- output_fields documentados em cada step
- output_schema com columns, types e sort

**hybrid:**
- `extraction` presente
- `bridge` presente e documenta campo de juncao, direcao e cobertura
- `query` ausente ou null
- Steps podem ter source: mcp ou source: sql
- Dependencies usam prefixo mcp: ou sql:

### Quality checks

Para todas as queries sql:
- Aditividade: N1 = Sum(N2), N2 = Sum(N3), N3 = Sum(N4)
- Integridade: meta >= 0, assessor com equipe NOT NULL
- Negocio: pct_atingimento NULL quando meta = 0

Para mcp:
- output_fields presentes na resposta
- Paginacao retornou todos os registros (comparar count)

Para hybrid:
- Cobertura do bridge >= 90%
- Registros sem match em segmento "Outros" com meta = 0

### Troubleshooting

| Problema | Causa provavel | Solucao |
|----------|----------------|---------|
| Sum(N4) != N3 | Metas assessor independentes | Documentar no analysis_guide como caveat |
| query retorna 0 linhas | Parametro data_inicio muito recente | Verificar default e range de dados |
| pct_atingimento > 2.0 | Possivel erro de unidade | Verificar se meta e realizado estao na mesma unidade |
| Assessor sem equipe | Cadastro incompleto | Incluir em "Outros" via COALESCE |
| Bridge coverage < 90% | Emails divergentes entre sistemas | Tentar match por nome ou codigo_xp |
