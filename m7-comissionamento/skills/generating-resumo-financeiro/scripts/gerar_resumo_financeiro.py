#!/usr/bin/env python3
"""
Gera resumo financeiro de comissões por assessor.

Uso:
    python3 gerar_resumo_financeiro.py <caminho_fase4_dados> <competencia_YYYYMM>

Exemplo:
    python3 gerar_resumo_financeiro.py "/path/to/2025/12-25/fase4_dados" "202512"
"""

import sys
import pandas as pd
from pathlib import Path


def converter_decimal_br(valor):
    """Converte string com formato brasileiro (vírgula) para float."""
    if pd.isna(valor) or valor == "":
        return 0.0
    if isinstance(valor, (int, float)):
        return float(valor)
    return float(str(valor).replace(".", "").replace(",", "."))


def gerar_resumo_financeiro(caminho_fase4: str, competencia: str) -> str:
    """
    Gera o arquivo resumo_financeiro_YYYY-MM.xlsx.

    Args:
        caminho_fase4: Caminho para a pasta fase4_dados
        competencia: Competência no formato YYYYMM (ex: 202512)

    Returns:
        Caminho do arquivo gerado
    """
    # Construir nome do arquivo de entrada
    ano = competencia[:4]
    mes = competencia[4:6]
    arquivo_entrada = f"COMISSOES_CONSOLIDADAS_{ano}_{mes}.csv"
    caminho_entrada = Path(caminho_fase4) / arquivo_entrada

    # Validar existência
    if not caminho_entrada.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho_entrada}")

    print(f"Lendo arquivo: {caminho_entrada}")

    # Ler CSV
    df = pd.read_csv(
        caminho_entrada,
        sep=";",
        encoding="utf-8-sig",
        dtype=str
    )

    print(f"Linhas lidas: {len(df)}")

    # Converter coluna de comissão para numérico
    df["COMISSÃO ASSESSOR LÍQUIDA"] = df["COMISSÃO ASSESSOR LÍQUIDA"].apply(converter_decimal_br)

    # Criar colunas de categorização
    # Seguros/Consórcios: CLASSE DE COMISSÃO = 'Seguros' OU Categoria = 'Consórcio'
    df["is_seguros_consorcio"] = (
        (df["CLASSE DE COMISSÃO"] == "Seguros") |
        (df["Categoria"] == "Consórcio")
    )

    # Plano de Saúde: Categoria contém 'Plano de Saúde'
    df["is_plano_saude"] = df["Categoria"].str.contains("Plano de Saúde", case=False, na=False)

    # Investimentos: tudo que não é seguros/consórcio nem plano de saúde
    df["is_investimentos"] = ~df["is_seguros_consorcio"] & ~df["is_plano_saude"]

    # Agrupar por assessor
    assessores = df.groupby(["Código Assessor", "Nome Assessor"]).agg(
        comissao_investimentos=("COMISSÃO ASSESSOR LÍQUIDA", lambda x: x[df.loc[x.index, "is_investimentos"]].sum()),
        comissao_seguros_consorcio=("COMISSÃO ASSESSOR LÍQUIDA", lambda x: x[df.loc[x.index, "is_seguros_consorcio"]].sum()),
        plano_saude=("COMISSÃO ASSESSOR LÍQUIDA", lambda x: x[df.loc[x.index, "is_plano_saude"]].sum())
    ).reset_index()

    # Calcular total
    assessores["total"] = (
        assessores["comissao_investimentos"] +
        assessores["comissao_seguros_consorcio"] +
        assessores["plano_saude"]
    )

    # Renomear colunas para formato final
    df_saida = pd.DataFrame()
    df_saida["Assessor"] = assessores["Nome Assessor"]
    df_saida["Código"] = assessores["Código Assessor"]
    df_saida["Comissão Investimentos"] = assessores["comissao_investimentos"]
    df_saida["Comissão Seguros/Consórcios"] = assessores["comissao_seguros_consorcio"]
    df_saida["Plano de Saúde"] = assessores["plano_saude"]
    df_saida["Total"] = assessores["total"]

    # Ordenar por nome do assessor
    df_saida = df_saida.sort_values("Assessor")

    # Filtrar assessores com algum valor (remover linhas zeradas)
    df_saida = df_saida[df_saida["Total"] != 0]

    # Caminho de saída
    nome_arquivo = f"resumo_financeiro_{ano}-{mes}.xlsx"
    arquivo_saida = Path(caminho_fase4) / nome_arquivo

    print(f"Gerando arquivo: {arquivo_saida}")

    # Salvar como Excel com formatação
    with pd.ExcelWriter(arquivo_saida, engine="openpyxl") as writer:
        df_saida.to_excel(writer, index=False, sheet_name="Resumo")

        # Ajustar largura das colunas
        worksheet = writer.sheets["Resumo"]
        worksheet.column_dimensions["A"].width = 30  # Assessor
        worksheet.column_dimensions["B"].width = 12  # Código
        worksheet.column_dimensions["C"].width = 25  # Comissão Investimentos
        worksheet.column_dimensions["D"].width = 28  # Comissão Seguros/Consórcios
        worksheet.column_dimensions["E"].width = 18  # Plano de Saúde
        worksheet.column_dimensions["F"].width = 18  # Total

    print(f"Arquivo gerado com sucesso!")
    print(f"Total de assessores: {len(df_saida)}")
    print(f"\n=== TOTAIS ===")
    print(f"Comissão Investimentos:      R$ {df_saida['Comissão Investimentos'].sum():,.2f}")
    print(f"Comissão Seguros/Consórcios: R$ {df_saida['Comissão Seguros/Consórcios'].sum():,.2f}")
    print(f"Plano de Saúde:              R$ {df_saida['Plano de Saúde'].sum():,.2f}")
    print(f"TOTAL GERAL:                 R$ {df_saida['Total'].sum():,.2f}")

    return str(arquivo_saida)


def main():
    if len(sys.argv) < 3:
        print("Uso: python3 gerar_resumo_financeiro.py <caminho_fase4_dados> <competencia_YYYYMM>")
        print("Exemplo: python3 gerar_resumo_financeiro.py '/path/to/fase4_dados' '202512'")
        sys.exit(1)

    caminho_fase4 = sys.argv[1]
    competencia = sys.argv[2]

    try:
        arquivo_gerado = gerar_resumo_financeiro(caminho_fase4, competencia)
        print(f"\nSucesso! Arquivo gerado: {arquivo_gerado}")
    except Exception as e:
        print(f"\nErro: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
