---
name: managing-action-plan
description: >-
  Gerencia o plano de acao de um projeto M7: criar, atualizar, comentar, listar,
  fazer follow-up proativo de prazos e sincronizar com ClickUp. Mantem o invariante
  de 3 camadas (Cronograma.xlsx local + changelog.md local + ClickUp SSOT) sempre
  consistentes apos cada operacao. Use quando o usuario quer mexer em acoes
  (criar/atualizar/deletar/comentar), perguntar sobre andamento, replanejar
  datas, ou sincronizar com ClickUp.

  <example>
  Context: usuario quer criar uma acao
  user: "Adiciona uma acao 3.6 'Validar handoff com gestor' ate 30/abr, responsavel Bruno"
  assistant: invoca managing-action-plan -> actions.py create; depois orquestra clickup_create_task; depois grava clickup_id e changelog
  </example>

  <example>
  Context: usuario quer review de atrasos
  user: "O que esta atrasado no projeto Playbook de Processos?"
  assistant: invoca managing-action-plan -> followup.py; pergunta 1-a-1 baseado em suggested_questions
  </example>

  <example>
  Context: usuario quer sincronizar
  user: "Sincroniza o cronograma com o ClickUp"
  assistant: invoca managing-action-plan -> sync.py prepare; resolve conflicts via prompts; aplica plan via MCP; sync.py finalize
  </example>
user-invocable: true
---

# Managing Action Plan

Gerencia o ciclo de vida do plano de acao de um projeto M7. Esta skill e o **wrapper conversacional** sobre 9 scripts Python deterministicos + chamadas MCP do ClickUp orquestradas pelo Claude.

**Principio central:** 3 camadas sempre consistentes — `Cronograma.xlsx` (estrutura local), `changelog.md` (auditoria + espelho de comentarios), `ClickUp` (SSOT global). Sincronizacao e regra invariante apos qualquer mutacao, nao um objetivo separado.

## Pre-requisitos

- Plugin `m7-projects` instalado
- Projeto inicializado via `initializing-project` (existe `<projeto>/4-status-report/`)
- Cronograma baseline existe em `<projeto>/1-planning/Cronograma.xlsx` (gerado por `building-project-plan` ou copiado manualmente)
- ClickUp MCP autenticado na sessao Claude (`mcp__claude_ai_ClickUp__*` disponiveis)
- Python 3.10+ com `openpyxl` (`pip3 install openpyxl`)

## Estado da arte (3 camadas)

```
<projeto>/
├── CLAUDE.md                                # Mantem secao "## Plano de Acao — Configuracao" (responsaveis mapping, status_map)
├── 1-planning/
│   └── Cronograma.xlsx                      # BASELINE imutavel (gerada por building-project-plan)
└── 4-status-report/
    ├── Cronograma.xlsx                      # LIVE (esta skill mantem)
    ├── changelog.md                         # LIVE append-only (esta skill mantem)
    ├── .sync-state.json                     # Sidecar com baselines + last_sync_hash
    └── YYYY-MM-DD/                          # Snapshots de cada reporte (outra skill: generating-status-materials)
```

ClickUp e o **SSOT global**: status, comentarios, datas oficiais. xlsx e estrutura; changelog e historico; ClickUp e a verdade operacional.

## Quando invocar cada operacao

| Pedido do usuario (em portugues) | Operacao | Script |
|---|---|---|
| "Inicia o plano de acao", "Coloca esse cronograma no ClickUp" | init | `init.py` |
| "Adiciona/cria uma acao" | create | `actions.py create` |
| "Muda o status de X", "Move a data de Y" | update | `actions.py update` |
| "Apaga/cancela essa acao" | delete | `actions.py delete` |
| "Comenta em X que..." | comment | `actions.py comment` |
| "O que esta atrasado", "O que precisa de atencao" | followup | `followup.py` |
| "Sincroniza com o ClickUp" | sync | `sync.py prepare` |

Pode haver mistura — "muda o status de X e me mostra o que mais esta atrasado" = `update` + `followup`.

