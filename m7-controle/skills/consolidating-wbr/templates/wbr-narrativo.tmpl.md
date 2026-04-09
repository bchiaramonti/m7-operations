# {vertical} — {periodo_display} | Checkpoint: {checkpoint_label}

<!-- MANCHETE: Uma unica frase-veredito que captura a historia do periodo MTD.
     Contem o destaque positivo mais relevante E o risco/desvio mais critico.
     Numeros especificos obrigatorios. Maximo 2 frases. -->

{manchete}

---

## Panorama

<!-- 3-5 frases que situam o leitor. Responde: "como estamos no geral?"
     - Semaforo em prosa: "X verdes, Y amarelos, Z vermelhos"
     - Projecao consolidada com cenario base
     - Contexto APENAS se impacta numeros (feriado, evento, mudanca de equipe)
     - Nunca mais de 5 frases -->

{panorama}

---

## O que Preocupa

<!-- Um bloco por indicador Vermelho (obrigatorio) e Amarelo relevante.
     Cada bloco segue: O que aconteceu → Por que → O que significa.

     Regras:
     - Numeros SEMPRE comparativos (vs meta, vs periodo anterior)
     - Causa-raiz narrada com nivel de confianca entre parenteses
     - Concentracao explicita: "78% do gap em 3 assessores"
     - Consequencia projetada: o que acontece se nada mudar
     - Amarelos: analise breve, foco em tendencia
     - Verdes que eram Vermelhos: mencao breve como recuperacao -->

### {indicador_vermelho_1} — {realizado} (meta: {meta})

{narrativa_desvio_1}

<!-- Repetir ### para cada Vermelho. Depois, Amarelos relevantes. -->

---

## O que Estamos Fazendo

<!-- 1 paragrafo sintetico sobre contramedidas. NAO repetir lista completa.
     Foco em:
     - Acoes criticas/atrasadas (responsavel + prazo)
     - Eficacia das concluidas no periodo
     - Volume/receita em risco
     - Conexao explicita com os desvios da secao anterior -->

{narrativa_acoes}

---

## Para Onde Estamos Indo

<!-- 1-2 paragrafos traduzindo projecoes em linguagem de decisao.
     - "Atingiremos/nao atingiremos" (nao "projecao indica 87%")
     - Gap traduzido em termos operacionais ("aceleracao de 2,3x no ritmo")
     - Conectar projecao com acoes necessarias
     - Cenarios detalhados apenas para indicadores em risco -->

{narrativa_projecoes}

---

## O que Precisa Acontecer

<!-- Chamadas para acao diretas. Cada item e uma decisao ou tarefa.
     Formato: acao especifica + owner + deadline
     Escalonamentos como decisao binaria: "X ou Y — decidir ate [data]"
     Ajustes de meta apenas se causa estrutural + projecao Improvavel -->

**Decisoes necessarias esta semana:**

1. **{acao_1}** — Owner: {responsavel} — Ate: {prazo}
2. **{acao_2}** — Owner: {responsavel} — Ate: {prazo}

<!-- Se ha escalonamentos para N1: -->
**Escalonamentos:**
- **{tema}**: {decisao_binaria} — Decisao necessaria ate: {prazo}

<!-- Se ha ajustes de meta sugeridos: -->
**Ajustes de meta:**
- {indicador}: {justificativa_ou_rejeicao}

<!-- Se nenhuma decisao pendente: -->
<!-- Nenhuma decisao adicional necessaria. Manter execucao das acoes em curso. -->

---

## Destaques Positivos

<!-- Minimo 2 destaques (mesmo em semanas dificeis, algo funcionou).
     - Reconhecer pessoas por nome quando possivel
     - Conectar destaque a acao/causa quando identificavel
     - Indicadores que recuperaram de Vermelho para Verde DEVEM aparecer -->

- **{destaque_1}**: {descricao_com_numeros}
- **{destaque_2}**: {descricao_com_numeros}
- **{destaque_3}**: {descricao_com_numeros}

---

> Fonte: ClickHouse + Bitrix24 | Vertical: {vertical} | Periodo: {data_inicio} a {data_fim}
> Qualidade dos dados: {status_qualidade}
> WBR estruturado completo: wbr-{vertical}-{data}.md

*Gerado automaticamente pela skill consolidating-wbr (G2.2-E6) | m7-controle*
