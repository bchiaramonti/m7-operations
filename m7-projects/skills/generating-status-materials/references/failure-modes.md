# Failure Modes

> Catálogo de modos de falha, sintomas, e como recuperar. Consulte quando a skill falhar ou emitir warning que não está claro.

## Índice

1. [Convenção](#convenção)
2. [Pré-requisitos ausentes](#pré-requisitos-ausentes)
3. [Dados inconsistentes](#dados-inconsistentes)
4. [Staleness](#staleness)
5. [Problemas de render](#problemas-de-render)
6. [Conflitos de output](#conflitos-de-output)
7. [Recovery patterns](#recovery-patterns)
8. [Debug flags](#debug-flags)

---

## Convenção

- **Fatal:** skill aborta com exit code ≠ 0 e mensagem clara. Usuário precisa agir.
- **Warning:** skill continua, emite aviso em stdout e também adiciona a `data.warnings[]` que aparece no output final.
- **Silent OK:** skill lida sem avisar (comportamento esperado que parece suspeito mas não é).

---

## Pré-requisitos ausentes

### Projeto não inicializado

**Sintoma:** `CLAUDE.md` não existe em `--project-dir`.

**Severidade:** Fatal.

**Mensagem:**
```
✗ Projeto não encontrado em <path>.
  Arquivo CLAUDE.md ausente. Rode `initializing-project` primeiro para criar a estrutura.
```

### Plano não construído

**Sintoma:** `<proj>/1-planning/` existe mas está vazio ou falta `plano-projeto.html`.

**Severidade:** Fatal.

**Mensagem:**
```
✗ Plano de projeto não encontrado.
  Esperado: <proj>/1-planning/plano-projeto.html
  Rode `building-project-plan` primeiro para gerar os 10 HTMLs do plano.
```

### Cronograma LIVE ausente

**Sintoma:** `<proj>/4-status-report/Cronograma.xlsx` não existe.

**Severidade:** Fatal.

**Mensagem:**
```
✗ Cronograma LIVE não inicializado.
  Esperado: <proj>/4-status-report/Cronograma.xlsx
  Rode `managing-action-plan init` para criar o LIVE a partir da BASELINE.
```

### Dependências Python ausentes

**Sintoma:** `ImportError` em `openpyxl`, `jinja2`, `beautifulsoup4`, ou `python-pptx`.

**Severidade:** Fatal.

**Mensagem:**
```
✗ Dependência Python ausente: <nome>.
  Instale com: pip install openpyxl jinja2 beautifulsoup4 python-pptx
```

### playwright E weasyprint ambos ausentes

**Sintoma:** Ao invocar `build_opr.py`, `ImportError` em ambos.

**Severidade:** Fatal (para OPR; PPTX pode ser gerado sozinho com `--only pptx`).

**Mensagem:**
```
✗ Nenhum driver HTML→PDF instalado.
  Instale:
    pip install playwright && playwright install chromium  (recomendado)
  OU:
    pip install weasyprint  (mais leve, suporte CSS limitado)
```

---

## Dados inconsistentes

### Cronograma com schema quebrado

**Sintoma:** Falta uma das colunas obrigatórias (`No.`, `Tipo`, `Etapa`, `Status`, `Fim Planejado`).

**Severidade:** Fatal.

**Mensagem:**
```
✗ Cronograma.xlsx com schema inválido.
  Colunas faltantes: <lista>
  Verifique o header na linha R4 da sheet principal.
```

### HTML do plano com estrutura divergente

**Sintoma:** BeautifulSoup não encontra seletores esperados (ex: `<h1>` para title, `.hero-meta` para metadata).

**Severidade:** Warning (nunca fatal — degradação graceful).

**Mensagem:**
```
⚠ plano-projeto.html: seletor `.hero-meta` não encontrado.
  Campo `project.pm` preenchido com placeholder "— não identificado —".
  Revalide o HTML rodando `building-project-plan` novamente se necessário.
```

### riscos.html ausente ou vazio

**Sintoma:** Arquivo não existe, ou existe mas `tbody` está vazio.

**Severidade:** Warning.

**Mensagem:**
```
⚠ riscos.html não encontrado ou sem linhas.
  Seção Riscos do PPTX e OPR terá placeholder "Nenhum risco mapeado".
```

### changelog.md vazio

**Sintoma:** Arquivo existe mas sem entries (ou menos de 3 entries no período).

**Severidade:** Warning.

**Mensagem:**
```
⚠ changelog.md tem poucas entries no período dos últimos 14 dias.
  Highlights podem estar incompletos.
  Se o projeto tem atividade real recente, verifique se `managing-action-plan` está sincronizando os eventos.
```

---

## Staleness

### `.sync-state.json` indica sync pendente

**Sintoma:** `sync_pending=true` ou `last_sync > 48h` antes de `report_date`.

**Severidade:** Warning (visível no topo do output).

**Mensagem:**
```
⚠ Dados podem estar desatualizados:
  last_sync: 2026-04-15T10:00:00 (há 72h)
  sync_pending: true
  Recomendado: rode `managing-action-plan sync` antes do reporte.
  (Continuando mesmo assim — pressione Ctrl+C para abortar.)
```

A skill continua a execução após 2s de pausa para o usuário poder abortar se quiser.

---

## Problemas de render

### OPR excede 1 página em modo normal

**Sintoma:** playwright mede `scrollHeight > 1123px` após render inicial.

**Severidade:** Silent OK (aplica modo compacto automaticamente) → Warning se persistir.

**Comportamento:**
1. Aplica classe `.compact` no `<body>`, rerender.
2. Se ainda excede: trunca highlights/next_steps/attentions para 2 itens cada (de 3), rerender.
3. Se ainda excede: imprime warning e mantém OPR com overflow (corte visível).

**Mensagem de warning (casos 2-3):**
```
⚠ OPR excedeu 1 página em modo compacto.
  Conteúdo truncado para 2 bullets por seção.
  Considere simplificar o objetivo ou reduzir marcos.
```

### Fonte Arial indisponível

**Sintoma:** weasyprint emite warning sobre fontes (`WARNING: Ignored 'font-family: "Arial"'`).

**Severidade:** Warning.

**Comportamento:** cai em `system-ui, sans-serif` via CSS fallback stack. Output visual pode variar ligeiramente entre sistemas.

**Mensagem:**
```
⚠ Fonte Arial não instalada no sistema.
  Usando fallback system-ui. OPR pode ter métricas tipográficas diferentes do design original.
```

### Logo M7 ausente

**Sintoma:** `assets/m7-logo-dark.png` ou `assets/m7-logo-offwhite.png` não encontrado.

**Severidade:** Warning.

**Comportamento:** renderiza o canto onde iria o logo com texto estilizado `M7` em itálico (cor apropriada ao fundo).

**Mensagem:**
```
⚠ Logo M7 ausente em assets/<arquivo>.png
  Usando proxy textual "M7" no canto superior direito.
```

---

## Conflitos de output

### Subpasta `YYYY-MM-DD/` já existe

**Sintoma:** Segunda execução no mesmo dia sem `--force`.

**Severidade:** Fatal.

**Mensagem:**
```
✗ Subpasta 4-status-report/2026-04-18/ já existe com arquivos.
  Opções:
    a) Rode com --force para sobrescrever
    b) Use --report-date YYYY-MM-DD diferente
    c) Apague a subpasta manualmente
```

### Build parcial (OPR gerou, PPTX falhou)

**Sintoma:** Execução aborta no meio; 1 arquivo OK, 2 incompletos.

**Severidade:** Fatal.

**Comportamento:** o código de `build_pptx.py` é idempotente — rerun após fix gera todos de novo. Não é necessário limpar nada.

---

## Recovery patterns

### "Só rodei e não gerou nada"

Checar na ordem:
1. `cwd` correto? Passar `--project-dir <path>` explícito
2. `CLAUDE.md` existe? → `initializing-project`
3. `Cronograma.xlsx` LIVE existe? → `managing-action-plan init`
4. HTMLs do plano existem? → `building-project-plan`
5. Dependências Python? → `pip install ...`

### "PPTX abriu quebrado no PowerPoint"

- Verificar fonte Arial instalada no sistema que abre o PPTX
- Verificar se o python-pptx está em versão recente (`pip show python-pptx` → ≥ 0.6.21)
- Abrir em Keynote se PowerPoint não funcionar — diferenças esperadas em alguns shapes rotacionados

### "OPR PDF tem páginas extras em branco"

- Modo compacto não detectou overflow — rodar com `--debug-overflow` para ver altura exata medida
- playwright vs weasyprint podem dar resultados diferentes — testar o outro driver

### "Dados estão desatualizados"

- Verificar `.sync-state.json` — se `sync_pending=true`, rodar `managing-action-plan sync` antes
- Verificar que `managing-action-plan` foi rodado após mudanças recentes no ClickUp
- Forçar rerun do collect com `--no-cache` (se implementado)

---

## Debug flags

| Flag | Efeito |
|---|---|
| `--debug` | Imprime dict canônico completo em stdout após collect |
| `--debug-overflow` | Log de medidas de altura em cada tentativa de render OPR |
| `--keep-html` | Não deleta o HTML intermediário após gerar PDF (útil para inspecionar CSS) |
| `--dry-run` | Coleta + valida, mas não escreve arquivos |
