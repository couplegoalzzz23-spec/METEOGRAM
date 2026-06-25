# ==========================================
# 1. IMPORTS
# ==========================================
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# ==========================================
# 2. PAGE CONFIG
# ==========================================
st.set_page_config(
    page_title="Dashboard ACS Lanud RSN", 
    layout="wide", 
    page_icon="✈️"
)

# ==========================================
# 3. HELPER & PREPROCESSING FUNCTIONS
# ==========================================
def get_season(month_num):
    """Mengklasifikasikan bulan ke dalam format musim klimatologi standar."""
    if month_num in [12, 1, 2]: return 'DJF'
    elif month_num in [3, 4, 5]: return 'MAM'
    elif month_num in [6, 7, 8]: return 'JJA'
    elif month_num in [9, 10, 11]: return 'SON'
    return 'Lainnya'

def map_month_to_datetime(month_str):
    """Mengubah string bulan menjadi representasi Datetime untuk sumbu X grafik (Tahun Base: 2021)."""
    month_map = {
        'JANUARY': 1, 'FEBRUARY': 2, 'MARCH': 3, 'APRIL': 4,
        'MAY': 5, 'JUNE': 6, 'JULY': 7, 'AUGUST': 8,
        'SEPTEMBER': 9, 'OCTOBER': 10, 'NOVEMBER': 11, 'DECEMBER': 12
    }
    m = month_map.get(str(month_str).strip().upper(), 1)
    return pd.to_datetime(f"2021-{m:02d}-01")

def parse_wind_sectors(columns):
    """Memetakan string sektor ACS menjadi representasi derajat numerik untuk polar plot/Windrose."""
    mapping = {
        '35 - 36 - 01': 0, '02 - 03 - 04': 30, '05 - 06 - 07': 60,
        '08 - 09 - 10': 90, '11 - 12 - 13': 120, '14 - 15 - 16': 150,
        '17 - 18 - 19': 180, '20 - 21 - 22': 210, '23 - 24 - 25': 240,
        '26 - 27 - 28': 270, '29 - 30 - 31': 300, '32 - 33 - 34': 330
    }
    # Membersihkan spasi (robuse space handling) untuk pencocokan akurat
    clean_mapping = {k.replace(" ", ""): v for k, v in mapping.items()}
    
    result = {}
    for col in columns:
        clean_col = str(col).replace(" ", "")
        if clean_col in clean_mapping:
            result[col] = clean_mapping[clean_col]
    return result

# ==========================================
# 4. DATA LOADING & CACHING (.XLSX)
# ==========================================
@st.cache_data
def load_data():
    """Memuat dan membersihkan 6 dataset secara defensif."""
    data = {}
    
    # 1. Dataset Kelembapan Spesifik / HS
    try:
        df = pd.read_excel("hs_2021_2025.xlsx")
        df['Datetime'] = df['DATE'].apply(map_month_to_datetime)
        data['hs'] = df.sort_values('Datetime')
    except Exception: data['hs'] = None
        
    # 2. Dataset RH Max Min
    try:
        df = pd.read_excel("rh_max_min_2021_2025.xlsx")
        cols = df.columns.tolist()
        cols[0] = 'DATE'
        if len(cols) >= 3: # Normalisasi header row dari excel
            cols[-3], cols[-2], cols[-1] = 'DAILY_MEAN', 'RH_MAX', 'RH_MIN'
        df.columns = cols
        df = df.drop(0).reset_index(drop=True)
        for c in ['DAILY_MEAN', 'RH_MAX', 'RH_MIN']:
            df[c] = pd.to_numeric(df[c], errors='coerce')
        df['Datetime'] = df['DATE'].apply(map_month_to_datetime)
        data['rh'] = df.sort_values('Datetime')
    except Exception: data['rh'] = None
        
    # 3. Dataset T Max Min
    try:
        df = pd.read_excel("t_max_min_2021_2025.xlsx")
        cols = df.columns.tolist()
        cols[0] = 'DATE'
        if len(cols) >= 3:
            cols[-3], cols[-2], cols[-1] = 'DAILY_MEAN', 'T_MAX', 'T_MIN'
        df.columns = cols
        df = df.drop(0).reset_index(drop=True)
        for c in ['DAILY_MEAN', 'T_MAX', 'T_MIN']:
            df[c] = pd.to_numeric(df[c], errors='coerce')
        df['Datetime'] = df['DATE'].apply(map_month_to_datetime)
        data['t'] = df.sort_values('Datetime')
    except Exception: data['t'] = None
        
    # 4. Dataset Temperature
    try:
        df = pd.read_excel("temperature_2021_2025.xlsx")
        df['Datetime'] = df['DATE'].apply(map_month_to_datetime)
        data['tavg'] = df.sort_values('Datetime')
    except Exception: data['tavg'] = None
        
    # 5. Dataset Visibility
    try:
        df = pd.read_excel("visibility_2021_2025.xlsx")
        df['Datetime'] = df['DATE'].apply(map_month_to_datetime)
        data['vis'] = df.sort_values('Datetime')
    except Exception: data['vis'] = None
        
    # 6. Dataset Wind Direction
    try:
        df_raw = pd.read_excel("WINDDIRECTION_2021_2025.xlsx")
        headers = df_raw.iloc[0].tolist() # Mengambil row index 0 sebagai header yang benar (sesuai gambar)
        df = df_raw.drop(0).reset_index(drop=True)
        df.columns = headers
        df['Datetime'] = df['DATE'].apply(map_month_to_datetime)
        df = df.sort_values('Datetime')
        # Konversi semua nilai frekuensi angin ke Float
        for c in df.columns:
            if c not in ['DATE', 'DIRECTION', 'Datetime']:
                df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
        data['wind'] = df
    except Exception: data['wind'] = None

    return data

