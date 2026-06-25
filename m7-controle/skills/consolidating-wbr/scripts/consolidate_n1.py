#!/usr/bin/env python3
"""consolidate_n1.py — Consolida WBRs N2 num WBR N1 de empresa (F1 — 2026-06-10).

Lê o Card N1-empresa (kpi_references + tipo_realizacao/regras_meta) e N WBRs N2
(wbr-*.data.json no schema canonical padrao) e agrega cada KPI conforme a regra:
  - tipo_realizacao=aditivo    -> realizado_n1 = SUM(realizado dos N2);
                                  meta_n1 = SUM(meta dos N2)  (ou meta_escritorio do card, se houver)
  - tipo_realizacao!=aditivo   -> NAO somar (ex: ratio/pct/media). realizado/meta N1
                                  ficam None + warning; exigem fonte/regra propria
                                  (espelha card_inv_n1_001.regras_meta: faturamento usa
                                   meta_escritorio independente; rentabilidade e media nao-aditiva).

Emite wbr-n1-{cod}-{periodo}.data.json no schema canonical (consumivel pelo Claude
Design e por validate-painel.py). Tolera WBRs com schema forkado (ex: PJ2 `_pj2_n2`,
cujo `indicadores` nao e dict id->valores) — sao pulados com warning.

NAO substitui o ciclo run-weekly: e a peca de JUNCAO N2->N1 (a "junção dos N2, não 100%"
do plano). run-weekly roda 1 Card; este consolida varios WBRs N2 ja gerados.

Uso:
    python consolidate_n1.py \
      --n1-card /path/card_m7_n1_001.yaml \
      --n2-wbr /path/wbr-investimentos-2026-06.data.json \
      --n2-wbr /path/wbr-pj2-2026-06.data.json \
      [--n2-wbr ...] \
      --periodo 2026-06 \
      --output /path/wbr-n1-m7-2026-06.data.json
"""
from __future__ import annotations

import argparse
import datetime
import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERRO: PyYAML nao instalado. Run: pip install pyyaml", file=sys.stderr)
    sys.exit(2)


def _num(x):
    """Retorna x se numerico (e nao bool), senao None."""
    return x if isinstance(x, (int, float)) and not isinstance(x, bool) else None


def _wbr_vertical(w: dict) -> str:
    return (w.get("meta", {}) or {}).get("vertical") or w.get("vertical") or "?"


def _collect_indicator_ids(card: dict) -> list[tuple[str, str]]:
    """Extrai (indicator_id, tipo_realizacao) dos kpi_references do Card N1."""
    out = []
    for ref in card.get("kpi_references", []) or []:
        iid = ref.get("indicator_id")
        if not iid:
            continue
        tipo = (ref.get("tipo_realizacao") or "aditivo").strip().lower()
        out.append((iid, tipo))
    return out


def consolidate(card: dict, n2_wbrs: list[dict]) -> tuple[dict, list[str]]:
    """Agrega os KPIs do Card N1 a partir dos WBRs N2. Retorna (indicadores, warnings)."""
    warnings: list[str] = []

    # Mapa indicator_id -> lista de contribuicoes (vertical, realizado, meta, raw)
    contrib: dict[str, list[tuple]] = {}
    for w in n2_wbrs:
        vert = _wbr_vertical(w)
        inds = w.get("indicadores")
        if not isinstance(inds, dict):
            warnings.append(f"WBR '{vert}': 'indicadores' ausente ou nao-dict (schema forkado? ex PJ2) — pulado")
            continue
        # Heuristica anti-forked: PJ2 tem indicadores={'atual':{...}}; valores nao tem 'realizado'
        looks_canonical = any(isinstance(v, dict) and ("realizado" in v) for v in inds.values())
        if not looks_canonical:
            warnings.append(f"WBR '{vert}': 'indicadores' nao parece canonical (sem 'realizado') — pulado")
            continue
        for kid, kv in inds.items():
            if isinstance(kv, dict):
                contrib.setdefault(kid, []).append((vert, _num(kv.get("realizado")), _num(kv.get("meta")), kv))

    out_inds: dict[str, dict] = {}
    for kid, tipo in _collect_indicator_ids(card):
        parts = contrib.get(kid, [])
        if not parts:
            warnings.append(f"KPI '{kid}': nenhum WBR N2 contribuiu (indicador ausente nos N2)")
        realizados = [r for (_, r, _, _) in parts if r is not None]
        metas = [m for (_, _, m, _) in parts if m is not None]
        sample = parts[0][3] if parts else {}
        unit = sample.get("unit")
        direction = sample.get("direction", "maior_melhor")
        label = sample.get("label", kid)

        if tipo == "aditivo":
            realizado = sum(realizados) if realizados else None
            meta_v = sum(metas) if metas else None
            via = "SUM(N2)"
        else:
            realizado = None
            meta_v = None
            via = f"pendente (tipo={tipo} nao-aditivo)"
            warnings.append(
                f"KPI '{kid}': tipo_realizacao='{tipo}' nao-aditivo — N1 nao derivavel por SUM; "
                f"requer meta_escritorio/regra propria (ver regras_meta do Card)"
            )

        pct = (realizado / meta_v) if (realizado is not None and meta_v not in (None, 0)) else None
        out_inds[kid] = {
            "label": label,
            "unit": unit,
            "direction": direction,
            "tipo_realizacao": tipo,
            "realizado": realizado,
            "meta": meta_v,
            "pct_atingimento": round(pct, 4) if pct is not None else None,
            "n2": {vert: {"realizado": r, "meta": m} for (vert, r, m, _) in parts},
            "_consolidado_via": via,
        }
    return out_inds, warnings


def main() -> int:
    ap = argparse.ArgumentParser(description="Consolida WBRs N2 num WBR N1 de empresa.")
    ap.add_argument("--n1-card", required=True, help="Card N1-empresa (define KPIs + tipo_realizacao)")
    ap.add_argument("--n2-wbr", action="append", required=True, help="WBR N2 (.data.json). Repetir p/ cada vertical.")
    ap.add_argument("--periodo", required=True, help="YYYY-MM do ciclo N1")
    ap.add_argument("--output", required=True, help="Path do wbr-n1-*.data.json de saida")
    args = ap.parse_args()

    card = yaml.safe_load(Path(args.n1_card).read_text(encoding="utf-8"))
    n2_wbrs = []
    for p in args.n2_wbr:
        try:
            n2_wbrs.append(json.loads(Path(p).read_text(encoding="utf-8")))
        except Exception as exc:
            print(f"ERRO ao ler WBR {p}: {exc}", file=sys.stderr)
            return 2

    inds, warnings = consolidate(card, n2_wbrs)
    meta = card.get("metadata", {}) or {}
    doc = {
        "_schema": "wbr-n1-consolidated-v1",
        "_generated_at": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "_consolidado_de": [_wbr_vertical(w) for w in n2_wbrs],
        "vertical": (meta.get("vertical_code") or "M7"),
        "nivel": "N1",
        "periodo": args.periodo,
        "meta": {
            "vertical": (meta.get("vertical_code") or "M7"),
            "nivel": "N1",
            "ciclo_label": f"N1 {meta.get('vertical_code', 'M7')} {args.periodo}",
        },
        "indicadores": inds,
        "_warnings": warnings,
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK: {len(inds)} KPIs consolidados de {len(n2_wbrs)} WBRs N2 -> {out}")
    for w in warnings:
        print("  WARN:", w)
    return 0


if __name__ == "__main__":
    sys.exit(main())
