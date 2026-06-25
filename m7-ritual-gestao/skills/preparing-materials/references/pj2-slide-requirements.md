# PJ2 Slide Requirements (V13 → Plugin Step 8)

**Origem:** transcrição Fireflies "Ajustes PJ2" (2026-05-11) — meeting Bruno + Pedro Villarroel.

Este documento é o **contrato vivo** entre o `build_pj2_deck.py` V13 (workaround offline editado em 11/05/2026) e o plugin oficial `m7-ritual-gestao/preparing-materials/build_deck.py` (template `ritual-pj2.tmpl.html` que será criado no **Step 8** da Sessão 5).

**Como usar:** quando a Sessão 5 chegar (criar template pj2 + slides novos), basta seguir cada item desta lista — sem redescobrir o que precisa mudar.

**Convenção:**
- 🟢 = aplicável a qualquer vertical/nível (multi-vertical, multi-N, multi-subnível)
- 🔵 = específico PJ2 (não replicar para Cards N3 single-vertical)
- 🖼 = mexe no builder/template (V13 + plugin Step 8)
- ⚙ = mexe em indicator YAML / Card / m7-controle (Sessão 3b)
- 🔍 = investigação pendente
- ⏰ = one-off desta reunião 12/05 (não vira requisito permanente)

---

## Estrutura atual do deck PJ2 V13 (21 slides modo combinado)

Antes de listar as edições, registro a estrutura V13 atual para referência:

| # | Slide | Função no V13 |
|---|---|---|
| 1 | Capa | `render_capa()` linha 765 |
| 2 | Agenda | `render_agenda()` linha 782 |
| 3 | Subcapa Bloco I — Fechamento | `render_subcapa()` linha 797 |
| 4 | Fechamento Visão Geral PJ2 | `render_fech_visao_geral()` linha 831 |
| 5 | Fechamento Vertical Seguros | `render_fech_vertical()` linha 893 |
| 6 | Fechamento Vertical Consórcios | `render_fech_vertical()` linha 893 |
| 7 | Diretrizes | `render_diretrizes()` linha 972 |
| 8 | Subcapa Bloco II — Mês até agora | `render_subcapa()` linha 797 |
| 9 | Matriz Seguros | `render_matriz()` linha 1260 |
| 10 | Matriz Consórcios | `render_matriz()` linha 1260 |
| 11 | PA Status | `render_pa_status()` linha 1304 |
| 12 | PA Lista | `render_pa_lista()` linha 1315 |
| 13 | Direto Seguros (Month-to-Date) | `render_direto()` linha 1392 |
| 14 | Análise por Canal Seguros | `render_analise_canal()` linha 1441 |
| 15 | Pipeline Seguros | `render_pipeline()` linha 1610 |
| 16 | Direto Consórcios | `render_direto()` linha 1392 |
| 17 | Análise por Canal Consórcios | `render_analise_canal()` linha 1441 |
| 18 | Pipeline Consórcios | `render_pipeline()` linha 1610 |
| 19 | Consolidado Seguros | `render_consolidado()` linha 1707 |
| 20 | Consolidado Consórcios | `render_consolidado()` linha 1707 |
| 21 | Encerramento (Próximos Passos atual) | `render_encerramento()` linha 1785 |

---

## Lista de edições (numeradas 1-25)

### #1 — Slide Agenda: bloco "Pontos discutidos na última N2"
- **Categoria:** 🔵🖼
- **Posição:** primeiro item da agenda (antes dos blocos atuais)
- **Fonte:** ata alinhamento comercial (`C:\Users\pedro\Downloads\ata alinhamento comercial.pdf`)
- **V13:** TODO — função `render_agenda()` linha 782
- **Plugin Step 8:** template `ritual-pj2.tmpl.html` deve renderizar bloco extra na agenda quando `card.metadata.label_responsavel == "canal"` (PJ2). Cards N3 single-vertical não têm "última N2" por definição.

### #2 — Slide Fechamento Mensal (visão geral): dividir visualmente Seg vs Cons
- **Categoria:** 🔵🖼
- **V13:** TODO — função `render_fech_visao_geral()` linha 831
- **Plugin Step 8:** novo placeholder de divisor visual entre 2 colunas (Seg | Cons) com gutter/borda nítida.

### #3 — Slide Fechamento Mensal (visão geral): título Seguros "Empresarial e Vida"
- **Categoria:** 🔵🖼
- **V13:** TODO — função `render_fech_visao_geral()` linha 831
- **Plugin Step 8:** label dinâmico baseado em `card.metadata.verticais_display` (futuro campo) ou hardcoded para PJ2 v1.

### #4 — Padrão de cards: barrinha de atingimento substitui "xx% da meta · meta R$ xxK"
- **Categoria:** 🟢🖼 (aplica em TODOS os slides com cards de indicador)
- **Especificação visual:**
  - Barra abaixo do valor realizado, escala 0–100%
  - Cor da barra segue intervalos de semáforos (verde / amarelo / vermelho — usando tokens M7-2026)
  - **"xx%" DENTRO da barra**, posicionado seguindo o preenchimento (vai se movendo conforme % cresce)
  - **"meta R$ xxK" FORA da barra**, à direita
- **V13:** TODO — helpers de cards em `render_fech_vertical()` linha 893, `render_matriz()` linha 1260, `render_direto()` linha 1392, `render_pipeline()` linha 1610, `render_consolidado()` linha 1707
- **Plugin Step 8:** criar componente CSS reutilizável `.atingimento-bar` no `ritual-pj2.tmpl.html`. Considerar adicionar também no `ritual.tmpl.html` legado (decisão futura).

### #5 — Aumentar fonte (números e letras proporcionalmente)
- **Categoria:** 🟢🖼
- **Aplicação:** todos os slides com cards
- **V13:** TODO — CSS_BASE linha 462 (ajustar `.fc-row .fc-val` e similares)
- **Plugin Step 8:** ajustar CSS do template novo

### #6 — Sufixo "CRM" nos indicadores do Bitrix
- **Categoria:** 🟢⚙🖼
- **Recebem sufixo:** Oportunidades Criadas, Taxa de Conversão, Oportunidades Ativas, Oportunidades Estagnadas, Oportunidades Sem Atividade (a-renomear)
- **NÃO recebem sufixo:** Receita, Volume, Quantidade de Contratos (fonte Excel/banco)
- **V13:** TODO — labels em `render_fech_vertical()`, `render_matriz()`, `render_direto()`, `render_pipeline()`, `render_consolidado()`
- **Indicator YAML (m7-metas Sessão 3b):** adicionar campo `display_name` ou suffix logic no `_schema.yaml` v3.2. Cards/builders consomem.
- **Card YAML (Sessão 3b):** referenciar via `kpi_references[].display_suffix` opcional ou usar a do indicator.

### #7 — Pareto Win/Lose: filtrar "Outros" zerados
- **Categoria:** 🟢🖼
- **Regra:** em "Outros", só aparecem assessores que TÊM Oportunidade Criada OU Fechada. Zerados em ambos → removidos.
- **V13:** TODO — `render_fech_vertical()` linha 893 (Pareto Criadas vs Fechadas)
- **Plugin Step 8:** mesma regra aplicada na função correspondente.

