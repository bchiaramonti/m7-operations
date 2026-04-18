"""
_lib.py — Utilitarios compartilhados pelos scripts de building-project-plan.

NAO invocar diretamente. Os scripts da skill importam via:

    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _lib import load_logo_b64, slugify, build_topbar_html, ...

Conteudo:
    - Tokens M7-2026 (cores, fonte)
    - Carregamento de logos base64
    - Helpers HTML compartilhados (topbar, page-header, footer, container)
    - Resolucao de paths (templates, assets)
    - Helpers de datas (BR locale + ISO)
"""

from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants — Design System M7-2026 (replicado em codigo Python; CSS gera-se via templates)
# ---------------------------------------------------------------------------

VERDE_CAQUI = "#424135"
LIME = "#eef77c"
OFF_WHITE = "#fffdef"
CINZA_700 = "#3d3d3d"
CINZA_400 = "#9a9a8e"
CINZA_200 = "#d9d9c8"
CINZA_100 = "#f0f0e4"
ACCENT_GREEN = "#7ab648"
ACCENT_RED = "#c0392b"

MESES_BR = {
    1: "jan", 2: "fev", 3: "mar", 4: "abr", 5: "mai", 6: "jun",
    7: "jul", 8: "ago", 9: "set", 10: "out", 11: "nov", 12: "dez",
}
MESES_BR_FULL = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho",
    7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
}

# Path do skill root (calculado relativo a este arquivo)
SKILL_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = SKILL_ROOT / "templates"
ASSETS_DIR = TEMPLATES_DIR / "assets"


# ---------------------------------------------------------------------------
# Asset loading
# ---------------------------------------------------------------------------

def load_logo_b64(variant: str = "offwhite") -> str:
    """
    Carrega o logo M7 em base64 a partir de templates/assets/.
    `variant` = "offwhite" (para fundo escuro/caqui) ou "dark" (fundo claro).
    Retorna o conteudo do arquivo .b64 sem newlines.
    """
    fname_map = {
        "offwhite": "m7-logo-offwhite.b64",
        "dark": "m7-logo-dark.b64",
    }
    if variant not in fname_map:
        raise ValueError(f"variant invalida: {variant}; use 'offwhite' ou 'dark'")
    path = ASSETS_DIR / fname_map[variant]
    if not path.exists():
        raise FileNotFoundError(f"Logo asset nao encontrado: {path}")
    return path.read_text(encoding="utf-8").strip().replace("\n", "")


def load_template(rel_path: str) -> str:
    """Le um template do diretorio templates/ por path relativo (ex: 'plano-projeto.tmpl.html' ou 'artefatos/eap.tmpl.html')."""
    path = TEMPLATES_DIR / rel_path
    if not path.exists():
        raise FileNotFoundError(f"Template nao encontrado: {path}")
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def parse_date(value):
    """Aceita datetime, ISO string YYYY-MM-DD, ou retorna None."""
    if value is None or value == "":
        return None
    if isinstance(value, dt.datetime):
        return value
    if isinstance(value, dt.date):
        return dt.datetime(value.year, value.month, value.day)
    if isinstance(value, str):
        if ISO_DATE_RE.match(value):
            return dt.datetime.strptime(value, "%Y-%m-%d")
    return None


def fmt_br(d, with_year: bool = False) -> str:
    """Formata data como '02/abr' ou '02/abr/2026'."""
    parsed = parse_date(d)
    if not parsed:
        return ""
    s = f"{parsed.day:02d}/{MESES_BR[parsed.month]}"
    if with_year:
        s += f"/{parsed.year}"
    return s


def fmt_period(start, end) -> str:
    """Formata periodo como '27/mar — 13/jul 2026' (assume mesmo ano para o final)."""
    s = parse_date(start)
    e = parse_date(end)
    if not s or not e:
        return ""
    s_str = f"{s.day:02d}/{MESES_BR[s.month]}"
    e_str = f"{e.day:02d}/{MESES_BR[e.month]} {e.year}"
    if s.year != e.year:
        s_str += f" {s.year}"
    return f"{s_str} — {e_str}"


def days_between(start, end) -> int:
    """Numero de dias entre duas datas (inclusivo)."""
    s = parse_date(start)
    e = parse_date(end)
    if not s or not e:
        return 0
    return (e - s).days + 1


def month_anchor_iso(year: int, month: int) -> str:
    return f"{year}-{month:02d}-01"


# ---------------------------------------------------------------------------
# String helpers
# ---------------------------------------------------------------------------

def html_escape(s) -> str:
    """Escape minimo para HTML (text contexts)."""
    if s is None:
        return ""
    s = str(s)
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;")
             .replace('"', "&quot;"))


def slugify(s: str) -> str:
    """Converte texto para slug kebab-case."""
    s = s.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    return s.strip("-")


# ---------------------------------------------------------------------------
# Shared HTML chunks (topbar, page-header, footer, container)
# ---------------------------------------------------------------------------

def build_topbar_html(prev_href: str, prev_label: str, title: str,
                      next_href: str, next_label: str) -> str:
    """Topbar de navegacao. prev/next labels ja incluem '←' / '→' fora do texto."""
    return (
        '<div class="topbar">\n'
        f'  <a href="{prev_href}">← {html_escape(prev_label)}</a>\n'
        f'  <span class="title">{html_escape(title)}</span>\n'
        f'  <a href="{next_href}">{html_escape(next_label)} →</a>\n'
        '</div>'
    )


def build_page_header_html(num: str, h1: str, logo_b64: str) -> str:
    """Page header padrao: numero grande + titulo + logo M7."""
    return (
        '<div class="page-header">\n'
        '  <div class="page-header-left">\n'
        f'    <div class="num">{html_escape(num)}</div>\n'
        f'    <h1>{html_escape(h1)}</h1>\n'
        '  </div>\n'
        f'  <img src="data:image/png;base64,{logo_b64}" alt="M7" class="logo">\n'
        '</div>'
    )


def build_footer_html(project_label: str, periodo: str = "") -> str:
    """Footer padrao M7."""
    suffix = f" — {periodo}" if periodo else ""
    return (
        '<div class="footer">\n'
        f'  M7 Investimentos — Equipe de Performance — {html_escape(project_label)}{html_escape(suffix)}\n'
        '</div>'
    )


def project_label(data: dict) -> str:
    """'<code> <name>' or just '<name>' if no code."""
    code = (data.get("project_code") or "").strip()
    name = (data.get("project_name") or "").strip()
    return f"{code} {name}".strip()


def project_period_label(data: dict) -> str:
    """Ex.: 'Abril 2026' a partir do period_start."""
    s = parse_date(data.get("period_start"))
    if not s:
        return ""
    return f"{MESES_BR_FULL[s.month]} {s.year}"
