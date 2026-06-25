#!/usr/bin/env python3
"""
resolve_controle_path.py — Resolve o path canonico de 02-Controle/ para um ciclo de Card.

CANONICAL S3 (norma desde 2026-05-20, memory `feedback_path_canonical_s3`):
    02-Controle/{Vertical-cap}[-{subnivel}]/{YYYY-MM}/{YYYY-MM-DD}/
        ├── analise/
        ├── dados/raw/
        ├── data-quality/
        ├── wbr/
        ├── CICLO.md
        ├── execution-plan.json
        └── execution-results.json

Convencoes:
    Vertical : capitalizado (seguros -> Seguros, consorcios -> Consorcios, pj2 -> PJ2)
    Subnivel : lowercase, concatenado com hifen apos vertical (ex: Seguros-wl, Seguros-re)
               1 Card = 1 unidade FS; conceitualmente WL/RE sao subniveis de Seguros
               (Card YAML preserva `vertical_crm: seguros` + `subnivel: wl` separados).
    YYYY-MM  : mes wrapper obrigatorio (ex: 2026-05/)
    YYYY-MM-DD : data exata do ciclo (ex: 2026-05-19/)

> S4 Fase 4 (2026-05-20): suporte a paths legacy lowercase-flat removido.
> Pre-S3 ciclos historicos estao em `_Historico/` (audit trail).

Uso CLI:
    python3 resolve_controle_path.py \\
        --base-dir /path/to/desempenho \\
        --vertical seguros \\
        --ciclo-date 2026-05-22 \\
        --card-path /path/to/card_seg_wl_n3_001.yaml
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERRO: PyYAML nao instalado. Run: pip install pyyaml", file=sys.stderr)
    sys.exit(2)


# Siglas all-caps preservadas (pj2 -> PJ2, nao 'Pj2' do .capitalize())
ALL_CAPS_VERTICALS = ("pj2", "pj1", "pj3", "ti", "rh", "ib")


def _vertical_display(vertical: str) -> str:
    """Capitaliza vertical respeitando siglas all-caps conhecidas.

    Ex: 'seguros' -> 'Seguros', 'pj2' -> 'PJ2', 'consorcios' -> 'Consorcios'
    """
    v = vertical.strip().lower()
    if v in ALL_CAPS_VERTICALS:
        return v.upper()
    return v.capitalize()


def _vertical_display_with_subnivel(vertical: str, subnivel: str | None) -> str:
    """Concatena vertical capitalizada + subnivel lowercase com hifen.

    Ex: ('seguros', 'wl') -> 'Seguros-wl'
        ('seguros', 're') -> 'Seguros-re'
        ('pj2', None)     -> 'PJ2'
        ('consorcios', None) -> 'Consorcios'
    """
    base = _vertical_display(vertical)
    if subnivel:
        return f"{base}-{subnivel.strip().lower()}"
    return base


def _normalize_subnivel(raw: str | None) -> str | None:
    """Normaliza subnivel para lowercase ou None."""
    if not raw:
        return None
    s = str(raw).strip().lower()
    return s if s and s not in ("null", "none", "~") else None


def _normalize_nivel(raw: str | None) -> str:
    """Normaliza metadata.nivel para 'N1'..'N5' (maiusculo, 2 chars).

    Copia do helper homonimo de resolve_ritual_path.py (plugins separados, sem
    cross-import — regra do CLAUDE.md). Default 'N3' para ciclos semanais.
    """
    if not raw:
        return "N3"  # default para ciclos semanais N3
    n = str(raw).strip().upper().replace("-", "")
    if n.startswith("N") and len(n) >= 2 and n[1].isdigit():
        return n[:2]
    if n.isdigit() and len(n) <= 1:
        return f"N{n}"
    if "N3" in n or "SEMANAL" in n:
        return "N3"
    if "N2" in n or "MENSAL" in n:
        return "N2"
    raise ValueError(f"Nivel nao reconhecido: {raw!r}")


def resolve_controle_path(
    base_dir: Path | str,
    vertical: str,
    ciclo_date: date,
    card_path: Path | str,
    *,
    level_first: bool = True,
    nivel: str | None = None,
) -> Path:
    """Retorna Path absoluto para diretorio do ciclo em 02-Controle/.

    Estrutura (level_first=True, DEFAULT desde 2026-06-09 — migracao level-first):
        {base}/02-Controle/{N{N}}/{Vertical-cap}[-{subnivel}]/{YYYY-MM}/{YYYY-MM-DD}/
    Estrutura (level_first=False, legado flat — via CLI --legacy-flat):
        {base}/02-Controle/{Vertical-cap}[-{subnivel}]/{YYYY-MM}/{YYYY-MM-DD}/

    Args:
        base_dir: raiz `desempenho/` OU pasta 02-Controle/ direto
        vertical: identificador da vertical em lowercase (ex: 'seguros', 'consorcios', 'pj2')
        ciclo_date: data do ciclo (datetime.date)
        card_path: Path do card_*.yaml com opcional `metadata.subnivel`
        level_first: se True (DEFAULT desde 2026-06-09 — migracao concluida), insere o segmento
                     de nivel (N{N}/) como pasta-pai (D2). False (CLI --legacy-flat) = layout legado flat.
        nivel: override do nivel (N1..N5); precedencia sobre metadata.nivel. So usado quando level_first=True.

    Returns:
        Path absoluto para o diretorio do ciclo (nao cria as pastas — use --create no CLI).

    Raises:
        FileNotFoundError: se card_path nao existir
    """
    base_dir = Path(base_dir).resolve()
    card_path = Path(card_path)
    if not card_path.exists():
        raise FileNotFoundError(f"Card nao encontrado: {card_path}")

    card = yaml.safe_load(card_path.read_text(encoding="utf-8"))
    meta = card.get("metadata") or {}
    subnivel = _normalize_subnivel(meta.get("subnivel"))
    yyyy_mm = ciclo_date.strftime("%Y-%m")
    yyyy_mm_dd = ciclo_date.strftime("%Y-%m-%d")

    vertical_fs = _vertical_display_with_subnivel(vertical, subnivel)
    parts = [vertical_fs, yyyy_mm, yyyy_mm_dd]

    # Level-first (D2): insere o segmento de nivel como pasta-pai da vertical.
    # OFF (default) -> path legado byte-identico. Nivel so e resolvido quando ON.
    if level_first:
        nivel_fs = _normalize_nivel(nivel or meta.get("nivel"))
        parts = [nivel_fs, *parts]

    # Montar path: base_dir [+ "02-Controle" se nao terminou nele] + parts
    if base_dir.name == "02-Controle":
        return base_dir.joinpath(*parts)
    return base_dir / "02-Controle" / Path(*parts)


def main():
    parser = argparse.ArgumentParser(
        description="Resolve canonical path for 02-Controle/ ciclos (canonical S3)"
    )
    parser.add_argument(
        "--base-dir",
        required=True,
        help="Raiz do repo 'desempenho' OU pasta 02-Controle/ direto",
    )
    parser.add_argument(
        "--vertical",
        required=True,
        help="Identificador da vertical em lowercase (ex: seguros, consorcios, pj2)",
    )
    parser.add_argument(
        "--ciclo-date",
        required=True,
        help="Data do ciclo no formato YYYY-MM-DD",
    )
    parser.add_argument(
        "--card-path",
        required=True,
        help="Path do card_*.yaml com opcional metadata.subnivel",
    )
    parser.add_argument(
        "--legacy-flat",
        action="store_true",
        help="Forca o layout legado flat (sem N{N}/). Default migrou para level-first ON em 2026-06-09.",
    )
    parser.add_argument(
        "--level-first",
        action="store_true",
        help="(compat/no-op) level-first ja e o default desde 2026-06-09.",
    )
    parser.add_argument(
        "--nivel",
        default=None,
        help="Override do nivel (N1..N5). Precedencia sobre metadata.nivel.",
    )
    parser.add_argument(
        "--create",
        action="store_true",
        help="Criar subpastas analise/, dados/raw/, data-quality/, wbr/",
    )
    args = parser.parse_args()

    try:
        ciclo_date = datetime.strptime(args.ciclo_date, "%Y-%m-%d").date()
    except ValueError:
        print(
            f"ERRO: --ciclo-date deve estar em YYYY-MM-DD, recebido: {args.ciclo_date!r}",
            file=sys.stderr,
        )
        sys.exit(2)

    try:
        ciclo_dir = resolve_controle_path(
            base_dir=args.base_dir,
            vertical=args.vertical,
            ciclo_date=ciclo_date,
            card_path=args.card_path,
            level_first=(not args.legacy_flat),
            nivel=args.nivel,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        sys.exit(2)

    if args.create:
        for sub in ("analise", "dados/raw", "data-quality", "wbr"):
            (ciclo_dir / sub).mkdir(parents=True, exist_ok=True)

    print(ciclo_dir)


if __name__ == "__main__":
    main()
