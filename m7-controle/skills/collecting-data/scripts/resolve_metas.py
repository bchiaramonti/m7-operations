#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G2.2 pre-E3: resolve metas de todas as fontes e grava metas-resolvidas.json.

Roda apos E2 (collecting-data Fase 3) e ANTES de E3 (analyzing-deviations).
Substitui inject_metas_ppi.py e resolve_kpi_m1_meta.py (ambos removidos).

Fontes consultadas (por prioridade):
  1. m7Prata.vw_ciclo_metas_ppi  -- PPIs de funil (via meta_resolver.py)
  2. m7Bronze.investimento_tb_dashboard_componente_universal_dados -- KPIs mensais
  3. m7Bronze.investimento_tb_meta_escritorio -- quantidade_seguros (quando saudavel)
  4. Card YAML -- fallback para metas fixas e quando ClickHouse offline

Offline-safe: se ClickHouse indisponivel, grava offline_fallback=true.
O analyst lera este JSON em E3-E6; quando offline_fallback=true, emite WARN e
usa o Card como complemento.

Uso:
    python resolve_metas.py \\
        --card {card_path} --vertical {vertical} \\
        --mes {YYYY-MM-01} --cycle-folder {cycle_folder} \\
        [--bib-scripts {dir}] [--dry-run]

ARMADILHA: na tabela dashboard_componente, filtrar por `data` (mes de competencia),
NAO por `data_ref` (data de ingestao -- fixo em 2026-05-07 para todas as linhas).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

# ---------------------------------------------------------------------------
# Mapeamento dashboard_componente: indicator_id -> ID da tabela
# Filtro: id_escritorio=35, data='{mes}' (coluna data, NAO data_ref)
# ---------------------------------------------------------------------------
DASHBOARD_COMP: dict[str, int] = {
    "quantidade_consorcio_mensal": 280,
    "volume_seguros_mensal":       281,
    "receita_consorcio_mensal":    283,
    "volume_consorcio_mensal":     284,
    "receita_seguros_mensal":      285,
}

# BUG TEMP: colunas da tabela meta_escritorio estao com ordens trocadas.
# Remover flag quando a tabela for corrigida pela TI.
META_ESCRITORIO_BUG_ACTIVE = True


# ---------------------------------------------------------------------------
# Bootstrap meta_resolver
# ---------------------------------------------------------------------------

def _load_resolver(bib_scripts: str | None):
    candidates: list[str] = []
    if bib_scripts:
        candidates.append(bib_scripts)
    candidates.append(str(
        Path.home() / "OneDrive - MULTI7 CAPITAL CONSULTORIA LTDA"
        / "Arquivos de Bruno Chiaramonti - desempenho" / "01-Metas"
        / "Biblioteca-de-Indicadores" / "scripts"
    ))
    for c in candidates:
        p = Path(c) / "meta_resolver.py"
        if p.is_file():
            if c not in sys.path:
                sys.path.insert(0, c)
            import meta_resolver as mr  # noqa: PLC0415
            import m7_extract_utils as u  # noqa: PLC0415
            return mr, u
    raise SystemExit(
        "ERRO: meta_resolver.py nao encontrado. Passe --bib-scripts <dir>."
    )


# ---------------------------------------------------------------------------
# Resolucao dashboard_componente (KPIs mensais)
# ---------------------------------------------------------------------------

def _fetch_dashboard_comp(u, mes: str, mes_next: str,
                          ids: list[int]) -> dict[int, dict[str, float | None]]:
    """Retorna {id: {'M0': value, 'M+1': value}} para os IDs pedidos.

    IMPORTANTE: filtrar por `data` (mes de competencia), NAO por `data_ref`.
    """
    if not ids:
        return {}
    ids_str = ", ".join(str(i) for i in ids)
    df = u.query_clickhouse(
        "SELECT id_dashboard_componente, data, meta "
        "FROM m7Bronze.investimento_tb_dashboard_componente_universal_dados "
        "WHERE id_escritorio = '35' "
        f"  AND id_dashboard_componente IN ({ids_str}) "
        f"  AND data IN ('{mes}', '{mes_next}') "
        "ORDER BY id_dashboard_componente, data",
    )
    result: dict[int, dict[str, float | None]] = {}
    for _, row in df.iterrows():
        comp_id = int(row["id_dashboard_componente"])
        data_str = str(row["data"])[:7]
        meta_val = float(row["meta"]) if row["meta"] is not None else None
        entry = result.setdefault(comp_id, {"M0": None, "M+1": None})
        if data_str == mes[:7]:
            entry["M0"] = meta_val
        elif data_str == mes_next[:7]:
            entry["M+1"] = meta_val
    return result


# ---------------------------------------------------------------------------
# Resolucao meta_escritorio (quantidade_seguros)
# ---------------------------------------------------------------------------

