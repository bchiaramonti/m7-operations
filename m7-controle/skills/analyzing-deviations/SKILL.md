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

> **OBRIGATORIO antes de classificar**: Ler as metas de `dados/metas-resolvidas.json` (SoT gerado pelo `resolve_metas.py` pre-E3). Se ausente ou `offline_fallback=true`, emitir WARN e usar o Card como fallback:
> 1. `metas-resolvidas.json["indicadores"]` — **SoT** para PPIs de funil e KPIs mensais do ciclo
> 2. `kpi_references[].regras_meta` do Card — complemento para KPIs sem entrada no JSON
> 3. `metas_ppi:` do Card — **fallback** somente quando `offline_fallback=true`
>
> NAO classifique nenhum PPI como "sem meta / cinza" antes de verificar o JSON. Cada chave em `indicadores` e uma meta formal a aplicar.

**Para indicadores em `kpi_references[].regras_meta` ou sem direction explicito** (regra padrao):

| Classificacao | Criterio | Acao |
|---------------|----------|------|
| **Verde** | >= 95% da meta | Registro breve (destaque se era Vermelho no ciclo anterior) |
| **Amarelo** | 80-94% da meta | Analise simplificada (tendencia + contexto) |
| **Vermelho** | < 80% da meta | Analise de fenomeno completa (5 dimensoes) |

**Para PPIs em `metas-resolvidas.json` (ou fallback `metas_ppi:` do Card)** (regra a):

| Classificacao | Criterio (maior_melhor) | Criterio (menor_melhor) |
|---------------|-------------------------|--------------------------|
| **Verde** | pct >= 100% | pct >= 100% |
| **Amarelo** | 70% <= pct < 100% | 70% <= pct < 100% |
| **Vermelho** | pct < 70% | pct < 70% |

Onde:
- `maior_melhor`: `pct = (realizado / meta) × 100`
- `menor_melhor`: `pct = (meta / max(realizado, 1)) × 100`, com cap em 200%

> **REGRA CRITICA**: O semaforo classifica o INDICADOR AGREGADO (N1) contra sua META FORMAL. A performance INDIVIDUAL de um assessor NAO afeta o semaforo — mesmo que um assessor esteja a 0%, se o agregado esta a 105%, o indicador e Verde. Concentracao de resultado em poucos individuos e um RISCO OPERACIONAL reportado separadamente na dimensao QUEM/ONDE, nunca um fator de reclassificacao do semaforo.
>
> Exemplo correto: Volume N1 a 105% = Verde, mesmo que Tereza esta a 0% e Douglas a 175%.
> Exemplo incorreto: Douglas "reclassificado" como Vermelho por "concentracao excessiva".

**Output Fase 1:** Tabela-semaforo com todos os indicadores classificados, separando KPIs (regra padrao 95/80) de PPIs (regra a 100/70 via `metas-resolvidas.json`). Registrar EXPLICITAMENTE quais indicadores nao tem meta (verdadeiramente cinza) e quais tem `_pending` no JSON ou `valor: pendente` no Card (cinza com justificativa).

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

### Fase 6.5 — Emissão canonical: `causa_raiz_resumo` (sidecar JSON) — NOVO em v4.x (S2a B4.17, 2026-05-18)

**Motivo:** O `deviation-cause-report.md` (Fase 6) e narrativo e detalhado. Downstream (E6 `consolidating-wbr` → build_deck do `m7-ritual-gestao:preparing-materials` Slide Riscos · Alertas) precisa de **1-2 frases sintetizando a causa-raiz por indicador** para renderizar no canonical WBR. Sintese fica em sidecar JSON estruturado consumido por E6.

**Output:** `{cycle_folder}/analise/e3-causa-raiz-{vertical}.json`

**Schema:**

