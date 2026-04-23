#!/usr/bin/env python3
"""
build_opr.py — Render OPR (one-page report) from canonical data dict.

Inputs:
  --data <json-path>            Canonical dict from collect_data.py
  --template <path>             Jinja2 template (default: templates/opr.tmpl.html)
  --assets-dir <path>           Directory with m7-logo-*.png
  --out-dir <path>              Where to write opr.html + opr.pdf
  --roadmap-html <path>         1-planning/artefatos/roadmap-marcos.html (for mini-swimlane embed)

Output files: opr.html (the rendered HTML), opr.pdf (A4 portrait).

The OPR is a one-page status snapshot. It reuses visual material from
building-project-plan (roadmap-marcos.html) by embedding a screenshot of the
milestones lane, rather than reinventing the timeline.

Tries playwright first, falls back to weasyprint. Aborts if neither installed.
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
import tempfile
from pathlib import Path


STATUS_LABEL = {
    "blue": "🔵 Entregas Avançadas",
    "green": "🟢 No Prazo",
    "yellow": "🟡 Atenção",
    "red": "🔴 Crítico",
}


def encode_image_b64(path: Path, mime: str = "image/png") -> str | None:
    if not path.exists():
        return None
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode("ascii")
    return f"data:{mime};base64,{data}"


def encode_logo(assets_dir: Path, filename: str) -> str | None:
    return encode_image_b64(assets_dir / filename, mime="image/png")


def generate_mini_swimlane(roadmap_html: Path | None, tmp_dir: Path) -> str | None:
    """Screenshot of the .lane.milestones strip from roadmap-marcos.html,
    encoded as base64 data URL for inline embed in the OPR HTML."""
    if not roadmap_html or not roadmap_html.exists():
        return None
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from render_html_section import render as render_section, PRESETS
        out = tmp_dir / "mini-marcos-lane.png"
        preset = PRESETS["marcos-lane"]
        render_section(
            input_path=roadmap_html,
            output_path=out,
            selector=preset["selector"],
            viewport=preset["viewport"],
            device_scale=preset["device_scale"],
            inject_css=preset["inject_css"],
        )
        return encode_image_b64(out, mime="image/png")
    except Exception as e:
        print(f"⚠ Mini-swimlane geração falhou: {e}", file=sys.stderr)
        return None


def pick_unhealthy_reasons(metric_zones: dict, reasons: list) -> list:
    """Legacy helper (kept for backwards-compat). Prefer build_health_narrative()."""
    keys = ["dg", "sg", "spi", "msi"]
    out = []
    for i, k in enumerate(keys):
        if i < len(reasons) and metric_zones.get(k) in ("yellow", "red"):
            out.append(reasons[i])
    return out


def build_health_narrative(metric_zones: dict, breakdown: dict) -> list[dict]:
    """Builds executive-friendly narratives for metrics in yellow/red zones.

    Each narrative is {title, body, examples}:
      - title: short metric label (e.g., "ARRANQUE") — bold, scannable
      - body: prose sentence with absolute counters and operational context
      - examples: up to 3 task references (list of {no, etapa}), empty list if N/A

    Falls back silently if breakdown keys are missing (old collect_data versions).
    """
    narratives = []

    # DG — Delivery Gap
    if metric_zones.get("dg") in ("yellow", "red"):
        d = breakdown.get("devido", {})
        total, pending = d.get("total", 0), d.get("pending", 0)
        if total and pending:
            pct = pending / total * 100
            narratives.append({
                "title": "ENTREGAS",
                "body": (
                    f"{pending} das {total} entregas previstas para até hoje "
                    f"ainda não foram concluídas ({pct:.0f}% do pipeline devido). "
                    "Tarefas concluídas no prazo não foram o suficiente para compensar o gap."
                ),
                "examples": d.get("pending_tasks", []),
            })

    # SG — Start Gap
    if metric_zones.get("sg") in ("yellow", "red"):
        i = breakdown.get("iniciavel", {})
        total, late = i.get("total", 0), i.get("late", 0)
        if total and late:
            pct = late / total * 100
            narratives.append({
                "title": "ARRANQUE",
                "body": (
                    f"{late} das {total} tarefas que já deveriam ter iniciado "
                    f"permanecem como 'não iniciadas' ({pct:.0f}% do pipeline ativo). "
                    "Sem arranque, o cronograma dessas frentes começa a escorregar "
                    "mesmo antes da primeira entrega vencer."
                ),
                "examples": i.get("late_tasks", []),
            })

    # SPI — Schedule Performance Index
    if metric_zones.get("spi") in ("yellow", "red"):
        spi = breakdown.get("spi", {})
        ev = spi.get("ev_days", 0.0)
        pv = spi.get("pv_days", 0.0)
        if pv > 0:
            ratio = ev / pv
            narratives.append({
                "title": "RITMO (SPI)",
                "body": (
                    f"Foram executados {ev:g} dias-trabalho dos {pv:g} planejados para até hoje "
                    f"(SPI = {ratio:.2f}). PMI considera projeto saudável com SPI ≥ 0.95; "
                    "abaixo de 0.85 o atraso vira estrutural e precisa replanejamento."
                ),
                "examples": [],
            })

    # MSI — Milestone Slip Index
    if metric_zones.get("msi") in ("yellow", "red"):
        msi = breakdown.get("msi", {})
        slip = msi.get("max_slip_days", 0)
        label = msi.get("milestone_label") or "marco crítico"
        if slip > 0:
            if slip <= 7:
                severity = "atenção"
                gravity = "ainda recuperável se agir nesta quinzena"
            else:
                severity = "crítico"
                gravity = "escalação ao sponsor obrigatória"
            narratives.append({
                "title": "MARCOS",
                "body": (
                    f"{label} está atrasado {slip} dia{'s' if slip != 1 else ''} "
                    f"({severity}): {gravity}."
                ),
                "examples": [],
            })

    return narratives


def pick_top_risks(risks: list[dict], limit: int = 3) -> list[dict]:
    """Top-N risks by severity (crit > high > med), excluding upsides."""
    actual = [r for r in risks if not r.get("is_upside")]
    order = {"crit": 0, "high": 1, "med": 2, "low": 3}
    actual.sort(key=lambda r: order.get(r.get("severity_class"), 99))
    return actual[:limit]


def pick_next_milestones(milestones: list[dict], limit: int = 3) -> list[dict]:
    """Next N milestones that are not yet 'done' — shows what's ahead."""
    upcoming = [m for m in milestones if m.get("status") != "done"]
    return upcoming[:limit]


