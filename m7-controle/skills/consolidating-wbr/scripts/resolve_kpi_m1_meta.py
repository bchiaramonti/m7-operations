#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G2.2-E6 — resolve a META de M+1 (mes seguinte) dos KPIs de meta-mensal-por-tabela.

PROBLEMA QUE RESOLVE (2026-06-22): o E5 (projecting-results, LLM) projetava o
REALIZADO de M+1 corretamente, mas para a META de M+1 ele HERDAVA a meta de M0
(copia) em vez de ler a meta do mes seguinte — que JA foi coletada no E2. A
tabela de metas (ex: dashboard id=283 para receita Cons, meta_escritorio para
volume) tem uma meta DIFERENTE por mes (a receita lagging cresce: jun 243K ->
jul 289K -> ago 336K...). Resultado: o deck mostrava a meta de M+1 = M0 (errada,
subestimada), e a classificacao/gap de M+1 saiam contra a regua errada.

ESTE HELPER (deterministico, idempotente) le `dados/raw/{ind}.json` (que o script
de coleta ja traz com TODOS os meses), pega a linha do mes M+1 e grava a meta
real em `canonical.projecoes.{ind}.M+1.meta_mes` (N1) e
`.por_especialista.{esp}.meta_mes` (N2), recomputando gap_meta e classificacao.
Tambem espelha no sidecar `projection-by-especialista.json` (meta_mes_seguinte).

ESCOPO: apenas KPIs cuja meta vem de tabela mensal — `receita_*`, `volume_*`,
`quantidade_*`. PPIs de funil (ativas/criadas/sem_atividade) tem meta do SoT
`ciclo_metas_ppi` (Fase 4.6 inject_metas_ppi) e NAO sao tocados aqui.

GARANTIA: sempre que a tabela tiver a meta do mes seguinte (o caso normal — ela
ja vem coletada), o M+1 usa a meta REAL. Se o mes seguinte nao estiver cadastrado
na tabela, mantem o valor existente e marca `m1_meta_inherited=true` (transparente,
nunca finge ter meta que nao existe).

Uso::

    python resolve_kpi_m1_meta.py --data wbr-*.data.json --raw-dir {cycle}/dados/raw \
        [--sidecar projection-by-especialista.json] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

# KPIs com meta mensal-por-tabela (prefixos). PPIs de funil ficam de fora.
KPI_PREFIXES = ("receita_", "volume_", "quantidade_")


