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

def clean_dataframe(df):
    """Fungsi Tahan Banting: Membuang kolom NaN, None, atau Unnamed dari Excel."""
    # Buang kolom yang header-nya bernilai null/NaN
    df = df.loc[:, df.columns.notnull()]
    # Buang kolom yang mengandung kata 'Unnamed' (hasil generate otomatis Pandas)
    df = df.loc[:, ~df.columns.astype(str).str.contains('Unnamed', case=False)]
    return df

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
    
    # 1. Dataset HS (Sekarang dimasukkan ke grafik)
    try:
        df = pd.read_excel("hs_2021_2025.xlsx")
        df = clean_dataframe(df)
        df['Datetime'] = df['DATE'].apply(map_month_to_datetime)
        data['hs'] = df.sort_values('Datetime')
    except Exception: data['hs'] = None
        
    # 2. Dataset RH
    try:
        df = pd.read_excel("rh_max_min_2021_2025.xlsx")
        cols = df.columns.tolist()
        cols[0] = 'DATE'
        if len(cols) >= 3:
            cols[-3], cols[-2], cols[-1] = 'DAILY_MEAN', 'RH_MAX', 'RH_MIN'
        df.columns = cols
        df = df.drop(0).reset_index(drop=True)
        df = clean_dataframe(df)
        for c in ['DAILY_MEAN', 'RH_MAX', 'RH_MIN']: df[c] = pd.to_numeric(df[c], errors='coerce')
        df['Datetime'] = df['DATE'].apply(map_month_to_datetime)
        data['rh'] = df.sort_values('Datetime')
    except Exception: data['rh'] = None
        
    # 3. Dataset Temperature
    try:
        df = pd.read_excel("t_max_min_2021_2025.xlsx")
        cols = df.columns.tolist()
        cols[0] = 'DATE'
        if len(cols) >= 3:
            cols[-3], cols[-2], cols[-1] = 'DAILY_MEAN', 'T_MAX', 'T_MIN'
        df.columns = cols
        df = df.drop(0).reset_index(drop=True)
        df = clean_dataframe(df)
        for c in ['DAILY_MEAN', 'T_MAX', 'T_MIN']: df[c] = pd.to_numeric(df[c], errors='coerce')
        df['Datetime'] = df['DATE'].apply(map_month_to_datetime)
        data['t'] = df.sort_values('Datetime')
    except Exception: data['t'] = None
        
    # 4. Dataset Visibility
    try:
        df = pd.read_excel("visibility_2021_2025.xlsx")
        df = clean_dataframe(df)
        df['Datetime'] = df['DATE'].apply(map_month_to_datetime)
        data['vis'] = df.sort_values('Datetime')
    except Exception: data['vis'] = None
        
    # 5. Dataset Wind Direction
    try:
        df_raw = pd.read_excel("WINDDIRECTION_2021_2025.xlsx")
        # Cari baris yang benar-benar berisi header untuk mencegah None
        header_idx = df_raw[df_raw.astype(str).apply(lambda x: x.str.contains('DATE', case=False, na=False)).any(axis=1)].index
        if len(header_idx) > 0:
            idx = header_idx[0]
            df = df_raw.iloc[idx+1:].reset_index(drop=True)
            df.columns = df_raw.iloc[idx].tolist()
        else:
            df = df_raw # fallback

        df = clean_dataframe(df) # MENGHANCURKAN KOLOM NONE/NAN!
        df['Datetime'] = df['DATE'].apply(map_month_to_datetime)
        df = df.sort_values('Datetime')
        
        for c in df.columns:
            if c not in ['DATE', 'DIRECTION', 'Datetime']:
                df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
        data['wind'] = df
    except Exception as e: 
        st.error(f"Error Wind Data: {e}")
        data['wind'] = None

    return data

