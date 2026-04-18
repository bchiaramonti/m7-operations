# Cronograma.xlsx — Schema BASELINE

Schema formal do xlsx produzido por esta skill. Este e o **contrato
machine-readable** que `managing-action-plan` consome no 1o run.

## Indice

1. [Localizacao e role](#localizacao-e-role)
2. [Layout fisico](#layout-fisico)
3. [Colunas](#colunas)
4. [Validacoes](#validacoes)
5. [Formatacao por Tipo](#formatacao-por-tipo)
6. [Diferencas entre BASELINE e LIVE](#diferencas-entre-baseline-e-live)

---

## Localizacao e role

| Path | Quem cria | Quem mantem | Mutabilidade |
|---|---|---|---|
| `<project-dir>/1-planning/Cronograma.xlsx` (BASELINE) | `building-project-plan` | **Ninguem** apos criacao | Imutavel |
| `<project-dir>/4-status-report/Cronograma.xlsx` (LIVE) | `managing-action-plan` (copia da BASELINE + adiciona col L) | `managing-action-plan` | Mutavel (sync com ClickUp) |

A BASELINE e o "ponto zero" do plano — referencia historica do que foi
planejado. A LIVE evolui ao longo da execucao.

## Layout fisico

```
A:    margem (vazia)
B-K:  10 colunas de dados
L:    NAO EXISTE na BASELINE (adicionada pela managing-action-plan no 1o run)

Linhas:
  R1: titulo do projeto (em col C)
  R2: subtitulo / metadata (em col C)
  R3: vazia (respiro visual)
  R4: HEADER (10 colunas B-K), bold, fundo caqui, texto off-white
  R5+: dados, formatacao por Tipo
```

**Sheet name:** `Cronograma Detalhado` (fixo, espelha H1-02).

**Freeze panes:** `B5` (primeira coluna de dados + header fixos).

**Auto-filter:** ativo na row 4, range `B4:K{last_data_row}`.

## Colunas

| Col | Header | Campo | Tipo | Obrigatorio | Largura |
|---|---|---|---|---|---|
| B | `No.` | `no` | string hierarquico (`1`, `1.1`, `1.1.1`) | sim | 7 |
| C | `Tipo` | `tipo` | enum: `Fase` / `Ação` / `Etapas da Ação` | sim | 16 |
| D | `Etapa` | `etapa` | string (titulo da linha) | sim | 70 |
| E | `Responsável` | `responsavel` | string (nome livre) | sim em Acao/Etapa, opcional em Fase | 18 |
| F | `Início Planejado` | `inicio_plan` | datetime | sim | 16 |
| G | `Fim Planejado` | `fim_plan` | datetime | sim | 16 |
| H | `Início Real` | `inicio_real` | datetime ou vazio | nao (sempre vazio na BASELINE) | 14 |
| I | `Fim Real` | `fim_real` | datetime ou vazio | nao (sempre vazio na BASELINE) | 14 |
| J | `Status` | `status` | enum: `not_started` / `in_progress` / `blocked` / `done` | sim (sempre `not_started` na BASELINE) | 14 |
| K | `Entregável` | `entregavel` | string (texto longo) | sim em Acao/Etapa | 70 |

**Coluna L `ClickUp ID`** e adicionada pela `managing-action-plan` no 1o run quando ela copia a BASELINE para LIVE. **Esta skill nunca cria essa coluna.**

## Validacoes

### Aplicadas pelo `generate_xlsx.py validate_payload()`

**Errors (bloqueiam geracao):**
- `no` vazio
- `no` duplicado
- `tipo` ausente ou fora do enum
- `etapa` vazio
- `inicio_plan` ou `fim_plan` ausente
- `inicio_plan` > `fim_plan`

**Sem warnings nesta skill** — toda inconsistencia bloqueia ate ser
corrigida no `data` antes de gerar.

### Data Validation no Excel

A skill aplica DataValidation nas colunas C (Tipo) e J (Status):

```
Tipo:    Fase | Ação | Etapas da Ação
Status:  not_started | in_progress | blocked | done
```

Tentativa de digitar valor fora do enum → erro do Excel. Garante
integridade quando o usuario edita manualmente o xlsx.

## Formatacao por Tipo

A formatacao reproduz o pattern do projeto-modelo H1-02 (com tokens
canonicos M7-2026; o xlsx do H1-02 usa `#2F3B4E` como historico, mas
a skill segue o sistema atual `#424135`):

| Tipo de linha | Background | Font | Texto |
|---|---|---|---|
| Header (R4) | `#424135` (caqui) | bold 11pt | `#FFFDEF` (off-white) |
| `Fase` (qualquer nivel) | `#424135` (caqui) | bold 11pt | `#FFFDEF` (off-white) |
| `Ação` | `#D9D9D9` (cinza-200) | normal 11pt | `#000000` (preto) |
| `Etapas da Ação` | branco | normal 10pt | `#3D3D3D` (cinza-700) |

**Coluna `Etapa` em rows tipo `Ação`:** bold (espelha o `<strong>` do HTML).

**Sub-fases (`Tipo=Fase` aninhada via `No.` 2.1, 2.1.1, etc.):** mesma
formatacao das Fases raiz (caqui + off-white + bold). A hierarquia
visual no HTML de cronograma (artefato 08) e dada pela coluna `No.`,
nao pelo nivel da formatacao.

## Diferencas entre BASELINE e LIVE

| Aspecto | BASELINE (`1-planning/`) | LIVE (`4-status-report/`) |
|---|---|---|
| Quem cria | `building-project-plan` | `managing-action-plan` (copia + adiciona col L) |
| Coluna L `ClickUp ID` | **Ausente** | Presente (preenchida apos push inicial) |
| `Status` | Sempre `not_started` | Atualizado conforme execucao |
| `Início Real` / `Fim Real` | Sempre vazios | Preenchidos quando ações comecarem/terminarem |
| `Etapa`, `Responsável`, datas planejadas | Imutaveis (referencia historica) | Mutaveis via sync ClickUp |
| Formatacao | Inicial conforme acima | Preservada por openpyxl em writes |

A BASELINE permite, a qualquer momento, comparar "o que foi planejado"
vs "o que esta acontecendo" (LIVE) — diff visual ou via script.

## Hierarquia via `No.`

`No.` segue o padrao `N.M.K.L...` com numero arbitrario de niveis.
Convencoes (espelhando H1-02):

| Padrao | Tipo esperado | Exemplo |
|---|---|---|
| `1` (so 1 numero) | Fase raiz | `1` Planejamento, `2` Execucao, `3` Encerramento |
| `1.1` (2 numeros) | Acao OU Sub-fase (Tipo=Fase aninhada) | `1.1` Elaborar TAP / `2.1` Cadeia de Valor (sub-fase) |
| `1.1.1` (3 numeros) | Etapa OU Acao (se pai e sub-fase) | `1.1.1` Definir escopo / `2.1.1` Definir macroprocessos (Acao dentro de sub-fase 2.1) |
| `2.1.1.1` (4+ numeros) | Etapa (de Acao em sub-fase) | `2.2.1.1.1` Conduzir discovery (Etapa) |

A hierarquia e flexivel — uma Fase pode conter sub-Fases (como `2.1`
em H1-02). O parser reconhece `Tipo=Fase` em qualquer nivel hierarquico
e aplica a formatacao caqui correspondente.

`parent_no("1.1.1") = "1.1"` — string slice deterministico, nao depende
de validacao FK na tabela.

## Geracao via CLI

```bash
# Gerar xlsx a partir de JSON
python3 generate_xlsx.py \
    --input plan-data.json \
    --output 1-planning/Cronograma.xlsx

# Validar payload sem gerar
python3 generate_xlsx.py \
    --input plan-data.json \
    --output ignored.xlsx \
    --validate-only
```

**Schema do `plan-data.json`:**

```json
{
  "project_name": "Playbook de Processos",
  "project_code": "H1-02",
  "project_subtitle": "90 dias | 27/mar a 18/jul 2026 | 3 fases | 9 processos",
  "rows": [
    {
      "no": "1",
      "tipo": "Fase",
      "etapa": "FASE 1 — PLANEJAMENTO",
      "responsavel": "Bruno",
      "inicio_plan": "2026-03-27",
      "fim_plan": "2026-04-14",
      "entregavel": ""
    },
    ...
  ]
}
```

Datas no JSON podem ser ISO `YYYY-MM-DD` (recomendado) — o `parse_date()`
do script tambem aceita `datetime` python (caso o JSON seja gerado de
outro script).

## Cross-skill: contrato com managing-action-plan

A `managing-action-plan/init.py` espera ler **exatamente** este schema.
O smoke test cross-skill confirmou que:

1. `generate_xlsx.py` produz `Cronograma.xlsx` em `1-planning/`
2. `init.py --project-dir <proj>` le `1-planning/Cronograma.xlsx`
3. Copia para `4-status-report/Cronograma.xlsx`
4. Adiciona coluna L `ClickUp ID`
5. Emite `push_plan` em ordem topologica para Claude pushar no ClickUp

Qualquer mudanca de schema desta skill DEVE ser refletida em
`m7-projects/skills/managing-action-plan/scripts/_lib.py:CronogramaXLSX` —
caso contrario o pipeline cross-skill quebra silenciosamente.
