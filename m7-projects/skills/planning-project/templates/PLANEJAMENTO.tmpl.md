---
projeto: "{{project_name}}"
codigo: "{{project_code}}"
lider: "{{lider}}"
sponsor: "{{sponsor}}"
inicio: "{{inicio_yyyy_mm_dd}}"
fim: "{{fim_yyyy_mm_dd}}"
planejamento_status: "DRAFT"
finalizado_em: ""
---

<!--
AVISO — ESTE DOCUMENTO SERÁ CARIMBADO COMO SNAPSHOT ESTÁTICO AO SER FINALIZADO.
Após `planejamento_status: FINAL`, o bloco abaixo será automaticamente preenchido.
Enquanto DRAFT, os artefatos podem ser reabertos/reescritos livremente.

CONVENÇÃO DE MARKERS (imediatamente após cada header `##`):

  <!-- STATUS: PENDING -->                        # estado inicial (sem data)
  <!-- STATUS: DRAFT | YYYY-MM-DD -->             # trabalhado mas não validado
  <!-- STATUS: ACCEPTED | YYYY-MM-DD -->          # validado pela skill + usuário
  <!-- STATUS: SKIPPED | YYYY-MM-DD -->           # não se aplica a este projeto
      <!-- REASON: <motivo curto> -->             # OBRIGATÓRIO quando SKIPPED

Quando o usuário decide ACCEPTED apesar de um critério falhar, a skill adiciona
na linha logo após o STATUS:

  <!-- OVERRIDE: <justificativa curta do usuário> -->

Exemplo real:
  ## 02 · OKRs
  <!-- STATUS: ACCEPTED | 2026-04-18 -->
  <!-- OVERRIDE: 6 KRs por objetivo aceitos porque ciclo curto (3m) exige granularidade maior que o default -->
-->

# Planejamento — {{project_name}}

## 01 · Contexto & Escopo
<!-- STATUS: PENDING -->

### Estrela Guia
*(preencher — métrica quantitativa + timeframe)*

### Contexto Estratégico
*(preencher — por que agora, por que este projeto, quais antecedentes)*

### Faremos (in-scope)
- *(pacotes/entregáveis dentro do escopo)*

### Não Faremos (out-of-scope)
- *(explicitar o que NÃO está no escopo — mínimo 3 itens)*

### Critérios de Aceite do Projeto
*(como saberemos que o projeto terminou?)*

### Decisões de Escopo
| Decisão | Justificativa |
|---|---|
| *(ex.: limitar piloto a 3 unidades)* | *(razão)* |

### Conexões com Portfólio (opcional)
*(este projeto depende de outros? destrava outros? integra programa maior?)*

## 02 · OKRs
<!-- STATUS: PENDING -->

### Cadência de Acompanhamento
*(quinzenal / mensal / outra)*

### Objetivo 1 — *(frase qualitativa, aspiracional, timeboxed no projeto)*
- **KR 1.1** baseline: `X` → target: `Y` até `YYYY-MM-DD` · fonte: *(onde medir)*
- **KR 1.2** ...
- **KR 1.3** ...

### Objetivo 2 — *(...)*
- **KR 2.1** ...
- **KR 2.2** ...

*(2-3 Objetivos recomendado; 3-5 KRs por Objetivo)*

## 03 · WBS/EAP
<!-- STATUS: PENDING -->

### Convenção
Níveis: Projeto → Fase → Subfase → Pacote de Trabalho
Codificação hierárquica: `1`, `1.1`, `1.1.1`
Pacotes entre 8h e 80h de esforço (regra 8/80).

### Decomposição

- **1 Planejamento**
  - 1.1 *(pacote — entregável verificável: ...; responsável: ...)*
  - 1.2 ...
- **2 Execução**
  - 2.1 *(subfase)*
    - 2.1.1 *(pacote ...)*
    - 2.1.2 ...
  - 2.2 ...
- **3 Encerramento**
  - 3.1 ...

## 04 · Cronograma
<!-- STATUS: PENDING -->

### Premissas de Estimativa
*(quem estimou, com base em quê — histórico, analogia, bottom-up)*

### Linhas do Cronograma
| # | Tipo | Pacote/Etapa | Responsável | Início | Fim | Dep. | Entregável | Status |
|---|---|---|---|---|---|---|---|---|
| 1 | *(Fase/Pacote/Marco)* | *(ref. WBS)* | *(pessoa)* | `YYYY-MM-DD` | `YYYY-MM-DD` | *(ref.)* | *(artefato)* | *(Não iniciado)* |

