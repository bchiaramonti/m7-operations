---
description: Executa o ciclo completo do pipeline G2.2 (E2 a E6) em sequencia para uma vertical (ou subnivel especifico quando a vertical tem split em multiplos cards). Pergunta periodo de analise e granularidade, cria pasta do ciclo com CICLO.md, invoca skills em cadeia e interrompe se alguma fase falhar.
argument-hint: <vertical> [subnivel]
disable-model-invocation: true
---

# m7-controle:run-weekly

Executa o pipeline de controle de performance (G2.2) para uma vertical (1 invocacao por Card).

## Input

- **vertical** (obrigatorio): `$ARGUMENTS[0]` — nome da vertical em kebab-case (ex: `investimentos`, `consorcios`, `credito`, `seguros`). Deve existir pelo menos 1 Card de Performance ativo em `cards/{vertical}/`.
- **subnivel** (condicional): `$ARGUMENTS[1]` — quando a vertical tem 2+ Cards com `metadata.subnivel` distinto (ex: SEG `wl`/`re`), o argumento e **obrigatorio** para selecionar qual Card processar. Vertical com Card unico: argumento ignorado (warn se passado). v6.5.0+ (2026-05-13).
- **periodo** (obrigatorio): Periodo de analise no formato `YYYY-MM` (ex: `2026-03`). Se nao informado nos argumentos, PERGUNTAR ao usuario antes de iniciar.
- **granularidade** (opcional): Frequencia do checkpoint de analise. Valores aceitos: `diaria`, `semanal`, `quinzenal`, `mensal`, `trimestral`. Default: `semanal`.

Se vertical nao informada, exibir: `"Uso: /m7-controle:run-weekly <vertical> [subnivel]"` e parar.

## Steps

### 1. Validar vertical

1. Normalizar o input para kebab-case lowercase
2. Verificar existencia de Cards de Performance: `Glob('**/cards/{vertical}/*.yaml')`
3. Se retornar **0 resultados**: exibir `"Nenhum Card de Performance encontrado para vertical '{vertical}'. Verifique se existe pelo menos 1 Card ativo em cards/{vertical}/."` e parar.
4. Se retornar resultados: vertical valida. **NAO prosseguir para E2 — ir para Step 1.1 primeiro.**

### 1.1. Resolver subnivel e Card alvo (v6.5.0+ — multi-card split)

> **Bug fix 2026-05-13:** Antes (v6.4.x), pipelines de verticais com 2+ Cards
> (ex: Seg WL + Seg RE) colidiam na mesma pasta `02-Controle/{vertical}/YYYY-MM-DD/`.
> Agora cada Card tem pasta dedicada via `OUTPUT_VERTICAL_DIR = {vertical}-{subnivel}`
> quando subnivel ativo (alinhado com `m7-ritual-gestao:prepare-ritual`).

1. **Ler todos os Cards** da vertical e particionar:
   - `cards_consolidados`: lista de Cards com `metadata.subnivel` ausente ou `null` (caso N1/N2/N3 single-vert).
   - `cards_split`: dict `subnivel → card_path` para Cards com `metadata.subnivel` populado.

