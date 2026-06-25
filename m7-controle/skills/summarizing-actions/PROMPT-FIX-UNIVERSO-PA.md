# Prompt para fix do Universo de Plano de Acao (E4)

> Este arquivo contem o prompt completo para fixar a definicao de "universo
> de PAs ativas" no E4 (`summarizing-actions`) do plugin m7-controle, conforme
> feedback do gestor 2026-05-05 durante o ritual G2.3 de Consorcios S19.

## Contexto

O **Slide 4 do deck** (PA Status) mostra `total_ativas` lido do `analise/action-report.md`,
que vem de `metricas_agregadas.total_ativas` no `wbr-{vertical}-{ciclo}.data.json`. Hoje
esse numero e o **snapshot atual do ClickUp**: tasks com status open + filtro Vertical=consorcios
+ exclusao subtasks + responsavel_externo resolvido (filtros canonicos aplicados em
E2 Fase 1.5 via ClickUp MCP).

**O que o gestor quer:** o universo deve ser:

```
universo_ritual_atual = {
    PAs que estavam ativas no inicio do ritual_anterior (snapshot anterior)
} UNION {
    PAs criadas durante o ritual_anterior (registradas em ata via decision-recorder)
}
```

Ou seja: o numero do Slide 4 deve representar **"o que o ritual passado deixou em curso
+ o que ele decidiu adicionar"** — nao um snapshot ao vivo do ClickUp no momento da extracao.

A diferenca e relevante porque:
- PAs FECHADAS desde o ritual passado precisam aparecer (com status concluido) — hoje
  somem do snapshot.
- PAs CRIADAS por outros rituais (outras verticais, outros niveis) NAO devem aparecer
  no escopo deste ritual.
- PAs criadas DEPOIS do ritual passado por terceiros (ad-hoc no ClickUp, sem passar
  por ata) NAO devem aparecer aqui — entram no proximo ritual.

## Objetivo do Fix

Modificar `summarizing-actions` (E4) para:

1. Carregar **snapshot do ritual anterior** (`{ritual_dir_anterior}/ata/ata-*.{md,json}`
   ou alternativa equivalente).
2. Extrair lista de PAs **vigentes no momento do ritual anterior** (snapshot inicial).
3. Extrair lista de PAs **adicionadas/decididas durante o ritual anterior** (delta da ata).
4. Construir `universo_ritual_atual` = uniao dos dois conjuntos.
5. Para cada PA do universo, buscar status atual no `clickup-tasks-{vertical}.json` (E2 F1.5)
   e classificar: concluida / em_dia / atrasada / critica / cancelada.
6. Substituir `metricas_agregadas` no `wbr-*.data.json` para refletir esse universo
   (e nao o snapshot atual filtrado).
7. Adicionar campos novos para rastreabilidade:
   - `universo_origem`: "ritual_anterior + decisoes_anteriores"
   - `delta_vs_snapshot`: numero de tasks no ClickUp filtradas que NAO entram nesse universo
     (criadas ad-hoc apos o ritual anterior — vao para o proximo ciclo)
   - `tasks_excluidas_ad_hoc`: lista dos IDs ClickUp excluidos com motivo

## Prompt detalhado para implementacao

