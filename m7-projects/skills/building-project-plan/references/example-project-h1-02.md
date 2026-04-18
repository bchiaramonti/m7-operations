# Example Project — H1-02 Playbook de Processos

Referencia canonica do projeto-modelo usado para abstrair os 10 templates
e o schema do `Cronograma.xlsx`. Quando ha duvida sobre estrutura, secao
ou visual, **consultar o H1-02**.

## Localizacao no OneDrive

```
/Users/bchiaramonti/Library/CloudStorage/OneDrive-MULTI7CAPITALCONSULTORIALTDA/
└── plan-estrategico/pe-26-30/iniciativas/H1-02_Playbook-de-Processos/
    ├── Cronograma-H1-02-Playbook-de-Processos.xlsx    ← Schema xlsx
    ├── plano-projeto/
    │   ├── plano-projeto.html                          ← Landing
    │   ├── TAP-H1-02-Playbook-de-Processos.pdf
    │   └── artefatos/
    │       ├── contexto-escopo.html                    ← 01
    │       ├── eap.html                                ← 02
    │       ├── roadmap-marcos.html                     ← 03
    │       ├── okrs.html                               ← 04
    │       ├── recursos-dependencias.html              ← 05
    │       ├── plano-comunicacao.html                  ← 06
    │       ├── riscos.html                             ← 07
    │       ├── cronograma.html                         ← 08
    │       └── calendario.html                         ← 09
    ├── H1-02_Playbook_de_Processos.md                  ← Doc-mae portfolio
    └── ../roadmap-h1-2026.html                         ← Reference swim-lane
```

## Resumo do projeto-modelo

| Campo | Valor |
|---|---|
| `project_code` | H1-02 |
| `project_name` | Playbook de Processos |
| `lider` | Bruno Chiaramonti |
| `sponsor` | Nisabro Fujita |
| `period_start` | 2026-03-27 |
| `period_end` | 2026-07-18 |
| `dias` | 90 (planejamento + execucao + encerramento) |
| `n_processos_mapeados` | 9 (P1-P9) |
| `n_pacotes_trabalho` | 68 (5 + 58 + 5) |
| `n_acoes_no_xlsx` | 70 |
| `n_etapas_no_xlsx` | 189 |
| `n_fases_no_xlsx` | 6 (3 raiz + 3 sub-fases) |
| `n_riscos` | 7 (R1-R7, mapeados em heatmap 3x3) |
| `n_okrs` | 3 objetivos × 3 KRs = 9 KRs |
| `n_team_members` | 7 (1 lider + 6 donos de processo) |
| `n_artefatos_html` | 10 (1 landing + 9 artefatos) |
| `n_marcos` | 6 (Planejamento Concluido, Cadeia Valor, etc.) |

## Mapeamento por artefato — o que olhar

### Landing (`plano-projeto.html`)
- **Hero:** gradient caqui, badge "Termo de Abertura de Projeto", h1 "Playbook de Processos", subtitle 1 frase, 5 meta-items (Projeto/Lider/Sponsor/Duracao/Periodo)
- **Estrela guia:** caixa caqui destacada com `★` em lime no canto
- **Nav-grid:** 9 cards (auto-fill 310px), cada um com `card-num` (01-09), `h3`, `p` (1-2 linhas), `arrow`

### 01 — `contexto-escopo.html`
- **Estrela-box** repetida (consistencia cross-artefato)
- **Card "Contexto Estrategico":** 3 paragrafos, depois **quote-box** com source "Planejamento Estrategico M7 2026-2030", depois mais paragrafos com `<h3>` "Por que este projeto e fundacao"
- **Scope-grid:** 8 itens em "Faremos" (verde), 6 em "Nao Faremos" (vermelho)
- **Decisoes de Escopo:** 6 linhas (Decisao / Justificativa)
- **Conexoes com Portfolio:** 4 linhas (H1-01, H1-03, H1-04, H1-05) com badges Entrada/Saida

### 02 — `eap.html`
- **Legend:** 4 swatches (N0/N1/N2/N3)
- **Tree:** root "H1-02 Playbook de Processos" → 3 fases (Planejamento, Execucao, Encerramento) → Execucao tem 3 sub-fases (Cadeia Valor, Verticais, Transversais) → cada sub-fase tem 4-6 processos → cada processo tem 6 pacotes
- **Wp-table:** 6 linhas (x.y.1 a x.y.6) explicando o template de pacotes por processo
- **Note-box:** "5 (Plan) + 58 (Exec) + 5 (Enc) = **68 pacotes de trabalho**"

