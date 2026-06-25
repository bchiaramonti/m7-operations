#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G2.2-E6 Fase 4.5 — injeta metas PPI da tabela no canonical (determinístico).

Le o WBR canonical ``wbr-*.data.json`` e, para cada indicador OPTED-IN (Card
declara ``fonte: m7Prata.ciclo_metas_ppi``), substitui ``meta``/``meta_volume``
(N1) e ``n2.{esp}.meta``/``meta_volume`` pelos valores do SoT
``m7Prata.ciclo_metas_ppi`` (via ``meta_resolver``), recalculando
``pct_atingimento``, ``gap`` e ``status`` com a MESMA regra de semaforo do deck
(``cor_from_pct``). Tira o LLM do loop de transcrever metas.

Garantias:
  * OPT-IN: sem ``fonte: ...ciclo_metas_ppi`` no Card, o indicador NAO e tocado
    (o cache do Card, ja no canonical, permanece). Use ``--force-all`` so para
    teste. => rodar isto antes da Fase 5 (Cards sem fonte) e NO-OP.
  * Offline-safe: ClickHouse indisponivel -> WARN + exit 0, canonical intacto
    (o cache do Card segue valendo).
  * ``--dry-run`` mostra o diff sem escrever. Escrita real faz backup ``.bak``.

Uso::

    python inject_metas_ppi.py --data wbr-*.data.json --card card_*.yaml \
        --vertical seguros_wl [--dry-run] [--force-all]
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any

import yaml

FONTE_SENTINEL = "ciclo_metas_ppi"


# ---------------------------------------------------------------------------
# Semaforo — copia fiel de build_deck.cor_from_pct (manter em sincronia)
# ---------------------------------------------------------------------------

def cor_from_pct(pct: float | None, direction: str = "maior_melhor") -> str:
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
    if p >= 1.00:
        return "good"
    if p >= 0.80:
        return "warn"
    return "bad"


_COR = {"good": "verde", "warn": "amarelo", "bad": "vermelho", "mute": "mute"}


# ---------------------------------------------------------------------------
# meta_resolver bootstrap
# ---------------------------------------------------------------------------

def _load_resolver(bib_scripts: str | None):
    candidates = [bib_scripts] if bib_scripts else []
    candidates.append(str(
        Path.home() / "OneDrive - MULTI7 CAPITAL CONSULTORIA LTDA"
        / "Arquivos de Bruno Chiaramonti - desempenho" / "01-Metas"
        / "Biblioteca-de-Indicadores" / "scripts"
    ))
    for c in candidates:
        if c and (Path(c) / "meta_resolver.py").is_file():
            sys.path.insert(0, c)
            import meta_resolver as mr  # noqa: E402
            return mr, c
    raise SystemExit("ERRO: meta_resolver.py nao encontrado. Passe --bib-scripts <dir>.")


# ---------------------------------------------------------------------------
# Classificacao do indicador canonical -> campos a injetar
# ---------------------------------------------------------------------------

def _fields_for(canonical_id: str) -> list[tuple[str, str]]:
    """Retorna [(campo_canonical, campo_resolver), ...] a injetar para o id.

    ESCOPO: apenas metas COUNT/BRL (substancia real da migracao = `ativas`, que
    diverge por correcao de formula; + `criadas`/`sem_atividade`, constantes
    count). Indicadores RATIO/DAYS (taxa_conversao, tempo_de_ciclo,
    estagnadas_pct_ativas) NAO sao injetados: sao constantes de gestao identicas
    em Card e tabela, e o canonical guarda sua unidade de forma inconsistente
    entre verticais (percent 40/25 vs ratio 0.40/0.25) + naming WL/RE divergente
    (`_pct_ativas_wl` vs `_re_pct_ativas`). Injetar a ratio da tabela corromperia
    o semaforo. Eles permanecem na fonte do Card (canonical via Fase 4.5).
    """
    cid = canonical_id
    # ratio/days e estagnadas (pct e qty contextual): NAO injetar
    if "_pct_ativas" in cid or cid.startswith("oportunidades_estagnadas_funil"):
        return []
    if cid.startswith(("taxa_conversao_funil", "tempo_de_ciclo_funil")):
        return []
    if cid.startswith("oportunidades_ativas_funil"):
        return [("meta", "qty"), ("meta_volume", "volume")]
    if cid.startswith(("oportunidades_criadas_funil",
                       "oportunidades_sem_atividade_planejada_funil",
                       "oportunidades_sem_movimentacao_funil")):
        return [("meta", "qty")]
    # PJ2 receita mensal (BRL, unidade nao-ambigua) — resolve mapeia p/ _pj2
    if cid.startswith(("receita_consorcio_mensal", "receita_seguros_mensal")):
        return [("meta", "valor")]
    return []


