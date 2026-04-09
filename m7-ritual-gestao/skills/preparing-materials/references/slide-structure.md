# Estrutura de Slides — Ritual de Gestao

Referencia para o material-generator sobre a estrutura do deck de ritual. O ritual e organizado **por especialista**, nao por KPI.

---

## Sumario

- [Arquitetura geral](#arquitetura-geral)
- [Slide 1: Capa](#slide-1-capa)
- [Slide 2: Visao Geral (Matriz)](#slide-2-visao-geral-matriz)
- [Slide 3: Agenda](#slide-3-agenda)
- [Bloco por Especialista (4 slides)](#bloco-por-especialista-4-slides)
  - [Dashboard](#dashboard)
  - [Analise](#analise)
  - [Projecao](#projecao)
  - [Sugestoes PPI](#sugestoes-ppi)
- [Agenda Transicao](#agenda-transicao)
- [Status Plano de Acao](#status-plano-de-acao)
- [Plano de Acao (tabela)](#plano-de-acao-tabela)
- [Encerramento](#encerramento)
- [Regras gerais de design](#regras-gerais-de-design)
- [Calculo de slides](#calculo-de-slides)

---

## Arquitetura geral

O deck segue esta estrutura fixa, derivada do Card de Performance da vertical:

```
1. Capa
2. Visao Geral (Matriz 7 colunas)
3. Agenda

--- Bloco Especialista 1 ---
4. [Esp1] Dashboard
5. [Esp1] Analise
6. [Esp1] Projecao
7. [Esp1] Sugestoes PPI
8. Agenda (transicao: Esp1 concluido, Esp2 atual)

--- Bloco Especialista 2 ---
9.  [Esp2] Dashboard
10. [Esp2] Analise
11. [Esp2] Projecao
12. [Esp2] Sugestoes PPI
13. Agenda (transicao: todos concluidos, Encerramento atual)

--- Encerramento ---
14. Status Plano de Acao
15. Plano de Acao (tabela)
16. Encerramento
```

**Regra**: Um bloco por especialista listado no Card de Performance (`metadata.responsaveis`). Cada bloco tem 3 ou 4 slides (Sugestoes PPI e **condicional** — gerar APENAS se o WBR contem secao de sugestoes por assessor).

**Formula**: `total_slides = 6 + n_especialistas * (slides_por_bloco + 1)`
- `slides_por_bloco` = 4 se WBR tem sugestoes, 3 se nao tem
- `+1` por bloco = slide de agenda transicao

Exemplo: 2 especialistas sem sugestoes = 6 + 2*(3+1) = 14 slides.
Exemplo: 2 especialistas com sugestoes = 6 + 2*(4+1) = 16 slides.

---

## Slide 1: Capa

| Campo | Fonte | Exemplo |
|-------|-------|---------|
| Titulo | Fixo + Card | "Ritual de Gestao N3 {Vertical}" |
| Subtitulo | CICLO.md | "Resultados {Mes} {Ano} \| Ciclo {data}" |
| Area/Nivel | Card | "Area: {vertical} \| Nivel: {nivel}" |
| Diretos | Card | "Diretos: {especialista1} \| {especialista2}" |
| Footer | Fixo | "M7 Investimentos" |
| Background | Design System | DARK (#424135) |

---

## Slide 2: Visao Geral (Matriz)

Matriz de 4 colunas com semaforo por indicador, desdobrada por especialista para o mes corrente.

### Estrutura da tabela

```
| Indicador | N3 | Esp1 | Esp2 |
```

- **Header row 1**: periodo ("Mes Corrente ({{periodo_mes_label}})") spanning todas as colunas de dados
- **Header row 2**: estrutura (N3, nome especialista 1, nome especialista 2)
- **Colunas de dados**: tons progressivos de verde-caqui (#424135 → #4f4e3c → #5f5e4c)

### Secoes de indicadores (rows agrupadas — derivadas do Card)

> **NUNCA hardcodar indicadores.** A lista de indicadores vem do campo `kpi_references` do Card de Performance da vertical. Cada indicador tem um `papel` que determina a secao.

| Secao | Header BG | Header Color | Criterio de inclusao |
|-------|-----------|-------------|----------------------|
| KPIs — Resultado | `#eef77c` (lime) | `#424135` | Indicadores com `papel: kpi_principal` no Card |
| PPIs — Processo | `#79755c` (gray) | `#FFFFFF` | Indicadores com `papel: ppi_funil` ou `papel: ppi_sugestoes` no Card |

**Regra de preenchimento:**
1. Ler `kpi_references[]` do Card de Performance
2. Agrupar por `papel`: `kpi_principal` → secao KPIs, `ppi_*` → secao PPIs
3. Para cada indicador do Card, buscar meta + realizado + desvio no **Painel de Indicadores** do WBR (Secao 1.5)
4. Se o WBR nao tem dados para um indicador do Card → exibir "—" com dot cinza (verde-caqui-200). **NUNCA omitir um indicador do Card**
5. Ordenar dentro de cada secao: vermelhos primeiro (por gap absoluto), amarelos, verdes

### Celula com status

Cada celula mostra: valor + meta (subscript) + desvio% (colorido) + dot de semaforo.

```html
<div class="status-cell">
  <div class="cell-data">
    <span class="cell-value">R$ 49,5K</span>
    <span class="cell-meta">meta 73,4K</span>
    <span class="cell-deviation negative">-32,6%</span>
  </div>
  <span class="status-dot red"></span>
</div>
```

- Dados nao disponiveis (PPIs sem dados): exibir "—" em cor #BDBDBD
- Legenda no rodape: No alvo (verde), Atencao (amarelo), Critico (vermelho), Sem meta (cinza)

---

## Slide 3: Agenda

Lista de blocos do ritual, um por especialista + encerramento.

| # | Titulo | Subtitulo | Tempo |
|---|--------|-----------|-------|
| 1 | {Especialista 1} | Resultados, analises e acoes da estrutura | ~20 min |
| 2 | {Especialista 2} | Resultados, analises e acoes da estrutura | ~20 min |
| N+1 | Encerramento | Resumo do plano de acao e proximos passos | ~10 min |

- Cada item: card com borda esquerda lime (#eef77c), numero em circulo verde-caqui (#424135), tempo em lime
- Tempo por especialista: ~20 min (fixo)
- Tempo encerramento: ~10 min (fixo)
- Background: OFF_WHITE (#fffdef)

---

## Bloco por Especialista (4 slides)

Repetido para cada especialista. Todos os dados vem do WBR desdobrado por N2.

### Dashboard

**Header**: Avatar (iniciais, circulo lime) + nome + badge periodo

**Layout** (3 areas verticais):

1. **Tabela de indicadores** — Mesmos grupos da Matriz (KPIs + PPIs derivados do Card via `kpi_references`), filtrados para este especialista. Rows: Meta, Real, Desvio (dots coloridos). Dados do Painel de Indicadores do WBR (Secao 1.5), coluna do especialista.

2. **Cards lado a lado** (2 colunas):
   - **Acoes Executadas** (header verde-caqui): bullets com dots coloridos (verde=feito, amarelo=parcial)
   - **Acoes Planejadas** (header verde-caqui): bullets com dots coloridos (vermelho=urgente, amarelo=planejado)

3. **Riscos e Pontos de Atencao** (header vermelho #e40014): ate 3 risk items com borda esquerda vermelha

**Fontes de dados**:
- Tabela indicadores: WBR Secao 1.5 (Painel), coluna N2 do especialista
- Acoes executadas/planejadas: WBR + plano-de-acao.csv
- Riscos: WBR secao de riscos

### Analise

**Header**: Avatar + nome + desvio principal (ex: "R$ 17.898 vs R$ 44.223 (-59,5%)")

**Layout** (2 paineis):

1. **Painel esquerdo (55%)** — 2 graficos de barras horizontais divergentes (zero no centro):
   - **Receita — Desvio em R$**: barras por assessor, ordenadas por desvio (positivo acima, negativo abaixo). Cores: verde (`#4CAF50`) para positivo, vermelho (`#e40014`) para negativo. Labels: nome assessor (8px), valor (8px weight 700).
   - **Volume — Desvio em R$**: mesmo layout para volume.

2. **Painel direito (45%)** — Card **Diagnostico 3G**:
   - **PROBLEMA** (vermelho): indicador principal + gap em R$
   - **ONDE OCORREU** (lime): quantos assessores abaixo + top 3 gaps + % do gap total (highlight amarelo)
   - **POR QUE?** (verde-caqui): 3 causas numeradas com metricas em vermelho
   - **DESTAQUE POSITIVO** (verde, fundo `#EFE`): 1-2 metricas positivas

**Regras dos graficos de barras**:
- Barras alinhadas ao centro (zero), com zona negativa a esquerda e positiva a direita
- Linha central cinza (`#79755c`) de 1px
- Altura de cada barra: 8px, border-radius 2px
- Label do assessor: 75px, font-size 8px, text-align right, truncate com ellipsis
- Valor: font-size 8px, weight 700, cor verde/vermelho conforme sinal
- Ordenar por valor absoluto descendente dentro de cada zona

**Fontes de dados (Analise)**:
- **Barras por assessor**: JSON consolidado (`DADOS_PATH`), filtrar por `indicator_id` receita/volume, `especialista` = nome, `assessor` != null. Extrair `realizado`, `meta`, gap. **Fallback**: WBR narrativo (secao analise desagregada)
- **Diagnostico 3G**: WBR narrativo (secao causa-raiz N2)

### Projecao

**Header**: Avatar + nome + "Projecao {Mes seguinte}" + tag "PROJECAO"

**Layout** (2 colunas):

1. **Coluna esquerda**:
   - **Pipeline card** (header verde-caqui): funil por estagio do CRM
     - Cada estagio: label + % probabilidade (colorido) + barra horizontal + contagem estagnados
     - Estagios: Prospeccao (25%), Investigacao (25%), Apresentacao (50%), Proposta (50%), Emissao (75%)
     - Totais no rodape: "Fecha {mes}" + "Estagnados" (vermelho se >5) + "Vol. Pond."
   - **Tags grid** (2×2): risk cards (fundo #FEE, borda vermelha) + success cards (fundo #EFE, borda verde)

2. **Coluna direita**:
   - **Gauges** (2 semicirculos SVG lado a lado): Receita + Volume. Cor do arco conforme atingimento (<85% vermelho, 85-95% amarelo, >95% verde).
   - **Projecao Receita**: card com rows (recorrente + pipeline ponderado) + total verde-caqui com desvio
   - **Projecao Volume**: mesmo layout

**Fontes de dados (Projecao)**:
- **Pipeline por estagio**: JSON consolidado (`DADOS_PATH`), filtrar indicadores de funil (`oportunidades_ativas`, `oportunidades_estagnadas`) por especialista. **Fallback**: WBR narrativo (secao pipeline detalhado)
- **Cenarios e projecao receita/volume**: WBR narrativo (secao projecoes N2)
- **Risk/success tags**: WBR narrativo (secao riscos N2)

### Sugestoes PPI (CONDICIONAL)

> **Gerar este slide APENAS se o WBR contem secao de sugestoes por assessor.** Se o WBR nao tem dados de sugestoes, pular este slide — o bloco do especialista tera 3 slides em vez de 4.

**Header**: Avatar + nome + "Sugestoes PPI" + tag lime "SUGESTOES"

**Layout**:

1. **KPI strip** (4 cards horizontais):
   - Total Sugestoes (verde-caqui)
   - Tx Tratamento (cor conforme semaforo)
   - Tx Execucao (cor conforme semaforo)
   - Tx Vencimento (cor conforme semaforo)

2. **Tabela detalhada por assessor**:
   - Colunas: Assessor, Total, Exec., Vencida, Ativa, Tx Tratam., Tx Vencim.
   - Taxas com badges coloridos (verde >80%, amarelo 50-80%, vermelho <50%)
   - Row total no rodape (fundo verde-caqui, texto branco)
   - Ordenar por Tx Tratamento ascendente (piores primeiro)

---

## Agenda Transicao

Mesmo layout da Agenda (slide 3), mas com estado atualizado:
- Especialistas concluidos: circulo verde com checkmark, opacity 0.7, borda esquerda verde
- Especialista atual: circulo verde-caqui, opacity 1, borda esquerda lime, fundo #FFFDF5
- Proximos: circulo cinza, opacity 0.5, borda esquerda cinza

Gerar 1 slide de transicao entre cada bloco de especialista e antes do encerramento.

---

## Status Plano de Acao

**Header**: "Status do Plano de Acao" + tag "{N} ACOES | CICLO {data}"

**Layout** (grid 2×2, coluna esquerda span 2 rows):

1. **Status Geral** (span 2 rows): donut/pie chart com contagem total no centro. Segmentos por status.
2. **Acoes por Semana (Prazo)**: stacked bar chart horizontal por semana ISO.
3. **Acoes por Responsavel**: stacked bar chart horizontal por nome.

**Legenda global** no rodape:
- Nao iniciada (#BDC3C7)
- Em andamento (#3498DB)
- Atrasada (#E74C3C)
- Concluida (#27AE60)

---

## Plano de Acao (tabela)

**Header**: "Plano de Acao: {N} acoes para {objetivo}" + tag "PLANO DE ACAO"

**Tabela completa**:

| Col | Largura | Conteudo |
|-----|---------|----------|
| # | 22px | Numero em circulo lime |
| Acao | flex | Descricao da acao |
| Causa | 90px | Indicador/metrica que originou |
| Resp. | 60px | Nome bold verde-caqui |
| Prazo | 42px | DD/MM em cinza |
| Status | 70px | Badge colorido (nao iniciada/andamento/atrasada/concluida) |

- Rows alternadas (#F9F9F9)
- Dados: plano-de-acao.csv filtrado para a vertical + acoes novas do WBR
- Ordenar por prazo ascendente

---

## Encerramento

**Background**: DARK (#424135)

| Campo | Conteudo |
|-------|----------|
| Titulo | "Proximos Passos" |
| Subtitulo | "Foco em {objetivo principal}" |
| Cards (3) | Top 3 prioridades: titulo lime + descricao branca |
| Footer | "Ritual de Gestao N3 {Vertical} \| M7 Investimentos \| {data}" |

- Cards: fundo rgba(255,255,255,0.1), border-radius 8px
- Numeros em lime (#eef77c), bold, 24px
- Titulo de cada card em lime, descricao em branco 12px

---

## Regras gerais de design

| Regra | Detalhe |
|-------|---------|
| Dimensoes slide | 720pt × 405pt (16:9) |
| Fundo content slides | `#fffdef` (OFF_WHITE), nunca branco puro |
| Fundo dark slides | `#424135` (capa, encerramento) |
| Header slides | `#424135`, h1 branco 18px weight 400, tags em lime |
| Section labels | `#eef77c` (lime) para KPIs, `#79755c` (gray) para PPIs |
| Fonte | `"twkEverett", Arial, sans-serif` |
| Font weight | 400 headings, 500 card headers, 700 **apenas** metricas/numeros. NUNCA usar keyword `bold` |
| Font min | 8px minimo absoluto. 10px para body/tabela. Ver escala tipografica abaixo |
| line-height | 1.4 minimo em todo body text |
| Semaforo | Verde `#4CAF50`, Amarelo `#FFC107`, Vermelho `#e40014` |
| Sem meta | Dot cinza `#d0d0cc` com borda `#aeada8` |
| Risk cards | Fundo `#FEE`, borda `#e40014`, titulo vermelho |
| Success cards | Fundo `#EFE`, borda `#4CAF50`, titulo verde |
| Avatar | Circulo 32px, fundo lime, iniciais verde-caqui weight 700 |
| Footer | Numero de pagina cinza `#79755c`, 9px, alinhado a direita |
| Dados | Identicos ao WBR — mesmo arredondamento, mesmas unidades |

---

## Valores CSS Mandatorios

O agent DEVE usar exatamente estes valores. Nao sao diretrizes — sao requisitos.
Se o conteudo nao cabe com estes tamanhos, REDUZA CONTEUDO (menos rows, texto abreviado), NAO reduza fontes ou espacamento.

> **Legibilidade > Completude.** Se uma tabela tem muitas rows para o slide a 10px: (1) dividir em 2 slides, (2) abreviar nomes de indicadores, (3) remover linhas menos criticas. **NUNCA** reduzir fonte abaixo de 8px.

### Paleta de cores permitidas (EXAUSTIVA)

| Token | Hex | Uso |
|-------|-----|-----|
| verde-caqui | `#424135` | Texto primario, bg headers, headings |
| off-white | `#fffdef` | Bg slides conteudo, superficies claras |
| lime | `#eef77c` | Labels KPI, acentos decorativos. **NUNCA como texto sobre fundo claro** |
| verde-medio | `#4f4e3c` | Headers secundarios, bg card headers |
| verde-claro | `#79755c` | Texto muted, meta, subtitulos, footers |
| verde-caqui-50 | `#f6f6f5` | Rows alternadas, backgrounds sutis |
| verde-caqui-100 | `#d0d0cc` | Bordas, separadores |
| verde-caqui-200 | `#aeada8` | Estados desabilitados, dot cinza "sem meta" |
| white | `#ffffff` | Fundo de cards internos |
| success | `#4CAF50` | Positivo, dot verde, titulo success card |
| warning | `#FFC107` | Atencao, dot amarelo |
| error | `#e40014` | Critico, dot vermelho, borda risk card |
| blue | `#3B82F6` | Status "em andamento" |
| risk-bg | `#FEE` | Fundo risk cards |
| success-bg | `#EFE` | Fundo success cards |

**Qualquer outro hex e VIOLACAO.** Mapeamento dos valores incorretos comuns:

| Valor incorreto | Substituir por | Token |
|-----------------|---------------|-------|
| `#2C3E50` | `#424135` | verde-caqui |
| `#D0D0D0`, `#E0E0E0` | `#d0d0cc` | verde-caqui-100 |
| `#BDBDBD` | `#aeada8` | verde-caqui-200 |
| `#F0F0F0`, `#F5F5F5`, `#F9F9F9` | `#f6f6f5` | verde-caqui-50 |
| `#9E9E9E` | `#79755c` | verde-claro |
| `#BDC3C7` | `#aeada8` | verde-caqui-200 |
| `#3498DB` | `#3B82F6` | blue |
| `#E74C3C` | `#e40014` | error |
| `#27AE60` | `#4CAF50` | success |

### Escala tipografica

| Elemento | Tamanho Min. | Weight |
|----------|-------------|--------|
| Header h1 (barra escura) | 18px | 400 |
| Section tag (barra escura) | 11px | 400 |
| Texto tabela/body | 10px | 400 |
| Valor metrica (cell-value) | 10px | 700 |
| Meta (cell-meta) | 8px | 400 |
| Desvio (cell-deviation) | 8px | 700 |
| Legenda | 9px | 400 |
| Card header (sub-titulo) | 11px | 500 |
| Body em cards/diagnosticos | 10px | 400 |
| Risk/alert items | 10px | 400 |
| Status badge | 9px | 700 |
| Page number | 9px | 400 |
| **Minimo absoluto** | **8px** | qualquer |

**NUNCA** font-size abaixo de 8px. **NUNCA** usar keyword `bold` — usar 400, 500 ou 700.

### Espacamento minimo (grid 4px)

| Elemento | Min. |
|----------|------|
| Content area padding | `12px 16px` |
| Table cell padding | `4px 4px` |
| Status dot | 14px × 14px |
| Legend dot | 8px × 8px |
| Card body padding | 12px |
| Gap entre elementos | 8px |
| line-height body text | 1.4 |

Todos os valores de espacamento DEVEM ser multiplos de 4px: 4, 8, 12, 16, 20, 24, 32.

---

## Calculo de slides

| Componente | Slides |
|------------|--------|
| Capa + Visao Geral + Agenda | 3 |
| Por especialista | 3 ou 4 (dashboard + analise + projecao + sugestoes PPI se disponivel) |
| Agenda transicao (entre blocos) | n_especialistas |
| Status + Plano + Encerramento | 3 |
| **Total** | **6 + n_especialistas × (slides_por_bloco + 1)** |

Exemplo Consorcios sem sugestoes (2 esp): 6 + 2*(3+1) = 14 slides.
Exemplo Consorcios com sugestoes (2 esp): 6 + 2*(4+1) = 16 slides.
