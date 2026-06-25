# Schema v2.1 — Contrato da Biblioteca de Indicadores M7

> Referencia legivel do _schema.yaml v2.x com regras condicionais por source_type.

Este documento traduz o _schema.yaml em regras acionaveis para a skill `creating-indicators`.

**Mudancas v2.1 (2026-05-12):**
- 4 campos visuais opcionais (`display_name`, `display_suffix`, `direction`, `output_schema.por_canal`) para suportar rituais multi-vertical (PJ2 N2) e indicators com semaforo invertido (menor melhor).
- 6 regras de validacao novas (34-39) — todas ATENCAO ou condicionais, nao quebram retrocompat com v2.0.
- Ver secao 3.1 e 3.2.

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
| `display_name` | string | — | Label visual para slides quando diferente de `name` (default: `name`) |
| `display_suffix` | string | — | Sufixo concatenado ao label em render (ex: "CRM" para indicators Bitrix) |
| `direction` | enum | — | `maior_melhor` (default) ou `menor_melhor` — direcao do semaforo |
| `output_schema.por_canal` | object | — | Declara decomposicao por canal emitida pelo indicator (PJ2 e similares) |

---

### 3.1 Campos visuais (display_name, display_suffix, direction)

Introduzidos no schema v2.1 para suportar rituais multi-vertical (PJ2 N2) e indicators com semaforo invertido (menor melhor). Aplicam a qualquer `source_type`.

**`display_name`** — string, opcional. Label usado por builders/decks. Quando ausente, builder usa `name`. Util quando o `name` canonico nao serve para slides (ex: nome tecnico longo).

```yaml
name: "Oportunidades Sem Atividade Planejada"
display_name: "Sem Atividade ou Atrasada"
```

**`display_suffix`** — string, opcional. Sufixo concatenado ao label final pelo builder. DRY para indicators Bitrix que precisam de marcador (#6 do contrato `pj2-slide-requirements.md`). Builder concatena como `f"{name|display_name} {display_suffix}"`.

```yaml
name: "Oportunidades Criadas"
display_suffix: "CRM"
# Builder renderiza: "Oportunidades Criadas CRM"
```

**`direction`** — enum, opcional. `maior_melhor` (default) ou `menor_melhor`. Inverte a logica de `cor_from_pct` no builder: para `menor_melhor`, pct >= 100% significa estouro (vermelho), pct <= 100% significa atingimento (verde). Obrigatorio para indicators de unit `days` ou `pct` quando reducao e o objetivo (ex: tempo de ciclo, % estagnacao).

```yaml
name: "Tempo de Ciclo Funil Consorcios"
unit: days
direction: menor_melhor
```

---

### 3.2 Output schema por_canal

Para indicators que emitem decomposicao por canal (PJ2: investimentos/credito/outros_m7; N3: por especialista). Pode estar:
- **Top-level** (`output_schema.por_canal`) para source_type `sql` ou `hybrid` (paralelo a `output_contract.columns`).
- **Dentro de `extraction.output_schema`** para source_type `mcp` (paralelo a `columns/types/sort`).

**Schema:**

```yaml
output_schema:
  por_canal:
    investimentos:
      qty: int            # quantidade total no canal
      vol: float          # volume agregado (R$)
      qty_won: int        # opcional: quantidade convertida (WON)
      pct_ativas: float   # opcional: % estagnadas sobre ativas (para indicators de estagnacao)
    credito:
      qty: int
      vol: float
    outros_m7:
      qty: int
      vol: float
```

**Convencoes:**
- `canal_id` segue `de-para-canal.yaml` da vertical (PJ2 = investimentos/credito/outros_m7; N3 = id do especialista).
- Campos sao OPCIONAIS dentro de cada canal — declare apenas os que o indicator efetivamente emite.
- Mesma CTE/fonte de classificacao de canal entre indicators correlacionados (ativas vs estagnadas) — caso contrario `pct_ativas` fica inconsistente.

**Exemplos por tipo de indicator:**

| Indicator | Campos por_canal declarados |
|---|---|
| `quantidade_consorcio_mensal_pj2` | qty, vol |
| `oportunidades_ativas_funil_pj2` | qty, vol |
| `oportunidades_estagnadas_funil_pj2` | qty, pct_ativas |
| `ticket_medio_premio_seg_pj2` (derived) | herda do divisor |

---

## 4. Validation Rules

### Regras gerais (todos os source_types)

1. `id` e snake_case e corresponde ao nome do arquivo
2. `domain` e um dominio valido; a vertical do indicador corresponde ao subdiretorio `{Vertical}/` (no layout por nivel: `N{org_level}/{Vertical}/`)
3. `source_type` e um dos valores validos: sql, mcp, hybrid
4. `unit` e um dos valores validos: BRL, pct, count, ratio, days, score
5. `granularity` esta preenchido
6. `owner` esta preenchido
7. `updated_at` esta no formato YYYY-MM-DD
8. `description` explica o que mede, como calcula e qual decisao suporta (>= 20 chars)
9. `parameters` referenciados na query/steps existem na lista parameters
10. `dependencies` listam todas as tabelas e tools usados
11. `tags` em lowercase, sem acentos
11b. (D5/Frente 7 — ATENCAO/WARN) `org_level` presente e ∈ {N1..N5}; quando a Biblioteca ja esta organizada por nivel, o path confere com `N{org_level}/{vertical_folder}/{id}.yaml`. Ausente durante a transicao (layout flat) = WARN; apos a migracao por nivel (Tempo 2) = CRITICO. Unicidade de `id` e composta `(org_level, id)` — o mesmo id pode existir em niveis distintos.

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

### Regras para campos visuais (v2.1+)

34. Se `display_name` presente, deve ser string nao vazia
35. Se `display_suffix` presente, deve ser string com tamanho <= 16 chars (limite visual de slides)
36. Se `direction` presente, deve ser exatamente `maior_melhor` ou `menor_melhor`
37. Quando `unit == "days"` e direction estiver ausente, emitir ATENCAO sugerindo `direction: menor_melhor`
38. Quando `output_schema.por_canal` presente:
    - Cada `canal_id` deve estar em lowercase snake_case (ex: `investimentos`, `outros_m7`)
    - Cada canal declara ao menos 1 campo (`qty` ou `vol`)
    - Se `pct_ativas` declarado em um canal, indicator e classificado como "estagnacao-like" e deve ter dependency em um indicator companheiro de `ativas` (related_indicators)
39. Indicators com `output_schema.por_canal` devem listar canais consistentes com `de-para-canal.yaml` da vertical referenciada nas tags (validacao ATENCAO se canal_id nao reconhecido)

---

## 5. Backwards Compatibility

Indicadores criados antes do schema v2.0 (sem `source_type`):
- Assumir `source_type: sql` implicitamente
- Campo `query` ja e obrigatorio no v1.0
- Bloco `extraction` nao existe — compativel
- Na proxima edicao, adicionar `source_type: sql` explicitamente

Indicadores da biblioteca atual (11 validated) sao todos `source_type: sql`.

### v2.0 → v2.1 (campos visuais opcionais)

Indicadores v2.0 sem `display_name`, `display_suffix`, `direction` ou `output_schema.por_canal` continuam validos. Builders fazem fallback:
- `display_name` ausente → usa `name`
- `display_suffix` ausente → render sem sufixo
- `direction` ausente → assume `maior_melhor`
- `output_schema.por_canal` ausente → builder usa decomposicao por especialista (N3) ou agregado simples

Regra 37 emite ATENCAO (nao CRITICO) — nao quebra validacao de indicators legados.