```json
{
  "_schema": "e3-causa-raiz v1.0",
  "_generated_at": "2026-05-19T08:30:00",
  "vertical": "consorcios",
  "data_referencia": "2026-05-19",
  "indicadores": {
    "<indicator_id>": {
      "causa_raiz_resumo": "1-2 frases sintetizando a hipotese de causa-raiz principal",
      "semaforo": "vermelho|amarelo|verde",
      "confianca": "alta|media|baixa",
      "n2_breakdown": {
        "<especialista>": {
          "causa_raiz_resumo": "OPCIONAL — 1 frase especifica para este especialista quando o desvio e individual"
        }
      }
    }
  }
}
```

**Regras de emissão:**

1. **Emitir para TODOS os indicadores Vermelhos** — `causa_raiz_resumo` obrigatório (sintese da hipotese principal da Fase 3)
2. **Emitir para indicadores Amarelos** — `causa_raiz_resumo` opcional; emitir apenas se Fase 4 identificou tendencia/contexto material (ex: "queda significativa vs M-1 por mix")
3. **Verdes**: emitir SE havia desvio vermelho/amarelo no ciclo anterior — `causa_raiz_resumo` descreve a recuperacao
4. **n2_breakdown.{especialista}.causa_raiz_resumo**: emitir APENAS quando a Fase 2 dimensão QUEM identificou concentracao individual (ex: "Douglas com 80% do gap")
5. **Cinza/sem meta**: NAO emitir entrada (não tem desvio formal a explicar)
6. **Tamanho**: 1-2 frases (max ~200 caracteres por `causa_raiz_resumo`). Quem precisa de detalhe le o MD narrativo
7. **Tom**: factual, sem sugestao de acao (acao e responsabilidade de E4)

### Checklist de qualidade — TODA `causa_raiz_resumo` DEVE ter:

> **REFORÇO 2026-05-19 (S2a Sessao A parcial).** Feedback do usuario apos ritual Cons 2026-05-19: card Riscos · Atencao no 1º slide de cada especialista mostrou analises rasas. Esta checklist garante densidade analitica.

Cada `causa_raiz_resumo` (1-2 frases, max ~200 chars) DEVE conter **3 elementos minimos**:

1. **Número específico** (quanto): pct, valor BRL compact, qty absoluta, ou gap relativo
   - Ex: "85% do gap", "R$ 5,2M concentrados", "47% (vs 28%)", "fator 24x meta"

2. **Identificador de QUEM/ONDE/QUANDO** (a quebra que explica):
   - QUEM: nome de pessoa (especialista, assessor) — ex: "Douglas", "Camila Quintino"
   - ONDE: estágio, canal, produto, equipe — ex: "estágio Proposta", "canal Investimentos", "B2B Alta Renda"
   - QUANDO: comparativo MoM/WoW, semana, dias — ex: "vs M-1", "WoW", "D+9", "ultimas 3 semanas"

3. **Direção causal** (por que): conexão entre o número e a explicação. Verbo causal explicito
   - Ex: "sinalizando retração", "indica gargalo de conducao", "puxa pct para cima", "antecipa queda em M+1"

**Se faltar QUALQUER um dos 3 elementos**, a frase está rasa. Reescrever.

### Exemplos RICOS (✅ aprovado) — variados por tipo de indicador

**Volume / Receita / qty (KPI principal):**
- ✅ "Douglas concentra 85% do gap (R$ 5,4M) de Volume. Funil de Investigacao caiu 40% MoM, sinalizando retracao de prospeccao."
- ✅ "Receita MTD em R$ 12K vs meta R$ 36K (33%) por Humberto NAO converter R$ 28K em Cotas Alocadas (parados ha >21d)."
- ✅ "Volume em fator 24x abaixo da meta. ICOFORT (R$ 60M) parado em Cotas Alocadas — sem decisao win/lose ha 3 semanas."
- ✅ "qty_won caiu de 8 para 2 entre Abril e Maio MTD; concentrada em B2B Alta Renda (Squad Douglas)."

