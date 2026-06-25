---
description: Registra decisoes pos-ritual em ata estruturada (MD + HTML + PDF) e cria/atualiza tasks no ClickUp (lista pa-resultado, SoT G2.2 do Plano de Acao). Equivalente a executar G2.3 E5 diretamente. Detecta automaticamente verticais multi-subnivel (split em 2+ cards), exigindo argumento `subnivel` quando aplicavel. Verifica entry criteria, solicita notas do ritual, invoca skill recording-decisions e atualiza CICLO.md.
argument-hint: <vertical> [subnivel]
disable-model-invocation: true
---

# m7-ritual-gestao:record-decisions

Registra decisoes pos-ritual (ata estruturada MD + HTML + PDF + criacao/atualizacao de tasks no **ClickUp via MCP**) para uma vertical a partir das notas do ritual.

> **Nota 2026-04-30:** O legado `plano-de-acao.csv` foi descontinuado. SoT G2.2 do Plano de Acao migrou para a lista ClickUp `pa-resultado` (id `901326795742`) acessada via ClickUp MCP. A skill `recording-decisions` (v2.0.0+) e o agent `decision-recorder` ja foram reescritos para esse fluxo. **Pre-requisito:** ClickUp MCP habilitado no projeto.

## Input

- **vertical** (obrigatorio): `$ARGUMENTS[0]` — vertical a processar. Valores aceitos: `investimentos`, `credito`, `universo`, `seguros`, `consorcios`.
- **subnivel** (condicional): `$ARGUMENTS[1]` — quando a vertical tem 2+ cards de performance com `metadata.subnivel` distinto, o argumento e **obrigatorio**. Vertical com card unico: argumento ignorado (warn se passado).

Se vertical nao informada, exibir: `"Uso: /m7-ritual-gestao:record-decisions <vertical> [subnivel]"` e parar.

## Steps

### 1. Validar vertical

1. Normalizar o input para lowercase.
2. Verificar se o valor esta na lista aceita: `investimentos`, `credito`, `universo`, `seguros`, `consorcios`.
3. Se valor invalido: exibir `"Vertical '{vertical}' invalida. Valores aceitos: investimentos, credito, universo, seguros, consorcios."` e parar.

### 1.5. Detectar cards e resolver subnivel (logica generica)

> **Regra:** este passo e **data-driven**. Algoritmo identico ao do `/m7-ritual-gestao:prepare-ritual` Step 1.5 — manter sincronizado.

1. Capitalizar vertical: ex `seguros` → `Seguros`.
2. **Listar cards** via `Glob('**/Cards-de-Performance/{Vertical}/card_*.yaml')` (ignorar `_Historico/`).
3. Se 0 cards: exibir `"Nenhum Card de Performance encontrado para {vertical}. Impossivel registrar decisoes sem contexto organizacional."` e parar.
4. **Particionar cards em 2 grupos**:
   - `cards_consolidados`: cards com `metadata.subnivel` ausente/`null`.
   - `cards_split`: dict `subnivel → card_path` para cards com `metadata.subnivel` populado.
   - `subniveis_distintos = sorted(cards_split.keys())`.

5. **Decidir modo de selecao** (4 casos):

   - **Caso A — argumento `$ARGUMENTS[1]` PASSADO**:
     - **A.1**: bate com chave em `cards_split` → `SUBNIVEL_ATIVO = arg`; `CARD_PATH = cards_split[arg]`.
     - **A.2**: nao bate → erro `"Subnivel '{arg}' nao encontrado em {vertical}. Subniveis disponiveis: {subniveis_distintos}"` (se vazio: `"Vertical {vertical} nao tem cards com subnivel; argumento '{arg}' nao se aplica"`) e parar.

   - **Caso B — argumento AUSENTE e `cards_consolidados` >= 1**:
     - **B.1**: 1 card consolidado → usar; `SUBNIVEL_ATIVO = None`.
     - **B.2**: 2+ cards consolidados → preferir `N1 > N2 > N3 > N4 > N5`; em empate, maior `metadata.version`. Warn de selecao automatica.

   - **Caso C — argumento AUSENTE, `cards_consolidados` vazio, 2+ subniveis em `cards_split`**:
     - Erro `"Vertical '{vertical}' tem {N} subniveis disponiveis: {lista}. Especifique: /m7-ritual-gestao:record-decisions {vertical} <subnivel>"` e parar.

   - **Caso D — argumento AUSENTE, `cards_consolidados` vazio, 1 unico subnivel em `cards_split`**:
     - Usar; `SUBNIVEL_ATIVO = primeiro_subnivel`. Warn opcional.

