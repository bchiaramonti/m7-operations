#!/usr/bin/env python3
"""
collect_data.py — Deterministic data collection for generating-status-materials.

Reads:
  - <proj>/CLAUDE.md
  - <proj>/BRIEFING.md (if present)
  - <proj>/1-planning/plano-projeto.html + artefatos/*.html
  - <proj>/4-status-report/Cronograma.xlsx (LIVE)
  - <proj>/4-status-report/changelog.md
  - <proj>/4-status-report/.sync-state.json (optional)

Emits a canonical JSON dict on stdout consumed by build_opr.py and build_pptx.py.

Pure Python: no MCP calls, no LLM inference. All narrative synthesis is
deterministic (rules in references/narrative-synthesis.md).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


CANONICAL_COLUMNS = {
    "No.": "no",
    "Tipo": "tipo",
    "Etapa": "etapa",
    "Responsável": "responsavel",
    "Responsavel": "responsavel",
    "Início Planejado": "inicio_plan",
    "Inicio Planejado": "inicio_plan",
    "Fim Planejado": "fim_plan",
    "Início Real": "inicio_real",
    "Inicio Real": "inicio_real",
    "Fim Real": "fim_real",
    "Status": "status",
    "Entregável": "entregavel",
    "Entregavel": "entregavel",
    "ClickUp ID": "clickup_id",
}
REQUIRED_COLUMNS = {"no", "tipo", "etapa", "status", "fim_plan"}

DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d/%m", "%d/%b/%Y", "%d/%b")

MONTH_PT = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
}

# Portuguese abbreviated month names → English (locale "C" uses English %b).
# Used to pre-translate dates like "14/abr" before parsing.
MONTH_PT_ABBREV_TO_EN = {
    "jan": "jan", "fev": "feb", "mar": "mar", "abr": "apr",
    "mai": "may", "jun": "jun", "jul": "jul", "ago": "aug",
    "set": "sep", "out": "oct", "nov": "nov", "dez": "dec",
}


@dataclass
class CollectResult:
    report_date: str
    project: dict = field(default_factory=dict)
    status: dict = field(default_factory=dict)
    highlights: list = field(default_factory=list)
    next_steps: list = field(default_factory=list)
    attentions: list = field(default_factory=list)
    milestones: list = field(default_factory=list)
    macro_milestones: list = field(default_factory=list)
    sprints: list = field(default_factory=list)
    fronts: list = field(default_factory=list)
    sprint_actions: list = field(default_factory=list)
    risks: list = field(default_factory=list)
    changelog_entries: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "report_date": self.report_date,
            "project": self.project,
            "status": self.status,
            "highlights": self.highlights,
            "next_steps": self.next_steps,
            "attentions": self.attentions,
            "milestones": self.milestones,
            "macro_milestones": self.macro_milestones,
            "sprints": self.sprints,
            "fronts": self.fronts,
            "sprint_actions": self.sprint_actions,
            "risks": self.risks,
            "changelog_entries": self.changelog_entries,
            "warnings": self.warnings,
        }


def normalize_date(value, default_year: int) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        s = value.strip()
        if s in ("—", "-", ""):
            return None
        # Pre-translate Portuguese month abbreviations to English to match %b in C locale
        s_translated = s
        for pt, en in MONTH_PT_ABBREV_TO_EN.items():
            # Case-insensitive replace of 3-letter PT abbrev when bordered by / or end
            s_translated = re.sub(
                rf"(?<=/){pt}(?=/|$)",
                en,
                s_translated,
                flags=re.IGNORECASE,
            )
        for candidate in (s, s_translated):
            for fmt in DATE_FORMATS:
                try:
                    dt = datetime.strptime(candidate, fmt)
                    if dt.year == 1900:
                        dt = dt.replace(year=default_year)
                    return dt
                except ValueError:
                    continue
    return None


def parent_no(no: str) -> str | None:
    parts = str(no).split(".")
    if len(parts) <= 1:
        return None
    return ".".join(parts[:-1])


# ---------- Readers ----------

def read_cronograma_live(path: Path, default_year: int, warnings: list) -> list[dict]:
    try:
        from openpyxl import load_workbook
    except ImportError:
        raise RuntimeError("openpyxl ausente. Instale: pip install openpyxl")

    wb = load_workbook(path, data_only=True, read_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if len(rows) < 5:
        raise ValueError("Cronograma.xlsx com menos de 5 linhas — schema esperado tem header em R4.")

    header_row = rows[3]
    col_map: dict[int, str] = {}
    for idx, val in enumerate(header_row):
        if isinstance(val, str) and val.strip() in CANONICAL_COLUMNS:
            col_map[idx] = CANONICAL_COLUMNS[val.strip()]

    present = set(col_map.values())
    missing_required = REQUIRED_COLUMNS - present
    if missing_required:
        raise ValueError(
            f"Cronograma.xlsx faltando colunas obrigatórias: {sorted(missing_required)}"
        )

    entries = []
    for row_num, row in enumerate(rows[4:], start=5):
        if not row or all(v is None for v in row):
            continue
        entry: dict[str, Any] = {"_row": row_num}
        for idx, canonical in col_map.items():
            if idx < len(row):
                entry[canonical] = row[idx]
        if not entry.get("no"):
            continue
        # Normalize dates
        for date_field in ("inicio_plan", "fim_plan", "inicio_real", "fim_real"):
            if date_field in entry:
                entry[date_field] = normalize_date(entry[date_field], default_year)
        # Normalize status
        status = entry.get("status")
        if status and status not in ("not_started", "in_progress", "blocked", "done"):
            warnings.append(f"Cronograma linha {row_num}: status '{status}' fora do enum — tratando como not_started")
            entry["status"] = "not_started"
        entries.append(entry)
    return entries


def read_changelog(path: Path) -> list[dict]:
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    entries = []
    # Pattern: ## YYYY-MM-DD HH:MM — op
    header_pat = re.compile(r"^##\s+(\d{4}-\d{2}-\d{2})(?:[T ](\d{2}:\d{2}))?\s*[—-]\s*(\w+)", re.MULTILINE)
    matches = list(header_pat.finditer(text))
    for i, m in enumerate(matches):
        date_str, time_str, op = m.group(1), m.group(2) or "00:00", m.group(3)
        ts = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[m.end():end].strip()
        entry = {"timestamp": ts.isoformat(), "op": op, "text": body, "raw": body}
        # Try to extract common fields
        for field_name in ("No.", "Campo", "Antes", "Depois", "Por"):
            pat = re.compile(rf"\*\*{re.escape(field_name)}:\*\*\s*(.+)")
            mm = pat.search(body)
            if mm:
                key = {"No.": "no", "Campo": "field", "Antes": "old", "Depois": "new", "Por": "by"}[field_name]
                entry[key] = mm.group(1).strip()
        entries.append(entry)
    return entries


def read_sync_state(path: Path, report_date: datetime, warnings: list) -> dict:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        warnings.append(f".sync-state.json inválido: {e}")
        return {}
    if data.get("sync_pending"):
        warnings.append("sync_pending=true — execute `managing-action-plan sync` antes do reporte para dados frescos")
    last_sync = data.get("last_sync")
    if last_sync:
        try:
            last_dt = datetime.fromisoformat(last_sync)
            age = report_date - last_dt
            if age > timedelta(hours=48):
                hours = int(age.total_seconds() / 3600)
                warnings.append(f"Sync stale: última sync há {hours}h ({last_sync})")
        except ValueError:
            pass
    return data


def read_html_text(path: Path, warnings: list, label: str) -> dict:
    """Loosely parses an HTML and returns {title, text, metadata}."""
    if not path.exists():
        warnings.append(f"{label}: arquivo não encontrado em {path}")
        return {}
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        raise RuntimeError("beautifulsoup4 ausente. Instale: pip install beautifulsoup4")
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
    title_tag = soup.find("h1") or soup.find("title")
    return {
        "title": title_tag.get_text(strip=True) if title_tag else None,
        "soup": soup,
    }


def parse_risks(path: Path, warnings: list) -> list[dict]:
    """Parses .risk-item cards from the riscos.html artifact produced by building-project-plan.

    Schema extracted per card:
      - .risk-id (text = code like "R01"/"O01"; class in {crit, high, med, low} = severity)
      - .risk-content > h4 = title
      - .risk-content > .tags > .tag-prob = "Prob: Alta/Média/Baixa"
      - .risk-content > .tags > .tag-imp  = "Imp: Crítico/Alto/Médio/Baixo"
      - .risk-content > p                 = description
      - .risk-content > .mitigation > span = contramedida
    """
    if not path.exists():
        warnings.append("riscos.html não encontrado — seção Riscos vazia")
        return []
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return []
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
    risks = []

    sev_class_map = {"crit": "critico", "high": "alto", "med": "medio", "low": "baixo"}

    for idx, card in enumerate(soup.select(".risk-item"), 1):
        id_el = card.select_one(".risk-id")
        code = id_el.get_text(strip=True) if id_el else f"R{idx:02d}"

        # Severity comes from the class of .risk-id (crit/high/med/low).
        # This is the authoritative visual severity from the plan.
        sev_raw = "low"
        if id_el:
            for c in id_el.get("class", []):
                if c in sev_class_map:
                    sev_raw = c
                    break
        severity_label = sev_class_map[sev_raw]

        title_el = card.select_one(".risk-content h4") or card.select_one("h4")
        title = title_el.get_text(strip=True) if title_el else ""

        prob_el = card.select_one(".tag-prob")
        prob_text = prob_el.get_text(strip=True) if prob_el else ""
        prob_value = _extract_after_colon(prob_text)

        imp_el = card.select_one(".tag-imp")
        imp_text = imp_el.get_text(strip=True) if imp_el else ""
        imp_value = _extract_after_colon(imp_text)

        desc_el = card.select_one(".risk-content > p")
        description = desc_el.get_text(" ", strip=True) if desc_el else ""

        mitig_el = card.select_one(".mitigation span") or card.select_one(".mitigation")
        mitigation = ""
        if mitig_el:
            raw = mitig_el.get_text(" ", strip=True)
            # Remove leading "Ação de Mitigação" header if present
            mitigation = re.sub(r"^Ação de Mitigação\s*", "", raw).strip()

        is_upside = code.upper().startswith("O")

        risks.append({
            "code": code,
            "title": title,
            "probability": _normalize_level(prob_value),
            "impact": _normalize_impact(imp_value),
            "severity": severity_label,
            "severity_class": sev_raw,
            "description": description,
            "mitigation": mitigation,
            "is_upside": is_upside,
        })

    if not risks:
        warnings.append("riscos.html: nenhum .risk-item encontrado — verifique se o arquivo foi gerado por building-project-plan")
    return risks


def _extract_after_colon(text: str) -> str:
    """Parses labels like 'Prob: Alta' or 'Imp: Crítico' -> 'alta' / 'crítico'."""
    if ":" in text:
        return text.split(":", 1)[1].strip().lower()
    return text.strip().lower()


def _normalize_level(s: str) -> str:
    s = s.strip().lower()
    if "alt" in s:
        return "alta"
    if "med" in s or "méd" in s:
        return "media"
    return "baixa"


def _normalize_impact(s: str) -> str:
    s = s.strip().lower()
    if "crít" in s or "crit" in s:
        return "critico"
    if "alt" in s:
        return "alto"
    if "med" in s or "méd" in s:
        return "medio"
    return "baixo"


def parse_plano_projeto(path: Path, warnings: list) -> dict:
    data = read_html_text(path, warnings, "plano-projeto.html")
    if not data:
        return {}
    soup = data["soup"]
    result = {"name": data.get("title")}
    # Common patterns: .hero-meta data-key="pm", .hero-meta__pm, etc.
    for key in ("pm", "lider", "líder", "sponsor", "duracao", "duração", "goal", "objetivo", "estrela"):
        el = soup.select_one(f"[data-key='{key}']") or soup.select_one(f".hero-meta__{key}")
        if el:
            result_key = {"lider": "pm", "líder": "pm", "objetivo": "goal"}.get(key, key)
            result[result_key] = el.get_text(strip=True)
    return result


def parse_milestones(path: Path, warnings: list, default_year: int, report_date: datetime) -> list[dict]:
    """Parses project milestones from roadmap-marcos.html.

    Looks for the canonical structure produced by building-project-plan:
      .lane.milestones > .track > .tick.{top|bottom}.{gate|regular}
        ├ .lbl  ("M0 KICKOFF")
        ├ .date ("14/abr")
        └ .desc ("TAP + OKRs aprovados")

    Status is inferred deterministically by date:
      - date <= report_date  → "done"   (treat as passed)
      - date == report_date ± 3 days → "in_progress"
      - date > report_date   → "not_started"

    `major` flag is True for .gate ticks (critical gates), False for .regular (informational).
    """
    if not path.exists():
        warnings.append("roadmap-marcos.html não encontrado — lista de marcos vazia")
        return []
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return []
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")

    milestones = []
    # Primary: ticks inside the milestones lane
    for tick in soup.select(".lane.milestones .tick"):
        lbl_el = tick.select_one(".lbl")
        date_el = tick.select_one(".date")
        desc_el = tick.select_one(".desc")
        if not lbl_el or not date_el:
            continue
        label = lbl_el.get_text(" ", strip=True)
        date_str = date_el.get_text(strip=True)
        dt = normalize_date(date_str, default_year)

        # Classes: tick top|bottom gate|regular
        classes = tick.get("class", [])
        is_gate = "gate" in classes

        if dt is None:
            status = "not_started"
        else:
            delta_days = (report_date - dt).days
            if delta_days > 3:
                status = "done"
            elif delta_days >= -3:
                status = "in_progress"
            else:
                status = "not_started"

        milestones.append({
            "code": label.split()[0] if label else "",
            "label": label,
            "name": label,
            "date": dt.strftime("%Y-%m-%d") if dt else None,
            "date_short": date_str,
            "description": desc_el.get_text(" ", strip=True) if desc_el else "",
            "status": status,
            "is_critical": is_gate,
            "major": is_gate,
        })

    # Fallback: generic .milestone lookup (legacy HTML structure)
    if not milestones:
        for item in soup.select(".milestone, [data-milestone], li.milestone"):
            name_el = item.select_one(".name, .title, h4")
            date_el = item.select_one(".date, [data-key='date'], time")
            if not name_el:
                continue
            date_val = None
            if date_el:
                date_val = date_el.get("datetime") or date_el.get_text(strip=True)
            dt = normalize_date(date_val, default_year) if date_val else None
            status = "not_started"
            if dt:
                delta = (report_date - dt).days
                status = "done" if delta > 3 else ("in_progress" if delta >= -3 else "not_started")
            milestones.append({
                "code": "",
                "label": name_el.get_text(strip=True),
                "name": name_el.get_text(strip=True),
                "date": dt.strftime("%Y-%m-%d") if dt else None,
                "date_short": date_val if isinstance(date_val, str) else None,
                "description": "",
                "status": status,
                "is_critical": "critical" in (item.get("class") or []),
                "major": "critical" in (item.get("class") or []),
            })

    return milestones


def parse_briefing(path: Path, warnings: list) -> dict:
    if not path.exists():
        warnings.append("BRIEFING.md não encontrado — project.goal pode estar incompleto")
        return {}
    text = path.read_text(encoding="utf-8")
    result = {}
    # Extract Objetivo section (first paragraph)
    m = re.search(r"^##\s+Objetivo\s*\n\s*\n?(.+?)(?=\n##|\Z)", text, re.DOTALL | re.MULTILINE | re.IGNORECASE)
    if m:
        para = m.group(1).strip().split("\n\n")[0]
        result["goal"] = para.strip()
    return result


def parse_claude_md(path: Path, warnings: list) -> dict:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    result = {}
    m = re.search(r"clickup_list_id:\s*(\S+)", text)
    if m:
        result["clickup_list_id"] = m.group(1).strip()
    m = re.search(r"email:\s*(\S+@\S+)", text)
    if m:
        result["pm_email"] = m.group(1).strip()
    return result


# ---------- Synthesis (deterministic heuristics) ----------

def synthesize(
    entries: list[dict],
    risks: list[dict],
    changelog: list[dict],
    milestones: list[dict],
    report_date: datetime,
    warnings: list,
) -> dict:
    actions = [e for e in entries if str(e.get("tipo", "")).lower() in ("ação", "acao")]
    phases = [e for e in entries if str(e.get("tipo", "")).lower() == "fase"]

    total = len(actions)
    done = sum(1 for a in actions if a.get("status") == "done")
    overdue = sum(
        1 for a in actions
        if a.get("status") != "done"
        and a.get("fim_plan")
        and isinstance(a["fim_plan"], datetime)
        and a["fim_plan"] < report_date
    )
    pct_done = round(100 * done / total) if total else 0

    # Status overall
    overall = "green"
    if total and overdue / total > 0.20:
        overall = "red"
    else:
        for m in milestones:
            if m.get("status") == "overdue" and m.get("is_critical"):
                overall = "red"
                break
        if overall != "red":
            for r in risks:
                if r["probability"] == "alta" and r["impact"] in ("critico", "alto") and not r.get("mitigation"):
                    overall = "red"
                    break
        if overall != "red" and total and overdue / total > 0.10:
            overall = "yellow"
        if overall == "green":
            for m in milestones:
                if m.get("status") == "overdue":
                    overall = "yellow"
                    break
        if overall == "green":
            for r in risks:
                if r["probability"] == "alta" or r["impact"] in ("critico", "alto"):
                    overall = "yellow"
                    break

    # Active sprint = first Fase not done with Fim Planejado >= report_date (ou a mais antiga em andamento)
    active_sprint = None
    active_idx = 0
    for i, phase in enumerate(sorted(phases, key=lambda p: p.get("inicio_plan") or datetime.max), 1):
        if phase.get("status") != "done":
            active_sprint = phase
            active_idx = i
            break

    # Highlights
    window_days = 14
    cutoff = report_date - timedelta(days=window_days)
    candidates = []
    for action in actions:
        if action.get("status") == "done" and isinstance(action.get("fim_real"), datetime) and action["fim_real"] >= cutoff:
            candidates.append({
                "text": f"Concluiu: {truncate(action.get('etapa', ''), 90)}",
                "date": action["fim_real"],
                "priority": 10,
            })
    for phase in phases:
        if isinstance(phase.get("fim_real"), datetime) and phase["fim_real"] >= cutoff:
            candidates.append({
                "text": f"Atingiu marco: {truncate(phase.get('etapa', ''), 80)}",
                "date": phase["fim_real"],
                "priority": 15,
            })
    keywords = ("decidido", "aprovado", "definido", "validado")
    for entry in changelog:
        if entry.get("op") == "comment" and any(k in entry.get("text", "").lower() for k in keywords):
            candidates.append({
                "text": f"Decidiu: {truncate(entry['text'], 90)}",
                "date": datetime.fromisoformat(entry["timestamp"]),
                "priority": 8,
            })
    candidates.sort(key=lambda c: (-c["priority"], -c["date"].timestamp()))
    highlights = [c["text"] for c in candidates[:5]]

    # Next steps
    lookahead = report_date + timedelta(days=14)
    next_candidates = []
    for phase in phases:
        ip = phase.get("inicio_plan")
        if isinstance(ip, datetime) and report_date <= ip <= lookahead:
            next_candidates.append({
                "action": f"Iniciar {truncate(phase.get('etapa', ''), 80)}",
                "deadline": ip.strftime("%d/%m"),
                "deadline_full": ip.strftime("%Y-%m-%d"),
                "rationale": f"Gate de entrada da fase {phase.get('no', '')}",
                "priority": 15,
            })
    for action in actions:
        status = action.get("status")
        fp = action.get("fim_plan")
        if status == "blocked":
            next_candidates.append({
                "action": f"Desbloquear: {truncate(action.get('etapa', ''), 80)}",
                "deadline": fp.strftime("%d/%m") if isinstance(fp, datetime) else "—",
                "deadline_full": fp.strftime("%Y-%m-%d") if isinstance(fp, datetime) else None,
                "rationale": "Bloqueio ativo — impede progresso",
                "priority": 20,
            })
        elif status != "done" and isinstance(fp, datetime) and report_date <= fp <= lookahead:
            next_candidates.append({
                "action": truncate(action.get("etapa", ""), 90),
                "deadline": fp.strftime("%d/%m"),
                "deadline_full": fp.strftime("%Y-%m-%d"),
                "rationale": f"Responsável: {action.get('responsavel', '—')}",
                "priority": 10,
            })
    next_candidates.sort(
        key=lambda c: (-c["priority"], c.get("deadline_full") or "9999")
    )
    next_steps = next_candidates[:5]

    # Attentions — prefer authoritative severity_class from riscos.html;
    # skip upsides (codes starting with O = Oportunidade, not risk to watch).
    attentions = []
    for risk in risks:
        if risk.get("is_upside"):
            continue
        sc = risk.get("severity_class") or ""
        if sc == "crit":
            sev = "critical"
        elif sc == "high":
            sev = "warning"
        else:
            # Fallback: derive from prob×impact for legacy data without severity_class
            sev = _risk_severity(risk.get("probability", ""), risk.get("impact", ""))
        if sev in ("critical", "warning"):
            attentions.append({
                "severity": sev,
                "text": f"{risk['code']} — {truncate(risk['title'], 90)}",
                "source": "risk",
            })
    for action in actions:
        if action.get("status") == "blocked":
            attentions.append({
                "severity": "critical",
                "text": f"Bloqueado: {truncate(action.get('etapa', ''), 85)}",
                "source": "blocked",
            })
    if total and overdue:
        pct_overdue = round(100 * overdue / total)
        attentions.append({
            "severity": "warning" if pct_overdue <= 20 else "critical",
            "text": f"{overdue} ação(ões) atrasada(s) ({pct_overdue}% do total)",
            "source": "overdue_summary",
        })
    order = {"critical": 0, "warning": 1, "neutral": 2}
    attentions.sort(key=lambda a: order.get(a["severity"], 99))
    attentions = attentions[:5]

    # Macro milestones — prefer gates M0-M7 parsed from roadmap-marcos.html (canonical
    # source of visual truth from building-project-plan). Falls back to xlsx root phases
    # only if the HTML artifact is absent or doesn't have a .milestones lane.
    root_phases = [p for p in phases if p.get("no") and "." not in str(p["no"])]
    root_phases.sort(key=lambda p: p.get("inicio_plan") or datetime.max)

    if milestones:
        # Show all milestones up to 8 (full M0-M7 strip like the Paper artboard).
        # If there are more than 8, filter to .gate (major) to avoid clutter.
        chosen = milestones if len(milestones) <= 8 else [m for m in milestones if m.get("major")]
        macro_milestones = [
            {
                "label": truncate(m.get("label", ""), 22),
                "status": m.get("status", "not_started"),
                "date": m.get("date"),
                "date_short": m.get("date_short"),
                "description": m.get("description", ""),
                "code": m.get("code", ""),
                "major": m.get("major", False),
            }
            for m in chosen[:8]
        ]
    else:
        macro_milestones = []
        for p in root_phases[:7]:
            status = "not_started"
            if p.get("status") == "done":
                status = "done"
            elif isinstance(p.get("fim_plan"), datetime) and p["fim_plan"] < report_date and p.get("status") != "done":
                status = "overdue"
            elif p.get("status") == "in_progress":
                status = "in_progress"
            macro_milestones.append({
                "label": truncate(p.get("etapa", ""), 28),
                "status": status,
                "no": p.get("no"),
            })

    # Sprints — simplified: treat root phases as sprints
    sprints = []
    for i, p in enumerate(root_phases, 1):
        period = ""
        if isinstance(p.get("inicio_plan"), datetime) and isinstance(p.get("fim_plan"), datetime):
            period = f"{p['inicio_plan'].strftime('%d/%b')} → {p['fim_plan'].strftime('%d/%b')}"
        sprint_status = "future"
        if active_sprint and p.get("no") == active_sprint.get("no"):
            sprint_status = "active"
        elif p.get("status") == "done":
            sprint_status = "done"
        sprints.append({
            "code": f"S{i - 1}",
            "title": p.get("etapa", ""),
            "period_label": period,
            "status": sprint_status,
            "no": p.get("no"),
            "fronts": [],
        })

    # Hero sentences
    hero_executive = f"{done} de {total} tarefas concluídas ({pct_done}%)" if total else "Sem ações cadastradas"
    active_count = sum(1 for s in sprints if s["status"] == "active")
    sprint_progress = f"{active_count} de {len(sprints)} sprint(s) em execução" if sprints else "Sem sprints"
    # Exclude upsides (O01, O02...) from risk counting — they are opportunities, not threats
    actual_risks = [r for r in risks if not r.get("is_upside")]
    critical_risks = sum(1 for r in actual_risks if r.get("severity_class") == "crit")
    high_risks = sum(1 for r in actual_risks if r.get("severity_class") == "high")
    if not actual_risks:
        risks_sentence = "Nenhum risco mapeado"
    elif critical_risks:
        risks_sentence = f"{len(actual_risks)} risco(s) mapeado(s) — {critical_risks} crítico(s)"
    elif high_risks:
        risks_sentence = f"{len(actual_risks)} risco(s) mapeado(s) — {high_risks} alto(s)"
    else:
        risks_sentence = f"{len(actual_risks)} risco(s) mapeado(s) — severidade média/baixa"

    return {
        "overall": overall,
        "percent_done": pct_done,
        "total_actions": total,
        "done_actions": done,
        "overdue_actions": overdue,
        "active_sprint": (
            {
                "code": f"S{next((i for i, p in enumerate(root_phases) if p.get('no') == active_sprint.get('no')), 0)}",
                "no": active_sprint.get("no"),
                "title": active_sprint.get("etapa"),
                "phase_name": (active_sprint.get("etapa") or "").upper()[:24],
                "eyebrow": f"S{active_idx - 1} · {(active_sprint.get('etapa') or '').upper()[:22]}",
                "period_label": _format_period(active_sprint),
            }
            if active_sprint else None
        ),
        "active_sprint_index": active_idx,
        "total_sprints": len(sprints),
        "hero_sentence": hero_executive,
        "sprint_progress_sentence": sprint_progress,
        "risks_sentence": risks_sentence,
        "_highlights": highlights,
        "_next_steps": next_steps,
        "_attentions": attentions,
        "_macro_milestones": macro_milestones,
        "_sprints": sprints,
    }


def _format_period(phase: dict) -> str:
    ip = phase.get("inicio_plan")
    fp = phase.get("fim_plan")
    if isinstance(ip, datetime) and isinstance(fp, datetime):
        return f"{ip.strftime('%d/%b')} → {fp.strftime('%d/%b')}"
    return ""


def _risk_severity(prob: str, impact: str) -> str:
    if prob == "alta" and impact in ("critico", "alto"):
        return "critical"
    if prob in ("alta", "media") or impact in ("critico", "alto"):
        return "warning"
    return "neutral"


def truncate(s: str, max_len: int) -> str:
    s = (s or "").strip()
    return s if len(s) <= max_len else s[: max_len - 1].rstrip() + "…"


# ---------- Main ----------

def collect(project_dir: Path, report_date_str: str) -> dict:
    report_date = datetime.strptime(report_date_str, "%Y-%m-%d")
    warnings: list = []

    xlsx = project_dir / "4-status-report" / "Cronograma.xlsx"
    if not xlsx.exists():
        raise FileNotFoundError(
            f"Cronograma LIVE não inicializado: {xlsx}\n"
            f"Rode `managing-action-plan init` primeiro."
        )

    entries = read_cronograma_live(xlsx, default_year=report_date.year, warnings=warnings)
    changelog = read_changelog(project_dir / "4-status-report" / "changelog.md")
    sync_state = read_sync_state(
        project_dir / "4-status-report" / ".sync-state.json",
        report_date,
        warnings,
    )
    plano_data = parse_plano_projeto(project_dir / "1-planning" / "plano-projeto.html", warnings)
    briefing = parse_briefing(project_dir / "BRIEFING.md", warnings)
    claude_data = parse_claude_md(project_dir / "CLAUDE.md", warnings)
    risks = parse_risks(project_dir / "1-planning" / "artefatos" / "riscos.html", warnings)
    milestones = parse_milestones(
        project_dir / "1-planning" / "artefatos" / "roadmap-marcos.html",
        warnings,
        default_year=report_date.year,
        report_date=report_date,
    )

    synth = synthesize(entries, risks, changelog, milestones, report_date, warnings)

    clickup_url = None
    list_id = sync_state.get("clickup_list_id") or claude_data.get("clickup_list_id")
    if list_id:
        clickup_url = f"https://app.clickup.com/{list_id}/l/{list_id}"

    result = CollectResult(
        report_date=report_date_str,
        project={
            "name": plano_data.get("name") or project_dir.name,
            "goal": briefing.get("goal") or plano_data.get("goal") or "",
            "pm": plano_data.get("pm") or "",
            "pm_email": claude_data.get("pm_email") or "",
            "period_label": _period_label(report_date),
            "footer_label": f"M7 Investimentos · {MONTH_PT[report_date.month]} {report_date.year}",
            "clickup_list_url": clickup_url,
        },
        status={
            k: v for k, v in synth.items()
            if not k.startswith("_")
        },
        highlights=synth["_highlights"],
        next_steps=synth["_next_steps"],
        attentions=synth["_attentions"],
        milestones=milestones,
        macro_milestones=synth["_macro_milestones"],
        sprints=synth["_sprints"],
        fronts=[],
        sprint_actions=[
            {
                "no": a.get("no"),
                "etapa": truncate(a.get("etapa", ""), 80),
                "status": a.get("status"),
                "responsavel": a.get("responsavel"),
                "fim_planejado": a["fim_plan"].strftime("%Y-%m-%d") if isinstance(a.get("fim_plan"), datetime) else None,
                "clickup_id": a.get("clickup_id"),
            }
            for a in [e for e in entries if str(e.get("tipo", "")).lower() in ("ação", "acao")
                      and e.get("status") in ("in_progress", "blocked")][:10]
        ],
        risks=risks,
        changelog_entries=[{k: v for k, v in e.items() if k != "raw"} for e in changelog[:30]],
        warnings=warnings,
    )
    return result.to_dict()


def _period_label(report_date: datetime, span_days: int = 14) -> str:
    start = report_date - timedelta(days=span_days)
    return f"Quinzena {start.strftime('%d/%m')} — {report_date.strftime('%d/%m/%Y')}"


def main():
    p = argparse.ArgumentParser(description="Collect status report data deterministically")
    p.add_argument("--project-dir", required=True, type=Path)
    p.add_argument("--report-date", required=True, help="YYYY-MM-DD")
    p.add_argument("--output", type=Path, help="Escrever JSON aqui; stdout se omitido")
    args = p.parse_args()

    if not args.project_dir.exists():
        print(f"✗ project-dir não encontrado: {args.project_dir}", file=sys.stderr)
        sys.exit(2)
    if not (args.project_dir / "CLAUDE.md").exists():
        print(
            "✗ Projeto não inicializado: CLAUDE.md ausente.\n"
            "  Rode `initializing-project` primeiro.",
            file=sys.stderr,
        )
        sys.exit(2)

    try:
        data = collect(args.project_dir, args.report_date)
    except FileNotFoundError as e:
        print(f"✗ {e}", file=sys.stderr)
        sys.exit(2)
    except ValueError as e:
        print(f"✗ {e}", file=sys.stderr)
        sys.exit(2)

    payload = json.dumps(data, indent=2, default=str, ensure_ascii=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
        print(f"✓ Coleta gravada em {args.output}")
        if data["warnings"]:
            print(f"⚠ {len(data['warnings'])} warning(s):", file=sys.stderr)
            for w in data["warnings"]:
                print(f"   · {w}", file=sys.stderr)
    else:
        print(payload)


if __name__ == "__main__":
    main()
