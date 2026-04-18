# Presentation Structure — 8 Slides 16:9

> Estrutura exata da apresentação PPTX, mapeada 1:1 do canvas Paper `status-report`. Cada slide tem dimensão 1280×720 (equivalente a 12.8" × 7.2" em python-pptx = `Inches(13.333, 7.5)` para 16:9 widescreen; usaremos `Emu` precisos para fidelidade).

## Índice

1. [Dimensões e conversão](#dimensões-e-conversão)
2. [Slide 01 — Cover](#slide-01--cover)
3. [Slide 02 — Agenda](#slide-02--agenda)
4. [Slide 03 — Visão Geral do Roadmap](#slide-03--visão-geral-do-roadmap)
5. [Slide 04 — Roadmap · Detalhe](#slide-04--roadmap--detalhe)
6. [Slide 05 — Section Divider](#slide-05--section-divider)
7. [Slide 06 — Executive Status](#slide-06--executive-status)
8. [Slide 07 — Risks](#slide-07--risks)
9. [Slide 08 — Closing](#slide-08--closing)
10. [Construção em python-pptx](#construção-em-python-pptx)

---

## Dimensões e conversão

- **Paper canvas:** 1280px × 720px (16:9, unidade lógica).
- **PPTX alvo:** 13.333" × 7.5" (slide widescreen padrão).
- **Fator de conversão:** `1 px ≈ 9525 EMU` para altura; em inches `13.333/1280 = 0.01042 in/px` para largura.
- **Helpers python-pptx:** use `Pt()` para tipografia, `Emu()` ou `Inches()` para posicionamento. Criar um helper `px_to_emu(px)` no build_pptx.py.

---

## Slide 01 — Cover

**Estrutura:** BG Verde Caqui `#424135` + imagem de fundo urbana escurecida (gradient overlay `oklab(23.9% -0.001 0.009 / 55–75%)`).

**Layout (padding 64/80):**

```
┌─────────────────────────────────────────────────────────────┐
│  STATUS REPORT (eyebrow Lime caps)              [logo M7]   │  64px do topo
│                                                              │
│                                                              │
│  Nome do Projeto                                             │  título 64px
│  Status Report                                               │
│  Quinzena DD/MM — DD/MM/AAAA (subtítulo Lime 22px)           │  gap 8px
│                                                              │
│                                                              │
│  M7 Investimentos · Mês AAAA              01                │  footer
└─────────────────────────────────────────────────────────────┘
```

**Placeholders:**
- Título: `{{ project.name }}` + linha "Status Report" fixa
- Subtítulo: `{{ project.period_label }}` (ex: "Quinzena 17/04 — 01/05/2026")
- Footer esquerda: `{{ project.footer_label }}` (ex: "M7 Investimentos · Abril 2026")
- Footer direita: número de slide `01`

**Imagem de fundo:** arquivo estático em `assets/cover-bg.jpg` (opcional — se ausente, usa BG sólido Verde Caqui + logo grande decorativo). O canvas Paper usa uma imagem urbana; para o PPTX, o build script permite `--cover-bg <path>` mas por padrão gera cover sem imagem (sólido Verde Caqui) para evitar dependência.

---

## Slide 02 — Agenda

**Estrutura:** BG Verde Caqui `#424135`, texto off-white + eyebrow Lime.

**Layout:**

```
STATUS REPORT (eyebrow Lime)                          [logo M7]

Agenda (título 64px off-white)
─────────────────────────────────────────────── (divider off-white 0.3 opacity)

01   Visão Geral do Roadmap                Slides 03–04
─────────────────────────────────────────────── 
02   Sprint Ativo — Status Executivo       Slides 05–06
─────────────────────────────────────────────── 
03   Riscos e Pontos de Atenção            Slide 07
─────────────────────────────────────────────── 
04   Próximos Passos                       Slide 08
```

**Construção:**
- Numerais `01`–`04`: eyebrow Lime com tracking 0.2em, font-size 13px
- Título do item: off-white 22px regular
- Slide range (ex: "Slides 03–04"): caption off-white opacidade 0.6, alinhado à direita
- Dividers: linha horizontal 1px off-white opacidade 0.2, altura total ~60px por linha

**Placeholder:** itens da agenda são fixos por enquanto (não parametrizados pelo dict de dados). Se o usuário tiver uma estrutura de slides diferente, manualmente editar após gerar.

---

## Slide 03 — Visão Geral do Roadmap

**Estrutura:** BG off-white `#FFFDEF`, tabela densa sprints × frentes.

**Layout:**

```
00 · ROADMAP (eyebrow Primary)                         [logo M7]
1 de 5 sprints em execução (H1 32px Primary)
Projeto iniciado em DD/fev — cobertura por processo... (subtítulo 14px #79755C)

┌──────┬──────────────────┬─────────────────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┐
│SPRINT│TÍTULO            │PERÍODO          │DIAG │PROC │REL  │AUTO │TREI │PIL  │ROT  │ ← header eyebrow
├──────┼──────────────────┼─────────────────┼─────┼─────┼─────┼─────┼─────┼─────┼─────┤
│ S0   │Processo Macro    │24/fev → 07/mar  │ ■   │ ■   │  —  │  —  │  —  │  —  │  —  │
│ S1   │Investimentos     │10/mar → 21/mar  │ □   │ □   │ □   │ □   │ □   │ □   │ □   │
│ S2   │Relatórios & KPIs │24/mar → 04/abr  │ □   │ □   │ □   │ □   │ □   │ □   │ □   │
│ S3   │Automação Cowork  │07/abr → 18/abr  │ □   │ □   │ □   │ □   │ □   │ □   │ □   │
│ S4   │Piloto & Rotina   │21/abr → 02/mai  │ □   │ □   │ □   │ □   │ □   │ □   │ □   │
└──────┴──────────────────┴─────────────────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┘

■ Sprint ativo   □ Sprint futuro   — Não aplicável     Fonte: ROADMAP.md · Atualizado em...
```

**Placeholders:**
- Hero sentence: `{{ status.sprint_progress_sentence }}` (calculado em `collect_data.py` — ex: "1 de 5 sprints em execução" ou "3 de 8 marcos concluídos")
- Tabela: `{{ sprints[] }}` com campos `code`, `title`, `period_label`, `fronts[]` (cada front tem `status`: `active`/`future`/`not_applicable`)

**Squares na célula:** 12×12 rotacionados? Não — no canvas Paper são quadrados retos (não rotated), `#3B82F6` para ativo, `#D0D0CC` para futuro, `—` texto para N/A.

---

## Slide 04 — Roadmap · Detalhe

**Estrutura:** BG off-white, swimlane Gantt-style (MAIS complexo de todos).

**Layout:**

```
03 · ROADMAP                                           [logo M7]
Visão Geral do Roadmap
5 sprints · 24/fev → 02/mai · Frentes por sprint

┌─────────────┬─┬─┬─┬─┬─┬─┬─│HOJE│─┬─┐  ← header de semanas (divisões verticais)
│ Frente · PO │S0│S1│S2│S3│...│ ...       │
├─────────────┼──────────────▶              ← bars com cor por frente
│ F1 Diag     │▓▓▓▓▓▓▓▓                    │
│ F2 Processo │▓▓▓▓▓▓▓▓▓▓▓▓                │
│ F3 Rel&KPI  │         ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓   │
│ F4 Auto     │              ▓▓▓▓▓▓▓        │
│ F5 Trein    │                  ▓▓▓▓▓▓▓    │
│ GOV         │▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓   │
└─────────────┴────────────────────────────┘

legenda de cores + linha vertical vermelha "HOJE"
```

**Estratégia de implementação:** este slide é o mais denso. Duas opções:

1. **Render como imagem PNG via matplotlib/PIL em `build_pptx.py` antes de inserir** — garante fidelidade visual, risco de fugir do design system.
2. **Construir com shapes python-pptx** — add_shape(RECTANGLE) para cada barra, add_line para conectores, add_text para labels. Mais verbose, totalmente editável no PowerPoint depois.

**Escolha:** opção 2 (shapes programáticos). Cada frente ocupa uma lane de ~70px de altura; barras posicionadas proporcionalmente à data de início/fim. Cores por frente em `fronts_palette` (configurable via data).

**Placeholders:**
- `fronts[]` — cada front tem `code` (F1, F2...), `title`, `po`, `start_date`, `end_date`, `color`, `sprint_bars[]` (cada bar com `start`, `end`, `label`)
- `today_line_date` — data de "HOJE" (do report_date)
- `sprint_headers[]` — sprints com datas para o header superior

Se os dados não tiverem granularidade suficiente (ex: nenhum HTML de plano informa duração por frente), o script emite placeholder cinza e Warn "Dados de frentes não disponíveis — preencher manualmente".

---

## Slide 05 — Section Divider

**Estrutura:** BG Verde Caqui, hero numeral Lime à esquerda + título à direita.

**Layout:**

```
SPRINT ATIVO · 02 DE 04 (eyebrow Lime)                 [logo M7]




     S0       │  FUNDAÇÃO (eyebrow off-white)
   (Lime      │  Base metodológica dos
   160px      │  rituais de gestão N2 (título 64px off-white)
   hero)      │
              │  24/fev → 07/mar · Sprint de 2 semanas (14px off-white 0.6)


                                                              04
```

**Placeholders:**
- Eyebrow topo-esquerda: `SPRINT ATIVO · {{ status.active_sprint_index }} DE {{ status.total_sprints }}`
- Hero numeral: `{{ status.active_sprint.code }}` (ex: `S0`, `S1`)
- Divisor vertical off-white 1px + padding lateral 24px
- Eyebrow do título: `{{ status.active_sprint.phase_name }}` (ex: "FUNDAÇÃO")
- Título: `{{ status.active_sprint.title }}`
- Subtítulo: `{{ status.active_sprint.period_label }}` + `Sprint de N semanas`

---

## Slide 06 — Executive Status (MAIS DENSO)

**Estrutura:** BG off-white, 4 zonas empilhadas (timeline + 2 colunas + attentions + legend).

**Padding especial:** `36px / 40px` (vs `56px / 80px` dos outros slides claros) — conteúdo aproveita quase toda a largura.

**Layout:**

```
S0 · FUNDAÇÃO (eyebrow Primary)                        [logo M7]
3 de 12 tarefas concluídas (25%) (H2 30px Primary)
───────────────────────────────────────────────────────────── divider 1px

CRONOGRAMA MACRO (eyebrow 10px)
┌─────────────────────────────────────────────────────────────┐
│ ◆──◆──◆──◆──◇──◇──◇  (marcos + conectores, 7 marcos) │
│ Estr  Org  Cad  Diag  Des  POP  Val                         │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────┬───────────────────────┐
│ STATUS EXECUTIVO    │ PRÓXIMAS ATIVIDADES   │ ← eyebrows (gap 16px)
│ ┌─────────────────┐ │ ┌─────────────────────┐
│ │ ▪ bullet 1      │ │ │ ▪ bullet 1          │
│ │ ▪ bullet 2      │ │ │ ▪ bullet 2          │
│ │ ▪ bullet 3      │ │ │ ▪ bullet 3          │
│ └─────────────────┘ │ └─────────────────────┘
└─────────────────────┴───────────────────────┘

PONTOS DE ATENÇÃO (eyebrow Warning amber)
┌─────────────────────────────────────────────────────────────┐
│ ▪ atenção 1                                                 │
│ ▪ atenção 2                                                 │
│ ▪ atenção 3                                                 │
└─────────────────────────────────────────────────────────────┘

Atualizado em DD/MMM/AAAA · Fonte: SPRINT-NN.md
                                       ◇ Não iniciado  ◆ Em andamento  ◆ Atrasado  ◆ Concluído
```

**Placeholders:**
- Eyebrow topo: `{{ status.active_sprint.eyebrow }}` (`S0 · FUNDAÇÃO`)
- Hero: `{{ status.hero_sentence }}` — "3 de 12 tarefas concluídas (25%)" calculado em `collect_data.py`
- `macro_milestones[]` — 7 marcos com `label`, `status` (`not_started`/`in_progress`/`done`/`overdue`)
- `highlights[]` — 3 bullets (truncar se >3 com "+N outros")
- `next_steps[]` — até 4 bullets
- `attentions[]` — até 3 bullets

**Construção técnica (marcos):**
- Diamante = `add_shape(MSO_SHAPE.DIAMOND)` rotacionado (ou retângulo 14×14 com `rotation=45`). Preenchimento conforme status.
- Conector = `add_shape(RECTANGLE)` 63×2 com cor de fundo conforme status adjacente.

---

## Slide 07 — Risks

**Estrutura:** BG off-white, até 3 risk cards empilhados com accent bar lateral.

**Layout:**

```
03 · RISCOS (eyebrow Primary)                          [logo M7]
3 riscos mapeados — 1 com probabilidade alta (H1 32px)
Monitoramento ativo. Contramedidas definidas para cada risco. (14px muted)

┌─┬───────────────────────────────────────────────────────────┐
│▮│ R1 — Baixa adesão da liderança aos rituais  [ALTA·CRÍTICO]│  accent bar 6px vermelha
│▮│                                                            │
│▮│ Probabilidade: Alta · Impacto: Crítico                     │
│▮│ Contramedida: Envolver diretoria no gate...                │
└─┴───────────────────────────────────────────────────────────┘

┌─┬───────────────────────────────────────────────────────────┐
│▮│ R2 — Dependência crítica do desenho...     [MÉDIA · ALTO] │  accent bar amber
...

┌─┬───────────────────────────────────────────────────────────┐
│▮│ R3 — Atraso na automação Cowork            [BAIXA · MÉDIO]│  accent bar neutral
...

Fonte: ROADMAP.md · Seção Riscos · Atualizado em DD/MMM/AAAA
```

**Placeholders:**
- `risks[]` — cada risk: `code` (R1), `title`, `probability` (baixa/media/alta), `impact` (baixo/medio/alto/critico), `mitigation`
- Severity tag = derivado de prob+impact: 
  - `alta` + `critico` → `ALTA · CRÍTICO` tag `#FDEDED`
  - `alta` + `alto` ou `media` + `alto` → `MÉDIA · ALTO` tag `#FDF3E0`
  - demais → tag neutral `#EFEFEC`

**Regra de fit:** máximo 3 risk cards no slide. Se `risks[]` tiver >3, incluir só top-3 por severidade (high-critical primeiro) e adicionar eyebrow `+N RISCOS ADICIONAIS` no footer.

---

## Slide 08 — Closing

**Estrutura:** BG Verde Caqui, título dominante (a "ação prioritária" do reporte).

**Layout:**

```
PRÓXIMOS PASSOS (eyebrow Lime)                         [logo M7]



UMA AÇÃO PRIORITÁRIA (eyebrow smaller off-white 0.6)

Concluir Sprint 0 · Fundação     (título 64px off-white)
até 07/mar/AAAA

Gate obrigatório com a diretoria para destravar Sprint 1 (Investimentos).
Validação da cadeia de valor N2 e POPs de ritual são entregáveis mandatórios.
(body 14px off-white 0.6)


──────────────────────────────────────────────────────────────── divider
M7 Investimentos · Status Report · Mês AAAA   Dúvidas: responsavel@m7...
```

**Placeholders:**
- Eyebrow: `PRÓXIMOS PASSOS` (fixo)
- Hero: `{{ next_steps[0].action }} até {{ next_steps[0].deadline }}`
- Body: `{{ next_steps[0].rationale }}` (texto expandido do próximo passo prioritário)
- Footer esquerda: `{{ project.footer_label }}`
- Footer direita: `Dúvidas: {{ project.pm_email }}`

---

## Construção em python-pptx

### Preparação

```python
from pptx import Presentation
from pptx.util import Emu, Pt, Inches
from pptx.dgm.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

PX_TO_EMU = 9525
def px(n: int) -> Emu:
    return Emu(n * PX_TO_EMU)

# Setup deck 16:9
prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]  # blank layout
```

### Padrão para cada slide

```python
def build_slide_01_cover(prs, data):
    slide = prs.slides.add_slide(BLANK)
    # 1. BG solid Verde Caqui
    bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
    bg.fill.solid(); bg.fill.fore_color.rgb = RGBColor(0x42, 0x41, 0x35)
    bg.line.fill.background()
    # 2. Eyebrow "STATUS REPORT" at px(80, 64)
    # 3. Logo M7 offwhite at px(1168, 64) size 56x56
    # 4. Title + subtitle block at px(80, 360)
    # 5. Footer at px(80, 656) and px(1200, 656)
    # ...
    return slide
```

### Construtor de shapes-utilitário

Definir helper em `build_pptx.py`:

```python
def add_text_box(slide, x_px, y_px, w_px, h_px, text, *, 
                 font="Arial", size=14, weight=False, color=(0x42, 0x41, 0x35),
                 letter_spacing=0.0, align="left"):
    ...
```

Esse helper padroniza posicionamento, fonte, tracking, cor, alinhamento. **Todos** os elementos de texto passam por aqui.

### Teste visual

Após gerar, abrir em PowerPoint E Keynote (se possível) para validar. Principal ponto de falha: **kerning/tracking** — python-pptx não aplica letter-spacing nativamente via alto nível, precisamos usar XML direto via `_element.get_or_add_rPr().set('spc', str(int(size*100*letter_spacing)))` (spc é em unidades de 1/100 de ponto).
