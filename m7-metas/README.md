# m7-metas

> Plugin Cowork | Processo BPM: G2.1 - Desdobramento de Metas (subprocesso Biblioteca de Indicadores)

Operacionaliza a criacao, validacao e manutencao de indicadores na Biblioteca de Indicadores M7, conforme a especificacao tecnica ESP-PERF-001 e o Guia de Elaboracao (GUIA-ELABORACAO-INDICADORES.md).

## Skill

| Skill | Descricao |
|-------|-----------|
| `creating-indicators` | Cria, valida, edita e promove indicadores. Entrevista guiada, validacao contra schema v2.0, ciclo de maturidade. |

## Modos de operacao

1. **Criar novo indicador** — Entrevista guiada (source_type, dominio, granularidade, unit) + descoberta de dados via MCP
2. **Validar indicador existente** — Validacao estrutural (schema v2.0) + execucao de quality_checks
3. **Promover status** — Transicao draft > validated > promoted_to_gold com validacao como pre-requisito
4. **Editar indicador existente** — Aplicar edicoes + revalidar + atualizar updated_at

## Dependencias MCP

- **ClickHouse (m7bronze)** — Testar queries SQL, listar tabelas/views, validar colunas
- **Bitrix24 CRM** — Testar tools MCP, listar campos de deals/users/stages

## Relacionamento com outros plugins

| Plugin | Relacao |
|--------|---------|
| `m7-controle` (PLG-01) | Consumidor: le indicadores para Cards de Performance e queries |
| `analise-dados-m7` | Substitui a skill `managing-indicators` (versao mais completa) |

## Referencia

- ESP-PERF-001 v1.0 — Especificacao tecnica da Biblioteca de Indicadores
- GUIA-ELABORACAO-INDICADORES.md — Guia pratico de construcao
- _schema.yaml v2.0 — Contrato de validacao estrutural
