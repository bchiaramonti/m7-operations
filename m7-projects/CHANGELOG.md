# Changelog

Todas as mudancas notaveis neste plugin serao documentadas neste arquivo.

O formato segue [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/),
e este projeto adere ao [Semantic Versioning](https://semver.org/lang/pt-BR/).

## [0.4.0] - 2026-04-18

Quarta release alpha. Adiciona a skill `planning-project` — interlocutora especializada em planejamento que conduz a elaboração iterativa do `PLANEJAMENTO.md` (snapshot estático denso, consumível por `building-project-plan`). 4 de 4 skills do ciclo de planejamento/execução agora presentes (faltando só `generating-status-materials` para v1.0.0).

### Added
- **Skill `planning-project`**: conduz elaboração iterativa do Plano de Projeto em Markdown (`1-planning/PLANEJAMENTO.md`) aplicando boas práticas PMBOK + mindset ágil. Fluxo em 3 fases (Setup → Loop de Incrementos → Revisão Consolidada) com um artefato por vez e aceite explícito.
  - Cobre 9 artefatos: Contexto/Escopo, OKRs, WBS/EAP, Cronograma, Roadmap & Marcos, Recursos & Dependências, Plano de Comunicação, Riscos, Calendário
  - **≥36 critérios de aceite** codificados (média 4+ por artefato) em `acceptance-criteria.md`
  - **≥25 push-backs calibrados** em `pushback-playbook.md` — skill confronta conteúdo raso antes de aceitar
  - **7 verificações cross-artefato** na Fase 3 (`consistency-checks.md`): marcos×cronograma, RACI×recursos, owners×equipe, KRs×trabalho, datas, pacotes×cronograma, rituais×comunicação
  - **Racional PMBOK/ágil** em `pmbok-artifact-best-practices.md` — 6 fontes canônicas citadas (PMBOK 7e, Doerr, Google re:Work, ISO 31000, PMI Stakeholder Matrix, Scrum Guide)
- **Schema formal do `PLANEJAMENTO.md`** em `planning-md-schema.md`: frontmatter YAML (com campo opcional `consistency_overrides`), 9 headers `## NN · ...` como âncoras fixas, markers `<!-- STATUS: ... -->` parseáveis, mapeamento seção → artefato HTML para consumo por `building-project-plan`
- **Template `PLANEJAMENTO.tmpl.md`**: 9 seções pre-stubbed com sub-headers guia + bloco de comentário HTML ilustrando convenção completa de markers (PENDING/DRAFT/ACCEPTED/SKIPPED + REASON + OVERRIDE)

### Architecture decisions
- **Skill conversacional, sem scripts Python** — toda lógica vive no prompt + references. Valor está no raciocínio guiado e nos push-backs codificados, não em transformação de dados.
- **Output estático** — `PLANEJAMENTO.md` é snapshot de planejamento inicial; **não é mantido em sync** com os HTMLs depois gerados por `building-project-plan` nem com o ClickUp. Carimbo visível no topo após `FINAL`.
- **Retrabalho permitido** — qualquer artefato `ACCEPTED` pode ser reaberto sem derrubar os demais (contraste com waterfall).
- **Estado persistente** — markers permitem pausar e retomar em dias diferentes.
- **Autonomia do usuário preservada** — skill push-backa, sugere, mas nunca aceita incremento sem ok explícito. Sobrescrita requer `<!-- OVERRIDE: <justificativa> -->` no MD; inconsistências aceitas na Fase 3 vão para `consistency_overrides` no frontmatter (trilha de auditoria para retrospectivas).
- **Fronteira firme com `building-project-plan`**: quality gate é responsabilidade de `planning-project`; transformação é de `building-project-plan`. A skill 03 **não re-aplica** push-backs em modo `read-md` — references de best practices vivem **apenas** aqui, sem duplicação.
- **Mindset ágil, não Scrum ritual** — entregáveis pequenos com aceite por incremento e retrabalho permitido; sem sprint backlog, sem retro, sem timeboxes fixos.

### Integration
- `planning-project` é **opcional** no fluxo. Projetos simples podem ir direto de `initializing-project` → `building-project-plan` em modo interativo. Projetos complexos passam por `planning-project` para densificar o pensamento antes de gerar visuais.
- Contrato com `building-project-plan`: frontmatter → hero da landing; cada seção `## NN · ...` → artefato HTML correspondente; seções `SKIPPED` resolvidas por skill 03 (placeholder vs omissão do nav-grid).

### Scope (próximas releases)
- `generating-status-materials` — OPR (PDF) + apresentação executiva (PPTX) com Design System M7-2026 (consome `4-status-report/Cronograma.xlsx` LIVE + `changelog.md`) — última skill antes de v1.0.0
- Ajustes em `building-project-plan` para consumir `PLANEJAMENTO.md` FINAL em modo `read-md` (parser + 9 handlers + fallback para SKIPPED) — documentados na spec 06

## [0.3.0] - 2026-04-18

Terceira release alpha. Adiciona a skill `building-project-plan` — geração do Plano de Projeto completo (10 HTMLs com Design System M7-2026 + Cronograma.xlsx baseline). Pipeline cross-skill com `managing-action-plan` validado end-to-end. 3 de 4 skills do plugin agora funcionais.

### Added
- **Skill `building-project-plan`**: produz o Plano de Projeto completo dentro de `1-planning/` reproduzindo fielmente a estrutura do projeto-modelo H1-02 Playbook de Processos:
  - 1 landing (`plano-projeto.html`) com hero/estrela/nav-grid de 9 cards
  - 9 artefatos HTML em `artefatos/`: contexto-escopo, eap (WBS org-chart CSS), roadmap-marcos (phase-bar + timeline + swim-lane com lanes/governance + milestone-grid), okrs (objetivos × KRs com cadência), recursos-dependencias (team-grid + alloc-table + dep-table), plano-comunicacao (rituais + RACI + canais), riscos (heatmap 3×3 + risk-legend + risk-detail), cronograma (wh-table com filtros derivada do xlsx), calendario (grid mensal + summary-table com events JS)
  - `Cronograma.xlsx` BASELINE com schema espelhando H1-02 (10 colunas B-K, header bold caqui, formatação por Tipo, freeze B5, auto-filter, data validation em Tipo/Status, todos `Status=not_started`)
- **4 scripts Python** (3 + lib compartilhada):
  - `_lib.py` — tokens M7-2026, helpers HTML compartilhados (topbar/page-header/footer), datas BR (jan/fev/mar/abr/...), asset loading
  - `generate_xlsx.py` — gera `Cronograma.xlsx` BASELINE com formatação completa (cores por Tipo, data validation, freeze, auto-filter)
  - `derive_calendar_events.py` — deriva `events[]` do calendário a partir de Fases do xlsx + milestones do roadmap + rituais (manual + recurring com freq/start/end/weekday)
  - `render_html.py` — engine de renderização: 10 builders (um por artefato), substituição de placeholders, montagem de chunks dinâmicos (nav cards, WBS tree, swim-lane lanes/bars/ticks/qrs com posicionamento `left%`/`width%`, heatmap cells, etc.)
- **10 templates HTML** em `templates/` (1 landing + 9 em `artefatos/`): cada um self-contained com CSS inline próprio + placeholders apenas onde varia o conteúdo. Total: ~1.560 linhas de templates fiéis ao H1-02.
- **5 references**: `design-system-m7-2026.md`, `artifact-catalog.md` (schema completo do `data` JSON por artefato), `cronograma-xlsx-schema.md` (contrato com managing-action-plan), `wbs-conventions.md` (3 níveis na árvore + nível 4 em tabela), `example-project-h1-02.md` (benchmark canônico)
- **Logo M7** (`templates/assets/m7-logo-offwhite.b64` + `m7-logo-dark.b64`) carregado e embedado base64 em hero/page-headers

### Architecture decisions
- **Modelo Z reforçado**: a skill é **proibida** de escrever fora de `1-planning/`. Toda saída do plano formal vive ali. `4-status-report/` é responsabilidade de outras skills.
- **Cronograma BASELINE imutável**: após criação, somente `managing-action-plan` toca em xlsx (e só na cópia LIVE em `4-status-report/`). A coluna L `ClickUp ID` NÃO é adicionada por esta skill — é responsabilidade da `managing-action-plan` no 1º run.
- **Templates self-contained**: cada HTML tem seu próprio `<style>` inline (espelha pattern do H1-02) — funciona offline, copia/cola por email, imprime corretamente. Logo embedado base64 em todos.
- **Renderer simples (Python str.replace)**: sem Jinja2 ou templating engine — placeholders `{{var}}` substituídos sequencialmente. Templates têm chunks dinâmicos (`{{nav_cards_html}}`, `{{wbs_tree_html}}`, etc.) que Python monta a partir do data JSON.
- **Cronograma.html derivado do xlsx**: lê 1:1 do `Cronograma.xlsx` (consistência item-a-item garantida; qualquer divergência seria bug do xlsx ou do parser).
- **Calendar events derivados do xlsx + rituais**: `derive_calendar_events.py` extrai linhas Fase do xlsx (início+fim) + milestones do roadmap + rituais com data fixa + recurring com freq/weekday.

### Cross-skill validation
- Smoke test cross-skill end-to-end passou: `building-project-plan/generate_xlsx.py` produz xlsx que `managing-action-plan/init.py` consome sem ajustes. Pipeline completo: planejamento → execução validado.
- Render end-to-end: 10/10 HTMLs renderizados, ZERO warnings de placeholders remanescentes, 13 events do calendário derivados automaticamente do xlsx + rituais.

### Validation
- Todos os 4 scripts passam `python3 -m py_compile`
- `validating-artifacts` grade C (1 fail em U6 por uso de `<example>` tags na description — decisão consciente e consistente com `initializing-project` e `managing-action-plan`)
- Templates testados com sample data sintético: 10 HTMLs gerados sem erros, ~135KB total

### Scope (próximas releases)
- `generating-status-materials` — OPR (PDF) + apresentação executiva (PPTX) com Design System M7-2026 (consome `4-status-report/Cronograma.xlsx` LIVE + `changelog.md`) — última skill antes de v1.0.0

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