def _card_key_for_optin(canonical_id: str) -> str:
    """canonical id -> chave do metas_ppi do Card p/ checar opt-in (fonte:)."""
    # derivado pct: oportunidades_estagnadas_funil_seg_pct_ativas_wl
    #            -> oportunidades_estagnadas_funil_seg_wl
    cid = canonical_id
    if "_pct_ativas" in cid:
        cid = cid.replace("_pct_ativas", "")
    return cid


# ---------------------------------------------------------------------------
# Opt-in set
# ---------------------------------------------------------------------------

def opted_in_keys(card: dict) -> set[str]:
    out: set[str] = set()
    for k, d in (card.get("metas_ppi") or {}).items():
        if not isinstance(d, dict):
            continue
        fonte = " ".join(str(d.get(x) or "") for x in ("fonte", "fonte_n1", "fonte_n2"))
        if FONTE_SENTINEL in fonte:
            out.add(k)
    return out


# ---------------------------------------------------------------------------
# Recompute pct/gap/status apos trocar meta
# ---------------------------------------------------------------------------

def _recompute(node: dict) -> None:
    """Recalcula pct_atingimento/gap/status de um node (ind ou n2) in place.

    So age quando ha `meta` numerica e `realizado` numerico. Nao mexe em status
    'cinza'/mute quando realizado ausente.
    """
    meta = node.get("meta")
    real = node.get("realizado")
    direction = node.get("direction") or "maior_melhor"
    if not isinstance(meta, (int, float)) or isinstance(meta, bool):
        return
    if not isinstance(real, (int, float)) or isinstance(real, bool):
        return
    if meta == 0:
        node["pct_atingimento"] = None
        return
    pct = real / meta
    node["pct_atingimento"] = round(pct, 4)
    node["gap"] = round(real - meta, 4) if isinstance(real - meta, float) else (real - meta)
    cor = _COR.get(cor_from_pct(pct, direction), "mute")
    if cor != "mute":
        node["status"] = cor


_NUM_TOKEN = re.compile(r"([+-])?(\d[\d.]*(?:,\d+)?)")


def _reformat_label(template: str, new_value: float) -> str:
    """Troca o 1o numero pt-BR de ``template`` por ``new_value``, preservando
    prefixo/sufixo (R$, %, K/M, ' deals'/' cartas'), precisao decimal e o sinal
    '+'. Mantem os ``*_label`` coerentes com a meta injetada (fix label-staleness:
    sem isso o Painel exibia o cache do Card — ex ativas Cons 38 com SoT=22)."""
    if not isinstance(template, str):
        return template
    m = _NUM_TOKEN.search(template)
    if not m:
        return template
    sign_in, num = m.group(1), m.group(2)
    tail = template[m.end():m.end() + 1]
    scale = 1e6 if tail.upper() == "M" else 1e3 if tail.upper() == "K" else 1.0
    dec = len(num.split(",")[1]) if "," in num else 0
    v = new_value / scale
    body = f"{abs(v):,.{dec}f}".replace(",", "\x00").replace(".", ",").replace("\x00", ".")
    if v < 0:
        body = "-" + body
    elif sign_in == "+":
        body = "+" + body
    return template[:m.start()] + body + template[m.end():]


