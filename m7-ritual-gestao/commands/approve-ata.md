---
description: G2.3-E5 sub-passo de distribuicao — Envia ata (PDF + opcionalmente MD) ao Gestor, participantes e lider direto (se escalacao acionada) via DM Slack do bot m7-desempenho. Cumpre INS-PERF-004 v2.0 Passos 4-6. Opera em 2 fases (preview/commit) para gate humano. Pre-requisito: E5 commit ClickUp concluido (ata gerada).
argument-hint: <vertical> [subnivel]
disable-model-invocation: true
---

# m7-ritual-gestao:approve-ata

Automatiza o sub-passo final de **E5 "Registrar Decisoes"** — a distribuicao da ata gerada (PDF) ao Gestor, participantes e (se houver escalacao) lider direto, via DM Slack do bot `m7-desempenho`.

> **Compliance:** INS-PERF-004 v2.0 Passos 4-6 (envio + validacao 24h + escalacao ao nivel superior). RN-06 (validacao humana) honrado via gate preview/commit.

> **Importante:** isso e um **sub-passo de E5**, nao uma nova fase. A linha E5 do CICLO.md ja deve estar `concluido` (tasks ClickUp criadas). Este command apenas adiciona o envio da ata por DM.

## Input

- **vertical** (obrigatorio): `$ARGUMENTS[0]`.
- **subnivel** (condicional): `$ARGUMENTS[1]`.

Se vertical nao informada, exibir: `"Uso: /m7-ritual-gestao:approve-ata <vertical> [subnivel]"` e parar.

## Steps

### 1. Validar vertical + resolver subnivel/Card

Mesmo padrao do `/approve-ritual` Step 1 (logica generica 4 casos A/B/C/D — sincronizado com `prepare-ritual` Step 1.5).

### 2. Verificar entry criteria

> **Timestamps**: obter via `date '+%Y-%m-%dT%H:%M'`.

1. **Localizar CICLO.md** mais recente da vertical.
2. **Calcular sufixo** `FASE_SUFIXO`.
3. **Verificar linha E5**: `E5{FASE_SUFIXO}` deve estar com `status: concluido` (commit ClickUp ja realizado). Se nao:
   `"E5{FASE_SUFIXO} nao concluida. Execute /m7-ritual-gestao:record-decisions {vertical}{ {sub}} antes."` e parar.
4. **Verificar se ata ja foi distribuida** (procurar no Log de Execucao linha `distribuicao_ata concluido`). Se sim, perguntar `"Ata ja distribuida. Re-enviar (ex: ata corrigida)? [s/n]"`. Se `n`, parar.
5. **Verificar SLACK_BOT_TOKEN** (mesma checagem de `/approve-ritual`).

### 2.5. Resolver `RITUAL_DIR` canonical via helper compartilhado

Mesmo padrao de `/approve-ritual` Step 2.5:

```bash
RITUAL_DIR=$(python3 {plugin_dir}/m7-ritual-gestao/skills/preparing-materials/scripts/resolve_ritual_path.py \
  --base-dir {DESEMPENHO_ROOT}/03-Rituais \
  --vertical {vertical} \
  --ciclo-date {YYYY-MM-DD} \
  --card-path {CARD_PATH})
```

Retorna `03-Rituais/N{N}/{Vertical-cap}[-{subnivel}]/{Cadencia}/{Periodo}/` (level-first, default ON 2026-06-09). Ex: `03-Rituais/N3/Consorcios/Semanal/2026-S21/`, `03-Rituais/N2/PJ2/Mensal/2026-05/`.

### 3. Localizar artefatos E5 no `RITUAL_DIR` canonical

6. **Localizar artefatos E5** em `{RITUAL_DIR}/ata/`:
   - `ata-ritual-{vertical}{-{subnivel}}-{YYYY-MM-DD}.pdf` (obrigatorio — INS-PERF-004 anexo principal)
   - `ata-ritual-{vertical}{-{subnivel}}-{YYYY-MM-DD}.md` (obrigatorio — usado para extrair decisoes + escalacao via regex)
   - Se ata.pdf nao existir: `"Ata PDF ausente em {RITUAL_DIR}/ata/. Re-execute /m7-ritual-gestao:record-decisions para regenerar."` e parar.

