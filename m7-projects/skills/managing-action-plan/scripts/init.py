#!/usr/bin/env python3
"""
init.py — Setup de primeira rodada do plano de acao para um projeto.

Operacoes locais (puras, nao tocam ClickUp):
    1. Verifica que `<project>/4-status-report/` existe
    2. Verifica que `<project>/1-planning/Cronograma.xlsx` existe
    3. Verifica que `<project>/4-status-report/Cronograma.xlsx` NAO existe
       (a menos que --force seja passado, indicando re-init confirmado)
    4. Copia baseline -> live
    5. Adiciona coluna `ClickUp ID` ao live xlsx
    6. Cria `4-status-report/changelog.md` (template)
    7. Cria `4-status-report/.sync-state.json` (initial)
    8. Parseia o live xlsx e emite plano de push em ordem topologica
       (parents antes de children) para Claude usar com clickup_create_task

Quem chama esta skill (Claude) e responsavel por:
    A. Pedir/criar a List no ClickUp e passar `--clickup-list-id` aqui
    B. Apos init.py rodar, iterar push_plan e chamar clickup_create_task
       para cada linha, depois chamar `xlsx_write.py write-clickup-id`
       para cada ID retornado
    C. Apos todos os pushes, chamar `sync.py finalize-init` para gravar
       last_sync_hash em .sync-state.json

Uso:
    python3 init.py --project-dir ./meu-projeto --clickup-list-id 901xxxxxxxxx
    python3 init.py --project-dir ./meu-projeto --clickup-list-id 901xxx --force

Saida (stdout, JSON):
    {
      "ok": true,
      "paths": {
        "baseline": "...",
        "live": "...",
        "changelog": "...",
        "sync_state": "..."
      },
      "stats": {"total": 265, "fases": 6, "acoes": 70, "etapas": 189},
      "push_plan": [                          # Em ordem topologica
        {
          "_row_index": 5,
          "no": "1",
          "tipo": "Fase",
          "etapa": "FASE 1 — PLANEJAMENTO",
          "responsavel": "Bruno",
          "parent_no": "",                    # vazio = root
          "payload": {                        # Pronto para clickup_create_task
            "list_id": "901xxx",
            "name": "FASE 1 — PLANEJAMENTO",
            "description": "...",
            "status": null,                   # ainda nao mapeado se vazio
            "start_date": "2026-03-27",
            "due_date": "2026-04-14",
            "parent_clickup_id": null         # filled by Claude when parent has ID
          }
        },
        ...
      ],
      "warnings": [...]
    }

Exit codes:
    0 — sucesso
    1 — erro fatal (paths invalidos, deps faltando, baseline nao existe)
    2 — re-init bloqueado (live ja existe e --force nao passado)
"""

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _lib import (  # noqa: E402
    CronogramaXLSX,
    STATUS_MAP_DEFAULT,
    canonical_row,
    date_to_iso,
    hash_table,
    parent_no,
    read_sync_state,
    sync_state_path,
    update_sync_state,
    write_sync_state,
    SYNC_STATE_DEFAULT,
)

CHANGELOG_HEADER = """# Changelog — Plano de Acao{project_suffix}

> Registro cronologico (reverse, mais novo no topo) de todas as operacoes
> sobre o plano de acao. Mantido automaticamente por `managing-action-plan`.
> Append-only: nunca editar entries existentes manualmente.

---
"""


def topological_sort(rows: list[dict]) -> list[dict]:
    """
    Ordena linhas de forma que pais venham antes de filhos.
    Usa o `No.` (numerico hierarquico) como chave.

    "1" antes de "1.1" antes de "1.1.1", "1.10" depois de "1.9", etc.
    """
    def key(row):
        no = str(row.get("no", "") or "")
        try:
            return tuple(int(p) for p in no.split("."))
        except ValueError:
            return (0,)
    return sorted(rows, key=key)


def build_payload(row: dict, list_id: str, status_map: dict, project_year: int | None) -> dict:
    """Constroi payload para clickup_create_task a partir de uma linha canonica."""
    canon = canonical_row(row, project_year)
    status_local = canon.get("status", "")
    status_remote = status_map.get(status_local) if status_local else None

    payload = {
        "list_id": list_id,
        "name": canon.get("etapa", "").strip() or "(sem titulo)",
        "description": canon.get("entregavel", "") or "",
    }
    if status_remote:
        payload["status"] = status_remote
    if canon.get("inicio_plan"):
        payload["start_date"] = canon["inicio_plan"]
    if canon.get("fim_plan"):
        payload["due_date"] = canon["fim_plan"]
    return payload


