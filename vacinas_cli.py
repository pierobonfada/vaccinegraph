#!/usr/bin/env python3
import ssl
import os
import sys
import argparse
import urllib.request
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import warnings

warnings.filterwarnings('ignore')

DATA_DIR = "data"
RAW_DATA_DIR = os.path.join(DATA_DIR, "raw")
OUTPUT_DIR = "output"


def resolve_city_name(city_arg):
    if city_arg.isdigit() and len(city_arg) == 6:
        return city_arg
        
    import urllib.request
    import json
    import gzip
    import os
    
    ibge_cache = os.path.join(DATA_DIR, "cidades_ibge.json")
    if not os.path.exists(ibge_cache):
        eprint(f"Baixando banco de dados estatico do IBGE pela primeira e unica vez...")
        try:
            req = urllib.request.Request('https://servicodados.ibge.gov.br/api/v1/localidades/municipios', headers={'Accept-Encoding': 'gzip'})
            with urllib.request.urlopen(req) as response:
                if response.info().get('Content-Encoding') == 'gzip':
                    data = json.loads(gzip.decompress(response.read()).decode('utf-8'))
                else:
                    data = json.loads(response.read().decode('utf-8'))
            with open(ibge_cache, 'w', encoding='utf-8') as cache_file:
                json.dump(data, cache_file, ensure_ascii=False)
        except Exception as e:
            eprint(f"ERRO ao baixar banco do IBGE: {e}")
            sys.exit(1)
            
    with open(ibge_cache, 'r', encoding='utf-8') as cache_file:
        data = json.load(cache_file)
        
    import unicodedata
    def normalize(s):
        return ''.join(c for c in unicodedata.normalize('NFD', s.lower()) if unicodedata.category(c) != 'Mn')
        
    search_norm = normalize(city_arg)
    for m in data:
        if normalize(m['nome']) == search_norm:
            code_str = str(m['id'])[:6]
            eprint(f" > Encontrado na base local: {m['nome']} ({m['microrregiao']['mesorregiao']['UF']['sigla']}) -> {code_str}")
            return code_str
            
    eprint(f"ERRO: Cidade '{city_arg}' nao encontrada na base IBGE.")
    sys.exit(1)
def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


import time
def check_file_age(filepath, max_days=180):
    if not os.path.exists(filepath):
        return False, "Missing"
    age_days = (time.time() - os.path.getmtime(filepath)) / (24 * 3600)
    if age_days > max_days:
        return True, "Old"
    return True, "OK"

def download_file(url, dest_path):
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        response = urllib.request.urlopen(url, context=ctx)
        total_size = int(response.headers.get('content-length', 0))
        block_size = 1024 * 1024
        downloaded = 0
        with open(dest_path, 'wb') as file:
            while True:
                data = response.read(block_size)
                if not data:
                    break
                file.write(data)
                downloaded += len(data)
                if total_size > 0:
                    pct = (downloaded / total_size) * 100
                    eprint(f"\rBaixando arquivo {os.path.basename(dest_path)}, {downloaded/(1024*1024):.1f} MB de {total_size/(1024*1024):.1f} MB ({pct:.1f}% completo)   ", end="")
                else:
                    eprint(f"\rBaixando arquivo {os.path.basename(dest_path)}, {downloaded/(1024*1024):.1f} MB baixados   ", end="")
        eprint()
    except Exception as e:
        raise e

def padroniza_nome_vacina(nome):
    nome = str(nome).upper()
    
    # COVID-19 Subtypes
    covid_keywords = ['COVID', 'CORONAVAC', 'ASTRAZENECA', 'PFIZER', 'COMIRNATY', 'JANSSEN', 'BUTANTAN', 'FIOCRUZ', 'COVISHIELD', 'SPIKEVAX', 'MODERNA']
    if any(k in nome for k in covid_keywords):
        if 'PFIZER' in nome or 'COMIRNATY' in nome or 'BIONTECH' in nome:
            return 'COVID-19 (Pfizer)'
        if 'CORONAVAC' in nome or 'SINOVAC' in nome or 'BUTANTAN' in nome:
            return 'COVID-19 (Coronavac)'
        if 'ASTRAZENECA' in nome or 'FIOCRUZ' in nome or 'COVISHIELD' in nome or 'CHADOX' in nome:
            return 'COVID-19 (AstraZeneca)'
        if 'JANSSEN' in nome or 'AD26' in nome:
            return 'COVID-19 (Janssen)'
        if 'MODERNA' in nome or 'SPIKEVAX' in nome:
            return 'COVID-19 (Moderna)'
        if 'INATIVADA' in nome and 'SINOVAC' not in nome and 'BHARAT' not in nome and 'SINOPHARM' not in nome:
            return 'COVID-19 (Coronavac)' 
        if 'RECOMBINANTE' in nome and 'ASTRAZENECA' not in nome and 'JANSSEN' not in nome and 'GAMALEYA' not in nome:
            return 'COVID-19 (AstraZeneca)' 
        return 'COVID-19 (Outras/Genérica)'
        
    if 'DENGUE' in nome or 'QDENGA' in nome or 'DENGVAXIA' in nome:
        if 'QDENGA' in nome:
            return 'Dengue (Qdenga/Atenuada)'
        if 'DENGVAXIA' in nome or ('RECOMBINANTE' in nome and 'ATENUADA' in nome):
            return 'Dengue (Dengvaxia/Recombinante)'
        if 'ATENUADA' in nome and 'RECOMBINANTE' not in nome:
            return 'Dengue (Qdenga/Atenuada)'
        return 'Dengue (Outras/Genérica)'
        
    if 'INFLUENZA' in nome and 'HAEMOPHILUS' not in nome:
        if 'TETRAVALENTE' in nome or 'QUADRIVALENT' in nome or 'TETRA' in nome:
            return 'Influenza (Tetravalente)'
        if 'TRIVALENTE' in nome or 'TRIVALENT' in nome or 'SPLIT 3V' in nome:
            return 'Influenza (Trivalente)'
        return 'Influenza (Outras/Genérica)'
        
    if 'HAEMOPHILUS' in nome: return 'Haemophilus influenzae b (Hib)'
    if 'POLIO' in nome and 'ORAL' in nome: return 'Poliomielite Oral (VOP)'
    if 'VOP' in nome: return 'Poliomielite Oral (VOP)'
    if 'POLIO' in nome: return 'Poliomielite Inativada (VIP)'
    if 'VIP' in nome: return 'Poliomielite Inativada (VIP)'
    if 'HEPATITE B' in nome: return 'Hepatite B'
    if 'HEPATITE A' in nome: return 'Hepatite A'
    if 'FEBRE AMARELA' in nome: return 'Febre Amarela'
    if 'RAIVA' in nome: return 'Raiva'
    if 'VARICELA' in nome: return 'Varicela'
    if 'PENTA' in nome: return 'Pentavalente (DTP-HB-Hib)'
    if 'TRÍPLICE VIRAL' in nome or 'SARAMPO' in nome: return 'Tríplice Viral (SCR)'
    if 'PNEUMO' in nome: return 'Pneumocócica'
    if 'MENING' in nome: return 'Meningocócica'
    if 'BCG' in nome: return 'BCG'
    if 'ROTAV' in nome: return 'Vacina Rotavírus'
    if 'HPV' in nome: return 'HPV'
    if 'DTP' in nome and 'PENTA' not in nome: return 'DTP (Tríplice Bacteriana)'
    
    return nome.title()


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

