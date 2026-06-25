---
name: collecting-data
description: >-
  G2.2-E2: Coleta dados de indicadores via execucao de scripts Python standalone.
  O script collect.py le Cards e Indicadores YAML, gera um plano de execucao JSON
  com scripts a executar, roda cada script via subprocess (acesso direto a ClickHouse
  e Bitrix24 via bibliotecas Python), e consolida os outputs JSON em dados validados.
  A skill orquestra 3 comandos: plan → run → consolidate. Zero interpretacao de YAMLs.
  Use when executing the weekly performance cycle (E2 step), when /m7-controle:next
  advances to E2, or when /m7-controle:run-weekly starts the automated pipeline.

  <example>
  Context: Pipeline semanal avanca para E2
  user: "/m7-controle:next"
  assistant: Roda collect.py plan, collect.py run, collect.py consolidate
  </example>

  <example>
  Context: Usuario quer coletar dados de uma vertical especifica
  user: "Coleta os dados de Consorcios para a semana 12"
  assistant: Localiza Cards e Indicadores, roda plan → run → consolidate, apresenta resultados
  </example>
user-invocable: false
---

# Collecting Data — Coleta via Scripts Python Standalone (E2)

> "Zero interpretacao. Scripts acessam dados diretamente. Voce orquestra 3 comandos."

Esta skill coleta dados de indicadores via **execucao de scripts Python standalone**. Cada indicador da Biblioteca tem seu proprio script `.py` que acessa ClickHouse (via `clickhouse-connect`) e Bitrix24 (via `requests`) diretamente, sem MCPs. O script `collect.py` orquestra o ciclo:

1. **`plan`** — Le Cards + Indicadores YAML, gera plano com scripts a executar
2. **`run`** — Executa cada script via `subprocess`, gera `execution-results.json`
3. **`consolidate`** — Valida outputs contra `output_contract`, gera dados consolidados

**PRINCIPIO FUNDAMENTAL**: O LLM NAO interpreta YAMLs de indicadores. O LLM NAO executa queries ou chamadas de API. O LLM apenas roda 3 comandos Python e le os resultados. Toda logica de extracao esta nos scripts standalone e no modulo `m7_extract_utils.py`.

## Dependencias Internas

- [scripts/collect.py](scripts/collect.py) — Motor deterministico (plan + run + consolidate) — INDICADORES de desempenho
- [references/data-quality-rules.md](references/data-quality-rules.md) — Regras de validacao e thresholds
- [references/execution-plan-schema.md](references/execution-plan-schema.md) — Schema do plano JSON v2.0
- [templates/data-quality-report.tmpl.md](templates/data-quality-report.tmpl.md) — Template do Data Quality Report

## Dependencias Externas (MCPs)

- **ClickUp MCP** (`mcp__claude_ai_ClickUp__*`) — usado na Fase 1.5 para coletar Plano de Acao da lista `pa-resultado` (id 901326795742). Tools necessarios: `clickup_filter_tasks`, `clickup_get_custom_fields`, `clickup_get_task` (opcional para detalhes adicionais).

> **Resolucao de caminhos**: Cards e Indicadores vivem no repositorio do usuario, NAO no plugin.
> Localizar via `Glob('**/cards/{vertical}/*.yaml')` e `Glob('**/Biblioteca-de-Indicadores/_index.yaml')`.
> Todos os outputs sao salvos na pasta do ciclo `{vertical}/{YYYY-MM-DD}/`.

## Pre-requisitos (Entry Criteria)

- Cards de Performance YAML existem no repositorio do usuario para a vertical
- Biblioteca de Indicadores YAML acessivel no repositorio do usuario (v3.0 com campo `script.path`)
- Variaveis de ambiente configuradas: `CLICKHOUSE_HOST`, `CLICKHOUSE_PORT`, `CLICKHOUSE_USER`, `CLICKHOUSE_PASSWORD`, `BITRIX_WEBHOOK_URL` (cada script define seu database internamente)
- **ClickUp MCP** habilitado no projeto (verificar `.claude/settings.local.json` da `desempenho/`) — necessario para a Fase 1.5 (coleta do Plano de Acao da lista `pa-resultado` 901326795742, SSoT G2.2 das acoes)
- Dependencias Python instaladas: `clickhouse-connect`, `requests`, `pyyaml`
- CICLO.md indica E2 como etapa atual (ou execucao forcada via run-weekly)
- Python 3 disponivel

