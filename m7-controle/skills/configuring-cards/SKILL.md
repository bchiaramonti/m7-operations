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
