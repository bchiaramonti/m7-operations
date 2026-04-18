#!/usr/bin/env python3
"""
parse_cronograma.py — Parser deterministico do Cronograma.xlsx.

Le um arquivo xlsx e produz um JSON estruturado em stdout. O LLM nao
parseia o xlsx — este script faz isso e devolve dados limpos (canonicos).

Uso:
    python3 parse_cronograma.py --file 4-status-report/Cronograma.xlsx
    python3 parse_cronograma.py --file ... --validate-only
    python3 parse_cronograma.py --file ... --include-hash

Saida (stdout, JSON):
    {
      "rows": [
        {
          "_row_index": 5,                        # linha no xlsx (1-based)
          "no": "1.1",
          "tipo": "Acao",
          "etapa": "Elaborar TAP",
          "responsavel": "Bruno",
          "inicio_plan": "2026-03-27",            # ISO YYYY-MM-DD
          "fim_plan": "2026-03-30",
          "inicio_real": "",
          "fim_real": "",
          "status": "",
          "entregavel": "Documento TAP aprovado",
          "clickup_id": "",
          "_hash": "sha256...",                   # so se --include-hash
          "_parent_no": "1",                      # derivado da hierarquia
          "_level": 2                              # 1=Fase, 2=Acao, 3=Etapa
        },
        ...
      ],
      "table_hash": "sha256...",                  # hash agregado ordenado por no
      "warnings": ["..."],                         # avisos nao-fatais
      "errors": [],                                # erros que impediram parse
      "stats": {"total": 265, "fases": 6, "acoes": 70, "etapas": 189}
    }

Exit codes:
    0 — sucesso (errors == [])
    2 — erros de parse (saida ainda em JSON)
    1 — erro fatal (arquivo nao existe, dependencia faltando)
"""

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _lib import (  # noqa: E402
    CronogramaXLSX,
    HASH_FIELDS,
    NO_PATTERN,
    STATUS_LOCAL_VALIDOS,
    TIPOS_VALIDOS,
    canonical_row,
    date_to_iso,
    hash_row,
    hash_table,
    hierarchy_level,
    parent_no,
)


def validate_rows(rows: list[dict], warnings: list[str], errors: list[str]) -> None:
    """Validacoes de integridade: No. unico, FKs hierarquicas, enums.

    A hierarquia e flexivel: Fases podem ter sub-Fases; o que importa
    semanticamente e que Acoes vivam dentro de Fases (em qualquer nivel)
    e Etapas vivam dentro de Acoes.
    """
    seen_no: set[str] = set()
    tipo_by_no: dict[str, str] = {}

    for row in rows:
        no = str(row.get("no", "") or "").strip()
        idx = row.get("_row_index", "?")

        if not no:
            errors.append(f"linha xlsx {idx}: coluna 'No.' vazia")
            continue

        if not NO_PATTERN.match(no):
            errors.append(f"linha xlsx {idx}: No. '{no}' invalido (esperado N, N.M, N.M.K)")
            continue

        if no in seen_no:
            errors.append(f"linha xlsx {idx}: No. duplicado '{no}'")
        seen_no.add(no)

        tipo = str(row.get("tipo", "") or "").strip()
        tipo_by_no[no] = tipo

        if tipo and tipo not in TIPOS_VALIDOS:
            warnings.append(f"linha xlsx {idx} (No. {no}): Tipo '{tipo}' fora do enum {sorted(TIPOS_VALIDOS)}")

        etapa = str(row.get("etapa", "") or "").strip()
        if not etapa:
            errors.append(f"linha xlsx {idx} (No. {no}): coluna 'Etapa' vazia (titulo obrigatorio)")

        status = str(row.get("status", "") or "").strip()
        if status and status not in STATUS_LOCAL_VALIDOS:
            warnings.append(
                f"linha xlsx {idx} (No. {no}): Status '{status}' fora do enum local "
                f"{sorted(s for s in STATUS_LOCAL_VALIDOS if s)}; sera ignorado no sync local"
            )

    # Coerencia semantica + FK: parent existe e tem tipo compativel
    for row in rows:
        no = str(row.get("no", "") or "").strip()
        if not no:
            continue
        tipo = tipo_by_no.get(no, "")
        p = parent_no(no)

        if not p:
            # Root — so faz sentido ser Fase
            if tipo and tipo not in ("Fase",):
                warnings.append(f"No. {no}: Tipo='{tipo}' na raiz (esperado Fase)")
            continue

        if p not in seen_no:
            warnings.append(f"No. {no}: parent '{p}' nao existe na tabela (sera tratado como orfao no sync)")
            continue

        ptipo = tipo_by_no.get(p, "")
        if tipo in ("Etapas da Ação", "Etapas da Acao") and ptipo not in ("Ação", "Acao"):
            warnings.append(f"No. {no} (Etapa): parent {p} tem Tipo='{ptipo}' (esperado Ação)")
        elif tipo in ("Ação", "Acao") and ptipo not in ("Fase",):
            warnings.append(f"No. {no} (Ação): parent {p} tem Tipo='{ptipo}' (esperado Fase)")


