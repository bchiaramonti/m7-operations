# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.9.0] - 2026-05-31

### Refactor — `plan-preview.json` schema v2.0 (canonicalizacao)

Auditoria de 5 plan-previews recentes (Seg WL/RE S20-S22 + Cons S21-S22) revelou
**4 schemas diferentes** circulando para `responsavel_externo` em `contramedidas_novas[]`.
Cada novo schema forcou um fallback defensivo em `slack_send.py:_extract_responsavel`
(4 caminhos) e em `render_ata.py:185` (triplo fallback). Hoje 2026-05-29 (Seg RE S22)
quebrou silenciosamente com Schema 4 (`responsavel_externo` sem `_label`) e exigiu
hot-patch no parser. Esta release canonicaliza o schema.

### Changed
- **`plan-preview-schema.md` v2.0** (era v1.0 de 2026-05-06):
  - `schema_version: "2.0"` literal (validador gatekeeper bloqueia outros valores).
  - `ata_id` prefix fixo: `C-NNN` para contramedidas (era `CM-NNN`), `D-NNN` para decisoes.
  - **Campos TOP-LEVEL obrigatorios em `contramedidas_novas[]`**: `name`, `descricao`,
    `due_date` (YYYY-MM-DD), `priority_clickup` (1-4), `priority_label`
    (`urgent`/`high`/`normal`/`low`), `responsavel_externo_label`,
    `responsavel_externo_option_value`. Sub-objeto `clickup_create_payload` so contem
    `list_id` + `status` quando necessario.
  - `decisoes[]`: campo `prazo` REMOVIDO (decisoes nao tem prazo — memory
    `feedback_decisoes_sem_prazo`); `descricao` substitui `decisao`; `titulo` novo
    para tabela curta; `transcricao_ref` novo para auditoria.
  - `tasks_atualizadas[]`: `clickup_id` (era `task_id`), `name_humano` (era
    `task_name`), `before.due_date` string YYYY-MM-DD (era `due_date_ms` epoch).
  - `proximos_passos_nao_clickup` (era `proximos_passos`).
  - `metricas_resumo` novo — agregados para sumario rapido.
- **`decision-recorder.md`** ganha exemplo literal v2.0 + regra explicita de NAO
  aninhar campos canonicos em `payload`/`clickup_create_payload`.
- **`recording-decisions/SKILL.md`** Fase 4.5: schema v2.0 documentado in-line +
  requisitos minimos listados.

### Added
- **`render_ata.py::_assert_schema_v2()`** — gatekeeper que aborta em commit se
  `schema_version != "2.0"`. Apontado para o doc canonico em mensagem de erro.
- **`slack_send.py::_assert_plan_preview_schema_v2()`** — gatekeeper espelhado:
  quando `--plan-preview-json` e fornecido (post_ritual), aborta se schema antigo.
  Evita "(sem responsavel)" silencioso em plan-previews pre-v3.9.0.

### Removed
- **`render_ata.py:185`** — fallback triplo `responsavel_externo_label or
  responsavel or responsavel_externo` simplificado para apenas
  `responsavel_externo_label`. Idem `due_date_label or due_date` → so `due_date`.
- **`slack_send.py::_extract_responsavel`** — removidos 4 fallbacks (custom_fields
  field_name, clickup_create_payload.custom_fields UUID, payload nested, list-form).
  Le APENAS `responsavel_externo_label` top-level (gatekeeper garante).
- Suporte legado dual-schema em `tasks_atualizadas[]` (`campos_alterar.status`,
  `name_atual`, `titulo`, `name`).

### Refactor cascata — referencias v2.0 em docs/templates do processo pos-ritual

Apos a canonicalizacao v2.0, auditados e atualizados:

- **`commands/record-decisions.md`**: exemplos `CM-001`/`CM-003` -> `C-001`/`C-003`; label `alta · prio 2` -> `high · prio 2`.
- **`references/clickup-actions-schema.md`**:
  - Secao 3 reescrita como "Mapeamento `plan-preview.json` v2.0 ↔ Payload MCP" — colunas refletindo campos TOP-LEVEL v2.0 (`name`, `descricao`, `due_date`, `priority_clickup`, `responsavel_externo_option_value`, `indicador_impactado_option_id`, `origem_option_id`, `volume_impacto`, `receita_impacto`).
  - Tabela de prioridade reescrita para usar `priority_label` (urgent/high/normal/low) + `priority_clickup` (1-4); legacy `critica/alta/media/baixa` deprecado.
  - Conversao de prazo: `cm["due_date"]` (string YYYY-MM-DD) -> epoch ms para MCP.
  - Checklist de integridade: refs atualizadas para campos v2.0.
- **`references/prioritization-rules.md`**: tabela de prioridade migrada para schema v2.0; ordenacao usa `priority_clickup` ascendente; `justificativa_prio` listada como campo obrigatorio top-level.
- **`templates/ata-ritual.tmpl.md`**: tabela de Decisoes sem coluna `Prazo` (memory `feedback_decisoes_sem_prazo`); comentario de ordenacao migrado para `urgent > high > normal > low`.
- **`agents/decision-recorder.md` Fase 5b**: tasks_atualizadas commit le `ta["before"]`/`ta["after"]`/`ta["comment"]` literal do plan-preview v2.0; `due_date` (YYYY-MM-DD) convertido para `due_date_ms` na chamada MCP.

### Fix — `distributing-materials/SKILL.md` Critical Rule 3

- Critical Rule 3 reescrita: era `"DMs-only: nunca postar em canal"` (legado pre-v3).
  Agora documenta corretamente:
  - `pre_ritual` → DMs individuais (so coordenador/gestor desde 2026-05-20).
  - `post_ritual` → canal da vertical (`Canal-Vertical-ID` no XLSX); fallback DMs
    apenas quando canal vazio.
  - Alinhado com memory `reference_ritual_dist_recipients_per_mode` v3 autoritativa.

### Memory atualizada
- `reference_slack_send_parser_schema` — historico de fallbacks consolidado; parser
  agora le APENAS o canonico v2.0.

### Migracao

- **Seg RE S22 (ciclo ativo)** migrado in-place para schema v2.0 nesta release.
  Backup do v1.0 salvo em `plan-preview.v10-backup.json` na mesma pasta.
- Plan-previews v1.0 mais antigos (Seg WL/RE S20-S21, Cons S21-S22) sao imutaveis
  — atas e ClickUp tasks ja commitados. Se for necessario re-rodar ciclo antigo:
  apagar `plan-preview.json` antigo e re-executar `/m7-ritual-gestao:record-decisions`
  (decision-recorder v2.0 emite novo JSON nativamente).

## [3.8.4] - 2026-05-26

### Added
- **`scripts/render_ata.py`** (337 linhas) substitui scripts ad hoc em `/tmp/`.
  Resolve incompatibilidade entre template Handlebars (`{{#each}}`/`{{#if}}`) e
  renderer chevron (Mustache puro) via pre-processador com stack matching.
  SKILL.md Fase 5.5a aponta pro script direto.

### Changed
- **SKILL.md Fase 4.5** ganha REGRA OBRIGATORIA: sumario stdout deve enumerar
  TODOS os itens da ata (decisoes + contramedidas + acoes_atualizadas +
  proximos_passos + decisoes_recorrentes + escalonamentos + duplicatas), nao
  apenas counts. Memory `feedback_preview_lista_tudo_da_ata` (lapsus Cons S22).
- **`ata-ritual.tmpl.html`**: 3 hardcodes "N2" substituidos por placeholder
  `{{nivel}}`. Memory `reference_ata_template_nivel_placeholder`.

## [3.8.3] - 2026-05-26

### Changed
- **Ata HTML/PDF** nao mostra mais colunas ID em tabelas humanas
  (Contramedidas / Duplicatas / Acoes Atualizadas). IDs ClickUp 86xxx sao infra
  e ficam exclusivamente no bloco `scope_task_ids` do MD (machine-readable).
  Tabelas humanas identificam por Titulo. Memory `feedback_clickup_invisible_to_humans`.
- **`slack_send.py` RN-07** check `tendencia_mom` agora aceita `data_referencia`
  (top-level) ou `meta.snapshot_at` como marcador temporal, alem do par
  `periodo_inicio + periodo_fim` legado — destrava `/approve-ata` para WBRs
  canonical v1.3+ que so emitem `data_referencia`.

## [3.8.2] - 2026-05-26

### Added
- **`/approve-ata`** anexa tambem a apresentacao do ritual
  (`RITUAL_DIR/apresentacao/ritual-*.html`) junto da `ata.pdf` quando
  disponivel. Anexo opcional (skip silencioso quando ausente). Referencia
  historica para participantes consultarem os slides apos o ritual.

### Fixed
- **`recording-decisions`** path canonical S3: `ata/` lowercase + `Transcricao*.md`
  (commit 051366c).
- **`distributing-materials`** `escalacao_acionada` falso positivo no `post_ritual`
  (commit 7f53b7d).

## [3.8.1] - 2026-05-25

### Changed
- **Post-ritual** vai pro canal Slack da vertical (`Canal-Vertical-ID` no XLSX)
  com contramedidas detalhadas agrupadas por Responsavel Externo (cada
  participante identifica acoes dele no canal coletivo); fallback DMs quando
  canal nao configurado.
- **Mensagens clean** sem tech case (sem ClickUp pa-resultado, sem decisoes —
  detalhe na ata PDF).
- **Pre-ritual** so para gestor + mensagem clean (commit 0398cc7).

## [3.8.0] - 2026-05-23

### Added
- **Bot Slack Phase 2** — wire automatico em `/next` (branchea em E3 e E5.7
  para previews) + Fase 7 distribuicao da ata pos E5. Commit final via
  `/approve-ritual` e `/approve-ata`.
- **Bot Slack Phase 1** — skill `distributing-materials` com `slack_send.py`
  (upload 3-step `getUploadURLExternal` -> PUT binario ->
  `completeUploadExternal`) + `resolve_recipients.py`. Le User IDs e Canal-ID
  do `Calendario-de-Rituais.xlsx` estendido (colunas Subnivel, Gestor-User-ID,
  Participantes-User-IDs, Lider-Direto-User-ID, Canal-Vertical-ID), abre DM via
  `conversations.open` em runtime.
- **Suporte multi-subnivel** (split por `metadata.subnivel` — caso piloto SEG
  WL/RE) com argumento opcional `subnivel` em todos os commands.

