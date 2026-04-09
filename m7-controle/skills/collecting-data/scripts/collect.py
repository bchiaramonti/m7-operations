#!/usr/bin/env python3
"""
collect.py — Motor deterministico de coleta de dados para m7-controle.

Tres subcomandos:
  plan         Le Cards + Indicadores YAML, resolve parametros,
               gera execution-plan.json com steps de execucao de scripts.
  run          Executa cada script do plano via subprocess, gera
               execution-results.json com status por step.
  consolidate  Le outputs dos scripts, valida contra output_contract,
               executa quality checks, gera dados-consolidados + provenance.

O LLM NAO interpreta YAMLs — este script faz isso.
O LLM apenas executa: plan → run → consolidate (3 comandos).

v5.0.0 — YAML-driven projection, timeout 300s, parallel execution, staleness check.
"""

import argparse
import concurrent.futures
import datetime
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERRO: pyyaml nao instalado. Execute: pip3 install pyyaml", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# YAML helpers
# ---------------------------------------------------------------------------

def load_yaml(path: str) -> dict:
    """Load a YAML file, return dict. Handles frontmatter-style docs."""
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    try:
        docs = list(yaml.safe_load_all(content))
        return docs[0] if docs else {}
    except yaml.YAMLError as e:
        print(f"WARN: Erro ao parsear {path}: {e}", file=sys.stderr)
        return {}


def find_indicator_yaml(indicators_dir: str, indicator_id: str, index: dict) -> str | None:
    """Locate the YAML file for an indicator_id.

    Strategy:
    1. Use _index.yaml domain to build path (lowercase and titlecase)
    2. Fallback: walk all subdirectories searching by filename
    """
    fname_target = f"{indicator_id}.yaml"

    # Try index-based lookup with domain
    for entry in index.get("indicators", []):
        if entry.get("id") == indicator_id:
            domain = entry.get("domain", "")
            # Try multiple casing: lowercase, titlecase, uppercase
            for variant in [domain, domain.title(), domain.capitalize(), domain.upper()]:
                candidate = os.path.join(indicators_dir, variant, fname_target)
                if os.path.isfile(candidate):
                    return candidate

    # Fallback: walk all subdirs (handles any directory naming)
    for root, _, files in os.walk(indicators_dir):
        for fname in files:
            if fname == fname_target:
                return os.path.join(root, fname)
    return None


# ---------------------------------------------------------------------------
# Parameter resolution
# ---------------------------------------------------------------------------

def resolve_params(indicator_yaml: dict, cli_params: dict) -> dict:
    """Resolve parameters with precedence: CLI > indicator defaults."""
    resolved = {}
    for param_def in indicator_yaml.get("parameters", []):
        name = param_def["name"]
        default = param_def.get("default", "")
        # CLI override takes precedence
        value = cli_params.get(name, default)
        # Resolve special values
        if value == "today":
            value = datetime.date.today().isoformat()
        elif value == "first_day_current_month":
            today = datetime.date.today()
            value = today.replace(day=1).isoformat()
        resolved[name] = value
    return resolved


# ---------------------------------------------------------------------------
# Checksum
# ---------------------------------------------------------------------------

def compute_sha256(filepath: str) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Card reading
# ---------------------------------------------------------------------------

def collect_indicator_ids_from_card(card: dict) -> list[str]:
    """Extract all indicator_ids referenced by a Card YAML."""
    ids = set()

    # kpi_references (principal KPIs)
    for ref in card.get("kpi_references", []):
        iid = ref.get("indicator_id")
        if iid:
            ids.add(iid)
        # Also collect correlated indicators
        for corr in ref.get("correlacionado_com", []):
            cid = corr.get("id")
            if cid:
                ids.add(cid)

    # logica_de_analise.kpis_analisar_como_contexto
    logica = card.get("logica_de_analise", {})
    for ctx in logica.get("kpis_analisar_como_contexto", []):
        iid = ctx.get("indicator_id")
        if iid:
            ids.add(iid)

    # logica_de_analise.kpis_analisar_juntos
    for grupo in logica.get("kpis_analisar_juntos", []) or []:
        for iid in grupo.get("grupo", []):
            if iid:
                ids.add(iid)

    # logica_de_analise.kpis_analisar_separados
    for sep in logica.get("kpis_analisar_separados", []) or []:
        iid = sep.get("indicator_id") if isinstance(sep, dict) else sep
        if iid:
            ids.add(iid)

    return sorted(ids)


# ---------------------------------------------------------------------------
# Plan generation (v2.0 — script-based)
# ---------------------------------------------------------------------------

