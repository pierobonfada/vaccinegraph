import os
import sys
import json
import pandas as pd
import duckdb
from src.utils import logger, padroniza_nome_vacina, eprint
from src.downloader import DATA_DIR, RAW_DATA_DIR, check_file_age, download_file

def resolve_city_name(city_arg):
    import json
    import os
    import sys
    import unicodedata
    
    ibge_cache = os.path.join(DATA_DIR, "cidades_ibge.json")
    if not os.path.exists(ibge_cache):
        if city_arg.isdigit() and len(city_arg) == 6:
            return city_arg, f"IBGE:{city_arg}"
        eprint("ERRO: Banco de dados de cidades (IBGE) nao encontrado. Execute com '--update' para baixar as bases.")
        sys.exit(1)
            
    with open(ibge_cache, 'r', encoding='utf-8') as cache_file:
        data = json.load(cache_file)
        
    if city_arg.isdigit() and len(city_arg) == 6:
        for m in data:
            if str(m['id'])[:6] == city_arg:
                return city_arg, f"{m['nome']}-{m['microrregiao']['mesorregiao']['UF']['sigla']}"
        return city_arg, f"IBGE:{city_arg}"
        
    def normalize(s):
        return ''.join(c for c in unicodedata.normalize('NFD', s.lower()) if unicodedata.category(c) != 'Mn')
        
    search_norm = normalize(city_arg)
    for m in data:
        if normalize(m['nome']) == search_norm:
            code_str = str(m['id'])[:6]
            city_display = f"{m['nome']}-{m['microrregiao']['mesorregiao']['UF']['sigla']}"
            eprint(f" > Cidade resolvida: {city_display} -> {code_str}")
            return code_str, city_display
            
    eprint(f"ERRO: Cidade '{city_arg}' nao encontrada na base IBGE.")
    sys.exit(1)