## Workflows detalhados

### `init` — primeira rodada

```
Claude:
  1. Verifica `<proj>/1-planning/Cronograma.xlsx` existe (se nao: erro pedindo building-project-plan)
  2. Verifica `<proj>/4-status-report/Cronograma.xlsx` NAO existe (se existe: pergunta confirmacao para --force)
  3. Pergunta o List ID no ClickUp:
     - Se usuario nao tem: orienta criar via UI ClickUp ou via outro MCP tool (workspace_hierarchy + criar list — fora do escopo desta skill)
     - Se tem: pega o ID
  4. Chama: python3 init.py --project-dir <proj> --clickup-list-id <id> --project-name <nome>
  5. init.py output:
     - Cria <proj>/4-status-report/Cronograma.xlsx (copia + col ClickUp ID)
     - Cria <proj>/4-status-report/changelog.md (header)
     - Cria <proj>/4-status-report/.sync-state.json (clickup_list_id + status_map)
     - Emite push_plan ordenado topologicamente
  6. Claude itera push_plan (parents antes de children):
     a. Se row tem parent_no, busca clickup_id do parent ja pushado (do plan)
     b. Resolve responsavel via secao "## Plano de Acao — Configuracao" do CLAUDE.md (assignees mapping)
     c. Se mapping nao tem o nome, tenta clickup_get_workspace_members + oferece adicionar mapping
     d. Chama clickup_create_task com payload (+ assignees + parent se houver)
     e. Recebe clickup_id retornado
     f. Chama: python3 xlsx_write.py write-clickup-id --file ... --row-index N --clickup-id ID
     g. Chama: python3 changelog_append.py --op create --summary "..." --details-json ...
  7. Apos todos os pushes:
     a. Chama: python3 sync.py finalize-init --file ...   # grava baselines em .sync-state.json
     b. Atualiza CLAUDE.md adicionando secao "## Plano de Acao — Configuracao" se nao existir
     c. Reporta ao usuario: "N acoes sincronizadas com ClickUp List <id>"
```

**Failure modes durante push:** ver [`failure-modes.md`](references/failure-modes.md) — partial push deixa `sync_pending=true`.

### `create` — nova acao

```
Claude:
  1. Coleta inputs: no, tipo, etapa (titulo), responsavel, inicio, fim, status (default not_started), entregavel
  2. Chama: python3 actions.py create --file <live.xlsx> --no <X> --tipo <T> --etapa "..." [...]
  3. actions.py:
     a. Valida no nao existe e parent existe (se aplica)
     b. Append linha local (clickup_id="")
     c. Salva xlsx
     d. Emite payload p/ ClickUp + parent_clickup_id (se parent ja sincronizado)
  4. Claude:
     a. Resolve responsavel -> assignee_id via mapping CLAUDE.md
     b. Chama clickup_create_task com payload + assignees + parent (se houver)
     c. Recebe clickup_id
     d. Chama xlsx_write.py write-clickup-id ...
     e. Chama changelog_append.py --op create ...
  5. Reporta: "Criada No. X — clickup_id Y"
```

### `update` — alterar campo

```
Claude:
  1. Identifica row (via "No. X" ou descricao do usuario)
  2. Identifica field + novo valor
  3. Chama: python3 actions.py update --file <live.xlsx> --no X --field <F> --value <V>
  4. actions.py:
     a. Valida row existe + field/value validos
     b. Aplica local (xlsx)
     c. Emite push_payload se row tem clickup_id
  5. Claude (se push_payload nao null):
     a. Mapeia field local -> field ClickUp (etapa->name, status->status mapeado, etc.)
     b. Chama clickup_update_task com payload
  6. Chama changelog_append.py --op update --summary "..."
  7. Reporta: "No. X <field>: <old> -> <new>"
```

### `delete` — remover acao