# ==========================================
# 4. METEOGRAM & VISUALIZATION 
# ==========================================
def plot_main_meteogram(data):
    """Meteogram 4 Baris: T, RH, VIS, dan HS."""
    fig = make_subplots(
        rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.08,
        subplot_titles=("1. Fluktuasi Suhu (°C)", "2. Kelembapan Relatif (%)", "3. Distribusi Jarak Pandang (%)", "4. Tinggi Dasar Awan / HS (%)")
    )
    
    # ROW 1: Suhu
    if data['t'] is not None:
        df = data['t']
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['T_MAX'], mode='lines+markers', name='T Max', line=dict(color='#d62728')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['DAILY_MEAN'], mode='lines+markers', name='T Mean', line=dict(color='#ff7f0e')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['T_MIN'], mode='lines+markers', name='T Min', line=dict(color='#1f77b4')), row=1, col=1)

    # ROW 2: RH
    if data['rh'] is not None:
        df = data['rh']
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['RH_MAX'], mode='lines+markers', name='RH Max', line=dict(color='#2ca02c')), row=2, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['DAILY_MEAN'], mode='lines+markers', name='RH Mean', line=dict(color='#98df8a')), row=2, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['RH_MIN'], mode='lines+markers', name='RH Min', line=dict(color='#8c564b')), row=2, col=1)

    # ROW 3: Visibility
    if data['vis'] is not None:
        df = data['vis']
        cols = [c for c in df.columns if '<' in str(c) or '>' in str(c)]
        for c in cols:
            fig.add_trace(go.Bar(x=df['Datetime'], y=df[c], name=f'Vis {c}'), row=3, col=1)

    # ROW 4: HS (BARU DITAMBAHKAN)
    if data['hs'] is not None:
        df = data['hs']
        cols = [c for c in df.columns if '<' in str(c)]
        for c in cols:
            fig.add_trace(go.Bar(x=df['Datetime'], y=df[c], name=f'HS {c}'), row=4, col=1)
            
    fig.update_layout(
        height=1000, 
        barmode='stack', 
        hovermode='x unified',
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    # Merapikan Grid
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')
    return fig

def render_wind_dashboard(df_wind):
    if df_wind is None:
        st.error("⚠️ Data Angin gagal dimuat.")
        return
        
    df_wind['Season'] = df_wind['Datetime'].dt.month.apply(get_season)
    
    dir_map = parse_wind_sectors(df_wind.columns)
    dir_cols = list(dir_map.keys())
    speed_cols = [c for c in df_wind.columns if '-' in str(c) or '>' in str(c)]
    speed_cols = [c for c in speed_cols if c not in dir_cols] # Pisahkan kolom speed dan direction
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Pola Arah Angin Musiman")
        if dir_cols:
            seasonal_dir = df_wind.groupby('Season')[dir_cols].mean().reset_index()
            melt_dir = seasonal_dir.melt(id_vars='Season', value_vars=dir_cols, var_name='Arah', value_name='Frekuensi (%)')
            fig_dir = px.bar(melt_dir, x='Season', y='Frekuensi (%)', color='Arah', barmode='group')
            st.plotly_chart(fig_dir, use_container_width=True)
        else: st.warning("Format kolom arah angin tidak sesuai.")
        
    with col2:
        st.subheader("Pola Kecepatan Angin Musiman")
        if speed_cols:
            seasonal_speed = df_wind.groupby('Season')[speed_cols].mean().reset_index()
            melt_speed = seasonal_speed.melt(id_vars='Season', value_vars=speed_cols, var_name='Kecepatan (Knot)', value_name='Frekuensi (%)')
            fig_speed = px.bar(melt_speed, x='Season', y='Frekuensi (%)', color='Kecepatan (Knot)', barmode='group')
            st.plotly_chart(fig_speed, use_container_width=True)
            
    st.markdown("---")
    st.subheader("Windrose Musiman")
    seasons = ['DJF', 'MAM', 'JJA', 'SON']
    cols_wr = st.columns(4)
    for i, season in enumerate(seasons):
        season_data = df_wind[df_wind['Season'] == season]
        if not season_data.empty and dir_cols:
            r_vals = season_data[dir_cols].mean().values
            theta_vals = [dir_map[c] for c in dir_cols]
            
            fig_wr = go.Figure(go.Barpolar(r=r_vals, theta=theta_vals, name=season, marker_color='#2c3e50', opacity=0.8))
            fig_wr.update_layout(title=f"Musim: {season}", polar=dict(angularaxis=dict(direction="clockwise", rotation=90)), margin=dict(t=40, b=20, l=20, r=20))
            cols_wr[i].plotly_chart(fig_wr, use_container_width=True)

# ==========================================
# 5. MAIN UI
# ==========================================
def main():
    st.title("✈️ Dashboard Aerodrome Climatological Summary (ACS)")
    st.markdown("Sistem Informasi Cuaca Terintegrasi untuk Mendukung Operasional Pangkalan Militer (Periode Observasi 2021-2025).")
    
    with st.spinner("Memuat dan membersihkan dataset klimatologi..."):
        dataset = load_data()

    tab1, tab2, tab3 = st.tabs(["📊 Meteogram Integrasi", "🧭 Analisis Angin", "📁 Inspeksi Data Bersih"])
    
    with tab1:
        st.subheader("Meteogram Multi-Parameter Terpadu")
        fig_main = plot_main_meteogram(dataset)
        st.plotly_chart(fig_main, use_container_width=True)
        
    with tab2:
        render_wind_dashboard(dataset['wind'])
        
    with tab3:
        st.subheader("Inspeksi Data Mentah (Telah Disanitasi)")
        option = st.selectbox("Pilih Dataset:", list(dataset.keys()), format_func=lambda x: x.upper())
        if dataset[option] is not None:
            st.dataframe(dataset[option], use_container_width=True)
        else:
            st.error("Data tidak ditemukan atau format rusak.")

if __name__ == "__main__":
    main()
