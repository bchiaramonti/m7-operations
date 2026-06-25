# Message Templates — Regras de Renderização

Esta skill usa 2 templates em `templates/`:

- `pre-ritual-message.tmpl.md` — enviado em E3 (pré-ritual) **só para o coordenador/gestor da vertical**
- `post-ritual-message.tmpl.md` — enviado em E5.7 (pós-ritual, sub-passo de E5):
  - **Se `Canal-Vertical-ID` está preenchido no XLSX:** 1 envio coletivo no canal da vertical (post mais recente; bot precisa ser membro)
  - **Fallback (canal vazio):** DMs para gestor + participantes + líder direto (se escalação)

> **Regra de destinatários por modo (2026-05-20):**
> - Pré-ritual: deck/briefing são ferramentas do CONDUTOR — só gestor recebe. `slack_send.py::run_preview` zera `recipients["participantes"]` em `mode=pre_ritual`.
> - Pós-ritual: ata é colaborativa — canal da vertical (1 post) preferencialmente, com contramedidas agrupadas por responsável pra cada um identificar a sua. DMs como fallback enquanto não há canal.

Ambos são strings com placeholders `{nome}` substituídos via `str.format_map(defaultdict(str, ...))` em `slack_send.py::render_message()` (funções `_build_pre_ritual_body()` e `_build_post_ritual_body()` internas). Placeholders ausentes viram string vazia (não geram erro).

---

## Convenções

### Slack mrkdwn

Os templates usam **Slack mrkdwn** (não Markdown padrão). Diferenças relevantes:

| Sintaxe | Slack mrkdwn | Markdown padrão |
|---|---|---|
| Bold | `*texto*` | `**texto**` |
| Italic | `_texto_` | `*texto*` ou `_texto_` |
| Code inline | `` `texto` `` | `` `texto` `` |
| Quote | `> texto` | `> texto` |
| Emoji | `:smile:` (shortcode) | `:smile:` (depende do renderer) |
| Lista | `- item` | `- item` |
| Mention user | `<@U043D1ZF69L>` | n/a |
| Link | `<https://url\|label>` | `[label](url)` |

Como **Slack só renderiza mrkdwn quando o texto vai como `text` ou `initial_comment`**, e nós usamos `initial_comment` no `files_completeUploadExternal`, o template é compatível.

### Quebra de linha

Slack mrkdwn requer **duas quebras de linha** entre parágrafos. Os templates usam `\n\n` literal entre blocos.

### Emojis

Os shortcodes usados nos templates devem existir na workspace M7. Os padrão do Slack são sempre seguros:

- `:white_check_mark:` ✅ (CTA de confirmação de leitura)
- `:red_circle:` 🔴 / `:large_yellow_circle:` 🟡 / `:large_green_circle:` 🟢 / `:white_circle:` ⚪ (semáforo)
- `:bar_chart:` 📊 (pré-ritual)
- `:memo:` 📝 (pós-ritual)
- `:warning:` ⚠️ (escalação)

---

## Pré-ritual — `pre-ritual-message.tmpl.md`

### Placeholders (atualizado 2026-05-20 — versão clean)

| Nome | Tipo | Fonte | Exemplo |
|---|---|---|---|
| `{subject}` | str | `slack_send.build_subject()` | Ritual Consorcios N3 S21 |
| `{cadencia_label}` | str | `slack_send.cadencia_label()` | N3 (Operacional) |
| `{sem_vermelho}` | int | `wbr.semaforo_resumo.vermelho` | 4 |
| `{sem_amarelo}` | int | `wbr.semaforo_resumo.amarelo` | 1 |
| `{sem_verde}` | int | `wbr.semaforo_resumo.verde` | 4 |
| `{sem_cinza_block}` | str | bloco opcional " \| ⚪ N (sem meta)" se cinza > 0 | ` | :white_circle: 1 (sem meta)` |
| `{checkpoint_label}` | str | `wbr.checkpoint_label` (top-level) ou `wbr.meta.ciclo_label` | Maio 2026, semana 4 (MTD) |
| `{n_top_desvios}` | int | min(N_top, count(desvios)) | 3 |
| `{desvios_bullets}` | str (multi-linha) | Top N por gap absoluto, vermelhos primeiro | - 🔴 **Vol Cons Mensal**: 68,0% (-R$5,28M) — Concentração 100% Douglas... |
| `{deck_size_kb}` | int | `deck_path.stat().st_size / 1024` | 3467 |
| `{briefing_size_kb}` | int | `briefing_path.stat().st_size / 1024` | 18 |

