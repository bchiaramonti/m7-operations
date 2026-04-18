# Critérios de Aceite por Artefato

Checklist operacional para skill decidir se um incremento está pronto para `ACCEPTED`. Cada critério é **verificável** — skill deve conseguir marcar ✅/❌ lendo o conteúdo que o usuário produziu. Se pelo menos um critério falhar, skill aplica push-back (ver [pushback-playbook.md](pushback-playbook.md)).

**Meta por artefato: ≥3 critérios de aceite** (spec 06). Este arquivo totaliza ≥30 critérios (média de 4+ por artefato).

**Regra geral:** skill sugere, push-backa, mas **nunca aceita sem ok explícito**. Sobrescrita requer `<!-- OVERRIDE: justificativa -->` no MD.

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

- [ ] **Estrela guia tem métrica quantitativa E timeframe** — "aumentar conversão em 15% até Set/26" ✅; "melhorar conversão" ❌
- [ ] **Business case articulado** — texto responde "por que este projeto?" e "por que agora?"
- [ ] **"Não faremos" explícito** com mínimo **3 itens** (escopo negativo evita assunções silenciosas)
- [ ] **Critérios de aceite do projeto** presentes — como saberemos que terminou?
- [ ] **Decisões de escopo registradas** com justificativa (ex.: "limitar piloto a 3 unidades porque...")
- [ ] **Conexões com portfólio** mencionadas (dependências up/down) OU explícito "nenhuma conexão"

## 02 · OKRs

- [ ] **2-3 Objetivos** (não 1, não 5+) — foco concentrado
- [ ] **3-5 KRs por Objetivo** (>5 = foco diluído; <3 = talvez objetivo trivial)
- [ ] **Cada KR tem baseline** — valor atual mensurável, não presumido
- [ ] **Cada KR tem target** — número concreto, não "melhorar"
- [ ] **Cada KR tem fonte de medição** — onde/como será medido (tabela, dashboard, pesquisa)
- [ ] **KRs são outcomes, não outputs** — efeito no mundo, não entregáveis ("NPS sobe 10pts" ✅; "playbook entregue" ❌)
- [ ] **Cadência de review definida** — quinzenal, mensal, etc.

## 03 · WBS/EAP

- [ ] **Regra dos 100%** — WBS cobre todo o escopo E apenas o escopo (nada fora do "Faremos")
- [ ] **Regra 8/80** — cada pacote entre ~8h e ~80h de esforço (granular sem virar tarefa; agregado sem virar fase)
- [ ] **MECE** — mutually exclusive, collectively exhaustive (sem overlap, sem buraco)
- [ ] **Um único responsável por pacote** — se tem 2, é dois pacotes ou renegociar
- [ ] **Entregável verificável por pacote** — artefato tangível que prova conclusão
- [ ] **Codificação hierárquica consistente** — `1`, `1.1`, `1.1.1` (sem `1.1a`, sem saltos)
- [ ] **Balanceamento razoável** — sem pacote de 300h convivendo com outro de 2h

## 04 · Cronograma

- [ ] **Dependências identificadas entre pacotes** — FS (finish-start) mínimo; FF/SS/SF quando relevante
- [ ] **Duração estimada com racional** — quem estimou, com base em quê (histórico, analogia, expert judgment)
- [ ] **Paralelismo explorado** — nem tudo em série; pacotes independentes rodam em paralelo
- [ ] **Buffer de incerteza ≥10%** da duração total OU justificativa explícita
- [ ] **Caminho crítico identificado** — quais pacotes, se atrasarem, atrasam o projeto
- [ ] **Marcos-chave alinhados com OKRs** — datas que disparam medição de KRs estão no cronograma
- [ ] **Responsáveis atribuídos** — cada linha tem pessoa (não time genérico)

## 05 · Roadmap & Marcos