### Caminho Crítico
*(identificar — quais atrasos afetam fim do projeto)*

### Buffer de Incerteza
*(≥10% da duração total, ou justificar por que não)*

## 05 · Roadmap & Marcos
<!-- STATUS: PENDING -->

### Visão em Ondas
- **Agora** (próximas 4-6 semanas, detalhado): ...
- **Próximo** (2-3 meses, contorno): ...
- **Depois** (horizonte do projeto, macro): ...

### Marcos-Chave
| # | Marco | Data | Owner | Critério de Aceite (DoD) | Tipo |
|---|---|---|---|---|---|
| M1 | *(ex.: Go/No-Go piloto)* | `YYYY-MM-DD` | *(pessoa)* | *(critério verificável)* | *(Gate/Handoff/Validação)* |

### Swim-Lane (opcional)
*(se houver múltiplas frentes paralelas — descrever lanes)*

## 06 · Recursos & Dependências
<!-- STATUS: PENDING -->

### Equipe
| Pessoa | Papel | Dedicação | Período | Plano de Proteção de Agenda |
|---|---|---|---|---|
| *(nome)* | *(papel)* | *(ex.: 40%)* | `YYYY-MM-DD`–`YYYY-MM-DD` | *(como garantir o tempo)* |

### Alocação por Período
*(tabela ou narrativa mostrando capacidade semanal/mensal)*

### Dependências Externas
| Dependência | Fornecedor | Data Handoff | Impacto se falhar | Plano B |
|---|---|---|---|---|
| *(ex.: acesso a base X)* | *(time/pessoa)* | `YYYY-MM-DD` | *(o que trava)* | *(contingência)* |

### Investimentos
*(financeiros, ferramentas, licenças — ou justificar ausência)*

## 07 · Plano de Comunicação
<!-- STATUS: PENDING -->

### Stakeholders e Engajamento
| Stakeholder | Papel | Engagement | Como sabemos? | Estratégia |
|---|---|---|---|---|
| *(nome)* | *(sponsor/usuário/...)* | *(unaware/resistant/neutral/supportive/leading)* | *(fonte de leitura)* | *(como mover o ponteiro)* |

### Matriz RACI
| Entregável/Atividade | R | A | C | I |
|---|---|---|---|---|
| *(item)* | *(quem faz)* | *(quem decide — único)* | *(quem consulta)* | *(quem é informado)* |

### Rituais
| Ritual | Frequência | Formato | Audiência | Output |
|---|---|---|---|---|
| *(ex.: Weekly do projeto)* | *(semanal)* | *(30min Teams)* | *(time core)* | *(decisões + blockers)* |

### Canais
- **Default:** *(Teams/Email/Slack)*
- **Urgente:** *(canal)*
- **Status report:** *(cadência + destinatários)*

## 08 · Riscos
<!-- STATUS: PENDING -->

| # | Descrição | Tipo | Prob | Impacto | Trigger Observável | Estratégia | Contramedida | Owner |
|---|---|---|---|---|---|---|---|---|
| R1 | *(específica)* | *(Ameaça/Oportunidade)* | *(Alta/Média/Baixa)* | *(Alto/Médio/Baixo)* | *(sinal de materialização)* | *(avoid/transfer/mitigate/accept \| exploit/share/enhance/accept)* | *(ação planejada)* | *(pessoa)* |

*(mínimo 5 riscos; incluir oportunidades, não só ameaças)*

### Matriz Probabilidade × Impacto
*(opcional — visualização da concentração de riscos)*

## 09 · Calendário
<!-- STATUS: PENDING -->

### Rituais Recorrentes
| Ritual | Cadência | Dia/Hora | Duração |
|---|---|---|---|
| *(ex.: Weekly projeto)* | *(semanal)* | *(quarta 10h)* | *(30min)* |

### Marcos no Calendário
*(plotagem dos marcos de §05 no eixo temporal — mês a mês)*

### Revisões de Fase
| Transição | Data | Participantes | Critério de transição |
|---|---|---|---|
| *(ex.: Planejamento → Execução)* | `YYYY-MM-DD` | *(sponsor + líder)* | *(pré-requisitos atendidos?)* |

### Eventos Externos (feriados, congelamentos)
*(bloqueios conhecidos que afetam o cronograma)*