6. Armazenar `CARD_PATH` e `SUBNIVEL_ATIVO` para uso pelos passos seguintes.

> **Compatibilidade**: Caso B preserva comportamento historico para verticais com cards consolidados (CON, INV). Caso C e o pattern novo para verticais como SEG (split puro, sem consolidado).

### 2. Verificar entry criteria para E5

> **Timestamps**: Sempre que este documento menciona `{timestamp}`, obter a hora real do sistema via `date '+%Y-%m-%dT%H:%M'` (Bash). NUNCA usar `00:00` ou estimar.

1. **Localizar CICLO.md** da vertical no diretorio de trabalho: `Glob('**/CICLO.md')` — selecionar o mais recente da vertical.
2. **Verificar secao G2.3** no CICLO.md (se existir). **Calcular sufixo** `FASE_SUFIXO = " {SUBNIVEL_ATIVO}" if SUBNIVEL_ATIVO else ""` para procurar as linhas certas:
   - **`E2{FASE_SUFIXO}` nao concluido**: exibir aviso `"Materiais pre-ritual (E2{FASE_SUFIXO}) nao gerados. Recomenda-se executar /m7-ritual-gestao:prepare-ritual {vertical}{ {sub}} antes. Deseja prosseguir mesmo assim? [s/n]"`. Se `n`, parar. Se `s`, prosseguir.
   - **`E3{FASE_SUFIXO}` nao marcado como enviado**: exibir aviso `"Distribuicao de materiais (E3{FASE_SUFIXO}) nao registrada. Deseja prosseguir? [s/n]"`. Se `n`, parar.
   - **`E5{FASE_SUFIXO}` ja concluido**: exibir `"E5{FASE_SUFIXO} ja registrado para {vertical} neste ciclo. Deseja sobrescrever? [s/n]"`. Se `n`, parar.
3. **Verificar pre-requisito ClickUp MCP**:
   - Conferir que tools `mcp__claude_ai_ClickUp__*` estao disponiveis (via permissions em `.claude/settings.local.json`).
   - Se ausente: exibir `"ClickUp MCP nao habilitado. A skill recording-decisions exige MCP para escrever no Plano de Acao. Habilite em .claude/settings.local.json e tente novamente."` e parar.
4. **Localizar WBR** mais recente da vertical via `Glob('**/wbr/wbr-{vertical}-*.md')` para contexto narrativo dos desvios.
   - Se nao encontrado: exibir aviso `"WBR nao encontrado para {vertical}. Prosseguindo sem contexto de desvios."` (nao bloqueia).
5. **Localizar snapshot ClickUp do ciclo** (opcional): `Glob('**/dados/raw/clickup-tasks-{vertical}.json')` — gerado em E2 Fase 1.5. Usado para deteccao de duplicatas. Se ausente, fallback para `clickup_filter_tasks` em tempo real (a skill faz isso automaticamente).

### 3. Confirmar ritual realizado

1. Perguntar ao usuario: `"Confirme que o ritual de {Vertical}{ - {SUBNIVEL_ATIVO}} foi realizado. [s/n]"`
2. Se `n`: exibir `"Registro cancelado. Execute este comando apos a realizacao do ritual."` e parar.
3. Se `s`: prosseguir.

### 4. Localizar notas do ritual (auto-descoberta com fallback)

> **v3.5.0**: Auto-descoberta no caminho canonico antes de pedir ao usuario.

1. **Resolver `RITUAL_DIR`** via helper compartilhado:
   ```bash
   python3 {plugin_dir}/m7-ritual-gestao/skills/preparing-materials/scripts/resolve_ritual_path.py \
     --base-dir {DESEMPENHO_ROOT}/03-Rituais \
     --vertical {vertical} \
     --ciclo-date {data_referencia} \
     --card-path {CARD_PATH}
   ```
   O helper le `Card.metadata.{nivel, subnivel}` e infere a cadencia, retornando o path completo `{base}/N{N}/{Vertical-cap}[-{subnivel}]/{Cadencia}/{Periodo}/` (level-first, default ON 2026-06-09). Ex: `03-Rituais/N3/Consorcios/Semanal/2026-S21/`.

