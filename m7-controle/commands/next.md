---
description: Avanca o pipeline G2.2 para a proxima fase pendente. Le CICLO.md, identifica a proxima fase com status "pendente", verifica entry criteria e invoca a skill correspondente via agent correto.
argument-hint: [vertical]
---

# m7-controle:next

Avanca o pipeline G2.2 para a proxima fase pendente de uma vertical.

## Input

- **vertical** (opcional): `$ARGUMENTS[0]` — nome da vertical em kebab-case. Se omitido, usa a ultima vertical ativa registrada no CICLO.md mais recente.

## Steps

1. **Localizar CICLO.md** da vertical no diretorio de trabalho, buscando em `{vertical}/????-??-??/CICLO.md`.
   - Se nao encontrado, criar novo ciclo para a data atual (YYYY-MM-DD) usando o template padrao (incluindo criacao da estrutura de pastas).

2. **Identificar proxima fase pendente** lendo a tabela Progresso do CICLO.md. A ordem de execucao e fixa:
   - E2 → E3 → E4 → E5 → E6
   - Selecionar a primeira fase com status `pendente`.

3. **Verificar entry criteria** da fase identificada:

   | Fase | Entry Criteria |
   |------|---------------|
   | E2 | Cards YAML da vertical existem; ambiente Python configurado (vars + deps) |
   | E3 | E2 concluido sem alertas criticos |
   | E4 | E3 concluido |
   | E5 | E4 concluido |
   | E6 | E5 concluido |

   - Se entry criteria nao atendido: exibir mensagem `"Pre-requisito faltante: [descricao]. Execute a fase anterior primeiro."` e parar.

4. **Registrar inicio no CICLO.md**:
   - Atualizar tabela Progresso: `status: em_andamento`, `inicio: {timestamp}`
   - Append ao **Log de Execucao**: `[{timestamp}] SISTEMA — Iniciando fase {fase} ({skill})`

5. **Invocar a skill correspondente**:

   > **Regra arquitetural**: O command invoca **skills**, nunca agents diretamente. A skill decide internamente se executa no main thread ou delega a um agente.

   | Fase | Skill |
   |------|-------|
   | E2 | collecting-data |
   | E3 | analyzing-deviations |
   | E4 | summarizing-actions |
   | E5 | projecting-results |
   | E6 | consolidating-wbr |

   Contexto disponivel para a skill: vertical, periodo (YYYY-MM), granularidade, checkpoint_label, data_inicio, data_fim, dias_uteis_totais, dias_uteis_decorridos, dias_uteis_restantes, caminho da pasta do ciclo e artefatos anteriores. Todos estes valores sao lidos do header do CICLO.md.

6. **Gate especial apos E2** (apenas quando fase executada = E2):
   - Verificar que `execution-plan.json` existe no cycle folder
   - Verificar que `dados/provenance.json` existe e nao esta vazio
   - Para cada entrada em `provenance.json`, verificar que o raw file existe
   - Verificar SHA-256: `shasum -a 256 dados/raw/{file}` vs `provenance.sha256`
   - Exibir tabela de proveniencia ao usuario
   - Se `data-quality/data-quality-report.md` contem alertas criticos: **PARAR**, registrar em Anomalias, informar usuario
   - Se verificacao de hash falhar: **PARAR**, registrar em Anomalias, informar usuario

7. **Atualizar CICLO.md** apos execucao:
   - Tabela Progresso: `status: concluido`, `fim: {timestamp}`, `artefato: {caminho}`
   - Append ao **Log de Execucao**: `[{timestamp}] AGENTE:{agent} — Fase {fase} concluida. Artefato: {caminho}`
   - Se a skill falhar:
     - Tabela Progresso: `status: erro`, `fim: {timestamp}`
     - Append a **Anomalias**: `[{timestamp}] SISTEMA — ERRO em {fase}: {detalhes}`
     - Sugerir retry

8. **Exibir resultado** ao usuario com:
   - Fase executada e duracao
   - Caminho do artefato gerado (relativo a pasta do ciclo)
   - Proxima fase sugerida (ou mensagem de pipeline concluido)

## Tratamento de erros

| Cenario | Acao |
|---------|------|
| CICLO.md nao encontrado | Criar novo ciclo para a data atual (YYYY-MM-DD) com estrutura de pastas |
| Entry criteria nao atendido | Exibir pre-requisito faltante e parar |
| Todas as fases concluidas | Exibir: `"Pipeline G2.2 concluido para {vertical}. Proximo: /m7-ritual-gestao:prepare-ritual {vertical}"` |
| Skill falha durante execucao | Registrar erro no CICLO.md (Anomalias + Log), exibir detalhes e sugerir retry |

## Output

Exibir ao usuario:

```
Executando fase {fase} ({skill}) para {vertical}...
Agent: {agent}
Entry criteria: {descricao}

[... execucao da skill ...]

{fase} concluida em {duracao}
Output: {vertical}/{YYYY-MM-DD}/{caminho-artefato}
Proximo: /m7-controle:next {vertical} ({proxima-fase}: {proxima-skill})
```
