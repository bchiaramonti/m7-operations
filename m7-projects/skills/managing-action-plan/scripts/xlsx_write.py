#!/usr/bin/env python3
"""
xlsx_write.py — Mutacoes locais no Cronograma.xlsx.

Subcomandos:
    write-clickup-id   --row-index N --clickup-id ID
    write-cell         --row-index N --field STATUS --value done
    append-row         --row-json '{"no":"3.6","tipo":"Acao","etapa":"...","responsavel":"Bruno",...}'
    delete-row         --row-index N
    bulk-cells         --ops-json '[{"row_index":N,"field":"status","value":"in_progress"},...]'

Todos preservam formatacao xlsx via openpyxl (mantem celulas adjacentes intocadas).
Campos de data sao normalizados via _lib.normalize_date antes de gravar.

Uso comum (apos Claude chamar clickup_create_task):
    python3 xlsx_write.py write-clickup-id \\
        --file 4-status-report/Cronograma.xlsx \\
        --row-index 5 --clickup-id "86abc123"

Saida (stdout, JSON):
    {"ok": true, "operation": "write-clickup-id", "row_index": 5, "clickup_id": "86abc123"}
"""

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _lib import CronogramaXLSX, CANONICAL_COLUMN_ORDER  # noqa: E402


def cmd_write_clickup_id(args, cron: CronogramaXLSX) -> dict:
    cron.ensure_clickup_id_column()
    cron.write_clickup_id(args.row_index, args.clickup_id)
    return {"row_index": args.row_index, "clickup_id": args.clickup_id}


def cmd_write_cell(args, cron: CronogramaXLSX) -> dict:
    if args.field not in CANONICAL_COLUMN_ORDER:
        raise ValueError(f"Campo invalido: {args.field}. Validos: {CANONICAL_COLUMN_ORDER}")
    cron.write_cell(args.row_index, args.field, args.value)
    return {"row_index": args.row_index, "field": args.field, "value": args.value}


def cmd_append_row(args, cron: CronogramaXLSX) -> dict:
    try:
        row = json.loads(args.row_json)
    except json.JSONDecodeError as e:
        raise ValueError(f"--row-json invalido: {e}")
    if not row.get("no"):
        raise ValueError("row precisa de pelo menos campo 'no'")
    if not row.get("etapa"):
        raise ValueError("row precisa de pelo menos campo 'etapa'")
    new_idx = cron.append_row(row)
    return {"row_index": new_idx, "no": row.get("no"), "etapa": row.get("etapa")}


def cmd_delete_row(args, cron: CronogramaXLSX) -> dict:
    cron.delete_row(args.row_index)
    return {"deleted_row_index": args.row_index}


def cmd_bulk_cells(args, cron: CronogramaXLSX) -> dict:
    try:
        ops = json.loads(args.ops_json)
    except json.JSONDecodeError as e:
        raise ValueError(f"--ops-json invalido: {e}")
    if not isinstance(ops, list):
        raise ValueError("--ops-json deve ser array")
    applied = []
    for op in ops:
        ridx = op.get("row_index")
        field = op.get("field")
        value = op.get("value")
        if not ridx or not field:
            raise ValueError(f"op invalida (precisa row_index + field): {op}")
        if field not in CANONICAL_COLUMN_ORDER:
            raise ValueError(f"campo invalido em op: {field}")
        cron.write_cell(ridx, field, value)
        applied.append({"row_index": ridx, "field": field, "value": value})
    return {"applied": applied, "count": len(applied)}


COMMANDS = {
    "write-clickup-id": cmd_write_clickup_id,
    "write-cell": cmd_write_cell,
    "append-row": cmd_append_row,
    "delete-row": cmd_delete_row,
    "bulk-cells": cmd_bulk_cells,
}


def main() -> int:
    p = argparse.ArgumentParser(description="Mutacoes no Cronograma.xlsx.")
    p.add_argument("--file", required=True, help="Caminho do Cronograma.xlsx live")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("write-clickup-id")
    s.add_argument("--row-index", type=int, required=True)
    s.add_argument("--clickup-id", required=True)

    s = sub.add_parser("write-cell")
    s.add_argument("--row-index", type=int, required=True)
    s.add_argument("--field", required=True)
    s.add_argument("--value", required=True)

    s = sub.add_parser("append-row")
    s.add_argument("--row-json", required=True)

    s = sub.add_parser("delete-row")
    s.add_argument("--row-index", type=int, required=True)

    s = sub.add_parser("bulk-cells")
    s.add_argument("--ops-json", required=True)

    args = p.parse_args()

    path = Path(args.file)
    if not path.exists():
        print(f"ERRO: arquivo nao existe: {path}", file=sys.stderr)
        return 1

    try:
        cron = CronogramaXLSX(path)
        cron.load()
        result = COMMANDS[args.cmd](args, cron)
        cron.save()
    except (ValueError, RuntimeError, FileNotFoundError) as e:
        print(f"ERRO ({args.cmd}): {e}", file=sys.stderr)
        return 1

    out = {"ok": True, "operation": args.cmd, **result}
    json.dump(out, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
