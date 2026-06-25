"""
slack_send.py — Orquestrador da distribuicao via bot Slack m7-desempenho.

Auto-contido: inclui geracao de subject (ISO week), validacao RN-07 e render
de mensagem. Importa apenas resolve_recipients.py como modulo (XLSX) — esse
fica separado por valor de debug standalone.

Opera em 2 fases (RN-06):

    Fase `preview`:
        - Valida conteudo (RN-07: 4 elementos)
        - Resolve destinatarios (XLSX, User IDs U...)
        - Renderiza mensagem
        - Salva `distribution-preview-{mode}.json` em --output-dir
        - ZERO chamadas Slack

    Fase `commit`:
        - Le `distribution-preview-{mode}.json` (congelado)
        - auth_test + conversations.open + upload 3-step + completeUploadExternal
        - Escreve linha em distribuicao-log.csv (CP-04)
        - Imprime JSON pro stdout com ts[] e dms_count

Suporta `--dry-run` em commit: nao chama Slack, escreve log com flag dry_run=true.

Token carregado de:
    1. env var SLACK_BOT_TOKEN
    2. ~/.claude/credentials/.env  (convencao M7)
    3. {plugin_dir}/.env
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

# Modulo standalone que mantemos separado pra debug do XLSX
from resolve_recipients import resolve as resolve_recipients  # noqa: E402

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


# =====================================================================
#                          CONSTANTES
# =====================================================================

CP04_DEADLINE_DAYS = {"N3": 1, "N2": 3, "N1": 3}  # D-1 semanal / D-3 mensal (RN-09); N1 e mensal = D-3

# Siglas all-caps preservadas — coincide com resolve_ritual_path.py
ALL_CAPS_VERTICALS = ("pj2", "pj1", "pj3", "ti", "rh", "ib", "wl", "re")


# =====================================================================
#                          UTILITARIOS GERAIS
# =====================================================================

def ts_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def fingerprint(token: str) -> str:
    if not token:
        return "(vazio)"
    return f"{token[:5]}...len={len(token)}"


def load_token() -> str | None:
    tok = os.environ.get("SLACK_BOT_TOKEN", "").strip()
    if tok:
        return tok
    candidates = [
        Path.home() / ".claude" / "credentials" / ".env",
        SCRIPT_DIR.parent.parent / ".env",
        SCRIPT_DIR / ".env",
    ]
    for env_file in candidates:
        if env_file.exists() and load_dotenv:
            load_dotenv(env_file, override=False)
            tok = os.environ.get("SLACK_BOT_TOKEN", "").strip()
            if tok:
                return tok
    return None


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _load_yaml(path: Path):
    import yaml
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _size_kb(path: Path) -> int:
    try:
        return max(1, round(path.stat().st_size / 1024))
    except OSError:
        return 0


# =====================================================================
#         ISO WEEK + SUBJECT (INS-PERF-002 v2.1 Passo 11)
# =====================================================================

def vertical_display(vertical: str) -> str:
    """Capitaliza vertical respeitando siglas all-caps conhecidas."""
    v = (vertical or "").strip().lower()
    if not v:
        raise ValueError("vertical vazio")
    if v in ALL_CAPS_VERTICALS:
        return v.upper()
    return v.capitalize()


def normalize_nivel(raw: str | None) -> str:
    """Normaliza nivel para 'N1'..'N5'."""
    if not raw:
        raise ValueError("nivel vazio")
    n = str(raw).strip().upper().replace("-", "")
    if n.startswith("N") and len(n) >= 2 and n[1].isdigit():
        return n[:2]
    if n.isdigit():
        return f"N{n}"
    raise ValueError(f"nivel nao reconhecido: {raw!r}")


def build_subject(vertical: str, nivel: str, ciclo_date: date, *, mode: str = "pre_ritual") -> str:
    """Compoe subject conforme INS-PERF-002 v2.1 Passo 11.

    Pre:  "Ritual {Vertical} N{NIVEL} S{NN}"  (ex: Ritual Consorcios N3 S21)
    Pos:  "Ata Ritual {Vertical} N{NIVEL} S{NN}"
    """
    if mode not in ("pre_ritual", "post_ritual"):
        raise ValueError(f"mode invalido: {mode!r}")
    vert = vertical_display(vertical)
    niv = normalize_nivel(nivel)
    week = ciclo_date.isocalendar()[1]
    prefix = "Ata Ritual" if mode == "post_ritual" else "Ritual"
    return f"{prefix} {vert} {niv} S{week:02d}"


def cadencia_label(nivel: str, subnivel: str = "") -> str:
    n = normalize_nivel(nivel)
    base = {"N1": "N1 (Estrategico)", "N2": "N2 (Tatico)", "N3": "N3 (Operacional)"}.get(n, n)
    if subnivel:
        return f"{base} - {subnivel.upper()}"
    return base


# =====================================================================
#         RN-07 VALIDATION (MAN-PERF-003)
# =====================================================================

def _check_metas_vs_realizado(wbr: dict) -> tuple[bool, str]:
    inds = wbr.get("indicadores") or {}
    if not isinstance(inds, dict) or not inds:
        return False, "WBR sem 'indicadores' ou vazio"
    com_meta = 0
    for ind in inds.values():
        if not isinstance(ind, dict):
            continue
        meta = ind.get("meta")
        realiz = ind.get("realizado")
        if isinstance(meta, (int, float)) and meta != 0 and isinstance(realiz, (int, float)):
            com_meta += 1
    if com_meta == 0:
        return False, "Nenhum indicador com meta+realizado numericos validos"
    return True, f"{com_meta} indicador(es) com meta+realizado validos"


def _check_desvios(wbr: dict, threshold_pp: float = 5.0) -> tuple[bool, str]:
    inds = wbr.get("indicadores") or {}
    desv = []
    for nome, ind in inds.items():
        if not isinstance(ind, dict):
            continue
        pct = ind.get("pct_atingimento")
        if pct is None:
            continue
        if abs(float(pct) - 100.0) > threshold_pp:
            desv.append(nome)
    if not desv:
        return False, f"Nenhum indicador com desvio >|{threshold_pp}|pp"
    return True, f"{len(desv)} indicador(es) com desvio >{threshold_pp}pp"


def _check_pa_status(clickup_path: Path | None, wbr: dict) -> tuple[bool, str]:
    if clickup_path and clickup_path.exists():
        try:
            data = _load_json(clickup_path)
            if isinstance(data, dict) and "tasks" in data:
                tasks = data["tasks"]
            elif isinstance(data, list):
                tasks = data
            else:
                tasks = []
            return True, f"clickup-tasks JSON com {len(tasks)} task(s)"
        except Exception as exc:
            return False, f"clickup-tasks JSON malformado: {exc}"
    if wbr.get("pa_status") or wbr.get("acoes") or wbr.get("plano_de_acao"):
        return True, "WBR carrega pa_status/acoes inline"
    return False, "Sem clickup-tasks.json e sem pa_status no WBR"


def _check_mom(wbr: dict, card: dict | None) -> tuple[bool, str]:
    """Check 4 de RN-07: tendencia MoM (proxy via presenca de marcadores temporais no WBR).

    Aceita 3 formas de marcador temporal (em ordem de preferencia):
      1. `periodo_inicio` + `periodo_fim` (top-level) — formato canonico antigo
      2. `data_referencia` (top-level) — formato canonico v1.3+ (3.8.3+)
      3. `meta.snapshot_at` (timestamp ISO) — fallback minimo

    Aceita 3 formas de checkpoint label (em ordem):
      `checkpoint_label`, `meta.checkpoint_label`, `meta.ciclo_label`.
    """
    meta = wbr.get("meta") or {}
    checkpoint = (
        wbr.get("checkpoint_label")
        or meta.get("checkpoint_label")
        or meta.get("ciclo_label")
        or ""
    )
    if not checkpoint:
        return False, "WBR sem checkpoint_label nem ciclo_label"

    # Marcador temporal: aceita periodo_inicio+fim OU data_referencia OU meta.snapshot_at
    has_periodo = bool(wbr.get("periodo_inicio") and wbr.get("periodo_fim"))
    has_data_ref = bool(wbr.get("data_referencia"))
    has_snapshot = bool(meta.get("snapshot_at"))

    if not (has_periodo or has_data_ref or has_snapshot):
        return False, "WBR sem periodo_inicio/fim, data_referencia ou meta.snapshot_at"

    marker_src = (
        "periodo_inicio+fim" if has_periodo else
        "data_referencia" if has_data_ref else
        "meta.snapshot_at"
    )

    if card:
        bc = card.get("briefing_customization") or {}
        if bc.get("versao") == "2.0":
            return True, f"checkpoint={checkpoint}; marker={marker_src}; Card v2.0 com filtros temporais"
    return True, f"checkpoint={checkpoint}; marker={marker_src}"


def _check_ata_post(ata_md_path: Path | None) -> tuple[bool, str]:
    if not ata_md_path:
        return False, "ata_md_path nao informado (obrigatorio em post_ritual)"
    if not ata_md_path.exists():
        return False, f"ata MD nao encontrada em {ata_md_path}"
    txt = ata_md_path.read_text(encoding="utf-8").lower()
    has_decisoes = "decis" in txt
    has_contramedidas = "contramedid" in txt
    has_scope = "scope_task_ids" in txt
    if not (has_decisoes and has_contramedidas):
        return False, "ata MD sem secoes 'decisoes' E/OU 'contramedidas'"
    if not has_scope:
        return False, "ata MD sem bloco 'scope_task_ids'"
    return True, "ata MD com decisoes, contramedidas e scope_task_ids"


def validate_rn07(
    mode: str,
    wbr: dict,
    *,
    clickup_path: Path | None = None,
    card: dict | None = None,
    ata_md_path: Path | None = None,
) -> dict:
    """Executa as 4 (ou 5 em post_ritual) checagens de RN-07.

    Retorna {ok, checks: [{name, ok, detail}], summary}.
    """
    checks = []
    for name, fn, kwargs in [
        ("metas_vs_realizado", _check_metas_vs_realizado, {"wbr": wbr}),
        ("desvios_5pp", _check_desvios, {"wbr": wbr}),
        ("pa_status", _check_pa_status, {"clickup_path": clickup_path, "wbr": wbr}),
        ("tendencia_mom", _check_mom, {"wbr": wbr, "card": card}),
    ]:
        ok, det = fn(**kwargs)
        checks.append({"name": name, "ok": ok, "detail": det})

    if mode == "post_ritual":
        ok, det = _check_ata_post(ata_md_path)
        checks.append({"name": "ata_md_estrutura", "ok": ok, "detail": det})

    all_ok = all(c["ok"] for c in checks)
    return {
        "ok": all_ok,
        "checks": checks,
        "summary": f"RN-07: {sum(1 for c in checks if c['ok'])}/{len(checks)} checks OK",
    }


# =====================================================================
#         BUILD MESSAGE (pre + pos)
# =====================================================================

TEMPLATE_DIR = SCRIPT_DIR.parent / "templates"


def _load_template(mode: str) -> str:
    fname = "pre-ritual-message.tmpl.md" if mode == "pre_ritual" else "post-ritual-message.tmpl.md"
    return (TEMPLATE_DIR / fname).read_text(encoding="utf-8")


def _build_pre_ritual_body(
    template: str, wbr: dict, deck_path: Path, briefing_path: Path,
    subject: str, cad_lbl: str, n_top: int = 3,
) -> tuple[str, dict]:
    """Renderiza body da mensagem pre-ritual.

    Conteudo da mensagem (decisao 2026-05-20): nome do ritual, cadencia, semaforo,
    periodo, top N desvios, anexos, CTA REAJA. SEM Card label (tech case) e SEM
    Plano de Acao (info redundante; o gestor ve no proprio briefing/ata anterior).
    """
    debug = {}
    sem = wbr.get("semaforo_resumo") or {}

    def _sem_count(flat_key: str, total_key: str) -> int:
        # Hardening 2026-06-11: o E6 analyst as vezes emite semaforo_resumo com
        # total_verde/total_amarelo/total_vermelho + aninhado kpis/ppis_com_meta,
        # em vez das chaves planas verde/amarelo/vermelho -> preview mostrava 0|0|0.
        # Aceitar todas as variantes, na ordem de preferencia flat > total > nested.
        # 2026-06-18: detectar DIVERGENCIA entre variantes — se o E6 emitir mais de
        # uma forma com valores diferentes, era silencioso (escolhia uma e seguia).
        # Agora registra em debug p/ o preview expor (schema inconsistente do E6).
        candidates: dict[str, int] = {}
        if sem.get(flat_key) is not None:
            candidates["flat"] = int(sem[flat_key])
        if sem.get(total_key) is not None:
            candidates["total"] = int(sem[total_key])
        # 2026-06-22: guard type — `kpis`/`ppis_com_meta` podem vir como INT
        # (contagem de indicadores) em vez de dict aninhado {verde/amarelo/vermelho}.
        # O E6 (analyst) emite ambas as formas; sem o isinstance o .get crashava
        # ('int' object has no attribute 'get') mesmo com as chaves planas presentes.
        _kpis = sem.get("kpis")
        _ppis = sem.get("ppis_com_meta")
        nested = _kpis.get(flat_key) if isinstance(_kpis, dict) else None
        nested_ppi = _ppis.get(flat_key) if isinstance(_ppis, dict) else None
        if nested is not None or nested_ppi is not None:
            candidates["nested"] = int(nested or 0) + int(nested_ppi or 0)
        if not candidates:
            return 0
        chosen = next(candidates[p] for p in ("flat", "total", "nested") if p in candidates)
        if len(set(candidates.values())) > 1:
            debug.setdefault("semaforo_resumo_divergencia", []).append(
                f"{flat_key}: variantes divergem {candidates} -> usando {chosen} (flat>total>nested)"
            )
        return chosen

    sem_vermelho = _sem_count("vermelho", "total_vermelho")
    sem_amarelo = _sem_count("amarelo", "total_amarelo")
    sem_verde = _sem_count("verde", "total_verde")
    sem_cinza = sem.get("cinza_sem_meta", sem.get("total_cinza"))
    if sem_cinza is None:
        sem_cinza = len(sem.get("cinza_sem_dados") or []) + len(sem.get("na_contexto") or [])
    sem_cinza = int(sem_cinza)
    sem_cinza_block = f" | :white_circle: {sem_cinza} (sem meta)" if sem_cinza else ""

    meta = wbr.get("meta") or {}
    checkpoint_label = (
        wbr.get("checkpoint_label")
        or meta.get("checkpoint_label")
        or meta.get("ciclo_label")
        or "(periodo nao informado)"
    )

    # Top N desvios (vermelhos primeiro, depois por |gap_pct|)
    inds = wbr.get("indicadores") or {}
    desvios = []
    for nome, ind in inds.items():
        if not isinstance(ind, dict):
            continue
        pct = ind.get("pct_atingimento")
        if pct is None:
            continue
        gap = abs(float(pct) - 100.0)
        status = ind.get("status", "")
        weight = (0 if status == "vermelho" else (1 if status == "amarelo" else 2), -gap)
        desvios.append((weight, nome, ind))
    desvios.sort(key=lambda t: t[0])
    top = desvios[:n_top]

    def _bullet(nome, ind):
        label = ind.get("label") or nome
        # FIX 2026-06-18: quando o canonical nao traz *_label (analyst E6 nem sempre
        # popula), formatar a partir dos numeros crus em vez de imprimir o ratio
        # (ex: "0.5782") com unidade vazia "()". Prefere realizado_label (mais
        # informativo) e cai em pct_atingimento*100 como ultimo recurso.
        pct_lbl = ind.get("pct_label")
        if not pct_lbl:
            real_lbl = ind.get("realizado_label")
            pct_raw = ind.get("pct_atingimento")
            if real_lbl:
                pct_lbl = real_lbl
            elif pct_raw is not None:
                try:
                    pct_lbl = f"{float(pct_raw) * 100:.0f}%"
                except (TypeError, ValueError):
                    pct_lbl = ""
            else:
                pct_lbl = ""
        gap_lbl = ind.get("gap_label") or ""
        status = ind.get("status", "info")
        emoji = {
            "vermelho": ":red_circle:",
            "amarelo": ":large_yellow_circle:",
            "verde": ":large_green_circle:",
        }.get(status, ":white_circle:")
        causa = ind.get("causa_raiz_resumo") or ""
        causa_short = causa if len(causa) <= 140 else causa[:137].rstrip() + "..."
        suffix = f" - {causa_short}" if causa_short else ""
        gap_part = f" ({gap_lbl})" if gap_lbl else ""
        return f"- {emoji} *{label}*: {pct_lbl}{gap_part}{suffix}"

    desvios_bullets = (
        "\n".join(_bullet(n, i) for _, n, i in top)
        if top
        else "- _(sem desvios significativos identificados)_"
    )
    debug["desvios_count_total"] = len(desvios)

    placeholders = {
        "subject": subject,
        "cadencia_label": cad_lbl,
        "sem_vermelho": sem_vermelho,
        "sem_amarelo": sem_amarelo,
        "sem_verde": sem_verde,
        "sem_cinza_block": sem_cinza_block,
        "checkpoint_label": checkpoint_label,
        "n_top_desvios": min(n_top, len(top)),
        "desvios_bullets": desvios_bullets,
        "deck_size_kb": _size_kb(deck_path),
        "briefing_size_kb": _size_kb(briefing_path),
    }
    body = template.format_map(defaultdict(str, placeholders))
    return body, debug


# Regex para extracao de scope / escalacao da ata MD
_SCOPE_BLOCK_RE = re.compile(r"scope_task_ids:\s*\n((?:\s*-\s+.*\n?)+)", re.IGNORECASE)
_TASK_ITEM_RE = re.compile(r"-\s+([\w-]+)")
_ESCALACAO_FLAG_RE = re.compile(r"escalacao_acionada:\s*(true|yes|sim|1)", re.IGNORECASE)


def _extract_scope_task_ids(ata_md: str) -> list[str]:
    m = _SCOPE_BLOCK_RE.search(ata_md)
    if not m:
        return []
    return _TASK_ITEM_RE.findall(m.group(1))


def _has_escalacao(ata_md: str) -> bool:
    return bool(_ESCALACAO_FLAG_RE.search(ata_md))


PLAN_PREVIEW_SCHEMA_REQUIRED = "2.0"


def _assert_plan_preview_schema_v2(plan_preview: dict | None, plan_preview_path: str) -> None:
    """Gatekeeper espelhado de render_ata.py: aborta se plan-preview.json nao for v2.0.

    Aplica em post_ritual quando plan-preview existe. Evita "(sem responsavel)" silencioso
    em plan-previews antigos (pre-v3.9.0) com schemas 1-4 do historico.
    """
    if not plan_preview:
        return  # ausente e tolerado (mode=post_ritual sem plan-preview opcional)
    v = plan_preview.get("schema_version")
    if v != PLAN_PREVIEW_SCHEMA_REQUIRED:
        print(
            json.dumps(
                {
                    "ok": False,
                    "phase": "schema_validation",
                    "error": (
                        f"plan-preview.json schema_version={v!r}, esperado "
                        f"{PLAN_PREVIEW_SCHEMA_REQUIRED!r}. Migrar para v2.0 ou re-executar "
                        "/m7-ritual-gestao:record-decisions {vertical}{ {sub}} para regerar."
                    ),
                    "plan_preview_path": plan_preview_path,
                    "schema_doc": (
                        "m7-operations/m7-ritual-gestao/skills/recording-decisions/"
                        "references/plan-preview-schema.md"
                    ),
                },
                ensure_ascii=False,
            )
        )
        sys.exit(2)


def _extract_responsavel(cm: dict) -> str:
    """Extrai 'Responsavel Externo' do plan-preview.json v2.0.

    Schema v2.0 (canonico desde 2026-05-31): campo top-level `responsavel_externo_label`
    OBRIGATORIO em cada item de `contramedidas_novas[]`. Os validadores
    `_assert_schema_v2()` em `render_ata.py` e `_assert_plan_preview_schema_v2()` aqui
    abortam antes se schema_version != "2.0".
    """
    if not isinstance(cm, dict):
        return "(sem responsavel)"
    return (cm.get("responsavel_externo_label") or "").strip() or "(sem responsavel)"


def _format_date_br(iso: str | None) -> str:
    """YYYY-MM-DD -> DD/MM."""
    if not iso or len(iso) < 10:
        return "sem prazo"
    return f"{iso[8:10]}/{iso[5:7]}"


def _render_contramedidas_por_responsavel(plan_preview: dict | None) -> tuple[str, int, int]:
    """Agrupa contramedidas novas por Responsavel Externo.

    Tasks atualizadas entram numa secao curta ao final (so se houver).

    Returns:
        (bloco_text, n_novas, n_atualizadas)
    """
    if not plan_preview:
        return "_(sem plano de contramedidas disponivel)_", 0, 0

    novas = plan_preview.get("contramedidas_novas") or []
    atualizadas = plan_preview.get("tasks_atualizadas") or []

    # Agrupa novas por responsavel (schema v2.0: TODOS os campos sao top-level)
    grupos: dict[str, list[str]] = {}
    for cm in novas:
        if not isinstance(cm, dict):
            continue
        name = (cm.get("name") or "(sem titulo)").strip()
        resp = _extract_responsavel(cm)
        due = _format_date_br(cm.get("due_date"))
        prio = (cm.get("priority_label") or "").strip()
        suffix = f" ({prio} · {due})" if prio else f" ({due})"
        grupos.setdefault(resp, []).append(f"  - {name}{suffix}")

    blocos = []
    for resp in sorted(grupos.keys()):
        blocos.append(f"*Para {resp}:*")
        blocos.extend(grupos[resp])
        blocos.append("")  # linha em branco entre grupos
    # remove ultima linha em branco
    if blocos and blocos[-1] == "":
        blocos.pop()

    if not blocos:
        blocos = ["_(nenhuma contramedida nova registrada)_"]

    # Tasks atualizadas — secao curta
    if atualizadas:
        blocos.append("")
        blocos.append(f"_Tasks anteriores atualizadas: {len(atualizadas)}_")

    return "\n".join(blocos), len(novas), len(atualizadas)


def _build_post_ritual_body(
    template: str, ata_md_text: str, plan_preview: dict | None, ciclo_date: str,
    subject: str, cad_lbl: str, include_md_anexo: bool = False,
    deck_path: Path | None = None,
) -> tuple[str, dict]:
    """Renderiza body da mensagem pos-ritual (distribuicao da ata).

    Conteudo da mensagem (decisao 2026-05-20 v2): subject, cadencia, data,
    CONTRAMEDIDAS AGRUPADAS POR RESPONSAVEL (cada participante ve as suas no canal
    da vertical), flag de escalacao, anexos, CTA REAJA.

    Decisoes registradas NAO entram (ficam na ata PDF — principio "se quer detalhe,
    abre o PDF").

    Desde 3.8.2: deck HTML do ritual e anexado quando disponivel (RITUAL_DIR/apresentacao/),
    para referencia historica junto da ata.
    """
    debug = {}
    debug["scope_task_ids_count"] = len(_extract_scope_task_ids(ata_md_text))

    contramedidas_block, n_novas, n_atualizadas = _render_contramedidas_por_responsavel(plan_preview)
    debug["n_novas"] = n_novas
    debug["n_atualizadas"] = n_atualizadas

    escalacao = _has_escalacao(ata_md_text)
    debug["escalacao"] = escalacao

    escalacao_block = ""
    if escalacao:
        escalacao_block = "\n:warning: *Escalacao acionada* — copia enviada ao lider direto."
    ata_md_line = "\n- Ata em Markdown (para edicao/revisao)" if include_md_anexo else ""
    deck_line = "\n- Apresentacao do ritual (HTML)" if (deck_path and deck_path.exists()) else ""
    debug["deck_attached"] = bool(deck_path and deck_path.exists())

    placeholders = {
        "subject": subject,
        "cadencia_label": cad_lbl,
        "data_ritual_label": ciclo_date,
        "contramedidas_block": contramedidas_block,
        "n_novas": n_novas,
        "n_atualizadas": n_atualizadas,
        "escalacao_block": escalacao_block,
        "ata_md_line": ata_md_line,
        "deck_line": deck_line,
    }
    body = template.format_map(defaultdict(str, placeholders))
    return body, debug


def render_message(
    mode: str,
    vertical: str,
    nivel: str,
    subnivel: str,
    ciclo_date_str: str,
    wbr: dict,
    *,
    card: dict | None = None,
    clickup_tasks: list | None = None,
    deck_path: Path | None = None,
    briefing_path: Path | None = None,
    ata_md_text: str | None = None,
    ata_pdf_path: Path | None = None,
    plan_preview: dict | None = None,
    include_md_anexo: bool = False,
    top_desvios: int = 3,
) -> dict:
    """Retorna {ok, subject, body, attachments[], debug, mode}."""
    ciclo_date = datetime.strptime(ciclo_date_str, "%Y-%m-%d").date()
    subject = build_subject(vertical, nivel, ciclo_date, mode=mode)
    cad_lbl = cadencia_label(nivel, subnivel)
    template = _load_template(mode)

    if mode == "pre_ritual":
        if not deck_path or not briefing_path:
            return {"ok": False, "error": "deck_path e briefing_path obrigatorios em pre_ritual"}
        body, debug = _build_pre_ritual_body(
            template, wbr, deck_path, briefing_path,
            subject, cad_lbl, n_top=top_desvios,
        )
        attachments = [str(deck_path), str(briefing_path)]
    else:
        if not ata_md_text or not ata_pdf_path:
            return {"ok": False, "error": "ata_md_text e ata_pdf_path obrigatorios em post_ritual"}
        body, debug = _build_post_ritual_body(
            template, ata_md_text, plan_preview, ciclo_date_str,
            subject, cad_lbl, include_md_anexo=include_md_anexo,
            deck_path=deck_path,
        )
        attachments = [str(ata_pdf_path)]
        # Deck do ritual (RITUAL_DIR/apresentacao/) anexado quando disponivel — 3.8.2.
        # Skip silencioso se ausente (verticais que nao usaram approve-ritual).
        if deck_path and deck_path.exists():
            attachments.append(str(deck_path))

    return {
        "ok": True, "subject": subject, "body": body,
        "attachments": attachments, "mode": mode, "debug": debug,
    }


# =====================================================================
#         CP-04: PONTUALIDADE + DELIVERY LOG
# =====================================================================

def compute_on_time(ciclo_date: date, nivel: str, now: datetime | None = None) -> tuple[bool, str]:
    """RN-09: deadline N3=D-1, N2=D-3."""
    n = normalize_nivel(nivel)
    days = CP04_DEADLINE_DAYS.get(n, 1)
    prazo_lbl = f"D-{days}"
    now = now or datetime.now(timezone.utc).astimezone()
    deadline = datetime.combine(ciclo_date, datetime.max.time(), tzinfo=now.tzinfo) - timedelta(days=days)
    return now <= deadline, prazo_lbl


def _sync_clickup_recorrencia(*, mode: str, vertical: str, nivel: str, subnivel: str,
                                dms_count: int, error_msg: str) -> None:
    """Sincroniza execução do ritual com a task ClickUp da lista "Comunicações Recorrentes".

    Chama _shared/clickup_sync.py via subprocess (sem importar — evita acoplamento
    com o pipeline de Rotinas/). Best-effort: erros logam mas não falham o commit.

    Mapping (mode, vertical, nivel, subnivel) → rotina_id:
      - pre_ritual + consorcios + N3 + ""    → ritual-pre-consorcios-n3
      - pos_ritual + consorcios + N3 + ""    → ritual-pos-consorcios-n3
      - pre_ritual + seguros   + N3 + "re"   → ritual-pre-seguros-n3-re
      - pos_ritual + seguros   + N3 + "re"   → ritual-pos-seguros-n3-re
      - pre_ritual + seguros   + N3 + "wl"   → ritual-pre-seguros-n3-wl
      - pos_ritual + seguros   + N3 + "wl"   → ritual-pos-seguros-n3-wl
    """
    import subprocess

    # Localiza _shared/clickup_sync.py no DESEMPENHO_ROOT
    desemp_root = os.environ.get("DESEMPENHO_ROOT", "").strip()
    if not desemp_root:
        # Fallback: tenta path padrão M7
        candidates = [
            Path.home() / "OneDrive - MULTI7 CAPITAL CONSULTORIA LTDA"
                / "Arquivos de Bruno Chiaramonti - desempenho",
        ]
        for c in candidates:
            if c.is_dir():
                desemp_root = str(c)
                break
    def _log(m):
        # log() é closure local de run_commit — usar stderr direto aqui
        print(f"[{ts_iso()}] {m}", file=sys.stderr, flush=True)

    if not desemp_root:
        _log("[clickup_sync] SKIP — DESEMPENHO_ROOT não resolvido")
        return

    clickup_sync = Path(desemp_root) / "02-Controle" / "Rotinas" / "_shared" / "clickup_sync.py"
    if not clickup_sync.is_file():
        _log(f"[clickup_sync] SKIP — script não encontrado em {clickup_sync}")
        return

    # Constrói rotina_id
    tipo = "pre" if mode == "pre_ritual" else "pos"
    nivel_label = f"{nivel}{('-' + subnivel) if subnivel else ''}"
    rotina_id = f"ritual-{tipo}-{vertical}-{nivel_label}".lower()

    # Status (success se >=1 DM enviada; senão failed)
    status = "success" if dms_count > 0 else "failed"

    try:
        proc = subprocess.run(
            [
                "python", str(clickup_sync),
                "--vertical", "consorcios",   # placeholder pra resolver token/list_id
                "--rotina-id", rotina_id,
                "--modo", "producao",
                "--status", status,
                "--recipients-count", str(dms_count),
                "--dms-sent", str(dms_count),
                "--error-msg", error_msg or "",
                "--artefatos", "",
            ],
            capture_output=True, text=True, timeout=30,
        )
        if proc.returncode == 0:
            _log(f"[clickup_sync] OK rotina={rotina_id}")
        else:
            err = (proc.stderr or proc.stdout or "").strip()
            hint = ""
            if "não mapeado" in err or "nao mapeado" in err or "not found" in err.lower():
                hint = (" -> rotina nao casou nenhuma task na lista Comunicacoes Recorrentes; "
                        "ROLLFORWARD/telemetria NAO aplicados (verifique a chave no YAML da vertical).")
            _log(f"[clickup_sync] FALHA rotina={rotina_id}{hint} stderr={err[:200]}")
    except Exception as exc:
        _log(f"[clickup_sync] EXCEPTION rotina={rotina_id}: {exc}")


def write_delivery_log(log_path: Path, **fields) -> None:
    """Append linha no distribuicao-log.csv. Header automatico na primeira escrita."""
    headers = [
        "timestamp", "vertical", "nivel", "subnivel", "cycle_date", "semana_iso",
        "tipo", "dms_count", "on_time", "prazo_referencia",
        "confirmacoes_leitura_count", "escalacao_acionada", "dry_run",
    ]
    write_header = not log_path.exists() or log_path.stat().st_size == 0
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        if write_header:
            w.writerow(headers)
        w.writerow([fields.get(h, "") for h in headers])


# =====================================================================
#         PREVIEW PHASE
# =====================================================================

def run_preview(args) -> int:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    preview_path = output_dir / f"distribution-preview-{args.mode}.json"

    # WBR (RN-08 single source of truth)
    if not args.wbr_data_json or not Path(args.wbr_data_json).exists():
        print(json.dumps({"ok": False, "error": f"WBR data JSON nao encontrado: {args.wbr_data_json}"}))
        return 2
    wbr = _load_json(Path(args.wbr_data_json))

    # Card YAML (opcional pra checagem v2.0)
    card = None
    if args.card_yaml and Path(args.card_yaml).exists():
        try:
            card = _load_yaml(Path(args.card_yaml))
        except Exception as exc:
            print(json.dumps({"ok": False, "error": f"Card YAML invalido: {exc}"}))
            return 2

    # Validacao RN-07
    clickup_path = Path(args.clickup_tasks_json) if args.clickup_tasks_json else None
    ata_md_path = Path(args.ata_md_path) if args.ata_md_path else None
    val_result = validate_rn07(
        args.mode, wbr,
        clickup_path=clickup_path, card=card, ata_md_path=ata_md_path,
    )
    if not val_result["ok"]:
        print(json.dumps(
            {"ok": False, "phase": "validate_rn07", "error": val_result["summary"], "checks": val_result["checks"]},
            ensure_ascii=False, indent=2,
        ))
        return 3

    # Resolver destinatarios (XLSX)
    include_esc = args.mode == "post_ritual"
    if not args.calendar_path or not Path(args.calendar_path).exists():
        print(json.dumps({"ok": False, "error": f"Calendario XLSX nao encontrado: {args.calendar_path}"}))
        return 2
    recipients = resolve_recipients(
        Path(args.calendar_path), args.vertical, args.nivel,
        subnivel=args.subnivel, include_escalacao=include_esc,
    )
    if not recipients.get("ok"):
        print(json.dumps(
            {"ok": False, "phase": "resolve_recipients", "error": recipients.get("error")},
            ensure_ascii=False, indent=2,
        ))
        return 4

    # Regra de distribuicao por modo (definida 2026-05-20):
    # - pre_ritual: materiais (deck + briefing) vao SO para o coordenador/gestor.
    #   Participantes nao recebem; o briefing e ferramenta de preparacao do condutor.
    # - post_ritual: ata vai para coordenador + participantes + lider direto (se escalacao).
    if args.mode == "pre_ritual":
        recipients["participantes"] = []
        recipients["lider_direto"] = None

    # Render mensagem
    clickup_tasks = None
    if clickup_path and clickup_path.exists():
        try:
            data = _load_json(clickup_path)
            clickup_tasks = (
                data.get("tasks") if isinstance(data, dict) and "tasks" in data
                else (data if isinstance(data, list) else None)
            )
        except Exception:
            clickup_tasks = None

    ata_md_text = None
    plan_preview = None
    if args.mode == "post_ritual":
        if not ata_md_path or not ata_md_path.exists():
            print(json.dumps({"ok": False, "error": f"Ata MD ausente: {args.ata_md_path}"}))
            return 2
        ata_md_text = ata_md_path.read_text(encoding="utf-8")
        if args.plan_preview_json and Path(args.plan_preview_json).exists():
            try:
                plan_preview = _load_json(Path(args.plan_preview_json))
            except Exception:
                plan_preview = None
            _assert_plan_preview_schema_v2(plan_preview, args.plan_preview_json)

    msg = render_message(
        mode=args.mode,
        vertical=args.vertical, nivel=args.nivel, subnivel=args.subnivel,
        ciclo_date_str=args.ciclo_date,
        wbr=wbr, card=card, clickup_tasks=clickup_tasks,
        deck_path=Path(args.deck_path) if args.deck_path else None,
        briefing_path=Path(args.briefing_path) if args.briefing_path else None,
        ata_md_text=ata_md_text,
        ata_pdf_path=Path(args.ata_pdf_path) if args.ata_pdf_path else None,
        plan_preview=plan_preview,
        include_md_anexo=args.include_md_anexo,
        top_desvios=args.top_desvios,
    )
    if not msg["ok"]:
        print(json.dumps({"ok": False, "phase": "render_message", "error": msg.get("error")}))
        return 5
    if args.mode == "post_ritual" and args.include_md_anexo and ata_md_path:
        msg["attachments"].append(str(ata_md_path))

    # Pontualidade
    try:
        cd = datetime.strptime(args.ciclo_date, "%Y-%m-%d").date()
    except ValueError:
        print(json.dumps({"ok": False, "error": f"--ciclo-date invalido: {args.ciclo_date}"}))
        return 2
    on_time, prazo_lbl = compute_on_time(cd, args.nivel)
    semana = cd.isocalendar()[1]

    # Escalacao acionada: SOMENTE quando a ata tem flag YAML "escalacao_acionada: true"
    # NAO basta o XLSX ter Lider-Direto-User-ID populado (bug pre-2026-05-20).
    # Em pre_ritual sempre False (sem ata).
    escalacao_real = False
    if args.mode == "post_ritual" and ata_md_text:
        escalacao_real = _has_escalacao(ata_md_text)

    # Empacotar preview
    preview = {
        "schema": "distribution-preview v1.0",
        "generated_at": ts_iso(),
        "mode": args.mode,
        "vertical": args.vertical,
        "nivel": normalize_nivel(args.nivel),
        "subnivel": args.subnivel or "",
        "ciclo_date": args.ciclo_date,
        "semana_iso": semana,
        "subject": msg["subject"],
        "body": msg["body"],
        "attachments": msg["attachments"],
        "recipients": recipients,
        "validate_rn07": val_result,
        "delivery_meta": {
            "on_time": on_time,
            "prazo_referencia": prazo_lbl,
            "escalacao_acionada": escalacao_real,
        },
        "debug": msg.get("debug", {}),
    }
    preview_path.write_text(json.dumps(preview, ensure_ascii=False, indent=2), encoding="utf-8")

    # Sumario stdout
    n_part = len(recipients.get("participantes", []))
    n_total = 1 + n_part + (1 if preview["delivery_meta"]["escalacao_acionada"] else 0)
    body_preview = msg["body"][:300] + ("..." if len(msg["body"]) > 300 else "")
    print(json.dumps({
        "ok": True, "phase": "preview", "mode": args.mode,
        "preview_path": str(preview_path),
        "subject": msg["subject"],
        "recipients_count": n_total,
        "gestor": recipients["gestor"]["name"],
        "participantes_count": n_part,
        "escalacao_acionada": preview["delivery_meta"]["escalacao_acionada"],
        "on_time": on_time, "prazo_referencia": prazo_lbl,
        "attachments": msg["attachments"],
        "body_preview": body_preview,
    }, ensure_ascii=False, indent=2))
    return 0


# =====================================================================
#         COMMIT PHASE (Slack API calls)
# =====================================================================

def _slack_client(token: str):
    from slack_sdk import WebClient
    return WebClient(token=token)


def _do_upload(client, file_path: Path) -> dict:
    import requests
    size = file_path.stat().st_size
    info = client.files_getUploadURLExternal(filename=file_path.name, length=size)
    upload_url = info["upload_url"]
    file_id = info["file_id"]
    with open(file_path, "rb") as fh:
        resp = requests.post(upload_url, files={"file": (file_path.name, fh)}, timeout=60)
    resp.raise_for_status()
    return {"id": file_id, "title": file_path.name, "size": size}


def _open_dm(client, user_id: str) -> str:
    conv = client.conversations_open(users=user_id)
    return conv["channel"]["id"]


def run_commit(args) -> int:
    preview_path = Path(args.preview_path) if args.preview_path else (
        Path(args.output_dir) / f"distribution-preview-{args.mode}.json"
    )
    if not preview_path.exists():
        print(json.dumps({"ok": False, "error": f"preview JSON nao encontrado: {preview_path}. Rode --phase preview primeiro."}))
        return 6

    preview = _load_json(preview_path)

    # Sanity: idade do preview
    try:
        gen_at = datetime.fromisoformat(preview["generated_at"])
        age_h = (datetime.now(gen_at.tzinfo) - gen_at).total_seconds() / 3600.0
    except Exception:
        age_h = 0.0
    if age_h > 24 and not args.force_stale:
        print(json.dumps({"ok": False, "warn": f"preview tem {age_h:.1f}h (>24h). Reexecute preview ou passe --force-stale."}))
        return 6

    dry_run = args.dry_run
    token = load_token()
    if not dry_run and not token:
        print(json.dumps({"ok": False, "error": "SLACK_BOT_TOKEN ausente. Defina em env ou ~/.claude/credentials/.env"}))
        return 2

    exec_log = []
    def log(m):
        line = f"[{ts_iso()}] {m}"
        exec_log.append(line)
        print(line, file=sys.stderr, flush=True)

    log(f"Commit mode={preview['mode']} vertical={preview['vertical']} nivel={preview['nivel']} dry_run={dry_run}")

    attach_paths = [Path(p) for p in preview["attachments"]]
    for ap in attach_paths:
        if not ap.exists():
            print(json.dumps({"ok": False, "error": f"anexo nao encontrado: {ap}"}))
            return 7

    recipients = preview["recipients"]

    # Decisao do target conforme modo (2026-05-20):
    # - pre_ritual: DM do gestor (so o coordenador recebe deck+briefing)
    # - post_ritual com canal_id no XLSX: 1 envio coletivo no canal da vertical
    # - post_ritual sem canal_id (verticais ainda sem canal Slack): fallback DMs
    targets = []
    post_canal_id = recipients.get("canal_id") if preview["mode"] == "post_ritual" else None

    if post_canal_id:
        targets.append({
            "role": "canal",
            "channel_id": post_canal_id,
            "name": f"#{preview['vertical']}{('-' + preview['subnivel']) if preview.get('subnivel') else ''}",
        })
    else:
        if preview["mode"] == "post_ritual":
            log("WARN post_ritual sem Canal-Vertical-ID no XLSX — fallback para DMs individuais")
        if recipients.get("gestor"):
            targets.append({"role": "gestor", **recipients["gestor"]})
        for p in recipients.get("participantes", []):
            targets.append({"role": "participante", **p})
        if preview["delivery_meta"].get("escalacao_acionada") and recipients.get("lider_direto"):
            targets.append({"role": "lider_direto", **recipients["lider_direto"]})

    deliveries = []

    if dry_run:
        log(f"DRY-RUN: pulando Slack. Targets={len(targets)} anexos={len(attach_paths)}")
        for t in targets:
            deliveries.append({
                "role": t["role"],
                "user_id": t.get("user_id") or "",
                "channel_id": t.get("channel_id") or "",
                "name": t.get("name", ""),
                "ok": True, "dry_run": True, "ts": None, "dm_channel": None,
            })
    else:
        log(f"Token: {fingerprint(token)}")
        client = _slack_client(token)
        try:
            auth = client.auth_test()
            log(f"auth_test OK user={auth.get('user')} team={auth.get('team')}")
        except Exception as exc:
            print(json.dumps({"ok": False, "error": f"auth_test falhou: {exc}"}))
            return 8

        for t in targets:
            # Resolver channel_id: canal direto (post_ritual) OU abrir DM (pre/fallback)
            if t.get("channel_id"):
                channel_id = t["channel_id"]
                log(f"target=canal {channel_id} role={t['role']}")
            else:
                try:
                    channel_id = _open_dm(client, t["user_id"])
                    log(f"open user={t['user_id']} role={t['role']} -> {channel_id}")
                except Exception as exc:
                    log(f"ERRO open user={t['user_id']}: {exc}")
                    deliveries.append({
                        "role": t["role"], "user_id": t.get("user_id", ""), "name": t.get("name", ""),
                        "ok": False, "error": f"open_failed: {exc}", "ts": None,
                    })
                    continue

            try:
                file_ids = []
                for ap in attach_paths:
                    info = _do_upload(client, ap)
                    file_ids.append({"id": info["id"], "title": info["title"]})
                log(f"upload OK target={channel_id} files={len(file_ids)}")
            except Exception as exc:
                log(f"ERRO upload target={channel_id}: {exc}")
                deliveries.append({
                    "role": t["role"], "user_id": t.get("user_id", ""), "channel_id": channel_id,
                    "name": t.get("name", ""),
                    "ok": False, "error": f"upload_failed: {exc}", "ts": None,
                })
                continue

            try:
                result = client.files_completeUploadExternal(
                    files=file_ids, channel_id=channel_id, initial_comment=preview["body"],
                )
                files_meta = result.get("files", [])
                msg_ts = None
                for fmeta in files_meta:
                    shares = fmeta.get("shares") or {}
                    for kind in ("private", "public"):
                        kshares = shares.get(kind) or {}
                        if channel_id in kshares and kshares[channel_id]:
                            msg_ts = kshares[channel_id][0].get("ts")
                            break
                    if msg_ts:
                        break
                deliveries.append({
                    "role": t["role"], "user_id": t.get("user_id", ""), "channel_id": channel_id,
                    "name": t.get("name", ""),
                    "ok": True, "ts": msg_ts, "files_count": len(files_meta),
                })
                log(f"complete OK target={channel_id} ts={msg_ts}")
            except Exception as exc:
                log(f"ERRO complete target={channel_id}: {exc}")
                deliveries.append({
                    "role": t["role"], "user_id": t.get("user_id", ""), "channel_id": channel_id,
                    "name": t.get("name", ""),
                    "ok": False, "error": f"complete_failed: {exc}", "ts": None,
                })

    ok_count = sum(1 for d in deliveries if d["ok"])
    fail_count = len(deliveries) - ok_count

    # CSV log
    log_path = Path(args.delivery_log_path) if args.delivery_log_path else None
    if log_path:
        write_delivery_log(
            log_path,
            timestamp=ts_iso(),
            vertical=preview["vertical"],
            nivel=preview["nivel"],
            subnivel=preview.get("subnivel", ""),
            cycle_date=preview["ciclo_date"],
            semana_iso=preview["semana_iso"],
            tipo=("pre" if preview["mode"] == "pre_ritual" else "pos"),
            dms_count=ok_count,
            on_time=str(preview["delivery_meta"]["on_time"]).lower(),
            prazo_referencia=preview["delivery_meta"]["prazo_referencia"],
            confirmacoes_leitura_count=0,
            escalacao_acionada=str(preview["delivery_meta"]["escalacao_acionada"]).lower(),
            dry_run=str(dry_run).lower(),
        )

    # ClickUp sync (best-effort, não falha o commit se quebrar) — adiciona
    # comment + roll-forward due_date na task da lista "Comunicações Recorrentes".
    # Mapeia (mode, vertical, nivel, subnivel) → rotina_id que está no YAML do Cons.
    if not dry_run and ok_count > 0:
        _sync_clickup_recorrencia(
            mode=preview["mode"],
            vertical=preview["vertical"],
            nivel=preview["nivel"],
            subnivel=preview.get("subnivel", ""),
            dms_count=ok_count,
            error_msg=("" if fail_count == 0 else f"{fail_count} entrega(s) falharam"),
        )

    out = {
        "ok": fail_count == 0, "phase": "commit", "dry_run": dry_run,
        "mode": preview["mode"], "vertical": preview["vertical"],
        "nivel": preview["nivel"], "subnivel": preview.get("subnivel", ""),
        "ciclo_date": preview["ciclo_date"], "semana_iso": preview["semana_iso"],
        "subject": preview["subject"],
        "dms_count_ok": ok_count, "dms_count_fail": fail_count,
        "on_time": preview["delivery_meta"]["on_time"],
        "prazo_referencia": preview["delivery_meta"]["prazo_referencia"],
        "escalacao_acionada": preview["delivery_meta"]["escalacao_acionada"],
        "delivery_log_path": str(log_path) if log_path else None,
        "deliveries": deliveries,
        "exec_log": exec_log,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if fail_count == 0 else 9


# =====================================================================
#         CLI
# =====================================================================

def main():
    p = argparse.ArgumentParser(description="Orchestrate Slack distribution for ritual materials (E3 + E5.7)")
    p.add_argument("--phase", required=True, choices=("preview", "commit"))
    p.add_argument("--mode", required=True, choices=("pre_ritual", "post_ritual"))
    p.add_argument("--vertical", required=True)
    p.add_argument("--nivel", required=True, help="N1/N2/N3")
    p.add_argument("--subnivel", default="")
    p.add_argument("--ciclo-date", required=True, help="YYYY-MM-DD")

    p.add_argument("--wbr-data-json", default="")
    p.add_argument("--card-yaml", default="")
    p.add_argument("--clickup-tasks-json", default="")
    p.add_argument("--deck-path", default="")
    p.add_argument("--briefing-path", default="")
    p.add_argument("--ata-md-path", default="")
    p.add_argument("--ata-pdf-path", default="")
    p.add_argument("--plan-preview-json", default="")
    p.add_argument("--include-md-anexo", action="store_true")
    p.add_argument("--calendar-path", default="")

    p.add_argument("--output-dir", required=True)

    p.add_argument("--preview-path", default="")
    p.add_argument("--delivery-log-path", default="")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--force-stale", action="store_true")

    p.add_argument("--top-desvios", type=int, default=3)

    args = p.parse_args()

    if args.phase == "preview":
        if not args.wbr_data_json:
            print(json.dumps({"ok": False, "error": "--wbr-data-json obrigatorio em preview"}))
            return 2
        if not args.calendar_path:
            print(json.dumps({"ok": False, "error": "--calendar-path obrigatorio em preview"}))
            return 2
        sys.exit(run_preview(args))
    else:
        sys.exit(run_commit(args))


if __name__ == "__main__":
    main()
