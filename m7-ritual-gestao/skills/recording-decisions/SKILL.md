---
name: recording-decisions
description: >-
  G2.3-E5: Registra decisoes pos-ritual em ata estruturada (MD + HTML + PDF), prioriza
  contramedidas por impacto (volume/receita) e cria/atualiza tasks no ClickUp (lista
  pa-resultado 901326795742, SoT G2.2 do Plano de Acao) via MCP. Garante rastreabilidade:
  decisao no ritual -> ata -> task no ClickUp -> proximo ciclo le via E2 Fase 1.5 ->
  acompanhamento no proximo WBR. Use when the pipeline advances to E5 after the ritual,
  when /m7-ritual-gestao:next reaches E5, or when the user shares post-ritual notes.

  <example>
  Context: Ritual concluido, pipeline avanca para registro de decisoes
  user: "/m7-ritual-gestao:next"
  assistant: Solicita notas do ritual, gera ata estruturada, cria tasks novas e atualiza tasks existentes no ClickUp via MCP
  </example>

  <example>
  Context: Usuario compartilha notas do ritual diretamente
  user: "Registra as decisoes do ritual de Investimentos de hoje: [notas...]"
  assistant: Gera ata MD, prioriza contramedidas, cria tasks no ClickUp via MCP com custom fields preenchidos (Vertical, Responsavel Externo, indicador, origem, receita, volume)
  </example>
user-invocable: false
---

# Recording Decisions — Registro de Decisoes Pos-Ritual (E5)

> "Decisao sem registro e conversa. Registro sem acao e burocracia."

Esta skill recebe notas do ritual (formato livre), gera ata estruturada em MD/HTML/PDF, prioriza contramedidas por impacto financeiro e **cria/atualiza tasks no ClickUp** (lista `pa-resultado` id `901326795742`, SoT G2.2 do Plano de Acao desde 2026-04-30) via ClickUp MCP. Substitui o legado `plano-de-acao.csv` em todas as operacoes de escrita.

> **REGRA DE HANDOFF**: Ao invocar o agente decision-recorder, NAO passe valores de dados no texto do prompt. Passe APENAS caminhos de arquivos (vertical, subnivel, card_path, cycle folder, OUTPUT_DIR resolvido, paths dos artefatos). O decision-recorder deve usar Read tool para carregar os dados dos arquivos em disco e MCP tools para acessar o ClickUp.

## Dependencias Internas

| Recurso | Caminho | Tipo |
|---------|---------|------|
| Schema ClickUp + MCP mapping | [references/clickup-actions-schema.md](references/clickup-actions-schema.md) | Referencia |
| Regras de priorizacao e duplicatas | [references/prioritization-rules.md](references/prioritization-rules.md) | Referencia |
| Template da ata | [templates/ata-ritual.tmpl.md](templates/ata-ritual.tmpl.md) | Template |
| Template HTML da ata | [templates/ata-ritual.tmpl.html](templates/ata-ritual.tmpl.html) | Template |
| Guia de geracao HTML | [references/ata-html-guide.md](references/ata-html-guide.md) | Referencia |
| Script HTML→PDF | scripts/html-to-pdf.js (requer `npm install` em scripts/) | Script |
| Agent executor | `decision-recorder` (agents/decision-recorder.md) | Agent |
| ~~Schema CSV legado~~ | ~~references/csv-schema.md~~ | **DEPRECATED 2026-04-30** |
| ~~Linha-modelo CSV~~ | ~~templates/acao-template.tmpl.csv~~ | **DEPRECATED 2026-04-30** |

## Dependencias Externas (MCPs)

- **ClickUp MCP** (`mcp__claude_ai_ClickUp__*`) — REQUIRED para todas as operacoes de escrita no Plano de Acao. Tools usadas:
  - `clickup_get_custom_fields` — descobrir IDs dos custom fields adicionais por nome (uma vez no inicio)
  - `clickup_filter_tasks` — buscar tasks existentes por ID antes de atualizar (verificar duplicatas)
  - `clickup_create_task` — criar nova contramedida (com custom_fields preenchidos)
  - `clickup_update_task` — atualizar status/percentual/datas de task existente
  - `clickup_create_task_comment` — registrar progresso e contexto (substitui o JSON inline `comentarios` do CSV legado)
  - `clickup_get_task` — ler estado de task antes de atualizar (defesa contra escrita em estado desatualizado)

## Pre-requisitos (Entry Criteria)

- Card(s) de Performance da vertical localizado(s) em `{CARDS_DIR}/{Vertical}/card_*.yaml`
- Ritual realizado (confirmacao do usuario ou flag em CICLO.md)
- WBR da semana disponivel para contexto (consolidado por vertical — mesmo WBR alimenta todos os subniveis)
- **ClickUp MCP habilitado no projeto** (verificar `desempenho/.claude/settings.local.json` permissions — se ausente, reportar e PARAR; sem MCP nao ha como escrever)
- CICLO.md com `vertical` e `data_referencia` definidos
- **Modo subnivel resolvido**: se a vertical tem 2+ cards com `metadata.subnivel` distinto, o argumento `subnivel` deve ser informado pelo command. A skill rejeita execucao ambigua.
- **Transcricao do ritual no caminho canonico** (preferencial): `03-Rituais/N{N}/{Vertical-cap}[-{subnivel}]/{Cadencia}/{Periodo}/ata/Transcricao*.md` (level-first 2026-06-09). A skill auto-descobre via `resolve_ritual_path.py` antes de pedir notas ao usuario. Se ausente, fallback para input manual.

