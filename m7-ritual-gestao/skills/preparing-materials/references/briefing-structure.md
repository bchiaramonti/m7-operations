# Estrutura do Briefing — Guia de Preparacao para o Ritual

Referencia para o material-generator sobre como gerar o briefing pre-ritual. O briefing NAO e um resumo do WBR. E um guia estrategico para quem conduz o ritual.

---

## Sumario

- [Principio fundamental](#principio-fundamental)
- [Secoes obrigatorias](#secoes-obrigatorias)
  - [1. Veredicto](#1-veredicto-3-frases-max)
  - [2. O Que Provocar](#2-o-que-provocar-perguntas-por-interlocutor)
  - [3. Armadilhas da Reuniao](#3-armadilhas-da-reuniao)
  - [4. Decisoes Que Precisam Sair](#4-decisoes-que-precisam-sair)
  - [5. Roteiro](#5-roteiro-pauta-com-intencao)
- [Regras de escrita](#regras-de-escrita)
- [Checklist de validacao](#checklist-de-validacao)

---

## Principio fundamental

> **O gestor ja leu o WBR. Ele sabe os numeros. O briefing existe para prepara-lo para AGIR sobre esses numeros.**

O briefing e como um consultor preparando um diretor para uma reuniao de acompanhamento de resultados. Nao repete dados — traduz dados em perguntas, armadilhas e decisoes.

| WBR | Briefing |
|-----|----------|
| O que aconteceu | O que fazer com isso |
| Dados + diagnostico | Perguntas + decisoes |
| Analise tecnica | Inteligencia de reuniao |
| Para quem acompanha | Para quem conduz |

**Regra de ouro**: Se uma frase do briefing poderia estar no WBR sem parecer fora de lugar, ela esta errada. Reescreva com tom de preparacao, nao de relato.

---

## Secoes obrigatorias

### 1. Veredicto (3 frases max)

Nao e resumo executivo. E a conclusao que o gestor precisa ter na cabeca antes de entrar na sala.

**Estrutura fixa**:
- Frase 1: Situacao geral em 1 linha (sem tabelas, sem listas de KPIs)
- Frase 2: O risco real que o semaforo NAO mostra (sempre existe — se o semaforo fosse suficiente, nao precisaria de ritual)
- Frase 3: A decisao que precisa sair DESTA reuniao (especifica, nao generica)

**Regras**:
- NUNCA liste numeros de KPIs aqui — o gestor ja sabe
- NUNCA use "semana mista" ou "performance saudavel" — seja direto sobre o que importa
- SEMPRE termine com a decisao-alvo do ritual
- Se todos os indicadores estao em verde: o risco e complacencia, concentracao, ou sustentabilidade. Diga isso.

**Exemplo**:
> Consorcios fecha marco em verde consolidado, mas 100% do volume vem de um unico especialista. Tereza Bernardo e seus 10 assessores zeraram vendas no mes inteiro. Voce precisa sair deste ritual com uma decisao sobre realocacao de recursos para Tereza.

### 2. O Que Provocar (perguntas por interlocutor)

Para cada pessoa relevante no ritual, listar perguntas especificas que o gestor deve fazer. Organizadas por **interlocutor** (nao por KPI). Cada pergunta tem:
- A pergunta direta (entre aspas, pronta para usar)
- **Por que perguntar**: contexto do WBR/Card que motiva a pergunta (1 frase)
- **Nao aceite**: resposta evasiva tipica que o gestor deve rejeitar (1 frase)

**Formato**:
```markdown
**[Nome] — [Papel/Cargo]**

1. "[Pergunta direta, fechada e provocativa]"
   - Por que perguntar: [dado do WBR que gera a pergunta]
   - Nao aceite: "[resposta evasiva tipica]" — redirecione para [o que pedir]

2. "[Segunda pergunta]"
   - Por que perguntar: [contexto]
   - Nao aceite: "[evasiva]" — redirecione para [acao]
```

**Como gerar perguntas**:
1. Para cada **desvio critico no WBR** (Vermelho/Amarelo), identificar QUEM e responsavel (usar Card de Performance para mapear especialista → assessores)
2. Para cada **acao pendente/atrasada**, gerar pergunta sobre progresso concreto (nao "como esta indo?", mas "qual o proximo passo e para quando?")
3. Para cada **risco mascarado** (verde consolidado com N2 critico), gerar pergunta que force o desdobramento
4. Incluir perguntas de auto-reflexao para o proprio gestor quando relevante ("O que voce ja tentou?", "Qual recurso esta faltando?")

**Regras**:
- Maximo 3-4 perguntas por interlocutor (ritual nao e inquerito)
- Perguntas devem ser FECHADAS (exigem resposta concreta, nao discurso)
- A secao "Nao aceite" e critica — impede que a reuniao vire conversa vazia
- Se o Card lista especialistas/assessores, use nomes reais
- NUNCA gere perguntas genericas tipo "como podemos melhorar?" — sempre ancore em dados

### 3. Armadilhas da Reuniao

Padroes previsíveis que podem desviar o ritual de decisoes uteis. Extraidos do cruzamento WBR + Card + historico de acoes.

**Formato**:
```markdown
- **[Nome da armadilha]**: [descricao em 1 frase]. **Redirecione**: [o que fazer quando perceber].
```

**Armadilhas tipicas a detectar** (gerar apenas as relevantes ao ciclo):

| Padrao no WBR | Armadilha | Redirecionamento |
|---------------|-----------|------------------|
| Todos os KPIs em verde | "Verde geral = tudo bem" | Desdobrar N2: quem esta carregando? |
| KPI em lag (receita atrasada) | "E lag, vai chegar" | Pedir evidencia: "mostre o pipeline que vira receita" |
| Muitas acoes abertas, poucas concluidas | "Estamos trabalhando em tudo" | Forcar priorizacao: "escolha 2 para terminar esta semana" |
| Acao vencida sem registro de progresso | "Esqueci de atualizar o status" | Tratar como acao parada, nao atrasada |
| Projecao otimista sem acao de suporte | "Vai melhorar naturalmente" | Exigir contramedida concreta: "o que muda se nao fizermos nada?" |
| Concentracao em poucos assessores | "Sao os melhores, e natural" | Provocar: "e se [assessor top] sair? Qual e o plano B?" |

**Regras**:
- Maximo 3-4 armadilhas por briefing (selecionar as mais provaveis)
- Cada armadilha deve ter redirecionamento acionavel
- NUNCA liste armadilhas genericas — sempre baseadas nos dados do ciclo

### 4. Decisoes Que Precisam Sair

Lista de decisoes concretas que o ritual DEVE produzir. Cada uma em formato binario (sim/nao ou opcao A vs B).

**Formato**:
```markdown
| # | Decisao | Quem decide | Ate quando | Se nao decidir |
|---|---------|-------------|------------|----------------|
| 1 | [Pergunta binaria: "Fazemos X ou Y?"] | [Nome] | [Data] | [Consequencia] |
```

**Como gerar decisoes**:
1. Ler secao "Recomendacoes" e "Escalonamentos" do WBR
2. Cada recomendacao com owner e prazo vira uma decisao
3. Cada escalonamento para N1 vira uma decisao obrigatoria
4. Acoes criticas pendentes ha >14 dias viram decisao: "Mantemos ou cancelamos?"

**Regras**:
- Maximo 3-4 decisoes (ritual nao e comite)
- A coluna "Se nao decidir" e obrigatoria — torna urgencia tangivel
- Decisoes devem ser especificas o bastante para serem respondidas com sim/nao
- NUNCA use "avaliar", "estudar", "considerar" — use "aprovar", "alocar", "cancelar"

### 5. Roteiro (pauta com intencao)

Similar a pauta, mas cada bloco tem **intencao** — o resultado esperado daquele momento, nao apenas o tema.

**Formato**:
```markdown
| # | Bloco | Duracao | Intencao (resultado esperado) |
|---|-------|---------|-------------------------------|
| 1 | Abertura | 5 min | [o que extrair] |
```

**Regras de tempo**:
- Base = 5 min (abertura) + 10 min (contramedidas) + 5 min (encaminhamentos)
- + 8 min por KPI Vermelho
- + 4 min por KPI Amarelo
- Se total > 90 min: comprimir Amarelos para 2 min
- Limite: 50-90 minutos

**Regras de intencao**:
- Cada bloco deve ter resultado mensuravel: "sair com compromisso de data", "confirmar ou descartar hipotese X", "obter aprovacao para Y"
- NUNCA use "discutir X" como intencao — discutir nao e resultado
- O bloco final deve consolidar todas as decisoes em owners + prazos

---

## Regras de escrita

| Regra | Detalhe |
|-------|---------|
| Tom | Direto, provocativo, orientado a decisao. Como um consultor falando com o cliente |
| Extensao total | 300-500 palavras (~1 pagina) |
| Numeros | Usar APENAS quando indispensaveis para a pergunta/decisao. Nao repetir dados do WBR |
| Moedas | Formato brasileiro: R$ X,XX (milhares: R$ X,XMM) |
| Datas | Formato DD/MM/YYYY |
| Verbos | Imperativo na secao de armadilhas ("Redirecione", "Exija", "Nao aceite") |
| Perguntas | Entre aspas, prontas para usar literalmente na reuniao |
| Repetir WBR | **NUNCA**. Se o gestor precisa do numero, ele consulta o WBR. O briefing prepara, nao informa |

---

## Checklist de validacao

Antes de salvar o briefing, verifique:

- [ ] Veredicto tem exatamente 3 frases (situacao, risco oculto, decisao-alvo)
- [ ] "O Que Provocar" usa nomes reais de pessoas (do WBR + Card)
- [ ] Cada pergunta tem "Nao aceite" com redirecionamento
- [ ] Armadilhas sao especificas ao ciclo (nao genericas)
- [ ] Decisoes sao binarias (sim/nao, A/B) com consequencia de nao-decisao
- [ ] Roteiro tem intencao (resultado esperado) em cada bloco, nao apenas tema
- [ ] Nenhuma secao repete dados do WBR (semaforo, tabelas de KPI, percentuais detalhados)
- [ ] Total de palavras entre 300-500
- [ ] Duracao do roteiro entre 50-90 minutos