2. **Resolver `SUBNIVEL_ATIVO`** e `CARD_PATH` conforme casos:
   - **Caso A — `$ARGUMENTS[1]` PASSADO** (pode ser um SUBNIVEL ou um NIVEL `N1..N5`):
     - A.1: bate com chave em `cards_split` (subnivel, ex: `wl`/`re`) → `SUBNIVEL_ATIVO = $ARGUMENTS[1]`; `CARD_PATH = cards_split[SUBNIVEL_ATIVO]`. Prosseguir.
     - A.1b: casa `^n[1-5]$` (nivel) → filtrar `cards_consolidados` por `metadata.nivel == {arg}`. 1 match → `CARD_PATH`, `SUBNIVEL_ATIVO = None`. 0 → erro `"Vertical '{vertical}' nao tem card consolidado no nivel '{arg}'. Niveis disponiveis: {niveis_distintos}"`. 2+ (mesmo nivel) → desempate por `metadata.version` maior (semver).
     - A.2: nao bate nem subnivel nem nivel → exibir `"Argumento '{arg}' nao e subnivel nem nivel valido em {vertical}. Subniveis: {subniveis_distintos}; Niveis: {niveis_distintos}"` e parar.
   - **Caso B — `$ARGUMENTS[1]` AUSENTE e `cards_consolidados` >= 1**:
     - B.1: 1 Card consolidado → `CARD_PATH` = esse Card unico; `SUBNIVEL_ATIVO = None`. Prosseguir.
     - B.2: 2+ Cards consolidados:
       - Se TODOS tem o mesmo `metadata.nivel` → desempate por `metadata.version` maior (semver). Warn: `"Vertical {vertical} tem {N} cards consolidados no nivel {nivel}; selecionado '{basename(CARD_PATH)}'."`. `SUBNIVEL_ATIVO = None`.
       - Se ha niveis DISTINTOS (ex: N2 centro + N3 operacional para a mesma vertical) → **NAO escolher silenciosamente**. Exigir o nivel: `"Vertical '{vertical}' tem cards consolidados em multiplos niveis: {niveis_distintos}. Especifique: /m7-controle:run-weekly {vertical} <nivel>"` e parar. (Substitui a antiga preferencia `N1>N2>N3`, que selecionava o Card errado quando N2 e N3 coexistem — fix 2026-06-09.)
   - **Caso C — `$ARGUMENTS[1]` AUSENTE, `cards_consolidados` vazio, 2+ subniveis em `cards_split`**:
     - Exigir argumento. Exibir `"Vertical '{vertical}' tem {N} subniveis disponiveis: {subniveis_distintos}. Especifique: /m7-controle:run-weekly {vertical} <subnivel>"` e parar.
   - **Caso D — `$ARGUMENTS[1]` AUSENTE, `cards_consolidados` vazio, 1 unico subnivel em `cards_split`**:
     - `CARD_PATH = cards_split[primeiro_subnivel]`; `SUBNIVEL_ATIVO = primeiro_subnivel`. Warn: `"Vertical {vertical} tem apenas 1 card com subnivel ('{sub}'); selecionado automaticamente."`.

3. **Derivar `OUTPUT_VERTICAL_DIR`** (label simbolico para logs/UI):
   - Se `SUBNIVEL_ATIVO` definido: `OUTPUT_VERTICAL_DIR = "{vertical}-{SUBNIVEL_ATIVO}"` (ex: `seguros-wl`)
   - Se `SUBNIVEL_ATIVO` ausente: `OUTPUT_VERTICAL_DIR = "{vertical}"`

   > **S3 2026-05-20:** `OUTPUT_VERTICAL_DIR` e label de display apenas. Path real do
   > ciclo e resolvido via helper `resolve_controle_path.py` (Step 1.1bis).

4. **Variaveis disponiveis para o restante do command:**
   - `CARD_PATH` — Card unico que sera processado
   - `SUBNIVEL_ATIVO` — string ou `None`
   - `OUTPUT_VERTICAL_DIR` — label simbolico (logs/UI; nao usar para paths reais)
   - `VERTICAL_LABEL` — para logs/UI: `f"{vertical} ({SUBNIVEL_ATIVO})"` ou apenas `vertical`

### 1.1bis. Resolver path canonical do ciclo (S3 2026-05-20+)

> **Mudanca S3:** ate 2026-05-19 o path era `02-Controle/{vertical}[-{subnivel}]/{YYYY-MM-DD}/`
> (lowercase, flat). Canonical S3 (Q1+P1 aprovadas 2026-05-19/20):
> `02-Controle/{Vertical-cap}[-{subnivel}]/{YYYY-MM}/{YYYY-MM-DD}/`. Cons ja usava o
> month wrapper desde 2026-05-04; Seg WL/RE/PJ2 sao migrados em Fase 3 do S3.
>
> **LEVEL-FIRST (default ON desde 2026-06-09):** o helper insere o nivel como pasta-pai →
> `02-Controle/N{N}/{Vertical-cap}[-{subnivel}]/{YYYY-MM}/{YYYY-MM-DD}/`. (`--legacy-flat` reverte ao layout sem `N{N}/`.)

Invocar o helper `resolve_controle_path.py` para obter o path absoluto canonical do ciclo:

```bash
CYCLE_DIR_ABS=$(python3 {plugin_dir}/m7-controle/skills/collecting-data/scripts/resolve_controle_path.py \
  --base-dir {DESEMPENHO_ROOT} \
  --vertical {vertical} \
  --ciclo-date {YYYY-MM-DD} \
  --card-path {CARD_PATH})
```

