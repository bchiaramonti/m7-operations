# CICLO.md G2.3 — Extensão de Schema para Distribuição

A linha **E3** já existe em CICLO.md hoje (gerada por `preparing-materials` quando E2 conclui), mas com `(distribuicao manual) | pendente`. Esta skill ativa E3 e adiciona sub-campo de distribuição da ata na linha E5.

---

## Estado Atual (sem distributing-materials)

```markdown
## G2.3 - Ritual de Gestao

| Fase | Skill | Status | Inicio | Fim | Artefato |
|------|-------|--------|--------|-----|----------|
| E2 | preparing-materials | concluido | 2026-05-19T08:00 | 2026-05-19T08:05 | output/consorcios/ritual-consorcios-2026-05-19.html + briefing-consorcios-2026-05-19.md |
| E3 | (distribuicao manual) | pendente | -- | -- | -- |
| E5 | recording-decisions | pendente | -- | -- | -- |
```

---

## Estado Alvo (com distributing-materials ativada)

### Modo `pre_ritual` (E3)

Após `commit` bem-sucedido, a linha E3 vira:

```markdown
| E3 | distributing-materials | concluido | 2026-05-19T08:07 | 2026-05-19T08:08 | bot_slack_dm (4 destinatarios, on_time=true, prazo=D-1) |
```

Adicionalmente, no **Log de Execução** do CICLO.md:

```
[2026-05-19T08:07] SISTEMA — Iniciando G2.3 E3 (distributing-materials) para consorcios mode=pre_ritual
[2026-05-19T08:08] AGENTE:slack_send.py — G2.3 E3 concluido. 4 DMs entregues no Slack. on_time=true. Subject: Ritual Consorcios N3 S21
```

### Modo `post_ritual` (E5 sub-passo de distribuição)

A linha E5 **não é alterada** (mantém `concluido` se o ClickUp commit deu certo). O sub-passo adiciona apenas linhas no Log de Execução:

```
[2026-05-19T15:00] SISTEMA — Iniciando G2.3 E5 sub-passo distribuicao_ata (distributing-materials) para consorcios mode=post_ritual
[2026-05-19T15:01] AGENTE:slack_send.py — G2.3 E5 distribuicao_ata concluido. 5 DMs entregues (incl. lider direto). escalacao_acionada=true. Subject: Ata Ritual Consorcios N3 S21
```

---

## Sufixo de subnivel

Quando a vertical tem split (ex: Seg WL/RE), a linha é `E3 wl` / `E3 re` (separadas), igual ao pattern já em uso para E2/E5.

---

## Campos do `Artefato` na linha E3 (formato literal)

```
bot_slack_dm (<N> destinatarios, on_time=<bool>, prazo=<D-N>)
```

Onde:
- `<N>` = `dms_count_ok` retornado pelo `slack_send.py --phase commit`
- `<bool>` = `true` ou `false` (computado por `compute_on_time`)
- `<D-N>` = `D-1` (N3 semanal) ou `D-3` (N2 mensal)

Se houve entregas parciais (alguns DMs falharam), o sufixo vira:

```
bot_slack_dm (3/4 destinatarios, on_time=true, prazo=D-1, 1 falha=user_not_visible)
```

---

## Tratamento de re-execução

Se `commit` é executado duas vezes (ex: usuário pediu reaprovação após edição), a linha E3 ganha **comma-separated artifacts**:

```
bot_slack_dm (4 destinatarios, on_time=true) + bot_slack_dm (4 destinatarios, on_time=true, re-envio)
```

E o Log de Execução registra ambos os timestamps.

---

## Anomalias (seção do CICLO.md)

Falhas parciais ou totais geram entrada na seção `## Anomalias`:

```
[2026-05-19T08:08] SISTEMA — G2.3 E3 entregas parciais: 3/4 DMs OK. Falha: Tereza Bernardo (U098F2S4GG4) — user_not_visible. Acao sugerida: verificar status da conta no workspace M7.
```

---

## Implementação no slack_send.py

A função `update_ciclo_md()` em `slack_send.py` (Phase 1) **NÃO está implementada na primeira iteração** — quem orquestra é o command `approve-ritual` / `approve-ata`, que após receber o JSON de retorno do slack_send.py:

1. Lê o CICLO.md mais recente da vertical
2. Localiza a linha `E3{FASE_SUFIXO}` (ou cria se ausente)
3. Atualiza status/inicio/fim/artefato conforme retorno
4. Append no Log de Execução
5. Se houve falha parcial, append em Anomalias

Esse padrão é consistente com o que `prepare-ritual` e `record-decisions` já fazem hoje.