def apply_filters_and_highlights(stats_df, sort_col, search_terms=None, top_n=None, bottom_n=None, until_terms=None, ascending=False):
    import pandas as pd
    import numpy as np
    stats_df = stats_df.copy()
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

def annotate_bars(ax, show_pct=False, total=None):
    for p in ax.patches:
        height = p.get_height()
        if height > 0:
            val_str = f'{int(height):,}'.replace(',', '.')
            if show_pct and total and total > 0:
                pct = (height / total) * 100
                val_str = f'{val_str} ({pct:.1f}%)'
            ax.annotate(val_str, 
                        (p.get_x() + p.get_width() / 2., height),
                        ha='center', va='bottom', rotation=90, color='black', fontweight='bold', fontsize=10, xytext=(0, 5), textcoords='offset points')
    ylim = ax.get_ylim()
    ax.set_ylim(ylim[0], ylim[1] * 1.3)

def format_millions(x, pos):
    if x >= 1e6:
        return f'{x*1e-6:g} Milhões'
    elif x >= 1e3:
        return f'{x*1e-3:g} Mil'
    return f'{x:g}'


def generate_infographic(res, total_doses, output_file=None):
    if not res:
        eprint("Nenhuma notificacao encontrada para esta vacina.")
        sys.exit(1)
        
    fig = plt.figure(figsize=(16, 10))
    fig.patch.set_facecolor('#f4f6f9')

    plt.suptitle(f"INFOGRÁFICO DE SEGURANÇA: {res['vaccine_name'].upper()}", fontsize=22, fontweight='black', color='#2c3e50', y=0.96)
    
    total_comps = sum(res['counts'].values())
    pct = (total_comps / total_doses * 100) if total_doses > 0 else 0
    doses_str = f'{int(total_doses):,}'.replace(',', '.')
    comps_str = f'{int(total_comps):,}'.replace(',', '.')
    
    fig.text(0.5, 0.91, f"Total de Doses Aplicadas (SI-PNI): {doses_str} | Notificações VigiMed: {comps_str} ({pct:.6f}%)", ha='center', fontsize=14, color='#7f8c8d')


    if res.get('total_obitos', 0) > 0:
        obito_msg = f"⚠ Esta vacina teve {res['total_obitos']} casos reportados que evoluíram para óbito."
        obito_color = '#c0392b'
    else:
        obito_msg = "✅ Esta vacina não teve NENHUM caso reportado de óbito neste período."
        obito_color = '#27ae60'
        
    fig.text(0.5, 0.02, obito_msg, ha='center', va='bottom', fontsize=12, color=obito_color, fontweight='bold', bbox=dict(facecolor='#ffffff', edgecolor=obito_color, boxstyle='round,pad=0.5'))
    
    gs = fig.add_gridspec(2, 3, wspace=0.3, hspace=0.4, bottom=0.08)


    # 1. Donut chart (Simples vs Graves)
    ax_donut = fig.add_subplot(gs[:, 0])
    labels = ['Simples', 'Graves (incl. Óbitos)']
    sizes = [res['counts']['Simples'], res['counts']['Graves (incl. Óbitos)']]
    colors = ['#3498db', '#e67e22']
    explode = (0.05, 0.05)

    l_f = [labels[i] for i in range(2) if sizes[i] > 0]
    s_f = [sizes[i] for i in range(2) if sizes[i] > 0]
    c_f = [colors[i] for i in range(2) if sizes[i] > 0]
    e_f = [explode[i] for i in range(2) if sizes[i] > 0]

    if s_f:
        wedges, texts, autotexts = ax_donut.pie(s_f, explode=e_f, labels=l_f, colors=c_f, autopct='%1.1f%%', shadow=False, startangle=140, textprops=dict(color="w", weight="bold"))
        ax_donut.legend(wedges, l_f, title="Gravidade", loc="lower center", bbox_to_anchor=(0.5, -0.1))
        plt.setp(autotexts, size=11, weight="bold", color="black")
        centre_circle = plt.Circle((0,0),0.65,fc='#f4f6f9')
        ax_donut.add_artist(centre_circle)
    ax_donut.set_title('Proporção de Notificações', fontweight='bold', fontsize=14, color='#34495e')

    def plot_barh(ax, data, color, title):
        if not data:
            ax.text(0.5, 0.5, "Sem Dados", ha='center', va='center', color='#95a5a6')
            ax.axis('off')
            ax.set_title(title, fontweight='bold', color=color)
            return
        
        y_pos = np.arange(len(data))
        values = list(data.values())
        keys = list(data.keys())
        # Wrap long labels
        import textwrap
        keys = ['\n'.join(textwrap.wrap(k, width=30)) for k in keys]
        
        ax.barh(y_pos, values, color=color)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(keys, fontsize=9)
        ax.invert_yaxis()
        ax.set_title(title, fontweight='bold', color=color)
        for i, v in enumerate(values):
            ax.text(v, i, f' {v}', va='center', fontsize=9, fontweight='bold')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_visible(False)
        ax.set_xticks([])

    # Middle Col: Reactions
    ax_sim = fig.add_subplot(gs[0, 1])
    plot_barh(ax_sim, res['top_simple'], '#2980b9', 'Top 10 Complicações SIMPLES')
    
    ax_sev = fig.add_subplot(gs[1, 1])
    plot_barh(ax_sev, res['top_severe'], '#d35400', 'Top 10 Complicações GRAVES (incl. Óbitos)')

    # Right Col: Demographics
    ax_dem_sex = fig.add_subplot(gs[0, 2])
    if res['demographics']['sex']:
        keys = list(res['demographics']['sex'].keys())
        values = list(res['demographics']['sex'].values())
        colors = ['#9b59b6' if k.lower()=='feminino' else '#34495e' if k.lower()=='masculino' else '#95a5a6' for k in keys]
        ax_dem_sex.bar(keys, values, color=colors)
        ax_dem_sex.set_title('Distribuição por Sexo', fontweight='bold', color='#8e44ad')
        ax_dem_sex.spines['top'].set_visible(False)
        ax_dem_sex.spines['right'].set_visible(False)
    else:
        ax_dem_sex.axis('off')
        
    ax_dem_age = fig.add_subplot(gs[1, 2])
    plot_barh(ax_dem_age, res['demographics']['age'], '#16a085', 'Faixa Etária (VigiMed)')

    plt.tight_layout(rect=[0, 0.06, 1, 0.88])
    handle_output(fig, output_file)

