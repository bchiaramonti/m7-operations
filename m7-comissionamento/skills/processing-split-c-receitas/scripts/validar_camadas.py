#!/usr/bin/env python3
"""
Validador Multicamadas - Split C
=================================
Valida integridade entre Bronze → Silver → Gold

Uso:
    python validar_camadas.py

Requer variáveis de ambiente (ou arquivo credentials/.env):
    DB_SERVER, DB_DATABASE, DB_USERNAME, DB_PASSWORD, DB_DRIVER
"""

import os
import sys
from pathlib import Path
from typing import Dict, List

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


def validar_bronze_vs_silver(cursor) -> Dict:
    """Compara totais Bronze vs Silver"""

    # Query Bronze
    cursor.execute('''
        SELECT
            COUNT(*) as qtd,
            SUM(receita_bruta) as receita_bruta,
            SUM(receita_liquida) as receita_liquida,
            SUM(comissao_escritorio) as comissao_escritorio
        FROM bronze.split_c_receitas_detalhadas
    ''')
    bronze_row = cursor.fetchone()

    # Query Silver
    cursor.execute('''
        SELECT
            COUNT(*) as qtd,
            SUM(receita_bruta) as receita_bruta,
            SUM(receita_liquida) as receita_liquida,
            SUM(comissao_escritorio) as comissao_escritorio
        FROM silver.vw_fact_receitas_comissionadas
    ''')
    silver_row = cursor.fetchone()

    bronze = {
        'qtd': bronze_row[0] if bronze_row else 0,
        'receita_bruta': float(bronze_row[1] or 0) if bronze_row else 0.0,
        'receita_liquida': float(bronze_row[2] or 0) if bronze_row else 0.0,
        'comissao_escritorio': float(bronze_row[3] or 0) if bronze_row else 0.0
    }

    silver = {
        'qtd': silver_row[0] if silver_row else 0,
        'receita_bruta': float(silver_row[1] or 0) if silver_row else 0.0,
        'receita_liquida': float(silver_row[2] or 0) if silver_row else 0.0,
        'comissao_escritorio': float(silver_row[3] or 0) if silver_row else 0.0
    }

    # Verificar divergências (tolerância de 0.01)
    divergente = (
        bronze['qtd'] != silver['qtd'] or
        abs(bronze['receita_bruta'] - silver['receita_bruta']) > 0.01 or
        abs(bronze['receita_liquida'] - silver['receita_liquida']) > 0.01 or
        abs(bronze['comissao_escritorio'] - silver['comissao_escritorio']) > 0.01
    )

    return {
        'divergente': divergente,
        'bronze': bronze,
        'silver': silver
    }


def validar_silver_vs_gold(cursor) -> Dict:
    """Compara totais Silver vs Gold"""

    # Query Silver
    cursor.execute('''
        SELECT
            SUM(comissao_escritorio) as total,
            SUM(CASE WHEN fonte_receita = 'Investimentos' THEN comissao_escritorio ELSE 0 END) as investimentos,
            SUM(CASE WHEN fonte_receita = 'Cross-Sell' THEN comissao_escritorio ELSE 0 END) as [cross]
        FROM silver.vw_fact_receitas_comissionadas
    ''')
    silver_row = cursor.fetchone()

    # Query Gold
    cursor.execute('''
        SELECT
            SUM(receita_total) as total,
            SUM(receita_investimentos) as investimentos,
            SUM(receita_cross) as [cross]
        FROM gold.vw_receitas_comissionadas_assessor
    ''')
    gold_row = cursor.fetchone()

    silver = {
        'total': float(silver_row[0] or 0) if silver_row else 0.0,
        'investimentos': float(silver_row[1] or 0) if silver_row else 0.0,
        'cross': float(silver_row[2] or 0) if silver_row else 0.0
    }

    gold = {
        'total': float(gold_row[0] or 0) if gold_row else 0.0,
        'investimentos': float(gold_row[1] or 0) if gold_row else 0.0,
        'cross': float(gold_row[2] or 0) if gold_row else 0.0
    }

    # Verificar divergências (tolerância de 0.01)
    divergente = (
        abs(silver['total'] - gold['total']) > 0.01 or
        abs(silver['investimentos'] - gold['investimentos']) > 0.01 or
        abs(silver['cross'] - gold['cross']) > 0.01
    )

    return {
        'divergente': divergente,
        'silver': silver,
        'gold': gold
    }


