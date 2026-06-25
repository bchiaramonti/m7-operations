---
name: preparing-materials
description: >-
  G2.3-E2: Generates ritual materials (HTML deck + Briefing MD + Briefing HTML A4)
  from the WBR produced by m7-controle. Orchestrates material-generator agent to
  build a per-specialist HTML presentation and a consultant-style briefing in
  two variants (digital MD + printable A4 HTML) for the ritual conductor. Use
  when /m7-ritual-gestao:prepare-ritual is invoked or when G2.3 E2 is the
  current pipeline step.

  <example>
  Context: WBR da vertical concluido (m7-controle E6 = completo no CICLO.md)
  user: "/m7-ritual-gestao:prepare-ritual consorcios"
  assistant: Locates the latest WBR, delegates to material-generator, produces deck HTML + briefing MD + briefing HTML A4
  </example>
user-invocable: false
---

# Preparar Materiais Pre-Ritual (G2.3-E2)

Transforma o WBR em tres materiais consumiveis pelo gestor: um **deck HTML autocontido** (slides para projecao e impressao PDF), um **briefing MD** (guia digital de preparacao do condutor) e um **briefing HTML A4** (variante imprimivel do briefing).

> **Principio:** o WBR e a unica fonte de verdade. Deck e briefing sao derivacoes visuais e textuais — nenhum numero e calculado ou inventado nesta etapa.

---

## Dependencias

| Recurso | Caminho | Tipo |
|---------|---------|------|
| Regras dos slides do deck | [references/slide-structure.md](references/slide-structure.md) | Referencia |
| Regras do briefing (5 secoes + 14-item checklist) | [references/briefing-structure.md](references/briefing-structure.md) | Referencia |
| Filtros v2.0 + 3 gatekeepers SSoT | [references/migration-v2.md](references/migration-v2.md) | Referencia |
| **Schema completo de `Card.apresentacao`** (overrides_ritual, projection_overrides, suppress_in_ritual, anomalias_custom, destaques_positivos_custom, pa_manual_append, sem_esp_ratio, responsavel_externo_aliases, n5_by_esp, regras Sem Especialista universal cinza) | [references/card-apresentacao-schema.md](references/card-apresentacao-schema.md) | **Referencia** |
| Template HTML do deck | [templates/ritual.tmpl.html](templates/ritual.tmpl.html) | Template |
| Template MD do briefing | [templates/ritual-briefing.tmpl.md](templates/ritual-briefing.tmpl.md) | Template |
| Template HTML A4 do briefing | [templates/ritual-briefing.tmpl.html](templates/ritual-briefing.tmpl.html) | Template |
| Gold standard deck (CON N3 S18) | [examples/ritual-deck-validado.example.html](examples/ritual-deck-validado.example.html) | Exemplo |
| Gold standard briefing MD | [examples/ritual-briefing-validado.example.md](examples/ritual-briefing-validado.example.md) | Exemplo |
| Gold standard briefing HTML A4 | [examples/ritual-briefing-validado.example.html](examples/ritual-briefing-validado.example.html) | Exemplo |
| Card de Performance | `{CARDS_DIR}/{Vertical}/card_*.yaml` | Contexto externo |
| Agent executor | `material-generator` (agents/material-generator.md) | Agent |
| Helper resolve_ritual_path | [scripts/resolve_ritual_path.py](scripts/resolve_ritual_path.py) | Script |

---

## Entry criteria

Antes de iniciar, verificar:

- [ ] Card(s) de Performance da vertical localizado(s) em `{CARDS_DIR}/{Vertical}/card_*.yaml`
- [ ] CICLO.md existe no cycle folder e E6 (consolidating-wbr) esta marcado como concluido
- [ ] WBR estruturado disponivel em `{cycle_folder}/wbr/wbr-{vertical}-{data}.md` (consolidado por vertical — mesmo WBR alimenta todos os subniveis quando vertical e split)
- [ ] **`{cycle_folder}/dados/raw/clickup-tasks-{vertical}.json` disponivel** (gerado em E2 Fase 1.5 via ClickUp MCP — fonte primaria de Slide 4 e Slide 5)
- [ ] **`{cycle_folder}/analise/action-report.md` disponivel** (gerado em E4 — contexto narrativo de aging/urgencia)
- [ ] **Modo subnivel resolvido** (Fase 1.0): se a vertical tem 2+ cards com `metadata.subnivel` distinto, o argumento `subnivel` deve ser informado pelo command. A skill rejeita execucao ambigua.

Se qualquer criterio falhar, interrompa e reporte ao usuario. Em particular: se o JSON ClickUp ou o action-report estiver ausente, retornar ao pipeline G2.2 antes de prosseguir — o Slide 5 nao tem fonte alternativa confiavel apos a descontinuacao do `plano-de-acao.csv` (2026-04-30).

---

## Workflow

### Fase 1.0 — Resolver subnivel e filtrar Card (logica generica)

> **Regra:** este passo e **data-driven**. Funciona para qualquer vertical (sem split / com split puro / com cards consolidados + cards split). Nao ha lista hardcoded de "verticais que tem subnivel".

