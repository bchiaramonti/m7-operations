# Convencoes CSV — Planos de Acao

Regras obrigatorias para qualquer operacao de escrita no CSV de acoes de melhoria.

## Contents
- [1. Protocolo de escrita](#1-protocolo-de-escrita)
- [2. Quoting e encoding](#2-quoting-e-encoding)
- [3. JSON embutido (comentarios)](#3-json-embutido-comentarios)
- [4. Geracao de IDs](#4-geracao-de-ids)
- [5. Backup](#5-backup)
- [6. Validacao pos-escrita](#6-validacao-pos-escrita)
- [7. Anti-patterns](#7-anti-patterns)

---

## 1. Protocolo de escrita

Toda operacao de escrita segue esta sequencia — sem excecao:

```
1. Ler CSV atual completo (Read tool)
2. Fazer backup em _Historico/ (Write tool)
3. Montar conteudo completo em memoria (header + linhas existentes + alteracoes)
4. Reescrever CSV inteiro (Write tool — NUNCA Edit tool)
5. Reler CSV escrito (Read tool)
6. Confirmar integridade: mesmo numero de colunas, nenhuma linha corrompida
7. Reportar resultado ao usuario
```

**Por que reescrever inteiro?** CSV nao suporta edicao in-place segura. Edit tool pode quebrar quoting de JSON embutido ou desalinhar colunas. Write tool garante consistencia.

---

## 2. Quoting e encoding

| Regra | Exemplo |
|-------|---------|
| Todos os campos entre aspas duplas | `"valor"` |
| Aspas internas: `""` (doubled) | `"Ele disse ""sim""."` |
| Campos vazios: aspas vazias | `""` |
| Nunca usar `null`, `N/A`, `none` | Sempre `""` para vazio |
| Separador: virgula (`,`) | `"campo1","campo2"` |
| Encoding: UTF-8 sem BOM | — |
| Quebra de linha: `\n` (LF) | Nunca `\r\n` |
| Sem trailing comma na linha | `"a","b","c"\n` |

### Datas

- Formato unico: `YYYY-MM-DD`
- Datas vazias: `""` (nunca `null`)
- Nunca armazenar hora — so data

### Numeros

- `percentual`: inteiro 0–100, sem `%` (ex: `"75"`)
- `sla_horas`: inteiro positivo (ex: `"24"`)

---

## 3. JSON embutido (comentarios)

O campo `comentarios` armazena um array JSON dentro de uma celula CSV.

### Formato do array

```json
[
  {"data": "2026-03-13", "autor": "Nome Completo", "texto": "Descricao da acao."},
  {"data": "2026-03-14", "autor": "Nome Completo", "texto": "Seguimento."}
]
```

### Regras de escrita no CSV

1. Serializar o array em uma unica linha (sem quebras de linha internas)
2. Escapar aspas duplas do JSON com `""` (CSV quoting):
   ```
   "[{""data"": ""2026-03-13"", ""autor"": ""Bruno"", ""texto"": ""Criado.""}]"
   ```
3. Ao atualizar: fazer parse do JSON existente, append do novo objeto, serializar novamente
4. Nunca remover comentarios existentes — so append
5. Ordem cronologica (mais antigo primeiro)

### Comentario de criacao (obrigatorio)

Toda linha nova recebe um comentario inicial:
```json
[{"data": "{hoje}", "autor": "{responsavel}", "texto": "Registro criado"}]
```

### Comentario de atualizacao (obrigatorio)

Toda atualizacao de registro exige um novo comentario descrevendo a alteracao:
```json
{"data": "{hoje}", "autor": "{responsavel}", "texto": "Status atualizado para em_andamento. Motivo: ..."}
```

---

## 4. Geracao de IDs

### Regras gerais

1. **Ler o CSV no momento da escrita** para determinar o proximo sequencial
2. **NUNCA cachear** proximo ID entre operacoes
3. Filtrar pelo prefixo e ano corrente, extrair maior sequencial, incrementar +1
4. Pad com zeros: `NNN` = 3 digitos, `NN` = 2 digitos

### Formatos por tipo

| Tipo | Formato | Como gerar |
|------|---------|------------|
| Melhoria / Sub-acao | `PA-{YYYY}-{NNN}` | Maior `PA-{YYYY}-*` + 1 |

### Exemplos

```
CSV tem: PA-2026-001, PA-2026-002, PA-2026-003
Proximo: PA-2026-004
```

---

## 5. Backup

### Antes de qualquer escrita

```
{caminho_base}/_Historico/{nome_csv}_ate-{YYYY-MM-DD}.csv
```

**Exemplo:**
- `_Historico/plano-de-acao_ate-2026-03-31.csv`

### Regras

- Se ja existe backup do mesmo dia: sobrescrever (o CSV ja mudou desde o backup anterior do dia)
- Nunca apagar backups antigos
- Backup inclui header + todas as linhas (copia fiel do CSV)

---

## 6. Validacao pos-escrita

Apos escrever o CSV, realizar estas verificacoes:

1. **Reler o arquivo** escrito (Read tool)
2. **Contar colunas** da primeira linha (header) — deve bater com o schema
3. **Contar colunas de cada linha** — todas devem ter o mesmo numero que o header
4. **Verificar que o ID gerado** aparece no arquivo
5. **Verificar JSON** do campo `comentarios` — deve ser parseavel

Se qualquer verificacao falhar: restaurar o backup e reportar o erro.

---

## 7. Anti-patterns

| NUNCA faca | Faca em vez disso |
|------------|-------------------|
| Usar Edit tool em CSV | Reescrever completo via Write tool |
| Armazenar `atrasada`/`atrasado` como status | Computar em runtime |
| Aceitar atualizacao sem comentario | Exigir texto de rastreabilidade |
| Concluir melhoria sem evidencia | Exigir campo `evidencia` preenchido |
| Deletar linhas do CSV | Cancelar com justificativa (status terminal) |
| Modificar `id`, `data_cadastro`, `parent_id` | Estes campos sao imutaveis apos criacao |
| Cachear proximo ID | Ler CSV no momento da escrita |
| Usar `null`, `N/A`, `none` | Usar `""` para campos vazios |
| Adicionar BOM ao UTF-8 | UTF-8 sem BOM |
| Quebrar linha com `\r\n` | Usar `\n` (LF) |
