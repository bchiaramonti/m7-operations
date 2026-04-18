# Data Sources — De onde vem cada campo

> Mapeamento exato: cada campo do dict canônico que `collect_data.py` emite → fonte no projeto. Use esta reference quando algo estiver faltando ou com valor estranho — indica onde o dado foi lido (ou deveria ter sido).

## Índice

1. [Dict canônico (resumo)](#dict-canônico-resumo)
2. [Tabela de mapeamento](#tabela-de-mapeamento)
3. [Ordem de precedência (conflitos)](#ordem-de-precedência-conflitos)
4. [Campos derivados vs lidos](#campos-derivados-vs-lidos)
5. [Warnings típicos](#warnings-típicos)

---

## Dict canônico (resumo)

```python
{
    "report_date": "YYYY-MM-DD",
    "project": {
        "name": str,
        "goal": str,
        "pm": str,
        "pm_email": str,
        "period_label": str,      # "Quinzena DD/MM — DD/MM/AAAA"
        "footer_label": str,      # "M7 Investimentos · Mês AAAA"
        "clickup_list_url": str,
    },
    "status": {
        "overall": "green|yellow|red",
        "percent_done": int,
        "total_actions": int,
        "done_actions": int,
        "overdue_actions": int,
        "active_sprint": {...} | None,
        "active_sprint_index": int,
        "total_sprints": int,
        "hero_sentence": str,           # "3 de 12 tarefas concluídas (25%)"
        "sprint_progress_sentence": str,
        "risks_sentence": str,
    },
    "highlights": [str, ...],           # até 5 bullets
    "next_steps": [{"action", "deadline", "rationale", ...}, ...],
    "attentions": [{"severity", "text", "source"}, ...],
    "milestones": [{"name", "date", "status", "is_critical"}, ...],
    "macro_milestones": [{"label", "status"}, ...],  # 7 marcos do slide 06
    "sprints": [{"code", "title", "period_label", "fronts", "status"}, ...],
    "fronts": [{"code", "title", "po", "start_date", "end_date", "color", "sprint_bars"}, ...],
    "sprint_actions": [...],            # ações em andamento/próximas
    "risks": [{"code", "title", "probability", "impact", "mitigation"}, ...],
    "changelog_entries": [...],         # parsed
    "warnings": [str, ...],             # avisos do collect (staleness, campo faltando)
}
```

---

## Tabela de mapeamento

### `project.*`

| Campo | Fonte | Path/Query |
|---|---|---|
| `project.name` | `1-planning/plano-projeto.html` | `<h1>` ou `<title>` — parse BeautifulSoup |
| `project.goal` | `BRIEFING.md` | Seção `## Objetivo`, primeira linha |
| `project.pm` | `1-planning/plano-projeto.html` | Bloco "Líder" ou "PM" (`.hero-meta` data-key="pm") |
| `project.pm_email` | `CLAUDE.md` | Frontmatter ou seção `## Contatos` com pattern `email: ...` |
| `project.period_label` | `--report-date` + `--period-days` | Formatado em script |
| `project.footer_label` | Constante | `"M7 Investimentos · {{ report_date.month_label }}"` |
| `project.clickup_list_url` | `4-status-report/.sync-state.json` | Campo `clickup_list_url`, se presente; senão construir a partir de `clickup_list_id` |

### `status.*`

| Campo | Fonte | Cálculo |
|---|---|---|
| `status.overall` | Derivado | `compute_status_overall()` — ver narrative-synthesis.md |
| `status.percent_done` | `Cronograma.xlsx` LIVE | `done / total * 100` (só `Tipo=Ação`) |
| `status.total_actions` | `Cronograma.xlsx` LIVE | Conta linhas `Tipo=Ação` |
| `status.done_actions` | `Cronograma.xlsx` LIVE | Conta `Status=done` e `Tipo=Ação` |
| `status.overdue_actions` | `Cronograma.xlsx` LIVE | `Fim Planejado < report_date AND Status != done AND Tipo=Ação` |
| `status.active_sprint` | `Cronograma.xlsx` LIVE + `roadmap-marcos.html` | Primeira Fase com `Fim Planejado >= report_date AND Status != done` |
| `status.*_sentence` | Derivado | Ver narrative-synthesis.md |

### `highlights[]`

Derivado de 3 fontes (ver `narrative-synthesis.md`):
- `Cronograma.xlsx` LIVE → ações recém-done
- `Cronograma.xlsx` LIVE → fases com `Fim Real` preenchido no período
- `4-status-report/changelog.md` → decisões (entries com keywords)

### `next_steps[]`

Derivado de `Cronograma.xlsx` LIVE:
- Fases com `Início Planejado` próximo
- Ações com `Fim Planejado` nos próximos N dias
- Ações `Status=blocked`

### `attentions[]`

Derivado de:
- `1-planning/artefatos/riscos.html` → riscos ativos (não encerrados)
- `Cronograma.xlsx` LIVE → ações bloqueadas
- `Cronograma.xlsx` LIVE → alerta de atrasadas (resumo)

### `milestones[]` e `macro_milestones[]`

| Campo | Fonte |
|---|---|
| `milestones[]` | `1-planning/artefatos/roadmap-marcos.html` — bloco de marcos |
| `macro_milestones[]` | `Cronograma.xlsx` LIVE, linhas `Tipo=Fase` em nível raiz — primeiras 7 em ordem de `Início Planejado` |

**Status de marco:**
- `done` se `Fim Real` preenchido e `<= report_date`
- `overdue` se `Fim Planejado < report_date` e não `done`
- `in_progress` se `Início Real` preenchido e não `done`
- `not_started` caso contrário

### `sprints[]` e `fronts[]`

| Campo | Fonte |
|---|---|
| `sprints[]` | Inferido de `Cronograma.xlsx` LIVE — agrupamento de Fases de nível raiz como "sprints" (heurística: Fases com duração < 21 dias). **Alternativamente:** se `BRIEFING.md` ou `1-planning/roadmap-marcos.html` tiver seção explícita "## Sprints", usar essa. |
| `fronts[]` | `1-planning/artefatos/recursos-dependencias.html` — bloco "Frentes" ou "Squads" |

Se não houver distinção clara sprint/front no projeto (projeto simples), `sprints[]` = fases raiz e `fronts[]` = `[]`.

### `risks[]`

| Campo | Fonte | Como |
|---|---|---|
| `code` | `riscos.html` | `<tr data-risk-id="R1">` ou numeração sequencial |
| `title` | `riscos.html` | `<td class="title">` |
| `probability` | `riscos.html` | `<td class="probability">` — normalizar para `baixa/media/alta` |
| `impact` | `riscos.html` | `<td class="impact">` — normalizar para `baixo/medio/alto/critico` |
| `mitigation` | `riscos.html` | `<td class="mitigation">` ou `.response` |

**Fallback:** se `riscos.html` não existir ou estiver vazio, `risks[]` = `[]` e adicionar warning.

### `changelog_entries[]`

Fonte: `4-status-report/changelog.md` — parser markdown simples que detecta entries.

**Formato esperado (mantido por `managing-action-plan`):**

```markdown
## 2026-04-18 14:32 — update

- **No.** 2.1.1
- **Campo:** status
- **Antes:** in_progress
- **Depois:** done
- **Por:** Bruno
```

Parser extrai: `timestamp`, `op`, `no`, `field`, `old`, `new`, `by`, `text` (texto livre se houver).

### `.sync-state.json` (opcional)

Campos usados:
- `last_sync` — comparar com `report_date` para detectar staleness (> 48h = warning)
- `sync_pending` — boolean; se `true`, warning "sync pendente"
- `clickup_list_id` — construir `clickup_list_url` se não estiver explícito
- `status_map` — para normalizar comparações local ↔ ClickUp (não usado na leitura de status local)

Se o arquivo não existir, **não** é erro — apenas warning.

---

## Ordem de precedência (conflitos)

Quando múltiplas fontes têm o mesmo dado:

1. **`Cronograma.xlsx` LIVE > HTMLs de `1-planning/`** — LIVE reflete o estado atual; os HTMLs são baseline imutável do plano.
2. **`CLAUDE.md` > `BRIEFING.md`** — `CLAUDE.md` é o orquestrador e tem dados operacionais atualizados.
3. **`.sync-state.json` > inferência** — se o arquivo tem `clickup_list_id`, usar; senão cair em busca em `CLAUDE.md`.

---

## Campos derivados vs lidos

| Derivado (calculado em `collect_data.py`) | Lido direto |
|---|---|
| `status.overall`, `status.hero_sentence`, `status.*_sentence` | `project.name`, `project.goal`, `project.pm` |
| `highlights[]`, `next_steps[]`, `attentions[]` | `risks[]`, `changelog_entries[]` |
| `macro_milestones[]` (top 7 de `phases`) | `milestones[]` (raw do HTML) |
| `sprints[].status` | `sprints[].code`, `sprints[].title` |

Campos **derivados** são computados após leitura bruta; se o raw estiver faltando, derivado vira `None` + warning.

---

## Warnings típicos

`data.warnings[]` pode conter:

- `"sync stale: last_sync > 48h (2026-04-16T10:00:00)"` — dado pode estar desatualizado
- `"sync_pending=true — executar managing-action-plan sync antes do reporte"`
- `"risks.html não encontrado — seção Riscos vazia no reporte"`
- `"recursos-dependencias.html: bloco 'Frentes' não identificado — slide 04 usará placeholder"`
- `"BRIEFING.md: seção '## Objetivo' não encontrada — usando primeira linha do arquivo"`
- `"changelog.md com menos de N entries no período — highlights podem estar incompletos"`

A skill **não aborta** por warnings; o builder gera o melhor possível e imprime a lista ao usuário.
