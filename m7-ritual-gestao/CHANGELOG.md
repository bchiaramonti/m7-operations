# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.7.2] - 2026-04-06

### Fixed
- Removed invalid `skills` and `agents` declarations from plugin.json that used bare names instead of paths, breaking Claude's component auto-discovery

## [1.7.1] - 2026-04-01

### Added
- **Acesso ao JSON consolidado do m7-controle** (`DADOS_PATH`): O material-generator agora pode ler `dados-consolidados-{vertical}.json` para quebras granulares por assessor (N5), equipe (N3) e squad (N4) nos slides Analise e Projecao
- Fontes de dados formalizadas no `slide-structure.md` para cada tipo de slide (Painel vs JSON vs WBR narrativo)
- Fallback graceful: se JSON indisponivel, usa WBR narrativo (comportamento anterior)

### Fixed
- Font sizes das barras divergentes no slide Analise: 7px → 8px (respeitando minimo absoluto)

## [1.7.0] - 2026-04-01

### Added
- **Regras CSS Obrigatorias no material-generator**: Paleta de cores exaustiva (15 tokens), escala tipografica (min 8px), espacamento grid 4px, validacao grep pos-geracao
- **Indicadores derivados do Card**: Slide 2 (Matriz) e Dashboards agora derivam indicadores de `kpi_references[]` do Card via Secao 1.5 do WBR (contrato com m7-controle v5.3.0)
- Secao "Valores CSS Mandatorios" no `slide-structure.md` com allowlist e tabela de mapeamento
- 8 novos anti-patterns no material-generator (CSS compliance, indicadores dinamicos)
- 6 novas metricas de qualidade (font compliance, cores on-brand, indicadores = Card)
- 4 validacoes CSS nos exit criteria da skill `preparing-materials`

### Changed
- **Fluxo invertido**: Fase 1 agora localiza Card ANTES do WBR (Card define estrutura, WBR fornece dados)
- **Template HTML corrigido**: Fontes maiores (meta 6→8px, body 9→10px), cores 100% on-brand M7-2026, `font-weight: bold` → numerico, `line-height: 1.4` em todos os slides, lime como badge (nao texto) na agenda
- **Indicadores nao mais hardcoded**: `slide-structure.md` referencia `kpi_references[]` do Card em vez de listar indicadores fixos
- Status colors atualizados para M7-2026 (`#3498DB`→`#3B82F6`, `#E74C3C`→`#e40014`, `#27AE60`→`#4CAF50`, `#BDC3C7`→`#aeada8`)

### Fixed
- Cores fora da paleta M7-2026 no template (`#2C3E50`, `#D0D0D0`, `#BDBDBD`, `#F0F0F0`, `#F5F5F5`, `#9E9E9E` etc.)
- Lime (`#eef77c`) usado como texto sobre fundo claro (contraste ~1.1:1 → agora como badge)
- Legenda "Sem meta" usava `#E0E0E0`/`#BDBDBD` → corrigido para `#d0d0cc`/`#aeada8`
- `.action-num` com texto branco sobre lime → corrigido para `#424135`

## [1.6.0] - 2026-04-01

### Added
- Geracao de PDF visual para ata de ritual (M7-2026 design system, Score A)
- Template HTML `ata-ritual.tmpl.html` com CSS identico ao WBR narrativo (TWK Everett, verde caqui, lime, off-white)
- Script `html-to-pdf.js` (Puppeteer ^22) para conversao HTML → PDF autocontido
- Referencia `ata-html-guide.md` com mapeamento de componentes (timeline, badges, KPI cards, callouts)
- Fase 5.5 no workflow de `recording-decisions` (gerar HTML e PDF apos registro no CSV)
- Exit criteria para HTML e PDF na skill `recording-decisions`

### Changed
- Agent `decision-recorder` agora inclui `Bash` nos tools (necessario para executar Puppeteer)
- Fluxo de dados atualizado: 3 artefatos de saida (MD + HTML + PDF) em vez de 1
- Regra de escopo do agent atualizada: Bash restrito a `html-to-pdf.js` e `npm install`

## [1.5.0] - 2026-03-31

### Added
- Command `record-decisions`: atalho direto para executar G2.3 E5 (registro de decisoes pos-ritual) sem precisar percorrer o pipeline sequencial via `/next`

## [1.4.0] - 2026-03-31

