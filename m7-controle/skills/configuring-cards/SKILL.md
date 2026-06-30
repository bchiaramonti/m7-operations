---
name: configuring-cards
description: >-
  G2.2-E1: Cria, valida, promove e edita Cards de Performance YAML conforme ESP-PERF-002.
  Um Card agrega KPIs, arvore de decomposicao, logica de analise e parametros de distribuicao
  para uma vertical do CRM, servindo como configuracao machine-readable do pipeline E2-E6.
  Use when the user wants to create a new performance card, validate an existing card,
  promote a card from draft to active, or edit card KPIs/logic.

  <example>
  Context: Usuario quer criar um Card para a vertical de Investimentos
  user: "Cria um Card de Performance N1 para Investimentos"
  assistant: Inicia entrevista guiada coletando KPIs, arvore, logica de analise e gera YAML
  </example>

  <example>
  Context: Usuario quer validar um Card existente
  user: "Valida o card_inv_n1_001"
  assistant: Le o YAML, executa 12 regras de validacao da ESP-PERF-002 e gera relatorio
  </example>

  <example>
  Context: Usuario quer ativar um Card draft
  user: "Promove o card_inv_n1_001 para active"
  assistant: Executa validacao completa e, se sem issues criticos, promove status para active
  </example>
user-invocable: false
---

# Configuring Cards — Cards de Performance (E1)

> "O Card e a planta baixa do pipeline. Sem Card, nao ha automacao."

Esta skill cria, valida, promove e edita Cards de Performance conforme a especificacao ESP-PERF-002. Um Card e um artefato YAML que agrega KPIs da Biblioteca de Indicadores em um framework de analise integrado para uma vertical, servindo como input machine-readable para o pipeline automatizado E2-E6.

## Dependencias Internas

- [references/esp-perf-002-resumo.md](references/esp-perf-002-resumo.md) — Regras de validacao, aditividade, ciclo de vida e schema
- [references/naming-conventions.md](references/naming-conventions.md) — Taxonomia de IDs, codigos, verticais e niveis
- [templates/card-template.yaml](templates/card-template.yaml) — Template YAML com todos os campos
- [templates/card-validation-report.tmpl.md](templates/card-validation-report.tmpl.md) — Template do relatorio de validacao
- Agent `analyst` — Executor (invocado automaticamente)

> **Resolucao de caminhos**: Cards ficam em `cards/{VERT}/` e a Biblioteca de Indicadores em `indicators/` no repositorio do usuario. Localizar via `Glob('**/cards/{VERT}/*.yaml')` e `Glob('**/indicators/_index.yaml')`. O `_schema_card.yaml` fica em `cards/`.

## Pre-requisitos (Entry Criteria)

- Biblioteca de Indicadores da vertical populada com pelo menos os KPIs principais
- `_schema_card.yaml` disponivel no repositorio do usuario (em `cards/`)
- Para Modo 2/3/4: Card YAML existente no caminho esperado

## Modos de Operacao

Esta skill opera em 4 modos, selecionado conforme o intent do usuario:

| Modo | Trigger | Output |
|------|---------|--------|
| **1. Criar** | "cria card", "novo card", "configura card" | Card YAML em `cards/{VERT}/{id}.yaml` |
| **2. Validar** | "valida card", "verifica card" | Relatorio em `output/card-validation-{id}.md` |
| **3. Promover** | "promove card", "ativa card", "arquiva card" | Card YAML atualizado (status + updated_at) |
| **4. Editar** | "edita card", "adiciona KPI", "ajusta arvore" | Card YAML atualizado (version + updated_at) |

---

## Modo 1 — Criar Novo Card (Entrevista Guiada)

### Passo 1: Coletar Metadata

Perguntar ao usuario:
- **Vertical**: Investimentos, Credito, Universo, Seguros & Consorcios
- **Nivel**: N1 (Escritorio), N2 (Equipe), N3 (Squad), N4 (Assessor)
- **Subnivel** (opcional): B2B, B2C, SQUAD01...
- **Nome legivel**, descricao, owner