1. Receber `vertical` (obrigatorio) e `subnivel` (opcional, pode ser `None`) como inputs.
2. Mapear vertical → codigo: consorcios=`Consorcios`, investimentos=`Investimentos`, credito=`Credito`, seguros=`Seguros`, universo=`Universo`.
3. **Listar cards da vertical**: `Glob('{CARDS_DIR}/{Vertical}/card_*.yaml')` (ignorar `_Historico/`).
4. Se 0 cards: avisar `"Card de Performance nao encontrado para {vertical}. Materiais serao gerados sem contexto organizacional."` e prosseguir SEM card (modo legado).
5. **Particionar cards em 2 grupos** (Read + parse YAML de cada):
   - `cards_consolidados`: lista de cards com `metadata.subnivel` ausente/`null` (cards N1/N2/N3 consolidados — caso historico de CON, INV).
   - `cards_split`: dict `subnivel → card_path` para cards com `metadata.subnivel` populado.
   - `subniveis_distintos = sorted(cards_split.keys())`.

6. **Decidir modo de selecao** (4 casos cobrindo todas as combinacoes — identico ao Step 1.5 dos commands):

   - **Caso A — `subnivel` PASSADO**:
     - A.1: `subnivel` bate com chave em `cards_split` → `SUBNIVEL_ATIVO = subnivel`; `CARD_PATH = cards_split[subnivel]`.
     - A.2: nao bate → erro `"Subnivel '{subnivel}' nao encontrado em {vertical}. Subniveis disponiveis: {subniveis_distintos}"` (se `cards_split` vazio: `"Vertical {vertical} nao tem cards com subnivel; argumento '{subnivel}' nao se aplica"`) e abortar.

   - **Caso B — `subnivel` AUSENTE e `cards_consolidados` >= 1**:
     - B.1: 1 card consolidado → `CARD_PATH = esse card`; `SUBNIVEL_ATIVO = None`.
     - B.2: 2+ cards consolidados → escolher por preferencia de nivel (`N1 > N2 > N3 > N4 > N5`); empate → maior `metadata.version` (semver). Warn no log: `"Vertical {vertical} tem {N} cards consolidados; selecionado '{basename(CARD_PATH)}' por preferencia de nivel/versao."`. `SUBNIVEL_ATIVO = None`.

   - **Caso C — `subnivel` AUSENTE, `cards_consolidados` vazio, 2+ subniveis em `cards_split`**:
     - Erro `"Vertical '{vertical}' tem {N} subniveis disponiveis: {subniveis_distintos}. A skill exige argumento subnivel. Reinvoque /m7-ritual-gestao:prepare-ritual {vertical} <subnivel>."` e abortar.

   - **Caso D — `subnivel` AUSENTE, `cards_consolidados` vazio, 1 unico subnivel em `cards_split`**:
     - `CARD_PATH = cards_split[primeiro_subnivel]`; `SUBNIVEL_ATIVO = primeiro_subnivel`. Warn opcional.

7. Armazenar `CARD_PATH` (caminho do card unico a processar) e `SUBNIVEL_ATIVO` (string ou `None`) para uso pelas fases seguintes. **Toda a skill processa APENAS o card unico selecionado** — nunca merge multi-card.

**Compatibilidade**:
- Caso B preserva comportamento historico para verticais com cards consolidados (CON tem 1 card; INV tem cards N1/N2 consolidados + N3 split — INV pega N1/N2 quando arg ausente).
- Caso C e o pattern novo para verticais como SEG (split puro, sem cards consolidados).
- Casos A e D permitem drill-down explicito em qualquer vertical com cards split, mesmo havendo cards consolidados.

### Fase 1 — Ler Card de Performance e WBR

> **Card ANTES do WBR:** o Card define QUEM sao os especialistas e QUAIS indicadores importam. Essa informacao guia a leitura do WBR, nao o contrario.

1. Read o Card em `CARD_PATH` (resolvido na Fase 1.0). Extrair:
   - lista de especialistas (de `apresentacao.responsaveis[]`),
   - `kpi_references[]`,
   - `logica_de_analise`,
   - `distribuicao`,
   - `briefing_customization` completo,
   - `metas_ppi`,
   - `metadata.subnivel` (caso ainda nao registrado),
   - **`apresentacao.*` completo** (rodadas 6+7+7.5+7.6+7.7 — ver [references/card-apresentacao-schema.md](references/card-apresentacao-schema.md)): `responsaveis[].squad` whitelist, `overrides_ritual` (N1/N2/N5 receita+volume), `projection_overrides`, `projecao_proximo_mes`, `suppress_in_ritual`, `destaques_positivos_custom`, `anomalias_custom`, `pa_manual_append`. Tambem `metadata.{total_label, responsaveis_n2, assessor_aliases, responsavel_externo_aliases}` e em `kpi_references[].matrix_views[]`: `compute_meta`, `n2_compute_meta`, `sem_esp_ratio`. Todos opcionais — ausentes = comportamento legado.
2. **Detectar versao do briefing_customization** no Card selecionado:
   - `briefing_customization.versao: "2.0"` → fluxo aberto v2.0 (filtros por sinal/contexto, briefing MD + HTML A4)
   - Versao ausente ou `"1.0"` → fluxo legado (apenas MD prescritivo). Avisar usuario: `Card sem briefing_customization v2.0 — usando fluxo legado. Considere atualizar via /m7-metas:creating-cards`
   - **Em vertical multi-subnivel**: a versao e detectada APENAS no card do subnivel selecionado. Outros cards da mesma vertical podem estar em versoes diferentes — sao processados em invocacoes separadas (1 ritual = 1 card = 1 detec deteccao de versao).
3. Localizar o cycle folder mais recente:
   - Glob para `**/wbr/wbr-{vertical}-*.md` nos diretorios de output
   - Selecionar o mais recente por data no nome do arquivo
4. Read CICLO.md do cycle folder
5. Confirmar que E6 (consolidating-wbr) esta completo (G2.2)
6. Extrair metadados: `vertical`, `data`, `checkpoint_label`

