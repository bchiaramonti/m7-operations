# Field Resolution Rules

Tabela completa com regra de resolucao por campo no caso `BOTH_CHANGED`
do three-way diff. Carregue para entender por que um campo especifico
foi resolvido de uma forma e nao de outra.

## Indice

1. [Tabela de regras](#tabela-de-regras)
2. [Justificativa por campo](#justificativa-por-campo)
3. [Aplicacao em LOCAL_ONLY e REMOTE_ONLY](#aplicacao-em-local_only-e-remote_only)
4. [Quando o usuario quer override](#quando-o-usuario-quer-override)
5. [Mapping campo local ↔ campo ClickUp](#mapping-campo-local--campo-clickup)

---

## Tabela de regras

`FIELD_RULES` em [`sync.py`](../scripts/sync.py):

| Campo local | Regra `BOTH_CHANGED` | Implementada em |
|---|---|---|
| `no` | N/A (local-only schema) | nao vai pro push |
| `tipo` | N/A (local-only schema) | nao vai pro push |
| `etapa` (name) | **conflict** — prompt + LLM sugere merge | `cls['conflicts']` |
| `entregavel` (description) | **conflict** — prompt + LLM sugere merge | idem |
| `status` | **remote-wins** (silent log) | `pull_fields[status]` |
| `inicio_plan` (start_date) | **local-wins** | `push_fields[inicio_plan]` |
| `fim_plan` (due_date) | **local-wins** | idem |
| `inicio_real` (date_started) | **remote-wins** | `pull_fields[inicio_real]` |
| `fim_real` (date_done) | **remote-wins** | idem |
| `responsavel` (assignees) | **remote-wins** | `pull_fields[responsavel]` |

## Justificativa por campo

### `etapa` / `entregavel` → conflict
Sao **campos editorais**: textos que humanos escrevem com intencao.
Merge automatico pode descartar nuance importante. Quando ambos lados
editam, o LLM apresenta diff side-by-side e sugere uma sintese; usuario
escolhe (manter local, manter remote, aceitar sugestao, ou editar a mao).

### `status` → remote-wins
ClickUp e o **SSOT operacional**. Status muda quando o assessor ou
gestor da acao mexe no card — o local nao tem como saber que isso
aconteceu sem pull. Se local tambem mudou (ex: usuario digitou no
xlsx em vez de mexer no ClickUp), assumimos que a versao do ClickUp
e mais confiavel porque foi feita no proprio sistema operacional.
Log silencioso no changelog para auditoria.

### `inicio_plan` / `fim_plan` → local-wins
Datas planejadas sao **decisoes de planejamento**. Tipicamente mudam
no xlsx quando o gestor reagenda algo. Se ClickUp mudou tambem
(provavel: alguem moveu a data no proprio card), mas local mudou
"depois" (porque o gestor reabriu o xlsx), local-wins reflete a
decisao mais recente do gestor formal.

### `inicio_real` / `fim_real` → remote-wins
Datas reais sao **fatos operacionais**. Quem trabalhou na acao
registra inicio/fim no card ClickUp (com botao). Local quase nunca
deveria mudar isso manualmente; se mudar, e provavel que tenha sido
estimativa. Verdade operacional vence.

### `responsavel` → remote-wins
Quando alguem reassigna o task no ClickUp, e a decisao operacional.
O xlsx pode ter o nome antigo. Se ambos mudaram, ClickUp vence
(decisao mais proxima do trabalho real).

## Aplicacao em LOCAL_ONLY e REMOTE_ONLY

Quando so um lado mudou, **nao ha conflito** — apenas propaga:

- `LOCAL_ONLY_CHANGED` → push para ClickUp (campos com mapeamento)
- `REMOTE_ONLY_CHANGED` → pull para xlsx (todos os campos)

Field rules so aplicam quando ambos os lados mudaram em relacao ao baseline.

## Quando o usuario quer override

A skill nao expoe override de regra automatico — toda mudanca segue
a tabela acima. Se o usuario quer comportamento diferente (ex:
"nessa rodada, local-wins para tudo"), a forma e:

1. Editar manualmente os valores no xlsx **depois** do `prepare`
2. Aplicar `xlsx_write.py` para escrever o valor desejado
3. Rodar `prepare` de novo para gerar plano novo

Ou (drastico): alterar `FIELD_RULES` em `sync.py` localmente e
rodar — mas isso nao e suportado e pode quebrar invariantes.

## Mapping campo local ↔ campo ClickUp

`LOCAL_TO_CU_FIELD` em [`sync.py`](../scripts/sync.py):

| Campo local | Campo ClickUp (no payload) |
|---|---|
| `etapa` | `name` |
| `entregavel` | `description` |
| `status` | `status` (mapeado via `status_map`) |
| `inicio_plan` | `start_date` (ISO date) |
| `fim_plan` | `due_date` (ISO date) |
| `responsavel` | `assignees` (array de IDs — Claude resolve nome → ID via mapping em CLAUDE.md) |
| `inicio_real` | `date_started` |
| `fim_real` | `date_done` |

Campos NAO mapeados (`no`, `tipo`, `clickup_id`) nunca entram em
push payload. Eles existem apenas na estrutura local. Se voce
adicionar campos novos, atualize `LOCAL_TO_CU_FIELD` para que sejam
considerados em push.