```
Claude:
  1. Identifica row + pergunta usuario:
     - Mode: archive (status=done no ClickUp) ou delete (apaga)
     - Se tem filhos: cascade ou cancelar
  2. Chama: python3 actions.py delete --file <live> --no X --mode <M> [--cascade]
  3. actions.py: remove linha(s) local + emite IDs ClickUp afetados
  4. Claude: para cada ID, chama clickup_delete_task ou clickup_update_task(status=done)
  5. Chama changelog_append.py --op delete
  6. Reporta sumario
```

### `comment` — adicionar comentario

```
Claude:
  1. Identifica row (precisa ter clickup_id; senao erro: "comente apos sincronizar")
  2. Coleta texto
  3. Chama: python3 actions.py comment --no X --clickup-id ID --text "..."
  4. actions.py emite payload (no xlsx mexer)
  5. Claude: chama clickup_create_task_comment com payload
  6. Chama changelog_append.py --op comment --comment "<texto>"
  7. Reporta: "Comentario adicionado em No. X"
```

### `followup` — review proativo

```
Claude:
  1. Pergunta lookahead se nao implicito (default 3 dias; para WBR semanal usa 7-14)
  2. Chama: python3 followup.py --file <live> --lookahead-days <N>
  3. followup.py devolve {categories, totals, suggested_questions}
  4. Claude:
     a. Mostra resumo: "N atrasadas, M proximas, K estagnadas, J nao iniciadas"
     b. Pergunta "Quer ir uma a uma? (s/n/depois)"
     c. Se sim: itera suggested_questions, comecando por overdue
     d. Cada resposta vira: actions.py update / actions.py comment / skip
     e. Apos cada acao, sincronizacao automatica (push para ClickUp + changelog entry)
  5. Sumariza decisoes ao final
```

Ver [`followup-heuristics.md`](references/followup-heuristics.md) para detalhes das categorias e formulacoes.

### `sync` — reconciliar manualmente

```
Claude:
  1. Pergunta razao se nao implicita (debug, suspeita de divergencia, pre-WBR)
  2. Chama: clickup_filter_tasks(list_id=<id>) -> tasks remotas
  3. Salva tasks remotas como JSON em /tmp/remote_<timestamp>.json
  4. Chama: python3 sync.py prepare --file <live> --remote-json /tmp/remote_*.json
  5. sync.py emite plan: {push_creates, push_updates, push_deletes, pull_creates, pull_updates, conflicts, orphans, unchanged_count}
  6. Claude apresenta sumario do plano
  7. Para cada conflict: prompt side-by-side com sugestao LLM (ver failure-modes.md)
  8. Para cada orphan: pergunta (recriar, dropar mapping, deletar local)
  9. Aplica plano:
     - push_creates: clickup_create_task + xlsx_write.py write-clickup-id
     - push_updates: clickup_update_task
     - push_deletes: clickup_delete_task ou archive (perguntar)
     - pull_creates: xlsx_write.py append-row + write-clickup-id (id ja vem do remote)
     - pull_updates: xlsx_write.py bulk-cells
  10. Chama: python3 sync.py finalize --file <live>   # regrava baselines
  11. Chama changelog_append.py --op sync --summary "..." --details-json <plan_summary>
  12. Reporta sumario ao usuario
```

## Mapping de responsaveis em CLAUDE.md

A skill mantem uma secao no `CLAUDE.md` do projeto:

```markdown
## Plano de Acao — Configuracao

clickup_list_id: 901xxxxxxx
clickup_space_id: 90xxxxxxx
status_map:
  not_started: "to do"
  in_progress: "in progress"
  blocked: "blocked"
  done: "complete"
responsaveis:
  Bruno: "user_id_xyz123"
  Maria: "user_id_abc456"
```

Quando precisar resolver "Bruno" -> assignee_id em um push, le essa secao. Se o nome nao esta no mapping:
1. Tenta `clickup_get_workspace_members` para encontrar o user
2. Se encontrar, pergunta "Adicionar mapping `<nome>: <id>` no CLAUDE.md?"
3. Se sim, atualiza a secao do CLAUDE.md

Esses dados tambem ficam em `.sync-state.json` (campo `clickup_list_id` e `status_map`) para nao precisar reler CLAUDE.md em cada operacao.