### Fase 2 — Resolver caminhos

Montar os caminhos absolutos necessarios. **`OUTPUT_DIR` e parametrizado por subnivel** quando ativo:

```
WBR_PATH            = {cycle_folder}/wbr/wbr-{vertical}-{data}.md      # consolidado por vertical (mesmo WBR para todos os subniveis)
CYCLE_FOLDER        = {cycle_folder}/
CARDS_DIR           = ~/Library/CloudStorage/OneDrive-MULTI7CAPITALCONSULTORIALTDA/desempenho/02-Controle/Cards-de-Performance
CARD_PATH           = resolvido na Fase 1.0 (card unico do subnivel selecionado, ou unico card da vertical)
SUBNIVEL_ATIVO      = string (ex: "wl", "re") quando vertical multi-subnivel; None quando single-card
DADOS_PATH          = {cycle_folder}/dados/dados-consolidados-{vertical}.json
CLICKUP_TASKS_PATH  = {cycle_folder}/dados/raw/clickup-tasks-{vertical}.json     # SoT G2.2 do Plano de Acao (fonte do Slide 5)
ACTION_REPORT_PATH  = {cycle_folder}/analise/action-report.md                    # contexto narrativo Slide 4/5 (de E4)
PREV_WBR_PATH       = <auto-resolvido pelo agent na Fase 1.7 via glob nas pastas-irmas
                       da vertical; null quando for o primeiro ciclo>
SKILL_DIR           = {plugins_dir}/m7-ritual-gestao/skills/preparing-materials

# MUDANCA 2026-05-12: eliminada pasta {cycle_folder}/output/ em 02-Controle.
# Outputs (deck + briefings) sao gerados DIRETAMENTE em 03-Rituais agora.
# Estrutura LEVEL-FIRST (default ON desde 2026-06-09), RESOLVIDA via resolve_ritual_path.py:
# 03-Rituais/N{N}/{Vertical-cap}[-{subnivel}]/{Cadencia}/{Periodo}/{apresentacao,ata,briefing}/
#   apresentacao/  → deck HTML do ritual (gerado por preparing-materials)
#   ata/           → ata MD/HTML/PDF (gerado por recording-decisions)
#   briefing/      → briefing MD + HTML A4 (gerado por preparing-materials)
RITUAIS_BASE_DIR    = {DESEMPENHO_ROOT}/03-Rituais
NIVEL               = metadata.nivel do Card (N1/N2/N3/...)
RITUAL_DIR          = resolve_ritual_path(RITUAIS_BASE_DIR, vertical, ciclo_date, card_path)
                      # = {RITUAIS_BASE_DIR}/N{N}/{Vertical-cap}[-{subnivel}]/{Cadencia}/{Periodo}/ (NUNCA montar a mao)

# Outputs ficam em subpastas dedicadas (substituem OUTPUT_DIR legado):
APRESENTACAO_DIR    = {RITUAL_DIR}/apresentacao/    # deck HTML
BRIEFING_DIR        = {RITUAL_DIR}/briefing/        # briefings (MD + HTML A4)
ATA_DIR             = {RITUAL_DIR}/ata/             # ata (gerenciado por recording-decisions, nao por esta skill)

# COMPAT LEGACY (deprecated 2026-05-12, manter ate ciclos pre-2026-05-12 serem migrados):
# OUTPUT_DIR_LEGADO  = {cycle_folder}/output/{vertical}{-{SUBNIVEL_ATIVO}}/  # fallback se RITUAL_DIR nao puder ser criado
```

**Filenames inalterados** dentro de `OUTPUT_DIR` (folder ja isola subniveis): `ritual-{vertical}-{data}.html`, `briefing-{vertical}-{data}.md`, `briefing-{vertical}-{data}.html`.

> `DADOS_PATH` e o JSON consolidado do m7-controle (E2) com dados hierarquicos N1→N5. Usado pelo material-generator para quebras granulares (por assessor, equipe, squad) nos slides de Analise e Projecao. Se o arquivo nao existir, o agente usa o WBR narrativo como fallback.
>
> `CLICKUP_TASKS_PATH` e a fonte primaria do **Slide 5 (Plano de Acao)** e do **Slide 4 (Status PA)**. Substitui o legado `plano-de-acao.csv`. Filtros canonicos (Vertical, exclusao subtasks, Responsavel Externo) ja foram aplicados em E2 Fase 1.5 via ClickUp MCP.
>
> `ACTION_REPORT_PATH` traz aging/urgencia/eficacia consolidados em E4 — usado como contexto narrativo dos Slides 4 e 5 (categorias Em dia/Atrasada/Critica/Sem prazo, taxa conclusao 30d, volume/receita em risco).
>
> `PREV_WBR_PATH` alimenta a coluna **"Δ vs S{prev}"** dos slides Dashboard por especialista (slides 6, 9, … no template editorial v3.0) — o agent compara Realizado da Secao 1.5 atual vs anterior, calcula delta, e renderiza seta literal (cinza) + valor absoluto colorido (verde/vermelho/cinza) com base no `direction` do indicador no Card. Se for o primeiro ciclo da vertical, a coluna toda renderiza como vazia.

Verificar que cada caminho existe (`ls`). `PREV_WBR_PATH` nao precisa de `ls` aqui — o agent resolve e valida na Fase 1.7. Se `CLICKUP_TASKS_PATH` nao existir, registrar em CICLO.md > Anomalias e PARAR — pedir para o usuario re-rodar E2 Fase 1.5 antes de prosseguir (Slide 5 nao tem fonte alternativa confiavel).

