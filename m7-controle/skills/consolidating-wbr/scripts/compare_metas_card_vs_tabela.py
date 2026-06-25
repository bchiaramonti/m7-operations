#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fase 0 (paridade, READ-ONLY) da migracao de metas PPI.

Cruza, meta a meta, os valores da tabela ClickHouse ``m7Prata.ciclo_metas_ppi``
contra os blocos ``metas_ppi:`` dos Cards de Performance atuais, para uma
vertical/mes do ciclo. Emite um relatorio com divergencias > tolerancia (default
5%) ANTES de qualquer religamento do pipeline ou edicao de Card.

NAO escreve nada. Apenas SELECTs no ClickHouse + leitura dos YAML dos Cards.

Uso:
    python compare_metas_card_vs_tabela.py --mes 2026-06-01
    python compare_metas_card_vs_tabela.py --vertical seguros_wl --mes 2026-06-01
    python compare_metas_card_vs_tabela.py --json relatorio-paridade.json

De-para e regras de escopo estao documentados em VERTICAIS abaixo e foram
derivados do snapshot real da tabela (ver plano da migracao). Pontos-chave:

  * A tabela colapsa Seguros WL e RE em ``vertical='Seg'`` e distingue squads
    apenas por ``nome_referencia``/``id_colaborador`` -> cada Card filtra so o
    seu squad; a linha literal ``N1 Escritorio M7`` (Seg) = WL+RE somados e NAO
    corresponde ao N1 de nenhum Card isolado.
  * Consorcios NAO tem linha N1 na tabela -> N1 = SUM(N2).
  * ``pct_ativas_max`` (Card, em %) <-> ``*_pct_ativas`` (tabela, ratio) => /100.
  * ``oportunidades_ativas_funil.volume`` (Card) <-> ``vol_oportunidades_ativas_*``.
  * receita/volume/quantidade/ticket MENSAIS de Cons/Seg nao estao na tabela
    (cobertos pela tabela universal dashboard_componente) -> ignorados aqui.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import unicodedata
from pathlib import Path
from typing import Any

import yaml

# ---------------------------------------------------------------------------
# Bootstrap: localizar a Biblioteca-de-Indicadores/scripts (m7_extract_utils)
# ---------------------------------------------------------------------------

def _find_bib_scripts(explicit: str | None) -> Path:
    """Resolve o diretorio scripts/ da Biblioteca (sede de m7_extract_utils)."""
    if explicit:
        p = Path(explicit)
        if (p / "m7_extract_utils.py").is_file():
            return p
        raise SystemExit(f"ERRO: --bib-scripts={explicit} nao contem m7_extract_utils.py")
    # Caminho canonico no OneDrive do desempenho
    candidates = [
        Path(os.environ.get("M7_BIB_SCRIPTS", "")),
        Path.home() / "OneDrive - MULTI7 CAPITAL CONSULTORIA LTDA"
        / "Arquivos de Bruno Chiaramonti - desempenho" / "01-Metas"
        / "Biblioteca-de-Indicadores" / "scripts",
    ]
    for c in candidates:
        if c and (c / "m7_extract_utils.py").is_file():
            return c
    raise SystemExit(
        "ERRO: nao encontrei m7_extract_utils.py. Passe --bib-scripts <dir> "
        "ou exporte M7_BIB_SCRIPTS."
    )


def _find_cards_dir(explicit: str | None) -> Path:
    if explicit:
        p = Path(explicit)
        if p.is_dir():
            return p
        raise SystemExit(f"ERRO: --cards-dir={explicit} nao existe")
    cand = (Path.home() / "OneDrive - MULTI7 CAPITAL CONSULTORIA LTDA"
            / "Arquivos de Bruno Chiaramonti - desempenho" / "02-Controle"
            / "Cards-de-Performance")
    if cand.is_dir():
        return cand
    raise SystemExit("ERRO: nao encontrei Cards-de-Performance. Passe --cards-dir <dir>")


# ---------------------------------------------------------------------------
# Normalizacao de nomes (Card sem acento <-> tabela com acento)
# ---------------------------------------------------------------------------

def norm(s: str | None) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.strip().lower()


