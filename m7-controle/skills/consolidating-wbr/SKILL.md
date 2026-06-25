---
name: consolidating-wbr
description: >-
  G2.2-E6: Consolida outputs de E2-E5 em um unico Weekly Business Report (WBR) com narrativa
  executiva coerente, semaforo, desvios, acoes, projecoes e recomendacoes. Produz documento
  autocontido pronto para consumo pelo gestor e pelo m7-ritual-gestao. Use when the pipeline
  advances to E6, when /m7-controle:next reaches E6, or when /m7-controle:run-weekly
  executes the final consolidation step.

  <example>
  Context: E5 concluido, pipeline avanca para consolidacao final
  user: "/m7-controle:next"
  assistant: Invoca analyst para consolidar E2-E5 em WBR unico com narrativa executiva
  </example>

  <example>
  Context: Usuario quer o relatorio semanal final
  user: "Gera o WBR de Investimentos dessa semana"
  assistant: Le relatorios parciais de E2-E5, consolida com narrativa coerente e gera WBR
  </example>
user-invocable: false
---

# Consolidating WBR — Weekly Business Report (E6)

> "O WBR e autocontido: quem le nao precisa consultar os relatorios parciais."

Esta skill consolida os outputs de E2 (qualidade), E3 (desvios), E4 (acoes) e E5 (projecoes) em um unico documento WBR com narrativa executiva coerente. E a etapa final do pipeline semanal.

> **REGRA DE HANDOFF**: Ao invocar o agente analyst, NAO passe valores de dados no texto do prompt. Passe APENAS caminhos de arquivos (vertical, cycle folder, paths dos artefatos). O analyst deve usar Read tool para carregar os dados dos arquivos em disco.

## Dependencias Internas

- [references/wbr-structure.md](references/wbr-structure.md) — Regras de narrativa, consolidacao e validacao de coerencia
- [templates/wbr.tmpl.md](templates/wbr.tmpl.md) — Template do WBR Estruturado com 5 secoes obrigatorias
- [templates/wbr-narrativo.tmpl.md](templates/wbr-narrativo.tmpl.md) — Template do WBR Narrativo com 7 secoes (prosa executiva)
- [templates/wbr-narrativo.tmpl.html](templates/wbr-narrativo.tmpl.html) — Template HTML com CSS M7-2026 e placeholders para geracao visual
- [references/wbr-html-guide.md](references/wbr-html-guide.md) — Guia de geracao SVG e mapeamento de dados para HTML
- Script `scripts/html-to-pdf.js` — Conversao HTML → PDF via Puppeteer (requer `npm install` em `scripts/`)
- Agent `analyst` — Executor da consolidacao (invocado automaticamente)
- Outputs de etapas anteriores (na pasta do ciclo):
  - `data-quality/data-quality-report.md` (E2)
  - `analise/deviation-cause-report.md` (E3)
  - `analise/action-report.md` (E4)
  - `analise/projection-report.md` (E5)

## Pre-requisitos (Entry Criteria)

- E5 concluido (todos os relatorios parciais E2-E5 disponiveis na pasta do ciclo)
- CICLO.md indica E6 como etapa atual
- Dados numericos consistentes entre relatorios (verificar na consolidacao)

## Modelo de Execucao — 2 passadas do analyst (NOVO v6.5.0 — 2026-06-12)

> **MUDANCA DE CONTRATO DO E6.** Para que as metas do SoT `m7Prata.ciclo_metas_ppi`
> (Fase 4.6) entrem coerentes em TODOS os artefatos (canonical + Estruturado +
> Narrativo + gate), o E6 roda em **2 invocacoes do agente `analyst`** com um passo
> deterministico do **main thread** (que tem Bash) no meio. O analyst NAO tem Bash —
> quem roda os scripts (`normalize_canonical`, `inject_metas_ppi`, `validate-painel`,
> `html-to-pdf`) e SEMPRE o main thread executor do skill.

Sequencia obrigatoria:

1. **PASSADA 1 — analyst (Fases 1 → 4.5, incl. 4.5.a–g):** consolida E2–E5 e escreve
   **SOMENTE o canonical** `wbr-{vertical}-{data}.data.json`. **PARE aqui** — NAO escreva
   ainda Estruturado/Narrativo (eles dependem do canonical pos-inject).
2. **MAIN THREAD (bash) — Fase 4.6:** roda `normalize_canonical.py` (conserta shape),
   `inject_metas_ppi.py` (injeta metas PPI do SoT nos indicadores opted-in) e
   `resolve_kpi_m1_meta.py` (grava a meta REAL do mes seguinte nos KPIs receita/volume/
   quantidade a partir dos dados coletados — corrige a heranca de meta M0 no M+1). Ver Fase 4.6.
3. **PASSADA 2 — analyst (Fases 5 → 7):** **LE o canonical ja injetado** e escreve
   Estruturado (5) + Narrativo MD (6) + HTML (6b) + spot-check (7). **REGRA CRITICA:**
   nesta passada o canonical e a fonte de verdade — NAO reescrever `indicadores.*`
   (so ler para formatar os docs).
4. **MAIN THREAD (bash) — Fases 6c + 7.5:** PDF (6c) + gate `validate-painel.py` (7.5).
   Como os docs da Passada 2 ja derivam do canonical injetado, o gate cross-artifact bate.

> **Offline / sem opt-in:** se o ClickHouse estiver fora (office-only) ou nenhum Card
> declarar `fonte:`, o `inject_metas_ppi` e NO-OP — o canonical permanece com o cache do
> Card e o fluxo segue identico ao legado (1 passada efetiva). Sem regressao.

## Workflow

### Fase 1 — Ler Relatorios Parciais

1. Ler todos os relatorios da pasta do ciclo:
   - `data-quality/data-quality-report.md` (E2) — alertas de qualidade
   - `analise/deviation-cause-report.md` (E3) — semaforo, desvios, causas
   - `analise/action-report.md` (E4) — status contramedidas
   - `analise/projection-report.md` (E5) — projecoes e cenarios
2. Extrair dados-chave de cada relatorio para consolidacao
3. Verificar coerencia numerica entre relatorios (ver [wbr-structure.md](references/wbr-structure.md))

### Fase 1.5 — Contexto Temporal

Ler `periodo`, `granularidade` e `checkpoint_label` do CICLO.md. Todos os resultados devem ser enquadrados como MTD (month-to-date) no checkpoint atual, NAO como resultados de uma unica semana. O `checkpoint_label` (ex: "Marco 2026, semana 4 (MTD)") deve ser usado no header e na narrativa.

### Fase 1.6 — Detectar close_mode (v6.1.0+)

> **NOVO 2026-05-06**: quando o ciclo foi disparado em `close_mode: true`
> (Step 1.2 do run-weekly), ajustar a narrativa e marcar projecoes como
> `is_retrospective: true` no canonical data JSON.

1. **Ler `close_mode`** do header do CICLO.md
2. **Se `close_mode == true`**:
   - **Narrativa de fechamento**: substituir secao "Projecoes" por secao "Fechamento do mes" com:
     - Total realizado consolidado vs meta (% atingimento por nivel)
     - Top 3 / Bottom 3 performers do mes (especialistas e/ou squads)
     - Causa-raiz dominante das variacoes (compilada de E3)
     - Licoes do mes consolidadas (compiladas de E3 + E4)
   - **Marcar projecoes**: no canonical data JSON (Fase 4.5), adicionar campo `is_retrospective: true` em cada bloco de projecao. Material-generator do m7-ritual-gestao usa essa flag para OCULTAR visualmente as barras de projecao no slide de fechamento (mes ja fechou, projecao retroativa nao faz sentido).
   - **Output rename**: salvar como `wbr-{vertical}-{mes}-fechamento.data.json` (em vez de `wbr-{vertical}-{data}.data.json`) para diferenciar do snapshot regular.
   - **Header WBR**: adicionar tag `[FECHAMENTO MENSAL]` no titulo do MD/HTML/PDF.
3. **Se `close_mode == false`**: prosseguir normalmente (comportamento legado).

### Fase 2 — Resumo Executivo

Redigir resumo executivo com **ate 150 palavras** contendo:

- Semaforo geral (X verde, Y amarelo, Z vermelho)
- Top 1-2 destaques positivos (indicadores que superaram meta ou recuperaram)
- Top 1-2 riscos principais (indicadores vermelhos com projecao "Improvavel")
- Projecao consolidada (tendencia geral de atingimento no periodo)

### Fase 3 — Consolidar Secoes

Montar as 6 secoes obrigatorias do WBR:

| Secao | Fonte | Foco |
|-------|-------|------|
| **1. Resumo Executivo** | Todos | Visao geral em <=150 palavras |
| **1.5. Painel de Indicadores** | Card + E2+E3 | Tabela unica com TODOS os KPIs e PPIs do Card: meta, realizado, gap, status |
| **2. Desvios e Causa-Raiz** | E3 | Semaforo + analise de fenomeno dos Vermelhos |
| **2.5. Saude do Pipeline** | E2+E3+Card | PPIs de funil: conversao, oportunidades, estagnacao |
| **3. Acoes** | E4 | Contramedidas criticas/atrasadas + metricas agregadas |
| **4. Projecoes** | E5 | Cenarios + indicadores em risco + gap |
| **5. Recomendacoes** | E3+E4+E5 | Contramedidas sugeridas + escalonamentos + ajustes de meta |

**Secao 1.5 — Painel de Indicadores (NOVO — obrigatorio):**

Tabela consolidada de TODOS os indicadores do Card de Performance, em posicao fixa e previsivel. Serve como fonte de dados para o m7-ritual-gestao (Slide 2 — Matriz de Status).

> **OBRIGATORIO antes de montar o Painel**: Ler **TODAS** as fontes de meta do Card. Metas estao em DOIS lugares:
> 1. `kpi_references[].regras_meta` — KPIs principais (Receita, Volume etc.)
> 2. `metas_ppi:` — bloco SEPARADO no top-level com metas dos PPIs de funil
>
> Use `Grep('^metas_ppi', card_path)` para confirmar existencia do bloco. Se existe, leia integralmente. PPIs em `metas_ppi` NAO sao "cinza" — recebem semaforo pela regra a (verde>=100% / amarelo 70-99% / vermelho <70%, com cap 200% para `menor_melhor`).
>
> **SKIP indicators SO-fechamento (2026-05-25):** quando `kpi_references[X].matrix_views[*].slide_visibility == ["fechamento"]` em TODAS as views, o indicador NAO entra no Painel WBR semanal. Aplicado a `tempo_de_ciclo_funil_*` (indicador retrospectivo — base parcial MTD nao tem valor analitico semanal; so renderiza em slide de Fechamento mensal). Validate-painel.py respeita essa regra automaticamente.
>
> **SPECIAL-CASE `meta=0` + `direction: menor_melhor`** (zero-target, ex: `oportunidades_sem_atividade_planejada_funil[_seg]`): a formula padrao `meta/max(real,1)×100` produz 0% mesmo com real=0 (matematicamente quebrado). Aplicar regra special-case ANTES da formula padrao:
> - `realizado == 0` → `pct = 100%` → verde
> - `realizado >= 1` → `pct = 0%` → vermelho
>
> Esta regra vale para qualquer PPI com meta=0 + menor_melhor (objetivo: pressao maxima de zerar).
>
> Verifique tambem se algum indicador tem `valor: pendente` em `metas_ppi` — esse e o unico caso valido de "cinza com justificativa". Documentar a justificativa na nota da linha do Painel.

1. **Ler o Card de Performance** da vertical via `Glob('**/Cards-de-Performance/{Vertical}/card_*.yaml')`
2. **Extrair `kpi_references[]`** — lista completa de indicadores com `papel`, `unidade`, `criterio_desvio_critico`
3. **Extrair `metas_ppi:` do Card** — cada chave e meta de PPI a aplicar com regra a (100/70/menor_melhor com cap 200%)
4. **Para cada indicador**, buscar em `dados/dados-consolidados-{vertical}.json`:
   - Valor realizado (N1 consolidado + desdobrado por especialista N2)
   - Meta (se disponivel — verificar AMBAS as fontes acima)
   - Gap absoluto e percentual
   - Semaforo (verde/amarelo/vermelho/cinza-com-justificativa)
5. **Montar tabela** com formato fixo:

```markdown
### 1.5 Painel de Indicadores

| Tipo | Indicador | Meta | Realizado | Gap | % Ating. | Status | N2: {Esp1} | N2: {Esp2} |
|------|-----------|------|-----------|-----|----------|--------|------------|------------|
| KPI  | {nome}    | {m}  | {r}       | {g} | {%}      | 🔴/🟡/🟢 | {val_esp1}  | {val_esp2} |
| PPI  | {nome}    | —    | {r}       | —   | —        | ⚪       | {val_esp1}  | {val_esp2} |
```

**Regras:**
- **Colunas N2 por especialista**: Uma coluna por especialista listado em `metadata.responsaveis` do Card
- **Tipo**: `KPI` para `papel: kpi_principal`, `PPI` para `papel: ppi_*`
- **Ordenacao**: KPIs primeiro (vermelhos por gap, amarelos, verdes), depois PPIs
- **PPIs sem meta**: exibir "—" em Meta, Gap, % Ating. O status e cinza (⚪)
- **Indicador do Card sem dados no JSON**: exibir "—" em todas as colunas de valor. **NUNCA omitir**
- **Nomes de indicadores**: usar nome legivel (ex: "Receita Seguros" em vez de "receita_seguros_mensal")
- **Unidades**: respeitar a `unidade` do Card (BRL → R$ com K/M, ratio → %, count → inteiro)

> **Esta tabela e a UNICA fonte de dados para o Slide 2 (Matriz) do m7-ritual-gestao.** Qualquer numero que aparece na Matriz DEVE existir aqui. O material-generator nao deve "garimpar" valores do WBR narrativo — deve ler esta tabela.

**Secao 2.5 — Saude do Pipeline:**

1. **Ler o Card de Performance** da vertical via `Glob('**/cards/{vertical}/*.yaml')`
2. **Extrair `logica_de_analise.kpis_analisar_como_contexto`** — PPIs de funil/processo
3. **Ler dados consolidados** de cada PPI em `dados/dados-consolidados-{vertical}.json`
4. **Apresentar** em formato compacto:

| Indicador | N1 Atual | Tendencia | Diagnostico |
|-----------|----------|-----------|-------------|
| {nome_ppi} | {valor_n1} | {↑↓→ vs M-1} | {1 linha usando racional do Card} |

> Esta secao usa dados de PPIs (sem meta formal). Nao entra no semaforo.
> Objetivo: dar ao gestor visibilidade sobre os drivers de processo que explicam os desvios de resultado.
> Se nenhum PPI de contexto disponivel no Card, omitir esta secao.

Para regras detalhadas de cada secao, consultar [wbr-structure.md](references/wbr-structure.md).

### Fase 4 — Recomendacoes

Gerar recomendacoes com base na convergencia dos relatorios:

1. **Contramedidas novas**: Vermelhos sem acao ativa em E4
2. **Escalonamentos**: Indicadores que precisam de decisao N1 (meta, recurso, prioridade)
3. **Ajustes de meta**: Se evidencia suficiente de que meta nao e atingivel (projecao "Improvavel" + causa estrutural)

Cada recomendacao deve ser **especifica e acionavel** com justificativa e prioridade.

### Fase 4.5 — Gerar Canonical Data JSON (OBRIGATORIO antes do Estruturado)

> **Single Source of Truth** para todos os artefatos do WBR. Os 4 artefatos (Estruturado MD, Narrativo MD, HTML, PDF) DEVEM derivar deste JSON. Re-edicoes (errata, ajustes pos-revisao) sempre comecam aqui.

Salvar em `wbr/wbr-{vertical}-{data}.data.json` com schema v1.3 (Item 3 follow-up Seguros-WL 2026-05-20, 2026-05-21 — bump v1.2 -> v1.3 com `recomendacoes` top-level + bloco `analise_por_responsavel` (riscos/alertas/acoes_sugeridas por esp/canal preparados para bot Telegram) + `escopo_kpi` por indicador):