### Fase 3 — Rodar build_deck.py + delegar narrativos ao agent

> **Arquitetura nova (refactor 2026-05-05):** geracao do HTML do deck e DETERMINISTICA via script Python (`scripts/build_deck.py`). Agente NAO gera HTML do zero — gera apenas blocos narrativos curtos via Edits cirurgicos. Razao: deck completo (1.2MB com fontes b64) excede o output budget de 32k tokens do agent em uma unica Write call.

**3.a — Executar build_deck.py (deterministico)**

```bash
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python3 {SKILL_DIR}/scripts/build_deck.py \
  --wbr-data-json {WBR_DATA_JSON_PATH} \
  --card {CARD_PATH} \
  --clickup-tasks {CLICKUP_TASKS_PATH} \
  --action-report {ACTION_REPORT_PATH} \
  --dados-consolidados {DADOS_PATH} \
  --skill-dir {SKILL_DIR} \
  --output {OUTPUT_DIR}/ritual-{vertical}-{data}.html \
  [--prev-wbr-data-json {PREV_WBR_DATA_JSON_PATH}]
```

> `WBR_DATA_JSON_PATH` = `{cycle_folder}/wbr/wbr-{vertical}-{data}.data.json` (canonical SoT do E6).
> Script le este JSON + Card YAML + ClickUp tasks + action-report MD + assets (`templates/assets/*.b64` + `deck-stage.js`) e renderiza ~62 placeholders deterministicamente.
> Output: HTML autocontido com 7+3*N sections (todas data-correct), ~1.2MB, gerado em <2 segundos.
> ~16 blocos narrativos ficam como `[TODO: ...]` placeholders amarelos no HTML — preenchidos na Fase 3.b.

**3.b — Delegar APENAS narrativas ao material-generator**

O agente recebe um prompt curto pedindo Edits cirurgicos no HTML ja gerado:

```
O deck foi gerado em {OUTPUT_DIR}/ritual-{vertical}-{data}.html via build_deck.py.
Ele contem ~16 blocos `[TODO: ...]` em fundo amarelo (rgba #fff3a0) que voce deve preencher
via Edit calls cirurgicos. Cada TODO tem label + hint indicando o que renderizar.

Caminhos para contexto:
- HTML a editar: {OUTPUT_DIR}/ritual-{vertical}-{data}.html
- WBR_DATA_JSON: {WBR_DATA_JSON_PATH} (SoT — leia para extrair narrativas)
- WBR_PATH (prosa): {WBR_PATH}
- CARD_PATH: {CARD_PATH} (briefing_customization v2.0 com armadilhas/decisoes)
- DADOS_PATH: {DADOS_PATH} (quebras N5 por assessor)
- ACTION_REPORT_PATH: {ACTION_REPORT_PATH}

TODOs tipicos:
- PA Status callout body (1 frase com diagnostico do plano)
- PA Vencendo foco (apontar 1-3 PAs criticas)
- Por especialista (x N):
  - Riscos: 3-4 risk-items (<div class="risk-item">) extraidos do WBR
  - Rank rows squad: 1 .rank-row por assessor (ler DADOS_PATH para N5)
  - Rank rows outside: assessores fora do squad mapeado
  - Summary cards: 5 .summary-card + 1 callout (concentracao, cobertura, estagnacao, sem ativ)
  - Funnel SVG: SVG inline 720x380 com N estagios (pipeline_stages do Card)
  - Destaque: top deals + conversao alta
  - Estagnacao: bloqueios + deals parados

Faca 1 Edit por TODO. Cada Edit substitui o `<span>...[TODO:...]...</span>` pelo HTML real.
NAO gere o deck inteiro. NAO regenere slides ja preenchidos.

Apos preencher os TODOs, EXECUTE {SKILL_DIR}/scripts/resolve_ritual_path.py para resolver
RITUAL_DIR final em RITUAIS_BASE_DIR/{Vertical}/{Cadencia}/[{SubArea}/]{Periodo}/. Copie:
  Apresentacao/ <- ritual-*.html
  Briefing/ <- briefing-*.md e .html
Crie Ata/ vazia se nao existir. Preserve Ata/ e dados/ existentes.
Valide gatekeeper #15 (existencia + byte-equal entre staging e final).
```

**3.c — Briefing (paralelo)**

Briefing MD + HTML A4 sao gerados pelo agente diretamente (textos curtos: 300-1200 palavras MD, ~400 linhas HTML A4 — cabem no output budget). O agente le `templates/ritual-briefing.tmpl.md` + `templates/ritual-briefing.tmpl.html` + WBR data JSON + Card briefing_customization e preenche os placeholders.

> Se versao briefing_customization e `"2.0"`, aplicar filtros por `sinal_generico_no_wbr` (armadilhas) e `contexto_tipico` (decisoes). Se `"1.0"`, fluxo legado prescritivo.

### Fase 4 — Verificar outputs

Apos o agent concluir, verificar:

#### Checks de existencia

