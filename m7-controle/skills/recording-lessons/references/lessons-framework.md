# Framework de Licoes Aprendidas — Retrospectiva Mensal G2.2

> Referencia para o agente analyst e a skill recording-lessons.
> Define a metodologia de extracao de licoes, criterios de qualidade e priorizacao de propostas.

---

## Indice

1. [Framework de 4 Categorias](#framework-de-4-categorias)
2. [Criterios de Qualidade de uma Licao](#criterios-de-qualidade-de-uma-licao)
3. [Metodo de Consolidacao Cross-Ciclo](#metodo-de-consolidacao-cross-ciclo)
4. [Priorizacao de Propostas de Melhoria](#priorizacao-de-propostas-de-melhoria)
5. [Exemplos de Licoes Bem Escritas vs. Mal Escritas](#exemplos-de-licoes-bem-escritas-vs-mal-escritas)
6. [Relacao com o Ciclo PDCA](#relacao-com-o-ciclo-pdca)

---

## Framework de 4 Categorias

Cada licao deve ser classificada em exatamente uma categoria. A categoria determina o tipo de acao proposta.

| Categoria | Pergunta-chave | Acao esperada |
|-----------|---------------|---------------|
| **O que funcionou** | Que processo, acao ou decisao levou a melhoria mensuravel? | **Replicar**: padronizar e disseminar para outras verticais/etapas |
| **O que nao funcionou** | Que processo, acao ou decisao falhou repetidamente? | **Corrigir**: propor mudanca especifica no processo |
| **O que surpreendeu** | Que resultado inesperado (positivo ou negativo) nao foi explicado pelas acoes tomadas? | **Investigar**: aprofundar analise para entender a causa |
| **O que faltou** | Que gap de dados, processo ou ritual impediu uma analise ou decisao? | **Complementar**: adicionar o que esta faltando |

### Regras de Classificacao

- Se o resultado foi positivo E atribuivel a uma acao especifica → **Funcionou**
- Se o resultado foi negativo E recorrente (2+ ciclos) → **Nao funcionou**
- Se o resultado foi inesperado (positivo ou negativo) SEM acao correspondente → **Surpreendeu**
- Se a analise foi limitada por ausencia de dados, ferramenta ou feedback → **Faltou**
- Em caso de duvida entre "nao funcionou" e "surpreendeu": se houve uma acao que deveria ter resolvido e nao resolveu → **Nao funcionou**. Se nao houve acao nenhuma → **Surpreendeu**.

---

## Criterios de Qualidade de uma Licao

Uma licao so e valida se atender TODOS os criterios abaixo:

| Criterio | Descricao | Teste |
|----------|-----------|-------|
| **Evidencia** | Suportada por dados de pelo menos 1 artefato (WBR, action-report, DQ-report ou ata) | Citar o artefato e o dado especifico |
| **Recorrencia** | Observada em 2+ ciclos OU impacto significativo em 1 ciclo (com justificativa) | Listar ciclos e datas |
| **Especificidade** | Descreve um fenomeno concreto, nao uma observacao generica | Substituir por "melhorar X" e ver se perde informacao — se nao perder, e generica demais |
| **Acionabilidade** | Permite gerar pelo menos 1 proposta de melhoria concreta | Escrever a proposta — se nao conseguir, a licao nao e acionavel |
| **Atribuicao** | Identifica a etapa (E2-E6 ou G2.3) e vertical(is) impactadas | Preencher os campos obrigatorios do template |

### Minimo por Ciclo Mensal

- **2 licoes** por relatorio mensal (criterio de qualidade do processo)
- Se nao ha evidencia suficiente para 2 licoes, o entry criteria da skill nao foi atendido — registrar como anomalia e revisar se os ciclos semanais estao gerando artefatos completos

---

## Metodo de Consolidacao Cross-Ciclo

### Evolucao de Semaforo

Para cada indicador acompanhado no mes, comparar o semaforo (verde/amarelo/vermelho) ao longo das semanas:

```
Indicador: Captacao Liquida
  Sem 1: Amarelo (gap -12%)
  Sem 2: Vermelho (gap -28%)
  Sem 3: Vermelho (gap -25%)
  Sem 4: Amarelo (gap -10%)
  Tendencia: Recuperacao (piorou e depois melhorou)
```

**Padroes a identificar:**
- **Persistente**: mesmo semaforo vermelho por 3+ semanas → candidato a "nao funcionou"
- **Recuperacao**: vermelho → amarelo/verde → candidato a "funcionou" (verificar qual acao causou)
- **Deterioracao**: verde → amarelo → vermelho → candidato a "surpreendeu" ou "nao funcionou"
- **Oscilacao**: alterna sem tendencia clara → candidato a "faltou" (dados insuficientes ou acao inconsistente)

### Eficacia de Acoes

Comparar metricas do action-report ao longo das semanas:

| Metrica | O que indica se piorou | O que indica se melhorou |
|---------|------------------------|--------------------------|
| Acoes criticas (%) | Contramedidas ineficazes ou tardias | Processo de resposta rapida funcionando |
| Taxa conclusao 30d | Pipeline de acoes travado | Execucao disciplinada |
| Aging medio | Acoes envelhecendo sem resolucao | Acoes sendo fechadas no prazo |
| Volume/receita em risco | Impacto financeiro crescente | Risco sendo mitigado |

### Qualidade de Dados

Comparar alertas dos data-quality-report ao longo das semanas:

- **Alerta recorrente** (mesmo indicador, mesmo tipo de alerta em 2+ semanas) → Licao "nao funcionou" ou "faltou" na coleta (E2)
- **Alerta resolvido** (apareceu na semana 1, desapareceu na semana 2+) → Nao e licao, e correcao pontual
- **Novos alertas na ultima semana** → Nao e licao (sem recorrencia), mas mencionar em "Tendencias"

### Feedback de Rituais (Atas)

Extrair das atas de rituais (G2.3):

1. **Decisoes com atribuicao** (campo `## Decisoes` da ata) — verificar se foram implementadas nos ciclos seguintes
2. **Escalonamentos** — verificar se foram resolvidos
3. **Feedback implicito** — participantes que questionaram a qualidade dos materiais, dados ou analises
4. **Nomes dos gestores N2** presentes — necessarios para atender o criterio "min 2 gestores N2"

---

## Priorizacao de Propostas de Melhoria

Cada proposta gerada a partir de uma licao deve ser priorizada pela matriz Impacto x Esforco.

### Matriz de Priorizacao

```
           Esforco Baixo    Esforco Medio    Esforco Alto
          ┌────────────────┬────────────────┬────────────────┐
Impacto   │                │                │                │
Alto      │  ALTA (fazer   │  ALTA (fazer   │  MEDIA         │
          │  imediatamente)│  no proximo    │  (planejar)    │
          │                │  ciclo)        │                │
          ├────────────────┼────────────────┼────────────────┤
Impacto   │                │                │                │
Medio     │  ALTA (quick   │  MEDIA         │  BAIXA         │
          │  win)          │  (avaliar ROI) │  (postergar)   │
          ├────────────────┼────────────────┼────────────────┤
Impacto   │                │                │                │
Baixo     │  MEDIA         │  BAIXA         │  BAIXA         │
          │  (se trivial)  │  (postergar)   │  (descartar)   │
          └────────────────┴────────────────┴────────────────┘
```

### Criterios de Impacto

| Impacto | Criterio |
|---------|----------|
| **Alto** | Afeta 2+ verticais OU impacto financeiro > R$ 100K OU bloqueia tomada de decisao |
| **Medio** | Afeta 1 vertical OU melhora qualidade de dados/analise significativamente |
| **Baixo** | Melhoria cosmetica OU afeta apenas eficiencia interna sem impacto em decisoes |

### Criterios de Esforco

| Esforco | Criterio |
|---------|----------|
| **Baixo** | Mudanca de configuracao, ajuste de YAML, update de template — implementavel em 1 dia |
| **Medio** | Mudanca de processo, novo script, ajuste de skill — implementavel em 1 semana |
| **Alto** | Nova ferramenta, mudanca de arquitetura, novo MCP/integracao — implementavel em 1+ mes |

### Tipos de Proposta

| Tipo | Descricao | Exemplos |
|------|-----------|----------|
| **processo** | Mudanca em etapa ou fluxo do G2.2 | Alterar frequencia de E4, adicionar gate em E3 |
| **dados** | Melhoria na coleta ou qualidade de dados | Novo indicador, correcao de script, nova fonte |
| **ritual** | Melhoria no formato ou frequencia dos rituais | Mudar pauta, adicionar participante, ajustar cadencia |
| **ferramenta** | Melhoria em tooling, automacao ou integracao | Novo MCP, script de automacao, dashboard |

---

## Exemplos de Licoes Bem Escritas vs. Mal Escritas

### Exemplo BOM

```markdown
### L1: Contramedidas de redistribuicao de carteira tem alta eficacia quando aplicadas em ate 1 semana

- **Categoria**: O que funcionou
- **Descricao**: A segmentacao por equipe em E3 identificou concentracao de gap em
  2 assessores nas 4 semanas. A contramedida de redistribuicao de carteira (acao #42)
  foi implementada na semana 2. O gap reduziu de 40% para 18% entre semana 2 e semana 4.
- **Evidencia**: WBR semanas 2-4 (consorcios/2026-03-10, 2026-03-17, 2026-03-24);
  action-report semana 2 (acao #42: status concluida, eficacia Eficaz)
- **Vertical(is)**: Consorcios
- **Ciclo(s)**: 2026-03-10, 2026-03-17, 2026-03-24
- **Etapa impactada**: E4 (acompanhamento de acoes)
- **Recorrencia**: Padrao observado em 3 ciclos consecutivos
- **Acao proposta**: Criar regra no E3 para automaticamente sugerir redistribuicao
  quando concentracao por assessor > 50% do gap por 2+ semanas
```

### Exemplo RUIM

```markdown
### L1: Precisamos melhorar a captacao

- **Categoria**: O que nao funcionou
- **Descricao**: A captacao ficou abaixo da meta no mes
- **Evidencia**: WBRs do mes
- **Etapa impactada**: E6
- **Acao proposta**: Melhorar o processo de captacao
```

**Por que e ruim:**
- "Melhorar a captacao" nao e especifico — nao identifica o fenomeno concreto
- Nao cita dados (qual gap? qual tendencia?)
- Nao identifica ciclos especificos
- "WBRs do mes" nao e evidencia concreta (quais WBRs? que dado?)
- Acao proposta e generica e nao e acionavel
- Etapa impactada errada (E6 consolida, nao causa desvios)

---

## Relacao com o Ciclo PDCA

E7 (Licoes Aprendidas) ocupa a posicao **A (Act)** no ciclo PDCA do processo G2.2:

```
P (Plan)  → E1: Configurar Cards de Performance (definir metas, indicadores, regras)
D (Do)    → E2: Coletar Dados (executar medicao)
C (Check) → E3-E6: Analisar, Acompanhar, Projetar, Consolidar WBR
A (Act)   → E7: Registrar Licoes Aprendidas (ajustar o processo)
```

### Feedback Loops

As licoes de E7 alimentam melhorias nas seguintes etapas:

| Licao impacta | Como ajustar |
|---------------|-------------|
| E1 (Cards) | Ajustar metas, adicionar/remover indicadores, refinar regras de semaforo |
| E2 (Coleta) | Corrigir scripts, adicionar fontes, melhorar validacoes de qualidade |
| E3 (Desvios) | Refinar investigation playbook, ajustar dimensoes de segmentacao |
| E4 (Acoes) | Melhorar criterios de urgencia, refinar avaliacao de eficacia |
| E5 (Projecoes) | Ajustar metodos de projecao, calibrar dependencias cruzadas |
| E6 (WBR) | Melhorar narrativa, ajustar secoes, refinar visualizacoes |
| G2.3 (Rituais) | Ajustar pauta, formato de materiais, cadencia |

### Periodicidade

- **Mensal**: Retrospectiva padrao — analisa 4-5 ciclos semanais
- **Trimestral**: Retrospectiva ampliada — analisa 3 relatorios mensais e identifica tendencias de longo prazo (usar os proprios lessons-learned mensais como input adicional)
