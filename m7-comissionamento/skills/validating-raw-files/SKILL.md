---
name: validating-raw-files
description: >-
  Valida arquivos Excel na pasta raw/ de uma competencia de comissionamento.
  Verifica presenca dos 12 arquivos esperados por produto, integridade,
  colunas e contagem de registros. Use quando o usuario pedir para validar
  arquivos raw, conferir recebimento, ou verificar se os arquivos da XP
  estao corretos.

  <example>
  Context: usuario recebeu os arquivos da XP e quer validar
  user: "Valida os arquivos raw da competencia 202604"
  assistant: lista 12 arquivos esperados, verifica integridade e colunas de cada um
  </example>
user-invocable: true
---

# Validar Arquivos Raw

Valida os arquivos Excel da pasta `raw/` de uma competencia, identificando presenca, integridade, colunas e contagem de registros.

**Modo**: somente leitura — nao modifica nenhum arquivo.

## Parametros

- **Competencia**: formato `YYYYMM` (ex: `202604`)

Se nao informado, perguntar ao usuario.

## Variaveis

A partir da competencia:

| Variavel | Formato | Exemplo |
|----------|---------|---------|
| `COMPETENCIA` | `YYYYMM` | `202604` |
| `ANO` | `YYYY` | `2026` |
| `MES` | `MM` | `04` |
| `MES_ANO` | `MM-YY` | `04-26` |
| `PASTA_RAW` | `{ANO}/{MES_ANO}/raw/` | `2026/04-26/raw/` |

## Workflow

### 1. Verificar existencia da pasta

Se `{PASTA_RAW}` nao existe, informar ao usuario e sugerir usar a skill `structuring-competencia`.

### 2. Listar arquivos presentes

Listar todos os arquivos na pasta raw/:
```bash
ls -la {PASTA_RAW}
```

### 3. Verificar os 12 arquivos esperados

| # | Produto | Nome esperado |
|---|---------|---------------|
| 1 | Investimentos | `investimentos_{YYYYMM}.xlsx` |
| 2 | XP US | `xp_us_{YYYYMM}.xlsx` |
| 3 | Mercado Internacional | `mercado_internacional_{YYYYMM}.xlsx` |
| 4 | Co-corretagem Terceiras | `cocorretagem_terceiras_{YYYYMM}.xlsx` |
| 5 | XP CS | `xp_cs_{YYYYMM}.xlsx` |
| 6 | Co-corretagem XPVP | `cocorretagem_xpvp_{YYYYMM}.xlsx` |
| 7 | Credito | `credito_{YYYYMM}.xlsx` |
| 8 | Financiamento Imobiliario | `financiamento_imobiliario_{YYYYMM}.xlsx` |
| 9 | Cambio | `cambio_{YYYYMM}.xlsx` |
| 10 | Avenue | `avenue_{YYYYMM}.xlsx` |
| 11 | Seguros | `seguros_{YYYYMM}.xlsx` |
| 12 | Consorcio | `consorcio_{YYYYMM}.xlsx` |

Para cada arquivo: verificar se existe (pode ter nome diferente — identificar pelo conteudo).

### 4. Validar cada arquivo encontrado

#### 4.1 Integridade
- Tentar abrir o arquivo (verificar se nao esta corrompido)
- Verificar tamanho > 0 bytes

#### 4.2 Identificacao do produto
Identificar a qual produto o arquivo corresponde baseado em: nome, colunas, conteudo das primeiras linhas.

#### 4.3 Validacao de colunas

Verificar se as colunas obrigatorias de cada produto estao presentes. Consultar a especificacao completa em [column-specs.md](references/column-specs.md).

#### 4.4 Contagem de registros
- Total de linhas (excluindo cabecalho)
- Linhas vazias
- Linhas com dados

### 5. Gerar relatorio

```
========================================
VALIDACAO DE ARQUIVOS RAW
Competencia: {MES_NOME}/{ANO} ({COMPETENCIA})
Pasta: {PASTA_RAW}
========================================

ARQUIVOS ESPERADOS vs ENCONTRADOS
---------------------------------
| # | Produto            | Status |
|---|--------------------|--------|
| 1 | Investimentos      | OK     |
| 2 | XP US              | AUSENTE|
...

RESUMO
------
- Arquivos esperados: 12
- Arquivos encontrados: ___
- Arquivos validos: ___
- Arquivos com problemas: ___

DETALHES POR ARQUIVO
--------------------
### investimentos_{YYYYMM}.xlsx
- Status: OK
- Tamanho: X KB
- Linhas: XXX
- Colunas faltantes: nenhuma

### xp_us_{YYYYMM}.xlsx
- Status: AUSENTE
...

PROXIMOS PASSOS
---------------
1. [Se arquivos ausentes] Solicitar arquivos faltantes a XP
2. [Se arquivos com erro] Verificar/reobter arquivos corrompidos
3. [Se OK] Prosseguir com processamento da Fase 1
```

### 6. Atualizar checklist (opcional)

Se existir `CHECKLIST_{COMPETENCIA}.md` na pasta da competencia, oferecer atualizacao automatica da secao 1.1 (Recebimento dos Arquivos) marcando como `[x]` os arquivos recebidos.