def _sync_derived(node: dict) -> None:
    """Propaga a ``meta`` injetada para os ESPELHOS humanos/numericos que o Painel
    e o deck consomem (``meta_label``/``pct_label``/``gap_label``/``gap_abs``/
    ``meta_qty``/``pct``), fechando o gap label-staleness. Roda DEPOIS de
    ``_recompute`` (que ja atualizou pct_atingimento/gap/status). In place,
    idempotente — so age quando ha ``meta`` numerica."""
    meta = node.get("meta")
    real = node.get("realizado")
    unit = (node.get("unit") or "").lower()
    if not isinstance(meta, (int, float)) or isinstance(meta, bool):
        return
    pa = node.get("pct_atingimento")
    # espelhos numericos
    if "pct" in node and pa is not None:
        node["pct"] = pa
    if "meta_qty" in node and unit in ("", "count"):
        node["meta_qty"] = int(round(meta)) if float(meta).is_integer() else meta
    if isinstance(real, (int, float)) and not isinstance(real, bool):
        g = real - meta
        if "gap_abs" in node:
            node["gap_abs"] = round(g, 4) if isinstance(g, float) else g
        if "gap_label" in node:
            node["gap_label"] = _reformat_label(node["gap_label"], g)
    # labels humanos
    if "meta_label" in node:
        node["meta_label"] = _reformat_label(node["meta_label"], meta)
    if "pct_label" in node and pa is not None:
        node["pct_label"] = _reformat_label(node["pct_label"], pa * 100.0)


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

def inject(data: dict, card: dict, vertical: str, mes: str, mr,
           force_all: bool) -> list[dict]:
    """Aplica injecoes in place; retorna lista de changes p/ relatorio."""
    idx = mr.build_index(mr.fetch(vertical, mes))  # pode levantar MetaResolverOffline
    opt = None if force_all else opted_in_keys(card)
    changes: list[dict] = []
    inds = data.get("indicadores") or {}

    for cid, node in inds.items():
        if not isinstance(node, dict):
            continue
        if opt is not None and _card_key_for_optin(cid) not in opt:
            continue  # nao opted-in -> mantem cache do Card

        direction = node.get("direction") or "maior_melhor"
        fields = _fields_for(cid)
        touched = False
        for can_field, res_field in fields:
            r = mr.resolve(idx, vertical, cid, res_field, nivel="N1")
            if r is None:
                continue
            old = node.get(can_field)
            new = r["value"]
            if old != new:
                changes.append({"id": cid, "nivel": "N1", "campo": can_field,
                                "de": old, "para": new, "basis": r["basis"]})
                node[can_field] = new
                touched = True
        if touched:
            node["meta_fonte"] = f"ciclo_metas_ppi ({vertical}, {mes})"
            node.pop("meta_stale", None)  # injecao fresca limpa flag de cache offline
            node.setdefault("direction", direction)
            _recompute(node)
            _sync_derived(node)  # propaga meta -> labels/espelhos (fix staleness)

        # N2
        for esp, n2node in (node.get("n2") or {}).items():
            if not isinstance(n2node, dict):
                continue
            n2node.setdefault("direction", direction)
            t2 = False
            for can_field, res_field in fields:
                r = mr.resolve(idx, vertical, cid, res_field, nivel="N2", ref=esp)
                if r is None:
                    continue
                old = n2node.get(can_field)
                new = r["value"]
                if old != new:
                    changes.append({"id": f"{cid} :: {esp}", "nivel": "N2",
                                    "campo": can_field, "de": old, "para": new,
                                    "basis": r["basis"]})
                    n2node[can_field] = new
                    t2 = True
            if t2:
                n2node.pop("meta_stale", None)
                _recompute(n2node)
                _sync_derived(n2node)  # propaga meta -> labels/espelhos (fix staleness)

    return changes


def stamp_offline_stale(data: dict, card: dict, vertical: str) -> int:
    """Marca indicadores opted-in como meta CACHE STALE quando o SoT (ClickHouse)
    esta offline e a injecao nao rodou.

    Sem isso, o canonical fica com a meta CACHE do Card mas indistinguivel de uma
    meta fresca do SoT -> downstream (validate-painel/deck/revisor) nao sabe que a
    meta esta velha. Marca `meta_stale=true` + `meta_fonte=cache_card_offline` nos
    indicadores que SERIAM injetados (opted-in + campos injetaveis). Retorna a
    contagem marcada. Idempotente. Limpo automaticamente quando a injecao real roda.
    """
    opt = opted_in_keys(card)
    if not opt:
        return 0
    n = 0
    for cid, node in (data.get("indicadores") or {}).items():
        if not isinstance(node, dict):
            continue
        if _card_key_for_optin(cid) not in opt or not _fields_for(cid):
            continue
        node["meta_stale"] = True
        node["meta_fonte"] = f"cache_card_offline (SoT ciclo_metas_ppi indisponivel — {vertical})"
        n += 1
        for n2node in (node.get("n2") or {}).values():
            if isinstance(n2node, dict):
                n2node["meta_stale"] = True
    return n