### Changed
- Removidas colunas YTD da Matriz de Visao Geral (Slide 2): de 7 colunas para 4 (Indicador + N3 + Esp1 + Esp2)
- Apresentacao agora exibe apenas resultados do mes corrente
- Cores dos headers da matriz unificadas em tons de verde-caqui (#424135 → #4f4e3c → #5f5e4c)

### Removed
- Colunas YTD (Year-to-Date) do template HTML e da referencia de slides
- Placeholder `{{periodo_ytd_label}}` do template
- Classes CSS `.ytd`, `.ytd-n`, `.ytd-e1`, `.ytd-e2` do template HTML

## [1.3.1] - 2026-03-30

### Fixed
- Migrar design tokens de M7-Navy (legado) para M7-2026 (oficial)
- Cores: #1E3A5F → #424135, #FAF9F6 → #fffdef, #C9A962 → #eef77c, #E46962 → #e40014
- Fonte: Arial → "twkEverett", Arial, sans-serif
- Headings: weight bold → 400 (autoridade por tamanho conforme brandbook M7)
- Borders: #E5E5E5 → #d0d0cc (verde-caqui-100)
- Aplicado em: slide-structure.md, ritual.tmpl.html, material-generator.md

## [1.3.0] - 2026-03-30

### Changed
- **BREAKING**: Output de PPTX para HTML autocontido (elimina python-pptx e m7_pptx_lib.py)
- **BREAKING**: Estrutura de slides refatorada de "por KPI" para "por especialista"
- Cada especialista do Card recebe bloco de 3-4 slides (Dashboard, Analise, Projecao, Sugestoes PPI condicional)
- Slide Sugestoes PPI e condicional — gerado apenas se WBR contem dados de sugestoes
- Agendas de transicao entre blocos de especialistas
- Novos slides fixos: Visao Geral (Matriz 7 colunas), Status Plano de Acao (donut + barras), Plano de Acao (tabela)

### Added
- Template `ritual.tmpl.html` — estrutura HTML autocontida com iframes por slide
- Paleta de cores do ritual documentada em `slide-structure.md` (navy #1E3A5F, gold #C9A962, off-white #FAF9F6)

### Removed
- Template `ritual-pptx-script.tmpl.py` (obsoleto — PPTX substituido por HTML)
- Dependencia de `python-pptx` e `m7_pptx_lib.py` (m7-apresentacoes)
- Dependencia de assets/logos externos

## [1.2.0] - 2026-03-30

### Changed
- **BREAKING**: Briefing refatorado de "mini-WBR" para "guia do consultor"
- Nova estrutura: Veredicto (3 frases) + O Que Provocar (perguntas por interlocutor) + Armadilhas da Reuniao + Decisoes Binarias + Roteiro com Intencao
- Briefing nao repete dados do WBR — traduz dados em perguntas, armadilhas e decisoes acionaveis
- Template `ritual-briefing.tmpl.md` atualizado com novos placeholders
- `material-generator` Fase 4 reescrita com novo fluxo de geracao
- Metricas de qualidade atualizadas: "Nao aceite" em 100% das perguntas, decisoes binarias, sem repeticao de dados

## [1.1.0] - 2026-03-30

### Added
- Integracao com Cards de Performance (YAML) como prerequisito de ambas as skills
- Ambos os agents (material-generator, decision-recorder) agora leem o card da vertical antes de executar
- Card fornece: responsaveis/especialistas, KPIs com criterios de desvio critico, logica de analise (7 passos), correlacoes entre indicadores

### Changed
- Fase 1 de `preparing-materials` agora localiza e passa CARD_PATH ao agent
- Fase 1 de `recording-decisions` agora le o card para contexto organizacional antes de solicitar notas
- `material-generator` enriquece briefing com correlacoes e foco do destinatario do card
- `decision-recorder` valida `indicador_impactado` contra KPIs reais do card e sugere responsaveis

## [1.0.0] - 2026-03-30

### Added
- Skill `preparing-materials` (G2.3-E2): gera PPTX + Briefing MD a partir do WBR
- Skill `recording-decisions` (G2.3-E5): registra decisoes pos-ritual em ata + CSV
- Agent `material-generator`: transforma WBR em materiais visuais (sonnet)
- Agent `decision-recorder`: formaliza notas do ritual em ata + plano-de-acao.csv (sonnet)
- Command `prepare-ritual`: gera materiais pre-ritual para uma vertical
- Command `next`: avanca pipeline G2.3 para proxima fase pendente
- Command `status`: exibe progresso do ciclo G2.3
- References: `slide-structure.md`, `briefing-structure.md`, `csv-schema.md`, `prioritization-rules.md`
- Templates: `ritual-briefing.tmpl.md`, `ritual-pptx-script.tmpl.py`, `ata-ritual.tmpl.md`, `acao-template.tmpl.csv`
- Documentacao E3 (distribuicao manual) em pipeline e commands
- Suporte a 5 verticais: investimentos, credito, universo, seguros, consorcios
