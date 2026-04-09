# Guia de Elaboracao de Indicadores M7

> Referencia para elaborar indicadores com o Claude.
> Cobre os 3 tipos de fonte: SQL (ClickHouse), MCP (Bitrix24) e Hibrido (ambos).

---

## Visao Geral

A Biblioteca de Indicadores M7 padroniza **o que medir**, **como extrair** e **como interpretar** cada KPI do escritorio. Cada indicador e um arquivo YAML auto-contido que serve como contrato entre humanos e agentes AI.

### Tipos de Fonte

| `source_type` | Quando usar | `query` | `extraction` |
|---------------|-------------|---------|--------------|
| `sql` | Dados 100% no ClickHouse | Obrigatorio | Nao existe |
| `mcp` | Dados 100% via API (Bitrix24) | `null` | Obrigatorio |
| `hybrid` | Dados de API + dimensoes do ClickHouse | `null` | Obrigatorio (steps SQL + MCP) |

---

## Estrutura Completa de um Indicador

```yaml
# ── IDENTIDADE E METADADOS (obrigatorio — todos os tipos) ──

id: nome_snake_case              # deve corresponder ao nome do arquivo
name: Nome Legivel em Portugues
status: draft | validated | promoted_to_gold
updated_at: YYYY-MM-DD
owner: nome.sobrenome
domain: comercial | receita | clientes | operacional | risco | pessoas
tags: [tag1, tag2, tag3]         # lowercase, sem acentos

description: >
  O que mede, como calcula, qual decisao suporta.
  Legivel por humanos e agentes AI.

unit: BRL | pct | count | ratio | days | score
granularity: "assessor / mes"    # dimensao / periodo
source_layer: bronze | silver | gold | api
refresh_frequency: realtime | daily | weekly | monthly

# ── FONTE DE DADOS — escolher conforme source_type ──

source_type: sql | mcp | hybrid  # define qual bloco preencher
```

---

## Bloco `query` (source_type: sql)

Usado quando todos os dados estao no ClickHouse. E a abordagem dos 11 indicadores atuais.

```yaml
dependencies:
  - m7Bronze.tabela_1
  - m7Bronze.tabela_2

parameters:
  - name: data_inicio
    type: date
    default: "2025-01-01"
    description: Data minima do filtro

query: |
  SELECT ...
  FROM tabela_1
  WHERE mes >= @data_inicio
  ORDER BY mes, nivel
```

**Regras:**
- Query deve ser **auto-suficiente** e **executavel** sem modificacao
- Parametros via `@param_name`
- Listar todas as tabelas em `dependencies`
- Funcoes ClickHouse: `toStartOfMonth`, `GROUPING SETS`, `sumIf`, etc.
- Colunas-padrao esperadas: mes, nivel, escritorio, equipe, squad, assessor, codigo_xp, meta, realizado, pct_atingimento

---

## Bloco `extraction` (source_type: mcp)

Usado quando todos os dados vem de API (ex: Bitrix24 via MCP).

```yaml
source_type: mcp

dependencies:
  - mcp: bitrix24_get_deals_from_date_range
  - mcp: bitrix24_get_all_users
  - mcp: bitrix24_get_deal_stages

parameters:
  - name: data_inicio
    type: date
    default: "2025-01-01"
    description: Data minima do filtro
  - name: data_fim
    type: date
    default: "today"
    description: Data maxima do filtro

extraction:
  description: >
    Breve descricao do que a extracao faz e por que usa MCP.

  steps:
    - id: 1
      source: mcp
      tool: bitrix24_get_deals_from_date_range
      params:
        date_from: "@data_inicio"
        date_to: "@data_fim"
      filters:
        CAMPO: "valor"           # filtros de negocio pos-extracao
      output_name: raw_deals
      output_fields: [ID, OPPORTUNITY, ASSIGNED_BY_ID, STAGE_ID, DATE_CREATE]
      note: "Paginacao automatica pelo MCP"

    - id: 2
      source: mcp
      tool: bitrix24_get_all_users
      params: {}
      output_name: users
      output_fields: [ID, NAME, LAST_NAME, EMAIL]
      note: "Cache possivel — muda raramente"

  transform: |
    # Pseudocodigo ou Python da transformacao
    deals = raw_deals.merge(users, left_on='ASSIGNED_BY_ID', right_on='ID')
    result = deals.groupby(['assessor', 'mes']).agg(...)

  output_schema:
    columns: [mes, nivel, assessor, metrica_1, metrica_2]
    types: [date, string, string, float64, int]
    sort: [mes, nivel, assessor]
```

