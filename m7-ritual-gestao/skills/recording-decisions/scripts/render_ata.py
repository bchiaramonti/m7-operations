"""
render_ata.py — Renderiza ata HTML a partir do template `ata-ritual.tmpl.html`
e do plan-preview.json gerado pela Fase 4.5 da skill recording-decisions.

Resolve a incompatibilidade entre o template Handlebars-flavored
(`{{#each X}}...{{/each}}`, `{{#if X}}...{{/if}}`) e o renderer Python
disponivel (`chevron`, que so fala Mustache puro `{{#X}}...{{/X}}`).

Pre-processamento:
  - `{{#each X}}...{{/each}}` -> `{{#X}}...{{/X}}`
  - `{{#if X}}...{{/if}}`     -> `{{#X}}...{{/X}}`
  - Casamento via stack (nominal close `each`/`if` resolve para o open mais recente)

Adicionado em 3.8.4 (2026-05-26) para substituir scripts ad hoc em /tmp/.

Uso CLI:
    python3 render_ata.py \\
        --plan-preview-json {OUTPUT_DIR}/plan-preview.json \\
        --template {SKILL_DIR}/templates/ata-ritual.tmpl.html \\
        --output {OUTPUT_DIR}/ata-ritual-{data}.html \\
        --nivel N3 \\
        --vertical Consorcios \\
        --data 2026-05-26 \\
        --participantes "Pedro V., Joel F., Douglas S., Tereza B., Sarah C." \\
        --duracao "~36 min" \\
        --wbr-referencia "Maio 2026, semana 5 (MTD)"

Dependencias: chevron (`pip install chevron`).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import chevron
except ImportError:
    print(
        "ERRO: pacote 'chevron' nao instalado. Rode: pip install chevron",
        file=sys.stderr,
    )
    sys.exit(2)


CLICKUP_BASE = "https://app.clickup.com/t/"

SCHEMA_VERSION_REQUIRED = "2.0"


def _assert_schema_v2(plan: dict) -> None:
    """Gatekeeper v3.9.0: aborta se plan-preview.json nao for schema v2.0.

    Bloqueia render em commit quando decision-recorder emite schema antigo (v1.0)
    ou formato adaptado. Forca canonicalizacao em todos os ciclos novos.
    """
    v = plan.get("schema_version")
    if v != SCHEMA_VERSION_REQUIRED:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": (
                        f"plan-preview.json schema_version={v!r}, esperado "
                        f"{SCHEMA_VERSION_REQUIRED!r}. Re-execute "
                        "/m7-ritual-gestao:record-decisions {vertical}{ {sub}} "
                        "para regerar com decision-recorder v2.0."
                    ),
                    "schema_doc": "skills/recording-decisions/references/plan-preview-schema.md",
                },
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        sys.exit(2)


# ---------------------------------------------------------------------------
# Handlebars -> Mustache (pre-processador)
# ---------------------------------------------------------------------------

def convert_handlebars_to_mustache(src: str) -> str:
    """Converte `{{#each X}}...{{/each}}` e `{{#if X}}...{{/if}}` para Mustache puro
    (`{{#X}}...{{/X}}`). Faz casamento via stack — close nominal (`each`/`if`)
    resolve para o nome do open mais recente.

    Tolerante a templates ja Mustache puro (no-op nesses casos).
    """
    pattern_open = re.compile(r"\{\{\s*(#each|#if|/each|/if)\s+?([^}]*)\}\}")
    out = []
    stack = []
    pos = 0
    for m in pattern_open.finditer(src):
        out.append(src[pos:m.start()])
        kind = m.group(1).strip()
        name = m.group(2).strip()
        if kind in ("#each", "#if"):
            stack.append(name)
            out.append("{{#" + name + "}}")
        else:  # /each ou /if (com nome adjacente)
            if not stack:
                raise ValueError(f"close sem open: {m.group()}")
            section = stack.pop()
            out.append("{{/" + section + "}}")
        pos = m.end()
    out.append(src[pos:])
    first_pass = "".join(out)

    # Segunda passada: trata `{{/each}}` e `{{/if}}` SEM nome adjacente
    fallback = re.compile(r"\{\{\s*/(each|if)\s*\}\}")
    if not fallback.search(first_pass):
        return first_pass

    # Re-processa do zero contemplando opens E closes (com/sem nome)
    p2 = re.compile(r"\{\{\s*#([^}\s]+)\s*\}\}|\{\{\s*/([^}\s]+)\s*\}\}")
    out2 = []
    stack2 = []
    pos2 = 0
    for m in p2.finditer(first_pass):
        out2.append(first_pass[pos2:m.start()])
        if m.group(1):  # open
            name = m.group(1)
            stack2.append(name)
            out2.append("{{#" + name + "}}")
        else:  # close
            closing_kw = m.group(2)
            if closing_kw in ("each", "if") and stack2:
                name = stack2.pop()
                out2.append("{{/" + name + "}}")
            else:
                if stack2 and stack2[-1] == closing_kw:
                    stack2.pop()
                out2.append("{{/" + closing_kw + "}}")
        pos2 = m.end()
    out2.append(first_pass[pos2:])
    return "".join(out2)


# ---------------------------------------------------------------------------
# Plan-preview -> chevron data dict
# ---------------------------------------------------------------------------

PRIO_CLASS = {
    # Schema v2.0 canonico (urgent/high/normal/low)
    "urgent": "critical",
    "high": "high",
    "normal": "medium",
    "low": "low",
    # Schema v1.0 (compatibilidade so para historicos pre-v2.0; nao usado em
    # ciclos novos pois _assert_schema_v2 bloqueia)
    "critica": "critical",
    "alta": "high",
    "media": "medium",
    "baixa": "low",
}

STATUS_CLASS = {
    "pendente": "pending",
    "atrasada": "delayed",
    "concluida": "completed",
    "em andamento": "in-progress",
}


def _prio_class(p: str) -> str:
    return PRIO_CLASS.get((p or "").lower(), "medium")


def _status_class(s: str) -> str:
    return STATUS_CLASS.get((s or "").lower(), "pending")


def build_template_data(
    plan: dict,
    *,
    nivel: str,
    vertical: str,
    data: str,
    participantes: str,
    duracao: str,
    wbr_referencia: str,
    timestamp: str | None = None,
) -> dict:
    """Constroi o dict de dados para o template a partir do plan-preview.json."""
    ts = timestamp or datetime.now(timezone.utc).astimezone().isoformat(timespec="minutes")

    # Decisoes (schema v2.0: ata_id + titulo + responsavel; SEM prazo)
    decisoes_data: list[dict] = []
    for d in (plan.get("decisoes") or []):
        decisoes_data.append({
            "decisao_id": d.get("ata_id") or "",
            "decisao_titulo": d.get("titulo") or "",
            "decisao_responsavel": d.get("responsavel") or "",
            "decisao_prazo": "",  # v2.0: decisoes nao tem prazo (memory feedback_decisoes_sem_prazo)
        })

    # Round 2: decisoes_recorrentes_adicionadas_round2 (3.8.3+, opcional em v2.0)
    for d in (plan.get("decisoes_recorrentes_adicionadas_round2") or []):
        decisoes_data.append({
            "decisao_id": d.get("ata_id") or "",
            "decisao_titulo": d.get("titulo") or "",
            "decisao_responsavel": d.get("responsavel") or "",
            "decisao_prazo": "",  # v2.0
        })

    # Contramedidas (schema v2.0: campos TOP-LEVEL canonicos sem fallback)
    contramedidas_data: list[dict] = []
    for cm in (plan.get("contramedidas_novas") or []):
        priority = cm.get("priority_label") or "normal"
        contramedidas_data.append({
            "cm_id": cm.get("ata_id", ""),  # mantido no dict; template 3.8.3+ nao renderiza coluna
            "cm_titulo": cm.get("name") or "",
            "cm_indicador": cm.get("indicador_impactado") or "",
            "cm_responsavel": cm.get("responsavel_externo_label") or "",
            "cm_prazo": cm.get("due_date") or "prazo a definir",
            "cm_prioridade": priority,
            "cm_prioridade_class": _prio_class(priority),
            "cm_status": "Aberta",
        })

    # Acoes atualizadas (schema v2.0: clickup_id + name_humano + before/after + comment)
    acoes_data: list[dict] = []
    for ta in (plan.get("tasks_atualizadas") or []):
        cid = ta.get("clickup_id") or ""
        titulo = ta.get("name_humano") or ""
        before = ta.get("before") or {}
        after = ta.get("after") or {}

        status_change = after.get("status") if before.get("status") != after.get("status") else None

        due_change = None
        if before.get("due_date") and after.get("due_date") and before["due_date"] != after["due_date"]:
            due_change = (before["due_date"], after["due_date"])

        if status_change:
            campo = "status"
            antes = before.get("status") or ""
            depois = status_change
            # Se também houve mudança de prazo, adicionar no depois
            if due_change:
                depois = f"{depois} (prazo {due_change[0]} → {due_change[1]})"
        elif due_change:
            campo = "prazo"
            antes = due_change[0]
            depois = due_change[1]
        else:
            campo = "comment"
            antes = "—"
            depois = (ta.get("comment") or "")[:140] + ("..." if len(ta.get("comment", "")) > 140 else "")

        acoes_data.append({
            "aa_id": cid,  # mantido no dict; template 3.8.3+ nao renderiza coluna
            "aa_titulo": titulo,
            "aa_campo": campo,
            "aa_antes": antes,
            "aa_depois": depois,
        })

    # Proximos passos (schema v2.0: proximos_passos_nao_clickup)
    pp_data: list[dict] = []
    for pp in (plan.get("proximos_passos_nao_clickup") or []):
        pp_data.append({
            "pp_acao": pp.get("acao") or "",
            "pp_responsavel": pp.get("responsavel") or "",
            "pp_prazo": pp.get("prazo") or "",
            "pp_tipo": pp.get("tipo") or "info",
        })

    # Escalonamentos
    esc_data: list[dict] = []
    for e in (plan.get("escalonamentos") or []):
        esc_data.append({"escalonamento_item": e if isinstance(e, str) else (e.get("item") or "")})

    # Duplicatas (schema v2.0: existing_name + razao)
    dup_data: list[dict] = []
    for d in (plan.get("duplicatas_detectadas") or []):
        dup_data.append({
            "dup_titulo": d.get("proposed_name") or "",
            "dup_status": "duplicata",
            "dup_status_class": "pending",
            "dup_acao": d.get("razao") or f"existing: {d.get('existing_url') or ''}",
        })

    resumo = plan.get("resumo") or {}
    total_decisoes = resumo.get("decisoes", len(decisoes_data))
    total_contramedidas = resumo.get("contramedidas_novas", len(contramedidas_data))
    total_atualizadas = resumo.get("tasks_atualizadas", len(acoes_data))
    total_duplicatas = resumo.get("duplicatas_detectadas", len(dup_data))
    total_escalonamentos = resumo.get("escalonamentos", len(esc_data))

    return {
        "nivel": nivel,
        "vertical": vertical,
        "data": data,
        "participantes": participantes,
        "duracao": duracao,
        "wbr_referencia": wbr_referencia,
        "timestamp": ts,
        "total_decisoes": total_decisoes,
        "total_contramedidas": total_contramedidas,
        "total_atualizadas": total_atualizadas,
        "total_duplicatas": total_duplicatas,
        "total_escalonamentos": total_escalonamentos,
        "resumo_number": 1,
        "proximos_passos_number": 6,
        "decisao_critica": None,
        "decisoes": decisoes_data,
        "contramedidas": contramedidas_data,
        "acoes_atualizadas": acoes_data,
        "proximos_passos": pp_data,
        "escalonamentos": esc_data or None,
        "duplicatas": dup_data or None,
        "escalonamentos_cor": "var(--vermelho)" if esc_data else "",
        "duplicatas_cor": "var(--amarelo)" if dup_data else "",
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Renderiza ata HTML (template + plan-preview.json)")
    ap.add_argument("--plan-preview-json", required=True, help="path do plan-preview.json gerado em Fase 4.5")
    ap.add_argument("--template", required=True, help="path do ata-ritual.tmpl.html")
    ap.add_argument("--output", required=True, help="path do HTML de saida")
    ap.add_argument("--nivel", required=True, help="N1|N2|N3|N4|N5")
    ap.add_argument("--vertical", required=True, help="nome da vertical (capitalizado)")
    ap.add_argument("--data", required=True, help="data do ritual YYYY-MM-DD")
    ap.add_argument("--participantes", required=True, help="lista de participantes (csv)")
    ap.add_argument("--duracao", default="~60 min", help='ex: "~36 min"')
    ap.add_argument("--wbr-referencia", default="", help='ex: "Maio 2026, semana 5 (MTD)"')
    args = ap.parse_args()

    plan_path = Path(args.plan_preview_json)
    if not plan_path.exists():
        print(f"ERRO: plan-preview.json nao encontrado: {plan_path}", file=sys.stderr)
        return 2

    template_path = Path(args.template)
    if not template_path.exists():
        print(f"ERRO: template nao encontrado: {template_path}", file=sys.stderr)
        return 2

    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    _assert_schema_v2(plan)
    raw_tpl = template_path.read_text(encoding="utf-8")
    mustache_tpl = convert_handlebars_to_mustache(raw_tpl)

    data = build_template_data(
        plan,
        nivel=args.nivel,
        vertical=args.vertical,
        data=args.data,
        participantes=args.participantes,
        duracao=args.duracao,
        wbr_referencia=args.wbr_referencia,
    )

    rendered = chevron.render(mustache_tpl, data)

    # Sanity: nenhum placeholder pendente
    remaining = re.findall(r"\{\{[^}]+\}\}", rendered)
    if remaining:
        print(f"AVISO: placeholders nao resolvidos: {remaining[:10]}", file=sys.stderr)

    Path(args.output).write_text(rendered, encoding="utf-8")
    print(json.dumps({
        "ok": True,
        "output": args.output,
        "size_bytes": Path(args.output).stat().st_size,
        "unresolved_placeholders": remaining,
        "decisoes": len(data["decisoes"]),
        "contramedidas": len(data["contramedidas"]),
        "acoes_atualizadas": len(data["acoes_atualizadas"]),
        "proximos_passos": len(data["proximos_passos"]),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
