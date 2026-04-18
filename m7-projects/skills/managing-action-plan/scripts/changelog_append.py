#!/usr/bin/env python3
"""
changelog_append.py — Anexa entradas ao changelog.md do projeto.

O changelog vive em `4-status-report/changelog.md` e e append-only.
Entradas mais novas no TOPO (apos o header e antes da entrada anterior).

Tipos de entrada suportados (--op):
    create        Nova acao criada (local + push ClickUp)
    update        Campo(s) alterado(s) em uma acao
    delete        Acao removida
    comment       Comentario adicionado (espelho do ClickUp)
    sync          Sync explicito (com diff resumido)
    init          Primeira inicializacao do plano
    error         Falha registrada (sync abortado, MCP offline, etc.)

Uso:
    python3 changelog_append.py \\
        --file 4-status-report/changelog.md \\
        --op update \\
        --summary "T037 status: not_started -> in_progress" \\
        --details-json '{"clickup_id":"86abc","field":"status","old":"not_started","new":"in_progress"}'

    python3 changelog_append.py --file ... --op comment \\
        --summary "Comentario em No. 2.1.3" \\
        --comment "@bruno revisei, OK p/ seguir"

Saida (stdout, JSON):
    {"ok": true, "lines_added": N, "timestamp": "2026-04-18T14:32:11"}
"""

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

VALID_OPS = {"create", "update", "delete", "comment", "sync", "init", "error"}

CHANGELOG_HEADER_DEFAULT = """# Changelog — Plano de Acao

> Registro cronologico (reverse, mais novo no topo) de todas as operacoes
> sobre o plano de acao. Mantido automaticamente por `managing-action-plan`.
> Append-only: nunca editar entries existentes manualmente.

---
"""


def format_entry(timestamp: str, op: str, summary: str,
                 details: dict | None, comment: str | None) -> str:
    """Formata uma entry padronizada."""
    lines = [f"## {timestamp} — {op} — {summary}", ""]
    lines.append(f"**Operacao:** {op}")
    lines.append(f"**Timestamp:** {timestamp}")

    if comment:
        lines.append("")
        lines.append("**Comentario:**")
        lines.append("")
        for ln in comment.splitlines():
            lines.append(f"> {ln}" if ln else ">")

    if details:
        lines.append("")
        lines.append("**Detalhes:**")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(details, ensure_ascii=False, indent=2, default=str))
        lines.append("```")

    lines.append("")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def find_insert_position(content: str) -> int:
    """
    Retorna a posicao (offset de chars) onde a nova entry deve ser inserida.
    Convencao: apos a primeira linha `---` que segue o header (separador),
    ou ao final se o arquivo so tem o header.
    """
    # Procura primeiro `---` linha sozinha apos o titulo
    lines = content.splitlines(keepends=True)
    pos = 0
    found_separator = False
    for i, ln in enumerate(lines):
        pos += len(ln)
        if ln.strip() == "---" and i > 0:
            found_separator = True
            # Pula tambem a quebra de linha em branco apos o separador, se houver
            if i + 1 < len(lines) and lines[i + 1].strip() == "":
                pos += len(lines[i + 1])
            break
    if not found_separator:
        # Header sem separador — adiciona separador no fim antes da entry
        return len(content)
    return pos


def append_to_changelog(path: Path, entry: str, init_if_missing: bool, project_name: str) -> int:
    """Insere a entry. Retorna numero de linhas adicionadas."""
    if not path.exists():
        if not init_if_missing:
            raise FileNotFoundError(f"Changelog nao existe: {path} (use --init para criar)")
        path.parent.mkdir(parents=True, exist_ok=True)
        header = CHANGELOG_HEADER_DEFAULT
        if project_name:
            header = header.replace("# Changelog — Plano de Acao",
                                    f"# Changelog — Plano de Acao — {project_name}")
        path.write_text(header, encoding="utf-8")

    content = path.read_text(encoding="utf-8")
    pos = find_insert_position(content)

    new_content = content[:pos] + entry + content[pos:]
    path.write_text(new_content, encoding="utf-8")
    return entry.count("\n")


def main() -> int:
    p = argparse.ArgumentParser(description="Append entry ao changelog.md.")
    p.add_argument("--file", required=True, help="Caminho do changelog.md")
    p.add_argument("--op", required=True, choices=sorted(VALID_OPS),
                   help=f"Tipo de operacao: {sorted(VALID_OPS)}")
    p.add_argument("--summary", required=True,
                   help="Resumo de 1 linha (vai no header da entry)")
    p.add_argument("--details-json", default=None,
                   help="JSON com detalhes estruturados (opcional)")
    p.add_argument("--comment", default=None,
                   help="Texto do comentario (so para --op comment)")
    p.add_argument("--init", action="store_true",
                   help="Cria changelog.md com header se nao existir")
    p.add_argument("--project-name", default="",
                   help="Nome do projeto (para header inicial)")
    p.add_argument("--timestamp", default=None,
                   help="ISO timestamp custom (default: agora)")
    args = p.parse_args()

    details = None
    if args.details_json:
        try:
            details = json.loads(args.details_json)
        except json.JSONDecodeError as e:
            print(f"ERRO: --details-json invalido: {e}", file=sys.stderr)
            return 1

    timestamp = args.timestamp or dt.datetime.now().replace(microsecond=0).isoformat()
    entry = format_entry(timestamp, args.op, args.summary, details, args.comment)

    try:
        lines_added = append_to_changelog(Path(args.file), entry, args.init, args.project_name)
    except (FileNotFoundError, OSError) as e:
        print(f"ERRO: {e}", file=sys.stderr)
        return 1

    result = {"ok": True, "lines_added": lines_added, "timestamp": timestamp,
              "file": args.file, "op": args.op}
    json.dump(result, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