**Regras:**
- Cada step tem um `id` sequencial, `source: mcp`, e o nome exato do `tool`
- `output_fields` documenta os campos esperados (equivalente ao SELECT)
- `output_name` nomeia a variavel intermediaria para uso no `transform`
- `filters` sao filtros de negocio aplicados apos a extracao (nao sao params da API)
- `transform` contem a logica de agregacao/calculo em Python/pseudocodigo
- `output_schema` e o contrato de saida (o que o consumidor recebe)

---

## Bloco `extraction` Hibrido (source_type: hybrid)

Usado quando a fonte primaria e API mas a **segmentacao depende de dimensoes do ClickHouse** (ex: dim_colaboradores, dim_equipe).

```yaml
source_type: hybrid

dependencies:
  - mcp: bitrix24_get_deals_from_date_range
  - mcp: bitrix24_get_all_users
  - sql: m7Bronze.vw_investimento_tb_colaborador
  - sql: m7Bronze.vw_investimento_tb_equipe

extraction:
  description: >
    Dados extraidos do Bitrix24, enriquecidos com hierarquia
    comercial do ClickHouse para segmentacao por equipe/squad/assessor.

  steps:
    # ── Steps MCP (fonte primaria) ──
    - id: 1
      source: mcp
      tool: bitrix24_get_deals_from_date_range
      params:
        date_from: "@data_inicio"
        date_to: "@data_fim"
      output_name: raw_deals
      output_fields: [ID, OPPORTUNITY, ASSIGNED_BY_ID, CATEGORY_ID, STAGE_ID, DATE_CREATE]

    - id: 2
      source: mcp
      tool: bitrix24_get_all_users
      params: {}
      output_name: bitrix_users
      output_fields: [ID, NAME, LAST_NAME, EMAIL]

    # ── Steps SQL (dimensoes para segmentacao) ──
    - id: 3
      source: sql
      query: |
        SELECT id_colaborador, nome, codigo_xp_a00000, id_equipe
        FROM vw_investimento_tb_colaborador
        WHERE CAST(id_equipe AS Int32) IN (348, 349, 350, 351, 352, 353)
      output_name: dim_colaboradores
      output_fields: [id_colaborador, nome, codigo_xp_a00000, id_equipe]

    - id: 4
      source: sql
      query: |
        SELECT id_equipe, nome_equipe
        FROM vw_investimento_tb_equipe
        WHERE id_equipe IN (348, 349, 350, 351, 352, 353)
      output_name: dim_equipe
      output_fields: [id_equipe, nome_equipe]

  # ── Ponte entre os dois mundos ──
  bridge: |
    A ponte entre Bitrix e ClickHouse e:
      bitrix_users.EMAIL -> dim_colaboradores.email_corporativo
      OU bitrix_users.ID -> tabela de-para bitrix_id -> codigo_xp

    Uma vez resolvido o colaborador, a hierarquia vem do ClickHouse:
      colaborador.id_equipe -> dim_equipe.nome_equipe
      id_equipe -> B2B/B2C (349,351=B2C | 350,352=B2B)

    Cobertura esperada: >90%. Registros sem match ficam em "Outros".

  transform: |
    # 1. Ponte: Bitrix user -> colaborador CH
    users_map = bitrix_users.merge(dim_colaboradores,
        left_on='EMAIL', right_on='email_corporativo')

    # 2. Enriquecer deals com hierarquia
    deals = raw_deals.merge(users_map, left_on='ASSIGNED_BY_ID', right_on='BITRIX_ID')
    deals = deals.merge(dim_equipe, on='id_equipe')

    # 3. Classificar e calcular
    deals['mes'] = deals['DATE_CREATE'].dt.to_period('M')
    result = deals.groupby([...]).agg(...)

  output_schema:
    columns: [mes, nivel, equipe, squad, assessor, metrica]
    types: [date, string, string, string, string, float64]
    sort: [mes, nivel, equipe, squad]
```

