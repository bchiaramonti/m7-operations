---
name: preparing-materials
description: >-
  G2.3-E2: Generates ritual materials (HTML deck + Briefing MD) from the WBR
  produced by m7-controle. Orchestrates material-generator agent to build a
  per-specialist HTML presentation and a consultant-style briefing for the
  ritual conductor. Use when /m7-ritual-gestao:prepare-ritual is invoked or
  when G2.3 E2 is the current pipeline step.

  <example>
  Context: WBR da vertical concluido (m7-controle E6 = completo no CICLO.md)
  user: "/m7-ritual-gestao:prepare-ritual consorcios"
  assistant: Locates the latest WBR, delegates to material-generator, produces HTML + briefing
  </example>
user-invocable: false
---

# Preparar Materiais Pre-Ritual (G2.3-E2)

Transforma o WBR em materiais consumiveis pelo gestor: um **HTML autocontido** (deck de slides para projecao e impressao PDF) e um **briefing MD** (guia de preparacao do condutor).

> **Principio:** O WBR e a unica fonte de verdade. HTML e briefing sao derivacoes visuais e textuais — nenhum numero e calculado ou inventado nesta etapa.

---

## Dependencias

| Recurso | Caminho | Tipo |
|---------|---------|------|
| Regras de slides | [references/slide-structure.md](references/slide-structure.md) | Referencia |
| Regras de briefing | [references/briefing-structure.md](references/briefing-structure.md) | Referencia |
| Template HTML ritual | [templates/ritual.tmpl.html](templates/ritual.tmpl.html) | Template |
| Template briefing | [templates/ritual-briefing.tmpl.md](templates/ritual-briefing.tmpl.md) | Template |
| Card de Performance | `{CARDS_DIR}/{Vertical}/card_*.yaml` | Contexto externo |
| Agent executor | `material-generator` (agents/material-generator.md) | Agent |

---

## Entry criteria

Antes de iniciar, verificar:

- [ ] Card de Performance da vertical localizado em `{CARDS_DIR}/{Vertical}/card_*.yaml`
- [ ] CICLO.md existe no cycle folder e E6 (consolidating-wbr) esta marcado como concluido
- [ ] WBR estruturado disponivel em `{cycle_folder}/wbr/wbr-{vertical}-{data}.md`

Se qualquer criterio falhar, interrompa e reporte ao usuario.

---

## Workflow

### Fase 1 — Localizar Card de Performance e WBR

> **Card ANTES do WBR:** O Card define QUEM sao os especialistas e QUAIS indicadores importam. Essa informacao deve guiar a leitura do WBR, nao o contrario.

1. Receber o nome da `vertical` como argumento (ex: "consorcios", "investimentos")
2. **Localizar e ler Card de Performance** da vertical (PRIMEIRO):
   - Mapear vertical → codigo: consorcios=`Consorcios`, investimentos=`Investimentos`, credito=`Credito`, seguros=`Seguros`, universo=`Universo`
   - Glob para `{CARDS_DIR}/{Vertical}/card_*.yaml` (ignorar `_Historico/`)
   - Se nenhum card encontrado: avisar usuario `"Card de Performance nao encontrado para {vertical}. Materiais serao gerados sem contexto organizacional."` e prosseguir
   - Se encontrado: armazenar caminho como `CARD_PATH`
   - Read o Card → extrair lista de especialistas (nomes, IDs), KPI references, logica de analise, distribuicao
3. Localizar o cycle folder mais recente:
   - Glob para `**/wbr/wbr-{vertical}-*.md` nos diretorios de output
   - Selecionar o mais recente por data no nome do arquivo
4. Read CICLO.md do cycle folder
5. Confirmar que E6 (consolidating-wbr) esta completo
6. Extrair metadados: `vertical`, `data`, `checkpoint_label`

### Fase 2 — Resolver caminhos

Montar os caminhos absolutos necessarios:

```
WBR_PATH        = {cycle_folder}/wbr/wbr-{vertical}-{data}.md
CYCLE_FOLDER    = {cycle_folder}/
CARDS_DIR       = ~/Library/CloudStorage/OneDrive-MULTI7CAPITALCONSULTORIALTDA/desempenho/02-Controle/Cards-de-Performance
CARD_PATH       = {CARDS_DIR}/{Vertical}/card_*.yaml  (resolvido na Fase 1)
DADOS_PATH      = {cycle_folder}/dados/dados-consolidados-{vertical}.json
SKILL_DIR       = {plugins_dir}/m7-ritual-gestao/skills/preparing-materials
OUTPUT_DIR      = {cycle_folder}/output/{vertical}
```

> `DADOS_PATH` e o JSON consolidado do m7-controle (E2) com dados hierarquicos N1→N5. Usado pelo material-generator para quebras granulares (por assessor, equipe, squad) nos slides de Analise e Projecao. Se o arquivo nao existir, o agente usa o WBR narrativo como fallback.

Verificar que cada caminho existe (`ls`).

### Fase 3 — Delegar ao material-generator