### Changed
- **Paths canonical S3 desde 2026-05-20**: `02-Controle/{Vertical-cap}[-{subnivel}]/{YYYY-MM}/{YYYY-MM-DD}/`
  + `03-Rituais/{Vertical-cap}[-{subnivel}]/N{N}-{Cadencia}/{Periodo}/`.
- **Calendar XLSX** estendido com colunas para distribuicao via bot.

### Fixed
- 9 fixes em `build_deck.py` validados em Seguros RE S20 (commit dec084f).
- 3 bugs no Delta vs prev cycle: direction, unidade, override-prev (commit 1037afa).
- 3 fixes: volume override stale, delta vazio, meta N2 sem por_especialista
  (commit 7110af0).
- 3 bugs em `build_deck`: Matriz total / causa-raiz / auto-resolve S3 (commit e91e15a).
- 2 bugs no Delta vs Sem.Ant. (Ticket Medio + auto-resolve, commit 37b9828).
- Apresentacao polish completa S1 (13 iter + 2 auditorias, commit baa1268).
- `validate-painel` regra 38b aditividade `SUM(n2) = N1` (commit 0ffc376).

## [3.7.0] - 2026-05-07

> **Minor release retrocompativel** — Reformulacao significativa dos slides
> de fechamento mensal apos 3 rounds de feedback do usuario sobre o preview
> visual. Inclui mudanca arquitetural: C8 sai de "agente improvisa HTML" para
> "script Python deterministico" + reformulacao do Slide Consolidado N3.

### Added

- **C8 v2 (commit 20cbdcf)** — slides de fechamento agora gerados pelo
  `build_deck.py` (deterministico). 3 funcoes Python novas:
  `render_fechamento_n1_slide`, `render_fechamento_esp_slides`,
  `render_diretrizes_slide`. Novos placeholders no template.
- **Args CLI novos**: `--wbr-fechamento` (auto-resolve via glob) e
  `--diretrizes-json` (output da LLM ou override do Card).
- **F1-F6 (commit 01b85f2)** — 6 ajustes de processo: ordem KPI Resultado
  (Volume → Receita → Quantidade), riscos com zoom em deals, Sem Especialista
  + projecao N1 sempre visivel, agenda dinamica com blocos extras, rank
  Criadas/Fechadas no slide Fechamento Especialista, headline jornalistica
  + cards compactos.
- **P1-P3 (commit 69d449a)** — proj N1 sempre visivel com fallback graceful,
  rank-card Criadas/Fechadas substitui SVG line chart (auto-resolve
  dados-consolidados do ciclo de fechamento), headline 36px + cards
  quadrados (`grid-auto-rows: 1fr` + `flex-grow:1`).
- **Q1+Q2 (commit f6bf358)** — Slide Consolidado N3 reformulado:
  - "N3 consolidado" renomeado para "M7 consolidado" + remocao de proj inline
  - Linha 2 nova: 2 cards Projecao M7 consolidado (Volume + Receita) com
    Realizado MTD / Proj. Mes Atual (M0) / Proj. Mes Seguinte (M+1) + meta
    de referencia. Preenche o espaco em branco abaixo dos cards de cima.
  - Bonus: `_resolve_indicator()` substitui hardcodes "consorcio_mensal" em
    `render_consolidado_encerramento` (estava quebrado para SEG).

### Changed

- **C2 reclassificacao KPI/PPI** continua como Fase C original
- **agente material-generator Fase 2.5** simplificada — agora so chama LLM
  para gerar JSON de diretrizes (renderizacao HTML deixou de ser atribuicao
  do agente)

### Compatibility

- 100% retrocompativel com WBRs antigos: campos novos opcionais.
- Cache local: precisa atualizar via `/plugin marketplace update m7-operations`
  + `/plugin install m7-ritual-gestao@m7-operations` para usar v3.7.0.

## [3.6.0] - 2026-05-07

> **Minor release retrocompativel** — 8 tweaks de template aplicados apos
> ritual N3 Consorcios 2026-S19. Foco: Lide jornalistico, classificacao
> KPI/PPI correta, riscos ligados a funil, fechamento mensal automatico
> com diretrizes via LLM, projecao bar style refeita, consolidado N1 com
> "Sem Especialista" + projecao da vertical.
>
> **Habilita** os campos novos do m7-controle v6.4.0 (`consolidado_n1`,
> `criada_em_ritual_anterior`, `is_first_ritual_of_month`, `close_mode`).

### Added

- **C1 — Lide jornalistico**: callout do Slide Matriz reformulado em manchete
  unica (pyramid invertida). Override via `Card.apresentacao.matriz_lide_override`.
  Label trocada de "Leitura" para "Lide".
- **C3 — Status PAs com flag `criada_em_ritual_anterior`**: barras stacked por
  owner com 3 segmentos coloridos (No Prazo verde / Atencao laranja / Atrasada
  vermelho) + badge ⭐ para tasks criadas no ritual anterior. Funcao
  `enrich_tasks_ritual_anterior` infere janela `[data_ultimo_ritual,
  data_ritual_atual)` lendo cycle_dir auto-resolvido.
- **C7 — Consolidado N1**: barra "Sem Especialista" cinza (sem meta) quando ha
  realizado nesse bucket. Linha consolidada da vertical agora consome
  `consolidado_n1` do projection-by-especialista.json (preferred), com fallback
  para meta_mes_corrente. Mostra Realizado MTD + Projecao M0.
- **C8 — 1o ritual do mes (close_mode dispatch)**:
  - Nova **Fase 1.6** no agente material-generator detecta
    `is_first_ritual_of_month: true` no WBR data JSON e localiza o WBR de
    fechamento do mes anterior em `{vertical}/{YYYY-MM}-fechamento/`.
  - Nova **Fase 2.5** insere 3 grupos de slides extras antes do Slide Matriz:
    1. Fechamento {Mes Anterior} consolidado (cards M7-2026)
    2. Fechamento por Especialista N3 (cards + grafico evolucao mensal)
    3. Diretrizes do Mes Atual (gerado via LLM com prompt versionado)
  - Nova reference [diretrizes-prompt.md](skills/preparing-materials/references/diretrizes-prompt.md)
    com template de prompt fixo + schema JSON de output + override manual via
    `Card.apresentacao.diretrizes_override` + log de auditoria em
    `{cycle_folder}/dados/llm-diretrizes-{vertical}.log.json`.

### Changed

- **C2 — Reclassificacao KPI/PPI nos Cards** (Cons + Seg WL + Seg RE):
  - `taxa_conversao_funil_*` → `papel: ppi_funil` (era `kpi_principal` em Cons).
    Taxa de conversao mede saude do funil, nao e indicador de resultado.
  - `quantidade_*_mensal` → `papel: kpi_principal` (era `contexto` em Cons,
    `ppi_funil` em Seg). Quantidade de cartas/apolices e indicador de Resultado
    (output da operacao), nao funil.
- **C4 — Riscos priorizados por PPI**: `_esp_riscos` agora ordena items por
  (PPI primeiro, depois severidade). Riscos sobre Funil (PPI) aparecem no topo;
  riscos sobre Resultado (KPI) descem para o fim. Decisao do usuario: riscos
  devem alertar sobre o que ainda PODE ser endereçado, nao sobre o que ja
  aconteceu.
- **C5 — Slide Analise por Canal limpo**:
  - Card "Intake mes" REMOVIDO (duplicava info ja presente na Matriz).
  - Fix de legibilidade nas barras vermelhas: `text-shadow: 0 0 2px rgba(0,0,0,0.55)`
    + `font-weight: 700` em `.fb-bad` e `.mini.dual .fb-lose`.
- **C6 — Projecao bar style refeita**:
  - Track clara representa META (100% da largura)
  - Fill colorido representa valor/meta (clamped a 100)
  - Coluna 1: label + valor real (Realizado: R$ 33K)
  - Coluna 3: META do indicador (referencia, lighter)
  - Antes: track tinha 100% width sempre, fill proporcional ao max(todos valores).
    Confundia interpretacao.

### Compatibility

- 100% retrocompativel com WBRs antigos: campos novos (`consolidado_n1`,
  `criada_em_ritual_anterior`, `is_first_ritual_of_month`) sao opcionais.
- Cards sem reclassificacao (`papel`) continuam renderizando via fallback.
- Fase 2.5 (close_mode dispatch) so ativa quando flag presente — caso ausente,
  deck regular.

## [3.5.1] - 2026-05-06

> **Patch release** — Padronizacao de `name` de contramedida ClickUp em verbo
> no infinitivo. Decisao formalizada no ritual N3 Consorcios 2026-05-06
> (Pedro action item 22:57): "Ajustar titulos das acoes no sistema para
> verbos no infinitivo".

### Added

- **Secao 3.1 em `clickup-actions-schema.md`**: regra obrigatoria de verbos no
  infinitivo no `name` de contramedida nova. Inclui: tabela errada/correto,
  lista de verbos comuns por categoria de acao (descoberta / producao /
  reuniao / corretiva / QA / comunicacao / fix), anti-padroes (substantivos,
  gerundios, referencias a pessoa, datas), validacao sugerida (terminacao
  `-r`) e regra de reescrita automatica via cognato (`Diagnostico` →
  `Diagnosticar`).
- **Anti-pattern #15 em `recording-decisions/SKILL.md`**: proibe criar task
  com nome que nao comece com infinitivo; obriga reescrita automatica + log
  em `pendencias` para confirmacao do usuario.
- **Regra inviolavel no `decision-recorder.md`** (Sobre o ClickUp): mesma
  regra com formato detalhado de aplicacao na Fase 4.5 (preview).

### Changed

- **Exemplo de payload em `clickup-actions-schema.md` secao 4** atualizado:
  `"Diagnostico carteiras zeradas..."` → `"Diagnosticar carteiras zeradas..."`.

## [3.5.0] - 2026-05-06

> **Minor release retrocompativel** — Reescreve o fluxo da skill
> `recording-decisions` (E5) com 2 capacidades novas: (1) auto-descoberta da
> transcricao do ritual no caminho canonico e (2) gate de aprovacao 2-fase
> preview/commit antes de qualquer escrita no ClickUp. Backward compat: skill
> ainda aceita `notas_ritual` inline e funciona se transcricao nao existir.

### Added

