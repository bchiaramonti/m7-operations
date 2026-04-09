# Relatorio de Validacao: {{id}}

**Data:** {{YYYY-MM-DD}}
**Status atual:** {{status}}
**Source type:** {{source_type}}
**Arquivo:** {{caminho_completo}}

---

## Resumo

| Categoria | CRITICO | ATENCAO | OK |
|-----------|---------|---------|-----|
| Campos obrigatorios | {{X}} | {{X}} | {{X}} |
| Campos condicionais ({{source_type}}) | {{X}} | {{X}} | {{X}} |
| Campos opcionais | {{X}} | {{X}} | {{X}} |
| Regras de validacao | {{X}} | {{X}} | {{X}} |
| **Total** | **{{X}}** | **{{X}}** | **{{X}}** |

---

## Issues

### CRITICO

{{Para cada issue critico:}}
- [ ] **{{campo}}**: {{descricao do problema}}

{{Se nenhum:}}
- Nenhum issue critico encontrado.

### ATENCAO

{{Para cada issue de atencao:}}
- [ ] **{{campo}}**: {{descricao do problema}}

{{Se nenhum:}}
- Nenhum issue de atencao encontrado.

### OK

{{Para cada campo conforme:}}
- [x] **{{campo}}**: conforme

---

## Detalhamento

### Campos Obrigatorios

| Campo | Valor | Status |
|-------|-------|--------|
| id | `{{valor}}` | {{OK/CRITICO}} |
| name | `{{valor}}` | {{OK/CRITICO}} |
| description | `{{primeiros 50 chars}}...` | {{OK/CRITICO}} |
| domain | `{{valor}}` | {{OK/CRITICO}} |
| source_type | `{{valor}}` | {{OK/CRITICO}} |
| unit | `{{valor}}` | {{OK/CRITICO}} |
| granularity | `{{valor}}` | {{OK/CRITICO}} |
| source_layer | `{{valor}}` | {{OK/CRITICO}} |
| owner | `{{valor}}` | {{OK/CRITICO}} |
| updated_at | `{{valor}}` | {{OK/CRITICO}} |

### Campos Condicionais ({{source_type}})

{{Para sql:}}
| Regra | Status |
|-------|--------|
| query presente e nao vazio | {{OK/CRITICO}} |
| extraction ausente | {{OK/CRITICO}} |
| Query usa @param_name | {{OK/ATENCAO}} |
| Query retorna colunas-padrao | {{OK/ATENCAO}} |

{{Para mcp:}}
| Regra | Status |
|-------|--------|
| extraction presente | {{OK/CRITICO}} |
| query ausente/null | {{OK/CRITICO}} |
| extraction.steps com source: mcp | {{OK/CRITICO}} |
| output_fields em cada step | {{OK/ATENCAO}} |
| output_schema com columns/types/sort | {{OK/ATENCAO}} |

{{Para hybrid:}}
| Regra | Status |
|-------|--------|
| extraction presente | {{OK/CRITICO}} |
| bridge presente | {{OK/CRITICO}} |
| query ausente/null | {{OK/CRITICO}} |
| Steps mcp + sql | {{OK/CRITICO}} |
| Dependencies com prefixo | {{OK/ATENCAO}} |

### Validacao por Status

{{Se status = validated ou promoted_to_gold:}}
| Regra | Status |
|-------|--------|
| quality_checks presentes | {{OK/CRITICO}} |
| analysis_guide preenchido | {{OK/CRITICO}} |
| explanatory_context.related_indicators (>=2) | {{OK/ATENCAO}} |
| explanatory_context.segmentation_dimensions (>=3) | {{OK/ATENCAO}} |
| explanatory_context.external_factors (>=1) | {{OK/ATENCAO}} |
| explanatory_context.investigation_playbook (>=5) | {{OK/ATENCAO}} |

{{Se status = promoted_to_gold:}}
| Regra | Status |
|-------|--------|
| source_layer = gold | {{OK/CRITICO}} |

### Consistencia

| Check | Status |
|-------|--------|
| id corresponde ao nome do arquivo | {{OK/CRITICO}} |
| domain corresponde ao subdiretorio | {{OK/CRITICO}} |
| parameters referenciados existem | {{OK/ATENCAO}} |
| dependencies completas | {{OK/ATENCAO}} |
| tags lowercase sem acentos | {{OK/ATENCAO}} |

---

## Teste com Dados Reais

{{Se MCP acessivel:}}

### Query/Extraction

| Teste | Resultado |
|-------|-----------|
| Execucao sem erro | {{OK/CRITICO}} |
| Retornou dados | {{OK/CRITICO}} |
| Colunas esperadas presentes | {{OK/ATENCAO}} |
| Linhas retornadas | {{N}} |

### Quality Checks

| Check | Resultado |
|-------|-----------|
| {{descricao do check}} | {{PASS/FAIL}} |

{{Se MCP nao acessivel:}}
> Teste com dados reais nao executado (MCP nao acessivel).

---

## Recomendacoes

{{Lista de proximos passos para resolver issues, ordenada por prioridade:}}

1. {{Resolver issue CRITICO 1}}
2. {{Resolver issue CRITICO 2}}
3. {{Melhorar issue ATENCAO 1}}

---

**Veredicto**: {{APROVADO | APROVADO COM RESSALVAS | REPROVADO}}

{{APROVADO: 0 CRITICO, 0 ATENCAO}}
{{APROVADO COM RESSALVAS: 0 CRITICO, >=1 ATENCAO}}
{{REPROVADO: >=1 CRITICO}}
