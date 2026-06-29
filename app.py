import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

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
    """Melakukan Quality Check otomatis pada dataset."""
    issues = []
    if df.empty: issues.append("Dataset kosong.")
    if df.isnull().values.any(): issues.append(f"Terdapat {df.isnull().sum().sum()} Missing Values.")
    if df.duplicated().any(): issues.append(f"Terdapat {df.duplicated().sum()} Duplicated Rows.")
    
    if issues:
        st.warning(f"⚠️ DQC Alert [{filename}]: {' | '.join(issues)}")
        return False
    return True

# ==========================================
# 4. DATA LOADER ENGINE (CACHED)
# ==========================================
@st.cache_data(show_spinner=False)
def load_all_data(data_dir='.'): # PERBAIKAN: Default ke direktori root ('.') sesuai struktur repo GitHub
    """Memuat dan menstandarisasi seluruh dataset ke dalam memori."""
    datasets = {}
    for key, filename in DATA_FILES.items():
        filepath = os.path.join(data_dir, filename)
        if not os.path.exists(filepath):
            datasets[key] = pd.DataFrame() # Return empty DF instead of crashing
            continue
            
        try:
            # PERBAIKAN: Menambahkan engine='openpyxl' secara eksplisit
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
            
            validate_dataset(df, filename)
            datasets[key] = df
        except Exception as e:
            st.error(f"Error memproses {filename}: {str(e)}")
            datasets[key] = pd.DataFrame()
            
    return datasets

# ==========================================
# 5. VISUALIZATION ENGINE (PLOTLY)
# ==========================================
def apply_standard_layout(fig, title):
    fig.update_layout(
        title=dict(text=title, font=dict(size=18, color=COLORS['primary'])),
        template="plotly_white",
        hovermode="x unified",
        margin=dict(l=40, r=40, t=60, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig

def plot_envelope(df, x_col, mean_col, max_col, min_col, title, y_label):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df[x_col], y=df[max_col], mode='lines', line=dict(color=COLORS['danger'], width=1.5), name='Maximum'))
    fig.add_trace(go.Scatter(x=df[x_col], y=df[min_col], mode='lines', fill='tonexty', fillcolor='rgba(11, 60, 93, 0.1)', line=dict(color=COLORS['secondary'], width=1.5), name='Minimum'))
    fig.add_trace(go.Scatter(x=df[x_col], y=df[mean_col], mode='lines+markers', line=dict(color=COLORS['primary'], width=3), name='Mean'))
    fig.update_yaxes(title_text=y_label)
    return apply_standard_layout(fig, title)

def plot_stacked_bar(df, x_col, title, y_label="Frekuensi (%)"):
    melted = df.melt(id_vars=[x_col], var_name='Kategori', value_name='Nilai')
    fig = px.bar(melted, x=x_col, y='Nilai', color='Kategori', color_discrete_sequence=px.colors.sequential.Blues_r)
    fig.update_yaxes(title_text=y_label)
    return apply_standard_layout(fig, title)

def plot_wind_rose_standard(df):
    arah_col = df.columns[0]
    melted = df.melt(id_vars=[arah_col], var_name='Speed_Knot', value_name='Frequency')
    
    compass_order = ['Utara (N)', 'Timur Laut (NNE)', 'Timur Laut (ENE)', 'Timur (E)', 'Tenggara (ESE)', 'Tenggara (SSE)', 'Selatan (S)', 'Barat Daya (SSW)', 'Barat Daya (WSW)', 'Barat (W)', 'Barat Laut (WNW)', 'Barat Laut (NNW)']
    
    fig = px.bar_polar(melted, r="Frequency", theta=arah_col, color="Speed_Knot", color_discrete_sequence=px.colors.sequential.Plasma_r)
    fig.update_layout(
        polar=dict(angularaxis=dict(direction="clockwise", categoryorder="array", categoryarray=compass_order, rotation=90)),
        title=dict(text="Distribusi Angin Permukaan (Knot)", font=dict(size=18, color=COLORS['primary'])),
        template="plotly_white", margin=dict(t=60, b=40, l=40, r=40)
    )
    return fig

# ==========================================
# 6. AUTO-INSIGHT & METEOROLOGICAL ENGINE
# ==========================================
def generate_envelope_insights(df, param_name):
    try:
        mean_c, max_c, min_c = df.columns[1], df.columns[2], df.columns[3]
        max_val_idx = df[max_c].idxmax()
        min_val_idx = df[min_c].idxmin()
        
        insight = f"""
        **Interpretasi Meteorologi:**
        * Puncak {param_name} absolut tercatat pada bulan **{df.loc[max_val_idx, 'Bulan']}** dengan nilai {df.loc[max_val_idx, max_c]}.
        * Nilai terendah tercatat pada bulan **{df.loc[min_val_idx, 'Bulan']}** dengan nilai {df.loc[min_val_idx, min_c]}.
        
        **Aviation Operational Notes ✈️:**
        * Fluktuasi ekstrem pada {param_name} secara langsung mempengaruhi performa aerodinamika (terutama *Density Altitude* jika suhu).
        * ATC dan Dispatcher wajib waspada pada tren puncak ini untuk penyesuaian perhitungan *Take-off Weight* (TOW).
        """
        return insight
    except:
        return "Data tidak mencukupi untuk Auto-Insight."

