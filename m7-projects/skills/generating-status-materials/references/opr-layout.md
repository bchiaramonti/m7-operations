# OPR Layout — One-Page Report

> Layout denso de uma página A4 retrato destinado a email, Slack, impressão. Otimizado para leitura rápida (< 2 min) e fidelidade ao Design System M7-2026.

## Índice

1. [Formato e margens](#formato-e-margens)
2. [Zonas (top-down)](#zonas-top-down)
3. [Regras de fit](#regras-de-fit)
4. [Modo compacto (fallback)](#modo-compacto-fallback)
5. [Renderização HTML → PDF](#renderização-html--pdf)

---

## Formato e margens

- **Papel:** A4 retrato (210mm × 297mm)
- **Margens:** `top: 8mm, bottom: 8mm, left: 10mm, right: 10mm`
- **Área útil:** 190mm × 281mm
- **Orientação alternativa:** `--landscape` trocar para A4 paisagem se o conteúdo tiver muitos marcos (>7)

---

## Zonas (top-down)

```
┌──────────────────────────────────────────────────────────────┐
│  [logo M7 dark]  Nome do Projeto            Status: 🟡       │  HEADER (faixa Verde Caqui + off-white)
│                  Quinzena DD/MM — DD/MM     % concluído: 34% │   altura ~28mm
├──────────────────────────────────────────────────────────────┤
│  OBJETIVO                                                     │  OBJETIVO (1 linha)
│  Padronizar rituais de gestão N2 da M7 até 02/mai/2026       │   altura ~12mm
├──────────────────────────────────────────────────────────────┤
│  HIGHLIGHTS (o que avançou)    │  PRÓXIMOS PASSOS            │  2 COLUNAS 50/50
│  ▪ Mapeou cadeia de valor N1   │  ▪ Diagnosticar rituais     │   altura ~55mm
│  ▪ Estruturou repositório      │  ▪ Desenhar processo N2     │
│  ▪ Organizou referências BPM   │  ▪ Apresentar diretoria     │
├──────────────────────────────────────────────────────────────┤
│  MARCOS                                                       │  TIMELINE
│  ◆──◆──◆──◇──◇──◇──◇                                         │   altura ~32mm
│  Kick  M1   M2   M3   M4   M5   M6                           │
├──────────────────────────────────────────────────────────────┤
│  PONTOS DE ATENÇÃO                                            │  ATTENTIONS
│  🔴 R1 — Baixa adesão liderança (prob alta)                  │   altura ~30mm
│  🟡 R2 — Dependência crítica desenho processo                 │
│  🟢 Sprint na 1ª semana — 9 tarefas até 07/mar               │
├──────────────────────────────────────────────────────────────┤
│  CLICKUP: https://app.clickup.com/...  · gerado por m7-projects/generating-status-materials │  FOOTER
└──────────────────────────────────────────────────────────────┘
```

**Dimensões por zona (mm aproximados):**

| Zona | Altura | Notas |
|---|---|---|
| Header | 28mm | BG `#424135`, texto off-white, logo dark à esquerda |
| Objetivo | 12mm | 1 linha densa 14px |
| Highlights + Next (2 col) | 55mm | Dois boxes side-by-side, gap 4mm |
| Marcos | 32mm | Timeline horizontal, máx 7 diamonds |
| Atenções | 30mm | Até 3 bullets com color-dot indicando severidade |
| Footer | 10mm | Caption 10px muted |

Total vertical: ~167mm + margens 16mm = ~183mm. Sobra folga de ~98mm para variação de conteúdo. A4 retrato tem 281mm úteis, então confortavelmente cabe.

---

## Regras de fit

**Princípio:** se o conteúdo excede 1 página, **truncar, nunca paginar.** OPR é one-page por contrato.

**Regras de truncamento (por seção):**

| Seção | Limite padrão | Se exceder |
|---|---|---|
| Highlights | 3 bullets | Manter top-3 por ordem cronológica reversa (mais recentes) |
| Next steps | 3 bullets | Manter top-3 por prazo ascendente (mais urgentes) |
| Atenções | 3 bullets | Manter top-3 por severidade (critical > warning > neutral) |
| Marcos | 7 diamantes | Agrupar excedentes em `+N outros marcos` no footer |
| Objetivo | 1 linha | Truncar com ellipsis se >120 chars |

**Rationale:** 3 bullets é o limite para scan rápido. Mais que isso, o leitor pula. A arquitetura do dict canônico já vem com `highlights: List[str]` — o builder aplica slice.

---

## Modo compacto (fallback)

Se, mesmo com truncamento, o render excede 1 página A4, ativar modo compacto:

- `font-size-body`: 14px → 12px
- `font-size-small`: 12px → 11px
- `font-size-dense`: 11px → 10px
- `gap-4` → `gap-3` (16px → 12px)
- `gap-5` → `gap-4` (18px → 16px)
- `line-height-body`: 20px → 18px

**Detecção:** playwright mede `page.evaluate(() => document.body.scrollHeight)` após render. Se `> 1123px` (A4 em 96dpi), rerender com class `.compact` aplicada ao `<body>`.

Se ainda assim excede em modo compacto, emitir warning no stdout e truncar via ellipsis fixo no final da última seção que cabe.

---

## Renderização HTML → PDF

### Driver primário: playwright

```python
from playwright.sync_api import sync_playwright

def render_pdf(html_str: str, output_path: Path):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html_str, wait_until="networkidle")
        # Detect overflow
        height = page.evaluate("document.body.scrollHeight")
        if height > 1123:  # A4 @ 96dpi in px
            page.evaluate("document.body.classList.add('compact')")
            page.wait_for_load_state("networkidle")
        page.pdf(
            path=str(output_path),
            format="A4",
            margin={"top": "8mm", "bottom": "8mm", "left": "10mm", "right": "10mm"},
            print_background=True,
        )
        browser.close()
```

**Vantagens:** suporte CSS completo (Grid, Flexbox moderno, gradients, @font-face). Mede overflow real.

**Requisito:** `playwright install chromium` uma vez (baixa Chromium ~180MB).

### Fallback: weasyprint

```python
from weasyprint import HTML, CSS

def render_pdf_fallback(html_str: str, output_path: Path):
    HTML(string=html_str).write_pdf(
        target=str(output_path),
        stylesheets=[CSS(string="@page { size: A4; margin: 8mm 10mm; }")],
    )
```

**Vantagens:** puro Python, sem dependência de browser. Leve (~30MB).

**Limitações:**
- Sem detecção de overflow (precisa aplicar modo compacto proativamente)
- CSS Grid limitado (não suporta subgrid, gap inconsistente em algumas versões)
- `@font-face` precisa URL file:// absoluta
- Não mede `document.scrollHeight` — modo compacto tem que ser sempre ligado ou estimado por lines-of-text

### Ordem de tentativa

```python
try:
    import playwright
    render_with_playwright(html, pdf)
except ImportError:
    try:
        import weasyprint
        render_with_weasyprint(html, pdf)
    except ImportError:
        raise RuntimeError(
            "Nenhum driver HTML→PDF disponível. Instale:\n"
            "  pip install playwright && playwright install chromium\n"
            "ou:\n"
            "  pip install weasyprint"
        )
```

---

## Decisões de design

### Timeline de marcos (densa)

7 diamantes em linha única, espaçamento proporcional ao tempo — se um gap entre marcos for > 45 dias, usar `gap-visual-fixed` para manter visual limpo (não spreadar gigante). O layout é semântico-estético, não escala temporal rigorosa; para escala rigorosa, o slide 04 do PPTX serve melhor.

### Status color-dot em atenções

Bullets com dot pequeno 8×8 à esquerda (cor semântica) + texto. Mantém densidade visual sem explodir em ícones.

### Logo no header

- `m7-logo-dark.png` NÃO — estamos no header escuro, precisa do branco.
- **`m7-logo-offwhite.png`** — usado no header do OPR (fundo Verde Caqui).
- Tamanho renderizado: 28×14mm (proporção 196×96 preservada).

### Hyperlinks

Link do ClickUp list no footer é `<a href="{{ clickup_list_url }}">` renderizável no HTML, clicável no PDF (playwright + weasyprint preservam hiperlinks).
