#!/usr/bin/env python3
"""
followup.py — Detecta acoes que precisam de atencao do usuario.

Categorias:
    overdue     due < hoje AND status != done
    upcoming    hoje <= due <= hoje + lookahead_days AND status != done
    stagnated   status == in_progress AND due - hoje > 14 AND sem update remoto recente
                (heuristica baseada em fim_real vazio + inicio_plan velho)
    unstarted   start <= hoje AND status == not_started

Filtra automaticamente:
    - Linhas com tipo `Fase` (agregadores; status raramente makes sense)
    - Linhas sem due_date
    - Linhas com status = done

A skill (Claude) usa o output para perguntar 1-a-1 ao usuario.

Uso:
    python3 followup.py --file 4-status-report/Cronograma.xlsx
    python3 followup.py --file ... --lookahead-days 7 --reference-date 2026-04-18
    python3 followup.py --file ... --include-fases   # incluir fases na detecao

Saida (stdout, JSON):
    {
      "ok": true,
      "reference_date": "2026-04-18",
      "categories": {
        "overdue":   [{"no":"...","etapa":"...","due":"...","days_late":N,...}, ...],
        "upcoming":  [...],
        "stagnated": [...],
        "unstarted": [...]
      },
      "totals": {"overdue": N, "upcoming": N, "stagnated": N, "unstarted": N},
      "suggested_questions": [
        "T037 (No. 1.1.1) venceu em 2026-04-15 (3 dias atraso) e esta in_progress. Andamento?",
        ...
      ]
    }
"""

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _lib import (  # noqa: E402
    CronogramaXLSX,
    canonical_row,
    normalize_date,
)


SKIP_TIPOS_DEFAULT = {"Fase"}
STAGNATION_DAYS = 14  # in_progress com due distante e sem fim_real preenchido


def categorize(rows: list[dict], today: dt.date, lookahead_days: int,
               include_fases: bool) -> dict:
    overdue = []
    upcoming = []
    stagnated = []
    unstarted = []

    skip = set() if include_fases else SKIP_TIPOS_DEFAULT
    upcoming_limit = today + dt.timedelta(days=lookahead_days)

    for row in rows:
        canon = canonical_row(row)
        tipo = canon.get("tipo", "")
        if tipo in skip:
            continue
        status = canon.get("status", "")
        if status == "done":
            continue

        due_str = canon.get("fim_plan", "")
        due_dt = normalize_date(due_str)
        due_d = due_dt.date() if due_dt else None

        start_str = canon.get("inicio_plan", "")
        start_dt = normalize_date(start_str)
        start_d = start_dt.date() if start_dt else None

        item = {
            "_row_index": row.get("_row_index", -1),
            "no": canon.get("no", ""),
            "tipo": tipo,
            "etapa": canon.get("etapa", ""),
            "responsavel": canon.get("responsavel", ""),
            "status": status or "(sem status)",
            "inicio_plan": canon.get("inicio_plan", ""),
            "fim_plan": canon.get("fim_plan", ""),
            "clickup_id": canon.get("clickup_id", ""),
        }

        if due_d:
            if due_d < today:
                item["days_late"] = (today - due_d).days
                overdue.append(item)
            elif today <= due_d <= upcoming_limit:
                item["days_until_due"] = (due_d - today).days
                upcoming.append(item)
            elif status == "in_progress" and (due_d - today).days > STAGNATION_DAYS:
                # heuristica: in_progress com due ainda longe, sem fim_real
                if not canon.get("fim_real", ""):
                    item["days_until_due"] = (due_d - today).days
                    stagnated.append(item)

        if start_d and start_d <= today and status == "not_started":
            item_un = dict(item)
            item_un["days_since_start"] = (today - start_d).days
            unstarted.append(item_un)

    return {
        "overdue": overdue,
        "upcoming": upcoming,
        "stagnated": stagnated,
        "unstarted": unstarted,
    }


def build_questions(categories: dict) -> list[str]:
    qs: list[str] = []
    for item in categories["overdue"]:
        qs.append(
            f"No. {item['no']} '{item['etapa'][:50]}' venceu em {item['fim_plan']} "
            f"({item['days_late']} dia(s) de atraso) e esta {item['status']}. "
            f"Andamento? (atualizar status / mover data / comentar / skip)"
        )
    for item in categories["unstarted"]:
        qs.append(
            f"No. {item['no']} '{item['etapa'][:50]}' deveria ter comecado em "
            f"{item['inicio_plan']} ({item['days_since_start']} dia(s) atras) e ainda "
            f"esta not_started. Iniciar agora? Reagendar? Bloqueado?"
        )
    for item in categories["upcoming"]:
        qs.append(
            f"No. {item['no']} '{item['etapa'][:50]}' vence em {item['fim_plan']} "
            f"({item['days_until_due']} dia(s)) e esta {item['status']}. "
            f"Vai entregar a tempo? Algum bloqueio?"
        )
    for item in categories["stagnated"]:
        qs.append(
            f"No. {item['no']} '{item['etapa'][:50]}' esta in_progress sem update ha um tempo "
            f"(due em {item['days_until_due']} dia(s)). Andamento?"
        )
    return qs


def main() -> int:
    p = argparse.ArgumentParser(description="Detecta acoes que precisam atencao.")
    p.add_argument("--file", required=True, help="Caminho do Cronograma.xlsx")
    p.add_argument("--lookahead-days", type=int, default=3,
                   help="Janela 'upcoming' em dias (default 3)")
    p.add_argument("--reference-date", default=None,
                   help="Data de referencia (default: hoje). Formato ISO YYYY-MM-DD")
    p.add_argument("--include-fases", action="store_true",
                   help="Inclui linhas tipo Fase (default: pula)")
    args = p.parse_args()

    if args.reference_date:
        try:
            today = dt.datetime.strptime(args.reference_date, "%Y-%m-%d").date()
        except ValueError:
            print(f"ERRO: --reference-date invalido: {args.reference_date}", file=sys.stderr)
            return 1
    else:
        today = dt.date.today()

    path = Path(args.file)
    if not path.exists():
        print(f"ERRO: arquivo nao existe: {path}", file=sys.stderr)
        return 1

    try:
        cron = CronogramaXLSX(path)
        cron.load()
    except (FileNotFoundError, ValueError, RuntimeError) as e:
        print(f"ERRO ao carregar xlsx: {e}", file=sys.stderr)
        return 1

    rows = cron.read_rows()
    categories = categorize(rows, today, args.lookahead_days, args.include_fases)
    questions = build_questions(categories)

    payload = {
        "ok": True,
        "reference_date": today.isoformat(),
        "lookahead_days": args.lookahead_days,
        "categories": categories,
        "totals": {k: len(v) for k, v in categories.items()},
        "suggested_questions": questions,
    }
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2, default=str)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
