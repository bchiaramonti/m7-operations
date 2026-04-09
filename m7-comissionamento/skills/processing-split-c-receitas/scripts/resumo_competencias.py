#!/usr/bin/env python3
"""
Resumo de Competencias - Split C (Multicamadas)
================================================
Exibe resumo consolidado de todas as competencias carregadas nas 3 camadas:
- Bronze: bronze.split_c_receitas_detalhadas
- Silver: silver.vw_fact_receitas_comissionadas
- Gold: gold.vw_receitas_comissionadas_assessor

Uso:
    python resumo_competencias.py

Requer variáveis de ambiente (ou arquivo credentials/.env):
    DB_SERVER, DB_DATABASE, DB_USERNAME, DB_PASSWORD, DB_DRIVER
"""

import os
import sys
from pathlib import Path

import pyodbc
from dotenv import load_dotenv

# Carregar variáveis de ambiente
env_paths = [
    Path(__file__).parent.parent.parent.parent.parent / 'credentials' / '.env',
    Path.cwd() / 'credentials' / '.env',
    Path.cwd() / '.env',
]
for env_path in env_paths:
    if env_path.exists():
        load_dotenv(env_path)
        break


def get_connection_string() -> str:
    """Monta string de conexão a partir das variáveis de ambiente"""
    driver = os.getenv('DB_DRIVER', 'ODBC Driver 17 for SQL Server')
    server = os.getenv('DB_SERVER')
    database = os.getenv('DB_DATABASE')
    username = os.getenv('DB_USERNAME')
    password = os.getenv('DB_PASSWORD')

    if not all([server, database, username, password]):
        raise ValueError(
            "Variáveis de ambiente não configuradas. "
            "Defina: DB_SERVER, DB_DATABASE, DB_USERNAME, DB_PASSWORD"
        )

    return (
        f"DRIVER={{{driver}}};"
        f"SERVER={server};"
        f"DATABASE={database};"
        f"UID={username};"
        f"PWD={password}"
    )


