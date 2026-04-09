---
name: collecting-data
description: >-
  G2.2-E2: Coleta dados de indicadores via execucao de scripts Python standalone.
  O script collect.py le Cards e Indicadores YAML, gera um plano de execucao JSON
  com scripts a executar, roda cada script via subprocess (acesso direto a ClickHouse
  e Bitrix24 via bibliotecas Python), e consolida os outputs JSON em dados validados.
  A skill orquestra 3 comandos: plan → run → consolidate. Zero interpretacao de YAMLs.
  Use when executing the weekly performance cycle (E2 step), when /m7-controle:next
  advances to E2, or when /m7-controle:run-weekly starts the automated pipeline.

  <example>
  Context: Pipeline semanal avanca para E2
  user: "/m7-controle:next"
  assistant: Roda collect.py plan, collect.py run, collect.py consolidate
  </example>

  <example>
  Context: Usuario quer coletar dados de uma vertical especifica
  user: "Coleta os dados de Consorcios para a semana 12"
  assistant: Localiza Cards e Indicadores, roda plan → run → consolidate, apresenta resultados
  </example>
user-invocable: false
---

# Collecting Data — Coleta via Scripts Python Standalone (E2)

> "Zero interpretacao. Scripts acessam dados diretamente. Voce orquestra 3 comandos."

Esta skill coleta dados de indicadores via **execucao de scripts Python standalone**. Cada indicador da Biblioteca tem seu proprio script `.py` que acessa ClickHouse (via `clickhouse-connect`) e Bitrix24 (via `requests`) diretamente, sem MCPs. O script `collect.py` orquestra o ciclo:

1. **`plan`** — Le Cards + Indicadores YAML, gera plano com scripts a executar
2. **`run`** — Executa cada script via `subprocess`, gera `execution-results.json`
3. **`consolidate`** — Valida outputs contra `output_contract`, gera dados consolidados

**PRINCIPIO FUNDAMENTAL**: O LLM NAO interpreta YAMLs de indicadores. O LLM NAO executa queries ou chamadas de API. O LLM apenas roda 3 comandos Python e le os resultados. Toda logica de extracao esta nos scripts standalone e no modulo `m7_extract_utils.py`.

## Dependencias Internas

- [scripts/collect.py](scripts/collect.py) — Motor deterministico (plan + run + consolidate)
- [references/data-quality-rules.md](references/data-quality-rules.md) — Regras de validacao e thresholds
- [references/execution-plan-schema.md](references/execution-plan-schema.md) — Schema do plano JSON v2.0
- [templates/data-quality-report.tmpl.md](templates/data-quality-report.tmpl.md) — Template do Data Quality Report

> **Resolucao de caminhos**: Cards e Indicadores vivem no repositorio do usuario, NAO no plugin.
> Localizar via `Glob('**/cards/{vertical}/*.yaml')` e `Glob('**/Biblioteca-de-Indicadores/_index.yaml')`.
> Todos os outputs sao salvos na pasta do ciclo `{vertical}/{YYYY-MM-DD}/`.

## Pre-requisitos (Entry Criteria)

- Cards de Performance YAML existem no repositorio do usuario para a vertical
- Biblioteca de Indicadores YAML acessivel no repositorio do usuario (v3.0 com campo `script.path`)
- Variaveis de ambiente configuradas: `CLICKHOUSE_HOST`, `CLICKHOUSE_PORT`, `CLICKHOUSE_USER`, `CLICKHOUSE_PASSWORD`, `BITRIX_WEBHOOK_URL` (cada script define seu database internamente)
- Dependencias Python instaladas: `clickhouse-connect`, `requests`, `pyyaml`
- CICLO.md indica E2 como etapa atual (ou execucao forcada via run-weekly)
- Python 3 disponivel

## Timestamps

Sempre que este documento menciona `{timestamp}`, obter a hora real via `date '+%Y-%m-%dT%H:%M'` (Bash). NUNCA usar `00:00` ou estimar.

## Workflow

### Fase 0 — Verificar Ambiente de Execucao

**Esta fase e obrigatoria e executa ANTES de qualquer coleta de dados.**

1. **Verificar variaveis de ambiente** via Bash:

```bash
python3 -c "
import os, sys
required = ['CLICKHOUSE_HOST','CLICKHOUSE_PORT','CLICKHOUSE_USER','CLICKHOUSE_PASSWORD','BITRIX_WEBHOOK_URL']
missing = [v for v in required if not os.environ.get(v)]
if missing:
    print(f'MISSING: {missing}', file=sys.stderr)
    sys.exit(1)
else:
    for v in required:
        val = os.environ[v]
        masked = val[:4] + '***' if len(val) > 4 else '***'
        print(f'{v}={masked}')
    print('Todas as variaveis OK')
"
```

2. **Verificar dependencias Python** via Bash:

```bash
python3 -c "import clickhouse_connect; import requests; import yaml; print('Dependencias OK')"
```

3. **Registrar resultado** no CICLO.md > Log: `[{timestamp}] SKILL:collecting-data — Ambiente verificado: vars={OK|FALHA}, deps={OK|FALHA}`
4. **Se alguma variavel ou dependencia faltar**: registrar em CICLO.md > Anomalias, informar usuario e AGUARDAR decisao
5. **Somente prossiga para Fase 1 se o ambiente estiver OK.**

### Fase 1 — Gerar Plano de Execucao

> **Nota sobre periodo**: Os parametros `data_inicio` e `data_fim` cobrem o PERIODO COMPLETO (mes inteiro), nao apenas a semana corrente. Ler estes valores do CICLO.md (header `Periodo`). A granularidade e usada pelas fases analiticas (E3-E6), nao pela coleta.

1. **Localizar Cards** da vertical via `Glob('**/cards/{vertical}/*.yaml')`
2. **Localizar Biblioteca de Indicadores** via `Glob('**/Biblioteca-de-Indicadores/_index.yaml')`
3. **Executar o script planner** via Bash:

```bash
python3 {path_to_plugin}/skills/collecting-data/scripts/collect.py plan \
  --cards-dir {cards_path} \
  --indicators-dir {indicators_path} \
  --cycle-folder {cycle_folder} \
  --param data_inicio={data_inicio} \
  --param data_fim={data_fim}
```

4. **Verificar que `execution-plan.json` foi gerado** no cycle folder
5. **Ler o execution-plan.json** e exibir resumo ao usuario:

```
Plano de Execucao E2 — {vertical}

Scripts: {total_scripts}
Checksums verificados: {checksums_verified}/{total_scripts}
Test status: passed={N}, untested={N}, failed={N}
Parametros: data_inicio={data_inicio}, data_fim={data_fim}

Steps:
  1. {indicator_name} ({source_type}) — {script_path}
  2. ...

Indicadores ignorados: {skipped}
Indicadores nao encontrados: {not_found}

Prosseguir com a execucao?
```

6. **Se houver checksums FALHA**: alertar usuario — scripts foram modificados desde o ultimo teste
7. **Se houver indicadores nao encontrados que sao kpi_principal**: PARAR e informar usuario
8. **Registrar no CICLO.md > Log**: `[{timestamp}] SKILL:collecting-data — Plano gerado: {total_scripts} scripts`

### Fase 2 — Executar Scripts

> **REGRA ABSOLUTA**: Um unico comando executa todos os scripts.
> O LLM NAO faz loop. O collect.py run gerencia tudo internamente via subprocess.

1. **Executar o runner** via Bash:

```bash
python3 {path_to_plugin}/skills/collecting-data/scripts/collect.py run \
  --plan {cycle_folder}/execution-plan.json \
  --cycle-folder {cycle_folder} \
  --timeout 900 \
  --parallel
```

2. **Verificar o exit code**:
   - Exit 0: execucao concluida com quorum OK
   - Exit 2: quorum insuficiente (<80% scripts com sucesso) — pipeline BLOQUEADO

3. **Ler `execution-results.json`** e verificar resultados:
   - Quantos scripts tiveram sucesso, erro, skip
   - Se quorum OK (>=80%)

4. **Se quorum FALHOU** (exit code 2):
   - Registrar em CICLO.md > Anomalias
   - Informar usuario com detalhes dos scripts que falharam
   - Apresentar opcoes:
     1. Retry scripts que falharam (reexecutar `collect.py run`)
     2. Prosseguir com dados parciais
     3. Abortar ciclo
   - **AGUARDAR decisao do usuario** — NAO prosseguir automaticamente

5. **Se algum script individual falhou** mas quorum esta OK:
   - Registrar em CICLO.md > Anomalias
   - Informar usuario sobre os scripts que falharam
   - Perguntar se deseja prosseguir (dados parciais) ou retry

6. **Registrar no CICLO.md > Log**: `[{timestamp}] SKILL:collecting-data — Execucao: {success}/{total} scripts com sucesso ({quorum_pct}%)`

