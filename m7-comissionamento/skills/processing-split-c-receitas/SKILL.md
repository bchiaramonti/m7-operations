---
name: processing-split-c-receitas
description: >-
  Processa arquivos CSV de receitas detalhadas Split C para carga no banco
  de dados com validacao multicamadas (Bronze, Silver, Gold). Use quando o
  usuario mencionar Split C, receitas detalhadas, processar CSV de comissoes,
  carregar arquivo de receitas, validar camadas, ou solicitar processamento
  de arquivo RECEITAS DETALHADA.

  <example>
  Context: usuario tem CSV de receitas e quer carregar no banco M7Medallion
  user: "Processa o arquivo de receitas detalhadas de abril"
  assistant: solicita caminho do arquivo, executa ETL Bronze, valida 3 camadas
  </example>
user-invocable: true
---

# Processamento de Receitas Split C

Pipeline ETL completo para receitas detalhadas Split C (comissoes XP):
- **Bronze**: Carga de dados brutos (`bronze.split_c_receitas_detalhadas`)
- **Silver**: Validacao da view normalizada (`silver.vw_fact_receitas_comissionadas`)
- **Gold**: Validacao da view agregada (`gold.vw_receitas_comissionadas_assessor`)

## Regra critica

**O USUARIO DEVE SEMPRE INFORMAR O CAMINHO DO ARQUIVO.** Nunca assuma, sugira ou liste arquivos. Pergunte explicitamente antes de qualquer acao.

## Workflow

### 1. Solicitar arquivo (OBRIGATORIO)

Perguntar ao usuario:
> "Qual o caminho completo do arquivo CSV que deseja processar?"

### 2. Verificar competencia (AUTOMATICO)

O script ETL verifica se a competencia (YYYYMM) ja existe no banco.

**Se NAO existe**: segue para carga (passo 3).

**Se JA existe**: exibe comparacao banco vs arquivo e pergunta:
> 1. Recarregar (apaga e recarrega) — usar `--force`
> 2. Apenas validar (pula para validacao de camadas)

### 3. Executar ETL Bronze

```bash
# Nova carga
python3 skills/processing-split-c-receitas/scripts/etl_split_c.py "CAMINHO_DO_ARQUIVO"

# Forcar reprocessamento
python3 skills/processing-split-c-receitas/scripts/etl_split_c.py "CAMINHO_DO_ARQUIVO" --force

# Apenas verificar se competencia existe
python3 skills/processing-split-c-receitas/scripts/etl_split_c.py "CAMINHO_DO_ARQUIVO" --check-only
```

### 4. Validar camadas (OBRIGATORIO)

Apos o ETL, executar validacao multicamadas:
```bash
python3 skills/processing-split-c-receitas/scripts/validar_camadas.py
```

Verifica: Bronze vs Silver (contagem, receitas, comissoes), Silver vs Gold (totais por tipo), classificacoes pendentes.

### 5. Exibir resumo consolidado (OBRIGATORIO)

```bash
python3 skills/processing-split-c-receitas/scripts/resumo_competencias.py
```

### 6. Classificar comissoes (SE NECESSARIO)

Se a validacao indicar classificacoes pendentes:
```bash
python3 skills/processing-split-c-receitas/scripts/classificar_comissoes.py
```

## Formato do arquivo CSV

- **Nome**: `RECEITAS DETALHADA_YYYYMM.csv` (com espaco)
- **Encoding**: UTF-8 com BOM
- **Delimitador**: `;` (ponto e virgula)
- **Colunas**: 16 colunas de dados (filename, Classificacao, Categoria, Nivel 1-4, Codigo Cliente, Codigo Assessor, Data, Receita Bruta/Liquida, Comissao %/Valor, CHAVE_COMISSAO, CLASSE DE COMISSAO)

## Arquitetura de dados

```
CSV (RECEITAS DETALHADA_YYYYMM.csv)
        |
        v
[etl_split_c.py] --> bronze.split_c_receitas_detalhadas (22 colunas)
        |
        v
[VIEW SQL] --> silver.vw_fact_receitas_comissionadas
        |-- JOIN com bronze.comissao_classificacao
        |-- Adiciona fonte_receita (Investimentos/Cross-Sell)
        v
[VIEW SQL] --> gold.vw_receitas_comissionadas_assessor
        |-- Agregacao por assessor + periodo
        |-- Metricas: receita_total, investimentos, cross_sell
```

## Variaveis de ambiente necessarias

Definidas em `credentials/.env`:

```
DB_SERVER=172.17.0.10
DB_DATABASE=M7Medallion
DB_USERNAME=m7invest
DB_PASSWORD=<senha>
DB_DRIVER=ODBC Driver 17 for SQL Server
```

## Scripts de suporte

| Script | Descricao |
|--------|-----------|
| [etl_split_c.py](scripts/etl_split_c.py) | ETL principal: CSV → Bronze |
| [validar_camadas.py](scripts/validar_camadas.py) | Validacao Bronze → Silver → Gold |
| [resumo_competencias.py](scripts/resumo_competencias.py) | Resumo consolidado das 3 camadas |
| [classificar_comissoes.py](scripts/classificar_comissoes.py) | Classificador interativo de comissoes |

## Tratamento de erros

| Erro | Acao |
|------|------|
| Arquivo nao encontrado | Solicitar novo caminho ao usuario |
| Nome invalido | Informar formato: `RECEITAS DETALHADA_YYYYMM.csv` |
| Arquivo duplicado | Perguntar se deseja reprocessar com `--force` |
| Erro de conexao | Verificar variaveis de ambiente do banco |
| Divergencia Bronze/Silver | Investigar registros nao mapeados na view Silver |
| Divergencia Silver/Gold | Verificar classificacoes pendentes |
| Classificacoes pendentes | Executar `classificar_comissoes.py` |

## Dependencias Python

- `pandas`
- `pyodbc`
- `python-dotenv`