def exibir_resumo():
    """Exibe resumo consolidado das 3 camadas"""
    try:
        conn_string = get_connection_string()
        conn = pyodbc.connect(conn_string)
        cursor = conn.cursor()

        # =================================================================
        # BRONZE
        # =================================================================
        print()
        print("=" * 90)
        print("CAMADA BRONZE - bronze.split_c_receitas_detalhadas")
        print("=" * 90)
        print(f"{'Competencia':<15} {'Registros':>15} {'Receita Bruta':>25} {'Comissao Escritorio':>25}")
        print("-" * 90)

        cursor.execute('''
            SELECT
                anomes_operacao AS competencia,
                COUNT(*) AS qtd_registros,
                SUM(receita_bruta) AS receita_bruta,
                SUM(comissao_escritorio) AS comissao_escritorio
            FROM bronze.split_c_receitas_detalhadas
            GROUP BY anomes_operacao
            ORDER BY anomes_operacao DESC
        ''')

        bronze_rows = cursor.fetchall()
        bronze_total_reg = 0
        bronze_total_bruta = 0
        bronze_total_comissao = 0

        if not bronze_rows:
            print("Nenhuma competencia carregada na camada Bronze.")
        else:
            for row in bronze_rows:
                comp = row[0]
                qtd = row[1]
                bruta = row[2] or 0
                comissao = row[3] or 0
                bronze_total_reg += qtd
                bronze_total_bruta += bruta
                bronze_total_comissao += comissao
                print(f"{comp:<15} {qtd:>15,} R$ {bruta:>22,.2f} R$ {comissao:>22,.2f}")

            print("-" * 90)
            print(f"{'TOTAL BRONZE':<15} {bronze_total_reg:>15,} R$ {bronze_total_bruta:>22,.2f} R$ {bronze_total_comissao:>22,.2f}")

        # =================================================================
        # SILVER
        # =================================================================
        print()
        print("=" * 90)
        print("CAMADA SILVER - silver.vw_fact_receitas_comissionadas")
        print("=" * 90)
        print(f"{'Competencia':<15} {'Registros':>15} {'Investimentos':>25} {'Cross-Sell':>25}")
        print("-" * 90)

        cursor.execute('''
            SELECT
                anomes_operacao AS competencia,
                COUNT(*) AS qtd_registros,
                SUM(CASE WHEN fonte_receita = 'Investimentos' THEN comissao_escritorio ELSE 0 END) AS investimentos,
                SUM(CASE WHEN fonte_receita = 'Cross-Sell' THEN comissao_escritorio ELSE 0 END) AS cross_sell
            FROM silver.vw_fact_receitas_comissionadas
            GROUP BY anomes_operacao
            ORDER BY anomes_operacao DESC
        ''')

        silver_rows = cursor.fetchall()
        silver_total_reg = 0
        silver_total_inv = 0
        silver_total_cross = 0

        if not silver_rows:
            print("Nenhuma competencia na camada Silver.")
        else:
            for row in silver_rows:
                comp = row[0]
                qtd = row[1]
                inv = row[2] or 0
                cross = row[3] or 0
                silver_total_reg += qtd
                silver_total_inv += inv
                silver_total_cross += cross
                print(f"{comp:<15} {qtd:>15,} R$ {inv:>22,.2f} R$ {cross:>22,.2f}")

            print("-" * 90)
            print(f"{'TOTAL SILVER':<15} {silver_total_reg:>15,} R$ {silver_total_inv:>22,.2f} R$ {silver_total_cross:>22,.2f}")

        # =================================================================
        # GOLD
        # =================================================================
        print()
        print("=" * 90)
        print("CAMADA GOLD - gold.vw_receitas_comissionadas_assessor")
        print("=" * 90)
        print(f"{'Competencia':<15} {'Assessores':>15} {'Receita Total':>25} {'Qtd Clientes':>25}")
        print("-" * 90)

        cursor.execute('''
            SELECT
                ano_mes_operacao AS competencia,
                COUNT(DISTINCT codigo_assessor_xp) AS qtd_assessores,
                SUM(receita_total) AS receita_total,
                SUM(ISNULL(clientes_operando_rv, 0) + ISNULL(clientes_operando_int_camb, 0) + ISNULL(clientes_operando_rf, 0)) AS qtd_clientes
            FROM gold.vw_receitas_comissionadas_assessor
            GROUP BY ano_mes_operacao
            ORDER BY ano_mes_operacao DESC
        ''')

        gold_rows = cursor.fetchall()
        gold_total_ass = 0
        gold_total_receita = 0
        gold_total_clientes = 0

        if not gold_rows:
            print("Nenhuma competencia na camada Gold.")
        else:
            for row in gold_rows:
                comp = row[0]
                ass = row[1]
                receita = row[2] or 0
                clientes = row[3] or 0
                gold_total_ass = max(gold_total_ass, ass)  # Maximo de assessores
                gold_total_receita += receita
                gold_total_clientes += clientes
                print(f"{comp:<15} {ass:>15,} R$ {receita:>22,.2f} {clientes:>25,}")

            print("-" * 90)
            print(f"{'TOTAL GOLD':<15} {gold_total_ass:>15,} R$ {gold_total_receita:>22,.2f} {gold_total_clientes:>25,}")

        # =================================================================
        # RESUMO CONSOLIDADO
        # =================================================================
        print()
        print("=" * 90)
        print("RESUMO CONSOLIDADO")
        print("=" * 90)
        print()

        # Verificar integridade Bronze vs Silver
        diff_reg = bronze_total_reg - silver_total_reg
        diff_comissao = bronze_total_comissao - (silver_total_inv + silver_total_cross)

        print("INTEGRIDADE DAS CAMADAS:")
        print()
        print(f"  Bronze total registros:    {bronze_total_reg:>15,}")
        print(f"  Silver total registros:    {silver_total_reg:>15,}")
        print(f"  Diferenca:                 {diff_reg:>15,}", end="")
        if diff_reg == 0:
            print(" (OK)")
        else:
            print(" (DIVERGENTE)")

        print()
        print(f"  Bronze comissao total:     R$ {bronze_total_comissao:>15,.2f}")
        print(f"  Silver comissao total:     R$ {(silver_total_inv + silver_total_cross):>15,.2f}")
        print(f"  Diferenca:                 R$ {diff_comissao:>15,.2f}", end="")
        if abs(diff_comissao) <= 0.01:
            print(" (OK)")
        else:
            print(" (DIVERGENTE)")

        print()
        print(f"  Gold receita total:        R$ {gold_total_receita:>15,.2f}")
        diff_gold = (silver_total_inv + silver_total_cross) - gold_total_receita
        print(f"  Diff Silver vs Gold:       R$ {diff_gold:>15,.2f}", end="")
        if abs(diff_gold) <= 0.01:
            print(" (OK)")
        else:
            print(" (DIVERGENTE)")

        # Verificar classificacoes pendentes
        cursor.execute('''
            SELECT COUNT(DISTINCT b.classe_comissao)
            FROM bronze.split_c_receitas_detalhadas b
            LEFT JOIN bronze.comissao_classificacao c ON b.classe_comissao = c.classe_comissao
            WHERE b.classe_comissao IS NOT NULL
              AND b.classe_comissao != ''
              AND c.classe_comissao IS NULL
        ''')
        pendentes = cursor.fetchone()[0]

        print()
        print("CLASSIFICACOES:")
        print(f"  Classes pendentes:         {pendentes:>15,}")
        if pendentes > 0:
            print("  >>> Execute: python classificar_comissoes.py")

        print()
        print("=" * 90)

        # Status final
        todas_ok = (diff_reg == 0 and abs(diff_comissao) <= 0.01 and abs(diff_gold) <= 0.01 and pendentes == 0)

        if todas_ok:
            print(">>> TODAS AS CAMADAS INTEGRAS <<<")
        else:
            print(">>> ATENCAO: VERIFICAR DIVERGENCIAS ACIMA <<<")

        print("=" * 90)
        print()

        conn.close()

    except Exception as e:
        print(f"\nErro ao consultar banco: {e}")
        sys.exit(1)


if __name__ == '__main__':
    exibir_resumo()
