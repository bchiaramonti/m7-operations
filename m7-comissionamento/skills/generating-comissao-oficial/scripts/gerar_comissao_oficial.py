#!/usr/bin/env python3
"""
Gera arquivo comissao_oficial_louro_tech_YYYY-MM.xlsx a partir do RECEITAS_DETALHADAS.

Uso:
    python3 gerar_comissao_oficial.py <caminho_competencia> <competencia_YYYYMM>

Exemplo:
    python3 gerar_comissao_oficial.py "/path/to/2025/12-25" "202512"

Lê de: raw/RECEITAS_DETALHADAS_{YYYY}_{MM}.csv
Salva em: fase4_dados/comissao_oficial_louro_tech_{YYYY}-{MM}.xlsx
"""

import sys
import calendar
import pandas as pd
from pathlib import Path
from datetime import datetime


def converter_decimal_br(valor):
    """Converte string com formato brasileiro (vírgula) para float."""
    if pd.isna(valor) or valor == "":
        return 0.0
    if isinstance(valor, (int, float)):
        return float(valor)
    return float(str(valor).replace(".", "").replace(",", "."))


def ajustar_data_competencia(data, ano_comp: int, mes_comp: int):
    """
    Ajusta a data para a competência correta.

    - Se data é NaT (vazia): retorna último dia da competência
    - Se data é de outro mês: ajusta para o mês da competência
      (mantém o dia se possível, senão usa último dia do mês)

    Args:
        data: datetime ou NaT
        ano_comp: Ano da competência (ex: 2025)
        mes_comp: Mês da competência (ex: 12)

    Returns:
        datetime ajustado para a competência
    """
    # Último dia do mês da competência
    ultimo_dia = calendar.monthrange(ano_comp, mes_comp)[1]

    # Se data é vazia (NaT), usar último dia da competência
    if pd.isna(data):
        return datetime(ano_comp, mes_comp, ultimo_dia)

    # Se data já é do mês correto, manter
    if data.month == mes_comp and data.year == ano_comp:
        return data

    # Se data é de outro mês, ajustar para a competência
    # Tentar manter o mesmo dia, se não existir usar último dia
    dia_original = data.day
    dia_ajustado = min(dia_original, ultimo_dia)

    return datetime(ano_comp, mes_comp, dia_ajustado)


