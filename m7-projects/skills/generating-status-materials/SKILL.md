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

Emite `status-presentation.pptx` com **6 slides** construídos programaticamente (sem master template). Slide 3 (Roadmap) embeda screenshot headless do `roadmap-marcos.html` com overlays dinâmicos: bars coloridas por status real do Cronograma.xlsx LIVE + linha vertical HOJE. Slide 4 (Mapa de Status Executivo) renderiza a timeline M0-M7 em python-pptx com HOJE overlay, 2 colunas e atenções. Slide 5 (Riscos) renderiza até 6 cards fiéis ao Paper (severidade crit+high por padrão). Detalhes em [`presentation-structure.md`](references/presentation-structure.md).

### 5. Reportar ao usuário

Imprimir:
- Caminhos dos 3 arquivos gerados
- Status overall (🔵/🟢/🟡/🔴) + % concluído + razões das métricas que dispararam
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

## Framework de classificação de status (v1.7)

Substituição da heurística legada (que confundia risco mapeado com projeto doente)
por um framework PMI-flavored com 5 métricas determinísticas do `Cronograma.xlsx` +
4 zonas + gates de override. **Riscos mapeados NÃO penalizam mais** o status geral —
eles aparecem apenas no OPR quando flag `is_incurred=True` (v1.6).

### 5 métricas base (todas em `scripts/collect_data.py`)

| Métrica | Fórmula | O que mede |
|---|---|---|
| **DG** · Delivery Gap | `(devido_hoje − done_até_hoje) / devido_hoje` | Fração de entregas prometidas e não concluídas |
| **SG** · Start Gap | `late_start_count / len(iniciavel_hoje)` | Fração de tarefas que deviam começar e não começaram |
| **SPI** · Schedule Performance Index | `EV / PV` (duração em dias) | Métrica PMI/PMBOK — saúde agregada do cronograma |
| **MSI** · Milestone Slip Index | `max(dias_atraso)` entre gates `major=True` overdue | Atraso do marco crítico mais atrasado |
| **EDR** · Early Delivery Rate | `done_before_fim_plan / total_done` | Taxa de entregas antecipadas |

### Thresholds (zona por métrica)

| Zona | DG | SG | SPI | MSI |
|---|---|---|---|---|
| 🔵 Entregas Avançadas | = 0 | = 0 | ≥ 1.05 | = 0 |
| 🟢 No Prazo | ≤ 5% | ≤ 10% | 0.95–1.05 | 0 |
| 🟡 Atenção | 5–15% | 10–25% | 0.85–0.95 | 1–7 dias |
| 🔴 Crítico | > 15% | > 25% | < 0.85 | > 7 dias |

### Regra final

`status = worst({dg_zone, sg_zone, spi_zone, msi_zone})` — a métrica **pior** define a zona.

### Gates de override (Tier 1)

- **Gate RED**: marco terminal atrasado (último `major=True` por data, com `status == overdue`) → força 🔴 independente das métricas.
- **Gate BLUE celebratory**: `ahead_ratio ≥ 25%` (mais de 1/4 das entregas devidas concluídas antecipadamente) → eleva 🟢/🔵 base para 🔵.

### Outputs no JSON

```json
"status": {
  "overall": "blue|green|yellow|red",
  "metrics": {"dg": 0.0, "sg": 0.417, "spi": 0.49, "msi": 0, "edr": 0.0, "ahead_ratio": 0.0},
  "metric_zones": {"dg": "blue", "sg": "red", "spi": "red", "msi": "blue"},
  "status_reasons": ["DG = 0.0% (🔵)", "SG = 41.7% (🔴)", ...],
  "gates_fired": []
}
```

Tier 2 (futuros — requer extensão de schema): gate "cadeia serial comprometida",
gate "recurso-chave indisponível".

## Mapeamento Paper → PPTX

O deck produzido tem **7 slides** executivos (v1.6 inverteu Roadmap ↔ Visão Geral —
"tempo" ancora o leitor antes de mergulhar no escopo):

| # | Slide | Fonte de conteúdo |
|---|---|---|
| 1 | Cover (foto M7 + dark overlay) | `assets/m7-hero-dark.png` + `project.name`, `period_label` |
| 2 | Agenda (5 itens) | lista fixa refletindo slides 3-7 |
| 3 | **Roadmap Completo** | **screenshot** `roadmap-marcos.html > .roadmap` com **overlays dinâmicos**: bars coloridas por status de execução (verde=done, azul=active, vermelho=overdue, fade=future) + linha vertical HOJE interpolada |
| 4 | **Visão Geral do Roadmap** | Matriz **processos × fases** renderizada em python-pptx. Linhas = processos; colunas = fases uniformes do trabalho; células = status da task intersectada. Fonte: `matrix-structure.json` + `Cronograma.xlsx` LIVE |
| 5 | **Mapa de Status Executivo** | Timeline M0-M7 python-pptx + HOJE overlay + 2 colunas (Status Executivo + Próximas Atividades) + Pontos de Atenção |
| 6 | Riscos Ativos | Até 6 cards (crit+high) em 2 colunas, de `risks` filtrado por `severity_class` |
| 7 | Closing | Próxima ação prioritária + contato |

## OPR — 6 zonas (v1.6)