# ---------------------------------------------------------------------------
# Configuracao das verticais: Card -> (vertical tabela, squad, dimensao)
# ---------------------------------------------------------------------------
# squad: lista de nomes (como aparecem na tabela) que pertencem ao Card.
#   - Para Seg, isso separa WL de RE dentro de vertical='Seg'.
#   - Para Cons, e o conjunto completo de N2.
# canal_dim: se True, a vertical e dimensionada por canal_pj2 (PJ2), nao por
#   id_colaborador; N1 = SUM(canais).
VERTICAIS: dict[str, dict[str, Any]] = {
    "consorcios": {
        "card": "Consorcios/card_con_n3_001.yaml",
        "tabela_vertical": "Cons",
        "squad": ["Douglas Silva", "Tereza Bernardo"],
        "n1_na_tabela": False,          # Cons nao tem linha N1 -> SUM(N2)
        "canal_dim": False,
    },
    "seguros_wl": {
        "card": "Seguros/card_seg_wl_n3_001.yaml",
        "tabela_vertical": "Seg",
        "squad": ["Claudia Moraes", "Tarcisio Catunda"],
        "n1_na_tabela": True,           # ha N1 literal, mas e WL+RE -> usamos SUM(squad)
        "canal_dim": False,
    },
    "seguros_re": {
        "card": "Seguros/card_seg_re_n3_001.yaml",
        "tabela_vertical": "Seg",
        "squad": ["Emmanuel Martins", "Samuel Sinval"],
        "n1_na_tabela": True,
        "canal_dim": False,
    },
    "pj2": {
        "card": "PJ2/card_pj2_n2_001.yaml",
        "tabela_vertical": "PJ2",
        "squad": [],                    # dimensionado por canal
        "n1_na_tabela": False,          # so ha linhas por canal -> SUM(canais)
        "canal_dim": True,
    },
}


# ---------------------------------------------------------------------------
# De-para: (card_indicator_id, field) -> (table_indicator_id, unit_factor)
# ---------------------------------------------------------------------------
# Retorna None quando o par nao tem equivalente na tabela (deve ser ignorado:
# metas mensais de receita/volume/qty/ticket, ticket_medio de funil derivado).

# Markers que identificam um indicador de funil (usados p/ detectar typo no stem
# no catch-all de map_card_to_table). _unmapped_warned dedupa o WARN por id.
_FUNIL_MARKERS = ("oportunidades", "funil", "taxa_conversao", "tempo_de_ciclo", "estagnad")
_unmapped_warned: set[str] = set()


def _strip_squad_suffix(ind: str) -> str:
    """Card usa _seg_wl/_seg_re; tabela usa _seg. Remove _wl/_re mantendo _seg."""
    for suf in ("_seg_wl", "_seg_re"):
        if ind.endswith(suf):
            return ind[: -len(suf)] + "_seg"
    # _wl / _re soltos (ex: ticket_medio_premio_seg_wl)
    if ind.endswith("_wl"):
        return ind[:-3]
    if ind.endswith("_re"):
        return ind[:-3]
    return ind


# campos do Card que sao metas mensais (cobertas pela tabela universal) -> ignorar
_MENSAIS_PREFIX = (
    "receita_seguros_mensal", "receita_consorcio_mensal",
    "volume_seguros_mensal", "volume_consorcio_mensal",
    "quantidade_seguros_mensal", "quantidade_consorcio_mensal",
    "ticket_medio_premio", "ticket_medio_consorcio", "ticket_medio_seguros",
    "receita_seguros_re_bitrix_ganhos",
)


