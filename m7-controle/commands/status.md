---
description: Exibe o progresso do ciclo atual do pipeline G2.2 - fases concluidas, fase atual, artefatos gerados, contadores de log/anomalias/decisoes e proximo passo sugerido. Filtra por vertical ou mostra todas as ativas.
argument-hint: [vertical]
---

# m7-controle:status

Exibe o status do pipeline G2.2 para uma ou todas as verticais ativas.

## Input

- **vertical** (opcional): `$ARGUMENTS[0]` — nome da vertical em kebab-case. Se omitido, mostra todas as verticais com ciclo ativo.

## Steps

1. **Localizar CICLO.md** da vertical especificada.
   - Se vertical omitida, localizar todos os CICLOs ativos via glob `**/{vertical}/????-??-??/CICLO.md`.
   - Se nenhum ciclo encontrado: exibir `"Nenhum ciclo ativo. Inicie com /m7-controle:run-weekly {vertical}"` e parar.

2. **Ler cada CICLO.md** e extrair:
   - Status de cada fase (E2-E6) da tabela Progresso
   - Caminhos dos artefatos gerados
   - Contadores: entradas no Log de Execucao, Anomalias e Decisoes

3. **Verificar existencia fisica dos artefatos** referenciados no CICLO.md usando Glob nos caminhos listados.
   - Se artefato referenciado nao existe no filesystem: marcar com alerta `"Artefato nao encontrado: {caminho}"`

4. **Calcular progresso**: fases concluidas / total de fases (5) = percentual

5. **Exibir tabela formatada** por vertical:

```
Pipeline G2.2 - {Vertical} - {YYYY-MM-DD}
Pasta: {vertical}/{YYYY-MM-DD}/

| Fase | Skill                | Status       | Artefato                              |
|------|----------------------|--------------|---------------------------------------|
| E2   | collecting-data      | Concluido    | data-quality/data-quality-report.md   |
| E3   | analyzing-deviations | Concluido    | analise/deviation-cause-report.md     |
| E4   | summarizing-actions  | Pendente     | --                                    |
| E5   | projecting-results   | Pendente     | --                                    |
| E6   | consolidating-wbr    | Pendente     | --                                    |

Progresso: {n}/5 ({pct}%)
Log: {x} entradas | Anomalias: {y} | Decisoes: {z}
Proximo: /m7-controle:next {vertical} ({proxima-fase}: {proxima-skill})
```

6. **Sugerir proximo passo**:
   - Se ha fase pendente: `/m7-controle:next {vertical}`
   - Se pipeline completo: `"Pipeline G2.2 concluido. WBR disponivel em {vertical}/{YYYY-MM-DD}/wbr/ (estruturado + narrativo)"`

## Cenarios especiais

| Cenario | Output |
|---------|--------|
| Nenhum ciclo ativo | `"Nenhum ciclo ativo. Inicie com /m7-controle:run-weekly {vertical}"` |
| Pipeline completo | `"Pipeline G2.2 concluido. WBR disponivel em {vertical}/{YYYY-MM-DD}/wbr/wbr-{vertical}-{data}.md"` |
| Artefato referenciado nao encontrado | `"Artefato nao encontrado: {caminho}"` na coluna de artefato |
| Multiplas verticais ativas (sem filtro) | Uma tabela separada por vertical |

## Output

Tabela Markdown formatada com status, percentual de progresso, contadores de changelog e sugestao de proximo comando.
