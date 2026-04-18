---
name: initializing-project
description: >-
  Cria a estrutura básica obrigatória de um diretório de projeto com as
  4 pastas de fase (1-planning, 2-development, 3-conclusion, 4-status-report),
  _docs/assets e _docs/bibliography, além de CLAUDE.md e BRIEFING.md iniciais.
  Use quando o usuário quer iniciar um novo projeto e precisa do scaffold base.
  Esta skill NÃO constrói o plano de projeto nem WBS/EAP — para isso use
  `building-project-plan` depois.

  <example>
  Context: usuário quer criar um novo projeto
  user: "Quero começar o projeto de padronização dos rituais M7"
  assistant: invoca initializing-project, coleta nome/objetivo/destino, cria o diretório
  </example>

  <example>
  Context: usuário tem apenas a ideia do projeto
  user: "Vou tocar um projeto de revisão do funil de captação, crie a estrutura"
  assistant: invoca initializing-project; depois sugere building-project-plan
  </example>
user-invocable: true
---

# Initializing Project

Cria o scaffold base de um diretório de projeto: 4 pastas de fase numeradas, `_docs/` de apoio, e os dois arquivos semânticos mínimos (`CLAUDE.md` e `BRIEFING.md`). É o **primeiro passo** do ciclo de vida de um projeto no plugin `m7-projects`.

Esta skill **não** cria plano, WBS/EAP, cronograma, ou integrações externas. Para esses, invoque as skills seguintes na sequência:

1. `initializing-project` *(esta skill)* — cria a casca
2. `building-project-plan` — preenche o plano formal (WBS/EAP, cronograma, stakeholders, riscos)
3. `managing-action-plan` — inicializa `CRONOGRAMA.md` + `CHANGELOG.md` e conecta ao ClickUp
4. `generating-status-materials` — gera OPR + apresentação por data

## Pré-requisitos

- Plugin `m7-projects` instalado
- Nome do projeto escolhido (kebab-case, sem acentos, ≤40 chars — ver [references/directory-layout.md](references/directory-layout.md))
- Destino definido — default: `1-projects/<nome>/` no vault brain; usuário pode sobrescrever

## Quick start

O usuário diz "cria a estrutura do projeto X". A skill:

1. Coleta 5 inputs (nome, destino, objetivo, stakeholders, prazo)
2. Valida que o destino não existe ou está vazio
3. Cria 6 pastas (cada uma com `.gitkeep`)
4. Instancia `CLAUDE.md` e `BRIEFING.md` a partir dos templates
5. Imprime tree e aponta `building-project-plan` como próximo passo

## Inputs (coletados interativamente)

Sempre pergunte os 5 inputs na abertura, em uma mensagem única (não um por vez):

| Input | Obrigatório | Default | Destino |
|---|---|---|---|
| `project_name` | sim | — | nome da pasta + placeholder `{{project_name}}` |
| `destination` | não | `1-projects/<project_name>/` | path absoluto ou relativo do vault |
| `project_goal` | sim | — | `{{project_goal}}` no BRIEFING e CLAUDE |
| `stakeholders` | não | `*(a definir)*` | `{{stakeholders_list}}` no BRIEFING |
| `deadline` | não | `TBD` | `{{deadline_or_tbd}}` |

Regras de normalização:

- `project_name` → kebab-case; strip acentos; remover chars `[^a-z0-9-]`; truncar a 40 chars
- `destination` → se relativo, resolver contra o working directory; nunca criar fora do vault sem confirmação
- `stakeholders` → lista livre, renderizar como bullets Markdown
- `creation_date` → `YYYY-MM-DD` da data atual (gerar, não perguntar)

## Processo (determinístico)

Execute em ordem. Se qualquer passo falhar, aborte com mensagem clara ao usuário e não deixe o diretório em estado parcial.

### 1. Validar destino

- Se `destination` existe e **não está vazio** → abortar: `"Destino já existe com conteúdo: <path>. Escolha outro nome ou apague/mova o existente."`
- Se `destination` existe e está vazio → ok, reusar
- Se `destination` não existe → criar

