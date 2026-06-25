# Schema ClickUp do Plano de Acao (substitui csv-schema.md)

> **Vigencia: 2026-04-30 em diante**. Este documento substitui o legado `csv-schema.md`.
> SoT do Plano de Acao migrou para a lista ClickUp `pa-resultado` (id `901326795742`).
> Toda escrita acontece via **ClickUp MCP** (`mcp__claude_ai_ClickUp__*`).

Referencia canonica usada pela skill `recording-decisions` e pelo agent `decision-recorder` para criar e atualizar tasks no ClickUp.

## Sumário

1. [Identificacao da lista](#1-identificacao-da-lista)
2. [Custom fields canonicos (IDs fixos)](#2-custom-fields-canonicos-ids-fixos)
3. [Mapeamento Ata ↔ Payload `clickup_create_task`](#3-mapeamento-ata--payload-clickup_create_task)
4. [Payload exemplo (`clickup_create_task`)](#4-payload-exemplo-clickup_create_task)
5. [Update de tasks existentes](#5-update-de-tasks-existentes)
6. [Verificacao de duplicatas](#6-verificacao-de-duplicatas)
7. [URLs de tasks (para a ata HTML)](#7-urls-de-tasks-para-a-ata-html)
8. [Erros e fallbacks](#8-erros-e-fallbacks)
9. [Diferenca semantica vs CSV legado (referencia)](#9-diferenca-semantica-vs-csv-legado-referencia)
10. [Checklist de integridade (apos cada `clickup_create_task`)](#10-checklist-de-integridade-apos-cada-clickup_create_task)

---

## 1. Identificacao da lista

| Item | Valor |
|---|---|
| Workspace | M7 Investimentos (id descoberto via `clickup_get_workspace_hierarchy`) |
| Lista | `pa-resultado` |
| List ID | `901326795742` |

---

## 2. Custom fields canonicos (IDs fixos)

### 2.1 Vertical (dropdown)

| Atributo | Valor |
|---|---|
| `field_id` | `a7c7bc7c-2526-4083-9753-aa2103a08f53` |
| Tipo | `drop_down` |
| Obrigatorio | **Sim** |

Mapeamento `option_value → vertical`:

```
0 → investimentos
1 → credito
2 → universo
3 → seguros
4 → consorcios
5 → wealth
6 → ib
```

### 2.2 Responsavel Externo (dropdown)

| Atributo | Valor |
|---|---|
| `field_id` | `e44c8cff-7d0b-4074-84ae-c10c67b0a26d` |
| Tipo | `drop_down` |
| Obrigatorio | **Sim** (stakeholder da decisao) |

Mapeamento `option_value → nome`:

```
0 → Berg Lima
1 → Bruno Chiaramonti
2 → Claudia Moraes
3 → Douglas Silva
4 → Felipe Nogueira
5 → Filipe Costa
6 → Joel Freitas
7 → Mauricio Sampaio
8 → Pedro Villarroel
9 → Sarah Caetano
10 → Tarcisio Catunda
11 → Tereza Bernardo
```

> **NAO confundir com `assignees[]`**. `assignees[]` e o executor operacional (membro do workspace ClickUp). `Responsavel Externo` e o stakeholder da decisao no ritual e e mostrado no Slide 5 do deck.

### 2.3 Custom fields adicionais (IDs descobertos dinamicamente)

Descobertos uma vez por sessao via `clickup_get_custom_fields(list_id="901326795742")`. Mapear por nome (case-insensitive). Aliases aceitos:

| Saida do agent | Aliases aceitos no ClickUp | Tipo esperado |
|---|---|---|
| `indicador_impactado` | "indicador impactado", "indicador", "kpi" | text ou drop_down |
| `origem` | "origem", "origin", "fonte" | text ou drop_down |
| `receita_impacto` | "receita", "receita impacto", "receita projetada" | currency / number |
| `volume_impacto` | "volume", "volume impacto", "volume projetado" | currency / number |
| `prazo` | usar campo nativo `due_date` (NAO custom field) | date |
| `prioridade` | usar campo nativo `priority` (NAO custom field) | int 1-4 |

> Se algum field adicional nao existir no ClickUp: criar a task sem o campo (warning ao usuario para preencher manualmente depois).

---

## 3. Mapeamento `plan-preview.json` v2.0 ↔ Payload `clickup_create_task`

> **v2.0 (2026-05-31)**: campos canonicos estao TOP-LEVEL em cada item de
> `contramedidas_novas[]`. O agente decision-recorder em Fase 5a deriva o payload
> MCP a partir desses top-level fields (NAO de `payload`/`clickup_create_payload`
> aninhado). Schema completo em [plan-preview-schema.md](plan-preview-schema.md).

| Campo v2.0 (top-level) | Campo do payload MCP | Notas |
|---|---|---|
| `name` | `name` | max ~80 chars; **comecar com verbo no infinitivo** (ver secao 3.1) |
| `descricao` | `description` | bloco markdown com contexto WBR + razao + criterio sucesso |
| `due_date` (YYYY-MM-DD) | `due_date_ms` | converter `YYYY-MM-DD` → epoch UTC * 1000 |
| `priority_clickup` (1-4) | `priority` | direto sem conversao |
| `priority_label` (urgent/high/normal/low) | — | so para legibilidade humana no preview |
| `clickup_create_payload.status` (opcional) | `status` | default `to do` se ausente |
| (derivado da vertical do ciclo) | `custom_fields[Vertical]` | option_value canonico (secao 2.1) |
| `responsavel_externo_option_value` | `custom_fields[Responsavel Externo]` | option_value canonico (secao 2.2) |
| `indicador_impactado_option_id` | `custom_fields[indicador_impactado]` | UUID resolvido via `clickup_get_custom_fields` |
| `origem_option_id` | `custom_fields[origem]` | UUID resolvido via `clickup_get_custom_fields` |
| `volume_impacto` | `custom_fields[volume_impacto]` | number (BRL); skip se null |
| `receita_impacto` | `custom_fields[receita_impacto]` | number (BRL); skip se null |

### 3.1. Padronizacao do `name` — verbos no infinitivo

> **Regra obrigatoria desde v3.5.1** (decisao do ritual N3 Consorcios 2026-05-06,
> Pedro action item 22:57). Todo `name` de contramedida nova DEVE comecar com
> verbo no infinitivo.

**Por que**: Padronizacao do Plano de Acao no ClickUp + leitura mais rapida em
listings + alinhamento entre rituais. Permite varrer a lista e identificar
"o que precisa ser feito" ja na primeira palavra.

**Exemplos**:

| Forma errada (substantivada) | Forma correta (infinitivo) |
|---|---|
| ~~"Diagnostico carteiras zeradas"~~ | "Diagnosticar carteiras zeradas dos 8 assessores" |
| ~~"Reuniao com Gustavo e Romulo"~~ | "Realizar reuniao com Gustavo e Romulo sobre estagnadas" |
| ~~"Mapeamento de oportunidades"~~ | "Mapear oportunidades estagnadas para desbloqueio" |
| ~~"Plano de prospeccao Tereza"~~ | "Elaborar plano de prospeccao Tereza" |
| ~~"Status WIN/LOSE 3 mega-prospects"~~ | "Definir status WIN/LOSE/RENEGOCIAR para 3 mega-prospects" |
| ~~"Comunicacao ao time M7 Produtos"~~ | "Comunicar ao time M7 Produtos sobre treinamento" |

**Verbos comuns** (escolher conforme acao real):
- **Diagnosticar** / **Investigar** / **Mapear** — para descoberta
- **Elaborar** / **Criar** / **Definir** / **Formalizar** — para producao de artefato
- **Realizar** / **Conduzir** / **Promover** — para reunioes ou eventos
- **Acelerar** / **Destravar** / **Desbloquear** — para acoes corretivas urgentes
- **Validar** / **Conferir** / **Revisar** — para QA ou auditoria
- **Comunicar** / **Notificar** / **Alinhar** — para acoes de comunicacao
- **Atualizar** / **Ajustar** / **Corrigir** — para fixes em sistemas/dados

**Anti-padroes a evitar**:
- Iniciar com substantivo: ~~"Diagnostico..."~~, ~~"Plano..."~~, ~~"Reuniao..."~~
- Iniciar com gerundio: ~~"Diagnosticando..."~~, ~~"Mapeando..."~~
- Iniciar com pessoa: ~~"Pedro: ajustar..."~~ (pessoa vai em `Responsavel Externo`)
- Iniciar com data: ~~"Esta semana: realizar..."~~ (prazo vai em `due_date` top-level YYYY-MM-DD)

**Validacao automatica** (sugerida para o agente):
1. Pegar a primeira palavra do `name`
2. Verificar se termina em `-r` (infinitivo regular: `-ar`/`-er`/`-ir`)
3. Excecoes aceitas: `Pôr`, `Pôr-se`, etc. (verbos terminados em `-or` arcaicos — raro)
4. Se nao termina em `-r`: WARN ao usuario na fase preview e sugerir reescrita

> **Regra de aplicacao**: A validacao e executada na Fase 4.5 (preview) antes de
> escrever `plan-preview.json`. Em caso de violacao, o agente reescreve
> automaticamente quando possivel (heuristica: substantivo → verbo cognato — ex:
> `Diagnostico` → `Diagnosticar`) e lista a mudanca em `pendencias` do sumario
> stdout para confirmacao do usuario.

### Mapeamento prioridade (v2.0)

Em `plan-preview.json` v2.0, dois campos sao top-level:

| Campo v2.0 | Valores | Uso |
|---|---|---|
| `priority_clickup` | 1, 2, 3, 4 | direto para ClickUp `priority` |
| `priority_label` | `urgent`, `high`, `normal`, `low` | so para legibilidade humana (preview, ata) |

| `priority_clickup` | `priority_label` | Cor visual |
|---|---|---|
| 1 | urgent | red |
| 2 | high | yellow |
| 3 | normal | blue |
| 4 | low | gray |

> **Legacy v1.0** (`critica/alta/media/baixa`): nao usar mais. O agente deve emitir
> `priority_label` em ingles (v2.0). Gatekeeper `_assert_schema_v2()` em `render_ata.py`
> aborta se schema_version != "2.0".

### Conversao de prazo (v2.0 → MCP)

```
cm["due_date"] (YYYY-MM-DD string) → datetime → epoch UTC → * 1000 → due_date_ms (int para MCP)
```

Sem prazo informado: NAO criar a task. Pergunte ao usuario antes — uma task sem `due_date` vai aparecer como "Sem prazo" no Slide 4 do proximo ritual e e flag de warning.

---

## 4. Payload exemplo (`clickup_create_task`)

```python
clickup_create_task(
    list_id="901326795742",
    name="Diagnosticar carteiras zeradas Seguros (8 assessores)",
    description="""
**Contexto WBR**: Ritual N3 Seguros 2026-04-29 (S18). 8 dos 20 assessores da
Claudia (40% da carteira) zeraram receita em Abril.

**Razao**: Sem diagnostico individual, coaching nao tem alvo. 40% inativa
estruturalmente compromete meta Maio.

**Criterio de sucesso**: 1 plano nominativo (bloqueio + acao + responsavel +
prazo) por assessor zerado, validado em conjunto com Claudia ate 15/05.
""",
    due_date_ms=1747353600000,  # cm["due_date"]="2026-05-15" -> epoch ms UTC
    priority=2,  # cm["priority_clickup"] (v2.0); priority_label="high"
    status="to do",
    custom_fields=[
        {"field_id": "a7c7bc7c-2526-4083-9753-aa2103a08f53", "value": 3},   # Vertical=Seguros
        {"field_id": "e44c8cff-7d0b-4074-84ae-c10c67b0a26d", "value": 6},   # Responsavel=Joel Freitas
        {"field_id": "<id-discovered>", "value": "receita_seguros_mensal"}, # indicador_impactado
        {"field_id": "<id-discovered>", "value": "ritual_seguros_2026-04-29"}, # origem
        {"field_id": "<id-discovered>", "value": 0},                        # volume_impacto (nao aplicavel)
        {"field_id": "<id-discovered>", "value": 41500.0},                  # receita_impacto (gap residual)
    ]
)
```

A response retorna o `id` da task (formato `86xxxxxxx`) — capturar e gravar na ata.

---

## 5. Update de tasks existentes

### 5.1 Campos permitidos via `clickup_update_task`

| Campo | Quando atualizar |
|---|---|
| `status` | Transicao de fase (`to do` → `in progress` → `complete`/`closed`) |
| `due_date_ms` | Prazo reajustado em ata |
| `priority` | Reescalonamento de prioridade |
| `custom_fields[volume_impacto]` | Volume revisado |
| `custom_fields[receita_impacto]` | Receita revisada |
| `custom_fields[indicador_impactado]` | Reapontamento (raro — quase sempre indica que era task errada) |

### 5.2 Campos PROIBIDOS de update (immutable apos create)

- `name` — nome original e a "memoria" da decisao. Nao alterar.
- `description` — contexto original. Nao alterar.
- `custom_fields[Vertical]` — vertical errada → criar nova task na vertical correta + cancelar a errada (`status: cancelled`)
- `custom_fields[Responsavel Externo]` — mudanca de stakeholder e decisao do ritual; quando acontece, **adicionar comment** explicando + criar task nova com responsavel correto se necessario
- `custom_fields[origem]` — historico imutavel
- `parent` — subtask hierarchy nao e gerenciada por este agent

### 5.3 Comments (`clickup_create_task_comment`)

Substitui o campo `comentarios` JSON inline do CSV legado. Cada ritual que toca uma task deve adicionar 1 comment de progresso.

**Formato sugerido:**

```
[Ritual {data} | WBR ref {checkpoint_label}]

Status: {before.status} → {after.status} (% conclusao: {before.percentual} → {after.percentual})

Decisao: {transcricao da decisao do ritual}

Evidencia: {link ou referencia, se mencionado pelo usuario}

Proximo passo: {acao concreta + responsavel + data}
```

**Regras**:
- Comments sao **append-only** — NUNCA editar ou deletar comments anteriores
- Cada ritual = 1 comment por task atualizada (uniformidade)
- Se a task foi concluida no ritual: comment final + `status: closed`/`complete`
- Se a task foi cancelada: comment com razao + `status: cancelled`

---

## 6. Verificacao de duplicatas

Antes de criar nova task, verificar duplicatas:

### 6.1 Spot-check rapido (snapshot JSON)

```python
snapshot = read_json("{cycle_folder}/dados/raw/clickup-tasks-{vertical}.json")

for nova_contramedida in contramedidas:
    candidatos = [
        t for t in snapshot["data"]
        if (
            similarity(t["name"], nova_contramedida["titulo"]) >= 0.85
            or any(termo_chave in t["name"].lower() for termo_chave in nova_contramedida["termos"])
        )
        and t["responsavel_externo"] == nova_contramedida["responsavel"]
    ]
    if candidatos:
        flag_como_potencial_duplicata(nova_contramedida, candidatos)
```

### 6.2 Confirmacao em tempo real (MCP)

Para casos limite ou quando o snapshot esta desatualizado:

```python
clickup_filter_tasks(
    list_id="901326795742",
    custom_fields=[
        {"field_id": "a7c7bc7c-2526-4083-9753-aa2103a08f53", "operator": "=",
         "value": vertical_option_value}
    ]
)
```

Comparar com a lista local. Match: NAO criar; listar em "Duplicatas Detectadas" da ata com `id` + `url`.

---

## 7. URLs de tasks (para a ata HTML)

Formato: `https://app.clickup.com/t/<task_id>`

Exemplo: task com `id: 86agymn2w` → `https://app.clickup.com/t/86agymn2w`

Usar como `<a href>` em todas as referencias de task na ata HTML para facilitar navegacao do gestor.

---

## 8. Erros e fallbacks

| Erro | Causa provavel | Acao do agent |
|---|---|---|
| `tool not found: clickup_create_task` | MCP ClickUp nao habilitado no projeto | Reportar em CICLO.md > Anomalias e PARAR. Pedir ao usuario para verificar `desempenho/.claude/settings.local.json` permissions. |
| `400 Bad Request — invalid custom_field` | field_id incorreto ou option_value fora do range | Re-rodar `clickup_get_custom_fields` para refrescar IDs. Validar option_value contra mapas canonicos. |
| `404 Not Found — task` em update | task_id incorreto, ou task em outra lista | Verificar com `clickup_get_task`. Se nao existir: NAO criar duplicata sem confirmar com usuario. |
| `Rate limit` (429) | Burst de creates | Backoff exponencial 1s/2s/4s. Se persistir >3 tentativas, parar e reportar. |
| Task criada mas custom field nao foi persistido | API ClickUp retornou 200 mas custom_fields[] vazio | Re-tentar via `clickup_update_task` com os custom_fields. Se persistir, registrar em anomalias. |

---

## 9. Diferenca semantica vs CSV legado (referencia)

| Conceito | CSV legado | ClickUp atual |
|---|---|---|
| Identificador | `PA-YYYY-NNN` (sequencial gerado pelo agent) | `id` ClickUp (gerado pelo ClickUp, formato `86xxxxxxx`) |
| Hierarquia | `parent_id` apontando para outro PA-* | `parent` apontando para `id` ClickUp; subtasks excluidas em E2 F1.5 |
| Comentarios | Campo `comentarios` (JSON array inline no CSV) | Comments do ClickUp (timeline append-only nativa) |
| Edicao | Edit no CSV (linha + campo) | `clickup_update_task` (campos permitidos) + `clickup_create_task_comment` (timeline) |
| Encoding | UTF-8 + delimitador `,` + escaping `""` | Nao aplicavel (API JSON) |
| Concorrencia | Risco de overwrite (sem locking) | Lock otimista do ClickUp |
| Backup/auditoria | Versionar o CSV no git | Snapshot `clickup-tasks-{vertical}.json` por ciclo + activity log do ClickUp |

> O `id` formato `PA-YYYY-NNN` pode ser opcionalmente armazenado em um custom field "ID interno" se o usuario quiser preservar a referencia historica. Nao e obrigatorio nem usado pelo pipeline.

---

## 10. Checklist de integridade (apos cada `clickup_create_task`)

- [ ] `id` retornado pelo MCP foi capturado e registrado na ata
- [ ] `Vertical` custom field bate com a vertical do ciclo
- [ ] `Responsavel Externo` custom field foi preenchido
- [ ] `due_date_ms` corresponde ao `cm["due_date"]` (converter de volta para `YYYY-MM-DD` e comparar)
- [ ] `priority` corresponde a `cm["priority_clickup"]` (1=urgent, 2=high, 3=normal, 4=low)
- [ ] `status` inicial e o status default da lista (`to do` ou equivalente)
- [ ] URL `https://app.clickup.com/t/<id>` foi adicionada na ata HTML como link clicavel
