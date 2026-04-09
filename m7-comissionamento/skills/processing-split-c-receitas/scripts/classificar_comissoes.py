#!/usr/bin/env python3
"""
Classificador de Comissoes - Split C
=====================================
Classifica comissoes como "Investimentos" ou "Cross-Sell"

Uso:
    python classificar_comissoes.py

Requer variáveis de ambiente (ou arquivo credentials/.env):
    DB_SERVER, DB_DATABASE, DB_USERNAME, DB_PASSWORD, DB_DRIVER
"""

import os
import sys
from pathlib import Path
from typing import List, Optional

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


def obter_classes_nao_classificadas(cursor) -> List[str]:
    """Busca classes de comissao que ainda nao estao classificadas"""
    cursor.execute('''
        SELECT DISTINCT b.classe_comissao
        FROM bronze.split_c_receitas_detalhadas b
        LEFT JOIN bronze.comissao_classificacao c ON b.classe_comissao = c.classe_comissao
        WHERE b.classe_comissao IS NOT NULL
          AND b.classe_comissao != ''
          AND c.classe_comissao IS NULL
        ORDER BY b.classe_comissao
    ''')
    rows = cursor.fetchall()
    return [row[0] for row in rows]


def obter_total_classes(cursor) -> int:
    """Conta total de classes distintas"""
    cursor.execute('''
        SELECT COUNT(DISTINCT classe_comissao)
        FROM bronze.split_c_receitas_detalhadas
        WHERE classe_comissao IS NOT NULL AND classe_comissao != ''
    ''')
    result = cursor.fetchone()
    return result[0] if result else 0


def obter_classes_classificadas(cursor) -> int:
    """Conta classes ja classificadas"""
    cursor.execute('SELECT COUNT(*) FROM bronze.comissao_classificacao')
    result = cursor.fetchone()
    return result[0] if result else 0


def solicitar_classificacao(classe: str) -> Optional[str]:
    """Exibe prompt interativo para classificacao"""
    print()
    print("=" * 60)
    print("CLASSIFICACAO DE COMISSAO")
    print("=" * 60)
    print()
    print(f"Classe: {classe}")
    print()
    print("[1] Investimentos (receitas core)")
    print("[2] Cross-Sell (produtos complementares)")
    print("[s] Pular esta classificacao")
    print("[q] Sair do classificador")
    print()

    while True:
        escolha = input("Escolha: ").strip().lower()

        if escolha == '1':
            return 'Investimentos'
        elif escolha == '2':
            return 'Cross-Sell'
        elif escolha == 's':
            print("Classificacao pulada.")
            return None
        elif escolha == 'q':
            return 'QUIT'
        else:
            print("Opcao invalida. Use 1, 2, s ou q.")


def inserir_classificacao(cursor, conn, classe: str, fonte: str) -> bool:
    """Insere classificacao no banco"""
    try:
        cursor.execute(
            'INSERT INTO bronze.comissao_classificacao (classe_comissao, fonte_receita) VALUES (?, ?)',
            (classe, fonte)
        )
        conn.commit()
        print(f"Classificado como: {fonte}")
        return True
    except Exception as e:
        print(f"Erro ao inserir classificacao: {e}")
        return False


def classificar_comissoes():
    """Executa o fluxo completo de classificacao"""
    try:
        conn_string = get_connection_string()
        conn = pyodbc.connect(conn_string)
        cursor = conn.cursor()

        print()
        print("=" * 60)
        print("CLASSIFICADOR INTERATIVO DE COMISSOES")
        print("=" * 60)
        print()

        # Estatisticas iniciais
        total = obter_total_classes(cursor)
        classificadas = obter_classes_classificadas(cursor)
        print(f"Total de classes distintas: {total}")
        print(f"Ja classificadas: {classificadas}")

        # Buscar pendentes
        pendentes = obter_classes_nao_classificadas(cursor)
        print(f"Pendentes de classificacao: {len(pendentes)}")

        if not pendentes:
            print()
            print("=" * 60)
            print("Todas as classes ja estao classificadas!")
            print("=" * 60)
            print()
            conn.close()
            return {
                'total': total,
                'classificadas': classificadas,
                'pendentes': 0,
                'processadas': 0,
                'puladas': 0
            }

        # Processar cada pendente
        stats = {
            'total': len(pendentes),
            'classificadas_agora': 0,
            'puladas': 0
        }

        print()
        print(f"Iniciando classificacao de {len(pendentes)} classes...")

        for idx, classe in enumerate(pendentes, 1):
            print(f"\n[{idx}/{len(pendentes)}]")

            fonte = solicitar_classificacao(classe)

            if fonte == 'QUIT':
                print("\nSaindo do classificador...")
                break
            elif fonte:
                sucesso = inserir_classificacao(cursor, conn, classe, fonte)
                if sucesso:
                    stats['classificadas_agora'] += 1
            else:
                stats['puladas'] += 1

        # Resumo final
        print()
        print("=" * 60)
        print("CLASSIFICACAO CONCLUIDA")
        print("=" * 60)
        print()
        print(f"Classes processadas: {stats['classificadas_agora'] + stats['puladas']}")
        print(f"  - Classificadas: {stats['classificadas_agora']}")
        print(f"  - Puladas: {stats['puladas']}")
        print(f"  - Restantes: {len(pendentes) - stats['classificadas_agora'] - stats['puladas']}")
        print()

        conn.close()
        return stats

    except Exception as e:
        print(f"\nErro ao classificar comissoes: {e}")
        sys.exit(1)


if __name__ == '__main__':
    classificar_comissoes()
