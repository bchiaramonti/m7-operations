#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
normalize_canonical.py — Normalizador deterministico de artefatos JSON do pipeline G2.2.

MOTIVO (2026-06-11): o agente `analyst` gera os sidecars (E3, E4, E5) e o canonical
WBR (E6) em texto livre e, recorrentemente, diverge do schema canonico de formas
que ou (a) quebram silenciosamente o consumo downstream, ou (b) so sao pegas pelo
validate-painel.py exigindo retrabalho manual. Este script CONSERTA essas divergencias
de FORMA (shape) de modo idempotente, sem depender do LLM acertar na primeira.

NAO inventa conteudo analitico (causa-raiz, riscos, acoes) — apenas normaliza estrutura.
Divergencias SEMANTICAS (ex: Regra 50 — cobertura de N2 vermelho) continuam a cargo do
analyst + gate validate-painel.py.

Bugs de FORMA tratados (todos observados em ciclos reais):
  E3 (e3-causa-raiz-{vertical}.json):
    - `indicadores` emitido como LISTA -> converte para DICT keyed by indicator_id
    - `n2_breakdown` como LISTA -> converte para DICT keyed by especialista
    - cada indicador/n2 usa `status` mas nao `semaforo` -> adiciona alias `semaforo`
  E4 (e4-acoes-{vertical}.json):
    - `acoes` como LISTA -> re-bucketiza nas 4 categorias (criticas/atrasadas/
      em_dia_priorizadas/concluidas_eficazes) por `status` (P3.1 2026-06-18)
    - chave `em_dia` ou `em_dia_proximas` -> alias `em_dia_priorizadas`
  E6 (wbr-{vertical}-{data}.data.json):
    - `indicadores` top-level ausente/vazio mas presente em `painel.indicadores`
      -> promove para top-level (convertendo list->dict se preciso)
    - `acoes.em_dia` / `acoes.em_dia_proximas` -> `acoes.em_dia_priorizadas`
    - `projecoes.{x}.M+1` == null (mal-formado) -> remove a chave
    - indicador com `status` mas sem `semaforo` -> nao aplicavel (canonical usa `status`);
      garante `status_emoji` coerente quando ausente

Uso:
    python3 normalize_canonical.py --cycle-folder <dir> --vertical <v> [--subnivel <s>] [--check]

    --check : nao escreve; sai com exit 3 se houver algo a normalizar (modo CI/gate).
              Sem --check: aplica as correcoes in-place e sai 0.

