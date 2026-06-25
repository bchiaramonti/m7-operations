# Migracao v2.0 — Cards de Performance abertos + SSoT

Referencia rapida para o agente `material-generator` aplicar a logica de filtro v2.0 (estrutura aberta) e os 3 gatekeepers de single source of truth (SSoT) que governam a coerencia briefing↔slide.

## Sumário

1. [Detectar versao do Card](#1-detectar-versao-do-card)
2. [Estrutura aberta v2.0 — principio nao-negociavel](#2-estrutura-aberta-v20--principio-nao-negociavel)
3. [Logica de filtro v2.0](#3-logica-de-filtro-v20)
4. [SSoT — os 3 gatekeepers](#4-ssot--os-3-gatekeepers)
5. [Itens secundarios do checklist (1-6, 8-9, 11, 13-14)](#5-itens-secundarios-do-checklist-1-6-8-9-11-13-14)
6. [Spot-check de SSoT (3 valores)](#6-spot-check-de-ssot-3-valores)
7. [Coerencia visual contra `examples/`](#7-coerencia-visual-contra-examples)
8. [Anti-patterns a evitar](#8-anti-patterns-a-evitar)
9. [Roadmap de retrocompatibilidade](#9-roadmap-de-retrocompatibilidade)
10. [Referencias cruzadas](#10-referencias-cruzadas)

---

## 1. Detectar versao do Card

Antes de gerar qualquer material, ler `briefing_customization.versao` no Card YAML:

| Versao | Comportamento |
|--------|---------------|
| `"2.0"` ou superior | Fluxo aberto v2.0 — aplicar filtros por `sinal_generico_no_wbr` e `contexto_tipico` (este documento). Gerar briefing MD + HTML A4 |
| `"1.0"` ou ausente | Fluxo prescritivo v1.0 (legado) — apenas briefing MD, sem filtros. Avisar usuario: `Card sem briefing_customization.versao 2.0 — usando fluxo legado. Considere atualizar o Card via /m7-metas:creating-cards` |

A migracao para v2.0 esta vigente em SEG (WL+RE), CON, INV desde 2026-04-27. Cards de outras verticais migrados gradualmente.

### Verticais multi-subnivel — deteccao por card individual

Em verticais split (ex: SEG WL/RE), a skill `preparing-materials` Fase 1.0 ja seleciona o **card unico** do subnivel solicitado antes de invocar o agent. Portanto a deteccao de versao acontece sobre **1 card**, nao sobre os N cards da vertical simultaneamente.

Implicacoes:

- Cards distintos do mesmo vertical podem estar em versoes diferentes (ex: WL em `"2.0"` e RE em `"1.0"`). Cada ritual e processado independentemente, com sua propria deteccao.
- Em modo split, a invocacao da skill **sempre** carrega o argumento `subnivel`. Sem ele, a skill aborta antes de chegar nesta deteccao.
- Filtros v2.0 (Secoes 3-7 deste doc) sao aplicados ao card individual selecionado — nunca cruzando familias entre cards diferentes.

Cuidados:

- Anti-pattern: detectar versao no card WL e aplicar filtros nos dados do card RE — sempre acoplar deteccao + dados ao mesmo card.
- Nota de governanca: ao promover um card de vertical multi-subnivel para v2.0, alinhar a versao dos demais cards da mesma vertical na mesma janela para evitar dissonancia visual entre rituais (deck WL com filtros v2.0 vs deck RE legado).

---

## 2. Estrutura aberta v2.0 — principio nao-negociavel

Texto canonico de `uso_pretendido` em todos os Cards v2.0:

> Estrutura aberta. Selecionar dos eixos abaixo APENAS os que o WBR do ciclo corrente sustenta. Nada aqui deve ser forcado quando os dados nao apontarem na direcao. Quando o ciclo trouxer um assunto NAO previsto aqui, esse assunto entra livremente no briefing — estes eixos sao adicionais, nao restritivos.

**Implicacao operacional:**

1. NAO copie armadilhas/decisoes do Card cegamente. Filtre antes de incluir.
2. PODE incluir armadilha/decisao que nao esta no Card, se o WBR daquele ciclo trouxer assunto novo.
3. O numero de armadilhas no briefing varia (3-4 tipico) conforme o ciclo. Nao ha quantidade fixa.

---

## 3. Logica de filtro v2.0

### Armadilhas — filtro por `sinal_generico_no_wbr`

```pseudocode
selecionadas = []
para cada item em Card.briefing_customization.familias_de_armadilhas:
    sinal = item.sinal_generico_no_wbr
    se sinal aparece como padrao no WBR atual (numero, percentual, indicador citado):
        selecionadas.append(item)
limitar a 3-4 mais provaveis no ciclo (priorizar maior impacto em volume/receita)

# Se WBR trouxer assunto NAO previsto no Card, criar armadilha ad-hoc:
se WBR cita padrao recorrente nao-coberto pelas familias:
    selecionadas.append(armadilha_ad_hoc(padrao_observado))
```

**Criterio de "sinal presente no WBR":**
- Numero exato (ex: "62 deals estagnados")
- Percentual (ex: "95% classificado como estagnado")
- Indicador citado por nome (ex: "Receita 148,3% Verde")
- Padrao narrativo (ex: "quarto ciclo consecutivo em vermelho")

### Decisoes — filtro por `contexto_tipico`

```pseudocode
selecionadas = []
para cada item em Card.briefing_customization.familias_de_decisoes:
    contexto = item.contexto_tipico
    se contexto presente no WBR (Recomendacoes, Escalonamentos, Riscos):
        selecionadas.append(item)
limitar a 1-4 (priorizar binarias com consequencia clara de nao-decidir)

# Adicionar decisoes vindas diretamente do WBR:
para cada recomendacao em WBR.Recomendacoes:
    se recomendacao nao corresponde a familia ja selecionada:
        selecionadas.append(decisao_do_wbr(recomendacao))
```

### Provocacoes — sempre instanciadas, varia o interlocutor

`eixos_de_provocacao_a_considerar` sempre sao seed para perguntas — o que varia e o interlocutor (de `apresentacao.responsaveis`) e o numero do ciclo que sustenta a provocacao.

```pseudocode
para cada interlocutor em apresentacao.responsaveis:
    perguntas_interlocutor = []
    para cada eixo em Card.briefing_customization.eixos_de_provocacao_a_considerar:
        se eixo se aplica ao perfil/desvio do interlocutor no ciclo:
            perguntas_interlocutor.append(instanciar_pergunta(eixo, interlocutor, dados_wbr))
    limitar a 2-4 perguntas por interlocutor
```

---

## 4. SSoT — os 3 gatekeepers

A skill so e considerada completa se os 3 itens de single source of truth passarem. Falha em qualquer um BLOQUEIA a publicacao.

### Gatekeeper 1 (Item 7): Rastreabilidade armadilha → WBR

Cada armadilha do briefing tem um campo `Sinal observado` (renderizado no MD/HTML; internamente populado a partir de `sinal_generico_no_wbr` do Card). **Esse texto deve aparecer literalmente (ou com matching flexivel de numero) no WBR do ciclo.**

```python
# Pseudocodigo de validacao
for armadilha in briefing.armadilhas:
    sinal = armadilha.sinal_no_wbr
    if not (sinal in wbr_text or numero_em_sinal_aparece_no_wbr(sinal, wbr_text)):
        raise ValidationError(f"Armadilha sem sinal rastreavel no WBR: {sinal}")
```

### Gatekeeper 2 (Item 10): Coerencia decisoes briefing ↔ Slide Encerramento (último, posição `7 + 3*N`)

**Numero D de decisoes no briefing == numero D de next-cards no Slide Encerramento (último, posição `7 + 3*N`).** Mesmos titulos.

```python
# Pseudocodigo de validacao
D_briefing = count(briefing.decisoes)
D_slide10 = count(deck.slide10.cards)
if D_briefing != D_slide10:
    raise ValidationError(f"Decisoes desalinhadas: briefing tem {D_briefing}, slide tem {D_slide10}")

for d in range(D_briefing):
    if briefing.decisoes[d].titulo != deck.slide10.cards[d].titulo:
        raise ValidationError(f"Titulo de decisao {d+1} divergente entre briefing e slide")
```

### Gatekeeper 3 (Item 12): Coerencia tempo briefing ↔ Slide 2

**Total de minutos no Roteiro do briefing == total na Agenda do Slide 2.** Composição v3.0: `T = T_VISAO (8) + T_OPERACAO (10) + 15*N + T_SINTESE (4) + T_FECHAMENTO (3) = 25 + 15*N`.

```python
# Pseudocodigo de validacao
total_briefing = sum(b.duracao_min for b in briefing.roteiro.blocos)
total_slide2 = deck.slide2.tempo_total
if total_briefing != total_slide2:
    raise ValidationError(f"Tempo desalinhado: briefing {total_briefing}min, slide {total_slide2}min")

# Verificar composicao tambem
expected = 10 + 25 * N + 5  # N especialistas
if abs(total_briefing - expected) > 5:  # tolerancia de 5min
    warning(f"Total fora do padrao: {total_briefing} vs esperado {expected}")
```

---

### Gatekeeper #16 (S1-A1#8 · 2026-05-15): Cross-slide PA count

**Total do donut PA Status (slide 4) deve bater com a soma das 4 categorias de `acoes` no WBR canonical** (criticas + atrasadas + em_dia_priorizadas + concluidas_eficazes). As 3 superficies visuais (donut, owner bars do slide 4, tabela do slide 5) devem refletir o mesmo subset curado pelo analyst.

**Implementacao:** `build_deck.py:render_pa_slides` chama `_gatekeeper_check("#16", ...)` antes do return.

**Tolerancia:** zero (sao contagens inteiras). Modo `blocking=False` por enquanto — gera WARNING; promovido para `blocking=True` quando manual append (pa_manual_append) deixar de existir.

```python
expected_total = (len(acoes["criticas"]) + len(acoes["atrasadas"])
                  + len(acoes["em_dia_priorizadas"]) + len(acoes["concluidas_eficazes"]))
_gatekeeper_check("#16", "PA count consistente", total_geral == expected_total, ...)
```

---

### Gatekeeper #17 (S1-A1#8 · 2026-05-15): Cross-slide esp value consistency

**Para cada KPI (receita / volume / qty) × cada especialista, o valor exibido no slide Consolidado N3 (velocimetros + barras por esp) deve bater com o valor exibido no slide Dashboard do mesmo esp (KPI tiles do Bloco 03).**

**Implementacao:** `build_deck.py:_gatekeeper_17_consolidado_vs_dashboard(data, esp_list)` chamado em `main()` apos os renders. Compara via 2 paths:
- Consolidado: `wbr.indicadores.{kpi_id}.n2.{esp}.realizado_mtd`
- Dashboard: `_esp_kpi_value(data, esp, kind, aspect)`

**Tolerancias (brutas, nao formatadas):**
- BRL compact: R$ 500
- qty/int: 1 unidade
- pct: 0.1 ponto percentual

**Modo:** `blocking=False` (WARNING) na S1 — pode promover para `blocking=True` em S2-B6 apos schema unificado eliminar overrides legados.

```python
ok = _gatekeeper_numeric_close(consol_v, dash_v, tolerance=500)
_gatekeeper_check("#17", f"esp value · {kind} · {esp}", ok, ...)
```

---

## 5. Itens secundarios do checklist (1-6, 8-9, 11, 13-14)

Ver `references/briefing-structure.md` Secao 10 para tabela completa. Os 11 itens nao-SSoT:

| # | Item | Como verificar |
|---|------|----------------|
| 1 | Cabecalho com Condutor + Participantes + PERIODO_DADOS + TIMESTAMP_WBR | Grep no MD |
| 2 | Veredicto tem exatamente 3 frases em paragrafo unico | Contar pontos finais; sem listas/tabelas |
| 3 | Frase 3 do Veredicto aponta para uma decisao concreta da Secao 4 | Verificar consistencia |
| 4 | Cada interlocutor da Secao 2 tem nome real | Cross-check Card |
| 5 | Cada pergunta tem aspas + Nao aceite + Redirecionamento (3 elementos) | Estrutura por pergunta |
| 6 | Numero de armadilhas e 3-4 | `grep -c '^\\*\\*"'` na secao 3 |
| 8 | Decisoes em formato binario (X OU Y), nao "vamos discutir" | Grep "OU" em cada decisao |
| 9 | Cada decisao tem Owner + Prazo (YYYY-MM-DD) + Consequencia | Estrutura por decisao |
| 11 | Roteiro tem N+2 blocos | Count blocos |
| 13 | Total entre 50-90 min | Numero |
| 14 | Briefing tem 300-1200 palavras (gold standard S18 = 1144) | `wc -w` |

Falha em itens nao-SSoT gera warning, mas nao bloqueia publicacao.

---

## 6. Spot-check de SSoT (3 valores)

Antes de salvar, escolher 3 numeros do briefing e verificar que aparecem identicos no WBR:

```python
# Pseudocodigo
valores_briefing = extract_numeros(briefing.text)  # ex: ["86%", "R$ 110M", "62 deals", "172 dias"]
amostra = sample(valores_briefing, 3)

for valor in amostra:
    if not aparece_em(valor, wbr_text):
        raise ValidationError(f"Valor {valor} no briefing nao encontrado no WBR (single source of truth)")
```

Match flexivel admite variacoes pequenas de formatacao (`R$ 110M` vs `R$ 110,0M`).

---

## 7. Coerencia visual contra `examples/`

Apos gerar deck e briefing, comparar estruturalmente com os gold standards em `examples/`:

| Comparacao | Como |
|------------|------|
| Estrutura de slides | `examples/ritual-deck-validado.example.html` tem 14 slide-wrappers (CON N3 com 2 esp). Esperado para vertical com N esp = `5 + N*4 + 1` |
| Paleta CSS | Grep no HTML gerado por hex fora da paleta documentada em `slide-structure.md` Secao 3 |
| Estrutura do briefing MD | 5 secoes, na ordem: Veredicto / O Que Provocar / Armadilhas / Decisoes / Roteiro |
| Estrutura do briefing HTML A4 | `<div class="section-title">` x 5 (uma por secao); `.question-block` por pergunta; `.trap-block` por armadilha; `.decision-block` por decisao; `.roteiro-block` por bloco |
| Tipografia | Fonte `"twkEverett", ...`; tamanhos respeitam minimos da Secao 3 do `slide-structure.md` |

Nao precisa ser identico em conteudo (cada vertical tem dados diferentes) — apenas em **estrutura visual** e **convencoes**.

---

## 8. Anti-patterns a evitar

- ❌ Copiar todas as familias do Card sem filtrar por sinal/contexto no WBR (vai inflar o briefing com armadilhas/decisoes irrelevantes)
- ❌ Gerar briefing apenas em MD quando o Card e v2.0 (skill exige MD + HTML A4)
- ❌ Ignorar gatekeepers — publicar briefing com decisao count != slide Encerramento next-cards (posição `7 + 3*N` no template editorial v3.0)
- ❌ Reusar texto de ciclos anteriores — cada briefing e ad-hoc para o ciclo
- ❌ Fallback silencioso v1.0 sem avisar usuario — sempre logar a versao detectada
- ❌ Decidir "Nao aceite" generico ("ele vai falar X") — usar fala real plausivel do interlocutor
- ❌ Calcular numeros novos no briefing — todos os numeros vem do WBR

---

## 9. Roadmap de retrocompatibilidade

A retrocompatibilidade v1.0 e temporaria. Sera removida quando:

- Todos os Cards M7 (INV N1, INV N2, INV N3 ×3, CRE, UNI, SEG N2, SEG N3, CON N2, CON N3) tiverem `briefing_customization.versao: "2.0"` ou superior
- Pelo menos 2 ciclos completos de cada vertical executados em fluxo v2.0 sem regressao
- Aprendizados v2.x consolidados em release minor (v1.9.x)

Estimativa: rollout completo em ~2 ciclos mensais (8 semanas) a partir de 2026-04-27. Rollout sequencial por vertical: CON → SEG → INV.

---

## 10. Referencias cruzadas

| Item | Caminho |
|------|---------|
| Estrutura completa do briefing | `references/briefing-structure.md` |
| Estrutura completa do deck | `references/slide-structure.md` |
| Template MD do briefing | `templates/ritual-briefing.tmpl.md` |
| Template HTML A4 do briefing | `templates/ritual-briefing.tmpl.html` |
| Template HTML do deck | `templates/ritual.tmpl.html` |
| Gold standard MD | `examples/ritual-briefing-validado.example.md` |
| Gold standard HTML A4 | `examples/ritual-briefing-validado.example.html` |
| Gold standard deck | `examples/ritual-deck-validado.example.html` |