| Verificacao | Como |
|-------------|------|
| Deck HTML existe | `ls {OUTPUT_DIR}/ritual-{vertical}-{data}.html` |
| Briefing MD existe | `ls {OUTPUT_DIR}/briefing-{vertical}-{data}.md` |
| Briefing HTML A4 existe (v2.0) | `ls {OUTPUT_DIR}/briefing-{vertical}-{data}.html` |
| Deck tem slides | Regex `^<section[^>]*data-label` (anchored em start-of-line) no deck HTML → exatamente `7 + 3*N` para N especialistas. Anchor evita false positives nos exemplos JSDoc do deck-stage.js inlineado |
| Briefing completo | Read briefing e verificar que as 5 secoes nao estao vazias |
| Dados consistentes | Spot-check: comparar 3 valores entre WBR e briefing (devem ser identicos) |
| Font sizes compliant | Grep `font-size:\s*[1-7]px` no deck → 0 matches |
| Cores on-brand | Grep hex fora da paleta M7-2026 → 0 matches |
| Sem bold keyword | Grep `font-weight: bold` no conteudo dos iframes → 0 matches |
| Lime nao como texto | Sem `color: #eef77c` em elementos sobre fundo claro (`#fffdef`) |

#### Coerencia briefing↔slide (3 gatekeepers SSoT — apenas v2.0)

Detalhes em [references/migration-v2.md](references/migration-v2.md) Secao 4.

| Item | Verificacao | Falha BLOQUEIA publicacao |
|------|-------------|---------------------------|
| **#7 Rastreabilidade** | Cada `Sinal observado` das armadilhas (campo interno `sinal_generico_no_wbr`) aparece literalmente no WBR | sim |
| **#10 Coerencia decisoes** | Numero D de decisoes no briefing == numero D de next-cards no Slide Encerramento (último, posição `7 + 3*N` — mesmos titulos) | sim |
| **#12 Coerencia tempo** | Total de minutos no Roteiro == total na Agenda do Slide 2 (composição default `25 + 15*N` min: T_VISAO=8 + T_OPERACAO=10 + 15×N + T_SINTESE=4 + T_FECHAMENTO=3) | sim |

Se qualquer gatekeeper falhar, o agent deve corrigir e re-validar antes de salvar.

#### Gatekeeper #15 — Replicacao para `03-Rituais/`

| Item | Verificacao | Falha BLOQUEIA publicacao |
|------|-------------|---------------------------|
| **#15 Replicacao 03-Rituais** | `{RITUAL_DIR}/` existe; `Apresentacao/`, `Briefing/`, `Ata/` criadas; arquivos copiados com tamanho identico ao staging (byte-equal) | sim |

Verificacao programatica:

```pseudocode
ritual_dir = resolve_ritual_path(vertical, ciclo_date, card_path)
assert (ritual_dir / "Apresentacao" / f"ritual-{v}-{d}.html").exists()
assert (ritual_dir / "Briefing"     / f"briefing-{v}-{d}.md").exists()
if versao == "2.0":
    assert (ritual_dir / "Briefing" / f"briefing-{v}-{d}.html").exists()
assert (ritual_dir / "Ata").is_dir()  # pode estar vazia
# byte-equal vs staging
for filename in os.listdir(staging):
    if filename.endswith((".html", ".md")):
        assert filecmp.cmp(staging / filename, ritual_dir / subdir / filename, shallow=False)
```

#### Comparacao com `examples/`

Verificacoes estruturais (nao de conteudo):

- Estrutura de slides do deck bate com `examples/ritual-deck-validado.example.html` (`7 + 3*N` `<section data-label`)
- Briefing MD tem 5 `## ` headers correspondentes a Veredicto / O Que Provocar / Armadilhas / Decisoes / Roteiro
- Briefing HTML A4 (v2.0) tem 5 `<div class="section-title">` correspondentes
- Tipografia: `"twkEverett"` referenciada nos 3 outputs

#### Smoke-check pos-render (P2.4, 2026-06-18)

Apos gerar o deck (e o briefing HTML), rodar o smoke-check para pegar render
quebrado que so o humano percebe abrindo o arquivo (placeholder `{{...}}` nao
substituido, `TODO` residual, "SEM DADOS", celula `None`/`NaN`, currency vazia,
mojibake):

```bash
python3 {plugin}/skills/preparing-materials/scripts/smoke_check_deck.py \
  --deck {RITUAL_DIR}/apresentacao/ritual-{vertical}-{data}.html \
  --briefing {RITUAL_DIR}/briefing/briefing-{vertical}-{data}.html
```

Exit 1 = sinal HARD (placeholder/TODO — render quebrado, corrigir antes de
distribuir). Sinais SOFT (None/SEM DADOS/mojibake) saem em exit 0 (advisory);
use `--strict` para trata-los como falha em execucao unattended.

### Fase 5 — Atualizar CICLO.md

> **Sufixo dinamico:** quando `SUBNIVEL_ATIVO` esta definido, todas as linhas G2.3 deste subnivel ganham sufixo (ex: `E2 wl`, `E5 wl`). Quando ausente (single-card), as linhas ficam sem sufixo (`E2`, `E5`) — preservando o formato historico.

1. Calcular `FASE_SUFIXO`:
   - `SUBNIVEL_ATIVO` definido: `FASE_SUFIXO = " {SUBNIVEL_ATIVO}"` (note o espaco inicial)
   - `SUBNIVEL_ATIVO == None`: `FASE_SUFIXO = ""`

2. Adicionar ou atualizar a secao G2.3 no CICLO.md. Em verticais multi-subnivel, **cada subnivel gera 3 linhas proprias** (E2/E3/E5 com sufixo) — quando o segundo subnivel for processado, suas linhas serao adicionadas independentemente das do primeiro:

```markdown
## G2.3 — Rituais de Gestao

| Fase | Skill | Status | Inicio | Fim | Artefato |
|------|-------|--------|--------|-----|----------|
| E2{FASE_SUFIXO} | preparing-materials | concluido | {timestamp} | {timestamp} | output/{OUTPUT_SUBDIR}/ritual-{vertical}-{data}.html |
| E3{FASE_SUFIXO} | (distribuicao manual) | pendente | -- | -- | -- |
| E5{FASE_SUFIXO} | recording-decisions | pendente | -- | -- | -- |
```

