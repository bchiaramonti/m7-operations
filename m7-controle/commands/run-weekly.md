---
description: Executa o ciclo completo do pipeline G2.2 (E2 a E6) em sequencia para uma vertical. Pergunta periodo de analise e granularidade, cria pasta do ciclo com CICLO.md, invoca skills em cadeia e interrompe se alguma fase falhar.
argument-hint: <vertical>
---

# m7-controle:run-weekly

Executa o pipeline de controle de performance (G2.2) para uma vertical.

## Input

- **vertical** (obrigatorio): `$ARGUMENTS[0]` — nome da vertical em kebab-case (ex: `investimentos`, `consorcios`, `credito`). Deve existir pelo menos 1 Card de Performance ativo em `cards/{vertical}/`.
- **periodo** (obrigatorio): Periodo de analise no formato `YYYY-MM` (ex: `2026-03`). Se nao informado nos argumentos, PERGUNTAR ao usuario antes de iniciar.
- **granularidade** (opcional): Frequencia do checkpoint de analise. Valores aceitos: `diaria`, `semanal`, `quinzenal`, `mensal`, `trimestral`. Default: `semanal`.

Se vertical nao informada, exibir: `"Uso: /m7-controle:run-weekly <vertical>"` e parar.

## Steps

### 1. Validar vertical

1. Normalizar o input para kebab-case lowercase
2. Verificar existencia de Cards de Performance: `Glob('**/cards/{vertical}/*.yaml')`
3. Se retornar **0 resultados**: exibir `"Nenhum Card de Performance encontrado para vertical '{vertical}'. Verifique se existe pelo menos 1 Card ativo em cards/{vertical}/."` e parar.
4. Se retornar resultados: vertical valida. **NAO prosseguir para E2 — ir para Step 1.5 primeiro.**

### 1.5. Configurar periodo e granularidade

> **OBRIGATORIO**: SEMPRE perguntar periodo e granularidade ao usuario usando AskUserQuestion ANTES de prosseguir. NAO assuma defaults silenciosamente. NAO pule esta etapa. O pipeline NAO pode iniciar sem confirmacao explicita do usuario.

1. **PARAR e perguntar ao usuario** usando AskUserQuestion:
   ```
   Antes de iniciar o pipeline, preciso confirmar:

   1. **Periodo de analise** (formato YYYY-MM): Qual mes analisar? (ex: 2026-03)
   2. **Granularidade do checkpoint**: diaria / semanal / quinzenal / mensal / trimestral (default: semanal)
   ```
2. **Aguardar resposta** do usuario. Se o usuario responder apenas a vertical sem periodo, PERGUNTAR NOVAMENTE.
3. Se o usuario confirmar o default (mes atual + semanal), aceitar e prosseguir.
4. **Derivar datas** a partir do periodo:
   - `data_inicio` = primeiro dia do mes: `{YYYY-MM}-01`
   - `data_fim` = ultimo dia do mes (calcular: 28/29/30/31 conforme mes/ano)
4. **Calcular checkpoint_label** baseado na data de execucao dentro do periodo:
   - Determinar em qual checkpoint da granularidade a data atual se encontra
   - Formato: `"{Mes} {Ano}, {granularidade} {N} (MTD)"`
   - Exemplos:
     - Execucao em 2026-03-23 com granularidade semanal: `"Marco 2026, semana 4 (MTD)"`
     - Execucao em 2026-03-15 com granularidade quinzenal: `"Marco 2026, quinzena 1 (MTD)"`
     - Execucao em 2026-03-31 com granularidade mensal: `"Marco 2026 (fechamento)"`
5. **Calcular parametros temporais**:
   - `dias_uteis_totais`: total de dias uteis do periodo completo (seg-sex, excluir feriados se disponivel)
   - `dias_uteis_decorridos`: dias uteis do `data_inicio` ate a data de execucao (inclusive)
   - `dias_uteis_restantes`: `dias_uteis_totais - dias_uteis_decorridos`

### 2. Criar estrutura de pastas do ciclo

Determinar a data do ciclo como `YYYY-MM-DD` (data atual de execucao).

> **Timestamps**: Sempre que este documento menciona `{timestamp}`, obter a hora real do sistema via `date '+%Y-%m-%dT%H:%M'` (Bash). NUNCA usar `00:00` ou estimar a hora — executar o comando `date` no momento exato do registro.

Criar a estrutura de pastas:

```
{vertical}/YYYY-MM-DD/
├── CICLO.md
├── dados/
│   └── raw/
├── data-quality/
├── analise/
└── wbr/
```

### 3. Inicializar CICLO.md

Verificar se ja existe um CICLO.md para a data atual e vertical (`{vertical}/YYYY-MM-DD/CICLO.md`):

