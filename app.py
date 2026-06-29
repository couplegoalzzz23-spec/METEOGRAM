
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

# ==========================================
# 1. PAGE CONFIGURATION & CSS
# ==========================================
st.set_page_config(
    page_title="ACS Aviation Climatology",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
        html, body, [class*="css"]  { font-family: 'Inter', sans-serif; }
        .main .block-container { padding-top: 2rem; padding-bottom: 2rem;}
        .bmkg-header {
            background: linear-gradient(135deg, #0B3C5D 0%, #328CC1 100%);
            padding: 25px; border-radius: 12px; color: white; margin-bottom: 25px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .bmkg-header h1 { margin: 0; font-size: 2.2rem; font-weight: 700; letter-spacing: -0.5px;}
        .bmkg-header p { margin: 8px 0 0 0; font-size: 1.1rem; opacity: 0.9; }
        div[data-testid="stMetricValue"] { color: #328CC1; font-weight: 700; font-size: 28px;}
        div[data-testid="stMetricLabel"] { font-weight: 600; color: #4B5563;}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. CONSTANTS & CONFIGURATION
# ==========================================
MONTHS_ORDER = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des']

COLORS = {
    'primary': '#0B3C5D', 'secondary': '#328CC1', 'accent': '#D9B310',
    'danger': '#E53935', 'warning': '#FB8C00', 'bg_light': '#F8FAFC'
}

DATA_FILES = {
    'hs': 'rekap_hs_2021_2025.xlsx',
    'rh_maxmin': 'rekap_rh_max_min_2021_2025.xlsx',
    'temp_maxmin': 'rekap_temp_max_min_2021_2025.xlsx',
    'temp_freq': 'rekap_temperature_2021_2025.xlsx',
    'vis': 'rekap_visibility_2021_2025.xlsx',
    'wind': 'rekap_wind_2021_2025.xlsx'
}

# ==========================================
# 4. DATA LOADER ENGINE (PERBAIKAN: path='.')
# ==========================================
@st.cache_data(show_spinner=False)
def load_all_data(data_dir='.'): 
    datasets = {}
    for key, filename in DATA_FILES.items():
        filepath = os.path.join(data_dir, filename)
        if not os.path.exists(filepath):
            datasets[key] = pd.DataFrame() 
            continue
            
        try:
            # Menggunakan engine openpyxl untuk kompatibilitas
            df = pd.read_excel(filepath, engine='openpyxl')
            
            # Auto-detect month column
            month_col = next((col for col in df.columns if str(col).strip().lower() in ['month', 'bulan']), None)
            
            if month_col:
                df = df.set_index(month_col)
                df.index = df.index.astype(str).str.strip()
                valid_months = [m for m in MONTHS_ORDER if m in df.index]
                if valid_months:
                    df = df.reindex(valid_months).reset_index()
                    df.rename(columns={'index': 'Bulan', month_col: 'Bulan'}, inplace=True)
            
            datasets[key] = df
        except Exception as e:
            datasets[key] = pd.DataFrame()
            
    return datasets

# ==========================================
# MAIN APP
# ==========================================
def main():
    datasets = load_all_data('.') 
    
    st.sidebar.title("☁️ ACS Navigator")
    menu = st.sidebar.radio("Pilih Analisis:", [
        "🏠 Home", "🌡️ Temperature Max Min", "📊 Temperature Frequency", 
        "💧 Relative Humidity", "🌫️ Visibility", "☁️ Cloud Base (HS)", 
        "🧭 Wind", "🔄 Cross Parameter Analysis", "ℹ️ Dataset Metadata"
    ])

    if menu == "🏠 Home":
        st.markdown("<h1>Aviation Climatological Summary</h1>", unsafe_allow_html=True)
        st.write("Dashboard operasional klimatologi penerbangan.")
    
    # Tambahkan logika routing lainnya di sini sesuai file asli
    # ... (skema routing dipertahankan)

if __name__ == "__main__":
    main()
