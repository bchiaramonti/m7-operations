# Regras de Estrutura e Narrativa do WBR

> Referencia para o agente analyst e a skill consolidating-wbr.
> Define regras de consolidacao, narrativa executiva e validacao de coerencia.

---

## Indice

1. [Principios do WBR](#principios-do-wbr)
2. [Regras por Secao — WBR Estruturado](#regras-por-secao--wbr-estruturado)
3. [WBR Narrativo — Estrutura e Regras](#wbr-narrativo--estrutura-e-regras)
4. [Validacao de Coerencia](#validacao-de-coerencia)
5. [Regras de Narrativa](#regras-de-narrativa)
6. [Priorizacao de Conteudo](#priorizacao-de-conteudo)

---

## Principios do WBR

1. **Autocontido**: O leitor NAO precisa consultar relatorios parciais (E2-E5). Todo contexto necessario esta no WBR.
2. **Executivo**: Escrito para gestores e diretores. Linguagem direta, sem jargao tecnico. Numeros primeiro, explicacao depois.
3. **Acionavel**: Cada problema identificado deve ter ou uma acao existente (E4) ou uma recomendacao nova (Secao 5).
4. **Coerente**: Numeros identicos em todas as secoes. Nenhuma contradicao entre semaforo, desvios, acoes e projecoes.
5. **Conciso**: Resumo Executivo <=150 palavras. Detalhamento apenas para Vermelhos e riscos. Verdes em tabela resumida.

---

## Regras por Secao — WBR Estruturado

### Secao 1 — Resumo Executivo

**Limite**: 150 palavras (contar rigorosamente).

**Estrutura obrigatoria** (3-5 frases):
1. Frase de abertura com semaforo geral: "Dos {N} indicadores, {X} estao verdes, {Y} amarelos e {Z} vermelhos."
2. Top destaque positivo (indicador que superou ou recuperou)
3. Top risco (indicador vermelho com maior impacto ou projecao improvavel)
4. Tendencia geral (projecao de atingimento consolidado)
5. Se aplicavel: alerta de qualidade de dados (E2) que afeta confiabilidade

**NAO incluir**: detalhes de causa-raiz, lista de acoes, numeros granulares.

### Secao 2 — Desvios e Causa-Raiz

**Fonte**: `deviation-cause-report.md` (E3)

**Estrutura**:
1. Tabela-semaforo completa (todos os indicadores com Realizado, Meta, %, Status)
2. Detalhamento por indicador Vermelho:
   - Gap absoluto e percentual
   - Analise de fenomeno resumida (5 dimensoes em formato compacto)
   - Causa-raiz provavel com confianca
   - Indicadores correlacionados
3. Indicadores Amarelos: 1-2 linhas cada (tendencia + contexto)
4. Indicadores Verdes: tabela resumida sem detalhamento

**Regra de priorizacao**: Ordenar Vermelhos por gap absoluto (maior primeiro).

### Secao 3 — Acoes

**Fonte**: `action-report.md` (E4)

**Estrutura**:
1. Metricas agregadas:
   - Total de acoes ativas
   - Taxa de conclusao (%)
   - Aging medio (dias)
   - Acoes atrasadas (count)
2. Tabela de acoes criticas e atrasadas (prioridade Alta ou status Atrasada)
3. Top acoes por impacto esperado (volume ou receita)

**Regra**: Listar no maximo 10 acoes na tabela. Se houver mais, agrupar as demais em "N acoes adicionais em andamento".

### Secao 4 — Projecoes

**Fonte**: `projection-report.md` (E5)

**Estrutura**:
1. Tabela de projecoes com cenarios (base, otimista, pessimista) e classificacao
2. Destaque de indicadores "Improvavel" — listar gap e ritmo necessario
3. Indicadores "No ritmo" — mencionados brevemente como positivo
4. Tendencia consolidada: % dos indicadores em cada classificacao

**Classificacoes de projecao** (de E5):
- **No ritmo**: projecao >= 95% da meta
- **Recuperavel**: projecao entre 80-94%, com acoes ativas
- **Em risco**: projecao entre 80-94%, sem acoes ativas
- **Improvavel**: projecao < 80%

### Secao 5 — Recomendacoes

**Fonte**: Convergencia de E3, E4 e E5.

**Tres categorias de recomendacao**:

1. **Contramedidas novas**:
   - Para cada Vermelho sem acao ativa em E4
   - Recomendacao especifica com responsavel sugerido e prazo
   - Justificativa: "Indicador X esta vermelho (-Z%), sem contramedida ativa"

2. **Escalonamentos para N1**:
   - Indicadores onde a decisao ultrapassa a alcada do gestor N2
   - Exemplos: realocacao de equipe, revisao de meta, investimento
   - Formato: "Escalonar [tema] para [decisor]: [justificativa]"

3. **Ajustes de meta**:
   - Quando projecao e "Improvavel" E causa-raiz e estrutural (confianca Alta)
   - Formato: "Considerar ajuste de meta de [indicador]: meta atual R$ X, projecao R$ Y. Causa: [causa estrutural]"
   - Requer duas evidencias: projecao pessimista < 80% + causa-raiz com confianca Alta

**Cada recomendacao deve ter**: descricao + justificativa + prioridade (Alta/Media/Baixa).

---

## WBR Narrativo — Estrutura e Regras

O WBR Narrativo e um segundo output que complementa o WBR Estruturado. Enquanto o estruturado e a fonte de verdade numerica (tabelas, metricas), o narrativo e a camada de interpretacao e acao — prosa-primeiro com numeros inline, fluxo natural de leitura, cada bloco terminando em acao.

**Proposito**: O gestor le em 3 minutos e sai sabendo o que aconteceu, por que, e o que fazer.

**Template**: [wbr-narrativo.tmpl.md](../templates/wbr-narrativo.tmpl.md)

### Fluxo Narrativo

O WBR Narrativo segue o arco **Situacao → Complicacao → Acao → Perspectiva**:

| Secao | Pergunta que Responde | Extensao |
|-------|----------------------|----------|
| **Manchete** | Qual o veredito da semana? | 1-2 frases |
| **Panorama** | Como estamos no geral? | 3-5 frases |
| **O que Preocupa** | O que desviou e por que? | 1-2 paragrafos por Vermelho |
| **O que Estamos Fazendo** | As acoes estao funcionando? | 1 paragrafo |
| **Para Onde Estamos Indo** | Vamos atingir a meta? | 1-2 paragrafos |
| **O que Precisa Acontecer** | O que eu preciso fazer? | Bullets com owner + deadline |
| **Destaques Positivos** | O que deu certo? | 2-5 bullets |

### Principios de Escrita Narrativa

1. **Prosa-primeiro**: Numeros aparecem dentro de frases, nao em tabelas isoladas. "Captacao atingiu R$ 14,2M (+18% vs meta)" — nao uma tabela com uma linha.

2. **Veredito antes de evidencia**: A primeira frase de cada bloco e a conclusao, nao o contexto. "A cobertura caiu pela 4a semana e e o principal risco" — depois os numeros e causas.

3. **Comparativos obrigatorios**: Todo numero deve ter referencia. Nao "R$ 14M" sozinho — "R$ 14M (+18% vs meta de R$ 12M)" ou "R$ 14M (+8% vs semana anterior)".

4. **Causa-raiz como historia**: Nao listar dimensoes — narrar a cadeia causa-efeito. "A causa principal (confianca alta) e a realocacao de 2 assessores senior, que reduziu capacidade de contato em 30%. Agravante: base Varejo+ cresceu 12% sem reforco."

5. **Consequencia projetada**: Cada desvio deve terminar com "o que acontece se nada mudar". Conecta o problema a urgencia da acao.

6. **Decisoes, nao problemas**: "Precisamos decidir ate sexta se redistribuimos as 80 contas" — nao "ha um problema de concentracao nas contas".

7. **Reconhecimento por nome**: Mencionar pessoas que se destacaram positivamente. Gera engajamento e reforco comportamental na equipe.

### Regras de Consistencia Numerica

O WBR Narrativo deve usar **exatamente os mesmos numeros** do WBR Estruturado. A diferenca e a apresentacao, nao os dados.

- Realizado, Meta e % devem ser identicos
- Classificacoes (Verde/Amarelo/Vermelho) identicas
- Projecoes e cenarios identicos
- Contagem de acoes e status identicos

### Extensao Alvo

O WBR Narrativo deve ter entre **1.5 a 2.5 paginas** (600-1000 palavras). Se ultrapassar:
- Comprimir Panorama (3 frases max)
- Amarelos: 1 frase cada (tendencia apenas)
- Destaques: 2 bullets max

---

## Validacao de Coerencia

Antes de salvar o WBR, verificar:

### Coerencia Numerica

| Verificacao | Regra |
|-------------|-------|
| Semaforo Resumo vs Secao 2 | Contagem Verde/Amarelo/Vermelho identica |
| Realizado/Meta Secao 2 vs E3 | Valores identicos (mesma precisao decimal) |
| Acoes Secao 3 vs E4 | Contagem e status identicos |
| Projecoes Secao 4 vs E5 | Valores e classificacoes identicos |

### Coerencia Logica

| Verificacao | Regra |
|-------------|-------|
| Vermelho com projecao "No ritmo" | Inconsistente — verificar se projecao considera acoes corretivas |
| Verde com recomendacao de ajuste | Inconsistente — Verdes nao precisam de ajuste |
| Acao ativa para indicador Verde | Verificar se acao e residual de ciclo anterior (OK) |
| Recomendacao sem justificativa | Invalido — toda recomendacao precisa de dados de suporte |
| Indicador em Secao 2 ausente na Secao 4 | Invalido — todos devem ter projecao |

### Coerencia de Alertas (E2)

Se o Data Quality Report (E2) registrou alertas de Atencao:
- Incluir nota de rodape no WBR: "Dados de [indicador] com ressalva: [alerta]"
- No Resumo Executivo, mencionar se alertas afetam confiabilidade das conclusoes

---

## Regras de Narrativa

### Tom

- **Direto**: Frases curtas, voz ativa. "Captacao ficou 40% abaixo da meta" (nao "foi observado que...")
- **Numerico**: Liderar com o numero. "R$ 15M vs meta de R$ 25M" antes da explicacao
- **Imparcial**: Descrever fatos, nao julgar pessoas. "Assessor A concentra 30% do gap" (nao "Assessor A esta com performance ruim")

### Conectores entre Secoes

O WBR deve fluir como narrativa, nao como colagem de relatorios. Usar conectores:

- Secao 2 → 3: "Para enderecar os desvios acima, as seguintes acoes estao em andamento:"
- Secao 3 → 4: "Com as acoes em curso, as projecoes para o final do periodo sao:"
- Secao 4 → 5: "Com base na analise de desvios, acoes e projecoes, recomenda-se:"

### Formatacao

- Tabelas para dados comparativos (semaforo, acoes, projecoes)
- Bullet points para listas curtas (recomendacoes, destaques)
- Bold para numeros criticos e classificacoes
- Nao usar emojis, cores ou formatacao visual alem de Markdown padrao

---

## Priorizacao de Conteudo

Quando o WBR ficar muito longo (>3 paginas), aplicar:

| Prioridade | Conteudo | Tratamento |
|-----------|----------|------------|
| **Alta** | Vermelhos + acoes criticas + projecoes Improvavel | Detalhamento completo |
| **Media** | Amarelos + acoes em andamento + projecoes Em Risco | 1-2 linhas cada |
| **Baixa** | Verdes + acoes concluidas + projecoes No Ritmo | Tabela resumida |

Objetivo: WBR entre 2-3 paginas. Se ultrapassar, comprimir conteudo de prioridade Baixa.

---

## WBR Narrativo HTML — Versao Visual

O WBR Narrativo HTML e uma terceira camada de output que complementa o Estruturado (tabelas) e o Narrativo MD (prosa). Apresenta os mesmos dados com visualizacoes SVG inline.

**Template**: [wbr-narrativo.tmpl.html](../templates/wbr-narrativo.tmpl.html)
**Guia de geracao**: [wbr-html-guide.md](wbr-html-guide.md)

**Regras de consistencia**: Todos os numeros, classificacoes e projecoes devem ser identicos ao WBR Estruturado e ao WBR Narrativo MD. A diferenca e exclusivamente visual.

**Design system**: CSS pre-validado para M7-2026 (TWK Everett, verde caqui, lime, off-white). Score A (Production-ready). NAO alterar o CSS do template.

**Outputs E6 (4 artefatos)**:

| # | Artefato | Formato | Publico-alvo |
|---|----------|---------|-------------|
| 1 | WBR Estruturado | `.md` | Fonte de verdade numerica, referencia analitica |
| 2 | WBR Narrativo | `.md` | Leitura rapida em 3 min, distribuicao por chat/email |
| 3 | WBR Narrativo Visual | `.html` | Apresentacao em rituais, visualizacao de dados |
| 4 | WBR Narrativo PDF | `.pdf` | Distribuicao por email/WhatsApp, impressao |