Idempotente: rodar 2x seguidas na 2a vez nao muda nada.
"""
import argparse
import glob
import json
import os
import sys

STATUS_EMOJI = {"verde": "\U0001F7E2", "amarelo": "\U0001F7E1",
                "vermelho": "\U0001F534", "cinza": "⚪"}


def _load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _save(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _list_to_dict(lst, key_field, changes=None, label=""):
    """Converte list[dict] -> dict keyed by item[key_field]. Preserva ordem.

    Itens nao-dict ou sem `key_field` sao PERDIDOS na conversao. Antes isso era
    SILENCIOSO (canonical ficava com menos linhas sem aviso — bug de perda de dado).
    2026-06-18: quando `changes` e fornecido, cada item descartado vira um WARN
    visivel (e, como a saida muda, o gate --check tambem sinaliza).
    """
    out = {}
    for i, it in enumerate(lst):
        if not isinstance(it, dict):
            if changes is not None:
                changes.append(f"{label}: WARN item[{i}] descartado (nao-dict: {type(it).__name__})")
            continue
        k = it.get(key_field)
        if k is None:
            if changes is not None:
                hint = it.get("nome") or it.get("name") or it.get("label") or list(it.keys())[:4]
                changes.append(f"{label}: WARN item[{i}] descartado — sem '{key_field}' (campos: {hint})")
            continue
        item = {kk: vv for kk, vv in it.items() if kk != key_field}
        out[k] = item
    return out


# Padronizacao de naming aspect/subnivel (2026-06-18).
# WL emite a forma DESVIANTE '{base}_{aspect}_{wl|re}' (aspect ANTES do subnivel,
# ex: oportunidades_estagnadas_funil_seg_pct_ativas_wl) -> NAO termina em
# '_pct_ativas' e quebra os ~15 checks endswith('_pct_ativas'|'_qty'|'_volume')
# espalhados no build_deck. RE ja usa a forma CANONICA '{base}_{wl|re}_{aspect}'
# (termina no aspect). Esta funcao converte a desviante p/ a canonica.
_ASPECTS = ("pct_ativas", "qty", "volume")
_SUBNIVEIS = ("wl", "re")


def _canonicalize_aspect_subnivel(key: str) -> str | None:
    """'{base}_{aspect}_{sub}' -> '{base}_{sub}_{aspect}'. None se ja canonico/N/A."""
    for sub in _SUBNIVEIS:
        suf = f"_{sub}"
        if key.endswith(suf):
            stem = key[: -len(suf)]
            for asp in _ASPECTS:
                aspsuf = f"_{asp}"
                if stem.endswith(aspsuf):
                    base = stem[: -len(aspsuf)]
                    return f"{base}_{sub}_{asp}"
    return None


def _deep_rename(obj, mapping: dict):
    """Renomeia recursivamente CHAVES de dict e VALORES string que casam EXATAMENTE
    uma chave do mapping. Necessario porque um indicator_id aparece nao so como chave
    de `indicadores` mas como VALOR em status_herdado_de, acoes.gaps_plano_acao[].
    indicador_vermelho e analise_por_responsavel.*.{indicadores_vermelhos,riscos[].
    indicador_origem,cross_indicators[].indicador,alertas[],acoes_sugeridas[]}.
    Renomear so a chave deixaria essas refs penduradas -> quebraria validate-painel
    Regra 50. Match EXATO (nao substring) -> sem colisao com outros ids.
    """
    if isinstance(obj, dict):
        return {(mapping.get(k, k) if isinstance(k, str) else k): _deep_rename(v, mapping)
                for k, v in obj.items()}
    if isinstance(obj, list):
        return [_deep_rename(x, mapping) for x in obj]
    if isinstance(obj, str):
        return mapping.get(obj, obj)
    return obj


def normalize_e3(path, changes):
    d = _load(path)
    ind = d.get("indicadores")
    if isinstance(ind, list):
        d["indicadores"] = _list_to_dict(ind, "indicator_id", changes, "E3.indicadores")
        changes.append(f"E3: indicadores list->dict ({len(d['indicadores'])} chaves)")
    ind = d.get("indicadores") or {}
    for iid, v in ind.items():
        if not isinstance(v, dict):
            continue
        # status -> semaforo alias
        if "semaforo" not in v and "status" in v:
            v["semaforo"] = v["status"]
            changes.append(f"E3: {iid} +semaforo (de status)")
        # n2_breakdown list -> dict
        n2 = v.get("n2_breakdown")
        if isinstance(n2, list):
            v["n2_breakdown"] = _list_to_dict(n2, "especialista", changes, f"E3.{iid}.n2_breakdown")
            changes.append(f"E3: {iid}.n2_breakdown list->dict")
            n2 = v["n2_breakdown"]
        if isinstance(n2, dict):
            for esp, nv in n2.items():
                if isinstance(nv, dict) and "semaforo" not in nv and "status" in nv:
                    nv["semaforo"] = nv["status"]
                    changes.append(f"E3: {iid}.n2[{esp}] +semaforo")
    return d


def normalize_e4(path, changes):
    d = _load(path)
    acoes = d.get("acoes")
    if isinstance(acoes, dict):
        for legacy in ("em_dia", "em_dia_proximas"):
            if legacy in acoes and "em_dia_priorizadas" not in acoes:
                acoes["em_dia_priorizadas"] = acoes.pop(legacy)
                changes.append(f"E4: acoes.{legacy}->em_dia_priorizadas")
    elif isinstance(acoes, list):
        # P3.1 (2026-06-18): acoes como LISTA -> re-bucketiza nas 4 categorias por
        # `status` (antes: so WARN, deixava o shape quebrado p/ fix manual). Repara
        # o shape de forma deterministica; a distincao fina critica-vs-atrasada e do
        # E4 (aging) — o change-note sinaliza p/ re-revisar a classificacao.
        buckets = {"criticas": [], "atrasadas": [], "em_dia_priorizadas": [], "concluidas_eficazes": []}
        for it in acoes:
            if not isinstance(it, dict):
                continue
            st = (it.get("status") or "").strip().lower()
            if any(x in st for x in ("conclu", "closed", "done", "complete")):
                buckets["concluidas_eficazes"].append(it)
            elif "critic" in st:
                buckets["criticas"].append(it)
            elif any(x in st for x in ("atrasad", "late", "overdue", "vencid")):
                buckets["atrasadas"].append(it)
            else:
                buckets["em_dia_priorizadas"].append(it)
        d["acoes"] = buckets
        changes.append(
            f"E4: acoes list->dict 4-categorias por status "
            f"(crit={len(buckets['criticas'])} atr={len(buckets['atrasadas'])} "
            f"emdia={len(buckets['em_dia_priorizadas'])} concl={len(buckets['concluidas_eficazes'])}) "
            f"— re-revisar classificacao critica/atrasada (aging e do E4)")
    return d


def normalize_canonical(path, changes):
    d = _load(path)
    # 1) indicadores top-level ausente/vazio -> promover de painel.indicadores
    ind = d.get("indicadores")
    if not ind:
        painel = d.get("painel")
        cand = None
        if isinstance(painel, dict):
            cand = painel.get("indicadores")
        if cand:
            if isinstance(cand, list):
                # escolhe a chave presente nos itens (indicator_id ou id) ANTES de
                # converter, p/ nao gerar WARN falso de descarte na chave ausente.
                key = "indicator_id" if any(
                    isinstance(x, dict) and "indicator_id" in x for x in cand) else "id"
                cand = _list_to_dict(cand, key, changes, "E6.painel.indicadores")
            d["indicadores"] = cand
            changes.append(f"E6: indicadores promovido de painel.indicadores ({len(cand)} chaves)")
        else:
            changes.append("E6: WARN indicadores top-level ausente e sem painel.indicadores — analyst deve regerar")
    elif isinstance(ind, list):
        d["indicadores"] = _list_to_dict(ind, "indicator_id", changes, "E6.indicadores")
        changes.append(f"E6: indicadores list->dict ({len(d['indicadores'])} chaves)")

    # 1.5) Padronizar naming aspect/subnivel (rename idempotente da forma WL
    # desviante p/ a canonica). Elimina a divergencia WL/RE na FONTE (E6) em vez
    # de depender do swap-fallback do deck. Renomeia a CHAVE em `indicadores` E
    # TODAS as refs string no canonical (status_herdado_de, acoes, analise_por_
    # responsavel...) via _deep_rename, p/ nao deixar referencia pendurada (que
    # quebraria validate-painel Regra 50). Colisao (forma canonica ja existe) ->
    # NAO mexe (preserva ambas; nao sobrescreve dado).
    inds = d.get("indicadores")
    if isinstance(inds, dict):
        rename_map: dict[str, str] = {}
        for key in list(inds.keys()):
            canonical = _canonicalize_aspect_subnivel(key)
            if (canonical and canonical != key and canonical not in inds
                    and canonical not in rename_map.values()):
                rename_map[key] = canonical
        if rename_map:
            d = _deep_rename(d, rename_map)
            for old, new in rename_map.items():
                changes.append(f"E6: indicador '{old}' -> '{new}' (naming aspect/subnivel padronizado + refs)")

    # 2) acoes.em_dia / em_dia_proximas -> em_dia_priorizadas
    acoes = d.get("acoes")
    if isinstance(acoes, dict):
        for legacy in ("em_dia", "em_dia_proximas"):
            if legacy in acoes and "em_dia_priorizadas" not in acoes:
                acoes["em_dia_priorizadas"] = acoes.pop(legacy)
                changes.append(f"E6: acoes.{legacy}->em_dia_priorizadas")

    # 3) projecoes.{x}.M+1 == null -> remover
    proj = d.get("projecoes")
    if isinstance(proj, dict):
        for pid, pv in proj.items():
            if isinstance(pv, dict) and "M+1" in pv and pv["M+1"] is None:
                del pv["M+1"]
                changes.append(f"E6: projecoes.{pid}.M+1 null removido")

    # 4) canonicalizar status (canonical usa `status`); alinhar semaforo; status_emoji.
    #    Fix 2026-06-24: o analyst E6 as vezes emite `semaforo` em vez de `status`
    #    (convencao canonical = status, lido por inject_metas_ppi/validate-painel).
    #    Como inject grava `status` mas nao toca `semaforo`, os dois divergiam no
    #    indicador injetado. Backfill bidirecional, preferindo `status` quando existe
    #    (inject e mais fresco). Idempotente.
    def _canon_status(node, label):
        if not isinstance(node, dict):
            return
        st = node.get("status") or node.get("semaforo")
        if not st:
            return
        if node.get("status") != st:
            node["status"] = st
            changes.append(f"E6: {label} status<-semaforo")
        if node.get("semaforo") != st:
            node["semaforo"] = st
            changes.append(f"E6: {label} semaforo<-status")
        if st in STATUS_EMOJI and node.get("status_emoji") != STATUS_EMOJI[st]:
            node["status_emoji"] = STATUS_EMOJI[st]

    ind = d.get("indicadores") or {}
    if isinstance(ind, dict):
        # 4a) estagnadas-qty (twin sem _pct_ativas) e CONTEXTUAL quando ha sibling
        #     `*pct_ativas*` no canonical e nao tem meta propria (skill 4.5.a — o
        #     semaforo e carregado pela linha % ativas). Evita Regra-50/cobertura
        #     espuria e mantem a cor coerente.
        has_pct_sibling = any(
            ("estagnadas" in k and ("pct_ativas" in k or "pct ativas" in k))
            for k in ind.keys()
        )
        for iid, v in ind.items():
            if not isinstance(v, dict):
                continue
            low = iid.lower()
            if (has_pct_sibling and "estagnadas" in low
                    and "pct_ativas" not in low and "pct ativas" not in low
                    and v.get("meta") in (None, "", 0)
                    and (v.get("status") or v.get("semaforo")) not in (None, "cinza")):
                v["status"] = "cinza"
                v["semaforo"] = "cinza"
                v["contextual"] = True
                changes.append(f"E6: {iid} -> cinza/contextual (twin de % ativas, skill 4.5.a)")
            _canon_status(v, iid)
            for esp, nv in (v.get("n2") or {}).items():
                _canon_status(nv, f"{iid}.n2[{esp}]")
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cycle-folder", required=True)
    ap.add_argument("--vertical", required=True)
    ap.add_argument("--subnivel", default=None)
    ap.add_argument("--check", action="store_true",
                    help="Nao escreve; exit 3 se houver algo a normalizar (modo gate).")
    args = ap.parse_args()

    cy = args.cycle_folder
    v = args.vertical
    changes = []

    targets = []
    e3 = os.path.join(cy, "analise", f"e3-causa-raiz-{v}.json")
    e4 = os.path.join(cy, "analise", f"e4-acoes-{v}.json")
    if os.path.exists(e3):
        targets.append(("e3", e3, normalize_e3))
    if os.path.exists(e4):
        targets.append(("e4", e4, normalize_e4))
    # canonical: wbr-{v}[-{sub}]-{data}.data.json (pega o(s) que existir(em))
    for canon in glob.glob(os.path.join(cy, "wbr", f"wbr-{v}*.data.json")):
        if canon.endswith(".precarryfix-bak.json"):
            continue
        targets.append(("e6", canon, normalize_canonical))

    if not targets:
        print(f"Nenhum artefato JSON encontrado em {cy} para vertical={v}")
        return 0

    any_change = False
    for kind, path, fn in targets:
        before = json.dumps(_load(path), ensure_ascii=False, sort_keys=True)
        local_changes = []
        data = fn(path, local_changes)
        after = json.dumps(data, ensure_ascii=False, sort_keys=True)
        if before != after:
            any_change = True
            changes.extend(local_changes)
            if not args.check:
                _save(path, data)
                print(f"[NORMALIZADO] {os.path.basename(path)}")
            else:
                print(f"[PENDENTE]   {os.path.basename(path)}")
        else:
            print(f"[OK]         {os.path.basename(path)}")

    if changes:
        print("\nMudancas:")
        for c in changes:
            print(f"  - {c}")

    if args.check and any_change:
        print("\nCHECK: ha divergencias de shape (exit 3). Rode sem --check para aplicar.")
        return 3
    if any_change:
        print("\nNormalizacao aplicada (idempotente — rodar de novo = no-op).")
    else:
        print("\nTudo conforme schema (no-op).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