- Output (level-first, default ON): `{DESEMPENHO_ROOT}/02-Controle/N{N}/{Vertical-cap}[-{subnivel}]/{YYYY-MM}/{YYYY-MM-DD}/`
- Subnivel concatenado com hifen apos vertical capitalizada (1 Card = 1 pasta no FS).
- Use `CYCLE_DIR_ABS` em todos os Steps seguintes ao construir paths de artefatos.

### 1.2. Detectar 1o ritual do mes (close_mode dispatch) — v6.1.0+

> **NOVO 2026-05-06**: Quando o ciclo atual e o 1o do mes calendario,
> disparar coleta DUPLA — 1 ciclo de fechamento do mes anterior +
> 1 ciclo normal do mes corrente. Habilita o slide "Fechamento mes
> anterior" do m7-ritual-gestao (tweak C8 do plano de ritual).
>
> **v6.5.0 (2026-05-13):** lookup usa `OUTPUT_VERTICAL_DIR` (com sufixo de
> subnivel quando aplicavel) para isolar historico de cada Card.

1. **Localizar ciclo anterior** do mesmo Card no canonical S3:
   - Derivar `CARD_BASE` = `{DESEMPENHO_ROOT}/02-Controle/N{N}/{Vertical-cap}[-{subnivel}]/` (= `CYCLE_DIR_ABS` 2 niveis acima; `N{N}` do `metadata.nivel`)
   - `Glob('{CARD_BASE}/*/*/CICLO.md')` (month wrapper / date)
   - Extrair de cada match a data via regex `\d{4}-\d{2}-\d{2}` no nome do pai imediato; filtrar com data ANTES da data atual de execucao
   - Pegar o mais recente
   - Se nao existe: `is_first_ritual_of_month = false` (1o ciclo do Card)
2. **Comparar mes**:
   - `mes_ciclo_anterior = ciclo_anterior.data_referencia[:7]`  # YYYY-MM
   - `mes_ciclo_atual = data_execucao[:7]`
   - Se `mes_ciclo_anterior < mes_ciclo_atual`: **e 1o ritual do novo mes** → `is_first_ritual_of_month = true`
   - Caso contrario: `is_first_ritual_of_month = false`
3. **Se `is_first_ritual_of_month = true`**:
   - **Fluxo dual**:
     1. **Primeiro**: rodar pipeline em modo `close_mode` apontando para `mes_ciclo_anterior` completo:
        - `periodo = mes_ciclo_anterior`, `data_inicio = {mes_ciclo_anterior}-01`, `data_fim = ultimo dia do mes`
        - `granularidade = mensal`, `checkpoint_label = "{Mes_Anterior} {Ano} (fechamento)"`
        - Pasta `CYCLE_DIR_ABS_CLOSE`: derivar via helper passando `--ciclo-date {ultimo_dia_mes_anterior}` (output canonical: `{CARD_BASE_CANONICAL}/{mes_ciclo_anterior}/{ultimo_dia_mes_anterior}/`). Sufixo `-fechamento` no nome final NAO se aplica (canonical S3 nao usa esse sufixo).
        - CICLO.md tem `close_mode: true` no header
     2. **Depois**: rodar pipeline normal do mes corrente (Step 1.5 em diante) com `is_first_ritual_of_month: true` no header do CICLO.md atual
   - Cada coleta gera seus proprios artefatos. Pular qualquer skill ja concluida (CICLO.md `concluido`).
4. **Se `is_first_ritual_of_month = false`**: prosseguir para Step 1.5 normalmente (fluxo unico, ciclo do mes corrente).

### 1.5. Configurar periodo e granularidade

> **REGRA AUTOMATICA (2026-06-18, decisao do usuario):** o pipeline NAO pergunta
> mais periodo/granularidade por padrao (era um gate humano que travava o unattended).
> Aplica deterministicamente:
> - **granularidade = semanal** (sempre)
> - **periodo = mes atual** (derivado da data de execucao do sistema, `YYYY-MM`)
> - **1o ritual do mes** → modo **combinado** (fechamento mes anterior + atual), via
>   `is_first_ritual_of_month` (Step 1) + auto-resolve do build_deck (helper
>   `resolve_is_first_ritual` le top-level OU `meta.`).
>
> So use AskUserQuestion se o usuario pedir EXPLICITAMENTE um periodo/granularidade
> diferente na propria invocacao, OU se `date` do sistema falhar/for ambigua.