6.5. **Localizar deck do ritual (opcional)** em `{RITUAL_DIR}/apresentacao/ritual-{vertical}{-{subnivel}}-{YYYY-MM-DD}.html` (3.8.2+). Se existir, sera anexado junto da ata como referencia historica. Se ausente (vertical nao passou por `/approve-ritual`), seguir sem o deck — apenas registrar warn no log.

7. **Localizar `plan-preview.json`** em `{RITUAL_DIR}/ata/plan-preview.json` (opcional — usado para contagem de novas/atualizadas tasks ClickUp na mensagem).

8. **Localizar WBR data JSON** via helper canonical (RN-08 single source of truth):

   ```bash
   CYCLE_DIR_ABS=$(python3 {plugin_dir}/m7-controle/skills/collecting-data/scripts/resolve_controle_path.py \
     --base-dir {DESEMPENHO_ROOT} \
     --vertical {vertical} \
     --ciclo-date {YYYY-MM-DD} \
     --card-path {CARD_PATH})
   ```
   - WBR data JSON esperado em `{CYCLE_DIR_ABS}/wbr/wbr-{vertical}{-{subnivel}}-{YYYY-MM-DD}.data.json`.
   - Se ausente: erro bloqueante.

9. **Localizar Calendario-de-Rituais.xlsx** em `{DESEMPENHO_ROOT}/03-Rituais/Calendario-de-Rituais.xlsx`.

### 3.5. Resolver `OUTPUT_DIR` do preview

`OUTPUT_DIR = {RITUAL_DIR}/distribuicao/` (subpasta dedicada no canonical).

### 4. Invocar skill em `phase=preview`

```bash
python3 {plugin_dir}/m7-ritual-gestao/skills/distributing-materials/scripts/slack_send.py \
  --phase preview \
  --mode post_ritual \
  --vertical {vertical} \
  --nivel {N_NIVEL} \
  --subnivel {SUBNIVEL_ATIVO_ou_vazio} \
  --ciclo-date {YYYY-MM-DD} \
  --wbr-data-json {WBR_DATA_JSON_PATH} \
  --card-yaml {CARD_PATH} \
  --ata-md-path {RITUAL_DIR}/ata/ata-ritual-{vertical}{-{subnivel}}-{YYYY-MM-DD}.md \
  --ata-pdf-path {RITUAL_DIR}/ata/ata-ritual-{vertical}{-{subnivel}}-{YYYY-MM-DD}.pdf \
  --plan-preview-json {RITUAL_DIR}/ata/plan-preview.json \
  --deck-path {RITUAL_DIR}/apresentacao/ritual-{vertical}{-{subnivel}}-{YYYY-MM-DD}.html \
  --calendar-path {DESEMPENHO_ROOT}/03-Rituais/Calendario-de-Rituais.xlsx \
  --output-dir {RITUAL_DIR}/distribuicao
```

- `--deck-path` (3.8.2+) — sempre informe o path canonical do deck. Se o arquivo existir, sera adicionado aos anexos; se nao existir, e ignorado silenciosamente (skip do deck, ata segue normal).
- `--include-md-anexo` — para incluir tambem a ata em MD como anexo (alguns gestores preferem editar).

### 5. Apresentar preview ao usuario

```
=== Preview de distribuicao pos-ritual (ata) — {Vertical}{ {SUBNIVEL}} ===

Subject: {subject}
Cadencia: {cadencia_label}

Destinatarios ({recipients_count}):
- Gestor: {gestor.name}
- Participantes: {p1.name}, {p2.name}, ...
{ - Lider Direto (escalacao): {lider_direto.name}}

Anexos:
- ata-ritual-{vertical}-{data}.pdf
{ - ritual-{vertical}-{data}.html (apresentacao do ritual)}
{ - ata-ritual-{vertical}-{data}.md}

Decisoes registradas: {n_decisoes}
Contramedidas: {n_novas} novas + {n_atualizadas} atualizadas

Escalacao acionada: {true/false}{ — copia ira ao lider direto}

Corpo da mensagem (preview):
{body_preview}

Aprovar e enviar? [s = commit / n = cancelar / editar = abortar e re-gerar ata]
```

