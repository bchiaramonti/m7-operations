---
name: comissionamento-next
description: >-
  Executa o proximo passo pendente do processamento de comissionamento.
  Identifica a fase e item atuais no checklist e executa a acao correspondente.
  Use para avancar o processamento de forma guiada, passo a passo.
argument-hint: [YYYYMM]
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# Executar Proximo Passo do Comissionamento

Identifica e executa o proximo item pendente no checklist da competencia.

## Input

Competencia (opcional): $ARGUMENTS

## Steps

### 1. Identificar competencia

Se $ARGUMENTS informado, usar como competencia (formato YYYYMM).

Se nao informado, detectar automaticamente:
- Buscar pastas `*/??-??/` no workspace atual
- Ordenar por nome (mais recente primeiro)
- Usar a mais recente como competencia ativa

### 2. Localizar e parsear o checklist

Ler `CHECKLIST_{YYYYMM}.md` na pasta da competencia (`YYYY/MM-YY/`).

Encontrar o **primeiro item pendente** (`- [ ]`) no checklist, percorrendo as fases em ordem (Fase 0 → Fase 10).

### 3. Mapear item para acao

Cada fase tem acoes especificas. Usar o mapeamento abaixo:

| Fase | Acao | Skill/Comando |
|------|------|---------------|
| 0 | Criar estrutura de diretorios | skill `structuring-competencia` |
| 1.0 | Revisar ajustes da competencia anterior | Ler AJUSTES anterior, registrar transbordos |
| 1.1-1.2 | Converter arquivos Excel para CSV | Guiar usuario (conversao manual ou script) |
| 2 | Processar correcoes nos CSVs | Guiar usuario com regras do checklist |
| 3 | Criar ajustes manuais e descontos | Guiar usuario |
| 4 | Atualizar parametrizacoes | Guiar usuario (revisar CSVs em fase2_parametrizacao/) |
| 5 | Carga no SplitC | Guiar usuario (plataforma web externa) |
| 6 | Envio de comissoes ao financeiro | Guiar usuario (elaborar e enviar email) |
| 7 | Relatorio Compromissada | Guiar usuario (filtrar e enviar) |
| 8a | Ajustes pre-pagamento | Guiar usuario (pleitos que impactam PGTO) |
| 9 | Pagamento (HARD DEADLINE dia 13) | Guiar usuario (exportar PGTO, enviar email) |
| 8b | Ajustes pos-pagamento | Guiar usuario (erratas, PGTO complementar, transbordos) |
| 10.1 | Carga no banco M7Medallion | skill `processing-split-c-receitas` |
| 10.2 | Resumo financeiro | skill `generating-resumo-financeiro` |

### 4. Executar a acao

**Se o item mapeia para uma skill**: invocar a skill correspondente com os parametros da competencia.

**Se o item requer acao manual**: exibir instrucoes detalhadas do checklist, listar arquivos relevantes e aguardar confirmacao do usuario antes de marcar como concluido.

**Se o item requer plataforma externa** (SplitC, email): exibir instrucoes passo a passo e perguntar ao usuario se foi concluido.

### 5. Atualizar checklist

Apos conclusao do item:
1. Marcar o item como `- [x]` no `CHECKLIST_{YYYYMM}.md`
2. Atualizar o emoji da secao (⬜ → 🟡 se parcial, 🟡 → ✅ se todos concluidos)
3. Registrar entrada no `CHANGELOG_{YYYYMM}.md` com timestamp real (`date +"%Y-%m-%d %H:%M"`)

### 6. Exibir resumo

```
=================================================
PASSO EXECUTADO
=================================================

Fase: {numero} — {descricao}
Item: {descricao do item}
Status: Concluido

Progresso da fase: X/Y itens
Proxima acao: {descricao do proximo item pendente}
```

Se a fase inteira foi concluida, destacar e indicar a proxima fase.

## Regras

- **Nunca pular itens**: executar rigorosamente na ordem do checklist
- **Nunca marcar como concluido sem confirmacao**: se a acao e manual, perguntar ao usuario
- **Sempre registrar no CHANGELOG**: cada acao executada gera uma entrada com timestamp real
- **Timestamps reais**: usar `date +"%Y-%m-%d %H:%M"` — nunca inventar horarios
