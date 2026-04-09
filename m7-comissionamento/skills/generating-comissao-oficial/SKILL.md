---
name: generating-comissao-oficial
description: >-
  Gera arquivo Excel consolidado de comissoes (comissao_oficial_louro_tech.xlsx)
  a partir do RECEITAS_DETALHADAS para importacao na plataforma Louro Tech.
  Use quando o usuario pedir para gerar comissao oficial, consolidar receitas,
  criar arquivo para Louro Tech, ou preparar dados para importacao.

  <example>
  Context: receitas detalhadas prontas, usuario precisa importar no Louro Tech
  user: "Gera a comissao oficial de abril 2026"
  assistant: executa script, ajusta datas, gera comissao_oficial_louro_tech_2026-04.xlsx
  </example>
user-invocable: true
---

# Geracao de Comissao Oficial Louro Tech

Gera o arquivo `comissao_oficial_louro_tech_YYYY-MM.xlsx` consolidando as receitas detalhadas de uma competencia para importacao no sistema Louro Tech.

## Input

- **Arquivo**: `RECEITAS_DETALHADAS_{YYYY}_{MM}.csv`
- **Localizacao**: `{competencia}/raw/`
- **Formato**: CSV com separador `;`, encoding UTF-8-BOM

### Colunas do input

| Coluna | Tipo | Descricao |
|--------|------|-----------|
| filename | string | Arquivo de origem (sera removida) |
| Classificacao | string | Tipo de receita |
| Categoria | string | Categoria do produto |
| Nivel 1-4 | string | Hierarquia |
| Codigo Cliente | integer | Codigo do cliente XP |
| Codigo Assessor | string | Codigo do assessor (ex: A12345) |
| Data | date | Data da receita (DD/MM/YYYY) |
| Receita Bruta / Liquida | decimal | Valores (separador decimal: virgula) |
| Comissao % / Valor Escritorio | decimal | Comissao |
| CHAVE_COMISSAO | string | Chave calculada (sera removida) |
| CLASSE DE COMISSAO | string | Classe (sera removida) |

## Output

- **Arquivo**: `comissao_oficial_louro_tech_{YYYY}-{MM}.xlsx`
- **Localizacao**: `{competencia}/fase4_dados/`

### Colunas do output (10 colunas — ordem exata para importacao)

| # | Coluna | Origem |
|---|--------|--------|
| 1 | Classificacao | Classificacao |
| 2 | Produto/Categoria | = Categoria (copia) |
| 3 | Nivel 1 | Nivel 1 |
| 4 | Nivel 2 | Nivel 2 |
| 5 | Nivel 3 | Nivel 3 |
| 6 | Nivel 4 | Nivel 4 |
| 7 | Codigo Cliente | Codigo Cliente |
| 8 | Data | Data (ajustada) |
| 9 | Comissao (R$) Escritorio | Comissao Escritorio |
| 10 | Codigo Assessor | Codigo Assessor |

**A ordem das colunas e critica para importacao na plataforma Louro Tech.**

### Tratamento de datas

A plataforma Louro Tech requer que todas as receitas sejam do mes da competencia:

| Situacao | Tratamento |
|----------|------------|
| Data vazia | Preenche com ultimo dia do mes da competencia |
| Data de outro mes | Ajusta para o mes da competencia (mantem dia se possivel) |
| Dia > ultimo dia do mes | Usa o ultimo dia do mes (ex: 31 → 28 em fevereiro) |

## Workflow

### 1. Identificar a competencia

Perguntar ao usuario ou identificar pelo contexto. O arquivo deve estar em `raw/RECEITAS_DETALHADAS_{YYYY}_{MM}.csv`.

### 2. Validar arquivo de entrada

Verificar: arquivo existe, tem as colunas esperadas, nao esta vazio.

### 3. Executar script

```bash
python3 skills/generating-comissao-oficial/scripts/gerar_comissao_oficial.py "{caminho_competencia}" "{YYYYMM}"
```

O script esta em [scripts/gerar_comissao_oficial.py](scripts/gerar_comissao_oficial.py).

**Caminhos**:
- Le de: `{caminho_competencia}/raw/RECEITAS_DETALHADAS_{YYYY}_{MM}.csv`
- Salva em: `{caminho_competencia}/fase4_dados/comissao_oficial_louro_tech_{YYYY}-{MM}.xlsx`

### 4. Validar output

1. Arquivo `.xlsx` foi criado
2. Numero de linhas bate com o CSV de entrada
3. Todas as datas sao do mes da competencia

## Tratamento de erros

| Erro | Solucao |
|------|---------|
| Arquivo nao encontrado | Verificar se raw/ existe e se RECEITAS_DETALHADAS foi gerado |
| Colunas faltando | Verificar se o CSV esta no formato correto |
| Encoding incorreto | Usar UTF-8-BOM para leitura |

## Dependencias Python

- `pandas`
- `openpyxl`