def main() -> int:
    p = argparse.ArgumentParser(description="Inicializa plano de acao do projeto.")
    p.add_argument("--project-dir", required=True,
                   help="Raiz do projeto (contem 1-planning/ e 4-status-report/)")
    p.add_argument("--clickup-list-id", required=True,
                   help="ID da List no ClickUp (Claude pergunta/cria antes)")
    p.add_argument("--force", action="store_true",
                   help="Permite re-init: sobrescreve live xlsx + changelog + sync-state")
    p.add_argument("--default-year", type=int, default=None,
                   help="Ano default para datas BR sem ano (ex: '02/abr')")
    p.add_argument("--project-name", default="",
                   help="Nome do projeto (vai no header do changelog)")
    args = p.parse_args()

    proj = Path(args.project_dir).resolve()
    if not proj.exists() or not proj.is_dir():
        print(f"ERRO: project-dir nao existe ou nao e diretorio: {proj}", file=sys.stderr)
        return 1

    planning_dir = proj / "1-planning"
    status_dir = proj / "4-status-report"
    baseline = planning_dir / "Cronograma.xlsx"
    live = status_dir / "Cronograma.xlsx"
    changelog = status_dir / "changelog.md"
    sync_state_file = sync_state_path(status_dir)

    if not status_dir.exists():
        print(f"ERRO: pasta nao existe: {status_dir}. Inicialize o projeto com `initializing-project` primeiro.", file=sys.stderr)
        return 1

    if not baseline.exists():
        print(f"ERRO: baseline nao existe: {baseline}. Construa o cronograma com `building-project-plan` primeiro.", file=sys.stderr)
        return 1

    if live.exists() and not args.force:
        print(
            f"ERRO: arquivo live ja existe: {live}. "
            f"Use --force para re-init (vai sobrescrever changelog.md e .sync-state.json tambem).",
            file=sys.stderr
        )
        return 2

    warnings: list[str] = []

    # 4. Copia baseline -> live
    shutil.copy2(baseline, live)

    # 5. Adiciona coluna ClickUp ID
    cron = CronogramaXLSX(live)
    cron.load()
    cu_col = cron.ensure_clickup_id_column()
    cron.save()

    # Re-load to get fresh state with new column registered
    cron = CronogramaXLSX(live)
    cron.load()

    rows = cron.read_rows()
    if not rows:
        warnings.append("baseline parseou com zero linhas de dados — verifique o xlsx")

    # 6. Cria changelog.md
    if changelog.exists() and not args.force:
        warnings.append(f"changelog.md ja existia e foi preservado (use --force para resetar)")
    else:
        suffix = f" — {args.project_name}" if args.project_name else ""
        changelog.write_text(CHANGELOG_HEADER.format(project_suffix=suffix), encoding="utf-8")

    # 7. Cria .sync-state.json (inicial — ainda sem last_sync_hash, sera gravado por finalize)
    initial_state = dict(SYNC_STATE_DEFAULT)
    initial_state["clickup_list_id"] = args.clickup_list_id
    initial_state["status_map"] = STATUS_MAP_DEFAULT
    write_sync_state(status_dir, initial_state)

    # 8. Push plan em ordem topologica
    rows_sorted = topological_sort(rows)
    push_plan: list[dict] = []
    for row in rows_sorted:
        canon = canonical_row(row, args.default_year)
        push_plan.append({
            "_row_index": row.get("_row_index", -1),
            "no": canon["no"],
            "tipo": canon["tipo"],
            "etapa": canon["etapa"],
            "responsavel": canon["responsavel"],
            "parent_no": parent_no(canon["no"]),
            "payload": build_payload(row, args.clickup_list_id, STATUS_MAP_DEFAULT, args.default_year),
        })

    payload = {
        "ok": True,
        "paths": {
            "baseline": str(baseline),
            "live": str(live),
            "changelog": str(changelog),
            "sync_state": str(sync_state_file),
        },
        "clickup_id_column_index": cu_col,
        "stats": {
            "total": len(rows),
            "fases": sum(1 for r in rows if str(r.get("tipo", "")).strip() == "Fase"),
            "acoes": sum(1 for r in rows if str(r.get("tipo", "")).strip() in ("Ação", "Acao")),
            "etapas": sum(1 for r in rows if str(r.get("tipo", "")).strip() in ("Etapas da Ação", "Etapas da Acao")),
        },
        "push_plan": push_plan,
        "warnings": warnings,
        "next_step": (
            "Para cada item de push_plan (em ordem): "
            "(1) resolva responsavel via mapping em CLAUDE.md -> assignee_id, "
            "(2) se parent_no nao vazio, busque clickup_id do parent ja pushado, "
            "(3) chame clickup_create_task com payload + assignees + parent (se houver), "
            "(4) chame `xlsx_write.py write-clickup-id --file <live> --row-index N --clickup-id ID`. "
            "Apos todos os pushes, rode `sync.py finalize-init --project-dir <proj>`."
        ),
    }

    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2, default=str)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