- **Auto-descoberta de transcricao** em `recording-decisions/SKILL.md` Fase 1
  e `decision-recorder.md` Fase 1. Antes de pedir notas ao usuario, a skill
  resolve `RITUAL_DIR` via `preparing-materials/scripts/resolve_ritual_path.py`
  (helper compartilhado, ja existente, suporta `N3-Semanal` + `N2-Mensal` +
  `subarea` para multi-subnivel) e busca `Transcricao-*.md` em `{RITUAL_DIR}/Ata/`.
  Se encontrado, `notas_ritual_path` e passado para o agente; se ausente,
  fallback para input inline. Cobre **todos os niveis** suportados pelo helper.
- **Modo de execucao 2-fase `preview` / `commit`** no agente
  `decision-recorder` e na skill `recording-decisions`:
  - **`mode=preview`** (default): le inputs, gera ata MD rascunho + monta
    `plan-preview.json` com payloads completos de cada operacao ClickUp
    prevista (create_task, update_task, comment), retorna sumario stdout.
    **Zero chamadas de escrita no ClickUp.** Apenas leitura
    (`clickup_get_custom_fields`, `clickup_filter_tasks`, `clickup_get_task`).
  - **`mode=commit`**: le `plan-preview.json` aprovado, valida (mtime <24h,
    schema_version, tasks ainda existem, sem duplicatas novas), executa
    Fases 5-6.
- **Gate de aprovacao no command** `/m7-ritual-gestao:record-decisions`
  (Step 6.5): apos invocar skill em `mode=preview`, command exibe no chat
  sumario estruturado em 5 secoes (decisoes / contramedidas novas / tasks
  atualizadas / duplicatas / pendencias) e pergunta `[s = commit / n = cancelar
  / editar = corrigir]`. Em `editar`, re-invoca preview com correcoes do
  usuario.
- **Novo reference** `recording-decisions/references/plan-preview-schema.md`
  documentando o schema canonico do `plan-preview.json` (TypeScript-style,
  exemplo minimo, regras de geracao, validacao em commit).
- **Novo input** `mode` na tabela de Inputs do `decision-recorder.md`
  (`"preview"` | `"commit"`).
- **Novo input** `notas_ritual_path` (alternativa a `notas_ritual` inline)
  populado automaticamente pela skill quando transcricao canonica encontrada.
- **Novo input** `plan_preview_path` (apenas `mode=commit`).

### Changed

- **`recording-decisions/SKILL.md`** Fase 1 step 6 reestruturado: auto-descoberta
  e o caminho primario, input do usuario e fallback. Anti-pattern #14 adicionado
  proibindo pular auto-descoberta quando caminho canonico existe.
- **`recording-decisions/SKILL.md`** Anti-pattern #12 adicionado proibindo
  qualquer escrita no ClickUp em `mode=preview`.
- **`decision-recorder.md`** Regra de Interacao com Usuario reescrita:
  exibicao do rascunho e aguardo de confirmacao agora e responsabilidade do
  command (via split preview/commit), nao do agente no main thread. Agente
  apenas gera plan-preview.json e retorna sumario stdout.
- **`decision-recorder.md`** Fase 0 nova: bifurcacao por modo (preview vai
  Fases 1→4.5; commit vai Fases 4.6→5+).
- **`decision-recorder.md`** Fase 4.5 nova: gerar `plan-preview.json` com
  payloads completos resolvidos (responsavel_externo → option_value,
  due_date_ms calculado, custom_fields completos).
- **`decision-recorder.md`** Fase 4.6 nova: validar plan-preview em
  `mode=commit` (idade, schema, tasks ainda existem, sem duplicatas novas).
- **`commands/record-decisions.md`** Step 4 reescrito (auto-descoberta com
  fallback). Step 6 desdobrado em 6 (invoke preview), 6.5 (apresentar plano
  + aprovar) e 6.6 (invoke commit). Tratamento de erros estendido com 5
  novos casos (transcricao ausente, rejeicao, edicao, plan-preview ausente,
  plan-preview velho).

### Compatibility

- Cards existentes (Consorcios, Investimentos, Seguros WL/RE, Universo,
  Credito) funcionam sem alteracoes — auto-descoberta e melhoria, transcricao
  ausente cai em fallback inline.
- Scheduled tasks `0 8 * * 4` (quinta 08:00) continuam validas — execucao
  agora pausa para aprovacao do usuario; em sessao automatizada sem
  presenca humana, recomenda-se manter `mode=preview` apenas e revisar
  manualmente antes do commit.

## [3.4.0] - 2026-05-06

> **Minor release retrocompativel** — Consolida 7+ rodadas de fixes do
> `prepare-ritual` Consorcios S19 (2026-05-06) em release oficial. Adiciona
> ~600 linhas em `build_deck.py` cobrindo 11 novos campos opcionais do
> `Card.apresentacao` que permitem customizacao de deck/briefing **sem
> editar HTML output**. Backward compat: campos ausentes = comportamento
> legado padrao.

### Added

- **Novo reference `card-apresentacao-schema.md`** (404 linhas) em
  `skills/preparing-materials/references/` documentando o schema completo
  de TODOS os campos opcionais do `Card.apresentacao` consumidos por
  `build_deck.py`. Inclui ordem de aplicacao no script e exemplos.
- **11 novos campos opcionais no Card.apresentacao** suportados pelo
  `build_deck.py`:
  - `responsaveis[].squad` — whitelist de assessores oficiais por especialista.
  - `overrides_ritual` (com `n5_by_esp`) — override de realizado por bug
    bridge SQL upstream.
  - `projection_overrides` — override de projecoes com `metodo` versionado
    (ex: bug fix `a-fix` para double-count receita).
  - `projecao_proximo_mes` — projecao M+1 quando Card v6.x ainda nao calcula.
  - `suppress_in_ritual` — filtros para Slide 12 Encerramento (anomalias /
    destaques / recomendacoes via keywords).
  - `destaques_positivos_custom` — prepended em wbr.destaques (alta prioridade).
  - `anomalias_custom` — prepended em wbr.anomalias.
  - `recomendacoes_custom` — prepended em wbr.recomendacoes.
  - `pa_manual_append` — tasks ClickUp manuais adicionadas no Slide 5 PA.
  - `metadata.{total_label, responsaveis_n2, assessor_aliases,
    responsavel_externo_aliases}` — labels e aliases para deduplicacao.
  - `kpi_references[].matrix_views[].sem_esp_ratio` — derivacao cross-indicator
    para celula Sem Especialista em rows derivadas (% ativas).
- **Funcoes-chave em build_deck.py:** `_apply_card_overrides`,
  `_apply_n5_overrides`, `_get_squad_whitelist`, `_resolve_n2`,
  `_derive_compute_sem_esp`, `_aggregate_assessor_volumes`, `_esp_riscos`,
  `render_consolidado_encerramento`, `render_pa_slides`. Total: 3.827 linhas.

### Changed

- **Template `ritual.tmpl.html`** atualizado:
  - Dashboard 5 colunas (sem `.stat`).
  - `.real` com cor texto (good/warn/bad) + `.desvio` com qtd + % entre parenteses.
  - `.matrix-grid.dense` (auto-aplicado quando matrix_rows > 9) reduz padding
    e font-size para caber 11+ rows em 1080px.
- **Sem Esp universal cinza** — qualquer Card/vertical: Sem Esp NUNCA tem
  meta nem semaforo (cor mute em todas as celulas).
- **Callout dedup parent** — Slide 3 lista TODOS vermelhos com dedup por
  parent_indicator (Estagnadas qty + % ativas = 1 indicador).
- **Prazo timezone fix** — Slide 5 normalizacao de `due_date` ClickUp:
  handle ambos formatos (str YYYY-MM-DD + int/str ms epoch +1h offset).
- **Dedup slug** — funcoes Cobertura/Concentracao deduplicam por slug em vez
  de string raw — resolve "Vinícius Rissi" vs "Vinicius Rissi" e "Waleska "
  vs "Waleska".
- **Agente `material-generator.md`** com link explicito para
  `card-apresentacao-schema.md` em "Regras criticas" item 0.
- **Skill `recording-decisions/SKILL.md`** sem mudancas estruturais (escopo
  mantido — proxima sessao avalia integracao com campos novos pos-ata S19).

### Fixed

- **ISSUE #3 KNOWN_ISSUES.md projecting-results** (double-count receita)
  workaround aplicado via `Card.apresentacao.projection_overrides` metodo
  `a-fix` em S19 Consorcios (rodada 7.7).

## [3.3.1] - 2026-05-05

### Added
- **Special-case `meta=0` + `direction: menor_melhor`** documentado em `slide-structure.md` §12 Regra de cor 3-tier:
  - `realizado == 0` → `pct = 100%` → `.good` (verde — meta zero atingida)
  - `realizado >= 1` → `pct = 0%` → `.bad` (vermelho — qualquer valor >0 é desvio)
- Aplicável quando `oportunidades_sem_atividade_planejada_funil[_seg]` tem `metas_ppi.qty: 0` (Cards CON v2.5.1+, SEG WL v2.11.1+, SEG RE v1.3.1+).

### Changed
- Agente `material-generator` (slide-structure §Slide 3 Matriz e §Dashboard) atualiza fórmula para incluir special-case meta=0.

## [3.3.0] - 2026-05-05

> **Minor release retrocompativel** — `oportunidades_sem_atividade_planejada_funil[_seg]` agora aparece tambem na Matriz consolidada (Slide 3) e no Dashboard de cada especialista (Slide N por especialista) como linha de PPI · Indicadores de Funil. Lista detalhada (Slide Análise) ganha coluna responsável (assessor OU especialista label).

### Added

- **Indicador na Matriz/Dashboard como PPI de Funil** — Cards CON v2.5.0+, SEG WL v2.11.0+, SEG RE v1.3.0+ declaram `papel: ppi_funil` para `oportunidades_sem_atividade_planejada_funil[_seg]` e adicionam entrada `metas_ppi.{indicador}.qty: pendente` (com `direction: menor_melhor`). Indicador agora aparece como linha PPI tanto no Slide 3 (Matriz consolidada) quanto no Slide N (Dashboard por especialista) com sub-label "Meta pendente" e dot/cor cinza no semáforo (regra de meta ausente).
- **Coluna responsável na lista do Slide Análise** — cada `<li>` da `.deal-list` ganha layout 2-linhas:
  - Linha 1: `<div class="dl-name">{nome_deal}</div>`
  - Linha 2: `<div class="dl-meta"><span class="dl-resp">{assessor_ou_esp}</span><span class="dl-stage">{estagio}</span></div>`
