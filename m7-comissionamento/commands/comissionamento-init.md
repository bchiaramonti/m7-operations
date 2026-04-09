---
name: comissionamento-init
description: >-
  Inicializa uma nova competencia de comissionamento mensal.
  Cria estrutura de diretorios, arquivos de controle e parametrizacoes.
  Use no inicio de cada ciclo mensal de comissionamento.
argument-hint: [MM YYYY]
allowed-tools: Read, Write, Bash, Glob, Grep
---

# Inicializar Competencia de Comissionamento

Invoca a skill `structuring-competencia` para criar a estrutura completa de uma nova competencia.

## Input

Competencia informada pelo usuario: $ARGUMENTS

Formatos aceitos: `MM YYYY` (ex: `04 2026`), `Mes YYYY` (ex: `Abril 2026`), `Mes de YYYY` (ex: `Abril de 2026`).

Se $ARGUMENTS estiver vazio, perguntar ao usuario qual competencia deseja inicializar.

## Steps

1. Validar os parametros recebidos (mes e ano)
2. Verificar se a competencia ja existe (buscar pasta `YYYY/MM-YY/` no workspace atual)
3. Se ja existe, avisar e perguntar se deseja sobrescrever
4. Executar a skill `structuring-competencia` com os parametros validados
5. Confirmar criacao exibindo resumo dos artefatos gerados

## Output

Exibir resumo:
- Diretorios criados (9)
- Arquivos de controle criados (4)
- Arquivos de parametrizacao preparados (8)
- Proximos passos (colocar arquivos na pasta raw/, revisar parametrizacoes)