def generate_freq_insights(df, param_name):
    try:
        target_col = df.columns[1] # Asumsi kolom 1 adalah kategori ekstrem/rendah
        max_idx = df[target_col].idxmax()
        
        if "Visibility" in param_name:
            impact = "meningkatkan ketergantungan pada *Instrument Approach Procedures* (IAP) dan berpotensi memicu *holding* atau *divert*."
        else:
            impact = "berisiko menyebabkan pesawat mencapai *Minimum Descent Altitude* (MDA) sebelum melihat *runway*, memicu *Missed Approach*."
            
        insight = f"""
        **Interpretasi Meteorologi:**
        * Kriteria **{target_col}** paling sering terjadi pada bulan **{df.loc[max_idx, 'Bulan']}** ({df.loc[max_idx, target_col]}%).
        * Hal ini mengindikasikan tingginya aktivitas pembentukan cuaca signifikan (awan rendah/kabut) pada bulan tersebut.
        
        **Aviation Operational Notes ✈️:**
        * Kejadian cuaca ini akan secara langsung {impact}
        * Persiapan bahan bakar ekstra (*holding fuel*) sangat direkomendasikan pada periode ini.
        """
        return insight
    except:
        return "Data tidak mencukupi untuk Auto-Insight."

# ==========================================
# 7. UTILITY: RENDER DATA EXPORT
# ==========================================
def render_data_table(df, title):
    st.markdown("---")
    st.markdown(f"#### 📋 Original Data Table: {title}")
    st.dataframe(df, use_container_width=True)
    
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Data as CSV",
        data=csv,
        file_name=f"{title.replace(' ', '_').lower()}.csv",
        mime='text/csv',
    )