> **Removidos em 2026-05-20** (decisão do usuário — mensagem clean, sem tech case):
> - `{card_label}` — irrelevante pro destinatário; deck/briefing já identificam o ritual via subject
> - `{pa_bullets}` — informação redundante; gestor consulta status do Plano de Ação no ClickUp diretamente

### Regras de bullets

- **Top desvios**: até 3 indicadores (configurável via `--top-desvios`), priorizados por status (vermelho > amarelo > resto) e depois por |gap_pct|.
- **Causa_raiz_resumo** truncada em 140 chars com `...` no final.

### Exemplo renderizado

Ver `examples/sample-pre-ritual-message.md`.

---

## Pós-ritual — `post-ritual-message.tmpl.md`

### Placeholders

| Nome | Tipo | Fonte | Exemplo |
|---|---|---|---|
| `{subject}` | str | `iso_week.build_subject(mode="post_ritual")` | Ata Ritual Consorcios N3 S21 |
| `{cadencia_label}` | str | igual ao pré | N3 (Operacional) - WL |
| `{data_ritual_label}` | str | `--ciclo-date` | 2026-05-19 |
| `{contramedidas_block}` | str (multi-linha) | `_render_contramedidas_por_responsavel()` — agrupa contramedidas novas do `plan-preview.json` por `Responsavel Externo` (custom_fields). Cada grupo `*Para {nome}:*` com bullets `  - {titulo} ({prioridade} · DD/MM)`. Tasks atualizadas viram linha curta agregada `_Tasks anteriores atualizadas: N_` quando houver. | `*Para Pedro Villarroel:*\n  - Corrigir flag banco... (alta · 20/05)\n\n*Para Tarcisio e Claudia:*\n  - Manter cadencia... (alta · 30/05)` |
| `{n_novas}` | int (debug only) | length de `contramedidas_novas[]` | 3 |
| `{n_atualizadas}` | int (debug only) | length de `tasks_atualizadas[]` | 0 |
| `{escalacao_block}` | str | bloco "⚠️ Escalação acionada" se YAML flag true | `\n- :warning: *Escalacao acionada* — copia enviada ao lider direto` |
| `{ata_md_line}` | str | `\n- Ata em Markdown` se `--include-md-anexo` | `\n- Ata em Markdown (para edicao/revisao)` |

### Regras

- **Contramedidas**: **listadas individualmente, agrupadas por responsável** (decisão 2026-05-20 v3: como vai pro canal coletivo, cada participante precisa identificar quais ações são dele). Sem mention `<@>` — só nome simples ("Para Tarcisio e Claudia:").
- **Decisões**: NÃO entram no template (decisão 2026-05-20). Ficam só na ata.
- **scope_task_ids** lido do bloco YAML embedado na ata (usado em debug/auditoria, não na mensagem).
- **Escalação**: flag `escalacao_acionada: true` no YAML block da ata MD ativa o bloco extra.

### Exemplo renderizado (versão clean 2026-05-20)

```
:memo: *Ata Ritual Consorcios N3 S21*
N3 (Operacional) | Ritual realizado em 2026-05-19

*Contramedidas no Plano de Ação:*
- 4 nova(s) criada(s)
- 2 existente(s) atualizada(s)

*Anexos:*
- Ata em PDF

_Reaja com :white_check_mark: para confirmar leitura._
```

> **Removidos em 2026-05-20** (decisão do usuário):
> - Seção "Decisões registradas" — força o destinatário a abrir a ata PDF pra ver detalhes
> - Referência "ClickUp `pa-resultado`" — tech case (ver [feedback_clickup_invisible_to_humans](../../../../../../../../.claude/projects/c--Users-pedro-OneDrive---MULTI7-CAPITAL-CONSULTORIA-LTDA-claude-plugins/memory/feedback_clickup_invisible_to_humans.md))

---

## Customização futura (fora do escopo Phase 1)

- **Por vertical**: hoje o template é único. Se Investimentos precisar de bullets adicionais (ex: NPS, churn), criar `pre-ritual-message-investimentos.tmpl.md` e selecionar por `args.vertical` em `slack_send.py::_load_template()`.
- **Por idioma**: hoje só PT-BR.
- **Por nível**: hoje N2 e N3 compartilham template; N2 mensal pode querer comparativo MoM mais elaborado.

Adições devem manter o **footer de CTA** ("Reaja com ✅") para CP-04.
