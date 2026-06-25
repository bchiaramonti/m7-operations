---
description: G2.3-E3 — Distribui materiais pre-ritual (apresentacao + briefing HTML) ao Gestor e participantes via DM Slack do bot m7-desempenho. Opera em 2 fases (preview/commit) para honrar RN-06 (validacao humana). Le destinatarios do Calendario-de-Rituais.xlsx, valida conteudo RN-07, renderiza mensagem e envia via bot.
argument-hint: <vertical> [subnivel]
disable-model-invocation: true
---

# m7-ritual-gestao:approve-ritual

Automatiza a etapa **E3 "Distribuir Materiais ao Gestor"** do processo G2.3 (Rituais de Gestao), distribuindo a apresentacao HTML + briefing HTML via DM Slack para o Gestor da vertical + todos os participantes listados no Calendario-de-Rituais.xlsx.

> **Pre-requisito tecnico:** Token Slack do bot `m7-desempenho` em `~/.claude/credentials/.env` como `SLACK_BOT_TOKEN=xoxb-...`. Plugin: `m7-operations/m7-ritual-gestao`, versao 3.8.0-preview+. Calendario-de-Rituais.xlsx estendido com colunas `Gestor-User-ID`, `Participantes-Nomes`, `Participantes-User-IDs` (ver `skills/distributing-materials/references/calendar-schema.md`).

> **Compliance:** MAN-PERF-003 RN-06 (validacao), RN-07 (conteudo), RN-08 (single source of truth), RN-09 (D-1 semanal / D-3 mensal) + INS-PERF-002 v2.1 Passos 11-13. Pontualidade alimenta KPI CP-04 (≥90% mensal).

## Input

- **vertical** (obrigatorio): `$ARGUMENTS[0]` — vertical a processar. Valores aceitos: `investimentos`, `credito`, `universo`, `seguros`, `consorcios`.
- **subnivel** (condicional): `$ARGUMENTS[1]` — obrigatorio quando a vertical tem 2+ cards com `metadata.subnivel` distinto (ex: SEG `wl`/`re`).

Se vertical nao informada, exibir: `"Uso: /m7-ritual-gestao:approve-ritual <vertical> [subnivel]"` e parar.

## Steps

### 1. Validar vertical + resolver subnivel/Card

Reusar a logica do Step 1.5 de `/m7-ritual-gestao:prepare-ritual` (data-driven, 4 casos A/B/C/D — manter sincronizado). Selecionar `CARD_PATH` unico e `SUBNIVEL_ATIVO` (string ou None).

### 2. Verificar entry criteria

> **Timestamps**: obter `{timestamp}` via `date '+%Y-%m-%dT%H:%M'` no momento exato do registro.

1. **Localizar CICLO.md** da vertical: `Glob('**/CICLO.md')` — selecionar o mais recente.
2. **Calcular sufixo** `FASE_SUFIXO = " {SUBNIVEL_ATIVO}" if SUBNIVEL_ATIVO else ""`.
3. **Verificar linha E2**: `E2{FASE_SUFIXO}` deve estar com `status: concluido`. Se nao:
   `"E2{FASE_SUFIXO} nao concluida. Execute /m7-ritual-gestao:prepare-ritual {vertical}{ {sub}} antes."` e parar.
4. **Verificar linha E3**: se ja `concluido`, perguntar `"E3{FASE_SUFIXO} ja distribuida. Re-enviar? [s/n]"`. Se `n`, parar.
5. **Verificar SLACK_BOT_TOKEN**: checar se carrega de env var ou `~/.claude/credentials/.env`. Se ausente:
   `"SLACK_BOT_TOKEN ausente. Configure em ~/.claude/credentials/.env (SLACK_BOT_TOKEN=xoxb-...) e tente de novo."` e parar.

### 2.5. Resolver `RITUAL_DIR` canonical via helper compartilhado

> **Regra:** os artefatos do ritual (deck, briefing, ata) vivem na estrutura canonical `03-Rituais/`, nao no staging local. Reusar o helper de `preparing-materials`.

```bash
RITUAL_DIR=$(python3 {plugin_dir}/m7-ritual-gestao/skills/preparing-materials/scripts/resolve_ritual_path.py \
  --base-dir {DESEMPENHO_ROOT}/03-Rituais \
  --vertical {vertical} \
  --ciclo-date {YYYY-MM-DD} \
  --card-path {CARD_PATH})
```

O helper le `Card.metadata.{nivel, subnivel}` e resolve: `03-Rituais/N{N}/{Vertical-cap}[-{subnivel}]/{Cadencia}/{Periodo}/` (level-first, default ON 2026-06-09). Exemplos:

