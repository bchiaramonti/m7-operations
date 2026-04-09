---
description: Exibe o progresso do ciclo G2.3 (Ritual de Gestao) - materiais gerados, distribuicao realizada e decisoes registradas. Filtra por vertical ou mostra todas as ativas.
argument-hint: [vertical]
---

# m7-ritual-gestao:status

Exibe o status do pipeline G2.3 para uma ou todas as verticais ativas.

## Input

- **vertical** (opcional): `$ARGUMENTS[0]` — nome da vertical em kebab-case. Se omitido, mostra todas as verticais com ciclo G2.3 ativo.

## Steps

1. **Localizar CICLO.md** da vertical especificada.
   - Se vertical omitida, localizar todos os CICLOs ativos via glob `**/{vertical}/????-??-??/CICLO.md`.
   - Em cada CICLO.md, buscar a secao `## G2.3 - Ritual de Gestao`.
   - Se nenhum CICLO.md com secao G2.3 encontrado: exibir `"Nenhum ciclo G2.3 ativo. Aguardando WBR do m7-controle."` e parar.

2. **Extrair status G2.3** lendo a tabela de Progresso dentro da secao `## G2.3`:
   - Status de cada fase (E2, E3, E5)
   - Caminhos dos artefatos gerados

3. **Verificar existencia fisica dos artefatos** referenciados na tabela G2.3 usando Glob:
   - `output/{vertical}/ritual-{vertical}-{data}.html`
   - `output/{vertical}/briefing-ritual-{data}.md`
   - `output/{vertical}/ata-ritual-{data}.md`
   - Se artefato referenciado nao existe no filesystem: marcar com alerta `"Artefato nao encontrado: {caminho}"`

4. **Verificar atualidade do WBR** usado como insumo:
   - Comparar a semana ISO do WBR fonte (registrado no CICLO.md) com a semana ISO atual.
   - Se WBR de semana anterior: adicionar aviso `"⚠️ WBR da semana anterior. Verifique /m7-controle:status"`

5. **Calcular progresso**: fases com status `concluido` ou `enviado` / total de fases (3) = percentual

6. **Exibir tabela formatada** por vertical:

```
Pipeline G2.3 - {Vertical} - Semana {YYYY-Www}

| Fase | Skill                | Status       | Artefato                              |
|------|----------------------|--------------|----------------------------------------|
| E2   | preparing-materials  | ✅ Concluido | ritual-{vertical}-{data}.html          |
|      |                      |              | briefing-ritual-{data}.md              |
| E3   | (distribuicao manual)| ✅ Enviado   | --                                     |
| E5   | recording-decisions  | ⬜ Pendente  | --                                     |

Progresso: {n}/3 ({pct}%)
Proximo: {sugestao}
```

7. **Sugerir proximo passo** com base no estado do pipeline:
   - Se E2 pendente: `/m7-ritual-gestao:next {vertical}` (gerar materiais)
   - Se E2 concluido e E3 pendente: `"Materiais prontos. Distribua ao gestor e marque como enviado."`
   - Se E3 concluido/enviado e E5 pendente: `"Apos o ritual, execute /m7-ritual-gestao:next {vertical}"`
   - Se todas as fases concluidas: `"Ciclo G2.3 concluido. Ata e acoes registradas."`

## Cenarios especiais

| Cenario | Output |
|---------|--------|
| Nenhum ciclo G2.3 ativo | `"Nenhum ciclo G2.3 ativo. Aguardando WBR do m7-controle."` |
| Materiais gerados, nao distribuidos | `"Materiais prontos. Distribua ao gestor e marque como enviado."` |
| Pipeline completo | `"Ciclo G2.3 concluido. Ata e acoes registradas."` |
| WBR desatualizado | `"⚠️ WBR da semana anterior. Verifique /m7-controle:status"` |
| Multiplas verticais ativas (sem filtro) | Uma tabela separada por vertical |

## Output

Tabela Markdown formatada com status, percentual de progresso e sugestao de proximo comando.
