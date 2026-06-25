# Schema completo do `Card.apresentacao` — consumido por build_deck.py

Ultima atualizacao: 2026-05-06 (rodada 7.9 prepare-ritual Consorcios S19 — `recomendacoes_custom` adicionado).

Esta referencia documenta TODOS os campos sob `apresentacao` que o `build_deck.py` consome ao gerar o deck HTML do ritual. Cada chave e **opcional** — quando ausente, o script aplica comportamento legado (backward compat). N-parametrico: nenhum campo e hardcoded para vertical especifica.

---

## Visao geral

```yaml
apresentacao:
  responsaveis:               # squad whitelist + nome canonico do esp
    - nome: "Douglas Silva"
      squad: ["Amanda Amarante", ...]
  overrides_ritual:           # overrides de N1/N2/N5 do ciclo (correcao bridge etc)
    ciclo: "2026-05-04"
    competencia: "2026-05"
    indicadores:
      receita_consorcio_mensal:
        n1: { realizado, meta }
        n2: { "Esp": { realizado, meta } }
        n5_by_esp: { "Esp": [ { assessor, realizado } ] }
  projecao_proximo_mes:       # metas M+1 quando WBR data JSON nao trouxer
    competencia: "2026-06"
    indicadores: { ... }
  projection_overrides:       # projecoes recalculadas pos-override (metodo "a-fix")
    ciclo: "2026-05-04"
    metodo: "a-fix"
    indicadores: { ... }
  suppress_in_ritual:         # filtro keywords pra Slide 12 (Top Riscos / Sinais)
    anomalias: [ ... ]
    destaques_positivos: [ ... ]
    recomendacoes: [ ... ]
  destaques_positivos_custom: # destaques sob medida prepended ao Slide 12
    - { titulo, texto }
  anomalias_custom:           # anomalias sob medida prepended ao Slide 12
    - { descricao, acao, severidade }
  recomendacoes_custom:       # recomendacoes sob medida prepended ao Slide 12 Encerramento
    - { texto, owner, prazo, prioridade }
  pa_manual_append:           # task IDs ClickUp a anexar manualmente ao Slide 5
    - "86ah6d1f2"
```

E em `metadata`:

```yaml
metadata:
  total_label: "M7 Total"     # label da coluna Total na Matriz/Dashboard
  responsaveis_n2: [ ... ]    # fallback de esp_list quando WBR data JSON nao trouxer
  assessor_aliases:           # dedupe manual (case-insensitive via slugify)
    "Pedro Araújo": "Pedro Ramos"
  responsavel_externo_aliases: # expansao de owners curtos no Slide 5
    "Douglas e Tereza": "Douglas Silva + Tereza Bernardo"
```

E em `kpi_references[].matrix_views[]`:

```yaml
matrix_views:
  - label: ...
    compute_meta: "..."        # formula da meta quando view usa compute (ratio)
    n2_compute_meta: "..."     # idem N2
    sem_esp_ratio:             # derivacao Sem Esp para pct cross-indicator
      numerator: { indicator, n1_path, n2_path }
      denominator: { indicator, n1_path, n2_path }
      multiplier: 100
```

---

## `apresentacao.responsaveis[]` — Squad whitelist

Define o squad oficial de cada especialista. Consumido em multiplos pontos:

- `_aggregate_assessor_volumes(scope="squad")` filtra rows N5 cujo `assessor` esta na whitelist (slugify match) — outsiders sao excluidos do ranking principal.
- `_aggregate_assessor_volumes(scope="outside_squad")` retorna assessores N5 do MESMO esp que NAO estao na whitelist (Ronaldo Dantas vinculado ao Douglas mas nao oficial). Substitui semantica antiga "outside" (esps fantasmas N2).
- `_esp_squad_size(esp, data)` retorna `len(squad)` para cobertura cards.
- `_esp_summary_cards` Card 2 (Cobertura): conta apenas membros whitelist com deal ativo; dedupe via slugify.
- `_esp_riscos` Concentracao + Cobertura B: outsiders nao contam (dedupe via slugify para evitar variantes acentos/espacos).
- Zero-fill: assessores oficiais sem deal aparecem com qty=0 no ranking.