## Modo de Execucao (preview / commit)

> **Adicionado v3.5.0** — Para garantir que **nada e escrito no ClickUp sem aprovacao explicita do usuario**, a skill opera em 2 modos sequenciais:

| Modo | Quando | Faz | NAO faz |
|------|--------|-----|---------|
| `preview` (default) | Primeira invocacao | Le todos os inputs, gera ata MD rascunho, monta plano de acoes ClickUp completo (payloads), salva `{OUTPUT_DIR}/plan-preview.json`, retorna sumario estruturado para o orquestrador exibir ao usuario | Nenhuma chamada `clickup_create_task` / `clickup_update_task` / `clickup_create_task_comment` |
| `commit` | Apos aprovacao do usuario | Le `{OUTPUT_DIR}/plan-preview.json`, executa Fases 5 (ClickUp) + 5.5 (HTML/PDF) + 5.6 (replicacao) + 6 (verificacao) | Nada de novo a planejar — o plano esta congelado no JSON |

**Contrato com o orquestrador (command `/m7-ritual-gestao:record-decisions`)**:
1. Invoca skill em `mode=preview` → recebe resumo
2. Apresenta resumo no chat e pergunta `[s/n/editar]`
3. `s` → invoca skill em `mode=commit`
4. `n` → cancela (mantem `plan-preview.json` para auditoria)
5. `editar` → coleta correcoes, re-invoca `mode=preview` (regenera plano)

**Schema do `plan-preview.json`** (v2.0 desde 2026-05-31): ver [references/plan-preview-schema.md](references/plan-preview-schema.md). Resumo crítico:

- `schema_version: "2.0"` literal (validador `_assert_schema_v2()` em `render_ata.py` aborta em commit se mismatch).
- `ata_id` prefix: `D-NNN` para decisões, `C-NNN` para contramedidas (NUNCA `CM-NNN`).
- **Campos TOP-LEVEL obrigatórios em `contramedidas_novas[]`**: `name`, `descricao`, `due_date` (YYYY-MM-DD), `priority_clickup` (1-4), `priority_label` (`urgent`/`high`/`normal`/`low`), `responsavel_externo_label` (string), `responsavel_externo_option_value` (int). NUNCA aninhar esses em `payload` ou `clickup_create_payload` — o script de commit ClickUp deriva do top-level.

## Workflow

### Fase 0 — Resolver subnivel e filtrar Card (logica generica)

> **Regra:** este passo e **data-driven**. Algoritmo identico ao da skill `preparing-materials` Fase 1.0 — manter sincronizado.

1. Receber `vertical` (obrigatorio) e `subnivel` (opcional, pode ser `None`) como inputs.
2. `CARDS_DIR` = `~/Library/CloudStorage/OneDrive-MULTI7CAPITALCONSULTORIALTDA/desempenho/02-Controle/Cards-de-Performance`.
3. **Listar cards** via `Glob('{CARDS_DIR}/{Vertical}/card_*.yaml')` (ignorar `_Historico/`).
4. Se 0 cards: avisar usuario e prosseguir sem contexto organizacional (modo legado).
5. **Particionar cards em 2 grupos**:
   - `cards_consolidados`: lista de cards com `metadata.subnivel` ausente/`null`.
   - `cards_split`: dict `subnivel → card_path` para cards com `metadata.subnivel` populado.
   - `subniveis_distintos = sorted(cards_split.keys())`.

6. **Decidir modo de selecao** (4 casos):

   - **Caso A — `subnivel` PASSADO**:
     - A.1: bate com chave em `cards_split` → `SUBNIVEL_ATIVO = subnivel`; `CARD_PATH = cards_split[subnivel]`.
     - A.2: nao bate → erro `"Subnivel '{subnivel}' nao encontrado em {vertical}. Subniveis disponiveis: {subniveis_distintos}"` (se vazio: `"Vertical {vertical} nao tem cards com subnivel; argumento '{subnivel}' nao se aplica"`) e abortar.

   - **Caso B — `subnivel` AUSENTE e `cards_consolidados` >= 1**:
     - B.1: 1 card consolidado → usar; `SUBNIVEL_ATIVO = None`.
     - B.2: 2+ cards consolidados → preferir `N1 > N2 > N3 > N4 > N5`; empate → maior `metadata.version`. Warn de selecao automatica.

   - **Caso C — `subnivel` AUSENTE, `cards_consolidados` vazio, 2+ subniveis em `cards_split`**:
     - Erro `"Vertical '{vertical}' tem {N} subniveis disponiveis: {subniveis_distintos}. A skill exige argumento subnivel. Reinvoque /m7-ritual-gestao:record-decisions {vertical} <subnivel>."` e abortar.

   - **Caso D — `subnivel` AUSENTE, `cards_consolidados` vazio, 1 unico subnivel em `cards_split`**:
     - Usar; `SUBNIVEL_ATIVO = primeiro_subnivel`. Warn opcional.