- [ ] **Cada marco tem critério de aceite (DoD)** — "como saberemos que foi atingido?"
- [ ] **Cada marco tem owner** — quem declara que foi atingido
- [ ] **Cada marco tem data** (dia, semana, ou mês, consoante maturidade)
- [ ] **Frequência compatível com duração** — 3m projeto → ≥1 marco/mês; 6m → ≥1 marco/~6sem
- [ ] **Marcos ligados a decisões/gates** — go/no-go, handoffs, validações externas, não só "meio do projeto"
- [ ] **Marco ≠ entregável** — marco é validação do entregável, não o artefato em si

## 06 · Recursos & Dependências

- [ ] **Cada pessoa tem % de dedicação explícito** — "Bruno 40%" vs "Bruno envolvido"
- [ ] **Cada pessoa tem período de alocação** — datas de início/fim de engajamento
- [ ] **Pessoas críticas com <50% têm plano de proteção de agenda** — como garantir o tempo?
- [ ] **Dependências externas com data de handoff** — quando precisam entregar?
- [ ] **Dependências externas com impacto se falharem** — o que trava se atrasar?
- [ ] **Plano B para recurso crítico indisponível** — contingência real, não "torcer"
- [ ] **Investimentos identificados** (financeiros, ferramentas, licenças) OU declarado "não há"

## 07 · Plano de Comunicação

- [ ] **Stakeholders categorizados por engagement level** — unaware/resistant/neutral/supportive/leading (PMI Stakeholder Cube)
- [ ] **Fonte de leitura do engagement** — como sabemos que stakeholder X está "resistant"?
- [ ] **RACI completo por entregável/atividade** — R, A, C, I preenchidos
- [ ] **Accountable singular** — cada linha RACI tem exatamente **um** A (não 2, não zero)
- [ ] **Rituais com 4 campos** — frequência, formato, audiência, output (o que se decide/produz)
- [ ] **Canal default definido** — Teams, email, Slack — qual é o primário
- [ ] **Status report com cadência fixa** — periodicidade + destinatários
- [ ] **Pelo menos um ritual executivo** — sponsor precisa de canal recorrente, não só operacional

## 08 · Riscos

- [ ] **Cada risco é específico** — "atraso do dataset X" ✅; "projeto atrasar" ❌ (isso é consequência)
- [ ] **Cada risco tem probabilidade** — Alta/Média/Baixa (qualitativo ok, quantitativo melhor)
- [ ] **Cada risco tem impacto** — Alto/Médio/Baixo
- [ ] **Cada risco tem trigger observável** — sinal concreto de materialização
- [ ] **Cada risco tem estratégia de resposta** — avoid/transfer/mitigate/accept (negativos); exploit/share/enhance/accept (positivos)
- [ ] **Cada risco tem contramedida** — ação planejada, não "ver depois"
- [ ] **Cada risco tem owner** — pessoa, não time
- [ ] **Separação risco vs problema** — risco é futuro/incerto; problema é presente/certo (problemas vão para outra lista)
- [ ] **Inclui riscos positivos (oportunidades)** — não só ameaças
- [ ] **Mínimo 5 riscos mapeados** — projetos raramente têm só 2-3 riscos reais

## 09 · Calendário

- [ ] **Rituais com cadência clara** — semanal/quinzenal/mensal, dia e hora fixos
- [ ] **Marcos de §05 plotados nos meses corretos** — consistência temporal
- [ ] **Sem overbooking do PM ou donos-chave** — conflitos sinalizados
- [ ] **Revisões de transição de fase presentes** — fechamento de fase + abertura da próxima com sponsor
- [ ] **Feriados/férias conhecidos considerados** — bloqueios identificados OU assumido "sem impacto"
- [ ] **Para projetos >6m: revisões trimestrais** — checkpoint macro com sponsor

## Como interpretar falhas

- **1-2 critérios faltando:** push-back direto, perguntar se ajusta
- **3+ critérios faltando:** sugerir que incremento está "imaturo" — voltar para coleta antes de decidir status
- **Critério sem possibilidade de preenchimento** (ex.: "não há fonte de medição possível para KR X"): usuário pode `OVERRIDE` com justificativa — mas skill deve alertar que isso vai prejudicar o acompanhamento futuro