STATUS_SHORT = {
    "blue": "Avançado",
    "green": "No Prazo",
    "yellow": "Atenção",
    "red": "Crítico",
}


def render_html(
    data: dict,
    template_path: Path,
    assets_dir: Path,
    roadmap_html: Path | None,
    compact: bool = False,
) -> str:
    """Renders the OPR v1.6 template with 6 zones matching the Paper artboard
    `OPR — Status Report`: Hero · Roadmap · Matriz · Progresso · Riscos · Footer."""
    try:
        from jinja2 import Template
    except ImportError:
        raise RuntimeError("jinja2 ausente. Instale: pip install jinja2")

    template = Template(template_path.read_text(encoding="utf-8"))
    logo_url = encode_logo(assets_dir, "m7-logo-offwhite.png")

    # Risks + incurred split
    all_risks = data.get("risks", [])
    actual_risks = [r for r in all_risks if not r.get("is_upside")]
    total_risks = len(actual_risks)
    incurred_risks = [r for r in actual_risks if r.get("is_incurred")]
    # When counting "critical" and "high" for the hero pill, use severity_class regardless of incurred
    risks_critical_count = sum(1 for r in actual_risks if r.get("severity_class") == "crit")
    risks_high_count = sum(1 for r in actual_risks if r.get("severity_class") == "high")

    # Next gate — first milestone that isn't done
    next_marcos = pick_next_milestones(data.get("macro_milestones", []), limit=3)

    # Roadmap data
    all_macro_milestones = data.get("macro_milestones", [])
    total_marcos = len(all_macro_milestones)
    done_marcos = sum(1 for m in all_macro_milestones if m.get("status") == "done")
    active_phase = _infer_active_phase(all_macro_milestones)
    roadmap_sentence = (
        f"{done_marcos} de {total_marcos} marcos atingidos · {active_phase}"
        if total_marcos > 0 else "Roadmap não disponível"
    )
    # For the OPR horizontal timeline, keep only major (gate) milestones to avoid
    # label overlap when regulars cluster near the end (e.g., M5/M6/M7 all in Jul).
    # The sentence above keeps the full count (e.g., "1 de 8 marcos").
    macro_milestones = [m for m in all_macro_milestones if m.get("major")] or all_macro_milestones
    roadmap_months, roadmap_months_range = _derive_roadmap_months(all_macro_milestones)
    roadmap_overlays = data.get("roadmap_overlays", {}) or {}

    # Matrix data
    matrix_structure = data.get("roadmap_structure", {}) or {}
    meta = matrix_structure.get("meta", {}) or {}
    matrix_total = meta.get("total_cells", 0)
    matrix_done = meta.get("done_cells", 0)
    matrix_active = meta.get("active_cells", 0)
    matrix_pct = round(100 * matrix_done / matrix_total) if matrix_total else 0
    matrix_sentence = (
        f"{matrix_done + matrix_active} de {matrix_total} entregas em execução · {matrix_pct}% concluídas"
        if matrix_total else "Matriz não disponível"
    )

    # Progress data
    progress_concluidas = data.get("progress_concluidas", [])
    progress_proximas = data.get("progress_proximas", [])
    progress_sentence = (
        f"{len(progress_concluidas)} task{'s' if len(progress_concluidas) != 1 else ''} concluída{'s' if len(progress_concluidas) != 1 else ''} na quinzena · "
        f"{len(progress_proximas)} próxima{'s' if len(progress_proximas) != 1 else ''} nos próximos 14 dias"
    )

    # Project meta with shortened clickup url for display
    project = dict(data.get("project", {}) or {})
    if project.get("clickup_list_url"):
        url = project["clickup_list_url"]
        short = url.replace("https://", "").replace("http://", "")
        project["clickup_list_url_short"] = short.split("/l/")[0] if "/l/" in short else short

    status = data.get("status", {}) or {}

    return template.render(
        project=project,
        report_date=data.get("report_date"),
        status=status,
        status_label=STATUS_LABEL.get(status.get("overall"), "🟢 OK"),
        status_label_short=STATUS_SHORT.get(status.get("overall"), "OK"),
        next_marcos=next_marcos,
        risks_critical_count=risks_critical_count,
        risks_high_count=risks_high_count,
        macro_milestones=macro_milestones,
        roadmap_sentence=roadmap_sentence,
        roadmap_months=roadmap_months,
        roadmap_months_range=roadmap_months_range,
        roadmap_overlays=roadmap_overlays,
        matrix_structure=matrix_structure,
        matrix_sentence=matrix_sentence,
        progress_concluidas=progress_concluidas,
        progress_proximas=progress_proximas,
        progress_sentence=progress_sentence,
        incurred_count=len(incurred_risks),
        incurred_risks=incurred_risks,
        total_risks=total_risks,
        status_reasons_unhealthy=pick_unhealthy_reasons(
            status.get("metric_zones", {}) or {},
            status.get("status_reasons", []) or [],
        ),
        health_narrative=build_health_narrative(
            status.get("metric_zones", {}) or {},
            status.get("metrics_breakdown", {}) or {},
        ),
        logo_url=logo_url,
        compact=compact,
    )


