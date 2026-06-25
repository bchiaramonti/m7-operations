---
name: creating-indicators
description: >-
  Cria, valida, promove e edita indicadores na Biblioteca de Indicadores M7 conforme
  ESP-PERF-001. Suporta 3 tipos de fonte (sql, mcp, hybrid) com entrevista guiada,
  descoberta de dados via MCP, e validacao contra _schema.yaml v3.2.

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

A Biblioteca de Indicadores esta em `01-Metas/Biblioteca-de-Indicadores/`. Estrutura-alvo **por nivel** (D5/Frente 7): `Biblioteca-de-Indicadores/N{org_level}/{Vertical}/{id}.yaml` (ex: `N3/Consorcios/`, `N2/Produtos/`, `N1/M7/`). Cada nivel tem SEUS indicadores; o mesmo `id` pode existir em niveis diferentes (composicao/agregacao distintas). **Transicao:** enquanto a Biblioteca nao foi migrada (Tempo 2), o layout flat legado `{Vertical}/{id}.yaml` (sem `N{N}/`) continua valido — o `collect.py` resolve por nivel com fallback flat (Passo 4). Sempre localizar a raiz via Glob — nunca assumir CWD.

---

## Protocolo OBRIGATORIO de Data Lineage (v1.2.0)

Antes de gerar ou modificar QUALQUER YAML em Modos 1, 4 ou 5 (Criar / Editar query/source / Clone), a skill DEVE apresentar ao usuario um bloco de Data Lineage com 5 pontos e pedir aprovacao explicita. Sem aprovacao, a skill NAO escreve o arquivo.

**Os 5 pontos:**

1. **Fonte de dados** — tabela/pipeline/CSV/MCP exato. Exemplos: `m7Bronze.consorcio_contratos`; Bitrix pipeline 156 WON; `m7Prata.seguro_comissao_assessor_fuzzy`.
2. **Filtros** — clausulas WHERE / status / datas / UFs. Exemplos: `situacao=ATIVO`, `DATE_CREATE in M0`, `delta_dias >= 2`, `UF_CRM_1773922604648=7268`.
3. **Mapeamento campo → canal** — qual campo classifica deals nos canais da vertical (de-para-canal.yaml). Exemplos: `UF_CRM_1758122406` (MKT Cons); `UF_CRM_1745419691` (SDR Seg); `centro_custo` (CH consorcio).
4. **Logica de agregacao** — COUNT / SUM / MEDIAN / derivacao. Exemplos: `MEDIAN(DATE_WON - DATE_CREATE)`, `SUM(premio_liquido)`, `volume_seg / quantidade_seg`.
5. **Output schema** — campos que o indicator vai emitir, incluindo `output_schema.por_canal` quando aplicavel.

**Formato de apresentacao (recomendado):**

```
## Data Lineage — {indicator_id}

| Ponto | Valor |
|---|---|
| Fonte | m7Bronze.consorcio_contratos |
| Filtros | situacao=ATIVO AND data_competencia in M0 |
| Canal mapping | centro_custo via de-para-canal.yaml |
| Agregacao | COUNT(*) por canal |
| Output schema | por_canal: {investimentos: {qty}, credito: {qty}, outros_m7: {qty}} |

Confirma? (sim/ajustar/nao)
```

**Quando aplica:**
- Modo 1 (Criar): SEMPRE antes de Fase 3 (Construcao da query/extraction).
- Modo 4 (Editar): SOMENTE quando edicao tocar em `query`, `extraction`, `dependencies` ou `output_schema`. Edicao cosmetica (analysis_guide, tags) NAO precisa.
- Modo 5 (Clone): SEMPRE antes de salvar o clone.

**Why:** memory `feedback_indicator_data_lineage` (2026-05-12). Indicators `_pj2` tem multiplas fontes possiveis (CH vs Bitrix vs hibrido) e mapeamentos de canal nao-obvios — sem revisao previa, erros caem em validacao V.1-V.4 e custam re-trabalho.

---

## 5 Modos de Operacao

### Modo 1 — Criar Novo Indicador

Entrevista guiada em 5 fases para gerar um indicador YAML completo.

