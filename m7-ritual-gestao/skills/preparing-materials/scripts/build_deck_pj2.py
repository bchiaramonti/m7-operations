#!/usr/bin/env python3
"""build_deck_pj2.py — Sidecar do plugin m7-ritual-gestao/preparing-materials para deck PJ2.

Portado de 02-Controle/_pj2-prep/scripts/build_pj2_deck.py V13 em 2026-05-12 (Sessao 4 da
maratona Bruno-Claude). Contrato: pj2-slide-requirements.md.

USO:
  - Dispatch automatico do build_deck.py quando Card eh PJ2 (is_pj2_card retorna True).
  - Pode ser invocado standalone tambem: python3 build_deck_pj2.py <args>

DEPENDENCIAS:
  - pandas, yaml (mesma stack do build_deck.py principal)
  - Assets em ../templates/assets/ (fontes M7 + logo) — resolvidos via __file__
  - Dump Bitrix offline em _pj2-prep/db-dump/ (override via env M7_PJ2_DUMP_DIR)

LIMITACOES CONHECIDAS:
  - Hardcoded "Maio 2026" e "Seguros e Consorcios" (default — overrides via globals + main) no titulo (TODO: usar metadata.ciclo + verticais)
  - Apos validacao V.1-V.4 com WBR canonical real, helpers _atingimento_bar/_gauge_svg
    serao migrados para build_deck.py principal (Sessao 4 v2).

Memory refs: feedback_pristine_cycles_skill_first, reference_avatar_circulo_id,
              feedback_canonical_data_json, project_pj2_n2_ritual_status.
"""
from __future__ import annotations
import argparse, html, io, json, sys, unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import yaml

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Resolved relative to script location for portability
SKILL_DIR = Path(__file__).parent.parent
PLUGIN_ASSETS = SKILL_DIR / "templates" / "assets"
# Override via env var ou CLI quando necessario:
import os as _os
if _os.environ.get("M7_PLUGIN_ASSETS"):
    PLUGIN_ASSETS = Path(_os.environ["M7_PLUGIN_ASSETS"])
# Path do dump Bitrix offline (V13 only — REQUER env var M7_PJ2_DUMP_DIR).
# S3 2026-05-20: _pj2-prep/ foi movido para _Historico/_pj2-prep_fase-A/ na Fase 3.
# S4 Fase 4 (2026-05-20): suporte ao path legacy `_pj2-prep/` removido.
# 2026-05-29: fallback hardcoded para path do dev removido — agora exige env var
# (portabilidade cross-user). Para ambiente M7: export M7_PJ2_DUMP_DIR=...
_dump_env = _os.environ.get("M7_PJ2_DUMP_DIR")
DUMP = Path(_dump_env) if _dump_env else None


def _require_dump() -> Path:
    """Acessor de DUMP que falha cedo com mensagem clara se env var ausente."""
    if DUMP is None:
        raise RuntimeError(
            "M7_PJ2_DUMP_DIR nao configurado. Set env var apontando para o "
            "dump Bitrix offline (ex: 02-Controle/_Historico/_pj2-prep_fase-A/db-dump). "
            "Sem ele as funcoes PJ2 load_users_by_id/load_deals_consorcios/"
            "load_deals_seguros nao podem ler dados."
        )
    return DUMP

# ────────────────────────────────────────────────────────────
# SHIM LAYER (2026-05-12 maratona Item 8) — DRY com plugin build_deck.py
# ────────────────────────────────────────────────────────────
# Importa helpers nativos do plugin para uso em NOVOS renders/refactors.
# Helpers V13 permanecem inalterados para preservar paridade byte-identica
# (ver bloco "TODO MIGRACAO DRY" abaixo para diferencas semanticas).
#
# Convencao de uso:
#   - Renders V13 portados (render_capa, render_fech_*, etc.): usam helpers V13
#     (cor_from_pct local com pct=0-100, _atingimento_bar local, etc.)
#   - Renders NOVOS (futuras adicoes pos-Sessao 4): preferir helpers do plugin
#     via prefixo `pdk.` (plugin deck helpers)
#
# Quando WBR canonical real emitir `por_canal[c]` em schema v1.1 (Sessao 6),
# migrar renders V13 gradualmente para `pdk.*` — validar paridade a cada
# substituicao antes de prosseguir.
# ────────────────────────────────────────────────────────────
try:
    import importlib.util as _ilu
    _spec = _ilu.spec_from_file_location("_pdk", SKILL_DIR / "scripts" / "build_deck.py")
    pdk = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(pdk)
    # Helpers disponiveis em pdk.*:
    #   pdk.cor_from_pct(pct, direction)        # pct 0-1.0 ranges 100/80 (plugin)
    #   pdk.status_from_pct(pct, direction)     # retorna {cor, emoji}
    #   pdk.resolve_circulo(responsavel, dir)   # P0-avatar (lookup avatars.yaml)
    #   pdk._gauge_svg(real, meta, label, dir)  # SVG semi-circular velocimetro
    #   pdk.load_template(skill_dir, variant)   # variant=pj2 etc.
    #   pdk.is_pj2_card(card)                   # detector Card PJ2
    _PDK_AVAILABLE = True
except Exception as _e:
    print(f"[build_deck_pj2] WARN: shim layer pdk nao disponivel ({_e}). Continuando com helpers V13.", file=__import__('sys').stderr)
    pdk = None
    _PDK_AVAILABLE = False

# ────────────────────────────────────────────────────────────
# TODO MIGRACAO DRY (Sessao 4 + 1 — 2026-05-12) — Helpers duplicados
# ────────────────────────────────────────────────────────────
# Este sidecar tem helpers proprios herdados do V13 que duplicam funcoes
# similares no `build_deck.py` principal do plugin:
#
#   Sidecar (este arquivo)        Plugin equivalente (build_deck.py)         Diferenca
#   ─────────────────────────     ───────────────────────────────────         ─────────
#   cor_from_pct (pct em 0-100,   cor_from_pct(pct, direction) (0-1.0,        Range diferente!
#     ranges 95/80)                 ranges 100/80)                            V13 mais permissivo
#                                                                             para verde
#   status_class(cor) → css       status_to_class(status) → css               Levemente diferente
#                                                                             (status string vs cor)
#   _atingimento_bar(...)         CSS .atingimento-bar (template)             V13 tem fill_width
#                                                                             cap em 100%
#   _ind_status(ind)              status_from_pct(pct, direction)             V13 le pre-computed;
#                                                                             plugin recalcula
#   slide_head/slide_foot         (inline em renders)                          Plugin nao tem equiv
#   esc / get                     html.escape / dict.get                       Compativeis
#
# Migracao FUTURA (quando WBR canonical real emitir por_canal[c] em schema v1.1):
#   1. Importar `from build_deck import cor_from_pct, status_from_pct, resolve_circulo, _gauge_svg`
#   2. Reescrever helpers V13 como shims que delegam (preservando assinatura legada)
#   3. Validar paridade BYTE-IDENTICA contra V13 do 12/05 antes de cada substituicao
#   4. Quando todos passarem, remover helpers V13 daqui
#
# Por que NAO migramos agora:
#   - Paridade visual 100% com V13 esta provada (diff 0 bytes) — mexer arrisca quebrar
#   - Ranges de cor_from_pct sao SEMANTICAMENTE diferentes (95/80 vs 100/80)
#   - Sessao 4 da maratona 2026-05-12 priorizou entregar deck funcional
#
# Referencias: pj2-slide-requirements.md edits #26/#30, RESUME-FROM-HERE.md
# ────────────────────────────────────────────────────────────

SQUAD_INV = 28
SQUAD_CRED = 7
SQUAD_TOTAL = 35

# Canonical injetado (Fase 4.6 inject_metas_ppi modo PJ2). Setado em main().
# Quando presente, as metas por canal (meta_canal / meta_canal_qty / meta_canal_vol)
# da tabela m7Prata.ciclo_metas_ppi tem precedencia sobre o split proporcional do Card,
# canal a canal (inv/cred). outros_m7 (e offline / nao-injetado) cai no Card.
_WBR_CANON = None


def _canon_meta_canal(vert, ind_id, fase, key):
    """Le meta por canal injetada no canonical. dict {canal: valor} ou None se ausente."""
    if _WBR_CANON is None:
        return None
    node = get(_WBR_CANON, "indicadores", fase, vert, ind_id)
    if not isinstance(node, dict):
        return None
    v = node.get(key)
    return v if isinstance(v, dict) and v else None


def _merge_canon_over_card(card_split, canon):
    """Merge canal a canal: tabela (inv/cred) sobre o split do Card; preserva o resto."""
    if not isinstance(canon, dict) or not canon:
        return card_split
    out = dict(card_split) if isinstance(card_split, dict) else {}
    for c, v in canon.items():
        if v is not None:
            out[c] = v
    return out

SNAPSHOT_DATE = datetime(2026, 5, 8, tzinfo=timezone.utc)

# Stages canônicos Cons — nomes SEM acento (paridade com STAGE_MAP_CONS do pipeline)
CONS_STAGES_ATIVO_ORDER = [
    ("C238:NEW", "Prospeccao", 45),
    ("C238:PREPARATION", "Investigacao", 35),
    ("C238:PREPAYMENT_INVOI", "Apresentacao", 25),
    ("C238:EXECUTING", "Proposta", 15),
    ("C238:FINAL_INVOICE", "Emissao de Contrato", 5),
    ("C238:UC_OTSRY0", "Cotas Alocadas", 2),
]
CONS_GANHO = ["C238:UC_V5VIOG", "C238:UC_M0R6Y3", "C238:UC_8E65GR", "C238:UC_R5G5TT", "C238:UC_LXOKS6", "C238:WON"]

# Stages canônicos Seg — nomes SEM acento (paridade com STAGE_MAP_SEG do pipeline)
SEG_STAGES_ATIVO_ORDER = [
    ("C156:UC_Y3C8IR", "Prospeccao", 30),
    ("C156:NEW", "Apresentacao", 25),
    ("C156:UC_JMC3M6", "Formalizacao", 20),
    ("C156:PREPARATION", "Cotacao", 15),
    ("C156:PREPAYMENT_INVOI", "Proposta Comercial", 10),
    ("C156:UC_2QHEO6", "Emissao de Apolice", 5),
    ("C156:UC_6GKZZR", "Onboarding", 2),
]
SEG_NOVA_VENDA_ID = 7268