## Timestamps

Sempre que este documento menciona `{timestamp}`, obter a hora real via `date '+%Y-%m-%dT%H:%M'` (Bash). NUNCA usar `00:00` ou estimar.

## Workflow

### Fase 0 — Verificar Ambiente de Execucao

**Esta fase e obrigatoria e executa ANTES de qualquer coleta de dados.**

1. **Configurar UTF-8 no Python** (OBRIGATORIO em Windows; inocuo em Linux/Mac):

Os scripts Bitrix emitem caracteres unicode (`→`, acentos, `→`) em prints. Em Windows com `cp1252` como locale default, o stdout falha com `'charmap' codec can't encode character`. Sintoma: 6/9 scripts retornam erro logo no inicio mesmo com env vars OK.

Antes de qualquer execucao do `collect.py`, exportar:

```bash
export PYTHONIOENCODING=utf-8
export PYTHONUTF8=1
```

> Se rodar em ambiente onde `export` nao persiste entre passos do bash (ex: ferramentas que abrem novo subshell por comando), incluir o `export` na MESMA linha do `python3 collect.py ...` ou usar prefixo inline: `PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python3 collect.py ...`.

2. **Verificar variaveis de ambiente** via Bash:

```bash
python3 -c "
import os, sys
required = ['CLICKHOUSE_HOST','CLICKHOUSE_PORT','CLICKHOUSE_USER','CLICKHOUSE_PASSWORD','BITRIX_WEBHOOK_URL']
missing = [v for v in required if not os.environ.get(v)]
if missing:
    print(f'MISSING: {missing}', file=sys.stderr)
    sys.exit(1)
else:
    for v in required:
        val = os.environ[v]
        masked = val[:4] + '***' if len(val) > 4 else '***'
        print(f'{v}={masked}')
    print('Todas as variaveis OK')
"
```

> ClickUp NAO precisa de env var — autenticacao e gerenciada pelo MCP do projeto. Se MCP nao estiver disponivel na Fase 1.5, voce vai receber erro `tool not found: clickup_filter_tasks` — conferir `desempenho/.claude/settings.local.json` permissions.

3. **Verificar dependencias Python** via Bash:

```bash
python3 -c "import clickhouse_connect; import requests; import yaml; print('Dependencias OK')"
```

4. **Verificar encoding ativo** via Bash:

```bash
python3 -c "import sys; assert sys.stdout.encoding.lower() in ('utf-8','utf8'), f'stdout encoding={sys.stdout.encoding} (precisa ser utf-8); exporte PYTHONIOENCODING=utf-8'; print('Encoding OK:', sys.stdout.encoding)"
```

5. **Registrar resultado** no CICLO.md > Log: `[{timestamp}] SKILL:collecting-data — Ambiente verificado: vars={OK|FALHA}, deps={OK|FALHA}, encoding={OK|FALHA}`
6. **Se alguma variavel/dependencia/encoding faltar**: registrar em CICLO.md > Anomalias, informar usuario e AGUARDAR decisao
7. **Somente prossiga para Fase 1 se o ambiente estiver OK.**

### Fase 1 — Gerar Plano de Execucao

> **Nota sobre periodo**: Os parametros `data_inicio` e `data_fim` cobrem o PERIODO COMPLETO (mes inteiro), nao apenas a semana corrente. Ler estes valores do CICLO.md (header `Periodo`). A granularidade e usada pelas fases analiticas (E3-E6), nao pela coleta.

1. **Localizar Cards** da vertical via `Glob('**/cards/{vertical}/*.yaml')`
2. **Localizar Biblioteca de Indicadores** via `Glob('**/Biblioteca-de-Indicadores/_index.yaml')`
3. **Executar o script planner** via Bash:

```bash
python3 {path_to_plugin}/skills/collecting-data/scripts/collect.py plan \
  --cards-dir {cards_path} \
  --indicators-dir {indicators_path} \
  --cycle-folder {cycle_folder} \
  --param data_inicio={data_inicio} \
  --param data_fim={data_fim}
```

