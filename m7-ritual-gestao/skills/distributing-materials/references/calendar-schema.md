# Schema do Calendário-de-Rituais.xlsx (extensão)

**Localização:** `desempenho/03-Rituais/Calendario-de-Rituais.xlsx` (sheet `Calendario`).

Este documento descreve as colunas que `resolve_recipients.py` espera. **A extensão real é tarefa manual do Pedro** (fora do escopo do código da skill).

---

## Estado Atual (pré-extensão)

A sheet `Calendario` tem hoje 11 colunas:

| # | Coluna | Tipo | Exemplo |
|---|---|---|---|
| 1 | Vertical | str | Consórcios |
| 2 | Sigla | str | CON |
| 3 | Nivel | str | N3 - Operacional |
| 4 | Frequencia | str | Semanal |
| 5 | Dia da Semana | str | Terça-feira |
| 6 | Horario | str | 13:00 |
| 7 | Duracao (min) | int | 60 |
| 8 | Condutor | str | Joel Freitas |
| 9 | Facilitador | str | Performance |
| 10 | Status | str | Definido |
| 11 | Observacoes | str | (livre) |

Sem colunas Slack — `INS-PERF-002 Passo 11` referencia "todos os participantes listados no Calendário" mas a sheet hoje não armazena participantes nem IDs.

---

## Estado Alvo (S4 2026-05-20 — gravado)

Adicionadas **5 colunas novas** ao final da sheet `Calendario`. Cabeçalho deve bater **exatamente** (case-sensitive):

