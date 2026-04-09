# Regras de Qualidade de Dados — Collecting Data (E2)

> Referencia para a skill collecting-data e o script collect.py.
> Define thresholds, classificacao de alertas e regras de validacao.

## Dimensoes de Qualidade

### 1. Checksum Integrity

Verificacao SHA-256 do script antes da execucao. Compara `script.checksum` no YAML com o hash real do arquivo `.py`.

| Resultado | Classificacao | Acao |
|-----------|---------------|------|
| Match | OK | Prossegue |
| Mismatch | Critico | Script SKIP — possivel adulteracao |
| Ausente no YAML | Atencao | Prossegue com warning |

**Verificado em**: `collect.py plan` (calcula e registra no step) e `collect.py run` (verifica antes de executar).

### 2. Contract Compliance

Validacao das colunas de saida do script contra o `output_contract` definido no YAML do indicador.

| Resultado | Classificacao | Acao |
|-----------|---------------|------|
| Todas colunas presentes | OK | Prossegue |
| Colunas extras (nao no contrato) | Informativo | Registra para rastreabilidade |
| Colunas ausentes | Critico | Bloqueia pipeline |

**Como validar:**
```
colunas_esperadas = output_contract.columns
colunas_reais = keys(data[0])
ausentes = esperadas - reais
extras = reais - esperadas
```

### 3. Completude

Percentual de campos esperados preenchidos (nao-nulos) no dataset coletado.

| Threshold | Classificacao | Acao |
|-----------|---------------|------|
| >95% | OK | Prossegue normalmente |
| 90-95% | Atencao | Prossegue com ressalva no report |
| <90% | Critico | Bloqueia pipeline |

**Como calcular:**
```
completude = (campos_preenchidos / campos_esperados) * 100
```

Campos esperados sao definidos pelo `output_contract.columns` do YAML do indicador. Campos hierarquicos (equipe, squad, assessor, codigo_xp, especialista, nivel, meta, pct_atingimento, etc.) sao **excluidos** do calculo — sao NULL by design em niveis agregados (N1, N2, N3).

### 4. Duplicatas

Linhas duplicadas por chave primaria do indicador.

| Threshold | Classificacao | Acao |
|-----------|---------------|------|
| 0% | OK | Prossegue |
| >0% | Critico | Bloqueia pipeline |

**Chave primaria**: definida no campo `primary_key` do YAML do indicador. Se ausente, usar combinacao de `indicator_id` + `data` + `quebra`.

### 5. Defasagem

Diferenca entre a data mais recente nos dados e a data atual (ou `data_fim` do ciclo).

| Threshold | Classificacao | Acao |
|-----------|---------------|------|
| <24h | OK | Prossegue |
| 24-48h | Atencao | Prossegue com ressalva |
| >48h | Critico | Bloqueia pipeline |

**Como calcular:**
```
defasagem = data_atual - max(data_registro)
```

### 6. Quality Checks do YAML

Cada indicador pode definir regras de validacao no campo `quality_checks` do YAML:

```yaml
quality_checks:
  - rule: "realizado_n1 == sum(realizado_n2)"
    severity: critical
    description: "Soma dos N2 deve bater com N1"
  - rule: "realizado >= 0"
    severity: warning
    description: "Realizado nao pode ser negativo"
```

| Resultado | Classificacao | Acao |
|-----------|---------------|------|
| Todos passam | OK | Prossegue |
| Falha em check `warning` | Atencao | Prossegue com ressalva |
| Falha em check `critical` | Critico | Bloqueia pipeline |

### 7. Volume

Numero de linhas retornadas pelo script.

| Threshold | Classificacao | Acao |
|-----------|---------------|------|
| >0 linhas, coerente com periodo | OK | Prossegue |
| 0 linhas para indicador critico | Critico | Bloqueia pipeline |
| 0 linhas para indicador nao-critico | Atencao | Prossegue com ressalva |

### 8. Defasagem Historica (Staleness)

Verifica se os dados mais recentes do indicador estao atualizados em relacao ao periodo de analise. Implementado automaticamente em `collect.py` (quality check na consolidacao).

| Threshold | Classificacao | Acao |
|-----------|---------------|------|
| Dados do periodo atual | OK | Prossegue |
| Dados <3 meses defasados | OK | Prossegue |
| Dados >=3 meses defasados | Atencao (WARNING) | Prossegue com ressalva prominente |
| Sem dados historicos | Info | Registrar ausencia |

**Como calcular:**
```
meses_defasagem = (ano_periodo × 12 + mes_periodo) - (ano_ultimo_dado × 12 + mes_ultimo_dado)
```

**NOTA**: Defasagem historica NAO bloqueia pipeline (nao e Critico). O indicador pode ter dados validos do periodo mas com historico incompleto. O warning sinaliza para E3-E5 que comparativos temporais e projecoes baseadas em historico terao menor confianca.

**Campos verificados**: `mes`, `data`, `data_referencia`, `data_snapshot` (o mais recente encontrado).

---

## Classificacao Final de Alertas

A qualidade geral do ciclo e determinada pelo pior alerta encontrado:

| Qualidade Geral | Condicao |
|-----------------|----------|
| **OK** | Nenhum alerta Critico ou Atencao |
| **Atencao** | Pelo menos 1 alerta Atencao, nenhum Critico |
| **Critico** | Pelo menos 1 alerta Critico |

Quando a qualidade geral e **Critico**, o pipeline bloqueia:
- E3 (analyzing-deviations) NAO deve iniciar
- O Data Quality Report e gerado com os alertas
- O usuario e notificado com a lista de alertas criticos e possiveis acoes corretivas

---

## Formato de Alerta

Cada alerta deve conter:

```
{indicator_id} | {dimensao} | {nivel} | {descricao} | {valor_encontrado} | {threshold}
```

Exemplo:
```
captacao_liquida | contract_compliance | Critico | Colunas ausentes: [meta] | 9/10 cols | 10/10
abertura_contas | completude | Atencao | 92% dos campos preenchidos | 92% | >95%
volume_consorcio | checksum | Critico | Mismatch SHA-256 | abc... | def...
```

---

## Regras de Precedencia

1. Checksum mismatch sempre bloqueia o script (nem executa)
2. Alertas Criticos sempre bloqueiam pipeline, independente de outros indicadores estarem OK
3. Um indicador pode ter multiplos alertas (ex: Atencao em completude + Informativo em contract_compliance)
4. O pior alerta de cada indicador define seu `quality_status` no JSON consolidado
5. Quality checks do YAML tem precedencia sobre regras genericas (ex: se o YAML define completude minima de 98%, usar 98% ao inves de 95%)