### 2. Criar 6 diretórios

```
<destination>/
├── 1-planning/
├── 2-development/
├── 3-conclusion/
├── 4-status-report/
└── _docs/
    ├── assets/
    └── bibliography/
```

### 3. Criar `.gitkeep` em cada pasta

Touch de arquivo vazio em:
- `1-planning/.gitkeep`
- `2-development/.gitkeep`
- `3-conclusion/.gitkeep`
- `4-status-report/.gitkeep`
- `_docs/assets/.gitkeep`
- `_docs/bibliography/.gitkeep`

Sem `.gitkeep`, pastas vazias somem no primeiro `git add` — quebrando o contrato visual de 4 fases.

### 4. Instanciar `CLAUDE.md`

Ler [templates/CLAUDE.tmpl.md](templates/CLAUDE.tmpl.md), substituir placeholders:

- `{{project_name}}` → input
- `{{project_goal}}` → input
- `{{deadline_or_tbd}}` → input ou `TBD`
- `{{clickup_list_id_or_tbd}}` → `TBD` (preenchido depois por `managing-action-plan`)

Escrever em `<destination>/CLAUDE.md`.

### 5. Instanciar `BRIEFING.md`

Ler [templates/BRIEFING.tmpl.md](templates/BRIEFING.tmpl.md), substituir:

- `{{project_name}}` → input
- `{{creation_date}}` → data atual `YYYY-MM-DD`
- `{{project_goal}}` → input
- `{{context_placeholder_instruction}}` → `*(preencher com o contexto atual, antecedentes e motivação — pode ser iterado durante building-project-plan)*`
- `{{stakeholders_list}}` → bullets a partir do input, ou `- *(a definir)*`
- `{{deadline_or_tbd}}` → input ou `TBD`

Escrever em `<destination>/BRIEFING.md`.

### 6. Imprimir tree + próximo passo

Gerar output visual como:

```
✓ Projeto criado em: 1-projects/<project_name>/
  ├── CLAUDE.md
  ├── BRIEFING.md
  ├── 1-planning/
  ├── 2-development/
  ├── 3-conclusion/
  ├── 4-status-report/
  └── _docs/
      ├── assets/
      └── bibliography/

Próximo passo: invoque `building-project-plan` para construir o plano formal
(WBS/EAP, cronograma, stakeholders detalhados, riscos).
```

## Validação pós-execução

Antes de declarar sucesso, verifique:

- [ ] Tree real bate com o tree esperado (6 pastas + 2 arquivos na raiz)
- [ ] `CLAUDE.md` e `BRIEFING.md` **não contêm** nenhum `{{...}}` remanescente (grep simples: se houver match, falhou a substituição)
- [ ] Todas as 6 pastas têm `.gitkeep`
- [ ] Ambos os campos obrigatórios (`project_name`, `project_goal`) foram preenchidos com valor não vazio

Se qualquer item falhar, **avise explicitamente** o usuário — não declare sucesso silenciosamente.

## Fora de escopo (intencional)

Esta skill **não faz**:

- WBS/EAP → escopo de `building-project-plan`
- `CRONOGRAMA.md` / `CHANGELOG.md` → criados por `managing-action-plan` na primeira operação
- Integração ClickUp → só quando `managing-action-plan` rodar
- Templates de artefatos do plano (escopo detalhado, matriz de riscos, stakeholders RACI) → escopo de `building-project-plan`
- Renomeação de projeto existente → operação manual; ver [references/directory-layout.md](references/directory-layout.md)

## Additional resources

- [references/directory-layout.md](references/directory-layout.md) — por que 4 pastas numeradas, convenção do `_docs/`, nomenclatura
- [templates/CLAUDE.tmpl.md](templates/CLAUDE.tmpl.md) — orquestrador do projeto
- [templates/BRIEFING.tmpl.md](templates/BRIEFING.tmpl.md) — contexto inicial