7. **Resolver `OUTPUT_DIR`** (level-first, default ON 2026-06-09):
   - Caminho canonico via `resolve_ritual_path.py`: `{RITUAIS_DIR}/N{N}/{Vertical-cap}[-{subnivel}]/{Cadencia}/{Periodo}/ata/`
   - Onde `RITUAIS_DIR = {DESEMPENHO_ROOT}/03-Rituais`
   - `N{N}/` (pasta-pai) = `metadata.nivel`; `Vertical-cap[-{sub}]` concatena vertical capitalizada + subnivel hifenizado (ex: `Seguros-wl`, `Seguros-re`, `PJ2`, `Consorcios`).
   - `{Cadencia}` inferida do nivel (`Semanal`/`Mensal`, SEM o prefixo `N{N}-`).
   - `Periodo`: ISO week `{YYYY}-S{NN:02d}` (Semanal) ou `{YYYY-MM}` (Mensal).
   - Exemplos:
     - Cons N3 (ritual 2026-05-19): `03-Rituais/N3/Consorcios/Semanal/2026-S21/ata/`
     - Seg WL N3 (ritual 2026-05-27): `03-Rituais/N3/Seguros-wl/Semanal/2026-S22/ata/`
     - PJ2 N2 (ritual 2026-05-12): `03-Rituais/N2/PJ2/Mensal/2026-05/ata/`
   - **Multi-ciclos mesmo periodo (P1=a S3):** SOBRESCRITA — so o ciclo mais recente fica.

8. Armazenar `CARD_PATH`, `SUBNIVEL_ATIVO`, `OUTPUT_DIR` para uso pelas fases seguintes.

**Compatibilidade**: Caso B preserva comportamento historico para verticais com cards consolidados (CON, INV). Caso C e o pattern novo para verticais split puro (SEG WL/RE).

### Fase 1 — Coletar Contexto

1. **Read o Card de Performance** em `CARD_PATH` (resolvido na Fase 0):
   - Extrair: responsaveis (especialistas), KPIs com `criterio_desvio_critico`, estrutura organizacional (N1-N5), `logica_de_analise` (sequencia 7 passos)
   - Em verticais multi-subnivel: o card e SO o do subnivel selecionado — `responsaveis[]` cobre apenas os especialistas daquele subproduto.

2. **Carregar snapshot ClickUp do ciclo** (se existir):
   - Ler `{cycle_folder}/dados/raw/clickup-tasks-{vertical}.json` (gerado em E2 Fase 1.5)
   - Esse JSON contem todas as tasks ATIVAS da vertical com filtros canonicos ja aplicados (Vertical=N, parent==null, Responsavel Externo resolvido). **Filtros sao por vertical, nao por subnivel** — todas as tasks SEG (WL+RE) compartilham o mesmo JSON. Distincao por subproduto opcional via custom field adicional, mas nao e padrao no schema atual.
   - Usar para deteccao de duplicatas e referencia cruzada (IDs de tasks existentes)
   - Se ausente: pode-se prosseguir, mas verificacao de duplicatas vai depender de chamada `clickup_filter_tasks` em tempo real

3. **Localizar WBR** mais recente da vertical via `Glob('**/wbr/wbr-{vertical}-*.md')` (contexto dos desvios discutidos — consolidado por vertical, mesmo para verticais split)

4. **Ler templates**: `templates/ata-ritual.tmpl.md` e `templates/ata-ritual.tmpl.html`

5. **Descobrir custom fields da lista** (uma chamada por sessao):
   ```
   clickup_get_custom_fields(list_id="901326795742")
   ```
   Construir mapa `name → field_id` para os fields adicionais (`indicador_impactado`, `origem`, `receita_impacto`, `volume_impacto`, `prazo`, `prioridade`). IDs canonicos dos 2 dropdowns principais ja conhecidos (Vertical e Responsavel Externo — ver [references/clickup-actions-schema.md](references/clickup-actions-schema.md)).

6. **Localizar notas do ritual** (auto-descoberta com fallback):

   a. **Resolver `RITUAL_DIR`** invocando `resolve_ritual_path.py` (helper compartilhado com `preparing-materials`):
      ```bash
      python3 {plugin_dir}/m7-ritual-gestao/skills/preparing-materials/scripts/resolve_ritual_path.py \
        --base-dir {DESEMPENHO_ROOT}/03-Rituais \
        --vertical {vertical} \
        --ciclo-date {data_referencia} \
        --card-path {CARD_PATH}
      ```
      O helper le `Card.metadata.{nivel, subnivel}` e infere a cadencia, retornando `{base}/N{N}/{Vertical-cap}[-{subnivel}]/{Cadencia}/{Periodo}/` (level-first 2026-06-09). Ex: `03-Rituais/N3/Consorcios/Semanal/2026-S21/`, `03-Rituais/N3/Seguros-wl/Semanal/2026-S22/`, `03-Rituais/N2/PJ2/Mensal/2026-05/`.

   b. **Buscar transcricao** via `Glob('{RITUAL_DIR}/ata/Transcricao*.md')`. Se 1+ arquivos: pegar o mais recente por mtime. Read o conteudo completo via Read tool e usar como `notas_ritual`.

   c. **Fallback** quando glob retorna vazio:
      - Se `notas_ritual` foi explicitamente fornecido pelo orquestrador (input do command/agente): usar.
      - Caso contrario: solicitar ao usuario `"Transcricao nao encontrada em {RITUAL_DIR}/ata/. Compartilhe as notas do ritual (formato livre)."` e aguardar.

   d. Notas aceitas em formato livre (bullets, prosa, transcricao Fireflies, portugues coloquial). Extrair: participantes, decisoes, contramedidas, responsaveis, prazos, escalonamentos.

