# m7-comissionamento

Processamento mensal de comissionamento da M7 Investimentos.

## Skills

| Skill | Descricao |
|-------|-----------|
| `structuring-competencia` | Cria estrutura de diretorios e arquivos de controle para nova competencia |
| `validating-raw-files` | Valida arquivos Excel na pasta `raw/` (presenca, integridade, colunas) |
| `processing-split-c-receitas` | ETL multicamadas (Bronze/Silver/Gold) de receitas detalhadas Split C |
| `generating-comissao-oficial` | Gera arquivo Excel consolidado para importacao na plataforma Louro Tech |
| `generating-resumo-financeiro` | Gera resumo de comissoes por assessor para o financeiro |

## Fluxo de processamento

```
structuring-competencia     → Preparar pasta da competencia
        ↓
validating-raw-files        → Validar arquivos recebidos da XP
        ↓
processing-split-c-receitas → Carregar receitas no banco M7Medallion
        ↓
generating-comissao-oficial → Gerar arquivo para Louro Tech
        ↓
generating-resumo-financeiro → Gerar resumo para o financeiro
```

## Dependencias Python

- `pandas`
- `openpyxl`
- `pyodbc`
- `python-dotenv`

## Variaveis de ambiente

Definidas em `credentials/.env`:

```
DB_SERVER=172.17.0.10
DB_DATABASE=M7Medallion
DB_USERNAME=m7invest
DB_PASSWORD=<senha>
DB_DRIVER=ODBC Driver 17 for SQL Server
```