def build_script_step(step_id: int, indicator: dict, yaml_path: str,
                      indicators_dir: str, params: dict) -> dict | None:
    """Build an execution step for a v3.0 indicator with script.path."""
    script_block = indicator.get("script", {})
    script_rel_path = script_block.get("path", "")

    if not script_rel_path:
        print(f"WARN: indicator {indicator['id']} has no script.path", file=sys.stderr)
        return None

    # Resolve script path relative to the indicator YAML's vertical directory
    # e.g., YAML at Consorcios/volume_consorcio_mensal.yaml with script.path=scripts/volume.py
    # → Consorcios/scripts/volume.py
    yaml_dir = os.path.dirname(yaml_path)
    script_abs_path = os.path.normpath(os.path.join(yaml_dir, script_rel_path))

    if not os.path.isfile(script_abs_path):
        print(f"WARN: script nao encontrado: {script_abs_path}", file=sys.stderr)
        return None

    # Checksum verification
    expected_checksum = script_block.get("checksum", "")
    actual_checksum = compute_sha256(script_abs_path)
    checksum_verified = (expected_checksum == actual_checksum) if expected_checksum else False

    # Output contract
    output_contract = indicator.get("output_contract", {})

    indicator_id = indicator["id"]

    # Per-script timeout from YAML (optional)
    script_timeout = script_block.get("timeout", None)

    step_dict = {
        "step_id": step_id,
        "indicator_id": indicator_id,
        "indicator_name": indicator.get("name", indicator_id),
        "source_type": indicator.get("source_type", "sql"),
        "script_path": script_abs_path,
        "script_checksum_expected": expected_checksum,
        "script_checksum_actual": actual_checksum,
        "checksum_verified": checksum_verified,
        "test_status": script_block.get("test_status", "untested"),
        "params": params,
        "output_file": f"dados/raw/{indicator_id}.json",
        "output_contract": {
            "columns": output_contract.get("columns", []),
            "types": output_contract.get("types", []),
            "sort": output_contract.get("sort", []),
        },
    }
    if script_timeout is not None:
        step_dict["timeout_override"] = int(script_timeout)

    return step_dict


