#!/usr/bin/env python3
"""
build_opr.py — Render OPR (one-page report) from canonical data dict.

Inputs:
  --data <json-path>            Canonical dict from collect_data.py
  --template <path>             Jinja2 template (default: templates/opr.tmpl.html)
  --assets-dir <path>           Directory with m7-logo-*.png
  --out-dir <path>              Where to write opr.html + opr.pdf

Output files: opr.html (the rendered HTML), opr.pdf (A4 portrait).

Tries playwright first, falls back to weasyprint. Aborts if neither installed.
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
from pathlib import Path


STATUS_LABEL = {"green": "🟢 OK", "yellow": "🟡 Atenção", "red": "🔴 Crítico"}


def encode_logo(assets_dir: Path, filename: str) -> str | None:
    path = assets_dir / filename
    if not path.exists():
        return None
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode("ascii")
    return f"data:image/png;base64,{data}"


def render_html(data: dict, template_path: Path, assets_dir: Path, compact: bool = False) -> str:
    try:
        from jinja2 import Template
    except ImportError:
        raise RuntimeError("jinja2 ausente. Instale: pip install jinja2")

    template = Template(template_path.read_text(encoding="utf-8"))
    logo_url = encode_logo(assets_dir, "m7-logo-offwhite.png")

    return template.render(
        project=data.get("project", {}),
        report_date=data.get("report_date"),
        status=data.get("status", {}),
        status_label=STATUS_LABEL.get(data.get("status", {}).get("overall"), "🟢 OK"),
        highlights=data.get("highlights", []),
        next_steps=data.get("next_steps", []),
        attentions=data.get("attentions", []),
        macro_milestones=data.get("macro_milestones", []),
        logo_url=logo_url,
        compact=compact,
    )


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

    html = render_html(data, template_path, assets_dir, compact=False)
    html_path = args.out_dir / "opr.html"
    html_path.write_text(html, encoding="utf-8")

    # Try to detect overflow
    height = measure_overflow_playwright(html)
    if height and height > 1123:
        print(f"⚠ OPR excede A4 ({height}px > 1123px). Rerenderizando em modo compacto.", file=sys.stderr)
        html = render_html(data, template_path, assets_dir, compact=True)
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

    if not args.keep_html:
        pass  # keep html anyway — it is useful for the user

    if data.get("warnings"):
        print(f"⚠ {len(data['warnings'])} warning(s):", file=sys.stderr)
        for w in data["warnings"]:
            print(f"   · {w}", file=sys.stderr)


if __name__ == "__main__":
    main()