Append ao Log de Execucao:

```
[{timestamp}] SKILL:preparing-materials — G2.3 E2{FASE_SUFIXO} concluido. Card processado: {basename(CARD_PATH)}. Versao briefing_customization: {versao_detectada}. PREV_WBR_PATH: {basename(prev) ou "null (primeiro ciclo)"}. Artefatos: ritual-{vertical}-{data}.html, briefing-{vertical}-{data}.md, briefing-{vertical}-{data}.html (se v2.0).
```

---

## Exit criteria

- [ ] `ritual-{vertical}-{data}.html` (deck) gerado em `{OUTPUT_DIR}/`
- [ ] `briefing-{vertical}-{data}.md` (briefing digital) gerado em `{OUTPUT_DIR}/`
- [ ] `briefing-{vertical}-{data}.html` (briefing A4 imprimivel) gerado em `{OUTPUT_DIR}/` — apenas v2.0
- [ ] Deck com 7 + 3*N slides totais (5 fixos pré: Capa/Agenda/Matriz/PA Status/PA Vencendo; 3 por especialista: Dashboard/Análise/Pipeline; 2 fixos pós: Consolidado/Encerramento)
- [ ] **Slide Dashboard (6, 9, …) com coluna "Δ vs S{prev}"** preenchida quando PREV_WBR_PATH foi resolvido — seta literal cinza + valor colorido por sentido. Células vazias quando primeiro ciclo da vertical ou indicador novo
- [ ] **Slide 3 (Matriz) sem dot semáforo** — coloração reside no `.num` via classe `.cell.{good|warn|bad|mute}` (regra 3-tier). Coluna Total = soma das demais. Cabeçalhos `KPI · Indicadores de Resultado` e `PPI · Indicadores de Funil`
- [ ] **Slide Consolidado (pré-último, posição `6 + 3*N`)** sempre gerado: 3 KPI tiles N3 + Receita por direto (omitido se N=1) + Top 3 riscos + Sinais positivos
- [ ] **Indicador Estagnadas no Matriz/Dashboard** com `% das ativas` como linha principal (semáforo 3-tier sobre `pct_ativas_max`) e `qty + R$ + dias` em sublabels (TODO-MIGRACAO Item 5)
- [ ] **Dashboard com meta N2 individual** quando canonical JSON tem `n2.{especialista}.meta` (TODO-MIGRACAO Item 6) — Cards com `metas_ppi.{indicador}.por_especialista`
- [ ] Briefing com todas as 5 secoes preenchidas
- [ ] Dados no deck e briefing identicos ao WBR (single source of truth)
- [ ] **Gatekeepers SSoT** (v2.0): rastreabilidade armadilha→WBR, decisoes briefing==slide 10, tempo briefing==slide 2
- [ ] **Gatekeeper #15 — Replicacao 03-Rituais**: `{RITUAL_DIR}/` resolvido via `resolve_ritual_path.py`; `Apresentacao/`, `Briefing/`, `Ata/` criadas; artefatos copiados byte-equal do staging
- [ ] CSS compliance: 0 fontes < 8px, 0 cores fora da paleta, 0 `font-weight: bold`
- [ ] Total entre 50-90 min, 300-1200 palavras no briefing
- [ ] CICLO.md atualizado com G2.3 E2 = concluido + versao detectada no log

---

## Outputs

Cada execucao produz tres artefatos em **dois destinos**:

### Staging (interno ao pipeline G2.2/G2.3 — auditoria)

| Output | Formato | Caminho | Quando |
|--------|---------|---------|--------|
| Deck do Ritual | HTML | `{OUTPUT_DIR}/ritual-{vertical}-{data}.html` | sempre |
| Briefing MD | MD | `{OUTPUT_DIR}/briefing-{vertical}-{data}.md` | sempre |
| Briefing HTML A4 | HTML | `{OUTPUT_DIR}/briefing-{vertical}-{data}.html` | apenas Cards v2.0 |

### Final (consumido pelo gestor — `03-Rituais/`)

> Canonical S3 (2026-05-20+): subpastas lowercase (`apresentacao/`, `briefing/`, `ata/`, `distribuicao/`).

| Output | Caminho |
|--------|---------|
| Deck do Ritual | `{RITUAL_DIR}/apresentacao/ritual-{vertical}{-{subnivel}}-{data}.html` |
| Briefing MD | `{RITUAL_DIR}/briefing/briefing-{vertical}{-{subnivel}}-{data}.md` |
| Briefing HTML A4 | `{RITUAL_DIR}/briefing/briefing-{vertical}{-{subnivel}}-{data}.html` |
| Pasta Ata | `{RITUAL_DIR}/ata/` (criada vazia, preenchida em G2.3-E5) |
| Pasta Distribuicao | `{RITUAL_DIR}/distribuicao/` (preview JSONs do bot Slack) |
| dados/ (opcional) | `{RITUAL_DIR}/dados/` (raw copies para rastreabilidade) |

---

## Destino dos artefatos

Os artefatos gerados (deck + briefings) vao **DIRETO** para o destino final em `03-Rituais/` (level-first); o staging em `02-Controle` e **legado (deprecated 2026-05-12)**:

### Staging (legado/deprecated) — `02-Controle/N{N}/{Vertical}/{ciclo}/output/{vertical}/`

