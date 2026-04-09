---
description: Consolida licoes aprendidas do ciclo mensal para o processo G2.2. Escaneia todos os ciclos semanais de TODAS as verticais no mes, rituais e artefatos para produzir registro unico de licoes e propostas de melhoria.
argument-hint: [periodo]
---

# m7-controle:record-lessons

Executa a etapa E7 (Licoes Aprendidas) do processo G2.2 para um periodo mensal.

## Input

- **periodo** (opcional): `$ARGUMENTS[0]` — periodo no formato `YYYY-MM` (ex: `2026-03`). Se nao informado, calcular default:
  - Se a data atual esta nos ultimos 5 dias do mes → usar mes atual
  - Caso contrario → usar mes anterior

## Steps

### 1. Resolver periodo

1. Se periodo informado: validar formato `YYYY-MM`
2. Se periodo NAO informado: calcular default conforme regra acima
3. **PARAR e confirmar** com o usuario via AskUserQuestion:
   ```
   Periodo para licoes aprendidas: {YYYY-MM} ({nome_mes} {ano})
   Confirma?
   ```
4. Derivar datas:
   - `data_inicio` = `{YYYY-MM}-01`
   - `data_fim` = ultimo dia do mes

### 2. Descobrir ciclos de TODAS as verticais

1. Executar `Glob('*/{periodo}-*/CICLO.md')` no diretorio de trabalho
2. Para cada CICLO.md encontrado:
   - Ler header para extrair vertical e status
   - Classificar como **completo** (E6 = concluido) ou **parcial**
3. Agrupar por vertical:

   ```
   Verticais encontradas:
   - consorcios: 4 ciclos (3 completos, 1 parcial)
   - seguros: 3 ciclos (3 completos)
   - investimentos: 0 ciclos
   ```

4. Se **0 ciclos completos** em todas as verticais:
   ```
   Nenhum ciclo completo encontrado para {periodo}.
   Execute pelo menos 1 /m7-controle:run-weekly <vertical> primeiro.
   ```
   **Parar**.

5. Se ha ciclos parciais: registrar warning (nao bloqueante), prosseguir com os completos.

### 3. Descobrir atas de rituais

1. Executar `Glob('*/{periodo}-*/output/*/ata-ritual-*.md')` no diretorio de trabalho
2. Contar atas e extrair nomes de gestores N2 (ler secao `## Participantes` de cada ata)
3. Se **0 atas encontradas**: registrar WARNING:
   ```
   ⚠ Nenhuma ata de ritual encontrada para {periodo}.
   Criterio de qualidade 'min 2 gestores N2' nao sera atendido.
   Prosseguindo com WBRs, action-reports e DQ-reports.
   ```
   **Nao bloquear** — atas sao input desejavel mas nao obrigatorio.

### 4. Criar pasta de output

1. Verificar se `mensal/{periodo}/` ja existe
   - Se existe e contem `lessons-learned-{periodo}.md`: perguntar ao usuario se deseja reexecutar
   - Se nao existe: criar `mensal/{periodo}/`

### 5. Invocar skill recording-lessons

> **Regra arquitetural**: O command invoca **skills**, nunca agents diretamente. A skill decide internamente se executa no main thread ou delega a um agente.

Contexto disponivel para a skill:
- Periodo: `{periodo}`, `data_inicio`, `data_fim`
- Lista de cycle folders completos (agrupados por vertical)
- Lista de cycle folders parciais
- Lista de atas de rituais
- Caminho de output: `mensal/{periodo}/`

### 6. Verificar output

Confirmar que `mensal/{periodo}/lessons-learned-{periodo}.md` foi gerado:
- Se NAO existe: registrar erro e exibir mensagem de falha
- Se existe: ler o relatorio para extrair contagens (licoes, propostas, gestores)

### 7. Exibir resumo

```
E7 Licoes Aprendidas — G2.2 — {periodo}

Verticais: {lista_verticais}
Ciclos analisados: {n_completos} completos + {n_parciais} parciais
Rituais analisados: {n_rituais}
Gestores N2 identificados: {n_gestores}

Licoes registradas: {n_licoes}
  - Funcionou: {n_funcionou}
  - Nao funcionou: {n_nao_funcionou}
  - Surpreendeu: {n_surpreendeu}
  - Faltou: {n_faltou}

Propostas de melhoria: {n_propostas}
  - Alta: {n_alta} | Media: {n_media} | Baixa: {n_baixa}

Output: mensal/{periodo}/lessons-learned-{periodo}.md
```

## Tratamento de erros

| Erro | Tratamento |
|------|------------|
| Periodo com formato invalido | Exibir formato esperado (YYYY-MM) e parar |
| 0 ciclos completos | Abortar com mensagem e sugerir run-weekly |
| 0 atas de rituais | Warning (nao bloqueante), registrar no relatorio |
| Menos de 2 licoes geradas | Alertar que criterio de qualidade nao foi atendido, mas salvar relatorio |
| Relatorio ja existe para o periodo | Perguntar ao usuario se deseja reexecutar |
| Skill falha durante execucao | Registrar erro, exibir detalhes e sugerir retry |
