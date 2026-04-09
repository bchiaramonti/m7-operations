---
name: structuring-competencia
description: >-
  Cria estrutura de diretorios e arquivos de controle para nova competencia
  de comissionamento mensal. Use quando o usuario pedir para criar, estruturar
  ou preparar uma nova competencia, ou mencionar "novo mes de comissionamento".

  <example>
  Context: usuario quer iniciar o processamento de um novo mes
  user: "Estrutura a competencia de abril 2026"
  assistant: cria diretorios (raw + 4 fases), 4 arquivos de controle, 8 parametrizacoes
  </example>
user-invocable: true
---

# Estruturar Diretorio de Competencia

Cria a estrutura completa de diretorios e arquivos para uma nova competencia de comissionamento mensal.

## Parametros

O usuario deve informar **mes** e **ano**. Formatos aceitos:
- `MM AAAA` (ex: `04 2026`)
- `Mes AAAA` (ex: `Abril 2026`)
- `Mes de AAAA` (ex: `Abril de 2026`)

Se nao informado, perguntar ao usuario.

### Mapeamento de meses por extenso

Janeiro=01, Fevereiro=02, Marco=03, Abril=04, Maio=05, Junho=06,
Julho=07, Agosto=08, Setembro=09, Outubro=10, Novembro=11, Dezembro=12

## Variaveis

A partir dos parametros, definir:

| Variavel | Formato | Exemplo |
|----------|---------|---------|
| `COMPETENCIA` | `YYYYMM` | `202604` |
| `MES_ANO` | `MM-YY` | `04-26` |
| `MES_NOME` | Nome do mes | `Abril` |
| `PASTA_ANO` | `{workspace}/YYYY/` | `2026/` |
| `PASTA_COMPETENCIA` | `{workspace}/YYYY/MM-YY/` | `2026/04-26/` |

## Workflow

### 1. Validar parametros

- Formato do mes: 01-12
- Formato do ano: 4 digitos, >= 2024
- Se o diretorio ja existe: avisar e perguntar se deseja sobrescrever

### 2. Criar estrutura de diretorios (raw + 4 fases)

```
YYYY/
└── MM-YY/
    ├── raw/
    │   ├── temp/
    │   │   └── .gitkeep
    │   └── .gitkeep
    ├── fase1_comissionamento/
    │   └── .gitkeep
    ├── fase2_parametrizacao/
    │   └── .gitkeep
    ├── fase3_pagamento/
    │   ├── pgto/
    │   │   └── .gitkeep
    │   ├── demonstrativo_xp/
    │   │   └── .gitkeep
    │   ├── compromissada/
    │   │   └── .gitkeep
    │   └── .gitkeep
    └── fase4_dados/
        └── .gitkeep
```

Subdiretorios de `fase3_pagamento/`:
- `pgto/` — arquivos PGTO e emails ao financeiro
- `demonstrativo_xp/` — demonstrativo Excel e email para Wealth
- `compromissada/` — relatorio Parabellum e emails

### 3. Criar 4 arquivos de controle na raiz da competencia

#### CHECKLIST_{COMPETENCIA}.md

Ler o template [CHECKLIST_COMISSIONAMENTO.tmpl.md](templates/CHECKLIST_COMISSIONAMENTO.tmpl.md) e substituir:
- `{YYYYMM}` → Competencia
- `{YYYY}` → Ano
- `{MM}` → Mes com zero
- `{YY}` → Ano abreviado
- `{MES_NOME}` → Nome do mes

Remover a secao `### Variaveis do Template` e tudo abaixo (se existir).

#### CHANGELOG_{COMPETENCIA}.md

Ler o template [CHANGELOG.tmpl.md](templates/CHANGELOG.tmpl.md) e substituir as variaveis.

- Executar `date +"%Y-%m-%d %H:%M"` para obter timestamp real (NUNCA inventar horarios)
- Substituir `{TIMESTAMP}` pelo timestamp real obtido

#### notes_{COMPETENCIA}.md

Ler o template [NOTES.tmpl.md](templates/NOTES.tmpl.md) e substituir as variaveis.

#### AJUSTES_{COMPETENCIA}.md