**Fase 1: Coleta de contexto**

Perguntar ao usuario:
1. Nome do indicador e o que mede
2. Qual decisao de negocio suporta
3. Fonte dos dados: ClickHouse (`sql`), Bitrix24/MCP (`mcp`), ambos (`hybrid`), OU **derivado** de outros indicadores existentes (`hybrid` + `aggregation_rule` — ver Fase 2 e Fase 2.5 variantes)
4. Granularidade desejada (assessor/mes, equipe/mes, etc.)
5. Unidade de medida: `BRL`, `pct`, `count`, `ratio`, `days`, `score`
6. Dominio: `comercial`, `receita`, `clientes`, `operacional`, `risco`, `pessoas`
6b. **org_level** — nivel ORGANIZACIONAL do indicador (`N1`..`N5`): a qual camada ele pertence e a pasta `N{org_level}/` onde sera gravado. `N1`=empresa/M7; `N2`=vertical/centro (ex: Produtos, Investimentos, Performance, Pessoas); `N3`=operacional (Consorcios, Seguros, Credito...). **DISTINTO** do `nivel` de LINHA do output (`N1-Escritorio`..`N5-Assessor`, que e a granularidade de DECOMPOSICAO dos resultados). Sugerir por heuristica do contexto (vertical/decisao) e confirmar com o usuario.
7. Se hybrid: qual dimensao do ClickHouse sera usada para segmentacao
8. **Se derivado** (3 marcou opcao derivado): quais 2 indicadores existentes compoem numerator e denominator? Qual a operacao (`ratio_from_components`)? Qual multiplier (100 para pct, 1 para ratio decimal)? Em quais niveis a regra aplica?

**Fase 1.5: Campos visuais (schema v2.1+)**

Perguntar quando aplicavel:
8. **display_name** — label customizado para slides. Pergunta SO se nome canonico (item 1) ficar tecnico/longo. Default: usa `name`.
9. **display_suffix** — sufixo concatenado ao label em render. Lista pre-definida (CRM, MTD, YTD, M0, M-1) + custom. Pergunta SO se indicator vem de Bitrix/CRM (sufixo "CRM" para distinguir de indicators de banco). Default: vazio.
10. **direction** — `maior_melhor` ou `menor_melhor`. Pergunta padrao `menor_melhor` quando unit ∈ {`days`} OU quando indicator mede "tempo de", "ciclo", "% estagnacao", "% atraso". Default: `maior_melhor`.
11. **output_schema.por_canal** — pergunta SO se domain == `comercial` E granularity inclui canal/vertical. Lista canais do `de-para-canal.yaml` da vertical:
    - PJ2: `investimentos`, `credito`, `outros_m7`
    - N3: por especialista (id_assessor)
    Para cada canal, perguntar quais campos emite (qty, vol, qty_won, pct_ativas). Default: ausente (indicator nao emite decomposicao por canal).

Gerar automaticamente:
- `id`: snake_case derivado do nome (confirmar com usuario)
- `owner`: extrair do contexto ou perguntar
- `tags`: sugerir baseado no nome e dominio (min 3, lowercase, sem acentos). Para indicators `_pj2`, incluir tag `pj2` + tag da vertical real (`consorcios`/`seguros`).

**Fase 2: Descoberta de dados**

Conforme o `source_type`, explorar fontes via MCP:

| source_type | Acoes |
|-------------|-------|
| `sql` | `clickhouse_list_tables` → `clickhouse_describe_table` → `clickhouse_get_table_sample` → identificar colunas |
| `mcp` | Listar tools Bitrix24 → testar com params de exemplo → documentar output_fields |
| `hybrid` | Descoberta de ambas as fontes + identificar campo de ponte (bridge) + validar cobertura (>90%) |
| **`hybrid` + `aggregation_rule`** (DERIVADO — v3.2) | **NAO** explora ClickHouse/Bitrix. Verifica que numerator e denominator existem no `_index.yaml`. Le `output_contract.columns` de ambos para confirmar que `numerator_field` e `denominator_field` declarados existem. Documenta que a derivacao acontece em E6 (consolidating-wbr), nao em runtime do script |