### #8 — Slide "Diretrizes para o mês seguinte" → REMOVER
- **Categoria:** 🟢🖼
- **V13:** TODO — remover `render_diretrizes()` linha 972 do array de slides ou substituir
- **Plugin Step 8:** `MODO_PHASES["fechamento"]["diretrizes"]` → substituir por nova fase `analise_problemas` (ver #9)

### #9 — Novo slide "Análise do que deu errado" (substitui Diretrizes)
- **Categoria:** 🟢🖼⚙
- **Layout:** dividido como slide 04 (Fechamento Vertical)
- **Foco:** lead indicators em **vermelho** trazem análise causal
- **Lógica:** "criei X, fechei Y → taxa Z%. Se meta de conversão era T%, faltou criar mais OU converter melhor"
- **2 indicadores NOVOS no slide Fechamento (entre Ticket Médio e Tx Conversão):**
  - 🟢⚙ **Tempo de Ciclo** — Pedro precisa **trazer valores reais** para Bruno definir meta + coloração
  - 🟢⚙ **Estagnação Mediana % dos ativos** — meta **40%** (último indicador da lista)
- **V13:** TODO — nova função `render_analise_problemas()` substitui `render_diretrizes()`
- **Plugin Step 8:** mesma estrutura

### #10 — Tempo de Ciclo: considerar deals com ciclo < 2 dias (deal direto)
- **Categoria:** 🟢⚙
- **Razão:** Bruno: "não necessariamente passa por todas as fases, mas se o tempo de ciclo é menor que 2 dias, você considera"
- **Indicator YAML novo:** `tempo_de_ciclo_funil_con.yaml` / `tempo_de_ciclo_funil_seg.yaml` (Sessão 3b ou pós-banco)

### #11 — Alinhar Taxa de Conversão para 25% em AMBAS Cons e Seg
- **Categoria:** 🔵⚙
- **Card PJ2:** atualmente `taxa_conversao_funil_con.valor: 0.30` → mudar para `0.25`
- **Card PJ2:** `taxa_conversao_funil_seg.valor: 0.25` → manter

### #12 — Quantidade Cons vem de centro_custo (linhas no mês, data_venda)
- **Categoria:** 🟢⚙
- **Mapeamento canal:**
  - Alta Renda / Private / Mesa / Corporate → **Investimentos**
  - Crédito → **Crédito**
  - Resto → **Outros M7**
- **Aplicação:** indicator `quantidade_consorcio_mensal_pj2.yaml` (Sessão 3b Fase D)

### #13 — Quantidade Seg continua Bitrix (POR ENQUANTO)
- **Categoria:** 🟢⚙
- **Pendente:** até tabela `apolice_seguros` no banco estar regularizada (pós-banco)
- **Indicator YAML:** `quantidade_seguros_mensal_pj2.yaml` (Sessão 3b Fase D)

### #14 — Renomear "Sem Movimentação" → "Sem atividades ou atrasadas"
- **Categoria:** 🟢⚙🖼
- **Aplica em:** indicator YAML (`oportunidades_sem_atividade_planejada_funil.yaml`), Card YAML, V13 labels, template plugin, slide-structure.md
- **Forma curta** (se ficar grande no card): "Sem Ativ. ou Atras."

### #15 — Renomear "Ticket" → "Ticket Médio Pipeline"
- **Categoria:** 🟢⚙🖼
- **Aplica em:** slides Oportunidades Ativas / Pipeline (cards de ticket de oportunidades ativas)
- **Distinção:** "Ticket Médio Pipeline" ≠ "Ticket Médio" (este último refere-se a Receita/Quantidade do mês fechado)

### #16 — Renomear "Quantidade" → "Contratos Fechados" (ou "Apólices Fechadas")
- **Categoria:** 🟢⚙🖼
- **Aplica em:** quando o indicador "Quantidade" se refere a convertidos do mês
  - Cons: "Contratos Fechados"
  - Seg: "Apólices Fechadas"
- **Aplica em:** indicator YAML (`quantidade_consorcio_mensal`, `quantidade_seguros_mensal`), Card, V13, template, slide-structure.md

### #17 — Nova estrutura PJ2: vertical por vertical
- **Categoria:** 🔵🖼
- **Ordem nova:** Matriz Seguros → Análise por Canal Seguros → Pipeline Seguros → Matriz Cons → Análise por Canal Cons → Pipeline Cons
- **Eliminação:** slide "Direto" (Month-to-Date) eliminado (ver #18)
- **V13:** atualizar array de slides em `main()` linhas 1938-1960
- **Plugin Step 8:** dispatch table de slides PJ2

### #18 — Remover slide "Direto Seguros — Maio 2026" APENAS para PJ2
- **Categoria:** 🔵🖼
- **Razão:** duplica info já presente em Matriz + Análise por Canal
- **V13:** remover `render_direto()` linhas 13 e 16 do array de slides
- **Plugin Step 8:** template `ritual-pj2.tmpl.html` não inclui slides Direto
- **Importante:** em outros rituais (N3 single-vert) **MANTER** + validar coluna "vs semana anterior"

### #19 — Remover 2 slides vazios de Consórcio (Status PA + Lista PA)
- **Categoria:** 🔵🖼⏰
- **Razão:** ciclo novo, sem PAs ainda
- **V13:** condicionar `render_pa_status()` e `render_pa_lista()` a PA-count > 0
- **Plugin Step 8:** condicionamento dinâmico via dados de PA

### #20 — Remover slides "Síntese Seguros" + "Síntese Consórcio"
- **Categoria:** 🟢🖼
- **V13:** identificar onde estão (provavelmente parte de `render_consolidado()` ou separados) e remover
- **Plugin Step 8:** não criar esses slides no template novo

### #21 — Substituir "Próximos Passos" por "Conclusão" com velocímetros
- **Categoria:** 🟢🖼
- **Especificação visual (image 3 referência):**
  - 3 velocímetros (gauge charts) — meio arco/semicircular
  - Realizado preenchendo o arco
  - Valor do realizado à **esquerda** do arco
  - Meta como total do arco preenchível (valor à **direita**)
  - % de atingimento **abaixo do arco**
- **Conteúdo PJ2:**
  - Velocímetro 1: Receita Seguros (Vertical 01)
  - Velocímetro 2: Receita Consórcios (Vertical 02)
  - Velocímetro 3: **Total PJ2 somado** (meta total + realizado total, **APENAS para Receita**)
- **Conteúdo outras verticais (N3/N2 single-vert):**
  - Velocímetro por **Desdobramento** (especialista ou canal) + Total Vertical
- **V13:** substituir `render_encerramento()` linha 1785 por `render_conclusao_velocimetros()`
- **Plugin Step 8:** mesma estrutura

### #22 — Projetar APENAS M0 (mês corrente)
- **Categoria:** 🟢🖼⏰
- **Razão:** Pedro tem reunião marcada com Joel sobre método M1
- **V13:** garantir que M1 não aparece em nenhum slide (Fechamento, Análise por Canal, Pipeline, Conclusão)
- **Plugin Step 8:** futuro suporte M1 quando método for definido

### #23 — Investigação: discrepância 47 vs 52 oportunidades criadas em Investimentos
- **Categoria:** 🔍 → **RESOLVIDO (decisão: manter + disclaimer)**
- **Sintoma:** soma do squad Pareto mostra 47 (Inv), card de Investimentos mostra 52
- **Causa raiz confirmada (Batch F 2026-05-11):**
  - 2 fontes de classificação distintas no V13 offline:
    - **Pareto** (`extract_per_assessor_cons` em [build_pj2_deck.py:167](c:/...build_pj2_deck.py)): usa apenas Bitrix (UF_CRM_1758122406 MKT + ASSIGNED_BY)
    - **Card / n2_agregado** (gerado por `pj2_offline_pipeline.py`): usa as 4 fontes do `de-para-canal.yaml` incluindo **centro_custo do ClickHouse** (`consorcio_receita`)
  - Total reconciliado: 75 deals em ambos (47+2+26 Bitrix = 52+13+10 Canonical)
  - Diff por canal: Inv +5 / Cred +11 / Outros M7 −16 (CH reclassifica 16 deals "Outros" como Inv/Cred via centro_custo)
- **Decisão Bruno 11/05 (após apresentação de 5 opções):** **Manter como está** + disclaimer visual no slide Fech Vertical com asterisco nos cards (Inv * / Cred *) e nota explicativa no rodapé do slide.
- **Implementação V13:** asterisco no `fc-head inv` e `fc-head cred` + `<div class="fech-vert-disclaimer">` antes do slide_foot.
- **Plugin Step 8:** mesma estratégia (disclaimer + asterisco) quando indicators `_pj2` finais usarem mapping canonical CH+Bitrix mas Pareto continuar Bitrix-only. Quando WBR canonical tiver per-assessor consolidado (pós-Fase D Sessão 3b), revisitar — pode usar uma fonte única e eliminar disclaimer.

### #24 — Caso Tereza ~2 deals criados sem assessor (Q1: ignorar para apresentação)
- **Categoria:** 🔍⏰
- **Decisão Bruno:** ignorar para apresentação amanhã

### #25 — Novo slide "NPS Consórcio" (one-off, append) ⏰
- **Categoria:** 🔵🖼⏰
- **Posição:** ANTES da Matriz de Consórcios do mês atual (entre slide 9 Matriz Seg e slide 10 Matriz Cons na numeração nova)
- **Conteúdo:** Top 3 pontos positivos + Top 3 pontos negativos
- **Fonte:** `C:\Users\pedro\Downloads\Pesquisa NPS - Consórcio(1-20).xlsx`
- **Colunas relevantes:**
  - Nota: "Em uma escala de 0 a 10, como você avalia o Consórcio M7? Considere desde a captação até o pós-venda."
  - Motivo: "O que te levou a dar essa nota? Sinta-se à vontade para expressar sua opinião e sugerir melhorias que nos ajudem a evoluir."
- **Geração:** script standalone à parte do V13, adicionado por **Append HTML** ao deck final
- **Plugin Step 8:** **NÃO documentar como requisito permanente** — é one-off para 12/05

---

## Coisas que NÃO mexer (decisões Bruno 11/05)

1. **Ticket médio Crédito** está "errado" → **NÃO é mexer no script**. A interpretação correta: validar matrizes de maio onde a **meta M7 Total** de um indicador **não é a soma/média** das metas dos desdobramentos. Crédito ticket = caso onde isso aparece. Registrar como TODO de investigação na sessão de validação.
2. **Receita Samuel apólice fechada no 1º dia de maio** (que era de abril) — não está no nosso poder mover. Não mexer.

---

## Cross-reference com m7-controle Sessão 3b

Itens que precisam ser refletidos em indicators / Cards (m7-controle):

| # da edição | Mudança | Onde aplicar (3b) |
|---|---|---|
| #6 | Sufixo "CRM" nos labels | Indicator YAML (display_name) + Card kpi_references |
| #9 + #10 | Indicators novos: Tempo de Ciclo + Estagnação Mediana % | Criar `tempo_de_ciclo_funil_{vert}.yaml` (pós-banco?) |
| #11 | Taxa de Conversão Cons 30% → 25% | Card PJ2 `metas_ppi.taxa_conversao_funil_con.valor: 0.25` |
| #12 | Quantidade Cons via centro_custo | Indicator `quantidade_consorcio_mensal_pj2.yaml` |
| #13 | Quantidade Seg via Bitrix (por enquanto) | Indicator `quantidade_seguros_mensal_pj2.yaml` |
| #14 | Renomear "Sem Movimentação" | Indicator + Card + builders |
| #15 | "Ticket" → "Ticket Médio Pipeline" | Labels Card + builders |
| #16 | "Quantidade" → "Contratos Fechados" / "Apólices Fechadas" | Indicator display_name + Card + builders |

---

## Batch I — Pós-validação reunião (2026-05-12 manhã)

Edits aplicados no V13 (`build_pj2_deck.py` + `compute_tempo_ciclo_estagnacao.py`) APÓS a Sessão 3c (Batches A-H + REVIEW 1-8). Originados de validação visual do deck rodada pelo usuário 12/05 antes da reunião N2 PJ2 das 14h.

### #26 — Ticket Médio recalculado dinamicamente vol/qty_won

- **Categoria:** 🟢🖼
- **Edição (2026-05-12):** Em `render_fech_visao_geral` (Image 1+2) e `render_fech_vertical` (Images 3+4+5), o `ticket_medio_*_fechamento` é **recalculado em runtime** como `vol_canal / qty_won_canal` (asses_data Bitrix-100%), substituindo valores pré-computados no WBR que estavam inconsistentes com a qty exibida.
- **Razão:** Usuário validou Image 1 (Seg geral): vol R$ 561k / qty 17 → R$ 33K (deck mostrava R$ 19K). Image 3 (Seg Inv): R$ 502k / 10 → R$ 50K (deck R$ 26K). Image 4 (Seg Cred): R$ 33k / 3 → R$ 11K (deck R$ 0). Image 5 (Cons Inv): R$ 4,1M / 10 → R$ 409K (deck R$ 381K). WBR pré-computou ticket usando contador diferente de apólices/contratos fechados.
- **V13 — linhas modificadas:**
  - `render_fech_visao_geral` (~linha 1052): nova função `_override_qty_and_ticket(data, asses_data, vert)` injeta `qty_id.n2_agregado` + `qty_id.n1_value` + `ticket_id.n2_agregado` + `ticket_id.n1_value` + recalcula `pct_atingimento` e `status.cor`. Aplicada para Seg e Cons antes de renderizar fgb_cards.
  - `render_fech_vertical` (~linha 1156): bloco análogo após sobrescrita de `qty_id` — recalcula `ticket_id.n2_agregado[canal] = vol_n2[canal] / asses_won[canal]` e `n1_value = total_vol / total_qty`.
- **Plugin Step 8 — como portar:**
  - Em `build_deck.py` (plugin), na render de fechamento por canal, ler `wbr.indicadores.X.por_canal[c].vol` e `por_canal[c].qty_won` e calcular ticket em runtime. NÃO ler `ticket_medio.por_canal[c]` direto do WBR (será descalibrado).
  - Quando indicators `_pj2` populam `wbr.indicadores.{ind_id}.por_canal[canal]` no WBR canonical, garantir que `qty_won` (apólices/contratos fechados Bitrix) está separado de `qty_total` (que pode incluir renovações). Builder usa `qty_won` no denominador.
- **Mudança em indicator/card (⚙):** Não aplicável — ajuste é só no render (não em fonte).
- **Mudança no WBR canonical:** garantir que `wbr.indicadores.{X}.por_canal[c].qty_won` exista além de `vol`. Builder usa esses 2 campos.

### #27 — Cor branca padronizada do % nas barras de atingimento

- **Categoria:** 🟢🖼
- **Edição (2026-05-12):** CSS `.atingimento-bar .pct-label.outside` mudou cor de `var(--verde-caqui)` para `#fff` + `text-shadow` reforçado (`0 0 3px rgba(0,0,0,0.85), 0 1px 2px rgba(0,0,0,0.7)`). Antes texto outside (pct baixo) ficava em verde-caqui sobre fundo claro; agora sempre branco com sombra preta para legibilidade.
- **Razão:** Usuário pediu "padronize para em todo canto que tiver a barra de porcentagem a cor da % dentro ser branca".
- **V13 — linhas modificadas:** CSS_BASE linhas 647-649 (3 classes `.pct-label`, `.pct-label.inside`, `.pct-label.outside`).
- **Plugin Step 8 — como portar:** Replicar mesma regra CSS no `ritual-pj2.tmpl.html` (template novo). Cor única branca + text-shadow forte. NÃO diferenciar inside/outside por cor — diferenciar só por position (left).

### #28 — Tempo de Ciclo com filtro ≥2 dias + meta 30d

- **Categoria:** 🟢⚙🖼
- **Edição (2026-05-12):**
  - `compute_tempo_ciclo_estagnacao.py` linha 138: **reverteu critério #10** ("incluir deals <2d"). Agora `if delta < 2: continue` antes de incluir no cálculo da mediana.
  - `build_pj2_deck.py` `extra_metas` em `render_fech_vertical`: `tempo_de_ciclo_funil_seg: 30` e `tempo_de_ciclo_funil_con: 30` (era `None` antes — sem meta).
- **Razão:** Usuário validou "Tempo de Ciclo 1,4 não faz sentido". Filtro `<2d` exclui deals diretos/passados já qualificados que distorcem a métrica de ciclo comercial real. Novos valores: Cons Inv 23,0d (4 won) / Cred 91,3d (1 won) / Outros 4,9d (1 won) | Seg Inv 21,3d (6 won) / Cred 38,0d (2 won) / Outros 30,9d (2 won). Meta 30d aplicada para visualizar barras de atingimento (menor melhor).
- **V13 — linhas modificadas:**
  - `compute_tempo_ciclo_estagnacao.py:135-141`
  - `build_pj2_deck.py:1257-1262` (`extra_metas` dict)
- **Plugin Step 8 — como portar:**
  - Script Python do indicator `tempo_de_ciclo_funil_{vert}_pj2` (futuro) deve aplicar `WHERE delta_dias >= 2` na query (ou filtro pós-extract).
  - Meta 30d deve ir no Card `metas_ppi.tempo_de_ciclo_funil_seg/con.valor: 30` (direção `menor_melhor`).
- **Mudança em indicator/card (⚙):**
  - Indicator (`tempo_de_ciclo_funil_seg_pj2.yaml` / `tempo_de_ciclo_funil_con_pj2.yaml`): adicionar filtro `delta_dias >= 2` na query SQL.
  - Card PJ2 `metas_ppi`: adicionar 2 entradas com `valor: 30, direction: menor_melhor`.

### #29 — pct_estagnadas % ativas por canal usa WBR n2_agregado (não asses_data)

- **Categoria:** 🟢🖼
- **Edição (2026-05-12):** Função `inject_pct_estagnadas_canal()` reescrita para usar `oportunidades_ativas_funil.n2_agregado_qty` e `oportunidades_estagnadas_funil.n2_agregado_qty` do WBR canonical (mesma fonte da matriz), em vez de agregar via `asses_data` (que classifica por SDR/MKT Bitrix-only).
- **Razão:** Usuário validou: "Crédito Consórcios tem 13 ativas e 10 estagnadas, logo não devia ser o 100% que diz ser". Discrepância: asses_data classificava só 3 deals Cred Cons (3/3=100%) mas WBR n2_agregado (que usa CTE centro_custo + fallback ASSIGNED) tem 13/10=77%. Matriz exibe 13/10 — pct precisa bater.
- **V13 — linhas modificadas:** `build_pj2_deck.py:2607-2629` (função `inject_pct_estagnadas_canal`).
- **Plugin Step 8 — como portar:**
  - Builder consome `wbr.indicadores.oportunidades_estagnadas_funil.por_canal[c].pct_ativas` diretamente do WBR canonical.
  - Indicator `oportunidades_estagnadas_funil_{vert}_pj2` (futuro) deve popular esse campo no JSON usando MESMA query/CTE de canal do `oportunidades_ativas_funil_pj2` (não fonte alternativa).
- **Mudança em indicator/card (⚙):** indicators `oportunidades_estagnadas/ativas_funil_pj2` precisam emitir `por_canal[c].qty` E `por_canal[c].pct_ativas` (qty_estagnada / qty_ativa) consistentes.

### #30 — status.cor + pct_atingimento recalculados no override (não usar pré-computed do WBR)

- **Categoria:** 🟢🖼
- **Edição (2026-05-12):** No `_override_qty_and_ticket` (visão geral) e no override correspondente em `render_fech_vertical`, após substituir `n1_value/n2_agregado`, recalcular:
  - `ind["pct_atingimento"] = realizado / meta * 100` (não usar pré-computed)
  - `ind["status"] = {"cor": cor_from_pct(pct), "emoji": ...}` (não usar pré-computed)
- **Razão:** Bug detectado pelo usuário: Ticket Médio Seg geral mostrava val em vermelho (`val_cls=bad`) com barra vermelha mas pct=105% — deveria ser verde. Causa: `_ind_status(ind)` lê `ind.status.cor` que estava cravado pré-override no WBR. Override de valor não basta — precisa override de status também.
- **V13 — linhas modificadas:** `build_pj2_deck.py` dentro de `_override_qty_and_ticket` (helpers `_COR` + `_status_from_pct`).
- **Plugin Step 8 — como portar:** Garantir que se o builder modifica `n1_value` ou `n2_agregado` de um indicador em runtime (override), também recalcula `pct_atingimento` e `status.cor` com base no novo valor. Não confiar em pre-computed quando override está ativo.

### #31 — M+1 Cons reintroduzido no slide Pipeline (só Cons, Seg sem M+1)

- **Categoria:** 🔵🖼
- **Edição (2026-05-12):** Em `render_pipeline` (linhas ~2078-2084), após renderizar pbars REAL e M0, adicionar pbars M+1 **apenas quando `vert == "consorcios"`** e `rec_M1/vol_M1` existem no WBR. Revertendo parcialmente o ajuste do Batch E #22 ("projeção apenas M0").
- **Razão:** Usuário pediu "Aqui consórcios deveria ter a projeção M1, só aqui". Cons tem método cycle-time-aware com M+1 calibrado (`pipeline_conversion_extended_v2_offline`); Seg ainda não tem método M+1 calibrado.
- **V13 — linhas modificadas:** `build_pj2_deck.py` `render_pipeline` linhas 2079-2084 (condicional `if vert == "consorcios" and rec_M1/vol_M1 is not None`).
- **Plugin Step 8 — como portar:**
  - Builder consome `wbr.projecoes.{vert}.{ind_id}.M+1` quando existe.
  - Card pode declarar `apresentacao.proj_periodos: ["M0", "M+1"]` ou similar — por vertical. Cons aceita M+1, Seg só M0 (até método estar calibrado).
- **Aviso visual sugerido:** quando `lagging_receita_M+1` (componente) for 0, exibir footnote pequena no slide explicando subestimação ("CH dump local sem competência M+1 — receita projetada subestimada").

---

## Resumo Batch I

6 fixes pós-validação visual da reunião 12/05. Todos refletem inconsistências entre **valor exibido** (que vem de cálculo em runtime usando asses_data) e **status/cor/pct** (que vinham de campos pré-computados do WBR). Lição para Plugin Step 8: **builder não deve confiar em campos pré-computed de status/pct quando reescreve valores em runtime** — recalcular sempre.

Cross-reference com m7-controle: 5 itens precisam virar campos canonicais nos indicators `_pj2`:

| # | Campo canonical sugerido | Indicator |
|---|---|---|
| #26 | `por_canal[c].qty_won` (separado de qty_total) | volume/receita/quantidade `_pj2` |
| #28 | filtro `delta_dias >= 2` na query | tempo_de_ciclo_funil_{vert}_pj2 |
| #28 | `metas_ppi.tempo_de_ciclo_*.valor: 30` | Card PJ2 |
| #29 | `por_canal[c].pct_ativas` coerente com matriz | oportunidades_estagnadas_funil_{vert}_pj2 |
| #31 | `wbr.projecoes.{vert}.M+1` opcional por vertical | metodologia projeção (lib helper) |

---

## Pendências para sessões futuras (registradas 2026-05-12 pós-validação pré-reunião)

Itens identificados durante a revisão do requirements.md que NÃO são edits visuais de slides, mas **lacunas estruturais** que precisam ser cobertas antes do plugin Step 8 ou da próxima rodada de rituais. Não devem ser feitos agora — abrir sessões dedicadas.

### PEND-1 — Documentar os 3 modos de apresentação e nuances PJ2 vs N3

**Escopo:** seção nova explicando:
- `atual` (default N3) | `combinado` (1º ritual mês ou PJ2) | `fechamento` (subset puro)
- Como cada Card escolhe modo (campo `apresentacao.modo` ou auto-detect `is_first_ritual_of_month`)
- PJ2 N2 sempre usa `combinado` (Card declara explicitamente)
- N3 single-vert auto-detecta
- Mapping de slides exibidos por modo (matriz/PA Status só em "atual", subcapas + fech vertical só em "combinado/fechamento", etc.)

**Por que importa:** Step 8 do plugin precisa portar o `MODO_PHASES` dispatch table com regras claras. Hoje a info está espalhada (Plan file Step 3+4, mas não no requirements.md como contrato).

**Sessão sugerida:** mesma sessão de paridade V13 ↔ plugin.

### PEND-2 — Origem dos `STAGE_PROBABILITY` + conflito de defaults

**Diagnóstico:**
- Valores em uso (V13 `pj2_offline_pipeline.py:68`): 30%/40%/55%/75%/90%/98% (Prospeccao→Cotas Alocadas)
- Valores no roadmap como "defasados/YAML default" (`m7-controle/skills/projecting-results/references/M+1-PROJECTION-ROADMAP.md`): 5%/10%/20%/40%/70%/90%
- Origem real: benchmark genérico de sales funnel, **não calibrado com histórico M7**
- Comentário no código diz "mediana histórica N3" mas isso é aspiracional

**Pendência:** decidir/registrar qual conjunto é o canônico e por quê. Implementar Gap 3 do roadmap (query SQL ClickHouse para calcular `stage_probability` real M-1 e M0-MTD).

**Regra do dia 15** (já documentada no roadmap, NÃO implementada):
```
SE dia_corrente <= 15:
  stage_probability_vigente = MEDIANA(M-1 completo)
SE dia_corrente > 15:
  stage_probability_vigente = MEDIANA(M0 MTD)
```

### PEND-3 — Modelar estagnação como modificador de stage_probability

**Insight nova (2026-05-12):** um deal em Prospeccao com 0 dias parado tem probabilidade diferente de um deal em Prospeccao com 30 dias parado. Hoje o método trata todos iguais (30% pra ambos).

**Hipótese a validar:** `stage_probability_adjusted = stage_probability_base × decay(dias_no_stage)`
- Onde `decay()` é uma função decrescente. Opções: linear, exponencial, step (cliff em >7d / >14d / >30d).
- Calibrar `decay` via histórico: deals que ficaram >30d no stage X qual % virou WON vs <7d?

**Implicação para projeção:** M+1 Cons hoje em R$ 30,4M tem deals em Prospeccao com tempo de ciclo Cred Cons 91d — possivelmente superestimado. Modelagem com decay reduziria contribuição de deals estagnados.

**Sessão sugerida:** sessão dedicada de modelagem de projeção (envolve EDA do histórico Bitrix + decisão de função de decay).

### PEND-4 — Auditoria 02-controle: artefatos prontos para rituais futuros

**Escopo:** percorrer todos os Cards + indicators + scripts em `02-Controle/` e validar:
- Cards de cada vertical: schema atualizado (v1.3), `metas_ppi` populado, `apresentacao` configurado
- Indicators existentes: rodam offline e online, output schema canônico
- Scripts pipeline G2.2: `collect.py`, `consolidating-wbr`, `projecting-results` aceitam `vertical=PJ2`
- ClickUp custom field `Vertical` aceita PJ2
- Memórias do plano (`refactor_pendente_plugin` no Card PJ2) que precisam ser checked-off

**Por que importa:** próximo ciclo de rituais (junho?) precisa rodar sem workarounds. Hoje PJ2 só funciona via V13 offline.

**Saída esperada:** checklist com status por vertical (CON, INV, CRE, SEG WL, SEG RE, UNI, PJ2) e por etapa (E1→E7) do pipeline G2.2.

**Sessão sugerida:** dedicada, fora dos rituais.

---

## Prompt sugerido para próxima sessão de paridade

> "Use `m7-operations/m7-ritual-gestao/skills/preparing-materials/references/pj2-slide-requirements.md` como contrato vivo (31 edits documentados Batches A-I + 4 pendências estruturais PEND-1 a PEND-4 registradas 12/05). Antes de propor gaps no plugin `build_deck.py`:
> 1. Leia PEND-1 a PEND-4 — não redescubra esses gaps, eles já estão registrados.
> 2. Para cada um dos 31 edits do contrato (Batches A-I), compare o que o plugin faz hoje vs o requisito. Use o V13 (`02-Controle/_pj2-prep/scripts/build_pj2_deck.py`, modificado 2026-05-12) como referência de implementação.
> 3. Output: lista priorizada de funções/CSS/templates que precisam ser portadas para o plugin Step 8, mapeada para cada edit (#1-#31).
>
> NÃO retomar a sessão antiga em `plans/objetivo-integrar-...` — ela está obsoleta (anterior ao Batch I)."

---

## Port plan V13 → Plugin Step 8 (registrado 2026-05-12)

Registrado a partir da sessão de paridade rodada em 2026-05-12 (após validação visual pré-reunião 14h N2 PJ2). Cobre o que o plugin `m7-ritual-gestao/preparing-materials` precisa portar do V13 para entregar o deck PJ2 sem o workaround offline. Os 13 indicators `_pj2` + Card PJ2 estão sendo tratados em **roadmap paralelo A.0 → V.4** (sessão dedicada) — este port-plan cobre o que sobra: WBR schema, builder, template novo, CSS, skill update, decisões arquiteturais.

### Snapshot do estado atual do plugin (2026-05-12)

- `build_deck.py` ([linha 1219+](../scripts/build_deck.py)) renderiza `7 + 3*N` slides single-vertical (capa+agenda+matriz+PA+3×N bloco_especialista+consolidado+encerramento).
- `MODO_PHASES = {atual, fechamento, combinado}` já implementado em [`build_deck.py:6504`](../scripts/build_deck.py) com resolução `_resolve_effective_modo()` ([linha 6531](../scripts/build_deck.py)) — precedência CLI → Card → auto-detect `is_first_ritual_of_month`.
- Template único `ritual.tmpl.html` ([template](../templates/ritual.tmpl.html)) — sub-capas placeholder, `ritual-pj2.tmpl.html` **não existe**.
- CSS atual: `.bar-row .track .fill-{good/warn/bad}` existe mas **não tem** `.atingimento-bar`/`.pct-label` (pct dentro da barra, texto branco com sombra), nem `.fech-vert-disclaimer`, nem `.veloc-gauge-wrap`.
- WBR canonical schema (v1.0 em `consolidating-wbr`) descompõe por **especialista** (`indicadores.{X}.n2.{esp}`), **não** por canal (`por_canal[c]`). Sem `qty_won` distinto de `qty_total`. Projeções têm `M0/M1/M2` mas a porta de `M+1` por vertical não está padronizada.

### Cross-session map

| Eixo de trabalho | Sessão responsável | Status |
|---|---|---|
| 13 indicators `_pj2` (quantidade, criadas, ativas, taxa_conv, estagnadas, sem_movimentacao, tempo_ciclo) | Roadmap paralelo A.0 → V.4 | Sessão A.1 em progresso |
| Correção N3 `quantidade_consorcio_mensal` (Bitrix → CH) | Roadmap A-D (Sessão D.1) | Pendente |
| Atualização Card PJ2 (`kpi_references` + `metas_ppi`) | Roadmap A-D (Sessões D.2 + D.3) | Pendente |
| Validação standalone + paridade V13 (REQUER ESCRITÓRIO) | Roadmap A-D (Sessões V.1 → V.4) | Pendente — CH só responde da rede interna |
| **WBR canonical schema** `por_canal[c]` + `M+1` opt-in | **Step 8** desta paridade | TIER P2 abaixo |
| **Builder + template novo + CSS + decisões arquiteturais** | **Step 8** desta paridade | TIER P0/P1 abaixo |
| Atualizar skill `m7-metas/creating-indicators` (display_name, direction, output_schema.por_canal, Modo 5 clone) | Sessão dedicada `creating-indicators v3` — **BLOQUEANTE** para roadmap A-D pós-decisão 2026-05-12 | TIER P0-skill abaixo |
| PEND-1/2/3/4 (modos, stage_probability, decay, auditoria) | Sessões dedicadas | Pendentes |

### Notação de prioridade

- **P0** = bloqueia o ritual PJ2 via plugin (sem isso o deck não fecha)
- **P1** = visual/consistência alto-impacto, aplica a múltiplos rituais
- **P2** = schema canonical / skill update (viabiliza P0)
- **P3** = polish, one-off ou pendência estrutural fora do Step 8

### TIER P0 — Bloqueantes do template PJ2

| # | Topic | Plugin hoje | V13 ref | Ação no Step 8 |
|---|---|---|---|---|
| #2 | Fechamento Visão Geral: divisor Seg\|Cons | ❌ | `render_fech_visao_geral()` V13:1052; CSS `.fech-2grids` `.fgb-grid` | Criar `render_fech_visao_geral_pj2()` no plugin + classes no `ritual-pj2.tmpl.html` |
| #4 | `.atingimento-bar` (pct dentro / meta fora) | ⚠ parcial (`.bar-row` sem pct interno) | CSS `build_pj2_deck.py:641-649` | Portar CSS para `ritual-pj2.tmpl.html`; aplicar em todos os cards de KPI (substitui `.bar-row` antigo); decisão futura para `ritual.tmpl.html` legado |
| #7 | Pareto: filtrar Outros zerados | ❌ | filtro dentro de `render_fech_vertical()` V13:1178 | Implementar regra "só assessor c/ Criada OU Fechada >0" no `render_fech_vertical_pj2()` |
| #9 | Slide "Análise do que deu errado" (substitui Diretrizes) | ❌ | `render_analise_problemas()` V13:2273 | Criar fase `analise_problemas` no `MODO_PHASES["combinado"]`/`["fechamento"]`; portar layout dual + lógica causal "criei X / fechei Y / faltou converter ou criar" |
| #17 | Ordem nova vertical-by-vertical | ❌ | array de slides `main()` V13:1938-1960 | Dispatch table no `ritual-pj2.tmpl.html`: Matriz_Seg → AnaliseCanal_Seg → Pipeline_Seg → Matriz_Cons → AnaliseCanal_Cons → Pipeline_Cons |
| #18 | Remover slide "Direto" SÓ PJ2 | ❌ (plugin não tem Direto) | — | Não chamar `render_direto` no template PJ2; manter para N3 single-vert |
| #21 | "Conclusão" com velocímetros (substitui Próximos Passos) | ❌ | `render_conclusao_velocimetros()` V13:2425 + helper `_gauge_svg()`; CSS `.veloc-gauge-wrap`, `.veloc-pct`, `.veloc-vals`, `.veloc-proj` | Criar função + helper SVG + CSS no plugin; **3 velocímetros PJ2 (Seg Receita / Cons Receita / Total PJ2 só p/ Receita)** |
| #23 | Disclaimer + asterisco discrepância Pareto vs Card | ❌ | asterisco em `fc-head inv/cred` + `<div class="fech-vert-disclaimer">` antes do `slide_foot` | Portar CSS `.fech-vert-disclaimer` + estrutura no `render_fech_vertical_pj2()` quando Pareto for Bitrix-only mas Card usar canonical CH+Bitrix |
| #26 | Ticket recalc dinâmico `vol/qty_won` em runtime | ❌ (consome `ticket_medio` direto) | `_override_qty_and_ticket()` V13:1058 | **Duas opções (decisão arquitetural):** (a) portar helper de override no builder; (b) exigir que WBR canonical emita `por_canal[c].qty_won` separado e `ticket` ser SEMPRE derivado. **Preferir (b)** + remover override do builder no longo prazo. Curto prazo: (a) como bridge. |
| #29 | `pct_estagnadas` por canal usa WBR (não asses_data) | ❌ | `inject_pct_estagnadas_canal()` V13:2619 | WBR canonical precisa emitir `oportunidades_estagnadas_funil.por_canal[c].pct_ativas` consistente com `oportunidades_ativas_funil.por_canal[c].qty` (mesma CTE de canal) |
| #30 | Status/pct recalc no override (não confiar em pre-computed) | ❌ | `_status_from_pct()` chamado após `n1_value` override em `_override_qty_and_ticket` | **Regra arquitetural:** builder NUNCA confia em `ind.status.cor`/`pct_atingimento` quando reescreve `n1_value`/`n2_agregado` em runtime. Sempre recalcular via `cor_from_pct(realizado/meta, direction)` |

### TIER P1 — Visual / consistência multi-ritual

| # | Topic | Plugin hoje | V13 ref | Ação no Step 8 |
|---|---|---|---|---|
| #1 | Agenda: bloco "Pontos discutidos na última N2" | ❌ | `render_agenda()` V13:932 | Renderizar bloco quando `card.metadata.label_responsavel == "canal"` (ou flag `card.apresentacao.show_recap_n2`). Fonte: campo `card.metadata.recap_n2` ou ata anterior |
| #3 | Título Seguros "Empresarial e Vida" | ❌ | label dinâmico `render_fech_visao_geral()` | Adicionar campo `card.metadata.verticais_display.{seg: "Empresarial e Vida"}` no Card PJ2; template lê |
| #5 | Aumentar fonte (números + letras proporcional) | ⚠ | CSS_BASE V13:462 | Ajustar `.fc-row .fc-val` e similares em `ritual-pj2.tmpl.html`; avaliar replicar em `ritual.tmpl.html` |
| #8 | Remover "Diretrizes para o mês seguinte" | ⚠ (plugin tem `render_diretrizes_slide` linha 6333) | retirado do array V13 | Substituir por `analise_problemas` no `MODO_PHASES["combinado/fechamento"]` (ver #9) |
| #11 | Taxa Conversão Cons → 25% | ❌ | Card metas_ppi | **Roadmap D.3** — Card PJ2 `metas_ppi.taxa_conversao_funil_con.valor: 0.25` |
| #14 | Renomear "Sem Movimentação" → "Sem atividades ou atrasadas" | ❌ | labels V13 | Indicator `oportunidades_sem_atividade_planejada_funil.display_name` + Card `kpi_references[].display_label` + slide-structure.md |
| #15 | "Ticket" → "Ticket Médio Pipeline" | ❌ | labels Pipeline/Ativas | Indicator + Card + template (distinto de "Ticket Médio" do mês fechado) |
| #16 | "Quantidade" → "Contratos Fechados" / "Apólices Fechadas" | ❌ | labels em todos slides | Indicator `quantidade_consorcio_mensal.display_name: "Contratos Fechados"` + Seg análogo |
| #19 | Remover PA Status + PA Lista quando vazios | ⚠ (plugin tem `render_pa_slides` linha 2353 sempre) | condicional V13 | Condicionar `render_pa_slides` a `count(pa_tasks) > 0` — aplicável a todos os rituais |
| #22 | Projetar apenas M0 (com exceção #31) | ⚠ | sem M+1 nos slides exceto Pipeline Cons | Builder não exibe `projecoes.M+1` por padrão; `apresentacao.proj_periodos` opt-in |
| #27 | Cor branca padronizada do % nas barras | ❌ | CSS V13:647-649 (`.pct-label.outside`) | CSS único cor `#fff` + `text-shadow: 0 0 3px rgba(0,0,0,0.85)`. Diferenciar inside/outside só por position, não por cor |
| #31 | M+1 reintroduzido SÓ Cons no Pipeline | ❌ | `render_pipeline()` V13:2079-2084 condicional `if vert == "consorcios"` | Card PJ2 declara `apresentacao.proj_periodos_por_vertical: {seg: ["M0"], cons: ["M0", "M+1"]}`; template Pipeline respeita. Footnote de subestimação quando `lagging_receita_M+1` baixa |

### TIER P2 — Schema canonical (responsabilidade m7-controle)

| # | Topic | Estado | Ação |
|---|---|---|---|
| **WBR schema** (sustenta #26, #29, #31) | `por_canal[c]` ausente | ❌ | Estender `consolidating-wbr` (m7-controle E6) para emitir `indicadores.{X}.por_canal[c].{vol, qty_won, qty_total, pct_ativas}` para indicadores PJ2; mesma CTE de canal entre indicators correlacionados (estagnação ↔ ativas) |
| **WBR schema** projecoes M+1 | parcial | ⚠ | Garantir `wbr.projecoes.{vert}.{ind_id}.M+1` opcional por vertical; `is_first_ritual_of_month` no JSON (não só CICLO.md) |

### TIER P2 — Indicators `_pj2` + Card PJ2 (via skill — ver TIER P0-skill abaixo)

**Mudança arquitetural 2026-05-12 (decisão Bruno):** indicators `_pj2` agora são criados via **skill `m7-metas/creating-indicators`** (Modo 1 ou Modo 5 Clone), **não** via `_pj2_runner.py` como gerador de YAML. Razão: memory `feedback_pristine_cycles_skill_first` — ciclos G2.2/G2.3 devem rodar pristine sem intervenção manual; YAML é responsabilidade da skill oficial.

**Papel revisado dos scripts em `02-Controle/_pj2-prep/scripts/`:**
- `_pj2_funil_extractor.py` — sobrevive como **camada de execução** (Bitrix client + canal classification helpers) referenciada pelos YAMLs `_pj2` via `extraction.method` quando `source_type: mcp` ou `hybrid`. NÃO emite YAML.
- `compute_tempo_ciclo_estagnacao.py` — idem, helper de computação chamado pelos YAMLs `tempo_de_ciclo_*_pj2`.
- `_pj2_runner.py` — **aposentado como gerador de YAML**. Se houver lógica de execução útil, migra para `m7-controle/collecting-data/scripts/collect.py` como parte do fluxo padrão E2.

**Roadmap revisado A.x → D.3 (via skill):**
- A.x — Skill cria quantidade Cons (Modo 1, source CH `consorcio_contratos`), quantidade Seg (Modo 1, source Bitrix pipeline 156), ticket derivado (Modo 1, source `derived`)
- B.x — Skill **Modo 5 Clone** dos N3 existentes: `oportunidades_criadas_funil_con` → `_pj2` (com override de canal mapping), idem para `_ativas` Cons/Seg
- C.x — Modo 5 Clone para `taxa_conversao`, `estagnadas`, `sem_movimentacao` (Cons + Seg)
- D.1 — Correção N3 `quantidade_consorcio_mensal` via Modo 4 (Editar)
- D.2 — Card PJ2 `kpi_references` atualizado (substituir 13 IDs originais pelos `_pj2`)
- D.3 — Popular `metas_ppi` no Card PJ2

**Cada indicator criado/clonado dispara obrigatoriamente o protocolo de data lineage** (memory `feedback_indicator_data_lineage`): skill mostra fonte/filtros/mapeamento canal/agregação/output schema ao Bruno → aprovação → YAML gerado. Sem aprovação, skill não escreve.

**Edits cobertos automaticamente pela skill v3 (TIER P0-skill abaixo):**
- #6 sufixo "CRM" — `display_suffix: "CRM"` declarado na entrevista para indicators Bitrix
- #10 / #28 — tempo de ciclo com `direction: menor_melhor` + meta 30d declarado na entrevista
- #12 / #13 — `output_schema.por_canal[c]` declarado para indicators com decomposição
- #29 — `por_canal[c].pct_ativas` declarado no output_schema

**V.1-V.4 (validação)** — REQUER ESCRITÓRIO (CH local). Não muda.

**Dependência crítica:** Sessões A-D só rodam DEPOIS da skill v3 estar pronta (TIER P0-skill bloqueia este TIER P2).

**Regra de transparência para cada sessão A-D (feedback 2026-05-12):**

ANTES de escrever qualquer YAML ou script `_pj2_runner.py`/`_pj2_funil_extractor.py`, apresentar ao usuário:

1. **Fonte de dados** — tabela/pipeline/CSV/MCP exato
2. **Filtros** — WHERE clauses, status, datas
3. **Mapeamento campo → canal** — qual UF/campo Bitrix → Inv/Cred/Outros M7 via `de-para-canal.yaml`
4. **Lógica de agregação** — COUNT, SUM, MEDIAN, derivação
5. **Output schema** — campos que o indicator vai emitir

Usuário aprova/ajusta os 5 pontos. Sem isso a sessão não avança.

**Data lineage conhecida (snapshot 2026-05-12 — completar em cada sessão):**

| Indicator `_pj2` | Fonte | Filtro | Agregação | Canal mapping | Sessão |
|---|---|---|---|---|---|
| `quantidade_consorcio_mensal_pj2` | CH `consorcio_contratos` | `situacao=ATIVO` + `data_venda` in M0 (coluna real validada 2026-05-07; memory `reference_consorcio_volume_source`) | `COUNT(*)` | `centro_custo` via `01-Metas/.../_referencias/canal.yaml` (Alta Renda/Private/Mesa/Mesa Digital/Corporate → investimentos; Crédito → credito; M7/resto → outros_m7) | A.1 |
| `quantidade_seguros_mensal_pj2` | Bitrix pipeline **156** WON | UF...648=**7268** (filtro Bruno 11/05) | `COUNT(deals)` | `UF_CRM_1745419691` (SDR Seg) → `de-para-canal.yaml` | A.2b |
| `ticket_medio_premio_seg_pj2` (DERIVADO) | — | — | `volume_seguros_mensal_pj2 / quantidade_seguros_mensal_pj2` | (herda) | A.3 |
| `oportunidades_criadas_funil_pj2` (Cons) | Bitrix pipeline **238** | `DATE_CREATE` in M0 | `COUNT(deals)` | `UF_CRM_1758122406` (MKT Cons) | B.1 |
| `oportunidades_ativas_funil_pj2` (Cons) | Bitrix pipeline 238 snapshot | stage ∈ ativas | `COUNT`, `SUM(volume)` | `UF_CRM_1758122406` | B.2 |
| `oportunidades_criadas_funil_seg_pj2` | Bitrix pipeline 156 | `DATE_CREATE` in M0 + filtro "nova venda" | `COUNT(deals)` | `UF_CRM_1745419691` | B.3 |
| `oportunidades_ativas_funil_seg_pj2` | Bitrix pipeline 156 snapshot | stage ∈ ativas | `COUNT`, `SUM(volume)` | `UF_CRM_1745419691` | B.4 |
| `taxa_conversao_funil_{con,seg}_pj2` (DERIVADO) | — | — | `qty_won / qty_criadas` period-matched | (herda) | C.1 |
| `oportunidades_estagnadas_funil_pj2` (Cons + Seg) | Bitrix stagehistory | ativas + `dias_no_stage >= 7` | `COUNT`, `pct_ativas = qty_estagnadas/qty_ativas` (#29) | UF por vertical | C.2 |
| `oportunidades_sem_movimentacao_funil_pj2` (Cons + Seg) | Bitrix activities | "sem atividade planejada OU atrasada" (#14) | `COUNT` | UF por vertical | C.3 |
| `tempo_de_ciclo_funil_{con,seg}_pj2` (POSSÍVEL GAP — confirmar) | Bitrix stagehistory | WON + `delta_dias >= 2` (#28) | `MEDIAN(DATE_WON - DATE_CREATE)` | UF por vertical | (não vista no roadmap atual) |

**Campos a confirmar em cada sessão (não pular):**
- Período exato de filtragem (M0 = mês corrente até `data_referencia`)
- Tratamento de fallback canal (deals sem UF preenchida → ASSIGNED_BY como fallback)
- Como `_pj2_runner.py` injeta os parâmetros (env vars vs args vs Card metadata)
- Tabela de dependências no YAML (`dependencies`) entre indicators derivados

### TIER P0-skill — Atualizar `m7-metas/creating-indicators` (BLOQUEANTE, decisão 2026-05-12)

**Promovido de P2-skill → P0-skill** em 2026-05-12. Decisão Bruno (memory `feedback_pristine_cycles_skill_first`): geração de YAML é responsabilidade exclusiva da skill oficial; `_pj2_runner.py` é aposentado como gerador. Sessões A-D NÃO rodam até skill estar feature-complete com os 4 campos novos + Modo 5 Clone + regra obrigatória de data lineage.

**Arquivos da skill a atualizar:**

| Arquivo | Gap |
|---|---|
| [`SKILL.md`](../../../m7-metas/skills/creating-indicators/SKILL.md) | Entrevista guiada NÃO pergunta `display_name`, `display_suffix`, `direction`, nem se o indicator emite `output_schema.por_canal[c]` |
| `references/schema-v2.md` (ou criar `_schema.yaml` concreto) | Não documenta `display_name` / `display_suffix` / `direction` / `output_schema.por_canal` |
| `templates/indicator-sql.tmpl.yaml` | Sem slot para os 4 campos novos |
| `templates/indicator-mcp.tmpl.yaml` | Idem |
| `templates/indicator-hybrid.tmpl.yaml` | Idem |

**Campos a adicionar:**

1. **`display_name`** (string, opcional, default = `name`) — label visual customizado para slides.
2. **`display_suffix`** (string, opcional) — sufixo concatenado ao `name` quando renderizado. Mais DRY para edit #6 ("CRM").
3. **`direction`** (enum: `maior_melhor` | `menor_melhor`, opcional, default = `maior_melhor`) — direção do semáforo. Crítico para edit #28 (tempo de ciclo 30d, menor melhor).
4. **`output_schema.por_canal`** (object opcional) — declara que o indicator emite decomposição por canal. Schema: `por_canal: {<canal_id>: {qty, vol, qty_won?, pct_ativas?, ...}}`. Crítico para edits #12, #13, #29.
5. **Modo 5 (clone)** — clonar indicator existente como variante (`_pj2`, `_n3`, etc.) — Modo 4 (Editar) atual não cobre.

**Sessão sugerida:** dedicada `creating-indicators v3` antes ou em paralelo às sessões A-D. Não bloqueia Step 8 imediato (`_pj2_runner.py` está criando indicators sem a skill).

### TIER P0-avatar — Círculo ID padronizado por responsável (decisão 2026-05-12)

Padronização visual decidida pelo usuário pós-port-plan original. Cada responsável/canal nos slides exibe um círculo lime #EEF77C de ~56-64px contendo OU foto base64 OU texto curto.

**Asset registry (criado nesta sessão):** [`assets/avatars/avatars.yaml`](../assets/avatars/avatars.yaml) + 5 arquivos `.b64` (douglas/tereza/cláudia/tarcísio/emmanuel) + text labels (SEG, CON, SS).

**Card YAML — campos novos em `apresentacao.responsaveis[i]`:**
- `avatar_key` (string, opcional) → lookup `assets/avatars/avatars.yaml#specialists.{key}` → builder lê `base64_file` e injeta inline
- `id_circulo` (string, opcional, max 3 chars) → texto direto no círculo (PJ2 SEG/CON, ou fallback temporário tipo Samuel "SS")

Exatamente 1 dos 2 campos por responsável. Se ambos presentes, `avatar_key` prevalece.

**CSS a portar/criar em `ritual-pj2.tmpl.html` (e replicar em `ritual.tmpl.html` legado para N3):**

```css
.circulo-id {
  width: 56px; height: 56px; border-radius: 50%;
  background: #EEF77C;
  display: flex; align-items: center; justify-content: center;
  font-weight: 700; font-size: 18px; color: #424135;
  overflow: hidden;
}
.circulo-id img { width: 100%; height: 100%; object-fit: cover; }
.circulo-id.lg { width: 120px; height: 120px; font-size: 36px; } /* variante destaque */
```

**Builder (`build_deck.py`) — função nova `resolve_circulo(responsavel)`:**

```
if responsavel.avatar_key:
  b64_path = avatars.yaml[specialists][avatar_key][base64_file]
  return <img src=read_file(assets/avatars/{b64_path})>
elif responsavel.id_circulo:
  return <span>{id_circulo}</span>
else:
  fallback: iniciais do nome (last resort)
```

**Mapping ativo (2026-05-12):**

| Vertical | Responsável | Tipo | Valor |
|---|---|---|---|
| Consórcios N3 | Douglas Silva | avatar_key | `douglas_silva` |
| Consórcios N3 | Tereza Bernardo | avatar_key | `tereza_bernardo` |
| Seguros N3 WL | Cláudia Moraes | avatar_key | `claudia_moraes` |
| Seguros N3 WL | Tarcísio Catunda | avatar_key | `tarcisio_catunda` |
| Seguros N3 RE | Emmanuel Martins | avatar_key | `emmanuel_martins` |
| Seguros N3 RE | Samuel Sinval | id_circulo (temp) | `SS` — TODO migrar para `samuel_sinval` quando foto profissional pronta |
| PJ2 N2 | Seguros (agregada) | id_circulo | `SEG` |
| PJ2 N2 | Consórcios (agregada) | id_circulo | `CON` |

**Aviso de peso:** Douglas/Tereza/Tarcísio são PNGs grandes (190-350KB cada). Builder embeda inline → HTML do ritual cresce ~1MB com 6 avatares. Se virar problema no Step 8, downscale para 128px reduz para ~30-50KB cada.

**Memory:** `reference_avatar_circulo_id.md` no MEMORY index do projeto.

### TIER P3 — Polish, one-offs e pendências futuras

| # | Topic | Ação |
|---|---|---|
| #20 | Remover "Síntese Seguros/Consórcio" | Plugin já não emite Síntese (tem Consolidado, diferente) — verificar no template novo que não recria |
| #24 | Caso Tereza ~2 deals sem assessor | One-off 12/05; ignorado |
| #25 | Slide NPS Consórcio (one-off) | Append via script à parte; **NÃO documentar no plugin permanente** |
| **PEND-1** | Documentar 3 modos (atual/combinado/fechamento) + nuances PJ2 vs N3 | Mesma sessão de paridade V13 ↔ plugin |
| **PEND-2** | `STAGE_PROBABILITY` origem + regra dia 15 | Sessão dedicada (Gap 3 do roadmap M+1) |
| **PEND-3** | Estagnação como modifier de stage_probability (decay) | Sessão dedicada de modelagem; EDA Bitrix + escolha de função decay |
| **PEND-4** | Auditoria 02-Controle pré-Step 8 | Sessão dedicada (checklist vertical × etapa) |

### Decisões arquiteturais explícitas (5 lições do Batch I)

1. **Builder não confia em pre-computed** (edit #30): se o builder reescreve `n1_value` ou `n2_agregado` em runtime, **sempre** recalcula `pct_atingimento` e `status.cor`. Nunca consome `ind.status.cor` ou `ind.pct_atingimento` após override.
2. **Ticket é sempre derivado** (edit #26): builder calcula `ticket = vol / qty_won` em runtime — `qty_won` ≠ `qty_total`. Indicator/WBR emite os 2 separados.
3. **Pareto e Card precisam usar a mesma fonte de canal** quando possível (edit #23): enquanto Pareto for Bitrix-only e Card for canonical CH+Bitrix, o disclaimer + asterisco é obrigatório. Ao migrar Pareto para canonical, eliminar disclaimer.
4. **`menor_melhor` é cidadão de primeira classe** (edit #28): `cor_from_pct(pct, direction)` precisa suportar ambas direções — não é opcional. Hoje vivo só no V13:78; falta no plugin.
5. **Projeções M+1 são opt-in por vertical** (edit #31): `apresentacao.proj_periodos_por_vertical` no Card; nada de default global. Footnote quando subestimação detectada (ex: `lagging_receita_M+1` ≈ 0 indicando CH dump local sem competência M+1).

### Ordem de execução cross-session (revisada 2026-05-12)

1. **TIER P0-skill — `creating-indicators v3`** (BLOQUEANTE, primeiro): 4 campos novos no schema + Modo 5 Clone + regra obrigatória de data lineage. Sem isso, indicators `_pj2` não podem ser criados.
2. **Roadmap _pj2 A.0 → D.3 via skill** (Modo 1 / Modo 5 Clone): 13 indicators + Card PJ2 atualizado (#11/#28 metas_ppi, kpi_references). Sub-roadmap A.0 do _pj2_runner como gerador de YAML está aposentado; helpers de execução (`_pj2_funil_extractor.py`, `compute_tempo_ciclo_estagnacao.py`) migram para `m7-controle/collecting-data` se ainda forem necessários.
3. **TIER P2 WBR schema** (m7-controle E6): estender `consolidating-wbr` com `por_canal[c]` + `M+1` opt-in.
4. **TIER P0 + P0-avatar (Step 8)**: builder + template novo `ritual-pj2.tmpl.html` + CSS `.atingimento-bar`/`.fech-vert-disclaimer`/`.veloc-gauge-wrap`/`.circulo-id` + resolver de avatares + 5 decisões arquiteturais.
5. **TIER P1** (Step 8 ou follow-up): polish (labels, fontes maiores, condicional PA, M+1 Cons-only).
6. **Roadmap V.1 → V.4** (REQUER ESCRITÓRIO): validação standalone + paridade vs V13.
7. **TIER P3 / PEND** — sessões separadas.

Dependências críticas:
- (1) bloqueia (2) — sem skill v3, sem indicators `_pj2`
- (2) bloqueia (4) — sem indicators populados, builder Step 8 só roda com stubs
- (3) pode paralelizar com (2) — schema canonical é independente do conteúdo dos YAMLs
- TIER P0-avatar depende apenas de `assets/avatars/avatars.yaml` + 5 arquivos `.b64` (já criados nesta sessão 2026-05-12) — pode ser feito junto do Step 8

### Cross-references — decisões arquiteturais paralelas a Step 8

Estas duas decisões NÃO fazem parte do Port plan do deck PJ2 mas afetam ciclos pós-12/05 e foram registradas em 2026-05-12 nesta mesma sessão. Linkadas aqui para que o Step 8 saiba que elas existem e não duplique trabalho:

| Decisão | Memory | Escopo | Sessão sugerida |
|---|---|---|---|
| Escopo de ações filtrado por ritual passado (G2.2 ciclo só puxa tasks da ata.md anterior + ad-hoc pós-ritual) | `reference_g2_2_action_scope_filter.md` | E5 ata + E2 Fase 1.5 ClickUp fetch + E4 narrativa | Dedicada `g22-action-scope-filter` |
| Data lineage transparente antes de gerar YAML de indicator (mostrar fonte/filtros/mapeamento/agregação/output_schema ao usuário pré-código) | `feedback_indicator_data_lineage.md` | Sessões A-D do roadmap `_pj2` e qualquer criação/edição futura | Aplicável a partir de já — vale para Sessão A.1 em andamento |