def contar_classificacoes_pendentes(cursor) -> int:
    """Conta classes de comissão que não estão classificadas"""
    cursor.execute('''
        SELECT COUNT(DISTINCT b.classe_comissao)
        FROM bronze.split_c_receitas_detalhadas b
        LEFT JOIN bronze.comissao_classificacao c ON b.classe_comissao = c.classe_comissao
        WHERE b.classe_comissao IS NOT NULL
          AND b.classe_comissao != ''
          AND c.classe_comissao IS NULL
    ''')
    result = cursor.fetchone()
    return result[0] if result else 0


def validar_camadas():
    """Executa validação completa das 3 camadas"""
    try:
        conn_string = get_connection_string()
        conn = pyodbc.connect(conn_string)
        cursor = conn.cursor()

        print()
        print("=" * 70)
        print("VALIDACAO MULTICAMADAS - BRONZE -> SILVER -> GOLD")
        print("=" * 70)

        resultado = {
            'bronze_vs_silver': {'divergente': False},
            'silver_vs_gold': {'divergente': False},
            'classificacoes_pendentes': 0
        }

        # =================================================================
        # SECAO 1: BRONZE vs SILVER
        # =================================================================
        print()
        print("-" * 70)
        print("SECAO 1: BRONZE -> SILVER")
        print("-" * 70)

        bs = validar_bronze_vs_silver(cursor)
        resultado['bronze_vs_silver'] = bs

        print()
        print("QUANTIDADE DE REGISTROS:")
        print(f"  Bronze: {bs['bronze']['qtd']:>15,}")
        print(f"  Silver: {bs['silver']['qtd']:>15,}")
        status_qtd = "OK" if bs['bronze']['qtd'] == bs['silver']['qtd'] else "DIVERGENTE"
        print(f"  Status: {status_qtd}")

        print()
        print("RECEITA BRUTA:")
        print(f"  Bronze: R$ {bs['bronze']['receita_bruta']:>15,.2f}")
        print(f"  Silver: R$ {bs['silver']['receita_bruta']:>15,.2f}")
        diff_bruta = abs(bs['bronze']['receita_bruta'] - bs['silver']['receita_bruta'])
        status_bruta = "OK" if diff_bruta <= 0.01 else f"DIFF: R$ {diff_bruta:,.2f}"
        print(f"  Status: {status_bruta}")

        print()
        print("RECEITA LIQUIDA:")
        print(f"  Bronze: R$ {bs['bronze']['receita_liquida']:>15,.2f}")
        print(f"  Silver: R$ {bs['silver']['receita_liquida']:>15,.2f}")
        diff_liquida = abs(bs['bronze']['receita_liquida'] - bs['silver']['receita_liquida'])
        status_liquida = "OK" if diff_liquida <= 0.01 else f"DIFF: R$ {diff_liquida:,.2f}"
        print(f"  Status: {status_liquida}")

        print()
        print("COMISSAO ESCRITORIO:")
        print(f"  Bronze: R$ {bs['bronze']['comissao_escritorio']:>15,.2f}")
        print(f"  Silver: R$ {bs['silver']['comissao_escritorio']:>15,.2f}")
        diff_comissao = abs(bs['bronze']['comissao_escritorio'] - bs['silver']['comissao_escritorio'])
        status_comissao = "OK" if diff_comissao <= 0.01 else f"DIFF: R$ {diff_comissao:,.2f}"
        print(f"  Status: {status_comissao}")

        print()
        if bs['divergente']:
            print(">>> BRONZE -> SILVER: DIVERGENCIAS DETECTADAS <<<")
        else:
            print(">>> BRONZE -> SILVER: VALIDACAO APROVADA <<<")

        # =================================================================
        # SECAO 2: SILVER vs GOLD
        # =================================================================
        print()
        print("-" * 70)
        print("SECAO 2: SILVER -> GOLD")
        print("-" * 70)

        sg = validar_silver_vs_gold(cursor)
        resultado['silver_vs_gold'] = sg

        print()
        print("RECEITA TOTAL:")
        print(f"  Silver: R$ {sg['silver']['total']:>15,.2f}")
        print(f"  Gold:   R$ {sg['gold']['total']:>15,.2f}")
        diff_total = abs(sg['silver']['total'] - sg['gold']['total'])
        status_total = "OK" if diff_total <= 0.01 else f"DIFF: R$ {diff_total:,.2f}"
        print(f"  Status: {status_total}")

        print()
        print("RECEITA INVESTIMENTOS:")
        print(f"  Silver: R$ {sg['silver']['investimentos']:>15,.2f}")
        print(f"  Gold:   R$ {sg['gold']['investimentos']:>15,.2f}")
        diff_inv = abs(sg['silver']['investimentos'] - sg['gold']['investimentos'])
        status_inv = "OK" if diff_inv <= 0.01 else f"DIFF: R$ {diff_inv:,.2f}"
        print(f"  Status: {status_inv}")

        print()
        print("RECEITA CROSS-SELL:")
        print(f"  Silver: R$ {sg['silver']['cross']:>15,.2f}")
        print(f"  Gold:   R$ {sg['gold']['cross']:>15,.2f}")
        diff_cross = abs(sg['silver']['cross'] - sg['gold']['cross'])
        status_cross = "OK" if diff_cross <= 0.01 else f"DIFF: R$ {diff_cross:,.2f}"
        print(f"  Status: {status_cross}")

        print()
        if sg['divergente']:
            print(">>> SILVER -> GOLD: DIVERGENCIAS DETECTADAS <<<")
        else:
            print(">>> SILVER -> GOLD: VALIDACAO APROVADA <<<")

        # =================================================================
        # SECAO 3: CLASSIFICACOES PENDENTES
        # =================================================================
        print()
        print("-" * 70)
        print("SECAO 3: CLASSIFICACOES PENDENTES")
        print("-" * 70)

        pendentes = contar_classificacoes_pendentes(cursor)
        resultado['classificacoes_pendentes'] = pendentes

        print()
        if pendentes > 0:
            print(f">>> ATENCAO: {pendentes} classes de comissao NAO classificadas <<<")
            print("    Execute: python classificar_comissoes.py")
        else:
            print(">>> Todas as classes de comissao estao classificadas <<<")

        # =================================================================
        # RESUMO FINAL
        # =================================================================
        print()
        print("=" * 70)
        print("RESUMO FINAL")
        print("=" * 70)
        print()

        status_bs = "DIVERGENTE" if bs['divergente'] else "OK"
        status_sg = "DIVERGENTE" if sg['divergente'] else "OK"

        print(f"Bronze -> Silver: {status_bs}")
        print(f"Silver -> Gold:   {status_sg}")
        print(f"Classificacoes pendentes: {pendentes}")
        print()

        if not bs['divergente'] and not sg['divergente'] and pendentes == 0:
            print("=" * 70)
            print(">>> TODAS AS VALIDACOES APROVADAS <<<")
            print("=" * 70)
        else:
            print("=" * 70)
            print(">>> ATENCAO: EXISTEM PENDENCIAS - VERIFICAR ACIMA <<<")
            print("=" * 70)

        print()
        conn.close()
        return resultado

    except Exception as e:
        print(f"\nErro ao validar camadas: {e}")
        sys.exit(1)


if __name__ == '__main__':
    validar_camadas()
