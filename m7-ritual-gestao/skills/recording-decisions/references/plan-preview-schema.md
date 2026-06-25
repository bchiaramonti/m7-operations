# Plan Preview Schema v2.0 — `plan-preview.json`

> **v2.0 (2026-05-31)** — Canonicalizacao apos auditoria revelar 4 schemas circulando
> entre Seg WL/RE S20-S22 + Cons S21-S22. Schema fixo + validador gatekeeper em
> `render_ata.py` que falha em commit se `schema_version != "2.0"`.
>
> v1.0 (2026-05-06) era o schema original com `responsavel` aninhado em
> `payload.custom_fields[]` — ver secao [Migracao v1.0 → v2.0](#migracao-v10--v20).

## Proposito

`plan-preview.json` e a **unica fonte de verdade** entre as duas invocacoes
da skill `recording-decisions` (preview → aprovacao do usuario → commit). Ele congela:

- O conteudo das decisoes da ata (texto exato apos parse das notas)
- Os campos canonicos top-level de cada contramedida nova
- Os estados `before` das tasks que serao atualizadas
- A lista de duplicatas detectadas

Apos o usuario aprovar, o agente em modo `commit` le este JSON e executa
**exatamente** o que foi planejado — sem re-parsing das notas, sem re-coleta
do estado ClickUp. Isso garante que o que foi mostrado ao usuario e o que
sera escrito.

## Schema v2.0 (TypeScript-style)

```typescript
interface PlanPreview {
  // ─────── Metadados ───────
  schema_version: "2.0";              // OBRIGATORIO — validador falha em qualquer outro valor
  generated_at: string;                // ISO 8601 — momento de geracao do preview
  vertical: string;                    // ex: "consorcios"
  subnivel: string | null;             // ex: "wl" | "re" | null
  data_referencia: string;             // YYYY-MM-DD — data do ritual
  nivel: string;                       // ex: "N3"
  participantes: string[];
  duracao: string | null;              // ex: "~37 min"
  wbr_referencia: string | null;       // ex: "Maio 2026, semana 5 (MTD) — wbr-seguros-re-2026-05-28"
  card_path: string;                   // path absoluto do card processado (ou label "card_xxx.yaml v1.8.9")
  notas_source: {                      // de onde vieram as notas
    type: "transcricao_canonica" | "input_usuario";
    path: string | null;
  };

  // ─────── Decisoes do ritual (D-NNN) ───────
  decisoes: Array<{
    ata_id: string;                    // "D-001", "D-002" — prefix OBRIGATORIO "D-"
    titulo: string;                    // titulo curto (1 linha)
    descricao: string;                 // texto livre da decisao
    responsavel: string | null;        // nome canonico (resolvido via Card.assessor_aliases se preciso)
    transcricao_ref: string | null;    // ex: "11:14, 13:45 — Pedro: 'nao deixem para fechar...'"
    contexto: string | null;           // referencia ao WBR/anomalia que originou
    gera_contramedida: string | null;  // ata_id da contramedida correspondente, se houver
    // NOTA: NAO ha campo `prazo` em decisoes (memory feedback_decisoes_sem_prazo)
  }>;

  // ─────── Contramedidas NOVAS a criar no ClickUp ───────
  contramedidas_novas: Array<{
    ata_id: string;                                  // "C-001", "C-002" — prefix OBRIGATORIO "C-"
    decisao_origem: string | null;                   // "D-NNN" da decisao que originou (opcional)
    name: string;                                    // TOP-LEVEL — <=80 chars, verbo no infinitivo
    descricao: string;                               // TOP-LEVEL — markdown longo (contexto + razao + criterio)
    due_date: string | null;                         // TOP-LEVEL — YYYY-MM-DD (canonico, nao due_date_iso)
    priority_clickup: 1 | 2 | 3 | 4;                 // TOP-LEVEL
    priority_label: "urgent"|"high"|"normal"|"low";  // TOP-LEVEL (era "critica"/"alta"/"media"/"baixa" em v1.0)
    responsavel_externo_label: string;               // TOP-LEVEL OBRIGATORIO — nome humano
    responsavel_externo_option_value: number;        // TOP-LEVEL OBRIGATORIO — ClickUp option_id (int)
    indicador_impactado: string | null;              // nome do KPI/PPI
    indicador_impactado_option_id: string | null;    // UUID ClickUp do option
    origem: string;                                  // ex: "Ritual N3"
    origem_option_id: string;                        // UUID ClickUp do option
    volume_impacto: number | null;                   // R$ ou unidades
    receita_impacto: number | null;                  // R$
    justificativa_prio: string;                      // texto curto para a ata
    transcricao_ref: string | null;                  // referencia textual da transcricao
    // OPCIONAL: payload ClickUp-only quando necessario (raro)
    clickup_create_payload?: {
      list_id: "901326795742";
      status: string;                                // tipicamente "to do"
      // NAO duplicar name/description/due_date/priority/custom_fields aqui.
      // Esses sao top-level no item — o script de commit ClickUp deriva.
    };
  }>;

  // ─────── Tasks EXISTENTES a atualizar ───────
  tasks_atualizadas: Array<{
    clickup_id: string;                              // "86xxxxxxx" — id ClickUp da task existente
    name_humano: string;                             // legibilidade humana (titulo da task)
    before: {                                        // snapshot lido via clickup_get_task no momento do preview
      status: string;
      due_date: string | null;                       // YYYY-MM-DD
    };
    after: {                                         // campos a serem definidos
      status?: string;
      due_date?: string | null;
    };
    comment: string;                                 // texto literal de clickup_create_task_comment
    decisao_origem?: string | null;                  // "D-NNN" (opcional)
  }>;

  // ─────── Duplicatas detectadas (NAO criadas) ───────
  duplicatas_detectadas: Array<{
    proposed_name: string;
    existing_id: string;
    existing_url: string;
    existing_name: string;
    similarity_score: number;                        // 0..1
    razao: string;                                   // ex: "match exato de name + responsavel_externo"
    decisao_origem: string | null;
  }>;

  // ─────── Outras secoes da ata ───────
  escalonamentos: Array<{                            // levados ao N1, sem task ClickUp
    item: string;
    decisao_origem: string | null;
  }>;
  proximos_passos_nao_clickup: Array<{               // gerais, sem task formal
    acao: string;
    responsavel: string | null;
    prazo: string | null;                            // YYYY-MM-DD ou "a definir" / "continuo"
  }>;
  pendencias: string[];                              // itens nao resolvidos no preview (mostrados ao usuario)
  decisoes_recorrentes_adicionadas_round2?: Array<{  // opcional — decisoes que entraram so no segundo passo
    ata_id: string;                                  // "D-NNN"
    titulo: string;
    descricao: string;
  }>;
  metricas_resumo: {
    total_decisoes: number;
    total_contramedidas_novas: number;
    criticas: number;                                // priority_clickup=1
    altas: number;                                   // priority_clickup=2
    medias: number;                                  // priority_clickup=3
    baixas: number;                                  // priority_clickup=4
    total_tasks_atualizadas: number;
    total_proximos_passos: number;
    total_escalonamentos: number;
    total_duplicatas: number;
    total_pendencias: number;
  };
}
```

## Regras de Geracao

1. **`schema_version: "2.0"` LITERAL** — sem este campo (ou com qualquer outro valor),
   o `render_ata.py` aborta com erro em commit (validador `_assert_schema_v2()`).
2. **Campos top-level OBRIGATORIOS em `contramedidas_novas[]`**:
   `name`, `descricao`, `due_date`, `priority_clickup`, `priority_label`,
   `responsavel_externo_label`, `responsavel_externo_option_value`.
   **NUNCA aninhar esses campos em `payload`/`clickup_create_payload`** — eles sao top-level.
3. **`ata_id` prefix fixo**: `D-NNN` para decisoes, `C-NNN` para contramedidas.
   Numeracao sequencial dentro do ciclo (ex: C-006 se ja existem C-001..C-005 em ritual anterior — manter contagem cumulativa por vertical/subnivel).
4. **Idempotencia**: gerar o mesmo plano duas vezes a partir das mesmas notas
   deve produzir JSONs identicos (exceto `generated_at`).
5. **Snapshot de `before`**: o `clickup_get_task` para popular `before` deve
   ser chamado UMA vez na Fase 4.5 e cacheado — nao re-chamar no commit.
6. **`due_date` null**: quando o usuario nao informou prazo, deixar `null`
   e NAO inferir. O sumario apresentado ao usuario deve listar "prazo a definir"
   como pendencia explicita.
7. **`responsavel_externo_option_value`**: resolver no preview via mapa canonico em
   [clickup-actions-schema.md](clickup-actions-schema.md). Commit NAO deve precisar
   resolver nada.
8. **`description`/`descricao` da contramedida**: deve incluir 3 blocos:
   - **Contexto**: referencia ao WBR (checkpoint + indicador + semaforo)
   - **Razao**: por que esta contramedida foi decidida
   - **Criterio de sucesso**: como saberemos que resolveu

## Validacao em Modo `commit`

Antes de prosseguir para Fase 5, o agente deve:

1. Verificar `mtime(plan-preview.json) < 24h` — alem disso, estado ClickUp
   pode ter divergido. Alertar e exigir re-preview.
2. **Verificar `schema_version == "2.0"`** — se mismatch, ERRO bloqueante
   (executado automaticamente pelo `render_ata.py::_assert_schema_v2()`).
3. Re-validar (somente leitura) que cada `clickup_id` em `tasks_atualizadas`
   ainda existe via `clickup_get_task`. Se uma task foi deletada entre
   preview e commit: alertar e pular essa atualizacao.
4. Para cada `contramedida_nova`: re-checar duplicata via snapshot ja
   cacheado em `cycle_folder/dados/raw/clickup-tasks-{vertical}.json` —
   se uma duplicata nova surgiu (criada por outro caminho entre preview e
   commit), alertar e pular.

## Exemplo Minimo v2.0

```json
{
  "schema_version": "2.0",
  "generated_at": "2026-05-31T16:15:00-03:00",
  "vertical": "seguros",
  "subnivel": "re",
  "nivel": "N3",
  "data_referencia": "2026-05-29",
  "participantes": ["Pedro Villarroel", "Emmanuel Martins", "Joel Freitas", "Samuel Sinval"],
  "duracao": "~37 min",
  "wbr_referencia": "Maio 2026, semana 5 (vespera fechamento) — wbr-seguros-re-2026-05-28",
  "card_path": "card_seg_re_n3_001.yaml v1.8.9",
  "notas_source": {
    "type": "transcricao_canonica",
    "path": "/abs/03-Rituais/N3/Seguros-re/Semanal/2026-S22/ata/Transcricao.md"
  },
  "decisoes": [
    {
      "ata_id": "D-001",
      "titulo": "Registrar ganhos/perdidos de Maio no Bitrix ate amanha",
      "descricao": "Emmanuel e Samuel registrarao todos os ganhos e perdidos pendentes de Maio no Bitrix hoje (29/05) ou amanha (30/05) antes do fechamento do mes.",
      "responsavel": "Emmanuel Martins + Samuel Sinval",
      "transcricao_ref": "11:14, 13:45 — Pedro: 'nao deixem para fechar nada no mes'",
      "contexto": "WBR S22 — taxa de conversao Mai pode poluir Junho",
      "gera_contramedida": null
    }
  ],
  "contramedidas_novas": [
    {
      "ata_id": "C-006",
      "decisao_origem": null,
      "name": "Avaliar 26 deals estagnados em Cotacao e Proposta Comercial de Emmanuel",
      "descricao": "**Contexto**: WBR S22 reporta 26 deals estagnados de Emmanuel (R$ 275K parados).\n**Razao**: Backlog confirma risco preditivo do W-1.\n**Criterio de sucesso**: triagem completa win/lose/postergar em 1 semana.",
      "due_date": "2026-06-05",
      "priority_clickup": 1,
      "priority_label": "urgent",
      "responsavel_externo_label": "Emmanuel Martins",
      "responsavel_externo_option_value": 13,
      "indicador_impactado": "oportunidades_estagnadas_funil_seg",
      "indicador_impactado_option_id": "63408a6e-f5b9-481e-95e1-8a06b90811db",
      "origem": "Ritual N3",
      "origem_option_id": "7bed3d9a-12de-4982-90df-9d8d6c737a53",
      "volume_impacto": 275765,
      "receita_impacto": null,
      "justificativa_prio": "Indicador Vermelho + volume R$ 275K + risco preditivo confirmado em 1 ciclo",
      "transcricao_ref": "Cross-link com WBR Estruturado 28/05 (Saude do Pipeline)",
      "clickup_create_payload": {
        "list_id": "901326795742",
        "status": "to do"
      }
    }
  ],
  "tasks_atualizadas": [
    {
      "clickup_id": "86ahmr46w",
      "name_humano": "Destravar oportunidades estagnadas com Nacha, Cleo, David Oliveira...",
      "before": {"status": "atrasada", "due_date": "2026-05-28"},
      "after": {"status": "pendente", "due_date": "2026-06-05"},
      "comment": "[Ritual 2026-05-29] Pedro ja passou a lista atualizada. Prazo reajustado para 05/06.",
      "decisao_origem": null
    }
  ],
  "duplicatas_detectadas": [],
  "escalonamentos": [],
  "proximos_passos_nao_clickup": [
    {
      "acao": "Emmanuel + Samuel: registrar atividades planejadas dos 65 deals ativos no Bitrix",
      "responsavel": "Emmanuel + Samuel",
      "prazo": "continuo"
    }
  ],
  "pendencias": [
    "Discussao sobre transferir deals Emmanuel -> Samuel: proposta verbalizada sem escopo formal — NAO virou contramedida."
  ],
  "metricas_resumo": {
    "total_decisoes": 1,
    "total_contramedidas_novas": 1,
    "criticas": 1,
    "altas": 0,
    "medias": 0,
    "baixas": 0,
    "total_tasks_atualizadas": 1,
    "total_proximos_passos": 1,
    "total_escalonamentos": 0,
    "total_duplicatas": 0,
    "total_pendencias": 1
  }
}
```

---

## Migracao v1.0 → v2.0

Mudancas estruturais entre v1.0 (2026-05-06) e v2.0 (2026-05-31):

| Aspecto | v1.0 | v2.0 |
|---------|------|------|
| `schema_version` | `"1.0"` | `"2.0"` (validador falha em qualquer outro) |
| `ata_id` prefix contramedida | `"CM-001"` | `"C-001"` |
| `ata_id` prefix decisao | `"D-001"` | `"D-001"` (sem mudanca) |
| `contramedidas_novas[].name` | aninhado em `payload.name` | TOP-LEVEL |
| `contramedidas_novas[].descricao` | aninhado em `payload.description` | TOP-LEVEL (campo `descricao`) |
| `contramedidas_novas[].due_date` | `payload.due_date_iso` + `payload.due_date_ms` | TOP-LEVEL `due_date` (YYYY-MM-DD apenas) |
| `contramedidas_novas[].priority_label` | aninhado em `payload.priority_label` (`critica/alta/media/baixa`) | TOP-LEVEL `priority_label` (`urgent/high/normal/low`) |
| `contramedidas_novas[].priority_clickup` | aninhado em `payload.priority` | TOP-LEVEL `priority_clickup` |
| Responsavel Externo | `payload.custom_fields[field_name="Responsavel Externo"]` | TOP-LEVEL `responsavel_externo_label` + `responsavel_externo_option_value` |
| Indicador Impactado | `payload.custom_fields[]` ou top-level `indicador_impactado` (so string) | TOP-LEVEL `indicador_impactado` + `indicador_impactado_option_id` |
| Origem | `payload.custom_fields[]` ou ausente | TOP-LEVEL `origem` + `origem_option_id` |
| `decisoes[].id` | `"D-001"` em campo `id` | renomeado para `ata_id` |
| `decisoes[].decisao` | texto livre | renomeado para `descricao` + novo campo `titulo` curto |
| `decisoes[].prazo` | YYYY-MM-DD ou null | **REMOVIDO** (decisoes nao tem prazo — memory `feedback_decisoes_sem_prazo`) |
| `decisoes[].transcricao_ref` | inexistente | NOVO — para auditoria |
| `tasks_atualizadas[].task_id` | `"86xxxxxxx"` em `task_id` | renomeado para `clickup_id` |
| `tasks_atualizadas[].task_name` | string | renomeado para `name_humano` |
| `tasks_atualizadas[].before.due_date_ms` | epoch ms | renomeado para `before.due_date` (YYYY-MM-DD) |
| `proximos_passos[]` | nome do array | renomeado para `proximos_passos_nao_clickup` |
| `metricas_resumo` | inexistente | NOVO — agregados para sumario rapido |

### Por que canonicalizar

- **Diagnostico:** auditoria revelou 4 schemas circulando entre Seg WL/RE S20-S22 + Cons S21-S22. Cada execucao o decision-recorder adaptava ao que "achava" da estrutura.
- **Consequencia:** `slack_send.py:_extract_responsavel` virou parser defensivo de 4 caminhos; `render_ata.py:185` ganhou triplo fallback. A cada novo schema, mais fallback. Hoje (Seg RE S22) gerou "(sem responsavel)" silenciosamente no preview porque parser nao reconhecia Schema 4.
- **Solucao:** schema fixo + gatekeeper (`_assert_schema_v2()` em `render_ata.py`) + parsers limpos sem fallback.

### Compatibilidade com plan-previews antigos

**Nao ha retro-compatibilidade.** Plan-previews v1.0 antigos (Seg WL S20, Cons S21, etc.) ja foram processados e suas atas/ClickUp tasks ja foram commitadas. Eles ficam imutaveis como historicos.

Se for necessario re-rodar um ciclo antigo apos 2026-05-31:
1. Apagar o `plan-preview.json` antigo do `RITUAL_DIR/ata/`
2. Re-executar `/m7-ritual-gestao:record-decisions {vertical}{ {sub}} --modo preview` — decision-recorder v2.0 emite novo JSON

### Decision-recorder agent

O agente `decision-recorder` deve sempre emitir `schema_version: "2.0"` literal em qualquer nova invocacao. Detalhes do prompt em [agents/decision-recorder.md](../../../agents/decision-recorder.md).
