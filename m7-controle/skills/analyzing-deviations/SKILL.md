---
name: analyzing-deviations
description: >-
  G2.2-E3: Analisa desvios entre realizado e meta, estratifica por dimensoes (O QUE, QUANDO,
  ONDE, QUEM, TENDENCIA) e infere causas-raiz usando cadeia causa-efeito da Biblioteca de
  Indicadores. Segue metodologia GPD/Falconi. Use when the pipeline advances to E3 after
  data collection (E2), when /m7-controle:next reaches E3, or when /m7-controle:run-weekly
  executes the analysis step.

  <example>
  Context: E2 concluido sem alertas criticos, pipeline avanca
  user: "/m7-controle:next"
  assistant: Invoca analyst para classificar indicadores e analisar desvios com causa-raiz
  </example>

  <example>
  Context: Usuario quer entender desvios de uma vertical
  user: "Analisa os desvios de Investimentos dessa semana"
  assistant: Le dados consolidados de E2, classifica semaforo e executa analise de fenomeno para Vermelhos
  </example>
user-invocable: false
---

# Analyzing Deviations — Analise de Desvios e Causa-Raiz (E3)

> "Nao basta saber que desviou. Precisa saber O QUE, QUANDO, ONDE, QUEM e para onde vai."

Esta skill identifica desvios entre realizado e meta, estratifica por dimensoes relevantes e infere causas-raiz utilizando a cadeia causa-efeito da Biblioteca de Indicadores. Produz diagnostico estruturado seguindo a metodologia GPD/Falconi (analise de fenomeno).

> **REGRA DE HANDOFF**: Ao invocar o agente analyst, NAO passe valores de dados no texto do prompt. Passe APENAS caminhos de arquivos (vertical, cycle folder, paths dos artefatos). O analyst deve usar Read tool para carregar os dados dos arquivos em disco.

## Dependencias Internas

- [references/analysis-methodology.md](references/analysis-methodology.md) — Metodologia GPD/Falconi, regras de inferencia e niveis de confianca
- [templates/deviation-report.tmpl.md](templates/deviation-report.tmpl.md) — Template do Relatorio de Desvios e Causa-Raiz
- Agent `analyst` — Executor da analise (invocado automaticamente)
- Output de E2: `dados/dados-consolidados-{vertical}.json` (na pasta do ciclo)

> **Resolucao de caminhos**: O campo `analysis_guide`, `explanatory_context` e `investigation_playbook` vem dos YAMLs da Biblioteca de Indicadores no repositorio do usuario. Localizar via `Glob('**/indicators/_index.yaml')`.

## Pre-requisitos (Entry Criteria)

- E2 concluido sem alertas criticos (verificar `data-quality/data-quality-report.md` na pasta do ciclo)
- Dados consolidados disponiveis em `dados/dados-consolidados-{vertical}.json` (na pasta do ciclo)
- Biblioteca de Indicadores acessivel com campos `analysis_guide` e `investigation_playbook`
- Cards de Performance da vertical acessiveis (para ler `kpis_analisar_como_contexto`)

## Workflow

### Fase 0 — Contexto Temporal

Ler `periodo`, `granularidade` e `checkpoint_label` do CICLO.md. A analise temporal (QUANDO, TENDENCIA) deve ser enquadrada como `{checkpoint_label}` — ex: "Marco 2026, semana 4 (MTD)", NAO "semana 12 do ano" ou "primeira semana de marco". Os dados refletem o mes inteiro ate a data do checkpoint.

### Fase 1 — Classificar Semaforo

Para cada indicador nos dados consolidados, comparar `realizado` vs `meta`:

| Classificacao | Criterio | Acao |
|---------------|----------|------|
| **Verde** | >= 95% da meta | Registro breve (destaque se era Vermelho no ciclo anterior) |
| **Amarelo** | 80-94% da meta | Analise simplificada (tendencia + contexto) |
| **Vermelho** | < 80% da meta | Analise de fenomeno completa (5 dimensoes) |

> **REGRA CRITICA**: O semaforo classifica o INDICADOR AGREGADO (N1) contra sua META FORMAL. A performance INDIVIDUAL de um assessor NAO afeta o semaforo — mesmo que um assessor esteja a 0%, se o agregado esta a 105%, o indicador e Verde. Concentracao de resultado em poucos individuos e um RISCO OPERACIONAL reportado separadamente na dimensao QUEM/ONDE, nunca um fator de reclassificacao do semaforo.
>
> Exemplo correto: Volume N1 a 105% = Verde, mesmo que Tereza esta a 0% e Douglas a 175%.
> Exemplo incorreto: Douglas "reclassificado" como Vermelho por "concentracao excessiva".

**Output Fase 1:** Tabela-semaforo com todos os indicadores classificados.

### Fase 2 — Analise de Fenomeno (Vermelhos)

Para cada indicador **Vermelho**, executar as 5 dimensoes da analise de fenomeno GPD/Falconi:

1. **O QUE**: Qual indicador desviou, gap absoluto e percentual
2. **QUANDO**: Em que periodo o desvio se intensificou (comparar MoM, WoW usando campo `historico`)
3. **ONDE**: Em que segmento o desvio e maior (usar `segmentation_dimensions` do YAML — equipe, produto, canal)
4. **QUEM**: Quais assessores/gestores concentram o desvio (usar campo `quebras` dos dados consolidados)
5. **TENDENCIA**: O desvio esta piorando, estavel ou melhorando (comparar ultimas 3-4 semanas)

