---
description: Gera materiais pre-ritual (HTML + briefing) para uma vertical. Equivalente a executar G2.3 E2 diretamente. Verifica existencia do WBR, invoca skill preparing-materials, salva outputs e atualiza CICLO.md.
argument-hint: <vertical>
---

# m7-ritual-gestao:prepare-ritual

Gera materiais pre-ritual (apresentacao HTML + briefing MD) para uma vertical a partir do WBR disponivel.

## Input

- **vertical** (obrigatorio): `$ARGUMENTS[0]` — vertical a processar. Valores aceitos: `investimentos`, `credito`, `universo`, `seguros`, `consorcios`.

Se vertical nao informada, exibir: `"Uso: /m7-ritual-gestao:prepare-ritual <vertical>"` e parar.

## Steps

### 1. Validar vertical

1. Normalizar o input para lowercase.
2. Verificar se o valor esta na lista aceita: `investimentos`, `credito`, `universo`, `seguros`, `consorcios`.
3. Se valor invalido: exibir `"Vertical '{vertical}' invalida. Valores aceitos: investimentos, credito, universo, seguros, consorcios."` e parar.

### 2. Verificar existencia do WBR

> **Timestamps**: Sempre que este documento menciona `{timestamp}`, obter a hora real do sistema via `date '+%Y-%m-%dT%H:%M'` (Bash). NUNCA usar `00:00` ou estimar a hora — executar o comando `date` no momento exato do registro.

1. Obter data atual e calcular inicio da semana (segunda-feira).
2. Buscar WBR da vertical: `Glob('**/wbr-{vertical}-*.md')` — filtrar apenas arquivos com data dentro da semana atual.
3. Avaliar resultado:

   - **WBR encontrado e da semana atual**: prosseguir para Step 3.
   - **WBR encontrado mas da semana anterior**: exibir `"WBR encontrado e da semana passada ({data}). Deseja usar mesmo assim? [s/n]"` e aguardar resposta do usuario. Se `n`, parar. Se `s`, prosseguir com o WBR encontrado.
   - **WBR nao encontrado**: exibir `"WBR nao encontrado para {vertical} na semana {semana}. Execute /m7-controle:run-weekly {vertical} primeiro."` e parar.

4. Armazenar caminho do WBR selecionado para uso pela skill.

### 3. Garantir pasta de output

1. Verificar/criar pasta `output/{vertical}/` para receber os arquivos gerados.

### 4. Invocar skill preparing-materials

> **Regra arquitetural**: O command invoca **skills**, nunca agents diretamente. A skill decide internamente se executa no main thread ou delega a um agente.

1. Registrar inicio: append ao **Log de Execucao** do CICLO.md (se existir): `[{timestamp}] SISTEMA — Iniciando G2.3 E2 (preparing-materials) para {vertical}`
2. Atualizar tabela Progresso do CICLO.md (se existir secao G2.3): `E2 status: em_andamento`, `inicio: {timestamp}`
3. Invocar skill `preparing-materials` com contexto:
   - Vertical sendo processada
   - Caminho do WBR selecionado
   - Caminho de output: `output/{vertical}/`
   - Data de referencia: `{YYYY-MM-DD}` (data atual)
   - Nomes esperados dos arquivos de saida:
     - `ritual-{vertical}-{YYYY-MM-DD}.html`
     - `briefing-{vertical}-{YYYY-MM-DD}.md`

### 5. Verificar outputs gerados

1. Confirmar existencia dos artefatos esperados:
   - `output/{vertical}/ritual-{vertical}-{YYYY-MM-DD}.html`
   - `output/{vertical}/briefing-{vertical}-{YYYY-MM-DD}.md`
2. Se HTML nao gerado:
   - Registrar erro no CICLO.md (Anomalias + Log)
   - Exibir: `"Erro na geracao do HTML. Verifique os logs do material-generator."` e parar.
3. Se briefing nao gerado: registrar erro e parar.

### 6. Atualizar CICLO.md

1. Localizar CICLO.md da vertical no diretorio de trabalho: `Glob('**/CICLO.md')` — selecionar o mais recente da vertical.
2. Se CICLO.md possui secao G2.3:
   - Atualizar tabela Progresso: `E2 status: concluido`, `fim: {timestamp}`, `artefato: output/{vertical}/ritual-{vertical}-{YYYY-MM-DD}.html + briefing-{vertical}-{YYYY-MM-DD}.md`
   - Append ao **Log de Execucao**: `[{timestamp}] SISTEMA — G2.3 E2 concluido. Materiais pre-ritual gerados.`
3. Se CICLO.md nao possui secao G2.3, adicionar:

```markdown
## G2.3 - Ritual de Gestao

| Fase | Skill | Status | Inicio | Fim | Artefato |
|------|-------|--------|--------|-----|----------|
| E2 | preparing-materials | concluido | {timestamp} | {timestamp} | output/{vertical}/ritual-{vertical}-{YYYY-MM-DD}.html |
| E3 | (distribuicao manual) | pendente | -- | -- | -- |
| E5 | recording-decisions | pendente | -- | -- | -- |
```

### 7. Exibir resultado final

Exibir resumo ao usuario:

```
Materiais pre-ritual gerados - {Vertical} - {YYYY-MM-DD}

Arquivos:
- output/{vertical}/ritual-{vertical}-{YYYY-MM-DD}.html
- output/{vertical}/briefing-{vertical}-{YYYY-MM-DD}.md

WBR utilizado: {caminho-wbr}
Tempo: {duracao}
Proximo: Valide os materiais e distribua ao gestor por e-mail.
```

## Tratamento de erros

| Erro | Tratamento |
|------|------------|
| Vertical nao informada | `"Uso: /m7-ritual-gestao:prepare-ritual <vertical>"` |
| Vertical invalida | `"Vertical '{vertical}' invalida. Valores aceitos: investimentos, credito, universo, seguros, consorcios."` |
| WBR nao encontrado | `"WBR nao encontrado para {vertical} na semana {semana}. Execute /m7-controle:run-weekly {vertical} primeiro."` |
| WBR desatualizado (semana anterior) | `"WBR encontrado e da semana passada ({data}). Deseja usar mesmo assim? [s/n]"` |
| Erro na geracao do HTML | Registrar erro no CICLO.md, exibir detalhes |
| CICLO.md nao encontrado | Prosseguir sem atualizacao de ciclo; exibir aviso `"CICLO.md nao encontrado. Outputs gerados mas progresso nao registrado."` |

## Uso como scheduled task

Este comando pode ser agendado para execucao automatica:

```json
{
  "name": "Materiais G2.3 {Vertical}",
  "schedule": "0 8 * * 2",
  "command": "/m7-ritual-gestao:prepare-ritual {vertical}"
}
```

Cadencia padrao: terca-feira 08:00 (materiais prontos antes do ritual).
