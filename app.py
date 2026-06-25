# ==========================================
# 1. IMPORTS & CONFIG
# ==========================================
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# Konfigurasi Halaman (Harus diletakkan paling atas)
st.set_page_config(
    page_title="Dashboard ACS Lanud RSN", 
    layout="wide", 
    page_icon="✈️",
    initial_sidebar_state="collapsed"
)

# Custom CSS untuk mempertegas nuansa elegan & tactical
st.markdown("""
    <style>
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    h1, h2, h3 { color: #f0f2f6; font-family: 'Helvetica Neue', sans-serif; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. HELPER & PREPROCESSING FUNCTIONS
# ==========================================
def get_season(month_num):
    if month_num in [12, 1, 2]: return 'DJF (Des-Jan-Feb)'
    elif month_num in [3, 4, 5]: return 'MAM (Mar-Apr-Mei)'
    elif month_num in [6, 7, 8]: return 'JJA (Jun-Jul-Agt)'
    elif month_num in [9, 10, 11]: return 'SON (Sep-Okt-Nov)'
    return 'Lainnya'

def get_season_color(month_num):
    # Mapping warna neon kontras tinggi berdasarkan kelompok musim
    if month_num in [12, 1, 2]: return '#FF2A6D'  # Neon Cyber-Pink
    elif month_num in [3, 4, 5]: return '#FF9900'  # Electric Amber
    elif month_num in [6, 7, 8]: return '#05FF00'  # Neon Lime Green
    elif month_num in [9, 10, 11]: return '#00F0FF' # Electric Cyan
    return '#00FFCC'

def map_month_to_datetime(month_str):
    month_map = {
        'JANUARY': 1, 'FEBRUARY': 2, 'MARCH': 3, 'APRIL': 4,
        'MAY': 5, 'JUNE': 6, 'JULY': 7, 'AUGUST': 8,
        'SEPTEMBER': 9, 'OCTOBER': 10, 'NOVEMBER': 11, 'DECEMBER': 12
    }
    m = month_map.get(str(month_str).strip().upper(), 1)
    return pd.to_datetime(f"2021-{m:02d}-01")

def safe_extract_min_max(filepath):
    try:
        df_raw = pd.read_excel(filepath, header=None)
        start_idx = df_raw[df_raw[0].astype(str).str.contains('JANUARY', case=False, na=False)].index[0]
        df_data = df_raw.iloc[start_idx:start_idx+12].reset_index(drop=True)
        
        df_clean = pd.DataFrame({
            'DATE': df_data.iloc[:, 0].astype(str).str.strip(),
            'DAILY_MEAN': pd.to_numeric(df_data.iloc[:, -3], errors='coerce'),
            'MAX_VAL': pd.to_numeric(df_data.iloc[:, -2], errors='coerce'),
            'MIN_VAL': pd.to_numeric(df_data.iloc[:, -1], errors='coerce')
        })
        return df_clean
    except Exception:
        return None

def safe_extract_distribution(filepath):
    try:
        df_raw = pd.read_excel(filepath)
        df_raw = df_raw.dropna(axis=1, how='all')
        
        months = ['JANUARY', 'FEBRUARY', 'MARCH', 'APRIL', 'MAY', 'JUNE', 'JULY', 'AUGUST', 'SEPTEMBER', 'OCTOBER', 'NOVEMBER', 'DECEMBER']
        date_col = next((col for col in df_raw.columns if df_raw[col].astype(str).str.upper().str.strip().isin(months).any()), None)
                
        if date_col is None: return None
            
        df_clean = df_raw[df_raw[date_col].astype(str).str.upper().str.strip().isin(months)].copy()
        df_clean.rename(columns={date_col: 'DATE'}, inplace=True)
        
        dist_cols = [c for c in df_clean.columns if '<' in str(c) or '>' in str(c)]
        for c in dist_cols:
            df_clean[c] = pd.to_numeric(df_clean[c], errors='coerce').fillna(0)
            
        return df_clean[['DATE'] + dist_cols]
    except Exception:
        return None

def parse_wind_sectors(columns):
    mapping = {
        '35 - 36 - 01': 0, '02 - 03 - 04': 30, '05 - 06 - 07': 60,
        '08 - 09 - 10': 90, '11 - 12 - 13': 120, '14 - 15 - 16': 150,
        '17 - 18 - 19': 180, '20 - 21 - 22': 210, '23 - 24 - 25': 240,
        '26 - 27 - 28': 270, '29 - 30 - 31': 300, '32 - 33 - 34': 330
    }
    clean_mapping = {k.replace(" ", ""): v for k, v in mapping.items()}
    return {col: clean_mapping[str(col).replace(" ", "")] for col in columns if str(col).replace(" ", "") in clean_mapping}

# ==========================================
# 3. ROBUST DATA LOADING
# ==========================================
@st.cache_data(show_spinner=False)
def load_data():
    data = {'hs': None, 'vis': None, 't': None, 'rh': None, 'wind': None}
    
    data['hs'] = safe_extract_distribution("hs_2021_2025.xlsx")
    if data['hs'] is not None: data['hs']['Datetime'] = data['hs']['DATE'].apply(map_month_to_datetime)
        
    data['vis'] = safe_extract_distribution("visibility_2021_2025.xlsx")
    if data['vis'] is not None: data['vis']['Datetime'] = data['vis']['DATE'].apply(map_month_to_datetime)
        
    data['t'] = safe_extract_min_max("t_max_min_2021_2025.xlsx")
    if data['t'] is not None: data['t']['Datetime'] = data['t']['DATE'].apply(map_month_to_datetime)
        
    data['rh'] = safe_extract_min_max("rh_max_min_2021_2025.xlsx")
    if data['rh'] is not None: data['rh']['Datetime'] = data['rh']['DATE'].apply(map_month_to_datetime)
        
    try:
        df_raw = pd.read_excel("WINDDIRECTION_2021_2025.xlsx")
        header_idx = df_raw[df_raw.astype(str).apply(lambda x: x.str.contains('DATE', case=False, na=False)).any(axis=1)].index
        df_wind = df_raw.iloc[header_idx[0]+1:].reset_index(drop=True) if len(header_idx) > 0 else df_raw
        df_wind.columns = df_raw.iloc[header_idx[0]].tolist() if len(header_idx) > 0 else df_raw.columns
            
        df_wind = df_wind.loc[:, df_wind.columns.notnull()]
        df_wind = df_wind.loc[:, ~df_wind.columns.astype(str).str.contains('Unnamed', case=False)]
        df_wind['Datetime'] = df_wind['DATE'].apply(map_month_to_datetime)
        
        if 'DIRECTION' in df_wind.columns:
            df_wind['DIRECTION'] = df_wind['DIRECTION'].astype(str).replace(['None', 'none', 'nan', 'NaN'], 'CALM')
            df_wind['DIRECTION'] = df_wind['DIRECTION'].fillna('CALM')
        
        for c in df_wind.columns:
            if c not in ['DATE', 'DIRECTION', 'Datetime']:
                df_wind[c] = pd.to_numeric(df_wind[c], errors='coerce').fillna(0)
        data['wind'] = df_wind.sort_values('Datetime')
    except Exception: pass

    return data

# ==========================================
# 4. METEOGRAM & VISUALIZATION 
# ==========================================
def plot_main_meteogram(data):
    fig = make_subplots(
        rows=4, cols=1, shared_xaxes=True, 
        vertical_spacing=0.08, 
        subplot_titles=(
            "1. Profil Suhu Udara (T Max, Mean, Min)", 
            "2. Profil Kelembapan Relatif (RH Max, Mean, Min)", 
            "3. Distribusi Jarak Pandang (Visibility)", 
            "4. Tinggi Dasar Awan Terendah (HS)"
        )
    )
    
    # Penempatan ke legend khusus (legend, legend2, legend3, legend4) agar sejajar per baris
    if data['t'] is not None:
        df = data['t'].sort_values('Datetime')
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['MAX_VAL'], mode='lines+markers', name='T Max', line=dict(color='#ff4b4b', width=2), legend='legend'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['DAILY_MEAN'], mode='lines+markers', name='T Mean', line=dict(color='#ffa500', width=2, dash='dot'), legend='legend'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['MIN_VAL'], mode='lines+markers', name='T Min', line=dict(color='#00bfff', width=2), legend='legend'), row=1, col=1)

    if data['rh'] is not None:
        df = data['rh'].sort_values('Datetime')
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['MAX_VAL'], mode='lines+markers', name='RH Max', line=dict(color='#00fa9a', width=2), legend='legend2'), row=2, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['DAILY_MEAN'], mode='lines+markers', name='RH Mean', line=dict(color='#90ee90', width=2, dash='dot'), legend='legend2'), row=2, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['MIN_VAL'], mode='lines+markers', name='RH Min', line=dict(color='#cd853f', width=2), legend='legend2'), row=2, col=1)

    if data['vis'] is not None:
        df = data['vis'].sort_values('Datetime')
        cols = [c for c in df.columns if '<' in str(c) or '>' in str(c)]
        colors_vis = px.colors.sequential.Tealgrn[1:] 
        for i, c in enumerate(cols):
            color = colors_vis[i % len(colors_vis)]
            fig.add_trace(go.Bar(x=df['Datetime'], y=df[c], name=f'Vis {c}', marker_color=color, legend='legend3'), row=3, col=1)

    if data['hs'] is not None:
        df = data['hs'].sort_values('Datetime')
        cols = [c for c in df.columns if '<' in str(c)]
        colors_hs = px.colors.sequential.Purp[2:] 
        for i, c in enumerate(cols):
            color = colors_hs[i % len(colors_hs)]
            fig.add_trace(go.Bar(x=df['Datetime'], y=df[c], name=f'HS {c}', marker_color=color, legend='legend4'), row=4, col=1)
            
    fig.update_yaxes(title_text="Suhu (°C)", row=1, col=1)
    fig.update_yaxes(title_text="RH (%)", row=2, col=1)
    fig.update_yaxes(title_text="Freq (%)", row=3, col=1)
    fig.update_yaxes(title_text="Freq (%)", row=4, col=1)

    # Konfigurasi Multi-Legend untuk Penyelarasan Posisi secara Presisi
    fig.update_layout(
        template="plotly_dark", 
        height=1250, 
        barmode='stack', 
        hovermode='x unified',
        plot_bgcolor="rgba(15, 20, 25, 1)", 
        paper_bgcolor="rgba(0,0,0,0)",       
        
        # Kotak Legenda Baris 1 (Suhu)
        legend=dict(
            x=1.02, y=1.00, yanchor='top', xanchor='left',
            title=dict(text="<b>Suhu</b>", font=dict(size=12, color="#ff4b4b")),
            bgcolor='rgba(20, 25, 30, 0.7)', bordercolor='rgba(255,75,75,0.3)', borderwidth=1
        ),
        # Kotak Legenda Baris 2 (RH)
        legend2=dict(
            x=1.02, y=0.73, yanchor='top', xanchor='left',
            title=dict(text="<b>RH</b>", font=dict(size=12, color="#00fa9a")),
            bgcolor='rgba(20, 25, 30, 0.7)', bordercolor='rgba(0,250,154,0.3)', borderwidth=1
        ),
        # Kotak Legenda Baris 3 (Visibility)
        legend3=dict(
            x=1.02, y=0.46, yanchor='top', xanchor='left',
            title=dict(text="<b>Visibility</b>", font=dict(size=12, color="#00a896")),
            bgcolor='rgba(20, 25, 30, 0.7)', bordercolor='rgba(0,168,150,0.3)', borderwidth=1
        ),
        # Kotak Legenda Baris 4 (HS)
        legend4=dict(
            x=1.02, y=0.19, yanchor='top', xanchor='left',
            title=dict(text="<b>HS</b>", font=dict(size=12, color="#aa4bfa")),
            bgcolor='rgba(20, 25, 30, 0.7)', bordercolor='rgba(170,75,250,0.3)', borderwidth=1
        ),
        margin=dict(l=60, r=180, t=80, b=50)
    )
    
    fig.update_xaxes(
        showgrid=True, 
        gridwidth=1, 
        gridcolor='rgba(255,255,255,0.1)', 
        tickformat="%b", 
        hoverformat="%B, Rekap 2021-2025" 
    )
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(255,255,255,0.1)')
    
    return fig

def render_wind_dashboard(df_wind):
    if df_wind is None:
        st.warning("⚠️ Data Angin tidak tersedia atau gagal dibaca.")
        return
        
    df_wind['Season'] = df_wind['Datetime'].dt.month.apply(get_season)
    
    dir_map = parse_wind_sectors(df_wind.columns)
    dir_cols = list(dir_map.keys())
    speed_cols = [c for c in df_wind.columns if '-' in str(c) or '>' in str(c)]
    speed_cols = [c for c in speed_cols if c not in dir_cols]
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 🧭 Pola Arah Angin Musiman")
        if dir_cols:
            seasonal_dir = df_wind.groupby('Season')[dir_cols].mean().reset_index()
            melt_dir = seasonal_dir.melt(id_vars='Season', value_vars=dir_cols, var_name='Arah', value_name='Frekuensi (%)')
            fig_dir = px.bar(melt_dir, x='Season', y='Frekuensi (%)', color='Arah', barmode='group', color_discrete_sequence=px.colors.qualitative.Pastel)
            fig_dir.update_layout(template="plotly_dark", plot_bgcolor="rgba(15, 20, 25, 1)", paper_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", y=-0.2))
            st.plotly_chart(fig_dir, use_container_width=True)
        
    with col2:
        st.markdown("### 🌪️ Pola Kecepatan Angin Musiman")
        if speed_cols:
            seasonal_speed = df_wind.groupby('Season')[speed_cols].mean().reset_index()
            melt_speed = seasonal_speed.melt(id_vars='Season', value_vars=speed_cols, var_name='Kecepatan (Knot)', value_name='Frekuensi (%)')
            fig_speed = px.bar(melt_speed, x='Season', y='Frekuensi (%)', color='Kecepatan (Knot)', barmode='group', color_discrete_sequence=px.colors.sequential.Agsunset)
            fig_speed.update_layout(template="plotly_dark", plot_bgcolor="rgba(15, 20, 25, 1)", paper_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", y=-0.2))
            st.plotly_chart(fig_speed, use_container_width=True)
            
    # SECTION 1: KEMBALIKAN WINDROSE MUSIMAN (DENGAN WARNA NEON KONTRAS TINGGI)
    st.markdown("---")
    st.markdown("### 🎯 Windrose Musiman Operasional (Radar View)")
    seasons = ['DJF (Des-Jan-Feb)', 'MAM (Mar-Apr-Mei)', 'JJA (Jun-Jul-Agt)', 'SON (Sep-Okt-Nov)']
    season_colors = ['#FF2A6D', '#FF9900', '#05FF00', '#00F0FF'] # Definisi warna kontras tinggi per musim
    
    cols_wr_season = st.columns(4)
    for i, season in enumerate(seasons):
        season_data = df_wind[df_wind['Season'] == season]
        if not season_data.empty and dir_cols:
            r_vals = season_data[dir_cols].mean().values
            theta_vals = [dir_map[c] for c in dir_cols]
            
            # Mendapatkan kecepatan dominan riil musiman
            dom_speed_s = "N/A"
            if speed_cols:
                mean_speeds_s = season_data[speed_cols].mean()
                dom_speed_s = mean_speeds_s.idxmax() if not mean_speeds_s.empty and mean_speeds_s.max() > 0 else "N/A"
            
            title_html_s = f"<b>{season}</b><br><span style='font-size:11px; color:#ffa500;'>Kec. Dominan: {dom_speed_s} Knot</span>"
            
            fig_wr_s = go.Figure(go.Barpolar(
                r=r_vals, 
                theta=theta_vals, 
                name=season, 
                marker_color=season_colors[i], 
                opacity=0.85,
                hovertemplate="Arah: %{theta}°<br>Frekuensi: %{r:.2f}%<extra></extra>"
            ))
            
            fig_wr_s.update_layout(
                template="plotly_dark",
                title=dict(text=title_html_s, x=0.5, font=dict(size=13, color=season_colors[i])), 
                polar=dict(
                    bgcolor='rgba(15, 20, 25, 1)',
                    angularaxis=dict(direction="clockwise", rotation=90, gridcolor='rgba(255,255,255,0.2)', tickfont=dict(size=10)),
                    radialaxis=dict(
                        gridcolor='rgba(255,255,255,0.2)', 
                        showticklabels=True,  # Menampilkan angka di jaring lingkaran
                        ticksuffix='%',       # Menambahkan tanda %
                        tickfont=dict(size=9, color='rgba(255,255,255,0.7)'),
                        angle=45
                    )
                ), 
                paper_bgcolor='rgba(0,0,0,0)',
                margin=dict(t=70, b=30, l=20, r=20)
            )
            cols_wr_season[i].plotly_chart(fig_wr_s, use_container_width=True)

    # SECTION 2: WINDROSE BULANAN (GRID 3x4 DENGAN FORMAT JUDUL PER BULAN REKAP DATA RIIL)
    st.markdown("---")
    st.markdown("### 📅 Windrose Bulanan Operasional 2021-2025 (Radar View)")
    
    month_names = {
        1: 'Januari', 2: 'Februari', 3: 'Maret', 4: 'April',
        5: 'Mei', 6: 'Juni', 7: 'Juli', 8: 'Agustus',
        9: 'September', 10: 'Oktober', 11: 'November', 12: 'Desember'
    }
    
    for row in range(3):
        cols_wr_month = st.columns(4)
        for col in range(4):
            month_num = row * 4 + col + 1
            month_label = month_names[month_num]
            
            # Filter riil data berdasarkan urutan bulan dari excel
            month_data = df_wind[df_wind['Datetime'].dt.month == month_num]
            
            if not month_data.empty and dir_cols:
                r_vals_m = month_data[dir_cols].mean().values
                theta_vals_m = [dir_map[c] for c in dir_cols]
                
                # Kalkulasi kecepatan dominan riil bulanan dari dataset
                dom_speed_m = "N/A"
                if speed_cols:
                    mean_speeds_m = month_data[speed_cols].mean()
                    dom_speed_m = mean_speeds_m.idxmax() if not mean_speeds_m.empty and mean_speeds_m.max() > 0 else "N/A"
                
                vibrant_color = get_season_color(month_num)
                title_html_m = f"<b>{month_label} 2021-2025</b><br><span style='font-size:11px; color:#ffa500;'>Kec. Dominan: {dom_speed_m} Knot</span>"
                
                fig_wr_m = go.Figure(go.Barpolar(
                    r=r_vals_m, 
                    theta=theta_vals_m, 
                    name=month_label, 
                    marker_color=vibrant_color, 
                    opacity=0.85,
                    hovertemplate="Arah: %{theta}°<br>Frekuensi: %{r:.2f}%<extra></extra>"
                ))
                
                fig_wr_m.update_layout(
                    template="plotly_dark",
                    title=dict(text=title_html_m, x=0.5, font=dict(size=13, color=vibrant_color)), 
                    polar=dict(
                        bgcolor='rgba(15, 20, 25, 1)',
                        angularaxis=dict(direction="clockwise", rotation=90, gridcolor='rgba(255,255,255,0.2)', tickfont=dict(size=10)),
                        radialaxis=dict(
                            gridcolor='rgba(255,255,255,0.2)', 
                            showticklabels=True,  # Menampilkan angka di jaring lingkaran bulanan
                            ticksuffix='%',       # Menambahkan tanda %
                            tickfont=dict(size=9, color='rgba(255,255,255,0.7)'),
                            angle=45
                        )
                    ), 
                    paper_bgcolor='rgba(0,0,0,0)',
                    margin=dict(t=70, b=30, l=20, r=20) 
                )
                cols_wr_month[col].plotly_chart(fig_wr_m, use_container_width=True)

# ==========================================
# 5. MAIN UI COMMAND CENTER
# ==========================================
def main():
    st.title("✈️ Dashboard Aerodrome Climatological Summary (ACS)")
    st.caption("Sistem Informasi Cuaca Terintegrasi - Operasional Pangkalan Militer (Rekapitulasi 2021-2025)")
    st.markdown("---")
    
    with st.spinner("Sinkronisasi instrumen klimatologi penerbangan..."):
        dataset = load_data()

    tab1, tab2, tab3 = st.tabs(["📊 METEOGRAM INTEGRASI", "🧭 ANALISIS ANGIN", "📁 INSPEKSI DATA"])
    
    with tab1:
        st.info("💡 **TIPS OPERASIONAL:** Arahkan kursor (*hover*) pada grafik untuk melihat pembacaan parameter. Klik item pada kotak legenda di samping kanan untuk menyembunyikan/menampilkan jalur data.")
        fig_main = plot_main_meteogram(dataset)
        st.plotly_chart(fig_main, use_container_width=True)
        
    with tab2:
        render_wind_dashboard(dataset['wind'])
        
    with tab3:
        st.markdown("### Status Matriks Data Asli")
        option = st.selectbox("Pilih Parameter Instrumen untuk Verifikasi:", list(dataset.keys()), format_func=lambda x: x.upper())
        if dataset[option] is not None:
            df_display = dataset[option].drop(columns=['Datetime'], errors='ignore')
            st.dataframe(df_display, use_container_width=True)
        else:
            st.error(f"❌ DATA_NOT_FOUND: Parameter {option.upper()} gagal dimuat.")

if __name__ == "__main__":
    main()
