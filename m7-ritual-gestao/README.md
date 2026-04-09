# m7-ritual-gestao

> Processo G2.3 — Rituais de Gestao | v1.3.0

Plugin para operacionalizar os rituais semanais de gestao da M7, consumindo o WBR produzido pelo m7-controle (G2.2) e gerando materiais de apoio + registro estruturado de decisoes.

## Pipeline

```
TER 08:00 (materiais pre-ritual)
│
├── E2: preparing-materials  → material-generator → HTML + Briefing MD
│
└── E3: Distribuicao manual  → Usuario envia ao gestor

QUA (ritual presencial/virtual)

QUI (registro pos-ritual)
│
└── E5: recording-decisions  → decision-recorder  → Ata MD + CSV atualizado
```

## Composicao

| Tipo | Qtd | Artefatos |
|------|-----|-----------|
| Skills | 2 | preparing-materials (E2), recording-decisions (E5) |
| Agents | 2 | material-generator, decision-recorder |
| Commands | 3 | next, status, prepare-ritual |

## Commands

| Comando | Descricao |
|---------|-----------|
| `/m7-ritual-gestao:prepare-ritual <vertical>` | Gera materiais pre-ritual (HTML + Briefing) |
| `/m7-ritual-gestao:next [vertical]` | Avanca pipeline G2.3 para proxima fase pendente (E2 → E3 manual → E5) |
| `/m7-ritual-gestao:status [vertical]` | Exibe progresso do ciclo G2.3 |

## Dependencias externas

| Dependencia | Tipo | Uso |
|-------------|------|-----|
| WBR (output do m7-controle) | Arquivo MD | Input principal para geracao de materiais |
| Card de Performance | Arquivo YAML | Contexto organizacional (especialistas, KPIs, logica de analise) |
| plano-de-acao.csv | Arquivo local | Escrita de novas contramedidas (E5) |

## Outputs

| Output | Formato | Etapa | Skill |
|--------|---------|-------|-------|
| Apresentacao do Ritual | HTML autocontido | E2 | preparing-materials |
| Briefing do Ritual | MD (guia do condutor) | E2 | preparing-materials |
| Ata do Ritual | MD | E5 | recording-decisions |
| plano-de-acao.csv (atualizado) | CSV | E5 | recording-decisions |

## Estrutura do Ritual (HTML)

O deck e organizado **por especialista**, nao por KPI:

```
1. Capa
2. Visao Geral (Matriz de indicadores × especialistas)
3. Agenda

Per specialist block (repetido):
  4. Dashboard (indicadores + acoes + riscos)
  5. Analise (desvio por assessor + diagnostico 3G)
  6. Projecao (pipeline + gauges + projecoes)
  7. Sugestoes PPI (condicional — so se dados disponiveis)
  8. Agenda transicao

Encerramento:
  N-2. Status Plano de Acao
  N-1. Plano de Acao (tabela)
  N.   Proximos Passos
```

## State management

Compartilha o CICLO.md do m7-controle, adicionando secao `## G2.3 - Ritual de Gestao` com progresso proprio.

## Relacionamento com outros plugins

| Plugin | Relacao |
|--------|---------|
| m7-controle | Fornecedor do WBR e Cards de Performance (G2.2 → G2.3) |
