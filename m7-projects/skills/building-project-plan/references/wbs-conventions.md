# WBS Conventions

Regras de decomposicao e codificacao para a Estrutura Analitica do
Projeto (WBS/EAP) usadas pela skill em `eap.html` e `Cronograma.xlsx`.

## Indice

1. [Codificacao numerica hierarquica](#codificacao-numerica-hierarquica)
2. [3 niveis na arvore + nivel 4 em tabela](#3-niveis-na-arvore--nivel-4-em-tabela)
3. [Quando ter sub-fases](#quando-ter-sub-fases)
4. [Padroes repetitivos](#padroes-repetitivos)
5. [Pacotes vs ações vs etapas](#pacotes-vs-acoes-vs-etapas)
6. [Critérios de aceite por pacote](#criterios-de-aceite-por-pacote)

---

## Codificacao numerica hierarquica

Todos os itens da WBS sao numerados conforme padrao `N.M.K.L...`:

| Nivel | Padrao | Significado |
|---|---|---|
| 0 | (raiz) | Projeto inteiro — `<project_code> <project_name>` |
| 1 | `N` | Fase principal (ex: `1` Planejamento, `2` Execucao, `3` Encerramento) |
| 2 | `N.M` | Sub-fase ou Pacote direto da Fase |
| 3 | `N.M.K` | Pacote dentro de Sub-fase, ou Etapa |
| 4+ | `N.M.K.L...` | Etapas / atividades dentro de pacotes |

**Regras de codificacao:**
- Sequencial dentro de cada nivel: `1`, `2`, `3` (nao pula numeros)
- Sem zero a esquerda: `1.1` (correto), `01.01` (errado)
- Sem letras: `1.A` invalido
- Maximo 5 niveis na pratica (mais que isso = decomposicao excessiva)

**No `Cronograma.xlsx`** o campo `No.` segue exatamente essa codificacao.
A coluna `Tipo` (Fase/Acao/Etapa) determina o **papel semantico** da
linha; o `No.` determina o **lugar na hierarquia**. Os dois sao
relacionados mas nao identicos:

```
1            Tipo=Fase   nivel 1  (Fase raiz)
1.1          Tipo=Ação   nivel 2  (Acao dentro de Fase)
1.1.1        Tipo=Etapa  nivel 3  (Etapa dentro de Acao)

2.1          Tipo=Fase   nivel 2  (Sub-fase aninhada — caso especial!)
2.1.1        Tipo=Ação   nivel 3  (Acao dentro de Sub-fase)
2.1.1.1      Tipo=Etapa  nivel 4  (Etapa dentro de Acao em Sub-fase)
```

## 3 niveis na arvore + nivel 4 em tabela

A **arvore visual** em `eap.html` (org-chart CSS) renderiza apenas ate
o **Nivel 3** (pacotes). Niveis mais profundos seriam ilegiveis na arvore.

Quando ha **padrao repetitivo no nivel 4** (ex: cada processo decompoe
em 6 pacotes identicos), expressamos isso como uma **tabela `.wp-table`**
abaixo da arvore, mostrando o **template de pacote** apenas uma vez.

Exemplo (H1-02): cada processo P1-P9 tem 6 pacotes identicos:
- `x.y.1` Mapa N2 Jornada
- `x.y.2` Mapa N3 Processos
- `x.y.3` DEIP + Desconexoes
- `x.y.4` Politicas e Manuais
- `x.y.5` Playbook Consolidado
- `x.y.6` Plano de Implementacao

Em vez de renderizar 9 × 6 = 54 nos na arvore, mostramos a tabela com
6 linhas (`x.y.1` a `x.y.6`) e a regra "x = subfase, y = processo".

**Configuracao em `data.eap.nivel_4`:**

```json
{
  "title": "Nível 4 — Pacotes de Trabalho por Processo",
  "intro_html": "Cada processo decompõe-se em 6 pacotes idênticos. Código WBS: <strong>2.{subfase}.{processo}.{pacote}</strong>.",
  "rows": [
    {"wbs": "x.y.1", "nome": "Mapa N2 — Jornada do Cliente", "nivel": "N2", "descricao": "...", "formato": "HTML + MD"},
    ...
  ]
}
```

## Quando ter sub-fases

Sub-fases sao linhas com `Tipo=Fase` e `No.` aninhado (ex: `2.1`, `2.2`).
Use sub-fases quando:

✅ Uma Fase tem **multiplos agrupamentos naturais** (ex: Execucao com `2.1
Cadeia de Valor`, `2.2 Verticais`, `2.3 Transversais`)

✅ Cada agrupamento tem **escopo, duracao e responsavel distintos** —
nao apenas uma colecao de pacotes

✅ Voce quer mostrar **paralelismo** entre agrupamentos no roadmap
(swim-lane / lanes)

❌ NAO use sub-fases se uma Fase tem so 3-5 pacotes — coloque-os
diretamente como filhos da Fase (`1.1`, `1.2`, ...)

❌ NAO use sub-fases para "agrupar pacotes por tema" sem distincao
operacional — vira complexidade desnecessaria

## Padroes repetitivos

Quando processos/sub-fases tem **estrutura interna identica**, padronize:

1. **Same number of children:** todos os processos tem o mesmo numero de
pacotes (ex: 6)
2. **Same names:** os nomes dos pacotes sao identicos (`x.y.1 Mapa N2`,
`x.y.2 Mapa N3`, ...)
3. **Same relative codes:** o ultimo digito segue a mesma sequencia
(`.1`, `.2`, ..., `.6`)

Beneficios:
- Reduz ruido visual no `eap.html` (tabela em vez de 54 nos)
- Facilita estimativas (cada pacote tem mesma duracao baseline)
- Habilita gestao por "fila de pacotes" no `managing-action-plan`
(filtrar todos `x.y.3` para ver status do pacote DEIP)

## Pacotes vs acoes vs etapas

A WBS desta skill usa 3 tipos no `Cronograma.xlsx`:

| Tipo | Sinonimo PMI | Exemplo H1-02 | Caracteristicas |
|---|---|---|---|
| `Fase` | Phase | `1` Planejamento | Agregador temporal; sem dono operacional unico; sem entregavel direto |
| `Ação` | Work Package | `1.1` Elaborar TAP | Menor unidade com dono e entregavel; tem inicio/fim, criterio de aceite |
| `Etapas da Ação` | Activity / Task | `1.1.1` Definir escopo | Sub-tarefa operacional dentro de uma Acao |

**Pacote de trabalho** (PMI) = nossa **`Ação`**. E o nivel onde:
- Se atribui responsavel **unico** (uma pessoa)
- Se define entregavel concreto + criterio de aceite
- Se faz o handoff para `managing-action-plan` (vira task no ClickUp)

Etapas (`Etapas da Ação`) sao **detalhamento operacional** — facilitam
acompanhamento granular mas nao sao unidades de gestao primarias.

## Criterios de aceite por pacote

Cada `Ação` (pacote) deve ter no campo `Entregável`:

✅ **Documento concreto:** "Documento TAP aprovado pelo sponsor com escopo, objetivos e estrela guia"

✅ **Output mensuravel:** "Mapa N3 completo do processo Credito com SLAs definidos"

✅ **Aceite formal:** "Playbook submetido e validado pelo dono do processo"

❌ **NAO use:** "Bom", "OK", "Concluido", "Feito" (nao verificavel)

❌ **NAO use:** descricao do trabalho ("Mapear funis" — isso e o nome
da acao, nao o entregavel)

O `Entregável` e usado:
- No artefato `cronograma.html` (coluna direita)
- No `managing-action-plan` quando push para ClickUp (vira `description`
do task)
- Para QA quando o pacote e marcado `done` (validar que o entregavel
existe e atende o criterio)

## Anti-patterns

- **WBS por fase de tempo:** "Semana 1", "Semana 2" → use `inicio_plan` /
`fim_plan` para isso, nao a WBS
- **WBS por funcao:** "Trabalho do Bruno", "Trabalho do Filipe" → use
`Responsável`, nao a WBS
- **Profundidade > 5 niveis:** sinal de decomposicao excessiva ou de que
a WBS deveria ter sub-fases
- **Pacote sem entregavel concreto:** transforma o pacote em "trabalho
infinito"
- **Mais de 1 responsavel por pacote:** indica que o pacote precisa ser
quebrado em multiplos pacotes
- **Etapa sem pacote pai:** Etapa orfa nao tem contexto operacional —
sempre deve viver dentro de uma Acao
