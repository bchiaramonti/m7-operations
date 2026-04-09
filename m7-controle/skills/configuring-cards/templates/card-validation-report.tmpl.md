# Relatorio de Validacao — {card_id}

> Gerado automaticamente por m7-controle (E1 — configuring-cards, Modo 2)
> Data: {data}

## Resumo

| Metrica | Valor |
|---------|-------|
| Card | `{card_id}` ({codigo}) |
| Vertical | {vertical_crm} ({vertical_code}) |
| Nivel | {nivel} |
| Status atual | {status} |
| Version | {version} |
| Total de regras | 12 |
| OK | {count_ok} |
| ATENCAO | {count_atencao} |
| CRITICO | {count_critico} |
| **Resultado** | {resultado} |

<!-- resultado: "APROVADO — pode ser promovido a active" | "REPROVADO — X issues criticos encontrados" -->

---

## Detalhamento por Regra

| # | Regra | Status | Detalhe |
|---|-------|--------|---------|
| 1 | ID em snake_case e corresponde ao arquivo | {status} | {detalhe} |
| 2 | Todos indicator_id existem na Biblioteca | {status} | {detalhe} |
| 3 | Nenhum indicator com status a_mapear em Card active | {status} | {detalhe} |
| 4 | kpis_juntos + kpis_separados cobrem todos kpi_principal | {status} | {detalhe} |
| 5 | sequencia_analise com min 3 passos | {status} | {detalhe} |
| 6 | quebras_obrigatorias existem nas queries | {status} | {detalhe} |
| 7 | Correlacoes bidirecionais | {status} | {detalhe} |
| 8 | conteudo_obrigatorio referencia KPIs presentes | {status} | {detalhe} |
| 9 | codigo em UPPERCASE derivavel do id | {status} | {detalhe} |
| 10 | vertical_code valido (INV/CRE/UNI/SEG) | {status} | {detalhe} |
| 11 | nivel valido (N1/N2/N3/N4) | {status} | {detalhe} |
| 12 | subnivel consistente entre id e codigo | {status} | {detalhe} |

---

## Issues Criticos

<!-- Listar apenas se count_critico > 0. Para cada issue, incluir a regra violada, o valor encontrado e a correcao sugerida. -->

### Regra #{numero} — {nome_regra}

- **Encontrado**: {valor_encontrado}
- **Esperado**: {valor_esperado}
- **Correcao**: {sugestao_de_correcao}

---

## Issues de Atencao

<!-- Listar apenas se count_atencao > 0. -->

### Regra #{numero} — {nome_regra}

- **Encontrado**: {valor_encontrado}
- **Recomendacao**: {sugestao}

---

## KPIs Referenciados

| indicator_id | Papel | Tipo Realizacao | Status na Biblioteca |
|--------------|-------|-----------------|---------------------|
| {indicator_id} | {papel} | {tipo_realizacao} | {status} |

---

## Arvore de Indicadores

<!-- Representacao textual da arvore, indicando profundidade e status dos influenciadores. -->

```
{kpi_principal}
├── {componente_1}
│   ├── {influenciador_1} [{tipo}] — {status}
│   └── {influenciador_2} [{tipo}] — {status}
└── {componente_2}
    └── {influenciador_3} [{tipo}] — {status}
```

---

*Fonte: {caminho_card} | ESP-PERF-002 v1.1 | m7-controle E1*