- Mantido para rastreabilidade e auditoria do ciclo G2.2 (intermediario do pipeline)
- Mesmo nome de arquivo dos artefatos finais (sincronizar)
- Nao e o caminho consultado pelo gestor durante o ritual

### Final — `03-Rituais/N{N}/{Vertical-cap}[-{subnivel}]/{Cadencia}/{Periodo}/` (level-first, default ON 2026-06-09)

> **Level-first (2026-06-09):** nivel = pasta-pai (`N{N}/`), depois vertical+subnivel concatenado, depois `{Cadencia}` (`Semanal`/`Mensal`, SEM o prefixo `N{N}-`), depois Periodo (ISO week ou YYYY-MM). Helper `resolve_ritual_path.py` gera o path (passe `--legacy-flat` para o layout antigo `{Vertical}/N{N}-{Cadencia}/`).

Estrutura interna obrigatoria (lowercase, pos-S3):

```
{RITUAL_DIR}/
├── apresentacao/
│   └── ritual-{vertical}{-{subnivel}}-{data}.html
├── briefing/
│   ├── briefing-{vertical}{-{subnivel}}-{data}.md
│   └── briefing-{vertical}{-{subnivel}}-{data}.html  (apenas v2.0)
├── ata/                                  # criada vazia; preenchida em G2.3-E5
├── distribuicao/                         # preview JSONs do bot Slack (G2.3-E3/E5)
└── dados/                                # opcional: cópia de wbr.md, card YAML, JSONs
```

### Resolucao de path

| Componente | Origem |
|------------|--------|
| `Vertical-cap[-{sub}]` | parametro do pipeline + subnivel concatenado (`seguros`+`wl` → `Seguros-wl`) |
| `N{N}/` (pasta-pai) + `{Cadencia}` | nivel do Card vira pasta-pai; cadencia inferida = `Semanal`/`Mensal` (SEM prefixo `N{N}-`) |
| `Periodo` | semanal: `{YYYY}-S{NN:02d}` (ISO week 8601; ex: `2026-S21`); mensal: `{YYYY-MM}` |
| Multi-ciclos mesmo periodo | **SOBRESCRITA** (P1=a S3) — so o ciclo mais recente fica |

**Helper Python:** [scripts/resolve_ritual_path.py](scripts/resolve_ritual_path.py) recebe `vertical`, `ciclo_date`, `card_path` e retorna o `Path` canonical S3.

### Regra de re-run (sobrescrita seletiva)

Se `{RITUAL_DIR}/{Periodo}/` ja existir (re-execucao do mesmo ciclo):
- **SOBRESCREVER** `Apresentacao/` e `Briefing/` (artefatos derivados — sempre regerados)
- **PRESERVAR** `Ata/` (registro pos-ritual humano)
- **PRESERVAR** `dados/` (cópia de raw — pode ter sido editada manualmente)

---

## Anti-patterns

- **NUNCA re-analise dados** — o WBR ja contem toda a analise. Esta skill traduz, nao analisa.
- **NUNCA passe dados no prompt do agent** — passe caminhos. O agent deve Read os arquivos.
- **NUNCA organize slides por KPI** — o ritual e organizado por especialista.
- **NUNCA pule um especialista do Card** — todos devem ter bloco.
- **NUNCA use cores fora da paleta** — usar apenas as documentadas em [references/slide-structure.md](references/slide-structure.md) Secao 3.
- **NUNCA publique com gatekeeper SSoT falhando** (v2.0) — bloqueia coerencia briefing↔slide.
- **NUNCA copie todas as familias do Card sem filtrar** (v2.0) — armadilha/decisao so entra se o WBR sustenta o sinal/contexto.
- **NUNCA gere apenas MD em Card v2.0** — o ritual real exige variante HTML A4 imprimivel.
- **NUNCA esqueca a replicacao para `03-Rituais/`** — staging em `02-Controle/.../output/` e auditoria interna; gestor consulta `03-Rituais/`. Gatekeeper #15 bloqueia publicacao.
- **NUNCA sobrescreva `Ata/` ou `dados/` em re-runs** — re-execucao do mesmo ciclo regenera Apresentacao+Briefing mas preserva registros pos-ritual humanos.
- **NUNCA merge multi-card** em verticais multi-subnivel — cada execucao processa 1 card unico. Mergear `apresentacao.responsaveis[]` de cards distintos viola o design intencional (rituais por subproduto sao isolados).
- **NUNCA hardcode nomes de vertical/subnivel** na logica da skill — a deteccao e data-driven via `metadata.subnivel` dos cards. SEG WL/RE e o caso piloto, nao a unica forma de uso.

---

## Recursos adicionais

- Para regras detalhadas dos slides: [references/slide-structure.md](references/slide-structure.md)
- Para regras do briefing (5 secoes, 14-item checklist): [references/briefing-structure.md](references/briefing-structure.md)
- Para filtros v2.0 e gatekeepers SSoT: [references/migration-v2.md](references/migration-v2.md)
- Para o template HTML do deck: [templates/ritual.tmpl.html](templates/ritual.tmpl.html)
- Para os templates do briefing: [templates/ritual-briefing.tmpl.md](templates/ritual-briefing.tmpl.md), [templates/ritual-briefing.tmpl.html](templates/ritual-briefing.tmpl.html)
- Para gold standards validados: [examples/](examples/)

---

## Versão 2.4 — Canonical v1.2 + Sidecars E3/E4 (S2a — 2026-05-18)

### Schema do WBR canonical consumido (`wbr-{vertical}-{data}.data.json`)