def gerar_comissao_oficial(caminho_competencia: str, competencia: str) -> str:
    """
    Gera o arquivo comissao_oficial_louro_tech_YYYY-MM.xlsx.

    Args:
        caminho_competencia: Caminho para a pasta da competência (ex: 2025/12-25)
        competencia: Competência no formato YYYYMM (ex: 202512)

    Returns:
        Caminho do arquivo gerado
    """
    # Construir caminhos
    ano = competencia[:4]
    mes = competencia[4:6]
    ano_int = int(ano)
    mes_int = int(mes)

    caminho_base = Path(caminho_competencia)
    caminho_raw = caminho_base / "raw"
    caminho_fase4 = caminho_base / "fase4_dados"

    arquivo_entrada = f"RECEITAS_DETALHADAS_{ano}_{mes}.csv"
    caminho_entrada = caminho_raw / arquivo_entrada

    # Validar existência
    if not caminho_entrada.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho_entrada}")

    # Garantir que pasta fase4_dados existe
    caminho_fase4.mkdir(parents=True, exist_ok=True)

    print(f"Lendo arquivo: {caminho_entrada}")
    print(f"Competência: {mes}/{ano}")

    # Ler CSV com encoding UTF-8-BOM e separador ponto-e-vírgula
    df = pd.read_csv(
        caminho_entrada,
        sep=";",
        encoding="utf-8-sig",
        dtype=str  # Ler tudo como string primeiro
    )

    print(f"Linhas lidas: {len(df)}")

    # Verificar colunas obrigatórias para o output
    colunas_obrigatorias = [
        "Classificação", "Categoria", "Nível 1", "Nível 2", "Nível 3", "Nível 4",
        "Código Cliente", "Código Assessor", "Data", "Comissão Escritório"
    ]

    colunas_faltando = [col for col in colunas_obrigatorias if col not in df.columns]
    if colunas_faltando:
        raise ValueError(f"Colunas faltando no arquivo: {colunas_faltando}")

    # Converter Data para datetime
    df["Data_parsed"] = pd.to_datetime(df["Data"], dayfirst=True, errors="coerce")

    # Estatísticas de datas antes do ajuste
    datas_vazias = df["Data_parsed"].isna().sum()
    datas_outro_mes = ((df["Data_parsed"].dt.month != mes_int) | (df["Data_parsed"].dt.year != ano_int)).sum() - datas_vazias

    print(f"\n=== AJUSTE DE DATAS ===")
    print(f"Datas vazias (serão preenchidas com último dia do mês): {datas_vazias}")
    print(f"Datas de outros meses (serão ajustadas): {max(0, datas_outro_mes)}")

    # Ajustar todas as datas para a competência
    df["Data_ajustada"] = df["Data_parsed"].apply(
        lambda x: ajustar_data_competencia(x, ano_int, mes_int)
    )

    # Criar DataFrame de saída com as 10 colunas do template Louro Tech
    df_saida = pd.DataFrame()

    # 1. Classificação
    df_saida["Classificação"] = df["Classificação"]

    # 2. Produto/Categoria (cópia da Categoria)
    df_saida["Produto/Categoria"] = df["Categoria"]

    # 3-6. Níveis hierárquicos
    df_saida["Nível 1"] = df["Nível 1"]
    df_saida["Nível 2"] = df["Nível 2"]
    df_saida["Nível 3"] = df["Nível 3"]
    df_saida["Nível 4"] = df["Nível 4"]

    # 7. Código Cliente - converter para numérico
    df_saida["Código Cliente"] = pd.to_numeric(df["Código Cliente"], errors="coerce")

    # 8. Data - usar data ajustada para a competência
    df_saida["Data"] = df["Data_ajustada"]

    # 9. Comissão (R$) Escritório - converter formato brasileiro
    df_saida["Comissão (R$) Escritório"] = df["Comissão Escritório"].apply(converter_decimal_br)

    # 10. Código Assessor (última coluna)
    df_saida["Código Assessor"] = df["Código Assessor"]

    # Limpar valores vazios representados como ""
    df_saida = df_saida.replace('""', "")
    df_saida = df_saida.replace('"', "")

    # Caminho de saída com sufixo YYYY-MM
    nome_arquivo = f"comissao_oficial_louro_tech_{ano}-{mes}.xlsx"
    arquivo_saida = caminho_fase4 / nome_arquivo

    print(f"\nGerando arquivo: {arquivo_saida}")

    # Salvar como Excel
    df_saida.to_excel(arquivo_saida, index=False, engine="openpyxl")

    print(f"\nArquivo gerado com sucesso!")
    print(f"Total de linhas: {len(df_saida)}")
    print(f"Colunas: {list(df_saida.columns)}")

    # Verificar datas após ajuste
    print(f"\n=== VERIFICAÇÃO ===")
    print(f"Todas as datas são de {mes}/{ano}: {(df_saida['Data'].dt.month == mes_int).all()}")

    return str(arquivo_saida)


def main():
    if len(sys.argv) < 3:
        print("Uso: python3 gerar_comissao_oficial.py <caminho_competencia> <competencia_YYYYMM>")
        print("Exemplo: python3 gerar_comissao_oficial.py '/path/to/2025/12-25' '202512'")
        print()
        print("Lê de: raw/RECEITAS_DETALHADAS_{YYYY}_{MM}.csv")
        print("Salva em: fase4_dados/comissao_oficial_louro_tech_{YYYY}-{MM}.xlsx")
        sys.exit(1)

    caminho_competencia = sys.argv[1]
    competencia = sys.argv[2]

    try:
        arquivo_gerado = gerar_comissao_oficial(caminho_competencia, competencia)
        print(f"\nSucesso! Arquivo gerado: {arquivo_gerado}")
    except Exception as e:
        print(f"\nErro: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
