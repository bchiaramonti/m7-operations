---
name: summarizing-actions
description: >-
  G2.2-E4: Le plano-de-acao.csv, filtra acoes da vertical, calcula aging e classifica por
  urgencia (Em dia / Atrasada / Critica), avalia eficacia das concluidas cruzando com dados
  de E2, e gera Relatorio de Acompanhamento de Acoes com metricas agregadas. Use when the
  pipeline advances to E4 after deviation analysis (E3), when /m7-controle:next reaches E4,
  or when /m7-controle:run-weekly executes the action tracking step.

  <example>
  Context: E3 concluido, pipeline avanca para acompanhamento de acoes
  user: "/m7-controle:next"
  assistant: Invoca analyst para ler plano-de-acao.csv, calcular aging e gerar relatorio de acoes
  </example>

  <example>
  Context: Usuario quer ver o status das acoes de uma vertical
  user: "Como estao as acoes de Investimentos?"
  assistant: Le o CSV, filtra por vertical, classifica por urgencia e gera relatorio com metricas
  </example>
user-invocable: false
---

# Summarizing Actions — Acompanhamento de Acoes (E4)

> "Acao sem prazo e intencao. Acao atrasada sem escalonamento e negligencia."

Esta skill le o plano-de-acao.csv, filtra acoes da vertical em andamento, calcula aging e dias restantes, classifica por urgencia, avalia eficacia das concluidas e gera relatorio de acompanhamento com metricas agregadas. E a quarta etapa do pipeline semanal (E4).

> **REGRA DE HANDOFF**: Ao invocar o agente analyst, NAO passe valores de dados no texto do prompt. Passe APENAS caminhos de arquivos (vertical, cycle folder, paths dos artefatos). O analyst deve usar Read tool para carregar os dados dos arquivos em disco.

## Dependencias Internas

- [templates/action-report.tmpl.md](templates/action-report.tmpl.md) — Template do Relatorio de Acompanhamento de Acoes
- Agent `analyst` — Executor da analise (invocado automaticamente)
- Output de E2: `dados/dados-consolidados-{vertical}.json` (na pasta do ciclo, para cruzamento de eficacia)
- Output de E3: `analise/deviation-cause-report.md` (na pasta do ciclo, contexto de desvios)

> **Resolucao de caminhos**: O `plano-de-acao.csv` fica no diretorio `03-implementacao/` do repositorio do usuario. Localizar via `Glob('**/03-implementacao/plano-de-acao.csv')`. Parametros do ciclo vem de `CICLO.md`.

## Pre-requisitos (Entry Criteria)

- E3 concluido (verificar `analise/deviation-cause-report.md` na pasta do ciclo)
- `plano-de-acao.csv` acessivel em `03-implementacao/` no repositorio do usuario
- CICLO.md com `vertical` e `data_referencia` definidos

## Workflow

### Fase 1 — Ler e Filtrar CSV

1. **Localizar CSV** via `Glob('**/03-implementacao/plano-de-acao.csv')`
2. **Ler arquivo completo** respeitando encoding (UTF-8 ou Latin-1) e delimitador (`;` ou `,`)
3. **Tratar campo `comentarios`**: contem JSON inline — parsear como string JSON se presente
4. **Filtrar** usando criterio OR para capturar acoes cross-vertical:
   - **(a)** `vertical` = vertical do ciclo ativo em CICLO.md
   - **(b)** OU `indicador_impactado` contem algum indicator_id referenciado pelo Card da vertical

   Para aplicar o criterio (b):
   - Ler o Card de Performance da vertical via `Glob('**/cards/{vertical}/*.yaml')`
   - Extrair todos os indicator_ids de `kpi_references` e `kpis_analisar_como_contexto`
   - Verificar se o campo `indicador_impactado` do CSV contem algum desses IDs

   Registrar no output quantas acoes vieram do criterio (a) vs (b) para transparencia.
   Exemplo: "12 acoes encontradas: 10 por vertical, 2 por indicador_impactado cross-vertical"

5. **Validar**: se 0 acoes encontradas por ambos os criterios, gerar relatorio vazio com metricas zeradas

**Campos-chave do CSV (24 campos, referencia Secao 7.1 ARQ-COWORK-001):**
`id`, `parent_id`, `vertical`, `titulo`, `responsavel`, `prioridade`, `data_cadastro`, `data_limite`, `status`, `percentual`, `indicador_impactado`, `volume`, `receita`

