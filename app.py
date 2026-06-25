# ==========================================
# 1. IMPORTS & CONFIG
# ==========================================
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

st.set_page_config(
    page_title="Dashboard ACS Lanud RSN", 
    layout="wide", 
    page_icon="✈️"
)

# ==========================================
# 2. HELPER & PREPROCESSING FUNCTIONS
# ==========================================
def get_season(month_num):
    if month_num in [12, 1, 2]: return 'DJF'
    elif month_num in [3, 4, 5]: return 'MAM'
    elif month_num in [6, 7, 8]: return 'JJA'
    elif month_num in [9, 10, 11]: return 'SON'
    return 'Lainnya'

def map_month_to_datetime(month_str):
    month_map = {
        'JANUARY': 1, 'FEBRUARY': 2, 'MARCH': 3, 'APRIL': 4,
        'MAY': 5, 'JUNE': 6, 'JULY': 7, 'AUGUST': 8,
        'SEPTEMBER': 9, 'OCTOBER': 10, 'NOVEMBER': 11, 'DECEMBER': 12
    }
    m = month_map.get(str(month_str).strip().upper(), 1)
    return pd.to_datetime(f"2021-{m:02d}-01")

def safe_extract_min_max(filepath):
    """Fungsi ekstraksi absolut untuk mengambil Mean, Max, Min dari 3 kolom terakhir."""
    try:
        df_raw = pd.read_excel(filepath, header=None)
        # Cari baris di mana data bulan pertama (JANUARY) dimulai
        start_idx = df_raw[df_raw[0].astype(str).str.contains('JANUARY', case=False, na=False)].index[0]
        # Ambil 12 baris ke bawah dari Januari
        df_data = df_raw.iloc[start_idx:start_idx+12].reset_index(drop=True)
        
        # Ekstrak kolom ke-1 (Date), dan 3 kolom terujung kanan (Mean, Max, Min)
        df_clean = pd.DataFrame({
            'DATE': df_data.iloc[:, 0].astype(str).str.strip(),
            'DAILY_MEAN': pd.to_numeric(df_data.iloc[:, -3], errors='coerce'),
            'MAX_VAL': pd.to_numeric(df_data.iloc[:, -2], errors='coerce'),
            'MIN_VAL': pd.to_numeric(df_data.iloc[:, -1], errors='coerce')
        })
        return df_clean
    except Exception as e:
        st.error(f"Error membaca {filepath}: {e}")
        return None

def safe_extract_distribution(filepath):
    """Fungsi sanitasi untuk data bertumpuk seperti Visibility dan HS."""
    try:
        df_raw = pd.read_excel(filepath)
        df_raw = df_raw.dropna(axis=1, how='all')
        
        months = ['JANUARY', 'FEBRUARY', 'MARCH', 'APRIL', 'MAY', 'JUNE', 'JULY', 'AUGUST', 'SEPTEMBER', 'OCTOBER', 'NOVEMBER', 'DECEMBER']
        date_col = None
        for col in df_raw.columns:
            if df_raw[col].astype(str).str.upper().str.strip().isin(months).any():
                date_col = col
                break
                
        if date_col is None: return None
            
        df_clean = df_raw[df_raw[date_col].astype(str).str.upper().str.strip().isin(months)].copy()
        df_clean.rename(columns={date_col: 'DATE'}, inplace=True)
        
        # Ambil kolom Date dan semua kolom yang mengandung karakter '<' atau '>'
        dist_cols = [c for c in df_clean.columns if '<' in str(c) or '>' in str(c)]
        for c in dist_cols:
            df_clean[c] = pd.to_numeric(df_clean[c], errors='coerce').fillna(0)
            
        return df_clean[['DATE'] + dist_cols]
    except Exception as e:
        return None

def parse_wind_sectors(columns):
    mapping = {
        '35 - 36 - 01': 0, '02 - 03 - 04': 30, '05 - 06 - 07': 60,
        '08 - 09 - 10': 90, '11 - 12 - 13': 120, '14 - 15 - 16': 150,
        '17 - 18 - 19': 180, '20 - 21 - 22': 210, '23 - 24 - 25': 240,
        '26 - 27 - 28': 270, '29 - 30 - 31': 300, '32 - 33 - 34': 330
    }
    clean_mapping = {k.replace(" ", ""): v for k, v in mapping.items()}
    result = {}
    for col in columns:
        clean_col = str(col).replace(" ", "")
        if clean_col in clean_mapping:
            result[col] = clean_mapping[clean_col]
    return result

