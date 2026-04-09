---
name: recording-lessons
description: >-
  G2.2-E7: Consolida licoes aprendidas do ciclo mensal a partir dos WBRs (E6),
  atas de rituais (G2.3), relatorios de acoes (E4) e data quality reports (E2)
  de TODAS as verticais. Produz registro unico de licoes no nivel do processo
  G2.2 com propostas de melhoria priorizadas. Use when the monthly cycle ends
  (last Friday of the month), when /m7-controle:record-lessons is invoked,
  or when the user requests a monthly retrospective.

  <example>
  Context: Fim do mes, 4 ciclos semanais completos para 2 verticais
  user: "/m7-controle:record-lessons 2026-03"
  assistant: Escaneia ciclos de todas as verticais no mes, consolida licoes e gera relatorio em mensal/2026-03/
  </example>

  <example>
  Context: Usuario quer revisar o que deu errado no mes
  user: "Quais as licoes aprendidas de marco?"
  assistant: Le WBRs, action-reports, DQ-reports e atas de todas as verticais, identifica padroes recorrentes e gera relatorio com propostas
  </example>

  <example>
  Context: Pipeline semanal concluido, ultimo ciclo do mes
  user: "Fecha o mes com as licoes aprendidas"
  assistant: Invoca recording-lessons para consolidar todos os ciclos do mes em relatorio unico
  </example>
user-invocable: false
---

# Recording Lessons — Licoes Aprendidas (E7)

> "Quem nao registra nao aprende. Quem nao aprende repete."

Esta skill consolida licoes aprendidas de todos os ciclos semanais e rituais de um mes, cruzando TODAS as verticais. O output e um relatorio unico sobre o **processo G2.2** — a vertical e um atributo de cada licao, nao uma dimensao de organizacao. E a etapa final do processo de controle de performance, com cadencia mensal.

> **REGRA DE HANDOFF**: Ao invocar o agente analyst, NAO passe valores de dados no texto do prompt. Passe APENAS caminhos de arquivos (lista de cycle folders, lista de atas, periodo). O analyst deve usar Read tool para carregar os dados dos arquivos em disco.

## Dependencias Internas

- [references/lessons-framework.md](references/lessons-framework.md) — Framework de 4 categorias, criterios de qualidade, metodo de consolidacao cross-ciclo e priorizacao
- [templates/lessons-learned-report.tmpl.md](templates/lessons-learned-report.tmpl.md) — Template do Registro de Licoes Aprendidas
- Agent `analyst` — Executor da analise (invocado automaticamente)
- Outputs de ciclos semanais do mes (para todas as verticais):
  - `wbr/wbr-narrativo-*.md` (E6 — Input I1)
  - `analise/action-report.md` (E4 — Input I3)
  - `data-quality/data-quality-report.md` (E2 — Input I4)
- Outputs de rituais do mes:
  - `output/*/ata-ritual-*.md` (G2.3 — Input I2)

> **Resolucao de caminhos**: Os ciclos semanais ficam em `{vertical}/YYYY-MM-DD/` no diretorio de trabalho do usuario. As atas ficam em `output/{vertical}/ata-ritual-YYYY-MM-DD.md` dentro das pastas de ciclo. Localizar via Glob com filtro pelo periodo.

## Pre-requisitos (Entry Criteria)

- Pelo menos 1 ciclo semanal com E6 = `concluido` no mes (em qualquer vertical)
- Periodo (YYYY-MM) definido
- Diretorio de trabalho do usuario acessivel

## Workflow

### Fase 1 — Descobrir Artefatos do Mes

1. **Localizar ciclos de TODAS as verticais**: `Glob('*/{periodo}-*/CICLO.md')` onde `{periodo}` e o YYYY-MM do mes
2. **Para cada CICLO.md encontrado**:
   - Ler o header para extrair vertical e status
   - Verificar se E6 = `concluido`
   - Se E6 nao concluido: registrar como ciclo incompleto (incluir no relatorio mas marcar como parcial)
3. **Para cada ciclo completo**, coletar paths de:
   - `wbr/wbr-narrativo-*.md` (I1: WBRs)
   - `analise/action-report.md` (I3: acoes)
   - `data-quality/data-quality-report.md` (I4: qualidade)
