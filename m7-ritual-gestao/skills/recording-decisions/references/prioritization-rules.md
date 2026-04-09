# Regras de Priorizacao e Duplicatas

Referencia canonica para priorizacao de contramedidas e deteccao de duplicatas. Usada tanto pela skill `recording-decisions` quanto pelo agent `decision-recorder`.

---

## Tabela de prioridade

| Prioridade | Criterio |
|------------|----------|
| `critica` | Indicador Vermelho + volume >= mediana das acoes existentes no CSV |
| `alta` | Indicador Vermelho |
| `media` | Indicador Amarelo |
| `baixa` | Preventiva (indicador Verde ou sem desvio) |

## Ordenacao

1. Ordenar por prioridade: `critica` > `alta` > `media` > `baixa`
2. Desempate por receita descendente (maior receita primeiro)
3. Incluir justificativa para cada atribuicao de prioridade na ata

## Regras de atribuicao

- Prioridade e baseada em **metricas objetivas** (semaforo do indicador + volume/receita), NUNCA em opiniao
- Se volume nao informado pelo usuario: inferir do WBR (secao de impacto financeiro do KPI)
- Se nem usuario nem WBR fornecem volume: atribuir `alta` (nao `critica`) para Vermelhos sem dados de volume

---

## Deteccao de duplicatas

Antes de inserir qualquer contramedida nova no CSV, verificar se **ja existe** acao com:

1. Mesmo `titulo` (comparacao case-insensitive, trimmed) **E**
2. Mesmo `indicador_impactado` **E**
3. Mesma `vertical` **E**
4. `status` diferente de `concluida` e `cancelada`

Usar `Grep` para busca eficiente no CSV.

### Se duplicata encontrada

- **NAO** inserir nova linha
- Informar ao usuario: "Acao '{titulo}' ja existe como {id} (status: {status})"
- Oferecer atualizar a acao existente em vez de criar nova
- Registrar na secao "Duplicatas Detectadas" da ata