def handle_output(fig, output_file):
    use_pipe = '--pipe' in sys.argv
    if use_pipe:
        import io
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=300, bbox_inches='tight')
        sys.stdout.buffer.write(buf.getvalue())
    else:
        if not output_file:
            import datetime
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"grafico_{ts}.png"
        out_path = os.path.join(OUTPUT_DIR, os.path.basename(output_file)) if not os.path.isabs(output_file) else output_file
        fig.savefig(out_path, dpi=300, bbox_inches='tight')
        eprint(f">> Grafico salvo em: {out_path}")

def generate_doses_chart(df, year, output_file=None, search_terms=None, top_n=None, bottom_n=None):
    df_doses = apply_filters_and_highlights(df, sort_col='total_doses', search_terms=search_terms, top_n=top_n, bottom_n=bottom_n)
    
    fig, ax1 = plt.subplots(figsize=(10, 8))
    ax1.bar(df_doses['vaccine'], df_doses['total_doses'], color=df_doses['color'])
    ax1.set_title(f'Total de Doses Aplicadas ({year})', fontsize=14, pad=20)
    ax1.set_ylabel('Total de Doses Aplicadas', fontsize=12)
    ax1.tick_params(axis='x', rotation=90)
    ax1.yaxis.set_major_formatter(FuncFormatter(format_millions))
    annotate_bars(ax1)
    handle_output(fig, output_file)

def generate_people_chart(df, year, output_file=None, search_terms=None, top_n=None, bottom_n=None):
    df_people = apply_filters_and_highlights(df, sort_col='total_doses', search_terms=search_terms, top_n=top_n, bottom_n=bottom_n)
    
    fig, ax2 = plt.subplots(figsize=(10, 8))
    ax2.bar(df_people['vaccine'], df_people['total_doses'], color=df_people['color'])
    
    ax2.set_title(f'Pessoas (Esquema Completo) ({year})', fontsize=14, pad=20)
    ax2.set_ylabel('Total de Pessoas (Esquemas Finalizados)', fontsize=12)
        
    ax2.tick_params(axis='x', rotation=90)
    ax2.yaxis.set_major_formatter(FuncFormatter(format_millions))
    annotate_bars(ax2)
    handle_output(fig, output_file)