**Estagnacao / Pct ativas:**
- ✅ "Estagnacao subiu para 47% das ativas (vs 28% em M-1). Concentrada no estagio Proposta com tickets >R$500K."
- ✅ "68,5% das ativas estagnadas (meta <=40%). Pareto: Pedro Ramos (Squad Douglas) responde por 8 deals, 4 sem atividade ha >21d."
- ✅ "% Estagnadas dispara de 32% (M-1) para 51% (MTD). Causada por desaceleracao de WON nos estagios finais — pipeline retem volume sem converter."

**Taxa de conversao:**
- ✅ "Taxa de conversao caiu de 18% para 9% MoM. Concentrada na transicao Apresentacao → Proposta — leads chegam sem qualificacao adequada."
- ✅ "Conversao zero em Maio MTD (0/5 deals fechados em B2B Mesa). Tickets medios subiram 60% — leads grandes exigem ciclo mais longo."

**Oportunidades criadas (entrada de funil):**
- ✅ "Criadas caem 35% MoM (de 47 para 30). Investimentos puxa para baixo (-50%); Credito estavel."
- ✅ "Criacao MTD em 12 deals vs media historica 22-28. Sem campanha de captacao ativa em Maio (queda esperada)."

**Tempo de ciclo / Sem atividade:**
- ✅ "Tempo medio de ciclo subiu para 47d (meta 30d). 3 deals com >60d em Apresentacao — pendencia de documentacao com cliente."
- ✅ "12 deals sem atividade planejada (vs 4 em M-1). Concentrados em Humberto e Pedro Araujo — sobrecarga de carteira."

### n2_breakdown — quando emitir analise por especialista

Emitir `n2_breakdown.{esp}.causa_raiz_resumo` APENAS quando a Fase 2 dimensão QUEM mostra **concentracao individual >50%** do gap, OU quando o desvio é binario (1 especialista vermelho, outros verdes).

**Exemplos n2_breakdown:**
- ✅ Douglas: "Concentra 85% do gap. Funil Investigacao caiu 40% MoM."
- ✅ Tereza: "Verde — 105% da meta. Carteira B2C com ticket medio crescente."
- ❌ NAO emitir n2_breakdown quando o desvio esta distribuido equilibradamente (sem concentracao)

### Anti-patterns — recusar emitir essas frases

- ❌ "Mercado dificil este mes" — generico, sem evidencia
- ❌ "Volume caiu" — nao explica causa
- ❌ "Revisar aging por canal" — sugestao de acao (acao e E4, nao E3)
- ❌ "Indicador X vermelho — N% meta" — descricao do sintoma, nao causa
- ❌ "Pipeline esta entupido" — adjetivo sem dado
- ❌ "Queda significativa em relacao ao mes passado" — sem numero
- ❌ "Provavel impacto de sazonalidade" — sem ancoragem em dado

### Procedimento de geracao

Para CADA indicador Vermelho (e Amarelos materiais), aplicar:

1. Ler a Fase 2 (5 dimensoes) e Fase 3 (hipoteses) do relatorio MD que voce mesmo gerou
2. Identificar a **hipotese de causa-raiz com confianca alta** (suportada por 2+ evidencias)
3. Reescrever essa hipotese em formato `causa_raiz_resumo` aplicando o checklist (numero + quem/onde/quando + verbo causal)
4. Validar contra anti-patterns — se cair em algum, voltar para passo 2 com hipotese mais forte
5. Se NAO ha hipotese de confianca alta, emitir `causa_raiz_resumo` com confianca media + qualificador explicito ("Provavelmente ..., mas dados nao bate em N5")
6. Tamanho final: 1-2 frases, max ~200 chars

**Consumo downstream:**

- E6 (`consolidating-wbr`) Fase 4.5.d le este sidecar e injeta em `indicadores.{id}.causa_raiz_resumo` no canonical WBR
- build_deck.py Slide Riscos · Alertas consome do canonical (com fallback graceful da S1 mantido)

