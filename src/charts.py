import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from src.utils import eprint, format_millions
from src.data import apply_filters_and_highlights
from src.downloader import OUTPUT_DIR

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

def generate_doses_chart(df, year, output_file=None, search_terms=None, top_n=None, bottom_n=None, exclude_terms=None, only_terms=None):
    df_doses = apply_filters_and_highlights(df, sort_col='total_doses', search_terms=search_terms, top_n=top_n, bottom_n=bottom_n, exclude_terms=exclude_terms, only_terms=only_terms)
    if df_doses.empty:
        print("Erro: A filtragem resultou em um grafico vazio.", file=sys.stderr)
        sys.exit(1)
    
    fig, ax1 = plt.subplots(figsize=(10, 8))
    ax1.bar(df_doses['vaccine'], df_doses['total_doses'], color=df_doses['color'])
    ax1.set_title(f'Total de Doses Aplicadas ({year})', fontsize=14, pad=20)
    ax1.set_ylabel('Total de Doses Aplicadas', fontsize=12)
    ax1.tick_params(axis='x', rotation=90)
    ax1.yaxis.set_major_formatter(FuncFormatter(format_millions))
    annotate_bars(ax1)
    handle_output(fig, output_file)

def generate_people_chart(df, year, output_file=None, search_terms=None, top_n=None, bottom_n=None, exclude_terms=None, only_terms=None):
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
        import math
        offset_doses = 3
        if comp > 0 and dose > 0:
            # If the log distance is too small, they will overlap.
            # We push the 'Doses' text higher by 45 points to clear the 3 lines of 'Casos' text.
            if math.log10(dose) - math.log10(comp) < 1.2:
                offset_doses = 45
                
        ax.annotate(f'{dose_str}\nDoses', (i, dose), ha='center', va='bottom', fontsize=9, color=color_text, xytext=(0, offset_doses), textcoords='offset points')
        ax.annotate(f'{comp_str}\nCasos\n({pct:.4f}%)', (i, comp), ha='center', va='bottom', fontsize=10, fontweight='bold', color='#c0392b', xytext=(0, 3), textcoords='offset points')
        
    ylim = ax.get_ylim()
    ax.set_ylim(ylim[0], ylim[1] * 3.5)
    
    fig.legend(loc='upper center', bbox_to_anchor=(0.5, 0.90), ncol=2, frameon=False, fontsize=12)
    
    plt.suptitle(title, fontsize=16, fontweight='black', color='#2c3e50', y=0.98)
    ax.set_title("As colunas vermelhas indicam o impacto absoluto (volume de casos). Não confunda a altura da barra com o risco (%),\npois uma vacina de risco ínfimo pode gerar mais casos se for aplicada em massa na população.", fontsize=10, color='#7f8c8d', style='italic', pad=30)
    
    
    if anomaly_msg:
        fig.text(0.5, 0.02, anomaly_msg, ha='center', va='bottom', fontsize=9, color='#c0392b', fontweight='bold', style='italic', bbox=dict(facecolor='#f8d7da', edgecolor='#f5c6cb', boxstyle='round,pad=0.5', alpha=0.8))
        plt.tight_layout(rect=[0, 0.05, 1, 0.88])
    else:
        plt.tight_layout(rect=[0, 0.06, 1, 0.88])
        
    handle_output(fig, output_file)



def generate_risk_chart(df, title, output_file=None, anomaly_msg=None):
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # We invert so highest is at the top of a horizontal bar chart
    df = df.iloc[::-1].reset_index(drop=True)
    
    colors = ['#c0392b' if c else '#34495e' for c in df.get('is_searched', pd.Series([False]*len(df)))]
    
    bars = ax.barh(df['vaccine'], df['pct_complications'], color=colors)
    
    ax.set_title(title, fontsize=14, pad=20, fontweight='black', color='#2c3e50')
    ax.set_xlabel('Taxa de Complicações (%)', fontsize=12)
    
    # Format x-axis as percentage with many decimals since risks are tiny
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, pos: f'{x:.4f}%'))
    
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    # Add text labels on the bars
    xlim_max = ax.get_xlim()[1]
    for bar, pct, dose, comp in zip(bars, df['pct_complications'], df['total_doses'], df['total_complications']):
        # Percentage next to the bar
        ax.text(bar.get_width() + (xlim_max*0.01), bar.get_y() + bar.get_height()/2,
                f'{pct:.4f}%',
                va='center', ha='left', fontsize=10, fontweight='bold', color='#c0392b')
                
        # Absolute numbers
        if bar.get_width() > xlim_max * 0.4:
            # Bar is very long, put text inside the bar (left aligned)
            ax.text(xlim_max * 0.01, bar.get_y() + bar.get_height()/2,
                    f"{int(comp):,} casos em {int(dose):,} doses".replace(',', '.'),
                    va='center', ha='left', fontsize=9, color='white')
        else:
            # Bar is short, put text at the far right edge of the chart (right aligned)
            ax.text(xlim_max * 0.99, bar.get_y() + bar.get_height()/2,
                    f"{int(comp):,} casos em {int(dose):,} doses".replace(',', '.'),
                    va='center', ha='right', fontsize=9, color='#7f8c8d')

    if anomaly_msg:
        fig.text(0.5, 0.02, anomaly_msg, ha='center', va='bottom', fontsize=9, color='#c0392b', fontweight='bold', style='italic', bbox=dict(facecolor='#f8d7da', edgecolor='#f5c6cb', boxstyle='round,pad=0.5', alpha=0.8))
        plt.tight_layout(rect=[0, 0.05, 1, 0.95])
    else:
        plt.tight_layout(rect=[0, 0.02, 1, 0.95])
        
    handle_output(fig, output_file)
