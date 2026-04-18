# Changelog Format

Formato exato das entries em `4-status-report/changelog.md`. Carregue
quando precisar gerar entries customizados ou debugar entries existentes.

## Estrutura geral do arquivo

```markdown
# Changelog — Plano de Acao — <Project Name>

> Registro cronologico (reverse, mais novo no topo) de todas as operacoes
> sobre o plano de acao. Mantido automaticamente por `managing-action-plan`.
> Append-only: nunca editar entries existentes manualmente.

---
## <timestamp> — <op> — <summary>           ← entry mais nova

**Operacao:** <op>
**Timestamp:** <timestamp>

[opcional: **Comentario:** com bloco quote]
[opcional: **Detalhes:** com bloco JSON]

---
## <timestamp anterior> — <op> — <summary>  ← entry anterior
...
---
```

Header (linhas 1-6) e estatico. Entries sao inseridas IMEDIATAMENTE
apos o primeiro `---` (linha 6) — ordem reverse-chronological natural.

## Tipos de entry (`--op`)

| Op | Quando | Detalhes tipicos |
|---|---|---|
| `init` | Primeira inicializacao do plano | rows_baselined, clickup_list_id |
| `create` | Nova acao criada | clickup_id, no, status, due |
| `update` | Campo de acao alterado | clickup_id, field, old_value, new_value |
| `delete` | Acao(es) removida(s) | clickup_ids, mode (delete/archive), cascade |
| `comment` | Comentario adicionado | clickup_id, no, comment text (em block quote) |
| `sync` | Sync explicito ou apos prepare+apply | summary do plan (push/pull counts), conflicts resolved |
| `error` | Falha registrada | error message, context, sync_pending state |

## Exemplo: entry `create`

```markdown
## 2026-04-18T14:05:00 — create — No. 3.6 'Nova ação teste' criado

**Operacao:** create
**Timestamp:** 2026-04-18T14:05:00

**Detalhes:**

```json
{
  "clickup_id": "86abc123",
  "no": "3.6",
  "status": "not_started",
  "due": "2026-04-30",
  "responsavel": "Bruno"
}
```

---
```

## Exemplo: entry `comment` (com texto em quote block)

```markdown
## 2026-04-18T14:10:00 — comment — Comentario em No. 1.1.1

**Operacao:** comment
**Timestamp:** 2026-04-18T14:10:00

**Comentario:**

> @bruno revisei, OK p/ seguir
> tudo certo

---
```

Cada linha do comentario vira `> linha` (markdown blockquote). Linhas em branco viram `>`.

## Exemplo: entry `sync` com conflito resolvido

```markdown
## 2026-04-18T15:30:00 — sync — 5 mudancas aplicadas, 1 conflito resolvido

**Operacao:** sync
**Timestamp:** 2026-04-18T15:30:00

**Detalhes:**

```json
{
  "push_updates": 3,
  "pull_updates": 2,
  "conflicts_resolved": [
    {
      "no": "1.1",
      "field": "etapa",
      "chose": "merge",
      "value": "Elaborar TAP — versao final"
    }
  ]
}
```

---
```

## Geracao via CLI

```bash
python3 changelog_append.py \
    --file 4-status-report/changelog.md \
    --op update \
    --summary "No. 1.1.1 status: not_started -> in_progress" \
    --details-json '{"clickup_id":"86abc","field":"status","old":"not_started","new":"in_progress"}' \
    --timestamp "2026-04-18T14:32:11"
```

- `--init` cria o changelog com header se nao existir (use no `init.py` apenas)
- `--timestamp` opcional (default: agora). Util quando reproduzindo um sync apos delay.
- `--project-name` so e usado em conjunto com `--init` para customizar o header.

## Espelho de comentarios do ClickUp

Comentarios sao a unica feature ClickUp-only que tem espelho local
(via changelog). Workflow:

1. Sync detecta novos comentarios via `clickup_get_task_comments` (Claude faz)
2. Para cada novo comentario, gera entry `comment` no changelog
3. Texto do comentario vai no campo `--comment`, formatado como blockquote

Comentarios **nao** geram modificacao no xlsx. As 3 camadas:
- **xlsx:** estrutura
- **changelog:** auditoria + espelho de comentarios
- **ClickUp:** SSOT de tudo, incluindo origem dos comentarios

## Invariantes

- **Append-only:** nunca editar ou deletar entries existentes. Para corrigir um valor errado, gere entry `update` com a correcao
- **Reverse-chronological:** entries mais novas no topo, sempre
- **Timestamp ISO 8601 sem milissegundos:** `YYYY-MM-DDTHH:MM:SS`
- **Auto-trim history em sync_state:** o `history` em `.sync-state.json` mantem apenas 20 entries; o changelog **nunca** e podado

## Tamanho esperado

Para um projeto medio (~250 acoes, sync semanal por 6 meses):
- ~50-100 entries de operacoes ad-hoc
- ~24 entries de sync semanal
- ~20-50 entries de comentarios espelhados
- **Total estimado:** 100-300 entries / ~5000-15000 linhas / ~150-500 KB

Changelog crescendo muito alem disso (>1MB) sugere uso fora do esperado — vale auditar.
