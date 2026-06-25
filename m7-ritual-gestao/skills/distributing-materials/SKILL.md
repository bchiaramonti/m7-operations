---
name: distributing-materials
description: >-
  G2.3-E3 (pre-ritual) e E5.7 (pos-ritual): distribui materiais ao Gestor e
  participantes via DM Slack usando bot dedicado `m7-desempenho`. Le destinatarios
  do Calendario-de-Rituais.xlsx (User IDs), abre DM via `conversations.open`, faz
  upload 3-step de apresentacao+briefing HTML (pre) ou ata.pdf+apresentacao.html+ata.md (pos), e
  registra entrega em `distribuicao-log.csv` (dataset CP-04). Aderente a
  MAN-PERF-003 RN-06..09 + INS-PERF-002 v2.1 Passos 11-13 + INS-PERF-004 v2.0
  Passos 4-6. Modo dual: `pre_ritual` (apos E2) e `post_ritual` (apos E5 commit).
  Sempre 2-fase (preview -> aprovacao humana -> commit) para gatekeeper RN-06.

  <example>
  Context: E2 concluido, materiais validados, hora de distribuir
  user: "/m7-ritual-gestao:approve-ritual consorcios"
  assistant: Invoca a skill em mode=pre_ritual preview, exibe destinatarios + assunto + corpo da mensagem, aguarda aprovacao do usuario, depois roda mode=pre_ritual commit que faz upload e envia via slack_send.py
  </example>

  <example>
  Context: E5 concluido (ata + ClickUp tasks), hora de distribuir a ata
  user: "/m7-ritual-gestao:approve-ata consorcios"
  assistant: Invoca a skill em mode=post_ritual preview com a ata gerada + lista de contramedidas + (se existir) a apresentacao do ritual, aguarda aprovacao, depois commit que faz upload da ata.pdf + apresentacao.html no canal/DMs (Gestor + participantes + lider direto se escalacao)
  </example>
user-invocable: false
---

# Distributing Materials — Distribuicao via Bot Slack (E3 + E5.7)

> "Material que nao chega ao Gestor no prazo nao existe."

Esta skill automatiza a entrega de materiais do ritual via DMs Slack do bot `m7-desempenho`,
substituindo a etapa manual de E3 (envio pre-ritual) e adicionando o sub-passo final de
E5 (envio da ata pos-ritual). **Sempre opera em 2 fases** (preview -> commit) para honrar
RN-06 (validacao humana antes de distribuir).

---

## Modos de Execucao

| Modo | Quando | O que envia | Para quem |
|------|--------|-------------|-----------|
| `pre_ritual` | Apos E2 concluido | apresentacao.html + briefing.html | Gestor + participantes |
| `post_ritual` | Apos E5 commit ClickUp | ata.pdf + apresentacao.html (se existir, 3.8.2+) + ata.md (opcional) | Gestor + participantes + lider direto (se escalacao) |

Cada modo opera em **2 fases**:

| Fase | Faz | NAO faz |
|------|-----|---------|
| `preview` | Renderiza mensagem, resolve destinatarios, valida conteudo (RN-07), retorna sumario para o command exibir ao usuario | Nenhuma chamada Slack, nenhum log gravado |
| `commit` | Faz upload, envia DMs, escreve `distribuicao-log.csv`, atualiza CICLO.md | Nada a planejar — plano congelado do preview |

---

## Dependencias Internas

| Recurso | Caminho | Tipo |
|---------|---------|------|
| Citacoes literais dos normativos | [references/normative-anchors.md](references/normative-anchors.md) | Referencia |
| Schema do Calendario-de-Rituais.xlsx | [references/calendar-schema.md](references/calendar-schema.md) | Referencia |
| Regras dos templates de mensagem | [references/message-templates.md](references/message-templates.md) | Referencia |
| Schema CICLO.md G2.3 extension | [references/ciclo-md-schema-extension.md](references/ciclo-md-schema-extension.md) | Referencia |
| Schema delivery-log CSV (CP-04) | [references/delivery-log-schema.md](references/delivery-log-schema.md) | Referencia |
| Template mensagem pre-ritual | [templates/pre-ritual-message.tmpl.md](templates/pre-ritual-message.tmpl.md) | Template |
| Template mensagem pos-ritual | [templates/post-ritual-message.tmpl.md](templates/post-ritual-message.tmpl.md) | Template |
| Mensagem renderizada (Cons N3 exemplo) | [examples/sample-pre-ritual-message.md](examples/sample-pre-ritual-message.md) | Exemplo |
| Linha exemplo do delivery-log | [examples/sample-delivery-log-entry.json](examples/sample-delivery-log-entry.json) | Exemplo |
| Helper de path canonico 03-Rituais/ | [../preparing-materials/scripts/resolve_ritual_path.py](../preparing-materials/scripts/resolve_ritual_path.py) | Script compartilhado |
| **Orquestrador unico** (preview/commit + ISO week + validate RN-07 + render mensagem) | [scripts/slack_send.py](scripts/slack_send.py) | Script principal |
| **Resolver destinatarios** (XLSX, CLI standalone para debug) | [scripts/resolve_recipients.py](scripts/resolve_recipients.py) | Script |
| Dependencias Python | [scripts/requirements.txt](scripts/requirements.txt) | Manifest |

