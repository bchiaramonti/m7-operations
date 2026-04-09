# ESP-PERF-002 — Resumo de Regras para Cards de Performance

> Referencia: ESP-PERF-002 v1.1, Secao 6.5

## Indice

1. [12 Regras de Validacao](#12-regras-de-validacao)
2. [Aditividade](#aditividade)
3. [Ciclo de Vida](#ciclo-de-vida)
4. [Correlacoes](#correlacoes)
5. [Pipeline de Execucao](#pipeline-de-execucao)

---

## 12 Regras de Validacao

Estas regras devem ser verificadas no Modo 2 (Validar). Issues sao classificadas como **CRITICO** (bloqueia ativacao), **ATENCAO** (nao bloqueia) ou **OK**.

| # | Regra | Severidade se falha |
|---|-------|---------------------|
| 1 | `id` em snake_case e correspondente ao nome do arquivo (sem `.yaml`) | CRITICO |
| 2 | Todos os `indicator_id` referenciados existem na Biblioteca de Indicadores | CRITICO |
| 3 | Indicadores com status `a_mapear` nao podem estar em Cards com status `active` | CRITICO |
| 4 | `kpis_analisar_juntos` + `kpis_analisar_separados` cobrem todos os `kpi_principal` | CRITICO |
| 5 | Cada `sequencia_analise` tem minimo 3 passos com `step`, `acao`, `pergunta_chave` | CRITICO |
| 6 | `quebras_obrigatorias` existem como colunas nas queries dos indicadores referenciados | ATENCAO |
| 7 | Correlacoes sao bidirecionais (se A declara B, B deve declarar A) | ATENCAO |
| 8 | `conteudo_obrigatorio` referencia KPIs presentes no Card | ATENCAO |
| 9 | `codigo` em UPPERCASE com hifens, derivavel do `id` (substituir `_` por `-`, uppercase) | CRITICO |
| 10 | `vertical_code` valido: INV, CRE, UNI, SEG | CRITICO |
| 11 | `nivel` valido: N1, N2, N3, N4 | CRITICO |
| 12 | `subnivel` consistente entre `id` e `codigo` (se presente em um, deve estar no outro) | ATENCAO |

### Formato do relatorio de validacao

Para cada regra, reportar:

```
| # | Regra | Status | Detalhe |
|---|-------|--------|---------|
| 1 | ID em snake_case | OK | card_inv_n1_001 corresponde ao arquivo |
| 2 | indicator_ids validos | CRITICO | captacao_liquida_mensal nao encontrado na Biblioteca |
```

---

## Aditividade

A classificacao de `tipo_realizacao` determina como valores sao agregados entre niveis hierarquicos (N4 → N3 → N2 → N1).

| Tipo | Regra de Agregacao | Exemplo |
|------|-------------------|---------|
| **aditivo** | N1 = SUM(N4) para realizado E meta | Captacao Liquida (R$), Volume de Deals |
| **nao_aditivo** | N1 ≠ SUM(N4). Usar AVG, MAX ou recalcular por formula propria | IEA (score), NPS |
| **parcialmente_aditivo** | Contagens sao aditivas; percentuais derivados dos sums | Rentabilidade: pct = SUM(abaixo_bench)/SUM(total) |

### Regra Critica

**NUNCA somar percentuais entre assessores.** Percentuais de indicadores `parcialmente_aditivo` devem ser recalculados a partir das contagens agregadas.

Exemplo correto:
```
Assessor A: 3/10 = 30%
Assessor B: 7/10 = 70%
Equipe: (3+7)/(10+10) = 50%   ← CORRETO (recalcula)
Equipe: (30%+70%)/2 = 50%     ← ERRADO (coincidencia neste caso, falha em geral)
```

### Campos de regras_meta

Para cada KPI, `regras_meta` pode conter:
- `tipo_agregacao`: sum | avg | max | recalcular
- `formula_agregacao`: expressao customizada se `recalcular`
- `peso`: peso para media ponderada (se avg)

---

## Ciclo de Vida

| Status | Pode transicionar para | Condicao |
|--------|----------------------|----------|
| `draft` | `active` | Todos os `kpi_references` com `indicator_id` valido; `sequencia_analise` definida; validacao sem CRITICO |
| `active` | `archived` | Motivo registrado: substituido por nova versao OU area desativada |
| `archived` | (terminal) | Manter para rastreabilidade. **Nunca deletar** |

### Versionamento

- **MAJOR** (1.0.0 → 2.0.0): Mudanca estrutural (remocao de KPI principal, reestruturacao de arvore)
- **MINOR** (1.0.0 → 1.1.0): Adicao de KPI, novo grupo em logica_de_analise
- **PATCH** (1.0.0 → 1.0.1): Ajuste de descricao, parametro, criterio_desvio_critico

---

## Correlacoes

Correlacoes entre KPIs devem ser **bidirecionais** e tipadas:

| Tipo | Significado | Exemplo |
|------|-------------|---------|
| **direta** | Sobem e descem juntos | Captacao e AuM |
| **inversa** | Um sobe quando o outro desce | Resgates e Retencao |
| **contexto** | Consultado condicionalmente, sem relacao causal | Selic e Captacao |

Se o Card de A declara correlacao com B:
1. Verificar se o Card de B (ou o indicador B) tambem declara correlacao com A
2. Se nao, registrar como issue ATENCAO na validacao

---

## Pipeline de Execucao (parametros_execucao)

O pipeline de 7 passos e fixo conforme ESP-PERF-002. Cada Card herda esta sequencia:

| Passo | Nome | Descricao | Gate? |
|-------|------|-----------|-------|
| 1 | Coleta | Executar scripts dos indicadores via collect.py (ClickHouse/Bitrix24 direto) | Nao |
| 2 | Validacao de Qualidade | quality_checks + checks de aditividade | **Sim** — bloqueia se falhar |
| 3 | Calculo de Metricas Derivadas | Acumulados YTD, comparativos MoM, percentuais derivados | Nao |
| 4 | Analise Correlacional | Executar sequencia_analise dos kpis_analisar_juntos | Nao |
| 5 | Analise Independente | Executar sequencia_analise dos kpis_analisar_separados | Nao |
| 6 | Geracao do Relatorio | Montar WBR/MBR conforme formato e conteudo_obrigatorio | Nao |
| 7 | Distribuicao | Enviar conforme canal e destinatarios | Nao |

O Passo 2 e um gate: se a validacao de qualidade falha (alertas criticos), o pipeline nao avanca para Passo 3+.
