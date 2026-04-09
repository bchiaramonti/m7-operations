---
description: Registra decisoes pos-ritual em ata estruturada (MD) e atualiza plano-de-acao.csv. Equivalente a executar G2.3 E5 diretamente. Verifica entry criteria, solicita notas do ritual, invoca skill recording-decisions e atualiza CICLO.md.
argument-hint: <vertical>
---

# m7-ritual-gestao:record-decisions

Registra decisoes pos-ritual (ata estruturada MD + atualizacao do plano-de-acao.csv) para uma vertical a partir das notas do ritual.

## Input

- **vertical** (obrigatorio): `$ARGUMENTS[0]` — vertical a processar. Valores aceitos: `investimentos`, `credito`, `universo`, `seguros`, `consorcios`.

Se vertical nao informada, exibir: `"Uso: /m7-ritual-gestao:record-decisions <vertical>"` e parar.

## Steps

### 1. Validar vertical

1. Normalizar o input para lowercase.
2. Verificar se o valor esta na lista aceita: `investimentos`, `credito`, `universo`, `seguros`, `consorcios`.
3. Se valor invalido: exibir `"Vertical '{vertical}' invalida. Valores aceitos: investimentos, credito, universo, seguros, consorcios."` e parar.

### 2. Verificar entry criteria para E5

> **Timestamps**: Sempre que este documento menciona `{timestamp}`, obter a hora real do sistema via `date '+%Y-%m-%dT%H:%M'` (Bash). NUNCA usar `00:00` ou estimar a hora — executar o comando `date` no momento exato do registro.

1. **Localizar CICLO.md** da vertical no diretorio de trabalho: `Glob('**/CICLO.md')` — selecionar o mais recente da vertical.
2. **Verificar secao G2.3** no CICLO.md (se existir):
   - **E2 nao concluido**: exibir aviso `"Materiais pre-ritual (E2) nao gerados. Recomenda-se executar /m7-ritual-gestao:prepare-ritual {vertical} antes. Deseja prosseguir mesmo assim? [s/n]"`. Se `n`, parar. Se `s`, prosseguir.
   - **E3 nao marcado como enviado**: exibir aviso `"Distribuicao de materiais (E3) nao registrada. Deseja prosseguir com o registro de decisoes? [s/n]"`. Se `n`, parar. Se `s`, prosseguir.
   - **E5 ja concluido**: exibir `"E5 ja registrado para {vertical} neste ciclo. Deseja sobrescrever? [s/n]"`. Se `n`, parar.
3. **Localizar plano-de-acao.csv** via `Glob('**/03-implementacao/plano-de-acao.csv')`.
   - Se nao encontrado: exibir `"plano-de-acao.csv nao encontrado em 03-implementacao/. Impossivel registrar contramedidas."` e parar.
4. **Localizar WBR** mais recente da vertical via `Glob('**/output/*/wbr-*.md')`.
   - Se nao encontrado: exibir aviso `"WBR nao encontrado para {vertical}. Prosseguindo sem contexto de desvios."` (nao bloqueia).

### 3. Confirmar ritual realizado

1. Perguntar ao usuario: `"Confirme que o ritual de {Vertical} foi realizado. [s/n]"`
2. Se `n`: exibir `"Registro cancelado. Execute este comando apos a realizacao do ritual."` e parar.
3. Se `s`: prosseguir.

### 4. Solicitar notas do ritual

1. Solicitar ao usuario: `"Compartilhe as notas do ritual (formato livre — bullets, texto corrido ou transcricao). Inclua: participantes, decisoes, contramedidas, responsaveis, prazos e escalonamentos."`
2. Aguardar input do usuario.
3. Se notas vazias ou insuficientes: pedir mais detalhes.

### 5. Garantir pasta de output

1. Verificar/criar pasta `output/{vertical}/` para receber os arquivos gerados.

### 6. Invocar skill recording-decisions

> **Regra arquitetural**: O command invoca **skills**, nunca agents diretamente. A skill decide internamente se executa no main thread ou delega a um agente.