```yaml
apresentacao:
  responsaveis:
    - nome: "Douglas Silva"
      squad:
        - "Amanda Amarante"
        - "David Oliveira Leite"
        - "Karyne Beuttenmüller"
        # ... 12 nomes para Douglas
    - nome: "Tereza Bernardo"
      squad:
        - "Gabriel Santos"
        # ... 10 nomes para Tereza
```

**Quando aplicar:** sempre que a vertical tiver squad oficial conhecido. Sem este bloco, o script aceita qualquer assessor com deal vinculado ao esp (legado).

---

## `apresentacao.overrides_ritual` — Override realizado/meta + N5

Sobrepoe valores de N1, N2 e N5 de indicadores especificos para o ciclo declarado. Aplicado pelo `_apply_card_overrides()` (em `data["wbr"]["indicadores"]`) e `_apply_n5_overrides()` (em `dados_n5`).

```yaml
apresentacao:
  overrides_ritual:
    ciclo: "2026-05-04"          # bate com wbr.metadata.ciclo (senao no-op)
    competencia: "2026-05"       # YYYY-MM filtrado em N5 override
    indicadores:
      receita_consorcio_mensal:
        n1:
          realizado: 109859.38
          meta: 201748.00
        n2:
          "Douglas Silva":
            realizado: 32686.62
            meta: 100874.00
          "Tereza Bernardo":
            realizado: 22946.60
            meta: 100874.00
          "Sem Especialista":
            realizado: 54226.16
            meta: 0
        n5_by_esp:                # FIX rodada 7.5 — override N5 receita
          "Douglas Silva":
            - assessor: "Douglas Silva"  # esp_direct (comercial = esp)
              realizado: 16793.59
            - assessor: "Karyne Beuttenmüller"
              realizado: 1312.02
            # ...
          "Tereza Bernardo":
            - assessor: "Claudio Vasconcelos"
              realizado: 3805.80
            # ...
```

**Quando aplicar:** quando view SQL upstream tem bug conhecido (ex: bridge `especialista` falha em consorcio_receita). Override e escopado por ciclo — apos correcao no banco, **remover bloco para nao mascarar regressao**.

**Comportamento do script:**
- N1: `realizado`/`meta` set em ambos `realizado_mtd`+`realizado` e `meta_mes_corrente`+`meta`+`meta_mes` (cobre qualquer matrix_view).
- N2: idem por especialista. Se Sem Especialista declarado, vira valor explicito (cell ainda renderizada como `mute` por regra universal).
- N5_by_esp: REMOVE rows N5 do mes override de `dados_n5.indicadores[].data` e ADICIONA novas baseadas nos entries declarados. Outros niveis e meses preservados.

---

## `apresentacao.projecao_proximo_mes` — Metas M+1

Declara metas do mes seguinte quando o WBR data JSON nao trouxer `meta_mes_seguinte` per indicador. Lido pelo render para classificar projecao M+1.

```yaml
apresentacao:
  projecao_proximo_mes:
    competencia: "2026-06"
    indicadores:
      receita_consorcio_mensal:
        n1:
          meta: 243341.00
        n2:
          "Douglas Silva":
            meta: 121670.50
          "Tereza Bernardo":
            meta: 121670.50
```

---

## `apresentacao.projection_overrides` — Projecoes recalculadas

Sobrepoe `projecao_mes_corrente`, `projecao_mes_seguinte` e classificacoes do indicador quando os valores do WBR data JSON ficaram stale (apos overrides_ritual). Mesmas chaves que `_esp_proj_bars` ja le.