def cmd_plan(args):
    """Generate an execution plan JSON from Cards + Indicators."""
    cards_dir = args.cards_dir
    indicators_dir = args.indicators_dir
    cycle_folder = args.cycle_folder

    # Parse CLI params
    cli_params = {}
    for p in (args.param or []):
        if "=" in p:
            k, v = p.split("=", 1)
            cli_params[k] = v

    # Load indicator index (optional — fallback to filesystem search if parse fails)
    index_path = os.path.join(indicators_dir, "_index.yaml")
    if os.path.isfile(index_path):
        index = load_yaml(index_path)
        if not index:
            print(f"WARN: _index.yaml falhou no parsing, usando busca por filesystem", file=sys.stderr)
            index = {"indicators": []}
    else:
        print(f"WARN: _index.yaml nao encontrado em {indicators_dir}, usando busca por filesystem", file=sys.stderr)
        index = {"indicators": []}

    # Read all active Cards
    card_ids = []
    all_indicator_ids = set()

    for fname in sorted(os.listdir(cards_dir)):
        if not fname.endswith((".yaml", ".yml")):
            continue
        card_path = os.path.join(cards_dir, fname)
        card = load_yaml(card_path)
        metadata = card.get("metadata", {})
        if metadata.get("status") != "active":
            print(f"SKIP: Card {fname} status={metadata.get('status')} (requer active)", file=sys.stderr)
            continue
        card_ids.append(metadata.get("id", fname))
        ids = collect_indicator_ids_from_card(card)
        all_indicator_ids.update(ids)

    if not card_ids:
        print(f"ERRO: Nenhum Card ativo encontrado em {cards_dir}", file=sys.stderr)
        sys.exit(1)

    if not all_indicator_ids:
        print(f"ERRO: Nenhum indicator_id extraido dos Cards", file=sys.stderr)
        sys.exit(1)

    # Build steps for each indicator
    steps = []
    step_id = 0
    skipped = []
    not_found = []
    checksums_ok = 0
    checksums_fail = 0
    test_status_counts = {"passed": 0, "untested": 0, "failed": 0}

    for iid in sorted(all_indicator_ids):
        yaml_path = find_indicator_yaml(indicators_dir, iid, index)
        if not yaml_path:
            not_found.append(iid)
            continue

        indicator = load_yaml(yaml_path)

        # Filter by status
        status = indicator.get("status", "draft")
        if status not in ("validated", "promoted_to_gold"):
            skipped.append({"id": iid, "status": status})
            continue

        # Resolve parameters
        params = resolve_params(indicator, cli_params)

        step_id += 1
        step = build_script_step(step_id, indicator, yaml_path, indicators_dir, params)
        if step:
            steps.append(step)
            if step["checksum_verified"]:
                checksums_ok += 1
            else:
                checksums_fail += 1
            ts = step.get("test_status", "untested")
            test_status_counts[ts] = test_status_counts.get(ts, 0) + 1

    # Resolve global params for output
    resolved_params = dict(cli_params)
    for k, v in resolved_params.items():
        if v == "today":
            resolved_params[k] = datetime.date.today().isoformat()
        elif v == "first_day_current_month":
            today = datetime.date.today()
            resolved_params[k] = today.replace(day=1).isoformat()

    # Build execution plan
    plan = {
        "schema_version": "2.0",
        "generated_at": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M"),
        "card_ids": card_ids,
        "vertical": os.path.basename(cards_dir.rstrip("/")),
        "resolved_params": resolved_params,
        "indicators_dir": os.path.abspath(indicators_dir),
        "steps": steps,
        "total_scripts": len(steps),
        "checksums_verified": checksums_ok,
        "checksums_failed": checksums_fail,
        "test_status_summary": test_status_counts,
        "skipped_indicators": skipped,
        "not_found_indicators": not_found,
    }

    # Write output
    os.makedirs(cycle_folder, exist_ok=True)
    output_path = os.path.join(cycle_folder, "execution-plan.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2, ensure_ascii=False)

    # Summary to stdout
    print(f"Plano gerado: {output_path}")
    print(f"  Cards ativos: {len(card_ids)}")
    print(f"  Scripts no plano: {len(steps)}")
    print(f"  Checksums verificados: {checksums_ok}/{len(steps)}")
    if checksums_fail:
        print(f"  Checksums FALHA: {checksums_fail}")
    print(f"  Test status: passed={test_status_counts.get('passed',0)}, "
          f"untested={test_status_counts.get('untested',0)}, "
          f"failed={test_status_counts.get('failed',0)}")
    if skipped:
        print(f"  Indicadores ignorados (status): {[s['id'] for s in skipped]}")
    if not_found:
        print(f"  Indicadores nao encontrados: {not_found}")


# ---------------------------------------------------------------------------
# Script execution (NEW in v4.0.0)
# ---------------------------------------------------------------------------

def run_script(step: dict, cycle_folder: str, timeout: int) -> dict:
    """Execute a single indicator script via subprocess.

    Returns a result dict with status, timing, and output info.
    """
    indicator_id = step["indicator_id"]
    script_path = step["script_path"]
    output_file = os.path.join(cycle_folder, step["output_file"])
    params = step.get("params", {})
    # Use per-step timeout override if present in the execution plan
    timeout = step.get("timeout_override", timeout)

    result = {
        "step_id": step["step_id"],
        "indicator_id": indicator_id,
        "script_path": script_path,
        "output_file": step["output_file"],
        "started_at": datetime.datetime.now().isoformat(),
    }

    # Gate: checksum must be verified
    if not step.get("checksum_verified", False):
        result["status"] = "skipped"
        result["error"] = (
            f"Checksum mismatch: expected={step.get('script_checksum_expected','N/A')}, "
            f"actual={step.get('script_checksum_actual','N/A')}"
        )
        result["finished_at"] = datetime.datetime.now().isoformat()
        result["duration_seconds"] = 0.0
        # Write error JSON
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump({
                "indicator_id": indicator_id,
                "extracted_at": result["started_at"],
                "status": "error",
                "error": result["error"],
                "rows_returned": 0,
                "params_used": params,
                "data": [],
            }, f, indent=2, ensure_ascii=False)
        return result

    # Gate: test_status=failed → skip
    if step.get("test_status") == "failed":
        result["status"] = "skipped"
        result["error"] = "Script has test_status=failed. Skipped."
        result["finished_at"] = datetime.datetime.now().isoformat()
        result["duration_seconds"] = 0.0
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump({
                "indicator_id": indicator_id,
                "extracted_at": result["started_at"],
                "status": "error",
                "error": result["error"],
                "rows_returned": 0,
                "params_used": params,
                "data": [],
            }, f, indent=2, ensure_ascii=False)
        return result

    # Build command
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    cmd = ["python3", script_path, "--output", output_file]
    for k, v in params.items():
        cmd.extend(["--param", f"{k}={v}"])

    # Execute
    start_time = time.monotonic()
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=os.environ.copy(),
        )
        elapsed = time.monotonic() - start_time

        result["exit_code"] = proc.returncode
        result["duration_seconds"] = round(elapsed, 2)
        result["finished_at"] = datetime.datetime.now().isoformat()

        if proc.returncode == 0:
            # Verify output file exists and has valid JSON
            if os.path.isfile(output_file):
                try:
                    with open(output_file, "r", encoding="utf-8") as f:
                        output_data = json.load(f)
                    if output_data.get("status") == "success":
                        result["status"] = "success"
                        result["rows_returned"] = output_data.get("rows_returned", 0)
                    else:
                        result["status"] = "error"
                        result["error"] = output_data.get("error", "Script returned non-success status")
                        result["rows_returned"] = 0
                except json.JSONDecodeError as e:
                    result["status"] = "error"
                    result["error"] = f"Invalid JSON in output: {e}"
                    result["rows_returned"] = 0
            else:
                result["status"] = "error"
                result["error"] = "Script exited 0 but output file not found"
                result["rows_returned"] = 0
        else:
            result["status"] = "error"
            result["error"] = proc.stderr[:500] if proc.stderr else f"Exit code {proc.returncode}"
            result["rows_returned"] = 0
            # Write error JSON if script didn't create one
            if not os.path.isfile(output_file):
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump({
                        "indicator_id": indicator_id,
                        "extracted_at": result["started_at"],
                        "status": "error",
                        "error": result["error"],
                        "rows_returned": 0,
                        "params_used": params,
                        "data": [],
                    }, f, indent=2, ensure_ascii=False)

        # Capture stdout/stderr snippets for debugging
        if proc.stdout:
            result["stdout_tail"] = proc.stdout[-300:]
        if proc.stderr:
            result["stderr_tail"] = proc.stderr[-300:]

    except subprocess.TimeoutExpired:
        elapsed = time.monotonic() - start_time
        result["status"] = "error"
        result["error"] = f"Timeout after {timeout}s"
        result["duration_seconds"] = round(elapsed, 2)
        result["finished_at"] = datetime.datetime.now().isoformat()
        result["rows_returned"] = 0
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump({
                "indicator_id": indicator_id,
                "extracted_at": result["started_at"],
                "status": "error",
                "error": result["error"],
                "rows_returned": 0,
                "params_used": params,
                "data": [],
            }, f, indent=2, ensure_ascii=False)

    except Exception as e:
        elapsed = time.monotonic() - start_time
        result["status"] = "error"
        result["error"] = str(e)
        result["duration_seconds"] = round(elapsed, 2)
        result["finished_at"] = datetime.datetime.now().isoformat()
        result["rows_returned"] = 0

    return result


