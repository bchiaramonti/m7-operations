# Playbook de Push-backs

Catálogo tático de push-backs por artefato. Quando um critério de [acceptance-criteria.md](acceptance-criteria.md) falha, a skill usa as frases e perguntas aqui como **matéria-prima** — não necessariamente literal, mas no espírito — para confrontar o usuário.

**Meta por artefato: ≥2 push-backs** (spec 06). Este playbook totaliza ≥20 (média de 2-3 por artefato).

## Princípios do Push-back

1. **Perguntar antes de afirmar** — "qual é o número?" vale mais que "isso está vago"
2. **Citar a fonte** quando ajuda (PMBOK, Doerr, etc.) — dá autoridade sem ser chato
3. **Oferecer saída** — se usuário insiste, aceitar com `OVERRIDE` + justificativa
4. **Nunca moralizar** — "você está errado" ≠ "esse critério está falhando, como resolver?"
5. **Proporcional** — 1 critério falho = push-back leve; 3+ falhos = recomendar voltar a coletar

## Índice

- [01 · Contexto & Escopo](#01--contexto--escopo)
- [02 · OKRs](#02--okrs)
- [03 · WBS/EAP](#03--wbseap)
- [04 · Cronograma](#04--cronograma)
- [05 · Roadmap & Marcos](#05--roadmap--marcos)
- [06 · Recursos & Dependências](#06--recursos--dependências)
- [07 · Plano de Comunicação](#07--plano-de-comunicação)
- [08 · Riscos](#08--riscos)
- [09 · Calendário](#09--calendário)

## 01 · Contexto & Escopo

### Estrela guia vaga

**Exemplo ruim do usuário:** "melhorar a operação"

**Push-back:**
> Essa estrela guia não é acionável hoje — e em 6 meses ninguém vai saber se "melhoramos" ou não. Três perguntas: (a) **qual número** mede essa melhoria? (b) **até quando** queremos atingir? (c) **como** vamos medir de forma confiável? Sem isso, todo o resto do plano fica sem destino.

### Ausência de "não faremos"

**Exemplo ruim:** seção "Não Faremos" vazia ou com 1 item

**Push-back:**
> Sem um "não faremos" explícito (mínimo 3 itens), stakeholders vão assumir que coisas óbvias-para-eles estão no escopo — e no meio da execução vão cobrar. Pensa em 3 coisas que alguém razoavelmente esperaria deste projeto entregar, mas que você **conscientemente** escolheu não fazer. Essas vão na lista.

### Sem conexões de portfólio

**Push-back:**
> Este projeto está solto no vácuo? Normalmente há pelo menos uma dependência com outra iniciativa — ou este projeto destrava algo adiante. Se realmente não há nenhuma conexão, registra isso explicitamente; mas vale conferir com o sponsor antes de assumir isolamento total.

### Sem critérios de aceite do projeto

**Push-back:**
> Como saberemos que o projeto terminou? "Quando os entregáveis estiverem prontos" não basta — precisa haver um teste de aceitação que o sponsor reconheça. Propõe 2-3 critérios concretos que, se cumpridos, declaram sucesso.

## 02 · OKRs

### KR é output, não outcome

**Exemplo ruim:** "KR 1.1: Entregar o playbook de gestão"

**Push-back:**
> Esse KR descreve um **output** (entregar algo), não um **outcome** (efeito no negócio). Doerr é claro: KRs medem mudanças no mundo, não tarefas. O que queremos que **aconteça** depois que o playbook for entregue? Uso adotado, ciclo de decisão reduzido, satisfação do time? Essa é a métrica.

### KR sem número

**Exemplo ruim:** "KR: melhorar engajamento do time"

**Push-back:**
> Sem número, "melhorar" pode ser qualquer coisa — incluindo nada. De onde saímos? Para onde? Se não existe instrumento de medição hoje, o primeiro KR pode ser justamente "estabelecer baseline de X até mês Y".

### Mais de 5 KRs por objetivo

**Push-back:**
> Mais de 5 KRs num objetivo é foco diluído. Se tudo importa, nada importa. Quais 3-5 capturam o essencial? O resto vira trabalho de apoio, não KR.

### Baseline ausente

**Push-back:**
> Sem baseline, não sabemos se avançamos. "Subir conversão para 20%" precisa saber: 20% a partir de quê? Se o dado não existe hoje, reconhecer isso abertamente — pode virar pré-trabalho do projeto.

## 03 · WBS/EAP

### Pacote genérico

**Exemplo ruim:** "Implementação"

**Push-back:**
> "Implementação" é fase, não pacote. Decompõe em pacotes de 8h a 80h com entregável verificável cada. Pergunta-chave: se outra pessoa assumisse esse pacote amanhã, saberia o que fazer e como declarar pronto?

### Pacote sem entregável tangível

**Push-back:**
> Qual é o **artefato** que prova que esse pacote está feito? Documento, código merged, relatório assinado, reunião realizada com ata? Sem artefato verificável, o pacote vira zona cinzenta — sempre "quase pronto".

### Dois pacotes iguais com mesmo dono

**Push-back:**
> Esses dois pacotes parecem fazer a mesma coisa e têm o mesmo responsável. É um só com dois subpontos? Ou são realmente atividades distintas com entregáveis distintos? Vale juntar ou separar claramente.

### Pacotes muito desbalanceados

**Exemplo:** um pacote de 300h, outro de 2h, no mesmo nível

**Push-back:**
> Essa diferença de escala (300h vs 2h) sugere que ou o grande está pouco decomposto, ou o pequeno deveria ser subatividade de outro. PMBOK recomenda pacotes em ordem de grandeza comparável — a regra 8/80 dá um corredor razoável.

## 04 · Cronograma

### Tudo começando na mesma data

**Push-back:**
> Todas as etapas começando no dia 1 é quase sempre irrealista. Onde há **dependências reais** (uma precisa da outra) e onde há apenas hábito de planejar em série? Dependências de tipo FS (finish-start) precisam ser explícitas; o resto pode paralelizar.

### Tudo em série

**Push-back:**
> Se nada paraleliza, ou (a) falta decompor em pacotes independentes, ou (b) todas as dependências são acidentais ("sempre fizemos assim"). Qual das duas?

### Sem buffer de incerteza

**Push-back:**
> PMBOK: 10% de buffer sobre a duração total é mínimo defensivo. Onde está a folga nesse cronograma? Se buffer zero é proposital (prazo externo apertado), registrar como risco explícito de §08.

### Estimativas redondas suspeitas

**Exemplo:** todos os pacotes com "5 dias" ou "1 semana"

**Push-back:**
> Essas durações redondas parecem chutadas, não estimadas. Qual é a base — histórico de projeto anterior, analogia, bottom-up, expert judgment? Sem racional, o cronograma vira narrativa.

### Pacote crítico em pessoa sobrecarregada

**Push-back:**
> O pacote X está no caminho crítico e atribuído à [pessoa] que também aparece em 3 outros lugares. Na prática, ela tem quantas horas semanais para este projeto? Se <50%, o caminho crítico está em risco real — ou reduz escopo, ou protege agenda, ou aceita o risco conscientemente.

## 05 · Roadmap & Marcos

### Marco vago

**Exemplo ruim:** "M2: projeto avançando"

**Push-back:**
> "Projeto avançando" não é marco — é sintoma. Marco é um ponto verificável no tempo: "Piloto rodando em 3 unidades com NPS ≥7", "Playbook aprovado pelo comitê", "Go/No-Go de expansão". Qual é o critério concreto?

### Marco sem owner

**Push-back:**
> Quem **declara** que esse marco foi atingido? Sem owner nomeado, vira zona cinzenta — passamos o marco ou não? Normalmente é sponsor (gates) ou líder (handoffs operacionais).

### Marcos só no fim

**Push-back:**
> Todos os marcos concentrados no último terço do projeto deixam muito espaço sem checkpoint. Se algo der errado nas primeiras 8 semanas, como saberemos? Marcos intermediários são para ajustar rota, não só para comemorar entrega final.

### Marco confundido com entregável

**Push-back:**
> "Playbook entregue" é **entregável** (artefato); o marco correspondente seria "Playbook validado pelo comitê em [data]" — a validação é que fecha o marco, não a entrega em si.

## 06 · Recursos & Dependências

### Dedicação 100% improvável

**Push-back:**
> [Pessoa] aparece com 100% de dedicação — ela realmente largou tudo para este projeto? Ou é aspiracional? Normalmente vale validar diretamente com ela e com o gestor dela antes de assumir no plano. Se for 100% real, ótimo — registra a decisão de relocação.

### Dependência sem data de handoff

**Push-back:**
> Dependência externa sem data vira bomba-relógio. Quando [time externo] precisa te entregar [X] para não travar? Pergunta pra eles — se não souberem, já é um sinal de risco a registrar em §08.

### Dependência sem plano B

**Push-back:**
> Se [dependência] atrasar 2 semanas, qual é o plano? "Torcer" não conta. Pode ser: (a) escopo reduzido, (b) atividade alternativa em paralelo, (c) aceitar atraso e comunicar, (d) escalar. Escolhe uma — ou explicitamente declara que não há plano B e isso vira um risco Alto.

### Líder em múltiplos projetos simultâneos

**Push-back:**
> [Líder] também está liderando [outros projetos]. Na prática, quantas horas semanais sobram para este? Se <30%, risco de split de foco é real — vale conversar com sponsor sobre prioridade relativa.

## 07 · Plano de Comunicação

### Stakeholder sem engagement level

**Push-back:**
> Esse stakeholder está a favor do projeto, contra, ou no meio? Como sabemos? O PMI Stakeholder Cube (unaware/resistant/neutral/supportive/leading) força a escolha — e a estratégia muda muito conforme a categoria. Não dá pra deixar "TBD".

### RACI com dois A

**Push-back:**
> Dois "A" (Accountable) na mesma linha significa que ninguém é realmente accountable — quando falha, ambos apontam o outro. RACI é rígido nisso: Accountable é **único**. Precisa escolher.

### Ritual sem output

**Push-back:**
> Qual é o **produto** dessa reunião? Decisão tomada? Blocker resolvido? Status consolidado? Um ritual sem output declarado vira reunião-hábito que ninguém quer cancelar mas ninguém quer estar.

### Só rituais operacionais

**Push-back:**
> Todos os rituais aqui são do time core. E o sponsor? Sem cadência executiva, ele fica no escuro e vai aparecer no pior momento pedindo update ad-hoc. Um status report mensal (mesmo que curto) previne isso.

## 08 · Riscos

### Risco é consequência, não risco

**Exemplo ruim:** "Risco: projeto atrasar"

**Push-back:**
> "Projeto atrasar" é o **resultado** de um risco se materializar, não o risco em si. Qual é a **causa**? Acesso ao dataset X atrasar? Pessoa-chave sair? Ferramenta não comprar? O risco precisa ser a causa nomeada — aí dá pra bolar contramedida específica.

### Risco sem trigger

**Push-back:**
> Como saberemos que esse risco está **se materializando**? Precisa haver um sinal observável — ex.: "atraso de ≥5 dias no handoff esperado" ou "pessoa-chave cancela 3 reuniões seguidas". Sem trigger, o risco vira surpresa quando estourar.

### Sem contramedida

**Push-back:**
> Se esse risco virar realidade amanhã, qual é a primeira ação? "Ver depois" não é plano. Mesmo contramedida simples ("escalar para sponsor em 24h") já vale — o importante é decidir antes, não durante a crise.

### Só riscos negativos

**Push-back:**
> Riscos positivos (oportunidades) também contam: e se a adoção for 2x maior que o esperado? E se o patrocinador quiser escalar antes do planejado? Vale mapear pelo menos 1-2 — estratégias diferentes (exploit/share/enhance/accept), mas a disciplina é a mesma.

### "Alto" sem dimensão

**Exemplo ruim:** "Risco alto: falta de buy-in"

**Push-back:**
> "Alto" como atributo genérico não ajuda a priorizar. Precisa separar: qual a **probabilidade** (Alta/Média/Baixa) de ocorrer, e qual o **impacto** (Alto/Médio/Baixo) se ocorrer? Um Alta×Alto merece ação imediata; Média×Baixo pode ser monitorado.

### Menos de 5 riscos

**Push-back:**
> Projetos reais raramente têm só 2-3 riscos — mais provável que alguns estão invisíveis por ainda não terem sido puxados. Pensa em: dependências externas, pessoas críticas, premissas de estimativa, integrações técnicas, buy-in de stakeholders. Geralmente 5+ emergem.

## 09 · Calendário

### Muitos rituais semanais

**Push-back:**
> Contando, são [N] rituais semanais só para este projeto — e o time já tem rituais de linha. Na prática, todos vão acontecer de verdade? Ou alguns vão ser "canceled, reschedule" virando entropia? Vale consolidar ou alternar quinzenalmente.

### Falta ritual de aceite entre fases

**Push-back:**
> Você planeja transição Planejamento → Execução em [data], mas não vejo um ritual específico de "fechamento de fase com sponsor". Sem esse checkpoint, entramos na próxima fase sem validação explícita — e depois descobrimos que o sponsor não estava a bordo.

### Overbooking do PM

**Push-back:**
> Pelo calendário, o PM (você?) tem [N] reuniões recorrentes do projeto + [M] de linha. Se média passa de 4h/dia em reuniões, sobra pouco para coordenar e pensar. Vale rever cadência ou delegar alguns rituais.

### Sem revisões trimestrais (projeto >6m)

**Push-back:**
> Projeto de [duração] sem revisão trimestral macro deixa sponsor longe demais da realidade. Não precisa ser pesado — 45min a cada 3 meses com sponsor + líder para recalibrar prioridades e confirmar rumo. Sem isso, só descobrimos divergência no final.

## Regra de sobrescrita

Quando usuário insiste que push-back não se aplica ao caso dele, a skill:

1. Pede **uma frase** de justificativa (não precisa ser longa)
2. Registra no MD como `<!-- OVERRIDE: <justificativa> -->` logo após o marker de status
3. Aceita o incremento

Isso preserva autonomia do usuário E cria registro para revisão posterior (ex.: na Fase 3 ou em retrospectivas pós-projeto).
