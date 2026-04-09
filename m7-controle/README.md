# m7-controle

> Plugin Cowork para o ciclo semanal de controle de performance (G2.2)

## Proposito

Operacionalizar o ciclo de controle de performance, desde a configuracao de Cards de Performance ate a consolidacao do WBR e registro de licoes aprendidas. Executa as etapas E1-E7 do processo G2.2 (E1-E6 semanal, E7 mensal).

## Pipeline Semanal

```
E1: configuring-cards (sob demanda, setup inicial ou manutencao)
│
│   analyst → card_{vert}_{nivel}_{seq}.yaml
│
SEG 06:00 (scheduled task) → cria {vertical}/YYYY-MM-DD/
│
├── E2: collecting-data       → collect.py (plan → run → consolidate)
│                               → dados/dados-consolidados-{vertical}.json
│                               → dados/raw/{indicator_id}.json
│                               → data-quality/data-quality-report.md
│                               → execution-plan.json + execution-results.json
├── E3: analyzing-deviations  → analyst  → analise/deviation-cause-report.md
├── E4: summarizing-actions   → analyst  → analise/action-report.md
├── E5: projecting-results    → analyst  → analise/projection-report.md
└── E6: consolidating-wbr     → analyst  → wbr/wbr-{vertical}-{data}.md
                                          → wbr/wbr-narrativo-{vertical}-{data}.md

MENSAL (ultima sexta do mes) ─────────────────────────────────────────
└── E7: recording-lessons     → analyst  → mensal/YYYY-MM/lessons-learned-YYYY-MM.md
                                           (cross-vertical, nivel processo)

Rastreabilidade: CICLO.md na pasta do ciclo (Log, Anomalias, Decisoes)
```

## Composicao

| Tipo | Qtd | Artefatos |
|------|-----|-----------|
| Skills | 7 | configuring-cards (E1), collecting-data (E2), analyzing-deviations (E3), summarizing-actions (E4), projecting-results (E5), consolidating-wbr (E6), recording-lessons (E7) |
| Agents | 1 | analyst |
| Commands | 4 | next, status, run-weekly, record-lessons |

## Arquitetura de Coleta (E2) — v4.0.0

Cada indicador da Biblioteca de Indicadores (v3.0) tem um **script Python standalone** que acessa as fontes de dados diretamente:

- **ClickHouse**: via `clickhouse-connect` (biblioteca Python nativa)
- **Bitrix24**: via `requests` (HTTP direto ao webhook)

O script `collect.py` orquestra o ciclo em 3 subcomandos:

1. **`plan`** — Le Cards + Indicadores YAML → gera `execution-plan.json` com scripts a executar
2. **`run`** — Executa cada script via `subprocess` → gera `execution-results.json`
3. **`consolidate`** — Valida outputs contra `output_contract` → gera dados consolidados + provenance + quality report

O LLM nao interpreta YAMLs, nao executa queries, nao chama MCPs para E2. Apenas roda 3 comandos Python.

## Variaveis de Ambiente (E2)

| Variavel | Descricao |
|----------|-----------|
| `CLICKHOUSE_HOST` | Host do servidor ClickHouse |
| `CLICKHOUSE_PORT` | Porta do ClickHouse (default: 8123) |
| `CLICKHOUSE_USER` | Usuario de acesso |
| `CLICKHOUSE_PASSWORD` | Senha de acesso |
| `BITRIX_WEBHOOK_URL` | URL base do webhook Bitrix24 |

## Dependencias Externas

| Dependencia | Tipo | Uso |
|-------------|------|-----|
| `clickhouse-connect` | Python lib | Acesso direto ao ClickHouse (E2) |
| `requests` | Python lib | Acesso direto ao Bitrix24 via webhook (E2) |
| `pyyaml` | Python lib | Leitura de YAMLs (E2) |
| Biblioteca de Indicadores (YAML v3.0) | Repositorio do usuario | Indicadores com scripts, output_contract, regras de analise (ESP-PERF-001) |
| Cards de Performance (YAML) | Repositorio do usuario | Composicao de KPIs, arvore, logica de analise (ESP-PERF-002) |
| plano-de-acao.csv | Repositorio do usuario | Leitura de contramedidas (E4) |

## Commands

| Command | Descricao |
|---------|-----------|
| `/m7-controle:next` | Avanca para a proxima etapa do ciclo |
| `/m7-controle:status` | Mostra status atual do ciclo (CICLO.md) |
| `/m7-controle:run-weekly` | Executa pipeline semanal completo (E2-E6) |
| `/m7-controle:record-lessons` | Consolida licoes aprendidas do mes (E7) |

## Outputs

| Output | Formato | Etapa | Skill |
|--------|---------|-------|-------|
| Card de Performance | YAML | E1 | configuring-cards |
| Data Quality Report | MD | E2 | collecting-data |
| Relatorio de Desvios e Causa-Raiz | MD | E3 | analyzing-deviations |
| Relatorio de Acompanhamento de Acoes | MD | E4 | summarizing-actions |
| Relatorio de Projecao | MD | E5 | projecting-results |
| WBR (Weekly Business Report) | MD | E6 | consolidating-wbr |
| Registro de Licoes Aprendidas | MD | E7 | recording-lessons |

## Referencia

- Processo BPM: G2.2 - Controle de Performance
- Arquitetura: ARQ-COWORK-001 v1.1, Secao 3.1
- Especificacoes: ESP-PERF-001 v3.0 (Indicadores), ESP-PERF-002 (Cards)