**Regras adicionais para hybrid:**
- Steps com `source: mcp` e `source: sql` podem ser intercalados
- O campo `bridge` e **obrigatorio** — documenta como os dois mundos se conectam
- `bridge` deve declarar: campo de juncao, direcao do match, cobertura esperada
- `dependencies` usa prefixo `mcp:` ou `sql:` para distinguir a origem

---

## Secoes Comuns (todos os tipos)

### analysis_guide

```yaml
analysis_guide: >
  Texto interpretativo: o que e o indicador, benchmarks, faixas,
  alertas conhecidos, sazonalidade. Usado pelo executive-communicator.
```

Conteudo obrigatorio (para validated):
1. **Benchmarks reais** com ano de referencia: "Benchmark M7 (2026): mediana R$ 1.2M/mes"
2. **Faixas de atingimento**: >=100% superacao, 80-99% normal, <80% atencao, <60% alarme
3. **Sazonalidade conhecida**: "Janeiro fraco por [razao]. Maio forte por [razao]"
4. **Caveats**: regras de aditividade, excecoes, limitacoes

### quality_checks

```yaml
quality_checks:
  - "realizado N1 = SUM(realizado N4) para o mesmo mes"
  - "pct_atingimento NULL quando meta = 0"
  - "sem valores negativos em [campo X]"      # se aplicavel
  # Para MCP/hybrid, adicionar:
  - "cobertura do bridge >= 90%"              # hybrid only
  - "output_fields presentes na resposta do MCP"
  - "paginacao retornou todos os registros (comparar count)"
```

### explanatory_context

Ver [esp-perf-001-resumo.md](esp-perf-001-resumo.md#3-explanatory-context) para estrutura completa.

---

## Referencia Rapida — Mapeamento Bitrix <-> ClickHouse

Tabelas de dimensao do ClickHouse frequentemente usadas para enriquecer dados do Bitrix:

| Dimensao | Tabela ClickHouse | Campo de juncao tipico |
|----------|-------------------|------------------------|
| Colaborador/Assessor | `vw_investimento_tb_colaborador` | `email`, `codigo_xp_a00000`, `id_colaborador` |
| Equipe | `vw_investimento_tb_equipe` | `id_equipe` |
| Equipe -> Segmento | Derivado | 349,351=B2C / 350,352=B2B / 348,353=Outros |
| Meta Escritorio | `vw_investimento_tb_meta_escritorio` | `mes` |
| Meta Equipe | `vw_investimento_tb_meta_equipe` | `id_equipe`, `mes` |
| Meta Assessor | `airbyte_internal.m7_raw__stream_invest_tb_meta_assessor` | `ID_COLABORADOR`, `MES` (JSON) |

### Ponte Bitrix -> ClickHouse

```
Bitrix: ASSIGNED_BY_ID -> bitrix24_get_all_users -> {ID, NAME, LAST_NAME, EMAIL}
                                                          |
ClickHouse: EMAIL ou NOME -> vw_investimento_tb_colaborador -> {id_colaborador, id_equipe, codigo_xp}
                                                                      |
                                                          vw_investimento_tb_equipe -> {nome_equipe}
                                                                      |
                                                          id_equipe -> B2B/B2C/Outros
```

> **Atencao:** A cobertura dessa ponte deve ser verificada em todo indicador hybrid.
> Incluir um quality_check: `"cobertura do bridge >= 90%"`.
> Registros sem match devem cair em segmento "Outros" com meta=0.