---

## Dependencias Externas

- **Bot Slack `m7-desempenho`** (bot_id=B0B4UM99VB4, workspace M7=T033RBSMRNX) com scopes `chat:write, files:write, users:read, im:write`
- **Token `SLACK_BOT_TOKEN`** em `~/.claude/credentials/.env` ou env var (carregado por `slack_send.py` via `python-dotenv`)
- **Calendario-de-Rituais.xlsx** em `desempenho/03-Rituais/Calendario-de-Rituais.xlsx` com colunas estendidas (ver `calendar-schema.md`)
- **Pacotes Python:** `slack-sdk>=3.27`, `python-dotenv>=1.0`, `openpyxl>=3.1`, `requests>=2.31`, `pyyaml>=6.0`

---

## Pre-requisitos (Entry Criteria)

### Modo `pre_ritual`

- [ ] CICLO.md da vertical existe e tem secao G2.3
- [ ] Linha `E2{FASE_SUFIXO}` esta com `status: concluido`
- [ ] Artefatos gerados em `output/{OUTPUT_SUBDIR}/`:
  - `ritual-{vertical}-{data}.html` (apresentacao)
  - `briefing-{vertical}-{data}.html` (briefing A4)
- [ ] Calendario-de-Rituais.xlsx tem linha para a vertical+nivel com `Gestor-User-ID` + `Participantes-User-IDs` preenchidos
- [ ] WBR data JSON disponivel em `wbr/wbr-{vertical}-{data}.data.json` (para validacao RN-07 e bullets executivos)
- [ ] `SLACK_BOT_TOKEN` carregavel (env var ou `.env`)

### Modo `post_ritual`

- [ ] Linha `E5{FASE_SUFIXO}` esta com `status: concluido` no CICLO.md
- [ ] Ata gerada em `{RITUAL_DIR}/ata/ata-ritual-{vertical}-{data}.pdf` (+ `.md` opcional)
- [ ] `plan-preview.json` da E5 disponivel (para extrair scope_task_ids da ata)
- [ ] (Opcional, 3.8.2+) Deck do ritual em `{RITUAL_DIR}/apresentacao/ritual-{vertical}-{data}.html` — anexado quando presente, ignorado quando ausente
- [ ] Mesmo Calendario + token requirements

Se qualquer criterio falhar: interromper e reportar ao usuario com mensagem clara.

---

## Workflow

### Fase 0 — Resolver subnivel e filtrar Card

> **Regra:** algoritmo identico ao da skill `preparing-materials` Fase 1.0 (data-driven, 4 casos A/B/C/D).
> Manter sincronizado.

1. Receber `vertical` (obrigatorio), `subnivel` (opcional), `mode` (`pre_ritual` ou `post_ritual`).
2. Listar cards via `Glob('{CARDS_DIR}/{Vertical}/card_*.yaml')` (ignorar `_Historico/`).
3. Particionar em `cards_consolidados` (sem subnivel) e `cards_split` (com subnivel).
4. **Decidir** modo de selecao (Caso A/B/C/D — ver `preparing-materials/SKILL.md` Fase 1.0 para detalhes).
5. Armazenar `CARD_PATH` e `SUBNIVEL_ATIVO`.

### Fase 1 — Carregar contexto

1. Read Card em `CARD_PATH`. Extrair:
   - `metadata.nivel` (N1/N2/N3)
   - `metadata.subnivel` (string ou None)
   - `metadata.vertical_display` (ex: "Consorcios" -> usado no subject)
   - `apresentacao.responsaveis[]` (lista de especialistas — usado em bullets)
2. Read WBR data JSON em `wbr-{vertical}-{data}.data.json`. Extrair:
   - `semaforo_resumo` (verde/amarelo/vermelho/cinza_sem_meta/total)
   - `indicadores` dict (label, status, pct_label, gap_label, causa_raiz_resumo)
   - `meta.checkpoint_label` (ex: "Maio 2026, semana 4 (MTD)")
3. Read `clickup-tasks-{vertical}.json` em `dados/raw/` (se disponivel). Extrair:
   - Total de tasks em escopo do ritual
   - Distribuicao por status (em_dia / atrasada / critica)