> **`--strict-indicators` (execucao unattended):** adicione esta flag para FALHAR
> (exit 3) quando algum `indicator_id` de Card ativo nao for encontrado na
> Biblioteca — assim o pipeline nao publica um WBR silenciosamente sem aquele
> indicador. Sem a flag (uso interativo), o plano segue mas emite ALERTA em stderr
> e marca `has_missing_indicators: true` no execution-plan.json.

4. **Verificar que `execution-plan.json` foi gerado** no cycle folder
5. **Ler o execution-plan.json** e exibir resumo ao usuario:

```
Plano de Execucao E2 — {vertical}

Scripts: {total_scripts}
Checksums verificados: {checksums_verified}/{total_scripts}
Test status: passed={N}, untested={N}, failed={N}
Parametros: data_inicio={data_inicio}, data_fim={data_fim}

Steps:
  1. {indicator_name} ({source_type}) — {script_path}
  2. ...

Indicadores ignorados: {skipped}
Indicadores nao encontrados: {not_found}

Prosseguir com a execucao?
```

6. **Se houver checksums FALHA**: alertar usuario — scripts foram modificados desde o ultimo teste
7. **Se houver indicadores nao encontrados que sao kpi_principal**: PARAR e informar usuario
8. **Registrar no CICLO.md > Log**: `[{timestamp}] SKILL:collecting-data — Plano gerado: {total_scripts} scripts`

### Fase 1.5 — Coletar Plano de Acao do ClickUp (SoT G2.2 de acoes)

> **Importante**: O Plano de Acao da M7 vive no ClickUp (lista `pa-resultado` id `901326795742`), NAO em CSV local. Esta fase substitui o legado `plano-de-acao.csv`. O output e consumido por E4 (`summarizing-actions`) e pelo Slide 5 do ritual G2.3.
>
> Esta fase corre **INDEPENDENTE** do flow `plan/run/consolidate` do `collect.py`. ClickUp tasks nao sao indicadores de desempenho — sao insumos do plano de acao.
>
> **Coleta via ClickUp MCP** (tools `mcp__claude_ai_ClickUp__*`). Sem script Python — o agent invoca os tools diretamente.

#### Constantes canonicas

| Item | Valor |
|---|---|
| List ID `pa-resultado` | `901326795742` |
| Custom field `Vertical` (id) | `a7c7bc7c-2526-4083-9753-aa2103a08f53` |
| Custom field `Responsavel Externo` (id) | `e44c8cff-7d0b-4074-84ae-c10c67b0a26d` |

**Resolucao do option do field Vertical (D3 — NAO hardcodar orderindex):**

> O `orderindex` e INSTAVEL — o split Seguros WL/RE (2026-05) ja deslocou os indices
> e o D3 (level-first) renomeia os labels para `{Nx - Vertical}`. **Resolver dinamicamente**
> a partir do `clickup_get_custom_fields` (Passo 1):
> 1. Ler `type_config.options` do field Vertical (id `a7c7bc7c-...`).
> 2. Normalizar `option.name` e o alvo (MANTER o token de nivel — NAO remover o prefixo):
>    lowercase, remover acentos, colapsar nao-alfanumericos em espaco unico, trim.
>    (Ex: `N3 - Consórcio` → `n3 consorcio`; `N2 - Crédito` → `n2 credito`.)
> 3. Alvo PRIMARIO = `n{nivel} {vertical_display}` (ex: card N3 + consorcios → `n3 consorcio`).
>    Casar com a opcao cujo nome normalizado seja igual OU contenha o alvo (substring cobre
>    plural: `consorcio` ⊂ `consorcios`). Manter o nivel no alvo DESAMBIGUA verticais que
>    existem em 2 niveis (`N2 - Crédito` vs `N3 - Crédito`; `N2/N3 - Investimentos`).
> 4. Fallback (transicao / labels flat antigos sem prefixo): se nenhum match com nivel,
>    casar so por `{vertical_display}`.
> 5. Usar o `orderindex` (ou `id`) da opcao casada como `value` no filtro.
>
> Aliases kebab → fragmento: `consorcios`→`consorcio`, `seguros-wl`→`seguros wl`,
> `seguros-re`→`seguros re`, `investimentos`→`investimentos`, `credito`→`credito`,
> `universo`→`universo`, `pj2`/`produtos`→`produtos`, `wealth`→`wealth`.
>
> **Snapshot vivo 2026-06-09 (REFERENCIA — consultar via get_custom_fields, drifta):**
> N3: Investimentos, Crédito, Universo, Seguros WL, Seguros RE, Consórcio · N2: Wealth,
> Produtos(=PJ2 tecnico), Investimentos, Crédito, Performance, Pessoas, Ecossistema, Marketing · N1: M7.
> (IB removido 2026-06-09; orderindexes mudam — por isso resolver por NOME, nunca por indice.)

