# Cronograma.xlsx — Schema de Referencia

Schema canonico do `Cronograma.xlsx` que esta skill consome e mantem.
Carregue esta reference quando precisar entender colunas, tipos, validacoes
ou hierarquia da planilha.

## Indice

1. [Origem do arquivo](#origem-do-arquivo)
2. [Layout fisico](#layout-fisico)
3. [Colunas canonicas](#colunas-canonicas)
4. [Coluna `ClickUp ID` (adicionada por esta skill)](#coluna-clickup-id-adicionada-por-esta-skill)
5. [Hierarquia via coluna `No.`](#hierarquia-via-coluna-no)
6. [Datas: parsing flexivel + writeback normalizado](#datas-parsing-flexivel--writeback-normalizado)
7. [Tipos validos e enums](#tipos-validos-e-enums)
8. [Validacoes aplicadas pelo parser](#validacoes-aplicadas-pelo-parser)

---

## Origem do arquivo

- **Baseline:** `<projeto>/1-planning/Cronograma.xlsx` — gerada pela skill `building-project-plan`. **Imutavel** apos init do plano de acao.
- **Live:** `<projeto>/4-status-report/Cronograma.xlsx` — copia da baseline na primeira rodada do `init.py` desta skill, depois cresce/muda continuamente.

A separacao baseline ↔ live preserva o "ponto zero" do plano para auditoria, enquanto permite mutacao livre da live ao longo da execucao.

## Layout fisico

- **Sheet ativa:** primeira sheet do workbook (convencao: nome `Cronograma Detalhado` mas o parser nao depende do nome).
- **Header:** linha **4** (R4). As linhas 1-3 sao titulo/legendas humanas.
- **Dados:** a partir da linha **5** ate a ultima linha com `No.` preenchido.
- **Coluna A:** vazia (margem visual). Nao usar.

## Colunas canonicas

| Col | Header (label aceito) | Campo canonico | Tipo |
|---|---|---|---|
| B | `No.` | `no` | string hierarquico (`1`, `1.1`, `1.1.1`) |
| C | `Tipo` | `tipo` | enum: `Fase` / `Ação` / `Etapas da Ação` |
| D | `Etapa` | `etapa` | string (titulo da linha) |
| E | `Responsável` | `responsavel` | texto livre (resolvido via mapping em `CLAUDE.md`) |
| F | `Início Planejado` | `inicio_plan` | datetime (ou string BR `02/abr` aceito no parse) |
| G | `Fim Planejado` | `fim_plan` | datetime |
| H | `Início Real` | `inicio_real` | datetime ou vazio |
| I | `Fim Real` | `fim_real` | datetime ou vazio |
| J | `Status` | `status` | enum local: `not_started` / `in_progress` / `blocked` / `done` |
| K | `Entregável` | `entregavel` | texto longo (vai para `description` no ClickUp) |
| L | `ClickUp ID` | `clickup_id` | string (adicionada na primeira rodada — ver abaixo) |

O parser tolera variacoes nos labels (com/sem acentos, sinonimos comuns como `Owner` para `responsavel`). Lista exata em `_lib.COLUMNS`.

## Coluna `ClickUp ID` (adicionada por esta skill)

A skill `building-project-plan` produz o xlsx **sem** coluna `ClickUp ID`. Na primeira execucao do `init.py`, esta skill:

1. Detecta a ultima coluna preenchida no header (R4)
2. Adiciona `ClickUp ID` na proxima coluna (preserva margem A e qualquer espaco intermediario)
3. Header bold + alinhamento centralizado por coerencia visual

A coluna `ClickUp ID` e a **ancora cross-session** da linha. Uma vez preenchida, qualquer reordenacao de linhas no xlsx nao quebra o sync — e o ID que casa local ↔ remoto, nao o `No.` (que e display humano e pode ser renumerado).

Linhas sem `ClickUp ID` (criadas localmente apos init) sao identificadas pelo hash de conteudo ate serem pushadas pela primeira vez.

## Hierarquia via coluna `No.`

A coluna `No.` define a hierarquia. Padrao: pontos separam niveis.

```
1            (Fase, raiz)
1.1          (Ação dentro da Fase 1)
1.1.1        (Etapa dentro da Ação 1.1)
2.1          (Sub-Fase dentro da Fase 2)  -- nivel arbitrario, ver abaixo
2.1.1        (Ação dentro da sub-Fase 2.1)
```

**Hierarquia flexivel:** uma `Fase` pode conter sub-Fases (qualquer nivel). A unica regra semantica que o parser checa:
- Toda `Etapas da Ação` deve ter um pai do tipo `Ação`
- Toda `Ação` deve ter um pai do tipo `Fase` (em qualquer nivel)

Violacoes geram **warning**, nao error. Cronogramas reais frequentemente tem irregularidades; a skill nao bloqueia sync por isso.

`parent_no("1.1.1")` = `"1.1"` (string slice deterministico, nao depende de validacao FK).

## Datas: parsing flexivel + writeback normalizado

O parser aceita:
- `datetime` nativo do Excel
- ISO `YYYY-MM-DD`
- BR `02/abr` ou `02/abr/2026` (`default-year` da CLI ou ano corrente)
- BR numerico `02/04` ou `02/04/2026` (assume `dd/mm`)
- vazio / `None` / `—` / `-` → vazio

**Normalizacao no writeback:** quando a skill grava qualquer celula de data, normaliza para `datetime` real do openpyxl. Isso quebra formatacao manual de strings tipo `"02/abr"` mas garante:
- Consistencia visual (Excel pode aplicar formato de data unico)
- Hash deterministico (string `02/abr` e datetime `2026-04-02` produzem o mesmo hash apos canonicalizacao)
- Comparacao com ClickUp (que devolve ms epoch UTC)

## Tipos validos e enums

```python
TIPOS_VALIDOS = {"Fase", "Ação", "Acao", "Etapas da Ação", "Etapas da Acao"}
STATUS_LOCAL = {"not_started", "in_progress", "blocked", "done"}
STATUS_MAP_DEFAULT = {
    "not_started": "to do",
    "in_progress": "in progress",
    "blocked": "blocked",
    "done": "complete",
}
```

`STATUS_MAP_DEFAULT` e o mapeamento canonico → ClickUp custom statuses. Pode ser sobrescrito no `.sync-state.json` por projeto se a List ClickUp usar outros nomes.

## Validacoes aplicadas pelo parser

**Errors (bloqueiam parse):**
- `No.` vazio
- `No.` em formato invalido (deve casar `^\d+(\.\d+)*$`)
- `No.` duplicado
- `Etapa` vazia (titulo obrigatorio)

**Warnings (nao bloqueiam):**
- `Tipo` fora do enum
- `Status` fora do enum local (vai ser ignorado pelo sync)
- `parent` (computado via `No.`) nao existe na tabela
- Tipo incompativel com tipo do parent (Etapa cuja parent nao e Ação, etc.)
- Linha `Tipo=Fase` com `No.` que nao e raiz e que tambem nao tem parent Fase
