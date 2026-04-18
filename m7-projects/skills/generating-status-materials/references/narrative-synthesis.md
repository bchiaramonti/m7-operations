# Narrative Synthesis — Heurísticas Determinísticas

> Regras que `collect_data.py` aplica para derivar narrativa executiva **sem LLM**. Princípio: decisão de "o que mostrar" é determinística e auditável; o LLM só entra se o usuário pedir edição manual depois.

## Índice

1. [Por que sem LLM](#por-que-sem-llm)
2. [Voz executiva (regras de redação)](#voz-executiva-regras-de-redação)
3. [Heurística: status overall (🟢 / 🟡 / 🔴)](#heurística-status-overall----)
4. [Heurística: highlights (o que avançou)](#heurística-highlights-o-que-avançou)
5. [Heurística: next steps (próximos passos)](#heurística-next-steps-próximos-passos)
6. [Heurística: attentions (pontos de atenção)](#heurística-attentions-pontos-de-atenção)
7. [Sentenças hero (headlines dos slides)](#sentenças-hero-headlines-dos-slides)
8. [Validação pós-síntese](#validação-pós-síntese)

---

## Por que sem LLM

Feedback arquitetural registrado (memória): "data collection uses deterministic script, never LLM interpretation". Motivo: reprodutibilidade entre reportes. Se duas execuções no mesmo dia com os mesmos inputs derem narrativas diferentes, perde-se confiança na série temporal de reportes.

## Voz executiva (regras de redação)

Essas regras ditam **como** escrever cada bullet — aplicadas no script via string formatting, não por LLM.

1. **Curto:** cada bullet < 110 chars. Se ultrapassar, truncar com ellipsis.
2. **Factual:** início com verbo no passado (highlights) ou infinitivo (next steps). Nada de "Conseguimos...", "Estamos felizes em...".
3. **Específico:** sempre incluir um número, data ou entidade concreta. "Mapeou cadeia de valor N1" ✅ ; "Progresso em diagnóstico" ❌
4. **Sem hedging:** remover "talvez", "possivelmente", "parece que", "acredito". Se há incerteza, mover para `attentions[]` com severity apropriada.
5. **Sem meta-linguagem:** nada de "neste reporte vamos falar sobre" ou "como vimos anteriormente".
6. **Português BR neutro:** sem gírias, sem anglicismos desnecessários ("kick-off" ok, "bater papo" não).

## Heurística: status overall (🟢 / 🟡 / 🔴)

Ordem de avaliação (primeiro que bater, ganha):

```python
def compute_status_overall(data) -> str:
    total = data["total_actions"]
    overdue = data["overdue_actions"]
    risks = data["risks"]
    milestones = data["milestones"]
    
    # RED
    if total > 0 and overdue / total > 0.20:
        return "red"
    for m in milestones:
        if m["status"] == "overdue" and m.get("is_critical") and m["days_overdue"] > 7:
            return "red"
    for r in risks:
        if r["probability"] == "alta" and r["impact"] in ("critico", "alto") and not r.get("mitigation"):
            return "red"
    
    # YELLOW
    if total > 0 and overdue / total > 0.10:
        return "yellow"
    for m in milestones:
        if m["status"] == "overdue":
            return "yellow"
    for r in risks:
        if r["probability"] == "alta" or r["impact"] in ("critico", "alto"):
            return "yellow"
    
    # GREEN
    return "green"
```

**Emojis:** `green` → 🟢, `yellow` → 🟡, `red` → 🔴. No PPTX, usar quadrado colorido sólido (não emoji) por consistência visual.

## Heurística: highlights (o que avançou)

Fontes (em ordem de prioridade):

1. **Ações marcadas `done` desde o último reporte** — cruzamento `changelog.md` (entries com `op=update` e `field=status` e `new=done`) com `Cronograma.xlsx` (linhas `Tipo=Ação` com `Status=done`).
2. **Marcos alcançados** — linhas `Tipo=Fase` com `Fim Real` preenchido no período.
3. **Decisões tomadas** — entries do `changelog.md` com `op=comment` contendo palavras-chave (`decidido`, `aprovado`, `definido`, `validado`).

### Algoritmo

```python
def compute_highlights(data, report_date, lookback_days=14) -> List[str]:
    window_start = report_date - timedelta(days=lookback_days)
    candidates = []
    
    # 1. Ações concluídas
    for action in data["actions"]:
        if action["status"] == "done" and action["fim_real"] >= window_start:
            candidates.append({
                "text": f"Concluiu: {action['etapa']}",
                "date": action["fim_real"],
                "priority": 10 if action["is_critical"] else 5,
            })
    
    # 2. Marcos alcançados
    for phase in data["phases"]:
        if phase["fim_real"] and phase["fim_real"] >= window_start:
            candidates.append({
                "text": f"Atingiu marco: {phase['etapa']}",
                "date": phase["fim_real"],
                "priority": 15,  # marcos > ações
            })
    
    # 3. Decisões
    decision_keywords = ("decidido", "aprovado", "definido", "validado")
    for entry in data["changelog_entries"]:
        if entry["op"] == "comment" and any(kw in entry["text"].lower() for kw in decision_keywords):
            candidates.append({
                "text": f"Decidiu: {truncate(entry['text'], 100)}",
                "date": entry["timestamp"],
                "priority": 8,
            })
    
    # Ordena: priority desc, depois data desc
    candidates.sort(key=lambda c: (-c["priority"], -c["date"].timestamp()))
    return [c["text"] for c in candidates[:5]]  # top 5 (OPR trunca para 3, PPTX mostra 3-5)
```

## Heurística: next steps (próximos passos)

Fontes:

1. **Marcos próximos (14 dias)** — linhas `Tipo=Fase` com `Início Planejado` ou `Fim Planejado` dentro da janela.
2. **Ações com prazo próximo** — `Tipo=Ação`, `Status != done`, `Fim Planejado` nos próximos 14 dias.
3. **Ações bloqueadas** — `Status=blocked` (atenção imediata).

```python
def compute_next_steps(data, report_date, lookahead_days=14) -> List[dict]:
    window_end = report_date + timedelta(days=lookahead_days)
    candidates = []
    
    for phase in data["phases"]:
        if phase["inicio_plan"] and report_date <= phase["inicio_plan"] <= window_end:
            candidates.append({
                "action": f"Iniciar {phase['etapa']}",
                "deadline": phase["inicio_plan"],
                "rationale": f"Gate de entrada da fase {phase['no']}",
                "priority": 15,
            })
    
    for action in data["actions"]:
        if action["status"] == "blocked":
            candidates.append({
                "action": f"Desbloquear: {action['etapa']}",
                "deadline": action["fim_plan"],
                "rationale": "Bloqueio ativo — impede progresso",
                "priority": 20,  # blocked sempre no topo
            })
        elif action["status"] != "done" and action["fim_plan"] and report_date <= action["fim_plan"] <= window_end:
            candidates.append({
                "action": action["etapa"],
                "deadline": action["fim_plan"],
                "rationale": f"Responsável: {action['responsavel']}",
                "priority": 10 if action["is_critical"] else 5,
            })
    
    # Priority desc, deadline asc
    candidates.sort(key=lambda c: (-c["priority"], c["deadline"]))
    return candidates[:5]
```

**Formato do bullet:** `{action} até {deadline_formatted}` (ex: "Concluir Sprint 0 · Fundação até 07/mar").

## Heurística: attentions (pontos de atenção)

Combina riscos ativos + bloqueios + alertas de prazo:

```python
def compute_attentions(data) -> List[dict]:
    items = []
    
    # 1. Riscos ativos com severity
    for risk in data["risks"]:
        severity = _risk_severity(risk["probability"], risk["impact"])
        if severity != "low":
            items.append({
                "severity": severity,  # "critical" | "warning" | "neutral"
                "text": f"{risk['code']} — {risk['title']}",
                "source": "risk",
            })
    
    # 2. Bloqueios
    for action in data["actions"]:
        if action["status"] == "blocked":
            items.append({
                "severity": "critical",
                "text": f"Bloqueado: {action['etapa']}",
                "source": "blocked",
            })
    
    # 3. Alertas de prazo
    overdue_count = sum(1 for a in data["actions"] 
                       if a["status"] != "done" and a["fim_plan"] and a["fim_plan"] < data["report_date"])
    if overdue_count > 0:
        total = data["total_actions"]
        pct = round(100 * overdue_count / total) if total else 0
        items.append({
            "severity": "warning" if pct <= 20 else "critical",
            "text": f"{overdue_count} ação(ões) atrasada(s) ({pct}% do total)",
            "source": "overdue_summary",
        })
    
    # Ordem: critical > warning > neutral, dentro estável
    order = {"critical": 0, "warning": 1, "neutral": 2}
    items.sort(key=lambda i: order[i["severity"]])
    return items[:5]


def _risk_severity(prob, impact) -> str:
    if prob == "alta" and impact in ("critico", "alto"):
        return "critical"
    if prob in ("alta", "media") or impact in ("critico", "alto"):
        return "warning"
    return "neutral"  # será filtrado por `!= "low"` acima? — ajustar: neutral passa
```

## Sentenças hero (headlines dos slides)

### Slide 06 Executive — "3 de 12 tarefas concluídas (25%)"

```python
def hero_sentence_executive(data) -> str:
    total_in_sprint = len([a for a in data["actions"] if a["sprint"] == data["active_sprint"]])
    done_in_sprint = len([a for a in data["actions"] if a["sprint"] == data["active_sprint"] and a["status"] == "done"])
    pct = round(100 * done_in_sprint / total_in_sprint) if total_in_sprint else 0
    return f"{done_in_sprint} de {total_in_sprint} tarefas concluídas ({pct}%)"
```

### Slide 03 Roadmap — "1 de 5 sprints em execução"

```python
def sprint_progress_sentence(data) -> str:
    total_sprints = len(data["sprints"])
    active = sum(1 for s in data["sprints"] if s["status"] == "active")
    return f"{active} de {total_sprints} sprint(s) em execução"
```

### Slide 07 Risks — "3 riscos mapeados — 1 com probabilidade alta"

```python
def risks_sentence(risks) -> str:
    total = len(risks)
    high = sum(1 for r in risks if r["probability"] == "alta")
    if total == 0:
        return "Nenhum risco mapeado"
    if high == 0:
        return f"{total} risco(s) mapeado(s) — nenhum com probabilidade alta"
    return f"{total} risco(s) mapeado(s) — {high} com probabilidade alta"
```

## Validação pós-síntese

Após `collect_data.py` gerar o JSON canônico, aplicar verificações de sanidade:

- Cada bullet < 110 chars
- `highlights + next_steps + attentions` todos não-vazios (se vazios, emitir warning "seção X sem conteúdo — revisar dados de entrada")
- `status.percent_done` consistente com `done_actions / total_actions`
- `active_sprint` (se definido) existe em `sprints[]`

Emitir lista de warnings em `data.warnings[]` para o builder exibir.