1. **Obter periodo automaticamente** (sem perguntar):
   - `periodo` = mes da data de execucao: `date '+%Y-%m'` (Bash)
   - `granularidade` = `semanal`
   - Registrar no Log do CICLO.md: `[{timestamp}] SISTEMA — periodo auto={periodo}, granularidade=semanal (regra automatica)`
2. **Override opcional**: se o usuario indicou outro mes/granularidade na invocacao (ex: "roda o fechamento de maio"), usar o que ele pediu em vez do default.
3. **Derivar datas** a partir do periodo:
   - `data_inicio` = primeiro dia do mes: `{YYYY-MM}-01`
   - `data_fim` = ultimo dia do mes (calcular: 28/29/30/31 conforme mes/ano)
4. **Calcular checkpoint_label** baseado na data de execucao dentro do periodo:
   - Determinar em qual checkpoint da granularidade a data atual se encontra
   - Formato: `"{Mes} {Ano}, {granularidade} {N} (MTD)"`
   - Exemplos:
     - Execucao em 2026-03-23 com granularidade semanal: `"Marco 2026, semana 4 (MTD)"`
     - Execucao em 2026-03-15 com granularidade quinzenal: `"Marco 2026, quinzena 1 (MTD)"`
     - Execucao em 2026-03-31 com granularidade mensal: `"Marco 2026 (fechamento)"`
5. **Calcular parametros temporais**:
   - `dias_uteis_totais`: total de dias uteis do periodo completo (seg-sex, excluir feriados se disponivel)
   - `dias_uteis_decorridos`: dias uteis do `data_inicio` ate a data de execucao (inclusive)
   - `dias_uteis_restantes`: `dias_uteis_totais - dias_uteis_decorridos`

### 2. Criar estrutura de pastas do ciclo

Determinar a data do ciclo como `YYYY-MM-DD` (data atual de execucao).

> **Timestamps**: Sempre que este documento menciona `{timestamp}`, obter a hora real do sistema via `date '+%Y-%m-%dT%H:%M'` (Bash). NUNCA usar `00:00` ou estimar a hora — executar o comando `date` no momento exato do registro.

Criar a estrutura de pastas dentro de `CYCLE_DIR_ABS` (path canonical absoluto resolvido em Step 1.1bis):

```
{CYCLE_DIR_ABS}/
├── CICLO.md
├── dados/
│   └── raw/
├── data-quality/
├── analise/
└── wbr/
```

Opcional — invocar o helper com `--create` ja cria as subpastas:
```bash
python3 {plugin_dir}/m7-controle/skills/collecting-data/scripts/resolve_controle_path.py \
  --base-dir {DESEMPENHO_ROOT} \
  --vertical {vertical} \
  --ciclo-date {YYYY-MM-DD} \
  --card-path {CARD_PATH} \
  --create
```

> **Exemplos de paths resultantes (canonical S3 2026-05-20+):**
> - `02-Controle/Consorcios/2026-05/2026-05-26/` (Cons N3, sem subnivel)
> - `02-Controle/Seguros-wl/2026-05/2026-05-27/` (Seg WL — subnivel hifenizado)
> - `02-Controle/Seguros-re/2026-05/2026-05-27/` (Seg RE — isolado de WL)
> - `02-Controle/PJ2/2026-05/2026-05-12/` (PJ2 N2, sem subnivel)
> - `02-Controle/Investimentos/2026-MM/2026-MM-DD/` (sem subnivel)

### 3. Inicializar CICLO.md

Verificar se ja existe um CICLO.md para a data atual e Card (`{CYCLE_DIR_ABS}/CICLO.md`):

- **Se existe e esta incompleto** (alguma fase pendente): retomar a partir da proxima fase pendente.
- **Se existe e esta completo**: perguntar ao usuario se deseja reexecutar.
- **Se nao existe**: criar novo CICLO.md com o template:

```markdown
# CICLO G2.2 - {VERTICAL_LABEL} - {YYYY-MM-DD}

> Iniciado: {YYYY-MM-DDTHH:MM}
> Vertical: {vertical}
> Subnivel: {SUBNIVEL_ATIVO|null}              <!-- v6.5.0+ — Step 1.1; null se Card consolidado -->
> Card: {basename(CARD_PATH)}                  <!-- v6.5.0+ — Card unico processado neste ciclo -->
> Periodo: {periodo} ({data_inicio} a {data_fim})
> Granularidade: {granularidade}
> Checkpoint: {checkpoint_label}
> Status: em_andamento
> Pasta: {CYCLE_DIR_ABS}  <!-- level-first: 02-Controle/N{N}/{Vertical-cap}[-sub]/{YYYY-MM}/{YYYY-MM-DD}/ -->
> Pasta_label: {OUTPUT_VERTICAL_DIR}/{YYYY-MM-DD}/  <!-- display only -->
> is_first_ritual_of_month: {true|false}   <!-- v6.1.0+ — Step 1.2 -->
> close_mode: {true|false}                 <!-- v6.1.0+ — true APENAS no ciclo de fechamento dispatch -->
> data_ultimo_ritual: {YYYY-MM-DD|null}    <!-- v6.1.0+ — referencia para A2 flag criada_em_ritual_anterior -->
> mes_ciclo_anterior: {YYYY-MM|null}       <!-- v6.1.0+ — usado em close_mode dispatch -->
>

## Progresso

| Fase | Skill | Status | Inicio | Fim | Artefato |
|------|-------|--------|--------|-----|----------|
| E2 | collecting-data | pendente | -- | -- | -- |
| E3 | analyzing-deviations | pendente | -- | -- | -- |
| E4 | summarizing-actions | pendente | -- | -- | -- |
| E5 | projecting-results | pendente | -- | -- | -- |
| E6 | consolidating-wbr | pendente | -- | -- | -- |

## Log de Execucao

<!-- Formato: [YYYY-MM-DDTHH:MM] {AGENTE:nome|SISTEMA|USUARIO} — {descricao} -->

## Anomalias

<!-- Alertas de qualidade, erros de scripts, dados ausentes -->
<!-- Formato: [YYYY-MM-DDTHH:MM] {AGENTE:nome|SISTEMA} — {severidade}: {descricao} -->

## Decisoes

<!-- Decisoes tomadas durante o ciclo com atribuicao explicita -->
<!-- Formato: [YYYY-MM-DDTHH:MM] {AGENTE:nome|USUARIO} — {decisao} | Justificativa: {razao} -->
```

### 4. Executar pipeline sequencialmente

Para cada fase na ordem E2 → E3 → E4 → E5 → E6:

#### 4a. Verificar entry criteria

| Fase | Entry Criteria | Como verificar |
|------|---------------|----------------|
| E2 | Cards YAML da vertical existem no repositorio do usuario | `Glob('**/cards/{VERT}/*.yaml')` retorna pelo menos 1 resultado |
| E3 | E2 concluido sem alertas criticos | CICLO.md E2 = `concluido` E `dados/dados-consolidados-{vertical}.json` existe |
| E4 | E3 concluido | CICLO.md E3 = `concluido` |
| E5 | E4 concluido | CICLO.md E4 = `concluido` |
| E6 | E5 concluido | CICLO.md E5 = `concluido` |

Se entry criteria **NAO atendido**: registrar erro no CICLO.md (Anomalias + Log) e parar (ver Step 5).

#### 4b. Registrar inicio no CICLO.md

1. Atualizar a tabela Progresso: `status: em_andamento`, `inicio: {timestamp}`.
2. Append ao **Log de Execucao**: `[{timestamp}] SISTEMA — Iniciando fase {fase} ({skill})`

#### 4c. Invocar skill correspondente

> **Regra arquitetural**: O command invoca **skills**, nunca agents diretamente. A skill decide internamente se executa no main thread ou delega a um agente.

| Fase | Skill |
|------|-------|
| E2 | collecting-data |
| E3 | analyzing-deviations |
| E4 | summarizing-actions |
| E5 | projecting-results |
| E6 | consolidating-wbr |

> **E6 em 2 passadas (v6.5.0):** consolidating-wbr orquestra Passada 1 (canonical) → main thread roda `normalize_canonical` + `inject_metas_ppi` (Fase 4.6, metas SoT `m7Prata.ciclo_metas_ppi`) → Passada 2 (docs do canonical injetado) → gate `validate-painel`. Ver "Modelo de Execucao" no SKILL.md.

> **MODO STRICT (2026-06-19 — run-weekly e unattended):** como este command roda sem
> operador, ativar os gates opt-in para nao publicar com gap em silencio:
> - **E2 (collecting-data):** rodar `collect.py plan` com `--strict-indicators`
>   (exit 3 se algum indicator_id de Card ativo nao for encontrado na Biblioteca).
> - **E6 (consolidating-wbr):** rodar `validate-painel.py` com `--strict-cross-artifact`
>   (divergencia cross-artifact vira FALHA exit 1 em vez de advisory).
> Em execucao interativa (`/m7-controle:next`), os flags ficam OFF (default advisory).

