# Changelog

Todas as mudancas notaveis neste plugin serao documentadas neste arquivo.

O formato segue [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/),
e este projeto adere ao [Semantic Versioning](https://semver.org/lang/pt-BR/).

## [6.5.0] - 2026-06-12

> **Minor release retrocompativel** — Religa as metas de PPI de funil ao SoT
> ClickHouse `m7Prata.ciclo_metas_ppi` (substitui o hardcode `metas_ppi:` dos
> Cards) e reestrutura o E6 em **2 passadas do analyst** para a injecao entrar
> coerente em todos os artefatos. Offline ou sem opt-in `fonte:` = NO-OP (fluxo
> legado intacto, sem regressao).

### Added

- **`scripts/inject_metas_ppi.py`** (E6 Fase 4.6) — injeta `meta`/`meta_volume`/`n2.{esp}.meta`
  do SoT da tabela no canonical e recalcula `pct_atingimento`/`gap`/`status` (regra `cor_from_pct`).
  Opt-in por indicador via `fonte: m7Prata.ciclo_metas_ppi` no Card. Escopo count/BRL
  (`oportunidades_ativas`/`criadas`/`sem_atividade`); ratio/days nao injetados (constantes
  com unidade inconsistente). Offline-safe (WARN + no-op), backup `.bak`, diff auditavel.
- **`scripts/compare_metas_card_vs_tabela.py`** — auditoria de paridade Card x tabela (read-only)
  por vertical/mes; rodar antes de declarar `fonte:` num Card.
- **Modelo de Execucao E6 em 2 passadas** (SKILL.md): Passada 1 analyst (canonical) → main thread
  roda `normalize_canonical` + `inject_metas_ppi` (Fase 4.6) → Passada 2 analyst (Estruturado/
  Narrativo do canonical injetado) → gate `validate-painel`.

### Changed

- **`scripts/validate-painel.py`** — `extract_card_metas` reconhece `fonte_n2:` e
  `validate_metas_ppi_sources` cobre tambem fontes `ciclo_metas_ppi` (alem da universal).
- **`agents/analyst.md`** — documenta os 2 modos do E6 (build-canonical | write-docs; na 2a
  passada o canonical e read-only para `indicadores.*`).
- **`commands/next.md` + `run-weekly.md`** — nota de que E6 roda em 2 passadas com inject no meio.
- **Dependencia externa:** `meta_resolver.py` vive na Biblioteca-de-Indicadores (pasta Desempenho,
  fora do repo), reutilizado via PYTHONPATH (mesmo padrao do `m7_extract_utils`).

### Notes

- **PJ2 nao religado** (canonical por canal; `build_deck_pj2` precisa ler o resolver direto) — pendente.
- Cards N3 (Cons v2.13.0, Seg WL v2.19.0, Seg RE v1.10.0) declaram `fonte:` nos PPIs count/BRL.

## [6.4.0] - 2026-05-06

> **Minor release retrocompativel** — Ativa `pipeline_conversion_extended_v2`
> em producao para Consorcios e Seguros (WL/RE), introduz `close_mode` automatico
> para 1o ritual do mes (snapshot duplo: mes anterior fechado + mes corrente),
> adiciona Fase 6.6 consolidacao N1 no projection-by-especialista.json e flag
> `criada_em_ritual_anterior` em E4 (acoes criadas no ultimo ritual).
>
> **Habilita** os tweaks de template C3, C7 e C8 do plano de ritual 2026-05-06
> (preparing-materials do m7-ritual-gestao consome os novos campos).

### Added

- **`pipeline_conversion_extended_v2` ATIVO** em `volume_consorcio_mensal.yaml` e
  `volume_seguros_mensal.yaml` (preferred: true). v1 vira fallback automatico
  com flag `v2_fallback_to_v1: true` quando inputs indisponiveis. Pre-requisitos
  atendidos: stage_metrics_vigentes YAMLs criados, scripts existentes,
  oportunidades_criadas com `extras.historico_3m`, data_competencia em Cons.
- **Indicadores YAML novos** para v2: `stage_metrics_vigentes.yaml` (Cons,
  PIPELINE_ID=238) e `stage_metrics_vigentes_seg.yaml` (Seg, PIPELINE_ID=156
  compartilhado WL+RE).
- **Cards bumpados** com v2 ativado: `card_con_n3_001.yaml` v2.9.0,
  `card_seg_wl_n3_001.yaml` v2.15.0, `card_seg_re_n3_001.yaml` v1.7.0.
- **Step 1.2 do `run-weekly`**: deteccao automatica de 1o ritual do mes via
  comparacao `mes(ciclo_anterior) < mes(ciclo_atual)`. Quando detectado,
  dispara coleta DUPLA: 1 ciclo `close_mode` para mes anterior fechado
  (`{vertical}/{YYYY-MM}-fechamento/`) + 1 ciclo normal do mes corrente.
  Persiste `is_first_ritual_of_month` e `close_mode` no header CICLO.md.
- **Fase 1.6 em `consolidating-wbr/SKILL.md`**: detecta `close_mode: true` e
  substitui secao "Projecoes" por "Fechamento do mes" (totais finais, top/bottom
  performers, licoes do mes). Marca projecoes como `is_retrospective: true`
  no canonical data JSON (template oculta visualmente).
- **Fase 6.6 em `projecting-results/SKILL.md`**: bloco `consolidado_n1` no
  `projection-by-especialista.json` agregando `volume_consolidada_mensal` e
  `receita_consolidada_mensal` da vertical inteira (regra de consolidacao
  configurada via `projection.consolidation` do YAML; default `sum`).
- **Fase 2.5 em `summarizing-actions/SKILL.md`**: flag `criada_em_ritual_anterior`
  em todas as tasks do JSON ClickUp, derivada de
  `[data_ultimo_ritual, data_ritual_atual)` lidos do CICLO.md.
- **TODO Gap 1 Seguros** em `volume_seguros_mensal.py`: filtro `parcela_comissao=1`
  preparado mas inativo ate coluna ser criada no schema
  `m7Prata.seguro_comissao_assessor_fuzzy`.

### Changed

- **`volume_seguros_mensal.yaml` updated_at: 2026-05-06**, methods reorganizado
  com v2 preferred + v1 fallback + run_rate_linear ultimate fallback.
- **`volume_consorcio_mensal.yaml`** removido bloco `activation_pending` de v2;
  v2 marcado preferred: true; v1 marcado preferred: false (fallback_for v2).
- **CICLO.md template** estendido com 4 novos campos no header:
  `is_first_ritual_of_month`, `close_mode`, `data_ultimo_ritual`,
  `mes_ciclo_anterior`.
- **Status do v2** em `projecting-results/SKILL.md`: de "DECLARADO MAS INATIVO"
  para "ATIVO desde 2026-05-06" com pre-requisitos checados.

### Compatibility

- 100% retrocompativel: ciclos antigos sem `is_first_ritual_of_month` no
  CICLO.md sao tratados como `false` (comportamento legado).
- Cards sem v2 ativado caem em v1 normalmente (preferred: true mantido).
- `projection-by-especialista.json` sem `consolidado_n1` sinaliza
  `consolidated_unavailable: true` ao consumidor (m7-ritual-gestao).

## [6.3.0] - 2026-05-06

> **Minor release retrocompativel** — Implementa option (b) do roadmap M+1
> Projection (decisao usuario 2026-05-05). Introduz `pipeline_conversion_extended_v2`
> (cycle-time-aware + selector dia 15) como `preferred` futuro, mantendo v1
> como fallback durante migracao gradual. Corrige formula `installment_amortization`
> para evitar double-count de lagging vs componente funil (resolve ISSUE #3).

### Added

- **Metodo `pipeline_conversion_extended_v2`** documentado em
  `projecting-results/SKILL.md` Fase 2 e em `references/projection-methodology.md`
  secao 5.2:
  - Cycle-time-aware: cada deal classificado em horizonte (M0, M+1, fora) baseado
    em `tempo_estimado_fechamento` + `stage_probability` vigentes.
  - Selector dia 15: antes do dia 15 usa medianas do mes anterior (estavel);
    a partir do dia 15 usa medianas do mes atual (vigente).
  - Output decomposto: `vol_lagging_competencia_M0/M+1`, `vol_componente_M0/M+1`,
    `vol_entradas_novas_M+1` — separacao explicita evita double-count.
- **ISSUE #5 (M+1 Volume Lagging gap)** adicionada em `KNOWN_ISSUES.md`:
  documenta workaround interim (`Vol_proj_M+1 = realizado_competencia_M+1`)
  vs solucao target (cycle-time-aware via v2).
- **Novo helper `compute_stage_metrics_vigentes`** em `m7_extract_utils.py`:
  calcula medianas reais por estagio×mes via Bitrix `crm.stagehistory.list`.
  Output: `stage_probability` + `stage_duration_dias` por estagio.
- **Novo helper `compute_historico_3m`** em `m7_extract_utils.py`: media movel
  3 meses de oportunidades criadas para uso em `entradas_novas_M+1`.
- **Parametro opcional `extras=None`** em `write_output`: scripts podem agora
  passar campos auxiliares (ex: `historico_3m`) que sao merged no top-level
  do JSON output. Backward compat: ausente = comportamento legado.
- **Scripts standalone novos:**
  - `01-Metas/Biblioteca-de-Indicadores/Consorcios/scripts/stage_metrics_vigentes.py`
  - `01-Metas/Biblioteca-de-Indicadores/Seguros/scripts/stage_metrics_vigentes_seg.py`
- **Helper `build_especialista_mapping(card_yaml_path)`** em `m7_extract_utils.py`:
  resolve bridge SQL especialista ler Card YAML em runtime e gerar mapping
  `nome_assessor -> especialista` dinamicamente. Card vira SoT do mapping.
  Companion: `render_especialista_cte_sql(mapping)` produz CTE ClickHouse.
- **Secao "Campos opcionais para integracao com m7-ritual-gestao"** adicionada
  em `configuring-cards/SKILL.md` (em 2026-05-06 anterior) e formalizada em
  `configuring-cards/references/esp-perf-002-resumo.md` v1.2 com tabela de
  todos os campos opcionais consumidos pelo `build_deck.py`.

### Changed

- **Formula `installment_amortization`** corrigida em `projecting-results/SKILL.md`:
  - **Antes (errada — double-count):** `novas_vendas_funil = Vol_proj × commission/installments`
    onde `Vol_proj` incluia lagging volume.
  - **Agora (correta):** M0 usa `stage_probability_M0`; M+1 usa
    `componente_funil_M+1` (= 0 no metodo "a" interim). NUNCA `lagging_volume`
    no componente funil. Exemplo numerico Consorcios + tabela inputs por
    vertical (CON: 0.035 / SEG: 0.50) incluidos.
- **`projection-methodology.md`** atualizado:
  - Secao 5.1 `pipeline_conversion_extended` (v1 — current/interim) com
    `deprecated_reason` documentado.
  - Secao 5.2 `pipeline_conversion_extended_v2` (target) com algoritmo
    dia-a-dia + exemplo concreto (deal Prospeccao dia 20 entra em M+1).
- **`volume_consorcio_mensal.yaml`** declarado v2 como `preferred: true`
  (high confidence) com v1 demoted para `preferred: false` + `confidence: medium`
  + `deprecated_reason`. Migracao gradual (`applicable: true` em ambos).
- **`volume_consorcio_mensal.py`** swap `data_venda` → `data_competencia`
  em todas as queries SQL `m7Bronze.consorcio_contratos`. Validacao runtime
  pendente (confirmar coluna existe no DESCRIBE TABLE).
- **`oportunidades_criadas_funil.py` + `_seg.py`** geram extras `historico_3m`
  no output JSON (3 meses agregados N1 para uso em projecao M+1).
- **`receita_consorcio_mensal.py` + `volume_consorcio_mensal.py`** refatorados
  para gerar CTE `mapa_especialista` dinamicamente do Card YAML em runtime
  (bridge SQL especialista — fix 2026-05-06). Resolve gaps anteriormente
  cobertos via `Card.apresentacao.overrides_ritual.n5_by_esp` (22 entradas
  manuais). Card v2.8.0 declara 12 assessores Douglas + 10 assessores Tereza
  + 9 aliases (acentos, typos) → CTE com 31 entradas. Adiciona Waleska
  (rodada 7), Pedro Araújo (alias Pedro Ramos), Káryne Bênutten (alias
  Karyne Beuttenmüller), Luís Eduardo (alias Luiz Eduardo), Gustav0 Melo
  (typo), Amanda Amarante (correcao typo "Amanda Marante" anterior).
  Fallback hardcoded mantido se Card nao encontrado.
- **`card-template.yaml`** template ampliado com exemplos comentados de
  `metadata.{total_label, responsaveis_n2, assessor_aliases,
  responsavel_externo_aliases}`, `kpi_references[].matrix_views[]`,
  `kpi_references[].projecao.componentes[]` formais com `inputs[]`, e bloco
  completo `apresentacao.*` com 8 campos opcionais.

### Tracking

- ISSUE #5 (M+1 Volume Lagging gap) — ATIVO ate validacao runtime do swap
  data_competencia + integracao stage_metrics_vigentes na skill projecting-results.
- Algoritmo dia-a-dia metodo "b" documentado mas ainda nao implementado em
  codigo da skill projecting-results — proxima sessao.

## [6.2.1] - 2026-05-05

### Added
- **Special-case `meta=0` + `direction: menor_melhor` (zero-target)** documentado em `consolidating-wbr/SKILL.md` Fase montagem do Painel: quando indicador tem `metas_ppi.qty: 0` com `direction: menor_melhor` (ex: `oportunidades_sem_atividade_planejada_funil[_seg]`), aplicar regra special-case ANTES da formula padrao `meta/max(real,1)×100`:
  - `realizado == 0` → `pct = 100%` → status verde
  - `realizado >= 1` → `pct = 0%` → status vermelho
- Novo valor enum `metas_ppi_zero_target` em `regra_semaforo` do canonical JSON.

### Changed
- Cards CON v2.5.1, SEG WL v2.11.1, SEG RE v1.3.1 com `metas_ppi.oportunidades_sem_atividade_planejada_funil[_seg].qty: 0` (era `pendente`).

## [6.2.0] - 2026-05-04 (noite)

> **Minor release retrocompativel** — RESOLVE KNOWN_ISSUES.md ISSUE #1
> (lagging_indicator matematicamente quebrado para receita). Introduz dois
> novos metodos de projecao em `projecting-results/SKILL.md`:
> `installment_amortization` (receita) e `pipeline_conversion_extended`
> (volume). Ambos suportam horizons `[mes_corrente, mes_seguinte]`.

### Added

- **Metodo `installment_amortization`** documentado em `projecting-results/SKILL.md` Fase 2:
  - Decompoe receita projetada em LAGGING (parcelas das vendas dos N-1 meses anteriores caindo no mes alvo, lidas do ledger ClickHouse) + NOVA (1a parcela das vendas que fecharao no mes alvo, derivada de Vol_proj × commission_rate / installments).
  - Parametros: `commission_rate` (CON 0.035; SEG 0.50), `installments` (12), `source_ledger` (CON: `m7Bronze.consorcio_receita`; SEG: `m7Prata.seguro_comissao_assessor_fuzzy`), `source_funil.horizon_aware: true`, `commission_rate_by_produto` (override por mix Seguros).
  - Substitui `lagging_indicator` (DEPRECADO 2026-05-04) que somava lag_weights=1.0 sem commission_rate, produzindo receita ≈ volume — bug critico documentado em KNOWN_ISSUES.md.

- **Metodo `pipeline_conversion_extended`** documentado em `projecting-results/SKILL.md` Fase 2:
  - Mes corrente: `Vol_Oport_Ativas × Taxa_Conversao_Mes` (snapshot simplificado).
  - Mes seguinte: `(pipeline_residual_M0 + entradas_novas_3m_média) × Taxa_Conversao` (forward projection usando media historica de oportunidades_criadas).
  - Substitui `pipeline_conversion` (stage_probability) que dependia de stage breakdown nao retornado pelos scripts atuais — DEPRECADO 2026-05-04.
  - Suporta `filtro_squad` (`wl`/`re`) para Cards split.

- **Horizons no output JSON** (`projection-by-especialista.json`): toda metrica projetada agora tem `projecao_mes_corrente` E `projecao_mes_seguinte` populados quando metodo preferido suporta (todos `installment_amortization` + `pipeline_conversion_extended`). Spec ja existia, agora implementacao garante populacao consistente.

### Changed

- **KNOWN_ISSUES.md ISSUE #1** marcado como **RESOLVIDO 2026-05-04** com pointer para os Cards/Indicadores/SKILL atualizados.
- **`projecting-results/SKILL.md` Fase 2** ganha 2 novas secoes de metodo (`installment_amortization`, `pipeline_conversion_extended`) e marca `lagging_indicator` + `pipeline_conversion` como DEPRECADOS (skill IGNORA quando encontra `applicable: false, deprecated: true` nos YAMLs).

### Migration notes

- Cards CON N3 v2.4.0+, SEG WL N3 v2.10.0+, SEG RE N3 v1.2.0+ ja referenciam os novos metodos via `metodo_preferido` em `kpi_references[].projecao`.
- Indicadores `receita_consorcio_mensal`, `volume_consorcio_mensal`, `receita_seguros_mensal`, `volume_seguros_mensal` atualizados com os novos metodos em `projection.methods` (preferred=true) e antigos marcados deprecated.
- Pipeline G2.2 E5 (`projecting-results`) precisa rodar com a v6.2.0 para popular ambos horizons no canonical JSON. Cycles antigos rodados com 5.4.0/6.1.0 nao tem `projecao_mes_seguinte` — re-rodar E5 ou aceitar fallback gracioso (slide renderiza bar vazia para M+1).
- m7-ritual-gestao >= 3.2.0 consome ambos horizons para renderizar Card Projecao com 6 bars (Receita + Volume × MTD/M0/M+1). Versoes anteriores ignoram silenciosamente.

## [6.1.0] - 2026-05-04

> **Minor release retrocompativel** — documenta o padrao novo de `metas_ppi` (com `pct_ativas_max` e subbloco `por_especialista`) e adiciona Fase 4.5 ao consolidating-wbr para derivar `pct_estagnadas_ativas` e popular `n2.{especialista}.meta` no canonical JSON. Cards CON N3 e SEG WL N3 ja adotaram o padrao em 2026-05-04. Nenhuma regressao de comportamento — pipeline existente continua funcional para Cards sem essas chaves.

### Added

- **`configuring-cards/SKILL.md` Passo 4.5** — documenta a estrutura completa de `metas_ppi:` no top-level do Card:
  - Estrutura por PPI com `qty`/`volume`/`ticket_medio` no top-level (N1) + subbloco opcional `por_especialista:` para metas N2 individuais (usar quando KPIs por especialista divergem, como Seg WL Claudia=18 vs Tarcisio=15 ativas).
  - Padrao especifico para `oportunidades_estagnadas_funil_*` com novo campo `pct_ativas_max` (% das ativas que sera o teto da meta de estagnadas, semaforo regra a, cap 200%, `direction: menor_melhor`).
  - Metodologia de derivacao top-down via Little's Law a partir de Meta Receita + Meta Volume + Meta Taxa Conversao + Meta qty WON.
  - Convencao para documentar inputs externos (FIX TEMPORARIO) em `nota:` quando colunas no banco ainda nao existem — link para `_estudo-metas-ppi/TODO-MIGRACAO.md`.
- **`consolidating-wbr/SKILL.md` Fase 4.5.a** — derivacao automatica de `pct_estagnadas_ativas`:
  - Para Cards com `metas_ppi.oportunidades_estagnadas_funil_*.pct_ativas_max` declarado, o agent cria entrada derivada `oportunidades_estagnadas_funil_*_pct_ativas` no canonical JSON.
  - `realizado = qty_estagnadas / qty_ativas × 100` (calculado para N1 e cada N2).
  - `meta = pct_ativas_max`, `direction: menor_melhor`, `regra_semaforo: metas_ppi_a_menor_melhor`.
  - Entrada original de `oportunidades_estagnadas_funil_*` (qty) preservada como contextual sem semaforo proprio.
- **`consolidating-wbr/SKILL.md` Fase 4.5.b** — leitura de `por_especialista` para popular meta N2:
  - Para Cards com subbloco `por_especialista:` em qualquer chave de `metas_ppi.{ppi}`, o agent popula `n2.{especialista}.meta` no canonical JSON com `qty`/`volume`/`ticket_medio` correspondentes.
  - Calcula `n2.{especialista}.pct` e `n2.{especialista}.status` aplicando regra de semaforo.
  - Sem subbloco: comportamento atual preservado (so realizado N2, sem meta N2).
- **Estudo `02-Controle/_estudo-metas-ppi/`** (referenciado no `configuring-cards`) com modelo reverso de funil (Little's Law) e checklist de migracao em `TODO-MIGRACAO.md`.

### Migration notes

- Cards CON N3 (v2.2.0) e SEG WL N3 (v2.8.0) ja adotaram o padrao em 2026-05-04.
- O `m7-ritual-gestao` >= 3.0.0 consome essas chaves derivadas para renderizar o indicador Estagnadas com `% das ativas` como linha principal e meta N2 individual no Dashboard. Versoes anteriores do ritual ignoram silenciosamente.
- Items 5/6 do `02-Controle/_estudo-metas-ppi/TODO-MIGRACAO.md` agora considerados implementados na pipeline (G2.2 E6 — consolidating-wbr).

## [6.0.0] - 2026-04-30

> **Major release** — `plano-de-acao.csv` descontinuado como SoT do Plano de Acao.
> A SoT migrou para a lista ClickUp `pa-resultado` (id `901326795742`) acessada
> via ClickUp MCP. Atualizar `m7-ritual-gestao` para `>= 2.0.0` na mesma janela.

### Added

- **E2 `collecting-data` ganha Fase 1.5 — Coleta do Plano de Acao via ClickUp MCP** (`mcp__claude_ai_ClickUp__*`):
  - Tools usadas: `clickup_filter_tasks`, `clickup_get_custom_fields`, `clickup_get_task`
  - Filtros canonicos aplicados:
    - **Vertical** (custom field id `a7c7bc7c-2526-4083-9753-aa2103a08f53`) — option_value mapeado por vertical
    - **Excluir subtasks** (`parent != null`) — subtasks pendentes viram nota descritiva no campo `subtasks_pendentes` da parent
    - **Responsavel Externo** (custom field id `e44c8cff-7d0b-4074-84ae-c10c67b0a26d`) resolvido para nome real
  - Output: `{cycle_folder}/dados/raw/clickup-tasks-{vertical}.json` com schema documentado em SKILL.md
  - Custom fields adicionais auto-descobertos por nome (case-insensitive): `indicador_impactado`, `origem`, `receita_impacto`, `volume_impacto`
- **Nova secao "Dependencias Externas (MCPs)"** no SKILL.md de E2 — documenta requisito de ClickUp MCP habilitado no projeto
- **`oportunidades_estagnadas_funil.py` (CON) e `oportunidades_estagnadas_funil_seg.py` (SEG) ganham `agg_by_stage`** — paridade com `oportunidades_ativas_funil*.py`. Output JSON agora inclui linhas com `estagio = <nome>` em N1-N5 (alem das linhas totais com `estagio = None`). Permite Slide 9 do ritual identificar em quais estagios as estagnadas estao concentradas

### Changed

- **E4 `summarizing-actions` reescrita** — input mudou de `plano-de-acao.csv` para `dados/raw/clickup-tasks-{vertical}.json` (gerado em E2 Fase 1.5):
  - Schema da skill atualizado com mapeamento legado CSV ↔ JSON ClickUp
  - Bucketing de status mapeado para 3 buckets (ativa/concluida/cancelada) sobre statuses do ClickUp (case-insensitive)
  - Classificacao "Sem prazo" adicionada (quando `due_date == null`) — flag de warning para exigir prazo no proximo ritual
  - Campos `volume_impacto` e `receita_impacto` ja vem como `number` do JSON (sem necessidade de parse de "R$" como no CSV)
  - Eficacia de acoes concluidas continua igual: cruza `indicador_impactado` com dados consolidados de E2
- **Pre-requisitos de E2** — `CLICKUP_API_TOKEN` NAO e necessario (auth gerenciada pelo MCP); pre-requisito agora e "ClickUp MCP habilitado no projeto"

### Removed / Deprecated

- **`plano-de-acao.csv` descontinuado como SoT** — todas as referencias removidas do SKILL.md de `summarizing-actions`. Anti-patterns adicionados:
  - "NUNCA leia `plano-de-acao.csv` local"
  - "NUNCA chame a API ClickUp (MCP ou HTTP) diretamente desta skill — coleta e responsabilidade de E2"
- **Indicador `volume_oportunidades_ativas_funil_seg` depreciado** — movido para `_Historico/` com sufixo `_ate-2026-04-30`. Volume das ativas SEG agora vem embutido no output de `oportunidades_ativas_funil_seg.py` (paridade com Consorcios refatorado em 2026-03-23). Card SEG atualizado: entrada `kpi_references[]` removida; criterio de desvio critico ajustado para usar `oportunidades_ativas_funil_seg.{quantidade,volume}`

### Breaking Changes

1. **E4 nao funciona mais sem E2 Fase 1.5 rodada antes** — quem rodar E4 esperando ler `plano-de-acao.csv` falha. Migracao: rodar E2 completo (incluindo Fase 1.5) antes de E4.
2. **ClickUp MCP virou dependencia mandatory de E2** — sem ele, Fase 1.5 aborta. Verificar `desempenho/.claude/settings.local.json` permissions inclui `mcp__claude_ai_ClickUp__*`.
3. **Schema do output de `oportunidades_estagnadas_funil*.py` mudou** — JSON agora inclui coluna `estagio` (com `None` para totais e nome do estagio para breakdowns N1-N5). Consumidores externos que parsavam o JSON antigo (sem `estagio`) precisam atualizar — o `decision-recorder` e o `material-generator` ja foram atualizados.
4. **Indicador `volume_oportunidades_ativas_funil_seg` nao existe mais como indicador top-level** — pipelines/Cards externos que referenciavam esse indicator_id precisam migrar para `oportunidades_ativas_funil_seg.volume`.

### Reference

- `skills/collecting-data/SKILL.md` (Fase 1.5 nova, Dependencias Externas, anti-patterns ClickUp)
- `skills/summarizing-actions/SKILL.md` (reescrita workflow Fases 1-5)
- `skills/projecting-results/KNOWN_ISSUES.md` (issue #1 `lagging_indicator` quebrado para receita — sem fix nesta release; m7-ritual-gestao v2.0.0 suprime visualmente o card via regra v1.13)

### Compatibility

- **m7-ritual-gestao requerido**: `>= 2.0.0` (consome o JSON ClickUp em Slides 4 e 5; agent decision-recorder escreve via MCP)
- **Snapshots de ciclos antigos** (`< 2026-04-30`) podem ter JSONs sem `estagio` em estagnadas — re-rodar `oportunidades_estagnadas_funil*.py` para popular

---

## [5.5.0] - 2026-04-29

### Added
- **Fase 6.5 em E5 `projecting-results`** — desagregacao de projecao por especialista (na hierarquia oficial, especialista = N3 — Douglas/Tereza/Claudia/Tarcisio; coordenador = N2 — Joel. Schemas legacy continuam usando label `N2-Especialista` — renomeacao esta fora de escopo desta versao):
  - Para cada especialista em `apresentacao.responsaveis[]` (ou colunas de especialista dos dados consolidados), aplica os mesmos `projection.methods[]` do YAML em subsets de dados
  - Resolve dependencias cruzadas tambem em nivel de especialista (ex: receita Douglas usa volume projetado Douglas)
  - Calcula projecao do **mes corrente E mes seguinte** (antes calculava so o mes corrente em N1)
  - Inclui linha "Sem Especialista" (bridge gap) com realizado mas sem projecao/meta
- **Novo output `analise/projection-by-especialista.json`** — estrutura JSON com projecoes por especialista consumida pelo m7-ritual-gestao para renderizar mini-graficos no Slide 9 (Funil Pipeline)

### Changed
- Exit Criteria de E5 agora exige `projection-by-especialista.json` gerado (alem do `projection-report.md` existente)

### Compatibility
- Output novo e **complementar** ao `projection-report.md` (que continua focado em N1) — sem breaking change para consumidores existentes
- m7-ritual-gestao v1.8.0+ consome o novo JSON; versoes anteriores ignoram

## [5.4.0] - 2026-04-02

### Changed
- **Graficos do WBR HTML migrados de SVG inline para D3.js v7**: Substituidas as 5 receitas de SVG manual (coordenadas hardcoded, viewBox, stroke-dasharray) por receitas D3.js carregadas via CDN. D3 calcula escalas e layout automaticamente, eliminando distorcoes causadas por erros de calculo do analyst agent
- **Semaforo de Indicadores com exemplo concreto**: Adicionado bloco HTML copy-paste no guia (`wbr-html-guide.md`) com 4 variantes de card (verde, vermelho, amarelo, cinza/PPI) e regras explicitas de mapeamento classe-cor-badge
- **Template HTML atualizado**: Adicionado `<script src="https://d3js.org/d3.v7.min.js">` no `<head>`, placeholders de chart atualizados para usar `<div id>` containers + `{{chart_d3_script}}`
- **SKILL.md**: Terminologia atualizada de SVG para D3 no workflow (Fase 6b), regras e exit criteria

## [5.3.0] - 2026-04-01

### Added
- **Secao 1.5 "Painel de Indicadores" no WBR**: Tabela consolidada com TODOS os indicadores do Card de Performance (`kpi_references[]`), incluindo colunas N2 por especialista. Posicao fixa entre Resumo Executivo e Desvios. Serve como contrato de dados para o m7-ritual-gestao (Slide 2 Matriz)
- Placeholder da Secao 1.5 no template `wbr.tmpl.md` com formato fixo e regras em comentarios
- Secao 1.5 como output obrigatorio no `analyst.md` com regras de preenchimento

### Changed
- WBR agora tem 6 secoes obrigatorias (era 5) — adicionada Secao 1.5
- Exit criteria atualizados para exigir Painel com todos indicadores do Card e colunas N2
- Anti-pattern atualizado: nunca omitir indicadores do Card no Painel

## [5.2.2] - 2026-04-01

### Fixed
- **`CLICKHOUSE_DATABASE` removido dos pre-requisitos**: A variavel estava listada como obrigatoria na skill `collecting-data` e no README, mas `collect.py` nao a consome — cada script de indicador define seu database internamente (m7Bronze, m7Prata, etc.). Exigir a variavel bloqueava o pipeline desnecessariamente

### Changed
- **`collecting-data/SKILL.md`**: Lista de variaveis de ambiente reduzida de 6 para 5, com nota explicativa ("cada script define seu database internamente")
- **`README.md`**: Removida linha `CLICKHOUSE_DATABASE` da tabela de variaveis de ambiente

## [5.2.1] - 2026-04-01

### Removed
- **`.mcp.json` deletado**: Removia servidores MCP (ClickHouse, Bitrix24) da sessao Claude Code. Nenhuma skill ou agent do plugin precisa de MCPs — E2 usa scripts Python standalone, analyst tem apenas tools Read/Write/Grep/Glob. O `.mcp.json` disponibilizava tools MCP na sessao, criando vetor de drift que levava o LLM a tentar coleta via MCP ao inves de scripts

### Fixed
- **`run-weekly.md`**: Removidas 3 referencias residuais a MCP — template CICLO.md ("erros de MCP" → "erros de scripts"), gate de proveniencia ("dados vieram de MCP real" → "execucao real de scripts"), tabela de erros ("MCP indisponivel" → "Script falhou")
- **`next.md`**: Entry criteria E2 corrigido ("MCPs acessiveis" → "ambiente Python configurado (vars + deps)")
- **`README.md`**: Removidas 2 linhas de dependencias MCP (ClickHouse MCP e Bitrix24 MCP para analyst E3-E6) — analyst nao usa MCPs
- **`card-template.yaml`**: Passo Coleta corrigido ("via ClickHouse MCP" → "via collect.py")
- **`esp-perf-002-resumo.md`**: Pipeline Coleta corrigido ("via ClickHouse/Bitrix24 MCP" → "via collect.py (ClickHouse/Bitrix24 direto)")

## [5.2.0] - 2026-03-31

### Added

#### E7 — Licoes Aprendidas (recording-lessons)
- **Nova skill `recording-lessons`**: Consolida licoes aprendidas do ciclo mensal a partir de WBRs (E6), atas de rituais (G2.3), action-reports (E4) e data-quality-reports (E2) de TODAS as verticais. Framework de 4 categorias (Funcionou / Nao funcionou / Surpreendeu / Faltou) com propostas de melhoria priorizadas via matriz Impacto x Esforco
- **Novo command `record-lessons`**: `/m7-controle:record-lessons [periodo]` — executa E7 para um mes completo. Descobre ciclos cross-vertical automaticamente
- **Novo template `lessons-learned-report.tmpl.md`**: Relatorio com resumo executivo, licoes categorizadas com evidencia rastreavel, propostas priorizadas, tendencias por vertical e feedback dos gestores N2
- **Nova reference `lessons-framework.md`**: Metodologia de extracao de licoes, criterios de qualidade, metodo de consolidacao cross-ciclo, matriz de priorizacao e exemplos bons vs. ruins

### Changed
- **Agent `analyst`**: Escopo expandido de E3-E6 para E3-E7. Adicionada secao E7 com processo de 10 passos, regras especificas e output path. Diagrama de fluxo de dados atualizado com E7
- **README.md**: Pipeline atualizado com E7 mensal, composicao (7 skills, 4 commands), tabelas de commands e outputs
- **plugin.json e marketplace.json**: Versao 5.2.0, descricao atualizada (7 etapas)

#### Decisao Arquitetural: Output Global
- E7 produz relatorio unico em `mensal/YYYY-MM/lessons-learned-YYYY-MM.md` (nivel processo, nao por vertical). Vertical e ciclo sao atributos dentro de cada licao. Isso permite identificar padroes cross-vertical que seriam perdidos com relatorios separados
- E7 NAO faz parte do pipeline `next`/`run-weekly` (cadencia diferente: mensal vs semanal)

## [5.1.1] - 2026-03-24

### Fixed
- `run-weekly.md`: LLM pulava prompt de periodo/granularidade e assumia defaults. Agora a instrucao e imperativa: SEMPRE perguntar via AskUserQuestion ANTES de iniciar pipeline. Step 1 redireciona explicitamente para Step 1.5

## [5.1.0] - 2026-03-24

### Added

#### WBR Narrativo HTML — Versao Visual (E6)
- **Novo template `wbr-narrativo.tmpl.html`**: HTML com CSS M7-2026 pre-validado (score A), KPI cards, semaforo grid, chart containers, timeline, callouts, decisao critica
- **Novo guia `wbr-html-guide.md`**: Receitas de SVG inline (horizontal bar, donut, funnel pipeline, cenarios P10/Base/P90), mapeamento de dados, design tokens e checklist de validacao
- **Nova Fase 6b** na skill `consolidating-wbr`: gera HTML visual com SVG charts inline (min 2, max 5 graficos), reutilizando exatamente os mesmos numeros do WBR Estruturado
- **Logo M7 embeddado** como base64 no template (self-contained, sem dependencias externas)

#### Geracao de PDF via Puppeteer (E6)
- **Novo script `html-to-pdf.js`**: converte HTML → PDF via Puppeteer (A4, print background, margins)
- **Nova Fase 6c** na skill: executa conversao HTML → PDF automaticamente apos geracao do HTML
- **Dependencia**: `puppeteer@^22` (mesmo pattern dos plugins apresentacoes e gestao-de-projetos)

#### Pipeline E6 Atualizado
- E6 agora produz **4 artefatos**: WBR Estruturado (.md), WBR Narrativo (.md), WBR Narrativo Visual (.html), WBR Narrativo PDF (.pdf)
- Exit criteria atualizados com verificacoes de HTML (CSS inalterado, SVGs presentes, numeros identicos, logo presente)
- Spot-check (Fase 7) agora verifica numeros no HTML tambem
- `analyst.md` atualizado com fluxo de dados e instrucoes para geracao HTML/PDF
- `run-weekly.md` atualizado com os 4 artefatos esperados de E6

## [5.0.1] - 2026-03-24

### Changed
- Default timeout de collect.py run aumentado de 300s para 900s (15 minutos) para acomodar scripts com enrichment Bitrix24 pesado

## [5.0.0] - 2026-03-24

### Changed (BREAKING)

#### E5 Projecao YAML-Driven (A8)
- **`projecting-results/SKILL.md` reescrito**: E5 agora le metodos de projecao do bloco `projection` dos YAMLs de indicadores em vez de hardcodar 4 metodos
- **Novos metodos YAML-driven**: `run_rate_linear`, `trend_exponential`, `pipeline_conversion`, `lagging_indicator` — cada indicador define quais usar
- **`pipeline_conversion`** com `stage_conversion_rates` e `stage_duration_days` do YAML e formula P(timing) que penaliza deals em estagios iniciais
- **`lagging_indicator`** com `lag_months` e `lag_weights` para indicadores derivados (ex: receita = f(volume com lag 1-3 meses))
- **Resolucao de dependencias cruzadas**: volume projeta primeiro (usa oportunidades_ativas), receita projeta depois (usa projecao de volume)
- **Card `projecao.obrigatoria`**: define quais indicadores DEVEM aparecer no WBR e quais geram cenarios P10/P90
- **`projection-methodology.md` reescrito**: documenta todos os metodos, formulas, resolucao de dependencias e leitura do YAML
- **Template `projection-report.tmpl.md` atualizado**: secoes de detalhe por metodo (pipeline conversion por estagio, lagging por lag) e dependencias cruzadas

#### Periodo e Granularidade Configuravel (A1+A7)
- **`run-weekly.md`**: agora pergunta `periodo` (YYYY-MM) e `granularidade` (diaria/semanal/quinzenal/mensal/trimestral) antes de iniciar
- **CICLO.md template**: novos campos `Periodo`, `Granularidade`, `Checkpoint` no header
- **Contexto temporal**: todas as skills e o analyst leem checkpoint_label do CICLO.md e enquadram analise como MTD (month-to-date), NAO como "semana isolada"
- **`dias_uteis_totais`**: agora refere-se ao periodo completo (mes inteiro), corrigindo projecoes de run-rate
- **Templates WBR**: header com `Periodo` e `Checkpoint` (estruturado e narrativo)

### Added

#### Execucao Paralela e Timeout (A3+A6)
- **`collect.py --parallel`**: novo flag para executar scripts em paralelo via ThreadPoolExecutor (max 4 workers)
- **Timeout default 120s → 300s**: evita timeouts em scripts com enrichment Bitrix24
- **Per-script timeout**: campo `script.timeout` no YAML do indicador gera `timeout_override` no execution-plan.json
- **`execution-plan-schema.md`**: adicionado campo `timeout_override` ao schema do Step

#### Deteccao de Dados Defasados (A2)
- **Staleness check** em `collect.py`: detecta indicadores com dados >= 3 meses defasados e gera warning no data-quality-report
- **Nova dimensao "Defasagem Historica"** em `data-quality-rules.md`: thresholds e regras de staleness

#### Regras de Classificacao Semaforo (A4)
- **`analyst.md`**: nova secao "Classificacao Semaforo — Regra Rigida" — semaforo e EXCLUSIVAMENTE % de meta, concentracao e flag de risco separado
- **`analyzing-deviations/SKILL.md`**: regra critica apos tabela semaforo reforçando que performance individual NAO afeta classificacao do agregado

#### Handling de Dados Nao Atribuidos (A5)
- **Nova Fase 2.1** em `analyzing-deviations`: detecta buckets "Sem Especialista"/NULL/vazio em segmentacoes e reporta explicitamente com valor e % do total
- **`analyst.md`**: regra para sempre verificar e reportar dados nao atribuidos

### Design Decisions
- **MAJOR version** (5.0.0) porque E5 muda completamente de metodos hardcoded para YAML-driven, alterando como projecoes sao calculadas e quais dados sao necessarios
- **Periodo antes de granularidade**: o pipeline analisa um PERIODO (mes), e a granularidade define apenas a frequencia dos checkpoints. Isso corrige o enquadramento temporal dos WBRs
- **stage_conversion_rates calibraveis**: os rates iniciais no YAML sao estimativas; apos 2-3 ciclos serao ajustados contra dados reais do taxa_conversao_funil_con
- **Parallel execution opt-in**: `--parallel` e flag explicito (nao default) para manter backward compatibility e permitir debug serial

## [4.0.0] - 2026-03-23

### Changed (BREAKING)

#### Arquitetura: Scripts Python Standalone Substituem MCPs na Coleta (E2)
- **`collect.py` reescrito** com 3 subcomandos: `plan` (gera plano com scripts), `run` (executa scripts via subprocess), `consolidate` (valida e consolida outputs)
- **Novo `collect.py run`**: executa cada script de indicador via `subprocess.run()`, acesso direto a ClickHouse (clickhouse-connect) e Bitrix24 (requests) sem MCPs
- **Eliminado loop mecanico do LLM**: a skill agora roda 3 comandos Python ao inves de executar N chamadas MCP individuais
- **Schema do execution-plan.json v2.0**: steps referenciam `script_path`, `script_checksum`, `test_status` e `output_contract` ao inves de `tool`, `tool_params`, `substeps`
- **Novo artefato `execution-results.json`**: status por script com timing, exit code, rows_returned

#### Verificacao de Integridade e Contrato
- SHA-256 checksum verificado antes de executar cada script (mismatch → skip)
- `test_status` gate: `failed` → skip, `untested` → warning, `passed` → executa
- Output validado contra `output_contract.columns/types` do YAML

#### Ambiente de Execucao
- Fase 0 da skill agora verifica variaveis de ambiente (CLICKHOUSE_*, BITRIX_WEBHOOK_URL) e dependencias Python ao inves de acessibilidade de MCPs
- MCPs mantidos apenas para E3-E6 (analyst pode consultar ClickHouse para drill-down)

### Removed
- `build_sql_step()`, `build_hybrid_step()` — substituidos por `build_script_step()`
- `load_raw_file()`, `preprocess_bitrix_dataframe()`, `run_hybrid_transform()` — scripts standalone fazem isso internamente
- `substitute_params()` — scripts usam interface CLI `--param key=value`
- Toda logica de substeps, enrichment, post-filters, transforms exec() — desnecessaria com scripts standalone
- Campo `total_mcp_calls` no plano → substituido por `total_scripts`
- Campo `mcp_calls_log` no consolidado → substituido por `script_execution_log`

### Design Decisions
- **Principio**: separacao completa entre descricao (YAML) e execucao (script .py). O YAML descreve o que o indicador e; o script extrai os dados. A skill orquestra sem interpretar nenhum dos dois.
- **subprocess ao inves de MCP**: MCPs introduziam instabilidade runtime (timeouts, wrappers variados, campos custom nao retornados). Scripts Python com bibliotecas nativas sao deterministicos e testaveis isoladamente.
- **Execucao dentro do collect.py**: o `cmd_run()` gerencia todos os subprocesses internamente, reduzindo o papel do LLM de "executor de N chamadas" para "orquestrador de 3 comandos".
- **MAJOR version** (4.0.0) porque o schema do execution-plan.json muda completamente (MCP steps → script steps).

## [3.2.0] - 2026-03-20

### Added

#### PPIs de contexto na analise de desvios (E3)
- Nova **Fase 2.5** na skill `analyzing-deviations`: le `kpis_analisar_como_contexto` do Card de Performance e usa os racionais para enriquecer a inferencia de causa-raiz
- PPIs de funil (taxa_conversao, oportunidades, estagnacao, ticket_medio) agora sao cruzados com KPIs Vermelhos para elevar confianca das hipoteses
- Pre-requisito adicionado: Card de Performance da vertical acessivel
- Exit criteria adicionado: PPIs consultados e incorporados (ou motivo registrado)

#### Secao "Saude do Pipeline" no WBR (E6)
- Nova secao **2.5** no WBR Estruturado entre "Desvios" e "Acoes"
- Apresenta PPIs de funil em formato compacto: valor N1, tendencia MoM, diagnostico em 1 linha
- WBR Narrativo atualizado: "O que Preocupa" agora incorpora diagnosticos de PPIs

#### Filtro cross-vertical em acoes (E4)
- Skill `summarizing-actions` agora filtra por criterio OR: `vertical` do CSV OU `indicador_impactado` que corresponda a algum indicator_id do Card da vertical
- Captura acoes como "Antecipar pagamento comissao consorcio" cadastradas com vertical=investimentos mas que impactam indicadores de consorcios
- Output registra quantas acoes vieram de cada criterio para transparencia

## [3.1.1] - 2026-03-19

### Fixed
- `collect.py consolidate`: MCP tools retornam data em formatos wrapper diferentes (`{"stages":[...]}`, `{"users":[...]}`, `{"pipelines":[...]}`) — adicionado unwrapping automatico em `load_raw_file()` que extrai o primeiro array de dentro do dict
- `collect.py consolidate`: campo `meta` adicionado aos campos excluidos do completude check — indicadores sem meta formal (ticket_medio) tem `meta=NULL` por design

## [3.1.0] - 2026-03-19

### Added

#### Enrichment substeps para campos UF_* do Bitrix24
- `collect.py plan` detecta automaticamente quando um substep MCP bulk (`bitrix24_get_deals_from_date_range`) lista campos `UF_*` nos `output_fields` do YAML
- Gera um substep de enrichment (`source: "enrichment"`) que instrui a skill a chamar `bitrix24_get_deal` individualmente para cada deal ID
- SKILL.md atualizada com instrucoes para executar enrichment substeps (ler deal IDs, fetch individual, consolidar)
- `collect.py consolidate` faz merge dos campos enriquecidos (ex: `UF_CRM_1758122406`) no DataFrame principal antes do transform
- Enrichment e best-effort: falhas individuais nao bloqueiam o pipeline

### Changed
- Removido placeholder `UF_CRM_1758122406 = None` do preprocessamento — campo deve vir de enrichment real, nao injetado como NULL

## [3.0.1] - 2026-03-19

### Fixed
- `collect.py consolidate`: deal_stages da API Bitrix nao tem campo TYPE — derivado automaticamente de STATUS_ID
- `collect.py consolidate`: deal_stages STATUS_IDs sem prefixo de pipeline (C238:) — expandidos com prefixos automaticamente
- `collect.py consolidate`: parametros do JSON perdiam tipo (float→string) — conversao forcada via YAML type definition
- `collect.py consolidate`: datetimes Bitrix com timezone (+03:00) — stripped para naive antes do transform
- `collect.py consolidate`: OPPORTUNITY como string — convertido para float automaticamente
- `collect.py consolidate`: UF_CRM_1758122406 (SDR) ausente em bulk calls — adicionado como NULL
- `collect.py consolidate`: completude contava NULL hierarquicos (equipe, squad, pct_atingimento) — excluidos da verificacao
- `collect.py consolidate`: erro no transform logava sem indicator_id — adicionado id e traceback

## [3.0.0] - 2026-03-19

### Changed (BREAKING)

#### Arquitetura: Coleta Deterministica via Script Python
- **Novo script `collect.py`** com dois subcomandos (`plan` + `consolidate`) substitui toda interpretacao de YAMLs pelo LLM
- `collect.py plan`: le Cards + Indicadores YAML, resolve parametros, gera `execution-plan.json` com chamadas MCP exatas (tool, params, output_file)
- `collect.py consolidate`: le raw files MCP, executa transforms (hybrid via `exec()` do YAML), valida qualidade, gera `dados-consolidados.json` + `provenance.json` + `data-quality-report.md`
- **Skill collecting-data reescrita** como loop mecanico: le JSON, executa cada chamada, escreve raw files — zero interpretacao
- **Principio**: O LLM nao interpreta YAMLs de indicadores. O LLM le um JSON e chama os tools listados nele. Toda logica de negocio esta no script Python e nos YAMLs.

#### Gate de Proveniencia com SHA-256
- `provenance.json` gerado com hash SHA-256 de cada raw file
- Gate pos-E2 em `run-weekly.md` e `next.md` verifica existencia de `execution-plan.json`, `provenance.json`, raw files, e valida hashes
- Tabela de proveniencia exibida ao usuario apos E2

#### File-Based Handoff para E3-E6
- Skills E3-E6 adicionam regra de handoff: "NAO passe valores de dados no prompt do analyst. Passe APENAS caminhos de arquivos."
- Agent `analyst.md` adicionada regra de fonte de dados: "SEMPRE use Read tool para carregar dados dos arquivos especificados"

#### Spot-Check Numerico pos-WBR
- Nova Fase 7 em `consolidating-wbr`: verifica top 3 indicadores por gap contra `dados-consolidados.json`
- Discrepancias sao sinalizadas no WBR e registradas em CICLO.md

#### Agent data-collector DEPRECATED
- Substituido pelo script `collect.py` — mantido apenas para referencia historica
- Se invocado, responde com aviso de deprecacao

### Added
- `skills/collecting-data/scripts/collect.py` — motor deterministico de coleta
- `skills/collecting-data/references/execution-plan-schema.md` — schema do JSON de execucao
- Suporte a indicadores SQL (ClickHouse) e hybrid (Bitrix24 MCP + ClickHouse)
- Resolucao de parametros com precedencia: CLI > CICLO.md > YAML defaults
- Regra de quorum: pipeline para se <80% das chamadas MCP tiverem sucesso

### Design Decisions
- **Principio**: substituir interpretacao por execucao mecanica. A fabricacao de dados ocorria porque o LLM interpretava YAMLs e decidia quais queries executar. Com o script, toda logica esta em Python deterministico.
- **exec() para transforms**: transforms hybrid vem dos YAMLs commitados na Biblioteca de Indicadores — risco equivalente a rodar qualquer codigo Python do repositorio. Beneficio: zero duplicacao entre YAML e script.
- **MAJOR version** (3.0.0) porque a skill collecting-data tem workflow completamente diferente (script-driven vs instruction-driven).

## [2.0.0] - 2026-03-18

### Changed (BREAKING)

#### Arquitetura: Skills como Orquestradores
- **Commands agora invocam Skills, nunca Agents diretamente**. A skill decide internamente se executa no main thread ou delega a um agente. Removidas todas as referencias a `subagent_type` nos commands run-weekly e next.
- **Skill collecting-data (E2) executa queries MCP diretamente no main thread**. NAO delega coleta a subagentes. Elimina o risco de fabricacao de dados por agentes.
- Skills E3-E6 continuam delegando ao agent `analyst` — decisao interna de cada skill.

#### Agent data-collector rebaixado a papel auxiliar
- data-collector nao e mais o executor primario de E2
- Disponivel apenas para operacoes auxiliares (cross-source joins) se a skill decidir invoca-lo
- Tools MCP e FAIL-SAFE mantidos para uso auxiliar

### Removed
- Removido gate de proveniencia pos-E2 (mcp_calls_log) — desnecessario porque a skill executa queries diretamente
- Removidas referencias a `Agent(data-collector)` nos commands

### Design Decisions
- **Principio**: quem executa queries MCP nao pode ser auditado por si mesmo. A skill (main thread) executa e registra — nao ha delegacao que permita fabricacao.
- **MAJOR version** (2.0.0) porque a mudanca altera fundamentalmente como commands invocam a execucao (breaking change para quem referencia agents nos commands).

## [1.3.1] - 2026-03-17

### Fixed
- Agentes registravam `00:00` nos timestamps do CICLO.md por nao saberem obter a hora real
- Adicionada instrucao explicita em run-weekly.md, data-collector.md e analyst.md para executar `date '+%Y-%m-%dT%H:%M'` via Bash no momento exato do registro

## [1.3.0] - 2026-03-17

### Fixed

#### Anti-Fabricacao de Dados (CRITICO)
- **Causa raiz**: agente data-collector declarava `tools: Read, Write, Bash, Grep, Glob` — sem acesso a ferramentas MCP. Nao podia fisicamente executar queries no ClickHouse ou Bitrix24
- Adicionadas 16 ferramentas MCP explicitas ao frontmatter: `clickhouse_query`, `clickhouse_list_databases`, `clickhouse_list_tables`, `clickhouse_describe_table`, `clickhouse_get_table_sample`, `clickhouse_get_table_stats`, `bitrix24_validate_webhook`, `bitrix24_list_deals`, `bitrix24_get_latest_deals`, `bitrix24_filter_deals_by_pipeline`, `bitrix24_filter_deals_by_status`, `bitrix24_get_deal_pipelines`, `bitrix24_get_deal_stages`, `bitrix24_get_all_users`, `bitrix24_resolve_user_names`, `bitrix24_get_deals_from_date_range`
- Modelo do agente atualizado de Sonnet para **Opus** (maior aderencia a instrucoes FAIL-SAFE)

### Added

#### Gate de Proveniencia pos-E2
- Novo campo obrigatorio `metadata.mcp_calls_log` no JSON consolidado — registra cada chamada MCP com indicator_id, tool, timestamp, status e rows_returned
- Pipeline verifica existencia de `mcp_calls_log` antes de avancar para E3. Se vazio/ausente: **BLOQUEIA** com alerta de possivel fabricacao
- Verificacao de pelo menos 1 chamada com `status: success` e `rows_returned > 0`

#### Anti-Patterns Adicionais no FAIL-SAFE
- Proibido gerar dados internamente consistentes por construcao (aditividade perfeita por design)
- Proibido criar nomes de assessores ou codigos ficticios
- Proibido produzir series historicas com valores redondos ou progressoes perfeitas

#### Filtro de Status Reforçado
- Cards com `status != active` sao explicitamente pulados e registrados no CICLO.md
- Indicadores com `status != validated/promoted_to_gold` sao explicitamente pulados e registrados
- Se nenhum Card ativo ou indicador valido encontrado: pipeline PARA e informa usuario

## [1.2.1] - 2026-03-17

### Fixed
- Removida lista fixa de verticais (`investimentos`, `credito`, `universo`, `seguros`) dos 3 commands (run-weekly, next, status)
- Validacao agora e dinamica: qualquer vertical e aceita se existir pelo menos 1 Card de Performance em `cards/{vertical}/`
- Input normalizado para kebab-case lowercase

## [1.2.0] - 2026-03-17

### Added

#### WBR Narrativo (E6)
- Novo output `wbr/wbr-narrativo-{vertical}-{data}.md` — prosa executiva complementar ao WBR estruturado
- 7 secoes narrativas: Manchete, Panorama, O que Preocupa, O que Estamos Fazendo, Para Onde Estamos Indo, O que Precisa Acontecer, Destaques Positivos
- Template `wbr-narrativo.tmpl.md` com instrucoes por secao e regras de escrita
- Secao "WBR Narrativo" no reference `wbr-structure.md` com principios de escrita narrativa (prosa-primeiro, comparativos obrigatorios, causa-raiz como historia, decisoes > problemas, reconhecimento por nome)
- Fase 6 na skill `consolidating-wbr` para geracao do narrativo apos validacao do estruturado
- Exit criteria atualizados: ambos os artefatos (estruturado + narrativo) obrigatorios

### Design Decisions
- WBR Narrativo complementa (nao substitui) o WBR Estruturado — o estruturado permanece como fonte de verdade numerica
- Extensao alvo: 600-1000 palavras (1.5-2.5 paginas) — leitura de 3 minutos
- Fluxo Situacao → Complicacao → Acao → Perspectiva para maximizar acionabilidade
- Destaques Positivos como secao obrigatoria para reforco comportamental

## [1.1.0] - 2026-03-17

### Changed

#### Estrutura de Pastas do Ciclo (Issues 1, 2, 5)
- Pasta do ciclo renomeada de `YYYY-Www` para `YYYY-MM-DD` (data de execucao)
- Artefatos reorganizados em subpastas semanticas: `dados/`, `data-quality/`, `analise/`, `wbr/`
- Data Quality Report movido para `data-quality/data-quality-report.md` (antes em `output/`)
- Dados consolidados movidos para `dados/dados-consolidados-{vertical}.json`
- Dados brutos de cada query agora persistidos em `dados/raw/{indicator_id}_{source}.json`
- Relatorios de analise (E3-E5) movidos para `analise/`
- WBR movido para `wbr/`

#### CICLO.md como Changelog (Issue 3)
- CICLO.md agora armazenado visivelmente na pasta do ciclo (`{vertical}/YYYY-MM-DD/CICLO.md`)
- Adicionadas 3 secoes de changelog: **Log de Execucao**, **Anomalias**, **Decisoes**
- Cada entrada registra timestamp, autor (AGENTE:nome, SISTEMA ou USUARIO) e descricao
- Agents e commands agora fazem append ao CICLO.md durante execucao

#### Fail-Safe Anti-Fabricacao de Dados (Issue 4)
- Nova secao **FAIL-SAFE** no agent data-collector com precedencia absoluta
- Agent deve PARAR imediatamente em caso de falha de MCP, registrar erro e AGUARDAR decisao do usuario
- Proibicoes absolutas contra dados sinteticos, placeholders e "exemplos ilustrativos"
- Anti-patterns reforçados na skill collecting-data

#### Verificacao de MCPs (Issue complementar)
- Nova **Fase 0** na skill collecting-data: verifica acessibilidade de ClickHouse e Bitrix24 ANTES de qualquer coleta
- Novo **step 0** no agent data-collector: testa conexao com ambos MCPs antes de executar queries
- Falha de MCP apresenta opcoes ao usuario ao inves de tentar contornar

### Fixed
- Paths de artefatos atualizados em todos os 14 arquivos do plugin (commands, skills, agents, templates)
- Remocao de todas as referencias ao formato `YYYY-Www` e paths genericos `output/`

## [1.0.0] - 2026-03-16

### Added

#### Plugin Infrastructure
- Plugin manifest (`plugin.json`) com 6 skills, 2 agents e 3 commands
- MCP config (`.mcp.json`) com ClickHouse (m7bronze) e Bitrix24 CRM
- Marketplace entry (categoria: performance-management)
- README.md com pipeline semanal E1-E6, composicao e dependencias

#### Skills — Implementadas
- **configuring-cards** (E1): Criacao e validacao de Cards de Performance YAML com KPIs, arvore de indicadores e logica de analise. Inclui schema ESP-PERF-002, naming conventions e templates
- **collecting-data** (E2): Coleta de indicadores via ClickHouse/Bitrix24 MCP com validacao de qualidade (completude >95%, duplicatas, defasagem <24h, quality_checks). Gera Data Quality Report com alertas por severidade (Critico/Atencao/Informativo). Alertas criticos bloqueiam pipeline
- **analyzing-deviations** (E3): Analise de desvios com metodologia GPD/Falconi — classificacao semaforo (Verde/Amarelo/Vermelho), analise de fenomeno em 5 dimensoes (O QUE/QUANDO/ONDE/QUEM/TENDENCIA), inferencia de causa-raiz com niveis de confianca (Alta/Media/Baixa). Inclui referencia completa de metodologia e arvore de decisao
- **summarizing-actions** (E4): Acompanhamento de contramedidas do plano de acao (plano-de-acao.csv, 24 campos). Classificacao por urgencia, avaliacao de efetividade
- **projecting-results** (E5): Projecao de atingimento de meta com 4 metodos estatisticos (run-rate linear, media movel ponderada, Holt-Winters, conversao de funis CRM). Consolidacao por mediana, classificacao de probabilidade (Provavel/Possivel/Improvavel), cenarios P10/P90, calculo de gap e ritmo necessario. Inclui referencia completa de metodologia com formulas e exemplos
- **consolidating-wbr** (E6): Consolidacao do Weekly Business Report com 5 secoes (semaforo, desvios, acoes, projecoes, decisoes). Inclui referencia de estrutura WBR

#### Agents
- **data-collector**: Agente de coleta via ClickHouse e Bitrix24 MCP (model: sonnet). Tools: Read, Write, Bash, Grep, Glob. Principio: "Quem coleta NAO analisa"
- **analyst**: Agente analista de performance para E3-E6 (model: opus). Tools: Read, Write, Grep, Glob. Principio: "Quem analisa NAO coleta"

#### Commands
- **next** (`/m7-controle:next`): Avanca para proxima etapa do ciclo verificando entry criteria
- **status** (`/m7-controle:status`): Mostra progresso do ciclo via CICLO.md
- **run-weekly** (`/m7-controle:run-weekly <vertical>`): Executa pipeline completo E2-E6

#### Specifications
- Especificacoes completas em `.claude/specs/m7-artifacts/m7-controle/`:
  - PLG-01 (plugin overview), SKL-01 a SKL-05 + SKL-08 (skills), AGT-01/02 (agents), CMD-01 a CMD-03 (commands)

### Design Decisions
- Separacao estrita de agentes: data-collector (coleta) vs analyst (analise) — misturar degrada qualidade
- Biblioteca de Indicadores e Cards de Performance como dependencias externas do repositorio do usuario, nao internas ao plugin
- State management via CICLO.md com timestamps e artifact paths
- Quality gates: alertas criticos em E2 bloqueiam avanço para E3
