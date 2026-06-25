# Delivery Log Schema — `distribuicao-log.csv`

Arquivo CSV append-only escrito pelo `slack_send.py --phase commit`. **Fonte primária do KPI CP-04** (≥90% pontualidade mensal).

---

## Localização

```
desempenho/03-Rituais/distribuicao-log.csv
```

Compartilhado entre todas as verticais — uma linha por envio (pré ou pós-ritual, real ou dry-run).

---

## Schema (13 colunas)

| # | Coluna | Tipo | Exemplo | Observações |
|---|---|---|---|---|
| 1 | `timestamp` | ISO 8601 com TZ | `2026-05-19T08:08:43-03:00` | Quando o envio completou |
| 2 | `vertical` | str lowercase | `consorcios` | Mesma string usada em commands |
| 3 | `nivel` | str | `N3` | N1/N2/N3 |
| 4 | `subnivel` | str | `wl` ou `` | Vazio quando vertical não-split |
| 5 | `cycle_date` | YYYY-MM-DD | `2026-05-19` | Data do ciclo (`--ciclo-date`) |
| 6 | `semana_iso` | int | `21` | ISO week number |
| 7 | `tipo` | str | `pre` ou `pos` | `pre_ritual` → `pre`, `post_ritual` → `pos` |
| 8 | `dms_count` | int | `4` | DMs entregues com sucesso (não tentativas) |
| 9 | `on_time` | str | `true` ou `false` | RN-09: dentro do prazo D-1 (N3) ou D-3 (N2)? |
| 10 | `prazo_referencia` | str | `D-1` | Para auditoria do cálculo on_time |
| 11 | `confirmacoes_leitura_count` | int | `0` | Inicial sempre 0; populado por feature futura (reactions:read) |
| 12 | `escalacao_acionada` | str | `true` ou `false` | Houve envio adicional ao líder direto? |
| 13 | `dry_run` | str | `true` ou `false` | Linha gerada por simulação ou execução real? |

---

## Exemplo de linha real

```csv
2026-05-19T08:08:43-03:00,consorcios,N3,,2026-05-19,21,pre,4,true,D-1,0,false,false
```

Decodificada:
- 2026-05-19 08:08:43 (UTC-3)
- Vertical Consórcios, N3, sem subnivel
- Ciclo de 2026-05-19, semana ISO 21
- Pré-ritual, 4 DMs entregues
- Dentro do prazo D-1
- 0 confirmações de leitura ainda (será atualizado depois pela skill de reactions)
- Sem escalação
- Envio real (não dry-run)

---

## Exemplo de linha dry-run

```csv
2026-05-19T15:30:11-03:00,seguros,N3,wl,2026-05-22,21,pos,5,true,D-1,0,true,true
```

Decodificada:
- Modo `--dry-run` ativo (`dry_run=true`)
- Subnivel `wl` preenchido
- Pós-ritual com escalação acionada (5 DMs incluindo líder direto)

---

## Comportamento append-only

- Cada `slack_send.py --phase commit` adiciona exatamente **uma linha**.
- Re-execução do commit (ex: reaprovação após edição) cria **nova linha** com mesmo `cycle_date` — downstream KPI considera só a entrega mais recente por `(vertical, nivel, subnivel, cycle_date, tipo)`.
- Header escrito automaticamente na primeira escrita (arquivo vazio ou inexistente).
- Newline padronizado `\n` (Python `lineterminator="\n"`).
- Encoding UTF-8 sem BOM.

---

## Consumo pelo KPI CP-04 (futuro)

Uma skill futura `reporting-distribution-kpi` consumirá este CSV:

```python
import pandas as pd
df = pd.read_csv("desempenho/03-Rituais/distribuicao-log.csv")
df = df[df["dry_run"] == "false"]  # excluir testes
df_mes = df[df["cycle_date"].str.startswith("2026-05")]

# Pontualidade do mes
pontuais = (df_mes["on_time"] == "true").sum()
total = len(df_mes)
pct = pontuais / total * 100 if total else 0.0
print(f"CP-04: {pct:.1f}% (meta 90%)")
```

A skill futura também produzirá breakdown por vertical/nivel + tendência MoM.

---

## Auditoria

Cada linha aponta para um envio rastreável:

- `cycle_date` + `vertical` + `tipo` → CICLO.md correspondente em `02-Controle/N{N}/{Vertical-cap}[-{subnivel}]/{YYYY-MM}/{cycle_date}/CICLO.md` (level-first, default ON 2026-06-09; ex: `N3/Seguros-wl/2026-05/2026-05-27/CICLO.md`). Use `**/` no Glob para tolerar tambem o layout legado sem `N{N}/`.
- `timestamp` → bate com `ts` retornado pelo Slack na resposta do `completeUploadExternal` (registrado no CICLO.md log)
- `dms_count` → bate com `len(deliveries[ok=true])` no JSON de retorno do slack_send.py

Discrepâncias indicam corrupção do log; investigar antes de gerar KPI.

---

## Rotação / arquivamento

Phase 1 não inclui rotação. Após 6+ meses, linhas podem ser arquivadas em `distribuicao-log-archive-{YYYY}.csv` para manter o arquivo principal performante.

Hoje, mesmo com 4 verticais × 2 envios/semana × 52 semanas = 416 linhas/ano. CSV cresce <100KB/ano. Sem urgência.