Contexto disponivel para a skill:
- Vertical sendo processada (`vertical`) e subnivel ativo (`SUBNIVEL_ATIVO`)
- Card unico processado (`CARD_PATH`)
- Periodo de analise: `periodo` (YYYY-MM), `data_inicio`, `data_fim`
- Granularidade: `granularidade`, `checkpoint_label`
- Parametros temporais: `dias_uteis_totais`, `dias_uteis_decorridos`, `dias_uteis_restantes`
- Caminho da pasta do ciclo: `{CYCLE_DIR_ABS}` (canonical S3; label `{OUTPUT_VERTICAL_DIR}/{YYYY-MM-DD}/` para logs)
- Caminho dos artefatos das fases anteriores
- Todos estes valores estao registrados no header do CICLO.md

> **v6.5.0+ (2026-05-13):** Quando `SUBNIVEL_ATIVO` ativo, a skill deve filtrar
> dados pelo Card (`CARD_PATH`) — apenas especialistas declarados em
> `card.apresentacao.responsaveis[]` contam para N1/N2. Skills E2-E6 sao
> compativeis com filtro por subnivel desde v6.4.0.

#### 4d. Verificar output

Confirmar que o artefato esperado foi gerado (sufixo `-{subnivel}` quando ativo):

| Fase | Artefato esperado (sem subnivel) | Com subnivel ativo |
|------|----------------------------------|--------------------|
| E2 | `data-quality/data-quality-report.md` + `dados/dados-consolidados-{vertical}.json` | mesmo path; JSON nao recebe sufixo (script de coleta unico por vertical) |
| E3 | `analise/deviation-cause-report.md` | mesmo |
| E4 | `analise/action-report.md` | mesmo |
| E5 | `analise/projection-report.md` | mesmo |
| E6 | `wbr/wbr-{vertical}-{data}.md` + variants | `wbr/wbr-{vertical}-{subnivel}-{data}.md` (ex: `wbr-seguros-wl-2026-05-13.md`) |

> Todos os caminhos sao relativos a `{CYCLE_DIR_ABS}` (canonical S3).
> O sufixo `-{subnivel}` no nome do WBR (E6) habilita o downstream
> `m7-ritual-gestao:prepare-ritual` a localizar o WBR correto via Glob.

#### 4e. Registrar conclusao no CICLO.md

1. Atualizar tabela Progresso: `status: concluido`, `fim: {timestamp}`, `artefato: {caminho}`.
2. Append ao **Log de Execucao**: `[{timestamp}] SISTEMA — Fase {fase} concluida. Artefato: {caminho}`

#### 4f. Gate check especial apos E2 (Proveniencia + Qualidade)

**Gate de Proveniencia** — verificar que dados vieram de execucao real de scripts:
1. Verificar que `execution-plan.json` existe no cycle folder
2. Verificar que `dados/provenance.json` existe e nao esta vazio
3. Para cada entrada em `provenance.json`, verificar que o raw file correspondente existe via `ls`
4. Para cada entrada, verificar SHA-256: executar `shasum -a 256 dados/raw/{file}` e comparar com `provenance.sha256`
5. Se QUALQUER verificacao falhar: **PARAR pipeline**, registrar em Anomalias, exibir ao usuario

**Gate de Qualidade** — verificar que dados sao confiaveis:
6. Se `data-quality/data-quality-report.md` contem alertas criticos:
   - Append a **Anomalias**: `[{timestamp}] SISTEMA — CRITICO: alertas de qualidade bloquearam pipeline`
   - Append a **Decisoes**: `[{timestamp}] SISTEMA — Pipeline interrompido. Aguardando decisao do usuario.`
   - **ALERTA SLACK (2026-06-19, decisao Gate 2 — obrigatorio em unattended):** postar no
     canal `C0B5UDSP6M9` via o **bot `m7-desempenho`** (NAO o Slack MCP do claude.ai —
     ele nao enxerga o workspace M7, da `channel_not_found`, testado 2026-06-19). Usar o
     `SLACK_BOT_TOKEN` (de `~/.claude/credentials/.env`) chamando Slack `chat.postMessage`
     com `channel=C0B5UDSP6M9` (mesmo token/mecanismo do `slack_send.py`). Mensagem:
     `":red_circle: Pipeline G2.2 {vertical}{SUBNIVEL_SUFIX} PAROU — qualidade Critico em {periodo}. Alertas: {lista_resumida}. Resolver e rodar /m7-controle:next {vertical}{SUBNIVEL_SUFIX}."`
     Sem o alerta, um run unattended pararia em silencio (proposito deste gate).
   - Exibir os alertas criticos ao usuario
   - Sugerir retomada com o mesmo invocador (incluir subnivel quando ativo):
     - `"Resolva os alertas criticos e execute /m7-controle:next {vertical}{SUBNIVEL_SUFIX} para retomar de E2"`
     - onde `{SUBNIVEL_SUFIX} = " {SUBNIVEL_ATIVO}"` se ativo, senao string vazia
   - **Parar pipeline**

