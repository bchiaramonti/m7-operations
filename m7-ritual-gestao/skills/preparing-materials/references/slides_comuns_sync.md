# slides_comuns_sync.md — Sync default ↔ PJ2 (A4 da S1)

> Output da Frente A4 da Sessão 1 (`C:\Users\pedro\.claude\plans\sess-o-1-quizzical-corbato.md`).
> Versão: 2026-05-15 · Política: duplicação inicial + refator `_common.py` agendado para S2-B6.

---

## Escopo da S1-A4

A1 (Frente A) traz 8 fixes globais ao default (`build_deck.py` + `ritual.tmpl.html`). PJ2 (`build_deck_pj2.py` + `ritual-pj2.tmpl.html`) ficou defasado nesta semana e precisa de port manual. O `_common.py` (módulo compartilhado) entra em S2-B6 quando o schema unificado WBR canonical eliminar fonte de divergência.

Os 4 slides considerados "comuns" entre os 2 builders são: Capa, Agenda, Riscos · Alertas, Consolidado. Slides únicos PJ2 (eixo canal Inv/Cred/Outros, fechamento mensal multi-vert) ficam fora do escopo de sync.

## Tabela de sync

| Fix | Slide | Default (atual S1) | PJ2 (atual S1) | Status |
|---|---|---|---|---|
| **A1#1** Override título capa (`apresentacao.titulo_publico`) | Capa | ✓ `render_capa_agenda_meta:1781` — fallback chain `titulo_publico → vertical_crm.capitalize() → wbr.metadata.vertical.capitalize()` | ✓ `_resolve_pj2_globals` lê `apresentacao.titulo_publico`; fallback para `metadata.verticais_display` / `verticais` joined | **sync OK** |
| **A1#2** Badge "fechamento DD/MM" condicional | Capa | ✓ `_show_fechamento_badge = effective_modo in ("fechamento", "combinado")`; placeholder `{{FECHAMENTO_SUFFIX}}` em template | ✓ `PJ2_EFFECTIVE_MODO` global resolvido em `_resolve_pj2_globals`; `_fechamento_suffix` inline em `render_capa`; `PJ2_DATA_FECHAMENTO_DISPLAY` deriva de `wbr.data_referencia` | **sync OK** |
| **A1#3a** Matriz N3 — meta nunca vazia | Matriz | ✓ `cell_for` no else branch removeu "ref"; mostra "—" + linha 3 meta abs quando numérica | n/a — PJ2 usa `dt_row` (estrutura diferente, eixo canal). Já mostra "—" quando vazio. | **n/a** (sem matriz N3 unificada) |
| **A1#3b** Matriz N3 — font-size +25% | Matriz | ✓ `.mx-row.data .col-ind` 16→20px; dense 13→16px; ultra-dense 11→14px | ✓ CSS embedded em `build_deck_pj2.py` linha 996 — 13→16px | **sync OK** |
| **A1#4** Cell padrão Realizado/pct/meta | Matriz | ✓ `cell_for` else branch padronizado em 3 linhas | n/a — `dt_row` tem layout próprio (4 colunas: ind/meta/real/desvio) | **n/a** |
| **A1#5** Slide Riscos enriquecido com `causa_raiz_resumo` | Dashboard esp / Riscos | ✓ `_esp_riscos` linha 5392 (bad) e 5406 (warn) consomem `causa_raiz_resumo` com fallback graceful | ✓ `gen_riscos_analise` consome `causa_raiz_resumo` por indicador; fallback para textos genéricos legados | **sync OK** |
| **A1#6** Pipeline overflow scroll bar | Pipeline esp | ✓ `.pipe-card { min-height: 0; overflow-y: auto; }` | TODO — PJ2 usa `.pipe-card-side` (estrutura diferente). Aplicar mesma diretriz `overflow-y: auto` quando bugar | **PJ2 TODO** |
| **A1#7** Donut 4 fatias paleta+ordem; pill verde Concluída + check + date_done | PA Status / PA Vencendo | ✓ `_render_donut_svg` ordem Concluídas→No prazo→Atenção→Atrasada, paleta `#2e7d32 / #4caf50 / #ffc107 / #e40014`; `_pa_row` pill "✓ CONCLUIDA" + label "Concluído em" + `date_done`; CSS `.pill-done` verde | n/a — PJ2 `render_pa_status` é placeholder "0 PAs ativas" (primeiro ritual); quando PA real existir em PJ2, replicar lógica completa | **PJ2 pendente** (próximo ciclo PJ2) |
| **A1#8** Gatekeepers #16/#17 | render_pa_slides + main | ✓ `_gatekeeper_check` + `_gatekeeper_numeric_close`; #16 em `render_pa_slides`, #17 chamado no main após renders | TODO — adicionar `_gatekeeper_pj2_*` ou importar do `_common.py` (S2-B6) | **PJ2 TODO** |

