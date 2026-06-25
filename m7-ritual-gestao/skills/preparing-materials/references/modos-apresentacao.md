# Modos de Apresentacao do Ritual (atual / combinado / fechamento)

> Referencia tecnica do `build_deck.py` — resolucao de `effective_modo` em `_resolve_effective_modo()` e dispatch via `MODO_PHASES`. Documentado em 2026-05-12 (PEND-1 do `pj2-slide-requirements.md`).

A skill `preparing-materials` suporta 3 modos de apresentacao que determinam quais slides aparecem no deck. Cada modo e tunado para um contexto de ritual diferente.

---

## 1. Comparativo dos 3 modos

| Modo | Dashboard mes atual | Fechamento mes passado | Sub-capas | Quando usar |
|---|---|---|---|---|
| **`atual`** | ✅ SIM | ❌ NAO | ❌ NAO | Ritual semanal regular (N3) — meio do mes. So mostra MTD. |
| **`fechamento`** | ❌ NAO | ✅ SIM | ❌ NAO | Ritual de fechamento puro — revisar mes anterior. Sem MTD. |
| **`combinado`** | ✅ SIM | ✅ SIM | ✅ SIM | 1o ritual do mes (N3) OU rituais N2 PJ2 (sempre). Cobre fechamento + MTD. |

Mapeamento em codigo (`build_deck.py:6716-6720` MODO_PHASES):

```python
MODO_PHASES = {
    "atual":      {"dashboard": True,  "fechamento": False, "sub_capas": False},
    "fechamento": {"dashboard": False, "fechamento": True,  "sub_capas": False},
    "combinado":  {"dashboard": True,  "fechamento": True,  "sub_capas": True},
}
```

---

## 2. Resolucao do modo efetivo

Precedencia em `_resolve_effective_modo()` ([build_deck.py:6743](../scripts/build_deck.py)):

1. **CLI `--modo`** (se != `auto`) — explicito override
2. **`Card.apresentacao.modo`** OU **`Card.metadata.modo`** (se != `auto`)
3. **`data.wbr.is_first_ritual_of_month == True`** → `combinado`
4. **Default** → `atual`

**Comportamento retro-compat:**
- Card N3 sem `modo` declarado em semana normal → `atual`
- Card N3 sem `modo` em 1o ritual do mes → `combinado` (auto-detect via WBR)
- Card PJ2 N2 declara explicitamente `apresentacao.modo: combinado` (ou e pego pelo dispatch via `is_pj2_card`)

---

## 3. Quais slides aparecem por modo

### Modo `atual` (N3 semanal regular)

```
1. Capa
2. Agenda
3. Matriz {NIVEL}              ← dashboard MTD
4. PA Status                   ← dashboard MTD
5. PA Vencendo                 ← dashboard MTD
6-N. Por especialista (3 slides x N especialistas):
   - {Esp} Dashboard
   - {Esp} Analise
   - {Esp} Pipeline
N+1. Consolidado {NIVEL}
N+2. Proximos Passos / Diretrizes
```

Total: **7 + 3 * N_especialistas slides**. Para Cons N3 (2 esp): 7+6 = 13 slides.

### Modo `fechamento` (revisao mes passado)

```
1. Capa
2. Agenda
3. Subcapa Bloco I — Fechamento
4. Fechamento N1 (visao geral mes anterior)
5-N. Por especialista (slides de fechamento):
   - {Esp} Fechamento
N+1. Analise do que deu errado (Lead indicators em vermelho)
N+2. Encerramento
```

Total: **6 + N_especialistas slides**.

### Modo `combinado` (1o ritual do mes OU PJ2 N2)

```
1. Capa
2. Agenda (+ recap N2 quando PJ2 — edit #1)
3. Subcapa Bloco I — Fechamento
4-K. Slides de fechamento (N3 single-vert) OU vert-by-vert (PJ2):
   - Fechamento Visao Geral
   - Fechamento Vertical Seguros (PJ2)
   - Fechamento Vertical Consorcios (PJ2)
   - Analise do que deu errado (edit #9)
K+1. Subcapa Bloco II — Mes ate agora
K+2... Slides MTD vert-by-vert (PJ2) OU dashboard N3:
   - Matriz Seg + Analise Canal Seg + Pipeline Seg
   - Matriz Cons + Analise Canal Cons + Pipeline Cons
   - (N3 single-vert: dashboard MTD por especialista)
Final. Conclusao com velocimetros (PJ2 — edit #21) OU Consolidado+Diretrizes (N3)
```