| # | Coluna | Tipo | Obrigatória? | Exemplo |
|---|---|---|---|---|
| 12 | **Subnivel** | str `wl`/`re` ou vazio | ⚠️ Só quando vertical tem split (ex: Seg WL/RE) | wl |
| 13 | **Gestor-User-ID** | str `U…` | ✅ Sim | U06RSGEH51R |
| 14 | **Participantes-Nomes** | str (lista `;`-separada) | ✅ Sim | Douglas Silva; Tereza Cristina; Sara Caetano |
| 15 | **Participantes-User-IDs** | str (lista `;`-separada) | ✅ Sim | U0A0AE52Q07; U098F2S4GG4; U05HEK3N7RN |
| 16 | **Lider-Direto-User-ID** | str `U…` ou vazio | ⚠️ Só usada em pós-ritual com escalação (fallback DM) | U043D1ZF69L |
| 17 | **Canal-Vertical-ID** | str `C…`/`G…` ou vazio | ⚠️ Usado em **pós-ritual** (envio coletivo ao canal). Vazio = fallback DMs | C0B51PR3FSA (Cons #consorcios) |

### Regras de preenchimento

1. **IDs são User IDs Slack** (formato `U` + 10-12 chars), **NÃO** DM Channel IDs (`D...`). Ver memória `reference_slack_user_vs_dm_ids.md` — o bot abre DM em runtime via `conversations.open`.
2. **Listas separadas por `;`** (ponto-e-vírgula seguido de espaço, ou apenas `;`). Trailing/leading whitespace é tolerado.
3. **Participantes-Nomes e Participantes-User-IDs devem ter o mesmo número de itens.** Mismatch causa erro `mismatch_participantes` em `resolve_recipients.py`.
4. **Linha por Vertical+Nivel+Subnivel** quando a vertical tem split (ex: Seguros WL e RE = 2 linhas com `Subnivel=wl` e `Subnivel=re`). Cards consolidados (sem subnivel) ficam com a coluna `Subnivel` vazia.
5. **Vertical com acento** (Consórcios, Crédito) é matcheada por normalização Unicode em `resolve_recipients.py::_norm_vertical_for_match`. O cabeçalho preserva o acento original.

### Lógica de match em `resolve_recipients.py`

- Coleta todas as linhas que matcheam Vertical+Nivel
- Se `--subnivel` informado: filtra pelas que têm `Subnivel == valor` (case-insensitive)
- Se `--subnivel` ausente:
  - Se há linhas com `Subnivel` preenchido e nenhuma vazia → erro `subnivel_required` com lista de subniveis disponíveis
  - Se há uma única linha sem `Subnivel` (vertical consolidada) → OK
  - Caso híbrido (consolidada + split) → preferir consolidada

### Linhas populadas hoje (2026-05-20)

| Vertical | Subnivel | Nivel | Cadência | Canal-Vertical-ID | Status |
|---|---|---|---|---|---|
| Consorcios | (vazio) | N3 | Terça 13:00 | C0B51PR3FSA ✅ | Definido ✅ |
| Seguros | wl | N3 | Quinta 15:00 | (a criar) | Definido (User IDs OK) |
| Seguros | re | N3 | Quinta 13:00 | (a criar) | Definido (User IDs OK) |
| PJ2 | (vazio) | N2 | Segunda após 2º domingo do mês, 14:00 | (a criar) | Definido (User IDs OK) |
| Investimentos, Crédito, Universo, Consórcios N2, Seguros N2 | — | — | — | — | A definir (linhas sem User IDs) |

> **Canais Slack:** Cons N3 já tem canal (`C0B51PR3FSA`, bot `m7-desempenho` é membro). Demais verticais ainda não — quando criar, adicionar `/invite @m7-desempenho` e preencher Canal-Vertical-ID no XLSX. Enquanto vazio, post_ritual cai em **fallback DMs** (gestor + participantes + líder direto se escalação).

---

## Validação programática

```bash
python skills/distributing-materials/scripts/resolve_recipients.py \
  --calendar-path "C:/.../03-Rituais/Calendario-de-Rituais.xlsx" \
  --vertical consorcios \
  --nivel N3
```

Saídas possíveis:

| Exit code | code (campo JSON) | Significado | Ação |
|---|---|---|---|
| 0 | — | OK, retorna JSON com gestor+participantes | Distribuição prossegue |
| 2 | — | Erro de invocação (openpyxl ausente, path inválido) | Corrigir comando |
| 3 | `row_not_found` | Linha vertical+nivel não encontrada | Pedro adiciona linha no XLSX |
| 3 | `subnivel_required` | Vertical tem split de subnivel mas `--subnivel` não informado | Re-rodar com `--subnivel wl` / `re` |
| 3 | `subnivel_not_found` | `--subnivel` informado não bate com nenhuma linha | Conferir argumento ou XLSX |
| 4 | `empty_cells` | Linha encontrada mas Gestor-User-ID/Participantes vazios | Pedro corrige células no XLSX |
| 4 | `mismatch_participantes` | Participantes-Nomes e Participantes-User-IDs com qtd diferente | Pedro corrige listas |
| 4 | `ambiguous_subnivel_match` / `ambiguous_consolidated` | Múltiplas linhas matcheando | Deduplicar XLSX |

---

## Mapeamento atual (registro 2026-05-19, 11 destinatários)

Coletado via `users.list` na workspace M7 — fonte primária para preenchimento manual do XLSX:

| Nome real (Slack) | Username | User ID | Papel |
|---|---|---|---|
| Bruno Chiaramonti | bruno.chiaramonti | U043D1ZF69L | Gestor de Performance (escalação) |
| Joel Freitas | joel.freitas | U06RSGEH51R | Gestor Cons + Seg + PJ2 |
| Filipe costa | filipe.costa | U0A35AVR5EJ | Gestor Investimentos |
| Tarcisio Catunda | tarcisio.catunda323 | U06F1R7N350 | Especialista Seg WL |
| Claudia Maria Moraes De Souza | claudia | U03H9T1DZPS | Especialista Seg WL |
| Emmanuel Martins | emmanuel.martins | U09V93Q1CTT | Especialista Seg RE |
| Samuel Sinval | samuel.sinval | U0A3ETJ864R | Especialista Seg RE |
| Douglas Silva | douglas.silva | U0A0AE52Q07 | Especialista Consórcios |
| Tereza Cristina | tereza.bernardo | U098F2S4GG4 | Especialista Consórcios |
| Sara Caetano | sara.caetano | U05HEK3N7RN | Backoffice Consórcios |
| Pedro Villarroel | (tbd) | U09S3CV4EN9 | Estagiário Performance |

### Atribuições sugeridas (Pedro confirma na hora de estender)

| Card | Gestor | Participantes | Líder Direto (escalação) |
|---|---|---|---|
| Consórcios N3 | Joel (U06RSGEH51R) | Douglas + Tereza + Sara | Bruno (U043D1ZF69L) |
| Seguros WL N3 | Joel (U06RSGEH51R) | Tarcisio + Cláudia | Bruno (U043D1ZF69L) |
| Seguros RE N3 | Joel (U06RSGEH51R) | Emmanuel + Samuel | Bruno (U043D1ZF69L) |
| Investimentos | Filipe (U0A35AVR5EJ) | (a definir) | Bruno (U043D1ZF69L) |

Pedro Villarroel (Estagiário) pode entrar como participante observador em qualquer Card — a confirmar.
