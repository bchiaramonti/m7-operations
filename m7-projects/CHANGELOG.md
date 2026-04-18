# Changelog

Todas as mudancas notaveis neste plugin serao documentadas neste arquivo.

O formato segue [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/),
e este projeto adere ao [Semantic Versioning](https://semver.org/lang/pt-BR/).

## [0.1.0] - 2026-04-18

Release alpha. Apenas a skill `initializing-project` esta implementada. As demais skills (`building-project-plan`, `managing-action-plan`, `generating-status-materials`) existem como scaffolds vazios e serao implementadas em releases subsequentes antes do v1.0.0.

### Added
- **Skill `initializing-project`**: cria a estrutura base de um diretorio de projeto com as 4 pastas de fase (`1-planning/`, `2-development/`, `3-conclusion/`, `4-status-report/`), subpasta `_docs/` com `assets/` e `bibliography/`, mais `CLAUDE.md` orquestrador e `BRIEFING.md` inicial. Cobre inputs interativos (nome, destino, objetivo, stakeholders, prazo), validacao de destino, criacao de `.gitkeep` em cada pasta, substituicao de placeholders nos templates e validacao pos-execucao (tree + grep de placeholders remanescentes).
- Templates `CLAUDE.tmpl.md` e `BRIEFING.tmpl.md` com placeholders `{{project_name}}`, `{{project_goal}}`, `{{deadline_or_tbd}}`, `{{stakeholders_list}}`, `{{creation_date}}`, `{{clickup_list_id_or_tbd}}`.
- Reference `directory-layout.md` documentando o racional das 4 pastas numeradas, convencao `_docs/` com underscore, formato `YYYY-MM-DD/` para status reports, regras de nomenclatura (kebab-case, sem acentos, max 40 chars) e guidance para renomeacao de projeto.

### Scope (proximas releases)
- `building-project-plan` — construcao do plano formal (WBS/EAP, cronograma, stakeholders, riscos)
- `managing-action-plan` — inicializacao de `CRONOGRAMA.md` + `CHANGELOG.md` do plano de acao e sync bidirecional com ClickUp (SSOT)
- `generating-status-materials` — geracao de OPR (PDF) e apresentacao executiva (PPTX) com Design System M7-2026