| Card | RITUAL_DIR resolvido (level-first) |
|---|---|
| `card_con_n3_001` (nivel=N3, sem subnivel) | `03-Rituais/N3/Consorcios/Semanal/2026-S21/` (5/19 → sem 21) |
| `card_seg_wl_n3_001` (nivel=N3, subnivel=wl) | `03-Rituais/N3/Seguros-wl/Semanal/2026-S22/` (5/27 → sem 22) |
| `card_pj2_n2_001` (nivel=N2, sem subnivel) | `03-Rituais/N2/PJ2/Mensal/2026-05/` |

### 3. Localizar artefatos E2 (no `RITUAL_DIR` canonical, NAO no staging local)

6. **Localizar artefatos E2** em `{RITUAL_DIR}/`:
   - `apresentacao/ritual-{vertical}{-{subnivel}}-{YYYY-MM-DD}.html` (deck — INS-PERF-002 Passo 11 anexo a)
   - `briefing/briefing-{vertical}{-{subnivel}}-{YYYY-MM-DD}.html` (briefing A4 — anexo b)
   - Se algum nao existir: `"Artefato E2 ausente: {path}. Re-execute /m7-ritual-gestao:prepare-ritual {vertical}{ {sub}}."` e parar.

7. **Localizar WBR data JSON** via helper canonical (RN-08 single source of truth — fica em `02-Controle`):

   ```bash
   CYCLE_DIR_ABS=$(python3 {plugin_dir}/m7-controle/skills/collecting-data/scripts/resolve_controle_path.py \
     --base-dir {DESEMPENHO_ROOT} \
     --vertical {vertical} \
     --ciclo-date {YYYY-MM-DD} \
     --card-path {CARD_PATH})
   ```

   - Level-first (default ON 2026-06-09): `02-Controle/N{N}/{Vertical-cap}[-{subnivel}]/{YYYY-MM}/{YYYY-MM-DD}/`
     Ex: `02-Controle/N3/Consorcios/2026-05/2026-05-19/`, `02-Controle/N3/Seguros-wl/2026-05/2026-05-22/`
   - WBR data JSON esperado em `{CYCLE_DIR_ABS}/wbr/wbr-{vertical}{-{subnivel}}-{YYYY-MM-DD}.data.json`
   - Se ausente: `"WBR data JSON nao encontrado. Re-execute /m7-controle:run-weekly antes."` e parar.

8. **Localizar Calendario-de-Rituais.xlsx**: `{DESEMPENHO_ROOT}/03-Rituais/Calendario-de-Rituais.xlsx`. Bloqueante.

9. **Localizar `clickup-tasks-{vertical}.json`** em `{CYCLE_DIR_ABS}/dados/raw/clickup-tasks-{vertical}{-{subnivel}}.json` (opcional — usado pra bullets de PA). `CYCLE_DIR_ABS` ja resolvido em Step 7 com fallback. Se ausente, mensagem renderiza com placeholder.

### 3.5. Resolver `OUTPUT_DIR` do preview

`OUTPUT_DIR = {RITUAL_DIR}/distribuicao/` (subpasta dedicada dentro do RITUAL_DIR canonical — preserva auditoria junto com os artefatos).

### 4. Invocar skill em `phase=preview`

Executar via Bash (paths absolutos derivados de Steps 2.5/3 acima):

```bash
python3 {plugin_dir}/m7-ritual-gestao/skills/distributing-materials/scripts/slack_send.py \
  --phase preview \
  --mode pre_ritual \
  --vertical {vertical} \
  --nivel {N_NIVEL} \
  --subnivel {SUBNIVEL_ATIVO_ou_vazio} \
  --ciclo-date {YYYY-MM-DD} \
  --wbr-data-json {WBR_DATA_JSON_PATH} \
  --card-yaml {CARD_PATH} \
  --clickup-tasks-json {CLICKUP_TASKS_JSON_PATH_ou_vazio} \
  --deck-path {RITUAL_DIR}/apresentacao/ritual-{vertical}{-{subnivel}}-{YYYY-MM-DD}.html \
  --briefing-path {RITUAL_DIR}/briefing/briefing-{vertical}{-{subnivel}}-{YYYY-MM-DD}.html \
  --calendar-path {DESEMPENHO_ROOT}/03-Rituais/Calendario-de-Rituais.xlsx \
  --output-dir {RITUAL_DIR}/distribuicao
```

A saida e um JSON com `subject`, `recipients_count`, `attachments`, `body_preview`, `on_time`.

### 5. Apresentar preview ao usuario (gate humano — RN-06)

Exibir no chat:

```
=== Preview de distribuicao pre-ritual — {Vertical}{ {SUBNIVEL}} ===

Subject: {subject}
Cadencia: {cadencia_label}
Prazo (RN-09): {prazo_referencia} — on_time: {on_time}

Destinatarios ({recipients_count}):
- Gestor: {gestor.name} (DM via bot)
- Participantes:
  - {p1.name} (DM via bot)
  - {p2.name} (DM via bot)
  ...

Anexos:
- {attachment_1}
- {attachment_2}

Corpo da mensagem (preview):
{body_preview}

Aprovar e enviar? [s = commit / n = cancelar / editar = abortar e re-validar artefatos]
```

