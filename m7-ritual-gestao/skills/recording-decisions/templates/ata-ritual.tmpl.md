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

<!-- Numerar sequencialmente. Toda decisao deve ter responsavel e prazo. -->

| # | Decisao | Responsavel | Prazo |
|---|---------|-------------|-------|
| D-001 | {decisao} | {responsavel} | {prazo} |

<!-- Se nenhuma decisao: "Nenhuma decisao registrada neste ritual." -->

---

## Contramedidas Definidas

<!-- Ordenar por prioridade: critica > alta > media > baixa. Desempate por receita desc. -->

| ID CSV | Titulo | Indicador | Responsavel | Prazo | Prioridade | Volume | Receita | Status |
|--------|--------|-----------|-------------|-------|------------|--------|---------|--------|
| {id} | {titulo} | {indicador} | {responsavel} | {prazo} | {prioridade} | {volume} | {receita} | Nova |

<!-- Status: "Nova" = inserida neste ritual | "Atualizada" = ja existia, atualizada neste ritual -->
<!-- Se nenhuma contramedida: "Nenhuma contramedida definida neste ritual." -->

---

## Acoes Atualizadas

<!-- Acoes existentes que tiveram status, percentual ou comentarios modificados no ritual. -->

| ID | Titulo | Campo Alterado | Valor Anterior | Valor Novo |
|----|--------|----------------|----------------|------------|
| {id} | {titulo} | {campo} | {antes} | {depois} |

<!-- Se nenhuma atualizacao: "Nenhuma acao existente atualizada neste ritual." -->

---

## Duplicatas Detectadas

<!-- Contramedidas solicitadas que ja existiam no CSV. Omitir secao se nenhuma. -->

| Titulo Solicitado | ID Existente | Status Atual | Acao Tomada |
|-------------------|--------------|--------------|-------------|
| {titulo} | {id_existente} | {status} | {atualizada/ignorada} |

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