Para detalhes da metodologia e regras de estratificacao, consultar [analysis-methodology.md](references/analysis-methodology.md).

### Fase 2.1 — Segmentacao "Sem Atribuicao"

Ao estratificar por dimensao QUEM/ONDE, verificar se existe bucket de dados nao atribuidos:

1. Filtrar por: assessor = NULL, "Sem Especialista", "Nao Atribuido", "(vazio)", "Outros"
2. Se valor > 0 neste bucket:
   - Reportar como segmento separado: `"Sem Especialista: R$ X ({pct}% do total N1)"`
   - Se > 5% do total N1: destacar como **risco operacional** (receita nao gerenciada)
   - NAO excluir do calculo do indicador N1 (faz parte do realizado total)
   - Registrar em CICLO.md > Decisoes se a atribuicao precisa ser corrigida na fonte (ex: deals sem owner no Bitrix24)
3. Se valor = 0: nao mencionar

> Dados nao atribuidos sao comuns em verticais com contratos legados (ex: Bancorbras em Consorcios).
> O analyst deve SEMPRE reporta-los explicitamente — nunca agrupa-los silenciosamente em "outros".

### Fase 2.5 — Enriquecer com Indicadores de Contexto (PPIs)

1. **Ler o Card de Performance** da vertical via `Glob('**/cards/{vertical}/*.yaml')`
2. **Extrair `logica_de_analise.kpis_analisar_como_contexto`** — lista de indicator_ids com racionais
3. **Para cada PPI listado**, ler os dados correspondentes de `dados/dados-consolidados-{vertical}.json`
4. **Usar o campo `racional` de cada PPI** para guiar a interpretacao:
   - O racional diz COMO o PPI se relaciona com os KPIs em desvio
   - Exemplo: se Volume esta Vermelho, o racional de `taxa_conversao_funil_con` instrui a verificar se o problema e de conversao ou de entrada no funil
5. **Para cada KPI Vermelho**, cruzar com os PPIs relevantes:
   - Se PPI de funil mostra pipeline vazio → causa-raiz: retracao de prospeccao
   - Se PPI de funil mostra pipeline cheio mas conversao baixa → causa-raiz: gargalo de fechamento
   - Se PPI de estagnacao mostra deals parados → causa-raiz: funil travado
   - Se quantidade OK mas volume baixo → causa-raiz: mudanca de mix (ticket menor)
6. **Incorporar achados** como evidencias na Fase 3 (elevam confianca da hipotese)

> Os PPIs enriquecem a causa-raiz mas NAO recebem classificacao semaforo propria
> (nao tem meta formal). Sao usados como evidencia diagnostica.

### Fase 3 — Inferencia de Causa-Raiz (Vermelhos)

Para cada indicador Vermelho, inferir causas seguindo esta sequencia:

1. **Correlacao**: Percorrer `related_indicators` do YAML — se indicador correlacionado tambem esta vermelho, hipotese de causa compartilhada
2. **Segmentacao**: Aplicar `segmentation_dimensions` — identificar dimensao com maior `diagnostic_value`
3. **Investigation playbook**: Seguir os `steps` do campo `investigation_playbook` do YAML em sequencia
4. **Gerar hipoteses** com nivel de confianca:

| Confianca | Criterio |
|-----------|----------|
| **Alta** | Suportada por 2+ evidencias (correlacao + segmentacao + dados historicos) |
| **Media** | Suportada por 1 evidencia direta |
| **Baixa** | Inferencia sem evidencia direta nos dados |

### Fase 4 — Analise Simplificada (Amarelos)

Para indicadores **Amarelos**:
- Tendencia (melhorando/piorando) com base em `historico`
- Contexto do campo `analysis_guide` do YAML
- Se o indicador estava Verde no ciclo anterior, destacar a piora

### Fase 5 — Destaques Positivos (Verdes)

Para indicadores **Verdes**:
- Registro breve: indicador + % de atingimento
- Se estava Vermelho/Amarelo no ciclo anterior, destacar a recuperacao
- Se superou meta em >10%, destacar como benchmark

### Fase 6 — Gerar Output

Gerar `analise/deviation-cause-report.md` (na pasta do ciclo) seguindo o [template](templates/deviation-report.tmpl.md).

## Exit Criteria

- [ ] Relatorio de Desvios e Causa-Raiz gerado em `analise/deviation-cause-report.md` (na pasta do ciclo)
- [ ] 100% dos indicadores classificados no semaforo (Verde/Amarelo/Vermelho)
- [ ] Analise de fenomeno completa (5 dimensoes) para cada Vermelho
- [ ] Pelo menos 1 hipotese de causa-raiz com nivel de confianca para cada Vermelho
- [ ] Hipoteses especificas e baseadas em dados (nao genericas)
- [ ] PPIs de `kpis_analisar_como_contexto` do Card consultados e incorporados na analise (ou motivo de exclusao registrado)

## Anti-Patterns

- NUNCA use causas genericas como "mercado dificil", "sazonalidade" sem evidencia nos dados
- NUNCA pule a analise de fenomeno para indicadores Vermelhos — todas as 5 dimensoes sao obrigatorias
- NUNCA invente dados de segmentacao — use apenas o que esta nos dados consolidados e quebras
- NUNCA sugira acoes corretivas detalhadas — isso e responsabilidade de E4 (summarizing-actions)
- NUNCA ignore indicadores Verdes que eram Vermelhos — a recuperacao e informacao valiosa
