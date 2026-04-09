#!/usr/bin/env python3
"""
ETL Split C - Receitas Detalhadas
=================================
Processa arquivo CSV e carrega em bronze.split_c_receitas_detalhadas

Uso:
    python etl_split_c.py "caminho/do/arquivo.csv"
    python etl_split_c.py "caminho/do/arquivo.csv" --force
    python etl_split_c.py "caminho/do/arquivo.csv" --check-only

Requer variaveis de ambiente (ou arquivo credentials/.env):
    DB_SERVER, DB_DATABASE, DB_USERNAME, DB_PASSWORD, DB_DRIVER
"""

import os
import sys
import re
import hashlib
import argparse
from pathlib import Path
from datetime import datetime, date

import pyodbc
import pandas as pd
from dotenv import load_dotenv

# Carregar variaveis de ambiente
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
    """Monta string de conexao a partir das variaveis de ambiente"""
    driver = os.getenv('DB_DRIVER', 'ODBC Driver 17 for SQL Server')
    server = os.getenv('DB_SERVER')
    database = os.getenv('DB_DATABASE')
    username = os.getenv('DB_USERNAME')
    password = os.getenv('DB_PASSWORD')

    if not all([server, database, username, password]):
        raise ValueError(
            "Variaveis de ambiente nao configuradas. "
            "Defina: DB_SERVER, DB_DATABASE, DB_USERNAME, DB_PASSWORD"
        )

    return (
        f"DRIVER={{{driver}}};"
        f"SERVER={server};"
        f"DATABASE={database};"
        f"UID={username};"
        f"PWD={password}"
    )


