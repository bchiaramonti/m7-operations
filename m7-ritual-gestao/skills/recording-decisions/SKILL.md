---
name: recording-decisions
description: >-
  G2.3-E5: Registra decisoes pos-ritual em ata estruturada (MD), prioriza contramedidas
  por impacto (volume/receita) e atualiza plano-de-acao.csv com novas acoes (append) ou
  status modificados (edit). Garante rastreabilidade: decisao no ritual -> ata -> acao no
  CSV -> acompanhamento no proximo WBR. Use when the pipeline advances to E5 after the
  ritual, when /m7-ritual-gestao:next reaches E5, or when the user shares post-ritual notes.

  <example>
  Context: Ritual concluido, pipeline avanca para registro de decisoes
  user: "/m7-ritual-gestao:next"
  assistant: Solicita notas do ritual, gera ata estruturada, registra contramedidas no CSV
  </example>

  <example>
  Context: Usuario compartilha notas do ritual diretamente
  user: "Registra as decisoes do ritual de Investimentos de hoje: [notas...]"
  assistant: Gera ata MD, prioriza contramedidas, faz append no plano-de-acao.csv
  </example>
user-invocable: false
---

# Recording Decisions — Registro de Decisoes Pos-Ritual (E5)

> "Decisao sem registro e conversa. Registro sem acao e burocracia."

Esta skill recebe notas do ritual (formato livre), gera ata estruturada em MD, prioriza contramedidas por impacto financeiro e registra novas acoes no plano-de-acao.csv — ou atualiza acoes existentes mencionadas no ritual. E a etapa E5 do processo G2.3.

> **REGRA DE HANDOFF**: Ao invocar o agente decision-recorder, NAO passe valores de dados no texto do prompt. Passe APENAS caminhos de arquivos (vertical, cycle folder, paths dos artefatos). O decision-recorder deve usar Read tool para carregar os dados dos arquivos em disco.

## Dependencias Internas

| Recurso | Caminho | Tipo |
|---------|---------|------|
| Schema CSV (24 campos) | [references/csv-schema.md](references/csv-schema.md) | Referencia |
| Regras de priorizacao e duplicatas | [references/prioritization-rules.md](references/prioritization-rules.md) | Referencia |
| Template da ata | [templates/ata-ritual.tmpl.md](templates/ata-ritual.tmpl.md) | Template |
| Template HTML da ata | [templates/ata-ritual.tmpl.html](templates/ata-ritual.tmpl.html) | Template |
| Linha-modelo CSV | [templates/acao-template.tmpl.csv](templates/acao-template.tmpl.csv) | Template |
| Guia de geracao HTML | [references/ata-html-guide.md](references/ata-html-guide.md) | Referencia |
| Script HTML→PDF | scripts/html-to-pdf.js (requer `npm install` em scripts/) | Script |
| Agent executor | `decision-recorder` (agents/decision-recorder.md) | Agent |
| Card de Performance | `{CARDS_DIR}/{Vertical}/card_*.yaml` | Contexto externo |
| WBR (contexto) | `Glob('**/output/*/wbr-*.md')` | Externo |
| plano-de-acao.csv | `Glob('**/03-implementacao/plano-de-acao.csv')` | Externo |

## Pre-requisitos (Entry Criteria)

- Card de Performance da vertical localizado em `{CARDS_DIR}/{Vertical}/card_*.yaml`
- Ritual realizado (confirmacao do usuario ou flag em CICLO.md)
- WBR da semana disponivel para contexto
- `plano-de-acao.csv` acessivel em `03-implementacao/`
- CICLO.md com `vertical` e `data_referencia` definidos

## Workflow

### Fase 1 — Coletar Contexto

1. **Localizar e ler Card de Performance** da vertical:
   - `CARDS_DIR` = `~/Library/CloudStorage/OneDrive-MULTI7CAPITALCONSULTORIALTDA/desempenho/02-Controle/Cards-de-Performance`
   - Glob para `{CARDS_DIR}/{Vertical}/card_*.yaml` (ignorar `_Historico/`)
   - Extrair do card: responsaveis (especialistas), KPIs monitorados com `criterio_desvio_critico`, estrutura organizacional (N1-N5), e `logica_de_analise` (sequencia de 7 passos)
   - Se nenhum card encontrado: avisar usuario e prosseguir sem contexto organizacional
