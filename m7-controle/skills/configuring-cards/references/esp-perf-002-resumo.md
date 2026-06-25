# ESP-PERF-002 — Resumo de Regras para Cards de Performance

> Referencia: ESP-PERF-002 v1.3, Secao 6.5
> Versao anterior: v1.2 (2026-05-06)
> Atualizado 2026-05-11: Regra 10 expandida (PJ2); +4 regras (13-16) para Cards multi-canal multi-vertical (PJ2). Campos opcionais multi-canal documentados.

## Indice

1. [12 Regras de Validacao](#12-regras-de-validacao)
2. [Aditividade](#aditividade)
3. [Ciclo de Vida](#ciclo-de-vida)
4. [Correlacoes](#correlacoes)
5. [Pipeline de Execucao](#pipeline-de-execucao)
6. [Campos opcionais (m7-ritual-gestao integration)](#campos-opcionais-m7-ritual-gestao-integration)

---

## 12 Regras de Validacao

Estas regras devem ser verificadas no Modo 2 (Validar). Issues sao classificadas como **CRITICO** (bloqueia ativacao), **ATENCAO** (nao bloqueia) ou **OK**.

| # | Regra | Severidade se falha |
|---|-------|---------------------|
| 1 | `id` em snake_case e correspondente ao nome do arquivo (sem `.yaml`) | CRITICO |
| 2 | Todos os `indicator_id` referenciados existem na Biblioteca de Indicadores | CRITICO |
| 3 | Indicadores com status `a_mapear` nao podem estar em Cards com status `active` | CRITICO |
| 4 | `kpis_analisar_juntos` + `kpis_analisar_separados` cobrem todos os `kpi_principal` | CRITICO |
| 5 | Cada `sequencia_analise` tem minimo 3 passos com `step`, `acao`, `pergunta_chave` | CRITICO |
| 6 | `quebras_obrigatorias` existem como colunas nas queries dos indicadores referenciados | ATENCAO |
| 7 | Correlacoes sao bidirecionais (se A declara B, B deve declarar A) | ATENCAO |
| 8 | `conteudo_obrigatorio` referencia KPIs presentes no Card | ATENCAO |
| 9 | `codigo` em UPPERCASE com hifens, derivavel do `id` (substituir `_` por `-`, uppercase) | CRITICO |
| 10 | `vertical_code` valido: INV, CRE, UNI, SEG, **PJ2** (v1.3) | CRITICO |
| 11 | `nivel` valido: N1, N2, N3, N4 | CRITICO |
| 12 | `subnivel` consistente entre `id` e `codigo` (se presente em um, deve estar no outro) | ATENCAO |
| 13 | Se `metadata.label_responsavel == "canal"`, cada `apresentacao.responsaveis[].id` deve estar declarado (canal_id obrigatorio) | CRITICO |
| 14 | Se `metadata.label_responsavel == "sub_bloco"`, ao menos 1 `apresentacao.responsaveis[].sub_blocos` preenchido | CRITICO |
| 15 | Se algum `matrix_views[].column_axis == "canal"`, `column_order` deve ser declarado nao-vazio | CRITICO |
| 16 | Se `metadata.verticais` declarado (multi-vertical), `vertical_code` deve ser umbrella (PJ2) e nao single (INV/CRE/UNI/SEG) | ATENCAO |

### Formato do relatorio de validacao

Para cada regra, reportar:

```
| # | Regra | Status | Detalhe |
|---|-------|--------|---------|
| 1 | ID em snake_case | OK | card_inv_n1_001 corresponde ao arquivo |
| 2 | indicator_ids validos | CRITICO | captacao_liquida_mensal nao encontrado na Biblioteca |
```

---

## Aditividade

A classificacao de `tipo_realizacao` determina como valores sao agregados entre niveis hierarquicos (N4 → N3 → N2 → N1).

| Tipo | Regra de Agregacao | Exemplo |
|------|-------------------|---------|
| **aditivo** | N1 = SUM(N4) para realizado E meta | Captacao Liquida (R$), Volume de Deals |
| **nao_aditivo** | N1 ≠ SUM(N4). Usar AVG, MAX ou recalcular por formula propria | IEA (score), NPS |
| **parcialmente_aditivo** | Contagens sao aditivas; percentuais derivados dos sums | Rentabilidade: pct = SUM(abaixo_bench)/SUM(total) |

### Regra Critica

**NUNCA somar percentuais entre assessores.** Percentuais de indicadores `parcialmente_aditivo` devem ser recalculados a partir das contagens agregadas.

Exemplo correto:
```
Assessor A: 3/10 = 30%
Assessor B: 7/10 = 70%
Equipe: (3+7)/(10+10) = 50%   ← CORRETO (recalcula)
Equipe: (30%+70%)/2 = 50%     ← ERRADO (coincidencia neste caso, falha em geral)
```

### Campos de regras_meta

Para cada KPI, `regras_meta` pode conter:
- `tipo_agregacao`: sum | avg | max | recalcular
- `formula_agregacao`: expressao customizada se `recalcular`
- `peso`: peso para media ponderada (se avg)

---

## Ciclo de Vida

| Status | Pode transicionar para | Condicao |
|--------|----------------------|----------|
| `draft` | `active` | Todos os `kpi_references` com `indicator_id` valido; `sequencia_analise` definida; validacao sem CRITICO |
| `active` | `archived` | Motivo registrado: substituido por nova versao OU area desativada |
| `archived` | (terminal) | Manter para rastreabilidade. **Nunca deletar** |

### Versionamento

- **MAJOR** (1.0.0 → 2.0.0): Mudanca estrutural (remocao de KPI principal, reestruturacao de arvore)
- **MINOR** (1.0.0 → 1.1.0): Adicao de KPI, novo grupo em logica_de_analise
- **PATCH** (1.0.0 → 1.0.1): Ajuste de descricao, parametro, criterio_desvio_critico

---

## Correlacoes

Correlacoes entre KPIs devem ser **bidirecionais** e tipadas:

| Tipo | Significado | Exemplo |
|------|-------------|---------|
| **direta** | Sobem e descem juntos | Captacao e AuM |
| **inversa** | Um sobe quando o outro desce | Resgates e Retencao |
| **contexto** | Consultado condicionalmente, sem relacao causal | Selic e Captacao |

Se o Card de A declara correlacao com B:
1. Verificar se o Card de B (ou o indicador B) tambem declara correlacao com A
2. Se nao, registrar como issue ATENCAO na validacao

---

## Pipeline de Execucao (parametros_execucao)

O pipeline de 7 passos e fixo conforme ESP-PERF-002. Cada Card herda esta sequencia:

| Passo | Nome | Descricao | Gate? |
|-------|------|-----------|-------|
| 1 | Coleta | Executar scripts dos indicadores via collect.py (ClickHouse/Bitrix24 direto) | Nao |
| 2 | Validacao de Qualidade | quality_checks + checks de aditividade | **Sim** — bloqueia se falhar |
| 3 | Calculo de Metricas Derivadas | Acumulados YTD, comparativos MoM, percentuais derivados | Nao |
| 4 | Analise Correlacional | Executar sequencia_analise dos kpis_analisar_juntos | Nao |
| 5 | Analise Independente | Executar sequencia_analise dos kpis_analisar_separados | Nao |
| 6 | Geracao do Relatorio | Montar WBR/MBR conforme formato e conteudo_obrigatorio | Nao |
| 7 | Distribuicao | Enviar conforme canal e destinatarios | Nao |

O Passo 2 e um gate: se a validacao de qualidade falha (alertas criticos), o pipeline nao avanca para Passo 3+.

---

## Campos opcionais (m7-ritual-gestao integration)

Adicionado em ESP-PERF-002 v1.2 (2026-05-06).

Cards podem declarar campos OPCIONAIS adicionais consumidos pelo plugin
`m7-ritual-gestao` (skill `preparing-materials`, script `build_deck.py`)
para customizar deck e briefing **sem editar HTML output**. Backward compat:
campos ausentes = comportamento legado padrao.

**Schema completo (autoritativo):**
- `m7-operations/m7-ritual-gestao/skills/preparing-materials/references/card-apresentacao-schema.md`

**Categorias de campos:**

| Bloco | Onde | Proposito |
|-------|------|-----------|
| `metadata.total_label` | Card.metadata | Label da linha N1 no deck (Slide 3) |
| `metadata.responsaveis_n2` | Card.metadata | Lista oficial de N2 (whitelist) |
| `metadata.assessor_aliases` | Card.metadata | Mapa nome canonico -> aliases |
| `metadata.responsavel_externo_aliases` | Card.metadata | Owner multi-name de tasks |
| `kpi_references[].matrix_views[]` | Card.kpi_references | Declarativo de rows da Matriz com `label`, `value_field`, `meta_field`, `direction`, `compute`, `derived_indicator_id`, `color_inherit_from_view`, `no_meta`, `sem_esp_ratio` |
| `kpi_references[].projecao.*.componentes` | Card.kpi_references | Componentes formais da projecao com `nome`, `tipo`, `formula`, `descricao`, `confianca`, `obrigatorio`, `aplicavel_em`, `inputs[]` |
| `apresentacao.responsaveis[].squad` | Card.apresentacao | Whitelist de assessores oficiais por especialista |
| `apresentacao.projecao_proximo_mes` | Card.apresentacao | Projecao M+1 quando Card v6.x ainda nao calcula |
| `apresentacao.projection_overrides` | Card.apresentacao | Override de projecoes com `metodo` versionado (ex: bug fix) |
| `apresentacao.overrides_ritual` | Card.apresentacao | Override de realizado por bug bridge SQL upstream |
| `apresentacao.suppress_in_ritual` | Card.apresentacao | Filtros para Slide 12 (anomalias / destaques / recomendacoes) |
| `apresentacao.destaques_positivos_custom` | Card.apresentacao | Prepended em wbr.destaques (alta prioridade) |
| `apresentacao.anomalias_custom` | Card.apresentacao | Prepended em wbr.anomalias |
| `apresentacao.recomendacoes_custom` | Card.apresentacao | Prepended em wbr.recomendacoes |
| `apresentacao.pa_manual_append` | Card.apresentacao | Tasks manuais adicionadas no Slide 5 PA |

**Ordem de aplicacao no script build_deck.py:**
1. `_apply_card_overrides` (carrega Card e aplica overrides_ritual + projection_overrides em-place no JSON).
2. `_apply_n5_overrides` (n5_by_esp por assessor).
3. Render dos slides com overrides ja aplicados.
4. `responsavel_externo_aliases` + `pa_manual_append` na renderizacao do Slide 5.
5. `*_custom` (destaques/anomalias/recomendacoes) prepended antes de `suppress_in_ritual` filtrar.

**Exemplo pratico:**
- `card_con_n3_001.yaml` v2.8.0 (Consorcios — todos os campos)
- `card_seg_wl_n3_001.yaml` v2.14.0 + `card_seg_re_n3_001.yaml` v1.6.0 (Seguros — subset)

**Validacao:** o validator do Modo 2 (Validar) **NAO** rejeita Card por
ausencia destes campos (todos sao opcionais). Quando presentes, deve validar
que valores sao internamente consistentes (ex: `n2_value_field` referenciado
existe no JSON do indicador).

---

## Campos opcionais multi-canal multi-vertical (v1.3, 2026-05-11)

Adicionados em ESP-PERF-002 v1.3 para suportar Cards umbrella (PJ2) que agregam
multiplas verticais sob um eixo de canal compartilhado (Inv / Cred / Outros M7).
Schema completo (autoritativo) em:
- `m7-operations/m7-ritual-gestao/skills/preparing-materials/references/card-apresentacao-schema.md`
- `m7-operations/m7-ritual-gestao/skills/preparing-materials/references/pj2-slide-requirements.md`

**Categorias:**

| Bloco | Onde | Proposito | Quando |
|-------|------|-----------|--------|
| `metadata.label_responsavel` | Card.metadata | Eixo de iteracao do bloco repetido: `especialista` (default) \| `canal` \| `sub_bloco` | Sempre opcional. PJ2 = `canal` |
| `metadata.verticais` | Card.metadata | Lista de verticais que o Card cobre: `[consorcios, seguros]` | Apenas multi-vertical |
| `metadata.modo` (alt: `apresentacao.modo`) | Card.metadata | Modo do deck: `atual` \| `fechamento` \| `combinado` \| `auto` | Override Card → CLI |
| `apresentacao.template` | Card.apresentacao | Template do builder: `default` (ritual.tmpl.html) \| `pj2` (ritual-pj2.tmpl.html — Sessao 5) | Default = `default` |
| `apresentacao.responsaveis[].id` | Card.apresentacao | Canal_id obrigatorio quando label_responsavel=canal: `investimentos` / `credito` / etc | Regra 13 valida |
| `apresentacao.responsaveis[].sub_blocos` | Card.apresentacao | Sub-divisoes do eixo: `B2B`, `B2C`, `Outros` (Card N3 INV) | Regra 14 valida |
| `apresentacao.hidden_in_squad_lists` | Card.apresentacao | Nomes (normalizados) ocultos das listagens visuais | Sem regra valida (lista plana) |
| `apresentacao.outros_m7` | Card.apresentacao | Sub-grupos do canal Outros M7: `{especialistas, coordenador, outros}` | Opcional |
| `apresentacao.metas_split` | Card.apresentacao | Split de meta por canal: `default_method: proporcional_squad`, overrides por indicator com `fixed_ratio` ou `absolute` | Opcional |
| `canal_taxonomia` | Card top-level | Taxonomia compartilhada de canais: `buckets_pareto_5`, `agregados_total_3`, `rollup_bucket_para_agregado`, `de_para_canal_path` | Opcional |
| `kpi_references[].matrix_views[].column_axis` | Card.kpi_references | Eixo de colunas da Matriz: `especialista` (default) \| `canal` | Regra 15 valida column_order |
| `metas_canal` | Card top-level | Override explicito de meta por canal e periodo: `{vertical: {ind_id: {periodo_key: {investimentos, credito, outros_m7}}}}` | Opcional |

**Exemplo pratico:**
- `card_pj2_n2_001.yaml` v1.0.0 (PJ2 — todos os campos novos)