O OPR é um A4 portrait denso, fiel ao artboard Paper `OPR — Status Report`:

| Zona | Conteúdo | Fonte |
|---|---|---|
| **Hero** (dark) | Project name + 4 métricas (status, conclusão, próximo gate, riscos) | `project`, `status`, `next_marcos[0]`, `risks_critical_count` |
| **Roadmap** | Timeline horizontal com marcos M0-M7 + HOJE line interpolada | `macro_milestones` com `left_pct` + `roadmap_overlays.today_pct` |
| **Matriz** | Processos × fases (mesma estrutura do slide 4 do deck) | `roadmap_structure` |
| **Progresso** | 2 colunas: Concluídas (últimos 14 dias) + Próximas (próximos 14 dias) | `progress_concluidas`, `progress_proximas` (campos novos em v1.6) |
| **Riscos** | Condicional: placeholder "0 incorridos" OU cards detalhados se houver | `is_incurred=True` em `risks[]` |
| **Footer** | ClickUp LIVE + PM + assinatura | `project.clickup_list_url`, `project.pm`, `project.pm_email` |

### Riscos condicionais

Um risco só aparece como card no OPR quando `is_incurred == True`. Default: `False` —
o placeholder minimalista ("Sem riscos materializados neste período") é exibido.

Para marcar um risco como incorrido, adicione `data-incurred="true"` no `.risk-item`
correspondente do `1-planning/artefatos/riscos.html` (requer suporte upstream pela
`building-project-plan`, hoje ainda não expõe esse atributo — será v1.7+).

### Matriz Processos × Fases no Slide Visão Geral (v1.5)

Estrutura persistida em `<proj>/4-status-report/matrix-structure.json`:

```json
{
  "version": 1,
  "source": "inferred",
  "processos": [{"label": "Crédito", "wbs_prefix": "2.5"}, ...],
  "fases": [
    {"code": "MAPA_N2", "label": "Mapa N2", "match_pattern": "Mapa N2 — Jornada do cliente"},
    ...
  ]
}
```

**Inferência automática** (primeira execução):
1. `collect_data.py::infer_matrix_structure` usa `bar_titles` do `roadmap-marcos.html` como
   lista canônica de processos (linhas)
2. Para cada processo, coleta tasks-Ação cujo `etapa` contém o título (matching NFD-normalized)
3. Se todos os processos têm **N tasks com prefixos uniformes**, extrai as N fases comuns
   (colunas). Exemplos: "Mapa N2 — Jornada do cliente", "Mapa N3 — Processos detalhados",
   "DEIP + Tabela de Desconexões", "Políticas e manuais aplicáveis", "Playbook consolidado",
   "Plano de implementação"
4. Labels curtos derivados heuristicamente ("Plano de implementação" → "Implementação",
   "Mapa N2 — Jornada do cliente" → "Mapa N2", etc.)

**Fallback: conversa interativa** (quando inferência falha — projetos sem padrão uniforme):

Scripts Python não têm acesso direto a `AskUserQuestion` (tool do runtime Claude Code).
Fluxo da skill quando o `matrix-structure.json` tem `"source": "pending_user_input"`:

1. `collect_data.py` escreve stub com campo `candidate_processos` (títulos das bars do roadmap)
   + warning + continua gerando os demais slides normalmente
2. **Agente (Claude Code) deve**, ao ver o warning:
   a. Rodar `AskUserQuestion` com lista de `candidate_processos` → usuário confirma/edita
   b. Coletar lista de fases (label + match_pattern) via prompt ou AskUserQuestion
   c. Atualizar o JSON: `source: "user_defined"`, `processos: [...]`, `fases: [...]`
   d. Re-rodar `collect_data.py` + `build_pptx.py` — estrutura agora carregada do arquivo
3. Em rodadas subsequentes, o arquivo JSON é fonte de verdade (nunca reinferido)

**Tasks estruturais fora da matriz**: F1 Planejamento, F2.0 Fundação Transversal,
F2.13 Monitoramento, F3 Encerramento. Essas não entram nas células — aparecem em outros
slides (Roadmap Completo, Mapa de Status Executivo, Riscos). A matriz fica enxuta e
consistente entre projetos.

### Overlays dinâmicos no Slide Roadmap (v1.4)

Antes do screenshot do `roadmap-marcos.html`, o playwright executa JS que:

1. **Colore cada `.bar`** com classe `.bar-status-{done|active|overdue|future}` baseada no
   resultado de `aggregate_bar_status(bar.title, xlsx_entries, report_date)`:
   - `done` se todas as tasks matched estão concluídas
   - `active` se há tasks in_progress ou parcialmente concluídas
   - `overdue` se nenhuma task concluída E `max(fim_plan) < report_date`
   - `future` caso contrário (ou sem matches)

2. **Insere linha vertical HOJE** em cada `.track` na posição % interpolada entre os
   marcos âncora M0 e M7 do roadmap (via `compute_today_pct`). O primeiro track
   também recebe a label "HOJE · DD/MM" destacada em vermelho.

Matching de bar título ↔ etapa é fuzzy: normalização NFD + case-fold, com estratégia
cascata (substring direto → token split em separadores `·•-–—+&/|` com min-length 3 e
stopwords PT filtradas). Bars sem matches ficam em `future` (fade 50%).

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