def map_card_to_table(card_ind: str, field: str, pj2: bool) -> tuple[str, float] | None:
    base = _strip_squad_suffix(card_ind)

    # PJ2 receitas: receita_*_mensal -> receita_*_mensal_pj2 (existe na tabela)
    if pj2 and card_ind in ("receita_consorcio_mensal", "receita_seguros_mensal"):
        if field in ("valor", "valor_proximo_mes"):
            return f"{card_ind}_pj2", 1.0
        return None

    # demais metas mensais de Cons/Seg: nao estao na tabela
    if any(base.startswith(p) for p in _MENSAIS_PREFIX):
        return None

    # estagnadas: pct_ativas_max (%) -> *_pct_ativas (ratio)
    if base.startswith("oportunidades_estagnadas_funil"):
        if field == "pct_ativas_max":
            tbl = base if base.endswith("_pct_ativas") else base + ("_pct_ativas")
            if pj2:
                tbl = _pj2_suffix(base) + "_pct_ativas"
            return tbl, 0.01
        return None  # 'qty' contextual da estagnada nao tem meta na tabela

    # ativas: qty -> oportunidades_ativas_funil*, volume -> vol_oportunidades_ativas_funil*
    if base.startswith("oportunidades_ativas_funil"):
        if field in ("qty", "qty_proximo_mes"):
            return (_pj2_suffix(base) if pj2 else base), 1.0
        if field in ("volume", "volume_proximo_mes"):
            volbase = "vol_" + base
            return (_pj2_suffix(volbase) if pj2 else volbase), 1.0
        return None  # ticket_medio derivado (nao tem meta propria)

    # criadas / sem_atividade / sem_movimentacao: qty -> mesmo id
    if base.startswith(("oportunidades_criadas_funil",
                        "oportunidades_sem_atividade_planejada_funil",
                        "oportunidades_sem_movimentacao_funil")):
        if field in ("qty", "qty_proximo_mes", "valor", "valor_proximo_mes"):
            return (_pj2_suffix(base) if pj2 else base), 1.0
        return None

    # taxa_conversao / tempo_de_ciclo: valor -> mesmo id (ratio/days, sem fator)
    if base.startswith(("taxa_conversao_funil", "tempo_de_ciclo_funil")):
        if field in ("valor", "valor_proximo_mes"):
            return (_pj2_suffix(base) if pj2 else base), 1.0
        return None

    # catch-all: nao casou nenhum mapeamento conhecido. Se o id PARECE indicador de
    # funil (mas escapou de todos os prefixos), e provavel TYPO no stem -> antes,
    # drop SILENCIOSO (a comparacao nunca rodava, sem flag). 2026-06-18: warn
    # visivel + deduplicado. Nao afeta ids legitimamente fora da tabela (mensais ja
    # tratados acima; ids sem marker de funil sao ignorados sem ruido).
    if card_ind not in _unmapped_warned and any(m in base for m in _FUNIL_MARKERS):
        _unmapped_warned.add(card_ind)
        print(f"WARN: '{card_ind}' (base='{base}') parece indicador de funil mas nao casou "
              f"nenhum mapeamento conhecido — possivel typo no id; NAO sera comparado "
              f"com a tabela.", file=sys.stderr)
    return None


def _pj2_suffix(base: str) -> str:
    """Insere o sufixo _con_pj2 / _seg_pj2 esperado pela tabela PJ2.

    Card PJ2 usa nomes-base (Cons) e sufixo _seg (Seguros). A tabela usa
    _con_pj2 e _seg_pj2. vol_ e _pct_ativas sao tratados pelo chamador.
    """
    if base.endswith("_pct_ativas"):
        core = base[: -len("_pct_ativas")]
        return _pj2_core(core) + "_pct_ativas"
    return _pj2_core(base)


def _pj2_core(base: str) -> str:
    # Card PJ2: indicadores Cons usam nome-base (sem sufixo) -> _con_pj2;
    # ja sufixados com _con/_seg recebem so _pj2 (tabela: *_con_pj2 / *_seg_pj2).
    if base.endswith(("_con", "_seg")):
        return base + "_pj2"
    return base + "_con_pj2"


# ---------------------------------------------------------------------------
# Comparacao
# ---------------------------------------------------------------------------

