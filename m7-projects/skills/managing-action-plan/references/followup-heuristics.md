# Followup Heuristics

Regras de deteccao + formulacoes de pergunta usadas por `followup.py`
quando o usuario pede "o que esta atrasado / o que precisa de atencao".

## Categorias detectadas

| Categoria | Condicao | Pergunta tipica |
|---|---|---|
| `overdue` | `fim_plan < hoje` AND `status != done` | "Venceu em X (N dias atraso). Andamento? (atualizar status / mover data / comentar / skip)" |
| `upcoming` | `hoje <= fim_plan <= hoje + lookahead_days` AND `status != done` | "Vence em X (N dias). Vai entregar a tempo? Algum bloqueio?" |
| `stagnated` | `status == in_progress` AND `fim_plan - hoje > 14 dias` AND `fim_real == ""` | "Esta in_progress sem update. Andamento?" |
| `unstarted` | `inicio_plan <= hoje` AND `status == not_started` | "Deveria ter comecado em X (N dias atras). Iniciar agora? Reagendar? Bloqueado?" |

## Filtros automaticos

Aplicados antes da categorizacao (em `followup.py`):

- **Skip `Tipo == Fase`** — Fases sao agregadores, nao tem status proprio significativo. Override com `--include-fases`.
- **Skip `status == done`** — fechado e fechado.
- **Skip linhas sem `fim_plan`** para `overdue` / `upcoming` / `stagnated`. Linha sem prazo nao pode estar atrasada por definicao.
- **Skip linhas sem `inicio_plan`** para `unstarted`.

## Parametros de tuning

```bash
followup.py --file 4-status-report/Cronograma.xlsx \\
    --reference-date 2026-04-18 \\
    --lookahead-days 7 \\
    --include-fases
```

- `--reference-date` (default: hoje) — util para "o que estava atrasado em uma data X"
- `--lookahead-days` (default: 3) — janela `upcoming`. Para WBR mensal, use 14 ou 21
- `--include-fases` — inclui Fases na deteccao (raramente util)

`STAGNATION_DAYS` em `followup.py` (default 14) define o que conta como "due distante" para detectar stagnated. Hardcoded por agora; ajustar no script se necessario.

## Como a skill deve usar o output

`followup.py` devolve `categories` + `suggested_questions`. A skill
(via Claude) deve:

1. Mostrar **resumo** primeiro: "Detectei N atrasadas, M proximas, K estagnadas, J nao iniciadas"
2. Perguntar **uma a uma**, comecando por `overdue` (mais critico)
3. Para cada resposta do usuario, mapear para uma operacao:
   - "atualizei o status" → `actions.py update --field status --value ...`
   - "movi a data" → `actions.py update --field fim_plan --value ...`
   - "comentei" → `actions.py comment --no ... --text "..." --clickup-id ...`
   - "skip" → noop, proxima pergunta
4. Apos terminar (ou usuario dizer "para"), oferece sumario do que foi feito

## Anti-patterns

- **Despejar todas as perguntas de uma vez:** sobrecarga cognitiva. Pergunta a pergunta, mesmo que sejam 50.
- **Forcar resposta:** "skip" sempre disponivel.
- **Aplicar update sem confirmar valor:** se usuario diz "movi para semana que vem", confirmar a data exata antes de gravar.
- **Esquecer de logar:** toda decisao do followup gera entry no changelog (uma por operacao).

## Calibragem por audiencia

- **Auto-followup diario (Bruno revisando proprio plano):** lookahead 3, no-skip de pergunta confortavel
- **Antes de WBR semanal:** lookahead 7-14, modo "review completo"
- **Antes de status report mensal:** lookahead 30, gera relatorio agrupado por categoria, nao 1-a-1

A skill nao implementa esses modos automaticamente — mas o Claude pode escolher chamar `followup.py` com diferentes `--lookahead-days` baseado no contexto da conversa.