4. **Localizar atas de rituais**: `Glob('*/{periodo}-*/output/*/ata-ritual-*.md')` (I2: feedback)
5. **Agrupar por vertical** para rastreabilidade — registrar quantos ciclos e atas cada vertical tem
6. **Validar**:
   - Se 0 ciclos completos: **ABORTAR** com mensagem "Nenhum ciclo completo encontrado para {periodo}. Execute pelo menos 1 /m7-controle:run-weekly primeiro."
   - Se 0 atas: **WARNING** (nao bloqueante) — registrar que criterio "min 2 gestores N2" nao sera atendido

**Output Fase 1**: Lista de paths agrupada por vertical + contagem de cobertura.

### Fase 2 — Ler e Sintetizar Artefatos

Invocar o agente `analyst` passando APENAS os paths dos artefatos coletados na Fase 1.

O analyst deve:

1. **Ler TODOS os WBR narrativos** (I1) — extrair:
   - Semaforo por indicador por semana (construir tabela de evolucao)
   - Indicadores persistentemente vermelhos (3+ semanas)
   - Indicadores que recuperaram (vermelho → verde)
   - Narrativas recorrentes (temas que aparecem em 2+ WBRs)

2. **Ler TODOS os action-reports** (I3) — extrair:
   - Tendencia de metricas: acoes criticas, taxa conclusao, aging medio
   - Acoes que foram concluidas e tiveram eficacia "Eficaz" (candidatas a "funcionou")
   - Acoes criticas persistentes (presentes em 2+ reports sem resolucao)
   - Volume e receita em risco — evolucao ao longo do mes

3. **Ler TODOS os data-quality-reports** (I4) — extrair:
   - Alertas recorrentes (mesmo indicador, mesmo tipo, 2+ semanas)
   - Alertas que foram corrigidos vs. que persistem
   - Indicadores com dados ausentes

4. **Ler TODAS as atas de rituais** (I2) — extrair:
   - Decisoes tomadas com responsavel e prazo
   - Escalonamentos registrados
   - Gestores N2 presentes (nomes)
   - Feedback sobre qualidade de materiais/dados/analises

**Output Fase 2**: Sintese estruturada por vertical com temas, tendencias e evidencias.

### Fase 3 — Identificar Licoes

Aplicar o framework de 4 categorias (ver [references/lessons-framework.md](references/lessons-framework.md)):

| Categoria | Fonte primaria de evidencia |
|-----------|----------------------------|
| **O que funcionou** | Acoes eficazes (E4) + indicadores que recuperaram (E6) |
| **O que nao funcionou** | Acoes criticas persistentes (E4) + indicadores persistentemente vermelhos (E6) |
| **O que surpreendeu** | Mudancas de semaforo sem acao correspondente (E6 vs E4) |
| **O que faltou** | Alertas de qualidade recorrentes (E2) + ausencia de atas (G2.3) + gaps identificados |

Para cada licao candidata:

1. **Validar criterios de qualidade** (ver reference): evidencia, recorrencia, especificidade, acionabilidade, atribuicao
2. **Atribuir vertical(is)**: pode ser especifica (1 vertical) ou cross-vertical (observada em 2+ verticais)
3. **Atribuir ciclo(s)**: listar datas dos ciclos onde a evidencia aparece
4. **Atribuir etapa impactada**: E2, E3, E4, E5, E6 ou G2.3
5. **Redigir acao proposta**: especifica e acionavel (ver exemplos bons vs. ruins no reference)

**Minimo**: 2 licoes. Se nao ha evidencia para 2 licoes, registrar como anomalia — os ciclos semanais nao estao gerando artefatos suficientes para retrospectiva.

**Output Fase 3**: Lista de licoes validadas com todos os atributos preenchidos.

### Fase 4 — Gerar Propostas de Melhoria (O2)

Para cada licao categorizada como "nao funcionou" ou "faltou":