**Validacao opcional contra JSON Schema (S2a B6.25):**

Apos emitir o sidecar, agente PODE validar contra schema declarativo em `m7-operations/_schema/v1.2/e3-causa-raiz.schema.json`:

```bash
python3 -c "
import json
from jsonschema import validate, ValidationError
try:
    schema = json.load(open('m7-operations/_schema/v1.2/e3-causa-raiz.schema.json'))
    data = json.load(open('{cycle_folder}/analise/e3-causa-raiz-{vertical}.json'))
    validate(data, schema)
    print('OK')
except ValidationError as e:
    print(f'SCHEMA VIOLATION: {e.message}')
    raise SystemExit(1)
"
```

Se schema violation, **NAO commitar e investigar**. Schema strict garante que E6 (Fase 4.5.d) consume sem erro.

**Normalizacao deterministica (OBRIGATORIO 2026-06-11):** apos emitir o sidecar, rodar o
normalizador para garantir o shape canonico (indicadores DICT keyed by indicator_id —
NUNCA lista; `semaforo` presente; `n2_breakdown` DICT keyed by especialista). Pega o bug
recorrente e SILENCIOSO em que o sidecar sai como lista e o E6 nao consegue injetar
`causa_raiz_resumo` (deck cai em texto generico sem erro visivel). Idempotente.

```bash
python3 {plugin_root}/m7-controle/skills/consolidating-wbr/scripts/normalize_canonical.py \
  --cycle-folder {cycle_folder} --vertical {vertical} [--subnivel {subnivel}]
```

## Exit Criteria

- [ ] Relatorio de Desvios e Causa-Raiz gerado em `analise/deviation-cause-report.md` (na pasta do ciclo)
- [ ] **`dados/metas-resolvidas.json` foi lido e aplicado** (SoT; ou fallback `metas_ppi:` do Card quando `offline_fallback=true`; cada PPI virou linha do semaforo com regra a 100/70/menor_melhor)
- [ ] 100% dos indicadores classificados no semaforo (Verde/Amarelo/Vermelho/Cinza-com-justificativa)
- [ ] Indicadores cinza tem motivo explicito: "sem meta no Card" OU "meta marcada como `valor: pendente` no Card"
- [ ] Analise de fenomeno completa (5 dimensoes) para cada Vermelho
- [ ] Pelo menos 1 hipotese de causa-raiz com nivel de confianca para cada Vermelho
- [ ] Hipoteses especificas e baseadas em dados (nao genericas)
- [ ] PPIs de `kpis_analisar_como_contexto` do Card consultados e incorporados na analise (ou motivo de exclusao registrado)
- [ ] **Sidecar JSON `analise/e3-causa-raiz-{vertical}.json` emitido** (Fase 6.5 — NOVO v4.x S2a B4.17) — todo indicador Vermelho tem `causa_raiz_resumo` 1-2 frases; Amarelos opcionais; n2_breakdown apenas quando ha concentracao individual
- [ ] **Cada `causa_raiz_resumo` passa pelo checklist de qualidade** (Fase 6.5, reforco 2026-05-19): contem (a) numero especifico, (b) identificador de QUEM/ONDE/QUANDO, (c) verbo causal. Sem os 3, reescrever. Frases ancoradas em dados (nao genericas tipo "mercado dificil" ou "volume caiu"). Validacao explicita antes de emitir o sidecar.

## Anti-Patterns

- NUNCA use causas genericas como "mercado dificil", "sazonalidade" sem evidencia nos dados
- NUNCA pule a analise de fenomeno para indicadores Vermelhos — todas as 5 dimensoes sao obrigatorias
- NUNCA invente dados de segmentacao — use apenas o que esta nos dados consolidados e quebras
- NUNCA sugira acoes corretivas detalhadas — isso e responsabilidade de E4 (summarizing-actions)
- NUNCA ignore indicadores Verdes que eram Vermelhos — a recuperacao e informacao valiosa
