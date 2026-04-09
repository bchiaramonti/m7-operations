# CSV Schemas — Planos de Acao M7

Schema do CSV de acoes de melhoria que alimenta o dashboard de gestao. Referencia para leitura e validacao.

**Caminho base:**
```
/Users/bchiaramonti/Library/CloudStorage/OneDrive-MULTI7CAPITALCONSULTORIALTDA/
  desempenho/02-Controle/Planos-de-Acao/
```

**Backup:**
```
{caminho_base}/_Historico/
```

---

## Indice

- [1. plano-de-acao.csv (Melhorias)](#1-plano-de-acacsv-melhorias)
- [2. Enums compartilhados](#2-enums-compartilhados)
- [3. Convencoes CSV](#3-convencoes-csv)

---

## 1. plano-de-acao.csv (Melhorias)

24 colunas. Prefixo de ID: `PA-`.

| # | Coluna | Tipo | Obrigatorio | Descricao |
|---|--------|------|:-----------:|-----------|
| 1 | `id` | string | sim | `PA-{YYYY}-{NNN}` |
| 2 | `parent_id` | string | nao | ID da acao pai (sub-acoes) |
| 3 | `data_cadastro` | date | sim | `YYYY-MM-DD` |
| 4 | `data_inicio` | date | sim | `YYYY-MM-DD` |
| 5 | `origem` | enum | sim | Ver [Enums](#origens) |
| 6 | `origem_detalhe` | string | sim | Descricao livre da origem |
| 7 | `indicador_impactado` | string | nao | Codigo(s) da Biblioteca de Indicadores |
| 8 | `vertical` | enum | sim | Ver [Enums](#verticais) |
| 9 | `titulo` | string | sim | Titulo curto da acao |
| 10 | `descricao` | string | sim | Descricao detalhada |
| 11 | `responsavel` | string | sim | Nome completo |
| 12 | `solicitante` | string | sim | Quem solicitou |
| 13 | `prioridade` | enum | sim | `critica`, `alta`, `media`, `baixa` |
| 14 | `data_limite` | date | sim | `YYYY-MM-DD` — prazo final |
| 15 | `data_followup` | date | nao | `YYYY-MM-DD` — proximo followup |
| 16 | `status` | enum | sim | `backlog`, `pendente`, `em_andamento`, `concluida`, `cancelada` |
| 17 | `percentual` | int | sim | 0-100 |
| 18 | `data_conclusao` | date | nao | `YYYY-MM-DD` (preenchida ao concluir) |
| 19 | `evidencia` | string | nao | Obrigatoria ao concluir |
| 20 | `observacoes` | string | nao | Notas livres |
| 21 | `volume` | string | nao | Volume impactado |
| 22 | `receita` | string | nao | `R$ NNN` ou `R$ NNk/mes` |
| 23 | `comentarios` | JSON | sim | Array de `{"data","autor","texto"}` |
| 24 | `ultima_atualizacao` | date | sim | `YYYY-MM-DD` |

### Status derivado (runtime)

```
atrasada = data_limite < hoje AND status IN (pendente, em_andamento)
```

NUNCA armazenar `atrasada` como status no CSV.

---

## 2. Enums compartilhados

### Origens

`indicador`, `ritual`, `auditoria`, `cliente`, `regulatorio`, `oportunidade`, `preventiva`

### Verticais

`investimentos`, `consorcios`, `seguros`, `cambio`, `credito`, `corporativo`, `tecnologia`, `compliance`

### Prioridades

`critica`, `alta`, `media`, `baixa`

---

## 3. Convencoes CSV

### Quoting
- Todos os campos entre aspas duplas (`"valor"`)
- Aspas internas escapadas como `""` (CSV padrao)
- JSON embutido usa `""` para aspas internas: `"[{""data"":""2026-01-01""}]"`

### Datas
- Formato: `YYYY-MM-DD`
- Campos vazios: `""` (nunca `null` ou `N/A`)

### Backup pre-escrita
- Antes de qualquer escrita, copiar CSV para `_Historico/{nome}_ate-{YYYY-MM-DD}.csv`
- Manter backups — nunca apagar

### Escrita
- NUNCA usar Edit tool em CSV — reescrever completo via Write tool
- Verificar integridade apos escrita (reler e contar linhas)