**Regra de handoff:** Passar APENAS caminhos de arquivos ao agent. NUNCA passar dados, numeros ou conteudo do WBR no prompt de delegacao.

Invocar o agent `material-generator` com o seguinte prompt:

```
Gere os materiais do ritual para a vertical {vertical}, ciclo {data}.

Caminhos:
- WBR_PATH: {WBR_PATH}
- CARD_PATH: {CARD_PATH}
- DADOS_PATH: {DADOS_PATH}  (JSON consolidado para quebras N3/N4/N5 — opcional)
- CYCLE_FOLDER: {CYCLE_FOLDER}
- SKILL_DIR: {SKILL_DIR}
- OUTPUT_DIR: {OUTPUT_DIR}

Siga o processo descrito no seu system prompt.
Leia o Card de Performance em CARD_PATH PRIMEIRO — extraia kpi_references[] para definir indicadores.
A Secao 1.5 (Painel de Indicadores) do WBR e a UNICA fonte para o Slide 2 (Matriz) e Dashboards.
Se DADOS_PATH existir, use o JSON consolidado para quebras por assessor (N5) nos slides Analise e Projecao.
Leia as references em {SKILL_DIR}/references/ para regras detalhadas.
Use os templates em {SKILL_DIR}/templates/ como base.
```

> Se `CARD_PATH` nao foi encontrado na Fase 1, omitir a linha do prompt e prosseguir sem card.

O agent executara:
1. Ler Card e WBR, extrair dados por especialista
2. Gerar HTML autocontido com blocos por especialista
3. Gerar briefing (guia do condutor)
4. Validar outputs

### Fase 4 — Verificar outputs

Apos o agent concluir, verificar:

| Verificacao | Como |
|-------------|------|
| HTML existe | `ls {OUTPUT_DIR}/ritual-{vertical}-{data}.html` |
| Briefing existe | `ls {OUTPUT_DIR}/briefing-{vertical}-{data}.md` |
| HTML tem slides | Grep por `slide-wrapper` no HTML (minimo 14 para 2 especialistas) |
| Briefing completo | Read briefing e verificar que as 5 secoes nao estao vazias |
| Dados consistentes | Spot-check: comparar 3 valores entre WBR e HTML |
| Font sizes compliant | Grep `font-size: [1-7]px` no HTML → deve retornar 0 matches |
| Cores on-brand | Grep `#2C3E50\|#D0D0D0\|#BDBDBD\|#F0F0F0\|#F5F5F5\|#9E9E9E\|#BDC3C7\|#3498DB\|#E74C3C\|#27AE60` → 0 matches |
| Sem bold keyword | Grep `font-weight: bold` no conteudo dos iframes → 0 matches |
| Lime nao como texto | Sem `color: #eef77c` em elementos sobre fundo claro (#fffdef) |

### Fase 5 — Atualizar CICLO.md

Adicionar ou atualizar a secao G2.3 no CICLO.md:

```markdown
## G2.3 — Rituais de Gestao

| Etapa | Status | Timestamp |
|-------|--------|-----------|
| E2 — Preparar Materiais | concluido | {timestamp} |
| E3 — Distribuir Materiais | pendente | — |
| E5 — Registrar Decisoes | pendente | — |
```

---

## Exit criteria

- [ ] `ritual-{vertical}-{data}.html` gerado em `{OUTPUT_DIR}/`
- [ ] `briefing-{vertical}-{data}.md` gerado em `{OUTPUT_DIR}/`
- [ ] HTML com blocos por especialista (1 bloco por especialista do Card)
- [ ] Briefing com todas as 5 secoes preenchidas
- [ ] Dados no HTML e briefing identicos ao WBR (single source of truth)
- [ ] CSS compliance: 0 fontes < 8px, 0 cores fora da paleta, 0 `font-weight: bold`
- [ ] CICLO.md atualizado com G2.3 E2 = concluido

---

## Outputs

| Output | Formato | Caminho |
|--------|---------|---------|
| Apresentacao do Ritual | HTML | `{OUTPUT_DIR}/ritual-{vertical}-{data}.html` |
| Briefing do Ritual | MD | `{OUTPUT_DIR}/briefing-{vertical}-{data}.md` |

---

## Anti-patterns

- **NUNCA re-analise dados** — O WBR ja contem toda a analise. Esta skill traduz, nao analisa.
- **NUNCA passe dados no prompt do agent** — Passe caminhos. O agent deve Read os arquivos.
- **NUNCA organize slides por KPI** — O ritual e organizado por especialista.
- **NUNCA pule um especialista do Card** — Todos devem ter bloco de slides.
- **NUNCA use cores fora da paleta** — Usar apenas cores documentadas em slide-structure.md.

---

## Recursos adicionais

- Para regras detalhadas de cada slide: [references/slide-structure.md](references/slide-structure.md)
- Para regras de conteudo do briefing: [references/briefing-structure.md](references/briefing-structure.md)
- Para o template HTML: [templates/ritual.tmpl.html](templates/ritual.tmpl.html)
- Para o template do briefing: [templates/ritual-briefing.tmpl.md](templates/ritual-briefing.tmpl.md)