# ────────────────────────────────────────────────────────────
# Step 8 hardcodes refactor (2026-05-12) — globals resolvidos em main()
# Permite usar mesmo sidecar em ciclos futuros sem editar codigo.
# ────────────────────────────────────────────────────────────
_MESES_PT = ['Janeiro', 'Fevereiro', 'Marco', 'Abril', 'Maio', 'Junho',
             'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
PJ2_VERTICAIS_DISPLAY = "Seguros e Consórcios"   # override em main()
PJ2_CICLO_ATUAL = "Maio 2026"                     # override em main() (ex: "Junho 2026")
PJ2_CICLO_FECHAMENTO = "Abril 2026"               # override em main() (mes anterior)
PJ2_COORDENADOR = "Joel Freitas"                  # override em main()
# S1-A1#2 (2026-05-15): Data do snapshot/cycle (badge "fechamento DD/MM/YYYY" da capa).
# Default placeholder; resolvido dinamicamente em _resolve_pj2_globals via wbr.data_referencia.
PJ2_DATA_FECHAMENTO_DISPLAY = "12/05/2026"        # override em main()
# Modo efetivo do ritual. Default "combinado" (PJ2 N2 mensal sempre cobre fechamento+atual).
# Badge "· fechamento DD/MM" so renderiza em ("fechamento", "combinado").
PJ2_EFFECTIVE_MODO = "combinado"                  # override em main() (via --modo se exposto)


def _resolve_pj2_globals(card, wbr, args=None):
    """Resolve globals PJ2_* a partir de Card + WBR. Chamado em main() apos load."""
    global PJ2_VERTICAIS_DISPLAY, PJ2_CICLO_ATUAL, PJ2_CICLO_FECHAMENTO, PJ2_COORDENADOR
    global PJ2_DATA_FECHAMENTO_DISPLAY, PJ2_EFFECTIVE_MODO

    # 1) verticais_display
    # S1-A1#1 (2026-05-15): Fallback chain do titulo de capa:
    #   1. card.apresentacao.titulo_publico (override explicito por Card)
    #   2. card.metadata.verticais_display (PJ2 sidecar legado)
    #   3. card.metadata.verticais joined ("X e Y" / "X, Y e Z")
    meta = (card or {}).get('metadata') or {}
    apresentacao = (card or {}).get('apresentacao') or {}
    titulo_publico = apresentacao.get('titulo_publico')
    if titulo_publico:
        PJ2_VERTICAIS_DISPLAY = titulo_publico
    else:
        vd = meta.get('verticais_display')
        if vd:
            PJ2_VERTICAIS_DISPLAY = vd
        else:
            verticais = meta.get('verticais') or []
            if len(verticais) >= 2:
                titles = [v.title() if isinstance(v, str) else str(v) for v in verticais]
                if len(titles) == 2:
                    PJ2_VERTICAIS_DISPLAY = f"{titles[0]} e {titles[1]}"
                else:
                    PJ2_VERTICAIS_DISPLAY = ", ".join(titles[:-1]) + f" e {titles[-1]}"
            elif len(verticais) == 1:
                PJ2_VERTICAIS_DISPLAY = str(verticais[0]).title()

    # 2) Coordenador
    coord = meta.get('owner') or ((meta.get('responsaveis') or {}).get('coordenador') or {}).get('nome')
    if coord:
        PJ2_COORDENADOR = coord

    # 3) Ciclos (atual + fechamento)
    def _fmt_periodo(p):
        """Aceita 'YYYY-MM' ou 'Maio 2026' ou date; retorna 'Mes YYYY'."""
        if not p: return None
        s = str(p)
        # Ja tem mes em PT (espaco + ano)? Mantem.
        if ' ' in s and any(m in s for m in _MESES_PT):
            return s
        # Tentar parse YYYY-MM ou YYYY-MM-DD
        try:
            from datetime import datetime
            if len(s) == 7 and s[4] == '-':
                d = datetime.strptime(s, '%Y-%m')
            else:
                d = datetime.fromisoformat(s.split('T')[0])
            return f"{_MESES_PT[d.month-1]} {d.year}"
        except Exception:
            return s

    periodo_atual = _fmt_periodo((wbr or {}).get('periodo_atual'))
    periodo_fech = _fmt_periodo((wbr or {}).get('periodo_fechamento'))
    if periodo_atual:
        PJ2_CICLO_ATUAL = periodo_atual
    if periodo_fech:
        PJ2_CICLO_FECHAMENTO = periodo_fech

    # Fallback: derivar de wbr.data_referencia (YYYY-MM-DD)
    data_ref = (wbr or {}).get('data_referencia')
    if not periodo_atual or not periodo_fech:
        if data_ref:
            try:
                from datetime import datetime
                d = datetime.fromisoformat(str(data_ref).split('T')[0])
                if not periodo_atual:
                    PJ2_CICLO_ATUAL = f"{_MESES_PT[d.month-1]} {d.year}"
                if not periodo_fech:
                    if d.month == 1:
                        m_prev, y_prev = 12, d.year - 1
                    else:
                        m_prev, y_prev = d.month - 1, d.year
                    PJ2_CICLO_FECHAMENTO = f"{_MESES_PT[m_prev-1]} {y_prev}"
            except Exception:
                pass

    # S1-A1#2 (2026-05-15): Data do snapshot do badge "fechamento DD/MM/YYYY" da capa.
    # Deriva de wbr.data_referencia (YYYY-MM-DD). Sem fallback: se data_referencia
    # ausente, mantem placeholder default ("12/05/2026").
    if data_ref:
        try:
            from datetime import datetime
            d = datetime.fromisoformat(str(data_ref).split('T')[0])
            PJ2_DATA_FECHAMENTO_DISPLAY = d.strftime("%d/%m/%Y")
        except Exception:
            pass

    # S1-A1#2 (2026-05-15): Modo efetivo. Precedencia:
    #   1. CLI --modo (se != "auto") — args opcional para retro-compat
    #   2. card.apresentacao.modo OR card.metadata.modo (se != "auto")
    #   3. default "combinado" (PJ2 N2 mensal sempre cobre fechamento+atual)
    cli_modo = getattr(args, "modo", None) if args is not None else None
    if cli_modo and cli_modo != "auto":
        PJ2_EFFECTIVE_MODO = cli_modo
    else:
        declared = apresentacao.get('modo') or meta.get('modo')
        if declared and declared != "auto":
            PJ2_EFFECTIVE_MODO = declared
        else:
            PJ2_EFFECTIVE_MODO = "combinado"


# ─── Helpers ───────────────────────────
def esc(s): return html.escape(str(s)) if s is not None else ""

def fmt_brl_short(v):
    if v is None: return "—"
    try: v = float(v)
    except: return str(v)
    if v == 0: return "R$ 0"
    if abs(v) >= 1e6: return f"R$ {v/1e6:.1f}M".replace(".", ",")
    if abs(v) >= 1e3: return f"R$ {v/1e3:.0f}K"
    return f"R$ {v:.0f}"

def fmt_pct(v, d=1):
    if v is None: return "—"
    try: return f"{float(v):.{d}f}%".replace(".", ",")
    except: return str(v)

def fmt_int(v):
    if v is None: return "—"
    try: return str(int(round(float(v))))
    except: return str(v)

def fmt_n(v):
    if v is None: return "—"
    try: v = float(v)
    except: return str(v)
    if v == int(v): return str(int(v))
    return f"{v:.2f}".replace(".", ",")

def status_class(cor):
    return {"verde": "good", "amarelo": "warn", "vermelho": "bad"}.get(cor, "mute")

def cor_from_pct(pct, direction="maior_melhor"):
    if pct is None: return "cinza"
    if direction == "menor_melhor":
        # Para "menor_melhor" (Estagnadas % ativas, Sem Movimentação):
        # pct = realizado / meta_max × 100. Se realizado <= meta_max → pct <= 100 (verde).
        if pct <= 100: return "verde"
        if pct <= 130: return "amarelo"
        return "vermelho"
    if pct >= 95: return "verde"
    if pct >= 80: return "amarelo"
    return "vermelho"

def get(d, *keys, default=None):
    for k in keys:
        if d is None: return default
        if isinstance(d, dict): d = d.get(k)
        else: return default
    return d if d is not None else default

def load_b64(name):
    p = PLUGIN_ASSETS / name
    if not p.exists(): return ""
    return p.read_text(encoding="utf-8").strip()

def normalize_name(s):
    if not s or pd.isna(s): return ""
    s = str(s).strip().upper()
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    return s

def parse_iso(s):
    if not s or pd.isna(s): return None
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except: return None

# ─── Squad classification ──────────────────────────────────────
def build_squad_index(card):
    """Retorna dict {nome_normalizado: ('investimentos'|'credito'|'outros_m7', nome_canonico)}."""
    idx = {}
    apresent = get(card, "apresentacao") or {}
    resp = apresent.get("responsaveis") or []
    for r in resp:
        nome_canal = (r.get("nome") or "").lower()
        if "credito" in nome_canal or "crédito" in nome_canal:
            canal = "credito"
        elif "investimento" in nome_canal:
            canal = "investimentos"
        else:
            continue
        for sq in (r.get("squad") or []):
            idx[normalize_name(sq)] = (canal, sq)
    outros = apresent.get("outros_m7") or {}
    for grupo in ["especialistas", "coordenador", "outros"]:
        for nm in (outros.get(grupo) or []):
            idx[normalize_name(nm)] = ("outros_m7", nm)
    return idx

def classify_assessor(nome, squad_idx):
    """Retorna (canal, nome_canonico). canal in {investimentos,credito,outros_m7,desconhecido}."""
    if not nome or pd.isna(nome): return ("desconhecido", str(nome))
    n = normalize_name(nome)
    if n in squad_idx:
        return squad_idx[n]
    # tentar primeiro+último
    parts = n.split()
    if len(parts) >= 2:
        first_last = f"{parts[0]} {parts[-1]}"
        if first_last in squad_idx:
            return squad_idx[first_last]
    return ("desconhecido", str(nome))

# ─── Extração por assessor ───────────────────────────────────
def load_users_by_id():
    dump = _require_dump()
    p = dump / "bitrix/users.json"
    if not p.exists(): return {}
    users = json.loads(p.read_text(encoding="utf-8"))
    return {str(u["ID"]): f"{u.get('NAME','').strip()} {u.get('LAST_NAME','').strip()}".strip() for u in users}

def days_in_stage(deal_id, stage_id, stage_idx, date_create):
    events = stage_idx.get(str(deal_id), [])
    matching = [e for e in events if str(e.get("STAGE_ID","")) == str(stage_id)]
    if matching:
        ts = max((parse_iso(e.get("CREATED_TIME")) for e in matching if parse_iso(e.get("CREATED_TIME"))), default=None)
    else:
        ts = parse_iso(date_create)
    if ts is None: return 0.0
    return (SNAPSHOT_DATE - ts).total_seconds() / 86400.0

def extract_per_assessor_cons(card, periodo_atual="2026-05", periodo_fech="2026-04"):
    dump = _require_dump()
    deals = pd.read_csv(dump / "bitrix/deals_consorcios.csv", encoding="utf-8-sig")
    deals["mes_create"] = pd.to_datetime(deals["DATE_CREATE"], errors="coerce").dt.strftime("%Y-%m")
    deals["mes_close"] = pd.to_datetime(deals["CLOSEDATE"], errors="coerce").dt.strftime("%Y-%m")
    sh = json.loads((dump / "bitrix/stagehistory_cons.json").read_text(encoding="utf-8"))
    sh_idx = defaultdict(list)
    for ev in sh: sh_idx[str(ev.get("OWNER_ID",""))].append(ev)
    acts = json.loads((dump / "bitrix/activities_pj2.json").read_text(encoding="utf-8"))
    deals_com_act = {str(a.get("_deal_id","")) for a in acts}

    squad_idx = build_squad_index(card)
    users = load_users_by_id()

    def resolve_assigned(uid):
        if pd.isna(uid) or not str(uid).strip(): return None
        return users.get(str(uid).split(".")[0])
    out = defaultdict(lambda: {
        "criadas_atual": 0, "criadas_fech": 0,
        "won_fech": 0, "won_atual": 0, "lose_fech": 0, "lose_atual": 0,
        "ativas_qty": 0, "ativas_vol": 0.0,
        "estagnadas_qty": 0, "estagnadas_vol": 0.0, "estagnadas_dias_total": 0.0,
        "sem_mov_qty": 0, "canal": "desconhecido",
    })

    ATIVO_IDS = {sid for sid, _, _ in CONS_STAGES_ATIVO_ORDER}

    # Stagehistory: 1a entrada GANHO/LOSE
    sh_df = pd.DataFrame(sh)
    if not sh_df.empty:
        sh_df["dt"] = pd.to_datetime(sh_df["CREATED_TIME"])
        sh_df["mes"] = sh_df["dt"].dt.strftime("%Y-%m")
        closures = sh_df[sh_df["STAGE_ID"].isin(CONS_GANHO + ["C238:LOSE"])]
        first = closures.sort_values("dt").drop_duplicates("OWNER_ID", keep="first")
        first_atual = first[first["mes"] == periodo_atual]
        first_fech = first[first["mes"] == periodo_fech]
    else:
        first_atual = first_fech = pd.DataFrame(columns=["OWNER_ID","STAGE_ID"])

    closures_by_id = {}
    for _, ev in pd.concat([first_atual, first_fech]).iterrows():
        closures_by_id[str(ev["OWNER_ID"])] = (ev["STAGE_ID"], ev.get("mes",""))

    deals_idx = deals.set_index(deals["ID"].astype(str))

    aliases = get_assessor_aliases(card)
    for _, d in deals.iterrows():
        nome_raw = d.get("UF_CRM_1758122406")
        # Correcao 2026-05-12: aplicar alias (Felipe Nogueira → Filipe Costa)
        nome_raw = apply_assessor_alias(nome_raw, aliases) if nome_raw and not pd.isna(nome_raw) else nome_raw
        canal, nome = classify_assessor(nome_raw, squad_idx)
        if canal == "desconhecido":
            # Fallback: usar ASSIGNED_BY_ID resolvido via users.json
            nome_assigned = resolve_assigned(d.get("ASSIGNED_BY_ID"))
            if nome_assigned:
                nome_assigned = apply_assessor_alias(nome_assigned, aliases)
            if nome_assigned:
                canal2, nome2 = classify_assessor(nome_assigned, squad_idx)
                if canal2 != "desconhecido":
                    canal, nome = canal2, nome2
                else:
                    nome = nome_assigned
            elif nome_raw and not pd.isna(nome_raw):
                nome = str(nome_raw).strip()
            else:
                nome = "Sem MKT/Responsável"
        rec = out[nome]
        rec["canal"] = canal

        # Criadas
        mc = d.get("mes_create")
        if mc == periodo_atual: rec["criadas_atual"] += 1
        elif mc == periodo_fech: rec["criadas_fech"] += 1

        # Ativas (whitelist)
        if d["STAGE_ID"] in ATIVO_IDS:
            rec["ativas_qty"] += 1
            rec["ativas_vol"] += float(d.get("OPPORTUNITY") or 0)
            # Estagnadas (≥7d)
            dias = days_in_stage(d["ID"], d["STAGE_ID"], sh_idx, d.get("DATE_CREATE"))
            if dias >= 7:
                rec["estagnadas_qty"] += 1
                rec["estagnadas_vol"] += float(d.get("OPPORTUNITY") or 0)
                rec["estagnadas_dias_total"] += dias

        # Won/Lose via stagehistory
        cls = closures_by_id.get(str(d["ID"]))
        if cls:
            stg, mes = cls
            if stg in CONS_GANHO:
                if mes == periodo_atual: rec["won_atual"] += 1
                elif mes == periodo_fech: rec["won_fech"] += 1
            elif stg == "C238:LOSE":
                if mes == periodo_atual: rec["lose_atual"] += 1
                elif mes == periodo_fech: rec["lose_fech"] += 1

    # Sem Movimentação não temos por assessor (dump activities incompleto)
    return dict(out)

def extract_per_assessor_seg(card, periodo_atual="2026-05", periodo_fech="2026-04"):
    dump = _require_dump()
    deals_raw = pd.read_csv(dump / "bitrix/deals_seguros.csv", encoding="utf-8-sig")
    deals = deals_raw[deals_raw["UF_CRM_1773922604648"] == SEG_NOVA_VENDA_ID].copy()
    deals["mes_create"] = pd.to_datetime(deals["DATE_CREATE"], errors="coerce").dt.strftime("%Y-%m")
    deals["mes_close"] = pd.to_datetime(deals["CLOSEDATE"], errors="coerce").dt.strftime("%Y-%m")
    sh = json.loads((dump / "bitrix/stagehistory_seg.json").read_text(encoding="utf-8"))
    sh_idx = defaultdict(list)
    for ev in sh: sh_idx[str(ev.get("OWNER_ID",""))].append(ev)
    users = load_users_by_id()
    squad_idx = build_squad_index(card)

    def resolve_assessor(uid_or_list):
        if pd.isna(uid_or_list) or not str(uid_or_list).strip() or str(uid_or_list) in ("False","0","nan"):
            return None
        first = str(uid_or_list).split("|")[0].split(".")[0]
        return users.get(first)

    out = defaultdict(lambda: {
        "criadas_atual": 0, "criadas_fech": 0,
        "won_fech": 0, "won_atual": 0, "lose_fech": 0, "lose_atual": 0,
        "ativas_qty": 0, "ativas_vol": 0.0,
        "estagnadas_qty": 0, "estagnadas_vol": 0.0, "estagnadas_dias_total": 0.0,
        "sem_mov_qty": 0, "canal": "desconhecido",
    })

    ATIVO_IDS_S = {sid for sid, _, _ in SEG_STAGES_ATIVO_ORDER}

    sh_df = pd.DataFrame(sh)
    if not sh_df.empty:
        sh_df["dt"] = pd.to_datetime(sh_df["CREATED_TIME"])
        sh_df["mes"] = sh_df["dt"].dt.strftime("%Y-%m")
        closures = sh_df[sh_df["STAGE_ID"].isin(["C156:WON", "C156:LOSE"])]
        first = closures.sort_values("dt").drop_duplicates("OWNER_ID", keep="first")
        deals_ids_set = set(deals["ID"].astype(str))
        first = first[first["OWNER_ID"].astype(str).isin(deals_ids_set)]
    else:
        first = pd.DataFrame(columns=["OWNER_ID","STAGE_ID","mes"])

    closures_by_id = {}
    for _, ev in first.iterrows():
        closures_by_id[str(ev["OWNER_ID"])] = (ev["STAGE_ID"], ev.get("mes",""))

    aliases = get_assessor_aliases(card)
    for _, d in deals.iterrows():
        nome = resolve_assessor(d.get("UF_CRM_1745419691"))
        if not nome:
            nome = resolve_assessor(d.get("ASSIGNED_BY_ID")) or "Sem SDR"
        # Correcao 2026-05-12: aplicar alias (Felipe Nogueira → Filipe Costa)
        nome = apply_assessor_alias(nome, aliases)
        canal, nome_canon = classify_assessor(nome, squad_idx)
        nome_use = nome_canon if canal != "desconhecido" else nome
        rec = out[nome_use]
        rec["canal"] = canal

        mc = d.get("mes_create")
        if mc == periodo_atual: rec["criadas_atual"] += 1
        elif mc == periodo_fech: rec["criadas_fech"] += 1

        if d["STAGE_ID"] in ATIVO_IDS_S:
            rec["ativas_qty"] += 1
            rec["ativas_vol"] += float(d.get("OPPORTUNITY") or 0)
            dias = days_in_stage(d["ID"], d["STAGE_ID"], sh_idx, d.get("DATE_CREATE"))
            if dias >= 7:
                rec["estagnadas_qty"] += 1
                rec["estagnadas_vol"] += float(d.get("OPPORTUNITY") or 0)
                rec["estagnadas_dias_total"] += dias

        cls = closures_by_id.get(str(d["ID"]))
        if cls:
            stg, mes = cls
            if stg == "C156:WON":
                if mes == periodo_atual: rec["won_atual"] += 1
                elif mes == periodo_fech: rec["won_fech"] += 1
            elif stg == "C156:LOSE":
                if mes == periodo_atual: rec["lose_atual"] += 1
                elif mes == periodo_fech: rec["lose_fech"] += 1

    return dict(out)

def get_hidden_names_norm(card):
    """Set normalizado de nomes hidden_in_squad_lists (não aparecem em listings)."""
    apresent = get(card, "apresentacao") or {}
    return set(normalize_name(n) for n in (apresent.get("hidden_in_squad_lists") or []))


def get_assessor_aliases(card):
    """Dict {nome_raw_normalizado: nome_canonico} para corrigir typos/cadastros incorretos do Bitrix."""
    apresent = get(card, "apresentacao") or {}
    raw_map = apresent.get("assessor_aliases") or {}
    return {normalize_name(k): v for k, v in raw_map.items()}


def apply_assessor_alias(nome, aliases_dict):
    """Aplica alias se houver. Retorna nome canonico ou nome original."""
    if not nome or not aliases_dict:
        return nome
    return aliases_dict.get(normalize_name(nome), nome)


def get_squad_full_list(card, canal):
    """Retorna lista completa de nomes do squad, excluindo hidden_in_squad_lists."""
    apresent = get(card, "apresentacao") or {}
    hidden = set(apresent.get("hidden_in_squad_lists") or [])
    if canal == "investimentos":
        for r in apresent.get("responsaveis") or []:
            if "investimento" in (r.get("nome") or "").lower():
                return [s for s in (r.get("squad") or []) if s not in hidden]
    if canal == "credito":
        for r in apresent.get("responsaveis") or []:
            if "credito" in (r.get("nome") or "").lower() or "crédito" in (r.get("nome") or "").lower():
                return [s for s in (r.get("squad") or []) if s not in hidden]
    if canal == "outros_m7":
        out = []
        outros = apresent.get("outros_m7") or {}
        for grupo in ["especialistas", "coordenador", "outros"]:
            out.extend(outros.get(grupo) or [])
        return [s for s in out if s not in hidden]
    return []


def filter_hidden(assesores_canal, card):
    """Remove assessores hidden da lista (assesores_canal é list de tuples (nome, dict))."""
    hidden = get_hidden_names_norm(card)
    return [(n, r) for n, r in assesores_canal if normalize_name(n) not in hidden]


# ─── Meta derivation ─────────────────────────────────────────
def meta_proporcional(meta_total):
    if meta_total is None: return {"investimentos": None, "credito": None, "outros_m7": None}
    return {
        "investimentos": meta_total * SQUAD_INV / SQUAD_TOTAL,
        "credito": meta_total * SQUAD_CRED / SQUAD_TOTAL,
        "outros_m7": None,
    }

def get_meta_explicit_canal(card, vert, ind_id, fase):
    per_key = "abril_2026" if fase == "fechamento" else "maio_2026"
    return get(card, "metas_canal", vert, ind_id, per_key)

def _derive_meta_canal_card(card, vert, ind_id, fase):
    explicit = get_meta_explicit_canal(card, vert, ind_id, fase)
    if explicit: return explicit
    if "taxa_conversao" in ind_id:
        v = get(card, "metas_ppi", ind_id, "valor")
        return {"investimentos": v, "credito": v, "outros_m7": v}
    metas_ppi = get(card, "metas_ppi", ind_id) or {}
    if fase == "atual" and "valor_proximo_mes" in metas_ppi:
        meta_total = metas_ppi.get("valor_proximo_mes")
    elif "valor" in metas_ppi:
        meta_total = metas_ppi.get("valor")
    elif fase == "atual" and "qty_proximo_mes" in metas_ppi:
        meta_total = metas_ppi.get("qty_proximo_mes")
    else:
        meta_total = metas_ppi.get("qty")
    return meta_proporcional(meta_total)


def derive_meta_canal(card, vert, ind_id, fase):
    """Meta por canal: prefere a tabela (canonical.meta_canal) inv/cred; Card no resto.

    ratio/days (taxa_conversao, tempo) NAO sao injetados -> caem 100% no Card
    (mesma regra do N3). Offline / sem inject -> _canon_meta_canal None -> Card.
    """
    card_split = _derive_meta_canal_card(card, vert, ind_id, fase)
    if "taxa_conversao" in ind_id or "tempo_de_ciclo" in ind_id:
        return card_split
    # ativas guarda a qty por canal em meta_canal_qty; demais em meta_canal
    key = "meta_canal_qty" if "oportunidades_ativas_funil" in ind_id else "meta_canal"
    return _merge_canon_over_card(card_split, _canon_meta_canal(vert, ind_id, fase, key))

def derive_meta_ativas_volume_canal(card, vert, fase):
    """Meta volume_ativas_canal = meta_qty_ativas_canal × ticket_medio_ativas_meta."""
    ativ_id = "oportunidades_ativas_funil_seg" if vert == "seguros" else "oportunidades_ativas_funil"
    metas_ppi = get(card, "metas_ppi", ativ_id) or {}
    if fase == "atual":
        v = metas_ppi.get("volume_proximo_mes") or metas_ppi.get("volume")
    else:
        v = metas_ppi.get("volume")
    # prefere a tabela (canonical.meta_canal_vol) inv/cred; Card no resto
    return _merge_canon_over_card(meta_proporcional(v),
                                  _canon_meta_canal(vert, ativ_id, fase, "meta_canal_vol"))

def derive_meta_ativas_ticket_canal(card, vert, fase):
    """Ticket meta Ativas por canal = vol_ativas_canal / qty_ativas_canal.
    Reflete o rebalanceamento planejado:
      - Se há split vol_mensal_canal explícito (rebalanceamento user) → usa essa proporção
      - Senão → vol_ativas_canal proporcional ao squad (mesma lógica de vol_ativas_canal)
      - qty_ativas_canal sempre proporcional ao squad
    Garante consistência: ticket_canal = vol_canal_meta / qty_canal_meta."""
    ativ_id = "oportunidades_ativas_funil_seg" if vert == "seguros" else "oportunidades_ativas_funil"
    metas_ppi = get(card, "metas_ppi", ativ_id) or {}
    if fase == "atual":
        vol_ativas_total = metas_ppi.get("volume_proximo_mes") or metas_ppi.get("volume")
        qty_ativas_total = metas_ppi.get("qty_proximo_mes") or metas_ppi.get("qty")
    else:
        vol_ativas_total = metas_ppi.get("volume")
        qty_ativas_total = metas_ppi.get("qty")

    # Tenta split de vol_mensal (rebalanceamento explícito)
    vol_mensal_id = "volume_seguros_mensal" if vert == "seguros" else "volume_consorcio_mensal"
    vol_mensal_meta = derive_meta_canal(card, vert, vol_mensal_id, fase) or {}
    sum_mensal = sum((v or 0) for v in vol_mensal_meta.values()) or 0

    # Fallback: split proporcional squad (mesmo usado em derive_meta_ativas_volume_canal)
    vol_ativas_canal_squad = meta_proporcional(vol_ativas_total)
    qty_meta_squad = meta_proporcional(qty_ativas_total)

    out = {}
    for c in ["investimentos", "credito", "outros_m7"]:
        v_mensal_c = vol_mensal_meta.get(c)
        # Decide vol_ativas_canal: usa rebalanceamento se vol_mensal_canal disponível, senão squad
        if v_mensal_c is not None and sum_mensal > 0:
            pct_vol_c = v_mensal_c / sum_mensal
            vol_ativas_c = vol_ativas_total * pct_vol_c if vol_ativas_total else None
        else:
            vol_ativas_c = vol_ativas_canal_squad.get(c)
        qty_c = qty_meta_squad.get(c)
        out[c] = (vol_ativas_c / qty_c) if (vol_ativas_c and qty_c and qty_c > 0) else None
    # override per canal pela tabela quando ha vol E qty injetados (inv/cred)
    cv = _canon_meta_canal(vert, ativ_id, fase, "meta_canal_vol") or {}
    cq = _canon_meta_canal(vert, ativ_id, fase, "meta_canal_qty") or {}
    for c in ["investimentos", "credito", "outros_m7"]:
        if cv.get(c) is not None and cq.get(c):
            out[c] = cv[c] / cq[c]
    return out

def derive_meta_ticket_fechamento_canal(card, vert, fase):
    """Ticket fechamento meta = vol_canal / qty_canal."""
    if vert == "seguros":
        vol_id, qty_id = "volume_seguros_mensal", "quantidade_seguros_mensal"
    else:
        vol_id, qty_id = "volume_consorcio_mensal", "quantidade_consorcio_mensal"
    vol_meta = derive_meta_canal(card, vert, vol_id, fase)
    qty_meta = derive_meta_canal(card, vert, qty_id, fase)
    out = {}
    for c in ["investimentos","credito","outros_m7"]:
        v = vol_meta.get(c); q = qty_meta.get(c)
        out[c] = (v / q) if (v is not None and q and q > 0) else None
    return out


# ─── CSS ────────────────────────────────────────────────────
CSS_BASE = """
@font-face { font-family: twkEverett; src: url(data:font/otf;base64,{ASSET_FONT_REGULAR_B64}) format("opentype"); font-weight: 400; }
@font-face { font-family: twkEverett; src: url(data:font/otf;base64,{ASSET_FONT_MEDIUM_B64}) format("opentype"); font-weight: 500; }
@font-face { font-family: twkEverett; src: url(data:font/otf;base64,{ASSET_FONT_BOLD_B64}) format("opentype"); font-weight: 700; }
@font-face { font-family: twkEverett; src: url(data:font/otf;base64,{ASSET_FONT_LIGHT_B64}) format("opentype"); font-weight: 300; }
@font-face { font-family: twkEverett; src: url(data:font/otf;base64,{ASSET_FONT_ULTRALIGHT_B64}) format("opentype"); font-weight: 200; }
:root {
  --verde-caqui:#424135; --verde-medio:#4f4e3c; --verde-claro:#79755c; --verde-escuro:#2d2d24;
  --off-white:#fffdef; --lime:#eef77c; --vc-50:#f6f6f5; --vc-100:#d0d0cc; --vc-200:#aeada8;
  --vc-300:#8a8981; --vc-400:#66655b; --vc-500:#424135; --vc-700:#28271f;
  --error:#e40014; --font-sans:"twkEverett",Arial,sans-serif;
}
*{box-sizing:border-box;margin:0;padding:0;-webkit-font-smoothing:antialiased;-moz-osx-font-smoothing:grayscale;text-rendering:optimizeLegibility;}
html,body{background:var(--vc-700);color:var(--vc-500);font-family:var(--font-sans);}
body{padding:24px;display:flex;flex-direction:column;gap:24px;align-items:center;line-height:1.5;}
section{width:1920px;height:1080px;background:var(--off-white);color:var(--vc-500);display:flex;flex-direction:column;overflow:hidden;position:relative;box-shadow:0 8px 24px rgba(0,0,0,0.4);font-family:var(--font-sans);}
section.dark{background:var(--verde-caqui);color:var(--off-white);}
.slide-head{flex-shrink:0;background:var(--verde-caqui);color:var(--off-white);display:flex;align-items:center;justify-content:space-between;padding:28px 56px;border-bottom:1px solid var(--verde-medio);}
.slide-head .h-left{display:flex;align-items:center;gap:24px;}
.slide-head .h-title{font-size:32px;font-weight:400;line-height:1.1;}
.slide-head .h-eyebrow{font-size:13px;font-weight:500;letter-spacing:0.18em;text-transform:uppercase;color:var(--lime);padding-bottom:6px;}
.slide-head .h-logo{height:32px;}
.slide-head .h-divider{width:1px;height:28px;background:var(--verde-claro);}
.avatar{width:56px;height:56px;border-radius:50%;background:var(--lime);color:var(--verde-caqui);display:flex;align-items:center;justify-content:center;font-weight:700;font-size:22px;}
.slide-body{flex-grow:1;display:flex;flex-direction:column;padding:36px 48px 28px;gap:18px;min-height:0;overflow:hidden;}
.slide-foot{flex-shrink:0;display:flex;align-items:center;justify-content:space-between;padding:16px 56px 22px;font-size:13px;color:var(--verde-claro);letter-spacing:0.1em;}
.slide-foot .f-num{font-variant-numeric:tabular-nums;font-weight:500;}
.slide-foot .f-meta{display:flex;align-items:center;gap:14px;}
.slide-foot .f-meta .dot{width:4px;height:4px;border-radius:50%;background:var(--vc-200);}

.card{background:#fff;border:1px solid var(--vc-100);border-radius:8px;display:flex;flex-direction:column;overflow:hidden;min-height:0;}
.card-head{background:var(--verde-medio);color:var(--off-white);padding:14px 20px;font-size:13px;font-weight:500;letter-spacing:0.12em;text-transform:uppercase;flex-shrink:0;}
.card-head.lime{background:var(--lime);color:var(--verde-caqui);}
.card-head.error{background:var(--error);color:#fff;}
.card-head.success{background:#4f7c4d;color:#fff;}
.card-body{padding:18px;display:flex;flex-direction:column;gap:10px;flex-grow:1;min-height:0;}

/* 2026-05-27: sync N3 — callout Lide +15% (14→16 body; 11→13 label). */
.callout{background:#fff;border:1px solid var(--vc-100);border-left:4px solid var(--lime);border-radius:6px;padding:14px 18px;font-size:16px;line-height:1.45;color:var(--verde-caqui);}
.callout strong{font-weight:600;}
.callout .label{font-size:13px;letter-spacing:0.18em;text-transform:uppercase;color:var(--verde-claro);display:block;margin-bottom:4px;}

/* Cover */
.cover{background:var(--verde-caqui);color:var(--off-white);padding:0;}
.cover .grid-bg{position:absolute;inset:0;background-image:linear-gradient(rgba(255,253,239,0.04) 1px,transparent 1px),linear-gradient(90deg,rgba(255,253,239,0.04) 1px,transparent 1px);background-size:80px 80px;}
.cover .cover-inner{position:relative;z-index:1;flex-grow:1;display:grid;grid-template-columns:1fr 1fr;padding:96px 96px 80px;gap:64px;}
.cover h1{font-size:116px;line-height:0.96;font-weight:300;letter-spacing:-0.025em;max-width:14ch;}
.cover h1 em{font-style:normal;color:var(--lime);}
.cover .cover-eyebrow{display:flex;align-items:center;gap:20px;margin-bottom:40px;}
.cover .cover-eyebrow .bar{width:64px;height:3px;background:var(--lime);}
.cover .cover-eyebrow span{font-size:16px;letter-spacing:0.24em;text-transform:uppercase;color:var(--lime);font-weight:500;}
.cover .cover-meta{display:flex;flex-direction:column;justify-content:flex-end;}
.cover .meta-block{display:grid;grid-template-columns:200px 1fr;gap:24px;padding:22px 0;border-top:1px solid rgba(255,253,239,0.18);}
.cover .meta-block .k{font-size:13px;letter-spacing:0.18em;text-transform:uppercase;color:var(--verde-claro);}
.cover .meta-block .v{font-size:22px;color:var(--off-white);}
.cover .meta-block .v strong{font-weight:500;color:var(--lime);}
.cover-foot{position:absolute;left:96px;right:96px;bottom:56px;display:flex;justify-content:space-between;align-items:flex-end;z-index:1;}
.cover-foot .logo{height:56px;}
.cover-foot .stamp{font-size:13px;letter-spacing:0.16em;text-transform:uppercase;color:var(--verde-claro);}
.cover-foot .stamp strong{color:var(--off-white);font-weight:500;}

/* Agenda */
.agenda{display:grid;grid-template-columns:320px 1fr;gap:80px;flex-grow:1;}
.ag-eyebrow{font-size:13px;letter-spacing:0.22em;text-transform:uppercase;color:var(--verde-claro);margin-bottom:24px;}
.agenda-tl{position:relative;padding-left:32px;}
.agenda-tl::before{content:"";position:absolute;left:11px;top:16px;bottom:16px;width:1px;background:var(--vc-100);}
.tl-row{position:relative;display:grid;grid-template-columns:1fr auto;gap:24px;padding:14px 0;border-bottom:1px solid var(--vc-50);}
.tl-row::before{content:"";position:absolute;left:-28px;top:26px;width:9px;height:9px;border-radius:50%;background:#fff;border:1.5px solid var(--vc-200);}
.tl-row .tl-num{font-size:12px;letter-spacing:0.18em;color:var(--verde-claro);margin-bottom:4px;text-transform:uppercase;}
.tl-row .tl-title{font-size:22px;line-height:1.15;color:var(--verde-caqui);}
.tl-row .tl-sub{font-size:13px;color:var(--verde-claro);margin-top:4px;}
.tl-row .tl-time{font-size:13px;letter-spacing:0.14em;text-transform:uppercase;color:var(--verde-claro);padding-top:22px;}
.tl-row.feature{padding:18px 24px;background:var(--verde-caqui);border-radius:6px;border-bottom:none;}
.tl-row.feature::before{background:var(--lime);border-color:var(--lime);}
.tl-row.feature .tl-num,.tl-row.feature .tl-time{color:var(--lime);}
.tl-row.feature .tl-title{color:var(--off-white);}
.tl-row.feature .tl-title em{font-style:normal;color:var(--lime);}
/* Correcao 2026-05-12 (REVIEW 6): Slide Recap — header padrao (slide_head), body com auto-distribuicao */
/* Body: auto-distribuição vertical via flex (justify-content:space-evenly) */
.recap2-slide .slide-body{display:flex;flex-direction:column;}
.recap2-body{padding:14px 8px;display:flex;flex-direction:column;flex-grow:1;justify-content:space-evenly;gap:0;}
.recap2-row{display:grid;grid-template-columns:5px 56px 230px 1fr;gap:18px;align-items:center;padding:10px 0;border-bottom:1px solid var(--vc-100);}
.recap2-row:last-child{border-bottom:none;}
.recap2-bar{width:5px;height:32px;background:var(--lime);border-radius:3px;}
.recap2-num{font-size:15px;font-weight:700;color:var(--verde-medio);letter-spacing:0.08em;font-variant-numeric:tabular-nums;padding-left:6px;}
.recap2-lbl{font-size:19px;font-weight:600;color:var(--verde-caqui);letter-spacing:0.005em;line-height:1.25;padding-right:28px;}
.recap2-txt{font-size:15px;color:var(--verde-medio);line-height:1.55;}
.recap2-slide .slide-foot{margin-top:14px;}
/* Correcao 2026-05-11 (REVIEW 3): Slide 08 design image 1 — cards horizontais com pct grande */
.prob-headline{font-size:17px;line-height:1.5;color:var(--verde-caqui);margin-bottom:26px;padding:20px 26px;background:#fff;border:1px solid var(--vc-100);border-left:4px solid var(--error);border-radius:6px;box-shadow:0 2px 8px rgba(66,65,53,0.04);}
.prob-headline .ch-eyebrow{display:block;font-size:12px;letter-spacing:0.2em;text-transform:uppercase;color:var(--error);font-weight:700;margin-bottom:9px;}
.prob-headline em{font-style:italic;font-family:Georgia,'Times New Roman',serif;font-weight:500;color:var(--verde-caqui);}
.prob-grid{display:grid;grid-template-columns:1fr 1fr;gap:31px;flex-grow:1;min-height:0;}
.prob-vert{display:flex;flex-direction:column;gap:15px;min-height:0;}
.prob-vert-head{font-size:14px;letter-spacing:0.18em;text-transform:uppercase;color:var(--verde-caqui);padding:9px 0 11px;border-bottom:2px solid var(--verde-medio);font-weight:700;flex-shrink:0;display:flex;align-items:center;gap:9px;}
.prob-vert-head::before{content:'';display:inline-block;width:4px;height:20px;background:var(--verde-medio);border-radius:2px;}
.prob-vert-head.seg::before{background:var(--verde-caqui);}
.prob-vert-head.cons::before{background:#8a7e58;}
.prob-vert-list{display:flex;flex-direction:column;gap:13px;flex:1 1 0;overflow-y:auto;min-height:0;}
.prob-vert-list::-webkit-scrollbar{width:6px;}
.prob-vert-list::-webkit-scrollbar-thumb{background:var(--vc-200);border-radius:3px;}
.prob-card{background:#fff;border:1px solid var(--vc-100);border-radius:8px;padding:20px 24px;display:flex;flex-direction:column;gap:11px;box-shadow:0 2px 6px rgba(66,65,53,0.04);}
.prob-card.prob-card-ok{border-left:4px solid #4caf50;}
.prob-card-head{display:flex;justify-content:space-between;align-items:flex-start;gap:13px;}
.prob-card-head-left{display:flex;flex-direction:column;gap:4px;flex:1;}
.prob-card-tit{font-size:20px;font-weight:700;color:var(--verde-caqui);line-height:1.2;letter-spacing:-0.005em;}
.prob-card-vals{font-size:13px;color:var(--verde-claro);font-weight:400;letter-spacing:0.02em;}
.prob-card-vals strong{color:var(--verde-medio);font-weight:600;}
.prob-card-vals .vs-meta{margin-left:4px;}
.prob-card-pct{font-size:53px;font-weight:700;color:var(--error);font-variant-numeric:tabular-nums;letter-spacing:-0.03em;line-height:0.9;}
.prob-card-pct .pct-mark{font-size:0.55em;font-weight:500;margin-left:1px;}
.prob-card-divider{height:1px;background:var(--vc-100);margin:2px 0;}
.prob-card-txt{font-size:14px;color:var(--verde-claro);line-height:1.55;margin-top:0;}

/* Slide 4 — fechamento visão geral (12 cards 2 grids 3x2) — VALORES MAIORES */
.fech-headline{background:var(--vc-50);border-left:6px solid var(--lime);padding:20px 24px;margin-bottom:14px;font-size:24px;line-height:1.3;color:var(--verde-caqui);font-weight:300;}
.fech-headline strong{font-weight:500;}
.fech-headline em{font-style:normal;font-weight:500;background:linear-gradient(180deg,transparent 60%,rgba(238,247,124,0.45) 60%);padding:0 4px;}
.fech-headline .fh-eyebrow{display:block;font-size:11px;letter-spacing:0.24em;text-transform:uppercase;color:var(--verde-claro);margin-bottom:8px;font-weight:500;}
/* Correcao 2026-05-11 #2 (REVIEW 2): divisao visual MAIS GROSSA #6E6A53 */
.fech-2grids{display:grid;grid-template-columns:1fr 1fr;gap:42px;flex-grow:1;min-height:0;position:relative;}
.fech-2grids::before{content:'';position:absolute;left:50%;top:0;bottom:0;width:5px;background:#6E6A53;transform:translateX(-50%);pointer-events:none;border-radius:3px;}
.fech-grid-block{display:flex;flex-direction:column;gap:10px;padding:0 6px;}
.fech-grid-block .fgb-head{font-size:13px;letter-spacing:0.16em;text-transform:uppercase;color:var(--off-white);padding:11px 18px;border-radius:6px;font-weight:600;}
.fech-grid-block .fgb-head.seg{background:linear-gradient(90deg,var(--verde-caqui),var(--verde-medio));border-left:4px solid var(--lime);}
.fech-grid-block .fgb-head.cons{background:linear-gradient(90deg,var(--verde-medio),var(--verde-claro));border-left:4px solid #d4b886;}
.fech-grid-block .fgb-grid{display:grid;grid-template-columns:repeat(3,1fr);grid-template-rows:1fr 1fr;gap:14px;flex-grow:1;}
.fech-grid-block .fgb-card{background:#fff;border:1px solid var(--vc-100);border-radius:10px;padding:22px 20px;display:flex;flex-direction:column;gap:6px;justify-content:center;}
.fech-grid-block .fgb-card .lbl{font-size:13px;letter-spacing:0.18em;text-transform:uppercase;color:var(--verde-claro);font-weight:500;}
.fech-grid-block .fgb-card .val{font-size:50px;font-weight:500;color:var(--verde-caqui);line-height:1;font-variant-numeric:tabular-nums;margin-top:4px;letter-spacing:-0.01em;}
.fech-grid-block .fgb-card .val.bad{color:var(--error);}
.fech-grid-block .fgb-card .val.warn{color:#d18000;}
.fech-grid-block .fgb-card .val.good{color:#2e7d32;}
.fech-grid-block .fgb-card .meta{font-size:13px;color:var(--verde-claro);line-height:1.4;padding-top:6px;}
.fech-grid-block .fgb-card .meta strong{color:var(--verde-caqui);font-weight:600;}
.fech-grid-block .fgb-card .atingimento-row{margin-top:10px;}

/* Slide 5/6 — Fechamento por vertical (2 cols indicators + lista pareto squads) */
.fech-vert-wrap{display:grid;grid-template-columns:1fr 1fr 1.6fr;gap:18px;flex-grow:1;min-height:0;}
/* 2026-06-03 (port deck-normal Img4): fontes fech-col +30% + overflow-y:auto de
   seguranca (PJ2 nao tem o grid 2x4 do deck-normal; rola se nao couber). */
.fech-col{background:#fff;border:1px solid var(--vc-100);border-radius:8px;padding:18px;display:flex;flex-direction:column;gap:12px;min-height:0;overflow-y:auto;}
.fech-col .fc-head{font-size:17px;letter-spacing:0.16em;text-transform:uppercase;color:#fff;padding:9px 14px;border-radius:4px;font-weight:500;}
.fech-col .fc-head.inv{background:var(--verde-caqui);}
.fech-col .fc-head.cred{background:var(--verde-medio);}
.fech-col .fc-row{display:flex;flex-direction:column;gap:2px;padding:7px 0;border-bottom:1px solid var(--vc-50);}
.fech-col .fc-row:last-child{border-bottom:none;}
.fech-col .fc-row .lbl{font-size:13px;letter-spacing:0.12em;text-transform:uppercase;color:var(--verde-claro);}
.fech-col .fc-row .val{font-size:31px;font-weight:500;font-variant-numeric:tabular-nums;line-height:1.05;color:var(--verde-caqui);}
.fech-col .fc-row .val.bad{color:var(--error);}
.fech-col .fc-row .val.warn{color:#d18000;}
.fech-col .fc-row .val.good{color:#2e7d32;}
.fech-col .fc-row .pct{font-size:14px;color:var(--verde-claro);margin-top:2px;}
.fech-col .fc-row .pct strong{color:var(--verde-caqui);font-weight:600;}
.fech-col .fc-row .atingimento-row{margin-top:2px;}
.fech-col .fc-row .atingimento-bar{height:18px;}
.fech-col .fc-row .atingimento-bar .pct-label{font-size:14px;}
/* Ajustes PJ2 2026-05-11 Batch B: barrinha de atingimento (substitui "xx% da meta · meta R$ xxK") */
.atingimento-row{display:grid;grid-template-columns:1fr auto;gap:10px;align-items:center;margin-top:6px;}
.atingimento-bar{position:relative;height:18px;background:var(--vc-50);border-radius:9px;overflow:hidden;border:1px solid var(--vc-100);}
.atingimento-bar .fill{position:absolute;top:0;left:0;height:100%;border-radius:9px;transition:width 0.3s;}
.atingimento-bar .fill.good{background:linear-gradient(90deg,#4caf50,#66bb6a);}
.atingimento-bar .fill.warn{background:linear-gradient(90deg,#ffc107,#ffb300);}
.atingimento-bar .fill.bad{background:linear-gradient(90deg,#e40014,#c62828);}
.atingimento-bar .fill.cinza{background:var(--vc-200);}
.atingimento-bar .pct-label{position:absolute;top:50%;transform:translateY(-50%);font-size:11px;font-weight:700;font-variant-numeric:tabular-nums;line-height:1;z-index:2;letter-spacing:0.02em;color:#fff;text-shadow:0 1px 2px rgba(0,0,0,0.55);left:8px;}
.atingimento-bar .pct-label.inside{color:#fff;text-shadow:0 1px 2px rgba(0,0,0,0.55);left:8px;}
.atingimento-bar .pct-label.outside{color:#fff;text-shadow:0 0 3px rgba(0,0,0,0.85),0 1px 2px rgba(0,0,0,0.7);left:8px;}
.atingimento-meta-side{font-size:14px;color:var(--verde-claro);white-space:nowrap;line-height:1.2;letter-spacing:0.04em;}
.atingimento-meta-side strong{color:var(--verde-caqui);font-weight:600;}
/* Correcao 2026-05-11 (REVIEW 3): NPS Score card CENTRALIZADO em cima + Top 3s embaixo + textos maiores */
.nps-wrap-v2{display:flex;flex-direction:column;gap:20px;flex-grow:1;min-height:0;}
.nps-top{display:flex;justify-content:center;}
.nps-score-card{background:linear-gradient(135deg,var(--verde-caqui),var(--verde-medio));color:var(--off-white);padding:22px 36px;border-radius:12px;display:grid;grid-template-columns:auto 1fr;gap:32px;align-items:center;min-width:760px;max-width:900px;}
.nps-score-card .nps-eyebrow{grid-row:1;grid-column:1;font-size:13px;letter-spacing:0.22em;text-transform:uppercase;color:var(--lime);font-weight:700;align-self:end;}
.nps-score-card .nps-score{grid-row:2;grid-column:1;font-size:88px;font-weight:300;line-height:0.9;color:var(--off-white);font-variant-numeric:tabular-nums;letter-spacing:-0.02em;}
.nps-score-card .nps-formula{grid-row:1/3;grid-column:2;font-size:18px;color:var(--vc-200);line-height:1.45;letter-spacing:0.01em;border-left:1px solid rgba(255,253,239,0.2);padding-left:24px;display:flex;flex-direction:column;justify-content:center;gap:8px;font-weight:500;}
.nps-score-card .nps-formula strong{font-weight:700;color:var(--lime);font-size:30px;letter-spacing:-0.01em;}
.nps-score-card .nps-breakdown{display:grid;grid-template-columns:repeat(3,auto);gap:18px;}
.nps-score-card .nps-row{display:grid;grid-template-columns:14px auto auto;gap:8px;align-items:center;font-size:13px;}
.nps-score-card .nps-dot{width:10px;height:10px;border-radius:50%;}
.nps-score-card .nps-row.pro .nps-dot{background:#4caf50;}
.nps-score-card .nps-row.pas .nps-dot{background:#ffc107;}
.nps-score-card .nps-row.det .nps-dot{background:#e40014;}
.nps-score-card .nps-lbl{color:var(--vc-100);font-size:12px;}
.nps-score-card .nps-val{font-weight:700;color:var(--off-white);font-variant-numeric:tabular-nums;font-size:14px;}
.nps-score-card .nps-val em{font-style:normal;color:var(--vc-200);font-weight:400;font-size:11px;margin-left:2px;}
.nps-score-card .nps-base{grid-row:3;grid-column:1/3;font-size:10px;letter-spacing:0.16em;text-transform:uppercase;color:var(--vc-300);padding-top:12px;border-top:1px solid rgba(255,253,239,0.15);margin-top:6px;}
.nps-cols-v2{display:grid;grid-template-columns:1fr 1fr;gap:24px;flex-grow:1;min-height:0;}
.nps-cols-v2 .nps-col{display:flex;flex-direction:column;gap:12px;}
.nps-cols-v2 .nps-col-head{font-size:14px;letter-spacing:0.18em;text-transform:uppercase;color:var(--off-white);padding:13px 18px;border-radius:6px;font-weight:700;}
.nps-cols-v2 .nps-col-head.pos{background:linear-gradient(90deg,#2e7d32,#4caf50);border-left:4px solid var(--lime);}
.nps-cols-v2 .nps-col-head.neg{background:linear-gradient(90deg,#b8000f,#e40014);border-left:4px solid #ffd1d4;}
.nps-cols-v2 .nps-card{background:#fff;border:1px solid var(--vc-100);border-radius:8px;padding:16px 20px;display:grid;grid-template-columns:42px 1fr;gap:16px;align-items:flex-start;}
.nps-cols-v2 .nps-card.nps-pos{border-left:4px solid #4caf50;}
.nps-cols-v2 .nps-card.nps-neg{border-left:4px solid #e40014;}
.nps-cols-v2 .nps-card-num{font-size:30px;font-weight:300;line-height:1;color:var(--verde-claro);font-variant-numeric:tabular-nums;}
.nps-cols-v2 .nps-card-body{display:flex;flex-direction:column;gap:8px;}
.nps-cols-v2 .nps-card-tit{font-size:16px;font-weight:700;color:var(--verde-caqui);line-height:1.25;letter-spacing:-0.005em;}
.nps-cols-v2 .nps-card-sint{font-size:13px;color:var(--verde-medio);line-height:1.5;}
.nps-cols-v2 .nps-card-cit{font-size:12px;color:var(--verde-claro);line-height:1.5;font-style:italic;border-top:1px dashed var(--vc-100);padding-top:8px;margin-top:2px;}
/* Correcao 2026-05-11 (REVIEW 3 + 4): Conclusao com FUNDO ESCURO verde-caqui */
.conc-slide{background:var(--verde-caqui);color:var(--off-white);}
.conc-slide .slide-head{background:transparent;color:var(--off-white);}
.conc-slide .slide-head .h-eyebrow{color:var(--lime);}
.conc-slide .slide-head .h-title{color:var(--off-white);}
.conc-slide .slide-foot{background:transparent;color:var(--vc-200);}
.conc-slide .slide-foot .f-meta,.conc-slide .slide-foot .f-num{color:var(--vc-200);}
/* 2026-05-27: sync N3 — headline +100% (16→32) e line-height 1.5→1.4. */
.conc-headline{font-size:32px;line-height:1.4;color:var(--vc-200);margin-bottom:32px;padding:0;background:transparent;border:none;letter-spacing:0.01em;}
.conc-headline .ch-eyebrow{display:none;}
.conc-headline strong{font-weight:700;color:var(--lime);}
.veloc-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:28px;flex-grow:1;min-height:0;}
.veloc{background:transparent;border:none;border-top:1px solid var(--lime);border-radius:0;padding:24px 8px 16px;display:flex;flex-direction:column;gap:14px;justify-content:flex-start;position:relative;overflow:hidden;}
.veloc-num{font-size:96px;font-weight:200;line-height:0.85;color:var(--lime);font-variant-numeric:tabular-nums;letter-spacing:-0.03em;margin-bottom:8px;}
.veloc-head{margin-bottom:0;border:none;padding-bottom:0;}
/* 2026-05-27: sync N3 — veloc-lbl +20% (26→31); veloc-sub +25% (12→15). */
.veloc-lbl{font-size:31px;font-weight:500;color:var(--off-white);letter-spacing:-0.01em;line-height:1.15;}
.veloc-sub{font-size:15px;color:var(--vc-200);letter-spacing:0.04em;margin-top:6px;}
.veloc-gauge-wrap{position:relative;display:flex;justify-content:center;align-items:center;padding-top:20px;flex-grow:1;}
.veloc-gauge-wrap .gauge-svg{width:100%;max-width:340px;height:auto;}
/* 2026-05-27: sync N3 — % sobe (bottom 6→80) p/ encostar na curva inferior do gauge. */
.veloc-pct{position:absolute;bottom:80px;left:50%;transform:translateX(-50%);font-size:64px;font-weight:300;line-height:1;font-variant-numeric:tabular-nums;letter-spacing:-0.03em;}
.veloc-pct .pct-mark{font-size:30px;font-weight:400;margin-left:2px;}
/* 2026-05-27: sync N3 — tira sobe (padding-top 18→8; margin-top 8→0). */
.veloc-vals{display:grid;grid-template-columns:1fr 1fr;gap:8px;padding-top:8px;margin-top:0;border-top:1px solid rgba(255,253,239,0.15);}
.veloc-side{display:flex;flex-direction:column;gap:4px;}
.veloc-side.veloc-meta{text-align:right;}
/* 2026-05-27: sync N3 — tira inferior +20% (vside-lbl 11→13; vside-val 24→29; veloc-proj 12→14). */
.vside-lbl{font-size:13px;letter-spacing:0.18em;text-transform:uppercase;color:var(--vc-200);font-weight:600;}
.vside-val{font-size:29px;font-weight:500;color:var(--off-white);font-variant-numeric:tabular-nums;line-height:1.1;}
.veloc-proj{text-align:left;font-size:14px;color:var(--vc-200);letter-spacing:0.04em;padding-top:6px;}
.veloc-proj strong{color:var(--lime);font-weight:700;}
/* Ajustes PJ2 2026-05-11 Batch F #23: disclaimer reconciliação Card vs Pareto */
.fech-vert-disclaimer{margin-top:14px;padding:8px 14px;background:var(--vc-50);border-left:3px solid var(--vc-200);border-radius:3px;font-size:10px;line-height:1.45;color:var(--verde-claro);letter-spacing:0.02em;}
.fech-vert-disclaimer strong{color:var(--verde-medio);font-weight:700;}

/* Pareto Squad Listing (assessor a assessor) */
/* Correcao 2026-05-11 #7+#8: fontes Pareto aumentadas (nomes assessores + numeros barras),
   altura limitada para garantir scrollbar interno funcionando */
.pareto-card{background:#fff;border:1px solid var(--vc-100);border-radius:8px;overflow:hidden;display:flex;flex-direction:column;min-height:0;max-height:100%;}
.pareto-card .pch{background:var(--verde-medio);color:var(--off-white);padding:10px 14px;font-size:12px;letter-spacing:0.14em;text-transform:uppercase;font-weight:500;display:grid;grid-template-columns:1.6fr 0.9fr 0.9fr;gap:6px;flex-shrink:0;}
.pareto-card .pch > div{padding:0;}
.pareto-card .pch > div:not(:first-child){text-align:center;border-left:1px solid rgba(255,253,239,0.12);padding-left:6px;}
.pareto-card .pcb{flex:1 1 0;overflow-y:auto;display:flex;flex-direction:column;min-height:0;}
/* Custom scrollbar visível mas discreto */
.pareto-card .pcb::-webkit-scrollbar{width:8px;}
.pareto-card .pcb::-webkit-scrollbar-track{background:var(--vc-50);}
.pareto-card .pcb::-webkit-scrollbar-thumb{background:var(--vc-200);border-radius:4px;}
.pareto-card .pcb::-webkit-scrollbar-thumb:hover{background:var(--verde-claro);}
.psq-head{padding:5px 14px;font-size:11px;font-weight:600;letter-spacing:0.18em;text-transform:uppercase;flex-shrink:0;}
.psq-head.inv{background:var(--lime);color:var(--verde-caqui);}
.psq-head.cred{background:#c4ce5e;color:var(--verde-caqui);}
.psq-head.outros{background:var(--vc-100);color:var(--verde-caqui);}
.psq-row{display:grid;grid-template-columns:1.6fr 0.9fr 0.9fr;gap:6px;align-items:center;padding:5px 14px;border-bottom:1px solid var(--vc-50);font-size:13px;min-height:26px;flex-shrink:0;}
.psq-row .nm{color:var(--verde-caqui);line-height:1.2;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-weight:500;}
.psq-row .nm.zero{color:var(--vc-300);font-weight:400;}
.psq-row .bar-cell{display:flex;align-items:center;border-left:1px solid var(--vc-100);padding-left:6px;}
.psq-row .mini{background:#f0f0ee;border-radius:3px;height:16px;flex-grow:1;overflow:hidden;display:flex;}
.psq-row .mini .fb{height:100%;padding:0 6px;font-size:11px;font-weight:700;color:#fff;display:flex;align-items:center;white-space:nowrap;}
.fb-good{background:#4caf50;}
.fb-lime{background:var(--lime);color:var(--verde-caqui)!important;}
.fb-mute{background:var(--vc-200);color:var(--verde-caqui)!important;}
.fb-bad{background:var(--error);}

/* Closing */
.closing{background:var(--verde-caqui);color:var(--off-white);padding:0;}
.closing-inner{flex-grow:1;display:flex;flex-direction:column;padding:64px 96px 56px;}
.closing .head-row{display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:36px;}
.closing h2{font-size:64px;font-weight:300;line-height:1.05;color:var(--off-white);max-width:18ch;}
.closing h2 em{color:var(--lime);font-style:normal;}
.closing .next-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:24px;flex-grow:1;}
.next-card{background:rgba(255,253,239,0.04);border:1px solid rgba(255,253,239,0.12);border-top:3px solid var(--lime);padding:32px 28px;display:flex;flex-direction:column;gap:18px;}
.next-card .nc-num{font-size:64px;font-weight:200;line-height:1;color:var(--lime);}
.next-card .nc-title{font-size:24px;line-height:1.3;color:var(--off-white);font-weight:500;min-height:72px;}
.next-card .nc-meta{display:flex;flex-direction:column;gap:14px;border-top:1px solid rgba(255,253,239,0.12);padding-top:18px;}
.next-card .nc-meta .k{font-size:12px;letter-spacing:0.2em;text-transform:uppercase;color:var(--verde-claro);margin-bottom:6px;}
.next-card .nc-meta .v{font-size:16px;line-height:1.5;color:var(--off-white);}
.closing .closing-foot{display:flex;justify-content:space-between;font-size:13px;letter-spacing:0.16em;text-transform:uppercase;color:var(--verde-claro);padding-top:24px;border-top:1px solid rgba(255,253,239,0.12);margin-top:20px;}
.closing .closing-foot strong{color:var(--off-white);}

/* Matriz dense */
.matrix{flex-grow:1;display:flex;flex-direction:column;gap:12px;min-height:0;}
/* S1-A2 iter 6 (2026-05-16): overflow: hidden estava cortando 4 indicadores PPI
   no slide PJ2 (mostrava 7 de 11). Trocar para overflow-y: auto (diretriz
   transversal scroll bar — nenhuma info se perde). Padding/font reduzidos para
   .ultra-dense level para caber todos sem scroll quando possivel. */
.matrix-grid{background:#fff;border:1px solid var(--vc-100);border-radius:8px;overflow-y:auto;flex-grow:1;display:flex;flex-direction:column;min-height:0;}
.mx-row{display:grid;grid-template-columns:1.6fr 1fr 1fr 1fr 1.1fr;}
/* 2026-05-27: sync N3 — sticky header pra cabecalho da matriz nao sumir no scroll. */
.mx-row.head{position:sticky;top:0;z-index:2;}
.mx-row.head > div{padding:12px 16px;font-size:12px;letter-spacing:0.14em;text-transform:uppercase;}
.mx-row.head .col-ind{background:var(--off-white);color:var(--verde-caqui);font-weight:500;}
.mx-row.head .col-c{color:var(--off-white);text-align:center;}
.mx-row.head .col-c.c-outros{background:#353530;}
.mx-row.head .col-c.c-cred{background:#5a5945;}
.mx-row.head .col-c.c-inv{background:var(--verde-caqui);}
.mx-row.head .col-c.c-total{background:#6c6b54;font-weight:500;}
.mx-section{padding:6px 16px;font-size:11px;font-weight:500;letter-spacing:0.18em;text-transform:uppercase;}
.mx-section.kpi{background:var(--lime);color:var(--verde-caqui);}
.mx-section.ppi{background:var(--verde-claro);color:#fff;}
/* S1-A2 iter 6 (2026-05-16): PJ2 tem 11 indicadores na matriz (3 KPI + 8 PPI),
   mesma contagem que CON N3 ultra-dense. Aplicar padding/font equivalentes ao
   .matrix-grid.ultra-dense do default para caber 11 rows no slide PJ2 sem scroll. */
.mx-row.data{border-bottom:1px solid #e0e0de;}
.mx-row.data:last-child{border-bottom:none;}
.mx-row.data > div{padding:12px 17px;min-height:53px;box-sizing:border-box;display:flex;align-items:center;}
/* col-ind sync com .ultra-dense do default (16px). */
.mx-row.data .col-ind{font-size:16px;color:var(--verde-caqui);display:flex;align-items:center;}
.mx-row.data .cell{display:flex;align-items:center;justify-content:center;font-variant-numeric:tabular-nums;border-left:1px solid #e0e0de;min-height:53px;}
/* Cell layout HORIZONTAL via grid. Fonts ultra-dense + +12,5%/+5% iter:
   num 15px; meta 11px; sub 9px (sync default ultra-dense). */
.mx-row.data .cell .v{display:grid;grid-template-columns:auto auto;align-items:center;column-gap:10px;row-gap:2px;}
.mx-row.data .cell .num{grid-row:1 / 3;grid-column:1;font-size:15px;font-weight:600;color:var(--verde-caqui);line-height:1.15;align-self:center;}
.mx-row.data .cell .meta{grid-column:2;grid-row:1;font-size:11px;color:var(--verde-claro);letter-spacing:0.04em;align-self:end;}
.mx-row.data .cell .sub{grid-column:2;grid-row:2;font-size:9px;color:var(--vc-300);letter-spacing:0.04em;align-self:start;}
.mx-row.data .cell.bad .num{color:var(--error);}
.mx-row.data .cell.warn .num{color:#d18000;}
.mx-row.data .cell.good .num{color:#2e7d32;}
.mx-row.data .cell.mute .num{color:var(--vc-300);}

/* Direto */
.dash{display:grid;grid-template-columns:1.4fr 1fr;gap:20px;flex-grow:1;min-height:0;}
.dash-table{background:#fff;border:1px solid var(--vc-100);border-radius:8px;overflow:hidden;display:flex;flex-direction:column;}
.dt-head{background:var(--verde-medio);color:var(--off-white);display:grid;grid-template-columns:2fr 1fr 1fr 1.4fr;font-size:12px;letter-spacing:0.14em;text-transform:uppercase;font-weight:500;}
.dt-head > div{padding:12px 14px;}
.dt-head > div:not(:first-child){text-align:center;}
.dt-section{padding:6px 14px;font-size:11px;font-weight:500;letter-spacing:0.18em;text-transform:uppercase;}
.dt-section.kpi{background:var(--lime);color:var(--verde-caqui);}
.dt-section.ppi{background:var(--verde-claro);color:#fff;}
.dt-row{display:grid;grid-template-columns:2fr 1fr 1fr 1.4fr;align-items:center;border-bottom:1px solid var(--vc-50);font-size:13px;}
.dt-row > div{padding:7px 14px;}
.dt-row > div:not(:first-child){text-align:center;font-variant-numeric:tabular-nums;}
.dt-row .ind{color:var(--verde-caqui);}
.dt-row .real{font-weight:600;color:var(--verde-caqui);}
.dt-row .real.bad{color:var(--error);}
.dt-row .real.warn{color:#d18000;}
.dt-row .real.good{color:#2e7d32;}
.dt-row .real.mute{color:var(--vc-300);}
.dt-row .desvio.bad{color:var(--error);font-weight:600;}
.dt-row .desvio.warn{color:#d18000;font-weight:600;}
.dt-row .desvio.good{color:#2e7d32;font-weight:600;}
.dt-row .desvio .pct{font-size:10px;color:var(--vc-400);display:block;margin-top:2px;}

.risks-card{background:#fff;border:1px solid var(--vc-100);border-radius:8px;overflow:hidden;display:flex;flex-direction:column;}
.risks-card .rh{background:var(--error);color:#fff;padding:14px 20px;font-size:13px;letter-spacing:0.14em;text-transform:uppercase;font-weight:500;}
.risks-card .rb{padding:16px;display:flex;flex-direction:column;gap:10px;flex-grow:1;}
.risk-item{background:var(--vc-50);border-left:3px solid var(--error);padding:12px 14px;font-size:18px;line-height:1.45;color:var(--verde-caqui);}
.risk-item strong{font-weight:600;}
.risk-item .ri-meta{font-size:16px;color:var(--verde-claro);margin-top:5px;font-style:italic;}

/* Análise por canal slide 14/17 — listing por assessor + cards laterais */
.analise-grid{display:grid;grid-template-columns:1.6fr 1fr;gap:20px;flex-grow:1;min-height:0;}
.canal-card{background:#fff;border:1px solid var(--vc-100);border-radius:8px;overflow:hidden;display:flex;flex-direction:column;}
/* Correcao 2026-05-12 (REVIEW): fontes maiores no slide Analise por Canal (legibilidade) */
/* S1-A2 iter 8 (2026-05-17): REVERT iter 7 — spec PJ2 original (compacto)
   e o default que sera atualizado para alinhar. PJ2 fica como referencia. */
.canal-head{background:var(--verde-medio);color:var(--off-white);display:grid;grid-template-columns:180px repeat(4,1fr);font-size:13px;letter-spacing:0.14em;text-transform:uppercase;font-weight:600;}
.canal-head > div{padding:13px 12px;}
.canal-head > div:not(:first-child){text-align:center;border-left:1px solid rgba(255,253,239,0.12);}
.canal-body{flex-grow:1;overflow-y:auto;}
.canal-body::-webkit-scrollbar{width:8px;}
.canal-body::-webkit-scrollbar-track{background:#e0e0de;}
.canal-body::-webkit-scrollbar-thumb{background:var(--vc-200);border-radius:4px;}
.canal-body::-webkit-scrollbar-thumb:hover{background:var(--verde-claro);}
.canal-row{display:grid;grid-template-columns:180px repeat(4,1fr);align-items:center;padding:7px 0;border-bottom:1px solid #e0e0de;font-size:13px;min-height:32px;}
.canal-row .nm{color:var(--verde-caqui);padding:0 14px;line-height:1.2;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-weight:500;}
.canal-row .nm.zero{color:var(--vc-300);font-weight:400;}
.canal-row .cn{padding:4px 8px;border-left:1px solid #e0e0de;}
.canal-row .cn .mini{background:#f0f0ee;border-radius:3px;height:18px;overflow:hidden;display:flex;}
.canal-row .cn .mini .fb{height:100%;padding:0 8px;font-size:12px;font-weight:700;color:#fff;display:flex;align-items:center;white-space:nowrap;}

.side-stats{display:flex;flex-direction:column;gap:12px;min-height:0;}
.stat-card{background:#fff;border:1px solid var(--vc-100);border-radius:8px;padding:14px 16px;}
.stat-card .sh{font-size:11px;letter-spacing:0.18em;text-transform:uppercase;color:var(--verde-claro);margin-bottom:6px;}
.stat-card .sv{font-size:30px;font-weight:600;color:var(--verde-caqui);line-height:1;font-variant-numeric:tabular-nums;}
.stat-card .sv.bad{color:var(--error);}
.stat-card .sv.warn{color:#d18000;}
.stat-card .sv.good{color:#2e7d32;}
.stat-card .sd{font-size:11px;color:var(--verde-claro);margin-top:6px;line-height:1.4;}
.stat-card.list{flex-grow:1;overflow:hidden;display:flex;flex-direction:column;}
.stat-card.list .deal-list{list-style:none;display:flex;flex-direction:column;gap:0;margin-top:6px;flex-grow:1;overflow-y:auto;}
.stat-card.list .deal-list li{display:grid;grid-template-columns:1fr auto auto;gap:8px;padding:7px 0;border-top:1px solid var(--vc-50);font-size:13px;align-items:baseline;}
.stat-card.list .deal-list li:first-child{border-top:none;}
.stat-card.list .deal-list .dl-name{color:var(--verde-caqui);font-weight:500;}
.stat-card.list .deal-list .dl-qty{font-weight:700;color:var(--error);font-variant-numeric:tabular-nums;font-size:15px;}
.stat-card.list .deal-list .dl-dias{font-size:11px;color:var(--verde-claro);font-variant-numeric:tabular-nums;}

/* Pipeline (slide 15/18) — funil canônico + 6 KPI tiles topo */
.kpi-row{display:grid;grid-template-columns:repeat(6,1fr);gap:10px;}
.kpi-tile{background:var(--vc-50);border-radius:6px;padding:14px 10px;display:flex;flex-direction:column;align-items:center;gap:4px;}
/* 2026-06-03 (port deck-normal #8): +30% tipografia Pipeline (kpi tiles + projecao). */
.kpi-tile .v{font-size:31px;font-weight:600;color:var(--verde-caqui);font-variant-numeric:tabular-nums;}
.kpi-tile .v.bad{color:var(--error);} .kpi-tile .v.good{color:#2e7d32;}
.kpi-tile .v.warn{color:#d18000;} .kpi-tile .v.mute{color:var(--vc-300);}
.kpi-tile .l{font-size:13px;letter-spacing:0.1em;text-transform:uppercase;color:var(--verde-claro);text-align:center;line-height:1.2;}
.pipe-wrap{display:grid;grid-template-columns:1.3fr 1fr;gap:18px;flex-grow:1;min-height:0;}
.funnel-card{background:#fff;border:1px solid var(--vc-100);border-radius:8px;padding:20px 24px;display:flex;flex-direction:column;gap:8px;}
.funnel-card .fnh{display:flex;align-items:center;justify-content:space-between;font-size:11px;letter-spacing:0.14em;text-transform:uppercase;color:var(--verde-claro);padding-bottom:6px;}
.funnel-svg{width:100%;flex-grow:1;}
.gargalo-line{margin-top:8px;font-size:13px;color:var(--verde-caqui);padding-top:8px;border-top:1px dashed var(--vc-100);}
.gargalo-line strong{color:var(--error);font-weight:600;}

.pipe-side{display:flex;flex-direction:column;gap:12px;min-height:0;}
/* S1-A2 (2026-05-16): scroll bar dentro do card quando conteudo excede altura
   disponivel (sync diretriz transversal do default — nenhuma info se perde). */
.pipe-card-side{background:#fff;border:1px solid var(--vc-100);border-radius:8px;overflow-y:auto;min-height:0;}
.pipe-card-side .pcs-head{padding:9px 16px;font-size:12px;letter-spacing:0.14em;text-transform:uppercase;color:#fff;font-weight:500;}
.pipe-card-side .pcs-head.dest{background:#4f7c4d;}
.pipe-card-side .pcs-head.estag{background:var(--error);}
.pipe-card-side .pcs-head.proj{background:var(--verde-medio);}
.pipe-card-side .pcs-body{padding:12px 16px;font-size:13px;color:var(--verde-caqui);display:flex;flex-direction:column;gap:5px;}
.pipe-card-side .pcs-body strong{font-weight:600;}

.proj-block{padding:10px 16px;display:flex;flex-direction:column;gap:6px;}
.proj-section-title{font-size:14px;letter-spacing:0.16em;text-transform:uppercase;color:var(--verde-claro);font-weight:500;padding-bottom:3px;}
.proj-row{display:grid;grid-template-columns:104px 1fr 96px;gap:8px;align-items:center;font-size:14px;}
.proj-row .lbl{color:var(--verde-claro);text-align:right;line-height:1.2;font-variant-numeric:tabular-nums;}
.proj-row .lbl strong{display:block;font-weight:700;color:var(--verde-caqui);font-size:16px;letter-spacing:0.05em;}
.proj-row .track{background:var(--vc-50);border-radius:3px;height:14px;overflow:hidden;}
.proj-row .track .fill{height:100%;}
.proj-row .v{font-size:14px;color:var(--verde-claro);text-align:right;font-variant-numeric:tabular-nums;line-height:1.2;}
.proj-row .v strong{display:block;color:var(--verde-caqui);font-weight:700;font-size:16px;}

/* Consolidado tiles + bars */
.consol-tiles{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;}
.consol-tile{background:var(--vc-50);border-radius:6px;padding:18px 12px;display:flex;flex-direction:column;align-items:center;gap:4px;}
.consol-tile .v{font-size:32px;font-weight:600;color:var(--verde-caqui);font-variant-numeric:tabular-nums;line-height:1;}
.consol-tile .v.bad{color:var(--error);} .consol-tile .v.good{color:#2e7d32;}
.consol-tile .v.warn{color:#d18000;} .consol-tile .v.mute{color:var(--vc-300);}
.consol-tile .l{font-size:11px;letter-spacing:0.1em;text-transform:uppercase;color:var(--verde-claro);text-align:center;line-height:1.2;margin-top:4px;}

.bar-row{display:grid;grid-template-columns:140px 1fr 110px;gap:12px;align-items:center;font-size:13px;padding:6px 0;}
.bar-row .lbl-l{color:var(--verde-caqui);}
.bar-row .track{background:#f0f0eb;height:22px;border-radius:3px;overflow:hidden;}
.bar-row .track .fill{height:100%;color:#fff;font-size:11px;line-height:22px;padding-right:6px;text-align:right;font-weight:600;}
.bar-row .vt{text-align:right;font-size:12px;line-height:1.3;font-variant-numeric:tabular-nums;}

/* ══════════════════════════════════════════════════════════════════
   2026-06-11 · +10% de tipografia nos SLIDES DE ESPECIALISTA (PJ2)
   Detalhe por vertical do Bloco II/III: Matriz · Análise por Canal ·
   Pipeline (Seguros + Consórcios). Escopado em .esp-slide para nao
   tocar capa/agenda/recap/fechamento/consolidado/conclusao. !important
   pois ha font-size inline; o funil (SVG render_funnel_canonical) e
   ajustado direto no .py (hierarquia 9–18px). Espelha o bloco do
   ritual.tmpl.html (deck N3).
   ══════════════════════════════════════════════════════════════════ */
.esp-slide .slide-head .h-title   { font-size:35px !important; }
.esp-slide .slide-head .h-eyebrow { font-size:14px !important; }
.esp-slide .avatar                { font-size:24px !important; }
.esp-slide .slide-foot            { font-size:14px !important; }
/* Matriz */
/* 2026-06-12: matriz −5% (espelho da Img 1 do N3) sobre o +10% anterior. */
.esp-slide .mx-row.head > div     { font-size:12.5px !important; }
.esp-slide .mx-section            { font-size:11.5px !important; }
.esp-slide .mx-row.data .col-ind  { font-size:17px !important; }
.esp-slide .mx-row.data .cell .num  { font-size:16px !important; }
.esp-slide .mx-row.data .cell .meta { font-size:11.5px !important; }
.esp-slide .mx-row.data .cell .sub  { font-size:9.5px !important; }
/* Análise por Canal */
.esp-slide .canal-head            { font-size:14px !important; }
.esp-slide .canal-row             { font-size:14px !important; }
.esp-slide .canal-row .cn .mini .fb { font-size:13px !important; }
.esp-slide .stat-card .sh         { font-size:12px !important; }
.esp-slide .stat-card .sv         { font-size:33px !important; }
.esp-slide .stat-card .sd         { font-size:12px !important; }
.esp-slide .stat-card.list .deal-list li      { font-size:14px !important; }
.esp-slide .stat-card.list .deal-list .dl-qty { font-size:17px !important; }
.esp-slide .stat-card.list .deal-list .dl-dias{ font-size:12px !important; }
/* Pipeline: KPI tiles + funil header + projecao + riscos */
.esp-slide .kpi-tile .v           { font-size:34px !important; }
.esp-slide .kpi-tile .l           { font-size:14px !important; }
.esp-slide .funnel-card .fnh      { font-size:12px !important; }
.esp-slide .gargalo-line          { font-size:14px !important; }
.esp-slide .pipe-card-side .pcs-head { font-size:13px !important; }
.esp-slide .pipe-card-side .pcs-body { font-size:14px !important; }
.esp-slide .proj-section-title    { font-size:15px !important; }
.esp-slide .proj-row              { font-size:15px !important; }
.esp-slide .proj-row .lbl strong  { font-size:18px !important; }
.esp-slide .proj-row .v           { font-size:15px !important; }
.esp-slide .proj-row .v strong    { font-size:18px !important; }
.esp-slide .risks-card .rh        { font-size:14px !important; }
.esp-slide .risk-item             { font-size:18.5px !important; } /* 2026-06-12: −7,5% (Img 2) sobre 20px */
/* .ri-meta nao e mais renderizado (subtexto nao-negrito removido — espelho do N3) */
"""


# ─── Slide head/foot ────────────────────────────────────────
def slide_head(eyebrow, title, logo, avatar=None):
    av = f'<div class="avatar">{esc(avatar)}</div><div class="h-divider"></div>' if avatar else ''
    return f'''<div class="slide-head"><div class="h-left">{av}<div>
<div class="h-eyebrow">{esc(eyebrow)}</div><div class="h-title">{esc(title)}</div></div></div>
<img class="h-logo" src="data:image/png;base64,{logo}" alt="M7"></div>'''

def slide_foot(meta, num):
    return f'''<div class="slide-foot"><div class="f-meta">{esc(meta)}<span class="dot"></span>{PJ2_VERTICAIS_DISPLAY} · Joel Freitas</div><div class="f-num">{num:02d}</div></div>'''


def _ind_status(ind): return get(ind, "status", "cor") or "cinza"


# ─── SLIDE 1 — Capa ──────────────────────────────────────────
def render_capa(card, ciclo, logo):
    coord = get(card, "metadata", "owner") or "Joel Freitas"
    # S1-A1#2 (2026-05-15): Badge "· fechamento DD/MM/YYYY" so aparece em modos
    # que olham para tras (fechamento + combinado). Modo "atual" esconde o badge.
    # Default PJ2 N2 mensal = "combinado", entao badge tipicamente visivel.
    _fechamento_suffix = (
        f" · fechamento <strong>{PJ2_DATA_FECHAMENTO_DISPLAY}</strong>"
        if PJ2_EFFECTIVE_MODO in ("fechamento", "combinado") else ""
    )
    return f'''<section class="cover"><div class="grid-bg"></div>
<div class="cover-inner">
<div><div class="cover-eyebrow"><div class="bar"></div><span>Ritual de Gestão · N2</span></div>
<h1>Resultados <em>{PJ2_VERTICAIS_DISPLAY}</em><br>{PJ2_CICLO_ATUAL}</h1></div>
<div class="cover-meta">
<div class="meta-block"><div class="k">Ciclo</div><div class="v">{esc(ciclo)}{_fechamento_suffix}</div></div>
<div class="meta-block"><div class="k">Vertical · Nível</div><div class="v">{PJ2_VERTICAIS_DISPLAY} · <strong>N2</strong></div></div>
<div class="meta-block"><div class="k">Canais</div><div class="v">Investimentos · Crédito · Outros M7</div></div>
<div class="meta-block"><div class="k">Coordenador</div><div class="v">{esc(coord)}</div></div>
</div></div>
<div class="cover-foot"><img class="logo" src="data:image/png;base64,{logo}" alt="M7"><div class="stamp"><strong>M7 Investimentos</strong> · Ritual de Gestão</div></div>
</section>'''


# ─── SLIDE 2 — Agenda ────────────────────────────────────────
def render_agenda(logo):
    # Correcao 2026-05-12 (REVIEW 8): Agenda com 6 entries detalhados
    # NOTA p/ plugin Step 8: "Indicadores em Alerta {mês}" deve generalizar — usar mes anterior do fechamento
    rows = '''<div class="tl-row"><div><div class="tl-num">01</div><div class="tl-title">Recap da <em>última N2</em></div><div class="tl-sub">7 frentes da ata Alinhamento Comercial 04/05</div></div><div class="tl-time">5 min</div></div>
<div class="tl-row feature"><div><div class="tl-num">02</div><div class="tl-title"><em>Fechamento</em> mês passado · {PJ2_VERTICAIS_DISPLAY}</div><div class="tl-sub">Visão geral + detalhado por vertical (Seguros + Consórcios)</div></div><div class="tl-time">12 min</div></div>
<div class="tl-row"><div><div class="tl-num">03</div><div class="tl-title">Indicadores em Alerta · <em>Abril</em></div><div class="tl-sub">Causa-raiz dos lead indicators em vermelho</div></div><div class="tl-time">8 min</div></div>
<div class="tl-row feature"><div><div class="tl-num">04</div><div class="tl-title"><em>Mês até agora</em> · Seguros</div><div class="tl-sub">Matriz + Análise por Canal + Pipeline</div></div><div class="tl-time">15 min</div></div>
<div class="tl-row feature"><div><div class="tl-num">05</div><div class="tl-title"><em>Mês até agora</em> · Consórcios</div><div class="tl-sub">NPS + Matriz + Análise por Canal + Pipeline</div></div><div class="tl-time">20 min</div></div>
<div class="tl-row"><div><div class="tl-num">06</div><div class="tl-title">Conclusão · Projeção M0</div><div class="tl-sub">3 velocímetros — Seguros · Consórcios · Total Receita</div></div><div class="tl-time">10 min</div></div>'''
    return f'''<section>{slide_head("Ritual N2 {PJ2_VERTICAIS_DISPLAY} · {PJ2_CICLO_ATUAL}", "Agenda", logo)}
<div class="slide-body"><div class="agenda">
<div class="agenda-aside"><div class="ag-eyebrow">Estrutura do ritual</div>
<div style="font-size:42px;line-height:1.1;color:var(--verde-caqui);font-weight:300;max-width:12ch;">2 canais · 1 coordenação · 70 min</div></div>
<div class="agenda-tl">{rows}</div></div></div>
{slide_foot("Agenda · Bloco 00 → V", 2)}</section>'''


def render_recap_ultima_n2(logo, num=3):
    """Slide dedicado: 'Pontos discutidos na última N2 · 04/05'.

    Correcao 2026-05-11 #1 (REVIEW USUARIO): antes era row dentro da Agenda.
    Agora vira slide separado, posicionado DEPOIS da Agenda. 7 pontos extraídos
    da ata Alinhamento Comercial 04/05/2026 secao 3 (Pontos Críticos Discutidos):
    3.1, 3.3, 3.4, 3.5, 3.7, 3.8, 3.9.
    """
    recap_points = [
        ("Apólices (urgente)", "Consolidar banco de apólices Seg via mutirão sábado (Joel + Emmanuel + Bruno) para habilitar previsibilidade de renovação"),
        ("Cotação Seg", "Produzir relatório de negócios perdidos via carta de nomeação + padrão de causa raiz (Joel + Emmanuel)"),
        ("Produto p/ nichos", "Definir ICP por produto e desenhar oferta para nichos específicos (médicos / dentistas — Universo / Uniodonto)"),
        ("Treinamento Seg", "Apresentar proposta consistente (cultura + processo + materiais) para retomar cadência semanal — Joel apresenta"),
        ("Comissões renegociadas", "Priorizar comercialização das seguradoras com comissão renegociada (Polo Seguro · MAG · Tokio Marine) para capturar valor das novas condições"),
        ("Estrutura WING / M7", "Discutir estrutura dedicada com Felipe Costa + Gonzalo para endereçar sobrecarga após WING absorver escopo M7 sem ampliar quadro"),
        ("Volume vs Receita", "Acompanhar Seg + Cons por volume operado (receita complementar) — receita atual sustentada por stock + reativações, não venda nova"),
    ]
    # Correcao 2026-05-11 (REVIEW 3): design image 4 — card unico com header dark
    # arredondado + lista limpa de 7 rows + footer padrao
    rows_html = "".join(
        f'''<div class="recap2-row">
<div class="recap2-bar"></div>
<div class="recap2-num">{i+1:02d}</div>
<div class="recap2-lbl">{esc(lbl)}</div>
<div class="recap2-txt">{esc(txt)}</div>
</div>'''
        for i, (lbl, txt) in enumerate(recap_points)
    )
    return f'''<section class="recap2-slide">{slide_head("Bloco 00 · Recap última N2", "Pontos discutidos na última N2 · 04/05", logo)}
<div class="slide-body">
<div class="recap2-body">
{rows_html}
</div>
</div>
{slide_foot("Bloco 00 · Recap última N2", num)}</section>'''


# ─── SLIDE 3/8 — Subcapa ────────────────────────────────────
def render_subcapa(num, eyebrow, h1m, h1e, descr, ciclo, logo, foot_label):
    return f'''<section class="cover"><div class="grid-bg"></div>
<div class="cover-inner">
<div><div class="cover-eyebrow"><div class="bar"></div><span>{esc(eyebrow)}</span></div>
<h1>{esc(h1m)} <em>{esc(h1e)}</em></h1></div>
<div class="cover-meta">
<div class="meta-block"><div class="k">Bloco</div><div class="v"><strong>{esc(eyebrow)}</strong></div></div>
<div class="meta-block"><div class="k">Foco</div><div class="v">{esc(descr)}</div></div>
<div class="meta-block"><div class="k">Ciclo</div><div class="v">{esc(ciclo)}</div></div>
</div></div>
<div class="cover-foot"><img class="logo" src="data:image/png;base64,{logo}" alt="M7"><div class="stamp"><strong>{esc(foot_label)}</strong> · slide {num:02d}</div></div>
</section>'''


# ─── Helper: barrinha de atingimento (Ajustes PJ2 2026-05-11 Batch B #4) ──────
def _atingimento_bar(pct, meta_str, cor, direction="maior_melhor"):
    """Renderiza barra de atingimento substituindo "xx% da meta · meta R$ xxK".

    Spec Bruno 11/05:
      - Barra de 0-100% abaixo do valor realizado
      - Cor da barra segue intervalos de semáforos
      - "xx%" DENTRO da barra (seguindo preenchimento)
      - "meta R$ xxK" FORA da barra à direita

    Args:
        pct: percentual de atingimento (0-200+). None → barra cinza vazia + label "sem dado".
        meta_str: string formatada da meta (ex: "R$ 100K") para mostrar à direita.
        cor: "verde" | "amarelo" | "vermelho" | "cinza" (ja resolvido pelo chamador).
        direction: "maior_melhor" (default) ou "menor_melhor" — afeta cap visual.

    Returns: HTML do bloco grid com barra + meta à direita.
    """
    cls = status_class(cor)
    if pct is None:
        return f'''<div class="atingimento-row"><div class="atingimento-bar"><div class="fill cinza" style="width:0%;"></div></div><div class="atingimento-meta-side">{meta_str}</div></div>'''
    # Cap visual: pct > 100 mostra barra cheia mas mantem texto real
    pct_int = int(round(pct))
    fill_width = min(max(pct_int, 0), 100)
    # Quando preenchimento < 20%, texto fica fora da barra (a direita do fill)
    pct_inside_cls = "outside" if fill_width < 18 else "inside"
    return f'''<div class="atingimento-row"><div class="atingimento-bar"><div class="fill {cls}" style="width:{fill_width}%;"></div><div class="pct-label {pct_inside_cls}">{pct_int}%</div></div><div class="atingimento-meta-side">{meta_str}</div></div>'''


# ─── SLIDE 4 — Visão geral (12 cards grandes) ────────────────
def fgb_card(label, ind, kind, meta_total):
    if not ind: ind = {}
    v = get(ind, "n1_value")
    if v is None: v = get(ind, "n1_qty")
    if kind == "brl": vstr = fmt_brl_short(v)
    elif kind == "pct" and v is not None and v < 1: vstr = fmt_pct(v*100, 1)
    elif kind == "int": vstr = fmt_int(v)
    else: vstr = fmt_n(v)
    cor = _ind_status(ind); cls = status_class(cor)
    pct = get(ind, "pct_atingimento")
    if meta_total is None: meta_str_inner = "sem meta"
    elif kind == "brl": meta_str_inner = fmt_brl_short(meta_total)
    elif kind == "pct": meta_str_inner = fmt_pct(meta_total*100 if meta_total<1 else meta_total, 1)
    elif kind == "int": meta_str_inner = fmt_int(meta_total)
    else: meta_str_inner = fmt_n(meta_total)
    # Ajustes PJ2 2026-05-11 Batch B: barrinha de atingimento substitui "xx% da meta · meta R$ xxK"
    meta_side = f"meta <strong>{meta_str_inner}</strong>" if meta_total is not None else "<span style='color:var(--vc-300);'>sem meta</span>"
    bar = _atingimento_bar(pct, meta_side, cor)
    return f'''<div class="fgb-card"><div class="lbl">{esc(label)}</div><div class="val {cls}">{esc(vstr)}</div>{bar}</div>'''


def render_fech_visao_geral(wbr, card, logo, asses_seg=None, asses_cons=None):
    fech = get(wbr, "indicadores", "fechamento", default={})
    cons = dict(fech.get("consorcios", {})); seg = dict(fech.get("seguros", {}))
    # Correcao 2026-05-12: aplicar mesmo over-ride Bitrix-100% que render_fech_vertical:
    # qty (quantidade_*) e ticket_medio_*_fechamento sao recalculados a partir de
    # asses_data (won_fech por canal) para coerencia entre visao geral e detalhe.
    def _override_qty_and_ticket(data_dict, asses_data, vert):
        if not asses_data:
            return data_dict
        qty_id = "quantidade_seguros_mensal" if vert == "seguros" else "quantidade_consorcio_mensal"
        vol_id = "volume_seguros_mensal" if vert == "seguros" else "volume_consorcio_mensal"
        ticket_id = "ticket_medio_premio_seg_fechamento" if vert == "seguros" else "ticket_medio_consorcio_fechamento"
        asses_won = {"investimentos": 0, "credito": 0, "outros_m7": 0}
        for _, r in asses_data.items():
            c = r.get("canal", "desconhecido")
            if c in asses_won:
                asses_won[c] += (r.get("won_fech", 0) or 0)
        total_qty = sum(asses_won.values())
        # Metas top-level (kpi do Card.metas_ppi)
        meta_qty = (get(card, "metas_ppi", qty_id, "valor") or 0)
        meta_ticket_id = "ticket_medio_premio_seg" if vert == "seguros" else "ticket_medio_consorcio_mensal"
        meta_ticket = (get(card, "metas_ppi", meta_ticket_id, "valor") or 0)
        # Correcao 2026-05-12: recalcular status.cor coerente com pct novo
        # (caso contrario val_cls e fill_cls usam status pre-override do WBR).
        _COR = {"verde":{"emoji":"\U0001F7E2","cor":"verde"},"amarelo":{"emoji":"\U0001F7E1","cor":"amarelo"},"vermelho":{"emoji":"\U0001F534","cor":"vermelho"},"cinza":{"emoji":"⚪","cor":"cinza"}}
        def _status_from_pct(pct_val):
            c = cor_from_pct(pct_val) if pct_val is not None else "cinza"
            return dict(_COR[c])
        # Override qty (com pct + status recalculados)
        if qty_id in data_dict and isinstance(data_dict[qty_id], dict):
            ind_copy = dict(data_dict[qty_id])
            ind_copy["n2_agregado"] = asses_won
            ind_copy["n1_value"] = total_qty
            ind_copy["n1_qty"] = total_qty
            if meta_qty:
                pct_qty = total_qty / meta_qty * 100
                ind_copy["pct_atingimento"] = pct_qty
                ind_copy["status"] = _status_from_pct(pct_qty)
            data_dict[qty_id] = ind_copy
        # Override ticket (com pct + status recalculados)
        vol_data = data_dict.get(vol_id) or {}
        vol_n2 = vol_data.get("n2_agregado") or {}
        total_vol = sum((vol_n2.get(c) or 0) for c in ("investimentos","credito","outros_m7"))
        ticket_existing = dict(data_dict.get(ticket_id) or {})
        ticket_n2 = {c: ((vol_n2.get(c) or 0) / asses_won[c]) if asses_won[c] > 0 else None for c in ("investimentos","credito","outros_m7")}
        ticket_existing["n2_agregado"] = ticket_n2
        ticket_n1 = (total_vol / total_qty) if total_qty > 0 else None
        ticket_existing["n1_value"] = ticket_n1
        if meta_ticket and ticket_n1 is not None:
            pct_ticket = ticket_n1 / meta_ticket * 100
            ticket_existing["pct_atingimento"] = pct_ticket
            ticket_existing["status"] = _status_from_pct(pct_ticket)
        data_dict[ticket_id] = ticket_existing
        return data_dict
    seg = _override_qty_and_ticket(seg, asses_seg, "seguros")
    cons = _override_qty_and_ticket(cons, asses_cons, "consorcios")
    rec_pj2 = (get(cons,"receita_consorcio_mensal","n1_value") or 0) + (get(seg,"receita_seguros_mensal","n1_value") or 0)
    meta_pj2 = (get(card,"metas_ppi","receita_consorcio_mensal","valor") or 0) + (get(card,"metas_ppi","receita_seguros_mensal","valor") or 0)
    pct_pj2 = (rec_pj2 / meta_pj2 * 100) if meta_pj2 else 0

    def m(ind_id):
        mp = get(card, "metas_ppi", ind_id) or {}
        return mp.get("valor")

    seg_cards = (
        fgb_card("Receita", get(seg,"receita_seguros_mensal"),"brl", m("receita_seguros_mensal")) +
        fgb_card("Volume", get(seg,"volume_seguros_mensal"),"brl", m("volume_seguros_mensal")) +
        fgb_card("Qtd Apólices", get(seg,"quantidade_seguros_mensal"),"int", m("quantidade_seguros_mensal")) +
        fgb_card("Ticket Médio", get(seg,"ticket_medio_premio_seg_fechamento"),"brl", m("ticket_medio_premio_seg")) +
        fgb_card("Tx Conversão", get(seg,"taxa_conversao_funil_seg"),"pct", m("taxa_conversao_funil_seg")) +
        fgb_card("Oport. Criadas", get(seg,"oportunidades_criadas_funil_seg"),"int", get(card,"metas_ppi","oportunidades_criadas_funil_seg","qty"))
    )
    cons_cards = (
        fgb_card("Receita", get(cons,"receita_consorcio_mensal"),"brl", m("receita_consorcio_mensal")) +
        fgb_card("Volume", get(cons,"volume_consorcio_mensal"),"brl", m("volume_consorcio_mensal")) +
        fgb_card("Qtd Cotas", get(cons,"quantidade_consorcio_mensal"),"int", m("quantidade_consorcio_mensal")) +
        fgb_card("Ticket Médio", get(cons,"ticket_medio_consorcio_fechamento"),"brl", m("ticket_medio_consorcio_mensal")) +
        fgb_card("Tx Conversão", get(cons,"taxa_conversao_funil_con"),"pct", m("taxa_conversao_funil_con")) +
        fgb_card("Oport. Criadas", get(cons,"oportunidades_criadas_funil"),"int", get(card,"metas_ppi","oportunidades_criadas_funil","qty"))
    )

    return f'''<section>{slide_head("Fechamento Mensal · {PJ2_CICLO_FECHAMENTO}","Fechamento {PJ2_VERTICAIS_DISPLAY} · Visão Geral", logo)}
<div class="slide-body">
<div class="fech-headline"><span class="fh-eyebrow">Como foi {PJ2_CICLO_FECHAMENTO} · {PJ2_VERTICAIS_DISPLAY}</span>{PJ2_VERTICAIS_DISPLAY} fechou em <em>{int(pct_pj2)}% da meta</em> · Receita <strong>{fmt_brl_short(rec_pj2)}</strong> · meta <strong>{fmt_brl_short(meta_pj2)}</strong>.</div>
<div class="fech-2grids">
<div class="fech-grid-block"><div class="fgb-head seg">Seguros · Empresarial e Vida · 6 indicadores</div><div class="fgb-grid">{seg_cards}</div></div>
<div class="fech-grid-block"><div class="fgb-head cons">Consórcios · 6 indicadores</div><div class="fgb-grid">{cons_cards}</div></div>
</div></div>
{slide_foot("Bloco I · Fechamento", 4)}</section>'''


# ─── SLIDE 5/6 — Fechamento detalhado por vertical ───────────
def fech_col_row(label, ind_atual, canal, kind, meta_canal_v):
    if not ind_atual: ind_atual = {}
    n2 = get(ind_atual, "n2_agregado") or {}
    v = n2.get(canal)
    # Ajustes PJ2 2026-05-11 Batch H: corrigido `v < 1` → `v <= 1` para suportar 100% exato
    if kind == "brl": vstr = fmt_brl_short(v)
    elif kind == "pct" and v is not None and v <= 1: vstr = fmt_pct(v*100, 1)
    elif kind == "int": vstr = fmt_int(v)
    else: vstr = fmt_n(v)
    if v is not None and meta_canal_v not in (None, 0):
        # Para indicadores "menor melhor" (estagnação, sem atividade, tempo de ciclo c/ meta):
        # detectar pelo label e inverter logica de cor
        lbl_low = (label or "").lower()
        eh_menor_melhor = ("estagna" in lbl_low) or ("sem ativ" in lbl_low) or ("tempo de ciclo" in lbl_low)
        if eh_menor_melhor:
            pct = v / meta_canal_v * 100
            # menor melhor: pct <= 100 = verde (dentro da meta), <=125 = amarelo, > 125 = vermelho
            cor = "verde" if pct <= 100 else ("amarelo" if pct <= 125 else "vermelho")
        else:
            pct = v / meta_canal_v * 100
            cor = cor_from_pct(pct)
    else:
        pct = None; cor = "cinza"
    if meta_canal_v is None: meta_str = "<span style='color:var(--vc-300);'>sem meta</span>"
    else:
        if kind == "brl": meta_str = f"meta <strong>{fmt_brl_short(meta_canal_v)}</strong>"
        elif kind == "pct" and meta_canal_v <= 1: meta_str = f"meta <strong>{fmt_pct(meta_canal_v*100, 1)}</strong>"
        elif kind == "int": meta_str = f"meta <strong>{fmt_int(meta_canal_v)}</strong>"
        else: meta_str = f"meta <strong>{fmt_n(meta_canal_v)}</strong>"
    # Ajustes PJ2 2026-05-11 Batch B: barrinha de atingimento substitui "xx% da meta"
    bar = _atingimento_bar(pct, meta_str, cor)
    return f'''<div class="fc-row"><div class="lbl">{esc(label)}</div><div class="val {status_class(cor)}">{esc(vstr)}</div>{bar}</div>'''


def render_fech_vertical(num, vert, wbr, card, asses_data, logo):
    fech = get(wbr, "indicadores", "fechamento", default={})
    data = fech.get(vert, {})
    # Ajustes PJ2 2026-05-11 Batch G #3: titulo Seguros explicita Empresarial+Vida
    label_vert = "Seguros · Empresarial e Vida" if vert == "seguros" else "Consórcios"
    # Correcao 2026-05-11 #10 (REVIEW): Cards refletem BITRIX 100% fielmente
    # (mesma fonte do Pareto: extract_per_assessor_*). Recalcular tanto:
    #  - oportunidades_criadas (criadas_fech)
    #  - quantidade (won_fech, Apólices Fechadas / Contratos Fechados)
    # a partir do asses_data por canal — garantindo que Card = Soma Pareto.
    asses_criadas = {"investimentos": 0, "credito": 0, "outros_m7": 0}
    asses_won = {"investimentos": 0, "credito": 0, "outros_m7": 0}
    for _, r in asses_data.items():
        c = r.get("canal", "desconhecido")
        if c in asses_criadas:
            asses_criadas[c] += (r.get("criadas_fech", 0) or 0)
            asses_won[c] += (r.get("won_fech", 0) or 0)
    cri_id = "oportunidades_criadas_funil_seg" if vert == "seguros" else "oportunidades_criadas_funil"
    qty_id = "quantidade_seguros_mensal" if vert == "seguros" else "quantidade_consorcio_mensal"
    data = dict(data)
    # Sobrescreve oport_criadas com Bitrix-only
    if cri_id in data and isinstance(data[cri_id], dict):
        ind_copy = dict(data[cri_id])
        ind_copy["n2_agregado"] = asses_criadas
        ind_copy["n1_qty"] = sum(asses_criadas.values())
        data[cri_id] = ind_copy
    # Sobrescreve quantidade (won_fech = nova venda fechada = contratos/apólices fechadas Bitrix)
    if qty_id in data and isinstance(data[qty_id], dict):
        ind_copy = dict(data[qty_id])
        ind_copy["n2_agregado"] = asses_won
        ind_copy["n1_qty"] = sum(asses_won.values())
        data[qty_id] = ind_copy
    # Correcao 2026-05-12: ticket_medio_*_fechamento RECALCULADO dinamicamente como
    # vol_canal / qty_canal_won (Bitrix-only) — substitui valores pre-computados
    # no WBR que estavam inconsistentes com a qty exibida no card.
    vol_id_calc = "volume_seguros_mensal" if vert == "seguros" else "volume_consorcio_mensal"
    ticket_id_calc = "ticket_medio_premio_seg_fechamento" if vert == "seguros" else "ticket_medio_consorcio_fechamento"
    vol_data_calc = get(data, vol_id_calc) or {}
    vol_n2_calc = vol_data_calc.get("n2_agregado") or {}
    ticket_n2_calc = {}
    for canal_calc in ("investimentos", "credito", "outros_m7"):
        vc = vol_n2_calc.get(canal_calc) or 0
        qc = asses_won.get(canal_calc) or 0
        ticket_n2_calc[canal_calc] = (vc / qc) if qc > 0 else None
    total_vol_calc = sum((vol_n2_calc.get(c) or 0) for c in ("investimentos","credito","outros_m7"))
    total_qty_calc = sum(asses_won.values())
    ticket_existing = dict(data.get(ticket_id_calc) or {})
    ticket_existing["n2_agregado"] = ticket_n2_calc
    ticket_existing["n1_value"] = (total_vol_calc / total_qty_calc) if total_qty_calc > 0 else None
    data[ticket_id_calc] = ticket_existing
    # Ajustes PJ2 2026-05-11 Batch C #9: 2 indicadores NOVOS no fechamento:
    #   - Tempo de Ciclo (entre Ticket Médio e Tx Conversão) — meta pendente
    #   - Estagnação Mediana % ativos (último) — meta 40%
    # IDs "tempo_de_ciclo_*" e "estagnacao_mediana_pct_ativas_*" nao existem no WBR
    # fabricado atual → cards mostram "—" como placeholder ate dados serem coletados.
    if vert == "seguros":
        ids = ["volume_seguros_mensal","receita_seguros_mensal","quantidade_seguros_mensal","ticket_medio_premio_seg",
               "tempo_de_ciclo_funil_seg","taxa_conversao_funil_seg","oportunidades_criadas_funil_seg",
               "estagnacao_mediana_pct_ativas_seg"]
        ticket_real_id = "ticket_medio_premio_seg_fechamento"
        qty_label = "Apólices Fechadas"
    else:
        ids = ["volume_consorcio_mensal","receita_consorcio_mensal","quantidade_consorcio_mensal","ticket_medio_consorcio_mensal",
               "tempo_de_ciclo_funil_con","taxa_conversao_funil_con","oportunidades_criadas_funil",
               "estagnacao_mediana_pct_ativas_con"]
        ticket_real_id = "ticket_medio_consorcio_fechamento"
        qty_label = "Contratos Fechados"
    # Ajustes PJ2 2026-05-11 (Batch A): "Quantidade" → "Contratos Fechados"/"Apólices Fechadas";
    # sufixo CRM em Tx Conversao e Oport. Criadas (indicadores Bitrix). Volume/Receita/Ticket sem CRM (fonte Excel/banco).
    # Tempo de Ciclo e Estagnacao Mediana sao CRM (fonte funil Bitrix).
    labels = ["Volume","Receita",qty_label,"Ticket Médio",
              "Tempo de Ciclo CRM","Tx Conversão CRM","Oport. Criadas CRM",
              "Estagnação Mediana CRM"]
    kinds = ["brl","brl","int","brl",
             "int","pct","int",
             "pct"]
    # Metas para os 2 indicadores novos (Tempo de Ciclo: TODO pendente; Estagnacao: 40%)
    # Aplicado uniformemente nos canais por enquanto.
    extra_metas = {
        "tempo_de_ciclo_funil_seg": 30,  # 30 dias (decisao Bruno 2026-05-12) — menor melhor
        "tempo_de_ciclo_funil_con": 30,
        "estagnacao_mediana_pct_ativas_seg": 0.40,  # 40% conforme decisao 11/05
        "estagnacao_mediana_pct_ativas_con": 0.40,
    }

    def metas_canal(canal):
        out = []
        for ind_id, kind in zip(ids, kinds):
            if ind_id in extra_metas:
                out.append(extra_metas[ind_id])
            elif "ticket_medio" in ind_id:
                m = derive_meta_ticket_fechamento_canal(card, vert, "fechamento")
                out.append(m.get(canal))
            else:
                m = derive_meta_canal(card, vert, ind_id, "fechamento")
                out.append(m.get(canal))
        return out

    metas_inv = metas_canal("investimentos")
    metas_cred = metas_canal("credito")

    rows_inv = ""; rows_cred = ""
    for label, ind_id, kind, m_inv, m_cred in zip(labels, ids, kinds, metas_inv, metas_cred):
        ind = get(data, ticket_real_id) if "ticket_medio" in ind_id else get(data, ind_id)
        rows_inv += fech_col_row(label, ind, "investimentos", kind, m_inv)
        rows_cred += fech_col_row(label, ind, "credito", kind, m_cred)

    # Pareto squad listing — assessor a assessor (TODOS exceto hidden, scroll interno)
    # Ajustes PJ2 2026-05-11 (Batch A #7): em "Outros M7", filtrar quem esta zerado em criadas+won+lose
    pareto_html = ""
    for canal_key, canal_label, css_cls in [("investimentos", "Squad Investimentos", "inv"), ("credito", "Squad Crédito", "cred"), ("outros_m7", "Outros M7", "outros")]:
        squad_full = get_squad_full_list(card, canal_key)
        assesores_canal = [(n, r) for n, r in asses_data.items() if r.get("canal") == canal_key]
        assesores_canal = filter_hidden(assesores_canal, card)  # remove hidden
        names_in_data = set(normalize_name(n) for n, _ in assesores_canal)
        for nm in squad_full:
            if normalize_name(nm) not in names_in_data:
                assesores_canal.append((nm, {"criadas_fech": 0, "won_fech": 0, "lose_fech": 0}))
        # Filtro Outros M7: so aparece quem tem criada OU fechada (sem zerados em ambos)
        if canal_key == "outros_m7":
            assesores_canal = [
                (n, r) for n, r in assesores_canal
                if (r.get("criadas_fech", 0) or 0) > 0
                or (r.get("won_fech", 0) or 0) > 0
                or (r.get("lose_fech", 0) or 0) > 0
            ]
        assesores_canal.sort(key=lambda x: -(x[1].get("criadas_fech", 0) or 0) - 0.5*(x[1].get("won_fech", 0) or 0))
        pareto_html += f'<div class="psq-head {css_cls}">{esc(canal_label)} · {len(assesores_canal)} assessores</div>'
        max_cri = max([r.get("criadas_fech", 0) or 0 for _, r in assesores_canal] + [1])
        max_won = max([(r.get("won_fech", 0) or 0) + (r.get("lose_fech", 0) or 0) for _, r in assesores_canal] + [1])
        for nm, r in assesores_canal:
            cri = r.get("criadas_fech", 0) or 0
            won = r.get("won_fech", 0) or 0
            lose = r.get("lose_fech", 0) or 0
            wcri = (cri / max_cri * 100) if cri else 0
            wwon = (won / max_won * 100) if won else 0
            wlose = (lose / max_won * 100) if lose else 0
            nm_cls = "nm zero" if (cri == 0 and won == 0 and lose == 0) else "nm"
            criadas_bar = f'<div class="mini"><div class="fb fb-lime" style="width:{wcri}%;">{cri}</div></div>' if cri else '<div class="mini"><div class="fb fb-mute" style="width:0%;"></div></div>'
            # Fechadas: dual W/L (mantém)
            if won + lose > 0:
                fech_bar = '<div class="mini">'
                if won: fech_bar += f'<div class="fb fb-good" style="width:{wwon}%;">{won}W</div>'
                if lose: fech_bar += f'<div class="fb fb-bad" style="width:{wlose}%;">{lose}L</div>'
                fech_bar += '</div>'
            else:
                fech_bar = '<div class="mini"><div class="fb fb-mute" style="width:0%;"></div></div>'
            pareto_html += f'<div class="psq-row"><div class="{nm_cls}">{esc(nm)}</div><div class="bar-cell">{criadas_bar}</div><div class="bar-cell">{fech_bar}</div></div>'

    # Correcao 2026-05-11 #10 (REVIEW USUARIO): disclaimer removido porque cards
    # agora refletem Bitrix 100% fielmente (n2_agregado oport_criadas recalculado a partir do asses_data).
    return f'''<section>{slide_head(f"Fechamento 2026-04 · Vertical", f"Fechamento {label_vert}", logo, avatar="SE" if vert == "seguros" else "CO")}
<div class="slide-body"><div class="fech-vert-wrap">
<div class="fech-col"><div class="fc-head inv">Investimentos · 28 assessores</div>{rows_inv}</div>
<div class="fech-col"><div class="fc-head cred">Crédito · 7 assessores</div>{rows_cred}</div>
<div class="pareto-card">
<div class="pch"><div>Assessor (SDR/MKT)</div><div>Criadas</div><div>Fechadas (W/L)</div></div>
<div class="pcb">{pareto_html}</div>
</div>
</div></div>
{slide_foot(f"Bloco I · Fechamento {label_vert}", num)}</section>'''


# ─── SLIDE 7 — Diretrizes ────────────────────────────────────
def render_diretrizes(wbr, logo):
    fech = get(wbr, "indicadores", "fechamento", default={})
    vermelhos = []
    for vert, inds in fech.items():
        if not isinstance(inds, dict): continue
        for ind_id, ind in inds.items():
            if isinstance(ind, dict) and _ind_status(ind) == "vermelho":
                pct = get(ind, "pct_atingimento")
                vermelhos.append((vert, ind_id, pct))
    vermelhos.sort(key=lambda x: x[2] if x[2] is not None else 0)
    diretrizes = []
    for vert, ind_id, pct in vermelhos[:3]:
        if "receita" in ind_id:
            diretrizes.append({
                "titulo": f"Receita {vert.title()} · {int(pct)}% da meta",
                "acao": f"Diagnóstico 1:1 com squad coordenador (Cred + Inv) e plano de retomada antes do checkpoint M+1.",
                "owner": "Joel Freitas"})
        elif "volume" in ind_id:
            diretrizes.append({
                "titulo": f"Volume {vert.title()} · {int(pct)}% da meta",
                "acao": f"Reativar pipeline subutilizado · revisão de aging por canal e priorização contas-âncora até 25/05.",
                "owner": "Joel Freitas"})
        elif "criadas" in ind_id:
            diretrizes.append({
                "titulo": f"Originação {vert.title()} · {int(pct)}% da meta",
                "acao": f"Plano de cadência semanal por SDR · meta de criação proporcional ao squad ({SQUAD_INV} Inv / {SQUAD_CRED} Cred).",
                "owner": "Joel Freitas + SDRs"})
        else:
            diretrizes.append({"titulo": f"Indicador em desvio · {vert.title()} {int(pct)}%", "acao": "Investigar causa-raiz com squad e definir contramedida no próximo ciclo.", "owner": "Joel Freitas"})
    while len(diretrizes) < 3:
        diretrizes.append({"titulo": "Reservado", "acao": "Espaço para nova diretriz a definir no ritual.", "owner": "—"})
    cards = ""
    for i, d in enumerate(diretrizes[:3], 1):
        cards += f'''<div class="next-card"><div class="nc-num">{i:02d}</div><div class="nc-title">{esc(d["titulo"])}</div><div class="nc-meta"><div><div class="k">Ação</div><div class="v">{esc(d["acao"])}</div></div><div><div class="k">Owner</div><div class="v">{esc(d["owner"])}</div></div></div></div>'''
    return f'''<section class="closing"><div class="closing-inner">
<div class="head-row"><div>
<div style="display:flex;align-items:center;gap:20px;margin-bottom:32px;"><div style="width:48px;height:3px;background:var(--lime);"></div>
<span style="font-size:14px;letter-spacing:0.24em;text-transform:uppercase;color:var(--lime);font-weight:500;">Bloco I · Diretrizes {PJ2_CICLO_ATUAL}</span></div>
<h2>Diretrizes para o <em>mês seguinte</em></h2>
<div style="color:var(--verde-claro);font-size:18px;margin-top:20px;max-width:60ch;line-height:1.5;">Top desvios identificados no fechamento de Abril · contramedidas para Maio.</div>
</div><img class="logo" src="data:image/png;base64,{logo}" alt="M7" style="height:36px;"></div>
<div class="next-grid">{cards}</div>
<div class="closing-foot"><div><strong>Diretrizes {PJ2_CICLO_ATUAL}</strong> · {PJ2_VERTICAIS_DISPLAY}</div><div>Slide 07 · Joel coordena</div></div>
</div></section>'''


# ─── SLIDE 9/10 — MATRIZ (dense, Outros M7 mute, 11 linhas) ─
def emit_cell(value, pct_str, meta_str, cor):
    cls = f"cell {status_class(cor)}"
    return f'<div class="{cls}"><div class="v"><div class="num">{esc(value)}</div><div class="meta">{esc(pct_str)}</div><div class="sub">{esc(meta_str)}</div></div></div>'


def matriz_row(label, ind, kind, vert, ind_id, card,
                  field_value="n1_value", field_canal="n2_agregado",
                  is_pct_field=False, custom_meta_canal_fn=None):
    if not ind: ind = {}
    n1 = get(ind, field_value)
    n2 = get(ind, field_canal) or {}

    def fmt_v(v):
        if v is None: return "—"
        if kind == "brl": return fmt_brl_short(v)
        if kind == "pct":
            if is_pct_field and v < 1: return fmt_pct(v*100, 1)
            return fmt_pct(v, 1)
        if kind == "int": return fmt_int(v)
        return fmt_n(v)

    def fmt_meta(v):
        if v is None: return "sem meta"
        if kind == "brl": return f"meta {fmt_brl_short(v)}"
        if kind == "pct": return f"meta {fmt_pct(v*100, 1) if v < 1 else fmt_pct(v, 1)}"
        if kind == "int": return f"meta {fmt_int(v)}"
        return f"meta {fmt_n(v)}"

    if custom_meta_canal_fn:
        metas = custom_meta_canal_fn(card, vert, "atual")
    elif "ticket_medio" in (ind_id or "") and "fechamento" not in (ind_id or ""):
        metas = derive_meta_ticket_fechamento_canal(card, vert, "atual")
    else:
        metas = derive_meta_canal(card, vert, ind_id, "atual") if ind_id else {"investimentos":None,"credito":None,"outros_m7":None}

    meta_total = None
    if ind_id:
        mp = get(card, "metas_ppi", ind_id) or {}
        meta_total = mp.get("valor_proximo_mes") or mp.get("valor") or mp.get("qty")
        if "oportunidades_ativas" in ind_id and field_value == "n1_volume":
            meta_total = mp.get("volume_proximo_mes") or mp.get("volume")
        if "oportunidades_ativas" in ind_id and field_value == "n1_ticket_medio":
            meta_total = mp.get("ticket_medio_proximo_mes") or mp.get("ticket_medio")

    cells = []
    # Outros M7: SEMPRE só realizado em cinza (mute), SEM linhas "sem meta"
    v_outros = n2.get("outros_m7") if isinstance(n2, dict) else None
    if v_outros is None:
        cells.append('<div class="cell mute"><div class="v"><div class="num">—</div></div></div>')
    else:
        cells.append(f'<div class="cell mute"><div class="v"><div class="num">{esc(fmt_v(v_outros))}</div></div></div>')

    # Cred + Inv: 3-níveis com cor
    for canal in ["credito", "investimentos"]:
        v = n2.get(canal) if isinstance(n2, dict) else None
        m = metas.get(canal)
        if v is None and m is None:
            cells.append('<div class="cell mute"><div class="v"><div class="num">—</div><div class="meta">—</div></div></div>')
            continue
        if v is not None and m not in (None, 0):
            pct = v / m * 100; cor = cor_from_pct(pct)
            pct_str = f"{int(pct)}% meta"
        else:
            cor = "cinza"; pct_str = "—" if v is None else "sem meta"
        cells.append(emit_cell(fmt_v(v), pct_str, fmt_meta(m), cor))

    # Total
    if n1 is not None and meta_total not in (None, 0):
        pct_t = n1 / meta_total * 100; cor_t = cor_from_pct(pct_t)
        cells.append(emit_cell(fmt_v(n1), f"{int(pct_t)}% meta", fmt_meta(meta_total), cor_t))
    elif n1 is not None:
        cells.append(emit_cell(fmt_v(n1), "—", fmt_meta(meta_total), "cinza"))
    else:
        cells.append('<div class="cell mute"><div class="v"><div class="num">—</div><div class="meta">—</div></div></div>')

    return f'<div class="mx-row data"><div class="col-ind">{esc(label)}</div>{"".join(cells)}</div>'


def _matriz_row_ativas_ticket(ind, card, vert, fase="atual"):
    """Linha Ativas (ticket) com cálculo vol_canal/qty_canal por canal."""
    if not ind: ind = {}
    n2_vol = get(ind, "n2_agregado_vol") or {}
    n2_qty = get(ind, "n2_agregado_qty") or {}
    n1_ticket = get(ind, "n1_ticket_medio")

    # Meta ticket por canal: usa derive helper (mesma meta total replicada Inv/Cred)
    metas = derive_meta_ativas_ticket_canal(card, vert, fase)
    ativ_id = "oportunidades_ativas_funil_seg" if vert == "seguros" else "oportunidades_ativas_funil"
    metas_ppi = get(card, "metas_ppi", ativ_id) or {}
    meta_total = metas_ppi.get("ticket_medio_proximo_mes") if fase == "atual" else metas_ppi.get("ticket_medio")
    if meta_total is None: meta_total = metas_ppi.get("ticket_medio")

    cells = []
    # Outros M7: realizado em mute, sem meta
    vol_o = n2_vol.get("outros_m7"); qty_o = n2_qty.get("outros_m7")
    ticket_o = (vol_o / qty_o) if (vol_o and qty_o) else None
    if ticket_o is None:
        cells.append('<div class="cell mute"><div class="v"><div class="num">—</div></div></div>')
    else:
        cells.append(f'<div class="cell mute"><div class="v"><div class="num">{esc(fmt_brl_short(ticket_o))}</div></div></div>')

    for canal in ["credito", "investimentos"]:
        vol_c = n2_vol.get(canal); qty_c = n2_qty.get(canal)
        ticket_c = (vol_c / qty_c) if (vol_c and qty_c) else None
        m = metas.get(canal)
        if ticket_c is None:
            cells.append('<div class="cell mute"><div class="v"><div class="num">—</div></div></div>')
            continue
        if m and m > 0:
            pct = ticket_c / m * 100
            cor = cor_from_pct(pct)
            cells.append(f'<div class="cell {status_class(cor)}"><div class="v"><div class="num">{esc(fmt_brl_short(ticket_c))}</div><div class="meta">{int(pct)}% meta</div><div class="sub">meta {fmt_brl_short(m)}</div></div></div>')
        else:
            cells.append(f'<div class="cell mute"><div class="v"><div class="num">{esc(fmt_brl_short(ticket_c))}</div></div></div>')

    # Total
    if n1_ticket is not None:
        if meta_total and meta_total > 0:
            pct_t = n1_ticket / meta_total * 100
            cor_t = cor_from_pct(pct_t)
            cells.append(f'<div class="cell {status_class(cor_t)}"><div class="v"><div class="num">{esc(fmt_brl_short(n1_ticket))}</div><div class="meta">{int(pct_t)}% meta</div><div class="sub">meta {fmt_brl_short(meta_total)}</div></div></div>')
        else:
            cells.append(f'<div class="cell mute"><div class="v"><div class="num">{esc(fmt_brl_short(n1_ticket))}</div></div></div>')
    else:
        cells.append('<div class="cell mute"><div class="v"><div class="num">—</div></div></div>')

    return f'<div class="mx-row data"><div class="col-ind">Ticket Médio Pipeline</div>{"".join(cells)}</div>'


def _matriz_row_est_qty(ind):
    """Estagnadas (qty): qty + volume entre parenteses, cor herdada do pct_ativas.
    S1-A2 (2026-05-16): sync com default — display "qty (R$ vol_compact)".
    """
    if not ind: ind = {}
    n1 = get(ind, "n1_qty")
    n1_vol = get(ind, "n1_vol") or get(ind, "vol_em_risco") or 0
    n2 = get(ind, "n2_agregado_qty") or {}
    n2_vol = get(ind, "n2_agregado_vol") or get(ind, "n2_agregado_volume") or {}
    pct_canal = get(ind, "pct_canal_ativas") or {}
    n1_pct = get(ind, "n1_pct_ativas")
    meta_max = 40

    def cor_for_pct(p):
        if p is None: return "cinza"
        if p <= meta_max: return "verde"
        if p <= meta_max * 1.3: return "amarelo"
        return "vermelho"

    def num_with_vol(qty, vol):
        qty_str = esc(fmt_int(qty))
        if isinstance(vol, (int, float)) and vol > 0:
            return f'{qty_str} ({esc(fmt_brl_short(vol))})'
        return qty_str

    cells = []
    # Outros M7: só num em mute
    v_o = n2.get("outros_m7")
    vol_o = n2_vol.get("outros_m7") if n2_vol else None
    cells.append(f'<div class="cell mute"><div class="v"><div class="num">{num_with_vol(v_o, vol_o)}</div></div></div>')
    # Cred + Inv: num com cor baseada em pct_ativas
    for canal in ["credito", "investimentos"]:
        v = n2.get(canal)
        vol_c = n2_vol.get(canal) if n2_vol else None
        if v is None:
            cells.append('<div class="cell mute"><div class="v"><div class="num">—</div></div></div>')
            continue
        p = pct_canal.get(canal)
        cor = cor_for_pct(p)
        cells.append(f'<div class="cell {status_class(cor)}"><div class="v"><div class="num">{num_with_vol(v, vol_c)}</div></div></div>')
    # Total
    cor_t = cor_for_pct(n1_pct)
    cells.append(f'<div class="cell {status_class(cor_t)}"><div class="v"><div class="num">{num_with_vol(n1, n1_vol)}</div></div></div>')
    return f'<div class="mx-row data"><div class="col-ind">Oport. Estagnadas CRM (qty)</div>{"".join(cells)}</div>'


def _matriz_row_sem_mov(ind, ativas_ind):
    """Sem Ativ. ou Atras. CRM: display "qty (X%)" + cor proporcional ao volume ativo.
    S1-A2 (2026-05-16): sync com default — regra cor 0=verde, 0-20%=amarelo, 21%+=vermelho.
    """
    if not ind: ind = {}
    n1 = get(ind, "n1_qty")
    n2 = get(ind, "n2_agregado") or {}
    # Se n2 não está preenchido (override só total), distribui proporcional às ativas
    if n1 is not None and (not n2 or all(v is None for v in n2.values())):
        ativ_n2 = get(ativas_ind, "n2_agregado_qty") or {}
        total_ativ = sum(v for v in ativ_n2.values() if v) or 1
        n2 = {c: round((ativ_n2.get(c) or 0) / total_ativ * n1) for c in ["investimentos", "credito", "outros_m7"]}

    n1_pct = get(ind, "n1_pct_ativas") or 0
    pct_canal = get(ind, "pct_canal_ativas") or {}
    # ativas por canal para computar pct quando override do indicador nao traz pct_canal
    ativas_n2 = get(ativas_ind, "n2_agregado_qty") or {} if ativas_ind else {}

    def cor_for(qty, pct):
        """Regra proporcional (sync default): 0=verde / 0-20%=amarelo / 21%+=vermelho."""
        if qty is None: return "cinza"
        if qty == 0: return "verde"
        if pct is None or pct <= 0: return "amarelo"  # has qty mas pct desconhecido
        if pct <= 20: return "amarelo"
        return "vermelho"

    def num_with_pct(qty, pct):
        qty_str = esc(fmt_int(qty))
        if isinstance(pct, (int, float)) and pct > 0:
            return f'{qty_str} ({pct:.0f}%)'
        return qty_str

    cells = []
    # Outros M7
    v_o = n2.get("outros_m7") if n2 else None
    p_o = pct_canal.get("outros_m7") if pct_canal else None
    if p_o is None and v_o is not None and ativas_n2.get("outros_m7"):
        p_o = (v_o / ativas_n2["outros_m7"]) * 100
    cells.append(f'<div class="cell mute"><div class="v"><div class="num">{num_with_pct(v_o, p_o) if v_o is not None else "—"}</div></div></div>')
    for canal in ["credito", "investimentos"]:
        v = n2.get(canal) if n2 else None
        if v is None:
            cells.append('<div class="cell mute"><div class="v"><div class="num">—</div></div></div>')
            continue
        p = pct_canal.get(canal) if pct_canal else None
        if p is None and ativas_n2.get(canal):
            p = (v / ativas_n2[canal]) * 100
        cor_c = cor_for(v, p)
        cells.append(f'<div class="cell {status_class(cor_c)}"><div class="v"><div class="num">{num_with_pct(v, p)}</div><div class="meta">meta 0</div></div></div>')
    # Total
    if n1 is not None:
        cor_t = cor_for(n1, n1_pct)
        cells.append(f'<div class="cell {status_class(cor_t)}"><div class="v"><div class="num">{num_with_pct(n1, n1_pct)}</div><div class="meta">meta 0</div></div></div>')
    else:
        cells.append('<div class="cell mute"><div class="v"><div class="num">—</div></div></div>')
    return f'<div class="mx-row data"><div class="col-ind">Sem Ativ. ou Atras. CRM</div>{"".join(cells)}</div>'


def _matriz_row_est_pct_ativas(ind):
    """Linha Estagnadas (% ativas) com pct por canal injetado."""
    if not ind: ind = {}
    n1_pct = get(ind, "n1_pct_ativas")
    pct_canal = get(ind, "pct_canal_ativas") or {}
    meta_pct_max = 40  # 40% das ativas é alarme

    def fmt_p(v):
        if v is None: return "—"
        return fmt_pct(v, 1)

    cells = []
    # Outros M7: só realizado em mute
    v_o = pct_canal.get("outros_m7")
    if v_o is None:
        cells.append('<div class="cell mute"><div class="v"><div class="num">—</div></div></div>')
    else:
        cells.append(f'<div class="cell mute"><div class="v"><div class="num">{esc(fmt_p(v_o))}</div></div></div>')
    # Cred + Inv
    for canal in ["credito", "investimentos"]:
        v = pct_canal.get(canal)
        if v is None:
            cells.append('<div class="cell mute"><div class="v"><div class="num">—</div></div></div>')
            continue
        # menor_melhor: pct > meta_pct_max é ruim
        if v <= meta_pct_max: cor = "verde"
        elif v <= meta_pct_max * 1.3: cor = "amarelo"
        else: cor = "vermelho"
        pct_str = f"{int(v / meta_pct_max * 100)}% meta"
        cells.append(f'<div class="cell {status_class(cor)}"><div class="v"><div class="num">{esc(fmt_p(v))}</div><div class="meta">{esc(pct_str)}</div><div class="sub">meta {meta_pct_max:.0f}%</div></div></div>')
    # Total
    if n1_pct is not None:
        if n1_pct <= meta_pct_max: cor = "verde"
        elif n1_pct <= meta_pct_max * 1.3: cor = "amarelo"
        else: cor = "vermelho"
        cells.append(f'<div class="cell {status_class(cor)}"><div class="v"><div class="num">{esc(fmt_p(n1_pct))}</div><div class="meta">{int(n1_pct / meta_pct_max * 100)}% meta</div><div class="sub">meta {meta_pct_max:.0f}%</div></div></div>')
    else:
        cells.append('<div class="cell mute"><div class="v"><div class="num">—</div></div></div>')

    return f'<div class="mx-row data"><div class="col-ind">Oport. Estagnadas CRM (% ativas)</div>{"".join(cells)}</div>'


def render_matriz(num, vert, wbr, card, logo, asses_data=None):
    atual = get(wbr, "indicadores", "atual", default={})
    data = atual.get(vert, {})
    label_vert = "Seguros" if vert == "seguros" else "Consórcios"
    # Correcao 2026-05-11 #10 (REVIEW 2): aplicar Bitrix-100% fielmente tambem na Matriz
    # (mes atual maio). Sobrescreve n2_agregado de oport_criadas e quantidade usando asses_data atual.
    if asses_data:
        asses_criadas_atual = {"investimentos": 0, "credito": 0, "outros_m7": 0}
        asses_won_atual = {"investimentos": 0, "credito": 0, "outros_m7": 0}
        for _, r in asses_data.items():
            c = r.get("canal", "desconhecido")
            if c in asses_criadas_atual:
                asses_criadas_atual[c] += (r.get("criadas_atual", 0) or 0)
                asses_won_atual[c] += (r.get("won_atual", 0) or 0)
        cri_id_m = "oportunidades_criadas_funil_seg" if vert == "seguros" else "oportunidades_criadas_funil"
        qty_id_m = "quantidade_seguros_mensal" if vert == "seguros" else "quantidade_consorcio_mensal"
        data = dict(data)
        if cri_id_m in data and isinstance(data[cri_id_m], dict):
            ind_copy = dict(data[cri_id_m]); ind_copy["n2_agregado"] = asses_criadas_atual; ind_copy["n1_qty"] = sum(asses_criadas_atual.values()); data[cri_id_m] = ind_copy
        if qty_id_m in data and isinstance(data[qty_id_m], dict):
            ind_copy = dict(data[qty_id_m]); ind_copy["n2_agregado"] = asses_won_atual; ind_copy["n1_qty"] = sum(asses_won_atual.values()); data[qty_id_m] = ind_copy
    if vert == "seguros":
        rec, vol, qty = "receita_seguros_mensal","volume_seguros_mensal","quantidade_seguros_mensal"
        tx, cri = "taxa_conversao_funil_seg","oportunidades_criadas_funil_seg"
        ativ, est, semv = "oportunidades_ativas_funil_seg","oportunidades_estagnadas_funil_seg","oportunidades_sem_movimentacao_funil_seg"
        qty_label = "Apólices Fechadas"
    else:
        rec, vol, qty = "receita_consorcio_mensal","volume_consorcio_mensal","quantidade_consorcio_mensal"
        tx, cri = "taxa_conversao_funil_con","oportunidades_criadas_funil"
        ativ, est, semv = "oportunidades_ativas_funil","oportunidades_estagnadas_funil","oportunidades_sem_movimentacao_funil"
        qty_label = "Contratos Fechados"

    # Ajustes PJ2 2026-05-11 (Batch A): renomeacoes + sufixo CRM em indicadores Bitrix
    rows_kpi = (
        matriz_row("Receita Mensal", get(data,rec), "brl", vert, rec, card) +
        matriz_row("Volume Mensal", get(data,vol), "brl", vert, vol, card) +
        matriz_row(qty_label, get(data,qty), "int", vert, qty, card)
    )
    rows_ppi = (
        matriz_row("Taxa de Conversão CRM", get(data,tx), "pct", vert, tx, card, is_pct_field=True) +
        matriz_row("Oport. Ativas CRM (qty)", get(data,ativ), "int", vert, ativ, card, field_value="n1_qty", field_canal="n2_agregado_qty") +
        matriz_row("Oport. Ativas CRM (volume)", get(data,ativ), "brl", vert, ativ, card, field_value="n1_volume", field_canal="n2_agregado_vol", custom_meta_canal_fn=derive_meta_ativas_volume_canal) +
        _matriz_row_ativas_ticket(get(data,ativ), card, vert) +
        matriz_row("Oport. Criadas CRM", get(data,cri), "int", vert, cri, card) +
        _matriz_row_est_qty(get(data,est)) +
        _matriz_row_est_pct_ativas(get(data,est)) +
        _matriz_row_sem_mov(get(data,semv), get(data,ativ))
    )

    callout = "Análise por canal: Inv puxa receita, Cred com gap em conversão. Funil com 'Sem Ativ. ou Atras.' alta — ação imediata na próxima cadência."

    return f'''<section class="esp-slide">{slide_head(f"Bloco II · Visão Consolidada", f"Matriz de Indicadores · {label_vert}", logo)}
<div class="slide-body"><div class="matrix">
<div class="matrix-grid">
<div class="mx-row head"><div class="col-ind">Indicador</div><div class="col-c c-outros">Outros M7</div><div class="col-c c-cred">Crédito</div><div class="col-c c-inv">Investimentos</div><div class="col-c c-total">M7 Total</div></div>
<div class="mx-section kpi">KPI · Indicadores de Resultado</div>{rows_kpi}
<div class="mx-section ppi">PPI · Indicadores de Funil</div>{rows_ppi}
</div>
<div class="callout"><span class="label">Lide</span>{esc(callout)}</div>
</div></div>
{slide_foot(f"Bloco II · Matriz {label_vert}", num)}</section>'''


# ─── SLIDE 11/12 — PA vazias ─────────────────────────────────
def render_pa_status(logo):
    return f'''<section>{slide_head("Bloco II · Plano de Ação", "Status das PAs · 0 ativas (1º ritual {PJ2_VERTICAIS_DISPLAY})", logo)}
<div class="slide-body" style="justify-content:center;align-items:center;">
<div style="background:#fff;border:1px solid var(--vc-100);border-radius:8px;padding:80px 100px;text-align:center;max-width:900px;">
<div style="font-size:96px;font-weight:200;color:var(--verde-caqui);line-height:1;">0</div>
<div style="font-size:14px;letter-spacing:0.18em;text-transform:uppercase;color:var(--verde-claro);margin-top:24px;">PAs ativas no {PJ2_CICLO_ATUAL}</div>
<div style="margin-top:32px;font-size:18px;color:var(--verde-claro);font-style:italic;line-height:1.5;max-width:60ch;">Primeiro ritual {PJ2_VERTICAIS_DISPLAY} — não há tasks no ClickUp ainda. Decisões de hoje virarão tasks na lista <strong style="color:var(--verde-caqui);">pa-resultado</strong>.</div>
</div></div>
{slide_foot("Bloco II · Status PA", 11)}</section>'''


def render_pa_lista(logo):
    return f'''<section>{slide_head("Bloco II · Plano de Ação", "Lista de PAs · próximos prazos", logo)}
<div class="slide-body" style="justify-content:center;align-items:center;">
<div style="background:var(--vc-50);border:2px dashed var(--vc-200);border-radius:8px;padding:60px 80px;text-align:center;max-width:900px;">
<div style="font-size:18px;color:var(--verde-claro);font-style:italic;line-height:1.5;max-width:60ch;">Lista vazia — nenhuma task {PJ2_VERTICAIS_DISPLAY} cadastrada.<br><br>Decisões deste ritual virarão tasks no ClickUp <strong style="color:var(--verde-caqui);">pa-resultado (lista 901326795742)</strong>.</div>
</div></div>
{slide_foot("Bloco II · Lista PAs", 12)}</section>'''


# ─── SLIDE 13/16 — DIRETO (11 inds, meta preenchida, riscos análise) ─
def dt_row(label, ind, kind, meta_total, field_value="n1_value", is_pct_field=False, direction="maior_melhor"):
    if not ind: ind = {}
    v = get(ind, field_value)
    cor = _ind_status(ind) if v is not None else "cinza"

    def fv(v):
        if v is None: return "—"
        if kind == "brl": return fmt_brl_short(v)
        if kind == "pct":
            if is_pct_field and v < 1: return fmt_pct(v*100, 1)
            return fmt_pct(v, 1)
        if kind == "int": return fmt_int(v)
        return fmt_n(v)

    def fm(v):
        if v is None: return "—"
        if kind == "brl": return fmt_brl_short(v)
        if kind == "pct": return fmt_pct(v*100, 1) if v < 1 else fmt_pct(v, 1)
        if kind == "int": return fmt_int(v)
        return fmt_n(v)

    # Pct atingimento INDEPENDENTE — sempre calcular do field_value vs meta_total
    if v is not None and meta_total not in (None, 0):
        pct = v / meta_total * 100; cor = cor_from_pct(pct, direction)
    elif direction == "menor_melhor" and v == 0:
        pct = 0.0; cor = "verde"
    elif field_value == "n1_value" and get(ind, "pct_atingimento") is not None:
        pct = get(ind, "pct_atingimento"); cor = cor_from_pct(pct, direction)
    else:
        pct = None
    pct_str = f'<span style="font-weight:600;font-size:15px;">{int(pct)}%</span><div class="pct">% atingimento</div>' if pct is not None else "—"
    return f'''<div class="dt-row"><div class="ind">{esc(label)}</div><div class="meta-v">{esc(fm(meta_total))}</div><div class="real {status_class(cor)}">{esc(fv(v))}</div><div class="desvio {status_class(cor)}">{pct_str}</div></div>'''


def gen_riscos_analise(data, vert):
    funil_ids = [
        "taxa_conversao_funil_seg" if vert == "seguros" else "taxa_conversao_funil_con",
        "oportunidades_criadas_funil_seg" if vert == "seguros" else "oportunidades_criadas_funil",
        "oportunidades_estagnadas_funil_seg" if vert == "seguros" else "oportunidades_estagnadas_funil",
        "oportunidades_sem_movimentacao_funil_seg" if vert == "seguros" else "oportunidades_sem_movimentacao_funil",
    ]
    riscos = []
    for ind_id in funil_ids:
        ind = data.get(ind_id) or {}
        cor = _ind_status(ind)
        if cor in ("vermelho", "amarelo"):
            pct = get(ind, "pct_atingimento")
            qty = get(ind, "n1_qty") or get(ind, "n1_value")
            pct_at = get(ind, "n1_pct_ativas")
            # S1-A1#5 (2026-05-15): causa_raiz_resumo do canonical (analyst E3).
            # Fallback graceful para texto generico legado quando ausente.
            causa_raiz = get(ind, "causa_raiz_resumo") or ""
            riscos.append({"id": ind_id, "cor": cor, "pct": pct, "qty": qty,
                           "pct_at": pct_at, "causa_raiz": causa_raiz})

    if not riscos: return '<div class="risk-item" style="border-left-color:var(--vc-200);"><em>Nenhum risco crítico identificado nos indicadores de funil.</em></div>'
    out = ""
    for r in riscos[:5]:
        ind_id = r["id"]
        # S1-A1#5: se canonical emitiu causa_raiz_resumo, usa como meta-texto;
        # caso contrario, mantem texto generico legado.
        meta_text_default = ""
        if "criadas" in ind_id:
            meta_text_default = "Cadência de SDRs precisa revisão · diagnóstico 1:1 com squad coordenador."
            headline = f'<strong>Originação fraca</strong> · {int(r["qty"] or 0)} criadas vs meta · {int(r["pct"] or 0)}% atingimento.'
        elif "estagnadas" in ind_id:
            meta_text_default = "Revisar aging por canal · descartar/avançar deals com 30+ dias parados."
            headline = f'<strong>Pipeline parado</strong> · {int(r["qty"] or 0)} deals estagnados ≥7d ({fmt_pct(r["pct_at"], 1)} das ativas).'
        elif "sem_movimentacao" in ind_id:
            meta_text_default = "Meta = 0 · acima de 40% é alarme operacional · plano de cadência semanal."
            headline = f'<strong>Cadência comercial</strong> · {int(r["qty"] or 0)} deals sem activity pendente ({fmt_pct(r["pct_at"], 1)} das ativas).'
        elif "taxa_conversao" in ind_id:
            v = get(data, ind_id, "n1_value") or 0
            meta_text_default = "Gargalo no stage de Proposta · revisar argumentação e aging por SDR."
            headline = f'<strong>Conversão abaixo</strong> · {fmt_pct(v*100, 1)} ({int(r["pct"] or 0)}% da meta).'
        else:
            continue
        meta_text = r.get("causa_raiz") or meta_text_default
        # 2026-06-12: subtexto nao-negrito (.ri-meta / causa-raiz) removido — espelho do N3 (Img 2)
        out += f'<div class="risk-item">{headline}</div>'
    return out


def render_direto(num, vert, wbr, card, logo):
    atual = get(wbr, "indicadores", "atual", default={})
    data = atual.get(vert, {})
    label_vert = "Seguros" if vert == "seguros" else "Consórcios"
    if vert == "seguros":
        rec, vol, qty = "receita_seguros_mensal","volume_seguros_mensal","quantidade_seguros_mensal"
        tx, cri = "taxa_conversao_funil_seg","oportunidades_criadas_funil_seg"
        ativ, est, semv = "oportunidades_ativas_funil_seg","oportunidades_estagnadas_funil_seg","oportunidades_sem_movimentacao_funil_seg"
    else:
        rec, vol, qty = "receita_consorcio_mensal","volume_consorcio_mensal","quantidade_consorcio_mensal"
        tx, cri = "taxa_conversao_funil_con","oportunidades_criadas_funil"
        ativ, est, semv = "oportunidades_ativas_funil","oportunidades_estagnadas_funil","oportunidades_sem_movimentacao_funil"

    def m(ind_id, key="valor"):
        mp = get(card, "metas_ppi", ind_id) or {}
        return mp.get(f"{key}_proximo_mes") or mp.get(key)

    kpi_rows = (
        dt_row("Receita Mensal", get(data,rec), "brl", m(rec)) +
        dt_row("Volume Mensal", get(data,vol), "brl", m(vol)) +
        dt_row("Quantidade", get(data,qty), "int", m(qty))
    )
    ppi_rows = (
        dt_row("Taxa de Conversão", get(data,tx), "pct", m(tx), is_pct_field=True) +
        dt_row("Oport. Ativas (qty)", get(data,ativ), "int", m(ativ, "qty"), field_value="n1_qty") +
        dt_row("Oport. Ativas (volume)", get(data,ativ), "brl", m(ativ, "volume"), field_value="n1_volume") +
        dt_row("Oport. Ativas (ticket)", get(data,ativ), "brl", m(ativ, "ticket_medio"), field_value="n1_ticket_medio") +
        dt_row("Oport. Criadas", get(data,cri), "int", get(card,"metas_ppi",cri,"qty_proximo_mes") or get(card,"metas_ppi",cri,"qty")) +
        dt_row("Oport. Estagnadas (qty)", get(data,est), "int", None, field_value="n1_qty") +
        dt_row("Oport. Estagnadas (% ativas)", get(data,est), "pct", 40, field_value="n1_pct_ativas", direction="menor_melhor") +
        dt_row("Sem Ativ. ou Atras. CRM", get(data,semv), "int", 0, field_value="n1_qty", direction="menor_melhor")
    )
    riscos = gen_riscos_analise(data, vert)

    return f'''<section>{slide_head(f"Bloco III · Direto {label_vert}", f"Direto {label_vert} · {PJ2_CICLO_ATUAL} (MTD)", logo, avatar="DS" if vert == "seguros" else "DC")}
<div class="slide-body"><div class="dash">
<div class="dash-table">
<div class="dt-head"><div>Indicador</div><div>Meta</div><div>Realizado</div><div>% Atingimento</div></div>
<div class="dt-section kpi">KPI · Indicadores de Resultado</div>{kpi_rows}
<div class="dt-section ppi">PPI · Indicadores de Funil</div>{ppi_rows}
</div>
<div class="risks-card">
<div class="rh">⚠ Top 5 Riscos · Análise dos Indicadores de Funil</div>
<div class="rb">{riscos}</div>
</div></div></div>
{slide_foot(f"Bloco III · Direto {label_vert}", num)}</section>'''


# ─── SLIDE 14/17 — Análise por Canal (listing assessor) ─────
def render_analise_canal(num, vert, wbr, card, asses_data, logo):
    label_vert = "Seguros" if vert == "seguros" else "Consórcios"
    # Lista assessor por squad — TODOS exceto hidden, com scroll interno
    rows_html = ""
    for canal_key, canal_label, css_cls in [("investimentos", "Squad Investimentos", "inv"), ("credito", "Squad Crédito", "cred"), ("outros_m7", "Outros M7", "outros")]:
        squad_full = get_squad_full_list(card, canal_key)
        assesores_canal = [(n, r) for n, r in asses_data.items() if r.get("canal") == canal_key]
        assesores_canal = filter_hidden(assesores_canal, card)  # remove hidden
        names_in_data = set(normalize_name(n) for n, _ in assesores_canal)
        for nm in squad_full:
            if normalize_name(nm) not in names_in_data:
                assesores_canal.append((nm, {}))
        # S1-A2 iter 8 (2026-05-17): ordem por CRIADAS DESC (sync default).
        # Quem criou mais fica em cima; demais cols (Ativas/Fechadas/Estagnadas)
        # mantem alinhamento na linha do assessor. Desempate: ativas DESC, nome ASC.
        assesores_canal.sort(key=lambda x: (
            -((x[1].get("criadas_atual", 0) or 0)),
            -((x[1].get("ativas_qty", 0) or 0)),
            (x[0] or "").lower(),
        ))
        rows_html += f'<div class="psq-head {css_cls}">{esc(canal_label)} · {len(assesores_canal)} assessores</div>'
        max_at = max([r.get("ativas_qty", 0) or 0 for _, r in assesores_canal] + [1])
        max_cri = max([r.get("criadas_atual", 0) or 0 for _, r in assesores_canal] + [1])
        max_est = max([r.get("estagnadas_qty", 0) or 0 for _, r in assesores_canal] + [1])
        max_fech = max([(r.get("won_atual", 0) or 0) + (r.get("lose_atual", 0) or 0) for _, r in assesores_canal] + [1])
        for nm, r in assesores_canal:  # TODOS (sem limite)
            at = r.get("ativas_qty", 0) or 0
            at_vol = r.get("ativas_vol", 0) or 0
            cri = r.get("criadas_atual", 0) or 0
            est = r.get("estagnadas_qty", 0) or 0
            won = r.get("won_atual", 0) or 0
            lose = r.get("lose_atual", 0) or 0

            nm_cls = "nm zero" if (at == 0 and cri == 0 and won == 0 and est == 0) else "nm"

            # Ativas cell: lime + (qty + vol abreviado)
            if at > 0:
                w = min(100, at / max_at * 100)
                ativas_lbl = f"{at} (R$ {int(at_vol/1000)}K)" if at_vol else f"{at}"
                ativas_cell = f'<div class="cn"><div class="mini"><div class="fb fb-lime" style="width:{w}%;">{ativas_lbl}</div></div></div>'
            else:
                ativas_cell = '<div class="cn"><div class="mini"><div class="fb fb-mute" style="width:0%;"></div></div></div>'

            # Criadas: lime (igual Ativas)
            if cri > 0:
                w = min(100, cri / max_cri * 100)
                cri_cell = f'<div class="cn"><div class="mini"><div class="fb fb-lime" style="width:{w}%;">{cri}</div></div></div>'
            else:
                cri_cell = '<div class="cn"><div class="mini"><div class="fb fb-mute" style="width:0%;"></div></div></div>'

            # Fechadas: dual W/L (igual slide 5/6)
            if won + lose > 0:
                wwon = (won / max_fech * 100) if won else 0
                wlose = (lose / max_fech * 100) if lose else 0
                fech_inner = ""
                if won: fech_inner += f'<div class="fb fb-good" style="width:{wwon}%;">{won}W</div>'
                if lose: fech_inner += f'<div class="fb fb-bad" style="width:{wlose}%;">{lose}L</div>'
                fech_cell = f'<div class="cn"><div class="mini">{fech_inner}</div></div>'
            else:
                fech_cell = '<div class="cn"><div class="mini"><div class="fb fb-mute" style="width:0%;"></div></div></div>'

            # Estagnadas: lime (mesma cor) + dias médios no label
            if est > 0:
                w = min(100, est / max_est * 100)
                dias_total = r.get("estagnadas_dias_total", 0) or 0
                dias_avg = int(dias_total / est) if est > 0 else 0
                est_cell = f'<div class="cn"><div class="mini"><div class="fb fb-lime" style="width:{w}%;">{est} ({dias_avg}d)</div></div></div>'
            else:
                est_cell = '<div class="cn"><div class="mini"><div class="fb fb-mute" style="width:0%;"></div></div></div>'

            rows_html += f'<div class="canal-row"><div class="{nm_cls}">{esc(nm)}</div>{ativas_cell}{cri_cell}{fech_cell}{est_cell}</div>'

    # Cards laterais
    atual = get(wbr, "indicadores", "atual", default={})
    data = atual.get(vert, {})
    if vert == "seguros":
        ativ_id, est_id, semv_id = "oportunidades_ativas_funil_seg", "oportunidades_estagnadas_funil_seg", "oportunidades_sem_movimentacao_funil_seg"
    else:
        ativ_id, est_id, semv_id = "oportunidades_ativas_funil", "oportunidades_estagnadas_funil", "oportunidades_sem_movimentacao_funil"

    # Concentração: top 2 assessores por volume ativo
    asses_list = sorted(asses_data.items(), key=lambda x: -(x[1].get("ativas_vol", 0) or 0))
    total_vol = sum(r.get("ativas_vol", 0) or 0 for _, r in asses_list)
    top2_vol = sum(r.get("ativas_vol", 0) or 0 for _, r in asses_list[:2])
    pct_top2 = (top2_vol / total_vol * 100) if total_vol > 0 else 0

    # Cobertura: assessores com ativas > 0
    cov_count = sum(1 for _, r in asses_list if (r.get("ativas_qty", 0) or 0) > 0)
    cov_total = sum(1 for nm in get_squad_full_list(card, "investimentos") + get_squad_full_list(card, "credito"))

    # Estagnação: tempo médio dias
    total_est = sum(r.get("estagnadas_qty", 0) or 0 for _, r in asses_list)
    total_dias = sum(r.get("estagnadas_dias_total", 0) or 0 for _, r in asses_list)
    avg_dias = (total_dias / total_est) if total_est > 0 else 0
    est_qty_n1 = get(data, est_id, "n1_qty") or 0
    pct_est = get(data, est_id, "n1_pct_ativas") or 0

    # Lista Oportunidades Atrasadas/Sem Atividade — proxy = estagnadas (exclui hidden)
    hidden_norm = get_hidden_names_norm(card)
    asses_problem = sorted(
        [(n, r) for n, r in asses_data.items()
         if (r.get("estagnadas_qty", 0) or 0) > 0 and normalize_name(n) not in hidden_norm],
        key=lambda x: -(x[1].get("estagnadas_qty", 0) or 0)
    )
    semv_items = ""
    for nm, r in asses_problem:
        est_q = r.get("estagnadas_qty", 0) or 0
        dias_total = r.get("estagnadas_dias_total", 0) or 0
        dias_avg = int(dias_total / est_q) if est_q > 0 else 0
        semv_items += f'<li><span class="dl-name">{esc(nm)}</span><span class="dl-qty">{est_q}</span><span class="dl-dias">{dias_avg}d média</span></li>'
    if not semv_items:
        semv_items = '<li><span class="dl-name" style="color:var(--verde-claro);font-style:italic;">Sem assessores com pipeline parado.</span><span></span><span></span></li>'

    side = f'''<div class="stat-card"><div class="sh">Concentração Volume Ativo</div><div class="sv warn">{int(pct_top2)}%</div><div class="sd">Top 2 assessores sustentam {int(pct_top2)}% do volume ativo · risco de concentração</div></div>
<div class="stat-card"><div class="sh">Cobertura Squad</div><div class="sv {'good' if cov_count >= cov_total*0.8 else 'warn'}">{cov_count} / {cov_total}</div><div class="sd">{cov_count} de {cov_total} assessores com deal ativo no funil</div></div>
<div class="stat-card"><div class="sh">Estagnação · Tempo Médio</div><div class="sv bad">{int(avg_dias)}d · {int(est_qty_n1)} deals</div><div class="sd">{int(pct_est)}% do pipeline estagnado · revisar aging por SDR/MKT</div></div>
<div class="stat-card list"><div class="sh">Oportunidades Atrasadas / Sem Atividade · por SDR/MKT</div><ul class="deal-list">{semv_items}</ul></div>'''

    return f'''<section class="esp-slide">{slide_head(f"Bloco III · Análise por Canal", f"Análise por Canal · {label_vert}", logo, avatar="AS" if vert == "seguros" else "AC")}
<div class="slide-body"><div class="analise-grid">
<div class="canal-card">
<div class="canal-head"><div>Assessor</div><div>Ativas</div><div>Criadas</div><div>Fechadas</div><div>Estagnadas</div></div>
<div class="canal-body">{rows_html}</div>
</div>
<div class="side-stats">{side}</div>
</div></div>
{slide_foot(f"Bloco III · Análise Canal {label_vert}", num)}</section>'''


# ─── SLIDE 15/18 — Pipeline (funil canônico) ──────────────────
def render_funnel_canonical(stages_data, stages_canonical):
    """Funil em ordem canônica (topo→base) estilo N3: centralizado, top verde, larguras proporcionais."""
    n = len(stages_canonical)
    h_per = 60
    svg_h = n * h_per + 40
    qtys = [(name, stages_data.get(name, {}).get("qty", 0) or 0) for _, name, _ in stages_canonical]
    top_name = max(qtys, key=lambda x: x[1])[0] if any(q for _, q in qtys) else None
    max_qty = max([q for _, q in qtys] + [1])

    bars = '<text x="680" y="22" style="font-size:10px;letter-spacing:0.12em;text-transform:uppercase;fill:var(--vc-300);" text-anchor="end">Deals · valor</text>'
    x_center = 360
    # Largura mínima pra acomodar TEXTO sempre (estimativa: 12px por char ~ 16-20 chars max)
    W_MIN_TEXT = 240
    for i, (sid, name, cycle_dias) in enumerate(stages_canonical):
        d = stages_data.get(name, {})
        q = d.get("qty", 0) or 0
        v = d.get("volume", 0) or 0
        # largura: sempre >= W_MIN_TEXT (240) pra acomodar texto, max 540
        if q == 0: w = W_MIN_TEXT
        else: w = max(W_MIN_TEXT, 540 * (q / max_qty))
        x = x_center - w / 2
        y = 30 + i * h_per
        is_top = (name == top_name and q > 0)
        if is_top: cor, opacity = "#2e7d32", "1"
        elif q == 0: cor, opacity = "#e8e8e4", "1"
        else:
            cor, opacity = "var(--vc-500)", f"{max(0.6, 1.0 - i*0.05):.2f}"
        bars += f'<g><polygon points="{x},{y} {x+w},{y} {x+w-5},{y+h_per-12} {x+5},{y+h_per-12}" fill="{cor}" opacity="{opacity}"/>'
        text_color = "#fff" if (is_top or q > 0) else "#79755c"
        sub_color = "rgba(255,255,255,0.85)" if is_top else ("rgba(255,253,239,0.7)" if q > 0 else "#79755c")
        bars += f'<text x="{x_center}" y="{y+h_per/2 - 5}" text-anchor="middle" fill="{text_color}" style="font-size:13px;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;">{esc(name)}</text>'
        bars += f'<text x="{x_center}" y="{y+h_per/2 + 11}" text-anchor="middle" fill="{sub_color}" style="font-size:11px;">~{cycle_dias}d para fechar</text>'
        deals_color = "#2e7d32" if is_top else "var(--verde-caqui)"
        deals_weight = "600" if is_top else "500"
        bars += f'<text x="650" y="{y+h_per/2 - 4}" style="font-size:18px;font-weight:{deals_weight};fill:{deals_color};">{int(q)} deals</text>'
        bars += f'<text x="650" y="{y+h_per/2 + 12}" style="font-size:12px;fill:var(--verde-claro);">{fmt_brl_short(v) if v else "—"}</text></g>'

    # Linhas de conexão entre stages
    for i in range(n - 1):
        y1 = 30 + i * h_per + h_per - 12
        y2 = 30 + (i + 1) * h_per
        bars += f'<line x1="{x_center}" y1="{y1}" x2="{x_center}" y2="{y2}" stroke="var(--vc-200)" stroke-dasharray="2,2" />'

    return f'<svg viewBox="0 0 720 {svg_h}" width="100%" height="100%" preserveAspectRatio="xMidYMid meet" style="display:block;flex-grow:1;">{bars}</svg>'


def render_pipeline(num, vert, wbr, card, logo):
    atual = get(wbr, "indicadores", "atual", default={})
    data = atual.get(vert, {})
    label_vert = "Seguros" if vert == "seguros" else "Consórcios"
    if vert == "seguros":
        ativ_id, est_id = "oportunidades_ativas_funil_seg","oportunidades_estagnadas_funil_seg"
        cri_id, tx_id, won_id = "oportunidades_criadas_funil_seg", "taxa_conversao_funil_seg", "quantidade_seguros_mensal"
        rec_id, vol_id = "receita_seguros_mensal","volume_seguros_mensal"
        stages_canonical = SEG_STAGES_ATIVO_ORDER
    else:
        ativ_id, est_id = "oportunidades_ativas_funil","oportunidades_estagnadas_funil"
        cri_id, tx_id, won_id = "oportunidades_criadas_funil", "taxa_conversao_funil_con", "quantidade_consorcio_mensal"
        rec_id, vol_id = "receita_consorcio_mensal","volume_consorcio_mensal"
        stages_canonical = CONS_STAGES_ATIVO_ORDER

    ativ = get(data, ativ_id) or {}
    est = get(data, est_id) or {}
    cri = get(data, cri_id) or {}
    tx = get(data, tx_id) or {}
    won = get(data, won_id) or {}
    stages_data = ativ.get("n2_estagio") or {}
    funnel_html = render_funnel_canonical(stages_data, stages_canonical)

    # 6 KPI tiles em cima
    qty_at = ativ.get("n1_qty") or 0
    vol_at = ativ.get("n1_volume") or 0
    ticket_at = ativ.get("n1_ticket_medio")
    qty_est = est.get("n1_qty") or 0
    qty_cri = cri.get("n1_value") or 0
    tx_n = tx.get("n1_value")
    kpi_html = f'''<div class="kpi-row">
<div class="kpi-tile"><div class="v">{int(qty_at)}</div><div class="l">Deals Ativos</div></div>
<div class="kpi-tile"><div class="v">{fmt_brl_short(vol_at)}</div><div class="l">Volume Ativo</div></div>
<div class="kpi-tile"><div class="v">{fmt_brl_short(ticket_at)}</div><div class="l">Ticket Médio</div></div>
<div class="kpi-tile"><div class="v {status_class(_ind_status(est))}">{int(qty_est)}</div><div class="l">Estagnados</div></div>
<div class="kpi-tile"><div class="v {status_class(_ind_status(cri))}">{int(qty_cri)}</div><div class="l">Opps Criadas</div></div>
<div class="kpi-tile"><div class="v {status_class(_ind_status(tx))}">{fmt_pct((tx_n or 0)*100, 0) if tx_n else "—"}</div><div class="l">Conv. Mês</div></div>
</div>'''

    # Identificar maior gargalo (stage com mais qty)
    if stages_data:
        gargalo = max(stages_data.items(), key=lambda x: x[1].get("qty", 0) or 0)
        gargalo_html = f'<div class="gargalo-line"><strong>Maior concentração:</strong> {esc(gargalo[0])} com {int(gargalo[1].get("qty", 0))} deals · {fmt_brl_short(gargalo[1].get("volume", 0))}</div>'
    else:
        gargalo_html = ""

    # Destaque + Estagnação
    top_stage_pair = max(stages_data.items(), key=lambda x: x[1].get("volume", 0) or 0) if stages_data else None
    top_vol = top_stage_pair[1].get("volume", 0) if top_stage_pair else 0
    total_vol = sum(s.get("volume", 0) or 0 for s in stages_data.values()) or 0
    top_pct = (top_vol / total_vol * 100) if total_vol > 0 else 0

    dest = f'''<div class="pipe-card-side"><div class="pcs-head dest">Destaque</div><div class="pcs-body">
<div><strong>Top stage:</strong> {esc(top_stage_pair[0]) if top_stage_pair else "—"} concentra {fmt_brl_short(top_vol)} ({int(top_pct)}% do volume ativo).</div>
<div style="font-size:11px;color:var(--verde-claro);margin-top:6px;">Volume total: {fmt_brl_short(total_vol)} · {int(ativ.get("n1_qty") or 0)} deals · ticket {fmt_brl_short(ativ.get("n1_ticket_medio"))}</div>
</div></div>'''

    estag = f'''<div class="pipe-card-side"><div class="pcs-head estag">Estagnação · ≥ 7 dias</div><div class="pcs-body">
<div style="font-size:24px;font-weight:600;color:var(--error);">{int(est.get("n1_qty") or 0)} deals</div>
<div>{fmt_brl_short(est.get("n1_volume"))} parados · {fmt_pct(est.get("n1_pct_ativas"), 1)} das ativas</div>
</div></div>'''

    # Projeção 3+3 barras
    proj = get(wbr, "projecoes", vert, default={})
    rec_real = get(data, rec_id, "n1_value") or 0
    vol_real = get(data, vol_id, "n1_value") or 0
    rec_meta = get(card, "metas_ppi", rec_id, "valor_proximo_mes") or get(card, "metas_ppi", rec_id, "valor") or 1
    vol_meta = get(card, "metas_ppi", vol_id, "valor_proximo_mes") or get(card, "metas_ppi", vol_id, "valor") or 1
    rec_M0 = get(proj, rec_id, "M0", "valor"); rec_M0_pct = get(proj, rec_id, "M0", "pct_meta")
    rec_M1 = get(proj, rec_id, "M+1", "valor"); rec_M1_pct = get(proj, rec_id, "M+1", "pct_meta")
    vol_M0 = get(proj, vol_id, "M0", "valor"); vol_M0_pct = get(proj, vol_id, "M0", "pct_meta")
    vol_M1 = get(proj, vol_id, "M+1", "valor"); vol_M1_pct = get(proj, vol_id, "M+1", "pct_meta")

    def pbar(top_label, val_str, pct):
        pct_w = max(0, min(100, pct or 0))
        fc = "#2e7d32" if (pct or 0) >= 95 else ("#d18000" if (pct or 0) >= 80 else "var(--error)")
        return f'<div class="proj-row"><div class="lbl"><strong>{esc(top_label)}</strong>{esc(val_str)}</div><div class="track"><div class="fill" style="width:{pct_w}%;background:{fc};"></div></div><div class="v"><strong>{int(pct or 0)}%</strong>meta</div></div>'

    # Ajustes PJ2 2026-05-11 Batch E #22: projecao M0 (Seg e Cons). M+1 reintroduzido
    # APENAS para Cons (decisao 2026-05-12) — Seg ainda sem metodo M+1 calibrado.
    rec_section = '<div class="proj-section-title">Receita</div>' + pbar("REAL", fmt_brl_short(rec_real), (rec_real/rec_meta*100)) + pbar("M0", fmt_brl_short(rec_M0), rec_M0_pct)
    vol_section = '<div class="proj-section-title" style="margin-top:6px;">Volume</div>' + pbar("REAL", fmt_brl_short(vol_real), (vol_real/vol_meta*100)) + pbar("M0", fmt_brl_short(vol_M0), vol_M0_pct)
    if vert == "consorcios" and rec_M1 is not None:
        rec_section += pbar("M+1", fmt_brl_short(rec_M1), rec_M1_pct)
    if vert == "consorcios" and vol_M1 is not None:
        vol_section += pbar("M+1", fmt_brl_short(vol_M1), vol_M1_pct)
    proj_html = f'''<div class="pipe-card-side"><div class="pcs-head proj">Projeção · {esc(label_vert)}</div><div class="proj-block">{rec_section}{vol_section}</div></div>'''

    return f'''<section class="esp-slide">{slide_head(f"Bloco III · Pipeline", f"{label_vert} · Funil + Projeção", logo, avatar="PS" if vert == "seguros" else "PC")}
<div class="slide-body" style="gap:14px;">
{kpi_html}
<div class="pipe-wrap">
<div class="funnel-card">
<div class="fnh"><span>Funil {esc(label_vert)} · estágios canônicos</span><span>SNAPSHOT {wbr.get("_snapshot_date","")}</span></div>
{funnel_html}
{gargalo_html}
</div>
<div class="pipe-side">{dest}{estag}{proj_html}</div>
</div></div>
{slide_foot(f"Bloco III · Pipeline {label_vert}", num)}</section>'''


# ─── SLIDE 19/20 — Consolidado ───────────────────────────────
def render_consolidado(num, vert, wbr, card, logo):
    atual = get(wbr, "indicadores", "atual", default={})
    data_a = atual.get(vert, {})
    label_vert = "Seguros" if vert == "seguros" else "Consórcios"
    if vert == "seguros":
        rec_id, vol_id, est_id = "receita_seguros_mensal","volume_seguros_mensal","oportunidades_estagnadas_funil_seg"
    else:
        rec_id, vol_id, est_id = "receita_consorcio_mensal","volume_consorcio_mensal","oportunidades_estagnadas_funil"

    rec_a = get(data_a, rec_id) or {}
    vol_a = get(data_a, vol_id) or {}
    est_a = get(data_a, est_id) or {}
    rec_meta = get(card, "metas_ppi", rec_id, "valor_proximo_mes") or get(card, "metas_ppi", rec_id, "valor")
    vol_meta = get(card, "metas_ppi", vol_id, "valor_proximo_mes") or get(card, "metas_ppi", vol_id, "valor")
    pct_rec = ((rec_a.get("n1_value") or 0) / rec_meta * 100) if rec_meta else 0
    pct_vol = ((vol_a.get("n1_value") or 0) / vol_meta * 100) if vol_meta else 0
    est_pct = est_a.get("n1_pct_ativas") or 0

    tiles = f'''<div class="consol-tile"><div class="v {status_class(_ind_status(rec_a))}">{fmt_brl_short(rec_a.get("n1_value"))}</div><div class="l">Receita {label_vert} · {int(pct_rec)}% meta</div></div>
<div class="consol-tile"><div class="v {status_class(_ind_status(vol_a))}">{fmt_brl_short(vol_a.get("n1_value"))}</div><div class="l">Volume {label_vert} · {int(pct_vol)}% meta</div></div>
<div class="consol-tile"><div class="v {status_class(_ind_status(est_a))}">{fmt_pct(est_pct, 1)}</div><div class="l">Estagnadas % · {int(est_pct)}% das ativas</div></div>'''

    n2_rec = rec_a.get("n2_agregado") or {}
    metas_canal_rec = derive_meta_canal(card, vert, rec_id, "atual")
    bars = ""
    for canal, lbl in [("investimentos", "Investimentos"), ("credito", "Crédito"), ("outros_m7", "Outros M7")]:
        v = n2_rec.get(canal, 0) or 0
        m = metas_canal_rec.get(canal)
        pct = (v / m * 100) if m else 0
        cor = "#2e7d32" if pct >= 95 else ("#d18000" if pct >= 80 else "var(--error)")
        meta_str = fmt_brl_short(m) if m else "sem meta"
        bars += f'''<div class="bar-row"><div class="lbl-l">{esc(lbl)}</div><div class="track"><div class="fill" style="width:{min(100,pct)}%;background:{cor};">{int(pct)}%</div></div><div class="vt">{fmt_brl_short(v)} / {meta_str}</div></div>'''
    cor_t = "#2e7d32" if pct_rec >= 95 else ("#d18000" if pct_rec >= 80 else "var(--error)")
    bars += f'''<div class="bar-row" style="border-top:2px solid var(--vc-200);padding-top:10px;margin-top:6px;font-weight:600;"><div class="lbl-l">{esc(label_vert)} consolidado</div><div class="track"><div class="fill" style="width:{int(min(100,pct_rec))}%;background:{cor_t};">{int(pct_rec)}%</div></div><div class="vt">{fmt_brl_short(rec_a.get("n1_value"))} / {fmt_brl_short(rec_meta)}</div></div>'''

    riscos = gen_riscos_analise(data_a, vert)
    proj = get(wbr, "projecoes", vert, default={})
    rec_M0 = get(proj, rec_id, "M0", "valor"); rec_M0_pct = get(proj, rec_id, "M0", "pct_meta")
    rec_M1 = get(proj, rec_id, "M+1", "valor"); rec_M1_pct = get(proj, rec_id, "M+1", "pct_meta")
    vol_M0 = get(proj, vol_id, "M0", "valor"); vol_M0_pct = get(proj, vol_id, "M0", "pct_meta")
    vol_M1 = get(proj, vol_id, "M+1", "valor"); vol_M1_pct = get(proj, vol_id, "M+1", "pct_meta")

    def pb(label_top, val_str, pct):
        pct_w = max(0, min(100, pct or 0))
        fc = "#2e7d32" if (pct or 0) >= 95 else ("#d18000" if (pct or 0) >= 80 else "var(--error)")
        return f'<div style="display:grid;grid-template-columns:160px 1fr 110px;gap:12px;align-items:center;font-size:13px;padding:6px 0;"><div style="color:var(--verde-caqui);">{esc(label_top)}</div><div style="background:#f0f0eb;height:18px;border-radius:3px;overflow:hidden;"><div style="height:100%;width:{pct_w}%;background:{fc};"></div></div><div style="text-align:right;font-weight:600;font-variant-numeric:tabular-nums;">{esc(val_str)}</div></div>'

    proj_rec_card = f'''<div class="card"><div class="card-head">Projeção Receita · {esc(label_vert)} consolidado</div><div class="card-body" style="gap:8px;">
{pb("Realizado MTD", fmt_brl_short(rec_a.get("n1_value")), pct_rec)}
{pb("Proj. M0 (Maio)", fmt_brl_short(rec_M0), rec_M0_pct)}
{pb("Proj. M+1 (Junho)", fmt_brl_short(rec_M1), rec_M1_pct) if vert == "consorcios" else ""}
<div style="font-size:11px;color:var(--verde-claro);padding-top:6px;border-top:1px dashed var(--vc-100);margin-top:4px;">Meta receita: M0 <strong style="color:var(--verde-caqui);">{fmt_brl_short(rec_meta)}</strong></div>
</div></div>'''

    proj_vol_card = f'''<div class="card"><div class="card-head">Projeção Volume · {esc(label_vert)} consolidado</div><div class="card-body" style="gap:8px;">
{pb("Realizado MTD", fmt_brl_short(vol_a.get("n1_value")), pct_vol)}
{pb("Proj. M0 (Maio)", fmt_brl_short(vol_M0), vol_M0_pct)}
{pb("Proj. M+1 (Junho)", fmt_brl_short(vol_M1), vol_M1_pct) if vert == "consorcios" else ""}
<div style="font-size:11px;color:var(--verde-claro);padding-top:6px;border-top:1px dashed var(--vc-100);margin-top:4px;">Meta volume: M0 <strong style="color:var(--verde-caqui);">{fmt_brl_short(vol_meta)}</strong></div>
</div></div>'''

    return f'''<section>{slide_head(f"Bloco IV · Consolidado", f"Síntese {label_vert} · {PJ2_CICLO_ATUAL} (MTD)", logo)}
<div class="slide-body">
<div style="display:grid;grid-template-columns:1fr 1fr;gap:24px;min-height:0;">
<div style="display:flex;flex-direction:column;gap:14px;">
<div class="consol-tiles">{tiles}</div>
<div class="card"><div class="card-head">Realizado por canal · MTD</div><div class="card-body" style="gap:6px;">{bars}</div></div>
</div>
<div style="display:flex;flex-direction:column;gap:14px;">
<div class="card"><div class="card-head error">Top 3 Riscos · Análise dos Indicadores de Funil</div><div class="card-body" style="gap:8px;">{riscos}</div></div>
</div>
</div>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:24px;flex-grow:1;min-height:0;">{proj_rec_card}{proj_vol_card}</div>
</div>
{slide_foot(f"Bloco IV · Consolidado {label_vert}", num)}</section>'''


# ─── SLIDE NPS Cons — pontual desta apresentacao (Batch D 2026-05-11) ────────
def render_nps_consorcio(num, logo):
    """Slide NPS Consorcio · {PJ2_CICLO_ATUAL}.

    One-off desta reuniao (12/05). Analise de 20 respostas da Pesquisa NPS Cons:
      NPS Score = %Promotores - %Detratores = 50% - 10% = 40
      Promotores (9-10): 10 / 20  (50%)
      Passivos (7-8):     8 / 20  (40%)
      Detratores (0-6):   2 / 20  (10%)

    Top 3 positivos: extraidos de promotores (notas 9-10)
    Top 3 negativos: extraidos de passivos+detratores (notas 6-8)

    Nao virara parte permanente do template PJ2 (Step 8 do plugin).
    """
    nps_score = 40  # 50% promotores - 10% detratores
    total = 20
    n_pro, n_pas, n_det = 10, 8, 2
    pct_pro = 50; pct_pas = 40; pct_det = 10

    # Top 3 positivos (categorias inferidas a partir das citacoes promotores 9-10)
    positivos = [
        ("Atendimento individual excelente",
         "Atendimento personalizado do Douglas, Sara (back office) e time de pós-venda — citações múltiplas de prontidão e relação direta",
         '“Sempre que precisei fui prontamente atendido” · “Douglas atende super rápido” · “Excelente atendimento”'),
        ("Agilidade na resolução de demandas",
         "Resposta rápida + retorno proativo quando informação não está disponível imediatamente",
         '“Agilidade na resolução das demandas” · “Se não tinha a informação, pouco depois ela chegava” · “Sempre que tem algum problema sou contactado pelo time”'),
        ("Time tecnicamente capacitado",
         "Competência reconhecida — Tereza/Douglas elogiados pelo conhecimento técnico do produto",
         '“Time de consórcio é bem estruturado e capacitado” · “Tereza tecnicamente é excelente” · “Todo o time faz um trabalho sensacional”'),
    ]
    # Top 3 negativos (categorias inferidas a partir das citacoes 6-8)
    negativos = [
        ("Apresentação comercial fraca",
         "Força de venda interna não consegue apresentar/converter — 4 menções diretas; gargalo de capacitação comercial",
         '“Comercial precisa melhorar apresentação do produto” · “Estamos errando na hora de apresentar” · “Falta uma atuação mais forte do comercial”'),
        ("Acesso difícil aos especialistas",
         "Disponibilidade restrita (Tereza nominalmente citada) + janela de telefone difícil (11:30-16h) — modelo de plantão sugerido por Cláudio",
         '“Tereza tecnicamente é excelente, mas muitas vezes difícil acesso” · “Contato via telefone complicado, de 11:30 até 16h é difícil”'),
        ("Falta divulgação ativa / iniciativas",
         "Sem fomento estruturado: ausência de checkup, palestras, comunicação de grupos ativos, boas-vindas pós-fechamento",
         '“Incluir consórcio no checkup financeiro” · “Aprimorar divulgação dos grupos ativos” · “Palestras sobre alavancagem” · “Enviar boas-vindas pós-fechamento”'),
    ]

    def card_html(idx, titulo, sintese, citacoes, tipo):
        cls = "nps-pos" if tipo == "pos" else "nps-neg"
        return f'''<div class="nps-card {cls}">
<div class="nps-card-num">{idx:02d}</div>
<div class="nps-card-body">
<div class="nps-card-tit">{esc(titulo)}</div>
<div class="nps-card-sint">{esc(sintese)}</div>
<div class="nps-card-cit">{citacoes}</div>
</div>
</div>'''

    pos_html = "".join(card_html(i+1, t, s, c, "pos") for i, (t, s, c) in enumerate(positivos))
    neg_html = "".join(card_html(i+1, t, s, c, "neg") for i, (t, s, c) in enumerate(negativos))

    # Correcao 2026-05-11 (REVIEW 3): NPS Score card centralizado em cima, Top 3s embaixo, textos maiores
    return f'''<section>{slide_head("Pesquisa NPS · {PJ2_CICLO_ATUAL}", "Voz do Comercial · Consórcio M7", logo, avatar="NP")}
<div class="slide-body"><div class="nps-wrap-v2">
<div class="nps-top">
<div class="nps-score-card">
<div class="nps-eyebrow">NPS Score</div>
<div class="nps-score">{nps_score}</div>
<div class="nps-formula">% Promotores − % Detratores<br><strong>{pct_pro}% − {pct_det}%</strong></div>
<div class="nps-breakdown">
<div class="nps-row pro"><span class="nps-dot"></span><span class="nps-lbl">Promotores · 9-10</span><span class="nps-val">{n_pro} <em>({pct_pro}%)</em></span></div>
<div class="nps-row pas"><span class="nps-dot"></span><span class="nps-lbl">Passivos · 7-8</span><span class="nps-val">{n_pas} <em>({pct_pas}%)</em></span></div>
<div class="nps-row det"><span class="nps-dot"></span><span class="nps-lbl">Detratores · 0-6</span><span class="nps-val">{n_det} <em>({pct_det}%)</em></span></div>
</div>
<div class="nps-base">Base: {total} respostas</div>
</div>
</div>
<div class="nps-cols-v2">
<div class="nps-col">
<div class="nps-col-head pos">Top 3 · Pontos positivos</div>
{pos_html}
</div>
<div class="nps-col">
<div class="nps-col-head neg">Top 3 · Pontos de atenção</div>
{neg_html}
</div>
</div>
</div></div>
{slide_foot("Bloco II · NPS Consórcio", num)}</section>'''


# ─── SLIDE Análise do que deu errado (Batch C #12 — slide DEDICADO) ──────────
# Correcao 2026-05-11 #12 (REVIEW 2): cada indicador VERMELHO tem analise dedicada.
# Iteramos sobre TODOS os indicators do fech_vertical (6 KPIs por vertical) e geramos
# 1 card por indicador em vermelho, com causa-raiz textual contextualizada.
def render_analise_problemas(wbr, card, logo, num=8):
    """Slide 'Análise do que deu errado' — substitui o slide Diretrizes removido.

    Layout: 2 colunas (Seg + Cons). Para cada vertical, lista os indicadores
    vermelhos do fechamento (Volume/Receita/Quantidade/Ticket/Tx Conv/Criadas/
    Tempo Ciclo/Estagnação) com análise causal específica por tipo de indicador.
    """
    fech = get(wbr, "indicadores", "fechamento", default={})

    def get_pct_n1(ind, meta_val, kind="brl"):
        """Retorna pct atingimento ou None."""
        v = get(ind, "n1_value") if get(ind, "n1_value") is not None else get(ind, "n1_qty")
        if v is None or not meta_val:
            return v, None
        return v, (v / meta_val * 100) if kind != "menor" else (meta_val / v * 100 if v > 0 else None)

    def vermelho(pct, direction="maior"):
        if pct is None: return False
        return (pct < 80) if direction == "maior" else (pct > 100)

    def diag_card(titulo, valor_str, meta_str, pct, racional):
        # Design image 1: titulo+vals à esquerda, pct GRANDE à direita, racional embaixo após divider
        return f'''<div class="prob-card">
<div class="prob-card-head">
<div class="prob-card-head-left">
<div class="prob-card-tit">{esc(titulo)}</div>
<div class="prob-card-vals"><strong>{esc(valor_str)}</strong> <span class="vs-meta">vs meta {esc(meta_str)}</span></div>
</div>
<div class="prob-card-pct">{int(pct) if pct else "—"}<span class="pct-mark">%</span></div>
</div>
<div class="prob-card-divider"></div>
<div class="prob-card-txt">{racional}</div>
</div>'''

    def causa_raiz_html(vert):
        data = fech.get(vert, {})
        label_vert = "Seguros · Empresarial e Vida" if vert == "seguros" else "Consórcios"

        # Mapeamento indicators do fech_vertical
        if vert == "seguros":
            ind_specs = [
                ("Receita", "receita_seguros_mensal", "brl", "valor", "Receita ficou aquém da meta. Diagnóstico provável: ticket médio baixo ou poucos fechamentos. Cruzar com volume + quantidade para identificar driver."),
                ("Volume (prêmio líquido)", "volume_seguros_mensal", "brl", "valor", "Volume novo abaixo do esperado. Mix de produtos pode ter caído (mais Vida e menos Empresarial). Validar mix com Joel."),
                ("Apólices Fechadas", "quantidade_seguros_mensal", "qty", "qty", "Volume de novas apólices abaixo. Cruzar com Oport. Criadas: se criação OK, gargalo é conversão; se baixa, é originação."),
                ("Ticket Médio", "ticket_medio_premio_seg", "brl", "valor", "Ticket médio baixo puxando receita pra baixo. Possíveis causas: mix de produto mudou, perda de big tickets, ou cotação via carta de nomeação (vide ata 04/05)."),
                ("Tx Conversão CRM", "taxa_conversao_funil_seg", "pct", "valor", "Conversão abaixo da meta de 25%. Gargalo no estágio de Proposta / argumentação. Revisar follow-up e cadência por SDR."),
                ("Oport. Criadas CRM", "oportunidades_criadas_funil_seg", "qty", "qty", "Pipeline de novas oportunidades insuficiente. Diagnóstico: hot-list semanal não está fluindo. Validar atuação dos especialistas no salão (vide ata 04/05)."),
                ("Tempo de Ciclo CRM", "tempo_de_ciclo_funil_seg", "qty", None, "Ciclo longo entre criação e fechamento. Deals demorando — possível indecisão de cliente ou cotação via terceiros (Cléo destacou na N2)."),
                ("Estagnação Mediana CRM", "estagnacao_mediana_pct_ativas_seg", "menor_pct", None, "Alta % de ativas estagnadas. Pipeline com deals sem cadência. Necessário descarte ou avanço de aging (>30d)."),
            ]
        else:
            ind_specs = [
                ("Receita", "receita_consorcio_mensal", "brl", "valor", "Receita Cons abaixo da meta. Comissão depende de contratos novos + lagging das parcelas. Validar mix de consorciadoras (cada uma tem comissão diferente)."),
                ("Volume Carta", "volume_consorcio_mensal", "brl", "valor", "Volume de novas cartas insuficiente. Sem volume novo, receita futura cai (lag 1-3 meses). Crítico."),
                ("Contratos Fechados", "quantidade_consorcio_mensal", "qty", "qty", "Quantidade de novas cartas abaixo. Cruzar com Tx Conversão: se conversão OK, é originação; se baixa, é argumentação."),
                ("Ticket Médio", "ticket_medio_consorcio_mensal", "brl", "valor", "Ticket Cons baixo. Mix de produto cartões pequenos > imobiliário comercial. Validar se há venda B2B (Alta Renda/Corporate) abaixo do esperado."),
                ("Tx Conversão CRM", "taxa_conversao_funil_con", "pct", "valor", "Conversão Cons abaixo de 25%. Ciclo médio de ~19 dias — se Tx baixa, gargalo está em Proposta ou follow-up. Revisar pipeline de propostas pendentes."),
                ("Oport. Criadas CRM", "oportunidades_criadas_funil", "qty", "qty", "Criação Cons insuficiente. Concentração na boca do funil em poucos assessores (vide N2 04/05). Necessário plano de prospecção semanal."),
                ("Tempo de Ciclo CRM", "tempo_de_ciclo_funil_con", "qty", None, "Ciclo Cons elevado. Validar Deal History dos contratos fechados — etapa que demora mais. Cuidado: deals direto (<2d) incluídos."),
                ("Estagnação Mediana CRM", "estagnacao_mediana_pct_ativas_con", "menor_pct", None, "Pipeline Cons com alta estagnação. Cartas paradas em Proposta > 7d. Limpar pipeline ou avançar com follow-up agressivo."),
            ]

        metas_ppi = card.get("metas_ppi", {}) or {}
        cards_html_list = []
        for titulo, ind_id, kind, meta_key, racional in ind_specs:
            ind = get(data, ind_id) or {}
            v = get(ind, "n1_value")
            if v is None: v = get(ind, "n1_qty")
            if v is None: continue
            # Meta
            if meta_key is None:
                meta_val = None
            else:
                meta_val = (metas_ppi.get(ind_id) or {}).get(meta_key)
            # Hard-coded meta para estagnação (40%)
            if "estagnacao" in ind_id:
                meta_val = 0.40
            # Pct
            if meta_val and v:
                if kind == "menor_pct":  # estagnação menor melhor
                    pct = meta_val / v * 100  # meta/realizado (quanto MAIS realizado, MENOR o pct)
                    is_red = (v > meta_val)
                else:
                    pct = v / meta_val * 100
                    is_red = pct < 80
            else:
                pct = None
                is_red = False
            if not is_red:
                continue
            # Format value
            if kind == "brl":
                valor_str = fmt_brl_short(v)
                meta_str = fmt_brl_short(meta_val) if meta_val else "sem meta"
            elif kind == "qty":
                valor_str = fmt_int(v)
                meta_str = fmt_int(meta_val) if meta_val else "sem meta"
            elif kind in ("pct", "menor_pct"):
                valor_str = fmt_pct(v * 100 if v <= 1 else v, 1)
                meta_str = fmt_pct(meta_val * 100 if meta_val and meta_val <= 1 else (meta_val or 0), 1) if meta_val else "sem meta"
            else:
                valor_str = fmt_n(v)
                meta_str = fmt_n(meta_val) if meta_val else "sem meta"
            # 2026-06-03 (port deck-normal): preferir causa-raiz REAL do canonical
            # (analyst E3 emite `causa_raiz_resumo`); fallback no racional hardcoded.
            racional_final = get(ind, "causa_raiz_resumo") or racional
            cards_html_list.append(diag_card(titulo, valor_str, meta_str, pct, racional_final))

        if not cards_html_list:
            cards_html_list.append(
                '<div class="prob-card prob-card-ok"><div class="prob-card-tit">Sem lead indicators críticos</div><div class="prob-card-txt">Todos os indicadores PPI dentro de margens aceitáveis. Manter cadência atual.</div></div>'
            )
        cards_html = "".join(cards_html_list)
        return f'''<div class="prob-vert"><div class="prob-vert-head {"seg" if vert == "seguros" else "cons"}">{esc(label_vert)}</div><div class="prob-vert-list">{cards_html}</div></div>'''

    return f'''<section>{slide_head("Bloco I · Análise do que deu errado", "Indicadores em alerta", logo)}
<div class="slide-body">
<div class="prob-headline"><span class="ch-eyebrow">Causa-raiz dos lead indicators em vermelho</span>Leitura crítica dos indicadores que ficaram abaixo da meta — <em>diagnóstico por causa-raiz</em> em vez de diretriz prescritiva.</div>
<div class="prob-grid">
{causa_raiz_html("seguros")}
{causa_raiz_html("consorcios")}
</div>
</div>
{slide_foot("Bloco I · Análise do que deu errado", num)}</section>'''


# ─── Helper: gauge SVG semicircular (Batch E 2026-05-11) ─────
def _gauge_svg(pct, cor_hex):
    """Renderiza gauge SVG semicircular (image 3 referencia).

    Args:
        pct: percentual 0-100+ (cap visual em 100; texto mostra valor real).
        cor_hex: cor do arco preenchido em hex.

    Returns: SVG inline para uso dentro do card .veloc.
    """
    import math
    p = max(min(pct or 0, 100), 0)  # cap visual 0-100
    radius = 78
    cx, cy = 100, 100
    angle = 180 + (p * 1.8)
    rad = math.radians(angle)
    x_end = cx + radius * math.cos(rad)
    y_end = cy + radius * math.sin(rad)
    bg_path = f"M {cx-radius} {cy} A {radius} {radius} 0 0 1 {cx+radius} {cy}"
    fill_path = f"M {cx-radius} {cy} A {radius} {radius} 0 0 1 {x_end:.2f} {y_end:.2f}"
    return f'''<svg viewBox="0 0 200 115" class="gauge-svg" preserveAspectRatio="xMidYMid meet">
<path d="{bg_path}" stroke="#e8e8e0" stroke-width="16" stroke-linecap="round" fill="none"/>
<path d="{fill_path}" stroke="{cor_hex}" stroke-width="16" stroke-linecap="round" fill="none"/>
</svg>'''


# ─── SLIDE Final — Conclusao com 3 velocimetros (Receita) ────────────────────
# Ajustes PJ2 2026-05-11 Batch E #21: substitui "Proximos Passos" (render_encerramento)
# Spec Bruno 11/05: 3 velocimetros mostrando proj M0 de Receita — Seg, Cons, Total PJ2.
def render_conclusao_velocimetros(wbr, card, logo, num):
    """Slide Conclusao com 3 velocimetros (image 3 referencia).

    PJ2: Velocimetro 1 (Seguros) | Velocimetro 2 (Consorcios) | Velocimetro 3 (Total PJ2 Receita).
    Apenas RECEITA conforme spec. M0 (mes corrente). M1 fica para depois.
    """
    atual = get(wbr, "indicadores", "atual", default={})
    proj = get(wbr, "projecoes", default={})

    def vert_data(vert, rec_id):
        # Correcao 2026-05-11 (REVIEW 4): meta deve ser valor_proximo_mes (M0 = mes corrente Maio),
        # nao .valor (que e a meta de abril). Alinhar com pct_meta da projecao WBR.
        ind = get(atual, vert, rec_id) or {}
        real = get(ind, "n1_value") or 0
        meta_ppi = (get(card, "metas_ppi", rec_id) or {})
        meta = meta_ppi.get("valor_proximo_mes") or meta_ppi.get("valor") or 0
        # Projecao M0 se houver, senao usa realizado MTD
        proj_m0 = get(proj, vert, rec_id, "M0", "valor")
        proj_pct = get(proj, vert, rec_id, "M0", "pct_meta")
        if proj_m0 is None:
            proj_m0 = real
            proj_pct = (real / meta * 100) if meta else 0
        return {"real": real, "meta": meta, "proj_m0": proj_m0, "proj_pct": proj_pct or 0}

    seg = vert_data("seguros", "receita_seguros_mensal")
    cons = vert_data("consorcios", "receita_consorcio_mensal")
    # Total PJ2 = soma Seg + Cons (somente Receita por spec)
    total_real = (seg["real"] or 0) + (cons["real"] or 0)
    total_meta = (seg["meta"] or 0) + (cons["meta"] or 0)
    total_proj = (seg["proj_m0"] or 0) + (cons["proj_m0"] or 0)
    total_pct = (total_proj / total_meta * 100) if total_meta else 0

    def cor_for(pct):
        if pct >= 95: return "#4caf50"
        if pct >= 80: return "#ffb300"
        return "#e40014"

    # Correcao 2026-05-11 #22+#24 (REVIEW 2): fill = projeção M0 (não realizado), título grande, estilo Próximos Passos
    def card_html(idx, label, sublabel, real_v, meta_v, proj_v, pct):
        cor = cor_for(pct)
        # gauge agora reflete projeção M0 atingimento (proj/meta), não realizado/meta
        return f'''<div class="veloc">
<div class="veloc-num">{idx:02d}</div>
<div class="veloc-head"><div class="veloc-lbl">{esc(label)}</div><div class="veloc-sub">{esc(sublabel)}</div></div>
<div class="veloc-gauge-wrap">{_gauge_svg(pct, cor)}<div class="veloc-pct" style="color:{cor};">{int(pct)}<span class="pct-mark">%</span></div></div>
<div class="veloc-vals">
<div class="veloc-side veloc-real"><div class="vside-lbl">Projeção M0</div><div class="vside-val">{fmt_brl_short(proj_v)}</div></div>
<div class="veloc-side veloc-meta"><div class="vside-lbl">Meta M0</div><div class="vside-val">{fmt_brl_short(meta_v)}</div></div>
</div>
<div class="veloc-proj">Realizado MTD · <strong>{fmt_brl_short(real_v)}</strong></div>
</div>'''

    veloc_seg = card_html(1, "Receita Seguros", "Empresarial + Vida", seg["real"], seg["meta"], seg["proj_m0"], seg["proj_pct"])
    veloc_cons = card_html(2, "Receita Consórcios", "Cartas + Recorrência", cons["real"], cons["meta"], cons["proj_m0"], cons["proj_pct"])
    veloc_total = card_html(3, "Total · Receita", "Seguros + Consórcios consolidado", total_real, total_meta, total_proj, total_pct)

    leitura = (f"{PJ2_VERTICAIS_DISPLAY} projeta <strong>{int(total_pct)}% da meta de Receita</strong> em Maio (M0) — "
               f"Seg em <strong>{int(seg['proj_pct'])}%</strong>, Cons em <strong>{int(cons['proj_pct'])}%</strong>.")

    return f'''<section class="conc-slide">{slide_head("Conclusão · Projeção M0 Receita {PJ2_CICLO_ATUAL}", "Conclusão · 3 velocímetros", logo)}
<div class="slide-body">
<div class="conc-headline"><span class="ch-eyebrow">Síntese de fechamento do mês corrente</span>{leitura}</div>
<div class="veloc-grid">
{veloc_seg}
{veloc_cons}
{veloc_total}
</div>
</div>
{slide_foot("Bloco V · Conclusão", num)}</section>'''


# ─── SLIDE Encerramento legado (Próximos Passos) — DEPRECATED 2026-05-11 Batch E
# Substituido por render_conclusao_velocimetros acima. Mantido como fallback se necessario.
def render_encerramento(wbr, logo):
    """Encerramento dinâmico: 3 cards de próximos passos baseados nos desvios."""
    ad = get(wbr, "analise_desvios") or {}
    leitura = get(ad, "cross_vertical", "receita_fechamento", "leitura") or ""

    # Coletar top desvios e contexto pra gerar próximos passos
    atual = get(wbr, "indicadores", "atual", default={})
    fech = get(wbr, "indicadores", "fechamento", default={})

    # 1. Maior risco do MÊS ATUAL (vermelho com pior pct)
    vermelhos_atual = []
    for vert, inds in atual.items():
        if not isinstance(inds, dict): continue
        for ind_id, ind in inds.items():
            if isinstance(ind, dict) and _ind_status(ind) == "vermelho":
                pct = get(ind, "pct_atingimento")
                if pct is not None and ind_id in (
                    "receita_consorcio_mensal", "receita_seguros_mensal",
                    "volume_consorcio_mensal", "volume_seguros_mensal"):
                    vermelhos_atual.append((vert, ind_id, pct, ind))
    vermelhos_atual.sort(key=lambda x: x[2])

    # 2. Sem Movimentação (Cons + Seg)
    semv_cons_n1 = get(atual, "consorcios", "oportunidades_sem_movimentacao_funil", "n1_qty") or 0
    semv_seg_n1 = get(atual, "seguros", "oportunidades_sem_movimentacao_funil_seg", "n1_qty") or 0

    # 3. Estagnadas %
    est_cons_pct = get(atual, "consorcios", "oportunidades_estagnadas_funil", "n1_pct_ativas") or 0
    est_seg_pct = get(atual, "seguros", "oportunidades_estagnadas_funil_seg", "n1_pct_ativas") or 0

    proxs = []
    # Card 1: maior gap de receita/volume
    if vermelhos_atual:
        vert, ind_id, pct, ind = vermelhos_atual[0]
        nome = "Receita" if "receita" in ind_id else "Volume"
        vert_lbl = "Seguros" if vert == "seguros" else "Consórcios"
        proxs.append({
            "titulo": f"Fechar gap {nome} {vert_lbl} · {int(pct)}% da meta",
            "acao": f"Joel conduz revisão 1:1 com squad coordenador. Plano de retomada e contramedidas até 19/05.",
            "owner": "Joel Freitas",
            "prazo": "1 semana",
        })

    # Card 2: cadência (Sem Movimentação)
    if (semv_cons_n1 + semv_seg_n1) > 0:
        total_semv = int(semv_cons_n1 + semv_seg_n1)
        proxs.append({
            "titulo": f"Reativar cadência · {total_semv} deals sem atividade",
            "acao": f"Cons {int(semv_cons_n1)} · Seg {int(semv_seg_n1)} sem activity pendente. Cadência semanal por SDR. Meta zerar até 31/05.",
            "owner": "SDRs + Coordenador",
            "prazo": "3 semanas",
        })

    # Card 3: estagnação pipeline
    pior_est = max(est_cons_pct, est_seg_pct)
    if pior_est > 30:
        vert_est = "Consórcios" if est_cons_pct > est_seg_pct else "Seguros"
        proxs.append({
            "titulo": f"Limpar pipeline {vert_est} · {int(pior_est)}% estagnado",
            "acao": "Revisão de aging por canal. Descartar ou avançar deals com 30+ dias parados. Validar com squad.",
            "owner": "Especialistas + SDRs",
            "prazo": "2 semanas",
        })

    # Default se nada urgente
    if not proxs:
        proxs.append({"titulo": "Manter cadência atual", "acao": "Ciclo dentro do esperado. Acompanhar evolução semanal.", "owner": "Joel Freitas", "prazo": "ciclo normal"})

    while len(proxs) < 3:
        proxs.append({"titulo": "Reservado", "acao": "Espaço para nova ação a definir no ritual.", "owner": "—", "prazo": "—"})

    cards_html = ""
    for i, p in enumerate(proxs[:3], 1):
        cards_html += f'''<div class="next-card">
<div class="nc-num">{i:02d}</div>
<div class="nc-title">{esc(p["titulo"])}</div>
<div class="nc-meta">
<div><div class="k">Ação</div><div class="v">{esc(p["acao"])}</div></div>
<div><div class="k">Owner · Prazo</div><div class="v"><strong>{esc(p["owner"])}</strong> · {esc(p["prazo"])}</div></div>
</div></div>'''

    # Resumo executivo no header
    resumo_top = leitura or "Ritual de manutenção · Acompanhar evolução dos indicadores na próxima cadência."

    return f'''<section class="closing"><div class="closing-inner">
<div class="head-row"><div>
<div style="display:flex;align-items:center;gap:20px;margin-bottom:24px;"><div style="width:48px;height:3px;background:var(--lime);"></div>
<span style="font-size:14px;letter-spacing:0.24em;text-transform:uppercase;color:var(--lime);font-weight:500;">Bloco V · Encerramento · {PJ2_CICLO_ATUAL}</span></div>
<h2>Próximos <em>passos</em></h2>
<div style="color:var(--verde-claro);font-size:20px;margin-top:18px;max-width:70ch;line-height:1.5;">{esc(resumo_top)}</div>
</div><img class="logo" src="data:image/png;base64,{logo}" alt="M7" style="height:36px;"></div>
<div class="next-grid">{cards_html}</div>
<div class="closing-foot"><div><strong>Ritual N2 {PJ2_VERTICAIS_DISPLAY}</strong> · M7 Investimentos</div><div>Próximo ritual: 12/06/2026 · Joel Freitas</div></div>
</div></section>'''


# ─── MAIN ────────────────────────────────────────────────────
def main():
    p = argparse.ArgumentParser()
    p.add_argument("--wbr-data-json", required=True, type=Path)
    p.add_argument("--card", required=True, type=Path)
    p.add_argument("--modo", default="combinado")
    p.add_argument("--output", required=True, type=Path)
    # Args adicionais aceitas via dispatch do build_deck.py (algumas ignoradas, outras opcionais):
    p.add_argument("--skill-dir", type=Path, default=None,
                   help="Plugin skill dir (auto-detected from __file__ se omitido)")
    p.add_argument("--clickup-tasks", type=Path, default=None,
                   help="JSON de tasks ClickUp (filter composto Sessao 5)")
    p.add_argument("--action-report", type=Path, default=None,
                   help="action-report.md de E4 (contexto narrativo Slide 5)")
    p.add_argument("--dados-consolidados", type=Path, default=None,
                   help="JSON consolidado N5 de E2 (drill por canal)")
    p.add_argument("--prev-wbr-data-json", type=Path, default=None,
                   help="WBR canonical do ciclo anterior (delta MoM)")
    p.add_argument("--per-assessor-csv-dir", type=Path, default=None,
                   help="Diretorio com dumps Bitrix offline (V13 workaround)")
    args = p.parse_args()
    # Override SKILL_DIR e PLUGIN_ASSETS se passado via CLI
    if args.skill_dir:
        global SKILL_DIR, PLUGIN_ASSETS
        SKILL_DIR = args.skill_dir
        PLUGIN_ASSETS = SKILL_DIR / "templates" / "assets"

    print("[build_pj2_deck] reading WBR + Card...")
    wbr = json.loads(args.wbr_data_json.read_text(encoding="utf-8"))
    card = yaml.safe_load(args.card.read_text(encoding="utf-8"))

    # Fase 4.6 (2026-06-16): se o canonical foi injetado com metas por canal da
    # tabela ciclo_metas_ppi, as funcoes derive_meta_* passam a preferi-las.
    global _WBR_CANON
    _WBR_CANON = wbr

    # Step 8 hardcodes refactor (2026-05-12): resolver globals PJ2_* a partir de Card + WBR
    # S1-A1#2 (2026-05-15): args propagado para resolver PJ2_EFFECTIVE_MODO via --modo
    _resolve_pj2_globals(card, wbr, args=args)
    print(f"[build_pj2_deck] PJ2_VERTICAIS_DISPLAY={PJ2_VERTICAIS_DISPLAY!r}")
    print(f"[build_pj2_deck] PJ2_CICLO_ATUAL={PJ2_CICLO_ATUAL!r} | PJ2_CICLO_FECHAMENTO={PJ2_CICLO_FECHAMENTO!r}")
    print(f"[build_pj2_deck] PJ2_COORDENADOR={PJ2_COORDENADOR!r}")
    print(f"[build_pj2_deck] PJ2_EFFECTIVE_MODO={PJ2_EFFECTIVE_MODO!r} | PJ2_DATA_FECHAMENTO_DISPLAY={PJ2_DATA_FECHAMENTO_DISPLAY!r}")

    print("[build_pj2_deck] extracting per-assessor data from dump...")
    asses_seg = extract_per_assessor_seg(card)
    asses_cons = extract_per_assessor_cons(card)
    print(f"  Seg: {len(asses_seg)} assessores | Cons: {len(asses_cons)} MKTs")

    # Injetar pct_ativas Estagnadas POR CANAL no WBR — usa n2_agregado_qty do WBR
    # (mesma fonte exibida na matriz) para coerencia.
    # Correcao 2026-05-12: anteriormente usava asses_data, mas asses_data classifica
    # por MKT/SDR (Bitrix-only via classify_assessor) enquanto a matriz mostra
    # n2_agregado_qty que vem da CTE de canal (centro_custo Cons / nome_assessor Seg
    # + fallback ASSIGNED). Pra Cons Cred: asses_data tinha 3/3 (100%); n2_agregado
    # tem 13/10 (77%) — usuario validou os 77% como correto.
    def inject_pct_estagnadas_canal(vert_key):
        atual = wbr.get("indicadores", {}).get("atual", {}).get(vert_key, {})
        ativ_id = "oportunidades_ativas_funil_seg" if vert_key == "seguros" else "oportunidades_ativas_funil"
        est_id = "oportunidades_estagnadas_funil_seg" if vert_key == "seguros" else "oportunidades_estagnadas_funil"
        if est_id not in atual or ativ_id not in atual: return
        ativ_n2 = (atual[ativ_id].get("n2_agregado_qty") or {})
        est_n2 = (atual[est_id].get("n2_agregado_qty") or {})
        pct_canal = {}
        for c in ["investimentos", "credito", "outros_m7"]:
            a = ativ_n2.get(c) or 0
            e = est_n2.get(c) or 0
            if a > 0:
                pct_canal[c] = e / a * 100
            elif e == 0:
                pct_canal[c] = 0.0  # 0 estagnadas e 0 ativas = 0% (verde)
            else:
                pct_canal[c] = None
        atual[est_id]["pct_canal_ativas"] = pct_canal

    inject_pct_estagnadas_canal("seguros")
    inject_pct_estagnadas_canal("consorcios")

    fonts = {
        "ASSET_FONT_REGULAR_B64": load_b64("twk-everett-regular.b64"),
        "ASSET_FONT_MEDIUM_B64": load_b64("twk-everett-medium.b64"),
        "ASSET_FONT_BOLD_B64": load_b64("twk-everett-bold.b64"),
        "ASSET_FONT_LIGHT_B64": load_b64("twk-everett-light.b64"),
        "ASSET_FONT_ULTRALIGHT_B64": load_b64("twk-everett-ultralight.b64"),
    }
    logo = load_b64("m7-logo-offwhite.b64")
    css = CSS_BASE
    for k, v in fonts.items():
        css = css.replace("{" + k + "}", v)

    ciclo = f"{wbr.get('periodo_fechamento','')} · {wbr.get('data_referencia','')}"

    # Ajustes PJ2 2026-05-11 (Batch A):
    #  - Removidos slides: PA Status, PA Lista (ciclo novo sem PAs), Direto Seg, Direto Cons (duplica Matriz)
    #  - Reordenado: vertical-por-vertical (Matriz Seg → Analise Seg → Pipeline Seg → Matriz Cons → Analise Cons → Pipeline Cons)
    #  - Consolidados ficam no final (Seg, Cons) antes da Conclusao
    slides = [
        render_capa(card, ciclo, logo),
        render_agenda(logo),
        # Correcao 2026-05-11 #1 (REVIEW USUARIO): Recap virou slide separado APOS a Agenda
        render_recap_ultima_n2(logo, num=3),
        render_subcapa(4, "Bloco I", "Fechamento mês", "passado", "Visão geral {PJ2_VERTICAIS_DISPLAY} + detalhado por vertical (8 indicadores)", ciclo, logo, "Bloco I · Fechamento"),
        render_fech_visao_geral(wbr, card, logo, asses_seg=asses_seg, asses_cons=asses_cons),
        render_fech_vertical(6, "seguros", wbr, card, asses_seg, logo),
        render_fech_vertical(7, "consorcios", wbr, card, asses_cons, logo),
        # Correcao 2026-05-11 #12 (REVIEW USUARIO): slide DEDICADO "Analise do que deu errado"
        render_analise_problemas(wbr, card, logo, num=8),
        render_subcapa(9, "Bloco II", "Mês até", "agora", "Matrizes + Análise por canal + Pipeline por vertical", ciclo, logo, "Bloco II · Atual"),
        # Vertical Seguros: Matriz → Analise → Pipeline (Matriz recebe asses_data para Bitrix-100%)
        render_matriz(10, "seguros", wbr, card, logo, asses_data=asses_seg),
        render_analise_canal(11, "seguros", wbr, card, asses_seg, logo),
        render_pipeline(12, "seguros", wbr, card, logo),
        # NPS Cons (one-off) ANTES da Matriz Cons
        render_nps_consorcio(13, logo),
        # Vertical Consorcios: Matriz → Analise → Pipeline
        render_matriz(14, "consorcios", wbr, card, logo, asses_data=asses_cons),
        render_analise_canal(15, "consorcios", wbr, card, asses_cons, logo),
        render_pipeline(16, "consorcios", wbr, card, logo),
        # Conclusao com 3 velocimetros (Seg + Cons + Total PJ2 Receita)
        render_conclusao_velocimetros(wbr, card, logo, 17),
    ]

    nav_js = """
<style>
  body { padding: 0; background: #1a1a15; }
  body.deck-mode { display: block; align-items: stretch; gap: 0; }
  body.deck-mode section { display: none; margin: 0 auto; transform-origin: top center; }
  body.deck-mode section.active { display: flex; }
  .nav-bar { position: fixed; bottom: 16px; left: 50%; transform: translateX(-50%); background: rgba(0,0,0,0.85); color: #fff; padding: 10px 20px; border-radius: 24px; display: flex; gap: 18px; align-items: center; font-family: Arial, sans-serif; z-index: 9999; box-shadow: 0 4px 16px rgba(0,0,0,0.5); }
  .nav-bar button { background: transparent; border: 1px solid rgba(255,255,255,0.3); color: #fff; width: 36px; height: 36px; border-radius: 50%; font-size: 18px; cursor: pointer; display: flex; align-items: center; justify-content: center; }
  .nav-bar button:hover { background: rgba(238,247,124,0.2); border-color: #eef77c; }
  .nav-bar .counter { font-size: 14px; font-variant-numeric: tabular-nums; min-width: 60px; text-align: center; }
  .nav-bar .toggle { font-size: 11px; padding: 4px 12px; border-radius: 12px; cursor: pointer; background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); }
  .nav-bar .toggle.on { background: #eef77c; color: #424135; border-color: #eef77c; font-weight: 600; }
</style>
<div class="nav-bar">
  <button id="nav-prev" title="Anterior (←)">‹</button>
  <span class="counter"><span id="curr">1</span> / <span id="total">21</span></span>
  <button id="nav-next" title="Próximo (→)">›</button>
  <span class="toggle" id="nav-toggle" title="Alternar modo PPT (P)">PPT</span>
</div>
<script>
(function() {
  const slides = Array.from(document.querySelectorAll('section'));
  const total = slides.length;
  document.getElementById('total').textContent = total;
  let idx = 0;
  let deckMode = true;

  function applyZoom() {
    if (!deckMode) return;
    const s = slides[idx];
    if (!s) return;
    const w = window.innerWidth, h = window.innerHeight - 80;
    const zoom = Math.min(w / 1920, h / 1080) * 0.96;
    s.style.transform = 'scale(' + zoom + ')';
    s.style.transformOrigin = 'top center';
    s.style.marginTop = '20px';
  }
  function show(i) {
    idx = Math.max(0, Math.min(total - 1, i));
    document.getElementById('curr').textContent = idx + 1;
    if (deckMode) {
      slides.forEach((s, k) => s.classList.toggle('active', k === idx));
      applyZoom();
    }
  }
  function setMode(on) {
    deckMode = on;
    document.body.classList.toggle('deck-mode', on);
    document.getElementById('nav-toggle').classList.toggle('on', on);
    if (on) {
      slides.forEach(s => { s.style.transform = ''; });
      show(idx);
    } else {
      slides.forEach(s => { s.classList.remove('active'); s.style.transform = ''; });
    }
  }
  document.getElementById('nav-prev').onclick = () => show(idx - 1);
  document.getElementById('nav-next').onclick = () => show(idx + 1);
  document.getElementById('nav-toggle').onclick = () => setMode(!deckMode);
  window.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowLeft' || e.key === 'PageUp') { show(idx - 1); e.preventDefault(); }
    else if (e.key === 'ArrowRight' || e.key === 'PageDown' || e.key === ' ') { show(idx + 1); e.preventDefault(); }
    else if (e.key === 'Home') show(0);
    else if (e.key === 'End') show(total - 1);
    else if (e.key === 'p' || e.key === 'P') setMode(!deckMode);
  });
  window.addEventListener('resize', applyZoom);
  setMode(true);
})();
</script>
"""
    html_doc = f'''<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="UTF-8"><title>Ritual N2 {PJ2_VERTICAIS_DISPLAY} · {esc(ciclo)}</title>
<style>{css}</style></head><body>
{chr(10).join(slides)}
{nav_js}
</body></html>'''

    # Step 8 hardcodes refactor (2026-05-12): pos-processing dos placeholders globais.
    # Strings hardcoded em divs HTML/argumentos de slide_head() viraram "{PJ2_X}"
    # placeholders literais — substituir aqui pelos valores resolvidos em main().
    html_doc = (html_doc
                .replace("{PJ2_VERTICAIS_DISPLAY}", PJ2_VERTICAIS_DISPLAY)
                .replace("{PJ2_CICLO_ATUAL}", PJ2_CICLO_ATUAL)
                .replace("{PJ2_CICLO_FECHAMENTO}", PJ2_CICLO_FECHAMENTO)
                .replace("{PJ2_COORDENADOR}", PJ2_COORDENADOR))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html_doc, encoding="utf-8")
    print(f"[build_pj2_deck] wrote {len(slides)} slides → {args.output}")


if __name__ == "__main__":
    main()