# ---------------------------------------------------------------------------
# Modo PJ2 (canonical por canal: indicadores.{atual,fechamento}.{vert}.{ind})
# ---------------------------------------------------------------------------
# O canonical PJ2 NAO tem indicadores.{id}.meta/n2 (isso e N3). Ele tem
# indicadores.{fase}.{vert}.{ind} com realizado por canal (n2_agregado*). O inject
# PJ2 escreve as METAS por canal (meta_canal / meta_canal_qty / meta_canal_vol +
# meta_n1*); o build_deck_pj2 (Fase D) le esses campos e calcula pct/status por
# canal. Escopo count/BRL (receita/ativas/criadas/sem_movimentacao); ratio/days e
# volume/qty MENSAIS ficam no Card (resolve retorna None p/ eles).

PJ2_CANAIS = ["investimentos", "credito", "outros_m7"]  # outros_m7 -> tabela None


def _fields_pj2(ind: str) -> list[tuple[str, str]]:
    """(meta_canal_key, campo_resolver) p/ um indicador do canonical PJ2."""
    if ind.startswith("oportunidades_ativas_funil"):
        return [("meta_canal_qty", "qty"), ("meta_canal_vol", "volume")]
    if ind.startswith(("receita_consorcio_mensal", "receita_seguros_mensal")):
        return [("meta_canal", "valor")]
    if ind.startswith(("oportunidades_criadas_funil",
                       "oportunidades_sem_movimentacao_funil",
                       "oportunidades_sem_atividade_planejada_funil")):
        return [("meta_canal", "qty")]
    return []  # ratio/days/mensais: nao migrados


def _fmt_canal(d) -> str:
    if not isinstance(d, dict):
        return str(d)
    parts = [f"{k[:3]}={('%.0f' % v) if isinstance(v,(int,float)) else v}"
             for k, v in d.items() if v is not None]
    return " ".join(parts) or "—"


def inject_pj2(data: dict, card: dict, mes_by_fase: dict, mr,
               force_all: bool) -> list[dict]:
    """Injeta metas por canal no canonical PJ2 (in place). Retorna changes."""
    opt = None if force_all else opted_in_keys(card)
    changes: list[dict] = []
    inds_root = data.get("indicadores") or {}
    for fase, mes in mes_by_fase.items():
        fase_block = inds_root.get(fase) or {}
        if not fase_block:
            continue
        idx = mr.build_index(mr.fetch("pj2", mes))
        for vert in ("consorcios", "seguros"):
            for ind, node in (fase_block.get(vert) or {}).items():
                if not isinstance(node, dict):
                    continue
                if opt is not None and ind not in opt:
                    continue
                for meta_key, res_field in _fields_pj2(ind):
                    # So os canais que a tabela cobre (inv/cred). outros_m7 fica de
                    # fora -> o deck faz merge com o Card (derive_meta_canal).
                    meta_canal = {}
                    for canal in PJ2_CANAIS:
                        r = mr.resolve(idx, "pj2", ind, res_field, nivel="CANAL", ref=canal)
                        if r is not None:
                            meta_canal[canal] = r["value"]
                    if not meta_canal:
                        continue
                    old = node.get(meta_key)
                    # merge: inv/cred da tabela SOBRE o existente; preserva canais
                    # que a tabela nao cobre (outros_m7 do Card/workaround).
                    merged = dict(old) if isinstance(old, dict) else {}
                    merged.update(meta_canal)
                    if merged != old:
                        node[meta_key] = merged
                        node["meta_fonte"] = f"ciclo_metas_ppi (pj2/{vert}, {mes})"
                        changes.append({
                            "id": f"{fase}.{vert}.{ind}", "nivel": "CANAL",
                            "campo": meta_key, "de": _fmt_canal(old),
                            "para": _fmt_canal(merged), "basis": "pj2_canal",
                        })
    return changes


def _derive_mes(data: dict, explicit: str | None) -> str:
    if explicit:
        return explicit
    dr = data.get("data_referencia") or (data.get("meta") or {}).get("data_referencia")
    if dr and len(str(dr)) >= 7:
        return f"{str(dr)[:7]}-01"
    raise SystemExit("ERRO: nao consegui derivar --mes do canonical; passe --mes YYYY-MM-01.")