> **Importante**: a transcricao Fireflies tipicamente tem secoes `Action Items` por pessoa que devem ser parseadas como contramedidas (responsavel = pessoa, descricao = action, prazo = inferido se ausente). Em caso de prazo ausente, **NAO inferir** — listar como "prazo a definir" no plan-preview e perguntar ao usuario na fase de aprovacao.

### Fase 2 — Gerar Ata Estruturada

1. Parsear notas do usuario (formato livre aceito)
2. Extrair e categorizar:
   - **Decisoes**: itens decididos no ritual (ex: "aprovado novo processo de X")
   - **Contramedidas**: acoes corretivas com responsavel e prazo
   - **Escalonamentos**: itens que precisam de decisao do N1
   - **Proximos passos**: tarefas gerais com responsavel e prazo
3. Numerar decisoes sequencialmente: D-001, D-002, D-003...
4. **Bloco `scope_task_ids` (adicionado v3.8.0 — 2026-05-12, memory `reference_g2_2_action_scope_filter`)**:
   - Identificar tasks discutidas no ritual em 2 grupos:
     - `created_in_ritual`: IDs (placeholders `<pendente-create>` resolvidos na Fase 6) das contramedidas/proximos passos novos criados nesse ritual.
     - `preexisting_discussed`: IDs de tasks ClickUp ja existentes que foram discutidas no ritual (re-priorizadas, status atualizado, comentadas).
   - Inserir no MD da ata bloco YAML embedado entre marcadores HTML comment:
     ```
     <!-- scope_task_ids:
     ritual_date: 2026-05-12
     vertical: pj2
     nivel: N2
     subnivel: null
     created_in_ritual:
       - <pendente-create-D001>
       - <pendente-create-D002>
     preexisting_discussed:
       - 86agymn2w
       - 86b1k7p3x
     -->
     ```
   - Fonte de verdade do ciclo G2.2 seguinte: o `m7-controle/collecting-data` Fase 1.5 parsea esse bloco para filtrar tasks ClickUp (ver tabela em [references/clickup-actions-schema.md](references/clickup-actions-schema.md)).
5. Preencher template [ata-ritual.tmpl.md](templates/ata-ritual.tmpl.md) com dados extraidos + bloco `scope_task_ids`
6. **Salvar ata** via Write em `{OUTPUT_DIR}/ata-ritual-{data}.md` (`OUTPUT_DIR` resolvido na Fase 0 via helper — level-first `03-Rituais/N{N}/{Vertical-cap}[-{subnivel}]/{Cadencia}/{Periodo}/ata/`)

> **Nota**: Os IDs de task na ata serao preenchidos como `<pendente-create>` nesta fase e atualizados com IDs reais do ClickUp na Fase 6 (apos o `clickup_create_task` retornar). O bloco `scope_task_ids` tambem deve ser atualizado na Fase 6 substituindo placeholders pelos IDs reais.

### Fase 3 — Priorizar Contramedidas

Para cada contramedida definida no ritual, aplicar as regras de [references/prioritization-rules.md](references/prioritization-rules.md):

1. Identificar `indicador_impactado` (cruzar com WBR se usuario nao informou)
2. Coletar `volume` e `receita` estimados (do usuario ou inferidos do WBR)
3. Atribuir prioridade conforme tabela de priorizacao (critica/alta/media/baixa)
4. Ordenar contramedidas: critica > alta > media > baixa; desempate por receita desc

### Fase 4 — Verificar Duplicatas

Aplicar regras de deteccao de duplicatas conforme [references/prioritization-rules.md](references/prioritization-rules.md):

- **Fonte primaria**: snapshot `clickup-tasks-{vertical}.json` (campo `name` + `responsavel_externo`)
- **Fallback**: `clickup_filter_tasks(list_id="901326795742", custom_fields=[{Vertical=N}])` em tempo real

Se duplicata encontrada: NAO criar nova task, informar ao usuario, e registrar na secao "Duplicatas Detectadas" da ata.

### Fase 4.5 — Apresentar Plano para Aprovacao (gate `preview` → `commit`)

> **Adicionado v3.5.0**. Esta fase e o **unico ponto de retorno antes de qualquer escrita no ClickUp**. Em modo `preview`, a fase termina aqui e devolve o controle ao orquestrador. Em modo `commit`, esta fase e PULADA — o plan ja foi aprovado e congelado.

**Em modo `preview`:**

