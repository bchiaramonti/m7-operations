# CLAUDE.md — {{project_name}}

> Orquestrador do projeto. Claude Code lê este arquivo ao entrar no diretório.

## Projeto

- **Nome:** {{project_name}}
- **Objetivo:** {{project_goal}}
- **Prazo estimado:** {{deadline_or_tbd}}

## Estrutura

| Pasta | Conteúdo | Mantida por |
|---|---|---|
| `1-planning/` | Plano de projeto, WBS/EAP, cronograma, stakeholders, riscos | Skill `building-project-plan` + `managing-action-plan` |
| `2-development/` | Atas, entregáveis em andamento, artefatos intermediários | Manual |
| `3-conclusion/` | Termo de encerramento, lições aprendidas | Manual |
| `4-status-report/` | OPRs e apresentações por data (`YYYY-MM-DD/`) | Skill `generating-status-materials` |
| `_docs/assets/` | Imagens, diagramas | Manual |
| `_docs/bibliography/` | Referências externas | Manual |

## Arquivos-chave

- **Briefing:** [BRIEFING.md](BRIEFING.md)
- **Cronograma (SSOT local):** [1-planning/CRONOGRAMA.md](1-planning/CRONOGRAMA.md) *(criado pela skill `managing-action-plan`)*
- **Changelog do plano de ação:** [1-planning/CHANGELOG.md](1-planning/CHANGELOG.md) *(criado pela skill `managing-action-plan`)*
- **ClickUp (SSOT):** `{{clickup_list_id_or_tbd}}` *(preenchido quando plano de ação for inicializado)*

## Skills disponíveis para este projeto

- `building-project-plan` — constrói o plano (WBS/EAP, cronograma, demais artefatos)
- `managing-action-plan` — CRUD de ações, comentários, follow-up, sync com ClickUp
- `generating-status-materials` — gera OPR + apresentação executiva

## Invariantes

- **ClickUp é SSOT** para status, datas, responsáveis, comentários das ações
- **CRONOGRAMA.md local** é SSOT para estrutura (hierarquia, dependências, `local_id`)
- **CHANGELOG.md** registra toda operação que altera o plano de ação
