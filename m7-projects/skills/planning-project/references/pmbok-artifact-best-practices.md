# Racional PMBOK + Ágil por Artefato

Explica **por que** cada critério de aceite existe, citando a fonte (PMBOK 7e, Doerr/Google OKRs, ISO 31000, PMI Stakeholder Cube, Scrum Guide). Use esta reference quando o usuário questionar "por que isso importa?" ou quando a skill precisa apresentar autoridade ao aplicar push-back.

**Não duplicar** os critérios aqui — este documento é **racional**, não checklist. Para checklist, ver [acceptance-criteria.md](acceptance-criteria.md).

## Índice

- [Fontes canônicas](#fontes-canônicas)
- [01 · Contexto & Escopo](#01--contexto--escopo)
- [02 · OKRs](#02--okrs)
- [03 · WBS/EAP](#03--wbseap)
- [04 · Cronograma](#04--cronograma)
- [05 · Roadmap & Marcos](#05--roadmap--marcos)
- [06 · Recursos & Dependências](#06--recursos--dependências)
- [07 · Plano de Comunicação](#07--plano-de-comunicação)
- [08 · Riscos](#08--riscos)
- [09 · Calendário](#09--calendário)

## Fontes canônicas

| Fonte | Escopo | Usada em |
|---|---|---|
| **PMBOK Guide 7th Edition** (PMI, 2021) | Princípios + Performance Domains | Artefatos 01, 03, 04, 05, 06, 07, 08 |
| **Measure What Matters** (John Doerr, 2017) | OKRs — Objectives & Key Results | Artefato 02 |
| **Google re:Work — OKR Playbook** | OKRs operacionais | Artefato 02 |
| **ISO 31000:2018** — Risk Management Guidelines | Framework de riscos | Artefato 08 |
| **PMI Stakeholder Engagement Assessment Matrix** | Categorização de engagement | Artefato 07 |
| **Scrum Guide** (Schwaber & Sutherland, 2020) | Mindset ágil — incrementos + aceite | Meta-princípio da skill |

## 01 · Contexto & Escopo

**Propósito PMBOK:** O **Project Charter** autoriza formalmente o projeto e dá autoridade ao gerente de projeto. O **Scope Statement** detalha o produto/resultado esperado e estabelece fronteiras.

**Por que métrica quantitativa + timeframe na estrela guia:**
- PMBOK 7e, Performance Domain "Measurement": planejamento sem métrica é narrativa
- Sem timeframe, não há quando declarar sucesso/fracasso
- Doerr: "If it doesn't have a number, it's not a KR" — aplica-se também à meta-estrela

**Por que "não faremos" explícito (escopo negativo):**
- PMBOK 7e, Performance Domain "Planning": `Scope Definition` inclui deliverables **excluídos**
- Princípio do **gold plating** — times tendem a entregar a mais "por gentileza", estourando prazo
- Stakeholders interpretam escopo por omissão — o que não está negado, está assumido

**Por que critérios de aceite do projeto:**
- PMBOK: cada entregável tem acceptance criteria; o **projeto como um todo** também
- Sem critérios, o "fechamento" (closing phase) vira subjetivo

## 02 · OKRs

**Propósito (Doerr):** alinhar esforço ao resultado; foco; cadência de revisão. "Structured goal-setting helps organizations stay focused on what matters."

**Por que 2-3 Objetivos:**
- Google re:Work: 3-5 Objetivos no máximo por ciclo; para projetos, 2-3 é refinamento
- Foco cognitivo: humanos acompanham 7±2 itens; 3 Objetivos × 4 KRs = 12 coisas para rastrear já é limite
- 1 Objetivo = provavelmente projeto pequeno demais para merecer OKR; 5+ = diluição

**Por que 3-5 KRs por Objetivo:**
- Menos de 3: Objetivo trivial ou mal decomposto
- Mais de 5: foco diluído, sinal de que o Objetivo cobre mais de um resultado

**Por que KRs devem ser outcomes, não outputs:**
- Doerr: "Output is what you produce; outcome is what changes in the world because of it"
- Exemplo canônico: "entregar playbook" (output) vs "tempo de decisão cai 30%" (outcome)
- KR de output mede esforço; KR de outcome mede impacto. Plano de projeto já tem cronograma para esforço — OKR precisa medir o que muda

**Por que baseline + target + fonte:**
- Sem baseline, "subir 20%" é indefinido (20% de quê?)
- Sem target, não há fim de jogo
- Sem fonte de medição, a medição vira negociação política no final

## 03 · WBS/EAP

**Propósito PMBOK:** Work Breakdown Structure é **decomposição hierárquica do trabalho** em pacotes gerenciáveis. PMBOK 7e trata como base de planejamento e controle.

**Regra dos 100%:**
- PMBOK: WBS cobre 100% do escopo E apenas o escopo
- Pacote que não aparece no WBS não será executado (ninguém tem responsabilidade); pacote fora do escopo é gold plating

**Regra 8/80:**
- Prática consolidada (não está literalmente no PMBOK 7e mas é referência de várias certificações PMI)
- Limite inferior ~8h: abaixo disso, vira tarefa de to-do list, não unidade de planejamento
- Limite superior ~80h: acima disso, esconde incerteza e impede tracking granular
- Exceções ok mas com consciência — pacote de 200h é sinal de decomposição incompleta

**MECE (Mutually Exclusive, Collectively Exhaustive):**
- Origem McKinsey, aplicável ao WBS
- Exclusividade evita dois pacotes reivindicarem o mesmo trabalho (dupla contagem de esforço)
- Exaustividade evita buracos (trabalho que ninguém percebeu)

**Um único responsável por pacote:**
- PMBOK Performance Domain "Team": responsabilidade compartilhada = responsabilidade de ninguém
- Não impede que várias pessoas **executem** o pacote; impede que várias sejam **responsáveis** por ele

**Entregável verificável:**
- PMBOK: cada pacote deve ter deliverable identificável
- Sem artefato tangível, status vira auto-declaração ("quase pronto" eterno)

## 04 · Cronograma

**Propósito PMBOK:** sequenciamento temporal com dependências e identificação do caminho crítico (Critical Path Method, CPM).

**Dependências explícitas (FS, FF, SS, SF):**
- PMBOK: 4 tipos de dependência — Finish-to-Start (FS) é default, mas FF/SS/SF existem e são válidos
- Forçar tipo explícito previne série "por hábito" quando paralelismo é possível

**Buffer ≥10%:**
- PMBOK reconhece **management reserve** como prática de incerteza conhecida
- 10% é referência prática; projetos de alta incerteza (R&D) podem precisar 30%+
- Buffer zero é sinal de otimismo — ou prazo externo forçado, que deveria virar risco em §08

**Caminho crítico:**
- CPM: sequência de atividades que determina a duração mínima do projeto
- Se caminho crítico não está identificado, gestão de prazo vira reativa
- Atrasos em pacotes **fora** do caminho crítico consomem folga sem impactar prazo final

**Paralelismo:**
- Scrum/ágil enfatiza entrega em paralelo quando dependências permitem
- PMBOK aceita fast-tracking como técnica de compressão de cronograma

## 05 · Roadmap & Marcos

**Propósito PMBOK + ágil:** comunicar trajetória do projeto em **ondas** — detalhado perto, macro longe (rolling wave planning).

**Marcos com DoD (Definition of Done):**
- Vocabulário Scrum: "Done" é critério compartilhado, não julgamento individual
- PMBOK: marcos são pontos no tempo de duração zero com significado (aceite, transição, decisão)

**Marcos com owner:**
- Sem owner, marco fica sem "declarador" — situação que gera ambiguidade em momentos sensíveis (go/no-go)

**Frequência de marcos:**
- Heurística: projetos de 3m → 1 marco/mês; 6m → 1 marco/~6sem; 12m → 1 marco/~2m
- Menos frequente que isso perde capacidade de correção de rota
- Rolling wave: marcos próximos são detalhados; marcos distantes são tentativos

**Marco ≠ entregável:**
- PMBOK: deliverable é artefato; marco é **ponto temporal** com significado (aprovação, decisão, handoff)
- "Playbook entregue" é deliverable; "Playbook aprovado pelo comitê em DD/MM" é marco

## 06 · Recursos & Dependências

**Propósito PMBOK:** Performance Domain "Team" + Resource Planning — explicitar capacidade e dependências externas.

**Dedicação explícita:**
- "Envolvido" sem % não permite cálculo de capacidade
- PMBOK: resource leveling depende de entradas quantitativas

**Proteção de agenda para <50%:**
- Abaixo de 50%, risco de split-attention é alto (Lei de Brooks: adicionar pessoas tarde não acelera)
- Plano de proteção (bloquear dias específicos, reduzir outros compromissos) é intervenção ativa

**Dependências externas com handoff + impacto + plano B:**
- PMBOK: external dependencies são constraints — precisam aparecer como entradas de cronograma
- Sem data, handoff vira negociação em crise
- Sem plano B, "atraso da dependência" vira "atraso do projeto" 1:1

## 07 · Plano de Comunicação

**Propósito PMBOK:** Performance Domain "Stakeholders" — alinhar expectativas, reduzir surpresa, mapear engajamento.

**PMI Stakeholder Engagement Assessment Matrix:**
- Cinco categorias: Unaware, Resistant, Neutral, Supportive, Leading
- Framework PMI padrão para categorizar stakeholders por posição atual vs desejada
- Estratégia muda conforme gap: Resistant → Neutral requer negociação; Supportive → Leading requer investimento de relacionamento

**RACI com Accountable singular:**
- RACI clássico: cada linha tem **exatamente 1 A**
- Dois A = ambos apontam o outro quando falha
- Zero A = entregável órfão
- Origem: General Electric nos anos 1970; padrão PMI desde a 5ª edição

**Rituais com output declarado:**
- Scrum: cada evento tem outcome específico (Sprint Planning produz Sprint Backlog)
- Reunião sem output = hábito, não prática

**Cadência executiva:**
- Sponsor sem ritual recorrente aparece no pior momento (crise, surpresa)
- Cadência mensal + ad-hoc por exceção > ad-hoc puro

## 08 · Riscos

**Propósito PMBOK + ISO 31000:** identificar, analisar, planejar resposta a incertezas que podem afetar objetivos (positivos ou negativos).

**Risco vs problema:**
- **Risco**: evento futuro, incerto, potencial
- **Problema** (ou "issue"): evento presente, certo, atual
- Confundir os dois leva a registrar "projeto atrasar" como risco quando é sintoma/consequência
- Disciplina ISO 31000: descrever risco como "causa → evento → consequência"

**Probabilidade × Impacto:**
- PMBOK: matriz qualitativa mínima (Alta/Média/Baixa em cada eixo)
- Projetos mais maduros usam escalas quantitativas (probabilidade %, impacto $)
- Sem dimensão, priorização vira negociação

**Trigger observável:**
- PMBOK: risk trigger é sinal de materialização
- Sem trigger, resposta vira reativa (descobrimos quando já estourou)
- Exemplo: risco "atraso do handoff" — trigger "≥5 dias de atraso comunicados pelo fornecedor"

**Estratégias de resposta (PMBOK):**
- **Ameaças**: avoid, transfer, mitigate, accept
- **Oportunidades**: exploit, share, enhance, accept
- Acceptance não é "ignorar" — é decisão consciente de não investir em contramedida, às vezes com reserve

**Oportunidades (riscos positivos):**
- PMBOK 7e integra explicitamente opportunities no risk management
- Projeto que só mapeia ameaças está defensivo; mapear oportunidades força pensar em upside
- Exemplo: "adoção 2x esperada" — estratégia enhance (investir para capturar mais)

**Mínimo 5 riscos:**
- Heurística prática: projetos reais têm dependências, pessoas-chave, premissas, integrações — cada categoria gera ≥1 risco
- 2-3 riscos mapeados geralmente indica superficialidade, não ausência real

## 09 · Calendário

**Propósito:** projeção temporal de rituais + marcos + eventos externos (feriados, congelamentos, férias).

**Cadência compatível:**
- Mais rituais ≠ melhor comunicação
- Muitos rituais semanais saturam agenda e viram hábito canceled-reschedule (entropia)

**Revisões de transição de fase:**
- PMBOK: phase gates (stage-gates) são pontos formais de decisão entre fases
- Sem ritual de aceite, entramos na fase seguinte com premissas não validadas

**Overbooking:**
- Se PM tem >4h/dia em reuniões recorrentes, sobra pouco para coordenar e pensar
- Sinal de que ou agenda está mal desenhada, ou escopo está maior que capacidade

**Revisões trimestrais para projetos >6m:**
- Sponsors em projetos longos perdem contexto sem checkpoint macro
- 45min a cada 3m com sponsor + líder é intervalo defensivo mínimo
- Evita o padrão "projeto de 12m que sponsor só descobre divergência no m9"

## Como usar esta reference durante o push-back

Quando a skill aplica um push-back e o usuário pergunta "por que isso importa?", a skill pode:

1. Citar a fonte concisamente (ex.: "PMBOK 7e trata isso em Performance Domain Planning porque...")
2. Dar o exemplo concreto do que acontece sem o critério (ex.: "sem baseline, em 6 meses ninguém vai conseguir dizer se mudamos")
3. Oferecer a saída: "se mesmo assim você quer sobrescrever, me dá uma frase de justificativa e eu registro como OVERRIDE"

Não **lê** esta reference inteira na conversa — apenas o trecho relevante. Progressive disclosure também em interação.