```json
{
  "_schema": "wbr-canonical-data v1.3",
  "_generated_at": "{timestamp}",
  "vertical": "...",
  "data_referencia": "YYYY-MM-DD",
  "checkpoint_label": "...",

  "meta": {
    "is_first_ritual_of_month": true|false,
    "vertical": "...",
    "ciclo_label": "...",
    "snapshot_at": "{ISO timestamp}"
  },

  "semaforo_resumo": {
    "verde": N, "amarelo": N, "vermelho": N, "cinza_sem_meta": N,
    "total_com_meta": N, "total_indicadores": N
  },

  "indicadores": {
    "<indicator_id>": {
      "tipo": "KPI|PPI|...", "label": "...", "unit": "BRL|count|ratio|days",
      "meta": <num|null>, "meta_label": "R$ X.XXX|—",
      "realizado": <num>, "realizado_label": "...",
      "gap_abs": <num|null>, "gap_label": "...",
      "pct_atingimento": <num|null>, "pct_label": "...",
      "status": "verde|amarelo|vermelho|cinza",
      "status_emoji": "🟢|🟡|🔴|⚪",
      "direction": "maior_melhor|menor_melhor",
      "regra_semaforo": "kpi_padrao_95_80|metas_ppi_a_maior_melhor|metas_ppi_a_menor_melhor|metas_ppi_zero_target|metas_ppi_pendente|sem_meta_formal",
      "causa_raiz_resumo": "1-2 frases (NOVO v1.2 — vem de e3-causa-raiz-{vertical}.json) | null",
      "n2": {
        "<especialista>": {
          "realizado": N, "meta": N, "pct": N, "status": "...",
          "volume_estagnado": N,      "<- NOVO v1.2 — APENAS para indicador `oportunidades_estagnadas_funil*`. Soma de volume das rows N2 desse especialista no indicador estagnadas."
          "causa_raiz_resumo": "OPCIONAL — quando E3 detectou concentracao individual"
        }
      },
      "vol_em_risco": N,              "<- NOVO v1.2 — APENAS para indicador `oportunidades_estagnadas_funil*`. SUM(n2.*.volume_estagnado) = volume total congelado no nivel do indicador."
      "por_canal": {
        "investimentos": { "qty": N, "vol": N, "qty_won": N, "pct_ativas": N },
        "credito":       { "qty": N, "vol": N, "qty_won": N, "pct_ativas": N },
        "outros_m7":     { "qty": N, "vol": N, "qty_won": N, "pct_ativas": N }
      },
      "aggregation_rule_applied": true|false  "<- NOVO v1.2 — quando true, o N1/N2 deste indicador foi derivado via aggregation_rule de YAML (helper _derived_aggregation.py + Fase 4.5.f). Quando false/omitido, vem do output do proprio script do indicador."
    }
  },

  "projecoes": {
    "<indicator_id>": {
      "M0":  { "meta_mes": N, "base": N, "pessimista": N, "otimista": N, "classificacao": "..." },
      "M+1": { "meta_mes": N, "base": N, "pessimista": N, "otimista": N, "classificacao": "..." }
    }
  },

  "acoes": {                                "<- NOVO v1.2 — vem de e4-acoes-{vertical}.json. v1.3: atrasadas SEMPRE list[task_item] + metricas_agregadas.atrasadas_count int."
    "criticas":            [<task_item>],
    "atrasadas":           [<task_item>],
    "em_dia_priorizadas":  [<task_item>],
    "concluidas_eficazes": [<task_item>],
    "metricas_agregadas":  { "atrasadas_count": N, "...": "..." }
  },

  "recomendacoes": [                        "<- NOVO v1.3 — lista plana, NUNCA dict de 3 categorias"
    {
      "titulo": "...", "descricao": "...",
      "responsavel": "...", "prazo": "YYYY-MM-DD",
      "prioridade": "alta|media|baixa",
      "categoria": "contramedida|escalonamento|ajuste_meta"
    }
  ],

  "analise_por_responsavel": {              "<- NOVO v1.3 — OBRIGATORIO quando Card tem N2 (Cons/Seg) ou e PJ2 (por canal). Bot Telegram consome acoes_sugeridas[].descricao_curta."
    "<especialista_ou_canal>": {
      "dimensao": "especialista|canal",
      "indicadores_vermelhos": ["<indicator_id>", ...],
      "riscos": [
        {
          "tipo": "estagnadas_alto|criadas_baixo|...",
          "descricao": "18 deals estagnados (50% das ativas) R$ 2.3M aging >60d",
          "indicador_origem": "oportunidades_estagnadas_funil_seg",
          "valor_observado": 18,
          "limite_referencia": "40% ativas",
          "severidade": "alta|media|baixa",
          "cross_indicators": [                 "<- >=2 quando indicador_origem e PPI funil (Regra 51)"
            {"indicador": "oportunidades_criadas_funil_seg", "valor": 4, "semaforo": "vermelho", "relacao": "causa_provavel"},
            {"indicador": "oportunidades_ativas_funil_seg", "valor": 36, "semaforo": "amarelo", "relacao": "compensa"}
          ]
        }
      ],
      "alertas": [
        {"tipo": "criadas_zero_no_mes", "descricao": "0 criadas ate dia 20", "indicador_origem": "oportunidades_criadas_funil_seg", "acao_imediata": "Acionar prospeccao"}
      ],
      "acoes_sugeridas": [                       "<- DM-ready para bot, descricao_curta <=200 chars (Regra 52)"
        {
          "descricao_curta": "Emmanuel: 18 deals estagnados R$ 2.3M. Revisar nominalmente ate sex e marcar WIN/LOSE.",
          "descricao_completa": "...",
          "indicador_origem": "oportunidades_estagnadas_funil_seg",
          "prazo": "2026-05-25",
          "prioridade": "alta"
        }
      ]
    }
  },

  "diagnostico_principal": { "manchete": "...", "gap_principal": "...", "...": "..." }
}
```

Os campos `*_label` sao formato canonico para humanos; os campos sem sufixo sao numeros puros para computacao. Validacao cruzada (Fase 7.5) usa os numeros puros com tolerancia.

**Novidades schema v1.1 (2026-05-12):**

