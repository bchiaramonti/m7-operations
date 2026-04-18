---
name: generating-status-materials
description: >-
  Gera materiais de status de projeto em dois formatos a partir dos mesmos
  insumos — OPR (one-page report HTML + PDF) para comunicação assíncrona, e
  apresentação executiva PPTX 16:9 para reuniões de reporte. Aplica o Design
  System M7-2026 (Verde Caqui, Off-White, Lime) mapeado do canvas Paper
  `status-report`. Lê os 10 HTMLs do plano em 1-planning/, o Cronograma.xlsx
  LIVE e o changelog.md em 4-status-report/. Use quando o usuário pede reporte,
  OPR, apresentação de projeto, material para stakeholders ou status quinzenal.
user-invocable: true
---

# Generating Status Materials

Produz dois artefatos do mesmo reporte a partir de um pipeline único de coleta de dados:

1. **OPR** — `opr.html` + `opr.pdf`: uma página A4 retrato, densa, para email/Slack/impressão
2. **PPTX** — `status-presentation.pptx`: apresentação 16:9 com 8 slides executivos (mapeada do canvas Paper `status-report`)

Ambos os formatos consomem o mesmo dict normalizado emitido por `scripts/collect_data.py` — **narrativa consistente garantida por construção**, não por disciplina de autoria.

## Exemplos de invocação

**Reporte completo (caso padrão):**
- Usuário: "Gera o status report da quinzena"
- Assistente: invoca `generating-status-materials`, coleta dados, produz OPR HTML + PDF + PPTX em `4-status-report/YYYY-MM-DD/`

**Só OPR para email:**
- Usuário: "Só preciso da OPR dessa sprint"
- Assistente: invoca `generating-status-materials` com flag `--only opr`

**Data customizada (backfill):**
- Usuário: "Gera o reporte com data 2026-04-15 para backfill"
- Assistente: invoca com `--report-date 2026-04-15`

## Pré-requisitos

- Projeto inicializado (`initializing-project`): `<proj>/CLAUDE.md` + `<proj>/4-status-report/`
- Plano construído (`building-project-plan`): 10 HTMLs em `<proj>/1-planning/` com stakeholders, marcos, riscos
- Plano de ação inicializado (`managing-action-plan`): `<proj>/4-status-report/Cronograma.xlsx` LIVE + `changelog.md`
- Python 3.10+ com: `openpyxl`, `jinja2`, `beautifulsoup4`, `python-pptx`, **e** (`playwright` **ou** `weasyprint`) para HTML→PDF
- Fontes: **Arial** (padrão — conforme canvas Paper). TWK Everett é suportado se instalado, mas fallback Arial é silencioso.

## Estado da arte

```
<proj>/
├── CLAUDE.md                         # metadados + clickup_list_id (LEITURA)
├── BRIEFING.md                       # objetivo, stakeholders (LEITURA)
├── 1-planning/                       # 10 HTMLs do plano (LEITURA)
│   ├── plano-projeto.html
│   └── artefatos/
│       ├── recursos-dependencias.html
│       ├── riscos.html
│       ├── roadmap-marcos.html
│       ├── okrs.html
│       └── ...                       # demais artefatos (não lidos hoje)
└── 4-status-report/
    ├── Cronograma.xlsx               # LIVE, mantido por managing-action-plan (LEITURA)
    ├── changelog.md                  # append-only, mantido por managing-action-plan (LEITURA)
    ├── .sync-state.json              # sidecar (LEITURA opcional — detectar staleness)
    └── YYYY-MM-DD/                   # ESCRITA exclusiva desta skill
        ├── opr.html
        ├── opr.pdf
        └── status-presentation.pptx
```

**Regra de escrita:** esta skill **nunca** mexe na raiz de `4-status-report/` (não toca em `Cronograma.xlsx`, `changelog.md`, `.sync-state.json`). Toda escrita é confinada à subpasta `YYYY-MM-DD/`.

## Workflow

### 1. Detectar projeto ativo

