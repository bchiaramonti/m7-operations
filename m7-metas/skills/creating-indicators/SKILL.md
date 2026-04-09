---
name: creating-indicators
description: >-
  Cria, valida, promove e edita indicadores na Biblioteca de Indicadores M7 conforme
  ESP-PERF-001. Suporta 3 tipos de fonte (sql, mcp, hybrid) com entrevista guiada,
  descoberta de dados via MCP, e validacao contra _schema.yaml v2.0.

  Use when the user asks to create a new indicator, add a KPI, build a metric,
  validate an existing indicator, promote indicator status, edit an indicator,
  or mentions indicador, KPI, PPI, biblioteca de indicadores, metrica, _schema.yaml.
  Also use when the user provides a business question that needs a new indicator to answer.

  <example>
  Context: User wants to create a new performance indicator
  user: "Quero criar um indicador de captacao liquida mensal"
  assistant: Inicia entrevista guiada coletando source_type, dominio, granularidade, unit, e constroi o YAML
  </example>

  <example>
  Context: User wants to validate existing indicators
  user: "Valida todos os indicadores da biblioteca"
  assistant: Le _schema.yaml e cada indicador, verifica campos obrigatorios e regras condicionais, gera relatorio
  </example>

  <example>
  Context: User wants to promote an indicator
  user: "Promove captacao_liquida_mensal para validated"
  assistant: Verifica transicao valida, executa validacao completa como pre-requisito, atualiza status e updated_at
  </example>

  <example>
  Context: User wants to edit an existing indicator
  user: "Atualiza o benchmark do captacao_liquida_mensal para 2026"
  assistant: Le o YAML, mostra o analysis_guide atual, aplica a alteracao e atualiza updated_at
  </example>
user-invocable: true
---

# Skill: creating-indicators

> "Indicador sem documentacao e query perdida. Indicador sem quality check e numero perigoso."

Gerencia a Biblioteca de Indicadores M7 — cria, valida, edita e promove indicadores YAML conforme ESP-PERF-001.

## Pre-requisitos

1. **Biblioteca de Indicadores** acessivel — localizar via:
   ```
   Glob('**/Biblioteca-de-Indicadores/_schema.yaml')
   ```
   O diretorio pai do `_schema.yaml` e a raiz da Biblioteca.

2. **_schema.yaml** presente (contrato de validacao)

3. **Para criacao/edicao**: MCPs ClickHouse e/ou Bitrix24 acessiveis (para descoberta de dados e teste de queries)

## Resolucao de caminhos

A Biblioteca de Indicadores esta em `01-Metas/Biblioteca-de-Indicadores/` dentro do projeto `padronizacao-rituais-gestao-m7`. Indicadores ficam em subdiretorios por vertical (ex: `Investimentos/`). Sempre localizar via Glob — nunca assumir CWD.

---

## 4 Modos de Operacao

### Modo 1 — Criar Novo Indicador

Entrevista guiada em 5 fases para gerar um indicador YAML completo.

**Fase 1: Coleta de contexto**

Perguntar ao usuario:
1. Nome do indicador e o que mede
2. Qual decisao de negocio suporta
3. Fonte dos dados: ClickHouse (`sql`), Bitrix24 (`mcp`), ou ambos (`hybrid`)
4. Granularidade desejada (assessor/mes, equipe/mes, etc.)
5. Unidade de medida: `BRL`, `pct`, `count`, `ratio`, `days`, `score`
6. Dominio: `comercial`, `receita`, `clientes`, `operacional`, `risco`, `pessoas`
7. Se hybrid: qual dimensao do ClickHouse sera usada para segmentacao

Gerar automaticamente:
- `id`: snake_case derivado do nome (confirmar com usuario)
- `owner`: extrair do contexto ou perguntar
- `tags`: sugerir baseado no nome e dominio (min 3, lowercase, sem acentos)

**Fase 2: Descoberta de dados**

Conforme o `source_type`, explorar fontes via MCP:

| source_type | Acoes |
|-------------|-------|
| `sql` | `clickhouse_list_tables` → `clickhouse_describe_table` → `clickhouse_get_table_sample` → identificar colunas |
| `mcp` | Listar tools Bitrix24 → testar com params de exemplo → documentar output_fields |
| `hybrid` | Descoberta de ambas as fontes + identificar campo de ponte (bridge) + validar cobertura (>90%) |

**Fase 3: Construcao da query/extraction**

Usar o template correspondente como ponto de partida:
- SQL: [indicator-sql.tmpl.yaml](templates/indicator-sql.tmpl.yaml)
- MCP: [indicator-mcp.tmpl.yaml](templates/indicator-mcp.tmpl.yaml)
- Hybrid: [indicator-hybrid.tmpl.yaml](templates/indicator-hybrid.tmpl.yaml)

Para regras detalhadas de construcao de queries e extraction, ver:
- [Convencoes de Query SQL](references/query-conventions.md)
- [Guia de Elaboracao](references/guia-elaboracao.md)

**Fase 4: Documentacao interpretativa**

Preencher:
- `analysis_guide`: benchmarks, faixas (>=100% superacao, 80-99% normal, <80% atencao, <60% alarme), sazonalidade, caveats, aditividade
- `quality_checks`: min 5 checks (aditividade + integridade + especificos do tipo)
- `explanatory_context`: related_indicators (>=2), segmentation_dimensions (>=3), external_factors (>=1), investigation_playbook (>=5 steps)

Para guidelines detalhados, ver [ESP-PERF-001 Resumo](references/esp-perf-001-resumo.md).

