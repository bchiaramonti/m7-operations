#!/usr/bin/env python3
"""parse_ata_scope.py — Parser do bloco scope_task_ids da ata anterior.

Lê o MD da ata mais recente do ritual passado (vertical/nível/subnível corretos)
e extrai os 2 grupos de task IDs documentados em ata-ritual.tmpl.md (v3.8.0):
  - created_in_ritual: IDs criados no ritual passado (placeholders <pendente-create> resolvidos para IDs ClickUp reais em Fase 6 do recording-decisions)
  - preexisting_discussed: IDs pre-existentes que foram comentados/atualizados no ritual

Output: dict pronto pra ser consumido por `collect.py` Fase 1.5 passo 7 (filter composto).

USO:
    from parse_ata_scope import find_latest_ata, parse_scope_block
    ata_path, ritual_date = find_latest_ata(rituais_base, vertical, nivel, subnivel)
    if ata_path:
        scope = parse_scope_block(ata_path)
        # scope = {
        #     'ritual_date': '2026-05-12',
        #     'vertical': 'pj2',
        #     'nivel': 'N2',
        #     'subnivel': None,
        #     'created_in_ritual': ['86xxxxxxx', '86xxxxxxy'],
        #     'preexisting_discussed': ['86agymn2w'],
        # }

Memory: reference_g2_2_action_scope_filter (2026-05-12).
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


# Regex para capturar o bloco scope_task_ids entre marcadores <!-- ... -->
_SCOPE_BLOCK_RE = re.compile(
    r"<!--\s*scope_task_ids:\s*\n(.*?)\n\s*-->",
    re.DOTALL,
)

# ID pattern ClickUp (alfanumerico ~9 chars). Tambem aceita placeholder <pendente-create-...>
_TASK_ID_RE = re.compile(r"[\w<>-]+")


def _vertical_display(vertical: str) -> str:
    """Capitaliza vertical respeitando siglas all-caps (sem subnivel)."""
    ALL_CAPS = ("pj2", "pj1", "pj3", "ti", "rh", "ib")
    v = vertical.strip().lower()
    if v in ALL_CAPS:
        return v.upper()
    return v.capitalize()


def _vertical_display_with_subnivel(vertical: str, subnivel: Optional[str]) -> str:
    """Concatena vertical capitalizada + subnivel lowercase com hifen.
    Ex: ('seguros', 'wl') -> 'Seguros-wl'
    """
    base = _vertical_display(vertical)
    if subnivel:
        return f"{base}-{subnivel.strip().lower()}"
    return base


def _find_latest_ata_canonical_s3(rituais_base: Path, vertical: str, nivel: str,
                                  subnivel: Optional[str],
                                  excluir_data: Optional[str]) -> tuple[Optional[Path], Optional[str]]:
    """Busca ata em 03-Rituais/, tolerante a DOIS layouts (D2 level-first):
        - legado (vertical-first): 03-Rituais/{Vertical-cap}[-{sub}]/N{N}-{Cadencia}/{Periodo}/ata/
        - level-first:             03-Rituais/N{N}/{Vertical-cap}[-{sub}]/{Cadencia}/{Periodo}/ata/

    Periodo e YYYY-S{NN} (Semanal) ou YYYY-MM (Mensal); a data efetiva da ata e
    derivada do filename (ata-ritual-{vertical}{-{subnivel}}-{YYYY-MM-DD}.md).
    """
    vertical_fs = _vertical_display_with_subnivel(vertical, subnivel)
    nivel_norm = nivel.strip().upper()

    # Diretorios-candidatos da vertical: legado (filha direta de 03-Rituais/)
    # + level-first (sob 03-Rituais/N{N}/). Robusto sem flag — cobre ambos.
    vertical_dirs = []
    for cand in (rituais_base / vertical_fs, rituais_base / nivel_norm / vertical_fs):
        if cand.exists() and cand.is_dir():
            vertical_dirs.append(cand)
    if not vertical_dirs:
        return None, None

    candidate_atas = []  # tuples (date_from_filename, ata_path)
    for vertical_dir in vertical_dirs:
        for cad_dir in vertical_dir.iterdir():
            if not cad_dir.is_dir() or cad_dir.name.startswith("_"):
                continue
            # Legado: 'N3-Semanal' (prefixo '{nivel}-'); level-first: 'Semanal'/'Mensal' puro.
            if not (cad_dir.name.startswith(f"{nivel_norm}-")
                    or cad_dir.name in ("Semanal", "Mensal")):
                continue
            for period_dir in cad_dir.iterdir():
                if not period_dir.is_dir():
                    continue
                ata_dir = period_dir / "ata"
                if not ata_dir.exists():
                    continue
                for ata_path in ata_dir.glob("ata-ritual-*.md"):
                    # Extrair data do filename: ata-ritual-{vertical}{-{sub}}-{YYYY-MM-DD}.md
                    m = re.search(r"(\d{4}-\d{2}-\d{2})\.md$", ata_path.name)
                    if not m:
                        continue
                    data_str = m.group(1)
                    if excluir_data and data_str == excluir_data:
                        continue
                    try:
                        data_obj = datetime.strptime(data_str, "%Y-%m-%d").date()
                        candidate_atas.append((data_obj, ata_path))
                    except ValueError:
                        continue
    if not candidate_atas:
        return None, None
    candidate_atas.sort(reverse=True)
    latest_date, latest_ata = candidate_atas[0]
    return latest_ata, latest_date.isoformat()


def find_latest_ata(rituais_base: Path, vertical: str, nivel: str,
                    subnivel: Optional[str] = None,
                    excluir_data: Optional[str] = None) -> tuple[Optional[Path], Optional[str]]:
    """Encontra a ata mais recente em 03-Rituais/ (canonical S3).

    Args:
        rituais_base: ~/.../desempenho/03-Rituais
        vertical: 'PJ2', 'Consorcios', 'Seguros', etc (case-insensitive)
        nivel: 'N2', 'N3', etc
        subnivel: 'wl', 're', None
        excluir_data: opcional, formato YYYY-MM-DD — se passado, ignora atas dessa data
                      (util para nao consumir a ata do ritual ATUAL como anterior)

    Returns:
        (Path da ata mais recente, ritual_date string YYYY-MM-DD) ou (None, None) se nao encontrar.

    Estrutura: {Vertical-cap}[-{sub}]/N{N}-{Cadencia}/{Periodo}/ata/ata-ritual-*.md

    > S4 Fase 4 (2026-05-20): suporte ao layout legacy_yyyymmdd removido.
    > Atas historicas pre-S3 estao em `_Historico/` (audit trail).
    """
    return _find_latest_ata_canonical_s3(rituais_base, vertical, nivel, subnivel, excluir_data)


def parse_scope_block(ata_path: Path) -> dict:
    """Le o MD da ata e extrai o bloco scope_task_ids embedado em HTML comment.

    Schema retornado (compativel com SKILL.md collecting-data Fase 1.5 passo 7):
        {
            'ritual_date': str (YYYY-MM-DD),
            'vertical': str,
            'nivel': str,
            'subnivel': str | None,
            'created_in_ritual': list[str],
            'preexisting_discussed': list[str],
            'ata_path': str,
        }

    Se bloco ausente ou mal-formado, retorna dict com listas vazias + metadata derivada do path.
    """
    text = ata_path.read_text(encoding='utf-8')
    match = _SCOPE_BLOCK_RE.search(text)

    result = {
        'ritual_date': None,
        'vertical': None,
        'nivel': None,
        'subnivel': None,
        'created_in_ritual': [],
        'preexisting_discussed': [],
        'ata_path': str(ata_path),
    }

    if not match:
        return result

    block = match.group(1)
    lines = [l.strip() for l in block.split('\n') if l.strip()]

    # Parser linha-a-linha (sem dependencia em yaml para evitar overhead)
    current_list = None
    for line in lines:
        # Header keys: "ritual_date: 2026-05-12", "vertical: pj2", etc
        if ':' in line and not line.startswith('-'):
            key, _, val = line.partition(':')
            key = key.strip(); val = val.strip()
            if key in ('ritual_date', 'vertical', 'nivel', 'subnivel'):
                result[key] = val if val and val.lower() not in ('null', 'none', '~') else None
                current_list = None
            elif key == 'created_in_ritual':
                current_list = result['created_in_ritual']
            elif key == 'preexisting_discussed':
                current_list = result['preexisting_discussed']
        # List items: "- <id>" (com ou sem aspas, com ou sem inline comment "# ...")
        elif line.startswith('-') and current_list is not None:
            item = line[1:].strip()
            if '#' in item:
                item = item.split('#', 1)[0].strip()
            item = item.strip('"').strip("'")
            if item:
                current_list.append(item)

    return result


def apply_scope_filter(all_tasks: list[dict], scope: dict,
                       last_ritual_date: Optional[str] = None,
                       pending_statuses: tuple = ('open', 'in_progress', 'blocked')) -> dict:
    """Aplica filter composto sobre lista de tasks ClickUp.

    Args:
        all_tasks: lista de tasks (cada task com 'id', 'status', 'date_created' iso, etc)
        scope: output de parse_scope_block (created + preexisting)
        last_ritual_date: data do ultimo ritual (YYYY-MM-DD); usado para particionar ad-hoc
        pending_statuses: lista de status considerados pendentes para ad-hoc

    Returns:
        Dict com 3 chaves canonicas (compat com SKILL.md collecting-data Fase 1.5):
            'escopo_ritual_passado': tasks no escopo formal do ritual
            'ad_hoc_pos_ritual': tasks criadas apos last_ritual_date, status pending
            'metadata': {escopo_modo, last_ritual_date, ata_anterior_path, ...}
    """
    escopo_ids = set(scope.get('created_in_ritual', []) + scope.get('preexisting_discussed', []))
    last_date_dt = None
    if last_ritual_date:
        try:
            last_date_dt = datetime.fromisoformat(last_ritual_date)
        except ValueError:
            pass

    escopo_ritual = []
    ad_hoc = []
    for task in all_tasks:
        task_id = str(task.get('id') or '')
        if task_id in escopo_ids:
            escopo_ritual.append(task)
            continue
        if last_date_dt is None:
            continue
        # Ad-hoc: criada APOS last_ritual_date E status pending
        date_created = task.get('date_created') or task.get('created_at')
        status = str(task.get('status') or '').lower()
        if not date_created or status not in pending_statuses:
            continue
        try:
            dc = datetime.fromisoformat(str(date_created).split('T')[0])
            if dc.date() > last_date_dt.date():
                ad_hoc.append(task)
        except ValueError:
            continue

    modo = 'filtrado' if escopo_ids or last_ritual_date else 'primeiro_ciclo'
    return {
        'escopo_ritual_passado': escopo_ritual,
        'ad_hoc_pos_ritual': ad_hoc,
        'metadata': {
            'escopo_modo': modo,
            'last_ritual_date': last_ritual_date,
            'ata_anterior_path': scope.get('ata_path'),
            'count_escopo': len(escopo_ritual),
            'count_ad_hoc': len(ad_hoc),
            'count_total': len(escopo_ritual) + len(ad_hoc),
        },
    }


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--rituais-base', type=Path, required=True,
                   help='Path para 03-Rituais/')
    p.add_argument('--vertical', required=True, help='Vertical (ex: PJ2, Consorcios)')
    p.add_argument('--nivel', required=True, help='N2, N3, etc')
    p.add_argument('--subnivel', default=None, help='wl, re, etc (opcional)')
    p.add_argument('--excluir-data', default=None, help='YYYY-MM-DD a ignorar (ritual ATUAL)')
    p.add_argument('--output-json', type=Path, default=None, help='Salva resultado em JSON')
    args = p.parse_args()

    ata_path, ritual_date = find_latest_ata(
        args.rituais_base, args.vertical, args.nivel, args.subnivel, args.excluir_data
    )

    if not ata_path:
        result = {
            'found': False,
            'message': f'Nenhuma ata encontrada em {args.rituais_base}/{args.vertical}/{args.nivel}/{args.subnivel or "-"}/',
            'escopo_modo': 'primeiro_ciclo',
        }
        if args.output_json:
            args.output_json.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    scope = parse_scope_block(ata_path)
    scope['found'] = True
    scope['last_ritual_date'] = ritual_date

    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(json.dumps(scope, indent=2, ensure_ascii=False), encoding='utf-8')
        print(f"[parse_ata_scope] Salvo em {args.output_json}")

    print(json.dumps(scope, indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
