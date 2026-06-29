import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import io

# ==========================================
# 1. PAGE CONFIGURATION & CSS (MUST BE FIRST)
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
# 3. DATA VALIDATION (QA ENGINE)
# ==========================================
def validate_dataset(df: pd.DataFrame, filename: str) -> bool:
    issues = []
    if df.empty: issues.append("Dataset kosong.")
    if df.isnull().values.any(): issues.append(f"Terdapat {df.isnull().sum().sum()} Missing Values.")
    if df.duplicated().any(): issues.append(f"Terdapat {df.duplicated().sum()} Duplicated Rows.")
    
    if issues:
        st.warning(f"⚠️ DQC Alert [{filename}]: {' | '.join(issues)}")
        return False
    return True

# ==========================================
# 4. DATA LOADER ENGINE (PERBAIKAN: '.' PATH)
# ==========================================
@st.cache_data(show_spinner=False)
def load_all_data(data_dir='.'): # Diubah dari 'data' menjadi '.'
    """Memuat dan menstandarisasi seluruh dataset ke dalam memori."""
    datasets = {}
    for key, filename in DATA_FILES.items():
        filepath = os.path.join(data_dir, filename)
        if not os.path.exists(filepath):
            datasets[key] = pd.DataFrame() 
            continue
            
        try:
            df = pd.read_excel(filepath)
            
            # Auto-detect month column
            month_col = next((col for col in df.columns if str(col).strip().lower() in ['month', 'bulan']), None)
            
            if month_col:
                df = df.set_index(month_col)
                df.index = df.index.astype(str).str.strip()
                valid_months = [m for m in MONTHS_ORDER if m in df.index]
                if valid_months:
                    df = df.reindex(valid_months).reset_index()
                    df.rename(columns={'index': 'Bulan', month_col: 'Bulan'}, inplace=True)
            
            validate_dataset(df, filename)
            datasets[key] = df
        except Exception as e:
            st.error(f"Error memproses {filename}: {str(e)}")
            datasets[key] = pd.DataFrame()
            
    return datasets

# ... (Fungsi 5, 6, dan 7 dibiarkan sama seperti skrip asli Anda) ...
# [Paste sisa fungsi visualisasi dan insight Anda di sini]

# ==========================================
# 8. MAIN UI & ROUTING ENGINE
# ==========================================
def main():
    # Menggunakan '.' untuk direktori saat ini
    datasets = load_all_data('.') 
    
    # Sidebar
    st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/8/8e/Logo_BMKG.png", width=70)
    st.sidebar.title("☁️ ACS Navigator")
    
    # ... (Sisa kode main Anda tetap sama) ...