def cmd_run(args):
    """Execute all scripts from the execution plan via subprocess."""
    plan_path = args.plan
    cycle_folder = args.cycle_folder
    timeout = args.timeout
    parallel = args.parallel

    # Load execution plan
    with open(plan_path, "r", encoding="utf-8") as f:
        plan = json.load(f)

    steps = plan.get("steps", [])
    if not steps:
        print("ERRO: Plano sem steps para executar", file=sys.stderr)
        sys.exit(1)

    results = []
    success_count = 0
    skip_count = 0
    error_count = 0

    if parallel and len(steps) > 1:
        max_workers = min(4, len(steps))
        print(f"Executando {len(steps)} scripts em paralelo (max_workers={max_workers})...")

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_step = {
                executor.submit(run_script, step, cycle_folder, timeout): step
                for step in steps
            }
            for future in concurrent.futures.as_completed(future_to_step):
                step = future_to_step[future]
                indicator_id = step["indicator_id"]
                try:
                    result = future.result()
                except Exception as exc:
                    result = {
                        "step_id": step["step_id"],
                        "indicator_id": indicator_id,
                        "status": "error",
                        "error": str(exc),
                    }
                results.append(result)

                status = result["status"]
                if status == "success":
                    success_count += 1
                    print(f"  [{step['step_id']}/{len(steps)}] {indicator_id}... OK ({result.get('rows_returned', 0)} linhas, {result.get('duration_seconds', 0)}s)")
                elif status == "skipped":
                    skip_count += 1
                    print(f"  [{step['step_id']}/{len(steps)}] {indicator_id}... SKIP: {result.get('error', '')}")
                else:
                    error_count += 1
                    print(f"  [{step['step_id']}/{len(steps)}] {indicator_id}... ERRO: {result.get('error', 'unknown')[:100]}")

        # Sort results by step_id for consistent ordering
        results.sort(key=lambda r: r.get("step_id", 0))
    else:
        print(f"Executando {len(steps)} scripts...")

        for step in steps:
            indicator_id = step["indicator_id"]
            test_status = step.get("test_status", "untested")

            # Warning for untested scripts
            if test_status == "untested":
                print(f"  WARN: {indicator_id} test_status=untested", file=sys.stderr)

            print(f"  [{step['step_id']}/{len(steps)}] {indicator_id}...", end=" ", flush=True)

            result = run_script(step, cycle_folder, timeout)
            results.append(result)

            status = result["status"]
            if status == "success":
                success_count += 1
                print(f"OK ({result.get('rows_returned', 0)} linhas, {result.get('duration_seconds', 0)}s)")
            elif status == "skipped":
                skip_count += 1
                print(f"SKIP: {result.get('error', '')}")
            else:
                error_count += 1
                print(f"ERRO: {result.get('error', 'unknown')[:100]}")

    # Write execution results
    total_executed = success_count + error_count  # excludes skipped
    quorum_base = len(steps) - skip_count  # quorum over non-skipped
    quorum_pct = (success_count / quorum_base * 100) if quorum_base > 0 else 0
    quorum_ok = quorum_pct >= 80

    execution_results = {
        "schema_version": "1.0",
        "executed_at": datetime.datetime.now().isoformat(),
        "plan_file": os.path.basename(plan_path),
        "total_steps": len(steps),
        "success": success_count,
        "errors": error_count,
        "skipped": skip_count,
        "quorum_pct": round(quorum_pct, 1),
        "quorum_ok": quorum_ok,
        "results": results,
    }

    results_path = os.path.join(cycle_folder, "execution-results.json")
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(execution_results, f, indent=2, ensure_ascii=False)

    # Summary
    print(f"\nExecucao concluida: {results_path}")
    print(f"  Sucesso: {success_count}/{len(steps)}")
    print(f"  Erros: {error_count}")
    print(f"  Ignorados: {skip_count}")
    print(f"  Quorum: {quorum_pct:.0f}% {'OK' if quorum_ok else 'FALHA (<80%)'}")

    if not quorum_ok:
        print(f"\nATENCAO: Quorum insuficiente ({quorum_pct:.0f}% < 80%). Pipeline deve ser BLOQUEADO.")
        sys.exit(2)


