#!/usr/bin/env python3
"""smoke_check_deck.py — smoke-check pos-render do deck HTML do ritual (P2.4, 2026-06-18).

Procura sinais de render QUEBRADO que hoje so o humano pega abrindo o deck:
  HARD (quebra dura, exit 1): placeholder {{...}} nao substituido, TODO residual.
  SOFT (advisory, exit 0):    "SEM DADOS", celula None/NaN/undefined, currency vazia,
                              parenteses vazios "()", mojibake (UTF-8 lido como Latin1).

Uso:
    python3 smoke_check_deck.py --deck path/ritual-*.html [--briefing path] [--strict]

--strict: trata os SOFT tambem como falha (exit 1). Default: SOFT so avisa.

Exit: 0 OK / 1 sinal HARD (ou SOFT com --strict) / 2 arquivo nao encontrado.
"""
import argparse
import re
import sys
from pathlib import Path

# Padroes de quebra dura — um deck FINAL nunca deveria conte-los.
HARD_PATTERNS = {
    "placeholder_nao_substituido": r"\{\{[^}\n]{1,80}\}\}",   # {{ ALGO }} nao preenchido
    "todo_residual": r"\bTODO\b",                            # narrativa livre nao preenchida
}

# Padroes de suspeita (advisory) — podem ser bug de dado/lookup.
SOFT_PATTERNS = {
    "sem_dados": r"SEM\s+DADOS?\b",
    "celula_none": r">\s*None\s*<",
    "celula_nan": r">\s*[Nn]a[Nn]\s*<|\bNaN\b",
    "undefined": r"\bundefined\b",
    "currency_vazia": r"R\$\s*(?=<)",          # "R$ " seguido de fechamento de tag
    "parenteses_vazios": r">\s*\(\s*\)\s*<",   # "()" — label vazio (ver fix realizado_label)
    "mojibake": r"Ã©|Ã£|Ã§|Ã¡|Ã³|Ã­|Ãª|Ã´|Ã¢|â€“|â€”|â€™|Ã‡|Ãƒ",
}


def scan(html: str) -> dict[str, int]:
    res: dict[str, int] = {}
    for name, pat in {**HARD_PATTERNS, **SOFT_PATTERNS}.items():
        hits = re.findall(pat, html)
        if hits:
            res[name] = len(hits)
    return res


def check_file(path: Path, strict: bool) -> int:
    if not path.exists():
        print(f"[smoke] ERRO: arquivo nao encontrado: {path}", file=sys.stderr)
        return 2
    html = path.read_text(encoding="utf-8", errors="replace")
    res = scan(html)
    if not res:
        print(f"[smoke] OK — nenhum sinal de render quebrado em {path.name}")
        return 0
    hard_hit = any(k in res for k in HARD_PATTERNS)
    print(f"[smoke] {path.name}: sinais detectados:", file=sys.stderr)
    for k, v in res.items():
        tier = "HARD" if k in HARD_PATTERNS else "soft"
        print(f"  [{tier}] {k}: {v}", file=sys.stderr)
    if hard_hit or (strict and res):
        print("[smoke] FALHA — render quebrado (placeholder/TODO" +
              (" ou sinal soft em --strict" if strict else "") + "); exit 1", file=sys.stderr)
        return 1
    print("[smoke] ADVISORY — revise os sinais soft acima (exit 0)", file=sys.stderr)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Smoke-check pos-render do deck/briefing HTML")
    ap.add_argument("--deck", required=True, help="Path do deck HTML do ritual")
    ap.add_argument("--briefing", default=None, help="Path do briefing HTML (opcional)")
    ap.add_argument("--strict", action="store_true", help="SOFT tambem falha (exit 1)")
    args = ap.parse_args()
    code = check_file(Path(args.deck), args.strict)
    if args.briefing:
        code = max(code, check_file(Path(args.briefing), args.strict))
    return code


if __name__ == "__main__":
    sys.exit(main())
