# Action Lifecycle — Estados, Operacoes e Transicoes

Documenta as operacoes que esta skill suporta sobre acoes do plano,
seus estados validos e quando cada operacao se aplica.

## Operacoes

| Operacao | Subcomando | Modifica xlsx? | Modifica ClickUp? | Modifica changelog? |
|---|---|---|---|---|
| **init**     | `init.py`              | Cria copia + adiciona col L      | Push inicial (Claude orquestra) | Header inicial |
| **create**   | `actions.py create`    | Append linha + clickup_id vazio  | `clickup_create_task` (Claude)  | Entry `create` |
| **update**   | `actions.py update`    | Edita celula                     | `clickup_update_task` (Claude)  | Entry `update` |
| **delete**   | `actions.py delete`    | Remove linha (com/sem cascade)   | `delete` ou `archive` (Claude)  | Entry `delete` |
| **comment**  | `actions.py comment`   | Nao mexe                         | `clickup_create_task_comment`   | Entry `comment` |
| **followup** | `followup.py`          | Read-only (gera perguntas)       | Read-only                        | Nao escreve direto (cada update do followup gera entry) |
| **sync**     | `sync.py prepare/finalize` | Pode escrever (pull)         | Pode escrever (push)             | Entry `sync` apos finalize |

## Estados de uma acao (status local)

```
        +-------------+
        | not_started |---+
        +-------------+   |
              |           |
              v           v
        +-------------+   +---------+
        | in_progress |<->| blocked |
        +-------------+   +---------+
              |
              v
        +-------------+
        |    done     |   (transicao final; mais updates raros)
        +-------------+
```

**Transicoes legais (status_local):**
- `not_started → in_progress` — start work
- `not_started → blocked` — bloqueado antes de comecar
- `in_progress → blocked` ↔ unblocked
- `in_progress → done` — entrega
- `blocked → in_progress` ou `not_started`
- `done → in_progress` (raro: re-abertura por bug ou retrabalho)

**Status no ClickUp:** mapeado via `status_map` no `.sync-state.json`. Se a List ClickUp tem custom statuses fora do mapping, o sync devolve warning e mantem string ClickUp em `status` local — usuario pode atualizar o mapping para incluir.

## Quando uma operacao e legal

### `init`
- Pre: `1-planning/Cronograma.xlsx` existe; `4-status-report/Cronograma.xlsx` NAO existe (ou usuario passou `--force`)
- Pos: `4-status-report/{Cronograma.xlsx, changelog.md, .sync-state.json}` criados
- Falha: baseline ausente → erro claro pedindo para rodar `building-project-plan`

### `create`
- Pre: `4-status-report/Cronograma.xlsx` existe; `No.` proposto nao existe; parent (se houver) existe
- Pos: linha appended com `clickup_id = ""` ate Claude pushar e gravar via `xlsx_write.py write-clickup-id`
- Caso edge: parent sem `clickup_id` (criado tambem nessa rodada e ainda nao pushado) — Claude precisa pushar parent primeiro, recuperar ID, e so entao pushar filho com `parent_clickup_id`

### `update`
- Pre: row existe (encontrada por `No.`); campo e valido (do enum `CANONICAL_COLUMN_ORDER` exceto `clickup_id`)
- Pos: celula atualizada localmente; se row tem `clickup_id`, Claude pusha mudanca para ClickUp
- Casos especiais: status fora do enum → erro; campo `clickup_id` → erro (use `xlsx_write.py write-clickup-id`)

### `delete`
- Pre: row existe; sem filhos OU `--cascade` passado
- Pos: linha removida (ou linhas, se cascade); Claude apaga ou arquiva no ClickUp conforme `--mode`
- Anti-pattern: deletar linha com filhos sem cascade — bloqueado por seguranca

### `comment`
- Pre: row tem `clickup_id` (sem ID, comentario nao tem onde viver)
- Pos: comentario criado no ClickUp; espelho gravado no `changelog.md`
- Comentarios NAO vao para o xlsx (nao tem coluna)

### `followup`
- Sempre legal (read-only). Detecta:
  - **overdue:** `fim_plan < hoje` AND `status != done`
  - **upcoming:** `hoje <= fim_plan <= hoje + lookahead_days` AND `status != done`
  - **stagnated:** `status == in_progress` AND `due distante > 14 dias` AND `fim_real vazio`
  - **unstarted:** `inicio_plan <= hoje` AND `status == not_started`
- Skip automatico de tipo `Fase` (agregadores) a menos que `--include-fases`

### `sync`
- `prepare` precisa: xlsx live + JSON de tasks remotas (Claude provem via `clickup_filter_tasks`)
- `finalize-init` precisa: xlsx live + push inicial concluido por Claude
- `finalize` precisa: xlsx live (estado pos-sync apos prepare ter sido aplicado)
- Apos `finalize-*`, baselines em `.sync-state.json` refletem o estado consistente local + remote

## Invariantes pos-operacao

Toda operacao deixa o sistema em um destes estados:

1. **Estado consistente:** xlsx + ClickUp + changelog refletem a mesma realidade. Caso esperado.
2. **Sync pendente:** `sync_pending=true` em `.sync-state.json`. Significa que algum push falhou parcialmente. Proxima operacao DEVE comecar com `sync.py prepare` para reconciliar antes de aceitar nova mutacao.
3. **Erro abortado:** nenhuma mudanca aplicada. Caso de validacao falhar antes de qualquer write.

A skill **nunca** deixa o sistema com xlsx parcialmente atualizado e ClickUp nao tocado (ou vice-versa). Em failure modes, ver `failure-modes.md`.