1. **`meta.is_first_ritual_of_month`** (bool) — replica o flag de `CICLO.md` no JSON canonical. Builder do ritual usa para escolher `effective_modo` sem precisar consultar `CICLO.md`.
2. **`indicadores.{X}.direction`** (`maior_melhor` | `menor_melhor`) — lido do YAML do indicator (schema v2.1 de `m7-metas/creating-indicators`). Builder usa em `cor_from_pct(pct, direction)` para inverter semaforo (edit #28 do `pj2-slide-requirements.md`).
3. **`indicadores.{X}.por_canal[c]`** (object opcional) — decomposicao por canal commercial (investimentos/credito/outros_m7 para PJ2; id_especialista para N3). Emitir quando o YAML do indicator declara `output_schema.por_canal`. Campos opcionais dentro de cada canal: `qty`, `vol`, `qty_won` (separado de `qty` para ticket runtime — edit #26), `pct_ativas` (estagnadas/ativas — edit #29). **Mesma CTE de canal** entre indicators correlacionados (ativas ↔ estagnadas usam mesma fonte).
4. **`projecoes.{X}.M+1`** (opt-in por vertical) — emitir apenas quando `Card.apresentacao.proj_periodos_por_vertical.{vert}` inclui `"M+1"`. Edit #31: Cons aceita M+1 (metodo `pipeline_conversion_extended_v2` calibrado); Seg ainda nao (metodo `installment_amortization` em calibracao).

**Backwards compat:** WBRs v1.0 sem `meta`/`direction`/`por_canal`/`M+1` continuam validos. Builders aplicam fallbacks:
- `meta.is_first_ritual_of_month` ausente → ler de CICLO.md (legacy)
- `direction` ausente → assume `maior_melhor`
- `por_canal` ausente → builder usa decomposicao por especialista (N3) ou agregado simples
- `projecoes.{X}.M+1` ausente → builder so renderiza M0 nos slides Pipeline/Conclusao

**Novidades schema v1.2 (2026-05-18 — S2a B4.17/B4.18/B4.20):**

5. **`indicadores.{X}.causa_raiz_resumo`** (string opcional, max ~200 chars) — vem do sidecar JSON `analise/e3-causa-raiz-{vertical}.json` emitido por E3 (Fase 6.5 do analyzing-deviations). 1-2 frases sintetizando a hipotese de causa-raiz principal. Consumido por build_deck Slide Riscos · Alertas (S1 mantém fallback graceful para texto genérico).
6. **`indicadores.{X}.n2.{esp}.causa_raiz_resumo`** (string opcional) — quando E3 detectou concentracao individual de desvio, frase específica por especialista. Consumido por build_deck Dashboard do esp (Riscos enriquecido).
7. **`indicadores.{X}.n2.{esp}.volume_estagnado`** (number) — APENAS para indicador `oportunidades_estagnadas_funil*`. Soma de `volume` das rows N2-Especialista no indicador estagnadas. Emitido em Fase 4.5.f. Substitui o fallback `_vol_estagnado_for_esp` em build_deck (linha 3119), que somava rows de `dados_consolidados` em runtime.
8. **`indicadores.{X}.vol_em_risco`** (number) — APENAS para `oportunidades_estagnadas_funil*`. Total agregado = SUM(n2.*.volume_estagnado). Consumido por build_deck Matriz N3 célula "Oport. Estagnadas (qty)" no nivel Total (linha 2995). Substitui fallback que somava por especialista em runtime.
9. **`indicadores.{X}.aggregation_rule_applied`** (bool opcional) — `true` quando o N1/n2 deste indicador foi derivado via `aggregation_rule` do YAML (Fase 4.5.f). `false` ou omitido para indicadores cujos valores vem do output do proprio script.
10. **`acoes`** (object) — vem do sidecar `e4-acoes-{vertical}.json` emitido por E4 (Fase 6.5 do summarizing-actions). 4 arrays canonicos (criticas/atrasadas/em_dia_priorizadas/concluidas_eficazes) + `metricas_agregadas`. Consumido por build_deck Slide 4 (donut + barras) e Slide 5 (PA Vencendo). Substitui a reconstrucao dinamica em runtime do build_deck.

**Backwards compat v1.1 → v1.2:** WBRs v1.1 sem os campos novos continuam validos. Builders aplicam fallbacks da S1:
- `causa_raiz_resumo` ausente → texto generico hardcoded ("Indicador X — N% meta")
- `n2.{esp}.volume_estagnado` ausente → `_vol_estagnado_for_esp` soma rows N2 de `dados_consolidados` (S1 fallback, linha 3119)
- `vol_em_risco` ausente → soma das `n2.*.volume_estagnado` ou fallback `ind.get("vol_em_risco")` (S1, linha 2995)
- `aggregation_rule_applied` ausente → assume false (indicador classico)
- `acoes` ausente → builder reconstroi dinamicamente de `clickup-tasks-{vertical}-scoped.json` (S1 fallback)

**Novidades schema v1.3 (2026-05-21 — Item 3 follow-up Seguros-WL 2026-05-20):**

11. **`acoes.atrasadas` (regra de output)** — SEMPRE `list[task_item]`. Contagem (int) vai SEMPRE em `acoes.metricas_agregadas.atrasadas_count`. Bug do ciclo v2 (atrasadas=int) NUNCA mais. Validate-painel.py via JSON Schema falha exit 2 se for emitido como int.

12. **`recomendacoes`** (top-level, `list[dict]`) — lista plana com `categoria` (`contramedida` | `escalonamento` | `ajuste_meta`) + `prioridade` (`alta` | `media` | `baixa`) em cada item. NUNCA dict de 3 categorias. Schema v1.3 enforca via `recomendacao_item` `$defs`.

13. **`analise_por_responsavel`** (NOVO bloco top-level) — riscos + alertas + acoes sugeridas estruturados por responsavel (especialista ou canal PJ2). OBRIGATORIO quando Card tem N2 ou e PJ2. Prepara payload DM-ready para o bot Telegram (memory `project_telegram_bot_alertas`) enviar alertas instantaneos por chat_id quando indicador vermelho. Detalhes completos em [analyst.md Schema v1.3 secao G/H/I](../../../agents/analyst.md). Validate-painel.py adiciona 3 regras:
    - **Regra 50** (FALHA exit 2): para cada esp/canal com indicador vermelho em N2, MUST existir entrada em `analise_por_responsavel` com >=1 risco + >=1 acao_sugerida citando aquele `indicador_origem`.
    - **Regra 51** (WARN/FALHA): PPI funil red (criadas/ativas/estagnadas/conversao) deve ter `cross_indicators[]` com >=2 entradas relacionadas (causa_provavel | consequencia | amplifica | compensa). FALHA se totalmente vazio.
    - **Regra 52** (WARN): `acoes_sugeridas[].descricao_curta` <=200 chars (DM-ready).

14. **`indicadores.{X}.escopo_kpi`** (string opcional, Item 4 follow-up) — carregado do `Card.apresentacao.escopo_kpi`. Quando `n1_escritorio`, validate-painel.py Regra 38b downgrade FALHA -> INFO (gap N1-n2 legitimo, Outros M7 nao rastreado em n2).

**Backwards compat v1.2 → v1.3:** WBRs v1.2 sem `recomendacoes` top-level ou sem `analise_por_responsavel` ainda passam o `jsonschema.validate()` (campos opcionais no schema raiz), MAS validate-painel.py Regra 50 falha exit 2 se houver vermelho em N2 e o bloco estiver ausente. Para emitir um ciclo v1.2 sem upgrade, declarar `_schema: wbr-canonical-data v1.2` (validator escolhe versao por declaracao).

**build_deck.py `_esp_riscos` refactor v1.3:**
- **Primary path:** consumir `analise_por_responsavel[esp].riscos` + `alertas` direto do canonical → renderizar slide 6+.
- **Fallback path:** quando bloco ausente (v1.2 antigo) ou `< 3 itens`, augmentar com heuristica A-H atual (Concentracao, Cobertura, Estagnacao, Mega-prospects, Anomalias, Cluster, N2 vermelho, Acoes criticas owner=esp).
- Mudanças futuras nas regras: editar `analyst.md` (config-as-code), nao build_deck.

#### Fase 4.5.a — Derivacao `pct_estagnadas_ativas` (regra estrutural)

Para Cards com `metas_ppi.oportunidades_estagnadas_funil_*.pct_ativas_max` declarado (Cons, Seg WL e qualquer vertical futura que adote o padrao), o agente DEVE criar uma entrada DERIVADA no canonical JSON ao lado da entrada original de estagnadas:

- **chave**: `oportunidades_estagnadas_funil_{vertical}_pct_ativas` (ex: `oportunidades_estagnadas_funil_pct_ativas` para Cons; `oportunidades_estagnadas_funil_seg_pct_ativas` para Seg)
- **realizado**: `qty_estagnadas / qty_ativas × 100` (em percentual, 0-100). Calcular para N1 e para cada N2 quando os dados N2 existirem.
- **meta**: valor de `pct_ativas_max` no Card
- **direction**: `menor_melhor`
- **unit**: `pct`
- **regra_semaforo**: `metas_ppi_a_menor_melhor` (regra a com cap 200%: `pct = meta / max(realizado, 1) × 100`)
- **label**: "% Estagnadas / Ativas"

A entrada original de `oportunidades_estagnadas_funil_*` (qty) deve ser preservada como **contextual** (sem semaforo proprio — exibir status `cinza` ou omitir status; manter realizado e label para referencia). A apresentacao atual ainda le `qty` ate refatoracao do material-generator — manter compatibilidade.

> Motivo: a regra de semaforo de Estagnadas migrou de Qtd absoluta para % das ativas, para que o sinal escale com o tamanho do pipeline. Cards declaram a nova meta em `pct_ativas_max`; a derivacao do realizado e responsabilidade do consolidating-wbr.

#### Fase 4.5.b — Leitura de `por_especialista` (meta N2 individual)

Para Cards com subbloco `por_especialista:` em qualquer chave de `metas_ppi.{ppi}` (ex: `oportunidades_ativas_funil_seg.por_especialista`), o agente DEVE popular `n2.{especialista}.meta` no canonical JSON com o valor correspondente:

- Para cada especialista em `metadata.responsaveis` ou `apresentacao.responsaveis`, ler `metas_ppi.{ppi}.por_especialista[especialista].{qty|volume|ticket_medio}` e gravar em `indicadores.{indicator_id}.n2.{especialista}.meta`
- Calcular `n2.{especialista}.pct` e `n2.{especialista}.status` aplicando a mesma regra de semaforo do indicador (regra a com `direction`)
- Se o subbloco `por_especialista` nao existir, manter comportamento atual (so realizado N2, sem meta N2)

> Motivo: especialistas com KPIs Receita/Volume divergentes (ex: Claudia vs Tarcisio em Seg WL) precisam de PPIs derivados diferentes. O Card declara N1 (SUM) no top-level e N2 individual no subbloco `por_especialista`. Apresentacao atual ignora `n2.{esp}.meta` (so renderiza realizado N2 hoje) — sem regressao. Quando refatorada, ela passa a consumir esse campo.

#### Fase 4.5.c — Schema rico para `riscos_principais`, `destaques_positivos`, `anomalias` (OBRIGATORIO)

> **NOVO 2026-05-14:** o analyst E6 DEVE emitir essas listas como `list[dict]` com campos analiticos, NUNCA como `list[str]` de frases soltas. A regra rich-narrative
> resolve o sintoma "Top 3 riscos com textinho obvio sem analise" do deck.

Para cada item de `riscos_principais`, `destaques_positivos` ou `anomalias`, emitir um dict com as chaves abaixo. Campos opcionais podem ser omitidos quando nao houver dado, mas `titulo`/`texto` (ou `descricao`/`acao` para anomalias) sao **mandatorios**.

**Schema `riscos_principais` / `destaques_positivos`** (mesma forma):

```json
{
  "titulo": "Estagnadas em 68,5% das ativas (meta <=40%)",
  "texto": "37 deals parados sustentam R$ 50,7M congelados. Pareto: Pedro Ramos (B2B Alta Renda Douglas) responde por 8 deals; 4 deles sem atividade no Bitrix ha >21 dias.",
  "causa": "Falta de cadencia disciplinada de follow-up apos Apresentacao; assessores priorizam novos deals em vez de fechar os ja iniciados.",
  "impacto": "Se conversao maio MTD (0%) persistir 2 semanas, gap fica em fator 24x vs meta R$ 16,5M.",
  "owner": "Douglas Silva",
  "prazo": "2026-05-15"
}
```

**Schema `anomalias`** (descricao + acao):

```json
{
  "descricao": "Volume MTD R$ 500K vs meta R$ 16,5M = 3% atingimento — outlier vs media historica 35-40%.",
  "acao": "Joel + Douglas decidir win/lose/renegociar ICOFORT (R$ 60M parado em Cotas Alocadas) ate sexta."
}
```

**Regras:**
- Cada `titulo` (ou `descricao`) tem que ser uma **observacao analitica**, nao uma descricao plana do que esta vermelho. Ruim: "Volume vermelho". Bom: "Volume MTD em 3% da meta no D+9 vs media historica 35-40%".
- `texto` (~80-200 chars) carrega o **dado de suporte** (Pareto, fator, distribuicao por assessor, comparativo periodo anterior).
- `causa` quando inferivel — usa cadeia causa-efeito da Biblioteca de Indicadores (mesma fonte do E3 analyzing-deviations).
- `impacto` quando ha projecao quantificada (gap, valor em risco, # dias).
- `owner`/`prazo` quando ha decisao binaria pendente.

**Backwards-compat:** o builder do ritual (preparing-materials/build_deck.py) tem shim (`_normalize_v1_1_to_v1_0`) que aceita `list[str]` legacy e quebra em titulo+texto via `_split_str_to_titulo_texto`. Mas a quebra heuristica perde a estrutura analitica — emitir dict desde a fonte e a forma correta.

#### Fase 4.5.d — Consumir sidecar `e3-causa-raiz-{vertical}.json` (NOVO v1.2 — S2a B4.17)

> Sidecar emitido por E3 (analyzing-deviations Fase 6.5).

1. **Localizar sidecar:** `{cycle_folder}/analise/e3-causa-raiz-{vertical}.json`
2. **Validar schema:** chave `_schema == "e3-causa-raiz v1.0"`, `vertical` bate
3. **Para cada `<indicator_id>` no sidecar:**
   - `e3.indicadores.{id}.causa_raiz_resumo` → `canonical.indicadores.{id}.causa_raiz_resumo`
   - `e3.indicadores.{id}.n2_breakdown.{esp}.causa_raiz_resumo` → `canonical.indicadores.{id}.n2.{esp}.causa_raiz_resumo` (quando `n2_breakdown` presente)
4. **Validação cruzada:** todo indicador `vermelho` no canonical DEVE ter `causa_raiz_resumo` populado. Se nao, emitir WARN no log + manter fallback graceful (build_deck cai em texto generico — comportamento S1)
5. **Se sidecar nao existe:** WARN no log, mas NÃO bloquear emissao do canonical (fallback graceful). E3 pode ter falhado ou nao foi rodado — registrar em CICLO.md > Log para investigacao
6. **Se sidecar existe mas vertical/data nao bate:** ERROR + bloquear emissao (consistencia violada)

#### Fase 4.5.e — Consumir sidecar `e4-acoes-{vertical}.json` (NOVO v1.2 — S2a B4.18)

> Sidecar emitido por E4 (summarizing-actions Fase 6.5).

1. **Localizar sidecar:** `{cycle_folder}/analise/e4-acoes-{vertical}.json`
2. **Validar schema:** `_schema == "e4-acoes v1.0"`, `vertical` bate, 4 categorias presentes (mesmo que arrays vazios)
3. **Injetar no canonical:**
   - `canonical.acoes.criticas` ← `e4.acoes.criticas`
   - `canonical.acoes.atrasadas` ← `e4.acoes.atrasadas`
   - `canonical.acoes.em_dia_priorizadas` ← `e4.acoes.em_dia_priorizadas`
   - `canonical.acoes.concluidas_eficazes` ← `e4.acoes.concluidas_eficazes`
   - `canonical.acoes.metricas_agregadas` ← `e4.metricas_agregadas`
4. **Aplicar alias legacy:** se sidecar tem `em_dia_proximas` em vez de `em_dia_priorizadas` (compat ate v6.1.0), copiar para `em_dia_priorizadas` no canonical. Log INFO.
5. **Validacao cruzada com E3:** se uma task `critica` tem `indicador_impactado` que esta `vermelho` em E3, adicionar flag `is_evidencia_e3: true` ao task_item. Use para destaque visual em build_deck.
6. **Se sidecar nao existe:** WARN + emitir `acoes: null` no canonical. Build_deck cai em fallback (reconstroi dinamicamente de clickup-tasks-scoped.json) — comportamento S1 preservado.

#### Fase 4.5.f — Aplicar `aggregation_rule` para indicadores DERIVADOS (NOVO v1.2 — S2a B4.20)

> Substitui Fase 4.5.a (derivacao hardcoded de `pct_estagnadas_ativas`). Generaliza para qualquer indicador YAML que declare `aggregation_rule`.

1. **Identificar indicadores derivados:** percorrer `_index.yaml` e localizar YAMLs com bloco `aggregation_rule.type` declarado (v3.2 do schema; ex: `oportunidades_estagnadas_funil_pct_ativas` em Cons/Seg/PJ2).
2. **Para cada indicador derivado:**
   - Ler `aggregation_rule.type`, `numerator`, `numerator_field`, `denominator`, `denominator_field`, `multiplier`, `applied_at_levels`
   - Buscar outputs dos indicadores componentes em `{cycle_folder}/dados/raw/{numerator}-{vertical}.json` e `{denominator}-{vertical}.json`
   - Para cada nivel em `applied_at_levels`:
     - **N1-Escritorio:** `value = SUM(numerator.rows nivel=N1.{numerator_field}) / SUM(denominator.rows nivel=N1.{denominator_field}) * multiplier`
     - **N2-Especialista** (ou N2-Canal para PJ2): para cada especialista/canal, `value = SUM(numerator.rows[esp].{numerator_field}) / SUM(denominator.rows[esp].{denominator_field}) * multiplier`
     - Niveis N3/N4/N5: idem, agregando pelo grupo correspondente
   - **Cap em 200%** quando `type == ratio_from_components` e `multiplier == 100`. Quando denominator = 0, emitir `null` (não dividir por zero).
3. **Popular canonical:**
   - `canonical.indicadores.{derived_id}.realizado` = value N1 calculado
   - `canonical.indicadores.{derived_id}.n2.{esp_or_canal}.realizado` = value N2 calculado
   - `canonical.indicadores.{derived_id}.meta` = lido do Card (`metas_ppi.{derived_id}.{field_meta}` ou padrao do schema)
   - `canonical.indicadores.{derived_id}.aggregation_rule_applied = true` (flag)
   - `canonical.indicadores.{derived_id}.direction` = lido do YAML do derivado (geralmente `menor_melhor`)
   - Calcular `pct_atingimento`, `gap_abs`, `status` aplicando regra de semaforo do indicador (`metas_ppi_a_menor_melhor` para % estagnadas, etc.)
4. **Fase 4.5.a (legacy) e DEPRECATED em v1.2:** a derivacao hardcoded de `pct_estagnadas_ativas` agora vem da Fase 4.5.f. Para retrocompatibilidade, Fase 4.5.a continua funcionando se NAO houver YAML derivado declarando aggregation_rule (cards antigos podem ter regra inline no Card via `pct_ativas_max`). Quando ambos existem, **YAML aggregation_rule prevalece** — Fase 4.5.a vira no-op e log INFO.
5. **Emissao de `n2.{esp}.volume_estagnado` e `vol_em_risco`** (independente de aggregation_rule):
   - Para o indicador `oportunidades_estagnadas_funil*` (numerator do derivado, NÃO o derivado):
     - Para cada especialista: `volume_estagnado = SUM(rows[esp].volume)` (campo `volume` do output_contract). Gravar em `canonical.indicadores.{id_estagnadas}.n2.{esp}.volume_estagnado`
     - Total: `vol_em_risco = SUM(n2.*.volume_estagnado)`. Gravar em `canonical.indicadores.{id_estagnadas}.vol_em_risco`
6. **Validacao:** se aggregation_rule referencia indicadores que NAO estao no `_index.yaml` ou cujos outputs nao existem em `dados/raw/`, ERROR + bloquear emissao + log explicito. NAO fazer fallback silencioso (caso classico de erro de configuracao).

#### Fase 4.5.g — Consumir sidecar `projection-by-especialista.json` (NOVO v1.3 — 2026-05-26)

> Sidecar emitido por E5 (projecting-results Fase 6.5/6.6). Resolve gap onde projecoes N2 ficavam isoladas no sidecar e build_deck nao tinha como ler — fallback prorata era ambiguo e meta_m1 herdava meta_m0 incorretamente. Aplica-se a TODAS as verticais (Cons, Seg WL, Seg RE, PJ2, Inv) sem hardcode.

1. **Localizar sidecar:** `{cycle_folder}/analise/projection-by-especialista.json`
2. **Validar schema:** chave `_schema` presente, bloco `especialistas` existe
3. **Para cada `<esp>` em `especialistas` e cada `<ind>` projetavel (volume_*, receita_*, qty/quantidade_*):**
   - Para cada horizonte `H` em `("M0", "M+1")`:
     - Se `especialistas.{esp}.{ind}.{H}` existe, copiar para `canonical.projecoes.{ind}.{H}.por_especialista.{esp}` os campos:
       - `meta_mes` (CRITICO — permite build_deck inferir meta_m1 distinta de meta_m0)
       - `base`, `pessimista`, `otimista` (cenarios)
       - `classificacao` (Provavel/Possivel/Improvavel)
       - `realizado_mtd`, `lagging_M0`, `realizado_lagging`, `realizado_lagging_ja_no_ledger` (quando presentes)
       - Outros campos diagnosticos (`pct_atingimento_mtd`, `racional`) opcionais
4. **Tambem injetar nos indicadores (compat com fallback legacy do build_deck):**
   - `canonical.indicadores.{ind}.n2.{esp}.projecao_mes_corrente` = `M0.base`
   - `canonical.indicadores.{ind}.n2.{esp}.projecao_mes_seguinte` = `M+1.base`
   - `canonical.indicadores.{ind}.n2.{esp}.classificacao_mes_corrente` = `M0.classificacao`
   - `canonical.indicadores.{ind}.n2.{esp}.classificacao_mes_seguinte` = `M+1.classificacao`
5. **Consolidado N1 (Fase 6.6 do projecting-results):** se sidecar tem `consolidado_n1.{ind}.{realizado_mtd, projecao_mes_corrente, projecao_mes_seguinte, meta_mes, gap_meta, classificacao}`, garantir que `canonical.projecoes.{ind}.{M0|M+1}` ja contem esses campos N1 (E6 ja faz isso na Fase 4.5 base — Fase 4.5.g so reforca se ausente).
6. **Se sidecar ausente:** WARN no log, fallback graceful (build_deck cai em prorata sobre N1 share). NAO bloquear emissao.
7. **Se sidecar existe mas vertical nao bate:** ERROR + bloquear (canonical malformado).

**Consumo downstream pelo build_deck.py (rotina `_esp_proj_section`):**

- **proj_m0 / proj_m1 (valor base)**: prefer `canonical.projecoes.{ind}.{horizon}.por_especialista.{esp}.base` → fallback `indicadores.{ind}.n2.{esp}.projecao_mes_corrente` → fallback prorata N1 share.
- **meta_m0 / meta_m1**: prefer `Card.metas_ppi.{ind}.por_especialista.{esp}.{valor|valor_proximo_mes}` → fallback `canonical.projecoes.{ind}.{horizon}.por_especialista.{esp}.meta_mes` (NOVO v1.3) → fallback meta_m0 herdado.
- **classificacao**: prefer `M0/M+1.por_especialista.{esp}.classificacao` → fallback `indicadores.{ind}.n2.{esp}.classificacao_mes_corrente/seguinte`.

**Backwards compat v1.2 → v1.3:** WBRs antigos sem `por_especialista` continuam validos. Build_deck aplica fallbacks (prorata) e Card.metas_ppi continua sendo a fonte autoritativa de meta_m1 quando declarado.

> **FIM DA PASSADA 1 do analyst.** O canonical esta escrito (com metas do cache
> `metas_ppi:` do Card). O analyst RETORNA aqui. O main thread assume e executa a Fase 4.6
> ANTES de invocar a Passada 2 (Fases 5–7).

### Fase 4.6 — Inject SoT `m7Prata.ciclo_metas_ppi` (MAIN THREAD, bash — NOVO v6.5.0 2026-06-12)

> **Roda no MAIN THREAD (tem Bash), entre as 2 passadas do analyst.** Substitui as metas
> dos indicadores **OPTED-IN** pelos valores do SoT da tabela e recalcula
> `pct_atingimento`/`gap`/`status`. Tira o LLM do loop de transcrever metas e garante que
> a Passada 2 (Estruturado/Narrativo) derive do canonical ja injetado.

**Passo 1 — normalize (conserta shape ANTES do inject):**
```bash
python3 {plugin_path}/skills/consolidating-wbr/scripts/normalize_canonical.py \
  --cycle-folder {cycle_folder} --vertical {vertical} [--subnivel {subnivel}]
```

**Passo 2 — inject:**
```bash
python3 {plugin_path}/skills/consolidating-wbr/scripts/inject_metas_ppi.py \
  --data {cycle_folder}/wbr/wbr-{vertical}-{data}.data.json \
  --card {path_to_card} --vertical {consorcios|seguros_wl|seguros_re}
  # --mes deriva de data_referencia; --dry-run p/ preview
```

Garantias do script:
1. **OPT-IN:** so altera indicadores cujo Card declara `fonte: m7Prata.ciclo_metas_ppi` no bloco `metas_ppi.{ind}`. Sem opt-in → **NO-OP** (cache do Card permanece; rollback trivial).
2. **ESCOPO count/BRL:** injeta apenas metas de unidade nao-ambigua — `oportunidades_ativas_funil` (qty + volume; substancia real da migracao, formula corrigida), `oportunidades_criadas_funil`, `oportunidades_sem_atividade_planejada_funil`. **NAO** injeta ratio/days (`taxa_conversao`, `tempo_de_ciclo`, `estagnadas_pct_ativas`) — constantes de gestao identicas em Card e tabela, com unidade inconsistente no canonical (percent vs ratio) e naming WL/RE divergente. Esses ficam no Card (canonical via Fase 4.5).
3. **N1/N2 corretos:** le `m7Prata.vw_ciclo_metas_ppi` (ultimo snapshot via `argMax(data_ref)`); N1 = SUM(squad) p/ count/BRL; N2 por `id_colaborador`/`nome_referencia`. Cada Card filtra SO o seu squad (Seg WL ≠ Seg RE, mesmo `vertical='Seg'`; a linha N1 literal da tabela = WL+RE somados, NAO usar).
4. **Offline-safe:** ClickHouse fora (office-only) → WARN + exit 0, canonical intacto, cache do Card vale. NUNCA bloqueia.
5. **Auditavel:** backup `.bak`, atualiza `meta_fonte`, imprime diff (de→para).

> Pre-requisito antes de declarar `fonte:` num Card novo: rodar `compare_metas_card_vs_tabela.py --vertical {v}` e revisar divergencias. PJ2 NAO usa esta fase (canonical por canal — pendente, ver build_deck_pj2).

**Passo 3 — resolver META de M+1 dos KPIs a partir dos dados coletados (NOVO 2026-06-22):**
```bash
python3 {plugin_path}/skills/consolidating-wbr/scripts/resolve_kpi_m1_meta.py \
  --data {cycle_folder}/wbr/wbr-{vertical}-{data}.data.json \
  --raw-dir {cycle_folder}/dados/raw \
  --sidecar {cycle_folder}/analise/projection-by-especialista.json
  # --dry-run p/ preview
```

Garantia: para os KPIs de meta-mensal-por-tabela (`receita_*`, `volume_*`,
`quantidade_*`), grava em `projecoes.{ind}.M+1.meta_mes` (N1) e
`.por_especialista.{esp}.meta_mes` (N2) a meta REAL do mes seguinte — lida da
linha do mes M+1 em `dados/raw/{ind}.json` (o script de coleta ja traz TODOS os
meses). Recomputa `gap_meta` + `classificacao` de M+1. **Corrige o bug em que o
E5 HERDAVA a meta de M0 no M+1** (ex Cons: receita jul real R$ 289K vs jun R$ 243K;
a meta lagging cresce mes a mes). PPIs de funil NAO sao tocados (meta vem do
`ciclo_metas_ppi`, Passo 2). Se o mes seguinte nao estiver cadastrado na tabela,
mantem o valor existente e marca `m1_meta_inherited=true` (transparente — nunca
inventa meta). Idempotente, backup `.bak`. Sem dependencia nova de office: a meta
de M+1 ja foi coletada no E2.

### Fase 5 — Validar e Salvar WBR Estruturado

> **PASSADA 2 do analyst — Fases 5 a 7.** Reinvocar o analyst para escrever os docs LENDO
> o canonical JSON **ja injetado/normalizado** (Fase 4.6). **NAO reescrever `indicadores.*`**
> — o canonical e a fonte de verdade; aqui so se LE para formatar.

1. Executar checklist de coerencia (ver [wbr-structure.md](references/wbr-structure.md))
2. Salvar `wbr/wbr-{vertical}-{data}.md` (na pasta do ciclo)

### Fase 6 — Gerar WBR Narrativo

> **REGRA CRITICA**: ler numeros APENAS de `wbr-{vertical}-{data}.data.json` (Fase 4.5). NAO extrair numeros do Estruturado MD (risco de copiar errado e divergencia). O canonical JSON e o SoT.

Gerar o WBR Narrativo seguindo o [template](templates/wbr-narrativo.tmpl.md) e as [regras de escrita narrativa](references/wbr-structure.md#wbr-narrativo--estrutura-e-regras).

O WBR Narrativo reutiliza **exatamente os mesmos numeros** do canonical JSON, mas apresenta-os como prosa executiva com fluxo Situacao → Complicacao → Acao → Perspectiva.

**7 secoes obrigatorias:**

1. **Manchete** (~1-2 frases): Veredito da semana — destaque positivo + risco critico
2. **Panorama** (~3-5 frases): Semaforo em prosa, projecao consolidada, contexto relevante
3. **O que Preocupa** (~1-2 paragrafos por Vermelho): O que aconteceu → Por que → O que significa. Incorporar diagnosticos de PPIs de funil quando relevantes para explicar a causa (ex: "o funil tem 32 oportunidades ativas mas 8 estagnadas, indicando gargalo de fechamento")
4. **O que Estamos Fazendo** (~1 paragrafo): Acoes criticas, eficacia, volume em risco
5. **Para Onde Estamos Indo** (~1-2 paragrafos): Projecoes em linguagem de decisao
6. **O que Precisa Acontecer** (bullets): Decisoes com owner + deadline, escalonamentos
7. **Destaques Positivos** (2-5 bullets): Reconhecimento de resultados e pessoas

**Regras criticas**:
- Numeros identicos ao WBR Estruturado (mesma fonte de verdade)
- Comparativos obrigatorios: todo numero com referencia (vs meta, vs periodo anterior)
- Causa-raiz narrada como historia, nao como lista de dimensoes
- Cada desvio termina com consequencia projetada ("se nada mudar...")
- Acoes sempre com owner e deadline
- Escalonamentos enquadrados como decisao binaria
- Extensao: 600-1000 palavras (1.5-2.5 paginas)

Salvar em `wbr/wbr-narrativo-{vertical}-{data}.md` (na pasta do ciclo).

### Fase 6b — Gerar WBR Narrativo HTML

> **REGRA CRITICA**: numeros lidos APENAS do canonical JSON (Fase 4.5). KPI cards, semaforo grid e dados dos charts D3 referenciam o JSON, nao copiam de Estruturado/Narrativo MD.

Gerar a versao HTML visual seguindo o [template](templates/wbr-narrativo.tmpl.html) e o [guia de geracao HTML](references/wbr-html-guide.md).

O WBR Narrativo HTML reutiliza **exatamente os mesmos numeros** do canonical JSON, mas apresenta-os com:
- Visualizacoes D3.js inline (bar charts, donut charts, funnel diagrams, cenarios de projecao)
- KPI cards com cor de status
- Semaforo visual em grid
- Timeline de acoes com dots coloridos
- Cards de destaques positivos
- Box de decisao critica

**Processo de geracao**:

1. **Ler o template** `templates/wbr-narrativo.tmpl.html` via Read tool
2. **Copiar o CSS inteiro** (bloco `<head>` com ~500 linhas) sem alteracoes
3. **Substituir placeholders** `{{...}}` com dados reais do WBR Estruturado
4. **Gerar graficos D3.js inline** seguindo as receitas do `references/wbr-html-guide.md`:
   - Horizontal bar chart para indicadores por assessor/especialista
   - Donut chart para composicao percentual
   - Funnel chart para pipeline CRM (se dados PPI disponiveis)
   - Cenarios P10/Base/P90 para projecoes
5. **Montar callouts** com interpretacao e insights para cada secao
6. **Validar** que todos os numeros conferem com WBR Estruturado

**Regras**:
- CSS do template e imutavel (ja validado pelo design system M7-2026, score A)
- Logo M7 esta embeddado como base64 no template — nao alterar
- Minimo 2 graficos D3, maximo 5
- D3 v7 CDN script tag deve estar no `<head>` (ja incluido no template)
- Cada chart container `<div>` deve ter um `id` unico
- Usar hex direto para cores no JS (CSS `svg text` cuida da tipografia automaticamente)

Salvar em `wbr/wbr-narrativo-{vertical}-{data}.html` (na pasta do ciclo).

### Fase 6c — Gerar PDF do WBR Narrativo

Converter o HTML gerado na Fase 6b em PDF via Puppeteer:

1. **Verificar dependencias**: Se `scripts/node_modules` nao existe, executar:
   ```bash
   cd {path_to_plugin}/skills/consolidating-wbr/scripts && npm install
   ```
2. **Gerar PDF** via Bash:
   ```bash
   node {path_to_plugin}/skills/consolidating-wbr/scripts/html-to-pdf.js \
     {cycle_folder}/wbr/wbr-narrativo-{vertical}-{data}.html \
     {cycle_folder}/wbr/wbr-narrativo-{vertical}-{data}.pdf
   ```
3. **Verificar** que o PDF foi gerado: `ls {cycle_folder}/wbr/wbr-narrativo-{vertical}-{data}.pdf`
4. Se falhar: registrar em CICLO.md > Anomalias como WARNING (PDF e complementar, nao bloqueia pipeline)

### Fase 7 — Verificacao Numerica (Spot-Check)

Antes de finalizar, verificar consistencia numerica entre WBR e dados de origem:

1. Ler `dados/dados-consolidados-{vertical}.json` da pasta do ciclo (via Read tool)
2. Selecionar os TOP 3 indicadores por gap (maior desvio entre realizado e meta)
3. Para cada indicador, verificar que os valores `realizado` e `meta` no WBR **E no HTML** correspondem EXATAMENTE ao JSON consolidado
4. Comparar `total_realizado_sum` do WBR com `metadata._verification.total_realizado_sum` do consolidado
5. Se QUALQUER discrepancia: registrar em CICLO.md > Anomalias e inserir aviso no WBR:
   `> AVISO: Discrepancia numerica detectada entre WBR e dados de origem. Valores podem nao ser confiaveis.`
6. Registrar no CICLO.md > Log: `[{timestamp}] AGENTE:analyst — Spot-check: {N}/3 verificacoes OK`

### Fase 7.5 — Validacao Programatica (Painel + Cross-Artifact)

> **Painel: GATE OBRIGATORIO. Cross-artifact: ADVISORY.**

**Passo 0 (safety idempotente) — Normalizar shape dos JSON antes do gate:** roda o normalizador
deterministico que conserta divergencias de FORMA recorrentes do analyst (indicadores
list->dict, status->semaforo, painel.indicadores->top-level, acoes.em_dia->em_dia_priorizadas,
projecoes.M+1 null removido). Idempotente — no-op quando ja conforme.

> **NOTA v6.5.0:** este normalize JA rodou na **Fase 4.6** (antes do inject). Rodar de novo
> aqui e safety idempotente (cobre shapes que a Passada 2 do analyst possa ter reintroduzido
> nos docs/canonical). Mantido.

```bash
python3 {plugin_path}/skills/consolidating-wbr/scripts/normalize_canonical.py \
  --cycle-folder {cycle_folder} --vertical {vertical} [--subnivel {subnivel}]
```

Depois, executar o gate via Bash com TODOS os artefatos (incluindo `--e3` para pegar o
bug silencioso de shape do sidecar E3):

```bash
python3 {plugin_path}/skills/consolidating-wbr/scripts/validate-painel.py \
  --card {path_to_card_yaml} \
  --wbr {cycle_folder}/wbr/wbr-{vertical}-{data}.md \
  --data {cycle_folder}/wbr/wbr-{vertical}-{data}.data.json \
  --narrativo {cycle_folder}/wbr/wbr-narrativo-{vertical}-{data}.md \
  --html {cycle_folder}/wbr/wbr-narrativo-{vertical}-{data}.html \
  --e3 {cycle_folder}/analise/e3-causa-raiz-{vertical}.json
```

**Validacoes em sequencia (exit final = max de todas):**

1. **Painel (GATE)**: confere que toda meta em `kpi_references[].regras_meta` ou `metas_ppi:` aparece no Painel do Estruturado com Meta preenchida e Status colorido. Falha (exit 1) bloqueia o ciclo.

2. **Cross-Artifact (ADVISORY, gate opt-in)**: confere que numeros criticos (realizado + meta de cada indicador) do canonical JSON aparecem em estruturado/narrativo/html dentro de tolerancia 5%. Default = AVISO (exit 0) — revisao manual (numeros podem divergir por formatacao legitima, ex "121,7K" vs "121.713"). Com `--strict-cross-artifact` (execucao unattended), divergencia vira FALHA (exit 1).

3. **Schema v1.1/v1.3 (GATE)**: aditividade N2 (Regra 38b), `analise_por_responsavel` (Regra 50), direction, etc. Falha critica = exit 2.

4. **Plausibilidade (GATE, 2026-06-18)**: sanidade semantica `realizado/meta/status` — pega erro SILENCIOSO que passa pelos gates de shape. Ex classico: `realizado=0 + meta>0 + status=verde` (maior_melhor) → impossivel. Tambem pega verde com ratio<0,60 e vermelho com ratio>=1,05 (contradicao 2-band). Falha = exit 2. `amarelo + realizado=0` vira AVISO (nao bloqueia — pode ser MTD inicio de mes). Baseia-se no ratio recomputado `realizado/meta` (nao no `pct_atingimento` armazenado, que e ratio 0-1). Pula derivados e unidades ratio/pct.

5. **Close_mode / retrospectiva (ADVISORY, P2.3 2026-06-18)**: quando o ciclo e FECHAMENTO (checkpoint contem "fechamento" ou data_referencia = ultimo dia do mes), `close_mode`/`is_retrospective` devem estar setados — senao o deck renderiza projecao FUTURA num mes ja fechado. Tambem avisa se algum bloco `projecoes.{ind}.is_retrospective != True` com close_mode ligado. AVISO (exit 0).

6. **Cobertura + causa-raiz E3 (ADVISORY, P2.1+P2.2 2026-06-18)**: requer `--data` + `--e3`. Para cada indicador VERMELHO no Painel, confere que existe entrada no sidecar E3 (senao: desvio nao analisado) e que `causa_raiz_resumo` nao e vazia/placeholder/trivial ("varias", <25 chars). AVISO (exit 0) — qualidade textual tem FP, so torna visivel.

**Comportamento por exit code:**
- **Exit 0**: Painel OK + Cross-artifact/plausibilidade OK ou advisory
- **Exit 1**: Painel falhou — corrigir Estruturado e re-executar
- **Exit 2**: Erro de leitura OU falha critica de schema (38b/50), aditividade ou plausibilidade — corrigir o canonical JSON e re-executar

Se exit 1 (Painel falhou):
1. Ler saida do script — identificar quais indicadores estao omissos/cinza sem justificativa
2. Corrigir o canonical JSON (Fase 4.5) — fonte de verdade
3. Re-gerar Estruturado, Narrativo, HTML, PDF a partir do canonical JSON corrigido
4. Re-executar validate-painel.py ate exit 0
5. **NAO concluir E6 com Painel falhando**

Se exit 0 com avisos cross-artifact:
1. Ler avisos — sao numeros que estao no canonical JSON mas nao casam com nenhum numero (com tolerancia 5%) no artefato citado
2. Verificar manualmente: se for prosa abreviada ("R$ 121,7K" no narrativo vs canonical "R$ 121.713") aceitar; se for divergencia real (canonical=R$ 80K, narrativo cita R$ 36K = ciclo anterior) corrigir o artefato
3. Re-executar para confirmar

Registrar em CICLO.md > Log: `[{timestamp}] SCRIPT:validate-painel — painel=exit_{code} | cross_artifact={N} avisos`

### Fase 8 — Finalizar

1. Atualizar CICLO.md com status "concluido" para E6
2. Registrar os quatro artefatos no CICLO.md (WBR Estruturado .md, WBR Narrativo .md, WBR Narrativo .html, WBR Narrativo .pdf)

## Exit Criteria

- [ ] **Canonical Data JSON gerado** em `wbr/wbr-{vertical}-{data}.data.json` (Fase 4.5) com schema **v1.2** (S2a B4.17/B4.18/B4.20) — SoT para todos os artefatos
- [ ] **Fase 4.5.d:** sidecar `e3-causa-raiz-{vertical}.json` consumido, `indicadores.{id}.causa_raiz_resumo` populado em todos os vermelhos (WARN se ausente; ERROR se vertical/data nao bate)
- [ ] **Fase 4.5.e:** sidecar `e4-acoes-{vertical}.json` consumido, `acoes.{4 categorias}` populadas no canonical (alias `em_dia_proximas → em_dia_priorizadas` aplicado quando legacy)
- [ ] **Fase 4.5.f:** indicadores com `aggregation_rule` declarado tem `aggregation_rule_applied: true` no canonical; N1/N2 computados via SUM(num)/SUM(den)*multiplier; Fase 4.5.a legacy DEPRECATED quando YAML novo prevalece
- [ ] **Fase 4.5.g (NOVO v1.3):** sidecar `projection-by-especialista.json` consumido; cada `<esp>` × `<ind>` × `<horizon>` injetado em `canonical.projecoes.{ind}.{M0|M+1}.por_especialista.{esp}` (com `meta_mes, base, pessimista, otimista, classificacao`) + reforco em `indicadores.{ind}.n2.{esp}.projecao_mes_corrente/seguinte` (compat fallback). Build_deck Pipeline slides renderiza barras corretas; meta_m1 distinta de meta_m0 quando aplicavel. Generico para todas as verticais.
- [ ] **`n2.{esp}.volume_estagnado` emitido** para `oportunidades_estagnadas_funil*` em cada especialista (substitui fallback build_deck `_vol_estagnado_for_esp`)
- [ ] **`vol_em_risco` emitido** no Total do indicador estagnadas (SUM dos n2.*.volume_estagnado)
- [ ] **Validacao JSON Schema** (S2a B6.25) — `wbr-{vertical}-{data}.data.json` valida contra `m7-operations/_schema/v1.2/wbr-canonical-data.schema.json` antes de prosseguir para Fase 5 (WBR Estruturado MD). Se schema violation, BLOQUEAR emissao do MD — canonical malformado propaga bug para deck e briefing.
- [ ] WBR Estruturado gerado com 6 secoes obrigatorias presentes e nao vazias (incluindo 1.5 Painel) — **lido a partir do canonical JSON**
- [ ] Painel de Indicadores (Secao 1.5) contem TODOS os indicadores do Card de Performance
- [ ] **`metas_ppi:` do Card foi lido e aplicado** no Painel (verificar via `Grep('^metas_ppi', card_path)`)
- [ ] **`validate-painel.py` retornou exit 0 no Painel** (Fase 7.5) — gate obrigatorio antes de concluir E6
- [ ] Cross-artifact validation rodada (advisory) — divergencias residuais revisadas e aceitas/corrigidas
- [ ] Painel com colunas N2 por especialista conforme Card `metadata.responsaveis`
- [ ] Resumo Executivo com <=150 palavras
- [ ] Narrativa coerente (sem contradicoes entre secoes)
- [ ] Dados numericos identicos aos relatorios de origem
- [ ] Recomendacoes especificas e acionaveis
- [ ] WBR autocontido (legivel sem consultar relatorios parciais)
- [ ] Arquivo estruturado salvo em `wbr/wbr-{vertical}-{data}.md` (na pasta do ciclo)
- [ ] WBR Narrativo gerado com 7 secoes (Manchete, Panorama, O que Preocupa, O que Estamos Fazendo, Para Onde Estamos Indo, O que Precisa Acontecer, Destaques Positivos)
- [ ] WBR Narrativo com numeros identicos ao Estruturado
- [ ] WBR Narrativo com 600-1000 palavras
- [ ] Arquivo narrativo salvo em `wbr/wbr-narrativo-{vertical}-{data}.md` (na pasta do ciclo)
- [ ] CICLO.md atualizado com os quatro artefatos E6
- [ ] WBR Narrativo HTML gerado com CSS M7-2026 inalterado
- [ ] HTML contem pelo menos 2 graficos D3.js inline com containers unicos
- [ ] Numeros no HTML identicos ao WBR Estruturado
- [ ] Logo M7 presente no cover (base64 inline)
- [ ] Arquivo HTML salvo em `wbr/wbr-narrativo-{vertical}-{data}.html` (na pasta do ciclo)
- [ ] PDF gerado em `wbr/wbr-narrativo-{vertical}-{data}.pdf` (na pasta do ciclo)

## Anti-Patterns

- NUNCA contradiga dados entre secoes (ex: indicador Verde no semaforo mas listado como risco)
- NUNCA arredonde numeros de forma diferente da origem (manter precisao do relatorio parcial)
- NUNCA gere recomendacoes genericas ("melhorar performance") — sempre especificas com justificativa
- NUNCA omita secoes — todas as 6 sao obrigatorias (1, 1.5, 2, 3, 4, 5), mesmo que vazias com "Nenhum item nesta secao"
- NUNCA omita indicadores do Card no Painel (Secao 1.5) — se nao ha dados, exibir "—" na linha
- NUNCA ultrapasse 150 palavras no Resumo Executivo — brevidade e proposital
