---
description: Avanca o pipeline G2.3 para a proxima fase pendente. Le CICLO.md (secao G2.3), identifica a proxima fase com status "pendente", verifica entry criteria e invoca a skill correspondente. Em 3.8.0+ branchea automaticamente em E3 (distribuicao pre-ritual via bot Slack) e no sub-passo de distribuicao da ata pos E5.
argument-hint: [vertical] [subnivel]
---

# m7-ritual-gestao:next

Avanca o pipeline G2.3 (Ritual de Gestao) para a proxima fase pendente de uma vertical.

> **3.8.0 (S4 2026-05-20):** o command agora orquestra E3 e o sub-passo E5.distribuicao-ata
> via bot Slack `m7-desempenho`. Gate humano preview→commit preservado: o `/next` invoca
> `distributing-materials` em modo `preview` e devolve o controle ao usuario, que confirma
> com `/m7-ritual-gestao:approve-ritual` (E3) ou `/m7-ritual-gestao:approve-ata` (E5.7).

## Input

- **vertical** (opcional): `$ARGUMENTS[0]` — nome da vertical em kebab-case (ex: `investimentos`, `consorcios`). Se omitido, usa a ultima vertical ativa registrada no CICLO.md mais recente.
- **subnivel** (condicional): `$ARGUMENTS[1]` — obrigatorio quando a vertical tem 2+ cards com `metadata.subnivel` distinto (ex: SEG `wl`/`re`). Logica identica a `/m7-ritual-gestao:prepare-ritual` Step 1.5.

## Steps

1. **Localizar CICLO.md** do Card: `Glob('02-Controle/**/{Vertical-cap}[-{subnivel}]/????-??/????-??-??/CICLO.md')` — o `**/` tolera o segmento de nivel level-first (`N{N}/`) quando ativo e o layout legado quando OFF; ignorar matches em `_Historico/`; selecionar o mais recente.
   - Se nao encontrado: exibir `"CICLO.md nao encontrado para {vertical}{ {subnivel}}. Execute /m7-controle:run-weekly antes."` e parar.

2. **Localizar ou criar secao G2.3** no CICLO.md.
   - Buscar a secao `## G2.3 - Ritual de Gestao`.
   - Se nao existir, criar com a tabela Progresso inicial:

     ```markdown
     ## G2.3 - Ritual de Gestao

     | Fase | Skill | Status | Inicio | Fim | Artefato |
     |------|-------|--------|--------|-----|----------|
     | E2{FASE_SUFIXO} | preparing-materials | pendente | -- | -- | -- |
     | E3{FASE_SUFIXO} | distributing-materials | pendente | -- | -- | -- |
     | E5{FASE_SUFIXO} | recording-decisions | pendente | -- | -- | -- |
     ```

   - `FASE_SUFIXO` = ` {SUBNIVEL_ATIVO}` quando subnivel passado, vazio caso contrario.

3. **Identificar proxima fase pendente** lendo a tabela Progresso da secao G2.3. A ordem fixa:
   - E2 → E3 → E5 (com sub-passo distribuicao-ata embutido em E5)
   - Selecionar a primeira fase com status `pendente`. Em E5, verificar ainda se o sub-passo `distribuicao_ata` foi concluido (procurar no Log de Execucao a linha `distribuicao_ata concluido`).

4. **Verificar entry criteria** da fase identificada:

   | Fase | Entry Criteria |
   |------|---------------|
   | E2 | WBR concluido: G2.2 E6 do mesmo CICLO.md com status `concluido` |
   | E3 | E2 concluido; Calendario-de-Rituais.xlsx estendido (Gestor-User-ID etc); `SLACK_BOT_TOKEN` disponivel |
   | E5 | E3 concluido; ritual realizado (confirmacao explicita do usuario) |
   | E5.distribuicao_ata | E5 commit ClickUp concluido; ata MD/PDF gerada |

   - Se entry criteria nao atendido, exibir mensagem clara apontando o passo anterior + parar.

5. **Registrar inicio no CICLO.md** (secao G2.3):
   - Atualizar tabela Progresso: `status: em_andamento`, `inicio: {timestamp}`
   - Append ao **Log de Execucao**: `[{timestamp}] SISTEMA — Iniciando fase {fase}{FASE_SUFIXO} ({skill})`

