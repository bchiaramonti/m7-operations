# Briefing — Ritual {{NIVEL}} {{VERTICAL}} | {{CICLO}} | {{DATA_RITUAL}}

**Condutor:** {{CONDUTOR}}
**Participantes:** {{LISTA_PARTICIPANTES}}

---

## 1. Veredicto

{{FRASE_1_SITUACAO_GERAL}} {{FRASE_2_RISCO_OCULTO_PELO_SEMAFORO}} {{FRASE_3_DECISAO_ALVO_DA_REUNIAO}}

<!--
Regras (ver briefing/CLAUDE.md secao 4):
- Exatamente 3 frases em paragrafo unico (sem listas, sem tabelas).
- Frase 1: situacao geral em 1 linha.
- Frase 2: risco real que o semaforo NAO mostra (deriva de eixos_de_risco_a_considerar do Card filtrado pelo WBR).
- Frase 3: decisao especifica que precisa sair desta reuniao (nao generica; aponta para uma das decisoes da secao 4).
- NUNCA listar numeros de KPIs aqui. O gestor ja leu o WBR.
-->

---

## 2. O Que Provocar

<!-- Repetir o bloco abaixo para cada interlocutor relevante (especialista, coordenador, head). Maximo 3-4 perguntas por interlocutor. -->

### Para {{NOME_INTERLOCUTOR_1}}

**"{{PERGUNTA_DIRETA_1A}}"**
Nao aceite: {{NAO_ACEITE_1A}}
Redirecionamento: {{REDIRECIONAMENTO_1A}}

**"{{PERGUNTA_DIRETA_1B}}"**
Nao aceite: {{NAO_ACEITE_1B}}
Redirecionamento: {{REDIRECIONAMENTO_1B}}

**"{{PERGUNTA_DIRETA_1C}}"**
Nao aceite: {{NAO_ACEITE_1C}}
Redirecionamento: {{REDIRECIONAMENTO_1C}}

### Para {{NOME_INTERLOCUTOR_2}}

**"{{PERGUNTA_DIRETA_2A}}"**
Nao aceite: {{NAO_ACEITE_2A}}
Redirecionamento: {{REDIRECIONAMENTO_2A}}

**"{{PERGUNTA_DIRETA_2B}}"**
Nao aceite: {{NAO_ACEITE_2B}}
Redirecionamento: {{REDIRECIONAMENTO_2B}}

<!--
Regras (ver briefing/CLAUDE.md secao 4):
- Perguntas FECHADAS (exigem resposta concreta, nao discurso).
- Cada pergunta tem 3 elementos: pergunta direta entre aspas, "Nao aceite" (resposta evasiva tipica), Redirecionamento (dado do ciclo que sustenta a provocacao).
- Aplicar eixos_de_provocacao_a_considerar do Card a interlocutores reais (de apresentacao.responsaveis ou equivalente).
- Citar nome do interlocutor (ex: Douglas Silva, Tereza Bernardo). Nunca pergunta generica sem dono.
- Numero de assessores nomeados deve ser real (do bridge Bitrix-ClickHouse).
-->

---

## 3. Armadilhas da Reuniao

<!-- Selecionar 3-4 armadilhas. Cada uma deve ter sinal real no WBR do ciclo (familias_de_armadilhas[].sinal_generico_no_wbr precisa estar presente). -->

**"{{FRASE_TIPICA_ARMADILHA_1}}"**
Sinal observado: {{SINAL_NO_WBR_1}}
Redirecionamento: {{REDIRECIONAMENTO_GERAL_1}}

**"{{FRASE_TIPICA_ARMADILHA_2}}"**
Sinal observado: {{SINAL_NO_WBR_2}}
Redirecionamento: {{REDIRECIONAMENTO_GERAL_2}}

**"{{FRASE_TIPICA_ARMADILHA_3}}"**
Sinal observado: {{SINAL_NO_WBR_3}}
Redirecionamento: {{REDIRECIONAMENTO_GERAL_3}}

**"{{FRASE_TIPICA_ARMADILHA_4}}"**
Sinal observado: {{SINAL_NO_WBR_4}}
Redirecionamento: {{REDIRECIONAMENTO_GERAL_4}}