## Anti-patterns a evitar

- **Mexer no xlsx baseline (`1-planning/`):** essa copia e imutavel. Toda mutacao vai no live (`4-status-report/`).
- **Deletar `.sync-state.json` manualmente:** quebra baselines, proximo sync vai gerar muitos falsos conflicts.
- **Editar entries antigas no `changelog.md`:** append-only por contrato (ver [changelog-format.md](references/changelog-format.md)). Para corrigir um valor errado, gere um update novo.
- **Passar `--timestamp` no fluxo normal do `changelog_append.py`:** o default (`dt.datetime.now()`) e obrigatorio para operacoes em tempo real; nunca improvisar ou reusar timestamps. `--timestamp` existe apenas para replay de sync que falhou meio-caminho.
- **Colocar proximos passos, planos ou TODOs em entries do changelog:** o changelog registra somente o que foi feito. Planos futuros vao para `BRIEFING.md`, `PLANEJAMENTO.md` ou ClickUp. Nunca aceitar summary ou details contendo "vai fazer X", "pendente Y", "proximo passo Z".
- **Reordenar entries manualmente:** `changelog_append.py` insere sempre no topo (ordem decrescente). Se o arquivo aparecer fora de ordem, investigar o script antes de editar a mao.
- **Skip do `sync.py finalize` apos push:** baselines nao atualizam, proximo sync faz tudo de novo.
- **Push de campos nao-mapeados (`no`, `tipo`):** sao schema local. Sync ja filtra automaticamente.
- **Aplicar update sem confirmar quando usuario fala data ambigua:** sempre confirmar valor exato antes de gravar.

## Validacoes pos-operacao

Apos qualquer operacao, verifique implicitamente:
- Xlsx parseia sem errors (so warnings ok): `python3 parse_cronograma.py --file <live> --validate-only`
- `.sync-state.json` valido (json + tem clickup_list_id)
- Changelog tem entry da operacao recem-feita

Se qualquer item falhar, **avisar o usuario** — nao declarar sucesso silencioso.

## Additional resources

- [`cronograma-schema.md`](references/cronograma-schema.md) — Layout exato do xlsx, colunas, hierarquia, datas
- [`action-lifecycle.md`](references/action-lifecycle.md) — Operacoes, estados, transicoes
- [`sync-algorithm.md`](references/sync-algorithm.md) — Three-way diff pseudocode
- [`field-resolution-rules.md`](references/field-resolution-rules.md) — Tabela completa com racional por campo
- [`followup-heuristics.md`](references/followup-heuristics.md) — Regras + formulacoes de pergunta
- [`failure-modes.md`](references/failure-modes.md) — MCP offline, partial push, orphans, recovery
- [`changelog-format.md`](references/changelog-format.md) — Formato exato dos entries
- [`templates/CHANGELOG.tmpl.md`](templates/CHANGELOG.tmpl.md) — Header inicial do changelog

## Scripts (referencia rapida)

| Script | Pure? | Funcao |
|---|---|---|
| `_lib.py` | sim | Modulo compartilhado (datas, hash, xlsx IO, sync state) — nao invocar diretamente |
| `parse_cronograma.py` | sim | Parser xlsx → JSON canonico |
| `hash_row.py` | sim | Hash deterministico (debug + sync) |
| `changelog_append.py` | sim | Append entries em changelog.md |
| `xlsx_write.py` | sim | Mutacoes no xlsx (write-clickup-id, write-cell, append-row, delete-row, bulk-cells) |
| `init.py` | sim (local) | First-run setup + emite push plan |
| `actions.py` | sim (local) | CRUD subcommands (create/update/delete/comment) |
| `followup.py` | sim | Detecta acoes que precisam atencao |
| `sync.py` | sim (local) | Three-way diff (prepare) + baseline refresh (finalize) |

"Pure" = nao chama MCP. As 9 scripts sao 100% Python local. Toda chamada ClickUp e responsabilidade do Claude (LLM) baseada nos payloads emitidos.
