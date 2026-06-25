#!/usr/bin/env python3
"""
build_deck.py — gerador deterministico do deck HTML do ritual N3.

Le canonical WBR data JSON + Card YAML + ClickUp tasks JSON + action-report MD
e template ritual.tmpl.html. Substitui placeholders {{...}} por strings HTML.
Escreve deck final em OUTPUT_HTML.

Narrativas livres (ESP_DESTAQUE, ESP_ESTAGNACAO, MX_CALLOUT_BODY, ENC_INTRO,
side cards de Analise) sao preenchidas com TODO placeholders que o agente
preenche em Edit calls subsequentes (opcao "a" do refactor 2026-05-05).

Uso:
    python3 build_deck.py \\
        --wbr-data-json PATH \\
        --card PATH \\
        --clickup-tasks PATH \\
        --action-report PATH \\
        --skill-dir PATH \\
        --output PATH \\
        [--prev-wbr-data-json PATH]

Codigo testado contra ciclo Consorcios 2026-05-04 (Card v2.5.1, briefing v2.0).
"""
import argparse
import json
import math
import re
import sys
import unicodedata
from datetime import date, datetime
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML required. pip install pyyaml", file=sys.stderr)
    sys.exit(1)


# ============================================================
# Helpers
# ============================================================

def slugify(s: str) -> str:
    """Remove diacritics + lowercase + replace non-alnum with _."""
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^a-zA-Z0-9]+", "_", s).strip("_").lower()
    return s


def resolve_is_first_ritual(wbr_blk: dict) -> bool:
    """Le is_first_ritual_of_month de forma ROBUSTA: top-level do bloco wbr OU
    aninhado em `meta.` (2026-06-18).

    Motivo: o canonical E6 poe a flag em `meta.is_first_ritual_of_month`, mas
    varios sites do builder liam SO o top-level -> agenda dinamica (1880) e slides
    de fechamento (9161) nao disparavam no 1o ritual quando a flag so existia em
    meta. A resolucao de modo (9318/9415) ja tinha esse fallback; isto unifica
    todos os sites. Top-level tem precedencia (mesmo se False) — espelha 9318.
    """
    if not isinstance(wbr_blk, dict):
        return False
    v = wbr_blk.get("is_first_ritual_of_month")
    if v is None:
        v = (wbr_blk.get("meta") or {}).get("is_first_ritual_of_month", False)
    return bool(v)


def fmt_brl(v: float, compact: bool = False) -> str:
    """Format BRL — full or compact (R$ 41,1M)."""
    if v is None:
        return "—"
    try:
        v = float(v)
    except (TypeError, ValueError):
        return str(v)
    if compact:
        if abs(v) >= 1e9:
            return f"R$ {v/1e9:.1f}B".replace(".", ",")
        if abs(v) >= 1e6:
            return f"R$ {v/1e6:.1f}M".replace(".", ",")
        if abs(v) >= 1e3:
            return f"R$ {v/1e3:.0f}K"
        return f"R$ {v:.0f}"
    # full BRL: 41.074.169,00
    return "R$ " + f"{v:,.0f}".replace(",", ".")


def fmt_pct(v: float, decimals: int = 0) -> str:
    if v is None:
        return "—"
    try:
        return f"{float(v):.{decimals}f}%".replace(".", ",")
    except (TypeError, ValueError):
        return str(v)


# ============================================================
# Helpers data-driven PJ2 / multi-canal (portados do build_pj2_deck.py V13)
# ============================================================
# Funcoes puras para classificacao de assessor por canal, listagem de squad
# com hidden filter, e derivacao de metas por canal. Generalizadas para ler
# tudo do Card YAML (sem hardcode 28/35+7/35 do V13 standalone).
#
# Card schema esperado (apresentacao):
#   apresentacao:
#     responsaveis:
#       - id: investimentos           # canal_id (NOVO — obrigatorio p/ label canal)
#         nome: Investimentos
#         squad: [Nome1, Nome2, ...]
#       - id: credito
#         nome: Credito
#         squad: [...]
#     outros_m7:                       # opcional, todos caem em canal "outros_m7"
#       especialistas: [...]
#       coordenador: [...]
#       outros: [...]
#     hidden_in_squad_lists: [Nome1, ...]
#     metas_split:                     # opcional
#       default_method: proporcional_squad
#       overrides:
#         receita_consorcio_mensal:
#           method: fixed_ratio
#           ratios: { investimentos: 0.65, credito: 0.20, outros_m7: 0.15 }
#
# Nenhuma destas funcoes e chamada por funcoes existentes do plugin —
# zero impacto em Cards N3 atuais.


def _norm_pj2(s: str) -> str:
    """Normalize uppercase + sem diacriticos (compativel com V13 normalize_name).

    Distinto de slugify() que retorna lowercase com underscores. Usado para
    comparacao case-insensitive de nomes de assessores no squad_index.
    """
    if not s:
        return ""
    s = str(s).strip().upper()
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    return s


def _canal_id_from_nome(nome: str) -> str:
    """Fallback heuristico para card.apresentacao.responsaveis sem campo 'id'.

    Detecta canal a partir de palavra-chave no nome. Usado apenas para
    backward-compat com Cards antigos. Cards novos (PJ2 v1.0+) devem
    declarar 'id' explicitamente em cada entrada de responsaveis.
    """
    n = (nome or "").lower()
    if "credito" in n or "crédito" in n:
        return "credito"
    if "investimento" in n:
        return "investimentos"
    return ""  # desconhecido


def build_squad_index(card: dict) -> dict:
    """Retorna dict {nome_normalizado: (canal_id, nome_canonico)}.

    Data-driven: itera card.apresentacao.responsaveis[] usando r['id'] como
    canal_id (com fallback heuristico via _canal_id_from_nome). Adiciona
    membros de card.apresentacao.outros_m7 como canal "outros_m7".
    """
    idx = {}
    apresent = (card or {}).get("apresentacao") or {}
    for r in (apresent.get("responsaveis") or []):
        canal_id = r.get("id") or _canal_id_from_nome(r.get("nome", ""))
        if not canal_id:
            continue
        for sq in (r.get("squad") or []):
            idx[_norm_pj2(sq)] = (canal_id, sq)
    outros = apresent.get("outros_m7") or {}
    for grupo in ("especialistas", "coordenador", "outros"):
        for nm in (outros.get(grupo) or []):
            idx[_norm_pj2(nm)] = ("outros_m7", nm)
    return idx


def classify_assessor(nome, squad_idx: dict) -> tuple:
    """Retorna (canal_id, nome_canonico).

    canal_id in {investimentos, credito, outros_m7, ..., desconhecido}.
    Tenta lookup exato, depois primeiro+ultimo nome. None/empty → desconhecido.
    """
    if not nome:
        return ("desconhecido", str(nome) if nome is not None else "")
    n = _norm_pj2(nome)
    if not n:
        return ("desconhecido", str(nome))
    if n in squad_idx:
        return squad_idx[n]
    parts = n.split()
    if len(parts) >= 2:
        first_last = f"{parts[0]} {parts[-1]}"
        if first_last in squad_idx:
            return squad_idx[first_last]
    return ("desconhecido", str(nome))


def get_hidden_names_norm(card: dict) -> set:
    """Set normalizado de nomes em card.apresentacao.hidden_in_squad_lists."""
    apresent = (card or {}).get("apresentacao") or {}
    return {_norm_pj2(n) for n in (apresent.get("hidden_in_squad_lists") or [])}


def get_squad_full_list(card: dict, canal_id: str) -> list:
    """Retorna lista completa de nomes do squad do canal, excluindo hidden.

    Para canal=outros_m7, agrega especialistas + coordenador + outros.
    Para canais nomeados (investimentos/credito/...), filtra responsaveis[id==canal_id].
    """
    apresent = (card or {}).get("apresentacao") or {}
    hidden = set(apresent.get("hidden_in_squad_lists") or [])
    if canal_id == "outros_m7":
        out = []
        outros = apresent.get("outros_m7") or {}
        for grupo in ("especialistas", "coordenador", "outros"):
            out.extend(outros.get(grupo) or [])
        return [s for s in out if s not in hidden]
    for r in (apresent.get("responsaveis") or []):
        rid = r.get("id") or _canal_id_from_nome(r.get("nome", ""))
        if rid == canal_id:
            return [s for s in (r.get("squad") or []) if s not in hidden]
    return []


def filter_hidden(assesores_canal, card: dict) -> list:
    """Remove assessores hidden de lista de tuples (nome, dict)."""
    hidden = get_hidden_names_norm(card)
    return [(n, r) for n, r in assesores_canal if _norm_pj2(n) not in hidden]


def _get_squad_sizes(card: dict) -> dict:
    """Retorna {canal_id: tamanho_squad} para todos os canais declarados.

    Usado por meta_proporcional como base do split proporcional. Substitui o
    hardcode SQUAD_INV=28, SQUAD_CRED=7, SQUAD_TOTAL=35 do V13 standalone.
    """
    sizes = {}
    apresent = (card or {}).get("apresentacao") or {}
    for r in (apresent.get("responsaveis") or []):
        canal_id = r.get("id") or _canal_id_from_nome(r.get("nome", ""))
        if not canal_id:
            continue
        sizes[canal_id] = len(r.get("squad") or [])
    return sizes


def meta_proporcional(meta_total, squad_sizes: dict, exclude_outros: bool = True) -> dict:
    """Divide meta_total proporcionalmente aos tamanhos de squad por canal.

    Args:
        meta_total: valor numerico a dividir; se None retorna dict de Nones.
        squad_sizes: {canal_id: int} — obtido via _get_squad_sizes(card).
        exclude_outros: se True (default V13), canal "outros_m7" recebe None
                        (nao tem meta proporcional). Definir False para incluir.

    Returns: {canal_id: float|None}. Inclui chave "outros_m7": None quando
             exclude_outros=True, mesmo se ausente em squad_sizes.
    """
    out = {}
    if exclude_outros:
        out["outros_m7"] = None
    if meta_total is None:
        for cid in squad_sizes:
            out.setdefault(cid, None)
        return out
    total = sum(v for cid, v in squad_sizes.items()
                if v and not (exclude_outros and cid == "outros_m7"))
    if total <= 0:
        for cid in squad_sizes:
            out.setdefault(cid, None)
        return out
    for cid, sz in squad_sizes.items():
        if exclude_outros and cid == "outros_m7":
            out[cid] = None
        elif sz and sz > 0:
            out[cid] = meta_total * sz / total
        else:
            out[cid] = None
    return out


def _metas_split_config(card: dict, ind_id: str) -> dict:
    """Le card.apresentacao.metas_split.overrides[ind_id], aplica default_method.

    Returns: {"method": str, "ratios": {...}|None, "values": {...}|None}.
    method default = "proporcional_squad" (mantem semantica V13).
    """
    apresent = (card or {}).get("apresentacao") or {}
    split_cfg = apresent.get("metas_split") or {}
    default_method = split_cfg.get("default_method", "proporcional_squad")
    overrides = (split_cfg.get("overrides") or {}).get(ind_id) or {}
    return {
        "method": overrides.get("method", default_method),
        "ratios": overrides.get("ratios"),
        "values": overrides.get("values"),
    }


def get_meta_explicit_canal(card: dict, vert: str, ind_id: str, fase: str,
                            mes_atual_key: str = "maio_2026",
                            mes_fech_key: str = "abril_2026"):
    """Le meta canal explicita de card.metas_canal.{vert}.{ind_id}.{periodo_key}.

    Returns: dict {canal_id: valor} ou None se nao declarado.
    """
    per_key = mes_fech_key if fase == "fechamento" else mes_atual_key
    metas_canal = (card or {}).get("metas_canal") or {}
    return ((metas_canal.get(vert) or {}).get(ind_id) or {}).get(per_key)


def derive_meta_canal(card: dict, vert: str, ind_id: str, fase: str) -> dict:
    """Deriva meta por canal usando precedencia:

    1. card.metas_canal.{vert}.{ind_id}.{periodo} (explicito por usuario)
    2. card.apresentacao.metas_split.overrides[ind_id] (method fixed_ratio|absolute)
    3. proporcional_squad (default — divide meta_total via squad_sizes do Card)

    Casos especiais:
    - taxa_conversao_*: aplica mesma meta a todos os canais (nao divide)

    Returns: {canal_id: float|None} para todos canais em squad_sizes + "outros_m7".
    """
    explicit = get_meta_explicit_canal(card, vert, ind_id, fase)
    if explicit:
        return explicit

    metas_ppi = ((card or {}).get("metas_ppi") or {}).get(ind_id) or {}

    # Taxa de conversao: meta uniforme por canal
    if "taxa_conversao" in ind_id:
        v = metas_ppi.get("valor")
        squad_sizes = _get_squad_sizes(card)
        return {cid: v for cid in (list(squad_sizes) + ["outros_m7"])}

    # Resolve meta_total da metas_ppi (cobre valor, qty, e variantes _proximo_mes)
    if fase == "atual" and "valor_proximo_mes" in metas_ppi:
        meta_total = metas_ppi.get("valor_proximo_mes")
    elif "valor" in metas_ppi:
        meta_total = metas_ppi.get("valor")
    elif fase == "atual" and "qty_proximo_mes" in metas_ppi:
        meta_total = metas_ppi.get("qty_proximo_mes")
    else:
        meta_total = metas_ppi.get("qty")

    cfg = _metas_split_config(card, ind_id)
    method = cfg["method"]
    squad_sizes = _get_squad_sizes(card)

    if method == "fixed_ratio" and cfg["ratios"]:
        if meta_total is None:
            return {cid: None for cid in cfg["ratios"]}
        return {cid: meta_total * float(r) for cid, r in cfg["ratios"].items()}
    if method == "absolute" and cfg["values"]:
        return dict(cfg["values"])
    # default: proporcional_squad
    return meta_proporcional(meta_total, squad_sizes, exclude_outros=True)


def derive_meta_ativas_volume_canal(card: dict, vert: str, fase: str,
                                    ativ_id_seg: str = "oportunidades_ativas_funil_seg",
                                    ativ_id_default: str = "oportunidades_ativas_funil") -> dict:
    """Meta volume_ativas_canal = meta_total dividida proporcionalmente."""
    ativ_id = ativ_id_seg if vert == "seguros" else ativ_id_default
    metas_ppi = ((card or {}).get("metas_ppi") or {}).get(ativ_id) or {}
    if fase == "atual":
        v = metas_ppi.get("volume_proximo_mes") or metas_ppi.get("volume")
    else:
        v = metas_ppi.get("volume")
    return meta_proporcional(v, _get_squad_sizes(card), exclude_outros=True)


def derive_meta_ativas_ticket_canal(card: dict, vert: str, fase: str,
                                    ativ_id_seg: str = "oportunidades_ativas_funil_seg",
                                    ativ_id_default: str = "oportunidades_ativas_funil") -> dict:
    """Ticket meta Ativas por canal = vol_ativas_canal / qty_ativas_canal.

    Se ha split vol_mensal_canal explicito (rebalanceamento user) → usa essa
    proporcao para vol_ativas. Senao → proporcional ao squad. qty sempre
    proporcional ao squad. Garante: ticket = vol_canal / qty_canal.
    """
    ativ_id = ativ_id_seg if vert == "seguros" else ativ_id_default
    metas_ppi = ((card or {}).get("metas_ppi") or {}).get(ativ_id) or {}
    if fase == "atual":
        vol_ativas_total = metas_ppi.get("volume_proximo_mes") or metas_ppi.get("volume")
        qty_ativas_total = metas_ppi.get("qty_proximo_mes") or metas_ppi.get("qty")
    else:
        vol_ativas_total = metas_ppi.get("volume")
        qty_ativas_total = metas_ppi.get("qty")

    vol_mensal_id = "volume_seguros_mensal" if vert == "seguros" else "volume_consorcio_mensal"
    vol_mensal_meta = derive_meta_canal(card, vert, vol_mensal_id, fase) or {}
    sum_mensal = sum((v or 0) for v in vol_mensal_meta.values()) or 0

    squad_sizes = _get_squad_sizes(card)
    vol_ativas_canal_squad = meta_proporcional(vol_ativas_total, squad_sizes, exclude_outros=True)
    qty_meta_squad = meta_proporcional(qty_ativas_total, squad_sizes, exclude_outros=True)

    out = {}
    canais_eval = list(squad_sizes) + ["outros_m7"]
    for c in canais_eval:
        v_mensal_c = vol_mensal_meta.get(c)
        if v_mensal_c is not None and sum_mensal > 0:
            pct_vol_c = v_mensal_c / sum_mensal
            vol_ativas_c = vol_ativas_total * pct_vol_c if vol_ativas_total else None
        else:
            vol_ativas_c = vol_ativas_canal_squad.get(c)
        qty_c = qty_meta_squad.get(c)
        out[c] = (vol_ativas_c / qty_c) if (vol_ativas_c and qty_c and qty_c > 0) else None
    return out


def derive_meta_ticket_fechamento_canal(card: dict, vert: str, fase: str) -> dict:
    """Ticket fechamento meta = vol_canal / qty_canal."""
    if vert == "seguros":
        vol_id, qty_id = "volume_seguros_mensal", "quantidade_seguros_mensal"
    else:
        vol_id, qty_id = "volume_consorcio_mensal", "quantidade_consorcio_mensal"
    vol_meta = derive_meta_canal(card, vert, vol_id, fase)
    qty_meta = derive_meta_canal(card, vert, qty_id, fase)
    out = {}
    squad_sizes = _get_squad_sizes(card)
    for c in list(squad_sizes) + ["outros_m7"]:
        v = vol_meta.get(c)
        q = qty_meta.get(c)
        out[c] = (v / q) if (v is not None and q and q > 0) else None
    return out


# ============================================================
# Step 5 Tier 1-3 (2026-05-11) — Label dinamico: especialista | canal | sub_bloco
# ============================================================
# Generaliza o eixo de iteracao do bloco repetido do deck (loop sobre N entradas
# do tipo especialista/canal/sub_bloco). Cards N3 atuais com label_responsavel
# ausente ou "especialista" caem no caminho legado — comportamento identico.
#
# Tier 1 (strings UI):       constantes LABEL_DISPLAY / LABEL_PT_PLURAL
# Tier 2 (filtros N5):       helper _eixo_key(card) → chave de row N5
# Tier 3 (lookups WBR ind):  helper _eixo_dict(ind, eixo) com fallback en cascata
#
# Tier 4 (forks de funcoes esp-specific como _esp_funnel_svg, _esp_summary_cards,
# etc.) sera implementado quando o template pj2 chamar funcoes proprias (Step 8).
# Por ora, as ocorrencias hardcoded de row.get("especialista") / ind.get("n2")
# em codigo existente NAO sao alteradas — preservam regressao zero N3.

LABEL_DISPLAY = {
    "especialista": "Especialista",
    "canal":        "Canal",
    "sub_bloco":    "Sub-bloco",
}

LABEL_PT_PLURAL = {
    "especialista": "especialistas",
    "canal":        "canais",
    "sub_bloco":    "sub-blocos",
}


def _eixo_key(card: dict, default: str = "especialista") -> str:
    """Resolve a chave do eixo de iteracao do Card.

    Lookup: card.metadata.label_responsavel → fallback default.
    Valores validos: "especialista" | "canal" | "sub_bloco".
    Card N3 sem label_responsavel → "especialista" (retro-compat).
    """
    meta = (card or {}).get("metadata") or {}
    val = meta.get("label_responsavel") or default
    if val not in LABEL_DISPLAY:
        # valor invalido no Card — fallback seguro
        return default
    return val


def _eixo_dict(ind: dict, eixo: str = "especialista") -> dict:
    """Lookup do dict de breakdown por entrada do eixo.

    Cascade:
      1. ind["por_{eixo}"]  (formato explicito por eixo: por_canal, por_sub_bloco)
      2. ind["n2"]          (formato canonical do WBR — usado por Cards N3 atuais)
      3. ind["por_especialista"]  (formato legacy CON pre-2026-05-04)

    Returns dict vazio se nenhum dos 3 estiver presente. Sempre retorna dict
    (nunca None), portanto seguro para .get() chains.
    """
    if not isinstance(ind, dict):
        return {}
    return (
        ind.get(f"por_{eixo}")
        or ind.get("n2")
        or ind.get("por_especialista")
        or {}
    )


def _get_per_assessor(wbr: dict, ind_id: str, nome: str, eixo: str = "especialista"):
    """Lookup de dados per-assessor dentro do WBR canonical.

    Contrato futuro (Step 7 / pos-banco): indicators _pj2 populam
    wbr.indicadores.{ind_id}.por_assessor[nome] = {canal, qty, vol, ...}.
    Por enquanto pode retornar None — chamadores devem fallback para
    per_assessor_loader (CSV workaround V13).
    """
    if not wbr or not ind_id or not nome:
        return None
    inds = (wbr.get("indicadores") or {})
    ind = inds.get(ind_id) if isinstance(inds, dict) else None
    if not ind:
        return None
    pa = ind.get("por_assessor") or ind.get(f"por_assessor_{eixo}") or {}
    return pa.get(nome)


# ============================================================
# Resolucao dinamica de KPI IDs (vertical-agnostic)
# ============================================================
# Refator 2026-05-07: substitui hardcodes "receita_consorcio_mensal",
# "taxa_conversao_funil_con" etc. por deteccao dinamica baseada nos IDs
# disponiveis no canonical WBR data JSON (data["wbr"].indicadores) ou no
# consolidado N5 (dados_n5.indicadores). Funciona para qualquer vertical
# (CON, SEG WL/RE, INV, CRED, UNI...) sem hardcode de sufixo.

def _resolve_kpi_id(indicadores, kind: str, default: str = None,
                     subnivel: str = None, aspect: str = None) -> str:
    """Resolve dinamicamente o ID do indicador para uma kind logica.

    Estrutura tipica em CON/INV/CRED:
      {kind}_{vertical}_mensal | {kind}_funil_{vertical_short}
      ex: receita_consorcio_mensal, taxa_conversao_funil_con
      ex: oportunidades_ativas_funil  (sem sufixo)

    Estrutura tipica em SEG (multi-subnivel + aspect split):
      {kind}_seguros_mensal_{subnivel}              ex: receita_seguros_mensal_wl
      {kind}_funil_seg_{subnivel}                   ex: oportunidades_criadas_funil_seg_wl
      {kind}_funil_seg_{subnivel}_{aspect}          ex: oportunidades_ativas_funil_seg_wl_qty

    Args:
        indicadores: dict {ind_id: data} (canonical WBR data JSON) OU
                     list [{indicator_id, data, ...}] (consolidado N5).
        kind: tipo logico — receita / volume / quantidade / taxa_conversao /
              ticket_medio / criadas / ativas / estagnadas / sem_atividade.
        default: retorno se nada bater.
        subnivel: 'wl' / 're' / None — quando dado, prioriza IDs com esse sufixo.
        aspect:   'qty' / 'volume' / 'pct_ativas' / None — qualificador adicional.

    Returns: primeiro ind_id que casa com o pattern do kind (com scoring), ou default.
    """
    if not indicadores:
        return default
    if isinstance(indicadores, dict):
        ids = list(indicadores.keys())
    elif isinstance(indicadores, list):
        ids = [(e.get("indicator_id") if isinstance(e, dict) else None) for e in indicadores if e]
        ids = [i for i in ids if i]
    else:
        return default

    pat_map = {
        "receita":          r"^receita_",
        "volume":           r"^volume_",
        "quantidade":       r"^quantidade_",
        "taxa_conversao":   r"^taxa_conversao_",
        "ticket_medio":     r"^ticket_medio_",
        "criadas":          r"^oportunidades_criadas_",
        "ativas":           r"^oportunidades_ativas_",
        "estagnadas":       r"^oportunidades_estagnadas_",
        "sem_atividade":    r"^oportunidades_sem_atividade",
    }
    base_pat = pat_map.get(kind)
    if not base_pat:
        return default

    matches = [rid for rid in ids if re.match(base_pat, rid)]
    if not matches:
        return default

    def _score(rid):
        s = 0
        # subnivel matching (peso alto)
        if subnivel:
            if re.search(rf"(?:^|_){re.escape(subnivel)}(?:_|$)", rid):
                s += 100
            else:
                s -= 50  # penaliza se nao bate quando subnivel pedido
        else:
            # sem subnivel pedido: penaliza IDs com subnivel suffix conhecido
            if re.search(r"(?:^|_)(wl|re)(?:_|$)", rid):
                s -= 10
            # bonus se termina em _n1 (consolidado N1)
            if rid.endswith("_n1") or "_n1_" in rid:
                s += 20
        # aspect matching
        if aspect:
            if rid.endswith(f"_{aspect}") or re.search(rf"_{re.escape(aspect)}(?:_|$)", rid):
                s += 50
            else:
                s -= 20
        else:
            # sem aspect pedido: penaliza IDs com aspect suffix conhecido
            if re.search(r"_(qty|volume|pct_ativas)$", rid):
                s -= 5
        return s

    matches.sort(key=_score, reverse=True)
    return matches[0]


def _kpi_id(data: dict, kind: str, aspect: str = None, default: str = None) -> str:
    """Wrapper: usa data['wbr'].indicadores + data['card'].metadata.subnivel."""
    indicadores = (data or {}).get("wbr", {}).get("indicadores", {})
    subnivel = (data or {}).get("card", {}).get("metadata", {}).get("subnivel")
    return _resolve_kpi_id(indicadores, kind, default=default, subnivel=subnivel, aspect=aspect)


def _kpi_id_n5(dados_n5: dict, card: dict, kind: str, aspect: str = None, default: str = None) -> str:
    """Wrapper: usa dados_n5.indicadores (lista) + card.metadata.subnivel.
    Nota: dados_n5 (consolidado E2) tipicamente NAO tem split por subnivel —
    filtro de subnivel acontece via row['especialista']. Por isso subnivel=None
    aqui; passamos so kind."""
    indicadores = (dados_n5 or {}).get("indicadores", []) or []
    return _resolve_kpi_id(indicadores, kind, default=default, subnivel=None, aspect=aspect)


def _esp_kpi_value(data: dict, esp: str, kind: str, aspect: str = None, field_legacy: str = None):
    """Resolve valor do KPI para um especialista, agnostico a schema do canonical.

    Suporta DOIS schemas comuns:
    1. CON-legacy: 1 ID base com `por_especialista.{esp}.{qty|volume|taxa|...}`
       (estrutura tradicional Consorcios — qty/volume embutidos como subfields).
    2. SEG-split: 2+ IDs com sufixo de aspect (`_qty`, `_volume`) e
       `n2.{esp}.realizado` como valor primario (estrutura Seguros pos-2026-05-04).

    Args:
      data: dict com data['wbr']['indicadores'].
      esp: nome do especialista (ex: 'Claudia Moraes').
      kind: 'ativas', 'criadas', 'estagnadas', 'taxa_conversao', 'sem_atividade'.
      aspect: 'qty', 'volume', 'pct_ativas', None — qualificador (SEG-split).
      field_legacy: nome do subfield em por_especialista (CON-legacy). Se None,
                    usa 'qty' como default.

    Returns: numero ou None se nada disponivel.
    """
    indicadores = (data or {}).get("wbr", {}).get("indicadores", {}) or {}

    # FIX 2026-05-14 (Bug 6 — KPI tiles Pipeline zerados): em RE (sem aspect-split),
    # n2.{esp} tem {qty, vol} subfields ao inves de "realizado" generico.
    # Aliases: aspect "qty" → tentar tambem ["qty", "realizado"]; "volume" → ["vol", "volume", "realizado"].
    aspect_field_aliases = {
        "qty":    ["qty", "realizado"],
        "volume": ["vol", "volume", "vol_total", "volume_total", "realizado"],
    }

    # Tentativa 1: ID com aspect (SEG-split)
    if aspect:
        aspect_id = _kpi_id(data, kind, aspect=aspect)
        if aspect_id:
            ind = indicadores.get(aspect_id, {}) or {}
            n2_esp = (ind.get("n2") or {}).get(esp, {}) or {}
            # Tenta aliases do aspect antes do generico "realizado"
            for fkey in aspect_field_aliases.get(aspect, ["realizado"]):
                v = n2_esp.get(fkey)
                if v is not None:
                    return v
            # tentar por_especialista.{esp}.realizado tambem (variant)
            pe_esp = (ind.get("por_especialista") or {}).get(esp, {}) or {}
            for fkey in aspect_field_aliases.get(aspect, ["realizado"]):
                v = pe_esp.get(fkey)
                if v is not None:
                    return v

    # Tentativa 2: ID base sem aspect (CON-legacy ou fallback SEG)
    base_id = _kpi_id(data, kind)
    if base_id:
        ind = indicadores.get(base_id, {}) or {}
        # 2a. por_especialista.{esp}.{aspect|legacy_field}
        pe_esp = (ind.get("por_especialista") or {}).get(esp, {}) or {}
        if pe_esp:
            field = field_legacy or aspect or "qty"
            v = pe_esp.get(field)
            if v is None and field != "realizado":
                v = pe_esp.get("realizado")
            if v is not None:
                return v
        # 2b. n2.{esp}.{aspect aliases} (caso por_especialista vazio)
        n2_esp = (ind.get("n2") or {}).get(esp, {}) or {}
        # Try aspect aliases primeiro, depois "realizado" / field_legacy
        candidates = []
        if aspect:
            candidates.extend(aspect_field_aliases.get(aspect, [aspect]))
        if field_legacy:
            candidates.append(field_legacy)
        candidates.append("realizado")
        for fkey in candidates:
            v = n2_esp.get(fkey)
            if v is not None:
                return v
    return None


def fmt_int(v) -> str:
    if v is None:
        return "—"
    try:
        return f"{int(v):,}".replace(",", ".")
    except (TypeError, ValueError):
        return str(v)


def iniciais(nome: str) -> str:
    """'Douglas Silva' → 'DS'. Max 3 chars."""
    parts = nome.split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][0]).upper()
    return nome[:2].upper()


def primeiro_nome(nome: str) -> str:
    return nome.split()[0]


def status_to_class(status: str) -> str:
    """WBR status → CSS class."""
    if status is None:
        return "mute"
    s = str(status).lower()
    if s in ("verde", "good"):
        return "good"
    if s in ("amarelo", "warn", "amarelo_proximo_verde"):
        return "warn"
    if s in ("vermelho", "bad"):
        return "bad"
    return "mute"


# ────────────────────────────────────────────────────────────────
# Helpers de semaforo (P0-pj2 Step 8 — schema v2.1 com direction)
# ────────────────────────────────────────────────────────────────

def cor_from_pct(pct: float, direction: str = "maior_melhor") -> str:
    """Calcula cor do semaforo dado pct_atingimento e direction.

    Args:
        pct: realizado / meta (float). None = mute.
        direction: 'maior_melhor' (default) ou 'menor_melhor'.

    Returns:
        'good' | 'warn' | 'bad' | 'mute' (CSS class compatible).

    Logica:
        maior_melhor:
          pct >= 1.00  → good
          0.80 <= pct < 1.00 → warn
          pct < 0.80   → bad

        menor_melhor (invertido — pct=realizado/meta, meta eh limite superior):
          pct <= 1.00  → good (dentro da meta)
          1.00 < pct <= 1.20 → warn (excedeu ate 20%)
          pct > 1.20   → bad (excedeu mais de 20%)

    Critico para edit #28 (tempo_de_ciclo com meta 30d direction=menor_melhor).
    """
    if pct is None:
        return "mute"
    try:
        p = float(pct)
    except (TypeError, ValueError):
        return "mute"
    if direction == "menor_melhor":
        if p <= 1.00:
            return "good"
        if p <= 1.20:
            return "warn"
        return "bad"
    # default: maior_melhor
    if p >= 1.00:
        return "good"
    if p >= 0.80:
        return "warn"
    return "bad"


def status_from_pct(pct: float, direction: str = "maior_melhor") -> dict:
    """Constroi dict {cor, emoji} a partir de pct + direction.

    Use APOS override de n1_value/n2_agregado em runtime — decisao
    arquitetural #30 (Batch I 2026-05-12): builder NUNCA confia em
    `ind.status.cor` pre-computed se reescreve realizado.

    Returns: {'cor': 'verde'|'amarelo'|'vermelho'|'mute', 'emoji': '🟢'|...}
    """
    cls = cor_from_pct(pct, direction)
    cor_map = {"good": "verde", "warn": "amarelo", "bad": "vermelho", "mute": "mute"}
    emoji_map = {"good": "🟢", "warn": "🟡", "bad": "🔴", "mute": "⚪"}
    return {"cor": cor_map.get(cls, "mute"), "emoji": emoji_map.get(cls, "⚪")}


def resolve_circulo(responsavel: dict, skill_dir: Path) -> str:
    """Resolve HTML do circulo-id (P0-avatar).

    Le card.apresentacao.responsaveis[i] e retorna HTML do <span class="circulo-id">:
      - Se `avatar_key` presente: lookup em assets/avatars/avatars.yaml,
        carrega .b64 file, retorna <img>.
      - Se `id_circulo` presente: retorna <span> com texto (max 3 chars).
      - Fallback: iniciais do nome.

    Args:
        responsavel: dict com chaves `avatar_key` OU `id_circulo` (+ `nome`).
        skill_dir: Path para `m7-ritual-gestao/skills/preparing-materials/`.

    Returns:
        HTML string com classe `.circulo-id` (ver CSS no template).

    Memory: reference_avatar_circulo_id (2026-05-12).
    """
    avatars_yaml_path = skill_dir / "assets" / "avatars" / "avatars.yaml"

    def _try_avatar_lookup(key: str) -> str | None:
        """Tenta resolver avatar_key explicito via avatars.yaml. Retorna HTML ou None."""
        if not key or not avatars_yaml_path.exists():
            return None
        import yaml
        try:
            registry = yaml.safe_load(avatars_yaml_path.read_text(encoding="utf-8")) or {}
            spec = (registry.get("specialists") or {}).get(key) or {}
            if spec.get("base64"):
                return f'<span class="circulo-id"><img src="{spec["base64"]}" alt="{spec.get("nome", key)}"></span>'
            b64_file = spec.get("base64_file") or f"{key}.b64"
            b64_path = avatars_yaml_path.parent / b64_file
            if b64_path.exists():
                b64_data = b64_path.read_text(encoding="utf-8").strip()
                if not b64_data.startswith("data:"):
                    b64_data = f"data:image/png;base64,{b64_data}"
                return f'<span class="circulo-id"><img src="{b64_data}" alt="{spec.get("nome", key)}"></span>'
        except Exception as e:
            print(f"[resolve_circulo] falha lendo avatar '{key}': {e}")
        return None

    # 1) avatar_key explicit
    html = _try_avatar_lookup(responsavel.get("avatar_key"))
    if html:
        return html

    # 1.5) AUTO-SLUG: tenta slugify(nome) — destrava Cards sem avatar_key explicito
    # quando o avatars.yaml ja tem entry para o especialista (ex: "Douglas Silva" → "douglas_silva").
    nome = responsavel.get("nome") or ""
    if nome:
        html = _try_avatar_lookup(slugify(nome))
        if html:
            return html

    # 2) id_circulo (texto curto)
    id_circ = responsavel.get("id_circulo")
    if id_circ:
        return f'<span class="circulo-id">{id_circ[:3]}</span>'

    # 3) Fallback: iniciais do nome
    return f'<span class="circulo-id">{iniciais(nome or "??")}</span>'


def status_to_emoji(status: str) -> str:
    s = str(status or "").lower()
    if "verde" in s or s == "good":
        return "🟢"
    if "amarelo" in s or s == "warn":
        return "🟡"
    if "vermelho" in s or s == "bad":
        return "🔴"
    if "mtd_insuf" in s or "sem_dados" in s:
        return "⏳"
    return "⚪"


def _gauge_svg(realizado: float, meta: float, label: str = "",
               direction: str = "maior_melhor") -> str:
    """Renderiza velocimetro semi-circular SVG (edit #21 — slide Conclusao).

    Args:
        realizado: valor realizado.
        meta: valor da meta (denominador).
        label: rotulo abaixo do velocimetro.
        direction: 'maior_melhor' (default) ou 'menor_melhor'.

    Returns:
        SVG string inline (sem container — wrap em .veloc-gauge-wrap no caller).

    Layout (image 3 do contrato pj2-slide-requirements):
        - Arco semi-circular preenchido conforme pct = realizado/meta
        - Cor segue cor_from_pct(pct, direction) — tokens M7-2026
        - Realizado a esquerda, Meta a direita, % abaixo
    """
    if meta and meta > 0:
        pct = realizado / meta
    else:
        pct = 0.0
    pct_clamped = max(0.0, min(pct, 1.5))   # cap em 150% pra render

    # Geometria: arco semi-circular 200x100 (centro 100,100, raio 80)
    cx, cy, r = 100, 100, 80
    # arco vai de (cx-r, cy) a (cx+r, cy) — angulo de 180° invertido (semi-circle superior)
    # angulo preenchido = pct * 180
    angle_deg = pct_clamped * 180
    angle_rad = math.radians(180 - angle_deg)   # 0% = ponta esquerda; 100% = ponta direita
    end_x = cx + r * math.cos(angle_rad)
    end_y = cy - r * math.sin(angle_rad)
    large_arc = 1 if angle_deg > 180 else 0
    # cor classe
    cls = cor_from_pct(pct, direction)
    color_map = {"good": "#4caf50", "warn": "#ffc107", "bad": "#e40014", "mute": "#aeada8"}
    fill_color = color_map.get(cls, color_map["mute"])

    fmt_val = fmt_brl if abs(meta or 0) >= 1000 else lambda v: f"{v:.1f}"

    svg = (
        f'<svg viewBox="0 0 200 130" xmlns="http://www.w3.org/2000/svg" '
        f'class="veloc-gauge" preserveAspectRatio="xMidYMid meet">'
        # Track (background arco completo)
        f'<path d="M {cx-r} {cy} A {r} {r} 0 0 1 {cx+r} {cy}" '
        f'fill="none" stroke="#d0d0cc" stroke-width="14" stroke-linecap="butt"/>'
        # Filled arc
        f'<path d="M {cx-r} {cy} A {r} {r} 0 {large_arc} 1 {end_x:.2f} {end_y:.2f}" '
        f'fill="none" stroke="{fill_color}" stroke-width="14" stroke-linecap="butt"/>'
        # Realizado (esquerda do arco)
        f'<text x="{cx-r-4}" y="{cy+18}" text-anchor="end" '
        f'font-size="11" fill="#424135" font-weight="600">{fmt_val(realizado)}</text>'
        # Meta (direita do arco)
        f'<text x="{cx+r+4}" y="{cy+18}" text-anchor="start" '
        f'font-size="11" fill="#424135" font-weight="600">{fmt_val(meta)}</text>'
        # % abaixo do arco
        f'<text x="{cx}" y="{cy+28}" text-anchor="middle" '
        f'font-size="20" fill="{fill_color}" font-weight="700">{int(pct*100)}%</text>'
    )
    if label:
        svg += (f'<text x="{cx}" y="{cy+50}" text-anchor="middle" '
                f'font-size="10" fill="#79755c" letter-spacing="0.05em">{label}</text>')
    svg += '</svg>'
    return svg


def iso_week(d: date) -> str:
    """2026-05-04 → 'S19' (ISO week)."""
    iso = d.isocalendar()
    return f"S{iso.week}"


def cycle_date_from_str(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def mes_ano_pt(d: date) -> str:
    meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
             "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
    return f"{meses[d.month - 1]} {d.year}"


def mes_curto_pt(d: date) -> str:
    return ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
            "Jul", "Ago", "Set", "Out", "Nov", "Dez"][d.month - 1]


def todo_block(label: str, hint: str = "") -> str:
    """Generate a TODO placeholder for narrative content the agent fills later."""
    h = f" — {hint}" if hint else ""
    return f'<span style="background:#fff3a0;padding:2px 6px;border-radius:3px;">[TODO: {label}{h}]</span>'


# ============================================================
# Loaders
# ============================================================

def load_assets(skill_dir: Path) -> dict:
    """Load b64 assets and JS as strings."""
    asset_dir = skill_dir / "templates" / "assets"
    if not asset_dir.exists():
        raise FileNotFoundError(f"Assets dir nao encontrado: {asset_dir}")
    offwhite_b64 = (asset_dir / "m7-logo-offwhite.b64").read_text(encoding="utf-8").strip()
    dark_b64 = (asset_dir / "m7-logo-dark.b64").read_text(encoding="utf-8").strip() if (asset_dir / "m7-logo-dark.b64").exists() else offwhite_b64
    return {
        "ASSET_FONT_ULTRALIGHT_B64": (asset_dir / "twk-everett-ultralight.b64").read_text(encoding="utf-8").strip(),
        "ASSET_FONT_LIGHT_B64":      (asset_dir / "twk-everett-light.b64").read_text(encoding="utf-8").strip(),
        "ASSET_FONT_REGULAR_B64":    (asset_dir / "twk-everett-regular.b64").read_text(encoding="utf-8").strip(),
        "ASSET_FONT_MEDIUM_B64":     (asset_dir / "twk-everett-medium.b64").read_text(encoding="utf-8").strip(),
        "ASSET_FONT_BOLD_B64":       (asset_dir / "twk-everett-bold.b64").read_text(encoding="utf-8").strip(),
        "ASSET_LOGO_OFFWHITE_B64":   offwhite_b64,
        "ASSET_LOGO_DARK_B64":       dark_b64,
        "ASSET_LOGO_OFFWHITE_DATA_URI": f"data:image/png;base64,{offwhite_b64}",
        "ASSET_LOGO_DARK_DATA_URI":  f"data:image/png;base64,{dark_b64}",
        "ASSET_DECK_STAGE_JS":       (asset_dir / "deck-stage.js").read_text(encoding="utf-8"),
    }


def load_template(skill_dir: Path, variant: str = "default") -> str:
    """Carrega template HTML.

    Args:
        skill_dir: diretorio da skill preparing-materials.
        variant: 'default' (ritual.tmpl.html, N3 single-vert) ou
                 'pj2' (ritual-pj2.tmpl.html, multi-vertical N2 — Step 8 2026-05-12).

    Para variant='pj2', o template usa placeholder {{STYLE_BLOCK}} que e
    substituido pelo bloco <style>...</style> extraido do template legado
    (DRY — mesma stylesheet, slides diferentes).
    """
    if variant == "pj2":
        pj2_tmpl = (skill_dir / "templates" / "ritual-pj2.tmpl.html").read_text(encoding="utf-8")
        # Extrair <style>...</style> do legacy template e injetar
        legacy = (skill_dir / "templates" / "ritual.tmpl.html").read_text(encoding="utf-8")
        style_match = re.search(r"<style>.*?</style>", legacy, re.DOTALL)
        style_block = style_match.group(0) if style_match else "<style></style>"
        return pj2_tmpl.replace("{{STYLE_BLOCK}}", style_block)
    return (skill_dir / "templates" / "ritual.tmpl.html").read_text(encoding="utf-8")


def is_pj2_card(card: dict) -> bool:
    """Detecta Card PJ2 multi-vertical (label_responsavel='canal' OU vertical_code='PJ2')."""
    if not card:
        return False
    meta = card.get("metadata") or {}
    if meta.get("vertical_code") == "PJ2":
        return True
    if meta.get("label_responsavel") == "canal":
        return True
    verticais = meta.get("verticais") or []
    return len(verticais) >= 2   # multi-vertical = PJ2


def extract_esp_subtemplate(template: str) -> tuple[str, str]:
    """
    Extrai o sub-template do bloco especialista que esta comentado.
    Retorna (template_sem_bloco, sub_template_str).

    No template, o bloco esta entre marcadores BEGIN_BLOCK_ESPECIALISTA
    e END_BLOCK_ESPECIALISTA dentro de um comentario HTML.
    """
    pattern = re.compile(
        r"<!--\s*BEGIN_BLOCK_ESPECIALISTA[^\n]*\n(.*?)END_BLOCK_ESPECIALISTA\s*-->",
        re.DOTALL,
    )
    m = pattern.search(template)
    if not m:
        raise ValueError("BEGIN/END_BLOCK_ESPECIALISTA nao encontrado no template")
    sub = m.group(1).strip()
    template_clean = pattern.sub("", template)
    return template_clean, sub


def _find_last_ritual_wbr(vertical_root: Path, vertical_lower: str,
                          current_date: str, current_month_prefix: str,
                          same_month_only: bool = True) -> Path:
    """Localiza o WBR base do ULTIMO RITUAL REAL via 03-Rituais/.

    NOVO 2026-05-20: complementa _auto_resolve_prev_wbr_data_json para que a
    coluna "Δ vs Sem. Ant." compare contra ciclo de ritual real (e nao ciclo
    intermediario qualquer). Ciclos intermediarios (re-execucao mid-week,
    correcoes pos-bug) nao representam "semana anterior".

    Algoritmo:
      1. Subir da pasta da vertical ate encontrar 03-Rituais/ irmao de 02-Controle
      2. Glob {Vertical}/N*/[{subnivel}/]YYYY-MM-DD/ata/ata-ritual-*.md
         (atas EXISTENTES — pasta vazia significa pre-ritual nao realizado)
      3. Filtrar: data < current_date, mesmo mes (se same_month_only)
      4. Pegar data mais recente — esse e o nome da pasta = data do WBR base
      5. Retornar 02-Controle/{Vertical}/{YYYY-MM}/{date}/wbr/wbr-{vertical}-{date}.data.json

    N-parametrico: funciona para qualquer vertical/nivel/subnivel.
    Retorna None se nao encontrar (cai em fallback last-cycle pelo caller).
    """
    # vertical_root e {OneDrive}/.../02-Controle/{Vertical}/
    # 03-Rituais e irmao: vertical_root.parent.parent / "03-Rituais"
    # range(6): tolera a profundidade extra do level-first (02-Controle/N{N}/{Vertical}/...)
    rituais_base = None
    p = vertical_root
    for _ in range(6):
        p = p.parent
        if not p.exists():
            break
        cand = p / "03-Rituais"
        if cand.exists() and cand.is_dir():
            rituais_base = cand
            break
    if not rituais_base:
        return None

    # Vertical em 03-Rituais e Capitalized (case-insensitive lookup).
    # S3 2026-05-20: aceita tanto Vertical (Consorcios, PJ2) quanto Vertical-subnivel (Seguros-wl, Seguros-re).
    # Coletamos TODAS as pastas que comecam com o prefixo da vertical para cobrir ambos patterns:
    #   - Canonical S3: rituais_base/{Vertical}[-{sub}]/N{N}-{Cad}/{Periodo}/ata/
    #   - Legacy_yyyymmdd: rituais_base/{Vertical}/N{N}/[{sub}/]{YYYY-MM-DD}/ata/
    #   - Legacy pre-2026-05-12: rituais_base/{Vertical}/N{N}-{Cad}/[{SubArea}/]{Periodo}/Ata/
    vert_dirs = []
    vertical_lower_l = vertical_lower.lower()
    # Level-first (D2): a vertical pode estar como filha DIRETA de 03-Rituais/ (legado)
    # OU sob um segmento de nivel 03-Rituais/N{N}/{Vertical}/ (level-first). Buscamos
    # nos dois: rituais_base + cada pasta N{N}/ abaixo dela.
    nivel_re = re.compile(r"^n[1-5]$", re.IGNORECASE)
    search_roots = [rituais_base]
    for d in rituais_base.iterdir():
        if d.is_dir() and nivel_re.match(d.name):
            search_roots.append(d)
    for root in search_roots:
        for d in root.iterdir():
            if not d.is_dir():
                continue
            name_l = d.name.lower()
            if name_l == vertical_lower_l or name_l.startswith(f"{vertical_lower_l}-"):
                vert_dirs.append(d)
    if not vert_dirs:
        return None

    # rglob por ata-ritual-*.md em qualquer profundidade.
    # IMPORTANTE: data retornada e a do WBR base, nao do ritual (conv. commit 37b9828).
    # Layout canonical S3: pasta avo = Periodo ("2026-S20" ou "2026-05") -> extrair via
    # FILENAME (data do RITUAL ≈ data do WBR base com 0-1 dia de erro).
    date_re_folder = re.compile(r"^(\d{4}-\d{2}-\d{2})$")
    date_re_file = re.compile(r"(\d{4}-\d{2}-\d{2})\.md$", re.IGNORECASE)
    candidates = []
    for vert_dir in vert_dirs:
        for ata_md in vert_dir.rglob("ata-ritual-*.md"):
            # Ignorar dentro de _Historico/
            if any(part.startswith("_Historico") or part.startswith("_historico") for part in ata_md.parts):
                continue
            # ata_md = .../{Vertical}/.../{folder-data-ou-periodo}/ata/ata-ritual-*.md
            # parent.parent = "2026-05-14" (legacy) ou "2026-S20" (canonical S3)
            folder_name = ata_md.parent.parent.name
            mf = date_re_folder.match(folder_name)
            if mf:
                candidates.append(mf.group(1))
                continue
            # Canonical S3: folder = Periodo, derivar data via filename
            mn = date_re_file.search(ata_md.name)
            if mn:
                candidates.append(mn.group(1))

    candidates = [
        d for d in candidates
        if d < current_date and (not same_month_only or d[:7] == current_month_prefix)
    ]
    if not candidates:
        return None
    candidates.sort()
    last_ritual_wbr_date = candidates[-1]

    # Caller passa vertical_root = cycle_folder.parent.
    # Canonical S3: cycle_folder = 02-Controle/{Vertical-cap}[-{sub}]/{YYYY-MM}/{YYYY-MM-DD}/
    #   -> cycle_folder.parent = .../{YYYY-MM}/ -> vertical_root.parent = .../{Vertical-cap}[-{sub}]/
    vertical_actual_root = vertical_root.parent
    yyyy_mm = last_ritual_wbr_date[:7]

    # Tentativa exata primeiro (caso WBR base seja gerado no dia do ritual)
    wbr_path = (vertical_actual_root / yyyy_mm / last_ritual_wbr_date / "wbr"
                / f"wbr-{vertical_lower}-{last_ritual_wbr_date}.data.json")
    if wbr_path.exists():
        return wbr_path

    # FIX 2026-05-20: data extraida do filename da ata e a data do RITUAL,
    # mas o WBR base costuma ser 1-2 dias antes (G2.2 roda na semana anterior).
    # Procurar WBR mais proximo ANTES da data do ritual no mesmo mes.
    mes_dir = vertical_actual_root / yyyy_mm
    if mes_dir.exists():
        ciclo_dirs = sorted(
            [d.name for d in mes_dir.iterdir()
             if d.is_dir() and re.match(r"^\d{4}-\d{2}-\d{2}$", d.name)
             and d.name <= last_ritual_wbr_date],
            reverse=True
        )
        for ciclo_date in ciclo_dirs:
            candidate = (mes_dir / ciclo_date / "wbr"
                         / f"wbr-{vertical_lower}-{ciclo_date}.data.json")
            if candidate.exists():
                return candidate

    return None


def _auto_resolve_prev_wbr_data_json(wbr_data_json_path: Path,
                                      same_month_only: bool = True) -> Path:
    """Auto-resolve PREV_WBR_DATA_JSON via glob nas pastas-irmas da vertical.

    DECISAO USUARIO 2026-05-05 — `same_month_only=True` (default): Delta vs S{prev}
    so faz sentido WITHIN-MONTH (S19 vs S18 cross-month e enviesado por mudanca de
    metas/cenarios mensais). Se for o 1o ciclo do mes, retorna None → coluna Delta
    fica VAZIA (correto), nao puxa do mes anterior.

    Tenta .data.json (canonical) primeiro, depois fallback .md (parser legado).
    Retorna Path do arquivo, ou None se primeiro ciclo do mes / sem candidato.
    N-parametrico: funciona para qualquer vertical.
    """
    if not wbr_data_json_path or not wbr_data_json_path.exists():
        return None
    cycle_folder = wbr_data_json_path.parent.parent
    vertical_root = cycle_folder.parent
    fname = wbr_data_json_path.name
    m = re.match(r"wbr-([a-z0-9_-]+)-(\d{4}-\d{2}-\d{2})\.data\.json", fname)
    if not m:
        return None
    vertical_lower, current_date = m.group(1), m.group(2)
    current_month_prefix = current_date[:7]  # 'YYYY-MM'

    def _find_candidates(suffix: str):
        candidates = []
        for pattern in [
            f"*/wbr/wbr-{vertical_lower}-*{suffix}",
            f"*/*/wbr/wbr-{vertical_lower}-*{suffix}",
        ]:
            candidates.extend(vertical_root.glob(pattern))
        if vertical_root.parent.exists():
            for pattern in [
                f"*/wbr/wbr-{vertical_lower}-*{suffix}",
                f"*/*/wbr/wbr-{vertical_lower}-*{suffix}",
            ]:
                candidates.extend(vertical_root.parent.glob(pattern))
        seen = set()
        dated = []
        for c in candidates:
            if c == wbr_data_json_path or "_Historico" in str(c) or "backup" in c.name.lower():
                continue
            if "narrativo" in c.name.lower():
                continue
            if str(c) in seen:
                continue
            seen.add(str(c))
            m2 = re.search(r"wbr-[a-z0-9_-]+-(\d{4}-\d{2}-\d{2})", c.name)
            if m2:
                dated.append((m2.group(1), c))
        dated.sort(key=lambda x: x[0])
        prev = None
        for d, p in dated:
            if d < current_date:
                # FILTRO same-month: ignora candidatos de meses anteriores
                if same_month_only and d[:7] != current_month_prefix:
                    continue
                prev = p
        return prev

    # PREFERENCIA RITUAL (FIX 2026-05-20): label do header diz "Δ vs Sem. Ant." —
    # semanticamente compara contra ultimo ciclo de RITUAL REAL, nao ultimo ciclo
    # qualquer. Procurar em 03-Rituais/{Vertical}/{nivel}/YYYY-MM-DD/ata/ata-ritual-*.md
    # (ata existe = ritual aconteceu). Cair em last-cycle se nao encontrar.
    ritual_prev = _find_last_ritual_wbr(
        vertical_root, vertical_lower, current_date, current_month_prefix, same_month_only
    )
    if ritual_prev:
        return ritual_prev

    prev = _find_candidates(".data.json")
    if prev:
        return prev
    prev_md = _find_candidates(".md")
    if prev_md:
        return prev_md

    # FIX 2026-05-14 (Bug 7 — Delta vazio em 1o ciclo split): quando vertical e
    # split (ex: "seguros-re", "seguros-wl"), e nada encontrado para o subnivel
    # especifico, cair em fallback para a vertical base ("seguros"). Isso permite
    # comparar o 1o ciclo split contra o ultimo ciclo consolidado pre-split.
    # Indicators podem ter IDs diferentes (consolidado: receita_seguros_mensal_re,
    # split: receita_seguros_mensal) mas _calc_delta ja tem fallback chain por
    # label slug + partial match nas primeiras palavras.
    if "-" in vertical_lower:
        base_vertical = vertical_lower.split("-")[0]
        original = vertical_lower

        def _find_candidates_base(suffix: str):
            candidates = []
            search_root = vertical_root.parent if vertical_root.parent.exists() else vertical_root
            for pattern in [
                f"{base_vertical}/*/wbr/wbr-{base_vertical}-*{suffix}",
                f"{base_vertical}/*/*/wbr/wbr-{base_vertical}-*{suffix}",
            ]:
                candidates.extend(search_root.glob(pattern))
            seen = set()
            dated = []
            for c in candidates:
                if c == wbr_data_json_path or "_Historico" in str(c) or "backup" in c.name.lower():
                    continue
                if "narrativo" in c.name.lower() or original in c.name.lower():
                    continue  # evita pegar o split atual de novo
                if str(c) in seen:
                    continue
                seen.add(str(c))
                m2 = re.search(rf"wbr-{re.escape(base_vertical)}-(\d{{4}}-\d{{2}}-\d{{2}})", c.name)
                if m2:
                    dated.append((m2.group(1), c))
            dated.sort(key=lambda x: x[0])
            prev = None
            for d, p in dated:
                if d < current_date:
                    if same_month_only and d[:7] != current_month_prefix:
                        continue
                    prev = p
            return prev

        prev = _find_candidates_base(".data.json") or _find_candidates_base(".md")
        return prev
    return None


def _split_str_to_titulo_texto(s: str, max_titulo: int = 80) -> dict:
    """Quebra uma frase em titulo + texto preservando a analise.
    Heuristica: usa primeiro ' — ' ou primeira frase como titulo; o restante vira texto.
    Quando nao ha quebra natural, titulo = primeiros max_titulo chars + reticencias; texto = frase inteira."""
    s = (s or "").strip()
    if not s:
        return {"titulo": "", "texto": ""}
    # Quebra em ' — ' (em-dash com espacos) ou ': '
    for sep in (" — ", " - ", ": ", " · "):
        if sep in s:
            titulo, _, resto = s.partition(sep)
            return {"titulo": titulo.strip()[:max_titulo], "texto": resto.strip()}
    # Quebra na primeira sentenca
    for sep in (". ", "; "):
        if sep in s:
            titulo, _, resto = s.partition(sep)
            return {"titulo": titulo.strip()[:max_titulo], "texto": resto.strip()}
    # Sem quebra: titulo abreviado + texto = frase completa (preserva analise)
    if len(s) > max_titulo:
        return {"titulo": s[:max_titulo].rstrip() + "…", "texto": s}
    return {"titulo": s, "texto": ""}


def _normalize_v1_1_to_v1_0(wbr: dict) -> None:
    """Shim: normaliza WBR canonical v1.1 (analyst novo) para layout v1.0 que
    o builder espera. Mutates in-place. NO-OP em WBRs ja v1.0.

    FIX #6 (2026-05-14): destaques/riscos como list[str] viravam dict com texto vazio,
    perdendo a analise. Agora quebra str em titulo+texto inteligentemente."""
    if not isinstance(wbr, dict):
        return
    # destaques_positivos: list[str] -> list[dict{titulo, texto}] com split inteligente
    dp = wbr.get("destaques_positivos")
    if isinstance(dp, list) and dp and isinstance(dp[0], str):
        wbr["destaques_positivos"] = [
            _split_str_to_titulo_texto(s) if isinstance(s, str) else s
            for s in dp
        ]
    # riscos_principais: idem (defensivo) — mesmo schema titulo+texto
    rp = wbr.get("riscos_principais")
    if isinstance(rp, list) and rp and isinstance(rp[0], str):
        wbr["riscos_principais"] = [
            _split_str_to_titulo_texto(s) if isinstance(s, str) else s
            for s in rp
        ]
    # anomalias: list[str] -> list[dict{descricao, acao}] (schema diferente de destaques!)
    # Render usa a.get("descricao") + a.get("acao"). Quando vem list[str], split tambem.
    anom = wbr.get("anomalias")
    if isinstance(anom, list) and anom and isinstance(anom[0], str):
        normalized = []
        for s in anom:
            if isinstance(s, str):
                d = _split_str_to_titulo_texto(s, max_titulo=120)
                normalized.append({"descricao": d["titulo"], "acao": d["texto"]})
            else:
                normalized.append(s)
        wbr["anomalias"] = normalized


def _normalize_pct_ativas_scale(wbr: dict) -> None:
    """Hardening 2026-06-11: o E6 analyst as vezes emite indicadores '*_pct_ativas'
    (% estagnadas das ativas) com `realizado`/`n2.realizado` em RAZAO 0-1 (ex: 0.857),
    mas a Matriz/Dashboard do build_deck esperam 0-100 (85.7) — sem isso a celula
    renderiza "0,9% / 200% meta verde" em vez de "85,7% vermelho".

    Idempotente: so escala valores 0<x<=1.5 (razao). Valores ja em 0-100 (>1.5) ficam
    intactos. % estagnadas/ativas nunca e legitimamente <=1.5% na pratica (e indicador
    de problema, tipicamente 30-90%), logo o falso-positivo e desprezivel. Meta NAO e
    tocada (build_deck a le do Card pct_ativas_max)."""
    for iid, e in (wbr.get("indicadores") or {}).items():
        if not isinstance(e, dict):
            continue
        is_pct = ("pct_ativas" in iid) or (
            e.get("unit") == "pct" and e.get("direction") == "menor_melhor")
        if not is_pct:
            continue
        r = e.get("realizado")
        if isinstance(r, (int, float)) and not isinstance(r, bool) and 0 < r <= 1.5:
            e["realizado"] = round(r * 100, 1)
        for _esp, n in (e.get("n2") or {}).items():
            if not isinstance(n, dict):
                continue
            nr = n.get("realizado")
            if isinstance(nr, (int, float)) and not isinstance(nr, bool) and 0 < nr <= 1.5:
                n["realizado"] = round(nr * 100, 1)


def load_data(wbr_data_json_path: Path, card_path: Path,
              prev_wbr_data_json_path: Path = None) -> dict:
    """Load + parse all data sources into single dict.
    FIX img7 — quando prev e .md, parsea para extrair Painel Section 1.5 N2 values.
    FIX rodada 6 — apos load, aplica Card.apresentacao.overrides_ritual em-place.
    FIX v1.1 — aplica shim _normalize_v1_1_to_v1_0 antes do resto."""
    wbr = json.loads(wbr_data_json_path.read_text(encoding="utf-8"))
    _normalize_v1_1_to_v1_0(wbr)
    _normalize_pct_ativas_scale(wbr)
    card = yaml.safe_load(card_path.read_text(encoding="utf-8"))
    prev = None
    if prev_wbr_data_json_path and prev_wbr_data_json_path.exists():
        if prev_wbr_data_json_path.suffix == ".json":
            prev = json.loads(prev_wbr_data_json_path.read_text(encoding="utf-8"))
            _normalize_v1_1_to_v1_0(prev)
            _normalize_pct_ativas_scale(prev)
        elif prev_wbr_data_json_path.suffix == ".md":
            prev = _parse_prev_wbr_md(prev_wbr_data_json_path)
    data = {"wbr": wbr, "card": card, "prev_wbr": prev}
    _apply_card_overrides(data)
    # FIX (2026-05-14): aplica os MESMOS Card overrides ao prev WBR. Antes, override
    # so aplicava ao WBR atual, gerando comparacoes invalidas em Delta vs prev
    # (ex: 'Receita Douglas caiu R$ 18.883' — falso, era diferenca entre prev raw
    # bugado e current override correto). Trick: swap prev para 'wbr' temporariamente
    # e reaproveita _apply_card_overrides. Override global (sem ciclo) aplica em ambos.
    if prev:
        prev_data = {"wbr": prev, "card": card}
        _apply_card_overrides(prev_data)
    return data


def _apply_card_overrides(data: dict) -> None:
    """FIX rodada 6 issue 6/7 — aplica Card.apresentacao.overrides_ritual aos dados.
    FIX rodada 7 issue 8 — aplica tambem projection_overrides (recalculo metodo "a"
    apos os overrides de N1/N2).

    Sobrepoe realizado/meta/projecoes de indicadores em data['wbr']['indicadores']
    quando o `ciclo` do override bate com o ciclo do WBR. Mutates data in-place.

    MOTIVO: views SQL upstream com bug conhecido + projecoes do JSON ficaram stale
    relativas aos novos N1/N2. Override e escopado por ciclo.

    N-parametrico: qualquer Card pode declarar; ausente = no-op."""
    card = data.get("card") or {}
    wbr = data.get("wbr") or {}
    apres = card.get("apresentacao") or {}
    overrides = apres.get("overrides_ritual") or {}
    proj_overrides = apres.get("projection_overrides") or {}
    # FIX (2026-05-14): wbr_ciclo lia metadata.ciclo (v1.0 legacy). v1.1 nao tem isso —
    # tem data_referencia top-level. Sem cycle match, override de ciclos antigos
    # (ex: 2026-05-04 'salvando o dia' do volume errado) vazava para o ciclo atual
    # (2026-05-13) sobrescrevendo dados corretos do WBR atual.
    # Fallback chain: metadata.ciclo (v1.0) -> data_referencia (v1.1) -> ''.
    wbr_ciclo = (
        (wbr.get("metadata") or {}).get("ciclo")
        or wbr.get("data_referencia")
        or ""
    )
    indicadores = wbr.setdefault("indicadores", {})

    # PARTE 1 — Override realizado/meta N1+N2 (rodada 6)
    # FIX (2026-05-14): cycle match agora EXIGE bate exato. Se override.ciclo declarado
    # e nao bate com wbr.data_referencia, override NAO e aplicado (era stale).
    # Antes: 'not wbr_ciclo' habilitava override em qualquer ciclo se WBR fosse v1.1.
    if overrides:
        over_ciclo = overrides.get("ciclo")
        cycle_match = (not over_ciclo) or (wbr_ciclo and over_ciclo == wbr_ciclo)
        if cycle_match:
            for ind_id, ov in (overrides.get("indicadores") or {}).items():
                ind = indicadores.setdefault(ind_id, {})
                n1_ov = ov.get("n1") or {}
                if "realizado" in n1_ov:
                    r = n1_ov["realizado"]
                    ind["realizado_mtd"] = r
                    ind["realizado"] = r
                    for fb in ("realizado_lagging_competencia_atual",):
                        if fb in ind:
                            ind[fb] = r
                if "meta" in n1_ov:
                    m = n1_ov["meta"]
                    ind["meta_mes_corrente"] = m
                    ind["meta"] = m
                    ind["meta_mes"] = m
                n2_ov = ov.get("n2") or {}
                if n2_ov:
                    n2_dict = ind.get("n2") or ind.get("por_especialista")
                    if n2_dict is None:
                        n2_dict = {}
                        ind["n2"] = n2_dict
                    for esp, eo in n2_ov.items():
                        e = n2_dict.setdefault(esp, {})
                        if "realizado" in eo:
                            r = eo["realizado"]
                            e["realizado_mtd"] = r
                            e["realizado"] = r
                        if "meta" in eo:
                            m = eo["meta"]
                            e["meta_mes"] = m
                            e["meta"] = m
                            e["meta_mes_corrente"] = m

    # PARTE 2 — Override projecoes N1+N2 (rodada 7 issue 8)
    # FIX (2026-05-14): mesma regra de cycle match estrita.
    if proj_overrides:
        po_ciclo = proj_overrides.get("ciclo")
        cycle_match_proj = (not po_ciclo) or (wbr_ciclo and po_ciclo == wbr_ciclo)
        if cycle_match_proj:
            for ind_id, ov in (proj_overrides.get("indicadores") or {}).items():
                ind = indicadores.setdefault(ind_id, {})
                n1_p = ov.get("n1") or {}
                if "projecao_mes_corrente" in n1_p:
                    ind["projecao_mes_corrente"] = n1_p["projecao_mes_corrente"]
                if "projecao_mes_seguinte" in n1_p:
                    ind["projecao_mes_seguinte"] = n1_p["projecao_mes_seguinte"]
                if "classificacao_mes_corrente" in n1_p:
                    ind["classificacao_mes_corrente"] = n1_p["classificacao_mes_corrente"]
                if "classificacao_mes_seguinte" in n1_p:
                    ind["classificacao_mes_seguinte"] = n1_p["classificacao_mes_seguinte"]
                n2_p = ov.get("n2") or {}
                if n2_p:
                    n2_dict = ind.get("n2") or ind.get("por_especialista")
                    if n2_dict is None:
                        n2_dict = {}
                        ind["n2"] = n2_dict
                    for esp, eo in n2_p.items():
                        e = n2_dict.setdefault(esp, {})
                        if "projecao_mes_corrente" in eo:
                            e["projecao_mes_corrente"] = eo["projecao_mes_corrente"]
                            e["projecao_maio_base"] = eo["projecao_mes_corrente"]
                        if "projecao_mes_seguinte" in eo:
                            e["projecao_mes_seguinte"] = eo["projecao_mes_seguinte"]
                            e["projecao_junho_base"] = eo["projecao_mes_seguinte"]
                        if "classificacao_mes_corrente" in eo:
                            e["classificacao_maio"] = eo["classificacao_mes_corrente"]
                            e["classificacao_mes_corrente"] = eo["classificacao_mes_corrente"]
                        if "classificacao_mes_seguinte" in eo:
                            e["classificacao_junho"] = eo["classificacao_mes_seguinte"]
                            e["classificacao_mes_seguinte"] = eo["classificacao_mes_seguinte"]


def _apply_n5_overrides(card: dict, dados_n5: dict) -> None:
    """FIX rodada 7 issue 5 — aplica Card.apresentacao.overrides_ritual
    .indicadores.{ind}.n5_by_esp em dados_n5 (rows N5-Assessor).

    Substitui rows N5-Assessor do indicador para a competencia override
    pelas entries declaradas no Card. Rows fora do mes override sao
    preservadas. Mutates dados_n5 in-place.

    MOTIVO: override rodada 6 sobrepoe N1+N2 em data['wbr'] mas N5 esta em
    dados_n5 (carregado separadamente). _esp_riscos card Concentracao,
    Top assessores e estagnacao leem N5 → sem este override, ainda usam
    distribuicao da view SQL buggy.

    N-parametrico: qualquer Card pode declarar n5_by_esp."""
    if not card or not dados_n5:
        return
    overrides = (card.get("apresentacao") or {}).get("overrides_ritual") or {}
    if not overrides:
        return
    ov_competencia = overrides.get("competencia", "")[:7]  # YYYY-MM
    if not ov_competencia:
        return

    inds_override = overrides.get("indicadores") or {}
    inds_data = dados_n5.get("indicadores") or []

    for ind_id, ov in inds_override.items():
        n5_by_esp = ov.get("n5_by_esp")
        if not n5_by_esp:
            continue
        # Achar entry em dados_n5
        entry = next((e for e in inds_data if e.get("indicator_id") == ind_id), None)
        if entry is None:
            # Cria entry se nao existir
            entry = {"indicator_id": ind_id, "data": []}
            inds_data.append(entry)

        # Remove rows N5-Assessor do mes override (preserva outras niveis e outros meses)
        filtered = []
        for row in entry.get("data", []):
            if row.get("nivel") == "N5-Assessor":
                row_mes = (row.get("mes") or row.get("data_referencia") or "")[:7]
                if row_mes == ov_competencia:
                    continue  # remove
            filtered.append(row)
        entry["data"] = filtered

        # Adiciona rows novas a partir de n5_by_esp
        mes_full = ov_competencia + "-01"  # YYYY-MM-01
        for esp, entries in n5_by_esp.items():
            for ent in (entries or []):
                row = {
                    "nivel": "N5-Assessor",
                    "mes": mes_full,
                    "especialista": esp,
                    "assessor": ent.get("assessor"),
                    "realizado": float(ent.get("realizado") or 0),
                }
                # Manter outros campos opcionais que vierem
                for k, v in ent.items():
                    if k not in ("assessor", "realizado") and v is not None:
                        row[k] = v
                entry["data"].append(row)


def _get_squad_whitelist(esp: str, card: dict) -> list:
    """FIX rodada 6 issue 14 — le squad whitelist do Card.apresentacao.
    Retorna lista de nomes oficiais do squad do esp ou [] se nao declarado.
    Refator 2026-05-07: aceita tanto `name` (Cards SEG/novos) quanto `nome` (legado).
    N-parametrico para qualquer Card."""
    if not card or not esp:
        return []
    apres = card.get("apresentacao") or {}
    for r in apres.get("responsaveis") or []:
        r_name = r.get("name") or r.get("nome")
        if r_name == esp:
            return list(r.get("squad") or [])
    return []


def _parse_prev_wbr_md(md_path: Path) -> dict:
    """Parser fragil do WBR.md (Section 1.5 Painel) — extrai por_especialista realizado.
    Retorna dict similar ao .data.json para que _calc_delta funcione.

    Frágil porque depende do formato textual do Painel. Funciona para WBR consolidados
    do m7-controle E6 que seguem o template padrao com tabela markdown.
    Fallback gracioso — retorna dict vazio se parsing falhar.
    """
    try:
        text = md_path.read_text(encoding="utf-8")
    except Exception:
        return {"indicadores": {}, "metadata": {}}

    indicadores = {}
    # Date do ciclo do filename
    m = re.search(r"wbr-[a-z0-9_-]+-(\d{4}-\d{2}-\d{2})", md_path.name)
    ciclo = m.group(1) if m else ""

    # Procurar Secao 1.5 Painel — tabela markdown com header tipo:
    # | Indicador | Meta | Realizado | Gap | % Atingimento | Status | N2_esp1 | N2_esp2 | ...
    panel_match = re.search(
        r"##\s+1\.5[^\n]*Painel.*?\n(.*?)(?=\n##\s|\Z)",
        text, re.DOTALL | re.IGNORECASE
    )
    if not panel_match:
        return {"indicadores": indicadores, "metadata": {"ciclo": ciclo}}

    panel = panel_match.group(1)
    lines = [l for l in panel.splitlines() if l.startswith("|")]
    if len(lines) < 3:
        return {"indicadores": indicadores, "metadata": {"ciclo": ciclo}}
    header_cols = [c.strip() for c in lines[0].split("|")[1:-1]]
    # Detectar coluna 'Indicador' e 'Realizado'
    try:
        idx_ind = next(i for i, c in enumerate(header_cols) if "indicador" in c.lower())
        idx_real = next(i for i, c in enumerate(header_cols)
                        if "realizado" in c.lower() and "anterior" not in c.lower())
    except StopIteration:
        return {"indicadores": indicadores, "metadata": {"ciclo": ciclo}}

    # Identificar colunas N2 (heuristica: prefixo "N2:" ou depois da coluna Status)
    META_LABELS = {"tipo", "indicador", "meta", "realizado", "gap",
                    "% ating.", "% ating", "% atingimento", "status", "atingimento"}
    esp_cols = []
    for i, c in enumerate(header_cols):
        cl = c.lower().strip()
        if cl in META_LABELS:
            continue
        # Strip 'N2:' / 'N2 -' prefix
        esp_name = re.sub(r"^N2[:\s\-]*", "", c).strip()
        if esp_name and i > idx_real:
            esp_cols.append((i, esp_name))

    for line in lines[2:]:  # skip header + separator
        cols = [c.strip() for c in line.split("|")[1:-1]]
        if len(cols) <= max(idx_ind, idx_real):
            continue
        ind_name = cols[idx_ind]
        if not ind_name or ind_name.startswith("-") or ind_name.lower() in META_LABELS:
            continue
        ind_id = slugify(ind_name)
        n2_dict = {}
        for col_idx, esp_name in esp_cols:
            if col_idx < len(cols):
                val_str = cols[col_idx]
                # Para celulas tipo "R$ 2,38M (73,3%) Amarelo", extrair so o numero principal
                val = _parse_brl_or_num(val_str.split("(")[0].strip())
                if val is not None:
                    n2_dict[esp_name] = {"realizado_mtd": val, "realizado": val}
        n1_real = _parse_brl_or_num(cols[idx_real].split("(")[0].strip())
        indicadores[ind_id] = {
            "label": ind_name,
            "realizado_mtd": n1_real,
            "realizado": n1_real,
            "n2": n2_dict,
        }
    return {"indicadores": indicadores, "metadata": {"ciclo": ciclo}}


def _parse_brl_or_num(s: str):
    """Parser auxiliar para extrair numero de uma celula tipo 'R$ 109.859' ou '74,2%' ou '16'."""
    if not s or s in ("—", "-", "ref"):
        return None
    # Remove R$, %, espacos
    cleaned = s.replace("R$", "").replace("%", "").strip()
    # Detect compact (M, K)
    multiplier = 1
    if cleaned.endswith("M") or cleaned.endswith("m"):
        multiplier = 1e6
        cleaned = cleaned[:-1].strip()
    elif cleaned.endswith("K") or cleaned.endswith("k"):
        multiplier = 1e3
        cleaned = cleaned[:-1].strip()
    # BR locale: . como milhares, , como decimal
    cleaned = cleaned.replace(".", "").replace(",", ".")
    try:
        return float(cleaned) * multiplier
    except (ValueError, TypeError):
        return None


def load_clickup_tasks(path: Path) -> list:
    """Carrega tasks do JSON exportado pelo m7-controle E2 Fase 1.5 (ClickUp MCP).

    FIX (2026-05-14): o schema canonical do collect.py emite as tasks em
    `escopo_ritual_passado` + `ad_hoc_pos_ritual` (separacao por escopo do
    ritual), NAO em `tasks`/`data`. Sem este reconhecimento, clickup_tasks
    ficava vazio e tanto o donut do Slide 4 (PA Status) quanto as barras
    por owner caiam no fallback metricas_agregadas (geralmente vazio no
    analyst v1.1), exibindo "1 task / Sem owner" em vez das 3 reais.

    Aceita ambos schemas:
      - Novo: {escopo_ritual_passado: [...], ad_hoc_pos_ritual: [...], ...}
      - Legacy: {tasks: [...]} ou {data: [...]} ou lista direta.
    """
    if not path.exists():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, dict):
        # Schema canonical collect.py (preferred)
        escopo = raw.get("escopo_ritual_passado") or []
        ad_hoc = raw.get("ad_hoc_pos_ritual") or []
        if escopo or ad_hoc:
            return list(escopo) + list(ad_hoc)
        # Schemas legacy
        return raw.get("tasks", []) or raw.get("data", []) or []
    return raw


def enrich_tasks_ritual_anterior(tasks: list, cycle_dir: Path) -> list:
    """C3 (2026-05-07): enriquece cada task com `criada_em_ritual_anterior: bool`
    derivado de date_created ∈ [data_ultimo_ritual, data_ritual_atual).

    Resolve `data_ultimo_ritual` lendo o CICLO.md mais recente da MESMA vertical
    (cycle_dir.parent/*/CICLO.md ordenado por data desc, descartando o atual).

    Graceful: se nao conseguir resolver, retorna tasks sem enriquecer (flag fica
    ausente — UI cai em comportamento legado, sem badge ⭐).
    """
    if not tasks or not cycle_dir or not cycle_dir.exists():
        return tasks
    try:
        # Cycle dir name = data_ritual_atual (ex: "2026-05-06" ou "2026-04-fechamento")
        atual_str = cycle_dir.name
        if "-fechamento" in atual_str:
            return tasks  # ciclo de fechamento nao tem janela "ritual anterior"
        try:
            data_ritual_atual = datetime.fromisoformat(atual_str[:10])
        except ValueError:
            return tasks

        # Lista todos os ciclos da mesma vertical (parent dir)
        sibling_dirs = sorted(
            (d for d in cycle_dir.parent.iterdir()
             if d.is_dir() and d.name != atual_str and "fechamento" not in d.name
             and not d.name.startswith("OLD_")),
            key=lambda d: d.name,
            reverse=True,
        )
        data_ultimo_ritual = None
        for d in sibling_dirs:
            try:
                data_ultimo_ritual = datetime.fromisoformat(d.name[:10])
                break
            except ValueError:
                continue
        if not data_ultimo_ritual:
            return tasks

        for t in tasks:
            dc = t.get("date_created")
            if not dc:
                t["criada_em_ritual_anterior"] = False
                continue
            try:
                dc_dt = datetime.fromisoformat(dc[:10])
            except ValueError:
                t["criada_em_ritual_anterior"] = False
                continue
            t["criada_em_ritual_anterior"] = (
                data_ultimo_ritual <= dc_dt < data_ritual_atual
            )
        return tasks
    except Exception:
        return tasks


# ============================================================
# Renderers — Capa, Agenda
# ============================================================

def render_capa_agenda_meta(data: dict) -> dict:
    wbr = data["wbr"]
    card = data["card"]
    # Fallback robusto: WBR canonical v1.0 usa top-level data_referencia + checkpoint_label,
    # v1.3 usa bloco "meta" (NAO "metadata"), e o E6 analyst as vezes poe data_referencia/
    # checkpoint_label/vertical SO dentro de meta (sem top-level). Aceitar todas as variantes
    # para nao quebrar (ValueError ciclo='' no cycle_date_from_str). (2026-06-11 hardening.)
    meta = dict(wbr.get("metadata") or wbr.get("meta") or {})
    _meta_src = wbr.get("meta") or {}
    if not meta.get("ciclo"):
        meta["ciclo"] = (wbr.get("data_referencia") or _meta_src.get("data_referencia")
                         or _meta_src.get("ciclo") or wbr.get("ciclo") or "")
    if not meta.get("checkpoint_label"):
        meta["checkpoint_label"] = (wbr.get("checkpoint_label") or _meta_src.get("checkpoint_label")
                                    or _meta_src.get("ciclo_label") or "")
    if not meta.get("vertical"):
        meta["vertical"] = (wbr.get("vertical") or _meta_src.get("vertical")
                            or card.get("metadata", {}).get("vertical_crm", ""))
    if "data_fim" not in meta:
        # Auto: ultimo dia do mes do ciclo
        ciclo_str = meta.get("ciclo", "")
        if ciclo_str and len(ciclo_str) >= 7:
            try:
                from calendar import monthrange
                y, m = int(ciclo_str[:4]), int(ciclo_str[5:7])
                meta["data_fim"] = f"{ciclo_str[:7]}-{monthrange(y, m)[1]:02d}"
            except Exception:
                meta["data_fim"] = meta["ciclo"]

    cycle_d = cycle_date_from_str(meta["ciclo"])
    week = iso_week(cycle_d)
    end_d = cycle_date_from_str(meta.get("data_fim", meta["ciclo"]))

    # Especialistas — tenta meta, depois card.metadata, depois wbr.cards (formato novo Seguros)
    esp_list = meta.get("responsaveis_n2") or card.get("metadata", {}).get("responsaveis_n2") or []
    if not esp_list and isinstance(wbr.get("cards"), dict):
        # Formato Seguros: wbr.cards.{wl,re}.responsaveis = [list]
        for sub_card in wbr["cards"].values():
            if isinstance(sub_card, dict) and sub_card.get("responsaveis"):
                esp_list.extend(sub_card["responsaveis"])
        # Filtrar apenas os do card atual quando subnivel disponivel
        card_responsaveis = (card.get("apresentacao", {}).get("responsaveis") or [])
        if card_responsaveis:
            card_esp_names = {r.get("nome") for r in card_responsaveis if isinstance(r, dict)}
            if card_esp_names:
                esp_list = [e for e in esp_list if e in card_esp_names]
    if not esp_list:
        # Fallback — try to extract from N2 of any indicator
        for ind in wbr.get("indicadores", {}).values():
            if isinstance(ind, dict) and "n2" in ind:
                esp_list = [k for k in ind["n2"].keys() if k != "Sem Especialista"]
                break

    nivel = card["metadata"].get("nivel", "N3")
    # FIX (2026-05-14): coordenador frequentemente vem como slug "joel.freitas"
    # do meta.owner (campo machine-readable). Prettificar para "Joel Freitas".
    # Card pode override com metadata.coordenador_display ("João da Silva e Sousa").
    coord_raw = (card.get("metadata") or {}).get("coordenador_display") or meta.get("coordenador") or card["metadata"].get("owner", "")

    def _prettify_name(raw: str) -> str:
        """Converte slugs/identifiers para Nome Proprio. Idempotente em nomes ja bonitos.
        Exemplos: 'joel.freitas' -> 'Joel Freitas'; 'pedro_villarroel' -> 'Pedro Villarroel';
        'Joel Freitas' -> 'Joel Freitas' (no-op)."""
        if not raw or not isinstance(raw, str):
            return raw or ""
        s = raw.strip()
        # Se ja contem espaco E primeira letra maiuscula, provavel ja bonito
        if " " in s and s[0].isupper() and "." not in s:
            return s
        # Trocar separadores comuns por espaco e title-case
        s = re.sub(r"[._-]+", " ", s)
        return " ".join(w.capitalize() for w in s.split() if w)

    coordenador = _prettify_name(coord_raw)

    # Ciclo label: "Maio 2026, semana 1 (MTD)"
    ciclo_label = meta.get("checkpoint_label", f"{mes_ano_pt(cycle_d)}, {week}")

    # Composicao agenda (default 8/10/15*N/4/3)
    n = len(esp_list)
    t_visao = 8
    t_operacao = 10
    t_esp = 15  # por especialista
    t_sintese = 4
    t_fechamento = 3
    total_min = t_visao + t_operacao + (t_esp * n) + t_sintese + t_fechamento

    # Numbers in agenda timeline: Visao=01, Operacao=02, Esp_K=02+K, Sintese=03+N, Fechamento=04+N
    num_sintese = f"{3 + n:02d}"
    num_fechamento = f"{4 + n:02d}"

    # Headline depends on N
    if n >= 2:
        headline = f"{n} especialistas · {nivel} · {ciclo_label}"
    else:
        headline = f"{esp_list[0] if esp_list else 'Especialista'} · {nivel} · {ciclo_label}"

    # F4 (2026-05-07): Agenda dinamica — quando 1o ritual do mes, prepend
    # blocos extras de Fechamento {Mes Ant} + Diretrizes do Mes na timeline
    # ANTES dos blocos de especialistas regulares.
    is_first = resolve_is_first_ritual(wbr)  # le top-level OU meta. (2026-06-18)
    tl_rows = []
    bloco_num = 1  # contador comeca em 1; +2 (Visao/Operacao) sao fixos no template
    extra_minutes = 0
    if is_first:
        # F4 (2026-05-07): Mes anterior — preferred wbr.mes_ciclo_anterior; fallback infere de data_referencia
        mes_ant_str = wbr.get("mes_ciclo_anterior", "") or ""
        if not mes_ant_str:
            data_ref = wbr.get("data_referencia") or meta.get("ciclo", "")
            if data_ref and len(data_ref) >= 7:
                try:
                    y, m = int(data_ref[:4]), int(data_ref[5:7])
                    if m == 1:
                        mes_ant_str = f"{y - 1}-12"
                    else:
                        mes_ant_str = f"{y}-{m - 1:02d}"
                except Exception:
                    pass
        if mes_ant_str and len(mes_ant_str) == 7:
            try:
                m = int(mes_ant_str[5:7])
                meses_pt = ["", "Janeiro", "Fevereiro", "Marco", "Abril", "Maio", "Junho",
                            "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
                mes_ant_lbl = f"{meses_pt[m]} {mes_ant_str[:4]}"
            except Exception:
                mes_ant_lbl = mes_ant_str
        else:
            mes_ant_lbl = "Mes anterior"
        # Bloco "Fechamento mes anterior"
        bloco_num += 1
        tl_rows.append(
            f'<div class="tl-row feature">'
            f'<div><div class="tl-num">Bloco {bloco_num:02d}</div>'
            f'<div class="tl-title"><em>Fechamento {mes_ant_lbl}</em></div>'
            f'<div class="tl-sub">N1 consolidado · {len(esp_list)} especialista(s)</div></div>'
            f'<div class="tl-time">10 min</div>'
            f'</div>'
        )
        extra_minutes += 10
        # Bloco "Diretrizes do mes atual"
        bloco_num += 1
        mes_atual_lbl = mes_ano_pt(cycle_d)
        tl_rows.append(
            f'<div class="tl-row feature">'
            f'<div><div class="tl-num">Bloco {bloco_num:02d}</div>'
            f'<div class="tl-title"><em>Diretrizes {mes_atual_lbl}</em></div>'
            f'<div class="tl-sub">Foco · 3-5 diretrizes · riscos a monitorar</div></div>'
            f'<div class="tl-time">5 min</div>'
            f'</div>'
        )
        extra_minutes += 5

    # Agenda timeline rows for especialistas (block per esp)
    for k, esp in enumerate(esp_list, start=1):
        bloco_num += 1
        tl_rows.append(
            f'<div class="tl-row feature">'
            f'<div><div class="tl-num">Bloco {bloco_num:02d}</div>'
            f'<div class="tl-title"><em>{esp}</em></div>'
            f'<div class="tl-sub">Dashboard · Análise · Pipeline</div></div>'
            f'<div class="tl-time">{t_esp} min</div>'
            f'</div>'
        )
    agenda_tl_feature = "\n".join(tl_rows)
    # Atualiza total_min com blocos extras
    total_min = total_min + extra_minutes
    # Renumera Sintese e Fechamento conforme novos blocos
    num_sintese = f"{bloco_num + 1:02d}"
    num_fechamento = f"{bloco_num + 2:02d}"

    # FIX item 10: "Snapshot" date = data de extracao (= ciclo), nao fim do periodo
    # DATA_FECHAMENTO_CURTA usado em footers de slides com label "Snapshot {data}"
    # → deve refletir a data de coleta, nao o fim do periodo de meta (31/05).
    # Capa: usa data do ciclo tambem (faz mais sentido no contexto MTD).

    # S1-A1#1 (2026-05-15): Override do titulo de capa por Card. Permite que Seguros
    # WL apresente "Seguro de Vida" e Seguros RE "Seguros Empresariais", ao inves do
    # default "Seguros". Fallback chain:
    #   1. card.apresentacao.titulo_publico (override explicito por Card)
    #   2. card.metadata.vertical_crm.capitalize() (default semantico)
    #   3. wbr.metadata.vertical.capitalize() (fallback final)
    _titulo_publico = (card.get("apresentacao") or {}).get("titulo_publico")
    _vertical_crm = (card.get("metadata") or {}).get("vertical_crm")
    _vertical_label = _titulo_publico or (_vertical_crm or meta["vertical"]).capitalize()

    # S1-A1#2 (2026-05-15): Badge "· fechamento DD/MM/YYYY" na capa so aparece em
    # modos que olham para tras (fechamento + combinado). Modo "atual" esconde o
    # badge. Modo "auto" foi resolvido em _resolve_effective_modo para fechamento|
    # combinado|atual antes deste ponto. data["_effective_modo"] e populado em main().
    _effective_modo = data.get("_effective_modo") or "atual"
    _show_fechamento_badge = _effective_modo in ("fechamento", "combinado")
    _fechamento_suffix = (
        f" · fechamento <strong>{cycle_d.strftime('%d/%m/%Y')}</strong>"
        if _show_fechamento_badge else ""
    )

    return {
        "VERTICAL": _vertical_label,
        "FECHAMENTO_SUFFIX": _fechamento_suffix,
        "VERTICAL_LOWER": meta["vertical"].lower(),
        "NIVEL": nivel,
        "SUBNIVEL_SUFFIX": "",  # populated if subnivel active (TODO)
        "MES_ANO": mes_ano_pt(cycle_d),
        "MES_ANO_UPPER": mes_ano_pt(cycle_d).upper(),
        "CICLO_LABEL": ciclo_label,
        "DATA_FECHAMENTO": cycle_d.strftime("%d/%m/%Y"),       # data do ciclo (snapshot)
        "DATA_FECHAMENTO_CURTA": cycle_d.strftime("%d/%m"),    # data do ciclo (snapshot)
        "DATA_FIM_PERIODO": end_d.strftime("%d/%m/%Y"),        # fim do periodo de meta (referencia)
        "ESPECIALISTAS_LISTA": " · ".join(esp_list),
        # FIX (2026-05-14): label "Diretos" da Capa virou Card-driven. Default = "Especialistas".
        # Card pode sobrescrever via metadata.label_diretos (ex: PJ2 declara "Verticais").
        "LABEL_DIRETOS": ((card.get("metadata") or {}).get("label_diretos") or "Especialistas"),
        "COORDENADOR": coordenador,
        "PREV_CICLO_LABEL": _prev_ciclo_label(data),
        # Agenda
        "AGENDA_HEADLINE": headline,
        "AGENDA_T_VISAO": str(t_visao),
        "AGENDA_T_OPERACAO": str(t_operacao),
        "AGENDA_T_SINTESE": str(t_sintese),
        "AGENDA_T_FECHAMENTO": str(t_fechamento),
        "AGENDA_NUM_SINTESE": num_sintese,
        "AGENDA_NUM_FECHAMENTO": num_fechamento,
        "AGENDA_TL_FEATURE_ROWS": agenda_tl_feature,
        # Slide nums (depend on N)
        "N3_SLIDE_NUM": f"{6 + 3*n:02d}",
        "N3_BLOCO_NUM": f"{3 + n:02d}",
        "N3_FNUM": f"{6 + 3*n:02d}",
        "ENC_SLIDE_NUM": f"{7 + 3*n:02d}",
        "_n_especialistas": n,
        "_total_slides": 7 + 3*n,
        "_esp_list": esp_list,
        "_total_min": total_min,
        # Step 5 Tier 1 (2026-05-11): Label dinamico — Card N3 sem
        # label_responsavel → "especialista" (retro-compat). Template
        # legado ritual.tmpl.html ignora estes placeholders; template
        # ritual-pj2.tmpl.html (Step 6 pendente) os consome.
        "_eixo_key": _eixo_key(card),
        "LABEL_RESP": _eixo_key(card),
        "LABEL_RESP_DISPLAY": LABEL_DISPLAY[_eixo_key(card)],
        "LABEL_RESP_PLURAL": LABEL_PT_PLURAL[_eixo_key(card)],
    }


def _prev_ciclo_label(data: dict) -> str:
    if not data.get("prev_wbr"):
        return "S—"
    try:
        prev_d = cycle_date_from_str(data["prev_wbr"]["metadata"]["ciclo"])
        return f"S{prev_d.isocalendar().week}"
    except Exception:
        return "Sem. Ant."


# ============================================================
# Matrix row resolution (declarative, N-parametric) — SoT for
# both Slide 3 (Matriz) and Slide N+0 (Dashboard per esp).
#
# A "matrix row" descreve UMA linha renderizada na Matriz e nos
# Dashboards. E resolvida lendo Card.kpi_references[]:
#   - Cada entry pode ter `matrix_views[]` declarando 1+ row
#   - Sem `matrix_views`: 1 row default usando heuristica de campos
#
# Schema de matrix_view (todos opcionais exceto label):
#   label             - texto exibido na coluna Indicador
#   value_field       - JSON key dentro do indicator entry para N1 valor
#   meta_field        - idem para N1 meta
#   unidade           - BRL/ratio/pct/count (override do indicator)
#   direction         - maior_melhor/menor_melhor (override do Card.metas_ppi)
#   n2_value_field    - JSON key dentro de n2[esp] para N2 valor
#   n2_meta_field     - idem para N2 meta
#   compute           - formula para campos derivados ("volume_total/realizado_qty")
#   n2_compute        - idem para N2
#   derived_indicator_id - se a view aponta para outro indicator entry (ex: pct_ativas)
#   thresholds        - {warn: 70, good: 100} override dos defaults
# ============================================================

# Heuristica de PPI vs KPI baseada em `papel`. KPI = kpi_principal puro;
# PPI = qualquer outro (kpi_principal_derivado, contexto, ppi_funil, etc).
# FIX item 3.1: kpi_principal_derivado classificado como PPI por default.
_KPI_PAPEIS = {"kpi_principal"}


def _is_kpi_papel(papel: str) -> bool:
    return (papel or "").lower() in _KPI_PAPEIS


def _resolve_matrix_rows(data: dict, ctx: dict) -> list:
    """Le Card.kpi_references[] + matrix_views[] e retorna lista normalizada de matrix_rows.
    Cada matrix_row tem todos os campos necessarios para renderizar a linha (Matriz + Dashboard).
    N-parametrico: funciona com qualquer numero de indicadores, qualquer numero de views."""
    card = data["card"]
    wbr_indicadores = data["wbr"].get("indicadores", {})
    metas_ppi = card.get("metas_ppi", {}) or {}
    kpi_refs = card.get("kpi_references", []) or []
    subnivel = (card.get("metadata") or {}).get("subnivel")
    out = []
    for ref in kpi_refs:
        ind_id = ref.get("indicator_id")
        if not ind_id:
            continue
        papel = ref.get("papel", "")
        is_kpi = _is_kpi_papel(papel)
        # Direction default: from Card.metas_ppi or from kpi_reference, fallback maior_melhor
        direction = (metas_ppi.get(ind_id, {}) or {}).get("direction", "maior_melhor")

        # Coletar matrix_views — se vazio, gerar 1 view default
        views = ref.get("matrix_views") or [{}]
        for view in views:
            mr = _build_matrix_row(ind_id, ref, view, wbr_indicadores, is_kpi, direction,
                                     subnivel=subnivel)
            if mr:
                out.append(mr)
    return out


def _build_matrix_row(ind_id: str, ref: dict, view: dict, wbr_indicadores: dict,
                       is_kpi: bool, default_direction: str,
                       subnivel: str = None) -> dict:
    """Constroi 1 matrix_row a partir de ref + view. Resolve campos com fallbacks heuristicos.
    Refator 2026-05-07: quando actual_ind_id nao bate diretamente no canonical, tenta
    sufixos de subnivel/scope (ex: 'receita_seguros_mensal' + subnivel='wl' →
    'receita_seguros_mensal_wl'). Para indicadores split aspect (qty/volume/pct_ativas),
    a primeira variante encontrada e usada como source — view-level pode override."""
    actual_ind_id = view.get("derived_indicator_id") or ind_id
    ind_entry = wbr_indicadores.get(actual_ind_id, {}) or {}
    # Inferir aspect (qty / volume / pct_ativas / ticket_medio) das pistas do view —
    # usado SEMPRE (mesmo quando ind_entry existe diretamente) para alimentar
    # _meta_from_card_metas_ppi com o aspect certo.
    aspect = None
    n2vf = (view.get("n2_value_field") or "").lower()
    mvf = (view.get("meta_field") or "").lower()
    lvw = (view.get("label") or "").lower()
    if "volume" in n2vf or "volume" in mvf or "vol oport" in lvw or "vol oportunidades" in lvw:
        aspect = "volume"
    elif "qtd_estagnados" in n2vf:
        aspect = "qty"  # estagnadas qty subfield
    elif "qty" in n2vf or "qty" in mvf or "(qty)" in lvw or "quantidade" in lvw:
        aspect = "qty"
    elif "pct" in n2vf or "% ativas" in lvw or "pct_ativas" in mvf:
        aspect = "pct_ativas"
    elif "ticket" in lvw and "pipeline" in lvw:
        aspect = "ticket_medio"
    # Fallback: tentar sufixos comuns quando ind_id base nao bate (canonical SEG-split).
    if not ind_entry and actual_ind_id:
        candidates = []
        # FIX 2026-06-10: convencao divergente do derived_indicator_id entre subniveis.
        # RE emite '{base}_re_pct_ativas' (aspect no fim); WL emite '{base}_pct_ativas_wl'
        # (subnivel no fim). Alguns Cards declaram o padrao WL para ambos. Tentar a
        # forma trocada (subnivel <-> aspect) quando o id literal nao bate.
        _swap = re.match(r"^(.*)_(pct_ativas|qty|volume)_(wl|re)$", actual_ind_id)
        if _swap:
            candidates.append(f"{_swap.group(1)}_{_swap.group(3)}_{_swap.group(2)}")
        # Heuristica para derived_indicator_id com aspect embutido (ex: ..._pct_ativas):
        # detectar sufixo de aspect no nome do ID e inserir subnivel ANTES dele.
        for asp_suffix in ("_pct_ativas", "_qty", "_volume"):
            if subnivel and actual_ind_id.endswith(asp_suffix):
                base = actual_ind_id[: -len(asp_suffix)]
                candidates.append(f"{base}_{subnivel}{asp_suffix}")  # ex: ..._seg_wl_pct_ativas
        if subnivel:
            if aspect:
                candidates.append(f"{actual_ind_id}_{subnivel}_{aspect}")
            candidates.append(f"{actual_ind_id}_{subnivel}")
        if aspect:
            candidates.append(f"{actual_ind_id}_{aspect}")
        candidates.append(f"{actual_ind_id}_n1")
        for cand in candidates:
            if cand in wbr_indicadores:
                actual_ind_id = cand
                ind_entry = wbr_indicadores[cand]
                break
    # Label: view > indicator label > ind_id
    label = view.get("label") or ind_entry.get("label") or ind_id
    # Unidade: view > indicator entry > count.
    # FIX 2026-05-15: canonical JSON (schema v1.1) usa `unit` (ingles) enquanto
    # Card YAML usa `unidade` (portugues). Checar ambos antes do fallback —
    # antes Taxa Conversao com `unit:"ratio"` no canonical nao era detectada,
    # caia em "count" -> fmt_int -> "21" em vez de "21,9%".
    unidade = (view.get("unidade") or view.get("unit")
               or ind_entry.get("unidade") or ind_entry.get("unit")
               or "count")
    # Direction: view > derived ind entry > parent ind entry (FIX img4 — derived
    # indicator pode nao ter direction, mas parent metas_ppi tem)
    direction = (
        view.get("direction")
        or ind_entry.get("direction")
        or default_direction
    )
    return {
        "source_indicator": actual_ind_id,
        "parent_indicator": ind_id,
        "label": label,
        "is_kpi": is_kpi,
        "unidade": unidade,
        "direction": direction,
        "value_field": view.get("value_field"),
        "value_field_fallbacks": view.get("value_field_fallbacks") or [],
        "meta_field": view.get("meta_field"),
        "n2_value_field": view.get("n2_value_field"),
        "n2_value_field_fallbacks": view.get("n2_value_field_fallbacks") or [],
        "n2_meta_field": view.get("n2_meta_field"),
        "compute": view.get("compute"),
        "compute_meta": view.get("compute_meta"),  # FIX rodada 6 issue 8
        "n2_compute": view.get("n2_compute"),
        "n2_compute_meta": view.get("n2_compute_meta"),  # FIX rodada 6 issue 8
        "thresholds": view.get("thresholds") or {},
        "status_n1": ind_entry.get("status"),
        "sub_info_template": view.get("sub_info_template"),
        "n2_sub_info_template": view.get("n2_sub_info_template"),
        "no_meta": view.get("no_meta", False),
        "color_inherit_from_view": view.get("color_inherit_from_view"),
        "sem_esp_ratio": view.get("sem_esp_ratio"),  # FIX rodada 7.5 — pct derivation Sem Esp
        "aspect": aspect,                            # Refator 2026-05-07: qty/volume/pct_ativas/ticket_medio
        # R5-3 (2026-05-07): controle de visibilidade da view por slide. Default = todos.
        # Card pode declarar `slide_visibility: ["fechamento"]` para suprimir a view
        # da Matriz N3 + Dashboard por especialista (ex: Ticket Medio Premio que so
        # faz sentido no slide Fechamento — KPI dependente de ClickHouse com lag).
        "slide_visibility": view.get("slide_visibility") or ["matriz", "dashboard", "fechamento"],
    }


def _meta_from_card_metas_ppi(card: dict, parent_ind_id: str, esp: str = None,
                                 aspect: str = None, horizon: str = None) -> float:
    """Le Card.metas_ppi.{parent_ind_id}.{valor|qty|volume|ticket_medio|...} ou
    .por_especialista.{esp}.{valor|qty|...} quando esp dado.
    Refator 2026-05-07: alimenta slides Dashboard/Matriz/Fechamento quando canonical
    nao traz meta (gap E2 / split por subnivel sem N2 meta gerado pelo m7-controle).

    Refator 2026-05-07 round 2: aceita `aspect` (qty/volume/ticket_medio/pct_ativas)
    para escolher subfield certo. Sem aspect, tenta valor primeiro (overall meta).
    Quando aspect dado, prefere o aspect; senao fallback ao "valor".

    Refator 2026-05-07 round 9: aceita `horizon` ("M0"/"M1"/"M+1"/"proximo_mes"/None).
    Quando horizon e M1, prefere `valor_proximo_mes` (Junho) antes de `valor` (Maio).
    Sem horizon, comportamento inalterado (le `valor` = mes corrente)."""
    if not card or not parent_ind_id:
        return None
    metas_ppi = (card.get("metas_ppi") or {}).get(parent_ind_id) or {}
    if not metas_ppi:
        # #Img1 (2026-06-03): resolucao por PREFIXO — Card pode declarar a chave com
        # sufixo de vertical (ex: parent_map base "tempo_de_ciclo_funil" vs Card
        # "tempo_de_ciclo_funil_con"). Antes retornava None (meta "sem meta").
        _allm = card.get("metas_ppi") or {}
        for _k, _vv in _allm.items():
            if _k.startswith(parent_ind_id):
                metas_ppi = _vv or {}
                break
    if not metas_ppi:
        return None
    # Migracao metas_ppi -> m7Prata.ciclo_metas_ppi (2026-06-12): quando o Card
    # declara `fonte:`/`fonte_n1:`/`fonte_n2:` apontando para ciclo_metas_ppi, o
    # numero no Card eh CACHE — o SoT foi injetado no canonical (E6 Fase 4.5.h por
    # inject_metas_ppi.py). Retornar None faz TODOS os callers deferirem ao
    # canonical (`ind.meta` / `n2.{esp}.meta`), que carrega o valor da tabela.
    # NO-OP enquanto nenhum Card declara fonte: ciclo_metas_ppi (pre-Fase 5).
    _fonte = " ".join(str(metas_ppi.get(_f) or "") for _f in ("fonte", "fonte_n1", "fonte_n2"))
    if "ciclo_metas_ppi" in _fonte:
        return None
    src = (metas_ppi.get("por_especialista") or {}).get(esp) or {} if esp else metas_ppi
    # FIX 2026-05-14 (Bug 3): quando esp pedido mas Card nao tem por_especialista
    # (ou esp ausente do bloco), cair em metas_ppi top-level. Caso classico SEG RE
    # onde Card declara pct_ativas_max=40 no top-level sem por_especialista.
    #
    # FIX 2026-05-15: fallback top-level SO se aspecto for ratio/pct (mesmo
    # alvo se aplica a cada esp). Para aspectos aditivos (qty/volume/valor/
    # ticket_medio), top-level e N1 — se aplicado direto a cada esp gera bug
    # tipo "cada esp tem meta 60 em vez de 30" (Cons criadas: N1=60 = 30
    # Douglas + 30 Tereza). Quando aditivo sem por_especialista declarado,
    # retorna None e deixa o caller usar a meta do canonical n2 entry (correta)
    # ou dividir N1/n_esps na sua propria logica.
    _RATIO_ASPECTS = {"pct_ativas", "pct", "ratio", "taxa", "taxa_conversao"}
    if not src and esp:
        if aspect in _RATIO_ASPECTS:
            src = metas_ppi
        else:
            return None
    if not src:
        return None
    # Round 9: M+1 (proximo_mes) tem prioridade quando horizon=M1
    if horizon in ("M1", "M+1", "proximo_mes"):
        v = src.get("valor_proximo_mes")
        if isinstance(v, (int, float)):
            return v
        if isinstance(v, str):
            s = v.strip().lower()
            if s not in ("pendente", "tbd", "n/a", "na", "—", "-", ""):
                try:
                    return float(s.replace(",", "."))
                except ValueError:
                    pass
        # fallback para valor (M0) se proximo_mes nao definido — mantem comportamento legado
    # Ordem de busca depende do aspect
    if aspect:
        # FIX 2026-05-14 (Bug 3): aceita aliases comuns por aspect.
        # `pct_ativas_max` e usado em Cards SEG (referindo ao maximo aceitavel).
        aspect_aliases = {
            "pct_ativas": ["pct_ativas", "pct_ativas_max"],
        }
        keys = aspect_aliases.get(aspect, [aspect]) + ["valor"]
    else:
        # sem aspect: prefere "valor" (overall), depois qty/volume como fallbacks
        keys = ["valor", "qty", "volume", "ticket_medio", "pct_ativas_max"]
    for k in keys:
        v = src.get(k)
        if v is None:
            continue
        # R5 (2026-05-07): aceitar apenas valores numericos. String sentinels como
        # "pendente" sao tratados como ausencia de meta (return None) — slides
        # consumidores ja sabem renderizar "—" quando meta=None.
        if isinstance(v, (int, float)):
            return v
        if isinstance(v, str):
            s = v.strip().lower()
            if s in ("pendente", "tbd", "n/a", "na", "—", "-", ""):
                return None
            # Tenta parse numerico (fallback para casos onde Card armazena str numerica)
            try:
                return float(s.replace(",", "."))
            except ValueError:
                return None
        return v
    return None


def _card_meta_is_pendente(card: dict, parent_ind_id: str, aspect: str = None, esp: str = None) -> bool:
    """R8 (2026-05-07): retorna True quando Card declara explicitamente meta=pendente
    para o indicador (ou subfield aspect). Usado para suprimir meta canonical no
    Matriz/Dashboard quando usuario marca "sem meta formal" via valor:pendente."""
    if not card or not parent_ind_id:
        return False
    metas_ppi = (card.get("metas_ppi") or {}).get(parent_ind_id) or {}
    if not metas_ppi:
        return False
    src = (metas_ppi.get("por_especialista") or {}).get(esp) or {} if esp else metas_ppi
    if not src and esp:
        src = metas_ppi  # fallback top-level quando esp sem por_especialista
    # Ordem: aspect-specific primeiro, depois "valor"
    keys = ([aspect, "valor"] if aspect else ["valor", "qty", "volume", "ticket_medio", "pct_ativas_max"])
    for k in keys:
        v = src.get(k)
        if v is None:
            continue
        if isinstance(v, str) and v.strip().lower() in ("pendente", "tbd", "n/a", "na", "—", "-"):
            return True
        # Achou um valor concreto — nao eh pendente
        return False
    return False


def _resolve_n1(mr: dict, data: dict) -> dict:
    """Resolve valores N1 para uma matrix_row. Retorna {realizado, meta} ou None."""
    # Caso especial: Ticket Medio Pipeline em SEG-split (cross-id volume/qty)
    # FIX 2026-05-14 (Bug 2 N1 "R$ 1"): so executa o cross-id quando qty_id != vol_id.
    # Em RE (sem aspect-split), qty e volume coexistem na mesma entry —
    # cross-id retorna o mesmo entry e v_real cai em qty (55) ao inves de vol_total.
    # Quando qty_id == vol_id, cair no fluxo padrao (compute via _eval_compute family-aware).
    if mr.get("aspect") == "ticket_medio" and mr.get("compute"):
        indicadores = data["wbr"].get("indicadores", {}) or {}
        subnivel = (data.get("card", {}).get("metadata") or {}).get("subnivel")
        qty_id = _resolve_kpi_id(indicadores, "ativas", subnivel=subnivel, aspect="qty")
        vol_id = _resolve_kpi_id(indicadores, "ativas", subnivel=subnivel, aspect="volume")
        if qty_id and vol_id and qty_id != vol_id:
            qty_e = indicadores.get(qty_id, {})
            vol_e = indicadores.get(vol_id, {})
            q_real = qty_e.get("realizado")
            v_real = vol_e.get("realizado")
            q_meta = qty_e.get("meta")
            v_meta = vol_e.get("meta")
            real = (v_real / q_real) if (q_real and v_real) else None
            meta = (v_meta / q_meta) if (q_meta and v_meta) else None
            if real is not None or meta is not None:
                return {"realizado": real, "meta": meta}

    ind_entry = data["wbr"].get("indicadores", {}).get(mr["source_indicator"], {}) or {}
    if not ind_entry:
        return None
    realizado = _extract_field(ind_entry, mr["value_field"], _N1_VALUE_FALLBACKS, mr.get("compute"))
    if realizado in (None, 0, 0.0):
        fallback_v = _try_value_fallbacks(ind_entry, mr.get("value_field_fallbacks") or [])
        if fallback_v not in (None, 0, 0.0):
            realizado = fallback_v
    # FIX rodada 5 — no_meta: true → nunca render meta
    if mr.get("no_meta"):
        meta_v = None
    elif mr.get("compute_meta"):
        # FIX rodada 6 issue 8 — meta computada via formula (ex: meta_volume / meta_qty)
        meta_v = _eval_compute(mr["compute_meta"], ind_entry)
    else:
        meta_v = _extract_field(ind_entry, mr["meta_field"], _N1_META_FALLBACKS)
        # Refator 2026-05-07: Card.metas_ppi OVERRIDE para N1 quando definido (usuario SoT).
        # Round 2: passa aspect para evitar pegar subfield errado.
        card_meta = _meta_from_card_metas_ppi(
            data.get("card"), mr.get("parent_indicator"), aspect=mr.get("aspect"),
        )
        if card_meta is not None:
            meta_v = card_meta
        # R8 (2026-05-07): Card declara "pendente" explicitamente → suprime meta
        # canonical (visualizacao cinza/sem semaforo). Usuario SoT com valor:pendente.
        # FIX 2026-05-14 (Bug 4): NAO suprimir quando WBR ja tem meta numerica
        # (incluindo 0 — caso zero-target). Card pendente e fallback, nao override.
        elif (_card_meta_is_pendente(data.get("card"), mr.get("parent_indicator"), aspect=mr.get("aspect"))
                and not isinstance(meta_v, (int, float))):
            meta_v = None
    return {"realizado": realizado, "meta": meta_v}


def _resolve_ticket_medio_pipeline_split(mr: dict, esp: str, data: dict) -> dict:
    """Caso especial: Ticket Medio Pipeline = volume_ativas / qty_ativas em IDs
    separados (SEG-split). Em CON, ambos coexistem em 1 ID; em SEG, qty e volume
    sao IDs distintos (`*_seg_wl_qty` + `*_seg_wl_volume`).

    FIX 2026-05-14 (Bug 2): so executa quando qty_id != vol_id. Em RE (sem
    aspect-split), retorna None para deixar o fluxo regular (n2_compute via
    _eval_compute family-aware) computar a partir da mesma entry.
    """
    indicadores = data["wbr"].get("indicadores", {}) or {}
    subnivel = (data.get("card", {}).get("metadata") or {}).get("subnivel")
    qty_id = _resolve_kpi_id(indicadores, "ativas", subnivel=subnivel, aspect="qty")
    vol_id = _resolve_kpi_id(indicadores, "ativas", subnivel=subnivel, aspect="volume")
    if not qty_id or not vol_id or qty_id == vol_id:
        return {"realizado": None, "meta": None, "status": None}
    qty_n2 = (indicadores.get(qty_id, {}).get("n2") or {}).get(esp, {})
    vol_n2 = (indicadores.get(vol_id, {}).get("n2") or {}).get(esp, {})
    q_real = qty_n2.get("realizado")
    v_real = vol_n2.get("realizado")
    q_meta = qty_n2.get("meta")
    v_meta = vol_n2.get("meta")
    real = (v_real / q_real) if (q_real and v_real) else None
    meta = (v_meta / q_meta) if (q_meta and v_meta) else None
    return {"realizado": real, "meta": meta, "status": qty_n2.get("status")}


def _derive_n1_raw_from_dados(data: dict, mr: dict, field_override: str = None):
    """FIX (2026-05-14) Bug 1 — extrai N1 raw (incluindo bridge Sem Especialista) do
    dados_consolidados.json. Usado quando WBR canonical consolidou n1.realizado
    (ou n1.meta) excluindo Sem Especialista (caso scope-restrito, ex: Card Seguros WL).

    Estrategia:
    1. Localiza o indicador em data['dados_consolidados']['indicadores'][]
       via match em `id` / `indicator_id` / source_indicator do mr.
    2. Filtra rows N1-Escritorio do mes_corrente.
    3. Retorna SUM(field).

    Args:
        data: dict com 'dados_consolidados' carregado
        mr: matrix_row da view
        field_override: nome do campo a somar. Quando None, usa mr['value_field']
                        (padrao = 'realizado'). Para meta, passar 'meta'.

    Retorna None quando dados_consolidados ausente ou indicador nao encontrado.
    """
    dados = (data or {}).get("dados_consolidados") or {}
    inds = dados.get("indicadores") or []
    if not inds:
        return None
    # IDs candidatos para match
    candidates = []
    for k in ("source_indicator", "indicator_id", "indicador_id", "ind_id"):
        v = mr.get(k)
        if v:
            candidates.append(str(v))
    # Fallback: source_indicator pode ser inferido do label
    if not candidates and mr.get("label"):
        candidates.append(slugify(mr["label"]))
    if not candidates:
        return None
    target_ind = None
    for ind in inds:
        iid = ind.get("id") or ind.get("indicator_id") or ind.get("ind_id") or ""
        if any(c == iid or c.startswith(iid) or iid.startswith(c) for c in candidates):
            target_ind = ind
            break
    if not target_ind:
        return None
    rows = target_ind.get("rows") or target_ind.get("data") or []
    if not rows:
        return None
    # Mes corrente do WBR
    wbr_meta = (data.get("wbr") or {}).get("metadata") or {}
    mes_corr = (wbr_meta.get("ciclo") or
                (data.get("wbr") or {}).get("data_referencia") or "")[:7]
    if not mes_corr:
        return None
    field = field_override or mr.get("value_field") or "realizado"
    # FIX (2026-05-14) Bug 1 — campo no Card (`realizado_mtd`) pode nao bater com o
    # nome usado nas rows do dados-consolidados (`realizado`). Mapping de aliases
    # entre nomenclatura WBR analyst v1.1 vs raw script output.
    _FIELD_ALIASES = {
        "realizado": ["realizado", "realizado_mtd", "valor", "valor_total"],
        "realizado_mtd": ["realizado_mtd", "realizado", "valor", "valor_total"],
        "meta": ["meta", "meta_mes", "meta_valor", "meta_total"],
        "meta_mes": ["meta_mes", "meta", "meta_valor"],
    }
    field_candidates = _FIELD_ALIASES.get(field, [field])
    total = 0.0
    matched = 0
    for r in rows:
        mes = (r.get("mes") or r.get("data_referencia") or "")[:7]
        if mes != mes_corr:
            continue
        nivel = (r.get("nivel") or "").lower()
        if "n1" not in nivel and nivel not in ("escritorio", "n1-escritorio"):
            continue
        v = None
        for fc in field_candidates:
            cand = r.get(fc)
            if isinstance(cand, (int, float)):
                v = cand
                break
        if isinstance(v, (int, float)):
            total += v
            matched += 1
    return total if matched > 0 else None


def _resolve_n2(mr: dict, esp: str, data: dict, n_esps: int = 0,
                 esp_list: list = None) -> dict:
    """Resolve valores N2 (especialista) para uma matrix_row. Retorna {realizado, meta, status} ou None.

    FIX img1 — Sem Especialista derivado: se esp == 'Sem Especialista' e n2 nao tem entry
    explicita, computar N1 - SUM(N2 esps conhecidos) para indicadores aditivos.

    FIX img3 — Meta NAO e dividida por N para ratios/percent (sao agregados, nao somas).

    FIX rodada 5 — `no_meta: true` na view: nunca renderiza meta nem fallback.
    """
    # Caso especial: Ticket Medio Pipeline em SEG-split (volume e qty em IDs distintos)
    if mr.get("aspect") == "ticket_medio" and mr.get("n2_compute"):
        special = _resolve_ticket_medio_pipeline_split(mr, esp, data)
        if special.get("realizado") is not None or special.get("meta") is not None:
            return special

    ind_entry = data["wbr"].get("indicadores", {}).get(mr["source_indicator"], {}) or {}
    n2_dict = ind_entry.get("n2") or ind_entry.get("por_especialista") or {}
    e = n2_dict.get(esp)

    # FIX rodada 7 issue 1 — Sem Especialista UNIVERSAL: nunca tem meta nem semaforo.
    # Sem Esp representa receita/volume sem dono — apenas referencia, nao gerenciavel.
    # Universal para qualquer Card/vertical.
    sem_esp = (esp == "Sem Especialista")

    # FIX rodada 7.5 — Sem Esp pct derivation via ratio cross-indicator declarado no Card.
    # Ex: Estagnadas % ativas Sem Esp = (qtd_estag_sem_esp / qtd_ativas_sem_esp) × 100
    # onde cada componente vem de N1 - SUM(esps) do indicador correspondente.
    if e is None and esp == "Sem Especialista" and esp_list and mr.get("sem_esp_ratio"):
        ratio_cfg = mr["sem_esp_ratio"]
        def _smart_lookup(d: dict, path: str):
            """_dig + leaf fallback + family fallback. Para schemas v1.1 onde Card
            declara dotted-path mas analyst emite flat."""
            v = _dig(d, path)
            if v is not None:
                return v
            if "." in path:
                leaf = path.rsplit(".", 1)[-1]
                v = _dig(d, leaf)
                if v is not None:
                    return v
                family = _FIELD_FAMILY_FALLBACKS.get(leaf)
                if family:
                    for f in family:
                        v = _dig(d, f)
                        if v is not None:
                            return v
            family = _FIELD_FAMILY_FALLBACKS.get(path)
            if family:
                for f in family:
                    v = _dig(d, f)
                    if v is not None:
                        return v
            return None

        def _derive_sem_esp_from(cfg_part):
            ind_id = cfg_part.get("indicator")
            n1_path = cfg_part.get("n1_path")
            n2_path = cfg_part.get("n2_path")
            if not ind_id or not n1_path or not n2_path:
                return None
            ind_other = data["wbr"].get("indicadores", {}).get(ind_id, {}) or {}
            n1_v = _smart_lookup(ind_other, n1_path)
            if not isinstance(n1_v, (int, float)):
                return None
            n2_other = ind_other.get("n2") or ind_other.get("por_especialista") or {}
            sum_v = 0
            count = 0
            for _e in esp_list:
                v = _smart_lookup(n2_other.get(_e) or {}, n2_path)
                if isinstance(v, (int, float)):
                    sum_v += v
                    count += 1
            if count == 0:
                return None
            return n1_v - sum_v
        num_se = _derive_sem_esp_from(ratio_cfg.get("numerator") or {})
        den_se = _derive_sem_esp_from(ratio_cfg.get("denominator") or {})
        if num_se is not None and den_se and den_se > 0:
            mult = ratio_cfg.get("multiplier") or 1
            pct = (num_se / den_se) * mult
            return {"realizado": pct, "meta": None, "status": None,
                    "_derived": True, "_sem_esp": True}
        # falhou — cai no fluxo padrao (retornara None)

    # FIX img1: Sem Especialista derivado para indicadores aditivos quando JSON nao traz
    if e is None and esp == "Sem Especialista" and esp_list:
        unidade = mr.get("unidade", "count")
        n2_compute = mr.get("n2_compute")
        # FIX rodada 6 issue 2 — Sem Esp derivado para indicadores compute (ex: Ticket Medio)
        if n2_compute and mr.get("compute"):
            derived = _derive_compute_sem_esp(mr, ind_entry, esp_list, n2_dict)
            if derived is not None:
                # FIX rodada 7 issue 1 — Sem Esp sempre meta=None
                return {"realizado": derived, "meta": None,
                        "status": None, "_derived": True, "_sem_esp": True}
            return None
        if unidade in ("count", "BRL", "qty"):  # so para aditivos
            n1_real = _extract_field(
                ind_entry, mr["value_field"], _N1_VALUE_FALLBACKS, mr.get("compute")
            ) or _try_value_fallbacks(ind_entry, mr.get("value_field_fallbacks") or [])
            # FIX (2026-05-14) Bug 1: quando WBR canonical consolidou n1.realizado
            # como SUM(n2_visible_esps) — descartando o bridge "Sem Especialista" do
            # raw data — buscamos o N1 verdadeiro em dados_consolidados (rows N1-
            # Escritorio agregadas em Maio). Cobre o caso Seguros WL onde scope =
            # Claudia+Tarcisio mas raw tem ~R$ 190K em assessores nao-mapeados.
            n1_raw = _derive_n1_raw_from_dados(data, mr) if data else None
            if isinstance(n1_raw, (int, float)) and n1_raw > 0:
                # Prefer raw quando bate ou e maior que n1_real (cur evidencia de
                # consolidacao restrita). Caso contrario mantem n1_real.
                if not isinstance(n1_real, (int, float)) or n1_raw > n1_real:
                    n1_real = n1_raw
            if isinstance(n1_real, (int, float)):
                sum_esps = 0
                count_resolved = 0
                for _esp in esp_list:
                    e_other = n2_dict.get(_esp)
                    if e_other is None:
                        continue
                    v = _extract_field(e_other, mr["n2_value_field"], _N2_VALUE_FALLBACKS,
                                        mr.get("n2_compute"))
                    if isinstance(v, (int, float)):
                        sum_esps += v
                        count_resolved += 1
                # So calcular se conseguimos somar pelo menos 1 esp (senao nao e confiavel)
                if count_resolved > 0:
                    derived = n1_real - sum_esps
                    if derived > 0:
                        # FIX rodada 7 issue 1 — Sem Esp sempre meta=None
                        return {"realizado": derived, "meta": None,
                                "status": None, "_derived": True, "_sem_esp": True}
        return None

    if e is None:
        return None

    # FIX (2026-05-14) Bug "% ativas Douglas 49,2%" (era pct_atingimento, deveria ser
    # o pct_ativas metric value 81,3%): analyst v1.1 emite o metric value como
    # `realizado` no derived indicator _pct_ativas, e usa `pct` para o pct_atingimento
    # (meta/real ratio). Card declara n2_value_field=pct mas isso pega o atingimento
    # ao inves do metric. Detectar e usar `realizado`.
    if (mr.get("source_indicator", "").endswith("_pct_ativas")
            and mr.get("n2_value_field") == "pct"
            and isinstance(e.get("realizado"), (int, float))):
        realizado = e["realizado"]
    else:
        realizado = _extract_field(e, mr["n2_value_field"], _N2_VALUE_FALLBACKS, mr.get("n2_compute"))
    if realizado in (None, 0, 0.0):
        fallback_v = _try_value_fallbacks(e, mr.get("n2_value_field_fallbacks") or [])
        if fallback_v not in (None, 0, 0.0):
            realizado = fallback_v

    # FIX rodada 5 — `no_meta: true`: nunca renderiza meta
    if mr.get("no_meta"):
        meta_v = None
    elif mr.get("n2_compute_meta"):
        # FIX rodada 6 issue 8 — meta N2 computada via formula
        meta_v = _eval_compute(mr["n2_compute_meta"], e)
        if meta_v is None:
            # Fallback: ratios tem mesma meta entre N1 e N2 — avalia contra ind_entry
            meta_v = _eval_compute(mr["n2_compute_meta"], ind_entry)
    else:
        # FIX (2026-05-14) bug Vol Ativas meta=19 qty: quando n2_meta_field nao declarado
        # e n2_value_field e volume-family, inferir meta_volume — evita fallback cair em
        # "meta" (qty) e mostrar "meta R$ 19" no slot de volume.
        n2_meta_field = mr.get("n2_meta_field")
        if not n2_meta_field:
            n2_vf = (mr.get("n2_value_field") or "").lower()
            if n2_vf in ("volume", "vol", "volume_total", "vol_total"):
                n2_meta_field = "meta_volume"
            elif n2_vf in ("qty", "realizado_qty"):
                n2_meta_field = "meta_qty"
        meta_v = _extract_field(e, n2_meta_field, _N2_META_FALLBACKS)
        has_compute = bool(mr.get("compute") or mr.get("n2_compute"))
        unidade = mr.get("unidade", "count")
        is_additive = unidade in ("count", "BRL", "qty")
        # FIX rodada 5 — fallback so se meta_field declarada (autor pode omitir intencionalmente)
        has_meta_field = bool(mr.get("meta_field"))
        # FIX (2026-05-14): quando N2 entry nao tem meta_volume/meta_qty E ind_entry tambem
        # nao tem, fallback adicional para Card.metas_ppi.{ind}.{volume|qty|...} (com aspect).
        # Resolve o caso de KPIs declaradamente 50/50 entre esps (Card nao declara
        # por_especialista). Antes: Dashboard Vol Oport Ativas N2 meta = '—' apesar de Card
        # declarar volume=R$ 40,6M no top-level. Agora: divide N1 do Card por n_esps.
        def _n1_meta_for_division():
            v = _extract_field(ind_entry, mr.get("meta_field"), _N1_META_FALLBACKS)
            if isinstance(v, (int, float)) and v > 0:
                return v
            v = _meta_from_card_metas_ppi(
                data.get("card"), mr.get("parent_indicator"), aspect=mr.get("aspect"),
            )
            return v if isinstance(v, (int, float)) and v > 0 else None
        if meta_v is None and n_esps > 0 and not has_compute and is_additive and (has_meta_field or mr.get("parent_indicator")):
            n1_meta = _n1_meta_for_division()
            if n1_meta:
                meta_v = n1_meta / n_esps
        elif meta_v is None and not has_compute and not is_additive and (has_meta_field or mr.get("parent_indicator")):
            n1_meta = _n1_meta_for_division()
            if n1_meta is not None:
                meta_v = n1_meta

    status_e = e.get("status_mtd") or e.get("status") or ind_entry.get("status")
    # FIX rodada 7 issue 1 — Sem Especialista UNIVERSAL: meta=None, status=None
    if sem_esp:
        return {"realizado": realizado, "meta": None, "status": None, "_sem_esp": True}
    # Refator 2026-05-07: Card.metas_ppi.por_especialista OVERRIDE quando definido.
    # Round 2: passa aspect (qty/volume/...) para escolher subfield certo do Card
    # (evita pegar `qty` quando view e Volume).
    if not mr.get("no_meta"):
        card_meta = _meta_from_card_metas_ppi(
            data.get("card"), mr.get("parent_indicator"), esp=esp,
            aspect=mr.get("aspect"),
        )
        if card_meta is not None:
            meta_v = card_meta
        # R8 (2026-05-07): "pendente" explicito no Card → suprime meta canonical N2.
        # FIX 2026-05-14 (Bug 4): NUNCA suprimir quando WBR ja tem meta numerica
        # (incluindo meta=0 — caso "zero target" como sem_atividade_planejada).
        # Card "pendente" e fallback default, nao override de dado WBR concreto.
        elif (_card_meta_is_pendente(data.get("card"), mr.get("parent_indicator"),
                                       aspect=mr.get("aspect"), esp=esp)
                and not isinstance(meta_v, (int, float))):
            meta_v = None
            status_e = None  # sem meta = sem semaforo (cinza)
    return {"realizado": realizado, "meta": meta_v, "status": status_e}


def _try_value_fallbacks(entry: dict, fallbacks: list):
    """Tenta uma lista de field paths em ordem; retorna primeiro non-None."""
    for f in fallbacks:
        v = _dig(entry, f)
        if v is not None:
            return v
    return None


# Formatadores disponiveis em sub_info_template ({field|formatter})
_TPL_FORMATTERS = {
    "brl_compact": lambda v: fmt_brl(v, compact=True) if v is not None else "—",
    "brl_full":    lambda v: fmt_brl(v, compact=False) if v is not None else "—",
    "pct_inline":  lambda v: fmt_pct(v, 0) if v is not None else "—",
    "pct1":        lambda v: fmt_pct(v, 1) if v is not None else "—",
    "int":         lambda v: fmt_int(v) if v is not None else "—",
    "days":        lambda v: f"{int(v)}d" if isinstance(v, (int, float)) else "—",
}


def render_sub_info(template: str, entry: dict) -> str:
    """Renderiza sub_info_template substituindo {field|formatter} pelos valores de entry.
    Suporta:
      - {field|formatter} → aplica formatter ao campo
      - {field} → string crua
      - {expr|formatter} onde expr pode ter operadores +/-/*/ (delegado a _eval_compute)
    N-parametrico — funciona com qualquer field path do entry."""
    if not template or not entry:
        return ""
    def _replace(m):
        token = m.group(1)
        if "|" in token:
            field_or_expr, formatter = token.rsplit("|", 1)
            formatter = formatter.strip()
        else:
            field_or_expr, formatter = token, None
        # Se field_or_expr tem operador, usar compute
        if any(op in field_or_expr for op in "/*+-"):
            v = _eval_compute(field_or_expr, entry)
        else:
            v = _dig(entry, field_or_expr.strip())
        if formatter and formatter in _TPL_FORMATTERS:
            return _TPL_FORMATTERS[formatter](v)
        return str(v) if v is not None else "—"
    return re.sub(r"\{([^}]+)\}", _replace, template)


# Heuristic field lookup orders (N-parametric defaults).
# Quando matrix_view nao especifica value_field/meta_field, tentar essas chaves em ordem.
_N1_VALUE_FALLBACKS = [
    "realizado_mtd", "realizado", "realizado_qty",
    "realizado_lagging_competencia_maio",  # Consorcios specific
]
_N1_META_FALLBACKS = ["meta", "meta_mes_corrente", "meta_qty", "meta_volume"]
_N2_VALUE_FALLBACKS = [
    "realizado_mtd", "realizado", "qty",
    "realizado_competencia_maio", "lagging_competencia_junho",
]
_N2_META_FALLBACKS = ["meta_mes", "meta", "meta_qty", "meta_volume"]


_FIELD_FAMILY_FALLBACKS = {
    # Volume requested: aceita vol/volume/vol_total/volume_total (analyst v1.1 emite "vol")
    "volume": ["vol", "volume_total", "vol_total", "volume_brl"],
    "volume_total": ["vol_total", "vol", "volume", "volume_brl"],
    # Qty requested: aceita realizado/qty (analyst v1.1 emite "realizado" para qty)
    "qty": ["realizado_mtd", "realizado", "quantidade"],
    "realizado_qty": ["realizado_mtd", "realizado", "qty", "quantidade"],
    # FIX (2026-05-14) Bug Estagnadas qty=81: Card declara qtd_estagnados (typo)
    # mas analyst v1.1 emite qty_estagnadas. Aliases bidirecionais.
    "qtd_estagnados": ["qty_estagnadas", "estagnados_qty", "estagnadas_qty", "qty_estag", "qtd_estag"],
    "qty_estagnadas": ["qtd_estagnados", "estagnados_qty", "estagnadas_qty", "qty_estag", "qtd_estag"],
    "qtd_ativos": ["qty_ativas", "ativas_qty", "ativos_qty"],
    "qty_ativas": ["qtd_ativos", "ativas_qty", "ativos_qty"],
    # Meta volume: aceita variantes
    "meta_volume": ["meta_vol", "meta_volume_total"],
    "meta_qty": ["meta", "meta_mes", "meta_qty_mensal"],
}


def _extract_field(entry: dict, field: str, fallbacks: list, compute: str = None):
    """Extrai um valor de entry. Se compute presente, avalia formula 'a/b' ou 'a*b'.
    Senao usa field se especificado; se field falhar (None), tenta fallbacks em ordem.

    FIX bug Volume tiny values (2026-05-14): quando n2_value_field="volume" e o JSON
    emite "vol" (analyst v1.1), o fallback chain caia em "realizado" (que e qty) e
    pintava qty no slot de volume — gerando "R$ 3" no Vol Oportunidades Ativas Sem Esp.
    Agora o lookup tem family-aware fallbacks: se voce pede "volume", tenta primeiro
    todas as variantes de volume (vol/volume_total/vol_total) antes de cair no
    fallback generico. Mesmo para "qty".
    """
    if compute:
        return _eval_compute(compute, entry)
    if field:
        v = _dig(entry, field)
        if v is not None:
            return v
        # FIX: field-family-aware fallback — para "volume", so retorna se encontrar
        # variante da MESMA familia. NUNCA cai em fallback generico que misture qty/volume.
        family = _FIELD_FAMILY_FALLBACKS.get(field)
        # FIX (2026-05-14): dotted paths (ex: "componentes.qtd_estagnados") — quando
        # o caminho falha, tentar a chave do ULTIMO segmento como flat field (analyst
        # v1.1 emite "qty_estagnadas" no top level do indicator, nao em "componentes.qtd_estagnados").
        # Aplica family check no leaf tambem.
        if family is None and "." in field:
            leaf = field.rsplit(".", 1)[-1]
            v = _dig(entry, leaf)
            if v is not None:
                return v
            family = _FIELD_FAMILY_FALLBACKS.get(leaf)
        if family is not None:
            for f in family:
                v = _dig(entry, f)
                if v is not None:
                    return v
            # Familia declarada e nada encontrado — retorna None (deixa N1-division fallback rodar)
            # NAO cai em _N2_META_FALLBACKS (que pegaria "meta" qty quando voce pediu meta_volume).
            return None
        # field declarado mas retornou None — tentar fallbacks como salvaguarda
    for f in fallbacks:
        v = _dig(entry, f)
        if v is not None:
            return v
    return None


def _dig(d: dict, path: str):
    """Lookup com suporte a dotted path."""
    if not isinstance(d, dict) or not path:
        return None
    cur = d
    for part in path.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
        if cur is None:
            return None
    return cur


def _derive_compute_sem_esp(mr: dict, ind_entry: dict, esp_list: list, n2_dict: dict):
    """FIX rodada 6 issue 2 — deriva valor Sem Especialista para matrix views com compute.

    Usa N1 compute (e.g. 'volume_total / realizado_qty') para identificar fields
    do N1 entry, e N2 compute (e.g. 'volume / qty') para identificar fields nas
    N2 entries. Para cada par (a_n1, a_n2), calcula:
        sem_esp_a = N1[a_n1] - SUM(N2[esp][a_n2] for esp in esp_list)
    Aplica entao a operacao do compute.

    Suporta operadores /, *, +, -. Retorna float ou None se nao puder derivar."""
    n1_compute = mr.get("compute")
    n2_compute = mr.get("n2_compute")
    if not n1_compute or not n2_compute:
        return None

    def _split(formula):
        for op in ("/", "*", "+", "-"):
            if op in formula:
                a, b = formula.split(op, 1)
                return op, a.strip(), b.strip()
        return None, formula.strip(), None

    op1, a1, b1 = _split(n1_compute)
    op2, a2, b2 = _split(n2_compute)
    if op1 != op2 or b1 is None or b2 is None:
        return None

    def _derive(n1_field, n2_field):
        n1_val = _dig(ind_entry, n1_field)
        if not isinstance(n1_val, (int, float)):
            return None
        sum_esps, count = 0, 0
        for _esp in esp_list:
            e_other = n2_dict.get(_esp) or {}
            v = _dig(e_other, n2_field)
            if isinstance(v, (int, float)):
                sum_esps += v
                count += 1
        if count == 0:
            return None
        return n1_val - sum_esps

    a = _derive(a1, a2)
    b = _derive(b1, b2)
    if a is None or b is None:
        return None
    try:
        a, b = float(a), float(b)
    except (TypeError, ValueError):
        return None
    if op1 == "/":
        return a / b if b != 0 else None
    if op1 == "*":
        return a * b
    if op1 == "+":
        return a + b
    if op1 == "-":
        return a - b
    return None


def _eval_compute(formula: str, entry: dict):
    """Avalia formulas simples 'a/b', 'a*b', 'a+b', 'a-b' com chaves de entry como variaveis.
    Suporta dotted paths (ex: 'componentes.qtd_estagnados/componentes.qtd_ativos').
    NAO usa eval() — parser manual seguro.

    FIX 2026-05-14 (Bug 2 — Ticket Medio "R$ 1"): compute 'volume_total / realizado_qty'
    falhava silenciosamente quando analyst v1.1 emite 'vol' e 'realizado' (sem '_total'
    e '_qty' suffixes). Agora aplica _FIELD_FAMILY_FALLBACKS quando o nome direto falha,
    paralelo a _extract_field.
    """
    def _lookup(d: dict, name: str):
        v = _dig(d, name)
        if v is not None:
            return v
        # Family-aware fallback (mesma estrategia de _extract_field)
        family = _FIELD_FAMILY_FALLBACKS.get(name)
        if family is None and "." in name:
            leaf = name.rsplit(".", 1)[-1]
            v = _dig(d, leaf)
            if v is not None:
                return v
            family = _FIELD_FAMILY_FALLBACKS.get(leaf)
        if family:
            for f in family:
                v = _dig(d, f)
                if v is not None:
                    return v
        return None
    for op in ["/", "*", "+", "-"]:
        if op in formula:
            parts = formula.split(op, 1)
            a_str, b_str = parts[0].strip(), parts[1].strip()
            a = _lookup(entry, a_str)
            b = _lookup(entry, b_str)
            if a is None or b is None:
                return None
            try:
                a, b = float(a), float(b)
            except (TypeError, ValueError):
                return None
            if op == "/":
                return a / b if b != 0 else None
            if op == "*":
                return a * b
            if op == "+":
                return a + b
            if op == "-":
                return a - b
    # Sem operador — apenas lookup direto (com family fallback)
    return _lookup(entry, formula)


# ============================================================
# Renderers — Matriz (Slide 3)
# ============================================================

def render_matriz(data: dict, ctx: dict) -> dict:
    """Slide 3 Matriz — render rows, headers, fractions, callout.
    Refatorado (2026-05-05): usa matrix_rows declarativos via _resolve_matrix_rows().
    N-parametrico: itera sobre Card.kpi_references[].matrix_views[] para suportar
    qualquer numero de indicadores compostos (ex: ativas qty/volume/ticket)."""
    wbr = data["wbr"]
    esp_list = ctx["_esp_list"]
    nivel = ctx["NIVEL"]

    # Columns: Indicador + Sem Especialista + N esp + Total
    n_cols_data = 1 + len(esp_list) + 1
    fractions = " ".join(["1fr"] * n_cols_data)

    # Headers
    headers = ['<div class="col-noesp">Sem Especialista</div>']
    tones = ["", "tone-2", "tone-3", "tone-4"]
    for i, esp in enumerate(esp_list):
        tone_cls = tones[min(i, 3)]
        cls = f"col-esp {tone_cls}".strip()
        headers.append(f'<div class="{cls}">{esp}</div>')

    # Resolve matrix rows declarativamente. Passa all_rows para resolver color_inherit_from_view.
    matrix_rows = _resolve_matrix_rows(data, ctx)
    # R5-3 (2026-05-07): respeitar slide_visibility — Card pode declarar
    # `slide_visibility: ["fechamento"]` para suprimir view da Matriz N3.
    matrix_rows = [mr for mr in matrix_rows if "matriz" in (mr.get("slide_visibility") or ["matriz"])]
    # F1 (2026-05-07): ordem canonica dos KPIs Resultado: Volume → Receita → Quantidade
    # (independente da ordem que aparecerem em kpi_references[]). PPIs mantem ordem do Card.
    _KPI_ORDER = ("volume", "receita", "quantidade")
    def _kpi_sort_key(mr):
        ind_id = (mr.get("indicator_id") or mr.get("label") or "").lower()
        for i, kw in enumerate(_KPI_ORDER):
            if kw in ind_id:
                return (i, mr.get("indicator_id", ""))
        return (len(_KPI_ORDER), mr.get("indicator_id", ""))  # outros KPIs no fim

    kpi_rows_raw = [mr for mr in matrix_rows if mr["is_kpi"]]
    kpi_rows_raw.sort(key=_kpi_sort_key)
    rows_kpi = [_matriz_row_v2(mr, esp_list, data, all_rows=matrix_rows) for mr in kpi_rows_raw]
    rows_ppi = [_matriz_row_v2(mr, esp_list, data, all_rows=matrix_rows) for mr in matrix_rows if not mr["is_kpi"]]

    # FIX item 3 — auto-aplica modo dense conforme N rows (1080px capacity):
    # - > 10 rows: ultra-dense (font 11/9, padding 5)
    # - > 9 rows: dense (font 13/10, padding 8)
    # - <= 9: default
    total_rows = len(matrix_rows)
    if total_rows > 10:
        grid_class = "ultra-dense"
    elif total_rows > 9:
        grid_class = "dense"
    else:
        grid_class = ""

    # FIX rodada 6 issue 3 — recomputa contagem de vermelhos via iteracao das
    # matrix_rows. FIX rodada 7 issue 2 — dedupe por parent_indicator (Estagnadas
    # qty + Estagnadas % ativas tem mesmo parent → 1 indicador) + lista todos
    # vermelhos (nao corta em 2).
    parent_status = {}  # {parent_indicator: pior_cls vista entre views}
    parent_label = {}   # {parent_indicator: label canonico (primeiro com meta)}
    verdes_n = amarelos_n = mtd_insuf_n = 0
    cls_rank = {"bad": 3, "warn": 2, "good": 1, "mute": 0}
    for mr in matrix_rows:
        # views com color_inherit_from_view nao contam separadamente — herdam do irmao
        if mr.get("color_inherit_from_view"):
            continue
        n1 = _resolve_n1(mr, data) or {}
        realizado = n1.get("realizado")
        meta = n1.get("meta")
        # FIX 2026-05-14 (Bug 1.5): normaliza ratio antes do pct atingimento.
        if mr.get("unidade") == "ratio":
            if isinstance(meta, (int, float)) and abs(meta) <= 1.0:
                meta = meta * 100
            if isinstance(realizado, (int, float)) and abs(realizado) <= 1.0:
                realizado = realizado * 100
        parent = mr.get("parent_indicator") or mr.get("source_indicator") or mr["label"]
        if mr.get("no_meta") or realizado is None:
            cls = "mute"
        elif not isinstance(realizado, (int, float)) or not isinstance(meta, (int, float)) or meta == 0:
            cls = "mute"
        else:
            direction = mr.get("direction", "maior_melhor")
            try:
                if direction == "menor_melhor":
                    pct = (meta / max(realizado, 1e-9)) * 100
                else:
                    pct = (realizado / meta) * 100
                cls = _class_3tier(pct, direction)
            except (TypeError, ZeroDivisionError):
                cls = "mute"
        # Mantem PIOR cls visto para esse parent
        if parent not in parent_status or cls_rank.get(cls, 0) > cls_rank.get(parent_status[parent], 0):
            parent_status[parent] = cls
            parent_label[parent] = mr["label"]
        elif cls != "mute" and parent not in parent_label:
            parent_label[parent] = mr["label"]

    vermelhos_labels = []
    for parent, cls in parent_status.items():
        if cls == "bad":
            vermelhos_labels.append(parent_label.get(parent, parent))
        elif cls == "warn":
            amarelos_n += 1
        elif cls == "good":
            verdes_n += 1
        else:
            mtd_insuf_n += 1

    # C1 (2026-05-07): callout reformulado em estilo LIDE jornalistico.
    # Override via Card.apresentacao.matriz_lide_override (string HTML) tem
    # precedencia. Se ausente, gera Lide programatico em manchete unica
    # (pyramid invertida: most critical first).
    apres = data.get("card", {}).get("apresentacao") or {}
    lide_override = apres.get("matriz_lide_override")

    total_inds = verdes_n + amarelos_n + len(vermelhos_labels) + mtd_insuf_n
    ciclo_lbl = ctx.get("CICLO_LABEL", "ciclo")
    vertical_nome = (data.get("card", {}).get("metadata") or {}).get("vertical_crm") or nivel or "Vertical"

    if lide_override:
        callout_class = "bad" if vermelhos_labels else ""
        callout_body = lide_override
    elif vermelhos_labels:
        callout_class = "bad"
        top2 = vermelhos_labels[:2]
        resto = len(vermelhos_labels) - len(top2)
        manchete_indicadores = " e ".join(f"<strong>{lbl}</strong>" for lbl in top2)
        if resto > 0:
            manchete_indicadores += f" (+ {resto} outros)"
        callout_body = (
            f"{vertical_nome} fechou {ciclo_lbl} com "
            f"<strong>{len(vermelhos_labels)}/{total_inds} indicadores em vermelho</strong>, "
            f"puxados por {manchete_indicadores}. "
            f"Ritual prioriza contramedidas para reverter o cenario antes "
            f"do proximo checkpoint."
        )
    else:
        callout_class = ""
        callout_body = (
            f"{vertical_nome} fechou {ciclo_lbl} "
            f"<strong>sem indicadores Vermelhos</strong> — "
            f"{verdes_n} verde(s), {amarelos_n} amarelo(s), "
            f"{mtd_insuf_n} sem MTD suficiente. "
            f"Foco do ritual em manter ritmo + acelerar amarelos."
        )

    # FIX rodada 6 issue 1 — total_label generico do Card (fallback "{nivel} Total")
    total_label = (data["card"].get("metadata") or {}).get("total_label") or f"{nivel} Total"

    return {
        "MX_COLS_SPEC_FRACTIONS": fractions,
        "MX_HEADERS": "\n".join(headers),
        "NIVEL_TOTAL_LABEL": total_label,
        "MX_ROWS_KPI": "\n".join(rows_kpi) or '<div class="mx-row data"><div class="col-ind" style="grid-column:1/-1;color:var(--verde-claro);font-style:italic;">Sem KPIs no Card.</div></div>',
        "MX_ROWS_PPI": "\n".join(rows_ppi) or '<div class="mx-row data"><div class="col-ind" style="grid-column:1/-1;color:var(--verde-claro);font-style:italic;">Sem PPIs no Card.</div></div>',
        "MX_CALLOUT_CLASS": callout_class,
        "MX_CALLOUT_BODY": callout_body,
        "MX_GRID_CLASS": grid_class,
    }


def _vol_estagnado_for_esp(data: dict, esp: str) -> float:
    """S1-A2 (2026-05-15): Agrega volume_estagnado por esp lendo dados_consolidados.

    IMPORTANTE: o dados_consolidados emite 2 niveis de rows N2-Especialista:
      (a) rows agregadas (estagio=null/empty) — soma por esp
      (b) rows detalhadas por estagio (estagio="Proposta", "ApresentacaO", etc)
    A soma de (a) + (b) duplica o valor. Filtrar APENAS rows agregadas (sem
    estagio) para nao contar 2x. Se a row agregada nao existir, somar as
    detalhadas por estagio como fallback.

    Retorna 0 quando dados_consolidados ausente ou esp nao encontrado.
    SoT temporario ate S2-B4 (m7-controle E6 emitir n2.{esp}.volume_estagnado
    diretamente no WBR canonical).
    """
    dados_n5 = (data or {}).get("dados_consolidados") or {}
    if not dados_n5:
        return 0.0
    for entry in dados_n5.get("indicadores", []) or []:
        ind_id = entry.get("indicator_id") or ""
        if not ind_id.startswith("oportunidades_estagnadas_funil"):
            continue
        if ind_id.endswith("_pct_ativas"):
            continue
        agg = 0.0
        agg_found = False
        per_stage = 0.0
        for row in entry.get("data", []) or []:
            if row.get("nivel") != "N2-Especialista":
                continue
            if row.get("especialista") != esp:
                continue
            v = row.get("volume") or 0
            if not isinstance(v, (int, float)):
                continue
            estagio = row.get("estagio")
            if estagio in (None, "", "null"):
                # Row agregada por esp (sem stage)
                agg += float(v)
                agg_found = True
            else:
                per_stage += float(v)
        return agg if agg_found else per_stage
    return 0.0


def _vol_estagnado_for_total(data: dict, esp_list: list) -> float:
    """Volume estagnado total (soma de todos os esps + Sem Esp se houver)."""
    total = 0.0
    for esp in (esp_list or []):
        total += _vol_estagnado_for_esp(data, esp)
    # Top-level: alguns canonicals tem `vol_em_risco` (=volume estagnado total).
    # Usar como fallback se nada agregou via esps.
    if total == 0:
        wbr_ind = (data or {}).get("wbr", {}).get("indicadores", {}) or {}
        for ind_id, ind in wbr_ind.items():
            if "estagnadas_funil" in ind_id and "_pct_ativas" in ind_id:
                v = (ind or {}).get("vol_em_risco")
                if isinstance(v, (int, float)):
                    return float(v)
    return total


def _pct_sem_atividade_for_esp(data: dict, esp: str) -> float:
    """S1-A2 (2026-05-15): pct sem_atividade / ativas para um esp.
    Lê qty_sem_atividade do WBR canonical (n2.{esp}.realizado do indicador
    'oportunidades_sem_atividade_planejada_funil*') e qty_ativas do indicador
    'oportunidades_ativas_funil' (base — exclui *_volume e *_pct_ativas que
    sao derived com unidades diferentes). Retorna pct ou 0.
    """
    indicadores = (data or {}).get("wbr", {}).get("indicadores", {}) or {}
    qty_sa = None
    qty_at = None
    # Suffixes a excluir do match de ativas (derived indicators com unidade BRL/pct)
    _excluded_ativas_suffixes = ("_volume", "_pct_ativas", "_vol")
    for ind_id, ind in indicadores.items():
        if not isinstance(ind, dict):
            continue
        n2_esp = ((ind.get("n2") or ind.get("por_especialista") or {}).get(esp) or {})
        if not n2_esp:
            continue
        if "sem_atividade_planejada_funil" in ind_id:
            v = n2_esp.get("realizado") or n2_esp.get("qty") or n2_esp.get("realizado_mtd")
            if isinstance(v, (int, float)):
                qty_sa = float(v)
        elif "oportunidades_ativas_funil" in ind_id and not any(
                ind_id.endswith(suf) for suf in _excluded_ativas_suffixes):
            v = n2_esp.get("qty") or n2_esp.get("realizado") or n2_esp.get("realizado_mtd")
            if isinstance(v, (int, float)):
                qty_at = float(v)
    if qty_at and qty_at > 0 and qty_sa is not None:
        return (qty_sa / qty_at) * 100
    return 0.0


def _matriz_row_v2(mr: dict, esp_list: list, data: dict, all_rows: list = None) -> str:
    """Render 1 row da Matriz (declarativo, N-parametrico).
    FIX rodada 5 — `color_inherit_from_view` resolve cor a partir de irmao na mesma matrix
    (ex: Estagnadas qty pega cor de Estagnadas % ativas que tem meta+semaforo).
    `no_meta=True` na view: nunca mostra meta (so realizado + cor herdada)."""
    label = mr["label"]
    unidade = mr["unidade"]
    direction = mr["direction"]
    sub_tpl_n1 = mr.get("sub_info_template")
    sub_tpl_n2 = mr.get("n2_sub_info_template")
    inherit_from = mr.get("color_inherit_from_view")
    # S1-A2 (2026-05-15): detecta view "Oport. Estagnadas (qty)" para enriquecer
    # cell display com volume estagnado entre parenteses ("24 (R$ 5,2M)").
    # Match agnostico ao Card: label contendo "estagnadas" + "(qty)" + unidade=count.
    # Cobre CON (n2_value_field=qtd_estagnados) e SEG WL/RE (n2_value_field=realizado).
    _lbl_lc = (label or "").lower()
    is_estagnadas_qty_view = (
        unidade == "count"
        and "estagnadas" in _lbl_lc
        and "(qty)" in _lbl_lc
    )
    # S1-A2 (2026-05-15): detecta view "Sem Ativ. ou Atras. CRM" para enriquecer
    # display com "qty (X%)" onde X% = qty_sem_atividade / qty_ativas. Cor segue
    # regra proporcional (override do menor_melhor binario): 0=verde,
    # 0-20%=amarelo, 21%+=vermelho. Match agnostico via label.
    is_sem_atividade_view = (
        unidade == "count"
        and ("sem ativ" in _lbl_lc or "sem atividade" in _lbl_lc)
    )

    def _resolve_inherited_cls(esp_or_n1: str) -> str:
        """Quando view declara color_inherit_from_view, resolver classe da view irma.
        esp_or_n1 = nome do esp ou 'n1' para o total."""
        if not inherit_from or not all_rows:
            return "mute"
        sibling = next((m for m in all_rows if m["label"] == inherit_from), None)
        if not sibling:
            return "mute"
        if esp_or_n1 == "n1":
            n1_data = _resolve_n1(sibling, data) or {}
            sib_real, sib_meta = n1_data.get("realizado"), n1_data.get("meta")
        elif esp_or_n1 == "Sem Especialista":
            d = _resolve_n2(sibling, "Sem Especialista", data, n_esps=0, esp_list=esp_list) or {}
            sib_real, sib_meta = d.get("realizado"), d.get("meta")
        else:
            d = _resolve_n2(sibling, esp_or_n1, data, n_esps=len(esp_list), esp_list=esp_list) or {}
            sib_real, sib_meta = d.get("realizado"), d.get("meta")
        if not isinstance(sib_real, (int, float)) or not isinstance(sib_meta, (int, float)) or sib_meta == 0:
            return "mute"
        sib_dir = sibling.get("direction", "maior_melhor")
        if sib_dir == "menor_melhor":
            pct_sib = (sib_meta / max(sib_real, 1e-9)) * 100
        else:
            pct_sib = (sib_real / sib_meta) * 100
        return _class_3tier(pct_sib, sib_dir)

    def cell_for(realizado, meta_v, status, *, sub_extra: str = "", inherit_key: str = None):
        # FIX 2026-05-14 (Bug 1.5 — unit clash ratio): Card YAML metas_ppi usa
        # fracao decimal (0.25) enquanto analyst v1.1 emite valores em pct (30.43).
        # Normalizar para mesma escala (pct) quando unidade=ratio antes de pct calc.
        if unidade == "ratio":
            if isinstance(meta_v, (int, float)) and abs(meta_v) <= 1.0:
                meta_v = meta_v * 100
            if isinstance(realizado, (int, float)) and abs(realizado) <= 1.0:
                realizado = realizado * 100
        if realizado is None:
            # S1-A2 (2026-05-15) feedback: TODA cell deve ter 3 linhas (Realizado /
            # pct meta / meta abs) para hierarquia visual consistente.
            if isinstance(meta_v, (int, float)) and meta_v:
                meta_str_abs = _fmt_value(meta_v, unidade)
                return (f'<div class="cell mute"><div class="v">'
                        f'<div class="num">—</div>'
                        f'<div class="meta">— meta</div>'
                        f'<div class="sub">meta {meta_str_abs}</div>'
                        f'</div></div>')
            return ('<div class="cell mute"><div class="v">'
                    '<div class="num">—</div>'
                    '<div class="meta">—</div>'
                    '<div class="sub">—</div></div></div>')
        num = _fmt_value(realizado, unidade)
        # S1-A2 (2026-05-15): view "Oport. Estagnadas (qty)" enriquecida com
        # volume entre parenteses. Display: "24 (R$ 5,2M)". Fonte temporaria:
        # dados_consolidados (rows N2-Especialista). SoT correto: S2-B4 (E6
        # emitir n2.{esp}.volume_estagnado no canonical WBR).
        if is_estagnadas_qty_view and inherit_key:
            if inherit_key == "n1":
                vol_estag = _vol_estagnado_for_total(data, esp_list)
            else:
                vol_estag = _vol_estagnado_for_esp(data, inherit_key)
            if vol_estag and vol_estag > 0:
                vol_str = fmt_brl(vol_estag, compact=True)
                num = f"{num} ({vol_str})"

        # S1-A2 (2026-05-15): view "Sem Ativ. ou Atras. CRM" enriquecida com
        # "qty (X%)" + cor proporcional (0=verde, 0-20%=amarelo, 21%+=vermelho).
        # Override total da regra de meta=0 binaria (que era menor_melhor com 0).
        sem_ativ_override_cls = None
        if is_sem_atividade_view and inherit_key and inherit_key not in (
                "Sem Especialista",):
            if inherit_key == "n1":
                # N1 total: SUM(qty_sa) / SUM(qty_ativas) × 100
                # Excluir suffixes _volume, _pct_ativas, _vol (derived indicators
                # com unidades BRL/pct, nao qty).
                _excl = ("_volume", "_pct_ativas", "_vol")
                total_sa = 0.0
                total_at = 0.0
                _indicadores = (data or {}).get("wbr", {}).get("indicadores", {}) or {}
                for _ind_id, _ind in _indicadores.items():
                    if not isinstance(_ind, dict):
                        continue
                    if "sem_atividade_planejada_funil" in _ind_id:
                        v = _ind.get("realizado_mtd") or _ind.get("realizado")
                        if isinstance(v, (int, float)):
                            total_sa = float(v)
                    elif "oportunidades_ativas_funil" in _ind_id and not any(
                            _ind_id.endswith(s) for s in _excl):
                        v = _ind.get("realizado_qty") or _ind.get("realizado")
                        if isinstance(v, (int, float)):
                            total_at = float(v)
                pct_sa = (total_sa / total_at * 100) if total_at else 0
            else:
                pct_sa = _pct_sem_atividade_for_esp(data, inherit_key)
            if isinstance(realizado, (int, float)):
                if realizado == 0:
                    sem_ativ_override_cls = "good"
                elif pct_sa <= 20:
                    sem_ativ_override_cls = "warn"
                else:
                    sem_ativ_override_cls = "bad"
                if pct_sa > 0:
                    num = f"{num} ({pct_sa:.0f}%)"
        # FIX rodada 7 issue 1 — Sem Especialista UNIVERSAL: cell sempre cinza, sem meta.
        # Aplicado por inherit_key (chave usada como nome do esp na chamada cell_for).
        # S1-A2 (2026-05-15) feedback: estrutura padrao 3 linhas mesmo para Sem Esp
        # (linhas 2 e 3 mostram "—" para preservar hierarquia visual).
        if inherit_key == "Sem Especialista":
            sub_html = f'<div class="sub-info">{sub_extra}</div>' if sub_extra else ""
            return (f'<div class="cell mute"><div class="v">'
                    f'<div class="num">{num}</div>'
                    f'<div class="meta">—</div>'
                    f'<div class="sub">—</div>{sub_html}</div></div>')
        # Detectar se view tem cor herdada (ex: Estagnadas qty herda de % ativas)
        # S1-A2 (2026-05-15) feedback: views com inherit_from tambem ganham 3 linhas
        # ("—" / "—" como placeholder consistente com Sem Esp).
        if inherit_from and inherit_key:
            cls = _resolve_inherited_cls(inherit_key)
            meta_html = '<div class="meta">—</div><div class="sub">—</div>'
        elif meta_v is not None and isinstance(meta_v, (int, float)) and meta_v != 0 and isinstance(realizado, (int, float)):
            try:
                if direction == "menor_melhor":
                    # R7 (2026-05-07): cap em 200% para evitar valores absurdos
                    # quando realizado=0 + menor_melhor (meta/0 = infinito).
                    if realizado <= 0:
                        pct = 200  # meta atingida com folga maxima
                    else:
                        pct = min(200, (meta_v / realizado) * 100)
                else:
                    pct = (realizado / meta_v) * 100
                pct_str = f"{pct:.0f}% meta".replace(".", ",")
                meta_str_abs = _fmt_value(meta_v, unidade)
                meta_html = f'<div class="meta">{pct_str}</div><div class="sub">meta {meta_str_abs}</div>'
                cls = _class_3tier(pct, direction)
            except (TypeError, ZeroDivisionError):
                meta_html = '<div class="meta">—</div>'
                cls = "mute"
        else:
            # S1-A1#3a + #4 (2026-05-15): Hierarquia padrao Realizado/pct/meta_abs
            # tambem aplicada no else branch. Cobertura:
            #   (a) realizado num + meta None: '—' (sem meta declarada — view sem meta)
            #   (b) realizado num + meta=0: 'meta 0' (zero target — ex: sem_atividade)
            #   (c) realizado num + meta nao-numerica (placeholder/text): mostra texto
            # Removido "ref" — confunde o leitor sem agregar valor.
            if isinstance(meta_v, (int, float)):
                meta_str_abs = _fmt_value(meta_v, unidade)
                # Sem pct atingimento confiavel (realizado nao-numerico ou meta=0):
                # mostra apenas meta absoluta na linha 3, deixando linha 2 vazia ("—").
                meta_html = (f'<div class="meta">—</div>'
                             f'<div class="sub">meta {meta_str_abs}</div>')
            elif meta_v:
                # meta nao-numerica (texto/placeholder semantico)
                meta_html = f'<div class="meta">{_fmt_value(meta_v, unidade)}</div>'
            else:
                meta_html = '<div class="meta">—</div>'
            cls = status_to_class(status) if status else "mute"
        # S1-A2 (2026-05-15): override cor para view "Sem Ativ. ou Atras. CRM"
        # com regra proporcional. Aplica DEPOIS do cls regular para sobrescrever.
        if sem_ativ_override_cls is not None:
            cls = sem_ativ_override_cls
        sub_html = f'<div class="sub-info">{sub_extra}</div>' if sub_extra else ""
        return f'<div class="cell {cls}"><div class="v"><div class="num">{num}</div>{meta_html}{sub_html}</div></div>'

    cells = []
    n_esps = len(esp_list)
    ind_entry = data["wbr"].get("indicadores", {}).get(mr["source_indicator"], {}) or {}
    n2_dict = ind_entry.get("n2") or ind_entry.get("por_especialista") or {}

    # Sem Especialista
    sem_esp_data = _resolve_n2(mr, "Sem Especialista", data, n_esps=0, esp_list=esp_list) or {}
    sem_esp_n2_entry = n2_dict.get("Sem Especialista", {}) or {}
    sub_sem = render_sub_info(sub_tpl_n2, sem_esp_n2_entry) if sub_tpl_n2 and sem_esp_n2_entry else ""
    cells.append(cell_for(sem_esp_data.get("realizado"), sem_esp_data.get("meta"),
                          sem_esp_data.get("status"), sub_extra=sub_sem,
                          inherit_key="Sem Especialista"))

    total_real = 0.0
    has_total = False
    # FIX (2026-05-14) Bug 1: incluir Sem Especialista derivado no Total quando
    # presente. Antes o Total era SUM(esps_declarados) e nao bata com N1 verdadeiro.
    if isinstance(sem_esp_data.get("realizado"), (int, float)):
        total_real += sem_esp_data["realizado"]
        has_total = True
    for esp in esp_list:
        e_data = _resolve_n2(mr, esp, data, n_esps=n_esps, esp_list=esp_list) or {}
        e_n2_entry = n2_dict.get(esp, {}) or {}
        sub_esp = render_sub_info(sub_tpl_n2, e_n2_entry) if sub_tpl_n2 and e_n2_entry else ""
        cells.append(cell_for(e_data.get("realizado"), e_data.get("meta"),
                              e_data.get("status"), sub_extra=sub_esp, inherit_key=esp))
        if isinstance(e_data.get("realizado"), (int, float)):
            total_real += e_data["realizado"]
            has_total = True
    # Total N1
    n1_data = _resolve_n1(mr, data) or {}
    n1_real = n1_data.get("realizado")
    n1_meta = n1_data.get("meta")
    # FIX (2026-05-14) Bug 1: quando Sem Especialista foi derivado via raw bridge,
    # prefer total_real (= sum incluindo bridge) sobre n1_real do WBR canonical que
    # foi consolidado restringindo aos esps declarados. Detecta via _sem_esp flag.
    # FIX (2026-05-14) Bug 1.5: META tambem precisa ser substituida pela meta raw
    # do N1 (incluindo bridge) — senao Total compara realizado-com-bridge contra
    # meta-sem-bridge e o pct atingimento fica fictcio (ex: Receita 312/135 = 231%
    # quando deveria ser 312/216 = 144% via meta N1 raw do componente '285').
    # FIX 2026-05-20 Bug 1 (estagnadas pct ativas mostrando 243,8%):
    # NUNCA substituir n1_real por total_real para indicadores derivados
    # (aggregation_rule_applied=true) OU unidades nao-aditivas (pct/ratio).
    # Caso: oportunidades_estagnadas_funil_pct_ativas — N2 sao percentuais por
    # esp (62,5% Douglas + 81,3% Tereza + 100% Sem Esp = 243,8% que e absurdo
    # matematicamente). N1 correto vem do canonical (= SUM(qty_estag)/SUM(qty_ativ)*100).
    src_ind_id = mr.get("source_indicator", "")
    src_ind_entry = data["wbr"].get("indicadores", {}).get(src_ind_id, {}) or {}
    is_derived_or_non_additive = (
        src_ind_entry.get("aggregation_rule_applied") is True
        or (mr.get("unidade") or "").lower() in ("ratio", "pct", "percent", "percentual", "%")
        or (src_ind_entry.get("unit") or "").lower() in ("ratio", "pct", "percent", "percentual", "%")
    )
    sem_esp_was_derived = (sem_esp_data.get("_sem_esp")
                            and isinstance(sem_esp_data.get("realizado"), (int, float))
                            and sem_esp_data["realizado"] > 0)
    if is_derived_or_non_additive:
        # Forcar n1 do canonical para indicadores derivados/pct (nao somar pcts).
        if n1_real is None:
            # canonical sem N1: melhor mostrar "—" que somar pcts.
            n1_real = None
    elif sem_esp_was_derived and has_total:
        n1_real = total_real
        # Tentar puxar a meta N1 raw do dados_consolidados (mesmo lookup que o realizado)
        n1_meta_raw = _derive_n1_raw_from_dados(data, mr, field_override="meta")
        if isinstance(n1_meta_raw, (int, float)) and n1_meta_raw > 0:
            n1_meta = n1_meta_raw
    elif n1_real is None and has_total:
        n1_real = total_real
    sub_n1 = render_sub_info(sub_tpl_n1, ind_entry) if sub_tpl_n1 else ""
    cells.append(cell_for(n1_real, n1_meta, mr.get("status_n1"),
                          sub_extra=sub_n1, inherit_key="n1"))

    return f'<div class="mx-row data"><div class="col-ind">{label}</div>{"".join(cells)}</div>'


# ============================================================
# Renderers — PA Status (Slide 4) + PA Vencendo (Slide 5)
# ============================================================

def render_pa_slides(data: dict, clickup_tasks: list, deviation_report_md: str = "") -> dict:
    wbr = data["wbr"]
    acoes = wbr.get("acoes", {})
    metricas = acoes.get("metricas_agregadas", {})

    # R6 (2026-05-07): filtrar tasks por subnivel (WL/RE) quando Card e split.
    # Match em (a) responsavel_externo == esp do Card (canal mais confiavel —
    # tasks sempre tem owner externo registrado); (b) responsaveis_globais do
    # Card (Pedro Villarroel, Joel Freitas — coordenadores cross-card relevantes
    # para todos os subniveis); (c) suffix do indicador_impactado; (d) nome do
    # esp no titulo da task. Quando nenhum filtro casa, mantem todas + warn.
    card = data.get("card") or {}
    subnivel = (card.get("metadata") or {}).get("subnivel")
    if subnivel and clickup_tasks:
        # Esps do Card (responsaveis declarados em apresentacao.responsaveis)
        esp_names = []
        for r in (card.get("apresentacao") or {}).get("responsaveis", []) or []:
            n = r.get("name") or r.get("nome")
            if n:
                esp_names.append(n.strip())
        # assessor_aliases pode trazer variantes (ex: "Emmanuel Martis" → "Emmanuel Martins")
        for k, v in ((card.get("metadata") or {}).get("assessor_aliases") or {}).items():
            esp_names.append(str(k).strip())
            esp_names.append(str(v).strip())
        esp_names_set = {n.lower() for n in esp_names if n}

        # Responsaveis globais (cross-card) — coordenadores/back-office cuja PA
        # afeta todos os subniveis. Default tipico: ["Pedro Villarroel", "Joel Freitas"].
        # Card pode override via metadata.pa_responsaveis_globais.
        globais_default = ["Pedro Villarroel", "Joel Freitas"]
        globais = (card.get("metadata") or {}).get("pa_responsaveis_globais", globais_default)
        globais_set = {str(g).strip().lower() for g in globais if g}

        # R7 (2026-05-07): keyword filter no titulo das tasks. Quando JSON ClickUp
        # nao traz responsavel_externo (NULL), match no titulo eh fallback util.
        # Card.metadata.pa_keyword_filter declara palavras-chave que indicam o subnivel.
        # Exemplo RE: ["Singular", "ROX", "Emmanuel", "Samuel"]; WL: ["Whole Life", "Claudia", "Tarcisio"].
        keyword_filter = (card.get("metadata") or {}).get("pa_keyword_filter") or []
        keyword_filter_lc = [str(k).strip().lower() for k in keyword_filter if k]

        suf = f"_{subnivel}"  # ex: _re ou _wl

        def _resp_matches_set(resp_field, name_set):
            """resp pode ser str ou list. Retorna True se algum nome bate em name_set."""
            if not resp_field or not name_set:
                return False
            if isinstance(resp_field, list):
                names = [str(x).strip().lower() for x in resp_field if x]
            else:
                # Pode vir 'Emmanuel Martins + Pedro Villarroel' apos expand_owner
                txt = str(resp_field).strip().lower()
                # Split em separadores comuns
                names = [p.strip() for p in re.split(r"\s*[,&+]\s*|\s+e\s+", txt) if p.strip()]
            for n in names:
                if n in name_set:
                    return True
                # match parcial (primeiro nome ou substring)
                for cand in name_set:
                    if cand in n or n in cand:
                        return True
            return False

        def _matches_subnivel(t: dict) -> bool:
            # (a) responsavel_externo (mais confiavel)
            resp = t.get("responsavel_externo") or t.get("owner")
            if _resp_matches_set(resp, esp_names_set):
                return True
            # (b) responsaveis globais (cross-card)
            if _resp_matches_set(resp, globais_set):
                return True
            # (c) indicador_impactado com suffix do subnivel
            ind = (t.get("indicador_impactado") or "").lower()
            if suf in ind or ind.endswith(suf):
                return True
            # (d) nome do esp no titulo
            title = (t.get("name") or t.get("titulo") or "").lower()
            for e in esp_names_set:
                if e and e in title:
                    return True
            # (e) keyword filter — palavras-chave do Card que indicam o subnivel
            # (ex: "Singular"/"ROX" para RE; "Whole Life"/"Claudia" para WL).
            for kw in keyword_filter_lc:
                if kw and kw in title:
                    return True
            # (f) custom field vertical/subnivel se existir
            cf = t.get("subnivel") or t.get("vertical_subnivel") or ""
            if cf and str(cf).lower() == subnivel.lower():
                return True
            return False

        matched = [t for t in clickup_tasks if _matches_subnivel(t)]
        if matched:
            print(f"[build_deck] R6 PA filtrado por subnivel='{subnivel}': "
                  f"{len(matched)}/{len(clickup_tasks)} tasks (esps={sorted(esp_names_set)} + globais={sorted(globais_set)})",
                  file=sys.stderr)
            clickup_tasks = matched
        else:
            print(f"[build_deck] R6 WARN: nenhuma task casou subnivel='{subnivel}' — "
                  f"mostrando todas as {len(clickup_tasks)}. Verificar responsavel_externo "
                  f"das tasks no ClickUp.", file=sys.stderr)

    # FIX rodada 6 issue 5 + rodada 7 — enriquece owner do WBR a partir do clickup_tasks JSON.
    # Suporta multi-name separators: ',', '&', ' e ' (custom field ClickUp usa "&" ou " e ").
    # Aplica responsavel_externo_aliases do Card primeiro (ex: "Douglas e Tereza" →
    # "Douglas Silva + Tereza Bernardo") e depois split em separadores.
    card = data.get("card") or {}
    resp_aliases = (card.get("metadata") or {}).get("responsavel_externo_aliases") or {}

    def _expand_owner(resp_raw):
        """Resolve responsavel_externo:
        1. Aplica alias literal do Card (ex: 'Douglas e Tereza' → 'Douglas Silva + Tereza Bernardo')
        2. Split em ',' / '&' / ' e ' / ' + '
        3. Junta com ' + '
        Retorna string final ou None se vazio."""
        if not resp_raw:
            return None
        if isinstance(resp_raw, list):
            names = [str(x).strip() for x in resp_raw if str(x).strip()]
        else:
            txt = str(resp_raw).strip()
            # Alias literal primeiro
            if txt in resp_aliases:
                txt = resp_aliases[txt]
            parts = re.split(r"\s*[,&+]\s*|\s+e\s+", txt)
            names = [p.strip() for p in parts if p.strip()]
        if not names:
            return None
        if len(names) >= 2:
            return " + ".join(names)
        return names[0]

    tasks_by_id = {t.get("id"): t for t in clickup_tasks if t.get("id")} if clickup_tasks else {}
    if tasks_by_id:
        for cat in ("criticas", "atrasadas", "em_dia_priorizadas"):
            for a in acoes.get(cat, []):
                tid = a.get("id")
                t = tasks_by_id.get(tid)
                if not t:
                    continue
                expanded = _expand_owner(t.get("responsavel_externo"))
                if expanded:
                    a["owner"] = expanded

    # FIX rodada 7 issue 10 — pa_manual_append: tasks declaradas no Card que
    # m7-controle E4 nao classificou (aging > cutoff). Resolve cada ID via
    # clickup_tasks lookup e prepara dict no mesmo formato de acoes.em_dia_priorizadas.
    pa_manual_ids = (card.get("apresentacao") or {}).get("pa_manual_append") or []
    manual_tasks = []
    cycle_date_str = (data.get("wbr", {}).get("metadata") or {}).get("ciclo", "")
    cycle_d = cycle_date_from_str(cycle_date_str) if cycle_date_str else None
    for tid in pa_manual_ids:
        t = tasks_by_id.get(tid)
        if not t:
            continue
        # due_date pode vir em 3 formatos: ms epoch (int/str raw da API ClickUp),
        # ou string YYYY-MM-DD (apos conversao pelo m7-controle E2 collect.py).
        # FIX rodada 7.6 — handle ambos formatos.
        due_raw = t.get("due_date")
        prazo_str = "—"
        dias_rest = None
        from datetime import datetime, timezone, timedelta, date as _date
        due_d = None
        if isinstance(due_raw, (int, float)):
            # ms epoch — adiciona 1h para normalizar (ClickUp 23:00 UTC → midnight)
            due_dt = datetime.fromtimestamp(float(due_raw) / 1000, tz=timezone.utc) + timedelta(hours=1)
            due_d = due_dt.date()
        elif isinstance(due_raw, str):
            s = due_raw.strip()
            if s.isdigit():
                due_dt = datetime.fromtimestamp(float(s) / 1000, tz=timezone.utc) + timedelta(hours=1)
                due_d = due_dt.date()
            else:
                # Tenta parse YYYY-MM-DD
                try:
                    due_d = datetime.strptime(s, "%Y-%m-%d").date()
                except ValueError:
                    due_d = None
        if due_d:
            prazo_str = due_d.strftime("%Y-%m-%d")
            dias_rest = (due_d - cycle_d).days if cycle_d else None
        owner_expanded = _expand_owner(t.get("responsavel_externo")) or "—"
        # Indicador via custom field ou nome
        indicador = t.get("indicador_impactado") or ""
        manual_tasks.append({
            "id": tid,
            "titulo": t.get("name") or "",
            "owner": owner_expanded,
            "prazo": prazo_str,
            "dias_restantes": dias_rest,
            "aging": dias_rest,
            "indicador": indicador,
            "_manual_append": True,
        })

    # FIX (2026-05-14) BUG #1: a fonte canonica de status+due e o clickup_tasks JSON.
    # metricas_agregadas do WBR vinha sendo lida com chaves erradas (total_ativas/em_dia
    # nao existem no schema do analyst v1.1 — ele emite total/ativas/atrasadas/concluidas_periodo).
    # Resultado: total=32 incluia 23 concluidas, gerando "Atencao (≤7d) 25 · 78%" — falso.
    # Refator: SEMPRE recomputar do clickup_tasks (autoridade), filtrando status concluida
    # ANTES do bucketing aging. metricas vira fallback so quando clickup_tasks vazio.
    #
    # S1-A1#7 (2026-05-15): NOTA — o filtro _STATUS_CONCLUIDAS aqui aplica apenas ao
    # aging compute legacy path (bloco abaixo). As 3 superficies visuais (donut do
    # slide 4 / owner bars / tabela do slide 5) consomem `acoes.*` do WBR (curado
    # pelo analyst E4), que inclui `concluidas_eficazes` como categoria separada
    # — concluidas aparecem normalmente nessas superficies com pill verde escuro
    # #2e7d32. Apenas `cancelada` esta universalmente excluida (nunca aparece).
    # Concluidas nao tem aging relevante; manter no filtro do aging path e correto.
    _STATUS_CONCLUIDAS = ("closed", "done", "completed", "concluida",
                          "concluido", "fechada", "cancelada")
    if clickup_tasks:
        from datetime import datetime as _dt, timezone as _tz, timedelta as _td
        # SoT: filtra concluidas antes de qualquer bucketing
        active_tasks = [t for t in clickup_tasks
                        if (t.get("status") or "").lower() not in _STATUS_CONCLUIDAS]
        cycle_date_str = (
            data.get("wbr", {}).get("metadata", {}).get("ciclo", "")
            or (data.get("wbr", {}).get("data_referencia") or "")[:10]
        )
        cycle_d = cycle_date_from_str(cycle_date_str) if cycle_date_str else None
        em_dia = atrasadas = criticas = 0
        for t in active_tasks:
            due = t.get("due_date")
            due_d = None
            if isinstance(due, (int, float)):
                due_d = (_dt.fromtimestamp(float(due) / 1000, tz=_tz.utc) + _td(hours=1)).date()
            elif isinstance(due, str) and due:
                try:
                    if due.isdigit():
                        due_d = (_dt.fromtimestamp(float(due) / 1000, tz=_tz.utc) + _td(hours=1)).date()
                    else:
                        due_d = _dt.strptime(due[:10], "%Y-%m-%d").date()
                except Exception:
                    pass
            if not due_d or not cycle_d:
                em_dia += 1  # sem data → considera em dia (ou pendente)
                continue
            delta = (due_d - cycle_d).days
            if delta < -7:
                criticas += 1  # >7d atrasada
            elif delta < 0:
                atrasadas += 1  # 0-7d atrasada
            else:
                em_dia += 1  # no prazo
        total = len(active_tasks)
    else:
        # Fallback: WBR metricas (apenas quando nao temos clickup_tasks crus)
        total = metricas.get("total_ativas") or (
            (metricas.get("ativas") or 0)
            + (metricas.get("atrasadas") or 0)
            + (metricas.get("criticas_atrasadas") or 0)
        ) or 1
        em_dia = metricas.get("em_dia", 0) or metricas.get("ativas", 0)
        atrasadas = metricas.get("atrasadas", 0)
        criticas = metricas.get("criticas", 0) or metricas.get("criticas_atrasadas", 0)
    # S1-A1#8 (2026-05-15): bug detectado pelo gatekeeper #16 — alias
    # em_dia_proximas → em_dia_priorizadas precisa ser aplicado ANTES do
    # bucketing, senao n_em_dia=0 quando WBR usa schema legacy `em_dia_proximas`.
    # Move o alias para cima (estava na linha ~3434, depois do callout).
    if "em_dia_priorizadas" not in acoes and "em_dia_proximas" in acoes:
        acoes["em_dia_priorizadas"] = acoes.get("em_dia_proximas", [])

    # Fix 2026-05-15: ESCOPO REDUZIDO — slide 4 (donut + bars) considera APENAS
    # as acoes que aparecem no slide 5 (PA Vencendo), ou seja, criticas +
    # atrasadas + em_dia_priorizadas + concluidas_eficazes do WBR.acoes (lista
    # curada pelo analyst). Antes contavamos todas as 30+ tasks do clickup_tasks
    # — gerava inconsistencia entre donut (todas) e tabela (apenas as priorizadas).
    # Agora donut, bars e tabela usam o mesmo subset.
    n_criticas = len(acoes.get("criticas", []) or [])
    n_atrasadas = len(acoes.get("atrasadas", []) or [])
    n_em_dia = len(acoes.get("em_dia_priorizadas", []) or [])
    n_concluidas = len(acoes.get("concluidas_eficazes", []) or [])
    total_geral = n_criticas + n_atrasadas + n_em_dia + n_concluidas

    # Sobrescrever variaveis usadas downstream (PA_ATRASADAS placeholder etc.)
    criticas = n_criticas
    atrasadas = n_atrasadas
    em_dia = n_em_dia
    concluidas = n_concluidas
    atencao = 0  # nao usamos bucket "atencao" no escopo do slide 5
    total = total_geral

    total_geral_safe = max(total_geral, 1)

    # PCT sobre total_geral (4 buckets somam 100%)
    pct_no_prazo = round((em_dia / total_geral_safe) * 100)
    pct_atencao = round((atencao / total_geral_safe) * 100)
    pct_atrasadas = round(((atrasadas + criticas) / total_geral_safe) * 100)
    pct_concluidas = round((concluidas / total_geral_safe) * 100)

    # Donut SVG (4 segments: no_prazo / atencao / atrasadas / concluidas)
    donut = _render_donut_svg(pct_no_prazo, pct_atencao, pct_atrasadas, pct_concluidas)

    # Bars by owner — aggregate from clickup tasks if available
    bars_by_owner = _render_owner_bars(clickup_tasks, acoes)

    # Callout (severity based on criticas) — auto-gerado a partir de aging + cluster
    cluster_msg = (acoes.get("eficacia_concluidas", {}) or {}).get("cluster_sem_efeito_concentrado", "")
    aging_med = metricas.get("aging_medio_atrasadas_dias", 0)
    # R5-4 (2026-05-07): fallback aging — computa media de aging das tasks ativas
    # atrasadas quando metricas do action-report nao trazem (ou trazem 0).
    if (not aging_med or aging_med == 0) and clickup_tasks:
        from datetime import datetime as _dt
        _CLOSED = {"closed", "done", "completed", "concluida", "concluido",
                   "concluído", "concluída", "fechada", "fechado", "cancelada",
                   "cancelado", "complete"}
        agings = []
        for t in clickup_tasks:
            if (t.get("status") or "").lower() in _CLOSED:
                continue
            dr = t.get("dias_restantes")
            if dr is None and t.get("due_date"):
                try:
                    due_d = _dt.fromisoformat(str(t["due_date"])[:10])
                    dr = (due_d - _dt.now()).days
                except Exception:
                    dr = None
            if dr is not None and dr < 0:
                agings.append(-dr)  # aging = dias passados do due
        if agings:
            aging_med = sum(agings) / len(agings)
    if criticas > 0:
        callout_class = "bad"
        callout_label = "Atencao"
        msg_cluster = f" Cluster sinalizado: {cluster_msg}." if cluster_msg else ""
        callout_body = (
            f"<strong>{criticas} acao(oes) critica(s)</strong> e {atrasadas} atrasada(s) "
            f"(aging medio {aging_med:.1f}d).{msg_cluster}"
        )
    elif atrasadas > 0:
        callout_class = "warn"
        callout_label = "Acompanhar"
        callout_body = (
            f"<strong>{atrasadas} acao(oes) atrasada(s)</strong> "
            f"(aging medio {aging_med:.1f}d). Sem criticas no ciclo, "
            f"mas cobrar entrega antes do proximo ritual."
        )
    else:
        callout_class = ""
        callout_label = "OK"
        callout_body = "Plano sem atrasos. Cobrar entregas no prazo."

    # S1-A1#8 (2026-05-15): alias em_dia_proximas → em_dia_priorizadas movido
    # para ANTES do bucketing (gatekeeper #16 detectou que ficava stale aqui).
    # Mantemos o nip aqui por defesa em caso de mutacao tardia de `acoes` por
    # outro path; redundancia segura.
    if "em_dia_priorizadas" not in acoes and "em_dia_proximas" in acoes:
        acoes["em_dia_priorizadas"] = acoes.get("em_dia_proximas", [])

    # PA vencendo top 12 + manual append
    # Refator 2026-05-07: quando acoes vazio (WBR sem dados), constroi
    # categorias dinamicamente do clickup_tasks via due_date.
    if not (acoes.get("criticas") or acoes.get("atrasadas") or acoes.get("em_dia_priorizadas")) and clickup_tasks:
        from datetime import datetime as _dt, timezone as _tz, timedelta as _td
        active_tasks = [t for t in clickup_tasks
                         if (t.get("status") or "").lower() not in ("closed","done","completed","concluida","concluido","fechada","cancelada")]
        cycle_date_str = (data.get("wbr", {}).get("metadata") or {}).get("ciclo", "") or data.get("wbr", {}).get("data_referencia", "")[:10]
        cycle_d = cycle_date_from_str(cycle_date_str) if cycle_date_str else None
        cat_criticas, cat_atrasadas, cat_em_dia = [], [], []
        for t in active_tasks:
            due = t.get("due_date")
            due_d = None
            if isinstance(due, (int, float)):
                due_d = (_dt.fromtimestamp(float(due) / 1000, tz=_tz.utc) + _td(hours=1)).date()
            elif isinstance(due, str) and due:
                try:
                    if due.isdigit():
                        due_d = (_dt.fromtimestamp(float(due) / 1000, tz=_tz.utc) + _td(hours=1)).date()
                    else:
                        due_d = _dt.strptime(due[:10], "%Y-%m-%d").date()
                except Exception:
                    pass
            owner_expanded = _expand_owner(t.get("responsavel_externo")) or "—"
            aging = (cycle_d - due_d).days if (due_d and cycle_d) else None
            entry = {
                "id": t.get("id"),
                "titulo": t.get("name") or "",
                "owner": owner_expanded,
                "prazo": due_d.strftime("%Y-%m-%d") if due_d else "—",
                "dias_restantes": -aging if aging is not None else None,
                "aging": aging,
                "indicador": t.get("indicador_impactado") or "",
            }
            if not due_d:
                cat_em_dia.append(entry)
            elif aging > 7:
                cat_criticas.append(entry)
            elif aging > 0:
                cat_atrasadas.append(entry)
            else:
                cat_em_dia.append(entry)
        # Sort by aging desc (mais antigas primeiro)
        cat_criticas.sort(key=lambda x: -(x.get("aging") or 0))
        cat_atrasadas.sort(key=lambda x: -(x.get("aging") or 0))
        cat_em_dia.sort(key=lambda x: x.get("dias_restantes") or 999)
        # Patch acoes para reuso pelas funcoes downstream
        acoes = {"criticas": cat_criticas, "atrasadas": cat_atrasadas, "em_dia_priorizadas": cat_em_dia}

    table_rows = _render_pa_vencendo_rows(acoes, deviation_report_md=deviation_report_md,
                                            manual_tasks=manual_tasks)
    # Foco: auto-gera apontando 1-3 acoes mais criticas (aging mais negativo)
    foco_items = []
    for a in acoes.get("criticas", [])[:1]:
        foco_items.append(f"<strong>{a.get('titulo', '')}</strong> ({a.get('owner', '—')}, {a.get('aging', '?')}d)")
    for a in acoes.get("atrasadas", [])[:2]:
        foco_items.append(f"<strong>{a.get('titulo', '')}</strong> ({a.get('owner', '—')}, {a.get('aging', '?')}d)")
    if foco_items:
        foco = "Foco do ritual: " + "; ".join(foco_items[:3]) + "."
    else:
        foco = "Sem PAs criticas. Ritual focado em planejamento da semana."

    # S1-A1#8 (2026-05-15): Gatekeeper SSoT #16 — cross-slide PA count.
    # Verifica que o total do donut (slide 4) bate com a soma das 4 categorias
    # de `acoes` no WBR canonical. As 3 superficies visuais (donut, owner bars,
    # tabela slide 5) devem refletir o mesmo subset.
    expected_total_from_acoes = (
        len(acoes.get("criticas", []) or [])
        + len(acoes.get("atrasadas", []) or [])
        + len(acoes.get("em_dia_priorizadas", []) or [])
        + len(acoes.get("concluidas_eficazes", []) or [])
    )
    _gatekeeper_check(
        "#16",
        "PA count consistente (donut total == sum acoes 4 categorias)",
        condition=(total_geral == expected_total_from_acoes),
        details=(f"donut total={total_geral} vs acoes sum={expected_total_from_acoes}"
                 f" [criticas={len(acoes.get('criticas', []) or [])}"
                 f" atrasadas={len(acoes.get('atrasadas', []) or [])}"
                 f" em_dia={len(acoes.get('em_dia_priorizadas', []) or [])}"
                 f" concluidas={len(acoes.get('concluidas_eficazes', []) or [])}]"),
        blocking=False,  # WARNING — nao bloqueia publicacao (escopo manual append etc)
    )

    return {
        "PA_DONUT_SVG": donut,
        "PA_TOTAL": str(total_geral),
        "PA_NO_PRAZO": str(em_dia),
        "PA_NO_PRAZO_PCT": str(pct_no_prazo),
        "PA_ATENCAO": str(atencao),
        "PA_ATENCAO_PCT": str(pct_atencao),
        "PA_ATRASADAS": str(atrasadas + criticas),
        "PA_ATRASADAS_PCT": str(pct_atrasadas),
        "PA_CONCLUIDAS": str(concluidas),
        "PA_CONCLUIDAS_PCT": str(pct_concluidas),
        "PA_BARS_BY_OWNER": bars_by_owner,
        "PA_CALLOUT_CLASS": callout_class,
        "PA_CALLOUT_LABEL": callout_label,
        "PA_CALLOUT_BODY": callout_body,
        "PA_TABLE_ROWS": table_rows,
        "PA_VENCENDO_FOCO": foco,
    }


# ============================================================
# S1-A1#8 (2026-05-15): Gatekeepers SSoT do build_deck
# ============================================================
# Padrao analogo aos gatekeepers #7/#10/#12/#15 existentes (raise ValueError em
# falha critica, log de WARNING quando blocking=False). Documentado em
# references/migration-v2.md secao "Gatekeepers SSoT".

def _gatekeeper_check(check_id: str, label: str, condition: bool,
                      details: str = "", blocking: bool = True) -> bool:
    """Gatekeeper SSoT rastreavel para validacao intra-deck.

    Args:
        check_id: identificador do gatekeeper ('#16', '#17', etc).
        label: descricao curta do que esta sendo verificado.
        condition: True = passa; False = falha.
        details: contexto extra (numeros, caminhos) que aparece na mensagem.
        blocking: True (default) levanta ValueError; False so loga WARNING.

    Returns:
        True se passou, False se falhou (apenas quando blocking=False).

    Raises:
        ValueError se blocking=True e condition=False.
    """
    if condition:
        print(f"[gatekeeper {check_id}] OK · {label}", file=sys.stderr)
        return True
    msg = f"[gatekeeper {check_id}] FAIL · {label}"
    if details:
        msg += f" — {details}"
    if blocking:
        raise ValueError(msg)
    print(f"WARNING: {msg}", file=sys.stderr)
    return False


def _gatekeeper_numeric_close(a, b, tolerance: float) -> bool:
    """Comparacao numerica bruta com tolerancia (S1-A1#8).
    Tolerances tipicas: R$ 500 (BRL compact), 1 (qty), 0.1 (pct pp).
    Aceita None de ambos os lados como 'equal' (skip — gap de dado).
    """
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    try:
        return abs(float(a) - float(b)) <= tolerance
    except (TypeError, ValueError):
        return str(a) == str(b)


def _gatekeeper_17_consolidado_vs_dashboard(data: dict, esp_list: list) -> None:
    """S1-A1#8 — Gatekeeper SSoT #17: cross-slide esp value consistency.

    Para cada KPI principal (receita, volume, qty), valida que o valor exposto
    para cada esp no slide Consolidado N3 bate (com tolerancia bruta) com o
    valor obtido via _esp_kpi_value (que alimenta os tiles do Dashboard por esp).

    Tolerancias (decisao S1):
      - BRL: 500 (R$ 500)
      - qty/int: 1 (uma unidade)
      - pct: 0.1 (0,1 ponto percentual)

    Implementacao minimal — compara via paths do WBR canonical. Quando os
    valores divergem por override (Card.metas_ppi) ou bridge (Sem Esp), o
    gatekeeper sinaliza divergencia real e (em modo blocking=False) registra
    WARNING sem bloquear publicacao. Pode evoluir para blocking=True em S2-B6
    apos schema unificado.
    """
    indicadores = (data or {}).get("wbr", {}).get("indicadores", {}) or {}
    tolerances = {"receita": 500, "volume": 500, "qty": 1, "pct": 0.1}
    aspect_per_kind = {"receita": None, "volume": None, "qty": "qty"}

    def _value_consolidado(kind: str, esp: str):
        kpi_id = _kpi_id(data, kind, aspect=aspect_per_kind.get(kind))
        if not kpi_id:
            return None
        ind = indicadores.get(kpi_id, {}) or {}
        n2 = (ind.get("n2") or ind.get("por_especialista") or {}).get(esp, {}) or {}
        for k in ("realizado_mtd", "realizado", "valor"):
            v = n2.get(k)
            if v is not None:
                return v
        return None

    for kind in ("receita", "volume", "qty"):
        tol = tolerances.get("receita" if kind == "receita" else
                             "volume" if kind == "volume" else "qty")
        for esp in (esp_list or []):
            consol_v = _value_consolidado(kind, esp)
            dash_v = _esp_kpi_value(data, esp, kind,
                                      aspect=aspect_per_kind.get(kind))
            # Skip quando ambos None (gap de dado, nao divergencia)
            if consol_v is None and dash_v is None:
                continue
            ok = _gatekeeper_numeric_close(consol_v, dash_v, tol)
            _gatekeeper_check(
                "#17",
                f"esp value consistente · {kind} · {esp}",
                condition=ok,
                details=f"consolidado={consol_v} dashboard={dash_v} tol={tol}",
                blocking=False,  # WARNING — S2-B6 podera promover para blocking=True
            )


def _render_donut_svg(p_ok: int, p_warn: int, p_bad: int, p_done: int = 0) -> str:
    """Donut: 4 stacked arcs over a circle.
    S1-A1#7 (2026-05-15): ordem revisada e paleta atualizada.
      Ordem horaria (a partir de 12h):
        1. Concluidas (#2e7d32 verde escuro) — primeiro
        2. No prazo  (#4caf50 verde claro)
        3. Atencao   (#ffc107 ambar)
        4. Atrasada  (#e40014 vermelho)
      Substituiu cinza #6b7e88 anterior por #2e7d32 (verde escuro) — gradiente
      positivo→negativo natural no sentido horario."""
    cx, cy, r = 100, 100, 70
    circ = 2 * 3.14159 * r
    seg_done = p_done / 100 * circ
    seg_ok = p_ok / 100 * circ
    seg_warn = p_warn / 100 * circ
    seg_bad = p_bad / 100 * circ
    return (
        f'<svg viewBox="0 0 200 200" width="200" height="200">'
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#f0f0eb" stroke-width="20"/>'
        # 1. Concluidas (verde escuro #2e7d32) — primeiro arc a partir de 12h
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#2e7d32" stroke-width="20" '
        f'stroke-dasharray="{seg_done} {circ}" transform="rotate(-90 {cx} {cy})"/>'
        # 2. No prazo (verde claro #4caf50)
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#4caf50" stroke-width="20" '
        f'stroke-dasharray="{seg_ok} {circ}" stroke-dashoffset="-{seg_done}" transform="rotate(-90 {cx} {cy})"/>'
        # 3. Atencao (ambar #ffc107)
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#ffc107" stroke-width="20" '
        f'stroke-dasharray="{seg_warn} {circ}" stroke-dashoffset="-{seg_done + seg_ok}" transform="rotate(-90 {cx} {cy})"/>'
        # 4. Atrasada (vermelho #e40014)
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#e40014" stroke-width="20" '
        f'stroke-dasharray="{seg_bad} {circ}" stroke-dashoffset="-{seg_done + seg_ok + seg_warn}" transform="rotate(-90 {cx} {cy})"/>'
        f'<text x="{cx}" y="{cy + 8}" text-anchor="middle" font-size="32" font-weight="500" fill="#424135">100%</text>'
        f'</svg>'
    )


def _render_owner_bars(tasks: list, acoes: dict) -> str:
    """C3 (2026-05-07): barras stacked por owner com segmentos No Prazo /
    Atencao / Atrasada (cores #2e7d32 / #d18000 / #c62828) e badge "ritual
    anterior" para tasks com criada_em_ritual_anterior=true.

    Classifica cada task em bucket via dias_restantes:
      - dias_restantes > 7  → No Prazo
      - 0 <= dias_restantes <= 7  → Atencao
      - dias_restantes < 0 OR critica/atrasada  → Atrasada

    Quando tasks nao tem dias_restantes (clickup raw), usa fallback acoes
    bucketizado (em_dia/atrasadas/criticas) somando por owner.
    """
    # Fix 2026-05-15: ESCOPO REDUZIDO — bars contam APENAS as acoes do slide 5
    # (WBR.acoes buckets: criticas + atrasadas + em_dia_priorizadas +
    # concluidas_eficazes). Antes contava todas as ~30 tasks ClickUp — gerava
    # inconsistencia visual entre donut e tabela. Agora os 3 elementos (donut,
    # bars, tabela) refletem o mesmo subset curado pelo analyst.
    # O parametro `tasks` (clickup_tasks) e ignorado nesta implementacao;
    # mantido na assinatura por compat.
    owners = {}
    for bucket_name, bucket_key in [("no_prazo", "em_dia_priorizadas"),
                                     ("atrasada", "atrasadas"),
                                     ("atrasada", "criticas"),  # criticas tambem renderiza como atrasada (vermelho)
                                     ("concluida", "concluidas_eficazes")]:
        for a in acoes.get(bucket_key, []) or []:
            # Fix 2026-05-15: usar `responsavel` (WBR canonical) ou `responsavel_externo`
            # (ClickUp raw) ou `owner` (renames internos). Antes so checava `owner` e
            # tudo caia em "Sem owner".
            owner = (a.get("responsavel") or a.get("responsavel_externo")
                     or a.get("owner") or "Sem owner")
            slot = owners.setdefault(owner, {"no_prazo": 0, "atencao": 0, "atrasada": 0, "concluida": 0, "ritual_anterior": 0})
            slot[bucket_name] += 1
            if a.get("criada_em_ritual_anterior"):
                slot["ritual_anterior"] += 1

    if not owners:
        return '<div style="color:var(--verde-claro);font-style:italic;">Sem dados de tasks por owner.</div>'

    # Total por owner = todas (incluindo concluidas)
    totals = {o: owners[o]["no_prazo"] + owners[o]["atencao"] + owners[o]["atrasada"] + owners[o]["concluida"] for o in owners}
    max_v = max(totals.values()) or 1

    bars = []
    for owner, total in sorted(totals.items(), key=lambda x: -x[1])[:8]:
        s = owners[owner]
        bar_w = (total / max_v) * 100
        # Segmento widths em % do total da barra (cada segmento dentro do bar_w)
        seg_ok = (s["no_prazo"] / total * 100) if total else 0
        seg_warn = (s["atencao"] / total * 100) if total else 0
        seg_bad = (s["atrasada"] / total * 100) if total else 0
        seg_done = (s["concluida"] / total * 100) if total else 0
        ritual_badge = (
            f'<span title="{s["ritual_anterior"]} criada(s) no ritual anterior" '
            f'style="color:var(--lime);font-size:13px;margin-right:4px;">⭐{s["ritual_anterior"]}</span>'
        ) if s["ritual_anterior"] else ""
        bars.append(
            f'<div class="bar-row" style="display:grid;grid-template-columns:160px 1fr 70px;align-items:center;gap:12px;font-size:13px;">'
            f'<div style="color:var(--verde-caqui);">{owner}</div>'
            f'<div style="background:#f0f0eb;border-radius:3px;height:18px;position:relative;display:flex;width:{bar_w:.1f}%;overflow:hidden;">'
            # S1-A1#7 (2026-05-15): paleta unificada com donut do slide 4.
            # Concluida = #2e7d32 (verde escuro); No prazo = #4caf50 (verde claro);
            # Atencao = #ffc107 (ambar); Atrasada = #e40014 (vermelho).
            f'<div title="{s["concluida"]} concluida(s)" style="background:#2e7d32;height:100%;width:{seg_done:.1f}%;"></div>'
            f'<div title="{s["no_prazo"]} no prazo" style="background:#4caf50;height:100%;width:{seg_ok:.1f}%;"></div>'
            f'<div title="{s["atencao"]} em atencao" style="background:#ffc107;height:100%;width:{seg_warn:.1f}%;"></div>'
            f'<div title="{s["atrasada"]} atrasada(s)" style="background:#e40014;height:100%;width:{seg_bad:.1f}%;"></div>'
            f'</div>'
            f'<div style="text-align:right;font-variant-numeric:tabular-nums;">{ritual_badge}<strong>{total}</strong></div>'
            f'</div>'
        )

    # Legenda compacta abaixo (4 categorias)
    # S1-A1#7 (2026-05-15): paleta unificada com donut. Ordem visual: Concluida →
    # No prazo → Atencao → Atrasada (gradiente positivo→negativo).
    legenda = (
        '<div style="display:flex;gap:14px;font-size:11px;color:var(--verde-claro);'
        'margin-top:10px;padding-top:8px;border-top:1px dashed var(--vc-100);flex-wrap:wrap;">'
        '<span><span style="display:inline-block;width:10px;height:10px;background:#2e7d32;'
        'border-radius:2px;vertical-align:middle;margin-right:4px;"></span>Concluida</span>'
        '<span><span style="display:inline-block;width:10px;height:10px;background:#4caf50;'
        'border-radius:2px;vertical-align:middle;margin-right:4px;"></span>No prazo</span>'
        '<span><span style="display:inline-block;width:10px;height:10px;background:#ffc107;'
        'border-radius:2px;vertical-align:middle;margin-right:4px;"></span>Atencao (≤7d)</span>'
        '<span><span style="display:inline-block;width:10px;height:10px;background:#e40014;'
        'border-radius:2px;vertical-align:middle;margin-right:4px;"></span>Atrasada</span>'
        '<span style="margin-left:auto;color:var(--verde-claro);font-style:italic;">'
        '⭐ = criada no ritual anterior</span></div>'
    )
    return "\n".join(bars) + "\n" + legenda


def _render_pa_vencendo_rows(acoes: dict, deviation_report_md: str = "",
                                manual_tasks: list = None) -> str:
    """Top 5 PAs by aging (criticas + atrasadas + em_dia next 7d).
    Template tem `<div class="pa-table">` com `<div class="pa-thead">` de 6 cols:
    # / Acao / Causa raiz / Responsavel / Prazo / Status. Renderizar `<div class="pa-row">`
    com 6 children matching."""
    rows = []
    causa_raiz_map = _build_causa_raiz_map(deviation_report_md) if deviation_report_md else {}
    # FIX (2026-05-14): dedupe causa-raiz por indicador. Antes, varias tasks com
    # mesmo indicador_alvo (ex: C-002/C-003/C-004/A-001 todas volume_consorcio_mensal)
    # mostravam o MESMO texto causa-raiz do deviation-cause-report. Visualmente:
    # 'Pedro Villarroel deve investigar bridge bug...' repetido 4 vezes — semanticamente
    # estranho porque o texto e estrutural (do indicador) mas a tabela mostra por task.
    # Solucao: trackear quais causas ja foram usadas; 2a+ aparicao cai no proximo
    # fallback (escalonamento_sugerido, palavras-chave do titulo, ou blank).
    seen_causas = set()
    idx = 1
    for a in acoes.get("criticas", []):
        rows.append(_pa_row(a, pill="bad", idx=idx, causa_raiz_map=causa_raiz_map, seen_causas=seen_causas))
        idx += 1
    for a in acoes.get("atrasadas", []):
        rows.append(_pa_row(a, pill="warn", idx=idx, causa_raiz_map=causa_raiz_map, seen_causas=seen_causas))
        idx += 1
    # FIX rodada 6 issue 4 — limite aumentado de 7 para 12 (slide tem capacidade
    # ate ~14 rows com font 14px). Tasks 86ah6d0t1/86ah6d1f2/86ah4n9z7/86ah6d0en
    # estavam sendo cortadas no limite anterior.
    for a in acoes.get("em_dia_priorizadas", []):
        if idx > 12:
            break
        rows.append(_pa_row(a, pill="good", idx=idx, causa_raiz_map=causa_raiz_map, seen_causas=seen_causas))
        idx += 1

    # FIX rodada 7 issue 10 — manual append de tasks declaradas em
    # Card.apresentacao.pa_manual_append (resolvido por render_pa_slides).
    # Render com pill-good (verde "EM DIA") conforme decidido pelo usuario.
    for a in (manual_tasks or []):
        if idx > 14:
            break  # limite total 14 (12 buckets + 2 manual)
        rows.append(_pa_row(a, pill="good", idx=idx, causa_raiz_map=causa_raiz_map, seen_causas=seen_causas))
        idx += 1

    # Fix 2026-05-15: append concluidas_eficazes ao final da tabela com pill="done"
    # (cinza azulado). Usuario quer ver progresso total do plano — nao so as ativas.
    for a in acoes.get("concluidas_eficazes", []) or []:
        if idx > 18:
            break  # limite total 18 (14 buckets + manual + ate 4 concluidas)
        rows.append(_pa_row(a, pill="done", idx=idx, causa_raiz_map=causa_raiz_map, seen_causas=seen_causas))
        idx += 1

    if not rows:
        return '<div class="pa-row empty" style="text-align:center;color:var(--verde-claro);font-style:italic;padding:20px;">Sem PAs vencendo nos proximos 7 dias.</div>'
    return "\n".join(rows)


def _build_causa_raiz_map(deviation_report_md: str) -> dict:
    """Mapa indicador (key normalizada) → causa-raiz curta extraida do deviation-cause-report.md.

    FIX img6 — captura tambem:
      - Multiplas hipoteses por indicador (concatena as primeiras 2)
      - "Recomendacoes" / "Acao corretiva" como fallback quando nao ha Causa-Raiz formal
      - Indicadores em qualquer secao (Vermelho, Amarelo, MTD insuficiente)
    """
    out = {}
    if not deviation_report_md:
        return out
    # Pattern principal: H3 indicador + H4 Causa-Raiz + Hipotese N
    pattern_main = re.compile(
        r"###\s+(?P<ind>[^\n]+)\n.*?####\s+Causa[-\s]Raiz.*?"
        r"\*\*Hipotese\s+\d+[^—]*—\s*(?P<causa>[^*\n]+)\*\*",
        re.IGNORECASE | re.DOTALL,
    )
    for m in pattern_main.finditer(deviation_report_md):
        ind_raw = m.group("ind").strip()
        causa = m.group("causa").strip()[:160]
        _store_causa_keys(out, ind_raw, causa)

    # Pattern fallback: H3 indicador SEM H4 Causa-Raiz, mas com Recomendacao
    pattern_fallback = re.compile(
        r"###\s+(?P<ind>[^\n]+)\n"
        r"(?P<body>(?:(?!###\s).)*?)"  # body ate proxima H3
        r"(?:####\s+(?:Recomendac|Acao\s+corretiv|Proxim))"
        r".*?"
        r"(?P<rec>[A-Z][^\n*]{20,180})",  # primeira sentenca apos
        re.IGNORECASE | re.DOTALL,
    )
    for m in pattern_fallback.finditer(deviation_report_md):
        ind_raw = m.group("ind").strip()
        # So adicionar se ainda nao tem causa para esse indicador
        if slugify(ind_raw) in out:
            continue
        rec = m.group("rec").strip()[:160]
        if rec:
            _store_causa_keys(out, ind_raw, rec)

    # Captura blocos "Diagnostico" tambem.
    # FIX 2026-05-20 Bug 2.i: bloquear cruzar fronteira H2 (\n## ) — antes,
    # **Diagnostico** que aparecia em secao H2 distinta (ex: ## Sem Atribuicao)
    # era amarrado ao H3 anterior, causando vazamento textual cross-secao.
    # Agora `(?:(?!###\s|\n## ).)*?` para o body no proximo H3 OU H2.
    pattern_diag = re.compile(
        r"###\s+(?P<ind>[^\n]+)\n"
        r"(?P<body>(?:(?!###\s|\n##\s).)*?)"
        r"\*\*[^*]*[Dd]iagnostico[^*]*\*\*\s*[—:]?\s*"
        r"(?P<diag>[^*\n]{20,200})",
        re.DOTALL,
    )
    for m in pattern_diag.finditer(deviation_report_md):
        ind_raw = m.group("ind").strip()
        if slugify(ind_raw) in out:
            continue
        diag = m.group("diag").strip()[:160]
        _store_causa_keys(out, ind_raw, diag)

    return out


def _store_causa_keys(out: dict, ind_raw: str, causa: str):
    """Guarda causa em multiplas keys (slug completo + 2 primeiras palavras + 1a palavra)
    para maximizar fuzzy match com `indicador` field das tasks."""
    out[slugify(ind_raw)] = causa
    words = re.findall(r"[a-zA-Z]+", ind_raw.lower())
    if len(words) >= 2:
        short = "_".join(words[:2])
        out.setdefault(short, causa)
    if words:
        first_word = words[0]
        if len(first_word) >= 5:
            out.setdefault(first_word, causa)


def _lookup_causa_raiz(indicador: str, causa_raiz_map: dict) -> str:
    """Fuzzy lookup: procura match de palavras-chave do `indicador` da task no map."""
    if not indicador or not causa_raiz_map:
        return ""
    ind_words = re.findall(r"[a-zA-Z]+", indicador.lower())
    if not ind_words:
        return ""
    slug = slugify(indicador)
    if slug in causa_raiz_map:
        return causa_raiz_map[slug]
    if len(ind_words) >= 2:
        short = "_".join(ind_words[:2])
        if short in causa_raiz_map:
            return causa_raiz_map[short]
    # FIX 2026-05-20 Bug 2.ii: word-boundary match em vez de substring.
    # Antes: `'quantidade' in 'oportunidades-estagnadas-quantidade-absoluta-...'` -> True,
    # mas semanticamente errado (Quantidade != Estagnadas Quantidade absoluta).
    # Agora: split key em tokens (palavras) e exigir match exato de pelo menos
    # uma palavra >=5 chars do indicador.
    for word in ind_words:
        if len(word) < 5:
            continue
        for key, causa in causa_raiz_map.items():
            key_tokens = re.findall(r"[a-zA-Z]+", key.lower())
            if word in key_tokens:
                return causa
    return ""


# FIX rodada 5 — keyword → causa mapping para tasks sem indicador.
# Padrao SEG WL S18: causas curtas tipo 'Pipeline parado', 'Auditoria comissao'.
# Lista N-parametrica: aplica-se a qualquer vertical. Usuarios podem adicionar novos
# patterns editando este dicionario. Match por OR sobre keywords (todas em lowercase).
_TASK_KEYWORD_TO_CAUSA = [
    (("estagn", "win/lose", "winlose", "renegoc", "destrava"), "Pipeline parado"),
    (("treinamento", "capacit", "fintrack", "treino"), "Capacitacao pendente"),
    (("marketing", "divulgacao", "calendario", "campanha"), "Acao marketing"),
    (("rotina", "carteira", "bater", "follow up", "followup"), "Cadencia comercial"),
    (("destino", "realoca", "transfer", "movimentacao"), "Realocacao squad"),
    (("diretriz", "mandatorio", "regra", "padronizacao"), "Padronizacao processo"),
    (("comissao", "comission", "comissi"), "Auditoria comissao"),
    (("metas", "indicador", "calculo", "dashboard", "louro"), "Falta sistema BI"),
    (("auditoria", "audit", "revisar"), "Auditoria pendente"),
    (("etl", "duplicidade", "dado", "qualidade dados"), "Risco dados"),
    (("apoia", "destravamen", "suporte"), "Suporte tactico"),
    (("checagem", "verificar", "validar", "validacao"), "Validacao"),
    (("intervencao", "engajamento", "reuniao", "alinhamento"), "Engajamento"),
    (("incorporar", "implementar", "configurar"), "Setup pendente"),
    (("apresent", "material", "deck"), "Material pendente"),
    (("bridge", "assigned", "uf_crm", "mapeamento"), "Bridge dados"),
    (("escalon", "escalar"), "Escalonamento pendente"),
    (("incentivo", "comissao agente"), "Incentivo pendente"),
]


def _infer_causa_from_title(title: str) -> str:
    """Aplica keyword mapping no titulo da task. Retorna '' se nenhum match."""
    if not title:
        return ""
    title_lc = title.lower()
    for keywords, causa in _TASK_KEYWORD_TO_CAUSA:
        for kw in keywords:
            if kw in title_lc:
                return causa
    return ""


def _pa_row(a: dict, pill: str, idx: int = 1, causa_raiz_map: dict = None, seen_causas: set = None) -> str:
    """Renderiza 1 row da pa-table (6 cols: # / Acao / Causa raiz / Responsavel / Prazo / Status).
    Match HTML structure do template (pa-table > pa-row > 6 div children).

    FIX (2026-05-14): analyst v1.1 emite chaves diferentes do esperado pelo template:
      responsavel (analyst) -> owner (template)
      due_date / due (analyst) -> prazo (template)
      indicador_alvo (analyst) -> indicador (causa raiz lookup)
      aging_dias / dias_atraso (analyst) -> aging
    Fazer fallback chain para destravar cells vazias (causa-raiz / responsavel / prazo)
    quando o WBR vem do schema v1.1.

    FIX (2026-05-14) dedupe causa-raiz: seen_causas e um set compartilhado entre
    chamadas do mesmo render_pa_slides — 2a+ ocorrencia da mesma causa cai no
    proximo fallback (escalonamento_sugerido / keyword_from_titulo / blank)."""
    if seen_causas is None:
        seen_causas = set()
    titulo = a.get("titulo") or a.get("name") or "—"
    owner = a.get("owner") or a.get("responsavel") or "—"
    prazo = a.get("prazo") or a.get("due_date") or a.get("due") or "—"
    # Normalizar prazo se vier em ISO datetime (ex: '2026-05-15T00:00:00') -> '2026-05-15'
    if isinstance(prazo, str) and len(prazo) > 10 and prazo[10] == "T":
        prazo = prazo[:10]
    aging = a.get("aging") or a.get("dias_restantes") or a.get("dias_atraso") or a.get("aging_dias")
    aging_str = ""
    aging_class = ""
    if aging is not None:
        if aging < 0:
            aging_str = f" <span style='color:var(--error);font-weight:500;'>({aging}d)</span>"
            aging_class = "bad"
        elif aging == 0:
            aging_str = " <span style='color:#d18000;font-weight:500;'>(hoje)</span>"
            aging_class = "warn"
        else:
            aging_str = f" <span style='color:var(--verde-claro);'>(+{aging}d)</span>"

    # FIX rodada 5 — Causa raiz multi-fonte com cascata:
    # 1. Custom field 'causa_raiz' do ClickUp (se existir)
    # 2. Lookup no deviation-cause-report.md por indicador
    # 3. Lookup no deviation-cause-report.md por palavras do titulo
    # 4. Keyword mapping inferida do titulo (padrao SEG WL: 'Pipeline parado', etc)
    # 5. Fallback "vinculada a {indicador}" quando ha indicador
    causa_raiz = "—"
    indicador_field = a.get("indicador") or a.get("indicador_alvo") or a.get("indicador_impactado") or ""
    if a.get("causa_raiz"):
        # Per-task causa explicit — sempre usar (nunca duplica naturalmente)
        causa_raiz = a.get("causa_raiz")
    else:
        # Causa do deviation-cause-report e por INDICADOR — varias tasks no mesmo
        # indicador veriam mesmo texto. Aplicar dedupe.
        causa_lookup = _lookup_causa_raiz(indicador_field, causa_raiz_map or {})
        if causa_lookup and causa_lookup not in seen_causas:
            causa_raiz = causa_lookup
            seen_causas.add(causa_lookup)
        elif causa_raiz_map:
            causa_lookup_titulo = _lookup_causa_raiz(titulo, causa_raiz_map)
            if causa_lookup_titulo and causa_lookup_titulo not in seen_causas:
                causa_raiz = causa_lookup_titulo
                seen_causas.add(causa_lookup_titulo)
        if causa_raiz == "—":
            # Causa do indicador ja usada por outra task — tenta fallbacks task-level.
            inferred = _infer_causa_from_title(titulo)
            if inferred:
                causa_raiz = inferred
            elif a.get("escalonamento_sugerido"):
                # FIX (2026-05-14): analyst emite escalonamento_sugerido — usar como
                # causa-raiz fallback quando lookup nao encontra (preserva contexto
                # estrategico que estava sendo descartado).
                causa_raiz = a.get("escalonamento_sugerido")[:120]
            elif indicador_field:
                causa_raiz = f"vinculada a {indicador_field}"

    status_label = pill.upper()
    if pill == "bad":
        status_label = "CRITICA"
    elif pill == "warn":
        status_label = "ATRASADA"
    elif pill == "good":
        status_label = "EM DIA"
    elif pill == "done":
        # S1-A1#7 (2026-05-15): tasks concluidas ganham check icon + label
        # "Concluido em" prefixando date_done (em vez de due_date).
        status_label = "✓ CONCLUIDA"
        # Concluidas nao mostram aging "(-Xd)" no prazo (irrelevante)
        aging_str = ""
        aging_class = ""
        # Coluna Prazo passa a mostrar date_done com label "Concluido em".
        date_done = a.get("date_done") or a.get("data_conclusao") or a.get("closed_at")
        if isinstance(date_done, str) and len(date_done) > 10 and date_done[10] == "T":
            date_done = date_done[:10]
        if date_done:
            prazo = f"<span style='color:var(--verde-claro);font-size:11px;letter-spacing:0.04em;'>Concluido em</span> {date_done}"
        # Sem date_done: mantem due_date original (informativo apenas)

    return (
        f'<div class="pa-row {aging_class}">'
        f'<div class="num">{idx:02d}</div>'
        f'<div class="acao">{titulo}</div>'
        f'<div class="causa-raiz">{causa_raiz}</div>'
        f'<div class="resp">{owner}</div>'
        f'<div class="prazo">{prazo}{aging_str}</div>'
        f'<div class="status"><span class="pill pill-{pill}">{status_label}</span></div>'
        f'</div>'
    )


# ============================================================
# Renderers — per Especialista (slides 6,7,8 / 9,10,11 / ...)
# ============================================================

def _resolve_assessor_alias(assessor_raw: str, card: dict) -> str:
    """Aplica Card.metadata.assessor_aliases para dedup manual de assessores.
    Ex: 'Káryne Bênutten' → 'Karyne Beuttenmüller'.
    FIX rodada 7 — lookup case-insensitive (via slugify) para evitar variantes
    de capitalizacao/acentuacao do JSON nao baterem com keys do Card.
    Ex: 'LUIS EDUARDO', 'Luís Eduardo', 'luis eduardo' todos resolvem para
    a key 'Luís Eduardo' do alias map.
    N-parametrico — qualquer Card pode declarar aliases."""
    if not assessor_raw or not isinstance(assessor_raw, str):
        return assessor_raw
    aliases = (card.get("metadata", {}) or {}).get("assessor_aliases") or {}
    raw = assessor_raw.strip()
    if raw in aliases:
        return aliases[raw]
    # Lookup case-insensitive via slugify
    raw_norm = slugify(raw)
    for k, v in aliases.items():
        if slugify(k) == raw_norm:
            return v
    return raw


def _get_current_month_prefix(data: dict) -> str:
    """Retorna 'YYYY-MM' do ciclo corrente do WBR data JSON.

    FIX (2026-05-14): WBR v1.1 nao tem 'metadata.ciclo' (legacy); tem 'meta.periodo.competencia'
    ou 'data_referencia' no top level. Sem o month prefix, _row_in_current_month nao filtra
    e o rank-card 'Fechadas' agrega HISTORICO inteiro (11W 8L) em vez de soh o mes corrente
    (0W 7L em maio). Cascade nas variantes."""
    wbr = data.get("wbr", {}) or {}
    # Legacy v1.0
    ciclo = (wbr.get("metadata") or {}).get("ciclo")
    if ciclo:
        return str(ciclo)[:7]
    # v1.1: meta.periodo.competencia (dict) OU meta.periodo string 'YYYY-MM' (o E6 analyst
    # as vezes emite periodo como string em vez de dict — tolerar ambos sem AttributeError). (2026-06-11)
    _periodo = (wbr.get("meta") or {}).get("periodo")
    if isinstance(_periodo, dict):
        comp = _periodo.get("competencia")
    elif isinstance(_periodo, str):
        comp = _periodo
    else:
        comp = None
    if comp and len(str(comp)) >= 7:
        return str(comp)[:7]
    # v1.1 top-level OU dentro de meta: data_referencia ou periodo_inicio
    _msrc = wbr.get("meta") or {}
    for key in ("data_referencia", "periodo_inicio", "periodo_fim"):
        v = wbr.get(key) or _msrc.get(key)
        if v and len(str(v)) >= 7:
            return str(v)[:7]
    return ""


def _row_in_current_month(row: dict, current_month: str) -> bool:
    """Filtro: aceita row se 'mes' field bate com mes corrente.
    Indicadores SNAPSHOT (oportunidades_*) nao tem 'mes' — usar 'data_referencia'.
    Quando nenhum dos dois existe, aceita (sem filtro temporal aplicavel)."""
    if not current_month:
        return True
    mes = row.get("mes") or row.get("data_referencia") or ""
    if not mes:
        return True
    return str(mes)[:7] == current_month


def _is_esp_direct(assessor) -> bool:
    """Detecta se assessor representa 'deal direto do especialista' (sem assessor mapeado).
    Variantes: None, '', 'Sem Assessor', 'Sem assessor', 'sem assessor', etc."""
    if assessor is None:
        return True
    if not isinstance(assessor, str):
        return False
    norm = assessor.strip().lower()
    return norm in ("", "sem assessor", "sem-assessor", "semassessor", "—", "-")


def _normalize_assessor_name(name: str) -> str:
    """Normaliza nome de assessor para deduplicar variantes (encoding, espacos, acentos abreviados).
    Estrategia: lowercase + strip + collapse espacos + slug. Retorna chave canonica.
    O nome de exibicao mantem a versao original (mais longa = mais completa)."""
    if not name:
        return ""
    return slugify(name.strip())


def _assessor_in_squad(name: str, squad_norms: set) -> bool:
    """Match flexivel de assessor vs squad whitelist.

    Tres estrategias em cascata:
      1) slug completo do nome (ex: 'Roberto Saraiva' -> 'roberto_saraiva') em squad_norms
      2) primeiro nome do `name` em squad_norms (ex: 'Waleska Feitoza' -> 'waleska')
      3) primeiro nome em qualquer entry de squad_norms (ex: squad tem 'roberto_saraiva',
         row tem 'roberto' soh)

    FIX (2026-05-14): bug #1-7. Squad declarava 'Waleska' / 'David Oliveira Leite' mas
    a fonte de dados emitia 'Waleska Feitoza' / 'David Oliveira'. Match exato falhava
    -> assessor virava 'outsider' -> Cobertura squad 0/13 errada. Estrategia (2) e (3)
    casam por primeiro nome com tolerancia."""
    if not name or not squad_norms:
        return False
    full_slug = _normalize_assessor_name(name)
    if full_slug in squad_norms:
        return True
    parts = full_slug.split("_")
    if not parts:
        return False
    first = parts[0]
    # Estrategia 2: primeiro nome direto em squad_norms (squad tem so primeiro nome)
    if first in squad_norms:
        return True
    # Estrategia 3: primeiro nome bate com primeiro nome de algum squad entry
    for sq in squad_norms:
        if sq.split("_")[0] == first:
            return True
    return False


def _consolidate_by_normalized_name(by_key: dict) -> dict:
    """Agrega entradas com mesma chave normalizada (acentos/encoding/espacos).
    Mantem o display name MAIS LONGO (geralmente o mais completo) como label canonico."""
    by_norm = {}
    for raw_name, m in by_key.items():
        norm = _normalize_assessor_name(raw_name) if "(esp)" not in raw_name else raw_name
        if norm not in by_norm:
            by_norm[norm] = {"_display_name": raw_name.strip(), "_data": m}
        else:
            # Mantem display name mais longo
            existing = by_norm[norm]["_display_name"]
            if len(raw_name.strip()) > len(existing):
                by_norm[norm]["_display_name"] = raw_name.strip()
            # Soma metricas
            existing_m = by_norm[norm]["_data"]
            for k, v in m.items():
                if k.startswith("_"):
                    continue
                if isinstance(v, (int, float)):
                    existing_m[k] = existing_m.get(k, 0) + v
    # Reconstruir dict {display_name: data}
    out = {}
    for norm_key, bundle in by_norm.items():
        out[bundle["_display_name"]] = bundle["_data"]
    return out


def _aggregate_assessor_volumes(esp: str, dados_n5: dict, ctx: dict, scope: str = "squad",
                                 card: dict = None, current_month: str = "") -> dict:
    """Variant que coleta tambem volume + tempo_medio_dias por assessor.
    Retorna dict {assessor_label → {ativas_qty, ativas_vol, criadas_qty, criadas_vol,
                                     fechadas_qty, fechadas_vol, won, lose,
                                     estagnadas_qty, estagnadas_vol, estagnadas_tempo_pond,
                                     estagnadas_tempo_den, _is_esp_direct, _esp_origem}}.
    N-parametrico para qualquer vertical/esp."""
    if not dados_n5:
        return {}
    indicadores = dados_n5.get("indicadores", [])
    esp_list = ctx.get("_esp_list", []) if ctx else []
    esp_direct_label = f"{esp} (esp)"

    # FIX rodada 6 issue 14 — squad whitelist oficial do Card
    squad_whitelist = _get_squad_whitelist(esp, card or {})
    squad_norms = {_normalize_assessor_name(a) for a in squad_whitelist}

    # Refator 2026-05-07 — resolve IDs dinamicamente por kind (vertical-agnostic)
    ativas_id     = _resolve_kpi_id(indicadores, "ativas")
    criadas_id    = _resolve_kpi_id(indicadores, "criadas")
    estagnadas_id = _resolve_kpi_id(indicadores, "estagnadas")
    taxa_id       = _resolve_kpi_id(indicadores, "taxa_conversao")
    receita_id    = _resolve_kpi_id(indicadores, "receita")
    quantidade_id = _resolve_kpi_id(indicadores, "quantidade")

    metric_map = {}
    if ativas_id:     metric_map[ativas_id]     = ("ativas",     "quantidade", "volume")
    if criadas_id:    metric_map[criadas_id]    = ("criadas",    "quantidade", "volume")
    if estagnadas_id: metric_map[estagnadas_id] = ("estagnadas", "quantidade", "volume")
    if taxa_id:       metric_map[taxa_id]       = ("fechadas",   "total_fechados", None)

    monthly_ids = {x for x in (receita_id, criadas_id, taxa_id, quantidade_id) if x}

    by_key = {}
    for entry in indicadores:
        ind_id = entry.get("indicator_id", "")
        if ind_id not in metric_map:
            continue
        metric_key, qty_field, vol_field = metric_map[ind_id]
        # FIX rodada 5 — filtrar mes corrente para indicadores monthly
        is_monthly = ind_id in monthly_ids
        for row in entry.get("data", []):
            if is_monthly and current_month and not _row_in_current_month(row, current_month):
                continue
            # FIX rodada 6 issue 11/12/13 — pular rows quebradas por estagio
            # (snapshot indicators tem 1 row total + N rows por estagio; somar
            # tudo duplica o total). Mantem apenas rows totais (estagio is None).
            if row.get("estagio"):
                continue
            row_esp = row.get("especialista")
            assessor_raw = row.get("assessor")
            # FIX rodada 5 — aplicar alias map antes de bucket
            assessor = _resolve_assessor_alias(assessor_raw, card or {}) if card else assessor_raw

            if scope == "squad":
                if row_esp != esp:
                    continue
                if row.get("nivel") != "N5-Assessor":
                    continue
                if _is_esp_direct(assessor):
                    bucket_key = esp_direct_label
                else:
                    bucket_key = (assessor or "").strip()  # strip para evitar 'Amanda ' vs 'Amanda'
                    # FIX rodada 6 issue 14 — squad whitelist: pula assessor que
                    # nao esta na squad oficial (ex: Ronaldo Dantas mapeado a
                    # Douglas no Bitrix mas nao e da squad oficial). Se Card
                    # nao declara squad, comportamento legado preservado.
                    if squad_norms and not _assessor_in_squad(bucket_key, squad_norms):
                        continue
            elif scope == "outside_squad":
                # FIX rodada 7 issue 4 — semantica nova: assessores N5 do MESMO esp
                # mas FORA da squad whitelist (ex: Ronaldo Dantas com deal atribuido
                # ao Douglas no Bitrix mas que nao pertence ao squad oficial).
                # Substitui comportamento legado "outside" que pegava esps fantasmas
                # (Joel/Nacha N2 fora do esp_list — nao eram do esp atual).
                if row_esp != esp:
                    continue
                if row.get("nivel") != "N5-Assessor":
                    continue
                if _is_esp_direct(assessor):
                    continue  # esp_direct nao e outsider
                bucket_key = (assessor or "").strip()
                # Se Card nao declara squad whitelist, comportamento legado: vazio
                if not squad_norms:
                    continue
                # So entra se NAO esta na whitelist
                if _assessor_in_squad(bucket_key, squad_norms):
                    continue
                # 2026-05-07: outside_squad ignora rows zeradas (assessor sem deal/criada/etc).
                # Karyne Beuttenmuller (Tarcisio's squad) aparecia 0/0/0/0 em Claudia outside.
                if (row.get("quantidade") or 0) <= 0:
                    continue
            elif scope == "outside":
                # Comportamento LEGADO mantido (esps fantasmas N2). Cards novos devem usar
                # outside_squad. Mantido para backward compat de outras verticais.
                if ind_id != ativas_id:
                    continue
                if row.get("nivel") != "N2-Especialista":
                    continue
                if not row_esp or row_esp in esp_list or row_esp == esp:
                    continue
                if (row.get("quantidade") or 0) <= 0:
                    continue
                bucket_key = row_esp
            else:
                continue

            if bucket_key not in by_key:
                by_key[bucket_key] = {
                    "ativas_qty": 0, "ativas_vol": 0,
                    "criadas_qty": 0, "criadas_vol": 0,
                    "fechadas_qty": 0, "won": 0, "lose": 0,
                    "estagnadas_qty": 0, "estagnadas_vol": 0,
                    "estagnadas_tempo_pond": 0, "estagnadas_tempo_den": 0,
                    "_esp_origem": row_esp,
                    "_is_esp_direct": (scope == "squad" and bucket_key == esp_direct_label),
                }
            qty = row.get(qty_field) or 0
            vol = row.get(vol_field) or 0 if vol_field else 0
            if ind_id == taxa_id:
                by_key[bucket_key]["fechadas_qty"] += qty
                by_key[bucket_key]["won"] += row.get("total_ganhos") or 0
                by_key[bucket_key]["lose"] += row.get("total_perdidos") or 0
            elif ind_id == estagnadas_id:
                by_key[bucket_key]["estagnadas_qty"] += qty
                by_key[bucket_key]["estagnadas_vol"] += vol
                tempo = row.get("tempo_medio_dias") or 0
                by_key[bucket_key]["estagnadas_tempo_pond"] += tempo * qty
                by_key[bucket_key]["estagnadas_tempo_den"] += qty
            else:
                by_key[bucket_key][f"{metric_key}_qty"] += qty
                if vol_field:
                    by_key[bucket_key][f"{metric_key}_vol"] += vol

    # Reconciliacao N2-N5 para esp_direct (squad apenas)
    if scope == "squad":
        for entry in indicadores:
            ind_id = entry.get("indicator_id", "")
            if ind_id not in metric_map:
                continue
            metric_key, qty_field, vol_field = metric_map[ind_id]
            is_monthly = ind_id in monthly_ids
            n2_qty = n2_vol = n5_qty = n5_vol = 0
            n5_esp_direct_qty = n5_esp_direct_vol = 0
            for row in entry.get("data", []):
                if is_monthly and current_month and not _row_in_current_month(row, current_month):
                    continue
                if row.get("especialista") != esp:
                    continue
                if row.get("nivel") == "N2-Especialista":
                    if not row.get("estagio"):
                        n2_qty += row.get(qty_field) or 0
                        n2_vol += row.get(vol_field) or 0 if vol_field else 0
                elif row.get("nivel") == "N5-Assessor":
                    q = row.get(qty_field) or 0
                    v = row.get(vol_field) or 0 if vol_field else 0
                    if _is_esp_direct(row.get("assessor")):
                        n5_esp_direct_qty += q
                        n5_esp_direct_vol += v
                    else:
                        n5_qty += q
                        n5_vol += v
            diff_qty = n2_qty - n5_qty - n5_esp_direct_qty
            diff_vol = n2_vol - n5_vol - n5_esp_direct_vol
            if diff_qty > 0 or diff_vol > 0:
                by_key.setdefault(esp_direct_label, {
                    "ativas_qty": 0, "ativas_vol": 0,
                    "criadas_qty": 0, "criadas_vol": 0,
                    "fechadas_qty": 0, "won": 0, "lose": 0,
                    "estagnadas_qty": 0, "estagnadas_vol": 0,
                    "estagnadas_tempo_pond": 0, "estagnadas_tempo_den": 0,
                    "_esp_origem": esp, "_is_esp_direct": True,
                })
                if ind_id == taxa_id:
                    by_key[esp_direct_label]["fechadas_qty"] += max(0, diff_qty)
                elif ind_id == estagnadas_id:
                    if diff_qty > 0:
                        by_key[esp_direct_label]["estagnadas_qty"] += diff_qty
                    if diff_vol > 0:
                        by_key[esp_direct_label]["estagnadas_vol"] += diff_vol
                else:
                    if diff_qty > 0:
                        by_key[esp_direct_label][f"{metric_key}_qty"] += diff_qty
                    if vol_field and diff_vol > 0:
                        by_key[esp_direct_label][f"{metric_key}_vol"] += diff_vol

    # FIX rodada 6 issue 14 — zero-fill: garantir que TODOS os assessores oficiais
    # da squad apareçam (mesmo zerados). Padrao SEG WL S18.
    if scope == "squad" and squad_whitelist:
        present_norms = {_normalize_assessor_name(k): k for k in by_key.keys()}
        for official in squad_whitelist:
            if _normalize_assessor_name(official) not in present_norms:
                by_key[official] = {
                    "ativas_qty": 0, "ativas_vol": 0,
                    "criadas_qty": 0, "criadas_vol": 0,
                    "fechadas_qty": 0, "won": 0, "lose": 0,
                    "estagnadas_qty": 0, "estagnadas_vol": 0,
                    "estagnadas_tempo_pond": 0, "estagnadas_tempo_den": 0,
                    "_esp_origem": esp, "_is_esp_direct": False,
                }
    return by_key


def _aggregate_assessor_metrics(esp: str, dados_n5: dict, ctx: dict, scope: str = "squad") -> dict:
    """Agrega metricas por assessor para o esp (Slide 7 Analise rank rows).

    scope='squad' = (a) assessores onde especialista==esp + (b) deals diretos do esp
                    (assessor=null/sem assessor) consolidados em UMA linha "{esp} (esp)".
    scope='outside' = especialistas N2 fora do `_esp_list` do ritual (N2 fantasmas
                      tipo Joel Freitas, Nacha Coutinho — relevantes para auditoria).
                      Consolida por especialista (1 linha por esp fora do ritual).

    N-parametrico: funciona para qualquer vertical, qualquer set de esps no ritual.
    """
    if not dados_n5:
        return {}
    indicadores = dados_n5.get("indicadores", [])
    esp_list = ctx.get("_esp_list", []) if ctx else []

    # Refator 2026-05-07 — resolve IDs dinamicamente por kind (vertical-agnostic)
    ativas_id     = _resolve_kpi_id(indicadores, "ativas")
    criadas_id    = _resolve_kpi_id(indicadores, "criadas")
    estagnadas_id = _resolve_kpi_id(indicadores, "estagnadas")
    taxa_id       = _resolve_kpi_id(indicadores, "taxa_conversao")

    metric_map = {}
    if ativas_id:     metric_map[ativas_id]     = ("ativas",     "quantidade")
    if criadas_id:    metric_map[criadas_id]    = ("criadas",    "quantidade")
    if estagnadas_id: metric_map[estagnadas_id] = ("estagnadas", "quantidade")
    if taxa_id:       metric_map[taxa_id]       = ("fechadas",   "total_fechados")

    by_key = {}
    esp_direct_label = f"{esp} (esp)"

    for entry in indicadores:
        ind_id = entry.get("indicator_id", "")
        if ind_id not in metric_map:
            continue
        metric_key, value_field = metric_map[ind_id]
        for row in entry.get("data", []):
            row_esp = row.get("especialista")
            assessor = row.get("assessor")

            if scope == "squad":
                # Escopo: tudo do esp atual
                if row_esp != esp:
                    continue
                # Para evitar duplicacao N2/N5: usar APENAS rows N5-Assessor
                # Excecao: rows N2-Especialista do esp com assessor=null sao deals
                # diretos que NAO aparecem em N5 — entao incluir desses
                if row.get("nivel") == "N5-Assessor":
                    if _is_esp_direct(assessor):
                        # Mesmo em N5, rows com assessor null/sem ja sao consolidados
                        bucket_key = esp_direct_label
                    else:
                        bucket_key = assessor
                else:
                    # NAO N5 — pular (evita double-count); deals sem assessor sao
                    # tratados via diff N2-N5 abaixo apos o loop
                    continue
            elif scope == "outside":
                # Outside = N2-Especialista de esp fora do ritual mapeado.
                # FILTRO: apenas esps com presenca no SNAPSHOT ATUAL (ativas),
                # senao incluiriamos historico de fechadas/perdidas com esps que ja sairam (Bianca, Maria etc).
                if ind_id != ativas_id:
                    continue
                if row.get("nivel") != "N2-Especialista":
                    continue
                if not row_esp or row_esp in esp_list:
                    continue
                if row_esp == esp:
                    continue
                # Pular row total sem estagio (qty=0 vol=0 vai duplicar consolidando)
                # Manter apenas rows com qty>0
                if (row.get("quantidade") or 0) <= 0:
                    continue
                bucket_key = row_esp  # consolidar por especialista fora do ritual
            else:
                continue

            v = row.get(value_field) or 0
            if bucket_key not in by_key:
                by_key[bucket_key] = {"ativas": 0, "criadas": 0, "fechadas": 0, "estagnadas": 0,
                                       "won": 0, "lose": 0, "_esp_origem": row_esp,
                                       "_is_esp_direct": (scope == "squad" and bucket_key == esp_direct_label)}
            if ind_id == taxa_id:
                by_key[bucket_key]["fechadas"] += v
                by_key[bucket_key]["won"] += row.get("total_ganhos") or 0
                by_key[bucket_key]["lose"] += row.get("total_perdidos") or 0
            else:
                by_key[bucket_key][metric_key] += v

    # Para scope=squad, calcular esp_direct via diff N2 - SUM(N5):
    # se algum indicador tem N2 maior que SUM(N5 com assessor != null/sem),
    # a diferenca e atribuida ao esp_direct_label
    if scope == "squad":
        for entry in indicadores:
            ind_id = entry.get("indicator_id", "")
            if ind_id not in metric_map:
                continue
            metric_key, value_field = metric_map[ind_id]
            n2_total = 0
            n5_assessor_total = 0
            n5_esp_direct = 0
            for row in entry.get("data", []):
                if row.get("especialista") != esp:
                    continue
                if row.get("nivel") == "N2-Especialista":
                    n2_total += row.get(value_field) or 0
                elif row.get("nivel") == "N5-Assessor":
                    v = row.get(value_field) or 0
                    if _is_esp_direct(row.get("assessor")):
                        n5_esp_direct += v
                    else:
                        n5_assessor_total += v
            diff = n2_total - n5_assessor_total - n5_esp_direct
            if diff > 0:
                # Adicionar ao esp_direct_label para reconciliar com o KPI tile
                by_key.setdefault(esp_direct_label, {
                    "ativas": 0, "criadas": 0, "fechadas": 0, "estagnadas": 0,
                    "won": 0, "lose": 0, "_esp_origem": esp, "_is_esp_direct": True,
                })
                if ind_id == taxa_id:
                    by_key[esp_direct_label]["fechadas"] += diff
                else:
                    by_key[esp_direct_label][metric_key] += diff

    return by_key


def _render_rank_rows_v2(by_key_volumes_raw: dict, scope: str = "squad") -> str:
    """REFACTOR 2026-05-05 (rodada 4 — features SEG WL S18):
      - Ordem ALFABETICA por nome do assessor
      - Cada row: 4 cells (Ativas/Criadas/Fechadas/Estagnadas)
      - Cada cell: bar lime proporcional ao max_metric + label 'X (R$ Y)' inline
      - Estagnadas mostra tempo medio
      - Fechadas mostra total + dual won/lose
      - Esp_direct: italic + bold ('{esp} (esp)')
      - Outside: cor cinza + italic
    N-parametrico — funciona para qualquer vertical/esp."""
    if not by_key_volumes_raw:
        if scope == "squad":
            msg = "Sem dados N5 para esta visao."
        elif scope == "outside_squad":
            msg = "Nenhum assessor fora da squad com deal atribuido."
        else:
            msg = "Sem especialistas fora do ritual."
        return (f'<div class="rank-row empty" style="padding:12px;color:var(--verde-claro);'
                f'font-style:italic;font-size:13px;">{msg}</div>')

    # FIX rodada 4 — deduplicar por nome normalizado (acentos, encoding, espacos diferentes)
    by_key_volumes = _consolidate_by_normalized_name(by_key_volumes_raw)

    # Edit #7 (2026-05-13): em scope "outside_squad" (equivalente "Outros" do PJ2),
    # filtrar assessores que zeraram TUDO (sem opp criada nem fechada no mes).
    # FIX (2026-05-14): tambem incluir assessores com ativas > 0 ou estagnadas > 0.
    # Usuario reclamou que "tile diz 16 ativas, soma do gráfico diz 12, onde estão as 4?"
    # — as 4 sao outsiders (Humberto, Ronaldo) com ativas mas sem criadas/fechadas no mes.
    # Filtro precisa contemplar QUALQUER sinal (ativas ou estagnadas ou criadas ou fechadas).
    if scope == "outside_squad":
        by_key_volumes = {
            k: m for k, m in by_key_volumes.items()
            if (m.get("ativas_qty", 0) or 0) > 0
            or (m.get("criadas_qty", 0) or 0) > 0
            or (m.get("fechadas_qty", 0) or 0) > 0
            or (m.get("estagnadas_qty", 0) or 0) > 0
        }
        if not by_key_volumes:
            return (
                '<div class="rank-row empty" style="padding:12px;color:var(--verde-claro);'
                'font-style:italic;font-size:13px;">Nenhum assessor fora da squad com '
                'deal ativo ou movimento no mes.</div>'
            )

    # S1-A2 iter 8 (2026-05-17): Ordem por CRIADAS DESC (quem criou mais fica em
    # cima). Esp_direct ('(esp)' suffix) sempre no topo. Desempate alfabetico.
    def _sort_key(item):
        key, m = item
        if "(esp)" in key:
            return (0, 0, key.lower())  # esp_direct sempre topo
        criadas = m.get("criadas_qty", 0) or 0
        return (1, -criadas, key.lower())  # criadas DESC, alfabetica desempate
    sorted_items = sorted(by_key_volumes.items(), key=_sort_key)

    # Max por metric (para escala proporcional)
    max_metrics = {
        "ativas": max((m.get("ativas_qty", 0) for _, m in sorted_items), default=0) or 1,
        "criadas": max((m.get("criadas_qty", 0) for _, m in sorted_items), default=0) or 1,
        "fechadas": max((m.get("fechadas_qty", 0) for _, m in sorted_items), default=0) or 1,
        "estagnadas": max((m.get("estagnadas_qty", 0) for _, m in sorted_items), default=0) or 1,
    }

    def _bar_cell(qty: int, vol: float, max_v: int, *, label_extra: str = "",
                  zero_label: str = "0", show_volume: bool = True) -> str:
        """Cell com bar lime sobre track transparente cinza. FIX rodada 5: track 100%
        SEMPRE visivel (mesmo qty=0), inner fill proporcional. Padrao SEG WL S18.

        R5-6 (2026-05-07): show_volume=False suprime `(R$ X)` no label — usado em
        Criadas (qty-only metric, volume nao agrega valor a leitura)."""
        # Track sempre 100% width, cor #F0F0EE (cinza super claro)
        # Fill: lime quando qty>0, cinza#D0D0CC quando qty=0 (so para mostrar label)
        # FIX (2026-05-14 iter 2): track height 16px -> 18px, padding interno
        # mais generoso (left 6px -> 8px) e padding-cell 0 4px -> 4px 6px.
        # Mantem 11px/weight 700 (PJ2 typography), aumenta respiro vertical.
        if qty <= 0:
            label = f'<div style="position:absolute;top:0;left:8px;color:#79755C;font-size:11px;font-weight:700;line-height:18px;">{zero_label}</div>'
            return (
                '<div class="rcell" style="padding:4px 6px;">'
                '<div style="background:#F0F0EE;border-radius:2px;height:18px;width:100%;position:relative;">'
                f'{label}'
                '</div></div>'
            )
        pct = max(8, min(95, (qty / max_v) * 100))
        vol_str = f' (R$ {fmt_brl_num_compact(vol)})' if (vol > 0 and show_volume) else ""
        full_label = f"{qty}{vol_str}{label_extra}"
        return (
            '<div class="rcell" style="padding:4px 6px;">'
            '<div style="background:#F0F0EE;border-radius:2px;height:18px;width:100%;position:relative;overflow:hidden;">'
            f'<div style="background:#EEF77C;border-radius:2px;height:100%;width:{pct:.0f}%;"></div>'
            f'<div style="position:absolute;top:0;left:8px;color:#000;font-size:11px;font-weight:700;line-height:18px;white-space:nowrap;">{full_label}</div>'
            '</div></div>'
        )

    def _fechadas_cell(won: int, lose: int) -> str:
        """Dual bar Fechadas — 2 segmentos visuais sobre track 100%.
        R6 (2026-05-07): cada segmento tem seu proprio label (XW preto no verde,
        YL branco no vermelho); sem label total separado.
        Largura de cada segmento dentro do track e proporcional a own qty (won ou lose)
        contra o max_metrics["fechadas"].
        FIX (2026-05-14 iter 2): track height 18px, padding 4px 6px, label padding 8px."""
        total = won + lose
        if total <= 0:
            return (
                '<div class="rcell" style="padding:4px 6px;">'
                '<div style="background:#F0F0EE;border-radius:2px;height:18px;width:100%;position:relative;">'
                '<div style="position:absolute;top:0;left:8px;color:#79755C;font-size:11px;font-weight:700;line-height:18px;">0</div>'
                '</div></div>'
            )
        max_v = max_metrics["fechadas"] or 1
        # Cada segmento ocupa proporcao independente do max — visualmente fica
        # "won_w | lose_w" dentro do track de 100% width.
        won_pct = max(0, min(95, (won / max_v) * 100)) if won else 0
        lose_pct = max(0, min(95, (lose / max_v) * 100)) if lose else 0
        # Label W e L: ambos branco sobre seus respectivos backgrounds.
        # FIX (2026-05-29 Seg RE): min-width 28px + flex-shrink:0 garante que
        # "1W"/"1L" caibam mesmo quando max_v >> qty (caso contrario overflow:hidden
        # corta a letra e fica so o numero, ex "1 6L", "1 1").
        won_label = (
            f'<div style="background:#4caf50;height:100%;width:{won_pct:.1f}%;'
            f'min-width:28px;flex-shrink:0;'
            f'position:relative;display:flex;align-items:center;padding-left:8px;'
            f'color:#fff;font-size:11px;font-weight:700;line-height:18px;'
            f'overflow:hidden;white-space:nowrap;">{won}W</div>'
        ) if won > 0 else ''
        lose_label = (
            f'<div style="background:var(--error);height:100%;width:{lose_pct:.1f}%;'
            f'min-width:28px;flex-shrink:0;'
            f'position:relative;display:flex;align-items:center;padding-left:8px;'
            f'color:#fff;font-size:11px;font-weight:700;line-height:18px;'
            f'overflow:hidden;white-space:nowrap;">{lose}L</div>'
        ) if lose > 0 else ''
        return (
            '<div class="rcell" style="padding:4px 6px;">'
            '<div style="background:#F0F0EE;border-radius:2px;height:18px;width:100%;position:relative;overflow:hidden;display:flex;">'
            f'{won_label}{lose_label}'
            '</div></div>'
        )

    rows = []
    for key, m in sorted_items:
        is_esp_direct = m.get("_is_esp_direct", False)
        if is_esp_direct:
            rname_style = 'font-style:italic;font-weight:700;'
        elif scope in ("outside", "outside_squad"):
            rname_style = 'color:var(--verde-claro);font-style:italic;'
        else:
            rname_style = ''
        rname = f'<div class="rname" style="{rname_style}">{key}</div>'

        # Cells
        ativas_cell = _bar_cell(m.get("ativas_qty", 0), m.get("ativas_vol", 0), max_metrics["ativas"])
        # R5-6 (2026-05-07): Criadas e qty-only metric — suprimir `(R$ X)` parens.
        criadas_cell = _bar_cell(m.get("criadas_qty", 0), m.get("criadas_vol", 0),
                                  max_metrics["criadas"], show_volume=False)
        fechadas_cell = _fechadas_cell(m.get("won", 0), m.get("lose", 0))
        # Estagnadas: qty + vol + tempo medio
        estag_qty = m.get("estagnadas_qty", 0)
        tempo_med = (m.get("estagnadas_tempo_pond", 0) / m["estagnadas_tempo_den"]
                     if m.get("estagnadas_tempo_den") else 0)
        tempo_extra = f" · {int(tempo_med)}d" if tempo_med > 0 else ""
        estagnadas_cell = _bar_cell(estag_qty, m.get("estagnadas_vol", 0),
                                     max_metrics["estagnadas"], label_extra=tempo_extra)

        rows.append(
            f'<div class="rank-row">{rname}{ativas_cell}{criadas_cell}{fechadas_cell}{estagnadas_cell}</div>'
        )
    return "\n".join(rows)


def fmt_brl_num_compact(v) -> str:
    """Formato BRL apenas numero (sem prefixo) compact: 24K, 1,2M."""
    if v is None or not isinstance(v, (int, float)):
        return "—"
    if abs(v) >= 1e6:
        return f"{v/1e6:.1f}M".replace(".", ",")
    if abs(v) >= 1e3:
        return f"{v/1e3:.0f}K"
    return f"{v:.0f}"


def _render_rank_rows(by_key: dict, max_rows: int = 12, scope: str = "squad") -> str:
    """Renderiza N rank-rows ordenadas por ativas DESC (limit configuravel).
    N-parametrico: funciona para qualquer numero de assessores/esps.

    Cada cell tem mini-bar visual proporcional ao max do conjunto + numero.
    Coluna Fechadas tem dual bar (won verde + lose vermelho) quando taxa_conversao tem dados.
    Esp_direct rows tem label `{esp} (esp)` em italic + classe .esp.
    Outside rows mostram esp_origem entre parens em label muted.
    """
    if not by_key:
        msg = ("Sem dados N5 para esta visao." if scope == "squad"
               else "Sem especialistas fora do ritual.")
        return (f'<div class="rank-row empty" style="padding:12px;color:var(--verde-claro);'
                f'font-style:italic;font-size:13px;">{msg}</div>')
    # Normalizar 0-qty rows: se assessor tem 0 em todos os 4, manter mas ordenar pro fim
    sorted_items = sorted(
        by_key.items(),
        key=lambda x: -(x[1].get("ativas", 0) + x[1].get("estagnadas", 0)
                        + x[1].get("criadas", 0) + x[1].get("fechadas", 0)),
    )

    # Calcular max por metric para barras proporcionais
    max_metrics = {
        "ativas": max((m.get("ativas", 0) for _, m in sorted_items), default=0) or 1,
        "criadas": max((m.get("criadas", 0) for _, m in sorted_items), default=0) or 1,
        "fechadas": max((m.get("fechadas", 0) for _, m in sorted_items), default=0) or 1,
        "estagnadas": max((m.get("estagnadas", 0) for _, m in sorted_items), default=0) or 1,
    }

    def _num_cell(value: int) -> str:
        """FIX img9 — celula simples so com numero (sem mini-bar). Mais limpa, evita
        ilusao de ordenacao ('barras pequenas iguais') quando max_v dwarfs values."""
        cls = "" if value > 0 else "zero"
        return (
            f'<div class="rcell">'
            f'<div class="vnum" style="font-size:13px;font-variant-numeric:tabular-nums;'
            f'{"color:var(--vc-300);" if value <= 0 else ""}">{value}</div>'
            f'</div>'
        )

    def _fechadas_cell(won: int, lose: int) -> str:
        """FIX img9 — coluna Fechadas: total + dual bar (won/lose) so se houve fechamentos.
        Sem 'porcentagem de conversao' explicita (nao foi combinado)."""
        total = won + lose
        if total <= 0:
            return '<div class="rcell"><div class="vnum" style="color:var(--vc-300);">0</div></div>'
        won_pct = (won / total) * 100
        lose_pct = (lose / total) * 100
        return (
            f'<div class="rcell">'
            f'<div class="mini dual" style="display:flex;background:#f0f0eb;height:4px;border-radius:2px;margin-bottom:2px;overflow:hidden;width:60%;">'
            f'<div style="background:#4caf50;height:100%;width:{won_pct:.0f}%;"></div>'
            f'<div style="background:var(--error);height:100%;width:{lose_pct:.0f}%;"></div>'
            f'</div>'
            f'<div class="vnum" style="font-size:12px;font-variant-numeric:tabular-nums;">{total} <span style="color:#4caf50;">{won}w</span> · <span style="color:var(--error);">{lose}l</span></div>'
            f'</div>'
        )

    rows = []
    for key, m in sorted_items[:max_rows]:
        is_esp_direct = m.get("_is_esp_direct", False)
        esp_origem = m.get("_esp_origem")
        if is_esp_direct:
            rname = f'<div class="rname esp" style="font-style:italic;font-weight:500;">{key}</div>'
        elif scope == "outside" and esp_origem and esp_origem != key:
            rname = f'<div class="rname outside" style="color:var(--verde-claro);">{key}</div>'
        else:
            rname = f'<div class="rname">{key}</div>'

        ativas_cell = _num_cell(m.get("ativas", 0))
        criadas_cell = _num_cell(m.get("criadas", 0))
        fechadas_cell = _fechadas_cell(m.get("won", 0), m.get("lose", 0))
        estagnadas_cell = _num_cell(m.get("estagnadas", 0))

        rows.append(
            f'<div class="rank-row">{rname}{ativas_cell}{criadas_cell}{fechadas_cell}{estagnadas_cell}</div>'
        )
    return "\n".join(rows)


def render_esp_block(esp_name: str, esp_idx: int, data: dict, ctx: dict, sub_template: str, assets: dict = None, dados_n5: dict = None, skill_dir: Path = None) -> str:
    """Render the 3-slide block for one specialist by filling sub_template."""
    n = ctx["_n_especialistas"]
    bloco_num = f"{2 + esp_idx + 1:02d}"  # 03 for esp 1, 04 for esp 2
    base_slide = 5 + 3 * esp_idx  # slide 6 for esp 1 (idx 0), slide 9 for esp 2 (idx 1)

    # FIX avatares (2026-05-14): localiza responsavel no Card e resolve circulo-id (foto ou iniciais).
    # Antes este caminho ficava com {{ESP_INICIAIS}} so com letras. Agora resolve foto via resolve_circulo()
    # com fallback automatico via slugify(nome) -> avatars.yaml.
    responsaveis_card = ((data.get("card", {}) or {}).get("apresentacao") or {}).get("responsaveis") or []
    resp_dict = next(
        (r for r in responsaveis_card if isinstance(r, dict) and (r.get("nome") or "").strip() == esp_name.strip()),
        {"nome": esp_name},
    )
    esp_avatar_html = resolve_circulo(resp_dict, skill_dir) if skill_dir else f'<span class="circulo-id">{iniciais(esp_name)}</span>'

    # FIX rotulo Analise (2026-05-14): N3 = "Analise por assessor" (default).
    # PJ2 sidecar sobrescreve para "Analise por canal" no seu proprio fluxo de render.
    apres = ((data.get("card", {}) or {}).get("apresentacao") or {})
    esp_analise_label = apres.get("esp_analise_label") or "Análise por assessor"
    # FIX (2026-05-14): "Direto" no eyebrow do Dashboard era confuso (usuario
    # disse "no direto nao deve ser PPI nem KPI"). Renomeado para "Especialista"
    # (default); Card pode sobrescrever via apresentacao.esp_dashboard_label.
    esp_dashboard_label = apres.get("esp_dashboard_label") or f"Especialista {((data.get('card', {}) or {}).get('metadata', {}) or {}).get('nivel', 'N3')}"

    placeholders = {
        "ESP_NOME": esp_name,
        "ESP_PRIMEIRO_NOME": primeiro_nome(esp_name),
        "ESP_INICIAIS": iniciais(esp_name),
        "ESP_AVATAR_HTML": esp_avatar_html,
        "ESP_ANALISE_LABEL": esp_analise_label,
        "ESP_DASHBOARD_LABEL": esp_dashboard_label,
        "ESP_BLOCO_NUM": bloco_num,
        "ESP_FNUM_DASH": f"{base_slide + 1:02d}",
        "ESP_FNUM_ANALISE": f"{base_slide + 2:02d}",
        "ESP_FNUM_PIPELINE": f"{base_slide + 3:02d}",
        "ESP_DASHBOARD_ROWS_KPI": _esp_dashboard_rows(esp_name, data, ctx, kpi_only=True),
        "ESP_DASHBOARD_ROWS_PPI": _esp_dashboard_rows(esp_name, data, ctx, kpi_only=False),
        "ESP_RISCOS": _esp_riscos(esp_name, data, dados_n5=dados_n5),
        "ESP_SQUAD_SIZE": str(_esp_squad_size(esp_name, data)),
        # R6 (2026-05-07): header section condicional — quando esp nao tem squad
        # fixo declarado (RE), exibir "SDRs com {esp}" em vez de "Squad X · 0 assessores".
        "ESP_RANK_HEADER_SQUAD": (
            f'<div class="rank-section squad">SDRs com {primeiro_nome(esp_name)}</div>'
            if _esp_squad_size(esp_name, data) == 0
            else f'<div class="rank-section squad">Squad {primeiro_nome(esp_name)} · {_esp_squad_size(esp_name, data)} assessores</div>'
        ),
        "ESP_RANK_HEADER_OUTSIDE": (
            ''  # quando esp nao tem squad, nao faz sentido "Fora da squad"
            if _esp_squad_size(esp_name, data) == 0
            else '<div class="rank-section outside">Fora da squad · referência</div>'
        ),
        "ESP_RANK_ROWS_SQUAD": _render_rank_rows_v2(
            _aggregate_assessor_volumes(esp_name, dados_n5 or {}, ctx, scope="squad",
                                          card=data["card"], current_month=_get_current_month_prefix(data)),
            scope="squad",
        ),
        # FIX rodada 7 issue 4 — scope outside_squad: assessores N5 do MESMO esp
        # fora da squad whitelist (ex: Ronaldo Dantas com deal vinculado a Douglas
        # mas que nao e da squad oficial). Substitui semantica antiga "outside"
        # (esps fantasmas N2). Card sem squad whitelist → vazio (legado).
        "ESP_RANK_ROWS_OUTSIDE": _render_rank_rows_v2(
            _aggregate_assessor_volumes(esp_name, dados_n5 or {}, ctx, scope="outside_squad",
                                          card=data["card"], current_month=_get_current_month_prefix(data)),
            scope="outside_squad",
        ),
        "ESP_SUMMARY_CARDS": _esp_summary_cards(esp_name, esp_idx, data, ctx, dados_n5 or {}),
        "ESP_KPI_TILES": _esp_kpi_tiles(esp_name, data),
        "ESP_FUNNEL_SVG": _esp_funnel_svg(esp_name, data, dados_n5 or {}),
        "ESP_DESTAQUE": _esp_destaque(esp_name, data, dados_n5 or {}),
        "ESP_ESTAGNACAO": _esp_estagnacao(esp_name, data, dados_n5 or {}),
        "ESP_PROJECAO_LABEL": _esp_proj_label(esp_name, data),
        "ESP_PROJECAO_NOTA": _esp_proj_nota(esp_name, data),
        # 2026-05-21: section unificada — gera open + titulo + bars + close OU string vazia
        # quando Card declara proj_periodos_por_indicador[ind]=[]. Substitui o wrap separado
        # que deixava o titulo "Volume" hardcoded vazar quando section deveria sumir.
        "ESP_PROJECAO_RECEITA_SECTION": _esp_proj_section(data, esp_name, _kpi_id(data, "receita") or "receita_mensal", "Receita"),
        "ESP_PROJECAO_VOLUME_SECTION":  _esp_proj_section(data, esp_name, _kpi_id(data, "volume") or "volume_mensal", "Volume"),
        # Legacy bars placeholders mantidos por compat (templates antigos) — vazio quando section unificada usada
        "ESP_PROJECAO_RECEITA_BARS": "",
        "ESP_PROJECAO_VOLUME_BARS": "",
    }

    out = sub_template
    for k, v in placeholders.items():
        out = out.replace("{{" + k + "}}", v)
    # Also fill outer ctx placeholders that appear inside the sub-template
    for k, v in ctx.items():
        if isinstance(v, str):
            out = out.replace("{{" + k + "}}", v)
    # Fill assets too (logo etc. embedded inside esp slides)
    if assets:
        for k, v in assets.items():
            out = out.replace("{{" + k + "}}", v)
    return out


def _esp_dashboard_rows(esp: str, data: dict, ctx: dict, kpi_only: bool) -> str:
    """Render dt-row entries para Dashboard (slide N+0 por esp).
    Estrutura template: dt-table > dt-head (6 cols) > dt-section > dt-row.
    Cada row tem 6 children: Indicador / Meta / Real / Desvio / Δ vs S{prev} / Stat (emoji).
    Itera sobre matrix_rows resolvidas (mesma SoT do Slide 3 — N-parametrico)."""
    matrix_rows = _resolve_matrix_rows(data, ctx)
    # R5-3 (2026-05-07): respeitar slide_visibility — Card pode declarar
    # `slide_visibility: ["fechamento"]` para suprimir view do Dashboard por esp.
    # FIX (2026-05-14) Bug 4: views com `color_inherit_from_view` (caso tipico:
    # "Oport. Estagnadas (qty)" herda cor de "% ativas") sao sempre uteis no
    # Dashboard porque mostram a contagem absoluta que a % esconde. Auto-incluir
    # estas views mesmo quando o Card declara slide_visibility sem "dashboard".
    matrix_rows = [
        mr for mr in matrix_rows
        if "dashboard" in (mr.get("slide_visibility") or ["dashboard"])
           or mr.get("color_inherit_from_view")
    ]
    n_esps = ctx.get("_n_especialistas", 0)
    esp_list_full = ctx.get("_esp_list", []) or []
    rows = []
    for mr in matrix_rows:
        if kpi_only != mr["is_kpi"]:
            continue
        n2_data = _resolve_n2(mr, esp, data, n_esps=n_esps, esp_list=esp_list_full)
        if n2_data is None:
            # Render empty row mantendo layout (sem dados para esp)
            rows.append(_dashboard_empty_row(mr))
            continue
        unidade = mr.get("unidade", "count")
        meta_v = n2_data.get("meta")
        real = n2_data.get("realizado")
        # FIX 2026-05-14 (Bug 1.5 — unit clash ratio): Card YAML usa fracao decimal
        # (0.25) enquanto analyst v1.1 emite valor ja em pct (30.43). Normalizar
        # ambos para pct antes do calculo de gap/desvio. Mesma heuristica usada em
        # _fmt_value (multiplica ×100 quando |v| <= 1.0).
        if unidade == "ratio":
            if isinstance(meta_v, (int, float)) and abs(meta_v) <= 1.0:
                meta_v = meta_v * 100
            if isinstance(real, (int, float)) and abs(real) <= 1.0:
                real = real * 100
        desvio_str = "—"
        pct_str = ""
        cls = "mute"
        direction = mr.get("direction", "maior_melhor")
        # FIX rodada 5 — color_inherit_from_view: cor herda do irmao na matrix (ex: Estagnadas qty)
        inherit_from = mr.get("color_inherit_from_view")
        if inherit_from:
            sibling = next((m for m in matrix_rows if m["label"] == inherit_from), None)
            if sibling:
                sib_n2 = _resolve_n2(sibling, esp, data, n_esps=n_esps, esp_list=esp_list_full) or {}
                sib_real, sib_meta = sib_n2.get("realizado"), sib_n2.get("meta")
                if isinstance(sib_real, (int, float)) and isinstance(sib_meta, (int, float)) and sib_meta != 0:
                    sib_dir = sibling.get("direction", "maior_melhor")
                    if sib_dir == "menor_melhor":
                        pct_sib = (sib_meta / max(sib_real, 1e-9)) * 100
                    else:
                        pct_sib = (sib_real / sib_meta) * 100
                    cls = _class_3tier(pct_sib, sib_dir)
            desvio_str = ""  # sem meta = sem desvio
        elif isinstance(real, (int, float)) and isinstance(meta_v, (int, float)) and meta_v == 0 and direction == "menor_melhor":
            # FIX #14 (2026-05-14): zero-target rule (ex: oportunidades_sem_atividade_planejada_funil).
            # Meta=0 + menor_melhor: real=0 -> verde 100%; real>=1 -> vermelho 0%. Formula
            # padrao (meta/max(real,1)) produz 0% mesmo com real=0 — matematicamente quebrado.
            # Mesma regra special-case que validate-painel.py e consolidating-wbr/SKILL.md aplicam.
            if real == 0:
                pct = 100.0
                cls = "good"
                desvio_str = "no alvo"
                pct_str = '<span class="pct">(0)</span>'
            else:
                pct = 0.0
                cls = "bad"
                gap = int(real)
                desvio_str = f"+{gap}"
                pct_str = f'<span class="pct">(meta 0)</span>'
        elif isinstance(real, (int, float)) and isinstance(meta_v, (int, float)) and meta_v != 0:
            gap = real - meta_v
            if direction == "menor_melhor":
                pct = (meta_v / max(real, 1e-9)) * 100
                # Para menor_melhor, % desvio = realizado/meta - 100 (negativo = bom)
                pct_desvio = ((real / meta_v) - 1) * 100
            else:
                pct = (real / meta_v) * 100
                pct_desvio = pct - 100
            cls = _class_3tier(pct, direction)
            sign = "+" if gap >= 0 else ""
            desvio_str = f"{sign}{_fmt_value(gap, unidade)}"
            # FIX rodada 6 issue 10 — desvio + % entre parenteses (padrao SEG WL S18)
            sign_pct = "+" if pct_desvio >= 0 else ""
            pct_str = f'<span class="pct">({sign_pct}{pct_desvio:.0f}%)</span>'.replace(".", ",")
        elif isinstance(real, (int, float)):
            desvio_str = "ref"
        delta = _calc_delta_n2(mr, esp, data, ctx)
        # FIX img12 — sub_info inline na coluna Real (compacto para Dashboard)
        sub_tpl = mr.get("n2_sub_info_template")
        sub_html = ""
        if sub_tpl:
            ind_entry = data["wbr"].get("indicadores", {}).get(mr["source_indicator"], {}) or {}
            n2_dict = ind_entry.get("n2") or ind_entry.get("por_especialista") or {}
            e_entry = n2_dict.get(esp, {}) or {}
            sub_text = render_sub_info(sub_tpl, e_entry) if e_entry else ""
            if sub_text:
                sub_html = f'<div class="sub-info" style="font-size:10px;color:var(--verde-claro);">{sub_text}</div>'

        # S1-A2 (2026-05-15) feedback: aplicar enriquecimento + cor proporcional
        # no Dashboard por esp tambem (nao so na matriz consolidada).
        # (a) "Oport. Estagnadas (qty)": display "qty (R$ vol_compact)"
        # (b) "Sem Ativ. ou Atras. CRM": display "qty (X%)" + cor proporcional
        #     (0=verde, 0-20%=amarelo, 21%+=vermelho).
        _lbl_lc_dash = (mr.get("label") or "").lower()
        real_str = _fmt_value(real, unidade)
        if unidade == "count" and "estagnadas" in _lbl_lc_dash and "(qty)" in _lbl_lc_dash:
            vol_estag = _vol_estagnado_for_esp(data, esp)
            if vol_estag and vol_estag > 0:
                real_str = f"{real_str} ({fmt_brl(vol_estag, compact=True)})"
        elif unidade == "count" and ("sem ativ" in _lbl_lc_dash or "sem atividade" in _lbl_lc_dash):
            pct_sa = _pct_sem_atividade_for_esp(data, esp)
            if isinstance(real, (int, float)):
                if real == 0:
                    cls = "good"
                elif pct_sa <= 20:
                    cls = "warn"
                else:
                    cls = "bad"
                if pct_sa > 0:
                    real_str = f"{real_str} ({pct_sa:.0f}%)"
                # Desvio coluna fica vazio (regra proporcional, sem meta numerica)
                desvio_str = ""
                pct_str = ""

        # FIX rodada 6 issue 10 — cor TEXTO em .real (substitui dot da coluna .stat).
        # Coluna .stat removida do template (5 cols). Desvio com qtd + %.
        rows.append(
            f'<div class="dt-row">'
            f'<div class="ind">{mr["label"]}</div>'
            f'<div class="meta">{_fmt_value(meta_v, unidade)}</div>'
            f'<div class="real {cls}">{real_str}{sub_html}</div>'
            f'<div class="desvio {cls}">{desvio_str}{pct_str}</div>'
            f'<div class="delta">{delta}</div>'
            f'</div>'
        )
    if not rows:
        return '<div class="dt-row empty" style="text-align:center;color:var(--verde-claro);font-style:italic;padding:14px;">Sem indicadores nesta categoria.</div>'
    return "\n".join(rows)


def _dashboard_empty_row(mr: dict) -> str:
    # FIX rodada 6 issue 10 — 5 cols (sem .stat)
    return (
        f'<div class="dt-row">'
        f'<div class="ind">{mr["label"]}</div>'
        f'<div class="meta">—</div>'
        f'<div class="real mute">—</div>'
        f'<div class="desvio mute">—</div>'
        f'<div class="delta"></div>'
        f'</div>'
    )


def _fmt_value(v, unidade: str) -> str:
    """Formatador unificado por unidade (chave da abordagem N-parametrica)."""
    if v is None:
        return "—"
    if unidade == "BRL":
        return fmt_brl(v, compact=True)
    if unidade == "ratio":
        # FIX 2026-05-14 (Bug 1 — Taxa Conversao 3043%): analyst v1.1 emite valores
        # com unit="ratio" mas ja em pct (34.43 = 34,4%, nao 0.3443). So multiplicar
        # ×100 quando o valor for <= 1.0 (fracao decimal verdadeira).
        try:
            fv = float(v)
            if abs(fv) <= 1.0:
                fv = fv * 100
            return fmt_pct(fv, 1)
        except (TypeError, ValueError):
            return str(v)
    if unidade == "pct":
        return fmt_pct(v, 1)
    if unidade in ("count", "qty", None):
        return fmt_int(v)
    return str(v)


def _class_3tier(pct: float, direction: str = "maior_melhor",
                 t_warn: float = 70, t_good: float = 100) -> str:
    """3-tier classification para .good/.warn/.bad/.mute. N-parametrico via thresholds."""
    if pct is None:
        return "mute"
    if direction == "menor_melhor":
        # Para menor_melhor: realizado/meta < 1 e bom (cap 200%)
        # Inverte: pct = meta/realizado * 100
        if pct >= t_good:
            return "good"
        if pct >= t_warn:
            return "warn"
        return "bad"
    # maior_melhor (default)
    if pct >= t_good:
        return "good"
    if pct >= t_warn:
        return "warn"
    return "bad"


def _calc_delta_n2(mr: dict, esp: str, data: dict, ctx: dict) -> str:
    """Wrapper para _calc_delta usando matrix_row (N-parametrico).
    FIX (2026-05-14): passa mr["unidade"] (view-level) e mr["direction"] para
    _calc_delta. Antes _calc_delta inferia unit do cur_ind WBR; quando source
    indicator era derived (_pct_ativas), unit virava 'pct' mesmo na view (qty)
    do mesmo indicador — '8 pp' no qty row. View-level unidade e a fonte certa."""
    if not data.get("prev_wbr"):
        return ""
    return _calc_delta(
        esp, mr["source_indicator"], data, ctx,
        sub_field=mr.get("n2_value_field"),
        view_unidade=mr.get("unidade"),
        view_direction=mr.get("direction"),
        view_aspect=mr.get("aspect"),
        view_label=mr.get("label"),
        n2_compute=mr.get("n2_compute"),
    )


def _calc_delta(esp: str, ind_id: str, data: dict, ctx: dict, sub_field: str = None,
                view_unidade: str = None, view_direction: str = None,
                view_aspect: str = None, view_label: str = None,
                n2_compute: str = None) -> str:
    """Compute Δ vs prev cycle for cell rendering. N-parametrico via sub_field opcional.

    FIX img7 — Quando prev vem de parser .md, keys do prev sao slug(label) e nao ind_id.
    Lookup por: ind_id direto > label normalizado do indicator atual.

    FIX 2026-05-14 (Issue 3): adicionado Fallback 4 aspect-aware para schemas
    v1.0 aspect-split (prev = "..._re_qty"/"..._re_volume") vs v1.1 single-id
    (cur = "..._funil_seg" com qty/vol como subfields).
    """
    prev = data.get("prev_wbr")
    if not prev:
        return ""
    prev_indicadores = prev.get("indicadores", {})
    cur_ind = data["wbr"].get("indicadores", {}).get(ind_id, {})
    # Tentar match direto por ind_id
    prev_ind = prev_indicadores.get(ind_id, {})
    # Fallback 1: slug do label do indicador atual
    if not prev_ind and cur_ind.get("label"):
        prev_ind = prev_indicadores.get(slugify(cur_ind["label"]), {})
    # Fallback 2: procurar por key cuja label bata exato
    if not prev_ind:
        cur_label_slug = slugify(cur_ind.get("label", ind_id))
        for k, v in prev_indicadores.items():
            if slugify(v.get("label", k)) == cur_label_slug:
                prev_ind = v
                break
    # Fallback 3: match parcial pelas 2 primeiras palavras do slug
    # (ex: 'volume_consorcio_mensal' vs 'volume_consorcio')
    if not prev_ind:
        cur_slug = slugify(cur_ind.get("label", ind_id))
        cur_words = cur_slug.split("_")[:2]
        if len(cur_words) >= 2:
            cur_short = "_".join(cur_words)
            for k, v in prev_indicadores.items():
                k_words = k.split("_")[:2]
                if len(k_words) >= 2 and "_".join(k_words) == cur_short:
                    prev_ind = v
                    break
    # Fallback 3.5 (FIX 2026-05-14): non-aspect lookup com sufixos de subnivel
    # ou consolidacao. Cobre o caso comum: cur WBR v1.1 usa ind_id base
    # (`receita_seguros_mensal`), prev WBR consolidado usa sufixo do subnivel
    # (`receita_seguros_mensal_wl`) ou de nivel (`taxa_conversao_funil_seg_n1`).
    # Aplica para indicadores SEM aspect-split (KPIs e PPIs single-value).
    if not prev_ind:
        cur_subnivel = (data.get("card", {}).get("metadata") or {}).get("subnivel")
        non_aspect_tries = []
        if cur_subnivel:
            non_aspect_tries.append(f"{ind_id}_{cur_subnivel}")
        non_aspect_tries.append(f"{ind_id}_n1")
        # Variante derivada de label slug
        cur_slug = slugify(cur_ind.get("label", ind_id))
        if cur_subnivel and cur_slug != ind_id:
            non_aspect_tries.append(f"{cur_slug}_{cur_subnivel}")
        non_aspect_tries.append(f"{cur_slug}_n1")
        for cand in non_aspect_tries:
            if cand in prev_indicadores:
                prev_ind = prev_indicadores[cand]
                break

    # Fallback 4 (FIX 2026-05-14): aspect-aware lookup para schemas v1.0
    # aspect-split. ind_id atual e base (sem aspect suffix); prev keys tem
    # sufixo `_{subnivel}_{aspect}` ou `_{aspect}`. Inferir aspect do sub_field
    # ou da unidade da view.
    if not prev_ind:
        # Inferir aspect candidato do sub_field
        sub_l = (sub_field or "").lower()
        candidates_aspect = []
        if "qty" in sub_l or "estagn" in sub_l:
            candidates_aspect.append("qty")
        if "vol" in sub_l:
            candidates_aspect.append("volume")
        if "pct" in sub_l:
            candidates_aspect.append("pct_ativas")
        # Subnivel do Card atual
        cur_subnivel = (data.get("card", {}).get("metadata") or {}).get("subnivel")
        for asp in candidates_aspect:
            # Tentar ind_id + subnivel + aspect (v1.0 typical: oport_..._funil_seg_re_qty)
            tries = []
            if cur_subnivel:
                tries.append(f"{ind_id}_{cur_subnivel}_{asp}")
            tries.append(f"{ind_id}_{asp}")
            # Variante derivada de label slug do indicator
            cur_slug = slugify(cur_ind.get("label", ind_id))
            if cur_subnivel:
                tries.append(f"{cur_slug}_{cur_subnivel}_{asp}")
            for cand in tries:
                if cand in prev_indicadores:
                    prev_ind = prev_indicadores[cand]
                    break
            if prev_ind:
                break
    # Fallback 5 (FIX 2026-05-14): para Ticket Medio Pipeline composite,
    # computar prev como vol_prev / qty_prev (mesma logica do cur).
    # Detect via view_aspect (preferido), view_label, ou n2_compute pattern.
    is_ticket_composite = (
        view_aspect == "ticket_medio"
        or ("ticket" in (view_label or "").lower() and "pipeline" in (view_label or "").lower())
        or (n2_compute and "/" in n2_compute and any(t in n2_compute.lower() for t in ("vol", "volume")))
        or ("ticket" in (cur_ind.get("label") or "").lower() and "pipeline" in (cur_ind.get("label") or "").lower())
    )
    if not prev_ind and is_ticket_composite:
        cur_subnivel = (data.get("card", {}).get("metadata") or {}).get("subnivel")
        qty_keys = ([f"{ind_id}_{cur_subnivel}_qty", f"{ind_id}_qty"] if cur_subnivel
                    else [f"{ind_id}_qty"])
        vol_keys = ([f"{ind_id}_{cur_subnivel}_volume", f"{ind_id}_volume"] if cur_subnivel
                    else [f"{ind_id}_volume"])
        qty_e = next((prev_indicadores[k] for k in qty_keys if k in prev_indicadores), None)
        vol_e = next((prev_indicadores[k] for k in vol_keys if k in prev_indicadores), None)
        if qty_e and vol_e:
            # Inject synthetic prev_ind with n2 ticket = vol / qty per esp
            synthetic_n2 = {}
            qty_n2 = qty_e.get("n2") or {}
            vol_n2 = vol_e.get("n2") or {}
            for esp_name in set(list(qty_n2.keys()) + list(vol_n2.keys())):
                q = (qty_n2.get(esp_name) or {}).get("realizado")
                v = (vol_n2.get(esp_name) or {}).get("realizado")
                if isinstance(q, (int, float)) and q > 0 and isinstance(v, (int, float)):
                    synthetic_n2[esp_name] = {"realizado": v / q}
            q_n1 = qty_e.get("realizado")
            v_n1 = vol_e.get("realizado")
            n1_ticket = (v_n1 / q_n1) if (isinstance(q_n1, (int, float)) and q_n1 > 0
                                            and isinstance(v_n1, (int, float))) else None
            prev_ind = {"realizado": n1_ticket, "n2": synthetic_n2, "_synthetic_ticket": True}
    if not prev_ind:
        return ""
    cur_ind = data["wbr"].get("indicadores", {}).get(ind_id, {})
    cur_n2 = (cur_ind.get("n2") or cur_ind.get("por_especialista") or {}).get(esp, {})
    prev_n2 = (prev_ind.get("n2") or prev_ind.get("por_especialista") or {}).get(esp, {})
    # FIX #4 (2026-05-14): PPIs vinham com Delta vazio porque diferentes versoes do schema
    # do WBR usam chaves distintas para o valor N2 (realizado_mtd no v1.0, realizado no v1.1,
    # qty/vol em PPIs de funil, taxa/pct em conversao). Ampliamos o fallback chain.
    _VALUE_KEYS = ("realizado_mtd", "realizado", "valor", "qty", "vol", "volume", "taxa", "pct", "pct_atingimento")
    # FIX (2026-05-14): cur_v tambem precisa de fallback chain (era so prev_v).
    # Schema v1.1 emite 'realizado' onde Card declara n2_value_field='qty'. Sem fallback,
    # cur_v=None -> Delta vazio para todos os PPIs (Vol Ativas qty, % estagnadas, etc.).
    # Helper smart com family-aware: pede 'qty' aceita 'realizado'; pede 'volume' aceita 'vol'.
    def _smart_n2_value(n2_entry: dict, sub: str = None):
        if sub:
            v = _dig(n2_entry, sub)
            if v is not None:
                return v
            # Family fallback do sub_field
            family = _FIELD_FAMILY_FALLBACKS.get(sub) or []
            for f in family:
                v = _dig(n2_entry, f)
                if v is not None:
                    return v
        # Generic fallback chain
        for k in _VALUE_KEYS:
            if k in n2_entry and n2_entry[k] is not None:
                return n2_entry[k]
        return None
    if sub_field:
        cur_v = _smart_n2_value(cur_n2, sub_field)
        prev_v = _smart_n2_value(prev_n2, sub_field)
    else:
        cur_v = _smart_n2_value(cur_n2)
        prev_v = _smart_n2_value(prev_n2)
    # FIX 2026-05-14 (Issue 3): para Ticket Medio Pipeline composite, cur_v deve
    # ser computado como vol/qty da entry corrente (n2 tem {qty, vol}), nao
    # cair em _smart_n2_value que pega "qty" (= 13) ao inves do ticket (= 328).
    # FIX 2026-05-20: prev_v simetrico (antes ficava como _smart_n2_value(prev_n2)
    # = realizado = qty, gerando delta = ticket_atual - qty_anterior = todo o
    # ticket atual). Aplicar mesma logica de recomputo para prev_v.
    if is_ticket_composite:
        cur_q = cur_n2.get("qty") or cur_n2.get("realizado_qty") or cur_n2.get("realizado")
        cur_vol = cur_n2.get("vol") or cur_n2.get("volume") or cur_n2.get("vol_total") or cur_n2.get("volume_total")
        if isinstance(cur_q, (int, float)) and cur_q > 0 and isinstance(cur_vol, (int, float)):
            cur_v = cur_vol / cur_q
        prev_q = prev_n2.get("qty") or prev_n2.get("realizado_qty") or prev_n2.get("realizado")
        prev_vol = prev_n2.get("vol") or prev_n2.get("volume") or prev_n2.get("vol_total") or prev_n2.get("volume_total")
        if isinstance(prev_q, (int, float)) and prev_q > 0 and isinstance(prev_vol, (int, float)):
            prev_v = prev_vol / prev_q
    # Fallback final: N1 quando N2 indisponivel no prev (schema legado pode nao ter n2 por esp)
    if prev_v is None and not prev_n2:
        prev_v = next((prev_ind[k] for k in _VALUE_KEYS if k in prev_ind and prev_ind[k] is not None), None)
    if cur_v is None or prev_v is None:
        return ""
    try:
        delta = float(cur_v) - float(prev_v)
    except (TypeError, ValueError):
        return ""
    if abs(delta) < 1e-6:
        return '<span style="color:#424135;">→</span> <span style="color:#424135;">0</span>'
    arrow = "↑" if delta > 0 else "↓"
    # FIX (2026-05-14): direction lookup robusto. Antes lia apenas
    # card.metas_ppi[ind_id].direction — falhava para indicadores derivados
    # (ex: oportunidades_estagnadas_funil_pct_ativas nao existe em metas_ppi;
    # parent e oportunidades_estagnadas_funil). Resultado: estagnadas subindo
    # ficava VERDE (default maior_melhor) em vez de VERMELHO (menor_melhor).
    # Cascade: matrix_row > cur_ind WBR > card.metas_ppi(ind_id) > card.metas_ppi(parent).
    metas_ppi = data["card"].get("metas_ppi", {})
    parent_id = ind_id.replace("_pct_ativas", "").replace("_qty", "").replace("_volume", "")
    # FIX (2026-05-14): direction lookup robusto. view_direction (matrix_row) tem
    # prioridade sobre cur_ind/metas_ppi.
    direction = (
        view_direction
        or cur_ind.get("direction")
        or metas_ppi.get(ind_id, {}).get("direction")
        or (metas_ppi.get(parent_id, {}).get("direction") if parent_id != ind_id else None)
        or "maior_melhor"
    )
    if direction == "maior_melhor":
        color = "#4CAF50" if delta > 0 else "#E40014"
    else:
        color = "#E40014" if delta > 0 else "#4CAF50"
    # FIX (2026-05-14): unidade lookup view-level primeiro (matrix_row.unidade),
    # depois cur_ind 'unit'/'unidade'. Antes derived indicators (e.g. _pct_ativas
    # com unit:pct) infectavam view-qty -> "8 pp" no qty row de Estagnadas.
    unidade = (
        view_unidade
        or cur_ind.get("unidade")
        or cur_ind.get("unit")
        or "count"
    ).lower()
    if unidade == "brl":
        val_str = fmt_brl(abs(delta), compact=True)
    elif unidade in ("ratio", "pct", "percent", "percentual"):
        val_str = f"{abs(delta):.1f} pp".replace(".", ",")
    else:
        val_str = fmt_int(abs(delta))
    return f'<span style="color:#424135;">{arrow}</span> <span style="color:{color};">{val_str}</span>'


def _esp_riscos(esp: str, data: dict, dados_n5: dict = None, max_items: int = 6) -> str:
    """Auto-fill Riscos card (Slide N+0 Dashboard).

    PRIMARY PATH (Item 3 follow-up Seguros-WL 2026-05-20, schema v1.3 2026-05-21):
      Consumir `analise_por_responsavel[esp].riscos` + `alertas` diretamente do
      canonical JSON quando disponivel. Renderiza descricao + severidade direto
      do payload estruturado emitido pelo analyst E6. Bot Telegram consome o
      mesmo bloco — paridade visual e textual.

    FALLBACK PATH — heuristica A-H (preserva compatibilidade com canonical v1.2):
      A. Concentracao de receita: top 1-2 assessores >= 40% do N2
      B. Cobertura: % squad assessores zerados (sem deal/won)
      C. Estagnacao: top stage estagnado vol + qty + aging
      D. Mega-prospects: top deals N5 sem assessor mapeado
      E. Anomalias do WBR mencionando esp (heuristica anterior)
      F. Cluster sem efeito visivel mencionando esp
      G. Indicadores N2 vermelho com gap especifico
      H. Acoes criticas com owner=esp

    Quando canonical tem analise_por_responsavel[esp] com >=3 itens: usa SOMENTE
    primary path (config-as-code via analyst). Quando <3 itens: augmenta com
    heuristica para preencher max_items.

    N-parametrico — funciona para qualquer vertical/esp.
    """
    wbr = data["wbr"]
    items = []
    esp_lc = esp.lower()
    primeiro = primeiro_nome(esp).lower()
    sev_order = {"alta": 0, "media": 1, "informativa": 2}

    # ─────────────────────────────────────────────────────────────────────
    # PRIMARY PATH — analise_por_responsavel[esp] (canonical v1.3+)
    # ─────────────────────────────────────────────────────────────────────
    analise_por_resp = wbr.get("analise_por_responsavel") or {}
    apr_entry = analise_por_resp.get(esp) or {}
    primary_items: list[tuple[str, str, str]] = []
    if apr_entry:
        for risco in apr_entry.get("riscos") or []:
            if not isinstance(risco, dict):
                continue
            sev = (risco.get("severidade") or "media").lower()
            desc = risco.get("descricao") or ""
            ind_orig = risco.get("indicador_origem") or ""
            cross = risco.get("cross_indicators") or []
            cross_txt = ""
            if cross:
                cross_names = [c.get("indicador", "") for c in cross[:3] if isinstance(c, dict)]
                cross_txt = "vs " + ", ".join(n.split("_funil")[0] for n in cross_names if n)
            ctx = f"{ind_orig}{(' · ' + cross_txt) if cross_txt else ''}"
            primary_items.append((sev, desc[:200], ctx))
        for alerta in apr_entry.get("alertas") or []:
            if not isinstance(alerta, dict):
                continue
            desc = alerta.get("descricao") or ""
            acao = alerta.get("acao_imediata") or alerta.get("indicador_origem") or ""
            primary_items.append(("alta", f"{desc}", acao[:120]))

    # Se primary path retornou >=3 itens, renderiza DIRETO (config-as-code via
    # analyst, paridade com bot Telegram). Heuristica A-H abaixo eh apenas
    # fallback para canonical v1.2 ou v1.3 com bloco esparso.
    if len(primary_items) >= 3:
        # Dedup + render compartilhado com path heuristico — pula bloco A-H
        deduped_primary = primary_items[:max_items]
        sev_color_p = {"alta": "var(--error)", "media": "#d18000", "baixa": "var(--verde-claro)",
                       "informativa": "var(--verde-claro)"}
        out_p = []
        for sev, desc, ctx in deduped_primary:
            color = sev_color_p.get(sev, "var(--verde-claro)")
            ctx_html = ""  # 2026-06-12: subtexto nao-negrito (ctx/linhagem) removido dos cards de risco (Img 2)
            out_p.append(
                f'<div class="risk-item" style="border-left:3px solid {color};padding:6px 10px;margin-bottom:6px;font-size:21px;line-height:1.4;">'
                f'<strong>{desc}</strong>{ctx_html}'
                f'</div>'
            )
        return "\n".join(out_p)

    # Augmenta com primary items quando <3 — heuristica complementa
    items.extend(primary_items)
    # R6 (2026-05-07): suppress filter via Card.apresentacao.suppress_in_ritual.riscos
    # Permite Card declarar keywords que filtram items dos Riscos por esp.
    suppress_kws_riscos = (
        (data.get("card", {}).get("apresentacao") or {})
        .get("suppress_in_ritual", {}) or {}
    ).get("riscos") or []
    suppress_kws_riscos_lc = [str(k).lower() for k in suppress_kws_riscos]

    def _is_suppressed(desc: str) -> bool:
        if not suppress_kws_riscos_lc or not desc:
            return False
        desc_lc = str(desc).lower()
        return any(kw in desc_lc for kw in suppress_kws_riscos_lc)

    # === A. CONCENTRACAO DE RECEITA — top assessor >=40% N2 (mes corrente, alias aplicado) ===
    card = data["card"]
    current_month = _get_current_month_prefix(data)
    # FIX rodada 7 issue 6 — squad whitelist: outsiders nao contam para concentracao
    # do squad (sao referencia, nao ponto unico de falha)
    squad_whitelist_local = _get_squad_whitelist(esp, card)
    squad_norms_local = {_normalize_assessor_name(a) for a in squad_whitelist_local}
    if dados_n5:
        receita_assessores = {}
        for entry in dados_n5.get("indicadores", []):
            ind_id = entry.get("indicator_id", "")
            if not ind_id.startswith("receita"):
                continue
            for row in entry.get("data", []):
                # FIX rodada 5 — Receita: filtrar mes corrente (era acumulando ALL meses)
                if current_month and not _row_in_current_month(row, current_month):
                    continue
                if row.get("especialista") != esp:
                    continue
                if row.get("nivel") == "N5-Assessor":
                    a_raw = row.get("assessor")
                    # FIX rodada 7 — assessor = esp name → esp_direct (override declara assim)
                    is_esp_self = (a_raw and isinstance(a_raw, str)
                                   and _normalize_assessor_name(a_raw) == _normalize_assessor_name(esp))
                    if _is_esp_direct(a_raw) or is_esp_self:
                        a_name = f"{esp} (esp)"
                    else:
                        a_name = _resolve_assessor_alias(a_raw, card)
                        # FIX rodada 7 — pula outsider (nao e da squad oficial)
                        if squad_norms_local and not _assessor_in_squad(a_name, squad_norms_local):
                            continue
                    real = row.get("realizado") or 0
                    if real > 0:
                        receita_assessores[a_name] = receita_assessores.get(a_name, 0) + real
        # FIX rodada 7 — receita_n2_total via SOMA dos N5 do squad oficial + esp_direct
        # (consistente com override aplicado a N5_by_esp). Nao usa N2 do dados_n5
        # que pode estar stale relativo ao override.
        receita_n2_total = sum(receita_assessores.values())
        if receita_n2_total > 0 and receita_assessores:
            top1 = max(receita_assessores.items(), key=lambda x: x[1])
            pct_top1 = (top1[1] / receita_n2_total) * 100
            # Cap em 100% — evita 478% bug em caso de discrepancia entre soma N5 e N2
            pct_top1 = min(100, pct_top1)
            if pct_top1 >= 40:
                items.append(("alta",
                              f"{top1[0]} = {pct_top1:.0f}% receita N2 sozinho ({fmt_brl(top1[1], compact=True)})",
                              "Ponto unico de falha — sem ele, gap dispara"))

    # === B. COBERTURA — % squad assessores zerados em ATIVAS (alias aplicado) ===
    # FIX rodada 7.5 — dedupe por SLUG (evita "Vinicius"/"Vinícius" e "Waleska "/"Waleska"
    # serem duas entries separadas no set). Garante zerados/total = 12 fixo Douglas.
    if dados_n5:
        squad_assessores_slug = set()
        ativos_set_slug = set()
        for entry in dados_n5.get("indicadores", []):
            if not (entry.get("indicator_id") or "").startswith("oportunidades_ativas_funil"):
                continue
            for row in entry.get("data", []):
                if row.get("especialista") != esp or row.get("nivel") != "N5-Assessor":
                    continue
                if row.get("estagio"):
                    continue  # snapshot only
                a_raw = row.get("assessor")
                if _is_esp_direct(a_raw):
                    continue
                a_name = _resolve_assessor_alias(a_raw, card)
                a_slug = _normalize_assessor_name(a_name)
                # FIX rodada 7 — limita squad whitelist (outsiders viram referencia em outro card)
                if squad_norms_local and a_slug not in squad_norms_local:
                    continue
                squad_assessores_slug.add(a_slug)
                if (row.get("quantidade") or 0) > 0:
                    ativos_set_slug.add(a_slug)
        # Adiciona squad whitelist members nao vistos (zero-fill cobertura)
        if squad_whitelist_local:
            for offic in squad_whitelist_local:
                squad_assessores_slug.add(_normalize_assessor_name(offic))
        if squad_assessores_slug:
            zerados = squad_assessores_slug - ativos_set_slug
            pct_zerados = (len(zerados) / len(squad_assessores_slug)) * 100
            if pct_zerados >= 30:
                items.append(("media" if pct_zerados < 50 else "alta",
                              f"{pct_zerados:.0f}% assessores zerados ({len(zerados)}/{len(squad_assessores_slug)})",
                              "Carteiras inativas — risco de perder mes"))

    # === C. ESTAGNACAO — top stage estagnado ===
    estag_pct = wbr.get("indicadores", {}).get("oportunidades_estagnadas_funil_pct_ativas", {})
    e_estag = (estag_pct.get("por_especialista", {}) or {}).get(esp, {})
    if e_estag:
        qty_est = e_estag.get("qtd_estagnados", 0)
        vol_est = e_estag.get("volume_estagnado", 0)
        tempo = e_estag.get("tempo_medio_dias", 0)
        if qty_est >= 5:
            items.append(("alta",
                          f"{qty_est} deals estagnados {fmt_brl(vol_est, compact=True)} aging {int(tempo)}d",
                          "Pipeline travado — limpeza pendente"))

    # === D. MEGA-PROSPECTS sem assessor (deals esp_direct grandes) ===
    if dados_n5:
        mega = []
        for entry in dados_n5.get("indicadores", []):
            if not (entry.get("indicator_id") or "").startswith("oportunidades_ativas_funil"):
                continue
            for row in entry.get("data", []):
                if row.get("especialista") != esp or row.get("nivel") != "N5-Assessor":
                    continue
                if not _is_esp_direct(row.get("assessor")):
                    continue
                vol = row.get("volume") or 0
                qty = row.get("quantidade") or 0
                if vol >= 10_000_000:
                    mega.append({"qty": qty, "vol": vol})
        if mega:
            total_qty = sum(m["qty"] for m in mega)
            total_vol = sum(m["vol"] for m in mega)
            items.append(("alta",
                          f"{total_qty} mega-prospects {fmt_brl(total_vol, compact=True)} sem assessor mapeado",
                          "Decisao binaria WIN/LOSE/RENEGOCIAR"))

    # === E. Anomalias mencionando esp (heuristica original) ===
    anomalias = sorted(
        wbr.get("anomalias", []),
        key=lambda x: sev_order.get(x.get("severidade", "media"), 1),
    )
    for a in anomalias:
        desc = (a.get("descricao") or "")
        acao = (a.get("acao") or "")
        if esp_lc in desc.lower() or primeiro in desc.lower():
            # R6: suppress via Card.apresentacao.suppress_in_ritual.riscos
            if _is_suppressed(desc) or _is_suppressed(acao):
                continue
            items.append((a.get("severidade", "media"), desc[:200], acao))

    # 2. Acoes criticas com owner = esp
    for a in wbr.get("acoes", {}).get("criticas", []):
        if (a.get("owner") or "").lower() == esp_lc:
            titulo_safe = a.get('titulo', '')[:100]
            if _is_suppressed(titulo_safe):
                continue
            items.append(("alta",
                          f"Acao critica: {titulo_safe} ({a.get('aging', '')}d)",
                          a.get("indicador", "")))

    # 3. Acoes atrasadas com owner = esp
    for a in wbr.get("acoes", {}).get("atrasadas", []):
        if (a.get("owner") or "").lower() == esp_lc:
            titulo_safe = a.get('titulo', '')[:100]
            if _is_suppressed(titulo_safe):
                continue
            items.append(("media",
                          f"Atrasada: {titulo_safe}",
                          f"prazo {a.get('prazo', '')}"))

    # 4. Recomendacoes com owner contendo esp (priorizar alta)
    for r in wbr.get("recomendacoes", []):
        if esp_lc in (r.get("owner") or "").lower():
            sev = "alta" if r.get("prioridade") == "alta" else "media"
            texto = r.get("texto", "")[:160]
            # R6: suppress via Card
            if _is_suppressed(texto):
                continue
            items.append((sev, texto, f"prazo {r.get('prazo', '')}"))

    # 5. Indicadores N2 do esp com status vermelho/amarelo
    # FIX rodada 7.6 — RECOMPUTA status via _class_3tier(realizado, meta, direction)
    # em vez de ler `status` do JSON (stale apos override). Resolve o caso "Douglas
    # Estagnadas amarelo" quando valor real (31%) e verde com direction=menor_melhor.
    metas_ppi_card = (data.get("card", {}) or {}).get("metas_ppi", {}) or {}
    for ind_id, ind in wbr.get("indicadores", {}).items():
        if not isinstance(ind, dict):
            continue
        n2_dict = ind.get("n2") or ind.get("por_especialista") or {}
        e_n2 = n2_dict.get(esp, {})
        if not e_n2:
            continue
        # Recompute status via direction + realizado + meta
        real = (e_n2.get("realizado_mtd") or e_n2.get("realizado")
                or e_n2.get("pct") or e_n2.get("qty"))
        meta = e_n2.get("meta_mes") or e_n2.get("meta")
        # R6 (2026-05-07): Card.metas_ppi override — quando Card declara meta
        # diferente do canonical, o Card e SoT (preserva semaforo customizado).
        # Usado para SEG RE onde taxa_conversao Card=25% mas canonical=39%.
        card_meta = _meta_from_card_metas_ppi(card, ind_id, esp=esp)
        if card_meta is None:
            # tentar parent ind id sem subnivel suffix (ex: taxa_*_seg_re → taxa_*_seg)
            for parent_id in (metas_ppi_card or {}).keys():
                if ind_id.startswith(parent_id):
                    card_meta = _meta_from_card_metas_ppi(card, parent_id, esp=esp)
                    if card_meta is None:
                        # tenta sem esp (top-level meta)
                        card_meta = _meta_from_card_metas_ppi(card, parent_id)
                    if card_meta is not None:
                        break
        if card_meta is not None:
            meta = card_meta
        # Direction: indicator JSON > Card.metas_ppi[ind_id] > parent ind metas_ppi
        direction = ind.get("direction")
        if not direction:
            direction = (metas_ppi_card.get(ind_id) or {}).get("direction")
        if not direction:
            # tentar parent (ex: oportunidades_estagnadas_funil_pct_ativas → oportunidades_estagnadas_funil)
            for parent_id, _meta_ppi in metas_ppi_card.items():
                if ind_id.startswith(parent_id):
                    direction = (_meta_ppi or {}).get("direction")
                    if direction:
                        break
        direction = direction or "maior_melhor"
        cls = "mute"
        if isinstance(real, (int, float)) and isinstance(meta, (int, float)) and meta != 0:
            try:
                if direction == "menor_melhor":
                    pct = (meta / max(real, 1e-9)) * 100
                else:
                    pct = (real / meta) * 100
                cls = _class_3tier(pct, direction)
            except (TypeError, ZeroDivisionError):
                cls = "mute"
        if cls == "bad":
            # S1-A1#5 (2026-05-15): causa-raiz enriquecida via campo novo no WBR
            # canonical. analyst E3 (m7-controle/analyzing-deviations) deve passar
            # a emitir `indicadores.{id}.causa_raiz_resumo` (top-level) e/ou
            # `indicadores.{id}.n2.{esp}.causa_raiz_resumo` (por especialista, mais
            # especifico). Fallback graceful: campos legados obs / classificacao_maio.
            # Quando nada existir, mantem texto curto generico (sem suprimir o risco).
            causa_raiz = (
                e_n2.get("causa_raiz_resumo")
                or ind.get("causa_raiz_resumo")
                or e_n2.get("obs")
                or e_n2.get("classificacao_maio")
                or ""
            )
            label_ind = ind.get("label", ind_id)
            pct_str = ""
            if isinstance(real, (int, float)) and isinstance(meta, (int, float)) and meta:
                if direction == "menor_melhor":
                    pct_v = (real / meta) * 100  # mostra pct cru, nao invertido
                else:
                    pct_v = (real / meta) * 100
                pct_str = f" ({pct_v:.0f}% meta)"
            desc = f"{label_ind} N2 vermelho{pct_str}"
            ctx_short = causa_raiz[:200] if causa_raiz else ""
            if not _is_suppressed(desc) and not _is_suppressed(ctx_short):
                items.append(("alta", desc, ctx_short))
        elif cls == "warn":
            # S1-A1#5 (2026-05-15): mesma causa_raiz_resumo para warn (com fallback).
            causa_raiz_warn = (
                e_n2.get("causa_raiz_resumo")
                or ind.get("causa_raiz_resumo")
                or e_n2.get("obs")
                or ""
            )
            label_ind = ind.get("label", ind_id)
            desc = f"{label_ind} N2 amarelo (acompanhar)"
            ctx_short_warn = causa_raiz_warn[:200] if causa_raiz_warn else ""
            if not _is_suppressed(desc) and not _is_suppressed(ctx_short_warn):
                items.append(("media", desc, ctx_short_warn))

    # 6. Cluster sem efeito visivel mencionando esp
    cluster_msg = (wbr.get("acoes", {}).get("eficacia_concluidas", {}) or {}).get(
        "cluster_sem_efeito_concentrado", "")
    if cluster_msg and (esp_lc in cluster_msg.lower() or primeiro in cluster_msg.lower()):
        items.append(("media", f"Cluster sem efeito: {cluster_msg[:160]}", ""))

    # 7. F2 (2026-05-07): ZOOM IN em deals — top deals estagnados por
    # tempo_medio_dias do esp (do dados_n5 ou do indicador no WBR). Usuario
    # quer riscos especificos, nao agregacoes ("X indicador vermelho").
    if dados_n5:
        deals_estagnados = []
        for entry in dados_n5.get("indicadores", []):
            ind_id = entry.get("indicator_id", "")
            if not ("estagnada" in ind_id.lower() or "estagnado" in ind_id.lower()):
                continue
            for row in entry.get("data", []):
                if row.get("especialista") != esp:
                    continue
                if row.get("nivel") != "N5-Assessor":
                    continue
                if row.get("estagio"):  # so totais por assessor (sem duplicar por estagio)
                    continue
                tempo = row.get("tempo_medio_dias") or 0
                qty = row.get("quantidade") or 0
                vol = row.get("volume") or 0
                if qty == 0 or tempo == 0:
                    continue
                a_raw = row.get("assessor")
                if _is_esp_direct(a_raw):
                    continue
                a_name = _resolve_assessor_alias(a_raw, card)
                if squad_norms_local and not _assessor_in_squad(a_name, squad_norms_local):
                    continue
                deals_estagnados.append({
                    "assessor": a_name,
                    "qty": qty,
                    "vol": vol,
                    "tempo": int(tempo),
                })
        # Top 3 por tempo medio
        deals_estagnados.sort(key=lambda x: -x["tempo"])
        for d in deals_estagnados[:3]:
            items.append((
                "alta" if d["tempo"] >= 60 else "media",
                f"Estagnacao {d['assessor']}: {d['qty']} deal(s) parados {d['tempo']}d ({fmt_brl(d['vol'], compact=True)})",
                "Deal-level zoom — priorizar revisao Win/Lose/Renegociar",
            ))

    # 8. F2 (2026-05-07): ZOOM IN em deals sem atividade planejada do esp
    # (deal-level via indicador modo Detalhe).
    _sa_all = wbr.get("indicadores", {})
    sem_ativ_ind = (
        _sa_all.get("oportunidades_sem_atividade_planejada_funil_seg")
        or _sa_all.get("oportunidades_sem_atividade_planejada_funil")
        # FIX 2026-06-18: cards split (Seg WL/RE) usam chave com sufixo de subnivel
        # (..._funil_seg_re / ..._funil_seg_wl) — exact .get() acima nao casava e o
        # card caia em "SEM DADOS" apesar do dado existir. Prefix-scan cobre qualquer sufixo.
        or next((v for k, v in _sa_all.items()
                 if k.startswith("oportunidades_sem_atividade_planejada_funil")), {})
        or {}
    )
    detalhe_deals = (sem_ativ_ind.get("por_especialista", {}) or {}).get(esp, {}).get("detalhe_deals", [])
    for deal in (detalhe_deals or [])[:2]:
        nome = deal.get("nome") or deal.get("titulo") or "Deal sem nome"
        estagio = deal.get("estagio") or "?"
        items.append((
            "alta",
            f"Deal sem atividade: {nome[:50]} (estagio {estagio})",
            "Sem cadencia agendada — risco de derrubar pipeline",
        ))

    # C4 (2026-05-07): priorizar riscos ligados a indicadores de FUNIL (PPI)
    # antes dos de RESULTADO (KPI). Funil = causa (acionavel); Resultado = sintoma
    # (ja medido). Usuario quer riscos focados no que ainda da pra agir.
    _FUNIL_KW = (
        "estagnad", "estagnac", "conversao", "ativa", "criada", "funil",
        "pipeline", "mega-prospect", "mega prospect", "zerado", "zerados",
        "intake", "cobertura", "carteira", "oport.", "oportunidade",
        "deals", "deal sem", "renegoc", "win/lose", "wln",
    )
    _RESULTADO_KW = (
        "receita ", "% receita", "volume ", "% volume", "comissao",
        "faturamento", "premio liquido", "ticket medio",
    )

    def _risk_priority(desc: str) -> int:
        """0 = funil/PPI (topo), 2 = resultado/KPI (fim), 1 = outros (meio)."""
        d = (desc or "").lower()
        if any(kw in d for kw in _FUNIL_KW):
            return 0
        if any(kw in d for kw in _RESULTADO_KW):
            return 2
        return 1

    # Sort por (PPI primeiro, depois severidade) + dedup (prefix match + topic keyword)
    items.sort(key=lambda x: (_risk_priority(x[1]), sev_order.get(x[0], 1)))
    # FIX rodada 6 issue 9 — dedup por TOPIC keyword. Caso recorrente:
    # mega-prospects aparecia 3x (D + anomalia E + recomendacao). Agora 1x.
    # Outros topicos com chance de duplicacao listados aqui sao agrupados.
    TOPIC_KEYWORDS = {
        "mega_prospects": ("mega-prospect", "mega prospect", "mega-prospects"),
        "estagnados": ("estagnados", "estagnacao", "deals estagnados"),
        "concentracao": ("concentracao", "= ", "% receita n2", "% volume n2"),
        "zerados": ("zerados", "carteiras inativas"),
        "win_lose_renegociar": ("win/lose/renegociar", "win lose renegociar",
                                "binaria win", "wln status"),
    }

    def _topic_of(desc: str) -> str:
        d = (desc or "").lower()
        for topic, kws in TOPIC_KEYWORDS.items():
            if any(kw in d for kw in kws):
                return topic
        return ""

    seen_prefix = set()
    seen_topics = set()
    deduped = []
    for it in items:
        key = it[1][:60].lower()
        topic = _topic_of(it[1])
        if key in seen_prefix:
            continue
        if topic and topic in seen_topics:
            continue
        seen_prefix.add(key)
        if topic:
            seen_topics.add(topic)
        deduped.append(it)
        if len(deduped) >= max_items:
            break

    if not deduped:
        return '<div class="risk-item" style="color:var(--verde-claro);font-style:italic;font-size:21px;">Sem riscos especificos para este especialista no ciclo.</div>'

    sev_color = {"alta": "var(--error)", "media": "#d18000", "informativa": "var(--verde-claro)"}
    out = []
    for sev, desc, ctx in deduped:
        color = sev_color.get(sev, "var(--verde-claro)")
        ctx_html = ""  # 2026-06-12: subtexto nao-negrito (ctx/linhagem) removido dos cards de risco (Img 2)
        out.append(
            f'<div class="risk-item" style="border-left:3px solid {color};padding:6px 10px;margin-bottom:6px;font-size:21px;line-height:1.4;">'
            f'<strong>{desc}</strong>{ctx_html}'
            f'</div>'
        )
    return "\n".join(out)


def _esp_squad_size(esp: str, data: dict) -> int:
    """Extrai tamanho do squad do esp.
    FIX rodada 6 issue 14/15 — primeiro tenta Card.apresentacao.responsaveis[esp].squad
    (whitelist oficial), fallback para parsing da description text."""
    card = data["card"]
    # Whitelist oficial primeiro
    squad = _get_squad_whitelist(esp, card)
    if squad:
        return len(squad)
    # Fallback heuristico — parse description
    desc = (card["metadata"].get("description") or "")
    for line in desc.splitlines():
        if f"Squad {esp}" in line and "assessor" in line.lower():
            m = re.search(r"(\d+)\s*assessor", line)
            if m:
                return int(m.group(1))
    return 0


def _esp_kpi_tiles(esp: str, data: dict) -> str:
    """6 KPI tiles for Pipeline slide. N-parametrico via _esp_kpi_value
    (suporta CON-legacy `por_especialista` e SEG-split `n2.realizado`)."""
    qty       = _esp_kpi_value(data, esp, "ativas",         aspect="qty")    or 0
    vol       = _esp_kpi_value(data, esp, "ativas",         aspect="volume") or 0
    estag_qty = _esp_kpi_value(data, esp, "estagnadas",     field_legacy="qtd_estagnados") or 0
    crd_qty   = _esp_kpi_value(data, esp, "criadas",        field_legacy="qty") or 0
    taxa_raw  = _esp_kpi_value(data, esp, "taxa_conversao", field_legacy="taxa") or 0
    # taxa pode vir como ratio (0.30) ou pct (30) — normalizar para pct
    taxa_v = (taxa_raw * 100) if (isinstance(taxa_raw, (int, float)) and 0 < taxa_raw <= 1.0) else taxa_raw
    ticket = (vol / qty) if qty else 0

    tiles = [
        f'<div class="kpi-tile"><div class="v">{fmt_int(qty)}</div><div class="l">Deals ativos</div></div>',
        f'<div class="kpi-tile"><div class="v">{fmt_brl(vol, compact=True)}</div><div class="l">Volume ativo</div></div>',
        f'<div class="kpi-tile"><div class="v">{fmt_brl(ticket, compact=True)}</div><div class="l">Ticket Médio Pipeline</div></div>',
        f'<div class="kpi-tile"><div class="v {"bad" if estag_qty > qty * 0.5 else "warn" if estag_qty > qty * 0.25 else ""}">{fmt_int(estag_qty)}</div><div class="l">Estagnados</div></div>',
        f'<div class="kpi-tile"><div class="v">{fmt_int(crd_qty)}</div><div class="l">Opps criadas</div></div>',
        f'<div class="kpi-tile"><div class="v {"bad" if taxa_v < 15 else "warn" if taxa_v < 30 else "good"}">{fmt_pct(taxa_v, 0)}</div><div class="l">Conv. mês</div></div>',
    ]
    return "\n".join(tiles)


def _esp_summary_cards(esp: str, esp_idx: int, data: dict, ctx: dict, dados_n5: dict) -> str:
    """Auto-fill 5 .summary-card + 1 callout (Slide N+1 Analise side panel).
    1. Concentracao de receita (top 2 deals = X% volume)
    2. Cobertura (X / total_squad assessores com deal ativo)
    3. Estagnacao alerta (dias medios)
    4. Assessores com opp criada no mes
    5. Sem atividade planejada — variante LISTA (top 5 deals)
    + Comparativo callout (apenas N>=2 esps)
    Todos N-parametricos."""
    cards = []
    indicadores = data["wbr"].get("indicadores", {})

    # FIX rodada 7 issue 6 — Concentracao + Cobertura usam squad whitelist + estagio is None
    squad_whitelist = _get_squad_whitelist(esp, data["card"])
    squad_norms = {_normalize_assessor_name(a) for a in squad_whitelist}

    # Card 1: Concentracao (limita a squad whitelist + esp_direct)
    deals_ativos = []
    for entry in dados_n5.get("indicadores", []):
        if not (entry.get("indicator_id") or "").startswith("oportunidades_ativas_funil"):
            continue
        for row in entry.get("data", []):
            if row.get("especialista") == esp and row.get("nivel") == "N5-Assessor":
                if row.get("estagio"):
                    continue  # snapshot only — evita double-count por estagio
                vol = row.get("volume") or 0
                if vol <= 0:
                    continue
                a_raw = row.get("assessor")
                # esp_direct conta para concentracao (representa o proprio esp)
                if _is_esp_direct(a_raw):
                    deals_ativos.append((a_raw, vol))
                    continue
                # FIX rodada 7 — aplica alias case-insensitive antes do squad filter
                a_canon = _resolve_assessor_alias(a_raw, data["card"])
                # outsiders nao contam para concentracao
                if squad_norms and not _assessor_in_squad(a_canon, squad_norms):
                    continue
                deals_ativos.append((a_canon, vol))
    deals_ativos.sort(key=lambda x: -x[1])
    total_vol = sum(v for _, v in deals_ativos) or 1
    top2_vol = sum(v for _, v in deals_ativos[:2])
    top2_pct = (top2_vol / total_vol) * 100
    sv_cls = "bad" if top2_pct >= 60 else ("warn" if top2_pct >= 40 else "")
    cards.append(
        f'<div class="summary-card"><div class="sh">Concentracao volume</div>'
        f'<div class="sv {sv_cls}">{int(top2_pct)}%</div>'
        f'<div class="sd">Top 2 assessores sustentam {int(top2_pct)}% do volume ativo</div></div>'
    )

    # Card 2: Cobertura — FIX rodada 7 issue 6 + 7.5: conta SOMENTE membros da squad
    # whitelist com deal ativo (exclui esp_direct, exclui outsiders). Dedupe via slug
    # para evitar variantes (acentos/espacos) virarem entries separadas.
    # R6 (2026-05-07): quando squad_size == 0 (RE sem squad fixo), exibir
    # "Squad pendente" em vez de "X / 0" (visualmente confuso).
    squad_size = _esp_squad_size(esp, data)
    if squad_size == 0 or not squad_whitelist:
        cards.append(
            f'<div class="summary-card"><div class="sh">Cobertura squad</div>'
            f'<div class="sv mute" style="color:var(--verde-claro);font-style:italic;font-size:22px;">Squad pendente</div>'
            f'<div class="sd" style="color:var(--verde-claro);font-style:italic;">Especialista sem squad fixo declarado.</div></div>'
        )
    else:
        assessores_com_deal_slugs = {
            _normalize_assessor_name(a)
            for a, v in deals_ativos
            if v > 0 and not _is_esp_direct(a)
            and _assessor_in_squad(a, squad_norms)
        }
        assessores_com_deal = len(assessores_com_deal_slugs)
        cobert_pct = (assessores_com_deal / squad_size * 100) if squad_size else 0
        sv_cls = "bad" if cobert_pct < 50 else ("warn" if cobert_pct < 75 else "")
        cards.append(
            f'<div class="summary-card"><div class="sh">Cobertura squad</div>'
            f'<div class="sv {sv_cls}">{assessores_com_deal} / {squad_size}</div>'
            f'<div class="sd">{assessores_com_deal} de {squad_size} assessores com deal ativo</div></div>'
        )

    # Card 3: Estagnacao alerta (dias medios)
    # Refator 2026-05-07: resolve dinamicamente o ID `oportunidades_estagnadas_*_pct_ativas`
    # via _kpi_id (suporta CON, SEG WL/RE — em SEG e `*_seg_wl_pct_ativas`, etc.)
    estag_pct_id = _kpi_id(data, "estagnadas", aspect="pct_ativas") or "oportunidades_estagnadas_funil_pct_ativas"
    estag_top = indicadores.get(estag_pct_id, {}) or {}
    # tenta por_especialista.{esp} (CON-legacy) e n2.{esp} (SEG)
    estag_n2 = (estag_top.get("por_especialista") or {}).get(esp) or (estag_top.get("n2") or {}).get(esp) or {}
    tempo_medio = estag_n2.get("tempo_medio_dias", 0)
    # S1-bug-Estagnacao (2026-05-15): pct_estag deve SEMPRE ser `realizado` (=
    # qty_estagnadas/qty_ativas × 100, valor semantico de "% pipeline parado").
    # O campo `pct` no canonical v1.1 do indicador *_pct_ativas e pct_atingimento
    # da meta (meta/realizado × 100 para menor_melhor), NAO o valor semantico.
    # Eliminada a heuristica "SEG schema vs CON schema" — agora padronizado em
    # `realizado` para todas as verticais.
    pct_estag = estag_n2.get("realizado", 0) or 0
    # Tempo medio fallback 1: indicador estagnadas qty no canonical (CON tem la)
    if not tempo_medio:
        estag_qty_id = _kpi_id(data, "estagnadas")
        if estag_qty_id and estag_qty_id != estag_pct_id:
            qty_n2 = (indicadores.get(estag_qty_id, {}).get("n2") or {}).get(esp) or {}
            tempo_medio = qty_n2.get("tempo_medio_dias", 0) or 0
    # Tempo medio fallback 2: agregado dos rows N2-Especialista do dados_n5 (SEG canonical
    # nao popula tempo_medio_dias em n2; mas dados-consolidados E2 tem nas rows).
    if not tempo_medio and dados_n5:
        for entry in dados_n5.get("indicadores", []):
            if not (entry.get("indicator_id") or "").startswith("oportunidades_estagnadas_funil"):
                continue
            for row in entry.get("data", []):
                if (row.get("especialista") == esp
                    and row.get("nivel") == "N2-Especialista"
                    and not row.get("estagio")):
                    tempo_medio = row.get("tempo_medio_dias", 0) or 0
                    if tempo_medio:
                        break
            if tempo_medio:
                break
    sv_cls = "bad" if pct_estag >= 50 else ("warn" if pct_estag >= 30 else "")
    cards.append(
        f'<div class="summary-card"><div class="sh">Estagnacao</div>'
        f'<div class="sv {sv_cls}">{int(tempo_medio)}d</div>'
        f'<div class="sd">Tempo medio · {int(pct_estag)}% pipeline parado</div></div>'
    )

    # Card 4: Sem atividade planejada — variante LISTA (top 5)
    # NOTA C5 (2026-05-07): card "Intake mes" removido por solicitacao do
    # usuario apos ritual Cons S19 — duplicava informacao ja presente na
    # Matriz (Oportunidades Criadas qty) e poluia visualmente.
    # FIX (2026-05-14): Card de Sem Atividade Planejada estava sempre 'sem dados'
    # porque lia apenas por_especialista.qty. Analyst v1.1 emite n2.{esp}.realizado.
    # Fallback chain: n2 -> por_especialista; realizado -> qty -> quantidade.
    sem_ativ = (
        indicadores.get("oportunidades_sem_atividade_planejada_funil")
        or indicadores.get("oportunidades_sem_atividade_planejada_funil_seg")
        # FIX 2026-06-18: cards split (Seg WL/RE) usam ..._funil_seg_re / ..._funil_seg_wl —
        # prefix-scan evita o falso "SEM DADOS" quando o exact .get() nao casa o sufixo.
        or next((v for k, v in indicadores.items()
                 if k.startswith("oportunidades_sem_atividade_planejada_funil")), {})
        or {}
    )
    sem_ativ_n2 = (sem_ativ.get("n2") or sem_ativ.get("por_especialista") or {}).get(esp, {}) or {}
    qty_sem_ativ = (
        sem_ativ_n2.get("realizado")
        if sem_ativ_n2.get("realizado") is not None
        else (sem_ativ_n2.get("qty") if sem_ativ_n2.get("qty") is not None
              else sem_ativ_n2.get("quantidade"))
    )
    if qty_sem_ativ is None:
        cards.append(
            f'<div class="summary-card list"><div class="sh">Sem atividade planejada<span class="sh-count">— sem dados</span></div>'
            f'<div class="sd" style="color:var(--verde-claro);font-style:italic;">Indicador nao coletado neste ciclo.</div></div>'
        )
    elif qty_sem_ativ == 0:
        cards.append(
            f'<div class="summary-card list"><div class="sh">Sem atividade planejada<span class="sh-count" style="color:#2e7d32;">0 deals</span></div>'
            f'<div class="sd" style="color:#2e7d32;">Sem deals nesta condicao.</div></div>'
        )
    else:
        # FIX (2026-05-14): listar top 5 deals do esp ordenados por dias_sem_atividade desc.
        # Detail rows vem de dados_n5 (indicador oportunidades_sem_atividade_planejada_funil).
        deals_detail = []
        for entry in (dados_n5 or {}).get("indicadores", []) or []:
            if not (entry.get("indicator_id") or "").startswith("oportunidades_sem_atividade_planejada_funil"):
                continue
            for row in entry.get("data") or []:
                if row.get("nivel") != "Detalhe":
                    continue
                if row.get("especialista") != esp:
                    continue
                deals_detail.append({
                    "nome": row.get("nome_deal") or row.get("deal_id") or "—",
                    "assessor": row.get("assessor") or "—",
                    "estagio": row.get("estagio") or "—",
                    "dias": row.get("dias_sem_atividade") or 0,
                    "vol": row.get("volume") or 0,
                })
        deals_detail.sort(key=lambda x: -(x.get("dias") or 0))
        top_deals = deals_detail[:5]
        if top_deals:
            list_html = "".join(
                f'<div style="display:flex;justify-content:space-between;gap:8px;font-size:11px;line-height:1.35;margin-top:4px;">'
                f'<span style="flex:1;color:var(--verde-caqui);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{d["nome"][:38]}</span>'
                f'<span style="color:var(--verde-claro);">{d["dias"]}d · {d["estagio"][:14]}</span>'
                f'</div>'
                for d in top_deals
            )
            extra = f'<div style="font-size:10px;color:var(--verde-claro);font-style:italic;margin-top:4px;">+{qty_sem_ativ - 5} outros</div>' if qty_sem_ativ > 5 else ""
            cards.append(
                f'<div class="summary-card list"><div class="sh">Sem atividade planejada<span class="sh-count">{qty_sem_ativ} deals</span></div>'
                f'<div class="sd" style="font-size:11px;color:var(--verde-claro);">Top {len(top_deals)} por dias parados:</div>'
                f'{list_html}{extra}</div>'
            )
        else:
            cards.append(
                f'<div class="summary-card list"><div class="sh">Sem atividade planejada<span class="sh-count">{qty_sem_ativ} deals</span></div>'
                f'<div class="sd">Cobertura de cadencia comercial pendente. Ver lista detalhada no plano.</div></div>'
            )

    # Callout Comparativo (apenas se N>=2)
    n = ctx["_n_especialistas"]
    if n >= 2:
        # Compara volume ativo vs outros esps
        outros = [e for e in ctx["_esp_list"] if e != esp]
        if outros:
            outro = outros[0]
            esp_vol = sum(v for _, v in deals_ativos)
            outro_vol = 0
            for entry in dados_n5.get("indicadores", []):
                if not (entry.get("indicator_id") or "").startswith("oportunidades_ativas_funil"):
                    continue
                for row in entry.get("data", []):
                    if row.get("especialista") == outro and row.get("nivel") == "N2-Especialista":
                        outro_vol = row.get("volume") or 0
                        break
            sign = "&gt;" if esp_vol > outro_vol else ("&lt;" if esp_vol < outro_vol else "≈")
            cls = "" if esp_vol >= outro_vol * 0.8 else "bad"
            cards.append(
                f'<div class="callout {cls}"><span class="label">Comparativo</span> '
                f'Squad {primeiro_nome(esp)} {sign} Squad {primeiro_nome(outro)} em volume ativo '
                f'({fmt_brl(esp_vol, compact=True)} vs {fmt_brl(outro_vol, compact=True)}).</div>'
            )

    return "\n".join(cards)


def _esp_funnel_svg(esp: str, data: dict, dados_n5: dict) -> str:
    """Gera SVG inline 720x380 do funil para o esp.
    Estagios vem de Card.pipeline_stages (N-parametrico).

    FIX 2026-05-05 (Slide 8): para garantir parity com KPI tile (qty/volume totais
    do N2), agregar PRIMARIO via N2-Especialista rows COM estagio (quando disponivel),
    senao fallback para N5-Assessor por estagio. Isso garante:
        Sigma(funnel) == KPI tile total (16 deals, R$ 82,5M para Douglas).
    """
    card = data["card"]
    stages = card.get("pipeline_stages", []) or []
    if not stages:
        return ('<div style="padding:40px;color:var(--verde-claro);font-style:italic;'
                'text-align:center;">Sem pipeline_stages declarados no Card.</div>')

    # Strategy: tentar N2-Especialista por estagio primeiro (mais preciso, evita
    # double-count com placeholders 0-qty do N5). Fallback N5 se nao achar.
    # Match case-insensitive + sem acentos (Card pode declarar "Emissão de Contrato"
    # mas dados ter "Emissão de contrato" — diferenca cosmetica nao deve perder match).
    stage_keys = [s["nome"] for s in stages]
    stage_lookup = {slugify(k): k for k in stage_keys}  # slug → canonical name do Card
    volumes_by_stage = {k: 0.0 for k in stage_keys}
    qty_by_stage = {k: 0 for k in stage_keys}

    def _match_stage(est_raw):
        """Retorna canonical stage name do Card para um estagio bruto do JSON, case-insensitive."""
        if not est_raw:
            return None
        return stage_lookup.get(slugify(est_raw))

    if dados_n5:
        # 1a tentativa: N2-Especialista com estagio (1 row por stage do esp)
        for entry in dados_n5.get("indicadores", []):
            if not (entry.get("indicator_id") or "").startswith("oportunidades_ativas_funil"):
                continue
            for row in entry.get("data", []):
                if row.get("especialista") != esp or row.get("nivel") != "N2-Especialista":
                    continue
                est_canon = _match_stage(row.get("estagio"))
                if est_canon:
                    volumes_by_stage[est_canon] += row.get("volume") or 0
                    qty_by_stage[est_canon] += row.get("quantidade") or 0

        # Fallback N5 quando N2 nao tem breakdown por estagio
        if sum(qty_by_stage.values()) == 0:
            for entry in dados_n5.get("indicadores", []):
                if not (entry.get("indicator_id") or "").startswith("oportunidades_ativas_funil"):
                    continue
                for row in entry.get("data", []):
                    if row.get("especialista") != esp or row.get("nivel") != "N5-Assessor":
                        continue
                    est_canon = _match_stage(row.get("estagio"))
                    if est_canon:
                        volumes_by_stage[est_canon] += row.get("volume") or 0
                        qty_by_stage[est_canon] += row.get("quantidade") or 0

    n = len(stages)
    if n == 0:
        return "<!-- funnel: 0 stages -->"

    # R5-8 (2026-05-07): refator visual do funil para padrao S18 — trapezios SVG
    # com largura proporcional ao volume, conectores com delta %, top stage verde,
    # foot com "Maior gargalo". Substitui retangulos do round 5.
    #
    # S1-A2 (2026-05-15): H calculado DINAMICAMENTE baseado em n stages para nao
    # cortar quando > 5 stages (SEG RE/WL tem 7 stages incluindo Emissao Apolice
    # + Onboarding). Antes era H=380 fixo (so cabia 5 stages).
    W = 720
    # Item 14 (2026-05-21): labels do estagio agora FORA da barra (esquerda, x=20+).
    # Shift cx para direita (400 vs 360) + reduzir max_half_w (230 vs 270) para abrir
    # coluna ~150px de labels a esquerda sem sobreposicao com trapezoide.
    # Trapezoide: left edge = 400-230 = 170 (folga ~30px do label mais longo).
    # Right edge = 400+230 = 630. Deals/valor a direita: 630+16 = 646, cabe ate W=720.
    cx = 400
    stage_h = 48
    gap = 12
    top_y = 30
    # H = topo + n × (stage_h + gap) − gap final + footer "Maior gargalo" (~70px)
    H = top_y + n * (stage_h + gap) - gap + 70
    max_half_w = 230  # half-width quando qty == max_qty

    max_qty = max(qty_by_stage.values()) or 1
    # Top stage para coloracao verde
    top_stage_name = max(qty_by_stage.items(), key=lambda x: x[1])[0] if qty_by_stage else None

    # R6 (2026-05-07): qty total esperado (KPI tile "Deals ativos") pode divergir
    # do SUM(stages) quando ha estagios de pos-venda (Emissao Apolice, Onboarding etc.)
    # nao declarados em pipeline_stages. Mostrar a diferenca como nota.
    qty_total_esp = _esp_kpi_value(data, esp, "ativas", aspect="qty") or 0
    qty_no_stages = sum(qty_by_stage.values())
    qty_outros = max(0, int(qty_total_esp) - int(qty_no_stages))

    parts = [f'<svg viewBox="0 0 {W} {H}" width="100%" height="100%" preserveAspectRatio="xMidYMid meet" style="display:block;" role="img" aria-label="Funil {esp}">']
    # R8 (2026-05-07): coluna esquerda "Volume relativo" (% etapa + header)
    # removida por solicitacao do usuario — manter apenas conectores delta % no
    # meio + "Deals · valor" direita.
    parts.append(f'<text x="{W-40}" y="22" style="font-size:10px;letter-spacing:0.12em;text-transform:uppercase;fill:var(--vc-300);" text-anchor="end">Deals · valor</text>')

    # 1a passada: stages
    stage_data = []  # registro (nome, qty, vol, half_w_top, half_w_bot, y_top, y_bot, fill, opacity)
    for i, s in enumerate(stages):
        nome = s["nome"]
        vol = volumes_by_stage.get(nome, 0)
        qty = qty_by_stage.get(nome, 0)
        # Half-widths: top = qty / max_qty * max_half_w; base ligeiramente menor (efeito funil)
        half_w_top = (qty / max_qty) * max_half_w if max_qty else 0
        half_w_top = max(20, half_w_top) if qty > 0 else 8  # min visual ~16px width quando qty=0
        half_w_bot = max(half_w_top - 5, 16) if qty > 0 else half_w_top  # leve estreitamento na base
        y_top = top_y + i * (stage_h + gap)
        y_bot = y_top + stage_h

        # Cor: top stage verde, ultimo (Proposta) verde se for o melhor performer; outros vc-500 com opacity decrescente
        # Item 14 follow-up (2026-05-21): labels do estagio agora FORA da barra
        # (a esquerda, x=20). Texto sempre em var(--verde-caqui) sobre BG off-white
        # do card — preserva legibilidade independente da cor/largura da barra.
        # Removida heuristica de text_fill adaptativo (text_overflows_trapezio)
        # e fill claro do estagio zerado: nao precisa mais porque label nao
        # esta dentro da forma colorida.
        if qty > 0 and nome == top_stage_name:
            fill = "#2e7d32"
            opacity = "1"
        elif qty == 0:
            fill = "#e8e8e4"
            opacity = "1"
        else:
            fill = "var(--vc-500)"
            # opacity decrescente: 1.0 → 0.66 ao longo dos 5 stages
            opacity_val = 1.0 - (i / max(1, n - 1)) * 0.34
            opacity = f"{opacity_val:.2f}"

        # Labels fora: sempre cor verde-caqui sobre BG off-white do card
        label_fill = "var(--verde-caqui)"
        sublabel_fill = "var(--verde-claro)"
        # Estagio zerado: opacity reduzida no label (sem ofuscar mas indica vazio)
        if qty == 0:
            label_fill = "#79755c"
            sublabel_fill = "#a9a597"

        stage_data.append({
            "i": i, "nome": nome, "qty": qty, "vol": vol,
            "half_w_top": half_w_top, "half_w_bot": half_w_bot,
            "y_top": y_top, "y_bot": y_bot,
            "fill": fill, "opacity": opacity,
            "label_fill": label_fill, "sublabel_fill": sublabel_fill,
        })

        # Trapezio: polygon top wider, bot narrower
        x1 = cx - half_w_top
        x2 = cx + half_w_top
        x3 = cx + half_w_bot
        x4 = cx - half_w_bot
        parts.append(
            f'<g><polygon points="{x1:.0f},{y_top} {x2:.0f},{y_top} {x3:.0f},{y_bot} {x4:.0f},{y_bot}" '
            f'fill="{fill}" opacity="{opacity}" />'
        )
        # Item 14 (2026-05-21): nome do stage FORA da barra (esquerda), sempre legivel
        parts.append(
            f'<text x="20" y="{y_top + 24}" text-anchor="start" fill="{label_fill}" '
            f'style="font-size:13px;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;">{nome}</text>'
        )
        # Sublabel descritiva (avg_days_to_close) tambem fora, embaixo do nome
        sub_hint = ""
        avg_days = s.get("avg_days_to_close")
        if avg_days:
            sub_hint = f"~{avg_days}d para fechar"
        if sub_hint:
            parts.append(
                f'<text x="20" y="{y_top + 40}" text-anchor="start" fill="{sublabel_fill}" '
                f'style="font-size:11px;font-style:italic;">{sub_hint}</text>'
            )
        # R8 (2026-05-07): label "% etapa" na esquerda removido por solicitacao
        # do usuario — coluna "Volume relativo" inteira escondida do funil.
        # Direita: deals + valor
        deals_color = "#2e7d32" if (qty > 0 and nome == top_stage_name) else "var(--verde-caqui)"
        deals_weight = "600" if (qty > 0 and nome == top_stage_name) else "500"
        vol_str = fmt_brl(vol, compact=True) if vol > 0 else "—"
        deals_lbl = f"{qty} deal{'s' if qty != 1 else ''}" if qty else "0 deals"
        parts.append(
            f'<text x="{cx + max_half_w + 16:.0f}" y="{y_top + 20}" '
            f'style="font-size:20px;font-weight:{deals_weight};fill:{deals_color};">{deals_lbl}</text>'
        )
        parts.append(
            f'<text x="{cx + max_half_w + 16:.0f}" y="{y_top + 36}" '
            f'style="font-size:12px;fill:var(--verde-claro);">{vol_str}</text></g>'
        )

    # Conectores entre stages (delta % entre i e i+1)
    biggest_drop = {"delta_pct": 0, "from_idx": None, "from_name": None, "to_name": None, "deals_lost": 0}
    for i in range(n - 1):
        a = stage_data[i]
        b = stage_data[i + 1]
        if a["qty"] > 0:
            delta_pct = ((b["qty"] - a["qty"]) / a["qty"]) * 100
        else:
            delta_pct = 0
        # Conector: tracejado vertical entre y_bot do stage i e y_top do stage i+1
        x_line = cx
        y_a = a["y_bot"]
        y_b = b["y_top"]
        parts.append(
            f'<line x1="{x_line}" y1="{y_a}" x2="{x_line}" y2="{y_b}" '
            f'stroke="var(--vc-200)" stroke-dasharray="2,2" />'
        )
        # Label do delta
        if delta_pct > 0:
            color = "#2e7d32"
            sign = "+"
        elif delta_pct < 0:
            color = "var(--error)"
            sign = "−"
        else:
            color = "var(--vc-400)"
            sign = "="
        # R8 (2026-05-07): labels delta % dos conectores tambem removidos
        # (parte da coluna "Volume relativo" escondida). Mantido o tracejado
        # vertical entre etapas (visualmente separa stages).
        delta_str = f"{sign}{abs(delta_pct):.0f}%" if delta_pct != 0 else "="
        # Track maior gargalo (maior queda)
        if delta_pct < biggest_drop["delta_pct"]:
            biggest_drop["delta_pct"] = delta_pct
            biggest_drop["from_idx"] = i
            biggest_drop["from_name"] = a["nome"]
            biggest_drop["to_name"] = b["nome"]
            biggest_drop["deals_lost"] = a["qty"] - b["qty"]

    # Foot: maior gargalo + total ativas
    foot_y = top_y + n * (stage_h + gap) + 6
    parts.append(f'<line x1="40" y1="{foot_y}" x2="{W-40}" y2="{foot_y}" stroke="var(--vc-100)" />')
    if biggest_drop["from_name"] and biggest_drop["delta_pct"] < 0:
        parts.append(
            f'<text x="40" y="{foot_y + 18}" style="font-size:11px;fill:var(--verde-claro);">Maior gargalo:</text>'
        )
        parts.append(
            f'<text x="118" y="{foot_y + 18}" style="font-size:11px;font-weight:700;fill:var(--error);">'
            f'{biggest_drop["from_name"]} → {biggest_drop["to_name"]}</text>'
        )
        deals_lost = biggest_drop["deals_lost"]
        parts.append(
            f'<text x="{118 + 6 * len(biggest_drop["from_name"]) + 6 * len(biggest_drop["to_name"]) + 30}" y="{foot_y + 18}" '
            f'style="font-size:11px;fill:var(--verde-claro);">'
            f'({biggest_drop["delta_pct"]:.0f}% · {deals_lost} deal{"s" if deals_lost != 1 else ""} perdido{"s" if deals_lost != 1 else ""})</text>'
        )
    # R6 (2026-05-07): nota de total quando soma dos stages diverge do KPI tile
    if qty_outros > 0:
        parts.append(
            f'<text x="{W-40}" y="{foot_y + 18}" text-anchor="end" '
            f'style="font-size:11px;fill:var(--verde-claro);font-style:italic;">'
            f'{int(qty_total_esp)} deals ativos · {int(qty_no_stages)} nos estagios · {qty_outros} em pos-venda/outros</text>'
        )
    parts.append('</svg>')
    return "\n".join(parts)


def _interpolate_color(c_start: str, c_end: str, t: float) -> str:
    """Interpola entre 2 hex colors. t=0 → c_start; t=1 → c_end."""
    def hex_to_rgb(h):
        h = h.lstrip("#")
        return [int(h[i:i+2], 16) for i in (0, 2, 4)]
    a = hex_to_rgb(c_start)
    b = hex_to_rgb(c_end)
    rgb = [int(a[i] + (b[i] - a[i]) * t) for i in range(3)]
    return "#" + "".join(f"{c:02x}" for c in rgb)


def _esp_destaque(esp: str, data: dict, dados_n5: dict) -> str:
    """Auto-fill Destaque card (Slide N+2 Pipeline). Top stage + Conversao + Top assessores.
    FIX rodada 5: aplica alias map + filtro mes corrente."""
    lines = []
    card = data["card"]
    current_month = _get_current_month_prefix(data)
    indicadores = data["wbr"].get("indicadores", {})
    esp_direct_label = f"{esp} (esp)"

    # 1. Top stage por volume
    if dados_n5:
        stage_volumes = {}
        for entry in dados_n5.get("indicadores", []):
            if not (entry.get("indicator_id") or "").startswith("oportunidades_ativas_funil"):
                continue
            for row in entry.get("data", []):
                if row.get("especialista") == esp and row.get("nivel") == "N2-Especialista":
                    est = row.get("estagio")
                    if est:
                        stage_volumes[est] = stage_volumes.get(est, 0) + (row.get("volume") or 0)
        if stage_volumes:
            top_stage, top_vol = max(stage_volumes.items(), key=lambda x: x[1])
            total_vol = sum(stage_volumes.values()) or 1
            pct = (top_vol / total_vol) * 100
            lines.append(
                f'<div style="margin-bottom:8px;"><strong>Top stage:</strong> {top_stage} '
                f'concentra {fmt_brl(top_vol, compact=True)} ({pct:.0f}% do volume ativo).</div>'
            )

    # 2. Conversao do mes
    taxa_id_local = _kpi_id(data, "taxa_conversao")
    taxa = indicadores.get(taxa_id_local, {}) if taxa_id_local else {}
    e_taxa = (taxa.get("por_especialista", {}) or {}).get(esp, {})
    if e_taxa:
        ganhos = e_taxa.get("ganhos", 0)
        fechados = e_taxa.get("fechados", 0)
        if fechados > 0:
            pct = (ganhos / fechados) * 100 if fechados else 0
            lines.append(
                f'<div style="margin-bottom:8px;"><strong>Conversao mes:</strong> '
                f'{ganhos}/{fechados} fechados = {pct:.0f}% ({"acima" if pct >= 30 else "abaixo"} da meta 30%).</div>'
            )

    # 3. Top 2 assessores ativos (snapshot — sem filtro mes; alias aplicado).
    # FIX rodada 6 issue 17 — exclui esp_direct ("{esp} (esp)") do top, pois ele
    # representa deals do PROPRIO especialista (sem assessor), nao "assessor"
    # comercial real. Tambem aplica squad whitelist quando declarada no Card.
    if dados_n5:
        ativas_id_n5 = _kpi_id_n5(dados_n5, data["card"], "ativas")
        squad_wl = _get_squad_whitelist(esp, card)
        squad_norms = {_normalize_assessor_name(a) for a in squad_wl}
        by_assessor = {}
        for entry in dados_n5.get("indicadores", []):
            if entry.get("indicator_id") != ativas_id_n5:
                continue
            for row in entry.get("data", []):
                if row.get("especialista") != esp or row.get("nivel") != "N5-Assessor":
                    continue
                if row.get("estagio"):
                    continue  # mesmo fix issue 11/12/13: somente totais
                vol = row.get("volume") or 0
                qty = row.get("quantidade") or 0
                if vol <= 0:
                    continue
                assessor_raw = row.get("assessor")
                if _is_esp_direct(assessor_raw):
                    continue  # FIX issue 17 — esp_direct nao e "Top assessor"
                label = _resolve_assessor_alias(assessor_raw, card)
                # squad whitelist filter (consistente com _aggregate_assessor_volumes)
                if squad_norms and not _assessor_in_squad(label, squad_norms):
                    continue
                if label not in by_assessor:
                    by_assessor[label] = {"vol": 0, "qty": 0}
                by_assessor[label]["vol"] += vol
                by_assessor[label]["qty"] += qty
        sorted_a = sorted(by_assessor.items(), key=lambda x: -x[1]["vol"])
        top2 = sorted_a[:2]
        if top2:
            lines.append('<div style="margin-bottom:4px;"><strong>Top assessores:</strong></div>')
            for label, m in top2:
                lines.append(
                    f'<div style="margin-bottom:4px;padding-left:12px;font-size:13px;">{label} '
                    f'· {fmt_brl(m["vol"], compact=True)} ({m["qty"]} deals)</div>'
                )

    if not lines:
        return '<span style="color:var(--verde-claro);font-style:italic;">Sem destaques estruturais identificados.</span>'
    return "\n".join(lines)


def _esp_estagnacao(esp: str, data: dict, dados_n5: dict) -> str:
    """Auto-fill Estagnacao card. FIX img10 — incluir top stages + assessores + tempo medio.
    Multi-faceted: stage com mais volume parado + assessor critico + tempo medio do esp.
    N-parametrico — qualquer vertical com indicador estagnadas."""
    lines = []
    indicadores = data["wbr"].get("indicadores", {})

    # 1. % das ativas estagnadas para o esp (semaforo principal)
    estag_pct_id = _kpi_id(data, "estagnadas", aspect="pct_ativas") or "oportunidades_estagnadas_funil_pct_ativas"
    estag_pct = indicadores.get(estag_pct_id, {})
    e_estag = (estag_pct.get("por_especialista", {}) or {}).get(esp, {})
    if e_estag:
        # S1-bug-Estagnacao (2026-05-15): mesmo fix do summary card (linha ~5880).
        # "% pipeline parado" deve ser `realizado` (= qtd_estagnados/qtd_ativas × 100,
        # valor semantico), NAO `pct` (= pct_atingimento da meta).
        qty_estag = e_estag.get("qtd_estagnados", 0)
        qty_ativa = e_estag.get("qtd_ativas", 0)
        pct = e_estag.get("realizado", 0)
        # Fallback: se canonical nao emitir `realizado`, computa manualmente da qty.
        if not pct and qty_ativa:
            pct = (qty_estag / qty_ativa) * 100
        tempo = e_estag.get("tempo_medio_dias", 0)
        sev_color = "var(--error)" if pct >= 60 else "#d18000" if pct >= 30 else "#2e7d32"
        lines.append(
            f'<div style="margin-bottom:8px;"><strong style="color:{sev_color};">{pct:.0f}% pipeline parado</strong> '
            f'({qty_estag}/{qty_ativa} deals · tempo medio {int(tempo)}d).</div>'
        )

    # 2. Top stage com volume estagnado (do esp)
    if dados_n5:
        stage_estag = {}
        for entry in dados_n5.get("indicadores", []):
            if not (entry.get("indicator_id") or "").startswith("oportunidades_estagnadas_funil"):
                continue
            for row in entry.get("data", []):
                if row.get("especialista") == esp and row.get("nivel") == "N2-Especialista":
                    est = row.get("estagio")
                    if est:
                        if est not in stage_estag:
                            stage_estag[est] = {"vol": 0, "qty": 0, "tempo": 0, "n_rows": 0}
                        stage_estag[est]["vol"] += row.get("volume") or 0
                        stage_estag[est]["qty"] += row.get("quantidade") or 0
                        stage_estag[est]["tempo"] += row.get("tempo_medio_dias") or 0
                        stage_estag[est]["n_rows"] += 1
        if stage_estag:
            sorted_st = sorted(stage_estag.items(), key=lambda x: -x[1]["vol"])
            top_st, top_data = sorted_st[0]
            tempo_avg = top_data["tempo"] / top_data["n_rows"] if top_data["n_rows"] else 0
            lines.append(
                f'<div style="margin-bottom:8px;"><strong>Stage critico:</strong> {top_st} '
                f'com {top_data["qty"]} deals · {fmt_brl(top_data["vol"], compact=True)} '
                f'({int(tempo_avg)}d).</div>'
            )

    # 3. Top 2 assessores com mais volume estagnado (alias aplicado).
    # FIX rodada 6 issue 18 — exclui esp_direct + aplica squad whitelist + skip estagio.
    if dados_n5:
        card = data["card"]
        squad_wl = _get_squad_whitelist(esp, card)
        squad_norms = {_normalize_assessor_name(a) for a in squad_wl}
        by_assessor = {}
        for entry in dados_n5.get("indicadores", []):
            if not (entry.get("indicator_id") or "").startswith("oportunidades_estagnadas_funil"):
                continue
            for row in entry.get("data", []):
                if row.get("especialista") != esp or row.get("nivel") != "N5-Assessor":
                    continue
                if row.get("estagio"):
                    continue  # somente totais (evita double-count por estagio)
                qty = row.get("quantidade") or 0
                vol = row.get("volume") or 0
                if qty <= 0:
                    continue
                assessor_raw = row.get("assessor")
                if _is_esp_direct(assessor_raw):
                    continue  # FIX issue 18 — esp_direct nao e "Top assessor"
                label = _resolve_assessor_alias(assessor_raw, card)
                if squad_norms and not _assessor_in_squad(label, squad_norms):
                    continue
                if label not in by_assessor:
                    by_assessor[label] = {"vol": 0, "qty": 0}
                by_assessor[label]["vol"] += vol
                by_assessor[label]["qty"] += qty
        sorted_a = sorted(by_assessor.items(), key=lambda x: -x[1]["vol"])
        top2 = sorted_a[:2]
        if top2:
            lines.append('<div style="margin-bottom:4px;"><strong>Top assessores estagnados:</strong></div>')
            for label, m in top2:
                lines.append(
                    f'<div style="margin-bottom:4px;padding-left:12px;font-size:13px;">{label} '
                    f'· {m["qty"]} deals · {fmt_brl(m["vol"], compact=True)}</div>'
                )

    if not lines:
        return '<span style="color:var(--verde-claro);font-style:italic;">Sem estagnacoes relevantes.</span>'
    return "\n".join(lines)


def _esp_proj_section(data: dict, esp_name: str, ind_id: str, label: str) -> str:
    """2026-05-21: retorna a section .proj-section inteira (open + titulo + barras + close)
    ou string vazia quando Card declara `proj_periodos_por_indicador[ind_id] = []`.

    Substitui a versao wrap (open/close separados) — o titulo hardcoded no template
    ficava fora do wrap, vazando quando a section deveria ser oculta.
    """
    card = data.get("card") or {}
    apresentacao = card.get("apresentacao") or {}
    proj_periodos_map = apresentacao.get("proj_periodos_por_indicador") or {}
    proj_periodos = proj_periodos_map.get(ind_id)
    # Lista vazia explicita = nao projetar = esconder section inteira
    if isinstance(proj_periodos, list) and len(proj_periodos) == 0:
        return ""
    bars = _esp_proj_bars(esp_name, data, ind_id)
    return (
        '<div class="proj-section">'
        f'<div class="proj-section-title">{label}</div>'
        f'{bars}'
        '</div>'
    )


def _esp_proj_label(esp: str, data: dict) -> str:
    """Worst classification of Receita and Volume."""
    indicadores = data["wbr"].get("indicadores", {})
    projecoes = data["wbr"].get("projecoes", {}) or {}
    rec_id = _kpi_id(data, "receita") or "receita_mensal"
    vol_id = _kpi_id(data, "volume")  or "volume_mensal"
    # Tenta CON-legacy (indicadores.n2.classificacao_maio) primeiro
    rec = indicadores.get(rec_id, {}).get("n2", {}).get(esp, {}).get("classificacao_maio")
    vol = indicadores.get(vol_id, {}).get("n2", {}).get(esp, {}).get("classificacao_maio")
    # Fallback SEG-split (projecoes._M0.n2.classificacao)
    if rec is None:
        rec = (projecoes.get(f"{rec_id}_M0", {}).get("n2") or {}).get(esp, {}).get("classificacao", "Possivel")
    if vol is None:
        vol = (projecoes.get(f"{vol_id}_M0", {}).get("n2") or {}).get(esp, {}).get("classificacao", "Possivel")
    order = {"Improvavel": 0, "Possivel": 1, "Provavel": 2}
    # Strip extra annotations like "Provavel (com ressalva: ...)"
    rec_short = rec.split(" (")[0] if isinstance(rec, str) else rec
    vol_short = vol.split(" (")[0] if isinstance(vol, str) else vol
    worst = min([rec_short, vol_short], key=lambda x: order.get(x, 1))
    return worst


def _esp_proj_bars(esp: str, data: dict, ind_id: str) -> str:
    """4 bars: Realizado MTD / Lagging real / Proj M0 / Proj M+1.
    FIX item 8.c: adicionada 4a bar 'Lagging real' usando realizado_competencia_maio
    do WBR data JSON quando disponivel (Consorcios v6.3.0a — base lagging real).
    Refator 2026-05-07: suporta dois schemas:
      - CON-legacy: data['wbr']['indicadores'][ind_id].n2.{esp}.{realizado_mtd, projecao_maio_base, ...}
      - SEG-split:  data['wbr']['projecoes']['{ind_id}_M0|M1'].n2.{esp}.{base, meta_mes, ...}
                    e realizado em data['wbr']['indicadores'][ind_id].n2.{esp}.realizado.
    N-parametrico: detecta automaticamente schema."""
    ind = data["wbr"].get("indicadores", {}).get(ind_id, {})
    e_ind = (ind.get("n2") or {}).get(esp, {})

    # FIX (2026-05-14) Bug Pipeline bars vazias: schema canonical analyst v1.1 e
    # `projecoes.{ind_id}.M0` (nested), NAO `projecoes.{ind_id}_M0` (flat). N2 esp
    # esta em `por_especialista`, NAO em `n2`. Mantemos lookup legacy como fallback
    # para retrocompat com schemas v1.0 aspect-split.
    projecoes = data["wbr"].get("projecoes", {}) or {}
    proj_ind_block = projecoes.get(ind_id, {}) or {}
    proj_m0_block = proj_ind_block.get("M0", {}) or projecoes.get(f"{ind_id}_M0", {})
    proj_m1_block = (proj_ind_block.get("M+1", {}) or proj_ind_block.get("M1", {})
                     or projecoes.get(f"{ind_id}_M1", {})
                     or projecoes.get(f"{ind_id}_M+1", {}))
    e_proj_m0 = ((proj_m0_block.get("por_especialista") or proj_m0_block.get("n2") or {})
                 .get(esp, {}))
    e_proj_m1 = ((proj_m1_block.get("por_especialista") or proj_m1_block.get("n2") or {})
                 .get(esp, {}))

    # Round 9 (2026-05-07): infere parent_indicator (sem sufixo subnivel) para
    # buscar meta no Card e fazer prorata sobre N1 quando WL/RE base ausente.
    parent_ind_id = ind_id
    for suffix in ("_wl", "_re", "_n1"):
        if parent_ind_id.endswith(suffix):
            parent_ind_id = parent_ind_id[: -len(suffix)]
            break
    card = data.get("card") or {}
    # Bloco N1 do mesmo indicador (para prorata cross-esp quando WL ausente).
    # FIX (2026-05-14): schema canonical e `projecoes.{parent_ind_id}.M0` (nested).
    # Quando parent == ind_id, reusa proj_m0_block. Senao busca via parent_ind_id.
    parent_proj_block = (projecoes.get(parent_ind_id, {}) or {}) if parent_ind_id != ind_id else proj_ind_block
    n1_proj_m0_block = (parent_proj_block.get("M0", {})
                        or projecoes.get(f"{parent_ind_id}_n1_M0", {}))
    n1_proj_m1_block = (parent_proj_block.get("M+1", {})
                        or parent_proj_block.get("M1", {})
                        or projecoes.get(f"{parent_ind_id}_n1_M1", {}))

    # Meta M0 e M+1 separadas (Round 9): le Card.metas_ppi para distinguir Maio/Junho.
    # Card override quando declarado, senao canonical.
    meta_card_m0 = _meta_from_card_metas_ppi(card, parent_ind_id, esp=esp, horizon="M0")
    meta_card_m1 = _meta_from_card_metas_ppi(card, parent_ind_id, esp=esp, horizon="M1")
    meta_canonical = (e_proj_m0.get("meta_mes")
                      or e_ind.get("meta_mes")
                      or e_ind.get("meta")
                      or ind.get("meta_mes_corrente")
                      or proj_m0_block.get("meta_mes"))
    meta_m0 = meta_card_m0 if meta_card_m0 is not None else (meta_canonical or 0)
    # FIX 2026-05-26 (Fase 4.5.g consolidating-wbr v1.3): meta_m1 agora tem fallback
    # intermediario via canonical.projecoes.{ind}.M+1.por_especialista.{esp}.meta_mes
    # antes de cair em meta_m0. Resolve display incorreto onde Junho herdava meta Maio
    # quando Card.metas_ppi nao declara valor_proximo_mes. Generico para todas verticais.
    meta_canonical_m1 = (e_proj_m1.get("meta_mes")
                          or n1_proj_m1_block.get("meta_mes"))
    meta_m1 = (meta_card_m1
                if meta_card_m1 is not None
                else (meta_canonical_m1 if meta_canonical_m1 is not None else (meta_m0 or 0)))
    meta_mes = meta_m0  # alias para preservar codigo legado abaixo

    # Realizado MTD: indicadores.n2.realizado_mtd (CON) → realizado (SEG)
    real_mtd = e_ind.get("realizado_mtd")
    if real_mtd is None:
        real_mtd = e_ind.get("realizado") or 0

    # Lagging field (CON) — detecta automaticamente via prefixo "lagging_competencia_" ou "realizado_competencia_"
    lagging_m0 = None
    for k, v in e_ind.items():
        if isinstance(k, str) and v is not None and isinstance(v, (int, float)):
            if "lagging_competencia" in k or "realizado_competencia" in k:
                if "junho" in k.lower():
                    continue  # M+1
                if lagging_m0 is None or v > lagging_m0:
                    lagging_m0 = v

    # Proj M0 / M+1: prefer SEG projecoes (WL especifico), fallback CON fields,
    # fallback final = prorata sobre N1 via share da meta do Card (Round 9).
    proj_m0 = e_proj_m0.get("base") if e_proj_m0 else None
    if proj_m0 is None:
        proj_m0 = e_ind.get("projecao_maio_base") or e_ind.get("projecao_mes_corrente")
    proj_m1 = e_proj_m1.get("base") if e_proj_m1 else None
    if proj_m1 is None:
        proj_m1 = e_ind.get("projecao_junho_base") or e_ind.get("projecao_mes_seguinte")

    # Round 9 prorata: quando WL especifico ausente, distribuir N1 pelo share da
    # meta declarada no Card (esp / total). Sinaliza com flag _is_prorata para o
    # render adicionar marker visual "(prorata)".
    proj_m0_is_prorata = False
    proj_m1_is_prorata = False
    n1_base_m0 = n1_proj_m0_block.get("base")
    n1_base_m1 = n1_proj_m1_block.get("base")
    if proj_m0 is None and isinstance(n1_base_m0, (int, float)):
        total_meta_m0 = _meta_from_card_metas_ppi(card, parent_ind_id, horizon="M0")
        if isinstance(meta_card_m0, (int, float)) and isinstance(total_meta_m0, (int, float)) and total_meta_m0:
            share_m0 = meta_card_m0 / total_meta_m0
            proj_m0 = n1_base_m0 * share_m0
            proj_m0_is_prorata = True
    if proj_m1 is None and isinstance(n1_base_m1, (int, float)):
        total_meta_m1 = _meta_from_card_metas_ppi(card, parent_ind_id, horizon="M1")
        if isinstance(meta_card_m1, (int, float)) and isinstance(total_meta_m1, (int, float)) and total_meta_m1:
            share_m1 = meta_card_m1 / total_meta_m1
            proj_m1 = n1_base_m1 * share_m1
            proj_m1_is_prorata = True

    # Normalize widths
    candidates = [v for v in (real_mtd, lagging_m0, proj_m0, proj_m1, meta_mes) if isinstance(v, (int, float))]
    max_v = max(candidates) if candidates else 1
    def _w(v):
        if v is None or not isinstance(v, (int, float)):
            return 0
        return min(100, (v / max_v) * 100) if max_v else 0
    def _color(v):
        if v is None or not isinstance(v, (int, float)) or not meta_mes:
            return "var(--verde-caqui)"
        pct = (v / meta_mes) * 100
        return "var(--success)" if pct >= 100 else "#d18000" if pct >= 80 else "var(--error)"

    # FIX img11 — colapsar Realizado MTD + Lagging real em 1 bar 'Realizado'
    # Quando MTD=0 e ha lagging, mostrar lagging (e o que ja entrou de fato)
    # Quando MTD>0 e lagging=None, mostrar MTD
    # Quando ambos existem e MTD>0: mostrar max(MTD, lagging) — lagging tipicamente >= MTD
    realizado_consolidado = None
    if isinstance(real_mtd, (int, float)) and real_mtd > 0:
        realizado_consolidado = real_mtd
        if isinstance(lagging_m0, (int, float)) and lagging_m0 > real_mtd:
            realizado_consolidado = lagging_m0  # lagging maior = inclui historico
    elif isinstance(lagging_m0, (int, float)) and lagging_m0 > 0:
        realizado_consolidado = lagging_m0
    else:
        realizado_consolidado = real_mtd  # 0 mesmo

    # R5-7 (2026-05-07): sempre renderizar 3 linhas (Realizado/M0/M+1) — quando
    # dado ausente, label exibe "—".
    #
    # Edit #31 (2026-05-13): Card declara `apresentacao.proj_periodos_por_indicador[ind_id]`
    # com lista de horizontes a exibir (subset de {"M0", "M+1"}). Default: ["M0", "M+1"]
    # para retrocompatibilidade. Quando lista vazia [], renderiza apenas Realizado
    # (caso Seg RE Receita — sem metodo calibrado de projecao).
    #
    # Lookup: usa ind_id (sufixado, ex: receita_seguros_mensal_wl) primeiro, fallback
    # para parent_ind_id (receita_seguros_mensal) — Card declara no nivel parent.
    apresentacao = (card.get("apresentacao") or {}) if card else {}
    proj_periodos_map = apresentacao.get("proj_periodos_por_indicador") or {}
    proj_periodos = proj_periodos_map.get(ind_id)
    if proj_periodos is None:
        proj_periodos = proj_periodos_map.get(parent_ind_id)
    if proj_periodos is None:
        proj_periodos = ["M0", "M+1"]  # default: comportamento legado
    proj_periodos_set = set(p.upper().replace("MAIS", "+").replace("MENOS", "-")
                              for p in proj_periodos if p)

    # Round 9: cada linha tem sua propria meta (Realizado/M0 usam meta_m0, M+1 usa meta_m1)
    # e flag _is_prorata para sinalizar valores derivados.
    bars = [("Realizado", realizado_consolidado, meta_m0, False)]
    if "M0" in proj_periodos_set:
        bars.append(("Proj. M0", proj_m0, meta_m0, proj_m0_is_prorata))
    if "M+1" in proj_periodos_set:
        bars.append(("Proj. M+1", proj_m1, meta_m1, proj_m1_is_prorata))

    rows = []
    for label, v, line_meta, is_prorata in bars:
        v_str = fmt_brl(v, compact=True) if v is not None else "—"
        meta_line_str = (fmt_brl(line_meta, compact=True)
                          if isinstance(line_meta, (int, float)) and line_meta else "—")
        if v is None or not isinstance(v, (int, float)):
            fill_w = 0
            fill_color = "var(--verde-caqui)"
        elif not isinstance(line_meta, (int, float)) or not line_meta:
            # 2026-05-21: quando meta ausente, usar width PROPORCIONAL ao max das 3 barras
            # (helper _w computa v/max_v*100 ja calculado em linha 6997-7001).
            # Cor neutra (verde-caqui) — sem semaforo possivel sem meta.
            fill_w = _w(v)
            fill_color = "var(--verde-caqui)"
        else:
            pct_line = (v / line_meta) * 100
            fill_w = min(100, pct_line)
            fill_color = "var(--success)" if pct_line >= 100 else "#d18000" if pct_line >= 80 else "var(--error)"
        prorata_marker = (' <span style="font-size:9px;color:var(--verde-claro);font-style:italic;">(prorata)</span>'
                           if is_prorata else "")
        # Refator 2026-05-07 round 3: label "Realizado · R$ 0" em UMA linha (com `·` separador).
        rows.append(
            f'<div class="proj-row">'
            f'<div class="lbl">'
            f'<strong style="display:inline;">{label}</strong>'
            f'<span style="color:var(--verde-caqui);font-weight:600;font-variant-numeric:tabular-nums;margin-left:6px;">· {v_str}</span>'
            f'{prorata_marker}'
            f'</div>'
            f'<div class="track" title="Track = meta {meta_line_str}; fill = {v_str} ({fill_w:.0f}% meta)">'
            f'<div class="fill" style="width:{fill_w:.1f}%; background:{fill_color};"></div></div>'
            f'<div class="v" title="Meta do indicador">meta {meta_line_str}</div>'
            f'</div>'
        )
    return "\n".join(rows)


def _esp_proj_nota(esp: str, data: dict) -> str:
    """Short note about meta/gap. N-parametrico: suporta CON-legacy
    (indicadores.n2.{esp}.projecao_*) e SEG-split (projecoes.{ind_id}_M0.n2.{esp}.base)."""
    indicadores = data["wbr"].get("indicadores", {})
    projecoes = data["wbr"].get("projecoes", {}) or {}
    rec_id = _kpi_id(data, "receita") or "receita_mensal"
    vol_id = _kpi_id(data, "volume")  or "volume_mensal"
    rec = indicadores.get(rec_id, {})
    vol = indicadores.get(vol_id, {})
    e_rec = rec.get("n2", {}).get(esp, {})
    e_vol = vol.get("n2", {}).get(esp, {})
    # Tentar projecoes SEG schema
    e_rec_proj = (projecoes.get(f"{rec_id}_M0", {}).get("n2") or {}).get(esp, {})
    e_vol_proj = (projecoes.get(f"{vol_id}_M0", {}).get("n2") or {}).get(esp, {})
    parts = []
    # Receita
    meta_r = (e_rec_proj.get("meta_mes")
              or e_rec.get("meta_mes")
              or e_rec.get("meta")
              or rec.get("meta_mes_corrente"))
    proj_r = (e_rec_proj.get("base")
              or e_rec.get("projecao_maio_base")
              or e_rec.get("projecao_mes_corrente"))
    if meta_r and proj_r:
        gap = proj_r - meta_r
        sig = "+" if gap >= 0 else ""
        parts.append(f"Receita: meta {fmt_brl(meta_r, compact=True)} · proj {sig}{fmt_brl(gap, compact=True)}")
    # Volume
    meta_v = (e_vol_proj.get("meta_mes")
              or e_vol.get("meta_mes")
              or e_vol.get("meta")
              or vol.get("meta_mes_corrente"))
    proj_v = (e_vol_proj.get("base")
              or e_vol.get("projecao_maio_base")
              or e_vol.get("projecao_mes_corrente"))
    if meta_v and proj_v:
        gap = proj_v - meta_v
        sig = "+" if gap >= 0 else ""
        parts.append(f"Volume: meta {fmt_brl(meta_v, compact=True)} · proj {sig}{fmt_brl(gap, compact=True)}")
    return ". ".join(parts) if parts else todo_block(f"Projecao nota {esp}")


# ============================================================
# Renderers — Consolidado + Encerramento
# ============================================================

def render_consolidado_encerramento(data: dict, ctx: dict) -> dict:
    wbr = data["wbr"]
    indicadores = wbr.get("indicadores", {})
    nivel = ctx["NIVEL"]
    esp_list = ctx["_esp_list"]

    # 3 KPI tiles N3: Receita, Volume, Estagnadas %
    # Refator 2026-05-07: prefer ID com sufixo subnivel (SEG split) sobre busca generica.
    card = data.get("card") or {}
    subnivel = (card.get("metadata") or {}).get("subnivel")

    def _resolve_with_subnivel(kind: str):
        """Tenta primeiro com sufixo subnivel (SEG split), fallback para generic."""
        ind_id = _resolve_kpi_id(indicadores, kind, subnivel=subnivel)
        if ind_id and ind_id in indicadores:
            return indicadores[ind_id]
        # fallback genericooo
        return _resolve_indicator(indicadores, [kind + "_"]) or {}

    rec = _resolve_with_subnivel("receita")
    vol = _resolve_with_subnivel("volume")
    # Estagnadas: prefer pct_ativas
    estag_id = _resolve_kpi_id(indicadores, "estagnadas", subnivel=subnivel, aspect="pct_ativas")
    estag = indicadores.get(estag_id, {}) if estag_id else (
        _resolve_indicator(indicadores, ["estagnada"]) or indicadores.get("oportunidades_estagnadas_funil_pct_ativas", {})
    )

    def _v_or_fallback(d, *keys):
        """Retorna o primeiro valor non-None entre as keys."""
        for k in keys:
            v = (d or {}).get(k)
            if v is not None:
                return v
        return None

    def _meta_with_card_fallback(ind_entry, parent_kind):
        """Resolve meta de top-level com fallback para Card.metas_ppi."""
        meta_v = _v_or_fallback(ind_entry, "meta_mes_corrente", "meta")
        if meta_v is None:
            meta_v = _meta_from_card_metas_ppi(card, f"{parent_kind}_seguros_mensal" if parent_kind in ("receita","volume","quantidade") else None)
        return meta_v

    def _tile(label, real, meta_v, status, unidade="BRL"):
        cls = status_to_class(status)
        if unidade == "BRL":
            v_str = fmt_brl(real, compact=True)
        elif unidade == "pct":
            v_str = fmt_pct(real, 1)
        else:
            v_str = fmt_int(real)
        pct = (real / meta_v * 100) if (meta_v and isinstance(real, (int, float))) else 0
        return (
            f'<div class="kpi-tile"><div class="v {cls}">{v_str}</div>'
            f'<div class="l">{label} · {fmt_pct(pct, 0)} meta</div></div>'
        )

    rec_real = _v_or_fallback(rec, "realizado_mtd", "realizado") or 0
    rec_meta = _meta_with_card_fallback(rec, "receita")
    vol_real = _v_or_fallback(vol, "realizado_mtd", "realizado") or 0
    vol_meta = _meta_with_card_fallback(vol, "volume")
    estag_real = _v_or_fallback(estag, "realizado_mtd", "realizado") or 0
    estag_meta = _v_or_fallback(estag, "meta") or 40

    n3_tiles = "\n".join([
        _tile("Receita N3", rec_real, rec_meta, rec.get("status")),
        _tile("Volume N3", vol_real, vol_meta, vol.get("status")),
        _tile("Estagnadas %", estag_real, estag_meta, estag.get("status"), unidade="pct"),
    ])

    # Bars per direto (Receita)
    n3_bars = []
    for esp in esp_list:
        e = rec.get("n2", {}).get(esp, {})
        meta_e = _v_or_fallback(e, "meta_mes", "meta") or 0
        real_e = _v_or_fallback(e, "realizado_mtd", "realizado") or 0
        # Fallback Card.metas_ppi.por_especialista
        if not meta_e:
            meta_e = _meta_from_card_metas_ppi(card, "receita_seguros_mensal", esp=esp) or 0
        pct = (real_e / meta_e * 100) if meta_e else 0
        cls = "good" if pct >= 100 else "warn" if pct >= 70 else "bad"
        n3_bars.append(
            f'<div class="bar-row" style="display:grid;grid-template-columns:140px 1fr 100px;gap:12px;align-items:center;">'
            f'<div>{esp}</div>'
            f'<div class="seg-track" style="background:#f0f0eb;height:22px;border-radius:3px;">'
            f'<div class="seg fill-{cls}" style="height:100%;width:{min(100, pct):.1f}%;background:var(--{"success" if cls == "good" else "warning" if cls == "warn" else "error"});border-radius:3px;color:#fff;text-align:right;padding-right:6px;font-size:12px;line-height:22px;">{fmt_pct(pct, 0)}</div>'
            f'</div>'
            f'<div style="font-size:12px;text-align:right;">{fmt_brl(real_e, compact=True)} / {fmt_brl(meta_e, compact=True)}</div>'
            f'</div>'
        )

    # C7 + F3 (2026-05-07): SEMPRE adiciona barra "Sem Especialista" cinza (sem
    # meta) — destaca bridge gap mesmo quando realizado=0. F3 alinhamento com
    # spec do usuario: "onde está a barra de sem especialista cinza?".
    sem_esp = rec.get("n2", {}).get("Sem Especialista", {})
    sem_esp_real = sem_esp.get("realizado_mtd") or 0
    sem_esp_label = fmt_brl(sem_esp_real, compact=True) if sem_esp_real > 0 else "R$ 0"
    n3_bars.append(
        f'<div class="bar-row" style="display:grid;grid-template-columns:140px 1fr 100px;gap:12px;align-items:center;color:var(--verde-claro);">'
        f'<div style="font-style:italic;">Sem Especialista</div>'
        f'<div class="seg-track" style="background:#f0f0eb;height:22px;border-radius:3px;">'
        f'<div style="height:100%;width:100%;background:var(--vc-200);border-radius:3px;text-align:right;padding-right:6px;font-size:12px;line-height:22px;color:var(--verde-claro);font-style:italic;">sem meta atribuida</div>'
        f'</div>'
        f'<div style="font-size:12px;text-align:right;">{sem_esp_label}</div>'
        f'</div>'
    )

    # Q1 (2026-05-07): linha "M7 consolidado" mostra APENAS realizado MTD vs
    # meta (sem proj inline). Projecao foi movida para 2 cards dedicados na
    # linha 2 do slide (N3_PROJECAO_VOLUME + N3_PROJECAO_RECEITA).
    cn1 = rec.get("consolidado_n1") or {}
    meta_n1 = (cn1.get("meta_mes") or _v_or_fallback(rec, "meta_mes_corrente", "meta")
               or rec_meta or 0)
    real_n1 = (cn1.get("realizado_mtd") or _v_or_fallback(rec, "realizado_mtd", "realizado")
               or rec_real or 0)
    pct_n1 = (real_n1 / meta_n1 * 100) if meta_n1 else 0
    cls_n1 = "good" if pct_n1 >= 100 else "warn" if pct_n1 >= 70 else "bad"

    n3_bars.append(
        f'<div class="bar-row" style="display:grid;grid-template-columns:140px 1fr 100px;gap:12px;align-items:center;font-weight:500;border-top:2px solid var(--vc-200);padding-top:10px;margin-top:6px;">'
        f'<div>M7 consolidado</div>'
        f'<div class="seg-track" style="background:#f0f0eb;height:22px;border-radius:3px;">'
        f'<div class="seg fill-{cls_n1}" style="height:100%;width:{min(100, pct_n1):.1f}%;background:var(--{"success" if cls_n1 == "good" else "warning" if cls_n1 == "warn" else "error"});border-radius:3px;color:#fff;text-align:right;padding-right:6px;font-size:12px;line-height:22px;">{fmt_pct(pct_n1, 0)}</div>'
        f'</div>'
        f'<div style="font-size:12px;text-align:right;line-height:1.3;">{fmt_brl(real_n1, compact=True)} / {fmt_brl(meta_n1, compact=True)}</div>'
        f'</div>'
    )

    # FIX rodada 7 issue 9 — suppress filter via Card.apresentacao.suppress_in_ritual
    suppress_cfg = (data.get("card", {}).get("apresentacao") or {}).get("suppress_in_ritual") or {}
    def _suppressed(text: str, key: str) -> bool:
        kws = suppress_cfg.get(key) or []
        if not kws or not text:
            return False
        text_lc = str(text).lower()
        return any(kw.lower() in text_lc for kw in kws)

    # Top 3 riscos: prepend Card.apresentacao.anomalias_custom + filtra suppress
    # FIX rodada 7.6 — anomalias_custom: usuario declara riscos sob medida no Card
    # que aparecem ANTES dos riscos do WBR. N-parametrico.
    custom_anomalias = (data.get("card", {}).get("apresentacao") or {}).get("anomalias_custom") or []
    anomalias_all = list(custom_anomalias) + (wbr.get("anomalias", []) or [])
    anomalias_filtered = [
        a for a in anomalias_all
        if not _suppressed(a.get("descricao", ""), "anomalias")
        and not _suppressed(a.get("acao", ""), "anomalias")
    ]
    anomalias = anomalias_filtered[:3]
    riscos = "\n".join([
        f'<div class="risk-item" style="border-left:3px solid var(--error);padding-left:10px;font-size:13px;line-height:1.4;">'
        f'<strong>{a.get("descricao", "—")[:120]}{"…" if len(a.get("descricao", "")) > 120 else ""}</strong> '
        f'<span style="color:var(--verde-claro);">— {a.get("acao", "—")}</span>'
        f'</div>'
        for a in anomalias
    ])

    # Sinais positivos: prepend Card.apresentacao.destaques_positivos_custom + filtra suppress
    # FIX rodada 7.5 — destaques_positivos_custom: usuario declara destaques sob medida
    # no Card que aparecem ANTES dos destaques do WBR. N-parametrico.
    custom_destaques = (data.get("card", {}).get("apresentacao") or {}).get("destaques_positivos_custom") or []
    destaques_all = list(custom_destaques) + (wbr.get("destaques_positivos", []) or [])
    destaques_filtered = [
        d for d in destaques_all
        if not _suppressed(d.get("titulo", ""), "destaques_positivos")
        and not _suppressed(d.get("texto", ""), "destaques_positivos")
    ]
    destaques = destaques_filtered[:3]
    sinais = "\n".join([
        f'<div class="risk-item" style="border-left:3px solid #4caf50;padding-left:10px;font-size:13px;line-height:1.4;">'
        f'<strong>{d.get("titulo", "—")}</strong> '
        f'<span style="color:var(--verde-claro);">— {d.get("texto", "")[:140]}</span>'
        f'</div>'
        for d in destaques
    ])

    # Encerramento next-cards: prepend Card.apresentacao.recomendacoes_custom +
    # filtra wbr.recomendacoes (alta -> media como fallback) + suppress.
    # FIX rodada 7.9 — recomendacoes_custom: items sob medida prepended ao Slide 12
    # FIX #10 (2026-05-14): garantir 3 next-cards. Antes filtrava por _suppressed em
    # r.get("texto") — mas WBR canonical v1.1 usa key "titulo" (nao "texto"), entao todas
    # as recs viravam empty -> filtradas -> deck ficava com 0-1 cards quando custom era 1.
    # Agora: (a) le titulo/texto com fallback; (b) suppress soh aciona se titulo+texto vazios;
    # (c) extende para prioridade=media quando alta < 3 (garante 3 cards quando possivel).
    def _rec_get(r, *keys):
        """Le valor da primeira key existente. Util para schema heterogeneo
        (custom_rec usa 'texto'/'owner'/'prazo'; analyst v1.1 emite 'titulo'/'owner_sugerido'/'due_date')."""
        for k in keys:
            v = (r or {}).get(k)
            if v:
                return v
        return ""

    custom_recs = (data.get("card", {}).get("apresentacao") or {}).get("recomendacoes_custom") or []
    all_wbr_recs = wbr.get("recomendacoes", []) or []
    wbr_recs_alta = [r for r in all_wbr_recs if r.get("prioridade") == "alta"]
    wbr_recs_media = [r for r in all_wbr_recs if r.get("prioridade") == "media"]
    wbr_recs_outras = [r for r in all_wbr_recs if r.get("prioridade") not in ("alta", "media")]
    recs_all = list(custom_recs) + wbr_recs_alta + wbr_recs_media + wbr_recs_outras
    recs = [
        r for r in recs_all
        if (_rec_get(r, "titulo", "texto", "descricao")
            and not _suppressed(_rec_get(r, "titulo", "texto"), "recomendacoes"))
    ][:3]
    next_cards = []
    for i, r in enumerate(recs, start=1):
        titulo = _rec_get(r, "titulo", "texto", "descricao") or "—"
        owner = _rec_get(r, "owner", "owner_sugerido", "responsavel") or "—"
        prazo = _rec_get(r, "prazo", "due_date") or "—"
        # Normalizar prazo ISO -> YYYY-MM-DD
        if isinstance(prazo, str) and len(prazo) > 10 and prazo[10] in ("T", " "):
            prazo = prazo[:10]
        next_cards.append(
            f'<div class="next-card">'
            f'<div class="nc-num">{i:02d}</div>'
            f'<div class="nc-title">{titulo}</div>'
            f'<div class="nc-meta">Owner: {owner} · Prazo: {prazo}</div>'
            f'<div class="nc-risk"><em>Sem decisão → projeção do ciclo segue exposta a esse risco.</em></div>'
            f'</div>'
        )
    enc_intro = f"Decisões que precisam sair do ritual antes do fechamento de {ctx['DATA_FECHAMENTO']}."

    # Q2 (2026-05-07): cards de Projeção M7 consolidado (Volume + Receita)
    # com 3 linhas: Realizado MTD / Proj M0 / Proj M+1.
    # Refator 2026-05-07: passa data para suportar SEG schema (projecoes.{ind_id}_M0/M1).
    proj_volume_html = _render_n3_projecao_card(vol, "Volume", unidade="BRL", data=data, kind="volume")
    proj_receita_html = _render_n3_projecao_card(rec, "Receita", unidade="BRL", data=data, kind="receita")

    # REDESIGN (2026-05-14): Consolidado N3 reestrutura para 3 velocimetros (paridade
    # design PJ2 image 3 contrato). Layout: 01 Receita Esp1 | 02 Receita Esp2 | 03 Total.
    # Substitui o layout antigo (KPI tiles + barras + riscos + sinais + projecoes).
    # Riscos analiticos passam a viver no Dashboard per esp (_esp_riscos), Conclusao
    # foca em projecao M0 da Receita por especialista — o card de fechamento do mes.

    def _receita_breakdown_for_esp(esp: str) -> dict:
        """Extrai realizado MTD + meta + projecao M0 da Receita para um especialista.

        Tenta varias fontes (analyst v1.1, Card.metas_ppi.por_especialista,
        Card.apresentacao.projection_overrides) e cai em defaults sensatos. Retorna
        {real, meta, proj_m0, pct}."""
        rec_n2 = (rec.get("n2") or rec.get("por_especialista") or {}).get(esp, {}) or {}
        real_v = _v_or_fallback(rec_n2, "realizado_mtd", "realizado", "valor") or 0
        meta_v = _v_or_fallback(rec_n2, "meta", "meta_mes_corrente", "meta_mes") or 0

        # Fallback meta: Card.metas_ppi.receita.por_especialista.{esp}
        if not meta_v:
            rec_id = next((k for k in indicadores.keys() if str(k).startswith("receita")), "")
            metas_ppi = card.get("metas_ppi", {}) or {}
            por_esp = ((metas_ppi.get(rec_id) or {}).get("por_especialista") or {}).get(esp, {})
            meta_v = por_esp.get("valor") or por_esp.get("meta") or 0

        # Projecao M0 — busca em ORDEM (Card override = SoT do gestor; analyst = fallback):
        # 1. Card.apresentacao.projection_overrides.indicadores.{ind}.n2.{esp}.projecao_mes_corrente
        #    (estrutura canonica documentada em SKILL.md projecting-results; metodo 'a' do
        #    GPD/Falconi). Card override existe quando o coordenador corrigiu numeros stale do JSON.
        # 2. WBR.projecoes.{ind}.M0.por_especialista.{esp}.base (analyst v1.1)
        # 3. WBR.projecoes.{ind}.n2.{esp}.M0.base (esquema alternativo)
        # 4. Split proporcional do N1
        # 5. Fallback final: realizado MTD
        rec_id = next((k for k in indicadores.keys() if str(k).startswith("receita")), "")
        proj_m0 = None
        proj_overrides_root = (card.get("apresentacao", {}) or {}).get("projection_overrides", {}) or {}
        # Suporta dois shapes do Card:
        #   Novo (Cons v2.7.0+): projection_overrides.indicadores.{ind}.n2.{esp}.projecao_mes_corrente
        #   Antigo/alternativo: projection_overrides.{ind}.n2.{esp}.M0
        ov_inds = proj_overrides_root.get("indicadores") or {}
        ov_ind = ov_inds.get(rec_id) or proj_overrides_root.get(rec_id) or {}
        if ov_ind:
            ov_esp = ((ov_ind.get("n2") or {}).get(esp) or {})
            proj_m0 = (
                ov_esp.get("projecao_mes_corrente")
                or ov_esp.get("M0")
                or ov_esp.get("projecao_m0")
                or ov_esp.get("base")
            )
        if proj_m0 is None:
            # FIX (2026-05-14): caminho canonico analyst v1.1 — projecoes.{X}.M0.por_especialista.{esp}.base
            wbr_proj = ((wbr.get("projecoes") or {}).get(rec_id) or {})
            wbr_proj_m0 = wbr_proj.get("M0") or {}
            por_esp = (wbr_proj_m0.get("por_especialista") or {}).get(esp, {}) or {}
            proj_m0 = por_esp.get("base") or por_esp.get("valor") or por_esp.get("projecao")
            # Caminho alternativo legado
            if proj_m0 is None:
                proj_n2 = ((wbr_proj.get("n2") or {}).get(esp) or {})
                if isinstance(proj_n2.get("M0"), (int, float)):
                    proj_m0 = proj_n2["M0"]
                elif isinstance(proj_n2.get("M0"), dict):
                    proj_m0 = proj_n2["M0"].get("base") or proj_n2["M0"].get("valor")
        # Split proporcional: real_esp share da N1 aplicada a proj_N1
        if proj_m0 is None:
            wbr_proj = ((wbr.get("projecoes") or {}).get(rec_id) or {})
            wbr_proj_m0_obj = wbr_proj.get("M0") or {}
            proj_n1 = wbr_proj_m0_obj.get("base") if isinstance(wbr_proj_m0_obj, dict) else wbr_proj_m0_obj
            real_n1 = _v_or_fallback(rec, "realizado_mtd", "realizado") or 0
            if isinstance(proj_n1, (int, float)) and isinstance(real_n1, (int, float)) and real_n1 > 0 and real_v:
                proj_m0 = proj_n1 * (real_v / real_n1)
        # Ultimo fallback: realizado MTD
        if proj_m0 is None:
            proj_m0 = real_v

        try:
            real_v = float(real_v or 0)
            meta_v = float(meta_v or 0)
            proj_m0 = float(proj_m0 or 0)
        except (TypeError, ValueError):
            real_v = meta_v = proj_m0 = 0
        pct = (proj_m0 / meta_v * 100) if meta_v else 0
        return {"real": real_v, "meta": meta_v, "proj_m0": proj_m0, "pct": pct}

    def _gauge_color(pct: float) -> str:
        if pct >= 95:
            return "#4caf50"
        if pct >= 80:
            return "#ffb300"
        return "#e40014"

    def _clean_arc_svg(pct: float, cor: str) -> str:
        """SVG arco semi-circular limpo (sem labels de realizado/meta/% inside).
        % aparece no overlay externo .veloc-pct.

        FIX (2026-05-14) Bug gauge fill realizado-not-projection: _gauge_svg renderizava
        labels de 'realizado' inline que confundiam o usuario (parecia que o fill estava
        usando o numero do realizado). Esta versao soh desenha o arco com base em pct
        diretamente, sem texts inline."""
        import math
        cx, cy, r = 100, 100, 80
        pct_clamped = max(0.0, min(pct / 100, 1.5))
        angle_deg = pct_clamped * 180
        angle_rad = math.radians(180 - angle_deg)
        end_x = cx + r * math.cos(angle_rad)
        end_y = cy - r * math.sin(angle_rad)
        large_arc = 1 if angle_deg > 180 else 0
        return (
            f'<svg viewBox="0 0 200 120" xmlns="http://www.w3.org/2000/svg" '
            f'class="veloc-gauge gauge-svg" preserveAspectRatio="xMidYMid meet">'
            f'<path d="M {cx-r} {cy} A {r} {r} 0 0 1 {cx+r} {cy}" '
            f'fill="none" stroke="#d0d0cc" stroke-width="14" stroke-linecap="butt"/>'
            f'<path d="M {cx-r} {cy} A {r} {r} 0 {large_arc} 1 {end_x:.2f} {end_y:.2f}" '
            f'fill="none" stroke="{cor}" stroke-width="14" stroke-linecap="butt"/>'
            f'</svg>'
        )

    def _veloc_card(idx: int, label: str, sublabel: str, real_v: float, meta_v: float, proj_v: float, pct: float) -> str:
        # P3.2 follow-up (2026-06-18): quando NAO ha meta (ex: Seg RE, que ainda nao
        # tem meta), renderiza estado INFORMATIVO ("sem meta") em vez de "0%" + "R$ 0"
        # — que parecia 0% de atingimento. Coerente com receita RE = projetar
        # informativo sem classificacao. Arco neutro, sem pct.
        sem_meta = not isinstance(meta_v, (int, float)) or meta_v <= 0
        cor = "var(--vc-300)" if sem_meta else _gauge_color(pct)
        # FIX (2026-05-14): arco renderiza pct = proj_v/meta_v (a projecao M0), nao
        # realizado/meta. % no overlay e a mesma. Usa _clean_arc_svg (sem labels
        # internos que confundiam o usuario).
        svg = _clean_arc_svg(0 if sem_meta else pct, cor)
        pct_html = (
            '<div class="veloc-pct" style="color:var(--vc-300);font-style:italic;font-size:13px;line-height:1.1;">sem meta</div>'
            if sem_meta else
            f'<div class="veloc-pct" style="color:{cor};">{int(pct)}<span class="pct-mark">%</span></div>'
        )
        meta_val_html = "sem meta" if sem_meta else fmt_brl(meta_v, compact=True)
        return (
            f'<div class="veloc">'
            f'<div class="veloc-num">{idx:02d}</div>'
            f'<div class="veloc-head">'
            f'<div class="veloc-lbl">{label}</div>'
            f'<div class="veloc-sub">{sublabel}</div>'
            f'</div>'
            f'<div class="veloc-gauge-wrap">{svg}'
            f'{pct_html}'
            f'</div>'
            f'<div class="veloc-vals">'
            f'<div class="veloc-side veloc-real"><div class="vside-lbl">Projeção M0</div><div class="vside-val">{fmt_brl(proj_v, compact=True)}</div></div>'
            f'<div class="veloc-side veloc-meta"><div class="vside-lbl">Meta M0</div><div class="vside-val">{meta_val_html}</div></div>'
            f'</div>'
            f'<div class="veloc-proj">Realizado MTD · <strong>{fmt_brl(real_v, compact=True)}</strong></div>'
            f'</div>'
        )

    def _esp_sublabel(esp_idx: int) -> str:
        """Sublabel deriva do squad do esp (primeiros 2 grupos) ou usa fallback."""
        resp_card = ((card.get("apresentacao") or {}).get("responsaveis") or [])
        if esp_idx < len(resp_card):
            sub = resp_card[esp_idx].get("sublabel")
            if sub:
                return sub
            sq = resp_card[esp_idx].get("squad") or []
            if sq:
                return f"Squad · {len(sq)} assessores"
        return f"Especialista · {esp_idx + 1}"

    esp1 = esp_list[0] if esp_list else ""
    esp2 = esp_list[1] if len(esp_list) > 1 else ""

    # FIX: caso single-esp (raro em N3), card 02 fica como "sem segundo especialista"
    if esp1 and esp2:
        d1 = _receita_breakdown_for_esp(esp1)
        d2 = _receita_breakdown_for_esp(esp2)
    elif esp1:
        d1 = _receita_breakdown_for_esp(esp1)
        d2 = {"real": 0, "meta": 0, "proj_m0": 0, "pct": 0}
    else:
        d1 = d2 = {"real": 0, "meta": 0, "proj_m0": 0, "pct": 0}

    # Total: preferir N1 do Card override, fallback analyst, fallback sum dos esps
    total_real = _v_or_fallback(rec, "realizado_mtd", "realizado", "valor") or (d1["real"] + d2["real"])
    total_meta = _v_or_fallback(rec, "meta", "meta_mes_corrente", "meta_mes") or (d1["meta"] + d2["meta"])
    rec_id = next((k for k in indicadores.keys() if str(k).startswith("receita")), "")
    # FIX (2026-05-14) Bug 8: quando dados_consolidados disponivel, prefer N1 raw
    # (Total M7 — inclui bridge Sem Especialista) sobre WBR canonical (WL squad
    # subset). Mesma semantica do Matriz N3 — meta R$ 135K (cache WL) substituida
    # por R$ 216K (raw N1 component '285' Total M7) quando o bridge esta presente.
    # P3.2 (2026-06-18): RE NAO entra nesse override. O raw N1 de SEG via componente
    # '285' e o ESCRITORIO M7 inteiro (R$ 216K) — para o consolidado RE isso e o bug
    # recorrente (velocimetro mostrava a meta do escritorio em vez da meta RE). RE
    # tem CH zerado (Emmanuel/Samuel nao cadastrados) entao o raw so traz bleed
    # office-wide. Aposenta o patch manual por ciclo: RE confia na meta canonical.
    _subnivel_veloc = ((card.get("metadata") or {}).get("subnivel") or "").lower()
    if rec_id and data.get("dados_consolidados") and _subnivel_veloc == "re":
        print(f"[build_deck] velocimetro Total RE: usando meta canonical "
              f"({total_meta}) — raw N1 office-wide ignorado (P3.2)", file=sys.stderr)
    if rec_id and data.get("dados_consolidados") and _subnivel_veloc != "re":
        synthetic_mr = {"source_indicator": rec_id, "indicator_id": rec_id,
                         "value_field": "realizado", "label": "Receita"}
        raw_real = _derive_n1_raw_from_dados(data, synthetic_mr)
        raw_meta = _derive_n1_raw_from_dados(data, synthetic_mr, field_override="meta")
        if isinstance(raw_real, (int, float)) and raw_real > 0:
            # Prefer raw quando maior que WBR canonical (evidencia de bridge presente)
            try:
                if raw_real > float(total_real or 0):
                    total_real = raw_real
            except (TypeError, ValueError):
                total_real = raw_real
        if isinstance(raw_meta, (int, float)) and raw_meta > 0:
            try:
                if raw_meta > float(total_meta or 0):
                    total_meta = raw_meta
            except (TypeError, ValueError):
                total_meta = raw_meta
    # FIX (2026-05-14): Total projection prefer Card override N1 (SoT).
    # Card structure: apresentacao.projection_overrides.indicadores.{ind}.n1.projecao_mes_corrente
    proj_overrides_root = (card.get("apresentacao", {}) or {}).get("projection_overrides", {}) or {}
    ov_inds = proj_overrides_root.get("indicadores") or {}
    ov_n1 = ((ov_inds.get(rec_id) or proj_overrides_root.get(rec_id) or {}).get("n1") or {})
    total_proj = ov_n1.get("projecao_mes_corrente") or ov_n1.get("M0") or ov_n1.get("base")
    if total_proj is None:
        wbr_proj_n1 = ((wbr.get("projecoes") or {}).get(rec_id) or {}).get("M0")
        if isinstance(wbr_proj_n1, dict):
            total_proj = wbr_proj_n1.get("base") or wbr_proj_n1.get("valor")
        elif isinstance(wbr_proj_n1, (int, float)):
            total_proj = wbr_proj_n1
    if total_proj is None:
        total_proj = d1["proj_m0"] + d2["proj_m0"]
    try:
        total_real, total_meta, total_proj = float(total_real or 0), float(total_meta or 0), float(total_proj or 0)
    except (TypeError, ValueError):
        total_real = total_meta = total_proj = 0
    # FIX (2026-05-14) Bug 8b: quando total_real reflete N1 raw (inclui bridge Sem
    # Esp) mas total_proj cobre apenas WL squad, o ratio fica subestimado. Ajusta
    # projecao adicionando o bridge ja realizado (assumindo que nao crescera mais
    # ate fim do mes — leitura conservadora) para consistencia:
    #   total_proj_adj = sum_esps_proj + (raw_real - sum_esps_real)
    # Equivale a "esps projetam + bridge fica congelado no MTD".
    sum_esps_real = float(d1["real"] or 0) + float(d2["real"] or 0)
    sum_esps_proj = float(d1["proj_m0"] or 0) + float(d2["proj_m0"] or 0)
    if total_real > 0 and sum_esps_real > 0 and total_real > sum_esps_real * 1.01:
        # Evidencia de bridge: total_real maior que sum dos esps declarados
        bridge_realized = total_real - sum_esps_real
        # Se total_proj atual = sum_esps_proj (analyst), adiciona o bridge realized
        if abs(total_proj - sum_esps_proj) < 1.0 or total_proj <= sum_esps_proj * 1.01:
            total_proj = sum_esps_proj + bridge_realized
    total_pct = (total_proj / total_meta * 100) if total_meta else 0

    vertical_label = ctx.get("VERTICAL", "") or ""
    if vertical_label and vertical_label[0].islower():
        vertical_label = vertical_label.capitalize()

    n3_conc_veloc_esp1 = _veloc_card(
        1, f"Receita {esp1}" if esp1 else "Receita (esp. 1)",
        _esp_sublabel(0) if esp1 else "—",
        d1["real"], d1["meta"], d1["proj_m0"], d1["pct"]
    )
    n3_conc_veloc_esp2 = _veloc_card(
        2, f"Receita {esp2}" if esp2 else "Receita (sem esp. 2)",
        _esp_sublabel(1) if esp2 else "—",
        d2["real"], d2["meta"], d2["proj_m0"], d2["pct"]
    )
    n3_conc_veloc_total = _veloc_card(
        3, "Total · Receita", f"{vertical_label or 'M7'} consolidado",
        total_real, total_meta, total_proj, total_pct
    )

    # Headline tipo "Consorcios projeta 82% da meta de Receita em Maio (M0) — Douglas em 64%, Tereza em 101%."
    mes_nome = "este mês"
    mes_ano_full = ctx.get("MES_ANO") or ""
    if mes_ano_full:
        mes_nome = mes_ano_full.split(" ")[0]
    n3_conc_headline = (
        f"{vertical_label or ctx.get('VERTICAL', 'M7')} projeta "
        f"<strong>{int(total_pct)}% da meta de Receita</strong> em {mes_nome} (M0) — "
        f"{primeiro_nome(esp1) if esp1 else 'Esp. 1'} em <strong>{int(d1['pct'])}%</strong>, "
        f"{primeiro_nome(esp2) if esp2 else 'Esp. 2'} em <strong>{int(d2['pct'])}%</strong>."
    )

    return {
        "N3_CONC_HEADLINE": n3_conc_headline,
        "N3_CONC_VELOC_ESP1": n3_conc_veloc_esp1,
        "N3_CONC_VELOC_ESP2": n3_conc_veloc_esp2,
        "N3_CONC_VELOC_TOTAL": n3_conc_veloc_total,
        # Mantidos para compat se algum outro slide ainda referenciar (no-op no template novo):
        "N3_VELOCIMETROS": "",
        "N3_KPI_TILES": n3_tiles,
        "N3_BARRAS_POR_DIRETO": "\n".join(n3_bars) or '<div style="color:var(--verde-claro);">Sem barras.</div>',
        "N3_TOP_RISCOS": riscos or '<div style="color:var(--verde-claro);">Sem riscos críticos.</div>',
        "N3_SINAIS_POSITIVOS": sinais or '<div style="color:var(--verde-claro);">Sem destaques positivos.</div>',
        "N3_PROJECAO_VOLUME": proj_volume_html,
        "N3_PROJECAO_RECEITA": proj_receita_html,
        "ENC_INTRO": enc_intro,
        "NEXT_CARDS": "\n".join(next_cards) or '<div style="color:var(--off-white);">Sem decisões registradas.</div>',
    }


def _render_n3_projecao_card(ind: dict, label: str, unidade: str = "BRL",
                              data: dict = None, kind: str = None) -> str:
    """Q2 (2026-05-07): card de projecao consolidada M7 com 3 linhas:
    Realizado MTD / Proj. Mes Atual (M0) / Proj. Mes Seguinte (M+1).

    Le de ind.consolidado_n1 (preferido — Fase 6.6 do projecting-results) com
    fallback para meta_mes_corrente do indicador.
    Refator 2026-05-07: tambem busca em data['wbr']['projecoes']['{ind_id}_M0/M1']
    quando schema SEG (projecoes top-level com chave por indicador+horizonte).
    """
    if not ind:
        return '<div style="color:var(--verde-claro);font-style:italic;">Indicador nao disponivel.</div>'

    cn1 = ind.get("consolidado_n1") or {}
    # SEG schema lookup
    seg_proj_m0 = {}
    seg_proj_m1 = {}
    if data and kind:
        # Tenta resolver o ID base + sufixos comuns
        wbr_inds = data.get("wbr", {}).get("indicadores", {})
        projecoes = data.get("wbr", {}).get("projecoes", {}) or {}
        subnivel = (data.get("card", {}).get("metadata") or {}).get("subnivel")
        ind_id_resolved = _resolve_kpi_id(wbr_inds, kind, subnivel=subnivel)
        if ind_id_resolved:
            seg_proj_m0 = projecoes.get(f"{ind_id_resolved}_M0", {}) or {}
            seg_proj_m1 = projecoes.get(f"{ind_id_resolved}_M1", {}) or {}
        # Tambem tenta no consolidado N1 (sem subnivel)
        if not seg_proj_m0:
            ind_id_n1 = _resolve_kpi_id(wbr_inds, kind, subnivel=None)
            if ind_id_n1:
                seg_proj_m0 = projecoes.get(f"{ind_id_n1}_M0", {}) or {}
                seg_proj_m1 = projecoes.get(f"{ind_id_n1}_M1", {}) or {}

    # Round 9: Card metas_ppi como SoT para meta M0 e M+1 (Maio e Junho).
    card = (data or {}).get("card") or {}
    parent_kind_map = {
        "receita": "receita_seguros_mensal",
        "volume":  "volume_seguros_mensal",
        "quantidade": "quantidade_seguros_mensal",
    }
    parent_ind_id = parent_kind_map.get(kind, kind)
    card_meta_m0 = _meta_from_card_metas_ppi(card, parent_ind_id, horizon="M0")
    card_meta_m1 = _meta_from_card_metas_ppi(card, parent_ind_id, horizon="M1")

    canonical_meta = (cn1.get("meta_mes")
                       or seg_proj_m0.get("meta_mes")
                       or ind.get("meta_mes_corrente")
                       or ind.get("meta"))
    meta_m0 = card_meta_m0 if card_meta_m0 is not None else (canonical_meta or 0)
    meta_m1 = card_meta_m1 if card_meta_m1 is not None else (meta_m0 or 0)

    real = (cn1.get("realizado_mtd")
            or ind.get("realizado_mtd")
            or ind.get("realizado") or 0)
    proj_m0 = (cn1.get("projecao_mes_corrente")
               or ind.get("projecao_mes_corrente")
               or seg_proj_m0.get("base"))
    proj_m1 = (cn1.get("projecao_mes_seguinte")
               or ind.get("projecao_mes_seguinte")
               or seg_proj_m1.get("base"))
    # Round 9: prorata via N1 quando WL ausente (M+1 nao calculado pelo E5 para WL)
    proj_m0_is_prorata = False
    proj_m1_is_prorata = False
    if data:
        wbr_inds = data.get("wbr", {}).get("indicadores", {})
        projecoes = data.get("wbr", {}).get("projecoes", {}) or {}
        ind_id_n1 = _resolve_kpi_id(wbr_inds, kind, subnivel=None)
        n1_m0 = projecoes.get(f"{ind_id_n1}_M0", {}) if ind_id_n1 else {}
        n1_m1 = projecoes.get(f"{ind_id_n1}_M1", {}) if ind_id_n1 else {}
        n1_base_m0 = n1_m0.get("base")
        n1_base_m1 = n1_m1.get("base")
        if proj_m0 is None and isinstance(n1_base_m0, (int, float)) \
                and isinstance(card_meta_m0, (int, float)) \
                and isinstance(n1_m0.get("meta_mes"), (int, float)) and n1_m0.get("meta_mes"):
            # Quando ind=WL e N1 tem proj+meta, prorata pelo share de meta WL/N1
            proj_m0 = n1_base_m0 * (card_meta_m0 / n1_m0.get("meta_mes"))
            proj_m0_is_prorata = True
        if proj_m1 is None and isinstance(n1_base_m1, (int, float)) \
                and isinstance(card_meta_m1, (int, float)) \
                and isinstance(n1_m1.get("meta_mes"), (int, float)) and n1_m1.get("meta_mes"):
            proj_m1 = n1_base_m1 * (card_meta_m1 / n1_m1.get("meta_mes"))
            proj_m1_is_prorata = True

    classif = cn1.get("classificacao") or seg_proj_m0.get("classificacao") or ""

    def _fmt(v):
        if v is None:
            return "—"
        return fmt_brl(v, compact=True) if unidade == "BRL" else fmt_int(v)

    rows = []
    # Edit #31 (2026-05-13): Card declara `apresentacao.proj_periodos_por_indicador[ind_id]`
    # com subset de {"M0", "M+1"}. Default ["M0", "M+1"]; vazio [] = so Realizado.
    apresentacao = (card.get("apresentacao") or {}) if card else {}
    proj_periodos_map = apresentacao.get("proj_periodos_por_indicador") or {}
    proj_periodos = proj_periodos_map.get(parent_ind_id)
    if proj_periodos is None:
        proj_periodos = ["M0", "M+1"]
    proj_periodos_set = set(p.upper() for p in proj_periodos if p)

    # Round 9: cada bar tem sua propria meta (Realizado/M0 usam meta_m0, M+1 usa meta_m1)
    bars = [("Realizado MTD", real, meta_m0, "", False)]
    if "M0" in proj_periodos_set:
        bars.append(("Proj. Mês Atual (M0)", proj_m0, meta_m0, classif, proj_m0_is_prorata))
    if "M+1" in proj_periodos_set:
        bars.append(("Proj. Mês Seguinte (M+1)", proj_m1, meta_m1, "", proj_m1_is_prorata))
    for lbl, v, line_meta, suffix, is_prorata in bars:
        v_str = _fmt(v)
        if is_prorata and v is not None:
            suffix = (suffix + " · prorata") if suffix else "prorata"
        suffix_html = f' <span style="font-size:10px;color:var(--verde-claro);">· {suffix}</span>' if suffix else ""
        if v is None:
            v_str = '<span style="font-style:italic;color:var(--verde-claro);">pendente</span>'
        # fill width/color baseados na meta da propria linha
        if v is None or not isinstance(v, (int, float)) or not isinstance(line_meta, (int, float)) or not line_meta:
            fill_w = 0
            fill_color = "var(--vc-200)"
        else:
            pct_line = (v / line_meta) * 100
            fill_w = min(100, pct_line)
            fill_color = "#2e7d32" if pct_line >= 100 else "#d18000" if pct_line >= 70 else "var(--error)"
        rows.append(
            f'<div style="display:grid;grid-template-columns:160px 1fr 110px;gap:12px;align-items:center;font-size:13px;">'
            f'<div style="color:var(--verde-caqui);">{lbl}</div>'
            f'<div style="background:#f0f0eb;height:18px;border-radius:3px;overflow:hidden;">'
            f'<div style="height:100%;width:{fill_w:.1f}%;background:{fill_color};"></div></div>'
            f'<div style="text-align:right;font-variant-numeric:tabular-nums;font-weight:600;color:var(--verde-caqui);">{v_str}{suffix_html}</div>'
            f'</div>'
        )

    # Footer com meta M0 + M+1 (Maio + Junho)
    meta_m0_str = _fmt(meta_m0) if meta_m0 else "sem meta"
    meta_m1_str = _fmt(meta_m1) if meta_m1 else "sem meta"
    rows.append(
        f'<div style="font-size:11px;color:var(--verde-claro);padding-top:8px;border-top:1px dashed var(--vc-100);margin-top:4px;">'
        f'Meta {label.lower()} M7: M0 <strong style="color:var(--verde-caqui);">{meta_m0_str}</strong>'
        f' · M+1 <strong style="color:var(--verde-caqui);">{meta_m1_str}</strong>'
        f'</div>'
    )

    return "\n".join(rows)


# ============================================================
# Renderers — C8 Fechamento Mes Anterior + Diretrizes (1o ritual do mes)
# ============================================================

def _auto_resolve_wbr_fechamento(wbr_data_path: Path, mes_ciclo_anterior: str = None) -> Path | None:
    """C8 (2026-05-07): localiza o WBR do mes fechado.
    Estrutura esperada: {vertical}/{YYYY-MM}-fechamento/wbr/wbr-{vertical}-{YYYY-MM}-fechamento.data.json

    Args:
        wbr_data_path: path do WBR atual (ciclo MTD)
        mes_ciclo_anterior: YYYY-MM do mes anterior; se None, infere do parent[1].name
    """
    try:
        cycle_dir = wbr_data_path.parent.parent  # wbr/file -> ciclo/
        parent = cycle_dir.parent
        # Detecta layout: S3 (parent e o month-wrapper YYYY-MM) vs legacy
        # (parent e a raiz da vertical, ciclos flat tipo "2026-05-31").
        if re.fullmatch(r"\d{4}-\d{2}", parent.name):
            vertical_root = parent.parent          # S3: .../{Vertical}/{YYYY-MM}/{ciclo}/
            cur_month = parent.name
        else:
            vertical_root = parent                 # legacy: .../{Vertical}/{ciclo}/
            m = re.match(r"(\d{4}-\d{2})", cycle_dir.name)
            cur_month = m.group(1) if m else None

        # Coleta candidatos de fechamento em ambos os layouts.
        candidates = list(vertical_root.glob("*/*/wbr/wbr-*-fechamento.data.json"))   # S3
        candidates += list(vertical_root.glob("*-fechamento/wbr/wbr-*-fechamento.data.json"))  # legacy
        if not candidates:
            return None

        def _month_of(p):
            mm = re.search(r"(\d{4}-\d{2})-fechamento\.data\.json$", p.name)
            return mm.group(1) if mm else ""

        # Se mes_ciclo_anterior foi dado, preferir match exato.
        if mes_ciclo_anterior:
            for p in candidates:
                if _month_of(p) == mes_ciclo_anterior:
                    return p
        # Senao: pegar o fechamento mais recente estritamente anterior ao mes corrente.
        valid = [p for p in candidates if _month_of(p) and (not cur_month or _month_of(p) < cur_month)]
        if not valid:
            valid = [p for p in candidates if _month_of(p)]
        if not valid:
            return None
        valid.sort(key=_month_of)
        return valid[-1]
    except Exception:
        return None


def _fech_card(label: str, value, meta=None, unidade: str = "BRL", direction: str = "maior_melhor") -> str:
    """Renderiza 1 card de fechamento (label + valor + meta context).

    Classifica cor via pct atingimento. Sem meta = neutro.
    Refator 2026-05-07: suporta unidade='ratio' (valor 0-1, exibido como pct).
    Auto-detecta ratio quando unidade='pct' e valor <= 1.0 (heuristica).
    """
    # Auto-detecta ratio quando taxa_conversao retorna valor 0-1 mas chamador passa unidade=pct
    if unidade == "pct" and isinstance(value, (int, float)) and 0 < abs(value) <= 1.0:
        unidade = "ratio"

    if unidade == "BRL":
        v_str = fmt_brl(value, compact=True) if value is not None else "—"
        m_str = fmt_brl(meta, compact=True) if meta else None
    elif unidade == "pct":
        v_str = fmt_pct(value, 1) if value is not None else "—"
        m_str = fmt_pct(meta, 0) if meta else None
    elif unidade == "ratio":
        # FIX 2026-05-14 (Bug 1 — Taxa Conversao): analyst v1.1 emite ratio ja em pct.
        # So multiplicar ×100 quando value <= 1.0 (mesmo heuristic ja aplicado a meta).
        v_pct = value * 100 if isinstance(value, (int, float)) and abs(value) <= 1.0 else value
        v_str = fmt_pct(v_pct, 1) if value is not None else "—"
        m_str = fmt_pct(meta * 100 if isinstance(meta, (int, float)) and abs(meta) <= 1.0 else meta, 0) if meta else None
    else:  # count
        v_str = fmt_int(value) if value is not None else "—"
        m_str = fmt_int(meta) if meta else None

    cls = ""
    meta_html = ""
    if value is not None and meta and isinstance(value, (int, float)) and isinstance(meta, (int, float)) and meta != 0:
        try:
            if direction == "menor_melhor":
                pct = (meta / max(value, 1e-9)) * 100
            else:
                pct = (value / meta) * 100
            cls = "good" if pct >= 100 else "warn" if pct >= 70 else "bad"
            # Edit #4 (2026-05-13): barra de atingimento visual substitui texto
            # "xx% da meta · meta R$ xxK". Barra escala 0-100% com cor por threshold.
            # Pct DENTRO da barra (segue preenchimento); meta FORA à direita.
            # CSS em ritual.tmpl.html (.atingimento-bar / .pct-label / .ab-fill).
            meta_html = _render_atingimento_bar(pct, m_str, cls)
        except (TypeError, ZeroDivisionError):
            pass
    elif m_str:
        meta_html = f'<div class="fc-meta">meta {m_str}</div>'
    elif meta is None:
        meta_html = '<div class="fc-meta" style="font-style:italic;">sem meta formal</div>'

    return (
        f'<div class="fech-card">'
        f'<div class="fc-label">{label}</div>'
        f'<div class="fc-value {cls}">{v_str}</div>'
        f'{meta_html}'
        f'</div>'
    )


def _render_atingimento_bar(pct: float, meta_str: str, cls: str) -> str:
    """Edit #4 (2026-05-13): barra visual de atingimento (substitui '% da meta · meta XX').

    - Barra escala 0-100%, cor por threshold (good/warn/bad/mute).
    - Pct DENTRO da barra (label segue posicao do fill via left:pct%).
    - Meta FORA à direita, abaixo da barra.
    - Cor do pct sempre branca + text-shadow (#27 — legibilidade sobre qualquer cor).
    """
    fill_w = max(0, min(100, pct))
    fill_cls = cls if cls in ("good", "warn", "bad") else "mute"
    # Img3 (2026-06-03): pct-label SEMPRE branco e ancorado no inicio do fill.
    # fill ganha min-width para o label branco ter sempre fundo colorido (mesmo
    # com pct baixo), em vez de cair "outside" escuro sobre o track claro.
    return (
        f'<div class="atingimento-bar-wrap">'
        f'<div class="atingimento-bar">'
        f'<div class="ab-fill {fill_cls}" style="width:{fill_w:.1f}%;min-width:38px;"></div>'
        f'<span class="pct-label inside" style="left:8px;">{pct:.0f}%</span>'
        f'</div>'
        f'<div class="atingimento-bar-meta">meta {meta_str}</div>'
        f'</div>'
    )


def _resolve_indicator(indicadores: dict, possible_ids: list) -> dict:
    """Procura o primeiro indicador que casa com possible_ids (case-insensitive)."""
    for k, v in indicadores.items():
        k_lc = k.lower()
        if any(pid.lower() in k_lc for pid in possible_ids):
            return v
    return {}


def _fech_headline(rec: dict, vol: dict, qty: dict, taxa: dict, mes_ant_lbl: str) -> str:
    """F6+P3 (2026-05-07): headline jornalistica grande resumindo o mes.
    Big idea — 1 frase de manchete com destaque <em> em pct/meta."""
    rec_real = rec.get("realizado_mtd") or rec.get("realizado") or 0
    rec_meta = rec.get("meta_mes_corrente") or rec.get("meta") or 0
    vol_real = vol.get("realizado_mtd") or vol.get("realizado") or 0
    qty_real = qty.get("realizado_mtd") or qty.get("realizado") or 0

    pct_rec = (rec_real / rec_meta * 100) if rec_meta else None
    rec_str = fmt_brl(rec_real, compact=True)
    vol_str = fmt_brl(vol_real, compact=True)
    qty_str = f"{int(qty_real)} contrato(s)" if qty_real else "0 contratos"

    if pct_rec is not None:
        if pct_rec >= 100:
            manchete = (
                f"Vertical <em>superou a meta</em> com {rec_str} de receita "
                f"({pct_rec:.0f}% · {vol_str} volume · {qty_str})."
            )
        elif pct_rec >= 70:
            manchete = (
                f"Vertical fechou em <em>{pct_rec:.0f}% da meta</em> com {rec_str} "
                f"de receita ({vol_str} volume · {qty_str})."
            )
        else:
            manchete = (
                f"Vertical fechou em <em>{pct_rec:.0f}% da meta</em> — gap relevante "
                f"com receita de {rec_str} ({vol_str} volume · {qty_str})."
            )
    else:
        manchete = (
            f"Vertical encerrou sem meta formal: {rec_str} de receita, "
            f"{vol_str} volume, {qty_str}."
        )

    return (
        f'<div class="fech-headline">'
        f'<span class="fh-eyebrow">Como foi {mes_ant_lbl}</span>'
        f'{manchete}'
        f'</div>'
    )


def _status_class_fech(cor: str) -> str:
    """Mapeia cor canonica (verde/amarelo/vermelho/cinza) para classe CSS fech-col."""
    return {"verde": "good", "amarelo": "warn", "vermelho": "bad", "cinza": "mute"}.get(cor, "mute")


def _atingimento_bar_fech(pct, meta_str: str, cor: str) -> str:
    """Renderiza barra de atingimento (paridade build_deck_pj2.py:_atingimento_bar).

    Item 9/S9 follow-up Seguros-WL 2026-05-20 (2026-05-21): portado para uso no
    render_fechamento_esp_slides com padrao fech-col x fc-row. Bar 0-100% colorida
    com pct dentro/fora + meta a direita.
    """
    cls = _status_class_fech(cor)
    if pct is None:
        return (f'<div class="atingimento-row"><div class="atingimento-bar">'
                f'<div class="fill cinza" style="width:0%;"></div></div>'
                f'<div class="atingimento-meta-side">{meta_str}</div></div>')
    pct_int = int(round(pct))
    fill_width = min(max(pct_int, 0), 100)
    # Img3 (2026-06-03): pct-label SEMPRE branco (inside) + fill com min-width para
    # ancorar o label sobre a cor mesmo com pct baixo (antes <18% caia "outside" escuro).
    return (f'<div class="atingimento-row"><div class="atingimento-bar">'
            f'<div class="fill {cls}" style="width:{fill_width}%;min-width:34px;"></div>'
            f'<div class="pct-label inside">{pct_int}%</div></div>'
            f'<div class="atingimento-meta-side">{meta_str}</div></div>')


def _fech_col_row_esp(label: str, ind_atual: dict, esp: str, kind: str,
                       meta_esp_v, direction_override: str = None) -> str:
    """Renderiza 1 fc-row de fech-col para um especialista.

    Item 9/S9 follow-up Seguros-WL 2026-05-20 (2026-05-21): adaptado de
    build_deck_pj2.fech_col_row, mas le ind.n2[esp].realizado em vez de
    ind.n2_agregado[canal]. Usado por render_fechamento_esp_slides para
    Cons / Seg WL / Seg RE.

    Args:
      label: rotulo da linha (Volume / Receita / Tempo de Ciclo CRM / ...)
      ind_atual: dict do indicator do canonical WBR (com n2)
      esp: nome do especialista (Card.apresentacao.responsaveis[i].nome)
      kind: 'brl' | 'pct' | 'int' | 'days'
      meta_esp_v: meta para o esp (numerico ou None)
      direction_override: 'menor_melhor' forca logica invertida (default
        auto-detecta via label keywords)

    Memory: feedback_metas_ppi_top_down + feedback_canonical_data_json.
    """
    if not ind_atual:
        ind_atual = {}
    n2 = ind_atual.get("n2") or {}
    esp_data = n2.get(esp) or {}
    v = esp_data.get("realizado_mtd")
    if v is None:
        v = esp_data.get("realizado")
    # Caso de tempo_de_ciclo: o campo eh tempo_ciclo_dias_p50 no canonical
    if v is None and kind == "days":
        v = esp_data.get("tempo_ciclo_dias_p50")

    # Formatar valor
    if kind == "brl":
        vstr = fmt_brl(v, compact=True) if v is not None else "—"
    elif kind == "pct" and v is not None:
        # canonical guarda ratio (0-1) ou pct ja (0-100)
        vstr = fmt_pct(v * 100, 1) if v <= 1 else fmt_pct(v, 1)
    elif kind == "int" and v is not None:
        vstr = fmt_int(v)
    elif kind == "days" and v is not None:
        vstr = f"{int(round(v))}"
    else:
        vstr = "—"

    # Detectar direction
    lbl_low = (label or "").lower()
    if direction_override:
        direction = direction_override
    elif "estagna" in lbl_low or "sem ativ" in lbl_low or "tempo de ciclo" in lbl_low:
        direction = "menor_melhor"
    else:
        direction = "maior_melhor"

    # Calcular pct e cor
    if v is not None and meta_esp_v not in (None, 0):
        try:
            if direction == "menor_melhor":
                # ratio = realizado/meta — verde quando <=100% (dentro)
                pct = (float(v) / float(meta_esp_v)) * 100
                cor = "verde" if pct <= 100 else ("amarelo" if pct <= 125 else "vermelho")
            else:
                pct = (float(v) / float(meta_esp_v)) * 100
                cls = cor_from_pct(pct / 100, direction="maior_melhor")
                cor = {"good": "verde", "warn": "amarelo", "bad": "vermelho"}.get(cls, "cinza")
        except (TypeError, ValueError):
            pct, cor = None, "cinza"
    else:
        pct, cor = None, "cinza"

    # Meta str
    if meta_esp_v is None:
        meta_str = "<span style='color:var(--vc-300);'>sem meta</span>"
    elif kind == "brl":
        meta_str = f"meta <strong>{fmt_brl(meta_esp_v, compact=True)}</strong>"
    elif kind == "pct":
        meta_v_display = meta_esp_v * 100 if meta_esp_v <= 1 else meta_esp_v
        meta_str = f"meta <strong>{fmt_pct(meta_v_display, 1)}</strong>"
    elif kind == "int":
        meta_str = f"meta <strong>{fmt_int(meta_esp_v)}</strong>"
    elif kind == "days":
        meta_str = f"meta <strong>{int(round(meta_esp_v))}</strong>"
    else:
        meta_str = f"meta <strong>{meta_esp_v}</strong>"

    bar = _atingimento_bar_fech(pct, meta_str, cor)
    val_cls = _status_class_fech(cor)
    return (f'<div class="fc-row"><div class="lbl">{label}</div>'
            f'<div class="val {val_cls}">{vstr}</div>{bar}</div>')


def render_fechamento_n1_slide(wbr_fech: dict, ctx: dict, dados_n5_fech: dict = None) -> str:
    """Slide consolidado N1 do mes fechado.
    Headline + 6 cards: Volume → Receita → Qtd {tipo_contrato} / Ticket → Taxa → Oport. Criadas.
    Ordem F1: KPIs Resultado (Volume/Receita/Qtd) primeiro.
    Sem projecao M+1 (mes ja fechou — is_retrospective=true).

    R5-1 (2026-05-07): quando dados_n5_fech disponivel, usa SUM(N5) como source-of-truth
    para Qtd e Oportunidades Criadas (paridade com slide Esp). Fallback para canonical N1
    quando N5 vazio.
    Label "Qtd {tipo_contrato}" puxado de Card.metadata.tipo_contrato (apolices/cartas/etc).
    """
    if not wbr_fech:
        return ""

    indicadores = wbr_fech.get("indicadores", {})
    mes_ant = wbr_fech.get("data_referencia", "")[:7] or wbr_fech.get("checkpoint_label", "Mes anterior")
    # Mes em PT extenso para headline
    mes_ant_lbl = mes_ant
    if mes_ant and len(mes_ant) == 7:
        try:
            m = int(mes_ant[5:7])
            meses_pt = ["", "Janeiro", "Fevereiro", "Marco", "Abril", "Maio", "Junho",
                        "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
            mes_ant_lbl = f"{meses_pt[m]} {mes_ant[:4]}"
        except Exception:
            pass

    vertical = ctx.get("VERTICAL", "")
    nivel = ctx.get("NIVEL", "N3")
    card = ctx.get("_card") or {}

    # Refator 2026-05-07: usa _resolve_kpi_id (data-driven) ao inves de _resolve_indicator
    # com substring. Suporta sufixos por subnivel (SEG WL: receita_seguros_mensal_wl).
    subnivel = (card.get("metadata") or {}).get("subnivel")
    def _ind(kind):
        rid = _resolve_kpi_id(indicadores, kind, subnivel=subnivel)
        if rid and rid in indicadores:
            return indicadores[rid]
        # fallback generic substring (legacy)
        legacy_map = {
            "receita": ["receita_"], "volume": ["volume_"], "quantidade": ["quantidade_"],
            "ticket_medio": ["ticket_medio_premio", "ticket_medio_consorcio", "ticket_medio_pipeline"],
            "taxa_conversao": ["taxa_conversao_"], "criadas": ["oportunidades_criadas_"]
        }
        return _resolve_indicator(indicadores, legacy_map.get(kind, [kind])) or {}

    rec = _ind("receita")
    vol = _ind("volume")
    qty = _ind("quantidade")
    ticket = _ind("ticket_medio")
    taxa = _ind("taxa_conversao")
    oport = _ind("criadas")

    headline = _fech_headline(rec, vol, qty, taxa, mes_ant_lbl)

    def _real(d):
        return d.get("realizado_mtd") if d.get("realizado_mtd") is not None else d.get("realizado")

    def _meta_with_card(d, parent_kind):
        # Tenta canonical primeiro; fallback Card.metas_ppi
        m = d.get("meta_mes_corrente") if d.get("meta_mes_corrente") is not None else d.get("meta")
        # Card override (usuario SoT)
        # Mapping kind→parent_indicator nome no Card
        parent_map = {
            "receita": "receita_seguros_mensal", "volume": "volume_seguros_mensal",
            "quantidade": "quantidade_seguros_mensal", "ticket_medio": "ticket_medio_premio_seg",
            "taxa_conversao": "taxa_conversao_funil_seg", "criadas": "oportunidades_criadas_funil_seg"
        }
        parent_id = parent_map.get(parent_kind)
        if parent_id:
            cm = _meta_from_card_metas_ppi(card, parent_id)
            if cm is not None:
                return cm
        return m

    # R6-1 (2026-05-07): usar N2-Especialista rows do dados_n5_fech filtrados pelos
    # esps do Card + filtro de mes (o coletor pode trazer multiplos meses).
    esp_filter = set(ctx.get("_esp_list", []) or [])
    # Mes do fechamento (formato YYYY-MM) — extraido de wbr_fech.data_referencia.
    fech_mes_prefix = (wbr_fech.get("data_referencia") or "")[:7]

    def _sum_n2_field(kind_match: str, field: str) -> float:
        """Soma `field` dos rows N2-Especialista filtrados por esps do Card e
        pelo mes do fechamento (evita somar Abril+Maio quando coletor pegou 2 meses)."""
        if not dados_n5_fech:
            return None
        total = 0
        found = False
        for entry in dados_n5_fech.get("indicadores", []):
            ind_id = (entry.get("indicator_id") or "").lower()
            if kind_match not in ind_id:
                continue
            for row in entry.get("data", []):
                if row.get("nivel") != "N2-Especialista":
                    continue
                if row.get("estagio"):
                    continue
                if esp_filter and row.get("especialista") not in esp_filter:
                    continue
                # R6: filtrar por mes do fechamento
                if fech_mes_prefix:
                    row_mes = str(row.get("mes") or "")[:7]
                    if row_mes and row_mes != fech_mes_prefix:
                        continue
                v = row.get(field)
                if v is not None:
                    total += v
                    found = True
        return total if found else None

    qty_real = _sum_n2_field("quantidade_", "realizado")
    criadas_real = _sum_n2_field("oportunidades_criadas_", "quantidade")
    # Taxa = total_ganhos / (total_ganhos + total_perdidos) consolidado por esps RE
    won = _sum_n2_field("taxa_conversao_", "total_ganhos") or 0
    lost = _sum_n2_field("taxa_conversao_", "total_perdidos") or 0
    taxa_real = (won / (won + lost)) if (won + lost) > 0 else None
    if taxa_real is None:
        taxa_real = _real(taxa)  # fallback canonical

    # R6 (2026-05-07): Volume / Receita / Ticket Convertido sao KPIs ClickHouse-dependent.
    # Para deck split (RE/WL com CTE mapa_especialista quebrado), forcar None quando
    # Card.metas_ppi.{kind}.valor == "pendente" (sentinel explicito de "sem dado RE valido").
    def _force_none_if_pendente(parent_kind: str, fallback_real):
        parent_id = parent_map.get(parent_kind)
        if parent_id:
            mp = (card.get("metas_ppi") or {}).get(parent_id) or {}
            if mp.get("valor") == "pendente":
                return None
        return fallback_real

    parent_map = {
        "receita": "receita_seguros_mensal", "volume": "volume_seguros_mensal",
        "quantidade": "quantidade_seguros_mensal", "ticket_medio": "ticket_medio_premio_seg",
        "taxa_conversao": "taxa_conversao_funil_seg", "criadas": "oportunidades_criadas_funil_seg"
    }

    rec_real = _force_none_if_pendente("receita", _real(rec))
    vol_real_raw = _force_none_if_pendente("volume", _real(vol))
    qty_real = qty_real if qty_real is not None else (_force_none_if_pendente("quantidade", _real(qty) or 0))

    # Ticket Medio = Volume/Qtd (Cons). Seg RE/WL: Volume=None (CH gap) -> Receita/Qtd. FIX 2026-06-10.
    ticket_real_calc = None
    if isinstance(vol_real_raw, (int, float)) and isinstance(qty_real, (int, float)) and qty_real > 0:
        ticket_real_calc = vol_real_raw / qty_real
    elif isinstance(rec_real, (int, float)) and isinstance(qty_real, (int, float)) and qty_real > 0:
        ticket_real_calc = rec_real / qty_real
    # Force None se metas_ppi.ticket_medio_premio_seg.valor=pendente
    ticket_real_calc = _force_none_if_pendente("ticket_medio", ticket_real_calc)

    # R5-transversal (2026-05-07): label "Qtd {tipo_contrato}" — puxado dinamicamente
    # do Card.metadata.tipo_contrato (apolices/cartas/contratos/...). Fallback "Contratos".
    # Edit #16 (2026-05-13): Card pode declarar `metadata.tipo_contrato_label` para
    # override completo (ex: "Contratos Fechados" / "Apólices Fechadas") quando a
    # variante "Qtd {tipo}" nao tem ressonancia com a vertical.
    tipo_label_override = (card.get("metadata") or {}).get("tipo_contrato_label")
    if tipo_label_override:
        qty_label = tipo_label_override
    else:
        tipo_contrato = ((card.get("metadata") or {}).get("tipo_contrato") or "Contratos")
        qty_label = f"Qtd {tipo_contrato.capitalize()}"

    # #2 (2026-06-02): meta N1 do Ticket Medio (fechamento) = meta_Volume / meta_Qtd
    # — derivada (consistente com o realizado = volume/qty). Antes ficava "sem meta
    # formal" pois parent_map["ticket_medio"]=ticket_medio_premio_seg nao existe em Cons.
    _tk_meta_n1 = _meta_with_card(ticket, "ticket_medio")
    if _tk_meta_n1 is None:
        _mv_n1 = _meta_with_card(vol, "volume")
        _mq_n1 = _meta_with_card(qty, "quantidade")
        if isinstance(_mv_n1, (int, float)) and isinstance(_mq_n1, (int, float)) and _mq_n1 > 0:
            _tk_meta_n1 = _mv_n1 / _mq_n1

    # F1 ordem: Volume → Receita → Quantidade (KPI Resultado primeiro), depois suportes
    cards = [
        _fech_card("Volume Fechado", vol_real_raw, _meta_with_card(vol, "volume"), unidade="BRL"),
        _fech_card("Receita Fechada", rec_real, _meta_with_card(rec, "receita"), unidade="BRL"),
        _fech_card(qty_label, qty_real, _meta_with_card(qty, "quantidade"), unidade="count"),
        _fech_card("Ticket Medio", ticket_real_calc, _tk_meta_n1, unidade="BRL"),
        _fech_card("Taxa Conversao", taxa_real, _meta_with_card(taxa, "taxa_conversao"), unidade="pct"),
        _fech_card("Oportunidades Criadas", criadas_real, _meta_with_card(oport, "criadas"), unidade="count"),
    ]

    return (
        f'<section data-label="Fechamento {mes_ant}">\n'
        f'  <div class="slide-head">\n'
        f'    <div class="h-left">\n'
        f'      <img src="{ctx.get("ASSET_LOGO_DARK_DATA_URI", "")}" class="h-logo" alt="M7"/>\n'
        f'      <div class="h-divider"></div>\n'
        f'      <div>\n'
        f'        <div class="h-eyebrow">Fechamento mensal</div>\n'
        f'        <div class="h-title">Fechamento {mes_ant_lbl} · {nivel} {vertical}</div>\n'
        f'      </div>\n'
        f'    </div>\n'
        f'  </div>\n'
        f'  <div class="slide-body">\n'
        f'    {headline}\n'
        f'    <div class="fech-grid">\n'
        f'      {chr(10).join(cards)}\n'
        f'    </div>\n'
        f'  </div>\n'
        f'  <div class="slide-foot">\n'
        f'    <div class="f-meta">Bloco extra · Fechamento mensal automatico (1o ritual do mes)</div>\n'
        f'    <div class="f-num">03a</div>\n'
        f'  </div>\n'
        f'</section>\n'
    )


def render_fechamento_esp_slides(wbr_fech: dict, ctx: dict, dados_n5_fech: dict = None, card: dict = None, skill_dir: Path = None) -> str:
    """1 slide por especialista N3 com cards de fechamento (esquerda) + rank
    Criadas/Fechadas por assessor (direita).
    P2 (2026-05-07): rank substitui SVG line chart anterior."""
    if not wbr_fech:
        return ""

    indicadores = wbr_fech.get("indicadores", {})
    mes_ant = wbr_fech.get("data_referencia", "")[:7] or "Mes anterior"
    esp_list = ctx.get("_esp_list", [])
    nivel = ctx.get("NIVEL", "N3")
    vertical = ctx.get("VERTICAL", "")
    if card is None:
        card = ctx.get("_card", {})

    # Refator 2026-05-07: data-driven via _resolve_kpi_id (suporta SEG split)
    subnivel = (card.get("metadata") or {}).get("subnivel") if card else None
    def _ind(kind):
        rid = _resolve_kpi_id(indicadores, kind, subnivel=subnivel)
        if rid and rid in indicadores:
            return indicadores[rid]
        legacy_map = {
            "receita": ["receita_"], "volume": ["volume_"], "quantidade": ["quantidade_"],
            "ticket_medio": ["ticket_medio_premio", "ticket_medio_consorcio"],
            "taxa_conversao": ["taxa_conversao_"], "criadas": ["oportunidades_criadas_"],
            # Item 9/S9 follow-up 2026-05-21: adicionados tempo_de_ciclo + estagnacao_pct
            "tempo_de_ciclo": ["tempo_de_ciclo_funil"],
            "estagnacao_pct": ["oportunidades_estagnadas_funil_pct_ativas",
                                "oportunidades_estagnadas_funil_seg_pct_ativas",
                                "oportunidades_estagnadas_funil_con_pct_ativas"],
        }
        return _resolve_indicator(indicadores, legacy_map.get(kind, [kind])) or {}

    rec = _ind("receita")
    vol = _ind("volume")
    qty = _ind("quantidade")
    ticket = _ind("ticket_medio")
    taxa = _ind("taxa_conversao")
    oport = _ind("criadas")
    # Item 9/S9 follow-up: tempo_de_ciclo + estagnacao_pct para fech-col x fc-row
    tempo_ciclo = _ind("tempo_de_ciclo")
    # FIX 2026-06-10: _ind("estagnacao_pct") retornava {} — "estagnacao_pct" nao esta no
    # pat_map do _resolve_kpi_id e o legacy_map nao cobria o sufixo _seg_re/_seg_wl
    # (so _seg_pct_ativas / _con_pct_ativas). Resolver via kind="estagnadas" +
    # aspect="pct_ativas" (o scoring trata subnivel corretamente).
    _estagn_pct_id = _resolve_kpi_id(indicadores, "estagnadas", subnivel=subnivel, aspect="pct_ativas")
    estagnacao_pct = (indicadores.get(_estagn_pct_id) or {}) if _estagn_pct_id else _ind("estagnacao_pct")

    parent_map = {
        "receita": "receita_seguros_mensal", "volume": "volume_seguros_mensal",
        "quantidade": "quantidade_seguros_mensal", "ticket_medio": "ticket_medio_premio_seg",
        "taxa_conversao": "taxa_conversao_funil_seg", "criadas": "oportunidades_criadas_funil_seg",
        # Item 9/S9: parent ids para metas_ppi lookup
        "tempo_de_ciclo": "tempo_de_ciclo_funil",  # base — _meta_from_card_metas_ppi resolve _con/_seg_wl/_seg_re via parent_id prefix
        "estagnacao_pct": "oportunidades_estagnadas_funil",
    }
    def _meta_card(esp_name, kind):
        # #Img1 (2026-06-03): tempo_de_ciclo = meta unica nao-aditiva (mediana 30d
        # aplica a todos) → esp=None p/ pegar `valor` top-level. estagnacao_pct =
        # meta ratio (pct_ativas_max=40) → aspect ratio resolve via top-level.
        if kind == "tempo_de_ciclo":
            return _meta_from_card_metas_ppi(card, parent_map.get(kind), esp=None)
        if kind == "estagnacao_pct":
            return _meta_from_card_metas_ppi(card, parent_map.get(kind), esp=esp_name, aspect="pct_ativas")
        return _meta_from_card_metas_ppi(card, parent_map.get(kind), esp=esp_name)

    sections = []
    for idx, esp in enumerate(esp_list, start=1):
        e_rec = (rec.get("n2") or {}).get(esp, {})
        e_vol = (vol.get("n2") or {}).get(esp, {})
        e_qty = (qty.get("n2") or {}).get(esp, {})
        e_ticket = (ticket.get("n2") or {}).get(esp, {})
        e_taxa = (taxa.get("n2") or {}).get(esp, {})
        e_oport = (oport.get("n2") or {}).get(esp, {})

        def _r(d):
            return d.get("realizado_mtd") if d.get("realizado_mtd") is not None else d.get("realizado")

        def _m(d, kind):
            cm = _meta_card(esp, kind)
            if cm is not None:
                return cm
            return d.get("meta_mes") or d.get("meta") or d.get("meta_mes_corrente")

        # R6-1 (2026-05-07): le N2-Especialista row do dados_n5_fech filtrado por esp
        # + mes do fechamento (coletor pode trazer multi-meses).
        fech_mes_prefix_esp = (wbr_fech.get("data_referencia") or "")[:7]
        def _n2_field_for_esp(kind_match: str, field: str):
            if not dados_n5_fech:
                return None
            for entry in dados_n5_fech.get("indicadores", []):
                ind_id = (entry.get("indicator_id") or "").lower()
                if kind_match not in ind_id:
                    continue
                for row in entry.get("data", []):
                    if row.get("nivel") != "N2-Especialista":
                        continue
                    if row.get("estagio"):
                        continue
                    if row.get("especialista") != esp:
                        continue
                    # R6: filtrar por mes do fechamento
                    if fech_mes_prefix_esp:
                        row_mes = str(row.get("mes") or "")[:7]
                        if row_mes and row_mes != fech_mes_prefix_esp:
                            continue
                    return row.get(field)
            return None

        n2_q = _n2_field_for_esp("quantidade_", "realizado")
        n2_c = _n2_field_for_esp("oportunidades_criadas_", "quantidade")
        n2_taxa = _n2_field_for_esp("taxa_conversao_", "taxa_conversao")

        q_real = n2_q if n2_q is not None else (_r(e_qty) or 0)
        c_real = n2_c if n2_c is not None else _r(e_oport)
        taxa_esp_real = n2_taxa if n2_taxa is not None else _r(e_taxa)

        # R6 (2026-05-07): Volume/Receita/Ticket = "—" quando metas_ppi.valor=pendente
        # Sinaliza que o esp nao tem dados ClickHouse RE validos (CTE 938/950 nao mapeia).
        def _force_none_esp(kind: str, fallback):
            parent = parent_map.get(kind)
            if parent and (card.get("metas_ppi", {}).get(parent, {}) or {}).get("valor") == "pendente":
                return None
            return fallback

        e_rec_real = _force_none_esp("receita", _r(e_rec))
        e_vol_real = _force_none_esp("volume", _r(e_vol))

        # Ticket Medio: Volume/Qtd (Cons — volume = valor da carta). Em Seg RE/WL o
        # Volume vem do ClickHouse e e None (gap 938/950), entao cai para Receita/Qtd
        # ("e so dividir": receita fechada / apolices). FIX 2026-06-10.
        ticket_calc = None
        if isinstance(e_vol_real, (int, float)) and isinstance(q_real, (int, float)) and q_real > 0:
            ticket_calc = e_vol_real / q_real
        elif isinstance(e_rec_real, (int, float)) and isinstance(q_real, (int, float)) and q_real > 0:
            ticket_calc = e_rec_real / q_real
        ticket_calc = _force_none_esp("ticket_medio", ticket_calc)

        # R5-transversal (2026-05-07): label "Qtd {tipo_contrato}" dinamico do Card.
        # Edit #16 (2026-05-13): Card pode override via `metadata.tipo_contrato_label`.
        tipo_label_override_esp = (card.get("metadata") or {}).get("tipo_contrato_label") if card else None
        if tipo_label_override_esp:
            qty_label_esp = tipo_label_override_esp
        else:
            tipo_contrato_esp = ((card.get("metadata") or {}).get("tipo_contrato") or "Contratos") if card else "Contratos"
            qty_label_esp = f"Qtd {tipo_contrato_esp.capitalize()}"

        # Item 9/S9 follow-up Seguros-WL 2026-05-20 (2026-05-21): refactor para
        # padrao fech-col x fc-row (paridade build_deck_pj2.py). 8 KPIs por
        # especialista incluindo Tempo de Ciclo CRM + Estagnacao Mediana CRM.
        # Memory: project_telegram_bot_alertas + feedback_metas_ppi_top_down.

        # Tempo de Ciclo: realizado vem do canonical n2[esp].tempo_ciclo_dias_p50
        tempo_meta = _meta_card(esp, "tempo_de_ciclo")
        # Estagnacao Mediana % ativas: realizado e meta vem do indicador derivado
        # oportunidades_estagnadas_funil_*_pct_ativas (Fase 4.5.f aggregation_rule).
        estagn_meta = _meta_card(esp, "estagnacao_pct")

        # Label do tipo de contrato para Qtd Fechadas
        tipo_label_override_esp = (card.get("metadata") or {}).get("tipo_contrato_label") if card else None
        if tipo_label_override_esp:
            qty_label_esp = tipo_label_override_esp
        else:
            tipo_contrato_esp = ((card.get("metadata") or {}).get("tipo_contrato") or "Contratos") if card else "Contratos"
            qty_label_esp = f"{tipo_contrato_esp.capitalize()} Fechados"

        # Construir indicators sinteticos com n2 forcado quando Ticket Medio
        # (calculado em runtime) ou quando _force_none_esp fixou None.
        def _synth_ind_with_n2_value(val):
            return {"n2": {esp: {"realizado": val}}}

        ticket_ind_for_row = _synth_ind_with_n2_value(ticket_calc)
        vol_ind_for_row = _synth_ind_with_n2_value(e_vol_real)
        rec_ind_for_row = _synth_ind_with_n2_value(e_rec_real)
        qty_ind_for_row = _synth_ind_with_n2_value(q_real)
        taxa_ind_for_row = _synth_ind_with_n2_value(taxa_esp_real)
        crd_ind_for_row = _synth_ind_with_n2_value(c_real)

        # #2 (2026-06-02): meta do Ticket Medio (fechamento) = meta_Volume / meta_Qtd
        # — derivada da meta de volume fechado e da meta de contratos fechados, em
        # paridade com o realizado (ticket_calc = volume/qty). Antes ficava sem meta
        # porque parent_map["ticket_medio"] aponta p/ ticket_medio_premio_seg (inexistente em Cons).
        _ticket_meta_explicit = _m(e_ticket, "ticket_medio")
        if _ticket_meta_explicit is not None:
            ticket_meta_val = _ticket_meta_explicit
        else:
            _mv = _m(e_vol, "volume")
            _mq = _m(e_qty, "quantidade")
            ticket_meta_val = (_mv / _mq) if (
                isinstance(_mv, (int, float)) and isinstance(_mq, (int, float)) and _mq > 0
            ) else None

        rows_html = "".join([
            _fech_col_row_esp("Volume", vol_ind_for_row, esp, "brl", _m(e_vol, "volume")),
            _fech_col_row_esp("Receita", rec_ind_for_row, esp, "brl", _m(e_rec, "receita")),
            _fech_col_row_esp(qty_label_esp, qty_ind_for_row, esp, "int", _m(e_qty, "quantidade")),
            _fech_col_row_esp("Ticket Medio", ticket_ind_for_row, esp, "brl", ticket_meta_val),
            _fech_col_row_esp("Tempo de Ciclo CRM", tempo_ciclo, esp, "days", tempo_meta),
            _fech_col_row_esp("Tx Conversao CRM", taxa_ind_for_row, esp, "pct", _m(e_taxa, "taxa_conversao")),
            _fech_col_row_esp("Oport. Criadas CRM", crd_ind_for_row, esp, "int", _m(e_oport, "criadas")),
            _fech_col_row_esp("Estagnadas % Ativas CRM", estagnacao_pct, esp, "pct", estagn_meta),
        ])

        # Cor do fc-head por especialista (CSS classes esp-* — caso opcional, default verde-caqui)
        esp_slug = (esp or "").lower().split()[0] if esp else ""
        head_class = f"esp-{esp_slug}" if esp_slug else ""

        # P2 (2026-05-07): rank por assessor (Criadas + Fechadas)
        chart_svg = _render_fechamento_esp_rank(esp, wbr_fech, dados_n5_fech, card)

        # #3 (2026-06-02): avatar do especialista no header (paridade com o slide
        # Dashboard do modo atual, que usa resolve_circulo). Antes o fechamento
        # so tinha o logo M7 + nome, sem a foto/identidade do especialista.
        responsaveis_card = ((card or {}).get("apresentacao") or {}).get("responsaveis") or []
        resp_dict = next(
            (r for r in responsaveis_card if isinstance(r, dict) and (r.get("nome") or "").strip() == (esp or "").strip()),
            {"nome": esp},
        )
        esp_avatar_html = resolve_circulo(resp_dict, skill_dir) if skill_dir else f'<span class="circulo-id">{iniciais(esp)}</span>'

        sections.append(
            f'<section data-label="Fechamento {esp}">\n'
            f'  <div class="slide-head">\n'
            f'    <div class="h-left">\n'
            f'      <div class="avatar">{esp_avatar_html}</div>\n'
            f'      <div class="h-divider"></div>\n'
            f'      <div>\n'
            f'        <div class="h-eyebrow">Fechamento {mes_ant} · Especialista {nivel}</div>\n'
            f'        <div class="h-title">{esp}</div>\n'
            f'      </div>\n'
            f'    </div>\n'
            f'    <img src="{ctx.get("ASSET_LOGO_DARK_DATA_URI", "")}" class="h-logo" alt="M7"/>\n'
            f'  </div>\n'
            f'  <div class="slide-body">\n'
            f'    <div class="fech-esp-wrap">\n'
            f'      <div class="fech-vert-wrap">\n'
            f'        <div class="fech-col">\n'
            f'          <div class="fc-head {head_class}">{esp}</div>\n'
            f'          <div class="fc-rows-grid">{rows_html}</div>\n'
            f'        </div>\n'
            f'      </div>\n'
            f'      <div class="fech-esp-side">\n'
            f'        <div class="fes-title">Criadas vs Fechadas · ultimos 6 meses</div>\n'
            f'        {chart_svg}\n'
            f'      </div>\n'
            f'    </div>\n'
            f'  </div>\n'
            f'  <div class="slide-foot">\n'
            f'    <div class="f-meta">Fechamento {mes_ant} · {esp}<span class="dot"></span>{nivel} {vertical}</div>\n'
            f'    <div class="f-num">03{chr(96+idx)}</div>\n'
            f'  </div>\n'
            f'</section>\n'
        )

    return "\n".join(sections)


def _render_fechamento_esp_rank(esp: str, wbr_fech: dict, dados_n5_fech: dict, card: dict) -> str:
    """P2 (2026-05-07): rank por assessor estilo slide Analise — colunas
    Criadas e Fechadas para o mes anterior do esp. Substitui o SVG line chart.

    Le dados_n5_fech (consolidados N5 do ciclo de fechamento — auto-resolved
    via convencao). Fallback graceful se ausente.
    """
    if not dados_n5_fech:
        return (
            '<div style="padding:30px 20px;text-align:center;color:var(--verde-claro);'
            'font-style:italic;font-size:13px;">Dados consolidados N5 do ciclo de '
            'fechamento nao disponiveis. Auto-resolve em <code>02-Controle/{vertical}/'
            '{YYYY-MM}-fechamento/dados/dados-consolidados-{vertical}.json</code>.</div>'
        )

    # Squad whitelist do esp + esp_direct para rank
    squad_wl = _get_squad_whitelist(esp, card)
    squad_norms = {_normalize_assessor_name(a) for a in squad_wl}
    esp_direct_label = f"{esp} (esp)"
    # R7 (2026-05-07): filtrar por mes do fechamento (canonical pode trazer multi-meses)
    fech_mes_prefix = (wbr_fech.get("data_referencia") or "")[:7]

    def _row_in_fech_mes(row):
        if not fech_mes_prefix:
            return True
        rm = str(row.get("mes") or "")[:7]
        return (not rm) or rm == fech_mes_prefix

    # Agrega: por assessor, {criadas_qty, fechadas_won, fechadas_lost, in_squad}
    by_assessor = {}
    # Refator 2026-05-07 round 3: zero-fill TODOS os assessores do squad
    # (mesmo zerados) — paridade visual com slide Analise.
    for a in squad_wl:
        by_assessor[a] = {"criadas": 0, "won": 0, "lost": 0, "in_squad": True}
    # R5-2 (2026-05-07): zero-fill esp_direct também (sempre mostra a linha
    # "{esp} (esp)" no rank, mesmo quando esp nao tem deals atribuidos
    # diretamente — comum em RE sem squad fixo).
    by_assessor[esp_direct_label] = {"criadas": 0, "won": 0, "lost": 0, "in_squad": True}

    def _resolve_a_name(row):
        """Retorna (a_name, in_squad_flag) — esp_direct vs squad/outsider."""
        a_raw = row.get("assessor")
        is_esp_self = a_raw and isinstance(a_raw, str) and _normalize_assessor_name(a_raw) == _normalize_assessor_name(esp)
        if _is_esp_direct(a_raw) or is_esp_self:
            return esp_direct_label, True
        a_name = _resolve_assessor_alias(a_raw, card)
        in_squad = squad_norms and _assessor_in_squad(a_name, squad_norms)
        return a_name, bool(in_squad)

    # Pass 1: criadas (oportunidades_criadas_*) — somar quantidade por assessor
    for entry in dados_n5_fech.get("indicadores", []):
        ind_id = (entry.get("indicator_id") or "").lower()
        if "oportunidades_criadas_" not in ind_id:
            continue
        for row in entry.get("data", []):
            if row.get("nivel") != "N5-Assessor": continue
            if row.get("estagio"): continue
            if row.get("especialista") != esp: continue
            if not _row_in_fech_mes(row): continue
            qty = row.get("quantidade") if row.get("quantidade") is not None else row.get("realizado")
            qty = qty or 0
            if qty <= 0: continue
            a_name, in_squad_flag = _resolve_a_name(row)
            slot = by_assessor.setdefault(a_name, {"criadas": 0, "won": 0, "lost": 0, "in_squad": in_squad_flag})
            slot["criadas"] += qty

    # Pass 2: R7 (2026-05-07) — won/lost por assessor via taxa_conversao_funil_seg
    # (canonical traz total_ganhos + total_perdidos por N5-Assessor). Substitui
    # o `quantidade_*` que so trazia won (sem split visual).
    for entry in dados_n5_fech.get("indicadores", []):
        ind_id = (entry.get("indicator_id") or "").lower()
        if "taxa_conversao_funil_" not in ind_id:
            continue
        for row in entry.get("data", []):
            if row.get("nivel") != "N5-Assessor": continue
            if row.get("estagio"): continue
            if row.get("especialista") != esp: continue
            if not _row_in_fech_mes(row): continue
            won = row.get("total_ganhos") or 0
            lost = row.get("total_perdidos") or 0
            if won + lost <= 0: continue
            a_name, in_squad_flag = _resolve_a_name(row)
            slot = by_assessor.setdefault(a_name, {"criadas": 0, "won": 0, "lost": 0, "in_squad": in_squad_flag})
            slot["won"] += won
            slot["lost"] += lost

    if not by_assessor:
        return (
            '<div style="padding:30px 20px;text-align:center;color:var(--verde-claro);'
            'font-style:italic;font-size:13px;">Sem assessores com criadas ou fechadas '
            'no mes de fechamento.</div>'
        )

    # R7 (2026-05-07): max para escala da bar — usa max(criadas, won+lost) em vez
    # de max(criadas, fechadas) porque "fechadas" passou a ser split won+lost.
    max_v = max((max(s["criadas"], s["won"] + s["lost"]) for s in by_assessor.values()), default=1) or 1

    # Item 10c (2026-05-25): squad agora ordenado por PARETO (criadas + 0.5*won),
    # paridade build_deck_pj2 + img 2/3 PJ2. Antes era alfabetico.
    squad_rows = sorted([(n, m) for n, m in by_assessor.items()
                          if m["in_squad"] and n != esp_direct_label],
                          key=lambda x: -(x[1]["criadas"] + 0.5 * x[1]["won"]))
    esp_direct_row = [(n, m) for n, m in by_assessor.items() if n == esp_direct_label]
    outside_rows = sorted([(n, m) for n, m in by_assessor.items() if not m["in_squad"]],
                            key=lambda x: -(x[1]["criadas"] + x[1]["won"] + x[1]["lost"]))

    def _row_html(name, m, *, italic=False):
        cri = m["criadas"]
        won = m["won"]
        lost = m["lost"]
        cri_w = (cri / max_v * 100) if max_v else 0
        rname_style = ' style="padding:6px 12px;font-style:italic;color:var(--verde-claro);"' if italic else ' style="padding:6px 12px;"'
        rname_class = "rname esp" if "(esp)" in name else "rname"

        # R7 Fechadas split: barra dual won/lost com labels {N}W (preto sobre verde)
        # + {N}L (branco sobre vermelho). Total = won + lost (mostrado a direita).
        fec_total = won + lost
        won_w = (won / max_v * 100) if max_v and won > 0 else 0
        lost_w = (lost / max_v * 100) if max_v and lost > 0 else 0
        # #Img2 (2026-06-03): barra e fonte IGUAIS entre Criadas e Fechadas —
        # ambas height 16px, font-size 11px, line-height 16px, mesma .mini.
        _BAR_H = 16
        if fec_total <= 0:
            fechadas_cell = (
                f'<div class="mini" style="background:#F0F0EE;border-radius:2px;height:{_BAR_H}px;width:100%;position:relative;">'
                f'<div style="position:absolute;top:0;left:6px;color:#79755C;font-size:11px;font-weight:600;line-height:{_BAR_H}px;">0</div>'
                f'</div>'
            )
        else:
            # Item 10c F9 (2026-05-25): cores DS chart seq (verde sage / vermelho WCAG)
            won_seg = (
                f'<div style="background:#6b8e6e;height:100%;width:{won_w:.1f}%;'
                f'display:flex;align-items:center;padding-left:4px;color:#fff;'
                f'font-size:11px;font-weight:600;line-height:{_BAR_H}px;overflow:hidden;'
                f'white-space:nowrap;">{int(won)}W</div>'
            ) if won > 0 else ''
            lost_seg = (
                f'<div style="background:var(--error-text);height:100%;width:{lost_w:.1f}%;'
                f'display:flex;align-items:center;padding-left:4px;color:#fff;'
                f'font-size:11px;font-weight:600;line-height:{_BAR_H}px;overflow:hidden;'
                f'white-space:nowrap;">{int(lost)}L</div>'
            ) if lost > 0 else ''
            fechadas_cell = (
                f'<div class="mini" style="background:#F0F0EE;border-radius:2px;height:{_BAR_H}px;'
                f'width:100%;position:relative;display:flex;overflow:hidden;">'
                f'{won_seg}{lost_seg}'
                f'</div>'
            )

        # #6/#7 (2026-06-03): numero DENTRO da barra (nao fora). Criadas: count
        # dentro da fb; Fechadas: W/L dentro. Removidos os `.vlbl` externos.
        # #Img2 (2026-06-03): mesma altura/fonte/line-height que Fechadas.
        cri_lbl = f'{int(cri)}' if cri else ''
        return (
            f'<div class="rank-row" style="grid-template-columns: 140px 1fr 1fr;">'
            f'  <div class="{rname_class}"{rname_style}>{name}</div>'
            f'  <div class="rcell">'
            f'    <div class="mini" style="height:{_BAR_H}px;">'
            f'      <div class="fb {"fb-mute" if cri == 0 else "fb-lime"}" style="width:{cri_w:.1f}%;min-width:{18 if cri else 0}px;height:100%;font-size:11px;font-weight:600;line-height:{_BAR_H}px;justify-content:flex-start;padding-left:6px;">{cri_lbl}</div>'
            f'    </div>'
            f'  </div>'
            f'  <div class="rcell">'
            f'    {fechadas_cell}'
            f'  </div>'
            f'</div>'
        )

    rows = []
    # R5-2 (2026-05-07): header da section adapta ao caso "sem squad fixo declarado"
    # (RE) vs "squad estruturado" (WL). Cards sem squad mostram "Especialista direto"
    # como header em vez de "Squad X · 0 assessores" (visualmente confuso).
    has_squad = bool(squad_wl)
    if squad_rows or esp_direct_row:
        if has_squad:
            header_squad = f'Squad {primeiro_nome(esp)} · {len(squad_wl)} assessores'
        else:
            header_squad = f'{primeiro_nome(esp)} · sem squad fixo declarado'
        rows.append(f'<div class="rank-section squad" style="grid-template-columns: 140px 1fr 1fr;">{header_squad}</div>')
    for name, m in squad_rows:
        rows.append(_row_html(name, m))
    for name, m in esp_direct_row:
        rows.append(_row_html(name, m))
    if outside_rows:
        outside_header = 'Fora da squad · referência' if has_squad else 'Outros assessores · referência'
        rows.append(f'<div class="rank-section outside" style="grid-template-columns: 140px 1fr 1fr;">{outside_header}</div>')
        # R7 (2026-05-07): mostrar TODOS os outsiders (era [:6]) — total do rank
        # deve igualar o card "Oport. Criadas" do esp.
        for name, m in outside_rows:
            rows.append(_row_html(name, m, italic=True))

    return (
        '<div class="rank-card" style="height:100%;">'
        '<div class="rank-head" style="grid-template-columns: 140px 1fr 1fr;">'
        '  <div></div>'
        '  <div>Criadas</div>'
        '  <div>Fechadas</div>'
        '</div>'
        + "\n".join(rows) +
        '</div>'
    )


def render_diretrizes_slide(diretrizes_data: dict, ctx: dict) -> str:
    """Slide de Diretrizes do mes atual (output da LLM ou override do Card).

    Espera dict com schema diretrizes-prompt.md:
      { foco_do_mes: str, diretrizes: [{titulo, acao, responsavel, metrica_sucesso}],
        riscos_monitorar: [str] }
    """
    if not diretrizes_data:
        return ""

    foco = diretrizes_data.get("foco_do_mes", "")
    diretrizes = diretrizes_data.get("diretrizes", [])
    riscos = diretrizes_data.get("riscos_monitorar", [])
    mes_atual = ctx.get("MES_ANO", "Mes atual")
    vertical = ctx.get("VERTICAL", "")
    nivel = ctx.get("NIVEL", "N3")

    if not foco and not diretrizes:
        # Placeholder graceful para LLM nao gerada
        return (
            f'<section class="diretrizes-section" data-label="Diretrizes {mes_atual}">\n'
            f'  <div class="closing-inner">\n'
            f'    <div class="head-row">\n'
            f'      <h2>Diretrizes <em>{mes_atual}</em></h2>\n'
            f'      <img src="{ctx.get("ASSET_LOGO_OFFWHITE_DATA_URI", "")}" class="logo" alt="M7"/>\n'
            f'    </div>\n'
            f'    <div class="foco-do-mes" style="background:rgba(228,0,20,0.08);border-left-color:var(--error);">\n'
            f'      <span class="fdm-label" style="color:var(--error);">Diretrizes nao geradas</span>\n'
            f'      Preencher manualmente via Card.apresentacao.diretrizes_override ou re-rodar prepare-ritual.\n'
            f'    </div>\n'
            f'  </div>\n'
            f'</section>\n'
        )

    dir_cards = []
    for i, d in enumerate(diretrizes, start=1):
        dir_cards.append(
            f'<div class="dir-card">\n'
            f'  <div class="dc-num">{i:02d}</div>\n'
            f'  <div class="dc-title">{d.get("titulo", "—")}</div>\n'
            f'  <div class="dc-acao">{d.get("acao", "—")}</div>\n'
            f'  <div class="dc-meta">\n'
            f'    <div><span class="k">Responsavel</span><div class="v">{d.get("responsavel", "—")}</div></div>\n'
            f'    <div><span class="k">Metrica de sucesso</span><div class="v">{d.get("metrica_sucesso", "—")}</div></div>\n'
            f'  </div>\n'
            f'</div>'
        )

    riscos_html = ""
    if riscos:
        riscos_li = "\n".join(f"<li>{r}</li>" for r in riscos)
        riscos_html = (
            f'<div class="riscos-row">\n'
            f'  <div class="rr-label">Riscos a monitorar</div>\n'
            f'  <ul class="rr-list">{riscos_li}</ul>\n'
            f'</div>'
        )

    return (
        f'<section class="diretrizes-section" data-label="Diretrizes {mes_atual}">\n'
        f'  <div class="closing-inner">\n'
        f'    <div class="head-row">\n'
        f'      <h2>Diretrizes <em>{mes_atual}</em></h2>\n'
        f'      <img src="{ctx.get("ASSET_LOGO_OFFWHITE_DATA_URI", "")}" class="logo" alt="M7"/>\n'
        f'    </div>\n'
        f'    <div class="foco-do-mes">\n'
        f'      <span class="fdm-label">Foco do mes</span>\n'
        f'      {foco}\n'
        f'    </div>\n'
        f'    <div class="dir-grid">\n'
        f'      {chr(10).join(dir_cards)}\n'
        f'    </div>\n'
        f'    {riscos_html}\n'
        f'  </div>\n'
        f'</section>\n'
    )


def render_subcapa_slide(bloco: str, titulo_main: str, titulo_em: str,
                          foco: str, ciclo_label: str, ctx: dict,
                          slide_num: str = "") -> str:
    """Sub-capa Bloco I/II (Item 10e 2026-05-25) — separador visual escuro
    entre blocos do deck. Paridade PJ2 12/05 imgs 5+6.

    Args:
      bloco: "Bloco I" ou "Bloco II"
      titulo_main: parte fixa do titulo (ex: "Fechamento mes")
      titulo_em: parte destacada lime (ex: "passado")
      foco: descricao do bloco
      ciclo_label: meses cobertos (ex: "2026-04 · 2026-05")
    """
    vertical = ctx.get("VERTICAL", "")
    nivel = ctx.get("NIVEL", "N3")
    bloco_id = bloco.replace("Bloco ", "").lower()  # "i" ou "ii"
    return (
        f'<section class="subcapa" data-label="{bloco}">\n'
        f'  <div class="sc-grid-bg"></div>\n'
        f'  <div class="sc-eyebrow">{bloco}</div>\n'
        f'  <div class="sc-title">{titulo_main} <em>{titulo_em}</em></div>\n'
        f'  <div class="sc-meta-grid">\n'
        f'    <div class="sc-meta-label">Bloco</div>\n'
        f'    <div class="sc-meta-value"><strong>{bloco}</strong></div>\n'
        f'    <div class="sc-meta-label">Foco</div>\n'
        f'    <div class="sc-meta-value">{foco}</div>\n'
        f'    <div class="sc-meta-label">Ciclo</div>\n'
        f'    <div class="sc-meta-value">{ciclo_label}</div>\n'
        f'  </div>\n'
        f'  <img src="{ctx.get("ASSET_LOGO_OFFWHITE_DATA_URI", "")}" class="sc-logo" alt="M7"/>\n'
        f'  <div class="sc-foot">{bloco} · {nivel} {vertical} · slide {slide_num}</div>\n'
        f'</section>\n'
    )


def render_indicadores_alerta_slide(wbr_fech: dict, ctx: dict, card: dict = None) -> str:
    """Slide "Indicadores em Alerta" — causa-raiz cards por esp/desdobramento
    com indicador vermelho no fechamento. NEW (Item 10d 2026-05-25).

    Regra (usuario): TODO indicador vermelho no fechamento por especialista
    (ou canal, para PJ2) DEVE ter um card aqui com causa-raiz.

    Layout (paridade PJ2 12/05 img 4):
      - Header eyebrow "BLOCO I · ANALISE DO QUE DEU ERRADO"
      - Titulo "Indicadores em alerta"
      - Callout vermelho com texto editorial "Leitura critica..."
      - Grid 2 colunas — 1 coluna por especialista (ou top-N esp se >2)
      - Cards: {label} {valor %} + descricao causa-raiz curta
    """
    if not wbr_fech:
        return ""
    indicadores = wbr_fech.get("indicadores", {})
    if card is None:
        card = ctx.get("_card") or {}
    mes_ant = wbr_fech.get("data_referencia", "")[:7] or "Mes anterior"
    vertical = ctx.get("VERTICAL", "")
    nivel = ctx.get("NIVEL", "N3")

    # Coletar especialistas do Card (ordem de exibicao)
    responsaveis = (card.get("apresentacao", {}) or {}).get("responsaveis", []) or []
    esp_list = [r.get("nome") for r in responsaveis if r.get("nome")]
    if not esp_list:
        # Fallback: extrair de n2 de algum indicator
        for ind in indicadores.values():
            n2 = ind.get("n2") or {}
            if isinstance(n2, dict):
                esp_list = list(n2.keys())
                break
    if not esp_list:
        return ""

    # Para cada esp, coletar indicators vermelhos com causa-raiz
    def _collect_red_for_esp(esp: str) -> list[dict]:
        out = []
        for ind_id, ind in indicadores.items():
            if not isinstance(ind, dict):
                continue
            n2 = ind.get("n2") or {}
            e_data = n2.get(esp) or {}
            if not e_data:
                continue
            status = (e_data.get("status") or "").lower()
            if status != "vermelho":
                continue
            label = ind.get("label") or ind_id
            real = e_data.get("realizado_mtd") or e_data.get("realizado") or e_data.get("pct") or 0
            meta = e_data.get("meta_mes") or e_data.get("meta") or 0
            pct = None
            if isinstance(real, (int, float)) and isinstance(meta, (int, float)) and meta:
                pct = round((float(real) / float(meta)) * 100)
            # Causa-raiz: prioridade n2_data > ind top-level > nota Card
            causa = (e_data.get("causa_raiz_resumo")
                     or ind.get("causa_raiz_resumo")
                     or e_data.get("obs")
                     or "")
            out.append({
                "ind_id": ind_id,
                "label": label,
                "real": real,
                "meta": meta,
                "pct": pct,
                "causa": causa[:280] if causa else "",
            })
        return out

    # Render
    cols_html = []
    for esp in esp_list[:2]:  # max 2 colunas (paridade visual PJ2 img 4)
        cards = _collect_red_for_esp(esp)
        col_cards_html = ""
        if cards:
            for c in cards:
                pct_txt = f"{c['pct']}<span class=\"ac-pct-sym\">%</span>" if c['pct'] is not None else "—"
                sub_real = ""
                if isinstance(c['real'], (int, float)) and isinstance(c['meta'], (int, float)) and c['meta']:
                    sub_real = f"{c['real']:g} vs meta {c['meta']:g}"
                desc = c['causa'] or "Causa-raiz pendente — diagnostico em proxima cadencia."
                col_cards_html += (
                    f'<div class="alerta-card">'
                    f'<div class="ac-label">{c["label"]}</div>'
                    f'<div class="ac-pct">{pct_txt}</div>'
                    f'<div class="ac-sub">{sub_real}</div>'
                    f'<div class="ac-desc">{desc}</div>'
                    f'</div>'
                )
        else:
            col_cards_html = (
                f'<div class="alerta-card" style="grid-template-columns:1fr;">'
                f'<div class="ac-desc" style="border-top:none;padding-top:0;color:var(--verde-claro);font-style:italic;">'
                f'Nenhum indicador em alerta para {esp} neste fechamento.'
                f'</div></div>'
            )
        cols_html.append(
            f'<div class="alerta-col">'
            f'<div class="alerta-col-header">{esp}</div>'
            f'{col_cards_html}'
            f'</div>'
        )

    # Slide numero — 03d (depois dos esp slides) ou seguinte
    n_esp = len(esp_list)
    slide_num = f"03{chr(96 + n_esp + 1)}"  # ex: 2 esps -> 03c+1 = 03d

    return (
        f'<section data-label="Indicadores em Alerta {mes_ant}">\n'
        f'  <div class="slide-head">\n'
        f'    <div class="h-left">\n'
        f'      <img src="{ctx.get("ASSET_LOGO_DARK_DATA_URI", "")}" class="h-logo" alt="M7"/>\n'
        f'      <div class="h-divider"></div>\n'
        f'      <div>\n'
        f'        <div class="h-eyebrow">Bloco I · Analise do que deu errado</div>\n'
        f'        <div class="h-title">Indicadores em alerta</div>\n'
        f'      </div>\n'
        f'    </div>\n'
        f'  </div>\n'
        f'  <div class="slide-body">\n'
        f'    <div class="alerta-callout">\n'
        f'      <div class="ac-eyebrow">Causa-raiz dos lead indicators em vermelho</div>\n'
        f'      <div class="ac-text">Leitura critica dos indicadores que ficaram abaixo da meta — '
        f'<em>diagnostico por causa-raiz</em> em vez de diretriz prescritiva.</div>\n'
        f'    </div>\n'
        f'    <div class="alerta-grid">\n'
        f'      {chr(10).join(cols_html)}\n'
        f'    </div>\n'
        f'  </div>\n'
        f'  <div class="slide-foot">\n'
        f'    <div class="f-meta">Bloco I · Indicadores em alerta · {nivel} {vertical}</div>\n'
        f'    <div class="f-num">{slide_num}</div>\n'
        f'  </div>\n'
        f'</section>\n'
    )


def render_fechamento_dispatch(data: dict, ctx: dict, wbr_fechamento_path: Path = None,
                                  diretrizes_json_path: Path = None,
                                  dados_n5_fech_path: Path = None,
                                  force: bool = False, skill_dir: Path = None) -> dict:
    """Master function — retorna placeholders dos slides extras de fechamento.

    Regras de ativacao:
      - force=True (modo fechamento ou combinado): popula sempre, ignorando is_first.
      - force=False (modo atual ou auto-detect legado): popula apenas se
        data.wbr.is_first_ritual_of_month=True (comportamento retro-compat).

    Step 4 (2026-05-11): param `force` adicionado para o dispatcher de modos.
    Quando o usuario seleciona --modo fechamento ou --modo combinado em qualquer
    semana, o fech_dispatch e' ativado mesmo fora do 1o ritual do mes.
    """
    is_first = resolve_is_first_ritual(data.get("wbr", {}))  # top-level OU meta. (2026-06-18)
    empty = {
        "SUBCAPA_BLOCO_I": "",
        "FECHAMENTO_N1_SLIDE": "",
        "FECHAMENTO_ESP_BLOCKS": "",
        "INDICADORES_ALERTA_SLIDE": "",
        "SUBCAPA_BLOCO_II": "",
        "DIRETRIZES_SLIDE": "",
    }
    if not (force or is_first):
        return empty

    # Carrega WBR de fechamento
    wbr_fech = None
    if wbr_fechamento_path and wbr_fechamento_path.exists():
        try:
            wbr_fech = json.loads(wbr_fechamento_path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[build_deck] WARN: falha ao ler WBR fechamento {wbr_fechamento_path}: {e}", file=sys.stderr)

    # P2 (2026-05-07): Carrega dados consolidados N5 do ciclo de fechamento
    # (auto-resolve via convencao se nao explicitado)
    dados_n5_fech = None
    if not dados_n5_fech_path and wbr_fechamento_path:
        # Convencao: ../dados/dados-consolidados-{vertical}.json
        candidate = wbr_fechamento_path.parent.parent / "dados" / f"dados-consolidados-{data.get('wbr', {}).get('vertical', '')}.json"
        if candidate.exists():
            dados_n5_fech_path = candidate
            print(f"[build_deck] Auto-resolved dados_n5_fech: {candidate}", file=sys.stderr)
    if dados_n5_fech_path and dados_n5_fech_path.exists():
        try:
            dados_n5_fech = json.loads(dados_n5_fech_path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[build_deck] WARN: falha ao ler dados N5 fechamento: {e}", file=sys.stderr)

    # Carrega diretrizes JSON (output da LLM ou override do Card)
    diretrizes_data = None
    # Override do Card tem precedencia
    card_apres = (data.get("card", {}).get("apresentacao") or {})
    if card_apres.get("diretrizes_override"):
        diretrizes_data = card_apres["diretrizes_override"]
        print(f"[build_deck] Diretrizes via Card.apresentacao.diretrizes_override (sem chamada LLM)", file=sys.stderr)
    elif diretrizes_json_path and diretrizes_json_path.exists():
        try:
            diretrizes_data = json.loads(diretrizes_json_path.read_text(encoding="utf-8"))
            print(f"[build_deck] Diretrizes via {diretrizes_json_path}", file=sys.stderr)
        except Exception as e:
            print(f"[build_deck] WARN: falha ao ler diretrizes JSON: {e}", file=sys.stderr)

    card = data.get("card", {})
    # Refator 2026-05-07: passa card via ctx['_card'] para fech slides usarem metas Card override
    ctx_with_card = dict(ctx)
    ctx_with_card["_card"] = card
    # Sub-capas Bloco I/II — renderizadas so quando modo=combinado (Item 10e)
    # Determinado pelo MODO_PHASES.combinado.sub_capas=True (caller injeta force=True).
    modo_phases = ctx.get("_modo_phases") or {}
    render_subcapas = modo_phases.get("sub_capas", False)

    mes_fech = (wbr_fech or {}).get("data_referencia", "")[:7] if wbr_fech else ""
    mes_atual = data.get("wbr", {}).get("data_referencia", "")[:7]
    ciclo_label = f"{mes_fech} · {mes_atual}" if mes_fech else mes_atual
    vertical_label = ctx.get("VERTICAL", "")

    subcapa_i = ""
    subcapa_ii = ""
    if render_subcapas:
        subcapa_i = render_subcapa_slide(
            "Bloco I", "Fechamento mes", "passado",
            f"Visao geral {vertical_label} + detalhado por especialista + indicadores em alerta",
            ciclo_label, ctx_with_card, slide_num="03"
        )
        subcapa_ii = render_subcapa_slide(
            "Bloco II", "Mes ate", "agora",
            f"Matriz + analise por especialista + pipeline {vertical_label}",
            ciclo_label, ctx_with_card, slide_num="09"
        )

    return {
        "SUBCAPA_BLOCO_I": subcapa_i,
        "FECHAMENTO_N1_SLIDE": render_fechamento_n1_slide(wbr_fech, ctx_with_card, dados_n5_fech),
        "FECHAMENTO_ESP_BLOCKS": render_fechamento_esp_slides(wbr_fech, ctx_with_card, dados_n5_fech, card, skill_dir),
        "INDICADORES_ALERTA_SLIDE": render_indicadores_alerta_slide(wbr_fech, ctx_with_card, card),
        "SUBCAPA_BLOCO_II": subcapa_ii,
        "DIRETRIZES_SLIDE": render_diretrizes_slide(diretrizes_data or {}, ctx),
    }


# ============================================================
# Dispatch table de modos (Step 4 / 2026-05-11)
# ============================================================
# Declara quais fases (grupos de slides) cada modo renderiza.
#
# Fases:
#   - dashboard:  matriz + PA + consolidado + esp_blocks (slides do mes corrente)
#   - fechamento: fechamento_n1 + fechamento_esp + diretrizes (slides do mes anterior)
#   - sub_capas:  separadores visuais "Fechamento" / "Mes ate agora" (NAO implementado
#                 ainda — placeholder para Step 8 quando portar render_subcapa do V13).
#
# Compatibilidade retro-compat preservada:
#   - modo=atual      + is_first=False → dashboard ON,  fech OFF (fluxo legado normal)
#   - modo=combinado  + is_first=True  → dashboard ON,  fech ON  (fluxo legado 1o ritual)
#   - modo=combinado  + is_first=False → dashboard ON,  fech ON  (NOVO: forca fech)
#   - modo=fechamento + qualquer       → dashboard OFF, fech ON  (NOVO: fech puro)
#
# Quando dashboard OFF: matriz/pa/consolidado/esp_blocks viram dicts vazios e o
# template ainda renderiza os <section> mas sem conteudo (placeholders nao
# substituidos). Para deck PJ2 modo=fechamento isso e' OK porque ele usara
# template ritual-pj2.tmpl.html que NAO tem esses sections.
MODO_PHASES = {
    "atual":      {"dashboard": True,  "fechamento": False, "sub_capas": False},
    "fechamento": {"dashboard": False, "fechamento": True,  "sub_capas": False},
    "combinado":  {"dashboard": True,  "fechamento": True,  "sub_capas": True},
}


# ============================================================
# Main
# ============================================================

def apply_substitutions(template: str, placeholders: dict) -> str:
    """Substitute placeholders. ESP_BLOCKS_HTML first (it may contain other placeholders)."""
    out = template
    # First pass — substitute the big block placeholder
    if "ESP_BLOCKS_HTML" in placeholders:
        out = out.replace("{{ESP_BLOCKS_HTML}}", str(placeholders["ESP_BLOCKS_HTML"]))
    # Then everything else
    for k, v in placeholders.items():
        if k.startswith("_") or k == "ESP_BLOCKS_HTML":
            continue
        out = out.replace("{{" + k + "}}", str(v))
    # Strip any remaining {{ESP_NOME}} from instructional comments (harmless residue)
    out = re.sub(r"\{\{ESP_NOME\}\}", "<!-- esp -->", out)
    return out


def _resolve_effective_modo(args, card: dict, data: dict) -> str:
    """Resolve modo efetivo via precedencia:

    1. CLI --modo (se != "auto")
    2. card.apresentacao.modo OU card.metadata.modo (se != "auto")
    3. data.wbr.is_first_ritual_of_month=True → "combinado"
    4. default → "atual"

    Comportamento retro-compat: Cards N3 sem `modo` declarado em semana
    normal → "atual" (comportamento atual). Cards N3 sem `modo` em 1o
    ritual do mes → "combinado" (formaliza o auto-detect atual via
    `render_fechamento_dispatch`).
    """
    cli_modo = getattr(args, "modo", None)
    if cli_modo and cli_modo != "auto":
        return cli_modo
    apresent = (card or {}).get("apresentacao") or {}
    meta = (card or {}).get("metadata") or {}
    declared = apresent.get("modo") or meta.get("modo")
    if declared and declared != "auto":
        return declared
    wbr_blk = (data or {}).get("wbr", {})
    if resolve_is_first_ritual(wbr_blk):  # top-level OU meta. (helper unificado 2026-06-18)
        return "combinado"
    return "atual"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--wbr-data-json", required=True, type=Path)
    parser.add_argument("--card", required=True, type=Path)
    parser.add_argument("--clickup-tasks", type=Path)
    parser.add_argument("--action-report", type=Path)
    parser.add_argument("--prev-wbr-data-json", type=Path)
    parser.add_argument("--dados-consolidados", type=Path,
                        help="JSON consolidado N5 (m7-controle E2). Alimenta rank rows + Destaque/Estagnacao.")
    parser.add_argument("--wbr-fechamento", type=Path,
                        help="C8: WBR data.json do mes fechado. Auto-resolve via glob se omitido. Usado quando is_first_ritual_of_month=true.")
    parser.add_argument("--diretrizes-json", type=Path,
                        help="C8: JSON com diretrizes do mes (output da LLM ou override). Schema em references/diretrizes-prompt.md. Override do Card.apresentacao.diretrizes_override tem precedencia.")
    parser.add_argument("--skill-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--modo", choices=["atual", "fechamento", "combinado", "auto"],
                        default="auto",
                        help="Modo do deck. atual=so mes corrente; fechamento=so mes anterior; "
                             "combinado=fechamento+atual; auto=deduz de Card.apresentacao.modo ou "
                             "is_first_ritual_of_month (default).")
    parser.add_argument("--per-assessor-csv-dir", type=Path, default=None,
                        help="TEMPORARIO (Step 7 workaround V13): diretorio com dumps Bitrix "
                             "(deals_consorcios.csv, deals_seguros.csv, stagehistory_*.json, "
                             "users.json) para popular per-assessor PJ2. Removido quando indicators "
                             "_pj2 populam wbr.indicadores.X.por_assessor diretamente.")
    parser.add_argument("--strict", action="store_true",
                        help="Eleva placeholders {{...}} nao-substituidos a erro fatal "
                             "(exit code 2). Default: warning apenas.")
    args = parser.parse_args()

    print(f"[build_deck] Loading data from WBR JSON + Card YAML")
    # Auto-resolve PREV_WBR_DATA_JSON quando nao passado explicitamente —
    # glob `../*/wbr/wbr-{vertical}-*.data.json` a partir do WBR atual + pegar imediatamente anterior.
    prev_path = args.prev_wbr_data_json
    if not prev_path:
        prev_path = _auto_resolve_prev_wbr_data_json(args.wbr_data_json)
        if prev_path:
            print(f"[build_deck] Auto-resolved PREV_WBR_DATA_JSON: {prev_path}")
        else:
            print(f"[build_deck] PREV_WBR_DATA_JSON nao encontrado — coluna Delta vs S{{prev}} ficara vazia")
    data = load_data(args.wbr_data_json, args.card, prev_path)

    # Step 8 (2026-05-12): detectar Card PJ2 multi-vertical → dispatch para sidecar build_deck_pj2.
    use_pj2 = is_pj2_card(data.get("card", {}))

    # Guarda de visibilidade (2026-06-18): o builder N3 ainda tem lookups hardcoded
    # de 'especialista' (Tier-4 nao portado — ver nota ~447). Se um Card NAO-pj2
    # declara eixo != especialista, os breakdowns por responsavel renderizariam
    # "Sem Responsavel" em SILENCIO. Torna o acoplamento latente visivel (nao refatora).
    if not use_pj2:
        _eixo = _eixo_key(data.get("card", {}))
        if _eixo != "especialista":
            print(f"[build_deck] WARN: Card declara label_responsavel='{_eixo}' mas o builder N3 "
                  f"tem lookups hardcoded de 'especialista' (Tier-4 pendente) — breakdowns por "
                  f"{_eixo} podem aparecer como 'Sem Responsavel'. Use build_deck_pj2 ou conclua o Tier-4.",
                  file=sys.stderr)
    if use_pj2:
        # Sidecar `build_deck_pj2.py` (portado do V13) tem suas proprias 17 render_* +
        # logica de canal mapping + Pareto + velocimetros. Invocamos via subprocess para
        # isolar dependencias (pandas) e nao misturar fluxos.
        import subprocess
        sidecar = Path(__file__).parent / "build_deck_pj2.py"
        if not sidecar.exists():
            print(f"[build_deck] ERRO: sidecar PJ2 nao encontrado em {sidecar}", file=sys.stderr)
            sys.exit(2)
        cmd = [sys.executable, str(sidecar)]
        # Propagar argumentos relevantes
        cmd.extend(["--wbr-data-json", str(args.wbr_data_json)])
        cmd.extend(["--card", str(args.card)])
        cmd.extend(["--skill-dir", str(args.skill_dir)])
        cmd.extend(["--output", str(args.output)])
        if args.clickup_tasks:
            cmd.extend(["--clickup-tasks", str(args.clickup_tasks)])
        if args.action_report:
            cmd.extend(["--action-report", str(args.action_report)])
        if args.dados_consolidados:
            cmd.extend(["--dados-consolidados", str(args.dados_consolidados)])
        if args.prev_wbr_data_json:
            cmd.extend(["--prev-wbr-data-json", str(args.prev_wbr_data_json)])
        if args.per_assessor_csv_dir:
            cmd.extend(["--per-assessor-csv-dir", str(args.per_assessor_csv_dir)])
        print(f"[build_deck] Card PJ2 detectado — delegando para sidecar build_deck_pj2.py")
        print(f"[build_deck] cmd: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=False)
        sys.exit(result.returncode)

    # Caminho normal (N3 single-vertical)
    template_variant = "default"
    print(f"[build_deck] Loading template (variant={template_variant}) + assets from {args.skill_dir}")
    template = load_template(args.skill_dir, variant=template_variant)
    template, esp_subtemplate = extract_esp_subtemplate(template)
    assets = load_assets(args.skill_dir)

    # Resolve modo efetivo (CLI > Card > is_first_ritual_of_month > atual).
    # Step 4 (2026-05-11): resolve modo efetivo e seleciona fases via MODO_PHASES.
    effective_modo = _resolve_effective_modo(args, data.get("card", {}), data)
    phases = MODO_PHASES.get(effective_modo) or MODO_PHASES["atual"]
    print(f"[build_deck] effective_modo={effective_modo} phases={phases} "
          f"(CLI={args.modo}, "
          f"card.apresentacao.modo={(data.get('card', {}).get('apresentacao') or {}).get('modo')}, "
          f"is_first_ritual_of_month={resolve_is_first_ritual(data.get('wbr', {}))})")

    clickup_tasks = load_clickup_tasks(args.clickup_tasks) if args.clickup_tasks else []

    # C3 (2026-05-07): enriquece tasks com flag criada_em_ritual_anterior.
    # Cycle dir = parent do wbr_data_json (estrutura: <vertical>/<data>/wbr/file.data.json).
    cycle_dir = args.wbr_data_json.parent.parent if args.wbr_data_json else None
    if clickup_tasks and cycle_dir:
        clickup_tasks = enrich_tasks_ritual_anterior(clickup_tasks, cycle_dir)
    # Deviation cause report (optional, used para mapear indicador -> causa-raiz no Slide 5)
    deviation_md = ""
    if args.action_report and args.action_report.exists():
        dev_path = args.action_report.parent / "deviation-cause-report.md"
        if dev_path.exists():
            deviation_md = dev_path.read_text(encoding="utf-8")
    # Dados consolidados N5 (opcional, alimenta rank rows do Slide 7 + funnel N5 + Destaque/Estagnacao)
    # FIX #2a (2026-05-14): auto-resolve quando --dados-consolidados nao passado. O funnel
    # do Slide Pipeline ficava vazio ("0 nos estagios · N em pos-venda/outros") quando o
    # caller esquecia o arg. Convencao: {cycle_folder}/dados/dados-consolidados-{vertical}.json
    # onde cycle_folder = wbr_data_json.parent.parent.
    dados_n5 = {}
    dados_path = args.dados_consolidados
    if not dados_path:
        cycle_folder = args.wbr_data_json.parent.parent
        vertical = data.get("wbr", {}).get("vertical") or (data.get("card", {}).get("metadata", {}) or {}).get("vertical_crm", "")
        if vertical:
            candidate = cycle_folder / "dados" / f"dados-consolidados-{vertical}.json"
            if candidate.exists():
                dados_path = candidate
                print(f"[build_deck] Auto-resolved dados_consolidados: {candidate}", file=sys.stderr)
    if dados_path and dados_path.exists():
        try:
            dados_n5 = json.loads(dados_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"[build_deck] WARNING: failed to parse dados_consolidados: {e}", file=sys.stderr)
    # FIX rodada 7 issue 5 — aplica Card.apresentacao.overrides_ritual.n5_by_esp em dados_n5
    _apply_n5_overrides(data["card"], dados_n5)

    # FIX (2026-05-14) Bug 1 — Sem Especialista bridge: WBR canonical analyst v1.1
    # consolida `n1.realizado` como SUM(n2.{esp_visible}), excluindo Sem Especialista
    # bridge (caso WL: scope = Claudia+Tarcisio, mas raw data tem ~R$ 190K em
    # assessores nao-mapeados que pertencem a vertical via RE bridge).
    # Expomos dados_consolidados no `data` dict para que _resolve_n2 possa derivar
    # Sem Especialista = N1_raw (das rows N1-Escritorio) - SUM(n2_visible_esps).
    data["dados_consolidados"] = dados_n5

    print(f"[build_deck] Rendering slides")
    # S1-A1#2 (2026-05-15): expoe effective_modo para render_capa_agenda_meta
    # decidir se o badge "· fechamento DD/MM" aparece na capa.
    data["_effective_modo"] = effective_modo
    ctx = render_capa_agenda_meta(data)
    # Refator 2026-05-07: expor URIs dos logos no ctx para slides Fechamento
    # (que usam ctx.get("ASSET_LOGO_DARK_DATA_URI") inline).
    ctx["ASSET_LOGO_OFFWHITE_DATA_URI"] = assets.get("ASSET_LOGO_OFFWHITE_DATA_URI", "")
    ctx["ASSET_LOGO_DARK_DATA_URI"] = assets.get("ASSET_LOGO_DARK_DATA_URI", "")

    # Fase "dashboard": matriz + PA + consolidado + esp_blocks (slides mes corrente)
    # Step 4: pulada quando modo=fechamento (deck puro de mes anterior).
    if phases["dashboard"]:
        matriz = render_matriz(data, ctx)
        pa = render_pa_slides(data, clickup_tasks, deviation_report_md=deviation_md)
        consolidado = render_consolidado_encerramento(data, ctx)
        esp_blocks_html = []
        for idx, esp in enumerate(ctx["_esp_list"]):
            esp_blocks_html.append(render_esp_block(esp, idx, data, ctx, esp_subtemplate,
                                                      assets=assets, dados_n5=dados_n5,
                                                      skill_dir=args.skill_dir))
        esp_blocks = "\n".join(esp_blocks_html)
        # S1-A1#8 (2026-05-15): Gatekeeper #17 — cross-slide esp value consistency.
        # Roda apos renders para validar coerencia Consolidado N3 ↔ Dashboard esp.
        _gatekeeper_17_consolidado_vs_dashboard(data, ctx.get("_esp_list", []))
    else:
        matriz, pa, consolidado = {}, {}, {}
        esp_blocks = ""
        print(f"[build_deck] phase dashboard SKIPPED (modo={effective_modo})")

    # Fase "fechamento": slides do mes anterior (visao N1 + esp + diretrizes).
    # Auto-resolve wbr-fechamento se nao passado.
    # Step 4: force=True quando modo in (fechamento, combinado) — ignora is_first_ritual.
    # Item 10e (2026-05-25): injeta `_modo_phases` no ctx para render_fechamento_dispatch
    # decidir se renderiza sub-capas.
    ctx["_modo_phases"] = phases
    if phases["fechamento"]:
        wbr_fech_path = args.wbr_fechamento
        if not wbr_fech_path:
            mes_ant = data.get("wbr", {}).get("mes_ciclo_anterior")
            wbr_fech_path = _auto_resolve_wbr_fechamento(args.wbr_data_json, mes_ant)
            if wbr_fech_path:
                print(f"[build_deck] Auto-resolved WBR fechamento: {wbr_fech_path}")
        fechamento_ph = render_fechamento_dispatch(
            data, ctx, wbr_fech_path, args.diretrizes_json, force=True, skill_dir=args.skill_dir
        )
    else:
        # modo=atual: mantem comportamento legado — popula somente se is_first=True.
        wbr_fech_path = args.wbr_fechamento
        if not wbr_fech_path:
            mes_ant = data.get("wbr", {}).get("mes_ciclo_anterior")
            wbr_fech_path = _auto_resolve_wbr_fechamento(args.wbr_data_json, mes_ant)
            if wbr_fech_path:
                print(f"[build_deck] Auto-resolved WBR fechamento: {wbr_fech_path}")
        fechamento_ph = render_fechamento_dispatch(
            data, ctx, wbr_fech_path, args.diretrizes_json, force=False, skill_dir=args.skill_dir
        )

    # Combine all placeholders
    all_ph = {}
    all_ph.update(assets)
    all_ph.update(ctx)
    all_ph.update(matriz)
    all_ph.update(pa)
    all_ph.update(consolidado)
    all_ph.update(fechamento_ph)
    all_ph["ESP_BLOCKS_HTML"] = esp_blocks

    print(f"[build_deck] Substituting {len(all_ph)} placeholders")
    final_html = apply_substitutions(template, all_ph)

    # Edit #19 (2026-05-13): remover slides PA quando PA_TOTAL=0 (ciclo sem PAs ativas).
    # Wrapper BEGIN_PA_SLIDES/END_PA_SLIDES no template (ritual.tmpl.html) marca os
    # 2 slides (PA Status + PA Vencendo). Quando PA_TOTAL == "0", regex remove o bloco.
    # Quando PA_TOTAL > 0, remove apenas os comentarios markers (mantendo os slides).
    pa_total_val = (pa or {}).get("PA_TOTAL", "0")
    try:
        pa_total_int = int(pa_total_val)
    except (TypeError, ValueError):
        pa_total_int = 0
    if pa_total_int == 0:
        before_len = len(final_html)
        final_html = re.sub(
            r"<!-- BEGIN_PA_SLIDES.*?<!-- END_PA_SLIDES -->",
            "",
            final_html,
            flags=re.DOTALL,
        )
        removed = before_len - len(final_html)
        if removed > 0:
            print(f"[build_deck] Edit #19: PA_TOTAL=0 → removidos slides PA "
                  f"({removed:,} bytes)")
    else:
        # Limpa os markers para nao poluir o HTML final.
        final_html = re.sub(r"<!-- BEGIN_PA_SLIDES[^>]*-->\s*", "", final_html)
        final_html = re.sub(r"<!-- END_PA_SLIDES -->\s*", "", final_html)

    # Sanity check — any leftover {{...}} placeholders
    leftover = re.findall(r"\{\{[A-Z_0-9]+\}\}", final_html)
    if leftover:
        unique = sorted(set(leftover))
        msg = f"[build_deck] {'ERROR' if args.strict else 'WARNING'}: " \
              f"{len(unique)} placeholder(s) nao substituidos: {unique[:10]}"
        print(msg, file=sys.stderr)
        if args.strict:
            sys.exit(2)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(final_html, encoding="utf-8")
    print(f"[build_deck] OK. Output: {args.output} ({len(final_html):,} bytes)")
    print(f"[build_deck] Slides totais: {ctx['_total_slides']} (7 + 3*{ctx['_n_especialistas']})")
    print(f"[build_deck] Tempo total agenda: {ctx['_total_min']} min")


if __name__ == "__main__":
    main()