def _fetch_meta_escritorio(u) -> float | None:
    if META_ESCRITORIO_BUG_ACTIVE:
        return None
    try:
        df = u.query_clickhouse(
            "SELECT apolice_seguros "
            "FROM m7Bronze.investimento_tb_meta_escritorio "
            "WHERE id_escritorio = '35' "
            "ORDER BY data_ref DESC LIMIT 1"
        )
        if df.empty:
            return None
        val = df.iloc[0]["apolice_seguros"]
        return float(val) if val is not None else None
    except Exception as e:
        print(f"  WARN meta_escritorio: {e}")
        return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _card_metas_ppi(card: dict) -> dict[str, dict]:
    # metas_ppi top-level (PPIs de funil)
    result = {k: v for k, v in (card.get("metas_ppi") or {}).items()
              if isinstance(v, dict)}
    # kpi_references com regras_meta (KPIs mensais como receita/volume/taxa_conversao)
    for ref in card.get("kpi_references") or []:
        ind_id = ref.get("indicator_id")
        if ind_id and ind_id not in result and ref.get("regras_meta"):
            result[ind_id] = dict(ref["regras_meta"])
    return result


def _expected_meta_indicators(card: dict) -> set[str]:
    """Enumera, de forma INDEPENDENTE de _card_metas_ppi, todo indicator_id do
    Card que deveria ter meta resolvida. Usado pelo guard de cobertura (Melhoria #3).

    Deliberadamente NAO reusa _card_metas_ppi: se aquela funcao regredir (ex: parar
    de ler kpi_references, como o bug de 2026-06-30), o guard ainda enumera o
    indicador aqui e detecta que ficou sem meta — em E2, nao 4 fases depois no E6.

    Criterio de 'deveria ter meta': aparece em metas_ppi (top-level) OU e um
    kpi_reference com regras_meta nao-vazio. Indicadores informativos (kpi_reference
    sem regras_meta) ficam de fora — nao se espera meta deles."""
    expected: set[str] = set()
    for k, v in (card.get("metas_ppi") or {}).items():
        if isinstance(v, dict):
            expected.add(k)
    for ref in card.get("kpi_references") or []:
        ind_id = ref.get("indicator_id")
        if ind_id and ref.get("regras_meta"):
            expected.add(ind_id)
    return expected


def _has_resolved_meta(entry: dict) -> bool:
    """True se o entry resolvido tem ALGUMA meta numerica utilizavel (N1, M+1,
    N2/por_canal, derivado ou _pending conhecido). Distingue 'tem entry' de
    'tem meta' — quantidade pode ter N1=card_fixo SEM valor mas M+1 com valor."""
    if not isinstance(entry, dict):
        return False
    if entry.get("source") == "derivado" or "_pending" in entry:
        return True
    _NUM_FIELDS = ("value", "value_volume", "qty", "valor", "volume", "pct_ativas_max")
    for nivel in ("N1", "M+1", "M0"):
        sub = entry.get(nivel)
        if isinstance(sub, dict) and any(sub.get(f) is not None for f in _NUM_FIELDS):
            return True
    for grp in ("N2", "por_canal"):
        sub = entry.get(grp)
        if isinstance(sub, dict):
            for ref_vals in sub.values():
                if isinstance(ref_vals, dict) and any(
                        ref_vals.get(f) is not None for f in _NUM_FIELDS):
                    return True
    return False


def _mes_seguinte(mes: str) -> str:
    y, m = int(mes[:4]), int(mes[5:7])
    m += 1
    if m > 12:
        m, y = 1, y + 1
    return f"{y}-{m:02d}-01"


# ---------------------------------------------------------------------------
# Core: build output
# ---------------------------------------------------------------------------