# ==========================================
# 5. PLOTTING FUNCTIONS
# ==========================================
def plot_main_meteogram(data):
    """Membuat Meteogram interaktif gabungan parameter (Suhu, RH, Visibility)."""
    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.1,
        subplot_titles=("Suhu (°C)", "Kelembapan Relatif (%)", "Distribusi Jarak Pandang (%)")
    )
    
    # 1. Plot Suhu
    if data['t'] is not None:
        df_t = data['t']
        fig.add_trace(go.Scatter(x=df_t['Datetime'], y=df_t['T_MAX'], mode='lines+markers', name='T Max', line=dict(color='red')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_t['Datetime'], y=df_t['DAILY_MEAN'], mode='lines+markers', name='T Mean', line=dict(color='orange')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_t['Datetime'], y=df_t['T_MIN'], mode='lines+markers', name='T Min', line=dict(color='blue')), row=1, col=1)

    # 2. Plot RH
    if data['rh'] is not None:
        df_rh = data['rh']
        fig.add_trace(go.Scatter(x=df_rh['Datetime'], y=df_rh['RH_MAX'], mode='lines+markers', name='RH Max', line=dict(color='darkgreen')), row=2, col=1)
        fig.add_trace(go.Scatter(x=df_rh['Datetime'], y=df_rh['DAILY_MEAN'], mode='lines+markers', name='RH Mean', line=dict(color='green')), row=2, col=1)
        fig.add_trace(go.Scatter(x=df_rh['Datetime'], y=df_rh['RH_MIN'], mode='lines+markers', name='RH Min', line=dict(color='lightgreen')), row=2, col=1)

    # 3. Plot Visibility (Stacked Bar)
    if data['vis'] is not None:
        df_vis = data['vis']
        cols_to_plot = [c for c in df_vis.columns if '<' in c or '>' in c]
        for c in cols_to_plot:
            fig.add_trace(go.Bar(x=df_vis['Datetime'], y=df_vis[c], name=f'Vis {c}'), row=3, col=1)
            
    fig.update_layout(height=800, title_text="Meteogram Multi-Parameter", barmode='stack', hovermode='x unified')
    return fig