**Mapeamento `option_value → nome` do field Responsavel Externo:**

```
0=Berg Lima | 1=Bruno Chiaramonti | 2=Claudia Moraes | 3=Douglas Silva
4=Felipe Nogueira | 5=Filipe Costa | 6=Joel Freitas | 7=Mauricio Sampaio
8=Pedro Villarroel | 9=Sarah Caetano | 10=Tarcisio Catunda | 11=Tereza Bernardo
```

#### Passos

1. **Descobrir custom fields** (se necessario para auto-mapear `indicador_impactado`, `origem`, `receita_impacto`, `volume_impacto`):

   ```
   clickup_get_custom_fields(list_id="901326795742")
   ```

   Construir mapa `name (lowercase) → field_id` para os fields adicionais. Aliases aceitos:
   - `indicador_impactado`: "indicador impactado", "indicador", "kpi"
   - `origem`: "origem", "origin", "fonte"
   - `receita_impacto`: "receita", "receita impacto", "receita projetada"
   - `volume_impacto`: "volume", "volume impacto", "volume projetado"

2. **Filtrar tasks por Vertical** via MCP:

   ```
   clickup_filter_tasks(
     list_id="901326795742",
     custom_fields=[{"field_id": "a7c7bc7c-2526-4083-9753-aa2103a08f53",
                     "operator": "=", "value": <orderindex_resolvido_dinamicamente>}],
     include_closed=true,
     subtasks=true,
     include_subtasks=true
   )
   ```

   > ⚠️ **HARDENING 2026-06-11 — o MCP vivo NAO filtra nem retorna custom fields no bulk.**
   > Apesar do exemplo acima, a versao instalada de `clickup_filter_tasks` IGNORA o
   > parametro `custom_fields` e NAO devolve o bloco `custom_fields` por task (so campos
   > base: id, name, status, priority, due_date, date_created/updated/closed, assignees,
   > parent). Logo voce **NAO consegue** obter a lista filtrada por Vertical so com filter_tasks.
   >
   > **Procedimento correto:**
   > 1. `clickup_filter_tasks(list_ids=["901326795742"], include_closed=true, subtasks=true)`
   >    → traz TODAS as tasks da lista (todas as verticais) com os campos base.
   > 2. Para cada task **candidata** (ver criterio abaixo), chamar
   >    `clickup_get_task(task_id, detail_level="detailed")` e ler o custom field `Vertical`
   >    (id `a7c7bc7c-...`, `value` = orderindex da opcao) — so o `get_task` detailed traz
   >    custom_fields. Manter no escopo as que casam a Vertical (incl. subnivel) do ciclo.
   > 3. **Candidatas a resolver via get_task** (para nao chamar get_task nas 80+):
   >    - todos os IDs em `created_in_ritual ∪ preexisting_discussed` da ata anterior; **+**
   >    - **TODAS as tasks abertas com `date_created > last_ritual_date`** (janela ad-hoc) —
   >      independentemente do dono. Resolver a Vertical de cada uma.
   > **NUNCA** inferir a vertical da task por keyword de especialista (`pa_keyword_filter` do
   > Card) nem assumir `ad_hoc=0` de ciclo anterior: tasks WL legitimas do **coordenador**
   > (ex.: Joel em Seguros) ou de Marketing nao batem keyword de assessor e seriam perdidas
   > (bug real detectado no WL 2026-06-10: 86ahghk33/86ah9a41u/86agymnd2 eram Seguros WL/Joel
   > e ficaram fora). O criterio de inclusao e o custom field `Vertical`, nunca o dono.