```yaml
apresentacao:
  projection_overrides:
    ciclo: "2026-05-04"
    metodo: "a-fix"     # versionamento — ver projecting-results/SKILL.md
    indicadores:
      receita_consorcio_mensal:
        n1:
          projecao_mes_corrente: 153703
          projecao_mes_seguinte: 113153
          classificacao_mes_corrente: "Possivel"
          classificacao_mes_seguinte: "Improvavel"
        n2:
          "Douglas Silva":
            projecao_mes_corrente: 62759
            projecao_mes_seguinte: 59552
            classificacao_mes_corrente: "Improvavel"
            classificacao_mes_seguinte: "Improvavel"
```

**Importante:** o script set `projecao_maio_base` e `projecao_junho_base` (alias historico) alem de `projecao_mes_corrente/seguinte` para compatibilidade com helpers que ainda usam nomes antigos.

---

## `apresentacao.suppress_in_ritual` — Filtro Slide 12

Listas de substrings (case-insensitive) que filtram itens do Top Riscos / Sinais Positivos / Encerramento ANTES do slice [:3]. Util quando WBR populou anomalias/destaques com numeros stale relativos ao override.

```yaml
apresentacao:
  suppress_in_ritual:
    anomalias:
      - "Bridge ASSIGNED_BY_ID"
      - "mega-prospects Douglas"
    destaques_positivos:
      - "99% no D+4"
      - "ETL diaria habilitou"
    recomendacoes:
      - "Bridge ASSIGNED"
```

**Match:** substring `in text.lower()`. Multiple keywords = OR.

---

## `apresentacao.destaques_positivos_custom` + `anomalias_custom` + `recomendacoes_custom` — Custom prepend Slide 12

Os 3 campos prepended ANTES dos respectivos campos do `wbr.*` na consolidacao Slide 12 (Top Riscos / Sinais Positivos / Encerramento). Mesma estrutura de cada lista do WBR.

```yaml
apresentacao:
  destaques_positivos_custom:        # vai pra "Sinais Positivos" Slide 12
    - titulo: "Metas operacionais completas"
      texto: "Pos-correcao bridge: agora vemos R$ 201,7K Maio e R$ 243,3K Junho..."
  anomalias_custom:                   # vai pra "Top 3 Riscos" Slide 12
    - descricao: "Falta de novas oportunidades criadas pode se propagar ate o proximo ciclo"
      acao: "Garantir cadencia de prospeccao para evitar pipeline gap futuro"
      severidade: alta
  recomendacoes_custom:               # vai pra "Encerramento next-cards" Slide 12
    - texto: "Plano de prospeccao da vertical — meta semanal por especialista + perfil + CTA"
      owner: "Joel Freitas"
      prazo: "2026-05-13"
      prioridade: "alta"              # IMPORTANTE: so prioridade=alta entra no Encerramento
```

Funcionam em conjunto com `suppress_in_ritual` — usuario pode suprimir um item tecnico stale e adicionar outro mais relevante para o ritual.

**Comportamento do script:**
- `destaques_positivos_custom` → prepended a `wbr.destaques_positivos`, depois `suppress_in_ritual.destaques_positivos` filter, depois slice [:3].
- `anomalias_custom` → prepended a `wbr.anomalias`, depois `suppress_in_ritual.anomalias` filter, depois slice [:3].
- `recomendacoes_custom` → prepended a `wbr.recomendacoes` (filtradas por `prioridade=alta`), depois `suppress_in_ritual.recomendacoes` filter, depois slice [:3]. **Apenas itens com `prioridade: "alta"` entram** (mesma regra de wbr.recomendacoes).

---

## `apresentacao.pa_manual_append` — Tasks manuais Slide 5

Lista de task IDs ClickUp anexadas manualmente ao final do Slide 5, apos os 3 buckets do WBR (criticas, atrasadas, em_dia_priorizadas). Util quando m7-controle E4 nao classificou tasks com aging > 7d cutoff mas o gestor quer expor no ritual.

