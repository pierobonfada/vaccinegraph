import datetime
import shutil
import pandas as pd
import argparse
import sys
import os
from src.utils import eprint
from src.downloader import global_update, RAW_DATA_DIR, OUTPUT_DIR, DATA_DIR
from src.data import resolve_city_name, padroniza_nome_vacina, update_modern_data, apply_filters_and_highlights, get_vigimed_data
from src.charts import (generate_infographic, generate_doses_chart, generate_people_chart,
                        generate_timeline_chart, generate_total_yearly_chart,
                        generate_monthly_chart, generate_profile_chart, generate_complications_chart)

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
    current_year = datetime.date.today().year
    parser.add_argument('--end-year', type=int, default=current_year, help="Ano final da análise (padrão: ano atual).")
    parser.add_argument('--state', type=str, nargs='+', help="Filtrar por Sigla(s) do Estado (Ex: RS SP).")
    parser.add_argument('--city', type=str, nargs='+', help="Filtrar por Nome da Cidade (ex: Veranópolis) ou Código IBGE (6 dígitos).")
    
    parser.add_argument('--top', type=int, help="Limita o gráfico para exibir apenas as N vacinas no topo do ranking.")
    parser.add_argument('--bottom', type=int, help="Exibe as N vacinas na base do ranking.")
    
    parser.add_argument('--search', type=str, nargs='+', help="Busca vacinas específicas por nome (Ex: HPV Influenza). Em infographic, define o alvo principal.")
    parser.add_argument('--exclude', type=str, nargs='+', help="Remove vacinas específicas do gráfico (Ex: Influenza COVID).")
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
        
    city_names = []
    if args.city:
        resolved = [resolve_city_name(c) for c in args.city]
        args.city = [r[0] for r in resolved]
        city_names = [r[1] for r in resolved]
        
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
        global_update()
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
                df_doses = apply_filters_and_highlights(df_doses, 'total_doses', search_terms=args.search, exclude_terms=args.exclude)
                df_doses = df_doses[df_doses['is_searched']]
            total_doses = df_doses['total_doses'].sum() if not df_doses.empty else 0
            
            df_cob = update_modern_data(y, args.update, states=args.state, cities=args.city, mode='cobertura')
            if args.search:
                df_cob = apply_filters_and_highlights(df_cob, 'total_doses', search_terms=args.search, exclude_terms=args.exclude)
                df_cob = df_cob[df_cob['is_searched']]
            total_schemas = df_cob['total_doses'].sum() if not df_cob.empty else 0
            
            timeline_data[y] = {'doses': total_doses, 'schemas': total_schemas}
            
        generate_timeline_chart(timeline_data, output_file=args.output)
        
    elif args.chart == 'total_yearly':
        yearly_data = {}
        for y in range(start, end + 1):
            df_doses = update_modern_data(y, args.update, states=args.state, cities=args.city, mode='doses')
            if args.search:
                df_doses = apply_filters_and_highlights(df_doses, 'total_doses', search_terms=args.search, exclude_terms=args.exclude)
                df_doses = df_doses[df_doses['is_searched']]
            yearly_data[y] = df_doses['total_doses'].sum() if not df_doses.empty else 0
        
        title = "Total Absoluto de Vacinas Aplicadas por Ano"
        if args.state: title += f" ({' '.join(args.state)})"
        if city_names: title += f" ({', '.join(city_names)})"
        generate_total_yearly_chart(yearly_data, output_file=args.output, title=title)
        
    elif args.chart == 'monthly':
        all_dfs = []
        for y in range(start, end + 1):
            df_y = update_modern_data(y, args.update, states=args.state, cities=args.city, mode='monthly')
            if not df_y.empty:
                all_dfs.append(df_y)
        if all_dfs:
            df = pd.concat(all_dfs)
            if args.exclude:
                exclude_terms = [e.lower() for e in args.exclude]
                df = df[~df['vaccine'].str.lower().apply(lambda x: any(e in x for e in exclude_terms))]
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
        if city_names: title += f" ({', '.join(city_names)})"
        
        generate_monthly_chart(df, title, output_file=args.output)
    elif args.chart == 'profile':
        all_dfs = []
        for y in range(start, end + 1):
            df_y = update_modern_data(y, args.update, states=args.state, cities=args.city, mode='profile')
            if not df_y.empty:
                all_dfs.append(df_y)
        if all_dfs:
            df = pd.concat(all_dfs)
            if args.exclude:
                exclude_terms = [e.lower() for e in args.exclude]
                df = df[~df['vaccine'].str.lower().apply(lambda x: any(e in x for e in exclude_terms))]
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
        if city_names: title += f" ({', '.join(city_names)})"
        
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
        if args.exclude:
            exclude_terms = [e.lower() for e in args.exclude]
            df_doses = df_doses[~df_doses['vaccine'].str.lower().apply(lambda x: any(e in x for e in exclude_terms))]
        
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
        df_merged = apply_filters_and_highlights(df_merged, sort_col, search_terms=args.search, top_n=args.top, bottom_n=args.bottom, exclude_terms=args.exclude, until_terms=args.until, ascending=ascending)
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
        if args.exclude:
            exclude_terms = [e.lower() for e in args.exclude]
            df_doses = df_doses[~df_doses['vaccine'].str.lower().apply(lambda x: any(e in x for e in exclude_terms))]
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
            generate_doses_chart(df, label_year, search_terms=args.search, top_n=args.top, bottom_n=args.bottom, exclude_terms=args.exclude, output_file=args.output)
        elif args.chart == 'people':
            generate_people_chart(df, label_year, search_terms=args.search, top_n=args.top, bottom_n=args.bottom, exclude_terms=args.exclude, output_file=args.output)

if __name__ == '__main__':
    main()

