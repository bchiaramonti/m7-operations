---
name: generating-resumo-financeiro
description: >-
  Gera resumo de comissoes para o financeiro com agregacao por assessor,
  separando Investimentos, Seguros/Consorcios e Plano de Saude.
  Use quando o usuario pedir resumo financeiro, relatorio para financeiro,
  consolidar comissoes por assessor, ou apos gerar o arquivo COMISSOES_CONSOLIDADAS.

  <example>
  Context: processamento mensal concluido, usuario precisa enviar ao financeiro
  user: "Gera o resumo financeiro de abril 2026"
  assistant: executa script, gera resumo_financeiro_2026-04.xlsx com totais por assessor
  </example>
user-invocable: true
---

# Geracao de Resumo Financeiro

Gera arquivo Excel com resumo de comissoes por assessor no formato solicitado pelo financeiro, separando Investimentos, Seguros/Consorcios e descontos de Plano de Saude.

## Input

- **Arquivo**: `COMISSOES_CONSOLIDADAS_{YYYY}_{MM}.csv`
- **Localizacao**: `{competencia}/fase4_dados/`
- **Formato**: CSV com separador `;` (ponto-e-virgula), encoding UTF-8-BOM

### Colunas utilizadas

| Coluna | Uso |
|--------|-----|
| Nome Assessor | Agrupamento |
| Codigo Assessor | Identificacao |
| CLASSE DE COMISSAO | Categorizacao (Seguros vs outros) |
| Categoria | Categorizacao (Consorcio, Plano de Saude) |
| COMISSAO ASSESSOR LIQUIDA | Valor da comissao |

## Output

- **Arquivo**: `resumo_financeiro_{YYYY}-{MM}.xlsx`
- **Localizacao**: `{competencia}/fase4_dados/`

### Colunas do output

| # | Coluna | Descricao |
|---|--------|-----------|
| 1 | Assessor | Nome do assessor |
| 2 | Codigo | Codigo do assessor (ex: A12345) |
| 3 | Comissao Investimentos | Soma das comissoes de investimentos |
| 4 | Comissao Seguros/Consorcios | Soma de Seguros + Consorcio |
| 5 | Plano de Saude | Valor do desconto (negativo) |
| 6 | Total | Soma de todas as colunas |

### Regras de categorizacao

| Categoria | Regra |
|-----------|-------|
| **Investimentos** | Tudo que NAO seja Seguros, Consorcio ou Plano de Saude |
| **Seguros/Consorcios** | `CLASSE DE COMISSAO = 'Seguros'` OU `Categoria = 'Consorcio'` |
| **Plano de Saude** | `Categoria` contem `'Plano de Saude'` |

## Workflow

### 1. Identificar a competencia

Formato da pasta: `YYYY/MM-YY/` (ex: `2026/04-26/`)

### 2. Executar script

```bash
python3 skills/generating-resumo-financeiro/scripts/gerar_resumo_financeiro.py "{caminho_fase4_dados}" "{YYYYMM}"
```

O script esta em [scripts/gerar_resumo_financeiro.py](scripts/gerar_resumo_financeiro.py).

### 3. Validar output

Apos geracao:
1. Verificar totais batem com COMISSOES_CONSOLIDADAS
2. Conferir se todos assessores estao presentes
3. Validar que Plano de Saude aparece como valor negativo

## Dependencias Python

- `pandas`
- `openpyxl`