**Output Fase 1:** Dataset filtrado por vertical com todos os 24 campos preservados.

### Fase 2 — Separar por Status e Calcular Aging

Separar acoes por `status`: `pendente`, `em_andamento`, `concluida`, `cancelada`.

Para acoes **pendentes** e **em_andamento**:

1. **Aging** = `data_referencia` - `data_cadastro` (dias corridos)
2. **Dias restantes** = `data_limite` - `data_referencia` (dias corridos)
3. **Classificar urgencia:**

| Classificacao | Criterio (dias_restantes) | Acao |
|---------------|---------------------------|------|
| **Em dia** | > 0 | Monitoramento normal |
| **Atrasada** | 0 a -7 | Alerta ao responsavel |
| **Critica** | < -7 | Requer escalonamento imediato |

**Tratamento de campos monetarios:** `volume` e `receita` podem conter "R$", separadores de milhar ou estar vazios. Extrair valor numerico; tratar vazio como 0.

**Output Fase 2:** Acoes ativas classificadas com aging e dias_restantes calculados.

### Fase 3 — Avaliar Eficacia das Concluidas

Para acoes com status `concluida` no periodo do ciclo:

1. **Identificar** o `indicador_impactado` de cada acao
2. **Cruzar** com dados consolidados de E2 (`dados/dados-consolidados-{vertical}.json` na pasta do ciclo)
3. **Verificar** se o indicador voltou a meta apos a conclusao da acao
4. **Classificar eficacia:**

| Eficacia | Criterio |
|----------|----------|
| **Eficaz** | Indicador voltou a >= 95% da meta |
| **Parcial** | Indicador melhorou mas permanece < 95% da meta |
| **Sem efeito** | Indicador nao melhorou ou piorou |

Se dados de E2 nao estao disponiveis para o indicador, registrar como "Dados insuficientes".

**Output Fase 3:** Tabela de eficacia das acoes concluidas.

### Fase 4 — Identificar Hierarquia e Impacto

1. **Hierarquia**: Acoes com `parent_id` preenchido sao sub-acoes (hotlists). Agrupar sob acao-pai
2. **Impacto**: Ordenar acoes por `volume` + `receita` projetados (decrescente)
3. **Top 5**: Selecionar as 5 acoes com maior impacto financeiro (independente de status)

**Output Fase 4:** Mapeamento hierarquico e ranking de impacto.

### Fase 5 — Calcular Metricas Agregadas

| Metrica | Formula |
|---------|---------|
| Total de acoes ativas | Count(status IN ['pendente', 'em_andamento']) |
| Taxa de conclusao (30d) | Count(concluidas nos ultimos 30d) / Count(total registradas nos ultimos 30d) × 100 |
| Acoes criticas | Count(dias_restantes < -7) |
| % de acoes criticas | Acoes criticas / Total ativas × 100 |
| Aging medio | Avg(aging) das ativas |
| Volume em risco | Sum(volume) das acoes criticas |
| Receita em risco | Sum(receita) das acoes criticas |

### Fase 6 — Gerar Output

Gerar `analise/action-report.md` (na pasta do ciclo) seguindo o [template](templates/action-report.tmpl.md).

O relatorio deve ser **auto-contido** — legivel sem necessidade de consultar o CSV original.

## Exit Criteria

- [ ] Relatorio de Acompanhamento de Acoes gerado em `analise/action-report.md` (na pasta do ciclo)
- [ ] Metricas agregadas calculadas (taxa conclusao, aging medio, % criticas, volume/receita em risco)
- [ ] Todas as acoes ativas classificadas (Em dia / Atrasada / Critica)
- [ ] Eficacia avaliada para acoes concluidas no periodo (quando dados de E2 disponiveis)
- [ ] Hierarquia parent_id respeitada no agrupamento

## Anti-Patterns

- NUNCA sugira contramedidas ou novas acoes — isso e responsabilidade de E6 (consolidating-wbr)
- NUNCA ignore acoes com campos `volume`/`receita` vazios — tratar como 0, nao excluir
- NUNCA some percentuais entre acoes diferentes — percentual e individual por acao
- NUNCA altere o plano-de-acao.csv — o relatorio e read-only sobre os dados
- NUNCA gere relatorio sem calcular aging — mesmo que todas as acoes estejam em dia
- NUNCA ignore acoes com parent_id — a hierarquia hotlist e informacao essencial para escalonamento
