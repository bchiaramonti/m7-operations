---
description: Gera materiais pre-ritual (HTML + briefing) para uma vertical. Equivalente a executar G2.3 E2 diretamente. Detecta automaticamente verticais multi-subnivel (split em 2+ cards com `metadata.subnivel` distinto), exigindo argumento `subnivel` quando aplicavel. Verifica existencia do WBR, invoca skill preparing-materials, salva outputs e atualiza CICLO.md.
argument-hint: <vertical> [subnivel]
disable-model-invocation: true
---

# m7-ritual-gestao:prepare-ritual

Gera materiais pre-ritual (apresentacao HTML + briefing MD/HTML A4) para uma vertical a partir do WBR disponivel.

## Input

- **vertical** (obrigatorio): `$ARGUMENTS[0]` — vertical a processar. Valores aceitos: `investimentos`, `credito`, `universo`, `seguros`, `consorcios`.
- **subnivel** (condicional): `$ARGUMENTS[1]` — quando a vertical tem 2+ cards de performance com `metadata.subnivel` distinto (ex: SEG `wl`/`re`), o argumento e **obrigatorio** para selecionar qual card processar. Vertical com card unico: argumento ignorado (warn se passado).

Se vertical nao informada, exibir: `"Uso: /m7-ritual-gestao:prepare-ritual <vertical> [subnivel]"` e parar.

## Steps

### 1. Validar vertical

1. Normalizar o input para lowercase.
2. Verificar se o valor esta na lista aceita: `investimentos`, `credito`, `universo`, `seguros`, `consorcios`.
3. Se valor invalido: exibir `"Vertical '{vertical}' invalida. Valores aceitos: investimentos, credito, universo, seguros, consorcios."` e parar.

### 1.5. Detectar cards e resolver subnivel (logica generica)

> **Regra:** este passo e **data-driven**. Nenhuma vertical hardcoded. Funciona para qualquer vertical futura que ganhe split em multiplos cards desde que cada card declare `metadata.subnivel`.

1. Capitalizar vertical para usar como nome de pasta: ex `seguros` → `Seguros`.
2. **Listar cards da vertical** via `Glob('**/Cards-de-Performance/{Vertical}/card_*.yaml')` (ignorar `_Historico/`).
3. Se 0 cards encontrados: exibir `"Nenhum Card de Performance encontrado para {vertical} em Cards-de-Performance/{Vertical}/. Crie/promova um card antes de gerar materiais."` e parar.
4. **Particionar cards em 2 grupos** (Read + parse YAML de cada):
   - `cards_consolidados`: lista de cards com `metadata.subnivel` ausente ou `null` (cards N1/N2/N3 consolidados — o caso historico).
   - `cards_split`: dict `subnivel → card_path` para cards com `metadata.subnivel` populado.
   - `subniveis_distintos = sorted(cards_split.keys())`.

5. **Decidir modo de selecao** (4 casos cobrindo todas as combinacoes):

   - **Caso A — argumento `$ARGUMENTS[1]` PASSADO**:
     - **Sub-caso A.1**: `$ARGUMENTS[1]` bate com chave em `cards_split` → `SUBNIVEL_ATIVO = $ARGUMENTS[1]`; `CARD_PATH = cards_split[SUBNIVEL_ATIVO]`. Prosseguir.
     - **Sub-caso A.2**: `$ARGUMENTS[1]` nao bate com nenhum subnivel → exibir `"Subnivel '{arg}' nao encontrado em {vertical}. Subniveis disponiveis: {subniveis_distintos}"` (se `cards_split` vazio: `"Vertical {vertical} nao tem cards com subnivel; argumento '{arg}' nao se aplica"`) e parar.

   - **Caso B — argumento AUSENTE e `cards_consolidados` >= 1**:
     - **Sub-caso B.1**: 1 card consolidado → `CARD_PATH` = esse card unico; `SUBNIVEL_ATIVO = None`. Prosseguir.
     - **Sub-caso B.2**: 2+ cards consolidados → escolher por preferencia de nivel: `N1 > N2 > N3 > N4 > N5`. Se ainda houver empate, escolher o de `metadata.version` mais alto (semver). Warn no log: `"Vertical {vertical} tem {N} cards consolidados; selecionado '{basename(CARD_PATH)}' por preferencia de nivel/versao."`. `SUBNIVEL_ATIVO = None`.

   - **Caso C — argumento AUSENTE, `cards_consolidados` vazio, e 2+ subniveis em `cards_split`**:
     - Exigir argumento. Exibir `"Vertical '{vertical}' tem {N} subniveis disponiveis: {subniveis_distintos}. Especifique: /m7-ritual-gestao:prepare-ritual {vertical} <subnivel>"` e parar.

   - **Caso D — argumento AUSENTE, `cards_consolidados` vazio, e 1 unico subnivel em `cards_split`**:
     - `CARD_PATH = cards_split[primeiro_subnivel]`; `SUBNIVEL_ATIVO = primeiro_subnivel`. Warn opcional: `"Vertical {vertical} tem apenas 1 card com subnivel ('{sub}'); selecionado automaticamente. Para explicitar, use: /m7-ritual-gestao:prepare-ritual {vertical} {sub}"`.