4. **Modo `post_ritual` adicional:** Read ata MD em `output/{OUTPUT_SUBDIR}/ata-ritual-{vertical}-{data}.md`. Extrair:
   - Lista de decisoes (D-001..D-NNN)
   - `scope_task_ids` (IDs ClickUp criados ou atualizados)
   - Flag de escalacao (se `escalacao_acionada: true` no YAML block)

### Fase 2 — Validar conteudo (RN-07)

`slack_send.py` invoca internamente `validate_rn07()` (funcao consolidada — antes script standalone). Verifica os 4 elementos de RN-07:

1. **Visao geral metas vs. realizado** — WBR tem indicadores com `meta` + `realizado`
2. **Desvios >5%** — pelo menos 1 indicador com `|gap_pct| > 5%`
3. **Status de contramedidas abertas** — clickup-tasks JSON nao vazio OU explicitamente "0 acoes"
4. **Tendencia MoM** — Card v2.0 tem `briefing_customization` com filtros `sinal_no_wbr`/`contexto_tipico` (proxy de tendencia)

Se algum dos 4 falhar: **abortar fase preview** com diagnostico — usuario deve corrigir o WBR/ata antes de tentar de novo.

### Fase 3 — Resolver destinatarios

`slack_send.py` importa `resolve_recipients` como modulo (mantido como script separado para permitir debug standalone via CLI). Args efetivos:
- `--calendar-path desempenho/03-Rituais/Calendario-de-Rituais.xlsx`
- `--vertical {vertical}`
- `--nivel N{nivel}`
- `--subnivel {SUBNIVEL_ATIVO ou ""}`
- `--include-escalacao true/false` (true so em modo `post_ritual` com flag `escalacao_acionada`)

Helper retorna JSON:
```json
{
  "gestor": {"name": "Joel Freitas", "user_id": "U06RSGEH51R"},
  "participantes": [
    {"name": "Douglas Silva", "user_id": "U0A0AE52Q07"},
    {"name": "Tereza Cristina", "user_id": "U098F2S4GG4"},
    {"name": "Sara Caetano", "user_id": "U05HEK3N7RN"}
  ],
  "lider_direto": {"name": "Bruno Chiaramonti", "user_id": "U043D1ZF69L"}
}
```

Se Calendario nao tem linha para `vertical+nivel`: **abortar** com `"Vertical {vertical} nivel N{nivel} nao encontrada no Calendario-de-Rituais.xlsx. Pedro deve estender com colunas Gestor-User-ID e Participantes-User-IDs."`.

### Fase 4 — Renderizar mensagem

`slack_send.py` invoca internamente `render_message()` (funcao consolidada — antes script standalone). Args efetivos:
- `--mode {pre_ritual|post_ritual}`
- `--vertical {vertical}`
- `--nivel N{nivel}`
- `--subnivel {SUBNIVEL_ATIVO ou ""}`
- `--ciclo-date {YYYY-MM-DD}`
- `--wbr-data-json {path}`
- `--clickup-tasks-json {path ou ""}`
- `--ata-md-path {path ou ""}` (so em post_ritual)
- `--template-dir {SKILL_DIR}/templates/`

Funcoes internas:
1. Calcula `subject` via `build_subject()` (consolidado — antes `iso_week.py`):
   - Pre: `Ritual {Vertical} N{NIVEL} S{NN}` (ex: `Ritual Consorcios N3 S21`)
   - Pos: `Ata Ritual {Vertical} N{NIVEL} S{NN}` (ex: `Ata Ritual Consorcios N3 S21`)
2. Le template (`pre-ritual-message.tmpl.md` ou `post-ritual-message.tmpl.md`)
3. Substitui placeholders com dados do WBR + Card + ClickUp + ata
4. Retorna JSON `{ subject, body, attachments[] }`

### Fase 5 — Preview (gate humano)

Em modo `preview`:
1. Empacotar JSON com:
   - `subject`, `body`, `attachments` (paths absolutos), `recipients` (gestor+participantes+lider_direto), `delivery_meta` (ciclo, prazo_referencia D-1/D-3, on_time bool)
2. Salvar em `output/{OUTPUT_SUBDIR}/distribution-preview-{mode}.json`
3. Retornar para o command exibir ao usuario via stdout estruturado

**Nenhuma chamada Slack ocorre em preview.** Nenhuma linha no `distribuicao-log.csv`.

### Fase 6 — Commit (envio real)