### 03 — `roadmap-marcos.html`
- **Phase-bar:** 3 segmentos com flex 1/5/0.5 (Planejamento curto, Execucao longa, Encerramento minusculo)
- **Timeline:** 12 blocks (Plan + 1 Cadeia + 6 Verticais + 3 Transversais + Encerramento) com classes `phase-start`, `cadeia`, `transversal`, `encerramento`
- **Dep-flow:** 3 linhas mostrando `Plan → CdV+P5 → P3-P8 → P9-P2 → Encerramento`
- **Milestone-grid:** 6 marcos, 2 marcados `.major` (`Todas Verticais`, `Projeto Concluido`)
- **Swim-lane (NOVA seção, derivada de [`roadmap-h1-2026.html`](file:///Users/bchiaramonti/Library/CloudStorage/OneDrive-MULTI7CAPITALCONSULTORIALTDA/plan-estrategico/pe-26-30/iniciativas/roadmap-h1-2026.html)):** lanes `F1 Planejamento` (`v-dark`), `F2 Cadeia Valor` (`v-purple`), `F3 Verticais` (`v-blue`), `F4 Transversais` (`v-teal`), `F5 Encerramento` (`v-amber`), `GOV` (`v-gov` com qrs)

### 04 — `okrs.html`
- **3 obj-cards** (caqui, com obj-num "Objetivo N" + h2)
- **9 KRs total** (3 por objetivo), cada um com `kr-num` numerado (1.1, 1.2, ..., 3.3), `h4`, `metric` (com `<strong>`), `kr-target` (ex: "9/9", "≥80%", "100%")
- **Cadence-box:** 3 cadence-items (Semanal / A cada Processo / Mensal)

### 05 — `recursos-dependencias.html`
- **Team-grid:** 7 cards (1 `.lead` para Bruno + 6 donos de processo)
- **Alloc-table:** Pessoa × 11 periodos cruzados; Bruno em todos os periodos com classes diferentes (Plan/CdV+P5/P3/P6/P4/P7/P8/P9/P1/P2/Enc)
- **Dep-table:** 4 dependencias (H1-01, H1-03, H1-04, H1-05)
- **Invest-card:** 4 paragrafos explicando "natureza documental + tempo dos donos como recurso critico"

### 06 — `plano-comunicacao.html`
- **Ritual-grid:** 6 cards, 2 com `.highlight` (Discovery, Validacao)
- **Raci-table:** 8 atividades × 5 papeis (Bruno / Dono / Sponsor / Time CRM / Diretoria), 28 atribuicoes RACI total
- **Channel-grid:** 4 canais (Teams, Reunioes, OneDrive, ClickUp)

### 07 — `riscos.html`
- **Heatmap 3x3:** 7 riscos posicionados (R1+R3 em high-high, R2+R6+R7 em med-high, R5 em high-med, R4 em med-med)
- **Risk-legend:** 7 risk-items, 2 com `.crit` (R1, R3), 4 com `.high`, 1 com `.medium`
- **Risk-detail table:** 7 linhas com Severidade + Contramedida + Acao + Trigger

### 08 — `cronograma.html`
- **Stats:** 6 fases / 70 acoes / 189 etapas / 90 dias
- **Filter-bar:** 4 botoes
- **Wh-table:** 265 linhas (1+5+58+5+189+ subtotais), com filterRows() JS

### 09 — `calendario.html`
- **Stats:** 9 Discovery + 9 Validacoes + 15 Check-ins + 3 Status Reports + 9 Handoffs + 6 Marcos
- **Calendar grid:** 4 meses (abr/mai/jun/jul 2026), eventos coloridos por tipo
- **Summary-table:** ~50 eventos listados em ordem cronologica

## Como esta skill se compara ao H1-02

A skill produz output **estruturalmente identico** ao H1-02 quando o
`data` JSON e completo. As **diferencas esperadas** sao:

| Aspecto | H1-02 (manual) | Skill (gerado) |
|---|---|---|
| Conteudo semantico | Especifico do projeto Playbook | Variavel — vem do `data` JSON |
| CSS | Inline em cada arquivo | Inline em cada arquivo (template) |
| Tokens | M7-2026 hardcoded | M7-2026 hardcoded em templates |
| Logo | Embedded base64 (cada arquivo tem copia) | Embedded base64 (carregado de `templates/assets/m7-logo-offwhite.b64`) |
| Estrutura de secoes | Manual em cada HTML | Templates com `{{placeholders}}` substituidos por Python |
| Cronograma rows | Hardcoded | Lidos do `Cronograma.xlsx` |
| Calendar events | Hardcoded em JS | `events_json` injetado a partir de `derive_calendar_events.py` |

**Bug = divergencia visual ou estrutural entre o output desta skill e o H1-02** (excluindo conteudo semantico, que e esperado variar por projeto).

## Como usar como benchmark

1. **Antes de release:** gerar plano de teste com `data` proximo ao H1-02; abrir cada HTML lado-a-lado com o original
2. **Bug visual:** se algo difere visualmente do H1-02 (alinhamento, espacamento, cor), abrir issue e corrigir o template correspondente
3. **Bug estrutural:** se uma secao esta faltando, na ordem errada, ou tem markup diferente, atualizar `render_html.py` (a logica de buildup)
4. **Validacao automatica:** spec do skill define checklist em "Checklist de Validacao" — toda mudanca deve passar

## Rodar a skill replicando H1-02

Para gerar uma replica funcional do H1-02 com a skill (uso interno de QA):

1. Compor `data` JSON com os campos do H1-02 (project_name, lider, sponsor, periodo, estrela_guia, contexto, eap, roadmap, okrs, recursos, comunicacao, riscos)
2. Gerar `Cronograma.xlsx` a partir das 265 linhas do H1-02 (parser do `Cronograma-H1-02-Playbook-de-Processos.xlsx` → JSON rows)
3. Rodar `derive_calendar_events.py` para gerar `data.events`
4. Rodar `render_html.py --input plan.json --xlsx ... --output 1-planning/`
5. Comparar visualmente com `H1-02_Playbook-de-Processos/plano-projeto/`

Diferencas semanticas (texto especifico do projeto) sao esperadas. Diferencas estruturais ou visuais nao deveriam existir.
