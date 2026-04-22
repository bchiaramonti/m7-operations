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
- Plano construído (`building-project-plan`): 10 HTMLs em `<proj>/1-planning/` — **obrigatórios para esta skill**: `roadmap-marcos.html` (fonte visual da swim-lane + marcos) e `riscos.html` (fonte dos riscos mapeados)
- Plano de ação inicializado (`managing-action-plan`): `<proj>/4-status-report/Cronograma.xlsx` LIVE + `changelog.md`
- Python 3.10+ com: `openpyxl`, `jinja2`, `beautifulsoup4`, `python-pptx`, **e** `playwright` + chromium (`python3 -m playwright install chromium`). Playwright é **obrigatório** — usado para (1) screenshot do roadmap para slides 3/4, (2) renderização HTML→PDF do OPR
- Fontes: **Arial** (padrão — conforme canvas Paper). TWK Everett é suportado se instalado, mas fallback Arial é silencioso.

### Contrato de reuso com `building-project-plan`

Esta skill **consome** artefatos produzidos pela `building-project-plan`, não reinventa:

| Artefato upstream | Usado por esta skill | Como |
|---|---|---|
| `roadmap-marcos.html` | Slides 3, 4 e OPR | Screenshot headless da swim-lane completa (`preset: roadmap-full`) e dos marcos (`preset: marcos-lane`) via playwright |
| `roadmap-marcos.html` `.lane.milestones` | Slide 6 cronograma macro | Parse dos 8 marcos M0-M7 (label, data, status computado por data) |
| `riscos.html` `.risk-item` | Slide 7 e OPR | Parse estruturado de 16 riscos com `severity_class` (crit/high/med/low), contramedidas, upsides filtrados |
| `BRIEFING.md` objetivo | Cover + OPR | Primeiro parágrafo da seção Objetivo |

**Granularidade herdada**: a skill **não decide** granularidade. Ela espelha a granularidade já aprovada em `roadmap-marcos.html` — se a fase PLANEJAMENTO aparece como 1 bar, o status report a trata como 1 bloco; se EXECUÇÃO aparece com 8+4 bars (playbooks), o status report detalha no mesmo nível.

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
  --out-dir <proj>/4-status-report/YYYY-MM-DD \
  --roadmap-html <proj>/1-planning/artefatos/roadmap-marcos.html
```

Emite `opr.html` + `opr.pdf`. Usa playwright (Chromium headless) para renderização HTML→PDF. Detalhes em [`opr-layout.md`](references/opr-layout.md).

### 4. Renderizar PPTX

```bash
python3 scripts/build_pptx.py \
  --data /tmp/collect-<ts>.json \
  --assets-dir assets \
  --out-dir <proj>/4-status-report/YYYY-MM-DD \
  --roadmap-html <proj>/1-planning/artefatos/roadmap-marcos.html
```

Emite `status-presentation.pptx` com 8 slides construídos programaticamente (sem master template). Slides 3 e 4 embedam screenshots headless do `roadmap-marcos.html`; Slide 6 renderiza a timeline M0-M7 via python-pptx com linha "HOJE" computada pela data do reporte; Slide 7 renderiza cards de risco fiéis ao Paper (até 6, severidade crit+high por padrão). Detalhes em [`presentation-structure.md`](references/presentation-structure.md).

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

| # | Paper artboard | Slide PPTX | Fonte de conteúdo |
|---|---|---|---|
| 1 | `01 — Cover` | Capa (foto M7 + dark overlay) | `assets/m7-hero-dark.png` + `project.name`, `period_label` |
| 2 | `02 — Agenda` | Sumário de seções | lista fixa |
| 3 | `03 — Marcos` | Timeline horizontal dos marcos M0-M7 | **screenshot** `roadmap-marcos.html > .lane.milestones` |
| 4 | `04 — Roadmap Completo` | Swim-lane completa do plano | **screenshot** `roadmap-marcos.html > .roadmap` (todas lanes expandidas) |
| 5 | `05 — Section Divider` | Divisor da sprint ativa | `status.active_sprint` (eyebrow + título separados automaticamente por "—") |
| 6 | `06 — Cronograma Macro` | Timeline M0-M7 python-pptx + HOJE overlay + highlights + próximos + atenções | `macro_milestones` (8 gates do roadmap-marcos) + `highlights`, `next_steps`, `attentions` |
| 7 | `07 — Riscos` | Até 6 cards de risco (crit+high) em 2 colunas | `risks` filtrado por `severity_class` |
| 8 | `08 — Closing` | Próxima ação prioritária + contato | `next_steps[0]`, `project.pm_email` |

Slides 3 e 4 são screenshots fiéis ao `roadmap-marcos.html` aprovado no plano — garantem fidelidade visual sem reinvenção. Slide 6 é renderizado via python-pptx para permitir o overlay "HOJE" dinâmico por data do reporte. Detalhes em [`presentation-structure.md`](references/presentation-structure.md).

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
