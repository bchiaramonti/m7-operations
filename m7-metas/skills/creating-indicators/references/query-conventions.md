# Convencoes de Query SQL — ClickHouse

> Referencia: ESP-PERF-001 v1.0, Secao 5
> Aplica-se a indicadores com `source_type: sql` e steps SQL em `source_type: hybrid`.

---

## Indice

1. [Parametrizacao](#1-parametrizacao)
2. [Funcoes ClickHouse](#2-funcoes-clickhouse)
3. [CAST e Tipos](#3-cast-e-tipos)
4. [COALESCE e LEFT JOINs](#4-coalesce-e-left-joins)
5. [Estrutura Multi-Nivel](#5-estrutura-multi-nivel)
6. [Colunas-Padrao](#6-colunas-padrao)
7. [Tabelas de Dimensao](#7-tabelas-de-dimensao)

---

## 1. Parametrizacao

Usar `@param_name` para parametros dinamicos. Todo @param na query deve ter entrada em `parameters`.

```yaml
parameters:
  - name: data_inicio
    type: date
    default: "2025-01-01"
    description: Data minima do filtro de meses

query: |
  SELECT ...
  WHERE mes >= @data_inicio
```

**Defaults uteis:**
- `"2025-01-01"` — inicio do ano fiscal
- `"first_day_current_month"` — mes corrente
- `"today"` — data atual
- `"last_day_previous_month"` — fechamento mensal

---

## 2. Funcoes ClickHouse

Funcoes mais usadas nos indicadores M7:

| Funcao | Uso | Exemplo |
|--------|-----|---------|
| `toStartOfMonth(date)` | Agrupar por mes | `toStartOfMonth(cap.data) AS mes` |
| `toDate(string)` | Converter string para date | `toDate(me.mes) AS mes` |
| `sumIf(col, cond)` | Soma condicional | `sumIf(valor, tipo = 'APP')` |
| `countIf(cond)` | Contagem condicional | `countIf(status = 'ativo')` |
| `round(val, n)` | Arredondamento | `round(real/meta, 4)` |
| `GROUPING(col)` | Detectar nivel de agrupamento | `GROUPING(equipe) = 1` |
| `COALESCE(a, b)` | Valor default para NULL | `COALESCE(r.realizado, 0)` |
| `CAST(col AS type)` | Conversao explicita | `CAST(me.captacao AS Float64)` |

---

## 3. CAST e Tipos

**Regra**: Sempre usar CAST explicito entre tipos diferentes.

```sql
-- Correto
CAST(c.id_equipe AS Int32) = e.id_equipe
CAST(ma.captacao AS Float64) AS meta

-- Incorreto (cast implicito — pode falhar)
c.id_equipe = e.id_equipe  -- se um e String e outro Int
```

**Tipos mais usados:**
- `Int32` — IDs, contagens
- `Float64` — Valores monetarios, percentuais
- `String` — Nomes, codigos
- `Date` — Datas (sem hora)

---

## 4. COALESCE e LEFT JOINs

**Regra**: Sempre usar COALESCE para colunas vindas de LEFT JOINs.

```sql
LEFT JOIN (
    SELECT id_colaborador, SUM(valor) AS realizado
    FROM vw_investimento_tb_captacao
    GROUP BY id_colaborador
) r ON ma.id_colaborador = r.id_colaborador

-- COALESCE para evitar NULLs no resultado
CAST(COALESCE(r.realizado, 0) AS Float64) AS realizado
```

Sem COALESCE, assessores sem captacao teriam `realizado = NULL` em vez de `0`.

---

## 5. Estrutura Multi-Nivel

A maioria dos indicadores M7 retorna dados em 4 niveis hierarquicos. A estrutura padrao usa GROUPING SETS para N1-N3 e UNION ALL para N4.

### Template generico

```sql
SELECT * FROM (

-- N1/N2/N3 via GROUPING SETS
SELECT
    mes,
    CASE
        WHEN GROUPING(equipe) = 1 AND GROUPING(squad) = 1 THEN 'N1-Escritorio'
        WHEN GROUPING(squad) = 1 THEN 'N2-Equipe'
        ELSE 'N3-Squad'
    END AS nivel,
    'M7 Investimentos' AS escritorio,
    equipe,
    squad,
    NULL AS assessor,
    NULL AS codigo_xp,
    SUM(meta_val) AS meta,
    SUM(real_val) AS realizado,
    CASE WHEN SUM(meta_val) > 0
         THEN round(SUM(real_val) / SUM(meta_val), 4)
         ELSE NULL END AS pct_atingimento
FROM (
    -- Subquery que prepara base_n3 com meta e realizado por squad/equipe
    SELECT
        toDate(me.mes) AS mes,
        CASE
            WHEN me.id_equipe IN (350, 352) THEN 'B2B'
            WHEN me.id_equipe IN (349, 351) THEN 'B2C'
            ELSE 'Outros'
        END AS equipe,
        CASE
            WHEN me.id_equipe IN (348, 353) THEN 'Outros'
            ELSE eq.nome_equipe
        END AS squad,
        CAST(me.{campo_meta} AS Float64) AS meta_val,
        CAST(COALESCE(r.realizado, 0) AS Float64) AS real_val
    FROM m7Bronze.vw_investimento_tb_meta_equipe me
    JOIN m7Bronze.vw_investimento_tb_equipe eq ON me.id_equipe = eq.id_equipe
    LEFT JOIN (
        -- Realizado agregado por equipe e mes
        ...
    ) r ON me.id_equipe = r.id_equipe AND toDate(me.mes) = r.mes
    WHERE me.id_equipe IN (348, 349, 350, 351, 352, 353)
) base_n3
GROUP BY GROUPING SETS (
    (mes, equipe, squad),   -- N3-Squad
    (mes, equipe),          -- N2-Equipe
    (mes)                   -- N1-Escritorio
)

UNION ALL

-- N4 - Assessor com meta
SELECT
    toDate(ma.mes) AS mes,
    'N4-Assessor' AS nivel,
    'M7 Investimentos' AS escritorio,
    -- equipe, squad, assessor, codigo_xp via JOINs
    ...
FROM m7Bronze.vw_investimento_tb_meta_assessor ma
JOIN m7Bronze.vw_investimento_tb_colaborador c ON ...
JOIN m7Bronze.vw_investimento_tb_equipe e ON ...
LEFT JOIN (...) r ON ...

UNION ALL

-- N4 - Assessores com realizado mas sem meta (meta=0)
SELECT
    -- Similar ao bloco acima, mas com anti-join na tabela de metas
    ...
    CAST(0 AS Float64) AS meta,
    ...
    NULL AS pct_atingimento
FROM ...
WHERE (id_colaborador, mes) NOT IN (
    SELECT id_colaborador, mes FROM meta_assessor
)

) AS cubo
WHERE mes >= @data_inicio
ORDER BY mes, nivel, equipe, squad, assessor
```

### Niveis hierarquicos

| Nivel | Label | Agregacao |
|-------|-------|-----------|
| N1 | N1-Escritorio | Todo o escritorio (GROUPING equipe=1, squad=1) |
| N2 | N2-Equipe | Por segmento: B2B, B2C, Outros |
| N3 | N3-Squad | Por time: Alta Renda, Mesa, Private, Corporate |
| N4 | N4-Assessor | Individual (UNION ALL separado) |

### Regra de aditividade

- Meta: N1 = Sum(N2) = Sum(N3) via GROUPING SETS
- Meta N4: independente (Sum(N4) pode != N3)
- Realizado: aditivo em todos os niveis

---

## 6. Colunas-Padrao

Todo indicador `source_type: sql` deve retornar estas colunas:

| Coluna | Tipo | Nullable | Descricao |
|--------|------|----------|-----------|
| `mes` | Date | Nao | toDate() ou toStartOfMonth() |
| `nivel` | String | Nao | N1-Escritorio, N2-Equipe, N3-Squad, N4-Assessor |
| `escritorio` | String | Nao | Sempre "M7 Investimentos" |
| `equipe` | String | Sim (N1) | B2B, B2C, Outros |
| `squad` | String | Sim (N1,N2) | Nome da equipe (de vw_investimento_tb_equipe) |
| `assessor` | String | Sim (N1-N3) | Nome do assessor (de vw_investimento_tb_colaborador) |
| `codigo_xp` | String | Sim (N1-N3) | Codigo XP (codigo_xp_a00000) |
| `meta` | Float64 | Nao | Valor da meta (0 para assessores sem meta) |
| `realizado` | Float64 | Nao | Valor realizado (0 via COALESCE) |
| `pct_atingimento` | Float64 | Sim | round(realizado/meta, 4); NULL quando meta=0 |

### Ordenacao padrao

```sql
ORDER BY mes, nivel, equipe, squad, assessor
```

---

## 7. Tabelas de Dimensao

Views do ClickHouse frequentemente usadas:

| View | Conteudo | Campos-chave |
|------|----------|--------------|
| `vw_investimento_tb_colaborador` | Cadastro de assessores | id_colaborador, nome, codigo_xp_a00000, id_equipe, email |
| `vw_investimento_tb_equipe` | Cadastro de equipes | id_equipe, nome_equipe |
| `vw_investimento_tb_meta_equipe` | Metas por equipe/mes | id_equipe, mes, {campo_meta} |
| `vw_investimento_tb_meta_assessor` | Metas por assessor/mes | id_colaborador, mes, {campo_meta} |
| `vw_investimento_tb_meta_escritorio` | Metas escritorio/mes | mes, {campo_meta} |
| `vw_investimento_tb_captacao` | Movimentacoes de captacao | id_colaborador, data, valor |

**Equipes M7 (hardcoded):**

| id_equipe | Segmento | Squad |
|-----------|----------|-------|
| 348 | Outros | Outros |
| 349 | B2C | Mesa |
| 350 | B2B | Alta Renda |
| 351 | B2C | Private |
| 352 | B2B | Corporate |
| 353 | Outros | Outros |

Filtro padrao: `WHERE id_equipe IN (348, 349, 350, 351, 352, 353)`
