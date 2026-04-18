# Design Tokens — M7-2026

> Tokens extraídos diretamente do canvas Paper `status-report` (8 artboards 1280×720). **Esta é a fonte de verdade** — qualquer alteração aqui precisa espelhar no canvas Paper (ou vice-versa). Valores verificados com `get_computed_styles` em 2026-04-18.

## Índice

1. [Cores](#cores)
2. [Tipografia](#tipografia)
3. [Espaçamento](#espaçamento)
4. [Elementos estruturais](#elementos-estruturais)
5. [Uso por contexto](#uso-por-contexto)

---

## Cores

### Neutros (base)

| Token | Hex | Uso |
|---|---|---|
| `--m7-primary` | `#424135` | Verde Caqui — texto principal em BG claro; fundo de slides escuros (Capa, Agenda, Divider, Closing) |
| `--m7-bg-light` | `#FFFDEF` | Off-White warm — fundo principal dos slides de conteúdo; texto em BG escuro |
| `--m7-text-muted` | `#4F4E3C` | Variante dessaturada de Verde Caqui — body text em cards e boxes |
| `--m7-text-subtle` | `#79755C` | Ainda mais apagado — subtítulos e descrições longas |
| `--m7-text-caption` | `#AEADA8` | Captions e footers muito discretos |

### Accent

| Token | Hex | Uso |
|---|---|---|
| `--m7-accent` | `#EEF77C` | Lime — **só** em elementos decorativos (eyebrow text sobre BG escuro, hero numerals tipo `S0`, bars, dividers, `EEF77C` com tracking 0.18–0.2em). **NUNCA** usar para body text. |

### Status semântico

| Token | Hex | Uso |
|---|---|---|
| `--status-ok` | `#00B050` | Verde — marcos concluídos no cronograma macro |
| `--status-progress` | `#3B82F6` | Azul — conectores/marcos em andamento, "sprint ativo" na tabela de roadmap |
| `--status-warning` | `#F59E0B` | Âmbar — risco médio, "pontos de atenção" (eyebrow color) |
| `--status-critical` | `#E46962` | Terracota — risco alto/crítico, accent bar vermelho |
| `--status-neutral` | `#D0D0CC` | Cinza morno — sprint futuro, marco não iniciado, accent bar neutro |

### Pastéis para severity tags (background pequenos)

| Token | Hex | Uso |
|---|---|---|
| `--tag-bg-critical` | `#FDEDED` | Fundo do severity tag `ALTA · CRÍTICO` |
| `--tag-bg-warning` | `#FDF3E0` | Fundo do severity tag `MÉDIA · ALTO` (derivado) |
| `--tag-bg-neutral` | `#EFEFEC` | Fundo do severity tag `BAIXA · MÉDIO` (derivado) |

### Banner de riscos (accent bar lateral)

A accent bar de 6px × altura-do-card usa a cor `--status-*` pura (sem pastel).

---

## Tipografia

**Família primária:** `Arial` (`"ArialMT"`, `"Arial-BoldMT"` para bold). Verificado no canvas Paper — é a fonte real do design, **não** TWK Everett. O PPTX/HTML deve usar Arial como base; TWK Everett é opcional/aspiracional.

**Fallback stack:** `"Arial", system-ui, sans-serif`

### Escala tipográfica (px)

| Token | Font-size | Line-height | Letter-spacing | Weight | Uso |
|---|---|---|---|---|---|
| `--size-hero-xxl` | 160px | 1.0 | -0.02em | 700 | Hero numeral (`S0`) em Divider — Lime |
| `--size-display` | 64px | 72px | -0.02em | 400 | Título da Capa (`Nome do Projeto / Status Report`) |
| `--size-h1` | 32px | 38px | -0.01em | 400 | Headline de slide (`1 de 5 sprints em execução`) |
| `--size-h2` | 30px | 36px | -0.01em | 400 | Headline de slide denso (`3 de 12 tarefas concluídas (25%)`) |
| `--size-h3-agenda` | 22px | 28px | 0 | 400 | Itens da Agenda e subtítulo da Capa |
| `--size-body-risk` | 16px | 22px | 0 | 700 | Título de risk card (`R1 — Baixa adesão...`) |
| `--size-body` | 14px | 20px | 0 | 400 | Body descritivo, footers, subtítulos longos |
| `--size-small` | 12px | 16px | 0 | 400 | Texto em tabelas, legendas, chips |
| `--size-body-dense` | 11px | 16px | 0 | 400 | Bullets dentro de box do slide 06 (cronograma) e no OPR (denso) |
| `--size-eyebrow` | 11–13px | 12–16px | 0.18–0.20em | 700 | Eyebrow caps (`STATUS REPORT`, `03 · RISCOS`, `STATUS EXECUTIVO`) |
| `--size-eyebrow-small` | 10px | 12px | 0.14em | 700 | Eyebrow caps compactos dentro de boxes |
| `--size-caption` | 10px | 12px | 0 | 400 | Footer caption de fonte/data |

### Regra de eyebrow (caps)

Caps bold + tracking aberto (`letter-spacing: 0.18em` a `0.20em`) + texto uppercase. Cor varia:

- `#EEF77C` (Lime) sobre BG escuro — em Capa, Agenda, Divider, Closing
- `#424135` (Primary) sobre BG claro — em slides de conteúdo (Roadmap, Executive, Risks)
- `#F59E0B` (Warning) para eyebrow de `PONTOS DE ATENÇÃO` no slide Executive

---

## Espaçamento

| Token | px | Uso |
|---|---|---|
| `--gap-0` | 2px | Separador fino (linha horizontal entre marcos) |
| `--gap-1` | 4px | Gap íntimo dentro de linha (bullet-marker ↔ texto) |
| `--gap-2` | 8px | Gap entre bullets empilhados |
| `--gap-3` | 12px | Gap entre linhas em tabela densa |
| `--gap-4` | 16px | Gap padrão entre grupos relacionados |
| `--gap-5` | 18–24px | Gap entre zonas principais do slide |
| `--gap-6` | 28–36px | Padding de slide (vertical), gap hero |
| `--pad-slide-x` | 80px | Padding lateral de slides de conteúdo (1280 - 80×2 = 1120px de conteúdo) |
| `--pad-slide-y` | 36–64px | Padding vertical (Capa tem 64px, Executive tem 36px) |
| `--pad-slide-exec-x` | 40px | Padding lateral reduzido para slide Executive (denso) |

### Grid de conteúdo

- **Slides 1280×720.** Slide 06 Executive usa padding `36px / 40px` por ser denso; demais usam `56px / 80px` (vertical / horizontal).
- **Zonas (slide 06):** Header → Zone 1 (timeline) → Zones 2-3 (2 colunas lado a lado) → Zone 4 (attention, full width) → Footer legend. Gaps de 18px entre zonas.

---

## Elementos estruturais

### Marcos (diamantes rotacionados 45°)

- **Concluído:** quadrado 14×14 rotacionado 45°, preenchido `#00B050`
- **Em andamento:** quadrado 14×14 rotacionado 45°, preenchido `#3B82F6`
- **Não iniciado:** quadrado 10×10 rotacionado 45°, outline 1.5px `#D0D0CC`, fill transparente
- **Atrasado:** quadrado 14×14 rotacionado 45°, preenchido `#E46962`

### Conector entre marcos (timeline do Executive)

- Retângulo 63×2, cor `#3B82F6` quando marcos adjacentes estão concluídos/em-andamento
- Cor `#D0D0CC` quando marcos adjacentes estão não iniciados
- Margens negativas (-6px em cada lado) para encostar nos marcos visualmente

### Accent bar (risk cards)

- 6px de largura, altura-do-card (110px), cor semântica (`--status-*`) pura
- Flexshrink 0, flexível em altura para acompanhar conteúdo

### Severity tags (risk)

- Padding: `4px 10px`, bg pastel do nível, text `#424135` bold small caps (`--size-eyebrow-small`)

### Tabela (slide 03 — Roadmap overview)

- Header: bg `#F1EFDE` (derivado do off-white com leve toque), texto `#4F4E3C` em eyebrow caps
- Linhas: alternância entre `#FFFDEF` (off-white) e branco-bruto, border-top `1px solid #E5E2CE`
- Células de status (squares 12×12): `#3B82F6` se sprint ativo, `#D0D0CC` se futuro, traço `—` se N/A

### Logo

- `assets/m7-logo-dark.png` (196×96 RGBA) → usar em fundos claros (off-white)
- `assets/m7-logo-offwhite.png` (196×96 RGBA) → usar em fundos escuros (Verde Caqui)
- Tamanho de exibição sugerido: 44×44 a 56×56 no canto superior direito

No canvas Paper, o logo é renderizado como texto stylizado `M7` em itálico; para o PPTX usamos o PNG como proxy visual fiel.

---

## Uso por contexto

### Slides escuros (Capa, Agenda, Divider, Closing)

- BG: `#424135`
- Texto principal: `#FFFDEF`
- Eyebrow/accent: `#EEF77C`
- Subtítulo discreto: `#FFFDEF` com opacidade 0.85
- Caption/footer: `#FFFDEF` com opacidade 0.6

### Slides claros (Roadmap Overview, Roadmap Detail, Executive, Risks)

- BG: `#FFFDEF`
- Texto principal: `#424135`
- Body/subtítulo: `#4F4E3C` a `#79755C`
- Caption: `#AEADA8`

### OPR (A4 retrato)

- BG: `#FFFDEF` (página inteira clara)
- Header: faixa 40mm com BG `#424135` e texto off-white — imita a personalidade dos slides escuros
- Zonas internas: off-white com cards em box `#FFFFFF` borda 1px `#E5E2CE`

---

## Palete de referência rápida (copy-paste)

```css
/* Cores */
--m7-primary:       #424135;
--m7-bg-light:      #FFFDEF;
--m7-text-muted:    #4F4E3C;
--m7-text-subtle:   #79755C;
--m7-text-caption:  #AEADA8;
--m7-accent:        #EEF77C;
--status-ok:        #00B050;
--status-progress:  #3B82F6;
--status-warning:   #F59E0B;
--status-critical:  #E46962;
--status-neutral:   #D0D0CC;
--tag-bg-critical:  #FDEDED;
--tag-bg-warning:   #FDF3E0;
--tag-bg-neutral:   #EFEFEC;

/* Tipografia */
font-family: Arial, "ArialMT", system-ui, sans-serif;
--weight-regular: 400;
--weight-bold:    700;
--size-display:   64px;
--size-h1:        32px;
--size-h2:        30px;
--size-h3:        22px;
--size-body:      14px;
--size-small:     12px;
--size-dense:     11px;
--size-caption:   10px;

/* Espaçamento */
--gap-1: 4px;  --gap-2: 8px;  --gap-3: 12px;  --gap-4: 16px;
--gap-5: 18px; --gap-6: 28px;
```