- **Se existe e esta incompleto** (alguma fase pendente): retomar a partir da proxima fase pendente.
- **Se existe e esta completo**: perguntar ao usuario se deseja reexecutar.
- **Se nao existe**: criar novo CICLO.md com o template:

```markdown
# CICLO G2.2 - {Vertical} - {YYYY-MM-DD}

> Iniciado: {YYYY-MM-DDTHH:MM}
> Vertical: {vertical}
> Periodo: {periodo} ({data_inicio} a {data_fim})
> Granularidade: {granularidade}
> Checkpoint: {checkpoint_label}
> Status: em_andamento
> Pasta: {vertical}/{YYYY-MM-DD}/

## Progresso

| Fase | Skill | Status | Inicio | Fim | Artefato |
|------|-------|--------|--------|-----|----------|
| E2 | collecting-data | pendente | -- | -- | -- |
| E3 | analyzing-deviations | pendente | -- | -- | -- |
| E4 | summarizing-actions | pendente | -- | -- | -- |
| E5 | projecting-results | pendente | -- | -- | -- |
| E6 | consolidating-wbr | pendente | -- | -- | -- |

## Log de Execucao

<!-- Formato: [YYYY-MM-DDTHH:MM] {AGENTE:nome|SISTEMA|USUARIO} — {descricao} -->

## Anomalias

<!-- Alertas de qualidade, erros de scripts, dados ausentes -->
<!-- Formato: [YYYY-MM-DDTHH:MM] {AGENTE:nome|SISTEMA} — {severidade}: {descricao} -->

## Decisoes

<!-- Decisoes tomadas durante o ciclo com atribuicao explicita -->
<!-- Formato: [YYYY-MM-DDTHH:MM] {AGENTE:nome|USUARIO} — {decisao} | Justificativa: {razao} -->
```

### 4. Executar pipeline sequencialmente

Para cada fase na ordem E2 → E3 → E4 → E5 → E6:

#### 4a. Verificar entry criteria

| Fase | Entry Criteria | Como verificar |
|------|---------------|----------------|
| E2 | Cards YAML da vertical existem no repositorio do usuario | `Glob('**/cards/{VERT}/*.yaml')` retorna pelo menos 1 resultado |
| E3 | E2 concluido sem alertas criticos | CICLO.md E2 = `concluido` E `dados/dados-consolidados-{vertical}.json` existe |
| E4 | E3 concluido | CICLO.md E3 = `concluido` |
| E5 | E4 concluido | CICLO.md E4 = `concluido` |
| E6 | E5 concluido | CICLO.md E5 = `concluido` |

Se entry criteria **NAO atendido**: registrar erro no CICLO.md (Anomalias + Log) e parar (ver Step 5).

#### 4b. Registrar inicio no CICLO.md

1. Atualizar a tabela Progresso: `status: em_andamento`, `inicio: {timestamp}`.
2. Append ao **Log de Execucao**: `[{timestamp}] SISTEMA — Iniciando fase {fase} ({skill})`

#### 4c. Invocar skill correspondente

> **Regra arquitetural**: O command invoca **skills**, nunca agents diretamente. A skill decide internamente se executa no main thread ou delega a um agente.

| Fase | Skill |
|------|-------|
| E2 | collecting-data |
| E3 | analyzing-deviations |
| E4 | summarizing-actions |
| E5 | projecting-results |
| E6 | consolidating-wbr |

Contexto disponivel para a skill:
- Vertical sendo processada
- Periodo de analise: `periodo` (YYYY-MM), `data_inicio`, `data_fim`
- Granularidade: `granularidade`, `checkpoint_label`
- Parametros temporais: `dias_uteis_totais`, `dias_uteis_decorridos`, `dias_uteis_restantes`
- Caminho da pasta do ciclo: `{vertical}/{YYYY-MM-DD}/`
- Caminho dos artefatos das fases anteriores
- Todos estes valores estao registrados no header do CICLO.md

#### 4d. Verificar output

Confirmar que o artefato esperado foi gerado:

| Fase | Artefato esperado |
|------|-------------------|
| E2 | `data-quality/data-quality-report.md` + `dados/dados-consolidados-{vertical}.json` |
| E3 | `analise/deviation-cause-report.md` |
| E4 | `analise/action-report.md` |
| E5 | `analise/projection-report.md` |
| E6 | `wbr/wbr-{vertical}-{data}.md` + `wbr/wbr-narrativo-{vertical}-{data}.md` + `.html` + `.pdf` |

> Todos os caminhos sao relativos a pasta do ciclo `{vertical}/{YYYY-MM-DD}/`.

#### 4e. Registrar conclusao no CICLO.md

