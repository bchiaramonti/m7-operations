# Ata do Ritual N2 - {vertical} - {data}

> Gerado automaticamente por m7-ritual-gestao (E5 — recording-decisions)

## Informacoes Gerais

| Campo | Valor |
|-------|-------|
| **Data** | {data} |
| **Vertical** | {vertical} |
| **Participantes** | {participantes} |
| **Duracao** | {duracao} |
| **WBR de referencia** | {wbr_referencia} |

---

## Decisoes

<!-- Numerar sequencialmente. Toda decisao deve ter responsavel. -->
<!-- v2.0 (2026-05-31): decisoes NAO tem prazo (memory feedback_decisoes_sem_prazo). -->

| # | Decisao | Responsavel |
|---|---------|-------------|
| D-001 | {titulo} | {responsavel} |

<!-- Se nenhuma decisao: "Nenhuma decisao registrada neste ritual." -->

---

## Contramedidas Definidas

<!-- Ordenar por prioridade v2.0: urgent > high > normal > low. Desempate por receita desc. -->
<!-- IDs ClickUp internos sao machine-only (bloco scope_task_ids no final do MD); -->
<!-- nao aparecem nas tabelas humanas. Membros M7 nao precisam saber que ClickUp existe. -->

| # | Titulo | Indicador | Responsavel | Prazo | Prioridade | Volume | Receita |
|---|--------|-----------|-------------|-------|------------|--------|---------|
| C-001 | {titulo} | {indicador} | {responsavel} | {prazo} | {prioridade} | {volume} | {receita} |

<!-- Numerar C-001, C-002, ... sequencialmente (humano-friendly). -->
<!-- Se nenhuma contramedida: "Nenhuma contramedida definida neste ritual." -->

---

## Acoes Atualizadas

<!-- Acoes pre-existentes que tiveram status, percentual ou comentarios atualizados no ritual. -->
<!-- Sem coluna ID — identificacao via Titulo (humano-friendly). -->

| Titulo | Campo Alterado | Valor Anterior | Valor Novo |
|--------|----------------|----------------|------------|
| {titulo} | {campo} | {antes} | {depois} |

<!-- Se nenhuma atualizacao: "Nenhuma acao existente atualizada neste ritual." -->

---

## Duplicatas Detectadas

<!-- Contramedidas solicitadas que ja existiam. Omitir secao se nenhuma. -->

| Titulo Solicitado | Acao Tomada |
|-------------------|-------------|
| {titulo} | {atualizada/ignorada — Titulo da task existente: "..."} |

---

## Escalonamentos para N1

<!-- Itens que precisam de decisao do comite executivo (N1). -->

- {item_escalonamento}

<!-- Se nenhum escalonamento: "Nenhum item para escalonamento." -->

---

## Proximos Passos

| Acao | Responsavel | Prazo |
|------|-------------|-------|
| {acao} | {responsavel} | {prazo} |

---

<!--
================================================================================
BLOCO MACHINE-READABLE — INVISIVEL NO RENDER MD/HTML/PDF

scope_task_ids (v3.8.0+ 2026-05-12): handoff para o proximo ciclo G2.2.
Consumido pela `m7-controle/collecting-data` Fase 1.5 (subcomando
`collect.py apply-scope-filter`) para particionar tasks ClickUp em
escopo_ritual_passado vs ad_hoc_pos_ritual.

Memory: reference_g2_2_action_scope_filter.

Membros M7 nao veem este bloco — fica em HTML comment para nao poluir
a leitura humana da ata. IDs sao infra de governanca pura.
================================================================================
-->
<!-- scope_task_ids:
ritual_date: {data_ritual}
vertical: {vertical}
nivel: {nivel}
subnivel: {subnivel}
created_in_ritual:
{lista_ids_created_in_ritual}
preexisting_discussed:
{lista_ids_preexisting_discussed}
-->

## Resumo Quantitativo

| Metrica | Valor |
|---------|-------|
| Decisoes registradas | {total_decisoes} |
| Contramedidas novas | {total_novas} |
| Acoes atualizadas | {total_atualizadas} |
| Duplicatas detectadas | {total_duplicatas} |
| Escalonamentos | {total_escalonamentos} |

---

*Gerado: {timestamp} | Referencia: WBR semana {semana} | Vertical: {vertical}*
