# Schema do plano-de-acao.csv

> **⚠ DEPRECATED 2026-04-30** — este documento esta preservado apenas como **referencia historica** do schema CSV legado. A SoT do Plano de Acao migrou para a lista ClickUp `pa-resultado` (id `901326795742`). Toda escrita agora vai via ClickUp MCP.
>
> **Use** [clickup-actions-schema.md](clickup-actions-schema.md) **em vez deste arquivo.**
>
> A skill `recording-decisions` e o agent `decision-recorder` NAO devem mais ler este documento como fonte autoritativa. Mantido aqui apenas para fins de auditoria e mapeamento campo-a-campo durante migracao de dados historicos (se necessario).

---

## (Conteudo legado abaixo — referencia historica apenas)

Referencia canonica do schema de 24 campos do plano-de-acao.csv (descontinuado).

---

## Campos (24)

```
id, parent_id, data_cadastro, data_inicio, origem, origem_detalhe,
indicador_impactado, vertical, titulo, descricao, responsavel, solicitante,
prioridade, data_limite, data_followup, status, percentual, data_conclusao,
evidencia, observacoes, volume, receita, comentarios, ultima_atualizacao
```

## Valores por campo

| Campo | Valor | Notas |
|-------|-------|-------|
| `id` | PA-{YYYY}-{NNN} (sequencial) | Regex: `^PA-\d{4}-\d{3}$`. NUNCA reutilizar, mesmo de canceladas |
| `parent_id` | "" (vazio) ou ID pai | Liga sub-acoes a acoes pai |
| `data_cadastro` | {data_ritual} (YYYY-MM-DD) | Data de criacao |
| `data_inicio` | {data_ritual} (YYYY-MM-DD) | Data de inicio |
| `origem` | "ritual" | Fixo para acoes de ritual |
| `origem_detalhe` | "Ritual N2 {vertical} - {data_ritual}" | Contexto da origem |
| `indicador_impactado` | {nome_indicador} ({id_indicador}) | Cruzar com WBR |
| `vertical` | {vertical} | Nome da vertical em kebab-case |
| `titulo` | {titulo_contramedida} | Descritivo e unico |
| `descricao` | {descricao_detalhada} | Detalhamento da acao |
| `responsavel` | {responsavel} | NUNCA inferir — perguntar ao usuario |
| `solicitante` | {quem_pediu_no_ritual} | Quem demandou no ritual |
| `prioridade` | `critica` \| `alta` \| `media` \| `baixa` | Ver [prioritization-rules.md](prioritization-rules.md) |
| `data_limite` | {prazo} (YYYY-MM-DD) | NUNCA inferir — perguntar ao usuario |
| `data_followup` | "" | Preenchido pelo acompanhamento |
| `status` | `pendente` \| `em_andamento` \| `concluida` \| `cancelada` | Default: "pendente" |
| `percentual` | "0" a "100" (string) | Inteiro 0-100 |
| `data_conclusao` | "" | Preencher quando status = "concluida" |
| `evidencia` | "" | Link ou descricao da evidencia |
| `observacoes` | {contexto_adicional} | Texto livre |
| `volume` | {volume_estimado} (ex: "R$ 74MM") | String, pode conter "R$" e separadores |
| `receita` | {receita_estimada} (ex: "R$ 205k") | String, pode conter "R$" e separadores |
| `comentarios` | JSON array com entrada inicial | Ver formato abaixo |
| `ultima_atualizacao` | {data_ritual} (YYYY-MM-DD) | Atualizar em cada modificacao |

## Formato do campo `comentarios`

JSON array dentro de campo CSV com aspas escapadas:

```
"[{""data"": ""2026-03-30"", ""autor"": ""Nome"", ""texto"": ""Contexto da decisao no ritual.""}]"
```

Cada entrada e um objeto `{"data", "autor", "texto"}`. Aspas internas escapadas com `""` (convencao CSV).

## Formato do CSV

| Propriedade | Valor |
|-------------|-------|
| Delimitador | `,` (virgula) |
| Encoding | UTF-8 |
| Campos | Todos entre aspas duplas `"` |
| Datas | Formato `YYYY-MM-DD` |
| Monetarios | Strings com "R$" e separadores de milhar — NUNCA arredondar |

## Regras de integridade

### Inserindo novas acoes (append)

1. Determinar proximo ID: ler todos IDs existentes, encontrar max NNN, usar NNN+1
2. Preencher todos os 24 campos (nenhum pode faltar, usar `""` para vazios)
3. Inserir ao final do arquivo (append, nunca no meio)
4. Preservar aspas duplas em todos os campos e encoding UTF-8
5. Campos obrigatorios que NUNCA podem ser vazios: `id`, `vertical`, `titulo`, `responsavel`, `prioridade`, `data_cadastro`, `status`, `origem`

### Atualizando acoes existentes (edit)

1. Localizar linha exata via Grep + Read (confirmar numero da linha antes de editar)
2. Campos atualizaveis: `status`, `percentual`, `comentarios`, `ultima_atualizacao`, `data_conclusao`
3. Para `comentarios`: parsear JSON array existente, **APPEND** nova entrada, serializar de volta
4. NUNCA substituir o campo `comentarios` inteiro
5. Preservar escaping CSV: aspas duplas dentro de campos usam `""`

### Proibicoes

- **NUNCA** reutilize IDs — IDs sao sequenciais e imutaveis
- **NUNCA** altere o header do CSV (primeira linha com os 24 campos e intocavel)
- **NUNCA** use delimitador `;` — o CSV usa `,`
- **NUNCA** remova ou reordene linhas existentes
- **NUNCA** altere encoding ou formato
- **NUNCA** omita campos — todos os 24 devem estar presentes em cada linha