```yaml
apresentacao:
  pa_manual_append:
    - "86ah6d1f2"  # Finalizar Kit Boas-Vindas
```

**Comportamento do script:**
- Resolve cada ID via `clickup_tasks` lookup.
- Renderiza com `pill-good` (verde "EM DIA").
- Owner via `responsavel_externo` (com expansao de aliases via `metadata.responsavel_externo_aliases`).
- `due_date` aceita 3 formatos: ms epoch (int/str) com offset +1h normalizado, OU string YYYY-MM-DD direta.
- Causa-raiz via `_lookup_causa_raiz` por `indicador_impactado` da task.
- Limite total Slide 5 = 14 rows (12 buckets + 2 manual).

---

## `metadata.total_label` — Label coluna Total

Substitui o default `"{nivel} Total"` (ex: "N3 Total") por label generico ("M7 Total", "Empresa Total", etc).

```yaml
metadata:
  total_label: "M7 Total"
```

---

## `metadata.responsaveis_n2` — Fallback esp_list

Lista canonica de especialistas, lida quando `wbr.metadata.responsaveis_n2` esta ausente.

```yaml
metadata:
  responsaveis_n2:
    - "Douglas Silva"
    - "Tereza Bernardo"
```

---

## `metadata.assessor_aliases` — Dedupe e canonicalizacao

Mapping `nome_raw → nome_canonico` aplicado pelo `_resolve_assessor_alias()`. **Lookup case-insensitive via slugify** — entrada "LUIS EDUARDO", "Luís Eduardo" e "luis eduardo" todas resolvem para a mesma chave normalizada.

```yaml
metadata:
  assessor_aliases:
    "Káryne Bênutten": "Karyne Beuttenmüller"
    "Luís Eduardo": "Luiz Eduardo"
    "Romulo": "Rômulo Rodrigues"
    "Pedro Araújo": "Pedro Ramos"
    "David Oliveira": "David Oliveira Leite"
    "Gustav0 Melo": "Gustavo Melo"   # typo zero-por-O
```

---

## `metadata.responsavel_externo_aliases` — Expansao multi-owner Slide 5

Mapping de valores literais do custom field `responsavel_externo` para expansao em multiplos nomes canonicos. Aplicado em `render_pa_slides` antes de splittar em separadores (`,` / `&` / ` e `).

```yaml
metadata:
  responsavel_externo_aliases:
    "Douglas e Tereza": "Douglas Silva + Tereza Bernardo"
    "Douglas & Tereza": "Douglas Silva + Tereza Bernardo"
```

---

## `kpi_references[].matrix_views[].compute_meta` / `n2_compute_meta`

Quando matrix view usa `compute` (ratio), declara formula da meta correspondente. Avaliado via `_eval_compute()` contra entry do indicador.

```yaml
- label: "Ticket Medio Pipeline"
  unidade: BRL
  compute: "volume_total / realizado_qty"
  compute_meta: "meta_volume / meta_qty"
  n2_compute: "volume / qty"
  n2_compute_meta: "meta_volume / meta_qty"
```

Sem este campo, ratio views ficam sem meta (so realizado).

---

## `kpi_references[].matrix_views[].sem_esp_ratio`

Declara derivacao Sem Especialista para indicadores `pct` ou ratio cross-indicator. Numerator e denominator podem apontar para indicadores DIFERENTES (ex: estagnadas qtd / ativas qtd).

```yaml
- label: "Oport. Estagnadas (% ativas)"
  unidade: pct
  derived_indicator_id: oportunidades_estagnadas_funil_pct_ativas
  sem_esp_ratio:
    numerator:
      indicator: oportunidades_estagnadas_funil_pct_ativas
      n1_path: componentes.qtd_estagnados
      n2_path: qtd_estagnados
    denominator:
      indicator: oportunidades_ativas_funil
      n1_path: realizado_qty
      n2_path: qty
    multiplier: 100
```

