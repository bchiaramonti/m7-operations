# Regras de Priorizacao e Duplicatas

Referencia canonica para priorizacao de contramedidas e deteccao de duplicatas. Usada tanto pela skill `recording-decisions` quanto pelo agent `decision-recorder`.

> **Atualizado 2026-05-31 (v3.9.0)** — labels migrados para schema v2.0 (`urgent/high/normal/low`).
> Referencias a CSV substituidas por ClickUp (SoT migrada em 2026-04-30 para lista `pa-resultado`
> id `901326795742`). Ver [clickup-actions-schema.md](clickup-actions-schema.md) para o schema atual
> e [plan-preview-schema.md](plan-preview-schema.md) para o JSON canonico.

---

## Tabela de prioridade (schema v2.0)

| `priority_label` | `priority_clickup` | Criterio |
|---|---|---|
| `urgent` | 1 | Indicador Vermelho + volume >= mediana das tasks ativas da vertical |
| `high` | 2 | Indicador Vermelho |
| `normal` | 3 | Indicador Amarelo |
| `low` | 4 | Preventiva (indicador Verde ou sem desvio) |

> A "mediana das tasks ativas da vertical" e calculada sobre o snapshot `dados/raw/clickup-tasks-{vertical}.json` (filtrado por status != `complete|closed|cancelled`). Use o campo `volume_impacto` como base.

> **Legacy v1.0** (`critica/alta/media/baixa`): nao usar mais. Schema v2.0 grava ambos
> `priority_label` (string ingles) e `priority_clickup` (int 1-4) TOP-LEVEL no item de
> `contramedidas_novas[]`.

## Ordenacao

1. Ordenar por prioridade: `urgent` > `high` > `normal` > `low` (equivalente a `priority_clickup` ascendente 1 → 4)
2. Desempate por receita descendente (maior `receita_impacto` primeiro)
3. Incluir `justificativa_prio` em cada item top-level (campo obrigatorio v2.0)

## Regras de atribuicao

- Prioridade e baseada em **metricas objetivas** (semaforo do indicador + volume/receita), NUNCA em opiniao
- Se volume nao informado pelo usuario: inferir do WBR (secao de impacto financeiro do KPI)
- Se nem usuario nem WBR fornecem volume: atribuir `high` (nao `urgent`) para Vermelhos sem dados de volume

---

## Deteccao de duplicatas

Antes de criar nova task no ClickUp, verificar se **ja existe** task com:

1. Mesmo `name` (comparacao case-insensitive, trimmed, similaridade ≥0.85) **E**
2. Mesmo `Responsavel Externo` (custom field) **E**
3. Mesma `Vertical` (custom field) **E**
4. `status` diferente de `complete`/`closed`/`cancelled`

### Fonte de verificacao

**Primaria — snapshot JSON** (rapido, ja filtrado):

```python
snapshot = read_json("{cycle_folder}/dados/raw/clickup-tasks-{vertical}.json")
# Já filtrado por Vertical em E2 F1.5; basta filtrar por status ativo + responsavel
candidatos = [
    t for t in snapshot["data"]
    if t["responsavel_externo"] == nova_contramedida["responsavel"]
    and (t.get("status") or "").lower() not in ("complete", "closed", "cancelled", "done")
    and similarity(t["name"], nova_contramedida["titulo"]) >= 0.85
]
```

**Confirmacao — `clickup_filter_tasks`** (em tempo real, quando o snapshot pode estar desatualizado):

```python
clickup_filter_tasks(
    list_id="901326795742",
    custom_fields=[
        {"field_id": "a7c7bc7c-2526-4083-9753-aa2103a08f53", "operator": "=",
         "value": vertical_option_value},
        {"field_id": "e44c8cff-7d0b-4074-84ae-c10c67b0a26d", "operator": "=",
         "value": responsavel_option_value}
    ]
)
```

### Se duplicata encontrada

- **NAO** invocar `clickup_create_task`
- Informar ao usuario: "Contramedida '{titulo}' ja existe como ClickUp `{id}` (status: `{status}`, url: https://app.clickup.com/t/{id})"
- Oferecer **atualizar** a task existente via `clickup_update_task` + `clickup_create_task_comment` em vez de criar nova
- Registrar na secao "Duplicatas Detectadas" da ata com `id` ClickUp + URL clicavel