**Fase 2.5: Data Lineage — APROVACAO HUMANA OBRIGATORIA**

Antes de avancar para Fase 3 (escrever query/extraction), apresentar o bloco de Data Lineage com os 5 pontos (ver secao "Protocolo OBRIGATORIO de Data Lineage" no topo desta SKILL.md). Aguardar aprovacao explicita do usuario. Sem aprovacao, NAO escrever o YAML.

**Variante DERIVADO (hybrid + aggregation_rule, v3.2):** os 5 pontos sao reinterpretados:

| Ponto | Valor para derivado |
|---|---|
| Fonte | Indicadores `{numerator_id}` + `{denominator_id}` (rows do output canonico de cada um) |
| Filtros | Mesmos do indicador `numerator` e `denominator` (herdados); pode acrescentar filtro de nivel via `applied_at_levels` |
| Canal mapping | Herdado dos indicadores componentes (se eles emitem por canal, o derivado tambem) |
| Agregacao | `{aggregation_rule.type}`(ex: ratio_from_components) com `multiplier={X}` |
| Output schema | columns: [data_referencia, nivel, ..., {output_column}]; tipo `float64` para o derivado |

Apresentar essa tabela no formato Data Lineage e pedir aprovacao explicita antes de salvar o YAML.

**Fase 3: Construcao da query/extraction**

Usar o template correspondente como ponto de partida:
- SQL: [indicator-sql.tmpl.yaml](templates/indicator-sql.tmpl.yaml)
- MCP: [indicator-mcp.tmpl.yaml](templates/indicator-mcp.tmpl.yaml)
- Hybrid: [indicator-hybrid.tmpl.yaml](templates/indicator-hybrid.tmpl.yaml)

Para regras detalhadas de construcao de queries e extraction, ver:
- [Convencoes de Query SQL](references/query-conventions.md)
- [Guia de Elaboracao](references/guia-elaboracao.md)

**Importante:** quando indicator usa `source_type: mcp` ou `hybrid` e precisa de logica de execucao customizada (canal classification, filtros stagehistory complexos), referenciar helpers de execucao via `extraction.method`. Exemplos de helpers existentes:
- `m7-operations/_pj2-prep/scripts/_pj2_funil_extractor.py` — Bitrix client + canal classification para PJ2 (executor, NAO gerador de YAML — ver secao "Aposentado" abaixo)
- `m7-operations/_pj2-prep/scripts/compute_tempo_ciclo_estagnacao.py` — computa tempo de ciclo via stagehistory

Esses scripts sao **camada de execucao** que indicators MCP/hybrid podem invocar. NAO geram YAMLs — geracao de YAML e responsabilidade EXCLUSIVA desta skill (memory `feedback_pristine_cycles_skill_first`).

**Variante DERIVADO (hybrid + aggregation_rule, v3.2):** o YAML aponta para um HELPER CANONICO:
```yaml
source_type: hybrid
script:
  path: ../scripts/_derived_aggregation.py
  checksum: "stub_derived_indicator"
  tested_at: 2026-05-18
  test_status: stub
aggregation_rule:
  type: ratio_from_components
  numerator: <id_indicador_existente>
  numerator_field: <coluna do output_contract>
  denominator: <id_indicador_existente>
  denominator_field: <coluna do output_contract>
  multiplier: 100        # 100 para pct, 1 para ratio decimal
  applied_at_levels:
    - N1-Escritorio
    - N2-Especialista
    # ...
```

O helper `_derived_aggregation.py` (em `01-Metas/Biblioteca-de-Indicadores/scripts/`) emite output canonico com `rows_returned=0` e flag `_derived_via_aggregation_rule=true` para satisfazer o contrato collect.py. A logica real e aplicada em E6 (`m7-controle:consolidating-wbr`) que le `aggregation_rule`, busca numerator/denominator no `_index.yaml`, soma os rows dos componentes e popula o canonical WBR.

**Fase 4: Documentacao interpretativa**