def calcular_hash_arquivo(arquivo_path: str) -> str:
    """Calcula hash SHA256 do arquivo"""
    hash_sha256 = hashlib.sha256()
    with open(arquivo_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()


def calcular_hash_row(row: pd.Series) -> str:
    """Calcula hash SHA256 de uma linha"""
    row_string = '|'.join(str(v) for v in row.values)
    return hashlib.sha256(row_string.encode('utf-8')).hexdigest()


def converter_monetario_br(valor) -> float:
    """Converte valor BR (1.234,56) para float"""
    if pd.isna(valor) or valor in ['', ' ', '-', 'nan', '""']:
        return 0.0
    try:
        valor_str = str(valor).strip()
        valor_limpo = valor_str.replace('.', '').replace(',', '.')
        return float(valor_limpo)
    except (ValueError, TypeError):
        return 0.0


def converter_data_br(valor):
    """Converte DD/MM/YYYY para date"""
    if pd.isna(valor) or valor in ['', ' ', 'nan', '-', '""']:
        return None
    try:
        valor_str = str(valor).strip()
        if '/' in valor_str:
            partes = valor_str.split('/')
            if len(partes) == 3:
                dia, mes, ano = int(partes[0]), int(partes[1]), int(partes[2])
                if 1 <= mes <= 12 and 1 <= dia <= 31 and 2020 <= ano <= 2030:
                    return date(ano, mes, dia)
        return None
    except (ValueError, TypeError, IndexError):
        return None


def converter_assessor(valor):
    """Remove prefixo 'A' do codigo assessor"""
    if pd.isna(valor) or valor in ['', ' ', 'nan', '-', '""']:
        return 'M7'
    valor_str = str(valor).strip()
    if valor_str.startswith('A') and len(valor_str) > 1:
        return valor_str[1:]
    return valor_str


def converter_cliente(valor):
    """Converte codigo cliente para int"""
    if pd.isna(valor) or valor in ['', ' ', 'nan', '-', '""']:
        return None
    try:
        valor_str = str(valor).strip()
        if valor_str.endswith('.0'):
            valor_str = valor_str[:-2]
        return int(valor_str) if valor_str.isdigit() else None
    except:
        return None


def calcular_anomes_comissao(anomes_operacao: int) -> int:
    """Calcula anomes_comissao (anomes_operacao + 1 mes)"""
    ano = anomes_operacao // 100
    mes = anomes_operacao % 100
    mes += 1
    if mes > 12:
        mes = 1
        ano += 1
    return ano * 100 + mes


def limpar_texto(valor):
    """Limpa campo de texto"""
    if pd.isna(valor) or valor in ['', '-', ' ', 'nan', 'None', 'NONE', '""']:
        return None
    return str(valor).strip() or None


def verificar_competencia_banco(cursor, anomes_operacao: int) -> dict:
    """
    Verifica se a competencia ja existe no banco

    Returns:
        Dict com dados da competencia ou None se nao existe
    """
    cursor.execute('''
        SELECT
            COUNT(*) AS qtd_registros,
            SUM(receita_bruta) AS receita_bruta,
            SUM(comissao_escritorio) AS comissao_escritorio,
            MIN(data_carga) AS data_carga
        FROM bronze.split_c_receitas_detalhadas
        WHERE anomes_operacao = ?
    ''', (anomes_operacao,))

    row = cursor.fetchone()
    if row and row[0] > 0:
        return {
            'qtd_registros': row[0],
            'receita_bruta': float(row[1] or 0),
            'comissao_escritorio': float(row[2] or 0),
            'data_carga': row[3]
        }
    return None


def extrair_competencia_do_csv(arquivo_path: str) -> int:
    """
    Extrai a competencia (YYYYMM) da coluna filename do CSV.
    Procura pelo padrao _YYYYMM no nome do arquivo de origem.
    """
    df = pd.read_csv(
        arquivo_path,
        sep=';',
        encoding='utf-8-sig',
        dtype=str,
        nrows=100  # Ler apenas primeiras linhas para performance
    )

    if 'filename' not in df.columns:
        raise ValueError("Coluna 'filename' nao encontrada no CSV")

    # Procurar padrao _YYYYMM nos valores da coluna filename
    for valor in df['filename'].dropna().unique():
        match = re.search(r'_(\d{6})\.csv$', str(valor))
        if match:
            anomes = int(match.group(1))
            ano, mes = anomes // 100, anomes % 100
            if 2020 <= ano <= 2030 and 1 <= mes <= 12:
                return anomes

    raise ValueError("Nao foi possivel extrair competencia da coluna 'filename'. Esperado padrao: *_YYYYMM.csv")


def calcular_totais_arquivo(arquivo_path: str) -> dict:
    """Calcula totais do arquivo CSV sem carregar completamente"""
    df = pd.read_csv(
        arquivo_path,
        sep=';',
        encoding='utf-8-sig',
        dtype=str
    )

    receita_bruta = sum(converter_monetario_br(v) for v in df['Receita Bruta'])
    comissao_escritorio = sum(converter_monetario_br(v) for v in df['Comissão Escritório'])

    return {
        'qtd_registros': len(df),
        'receita_bruta': receita_bruta,
        'comissao_escritorio': comissao_escritorio
    }


def exibir_comparacao(banco: dict, arquivo: dict, anomes_operacao: int):
    """Exibe comparacao entre banco e arquivo"""
    print()
    print("=" * 70)
    print(f"COMPETENCIA {anomes_operacao} JA CARREGADA NO BANCO")
    print("=" * 70)
    print()
    print(f"{'Metrica':<25} {'Banco':>20} {'Arquivo':>20}")
    print("-" * 70)
    print(f"{'Registros':<25} {banco['qtd_registros']:>20,} {arquivo['qtd_registros']:>20,}")
    print(f"{'Receita Bruta':<25} R$ {banco['receita_bruta']:>17,.2f} R$ {arquivo['receita_bruta']:>17,.2f}")
    print(f"{'Comissao Escritorio':<25} R$ {banco['comissao_escritorio']:>17,.2f} R$ {arquivo['comissao_escritorio']:>17,.2f}")
    print("-" * 70)

    # Calcular diferencas
    diff_reg = arquivo['qtd_registros'] - banco['qtd_registros']
    diff_bruta = arquivo['receita_bruta'] - banco['receita_bruta']
    diff_comissao = arquivo['comissao_escritorio'] - banco['comissao_escritorio']

    print(f"{'Diferenca':<25} {diff_reg:>20,} R$ {diff_bruta:>17,.2f}")
    print()

    if diff_reg == 0 and abs(diff_bruta) < 0.01 and abs(diff_comissao) < 0.01:
        print(">>> ARQUIVO IDENTICO AO BANCO <<<")
    else:
        print(">>> ARQUIVO DIFERENTE DO BANCO <<<")

    print()
    print("=" * 70)


def processar_split_c(arquivo_path: str, force_reload: bool = False, check_only: bool = False) -> dict:
    """
    Processa arquivo CSV Split C e carrega no banco

    Args:
        arquivo_path: Caminho completo do arquivo CSV
        force_reload: Se True, reprocessa mesmo se ja carregado
        check_only: Se True, apenas verifica se competencia existe (nao carrega)

    Returns:
        Dict com resultado do processamento
    """
    print(f"\n{'='*70}")
    print(f"PROCESSANDO: {os.path.basename(arquivo_path)}")
    print(f"{'='*70}\n")

    # 1. VALIDAR ARQUIVO
    print("1. Validando arquivo...")
    if not os.path.exists(arquivo_path):
        print(f"   ERRO: Arquivo nao encontrado: {arquivo_path}")
        return {'status': 'erro', 'mensagem': f'Arquivo nao encontrado: {arquivo_path}'}

    if not arquivo_path.lower().endswith('.csv'):
        print("   ERRO: Arquivo deve ser .csv")
        return {'status': 'erro', 'mensagem': 'Arquivo deve ser .csv'}

    MIN_FILE_SIZE_KB = 10
    tamanho_kb = os.path.getsize(arquivo_path) / 1024
    if tamanho_kb < MIN_FILE_SIZE_KB:
        print(f"   ERRO: Arquivo muito pequeno: {tamanho_kb:.2f} KB")
        return {'status': 'erro', 'mensagem': f'Arquivo muito pequeno: {tamanho_kb:.2f} KB'}

    with open(arquivo_path, 'r', encoding='utf-8-sig') as f:
        primeira_linha = f.readline()
        if ';' not in primeira_linha:
            print('   ERRO: Delimitador ";" nao encontrado')
            return {'status': 'erro', 'mensagem': 'Delimitador ";" nao encontrado'}

    print(f"   OK: Arquivo valido ({tamanho_kb:.2f} KB)")

    # 2. EXTRAIR COMPETENCIA DOS DADOS DO CSV
    print("2. Extraindo competencia dos dados do CSV...")
    nome_arquivo = os.path.basename(arquivo_path)
    try:
        anomes_operacao = extrair_competencia_do_csv(arquivo_path)
        ano, mes = anomes_operacao // 100, anomes_operacao % 100
        anomes_comissao = calcular_anomes_comissao(anomes_operacao)
        print(f"   OK: anomes_operacao={anomes_operacao}, anomes_comissao={anomes_comissao}")
    except ValueError as e:
        print(f"   ERRO: {e}")
        return {'status': 'erro', 'mensagem': str(e)}

    # 3. CONECTAR AO BANCO
    print("3. Conectando ao banco...")
    try:
        conn_string = get_connection_string()
        conn = pyodbc.connect(conn_string)
        cursor = conn.cursor()
        print("   OK: Conexao estabelecida")
    except Exception as e:
        print(f"   ERRO: Falha na conexao: {e}")
        return {'status': 'erro', 'mensagem': f'Falha na conexao: {e}'}

    # 4. VERIFICAR SE COMPETENCIA JA EXISTE
    print("4. Verificando competencia no banco...")
    dados_banco = verificar_competencia_banco(cursor, anomes_operacao)

    if dados_banco:
        print(f"   ATENCAO: Competencia {anomes_operacao} ja existe no banco!")
        print(f"   Data da carga: {dados_banco['data_carga']}")

        # Calcular totais do arquivo para comparacao
        print("   Calculando totais do arquivo...")
        dados_arquivo = calcular_totais_arquivo(arquivo_path)

        # Exibir comparacao
        exibir_comparacao(dados_banco, dados_arquivo, anomes_operacao)

        if check_only:
            conn.close()
            return {
                'status': 'competencia_existente',
                'anomes_operacao': anomes_operacao,
                'banco': dados_banco,
                'arquivo': dados_arquivo,
                'mensagem': f'Competencia {anomes_operacao} ja carregada. Use --force para recarregar.'
            }

        if not force_reload:
            conn.close()
            return {
                'status': 'competencia_existente',
                'anomes_operacao': anomes_operacao,
                'banco': dados_banco,
                'arquivo': dados_arquivo,
                'mensagem': f'Competencia {anomes_operacao} ja carregada. Use --force para recarregar.'
            }

        # Force reload: deletar competencia
        print(f"\n   Removendo competencia {anomes_operacao} do banco...")
        cursor.execute(
            "DELETE FROM bronze.split_c_receitas_detalhadas WHERE anomes_operacao = ?",
            (anomes_operacao,)
        )
        conn.commit()
        print(f"   OK: {dados_banco['qtd_registros']:,} registros removidos")
    else:
        print(f"   OK: Competencia {anomes_operacao} nao existe no banco (nova carga)")

    # 5. VERIFICAR DUPLICACAO POR HASH
    print("5. Verificando hash do arquivo...")
    hash_arquivo = calcular_hash_arquivo(arquivo_path)

    cursor.execute(
        "SELECT COUNT(*) FROM bronze.split_c_receitas_detalhadas WHERE hash_arquivo = ?",
        (hash_arquivo,)
    )
    ja_processado = cursor.fetchone()[0] > 0

    if ja_processado and not force_reload:
        conn.close()
        print(f"   AVISO: Arquivo ja processado (hash: {hash_arquivo[:16]}...)")
        return {'status': 'duplicado', 'mensagem': f'Arquivo ja processado (hash: {hash_arquivo[:16]}...)'}

    if ja_processado and force_reload:
        print("   Removendo carga anterior por hash...")
        cursor.execute(
            "DELETE FROM bronze.split_c_receitas_detalhadas WHERE hash_arquivo = ?",
            (hash_arquivo,)
        )
        conn.commit()
        print("   OK: Carga anterior removida")
    else:
        print(f"   OK: Arquivo novo (hash: {hash_arquivo[:16]}...)")

    # 6. CARREGAR CSV
    print("6. Carregando CSV...")
    df = pd.read_csv(
        arquivo_path,
        sep=';',
        encoding='utf-8-sig',
        dtype=str
    )
    print(f"   OK: {len(df):,} linhas x {len(df.columns)} colunas")

    # 7. VALIDAR ESTRUTURA
    print("7. Validando estrutura...")
    colunas_obrigatorias = [
        'filename', 'Classificação', 'Categoria', 'Nível 1', 'Nível 2', 'Nível 3', 'Nível 4',
        'Código Cliente', 'Código Assessor', 'Data', 'Receita Bruta', 'Receita Líquida',
        'Comissão % Escritório', 'Comissão Escritório', 'CHAVE_COMISSAO', 'CLASSE DE COMISSÃO'
    ]
    colunas_faltantes = [c for c in colunas_obrigatorias if c not in df.columns]
    if colunas_faltantes:
        conn.close()
        print(f"   ERRO: Colunas faltantes: {colunas_faltantes}")
        return {'status': 'erro', 'mensagem': f'Colunas faltantes: {colunas_faltantes}'}
    print(f"   OK: Estrutura valida ({len(df.columns)} colunas, {len(colunas_obrigatorias)} obrigatorias)")

    # 8. TRANSFORMAR DADOS
    print("8. Transformando dados...")

    # Codigo assessor
    df['Código Assessor'] = df['Código Assessor'].fillna('AM7')
    df['cod_assessor'] = df['Código Assessor'].apply(converter_assessor)

    # Valores monetarios
    df['receita_bruta'] = df['Receita Bruta'].apply(converter_monetario_br)
    df['receita_liquida'] = df['Receita Líquida'].apply(converter_monetario_br)
    df['comissao_percentual_escritorio'] = df['Comissão % Escritório'].apply(converter_monetario_br)
    df['comissao_escritorio'] = df['Comissão Escritório'].apply(converter_monetario_br)

    # Data
    df['data_operacao'] = df['Data'].apply(converter_data_br)

    # Codigo cliente
    df['cod_cliente'] = df['Código Cliente'].apply(converter_cliente)

    # Campos de texto
    df['arquivo_origem_dados'] = df['filename'].apply(limpar_texto)
    df['classificacao'] = df['Classificação'].apply(lambda x: limpar_texto(x).upper() if limpar_texto(x) else None)
    df['categoria'] = df['Categoria'].apply(limpar_texto)
    df['nivel_1'] = df['Nível 1'].apply(limpar_texto)
    df['nivel_2'] = df['Nível 2'].apply(limpar_texto)
    df['nivel_3'] = df['Nível 3'].apply(limpar_texto)
    df['nivel_4'] = df['Nível 4'].apply(limpar_texto)
    df['chave_comissao'] = df['CHAVE_COMISSAO'].apply(limpar_texto)
    df['classe_comissao'] = df['CLASSE DE COMISSÃO'].apply(limpar_texto)

    # Colunas de controle
    df['data_carga'] = date.today()
    df['arquivo_origem'] = nome_arquivo
    df['hash_arquivo'] = hash_arquivo
    df['row_hash'] = df.apply(calcular_hash_row, axis=1)
    df['anomes_operacao'] = anomes_operacao
    df['anomes_comissao'] = anomes_comissao

    print("   OK: Transformacoes aplicadas")

    # 9. INSERIR NO BANCO
    print("9. Inserindo no banco...")

    insert_query = """
        INSERT INTO bronze.split_c_receitas_detalhadas (
            arquivo_origem_dados, classificacao, categoria, nivel_1, nivel_2, nivel_3, nivel_4,
            cod_cliente, cod_assessor, data_operacao, receita_bruta, receita_liquida,
            comissao_percentual_escritorio, comissao_escritorio, chave_comissao, classe_comissao,
            data_carga, arquivo_origem, hash_arquivo, row_hash, anomes_operacao, anomes_comissao
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    def safe_str(val):
        """Converte NaN/None para None, garante str ou None para colunas varchar"""
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return None
        return str(val)

    registros_inseridos = 0
    for idx, row in df.iterrows():
        # Converter numpy types para Python nativos (pyodbc requer tipos nativos)
        valores = (
            safe_str(row['arquivo_origem_dados']),
            safe_str(row['classificacao']),
            safe_str(row['categoria']) or 'N/A',
            safe_str(row['nivel_1']),
            safe_str(row['nivel_2']),
            safe_str(row['nivel_3']),
            safe_str(row['nivel_4']),
            int(row['cod_cliente']) if row['cod_cliente'] is not None and not pd.isna(row['cod_cliente']) else None,
            safe_str(row['cod_assessor']) or 'M7',
            row['data_operacao'] if not (isinstance(row['data_operacao'], float) and pd.isna(row['data_operacao'])) else None,
            float(row['receita_bruta']) if not pd.isna(row['receita_bruta']) else 0.0,
            float(row['receita_liquida']) if not pd.isna(row['receita_liquida']) else 0.0,
            float(row['comissao_percentual_escritorio']) if not pd.isna(row['comissao_percentual_escritorio']) else 0.0,
            float(row['comissao_escritorio']) if not pd.isna(row['comissao_escritorio']) else 0.0,
            safe_str(row['chave_comissao']),
            safe_str(row['classe_comissao']),
            row['data_carga'],
            row['arquivo_origem'],
            row['hash_arquivo'],
            row['row_hash'],
            int(row['anomes_operacao']),
            int(row['anomes_comissao'])
        )
        try:
            cursor.execute(insert_query, valores)
        except Exception as e:
            print(f"\n   ERRO na linha {idx}:")
            nomes = ['arquivo_origem_dados','classificacao','categoria','nivel_1','nivel_2','nivel_3','nivel_4',
                     'cod_cliente','cod_assessor','data_operacao','receita_bruta','receita_liquida',
                     'comissao_pct_esc','comissao_esc','chave_comissao','classe_comissao',
                     'data_carga','arquivo_origem','hash_arquivo','row_hash','anomes_op','anomes_com']
            for i, (n, v) in enumerate(zip(nomes, valores)):
                print(f"     [{i+1:>2}] {n:<25} = {repr(v)} ({type(v).__name__})")
            raise
        registros_inseridos += 1

    conn.commit()
    print(f"   OK: {registros_inseridos:,} registros inseridos")

    # 10. VALIDACAO ARQUIVO vs BANCO
    print("10. Validando arquivo vs banco...")

    cursor.execute("""
        SELECT COUNT(*), SUM(comissao_escritorio)
        FROM bronze.split_c_receitas_detalhadas
        WHERE hash_arquivo = ?
    """, (hash_arquivo,))

    banco = cursor.fetchone()
    conn.close()

    if banco[0] != len(df):
        print(f"   ERRO: Divergencia - arquivo={len(df)}, banco={banco[0]}")
        return {'status': 'erro', 'mensagem': f'Divergencia: arquivo={len(df)}, banco={banco[0]}'}

    print(f"   OK: {banco[0]:,} registros, R$ {banco[1]:,.2f} comissao")

    print(f"\n{'='*70}")
    print("SUCESSO! Arquivo processado com sucesso")
    print(f"{'='*70}\n")

    return {
        'status': 'sucesso',
        'registros': registros_inseridos,
        'comissao_total': float(banco[1]),
        'anomes_operacao': anomes_operacao
    }


def main():
    parser = argparse.ArgumentParser(description='ETL Split C - Receitas Detalhadas')
    parser.add_argument('arquivo', help='Caminho do arquivo CSV')
    parser.add_argument('--force', action='store_true', help='Forcar reprocessamento')
    parser.add_argument('--check-only', action='store_true', help='Apenas verificar se competencia existe')

    args = parser.parse_args()

    resultado = processar_split_c(args.arquivo, args.force, args.check_only)

    if resultado['status'] == 'sucesso':
        sys.exit(0)
    elif resultado['status'] == 'duplicado':
        print(f"\nArquivo duplicado. Use --force para reprocessar.")
        sys.exit(1)
    elif resultado['status'] == 'competencia_existente':
        print(f"\nCompetencia {resultado['anomes_operacao']} ja carregada.")
        print("Opcoes:")
        print("  1. Recarregar: python etl_split_c.py <arquivo> --force")
        print("  2. Apenas validar: execute validar_camadas.py e resumo_competencias.py")
        sys.exit(1)
    else:
        print(f"\nErro: {resultado['mensagem']}")
        sys.exit(2)


if __name__ == '__main__':
    main()