_PHASE_HINTS = {
    "KICKOFF": "Kickoff em curso",
    "FUNDAÇÃO": "Fundação em curso",
    "FUNDACAO": "Fundação em curso",
    "PRIMEIROS": "Execução inicial em curso",
    "MID-POINT": "Execução em meio-caminho",
    "COBERTURA": "Execução na reta final",
    "CONSOLIDAÇÃO": "Consolidação em curso",
    "CONSOLIDACAO": "Consolidação em curso",
    "HANDOFFS": "Handoffs em curso",
    "TE": "Encerramento em curso",
}


def _infer_active_phase(milestones: list[dict]) -> str:
    """Finds the next not-yet-done milestone and maps its label to a short phase name."""
    if not milestones:
        return "sem marcos"
    target = next((m for m in milestones if m.get("status") in ("in_progress", "active", "not_started")), None)
    if not target:
        return "todos marcos atingidos"
    label_upper = (target.get("label") or "").upper()
    for key, phrase in _PHASE_HINTS.items():
        if key in label_upper:
            return phrase
    return f"próximo marco: {target.get('label', '')}"


def _derive_roadmap_months(milestones: list[dict]) -> tuple[list[str], str]:
    """Extracts month range (e.g., ['MAR', 'ABR', 'MAI', 'JUN', 'JUL'])
    and a compact range label (e.g., 'mar — jul 2026') from milestone dates.
    Falls back to ['MAR', 'ABR', 'MAI', 'JUN', 'JUL'] if dates are missing.
    """
    from datetime import datetime as _dt
    months_pt = {1: "JAN", 2: "FEV", 3: "MAR", 4: "ABR", 5: "MAI", 6: "JUN",
                 7: "JUL", 8: "AGO", 9: "SET", 10: "OUT", 11: "NOV", 12: "DEZ"}
    dates = []
    for m in milestones:
        d = m.get("date")
        if not d:
            continue
        try:
            dates.append(_dt.strptime(d, "%Y-%m-%d"))
        except (ValueError, TypeError):
            continue
    if not dates:
        return ["MAR", "ABR", "MAI", "JUN", "JUL"], ""
    dates.sort()
    start, end = dates[0], dates[-1]
    # Build month list from start month through end month (inclusive)
    months = []
    year, month = start.year, start.month
    while (year, month) <= (end.year, end.month):
        months.append(months_pt.get(month, str(month)))
        month += 1
        if month > 12:
            month = 1
            year += 1
    range_label = f"{months[0].lower()} — {months[-1].lower()} {end.year}"
    return months, range_label