Preencher:
- `analysis_guide`: benchmarks, faixas (>=100% superacao, 80-99% normal, <80% atencao, <60% alarme), sazonalidade, caveats, aditividade
- `quality_checks`: min 5 checks (aditividade + integridade + especificos do tipo)
- `explanatory_context`: related_indicators (>=2), segmentation_dimensions (>=3), external_factors (>=1), investigation_playbook (>=5 steps)

Para guidelines detalhados, ver [ESP-PERF-001 Resumo](references/esp-perf-001-resumo.md).

**Fase 5: Validacao e salvamento**

1. Validar contra _schema.yaml (executar Modo 2)
2. Gravar `org_level` e `vertical_folder` no YAML (metadados de nivel/pasta).
3. Salvar em `Biblioteca-de-Indicadores/N{org_level}/{Vertical}/{id}.yaml` com `status: draft`.
   - **Transicao:** se a pasta `N{org_level}/` ainda nao existe (Biblioteca nao migrada), salvar no layout flat `Biblioteca-de-Indicadores/{Vertical}/{id}.yaml` — mas gravar `org_level` no YAML mesmo assim (o `collect.py` faz lookup level-scoped com fallback flat — Passo 4).
4. Regenerar `_index.yaml`

---

### Modo 2 — Validar Indicador(es)

Verifica indicador(es) contra o contrato _schema.yaml v3.2.

**Escopo**: Indicador especifico (por id) ou todos da biblioteca.

**Regras de validacao completas**: ver [Schema v3.2](references/schema-v2.md).

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
3. **Se edicao toca em `query`/`extraction`/`dependencies`/`output_schema`:** disparar Protocolo de Data Lineage (5 pontos) ANTES de salvar
4. Atualizar `updated_at` para data atual
5. Executar validacao (Modo 2)
6. Salvar no mesmo caminho
7. Se `tags`, `status`, `name`, `domain` ou `org_level` mudaram, regenerar `_index.yaml`

**Regras**:
- Se `domain` mudou, mover arquivo para novo subdiretorio
- Se `org_level` mudou, mover arquivo para a pasta `N{org_level}/{Vertical}/` correspondente
- Se `id` mudou, renomear arquivo e atualizar `related_indicators` em outros indicadores

---

### Modo 5 — Clonar Indicador (variante)

Clona um indicator existente como variante (sufixo `_pj2`, `_n3`, etc.) preservando estrutura mas permitindo overrides de query/dependencies/canal mapping. Util para criar familia de indicators paralelos (ex: 13 indicators `_pj2` clonados dos `_n3` correspondentes — roadmap 2026-05-12).

**Pre-requisito:** indicator base deve existir no `_index.yaml` ou ser localizavel via Glob.

**Fluxo:**

1. **Selecao da base**
   - Listar indicators existentes filtrados por `domain` e/ou `tags` do contexto (se usuario nao especificou).
   - Usuario escolhe o `id` base (ex: `oportunidades_criadas_funil_con`).

2. **Definir variante**
   - Perguntar sufixo (`_pj2`, `_n3_subnivel_x`, etc.).
   - Gerar `id` derivado: `{base_id}{sufixo}` (ex: `oportunidades_criadas_funil_con_pj2`).
   - Forcar `status: draft` no clone (sempre — independente do status do base).

3. **Apresentar diff esperado**
   - Mostrar ao usuario quais campos serao MANTIDOS (description, tags, granularity, unit, source_type, source_layer, refresh_frequency, analysis_guide, quality_checks, explanatory_context, parameters).
   - Mostrar quais ele PODE sobrescrever:
     - `query` ou `extraction` (filtros adicionais, pipeline diferente, fonte trocada)
     - `dependencies` (tabelas/tools diferentes)
     - `output_schema.por_canal` (canais diferentes — PJ2 usa `investimentos/credito/outros_m7`, N3 usa especialistas)
     - `display_name`, `display_suffix`, `direction` (campos visuais v2.1)
     - `tags` (adicionar `pj2` ou outras)

4. **Disparar Protocolo de Data Lineage** (obrigatorio)
   - Mesmo que muitos campos sejam herdados, mudancas em fonte/filtro/canal exigem aprovacao explicita dos 5 pontos antes de salvar.