3. **Filtrar parent==null** (excluir subtasks). Para cada subtask retornada cujo `parent` esta no resultado, anexar nota `"<id> (<nome[:80]>)"` no campo `subtasks_pendentes` da parent. Subtasks ja fechadas/canceladas (`status` em `closed|cancelled|complete|done`) NAO entram como nota.

4. **Resolver Responsavel Externo** para cada task: ler valor do custom field (option_value), aplicar mapa do header. Se task nao tem o field, marcar como `null`.

5. **Resolver demais custom fields** (auto-descobertos no passo 1): para cada task, ler valor pelo `field_id` correspondente. Tipo `drop_down` → resolver via `type_config.options[orderindex].name`; demais (number, date, text) → ler valor direto.

5.b **Extrair `date_closed`** (campo padrao do ClickUp, adicionado v6.4.2 S2a B4.15): para cada task, ler atributo `date_closed` do retorno do `clickup_filter_tasks` (vem em ms epoch ou `null`). Converter para `YYYY-MM-DD` quando presente; manter `null` para tasks com status em aberto ou cancelada. Tasks com status `complete`/`closed`/`done` DEVEM ter `date_closed` populado.

6. **Montar JSON de saida** com schema canonico abaixo e gravar em `{cycle_folder}/dados/raw/clickup-tasks-{vertical}.json`.

7. **Filter composto de escopo (v3.x — 2026-05-12, memory `reference_g2_2_action_scope_filter`)**:

   Localizar a ata do ritual anterior via o helper `parse_ata_scope.py` (NAO montar
   path a mao — o helper resolve a estrutura canonica S3 E os dois layouts legado/level-first,
   eliminando o path hardcoded/Mac antigo):
   ```
   python3 scripts/parse_ata_scope.py \
     --rituais-base {DESEMPENHO_ROOT}/03-Rituais \
     --vertical {Vertical} --nivel {N_NIVEL} [--subnivel {sub}] \
     --excluir-data {data_ciclo_atual} \
     --output-json {cycle_folder}/dados/raw/scope-anterior.json
   # find_latest_ata() busca em:
   #   03-Rituais/{Vertical}[-{sub}]/N{N}-{Cad}/{Periodo}/ata/   (legado vertical-first)
   #   03-Rituais/N{N}/{Vertical}[-{sub}]/{Cad}/{Periodo}/ata/    (level-first)
   # e ja parseia o bloco scope_task_ids da ata mais recente (last_ritual_date).
   ```

   Se ata anterior encontrada:
   - Parsear bloco `<!-- scope_task_ids: ... -->` do MD da ata
   - Extrair `created_in_ritual` + `preexisting_discussed` + `ritual_date`

   Aplicar filter composto sobre as tasks ja extraidas (do passo 2-6):
   ```
   escopo_ritual_passado = {
     task for task in all_tasks
     if task.id in (created_in_ritual ∪ preexisting_discussed)
   }
   ad_hoc_pos_ritual = {
     task for task in all_tasks
     if task.id NOT in (created_in_ritual ∪ preexisting_discussed)
        AND task.date_created > last_ritual_date
        AND task.status NOT in ('done', 'closed', 'cancelled', 'complete')
   }
   ```

   > ⚠️ **`all_tasks` para a janela ad-hoc DEVE ter a Vertical resolvida por task via
   > `get_task` detailed** (ver hardening 2026-06-11 no passo 2). Enumerar TODAS as abertas
   > com `date_created > last_ritual_date`, resolver `Vertical` de cada, e incluir as que
   > casam a Vertical do ciclo — inclusive tasks do coordenador (Joel). NAO confiar no
   > `ad_hoc` de ciclos anteriores nem em keyword de especialista.

   Output JSON com 3 chaves:
   ```json
   {
     "escopo_ritual_passado": [<tasks>],
     "ad_hoc_pos_ritual": [<tasks>],
     "metadata": {
       "escopo_modo": "filtrado" | "primeiro_ciclo",
       "last_ritual_date": "2026-05-05",
       "ata_anterior_path": "03-Rituais/PJ2/N2/2026-05-05/ata/ata-ritual-2026-05-05.md"
     }
   }
   ```

   **Fallback primeiro ciclo** (sem ata anterior encontrada):
   - `escopo_ritual_passado` = todas as tasks open (filtro do passo 2-6 sem restricao)
   - `ad_hoc_pos_ritual` = vazio
   - `metadata.escopo_modo` = `"primeiro_ciclo"`

   **Tasks excluidas (orfas antigas)**: tasks criadas ANTES do ultimo ritual e NAO mencionadas na ata anterior. Ficam fora do ciclo ate serem oficializadas em algum ritual.