### 6. Decidir conforme resposta

- `s` → Step 7
- `n` → preservar JSON, registrar CICLO.md log: `G2.3 E5{FASE_SUFIXO} sub-passo distribuicao_ata cancelado pelo usuario.`
- `editar` → orientar `"Para corrigir ata: re-execute /m7-ritual-gestao:record-decisions {vertical}{ {sub}} em modo de edicao."` e parar.

### 7. Invocar skill em `phase=commit`

```bash
python3 {plugin_dir}/m7-ritual-gestao/skills/distributing-materials/scripts/slack_send.py \
  --phase commit \
  --mode post_ritual \
  --vertical {vertical} \
  --nivel {N_NIVEL} \
  --subnivel {SUBNIVEL_ATIVO_ou_vazio} \
  --ciclo-date {YYYY-MM-DD} \
  --output-dir {RITUAL_DIR}/distribuicao \
  --preview-path {RITUAL_DIR}/distribuicao/distribution-preview-post_ritual.json \
  --delivery-log-path {DESEMPENHO_ROOT}/03-Rituais/distribuicao-log.csv
```

### 8. Atualizar CICLO.md

Diferente do `/approve-ritual`, **NAO altera a linha E5** (ela ja esta concluida). Apenas append no Log de Execucao + (se aplicavel) Anomalias:

```
[{ts_preview}] SISTEMA — Iniciando G2.3 E5{FASE_SUFIXO} sub-passo distribuicao_ata (distributing-materials) mode=post_ritual
[{ts_commit}] AGENTE:slack_send.py — G2.3 E5{FASE_SUFIXO} distribuicao_ata concluido. {dms_count_ok} DMs entregues. escalacao_acionada={bool}. Subject: {subject}
```

Se houver entregas parciais, registrar Anomalia.

### 9. Exibir resultado final

```
G2.3 E5{FASE_SUFIXO} ata distribuida — {Vertical}{ {SUBNIVEL}} — {YYYY-MM-DD}

Subject: {subject}
DMs entregues: {dms_count_ok}/{total}
Escalacao acionada: {true/false}
On-time (RN-09 {prazo}): {on_time}
Log CP-04: linha adicionada em desempenho/03-Rituais/distribuicao-log.csv

Pipeline G2.3 fechado para {vertical}{ {SUBNIVEL_ATIVO}} nesta semana.
```

## Tratamento de erros

| Cenario | Acao |
|---------|------|
| Vertical nao informada | `"Uso: /m7-ritual-gestao:approve-ata <vertical> [subnivel]"` |
| E5 nao concluida (ClickUp commit faltando) | `"E5{FASE_SUFIXO} nao concluida. Execute /m7-ritual-gestao:record-decisions antes."` |
| Ata PDF/MD ausente | `"Ata ausente. Re-execute /m7-ritual-gestao:record-decisions para regenerar."` |
| SLACK_BOT_TOKEN ausente | Mensagem com instrucao de configurar |
| Validacao RN-07 falha (post_ritual extra: ata sem decisoes/contramedidas/scope_task_ids) | Lista o que falta; usuario corrige a ata e re-tenta |
| Entrega parcial | Status registrado, Anomalia adicionada, sugerir investigar |
| Usuario rejeita preview | Cancela, preserva JSON |

## Modo dry-run

Mesma logica de `/approve-ritual`: `--dry-run` em commit nao chama Slack mas escreve linha de log com `dry_run=true`.

Util na Etapa 6 do roadmap (primeiro ciclo real Seg N3) para validar antes do envio real.
