#!/usr/bin/env python3
"""
hash_row.py — CLI para hashing deterministico de uma linha do cronograma.

Uso primario: invocado por sync.py / operation scripts quando precisam
verificar se uma linha mudou em relacao ao baseline. Tambem util para
debug manual.

Modos:
    --row-json '<json>'             Hash uma unica linha passada como JSON
    --stdin                         Le lista de linhas (JSON array) de stdin
    --table                         Quando combinado com --stdin, hasheia a tabela inteira

Exemplos:
    echo '{"no":"1.1","tipo":"Acao","etapa":"X","inicio_plan":"2026-04-01"}' \\
        | python3 hash_row.py --stdin
    python3 hash_row.py --row-json '{"no":"1","tipo":"Fase","etapa":"F"}'

Saida (stdout, JSON):
    {"hash": "sha256...", "fields": {...canonical row...}}
    ou para --table:
    {"table_hash": "sha256...", "row_count": N, "row_hashes": ["..."]}
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _lib import canonical_row, hash_row, hash_table  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description="Hash deterministico de linhas do cronograma.")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--row-json", help="JSON de uma unica linha")
    g.add_argument("--stdin", action="store_true", help="Le linha(s) de stdin")
    p.add_argument("--table", action="store_true",
                   help="Quando --stdin recebe array, computa hash da tabela inteira")
    p.add_argument("--default-year", type=int, default=None,
                   help="Ano default para datas BR sem ano")
    args = p.parse_args()

    if args.row_json:
        try:
            row = json.loads(args.row_json)
        except json.JSONDecodeError as e:
            print(f"ERRO: --row-json nao e JSON valido: {e}", file=sys.stderr)
            return 1
        result = {"hash": hash_row(row, args.default_year),
                  "fields": canonical_row(row, args.default_year)}
        json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 0

    # --stdin
    raw = sys.stdin.read()
    if not raw.strip():
        print("ERRO: stdin vazio", file=sys.stderr)
        return 1
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"ERRO: stdin nao e JSON valido: {e}", file=sys.stderr)
        return 1

    if isinstance(data, dict):
        result = {"hash": hash_row(data, args.default_year),
                  "fields": canonical_row(data, args.default_year)}
    elif isinstance(data, list):
        if args.table:
            result = {"table_hash": hash_table(data, args.default_year),
                      "row_count": len(data),
                      "row_hashes": [hash_row(r, args.default_year) for r in data]}
        else:
            result = [{"hash": hash_row(r, args.default_year),
                       "fields": canonical_row(r, args.default_year)} for r in data]
    else:
        print(f"ERRO: stdin deve ser dict ou array, recebeu {type(data).__name__}", file=sys.stderr)
        return 1

    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