def emit(rows: list[dict], default_year: int | None, include_hash: bool,
         warnings: list[str], errors: list[str]) -> dict:
    """Constroi o payload final com canonical rows, hashes, derivados."""
    canon_rows: list[dict] = []
    stats = {"total": 0, "fases": 0, "acoes": 0, "etapas": 0}
    for row in rows:
        canon = canonical_row(row, default_year)
        canon["_row_index"] = row.get("_row_index", -1)
        canon["_parent_no"] = parent_no(canon["no"])
        canon["_level"] = hierarchy_level(canon["no"])
        if include_hash:
            canon["_hash"] = hash_row(row, default_year)
        canon_rows.append(canon)

        stats["total"] += 1
        tipo = canon.get("tipo", "")
        if tipo == "Fase":
            stats["fases"] += 1
        elif tipo in ("Ação", "Acao"):
            stats["acoes"] += 1
        elif tipo in ("Etapas da Ação", "Etapas da Acao"):
            stats["etapas"] += 1

    return {
        "rows": canon_rows,
        "table_hash": hash_table(rows, default_year),
        "warnings": warnings,
        "errors": errors,
        "stats": stats,
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Parse Cronograma.xlsx em JSON canonico.")
    p.add_argument("--file", required=True, help="Caminho do Cronograma.xlsx")
    p.add_argument("--validate-only", action="store_true",
                   help="So valida; saida = {ok: bool, errors: [], warnings: []}")
    p.add_argument("--include-hash", action="store_true",
                   help="Inclui campo _hash em cada linha (mais lento)")
    p.add_argument("--default-year", type=int, default=None,
                   help="Ano default para datas BR sem ano (ex: '02/abr'). Default: ano corrente.")
    args = p.parse_args()

    path = Path(args.file)
    if not path.exists():
        print(f"ERRO: arquivo nao existe: {path}", file=sys.stderr)
        return 1

    try:
        cron = CronogramaXLSX(path)
        cron.load()
    except (FileNotFoundError, ValueError, RuntimeError) as e:
        print(f"ERRO ao carregar xlsx: {e}", file=sys.stderr)
        return 1

    rows = cron.read_rows()
    warnings: list[str] = []
    errors: list[str] = []
    validate_rows(rows, warnings, errors)

    if args.validate_only:
        compact = {"ok": not errors, "errors": errors, "warnings": warnings,
                   "stats": {"total": len(rows)}}
        json.dump(compact, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 0 if not errors else 2

    payload = emit(rows, args.default_year, args.include_hash, warnings, errors)
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2, default=str)
    sys.stdout.write("\n")
    return 0 if not errors else 2


if __name__ == "__main__":
    sys.exit(main())
