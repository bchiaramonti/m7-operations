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

1. **Ler o Card de Performance** da vertical via `Glob('**/Cards-de-Performance/{Vertical}/card_*.yaml')`
2. **Extrair `kpi_references[]`** — lista completa de indicadores com `papel`, `unidade`, `criterio_desvio_critico`
3. **Para cada indicador**, buscar em `dados/dados-consolidados-{vertical}.json`:
   - Valor realizado (N1 consolidado + desdobrado por especialista N2)
   - Meta (se disponivel)
   - Gap absoluto e percentual
   - Semaforo (verde/amarelo/vermelho/cinza)
4. **Montar tabela** com formato fixo:

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

### Fase 5 — Validar e Salvar WBR Estruturado

1. Executar checklist de coerencia (ver [wbr-structure.md](references/wbr-structure.md))
2. Salvar `wbr/wbr-{vertical}-{data}.md` (na pasta do ciclo)

### Fase 6 — Gerar WBR Narrativo

Com base no WBR Estruturado ja validado, gerar o WBR Narrativo seguindo o [template](templates/wbr-narrativo.tmpl.md) e as [regras de escrita narrativa](references/wbr-structure.md#wbr-narrativo--estrutura-e-regras).

O WBR Narrativo reutiliza **exatamente os mesmos numeros** do WBR Estruturado, mas apresenta-os como prosa executiva com fluxo Situacao → Complicacao → Acao → Perspectiva.

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

Com base no WBR Estruturado e no WBR Narrativo MD ja validados, gerar a versao HTML visual seguindo o [template](templates/wbr-narrativo.tmpl.html) e o [guia de geracao HTML](references/wbr-html-guide.md).

O WBR Narrativo HTML reutiliza **exatamente os mesmos numeros** dos outputs anteriores, mas apresenta-os com:
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

### Fase 8 — Finalizar

1. Atualizar CICLO.md com status "concluido" para E6
2. Registrar os quatro artefatos no CICLO.md (WBR Estruturado .md, WBR Narrativo .md, WBR Narrativo .html, WBR Narrativo .pdf)

## Exit Criteria

- [ ] WBR Estruturado gerado com 6 secoes obrigatorias presentes e nao vazias (incluindo 1.5 Painel)
- [ ] Painel de Indicadores (Secao 1.5) contem TODOS os indicadores do Card de Performance
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