1. **Montar payload completo** de cada operacao ClickUp prevista nas Fases 5a/5b — sem executar:
   - Para cada `contramedida nova`: payload de `clickup_create_task` com TODOS os campos (name, description, due_date_ms, due_date_iso para legibilidade, priority, priority_label, status, custom_fields completos com nomes humanos alem dos IDs).
   - Para cada `task atualizada`: estado `before` (lido via `clickup_get_task`) + estado `after` (campos a modificar) + texto completo do `comment` a adicionar.
   - Para cada `duplicata detectada`: nome proposto + ID/URL da task existente que bloqueou a criacao.

2. **Persistir plano** em `{OUTPUT_DIR}/plan-preview.json` **no schema v2.0 literal** conforme [references/plan-preview-schema.md](references/plan-preview-schema.md). Requisitos minimos:
   - `schema_version: "2.0"` como string literal no topo.
   - Cada item de `decisoes[]` tem `ata_id` com prefix `D-` (ex: `"D-001"`).
   - Cada item de `contramedidas_novas[]` tem `ata_id` com prefix `C-` (ex: `"C-001"`) e TODOS os campos TOP-LEVEL canonicos: `name`, `descricao`, `due_date`, `priority_clickup`, `priority_label`, `responsavel_externo_label`, `responsavel_externo_option_value`.
   - **NAO duplicar** esses campos em `payload`/`clickup_create_payload` (campo opcional que so contem `list_id` + `status` quando necessario).
   - `metricas_resumo` populado para sumario rapido.

   Este arquivo e a **unica fonte de verdade** entre as duas invocacoes (preview e commit). O `render_ata.py` em commit invoca `_assert_schema_v2()` que aborta se `schema_version != "2.0"`.

3. **Persistir ata MD rascunho** em `{OUTPUT_DIR}/ata-ritual-{data}.md` (com IDs `<pendente-create>`). Esta versao serve para o usuario revisar a redacao das decisoes.

4. **Retornar sumario estruturado** ao orquestrador (via stdout do agent). **REGRA OBRIGATORIA (3.8.4+, memory `feedback_preview_lista_tudo_da_ata`)**: o sumario deve **enumerar TODOS os itens** que vao para a ata distribuida, nao apenas counts. Cada secao do plan-preview.json com itens humanos deve aparecer com lista completa (titulo + responsavel + prazo). Falhar em listar qualquer secao = violacao do gate humano RN-06 porque o usuario nao tem como aprovar/editar o que nao ve.

   ```
   PREVIEW_GENERATED
   plan_path: {OUTPUT_DIR}/plan-preview.json
   ata_draft_path: {OUTPUT_DIR}/ata-ritual-{data}.md

   resumo (counts):
     decisoes: N (X estrategicas + Y recorrentes/continuas)
     contramedidas_novas: M (criticas: X, altas: Y, medias: Z, baixas: W)
     tasks_atualizadas: U
     proximos_passos_nao_clickup: P
     duplicatas_detectadas: V
     escalonamentos: E

   ## Decisoes (N)  <-- decisoes NAO tem prazo (memory feedback_decisoes_sem_prazo)
   - D-001 | {titulo} | {responsavel}
   - D-002 | ...

   ## Contramedidas novas (M)
   - C-001 | {titulo} | {indicador} | {responsavel} | {prazo} | {prioridade}
   - C-002 | ...

   ## Tasks atualizadas (U)
   - {titulo} | {status_change_ou_comment_summary}
   - ...

   ## Proximos Passos (P)  <-- OBRIGATORIO mesmo nao virando task ClickUp
   - {acao} | {responsavel} | {prazo}
   - ...

   ## Escalonamentos (E)
   - {item}
   - ...

   ## Duplicatas detectadas (V)  <-- se houver
   - {titulo solicitado} | acao tomada: {...}
   ```

5. **PARAR** — nao executar Fase 5+. O orquestrador exibe o sumario INTEGRAL ao usuario e decide o proximo passo. Se omitir qualquer secao, considerar a iteracao como "preview invalido" e re-gerar.

**Em modo `commit`:**

1. **Read `{OUTPUT_DIR}/plan-preview.json`**. Se ausente: ERRO `"Plano de preview nao encontrado. Execute mode=preview primeiro."` e parar.
2. **Validar idade do plano**: se `mtime > 24h`, alertar e exigir re-preview (estado ClickUp pode ter divergido).
3. **Pular Fases 1-4** (ja foram executadas em preview) e prosseguir direto para Fase 5 usando os payloads do JSON.

### Fase 5 — Registrar no ClickUp via MCP

> **Executar APENAS em modo `commit`**. Em modo `preview`, esta fase nao roda — os payloads ja foram montados na Fase 4.5 e aguardam aprovacao.

Seguir integralmente as regras de [references/clickup-actions-schema.md](references/clickup-actions-schema.md) para criar tasks novas e atualizar existentes.

**Resumo operacional:**

#### 5a. Novas contramedidas (clickup_create_task)

Para cada contramedida nao-duplicata, montar payload conforme schema e invocar:

```
clickup_create_task(
  list_id="901326795742",
  name="<titulo descritivo da contramedida>",
  description="<contexto: WBR ref + razao da contramedida + indicador impactado>",
  due_date_ms=<timestamp em ms>,
  priority=<1-4 conforme prioritization-rules>,
  status="<status inicial — tipicamente 'to do' ou 'open'>",
  custom_fields=[
    {field_id: "a7c7bc7c-2526-4083-9753-aa2103a08f53", value: <vertical_option_value>},
    {field_id: "e44c8cff-7d0b-4074-84ae-c10c67b0a26d", value: <responsavel_option_value>},
    {field_id: "<id_indicador_impactado>", value: "<indicador_id>"},
    {field_id: "<id_origem>", value: "<origem_descritiva>"},
    {field_id: "<id_receita_impacto>", value: <number>},
    {field_id: "<id_volume_impacto>", value: <number>}
  ]
)
```

A response inclui o `id` da task criada (formato `86xxxxxxx`). Capturar e registrar na ata.

#### 5b. Tasks existentes mencionadas (clickup_update_task + clickup_create_task_comment)

Quando o ritual atualiza uma task existente (ex: "PA-2026-003 agora 50% concluida" ou referencia direta a `id` ClickUp):

1. **Ler estado atual**: `clickup_get_task(task_id="<id>")` — defesa contra escrita em estado desatualizado
2. **Atualizar campos** via `clickup_update_task`:
   - `status` (ex: `to do` → `in progress` → `complete`)
   - `due_date_ms` (se prazo foi reajustado)
   - `priority` (se reescalonado)
   - Custom fields adicionais (ex: `volume_impacto` revisado, `indicador_impactado` ajustado)
3. **Adicionar comentario de progresso** via `clickup_create_task_comment`:
   - Substitui o campo `comentarios` JSON inline do CSV legado
   - Comment text deve incluir: data do ritual, decisao tomada, contexto (% conclusao, evidencia, justificativa)
   - Formato sugerido: `"[Ritual {data}] Status atualizado para {status}. {observacao}. WBR ref: {checkpoint_label}"`

> **NUNCA substitua descricao ou nome da task** — sao a "memoria" original. Use comments para registro temporal.

### Fase 5.5 — Gerar Ata HTML e PDF

Com base na ata MD ja validada (Fase 2) e nos IDs ClickUp obtidos (Fase 5), gerar a versao visual HTML e converter para PDF.

#### 5.5a. Gerar HTML

**Regra (3.8.4+):** usar o script reusavel `scripts/render_ata.py` em vez de implementar o render ad hoc. Ele resolve a incompatibilidade entre o template Handlebars-flavored (`{{#each X}}...{{/each}}`) e o renderer Python `chevron` (Mustache puro), e ja monta o dict de dados a partir do `plan-preview.json`.

```bash
python3 {SKILL_DIR}/scripts/render_ata.py \
  --plan-preview-json {OUTPUT_DIR}/plan-preview.json \
  --template {SKILL_DIR}/templates/ata-ritual.tmpl.html \
  --output {OUTPUT_DIR}/ata-ritual-{data}.html \
  --nivel {N1|N2|N3} \
  --vertical {Vertical-cap} \
  --data {YYYY-MM-DD} \
  --participantes "Nome1, Nome2, Nome3" \
  --duracao "~36 min" \
  --wbr-referencia "Maio 2026, semana 5 (MTD)"
```

Saida JSON com `ok`, `output`, `size_bytes`, `unresolved_placeholders` (lista vazia = sucesso), `decisoes`, `contramedidas`, `acoes_atualizadas`, `proximos_passos`.

**Requisito do `plan-preview.json` (Fase 4.5)**: para o render funcionar 100%, o plan-preview deve conter os arrays **`decisoes`** (top-level) E `contramedidas_novas` E `tasks_atualizadas` E `proximos_passos_nao_clickup` E (opcional) `decisoes_recorrentes_adicionadas_round2` / `escalonamentos` / `duplicatas_detectadas`. Cada item: `ata_id`, `name`/`titulo`/`acao`, `responsavel`, `prazo`/`due_date`, etc. Sem `decisoes` no top-level, a secao "Decisoes" do HTML fica vazia.

**O que o script entrega:**
- CSS M7-2026 imutavel (copia do template, Score A)
- IDs ClickUp NAO aparecem em tabelas humanas (3.8.3+) — somente em `scope_task_ids` do MD. Memory: `feedback_clickup_invisible_to_humans`
- Sem placeholders `{{...}}` pendentes (validacao automatica)
- Logo M7 embeddado como base64 no template (nao alterar)

**Se o script falhar** (chevron ausente, template invalido): cair para implementacao ad hoc — Read template, fazer substituicao manual de placeholders, salvar. Mas registrar isso como anomalia para fix posterior.

**Regras**:
- CSS do template e imutavel (M7-2026 design system, score A)
- Logo M7 embeddado como base64 no template — nao alterar
- Nao gerar graficos SVG (ata e dados estruturados, nao analiticos)
- Nenhum placeholder `{{...}}` deve restar no HTML final

#### 5.5b. Gerar PDF

1. **Verificar dependencias**: Se `scripts/node_modules` nao existe, executar:
   ```bash
   cd {SKILL_DIR}/scripts && npm install
   ```