### 6. Decidir conforme resposta

- `s` → prosseguir para Step 7
- `n` → abortar, exibir `"Distribuicao cancelada. Preview preservado em {OUTPUT_DIR}/distribution-preview-pre_ritual.json para auditoria."` Append CICLO.md Log: `[{timestamp}] SISTEMA — G2.3 E3{FASE_SUFIXO} cancelada pelo usuario.`
- `editar` → exibir orientacao: `"Para alterar conteudo: regenere WBR (E6) ou ajuste Card. Re-execute /m7-ritual-gestao:approve-ritual {vertical}{ {sub}} depois."` e parar.

### 7. Invocar skill em `phase=commit`

```bash
python3 {plugin_dir}/m7-ritual-gestao/skills/distributing-materials/scripts/slack_send.py \
  --phase commit \
  --mode pre_ritual \
  --vertical {vertical} \
  --nivel {N_NIVEL} \
  --subnivel {SUBNIVEL_ATIVO_ou_vazio} \
  --ciclo-date {YYYY-MM-DD} \
  --output-dir {RITUAL_DIR}/distribuicao \
  --preview-path {RITUAL_DIR}/distribuicao/distribution-preview-pre_ritual.json \
  --delivery-log-path {DESEMPENHO_ROOT}/03-Rituais/distribuicao-log.csv
```

A saida JSON contem `dms_count_ok`, `dms_count_fail`, `deliveries[]` (lista de DMs com `ts`), `on_time`, `exec_log`.

### 8. Atualizar CICLO.md

1. **Atualizar linha `E3{FASE_SUFIXO}`** na tabela Progresso:
   - `status: concluido` (ou `parcial` se `dms_count_fail > 0`)
   - `inicio: {ts_preview}`, `fim: {ts_commit}`
   - `artefato: bot_slack_dm ({dms_count_ok}/{total} destinatarios, on_time={on_time}, prazo={prazo_referencia})`
2. **Append Log de Execucao**:
   ```
   [{ts_preview}] SISTEMA — Iniciando G2.3 E3{FASE_SUFIXO} (distributing-materials) mode=pre_ritual
   [{ts_commit}] AGENTE:slack_send.py — G2.3 E3{FASE_SUFIXO} concluido. {dms_count_ok} DMs entregues. Subject: {subject}
   ```
3. **Se falhas parciais**, append Anomalias:
   ```
   [{ts_commit}] SISTEMA — G2.3 E3{FASE_SUFIXO} entregas parciais: {dms_count_fail} falha(s). Detalhes: {lista_de_failures}.
   ```

### 9. Exibir resultado final

```
G2.3 E3{FASE_SUFIXO} distribuida — {Vertical}{ {SUBNIVEL}} — {YYYY-MM-DD}

Subject: {subject}
DMs entregues: {dms_count_ok}/{total}
On-time (RN-09 {prazo}): {on_time}
Log CP-04: linha adicionada em desempenho/03-Rituais/distribuicao-log.csv

Proximo: aguardar o ritual; depois /m7-ritual-gestao:record-decisions {vertical}{ {sub}} → /m7-ritual-gestao:approve-ata {vertical}{ {sub}}.
```

## Tratamento de erros

| Cenario | Acao |
|---------|------|
| Vertical nao informada | `"Uso: /m7-ritual-gestao:approve-ritual <vertical> [subnivel]"` |
| E2 nao concluida | `"E2{FASE_SUFIXO} nao concluida. Execute /m7-ritual-gestao:prepare-ritual antes."` |
| SLACK_BOT_TOKEN ausente | Mensagem com instrucao de configurar `~/.claude/credentials/.env` |
| Calendario sem linha p/ vertical+nivel | Mensagem com instrucao de estender o XLSX (calendar-schema.md) |
| Colunas Slack vazias no XLSX | Lista de celulas a preencher |
| Validacao RN-07 falha | Lista quais dos 4 elementos falharam — usuario corrige WBR antes de re-tentar |
| auth_test falha | `"Token Slack invalido/expirado. Renove em api.slack.com/apps e atualize ~/.claude/credentials/.env."` |
| conversations.open falha p/ um user | Continua com os outros, marca falha parcial |
| Entrega parcial (dms_count_fail > 0) | Status `parcial` no CICLO.md + Anomalia + sugerir investigar usuario faltante |
| Usuario rejeita preview (`n`) | Cancela, preserva JSON, registra CICLO.md log |

## Modo dry-run (para testes)

Para validar fluxo sem enviar de fato (durante setup/QA):

```bash
# Preview normal
python3 .../slack_send.py --phase preview ...

# Commit em dry-run (escreve no log com flag dry_run=true, sem chamar Slack)
python3 .../slack_send.py --phase commit ... --dry-run
```

Util na Etapa 5 do roadmap (primeiro ciclo real Cons N3) caso queira-se simular antes do envio definitivo.
