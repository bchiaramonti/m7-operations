# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