def _is_num(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _diff_pct(card_v: float, tbl_v: float) -> float | None:
    if tbl_v == 0:
        return None if card_v == 0 else float("inf")
    return abs(card_v - tbl_v) / abs(tbl_v)


def compare_vertical(key: str, cfg: dict, cards_dir: Path, table_rows: list[dict],
                     mes: str, tol: float) -> list[dict]:
    """Retorna lista de findings (dicts) para uma vertical."""
    card_path = cards_dir / cfg["card"]
    card = yaml.safe_load(card_path.read_text(encoding="utf-8"))
    metas_ppi = card.get("metas_ppi", {}) or {}
    pj2 = cfg["canal_dim"]
    squad_norm = {norm(s) for s in cfg["squad"]}

    # Index tabela por (indicator_id) -> {norm_nome: meta, ...} + n1 literal + soma squad
    by_ind: dict[str, dict[str, float]] = {}
    n1_literal: dict[str, float] = {}
    for r in table_rows:
        ind = r["indicator_id"]
        nome = r["nome_referencia"]
        meta = float(r["meta"])
        by_ind.setdefault(ind, {})
        if r["id_colaborador"] is None and norm(nome).startswith("n1 escritorio"):
            n1_literal[ind] = meta
        else:
            by_ind[ind][norm(nome)] = meta

    findings: list[dict] = []

    def squad_sum(ind: str) -> tuple[float | None, int]:
        """Soma metas da tabela para os membros do squad deste Card."""
        rows = by_ind.get(ind, {})
        if pj2:
            vals = [v for v in rows.values()]  # todos os canais
        else:
            vals = [v for n, v in rows.items() if n in squad_norm]
        if not vals:
            return None, 0
        return sum(vals), len(vals)

    for card_ind, meta_def in metas_ppi.items():
        if card_ind == "_nota" or not isinstance(meta_def, dict):
            continue
        por_esp = meta_def.get("por_especialista") or {}

        # Campos numericos do nivel N1 do Card (qty/volume/valor/pct_ativas_max...)
        for field, card_val in list(meta_def.items()):
            if field in ("direction", "nota", "fonte", "fonte_n1", "fonte_futura",
                         "id_dashboard_componente", "regra_split", "por_especialista",
                         "formula"):
                continue
            mapping = map_card_to_table(card_ind, field, pj2)
            if mapping is None:
                continue
            tbl_ind, factor = mapping

            # --- N1 ---
            if _is_num(card_val):
                card_n1 = float(card_val) * factor
                tbl_sum, n = squad_sum(tbl_ind)
                tbl_lit = n1_literal.get(tbl_ind)
                # ratio/days nao somam: usam o valor do membro (todos iguais)
                is_ratio_days = factor != 1.0 or tbl_ind.startswith(
                    ("taxa_conversao_funil", "tempo_de_ciclo_funil")
                ) or tbl_ind.endswith("_pct_ativas")
                if is_ratio_days and by_ind.get(tbl_ind):
                    # pega valor representativo (primeiro do squad/canal)
                    rep = squad_sum(tbl_ind)
                    members = [v for nn, v in by_ind[tbl_ind].items()
                               if pj2 or nn in squad_norm]
                    tbl_n1 = members[0] if members else tbl_lit
                else:
                    tbl_n1 = tbl_sum
                d = _diff_pct(card_n1, tbl_n1) if (tbl_n1 is not None) else None
                findings.append({
                    "vertical": key, "card_indicator": card_ind, "field": field,
                    "table_indicator": tbl_ind, "nivel": "N1",
                    "card_value": round(card_n1, 4),
                    "table_value": None if tbl_n1 is None else round(tbl_n1, 4),
                    "table_n1_literal": None if tbl_lit is None else round(tbl_lit, 4),
                    "diff_pct": None if d is None else (round(d * 100, 2) if d != float("inf") else "inf"),
                    "flag": _flag(card_n1, tbl_n1, d, tol),
                })
            elif str(card_val).lower() == "pendente":
                tbl_sum, n = squad_sum(tbl_ind)
                findings.append({
                    "vertical": key, "card_indicator": card_ind, "field": field,
                    "table_indicator": tbl_ind, "nivel": "N1",
                    "card_value": "pendente",
                    "table_value": None if tbl_sum is None else round(tbl_sum, 4),
                    "diff_pct": None,
                    "flag": "TABELA_PREENCHE" if tbl_sum is not None else "AMBOS_VAZIO",
                })

            # --- N2 por especialista ---
            for esp, esp_def in por_esp.items():
                if not isinstance(esp_def, dict):
                    continue
                ev = esp_def.get(field)
                if not _is_num(ev):
                    continue
                card_n2 = float(ev) * factor
                tbl_n2 = by_ind.get(tbl_ind, {}).get(norm(esp))
                d = _diff_pct(card_n2, tbl_n2) if tbl_n2 is not None else None
                findings.append({
                    "vertical": key, "card_indicator": card_ind, "field": field,
                    "table_indicator": tbl_ind, "nivel": f"N2:{esp}",
                    "card_value": round(card_n2, 4),
                    "table_value": None if tbl_n2 is None else round(tbl_n2, 4),
                    "diff_pct": None if d is None else (round(d * 100, 2) if d != float("inf") else "inf"),
                    "flag": _flag(card_n2, tbl_n2, d, tol),
                })

    return findings


def _flag(card_v, tbl_v, d, tol) -> str:
    if tbl_v is None:
        return "SO_NO_CARD"          # tabela nao cobre -> Card permanece SoT
    if d is None:
        return "OK"
    if d == float("inf"):
        return "DIVERGENTE"
    return "OK" if d <= tol else "DIVERGENTE"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description="Paridade metas Card vs ciclo_metas_ppi (read-only)")
    ap.add_argument("--mes", default="2026-06-01", help="Primeiro dia do mes do ciclo (YYYY-MM-01)")
    ap.add_argument("--vertical", choices=list(VERTICAIS) + ["all"], default="all")
    ap.add_argument("--tol", type=float, default=0.05, help="Tolerancia relativa (default 0.05 = 5%%)")
    ap.add_argument("--bib-scripts", default=None)
    ap.add_argument("--cards-dir", default=None)
    ap.add_argument("--json", default=None, help="Grava relatorio JSON nesse caminho")
    ap.add_argument("--only-diffs", action="store_true", help="Exibe so DIVERGENTE/SO_NO_CARD/TABELA_PREENCHE")
    args = ap.parse_args()

    bib = _find_bib_scripts(args.bib_scripts)
    cards_dir = _find_cards_dir(args.cards_dir)
    sys.path.insert(0, str(bib))
    import m7_extract_utils as u  # noqa: E402

    # Snapshot mais recente por (vertical) para o mes
    df = u.query_clickhouse(
        """
        SELECT vertical, indicator_id, id_colaborador, nome_referencia,
               canal_pj2, meta, unit, direction
        FROM m7Prata.ciclo_metas_ppi
        WHERE data = {mes:Date}
          AND (data_ref, ingestion_tstamp) IN (
              SELECT data_ref, max(ingestion_tstamp)
              FROM m7Prata.ciclo_metas_ppi GROUP BY data_ref
          )
        """,
        parameters={"mes": args.mes},
    )
    rows_all = df.to_dict("records")
    # normaliza id_colaborador NaN -> None
    for r in rows_all:
        cid = r.get("id_colaborador")
        r["id_colaborador"] = None if (cid is None or (isinstance(cid, float) and cid != cid)) else int(cid)

    verticais = list(VERTICAIS) if args.vertical == "all" else [args.vertical]
    all_findings: list[dict] = []
    for key in verticais:
        cfg = VERTICAIS[key]
        tbl_rows = [r for r in rows_all if r["vertical"] == cfg["tabela_vertical"]]
        all_findings.extend(compare_vertical(key, cfg, cards_dir, tbl_rows, args.mes, args.tol))

    _print_report(all_findings, args.mes, args.tol, args.only_diffs)

    if args.json:
        Path(args.json).write_text(json.dumps(all_findings, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nRelatorio JSON: {args.json}")

    divs = [f for f in all_findings if f["flag"] == "DIVERGENTE"]
    return 1 if divs else 0


def _print_report(findings: list[dict], mes: str, tol: float, only_diffs: bool) -> None:
    print("=" * 100)
    print(f"PARIDADE metas_ppi (Card)  vs  m7Prata.ciclo_metas_ppi   |  mes={mes}  tol={tol*100:.0f}%")
    print("=" * 100)
    by_flag: dict[str, int] = {}
    for f in findings:
        by_flag[f["flag"]] = by_flag.get(f["flag"], 0) + 1

    header = f"{'vertical':<11} {'card_indicator':<42} {'fld':<14} {'nivel':<22} {'card':>13} {'tabela':>13} {'diff%':>7} flag"
    last_v = None
    for f in sorted(findings, key=lambda x: (x["vertical"], x["card_indicator"], x["nivel"])):
        if only_diffs and f["flag"] in ("OK",):
            continue
        if f["vertical"] != last_v:
            print("\n" + header)
            print("-" * 100)
            last_v = f["vertical"]
        cv = f["card_value"]; tv = f["table_value"]; dp = f["diff_pct"]
        cv = f"{cv:,.2f}" if isinstance(cv, (int, float)) else str(cv)
        tv = "—" if tv is None else (f"{tv:,.2f}" if isinstance(tv, (int, float)) else str(tv))
        dp = "" if dp is None else str(dp)
        mark = "  " if f["flag"] == "OK" else ">>"
        print(f"{mark}{f['vertical']:<9} {f['card_indicator']:<42} {f['field']:<14} {f['nivel']:<22} {cv:>13} {tv:>13} {dp:>7} {f['flag']}")

    print("\n" + "=" * 100)
    print("RESUMO:", ", ".join(f"{k}={v}" for k, v in sorted(by_flag.items())))
    print("Legenda: OK=bate (<=tol) | DIVERGENTE=>tol | SO_NO_CARD=tabela nao cobre (Card SoT) | "
          "TABELA_PREENCHE=Card pendente e tabela tem | AMBOS_VAZIO")
    print("=" * 100)


if __name__ == "__main__":
    sys.exit(main())