def update_modern_data(year, force_update, states=None, mode='doses', cities=None):
    if year < 2023:
        eprint(f"ERRO: O ano {year} eh invalido. O sistema moderno (SIPNIBD em modo dados abertos) so possui dados a partir de 2023.")
        sys.exit(1)
        
    suffix = "_" + "_".join(states) if states else ""
    if cities: suffix += "_mun_" + "_".join(cities)
    
    filename = "Doses_Residencia.parquet" if mode in ['doses', 'monthly', 'profile'] else "Cobertura_Residencia.parquet"
    DATABASE_FILE = os.path.join(DATA_DIR, f"vaccination_aggregate_{year}_{mode}{suffix}.parquet")
    
    eprint(f"\n[Fase 1] Verificacao de Dados Reais do SI-PNI (SIPNIBD - {year}) - Modo: {mode}")
    url = f"ftp://ftp.datasus.gov.br/dissemin/publicos/Dados_Abertos/SIPNIBD/{filename}"
    dest_path = os.path.join(RAW_DATA_DIR, filename)
    
    updated_any = False
    exists, status = check_file_age(dest_path)
    if not exists:
        if not force_update:
            eprint(f"ERRO: Banco de dados '{filename}' nao encontrado. Execute o programa com '--update' para baixar.")
            sys.exit(1)
        download_file(url, dest_path)
        updated_any = True
    elif status == "Old" and not force_update:
        eprint(f"AVISO: O arquivo '{filename}' nao e atualizado ha mais de 180 dias. Considere rodar com '--update'.")

        
    if updated_any or not os.path.exists(DATABASE_FILE) or force_update:
        eprint(f">> Processando Parquet massivo via DuckDB (Ultra Otimizado/Out-of-Core)...")
        import duckdb
        
        UF_CODES = {'AC': '12', 'AL': '27', 'AM': '13', 'AP': '16', 'BA': '29', 'CE': '23', 'DF': '53', 'ES': '32', 'GO': '52', 'MA': '21', 'MG': '31', 'MS': '50', 'MT': '51', 'PA': '15', 'PB': '25', 'PE': '26', 'PI': '22', 'PR': '41', 'RJ': '33', 'RN': '24', 'RO': '11', 'RR': '14', 'RS': '43', 'SC': '42', 'SE': '28', 'SP': '35', 'TO': '17'}
        
        where_clauses = []
        
        if filename == "Doses_Residencia.parquet":
            where_clauses.append(f"nu_ano = {year}")
            if states:
                state_prefixes = [UF_CODES[uf] for uf in states]
                # SUBSTRING(co_municipio, 1, 2) IN ('43', '42')
                prefixes_str = ", ".join([f"'{p}'" for p in state_prefixes])
                where_clauses.append(f"SUBSTRING(CAST(co_municipio AS VARCHAR), 1, 2) IN ({prefixes_str})")
            if cities:
                cities_str = ", ".join([f"'{c}'" for c in cities])
                where_clauses.append(f"CAST(co_municipio AS VARCHAR) IN ({cities_str})")
                
            where_sql = " AND ".join(where_clauses)
            
            if mode == 'monthly':
                query = f"SELECT ds_imuno, nu_mes, nu_ano, SUM(TRY_CAST(qt_dose AS NUMERIC)) as total_doses FROM read_parquet('{dest_path}') WHERE {where_sql} GROUP BY ds_imuno, nu_mes, nu_ano"
                df = duckdb.query(query).to_df()
                df['vaccine'] = df['ds_imuno'].apply(padroniza_nome_vacina)
                df = df.groupby(['vaccine', 'nu_mes', 'nu_ano'])['total_doses'].sum().reset_index()
                
            elif mode == 'profile':
                query = f"SELECT ds_imuno, co_sexo, co_racacor, nu_idade, SUM(TRY_CAST(qt_dose AS NUMERIC)) as total_doses FROM read_parquet('{dest_path}') WHERE {where_sql} GROUP BY ds_imuno, co_sexo, co_racacor, nu_idade"
                df_ano = duckdb.query(query).to_df()
                
                df_ano['vaccine'] = df_ano['ds_imuno'].apply(padroniza_nome_vacina)
                df_ano['nu_idade'] = pd.to_numeric(df_ano['nu_idade'], errors='coerce')
                
                def get_age_group(age):
                    if pd.isna(age): return 'Sem Informação'
                    if age <= 4: return '0-4 anos'
                    if age <= 11: return '5-11 anos'
                    if age <= 19: return '12-19 anos'
                    if age <= 39: return '20-39 anos'
                    if age <= 59: return '40-59 anos'
                    return '60+ anos'
                    
                df_ano['age_group'] = df_ano['nu_idade'].apply(get_age_group)
                df_ano['co_sexo'] = df_ano['co_sexo'].fillna('SEM INFORMACAO').astype(str)
                df_ano['co_racacor'] = df_ano['co_racacor'].fillna('SEM INFORMACAO').astype(str)
                
                df = df_ano.groupby(['vaccine', 'co_sexo', 'co_racacor', 'age_group'])['total_doses'].sum().reset_index()
                
            else:
                query = f"SELECT ds_imuno, SUM(TRY_CAST(qt_dose AS NUMERIC)) as total_doses FROM read_parquet('{dest_path}') WHERE {where_sql} GROUP BY ds_imuno"
                df = duckdb.query(query).to_df()
                df['vaccine'] = df['ds_imuno'].apply(padroniza_nome_vacina)
                df = df.groupby('vaccine')['total_doses'].sum().reset_index()
                
        else:
            where_clauses.append(f"CO_ANO = '{year}'")
            if states:
                states_str = ", ".join([f"'{s}'" for s in states])
                where_clauses.append(f"CO_UF IN ({states_str})")
            if cities:
                cities_str = ", ".join([f"'{c}'" for c in cities])
                where_clauses.append(f"CAST(CO_MUNICIPIO AS VARCHAR) IN ({cities_str})")
                
            where_sql = " AND ".join(where_clauses)
            
            query = f"SELECT NU_IMUNO, SUM(TRY_CAST(QT_DOSE AS NUMERIC)) as total_doses FROM read_parquet('{dest_path}') WHERE {where_sql} GROUP BY NU_IMUNO"
            df = duckdb.query(query).to_df()
            df['vaccine'] = df['NU_IMUNO'].apply(padroniza_nome_vacina)
            df = df.groupby('vaccine')['total_doses'].sum().reset_index()

        df.to_parquet(DATABASE_FILE, index=False)
        return df
    else:
        eprint(">> Base cacheada ja existe.")
        return pd.read_parquet(DATABASE_FILE)

