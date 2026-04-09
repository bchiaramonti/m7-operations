---
description: Avanca o pipeline G2.3 para a proxima fase pendente. Le CICLO.md (secao G2.3), identifica a proxima fase com status "pendente", verifica entry criteria e invoca a skill correspondente.
argument-hint: [vertical]
---

# m7-ritual-gestao:next

Avanca o pipeline G2.3 (Ritual de Gestao) para a proxima fase pendente de uma vertical.

## Input

- **vertical** (opcional): `$ARGUMENTS[0]` — nome da vertical em kebab-case (ex: `investimentos`, `consorcios`). Se omitido, usa a ultima vertical ativa registrada no CICLO.md mais recente.

## Steps

1. **Localizar CICLO.md** da vertical no diretorio de trabalho, buscando em `{vertical}/????-??-??/CICLO.md`.
   - Se nao encontrado: exibir `"CICLO.md nao encontrado para {vertical}. Execute /m7-controle:run-weekly {vertical} primeiro."` e parar.

2. **Localizar ou criar secao G2.3** no CICLO.md.
   - Buscar a secao `## G2.3 - Ritual de Gestao`.
   - Se nao existir, criar a secao com a tabela Progresso inicial:

     ```markdown
     ## G2.3 - Ritual de Gestao

     | Fase | Skill | Status | Inicio | Fim | Artefato |
     |------|-------|--------|--------|-----|----------|
     | E2   | preparing-materials | pendente | -- | -- | -- |
     | E3   | (distribuicao manual) | pendente | -- | -- | -- |
     | E5   | recording-decisions | pendente | -- | -- | -- |
     ```

3. **Identificar proxima fase pendente** lendo a tabela Progresso da secao G2.3. A ordem de execucao e fixa:
   - E2 → E3 (manual) → E5
   - E3 e uma etapa manual (distribuicao de materiais ao gestor por e-mail). O command `/next` NAO executa E3 — apenas verifica se o usuario ja a marcou como `enviado` antes de prosseguir para E5.
   - Selecionar a primeira fase com status `pendente`.

4. **Verificar entry criteria** da fase identificada:

   | Fase | Entry Criteria |
   |------|---------------|
   | E2 | WBR concluido: secao G2.2 do mesmo CICLO.md tem E6 com status `concluido` |
   | E3 | E2 concluido. Etapa manual — exibir: `"Materiais prontos. Distribua ao gestor e marque como enviado."` e parar. |
   | E5 | E3 marcado como `enviado` + ritual realizado: confirmacao explicita do usuario |

   - Se entry criteria nao atendido:
     - E2: exibir `"WBR nao encontrado. Execute /m7-controle:run-weekly {vertical} primeiro."` e parar.
     - E5: exibir `"Confirme que o ritual foi realizado para prosseguir com o registro de decisoes."` e aguardar confirmacao do usuario.

5. **Registrar inicio no CICLO.md** (secao G2.3):
   - Atualizar tabela Progresso: `status: em_andamento`, `inicio: {timestamp}`
   - Append ao **Log de Execucao**: `[{timestamp}] SISTEMA — Iniciando fase {fase} ({skill})`

6. **Invocar a skill correspondente**:

   > **Regra arquitetural**: O command invoca **skills**, nunca agents diretamente. A skill decide internamente se executa no main thread ou delega a um agente.

   | Fase | Skill |
   |------|-------|
   | E2 | preparing-materials |
   | E3 | (manual — nao invoca skill) |
   | E5 | recording-decisions |

   Contexto disponivel para a skill: vertical, periodo, caminho da pasta do ciclo, artefatos de G2.2 (WBR, dados consolidados), e artefatos anteriores de G2.3.

7. **Fluxo especial para E5** (apenas quando fase executada = E5):
   - Apos confirmacao do ritual (step 4), solicitar ao usuario as notas do ritual (texto livre ou estruturado).
   - Invocar a skill `recording-decisions` com as notas como input.
   - A skill (via decision-recorder agent) gera a ata estruturada.
   - Apresentar ata ao usuario para confirmacao.
   - Apos confirmacao, registrar contramedidas no `plano-de-acao.csv`.
   - Se usuario rejeitar a ata: permitir ajustes e re-apresentar.

8. **Atualizar CICLO.md** (secao G2.3) apos execucao:
   - Tabela Progresso: `status: concluido`, `fim: {timestamp}`, `artefato: {caminho}`
   - Append ao **Log de Execucao**: `[{timestamp}] AGENTE:{agent} — Fase {fase} concluida. Artefato: {caminho}`
   - Se a skill falhar:
     - Tabela Progresso: `status: erro`, `fim: {timestamp}`
     - Append a **Anomalias**: `[{timestamp}] SISTEMA — ERRO em {fase}: {detalhes}`
     - Sugerir retry com `/m7-ritual-gestao:next {vertical}`

9. **Exibir resultado** ao usuario com:
   - Fase executada e duracao
   - Caminho dos artefatos gerados (relativo a pasta do ciclo)
   - Proxima fase sugerida (ou mensagem de pipeline concluido)

## Tratamento de erros

| Cenario | Acao |
|---------|------|
| CICLO.md nao encontrado | Exibir: `"CICLO.md nao encontrado para {vertical}. Execute /m7-controle:run-weekly {vertical} primeiro."` |
| WBR nao disponivel para E2 | Exibir: `"WBR nao encontrado. Execute /m7-controle:run-weekly {vertical} primeiro."` |
| Ritual nao confirmado para E5 | Exibir: `"Confirme que o ritual foi realizado para prosseguir com o registro de decisoes."` |
| Todas as fases concluidas | Exibir: `"Pipeline G2.3 concluido para {vertical} nesta semana."` |
| Skill falha durante execucao | Registrar erro no CICLO.md (Anomalias + Log), exibir detalhes e sugerir retry |

## Output

Exibir ao usuario:

```
Executando fase {fase} ({skill}) para {vertical}...
Agent: {agent}
Entry criteria: {descricao}

[... execucao da skill ...]

✅ {fase} concluida em {duracao}
- Artefatos: {vertical}/{YYYY-MM-DD}/{caminho-artefato}
Proximo: /m7-ritual-gestao:next {vertical} ({proxima-fase}: {proxima-skill})
```

Quando pipeline completo:

```
✅ Pipeline G2.3 concluido para {vertical} nesta semana.
```
