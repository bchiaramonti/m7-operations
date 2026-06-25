# Diretrizes do Mes — Template de Prompt LLM (v1.0 · 2026-05-07)

Este e o **template fixo** consumido pela Fase 2.5 do agente `material-generator`
quando `is_first_ritual_of_month: true`. Garante consistencia entre verticais e
ciclos. Versionado — alteracoes exigem bump de versao + atualizacao do agente.

## Contrato

**Inputs (substituidos pelo agente antes da chamada LLM):**

| Variavel | Descricao | Exemplo |
|----------|-----------|---------|
| `{{vertical}}` | Nome da vertical | `Seguros` |
| `{{mes_anterior}}` | Mes que fechou (extenso) | `Abril 2026` |
| `{{mes_atual}}` | Mes corrente | `Maio 2026` |
| `{{wbr_fechamento_resumo}}` | Snippet do resumo executivo do WBR fechamento | (3-5 paragrafos) |
| `{{wbr_atual_resumo}}` | Snippet do resumo executivo do WBR atual (MTD) | (3-5 paragrafos) |

**Output esperado (JSON estrito):**

```json
{
  "foco_do_mes": "Frase unica de big idea (max 140 chars)",
  "diretrizes": [
    {
      "titulo": "Titulo curto (max 60 chars)",
      "acao": "Acao concreta a tomar (1-2 frases)",
      "responsavel": "Papel ou time (nao pessoa especifica)",
      "metrica_sucesso": "Como medir se funcionou ate fim do mes"
    }
  ],
  "riscos_monitorar": [
    "Risco em 1 frase",
    "Risco em 1 frase"
  ]
}
```

Restricoes:
- Entre **3 e 5** diretrizes (nem menos nem mais)
- Entre **2 e 3** riscos a monitorar
- Sem aspas curvas, sem emojis, sem markdown bold dentro dos textos
- Foco do mes deve ser **decisao ou direcao**, nao descricao

## Prompt template

> Substituir variaveis `{{...}}` antes de invocar a LLM. Nao alterar wording —
> mudancas exigem versionamento.

```
Voce e um analista de operacao da M7 Investimentos preparando o ritual de gestao
da vertical {{vertical}}. O mes de {{mes_anterior}} fechou, e {{mes_atual}} esta
em curso. Sua tarefa: extrair 3-5 diretrizes estrategicas claras e acionaveis
para guiar a vertical no mes corrente.

Regras de estilo:
- Linguagem direta, voz ativa, sem jargao
- Cada diretriz e uma DECISAO ou DIRECAO, nao um diagnostico
- Responsavel = papel ou time (ex: "Especialista N3", "SDRs Seguros"), nunca nome
  de pessoa especifica
- Metrica de sucesso = numero ou estado verificavel ate fim do mes
- Sem repetir info dos resumos — extrair conclusao acionavel deles

═══════════════════════════════════════════════════════════════════
FECHAMENTO {{mes_anterior}}
═══════════════════════════════════════════════════════════════════

{{wbr_fechamento_resumo}}

═══════════════════════════════════════════════════════════════════
SITUACAO MTD {{mes_atual}}
═══════════════════════════════════════════════════════════════════

{{wbr_atual_resumo}}

═══════════════════════════════════════════════════════════════════
SAIDA OBRIGATORIA (JSON estrito conforme schema):
═══════════════════════════════════════════════════════════════════

{
  "foco_do_mes": "...",
  "diretrizes": [
    {
      "titulo": "...",
      "acao": "...",
      "responsavel": "...",
      "metrica_sucesso": "..."
    }
  ],
  "riscos_monitorar": ["...", "..."]
}

Responda APENAS com o JSON. Sem texto antes ou depois. Sem comentarios.
Sem code fences (```).
```

## Validacao do output

Antes de injetar no slide, agente DEVE validar:

1. JSON parsed sem erro
2. `foco_do_mes` presente, string, len <= 140
3. `diretrizes` array com 3-5 itens
4. Cada diretriz tem todas as 4 chaves (`titulo`, `acao`, `responsavel`, `metrica_sucesso`)
5. `responsavel` nao contem nomes proprios (heuristica: nao tem palavra capitalizada
   alem da primeira; ou checar contra lista de assessores/especialistas do Card)
6. `riscos_monitorar` array com 2-3 strings

Se validacao falha:
- Logar resposta bruta + erro em `llm-diretrizes-{vertical}.log.json`
- Renderizar slide com placeholder `Diretrizes nao geradas — preencher manualmente
  via Card.apresentacao.diretrizes_override`
- Continuar geracao do deck (nao abortar)

## Override manual (Card)

Caso o gestor queira escrever diretrizes manualmente (sem LLM), declarar em
`Card.apresentacao.diretrizes_override`:

```yaml
apresentacao:
  diretrizes_override:
    foco_do_mes: "..."
    diretrizes:
      - titulo: "..."
        acao: "..."
        responsavel: "..."
        metrica_sucesso: "..."
    riscos_monitorar: ["...", "..."]
```

Quando esse bloco existir e estiver completo, o agente PULA a chamada LLM e usa
o override diretamente. Util para iteracoes finas pos-ritual.

## Log de auditoria

Cada chamada LLM gera `{cycle_folder}/dados/llm-diretrizes-{vertical}.log.json`:

```json
{
  "timestamp": "2026-05-07T12:34:56",
  "prompt_template_version": "1.0",
  "prompt_inputs": {
    "vertical": "Seguros",
    "mes_anterior": "Abril 2026",
    "mes_atual": "Maio 2026",
    "wbr_fechamento_resumo": "...",
    "wbr_atual_resumo": "..."
  },
  "prompt_full": "<prompt completo apos substituicao>",
  "llm_response_raw": "<resposta crua da LLM>",
  "llm_response_parsed": { ... },  // null se parse falhou
  "validation_errors": [],
  "used_in_deck": true
}
```

Permite reproduzir e auditar diretrizes futuras.