def generate_timeline_chart(timeline_data, output_file=None):
    import numpy as np
    years = sorted(list(timeline_data.keys()))
    doses = [timeline_data[y]['doses'] for y in years]
    schemas = [timeline_data[y]['schemas'] for y in years]
    
    x = np.arange(len(years))
    width = 0.35
    
    fig, ax = plt.subplots(figsize=(12, 8))
    rects1 = ax.bar(x - width/2, doses, width, label='Doses Aplicadas', color='#3498db')
    rects2 = ax.bar(x + width/2, schemas, width, label='Esquema Completo (Cobertura)', color='#e74c3c')
    
    ax.set_title('Evolução: Doses Totais Aplicadas vs Esquemas Vacinais Completos', fontsize=14, pad=20)
    ax.set_ylabel('Volume Absoluto', fontsize=12)
    ax.set_xticks(x)
    ax.set_xticklabels(years)
    ax.legend()
    ax.yaxis.set_major_formatter(FuncFormatter(format_millions))
    annotate_bars(ax)
    handle_output(fig, output_file)




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

def generate_complications_chart(df, title, output_file=None, anomaly_msg=""):
    if df.empty:
        eprint("ERRO: Nenhum dado de complicacao para plotar.")
        sys.exit(1)
        
    fig, ax = plt.subplots(figsize=(15, 8))
    fig.patch.set_facecolor('#f8f9fa')
    ax.set_facecolor('#ffffff')
    
    x = range(len(df['vaccine']))
    
    color_doses = df.get('color', '#bdc3c7')
    color_doses = df.get('color', '#bdc3c7')
    bars_doses = ax.bar(x, df['total_doses'], width=0.8, color=color_doses, edgecolor='#95a5a6', label='Doses Aplicadas')
    bars_comps = ax.bar(x, df['total_complications'], width=0.4, color='#e74c3c', label='Complicações (VigiMed)')
    
    ax.set_yscale('log')
    ax.set_ylabel('Quantidade (Escala Logarítmica)', fontsize=12, fontweight='bold', color='#2c3e50')
    ax.yaxis.set_major_formatter(FuncFormatter(format_millions))
    
    ax.set_xticks(x)
    ax.set_xticklabels(df['vaccine'], rotation=40, ha='right', fontsize=11, fontweight='bold')
    
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    
    for i, (dose, comp, pct) in enumerate(zip(df['total_doses'], df['total_complications'], df['pct_complications'])):
        dose_str = f'{int(dose):,}'.replace(',', '.')
        comp_str = f'{int(comp):,}'.replace(',', '.')
        
        color_text = '#27ae60' if df.get('is_searched', __import__('pandas').Series([False]*len(df))).iloc[i] else '#7f8c8d'
        color_text = '#27ae60' if df.get('is_searched', pd.Series([False]*len(df))).iloc[i] else '#7f8c8d'
        ax.annotate(f'{dose_str}\nDoses', (i, dose), ha='center', va='bottom', fontsize=9, color=color_text, xytext=(0, 3), textcoords='offset points')
        ax.annotate(f'{comp_str}\nCasos\n({pct:.4f}%)', (i, comp), ha='center', va='bottom', fontsize=10, fontweight='bold', color='#c0392b', xytext=(0, 3), textcoords='offset points')
        
    ylim = ax.get_ylim()
    ax.set_ylim(ylim[0], ylim[1] * 3.5)
    
    fig.legend(loc='upper center', bbox_to_anchor=(0.5, 0.90), ncol=2, frameon=False, fontsize=12)
    
    plt.suptitle(title, fontsize=16, fontweight='black', color='#2c3e50', y=0.98)
    ax.set_title("O eixo Y está em escala logarítmica para evidenciar a grande diferença entre doses e casos", fontsize=10, color='#7f8c8d', style='italic', pad=30)
    
    
    if anomaly_msg:
        fig.text(0.5, 0.02, anomaly_msg, ha='center', va='bottom', fontsize=9, color='#c0392b', fontweight='bold', style='italic', bbox=dict(facecolor='#f8d7da', edgecolor='#f5c6cb', boxstyle='round,pad=0.5', alpha=0.8))
        plt.tight_layout(rect=[0, 0.05, 1, 0.88])
    else:
        plt.tight_layout(rect=[0, 0.06, 1, 0.88])
        
    handle_output(fig, output_file)
def generate_profile_chart(df, title, output_file=None):
    if df.empty:
        eprint("ERRO: Nenhum dado para plotar perfil.")
        sys.exit(1)
        
    fig, axes = plt.subplots(2, 2, figsize=(14, 12))
    fig.suptitle(title, fontsize=18, fontweight='bold', y=0.98)
    
    # 1. Sexo
    ax1 = axes[0, 0]
    df_sexo = df.groupby('co_sexo')['total_doses'].sum().sort_values(ascending=False)
    
    def make_autopct(values):
        def my_autopct(pct):
            total = sum(values)
            val = int(round(pct*total/100.0))
            val_str = f'{val:,}'.replace(',', '.')
            return f'{pct:.1f}%\n({val_str})'
        return my_autopct
        
    ax1.pie(df_sexo.values, labels=df_sexo.index, autopct=make_autopct(df_sexo.values), startangle=90, colors=['#3498db', '#e74c3c', '#95a5a6'], textprops={'color':'black', 'weight':'bold'})
    ax1.set_title("Distribuição por Sexo", fontsize=14)
    
    # 2. Raça/Cor
    ax2 = axes[0, 1]
    df_raca = df.groupby('co_racacor')['total_doses'].sum().sort_values(ascending=True)
    ax2.barh(df_raca.index, df_raca.values, color='#9b59b6')
    ax2.set_title("Distribuição por Raça/Cor", fontsize=14)
    ax2.xaxis.set_major_formatter(FuncFormatter(format_millions))
    
    for p in ax2.patches:
        width = p.get_width()
        if width > 0:
            val_str = f'{int(width):,}'.replace(',', '.')
            ax2.annotate(val_str,
                         (width, p.get_y() + p.get_height() / 2.),
                         ha='left', va='center', color='black', fontweight='bold', fontsize=10, xytext=(5, 0), textcoords='offset points')
    xlim = ax2.get_xlim()
    ax2.set_xlim(xlim[0], xlim[1] * 1.3)
    
    # 3. Faixa Etária
    ax3 = plt.subplot(2, 1, 2)
    age_order = ['0-4 anos', '5-11 anos', '12-19 anos', '20-39 anos', '40-59 anos', '60+ anos', 'Sem Informação']
    df_idade = df.groupby('age_group')['total_doses'].sum().reindex(age_order).fillna(0)
    
    bars = ax3.bar(df_idade.index, df_idade.values, color='#f1c40f')
    ax3.set_title("Distribuição por Faixa Etária", fontsize=14)
    ax3.yaxis.set_major_formatter(FuncFormatter(format_millions))
    annotate_bars(ax3, show_pct=True, total=df_idade.sum())
    
    # Hide axes[1,0] and axes[1,1] because we used a big subplot for age
    axes[1,0].remove()
    axes[1,1].remove()
    
    handle_output(fig, output_file)