2. **Buscar transcricao** via `Glob('{RITUAL_DIR}/ata/Transcricao*.md')` e selecionar o mais recente por mtime.

3. **Decisao**:
   - **Se encontrado**: passar `notas_ritual_path = {path_da_transcricao}` para a skill (a skill faz Read internamente). Informar ao usuario: `"Transcricao localizada em {path}. Sera usada como fonte das notas."`.
   - **Se nao encontrado**: solicitar ao usuario: `"Transcricao nao encontrada em {RITUAL_DIR}/ata/. Compartilhe as notas do ritual (formato livre — bullets, texto corrido ou transcricao). Inclua: participantes, decisoes, contramedidas, responsaveis, prazos e escalonamentos."`. Aguardar input. Passar como `notas_ritual` (texto inline) para a skill.

### 5. Resolver pasta de output (parametrizado por subnivel)

1. Calcular `OUTPUT_SUBDIR`:
   - Se `SUBNIVEL_ATIVO` definido: `OUTPUT_SUBDIR = "{vertical}-{SUBNIVEL_ATIVO}"` (ex: `seguros-wl`)
   - Se ausente: `OUTPUT_SUBDIR = "{vertical}"` (path historico preservado)
2. Verificar/criar pasta `output/{OUTPUT_SUBDIR}/`.

### 6. Invocar skill recording-decisions em modo `preview`

> **Regra arquitetural**: O command invoca **skills**, nunca agents diretamente. A skill decide internamente se executa no main thread ou delega ao agente `decision-recorder`. Toda escrita do Plano de Acao vai via ClickUp MCP — **nenhum write em CSV** ocorre.
>
> **v3.5.0**: O fluxo agora e **2-fase**: primeiro modo `preview` (gera plano sem escrever no ClickUp), depois aprovacao do usuario, depois modo `commit` (executa).

1. Registrar inicio: append ao **Log de Execucao** do CICLO.md (se existir): `[{timestamp}] SISTEMA — Iniciando G2.3 E5{FASE_SUFIXO} (recording-decisions) para {vertical} em mode=preview`
2. Atualizar tabela Progresso do CICLO.md (linha `E5{FASE_SUFIXO}`): `status: em_andamento`, `inicio: {timestamp}`.
3. Invocar skill `recording-decisions` com `mode=preview` e contexto:
   - `mode: "preview"`
   - `vertical` sendo processada
   - `subnivel` (string ou `None`) — passado tal qual recebido
   - `card_path` — selecionado no Step 1.5
   - `notas_ritual_path` (path da transcricao auto-descoberta, se houver) OU `notas_ritual` (texto inline)
   - Caminho do CICLO.md (pasta do ciclo)
   - Caminho do WBR (se disponivel) — contexto dos desvios
   - Caminho do snapshot ClickUp (se disponivel) — `dados/raw/clickup-tasks-{vertical}.json`
   - Caminho de output: `output/{OUTPUT_SUBDIR}/`
   - Data de referencia: `{YYYY-MM-DD}` (data atual)
4. A skill retorna sumario stdout `PREVIEW_GENERATED` com paths de `plan-preview.json` e `ata-ritual-{data}.md` (rascunho), alem de contagens.

### 6.5. Apresentar plano e aguardar aprovacao do usuario

> **Gate critico**: antes deste passo, ZERO escrita no ClickUp. A skill em modo preview so leu, planejou e escreveu arquivos locais.

1. **Read** `{output_dir}/plan-preview.json`.

2. **Exibir no chat** sumario estruturado, com 5 secoes:

   **(a) Decisoes (D-NNN)** — uma linha por decisao:
   ```
   D-001 — Mapear oportunidades estagnadas para desbloqueio
            Responsavel: Tereza Bernardo · Prazo: 2026-05-13
   ```

   **(b) Contramedidas NOVAS a criar** — uma linha por contramedida com payload chave:
   ```
   C-001 — "Mapear e desbloquear oportunidades estagnadas" (high · prio 2)
            Responsavel Externo: Tereza Bernardo · Prazo: 2026-05-13
            Indicador: oportunidades_estagnadas_funil_pct_ativas
            Volume impacto: R$ 6,5M · Receita impacto: R$ 0
            Justificativa prio: Vermelho + volume alto
   ```

   **(c) Tasks EXISTENTES a atualizar** — uma linha por update com diff:
   ```
   86agymn2w — "Acelerar negociacao Icoforte"
              Diff: status: to do → in progress; prioridade: 3 → 2
              Comment: "[Ritual 2026-05-06] Status atualizado..."
   ```

   **(d) Duplicatas detectadas (NAO criadas)** — listar com link:
   ```
   "Mapear estagnadas Tereza" → similar a 86agt95x6 (https://app.clickup.com/t/86agt95x6)
   ```

   **(e) Pendencias** — itens com dados faltantes:
   ```
   - C-003 sem prazo definido — favor informar
   ```

