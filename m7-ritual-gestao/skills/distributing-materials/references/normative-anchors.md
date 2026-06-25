# Normative Anchors — distributing-materials

Citações literais dos normativos M7 que governam a distribuição de materiais de ritual. Esta skill **deve** cumprir cada uma delas.

> Fonte: documentos em `00-Institucional/Normativos/` no OneDrive M7.

---

## MAN-PERF-003 v1.0 (Manual do Processo de Rituais de Gestão) — Seção 5.2

**RN-06 — Validação humana antes da distribuição**

> "A geração de materiais é automatizada via Cowork; o analista de Performance valida o output antes da distribuição."

**Implicação na skill:** o fluxo é obrigatoriamente **2-fase** (`preview` → aprovação humana → `commit`). O command `/approve-ritual` (E3) e `/approve-ata` (E5.7) executam o gate humano. **Nunca pular preview.**

---

## MAN-PERF-003 v1.0 — Tabela 6 (Regras de Negócio Preparação e Distribuição)

**RN-07 — Conteúdo obrigatório do material**

> "O material deve conter: visão geral metas vs. realizado, desvios >5%, status de contramedidas abertas e tendência MoM."

**Implicação na skill:** `validate_content.py` verifica os **4 elementos** antes de liberar preview. Falha em qualquer um aborta o fluxo.

**RN-08 — Single source of truth**

> "Indicadores devem usar a mesma fonte e período do WBR (G2.2) para single source of truth."

**Implicação na skill:** mensagem deriva **exclusivamente** do `wbr-{vertical}-{data}.data.json` (canonical JSON gerado em E6). Nunca do MD/HTML do briefing.

**RN-09 — Antecedência mínima**

> "O gestor deve receber os materiais com antecedência mínima de 24h (semanal) ou 72h (mensal)."

**Implicação na skill:** `compute_on_time()` em `slack_send.py` calcula:
- N3 (Semanal): deadline = ciclo_date - 1 dia (23:59)
- N2 (Mensal): deadline = ciclo_date - 3 dias (23:59)

Resultado vai no `distribuicao-log.csv` (coluna `on_time`) — alimenta KPI CP-04 mensal.

---

## MAN-PERF-003 v1.0 — Seção 9 (Critérios de Qualidade)

**CP-04 — Distribuição no prazo + confirmação de leitura**

> "Materiais entregues com antecedência (24h semanal / 72h mensal); confirmação de leitura do gestor."

**Implicação na skill:** dois sub-critérios:
1. **Entrega no prazo** — coluna `on_time` no log CSV. KPI ≥90% mensal.
2. **Confirmação de leitura** — coluna `confirmacoes_leitura_count` (inicialmente `0`; populada por feature futura via `reactions:read`). Mensagem solicita explicitamente "Reaja com ✅".

---

## INS-PERF-002 v2.1 (Preparação Pré-Ritual N) — Seção 4.3, Passos 11-13

**Passo 11 — Anexos e assunto**

> "Envie ao Gestor e a todos os participantes listados no Calendário de Rituais (03-Rituais/Calendario-de-Rituais.xlsx) uma mensagem contendo:
> a) Apresentação HTML do ritual
> b) Briefing HTML
> Assunto: 'Ritual {Vertical} N{NIVEL} S{nº semana}'"

**Implicação na skill:**
- Anexos pré-ritual = **HTML deck + HTML briefing** (NÃO o briefing MD; é uso interno)
- Subject literal montado por `iso_week.py`: `"Ritual {Vertical} N{NIVEL} S{NN}"` com ISO week 2 dígitos
- Destinatários lidos do Calendário-de-Rituais.xlsx (colunas estendidas — ver `calendar-schema.md`)

**Passo 12 — Follow-up e escalação**

> "Solicite confirmação de recebimento ao Gestor. Se não houver resposta em 12 horas, faça follow-up direto. Se não responder até o final de D-1, escale ao líder direto do Gestor."

**Implicação na skill (Phase 1):** mensagem solicita reação ✅; CICLO.md registra `escalacao_acionada` quando aplicável. **Lógica de follow-up automático ficará para feature futura** (`reactions:read` polling), mas o slot do log já existe.

**Passo 13 — Arquivamento**

> "Confirme que os arquivos finais estão salvos em: 03-Rituais/N{N}/{Vertical}/{Semanal ou Mensal}/{YYYY-SNN ou YYYY-MM}/"