**Fase 5: Validacao e salvamento**

1. Validar contra _schema.yaml v2.0 (executar Modo 2)
2. Salvar em `Biblioteca-de-Indicadores/{Vertical}/{id}.yaml` com `status: draft`
3. Regenerar `_index.yaml`

---

### Modo 2 — Validar Indicador(es)

Verifica indicador(es) contra o contrato _schema.yaml v2.0.

**Escopo**: Indicador especifico (por id) ou todos da biblioteca.

**Regras de validacao completas**: ver [Schema v2.0](references/schema-v2.md).

**Resumo das validacoes**:

1. **Regras gerais (todos os source_types)**:
   - `id` snake_case e corresponde ao nome do arquivo
   - `domain` corresponde ao subdiretorio
   - `source_type` valido: sql, mcp, hybrid
   - `unit` valido: BRL, pct, count, ratio, days, score
   - `granularity`, `owner`, `updated_at` (YYYY-MM-DD) preenchidos
   - `description` explica o que mede, como calcula, qual decisao suporta
   - `parameters` referenciados existem na lista parameters
   - `dependencies` listam todas as tabelas e tools usados
   - `tags` em lowercase, sem acentos

2. **Regras condicionais por source_type**:
   - **sql**: `query` presente e nao vazio; `extraction` ausente; usa @param_name; retorna colunas-padrao
   - **mcp**: `extraction` com steps/transform/output_schema; `query` ausente; steps com source: mcp
   - **hybrid**: `extraction` + `bridge` presentes; `query` ausente; steps mcp + sql; dependencies com prefixo

3. **Regras por status**:
   - **validated**: quality_checks + analysis_guide presentes; explanatory_context com related_indicators e segmentation_dimensions
   - **promoted_to_gold**: source_layer = gold; todos os requisitos de validated

**Output**: Relatorio de validacao usando template [validation-report.tmpl.md](templates/validation-report.tmpl.md).

Categorias de issues:
- **CRITICO**: campo obrigatorio ausente, source_type inconsistente, query invalida
- **ATENCAO**: analysis_guide incompleto, quality_checks insuficientes, explanatory_context parcial
- **OK**: campo conforme

**Opcionalmente** (se MCPs acessiveis): executar query SQL ou tools MCP para teste real.

---

### Modo 3 — Promover Status

Transicoes validas:

| De | Para | Pre-requisitos |
|----|------|----------------|
| `draft` | `validated` | quality_checks + analysis_guide presentes; explanatory_context com related_indicators e segmentation_dimensions |
| `validated` | `promoted_to_gold` | source_layer = gold; view criada e homologada pela TI |

**Fluxo**:
1. Executar validacao completa (Modo 2) como pre-requisito
2. Se validacao sem issues CRITICO:
   - Atualizar `status`
   - Atualizar `updated_at`
   - Copiar versao anterior para `_Historico/` com sufixo `_ate-{YYYY-MM-DD}`
3. Regenerar `_index.yaml`

---

### Modo 4 — Editar Indicador Existente

1. Ler arquivo YAML e apresentar ao usuario
2. Aplicar edicoes solicitadas
3. Atualizar `updated_at` para data atual
4. Executar validacao (Modo 2)
5. Salvar no mesmo caminho
6. Se `tags`, `status`, `name` ou `domain` mudaram, regenerar `_index.yaml`

**Regras**:
- Se `domain` mudou, mover arquivo para novo subdiretorio
- Se `id` mudou, renomear arquivo e atualizar `related_indicators` em outros indicadores

---

## Regeneracao do _index.yaml

Executar apos qualquer criacao, edicao ou promocao:

1. Listar todos os `.yaml` em subdiretorios (exceto `_schema.yaml`, `_index.yaml`)
2. Para cada arquivo: ler `id`, `name`, `domain`, `tags`, `status`, `unit`, `source_layer`
3. Calcular `summary` (total, por dominio, por status)
4. Ordenar por dominio, depois por nome
5. Escrever `_index.yaml` atualizado

---

## Indicadores de Referencia

Consultar indicadores existentes como exemplos de qualidade:
- SQL: `captacao_liquida_mensal.yaml`, `abertura_contas_300k.yaml` (11 indicadores validated)
- Hybrid: usar template [indicator-hybrid.tmpl.yaml](templates/indicator-hybrid.tmpl.yaml)

---

## References

Para regras detalhadas e construcao, consultar (progressive disclosure):
- [ESP-PERF-001 Resumo](references/esp-perf-001-resumo.md) — campos, regras, ciclo de maturidade
- [Guia de Elaboracao](references/guia-elaboracao.md) — padroes dos 3 tipos de fonte
- [Schema v2.0](references/schema-v2.md) — contrato de validacao com regras condicionais
- [Convencoes de Query SQL](references/query-conventions.md) — parametrizacao, GROUPING SETS, colunas-padrao

---

## Anti-Patterns

- NUNCA criar indicador sem verificar unicidade do id no _index.yaml
- NUNCA promover para validated sem quality_checks, analysis_guide e explanatory_context
- NUNCA editar sem atualizar updated_at
- NUNCA deixar _index.yaml dessincronizado apos operacao
- NUNCA criar indicador "guarda-chuva" com multiplas metricas — um YAML por indicador
- NUNCA salvar query que nao foi pelo menos parseable (verificar sintaxe SQL)
- NUNCA criar subdiretorio que nao corresponde a um domain valido
- NUNCA usar `query` para source_type mcp — usar `extraction`
- NUNCA omitir `bridge` para source_type hybrid
