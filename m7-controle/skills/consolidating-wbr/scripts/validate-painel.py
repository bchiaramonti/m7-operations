#!/usr/bin/env python3
"""
validate-painel.py — Valida o Painel de Indicadores do WBR Estruturado contra
todas as metas declaradas no Card de Performance.

Falha o pipeline (exit 1) se uma meta foi declarada no Card mas o indicador
correspondente nao aparece no Painel com Meta preenchida e Status colorido.

Uso:
    python3 validate-painel.py \\
        --card path/to/card_*.yaml \\
        --wbr path/to/wbr-{vertical}-{data}.md \\
        [--strict]   (default: nao-strict; com --strict, pendente conta como falha)

Quando --data e fornecido, roda tambem (alem do gate Painel->Card):
  * cross-artifact consistency (advisory)
  * schema v1.1/v1.3 (Regras 34-52, aditividade N2 38b, analise_por_responsavel)
  * metas_ppi sources (cache Card vs tabela, advisory)
  * PLAUSIBILIDADE (2026-06-18): sanidade semantica realizado/meta/status —
    pega erro silencioso (ex: realizado=0/meta>0/verde) que passa pelos gates
    de shape. Hard gate (exit 2 em falha).

Exit codes:
    0 = OK (todas metas declaradas estao refletidas no Painel)
    1 = FALHA (alguma meta declarada esta omissa ou cinza sem justificativa)
    2 = ERRO de leitura OU falha critica de schema/plausibilidade/aditividade

Autor: m7-controle (G2.2-E6)
"""

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    print("ERRO: pyyaml nao instalado. Execute: pip install pyyaml", file=sys.stderr)
    sys.exit(2)


# ───────────────────────────────────────────────────
# Extracao de metas do Card
# ───────────────────────────────────────────────────

def extract_card_metas(card_path: Path) -> dict[str, dict[str, Any]]:
    """Le o Card e retorna dict {indicator_id: meta_info}.

    meta_info contem:
        - source: 'kpi_references' | 'metas_ppi'
        - has_meta: bool (False se valor: pendente)
        - pendente_reason: str | None
        - meta_values: dict (valores numericos)
        - direction: 'maior_melhor' | 'menor_melhor' | None
    """
    with open(card_path, 'r', encoding='utf-8') as f:
        card = yaml.safe_load(f)

    metas: dict[str, dict[str, Any]] = {}

    # 1. kpi_references[].regras_meta
    # Considera "tem meta" SOMENTE se ha campo numerico explicito
    # (ex: 'meta', 'valor', 'qty', 'meta_default') OU nota com valor reconhecivel.
    # Campos como 'tipo_agregacao: ratio/sum/avg' sao metadata, nao meta.
    META_VALUE_KEYS = {'meta', 'valor', 'qty', 'volume', 'meta_default', 'default'}
    META_AGGR_METADATA = {'tipo_agregacao'}  # nao e meta, e como agregar

    for kpi in card.get('kpi_references', []):
        ind_id = kpi.get('indicator_id')
        if not ind_id:
            continue

        # 2026-05-25: skip indicators marcados como SO-fechamento.
        # Quando TODAS as matrix_views[] tem slide_visibility=["fechamento"] (so),
        # o indicador nao deve aparecer no Painel WBR semanal nem ser cobrado
        # por validate-painel. Aplicado a tempo_de_ciclo_funil_* (memory:
        # indicador retrospectivo de fechamento mensal — base parcial em MTD
        # nao tem valor analitico semanal).
        matrix_views = kpi.get('matrix_views') or []
        if matrix_views:
            all_fech_only = all(
                set(view.get('slide_visibility') or ['matriz', 'dashboard', 'fechamento']) == {'fechamento'}
                for view in matrix_views
                if isinstance(view, dict)
            )
            if all_fech_only:
                continue   # skip Painel/cobertura — so aparece em slide de fechamento

        regras = kpi.get('regras_meta', {}) or {}
        nota = (regras.get('nota') or '').lower()

        # 1a. Tem valor numerico explicito?
        has_numeric = any(
            isinstance(regras.get(k), (int, float)) for k in META_VALUE_KEYS
        )
        # 1b. Nota menciona meta com numero/percentual? (ex: "Meta default 39%")
        has_nota_meta = bool(re.search(r'\bmeta(?:\s+default)?\s*[:=]?\s*[\d.,]+\s*%?', nota))
        # 1c. Nota explicitamente diz "sem meta"
        explicitly_no_meta = (
            'sem metas formais' in nota or
            'meta=0' in nota or
            'sem meta' in nota or
            'meta nao' in nota
        )

        has_meta = (has_numeric or has_nota_meta) and not explicitly_no_meta

        metas[ind_id] = {
            'source': 'kpi_references',
            'has_meta': has_meta,
            'pendente_reason': nota if explicitly_no_meta else None,
            'meta_values': {k: v for k, v in regras.items() if k not in META_AGGR_METADATA},
            'direction': None,
            'papel': kpi.get('papel'),
        }

    # 2. metas_ppi (bloco top-level)
    metas_ppi = card.get('metas_ppi', {}) or {}
    for ppi_id, meta_def in metas_ppi.items():
        if not isinstance(meta_def, dict):
            continue
        valor = meta_def.get('valor')
        is_pendente = (str(valor).lower() == 'pendente')
        nota = meta_def.get('nota', '')
        # Coletar valores numericos (qty, volume, ticket_medio, etc.)
        meta_values = {
            k: v for k, v in meta_def.items()
            if k not in ('direction', 'nota', 'valor', 'fonte', 'fonte_n1',
                         'fonte_n2', 'fonte_futura', 'id_dashboard_componente',
                         'regra_split', 'por_especialista', 'formula')
            and isinstance(v, (int, float))
        }
        # Fonte canonica: metas_ppi pode declarar `fonte:`/`fonte_n1:`/`fonte_n2:`
        # apontando para tabela canonica. Quando presente, o valor numerico no
        # Card eh CACHE — SoT real eh a tabela (universal 2026-05-13 ou
        # m7Prata.ciclo_metas_ppi 2026-06-12). Ver inject_metas_ppi.py.
        fonte = (meta_def.get('fonte') or meta_def.get('fonte_n1')
                 or meta_def.get('fonte_n2') or meta_def.get('fonte_futura'))
        id_componente = meta_def.get('id_dashboard_componente')

        metas[ppi_id] = {
            'source': 'metas_ppi',
            'has_meta': not is_pendente and (len(meta_values) > 0 or fonte is not None),
            'pendente_reason': f"valor=pendente: {nota}" if is_pendente else None,
            'meta_values': meta_values,
            'direction': meta_def.get('direction'),
            'papel': 'ppi_funil',
            'fonte_canonica': fonte,                 # ex: m7Bronze.investimento_tb_dashboard_componente_universal_dados
            'id_dashboard_componente': id_componente,
            'cache_valor': valor if isinstance(valor, (int, float)) else None,
        }

    return metas


# ───────────────────────────────────────────────────
# Parsing do Painel do WBR
# ───────────────────────────────────────────────────

# Mapa nome legivel -> indicator_id (case-insensitive substring match)
NAME_HINTS = {
    'receita': ['receita', 'comissao'],
    'volume_seguros': ['volume seguros', 'volume premio', 'premio mensal'],
    'volume_consorcio': ['volume consorcio', 'volume cartas'],
    'quantidade_seguros': ['quantidade apolices', 'quantidade seguros', 'qtde apolice'],
    'quantidade_consorcio': ['quantidade consorcio', 'qtde cartas'],
    'taxa_conversao': ['taxa conversao', 'taxa de conversao'],
    'ticket_medio_premio': ['ticket medio premio', 'ticket premio'],
    'ticket_medio_pipeline': ['ticket pipeline', 'ticket medio pipeline'],
    # 2026-05-20: aliases 'oport.' (com ponto) e 'oport ' (sem ponto) adicionados
    # pos-ciclo Seg RE 2026-05-20 — labels abreviados no Painel ("Oport. Criadas RE",
    # "Oport. Ativas", "Oport. Estagnadas", "Oport. Sem Atividade") falhavam o gate.
    'oportunidades_ativas': ['opp ativas', 'oportunidades ativas', 'oport. ativas', 'oport ativas'],
    'oportunidades_criadas': ['opp criadas', 'oportunidades criadas', 'oport. criadas', 'oport criadas'],
    'oportunidades_estagnadas': ['opp estagnadas', 'oportunidades estagnadas', 'oport. estagnadas', 'oport estagnadas'],
    'oportunidades_sem_atividade_planejada': ['sem atividade planejada', 'sem ativ. planejada', 'oport. sem atividade', 'oport sem atividade', 'sem ativ', 'sem atividade'],
    'volume_oportunidades_ativas': ['vol opp ativas', 'volume opp ativas', 'volume oportunidades'],
}


