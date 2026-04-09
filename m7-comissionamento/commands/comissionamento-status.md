---
name: comissionamento-status
description: >-
  Exibe o status atual do processamento de comissionamento.
  Mostra progresso por fase, itens pendentes e proximas acoes.
  Use para verificar o andamento da competencia atual.
argument-hint: [YYYYMM]
allowed-tools: Read, Glob, Grep
---

# Status do Comissionamento

Exibe o progresso do processamento da competencia atual.

## Input

Competencia (opcional): $ARGUMENTS

## Steps

### 1. Identificar competencia

Se $ARGUMENTS informado, usar como competencia (formato YYYYMM).

Se nao informado, detectar automaticamente:
- Buscar pastas `*/??-??/` no workspace atual
- Ordenar por nome (mais recente primeiro)
- Usar a mais recente como competencia ativa

### 2. Localizar o checklist

Buscar `CHECKLIST_{YYYYMM}.md` na pasta da competencia (`YYYY/MM-YY/`).

Se nao encontrado, informar ao usuario e sugerir `/comissionamento-init`.

### 3. Parsear o checklist

Ler o arquivo CHECKLIST e extrair:

- **Fases** (secoes `## `): identificar emoji de status (✅, 🟡, ⬜, ⏭️)
- **Itens** (linhas `- [ ]` e `- [x]`): contar concluidos vs pendentes por fase
- **Informacoes da competencia**: tabela no topo do checklist

### 4. Exibir relatorio de status

```
=================================================
COMISSIONAMENTO — {MES_NOME}/{ANO} ({YYYYMM})
=================================================

PROGRESSO POR FASE
------------------
| Fase | Descricao                         | Status | Progresso   |
|------|-----------------------------------|--------|-------------|
| 0    | Preparacao da Competencia         | ✅     | 5/5 (100%)  |
| 1    | Recebimento e Conversao           | 🟡     | 8/12 (67%)  |
| 2    | Processamento e Correcoes         | ⬜     | 0/5 (0%)    |
| ...  | ...                               | ...    | ...         |

RESUMO
------
- Fases concluidas: X/11
- Itens concluidos: XX/YY
- Proxima acao pendente: [descricao do proximo item - [ ]]

PROXIMOS PASSOS
---------------
1. [primeiro item pendente]
2. [segundo item pendente]
3. [terceiro item pendente]
```

### 5. Verificar CHANGELOG

Ler `CHANGELOG_{YYYYMM}.md` e exibir a ultima entrada registrada (data e descricao).