#### Schema do output

```json
{
  "extracted_at": "2026-04-30T10:00:00",
  "list_id": "901326795742",
  "vertical": "seguros",
  "filters_applied": {
    "vertical_custom_field": {
      "id": "a7c7bc7c-2526-4083-9753-aa2103a08f53",
      "expected_option_value": 3,
      "label_extracted": "Seguros"
    },
    "exclude_subtasks": true,
    "responsavel_externo_field": "e44c8cff-7d0b-4074-84ae-c10c67b0a26d"
  },
  "rows_returned": <int>,
  "data": [
    {
      "id": "86agymn2w",
      "name": "Reuniao intervencao Nisa",
      "status": "in progress",
      "priority": "high",
      "priority_orderindex": 2,
      "due_date": "2026-05-15",
      "parent": null,
      "vertical": "Seguros",
      "vertical_option_value": 3,
      "responsavel_externo": "Bruno Chiaramonti",
      "responsavel_externo_option_value": 1,
      "assignees": ["Pedro Villarroel"],
      "indicador_impactado": "receita_seguros_mensal",
      "origem": "ritual_2026-04-22",
      "receita_impacto": 11000,
      "volume_impacto": null,
      "subtasks_pendentes": ["86agymmyx (Briefing Nisa)"],
      "date_created": "2026-04-22",
      "date_updated": "2026-04-29",
      "date_closed": null,
      "url": "https://app.clickup.com/t/86agymn2w"
    }
  ]
}
```

Mapeamento de `priority_orderindex` (campo padrao do ClickUp): `1=urgent | 2=high | 3=normal | 4=low`.

`due_date`, `date_created`, `date_updated` e `date_closed` vem do ClickUp em ms epoch — converter para `YYYY-MM-DD`.

`date_closed` (adicionado v6.4.2 — S2a B4.15, 2026-05-18): timestamp em que a task foi marcada como `complete`/`closed`/`done`. Vem populado pelo ClickUp apenas para tasks fechadas; tasks abertas retornam `null`. Consumido downstream por preparing-materials Slide 5 PA Vencendo (label "Concluido em DD/MM"). Manter `null` quando ClickUp nao emitir (status em aberto ou cancelada).

#### Validar output

- `rows_returned > 0` ou justificar (vertical sem acoes ativas e plausivel)
- Spot-check: 1-2 tasks tem `vertical_option_value` igual a vertical do ciclo
- Spot-check: nenhuma task tem `parent != null` (filtro aplicado)
- Warning quando algum custom field adicional (`indicador_impactado`, etc.) volta `null` em todas as tasks — pode indicar que o field nao existe no ClickUp ou tem nome divergente dos aliases

#### Registrar no CICLO.md > Log

```
[{timestamp}] SKILL:collecting-data — Fase 1.5 ClickUp via MCP: {N} tasks coletadas (vertical={vertical}), output {cycle_folder}/dados/raw/clickup-tasks-{vertical}.json
```

### Fase 1.5b — Snapshot mapa_comercial (Cons/PJ2)

> **NOVO v6.5 (2026-05-21, Item 7 follow-up Seguros-WL 2026-05-20).**
> **Aplica apenas a verticais Cons e PJ2** (mapping comercial→codigo_xp lido de `m7Bronze.consorcio_contratos`).
> Seguros WL/RE/Investimentos NAO precisam — pular este passo.

**Motivacao:** `mapa_comercial` estava embedded como CTE em scripts (volume/receita Cons), lendo live. Mudancas no mapping entre snapshots PREV/CUR causavam drift nao rastreavel (ex: A22507 adicionado para Matheus Sales entre 13/05 e 20/05). Re-runs de ciclos antigos liam estado novo, perdendo reproducibilidade.