# ---------------------------------------------------------------------------
# Output contract validation
# ---------------------------------------------------------------------------

def validate_output_contract(data: list, contract: dict, indicator_id: str) -> list:
    """Validate script output against the output_contract from YAML.

    Returns list of alert dicts.
    """
    alerts = []
    expected_columns = contract.get("columns", [])
    expected_types = contract.get("types", [])

    if not expected_columns or not data:
        return alerts

    # Check column names
    actual_columns = list(data[0].keys()) if data else []
    missing = [c for c in expected_columns if c not in actual_columns]
    extra = [c for c in actual_columns if c not in expected_columns]

    if missing:
        alerts.append({
            "indicator_id": indicator_id,
            "severity": "critical",
            "dimension": "contract_compliance",
            "message": f"Colunas ausentes no output: {missing}",
        })
    if extra:
        alerts.append({
            "indicator_id": indicator_id,
            "severity": "info",
            "dimension": "contract_compliance",
            "message": f"Colunas extras no output (nao previstas no contrato): {extra}",
        })

    return alerts


# ---------------------------------------------------------------------------
# Quality checks
# ---------------------------------------------------------------------------

def run_standard_quality_checks(data: list, indicator_id: str) -> list:
    """Run standard quality checks (completude, duplicatas, volume)."""
    alerts = []

    if not data:
        alerts.append({
            "indicator_id": indicator_id,
            "severity": "critical",
            "dimension": "volume",
            "message": "Zero linhas retornadas",
        })
        return alerts

    # Completude: check for NULL in required fields only
    # Fields like equipe, squad, assessor, codigo_xp are NULL by design
    # in aggregated levels (N1, N2, N3). Exclude these from completude check.
    HIERARCHY_FIELDS = {"equipe", "squad", "assessor", "codigo_xp", "especialista",
                        "escritorio", "colaborador", "codigo_xp_esp", "codigo_xp_sdr",
                        "pct_atingimento", "dimensao", "nivel", "nome_funil", "funil",
                        "estagio", "nome_estagio", "data_snapshot", "sdr_nome",
                        "meta"}
    total_fields = 0
    null_fields = 0
    for row in data:
        for k, v in row.items():
            if k in HIERARCHY_FIELDS:
                continue
            total_fields += 1
            if v is None:
                null_fields += 1
    if total_fields > 0:
        completude = 1.0 - (null_fields / total_fields)
        if completude < 0.90:
            alerts.append({
                "indicator_id": indicator_id,
                "severity": "critical",
                "dimension": "completude",
                "message": f"Completude {completude:.1%} < 90%",
            })
        elif completude < 0.95:
            alerts.append({
                "indicator_id": indicator_id,
                "severity": "warning",
                "dimension": "completude",
                "message": f"Completude {completude:.1%} entre 90-95%",
            })

    # Staleness check: detect if most recent data is stale (>= 3 months old)
    date_field_names = ["mes", "data", "data_referencia", "data_snapshot"]
    max_date = None
    for row in data:
        for df in date_field_names:
            val = row.get(df)
            if val and isinstance(val, str):
                try:
                    d = datetime.date.fromisoformat(val[:10])
                    if max_date is None or d > max_date:
                        max_date = d
                except (ValueError, TypeError):
                    pass
    if max_date:
        today = datetime.date.today()
        months_stale = (today.year * 12 + today.month) - (max_date.year * 12 + max_date.month)
        if months_stale >= 3:
            alerts.append({
                "indicator_id": indicator_id,
                "severity": "warning",
                "dimension": "staleness",
                "message": f"Dados defasados: ultimo registro de {max_date.isoformat()} ({months_stale} meses atras)",
            })

    return alerts