2. **Gerar PDF** via Bash:
   ```bash
   node {SKILL_DIR}/scripts/html-to-pdf.js \
     {OUTPUT_DIR}/ata-ritual-{data}.html \
     {OUTPUT_DIR}/ata-ritual-{data}.pdf
   ```
3. **Verificar** que o PDF foi gerado com sucesso
4. Se falhar: registrar em CICLO.md > Anomalias como WARNING (PDF e complementar, nao bloqueia pipeline)

### Fase 5.6 — Replicar artefatos para `03-Rituais/.../ata/`

> Coerencia com a Fase 5 do material-generator (G2.3-E2). A skill `preparing-materials` ja criou `RITUAL_DIR/ata/` vazio. Esta fase preenche com os artefatos finais.

1. Resolver `RITUAL_DIR` invocando `{plugin}/m7-ritual-gestao/skills/preparing-materials/scripts/resolve_ritual_path.py` (mesmo helper)
2. Copiar:
   - `{OUTPUT_DIR}/ata-ritual-{data}.md` → `{RITUAL_DIR}/ata/ata-ritual-{data}.md`
   - `{OUTPUT_DIR}/ata-ritual-{data}.html` → `{RITUAL_DIR}/ata/ata-ritual-{data}.html`
   - `{OUTPUT_DIR}/ata-ritual-{data}.pdf` → `{RITUAL_DIR}/ata/ata-ritual-{data}.pdf` (se gerado)
3. Validar byte-equal com staging

### Fase 6 — Finalizar e Validar

1. **Verificar tasks criadas** via `clickup_get_task` em cada `id` retornado pelo `clickup_create_task` — confirmar que custom fields foram persistidos corretamente
2. **Atualizar ata MD** com IDs definitivos do ClickUp **apenas no bloco machine-readable `scope_task_ids`** (substituir `<pendente-create>` por IDs reais retornados na Fase 5). Tabelas humanas do MD nao tem IDs ClickUp — identificacao por Titulo.
3. **Re-gerar ata HTML** com a ata MD atualizada (a HTML nao mostra IDs ClickUp em nenhuma tabela visual desde 3.8.3 — IDs sao infra)
4. **Re-copiar para `RITUAL_DIR/ata/`** se houve atualizacao
5. **Atualizar CICLO.md**: G2.3 E5 = concluido
6. **Exibir resumo** ao usuario:
   - X decisoes registradas
   - Y contramedidas novas (listar IDs ClickUp + URLs)
   - Z tasks atualizadas (listar IDs)
   - W comentarios adicionados
   - V duplicatas detectadas (se houver)
7. **Sugerir sub-passo distribuicao-ata** (S4 Phase 2 2026-05-20):

   Apos commit ClickUp concluido, append ao Log de Execucao:
   ```
   [{timestamp}] SISTEMA — G2.3 E5{FASE_SUFIXO} commit ClickUp concluido.
   Sub-passo distribuicao_ata = pendente. Execute /m7-ritual-gestao:next para
   gerar preview do envio via DM Slack (apos: /m7-ritual-gestao:approve-ata).
   ```

   E exibir no chat:
   ```
   Proximo: /m7-ritual-gestao:next {vertical}{ {subnivel}}
   (Vai gerar preview da distribuicao da ata via bot Slack m7-desempenho;
    aprovacao explicita em /m7-ritual-gestao:approve-ata libera o envio.)
   ```

### Fase 7 — Distribuicao da Ata via Bot Slack (sub-passo opcional, gate `/approve-ata`)

> **S4 Phase 2 (2026-05-20):** sub-passo conceitual de E5, executado por command separado
> (`/m7-ritual-gestao:next` gera preview; `/m7-ritual-gestao:approve-ata` faz commit).
> A skill `recording-decisions` NAO executa este passo diretamente — apenas sugere
> em Fase 6 passo 7.

Fluxo (gerenciado pelos commands, nao por esta skill):

1. `/m7-ritual-gestao:next` detecta E5 commit concluido + sub-passo distribuicao_ata pendente
2. Invoca `distributing-materials` em `phase=preview mode=post_ritual`:
   - Le ata MD/PDF + `plan-preview.json` em `{RITUAL_DIR}/ata/`
   - Valida RN-07 + RN-08 (single source of truth do WBR)
   - Resolve destinatarios via `Calendario-de-Rituais.xlsx` (Gestor + participantes;
     `--include-escalacao` se ata tem `escalacao_acionada: true`)
   - Renderiza mensagem com decisoes + contramedidas + escalacao block
   - Salva preview em `{RITUAL_DIR}/distribuicao/distribution-preview-post_ritual.json`
3. Usuario revisa e executa `/m7-ritual-gestao:approve-ata`:
   - Le preview JSON
   - Executa `slack_send.py --phase commit --mode post_ritual` (upload + DM)
   - Escreve linha em `desempenho/03-Rituais/distribuicao-log.csv` (CP-04)
   - Atualiza Log de Execucao com `distribuicao_ata concluido`

Compliance: INS-PERF-004 v2.0 Passos 4-6 (envio ata + escalacao nivel superior + timeout 48h documentado no log).

## Exit Criteria