- **Lógica do responsável**: agente lê campo `assessor` do canonical JSON (`nivel='Detalhe'`):
  - `assessor` populado → renderiza nome do assessor em texto normal.
  - `assessor` null/vazio (carteira do próprio especialista) → renderiza `{especialista} (esp)` em italic muted (classe `.dl-resp.esp`).
- **CSS atualizado** em `ritual.tmpl.html`:
  - `.summary-card.list .deal-list li` agora `display: flex; flex-direction: column` (2 linhas)
  - `.dl-meta` com `display: flex; justify-content: space-between` para responsável + estágio
  - `.dl-resp.esp` com `font-style: italic; color: var(--vc-400)` para distinguir
  - `max-height` do card aumentado de 280px → 320px para acomodar 2 linhas por deal

### Changed

- **`slide-structure.md` §Slide N+1 Análise → side card 5** documenta layout 2-linhas com ASCII art e regras de renderização.
- **`material-generator.md` Fase 2 step 5b** atualiza HTML structure e adiciona spec da lógica `assessor` vs `especialista (esp)`.
- **Cards `kpi_references[oportunidades_sem_atividade_*]`**: campo `papel` mudado de `contexto` (CON) para `ppi_funil` (paridade com SEG WL/RE).

### Migration notes

- Cards CON v2.5.0+, SEG WL v2.11.0+, SEG RE v1.3.0+ já refletem o novo padrão.
- Indicador `oportunidades_sem_atividade_planejada_funil[_seg]` permanece em `status: draft` enquanto `metas_ppi.qty: pendente`. Promove para `validated` após 3-6 ciclos de baseline e definição de threshold com coordenador.
- Para o card lateral (lista) renderizar com responsável real, o canonical JSON precisa ter campo `assessor` populado nas linhas `nivel='Detalhe'` — já está garantido pelo script Python via `enrich_deals_funil()` (existente desde v3.1.0).
- Verticais sem o indicador (INV, CRE, UNI) continuam degradando graciosamente — linha PPI não aparece na Matriz/Dashboard, card lateral pulado.

## [3.2.0] - 2026-05-04 (noite)

