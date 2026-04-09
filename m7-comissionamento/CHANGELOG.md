# Changelog

All notable changes to this project will be documented in this file.

## [1.0.2] - 2026-04-09

### Fixed
- Remove explicit `skills`, `agents`, `commands` arrays from plugin.json — these block auto-discovery in Claude Desktop (same fix as 302ce31 for other plugins)

## [1.0.1] - 2026-04-09

### Fixed
- Bare `except:` clauses in `etl_split_c.py` replaced with specific exception types (`ValueError`, `TypeError`, `IndexError`)
- Magic number `10` (min file size KB) extracted to named constant `MIN_FILE_SIZE_KB`
- Stale directory count in `comissionamento-init` command (5 → 9)
- Marketplace description synced with plugin.json (added "Use quando..." clause)

### Changed
- Checklist template split Fase 8 into 8a (pre-pagamento) and 8b (pos-pagamento) with Fase 9 between them
- Checklist template added Fase 1.0 (revisao de ajustes da competencia anterior)
- Directory structure: added `raw/temp/`, `fase3_pagamento/pgto/`, `fase3_pagamento/demonstrativo_xp/`, `fase3_pagamento/compromissada/` (5 → 9 dirs)
- AJUSTES template changed from flat table to section-based format with emoji legend
- Control file templates (CHANGELOG, AJUSTES, NOTES) extracted from inline SKILL.md to `.tmpl.md` files
- Column specs for `validating-raw-files` extracted to `references/column-specs.md`
- Checklist template version bumped to v6.0

### Added
- 3 commands: `comissionamento-init`, `comissionamento-next`, `comissionamento-status`
- `README.md` at plugin root
- `agents: []` field in plugin.json
- 3 new templates: `AJUSTES.tmpl.md`, `CHANGELOG.tmpl.md`, `NOTES.tmpl.md`
- `references/column-specs.md` for validating-raw-files skill

## [1.0.0] - 2026-04-09

### Added
- Initial release with 5 skills: structuring-competencia, validating-raw-files, processing-split-c-receitas, generating-comissao-oficial, generating-resumo-financeiro
- 6 Python scripts for ETL, validation, classification, and report generation
- Checklist template (v5.0) with 10 phases covering the full commission cycle
- 8 parameterization file templates
