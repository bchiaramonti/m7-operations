#!/usr/bin/env python3
"""
sync.py — Three-way diff e plano de sincronizacao Cronograma.xlsx <-> ClickUp.

Esta script faz a parte LOCAL do sync. Ele NAO chama MCP — o Claude (LLM)
chama `clickup_filter_tasks` antes (para alimentar --remote-json) e
`clickup_create_task` / `clickup_update_task` / `clickup_delete_task`
depois (para aplicar o plano emitido).

Subcomandos:
    prepare        Compara local vs remote vs baseline; emite plano de sync
    finalize       Pos-aplicacao: refresca baselines + last_sync_hash
    finalize-init  Variante para o final do init (apenas hash baseline, sem push)

Three-way diff:
    baseline = hash + canonical de cada row no ultimo sync ok (.sync-state.json)
    local    = estado atual do Cronograma.xlsx
    remote   = estado atual do ClickUp (Claude passou via --remote-json)

Cada row e classificada em uma das categorias:
    UNCHANGED                         noop
    LOCAL_ONLY_CHANGED                push update
    REMOTE_ONLY_CHANGED               pull (write local)
    BOTH_CHANGED                      aplica field rules; campos prompt-type viram conflicts
    LOCAL_ONLY_NEW (sem clickup_id)   push create
    REMOTE_ONLY_NEW                   pull (append local row)
    LOCAL_ONLY_DELETED                push delete (ou archive — depende mode)
    REMOTE_ONLY_DELETED               prompt: recriar local ou remover mapping
    ORPHAN                            clickup_id local nao existe no remote (deletado externo)

Field resolution rules (BOTH_CHANGED):
    etapa (name)            -> conflict prompt (LLM sugere merge)
    entregavel (description) -> conflict prompt
    status                  -> remote-wins (ClickUp e SSOT operacional)
    inicio_plan/fim_plan    -> local-wins (estrutura e responsabilidade local)
    responsavel/assignee    -> remote-wins (gestao operacional no ClickUp)
    inicio_real/fim_real    -> remote-wins (verdade operacional)

Uso:
    # Apos clickup_filter_tasks(list_id) -> remote_tasks.json:
    python3 sync.py prepare \\
        --file 4-status-report/Cronograma.xlsx \\
        --remote-json /tmp/remote_tasks.json

    # Apos init.py + push inicial concluido por Claude:
    python3 sync.py finalize-init --file 4-status-report/Cronograma.xlsx

    # Apos plano do prepare ter sido aplicado por Claude:
    python3 sync.py finalize \\
        --file 4-status-report/Cronograma.xlsx \\
        --remote-json /tmp/remote_tasks_after.json
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
    HASH_FIELDS,
    canonical_row,
    date_to_iso,
    hash_row,
    hash_table,
    parent_no,
    read_sync_state,
    update_sync_state,
    write_sync_state,
)


# ---------------------------------------------------------------------------
# Mapping ClickUp -> canonical local
# ---------------------------------------------------------------------------

def remote_to_canonical(task: dict, status_map_inverse: dict[str, str]) -> dict:
    """
    Converte um task ClickUp (formato MCP clickup_filter_tasks/get_task)
    para o schema canonico local. NAO inclui `no` nem `tipo` (esses ficam
    com os valores locais; ClickUp nao tem nocao deles).
    """
    cu_status = task.get("status", "")
    if isinstance(cu_status, dict):
        cu_status = cu_status.get("status", "")
    local_status = status_map_inverse.get(str(cu_status).lower(), "")

    assignees = task.get("assignees") or []
    responsavel = ""
    if assignees:
        first = assignees[0]
        if isinstance(first, dict):
            responsavel = first.get("username") or first.get("email") or ""
        else:
            responsavel = str(first)

    return {
        "etapa": task.get("name", "") or "",
        "responsavel": responsavel,
        "inicio_plan": _ts_to_iso(task.get("start_date")),
        "fim_plan": _ts_to_iso(task.get("due_date")),
        "inicio_real": _ts_to_iso(task.get("date_started")),
        "fim_real": _ts_to_iso(task.get("date_done")),
        "status": local_status,
        "entregavel": task.get("description", "") or task.get("text_content", "") or "",
    }


def _ts_to_iso(value) -> str:
    """Aceita ms epoch (str ou int) ou ISO; devolve YYYY-MM-DD ou ''.

    Usa UTC para evitar drift de TZ entre maquinas — ClickUp armazena ms epoch
    UTC, e queremos o mesmo dia em qualquer TZ que o sync rode.
    """
    if not value:
        return ""
    if isinstance(value, str):
        try:
            ms = int(value)
            return dt.datetime.fromtimestamp(ms / 1000, tz=dt.timezone.utc).strftime("%Y-%m-%d")
        except ValueError:
            return date_to_iso(value)
    if isinstance(value, (int, float)):
        try:
            return dt.datetime.fromtimestamp(value / 1000, tz=dt.timezone.utc).strftime("%Y-%m-%d")
        except (OSError, ValueError):
            return ""
    return ""


# ---------------------------------------------------------------------------
# Field resolution rules
# ---------------------------------------------------------------------------

# Quem vence em BOTH_CHANGED, por campo
FIELD_RULES = {
    "etapa":       "conflict",   # LLM/usuario decide
    "entregavel":  "conflict",
    "status":      "remote",
    "inicio_plan": "local",
    "fim_plan":    "local",
    "responsavel": "remote",
    "inicio_real": "remote",
    "fim_real":    "remote",
}

# Mapeia campo canonico -> nome do campo no payload do ClickUp (para push)
LOCAL_TO_CU_FIELD = {
    "etapa":       "name",
    "entregavel":  "description",
    "status":      "status",
    "inicio_plan": "start_date",
    "fim_plan":    "due_date",
    "responsavel": "assignees",  # tratamento especial: array de IDs
    "inicio_real": "date_started",
    "fim_real":    "date_done",
}


# ---------------------------------------------------------------------------
# Diff core
# ---------------------------------------------------------------------------

def diff_field_set(local: dict, remote: dict, baseline: dict | None) -> dict[str, dict]:
    """
    Para cada campo em HASH_FIELDS, retorna se local e/ou remote mudaram vs baseline.
    Se baseline e None (nunca foi sincronizado), tudo conta como local-only-changed.

    Retorna: {field: {"local_changed": bool, "remote_changed": bool, "local_v": ..., "remote_v": ..., "baseline_v": ...}}
    """
    result: dict[str, dict] = {}
    for field in HASH_FIELDS:
        lv = local.get(field, "")
        rv = remote.get(field, "")
        bv = (baseline or {}).get(field, "")
        result[field] = {
            "local_changed": (lv != bv) if baseline else (lv != ""),
            "remote_changed": (rv != bv) if baseline else False,
            "local_v": lv,
            "remote_v": rv,
            "baseline_v": bv,
        }
    return result


def classify_row(local_row: dict, remote_task: dict | None,
                 baseline: dict | None, status_map_inverse: dict) -> dict:
    """
    Classifica uma linha em UNCHANGED / LOCAL_ONLY_CHANGED / REMOTE_ONLY_CHANGED /
    BOTH_CHANGED / ORPHAN.

    Retorna: {category, field_diffs, resolutions, conflicts}
    """
    canon_local = canonical_row(local_row)
    canon_remote_partial = remote_to_canonical(remote_task, status_map_inverse) if remote_task else {}

    # Preenche os campos que ClickUp nao tem (no, tipo, clickup_id) com valor local
    canon_remote = dict(canon_local)
    canon_remote.update(canon_remote_partial)

    # baseline e armazenado como {hash, canonical: {...}}; extrai canonical
    baseline_canonical = baseline.get("canonical") if baseline else None
    diffs = diff_field_set(canon_local, canon_remote, baseline_canonical)
    has_local = any(d["local_changed"] for d in diffs.values())
    has_remote = any(d["remote_changed"] for d in diffs.values())

    if not has_local and not has_remote:
        category = "UNCHANGED"
    elif has_local and not has_remote:
        category = "LOCAL_ONLY_CHANGED"
    elif has_remote and not has_local:
        category = "REMOTE_ONLY_CHANGED"
    else:
        category = "BOTH_CHANGED"

    resolutions: dict[str, dict] = {}
    conflicts: list[dict] = []

    for field, d in diffs.items():
        if not (d["local_changed"] or d["remote_changed"]):
            continue
        rule = FIELD_RULES.get(field, "local")
        if d["local_changed"] and not d["remote_changed"]:
            resolutions[field] = {"winner": "local", "value": d["local_v"]}
        elif d["remote_changed"] and not d["local_changed"]:
            resolutions[field] = {"winner": "remote", "value": d["remote_v"]}
        else:  # both changed
            if rule == "conflict":
                conflicts.append({
                    "field": field,
                    "local": d["local_v"],
                    "remote": d["remote_v"],
                    "baseline": d["baseline_v"],
                })
                resolutions[field] = {"winner": "PROMPT", "value": None}
            elif rule == "local":
                resolutions[field] = {"winner": "local", "value": d["local_v"]}
            else:  # remote
                resolutions[field] = {"winner": "remote", "value": d["remote_v"]}

    return {
        "category": category,
        "field_diffs": diffs,
        "resolutions": resolutions,
        "conflicts": conflicts,
    }


# ---------------------------------------------------------------------------
# Plan builders
# ---------------------------------------------------------------------------

def build_plan(local_rows: list[dict], remote_tasks: list[dict],
               baselines: dict, status_map: dict) -> dict:
    """Plano completo de sync."""
    status_map_inverse = {v.lower(): k for k, v in status_map.items()}

    # Indexa remote por clickup_id
    remote_by_id = {str(t.get("id")): t for t in remote_tasks if t.get("id")}

    plan = {
        "push_creates": [],     # local sem clickup_id
        "push_updates": [],     # local mudou
        "push_deletes": [],     # remote orfao (existe no baseline mas nao local)
        "pull_creates": [],     # remote sem correspondente local
        "pull_updates": [],     # remote mudou (campos remote-wins)
        "conflicts": [],        # both changed em campos prompt-type
        "orphans": [],          # local tem clickup_id que nao existe no remote
        "unchanged_count": 0,
    }

    seen_remote_ids: set[str] = set()

    for row in local_rows:
        cu_id = str(row.get("clickup_id", "") or "").strip()
        canon = canonical_row(row)

        if not cu_id:
            # LOCAL_ONLY_NEW — push create
            plan["push_creates"].append({
                "_row_index": row.get("_row_index"),
                "no": canon["no"],
                "tipo": canon["tipo"],
                "etapa": canon["etapa"],
                "responsavel": canon["responsavel"],
                "parent_no": parent_no(canon["no"]),
                "fields": canon,
            })
            continue

        if cu_id not in remote_by_id:
            # ORPHAN — clickup_id local nao existe no remote
            plan["orphans"].append({
                "_row_index": row.get("_row_index"),
                "no": canon["no"],
                "clickup_id": cu_id,
                "etapa": canon["etapa"],
            })
            continue

        seen_remote_ids.add(cu_id)
        remote_task = remote_by_id[cu_id]
        baseline = baselines.get(cu_id)
        cls = classify_row(row, remote_task, baseline, status_map_inverse)

        if cls["category"] == "UNCHANGED":
            plan["unchanged_count"] += 1
            continue

        # Coleta resolucoes que requerem push (winner=local) e pull (winner=remote).
        # Filtra: so campos com mapeamento ClickUp vao para push (no/tipo sao locais).
        push_fields = {}
        pull_fields = {}
        for field, res in cls["resolutions"].items():
            if res["winner"] == "local" and field in LOCAL_TO_CU_FIELD:
                push_fields[field] = res["value"]
            elif res["winner"] == "remote":
                # Pull aplica em qualquer campo (no/tipo viriam do remote so se
                # houvesse esse mapeamento — atualmente nao, mas e seguro)
                pull_fields[field] = res["value"]

        if push_fields:
            plan["push_updates"].append({
                "_row_index": row.get("_row_index"),
                "no": canon["no"],
                "clickup_id": cu_id,
                "fields": push_fields,
                "category": cls["category"],
            })
        if pull_fields:
            plan["pull_updates"].append({
                "_row_index": row.get("_row_index"),
                "no": canon["no"],
                "clickup_id": cu_id,
                "fields": pull_fields,
                "category": cls["category"],
            })
        if cls["conflicts"]:
            plan["conflicts"].append({
                "_row_index": row.get("_row_index"),
                "no": canon["no"],
                "clickup_id": cu_id,
                "etapa": canon["etapa"],
                "conflicts": cls["conflicts"],
            })

    # Remote-only-new: tasks no ClickUp que nao tem clickup_id local
    for cu_id, task in remote_by_id.items():
        if cu_id in seen_remote_ids:
            continue
        # Verifica se este ID esta no baseline — se sim, era nosso e foi deletado no remote (ja tratamos como orphan? na verdade nao, orphan e o caso oposto). Se nao, e novo no remote.
        if cu_id in baselines:
            # era nosso, mas a linha local foi removida — push delete
            plan["push_deletes"].append({
                "clickup_id": cu_id,
                "name": task.get("name", ""),
            })
        else:
            plan["pull_creates"].append({
                "clickup_id": cu_id,
                "name": task.get("name", ""),
                "fields": remote_to_canonical(task, status_map_inverse),
            })

    return plan


def update_baselines_from_xlsx(local_rows: list[dict]) -> dict:
    """Recalcula baselines (hash + canonical) por clickup_id."""
    out: dict[str, dict] = {}
    for row in local_rows:
        cu_id = str(row.get("clickup_id", "") or "").strip()
        if not cu_id:
            continue
        canon = canonical_row(row)
        out[cu_id] = {
            "hash": hash_row(row),
            "canonical": {f: canon.get(f, "") for f in HASH_FIELDS},
        }
    return out


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------

def cmd_prepare(args) -> dict:
    cron = CronogramaXLSX(args.file)
    cron.load()
    local_rows = cron.read_rows()

    remote_path = Path(args.remote_json)
    if not remote_path.exists():
        raise FileNotFoundError(f"--remote-json nao existe: {remote_path}")
    remote_data = json.loads(remote_path.read_text(encoding="utf-8"))
    if isinstance(remote_data, dict) and "tasks" in remote_data:
        remote_tasks = remote_data["tasks"]
    elif isinstance(remote_data, list):
        remote_tasks = remote_data
    else:
        raise ValueError("--remote-json deve ser array ou {tasks: [...]}")

    status_dir = Path(args.file).parent
    sstate = read_sync_state(status_dir)
    baselines = sstate.get("baselines", {})
    status_map = sstate.get("status_map", {})

    plan = build_plan(local_rows, remote_tasks, baselines, status_map)

    summary = {
        "push_creates": len(plan["push_creates"]),
        "push_updates": len(plan["push_updates"]),
        "push_deletes": len(plan["push_deletes"]),
        "pull_creates": len(plan["pull_creates"]),
        "pull_updates": len(plan["pull_updates"]),
        "conflicts": len(plan["conflicts"]),
        "orphans": len(plan["orphans"]),
        "unchanged": plan["unchanged_count"],
    }
    has_changes = any(v > 0 for k, v in summary.items() if k != "unchanged")

    return {
        "ok": True,
        "operation": "prepare",
        "summary": summary,
        "has_changes": has_changes,
        "plan": plan,
        "next_step": (
            "Plano sem mudancas — nada a sincronizar." if not has_changes else
            "Resolva conflicts via prompts ao usuario; depois aplique push_creates "
            "(usar clickup_create_task em ordem topologica), push_updates "
            "(clickup_update_task), push_deletes (clickup_delete_task ou archive). "
            "Para pull_creates: xlsx_write.py append-row + write-clickup-id. "
            "Para pull_updates: xlsx_write.py bulk-cells. "
            "No final: sync.py finalize."
        ),
    }


def cmd_finalize_init(args) -> dict:
    """Apos init + todos os pushes iniciais. Apenas grava baseline."""
    cron = CronogramaXLSX(args.file)
    cron.load()
    local_rows = cron.read_rows()

    baselines = update_baselines_from_xlsx(local_rows)
    status_dir = Path(args.file).parent
    table_h = hash_table(local_rows)
    now_iso = dt.datetime.now().replace(microsecond=0).isoformat()

    state = read_sync_state(status_dir)
    state["baselines"] = baselines
    state["last_sync"] = now_iso
    state["last_sync_hash"] = table_h
    state["sync_pending"] = False
    state.setdefault("history", []).append({
        "timestamp": now_iso,
        "operation": "finalize-init",
        "rows_baselined": len(baselines),
    })
    write_sync_state(status_dir, state)

    return {
        "ok": True,
        "operation": "finalize-init",
        "rows_baselined": len(baselines),
        "table_hash": table_h,
        "last_sync": now_iso,
    }


def cmd_finalize(args) -> dict:
    """Apos um sync (prepare + apply). Refresca baselines do estado pos-sync."""
    cron = CronogramaXLSX(args.file)
    cron.load()
    local_rows = cron.read_rows()

    baselines = update_baselines_from_xlsx(local_rows)
    status_dir = Path(args.file).parent
    table_h = hash_table(local_rows)
    now_iso = dt.datetime.now().replace(microsecond=0).isoformat()

    state = read_sync_state(status_dir)
    state["baselines"] = baselines
    state["last_sync"] = now_iso
    state["last_sync_hash"] = table_h
    state["sync_pending"] = False
    state.setdefault("history", []).append({
        "timestamp": now_iso,
        "operation": "finalize",
        "rows_baselined": len(baselines),
    })
    write_sync_state(status_dir, state)

    return {
        "ok": True,
        "operation": "finalize",
        "rows_baselined": len(baselines),
        "table_hash": table_h,
        "last_sync": now_iso,
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Three-way sync Cronograma.xlsx <-> ClickUp.")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("prepare")
    s.add_argument("--file", required=True)
    s.add_argument("--remote-json", required=True,
                   help="JSON file com array de tasks ClickUp (clickup_filter_tasks output)")

    s = sub.add_parser("finalize-init")
    s.add_argument("--file", required=True)

    s = sub.add_parser("finalize")
    s.add_argument("--file", required=True)

    args = p.parse_args()

    handlers = {
        "prepare": cmd_prepare,
        "finalize-init": cmd_finalize_init,
        "finalize": cmd_finalize,
    }
    try:
        result = handlers[args.cmd](args)
    except (FileNotFoundError, ValueError, RuntimeError) as e:
        print(f"ERRO ({args.cmd}): {e}", file=sys.stderr)
        return 1

    json.dump(result, sys.stdout, ensure_ascii=False, indent=2, default=str)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