<!--
Regras (ver briefing/CLAUDE.md secao 4):
- Frase tipica = como a armadilha aparecera na reuniao (uma fala plausivel do interlocutor).
- Sinal observado = evidencia concreta do periodo corrente que materializa a familia (numero, percentual, indicador). Sem sinal, NAO incluir a armadilha.
- Redirecionamento usa o redirecionamento_geral da familia, adaptado ao caso especifico.
- Maximo 3-4. Selecionar as MAIS PROVAVEIS no ciclo, nao todas as familias do Card.
-->

---

## 4. Decisoes Que Precisam Sair

<!-- 1 a 4 decisoes binarias com owner, prazo e consequencia explicitas. -->

**1. {{TITULO_DECISAO_1}}**
Formato: {{FORMA_BINARIA_1}}
Owner: {{OWNER_1}} | Prazo: {{PRAZO_1}}
Consequencia de nao-decidir: {{CONSEQUENCIA_1}}

**2. {{TITULO_DECISAO_2}}**
Formato: {{FORMA_BINARIA_2}}
Owner: {{OWNER_2}} | Prazo: {{PRAZO_2}}
Consequencia de nao-decidir: {{CONSEQUENCIA_2}}

**3. {{TITULO_DECISAO_3}}**
Formato: {{FORMA_BINARIA_3}}
Owner: {{OWNER_3}} | Prazo: {{PRAZO_3}}
Consequencia de nao-decidir: {{CONSEQUENCIA_3}}

<!--
Regras (ver briefing/CLAUDE.md secao 4):
- Cada decisao no formato BINARIO (sim/nao OU opcao A vs B). Nada de "vamos discutir X".
- Owner com nome real (nao papel generico). Quando a decisao tem dois owners (decide+executa), explicitar ambos.
- Prazo em data absoluta (YYYY-MM-DD), nunca "em breve" ou "asap".
- Consequencia de nao-decidir tem que ser concreta (impacto em projecao, gap operacional, custo de continuar).
- Cada decisao deve estar referenciada nas familias_de_decisoes do Card OU vir explicitamente das Recomendacoes/Escalonamentos do WBR.
- Decisoes precisam estar coerentes com slide 10 (Encerramento) da apresentacao do ritual — mesmas decisoes, mesmo numero D.
-->

---

## 5. Roteiro

<!-- Tempo total = soma das duracoes. Default: T = 10 + 25*N + 5 (N = qtd de especialistas). Ajustar conforme estrutura_de_roteiro.duracao_min do Card. -->

**Visao Geral ({{DUR_VISAO_GERAL}} min)**
{{INTENCAO_VISAO_GERAL}}

**Bloco {{ESPECIALISTA_1}} ({{DUR_ESPECIALISTA_1}} min)**
Intencao: {{INTENCAO_ESPECIALISTA_1}}
- Dashboard: {{ITEM_DASHBOARD_1}}
- Analise: {{ITEM_ANALISE_1}}
- Funil: {{ITEM_FUNIL_1}}
- Saida obrigatoria: {{SAIDA_OBRIGATORIA_1}}

**Bloco {{ESPECIALISTA_2}} ({{DUR_ESPECIALISTA_2}} min)**
Intencao: {{INTENCAO_ESPECIALISTA_2}}
- Dashboard: {{ITEM_DASHBOARD_2}}
- Analise: {{ITEM_ANALISE_2}}
- Funil: {{ITEM_FUNIL_2}}
- Saida obrigatoria: {{SAIDA_OBRIGATORIA_2}}

<!-- Repetir bloco para N especialistas. -->

**Decisoes e Encerramento ({{DUR_ENCERRAMENTO}} min)**
{{INTENCAO_ENCERRAMENTO}}

**Total: {{DUR_TOTAL}} min** (alinhado com slide 2 da apresentacao: {{COMPOSICAO_AGENDA}}).

<!--
Regras (ver briefing/CLAUDE.md secao 4):
- Cada bloco tem INTENCAO (resultado esperado), nao apenas tema.
- "Saida obrigatoria" = artefato concreto que precisa sair do bloco (lista de deals classificados, deals priorizados com data, decisao em ata).
- Tempos respeitam estrutura_de_roteiro[].duracao_min do Card. Regras adicionais por status do indicador (+8 min por Vermelho, +4 min por Amarelo) sao ajustes opcionais.
- Total final precisa bater com agenda do slide 2 da apresentacao (coerencia briefing <-> slide).
-->