# ---------------------------------------------------------------------------
# Quality report generation
# ---------------------------------------------------------------------------

def generate_quality_report(
    indicators_results: list,
    all_alerts: list,
    output_path: str,
    vertical: str,
    date_str: str,
):
    """Generate the data-quality-report.md file."""
    critical_alerts = [a for a in all_alerts if a.get("severity") == "critical"]
    warning_alerts = [a for a in all_alerts if a.get("severity") == "warning"]
    info_alerts = [a for a in all_alerts if a.get("severity") == "info"]

    if critical_alerts:
        qualidade_geral = "Critico"
    elif warning_alerts:
        qualidade_geral = "Atencao"
    else:
        qualidade_geral = "OK"

    lines = [
        f"# Data Quality Report - {vertical} - {date_str}",
        "",
        "## Resumo",
        f"- Indicadores coletados: {len(indicators_results)}",
        f"- Qualidade geral: {qualidade_geral}",
        f"- Alertas criticos: {len(critical_alerts)}",
        f"- Alertas atencao: {len(warning_alerts)}",
        "",
    ]

    if critical_alerts:
        lines.append("## Alertas Criticos")
        for a in critical_alerts:
            lines.append(f"- **{a['indicator_id']}**: {a['message']} ({a['dimension']})")
        lines.append("")

    if warning_alerts:
        lines.append("## Alertas Atencao")
        for a in warning_alerts:
            lines.append(f"- **{a['indicator_id']}**: {a['message']} ({a['dimension']})")
        lines.append("")

    if info_alerts:
        lines.append("## Alertas Informativos")
        for a in info_alerts:
            lines.append(f"- **{a['indicator_id']}**: {a['message']} ({a['dimension']})")
        lines.append("")

    lines.append("## Dados Coletados")
    lines.append("| Indicador | Linhas | Qualidade | Script |")
    lines.append("|-----------|--------|-----------|--------|")
    for ir in indicators_results:
        iid = ir["indicator_id"]
        rows = ir.get("rows_count", 0)
        status = ir.get("quality_status", "OK")
        script = os.path.basename(ir.get("script_path", "N/A"))
        lines.append(f"| {iid} | {rows} | {status} | {script} |")
    lines.append("")

    lines.append("## Decisao do Pipeline")
    if critical_alerts:
        lines.append("- **CRITICO**: Pipeline BLOQUEADO. Resolva os alertas criticos antes de avancar para E3.")
    elif warning_alerts:
        lines.append("- **Atencao**: Prossegue com ressalvas registradas.")
    else:
        lines.append("- **OK**: Prossegue para E3.")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# ---------------------------------------------------------------------------
# Consolidation (v4.0.0 — simplified, no transforms)
# ---------------------------------------------------------------------------

