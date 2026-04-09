# Execution Plan JSON Schema (v2.0)

Schema do arquivo `execution-plan.json` gerado por `collect.py plan`.

> **v2.0 BREAKING**: Steps agora referenciam scripts Python standalone ao inves de chamadas MCP.
> Campos `tool`, `tool_params`, `substeps`, `transform_source`, `post_filters` foram removidos.

## Campos Raiz

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `schema_version` | string | Versao do schema (`"2.0"`) |
| `generated_at` | string | Timestamp ISO de geracao do plano |
| `card_ids` | string[] | IDs dos Cards ativos processados |
| `vertical` | string | Nome da vertical (derivado do dir de cards) |
| `resolved_params` | object | Parametros resolvidos (data_inicio, data_fim, etc.) |
| `indicators_dir` | string | Caminho absoluto da Biblioteca de Indicadores |
| `steps` | Step[] | Lista ordenada de steps a executar |
| `total_scripts` | int | Contagem de scripts (indicadores) |
| `checksums_verified` | int | Quantidade de scripts com checksum OK |
| `checksums_failed` | int | Quantidade de scripts com checksum divergente |
| `test_status_summary` | object | Contagem por test_status: `{passed, untested, failed}` |
| `skipped_indicators` | object[] | Indicadores ignorados por status invalido |
| `not_found_indicators` | string[] | indicator_ids nao encontrados na biblioteca |

## Step (Script)

```json
{
  "step_id": 1,
  "indicator_id": "volume_consorcio_mensal",
  "indicator_name": "Volume Consorcio Mensal",
  "source_type": "sql",
  "script_path": "/abs/path/to/Consorcios/scripts/volume_consorcio_mensal.py",
  "script_checksum_expected": "abc123...",
  "script_checksum_actual": "abc123...",
  "checksum_verified": true,
  "test_status": "passed",
  "params": {
    "data_inicio": "2026-01-01"
  },
  "output_file": "dados/raw/volume_consorcio_mensal.json",
  "output_contract": {
    "columns": ["mes", "nivel", "escritorio", "equipe", "squad", "assessor", "codigo_xp", "meta", "realizado", "pct_atingimento"],
    "types": ["date", "string", "string", "string", "string", "string", "string", "float64", "float64", "float64"],
    "sort": ["mes", "nivel"]
  }
}
```

### Campos do Step

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `step_id` | int | Sequencia de execucao |
| `indicator_id` | string | ID do indicador |
| `indicator_name` | string | Nome legivel |
| `source_type` | string | Tipo descritivo: `sql`, `api`, `hybrid` |
| `script_path` | string | Caminho absoluto do script .py |
| `script_checksum_expected` | string | SHA-256 registrado no YAML |
| `script_checksum_actual` | string | SHA-256 calculado do arquivo atual |
| `checksum_verified` | bool | `true` se expected == actual |
| `test_status` | string | Status de teste: `passed`, `untested`, `failed` |
| `params` | object | Parametros resolvidos para o script |
| `output_file` | string | Caminho relativo do JSON de saida |
| `output_contract` | object | Contrato de saida com columns, types, sort |
| `timeout_override` | int\|null | Timeout em segundos especifico para este script (overrides --timeout global). Lido de `script.timeout` no YAML do indicador. Se ausente, usa o timeout global. |

### Gates de Execucao

| Condicao | Comportamento |
|----------|---------------|
| `checksum_verified: false` | Script SKIP — possivel adulteracao |
| `test_status: "failed"` | Script SKIP — teste anterior falhou |
| `test_status: "untested"` | Script EXECUTA com WARNING |

## Script Output Format

Cada script produz um JSON padronizado via `m7_extract_utils.write_output()`:

```json
{
  "indicator_id": "volume_consorcio_mensal",
  "extracted_at": "2026-03-23T15:47:32.123456",
  "status": "success",
  "rows_returned": 94,
  "params_used": {
    "data_inicio": "2026-01-01"
  },
  "checksum": "sha256 do payload data",
  "data": [ ... ]
}
```

Se o script falhar:

```json
{
  "indicator_id": "volume_consorcio_mensal",
  "extracted_at": "2026-03-23T15:47:32.123456",
  "status": "error",
  "error": "mensagem de erro",
  "rows_returned": 0,
  "params_used": { ... },
  "data": []
}
```

## Execution Results Format

Gerado por `collect.py run`, arquivo `execution-results.json`:

```json
{
  "schema_version": "1.0",
  "executed_at": "2026-03-23T16:00:00",
  "plan_file": "execution-plan.json",
  "total_steps": 9,
  "success": 8,
  "errors": 0,
  "skipped": 1,
  "quorum_pct": 100.0,
  "quorum_ok": true,
  "results": [
    {
      "step_id": 1,
      "indicator_id": "volume_consorcio_mensal",
      "script_path": "/path/to/script.py",
      "output_file": "dados/raw/volume_consorcio_mensal.json",
      "started_at": "ISO timestamp",
      "finished_at": "ISO timestamp",
      "duration_seconds": 3.2,
      "status": "success",
      "rows_returned": 94,
      "exit_code": 0
    }
  ]
}
```

## Fluxo de Execucao

```
collect.py plan  -->  execution-plan.json
                         |
                         v
collect.py run   -->  executa scripts via subprocess
                      (acesso direto a ClickHouse + Bitrix24)
                         |
                         v
                      dados/raw/*.json (output de cada script)
                      execution-results.json (status por script)
                         |
                         v
collect.py consolidate  -->  dados-consolidados.json
                              provenance.json
                              data-quality-report.md
```
