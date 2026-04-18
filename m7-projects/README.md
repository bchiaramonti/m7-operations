# m7-projects

> Gestão completa do ciclo de vida de projetos M7: do scaffolding inicial à geração de materiais executivos de status, passando por plano de projeto com WBS/EAP e plano de ação continuamente sincronizado com ClickUp.

## Status (v0.1.0 — alpha)

| Skill | Status |
|---|---|
| `initializing-project` | ✅ Implementada |
| `building-project-plan` | 🚧 Planejada (próxima release) |
| `managing-action-plan` | 🚧 Planejada |
| `generating-status-materials` | 🚧 Planejada |

Apenas `initializing-project` está funcional nesta versão. As três skills restantes serão liberadas em releases subsequentes antes do v1.0.0 — ver [CHANGELOG.md](CHANGELOG.md).

## O que é

Plugin Claude Code que cobre o ciclo de vida completo de projetos em quatro skills:

1. **Inicialização** — cria estrutura de diretório padronizada
2. **Plano de projeto** — constrói plano formal com WBS/EAP e cronograma (artefatos configuráveis)
3. **Plano de ação** — CRUD de ações, follow-up proativo de prazos, sincronização bidirecional com ClickUp
4. **Status reports** — OPR (one-page report HTML/PDF) + apresentação executiva (PPTX)

**Princípio central:** três camadas locais sincronizadas (`CLAUDE.md` + `CRONOGRAMA.md` + `CHANGELOG.md`) mantidas consistentes com **ClickUp como SSOT (Single Source of Truth)**. Sync é regra invariante interna, não objetivo.

## Pré-requisitos

- **ClickUp** — workspace configurado e MCP autenticado (OAuth via Claude.ai)
- **Python 3.11+** com:
  - `python-pptx` — geração de apresentações
  - `pyyaml` — parsing do frontmatter do CRONOGRAMA.md
  - `playwright` **ou** `weasyprint` — conversão HTML → PDF do OPR
- **Fonte TWK Everett** instalada localmente (fallback automático para Arial quando ausente)

## Skills

| Skill | Descrição | Quando usar |
|---|---|---|
| `initializing-project` | Cria estrutura básica: `1-planning/`, `2-development/`, `3-conclusion/`, `4-status-report/`, `_docs/{assets,bibliography}/` + `CLAUDE.md` + `BRIEFING.md` | Ao iniciar qualquer novo projeto |
| `building-project-plan` | Constrói plano de projeto com WBS/EAP, cronograma e demais artefatos | Após scaffold, antes de começar execução |
| `managing-action-plan` | CRUD de ações, comentários, follow-up proativo e sync com ClickUp | No dia a dia — criar ação, atualizar status, perguntar atrasos, sincronizar |
| `generating-status-materials` | Gera OPR (HTML/PDF) + apresentação executiva (PPTX) aplicando M7-2026 | Em cadência de reporte (semanal, quinzenal) ou sob demanda |

Skills são **user-invocable** — aparecem diretamente no menu `/` do Claude Code. Não há commands nem agents neste plugin (decisão arquitetural explícita: skills coesas resolvem o escopo).

## Estrutura de projeto gerada

Quando `initializing-project` executa, cria dentro do destino:

```
<project-dir>/
├── CLAUDE.md                    # Orquestrador do projeto
├── BRIEFING.md                  # Contexto, objetivo, stakeholders
├── 1-planning/                  # Plano + WBS/EAP + CRONOGRAMA + CHANGELOG
├── 2-development/               # Execução: atas, entregáveis em andamento
├── 3-conclusion/                # Encerramento, lições aprendidas
├── 4-status-report/             # OPRs e apresentações por data (YYYY-MM-DD/)
└── _docs/
    ├── assets/                  # Imagens, diagramas
    └── bibliography/            # Referências externas
```

## Fluxo de uso

```
1. /m7-projects:initializing-project                  → scaffold do diretório
         ↓
2. /m7-projects:building-project-plan                 → plano formal (WBS/EAP + cronograma)
         ↓
3. /m7-projects:managing-action-plan                  → uso diário: CRUD, follow-up, sync
         ↻  (ciclo contínuo)
         ↓
4. /m7-projects:generating-status-materials           → OPR + PPTX para stakeholders
```

## Três camadas sincronizadas

```
    ┌──────────────┐
    │  CLAUDE.md   │ ← orquestração (aponta para os outros)
    └──────┬───────┘
           │
    ┌──────┴──────────────────────────────────┐
    │  1-planning/CRONOGRAMA.md               │ ← estrutura local (SSOT estrutural)
    │  (markdown table + YAML frontmatter)    │
    └──────┬──────────────────────────────────┘
           │
    ┌──────┴──────────────────────────────────┐
    │  1-planning/CHANGELOG.md                │ ← histórico append-only de mutações
    └──────┬──────────────────────────────────┘
           │
           ↕  sync invariante (three-way diff)
           │
    ┌──────┴──────────┐
    │   ClickUp       │ ← SSOT executivo (status, datas, assignees, comentários)
    └─────────────────┘
```

A skill `managing-action-plan` executa sync automaticamente após cada operação. Conflitos determinísticos são resolvidos por regras; conflitos ambíguos (edição concorrente em título/notas) entram em prompt interativo.

## Regras de resolução de conflito

| Campo | Local vs ClickUp | Regra |
|---|---|---|
| Estrutura (add/del ação) | — | **local-wins** |
| `status` | ambos mudaram | **ClickUp-wins** |
| `assignee` | ambos mudaram | **ClickUp-wins** |
| `due` / `start` | ambos mudaram | **local-wins** se local >= `last_sync`; senão prompt |
| `priority` | ambos mudaram | **local-wins** |
| `parent` / `deps` | ambos mudaram | **local-wins** |
| `title` / `notes` | ambos mudaram | prompt + sugestão de merge |
| `time_tracked` / comentários | — | **ClickUp-only** (mirror read-only) |

## Design System M7-2026

Todos os materiais visuais (OPR, apresentação) aplicam:

| Token | Valor |
|---|---|
| Cor primária | Verde Caqui `#424135` |
| Background claro | Off-White `#fffdef` |
| Accent (decorativo, nunca texto) | Lime `#EEF77C` |
| Fonte | TWK Everett (fallback Arial) |

## Diferenças vs `gestao-de-projetos` (deprecated)

O plugin anterior `gestao-de-projetos` (marketplace `chiaras-ai`) foi **substituído** por este plugin. Diferenças principais:

- **Paradigma:** sprint-first → **WBS/EAP first** (cronograma é entregável do plano)
- **Sync:** unidirecional local → ClickUp → **bidirecional com ClickUp como SSOT**
- **Status reports:** só PPTX → **OPR (HTML/PDF) + PPTX** unificados
- **Arquitetura:** 4 agents + 3 skills + ClickUp tight-coupling → **4 skills coesas, zero agents, sync como invariante**

## Versão

`1.0.0` — plugin novo, sem histórico de migração semântica.