A partir da S2a (commit `0eee058` em `Teste-Ritual-html`), o canonical WBR está em **schema v1.2** com campos novos emitidos pelo m7-controle:

- `indicadores.{id}.causa_raiz_resumo` (string, 1-2 frases) — vem do sidecar `analise/e3-causa-raiz-{vertical}.json` emitido por E3 Fase 6.5. Consumido por build_deck Slide Riscos · Alertas.
- `indicadores.{id}.n2.{esp}.causa_raiz_resumo` — frase especifica quando E3 detectou concentracao individual.
- `indicadores.oportunidades_estagnadas_funil*.n2.{esp}.volume_estagnado` (number) — soma de `volume` das rows N2-Especialista. Substitui fallback `_vol_estagnado_for_esp` (build_deck linha 3119).
- `indicadores.oportunidades_estagnadas_funil*.vol_em_risco` (number) — SUM(n2.*.volume_estagnado). Consumido em Matriz N3 célula Total de "Oport. Estagnadas (qty)" (build_deck linha 2995).
- `indicadores.{id}.aggregation_rule_applied` (bool) — `true` quando o N1/N2 foi derivado via `aggregation_rule` do YAML (indicadores `*_pct_ativas` v3.2). E6 Fase 4.5.f.
- `acoes.{criticas, atrasadas, em_dia_priorizadas, concluidas_eficazes}` (4 arrays de task_item) — vem do sidecar `analise/e4-acoes-{vertical}.json` emitido por E4 Fase 6.5. Consumido por Slide 4 (donut + barras owner) e Slide 5 (PA Vencendo).

### Schema do `clickup-tasks-{vertical}.json` (input do build_deck)

A partir da S2a B4.15 (v6.4.2 do collecting-data), cada `task_item` ganha `date_closed` (ms epoch convertido para `YYYY-MM-DD`). Tasks com `status` ∈ {complete, closed, done} DEVEM ter `date_closed` populado. Consumido por Slide 5 PA Vencendo no label "Concluido em DD/MM" (build_deck linha 4246, substitui fallback `due_date`).

### Fallback chains documentadas (S1 — preservadas como safety net)

Construções defensivas em build_deck.py que garantem renderização correta mesmo se canonical v1.2 vier incompleto. NÃO REMOVER sem auditoria item-a-item:

| Campo canonical v1.2 | Fallback se ausente | Localização |
|---|---|---|
| `causa_raiz_resumo` | Texto generico hardcoded por tipo de indicador | build_deck:5786-5808 (`_render_risks_slides`) |
| `n2.{esp}.volume_estagnado` | Soma de `volume` rows N2 de `dados_consolidados` | build_deck:3119 (`_vol_estagnado_for_esp`) |
| `vol_em_risco` | Agregação esp → `ind.get("vol_em_risco")` → 0.0 | build_deck:2995 (`_vol_estagnado_for_total`) |
| `date_closed` | `date_done → data_conclusao → closed_at → due_date` | build_deck:4246 (`_pa_row`) |
| `acoes.{4 categorias}` | Reconstrução dinâmica de `clickup-tasks-scoped.json` | build_deck:3554-3557 (`render_pa_slides`) |
| Alias `em_dia_proximas → em_dia_priorizadas` | Aplicado defensivamente 2x antes do bucketing (linhas 3545+3632) | build_deck `render_pa_slides` |
| `aggregation_rule` (não-implementado em build_deck) | Hardcoded `ratio_cfg` para Sem Especialista `_pct_ativas` | build_deck:2337-2378 |
| `_calc_delta` Fallback 3.5 | Non-aspect lookup (ind_id + subnivel sufixos) | build_deck:5306-5410 |

### Gatekeepers SSoT (S1) — bloqueiam publicação se inconsistente

| # | Nome | Validação | Tolerância |
|---|---|---|---|
| 7 | Rastreabilidade armadilha | Cada armadilha do briefing referencia indicador real | exact |
| 10 | Decisões = next cards | Decisões do briefing batem com próximo ritual | exact |
| 12 | Tempo briefing = agenda | Soma de tempos no briefing == agenda do deck | ±2min |
| 15 | Replicação byte-equal | Arquivos em `02-Controle/output/` == `03-Rituais/` | byte-equal |
| 16 | Cross-slide PA count (S1) | Donut Slide 4 == count rows Slide 5 == SUM owner bars | exact (counts) |
| 17 | Cross-slide esp consistency (S1) | Valor de indicador em Consolidado N3 == Dashboard do esp | R$ 500 / 1 unidade / 0.1pp |

PJ2 atualmente NÃO tem gatekeepers #16/#17 (backlog Sessão A B6.24).

### Sidecars E3/E4 (S2a) — consumo pelo material-generator

Quando o material-generator (agente) é invocado para gerar o deck, ele:
1. Lê `wbr-{vertical}-{data}.data.json` (canonical v1.2) como fonte primária
2. Se `causa_raiz_resumo` ausente em algum indicador vermelho → log WARN, fallback graceful
3. Se `acoes.*` ausente → reconstrói de `clickup-tasks-{vertical}-scoped.json`
4. Se algum indicador derivado (`*_pct_ativas`) tem `aggregation_rule_applied: true` mas N1 vazio → ERROR (canonical malformado)
5. Não invoca diretamente os sidecars `e3-causa-raiz-*.json` ou `e4-acoes-*.json` — esses são consumidos por E6 e injetados no canonical

Memory aplicada: `feedback_canonical_data_json` (canonical é SoT único; sidecars são insumos de E6, não acessados diretamente por material-generator).