PJ2 N2 combinado: **17 slides** (Capa + Agenda + Sub-capa I + Fech VisaoGeral + Fech Seg + Fech Cons + AnaliseProblemas + Sub-capa II + Matriz Seg + AnaliseCanal Seg + Pipeline Seg + Matriz Cons + NPS (one-off) + AnaliseCanal Cons + Pipeline Cons + Conclusao + encerramento).

N3 single-vert combinado: variavel, depende de N_especialistas.

---

## 4. Nuances PJ2 vs N3 no modo `combinado`

| Aspecto | N3 single-vert | PJ2 N2 multi-vertical |
|---|---|---|
| **Eixo de decomposicao** | Especialista (Douglas/Tereza, Claudia/Tarcisio, etc) | Canal commercial (Investimentos/Credito/Outros M7) |
| **Slide "Por especialista"** | Sim — 3 slides por especialista (Dashboard/Analise/Pipeline) | NAO — substituido por slides por vertical (Matriz/AnaliseCanal/Pipeline) |
| **Pareto 5-bucket** | Por especialista | Por canal (Inv/Cred/Esp/Coord/Outros) |
| **Fech Visao Geral** | 1 slide com cards do mes | 1 slide com **divisor Seg \| Cons** (edit #2) + 12 cards (6 por vertical) |
| **Conclusao** | Diretrizes para o mes seguinte | **3 velocimetros** (Seg Receita + Cons Receita + Total PJ2 — edit #21) |
| **Recap N2** | NAO aplicavel | 1 slide dedicado com pontos da ata anterior (edit #1) |
| **Template HTML** | `ritual.tmpl.html` (variant=default) | `ritual-pj2.tmpl.html` (variant=pj2) |
| **Builder** | `build_deck.py` (fluxo padrao) | `build_deck_pj2.py` (sidecar via subprocess dispatch) |
| **Dispatch** | Auto — quando `is_pj2_card(card) == False` | Auto — quando `is_pj2_card(card) == True` |

---

## 5. Configuracao no Card

```yaml
# Card N3 single-vert (semana normal)
apresentacao:
  modo: atual   # ou omitir — vira atual por default
  label_responsavel: especialista

# Card N3 single-vert (1o ritual do mes — auto-combinado)
apresentacao:
  modo: auto                              # default
  # WBR vai ter is_first_ritual_of_month=true → effective_modo=combinado

# Card PJ2 N2 (sempre combinado)
metadata:
  vertical_code: PJ2                      # gatilha is_pj2_card
  verticais: [consorcios, seguros]         # gatilha is_pj2_card via len >= 2
  label_responsavel: canal                 # gatilha is_pj2_card
  verticais_display: "Seguros e Consórcios"  # ordem visual (edit #3)
apresentacao:
  modo: combinado                          # explicito (defensive)
  proj_periodos_por_vertical:
    cons: ["M0", "M+1"]                    # Cons aceita M+1 (edit #31)
    seg:  ["M0"]                            # Seg sem M+1 (metodo nao calibrado)
```

---

## 6. Detalhamento dos slides PJ2 (edits #1-31 do contrato)

Ver tabela completa de cobertura em `RESUME-FROM-HERE.md` (Sessao 4 completa). Cada um dos 31 edits do Batches A-I do `pj2-slide-requirements.md` esta coberto pelo sidecar V13 portado em 2026-05-12 (`build_deck_pj2.py`).

Cross-references:
- [pj2-slide-requirements.md](pj2-slide-requirements.md) — contrato vivo dos 31 edits
- [slide-structure.md](slide-structure.md) — estrutura de slides N3 legacy
- [briefing-structure.md](briefing-structure.md) — briefing v2.0 (estrutura aberta) vs v1.0 (prescritiva)
- [RESUME-FROM-HERE.md](RESUME-FROM-HERE.md) — estado pos-Sessao 4 maratona 2026-05-12