def parse_painel_rows(wbr_md: str) -> list[dict[str, str]]:
    """Extrai linhas da tabela do Painel de Indicadores do WBR Estruturado.

    Retorna lista de dicts com chaves: indicador, meta, status (lowercased).
    """
    # Localizar a secao 1.5 Painel de Indicadores
    painel_match = re.search(
        r'##?\s*1\.5\.?\s+Painel de Indicadores(.+?)(?=\n##?\s|\Z)',
        wbr_md, re.DOTALL | re.IGNORECASE
    )
    if not painel_match:
        return []

    painel_text = painel_match.group(1)
    # Extrair tabela: linhas que comecam com | e tem >= 5 pipes
    rows = []
    for line in painel_text.splitlines():
        line = line.strip()
        if not line.startswith('|') or line.startswith('|---') or line.startswith('|:'):
            continue
        cells = [c.strip() for c in line.split('|')[1:-1]]
        if len(cells) < 5:
            continue
        # Heuristica: header tem "Indicador" no inicio
        if any(c.lower().strip() == 'indicador' for c in cells):
            continue
        # Estrutura esperada: Tipo | Indicador | Meta | Realizado | Gap | % Ating | Status | ...
        if len(cells) >= 7:
            rows.append({
                'tipo': cells[0],
                'indicador': cells[1],
                'meta': cells[2],
                'realizado': cells[3],
                'gap': cells[4],
                'pct': cells[5],
                'status': cells[6].lower(),
                'raw': line,
            })
    return rows


def match_indicator(ind_id: str, painel_rows: list[dict[str, str]]) -> dict[str, str] | None:
    """Encontra a linha do painel correspondente ao indicator_id usando NAME_HINTS.

    Fix order-independence (2026-06-22): quando VARIAS rows casam o mesmo
    indicator_id (ex: 'Oport. Estagnadas (qty)' Meta='—' contextual + 'Oport.
    Estagnadas (% ativas)' Meta='<=40%' com semaforo), prefere a row com Meta
    PREENCHIDA e status colorido — antes retornava a 1a row na ordem do Painel,
    falhando o gate so porque a qty contextual vinha primeiro (06-22 vs 06-17).
    Se NENHUMA row casada tem meta, retorna a 1a (preserva a FALHA legitima para
    meta genuinamente omissa)."""
    matches: list[dict[str, str]] = []
    low = ind_id.lower()
    # Buscar hint exato
    for hint_key, patterns in NAME_HINTS.items():
        if hint_key in low or any(p in low for p in patterns):
            for row in painel_rows:
                if any(p in row['indicador'].lower() for p in patterns) and row not in matches:
                    matches.append(row)
    # Fallback: buscar token-a-token
    if not matches:
        tokens = [t for t in low.replace('_', ' ').split() if len(t) > 3]
        if tokens[:2]:
            for row in painel_rows:
                if all(t in row['indicador'].lower() for t in tokens[:2]) and row not in matches:
                    matches.append(row)
    if not matches:
        return None
    # Preferencia: meta preenchida + status colorido > meta preenchida > 1a row
    for row in matches:
        if is_meta_filled(row['meta']) and is_status_colored(row['status']):
            return row
    for row in matches:
        if is_meta_filled(row['meta']):
            return row
    return matches[0]


# ───────────────────────────────────────────────────
# Validacao
# ───────────────────────────────────────────────────

def is_meta_filled(cell: str) -> bool:
    """Considera meta preenchida se nao for um dos placeholders de 'sem meta'."""
    s = cell.strip()
    return s not in ('—', '-', '', 'n/a', 'N/A', '–')


def is_status_colored(cell: str) -> bool:
    """Considera status colorido se mencionar verde/amarelo/vermelho (qualquer forma)."""
    s = cell.lower()
    return any(k in s for k in ['verde', 'amarelo', 'vermelho', 'green', 'yellow', 'red',
                                 '🟢', '🟡', '🔴'])


def validate(card_path: Path, wbr_path: Path, strict: bool = False) -> tuple[int, list[str]]:
    """Retorna (exit_code, mensagens)."""
    msgs: list[str] = []

    if not card_path.exists():
        return 2, [f"ERRO: Card nao encontrado: {card_path}"]
    if not wbr_path.exists():
        return 2, [f"ERRO: WBR nao encontrado: {wbr_path}"]

    metas = extract_card_metas(card_path)
    with open(wbr_path, 'r', encoding='utf-8') as f:
        wbr_md = f.read()
    painel_rows = parse_painel_rows(wbr_md)

    if not painel_rows:
        return 1, ["FALHA: Painel de Indicadores nao encontrado ou vazio no WBR"]

    msgs.append(f"Card: {len(metas)} indicadores com regras_meta ou metas_ppi declaradas")
    msgs.append(f"WBR Painel: {len(painel_rows)} linhas detectadas")
    msgs.append("")

    failures: list[str] = []
    warnings: list[str] = []

    for ind_id, info in metas.items():
        row = match_indicator(ind_id, painel_rows)

        # Caso A: meta declarada com valores numericos
        if info['has_meta']:
            if row is None:
                failures.append(
                    f"  [FALHA] '{ind_id}' tem meta em {info['source']} mas NAO aparece no Painel"
                )
                continue
            if not is_meta_filled(row['meta']):
                failures.append(
                    f"  [FALHA] '{ind_id}' (meta em {info['source']}) "
                    f"aparece no Painel mas Meta='{row['meta']}' (vazio/—)"
                )
                continue
            if not is_status_colored(row['status']):
                failures.append(
                    f"  [FALHA] '{ind_id}' (meta em {info['source']}) "
                    f"aparece no Painel mas Status='{row['status']}' (cinza, sem cor)"
                )
                continue

        # Caso B: meta pendente (valor: pendente)
        elif info['pendente_reason']:
            if row is None:
                warnings.append(
                    f"  [AVISO] '{ind_id}' marcado pendente no Card e nao aparece no Painel"
                )
            elif strict:
                failures.append(
                    f"  [FALHA --strict] '{ind_id}' tem meta pendente — strict mode "
                    f"requer pactuacao antes de WBR"
                )

    # Output
    if failures:
        msgs.append("=" * 70)
        msgs.append(f"FALHAS ({len(failures)}):")
        msgs.extend(failures)
    if warnings:
        msgs.append("=" * 70)
        msgs.append(f"AVISOS ({len(warnings)}):")
        msgs.extend(warnings)

    msgs.append("=" * 70)
    if failures:
        msgs.append(f"RESULTADO: FALHA ({len(failures)} metas omissas/cinza)")
        return 1, msgs
    msgs.append(f"RESULTADO: OK ({len(metas)} metas validadas, {len(warnings)} avisos)")
    return 0, msgs


# ───────────────────────────────────────────────────
# Validacao cross-artifact (canonical data JSON)
# ───────────────────────────────────────────────────

def _extract_numbers(text: str) -> list[float]:
    """Extrai todos os numeros (com decimais BR/US + abreviacoes K/M) do texto como floats."""
    # Padrao 1: numeros com K/M sufixo (ex: 121,7K | 1M | R$ 80,17K | 1,24M)
    pattern_km = r'-?\d{1,3}(?:[\.,]\d+)?(?=\s*[KM])'
    nums = []
    for m in re.finditer(r'(-?\d{1,3}(?:[\.,]\d+)?)\s*([KM])', text):
        raw, suffix = m.group(1), m.group(2)
        # Decimal: assume virgula = decimal nesse contexto (R$ 80,17K)
        s = raw.replace(',', '.') if ',' in raw and '.' not in raw else raw
        try:
            val = float(s)
            multiplier = 1000 if suffix == 'K' else 1_000_000
            nums.append(val * multiplier)
        except ValueError:
            continue

    # Padrao 1b: numeros com palavra "mil"/"milhao"/"milhoes" (prosa BR — ex: "R$ 140 mil", "1,2 milhoes")
    # Alinha a implementacao ao intent documentado ("abreviacao aceita"): antes so K/M eram expandidos,
    # entao "R$ 140 mil" virava 140 e falhava o cross-artifact strict contra o canonical 140257.
    for m in re.finditer(r'(-?\d{1,3}(?:[\.,]\d+)?)\s*(milh[oõ]es|milh[aã]o|mil)\b', text, re.IGNORECASE):
        raw, word = m.group(1), m.group(2).lower()
        s = raw.replace(',', '.') if ',' in raw and '.' not in raw else raw
        try:
            val = float(s)
            multiplier = 1000 if word == 'mil' else 1_000_000
            nums.append(val * multiplier)
        except ValueError:
            continue

    # Padrao 2: numeros normais (sem sufixo K/M nem palavra mil/milhao na cara)
    # Para evitar duplicar matches dos padroes 1/1b, removemos essas porcoes antes
    text_clean = re.sub(r'(-?\d{1,3}(?:[\.,]\d+)?)\s*[KM]', '', text)
    text_clean = re.sub(r'(-?\d{1,3}(?:[\.,]\d+)?)\s*(?:milh[oõ]es|milh[aã]o|mil)\b', '', text_clean, flags=re.IGNORECASE)
    pattern = r'-?\d{1,3}(?:[\.,]\d{3})*(?:[\.,]\d+)?|-?\d+(?:[\.,]\d+)?'
    for m in re.findall(pattern, text_clean):
        s = m
        if ',' in s and '.' in s:
            if s.rfind(',') > s.rfind('.'):
                s = s.replace('.', '').replace(',', '.')
            else:
                s = s.replace(',', '')
        elif ',' in s:
            parts = s.split(',')
            if len(parts) == 2 and len(parts[1]) <= 2:
                s = s.replace(',', '.')
            else:
                s = s.replace(',', '')
        elif '.' in s:
            parts = s.split('.')
            if len(parts) > 2 or (len(parts) == 2 and len(parts[1]) == 3):
                s = s.replace('.', '')
        try:
            nums.append(float(s))
        except ValueError:
            continue
    return nums


