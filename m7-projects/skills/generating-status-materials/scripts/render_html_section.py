#!/usr/bin/env python3
"""
render_html_section.py — Headless screenshot of a section of an HTML artifact.

Purpose: status materials reuse the visual artifacts produced by building-project-plan
(roadmap-marcos.html, riscos.html) as the source of visual truth. This script opens
those HTMLs locally and captures the target section as a PNG that gets embedded into
PPTX slides and the OPR HTML.

Strategy:
  - Launch chromium headless via playwright
  - Navigate to file:// URL
  - Wait for fonts + any JS-driven layout to settle
  - Optional CSS injection (to force all lanes open, hide topbar, etc.)
  - Screenshot either the full page or a specific CSS selector's bounding box

Usage examples:
  python3 render_html_section.py \
    --input /path/to/roadmap-marcos.html \
    --selector ".roadmap" \
    --viewport 1600x1000 \
    --output /tmp/roadmap.png

  python3 render_html_section.py \
    --input /path/to/roadmap-marcos.html \
    --preset roadmap-full \
    --output /tmp/roadmap.png

  python3 render_html_section.py \
    --input /path/to/roadmap-marcos.html \
    --preset mini-swimlane \
    --output /tmp/mini-swimlane.png
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


# Preset = self-contained recipe for a common status-materials screenshot use case.
#
# Each preset specifies:
#   - selector: CSS selector to crop (None = full page)
#   - viewport: (width, height) for chromium window
#   - device_scale: 2.0 = retina quality (larger output file, sharper text)
#   - inject_css: CSS string to force-open lanes, hide chrome, etc.
PRESETS: dict[str, dict] = {
    "roadmap-full": {
        # For PPTX Slide 4 (Roadmap Detalhado): full swim-lane, all lanes expanded,
        # generous viewport so the last milestone (M7) fits without clipping.
        "selector": ".roadmap",
        "viewport": (2400, 1300),
        "device_scale": 2.0,
        "inject_css": """
          .topbar, .roadmap-controls, .site-footer { display: none !important; }
          .lane-toggle, .phase-toggle { pointer-events: none; }
          .lane.collapsed .bars, .lane.collapsed .track { display: block !important; }
          .lane.collapsed { max-height: none !important; }
          body { background: #fffdef !important; padding: 20px !important; }
          /* Ensure roadmap uses full viewport width so last column isn't clipped */
          .roadmap { min-width: 2300px !important; }
        """,
    },
    "phase-bar": {
        # For PPTX Slide 3 (Visão Geral Roadmap): condensed phase-bar summary only.
        "selector": ".phase-bar, .phases, section.phases",
        "viewport": (1800, 600),
        "device_scale": 2.0,
        "inject_css": """
          .topbar, .site-footer { display: none !important; }
          body { background: #fffdef !important; padding: 20px !important; }
        """,
    },
    "marcos-lane": {
        # For PPTX Slide 3 (Marcos do Projeto): just the top .lane.milestones strip,
        # which contains the M0-M7 gate ticks on a horizontal timeline.
        "selector": ".lane.milestones",
        "viewport": (2400, 500),
        "device_scale": 2.0,
        "inject_css": """
          .topbar, .roadmap-controls, .site-footer { display: none !important; }
          body { background: #fffdef !important; padding: 20px !important; }
          .lane.milestones { min-width: 2300px !important; background: transparent !important; }
          .lane.milestones .track { padding: 40px 0 !important; }
        """,
    },
    "mini-swimlane": {
        # For OPR (one-page report): reduced swim-lane for 1-page A4 embed.
        "selector": ".roadmap",
        "viewport": (1200, 700),
        "device_scale": 1.5,
        "inject_css": """
          .topbar, .roadmap-controls, .site-footer { display: none !important; }
          .lane.collapsed .bars, .lane.collapsed .track { display: block !important; }
          .lane.collapsed { max-height: none !important; }
          body { background: #fffdef !important; padding: 10px !important; font-size: 11px !important; }
        """,
    },
    "roadmap-full-with-status-overlays": {
        # Same as roadmap-full but with CSS for status-colored bars and the HOJE vertical line.
        # The chamador must pass `extra_js` (built via build_roadmap_overlay_js) to apply dynamic data.
        "selector": ".roadmap",
        "viewport": (2400, 1300),
        "device_scale": 2.0,
        "inject_css": """
          .topbar, .roadmap-controls, .site-footer { display: none !important; }
          .lane-toggle, .phase-toggle { pointer-events: none; }
          .lane.collapsed .bars, .lane.collapsed .track { display: block !important; }
          .lane.collapsed { max-height: none !important; }
          body { background: #fffdef !important; padding: 20px !important; }
          .roadmap { min-width: 2300px !important; }

          /* Status-based bar coloring (applied by build_roadmap_overlay_js at runtime) */
          .bar.bar-status-done      { background: #00B050 !important; }
          .bar.bar-status-active    { background: #3B82F6 !important; }
          .bar.bar-status-overdue   { background: #E46962 !important; }
          .bar.bar-status-future    { opacity: 0.50 !important; }

          /* HOJE vertical line inside each .track (aligned across all lanes by left%) */
          .hoje-line {
            position: absolute;
            top: 0; bottom: 0;
            width: 2px;
            background: #E46962;
            z-index: 100;
            pointer-events: none;
          }
          .hoje-line[data-label]::before {
            content: attr(data-label);
            position: absolute;
            top: -22px;
            left: -30px;
            font-size: 11px;
            font-weight: 700;
            color: #E46962;
            letter-spacing: 0.08em;
            white-space: nowrap;
            background: #fffdef;
            padding: 2px 6px;
            border: 1px solid #E46962;
            border-radius: 2px;
          }
        """,
    },
    "risks-heatmap": {
        # For PPTX or OPR: riscos.html heat-map 3x3 matrix only.
        "selector": ".heat-map, .matrix-container",
        "viewport": (900, 700),
        "device_scale": 2.0,
        "inject_css": """
          .topbar, .site-footer { display: none !important; }
          body { background: #fffdef !important; padding: 16px !important; }
        """,
    },
}


def render(
    input_path: Path,
    output_path: Path,
    selector: str | None = None,
    viewport: tuple[int, int] = (1600, 1000),
    device_scale: float = 2.0,
    inject_css: str = "",
    extra_js: str = "",
    wait_ms: int = 600,
) -> None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise RuntimeError(
            "playwright ausente. Instale:\n"
            "  pip install playwright && python3 -m playwright install chromium"
        )

    if not input_path.exists():
        raise FileNotFoundError(f"HTML input não encontrado: {input_path}")

    url = f"file://{input_path.resolve()}"

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": viewport[0], "height": viewport[1]},
            device_scale_factor=device_scale,
        )
        page = context.new_page()
        page.goto(url, wait_until="networkidle")

        # Inject CSS tweaks before measuring layout
        if inject_css:
            page.add_style_tag(content=inject_css)

        # Inject JS for dynamic DOM modifications (e.g., HOJE line, bar coloring).
        # Runs after CSS injection so classes added here pick up the new styles.
        if extra_js:
            page.evaluate(extra_js)

        # Wait for custom fonts + any post-load layout shifts
        try:
            page.evaluate("document.fonts.ready")
        except Exception:
            pass
        page.wait_for_timeout(wait_ms)

        output_path.parent.mkdir(parents=True, exist_ok=True)

        if selector:
            # Try multiple selectors (comma-separated) and pick the first that matches
            el = None
            for sel in [s.strip() for s in selector.split(",")]:
                el = page.query_selector(sel)
                if el:
                    break
            if not el:
                raise RuntimeError(
                    f"Selector '{selector}' não encontrou nenhum elemento em {input_path.name}"
                )
            el.screenshot(path=str(output_path), omit_background=False)
        else:
            page.screenshot(path=str(output_path), full_page=True, omit_background=False)

        browser.close()


def build_roadmap_overlay_js(today_pct: float | None, today_label: str, bar_status_map: dict) -> str:
    """Composes a self-contained JS string that, when executed via playwright's
    page.evaluate(), performs two DOM modifications on the roadmap-marcos.html:

      1. Colors each `.bar` by adding class `.bar-status-{done|active|overdue|future}`
         based on a lookup by its `.title` text in `bar_status_map`.
      2. Appends a vertical `.hoje-line` to each `.track` element at horizontal
         position `today_pct%` (so the line is visible across every lane).

    The CSS for these classes is assumed to be injected via `inject_css` (see the
    `roadmap-full-with-status-overlays` preset below). Safe to call even when
    today_pct is None (it'll simply skip the HOJE line).
    """
    import json as _json
    today_pct_js = "null" if today_pct is None else f"{today_pct:.4f}"
    return f"""
    (function() {{
        const TODAY_PCT = {today_pct_js};
        const TODAY_LABEL = {_json.dumps(today_label)};
        const BAR_STATUS_MAP = {_json.dumps(bar_status_map, ensure_ascii=True)};

        // 1. Color each .bar by its title
        document.querySelectorAll('.bar').forEach(function(bar) {{
            const titleEl = bar.querySelector('.title');
            if (!titleEl) return;
            const title = titleEl.textContent.trim();
            const status = BAR_STATUS_MAP[title];
            if (status) bar.classList.add('bar-status-' + status);
        }});

        // 2. Add HOJE vertical line inside each track (aligned by left% across all lanes)
        if (TODAY_PCT !== null) {{
            document.querySelectorAll('.track').forEach(function(track, idx) {{
                const cs = window.getComputedStyle(track);
                if (cs.position === 'static') track.style.position = 'relative';
                const line = document.createElement('div');
                line.className = 'hoje-line';
                line.style.left = TODAY_PCT + '%';
                // Only the first track gets the text label (avoid repetition down the column)
                if (idx === 0) line.setAttribute('data-label', TODAY_LABEL);
                track.appendChild(line);
            }});
        }}
    }})();
    """


def main():
    p = argparse.ArgumentParser(description="Headless screenshot of HTML section")
    p.add_argument("--input", required=True, type=Path, help="Path to HTML artifact")
    p.add_argument("--output", required=True, type=Path, help="Destination PNG path")
    p.add_argument("--selector", help="CSS selector to crop (comma-separated fallbacks)")
    p.add_argument("--preset", choices=list(PRESETS.keys()), help="Use a predefined recipe")
    p.add_argument("--viewport", help="WxH (e.g. '1600x1000'). Ignored if --preset provided.")
    p.add_argument("--device-scale", type=float, default=2.0)
    p.add_argument("--inject-css", default="", help="Extra CSS to inject before screenshot")
    args = p.parse_args()

    if args.preset:
        preset = PRESETS[args.preset]
        selector = args.selector or preset["selector"]
        viewport = preset["viewport"]
        device_scale = preset["device_scale"]
        inject_css = (preset["inject_css"] + "\n" + args.inject_css).strip()
    else:
        selector = args.selector
        if args.viewport:
            try:
                w, h = args.viewport.lower().split("x")
                viewport = (int(w), int(h))
            except ValueError:
                print(f"✗ --viewport inválido: {args.viewport} (esperado 'WxH')", file=sys.stderr)
                sys.exit(2)
        else:
            viewport = (1600, 1000)
        device_scale = args.device_scale
        inject_css = args.inject_css

    try:
        render(
            input_path=args.input,
            output_path=args.output,
            selector=selector,
            viewport=viewport,
            device_scale=device_scale,
            inject_css=inject_css,
        )
    except Exception as e:
        print(f"✗ {e}", file=sys.stderr)
        sys.exit(2)

    size = args.output.stat().st_size
    print(f"✓ Screenshot salvo: {args.output} ({size // 1024} KB)")


if __name__ == "__main__":
    main()