def resolve(card: dict, vertical: str, mes: str, mr, u) -> tuple[dict, bool]:
    offline = False
    query_errors: list[str] = []  # erros de QUERY/SCHEMA (bug, nao offline) — Melhoria #1
    mes_next = _mes_seguinte(mes)
    indicadores: dict[str, Any] = {}
    sources_used: list[str] = []
    card_metas = _card_metas_ppi(card)
    query_err_cls = getattr(sys.modules.get("meta_resolver", None),
                            "MetaResolverQueryError", None)
    offline_cls = getattr(sys.modules.get("meta_resolver", None),
                          "MetaResolverOffline", None)

    def _handle_ch_exc(stage: str, e: Exception) -> bool:
        """Classifica excecao de fetch. Retorna True se foi OFFLINE (rede).
        Query/schema error → registra em query_errors (NAO marca offline)."""
        if query_err_cls and isinstance(e, query_err_cls):
            print(f"  ERRO QUERY {stage} (bug deterministico, NAO e offline): {e}")
            query_errors.append(f"{stage}: {e}")
            return False
        if offline_cls and isinstance(e, offline_cls):
            print(f"  WARN OFFLINE {stage}: {e}")
            return True
        # Excecao inesperada (nao veio classificada do meta_resolver): tratar como
        # bug visivel, nao mascarar como offline.
        print(f"  ERRO {stage} (nao classificado, tratado como bug): {e}")
        query_errors.append(f"{stage}: {e}")
        return False

    # --- 1. PPIs de funil via vw_ciclo_metas_ppi ----------------------------
    try:
        idx = mr.build_index(mr.fetch(vertical, mes))
        cfg = mr.VERTICAIS[mr.vertical_key(vertical)]
        is_pj2 = cfg.get("canal_dim", False)

        for ind_id, subdict in card_metas.items():
            for field in ("qty", "volume", "valor"):
                mapping = mr.map_card_to_table(ind_id, field, is_pj2)
                if mapping is None:
                    continue
                r_n1 = mr.resolve(idx, vertical, ind_id, field, nivel="N1")
                if r_n1 is None:
                    continue
                entry = indicadores.setdefault(ind_id, {})
                fk = "value_volume" if field == "volume" else "value"
                entry.setdefault("N1", {})[fk] = r_n1["value"]
                entry["N1"]["source"] = "ciclo_metas_ppi"
                if "unit" in r_n1:
                    entry["N1"]["unit"] = r_n1["unit"]

                if is_pj2:
                    for canal in ("investimentos", "credito", "outros_m7"):
                        r_c = mr.resolve(idx, vertical, ind_id, field,
                                         nivel="CANAL", ref=canal)
                        if r_c is None:
                            continue
                        entry.setdefault("por_canal", {}) \
                             .setdefault(canal, {})[fk] = r_c["value"]
                        entry["por_canal"][canal]["source"] = "ciclo_metas_ppi"
                else:
                    for esp in cfg.get("squad") or []:
                        r_n2 = mr.resolve(idx, vertical, ind_id, field,
                                          nivel="N2", ref=esp)
                        if r_n2 is None:
                            continue
                        entry.setdefault("N2", {}) \
                             .setdefault(esp, {})[fk] = r_n2["value"]
                        entry["N2"][esp]["source"] = "ciclo_metas_ppi"

        sources_used.append("ciclo_metas_ppi")

    except Exception as e:
        if _handle_ch_exc("ciclo_metas_ppi", e):
            offline = True

    # --- 2. KPIs mensais via dashboard_componente ---------------------------
    relevant = {ind: cid for ind, cid in DASHBOARD_COMP.items()
                if ind in card_metas}
    if relevant and not offline:
        try:
            dc = _fetch_dashboard_comp(u, mes, mes_next, list(relevant.values()))
            for ind_id, comp_id in relevant.items():
                row = dc.get(comp_id)
                if not row:
                    continue
                entry = indicadores.setdefault(ind_id, {})
                if row["M0"] is not None:
                    entry.setdefault("N1", {}).update({
                        "value": row["M0"],
                        "source": "dashboard_componente",
                        "dashboard_componente_id": comp_id,
                    })
                if row["M+1"] is not None:
                    entry.setdefault("M+1", {}).update({
                        "value": row["M+1"],
                        "source": "dashboard_componente",
                        "dashboard_componente_id": comp_id,
                    })
            sources_used.append("dashboard_componente")
        except Exception as e:
            if _handle_ch_exc("dashboard_componente", e):
                offline = True

    # --- 3. quantidade_seguros via meta_escritorio --------------------------
    _QTDE_SEG = ("quantidade_seguros_mensal_wl", "quantidade_seguros_mensal_re",
                 "quantidade_seguros_mensal")
    if not META_ESCRITORIO_BUG_ACTIVE and not offline:
        val = _fetch_meta_escritorio(u)
        if val is not None:
            for ind_id in _QTDE_SEG:
                if ind_id in card_metas:
                    indicadores.setdefault(ind_id, {}) \
                               .setdefault("N1", {}).update({
                                   "value": val,
                                   "source": "meta_escritorio",
                               })
            sources_used.append("meta_escritorio")
    elif META_ESCRITORIO_BUG_ACTIVE:
        for ind_id in _QTDE_SEG:
            if ind_id in card_metas:
                indicadores.setdefault(ind_id, {}) \
                           ["_pending"] = "meta_escritorio_bug"

    # --- 4. Derivados (ticket_medio) ----------------------------------------
    for ind_id in card_metas:
        if ind_id.startswith("ticket_medio"):
            indicadores.setdefault(ind_id, {}).update({
                "source": "derivado",
                "formula": "receita / quantidade",
            })

    # --- 5. Fixas do Card (fallback para tudo nao resolvido) ----------------
    for ind_id, subdict in card_metas.items():
        if ind_id in indicadores and "N1" in indicadores[ind_id]:
            continue  # ja resolvido por tabela
        entry = indicadores.setdefault(ind_id, {})
        n1 = entry.setdefault("N1", {})
        n1.setdefault("source", "card_fixo")
        for field in ("valor", "qty", "volume", "pct_ativas_max"):
            if field in subdict:
                n1[field] = subdict[field]
        por_esp = subdict.get("por_especialista") or {}
        if por_esp:
            for esp, esp_vals in por_esp.items():
                entry.setdefault("N2", {})[esp] = {
                    "source": "card_fixo",
                    **{k: v for k, v in esp_vals.items()
                       if k not in ("fonte",)},
                }
    if "card_fixo" not in sources_used:
        sources_used.append("card_fixo")

    # --- Guard de cobertura (Melhoria #3) -----------------------------------
    # Todo indicador do Card que deveria ter meta foi resolvido com valor?
    # Enumeracao independente p/ pegar regressao de _card_metas_ppi na origem (E2).
    expected = _expected_meta_indicators(card)
    coverage_gaps = sorted(
        ind_id for ind_id in expected
        if not _has_resolved_meta(indicadores.get(ind_id, {}))
    )

    return {
        "_schema": "metas-resolvidas v1.1",
        "_generated_at": datetime.now(timezone.utc).isoformat(),
        "vertical": vertical,
        "mes": mes,
        "mes_seguinte": mes_next,
        "offline_fallback": offline,
        "query_errors": query_errors,
        "coverage_gaps": coverage_gaps,
        "sources_used": sources_used,
        "indicadores": indicadores,
    }, offline


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description="Resolve metas pre-E3 (G2.2)")
    ap.add_argument("--card", required=True, help="Caminho para card_*.yaml")
    ap.add_argument("--vertical", required=True,
                    help="consorcios|seguros_wl|seguros_re|pj2")
    ap.add_argument("--mes", required=True,
                    help="YYYY-MM-01 (mes de competencia do ciclo)")
    ap.add_argument("--cycle-folder", required=True,
                    help="Pasta do ciclo (metas-resolvidas.json sera gravado em dados/)")
    ap.add_argument("--bib-scripts", default=None,
                    help="Caminho para a pasta com meta_resolver.py")
    ap.add_argument("--dry-run", action="store_true",
                    help="Mostra resultado sem gravar arquivo")
    args = ap.parse_args()

    mr, u = _load_resolver(args.bib_scripts)

    card = yaml.safe_load(Path(args.card).read_text(encoding="utf-8"))
    print(f"resolve_metas | vertical={args.vertical} mes={args.mes}"
          f"{' [DRY-RUN]' if args.dry_run else ''}")

    data, offline = resolve(card, args.vertical, args.mes, mr, u)

    ind = data["indicadores"]
    n_total = len(ind)
    n_tabela = sum(1 for v in ind.values()
                   if isinstance(v.get("N1"), dict)
                   and v["N1"].get("source") not in ("card_fixo", "derivado", None))
    n_fixo = sum(1 for v in ind.values()
                 if isinstance(v.get("N1"), dict)
                 and v["N1"].get("source") == "card_fixo")
    n_deriv = sum(1 for v in ind.values() if v.get("source") == "derivado")

    print(f"  {n_total} indicadores: {n_tabela} de tabela | "
          f"{n_fixo} fixos Card | {n_deriv} derivados")

    query_errors = data.get("query_errors") or []
    coverage_gaps = data.get("coverage_gaps") or []
    if query_errors:
        print(f"  ERRO: {len(query_errors)} erro(s) de QUERY/SCHEMA (bug, NAO offline):")
        for qe in query_errors:
            print(f"    - {qe}")
    if coverage_gaps:
        print(f"  ERRO COBERTURA: {len(coverage_gaps)} indicador(es) do Card SEM meta resolvida:")
        for g in coverage_gaps:
            print(f"    - {g}")
    if offline:
        print("  WARN: ClickHouse offline (rede) -- offline_fallback=true no JSON")

    if not args.dry_run:
        out_dir = Path(args.cycle_folder) / "dados"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "metas-resolvidas.json"
        out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                            encoding="utf-8")
        print(f"  -> {out_path}")
    else:
        print("\n--- DRY-RUN: metas-resolvidas.json ---")
        print(json.dumps(data, ensure_ascii=False, indent=2))

    # Exit codes (aditivos; 0=ok, !=0=atencao):
    #   2 = erro de query/schema (bug deterministico — corrigir o script/SQL)
    #   3 = gap de cobertura (meta declarada no Card nao resolvida)
    #   1 = offline por rede (fallback card_fixo aplicado — pode ser aceitavel)
    if query_errors:
        return 2
    if coverage_gaps:
        return 3
    return 1 if offline else 0


if __name__ == "__main__":
    sys.exit(main())