5. **Salvar**
   - Caminho: `Biblioteca-de-Indicadores/N{org_level}/{Vertical}/{id_clonado}.yaml` (ver Fase 5 do Modo 1 p/ o fallback flat de transicao). Clone ENTRE niveis (ex: N3→N2 com sufixo `_pj2`) muda o `org_level` — perguntar/derivar o nivel de destino e gravar `org_level` no YAML clonado.
   - Atualizar `updated_at` para data atual.
   - Regenerar `_index.yaml`.

**Exemplo end-to-end (variante PJ2):**

```
Usuario: "Clone oportunidades_criadas_funil_con como _pj2"
Skill:   "Base encontrada: oportunidades_criadas_funil_con (Cons N3, mcp, draft)."
         "ID derivado: oportunidades_criadas_funil_con_pj2"
         "Mantenho? (description, tags, source_type, unit, etc.)"
         "Quais overrides? (query/dependencies/output_schema/display_*)"
Usuario: "Override canal mapping: usar UF_CRM_1758122406 (MKT Cons) ao inves do default ASSIGNED_BY"
         "Override output_schema.por_canal: investimentos/credito/outros_m7 com qty e vol"
         "Adicionar tag: pj2"
Skill:   [Apresenta Data Lineage com 5 pontos atualizados]
Usuario: "Aprovado"
Skill:   [Cria YAML em Cons/oportunidades_criadas_funil_con_pj2.yaml status=draft]
```

**Anti-pattern:** NUNCA usar Modo 5 para fazer fork de logica mantendo o mesmo id — isso e edicao (Modo 4), nao clone.

---

## Regeneracao do _index.yaml

Executar apos qualquer criacao, edicao ou promocao:

1. Listar todos os `.yaml` em subdiretorios. Descer ATE 2 niveis no layout por nivel (`N{N}/{Vertical}/*.yaml`) e tambem cobrir o layout flat de transicao (`{Vertical}/*.yaml`). Excluir `_schema.yaml`, `_index.yaml`.
2. Para cada arquivo: ler `id`, `name`, `domain`, `org_level`, `vertical_folder`, `tags`, `status`, `unit`, `source_layer`. Quando `org_level`/`vertical_folder` ausentes no YAML, derivar do path (`N{N}/{Vertical}/`).
3. Calcular `summary` (total, por dominio, por status, por `org_level`)
4. Ordenar por `org_level`, depois `domain`, depois `name`
5. Escrever `_index.yaml` atualizado

---

## Indicadores de Referencia

Consultar indicadores existentes como exemplos de qualidade:
- SQL: `captacao_liquida_mensal.yaml`, `abertura_contas_300k.yaml` (11 indicadores validated)
- Hybrid: usar template [indicator-hybrid.tmpl.yaml](templates/indicator-hybrid.tmpl.yaml)

---

## Padrao especial — indicadores com modo Detalhe (1 linha por entidade)

Indicadores consumidos por componentes visuais que precisam de **listas** (ex: card "Sem atividade planejada" no ritual de gestao, mostrando `NOME | Estagio` por deal) podem produzir linhas de **detalhe** alem das agregacoes hierarquicas.

**Convencao:**
- Coluna `nivel` aceita `Detalhe` como valor especial alem de `N1-Escritorio` ... `N5-Assessor`. (Esta coluna `nivel` e a granularidade de DECOMPOSICAO do output — NAO confundir com o metadado `org_level` do indicador, que e a pasta `N{N}/` onde ele mora.)
- Linhas com `nivel='Detalhe'` representam **1 entidade individual por linha** (1 deal, 1 cliente, 1 ticket, etc.).
- Colunas extras especificas do detalhe (ex: `deal_id`, `nome_deal`, `dias_sem_atividade`, `estagio`) ficam preenchidas APENAS nas linhas de Detalhe; nas linhas de agregacao N1-N5 ficam `null`.
- O `output_contract.columns` lista TODAS as colunas (agregadas + detalhe); `null` onde nao aplicavel.

**Exemplos de referencia:**
- `oportunidades_sem_atividade_planejada_funil_seg.yaml` (Seguros)
- `oportunidades_sem_atividade_planejada_funil.yaml` (Consorcios)