6. Armazenar para uso pelos passos seguintes:
   - `CARD_PATH` selecionado
   - `SUBNIVEL_ATIVO` (string ou `None`)

> **Compatibilidade**: o Caso B preserva o comportamento historico para verticais com cards consolidados (CON, INV — ate aparecerem cards split adicionais sem versao consolidada). O Caso C e o pattern novo para verticais como SEG (apenas split, sem consolidado).

### 2. Verificar existencia do WBR

> **Timestamps**: Sempre que este documento menciona `{timestamp}`, obter a hora real do sistema via `date '+%Y-%m-%dT%H:%M'` (Bash). NUNCA usar `00:00` ou estimar a hora — executar o comando `date` no momento exato do registro.

> **v6.5.0 (2026-05-13):** WBR agora e gerado por Card (nao por vertical) —
> alinhado com `m7-controle:run-weekly` que cria pasta `{vertical}-{subnivel}/`
> separada e nomeia WBR com sufixo `-{subnivel}` quando aplicavel. Lookup
> abaixo localiza o WBR especifico do Card que sera processado.

1. Obter data atual e calcular inicio da semana (segunda-feira).
2. Derivar `WBR_SOURCE_DIR` (canonical S3, tolerante a level-first): `02-Controle/**/{Vertical-cap}[-{subnivel}]/{YYYY-MM}/{YYYY-MM-DD}/wbr/` — o `**/` cobre o segmento de nivel `N{N}/` quando o repo estiver migrado (level-first ON) e o layout legado quando OFF; ignorar matches em `_Historico/`
   - Vertical-cap via `_vertical_display_with_subnivel(vertical, subnivel)` — ex: `Seguros-wl`, `Consorcios`, `PJ2`
   - Padrao de arquivo:
     - Com subnivel: `wbr-{vertical}-{SUBNIVEL_ATIVO}-*.md`
     - Sem subnivel: `wbr-{vertical}-*.md`
3. Buscar WBR via Glob no `WBR_SOURCE_DIR`, filtrado por arquivos cuja data esta dentro da semana atual.
4. Avaliar resultado:

   - **WBR encontrado e da semana atual**: prosseguir para Step 3.
   - **WBR encontrado mas da semana anterior**: exibir `"WBR encontrado e da semana passada ({data}). Deseja usar mesmo assim? [s/n]"` e aguardar resposta do usuario. Se `n`, parar. Se `s`, prosseguir com o WBR encontrado.
   - **WBR nao encontrado**: exibir `"WBR nao encontrado para {vertical}{sufixo} na semana {semana}. Execute /m7-controle:run-weekly {vertical}{sufixo} primeiro."` onde `{sufixo} = " {SUBNIVEL_ATIVO}"` se ativo senao "". E parar.

6. Armazenar caminho do WBR selecionado para uso pela skill.

### 3. Resolver `RITUAL_DIR` canonical (S3 2026-05-20+)

> **Mudanca S3:** outputs sao gerados DIRETAMENTE em `03-Rituais/` (sem staging
> intermediario em `output/`). Pattern canonical:
> `03-Rituais/{Vertical-cap}[-{subnivel}]/N{N}-{Cadencia}/{Periodo}/`
> onde Periodo = `{YYYY}-S{NN:02d}` (Semanal) ou `{YYYY-MM}` (Mensal),
> conforme `metadata.nivel` do Card.