3. **Perguntar ao usuario**:
   ```
   Plano apresentado acima sera escrito no ClickUp em 1 chamada por contramedida.
   Aprovar e prosseguir? [s = commit / n = cancelar / editar = corrigir]
   ```

4. **Decisao**:
   - **`s`**: prosseguir para Step 6.6 (commit)
   - **`n`**: cancelar registro. Append ao CICLO.md: `[{timestamp}] SISTEMA — G2.3 E5{FASE_SUFIXO} cancelado pelo usuario. Plan-preview.json preservado em {output_dir} para auditoria.`. Status linha E5 = `cancelado_pelo_usuario`. PARAR.
   - **`editar`**: solicitar ao usuario as correcoes (formato livre). Re-invocar skill em `mode=preview` com as correcoes injetadas como adendo ao notas_ritual. Repetir Step 6.5 com novo plano.

### 6.6. Invocar skill recording-decisions em modo `commit`

1. Append ao Log de Execucao: `[{timestamp}] SISTEMA — Plano aprovado pelo usuario. Iniciando mode=commit.`
2. Re-invocar skill `recording-decisions` com `mode=commit`:
   - `mode: "commit"`
   - Mesmos paths do Step 6 (vertical, subnivel, card_path, output_dir, etc.)
   - `plan_preview_path: {output_dir}/plan-preview.json`
3. A skill executa Fases 5 (ClickUp) → 5.5 (HTML/PDF) → 5.6 (replicacao 03-Rituais) → 6 (verificacao).
4. Skill retorna IDs criados, IDs atualizados, comments adicionados.

### 7. Verificar outputs gerados

1. Confirmar existencia da ata MD:
   - `output/{OUTPUT_SUBDIR}/ata-ritual-{vertical}-{YYYY-MM-DD}.md`
2. Confirmar existencia da ata HTML:
   - `output/{OUTPUT_SUBDIR}/ata-ritual-{vertical}-{YYYY-MM-DD}.html`
3. Confirmar que tasks foram criadas/atualizadas no ClickUp (a skill retorna a lista de IDs criados e tasks atualizadas — verificar nao-vazio quando ha contramedidas).
4. Se ata MD nao gerada:
   - Registrar erro no CICLO.md (Anomalias + Log)
   - Exibir: `"Erro na geracao da ata. Verifique os logs do decision-recorder."` e parar.

### 8. Atualizar CICLO.md

1. Localizar linha `E5{FASE_SUFIXO}` na secao G2.3 do CICLO.md:
   - **Se linha existe**: atualizar `status: concluido`, `fim: {timestamp}`, `artefato: output/{OUTPUT_SUBDIR}/ata-ritual-{vertical}-{YYYY-MM-DD}.md`
   - **Se linha NAO existe** (modo split, primeira execucao deste subnivel sem prepare-ritual previo): adicionar 3 novas linhas conforme template abaixo.
   - Append ao **Log de Execucao**: `[{timestamp}] SISTEMA — G2.3 E5{FASE_SUFIXO} concluido. Ata gerada e tasks ClickUp criadas/atualizadas.`
2. Se CICLO.md nao possui secao G2.3, adicionar (com sufixo so se aplicavel):

```markdown
## G2.3 - Ritual de Gestao

| Fase | Skill | Status | Inicio | Fim | Artefato |
|------|-------|--------|--------|-----|----------|
| E2{FASE_SUFIXO} | preparing-materials | pendente | -- | -- | -- |
| E3{FASE_SUFIXO} | (distribuicao manual) | pendente | -- | -- | -- |
| E5{FASE_SUFIXO} | recording-decisions | concluido | {timestamp} | {timestamp} | output/{OUTPUT_SUBDIR}/ata-ritual-{vertical}-{YYYY-MM-DD}.md |
```

### 9. Exibir resultado final

Exibir resumo ao usuario (incluir subnivel quando ativo):