```
ROLE: Voce e um engenheiro de pipeline trabalhando no plugin m7-controle, especificamente
em E4 (skill `summarizing-actions`, agent `analyst`). Sua tarefa e refatorar a definicao
de universo de PAs ativas conforme decisao do gestor (2026-05-05 ritual Consorcios S19).

OBJETIVO: O numero `total_ativas` (e seus desdobramentos em em_dia/atrasadas/criticas)
no `wbr-{vertical}-{ciclo}.data.json` precisa representar o universo do ritual anterior
(snapshot anterior + decisoes anteriores), nao o snapshot ClickUp atual.

LEITURAS OBRIGATORIAS antes de codar:
1. `m7-operations/m7-controle/skills/summarizing-actions/SKILL.md` — entender E4 atual
2. `m7-operations/m7-controle/agents/analyst.md` — entender como o agent monta `acoes`
   no canonical data JSON
3. `m7-operations/m7-ritual-gestao/skills/recording-decisions/SKILL.md` — entender a
   estrutura da ata gerada por E5 (G2.3)
4. Sample real: `Arquivos de Bruno Chiaramonti - desempenho/03-Rituais/N3/Consorcios/Semanal/2026-S18/ata/`
   — formato real da ata anterior (se existir)
5. Sample real: `Arquivos de Bruno Chiaramonti - desempenho/02-Controle/Consorcios/2026-05/2026-05-04/wbr/wbr-consorcios-2026-05-04.data.json`
   — campo `acoes` atual

PASSOS:

1. ANALISE DA ATA ANTERIOR (formato canonico):
   - Verificar se existe schema documentado para ata em recording-decisions/SKILL.md
   - Se nao houver, propor schema: ata YAML com campos:
     ```yaml
     ata:
       ritual_id: "S18-consorcios-2026-04-29"
       data_ritual: "2026-04-29T08:00"
       snapshot_clickup_inicial:
         tasks_ativas:
           - id: "86agx9u71"
             titulo: "Icoforte: decidir win/lose"
             owner: "Joel Freitas"
             status_no_inicio: "open"
       decisoes:
         - tipo: "nova_pa"          # nova / encerramento / mudanca_owner / mudanca_prazo
           clickup_task_id: "86xxx"  # criado via clickup_create_task
           titulo: "Auditoria bridge"
           owner: "Pedro Villarroel"
           prazo: "2026-05-14"
         - tipo: "encerramento"
           clickup_task_id: "86yyy"
           motivo: "concluida pos-ritual"
     ```
   - Se schema diferente, se adapte; **NAO assuma o schema antes de ler**

2. RESOLUCAO DE PATH DA ATA ANTERIOR:
   - Glob `{cycle_folder}/../*/wbr-*.md` ou `03-Rituais/N{N}/{Vertical}/{Cadencia}/*/ata/`
   - Selecionar ciclo imediatamente anterior por data
   - Se nao houver ata anterior (primeiro ritual ou ata ausente):
     - Fallback: usar snapshot ClickUp atual como universo (comportamento atual)
     - Logar warning explicito no CICLO.md > Anomalias

3. CONSTRUIR universo_ritual_atual:
   ```python
   tasks_anteriores = ata_anterior.get("snapshot_clickup_inicial", {}).get("tasks_ativas", [])
   ids_anteriores = {t["id"] for t in tasks_anteriores}

   decisoes_novas = [d for d in ata_anterior.get("decisoes", []) if d["tipo"] == "nova_pa"]
   ids_novas = {d["clickup_task_id"] for d in decisoes_novas if d.get("clickup_task_id")}

   universo_ids = ids_anteriores | ids_novas
   ```

4. CRUZAR COM SNAPSHOT CLICKUP ATUAL:
   - Carregar `{cycle_folder}/dados/raw/clickup-tasks-{vertical}.json`
   - Para cada task atual, marcar:
     - `in_universe = task.id in universo_ids`
     - Se `in_universe and status == "concluida"` → categoria: concluida
     - Se `in_universe and status == "open" and aging > 7d` → atrasada
     - Se `in_universe and status == "open" and aging > 14d` → critica
     - Se `in_universe and status == "open" and aging <= 7d` → em_dia
     - Se `not in_universe` → ad_hoc (NAO conta nas metricas)

5. RECALCULAR metricas_agregadas:
   ```python
   metricas_agregadas = {
       "total_ativas": len(universo_ids),  # NAO mais len(snapshot atual)
       "concluidas_30d": ...,  # tasks do universo concluidas desde ritual_anterior
       "em_dia": ...,
       "atrasadas": ...,
       "criticas": ...,
       "universo_origem": "ritual_anterior + decisoes_anteriores",
       "delta_vs_snapshot": len(snapshot_atual) - len(universo_ids & snapshot_atual_ids),
       "tasks_excluidas_ad_hoc": [...]  # ate 10 IDs excluidas com motivo
   }
   ```

6. SUBSTITUIR `acoes.metricas_agregadas` no canonical data JSON.
7. PRESERVAR demais campos de `acoes` (criticas/atrasadas/em_dia_priorizadas/eficacia_concluidas/gaps_diagnostico_vs_plano) — esses ja sao listas detalhadas que podem ser filtradas pelo universo.

VALIDACAO:
- `total_ativas` antes vs depois (logar diferenca explicita)
- `tasks_excluidas_ad_hoc` deve incluir todas as tasks criadas no ClickUp DEPOIS da
  data do ritual anterior sem passar por ata
- Adicionar campo `_universo_definition` com explicacao textual no JSON para auditoria

EDGE CASES:
- Ata anterior ausente → fallback snapshot atual + warning
- Ata anterior sem `snapshot_clickup_inicial` → tentar reconstruir via ClickUp
  filtrando tasks com `date_created < data_ritual_anterior` (mais fragil mas funciona)
- Decisao com `clickup_task_id` null → indica falha do decision-recorder; logar mas
  nao bloquear

DEPENDENCIAS:
- E5 (recording-decisions, G2.3) precisa garantir que o snapshot inicial e gravado
  na ata + que toda decisao "nova_pa" gere clickup_task_id de fato. Se isso nao esta
  feito, primeiro fixar la antes de mexer aqui.

ARTEFATOS GERADOS:
- `summarizing-actions/SKILL.md` atualizada (passos novos)
- `analyst.md` atualizada (novo metodo de calculo de universo)
- Funcoes Python helper se necessario (em scripts/)
- Versao bump: m7-controle bumped (provavelmente minor — feature nova)

NAO INCLUIR NESTE FIX:
- Mudancas no Slide 4 do deck (build_deck.py) — esse ja le `metricas_agregadas` e
  re-calcula automaticamente quando o JSON mudar. Verificar com 1 ciclo de teste
  apos o fix antes de sinalizar como concluido.
- Schema da ata se ja existir — manter compatibilidade com decision-recorder atual.
```

## Validacao depois de implementar

Rodar 1 ciclo de teste:
```
/m7-controle:run-weekly consorcios   # gera novo wbr-*.data.json com universo correto
/m7-ritual-gestao:prepare-ritual consorcios  # rodam scripts; Slide 4 atualizado
```

Comparar `metricas_agregadas.total_ativas` antes vs depois. Validar com gestor que o
numero faz sentido. Se sim, marcar fix como completo e versionar m7-controle.