> **Minor release retrocompativel** — Card Projecao do Slide Pipeline EXPANDIDO de 2 bars para 6 bars. Renderiza Receita E Volume × (Realizado MTD + Proj. mes corrente + Proj. mes seguinte). Reativa leitura de `projection-by-especialista.json` (suprimida desde v1.13). Depende de m7-controle >= 6.2.0 (novo metodo `installment_amortization` resolvendo KNOWN_ISSUES #1).

### Added

- **Variante CSS `.proj-section`** com `.proj-section-title` (uppercase muted) e divider dashed entre sections — duas sections (Receita + Volume) cabem dentro do mesmo card lateral.
- **Classe `.confidence-low`** aplicada em `.proj-row` quando `confianca == "low"` ou `projecao_mes_seguinte` ausente — italic muted no `.v` para sinalizar incerteza.
- **Placeholders `{{ESP_PROJECAO_RECEITA_BARS}}` e `{{ESP_PROJECAO_VOLUME_BARS}}`** no template — agente preenche cada um com 3 `.proj-row` consecutivos (Realizado MTD + Proj. {MES_CORR} + Proj. {MES_SEG}).
- **Render dinâmico do Card Projecao** baseado em `Card.kpi_references[].projecao.obrigatoria`:
  - 2 sections × 3 bars (default CON/SEG WL/SEG RE após Cards v2.4.0/2.10.0/1.2.0)
  - 1 section × 3 bars (quando só uma das métricas é obrigatória)
  - sem card (raro — só se ambas tem obrigatoria=false)

### Changed

- **`{{ESP_PROJECAO_BARS}}` (placeholder único v3.1.0)** REMOVIDO — substituído por dois placeholders separados: `{{ESP_PROJECAO_RECEITA_BARS}}` e `{{ESP_PROJECAO_VOLUME_BARS}}`. Breaking change visual mas degrada graciosamente em deck antigo.
- **`{{ESP_PROJECAO_TITULO}}` REMOVIDO** — substituído pelos titles dentro de cada `.proj-section`.
- **`PROJECAO_ESPECIALISTA_PATH` REATIVADO** no agent material-generator — agente agora DEVE ler `{cycle_folder}/analise/projection-by-especialista.json` (era ignorado desde v1.13 por KNOWN_ISSUES.md ISSUE #1, agora resolvido em m7-controle 6.2.0).
- **Lógica de classificação `{{ESP_PROJECAO_LABEL}}`** consolidada — pega o pior dos dois (Receita ou Volume): se Receita=Provável e Volume=Improvável, label = Improvável.
- **`slide-structure.md` §Slide N+2 Pipeline** documenta nova estrutura visual do card com ASCII art e contrato JSON da fonte de dados.

### Removed

- Lógica antiga de escolha de cenário por `card.projecao.metodo` (run-rate, wl-atual, consorcios-atual, pipeline-conversion) — agora o agente apenas LÊ o JSON gerado por E5 e renderiza. A escolha de método vive no Card/Indicador (consumido por E5).

### Migration notes

- Cards CON v2.4.0, SEG WL v2.10.0, SEG RE v1.2.0 já referenciam novos métodos via `metodo_preferido: installment_amortization` (Receita) e `metodo_preferido: pipeline_conversion_extended` (Volume).
- Para o Card Projeção renderizar com dados reais, m7-controle E5 precisa rodar v6.2.0+. Cycles antigos (5.4.0/6.1.0) renderizam Card com bars vazias e classe `.confidence-low` — degradação graciosa, não bloqueia o deck.
- Verticais sem o método novo configurado (INV, CRE, UNI) caem em fallback `run_rate_linear` ou não renderizam o Card Projeção (quando `obrigatoria=false`).

## [3.1.0] - 2026-05-04

> **Minor release retrocompativel** — substitui o placeholder do card "Oportunidades sem Atividade Planejada" por implementacao real consumindo o novo indicador `oportunidades_sem_atividade_planejada_funil[_seg]` (modo Detalhe). Apresenta LISTA "NOME | Estagio" no Slide Analise. Inclui correcao critica para Cons (filtro por nome de estagio em STAGES_ATIVO em vez de semantic_id, evitando 'fake closed' stages).

### Added

- **Variante CSS `.summary-card.list`** com classe `.deal-list` (UL) — cada item mostra `.dl-name` (nome do deal, max 28 chars com ellipsis) + `.dl-stage` (estagio em uppercase pequeno, classe `.late` se `dias_sem_atividade > 14`). Header `.sh` com `.sh-count` exibindo total de deals em vermelho. `.more-note` para "+N restantes" quando lista tem mais de 5 itens.
- **Render real do summary-card "Sem atividade planejada"** no Slide Analise por especialista — agente le indicador `oportunidades_sem_atividade_planejada_funil[_seg]` do canonical JSON (filtro `nivel='Detalhe'` + `especialista=ESP_NOME`), ordena por `dias_sem_atividade DESC`, renderiza top 5 com nome_deal + estagio.
- **Degradacao graciosa**: se Card nao tem o indicador em `kpi_references[]` (verticais nao-migradas), o agente PULA o card silenciosamente. Sem placeholder, sem feature flag.

### Changed

- **agent material-generator** Fase 2 step 5b — atualizada lista de summary-cards. Card 5 era placeholder gated por flag, agora e LIST real.
- **slide-structure.md §Slide N+1 Analise** documenta variante LISTA com filtros canonicos por vertical (SEG: STAGE_SEMANTIC_ID='P' incluindo On Hold; CON: whitelist STAGES_ATIVO por nome).

### Removed

- Feature flag `feature_sem_atividade_planejada` — implementacao real disponivel, flag descontinuada.
- Placeholder `<div class="summary-card placeholder">Investigar fonte</div>` — substituido por LISTA real ou null (skip silencioso).

### Migration notes

- Cards CON N3 (v2.2.0+), SEG WL N3 (v2.8.0+), SEG RE N3 (v1.0.0+) ganharam o indicador `oportunidades_sem_atividade_planejada_funil[_seg]` em `kpi_references[]` e `indicadores_criados[]` na mesma janela (2026-05-04).
- Pipeline G2.2 E2 precisa rodar uma vez para popular o canonical JSON com a entrada de Detalhe antes do primeiro ritual usar o card.
- Verticais sem o indicador (INV, CRE, UNI) renderizam apenas 4 summary-cards no Slide Analise (sem regressao visual — layout da rank-side comporta).

## [3.0.0] - 2026-05-04

> **Major release — breaking change visual.** Migracao do deck HTML para template editorial M7-2026 (handoff Claude Design). Single-file autocontido com fontes TWKEverett embedadas em base64. Briefing MD/HTML A4 inalterados. Compatibilidade com Cards v2.0 e fluxo legado v1.0 preservada.

### Added

- **Novo template editorial** (`templates/ritual.tmpl.html`) baseado em `<deck-stage>` web component (1920×1080, fonte TWKEverett, 5 weights via `@font-face` base64). CSS unificado com `m7-tokens.css` + `deck.css` + slide-specific helpers inline.
- **Asset bundle inline** (`templates/assets/`) com 5 arquivos `.b64` de fontes TWKEverett (Ultralight/Light/Regular/Medium/Bold), 2 logos M7 (offwhite + dark) e `deck-stage.js` literal. Agente injeta via placeholders `{{ASSET_FONT_*_B64}}`, `{{ASSET_LOGO_*_B64}}`, `{{ASSET_DECK_STAGE_JS}}`. Resulta em deck único portátil de ~1.5-2MB.
- **Slide Consolidado N3 (NOVO, posição `6 + 3*N`)** — sempre gerado: 3 KPI tiles N3 + barras de Receita por direto (vs meta) + Top 3 riscos + Sinais positivos. Quando N=1, omite "Receita por direto" trivial.
- **Summary card "Assessores com opp criada no mês"** no Slide Análise — derivado do canonical JSON `oportunidades_criadas_funil_*` agrupando `responsavel_id` distinct no mês.
- **Summary card "Oportunidades sem atividade planejada"** no Slide Análise — atrás de feature flag `feature_sem_atividade_planejada` (default off, render placeholder "Investigar fonte" enquanto fonte Bitrix24 não confirmada). Campos candidatos a investigar: `ACTIVITY_DEADLINE` ausente, `UF_CRM_*` de próxima atividade.
- **Indicador Estagnadas refatorado (TODO-MIGRACAO Item 5)** — render no Slide 3 (Matriz) e Slide Dashboard com `% das ativas` (semáforo) como linha principal + `qty + R$ + dias` em sublabels. Lê entrada derivada `oportunidades_estagnadas_funil_*_pct_ativas` do canonical JSON quando presente; fallback render legado (qty como semáforo) para Cards sem `pct_ativas_max` ou ciclos antigos.
- **Meta N2 individual no Dashboard (TODO-MIGRACAO Item 6)** — agente lê `n2.{especialista}.meta` do canonical JSON quando Cards declaram `metas_ppi.{indicador}.por_especialista` (ex: SEG WL com Claudia=18 ativas / Tarcísio=15 ativas). Fallback meta N1 agregada quando ausente.
- **Bars duplas Won/Lose** na coluna "Fechadas" do ranking por assessor (Slide Análise) — `<div class="mini dual">` com `.fb-won` (verde) + `.fb-lose` (vermelho) lado a lado. Fonte: `taxa_conversao_funil_*` (Bitrix won/lose).
- **Linhas verticais escurecidas** entre rcells do ranking (Slide Análise) — `border-left: 1px solid var(--vc-100)` (substitui `--vc-50` legado).
- **Card Projeção contextual** (Slide Pipeline) — agente lê `Card.projecao.metodo` para escolher cenário: `run-rate`, `wl-atual`, `consorcios-atual`, `pipeline-conversion`. Label classifica `provável`/`possível`/`improvável` por % atingimento projetado.
- **Gold standard exemplo autocontido** (`examples/ritual-deck-validado.example.html`, ~1.2MB) gerado a partir do `Ritual N3 Seguros - S18.html` do handoff com fontes/logos/JS inlineados.

### Changed

- **Fórmula de slides:** `total_slides = 7 + 3 × N` (era `5 + 4*N + 1`). Estrutura: 5 fixos pré (Capa/Agenda/Matriz/PA Status/PA Vencendo) + 3 por especialista (Dashboard/Análise/Pipeline) + 2 fixos pós (Consolidado/Encerramento). Removido o slide histórico "Agenda Especialista" (transição) — avatar de iniciais no header sinaliza visualmente a troca.
- **Composição de tempo da Agenda:** default `T = 25 + 15*N` min (`T_VISAO=8 + T_OPERACAO=10 + 15*N + T_SINTESE=4 + T_FECHAMENTO=3`). Era `10 + 25*N + 5`. Gatekeeper SSoT #12 atualizado.
- **Cabeçalhos da Matriz** (Slide 3): `KPI - Resultado` → **`KPI · Indicadores de Resultado`**; `PPI - Resultado` → **`PPI · Indicadores de Funil`**. Leitura canônica da seção PPI: "O que preciso ter no meu funil para atingir minhas metas de KPI?"
- **Coluna Total da Matriz** = soma das colunas anteriores (era N1 bruto). Diferença vs N1 bruto vai para callout/sublabel quando relevante.
- **Sem dot semáforo na Matriz** — coloração reside no `.num` via classe `.cell.{good|warn|bad|mute}` (regra 3-tier sobre o valor de Realizado). Cor amarela `#d18000`/`var(--warning)` adicionada para faixa intermediária 70-99,9%.
- **Stat emoji preservado** apenas no Slide Dashboard por especialista (coluna stat 🟢🟡🔴⚪) como exceção visual da Matriz.
- **Card de Riscos no Dashboard** posicionado à direita (leitura horizontal `1.4fr 1fr`), não embaixo da tabela.
- **Coluna "vs Sem. Ant." → "Δ vs S{prev}"** no Dashboard, com seta cinza literal + valor colorido por sentido.
- **Gatekeeper SSoT #10** atualizado: `count(briefing.decisoes) == count(deck.slide_encerramento.next_cards)` — slide Encerramento é o último (posição `7 + 3*N`), era posição 10 fixa.
- **Plugin version** bump para `3.0.0` (breaking change visual). marketplace.json sincronizado.
- **slide-structure.md reescrito** (~750 linhas) refletindo nova estrutura editorial.
- **material-generator.md atualizado** (Fase 2 completa reescrita com novo fluxo, Fase 4 com nova fórmula e checks).
- **SKILL.md** com fórmula e exit criteria atualizados.

### Removed

- Slide histórico "Agenda Especialista" (transição entre blocos por especialista) — não existe mais. O avatar de iniciais (`<div class="avatar">XX</div>`) no header dos 3 slides do bloco substitui o sinalizador visual de troca.
- Card Projeção SUPRIMIDO da v1.13 — REINTRODUZIDO em v3.0 com método contextual (`run-rate`, `wl-atual`, `consorcios-atual`, `pipeline-conversion`).
- Iframes `srcdoc` para cada slide-wrapper — substituídos por `<section data-label>` filhos diretos de `<deck-stage>`.

### Migration notes

- Cards de Performance ainda em v2.0 da `briefing_customization` continuam funcionando — apenas o deck visual muda (template independente de versão de briefing).
- Verticais com `pct_ativas_max` ausente nas `metas_ppi` caem no fallback legado da Estagnadas (qty como semáforo principal). CON N3 e SEG WL N3 já têm o campo desde 2026-05-04.
- Verticais sem `por_especialista` no `metas_ppi` caem no fallback meta N1 agregada para o Dashboard. SEG WL é o caso piloto com metas N2 divergentes.
- Briefings MD/HTML A4 não mudam — estrutura das 5 seções e checklist 14 itens preservados.
- ClickUp como SSoT do Plano de Ação (Slides 4 e 5) com filtros canônicos preservados.

## [2.1.0] - 2026-04-30

> **Minor release retrocompativel** — adiciona capacidade generica de suporte a verticais multi-subnivel (split em N cards com `metadata.subnivel` distinto) sem breaking change para verticais sem split. Caso piloto: SEG WL/RE.

### Added

- **Argumento opcional `[subnivel]`** nos commands `/m7-ritual-gestao:prepare-ritual` e `/m7-ritual-gestao:record-decisions` — `argument-hint: <vertical> [subnivel]`. Exigido quando a vertical tem 2+ cards com `metadata.subnivel` distinto; ignorado (com warning) quando a vertical tem card unico.
- **Logica generica data-driven** de deteccao de split (Step 1.5 dos commands; Fase 1.0 das skills): `Glob('cards/{Vertical}/card_*.yaml')` → ler `metadata.subnivel` de cada → conjunto com 2+ valores distintos dispara modo split. **Nenhuma vertical hardcoded** no codigo. Qualquer vertical futura que ganhe split em multiplos cards (ex: CON tradicional/imobiliario, INV b2b/b2c) e absorvida automaticamente desde que cada card declare `metadata.subnivel`, `ritual.subarea`, `apresentacao.responsaveis[]` proprio e `briefing_customization.versao: "2.0"`.
- **OUTPUT_DIR sufixado por subnivel** quando ativo: `{cycle_folder}/output/{vertical}-{subnivel}/` (ex: `Seguros/2026-04-30/output/seguros-wl/`). Quando ausente: `{cycle_folder}/output/{vertical}/` (path historico preservado byte-equal).
- **CICLO.md G2.3 com sufixo dinamico** quando split detectado: linhas `E2 wl`, `E3 wl`, `E5 wl` + `E2 re`, `E3 re`, `E5 re` (em vez das 3 linhas unicas E2/E3/E5). Verticais sem split: 3 linhas como hoje.
- **`SUBNIVEL` como input dos agents `material-generator` e `decision-recorder`** — string quando split, `null` quando single-card. Agents recebem `card_path` e `output_dir` ja resolvidos pela skill upstream — nao decidem qual card processar.
- **Cleanup de refs CSV legacy em `commands/record-decisions.md`** — removidos stubs antigos (`plano-de-acao.csv`, `03-implementacao/`) que ficaram para tras na rewriting v2.0.0 (skill ja usa ClickUp MCP). Argument-hint, descricao e Steps atualizados para o fluxo MCP.
- **`MAPA_ESPECIALISTA_SEG` ampliado** em `01-Metas/Biblioteca-de-Indicadores/scripts/m7_extract_utils.py`: adicionados `Emmanuel Martins: []` e `Samuel Sinval: []` (carteira individual sem squad fixo — empty list = no zero-injection, comportamento correto da `reaggregate_hierarchy`).
- **Documentacao do pattern multi-subnivel** em `slide-structure.md` §6 (tabela comparativa `n2_expandido` vs multi-subnivel; pre-requisitos de cards futuros) e §7 (caso extremo `Vertical com 2+ cards split`).
- **Adendo em `migration-v2.md` §1** sobre deteccao de versao por card individual em verticais multi-subnivel — cards distintos podem estar em versoes diferentes; cada ritual e processado independentemente.

### Changed

- **Card SEG-RE promovido** (`02-Controle/Cards-de-Performance/Seguros/card_seg_re_n3_001.yaml`):
  - `metadata.version: "0.1.0" → "1.0.0"`
  - `metadata.status: draft → active`
  - `briefing_customization.versao: "0.1" → "2.0"` (estrutura sempre foi v2.0 — `"0.1"` era marcador de clone-versioning que confundia o detector do material-generator, fazendo o ritual cair em fluxo legado por engano)
- **`preparing-materials/SKILL.md`** Fase 1.0 nova (resolver subnivel + filtrar card antes de qualquer outra fase). Fase 1 agora le APENAS o card unico filtrado — nunca merge multi-card. Fase 2 OUTPUT_DIR parametrizado. Fase 5 CICLO.md com sufixo dinamico.
- **`recording-decisions/SKILL.md`** Fase 0 nova (analoga a 1.0 da preparing-materials). Todas as refs a `output/{vertical}/ata*` substituidas por `{OUTPUT_DIR}` resolvido na Fase 0.
- **`material-generator.md`** e **`decision-recorder.md`** ganham linha `SUBNIVEL` na tabela de inputs e secao explicita de inputs recebidos da skill. Anti-patterns ampliados: nunca merge multi-card, nunca hardcode de vertical/subnivel, nunca salvar em `output/{vertical}/` quando subnivel ativo.

### Compatibility

- **Verticais sem split (CON, INV, CRE, UNI)**: comportamento atual preservado byte-equal. `subnivel` ausente → path historico (`output/{vertical}/`) e CICLO.md sem sufixo (`E2`, `E5`).
- **m7-controle**: nenhuma mudanca exigida (G2.2 ja era vertical-driven via `Glob('cards/{vertical}/*.yaml')` e scripts de coleta agregam por `ASSIGNED_BY_ID` independente de quantos cards existam). Versao continua `>= 6.0.0`.
- **Helper `resolve_ritual_path.py`**: ja era generico (consome `Card.ritual.subarea`); nenhuma mudanca.
- **Snapshots de ciclos antigos** (`< 2026-04-30`) sem CICLO.md sufixado: a skill detecta linha `E2`/`E5` legacy e atualiza in-place quando vertical e single-card; em verticais que ganharem split posterior, a primeira execucao apos o split adiciona as linhas sufixadas sem remover as legacy.

### Reference

- `commands/prepare-ritual.md` (Step 1.5 novo + OUTPUT_DIR parametrizado + sufixo CICLO.md)
- `commands/record-decisions.md` (Step 1.5 + cleanup CSV + redirecionamento ClickUp MCP)
- `skills/preparing-materials/SKILL.md` (Fase 1.0 nova + Fase 2 OUTPUT_DIR + Fase 5 sufixo)
- `skills/recording-decisions/SKILL.md` (Fase 0 nova + paths atualizados)
- `agents/material-generator.md` (input SUBNIVEL + Fase 1 nota de card unico + anti-patterns)
- `agents/decision-recorder.md` (input SUBNIVEL + Fluxo de Dados + Localizacao de Arquivos + secao "Sobre subnivel")
- `skills/preparing-materials/references/slide-structure.md` (§6 nova subsecao + §7 casos extremos)
- `skills/preparing-materials/references/migration-v2.md` (§1 adendo verticais multi-subnivel)

---

## [2.0.0] - 2026-04-30

> **Major release** — multiplas mudancas breaking que invalidam workflows do `1.x`.
> Atualizar `m7-controle` para `>= 6.0.0` na mesma janela (cadeia G2.2 → G2.3 mudou).

### Added

- **Replicacao automatica para `03-Rituais/`** (regra v1.13):
  - Helper `skills/preparing-materials/scripts/resolve_ritual_path.py` resolve `RITUAL_DIR = {RITUAIS_BASE_DIR}/{Vertical}/{Cadencia}/[{SubArea}/]{Periodo}/`
  - `Cadencia` lida de `Card.ritual.cadencia` (`N3-Semanal` ou `N2-Mensal`); fallback inferido do nivel
  - `SubArea` opcional (ex: SEG `WholeLife`); ausente → omite subpasta
  - `Periodo`: ISO week `YYYY-S{NN}` para semanal, `YYYY-MM` para mensal
  - Material-generator (Fase 5 nova) copia `Apresentacao/`, `Briefing/`, cria `Ata/` vazia. Preserva `Ata/` e `dados/` em re-runs
  - **Gatekeeper #15 (novo)** — bloqueia publicacao se replicacao falhar (byte-equal vs staging)
- **Slide 5 (Plano de Acao) e Slide 4 (Status PA) consomem JSON ClickUp**:
  - Novos inputs ao agent: `CLICKUP_TASKS_PATH` (`{cycle_folder}/dados/raw/clickup-tasks-{vertical}.json`) e `ACTION_REPORT_PATH` (`analise/action-report.md`)
  - Filtros canonicos ja aplicados em E2 Fase 1.5: `Vertical` (custom field id `a7c7bc7c-...`), `Responsavel Externo` (id `e44c8cff-...`), `parent == null`
  - Tabela usa `name` original do ClickUp + `responsavel_externo` (NAO `assignees[]`) + `url` clicavel
- **Slide 9 — duas regras visuais novas**:
  - Stage breakdown preferido (`oportunidades_ativas_funil_*.data[].estagio`) com fallback aging buckets
  - 6 metricas obrigatorias no card superior (Deals Ativos, Volume Ativo, Ticket Medio, Estagnadas, Squad com opp, Conversao)
- **Slide 8 — separacao squad+especialista / fora do squad** com divisor visual e cores diferenciadas (regra v1.10/v1.13)
- **Slide 10 — estrutura de decisao com 5 campos** (`titulo` + `formato/owner/prazo/consq` em vez de `DESC` unico): cards 280px auto-fit, fallback para D≠3
- **Cards SEG e CON ganham bloco `ritual:`** (`cadencia: N3-Semanal`, `subarea: WholeLife` para SEG)
- **Cards SEG e CON ganham bloco `pipeline_stages:`** com IDs Bitrix canonicos (SEG: 5 stages ativos; CON: 6 stages ativos) — single source of truth do funil

### Changed

- **`recording-decisions` reescrita inteira** (CSV → ClickUp MCP):
  - `clickup_create_task` em vez de append no CSV
  - `clickup_update_task` em vez de Edit no CSV
  - `clickup_create_task_comment` em vez de campo `comentarios` JSON inline (timeline append-only nativa)
  - Detecao de duplicatas via snapshot JSON + `clickup_filter_tasks` (em vez de Grep no CSV)
  - Custom fields canonicos preenchidos automaticamente: `Vertical` + `Responsavel Externo` + `indicador_impactado` + `origem` + `receita_impacto` + `volume_impacto`
  - Mapeamento prioridade ata → ClickUp `priority` (1-4): critica=1, alta=2, media=3, baixa=4
  - Fase 5.6 nova: replicacao para `RITUAL_DIR/Ata/` (coerencia com material-generator)
  - Agent `decision-recorder` ganha 8 ClickUp MCP tools no frontmatter
- **Coluna "Desvio" do Slide 7** com formato `sinal + delta + (% do delta)` colorido por sentido (`maior_melhor` / `menor_melhor`); pp para ratios
- **Card "Fechadas" do Slide 8** usa `taxa_conversao_funil_*` (Bitrix won/lose) em vez de `quantidade_*_mensal` (ClickHouse) — coerencia com taxa de conversao do Slide 3/7

### Removed / Deprecated

- **Card Projecao do Slide 9 SUPRIMIDO** (regra v1.13) — somente 2 cards laterais (Destaque + Estagnacao). Razao: metodologia de projecao de receita ainda nao confiavel (`projecting-results/KNOWN_ISSUES.md` ISSUE #1). Spec preservado para reativacao futura.
- **Input `PROJECAO_ESPECIALISTA_PATH` ignorado** enquanto Card Projecao estiver suprimido. JSON pode existir em `analise/projection-by-especialista.json` mas nao deve ser lido para renderizacao.
- **`plano-de-acao.csv` descontinuado** como SoT em todos os pontos: pre-requisitos, fluxo de dados, prompt de delegacao, anti-patterns
- **`references/csv-schema.md` marcado DEPRECATED** — preservado como referencia historica
- **`templates/acao-template.tmpl.csv` marcado DEPRECATED**

### Breaking Changes

1. **ClickUp MCP virou dependencia mandatory** — sem ele, `recording-decisions` aborta. Verificar `desempenho/.claude/settings.local.json` permissions.
2. **Placeholders do Slide 10 mudaram** — `{{DECISAO_x_DESC}}` removido, substituido por `{{DECISAO_x_FORMATO}}` + `{{DECISAO_x_OWNER}}` + `{{DECISAO_x_PRAZO}}` + `{{DECISAO_x_CONSQ}}`. Templates externos que dependiam do schema antigo quebram.
3. **Outputs em `03-Rituais/` viraram obrigatorios** (gatekeeper #15 bloqueia). Workflow human-facing mudou: gestor consulta `03-Rituais/{V}/{Cad}/[{Sub}/]{Periodo}/`, nao mais `02-Controle/.../output/`.
4. **`recording-decisions` nao escreve mais em CSV** — todas as escritas vao via MCP. Decisoes do ritual aparecem live no ClickUp e sao lidas pelo proximo ciclo via E2 Fase 1.5.
5. **Cards de Performance precisam de bloco `ritual:`** (`cadencia` + opcional `subarea`) para `resolve_ritual_path.py` funcionar deterministicamente; sem ele, fallback heuristico baseado em `metadata.nivel`.

### Reference

- `references/slide-structure.md` (regra v1.13 — supressao Card Projecao + nova ordem de cards laterais)
- `references/clickup-actions-schema.md` (NOVO — substitui csv-schema.md)
- `references/prioritization-rules.md` (atualizado — fonte JSON snapshot + clickup_filter_tasks)
- `agents/material-generator.md` (Fase 5 nova replicacao 03-Rituais)
- `agents/decision-recorder.md` (reescrita — 274 → 402 linhas)

### Compatibility

- **m7-controle requerido**: `>= 6.0.0` (Fase 1.5 ClickUp MCP em E2 deve estar disponivel)
- **Cards de Performance**: bloco `ritual:` recomendado (sem ele, helper cai em fallback)
- **Snapshots de ciclos antigos** (`< 2026-04-30`) sem `clickup-tasks-{vertical}.json` exigem re-rodar E2 Fase 1.5 antes de gerar deck/briefing/ata

---

## [1.9.0] - 2026-04-29

### Added
- **Slide 7 (Dashboard) — coluna "vs Sem. Ant." nas tabelas KPI/PPI** por especialista, mostrando variacao semana-sobre-semana logo apos a coluna "Desvio":
  - **Seta literal cinza** (`#424135`) representa direcao do valor: `↑` se subiu, `↓` se caiu, `→` se sem variacao
  - **Valor absoluto colorido** representa julgamento por sentido do indicador (`direction` em `Card.metas_ppi[*]`):
    - `maior_melhor` + Δ > 0 → valor verde (`#4CAF50`); Δ < 0 → vermelho (`#E40014`)
    - `menor_melhor` + Δ > 0 → vermelho; Δ < 0 → verde
    - Sem variacao → cinza neutro
  - Formato do valor: BRL compacto (`R$ 2,8M`), unidade direta para count/inteiro, **pontos percentuais (pp)** para %
  - **Auto-discovery do ciclo anterior**: novo input `PREV_WBR_PATH` resolvido pelo agent via glob nas pastas-irmas da vertical (`{Vertical}/YYYY-MM-DD/wbr/...`); pega o ciclo imediatamente anterior por data
  - **Edge cases**: primeiro ciclo da vertical (sem `PREV_WBR_PATH`), indicador novo, indicador renomeado, ou Realizado nulo → celula vazia (sem invencao de dado)
  - Widths atualizados: `26 / 14 / 14 / 18 / 18 / 10` (= 100%)
  - **Escopo restrito**: APENAS Slide 7 (Dashboard de cada especialista). Slides 3, 8, 9 e briefings nao recebem coluna WoW

### Changed
- `material-generator.md`: novas Fases 1.7 (localizar WBR anterior) e 1.8 (mapear sentido + calcular variacao WoW). Passo 4a da Fase 2 referencia o dicionario `var_semana_por_indicador` na renderizacao do Dashboard
- `slide-structure.md`: Secao "Slide 7 — Dashboard" expandida com tabela de regras de seta/cor por sentido, formato do delta por unidade, exemplos de leitura
- `SKILL.md`: `PREV_WBR_PATH` adicionado a Fase 2 (Resolver caminhos) com nota explicativa; prompt da Fase 3 inclui instrucao de resolucao automatica
- Log de execucao do CICLO.md agora registra o `basename(PREV_WBR_PATH)` ou `null (primeiro ciclo)`

### Notes
- Cards sem `direction` em `metas_ppi[indicator_id]` caem no default `maior_melhor` com warning no log — sinaliza necessidade de atualizar o Card via `/m7-controle:configuring-cards`
- Briefings (MD e HTML A4) ficam byte-equivalentes ao baseline — coluna WoW nao se aplica a eles

## [1.8.0] - 2026-04-29

> **Cross-plugin dependency:** o Card Projecao (mini-graficos no Slide 9) depende de **m7-controle ≥ v5.5.0** (que gera `projection-by-especialista.json`). Para rituais com `m7-controle v5.4.x` ou anterior, o card mostra valor agregado N1 com nota de fallback.
>
> **Nota de nomenclatura:** "especialista" nesta documentacao se refere a Douglas/Tereza/Claudia/Tarcisio (N3 na hierarquia oficial M7). Coordenador (Joel) e N2.
>
> **Tratamento de N2 no schema atual:** Joel e tratado como **ator transversal** — tem deals proprios (`ASSIGNED_BY_ID = Joel`) mas NAO e modelado como agregador dos N3 abaixo dele. Por isso, deals do Joel aparecem na coluna `Sem Especialista` do Slide 3, junto com bridge gaps. Modelagem como agregador hierarquico fica fora de escopo — manter logica transversal por enquanto.
>
> Schemas legacy podem usar `N2-Especialista` por historia — renomeacao do schema esta fora de escopo desta versao.

### Added
- **Slide 8 (Analise) — proprio especialista incluido nas barras** quando responsavel direto:
  - Deals com `ASSIGNED_BY_ID = especialista` E `assessor (UF_CRM)` vazio passam a aparecer como uma barra propria com label `Nome do Especialista (especialista)` em italic muted (cor padrao `#424135`)
  - Antes: esses deals contavam no Slide 3 mas sumiam do Slide 8 (gap silencioso)
  - **Identidade contabil obrigatoria**: `Σ qty barras Slide 8 = valor da coluna do especialista no Slide 3` (e idem para volume) — agente bloqueia publicacao se reconciliar nao bater
  - Aplica para os 4 cards: Ativas, Criadas, Fechadas, Estagnadas
- **Slide 9 (Funil Pipeline) — mesma regra**: funil agrega TODOS os deals com `ASSIGNED_BY_ID = especialista`, independente de assessor preenchido
  - **Identidade contabil obrigatoria**: `Σ qty estagios funil = qty ativas do especialista no Slide 3`; idem para volume
  - Cards "Destaque" e "Estagnacao" podem citar deals do especialista direto nominalmente, sufixando `(deal direto)` em italic muted quando relevante (ex: "Icoforte (deal direto, 172d)")
  - Antes: funil podia filtrar por squad inadvertidamente, escondendo deals diretos do especialista
- **Slide 3 (Matriz) — nova estrutura de colunas canonica** com `Sem Especialista` explicito e `M7 Total` calculado por construcao:
  - Estrutura: `Indicador | Sem Especialista | Esp1 | Esp2 | ... | EspN | M7 Total`
  - Identidade contabil obrigatoria: `M7 Total = Sem Especialista + Σ Esp_i` (soma das colunas, nao N1 bruto do banco)
  - Coluna "Sem Especialista" expoe o gap de bridge (deals com ASSIGNED_BY_ID nao mapeado para nenhum especialista)
  - Suporta N variavel (1 a M+ especialistas) com larguras adaptativas; quebra em 2 slides (3a + 3b) quando N+3 ≥ 8 colunas
- **Slide 9 (Funil) — Card Projecao com mini-graficos V/R por especialista**:
  - 2 mini-graficos compactos (~200×80 px): Volume + Receita
  - Cada um com 3 barras (`MTD`, `Mes`, `Mes+1`) e linha pontilhada de meta
  - Cor da barra "Mes" reflete classificacao de probabilidade: Provavel=verde / Possivel=amarelo / Improvavel=vermelho
  - Fonte: novo input `PROJECAO_ESPECIALISTA_PATH` = `{cycle_folder}/analise/projection-by-especialista.json` (gerado por m7-controle E5 Fase 6.5, v5.5.0+)
  - Fallback graceful: se JSON nao existir, exibir N1 agregado com nota
- **`metas_ppi` no Card de Performance** — bloco no nivel do card com metas iguais aplicadas a todos os especialistas N2 da vertical. Estrutura por `indicator_id`:
  - Sub-campos: `qty` (int), `volume` (BRL), `ticket_medio` (BRL), `valor` (numero generico), `direction` (`maior_melhor` / `menor_melhor`), `nota` (string opcional)
  - Suporta `valor: pendente` para metas aguardando dados externos
  - Aplicado em CON (`card_con_n3_001.yaml`) e SEG (`card_seg_n3_001.yaml`)
- **Slide 3 (Matriz) com 6 linhas PPI canonicas** definidas dinamicamente do Card:
  - Contratos Fechados (qty), Opps. Ativas (qty), Volume Opps. Ativas (R$), Ticket Medio Ativas (R$), Opps. Criadas (qty), Opps. Estagnadas (qty + sub-label R$ vol + dias media)
  - Plus KPIs principais (Volume, Receita, Taxa Conversao) ja com meta no Card
- **Calculo de % atingimento + semaforo** (regra a — universal):
  - `maior_melhor`: `(realizado / meta) × 100`
  - `menor_melhor` (estagnadas): `(meta / max(realizado, 1)) × 100` cap 200%
  - Threshold: ≥100% verde / 70-99% amarelo / <70% vermelho / pendente cinza
  - **Sem pacing** — semaforo compara realizado direto contra meta mensal cheia
- **Slide 9 — ordem canonica dos 3 cards laterais alterada**: Destaque → Estagnacao → Projecao (era Estagnacao → Projecao → Destaque)
- **Suporte a Cards de Performance v2.0 (estrutura aberta)** na skill `preparing-materials`: deteccao automatica de `briefing_customization.versao` e bifurcacao de fluxo (v2.0 com filtros / v1.0 legado)
- **Filtros v2.0 no agente `material-generator`** (Fase 1.5):
  - Armadilhas: incluir familia apenas se `sinal_generico_no_wbr` casa com algo no WBR atual
  - Decisoes: incluir familia apenas se `contexto_tipico` casa com WBR ou Recomendacoes
  - Provocacoes sempre instanciadas (varia o interlocutor + dado do ciclo)
- **Variante HTML A4 imprimivel do briefing** (`templates/ritual-briefing.tmpl.html`): CSS embarcado com classes `.disclaimer`, `.section-title`, `.subsection-title`, `.question-block`, `.trap-block`, `.decision-block`, `.roteiro-block`. Paleta M7-2026, fonte twkEverett, page A4 com margens 24mm/20mm, max-width 750px
- **Diretorio `examples/`** com 3 gold standards validados em ritual real (CON N3 S18, 2026-04-27): `ritual-deck-validado.example.html`, `ritual-briefing-validado.example.md`, `ritual-briefing-validado.example.html`. Agente compara estruturalmente contra estes exemplos antes de finalizar
- **3 gatekeepers SSoT briefing↔slide** (Fase 4.5 do agente, Phase 4 do SKILL.md) — falha BLOQUEIA publicacao:
  - Item 7: cada `Sinal no WBR` das armadilhas aparece literalmente no WBR
  - Item 10: numero D de decisoes no briefing == numero D de cards no Slide 10 (mesmos titulos)
  - Item 12: total de minutos do Roteiro == total da Agenda no Slide 2 (composicao 10 + 25*N + 5)
- **Nova reference `migration-v2.md`** com pseudocodigo dos filtros v2.0, especificacao dos 3 gatekeepers, spot-check de SSoT (3 valores), comparacao com `examples/`, anti-patterns v2.0 e roadmap de retrocompatibilidade
- 14-item checklist de auditoria do briefing aplicado pelo agente antes de salvar (3 SSoT + 11 secundarios)
- Logging da `versao_briefing` detectada no CICLO.md por execucao

### Changed
- **Templates substituidos** pelos validados institucionalmente:
  - `templates/ritual.tmpl.html` (deck): novo template `Apresentacao-Ritual-N.html` com 10 slides base + bloco repetivel N especialistas, regex de placeholder simples `\{\{([A-Z_0-9.+]+)\}\}`, coluna M7 (Total) opcional, renumeracao sequencial 1..N obrigatoria
  - `templates/ritual-briefing.tmpl.md` (briefing MD): novo template alinhado a estrutura aberta v2.0, placeholders nominais por interlocutor/armadilha/decisao/especialista
- **`references/briefing-structure.md`** reescrito (391 → 362 linhas): filosofia v2.0 aberta, mapeamento Card→briefing por campo, sistema de placeholders MD+HTML A4, 14-item checklist com 3 SSoT marcados
- **`references/slide-structure.md`** reescrito (422 → 555 linhas): arquitetura 10+N×4 detalhada, regras de Slide 3 (coluna N3 = soma especialistas, coluna M7 opcional), Slide 4 (layout adaptativo + recalculo dasharrays), Slide 6 (N+2 cards), Slide 8 (split visual barras <30%, ordenacao A-Z mesma em todos cards, sem limite de barras), Slide 9 (formula interpolacao linear de cores), Slide 10 (cards = decisoes do briefing), bridge/typos comuns CH↔Bitrix, auditoria final
- **`SKILL.md`** workflow atualizado:
  - Fase 1: deteccao de versao do `briefing_customization`
  - Fase 4: 3 gatekeepers SSoT + comparacao estrutural com `examples/`
  - Exit criteria: produzir `.md` E `.html` do briefing em Cards v2.0
- **`agents/material-generator.md`** estendido:
  - Fase 1.5 nova com pseudocodigo de filtros v2.0
  - Fase 3 com geracao da variante HTML A4
  - Fase 4 reorganizada em 7 sub-fases (existencia, estrutura, CSS compliance, spot-check SSoT, gatekeepers SSoT, comparacao com examples/, checklist 14 itens)
  - Tabela de inputs declara explicitamente outputs MD + HTML A4
  - 5 anti-patterns novos relacionados a v2.0 e SSoT
  - 6 metricas de qualidade novas (HTML A4 gerado, 3 gatekeepers, 2 filtros)

### Migration notes

Cards M7 atualmente em `briefing_customization.versao: "2.0"`: SEG, CON, INV (todos os 5: N1, N2, 3× N3). Cards de outras verticais migrados gradualmente — a skill mantem retrocompatibilidade v1.0 ate todos os Cards estarem migrados (estimativa: 8 semanas).

Rollout sequencial sugerido: CON primeiro (gold standard existe), SEG segundo, INV depois.

## [1.7.2] - 2026-04-06

### Fixed
- Removed invalid `skills` and `agents` declarations from plugin.json that used bare names instead of paths, breaking Claude's component auto-discovery

## [1.7.1] - 2026-04-01

### Added
- **Acesso ao JSON consolidado do m7-controle** (`DADOS_PATH`): O material-generator agora pode ler `dados-consolidados-{vertical}.json` para quebras granulares por assessor (N5), equipe (N3) e squad (N4) nos slides Analise e Projecao
- Fontes de dados formalizadas no `slide-structure.md` para cada tipo de slide (Painel vs JSON vs WBR narrativo)
- Fallback graceful: se JSON indisponivel, usa WBR narrativo (comportamento anterior)

### Fixed
- Font sizes das barras divergentes no slide Analise: 7px → 8px (respeitando minimo absoluto)

## [1.7.0] - 2026-04-01

### Added
- **Regras CSS Obrigatorias no material-generator**: Paleta de cores exaustiva (15 tokens), escala tipografica (min 8px), espacamento grid 4px, validacao grep pos-geracao
- **Indicadores derivados do Card**: Slide 2 (Matriz) e Dashboards agora derivam indicadores de `kpi_references[]` do Card via Secao 1.5 do WBR (contrato com m7-controle v5.3.0)
- Secao "Valores CSS Mandatorios" no `slide-structure.md` com allowlist e tabela de mapeamento
- 8 novos anti-patterns no material-generator (CSS compliance, indicadores dinamicos)
- 6 novas metricas de qualidade (font compliance, cores on-brand, indicadores = Card)
- 4 validacoes CSS nos exit criteria da skill `preparing-materials`

### Changed
- **Fluxo invertido**: Fase 1 agora localiza Card ANTES do WBR (Card define estrutura, WBR fornece dados)
- **Template HTML corrigido**: Fontes maiores (meta 6→8px, body 9→10px), cores 100% on-brand M7-2026, `font-weight: bold` → numerico, `line-height: 1.4` em todos os slides, lime como badge (nao texto) na agenda
- **Indicadores nao mais hardcoded**: `slide-structure.md` referencia `kpi_references[]` do Card em vez de listar indicadores fixos
- Status colors atualizados para M7-2026 (`#3498DB`→`#3B82F6`, `#E74C3C`→`#e40014`, `#27AE60`→`#4CAF50`, `#BDC3C7`→`#aeada8`)

### Fixed
- Cores fora da paleta M7-2026 no template (`#2C3E50`, `#D0D0D0`, `#BDBDBD`, `#F0F0F0`, `#F5F5F5`, `#9E9E9E` etc.)
- Lime (`#eef77c`) usado como texto sobre fundo claro (contraste ~1.1:1 → agora como badge)
- Legenda "Sem meta" usava `#E0E0E0`/`#BDBDBD` → corrigido para `#d0d0cc`/`#aeada8`
- `.action-num` com texto branco sobre lime → corrigido para `#424135`

## [1.6.0] - 2026-04-01

### Added
- Geracao de PDF visual para ata de ritual (M7-2026 design system, Score A)
- Template HTML `ata-ritual.tmpl.html` com CSS identico ao WBR narrativo (TWK Everett, verde caqui, lime, off-white)
- Script `html-to-pdf.js` (Puppeteer ^22) para conversao HTML → PDF autocontido
- Referencia `ata-html-guide.md` com mapeamento de componentes (timeline, badges, KPI cards, callouts)
- Fase 5.5 no workflow de `recording-decisions` (gerar HTML e PDF apos registro no CSV)
- Exit criteria para HTML e PDF na skill `recording-decisions`

### Changed
- Agent `decision-recorder` agora inclui `Bash` nos tools (necessario para executar Puppeteer)
- Fluxo de dados atualizado: 3 artefatos de saida (MD + HTML + PDF) em vez de 1
- Regra de escopo do agent atualizada: Bash restrito a `html-to-pdf.js` e `npm install`

## [1.5.0] - 2026-03-31

### Added
- Command `record-decisions`: atalho direto para executar G2.3 E5 (registro de decisoes pos-ritual) sem precisar percorrer o pipeline sequencial via `/next`

## [1.4.0] - 2026-03-31

### Changed
- Removidas colunas YTD da Matriz de Visao Geral (Slide 2): de 7 colunas para 4 (Indicador + N3 + Esp1 + Esp2)
- Apresentacao agora exibe apenas resultados do mes corrente
- Cores dos headers da matriz unificadas em tons de verde-caqui (#424135 → #4f4e3c → #5f5e4c)

### Removed
- Colunas YTD (Year-to-Date) do template HTML e da referencia de slides
- Placeholder `{{periodo_ytd_label}}` do template
- Classes CSS `.ytd`, `.ytd-n`, `.ytd-e1`, `.ytd-e2` do template HTML

## [1.3.1] - 2026-03-30

### Fixed
- Migrar design tokens de M7-Navy (legado) para M7-2026 (oficial)
- Cores: #1E3A5F → #424135, #FAF9F6 → #fffdef, #C9A962 → #eef77c, #E46962 → #e40014
- Fonte: Arial → "twkEverett", Arial, sans-serif
- Headings: weight bold → 400 (autoridade por tamanho conforme brandbook M7)
- Borders: #E5E5E5 → #d0d0cc (verde-caqui-100)
- Aplicado em: slide-structure.md, ritual.tmpl.html, material-generator.md

## [1.3.0] - 2026-03-30

### Changed
- **BREAKING**: Output de PPTX para HTML autocontido (elimina python-pptx e m7_pptx_lib.py)
- **BREAKING**: Estrutura de slides refatorada de "por KPI" para "por especialista"
- Cada especialista do Card recebe bloco de 3-4 slides (Dashboard, Analise, Projecao, Sugestoes PPI condicional)
- Slide Sugestoes PPI e condicional — gerado apenas se WBR contem dados de sugestoes
- Agendas de transicao entre blocos de especialistas
- Novos slides fixos: Visao Geral (Matriz 7 colunas), Status Plano de Acao (donut + barras), Plano de Acao (tabela)

### Added
- Template `ritual.tmpl.html` — estrutura HTML autocontida com iframes por slide
- Paleta de cores do ritual documentada em `slide-structure.md` (navy #1E3A5F, gold #C9A962, off-white #FAF9F6)

### Removed
- Template `ritual-pptx-script.tmpl.py` (obsoleto — PPTX substituido por HTML)
- Dependencia de `python-pptx` e `m7_pptx_lib.py` (m7-apresentacoes)
- Dependencia de assets/logos externos

## [1.2.0] - 2026-03-30

### Changed
- **BREAKING**: Briefing refatorado de "mini-WBR" para "guia do consultor"
- Nova estrutura: Veredicto (3 frases) + O Que Provocar (perguntas por interlocutor) + Armadilhas da Reuniao + Decisoes Binarias + Roteiro com Intencao
- Briefing nao repete dados do WBR — traduz dados em perguntas, armadilhas e decisoes acionaveis
- Template `ritual-briefing.tmpl.md` atualizado com novos placeholders
- `material-generator` Fase 4 reescrita com novo fluxo de geracao
- Metricas de qualidade atualizadas: "Nao aceite" em 100% das perguntas, decisoes binarias, sem repeticao de dados

## [1.1.0] - 2026-03-30

### Added
- Integracao com Cards de Performance (YAML) como prerequisito de ambas as skills
- Ambos os agents (material-generator, decision-recorder) agora leem o card da vertical antes de executar
- Card fornece: responsaveis/especialistas, KPIs com criterios de desvio critico, logica de analise (7 passos), correlacoes entre indicadores

### Changed
- Fase 1 de `preparing-materials` agora localiza e passa CARD_PATH ao agent
- Fase 1 de `recording-decisions` agora le o card para contexto organizacional antes de solicitar notas
- `material-generator` enriquece briefing com correlacoes e foco do destinatario do card
- `decision-recorder` valida `indicador_impactado` contra KPIs reais do card e sugere responsaveis

## [1.0.0] - 2026-03-30

### Added
- Skill `preparing-materials` (G2.3-E2): gera PPTX + Briefing MD a partir do WBR
- Skill `recording-decisions` (G2.3-E5): registra decisoes pos-ritual em ata + CSV
- Agent `material-generator`: transforma WBR em materiais visuais (sonnet)
- Agent `decision-recorder`: formaliza notas do ritual em ata + plano-de-acao.csv (sonnet)
- Command `prepare-ritual`: gera materiais pre-ritual para uma vertical
- Command `next`: avanca pipeline G2.3 para proxima fase pendente
- Command `status`: exibe progresso do ciclo G2.3
- References: `slide-structure.md`, `briefing-structure.md`, `csv-schema.md`, `prioritization-rules.md`
- Templates: `ritual-briefing.tmpl.md`, `ritual-pptx-script.tmpl.py`, `ata-ritual.tmpl.md`, `acao-template.tmpl.csv`
- Documentacao E3 (distribuicao manual) em pipeline e commands
- Suporte a 5 verticais: investimentos, credito, universo, seguros, consorcios