def _infer_vertical(data_path: Path, explicit: str | None) -> str:
    if explicit:
        return explicit
    s = str(data_path).lower()
    for needle, vk in (("seguros-wl", "seguros_wl"), ("seguros-re", "seguros_re"),
                       ("seg-wl", "seguros_wl"), ("seg-re", "seguros_re"),
                       ("consorcio", "consorcios"), ("pj2", "pj2")):
        if needle in s:
            return vk
    raise SystemExit("ERRO: nao inferi --vertical do caminho; passe --vertical.")


def main() -> int:
    ap = argparse.ArgumentParser(description="Injeta metas PPI da tabela no canonical (E6 F4.5)")
    ap.add_argument("--data", required=True, help="wbr-*.data.json")
    ap.add_argument("--card", required=True, help="card_*.yaml")
    ap.add_argument("--vertical", default=None, help="consorcios|seguros_wl|seguros_re|pj2")
    ap.add_argument("--mes", default=None, help="YYYY-MM-01 (default: do canonical)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force-all", action="store_true", help="ignora opt-in fonte: (TESTE)")
    ap.add_argument("--bib-scripts", default=None)
    args = ap.parse_args()

    mr, _ = _load_resolver(args.bib_scripts)
    data_path = Path(args.data)
    data = json.loads(data_path.read_text(encoding="utf-8"))
    card = yaml.safe_load(Path(args.card).read_text(encoding="utf-8"))
    vertical = mr.vertical_key(_infer_vertical(data_path, args.vertical))

    if vertical == "pj2":
        mes_by_fase = {"atual": _derive_mes(data, args.mes)}
        pf = data.get("periodo_fechamento")
        if pf and len(str(pf)) >= 7:
            mes_by_fase["fechamento"] = f"{str(pf)[:7]}-01"
        mes_lbl = " ".join(f"{k}={v}" for k, v in mes_by_fase.items())
    else:
        mes = _derive_mes(data, args.mes)
        mes_lbl = mes

    print(f"inject_metas_ppi | vertical={vertical} {mes_lbl} "
          f"{'[DRY-RUN]' if args.dry_run else ''} {'[FORCE-ALL]' if args.force_all else '[OPT-IN]'}")

    try:
        if vertical == "pj2":
            changes = inject_pj2(data, card, mes_by_fase, mr, args.force_all)
        else:
            changes = inject(data, card, vertical, mes, mr, args.force_all)
    except mr.MetaResolverOffline as e:
        print(f"WARN OFFLINE: {e}\n  -> cache do Card permanece como meta; marcando como STALE.")
        # PJ2 tem estrutura aninhada (indicadores.{fase}.{vert}.{ind}); o stamp flat
        # so se aplica a N3. Para PJ2 segue intacto (no-op).
        n_stale = 0 if vertical == "pj2" else stamp_offline_stale(data, card, vertical)
        if n_stale and not args.dry_run:
            bak = data_path.with_suffix(data_path.suffix + ".bak")
            shutil.copy2(data_path, bak)
            data_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"  -> {n_stale} indicador(es) opted-in marcado(s) meta_stale=true "
                  f"(SoT offline). Backup: {bak.name}")
        elif n_stale:
            print(f"  -> [DRY-RUN] marcaria {n_stale} indicador(es) meta_stale=true")
        else:
            print("  -> nenhum indicador opted-in; canonical intacto.")
        return 0

    if not changes:
        opt = opted_in_keys(card)
        print(f"Nenhuma mudanca. (indicadores opted-in no Card: {len(opt)} {sorted(opt) or '— nenhum tem fonte: ciclo_metas_ppi'})")
        return 0

    print(f"\n{len(changes)} alteracoes:")
    print(f"  {'indicador':<52} {'nivel':<4} {'campo':<12} {'de':>14} {'para':>14} basis")
    for c in changes:
        de = c["de"]; pa = c["para"]
        de = f"{de:,.2f}" if isinstance(de, (int, float)) else str(de)
        pa = f"{pa:,.2f}" if isinstance(pa, (int, float)) else str(pa)
        print(f"  {c['id']:<52} {c['nivel']:<4} {c['campo']:<12} {de:>14} {pa:>14} {c['basis']}")

    if args.dry_run:
        print("\n[DRY-RUN] nada escrito.")
        return 0

    bak = data_path.with_suffix(data_path.suffix + ".bak")
    shutil.copy2(data_path, bak)
    data_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nEscrito: {data_path}\nBackup:  {bak}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
