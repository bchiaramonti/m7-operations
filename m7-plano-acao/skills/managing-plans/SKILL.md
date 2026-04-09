---
name: managing-plans
description: >-
  Gerencia Planos de Acao M7 com CRUD para acoes de melhoria.
  Cobre criacao, atualizacao, conclusao, cancelamento e follow-up.
  Use when the user wants to create, update, complete, cancel, or follow up on action plans.

  <example>
  Context: user wants to register a new improvement action
  user: "quero cadastrar uma melhoria para aumentar volume de consorcios"
  assistant: detects tipo=melhoria, starts guided interview for required fields, creates PA-2026-NNN
  </example>

  <example>
  Context: user wants to complete an action with evidence
  user: "conclui PA-2026-003, a evidencia e o relatorio no SharePoint"
  assistant: detects ID prefix PA-, validates status transition, sets evidencia, percentual=100, data_conclusao=hoje
  </example>

  <example>
  Context: user wants to update an existing action
  user: "atualiza PA-2026-003 para em_andamento, comecei a trabalhar"
  assistant: detects ID prefix PA-, reads plano-de-acao.csv, validates transition, appends comment, rewrites CSV
  </example>
user-invocable: true
---

# Managing Plans

Skill de escrita para o CSV de acoes de melhoria do Plano de Acao (prefixo `PA-`, arquivo `plano-de-acao.csv`).

## Pre-requisitos

Antes de qualquer operacao:

1. Ler [csv-schemas.md](references/csv-schemas.md) para o schema e o **caminho base** do CSV
2. Ler [csv-conventions.md](references/csv-conventions.md) para regras de escrita
3. Confirmar que `plano-de-acao.csv` existe via Glob no caminho base definido em csv-schemas.md

## Deteccao de modo

| Operacao | Modo | Descricao |
|----------|------|-----------|
| `criar` | 1 | Novo registro (melhoria ou sub-acao) |
| `atualizar` | 2 | Modificar campos existentes |
| `concluir` | 3 | Marcar como concluida |
| `cancelar` | 4 | Cancelar com justificativa |
| `followup` | 5 | Agendar proximo follow-up |

Todos os IDs usam prefixo `PA-` e operam em `plano-de-acao.csv`. Tipos validos: `melhoria` e `sub-acao` (com `parent_id`).

---

## Modo 1 — Criar registro

### Passo 1: Carregar schema

Carregar schema de [csv-schemas.md](references/csv-schemas.md).

### Passo 2: Entrevista guiada

Solicitar campos obrigatorios (ver schema). Para sub-acoes (`parent_id`): validar que o parent existe no CSV.

Aplicar defaults automaticamente:
- `data_cadastro` = hoje
- `ultima_atualizacao` = hoje
- `status` = `backlog`
- `percentual` = `0`
- `comentarios` = `[{"data":"{hoje}","autor":"{responsavel}","texto":"Registro criado"}]`

### Passo 3: Protocolo de escrita

Seguir o protocolo completo de [csv-conventions.md](references/csv-conventions.md):

```
1. Ler CSV atual
2. Backup → _Historico/{nome}_ate-{YYYY-MM-DD}.csv
3. Gerar proximo ID (ler CSV para determinar sequencial)
4. Validar campos contra schema
5. Formatar nova linha com double-quoting
6. Reescrever CSV completo via Write tool (header + existentes + nova linha)
7. Reler e confirmar integridade
```

### Passo 4: Confirmar

Reportar ao usuario no formato:

```
Registro criado com sucesso

  ID:        <id-gerado>
  Tipo:      <tipo>
  Titulo:    <titulo>
  Parent:    <parent_id ou "—">
  Status:    <status inicial>
```

---

## Modo 2 — Atualizar registro

### Passo 1: Localizar

Ler CSV correspondente ao prefixo do ID. Exibir estado atual ao usuario.

### Passo 2: Coletar alteracoes

Campos atualizaveis dependem do schema (ver [csv-schemas.md](references/csv-schemas.md)). Validar transicoes de status:

```
backlog → pendente → em_andamento → concluida/cancelada
```

Rejeitar transicoes invalidas (ex: `concluida → pendente`). Informar o usuario sobre o motivo.

### Passo 3: Comentario obrigatorio

Toda atualizacao exige texto de comentario. Formato:
```json
{"data": "{hoje}", "autor": "{responsavel}", "texto": "Descricao da alteracao"}
```

Fazer append ao array JSON existente — nunca substituir.

### Passo 4: Protocolo de escrita

Backup → validar → reescrever CSV completo → confirmar integridade.

---

## Modo 3 — Concluir

Status → `concluida`:

1. `evidencia` e **obrigatoria** — nunca aceitar vazio. Perguntar ao usuario se nao fornecida.
2. `percentual` = `100`
3. `data_conclusao` = hoje
4. Comentario descrevendo a conclusao

---

## Modo 4 — Cancelar

1. `status` = `cancelada`
2. Motivo **obrigatorio** em `comentarios` — nunca aceitar vazio
3. Se tem sub-acoes: perguntar se aplica cancelamento em cascata

---

## Modo 5 — Follow-up

1. Atualizar `data_followup` para proxima data
2. Registrar observacao do follow-up em `comentarios`
3. Sugerir proximo follow-up conforme prioridade:
   - `critica`: +3 dias
   - `alta`: +7 dias
   - `media`: +14 dias
   - `baixa`: +30 dias
4. Usuario pode aceitar sugestao ou informar data diferente

---

## Resumo do protocolo de escrita

Independente do modo, toda operacao de escrita segue:

```
Pre-requisitos → Identificar CSV → Ler CSV → Backup → Modificar → Reescrever → Validar → Confirmar
```

Para detalhes completos de quoting, IDs, JSON e backup, ver [csv-conventions.md](references/csv-conventions.md).
Para schemas e enums, ver [csv-schemas.md](references/csv-schemas.md).