def render_pdf_playwright(html: str, pdf_path: Path) -> bool:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            try:
                page = browser.new_page()
                page.set_content(html, wait_until="networkidle")
                page.pdf(
                    path=str(pdf_path),
                    format="A4",
                    margin={"top": "8mm", "bottom": "8mm", "left": "10mm", "right": "10mm"},
                    print_background=True,
                )
            finally:
                browser.close()
        return True
    except Exception as e:
        print(f"⚠ playwright falhou: {e}", file=sys.stderr)
        return False


def render_pdf_weasyprint(html: str, pdf_path: Path) -> bool:
    try:
        from weasyprint import HTML as WPHtml
    except ImportError:
        return False
    try:
        WPHtml(string=html).write_pdf(target=str(pdf_path))
        return True
    except Exception as e:
        print(f"⚠ weasyprint falhou: {e}", file=sys.stderr)
        return False


def measure_overflow_playwright(html: str) -> int | None:
    """Returns scrollHeight in px, or None if playwright unavailable."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            try:
                page = browser.new_page(viewport={"width": 794, "height": 1123})
                page.set_content(html, wait_until="networkidle")
                return page.evaluate("document.body.scrollHeight")
            finally:
                browser.close()
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, type=Path)
    ap.add_argument("--template", type=Path)
    ap.add_argument("--assets-dir", type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    ap.add_argument(
        "--roadmap-html", type=Path,
        help="Path to 1-planning/artefatos/roadmap-marcos.html (embeds mini-swimlane).",
    )
    ap.add_argument("--keep-html", action="store_true")
    args = ap.parse_args()

    script_dir = Path(__file__).parent
    skill_dir = script_dir.parent
    template_path = args.template or (skill_dir / "templates" / "opr.tmpl.html")
    assets_dir = args.assets_dir or (skill_dir / "assets")

    if not args.data.exists():
        print(f"✗ Arquivo de dados não encontrado: {args.data}", file=sys.stderr)
        sys.exit(2)
    if not template_path.exists():
        print(f"✗ Template não encontrado: {template_path}", file=sys.stderr)
        sys.exit(2)

    data = json.loads(args.data.read_text(encoding="utf-8"))
    args.out_dir.mkdir(parents=True, exist_ok=True)

    html = render_html(data, template_path, assets_dir, args.roadmap_html, compact=False)
    html_path = args.out_dir / "opr.html"
    html_path.write_text(html, encoding="utf-8")

    # Try to detect overflow (A4 portrait is ~1123px high at 96dpi)
    height = measure_overflow_playwright(html)
    if height and height > 1123:
        print(f"⚠ OPR excede A4 ({height}px > 1123px). Rerenderizando em modo compacto.", file=sys.stderr)
        html = render_html(data, template_path, assets_dir, args.roadmap_html, compact=True)
        html_path.write_text(html, encoding="utf-8")

    pdf_path = args.out_dir / "opr.pdf"
    ok = render_pdf_playwright(html, pdf_path) or render_pdf_weasyprint(html, pdf_path)
    if not ok:
        print(
            "✗ Nenhum driver HTML→PDF disponível.\n"
            "  Instale: pip install playwright && playwright install chromium\n"
            "      ou: pip install weasyprint",
            file=sys.stderr,
        )
        sys.exit(3)

    print(f"✓ OPR gerado: {html_path}")
    print(f"✓ OPR PDF:    {pdf_path}")

    if data.get("warnings"):
        print(f"⚠ {len(data['warnings'])} warning(s):", file=sys.stderr)
        for w in data["warnings"]:
            print(f"   · {w}", file=sys.stderr)


if __name__ == "__main__":
    main()
