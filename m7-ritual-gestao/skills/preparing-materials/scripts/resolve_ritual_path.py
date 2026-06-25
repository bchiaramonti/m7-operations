#!/usr/bin/env python3
"""
resolve_ritual_path.py — Resolve o path canonico de 03-Rituais/ para um ritual.

CANONICAL S3 (norma desde 2026-05-20, memory `feedback_path_canonical_s3`):
    03-Rituais/{Vertical-cap}[-{subnivel}]/N{N}-{Cadencia}/{Periodo}/
        ├── apresentacao/  (deck HTML — preparing-materials)
        ├── ata/           (ata MD/HTML/PDF — recording-decisions)
        ├── briefing/      (briefing MD + HTML A4 — preparing-materials)
        └── distribuicao/  (preview JSONs bot Slack — distributing-materials)

Convencoes (1 Card = 1 unidade FS):
    Vertical-cap : capitalizado (seguros -> Seguros, consorcios -> Consorcios, pj2 -> PJ2)
                   Concatenado com subnivel via hifen quando presente.
                   Ex: ('seguros', 'wl') -> 'Seguros-wl'
                       ('seguros', 're') -> 'Seguros-re'
                       ('pj2', None)     -> 'PJ2'
                   Conceitualmente WL/RE sao subniveis de Seguros (Card YAML preserva
                   `vertical_crm: seguros` + `subnivel: wl` separados), mas no filesystem
                   concatenamos pois cada Card e uma unidade de pipeline independente.
    N{N}-{Cad} : nivel + cadencia (ex: N3-Semanal, N2-Mensal).
                 Cadencia inferida de metadata.nivel se Card.ritual.cadencia ausente:
                   N3+ -> Semanal (default)
                   N2  -> Mensal  (default)
                   N1  -> Mensal  (default; Card pode override)
    Periodo : derivado da cadencia:
                Semanal -> {YYYY}-S{NN:02d}  (ISO week; ex: 2026-S20)
                Mensal  -> {YYYY-MM}         (ex: 2026-05)
    Multiplos ciclos no mesmo periodo -> sobrescrita (P1=a S3).

> S4 Fase 4 (2026-05-20): suporte a paths legacy (pre-2026-05-12) e
> legacy_yyyymmdd (2026-05-12..05-19) removido. Ciclos historicos estao
> em `_Historico/` (audit trail).

Uso CLI:
    python3 resolve_ritual_path.py \\
        --base-dir /path/to/desempenho \\
        --vertical seguros \\
        --ciclo-date 2026-05-22 \\
        --card-path /path/to/card_seg_wl_n3_001.yaml
    # Saida: .../03-Rituais/Seguros-wl/N3-Semanal/2026-S21/
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


# Nivel valido (qualquer um aceito; preserve maiusculas conforme metadata.nivel do Card)
VALID_NIVEIS = ("N1", "N2", "N3", "N4", "N5")

# Cadencias suportadas
VALID_CADENCIAS = ("Semanal", "Mensal")

# Siglas all-caps preservadas (pj2 -> PJ2, nao 'Pj2' do .capitalize())
# wl/re NAO incluidos aqui pois sao subniveis lowercase (concatenados com hifen).
ALL_CAPS_VERTICALS = ("pj2", "pj1", "pj3", "ti", "rh", "ib")


def _vertical_display(vertical: str) -> str:
    """Capitaliza vertical respeitando siglas all-caps conhecidas."""
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


def _normalize_nivel(raw: str | None) -> str:
    """Normaliza metadata.nivel para 'N1'..'N5' (maiusculo, 2 chars)."""
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


def _normalize_subnivel(raw: str | None) -> str | None:
    """Normaliza subnivel para lowercase ou None."""
    if not raw:
        return None
    s = str(raw).strip().lower()
    return s if s and s not in ("null", "none", "~") else None


def _infer_cadencia(nivel: str, card: dict) -> str:
    """Inferir cadencia (Semanal/Mensal) a partir de Card ou heuristica do nivel.

    Prioridade:
    1. card.ritual.cadencia se presente e valida
    2. Heuristica por nivel: N3+ -> Semanal, N2/N1 -> Mensal
    """
    ritual_cfg = card.get("ritual") or {}
    raw = ritual_cfg.get("cadencia")
    if raw:
        s = str(raw).strip()
        if s in VALID_CADENCIAS:
            return s
        if "Semanal" in s:
            return "Semanal"
        if "Mensal" in s:
            return "Mensal"
    # Heuristica
    if nivel in ("N3", "N4", "N5"):
        return "Semanal"
    if nivel in ("N1", "N2"):
        return "Mensal"
    raise ValueError(f"Cadencia nao inferida para nivel {nivel!r}")


def _periodo_from_cadencia(cadencia: str, ciclo_date: date) -> str:
    """Derivar Periodo string a partir da cadencia + ciclo_date.

    Semanal -> {YYYY}-S{NN:02d} (ISO week)
    Mensal  -> {YYYY-MM}
    """
    if cadencia == "Semanal":
        ano, semana, _ = ciclo_date.isocalendar()
        return f"{ano}-S{semana:02d}"
    if cadencia == "Mensal":
        return ciclo_date.strftime("%Y-%m")
    raise ValueError(f"Cadencia desconhecida: {cadencia!r}")


def resolve_ritual_path(
    base_dir: Path | str,
    vertical: str,
    ciclo_date: date,
    card_path: Path | str,
    *,
    level_first: bool = True,
    nivel: str | None = None,
) -> Path:
    """Retorna Path absoluto para diretorio do ritual em 03-Rituais/.

    Estrutura (level_first=True, DEFAULT desde 2026-06-09 — migracao level-first):
        {base}/03-Rituais/{N{N}}/{Vertical-cap}[-{subnivel}]/{Cadencia}/{Periodo}/
    Estrutura (level_first=False, legado flat — via CLI --legacy-flat):
        {base}/03-Rituais/{Vertical-cap}[-{subnivel}]/N{N}-{Cadencia}/{Periodo}/

    Ex (legado): 03-Rituais/Seguros-wl/N3-Semanal/2026-S21/
                 03-Rituais/Consorcios/N3-Semanal/2026-S20/
                 03-Rituais/PJ2/N2-Mensal/2026-05/
    Ex (level-first): 03-Rituais/N3/Seguros-wl/Semanal/2026-S21/
                      03-Rituais/N2/Produtos/Mensal/2026-05/
                      03-Rituais/N1/M7/Mensal/2026-06/

    Args:
        base_dir: raiz do diretorio 03-Rituais/ (ou raiz `desempenho/`)
        vertical: identificador da vertical em lowercase
        ciclo_date: data do ciclo (datetime.date)
        card_path: Path do card_*.yaml com `metadata.nivel` (+ opcional `metadata.subnivel`)
        level_first: se True (DEFAULT desde 2026-06-09 — migracao concluida), nivel vira pasta-pai
                     e o subfolder perde o prefixo "N{N}-" (D2). False (CLI --legacy-flat) = layout legado.
        nivel: override do nivel (N1..N5); precedencia sobre metadata.nivel.

    Returns:
        Path absoluto para o diretorio do ritual (nao cria as pastas — use --create no CLI).

    Raises:
        FileNotFoundError: se card_path nao existir
        ValueError: se nivel/cadencia desconhecido
    """
    base_dir = Path(base_dir).resolve()
    card_path = Path(card_path)
    if not card_path.exists():
        raise FileNotFoundError(f"Card nao encontrado: {card_path}")

    card = yaml.safe_load(card_path.read_text(encoding="utf-8"))
    meta = card.get("metadata") or {}
    nivel_fs = _normalize_nivel(nivel or meta.get("nivel"))
    subnivel = _normalize_subnivel(meta.get("subnivel"))
    cadencia = _infer_cadencia(nivel_fs, card)
    periodo = _periodo_from_cadencia(cadencia, ciclo_date)
    vertical_fs = _vertical_display_with_subnivel(vertical, subnivel)

    # Level-first (D2): nivel vira pasta-pai e o subfolder perde o prefixo "N{N}-".
    # OFF (default) -> path legado byte-identico.
    if level_first:
        parts = [nivel_fs, vertical_fs, cadencia, periodo]
    else:
        parts = [vertical_fs, f"{nivel_fs}-{cadencia}", periodo]

    # Montar path: base_dir [+ "03-Rituais" se nao terminou nele] + parts
    if base_dir.name == "03-Rituais":
        return base_dir.joinpath(*parts)
    return base_dir / "03-Rituais" / Path(*parts)


def main():
    parser = argparse.ArgumentParser(
        description="Resolve canonical path for 03-Rituais/ artifacts (canonical S3)"
    )
    parser.add_argument(
        "--base-dir",
        required=True,
        help="Raiz do repo 'desempenho' OU pasta 03-Rituais/ direto",
    )
    parser.add_argument(
        "--vertical",
        required=True,
        help="Identificador da vertical em lowercase (ex: seguros, pj2)",
    )
    parser.add_argument(
        "--ciclo-date",
        required=True,
        help="Data do ciclo no formato YYYY-MM-DD",
    )
    parser.add_argument(
        "--card-path", required=True,
        help="Path do card_*.yaml com metadata.nivel (+ opcional subnivel)"
    )
    parser.add_argument(
        "--legacy-flat",
        action="store_true",
        help="Forca o layout legado flat ({Vertical}/N{N}-{Cad}/). Default migrou para level-first ON em 2026-06-09.",
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
        help="Criar subpastas apresentacao/ata/briefing/distribuicao",
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
        ritual_dir = resolve_ritual_path(
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
        for sub in ("apresentacao", "ata", "briefing", "distribuicao"):
            (ritual_dir / sub).mkdir(parents=True, exist_ok=True)

    print(ritual_dir)


if __name__ == "__main__":
    main()
