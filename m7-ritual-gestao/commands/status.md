---
description: Exibe o progresso do ciclo G2.3 (Ritual de Gestao) - materiais gerados, distribuicao Slack realizada, decisoes registradas + ata distribuida. Inclui pontualidade CP-04 do mes (3.8.0+).
argument-hint: [vertical] [subnivel]
---

# m7-ritual-gestao:status

Exibe o status do pipeline G2.3 para uma ou todas as verticais ativas.

> **3.8.0 (S4 2026-05-20):** mostra E3 (distribuicao pre-ritual via bot Slack) e sub-passo
> E5.distribuicao_ata como linhas separadas, com contador de DMs entregues e flag on_time.
> Tambem exibe pontualidade CP-04 do mes corrente (≥90% meta mensal).

## Input

- **vertical** (opcional): `$ARGUMENTS[0]` — nome da vertical em kebab-case. Se omitido, mostra todas as verticais com ciclo G2.3 ativo.
- **subnivel** (opcional): `$ARGUMENTS[1]` — quando a vertical tem split (ex: SEG `wl`/`re`).

## Steps

1. **Localizar CICLO.md** da vertical especificada: `Glob('02-Controle/**/{Vertical-cap}[-{subnivel}]/????-??/????-??-??/CICLO.md')` (o `**/` tolera o nivel level-first `N{N}/` e o legado; ignorar `_Historico/`).
   - Se vertical omitida, iterar todas as pastas filhas de `02-Controle/` (skip `_Historico/`) e pegar CICLO.md mais recente de cada uma com secao G2.3.
   - Se nenhum CICLO.md com secao G2.3 encontrado: exibir `"Nenhum ciclo G2.3 ativo. Aguardando WBR do m7-controle."` e parar.

2. **Extrair status G2.3** lendo a tabela de Progresso dentro da secao `## G2.3`:
   - Status de cada fase (E2, E3, E5)
   - Caminhos dos artefatos gerados
   - Log de Execucao — procurar linhas `preview gerado` (aguarda aprovacao) e `distribuicao_ata concluido` (sub-passo E5.7)

3. **Verificar existencia fisica dos artefatos** referenciados via Glob no `RITUAL_DIR` canonical (resolvido via `resolve_ritual_path.py`):
   - `{RITUAL_DIR}/apresentacao/ritual-{vertical}{-{sub}}-{data}.html`
   - `{RITUAL_DIR}/briefing/briefing-{vertical}{-{sub}}-{data}.html`
   - `{RITUAL_DIR}/ata/ata-ritual-{vertical}{-{sub}}-{data}.pdf`
   - `{RITUAL_DIR}/distribuicao/distribution-preview-{pre|post}_ritual.json`
   - Se artefato referenciado nao existe: marcar com alerta `"Artefato nao encontrado: {caminho}"`

4. **Verificar atualidade do WBR** usado como insumo:
   - Comparar a semana ISO do WBR fonte (registrado no CICLO.md) com a semana ISO atual.
   - Se WBR de semana anterior: adicionar aviso `"⚠️ WBR da semana anterior. Verifique /m7-controle:status"`

5. **Ler log de distribuicao Slack** (CP-04 dataset):
   - Path: `{DESEMPENHO_ROOT}/03-Rituais/distribuicao-log.csv`
   - Filtrar linhas do ciclo corrente (`cycle_date` + `vertical` + `subnivel`)
   - Extrair: `dms_count`, `on_time`, `escalacao_acionada` para pre e pos

6. **Calcular pontualidade CP-04 do mes corrente** (apenas quando comando sem filtro de vertical, ou ao final do bloco de uma vertical especifica):
   - Ler `distribuicao-log.csv` filtrando `dry_run=false` E `cycle_date` no mes atual
   - `pontualidade = sum(on_time=true) / count(*) * 100`
   - Status emoji: ✅ se ≥90%, ⚠️ se 75-89%, ❌ se <75%
   - Mostrar contagem detalhada (`{N_on_time}/{N_total} entregas no prazo`)

7. **Calcular progresso**: fases com status `concluido` / total (3 ou 4 com sub-passo) = percentual

8. **Exibir tabela formatada** por vertical:

```
Pipeline G2.3 - {Vertical}{ - {SUBNIVEL}} - {Periodo} (ciclo {YYYY-MM-DD})

| Fase | Skill                       | Status              | Artefato/Detalhe                                  |
|------|-----------------------------|---------------------|---------------------------------------------------|
| E2   | preparing-materials         | ✅ Concluido        | apresentacao + briefing                           |
| E3   | distributing-materials      | ✅ Concluido        | bot_slack_dm (4 DMs, on_time=true, prazo=D-1)     |
| E5   | recording-decisions         | ✅ Concluido        | ata MD/PDF + 7 tasks ClickUp                      |
| E5.7 | distributing-materials (pos)| ⬜ Preview gerado    | aguarda /approve-ata                              |

Progresso: 3/4 (75%)
Proximo: /m7-ritual-gestao:approve-ata {vertical}{ {sub}}

CP-04 mes corrente (Mai/2026):
✅ 6/6 entregas no prazo (100%)
```

9. **Sugerir proximo passo** com base no estado do pipeline:
   - Se E2 pendente: `/m7-ritual-gestao:next {vertical}{ {sub}}` (gerar materiais)
   - Se E2 concluido e E3 pendente: `/m7-ritual-gestao:next` (gera preview Slack) → `/approve-ritual`
   - Se E3 preview gerado mas nao concluido: `/m7-ritual-gestao:approve-ritual {vertical}{ {sub}}`
   - Se E3 concluido e E5 pendente: `"Apos o ritual, execute /m7-ritual-gestao:next {vertical}{ {sub}}"`
   - Se E5 commit ClickUp concluido mas sub-passo distribuicao_ata pendente: `/m7-ritual-gestao:next` (gera preview) → `/approve-ata`
   - Se E5.7 preview gerado: `/m7-ritual-gestao:approve-ata {vertical}{ {sub}}`
   - Se todas as fases concluidas (incl distribuicao_ata): `"Ciclo G2.3 concluido. Ata, acoes ClickUp e distribuicao Slack registradas."`

## Cenarios especiais

| Cenario | Output |
|---------|--------|
| Nenhum ciclo G2.3 ativo | `"Nenhum ciclo G2.3 ativo. Aguardando WBR do m7-controle."` |
| Materiais gerados (E2 concluido), E3 pendente | `"Execute /m7-ritual-gestao:next para gerar preview de distribuicao."` |
| E3 preview gerado, aguardando aprovacao | `"Execute /m7-ritual-gestao:approve-ritual para liberar envio Slack."` |
| Pipeline completo (incl distribuicao_ata) | `"Ciclo G2.3 concluido. Ata, acoes ClickUp e distribuicao Slack registradas."` |
| WBR desatualizado | `"⚠️ WBR da semana anterior. Verifique /m7-controle:status"` |
| Pontualidade CP-04 do mes <90% | Header de alerta `"⚠️ Pontualidade CP-04 abaixo da meta no mes"` antes da tabela |
| Multiplas verticais ativas (sem filtro) | Uma tabela por vertical/subnivel + bloco global CP-04 no fim |

## Output

Tabela Markdown formatada por vertical, com:
- Status das 4 linhas (E2 / E3 / E5 / E5.7)
- Detalhes de cada artefato + contagem de DMs entregues quando aplicavel
- Bloco CP-04 mes corrente (so quando vertical=todos OU bloco global no rodape)
- Sugestao do proximo comando