## Bugs adicionais detectados e fixados durante S1

| Bug | Causa raiz | Fix |
|---|---|---|
| `em_dia_proximas` alias aplicado APÓS bucketing | `_STATUS_CONCLUIDAS` filter + bucket calc lia `em_dia_priorizadas` antes do alias ser aplicado, resultando em `n_em_dia = 0` quando WBR usa schema legacy `em_dia_proximas` | Movido alias para ANTES do bucket calc em `render_pa_slides` (detectado por gatekeeper #16) |
| Summary card Estagnação mostrando pct_atingimento ao invés de % pipeline parado | `pct_estag = estag_n2.get("pct")` (lê pct_atingimento da meta) | Trocar por `estag_n2.get("realizado")` em 2 lugares (build_deck.py linha 5880 + 6360) |
| Coluna Δ vs prev cycle no Dashboard usando pct_atingimento ao invés de variação do realizado | Card declarava `n2_value_field: pct` (=pct_atingimento), fazendo `_calc_delta` ler variação errada | `card_con_n3_001.yaml:610` `n2_value_field: pct → realizado`. SEG WL/RE já estavam corretos. PJ2 n/a (não usa essa view) |

## Roadmap S2-B6: refator `_common.py`

Quando: S2 (Pipeline Robustness).

O quê: extrair utilitários compartilhados entre `build_deck.py` e `build_deck_pj2.py` para `m7-operations/m7-ritual-gestao/skills/preparing-materials/scripts/_common.py`. Candidatos:

- `_derive_n1_raw_from_dados` (Total meta raw)
- `_resolve_n2` Sem Esp bridge logic
- `load_clickup_tasks` (escopo_ritual_passado + ad_hoc)
- `_calc_delta` Fallback 3.5
- `_gatekeeper_check` + `_gatekeeper_numeric_close` (helpers SSoT)
- `_gatekeeper_17_consolidado_vs_dashboard` (pode generalizar)
- Field aliases (`_N1_VALUE_FALLBACKS`, `_N2_VALUE_FALLBACKS`, etc.)
- Status filters (`_STATUS_CONCLUIDAS`, `_STATUS_CANCELADAS` quando renomeado)

Justificativa: hoje os 2 builders divergem por necessidade (eixos visuais diferentes), mas reusam ~30% da lógica. `_common.py` mata a dívida técnica de manter 2 cópias em sync manual e habilita gatekeepers #16/#17 plenos no PJ2.

## Validação

Após sync (rebuild dos 4 decks em `c:\tmp\rebuild-s1\`):
- SEG WL · 2.78 MB · gatekeepers #16 + #17 (4/4) OK
- SEG RE · 1.46 MB · gatekeeper #16 OK; #17 skip (sem dados — memory `reference_seg_re_ch_gap`)
- CON N3 · 3.54 MB · gatekeepers #16 + #17 (4/4) OK
- PJ2 N2 · 1.29 MB · 17 slides gerados; gatekeepers PJ2 TODO (S2-B6)

## Iter 2-4 (2026-05-15/16): polish visual + PJ2 sync completo

Após iteração com usuário pós-rebuild inicial:

**Default (`ritual.tmpl.html` + `build_deck.py`):**
- Cell layout HORIZONTAL via grid 2 colunas (num esquerda + stack pct/meta direita)
- Padding row +20% (22px 24px → 26px 29px) + min-height 77px
- Font `.cell .num` (realizado) +12,5% (22 → 25px)
- Font `.cell .meta` (pct atingimento) +12,5%+5% (12 → 14 → 15px)
- Font `.cell .sub` (meta absoluta) +5% (11 → 12px)
- Border-color row/cell: `var(--vc-50)` → `#e0e0de` (mais visível mas leve)
- Modo `--modo atual` removeu badge "fechamento" do ritual N3 semanal normal
- Bugs corrigidos: pct_estag lendo pct_atingimento ao invés de realizado; Δ vs prev cycle usando pct_atingimento; iteração `_pct_sem_atividade` matchava `_volume` derived
- Indicador "Oport. Sem Atividade Planejada" → "Sem Ativ. ou Atras. CRM"
  - Cards CON/WL/RE atualizados
  - Cell render: `qty (X%)` onde X% = qty_sem_atividade / qty_ativas × 100
  - Cor proporcional: `0` verde, `0-20%` amarelo, `21%+` vermelho (override da regra meta=0 binária)
  - Aplicado tanto na **matriz consolidada** quanto no **Dashboard por esp** (`_esp_dashboard_rows`)
- Indicador "Oport. Estagnadas (qty)" enriquecido com volume entre parênteses (`qty (R$ vol_compact)`)
  - Aplicado em matriz E Dashboard por esp
- Funil viewBox H dinâmico (suporta 7 estágios SEG RE/WL sem cortar) + text fill adaptativo (texto não some no BG branco quando trapézio estreito)

**PJ2 sidecar (`build_deck_pj2.py` + `ritual-pj2.tmpl.html`):**
- CSS embedded: padding 26px 29px / min-height 77px / border `#e0e0de` / num 25px / meta 15px / sub 12px
- Cell layout horizontal via grid (sync default)
- `_matriz_row_est_qty` ganhou display `qty (R$ vol_compact)` por canal (Outros/Cred/Inv/Total)
- `_matriz_row_sem_mov` ganhou display `qty (X%)` + cor proporcional 0=verde/0-20%=amarelo/21%+=vermelho
- `.pipe-card-side` ganhou `overflow-y: auto` (scrollbar quando conteúdo excede)
- Gatekeepers #16/#17 PJ2 — TODO S2-B6 (sem PA real no PJ2 atual + complexidade adapter multi-vert)
- Cards PJ2: rename não necessário (PJ2 hardcoded sem matriz_views declarativa)

**Pendente externamente:**
- E3 emitir `causa_raiz_resumo` no canonical (Riscos enriquecidos — S2-B4)
- E6 emitir `n2.{esp}.volume_estagnado` no canonical (remove fallback `dados_consolidados` — S2-B4)
- E6 emitir `vol_em_risco` no nível Total do indicador (Estagnadas CRM Total atualmente sem vol no PJ2 — S2-B4)
- collect.py incluir `date_closed` no JSON ClickUp ("Concluído em" hoje fallback `due_date` — S2-B4)
- Indicador YAML `aggregation_rule: ratio_from_components` para `*_pct_ativas` (S2-B2)
- `_common.py` extraindo utilitários compartilhados (gatekeepers PJ2, helpers de matriz) — S2-B6

## Iter 8 (2026-05-17): inversão da direção do sync — default segue PJ2

**Contexto:** após iter 5-7 onde apliquei densidade dense/ultra-dense no PJ2 para alinhar com CON N3, usuário identificou que o **PJ2 original era o "tamanho ideal"** e o que precisava mudar era o **default** (que estava espaçoso demais). Inversão da direção:

**Default `.rank-row` (ritual.tmpl.html) — sync com PJ2 `.canal-row`:**
- `min-height`: 34 → **32px**
- Padding row: 0 → **7px 0**
- `.rname` padding: `9px 16px` (vertical extra) → **`0 16px`** (sem padding vertical, controlado por min-height)
- `.rname`: + `white-space: nowrap; overflow: hidden; text-overflow: ellipsis` (sync PJ2)
- `.rcell` padding: `8px 10px` → **`4px 10px`**
- `.mini .fb` font: 11px → **12px**
- Border: `var(--vc-50)` → **`#e0e0de`**
- Border `.rcell` left: `var(--vc-100)` → **`#e0e0de`**

**PJ2 revertido ao spec compacto original (REVERT iter 7):**
- `.canal-row`: `min-height: 32px; padding: 7px 0`
- `.canal-row .nm`: `padding: 0 14px`
- `.canal-row .cn`: `padding: 4px 8px`
- `.canal-row .cn .mini`: simples (sem flex-grow extra)

**Ordenação por CRIADAS DESC em ambos builders:**
- **Default `_render_rank_rows_v2` (build_deck.py:4782):** `_sort_key` agora retorna `(prio, -criadas_qty, nome_lower)`. Esp_direct (`(esp)` suffix) sempre topo. Quem criou mais fica em cima; desempate alfabético.
- **PJ2 `render_analise_canal` (build_deck_pj2.py:2134):** `assesores_canal.sort` por `(-criadas_atual, -ativas_qty, nome)`. Primary criadas DESC, desempate ativas DESC, alfabético.
- **Garantia de coerência horizontal:** linhas reordenadas mantêm Ativas/Fechadas/Estagnadas alinhadas no assessor — a mudança é só na ordem das rows, valores per assessor preservados.

**Validação visual (4 decks em `c:\tmp\rebuild-s1\`):**
- ✅ CON N3, SEG WL, SEG RE — rank-row visual idêntico ao PJ2 canal-row
- ✅ PJ2 — Ari Alencar / Camila Quintino topo do Squad Investimentos; Cleonildo topo Crédito
- ✅ Usuário aprovou: "está perfeito"

**S1 fechada em 2026-05-17.**

## Memory aplicada

- `feedback_session_segmentation` — A4 mantido em sub-frente da S1 (não foi para sessão separada)
- `feedback_canonical_data_json` — WBR é SoT único; A1#5 (causa_raiz_resumo) decisão final é emissão no canonical
- `reference_pj2_no_folder` — PJ2 sidecar tem builder próprio + template próprio; sync via _common.py é S2-B6
