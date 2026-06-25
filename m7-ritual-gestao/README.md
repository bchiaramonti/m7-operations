# m7-ritual-gestao

> Processo G2.3 — Rituais de Gestao | v3.8.0

Plugin para operacionalizar os rituais semanais de gestao da M7, consumindo o WBR produzido pelo m7-controle (G2.2) e gerando materiais de apoio + registro estruturado de decisoes + **distribuicao automatica via bot Slack** (novo em 3.8.0).

## Pipeline

```
TER 08:00 (materiais pre-ritual)
│
├── E2: preparing-materials  → material-generator → HTML + Briefing
│
└── E3: distributing-materials  → bot Slack m7-desempenho → DMs Gestor + Participantes
        (opt-in via /approve-ritual; gate humano RN-06)

QUA (ritual presencial/virtual)

QUI (registro pos-ritual)
│
└── E5: recording-decisions  → decision-recorder  → Ata MD/HTML/PDF + ClickUp tasks
        + sub-passo distribuicao_ata (opt-in via /approve-ata; INS-PERF-004 Passos 4-6)
```

## Composicao

| Tipo | Qtd | Artefatos |
|------|-----|-----------|
| Skills | 3 | preparing-materials (E2), distributing-materials (E3 + E5.7), recording-decisions (E5) |
| Agents | 2 | material-generator, decision-recorder |
| Commands | 5 | next, status, prepare-ritual, record-decisions, approve-ritual, approve-ata |

## Commands

| Comando | Descricao |
|---------|-----------|
| `/m7-ritual-gestao:prepare-ritual <vertical> [subnivel]` | Gera materiais pre-ritual (HTML + Briefing) |
| `/m7-ritual-gestao:record-decisions <vertical> [subnivel]` | Registra decisoes + cria tasks ClickUp |
| **`/m7-ritual-gestao:approve-ritual <vertical> [subnivel]`** **🆕** | Distribui materiais pre-ritual via bot Slack (E3, gate humano preview/commit) |
| **`/m7-ritual-gestao:approve-ata <vertical> [subnivel]`** **🆕** | Distribui ata via bot Slack (sub-passo de E5, INS-PERF-004) |
| `/m7-ritual-gestao:next [vertical]` | Avanca pipeline G2.3 (E2 → E3 manual → E5; novos commands ainda nao auto-acionados) |
| `/m7-ritual-gestao:status [vertical]` | Exibe progresso do ciclo G2.3 |

> **🆕 3.8.0 (S4 2026-05-20):** `/next` orquestra automaticamente E3 (preview Slack) e
> sub-passo E5.7 (preview distribuicao-ata). Aprovacao explicita ainda via `/approve-ritual`
> e `/approve-ata` (gate humano preview→commit preservado, RN-06).

## Setup do bot Slack (pre-requisito para 3.8.0)

1. Bot `m7-desempenho` criado em api.slack.com/apps com scopes `chat:write, files:write, users:read, im:write`.
2. Token salvo em `~/.claude/credentials/.env` como `SLACK_BOT_TOKEN=xoxb-...`.
3. `Calendario-de-Rituais.xlsx` estendido com colunas `Gestor-User-ID`, `Participantes-Nomes`, `Participantes-User-IDs`, `Lider-Direto-User-ID` (ver `skills/distributing-materials/references/calendar-schema.md`).
4. `pip install -r skills/distributing-materials/scripts/requirements.txt` (slack-sdk, openpyxl, python-dotenv, requests, PyYAML).

## Dependencias externas

| Dependencia | Tipo | Uso |
|-------------|------|-----|
| WBR (output do m7-controle) | Arquivo MD + canonical data JSON | Input principal para materiais (E2) e mensagem Slack (E3/E5.7) |
| Card de Performance | Arquivo YAML | Contexto organizacional (especialistas, KPIs, logica de analise) |
| ClickUp MCP (`pa-resultado` 901326795742) | MCP write | Plano de Acao SoT (E5; substitui plano-de-acao.csv) |
| **Bot Slack `m7-desempenho`** **🆕** | API Slack (slack-sdk) | Distribuicao DM (E3 + E5.7) |
| **Calendario-de-Rituais.xlsx** **🆕** | XLSX estendido | Resolucao de destinatarios por vertical+nivel |

## Outputs

| Output | Formato | Etapa | Skill |
|--------|---------|-------|-------|
| Apresentacao do Ritual | HTML autocontido | E2 | preparing-materials |
| Briefing do Ritual | MD (guia do condutor) | E2 | preparing-materials |
| Ata do Ritual | MD | E5 | recording-decisions |
| plano-de-acao.csv (atualizado) | CSV | E5 | recording-decisions |

## Estrutura do Ritual (HTML)

O deck e organizado **por especialista**, nao por KPI:

```
1. Capa
2. Visao Geral (Matriz de indicadores × especialistas)
3. Agenda

Per specialist block (repetido):
  4. Dashboard (indicadores + acoes + riscos)
  5. Analise (desvio por assessor + diagnostico 3G)
  6. Projecao (pipeline + gauges + projecoes)
  7. Sugestoes PPI (condicional — so se dados disponiveis)
  8. Agenda transicao

Encerramento:
  N-2. Status Plano de Acao
  N-1. Plano de Acao (tabela)
  N.   Proximos Passos
```

## State management

Compartilha o CICLO.md do m7-controle, adicionando secao `## G2.3 - Ritual de Gestao` com progresso proprio.

## Relacionamento com outros plugins

| Plugin | Relacao |
|--------|---------|
| m7-controle | Fornecedor do WBR e Cards de Performance (G2.2 → G2.3) |
