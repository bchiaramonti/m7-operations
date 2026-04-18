# CLAUDE.md — {{project_name}}

> Orquestrador do projeto. Claude Code lê este arquivo ao entrar no diretório.

## Projeto

- **Nome:** {{project_name}}
- **Objetivo:** {{project_goal}}
- **Prazo estimado:** {{deadline_or_tbd}}

## Estrutura

| Pasta | Conteúdo | Mantida por |
|---|---|---|
| `1-planning/` | Plano de projeto, WBS/EAP, **`Cronograma.xlsx` baseline**, stakeholders, riscos | Skill `building-project-plan` |
| `2-development/` | Atas, entregáveis em andamento, artefatos intermediários | Manual |
| `3-conclusion/` | Termo de encerramento, lições aprendidas | Manual |
| `4-status-report/` | **`Cronograma.xlsx` live + `changelog.md` + `.sync-state.json` + snapshots `YYYY-MM-DD/` (OPR + PPTX)** | Skills `managing-action-plan` + `generating-status-materials` |
| `_docs/assets/` | Imagens, diagramas | Manual |
| `_docs/bibliography/` | Referências externas | Manual |

## Arquivos-chave

- **Briefing:** [BRIEFING.md](BRIEFING.md)
- **Cronograma baseline (estrutura inicial):** [1-planning/Cronograma.xlsx](1-planning/Cronograma.xlsx) *(gerado por `building-project-plan`; imutável)*
- **Cronograma live (estrutura corrente):** [4-status-report/Cronograma.xlsx](4-status-report/Cronograma.xlsx) *(criado por `managing-action-plan` na primeira rodada)*
- **Changelog do plano de ação:** [4-status-report/changelog.md](4-status-report/changelog.md) *(criado por `managing-action-plan`)*
- **Sync state (sidecar):** [4-status-report/.sync-state.json](4-status-report/.sync-state.json) *(baselines + last_sync_hash)*
- **ClickUp (SSOT global):** ver seção `## Plano de Ação — Configuração` abaixo *(preenchida na primeira rodada de `managing-action-plan`)*

## Skills disponíveis para este projeto

- `building-project-plan` — constrói o plano (WBS/EAP, cronograma, demais artefatos)
- `managing-action-plan` — CRUD de ações, comentários, follow-up, sync com ClickUp
- `generating-status-materials` — gera OPR + apresentação executiva

## Invariantes

- **ClickUp é SSOT global** — vence em conflito de status, responsáveis, datas reais, comentários
- **Cronograma.xlsx live** (`4-status-report/`) é SSOT local da estrutura (hierarquia via `No.`, datas planejadas, entregáveis)
- **Cronograma.xlsx baseline** (`1-planning/`) é imutável após init do plano de ação
- **changelog.md** registra toda operação + espelha comentários do ClickUp (3 camadas: xlsx + changelog + ClickUp)
- **`.sync-state.json`** mantém baselines per-row + last_sync_hash (sidecar não-humano; não editar)

> **Nota:** A skill `managing-action-plan` injeta uma seção `## Plano de Ação — Configuração` neste arquivo
> na primeira rodada do plano (com `clickup_list_id`, `status_map`, mapping `responsaveis` → user IDs do ClickUp).