# ==========================================
# 3. ROBUST DATA LOADING
# ==========================================
@st.cache_data
def load_data():
    data = {}
    
    # 1. HS
    data['hs'] = safe_extract_distribution("hs_2021_2025.xlsx")
    if data['hs'] is not None: data['hs']['Datetime'] = data['hs']['DATE'].apply(map_month_to_datetime)
        
    # 2. VISIBILITY
    data['vis'] = safe_extract_distribution("visibility_2021_2025.xlsx")
    if data['vis'] is not None: data['vis']['Datetime'] = data['vis']['DATE'].apply(map_month_to_datetime)
        
    # 3. TEMPERATURE MAX & MIN
    data['t'] = safe_extract_min_max("t_max_min_2021_2025.xlsx")
    if data['t'] is not None: data['t']['Datetime'] = data['t']['DATE'].apply(map_month_to_datetime)
        
    # 4. RH MAX & MIN
    data['rh'] = safe_extract_min_max("rh_max_min_2021_2025.xlsx")
    if data['rh'] is not None: data['rh']['Datetime'] = data['rh']['DATE'].apply(map_month_to_datetime)
        
    # 5. WIND DIRECTION
    try:
        df_raw = pd.read_excel("WINDDIRECTION_2021_2025.xlsx")
        header_idx = df_raw[df_raw.astype(str).apply(lambda x: x.str.contains('DATE', case=False, na=False)).any(axis=1)].index
        if len(header_idx) > 0:
            df_wind = df_raw.iloc[header_idx[0]+1:].reset_index(drop=True)
            df_wind.columns = df_raw.iloc[header_idx[0]].tolist()
        else:
            df_wind = df_raw
            
        df_wind = df_wind.loc[:, df_wind.columns.notnull()]
        df_wind = df_wind.loc[:, ~df_wind.columns.astype(str).str.contains('Unnamed', case=False)]
        df_wind['Datetime'] = df_wind['DATE'].apply(map_month_to_datetime)
        
        for c in df_wind.columns:
            if c not in ['DATE', 'DIRECTION', 'Datetime']:
                df_wind[c] = pd.to_numeric(df_wind[c], errors='coerce').fillna(0)
        data['wind'] = df_wind.sort_values('Datetime')
    except Exception:
        data['wind'] = None

    return data

# ==========================================
# 4. METEOGRAM & VISUALIZATION 
# ==========================================
def plot_main_meteogram(data):
    """Meteogram 4 Baris: T, RH, VIS, dan HS dengan Desain Militer/Aviation Standard."""
    fig = make_subplots(
        rows=4, cols=1, shared_xaxes=True, 
        vertical_spacing=0.08, # Jarak diperlebar agar tidak semrawut
        subplot_titles=(
            "1. Profil Suhu Udara Maksimum, Rata-rata, & Minimum", 
            "2. Profil Kelembapan Relatif (RH)", 
            "3. Distribusi Jarak Pandang (Visibility)", 
            "4. Tinggi Dasar Awan (Height of Base of Lowest Cloud / HS)"
        )
    )
    
    # ROW 1: Suhu (Warna Tegas: Merah, Jingga, Biru)
    if data['t'] is not None:
        df = data['t'].sort_values('Datetime')
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['MAX_VAL'], mode='lines+markers', name='T Max', line=dict(color='#d62728', width=2)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['DAILY_MEAN'], mode='lines+markers', name='T Mean', line=dict(color='#ff7f0e', width=2, dash='dot')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['MIN_VAL'], mode='lines+markers', name='T Min', line=dict(color='#1f77b4', width=2)), row=1, col=1)

    # ROW 2: RH (Warna Tegas: Hijau Tua, Hijau Muda, Cokelat)
    if data['rh'] is not None:
        df = data['rh'].sort_values('Datetime')
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['MAX_VAL'], mode='lines+markers', name='RH Max', line=dict(color='#2ca02c', width=2)), row=2, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['DAILY_MEAN'], mode='lines+markers', name='RH Mean', line=dict(color='#98df8a', width=2, dash='dot')), row=2, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['MIN_VAL'], mode='lines+markers', name='RH Min', line=dict(color='#8c564b', width=2)), row=2, col=1)

    # ROW 3: Visibility (Gradasi Biru Elegan)
    if data['vis'] is not None:
        df = data['vis'].sort_values('Datetime')
        cols = [c for c in df.columns if '<' in str(c) or '>' in str(c)]
        colors_vis = px.colors.sequential.Blues[1:] # Hindari warna terlalu putih
        for i, c in enumerate(cols):
            color = colors_vis[i % len(colors_vis)]
            fig.add_trace(go.Bar(x=df['Datetime'], y=df[c], name=f'Vis {c}', marker_color=color), row=3, col=1)

    # ROW 4: HS (Gradasi Abu-abu/Hitam Taktis)
    if data['hs'] is not None:
        df = data['hs'].sort_values('Datetime')
        cols = [c for c in df.columns if '<' in str(c)]
        colors_hs = px.colors.sequential.Greys[2:] 
        for i, c in enumerate(cols):
            color = colors_hs[i % len(colors_hs)]
            fig.add_trace(go.Bar(x=df['Datetime'], y=df[c], name=f'HS {c}', marker_color=color), row=4, col=1)
            
    # Penyesuaian Sumbu dan Layout untuk Tampilan Bersih
    fig.update_yaxes(title_text="Suhu (°C)", row=1, col=1)
    fig.update_yaxes(title_text="RH (%)", row=2, col=1)
    fig.update_yaxes(title_text="Frekuensi (%)", row=3, col=1)
    fig.update_yaxes(title_text="Frekuensi (%)", row=4, col=1)

    fig.update_layout(
        height=1300, # Diperbesar agar grafik tidak sesak
        barmode='stack', 
        hovermode='x unified',
        plot_bgcolor="rgba(240, 242, 246, 0.5)", # Warna latar abu-abu sangat muda agar rapi
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, bgcolor='rgba(255,255,255,0.8)'),
        margin=dict(l=40, r=20, t=80, b=40)
    )
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='white', tickformat="%b")
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='white')
    return fig

