# JSON Schemas v1.2 — Canonical WBR + Sidecars E3/E4

Schemas criados na Sessão A (2026-05-18, S2a B6.25/26) para validar output do pipeline G2.2 contra contrato declarativo. Substituem validação imperativa espalhada em scripts.

## Schemas disponíveis

| Schema | Path | Valida |
|---|---|---|
| WBR Canonical v1.2 | `wbr-canonical-data.schema.json` | Output de E6 (`consolidating-wbr` Fase 4.5) |
| E3 Causa-Raiz | `e3-causa-raiz.schema.json` | Sidecar emitido por E3 Fase 6.5 |
| E4 Ações | `e4-acoes.schema.json` | Sidecar emitido por E4 Fase 6.5 |

## Como usar

### Validação manual

```bash
pip install jsonschema
python -c "
import json
from jsonschema import validate
schema = json.load(open('m7-operations/_schema/v1.2/wbr-canonical-data.schema.json'))
data = json.load(open('path/to/wbr-{vertical}-{data}.data.json'))
validate(data, schema)
print('OK')
"
```

### Hook em E2 (sidecars) — opcional

Em `summarizing-actions` e `analyzing-deviations`, após emitir o sidecar JSON, agente pode validar contra o schema correspondente:

```python
import json
from jsonschema import validate, ValidationError
try:
    schema = json.load(open('m7-operations/_schema/v1.2/e3-causa-raiz.schema.json'))
    data = json.load(open(sidecar_path))
    validate(data, schema)
except ValidationError as e:
    log.error(f"Schema violation: {e.message}")
```

### Hook em E6 (canonical) — opcional

Em `consolidating-wbr` Fase 4.5, após emitir o canonical JSON, validar antes de prosseguir para Fase 5 (WBR Estruturado MD):

```python
schema = json.load(open('m7-operations/_schema/v1.2/wbr-canonical-data.schema.json'))
canonical = json.load(open(canonical_path))
validate(canonical, schema)
```

Se a validação falhar, **BLOQUEAR emissão do MD** — canonical malformado vai propagar bug para deck e briefing.

## Compatibilidade

- **v1.0/v1.1 WBRs** continuam válidos no pipeline atual (builders aplicam fallbacks). O schema v1.2 é **strict** para WBRs gerados em S2a+ (canonical v1.2 declarado no header).
- Campos novos em v1.2 (`causa_raiz_resumo`, `n2.{esp}.volume_estagnado`, `vol_em_risco`, `aggregation_rule_applied`, `acoes`) são **opcionais no schema** (com graceful fallback no build_deck), mas obrigatórios em produção quando applicável.
