# Directory Layout — Decisões de Design

Referência descritiva sobre **por que** a estrutura criada pela skill `initializing-project` é dessa forma. Esta doc é carregada sob demanda — só leia se precisar entender o racional ou se estiver customizando a skill.

## Índice

1. [Por que 4 pastas numeradas](#por-que-4-pastas-numeradas)
2. [Por que `_docs/` com prefixo underscore](#por-que-_docs-com-prefixo-underscore)
3. [Convenção de status report por data](#convenção-de-status-report-por-data)
4. [Nomenclatura do projeto](#nomenclatura-do-projeto)
5. [Quando renomear `<project-dir>`](#quando-renomear-project-dir)

---

## Por que 4 pastas numeradas

As pastas seguem o ciclo de vida clássico de um projeto, na ordem temporal de execução:

| # | Pasta | Fase PMI-like | O que vive aqui |
|---|---|---|---|
| 1 | `1-planning/` | Planejamento | Plano formal, WBS/EAP, cronograma, stakeholders, riscos, escopo |
| 2 | `2-development/` | Execução + M&C | Atas de reunião, entregáveis em andamento, artefatos intermediários, evidências |
| 3 | `3-conclusion/` | Encerramento | Termo de encerramento, lições aprendidas, aceite final |
| 4 | `4-status-report/` | Transversal | OPRs e apresentações executivas por data de reporte |

**Por que numerado (`1-`, `2-`, ...):**

- **Ordem visual consistente** — no finder/ls, as pastas aparecem na ordem cronológica do ciclo, não alfabética (`conclusion` < `development` < `planning` alfabeticamente seria o oposto do fluxo real)
- **Reforço pedagógico** — qualquer pessoa que abre o diretório entende "primeiro planejo, depois executo, depois fecho"
- **Índice de conversão** — fácil dizer "veja a pasta 3" em vez de "veja a pasta de encerramento"

**Por que exatamente essas 4:**

- `1-planning` e `3-conclusion` são fronteiras bem definidas no ciclo PMI (iniciação/planejamento e encerramento)
- `2-development` consolida execução + monitoramento/controle em uma pasta só — projetos M7 são pequenos/médios o suficiente para não precisar separá-los
- `4-status-report` é **transversal** ao ciclo (pode ter reportes em qualquer fase), mas ganha pasta própria porque é o artefato mais demandado por stakeholders externos e é gerado por uma skill dedicada (`generating-status-materials`)

---

## Por que `_docs/` com prefixo underscore

`_docs/` agrupa material de apoio que **não é fase do ciclo**: imagens, PDFs de referência, diagramas externos.

**Por que o underscore:**

- **Separação visual** — em listagem alfabética, `_docs/` cai separado das pastas numeradas (antes ou depois dependendo do sistema), sinalizando visualmente "isto não é fase"
- **Convenção "pasta de apoio"** — padrão comum em repositórios para indicar conteúdo auxiliar (similar a `_site/`, `_build/`, `_vendor/`)

Subestrutura:

- `_docs/assets/` — imagens, diagramas, screenshots (usados em docs do projeto)
- `_docs/bibliography/` — PDFs, artigos, links para referências externas

---

## Convenção de `4-status-report/` — arquivos live + snapshots por data

A pasta `4-status-report/` hospeda **dois tipos de conteúdo**:

```
4-status-report/
├── Cronograma.xlsx              # LIVE — gerenciado por managing-action-plan
├── changelog.md                 # LIVE append-only — espelha mutações + comentários
├── .sync-state.json             # Sidecar com baselines + last_sync_hash
├── 2026-04-25/                  # Snapshot do reporte daquela data
│   ├── OPR.pdf
│   └── apresentacao.pptx
├── 2026-05-02/                  # Próximo reporte
│   ├── OPR.pdf
│   └── apresentacao.pptx
└── 2026-06-13/
    └── ...
```

**Arquivos LIVE na raiz da pasta:**
- `Cronograma.xlsx` — cópia da baseline (`1-planning/Cronograma.xlsx`) feita pela skill `managing-action-plan` na primeira rodada. Cresce/muda continuamente: novas ações, status atualizado, datas reais, etc. Sincronizada com ClickUp via three-way diff.
- `changelog.md` — append-only. Toda mutação (create/update/delete/comment/sync) gera entry. Comentários do ClickUp são espelhados aqui também.
- `.sync-state.json` — sidecar com baselines per-row + last_sync_hash. **Não editar manualmente.**

**Subpastas dated `YYYY-MM-DD/` — snapshots por reporte:**
- Cada reunião de status report gera uma subpasta nova com `OPR.pdf` + `apresentacao.pptx` daquele dia
- Snapshots são **imutáveis** — preservam o histórico ("o que mostramos em abril?" tem caminho óbvio)
- O `Cronograma.xlsx` live continua na raiz; não é copiado para cada snapshot (a apresentação já tem a foto da estrutura naquele momento)
- Ordenação natural ISO 8601 nos finders

**Quem mexe em quê:**
| Arquivo / pasta | Quem mantém |
|---|---|
| `Cronograma.xlsx` (raiz) | `managing-action-plan` |
| `changelog.md` | `managing-action-plan` |
| `.sync-state.json` | `managing-action-plan` |
| `YYYY-MM-DD/` (snapshots) | `generating-status-materials` |

---

## Nomenclatura do projeto

Regras aplicadas pela skill ao normalizar `project_name`:

| Regra | Motivo | Exemplo |
|---|---|---|
| `kebab-case` (hífen, minúsculas) | Compatibilidade com URLs, shell, git | `padronizacao-rituais` |
| Sem acentos | Evita bugs em paths cross-platform (iCloud, macOS HFS, Linux) | `padronizacao` não `padronização` |
| Sem caracteres especiais (`[^a-z0-9-]`) | Shell-safe; evita escape em scripts | rejeita `m7!rituais`, aceita `m7-rituais` |
| Máximo 40 caracteres | Paths longos quebram em alguns sistemas; nome longo sinaliza escopo mal-definido | truncar `modernizacao-da-gestao-dos-indicadores-comerciais-m7` → `modernizacao-gestao-indicadores` |
| Prefer substantivo (não verbo) | Nome descreve o **projeto**, não a ação | `revisao-funil-captacao` (substantivo) em vez de `revisar-funil-captacao` (verbo) |

Nome ruim vs bom:

- ❌ `projeto` (genérico), `revisar-tudo` (verbo + vago), `Reestruturação_M7!` (acento, caixa, especial)
- ✅ `reestruturacao-m7`, `desdobramento-metas-2026`, `comissionamento-q2`

---

## Quando renomear `<project-dir>`

**Evite renomear** depois da criação. Se precisar:

1. **Antes de qualquer integração** (ClickUp, cross-refs de outros projetos): rename é seguro, basta atualizar `{{project_name}}` em `CLAUDE.md` e `BRIEFING.md`.

2. **Depois de `managing-action-plan` rodar** (ClickUp já conectado): o `clickup_list_id` em `CLAUDE.md` não muda, mas:
   - Qualquer documento externo que cite o caminho antigo vai quebrar
   - Referências cruzadas `[[nome-antigo]]` em outros arquivos do vault precisam ser atualizadas manualmente
   - Faça um `grep -r '<nome-antigo>'` no vault antes de confirmar

3. **Depois de gerar status reports**: baixo impacto (PDFs/PPTX não têm paths relativos embutidos), mas verifique se algum OPR linka de volta para o projeto.

**Alternativa mais segura:** mantenha o nome antigo do diretório e use um campo `display_name` no BRIEFING para rebatizar externamente.
