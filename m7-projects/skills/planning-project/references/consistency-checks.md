# 7 Verificações de Consistência Cross-Artefato (Fase 3)

Antes de carimbar `planejamento_status: FINAL`, a skill roda as 7 verificações abaixo para detectar inconsistências **entre** artefatos. Erros comuns: marco mencionado no roadmap mas ausente do cronograma, stakeholder no RACI mas não alocado em Recursos, owner de risco que não existe na equipe.

**Regra firme:** a skill **não corrige automaticamente**. Lista inconsistências, usuário decide se resolve no artefato fonte (voltando ao incremento) ou se sobrescreve com justificativa.

## Como executar as verificações

A skill carrega o MD inteiro, parseia cada seção, e roda as 7 verificações em sequência. Para cada, emite relatório:

```
✅ Consistente
⚠️  Inconsistência detectada: <descrição específica>
```

Ao final, apresenta resumo consolidado ao usuário.

## As 7 verificações

### 1. Marcos do Roadmap existem no Cronograma?

**O que verifica:** cada marco listado em §05 · Roadmap & Marcos deve aparecer como linha no §04 · Cronograma (com mesma data ou data coerente).

**Como detectar:** extrair lista de marcos (nome + data) de §05; para cada, buscar linha correspondente em §04 (texto do marco na coluna "Pacote/Etapa" ou "Tipo=Marco").

**Falha típica:**
- Roadmap declara "M2: Piloto validado em 2026-06-15"
- Cronograma não tem nenhuma linha tipo "Marco" próxima dessa data

**Resolução sugerida:**
- Adicionar linha ao cronograma com tipo=Marco, ou
- Remover marco do roadmap se era apenas aspiracional

### 2. Stakeholders do RACI estão em Recursos?

**O que verifica:** cada pessoa mencionada no RACI (§07) deve aparecer na tabela de Equipe (§06), ou ter relação explicada (stakeholder externo, consultor ad-hoc).

**Como detectar:** extrair nomes únicos do RACI (colunas R, A, C, I); cross-referenciar com nomes em §06 · Equipe.

**Falha típica:**
- RACI cita "Maria — A para aprovação do playbook"
- Maria não aparece em §06 (não é time core nem stakeholder formal)

**Resolução sugerida:**
- Adicionar Maria ao §06 com papel de "stakeholder externo" e % de engajamento, ou
- Mover responsabilidade para alguém do time core, ou
- Adicionar nota em §07 explicando status de Maria

### 3. Owners de Riscos estão na equipe?

**O que verifica:** cada owner de risco em §08 deve ser pessoa identificada em §06 (ou com nota explicativa se for externa).

**Como detectar:** extrair coluna "Owner" de §08; cross-referenciar com §06.

**Falha típica:**
- Risco R3 com owner "time de dados"
- "Time de dados" não é pessoa — owner precisa ser singular

**Resolução sugerida:**
- Substituir "time de dados" por pessoa específica, ou
- Explicitar que owner formal é [pessoa X] mesmo que execução seja pelo time

### 4. KRs dos OKRs são suportados por trabalho no Cronograma?

**O que verifica:** para cada KR em §02, deve existir pelo menos um pacote no §03 WBS (e portanto linha no §04) cujo entregável contribua para atingir o KR.

**Como detectar:** para cada KR, perguntar "qual pacote do WBS produz o resultado que move este KR?". Verificação **qualitativa** (skill apresenta ao usuário, usuário confirma mentalmente).

**Falha típica:**
- KR 1.1: "NPS interno sobe de 6 para 8 até Set/26"
- Nenhum pacote no WBS trata de coleta de NPS, intervenções de engajamento, ou medição

**Resolução sugerida:**
- Adicionar pacote(s) no WBS que suportem o KR, ou
- Reavaliar KR — se não há trabalho planejado, ele não será atingido

### 5. Datas-chave consistentes em todos os artefatos?