def render_wind_dashboard(df_wind):
    if df_wind is None:
        st.error("⚠️ Data Angin gagal dimuat atau belum tersedia.")
        return
        
    df_wind['Season'] = df_wind['Datetime'].dt.month.apply(get_season)
    
    dir_map = parse_wind_sectors(df_wind.columns)
    dir_cols = list(dir_map.keys())
    speed_cols = [c for c in df_wind.columns if '-' in str(c) or '>' in str(c)]
    speed_cols = [c for c in speed_cols if c not in dir_cols]
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Pola Arah Angin Musiman")
        if dir_cols:
            seasonal_dir = df_wind.groupby('Season')[dir_cols].mean().reset_index()
            melt_dir = seasonal_dir.melt(id_vars='Season', value_vars=dir_cols, var_name='Arah', value_name='Frekuensi (%)')
            fig_dir = px.bar(melt_dir, x='Season', y='Frekuensi (%)', color='Arah', barmode='group', color_discrete_sequence=px.colors.qualitative.Prism)
            st.plotly_chart(fig_dir, use_container_width=True)
        
    with col2:
        st.subheader("Pola Kecepatan Angin Musiman")
        if speed_cols:
            seasonal_speed = df_wind.groupby('Season')[speed_cols].mean().reset_index()
            melt_speed = seasonal_speed.melt(id_vars='Season', value_vars=speed_cols, var_name='Kecepatan (Knot)', value_name='Frekuensi (%)')
            fig_speed = px.bar(melt_speed, x='Season', y='Frekuensi (%)', color='Kecepatan (Knot)', barmode='group', color_discrete_sequence=px.colors.sequential.Teal)
            st.plotly_chart(fig_speed, use_container_width=True)
            
    st.markdown("---")
    st.subheader("Windrose Musiman Operasional")
    seasons = ['DJF', 'MAM', 'JJA', 'SON']
    cols_wr = st.columns(4)
    for i, season in enumerate(seasons):
        season_data = df_wind[df_wind['Season'] == season]
        if not season_data.empty and dir_cols:
            r_vals = season_data[dir_cols].mean().values
            theta_vals = [dir_map[c] for c in dir_cols]
            
            fig_wr = go.Figure(go.Barpolar(r=r_vals, theta=theta_vals, name=season, marker_color='#2c3e50', opacity=0.8))
            fig_wr.update_layout(
                title=f"Musim: {season}", 
                polar=dict(angularaxis=dict(direction="clockwise", rotation=90)), 
                margin=dict(t=40, b=20, l=20, r=20)
            )
            cols_wr[i].plotly_chart(fig_wr, use_container_width=True)

# ==========================================
# 5. MAIN UI COMMAND CENTER
# ==========================================
def main():
    st.title("✈️ Dashboard Aerodrome Climatological Summary (ACS)")
    st.markdown("**Sistem Informasi Cuaca Terintegrasi - Operasional Pangkalan Militer (2021-2025)**")
    
    with st.spinner("Menyelaraskan data klimatologi..."):
        dataset = load_data()

    tab1, tab2, tab3 = st.tabs(["📊 Meteogram Integrasi", "🧭 Analisis Angin", "📁 Inspeksi Data (Debug)"])
    
    with tab1:
        st.subheader("Meteogram Multi-Parameter Terpadu")
        st.info("Kursor dapat diarahkan ke grafik untuk melihat nilai spesifik (Tooltip). Klik legenda untuk menyembunyikan/menampilkan parameter tertentu.")
        fig_main = plot_main_meteogram(dataset)
        st.plotly_chart(fig_main, use_container_width=True)
        
    with tab2:
        render_wind_dashboard(dataset['wind'])
        
    with tab3:
        st.subheader("Status Data Terekstrak")
        option = st.selectbox("Pilih Parameter untuk Inspeksi:", list(dataset.keys()), format_func=lambda x: x.upper())
        if dataset[option] is not None:
            st.dataframe(dataset[option], use_container_width=True)
        else:
            st.error(f"❌ Data {option.upper()} gagal diekstrak. Pastikan file tersedia.")

if __name__ == "__main__":
    main()