2. **Localizar CSV** via `Glob('**/03-implementacao/plano-de-acao.csv')`
3. **Ler CSV completo** respeitando encoding UTF-8 e delimitador `,` (campos entre aspas duplas)
4. **Tratar campo `comentarios`**: contem JSON inline — parsear como string JSON
5. **Localizar WBR** mais recente da vertical via `Glob('**/output/*/wbr-*.md')` (contexto dos desvios discutidos)
6. **Ler templates**: `templates/ata-ritual.tmpl.md` e `templates/acao-template.tmpl.csv`
7. **Solicitar notas** do ritual ao usuario (se nao fornecidas no input)

Notas aceitas em formato livre. Extrair: participantes, decisoes, contramedidas, responsaveis, prazos, escalonamentos.

### Fase 2 — Gerar Ata Estruturada

1. Parsear notas do usuario (formato livre aceito)
2. Extrair e categorizar:
   - **Decisoes**: itens decididos no ritual (ex: "aprovado novo processo de X")
   - **Contramedidas**: acoes corretivas com responsavel e prazo
   - **Escalonamentos**: itens que precisam de decisao do N1
   - **Proximos passos**: tarefas gerais com responsavel e prazo
3. Numerar decisoes sequencialmente: D-001, D-002, D-003...
4. Preencher template [ata-ritual.tmpl.md](templates/ata-ritual.tmpl.md) com dados extraidos
5. **Salvar ata** via Write em `output/{vertical}/ata-ritual-{data}.md`

> **Nota**: Os IDs de acao na ata (coluna "ID CSV") serao preenchidos como `PA-XXXX-XXX` nesta fase e atualizados com IDs reais na Fase 6.

### Fase 3 — Priorizar Contramedidas

Para cada contramedida definida no ritual, aplicar as regras de [references/prioritization-rules.md](references/prioritization-rules.md):

1. Identificar `indicador_impactado` (cruzar com WBR se usuario nao informou)
2. Coletar `volume` e `receita` estimados (do usuario ou inferidos do WBR)
3. Atribuir prioridade conforme tabela de priorizacao (critica/alta/media/baixa)
4. Ordenar contramedidas: critica > alta > media > baixa; desempate por receita desc

### Fase 4 — Verificar Duplicatas

Aplicar regras de deteccao de duplicatas conforme [references/prioritization-rules.md](references/prioritization-rules.md). Usar `Grep` para busca eficiente no CSV. Se duplicata encontrada: NAO inserir, informar ao usuario, e registrar na secao "Duplicatas Detectadas" da ata.

### Fase 5 — Registrar no plano-de-acao.csv

Seguir integralmente as regras de [references/csv-schema.md](references/csv-schema.md) para inserir novas acoes (append) e atualizar existentes (edit).

**Resumo operacional:**

#### 5a. Novas acoes (append)

1. Determinar proximo ID sequencial (PA-YYYY-NNN+1)
2. Preencher todos os 24 campos conforme [csv-schema.md](references/csv-schema.md) — ver tabela "Valores por campo"
3. Inserir ao final do CSV usando Edit tool
4. Template de referencia: [acao-template.tmpl.csv](templates/acao-template.tmpl.csv)

#### 5b. Acoes existentes mencionadas (update)

1. Localizar linha exata via Grep + Read (confirmar numero da linha antes de editar)
2. Atualizar campos permitidos: `status`, `percentual`, `comentarios`, `ultima_atualizacao`, `data_conclusao`
3. Para `comentarios`: APPEND ao JSON array existente — nunca substituir (ver formato em csv-schema.md)

### Fase 5.5 — Gerar Ata HTML e PDF

Com base na ata MD ja validada (Fase 2) e nos dados registrados (Fase 5), gerar a versao visual HTML e converter para PDF.

#### 5.5a. Gerar HTML

