# Schema formal do PLANEJAMENTO.md

Define estrutura obrigatória do arquivo `<project-dir>/1-planning/PLANEJAMENTO.md`. Esta reference é a **fonte de verdade** para regras de parsing — `building-project-plan` depende de que o MD siga este schema à risca.

## Índice

- [Arquivo e localização](#arquivo-e-localização)
- [Frontmatter YAML](#frontmatter-yaml)
- [Aviso de snapshot (após FINAL)](#aviso-de-snapshot-após-final)
- [Headers de nível 2 — âncoras fixas](#headers-de-nível-2--âncoras-fixas)
- [Markers de status](#markers-de-status)
- [Sub-headers e conteúdo](#sub-headers-e-conteúdo)
- [Tabelas e listas](#tabelas-e-listas)
- [Mapeamento seção → artefato HTML](#mapeamento-seção--artefato-html)
- [Regras de parsing esperadas](#regras-de-parsing-esperadas)

## Arquivo e localização

- Caminho fixo: `<project-dir>/1-planning/PLANEJAMENTO.md`
- Um projeto, um MD — nunca múltiplos arquivos
- Encoding: UTF-8, LF (unix)

## Frontmatter YAML

Obrigatório no topo. Campos:

```yaml
---
projeto: "Padronizacao dos Rituais de Gestao M7"     # nome legível
codigo: "H1-02"                                       # código do portfólio (opcional se não houver)
lider: "Bruno Chiaramonti"                            # líder operacional
sponsor: "Felipe Brasil"                              # patrocinador executivo
inicio: "2026-03-01"                                  # ISO-8601
fim: "2026-09-30"                                     # ISO-8601
planejamento_status: "DRAFT"                          # DRAFT | FINAL
finalizado_em: ""                                     # YYYY-MM-DD quando FINAL, vazio antes
consistency_overrides: []                             # opcional — lista de inconsistências cross-artefato aceitas conscientemente na Fase 3
---
```

Regras:
- **Datas** sempre em ISO-8601 (`YYYY-MM-DD`). Nunca `dd/mm/yyyy`.
- **Strings** sempre entre aspas duplas para evitar ambiguidade YAML
- **`planejamento_status`** só assume dois valores: `DRAFT` (em elaboração, mesmo se todas seções ACCEPTED mas usuário não finalizou) ou `FINAL` (carimbado, snapshot estático)
- **`finalizado_em`** só é preenchido quando `planejamento_status` vira `FINAL`
- **`consistency_overrides`** é **opcional**; presente apenas quando Fase 3 detectou inconsistências e o usuário decidiu finalizar sem resolver. Formato: lista YAML de strings (cada string é uma justificativa de uma inconsistência aceita). Quando não há overrides, pode ser omitido ou declarado como lista vazia `[]`. O parser de `building-project-plan` deve tratar ausência do campo como equivalente a lista vazia.
- Campos opcionais podem ser omitidos; não usar `null`, usar string vazia `""` ou lista vazia `[]`

**Exemplo com `consistency_overrides` preenchido:**

```yaml
---
projeto: "..."
planejamento_status: "FINAL"
finalizado_em: "2026-04-18"
consistency_overrides:
  - "R3 owner genérico 'time de dados' aceito — time ainda sem líder nomeado, owner nominal será atribuído em 2026-05"
  - "KR 1.1 (NPS) sem suporte no WBS aceito — medição será externa ao projeto via pesquisa corporativa trimestral"
---
```

## Aviso de snapshot (após FINAL)

Logo após o frontmatter, quando o MD for finalizado, a skill adiciona:

```markdown
> **⚠️ Snapshot de planejamento inicial.** Este documento reflete o pensamento
> do projeto em {{finalizado_em}}. Para estado atual do plano, ver
> [plano-projeto.html](plano-projeto.html) e para estado das ações ver
> [../4-status-report/Cronograma.xlsx](../4-status-report/Cronograma.xlsx).
> **Este MD NÃO é atualizado após a geração dos artefatos.**
```

Enquanto `DRAFT`, este bloco **não** deve estar presente — adicionar apenas na transição para `FINAL`.

## Headers de nível 2 — âncoras fixas

O schema depende de que cada seção tenha header `##` no formato **exato**:

```
## 01 · Contexto & Escopo
## 02 · OKRs
## 03 · WBS/EAP
## 04 · Cronograma
## 05 · Roadmap & Marcos
## 06 · Recursos & Dependências
## 07 · Plano de Comunicação
## 08 · Riscos
## 09 · Calendário
```

Regras estritas:
- Prefixo numérico `NN` com zero à esquerda (`01`, não `1`)
- Separador `·` (middle dot U+00B7), com espaços antes e depois
- Nome do artefato em Title Case conforme lista acima
- Não traduzir, não abreviar, não reordenar os números

**Regex de parsing** (usado por `parse_planejamento_md.py` em `building-project-plan`):

```python
r'^## (\d\d) · (.+)$'  # multiline; captura número e nome
```

Se qualquer header divergir do schema, o parser falhará. Por isso o template já vem com os headers corretos — a skill **não deve** permitir que o usuário renomeie seções.

## Markers de status

Imediatamente após cada header `##`, uma linha HTML comment:

```html
<!-- STATUS: PENDING -->
<!-- STATUS: DRAFT | 2026-04-18 -->
<!-- STATUS: ACCEPTED | 2026-04-18 -->
<!-- STATUS: SKIPPED | 2026-04-18 -->
```

Regras:
- **PENDING**: estado inicial, sem data (ainda não foi tocado)
- **DRAFT**, **ACCEPTED**, **SKIPPED**: obrigatório acompanhar data ISO da última mudança, separada por ` | `
- Só um marker por seção; atualizar in-place, não empilhar

**Markers auxiliares** (quando aplicáveis, na linha logo após o STATUS):

```html
<!-- REASON: Projeto interno sem stakeholders externos, não se aplica. -->
<!-- OVERRIDE: Aceito com 4 KRs por objetivo porque... -->
```

- `REASON:` — obrigatório quando status = `SKIPPED`
- `OVERRIDE:` — obrigatório quando usuário sobrescreve push-back (registro de por que aceitou apesar de falhar critério)

## Sub-headers e conteúdo

- **Sub-headers `###`** podem variar conforme o conteúdo — não há schema estrito além do nível 2
- Recomenda-se seguir os sub-headers do [template](../templates/PLANEJAMENTO.tmpl.md) para máxima compatibilidade com os handlers de `building-project-plan`
- Conteúdo em prosa, bullets, tabelas, ou combinação — usar o que fizer sentido para o artefato

## Tabelas e listas

- Formato Markdown padrão (pipes `|` + separator `---`)
- Para WBS, usar listas aninhadas com 2 espaços de indentação por nível
- Não misturar tabelas HTML com Markdown — o parser só lê Markdown

Exemplo de tabela bem-formada (Riscos §08):

```markdown
| # | Descrição | Tipo | Prob | Impacto | Trigger | Estratégia | Contramedida | Owner |
|---|---|---|---|---|---|---|---|---|
| R1 | Atraso no acesso ao dataset | Ameaça | Alta | Alto | Handoff de dados atrasa ≥5 dias | Mitigate | Escalonar a Felipe semana 3 | Bruno |
```

Exemplo de WBS bem-formado (§03):

```markdown
- **1 Planejamento**
  - 1.1 Definição de escopo (entregável: scope doc; resp.: líder)
  - 1.2 Alinhamento de stakeholders
    - 1.2.1 Entrevistas individuais
    - 1.2.2 Workshop consolidação
```

## Mapeamento seção → artefato HTML

Quando `building-project-plan` operar em modo `read-md`, este é o mapa de extração:

| Seção MD | Artefato gerado |
|---|---|
| Frontmatter YAML | Hero da landing `plano-projeto.html` |
| `## 01 · Contexto & Escopo` | `artefatos/contexto-escopo.html` |
| `## 02 · OKRs` | `artefatos/okrs.html` |
| `## 03 · WBS/EAP` | `artefatos/eap.html` |
| `## 04 · Cronograma` | `artefatos/cronograma.html` + linhas do `Cronograma.xlsx` |
| `## 05 · Roadmap & Marcos` | `artefatos/roadmap-marcos.html` |
| `## 06 · Recursos & Dependências` | `artefatos/recursos-dependencias.html` |
| `## 07 · Plano de Comunicação` | `artefatos/plano-comunicacao.html` |
| `## 08 · Riscos` | `artefatos/riscos.html` |
| `## 09 · Calendário` | `artefatos/calendario.html` |

Seções `SKIPPED` resolvidas por skill 03: placeholder visível ou omissão do nav-grid (configurável).

## Regras de parsing esperadas

Assumir que `building-project-plan` usará:

1. **YAML parser** para o frontmatter (extrai metadados)
2. **Regex `^## (\d\d) · (.+)$`** (multiline) para identificar seções
3. **Remoção do marker `<!-- STATUS: ... -->`** antes de passar conteúdo para handlers
4. **Separação por status**: seções `ACCEPTED` vão para handlers; `SKIPPED` para fallback
5. **Tabelas Markdown** parseadas por handlers específicos de cada artefato

Se a skill `planning-project` gerar MD que quebra qualquer uma dessas suposições, a skill 03 falhará com erro de parsing. Por isso: **respeitar rigorosamente o schema**.