1. Registrar inicio: append ao **Log de Execucao** do CICLO.md (se existir): `[{timestamp}] SISTEMA — Iniciando G2.3 E5 (recording-decisions) para {vertical}`
2. Atualizar tabela Progresso do CICLO.md (se existir secao G2.3): `E5 status: em_andamento`, `inicio: {timestamp}`
3. Invocar skill `recording-decisions` com contexto:
   - Vertical sendo processada
   - Notas do ritual fornecidas pelo usuario
   - Caminho do CICLO.md (pasta do ciclo)
   - Caminho do plano-de-acao.csv
   - Caminho do WBR (se disponivel)
   - Caminho de output: `output/{vertical}/`
   - Data de referencia: `{YYYY-MM-DD}` (data atual)
   - Nome esperado da ata: `ata-ritual-{vertical}-{YYYY-MM-DD}.md`

### 7. Verificar outputs gerados

1. Confirmar existencia da ata:
   - `output/{vertical}/ata-ritual-{vertical}-{YYYY-MM-DD}.md`
2. Confirmar que plano-de-acao.csv foi atualizado (comparar timestamp de modificacao ou contar linhas).
3. Se ata nao gerada:
   - Registrar erro no CICLO.md (Anomalias + Log)
   - Exibir: `"Erro na geracao da ata. Verifique os logs do decision-recorder."` e parar.

### 8. Atualizar CICLO.md

1. Se CICLO.md possui secao G2.3:
   - Atualizar tabela Progresso: `E5 status: concluido`, `fim: {timestamp}`, `artefato: output/{vertical}/ata-ritual-{vertical}-{YYYY-MM-DD}.md`
   - Append ao **Log de Execucao**: `[{timestamp}] SISTEMA — G2.3 E5 concluido. Ata gerada e plano-de-acao.csv atualizado.`
2. Se CICLO.md nao possui secao G2.3, adicionar:

```markdown
## G2.3 - Ritual de Gestao

| Fase | Skill | Status | Inicio | Fim | Artefato |
|------|-------|--------|--------|-----|----------|
| E2 | preparing-materials | pendente | -- | -- | -- |
| E3 | (distribuicao manual) | pendente | -- | -- | -- |
| E5 | recording-decisions | concluido | {timestamp} | {timestamp} | output/{vertical}/ata-ritual-{vertical}-{YYYY-MM-DD}.md |
```

### 9. Exibir resultado final

Exibir resumo ao usuario:

```
Decisoes registradas - {Vertical} - {YYYY-MM-DD}

Arquivos:
- output/{vertical}/ata-ritual-{vertical}-{YYYY-MM-DD}.md

Resumo:
- X decisoes registradas
- Y contramedidas novas (IDs: PA-YYYY-NNN, ...)
- Z acoes atualizadas
- W duplicatas detectadas

CSV atualizado: {caminho-csv}
Tempo: {duracao}
Pipeline G2.3 concluido para {vertical} nesta semana.
```

## Tratamento de erros

| Erro | Tratamento |
|------|------------|
| Vertical nao informada | `"Uso: /m7-ritual-gestao:record-decisions <vertical>"` |
| Vertical invalida | `"Vertical '{vertical}' invalida. Valores aceitos: investimentos, credito, universo, seguros, consorcios."` |
| plano-de-acao.csv nao encontrado | `"plano-de-acao.csv nao encontrado em 03-implementacao/. Impossivel registrar contramedidas."` |
| E2 nao concluido | Aviso com opcao de prosseguir (nao bloqueia) |
| E3 nao marcado enviado | Aviso com opcao de prosseguir (nao bloqueia) |
| E5 ja concluido | Perguntar se deseja sobrescrever |
| Ritual nao confirmado | `"Registro cancelado. Execute este comando apos a realizacao do ritual."` |
| WBR nao encontrado | Aviso informativo (nao bloqueia — prossegue sem contexto de desvios) |
| Erro na geracao da ata | Registrar erro no CICLO.md, exibir detalhes |
| CICLO.md nao encontrado | Prosseguir sem atualizacao de ciclo; exibir aviso `"CICLO.md nao encontrado. Ata gerada mas progresso nao registrado."` |

## Uso como scheduled task

Este comando pode ser agendado para execucao automatica:

```json
{
  "name": "Registro G2.3 {Vertical}",
  "schedule": "0 8 * * 4",
  "command": "/m7-ritual-gestao:record-decisions {vertical}"
}
```

Cadencia padrao: quinta-feira 08:00 (registro apos ritual de quarta-feira).
