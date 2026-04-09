# Naming Conventions — Cards de Performance

> Referencia: ESP-PERF-002 v1.1, Secao 5

## Indice

1. [Formato do ID](#formato-do-id)
2. [Formato do Codigo](#formato-do-codigo)
3. [Codigos de Vertical](#codigos-de-vertical)
4. [Niveis Hierarquicos](#niveis-hierarquicos)
5. [Subniveis](#subniveis)
6. [Exemplos Completos](#exemplos-completos)
7. [Regra de Derivacao ID ↔ Codigo](#regra-de-derivacao-id--codigo)

---

## Formato do ID

**Padrao**: `card_{vert}_{nivel}_{seq}[_{sub}]`

| Componente | Formato | Obrigatorio |
|------------|---------|-------------|
| Prefixo | `card` | Sim |
| Vertical | 3 letras minusculas | Sim |
| Nivel | n1, n2, n3, n4 | Sim |
| Sequencia | 3 digitos (001, 002...) | Sim |
| Subnivel | string livre, snake_case | Nao |

**Regras:**
- Somente snake_case (underscores, minusculas, numeros)
- Deve corresponder ao nome do arquivo (sem `.yaml`)
- Sequencia inicia em 001 por vertical+nivel

---

## Formato do Codigo

**Padrao**: `CARD-{VERT}-{NIVEL}-{SEQ}[-{SUB}]`

| Componente | Formato | Obrigatorio |
|------------|---------|-------------|
| Prefixo | `CARD` | Sim |
| Vertical | 3 letras MAIUSCULAS | Sim |
| Nivel | N1, N2, N3, N4 | Sim |
| Sequencia | 3 digitos (001, 002...) | Sim |
| Subnivel | string livre, UPPERCASE | Nao |

**Regras:**
- Somente UPPERCASE com hifens
- Derivavel do ID (substituir `_` por `-`, uppercase)

---

## Codigos de Vertical

| Vertical CRM | Codigo (ID) | Codigo (Normativo) |
|--------------|-------------|-------------------|
| Investimentos | inv | INV |
| Credito | cre | CRE |
| Universo | uni | UNI |
| Seguros & Consorcios | seg | SEG |

---

## Niveis Hierarquicos

| Nivel | Codigo | Escopo | Tipico |
|-------|--------|--------|--------|
| N1 | n1/N1 | Escritorio (visao geral) | Diretoria, Head de Vertical |
| N2 | n2/N2 | Equipe | Gerente de Equipe |
| N3 | n3/N3 | Squad | Lider de Squad |
| N4 | n4/N4 | Assessor (individual) | Assessor de Investimentos |

---

## Subniveis

Subniveis sao opcionais e representam segmentacoes dentro de um nivel:

| Subnivel | Uso tipico | Exemplo |
|----------|-----------|---------|
| b2b | Segmento B2B | card_inv_n2_001_b2b |
| b2c | Segmento B2C | card_cre_n2_001_b2c |
| squad01 | Squad especifico | card_uni_n3_001_squad01 |

---

## Exemplos Completos

| Cenario | ID | Codigo | Arquivo | Caminho |
|---------|----|--------|---------|---------|
| Investimentos N1, primeiro Card | card_inv_n1_001 | CARD-INV-N1-001 | card_inv_n1_001.yaml | cards/INV/card_inv_n1_001.yaml |
| Investimentos N2, segmento B2B | card_inv_n2_001_b2b | CARD-INV-N2-001-B2B | card_inv_n2_001_b2b.yaml | cards/INV/card_inv_n2_001_b2b.yaml |
| Credito N1, segundo Card | card_cre_n1_002 | CARD-CRE-N1-002 | card_cre_n1_002.yaml | cards/CRE/card_cre_n1_002.yaml |
| Seguros N4, assessor | card_seg_n4_001 | CARD-SEG-N4-001 | card_seg_n4_001.yaml | cards/SEG/card_seg_n4_001.yaml |

---

## Regra de Derivacao ID ↔ Codigo

Para converter ID em codigo:
1. Converter para UPPERCASE
2. Substituir `_` por `-`

```
card_inv_n1_001     → CARD-INV-N1-001
card_inv_n2_001_b2b → CARD-INV-N2-001-B2B
```

Para converter codigo em ID:
1. Converter para lowercase
2. Substituir `-` por `_`

```
CARD-INV-N1-001     → card_inv_n1_001
CARD-INV-N2-001-B2B → card_inv_n2_001_b2b
```

A validacao (Regra #9) verifica que esta derivacao e consistente.