def cmd_consolidate(args):
    """Read script outputs, validate quality, produce consolidated output."""
    plan_path = args.plan
    results_path = args.results
    indicators_dir = args.indicators_dir
    cycle_folder = args.cycle_folder
    vertical = args.vertical

    # Load execution plan
    with open(plan_path, "r", encoding="utf-8") as f:
        plan = json.load(f)

    # Load execution results
    with open(results_path, "r", encoding="utf-8") as f:
        exec_results = json.load(f)

    # Build lookup of results by indicator_id
    results_by_id = {}
    for r in exec_results.get("results", []):
        results_by_id[r["indicator_id"]] = r

    # Use indicators_dir from plan if not overridden
    if not indicators_dir:
        indicators_dir = plan.get("indicators_dir", "")
    if not indicators_dir or not os.path.isdir(indicators_dir):
        print(f"ERRO: indicators_dir invalido: {indicators_dir}", file=sys.stderr)
        sys.exit(1)

    # Load indicator index
    index_path = os.path.join(indicators_dir, "_index.yaml")
    index = load_yaml(index_path) if os.path.isfile(index_path) else {"indicators": []}

    indicators_results = []
    script_execution_log = []
    all_alerts = []
    provenance_entries = []
    total_realizado_sum = 0.0
    date_str = datetime.date.today().isoformat()

    for step in plan.get("steps", []):
        indicator_id = step["indicator_id"]
        exec_result = results_by_id.get(indicator_id, {})

        # Skip failed/skipped scripts
        if exec_result.get("status") not in ("success",):
            script_execution_log.append({
                "indicator_id": indicator_id,
                "script_path": step.get("script_path", ""),
                "timestamp": exec_result.get("started_at", ""),
                "status": exec_result.get("status", "unknown"),
                "error": exec_result.get("error", ""),
                "rows_returned": 0,
                "raw_file": step["output_file"],
            })
            if exec_result.get("status") == "error":
                all_alerts.append({
                    "indicator_id": indicator_id,
                    "severity": "critical",
                    "dimension": "coleta",
                    "message": f"Script falhou: {exec_result.get('error', 'unknown')[:100]}",
                })
            continue

        # Read script output JSON
        raw_path = os.path.join(cycle_folder, step["output_file"])
        if not os.path.isfile(raw_path):
            all_alerts.append({
                "indicator_id": indicator_id,
                "severity": "critical",
                "dimension": "coleta",
                "message": "Arquivo de saida nao encontrado",
            })
            continue

        with open(raw_path, "r", encoding="utf-8") as f:
            output_data = json.load(f)

        data = output_data.get("data", [])
        rows = output_data.get("rows_returned", len(data))

        # Provenance
        provenance_entries.append({
            "indicator_id": indicator_id,
            "file": step["output_file"],
            "sha256": compute_sha256(raw_path),
            "status": "success",
            "rows": rows,
        })

        # Execution log
        script_execution_log.append({
            "indicator_id": indicator_id,
            "script_path": step.get("script_path", ""),
            "timestamp": exec_result.get("started_at", ""),
            "status": "success",
            "rows_returned": rows,
            "duration_seconds": exec_result.get("duration_seconds", 0),
            "raw_file": step["output_file"],
        })

        # Validate against output_contract
        contract = step.get("output_contract", {})
        contract_alerts = validate_output_contract(data, contract, indicator_id)
        all_alerts.extend(contract_alerts)

        # Standard quality checks
        quality_alerts = run_standard_quality_checks(data, indicator_id)
        all_alerts.extend(quality_alerts)

        combined_alerts = contract_alerts + quality_alerts
        quality_status = "OK"
        if any(a["severity"] == "critical" for a in combined_alerts):
            quality_status = "Critico"
        elif any(a["severity"] == "warning" for a in combined_alerts):
            quality_status = "Atencao"

        # Sum realizado for verification
        for row in data:
            r = row.get("realizado")
            if r is not None and isinstance(r, (int, float)):
                total_realizado_sum += float(r)

        indicators_results.append({
            "indicator_id": indicator_id,
            "source_type": step.get("source_type", "sql"),
            "rows_count": rows,
            "data": data,
            "quality_status": quality_status,
            "quality_alerts": [a for a in combined_alerts if a["indicator_id"] == indicator_id],
            "raw_file": step["output_file"],
            "script_path": step.get("script_path", ""),
        })

    # Collect quality_checks from indicator YAMLs for pending evaluation
    quality_checks_pending = []
    for ir in indicators_results:
        iid = ir["indicator_id"]
        yaml_path = find_indicator_yaml(indicators_dir, iid, index)
        if yaml_path:
            ind_yaml = load_yaml(yaml_path)
            checks = ind_yaml.get("quality_checks", [])
            if checks:
                quality_checks_pending.append({
                    "indicator_id": iid,
                    "checks": checks,
                    "rows_count": ir["rows_count"],
                })

    # Build consolidated output
    critical_count = len([a for a in all_alerts if a.get("severity") == "critical"])
    qualidade_geral = "Critico" if critical_count > 0 else (
        "Atencao" if any(a.get("severity") == "warning" for a in all_alerts) else "OK"
    )

    # Compute provenance hash
    provenance_path = os.path.join(cycle_folder, "dados", "provenance.json")
    os.makedirs(os.path.dirname(provenance_path), exist_ok=True)
    with open(provenance_path, "w", encoding="utf-8") as f:
        json.dump(provenance_entries, f, indent=2, ensure_ascii=False)
    provenance_sha = compute_sha256(provenance_path)

    consolidated = {
        "metadata": {
            "vertical": vertical,
            "periodo": plan.get("resolved_params", {}),
            "coletado_em": datetime.datetime.now().isoformat(),
            "qualidade_geral": qualidade_geral,
            "alertas_criticos": critical_count,
            "cycle_folder": cycle_folder,
            "execution_plan": os.path.basename(plan_path),
            "script_execution_log": script_execution_log,
            "_verification": {
                "consolidated_at": datetime.datetime.now().isoformat(),
                "indicator_count": len(indicators_results),
                "raw_files_read": [e["file"] for e in provenance_entries],
                "total_realizado_sum": round(total_realizado_sum, 2),
                "provenance_sha256": provenance_sha,
            },
        },
        "indicadores": [
            {
                "indicator_id": ir["indicator_id"],
                "source_type": ir["source_type"],
                "rows_count": ir["rows_count"],
                "quality_status": ir["quality_status"],
                "quality_alerts": ir["quality_alerts"],
                "raw_file": ir["raw_file"],
                "data": ir["data"],
            }
            for ir in indicators_results
        ],
        "quality_checks_pending": quality_checks_pending,
    }

    # Write consolidated JSON
    consolidated_path = os.path.join(cycle_folder, "dados", f"dados-consolidados-{vertical}.json")
    os.makedirs(os.path.dirname(consolidated_path), exist_ok=True)
    with open(consolidated_path, "w", encoding="utf-8") as f:
        json.dump(consolidated, f, indent=2, ensure_ascii=False, default=str)

    # Generate quality report
    report_path = os.path.join(cycle_folder, "data-quality", "data-quality-report.md")
    generate_quality_report(indicators_results, all_alerts, report_path, vertical, date_str)

    # Summary
    print(f"Consolidacao concluida:")
    print(f"  Indicadores processados: {len(indicators_results)}")
    print(f"  Qualidade geral: {qualidade_geral}")
    print(f"  Alertas criticos: {critical_count}")
    print(f"  Dados consolidados: {consolidated_path}")
    print(f"  Quality report: {report_path}")
    print(f"  Provenance: {provenance_path}")

    if critical_count > 0:
        print(f"\nATENCAO: {critical_count} alertas criticos. Pipeline deve ser BLOQUEADO.")
        sys.exit(2)  # Exit code 2 = critical alerts


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Motor deterministico de coleta de dados para m7-controle (v5.0.0)"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Plan subcommand
    plan_parser = subparsers.add_parser("plan", help="Gera plano de execucao JSON")
    plan_parser.add_argument("--cards-dir", required=True, help="Diretorio com Cards YAML ativos")
    plan_parser.add_argument("--indicators-dir", required=True, help="Diretorio da Biblioteca de Indicadores")
    plan_parser.add_argument("--cycle-folder", required=True, help="Pasta do ciclo (output)")
    plan_parser.add_argument("--param", action="append", help="Parametro key=value (pode repetir)")

    # Run subcommand (NEW in v4.0.0)
    run_parser = subparsers.add_parser("run", help="Executa scripts do plano via subprocess")
    run_parser.add_argument("--plan", required=True, help="Caminho do execution-plan.json")
    run_parser.add_argument("--cycle-folder", required=True, help="Pasta do ciclo")
    run_parser.add_argument("--timeout", type=int, default=900, help="Timeout por script em segundos (default: 900 = 15min)")
    run_parser.add_argument("--parallel", action="store_true", help="Executa scripts em paralelo (max 4 workers)")

    # Consolidate subcommand
    cons_parser = subparsers.add_parser("consolidate", help="Consolida outputs dos scripts em dados validados")
    cons_parser.add_argument("--plan", required=True, help="Caminho do execution-plan.json")
    cons_parser.add_argument("--results", required=True, help="Caminho do execution-results.json")
    cons_parser.add_argument("--indicators-dir", default="", help="Diretorio da Biblioteca (override)")
    cons_parser.add_argument("--cycle-folder", required=True, help="Pasta do ciclo")
    cons_parser.add_argument("--vertical", required=True, help="Nome da vertical")

    args = parser.parse_args()

    if args.command == "plan":
        cmd_plan(args)
    elif args.command == "run":
        cmd_run(args)
    elif args.command == "consolidate":
        cmd_consolidate(args)


if __name__ == "__main__":
    main()
