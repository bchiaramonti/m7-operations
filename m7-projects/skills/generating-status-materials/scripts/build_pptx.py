#!/usr/bin/env python3
"""
build_pptx.py — Render 8-slide status presentation (16:9) from canonical data.

Mapping canvas Paper `status-report`:
  01 Cover · 02 Agenda · 03 Roadmap Overview · 04 Roadmap Detail
  05 Section Divider · 06 Executive Status · 07 Risks · 08 Closing

Inputs:
  --data <json-path>       Canonical dict from collect_data.py
  --assets-dir <path>      Directory with m7-logo-*.png
  --out-dir <path>         Where to write status-presentation.pptx

Pure python-pptx — no MCP or LLM calls.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from pptx import Presentation
    from pptx.util import Emu, Pt, Inches
    from pptx.dml.color import RGBColor
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
except ImportError:
    print("✗ python-pptx ausente. Instale: pip install python-pptx", file=sys.stderr)
    sys.exit(2)


# ---- Tokens (mirrored from references/design-tokens.md) ----

COL_PRIMARY        = RGBColor(0x42, 0x41, 0x35)
COL_BG_LIGHT       = RGBColor(0xFF, 0xFD, 0xEF)
COL_TEXT_MUTED     = RGBColor(0x4F, 0x4E, 0x3C)
COL_TEXT_SUBTLE    = RGBColor(0x79, 0x75, 0x5C)
COL_TEXT_CAPTION   = RGBColor(0xAE, 0xAD, 0xA8)
COL_ACCENT_LIME    = RGBColor(0xEE, 0xF7, 0x7C)
COL_STATUS_OK      = RGBColor(0x00, 0xB0, 0x50)
COL_STATUS_PROG    = RGBColor(0x3B, 0x82, 0xF6)
COL_STATUS_WARN    = RGBColor(0xF5, 0x9E, 0x0B)
COL_STATUS_CRIT    = RGBColor(0xE4, 0x69, 0x62)
COL_STATUS_NEUTRAL = RGBColor(0xD0, 0xD0, 0xCC)
COL_TAG_BG_CRIT    = RGBColor(0xFD, 0xED, 0xED)
COL_TAG_BG_WARN    = RGBColor(0xFD, 0xF3, 0xE0)
COL_TAG_BG_NEUTRAL = RGBColor(0xEF, 0xEF, 0xEC)
COL_TABLE_HDR_BG   = RGBColor(0xF1, 0xEF, 0xDE)
COL_ROW_BORDER     = RGBColor(0xE5, 0xE2, 0xCE)

# ---- Slide layout constants (documented values from references/design-tokens.md) ----
# Pixel-to-EMU conversion: 1 px = 9525 EMU (slide 13.333in x 7.5in @ 96dpi = 1280x720 px)
PX = 9525

# Canvas dimensions (Paper artboards are 1280x720; see references/presentation-structure.md)
SLIDE_W_PX = 1280
SLIDE_H_PX = 720

# Paddings (vertical / horizontal) — see design-tokens.md §Espaçamento
PAD_SLIDE_X = 80        # default horizontal padding for content slides
PAD_SLIDE_Y_TOP = 56    # default top padding
PAD_SLIDE_Y_BOT = 56    # default bottom padding
PAD_EXEC_X = 40         # slide 06 Executive uses tighter padding (denser)
PAD_EXEC_Y = 36

# Content column width (after left+right padding): 1280 - 80*2 = 1120
CONTENT_W_PX = SLIDE_W_PX - PAD_SLIDE_X * 2

# Milestone/timeline element sizes — see design-tokens.md §Elementos estruturais
DIAMOND_SIZE_ACTIVE = 14    # filled diamond (done, in_progress, overdue)
DIAMOND_SIZE_NEUTRAL = 10   # outlined diamond (not_started)

# Risk card dimensions — see presentation-structure.md §Slide 07
RISK_CARD_H = 120
RISK_CARD_GAP = 14
RISK_ACCENT_BAR_W = 6
RISK_TAG_W = 150

# Logo display sizes (source PNG is 196x96; aspect preserved)
LOGO_SIZE_COVER = 60        # Cover, Agenda, Section Divider, Closing (dark BGs)
LOGO_SIZE_CONTENT = 60      # Roadmap, Risks (light BGs)
LOGO_SIZE_EXEC = 44         # Executive Status (tighter padding)


def emu(px_val: float) -> int:
    return int(px_val * PX)


# ---- Helpers ----

def fill_solid(shape, rgb: RGBColor):
    shape.fill.solid()
    shape.fill.fore_color.rgb = rgb
    shape.line.fill.background()


def add_bg_rect(slide, w_emu, h_emu, rgb: RGBColor):
    rect = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, w_emu, h_emu)
    fill_solid(rect, rgb)


def add_text(
    slide, x_px, y_px, w_px, h_px, text, *,
    size=14, bold=False, color=COL_PRIMARY, tracking=0.0,
    align="left", anchor="top", italic=False, font="Arial"
):
    box = slide.shapes.add_textbox(emu(x_px), emu(y_px), emu(w_px), emu(h_px))
    tf = box.text_frame
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.word_wrap = True
    if anchor == "middle":
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    elif anchor == "bottom":
        tf.vertical_anchor = MSO_ANCHOR.BOTTOM
    else:
        tf.vertical_anchor = MSO_ANCHOR.TOP
    # First paragraph
    p = tf.paragraphs[0]
    align_map = {"left": PP_ALIGN.LEFT, "center": PP_ALIGN.CENTER, "right": PP_ALIGN.RIGHT}
    p.alignment = align_map.get(align, PP_ALIGN.LEFT)
    for i, line in enumerate(str(text).split("\n")):
        if i > 0:
            p = tf.add_paragraph()
            p.alignment = align_map.get(align, PP_ALIGN.LEFT)
        run = p.add_run()
        run.text = line
        run.font.name = font
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.italic = italic
        run.font.color.rgb = color
        if tracking:
            # spc is in 1/100 pt; 1em ~= size pt, so spc = tracking * size * 100
            rPr = run._r.get_or_add_rPr()
            rPr.set("spc", str(int(tracking * size * 100)))
    return box


def add_rect(slide, x_px, y_px, w_px, h_px, rgb: RGBColor, line_rgb=None):
    r = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, emu(x_px), emu(y_px), emu(w_px), emu(h_px))
    fill_solid(r, rgb)
    if line_rgb is not None:
        r.line.color.rgb = line_rgb
        r.line.width = Emu(0)
    return r


def add_diamond(slide, x_px, y_px, size_px, rgb: RGBColor, outlined=False):
    d = slide.shapes.add_shape(MSO_SHAPE.DIAMOND, emu(x_px), emu(y_px), emu(size_px), emu(size_px))
    if outlined:
        d.fill.background()
        d.line.color.rgb = rgb
        d.line.width = Pt(1.5)
    else:
        fill_solid(d, rgb)
    return d


def add_logo(slide, x_px, y_px, size_px, assets_dir: Path, variant: str):
    path = assets_dir / f"m7-logo-{variant}.png"
    if path.exists():
        # Logo original is 196x96; maintain aspect ratio, target width~44-56px
        slide.shapes.add_picture(str(path), emu(x_px), emu(y_px), width=emu(size_px))
    else:
        color = COL_BG_LIGHT if variant == "offwhite" else COL_PRIMARY
        add_text(slide, x_px, y_px, size_px, size_px * 0.45, "M7",
                 size=22, bold=True, italic=True, color=color, align="right")


# ---- Severity helpers ----

def risk_severity_label(risk) -> tuple[str, RGBColor, RGBColor]:
    prob = risk.get("probability", "baixa")
    impact = risk.get("impact", "baixo")
    if prob == "alta" and impact in ("critico", "alto"):
        return "ALTA · CRÍTICO", COL_TAG_BG_CRIT, COL_STATUS_CRIT
    if prob in ("alta", "media") or impact in ("critico", "alto"):
        p = "ALTA" if prob == "alta" else "MÉDIA"
        i = "ALTO" if impact == "alto" else "CRÍTICO" if impact == "critico" else "MÉDIO"
        return f"{p} · {i}", COL_TAG_BG_WARN, COL_STATUS_WARN
    return f"{prob.upper()} · {impact.upper()}", COL_TAG_BG_NEUTRAL, COL_STATUS_NEUTRAL


# ---- Slides ----

def slide_01_cover(prs, data, assets_dir):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_bg_rect(slide, prs.slide_width, prs.slide_height, COL_PRIMARY)
    # Eyebrow "STATUS REPORT"
    add_text(slide, 80, 64, 400, 20, "STATUS REPORT",
             size=13, bold=True, color=COL_ACCENT_LIME, tracking=0.2)
    # Logo top right
    add_logo(slide, 1180, 50, 60, assets_dir, "offwhite")
    # Title block
    project_name = data.get("project", {}).get("name", "Projeto")
    add_text(slide, 80, 320, 960, 80, project_name,
             size=56, bold=False, color=COL_BG_LIGHT)
    add_text(slide, 80, 400, 960, 80, "Status Report",
             size=56, bold=False, color=COL_BG_LIGHT)
    # Subtitle Lime
    add_text(slide, 80, 496, 960, 30, data.get("project", {}).get("period_label", ""),
             size=22, color=COL_ACCENT_LIME)
    # Footer
    add_text(slide, 80, 664, 800, 20, data.get("project", {}).get("footer_label", ""),
             size=12, color=COL_BG_LIGHT)
    # Footer right (slide number)
    add_text(slide, 1160, 664, 80, 20, "01",
             size=12, color=COL_BG_LIGHT, align="right")


def slide_02_agenda(prs, data, assets_dir):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_bg_rect(slide, prs.slide_width, prs.slide_height, COL_PRIMARY)
    add_text(slide, 80, 64, 400, 20, "STATUS REPORT",
             size=13, bold=True, color=COL_ACCENT_LIME, tracking=0.2)
    add_logo(slide, 1180, 50, 60, assets_dir, "offwhite")
    # Title
    add_text(slide, 80, 140, 800, 60, "Agenda",
             size=48, color=COL_BG_LIGHT)
    # Divider
    add_rect(slide, 80, 220, 1120, 1, COL_BG_LIGHT)
    # Items
    items = [
        ("01", "Visão Geral do Roadmap", "Slides 03–04"),
        ("02", "Sprint Ativo — Status Executivo", "Slides 05–06"),
        ("03", "Riscos e Pontos de Atenção", "Slide 07"),
        ("04", "Próximos Passos", "Slide 08"),
    ]
    y = 246
    for num, title, rng in items:
        add_text(slide, 80, y, 60, 20, num,
                 size=13, bold=True, color=COL_ACCENT_LIME, tracking=0.2)
        add_text(slide, 160, y, 800, 28, title,
                 size=22, color=COL_BG_LIGHT)
        add_text(slide, 980, y + 4, 220, 20, rng,
                 size=10, color=COL_TEXT_CAPTION, align="right")
        y += 40
        add_rect(slide, 80, y + 16, 1120, 1, COL_BG_LIGHT)
        y += 30


def slide_03_roadmap_overview(prs, data, assets_dir):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_bg_rect(slide, prs.slide_width, prs.slide_height, COL_BG_LIGHT)
    # Eyebrow
    add_text(slide, 80, 56, 400, 16, "00 · ROADMAP",
             size=12, bold=True, color=COL_PRIMARY, tracking=0.2)
    # Logo
    add_logo(slide, 1180, 48, 60, assets_dir, "dark")
    # Hero
    add_text(slide, 80, 80, 800, 40, data.get("status", {}).get("sprint_progress_sentence", ""),
             size=32, color=COL_PRIMARY)
    # Subtitle
    add_text(slide, 80, 128, 800, 24, "Projeto em andamento · cobertura por processo de execução ao longo das sprints.",
             size=14, color=COL_TEXT_SUBTLE)

    sprints = data.get("sprints", [])[:6]
    # Table header
    header_y = 200
    row_h = 44
    # Draw header BG
    add_rect(slide, 80, header_y, 1120, 36, COL_TABLE_HDR_BG)
    cols = [
        ("SPRINT", 80, 72),
        ("TÍTULO", 152, 220),
        ("PERÍODO", 372, 150),
        ("DIAGNÓSTICO", 522, 130),
        ("PROCESSO", 652, 120),
        ("RELATÓRIOS", 772, 120),
        ("AUTOMAÇÃO", 892, 120),
        ("PILOTO", 1012, 90),
        ("ROTINA", 1102, 98),
    ]
    for label, x, w in cols:
        add_text(slide, x + 8, header_y + 10, w - 8, 16, label,
                 size=10, bold=True, color=COL_TEXT_MUTED, tracking=0.14)

    y = header_y + 36
    for s in sprints:
        # Row bottom border
        add_rect(slide, 80, y + row_h - 1, 1120, 1, COL_ROW_BORDER)
        add_text(slide, 88, y + 12, 60, 20, s.get("code", ""),
                 size=14, bold=True, color=COL_PRIMARY)
        add_text(slide, 160, y + 12, 200, 20, s.get("title", ""),
                 size=12, color=COL_TEXT_MUTED)
        add_text(slide, 380, y + 12, 140, 20, s.get("period_label", ""),
                 size=10, color=COL_TEXT_SUBTLE)
        # Status squares (simplified — show active/future marker)
        is_active = s.get("status") == "active"
        for i, (_, cx, cw) in enumerate(cols[3:]):
            sq_x = cx + cw // 2 - 6
            if is_active and i <= 1:  # Use heuristic: first 2 columns for active sprint
                add_rect(slide, sq_x, y + 14, 12, 12, COL_STATUS_PROG)
            else:
                add_rect(slide, sq_x, y + 14, 12, 12, COL_STATUS_NEUTRAL)
        y += row_h

    # Legend
    add_text(slide, 80, 660, 600, 14, "■ Sprint ativo   ■ Sprint futuro   — Não aplicável",
             size=10, color=COL_TEXT_MUTED)
    add_text(slide, 720, 660, 480, 14,
             f"Fonte: Cronograma.xlsx · Atualizado em {data.get('report_date', '')}",
             size=10, color=COL_TEXT_CAPTION, align="right")


def slide_04_roadmap_detail(prs, data, assets_dir):
    """Simplified swimlane: shows macro milestones as a Gantt-ish timeline."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_bg_rect(slide, prs.slide_width, prs.slide_height, COL_BG_LIGHT)
    add_text(slide, 80, 56, 400, 16, "03 · ROADMAP",
             size=12, bold=True, color=COL_PRIMARY, tracking=0.2)
    add_logo(slide, 1180, 48, 60, assets_dir, "dark")
    add_text(slide, 80, 80, 900, 40, "Visão Geral do Roadmap",
             size=32, color=COL_PRIMARY)
    add_text(slide, 80, 128, 900, 24,
             "Fases · marcos · status por etapa do projeto.",
             size=14, color=COL_TEXT_SUBTLE)

    milestones = data.get("macro_milestones", [])[:7]
    if not milestones:
        add_text(slide, 80, 360, 1120, 40,
                 "— Marcos não identificados no plano. Execute building-project-plan para popular. —",
                 size=14, color=COL_TEXT_CAPTION, align="center")
        return

    # Timeline strip
    strip_x, strip_y, strip_w, strip_h = 120, 260, 1040, 180
    add_rect(slide, strip_x - 20, strip_y - 20, strip_w + 40, strip_h + 40, COL_TAG_BG_NEUTRAL)

    n = len(milestones)
    spacing = strip_w // max(n - 1, 1) if n > 1 else 0
    for i, m in enumerate(milestones):
        cx = strip_x + i * spacing
        status = m.get("status", "not_started")
        color = {
            "done": COL_STATUS_OK,
            "in_progress": COL_STATUS_PROG,
            "overdue": COL_STATUS_CRIT,
            "not_started": COL_STATUS_NEUTRAL,
        }.get(status, COL_STATUS_NEUTRAL)
        outlined = status == "not_started"
        size = 20 if not outlined else 16
        add_diamond(slide, cx - size // 2, strip_y + strip_h // 2 - size // 2, size, color, outlined)
        # Label below
        add_text(slide, cx - 80, strip_y + strip_h // 2 + 24, 160, 30,
                 m.get("label", ""), size=11, color=COL_TEXT_MUTED, align="center")
        # Connector to next
        if i < n - 1:
            add_rect(slide, cx + size // 2, strip_y + strip_h // 2 - 1, spacing - size, 2, color)

    add_text(slide, 80, 660, 600, 14,
             "◆ Concluído   ◆ Em andamento   ◆ Atrasado   ◇ Não iniciado",
             size=10, color=COL_TEXT_MUTED)


def slide_05_section_divider(prs, data, assets_dir):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_bg_rect(slide, prs.slide_width, prs.slide_height, COL_PRIMARY)
    active = data.get("status", {}).get("active_sprint") or {}
    idx = data.get("status", {}).get("active_sprint_index", 1)
    total = data.get("status", {}).get("total_sprints", 1)
    # Eyebrow
    add_text(slide, 80, 64, 400, 20,
             f"SPRINT ATIVO · {idx:02d} DE {total:02d}",
             size=13, bold=True, color=COL_ACCENT_LIME, tracking=0.2)
    add_logo(slide, 1180, 50, 60, assets_dir, "offwhite")
    # Hero numeral
    add_text(slide, 120, 260, 300, 200,
             active.get("code", "S0"),
             size=160, color=COL_ACCENT_LIME, align="left", bold=False)
    # Divider vertical line
    add_rect(slide, 440, 280, 1, 180, COL_BG_LIGHT)
    # Eyebrow above title
    add_text(slide, 480, 280, 600, 20,
             active.get("phase_name", "").upper(),
             size=13, bold=True, color=COL_BG_LIGHT, tracking=0.2)
    # Title
    title = active.get("title") or "Sprint ativa"
    add_text(slide, 480, 310, 700, 140,
             title, size=48, color=COL_BG_LIGHT)
    # Period
    add_text(slide, 480, 460, 700, 24,
             (active.get("period_label") or "") + "  ·  Sprint atual",
             size=14, color=COL_BG_LIGHT)
    # Slide number
    add_text(slide, 1160, 660, 80, 18, "05",
             size=12, color=COL_BG_LIGHT, align="right")


def slide_06_executive_status(prs, data, assets_dir):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_bg_rect(slide, prs.slide_width, prs.slide_height, COL_BG_LIGHT)
    active = data.get("status", {}).get("active_sprint") or {}

    # Eyebrow + Hero
    add_text(slide, 40, 40, 800, 16,
             active.get("eyebrow", "SPRINT ATIVA"),
             size=11, bold=True, color=COL_PRIMARY, tracking=0.2)
    add_text(slide, 40, 60, 900, 40,
             data.get("status", {}).get("hero_sentence", ""),
             size=30, color=COL_PRIMARY)
    add_logo(slide, 1200, 36, 44, assets_dir, "dark")

    # Zone 1: Cronograma Macro
    zone1_y = 120
    add_text(slide, 40, zone1_y, 600, 14, "CRONOGRAMA MACRO",
             size=10, bold=True, color=COL_TEXT_MUTED, tracking=0.14)
    mm = data.get("macro_milestones", [])[:7]
    if mm:
        timeline_y = zone1_y + 30
        strip_x = 60
        strip_w = 1160
        n = len(mm)
        spacing = strip_w // max(n - 1, 1) if n > 1 else 0
        # BG box
        add_rect(slide, 40, zone1_y + 16, 1200, 90, COL_BG_LIGHT, line_rgb=COL_ROW_BORDER)
        for i, m in enumerate(mm):
            cx = strip_x + i * spacing
            status = m.get("status", "not_started")
            color = {
                "done": COL_STATUS_OK,
                "in_progress": COL_STATUS_PROG,
                "overdue": COL_STATUS_CRIT,
                "not_started": COL_STATUS_NEUTRAL,
            }.get(status, COL_STATUS_NEUTRAL)
            outlined = status == "not_started"
            ds = 14 if not outlined else 10
            add_diamond(slide, cx - ds // 2, timeline_y + 14, ds, color, outlined)
            add_text(slide, cx - 60, timeline_y + 36, 120, 30,
                     m.get("label", ""), size=10, color=COL_TEXT_MUTED, align="center")
            if i < n - 1:
                add_rect(slide, cx + ds // 2, timeline_y + 20, spacing - ds, 2,
                         color if status in ("done", "in_progress") else COL_STATUS_NEUTRAL)

    # Zone 2-3: Two columns
    zone2_y = 260
    col_w = 586
    # Label columns
    add_text(slide, 40, zone2_y, col_w, 14, "STATUS EXECUTIVO",
             size=10, bold=True, color=COL_TEXT_MUTED, tracking=0.14)
    add_text(slide, 40 + col_w + 20, zone2_y, col_w, 14, "PRÓXIMAS ATIVIDADES",
             size=10, bold=True, color=COL_TEXT_MUTED, tracking=0.14)

    # Box Left (Highlights)
    add_rect(slide, 40, zone2_y + 20, col_w, 240, COL_BG_LIGHT, line_rgb=COL_ROW_BORDER)
    highlights = data.get("highlights", [])[:5]
    y = zone2_y + 36
    for h in highlights:
        add_rect(slide, 56, y + 6, 4, 4, COL_PRIMARY)
        add_text(slide, 68, y, col_w - 36, 20, h,
                 size=11, color=COL_TEXT_MUTED)
        y += 24

    # Box Right (Next steps)
    add_rect(slide, 40 + col_w + 20, zone2_y + 20, col_w, 240, COL_BG_LIGHT, line_rgb=COL_ROW_BORDER)
    next_steps = data.get("next_steps", [])[:5]
    y = zone2_y + 36
    for n in next_steps:
        add_rect(slide, 40 + col_w + 20 + 16, y + 6, 4, 4, COL_PRIMARY)
        add_text(slide, 40 + col_w + 20 + 28, y, col_w - 36, 20,
                 f"{n.get('action','')} — até {n.get('deadline','')}",
                 size=11, color=COL_TEXT_MUTED)
        y += 24

    # Zone 4: Attentions
    zone4_y = 540
    add_text(slide, 40, zone4_y, 800, 14, "PONTOS DE ATENÇÃO",
             size=10, bold=True, color=COL_STATUS_WARN, tracking=0.14)
    add_rect(slide, 40, zone4_y + 20, 1200, 90, COL_BG_LIGHT, line_rgb=COL_ROW_BORDER)
    y = zone4_y + 32
    for a in data.get("attentions", [])[:3]:
        sev_color = {
            "critical": COL_STATUS_CRIT,
            "warning": COL_STATUS_WARN,
            "neutral": COL_STATUS_NEUTRAL,
        }.get(a.get("severity"), COL_STATUS_NEUTRAL)
        add_rect(slide, 56, y + 6, 4, 4, sev_color)
        add_text(slide, 68, y, 1130, 20, a.get("text", ""),
                 size=11, color=COL_TEXT_MUTED)
        y += 24

    # Footer
    add_text(slide, 40, 680, 600, 14,
             f"Atualizado em {data.get('report_date', '')} · Fonte: Cronograma.xlsx LIVE",
             size=10, color=COL_TEXT_CAPTION)


def slide_07_risks(prs, data, assets_dir):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_bg_rect(slide, prs.slide_width, prs.slide_height, COL_BG_LIGHT)
    add_text(slide, 80, 56, 400, 16, "03 · RISCOS",
             size=12, bold=True, color=COL_PRIMARY, tracking=0.2)
    add_logo(slide, 1180, 48, 60, assets_dir, "dark")
    add_text(slide, 80, 80, 900, 40,
             data.get("status", {}).get("risks_sentence", ""),
             size=32, color=COL_PRIMARY)
    add_text(slide, 80, 128, 900, 24,
             "Monitoramento ativo. Contramedidas definidas para cada risco.",
             size=14, color=COL_TEXT_SUBTLE)

    risks = data.get("risks", [])[:3]
    card_y = 200
    card_w = 1120
    card_h = 120
    gap = 14
    for r in risks:
        severity_label, tag_bg, bar_color = risk_severity_label(r)
        # Accent bar
        add_rect(slide, 80, card_y, 6, card_h, bar_color)
        # Card box
        add_rect(slide, 92, card_y, card_w - 12, card_h, COL_BG_LIGHT, line_rgb=COL_ROW_BORDER)
        # Title
        add_text(slide, 112, card_y + 16, 800, 24,
                 f"{r.get('code','R')} — {r.get('title','')}",
                 size=16, bold=True, color=COL_PRIMARY)
        # Severity tag
        tag_w = 150
        add_rect(slide, card_w + 80 - tag_w, card_y + 18, tag_w - 10, 22, tag_bg)
        add_text(slide, card_w + 80 - tag_w + 6, card_y + 22, tag_w - 22, 18,
                 severity_label, size=9, bold=True, color=COL_PRIMARY, tracking=0.14, align="center")
        # Details
        add_text(slide, 112, card_y + 54, card_w - 44, 20,
                 f"Probabilidade: {r.get('probability','').capitalize()} · Impacto: {r.get('impact','').capitalize()}",
                 size=12, color=COL_TEXT_SUBTLE)
        add_text(slide, 112, card_y + 80, card_w - 44, 30,
                 f"Contramedida: {r.get('mitigation','— sem contramedida —')}",
                 size=12, color=COL_TEXT_MUTED)
        card_y += card_h + gap

    if not risks:
        add_text(slide, 80, 340, 1120, 40,
                 "Nenhum risco mapeado.",
                 size=18, color=COL_TEXT_SUBTLE, align="center")

    add_text(slide, 80, 660, 1120, 14,
             f"Fonte: riscos.html · Atualizado em {data.get('report_date','')}",
             size=10, color=COL_TEXT_CAPTION)


def slide_08_closing(prs, data, assets_dir):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_bg_rect(slide, prs.slide_width, prs.slide_height, COL_PRIMARY)
    add_text(slide, 80, 64, 400, 20, "PRÓXIMOS PASSOS",
             size=13, bold=True, color=COL_ACCENT_LIME, tracking=0.2)
    add_logo(slide, 1180, 50, 60, assets_dir, "offwhite")

    ns = data.get("next_steps", [])
    primary = ns[0] if ns else None
    # Eyebrow
    add_text(slide, 80, 200, 600, 16, "UMA AÇÃO PRIORITÁRIA",
             size=11, bold=True, color=COL_BG_LIGHT, tracking=0.18)
    # Hero
    if primary:
        hero = f"{primary['action']} até {primary.get('deadline','')}"
    else:
        hero = "Sem ações cadastradas"
    add_text(slide, 80, 260, 1120, 120, hero,
             size=48, color=COL_BG_LIGHT)
    # Rationale
    if primary and primary.get("rationale"):
        add_text(slide, 80, 420, 900, 60, primary["rationale"],
                 size=14, color=COL_BG_LIGHT)
    # Divider
    add_rect(slide, 80, 600, 1120, 1, COL_BG_LIGHT)
    # Footer left
    add_text(slide, 80, 620, 600, 18,
             data.get("project", {}).get("footer_label", ""),
             size=12, color=COL_BG_LIGHT)
    # Footer right (contact)
    email = data.get("project", {}).get("pm_email") or "—"
    add_text(slide, 820, 620, 380, 18,
             f"Dúvidas: {email}", size=12, color=COL_BG_LIGHT, align="right")


# ---- Main ----

def build(data: dict, out_path: Path, assets_dir: Path):
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    slide_01_cover(prs, data, assets_dir)
    slide_02_agenda(prs, data, assets_dir)
    slide_03_roadmap_overview(prs, data, assets_dir)
    slide_04_roadmap_detail(prs, data, assets_dir)
    slide_05_section_divider(prs, data, assets_dir)
    slide_06_executive_status(prs, data, assets_dir)
    slide_07_risks(prs, data, assets_dir)
    slide_08_closing(prs, data, assets_dir)

    prs.save(str(out_path))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, type=Path)
    ap.add_argument("--assets-dir", type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    args = ap.parse_args()

    script_dir = Path(__file__).parent
    skill_dir = script_dir.parent
    assets_dir = args.assets_dir or (skill_dir / "assets")

    if not args.data.exists():
        print(f"✗ Arquivo de dados não encontrado: {args.data}", file=sys.stderr)
        sys.exit(2)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    data = json.loads(args.data.read_text(encoding="utf-8"))
    out_path = args.out_dir / "status-presentation.pptx"
    build(data, out_path, assets_dir)
    print(f"✓ PPTX gerado: {out_path}")

    if data.get("warnings"):
        print(f"⚠ {len(data['warnings'])} warning(s):", file=sys.stderr)
        for w in data["warnings"]:
            print(f"   · {w}", file=sys.stderr)


if __name__ == "__main__":
    main()
