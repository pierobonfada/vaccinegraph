#!/usr/bin/env python3
import os
import sys
import argparse
import urllib.request
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import warnings

warnings.filterwarnings('ignore')

DATA_DIR = "data"
RAW_DATA_DIR = os.path.join(DATA_DIR, "raw")
OUTPUT_DIR = "output"

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def download_file(url, dest_path):
    try:
        response = urllib.request.urlopen(url)
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
    if 'COVID' in nome: return 'COVID-19'
    if 'INFLUENZA' in nome and 'HAEMOPHILUS' not in nome: return 'Influenza'
    if 'HAEMOPHILUS' in nome: return 'Haemophilus influenzae b (Hib)'
    if 'POLIO' in nome and 'ORAL' in nome: return 'Poliomielite Oral (VOP)'
    if 'VOP' in nome: return 'Poliomielite Oral (VOP)'
    if 'POLIO' in nome: return 'Poliomielite Inativada (VIP)'
    if 'VIP' in nome: return 'Poliomielite Inativada (VIP)'
    if 'HEPATITE B' in nome: return 'Hepatite B'
    if 'HEPATITE A' in nome: return 'Hepatite A'
    if 'FEBRE AMARELA' in nome: return 'Febre Amarela'
    if 'DENGUE' in nome: return 'Dengue'
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
    
    filename = "Doses_Residencia.parquet" if mode in ['doses', 'monthly'] else "Cobertura_Residencia.parquet"
    DATABASE_FILE = os.path.join(DATA_DIR, f"vaccination_aggregate_{year}_{mode}{suffix}.parquet")
    
    eprint(f"\n[Fase 1] Verificacao de Dados Reais do SI-PNI (SIPNIBD - {year}) - Modo: {mode}")
    url = f"ftp://ftp.datasus.gov.br/dissemin/publicos/Dados_Abertos/SIPNIBD/{filename}"
    dest_path = os.path.join(RAW_DATA_DIR, filename)
    
    updated_any = False
    if not os.path.exists(dest_path) or force_update:
        download_file(url, dest_path)
        updated_any = True
        
    if updated_any or not os.path.exists(DATABASE_FILE) or force_update:
        eprint(f">> Lendo banco Parquet massivo de {mode} e agregando doses...")
        
        UF_CODES = {'AC': '12', 'AL': '27', 'AM': '13', 'AP': '16', 'BA': '29', 'CE': '23', 'DF': '53', 'ES': '32', 'GO': '52', 'MA': '21', 'MG': '31', 'MS': '50', 'MT': '51', 'PA': '15', 'PB': '25', 'PE': '26', 'PI': '22', 'PR': '41', 'RJ': '33', 'RN': '24', 'RO': '11', 'RR': '14', 'RS': '43', 'SC': '42', 'SE': '28', 'SP': '35', 'TO': '17'}
        
        if mode in ['doses', 'monthly']:
            cols = ['nu_ano', 'nu_mes', 'co_municipio', 'ds_imuno', 'qt_dose'] if mode == 'monthly' else ['nu_ano', 'co_municipio', 'ds_imuno', 'qt_dose']
            df_raw = pd.read_parquet(dest_path, columns=cols)
            df_ano = df_raw[df_raw['nu_ano'] == int(year)].copy()
            if states:
                codes = [UF_CODES[uf] for uf in states]
                df_ano = df_ano[df_ano['co_municipio'].str[:2].isin(codes)]
            if cities:
                df_ano = df_ano[df_ano['co_municipio'].isin(cities)]
            df_ano['vaccine'] = df_ano['ds_imuno'].apply(padroniza_nome_vacina)
            df_ano['qt_dose'] = pd.to_numeric(df_ano['qt_dose'], errors='coerce').fillna(0)
            if mode == 'monthly':
                df = df_ano.groupby(['vaccine', 'nu_mes', 'nu_ano'])['qt_dose'].sum().reset_index()
            else:
                df = df_ano.groupby('vaccine')['qt_dose'].sum().reset_index()
            df = df.rename(columns={'qt_dose': 'total_doses'})
        else:
            df_raw = pd.read_parquet(dest_path)
            df_raw['CO_ANO'] = df_raw['CO_ANO'].astype(str)
            df_ano = df_raw[df_raw['CO_ANO'] == str(year)].copy()
            if states:
                df_ano = df_ano[df_ano['CO_UF'].isin(states)]
            if cities:
                df_ano = df_ano[df_ano['CO_MUNICIPIO'].astype(str).isin(cities)]
            df_ano['vaccine'] = df_ano['NU_IMUNO'].apply(padroniza_nome_vacina)
            df_ano['QT_DOSE'] = pd.to_numeric(df_ano['QT_DOSE'], errors='coerce').fillna(0)
            df = df_ano.groupby('vaccine')['QT_DOSE'].sum().reset_index()
            df = df.rename(columns={'QT_DOSE': 'total_doses'})

        df.to_parquet(DATABASE_FILE, index=False)
        return df
    else:
        eprint(">> Base cacheada ja existe.")
        return pd.read_parquet(DATABASE_FILE)