6. **Invocar a skill correspondente**:

   > **Regra arquitetural:** O command invoca **skills**, nunca agents diretamente. A skill decide internamente se executa no main thread ou delega a um agente.

   | Fase | Skill | Modo |
   |------|-------|------|
   | E2 | preparing-materials | direto |
   | E3 | distributing-materials | mode=preview (gate humano) |
   | E5 | recording-decisions | mode=preview (gate humano) |
   | E5.distribuicao_ata | distributing-materials | mode=preview pos_ritual (gate humano) |

   - **Para E2:** invocar `preparing-materials` com `vertical`, `subnivel`, `card_path`, paths do WBR + output. Ao final, sugerir `/m7-ritual-gestao:next {vertical}{ {sub}}` para avancar a E3.

   - **Para E3:** invocar `distributing-materials` em `phase=preview mode=pre_ritual`:
     - Mesma logica do `/m7-ritual-gestao:approve-ritual` Steps 2.5/3 (resolve RITUAL_DIR, localiza WBR data JSON via `resolve_controle_path.py`, valida calendar)
     - Renderiza mensagem + JSON preview em `{RITUAL_DIR}/distribuicao/distribution-preview-pre_ritual.json`
     - Exibe sumario no chat (subject + recipients_count + body_preview + on_time)
     - **PARA aqui.** Instruir o usuario:
       ```
       Preview de distribuicao pre-ritual gerado.
       Revise acima e execute:
         /m7-ritual-gestao:approve-ritual {vertical}{ {subnivel}}
       para liberar o envio via DM Slack (ou regenere com /next apos ajuste).
       ```

   - **Para E5:** invocar `recording-decisions` mode=preview (fluxo existente). Apos commit ClickUp completar, registrar no Log `[ts] SISTEMA — E5 commit concluido. Proximo: sub-passo distribuicao_ata via /next.`

   - **Para E5.distribuicao_ata (NOVO sub-passo):** quando E5 ja `concluido` mas Log nao tem `distribuicao_ata concluido`, invocar `distributing-materials` em `phase=preview mode=post_ritual` (le ata MD/PDF + plan-preview JSON; preview salvo em `{RITUAL_DIR}/distribuicao/distribution-preview-post_ritual.json`). Instruir:
     ```
     Preview de distribuicao da ata gerado.
     Revise acima e execute:
       /m7-ritual-gestao:approve-ata {vertical}{ {subnivel}}
     para liberar o envio via DM Slack.
     ```

7. **Atualizar CICLO.md** apos execucao bem-sucedida (so se a skill alcancou estado final; previews E3/E5.distribuicao_ata NAO marcam como concluido — esperam aprovacao em `/approve-*`):
   - **E2:** tabela Progresso = `concluido`, `fim`, `artefato`. Log append.
   - **E3 preview:** NAO marcar como concluido. Apenas Log: `[ts] SISTEMA — E3{FASE_SUFIXO} preview gerado. Aguardando /approve-ritual.`
   - **E5 commit ClickUp:** tabela Progresso = `concluido`, `fim`, `artefato` (ata MD path). Log append. (Sub-passo distribuicao_ata = separado.)
   - **E5.distribuicao_ata preview:** NAO marcar como concluido. Log: `[ts] SISTEMA — E5{FASE_SUFIXO} sub-passo distribuicao_ata preview gerado. Aguardando /approve-ata.`
   - **Se skill falhar:** tabela `erro`, Anomalias append, sugerir retry.

   > O status `concluido` final de E3 e E5.distribuicao_ata sera escrito pelos commands `/approve-ritual` e `/approve-ata` quando o commit Slack rodar (mesmo padrao 2-fase do recording-decisions ClickUp).

8. **Exibir resultado** ao usuario com:
   - Fase executada e tempo decorrido
   - Caminho dos artefatos gerados / preview salvo
   - Proxima acao sugerida: comando de aprovacao (se preview) ou `/next` (se fase concluida)

## Tratamento de erros

| Cenario | Acao |
|---------|------|
| CICLO.md nao encontrado | Exibir mensagem instruindo `/m7-controle:run-weekly` antes |
| WBR nao disponivel para E2 | Exibir: `"WBR nao encontrado. Execute /m7-controle:run-weekly {vertical}{ {subnivel}} primeiro."` |
| Calendario sem linha p/ vertical+nivel em E3 | Apontar `calendar-schema.md` para preencher antes |
| `SLACK_BOT_TOKEN` ausente em E3 ou E5.distribuicao_ata | Apontar `~/.claude/credentials/.env` |
| Validacao RN-07 falha em E3/E5.7 preview | Listar quais dos 4 elementos faltam (corrigir WBR/ata antes) |
| Ritual nao confirmado para E5 | Exibir: `"Confirme que o ritual foi realizado para prosseguir."` e aguardar |
| Todas as fases concluidas | Exibir: `"Pipeline G2.3 concluido para {vertical}{ {subnivel}} no ciclo {data}."` |
| Skill falha | Registrar erro em Anomalias + Log; sugerir retry |

## Output

Exibir ao usuario:

```
Executando fase {fase}{FASE_SUFIXO} ({skill}{ mode=...}) para {vertical}{ {subnivel}}...
Entry criteria: {descricao}

[... execucao da skill ...]

{Se preview E3 ou E5.distribuicao_ata}
Preview gerado em {RITUAL_DIR}/distribuicao/distribution-preview-{mode}.json
Proximo: /m7-ritual-gestao:approve-{ritual|ata} {vertical}{ {subnivel}}

{Se concluido}
{fase} concluida em {duracao}
Artefatos: {paths}
Proximo: /m7-ritual-gestao:next {vertical}{ {subnivel}} ({proxima-fase}: {proxima-skill})
```

Quando pipeline completo:

```
Pipeline G2.3 concluido para {vertical}{ {subnivel}} no ciclo {data}.
```