**Quando usar:**
- Componente visual exige lista de itens individuais (top-N, drill-down).
- Decisao operacional requer identificar deals/clientes especificos, nao so agregados.

**Quando NAO usar:**
- Indicadores puramente agregados (KPIs, taxas, ratios) — manter N1-N5 e ignorar Detalhe.
- Quando o agregado N5-Assessor ja resolve a necessidade visual.

---

## References

Para regras detalhadas e construcao, consultar (progressive disclosure):
- [ESP-PERF-001 Resumo](references/esp-perf-001-resumo.md) — campos, regras, ciclo de maturidade
- [Guia de Elaboracao](references/guia-elaboracao.md) — padroes dos 3 tipos de fonte
- [Schema v3.2](references/schema-v2.md) — contrato de validacao com regras condicionais
- [Convencoes de Query SQL](references/query-conventions.md) — parametrizacao, GROUPING SETS, colunas-padrao

---

## Anti-Patterns

- NUNCA criar indicador sem verificar unicidade do id no _index.yaml. A unicidade e COMPOSTA `(org_level, id)`: o mesmo `id` PODE coexistir em niveis diferentes (ex: `captacao_liquida_mensal` em `N3/` e `N2/`, com composicao/agregacao distintas), mas NUNCA duas vezes no mesmo `org_level`
- NUNCA promover para validated sem quality_checks, analysis_guide e explanatory_context
- NUNCA editar sem atualizar updated_at
- NUNCA deixar _index.yaml dessincronizado apos operacao
- NUNCA criar indicador "guarda-chuva" com multiplas metricas — um YAML por indicador
- NUNCA salvar query que nao foi pelo menos parseable (verificar sintaxe SQL)
- NUNCA criar subdiretorio que nao corresponde a um domain valido
- NUNCA usar `query` para source_type mcp — usar `extraction`
- NUNCA omitir `bridge` para source_type hybrid
- NUNCA gerar/salvar YAML sem disparar Protocolo de Data Lineage em Modos 1/4/5 (quando aplicavel) — aprovacao explicita dos 5 pontos e bloqueante (memory `feedback_indicator_data_lineage`)
- NUNCA usar scripts ad-hoc (`_pj2_runner.py`, etc.) como geradores de YAML — geracao de YAML e responsabilidade exclusiva desta skill (memory `feedback_pristine_cycles_skill_first`). Scripts podem ser camada de execucao (referenciados por `extraction.method`), nao gerador.
- NUNCA omitir `direction` para indicators com `unit: days` — emitir ATENCAO sugerindo `menor_melhor` (regra 37 do schema v2.1)

---

## Aposentado (2026-05-12) — Scripts como geradores de YAML

Decisao Bruno 2026-05-12 (memory `feedback_pristine_cycles_skill_first`): scripts ad-hoc tipo `_pj2_runner.py` como **geradores de YAML** estao APOSENTADOS. A geracao de YAML e responsabilidade EXCLUSIVA desta skill (Modos 1 / 4 / 5).

**O que muda:**
- Indicators novos da familia `_pj2` (13 indicators do roadmap 2026-05-12) sao criados via Modo 1 (Criar) ou Modo 5 (Clone) — **nao** rodando `_pj2_runner.py`.
- `_pj2_runner.py` como **orquestrador de execucao** (rodar Bitrix client, chamar canal classifiers, gerar dataframes) continua valido — apenas nao escreve YAMLs.
- Helpers de execucao (`_pj2_funil_extractor.py`, `compute_tempo_ciclo_estagnacao.py`) continuam validos como **camada de execucao** referenciada pelos YAMLs via `extraction.method` (source_type mcp/hybrid).

**Razao:** ciclos G2.2/G2.3 precisam rodar pristine, sem intervencao manual. YAML produzido por script ad-hoc fica fora do fluxo de validacao/promocao/data lineage da skill — viola a regra de pristine.

**Migracao:** se sua sessao herdou um YAML gerado por `_pj2_runner.py`, recria-lo via Modo 1 ou Modo 5 desta skill, garantindo passagem pelo Protocolo de Data Lineage.