1. Invocar o helper `resolve_ritual_path.py`:
   ```bash
   RITUAL_DIR=$(python3 {plugin_dir}/m7-ritual-gestao/skills/preparing-materials/scripts/resolve_ritual_path.py \
     --base-dir {DESEMPENHO_ROOT}/03-Rituais \
     --vertical {vertical} \
     --ciclo-date {YYYY-MM-DD} \
     --card-path {CARD_PATH} \
     --create)
   ```
   - Output: `{DESEMPENHO_ROOT}/03-Rituais/{Vertical-cap}[-{subnivel}]/N{N}-{Cadencia}/{Periodo}/`
   - `--create` cria as subpastas `apresentacao/`, `briefing/`, `ata/`
2. Manter label simbolico `OUTPUT_SUBDIR` apenas para logs/UI:
   - Se `SUBNIVEL_ATIVO` definido: `OUTPUT_SUBDIR = "{vertical}-{SUBNIVEL_ATIVO}"` (ex: `seguros-wl`)
   - Se ausente: `OUTPUT_SUBDIR = "{vertical}"`

### 4. Invocar skill preparing-materials

> **Regra arquitetural**: O command invoca **skills**, nunca agents diretamente. A skill decide internamente se executa no main thread ou delega a um agente.

1. Registrar inicio: append ao **Log de Execucao** do CICLO.md (se existir): `[{timestamp}] SISTEMA — Iniciando G2.3 E2 (preparing-materials) para {vertical}{sufixo}` onde `{sufixo} = " ({SUBNIVEL_ATIVO})" se ativo senao ""`.
2. Atualizar tabela Progresso do CICLO.md (se existir secao G2.3): `E2{ ` ou ` {sub}`} status: em_andamento`, `inicio: {timestamp}`. Detalhes do sufixo no Step 6.
3. Invocar skill `preparing-materials` com contexto:
   - `vertical` sendo processada
   - `subnivel` (string ou `None`) — passado tal qual recebido
   - `card_path` — selecionado no Step 1.5 (caminho absoluto do card unico)
   - Caminho do WBR selecionado
   - Caminho `RITUAL_DIR` (canonical S3) resolvido em Step 3
   - Data de referencia: `{YYYY-MM-DD}` (data atual)
   - Nomes esperados dos arquivos de saida em `{RITUAL_DIR}/`:
     - `apresentacao/ritual-{vertical}{-{subnivel}}-{YYYY-MM-DD}.html`
     - `briefing/briefing-{vertical}{-{subnivel}}-{YYYY-MM-DD}.md`
     - `briefing/briefing-{vertical}{-{subnivel}}-{YYYY-MM-DD}.html` (apenas Cards v2.0)

### 5. Verificar outputs gerados

1. Confirmar existencia dos artefatos esperados em `{RITUAL_DIR}/`:
   - `apresentacao/ritual-{vertical}{-{subnivel}}-{YYYY-MM-DD}.html`
   - `briefing/briefing-{vertical}{-{subnivel}}-{YYYY-MM-DD}.md`
   - `briefing/briefing-{vertical}{-{subnivel}}-{YYYY-MM-DD}.html` (Card v2.0)
2. Se HTML do deck nao gerado:
   - Registrar erro no CICLO.md (Anomalias + Log)
   - Exibir: `"Erro na geracao do HTML. Verifique os logs do material-generator."` e parar.
3. Se briefing MD nao gerado: registrar erro e parar.
4. Se Card v2.0 e briefing HTML A4 ausente: erro (gatekeeper SSoT bloqueia).

### 6. Atualizar CICLO.md

1. Localizar CICLO.md da vertical no diretorio de trabalho: `Glob('**/CICLO.md')` — selecionar o mais recente da vertical.
2. **Calcular sufixo da fase**:
   - Se `SUBNIVEL_ATIVO` definido: `FASE_SUFIXO = " {SUBNIVEL_ATIVO}"` (ex: ` wl`)
   - Se ausente: `FASE_SUFIXO = ""`
3. Se CICLO.md possui secao G2.3:
   - **Procurar linha existente** com fase `E2{FASE_SUFIXO}` (ex: `E2 wl`, ou apenas `E2` em vertical sem split).
   - **Se linha existe**: atualizar `status: concluido`, `fim: {timestamp}`, `artefato: {RITUAL_DIR}/apresentacao/ritual-{vertical}{-{subnivel}}-{YYYY-MM-DD}.html + briefing/briefing-{vertical}{-{subnivel}}-{YYYY-MM-DD}.md`
   - **Se linha NAO existe** (modo split, primeira execucao deste subnivel): adicionar 3 novas linhas para o subnivel:
     ```markdown
     | E2 {sub} | preparing-materials | concluido | {timestamp} | {timestamp} | {RITUAL_DIR}/apresentacao/ritual-{vertical}-{sub}-{YYYY-MM-DD}.html |
     | E3 {sub} | distributing-materials | pendente | -- | -- | -- |
     | E5 {sub} | recording-decisions | pendente | -- | -- | -- |
     ```
   - Append ao **Log de Execucao**: `[{timestamp}] SISTEMA — G2.3 E2{FASE_SUFIXO} concluido. Materiais pre-ritual gerados.`
4. Se CICLO.md nao possui secao G2.3, adicionar (com sufixo so se aplicavel):

```markdown
## G2.3 - Ritual de Gestao

