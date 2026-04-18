# Failure Modes — Deteccao e Recuperacao

Catalogo de falhas conhecidas e como a skill (combinacao de scripts +
Claude orquestrador) deve responder. Carregue quando algo der errado
para nao improvisar.

## Indice

1. [ClickUp MCP offline](#clickup-mcp-offline)
2. [Partial push (sucesso parcial)](#partial-push-sucesso-parcial)
3. [Orphan clickup_id](#orphan-clickup_id)
4. [Conflito BOTH_CHANGED em campo conflict](#conflito-both_changed-em-campo-conflict)
5. [Status custom fora do status_map](#status-custom-fora-do-status_map)
6. [Assignee nao resolve](#assignee-nao-resolve)
7. [Xlsx corrompido / parse falha](#xlsx-corrompido--parse-falha)
8. [Sync state corrompido](#sync-state-corrompido)
9. [Hierarquia inconsistente](#hierarquia-inconsistente)

---

## ClickUp MCP offline

**Sintoma:** Claude tenta `clickup_filter_tasks` (ou qualquer tool MCP) e recebe erro de conexao / autenticacao / 5xx.

**Resposta:**
1. **NAO aplicar mudancas locais ainda.** Se a operacao era um `update`/`create` que ja foi escrito no xlsx mas nao pushado, marcar `sync_pending=true` em `.sync-state.json`.
2. Adicionar entry de `error` no `changelog.md` com detalhe ("MCP unreachable: <error>")
3. Avisar usuario: "ClickUp indisponivel. As mudancas locais foram preservadas; quando ClickUp voltar, rode `sync.py prepare` para reconciliar."

**Recovery quando MCP volta:**
- `sync.py prepare` detecta `sync_pending=true` (ou simplesmente ve mudancas locais sem reflexo no remote)
- Plano emite push_updates/push_creates correspondentes
- Apos Claude aplicar, `sync.py finalize` desmarca `sync_pending`

## Partial push (sucesso parcial)

**Sintoma:** durante init.py first-push (262 creates) ou um sync grande, Claude pushou N tasks com sucesso, mas a (N+1)-esima falhou (timeout, validation error, etc.).

**Resposta:**
1. **Preservar IDs ja gravados.** Cada `clickup_create_task` ok deve ter sido seguido por `xlsx_write.py write-clickup-id`. Nao desfazer esses IDs.
2. Marcar `sync_pending=true`.
3. Adicionar entry `error` em changelog: "partial push N/M ok; restantes pending".
4. Avisar usuario: "Pushei N de M com sucesso. Pode tentar continuar agora ou depois."

**Recovery:**
- Re-rodar a operacao (init.py + push iterativo, ou sync.py prepare); script detecta linhas sem clickup_id e pusha os restantes
- Ordem topologica preservada: parents ja com ID, filhos pendentes pegam o `parent_clickup_id` correto

## Orphan clickup_id

**Sintoma:** linha local tem `clickup_id` que nao aparece em `clickup_filter_tasks`. Provavel causa: alguem deletou a task no ClickUp diretamente.

**Resposta:** entra em `plan.orphans` no output do `sync.py prepare`. Claude pergunta:
- (a) **Recriar no ClickUp** com o conteudo local — chama `clickup_create_task`, grava novo clickup_id na linha (sobrescreve o antigo). Log: "orphan recreated".
- (b) **Remover mapping** — limpa o `clickup_id` local; linha vira `LOCAL_ONLY_NEW` no proximo sync (sera pushada como nova). Log: "orphan dropped".
- (c) **Deletar linha local** — remove a linha do xlsx. Log: "orphan removed locally".

A skill **nao decide sozinha** — sempre pergunta.

## Conflito BOTH_CHANGED em campo conflict

**Sintoma:** `plan.conflicts` nao vazio. Tipicamente em `etapa` ou `entregavel`.

**Resposta:** Claude apresenta diff side-by-side:

```
No. 1.1 (clickup_id cu_002):
  Campo: etapa
  Local:    "Elaborar Termo de Abertura do Projeto (TAP)"
  Remote:   "Elaborar TAP — versao curta"
  Baseline: "Elaborar Termo de Abertura do Projeto (TAP)"

  Sugestao do LLM (merge): "Elaborar Termo de Abertura do Projeto (TAP) — versao curta"

  Escolha: (1) local / (2) remote / (3) sugestao / (4) editar / (5) skip
```

Apos escolha:
- Atualiza valor no plan.resolutions
- Adiciona ao push_fields ou pull_fields conforme winner
- Continua o sync

Logar a decisao em changelog: "conflict T### etapa: chose <local|remote|merge>".

## Status custom fora do status_map

**Sintoma:** `clickup_filter_tasks` retorna task com status que nao tem chave inversa no `status_map` (ex: "in review", mapping so tem to do/in progress/blocked/complete).

**Resposta:**
1. `remote_to_canonical` devolve `status=""` (vazio)
2. Sync trata como "remote nao tem status mapeado"
3. **Warning** no plan: "Task cu_xxx tem status remote 'in review' fora do status_map; preservado vazio em local"
4. Sugerir ao usuario adicionar a chave: editar `.sync-state.json` `status_map` → `{"in_review": "in review"}`

## Assignee nao resolve

**Sintoma:** linha local tem `responsavel: "Joao"` mas mapping em CLAUDE.md nao tem entry para "Joao". Push de create/update precisa de `assignees: [user_id]`.

**Resposta:**
1. Tentar `clickup_resolve_assignees` ou `clickup_get_workspace_members` para encontrar Joao por nome/email
2. Se encontrar: oferecer ao usuario "Adicionar mapping `Joao: <id>` ao CLAUDE.md?" — se sim, atualiza
3. Se nao encontrar: pushar a task **sem assignees** (vai pra ClickUp com unassigned), warning no changelog: "Joao nao resolve; task cu_xxx criada unassigned"
4. Usuario pode corrigir depois e re-sync

## Xlsx corrompido / parse falha

**Sintoma:** `parse_cronograma.py` ou `_lib.CronogramaXLSX.load()` levanta excecao (zipfile error, invalid format, etc.)

**Resposta:**
1. **Abort imediato.** Nenhuma operacao tenta consertar o xlsx automaticamente.
2. Avisar usuario com erro exato + path do arquivo
3. Sugerir: (a) restaurar de backup do OneDrive/Time Machine, (b) recopiar baseline (`init.py --force`)
4. NAO escrever nada no changelog (o changelog provavelmente esta ok, mas nao queremos misturar entries com xlsx em estado indefinido)

## Sync state corrompido

**Sintoma:** `.sync-state.json` nao parseia (json invalido, campos faltando).

**Resposta:**
1. `_lib.read_sync_state` ja faz fallback para defaults se json invalido — entao a leitura nao crasha
2. Mas isso significa que **baselines foram perdidos** — proximo sync vai tratar tudo como "primeira sync"
3. Resultado: muitas linhas viram BOTH_CHANGED quando na verdade so mudaram um lado. Plan vai ter muitos conflicts falsos
4. Acao recomendada: rodar `sync.py prepare` e checar — se plan tiver conflicts em campos identicos local/remote, e o sintoma. Resposta: rodar `sync.py finalize` (sem prepare) para regravar baselines do estado atual como "verdade de momento"; perde-se historia mas o sync volta a funcionar

## Hierarquia inconsistente

**Sintoma:** parser warning "No. X tem parent Y (Etapa) fora de Acao" — usuario tem hierarquia bagunçada no xlsx.

**Resposta:**
1. Sync **continua funcionando** (warning, nao error)
2. No push para ClickUp, a hierarquia segue o `parent_no` do xlsx — ClickUp aceita qualquer aninhamento de subtask
3. Visualmente no ClickUp pode ficar estranho (Etapa filha de Etapa, sem Acao no meio), mas funcionalmente OK
4. Se usuario quer corrigir: editar No. no xlsx, sync detecta como hash mudado → push update

## Quando NAO recuperar automaticamente

A skill prefere abortar e pedir ajuda do que adivinhar. Em particular:
- Nunca apaga linhas locais sem confirmacao
- Nunca apaga tasks remotas sem confirmacao
- Nunca sobrescreve `clickup_id` ja preenchido sem confirmacao
- Nunca edita o `Cronograma.xlsx` baseline em `1-planning/`

Erro acidental >> retrabalho — pequenas pausas para confirmar valem mais do que automacao agressiva.
