# Changelog

Todas as mudancas notaveis neste plugin serao documentadas neste arquivo.

O formato segue [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/),
e este projeto adere ao [Semantic Versioning](https://semver.org/).

Regras de manutencao (Keep a Changelog 1.1.0):

- Ordem decrescente — release mais recente no topo
- Datas reais — verificar data/hora do sistema no momento do registro; nunca estimar ou retropolar
- Sem proximos passos / roadmap — changelog registra somente o que ja foi liberado; planos futuros vivem em issues/milestones
- Agrupar por tipo — `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security`
- Entries imutaveis apos publicadas — correcoes ao historico viram nova entry, nao edicao da antiga

## [1.0.3] - 2026-04-20

Fix de inconsistencia em `building-project-plan/render_html.py`: os campos de prosa livre `contexto.paragrafos_pre_quote` e `contexto.paragrafos_pos_quote` agora aceitam HTML inline (`<strong>`, `<em>`, `<code>`), consistentes com `recursos.investimentos_paragrafos`, `okrs[].krs[].metric` e campos com sufixo `_html`. Antes, tags passadas nesses campos eram escapadas e apareciam literalmente no render.

### Fixed
- [render_html.py](skills/building-project-plan/scripts/render_html.py) — removido `html_escape()` nas linhas que geram `<p>` para `paragrafos_pre_quote` e `paragrafos_pos_quote`. Passa cru (`f'    <p>{p}</p>'`), igual a `investimentos_paragrafos`. `quote.text`, `quote.source` e `pos_quote_h3` continuam escapados (sao dados estruturados, nao prosa livre).

### Added
- Secao `## Convencao HTML inline vs escape` em [artifact-catalog.md](skills/building-project-plan/references/artifact-catalog.md) — tabela unica listando os 6 campos que passam cru (prosa livre + sufixo `_html`) vs o default seguro (escape). Orienta quem gera `data.json` a usar convencao editorial (CAIXA ALTA, aspas) em campos que escapam.
- Anti-pattern em [building-project-plan/SKILL.md](skills/building-project-plan/SKILL.md): "Usar `<strong>`/`<em>`/`<code>` em campos que escapam HTML" com ponteiro para a secao do catalog.

### Changed
- Tabela de placeholders do artefato 01 em `artifact-catalog.md` agora marca explicitamente `paragrafos_pre_quote` e `paragrafos_pos_quote` como "aceita HTML inline".

### Validation
- `render_html.py` passa `py_compile`
- Smoke test: `<strong>Origem</strong>` em `paragrafos_pre_quote` renderiza como tag (antes: escapado); `quote.text` com `<tag>` continua escapado corretamente (`&lt;tag&gt;`)

## [1.0.2] - 2026-04-20

Alinhamento do comportamento de changelog (plugin + per-projeto) com Keep a Changelog 1.1.0. Remove secoes de "Scope (proximas releases)" das entries historicas, adiciona regras explicitas no header, codifica no template/skill/CLAUDE.md de projeto. Sem mudancas funcionais nos scripts.

### Added
- Bloco de regras de manutencao do changelog no header deste `CHANGELOG.md`, citando Keep a Changelog 1.1.0 (ordem decrescente, datas reais via relogio do sistema, sem proximos passos, agrupamento por tipo, imutabilidade).
- Secao `## Regras de atualizacao do changelog` em [CLAUDE.tmpl.md](skills/initializing-project/templates/CLAUDE.tmpl.md) (template instanciado em todo projeto novo) — garante que cada projeto M7 carregue as regras comportamentais para o `4-status-report/changelog.md`.
- Secao `## Regras de manutencao (Keep a Changelog 1.1.0)` em [changelog-format.md](skills/managing-action-plan/references/changelog-format.md) — formaliza o contrato operacional do per-project changelog.
- Header do template [CHANGELOG.tmpl.md](skills/managing-action-plan/templates/CHANGELOG.tmpl.md) agora referencia Keep a Changelog 1.1.0 e lista as 3 regras operacionais.

### Changed
- [managing-action-plan/SKILL.md](skills/managing-action-plan/SKILL.md) — secao `## Anti-patterns a evitar` expandida com as 3 regras: ordem decrescente, sem proximos passos, timestamp sempre via relogio (nunca improvisar data).
- [changelog_append.py](skills/managing-action-plan/scripts/changelog_append.py) — docstring reforca o contrato: `--timestamp` so existe para casos de replay; fluxo normal usa `dt.datetime.now()` do sistema.

### Removed
- Secoes `### Scope (proximas releases)` das entries historicas `[1.0.0]`, `[0.4.0]`, `[0.3.0]`, `[0.2.0]`, `[0.1.0]` — viola "no future plans in changelog" do Keep a Changelog 1.1.0. Roadmap futuro, quando existir, vive em issues/milestones, nao no historico de releases.
- Secao `### Not changed` da entry `[1.0.1]` — nao e tipo suportado pelo Keep a Changelog 1.1.0; o conteudo era um disclaimer meta que pertence ao corpo introdutorio da entry, nao a uma secao tipada.

## [1.0.1] - 2026-04-18

Patch release — aplicando correções do `validating-artifacts` na skill `generating-status-materials` para levar a grade de C → A (0 fails, 0 warnings). Sem mudanças de comportamento.

### Fixed
- **U6** — `generating-status-materials/SKILL.md`: removidas 2 tags `<example>` do campo `description` do frontmatter. Exemplos de invocação movidos para seção `## Exemplos de invocação` no corpo do SKILL.md (3 exemplos: reporte completo, só OPR, data customizada). Description caiu de 927 → 522 chars.
- **S6** — Adicionado `## Índice` em 4 references longas (>100 linhas) que estavam sem TOC: [narrative-synthesis.md](skills/generating-status-materials/references/narrative-synthesis.md), [xlsx-reading.md](skills/generating-status-materials/references/xlsx-reading.md), [data-sources.md](skills/generating-status-materials/references/data-sources.md), [failure-modes.md](skills/generating-status-materials/references/failure-modes.md). As outras 3 references (design-tokens, opr-layout, presentation-structure) já tinham Índice.
- **S8** — `generating-status-materials/scripts/build_pptx.py`: bloco de 10 constantes documentadas no topo do arquivo (`PAD_SLIDE_X`, `PAD_EXEC_X`, `CONTENT_W_PX`, `DIAMOND_SIZE_ACTIVE`, `DIAMOND_SIZE_NEUTRAL`, `RISK_CARD_H`, `RISK_CARD_GAP`, `RISK_ACCENT_BAR_W`, `RISK_TAG_W`, `LOGO_SIZE_*`) com comentários cruzando para [`design-tokens.md`](skills/generating-status-materials/references/design-tokens.md) e [`presentation-structure.md`](skills/generating-status-materials/references/presentation-structure.md). Constantes são simbólicas (não usadas nos bodies ainda) — posicionamento para refactor gradual sem quebrar comportamento.

### Validation
- `build_pptx.py` passa `ast.parse` após refactor
- Smoke test: PPTX regenerado com sucesso (48589 bytes, 8 slides)
- Description parseia para 522 chars sem XML tags
- Todas as 7 references agora têm `## Índice`

## [1.0.0] - 2026-04-18

Release 1.0.0 — plugin completo. Adiciona a skill `generating-status-materials`, fechando o pipeline end-to-end do ciclo de vida de projetos M7: do scaffolding (`initializing-project`) ao reporte executivo (`generating-status-materials`), passando por planejamento iterativo (`planning-project`), plano formal (`building-project-plan`) e execução sincronizada com ClickUp (`managing-action-plan`). 5 de 5 skills funcionais.

### Added
- **Skill `generating-status-materials`**: gera materiais de status em dois formatos a partir do mesmo pipeline de coleta — **OPR** (one-page report HTML + PDF A4 retrato) para comunicação assíncrona, e **apresentação executiva PPTX 16:9** com 8 slides para reuniões de reporte. Narrativa consistente por construção (ambos consomem o mesmo dict canônico).
  - **3 scripts Python**: `collect_data.py` (coleta determinística: xlsx LIVE + HTMLs do plano + changelog + .sync-state.json → JSON canônico), `build_opr.py` (Jinja2 → HTML → PDF via playwright/weasyprint com fallback), `build_pptx.py` (8 slides construídos programaticamente via python-pptx, fiéis ao canvas Paper `status-report`).
  - **7 references**: [`design-tokens.md`](skills/generating-status-materials/references/design-tokens.md) (cores, tipografia, espaçamento extraídos com `get_computed_styles` do canvas Paper), [`opr-layout.md`](skills/generating-status-materials/references/opr-layout.md) (zonas A4, regras de fit, modo compacto), [`presentation-structure.md`](skills/generating-status-materials/references/presentation-structure.md) (8 slides detalhados + construção), [`narrative-synthesis.md`](skills/generating-status-materials/references/narrative-synthesis.md) (heurísticas determinísticas para status overall, highlights, next steps, attentions), [`data-sources.md`](skills/generating-status-materials/references/data-sources.md) (mapeamento exato campo → fonte), [`xlsx-reading.md`](skills/generating-status-materials/references/xlsx-reading.md) (leitura read-only do LIVE), [`failure-modes.md`](skills/generating-status-materials/references/failure-modes.md).
  - **1 template**: `opr.tmpl.html` (Jinja2 com CSS inline completo, 23 substituições + 26 blocos de controle, tokens M7-2026 via variáveis CSS, modo compacto via classe `.compact`).
  - **2 assets**: `m7-logo-dark.png` (para fundos off-white) e `m7-logo-offwhite.png` (para fundos Verde Caqui), embedados em base64 data URLs no OPR.
- **Mapeamento Paper → PPTX**: 8 artboards 1280×720 do canvas `status-report` mapeiam 1:1 para slides PPTX: Cover · Agenda · Roadmap Overview · Roadmap Detail · Section Divider · Executive Status · Risks · Closing. Tokens visuais (cores exatas, tracking, padding) verificados via `get_computed_styles`.

### Architecture decisions
- **Coleta 100% determinística** — `collect_data.py` aplica heurísticas explícitas (status overall, highlights, next steps, attentions) sem invocar LLM. Honra o feedback arquitetural: "data collection uses deterministic script, never LLM interpretation". Duas execuções com os mesmos inputs produzem dicts canônicos byte-identicos → série temporal de reportes auditável.
- **Skill read-only** — nunca toca em `Cronograma.xlsx` LIVE, `changelog.md` ou `.sync-state.json` (domínio exclusivo de `managing-action-plan`). Escrita confinada a `4-status-report/YYYY-MM-DD/`. Boundary arquitetural: esta skill é consumidora pura do LIVE.
- **Zero MCP** — diferente de `managing-action-plan` (que orquestra ClickUp MCP), `generating-status-materials` é 100% local Python. `clickup_list_url` é derivado de `.sync-state.json` ou `CLAUDE.md`, não consultado.
- **Font Arial (não TWK Everett)** — o canvas Paper `status-report` usa Arial como fonte real (verificado em `get_computed_styles`). Design System M7-2026 aceita Arial como primário oficial; TWK Everett é aspiracional/opcional. Simplifica portabilidade (Arial é ubíquo).
- **8 slides em vez de 10** — reconciliação entre spec 04 (10 slides teóricos) e canvas Paper real (8 slides desenhados). Canvas é fonte de verdade; spec atualizada implicitamente. Cada slide mapeia para dados específicos do dict canônico; ausência de campo vira placeholder visível, nunca silêncio.
- **Dois drivers HTML→PDF com fallback** — playwright (primário, suporte CSS completo, detecta overflow via `document.scrollHeight`) ou weasyprint (fallback leve, puro Python, CSS limitado). Skill degrada graceful se nenhum instalado, mantém PPTX funcional via `--only pptx`.
- **Modo compacto automático no OPR** — detecta overflow A4 em px, rerender com `.compact` (reduz font-size/line-height/gap). Se ainda excede, trunca bullets. "1 página" é contrato; não pagina nunca.

### Validation
- Todos os 3 scripts passam `python3 -m ast.parse`
- Template HTML: 23 Jinja2 variables + 26 control blocks com braces balanceados; CSS `<style>` balanceado
- Smoke test: `build_pptx.py` com dados stub gerou PPTX 51KB com 8 slides sem erros
- Tokens M7-2026 verificados caso-a-caso contra `get_computed_styles` do canvas Paper (cores hex, font-sizes px, letter-spacing em, padding px)

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

## [0.1.0] - 2026-04-18

Release alpha. Apenas a skill `initializing-project` esta implementada. As demais skills (`building-project-plan`, `managing-action-plan`, `generating-status-materials`) existem como scaffolds vazios e serao implementadas em releases subsequentes antes do v1.0.0.

### Added
- **Skill `initializing-project`**: cria a estrutura base de um diretorio de projeto com as 4 pastas de fase (`1-planning/`, `2-development/`, `3-conclusion/`, `4-status-report/`), subpasta `_docs/` com `assets/` e `bibliography/`, mais `CLAUDE.md` orquestrador e `BRIEFING.md` inicial. Cobre inputs interativos (nome, destino, objetivo, stakeholders, prazo), validacao de destino, criacao de `.gitkeep` em cada pasta, substituicao de placeholders nos templates e validacao pos-execucao (tree + grep de placeholders remanescentes).
- Templates `CLAUDE.tmpl.md` e `BRIEFING.tmpl.md` com placeholders `{{project_name}}`, `{{project_goal}}`, `{{deadline_or_tbd}}`, `{{stakeholders_list}}`, `{{creation_date}}`, `{{clickup_list_id_or_tbd}}`.
- Reference `directory-layout.md` documentando o racional das 4 pastas numeradas, convencao `_docs/` com underscore, formato `YYYY-MM-DD/` para status reports, regras de nomenclatura (kebab-case, sem acentos, max 40 chars) e guidance para renomeacao de projeto.