```
Decisoes registradas - {Vertical}{ - {SUBNIVEL_ATIVO}} - {YYYY-MM-DD}

Card processado: {basename(CARD_PATH)}
Arquivos:
- output/{OUTPUT_SUBDIR}/ata-ritual-{vertical}-{YYYY-MM-DD}.md
- output/{OUTPUT_SUBDIR}/ata-ritual-{vertical}-{YYYY-MM-DD}.html
- output/{OUTPUT_SUBDIR}/ata-ritual-{vertical}-{YYYY-MM-DD}.pdf (se gerado)

ClickUp:
- X decisoes registradas (D-001..D-NNN)
- Y tasks NOVAS criadas (IDs: 86xxxxxxx, ..., links em ata HTML)
- Z tasks atualizadas via clickup_update_task
- W comments adicionados via clickup_create_task_comment
- V duplicatas detectadas (nao-criadas — ver secao "Duplicatas Detectadas" da ata)

Replicado para: {ritual_dir}/ata/ (03-Rituais/)
Tempo: {duracao}
Pipeline G2.3 concluido para {vertical}{ {SUBNIVEL_ATIVO}} nesta semana.
```

## Tratamento de erros

| Erro | Tratamento |
|------|------------|
| Vertical nao informada | `"Uso: /m7-ritual-gestao:record-decisions <vertical> [subnivel]"` |
| Vertical invalida | `"Vertical '{vertical}' invalida. Valores aceitos: investimentos, credito, universo, seguros, consorcios."` |
| Nenhum card encontrado | `"Nenhum Card de Performance encontrado para {vertical}. Impossivel registrar decisoes sem contexto organizacional."` |
| Vertical multi-subnivel sem subnivel passado | `"Vertical '{vertical}' tem {N} subniveis disponiveis: {lista}. Especifique: /m7-ritual-gestao:record-decisions {vertical} <subnivel>"` |
| Subnivel passado nao corresponde a card existente | `"Subnivel '{arg}' nao encontrado em {vertical}. Subniveis disponiveis: {lista}"` |
| Subnivel passado em vertical sem split | Warn: `"Vertical {vertical} tem apenas 1 card; argumento '{arg}' ignorado."`; processa normalmente |
| ClickUp MCP indisponivel | `"ClickUp MCP nao habilitado. A skill recording-decisions exige MCP para escrever no Plano de Acao. Habilite em .claude/settings.local.json e tente novamente."` |
| E2 nao concluido (linha do subnivel) | Aviso com opcao de prosseguir (nao bloqueia) |
| E3 nao marcado enviado | Aviso com opcao de prosseguir (nao bloqueia) |
| E5 ja concluido | Perguntar se deseja sobrescrever |
| Ritual nao confirmado | `"Registro cancelado. Execute este comando apos a realizacao do ritual."` |
| WBR nao encontrado | Aviso informativo (nao bloqueia — prossegue sem contexto de desvios) |
| Erro na geracao da ata | Registrar erro no CICLO.md, exibir detalhes |
| CICLO.md nao encontrado | Prosseguir sem atualizacao de ciclo; exibir aviso `"CICLO.md nao encontrado. Ata gerada mas progresso nao registrado."` |
| Transcricao nao encontrada em `03-Rituais/.../ata/` | Fallback informativo — pedir notas inline ao usuario (nao bloqueia) |
| Usuario rejeita preview (`n`) | Cancelar fluxo, preservar `plan-preview.json` para auditoria, marcar E5 = `cancelado_pelo_usuario` |
| Usuario solicita edicao (`editar`) | Coletar correcoes, re-invocar skill em mode=preview, re-apresentar plano |
| `plan-preview.json` ausente em mode=commit | ERRO: skill aborta com `"plan-preview.json nao encontrado. Execute mode=preview primeiro."` |
| `plan-preview.json` >24h em mode=commit | Alerta: estado ClickUp pode ter divergido. Recomendar re-preview |

## Uso como scheduled task

Este comando pode ser agendado para execucao automatica. Para verticais multi-subnivel, agendar uma task por subnivel:

```json
{
  "name": "Registro G2.3 {Vertical} {Subnivel}",
  "schedule": "0 8 * * 4",
  "command": "/m7-ritual-gestao:record-decisions {vertical} {subnivel}"
}
```

Cadencia padrao: quinta-feira 08:00 (registro apos ritual de quarta-feira). Em verticais com split, recomenda-se 1 task agendada por subnivel.
