# Checklist do Comissionamento — {YYYYMM}

Competencia {MES_NOME}/{YYYY}.

### Convencao de emojis

| Emoji | Uso | Onde |
|-------|-----|------|
| ✅ | Concluido | Itens (`- ✅`) e secoes 100% concluidas (`### ✅`) |
| ⬜ | Pendente | Itens (`- ⬜`) e secoes 100% pendentes (`### ⬜`) |
| 🟡 | Em andamento | Secoes parcialmente concluidas (`## 🟡`, `### 🟡`) |
| ⚠️ | Desvio | Registro de desvios ou excecoes (`- ⚠️ **Desvio**: ...`) |
| ⏭️ | Nao se aplica | Itens ou secoes que nao se aplicam nesta competencia |

Ao avancar na execucao, atualizar os emojis das secoes (##, ###, ####) conforme o progresso dos itens filhos.

---

## Informacoes da Competencia

| Campo | Valor |
|-------|-------|
| **Competencia** | {YYYYMM} |
| **Mes/Ano** | {MES_NOME}/{YYYY} |
| **Responsavel** | Bruno Chiaramonti |
| **Data Inicio** | ___/___/______ |
| **Data Conclusao** | ___/___/______ |

---

## ⬜ Fase 0 — Preparacao da Competencia

**Output**: Estrutura de diretorios e arquivos de controle criados

- [ ] Criar diretorios: `raw/`, `fase1_comissionamento/`, `fase2_parametrizacao/`, `fase3_pagamento/`, `fase4_dados/`
- [ ] Criar `CHANGELOG_{YYYYMM}.md` para registro cronologico
- [ ] Criar `CHECKLIST_{YYYYMM}.md` para acompanhamento
- [ ] Criar `notes_{YYYYMM}.md` para registro de resumo, desvios e licoes aprendidas
- [ ] Copiar 8 arquivos de parametrizacao da competencia anterior

---

## ⬜ Fase 1 — Recebimento e Conversao de Arquivos

**Metodo**: Conversao Excel→CSV (UTF-8, separador virgula)
**Output**: `fase1_comissionamento/*.csv`

### ⬜ 1.0. Revisao de ajustes da competencia anterior

- [ ] Revisar `AJUSTES_{YYYYMM_ANTERIOR}.md` — identificar ajustes pendentes (🟡), transbordos (⏭️) e itens nao resolvidos
- [ ] Registrar transbordos em `AJUSTES_{YYYYMM}.md` com referencia a origem (ex: `AJUSTES_{YYYYMM_ANTERIOR}.md #N`)

### ⬜ 1.1. Arquivos XP (conversao direta)

- [ ] `investimentos_{YYYYMM}.csv` — de `8426_M7Investim_{YYYYMM}.xlsx`
- [ ] `xp_us_{YYYYMM}.csv` — de `8426_M7Investim_{YYYYMM}_XP US.xlsx`
- [ ] `mercado_internacional_{YYYYMM}.csv` — de `8426_M7Investim_{YYYYMM}_Mercado Internacional.xlsx`
- [ ] `cocorretagem_terceiras_{YYYYMM}.csv` — de `8426_M7Investim_{YYYYMM}_Co-corretagem Terceiras.xlsx`
- [ ] `xp_cs_{YYYYMM}.csv` — de `8426_M7Investim_{YYYYMM}_XPCS.xlsx`
- [ ] `cocorretagem_xpvp_{YYYYMM}.csv` — de `8426_M7Investim_{YYYYMM}_Co-corretagem XPVP.xlsx`
- [ ] `credito_{YYYYMM}.csv` — de `8426_M7Investim_{YYYYMM}_Credito.xlsx`
- [ ] `cambio_{YYYYMM}.csv` — de `8426_M7Investim_{YYYYMM}_Cambio.xlsx`

### ⬜ 1.2. Arquivos com tratamento especial

- [ ] `avenue_{YYYYMM}.csv` — consolidar e converter de `avenue_{YYYYMM}.xlsx`
- [ ] `seguros_{YYYYMM}.csv` — de `GERAL - PRODUÇÃO M7 - NOVO..xlsx` (aba Faturamento): filtrar competencia, remover Previdencia/Prestamista
- [ ] `consorcio_{YYYYMM}.csv` — consolidar 4 CSVs: BANCORBRAS, BRADESCO, CNP, PORTO (`XP_INV_CONSORCIO_{ADMIN}_{YYYYMM}.csv`)
- [ ] `financiamento_imobiliario_{YYYYMM}.csv` — de `8426_M7Investim_{YYYYMM}_Financiamento.xlsx` (se houver)

> **Nota**: Seguros — manter apenas: Vida, Auto, Viagem, Residencial, Empresarial, Garantia, Bonus, RC. Consorcio — adicionar coluna `Administradora` baseada no nome do arquivo.

---

## ⬜ Fase 2 — Processamento e Correcoes por Arquivo

**Metodo**: Correcoes e padronizacoes nos CSVs gerados na Fase 1
**Output**: Arquivos atualizados em `fase1_comissionamento/`

### ⬜ 2.1. investimentos

- [ ] Preencher assessores ausentes (regras padrao: Fundos Exclusivos JOLUGAJU/8 FIM → A74905, Indicacao PJ XPICCTVM → A67281)
- [ ] Padronizar campanhas FULL

### ⬜ 2.2. seguros

- [ ] Transformar para formato SplitC
- [ ] Corrigir assessores (matching via apolices)
- [ ] Remover linhas invalidas

### ⬜ 2.3. xp_cs

- [ ] Preencher Nivel 3 com valor da Categoria

### ⬜ 2.4. cocorretagem_xpvp

- [ ] Preencher Nivel 3 com valor da Categoria

### ⬜ 2.5. cambio

- [ ] Corrigir campos ausentes
- [ ] Padronizar campanhas FULL

---

## ⬜ Fase 3 — Ajustes Manuais

**Output**: `fase1_comissionamento/ajustes_manuais_{YYYYMM}.csv`, `fase1_comissionamento/descontos_{YYYYMM}.csv`

### ⬜ 3.1. ajustes_manuais

- [ ] Criar `ajustes_manuais_{YYYYMM}.csv` — campanhas FULL nao recebidas, estornos

### ⬜ 3.2. descontos

- [ ] Criar `descontos_{YYYYMM}.csv` — plano de saude, outros descontos

---

## ⬜ Fase 4 — Atualizacao de Parametrizacoes

**Output**: `fase2_parametrizacao/*.csv` (8 arquivos)

### ⬜ 4.1. cotacao_dolar

- [ ] Definir cotacao USD/BRL do periodo em `cotacao_dolar_{YYYYMM}.csv` (usado por mercado_internacional + xp_us)

### ⬜ 4.2. estrutura

- [ ] Adicionar novos assessores e aliases em `estrutura_{YYYYMM}.csv`

### ⬜ 4.3. apolices_seguros

- [ ] Cadastrar apolices novas e definir corretor responsavel em `apolices_seguros_{YYYYMM}.csv`

### ⬜ 4.4. contratos_consorcio

- [ ] Cadastrar contratos novos de consorcio em `contratos_consorcio_{YYYYMM}.csv`

### ⬜ 4.5. comissao_base

- [ ] Cadastrar chaves de comissao ausentes em `comissao_base_{YYYYMM}.csv`

### ⬜ 4.6. contas_offshore

- [ ] Cadastrar contas internacionais novas em `contas_offshore_{YYYYMM}.csv` (se houver)

### ⬜ 4.7. rebate_originacao

- [ ] Atualizar rebates e originacao em `rebate_originacao_{YYYYMM}.csv` (se houver)

### ⬜ 4.8. fixo_piso

- [ ] Atualizar valores fixos e pisos em `fixo_piso_{YYYYMM}.csv` (se houver)

---

## ⬜ Fase 5 — Carga no SplitC

**Ferramenta**: https://app.splitc.com.br
**Output**: Plano de calculo criado e validado na plataforma

- [ ] Criar plano de calculo na plataforma SplitC
- [ ] Upload de 8 arquivos de `fase2_parametrizacao/`
- [ ] Upload de 12 arquivos de `fase1_comissionamento/` + ajustes
- [ ] Validar assessores — corrigir comissoes sem assessor ate zerar pendencias
- [ ] Validar chaves — corrigir comissoes sem percentual ate zerar pendencias
- [ ] Publicar visualizacao do periodo para assessores (SplitC → Liberar)

---

## ⬜ Fase 6 — Envio de Comissoes XP (Financeiro e Wealth)

**Output**: Comissoes recebidas da XP enviadas ao financeiro e ao Wealth

- [ ] Elaborar demonstrativo em Excel — `fase3_pagamento/demonstrativo_xp/demonstrativo_comissoes_xp_{YYYYMM}.xlsx`
- [ ] Elaborar e-mail HTML — `fase3_pagamento/demonstrativo_xp/email_demonstrativo_xp_{YYYYMM}.html`
- [ ] Enviar e-mail com o relatorio detalhado ao financeiro e ao Wealth

---

## ⬜ Fase 7 — Relatorio Compromissada (Parabellum)

**Output**: Relatorio de comissoes filtrado por Nivel 1 = COMP (Compromissada) enviado ao fornecedor Parabellum

- [ ] Gerar relatorio filtrado — `fase3_pagamento/compromissada/relatorio_compromissada_{YYYYMM}.xlsx`
- [ ] Enviar relatorio ao fornecedor Parabellum
- [ ] Elaborar e-mail HTML — `fase3_pagamento/compromissada/email_compromissada_{YYYYMM}.html`

---

## ⬜ Fase 8a — Ajustes Pre-Pagamento

**Output**: `AJUSTES_{YYYYMM}.md` atualizado com pleitos resolvidos

Pleitos que impactam o PGTO. Resolver antes da Fase 9.

- [ ] Registrar ajustes recebidos — documentar solicitacoes em `AJUSTES_{YYYYMM}.md`
- [ ] Avaliar pleitos — classificar como procedente, improcedente ou pendente de informacao
- [ ] Recarregar no SplitC — atualizar arquivos corrigidos na plataforma (se houver ajustes procedentes)
- [ ] Recalcular comissoes — validar impacto dos ajustes nos valores

> **Nota:** Somente pleitos recebidos e resolvidos antes do PGTO entram nesta fase. Pleitos tardios vao para 8b.

---

## ⬜ Fase 9 — Pagamento

**Output**: `fase3_pagamento/pgto/PGTO-{YYYY}-{MM}-v1.csv`, `fase3_pagamento/pgto/email_financeiro_{YYYYMM}.html`

Incorpora ajustes da Fase 8a. **HARD DEADLINE — dia 13 do mes seguinte.**

- [ ] Gerar PGTO — exportar e formatar arquivo de pagamento do SplitC em `fase3_pagamento/pgto/`
- [ ] Aplicar ajustes procedentes da Fase 8a
- [ ] Criar e-mail HTML — `fase3_pagamento/pgto/email_financeiro_{YYYYMM}.html`
- [ ] Enviar ao financeiro (financeiro@multisete.com, CC manuella/gonzalo)

---

## ⬜ Fase 8b — Ajustes Pos-Pagamento

**Output**: `AJUSTES_{YYYYMM}.md`, `fase3_pagamento/pgto/PGTO-{YYYY}-{MM}-complementar.csv`

Pleitos tardios, erratas, PGTO complementar e transbordos para proxima competencia.

- [ ] Registrar ajustes tardios — documentar em `AJUSTES_{YYYYMM}.md`
- [ ] Recarregar no SplitC — atualizar arquivos corrigidos (se houver)
- [ ] Recalcular comissoes — processar novo calculo e identificar diferencas
- [ ] Gerar PGTO complementar — `fase3_pagamento/pgto/PGTO-{YYYY}-{MM}-complementar.csv`
- [ ] Enviar errata/complementar ao financeiro
- [ ] Registrar transbordos — marcar ajustes nao resolvidos como ⏭️ com nota para proxima competencia

> **Nota:** Tarefas 8b.2 a 8b.5 serao executadas somente quando houver solicitacoes procedentes apos o PGTO.

---

## ⬜ Fase 10 — Carga no Banco de Dados e Arquivo de Custos

**Output**: Comissoes carregadas no banco M7Medallion + arquivo de custos para o financeiro

### ⬜ 10.1. Carga da comissao no banco de dados

- [ ] Carregar dados de comissao no banco M7Medallion (SQL Server `172.17.0.10`) — via skill `processing-split-c-receitas`
- [ ] Validar integridade da carga (contagem de registros, totais)

### ⬜ 10.2. Emissao do arquivo de custos para o financeiro

- [ ] Gerar arquivo consolidado de custos por assessor — `fase4_dados/resumo_financeiro_{YYYY}-{MM}.xlsx` via skill `generating-resumo-financeiro`
- [ ] Enviar arquivo de custos ao financeiro (financeiro@multisete.com, CC manuella/gonzalo)

---

## Resumo Final

| Metrica | Valor |
|---------|-------|
| **Total de registros processados** | _____ |
| **Total de comissao assessor (R$)** | _____ |
| **Total de comissao escritorio (R$)** | _____ |
| **Assessores no PGTO** | _____ |
| **Assessores no resumo financeiro** | _____ |
| **Arquivos comissionamento carregados** | __/12 + ajustes |
| **Parametrizacoes carregadas** | __/8 |
| **Carga banco M7Medallion** | _____ registros |
| **Resumo financeiro** | `fase4_dados/resumo_financeiro_{YYYY}-{MM}.xlsx` |

---

**Versao**: 6.0
**Ultima atualizacao**: Abril/2026
**Baseado em**: Processo real executado desde 202501
