# Changelog

Todas as mudancas notaveis neste plugin serao documentadas neste arquivo.

O formato segue [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/),
e este projeto adere ao [Semantic Versioning](https://semver.org/lang/pt-BR/).

## [0.2.0] - 2026-04-18

Segunda release alpha. Adiciona a skill `managing-action-plan` (núcleo técnico do plugin) e revisa a `initializing-project` para refletir a nova arquitetura de path (Modelo Z) e o uso de `Cronograma.xlsx` como artefato local.

### Added
- **Skill `managing-action-plan`**: gerencia o ciclo de vida do plano de ação com sincronização three-way determinística entre `Cronograma.xlsx` (estrutura local), `changelog.md` (auditoria + espelho de comentários) e ClickUp (SSOT global). Operações: `init`, `create`, `update`, `delete`, `comment`, `followup`, `sync`.
- **9 scripts Python puros** (sem MCP — Claude orquestra chamadas ClickUp baseado nos payloads emitidos):
  - `_lib.py` — biblioteca compartilhada (parsing/normalização/hash/IO xlsx/sync state)
  - `parse_cronograma.py` — parser xlsx → JSON canônico (tolera datas mistas BR `02/abr` + datetime; valida hierarquia)
  - `hash_row.py` — hash SHA-256 determinístico (estável entre formatos de data equivalentes)
  - `changelog_append.py` — append entries no `changelog.md` (formato Keep a Changelog adaptado)
  - `init.py` — first-run setup (copia baseline → live + adiciona coluna L `ClickUp ID` + cria changelog/sync-state + emite push plan topológico)
  - `xlsx_write.py` — mutações no xlsx (write-clickup-id, write-cell, append-row, delete-row, bulk-cells)
  - `actions.py` — CRUD subcommands (create/update/delete/comment) com payloads ClickUp prontos
  - `followup.py` — detecção de overdue/upcoming/stagnated/unstarted + perguntas formuladas
  - `sync.py` — three-way diff (prepare) + baseline refresh (finalize/finalize-init)
- **7 references** (`cronograma-schema`, `action-lifecycle`, `sync-algorithm`, `field-resolution-rules`, `followup-heuristics`, `failure-modes`, `changelog-format`)
- **Template** `CHANGELOG.tmpl.md`
- `.gitignore` na raiz do marketplace (`__pycache__`, `*.pyc`, `.DS_Store`)

### Changed
- **`initializing-project`**: `templates/CLAUDE.tmpl.md` e `references/directory-layout.md` atualizados para refletir Modelo Z — `4-status-report/` agora hospeda arquivos live (`Cronograma.xlsx` + `changelog.md` + `.sync-state.json`) na raiz da pasta + snapshots dated `YYYY-MM-DD/` (OPR + PPTX). `1-planning/` ganhou referência ao `Cronograma.xlsx` baseline produzido por `building-project-plan`. Tabela de invariantes da skill atualizada com as 3 camadas.

### Architecture decisions
- **Cronograma é xlsx, não markdown**: descoberto durante implementação que o usuário trabalha com cronogramas em Excel (não markdown como a spec original previa). Spec 02 reescrita; trabalho inicial de parser markdown descartado.
- **Modelo Z (path policy)**: arquivos de gestão do plano vivem na raiz de `4-status-report/`; subpastas dated guardam só snapshots de reportes. Mais simples que alternativas com pasta `current/` separada.
- **`ClickUp ID` em coluna L** do xlsx: visível, simples, é a âncora estável cross-session (não o `No.` que pode renumerar).
- **3 camadas com SSOT global no ClickUp**: status/comentários/dados operacionais vencem do ClickUp; estrutura/datas planejadas vencem do xlsx local. Field resolution rules em [field-resolution-rules.md](skills/managing-action-plan/references/field-resolution-rules.md).
- **Mapping responsáveis em CLAUDE.md do projeto** (não em sidecar JSON): humano-legível e versionável junto do orquestrador.

### Scope (próximas releases)
- `building-project-plan` — construção do plano formal incluindo geração do `Cronograma.xlsx` baseline (v0.3.0)
- `generating-status-materials` — OPR (PDF) + apresentação (PPTX) com Design System M7-2026 (v1.0.0)

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