Gerar automaticamente ID e codigo conforme [naming-conventions.md](references/naming-conventions.md).

### Passo 2: Selecionar KPIs (kpi_references)

1. Listar indicadores disponiveis na Biblioteca para a vertical (`Glob('**/indicators/{dominio}/*.yaml')`)
2. Filtrar por status `validated` ou `promoted_to_gold`
3. Para cada KPI selecionado, definir:
   - `papel`: kpi_principal | ppi | ppi_segunda_ordem | contexto
   - `tipo_realizacao`: aditivo | nao_aditivo | parcialmente_aditivo
   - `criterio_desvio_critico`: condicao de alerta (ex: `pct_atingimento < 0.90`)
   - `quebras_obrigatorias`: dimensoes de drill-down [equipe, squad, assessor]
   - `correlacionado_com`: KPIs correlacionados (tipo: direta | inversa | contexto)
   - `regras_meta`: regras de aditividade entre niveis

**REGRA CRITICA de aditividade**: Consultar [esp-perf-002-resumo.md](references/esp-perf-002-resumo.md) Secao Aditividade antes de classificar qualquer KPI.

### Passo 3: Construir Arvore de Indicadores

Para cada KPI principal:
1. Definir `formula_conceitual` (ex: CapLiq = Cap Novas + Cap Base - Resgates)
2. Listar `componentes` com descricao
3. Para cada componente, identificar `influenciadores_diretos`:
   - `indicator_id` (da Biblioteca, se disponivel)
   - `tipo`: KPI | PPI | PPI_segunda_ordem | externo
   - `status`: disponivel | a_mapear | externo
4. **Profundidade maxima**: 2 niveis abaixo do KPI principal

### Passo 4: Definir Logica de Analise

1. Agrupar KPIs em `kpis_analisar_juntos` com `racional` e `sequencia_analise` (min 3 passos)
2. Definir `kpis_analisar_separados` para KPIs independentes
3. Definir `kpis_analisar_como_contexto` (consultados condicionalmente)
4. Definir `profundidade_maxima_arvore` (tipicamente 3)
5. Incluir `nota_aditividade_parcial` se aplicavel

**Cada passo da sequencia_analise deve ter**: `step`, `acao`, `pergunta_chave`.

### Passo 4.5: Definir `metas_ppi` (PPIs de funil)

O bloco `metas_ppi:` no top-level do Card declara metas dos PPIs de funil que recebem semaforo (regra a — verde >=100% / amarelo 70-99% / vermelho <70%, com cap 200% para `direction: menor_melhor`). Padrao consolidado em 2026-05-04 (Cons + Seg WL):

**Estrutura por PPI (vertical-level + N2 opcional):**

```yaml
metas_ppi:
  <indicator_id>:
    qty: <int>          # N1 = SUM dos especialistas (ou unico valor se KPIs iguais)
    volume: <int>       # opcional, idem
    ticket_medio: <int> # opcional, idem
    direction: maior_melhor | menor_melhor
    por_especialista:   # OPCIONAL — usar quando KPIs N2 divergem
      "<Especialista 1>":
        qty: <int>
        volume: <int>
        ticket_medio: <int>
      "<Especialista 2>":
        qty: <int>
        ...
    nota: >
      Origem dos numeros (manual/banco), formula de derivacao quando aplicavel,
      e migration path se for fix temporario.
```

**Quando usar `por_especialista`:**
- Especialistas com KPIs (Receita/Volume) iguais (ex: Cons Douglas/Tereza com 50/50 do escritorio): NAO precisa, valor unico no top-level basta.
- Especialistas com KPIs divergentes (ex: Seg WL Claudia vs Tarcisio com squads diferentes): OBRIGATORIO `por_especialista` para que o consolidating-wbr (E6 Fase 4.5.b) popule `n2.{esp}.meta` com a meta individual.

**Padrao especifico — `oportunidades_estagnadas_funil_*`:**

