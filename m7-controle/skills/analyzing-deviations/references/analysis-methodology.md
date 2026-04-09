# Metodologia de Analise — GPD/Falconi + Regras de Inferencia

> Referencia para o agente analyst e a skill analyzing-deviations.
> Define a metodologia de analise de fenomeno, regras de inferencia e niveis de confianca.

---

## Indice

1. [Analise de Fenomeno (GPD/Falconi)](#analise-de-fenomeno-gpdfalconi)
2. [Estratificacao por Dimensoes](#estratificacao-por-dimensoes)
3. [Inferencia de Causa-Raiz](#inferencia-de-causa-raiz)
4. [Niveis de Confianca](#niveis-de-confianca)
5. [Uso dos Campos do YAML](#uso-dos-campos-do-yaml)
6. [Regras de Redacao](#regras-de-redacao)

---

## Analise de Fenomeno (GPD/Falconi)

A analise de fenomeno e o primeiro passo da metodologia GPD (Gerenciamento Pelas Diretrizes) para tratar desvios. O objetivo e **descrever o fenomeno com precisao** antes de investigar causas.

### As 5 Dimensoes

| Dimensao | Pergunta-chave | Fonte de dados |
|----------|---------------|----------------|
| **O QUE** | Qual indicador desviou? Em quanto? | `realizado` vs `meta` dos dados consolidados |
| **QUANDO** | Quando o desvio comecou/intensificou? | Campo `historico` — comparar MoM, WoW |
| **ONDE** | Em que segmento o desvio e maior? | Campo `quebras` + `segmentation_dimensions` do YAML |
| **QUEM** | Quais responsaveis concentram o desvio? | Campo `quebras` por assessor/gestor |
| **TENDENCIA** | O desvio esta piorando, estavel ou melhorando? | Ultimas 3-4 semanas do `historico` |

### Exemplo de Analise de Fenomeno

```
O QUE: Captacao Liquida ficou em R$ 15M vs meta de R$ 25M (-40%)
QUANDO: Desvio se intensificou na semana 10 (era -15% na semana 9)
ONDE: Concentrado no segmento Varejo (responde por 70% do gap)
QUEM: Assessores A e B concentram 45% do gap do segmento Varejo
TENDENCIA: Piorando — 3 semanas consecutivas de queda no ritmo
```

---

## Estratificacao por Dimensoes

### Regra de Pareto

Ao estratificar por qualquer dimensao, aplicar a regra de Pareto:
- Identificar os itens que respondem por **80% do desvio**
- Focar a analise nesses itens (tipicamente 20% do total)
- Listar os demais como "outros" com valor agregado

### Dimensoes de Segmentacao

As dimensoes vem do campo `segmentation_dimensions` do YAML do indicador:

```yaml
segmentation_dimensions:
  - dimension: equipe
    diagnostic_value: high
  - dimension: produto
    diagnostic_value: medium
  - dimension: canal
    diagnostic_value: low
```

**Prioridade de analise**: seguir a ordem de `diagnostic_value` (high > medium > low).

### Calculos de Estratificacao

Para cada dimensao:

```
gap_segmento = realizado_segmento - meta_segmento
contribuicao_gap = gap_segmento / gap_total * 100
```

Apresentar em tabela ordenada por contribuicao ao gap (maior primeiro).

---

## Inferencia de Causa-Raiz

### Sequencia de Investigacao

1. **Correlacao entre indicadores**
   - Ler `related_indicators` do YAML
   - Verificar se indicadores correlacionados tambem estao Vermelhos
   - Se sim: hipotese de causa compartilhada (ex: "queda em captacao bruta E captacao liquida sugere problema na geracao de pipeline, nao em resgates")

2. **Segmentacao diagnostica**
   - Se 1 segmento concentra >60% do gap: causa localizada nesse segmento
   - Se o gap e distribuido uniformemente: causa sistemica (processo, mercado)
   - Se poucos individuos concentram o gap: causa individual (performance, ausencia)

3. **Investigation playbook do YAML**
   - Seguir os `steps` em sequencia — cada step define uma verificacao especifica
   - Exemplo de playbook:
     ```yaml
     investigation_playbook:
       steps:
         - "Comparar MoM e YoY para isolar sazonalidade"
         - "Segmentar por equipe para identificar concentracao"
         - "Drill-down nos top 3 assessores com maior gap"
         - "Verificar pipeline CRM para funil de conversao"
     ```

4. **Explanatory context do YAML**
   - Usar `explanatory_context` como contexto adicional para interpretar os dados
   - Este campo contem conhecimento de dominio que nao esta nos dados (ex: "meta ajustada em marco por mudanca de escopo")

### Arvore de Decisao para Causa-Raiz

```
O desvio e concentrado em poucos segmentos?
├── SIM → Causa localizada
│   ├── Concentrado em poucos individuos?
│   │   ├── SIM → Causa individual (performance, ausencia, carteira)
│   │   └── NAO → Causa de segmento (produto, canal, regiao)
│   └── Indicadores correlacionados tambem vermelhos?
│       ├── SIM → Causa compartilhada (pipeline, processo)
│       └── NAO → Causa especifica deste indicador
└── NAO → Causa sistemica
    ├── Desvio recente (ultimas 2 semanas)?
    │   ├── SIM → Evento pontual (mercado, operacional)
    │   └── NAO → Tendencia estrutural (processo, capacidade)
    └── Padrao sazonal identificado (YoY)?
        ├── SIM → Sazonalidade (com evidencia historica)
        └── NAO → Investigar mudancas de processo/mercado
```

---

## Niveis de Confianca

| Nivel | Criterio | Exemplo |
|-------|----------|---------|
| **Alta** | 2+ evidencias independentes convergem | Correlacao com indicador relacionado + concentracao em 1 segmento + tendencia de piora |
| **Media** | 1 evidencia direta nos dados | Concentracao clara em 1 equipe, mas sem correlacao com outros indicadores |
| **Baixa** | Inferencia logica sem evidencia direta | Hipotese baseada em explanatory_context sem confirmacao nos numeros |

### Regras de Atribuicao

- Confianca **Alta**: requer pelo menos 2 das seguintes evidencias:
  - Correlacao com `related_indicators` (ambos Vermelhos)
  - Concentracao >60% do gap em 1 segmento (Pareto)
  - Tendencia consistente por 3+ periodos
  - Evidencia no `investigation_playbook`

- Confianca **Media**: exatamente 1 evidencia das acima

- Confianca **Baixa**: nenhuma evidencia direta, apenas:
  - Conhecimento de dominio (explanatory_context)
  - Hipotese logica sem dados de suporte
  - Sazonalidade presumida sem comparativo YoY

---

## Uso dos Campos do YAML

| Campo YAML | Uso na Analise |
|------------|---------------|
| `analysis_guide` | Guia geral de como interpretar o indicador — usar como contexto |
| `explanatory_context` | Fatores externos que afetam o indicador — usar para hipoteses |
| `investigation_playbook` | Steps sequenciais de investigacao — seguir na ordem |
| `segmentation_dimensions` | Dimensoes para estratificar — priorizar por `diagnostic_value` |
| `related_indicators` | Indicadores correlacionados — verificar semaforo para correlacao |
| `benchmark` | Referencia de mercado — usar para contextualizar o gap |
| `trend_direction` | Direcao esperada — comparar com tendencia real |

---

## Regras de Redacao

### O que DEVE conter o relatorio

- Numeros absolutos E percentuais (ex: "R$ 15M vs R$ 25M, -40%")
- Comparativos temporais (MoM, WoW, YoY quando disponivel)
- Tabelas de estratificacao ordenadas por contribuicao ao gap
- Hipoteses especificas com nivel de confianca justificado
- Indicadores correlacionados e seu status

### O que NAO deve conter

- Adjetivos vagos sem numero ("significativo", "expressivo", "preocupante")
- Causas genericas ("mercado dificil", "momento economico", "sazonalidade") sem evidencia
- Recomendacoes de acoes detalhadas (isso e E4)
- Dados inventados ou extrapolados sem base no dataset
- Opinioes ou julgamentos sobre pessoas

### Formato de Hipotese

```
**Causa-raiz provavel**: [descricao especifica]
- **Confianca**: [Alta/Media/Baixa]
- **Evidencias**: [lista das evidencias que suportam]
- **Indicadores correlacionados**: [lista com status]
```