**Implicação na skill:** a skill `preparing-materials` (E2) replica os artefatos em **`03-Rituais/N{N}/{Vertical-cap}[-{subnivel}]/{Cadencia}/{Periodo}/`** (level-first, default ON 2026-06-09; ex: `N3/Seguros-wl/Semanal/2026-S22/`). Esta skill apenas lê desse local via `resolve_ritual_path.py`.

---

## INS-PERF-004 v2.0 (Registro Pós-Ritual N) — Seção 4.2, Passos 4-6

**Passo 4 — Envio da ata**

> "Envie a ata para o Gestor do ritual e para todos os participantes, solicitando confirmação de recebimento."

**Implicação na skill:** modo `post_ritual` envia a ata para os mesmos destinatários do pré-ritual (Gestor + Participantes).

**Passo 5 — Validação**

> "Aguarde retorno em até 24 horas. Caso algum destinatário aponte correções ou complementos, ajuste a ata e redistribua a versão atualizada."

**Implicação na skill:** se ata for re-gerada (E5 re-executada), `slack_send.py --phase commit` cria nova linha de log com `cycle_date` igual; downstream KPI conta apenas a entrega mais recente.

**Passo 6 — Escalação ao nível superior**

> "Se houver escalações ao nível superior, envie a ata também ao líder do nível acima (ex.: N3 envia ao Gestor N2; N2 envia à Diretoria)."

**Implicação na skill:** quando a ata contém `escalacao_acionada: true` no YAML block, `resolve_recipients.py --include-escalacao` retorna o `lider_direto` (coluna `Lider-Direto-User-ID` do XLSX). Esse target recebe DM adicional.

**ATENÇÃO — timeout de 48h**

> "Se não houver confirmação de recebimento em 48h, registre a pendência e prossiga com as demais entregas (contramedidas e boas práticas)."

**Implicação na skill (Phase 1):** log CSV registra timestamp do envio; tracking de confirmação fica para feature futura.

---

## POL-PERF-001 v1.2 (Política de Performance)

Cláusula geral sobre antecedência mínima por nível de ritual:

> "Materiais devem ser entregues ao gestor com antecedência mínima de 48 horas (N1), 24 horas (N2) e 4 horas (N3)."

**Conflito aparente:** POL diz "N3 = 4 horas" mas MAN-PERF-003 RN-09 diz "semanal = 24h". A skill segue **MAN-PERF-003 RN-09** porque é mais conservador (24h > 4h) e o MAN é o documento operacional vigente (consistente com INS-PERF-002 Passo 11 "D-1").

---

## Indicador CP-04 — Pontualidade de entrega

| Campo | Valor |
|---|---|
| Nome | Pontualidade de entrega de materiais |
| Fórmula | `(Materiais entregues no prazo / Total de materiais programados) × 100` |
| Fonte | `desempenho/03-Rituais/distribuicao-log.csv` (gerado por esta skill) |
| Meta | **≥90%** (mensal) |
| Frequência | Mensal |
| Verificador | Analista de Performance |

**Implicação na skill:** a skill **não calcula** o KPI; ela apenas grava cada entrega no CSV. Uma futura skill `reporting-distribution-kpi` consumirá o CSV e gerará o relatório mensal.

---

## Resumo: Regra → Implementação

| Regra | Onde está implementada |
|---|---|
| RN-06 (validação humana) | SKILL.md Fase 5/6 + commands `approve-ritual` e `approve-ata` (gate preview→commit) |
| RN-07 (4 elementos) | `slack_send.py::validate_rn07()` |
| RN-08 (single source of truth) | `slack_send.py::render_message()` lê só do `wbr-*.data.json` |
| RN-09 (D-1/D-3) | `slack_send.py::compute_on_time()` + log CSV |
| CP-04 (entrega + leitura) | `delivery-log-schema.md` + future `reporting-distribution-kpi` |
| Passo 11 (anexos + subject) | `slack_send.py::render_message()` + `build_subject()` (ISO week) |
| Passo 12 (escalação) | `--include-escalacao` em `resolve_recipients.py` + slot no log |
| Passo 13 (arquivamento) | Reusa estrutura `03-Rituais/` já criada por `preparing-materials` E2 |
| Passos 4-6 INS-PERF-004 | Modo `post_ritual` da skill |