Verificar que `cwd` (ou path passado) contém `CLAUDE.md` **e** `4-status-report/Cronograma.xlsx` existe. Caso contrário, erro claro apontando qual skill rodar antes (ver [failure-modes](#failure-modes)).

### 2. Coletar dados (determinístico)

```bash
python3 scripts/collect_data.py --project-dir <proj> --report-date YYYY-MM-DD
```

`collect_data.py` é **pure Python**: lê HTMLs do plano (BeautifulSoup), xlsx LIVE (openpyxl), `changelog.md` (parse markdown), e emite JSON canônico em stdout. **Nenhuma interpretação de LLM na coleta** — seguimos o princípio de coleta determinística (feedback arquitetural registrado na memória).

Cálculos derivados (status overall, highlights, next_steps, attentions) são feitos por heurísticas **no script**, não por LLM — regras explícitas em [`narrative-synthesis.md`](references/narrative-synthesis.md).

### 3. Renderizar OPR

```bash
python3 scripts/build_opr.py \
  --data /tmp/collect-<ts>.json \
  --template templates/opr.tmpl.html \
  --assets-dir assets \
  --out-dir <proj>/4-status-report/YYYY-MM-DD
```

Emite `opr.html` + `opr.pdf`. Usa playwright (Chromium headless) como primeiro driver; cai em weasyprint se playwright indisponível. Detalhes em [`opr-layout.md`](references/opr-layout.md).

### 4. Renderizar PPTX

```bash
python3 scripts/build_pptx.py \
  --data /tmp/collect-<ts>.json \
  --assets-dir assets \
  --out-dir <proj>/4-status-report/YYYY-MM-DD
```

Emite `status-presentation.pptx` com 8 slides construídos programaticamente (sem master template). Layout fiel ao canvas Paper `status-report`. Detalhes em [`presentation-structure.md`](references/presentation-structure.md).

### 5. Reportar ao usuário

Imprimir:
- Caminhos dos 3 arquivos gerados
- Status overall (🟢/🟡/🔴) + % concluído
- Warnings (staleness do sync, fontes ausentes, campos faltando)
- Snapshot textual dos highlights + next steps (para o usuário validar antes de enviar)

## Flags de invocação

| Flag | Default | Efeito |
|---|---|---|
| `--only opr` | off | Gera só OPR (html + pdf), pula PPTX |
| `--only pptx` | off | Gera só PPTX, pula OPR |
| `--report-date YYYY-MM-DD` | hoje | Data do reporte (nome da subpasta) |
| `--project-dir <path>` | cwd | Diretório raiz do projeto |
| `--force` | off | Sobrescreve arquivos se `YYYY-MM-DD/` já existe |

## Cálculo de status overall (heurística)

Executado em `collect_data.py` (não em LLM). Regras em [`narrative-synthesis.md`](references/narrative-synthesis.md):

- **🔴 red** se `overdue > 20% do total` OU marco crítico atrasado > 7 dias OU risco prob=high ∧ impact=high sem contramedida
- **🟡 yellow** se `overdue > 10% do total` OU qualquer marco atrasado OU algum risco prob=high OU impact=high
- **🟢 green** caso contrário

## Mapeamento Paper → PPTX

O canvas Paper `status-report` contém **8 artboards 1280×720** que mapeiam 1:1 para os slides PPTX:

| # | Paper artboard | Slide PPTX | Dados consumidos |
|---|---|---|---|
| 1 | `01 — Cover` | Capa (fundo escuro com imagem) | `project.name`, `report_date`, `project.period_label` |
| 2 | `02 — Agenda` | Sumário de seções | lista fixa de seções |
| 3 | `03 — Visão Geral do Roadmap` | Tabela sprints × frentes | `milestones`, `sprints` |
| 4 | `04 — Roadmap · Detalhe` | Swimlane Gantt-style (imagem renderizada) | `milestones`, `sprint_bars` |
| 5 | `05 — Section Divider` | Divisor da sprint ativa | `status.active_sprint` |
| 6 | `06 — Executive Status` | Cronograma macro + highlights + next + attentions | `highlights`, `next_steps`, `attentions`, `macro_milestones` |
| 7 | `07 — Risks` | Cards de riscos com severidade | `risks` |
| 8 | `08 — Closing` | Próximos passos + contato | `next_steps[0]`, `project.pm_email` |

Slide 4 (swimlane Gantt) é construído via shapes python-pptx diretamente — detalhes em [`presentation-structure.md`](references/presentation-structure.md#slide-4--roadmap-detalhe).

## Anti-patterns a evitar

- **Misturar voz de agente com coleta de dados:** `collect_data.py` é 100% determinístico. Não invocar LLM para "decidir highlights" — heurísticas explícitas cobrem isso.
- **Escrever na raiz de `4-status-report/`:** só dentro de `YYYY-MM-DD/`. Nunca tocar em `Cronograma.xlsx` LIVE ou `changelog.md` (esses são domínio de `managing-action-plan`).
- **Skip do aviso de staleness:** se `.sync-state.json` indica `last_sync > 48h` ou `sync_pending=true`, **avisar explicitamente** no output — o usuário precisa saber que os dados podem estar desatualizados.
- **Hardcode de dados do projeto no PPTX:** tudo vem do dict normalizado. Se um campo está faltando, `collect_data.py` emite `null` e o builder pinta placeholder visível (`— faltando —`) em vez de string vazia silenciosa.
- **Misturar Design System:** tokens M7-2026 apenas. Sem misturar com Planner Editorial Noturno ou qualquer outro sistema.
- **Depender de `playwright` silenciosamente:** se ausente, cair em weasyprint e avisar que o OPR pode ter limitações de CSS (weasyprint não suporta todos os seletores modernos).

## Failure modes

| Modo | Resposta |
|---|---|
| Projeto não inicializado (sem `CLAUDE.md`) | Erro: "Projeto não encontrado. Rode `initializing-project` primeiro." |
| Plano não construído (sem HTMLs em `1-planning/`) | Erro: "Plano não encontrado. Rode `building-project-plan` primeiro." |
| `Cronograma.xlsx` LIVE ausente | Erro: "Cronograma LIVE não inicializado. Rode `managing-action-plan init` primeiro." |
| `changelog.md` ausente | Warn, gera sem histórico, nota "histórico indisponível" |
| `.sync-state.json` indica staleness | Warn visível no output final |
| HTML do plano com estrutura divergente | Warn por arquivo, placeholder nos campos faltantes |
| xlsx sem coluna esperada (schema quebrado) | Erro com lista de colunas faltantes |
| `playwright` + `weasyprint` ambos ausentes | Erro com instruções de instalação |
| Fonte Arial indisponível (muito raro) | Warn, usa fallback system-ui, nota no footer |
| Logo M7 ausente em `assets/` | Warn, gera sem logo mas com texto "M7" |
| Conteúdo excede 1 página A4 no OPR | Modo compacto automático (reduz font-size 1px, gap 2px); se persistir, trunca e avisa |
| `YYYY-MM-DD/` já existe sem `--force` | Erro pedindo `--force` ou data diferente |

Detalhamento em [`failure-modes.md`](references/failure-modes.md).

## Additional resources

- [`opr-layout.md`](references/opr-layout.md) — Zonas do OPR, regras de fit A4, modo compacto
- [`presentation-structure.md`](references/presentation-structure.md) — 8 slides detalhados + construção via python-pptx
- [`design-tokens.md`](references/design-tokens.md) — Tokens M7-2026 extraídos do canvas Paper (cores, tipografia, espaçamentos exatos)
- [`narrative-synthesis.md`](references/narrative-synthesis.md) — Heurísticas determinísticas para status overall, highlights, next steps, attentions
- [`data-sources.md`](references/data-sources.md) — Mapeamento exato: cada campo do dict canônico → fonte no projeto
- [`xlsx-reading.md`](references/xlsx-reading.md) — Como ler `Cronograma.xlsx` LIVE (sheet, header R4, colunas B-L, datas, normalização)
- [`failure-modes.md`](references/failure-modes.md) — Modos de falha detalhados e recovery
- [`templates/opr.tmpl.html`](templates/opr.tmpl.html) — Template Jinja2 do OPR com CSS inline

## Scripts (referência rápida)

| Script | Pure? | Função |
|---|---|---|
| `collect_data.py` | sim | Coleta determinística: xlsx + HTMLs + changelog → JSON canônico |
| `build_opr.py` | sim | Renderiza OPR: JSON + Jinja2 → HTML → PDF (playwright/weasyprint) |
| `build_pptx.py` | sim | Constrói PPTX: JSON + python-pptx → 8 slides 16:9 |

**Pure = não chama MCP e não consulta LLM.** Toda a skill é 100% local — diferente de `managing-action-plan` (que orquestra ClickUp MCP), aqui não há integração externa.
