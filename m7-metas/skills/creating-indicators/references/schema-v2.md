# Schema v2.0 — Contrato da Biblioteca de Indicadores M7

> Referencia legivel do _schema.yaml v2.0 com regras condicionais por source_type.

Este documento traduz o _schema.yaml em regras acionaveis para a skill `creating-indicators`.

---

## Indice

1. [Required Fields](#1-required-fields)
2. [Conditional Fields](#2-conditional-fields)
3. [Optional Fields](#3-optional-fields)
4. [Validation Rules](#4-validation-rules)
5. [Backwards Compatibility](#5-backwards-compatibility)

---

## 1. Required Fields

Devem estar presentes em **todo** indicador, independente de status ou source_type.

| Campo | Tipo | Formato | Exemplo |
|-------|------|---------|---------|
| `id` | string | snake_case, sem acentos | `captacao_liquida_mensal` |
| `name` | string | Portugues legivel | `Captacao Liquida Mensal` |
| `description` | text | >= 20 chars, 2-4 frases | O que mede + como calcula + decisao |
| `domain` | enum | comercial, receita, clientes, operacional, risco, pessoas | `comercial` |
| `source_type` | enum | sql, mcp, hybrid | `sql` |
| `unit` | enum | BRL, pct, count, ratio, days, score | `BRL` |
| `granularity` | string | "dimensao / periodo" | `assessor / mes` |
| `source_layer` | enum | bronze, silver, gold, api | `bronze` |
| `owner` | string | nome.sobrenome | `bruno.chiaramonti` |
| `updated_at` | date | YYYY-MM-DD | `2026-03-16` |

---

## 2. Conditional Fields

Presenca depende do `source_type` declarado.

### source_type: sql

| Campo | Presenca | Descricao |
|-------|----------|-----------|
| `query` | **Obrigatorio** | Query SQL executavel com @param_name |
| `extraction` | **Ausente** | Nao pode existir |
| `dependencies` | Recomendado | Lista de tabelas: `schema.tabela` |
| `parameters` | Recomendado | Lista de @param usados na query |

**Colunas-padrao esperadas no resultado da query:**

| Coluna | Tipo | Nullable | Descricao |
|--------|------|----------|-----------|
| `mes` | Date | Nao | Periodo de referencia |
| `nivel` | String | Nao | N1-Escritorio, N2-Equipe, N3-Squad, N4-Assessor |
| `escritorio` | String | Nao | Sempre "M7 Investimentos" |
| `equipe` | String | Sim (N1) | B2B, B2C, Outros |
| `squad` | String | Sim (N1,N2) | Nome da equipe |
| `assessor` | String | Sim (N1-N3) | Nome do assessor |
| `codigo_xp` | String | Sim (N1-N3) | Codigo XP do assessor |
| `meta` | Float64 | Nao | Valor da meta |
| `realizado` | Float64 | Nao | Valor realizado |
| `pct_atingimento` | Float64 | Sim (quando meta=0) | round(realizado/meta, 4) |

### source_type: mcp

| Campo | Presenca | Descricao |
|-------|----------|-----------|
| `query` | **Ausente/null** | Nao pode existir |
| `extraction` | **Obrigatorio** | Bloco completo |
| `extraction.description` | Obrigatorio | O que a extracao faz |
| `extraction.steps` | Obrigatorio | Lista sequencial de steps |
| `extraction.transform` | Obrigatorio | Logica de transformacao |
| `extraction.output_schema` | Obrigatorio | Contrato de saida |
| `dependencies` | Recomendado | Com prefixo `mcp:` |

**Formato de cada step:**

```yaml
- id: 1                        # sequencial
  source: mcp                  # obrigatorio: mcp
  tool: bitrix24_get_deals_... # nome exato do tool MCP
  params:                      # parametros do tool
    date_from: "@data_inicio"
  filters:                     # filtros pos-extracao (opcional)
    CAMPO: "valor"
  output_name: raw_deals       # variavel para uso no transform
  output_fields: [ID, ...]     # campos esperados na resposta
  note: "..."                  # observacoes (opcional)
```

### source_type: hybrid

Herda todas as regras de `mcp`, mais:

| Campo | Presenca | Descricao |
|-------|----------|-----------|
| `extraction.bridge` | **Obrigatorio** | Documentacao da ponte entre mundos |
| Steps com `source: sql` | Permitido | Steps podem ser mcp ou sql |
| `dependencies` | Recomendado | Prefixos `mcp:` e `sql:` obrigatorios |

**Formato de step SQL (dentro de extraction.steps):**

```yaml
- id: 3
  source: sql                  # obrigatorio: sql
  query: |                     # query inline
    SELECT ... FROM ...
  output_name: dim_colaboradores
  output_fields: [col1, col2]
```

**Formato do bridge:**

```yaml
bridge: |
  Campo de juncao: bitrix_users.EMAIL -> dim_colaboradores.email
  Direcao: Bitrix -> ClickHouse (LEFT JOIN)
  Cobertura esperada: >90%
  Registros sem match: segmento "Outros" com meta=0
```

---

## 3. Optional Fields

| Campo | Tipo | required_for | Descricao |
|-------|------|--------------|-----------|
| `status` | enum | — | draft (default), validated, promoted_to_gold |
| `refresh_frequency` | enum | — | realtime, daily, weekly, monthly |
| `tags` | list[string] | — | Min 3, lowercase, sem acentos |
| `parameters` | list[object] | — | @param_name referenciados |
| `dependencies` | list[string] | — | Tabelas/tools usados |
| `analysis_guide` | text | validated | Benchmarks, faixas, sazonalidade |
| `quality_checks` | list[string] | validated | Validacoes verificaveis (min 5) |
| `explanatory_context` | object | validated (parcial) | Rede investigativa |

---

## 4. Validation Rules

### Regras gerais (todos os source_types)

1. `id` e snake_case e corresponde ao nome do arquivo
2. `domain` corresponde ao subdiretorio
3. `source_type` e um dos valores validos: sql, mcp, hybrid
4. `unit` e um dos valores validos: BRL, pct, count, ratio, days, score
5. `granularity` esta preenchido
6. `owner` esta preenchido
7. `updated_at` esta no formato YYYY-MM-DD
8. `description` explica o que mede, como calcula e qual decisao suporta (>= 20 chars)
9. `parameters` referenciados na query/steps existem na lista parameters
10. `dependencies` listam todas as tabelas e tools usados
11. `tags` em lowercase, sem acentos

### Regras condicionais — sql

12. Campo `query` presente e nao vazio
13. Bloco `extraction` ausente
14. Query usa @param_name para parametros
15. Query retorna colunas-padrao (ver tabela acima)

### Regras condicionais — mcp

16. Bloco `extraction` presente com description, steps, transform, output_schema
17. Campo `query` ausente ou null
18. Todos os steps tem source: mcp e tool preenchido
19. output_fields documentados em cada step
20. output_schema com columns, types e sort

### Regras condicionais — hybrid

21. Bloco `extraction` presente
22. Campo `bridge` presente e documenta campo de juncao, direcao e cobertura
23. Campo `query` ausente ou null
24. Steps podem ter source: mcp ou source: sql
25. Dependencies usam prefixo mcp: ou sql:

### Regras para status validated

26. `quality_checks` presentes (lista nao vazia, min 5)
27. `analysis_guide` preenchido com benchmarks
28. `explanatory_context.related_indicators` com ao menos 2 indicadores
29. `explanatory_context.segmentation_dimensions` com ao menos 3 dimensoes
30. Para mcp: quality_checks incluem validacao de output_fields e paginacao
31. Para hybrid: quality_checks incluem cobertura do bridge >= 90%

### Regras para status promoted_to_gold

32. `source_layer` = gold
33. Todos os requisitos de validated mantidos

---

## 5. Backwards Compatibility

Indicadores criados antes do schema v2.0 (sem `source_type`):
- Assumir `source_type: sql` implicitamente
- Campo `query` ja e obrigatorio no v1.0
- Bloco `extraction` nao existe — compativel
- Na proxima edicao, adicionar `source_type: sql` explicitamente

Indicadores da biblioteca atual (11 validated) sao todos `source_type: sql`.