**Comportamento:** quando `e is None` para esp=Sem Especialista e `mr.sem_esp_ratio` declarado, o script:
1. Busca N1 do `numerator.indicator.n1_path` e SUM dos esp_list em `n2_path`.
2. Sem Esp num = N1 - SUM.
3. Idem para denominator.
4. Resultado = (num / den) * multiplier.
5. Render como cell `mute` (Sem Esp universal cinza).

---

## Regras universais Sem Especialista

- `_resolve_n2(esp="Sem Especialista")` SEMPRE retorna `meta=None` e `status=None`, mesmo se override declarar meta.
- `_matriz_row_v2.cell_for(inherit_key="Sem Especialista")` SEMPRE retorna `cell mute` (cinza), sem semaforo, sem meta.
- Sem Esp pode ter realizado derivado (via `n2_compute` em compute, ou `sem_esp_ratio` em pct, ou aditivo via N1-SUM).

---

## Ordem de aplicacao no script

```
load_data()
  └── _apply_card_overrides(data)        # N1/N2 + projection_overrides em data["wbr"]
      └── _apply_n5_overrides(card, dados_n5)  # N5 em dados_n5
render_*()
  └── _resolve_matrix_rows / _resolve_n1 / _resolve_n2
      └── le tudo overrides ja aplicados
render_pa_slides()
  └── responsavel_externo_aliases + pa_manual_append
render_consolidado_encerramento()
  └── anomalias_custom prepend + destaques_positivos_custom prepend +
      recomendacoes_custom prepend + suppress_in_ritual filter (3 listas)
```

---

## Exemplo completo de Card minimo com `apresentacao`

```yaml
metadata:
  total_label: "M7 Total"
  responsaveis_n2: ["Douglas Silva", "Tereza Bernardo"]
  assessor_aliases:
    "Pedro Araújo": "Pedro Ramos"
  responsavel_externo_aliases:
    "Douglas e Tereza": "Douglas Silva + Tereza Bernardo"

apresentacao:
  responsaveis:
    - nome: "Douglas Silva"
      squad: ["Amanda Amarante", "Pedro Ramos", ...]
    - nome: "Tereza Bernardo"
      squad: [...]
```

Esse minimo ja habilita: squad whitelist, dedupe por slug, scope outside_squad, expansao multi-owner.

Adicionar overrides_ritual, projection_overrides, suppress_in_ritual e custom destaques/anomalias quando o ciclo exigir.

---

## Extensao multi-canal (PJ2 v1.0+)

A partir do Card PJ2 N2 v1.0.0 (2026-05-08), o schema do Card aceita campos
opcionais para suportar verticais multi-canal (label_responsavel ≠ "especialista")
e os 3 modos de apresentacao (atual/fechamento/combinado). **Todos os campos abaixo
sao opcionais** — Cards N3 existentes nao precisam ser alterados.

### `metadata.label_responsavel` (NOVO)