### Fase 3 — Consolidar Resultados

1. **Executar o consolidator** via Bash:

```bash
python3 {path_to_plugin}/skills/collecting-data/scripts/collect.py consolidate \
  --plan {cycle_folder}/execution-plan.json \
  --results {cycle_folder}/execution-results.json \
  --indicators-dir {indicators_path} \
  --cycle-folder {cycle_folder} \
  --vertical {vertical}
```

2. **Verificar que os outputs foram gerados**:
   - `dados/dados-consolidados-{vertical}.json` — dataset consolidado
   - `dados/provenance.json` — SHA-256 de cada output file
   - `data-quality/data-quality-report.md` — relatorio de qualidade

3. **Se o script retornar exit code 2**: alertas criticos detectados, pipeline deve ser bloqueado

4. **Registrar no CICLO.md > Log**: `[{timestamp}] SKILL:collecting-data — Consolidacao concluida: {N} indicadores processados`

### Fase 4 — Gate de Qualidade

1. **Ler `dados-consolidados-{vertical}.json`** e verificar campo `metadata.qualidade_geral`
2. **Se qualidade_geral == "Critico"**:
   - Registrar em CICLO.md > Anomalias
   - Exibir alertas criticos ao usuario
   - **BLOQUEAR pipeline** — E3 NAO inicia
   - Sugerir: `"Resolva os alertas criticos e execute /m7-controle:next {vertical} para retomar de E2"`
3. **Se qualidade_geral == "Atencao"**: prosseguir com ressalvas registradas
4. **Avaliar quality_checks_pending** do JSON consolidado:
   - Para cada check, avaliar pass/fail com base nos dados fornecidos
   - Registrar resultados no CICLO.md

### Fase 5 — Apresentar Resultados

Exibir tabela de proveniencia ao usuario:

```
E2 Coleta Concluida — Resumo de Proveniencia

| Indicador | Script | Linhas | Arquivo | Status | Tempo |
|-----------|--------|--------|---------|--------|-------|
| volume_consorcio_mensal | volume_consorcio_mensal.py | 94 | volume_...json | OK | 3.2s |
| taxa_conversao_funil_con | taxa_conversao_funil_con.py | 245 | taxa_...json | OK | 8.1s |
| ... | ... | ... | ... | ... | ... |

Proveniencia: {success}/{total} scripts com sucesso ({quorum_pct}%)
Qualidade geral: {OK|Atencao|Critico}
```

Registrar conclusao no CICLO.md:
- Log: `[{timestamp}] SKILL:collecting-data — E2 concluido. {N} indicadores coletados, qualidade: {status}`

## Exit Criteria

- [ ] Variaveis de ambiente verificadas na Fase 0 (resultado registrado no CICLO.md)
- [ ] execution-plan.json gerado pelo script collect.py plan (Fase 1)
- [ ] Scripts executados via collect.py run (Fase 2)
- [ ] Cada script com sucesso produziu um output JSON em dados/raw/
- [ ] execution-results.json gerado com status por script
- [ ] Consolidacao executada pelo script collect.py consolidate (Fase 3)
- [ ] dados-consolidados-{vertical}.json gerado com script_execution_log e _verification
- [ ] provenance.json gerado com SHA-256 de cada output file
- [ ] data-quality-report.md gerado
- [ ] Nenhum alerta critico (caso contrario, pipeline bloqueia)
- [ ] Tabela de proveniencia apresentada ao usuario (Fase 5)

## Anti-Patterns

- NUNCA interprete YAMLs de indicadores — o script collect.py faz isso
- NUNCA execute queries SQL ou chamadas de API diretamente — os scripts standalone fazem isso
- NUNCA construa dados consolidados sem rodar o script consolidate
- NUNCA execute scripts sem verificar que o ambiente (variaveis + dependencias) esta OK
- NUNCA execute scripts com checksum nao verificado sem alertar o usuario
- NUNCA execute scripts com test_status=failed sem aprovacao explicita do usuario
- NUNCA invente dados se um script falhar — o collect.py registra o erro e voce PARA
- NUNCA defina variaveis de ambiente com valores inventados
- NUNCA avance para E3 se houver alertas criticos
- NUNCA gere dados sinteticos, placeholders ou "exemplos ilustrativos"
- NUNCA use Cards com status diferente de `active` (o script filtra, mas nao confie apenas nele)
- NUNCA prossiga apos falha de quorum sem decisao do usuario — PARE e reporte