def apply_filters_and_highlights(stats_df, sort_col, search_terms=None, top_n=None, bottom_n=None, until_terms=None, ascending=False, exclude_terms=None):
    import pandas as pd
    import numpy as np
    stats_df = stats_df.copy()
    
    if exclude_terms:
        exclude_terms = [e.lower() for e in exclude_terms]
        stats_df = stats_df[~stats_df['vaccine'].str.lower().apply(lambda x: any(e in x for e in exclude_terms))]

    stats_df = stats_df.sort_values(by=sort_col, ascending=ascending).reset_index(drop=True)
    
    if until_terms:
        until_terms = [s.lower() for s in until_terms]
        max_idx = -1
        for i, row in stats_df.iterrows():
            if any(s in row['vaccine'].lower() for s in until_terms):
                max_idx = max(max_idx, i)
        if max_idx != -1:
            top_n = max_idx + 1
            # Removido: search_terms = (search_terms or []) + until_terms para não forçar a cor verde
            
    if search_terms:
        search_terms = [s.lower() for s in search_terms]
        def match_search(name):
            return any(s in name.lower() for s in search_terms)
        stats_df['is_searched'] = stats_df['vaccine'].apply(match_search)
    else:
        stats_df['is_searched'] = False
        
    stats_df['color'] = stats_df['is_searched'].map({True: '#2ecc71', False: '#95a5a6'})
    
    # Forcar para o topo apenas se nao for --until
    if search_terms and not until_terms:
        searched_df = stats_df[stats_df['is_searched']]
        unsearched_df = stats_df[~stats_df['is_searched']]
        stats_df = pd.concat([searched_df, unsearched_df]).reset_index(drop=True)
    
    if top_n is not None and bottom_n is not None:
        stats_df = pd.concat([stats_df.head(top_n), stats_df.tail(bottom_n)]).drop_duplicates().reset_index(drop=True)
    elif top_n is not None:
        stats_df = stats_df.head(top_n).reset_index(drop=True)
    elif bottom_n is not None:
        stats_df = stats_df.tail(bottom_n).reset_index(drop=True)
        
    return stats_df

def get_vigimed_data(severity, states=None, start_year=None, end_year=None):
    vigimed_path = os.path.join(RAW_DATA_DIR, "VigiMed_Notificacoes.csv")
    exists, status = check_file_age(vigimed_path)
    if not exists:
        eprint("ERRO: Banco de dados do VigiMed nao encontrado. Execute o programa com '--update' para baixar.")
        sys.exit(1)
    elif status == "Old":
        eprint("AVISO: O arquivo do VigiMed nao e atualizado ha mais de 180 dias. Considere rodar com '--update'.")

        
    import duckdb
    severity_filter = ""
    if severity == 'mild':
        severity_filter = "AND LOWER(GRAVE) NOT LIKE '%sim%'"
    elif severity == 'severe':
        severity_filter = "AND LOWER(GRAVE) LIKE '%sim%' AND LOWER(DESFECHO) NOT LIKE '%óbito%'"
    elif severity == 'death':
        severity_filter = "AND (LOWER(DESFECHO) LIKE '%óbito%' OR LOWER(DESFECHO) LIKE '%obito%' OR LOWER(DESFECHO) LIKE '%fatal%')"
        
    eprint(f">> Processando Notificacoes VigiMed via Pandas (Filtro: {severity})")
    try:
        df_raw = pd.read_csv(vigimed_path, sep=';', encoding='ISO-8859-1', on_bad_lines='skip', low_memory=False)
    except Exception as e:
        eprint(f"ERRO ao ler VigiMed CSV via pandas: {e}")
        sys.exit(1)
        
    if severity == 'mild':
        df_raw = df_raw[~df_raw['GRAVE'].str.contains('Sim', case=False, na=False)]
    elif severity == 'severe':
        df_raw = df_raw[df_raw['GRAVE'].str.contains('Sim', case=False, na=False) & ~df_raw['DESFECHO'].str.contains('óbito|obito|fatal', case=False, na=False)]
    elif severity == 'death':
        df_raw = df_raw[df_raw['DESFECHO'].str.contains('óbito|obito|fatal', case=False, na=False)]
        
    df_raw = df_raw.rename(columns={'NOME_MEDICAMENTO_WHODRUG': 'ds_imuno'})
    df_raw = df_raw.dropna(subset=['ds_imuno'])
    
    # As rows can have multiple drugs (pipe separated), we expand them or apply padroniza loosely
    def loose_padroniza(name):
        if not isinstance(name, str): return 'Outros'
        return padroniza_nome_vacina(name)

    df_raw['vaccine'] = df_raw['ds_imuno'].apply(loose_padroniza)
    df_vigimed = df_raw.groupby('vaccine').size().reset_index(name='total_complications')
    return df_vigimed