Define qual o eixo de iteracao do bloco repetido do deck (o que era o "loop
por especialista" no template legado).

```yaml
metadata:
  label_responsavel: canal         # enum: especialista | canal | sub_bloco
```

- `especialista` (default, omissivel): loop sobre `responsaveis_n2`, mesma logica atual.
- `canal`: loop sobre `apresentacao.responsaveis[].id` (Inv/Cred/Outros M7).
- `sub_bloco`: loop sobre `apresentacao.responsaveis[X].sub_blocos.keys()` (B2B/B2C/Outros).

### `metadata.verticais` (NOVO)

Lista de verticais que o Card cobre. Para PJ2: `[consorcios, seguros]`.
Para Cards single-vertical, omitir ou usar `[vertical_code normalizado]`.

```yaml
metadata:
  verticais: [consorcios, seguros]
```

### `apresentacao.template` (NOVO)

Seleciona o template HTML do builder. Default `"default"` aponta para
`ritual.tmpl.html` (template legado N3). PJ2 aponta para
`ritual-pj2.tmpl.html` (template multi-vertical com slides Direto/Analise
Canal/Pipeline por vertical).

```yaml
apresentacao:
  template: pj2                    # enum: default | pj2
```

### `apresentacao.modo` (NOVO)

Define quais slides entram no deck. Default `auto` herda o comportamento
atual (1 ritual mes auto-inclui fechamento via `wbr.is_first_ritual_of_month`).

```yaml
apresentacao:
  modo: combinado                  # enum: atual | fechamento | combinado | auto
```

- `atual`: apenas slides do mes corrente (~13-15 slides PJ2 / ~7+3N slides N3).
- `fechamento`: apenas slides de fechamento do mes anterior (~7 slides).
- `combinado`: fechamento + atual + sub-capas (~21 slides PJ2).
- `auto`: deduz de `wbr.is_first_ritual_of_month` (legado preservado).

CLI override: `--modo {atual|fechamento|combinado|auto}` ganha precedencia
sobre Card.apresentacao.modo. Ordem: CLI > Card > auto.

### `apresentacao.hidden_in_squad_lists` (NOVO)

Lista plana de nomes (normalizados case-insensitive) que NAO aparecem em
listagens de squad nos slides Detalhado por Canal / Pareto / Pipeline.

```yaml
apresentacao:
  hidden_in_squad_lists:
    - "Francisco Vale"
    - "Davi Meirelles Leitão"
```

**Comportamento:** `filter_hidden()` e `get_squad_full_list()` consultam
essa lista. Cards N3 sem o campo: nada filtrado.

### `apresentacao.responsaveis[].id` (NOVO — obrigatorio p/ label canal)

Quando `metadata.label_responsavel == "canal"`, cada entrada de
`responsaveis[]` representa um canal (nao mais um especialista). O campo
`id` se torna obrigatorio (canal_id usado como chave em `por_canal` no
WBR, em `metas_canal`, em `derive_meta_canal`, etc.).

```yaml
apresentacao:
  responsaveis:
    - id: investimentos
      nome: Investimentos
      cargo: Canal comercial
      squad: [...]
    - id: credito
      nome: Credito
      cargo: Canal comercial
      squad: [...]
```

**Fallback retro-compat:** Cards sem `id` em responsaveis recebem heuristica
`_canal_id_from_nome()` (detecta "credito"/"investimento" no nome). Cards N3
com label_responsavel: especialista nao precisam de `id` (omitir).

### `apresentacao.responsaveis[].sub_blocos` (NOVO — obrigatorio p/ label sub_bloco)

Quando `metadata.label_responsavel == "sub_bloco"`, define sub-divisoes do
canal/especialista. Util para Cards N3 INV quebrando por equipe.

```yaml
apresentacao:
  responsaveis:
    - id: investimentos
      nome: Investimentos
      sub_blocos:
        B2B:
          equipes: [Alta Renda, Corporate]
          squad: [...]
        B2C:
          equipes: [Mesa, Private]
          squad: [...]
        Outros:
          equipes: [Outros, Sem equipe]
          squad: [...]
```

Quando `label_responsavel == "canal"`, sub_blocos pode existir como sub-
estrutura visual interna (sub-headers em Analise por Canal) sem alterar o
eixo principal de iteracao.

### `apresentacao.outros_m7` (NOVO — opcional p/ label canal)

Agrupa nomes que nao pertencem a squads comerciais oficiais (canal Outros
M7 no Pareto 5-bucket / agregado N1). Subdividido em 3 grupos.

```yaml
apresentacao:
  outros_m7:
    nota: "NAO tem bloco proprio de analise — apenas agregado nas matrizes/consolidado"
    especialistas: [Claudia Moraes, Douglas Silva, ...]
    coordenador: [Joel Freitas]
    outros: [Andrea Leite, ...]
```

Todos os 3 grupos sao tratados como canal_id="outros_m7" no `build_squad_index`.

### `apresentacao.metas_split` (NOVO)

Configura como meta_total e dividida por canal. Substitui o hardcode V13
de 28/35+7/35 por configuracao data-driven.

```yaml
apresentacao:
  metas_split:
    default_method: proporcional_squad     # default: usa squad sizes do Card
    overrides:
      receita_consorcio_mensal:
        method: fixed_ratio                # enum: proporcional_squad | fixed_ratio | absolute
        ratios:
          investimentos: 0.65
          credito: 0.20
          outros_m7: 0.15
      ticket_medio_consorcio_mensal:
        method: absolute
        values:
          investimentos: 850000
          credito: 1200000
```

**Metodos:**
- `proporcional_squad` (default): meta_canal = meta_total × len(squad_canal) / sum(squads). Outros M7 recebe None.
- `fixed_ratio`: aplica ratios literais ao meta_total. Soma deve ser ≤ 1.0.
- `absolute`: usa valores absolutos por canal, ignora meta_total.

Quando `card.metas_canal.{vert}.{ind_id}.{periodo_key}` esta declarado
explicitamente, ele tem precedencia sobre metas_split (ver `get_meta_explicit_canal`).

### `canal_taxonomia` (NOVO — top-level)

Declara a taxonomia de buckets para Pareto / agregados. Lido por
`render_analise_canal` e helpers de Pareto 5-bucket.

```yaml
canal_taxonomia:
  buckets_pareto_5: [investimentos, credito, especialistas, coordenador, outros]
  agregados_total_3: [investimentos, credito, outros_m7]
  rollup_bucket_para_agregado:
    investimentos: investimentos
    credito: credito
    especialistas: outros_m7
    coordenador: outros_m7
    outros: outros_m7
  de_para_canal_path: "02-Controle/_pj2-prep/pj2-mapping/de-para-canal.yaml"
```

### `kpi_references[].matrix_views[].column_axis` (NOVO)

Quando `column_axis == "canal"`, a Matriz substitui o loop sobre `_esp_list`
pelo loop sobre `column_order`. Util para Matriz PJ2 com colunas fixas
Outros M7 | Credito | Investimentos | Total.

```yaml
kpi_references:
  - indicator_id: receita_consorcio_mensal
    matrix_views:
      - label: "Receita Cons"
        column_axis: canal                       # enum: especialista | canal. Default: especialista
        column_order: [outros_m7, credito, investimentos]  # obrigatorio se column_axis=canal
```

Helpers de cell rendering (`_matriz_row_v2`, `cell_for`) ficam intactos —
so o eixo de iteracao das colunas muda.

---

## Exemplo Card multi-canal (PJ2 v1.0+)

```yaml
metadata:
  label_responsavel: canal
  verticais: [consorcios, seguros]
  responsaveis_n2: [Credito, Investimentos]    # fallback p/ esp_list

apresentacao:
  template: pj2
  modo: combinado
  responsaveis:
    - id: investimentos
      nome: Investimentos
      squad: [...]
    - id: credito
      nome: Credito
      squad: [...]
  outros_m7:
    especialistas: [Claudia Moraes, ...]
    coordenador: [Joel Freitas]
    outros: [Andrea Leite, ...]
  hidden_in_squad_lists: [Francisco Vale, ...]
  metas_split:
    default_method: proporcional_squad

canal_taxonomia:
  buckets_pareto_5: [investimentos, credito, especialistas, coordenador, outros]
  agregados_total_3: [investimentos, credito, outros_m7]

metas_canal:                                   # opcional — overrides explicitos
  consorcios:
    receita_consorcio_mensal:
      maio_2026: {investimentos: 111331, credito: 52500, outros_m7: 37917}
```
