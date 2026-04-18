#!/usr/bin/env python3
"""
actions.py — CRUD orquestrado de acoes no plano (xlsx + ClickUp + changelog).

Subcomandos:
    create    Cria nova acao: append no xlsx + emite payload p/ Claude pushar no ClickUp
    update    Altera campo(s) de acao: aplica local + emite payload p/ Claude pushar
    delete    Remove acao: exclui local + emite ID p/ Claude apagar/arquivar no ClickUp
    comment   Registra comentario: emite payload p/ Claude criar no ClickUp + grava no changelog

Esta script faz a parte LOCAL e DETERMINISTICA. Claude (LLM) executa a parte
MCP (chamadas ClickUp) baseada no payload retornado, e depois grava o
clickup_id de volta via `xlsx_write.py write-clickup-id` se necessario.

Saidas (stdout, JSON) sempre tem `next_step` instruindo o Claude.

Uso:
    actions.py create --file <live.xlsx> --no 3.6 --tipo Acao --parent-no 3 \\
        --etapa "Nova acao" --responsavel "Bruno" \\
        --inicio "2026-04-25" --fim "2026-04-30" --entregavel "..."

    actions.py update --file <live.xlsx> --no 1.1.1 --field status --value in_progress

    actions.py delete --file <live.xlsx> --no 1.1.3 --mode archive   # ou delete

    actions.py comment --no 2.1.3 --text "@bruno revisei, OK p/ seguir" \\
        --clickup-id 86abc456 --changelog 4-status-report/changelog.md
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
    CANONICAL_COLUMN_ORDER,
    STATUS_LOCAL_VALIDOS,
    canonical_row,
    date_to_iso,
    parent_no,
    read_sync_state,
    update_sync_state,
)


def find_row_by_no(rows: list[dict], no: str) -> dict | None:
    for r in rows:
        if str(r.get("no", "")).strip() == no:
            return r
    return None


def cmd_create(args) -> dict:
    cron = CronogramaXLSX(args.file)
    cron.load()
    rows = cron.read_rows()

    # Valida que `no` ainda nao existe
    if find_row_by_no(rows, args.no):
        raise ValueError(f"No. '{args.no}' ja existe — use update ou escolha outro No.")

    # Valida parent (se especificado)
    parent = args.parent_no or parent_no(args.no)
    parent_clickup_id = None
    if parent:
        parent_row = find_row_by_no(rows, parent)
        if not parent_row:
            raise ValueError(f"parent No. '{parent}' nao existe na tabela")
        parent_clickup_id = str(parent_row.get("clickup_id", "") or "").strip() or None

    new_row = {
        "no": args.no,
        "tipo": args.tipo,
        "etapa": args.etapa,
        "responsavel": args.responsavel or "",
        "inicio_plan": args.inicio or "",
        "fim_plan": args.fim or "",
        "status": args.status or "",
        "entregavel": args.entregavel or "",
        "clickup_id": "",
    }
    cron.ensure_clickup_id_column()
    new_idx = cron.append_row(new_row)
    cron.save()

    # Resolve sync_state para list_id e status_map
    status_dir = Path(args.file).parent
    sstate = read_sync_state(status_dir)
    status_map = sstate.get("status_map", {})

    payload = {
        "list_id": sstate.get("clickup_list_id", ""),
        "name": new_row["etapa"],
        "description": new_row["entregavel"],
    }
    if new_row.get("inicio_plan"):
        payload["start_date"] = date_to_iso(new_row["inicio_plan"])
    if new_row.get("fim_plan"):
        payload["due_date"] = date_to_iso(new_row["fim_plan"])
    status_local = new_row.get("status", "")
    if status_local and status_local in status_map:
        payload["status"] = status_map[status_local]
    if parent_clickup_id:
        payload["parent_clickup_id"] = parent_clickup_id

    return {
        "ok": True,
        "operation": "create",
        "row_index": new_idx,
        "no": args.no,
        "parent_no": parent,
        "parent_clickup_id": parent_clickup_id,
        "payload": payload,
        "next_step": (
            f"Resolva responsavel '{new_row['responsavel']}' via mapping em CLAUDE.md "
            f"-> assignee_id. Chame clickup_create_task com payload (+ assignees). "
            f"Depois: xlsx_write.py write-clickup-id --file {args.file} "
            f"--row-index {new_idx} --clickup-id <ID>. E changelog_append.py --op create."
        ),
        "changelog_summary": f"No. {args.no} '{new_row['etapa'][:60]}' criado",
    }


def cmd_update(args) -> dict:
    cron = CronogramaXLSX(args.file)
    cron.load()
    rows = cron.read_rows()

    target = find_row_by_no(rows, args.no)
    if not target:
        raise ValueError(f"No. '{args.no}' nao encontrado")

    field = args.field
    if field not in CANONICAL_COLUMN_ORDER:
        raise ValueError(f"Campo invalido: {field}. Validos: {CANONICAL_COLUMN_ORDER}")
    if field == "clickup_id":
        raise ValueError("Use xlsx_write.py write-clickup-id para alterar clickup_id")

    canon_old = canonical_row(target)
    old_value = canon_old.get(field, "")
    new_value = args.value

    if field == "status" and new_value and new_value not in STATUS_LOCAL_VALIDOS:
        raise ValueError(f"Status invalido: '{new_value}'. Validos: {sorted(s for s in STATUS_LOCAL_VALIDOS if s)}")

    cron.write_cell(target["_row_index"], field, new_value)
    cron.save()

    cu_id = str(target.get("clickup_id", "") or "").strip() or None
    status_dir = Path(args.file).parent
    sstate = read_sync_state(status_dir)
    status_map = sstate.get("status_map", {})

    # Mapeia campo local -> campo ClickUp para o payload
    cu_field_map = {
        "etapa": "name",
        "entregavel": "description",
        "status": "status",
        "inicio_plan": "start_date",
        "fim_plan": "due_date",
    }
    cu_field = cu_field_map.get(field)
    cu_value = new_value
    if field == "status" and new_value in status_map:
        cu_value = status_map[new_value]
    if field in ("inicio_plan", "fim_plan"):
        cu_value = date_to_iso(new_value)

    push_payload = None
    if cu_id and cu_field:
        push_payload = {"clickup_id": cu_id, cu_field: cu_value}

    return {
        "ok": True,
        "operation": "update",
        "row_index": target["_row_index"],
        "no": args.no,
        "field": field,
        "old_value": old_value,
        "new_value": new_value,
        "clickup_id": cu_id,
        "push_payload": push_payload,
        "next_step": (
            "Sem clickup_id — apenas local; rode sync.py depois para reconciliar."
            if not cu_id else
            f"Chame clickup_update_task com push_payload. Depois changelog_append.py --op update."
        ),
        "changelog_summary": f"No. {args.no} {field}: '{old_value}' -> '{new_value}'",
    }


def cmd_delete(args) -> dict:
    cron = CronogramaXLSX(args.file)
    cron.load()
    rows = cron.read_rows()

    target = find_row_by_no(rows, args.no)
    if not target:
        raise ValueError(f"No. '{args.no}' nao encontrado")

    # Detectar filhos (linhas com `no` que comece com args.no + ".")
    prefix = args.no + "."
    children = [r for r in rows if str(r.get("no", "")).startswith(prefix)]

    if children and not args.cascade:
        raise ValueError(
            f"No. '{args.no}' tem {len(children)} filho(s). "
            f"Use --cascade para deletar todos juntos, ou apague os filhos primeiro."
        )

    cu_id = str(target.get("clickup_id", "") or "").strip() or None
    children_clickup_ids = [
        str(c.get("clickup_id", "") or "").strip()
        for c in children if str(c.get("clickup_id", "") or "").strip()
    ]

    # Deleta na ordem inversa (filhos primeiro) para nao bagunçar row indexes
    to_delete = sorted(
        [target] + (children if args.cascade else []),
        key=lambda r: r["_row_index"],
        reverse=True
    )
    for row in to_delete:
        cron.delete_row(row["_row_index"])
    cron.save()

    next_step_parts = []
    if cu_id or children_clickup_ids:
        all_ids = ([cu_id] if cu_id else []) + children_clickup_ids
        action = "clickup_delete_task" if args.mode == "delete" else "clickup_update_task (status=done)"
        next_step_parts.append(f"Para cada ID em {all_ids}, chame {action}.")
    next_step_parts.append("Depois changelog_append.py --op delete.")

    return {
        "ok": True,
        "operation": "delete",
        "no": args.no,
        "mode": args.mode,
        "cascade": args.cascade,
        "deleted_count": len(to_delete),
        "deleted_clickup_ids": ([cu_id] if cu_id else []) + children_clickup_ids,
        "next_step": " ".join(next_step_parts),
        "changelog_summary": f"No. {args.no} ({args.mode}, {len(to_delete)} linha(s))",
    }


def cmd_comment(args) -> dict:
    """
    Comentarios so existem no ClickUp + espelho no changelog.md.
    Nao mexem no xlsx. Esta op NAO requer --file (xlsx).
    """
    if not args.clickup_id:
        raise ValueError(
            "--clickup-id obrigatorio. Comentarios so existem em rows ja sincronizadas."
        )

    return {
        "ok": True,
        "operation": "comment",
        "no": args.no,
        "clickup_id": args.clickup_id,
        "text": args.text,
        "push_payload": {"task_id": args.clickup_id, "comment_text": args.text},
        "next_step": (
            f"Chame clickup_create_task_comment com push_payload. "
            f"Depois changelog_append.py --op comment --comment '{args.text}'."
        ),
        "changelog_summary": f"Comentario em No. {args.no}",
    }


def main() -> int:
    p = argparse.ArgumentParser(description="CRUD orquestrado do plano de acao.")
    sub = p.add_subparsers(dest="cmd", required=True)

    # create
    s = sub.add_parser("create")
    s.add_argument("--file", required=True)
    s.add_argument("--no", required=True, help="Numero hierarquico (ex: 3.6 ou 1.1.4)")
    s.add_argument("--tipo", required=True, choices=["Fase", "Ação", "Acao", "Etapas da Ação", "Etapas da Acao"])
    s.add_argument("--etapa", required=True, help="Titulo da acao")
    s.add_argument("--parent-no", default=None, help="Override do parent inferido pelo No.")
    s.add_argument("--responsavel", default="")
    s.add_argument("--inicio", default="", help="Data inicio (ISO ou BR)")
    s.add_argument("--fim", default="", help="Data fim (ISO ou BR)")
    s.add_argument("--status", default="", choices=["", "not_started", "in_progress", "blocked", "done"])
    s.add_argument("--entregavel", default="")

    # update
    s = sub.add_parser("update")
    s.add_argument("--file", required=True)
    s.add_argument("--no", required=True)
    s.add_argument("--field", required=True, choices=[c for c in CANONICAL_COLUMN_ORDER if c != "clickup_id"])
    s.add_argument("--value", required=True)

    # delete
    s = sub.add_parser("delete")
    s.add_argument("--file", required=True)
    s.add_argument("--no", required=True)
    s.add_argument("--mode", choices=["delete", "archive"], default="archive",
                   help="delete = apaga no ClickUp; archive = marca status=done")
    s.add_argument("--cascade", action="store_true",
                   help="Tambem deleta todos os filhos (No. comecando com <no>.)")

    # comment
    s = sub.add_parser("comment")
    s.add_argument("--no", required=True)
    s.add_argument("--clickup-id", required=True)
    s.add_argument("--text", required=True)

    args = p.parse_args()

    handlers = {
        "create": cmd_create,
        "update": cmd_update,
        "delete": cmd_delete,
        "comment": cmd_comment,
    }
    try:
        result = handlers[args.cmd](args)
    except (ValueError, RuntimeError, FileNotFoundError) as e:
        print(f"ERRO ({args.cmd}): {e}", file=sys.stderr)
        return 1

    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