def generate_monthly_chart(df, title, output_file=None):
    if df.empty:
        eprint("ERRO: Nenhum dado para plotar.")
        sys.exit(1)
        
    df['periodo'] = df['nu_ano'].astype(str) + '-' + df['nu_mes'].astype(str).str.zfill(2)
    df = df.sort_values('periodo')
    
    # Pivot so each vaccine is a column
    pivot = df.pivot(index='periodo', columns='vaccine', values='total_doses').fillna(0)
    
    fig, ax = plt.subplots(figsize=(14, 7))
    
    # Plot each line
    for col in pivot.columns:
        ax.plot(pivot.index, pivot[col], marker='o', linewidth=2, label=col)
        
    ax.set_title(title, fontsize=16, pad=20)
    ax.set_ylabel('Total Absoluto de Vacinas Aplicadas', fontsize=12)
    ax.set_xlabel('Período (Ano-Mês)', fontsize=12)
    ax.tick_params(axis='x', rotation=45)
    ax.yaxis.set_major_formatter(FuncFormatter(format_millions))
    ax.grid(True, linestyle='--', alpha=0.6)
    
    # Put legend outside if too many
    ax.legend(title='Vacina', bbox_to_anchor=(1.05, 1), loc='upper left')
    
    handle_output(fig, output_file)

def generate_total_yearly_chart(yearly_data, output_file=None, title="Total de Doses Aplicadas por Ano"):
    import numpy as np
    years = sorted(list(yearly_data.keys()))
    totals = [yearly_data[y] for y in years]
    
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(years, totals, color='#8e44ad')
    
    ax.set_title(title, fontsize=14, pad=20)
    ax.set_ylabel('Total Absoluto de Vacinas', fontsize=12)
    ax.set_xticks(years)
    ax.yaxis.set_major_formatter(FuncFormatter(format_millions))
    annotate_bars(ax)
    handle_output(fig, output_file)