Ler o template [AJUSTES.tmpl.md](templates/AJUSTES.tmpl.md) e substituir as variaveis.

Remover a secao de exemplo `## ⬜ Ajuste #1` do arquivo gerado (manter apenas o header e a legenda de emojis).

### 4. Criar/copiar arquivos de parametrizacao em `fase2_parametrizacao/`

Os 8 arquivos de parametrizacao:

| Arquivo | Descricao |
|---------|-----------|
| `estrutura_{COMPETENCIA}.csv` | Mapeamento de assessores |
| `comissao_base_{COMPETENCIA}.csv` | Percentuais por chave |
| `cotacao_dolar_{COMPETENCIA}.csv` | Cotacao USD/BRL |
| `apolices_seguros_{COMPETENCIA}.csv` | Apolices com corretor |
| `contas_offshore_{COMPETENCIA}.csv` | Contas internacionais |
| `contratos_consorcio_{COMPETENCIA}.csv` | Contratos de consorcio |
| `rebate_originacao_{COMPETENCIA}.csv` | Rebates e originacao |
| `fixo_piso_{COMPETENCIA}.csv` | Valores fixos e pisos |

**Se existir competencia anterior** (buscar pastas MM-YY ordenadas):
- Copiar os 8 arquivos de `fase2_parametrizacao/`
- Renomear para a nova competencia (substituir YYYYMM antigo pelo novo)

**Se NAO existir competencia anterior**, criar com headers CSV vazios:

```csv
# estrutura_{COMPETENCIA}.csv
codigo_assessor,nome,cpf,status,tipo

# comissao_base_{COMPETENCIA}.csv
chave_comissao,percentual_assessor,percentual_m7

# cotacao_dolar_{COMPETENCIA}.csv
data,cotacao_compra,cotacao_venda

# apolices_seguros_{COMPETENCIA}.csv
numero_apolice,cliente,assessor_responsavel,seguradora,produto

# contas_offshore_{COMPETENCIA}.csv
conta,cliente,assessor_responsavel,corretora

# contratos_consorcio_{COMPETENCIA}.csv
numero_contrato,cliente,assessor_responsavel,administradora,grupo,cota

# rebate_originacao_{COMPETENCIA}.csv
chave_comissao,tipo,percentual,assessor

# fixo_piso_{COMPETENCIA}.csv
assessor,tipo,valor,descricao
```

### 5. Exibir resumo

- Diretorios criados (9: raw, raw/temp, 4 fases, 3 subdirs de fase3_pagamento)
- Arquivos de controle criados (4: CHECKLIST, CHANGELOG, notes, AJUSTES)
- Arquivos de parametrizacao preparados (8)
- Competencia anterior usada como base (se aplicavel)
- Proximos passos

## Exemplo de execucao

```
> Estrutura a competencia 03 2026

Criando estrutura para competencia Marco/2026 (202603)

Diretorios criados (9):
  2026/03-26/raw/
  2026/03-26/raw/temp/
  2026/03-26/fase1_comissionamento/
  2026/03-26/fase2_parametrizacao/
  2026/03-26/fase3_pagamento/
  2026/03-26/fase3_pagamento/pgto/
  2026/03-26/fase3_pagamento/demonstrativo_xp/
  2026/03-26/fase3_pagamento/compromissada/
  2026/03-26/fase4_dados/

Arquivos de controle (4):
  CHECKLIST_202603.md
  CHANGELOG_202603.md
  notes_202603.md
  AJUSTES_202603.md

Arquivos de parametrizacao (8, copiados de 02-26):
  estrutura_202603.csv
  comissao_base_202603.csv
  cotacao_dolar_202603.csv
  apolices_seguros_202603.csv
  contas_offshore_202603.csv
  contratos_consorcio_202603.csv
  rebate_originacao_202603.csv
  fixo_piso_202603.csv

Proximos passos:
1. Coloque os arquivos Excel da XP na pasta raw/
2. Revise/atualize os arquivos de parametrizacao
3. Use o CHECKLIST_202603.md para acompanhar o processamento
4. Valide os arquivos raw quando estiverem prontos
```
