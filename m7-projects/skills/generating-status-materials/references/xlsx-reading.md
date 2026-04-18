# Cronograma.xlsx — Leitura para Status Materials

> Como `collect_data.py` lê o `Cronograma.xlsx` LIVE. O schema canônico é mantido por `managing-action-plan`; esta skill é **read-only**. Para schema completo, ver `managing-action-plan/references/cronograma-schema.md` — aqui só o necessário para consumo.

## Índice

1. [Resumo do schema](#resumo-do-schema)
2. [Colunas consumidas](#colunas-consumidas)
3. [Código de leitura](#código-de-leitura)
4. [Normalização de campos](#normalização-de-campos)
5. [Filtros úteis](#filtros-úteis)
6. [Staleness via `.sync-state.json`](#staleness-via-sync-statejson)
7. [Não-responsabilidades](#não-responsabilidades)

---

## Resumo do schema

- **Arquivo:** `<proj>/4-status-report/Cronograma.xlsx`
- **Sheet:** primeira sheet (convencionalmente `Cronograma Detalhado`)
- **Header row:** linha **4** (R4)
- **Dados:** linha 5 em diante
- **Coluna A:** vazia (margem)

## Colunas consumidas

| Col | Header | Canônico | Uso aqui |
|---|---|---|---|
| B | `No.` | `no` | Identificação + hierarquia (pontos) |
| C | `Tipo` | `tipo` | Filtro: `Ação` para actions, `Fase` para milestones |
| D | `Etapa` | `etapa` | Título para highlights/next_steps/display |
| E | `Responsável` | `responsavel` | Rationale em next_steps |
| F | `Início Planejado` | `inicio_plan` | Detectar marcos próximos |
| G | `Fim Planejado` | `fim_plan` | Detectar atrasos, marcos próximos |
| H | `Início Real` | `inicio_real` | Marcar `in_progress` |
| I | `Fim Real` | `fim_real` | Marcar `done`, identificar highlights |
| J | `Status` | `status` | Filtro principal: `done`/`in_progress`/`blocked`/`not_started` |
| K | `Entregável` | `entregavel` | (opcional) texto de apoio |
| L | `ClickUp ID` | `clickup_id` | (opcional) link profundo no ClickUp |

## Código de leitura

```python
from openpyxl import load_workbook
from datetime import datetime
from pathlib import Path

CANONICAL_COLUMNS = {
    "No.": "no",
    "Tipo": "tipo",
    "Etapa": "etapa",
    "Responsável": "responsavel",
    "Início Planejado": "inicio_plan",
    "Fim Planejado": "fim_plan",
    "Início Real": "inicio_real",
    "Fim Real": "fim_real",
    "Status": "status",
    "Entregável": "entregavel",
    "ClickUp ID": "clickup_id",
}

def read_cronograma_live(path: Path) -> list[dict]:
    wb = load_workbook(path, data_only=True, read_only=True)
    ws = wb.active
    # Header na linha 4 (index 3)
    rows = list(ws.iter_rows(values_only=True))
    header_row = rows[3]  # linha 4
    
    # Mapear col_index → canonical
    col_map: dict[int, str] = {}
    for idx, cell_value in enumerate(header_row):
        if cell_value in CANONICAL_COLUMNS:
            col_map[idx] = CANONICAL_COLUMNS[cell_value]
    
    missing = set(CANONICAL_COLUMNS.values()) - set(col_map.values())
    # Obrigatórias (se faltar, erro):
    required = {"no", "tipo", "etapa", "status", "fim_plan"}
    missing_required = required - set(col_map.values())
    if missing_required:
        raise ValueError(f"Cronograma.xlsx faltando colunas obrigatórias: {missing_required}")
    
    entries = []
    for row_num, row in enumerate(rows[4:], start=5):  # dados a partir da linha 5
        if not row or all(v is None for v in row):
            continue
        entry = {"_row": row_num}
        for idx, canonical in col_map.items():
            if idx < len(row):
                entry[canonical] = row[idx]
        # Pular linhas sem `no` (margens/totais)
        if not entry.get("no"):
            continue
        entries.append(entry)
    
    return entries
```

## Normalização de campos

### Datas (F, G, H, I)

openpyxl com `data_only=True` devolve:
- `datetime` se a célula tem formato de data
- `str` se o usuário digitou data como texto (ex: `"02/abr"`)
- `None` se vazia

```python
def normalize_date(value, default_year=2026) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        s = value.strip()
        if s in ("—", "-", ""):
            return None
        # Tenta formatos comuns
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d/%m", "%d/%b", "%d/%b/%Y"):
            try:
                dt = datetime.strptime(s, fmt)
                if dt.year == 1900:  # fmt sem ano
                    dt = dt.replace(year=default_year)
                return dt
            except ValueError:
                continue
        return None  # formato desconhecido; warning no caller
    return None
```

`_lib.py` do `managing-action-plan` tem uma versão mais sofisticada; aqui simplificamos porque a leitura é unidirecional.

### Status

Valores válidos (esperados no LIVE): `not_started`, `in_progress`, `blocked`, `done`.

Se encontrar valor fora do enum (ex: `"fazendo"`, `"pendente"`), **não normalizar silenciosamente** — emitir warning e assumir `not_started` como default seguro.

### Hierarquia via `No.`

```python
def parent_no(no: str) -> str | None:
    """1.2.3 → 1.2 ; 1 → None"""
    parts = no.split(".")
    if len(parts) <= 1:
        return None
    return ".".join(parts[:-1])

def is_critical(no: str, all_entries) -> bool:
    """Heurística: fases raiz com muitas filhas = críticas."""
    children = sum(1 for e in all_entries if e.get("no", "").startswith(f"{no}."))
    return children >= 3  # configurable
```

## Filtros úteis

```python
def filter_actions(entries):
    return [e for e in entries if e.get("tipo") in ("Ação", "Acao")]

def filter_phases(entries):
    return [e for e in entries if e.get("tipo") == "Fase"]

def filter_overdue(entries, report_date):
    return [
        e for e in entries
        if e.get("tipo") in ("Ação", "Acao")
        and e.get("status") != "done"
        and e.get("fim_plan") and e["fim_plan"] < report_date
    ]

def filter_recent_done(entries, window_days, report_date):
    from datetime import timedelta
    cutoff = report_date - timedelta(days=window_days)
    return [
        e for e in entries
        if e.get("status") == "done"
        and e.get("fim_real")
        and e["fim_real"] >= cutoff
    ]
```

## Staleness via `.sync-state.json`

```python
import json
from datetime import datetime, timedelta

def check_staleness(sync_state_path: Path, report_date: datetime, threshold_hours=48):
    if not sync_state_path.exists():
        return None
    data = json.loads(sync_state_path.read_text())
    warnings = []
    if data.get("sync_pending"):
        warnings.append("sync_pending=true — executar managing-action-plan sync antes do reporte")
    last_sync = data.get("last_sync")
    if last_sync:
        last_sync_dt = datetime.fromisoformat(last_sync)
        age = report_date - last_sync_dt
        if age > timedelta(hours=threshold_hours):
            warnings.append(f"sync stale: última sync há {age.total_seconds()/3600:.0f}h ({last_sync})")
    return warnings
```

## Não-responsabilidades

Esta skill **não**:
- Escreve no xlsx (isso é `managing-action-plan` domínio)
- Valida hash consistency entre `changelog.md` e xlsx (isso é `managing-action-plan sync`)
- Resolve conflitos com ClickUp (fora de escopo)
- Modifica datas, status, ou adiciona colunas

Leitura pura → JSON canônico → builders.
