# Changelog

All notable changes to this project will be documented in this file.

## [2.0.1] - 2026-04-06

### Fixed
- Removed invalid `skills` object format (used `{name, source}` objects instead of path strings) from plugin.json
- Removed empty `agents: []` and `commands: []` arrays that were blocking Claude's auto-discovery of default directories

## [2.0.0] - 2026-04-01

### Breaking
- Plugin agora gerencia apenas acoes de melhoria (plano-de-acao.csv)
- Removidos dominios de projetos estrategicos e rotinas operacionais

### Removed
- managing-plans: Modo 6 (marcar rotina como nao executada)
- managing-plans: Operacao "pausar" (era exclusiva de projetos)
- reviewing-plans: Modo 3 (gerar instancias de rotinas)
- reviewing-plans: Secoes de projeto e rotinas no plano do dia
- reviewing-plans: KPIs de projetos e rotinas
- csv-schemas.md: Schemas de projetos-estrategicos.csv e rotinas-operacionais.csv
- csv-conventions.md: Regras de ID para PJ- e RO-
- reviewing-plans/references/csv-schemas.md (copia duplicada removida)

### Changed
- managing-plans: 6 modos → 5 (criar, atualizar, concluir, cancelar, followup)
- reviewing-plans: 3 modos → 2 (plano do dia, KPIs) — agora 100% read-only
- Plano do dia: 5 secoes → 3 (criticos, follow-ups, proximos 7 dias)
- KPIs: removido filtro de tipo (so melhorias restam)
- Matriz de validacao simplificada para lista unica
- reviewing-plans referencia csv-schemas.md de managing-plans (sem duplicacao)

## [1.1.0] - 2026-03-31

### Changed
- Migrated 3 commands (add, update, review) into user-invocable skills
- Both skills now `user-invocable: true` with natural-language trigger examples
- managing-plans: absorbed operation validation matrix and output format from commands
- reviewing-plans: absorbed mode defaults and date-format inference from review command
- Extracted hardcoded OneDrive path from SKILL.md bodies to csv-schemas.md references
- Added `skills`, `agents`, `commands` arrays to plugin.json manifest
- Improved descriptions with "when to use" trigger clauses (U4 compliance)
- Rewrote managing-plans description opener to third-person verb form (U3 compliance)
- Added `name: review` to review.md frontmatter for consistency (before removal)

### Removed
- `commands/` directory (add.md, update.md, review.md) — functionality absorbed by skills

## [1.0.0] - 2026-03-31

### Added
- Plugin structure scaffolded from PLG-04 spec
- Skills: managing-plans, reviewing-plans (stubs)
- Commands: add, update, review (stubs)
- References: csv-schemas, csv-conventions (stubs)