**Executar:**

```bash
python3 {path_to_plugin}/skills/collecting-data/scripts/collect.py extract-mapa-comercial \
  --indicators-dir {desempenho_root}/01-Metas/Biblioteca-de-Indicadores \
  --output {cycle_folder}/dados/raw/mapa-comercial-snapshot.csv
```

**Output:** CSV com columns `comercial,codigo_xp,contratos,ultimo_contrato`.

**Consumo downstream:** scripts vol/receita Cons podem ler via `--param mapa_comercial_path={cycle}/dados/raw/mapa-comercial-snapshot.csv`. Sem o param, default eh live ClickHouse (comportamento legado preservado para retrocompatibilidade).

**Re-runs:** ciclos antigos devem usar o snapshot daquele ciclo (NUNCA refazer query live). Snapshot fica como artefato em `dados/raw/`.

#### Registrar no CICLO.md > Log

```
[{timestamp}] SKILL:collecting-data — Fase 1.5b mapa_comercial snapshot: {N} rows, output {cycle_folder}/dados/raw/mapa-comercial-snapshot.csv
```

### Fase 2 — Executar Scripts

> **REGRA ABSOLUTA**: Um unico comando executa todos os scripts.
> O LLM NAO faz loop. O collect.py run gerencia tudo internamente via subprocess.

1. **Executar o runner** via Bash:

```bash
python3 {path_to_plugin}/skills/collecting-data/scripts/collect.py run \
  --plan {cycle_folder}/execution-plan.json \
  --cycle-folder {cycle_folder} \
  --timeout 900 \
  --parallel
```

2. **Verificar o exit code**:
   - Exit 0: execucao concluida com quorum OK
   - Exit 2: quorum insuficiente (<80% scripts com sucesso) — pipeline BLOQUEADO

3. **Ler `execution-results.json`** e verificar resultados:
   - Quantos scripts tiveram sucesso, erro, skip
   - Se quorum OK (>=80%)

4. **Se quorum FALHOU** (exit code 2):
   - Registrar em CICLO.md > Anomalias
   - Informar usuario com detalhes dos scripts que falharam
   - Apresentar opcoes:
     1. Retry scripts que falharam (reexecutar `collect.py run`)
     2. Prosseguir com dados parciais
     3. Abortar ciclo
   - **AGUARDAR decisao do usuario** — NAO prosseguir automaticamente

5. **Se algum script individual falhou** mas quorum esta OK:
   - Registrar em CICLO.md > Anomalias
   - Informar usuario sobre os scripts que falharam
   - Perguntar se deseja prosseguir (dados parciais) ou retry

6. **Registrar no CICLO.md > Log**: `[{timestamp}] SKILL:collecting-data — Execucao: {success}/{total} scripts com sucesso ({quorum_pct}%)`

### Fase 3 — Consolidar Resultados

1. **Executar o consolidator** via Bash:

```bash
python3 {path_to_plugin}/skills/collecting-data/scripts/collect.py consolidate \
  --plan {cycle_folder}/execution-plan.json \
  --results {cycle_folder}/execution-results.json \
  --indicators-dir {indicators_path} \
  --cycle-folder {cycle_folder} \
  --vertical {vertical}
```

2. **Verificar que os outputs foram gerados**:
   - `dados/dados-consolidados-{vertical}.json` — dataset consolidado
   - `dados/provenance.json` — SHA-256 de cada output file
   - `data-quality/data-quality-report.md` — relatorio de qualidade

3. **Se o script retornar exit code 2**: alertas criticos detectados, pipeline deve ser bloqueado

4. **Registrar no CICLO.md > Log**: `[{timestamp}] SKILL:collecting-data — Consolidacao concluida: {N} indicadores processados`

### Fase 4 — Gate de Qualidade

1. **Ler `dados-consolidados-{vertical}.json`** e verificar campo `metadata.qualidade_geral`
2. **Se qualidade_geral == "Critico"**:
   - Registrar em CICLO.md > Anomalias
   - Exibir alertas criticos ao usuario
   - **BLOQUEAR pipeline** — E3 NAO inicia
   - Sugerir: `"Resolva os alertas criticos e execute /m7-controle:next {vertical} para retomar de E2"`
