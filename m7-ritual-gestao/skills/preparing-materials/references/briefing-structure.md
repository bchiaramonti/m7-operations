# Briefing do Ritual — Estrutura v2.0 (aberta)

Referencia para o agente `material-generator` gerar o briefing do condutor (G2.3-E2). Funciona para qualquer nivel (N1, N2, N3) e qualquer vertical (INV, CRE, UNI, SEG, CON).

> **Sobre o briefing:** o gestor ja leu o WBR. Ele sabe os numeros. O briefing existe para PREPARA-LO PARA AGIR sobre esses numeros — nao para informar. Tom direto, provocativo, orientado a decisao.

## Sumário

1. [Papel do briefing no fluxo G2.3](#1-papel-do-briefing-no-fluxo-g23)
2. [Fontes de dados](#2-fontes-de-dados)
3. [Filosofia da estrutura aberta v2.0](#3-filosofia-da-estrutura-aberta-v20)
4. [Estrutura do briefing — 5 secoes obrigatorias](#4-estrutura-do-briefing--5-secoes-obrigatorias)
5. [Mapeamento Card YAML → secoes do briefing](#5-mapeamento-card-yaml--secoes-do-briefing)
6. [Sistema de placeholders (Briefing-Template.md / .html)](#6-sistema-de-placeholders-briefing-templatemd--html)
7. [Variantes do briefing — MD e HTML A4](#7-variantes-do-briefing--md-e-html-a4)
8. [Casos extremos e fallbacks](#8-casos-extremos-e-fallbacks)
9. [Aprendizados do gold standard CON S18 (2026-04-27)](#9-aprendizados-do-gold-standard-con-s18-2026-04-27)
10. [Checklist de auditoria (14 itens)](#10-checklist-de-auditoria-14-itens)
11. [Referencias cruzadas](#11-referencias-cruzadas)

---

## 1. Papel do briefing no fluxo G2.3

Cadeia de artefatos do ritual:

```
G2.2 (Controle)              G2.3 (Ritual)
  ┌──────────────┐
  │  Dados       │
  │  consolidados│ E2
  └─────┬────────┘
        ↓
  ┌──────────────┐
  │  WBR         │ E6  (informa: o que aconteceu, por que, projecao)
  └─────┬────────┘
        │
        │ ───── Card de Performance YAML (briefing_customization v2.0)
        │       fornece eixos / familias / categorias para pensar o ritual
        │
        ↓
  ┌──────────────────────────┐  ┌────────────────────────┐
  │  Briefing do condutor    │  │  Apresentacao do ritual│  G2.3-E2
  │  (.md + .html A4)        │  │  (deck HTML 16:9)      │
  │  prepara para AGIR       │  │  visualiza para todos  │
  └──────────────────────────┘  └────────────────────────┘
                ↓
        Ritual acontece (G2.3-E3)
                ↓
  ┌──────────────┐
  │  Ata do      │ E5  (registra decisoes tomadas)
  │  ritual      │
  └──────────────┘
```

| Documento | Audiencia | Proposito | Tom |
|-----------|-----------|-----------|-----|
| WBR | Gestor (leitura previa) | Informar — o que aconteceu, causa-raiz, projecao | Analitico, completo |
| Briefing | Condutor (preparacao) | Provocar — perguntas, armadilhas, decisoes-alvo | Direto, provocativo |
| Apresentacao | Time + condutor (durante ritual) | Visualizar — semaforo, dashboards, funil | Visual, sintetico |

---

## 2. Fontes de dados

| Fonte | Caminho relativo ao cycle folder | O que extrair |
|-------|----------------------------------|---------------|
| WBR estruturado | `wbr/wbr-{vertical}-{data}.md` | Painel de Indicadores (1.5), Desvios (2), Acoes (3), Projecoes (4), Recomendacoes (5) |
| Card de Performance | `{CARDS_DIR}/{Vertical}/card_*.yaml` | Secao `briefing_customization` v2.0 + `apresentacao.responsaveis` |
| ClickUp (Plano de Acao) | API ClickUp, lista `pa-resultado` ID 901326795742 | Status binario, aging, owner, prazo |
| Bitrix24 (deals) | Dados ja consolidados pelo G2.2-E2 | Pipeline, deals estagnados, valores criticos |

**Regra single source of truth:** numeros vem do WBR. Se o briefing menciona um valor que nao esta no WBR, esta errado.

**Filtros ClickUp para Slide 5 e Secao 2/4 do briefing (canonicos — ver `slide-structure.md` §Slide 5):**

(a) filtrar tasks por custom field `Vertical` igual a vertical do ritual (id
`a7c7bc7c-2526-4083-9753-aa2103a08f53`; opcoes 0=Investimentos, 1=Credito,
2=Universo, 3=Seguros, 4=Consorcio, 5=Wealth, 6=IB) — **nao pelo nome ou pela
pasta**;

(b) usar custom field `Responsavel Externo` (id `e44c8cff-7d0b-4074-84ae-c10c67b0a26d`)
em vez de `assignees[]` — Responsavel Externo e o stakeholder da decisao;
`assignees[]` e o executor operacional;

(c) excluir subtasks (filtrar `parent == null`) — subtasks pendentes viram
nota descritiva dentro da parent, nao linhas independentes do Slide 5.

A coerencia Slide 5 ↔ briefing exige que ambos usem exatamente os mesmos 3 filtros.

---

## 3. Filosofia da estrutura aberta v2.0

A versao 2.0 dos Cards (vigente em SEG, CON, INV desde 2026-04-27) substituiu uma v1.0 prescritiva. A v1.0 listava instancias passadas (acoes especificas, nomes proprios, percentuais especificos) e foi descartada porque enviesava o ritual a re-discutir assuntos ja resolvidos.

A v2.0 lista **eixos / familias / categorias estaveis** que o agente seleciona apenas quando o WBR do ciclo sustenta. Texto canonico de `uso_pretendido` em todos os Cards:

> Estrutura aberta. Selecionar dos eixos abaixo APENAS os que o WBR do ciclo corrente sustenta. Nada aqui deve ser forcado quando os dados nao apontarem na direcao. Quando o ciclo trouxer um assunto NAO previsto aqui, esse assunto entra livremente no briefing — estes eixos sao adicionais, nao restritivos.

**Implicacoes praticas para o agente:**

- NAO copia armadilhas/decisoes do Card cegamente. Filtra por `sinal_generico_no_wbr` (familias_de_armadilhas) e `contexto_tipico` (familias_de_decisoes) — so inclui o que o WBR atual sustenta.
- PODE incluir armadilha/decisao que nao esta no Card, se o WBR daquele ciclo trouxer assunto novo.
- Numero de armadilhas no briefing varia (3 a 4 tipico) conforme o ciclo. Nao ha quantidade fixa.

---

## 4. Estrutura do briefing — 5 secoes obrigatorias

Toda instancia de briefing (qualquer vertical, qualquer nivel) tem exatamente estas 5 secoes, nesta ordem. Espelham os 5 blocos do `briefing_customization` no Card.

### Secao 1 — Veredicto

Paragrafo unico de **3 frases**:

| Frase | Conteudo | Origem |
|-------|----------|--------|
| 1 | Situacao geral do ciclo em uma linha | WBR Resumo Executivo (1) |
| 2 | Risco real que o semaforo NAO mostra | `eixos_de_risco_a_considerar[].racional` filtrado pelos sinais do WBR |
| 3 | Decisao especifica que precisa sair desta reuniao | Aponta para uma das decisoes da Secao 4 |

Regras:
- Sem listas, sem tabelas, sem bullets.
- Usar apenas numeros indispensaveis (ate 2-3). NAO listar todos os KPIs.
- Decisao da frase 3 deve ser concreta (nome do deal, escopo da intervencao). NAO generica ("vamos discutir resultado", "focar em melhoria").

### Secao 2 — O Que Provocar

Lista de perguntas POR INTERLOCUTOR (cada nome em `apresentacao.responsaveis` ou equivalente do Card).

Para cada interlocutor:
- 2 a 4 perguntas (3 e o tipico para ritual de 50-90 min)
- Cada pergunta tem 3 elementos:
  - **Pergunta direta** entre aspas — fechada (exige resposta concreta, nao discurso)
  - **Nao aceite** — a resposta evasiva tipica que o interlocutor dara
  - **Redirecionamento** — dado especifico do ciclo que sustenta a pergunta e refuta a evasiva

Origem: `eixos_de_provocacao_a_considerar` do Card aplicados a interlocutores reais com numeros do WBR.

Regras:
- Citar nome do interlocutor (Douglas, Tereza). Nunca pergunta sem dono.
- Citar deals/clientes/assessores nominalmente quando relevante (Icoforte, Rebeca Canafistula).
- "Nao aceite" precisa ser plausivel — a evasiva real, nao caricatura.

### Secao 3 — Armadilhas da Reuniao

Padroes ESTRUTURAIS de discurso que tendem a desviar o ritual. **3 a 4 armadilhas** maximo.

Cada armadilha tem:
- **Frase tipica** entre aspas — como a armadilha aparece (uma fala plausivel)
- **Sinal observado** — evidencia concreta do periodo (numero, percentual, indicador). *No template/output renderiza como "Sinal observado:" — jargao "WBR" nao vaza para o condutor.*
- **Redirecionamento** — texto de `redirecionamento_geral` da familia, adaptado

Origem: `familias_de_armadilhas` do Card filtradas por `sinal_generico_no_wbr` presente no WBR atual (campo interno do Card; o label renderizado e "Sinal observado").

Criterio de selecao: **se nao ha sinal observado no periodo, NAO incluir a armadilha**. Selecionar as 3-4 mais provaveis no ciclo.

### Secao 4 — Decisoes Que Precisam Sair

1 a 4 decisoes obrigatorias em formato BINARIO. Tres elementos por decisao:
- **Formato** binario (X ou Y)
- **Owner** com nome real (e quando aplicavel, decide+executa como dois nomes)
- **Prazo** em data absoluta (YYYY-MM-DD)
- **Consequencia de nao-decidir** — impacto concreto no proximo ciclo

Origem: `familias_de_decisoes[].forma_binaria` aplicado ao contexto + Recomendacoes/Escalonamentos do WBR.

Coerencia critica: as decisoes desta secao devem ser **identicas** as do slide Encerramento (último, posição `7 + 3*N`) da apresentacao. Mesmo numero D, mesmos titulos.

### Secao 5 — Roteiro

Pauta com tempos e intencao por bloco. Default v3.0: `T = T_VISAO (8) + T_OPERACAO (10) + 15*N + T_SINTESE (4) + T_FECHAMENTO (3) = 25 + 15*N` minutos. Faixa permitida 40-100 min.

Estrutura padrao (3 blocos do `estrutura_de_roteiro` do Card):
- **Visao Geral** (default 10 min, faixa 2-5 a 10) — posicionar leitura compartilhada, sinalizar decisoes do dia
- **Bloco por especialista** (default 25 min, faixa 12-25) — 1 bloco para cada nome em `apresentacao.responsaveis`
- **Decisoes e Encerramento** (default 5 min, faixa 5-13) — registrar decisoes em ata, NAO abrir novos assuntos

Cada bloco de especialista deve incluir:
- 2-3 itens de pauta com referencia ao slide (Dashboard, Analise, Funil)
- **Saida obrigatoria** — artefato concreto que precisa sair do bloco

Coerencia critica: total final do roteiro precisa bater com agenda do slide 2 da apresentacao.

---

## 5. Mapeamento Card YAML → secoes do briefing

| Campo do Card | Secao do briefing | Como usar |
|---------------|-------------------|-----------|
| `metadata.vertical_crm` | Cabecalho | `{{VERTICAL}}` |
| `apresentacao.responsaveis[]` | Secoes 2 e 5 | 1 sub-bloco em "O Que Provocar" + 1 bloco em "Roteiro" por nome |
| `briefing_customization.uso_pretendido` | Filosofia (nao escreve no briefing) | Diretiva — "selecionar APENAS o que o WBR sustenta" |
| `caracteristicas_estruturais.organizacao[]` | Veredicto (frase 1, contexto) | Pano de fundo para leitura do semaforo |
| `caracteristicas_estruturais.operacao[]` | Veredicto (frase 2) e Armadilhas | Justifica lag, ciclo, peculiaridade da vertical |
| `caracteristicas_estruturais.pontos_de_atencao_de_dados[]` | Decisoes (auditoria/atribuicao) | Sinaliza quando bridge falhando precisa virar decisao |
| `eixos_de_risco_a_considerar[].racional` | Veredicto (frase 2) | Linguagem narrativa do risco oculto |
| `eixos_de_risco_a_considerar[].dimensoes_possiveis` | Selecao de armadilhas | Quais dimensoes especificas estao ativas |
| `eixos_de_provocacao_a_considerar[]` | O Que Provocar | Tema da pergunta (instanciado com dado do WBR) |
| `familias_de_armadilhas[].familia` | Armadilhas (rotulo) | Nome estrutural |
| `familias_de_armadilhas[].sinal_generico_no_wbr` | **Filtro de selecao** | So inclui se sinal presente no WBR |
| `familias_de_armadilhas[].redirecionamento_geral` | Armadilhas (texto Redirecione) | Adaptar com numeros reais |
| `familias_de_decisoes[].forma_binaria` | Decisoes (formato) | Template da decisao |
| `familias_de_decisoes[].contexto_tipico` | **Filtro de selecao** | So inclui se contexto presente no ciclo |
| `estrutura_de_roteiro[].bloco` | Roteiro (titulo do bloco) | Nome do bloco |
| `estrutura_de_roteiro[].duracao_min` | Roteiro (coluna Duracao) | Tempo dentro da faixa, ajustar conforme N especialistas |
| `estrutura_de_roteiro[].intencao_padrao` | Roteiro (linha Intencao) | Resultado esperado do bloco |
| `estrutura_de_roteiro[].slides_referenciados` | Roteiro (itens do bloco) | Lista de slides da apresentacao a percorrer |

---

## 6. Sistema de placeholders (Briefing-Template.md / .html)

Convencao `{{X}}`, find-and-replace simples (regex `\{\{([A-Z_0-9.+]+)\}\}`). Sem Mustache nem Jinja.

### Globais (cabecalho)

| Placeholder | Descricao | Exemplo |
|-------------|-----------|---------|
| `{{VERTICAL}}` | Nome da vertical | Consorcios |
| `{{NIVEL}}` | Nivel do ritual | N3 |
| `{{CICLO}}` | Identificador do ciclo | S18 |
| `{{DATA_RITUAL}}` | Data do ritual | 2026-04-27 |
| `{{CONDUTOR}}` | Quem conduzira | Joel Freitas |
| `{{LISTA_PARTICIPANTES}}` | Participantes nominais | Douglas Silva, Tereza Bernardo |
| `{{PERIODO_DADOS}}` | Periodo dos dados do WBR | Abril 2026 MTD |
| `{{DU_DECORRIDOS}}/{{DU_TOTAIS}}` | Dias uteis | 17/20 |
| `{{TIMESTAMP_WBR}}` | Quando o WBR foi gerado | 2026-04-27T16:05 |

### Veredicto

| Placeholder | Descricao |
|-------------|-----------|
| `{{FRASE_1_SITUACAO_GERAL}}` | Frase 1 |
| `{{FRASE_2_RISCO_OCULTO_PELO_SEMAFORO}}` | Frase 2 |
| `{{FRASE_3_DECISAO_ALVO_DA_REUNIAO}}` | Frase 3 |

### O Que Provocar (iterativo por interlocutor i = 1..M, perguntas A,B,C)

| Placeholder | Descricao |
|-------------|-----------|
| `{{NOME_INTERLOCUTOR_i}}` | Nome do interlocutor i |
| `{{PERGUNTA_DIRETA_iX}}` | Pergunta X do interlocutor i |
| `{{NAO_ACEITE_iX}}` | "Nao aceite" da pergunta iX |
| `{{REDIRECIONAMENTO_iX}}` | Redirecionamento da pergunta iX |
| `{{TITULO_PERGUNTA_iX}}` (HTML A4) | Rotulo curto da pergunta |

### Armadilhas (iterativo por armadilha j = 1..K)

| Placeholder | Descricao |
|-------------|-----------|
| `{{FRASE_TIPICA_ARMADILHA_j}}` | Como a armadilha aparece em fala |
| `{{SINAL_NO_WBR_j}}` | Evidencia concreta do ciclo |
| `{{REDIRECIONAMENTO_GERAL_j}}` | Como reconduzir |

### Decisoes (iterativo por decisao d = 1..D)

| Placeholder | Descricao |
|-------------|-----------|
| `{{TITULO_DECISAO_d}}` | Titulo curto |
| `{{FORMA_BINARIA_d}}` | Formato binario |
| `{{OWNER_d}}` | Owner(s) |
| `{{PRAZO_d}}` | Data absoluta |
| `{{CONSEQUENCIA_d}}` | Impacto de nao-decidir |

### Roteiro (iterativo por especialista e = 1..N)

| Placeholder | Descricao |
|-------------|-----------|
| `{{DUR_VISAO_GERAL}}` | Minutos do bloco Visao Geral |
| `{{INTENCAO_VISAO_GERAL}}` | Intencao do bloco |
| `{{ESPECIALISTA_e}}` | Nome do especialista e |
| `{{DUR_ESPECIALISTA_e}}` | Minutos do bloco e |
| `{{INTENCAO_ESPECIALISTA_e}}` | Intencao do bloco e |
| `{{ITEM_DASHBOARD_e}}`, `{{ITEM_ANALISE_e}}`, `{{ITEM_FUNIL_e}}` | Itens da pauta |
| `{{SAIDA_OBRIGATORIA_e}}` | Artefato concreto a sair |
| `{{INICIO_e}}/{{FIM_e}}` (HTML A4) | Intervalos cumulativos `[m-n min]` |
| `{{DUR_ENCERRAMENTO}}`, `{{INTENCAO_ENCERRAMENTO}}` | Bloco final |
| `{{DUR_TOTAL}}`, `{{COMPOSICAO_AGENDA}}` | Total e composicao formula (ex: "10 + 25 + 25 + 5") |

---

## 7. Variantes do briefing — MD e HTML A4

A skill produz duas variantes do MESMO briefing:

| Variante | Quando usar | Formato |
|----------|-------------|---------|
| MD | Consumo digital (chat, IDE, leitura no laptop) | Markdown puro |
| HTML A4 | Leitura impressa antes do ritual | HTML com `@page { size: A4; margin: 24mm 20mm; }` |

A variante HTML reproduz o conteudo do MD com classes CSS para destaque visual:

| Classe CSS | Uso |
|------------|-----|
| `.disclaimer` | Bloco italico no topo (lembrete: "o gestor ja leu o WBR") |
| `.section-title` | Cabecalho de secao com underline lime (`border-bottom: 2px solid #eef77c`) |
| `.subsection-title` | Cabecalho de subsecao (Para Douglas, Para Tereza) |
| `.question-block` | Cartao branco bordado para cada pergunta da secao 2 |
| `.question-label` | Rotulo "PERGUNTA 1" em uppercase muted |
| `.question-redirect` | Borda esquerda vermelha (Nao aceite, Contexto) |
| `.trap-block` | Cartao para armadilhas (borda esquerda amarela `#FFC107`) |
| `.decision-block` | Cartao para decisoes (borda esquerda vermelha) |
| `.roteiro-block` | Tabela ou cards do roteiro (fundo `#f6f5f0`) |

Identidade visual herdada da apresentacao: `#424135` (texto), `#fffdef` (acento light), `#eef77c` (lime), `#79755c` (muted), `#f6f5f0` (background sutil), `#e8e8e4` (bordas).

Fonte: `"twkEverett", "Segoe UI", Arial, sans-serif`.

Largura util: `max-width: 750px` (ergonomico para A4 retrato com margens 24mm/20mm).

Headings:
- `h1` 28px font-weight 700
- `h2` 14px font-weight 400 (subtitulo do cabecalho)
- `.section-title` 22px font-weight 700 com underline lime
- `.subsection-title` 17px font-weight 700

Ver `examples/ritual-briefing-validado.example.html` como referencia visual completa.

---

## 8. Casos extremos e fallbacks

| Cenario | Como tratar |
|---------|-------------|
| 1 especialista no Card | Secao 2 e Secao 5 tem apenas 1 bloco. Total = `10 + 25 + 5 = 40 min` (ou ampliar bloco unico para 30-40 min se desvio critico) |
| N >= 5 especialistas | Considerar agrupar por equipe N3 ou cortar nivel de detalhe por bloco. Total > 90 min sinaliza ritual longo demais — escalar para N2 |
| 0 acoes ativas no PA | Secao 4 tem decisoes vindas apenas do WBR (Recomendacoes/Escalonamentos). PA nao gera linhas |
| Indicador sem dado (NULL/missing) | Sinaliza armadilha "Qualidade da atribuicao de dados". Vira decisao de auditoria com owner+prazo |
| WBR todo verde | Veredicto frase 2 traz risco estrutural (concentracao, lag, qualidade da carteira). Briefing NAO deixa de existir — verde nao e ausencia de risco |
| Pipeline ausente | Itens "Funil" do roteiro sao omitidos. Bloco fica com Dashboard + Analise apenas |
| WBR sem secao Recomendacoes | Decisoes vem apenas das familias_de_decisoes do Card aplicadas ao contexto |
| Apenas leading verde + lagging vermelho (ou inverso) | Frase 2 do Veredicto cita lag explicitamente; armadilha "Lag temporal como blindagem" e candidata forte |
| Conflito entre WBR e Card | WBR ganha — single source of truth. Atualizar Card depois se evidencia for estrutural |
| Card sem `briefing_customization.versao: "2.0"` | Fallback para fluxo v1.0 (5 secoes prescritivas, sem filtro por sinal). Avisar o usuario para atualizar o Card |

---

## 9. Aprendizados do gold standard CON S18 (2026-04-27)

Validados nas 8 refatoracoes do ciclo:

1. **Citar dado pedindo o dado** — quando uma decisao referencia "20 contratos formalizados (Juliane 19 + Emmanuel 1, R$ 2,51M = 47,4% do volume N1)", o leitor entende imediatamente o tamanho do problema e valida a urgencia
2. **Owner duplo quando aplicavel** — `Owner: Joel Freitas (define) + Tereza Bernardo (executa)` torna explicito que ha dois papeis e dois prazos potencialmente diferentes
3. **Citar deals nominalmente** — "Icoforte parado ha 172 dias", "deal de Thomaz Bianchi (ativa R$ 8,5M)" — abstracao perde forca, nome cria responsabilidade
4. **"Nao aceite" plausivel** — "estou trabalhando nisso", "ela nao vai sair", "os clientes estao pensando" — sao falas reais que vao aparecer; preparar refutacao previa antes de ouvi-las e o que prepara para AGIR
5. **Redirecionamento usa numero do ciclo** — "Estagnadas pioraram de 18 para 62 deals em uma semana" tem mais peso que "concentracao e ruim"
6. **Ciclos consecutivos sao gatilho de decisao binaria** — "quarto ciclo consecutivo em vermelho nos tres KPIs" justifica decisao de mudanca de escopo
7. **Saida obrigatoria por bloco** — explicitar "Lista com status WIN/LOSE/RENEGOCIAR + data de follow-up por deal" obriga o condutor a nao terminar o bloco sem isso
8. **Sair do verde NAO e validacao** — frase explicita do Veredicto desfaz armadilha de "estamos no caminho certo"
9. **Coerencia briefing <-> slide** (v3.0) — total `25 + 15*N` min do roteiro = soma da agenda do slide 2 (composição `8 + 10 + 15*N + 4 + 3`). Numero de decisoes = numero de next-cards no slide Encerramento (último, posição `7 + 3*N`). Numero de especialistas = N do bloco repetível (3 slides por especialista: Dashboard + Análise + Pipeline). Total slides do deck = `7 + 3*N`
10. **Janela de momentum** — citar quando uma decisao foi cabivel e ja passou ("O Summit CON foi concluido em 24/04. A janela de momentum passou.") justifica decidir agora mesmo que mal
11. **Sinal observado vem antes da redacao da armadilha** — gerar a armadilha sempre comeca pelo sinal (numero), nunca pela frase tipica

---

## 10. Checklist de auditoria (14 itens)

Execucao da skill so e considerada completa se todos os 14 itens passarem.

| # | Item | Como verificar | Tipo |
|---|------|----------------|------|
| 1 | Cabecalho com Condutor + Participantes + PERIODO_DADOS + TIMESTAMP_WBR | Grep no MD | — |
| 2 | Veredicto tem exatamente 3 frases em paragrafo unico | Contar pontos finais; sem listas/tabelas | — |
| 3 | Frase 3 do Veredicto aponta para uma decisao concreta da Secao 4 | Verificar consistencia | — |
| 4 | Cada interlocutor da Secao 2 tem nome real (de apresentacao.responsaveis) | Cross-check Card | — |
| 5 | Cada pergunta tem aspas + Nao aceite + Redirecionamento (3 elementos) | Estrutura por pergunta | — |
| 6 | Numero de armadilhas e 3-4 | `grep -c '^\\*\\*"'` na secao 3 | — |
| 7 | Cada armadilha tem `sinal_no_wbr` presente no WBR (rastreabilidade) | Spot-check 3 valores | **SSoT** |
| 8 | Decisoes em formato binario (X OU Y), nao "vamos discutir" | Grep "OU" em cada decisao | — |
| 9 | Cada decisao tem Owner + Prazo (YYYY-MM-DD) + Consequencia | Estrutura por decisao | — |
| 10 | Numero de decisoes do briefing == numero de next-cards do slide Encerramento (último, posição `7 + 3*N`) da apresentacao | Coerencia | **SSoT** |
| 11 | Roteiro tem N+2 blocos (1 abertura + N especialistas + 1 encerramento) | Count blocos | — |
| 12 | Total do roteiro bate com agenda do slide 2 da apresentacao | `{{DUR_TOTAL}}` | **SSoT** |
| 13 | Total entre 50-90 min (faixa esperada) | Numero | — |
| 14 | Briefing tem 300-1200 palavras (gold standard S18 = 1144) | `wc -w` | — |

> Itens 7, 10 e 12 sao **single source of truth** — sem eles o briefing perde rastreabilidade vs WBR + Apresentacao. Falha em qualquer um BLOQUEIA a publicacao.

---

## 11. Referencias cruzadas

| Item | Caminho relativo a skill |
|------|--------------------------|
| Template MD | `templates/ritual-briefing.tmpl.md` |
| Template HTML A4 | `templates/ritual-briefing.tmpl.html` |
| Gold standard MD | `examples/ritual-briefing-validado.example.md` |
| Gold standard HTML A4 | `examples/ritual-briefing-validado.example.html` |
| Estrutura dos slides (deck) | `references/slide-structure.md` |
| Filtros v2.0 e SSoT | `references/migration-v2.md` |