| Fase | Skill | Status | Inicio | Fim | Artefato |
|------|-------|--------|--------|-----|----------|
| E2{FASE_SUFIXO} | preparing-materials | concluido | {timestamp} | {timestamp} | {RITUAL_DIR}/apresentacao/ritual-{vertical}{-{subnivel}}-{YYYY-MM-DD}.html |
| E3{FASE_SUFIXO} | distributing-materials | pendente | -- | -- | -- |
| E5{FASE_SUFIXO} | recording-decisions | pendente | -- | -- | -- |
```

### 7. Exibir resultado final

Exibir resumo ao usuario (incluir subnivel quando ativo):

```
Materiais pre-ritual gerados - {Vertical}{ - {SUBNIVEL_ATIVO}} - {YYYY-MM-DD}

Card processado: {basename(CARD_PATH)}
RITUAL_DIR canonical: {RITUAL_DIR}
Arquivos:
- {RITUAL_DIR}/apresentacao/ritual-{vertical}{-{subnivel}}-{YYYY-MM-DD}.html
- {RITUAL_DIR}/briefing/briefing-{vertical}{-{subnivel}}-{YYYY-MM-DD}.md
- {RITUAL_DIR}/briefing/briefing-{vertical}{-{subnivel}}-{YYYY-MM-DD}.html (Card v2.0)

WBR utilizado: {caminho-wbr}
Tempo: {duracao}
Proximo: /m7-ritual-gestao:approve-ritual {vertical}{SUBNIVEL_SUFIX}
        (distribui materiais ao Gestor via DM Slack — gate humano preview/commit)
```

## Tratamento de erros

| Erro | Tratamento |
|------|------------|
| Vertical nao informada | `"Uso: /m7-ritual-gestao:prepare-ritual <vertical> [subnivel]"` |
| Vertical invalida | `"Vertical '{vertical}' invalida. Valores aceitos: investimentos, credito, universo, seguros, consorcios."` |
| Nenhum card encontrado para a vertical | `"Nenhum Card de Performance encontrado para {vertical} em Cards-de-Performance/{Vertical}/. Crie/promova um card antes de gerar materiais."` |
| Vertical multi-subnivel sem subnivel passado | `"Vertical '{vertical}' tem {N} subniveis disponiveis: {lista}. Especifique: /m7-ritual-gestao:prepare-ritual {vertical} <subnivel>"` |
| Subnivel passado nao corresponde a card existente | `"Subnivel '{arg}' nao encontrado em {vertical}. Subniveis disponiveis: {lista}"` |
| Subnivel passado em vertical sem split | Warn: `"Vertical {vertical} tem apenas 1 card; argumento '{arg}' ignorado."`; processa normalmente |
| WBR nao encontrado | `"WBR nao encontrado para {vertical} na semana {semana}. Execute /m7-controle:run-weekly {vertical} primeiro."` |
| WBR desatualizado (semana anterior) | `"WBR encontrado e da semana passada ({data}). Deseja usar mesmo assim? [s/n]"` |
| Erro na geracao do HTML | Registrar erro no CICLO.md, exibir detalhes |
| CICLO.md nao encontrado | Prosseguir sem atualizacao de ciclo; exibir aviso `"CICLO.md nao encontrado. Outputs gerados mas progresso nao registrado."` |

## Uso como scheduled task

Este comando pode ser agendado para execucao automatica. Para verticais multi-subnivel, agendar uma task por subnivel:

```json
{
  "name": "Materiais G2.3 {Vertical} {Subnivel}",
  "schedule": "0 8 * * 2",
  "command": "/m7-ritual-gestao:prepare-ritual {vertical} {subnivel}"
}
```

Cadencia padrao: terca-feira 08:00 (materiais prontos antes do ritual). Em verticais com split, recomenda-se 1 task agendada por subnivel.