Em modo `commit`:
1. Read `distribution-preview-{mode}.json` (congelado do preview)
2. Validar que arquivo nao tem mais de 24h (warn caso contrario — estado pode ter mudado)
3. Chamar `scripts/slack_send.py` com `--preview-path {arquivo}`
4. Script faz:
   - `auth_test` (sanity)
   - Para cada user_id da lista (gestor + participantes + lider_direto): `conversations.open(users=U)` -> obtem DM channel
   - Para cada anexo: `files_getUploadURLExternal` + PUT binario + colectar file_id
   - Para cada DM: `files_completeUploadExternal(files=[...], channel_id=DM, initial_comment=body)`
5. Coletar `ts` retornado de cada envio
6. Escrever linha no `desempenho/03-Rituais/distribuicao-log.csv` (CP-04 dataset)
7. Atualizar CICLO.md G2.3 (linha E3 ou sub-campo de E5)
8. Retornar JSON pro stdout: `{status, ts[], dms_count, on_time, escalacao_acionada}`

### Fase 7 — Atualizar CICLO.md

Conforme `references/ciclo-md-schema-extension.md`:

- **Modo `pre_ritual`:** atualizar linha `E3{FASE_SUFIXO}`:
  - `status: concluido`
  - `inicio: {preview_ts}`, `fim: {commit_ts}`
  - `artefato: bot_slack_dm (N destinatarios, on_time=true/false)`
- **Modo `post_ritual`:** adicionar sub-campo na linha `E5{FASE_SUFIXO}` (Log de Execucao):
  - `[{timestamp}] SISTEMA — G2.3 E5{FASE_SUFIXO} sub-passo distribuicao_ata concluido. {N} DMs entregues. Escalacao: {bool}.`

---

## Dry-run

Toda fase commit aceita `--dry-run`:
- Pula auth_test, conversations.open, uploads e completeUploadExternal
- Escreve mock JSON em stdout: `{would_send_to: [...], subject, body_preview, attachments, dry_run: true}`
- Linha no `distribuicao-log.csv` ganha flag `dry_run: true`

Util para Phase 1 dos testes secos (sem mexer em Slack real) e para diagnostico operacional.

---

## Tratamento de erros

| Cenario | Acao |
|---------|------|
| `SLACK_BOT_TOKEN` ausente em commit | Abortar com: `"Token Slack ausente. Defina SLACK_BOT_TOKEN em ~/.claude/credentials/.env ou env var."` |
| Calendario sem linha p/ vertical+nivel | Abortar com instrucao de estender o XLSX |
| Coluna Gestor-User-ID/Participantes-User-IDs vazia | Abortar e listar quais celulas precisa preencher |
| auth_test falha (`invalid_auth`) | Abortar com: `"Token Slack invalido/expirado. Renove em api.slack.com/apps."` |
| conversations.open falha p/ um user | Logar warn, marcar destinatario como `failed_open`, continuar com os outros |
| files.completeUploadExternal falha p/ um DM | Marcar entrega parcial; CICLO.md ganha `entregas_parciais: {N}` |
| Validacao RN-07 falha | Abortar preview, listar quais dos 4 elementos falharam |
| Preview JSON >24h em commit | Warn e perguntar se quer regenerar preview |
| Bot nao tem permissao de DM com user (deactivated/email-only) | `user_not_visible` — pular esse destinatario, registrar no log, alertar usuario |

---

## Critical Rules

1. **2-fase obrigatorio:** `preview` -> aprovacao humana -> `commit`. Pular preview viola RN-06.
2. **Bot abre DM em runtime:** **NUNCA** confiar em `D...` armazenado no calendario. Sempre `conversations.open(users=U...)`.
3. **Canal vs DM por modo:**
   - `pre_ritual`: DMs individuais (gestor + participantes). Bot abre DM via `conversations.open(users=U...)`. Briefing e ferramenta do CONDUTOR — pre_ritual em 2026-05-20+ envia SO ao coordenador/gestor (memory `reference_ritual_dist_recipients_per_mode`).
   - `post_ritual`: post no canal da vertical (`Canal-Vertical-ID` no XLSX). Fallback DMs (gestor + participantes + lider direto se escalacao) apenas quando `Canal-Vertical-ID` vazio. Bot precisa ser membro do canal (memory `reference_slack_bot_canal_membership`).
4. **Subject literal:** `Ritual {Vertical} N{NIVEL} S{NN}` (pre) ou `Ata Ritual {Vertical} N{NIVEL} S{NN}` (pos). ISO week. Sem hifen, sem extra.
5. **Pontualidade (RN-09):** logar `on_time: true` se entrega ate D-1 EOD (N3) ou D-3 (N2). Usado pelo KPI CP-04 ≥90% mensal.
6. **Single source of truth:** mensagem deriva do `wbr-*.data.json` (E6) — nunca do MD/HTML do briefing.
7. **Tokens nao saem do .env:** `slack_send.py` so faz `fingerprint(token)` em logs (`xoxb...len=58`), nunca o token completo.