3. **Se qualidade_geral == "Atencao"**: prosseguir com ressalvas registradas
4. **Avaliar quality_checks_pending** do JSON consolidado:
   - Para cada check, avaliar pass/fail com base nos dados fornecidos
   - Registrar resultados no CICLO.md

### Fase 5 — Apresentar Resultados

Exibir tabela de proveniencia ao usuario:

```
E2 Coleta Concluida — Resumo de Proveniencia

| Indicador | Script | Linhas | Arquivo | Status | Tempo |
|-----------|--------|--------|---------|--------|-------|
| volume_consorcio_mensal | volume_consorcio_mensal.py | 94 | volume_...json | OK | 3.2s |
| taxa_conversao_funil_con | taxa_conversao_funil_con.py | 245 | taxa_...json | OK | 8.1s |
| ... | ... | ... | ... | ... | ... |

Proveniencia: {success}/{total} scripts com sucesso ({quorum_pct}%)
Qualidade geral: {OK|Atencao|Critico}
```

Registrar conclusao no CICLO.md:
- Log: `[{timestamp}] SKILL:collecting-data — E2 concluido. {N} indicadores coletados, qualidade: {status}`

## Exit Criteria

- [ ] Variaveis de ambiente verificadas na Fase 0 (resultado registrado no CICLO.md). ClickUp NAO precisa env var — auth via MCP.
- [ ] **Encoding UTF-8 ativo** (`PYTHONIOENCODING=utf-8` + `PYTHONUTF8=1` exportados antes de qualquer comando python3 em Windows)
- [ ] execution-plan.json gerado pelo script collect.py plan (Fase 1)
- [ ] **`dados/raw/clickup-tasks-{vertical}.json` gerado via ClickUp MCP (Fase 1.5)** — SoT G2.2 das acoes
- [ ] Scripts executados via collect.py run (Fase 2)
- [ ] Cada script com sucesso produziu um output JSON em dados/raw/
- [ ] execution-results.json gerado com status por script
- [ ] Consolidacao executada pelo script collect.py consolidate (Fase 3)
- [ ] dados-consolidados-{vertical}.json gerado com script_execution_log e _verification
- [ ] provenance.json gerado com SHA-256 de cada output file
- [ ] data-quality-report.md gerado
- [ ] Nenhum alerta critico (caso contrario, pipeline bloqueia)
- [ ] Tabela de proveniencia apresentada ao usuario (Fase 5)

## Anti-Patterns

- NUNCA interprete YAMLs de indicadores — o script collect.py faz isso
- NUNCA execute queries SQL ou chamadas de API diretamente — os scripts standalone fazem isso
- NUNCA construa dados consolidados sem rodar o script consolidate
- NUNCA execute scripts sem verificar que o ambiente (variaveis + dependencias) esta OK
- NUNCA execute scripts com checksum nao verificado sem alertar o usuario
- NUNCA execute scripts com test_status=failed sem aprovacao explicita do usuario
- NUNCA invente dados se um script falhar — o collect.py registra o erro e voce PARA
- NUNCA defina variaveis de ambiente com valores inventados
- NUNCA avance para E3 se houver alertas criticos
- NUNCA gere dados sinteticos, placeholders ou "exemplos ilustrativos"
- NUNCA use Cards com status diferente de `active` (o script filtra, mas nao confie apenas nele)
- NUNCA prossiga apos falha de quorum sem decisao do usuario — PARE e reporte
- NUNCA leia `plano-de-acao.csv` local — o SoT do G2.2 e o ClickUp. CSVs antigos podem estar desatualizados em dias.
- NUNCA filtre tasks ClickUp pelo nome ou pasta — use SEMPRE o custom field `Vertical` (id `a7c7bc7c-2526-4083-9753-aa2103a08f53`) via option_value
- NUNCA use `assignees[]` no lugar do `Responsavel Externo` (custom field id `e44c8cff-7d0b-4074-84ae-c10c67b0a26d`) — assignees e executor operacional, Responsavel Externo e o stakeholder da decisao
- NUNCA inclua subtasks como linhas independentes — subtasks pendentes viram nota descritiva dentro da parent (campo `subtasks_pendentes`)