1. Atualizar tabela Progresso: `status: concluido`, `fim: {timestamp}`, `artefato: {caminho}`.
2. Append ao **Log de Execucao**: `[{timestamp}] SISTEMA — Fase {fase} concluida. Artefato: {caminho}`

#### 4f. Gate check especial apos E2 (Proveniencia + Qualidade)

**Gate de Proveniencia** — verificar que dados vieram de execucao real de scripts:
1. Verificar que `execution-plan.json` existe no cycle folder
2. Verificar que `dados/provenance.json` existe e nao esta vazio
3. Para cada entrada em `provenance.json`, verificar que o raw file correspondente existe via `ls`
4. Para cada entrada, verificar SHA-256: executar `shasum -a 256 dados/raw/{file}` e comparar com `provenance.sha256`
5. Se QUALQUER verificacao falhar: **PARAR pipeline**, registrar em Anomalias, exibir ao usuario

**Gate de Qualidade** — verificar que dados sao confiaveis:
6. Se `data-quality/data-quality-report.md` contem alertas criticos:
   - Append a **Anomalias**: `[{timestamp}] SISTEMA — CRITICO: alertas de qualidade bloquearam pipeline`
   - Append a **Decisoes**: `[{timestamp}] SISTEMA — Pipeline interrompido. Aguardando decisao do usuario.`
   - Exibir os alertas criticos ao usuario
   - Sugerir: `"Resolva os alertas criticos e execute /m7-controle:next {vertical} para retomar de E2"`
   - **Parar pipeline**

**Resumo de Proveniencia** — exibir ao usuario:
```
E2 Coleta Concluida — Proveniencia

| Indicador | Tool | Linhas | Raw File | Hash OK |
|-----------|------|--------|----------|---------|
| {indicator_id} | {tool} | {rows} | {file} | {OK|FALHA} |

Proveniencia: {N}/{M} verificacoes OK
Qualidade: {OK|Atencao|Critico}
```

### 5. Tratamento de falhas

Se qualquer fase falhar:

1. Registrar no CICLO.md:
   - Tabela Progresso: `status: erro`, `fim: {timestamp}`
   - Append a **Anomalias**: `[{timestamp}] SISTEMA — ERRO em {fase}: {mensagem_erro}`
   - Append ao **Log de Execucao**: `[{timestamp}] SISTEMA — Pipeline interrompido em {fase}`
2. **Interromper pipeline** (nao avancar para proxima fase)
3. Exibir resumo parcial:

```
Pipeline G2.2 interrompido em {fase} ({skill}) - {vertical}

| Fase | Status       | Artefato                              |
|------|--------------|---------------------------------------|
| E2   | Concluido    | data-quality/data-quality-report.md   |
| E3   | Erro         | --                                    |
| E4   | Pendente     | --                                    |
| E5   | Pendente     | --                                    |
| E6   | Pendente     | --                                    |

Erro: {descricao}
Acao: /m7-controle:next {vertical} para retry da fase {fase}
```

### 6. Exibir resumo final (sucesso)

Ao concluir todas as 5 fases:

1. Atualizar CICLO.md: `> Status: concluido`
2. Append ao **Log de Execucao**: `[{timestamp}] SISTEMA — Pipeline G2.2 concluido com sucesso`
3. Exibir resumo completo:

```
Pipeline G2.2 concluido - {Vertical} - {YYYY-MM-DD}

| Fase | Tempo  | Artefato                                  |
|------|--------|-------------------------------------------|
| E2   | {dur}  | data-quality/data-quality-report.md        |
| E3   | {dur}  | analise/deviation-cause-report.md          |
| E4   | {dur}  | analise/action-report.md                   |
| E5   | {dur}  | analise/projection-report.md               |
| E6   | {dur}  | wbr/wbr-{vertical}-{data}.md + wbr-narrativo |

Total: {duracao_total}
Pasta do ciclo: {vertical}/{YYYY-MM-DD}/
Proximo: /m7-ritual-gestao:prepare-ritual {vertical}
```

## Tratamento de erros

| Erro | Tratamento |
|------|------------|
| Vertical nao informada | Exibir uso e parar |
| Vertical invalida | Exibir valores aceitos e parar |
| Script falhou em E2 (env vars ausentes, dependencias, timeout) | Interromper, registrar em Anomalias, apresentar opcoes ao usuario (retry, verificar ambiente) e AGUARDAR decisao |
| Alerta critico em E2 | Interromper, registrar em Anomalias, exibir alertas, sugerir resolver antes de continuar |
| Fase intermediaria falha | Interromper, registrar erro em Anomalias e Log, sugerir `/m7-controle:next` para retry |
| CICLO.md corrompido | Recriar CICLO.md preservando fases ja concluidas |