Este PPI sofreu mudanca estrutural de semaforo (qty -> % das ativas). Estrutura canonica:

```yaml
oportunidades_estagnadas_funil_*:
  qty: <int>                  # contextual N1 (sem semaforo proprio; referencia P50 baseline)
  pct_ativas_max: <int>       # meta com semaforo (estagnadas/ativas x 100, em pct 0-100)
  direction: menor_melhor
  nota: >
    Composicao:
      - Qtd: contextual (sem semaforo)
      - % das ativas: COM meta (pct_ativas_max) e semaforo (regra a, cap 200%)
      - Volume estagnado: sub-label (sem meta)
      - Media de dias: sub-label (sem meta)
```

O `consolidating-wbr` (E6 Fase 4.5.a) deriva automaticamente `oportunidades_estagnadas_funil_*_pct_ativas` no canonical JSON, com `realizado = qty_estagnadas / qty_ativas x 100` e `meta = pct_ativas_max`. Nao e preciso script Python adicional na coleta (E2) — derivacao vive no consolidate.

**Metodologia de derivacao top-down (Little's Law) para metas de funil:**

Quando uma vertical tiver Meta Receita + Meta Volume + Meta Taxa Conversao + Meta qty WON disponiveis (do banco ou manual), os PPIs de funil podem ser derivados matematicamente:

- `opps_fechadas_mes = qty_won / c`
- `T_ciclo_meses = T_ciclo_dias / 30.4375`
- `opps_ativas_medio = opps_fechadas_mes x T_ciclo_meses` (Little's Law)
- `vol_opps_ativas = opps_ativas_medio x ticket_pipeline_medio` (ticket_pipeline da baseline)
- `opps_criadas_mes = opps_fechadas_mes` (regime estacionario)
- `pct_ativas_max` = decisao de gestao informada por baseline P75/P90 (estagnadas/ativas)

Referencia: `02-Controle/_estudo-metas-ppi/modelo-reverso-funil.md` (estudo de Maio/2026).

**Inputs externos atuais (FIX TEMPORARIO):**

Algumas metas vem de fontes manuais enquanto colunas no banco nao existem. Documentar **sempre** em `nota:` do PPI:
- O que e (manual/Excel/etc.)
- Onde virá no banco quando coluna for criada
- Tracking em `_estudo-metas-ppi/TODO-MIGRACAO.md`

**Como as metas chegam ao pipeline (v7.0.0 — 2026-06-29):**

A partir da v7.0.0, o mecanismo de opt-in via `fonte:` foi eliminado. O script `resolve_metas.py` roda automaticamente ao final do E2 (Fase 3.5) e produz `dados/metas-resolvidas.json` — unico SoT de metas para todo o ciclo (E3, E4, E5, E6). O analyst le esse arquivo; o Card YAML serve apenas como fallback offline.

```yaml
metas_ppi:
  oportunidades_ativas_funil_seg_wl:
    qty: 7              # fallback offline (SoT: metas-resolvidas.json via vw_ciclo_metas_ppi)
    volume: 317558      # fallback offline
    direction: maior_melhor
    por_especialista:                 # fallback offline N2
      "Claudia Moraes": { qty: 3, volume: 139129 }
      "Tarcisio Catunda": { qty: 4, volume: 178429 }
```

Regras para o bloco `metas_ppi:`:
- **NAO declarar `fonte:`** — a chave foi eliminada; `resolve_metas.py` cobre todos os indicadores por regra.
- Os valores numericos (qty, volume, por_especialista) **devem ser mantidos** como snapshot offline: se o ClickHouse estiver indisponivel, o `resolve_metas.py` grava `offline_fallback=true` e o analyst usa o Card.
- Atualizar os valores snapshot sempre que a meta mudar na tabela (para evitar desvio muito grande no fallback).
- `pct_ativas_max` e `direction` continuam validos — sao lidos pelo `resolve_metas.py` e copiados para o JSON com `source: card_fixo`.
- Cobertura da tabela: 7 PPIs de funil (Cons/Seg) + receitas PJ2. Receita/Volume/Qty/Ticket MENSAIS de Cons/Seg seguem na tabela universal `dashboard_componente_universal` (fonte distinta).

### Passo 5: Configurar Distribuicao

- Destinatarios: cargo, escopo de niveis visiveis, foco
- Formato: WBR | MBR | dashboard | custom
- Frequencia: diaria | semanal | quinzenal | mensal
- Canal: email | slack | sharepoint | misto
- Conteudo obrigatorio (ex: "Semaforo geral", "Desvios criticos com causa-raiz")

### Passo 6: Gerar e Salvar

1. Preencher [card-template.yaml](templates/card-template.yaml) com os dados coletados
2. Configurar `parametros_execucao` (pipeline de 7 passos fixo — ver template)
3. Salvar em `cards/{VERT}/{id}.yaml` com status `draft`
4. Executar validacao (Modo 2) como pos-processamento

---

## Modo 2 — Validar Card Existente

1. Ler Card YAML
2. Validar contra `_schema_card.yaml` (campos obrigatorios, tipos)
3. Executar as **12 regras de validacao** detalhadas em [esp-perf-002-resumo.md](references/esp-perf-002-resumo.md)
4. Gerar relatorio seguindo [card-validation-report.tmpl.md](templates/card-validation-report.tmpl.md)
5. Salvar em `output/card-validation-{id}.md`

**Classificacao de issues**: CRITICO (bloqueia ativacao) | ATENCAO (nao bloqueia) | OK

---

## Modo 3 — Promover Status

Transicoes validas:
- `draft` → `active`: Requer validacao completa (Modo 2) sem issues CRITICO
- `active` → `archived`: Requer motivo registrado (substituido ou area desativada)

1. Verificar transicao valida
2. Se `draft → active`: executar Modo 2 como pre-requisito
3. Atualizar `status` e `updated_at`
4. Salvar YAML

---

## Modo 4 — Editar Card Existente

1. Ler Card YAML
2. Aplicar edicoes solicitadas
3. Incrementar version:
   - **MINOR**: adicao/remocao de KPI
   - **PATCH**: ajuste de parametro, descricao, logica
4. Executar validacao (Modo 2) como pos-processamento
5. Salvar com `updated_at` atualizado

---

## Exit Criteria

- [ ] Card YAML gerado/atualizado em `cards/{VERT}/{id}.yaml`
- [ ] Validacao completa executada sem issues CRITICO (para Modos 1, 3, 4)
- [ ] Status adequado: `draft` se incompleto, `active` se pronto para pipeline
- [ ] ID e codigo seguem taxonomia (ver [naming-conventions.md](references/naming-conventions.md))
- [ ] Correlacoes bidirecionais (se A declara B, B deve declarar A)
- [ ] sequencia_analise com minimo 3 passos por grupo

## Anti-Patterns

- NUNCA redefina dados tecnicos de indicadores — o Card apenas referencia por `indicator_id`
- NUNCA some percentuais entre assessores — percentuais parcialmente aditivos devem ser recalculados
- NUNCA permita `a_mapear` em Cards `active` — sinalize como lacuna para escalar a TI
- NUNCA crie arvore com mais de 2 niveis de profundidade abaixo do KPI principal
- NUNCA pule a validacao ao criar ou editar — Modo 2 e pos-processamento obrigatorio
- NUNCA delete Cards — archive com motivo para rastreabilidade

---

## Campos opcionais para integracao com m7-ritual-gestao (preparing-materials)

A skill `m7-ritual-gestao:preparing-materials` (G2.3-E2) consome campos
**adicionais** sob `apresentacao.*` e em `kpi_references[].matrix_views[].*`.
Todos sao opcionais — ausentes = comportamento legado. Ver schema completo
em [m7-ritual-gestao/skills/preparing-materials/references/card-apresentacao-schema.md](../../../../m7-ritual-gestao/skills/preparing-materials/references/card-apresentacao-schema.md).

### `apresentacao.*` (lido pelo build_deck.py)

```yaml
apresentacao:
  responsaveis:               # squad whitelist por especialista (zero-fill no ranking)
    - nome: "Douglas Silva"
      squad: ["Amanda Amarante", "Pedro Ramos", ...]
  overrides_ritual:           # override realizado/meta de N1/N2/N5 do ciclo
    ciclo: "..."              # bate com wbr.metadata.ciclo
    indicadores: { ... }      # inclui n5_by_esp para sobrepor dados_n5
  projecao_proximo_mes:       # metas M+1 quando WBR data JSON nao trouxer
  projection_overrides:       # projecoes recalculadas pos-override (metodo "a-fix")
  suppress_in_ritual:         # filter keywords pra Slide 12 (anomalias/destaques/recomendacoes stale)
  destaques_positivos_custom: # destaques sob medida prepended ao Slide 12 Sinais Positivos
  anomalias_custom:           # anomalias sob medida prepended ao Slide 12 Top Riscos
  recomendacoes_custom:       # recomendacoes sob medida prepended ao Slide 12 Encerramento (apenas prioridade=alta)
  pa_manual_append:           # task IDs ClickUp anexadas manualmente ao Slide 5
```

### `metadata.*` (alem do schema ESP-PERF-002 padrao)

```yaml
metadata:
  total_label: "M7 Total"     # label da coluna Total na Matriz (substitui "{nivel} Total")
  responsaveis_n2: [ ... ]    # fallback de esp_list para o deck
  assessor_aliases: { ... }   # dedupe manual (lookup case-insensitive via slugify)
  responsavel_externo_aliases: { ... }  # expansao multi-owner Slide 5
```

### `kpi_references[].matrix_views[].*` extensao

```yaml
matrix_views:
  - label: ...
    compute_meta: "..."        # formula da meta quando view usa compute (ex: meta_volume / meta_qty)
    n2_compute_meta: "..."     # idem N2
    sem_esp_ratio:             # derivacao Sem Esp para pct cross-indicator
      numerator: { indicator, n1_path, n2_path }
      denominator: { indicator, n1_path, n2_path }
      multiplier: 100
```

### Quando usar

- **Squad whitelist:** sempre que a vertical tiver squad oficial conhecido — habilita filtragem outsiders, zero-fill, cobertura correta.
- **assessor_aliases / responsavel_externo_aliases:** sempre que JSON tiver variantes de nome (acentos, abreviacoes, typos) ou multi-owners em custom fields.
- **overrides_ritual + projection_overrides:** apenas em ciclos com bug conhecido na fonte (ex: bridge SQL falhando). Remover apos correcao upstream para nao mascarar regressao.
- **suppress_in_ritual + custom destaques/anomalias/recomendacoes:** quando WBR populou itens stale relativos ao override OU quando usuario quer adicionar item especifico ao Slide 12 (ex: recomendacao de prospeccao da vertical no Encerramento).
- **pa_manual_append:** quando E4 nao classifica tasks com aging > cutoff mas o gestor quer mostrar no ritual.
- **sem_esp_ratio:** sempre que indicador for `pct` derivado de cross-indicator (ex: Estagnadas % das Ativas).
- **compute_meta / n2_compute_meta:** sempre que matrix_view usar `compute` (Ticket Médio etc).

### Princípios universais aplicados pelo build_deck.py

1. **Sem Especialista universal cinza** — esp="Sem Especialista" SEMPRE retorna meta=None e cell=mute, mesmo se override declarar meta.
2. **Dedupe por slug** — squad members "Vinícius"/"Vinicius" e "Waleska "/"Waleska" viram 1 entry no set via slugify.
3. **Callout vermelhos dedup parent_indicator** — Slide 3 callout conta indicadores vermelhos agrupados por `parent_indicator`, nao por matrix_view (Estagnadas qty + % ativas = 1 vermelho, nao 2).