def _matches_with_tolerance(canonical: float, candidates: list[float],
                             tol_rel: float = 0.05, tol_abs: float = 0.5) -> bool:
    """Considera match se algum candidato esta dentro de tol_rel (5%) ou tol_abs (0.5)."""
    for c in candidates:
        if abs(c - canonical) <= tol_abs:
            return True
        if canonical != 0 and abs(c - canonical) / abs(canonical) <= tol_rel:
            return True
    return False


def extract_canonical_critical_numbers(data_json: dict) -> dict[str, list[float]]:
    """Extrai numeros CRITICOS (realizado + meta de cada indicator com meta) do canonical.

    Foco: validar que cada numero importante (que orienta decisao) aparece nos artefatos
    com tolerancia de arredondamento (5%). Ignora gap_label/pct_label que sao derivados.
    """
    keys: dict[str, list[float]] = {}
    inds = data_json.get('indicadores', {}) or {}
    for ind_id, ind_data in inds.items():
        nums = []
        for field in ('realizado', 'meta'):
            v = ind_data.get(field)
            if isinstance(v, (int, float)) and v != 0:
                nums.append(float(v))
        if nums:
            keys[ind_id] = nums
    # Projecoes: cenario base (plano legacy v1.0 OU aninhado em M0/M+1 no schema v1.3)
    # 2026-06-05: hardening — `projecoes` pode conter flags (is_retrospective: bool) e o
    # bloco `por_especialista` como irmaos das entradas de indicador; pular tudo que nao
    # for dict de indicador com 'base'/'M0'/'M+1' (evita AttributeError 'bool'.get).
    proj = data_json.get('projecoes', {}) or {}
    for proj_id, proj_data in proj.items():
        if not isinstance(proj_data, dict):
            continue  # ex: is_retrospective (bool)
        candidates = []
        if isinstance(proj_data.get('base'), (int, float)):
            candidates.append(proj_data['base'])
        for hz in ('M0', 'M+1'):
            blk = proj_data.get(hz)
            if isinstance(blk, dict) and isinstance(blk.get('base'), (int, float)):
                candidates.append(blk['base'])
        vals = [float(v) for v in candidates if v != 0]
        if vals:
            keys[f'projecao_{proj_id}'] = vals
    return keys