**O que verifica:** frontmatter (`inicio`, `fim`) bate com:
- Datas de primeira/última atividade em §04 Cronograma
- Período declarado em §05 Roadmap
- Alocação de equipe em §06

**Como detectar:** extrair início/fim de cada artefato; comparar.

**Falha típica:**
- Frontmatter: `inicio: "2026-03-01"`, `fim: "2026-09-30"`
- §04 tem primeira atividade em 2026-02-15 (antes do início declarado)
- §06 aloca equipe até 2026-12-31 (depois do fim)

**Resolução sugerida:**
- Ajustar frontmatter para refletir realidade (se início real é antes, atualizar), ou
- Ajustar artefatos divergentes

### 6. Pacotes do WBS aparecem no Cronograma?

**O que verifica:** cada pacote de trabalho (folha da árvore WBS em §03) deve ter linha correspondente em §04 Cronograma.

**Como detectar:** extrair todos os pacotes folha do WBS (itens terminais das listas aninhadas); cross-referenciar com coluna "Pacote/Etapa" em §04.

**Falha típica:**
- WBS tem pacote "1.2.3 Workshop de alinhamento com stakeholders"
- Cronograma não menciona esse workshop em nenhuma linha

**Resolução sugerida:**
- Adicionar linha ao cronograma, ou
- Remover pacote do WBS se era redundante (mas verificar que não era necessário antes)

### 7. Rituais do Calendário estão no Plano de Comunicação?

**O que verifica:** cada ritual recorrente em §09 · Calendário deve ter entrada correspondente em §07 · Rituais (mesma frequência, mesmo propósito).

**Como detectar:** comparar tabela de Rituais de §07 com tabela de Rituais Recorrentes de §09.

**Falha típica:**
- §09 lista "Daily stand-up" como ritual diário
- §07 não menciona daily — só o weekly

**Resolução sugerida:**
- Adicionar daily ao §07 com formato/audiência/output explícitos, ou
- Remover daily do §09 se não é real, ou
- Verificar se são mesma coisa nomeada diferente

## Formato do relatório final

A skill apresenta ao usuário no final da Fase 3:

```
REVISÃO DE CONSISTÊNCIA — <projeto>

1. Marcos do Roadmap no Cronograma
   ⚠️  M2 "Piloto validado" (2026-06-15) não aparece em §04

2. Stakeholders do RACI em Recursos
   ✅ Consistente

3. Owners de Riscos na equipe
   ⚠️  R3 owner "time de dados" não é pessoa singular

4. KRs suportados por trabalho no Cronograma
   ⚠️  KR 1.1 (NPS) — nenhum pacote do WBS suporta

5. Datas-chave consistentes
   ✅ Consistente

6. Pacotes do WBS no Cronograma
   ✅ Consistente

7. Rituais do Calendário no Plano de Comunicação
   ⚠️  "Daily stand-up" em §09 não aparece em §07

RESUMO: 4 inconsistências detectadas em 3 artefatos (§05, §08, §02, §09/§07).

Como resolver:
- (a) voltar a cada artefato e corrigir (volta para Fase 2, reabre incremento)
- (b) aceitar inconsistências com OVERRIDE + justificativa (registro no MD)
- (c) pausar — fechar depois

Qual caminho?
```

## Regra de ouro

Inconsistências **detectadas** e **aceitas conscientemente** (com OVERRIDE) são OK. Inconsistências **não detectadas** ou **silenciadas** são débito técnico de planejamento — e aparecem como surpresa 3 meses depois.

A skill executa as 7 verificações **sempre**, mesmo que usuário queira pular. Se o usuário insiste em finalizar sem resolver, registrar no frontmatter uma nota:

```yaml
consistency_overrides:
  - "R3 owner genérico aceito — time de dados ainda sem líder nomeado"
  - "KR 1.1 sem suporte no WBS aceito — medição será externa ao projeto"
```

Isso preserva autonomia do usuário **e** cria trilha de auditoria para retrospectivas.