def apply_filters_and_highlights(stats_df, sort_col, search_terms=None, top_n=None, bottom_n=None):
    stats_df = stats_df.copy()
    stats_df = stats_df.sort_values(by=sort_col, ascending=False).reset_index(drop=True)
    
    if search_terms:
        search_terms = [s.lower() for s in search_terms]
        def match_search(name):
            return any(s in name.lower() for s in search_terms)
        stats_df['is_searched'] = stats_df['vaccine'].apply(match_search)
    else:
        stats_df['is_searched'] = False
        
    stats_df['color'] = stats_df['is_searched'].map({True: '#2ecc71', False: '#95a5a6'})
    
    if search_terms:
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

def annotate_bars(ax):
    for p in ax.patches:
        val = p.get_height()
        if val > 0:
            ax.annotate(f'{int(val):,}', 
                        (p.get_x() + p.get_width() / 2., val/2), 
                        ha='center', va='center', rotation=90, 
                        color='white', fontsize=10, fontweight='bold')

def format_millions(x, pos):
    if x >= 1e6:
        return f'{x*1e-6:g} Milhões'
    elif x >= 1e3:
        return f'{x*1e-3:g} Mil'
    return f'{x:g}'

def handle_output(fig, output_file):
    plt.tight_layout()
    if output_file:
        out_path = os.path.join(OUTPUT_DIR, os.path.basename(output_file)) if not os.path.isabs(output_file) else output_file
        fig.savefig(out_path, dpi=300, bbox_inches='tight')
        eprint(f">> Grafico salvo em: {out_path}")
    else:
        import io
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=300, bbox_inches='tight')
        sys.stdout.buffer.write(buf.getvalue())
    plt.close(fig)

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
    parser = argparse.ArgumentParser(description="Analise DADOS REAIS de vacinacao (DATASUS >= 2023)")
    
    parser.add_argument('--year', type=int, help="Ano de pesquisa (ex: 2023, 2024). Substituto para start-year e end-year se for apenas 1 ano.")
    parser.add_argument('--start-year', type=int, help="Ano inicial (min: 2023).")
    parser.add_argument('--end-year', type=int, help="Ano final.")
    parser.add_argument('--clear-cache', action='store_true', help="Deleta todos os dados baixados e o banco consolidado.")
    parser.add_argument('--update', action='store_true', help="Forca o download ignorando cache.")
    parser.add_argument('--chart', type=str, choices=['doses', 'people', 'timeline', 'total_yearly', 'monthly'], default='doses', help="Tipo de grafico.")
    parser.add_argument('--search', type=str, nargs='+')
    parser.add_argument('--top', type=int)
    parser.add_argument('--bottom', type=int)
    parser.add_argument('--state', type=str, nargs='+', help='Estados para filtrar (ex: RS SP).')
    parser.add_argument('--city', type=str, nargs='+', help='Codigos IBGE de municipios (6 digitos).')
    parser.add_argument('-o', '--output', type=str, help='Arquivo de saida para a imagem PNG. (Salvo na pasta output/)')
    
    args = parser.parse_args()
    
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
        else:
            df = pd.DataFrame(columns=['vaccine', 'nu_mes', 'nu_ano', 'total_doses'])
            
        title = f"Série Temporal de Vacinação (Mês a Mês)"
        if args.search: title += f"\n[{', '.join(args.search)}]"
        if args.state: title += f" ({' '.join(args.state)})"
        if args.city: title += f" (Mun: {','.join(args.city)})"
        
        generate_monthly_chart(df, title, output_file=args.output)
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