def validate_artifact_consistency(data_json_path: Path,
                                   artifact_paths: dict[str, Path],
                                   strict: bool = False) -> tuple[int, list[str]]:
    """Verifica que numeros CRITICOS do canonical JSON aparecem em cada artefato com
    tolerancia de arredondamento. Modo advisory por padrao (exit 0 + avisos).
    """
    msgs: list[str] = []
    if not data_json_path.exists():
        return 2, [f"ERRO: canonical JSON nao encontrado: {data_json_path}"]

    import json
    with open(data_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    critical = extract_canonical_critical_numbers(data)
    total_checks = sum(len(v) for v in critical.values())
    msgs.append(f"Canonical JSON: {len(critical)} indicadores, {total_checks} numeros criticos para verificar")
    msgs.append("Tolerancia: 5% relativo (rounding/abreviacao aceita)")
    msgs.append("")

    divergences: list[str] = []

    for artifact_name, artifact_path in artifact_paths.items():
        if not artifact_path.exists():
            divergences.append(f"  [FALHA] {artifact_name}: arquivo nao existe")
            continue
        with open(artifact_path, 'r', encoding='utf-8') as f:
            content = f.read()
        artifact_nums = _extract_numbers(content)

        missing: list[str] = []
        for ind_id, canon_nums in critical.items():
            for canon in canon_nums:
                ok = _matches_with_tolerance(canon, artifact_nums)
                # Reconciliacao ratio<->percent (fix 2026-06-24): indicadores de
                # unidade ratio guardam 0-1 no canonical (ex taxa_conversao 0,3889)
                # mas a prosa exibe percent ("38,9%"). Aceitar a forma equivalente
                # antes de marcar como ausente (FP recorrente sob --strict).
                if not ok and 0 < abs(canon) <= 1:
                    ok = _matches_with_tolerance(canon * 100, artifact_nums)
                if not ok and abs(canon) > 1:
                    ok = _matches_with_tolerance(canon / 100, artifact_nums)
                if not ok:
                    missing.append(f"{ind_id}={canon:g}")

        if missing:
            divergences.append(
                f"  [{artifact_name}] {len(missing)}/{total_checks} numeros criticos ausentes "
                f"(>5% off ou nao encontrados). Top: {missing[:5]}"
            )

    msgs.append("=" * 70)
    if divergences:
        msgs.append(f"AVISOS CROSS-ARTIFACT ({len(divergences)} artefatos com divergencias):")
        msgs.extend(divergences)
        msgs.append("")
        # P3.3 (2026-06-18): gate OPT-IN. Default permanece ADVISORY (exit 0) —
        # numeros podem divergir por formatacao legitima (ex: "121,7K" vs "121.713")
        # e promover a hard gate geraria FP. Com --strict-cross-artifact (unattended),
        # divergencia vira FALHA (exit 1).
        if strict:
            msgs.append("RESULTADO CROSS-ARTIFACT: FALHA (--strict-cross-artifact; exit 1)")
            return 1, msgs
        msgs.append("RESULTADO CROSS-ARTIFACT: ADVISORY (revise manualmente; exit code 0)")
    else:
        msgs.append(f"RESULTADO CROSS-ARTIFACT: OK ({len(artifact_paths)} artefatos consistentes)")
    return 0, msgs


def validate_wbr_schema_v1_1(data_json_path: Path, card_path: Path | None = None, strict: bool = False) -> tuple[int, list[str]]:
    """Valida campos novos do schema v1.1 (2026-05-12) no canonical JSON.

    Regras (mapeadas para schema-v2.1 do creating-indicators):
      34. display_name (se presente) deve ser string nao vazia
      35. display_suffix (se presente) tamanho <= 16 chars
      36. direction (se presente) ∈ {maior_melhor, menor_melhor}
      37. unit='days' sem direction → ATENCAO sugerindo menor_melhor
      38. por_canal[c] aditividade: SUM(qty por canal) ≈ realizado N1 (tol 5%)
      38b. n2[esp] aditividade: SUM(n2.*.realizado) ≈ realizado N1 (tol 1%, FAIL)
           — invariante matematica para indicadores N3 (Cons/Seg/Inv/Cred N3).
           Pula indicadores nao-aditivos (unit ratio/pct/percentual), unidades de
           media ponderada com `tipo_realizacao=nao_aditivo` no Card (2026-05-20)
           e derivados (aggregation_rule_applied=true). FAIL = exit 2 (gate hard).
      39. por_canal[c] e pct_ativas: requer companion indicator de ativas (related_indicators)

    Plus checks PJ2-especificos:
      - is_first_ritual_of_month deve estar presente em meta (advisory se ausente)
      - projecoes.{X}.M+1 so deve existir se Card declara proj_periodos_por_vertical[vert] incluindo M+1
      - mesma CTE de canal entre indicators de ativas + estagnadas (advisory)

    Args:
        data_json_path: caminho do canonical JSON
        card_path: opcional — quando passado, le `kpi_references[].tipo_realizacao`
            para skipar Regra 38b em indicadores `nao_aditivo` (ex: ticket_medio
            que tem unit=BRL mas e media ponderada por volume).
        strict: nao usado atualmente

    Retorna (exit_code, mensagens). exit_code: 0=OK, 1=warn, 2=critico.
    """
    if not data_json_path.exists():
        return 2, [f"ERRO: canonical JSON nao encontrado: {data_json_path}"]
    try:
        data = json.loads(data_json_path.read_text(encoding='utf-8'))
    except Exception as e:
        return 2, [f"ERRO: falha lendo JSON: {e}"]

    # Carregar tipo_realizacao do Card (FP-2 fix 2026-05-20) — set de indicadores
    # com tipo_realizacao=nao_aditivo, que devem ser pulados na Regra 38b
    # mesmo com unit nao sendo ratio/pct (ex: Ticket Medio unit=BRL).
    nao_aditivos_card: set[str] = set()
    # Item 4 follow-up Seguros-WL 2026-05-20 (2026-05-21): apresentacao.escopo_kpi
    # — quando = "n1_escritorio", Regra 38b downgrada FALHA -> INFO porque o N1
    # legitimamente inclui Outros M7 nao rastreados no n2 do Card squad.
    # Default (ausente ou "n2_squad"): preserva comportamento atual (FALHA exit 2).
    card_escopo_kpi: str = 'n2_squad'  # default conservador
    if card_path and card_path.exists():
        try:
            card_data = yaml.safe_load(card_path.read_text(encoding='utf-8'))
            for kpi in (card_data or {}).get('kpi_references', []) or []:
                if (kpi.get('tipo_realizacao') or '').lower() == 'nao_aditivo':
                    iid = kpi.get('indicator_id')
                    if iid:
                        nao_aditivos_card.add(iid)
            apresentacao = (card_data or {}).get('apresentacao') or {}
            card_escopo_kpi = (apresentacao.get('escopo_kpi') or 'n2_squad').lower()
        except Exception:
            pass  # silencioso — Card opcional

    msgs: list[str] = ["=" * 70, "VALIDACAO WBR SCHEMA v1.1/v1.3 (PJ2 + direction + analise_por_responsavel)", "=" * 70]
    warnings: list[str] = []
    failures: list[str] = []

    schema = data.get('_schema', '')
    if 'v1.1' not in schema and 'v1.0' in schema:
        msgs.append(f"INFO: schema declarado eh v1.0 — validacoes v1.1 sao opcionais (legacy)")

    # Check meta.is_first_ritual_of_month
    meta_block = data.get('meta') or {}
    if 'is_first_ritual_of_month' not in meta_block:
        warnings.append("  [WARN] meta.is_first_ritual_of_month ausente — builder fallback para CICLO.md")

    indicadores = data.get('indicadores') or {}
    for ind_id, ind in indicadores.items():
        # Regra 36: direction valido
        direction = ind.get('direction')
        if direction and direction not in ('maior_melhor', 'menor_melhor'):
            failures.append(f"  [FALHA] '{ind_id}': direction='{direction}' invalido (esperado maior_melhor|menor_melhor)")

        # Regra 37: unit=days sem direction → ATENCAO
        if ind.get('unit') == 'days' and not direction:
            warnings.append(f"  [WARN] '{ind_id}': unit=days sem direction declarado — sugerir 'menor_melhor'")

        # Regra 38: por_canal aditividade (SUM por canal ≈ N1)
        por_canal = ind.get('por_canal')
        if por_canal and isinstance(por_canal, dict):
            realizado_n1 = ind.get('realizado')
            for field in ('qty', 'vol'):
                soma = 0.0
                tem_field = False
                for canal_id, canal_data in por_canal.items():
                    if not isinstance(canal_data, dict): continue
                    val = canal_data.get(field)
                    if val is not None:
                        try:
                            soma += float(val); tem_field = True
                        except (TypeError, ValueError):
                            pass
                if tem_field and realizado_n1 is not None:
                    # Tolerancia 5% ou 1 unit (para count) — o que for maior
                    try:
                        ref = float(realizado_n1)
                        tol = max(abs(ref) * 0.05, 1.0)
                        if abs(soma - ref) > tol:
                            warnings.append(
                                f"  [WARN] '{ind_id}': por_canal.{field} SUM={soma} divergente de realizado={ref} (tol {tol:.2f})"
                            )
                    except (TypeError, ValueError):
                        pass

            # Regra 39: pct_ativas requer companion indicator de ativas
            tem_pct_ativas = any(
                isinstance(cd, dict) and cd.get('pct_ativas') is not None
                for cd in por_canal.values()
            )
            if tem_pct_ativas and 'estagnadas' in ind_id.lower():
                # Esperado ter companion `ativas` correspondente
                ativas_id = ind_id.replace('estagnadas', 'ativas')
                if ativas_id not in indicadores:
                    warnings.append(
                        f"  [WARN] '{ind_id}' tem por_canal[c].pct_ativas mas companion '{ativas_id}' ausente — coerencia matriz nao garantida"
                    )

        # Regra 38b (NOVO 2026-05-20): n2[esp] aditividade SUM(n2.*.realizado) ≈ realizado
        # — invariante matematica. Caso Cons 19/05 antes do fix LEFT JOIN whitelist:
        #   Vol N1=R$ 11.72M; n2 Douglas=10.72M + Sem Esp=0 + Tereza=0 = R$ 10.72M
        #   Gap R$ 1M (Amanda + M7 orfaos) — esse gate teria bloqueado E6 publish.
        # Pula:
        #   - indicadores nao-aditivos (unit ratio/pct/percent/percentual)
        #   - indicadores com tipo_realizacao=nao_aditivo no Card (FP-2 fix 2026-05-20)
        #     — ex: ticket_medio_premio_seg tem unit=BRL mas e media ponderada por
        #     volume (Ticket Medio N1 ≠ SUM(N2 ticket)). Lido do Card kpi_references.
        # Downgrade FALHA -> INFO (Item 4 follow-up 2026-05-21):
        #   - Card.apresentacao.escopo_kpi=n1_escritorio: gap N1-n2 esperado pois
        #     N1 inclui Outros M7 legitimamente, mas n2 lista apenas squad Card.
        #     Caso Seg WL 2026-05-20: realizado N1 R$ 160K (escritorio); n2 Claudia+Tarcisio
        #     R$ 96K (squad WL). Gap R$ 64K = Outros M7 (Claudio Fontenele). Legitimo.
        #   - indicadores derivados (aggregation_rule_applied=true) — esses nao
        #     somam linearmente os n2 (ex: pct_estagnadas_ativas = est/ativas)
        #   - realizado N1 ausente ou n2 vazio
        n2 = ind.get('n2')
        unit_lower = (ind.get('unit') or '').lower()
        non_additive_units = ('ratio', 'pct', 'percent', 'percentual', '%')
        is_derived = bool(ind.get('aggregation_rule_applied'))
        is_nao_aditivo_card = ind_id in nao_aditivos_card  # FP-2 fix 2026-05-20
        if (n2 and isinstance(n2, dict) and ind.get('realizado') is not None
                and unit_lower not in non_additive_units and not is_derived
                and not is_nao_aditivo_card):
            soma_n2 = 0.0
            tem_dado_n2 = False
            for esp, esp_data in n2.items():
                if not isinstance(esp_data, dict): continue
                v = esp_data.get('realizado')
                if v is None: continue
                try:
                    soma_n2 += float(v); tem_dado_n2 = True
                except (TypeError, ValueError):
                    pass
            if tem_dado_n2:
                try:
                    ref = float(ind['realizado'])
                    # Tolerancia: 1% absoluto ou 1 unit (count) ou R$ 100 (BRL) — o maior.
                    tol_pct = abs(ref) * 0.01
                    tol_floor = 100.0 if unit_lower == 'brl' else 1.0
                    tol = max(tol_pct, tol_floor)
                    if abs(soma_n2 - ref) > tol:
                        # Item 4 follow-up (2026-05-21): escopo_kpi=n1_escritorio
                        # downgrada FALHA -> INFO. Quando Card declara escopo escritorio,
                        # n2 lista apenas squad do Card mas N1 inclui Outros M7
                        # legitimamente — gap esperado, nao bug aditividade.
                        if card_escopo_kpi == 'n1_escritorio':
                            warnings.append(
                                f"  [INFO] '{ind_id}': escopo n1_escritorio — gap N1-n2={soma_n2-ref:+.2f} esperado (Outros M7 nao rastreado em n2)"
                            )
                        else:
                            failures.append(
                                f"  [FALHA] '{ind_id}': SUM(n2.*.realizado)={soma_n2:.2f} ≠ realizado_N1={ref:.2f} "
                                f"(gap={soma_n2-ref:+.2f}, tol={tol:.2f}). "
                                f"Aditividade quebrada — provavel especialista orfao no raw N2. "
                                f"(Card.apresentacao.escopo_kpi='{card_escopo_kpi}'; setar 'n1_escritorio' downgrada para INFO se intencional)"
                            )
                except (TypeError, ValueError):
                    pass

    # Check projecoes.{X}.M+1
    projecoes = data.get('projecoes') or {}
    for ind_id, proj in projecoes.items():
        if isinstance(proj, dict) and 'M+1' in proj:
            m1 = proj.get('M+1')
            if not isinstance(m1, dict) or 'base' not in m1:
                warnings.append(f"  [WARN] projecoes.{ind_id}.M+1 presente mas mal-formado")

    # ─────────────────────────────────────────────────────────────────────
    # Item 3 follow-up Seguros-WL 2026-05-20 (2026-05-21):
    # Regras 50-52 — analise_por_responsavel + cross-indicator + DM-ready
    # 2026-05-25: ADVISORY-ONLY mode — Regras so disparam quando bloco
    # `analise_por_responsavel` JA EXISTE no canonical. Quando ausente,
    # nao bloqueia pipeline (evita falhar Cons 26/05 caso analyst E6 ainda
    # nao emita v1.3 corretamente). Quando analyst emitir, valida normalmente.
    # ─────────────────────────────────────────────────────────────────────
    analise_por_resp = data.get('analise_por_responsavel') or {}
    schema_v13 = bool(re.search(r"v1\.([3-9]|\d{2,})", schema))
    # Aplica APENAS quando bloco existe E schema declara v1.3 (ambos opt-in)
    if schema_v13 and analise_por_resp:

        # Coletar (esp, indicator_id) com vermelho em N2 nos indicadores
        n2_red_pairs: list[tuple[str, str]] = []
        for ind_id, ind in indicadores.items():
            n2 = ind.get('n2') or {}
            if not isinstance(n2, dict):
                continue
            for esp, esp_data in n2.items():
                if isinstance(esp_data, dict) and (esp_data.get('status') or '').lower() == 'vermelho':
                    n2_red_pairs.append((esp, ind_id))

        # Tambem por_canal para PJ2 — coletar canais com algum indicador vermelho
        # (heuristica simples: por_canal[c].pct_ativas > limite Card)
        # Por simplicidade: tratamos apenas N2 esp aqui; PJ2 pode emitir
        # `analise_por_responsavel` com dimensao=canal e validate-painel verifica
        # presenca por canal listado em por_canal de algum indicador vermelho.
        canais_red = set()
        for ind_id, ind in indicadores.items():
            if (ind.get('status') or '').lower() != 'vermelho':
                continue
            por_canal = ind.get('por_canal') or {}
            for canal in (por_canal.keys() if isinstance(por_canal, dict) else []):
                canais_red.add((canal, ind_id))

        red_pairs = n2_red_pairs + list(canais_red)

        # Regra 50: completude — para cada (esp_ou_canal, ind_id) com vermelho
        # MUST existir em analise_por_responsavel com >=1 risco + >=1 acao
        # citando ind_id em indicador_origem.
        responsaveis_vistos: set[str] = set(analise_por_resp.keys())
        for resp, ind_id in red_pairs:
            entry = analise_por_resp.get(resp)
            if not entry:
                failures.append(
                    f"  [FALHA Regra 50] analise_por_responsavel['{resp}'] ausente "
                    f"(esp/canal tem '{ind_id}' vermelho em N2/por_canal — bot Telegram nao tera payload)"
                )
                continue
            riscos = entry.get('riscos') or []
            acoes = entry.get('acoes_sugeridas') or []
            has_risco_for_ind = any(r.get('indicador_origem') == ind_id for r in riscos if isinstance(r, dict))
            has_acao_for_ind = any(a.get('indicador_origem') == ind_id for a in acoes if isinstance(a, dict))
            if not has_risco_for_ind:
                failures.append(
                    f"  [FALHA Regra 50] analise_por_responsavel['{resp}'].riscos sem entrada com indicador_origem='{ind_id}' "
                    f"(esp/canal tem esse indicador vermelho)"
                )
            if not has_acao_for_ind:
                failures.append(
                    f"  [FALHA Regra 50] analise_por_responsavel['{resp}'].acoes_sugeridas sem entrada com indicador_origem='{ind_id}'"
                )

        # Regra 51: cross-indicator obrigatorio para PPI funil
        funil_indicators_kw = ('criadas_funil', 'ativas_funil', 'estagnadas_funil', 'taxa_conversao_funil', 'tempo_de_ciclo_funil')
        for resp, entry in analise_por_resp.items():
            if not isinstance(entry, dict):
                continue
            for risco in entry.get('riscos') or []:
                if not isinstance(risco, dict):
                    continue
                ind_orig = risco.get('indicador_origem') or ''
                is_ppi_funil = any(kw in ind_orig.lower() for kw in funil_indicators_kw)
                if not is_ppi_funil:
                    continue
                cross = risco.get('cross_indicators') or []
                n_cross = len([c for c in cross if isinstance(c, dict) and c.get('indicador')])
                if n_cross == 0:
                    failures.append(
                        f"  [FALHA Regra 51] analise_por_responsavel['{resp}'].riscos[indicador_origem='{ind_orig}']: "
                        f"PPI funil vermelho sem cross_indicators (>=2 obrigatorio)"
                    )
                elif n_cross < 2:
                    warnings.append(
                        f"  [WARN Regra 51] analise_por_responsavel['{resp}'].riscos[indicador_origem='{ind_orig}']: "
                        f"PPI funil tem apenas {n_cross} cross_indicator (esperado >=2)"
                    )

        # Regra 52: descricao_curta DM-ready (<=200 chars)
        for resp, entry in analise_por_resp.items():
            if not isinstance(entry, dict):
                continue
            for acao in entry.get('acoes_sugeridas') or []:
                if not isinstance(acao, dict):
                    continue
                curta = acao.get('descricao_curta') or ''
                if isinstance(curta, str) and len(curta) > 200:
                    warnings.append(
                        f"  [WARN Regra 52] analise_por_responsavel['{resp}'].acoes_sugeridas: "
                        f"descricao_curta {len(curta)} chars > 200 (bot Telegram pode truncar): {curta[:60]}..."
                    )

        # Marker no msgs sobre schema v1.3
        if red_pairs:
            msgs.append(f"Schema v1.3: {len(red_pairs)} pares (esp/canal × indicador vermelho) verificados em analise_por_responsavel")

    # Sumario
    msgs.append(f"Indicadores validados: {len(indicadores)}")
    msgs.append(f"Projecoes validadas: {len(projecoes)}")
    msgs.append("")
    if failures:
        msgs.append(f"FALHAS CRITICAS ({len(failures)}):")
        msgs.extend(failures)
    if warnings:
        msgs.append(f"AVISOS ({len(warnings)}):")
        msgs.extend(warnings)
    if not failures and not warnings:
        msgs.append("RESULTADO SCHEMA v1.1: OK (todos os campos coerentes)")
    elif not failures:
        msgs.append(f"RESULTADO SCHEMA v1.1: ADVISORY ({len(warnings)} avisos; exit 0)")
    else:
        msgs.append(f"RESULTADO SCHEMA v1.1: CRITICO ({len(failures)} falhas; exit 2)")

    code = 2 if failures else (0 if not warnings else (1 if strict else 0))
    return code, msgs


def validate_metas_ppi_sources(card_path: Path,
                                data_json_path: Path) -> tuple[int, list[str]]:
    """Verifica coerencia entre `metas_ppi.<ind>.fonte:` no Card e meta coletada no data.json.

    Quando Card declara `fonte:` apontando para a tabela universal
    `investimento_tb_dashboard_componente_universal_dados`, o valor numerico em
    `valor:` (Card) eh CACHE — SoT eh o indicator coletado. Esta funcao emite WARN
    se cache divergir mais que 5% da meta coletada (advisory, exit 0).

    Migracao 2026-05-13.
    """
    msgs: list[str] = ["=" * 70,
                       "VALIDACAO METAS_PPI SOURCES (cache vs tabela universal)",
                       "=" * 70]
    warnings: list[str] = []
    aligned: list[str] = []

    metas = extract_card_metas(card_path)
    if not data_json_path.exists():
        return 0, msgs + [f"INFO: canonical JSON ausente ({data_json_path}) — pulando check de sources"]

    try:
        data = json.loads(data_json_path.read_text(encoding='utf-8'))
    except Exception as e:
        return 0, msgs + [f"WARN: falha lendo canonical JSON: {e}"]

    indicadores = data.get('indicadores') or {}

    CANONICAL_TABLES = ('dashboard_componente_universal', 'ciclo_metas_ppi')
    for ind_id, info in metas.items():
        fonte = info.get('fonte_canonica')
        if not fonte or not any(t in str(fonte) for t in CANONICAL_TABLES):
            continue  # so checa fontes canonicas (tabela universal ou ciclo_metas_ppi)

        cache = info.get('cache_valor')
        id_comp = info.get('id_dashboard_componente') or str(fonte).split('.')[-1]
        coleta = indicadores.get(ind_id, {})
        meta_coletada = coleta.get('meta')

        if not isinstance(meta_coletada, (int, float)) or meta_coletada == 0:
            warnings.append(
                f"  [WARN] '{ind_id}' (id={id_comp}): Card declara fonte canonica mas data.json "
                f"nao tem meta coletada ou eh 0. Indicator pode nao ter rodado."
            )
            continue

        if cache is None:
            aligned.append(f"  [OK] '{ind_id}' (id={id_comp}): SoT={meta_coletada:g} (sem cache no Card)")
            continue

        # Comparacao com tolerancia 5%
        if meta_coletada != 0:
            divergencia_rel = abs(cache - meta_coletada) / abs(meta_coletada)
            if divergencia_rel > 0.05:
                warnings.append(
                    f"  [WARN] '{ind_id}' (id={id_comp}): cache Card={cache:g} divergente "
                    f"de meta coletada={meta_coletada:g} ({divergencia_rel*100:.1f}% > 5%). "
                    f"Atualizar `valor:` do Card ou validar tabela."
                )
            else:
                aligned.append(
                    f"  [OK] '{ind_id}' (id={id_comp}): cache={cache:g} ~= SoT={meta_coletada:g} "
                    f"(div {divergencia_rel*100:.2f}%)"
                )

    # Item 15 follow-up Seguros-WL 2026-05-20 (2026-05-21): expandir cobertura
    # para emitir WARN quando metas_ppi tem valor numerico HARDCODED sem `fonte:`
    # declarada. Tarefa de auditoria — usuario decide caso a caso se eh OK (cache
    # estabilizado anual) ou PROBLEMATICO (alta volatilidade, deveria ser SoT).
    # Respeita memory `feedback_never_edit_card_overrides` — nao edita Cards,
    # apenas reporta.
    hardcoded_no_fonte: list[str] = []
    for ind_id, info in metas.items():
        # Apenas metas_ppi (fonte_canonica/cache_valor declarados no metas_ppi block)
        if info.get('source') != 'metas_ppi':
            continue
        fonte = info.get('fonte_canonica')
        if fonte:
            continue  # ja tem fonte declarada
        # Verifica se ha algum valor numerico em meta_values
        meta_values = info.get('meta_values') or {}
        if meta_values:
            campos = ", ".join(f"{k}={v}" for k, v in list(meta_values.items())[:3])
            hardcoded_no_fonte.append(
                f"  [WARN] '{ind_id}': metas_ppi com valores HARDCODED sem `fonte:` declarada ({campos}). "
                f"Item 15 follow-up: classificar como OK (cache estavel) ou PROBLEMATICO (mover para SoT)."
            )

    # meta_stale: indicadores marcados por inject_metas_ppi quando o SoT
    # (ClickHouse) estava offline e a meta ficou no cache do Card (2026-06-18).
    # Torna a staleness VISIVEL no output do gate, nao so no canonical.
    stale_ids = [iid for iid, ind in indicadores.items()
                 if isinstance(ind, dict) and ind.get('meta_stale')]

    msgs.append(f"Indicators com fonte canonica: {len(aligned) + len(warnings)}")
    msgs.append(f"  Alinhados: {len(aligned)}")
    msgs.append(f"  Divergentes: {len(warnings)}")
    msgs.append(f"  Hardcoded sem fonte: {len(hardcoded_no_fonte)}")
    if stale_ids:
        msgs.append(f"  META STALE (SoT estava offline; cache do Card): {len(stale_ids)} -> {stale_ids[:6]}")
    msgs.append("")
    if warnings:
        msgs.extend(warnings)
    if aligned:
        msgs.append("Alinhados:")
        msgs.extend(aligned)
    if hardcoded_no_fonte:
        msgs.append("")
        msgs.append(f"HARDCODED SEM FONTE (Item 15 follow-up — audit manual):")
        msgs.extend(hardcoded_no_fonte)
    msgs.append("")
    msgs.append("RESULTADO METAS_PPI SOURCES: ADVISORY (exit 0; revise WARNs manualmente)")
    return 0, msgs  # sempre advisory durante transicao


def _status_band(status: Any) -> str | None:
    """Mapeia rotulo de status -> banda canonica ('good'|'warn'|'bad'|None)."""
    if not isinstance(status, str):
        return None
    s = status.lower()
    if any(k in s for k in ('verde', 'green', '🟢')):
        return 'good'
    if any(k in s for k in ('amarelo', 'yellow', '🟡')):
        return 'warn'
    if any(k in s for k in ('vermelho', 'red', '🔴')):
        return 'bad'
    return None


def _looks_menor_melhor(ind_id: str, unit: str | None) -> bool:
    """Heuristica para inferir direction=menor_melhor quando ausente no canonical.

    Cobre indicadores onde realizado BAIXO e BOM (estagnadas, tempo de ciclo,
    sem atividade, churn/evasao/ruptura/inadimplencia, unidades em dias). Usado
    so como fallback quando o campo `direction` nao esta declarado, para nao
    aplicar a regra maior_melhor a indicadores que sao o oposto.
    """
    iid = ind_id.lower()
    if any(kw in iid for kw in ('estagnad', 'tempo_de_ciclo', 'tempo_ciclo',
                                'sem_atividade', 'sem_ativ', 'sem_movimentacao',
                                'churn', 'evasao', 'ruptura', 'inadimpl')):
        return True
    if (unit or '').lower() in ('days', 'dias'):
        return True
    return False


def validate_plausibility(data_json_path: Path) -> tuple[int, list[str]]:
    """Regra de PLAUSIBILIDADE (2026-06-18) — sanidade semantica realizado/meta/status.

    Pega combinacoes semanticamente impossiveis que passam pelos gates de SHAPE
    (que so checam estrutura do JSON) mas geram artefato errado silenciosamente.
    Caso classico da auditoria: `realizado=0, meta>0, status=verde` (maior_melhor).

    Robustez anti-falso-positivo (memory reference_validate_painel_known_fps):
      * Base-se no RATIO recomputado `realizado/meta` (inequivoco), NUNCA no campo
        `pct_atingimento` armazenado — que e ratio 0-1 (ver inject_metas_ppi
        cor_from_pct) e pode vir em escala inconsistente do analyst.
      * Respeita `direction`; quando ausente, infere menor_melhor por heuristica
        (_looks_menor_melhor) antes de aplicar a regra maior_melhor.
      * Pula derivados (aggregation_rule_applied), unidades ratio/pct, e qualquer
        indicador sem meta numerica positiva ou sem realizado numerico.
      * Margens generosas no P2 (verde so falha com ratio<0.60; vermelho so falha
        com ratio>=1.05) — imune a thresholds custom de semaforo por Card.

    Exit 2 (FALHA) se implausibilidade; 0 se OK/ausente. Advisory para WARNs.
    """
    msgs = ["=" * 70,
            "VALIDACAO PLAUSIBILIDADE (sanidade realizado/meta/status)",
            "=" * 70]
    if not data_json_path.exists():
        return 0, msgs + [f"INFO: canonical JSON ausente ({data_json_path.name}) — pulando check"]
    try:
        data = json.loads(data_json_path.read_text(encoding='utf-8'))
    except Exception as e:
        return 2, msgs + [f"ERRO: falha lendo JSON: {e}"]

    failures: list[str] = []
    warnings: list[str] = []
    checked = 0
    NON_ADDITIVE_UNITS = ('ratio', 'pct', 'percent', 'percentual', '%')

    indicadores = data.get('indicadores') or {}
    for ind_id, ind in indicadores.items():
        if not isinstance(ind, dict):
            continue
        if ind.get('aggregation_rule_applied'):
            continue  # derivado: realizado/meta nao tem semantica linear
        unit_lower = (ind.get('unit') or '').lower()
        if unit_lower in NON_ADDITIVE_UNITS:
            continue
        meta = ind.get('meta')
        real = ind.get('realizado')
        if not isinstance(meta, (int, float)) or isinstance(meta, bool) or meta <= 0:
            continue  # sem meta numerica positiva → fora de escopo
        if not isinstance(real, (int, float)) or isinstance(real, bool):
            continue
        band = _status_band(ind.get('status') or ind.get('semaforo'))
        if band is None:
            continue  # mute/cinza/ausente → nada a contradizer

        direction = ind.get('direction')
        is_menor = (direction == 'menor_melhor') or (
            direction is None and _looks_menor_melhor(ind_id, unit_lower))
        ratio = real / meta
        checked += 1

        if not is_menor:
            # P1: realizado=0 com meta>0 (maior_melhor).
            #   verde  → FALHA: cor_from_pct so da verde com ratio>=1.0; 0% jamais
            #            e verde, mesmo em inicio de mes (status stale ou zero-fill).
            #   amarelo → WARN: realizado=0 em inicio de mes (MTD semana-1) e estado
            #            legitimo conhecido (memory tempo_ciclo_mtd_week1_false_positive);
            #            torna visivel sem bloquear retroativamente.
            if real == 0 and band == 'good':
                failures.append(
                    f"  [FALHA P1] '{ind_id}': realizado=0 com meta={meta:g} (maior_melhor) "
                    f"mas status=VERDE — 0% de meta positiva nao pode ser verde"
                )
                continue
            if real == 0 and band == 'warn':
                warnings.append(
                    f"  [WARN P1] '{ind_id}': realizado=0 com meta={meta:g} (maior_melhor) status=AMARELO "
                    f"— confirme se e inicio de mes (MTD) e nao gap de dado/zero-fill"
                )
                continue
            # P2: contradicao 2-band com margem (imune a threshold custom)
            if band == 'good' and ratio < 0.60:
                failures.append(
                    f"  [FALHA P2] '{ind_id}': status=VERDE mas realizado/meta={ratio:.2f} (<0.60) — "
                    f"implausivel (real={real:g}, meta={meta:g})"
                )
            elif band == 'bad' and ratio >= 1.05:
                failures.append(
                    f"  [FALHA P2] '{ind_id}': status=VERMELHO mas realizado/meta={ratio:.2f} (>=1.05) — "
                    f"bateu/passou a meta porem vermelho (real={real:g}, meta={meta:g})"
                )
        else:
            # menor_melhor: realizado BAIXO e bom (ratio <= 1.0 ideal)
            if band == 'good' and ratio > 1.40:
                failures.append(
                    f"  [FALHA P2] '{ind_id}': status=VERDE (menor_melhor) mas realizado/meta={ratio:.2f} "
                    f"(>1.40) — bem acima da meta porem verde (real={real:g}, meta={meta:g})"
                )
            elif band == 'bad' and ratio <= 0.95:
                failures.append(
                    f"  [FALHA P2] '{ind_id}': status=VERMELHO (menor_melhor) mas realizado/meta={ratio:.2f} "
                    f"(<=0.95) — dentro da meta porem vermelho (real={real:g}, meta={meta:g})"
                )

    msgs.append(f"Indicadores avaliados para plausibilidade: {checked}")
    msgs.append("")
    if failures:
        msgs.append(f"FALHAS DE PLAUSIBILIDADE ({len(failures)}):")
        msgs.extend(failures)
    if warnings:
        msgs.append(f"AVISOS DE PLAUSIBILIDADE ({len(warnings)}):")
        msgs.extend(warnings)
    if failures:
        msgs.append("")
        msgs.append(f"RESULTADO PLAUSIBILIDADE: CRITICO ({len(failures)} implausibilidades; exit 2)")
        return 2, msgs
    if warnings:
        msgs.append("")
        msgs.append(f"RESULTADO PLAUSIBILIDADE: ADVISORY ({len(warnings)} avisos; exit 0)")
        return 0, msgs
    msgs.append("RESULTADO PLAUSIBILIDADE: OK (nenhuma implausibilidade detectada)")
    return 0, msgs


def validate_e3_sidecar(e3_path: Path) -> tuple[int, list[str]]:
    """Valida a FORMA do sidecar e3-causa-raiz-{vertical}.json (2026-06-11).

    Pega o bug RECORRENTE e SILENCIOSO: o analyst emite `indicadores` como LISTA
    (deveria ser DICT keyed by indicator_id) e/ou usa `status` sem `semaforo`.
    Quando isso acontece, E6 Fase 4.5.d nao consegue injetar causa_raiz_resumo e o
    deck cai em texto generico — sem erro visivel. Este check torna o bug RUIDOSO.

    Exit 2 (FALHA) se shape errado; 0 se OK ou ausente (E3 pode nao ter rodado).
    Sugere rodar normalize_canonical.py para corrigir automaticamente.
    """
    msgs = ["=" * 70, "VALIDACAO SIDECAR E3 (e3-causa-raiz — shape)", "=" * 70]
    if not e3_path.exists():
        return 0, msgs + [f"INFO: sidecar E3 ausente ({e3_path.name}) — pulando check"]
    try:
        with open(e3_path, encoding="utf-8") as f:
            d = json.load(f)
    except Exception as e:
        return 2, msgs + [f"ERRO: falha lendo sidecar E3: {e}"]

    ind = d.get("indicadores")
    fails = []
    if isinstance(ind, list):
        fails.append("FALHA: `indicadores` e LISTA (esperado DICT keyed by indicator_id). "
                     "Rode: normalize_canonical.py --cycle-folder <dir> --vertical <v>")
    elif isinstance(ind, dict):
        for iid, v in ind.items():
            if not isinstance(v, dict):
                continue
            if "semaforo" not in v and "status" not in v:
                fails.append(f"FALHA: indicador '{iid}' sem `semaforo` nem `status`")
            n2 = v.get("n2_breakdown")
            if isinstance(n2, list):
                fails.append(f"FALHA: '{iid}'.n2_breakdown e LISTA (esperado DICT keyed by especialista)")
    else:
        fails.append("FALHA: `indicadores` ausente ou tipo invalido no sidecar E3")

    if fails:
        return 2, msgs + fails + ["RESULTADO E3: CRITICO (shape divergente; exit 2). "
                                  "normalize_canonical.py corrige automaticamente."]
    n = len(ind) if isinstance(ind, dict) else 0
    return 0, msgs + [f"RESULTADO E3: OK ({n} indicadores, shape dict + semaforo/status presente)"]


# Placeholders genericos que NAO sao causa-raiz real (P2.1, 2026-06-18).
_CAUSA_PLACEHOLDERS = (
    "varias", "varios", "diversas", "diversos", "a definir", "a investigar",
    "todo", "tbd", "n/d", "nd", "sem causa", "nao identificada", "nao identificado",
    "indefinida", "indefinido", "pendente", "...", "-",
)


def _is_placeholder_causa(txt) -> bool:
    """True se a causa-raiz e ausente/trivial/placeholder. Conservador (anti-FP):
    so dispara em texto vazio, MUITO curto (<25 chars) ou que e LITERALMENTE um
    placeholder — nao em causas longas que por acaso comecem com 'diversos'."""
    if not txt or not isinstance(txt, str):
        return True
    t = txt.strip()
    if len(t) < 25:
        return True
    tn = "".join(c for c in unicodedata.normalize("NFKD", t.lower())
                 if not unicodedata.combining(c))
    return tn in _CAUSA_PLACEHOLDERS


def validate_e3_coverage(data_json_path: Path, e3_path: Path) -> tuple[int, list[str]]:
    """P2.1 + P2.2 (2026-06-18) — cobertura e QUALIDADE da causa-raiz vs Painel.

    Para cada indicador VERMELHO no canonical (Painel), confere que:
      - existe entrada correspondente no sidecar E3 (senao: desvio nao analisado)
      - a causa_raiz_resumo nao e vazia/placeholder/trivial (P2.1)

    Hoje so o humano percebe "vermelho sem causa" ou "causa = 'varias'". Advisory
    (exit 0 + WARN) — torna visivel sem bloquear (qualidade textual tem FP). Roda
    so quando AMBOS canonical e sidecar E3 existem.
    """
    msgs = ["=" * 70, "VALIDACAO COBERTURA+CAUSA-RAIZ E3 (vermelho -> desvio analisado)", "=" * 70]
    if not data_json_path.exists() or not e3_path.exists():
        return 0, msgs + ["INFO: canonical ou sidecar E3 ausente — pulando coverage check"]
    try:
        data = json.loads(data_json_path.read_text(encoding="utf-8"))
        e3 = json.loads(e3_path.read_text(encoding="utf-8"))
    except Exception as e:
        return 0, msgs + [f"WARN: falha lendo arquivos p/ coverage: {e}"]

    e3_inds = e3.get("indicadores") or {}
    if not isinstance(e3_inds, dict):
        return 0, msgs + ["INFO: E3.indicadores nao-dict (shape tratado por validate_e3_sidecar) — pulando"]

    canon_inds = data.get("indicadores") or {}
    warns: list[str] = []
    vermelhos = 0
    for iid, ind in canon_inds.items():
        if not isinstance(ind, dict):
            continue
        st = ind.get("status") or ind.get("semaforo") or ""
        if not (isinstance(st, str) and "vermelho" in st.lower()):
            continue
        vermelhos += 1
        e3ent = e3_inds.get(iid)
        if not isinstance(e3ent, dict):
            warns.append(f"  [WARN cobertura] '{iid}' VERMELHO no Painel mas SEM entrada no "
                         f"sidecar E3 — desvio nao analisado")
            continue
        causa = e3ent.get("causa_raiz_resumo") or e3ent.get("causa_raiz")
        if _is_placeholder_causa(causa):
            preview = (str(causa).strip()[:40] + "...") if causa else "(vazia)"
            warns.append(f"  [WARN causa] '{iid}' VERMELHO com causa_raiz fraca/placeholder: {preview}")

    msgs.append(f"Indicadores vermelhos no Painel: {vermelhos}")
    msgs.append("")
    if warns:
        msgs.extend(warns)
        msgs.append("")
        msgs.append(f"RESULTADO COBERTURA E3: ADVISORY ({len(warns)} avisos; exit 0)")
    else:
        msgs.append("RESULTADO COBERTURA E3: OK (todo vermelho tem desvio com causa-raiz)")
    return 0, msgs


def _is_last_day_of_month(date_str) -> bool:
    try:
        import calendar
        y, m, dd = (int(x) for x in str(date_str)[:10].split("-"))
        return dd == calendar.monthrange(y, m)[1]
    except Exception:
        return False


def validate_close_mode_consistency(data_json_path: Path) -> tuple[int, list[str]]:
    """P2.3 (2026-06-18) — coerencia fechamento/retrospectiva nas projecoes.

    Quando o ciclo e de FECHAMENTO (mes fechado), as projecoes devem ser
    RETROSPECTIVAS (valores finais), nao futuras. Pega o caso silencioso em que o
    analyst esquece de marcar `close_mode`/`is_retrospective` -> o deck renderiza
    projecao FUTURA num mes ja fechado (so o humano nota "Projecao Junho" numa ata
    de fechamento de Maio). Advisory (exit 0 + WARN).
    """
    msgs = ["=" * 70, "VALIDACAO CLOSE_MODE / RETROSPECTIVA (projecao em mes fechado)", "=" * 70]
    if not data_json_path.exists():
        return 0, msgs + [f"INFO: canonical ausente ({data_json_path.name}) — pulando"]
    try:
        data = json.loads(data_json_path.read_text(encoding="utf-8"))
    except Exception as e:
        return 0, msgs + [f"WARN: falha lendo canonical: {e}"]

    meta = data.get("meta") or {}
    checkpoint = str(data.get("checkpoint_label") or meta.get("checkpoint_label") or "")
    data_ref = data.get("data_referencia") or meta.get("data_referencia") or ""
    close_mode = bool(data.get("close_mode") or meta.get("close_mode")
                      or data.get("is_retrospective") or meta.get("is_retrospective"))
    closed_signal = ("fechamento" in checkpoint.lower()) or _is_last_day_of_month(data_ref)

    warns: list[str] = []
    if closed_signal and not close_mode:
        warns.append(f"  [WARN] ciclo parece FECHAMENTO (checkpoint='{checkpoint}', data_ref={data_ref}) "
                     f"mas close_mode/is_retrospective NAO setado — projecoes seriam renderizadas como "
                     f"FUTURAS num mes ja fechado")
    if close_mode:
        proj = data.get("projecoes") or {}
        for pid, pv in proj.items():
            if isinstance(pv, dict) and pv.get("is_retrospective") is not True:
                warns.append(f"  [WARN] close_mode=True mas projecoes['{pid}'].is_retrospective != True "
                             f"(bloco esquecido — projecao apareceria como futura)")

    msgs.append(f"close_mode={close_mode} | sinal_fechamento={closed_signal} | checkpoint='{checkpoint}'")
    msgs.append("")
    if warns:
        msgs.extend(warns)
        msgs.append("")
        msgs.append(f"RESULTADO CLOSE_MODE: ADVISORY ({len(warns)} avisos; exit 0)")
    else:
        msgs.append("RESULTADO CLOSE_MODE: OK (coerencia fechamento/retrospectiva)")
    return 0, msgs


def main():
    parser = argparse.ArgumentParser(
        description="Valida Painel do WBR contra metas do Card + cross-artifact consistency + schema v1.1",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('--card', required=True, help='Path do Card YAML')
    parser.add_argument('--wbr', required=True, help='Path do WBR Estruturado MD')
    parser.add_argument('--data', help='Path do canonical data JSON (wbr-*.data.json). '
                                       'Se fornecido, ativa validacao cross-artifact + schema v1.1.')
    parser.add_argument('--narrativo', help='Path do WBR Narrativo MD (para cross-check)')
    parser.add_argument('--html', help='Path do WBR Narrativo HTML (para cross-check)')
    parser.add_argument('--e3', help='Path do sidecar e3-causa-raiz-{vertical}.json '
                                     '(opcional; valida shape dict vs lista — bug silencioso)')
    parser.add_argument('--strict', action='store_true',
                        help='Exigir que metas pendentes tenham sido pactuadas')
    parser.add_argument('--strict-cross-artifact', action='store_true',
                        help='Promove a checagem cross-artifact a GATE (exit 1 em divergencia). '
                             'Default: advisory. Use em execucao unattended.')
    args = parser.parse_args()

    # 1. Validacao Card -> Painel (sempre)
    code, msgs = validate(Path(args.card), Path(args.wbr), strict=args.strict)
    for m in msgs:
        print(m)

    # 2. Validacao cross-artifact (opcional, se --data fornecido)
    cross_code = 0
    schema_code = 0
    sources_code = 0
    if args.data:
        artifact_paths: dict[str, Path] = {'estruturado': Path(args.wbr)}
        if args.narrativo:
            artifact_paths['narrativo_md'] = Path(args.narrativo)
        if args.html:
            artifact_paths['html'] = Path(args.html)
        print("")
        cross_code, cross_msgs = validate_artifact_consistency(
            Path(args.data), artifact_paths, strict=args.strict_cross_artifact)
        for m in cross_msgs:
            print(m)

        # 3. Validacao schema v1.1 (2026-05-12): direction + por_canal + M+1
        print("")
        schema_code, schema_msgs = validate_wbr_schema_v1_1(Path(args.data), card_path=Path(args.card), strict=args.strict)
        for m in schema_msgs:
            print(m)

        # 4. Validacao metas_ppi sources (2026-05-13): cache Card vs tabela universal
        print("")
        sources_code, sources_msgs = validate_metas_ppi_sources(Path(args.card), Path(args.data))
        for m in sources_msgs:
            print(m)

        # 4b. Validacao PLAUSIBILIDADE (2026-06-18): sanidade realizado/meta/status
        # — pega erro semantico silencioso (ex: realizado=0/meta>0/verde) que passa
        # pelos gates de shape. Hard gate (exit 2 em falha).
        print("")
        plaus_code, plaus_msgs = validate_plausibility(Path(args.data))
        for m in plaus_msgs:
            print(m)

        # 4c. Close_mode / retrospectiva (P2.3): projecao futura em mes fechado.
        # Advisory (exit 0).
        print("")
        _, close_msgs = validate_close_mode_consistency(Path(args.data))
        for m in close_msgs:
            print(m)
    else:
        plaus_code = 0

    # 5. Validacao sidecar E3 (2026-06-11): shape dict vs lista (bug silencioso)
    e3_code = 0
    if args.e3:
        print("")
        e3_code, e3_msgs = validate_e3_sidecar(Path(args.e3))
        for m in e3_msgs:
            print(m)

        # 5b. Cobertura+causa-raiz E3 (2026-06-18, P2.1+P2.2): todo vermelho do
        # Painel tem desvio analisado com causa-raiz real. Advisory (exit 0).
        if args.data:
            print("")
            cov_code, cov_msgs = validate_e3_coverage(Path(args.data), Path(args.e3))
            for m in cov_msgs:
                print(m)

    # Exit code = max(painel, cross, schema, sources, plausibilidade, e3)
    sys.exit(max(code, cross_code, schema_code, sources_code, plaus_code, e3_code))


if __name__ == '__main__':
    main()
