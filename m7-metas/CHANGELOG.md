# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2026-05-12

### Added — Schema v2.1 (4 campos visuais opcionais)

- **`display_name`** (string, opcional) — label customizado para slides quando diferente de `name`. Aplica a qualquer `source_type`. Documentado em `references/schema-v2.md` secao 3.1.
- **`display_suffix`** (string, opcional, max 16 chars) — sufixo concatenado ao label em render (ex: "CRM" para indicators Bitrix, "MTD" para month-to-date). DRY para evitar repetir suffix em multiplos slides/Cards.
- **`direction`** (enum: `maior_melhor` | `menor_melhor`, opcional, default `maior_melhor`) — direcao do semaforo. Critico para indicators de `unit: days` ou `% estagnacao` onde reducao e o objetivo.
- **`output_schema.por_canal`** (object opcional) — declara decomposicao por canal emitida pelo indicator. Schema: `por_canal: {<canal_id>: {qty, vol, qty_won?, pct_ativas?}}`. Pode estar top-level (sql/hybrid) ou dentro de `extraction.output_schema` (mcp/hybrid).
- 6 regras de validacao novas (34-39) em `schema-v2.md` — todas ATENCAO ou condicionais, nao quebram retrocompat com v2.0.
- 3 templates `.tmpl.yaml` (sql/mcp/hybrid) atualizados com slots/comentarios dos 4 campos novos.

### Added — Modo 5: Clonar Indicador (variante)

- Novo modo de operacao para clonar um indicator existente como variante (sufixo `_pj2`, `_n3_subnivel_x`, etc.).
- Preserva description/tags/granularity/unit/source_type/source_layer/refresh_frequency/analysis_guide/quality_checks/explanatory_context do base.
- Permite override de `query`/`extraction`/`dependencies`/`output_schema.por_canal`/`display_*`/`tags`.
- Forca `status: draft` no clone (sempre).
- Dispara Protocolo de Data Lineage obrigatorio antes de salvar.
- Casos de uso primario: 13 indicators `_pj2` clonados dos `_n3` correspondentes (roadmap 2026-05-12).

### Added — Protocolo OBRIGATORIO de Data Lineage

- Nova secao no topo da `SKILL.md` formalizando regra: antes de gerar/modificar QUALQUER YAML em Modos 1/4/5 (quando muda fonte/query/canal), apresentar bloco de 5 pontos (Fonte, Filtros, Mapeamento canal, Agregacao, Output schema) e aguardar aprovacao explicita.
- Sem aprovacao, skill NAO escreve arquivo.
- Aplica-se a edicoes que tocam em `query`, `extraction`, `dependencies` ou `output_schema`. Edicoes cosmeticas (analysis_guide, tags) NAO precisam.
- Razao: memory `feedback_indicator_data_lineage` — evitar re-trabalho em V.1-V.4 por mapeamentos de canal nao-obvios.

### Changed

- `SKILL.md` reorganizada para 5 modos (era 4): Criar (Modo 1), Validar (Modo 2), Promover (Modo 3), Editar (Modo 4), Clone (Modo 5).
- Fase 1 do Modo 1 expandida para Fase 1 (contexto) + Fase 1.5 (4 campos visuais opcionais).
- Fase 2.5 nova: aprovacao do Data Lineage antes de Fase 3 (Construcao da query/extraction).
- Anti-patterns ampliados: 3 novas regras (data lineage bloqueante, scripts ad-hoc nao geram YAML, direction obrigatoria para unit=days).

### Deprecated

- **Scripts ad-hoc como geradores de YAML** (ex: `_pj2_runner.py` usado em sessao A.x do roadmap 2026-05-09 para gerar YAMLs `_pj2`). Geracao de YAML agora e responsabilidade EXCLUSIVA desta skill (Modos 1/4/5). Razao: memory `feedback_pristine_cycles_skill_first` — ciclos G2.2/G2.3 devem rodar pristine sem intervencao manual.
- Helpers de execucao (`_pj2_funil_extractor.py`, `compute_tempo_ciclo_estagnacao.py`) continuam validos como camada de runtime referenciada por YAMLs via `extraction.method`.

### Backwards Compatibility

- Indicators v2.0 sem campos visuais continuam validos. Builders fazem fallback (display_name ausente → name; direction ausente → maior_melhor; etc.).
- Indicators v1.0 sem `source_type` continuam validos (assumem `source_type: sql` implicitamente).

## [1.1.0] - 2026-05-04

### Added
- **Padrao especial "modo Detalhe"** documentado em `creating-indicators/SKILL.md` — convencao para indicadores que produzem 1 linha por entidade (deal, cliente, ticket) alem das agregacoes hierarquicas. Coluna `nivel='Detalhe'` indica que o registro e individual; colunas extras (deal_id, nome_deal, dias_sem_atividade, estagio) ficam preenchidas APENAS nessas linhas. Usado por componentes visuais que precisam de listas (ex: card "Sem atividade planejada" do ritual de gestao). Exemplos de referencia: `oportunidades_sem_atividade_planejada_funil_seg.yaml` (Seguros), `oportunidades_sem_atividade_planejada_funil.yaml` (Consorcios).
- Secao "Padrao especial — indicadores com modo Detalhe (1 linha por entidade)" em `creating-indicators/SKILL.md` com criterios de quando usar/nao usar.

## [1.0.1] - 2026-04-06

### Fixed
- Removed redundant `"skills": "./skills/"` from plugin.json (duplicates default auto-discovery behavior)

## [1.0.0] - 2026-03-16

### Added
- Plugin scaffold: plugin.json, .mcp.json, README.md
- Skill `creating-indicators` with 4 modes: create, validate, promote, edit
- SKILL.md with progressive disclosure (238 lines, under 500 limit)
- Reference `esp-perf-001-resumo.md` — fields, rules, maturity cycle, business logic
- Reference `guia-elaboracao.md` — building patterns for sql, mcp, hybrid source types
- Reference `schema-v2.md` — 33 validation rules with conditionals by source_type
- Reference `query-conventions.md` — ClickHouse patterns, GROUPING SETS, dimension tables
- Template `indicator-sql.tmpl.yaml` — full multi-level SQL structure based on captacao_liquida_mensal
- Template `indicator-mcp.tmpl.yaml` — MCP extraction with steps + transform
- Template `indicator-hybrid.tmpl.yaml` — hybrid template with bridge documentation
- Template `validation-report.tmpl.md` — CRITICO/ATENCAO/OK report with verdict
- Marketplace entry in `.claude-plugin/marketplace.json`