### Modo `preview`
- [ ] Auto-descoberta de transcricao executada via `resolve_ritual_path.py` antes de pedir ao usuario
- [ ] `{OUTPUT_DIR}/plan-preview.json` gerado conforme [references/plan-preview-schema.md](references/plan-preview-schema.md)
- [ ] `{OUTPUT_DIR}/ata-ritual-{data}.md` gerado em rascunho (IDs `<pendente-create>`)
- [ ] Sumario estruturado retornado ao orquestrador (decisoes / contramedidas / updates / comments / duplicatas)
- [ ] **NENHUMA chamada `clickup_create_task` / `clickup_update_task` / `clickup_create_task_comment` executada** — verificacao por log

### Modo `commit`
- [ ] `{OUTPUT_DIR}/plan-preview.json` lido com sucesso (mtime <24h)
- [ ] Cada `contramedida_nova` do plano gerou 1 `clickup_create_task` bem-sucedida (id capturado)
- [ ] Cada `task_atualizada` do plano gerou 1 `clickup_update_task` + 1 `clickup_create_task_comment`
- [ ] Custom fields canonicos preenchidos: `Vertical` + `Responsavel Externo` + adicionais quando presentes no plano
- [ ] Ata MD final atualizada com IDs ClickUp reais (substituindo `<pendente-create>`)
- [ ] Ata HTML gerada em `{OUTPUT_DIR}/ata-ritual-{data}.html` com CSS M7-2026 inalterado, timeline de decisoes, tabela de contramedidas com badges (sem coluna ID — 3.8.3+), tabela de acoes atualizadas (sem coluna ID), KPI cards de resumo, sem placeholders `{{...}}` e sem IDs ClickUp em tabelas visuais (memory `feedback_clickup_invisible_to_humans`)
- [ ] Numeros no HTML identicos a ata MD
- [ ] PDF gerado em `{OUTPUT_DIR}/ata-ritual-{data}.pdf` (WARNING se falhar, nao bloqueia)
- [ ] Replicacao para `RITUAL_DIR/ata/` concluida com byte-equal vs staging
- [ ] CICLO.md atualizado (G2.3 E5 = concluido)

## Anti-Patterns

1. **NUNCA crie task sem verificar duplicatas** — sempre executar Fase 4 antes de Fase 5
2. **NUNCA escreva no `plano-de-acao.csv` legado** — descontinuado em 2026-04-30. SoT e o ClickUp via MCP
3. **NUNCA chame a API ClickUp via HTTP/curl** — use SEMPRE os tools `mcp__claude_ai_ClickUp__*`
4. **NUNCA gere ata sem numeros de decisao** (D-NNN) — toda decisao deve ser numerada e rastreavel
5. **NUNCA infira prioridade sem criterio** — usar regras de [references/prioritization-rules.md](references/prioritization-rules.md)
6. **NUNCA substitua a descricao ou o nome de uma task existente** — use `clickup_create_task_comment` para registro temporal
7. **NUNCA use `assignees[]` no lugar de `Responsavel Externo`** — assignees e executor operacional; Responsavel Externo (custom field) e o stakeholder da decisao
8. **NUNCA crie subtasks pelo agent** — politica G2.2: cada decisao do ritual vira uma task PARENT; subtasks sao gerenciadas pelo executor depois
9. **NUNCA preencha o custom field `Vertical` errado** — usar option_value canonico mapeado em [references/clickup-actions-schema.md](references/clickup-actions-schema.md)
10. **NUNCA hardcode nomes de vertical/subnivel** na logica da skill — a deteccao do subnivel e data-driven via `metadata.subnivel` dos cards. Quando vertical e split, processa SEMPRE 1 card unico (do subnivel selecionado), nunca merge.
11. **NUNCA gere ata em `{cycle_folder}/output/{vertical}/` quando ha subnivel ativo** — usar `{OUTPUT_DIR}` resolvido na Fase 0 (sufixado com `-{subnivel}`).
12. **NUNCA execute Fase 5 (ClickUp writes) em modo `preview`** — qualquer chamada `clickup_create_task` / `clickup_update_task` / `clickup_create_task_comment` antes da aprovacao do usuario e violacao critica do contrato preview/commit (v3.5.0+).
13. **NUNCA infira prazos ausentes na transcricao Fireflies** — listar como "prazo a definir" no plan-preview e perguntar ao usuario na fase de aprovacao. Inferir prazo silenciosamente compromete a fidelidade da ata.
14. **NUNCA pule auto-descoberta de transcricao** quando o caminho canonico existe — pedir notas ao usuario diretamente quando `{RITUAL_DIR}/ata/Transcricao*.md` esta disponivel e desperdicio de input e fonte de divergencia.
15. **NUNCA crie task ClickUp com `name` que nao comece com verbo no infinitivo** (regra v3.5.1). Reescrita automatica obrigatoria de substantivos/gerundios para forma cognata (`Diagnostico` → `Diagnosticar`); listar a reescrita em `pendencias` do sumario stdout. Detalhes em [references/clickup-actions-schema.md secao 3.1](references/clickup-actions-schema.md).
16. Para regras completas de payload e formato, ver [references/clickup-actions-schema.md](references/clickup-actions-schema.md)