def _is_num(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _next_month(yyyymm: str) -> str:
    y, m = int(yyyymm[:4]), int(yyyymm[5:7])
    m += 1
    if m > 12:
        m = 1
        y += 1
    return f"{y:04d}-{m:02d}"


def _classify(base, meta) -> str | None:
    if not _is_num(base) or not _is_num(meta) or meta == 0:
        return None
    p = base / meta
    if p >= 0.90:
        return "Provavel"
    if p >= 0.70:
        return "Possivel"
    return "Improvavel"


def _load_raw_month_meta(raw_dir: Path, ind: str, m1: str):
    """Retorna (n1_meta, {especialista: n2_meta}) para o mes M+1, ou (None, {})."""
    f = raw_dir / f"{ind}.json"
    if not f.is_file():
        return None, {}
    rows = (json.loads(f.read_text(encoding="utf-8")) or {}).get("data") or []
    n1_meta = None
    n2 = {}
    for r in rows:
        if not str(r.get("mes", "")).startswith(m1):
            continue
        niv = str(r.get("nivel", ""))
        if niv == "N1-Escritorio" and _is_num(r.get("meta")):
            n1_meta = r["meta"]
        elif niv == "N2-Especialista" and _is_num(r.get("meta")):
            esp = r.get("especialista")
            if esp:
                n2[esp] = r["meta"]
    return n1_meta, n2


def resolve(data: dict, raw_dir: Path, sidecar: dict | None) -> list[dict]:
    """Aplica in place; retorna lista de changes p/ relatorio."""
    dr = data.get("data_referencia") or (data.get("meta") or {}).get("data_referencia")
    if not dr or len(str(dr)) < 7:
        raise SystemExit("ERRO: data_referencia ausente no canonical.")
    m0 = str(dr)[:7]
    m1 = _next_month(m0)
    changes: list[dict] = []

    for ind, pblock in (data.get("projecoes") or {}).items():
        if not ind.startswith(KPI_PREFIXES):
            continue
        m1block = (pblock or {}).get("M+1")
        if not isinstance(m1block, dict):
            continue
        n1_meta, n2_meta = _load_raw_month_meta(raw_dir, ind, m1)
        if n1_meta is None and not n2_meta:
            m1block["m1_meta_inherited"] = True  # mes seguinte sem meta cadastrada
            changes.append({"ind": ind, "nivel": "N1", "de": m1block.get("meta_mes"),
                            "para": "(inherited — sem meta {} na tabela)".format(m1)})
            continue

        # N1
        if n1_meta is not None and m1block.get("meta_mes") != n1_meta:
            old = m1block.get("meta_mes")
            m1block["meta_mes"] = n1_meta
            base = m1block.get("base")
            if _is_num(base):
                m1block["gap_meta"] = round(base - n1_meta, 2)
                cls = _classify(base, n1_meta)
                if cls:
                    m1block["classificacao"] = cls
            m1block.pop("m1_meta_inherited", None)
            changes.append({"ind": ind, "nivel": "N1", "de": old, "para": n1_meta})

        # N2 por especialista (no canonical projecoes)
        for esp, node in (m1block.get("por_especialista") or {}).items():
            if not isinstance(node, dict):
                continue
            nm = n2_meta.get(esp)
            if nm is not None and node.get("meta_mes") != nm:
                old = node.get("meta_mes")
                node["meta_mes"] = nm
                base = node.get("base")
                if _is_num(base):
                    node["gap_meta"] = round(base - nm, 2)
                    cls = _classify(base, nm)
                    if cls:
                        node["classificacao"] = cls
                changes.append({"ind": ind, "nivel": f"N2 {esp}", "de": old, "para": nm})

        # Espelho no canonical.indicadores.{ind}.n2.{esp}.meta_proximo_mes (se existir)
        ind_node = (data.get("indicadores") or {}).get(ind)
        if isinstance(ind_node, dict):
            for esp, n2n in (ind_node.get("n2") or {}).items():
                nm = n2_meta.get(esp)
                if isinstance(n2n, dict) and nm is not None and "meta_proximo_mes" in n2n:
                    n2n["meta_proximo_mes"] = nm

        # Sidecar projection-by-especialista (meta_mes_seguinte + M+1.meta_mes)
        if sidecar:
            for esp, espnode in (sidecar.get("especialistas") or {}).items():
                nm = n2_meta.get(esp)
                if nm is None:
                    continue
                ib = (espnode or {}).get(ind)
                if isinstance(ib, dict):
                    if "meta_mes_seguinte" in ib:
                        ib["meta_mes_seguinte"] = nm
                    if isinstance(ib.get("M+1"), dict) and "meta_mes" in ib["M+1"]:
                        ib["M+1"]["meta_mes"] = nm
            cons = (sidecar.get("consolidado_n1") or {}).get(ind) \
                or (sidecar.get("consolidado_n1") or {}).get(ind.replace("_mensal", "_consolidada_mensal"))
            if isinstance(cons, dict) and n1_meta is not None and "meta_mes_seguinte" in cons:
                cons["meta_mes_seguinte"] = n1_meta

    return changes


def main() -> int:
    ap = argparse.ArgumentParser(description="Resolve meta de M+1 dos KPIs a partir dos dados coletados (E6)")
    ap.add_argument("--data", required=True, help="wbr-*.data.json (canonical)")
    ap.add_argument("--raw-dir", required=True, help="{cycle}/dados/raw")
    ap.add_argument("--sidecar", default=None, help="projection-by-especialista.json (opcional)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    data_path = Path(args.data)
    data = json.loads(data_path.read_text(encoding="utf-8"))
    raw_dir = Path(args.raw_dir)
    sidecar_path = Path(args.sidecar) if args.sidecar else None
    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8")) if sidecar_path and sidecar_path.is_file() else None

    changes = resolve(data, raw_dir, sidecar)

    m0 = str(data.get("data_referencia"))[:7]
    print(f"resolve_kpi_m1_meta | M0={m0} -> M+1={_next_month(m0)} "
          f"{'[DRY-RUN]' if args.dry_run else ''}")
    if not changes:
        print("Nenhuma mudanca (M+1 ja com a meta do mes seguinte, ou sem KPIs com M+1).")
        return 0
    print(f"\n{len(changes)} alteracoes:")
    for c in changes:
        de = c["de"]; pa = c["para"]
        de = f"{de:,.2f}" if _is_num(de) else str(de)
        pa = f"{pa:,.2f}" if _is_num(pa) else str(pa)
        print(f"  {c['ind']:<32} {c['nivel']:<16} {de:>16} -> {pa:>16}")

    if args.dry_run:
        print("\n[DRY-RUN] nada escrito.")
        return 0

    shutil.copy2(data_path, data_path.with_suffix(data_path.suffix + ".bak"))
    data_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    if sidecar and sidecar_path:
        shutil.copy2(sidecar_path, sidecar_path.with_suffix(sidecar_path.suffix + ".bak"))
        sidecar_path.write_text(json.dumps(sidecar, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nEscrito: {data_path.name} + {sidecar_path.name} (backups .bak)")
    else:
        print(f"\nEscrito: {data_path.name} (backup .bak)")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