**Resumo de Proveniencia** — exibir ao usuario:
```
E2 Coleta Concluida — Proveniencia

| Indicador | Tool | Linhas | Raw File | Hash OK |
|-----------|------|--------|----------|---------|
| {indicator_id} | {tool} | {rows} | {file} | {OK|FALHA} |

Proveniencia: {N}/{M} verificacoes OK
Qualidade: {OK|Atencao|Critico}
```

### 5. Tratamento de falhas

Se qualquer fase falhar:

1. Registrar no CICLO.md:
   - Tabela Progresso: `status: erro`, `fim: {timestamp}`
   - Append a **Anomalias**: `[{timestamp}] SISTEMA — ERRO em {fase}: {mensagem_erro}`
   - Append ao **Log de Execucao**: `[{timestamp}] SISTEMA — Pipeline interrompido em {fase}`
2. **Interromper pipeline** (nao avancar para proxima fase)
3. Exibir resumo parcial:

```
Pipeline G2.2 interrompido em {fase} ({skill}) - {VERTICAL_LABEL}

| Fase | Status       | Artefato                              |
|------|--------------|---------------------------------------|
| E2   | Concluido    | data-quality/data-quality-report.md   |
| E3   | Erro         | --                                    |
| E4   | Pendente     | --                                    |
| E5   | Pendente     | --                                    |
| E6   | Pendente     | --                                    |

Erro: {descricao}
Acao: /m7-controle:next {vertical}{SUBNIVEL_SUFIX} para retry da fase {fase}
```

> `{VERTICAL_LABEL}` = `"{vertical} ({SUBNIVEL_ATIVO})"` quando subnivel ativo, senao `vertical`.

### 6. Exibir resumo final (sucesso)

Ao concluir todas as 5 fases:

1. Atualizar CICLO.md: `> Status: concluido`
2. Append ao **Log de Execucao**: `[{timestamp}] SISTEMA — Pipeline G2.2 concluido com sucesso`
3. Exibir resumo completo:

```
Pipeline G2.2 concluido - {Vertical} - {YYYY-MM-DD}

| Fase | Tempo  | Artefato                                  |
|------|--------|-------------------------------------------|
| E2   | {dur}  | data-quality/data-quality-report.md        |
| E3   | {dur}  | analise/deviation-cause-report.md          |
| E4   | {dur}  | analise/action-report.md                   |
| E5   | {dur}  | analise/projection-report.md               |
| E6   | {dur}  | wbr/wbr-{vertical}{-subnivel}-{data}.md + wbr-narrativo |

Total: {duracao_total}
Pasta do ciclo: {CYCLE_DIR_ABS}  (label: {OUTPUT_VERTICAL_DIR}/{YYYY-MM-DD}/)
Proximo: /m7-ritual-gestao:prepare-ritual {vertical}{SUBNIVEL_SUFIX}
```

## Tratamento de erros

| Erro | Tratamento |
|------|------------|
| Vertical nao informada | Exibir uso e parar |
| Vertical invalida | Exibir valores aceitos e parar |
| Script falhou em E2 (env vars ausentes, dependencias, timeout) | Interromper, registrar em Anomalias, apresentar opcoes ao usuario (retry, verificar ambiente) e AGUARDAR decisao |
| Alerta critico em E2 | Interromper, registrar em Anomalias, exibir alertas, sugerir resolver antes de continuar |
| Fase intermediaria falha | Interromper, registrar erro em Anomalias e Log, sugerir `/m7-controle:next` para retry |
| CICLO.md corrompido | Recriar CICLO.md preservando fases ja concluidas |