1. **Ler template** [templates/ata-ritual.tmpl.html](templates/ata-ritual.tmpl.html) via Read tool
2. **Copiar CSS inteiro** (bloco `<head>`) sem alteracoes — CSS M7-2026 imutavel, Score A
3. **Substituir placeholders** `{{...}}` com dados reais da ata (decisoes, contramedidas, acoes atualizadas, proximos passos, resumo quantitativo)
4. **Montar componentes visuais** seguindo [references/ata-html-guide.md](references/ata-html-guide.md):
   - Timeline para decisoes (D-001, D-002...) com dot azul
   - Tabela com badges de prioridade para contramedidas
   - Tabela before/after para acoes atualizadas
   - Timeline para proximos passos com dot caqui
   - KPI cards para resumo quantitativo
   - Callout-alert para escalonamentos (se houver)
   - Decisao-critica box para decisoes criticas (se houver)
5. **Omitir secoes vazias** — se nao ha escalonamentos, omitir secao inteira; se nao ha duplicatas, omitir callout
6. **Validar** que todos os numeros conferem com a ata MD
7. **Salvar** em `output/{vertical}/ata-ritual-{data}.html`

**Regras**:
- CSS do template e imutavel (M7-2026 design system, score A)
- Logo M7 embeddado como base64 no template — nao alterar
- Nao gerar graficos SVG (ata e dados estruturados, nao analiticos)
- Nenhum placeholder `{{...}}` deve restar no HTML final

#### 5.5b. Gerar PDF

1. **Verificar dependencias**: Se `scripts/node_modules` nao existe, executar:
   ```bash
   cd {SKILL_DIR}/scripts && npm install
   ```
2. **Gerar PDF** via Bash:
   ```bash
   node {SKILL_DIR}/scripts/html-to-pdf.js \
     {cycle_folder}/output/{vertical}/ata-ritual-{data}.html \
     {cycle_folder}/output/{vertical}/ata-ritual-{data}.pdf
   ```
3. **Verificar** que o PDF foi gerado com sucesso
4. Se falhar: registrar em CICLO.md > Anomalias como WARNING (PDF e complementar, nao bloqueia pipeline)

### Fase 6 — Finalizar e Validar

1. **Reler CSV** apos edicoes para confirmar integridade (nenhuma linha corrompida)
2. **Verificar** que todas as 24 colunas estao presentes em cada linha editada/adicionada
3. **Atualizar ata MD** com IDs definitivos das acoes (substituir `PA-XXXX-XXX` por IDs reais)
4. **Atualizar ata HTML** com IDs definitivos (mesma substituicao no HTML gerado na Fase 5.5)
5. **Atualizar CICLO.md**: G2.3 E5 = concluido
6. **Exibir resumo** ao usuario:
   - X decisoes registradas
   - Y contramedidas novas (listar IDs)
   - Z acoes atualizadas (listar IDs)
   - W duplicatas detectadas (se houver)

## Exit Criteria

- [ ] Ata gerada em `output/{vertical}/ata-ritual-{data}.md` com campos obrigatorios (participantes, decisoes, contramedidas)
- [ ] IDs de acao unicos e sequenciais (nao reutiliza IDs existentes)
- [ ] CSV atualizado sem corromper linhas existentes (encoding preservado)
- [ ] Priorizacao documentada com justificativa (volume/receita)
- [ ] Nenhuma contramedida duplicada inserida (verificacao executada)
- [ ] Campo `comentarios` atualizado como JSON array (append, nao substituicao)
- [ ] CICLO.md atualizado (G2.3 E5 = concluido)
- [ ] Ata HTML gerada em `output/{vertical}/ata-ritual-{data}.html` com CSS M7-2026 inalterado
- [ ] HTML contem timeline de decisoes, tabela de contramedidas com badges, KPI cards de resumo
- [ ] Numeros no HTML identicos a ata MD (resumo quantitativo, IDs, contagens)
- [ ] Nenhum placeholder `{{...}}` remanescente no HTML final
- [ ] PDF gerado em `output/{vertical}/ata-ritual-{data}.pdf` (WARNING se falhar, nao bloqueia)

## Anti-Patterns

1. **NUNCA insira acao sem verificar duplicatas** — sempre executar Fase 4 antes de Fase 5
2. **NUNCA gere ata sem numeros de decisao** (D-NNN) — toda decisao deve ser numerada e rastreavel
3. **NUNCA infira prioridade sem criterio** — usar regras de [references/prioritization-rules.md](references/prioritization-rules.md)
4. **NUNCA edite linha do CSV sem antes localizar via Grep** — confirmar numero da linha antes de usar Edit
5. Para regras completas de integridade do CSV, ver [references/csv-schema.md](references/csv-schema.md)