def main():
    parser = argparse.ArgumentParser(
        description="VaccineGraph - Sistema Analítico de Vacinação (SI-PNI + VigiMed)\
"
                    "Cruza dados abertos de vacinação com notificações de eventos adversos.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    parser.add_argument('--chart', type=str, choices=['doses', 'people', 'timeline', 'total_yearly', 'monthly', 'profile', 'complications', 'infographic'], default='doses', 
                        help="Define qual gráfico gerar:\
"
                             " - doses: Vacinas mais aplicadas (Total de Doses)\
"
                             " - people: Vacinas mais aplicadas (Total de Pessoas)\
"
                             " - timeline: Série histórica por vacina ao longo dos anos\
"
                             " - total_yearly: Total de doses aplicadas ano a ano\
"
                             " - monthly: Série histórica mensal detalhada\
"
                             " - profile: Perfil demográfico (idade, sexo, raça) dos vacinados\
"
                             " - complications: Taxa de complicações (SI-PNI vs VigiMed)\
"
                             " - infographic: Infográfico completo de complicações para UMA vacina específica (use --search)")
                             
    parser.add_argument('--start-year', type=int, default=2023, help="Ano inicial da análise (Mínimo: 2023).")
    import datetime
    current_year = datetime.date.today().year
    parser.add_argument('--end-year', type=int, default=current_year, help="Ano final da análise (padrão: ano atual).")
    parser.add_argument('--state', type=str, nargs='+', help="Filtrar por Sigla(s) do Estado (Ex: RS SP).")
    parser.add_argument('--city', type=str, nargs='+', help="Filtrar por Nome da Cidade (ex: Veranópolis) ou Código IBGE (6 dígitos).")
    
    parser.add_argument('--top', type=int, help="Limita o gráfico para exibir apenas as N vacinas no topo do ranking.")
    parser.add_argument('--bottom', type=int, help="Exibe as N vacinas na base do ranking.")
    
    parser.add_argument('--search', type=str, nargs='+', help="Busca vacinas específicas por nome (Ex: HPV Influenza). Em infographic, define o alvo principal.")
    parser.add_argument('--until', type=str, nargs='+', help="Busca dinâmica: lista o ranking progressivamente até encontrar a vacina desejada.")
    
    parser.add_argument('--severity', type=str, choices=['simple', 'severe', 'death', 'all'], default='severe', help="Filtra a gravidade das complicações no VigiMed (padrão: severe).")
    parser.add_argument('--sort', type=str, choices=['most_doses', 'most_complications', 'least_complications'], default='most_complications', help="Ordenação do gráfico de complicações.")
    
    parser.add_argument('-o', '--output', type=str, help="Salva a imagem no caminho especificado ao invés de abrir uma janela interativa.")
    parser.add_argument('--update', action='store_true', help="Força o download de novos dados governamentais (ignora cache local).")
    parser.add_argument('--clear-cache', action='store_true', help="Limpa bases cacheadas locais do DuckDB/Parquet.")
    parser.add_argument('--list-vaccines', action='store_true', help="Lista o nome exato padronizado de todas as vacinas disponíveis para pesquisa.")

    parser.add_argument('--pipe', action='store_true', help="Força a saída da imagem em binário (PNG) direto para o stdout, ideal para pipes.")
    
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)
        
    args = parser.parse_args()

    if args.start_year > args.end_year:
        parser.error("O --start-year nao pode ser maior que o --end-year.")
    if args.start_year < 2023:
        parser.error("O sistema moderno SIPNIBD (Dados Abertos) so possui registros a partir de 2023. Ajuste o --start-year.")
    if args.end_year > current_year:
        parser.error(f"O --end-year ({args.end_year}) nao pode estar no futuro (ano atual: {current_year}).")
        
    if args.chart == 'infographic' and (not args.search or len(args.search) > 1):
        parser.error("O grafico 'infographic' requer exatamente UMA vacina definida em --search. Para comparar varias, use --chart complications.")
        
    if args.city:
        args.city = [resolve_city_name(c) for c in args.city]
        
    if not args.update and (args.search or args.until):
        import duckdb
        db_path = os.path.join(RAW_DATA_DIR, "Doses_Residencia.parquet")
        if os.path.exists(db_path):
            query = "SELECT DISTINCT ds_imuno FROM read_parquet('data/raw/Doses_Residencia.parquet')"
            try:
                df_vac = duckdb.query(query).to_df()
                vacinas = sorted(list(set(df_vac['ds_imuno'].apply(padroniza_nome_vacina))))
                
                def check_terms(terms, arg_name):
                    if not terms: return
                    for term in terms:
                        term_lower = term.lower()
                        if not any(term_lower in v.lower() for v in vacinas):
                            parser.error(f"O termo '{term}' passado em {arg_name} nao corresponde a NENHUMA vacina no banco de dados.\nUse --list-vaccines para ver as opcoes disponiveis.")
                
                check_terms(args.search, '--search')
                check_terms(args.until, '--until')
            except Exception as e:
                pass # Ignora erros de validacao se o banco estiver corrompido

    


    if args.update:
        eprint("\n[Atualizacao Global] Baixando bancos de dados em paralelo...")
        import concurrent.futures
        
        urls_dests = [
            ("ftp://ftp.datasus.gov.br/dissemin/publicos/Dados_Abertos/SIPNIBD/Doses_Residencia.parquet", os.path.join(RAW_DATA_DIR, "Doses_Residencia.parquet")),
            ("ftp://ftp.datasus.gov.br/dissemin/publicos/Dados_Abertos/SIPNIBD/Cobertura_Residencia.parquet", os.path.join(RAW_DATA_DIR, "Cobertura_Residencia.parquet")),
            ("https://dados.anvisa.gov.br/dados/VigiMed_Notificacoes.csv", os.path.join(RAW_DATA_DIR, "VigiMed_Notificacoes.csv"))
        ]
        
        def download_task(item):
            url, dest = item
            eprint(f" Iniciando download: {os.path.basename(dest)}")
            download_file(url, dest)
            eprint(f" Concluido: {os.path.basename(dest)}")
            return True
            
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            executor.map(download_task, urls_dests)
            
        eprint("Todos os bancos foram atualizados com sucesso!\n")
        
        if len(sys.argv) == 2:
            sys.exit(0)

    if args.list_vaccines:
        db_path = os.path.join(RAW_DATA_DIR, "Doses_Residencia.parquet")
        if not os.path.exists(db_path):
            eprint("ERRO: Banco de dados nao encontrado. Execute com '--update' para baixar.")
            sys.exit(1)
        query = f"SELECT DISTINCT ds_imuno FROM read_parquet('{db_path}')"
        import duckdb
        df = duckdb.query(query).to_df()
        vacinas = sorted(list(set(df['ds_imuno'].apply(padroniza_nome_vacina))))
        print("\n=== Vacinas Disponíveis para Busca ===")
        for v in vacinas:
            print(f" - {v}")
        print("======================================\n")
        sys.exit(0)

    if args.clear_cache:
        eprint(">> Limpando o cache e deletando gigabytes de dados...")
        import shutil
        if os.path.exists(DATA_DIR): shutil.rmtree(DATA_DIR)
        eprint(">> Cache limpo com sucesso!")
        return

    if not os.path.exists(RAW_DATA_DIR): os.makedirs(RAW_DATA_DIR)
    if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)

    start = args.start_year if args.start_year else (args.year if args.year else 2024)
    end = args.end_year if args.end_year else (args.year if args.year else 2024)
    
    if start < 2023:
        eprint("ERRO: O periodo inicial eh anterior a 2023. O sistema so possui dados brutos a partir de 2023.")
        sys.exit(1)
    
    if args.chart == 'timeline':
        timeline_data = {}
        for y in range(start, end + 1):
            df_doses = update_modern_data(y, args.update, states=args.state, cities=args.city, mode='doses')
            if args.search:
                df_doses = apply_filters_and_highlights(df_doses, 'total_doses', search_terms=args.search)
                df_doses = df_doses[df_doses['is_searched']]
            total_doses = df_doses['total_doses'].sum() if not df_doses.empty else 0
            
            df_cob = update_modern_data(y, args.update, states=args.state, cities=args.city, mode='cobertura')
            if args.search:
                df_cob = apply_filters_and_highlights(df_cob, 'total_doses', search_terms=args.search)
                df_cob = df_cob[df_cob['is_searched']]
            total_schemas = df_cob['total_doses'].sum() if not df_cob.empty else 0
            
            timeline_data[y] = {'doses': total_doses, 'schemas': total_schemas}
            
        generate_timeline_chart(timeline_data, output_file=args.output)
        
    elif args.chart == 'total_yearly':
        yearly_data = {}
        for y in range(start, end + 1):
            df_doses = update_modern_data(y, args.update, states=args.state, cities=args.city, mode='doses')
            if args.search:
                df_doses = apply_filters_and_highlights(df_doses, 'total_doses', search_terms=args.search)
                df_doses = df_doses[df_doses['is_searched']]
            yearly_data[y] = df_doses['total_doses'].sum() if not df_doses.empty else 0
        
        title = "Total Absoluto de Vacinas Aplicadas por Ano"
        if args.state: title += f" ({' '.join(args.state)})"
        if args.city: title += f" (Municípios: {','.join(args.city)})"
        generate_total_yearly_chart(yearly_data, output_file=args.output, title=title)
        
    elif args.chart == 'monthly':
        all_dfs = []
        for y in range(start, end + 1):
            df_y = update_modern_data(y, args.update, states=args.state, cities=args.city, mode='monthly')
            if not df_y.empty:
                all_dfs.append(df_y)
        if all_dfs:
            df = pd.concat(all_dfs)
            if args.search:
                search_terms = [s.lower() for s in args.search]
                df = df[df['vaccine'].str.lower().apply(lambda x: any(s in x for s in search_terms))]
            if args.top and not args.search:
                top_vaccines = df.groupby('vaccine')['total_doses'].sum().nlargest(args.top).index
                df = df[df['vaccine'].isin(top_vaccines)]
        else:
            df = pd.DataFrame(columns=['vaccine', 'nu_mes', 'nu_ano', 'total_doses'])
            
        title = f"Série Temporal de Vacinação (Mês a Mês)"
        if args.search: title += f"\n[{', '.join(args.search)}]"
        if args.state: title += f" ({' '.join(args.state)})"
        if args.city: title += f" (Mun: {','.join(args.city)})"
        
        generate_monthly_chart(df, title, output_file=args.output)
    elif args.chart == 'profile':
        all_dfs = []
        for y in range(start, end + 1):
            df_y = update_modern_data(y, args.update, states=args.state, cities=args.city, mode='profile')
            if not df_y.empty:
                all_dfs.append(df_y)
        if all_dfs:
            df = pd.concat(all_dfs)
            if args.search:
                search_terms = [s.lower() for s in args.search]
                df = df[df['vaccine'].str.lower().apply(lambda x: any(s in x for s in search_terms))]
            if args.top and not args.search:
                top_vaccines = df.groupby('vaccine')['total_doses'].sum().nlargest(args.top).index
                df = df[df['vaccine'].isin(top_vaccines)]
        else:
            df = pd.DataFrame(columns=['vaccine', 'co_sexo', 'co_racacor', 'age_group', 'total_doses'])
            
        title = f"Perfil Demográfico da População Vacinada"
        if args.search: title += f"\n[{', '.join(args.search)}]"
        if args.state: title += f" ({' '.join(args.state)})"
        if args.city: title += f" (Mun: {','.join(args.city)})"
        
        generate_profile_chart(df, title, output_file=args.output)
    elif args.chart == 'complications':
        all_dfs = []
        for y in range(start, end + 1):
            df_y = update_modern_data(y, args.update, states=args.state, cities=args.city, mode='doses')
            if not df_y.empty:
                all_dfs.append(df_y)
                
        if not all_dfs:
            eprint("Sem dados de doses para o periodo.")
            sys.exit(1)
            
        df_doses = pd.concat(all_dfs).groupby('vaccine')['total_doses'].sum().reset_index()
        
        # Merge with VigiMed
        df_vigimed = get_vigimed_data(args.severity, states=args.state, start_year=start, end_year=end)
        df_merged = pd.merge(df_doses, df_vigimed, on='vaccine', how='inner')
        
        if df_merged.empty:
            eprint("Nenhuma vacina em comum entre a base de doses e as notificacoes do VigiMed (apos filtros).")
            sys.exit(1)
            
        # Calculate percentage
        df_merged['pct_complications'] = (df_merged['total_complications'] / df_merged['total_doses']) * 100
        
        # Filtro de anomalia (mais de 100% de complicacao)
        anomalies = df_merged[df_merged['pct_complications'] > 100]
        df_merged = df_merged[df_merged['pct_complications'] <= 100].reset_index(drop=True)
        
        anomaly_texts = []
        for _, row in anomalies.iterrows():
            v = row['vaccine']
            c = int(row['total_complications'])
            d = int(row['total_doses'])
            anomaly_texts.append(f"{v} ({c} casos p/ {d} doses)")
            
        anomaly_msg = ""
        if anomaly_texts:
            anomaly_msg = "OBSERVAÇÃO: " + ", ".join(anomaly_texts) + " indicam perda de dados no SIPNI (taxa > 100%) e foram ocultadas."

        sort_col_map = {
            'most_complications': 'pct_complications',
            'least_complications': 'pct_complications',
            'most_doses': 'total_doses'
        }
        sort_col = sort_col_map.get(args.sort, 'pct_complications')
        ascending = True if args.sort == 'least_complications' else False
        df_merged = apply_filters_and_highlights(df_merged, sort_col, search_terms=args.search, top_n=args.top, bottom_n=args.bottom, until_terms=args.until, ascending=ascending)
        state_str = f" (UF: {' '.join(args.state)})" if args.state else " (Brasil)"
        title = f"Doses Aplicadas vs Complicações Notificadas{state_str}"
        title += f"\nFiltro de Gravidade: {args.severity.upper()} | Ordenacao: {args.sort}"
        
        generate_complications_chart(df_merged, title, output_file=args.output, anomaly_msg=anomaly_msg)
    elif args.chart == 'infographic':
        if not args.search:
            eprint("ERRO: Para o infográfico, você deve especificar uma vacina usando --search")
            sys.exit(1)
            
        vaccine_search = args.search[0].lower()
        
        # 1. Total doses
        all_dfs = []
        for y in range(start, end + 1):
            df_y = update_modern_data(y, args.update, states=args.state, cities=args.city, mode='doses')
            if not df_y.empty:
                all_dfs.append(df_y)
        if all_dfs:
            df_doses = pd.concat(all_dfs).groupby('vaccine')['total_doses'].sum().reset_index()
        else:
            eprint("Sem dados de doses para o periodo.")
            sys.exit(1)
            
        # 2. VigiMed
        df_v = get_vigimed_data('all') # Need custom query since we need all severity levels
        # Wait, get_vigimed_data currently filters by severity and aggregates! We need raw parsed!
        # Let's do it here:
        df_v_raw = pd.read_csv('data/raw/VigiMed_Notificacoes.csv', sep=';', encoding='ISO-8859-1', on_bad_lines='skip', low_memory=False)
        df_v_raw = df_v_raw.dropna(subset=['NOME_MEDICAMENTO_WHODRUG'])
        
        if args.state:
            df_v_raw = df_v_raw[df_v_raw['UF'].isin(args.state)]
            
        df_v_raw['ano_noti'] = df_v_raw['DATA_INCLUSAO_SISTEMA'].str.extract(r'(\d{4})').astype(float)
        df_v_raw = df_v_raw[(df_v_raw['ano_noti'] >= start) & (df_v_raw['ano_noti'] <= end)]
        df_v_raw['vaccine_std'] = df_v_raw['NOME_MEDICAMENTO_WHODRUG'].apply(padroniza_nome_vacina)
        
        df_v_filtered = df_v_raw[df_v_raw['vaccine_std'].str.lower().str.contains(vaccine_search)]
        if df_v_filtered.empty:
            eprint("Nenhuma notificacao encontrada para esta pesquisa.")
            sys.exit(1)
            
        vaccine_name = df_v_filtered['vaccine_std'].iloc[0]
        df_v_filtered = df_v_filtered[df_v_filtered['vaccine_std'] == vaccine_name]
        
        # Match doses
        match_dose = df_doses[df_doses['vaccine'] == vaccine_name]
        total_doses = match_dose.iloc[0]['total_doses'] if not match_dose.empty else 0
        
        def expand_reactions(df_subset):
            if df_subset.empty: return {}
            s = df_subset['REACAO_EVENTO_ADVERSO_MEDDRA'].dropna().str.split('|').explode().str.strip()
            return s.value_counts().head(10).to_dict()
            
        is_death = df_v_filtered['DESFECHO'].str.contains('óbito|fatal', case=False, na=False) | df_v_filtered['GRAVIDADE'].str.contains('óbito|fatal', case=False, na=False)
        is_severe = (df_v_filtered['GRAVE'] == 'Sim') | is_death
        is_simple = (df_v_filtered['GRAVE'] == 'Não') & (~is_severe)
        
        res = {
            'vaccine_name': vaccine_name,
            'total_obitos': int(is_death.sum()),
            'counts': {
                'Graves (incl. Óbitos)': int(is_severe.sum()),
                'Simples': int(is_simple.sum())
            },
            'top_severe': expand_reactions(df_v_filtered[is_severe]),
            'top_simple': expand_reactions(df_v_filtered[is_simple]),
            'demographics': {
                'sex': df_v_filtered['SEXO'].value_counts().to_dict(),
                'age': df_v_filtered['GRUPO_IDADE'].value_counts().to_dict()
            }
        }
        
        generate_infographic(res, total_doses, output_file=args.output)

    else:
        all_dfs = []
        for y in range(start, end + 1):
            mode = 'cobertura' if args.chart == 'people' else 'doses'
            df_y = update_modern_data(y, args.update, states=args.state, cities=args.city, mode=mode)
            if not df_y.empty:
                all_dfs.append(df_y)
            
        if all_dfs:
            df = pd.concat(all_dfs)
            df = df.groupby('vaccine').sum().reset_index()
        else:
            df = pd.DataFrame(columns=['vaccine', 'total_doses'])
            
        label_year = f"{start}-{end}" if start != end else str(start)
        state_label = f" ({' '.join(args.state)})" if args.state else ""
        city_label = f" (Mun: {','.join(args.city)})" if args.city else ""
        label_year += state_label + city_label
        
        if args.chart == 'doses':
            generate_doses_chart(df, label_year, search_terms=args.search, top_n=args.top, bottom_n=args.bottom, output_file=args.output)
        elif args.chart == 'people':
            generate_people_chart(df, label_year, search_terms=args.search, top_n=args.top, bottom_n=args.bottom, output_file=args.output)

if __name__ == '__main__':
    main()