def render_wind_dashboard(df_wind):
    """Merender tab khusus Klimatologi Angin."""
    if df_wind is None:
        st.error("⚠️ Data WINDDIRECTION_2021_2025.xlsx gagal dimuat. Periksa format atau keberadaan file.")
        return
        
    df_wind['Month_Num'] = df_wind['Datetime'].dt.month
    df_wind['Season'] = df_wind['Month_Num'].apply(get_season)
    
    dir_map = parse_wind_sectors(df_wind.columns)
    dir_cols = list(dir_map.keys())
    speed_cols = [c for c in ['1 - 5', '6 - 10', '11 - 15', '16 - 20', '21 - 25', '26 - 30', '31 - 35', '36 - 45', '> 45'] if c in df_wind.columns]
    
    # Bagian 1 & 2: Pola Musiman Bar Chart
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Pola Arah Angin Musiman")
        seasonal_dir = df_wind.groupby('Season')[dir_cols].mean().reset_index()
        melt_dir = seasonal_dir.melt(id_vars='Season', value_vars=dir_cols, var_name='Arah', value_name='Frekuensi (%)')
        fig_dir = px.bar(melt_dir, x='Season', y='Frekuensi (%)', color='Arah', barmode='group')
        st.plotly_chart(fig_dir, use_container_width=True)
        
    with col2:
        st.subheader("Pola Kecepatan Angin Musiman")
        seasonal_speed = df_wind.groupby('Season')[speed_cols].mean().reset_index()
        melt_speed = seasonal_speed.melt(id_vars='Season', value_vars=speed_cols, var_name='Kecepatan (Knot)', value_name='Frekuensi (%)')
        fig_speed = px.bar(melt_speed, x='Season', y='Frekuensi (%)', color='Kecepatan (Knot)', barmode='group')
        st.plotly_chart(fig_speed, use_container_width=True)
        
    # Bagian 3: Windrose Musiman
    st.markdown("---")
    st.subheader("Windrose Musiman (Mawar Angin)")
    seasons = ['DJF', 'MAM', 'JJA', 'SON']
    cols_wr = st.columns(4)
    for i, season in enumerate(seasons):
        season_data = seasonal_dir[seasonal_dir['Season'] == season]
        if not season_data.empty:
            r_vals = season_data[dir_cols].values[0]
            theta_vals = [dir_map[c] for c in dir_cols]
            
            fig_wr = go.Figure(go.Barpolar(
                r=r_vals, theta=theta_vals, name=season, marker_color='royalblue', opacity=0.8
            ))
            # Menyesuaikan arah Utara (0) di atas dan putaran searah jarum jam
            fig_wr.update_layout(
                title=f"Musim: {season}",
                polar=dict(angularaxis=dict(direction="clockwise", rotation=90)),
                margin=dict(t=40, b=20, l=20, r=20)
            )
            cols_wr[i].plotly_chart(fig_wr, use_container_width=True)
            
    # Bagian 4: Meteogram Khusus Angin
    st.markdown("---")
    st.subheader("Meteogram Bulanan (Distribusi Angin)")
    fig_meteo = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1, subplot_titles=("Frekuensi Kecepatan Angin (%)", "Frekuensi Arah Angin (%)"))
    
    for sc in speed_cols: fig_meteo.add_trace(go.Bar(x=df_wind['DATE'], y=df_wind[sc], name=sc), row=1, col=1)
    for dc in dir_cols: fig_meteo.add_trace(go.Bar(x=df_wind['DATE'], y=df_wind[dc], name=dc), row=2, col=1)
        
    fig_meteo.update_layout(height=600, barmode='stack', hovermode='x unified')
    st.plotly_chart(fig_meteo, use_container_width=True)


# ==========================================
# 6. MAIN UI / LAYOUT
# ==========================================
def main():
    st.title("✈️ Dashboard Aerodrome Climatological Summary (ACS)")
    st.markdown("Sistem Informasi Cuaca Terintegrasi untuk Mendukung Operasional Pangkalan Militer Roesmin Nurjadin (Periode Observasi 2021-2025).")
    
    # Eksekusi Cache Data
    with st.spinner("Memuat dataset klimatologi..."):
        dataset = load_data()
        
    # Memeriksa peringatan dataset
    missing_files = [k for k, v in dataset.items() if v is None]
    if missing_files:
        st.warning(f"⚠️ Terdapat dataset yang gagal dimuat: {', '.join(missing_files).upper()}. Pastikan nama file .xlsx di GitHub sesuai.")

    # Membuat Sistem Tab
    tab1, tab2, tab3 = st.tabs(["📊 Meteogram Utama", "🧭 Dashboard Angin", "📁 Data Tabular Mentah"])
    
    # Tab 1: Meteogram Multi-Parameter
    with tab1:
        st.subheader("Meteogram Integrasi")
        fig_main = plot_main_meteogram(dataset)
        st.plotly_chart(fig_main, use_container_width=True)
        
    # Tab 2: Dashboard Angin Spesifik
    with tab2:
        render_wind_dashboard(dataset['wind'])
        
    # Tab 3: Data Viewer / Filter
    with tab3:
        st.subheader("Inspeksi Data Mentah")
        option = st.selectbox("Pilih Dataset untuk diinspeksi:", list(dataset.keys()), format_func=lambda x: x.upper())
        if dataset[option] is not None:
            st.dataframe(dataset[option], use_container_width=True)
        else:
            st.info("Data tidak tersedia.")

if __name__ == "__main__":
    main()