1. **Derivar proposta** a partir da acao proposta da licao
2. **Classificar tipo**: processo / dados / ritual / ferramenta
3. **Avaliar impacto**: Alto / Medio / Baixo (ver criterios no reference)
4. **Avaliar esforco**: Baixo / Medio / Alto (ver criterios no reference)
5. **Calcular prioridade** via matriz Impacto x Esforco (ver reference)
6. **Atribuir responsavel sugerido**: Performance / Gestores N2 / TI / Cowork
7. **Atribuir prazo sugerido**: proximo ciclo / proximo mes / proximo trimestre

Licoes "funcionou" e "surpreendeu" tambem podem gerar propostas (de replicacao ou investigacao), mas nao e obrigatorio.

**Output Fase 4**: Lista de propostas priorizadas vinculadas as licoes.

### Fase 5 — Gerar Relatorio (O1)

1. **Preencher o template** [lessons-learned-report.tmpl.md](templates/lessons-learned-report.tmpl.md) com:
   - Resumo executivo (3-5 frases sobre o processo G2.2 no mes)
   - Cobertura de fontes por vertical
   - Licoes com todos os atributos
   - Propostas priorizadas
   - Tendencias do mes por vertical (tabelas de evolucao)
   - Feedback dos gestores N2
   - Acompanhamento de decisoes de rituais
2. **Criar pasta** `mensal/{periodo}/` se nao existir
3. **Salvar** como `mensal/{periodo}/lessons-learned-{periodo}.md`

**Output Fase 5**: Relatorio final em disco.

### Fase 6 — Finalizar

1. **Registrar conclusao** nos CICLO.md mais recentes de cada vertical do mes:
   - Append ao **Log de Execucao**: `[{timestamp}] SISTEMA — E7 concluida. Relatorio mensal: mensal/{periodo}/lessons-learned-{periodo}.md`
2. **Exibir resumo** ao usuario:

```
E7 Licoes Aprendidas — G2.2 — {periodo}

Verticais: {lista_verticais}
Ciclos analisados: {n_completos} completos + {n_parciais} parciais
Rituais analisados: {n_rituais}
Gestores N2 identificados: {n_gestores}

Licoes registradas: {n_licoes}
  - Funcionou: {n_funcionou}
  - Nao funcionou: {n_nao_funcionou}
  - Surpreendeu: {n_surpreendeu}
  - Faltou: {n_faltou}

Propostas de melhoria: {n_propostas}
  - Alta: {n_alta} | Media: {n_media} | Baixa: {n_baixa}

Output: mensal/{periodo}/lessons-learned-{periodo}.md
```

## Exit Criteria

- [ ] Minimo 2 licoes registradas (criterio de qualidade G2.2-E7)
- [ ] Cada licao tem evidencia de pelo menos 1 artefato concreto (com dados especificos)
- [ ] Cada licao tem vertical(is), ciclo(s) e etapa impactada atribuidos
- [ ] Propostas de melhoria geradas para licoes "nao funcionou" e "faltou"
- [ ] Propostas priorizadas via matriz Impacto x Esforco
- [ ] Relatorio salvo em `mensal/{periodo}/lessons-learned-{periodo}.md`
- [ ] Log registrado nos CICLO.md mais recentes de cada vertical

## Anti-Patterns

- NUNCA gere licoes genericas ("melhorar captacao", "aumentar qualidade") — sempre com fenomeno especifico, dados concretos e evidencia rastreavel
- NUNCA invente dados ou tendencias nao suportados pelos artefatos lidos — se nao ha dados, e "faltou", nao "nao funcionou"
- NUNCA ignore as atas de rituais (I2) — o feedback dos gestores N2 e input mandatorio do processo. Se nao ha atas, registrar como gap explicito
- NUNCA registre como licao algo que aconteceu em apenas 1 semana sem impacto significativo — isso e anomalia, nao licao. Exigir recorrencia (2+ ciclos) OU justificativa de impacto significativo
- NUNCA produza menos de 2 licoes — se nao ha evidencia, registrar como anomalia e investigar se os ciclos semanais estao completos
- NUNCA organize o relatorio por vertical — o relatorio e sobre o PROCESSO G2.2. A vertical e um atributo da licao
- NUNCA escreva propostas vagas ("melhorar o processo") — cada proposta deve ter tipo, prioridade, esforco, responsavel e prazo sugeridos
- NUNCA altere artefatos de ciclos semanais — E7 e read-only sobre os outputs de E2-E6 e G2.3