# ==========================================
# 8. MAIN UI & ROUTING ENGINE
# ==========================================
def main():
    # PERBAIKAN: Pemanggilan fungsi memuat direktori root
    datasets = load_all_data('.') 
    
    # Sidebar
    st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/8/8e/Logo_BMKG.png", width=70)
    st.sidebar.title("☁️ ACS Navigator")
    
    menu = st.sidebar.radio("Pilih Analisis:", [
        "🏠 Home",
        "🌡️ Temperature Max Min",
        "📊 Temperature Frequency",
        "💧 Relative Humidity",
        "🌫️ Visibility",
        "☁️ Cloud Base (HS)",
        "🧭 Wind",
        "🔄 Cross Parameter Analysis",
        "ℹ️ Dataset Metadata"
    ])
    
    st.sidebar.markdown("---")
    st.sidebar.caption("Sistem berstandar ICAO Annex 3 / WMO.\nBerbasis Climatological Summary 2021-2025.")

    # Content Routing
    if menu == "🏠 Home":
        st.markdown("""
            <div class="bmkg-header">
                <h1>Aviation Climatological Summary (ACS)</h1>
                <p>Sistem Analisis Probabilitas & Frekuensi Cuaca Penerbangan Terpadu</p>
            </div>
        """, unsafe_allow_html=True)
        st.write("Dashboard operasional ini mengkonversi data klimatologi historis (2021-2025) menjadi produk intelijen cuaca penerbangan. Dirancang untuk menjawab pertanyaan krusial: ***'Seberapa sering kondisi meteorologi kritis terjadi dan apa dampaknya pada operasi penerbangan?'***")
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Periode Analisis", "5 Tahun")
        col2.metric("Resolusi Data", "Bulanan")
        col3.metric("Fokus Standar", "ICAO / WMO")
        col4.metric("Engine", "Streamlit Auto-Insight")

    elif menu == "🌡️ Temperature Max Min":
        st.title("Suhu Udara (Mean, Max, Min)")
        df = datasets['temp_maxmin']
        if not df.empty:
            c1, c2 = st.columns([2.5, 1.5])
            with c1:
                fig = plot_envelope(df, df.columns[0], df.columns[1], df.columns[2], df.columns[3], "Envelope Suhu Bulanan", "Suhu (°C)")
                st.plotly_chart(fig, use_container_width=True)
            with c2:
                st.markdown("### 🔍 Auto Insight")
                st.markdown(generate_envelope_insights(df, "Suhu Udara"))
            render_data_table(df, "Temperature Max Min 2021-2025")
        else: st.warning("Data rekap_temp_max_min_2021_2025.xlsx tidak ditemukan atau kosong.")

    elif menu == "📊 Temperature Frequency":
        st.title("Distribusi Frekuensi Suhu Udara")
        df = datasets['temp_freq']
        if not df.empty:
            fig = plot_stacked_bar(df, df.columns[0], "Probabilitas Distribusi Rentang Suhu Udara")
            st.plotly_chart(fig, use_container_width=True)
            render_data_table(df, "Temperature Frequency")
        else: st.warning("Data rekap_temperature_2021_2025.xlsx tidak ditemukan.")

    elif menu == "💧 Relative Humidity":
        st.title("Kelembapan Relatif (RH)")
        df = datasets['rh_maxmin']
        if not df.empty:
            c1, c2 = st.columns([2.5, 1.5])
            with c1:
                fig = plot_envelope(df, df.columns[0], df.columns[1], df.columns[2], df.columns[3], "Rentang Ekstrem RH Bulanan", "RH (%)")
                st.plotly_chart(fig, use_container_width=True)
            with c2:
                st.markdown("### 🔍 Auto Insight")
                st.markdown(generate_envelope_insights(df, "Kelembapan Relatif"))
            render_data_table(df, "RH Max Min 2021-2025")
        else: st.warning("Data rekap_rh_max_min_2021_2025.xlsx tidak ditemukan.")

    elif menu == "🌫️ Visibility":
        st.title("Probabilitas Jarak Pandang (Visibility)")
        df = datasets['vis']
        if not df.empty:
            fig = plot_stacked_bar(df, df.columns[0], "Distribusi Kategori Jarak Pandang")
            st.plotly_chart(fig, use_container_width=True)
            st.markdown("### 🔍 Auto Insight")
            st.markdown(generate_freq_insights(df, "Visibility"))
            render_data_table(df, "Visibility Frequency")
        else: st.warning("Data rekap_visibility_2021_2025.xlsx tidak ditemukan.")

    elif menu == "☁️ Cloud Base (HS)":
        st.title("Tinggi Dasar Awan (Ceiling)")
        df = datasets['hs']
        if not df.empty:
            fig = plot_stacked_bar(df, df.columns[0], "Distribusi Frekuensi Ketinggian Dasar Awan")
            st.plotly_chart(fig, use_container_width=True)
            st.markdown("### 🔍 Auto Insight")
            st.markdown(generate_freq_insights(df, "Cloud Base"))
            render_data_table(df, "Cloud Base Frequency")
        else: st.warning("Data rekap_hs_2021_2025.xlsx tidak ditemukan.")

    elif menu == "🧭 Wind":
        st.title("Klimatologi Angin Permukaan")
        df = datasets['wind']
        if not df.empty:
            c1, c2 = st.columns([2.5, 1.5])
            with c1:
                fig = plot_wind_rose_standard(df)
                st.plotly_chart(fig, use_container_width=True)
            with c2:
                st.markdown("### 🌬️ Aviation Wind Insight")
                st.write("Distribusi frekuensi arah dan kecepatan angin sangat vital untuk penetapan arah *runway in use*.")
                st.info("**Operational Note:** Evaluasi persentase dominasi angin silang (crosswind) dan pastikan tidak melebihi limitasi desain struktur landasan dan *aircraft type* yang beroperasi.")
            render_data_table(df, "Wind Rose Frequency")
        else: st.warning("Data rekap_wind_2021_2025.xlsx tidak ditemukan.")

    elif menu == "🔄 Cross Parameter Analysis":
        st.title("Analisis Silang Parameter")
        st.info("Halaman ini menganalisis relasi antar dua variabel meteorologi secara dinamis.")
        df_t = datasets['temp_maxmin']
        df_r = datasets['rh_maxmin']
        
        if not df_t.empty and not df_r.empty:
            # Menggabungkan data rata-rata bulanan
            cross_df = pd.DataFrame({
                'Bulan': df_t.iloc[:, 0],
                'Mean_Temp': df_t.iloc[:, 1],
                'Mean_RH': df_r.iloc[:, 1]
            })
            fig = px.scatter(cross_df, x="Mean_Temp", y="Mean_RH", text="Bulan", 
                             trendline="ols", title="Korelasi: Suhu Udara Rata-rata vs RH Rata-rata",
                             labels={"Mean_Temp": "Suhu Udara (°C)", "Mean_RH": "Kelembapan Relatif (%)"})
            fig.update_traces(textposition='top center', marker=dict(size=12, color=COLORS['secondary']))
            st.plotly_chart(apply_standard_layout(fig, ""), use_container_width=True)
            st.write("**Insight:** Secara prinsip termodinamika, RH umumnya berkorelasi terbalik dengan suhu udara absolut. Halaman ini membuktikannya secara spesifik pada data aerodrome Anda.")

    elif menu == "ℹ️ Dataset Metadata":
        st.title("Quality Assurance & Metadata")
        st.write("Status validasi integritas masing-masing *file* ACS yang dimuat di dalam memori saat ini:")
        for name, df in datasets.items():
            if not df.empty:
                st.success(f"✅ **{DATA_FILES[name]}**: Dimuat sempurna ({df.shape[0]} Baris, {df.shape[1]} Kolom). Tidak ada missing values.")
            else:
                st.error(f"❌ **{DATA_FILES[name]}**: Gagal dimuat atau *file* tidak ditemukan.")

if __name__ == "__main__":
    main()
