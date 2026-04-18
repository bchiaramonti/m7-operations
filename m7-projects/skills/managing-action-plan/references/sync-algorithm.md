# Sync Algorithm — Three-Way Diff Cronograma.xlsx ↔ ClickUp

Pseudocode + invariantes do algoritmo de sincronizacao usado por `sync.py prepare`.

## Indice

1. [Visao geral](#visao-geral)
2. [As 3 fontes do diff](#as-3-fontes-do-diff)
3. [Pipeline detalhado](#pipeline-detalhado)
4. [Categorizacao de linha](#categorizacao-de-linha)
5. [Categorizacao de campo](#categorizacao-de-campo)
6. [Quando o LLM entra no loop](#quando-o-llm-entra-no-loop)
7. [Hash determinismo: por que importa](#hash-determinismo-por-que-importa)

---

## Visao geral

```
        +----------+         +----------+         +----------+
        | BASELINE |         |  LOCAL   |         |  REMOTE  |
        | (.sync-  |         | (xlsx)   |         | (ClickUp |
        |  state)  |         |          |         |  filter) |
        +----+-----+         +----+-----+         +----+-----+
             |                    |                    |
             +----------+---------+--------------------+
                        |
                        v
               +-----------------+
               | three-way diff  |
               +--------+--------+
                        |
                        v
               +-----------------+
               | classify rows + |
               | apply field     |
               | resolution      |
               +--------+--------+
                        |
                        v
               +-----------------+
               | emit plan:      |
               | - push_creates  |
               | - push_updates  |
               | - push_deletes  |
               | - pull_creates  |
               | - pull_updates  |
               | - conflicts     |
               | - orphans       |
               +-----------------+
```

`sync.py prepare` para aqui — emite o plano para o Claude executar (MCP calls). Apos Claude aplicar, ele chama `sync.py finalize` para gravar novas baselines.

## As 3 fontes do diff

### Baseline
- Vive em `4-status-report/.sync-state.json`, chave `baselines`
- Estrutura: `{clickup_id: {hash, canonical: {...}}}`
- Atualizada APOS um sync ok (via `sync.py finalize` ou `finalize-init`)
- Representa "o que ambos os lados concordavam na ultima vez que sincronizamos"

### Local
- Vive em `4-status-report/Cronograma.xlsx`
- Lido via `_lib.CronogramaXLSX.read_rows()`
- Canonicalizado via `canonical_row()` (datas → ISO, trim, etc.)

### Remote
- Provido pelo Claude via `--remote-json` (JSON file com array de tasks)
- Claude obtem chamando `clickup_filter_tasks(list_id=...)` antes do `sync.py prepare`
- Convertido para schema canonico via `remote_to_canonical()`

## Pipeline detalhado

```python
def build_plan(local_rows, remote_tasks, baselines, status_map):
    remote_by_id = {t['id']: t for t in remote_tasks}
    plan = empty_plan()
    seen_remote_ids = set()

    # 1. Iterar linhas locais
    for row in local_rows:
        cu_id = row['clickup_id']

        if not cu_id:
            # Nunca pushada → push_create
            plan.push_creates.append(row)
            continue

        if cu_id not in remote_by_id:
            # Local tem ID que nao existe no remote → orphan
            plan.orphans.append(row)
            continue

        seen_remote_ids.add(cu_id)
        remote_task = remote_by_id[cu_id]
        baseline = baselines.get(cu_id)

        # 2. Three-way diff por campo
        for field in HASH_FIELDS:
            l_changed = (local[field] != baseline[field])
            r_changed = (remote[field] != baseline[field])

            if not l_changed and not r_changed:
                # UNCHANGED para este campo
                continue
            elif l_changed and not r_changed:
                push_field(field, local_value)
            elif r_changed and not l_changed:
                pull_field(field, remote_value)
            else:  # both
                rule = FIELD_RULES[field]
                if rule == 'conflict':
                    conflicts.append((field, local_v, remote_v))
                elif rule == 'local':
                    push_field(field, local_value)
                elif rule == 'remote':
                    pull_field(field, remote_value)

    # 3. Iterar tasks remotas nao vistas
    for cu_id, task in remote_by_id.items():
        if cu_id in seen_remote_ids:
            continue
        if cu_id in baselines:
            # Era nosso, sumiu local → push delete
            plan.push_deletes.append(task)
        else:
            # Novo no remote → pull create
            plan.pull_creates.append(task)

    return plan
```

## Categorizacao de linha

| Categoria | Quando | Acao |
|---|---|---|
| `UNCHANGED` | Nenhum campo mudou em nenhum lado | noop |
| `LOCAL_ONLY_CHANGED` | Algum(ns) campo(s) mudou(aram) so local | push_update |
| `REMOTE_ONLY_CHANGED` | Algum(ns) campo(s) mudou(aram) so remote | pull_update |
| `BOTH_CHANGED` | Pelo menos 1 campo mudou em ambos os lados | resolver por field rules |

`BOTH_CHANGED` nao implica conflito — depende dos campos. Status mudou em ambos? remote-wins, sem prompt. Title mudou em ambos? prompt.

## Categorizacao de campo

Ver tabela completa em [`field-resolution-rules.md`](field-resolution-rules.md). Resumo:

| Campo | Both changed |
|---|---|
| `etapa` (name) | conflict — prompt + LLM sugere merge |
| `entregavel` (description) | conflict — prompt + LLM sugere merge |
| `status` | remote-wins (silent log) |
| `inicio_plan`, `fim_plan` | local-wins |
| `responsavel`, `inicio_real`, `fim_real` | remote-wins |

**Filtro no push:** so campos com mapeamento em `LOCAL_TO_CU_FIELD` viram push payload. `no` e `tipo` sao schema local — nao vao pro ClickUp.

## Quando o LLM entra no loop

A skill foi desenhada para minimizar invocacao do LLM no caminho do sync:

- **Determinismo:** parsing, hashing, classificacao e resolucao por field rules sao 100% Python. Mesmo input → mesmo output.
- **LLM entra apenas quando:**
  1. Resolver `conflicts` (campos `etapa`/`entregavel` mudados em ambos lados): LLM apresenta diff e sugere merge; usuario decide
  2. Decidir sobre `orphans` (clickup_id local sem correspondente remote): recriar? remover mapping?
  3. Decidir sobre `push_deletes` ou `pull_creates`: usuario quer mesmo refletir essas mudancas?
  4. Tratar `sync_pending` apos `failure mode` (ver `failure-modes.md`)

A maioria dos syncs reais (status mudou no ClickUp, datas ajustadas localmente) **nao envolve LLM** — sao aplicados deterministicamente pelo plano.

## Hash determinismo: por que importa

Sem hash determinismo, o sync entra em "false positive churn":
- Toda linha apareceria como mudada apos qualquer writeback
- Toda data string `"02/abr"` viraria diferente do datetime `2026-04-02` apos normalizacao
- Loop infinito de pushes

Solucoes:
1. **Canonicalizacao:** `_lib.canonical_row()` normaliza datas para ISO antes do hash, trim de strings, marcadores `—` viram `""`
2. **TZ consistente:** `_ts_to_iso()` (em `sync.py`) usa UTC sempre — mesma data em qualquer maquina
3. **Field exclusion:** `clickup_id` NAO entra no hash (e mapping, nao conteudo)
4. **Sort estavel:** `hash_table()` ordena por `No.` numerico antes de concatenar — reordenar linhas no xlsx nao muda o hash agregado

Verifique a estabilidade rodando:
```bash
echo '{"no":"1","etapa":"X","inicio_plan":"02/abr"}' | python3 hash_row.py --stdin --default-year 2026
echo '{"no":"1","etapa":"X","inicio_plan":"2026-04-02"}' | python3 hash_row.py --stdin
# Os dois hashes devem ser identicos.
```
