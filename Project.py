import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker


# Konfigurasi halaman
st.set_page_config(
    page_title="SCPK – Masa Tanam Optimal",
    page_icon="🌾",
    layout="wide",
)

st.title("🌾 Penentuan Masa Tanam Optimal")
st.caption("Metode SAW (Simple Additive Weighting) · Data Historis Cuaca Harian Indonesia")

# Upload / default data
st.sidebar.header("📂 Data Cuaca")
uploaded = st.sidebar.file_uploader("Upload CSV cuaca (opsional)", type="csv")

@st.cache_data
def load_data(file=None):
    if file is not None:
        df = pd.read_csv(file)
    else:
        df = pd.read_csv("Indonesia_weather_data.csv")

    # Parsing tanggal fleksibel
    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
    df = df.dropna(subset=["Date"])
    df["Month"] = df["Date"].dt.month
    df["Year"]  = df["Date"].dt.year
    return df

try:
    df = load_data(uploaded)
except FileNotFoundError:
    st.error("File `Indonesia_weather_data.csv` tidak ditemukan. Silakan upload lewat sidebar.")
    st.stop()

MONTH_NAMES = {
    1:"Januari", 2:"Februari", 3:"Maret", 4:"April",
    5:"Mei", 6:"Juni", 7:"Juli", 8:"Agustus",
    9:"September", 10:"Oktober", 11:"November", 12:"Desember"
}


st.sidebar.header("⚙️ Parameter SAW")

st.sidebar.subheader("Bobot Kriteria")
st.sidebar.caption("Total bobot harus = 1.0")

w_prec  = st.sidebar.slider("💧 Curah Hujan (Benefit)", 0.0, 1.0, 0.35, 0.05)
w_temp  = st.sidebar.slider("🌡️ Suhu Rata-rata (Cost)",  0.0, 1.0, 0.25, 0.05)
w_sun   = st.sidebar.slider("☀️ Sinar Matahari (Benefit)", 0.0, 1.0, 0.25, 0.05)
w_wind  = st.sidebar.slider("💨 Kecepatan Angin (Cost)",  0.0, 1.0, 0.15, 0.05)

total_w = round(w_prec + w_temp + w_sun + w_wind, 2)
if total_w != 1.0:
    st.sidebar.warning(f"⚠️ Total bobot = {total_w} (harus 1.0)")
    bobot_valid = False
else:
    st.sidebar.success(f"✅ Total bobot = {total_w}")
    bobot_valid = True

st.sidebar.subheader("Filter Tahun")
years = sorted(df["Year"].unique())
opsi_tahun = st.sidebar.radio(
    "Pilih Opsi Tahun", 
    ("Per Tahun", "Rentang Tahun")
)

if opsi_tahun == "Per Tahun" :
    pilih_tahun = st.sidebar.selectbox("Pilih Tahun", options= years)
    df_filtered = df[df["Year"] == pilih_tahun].copy()
    periode = str(pilih_tahun)
else:
    year_range = st.sidebar.select_slider(
        "Rentang Tahun",
        options=years,
        value=(years[0], years[-1]),
    )
    df_filtered = df[(df["Year"] >= year_range[0]) & (df["Year"] <= year_range[1])].copy()
    periode = f"{year_range[0]-year_range[1]}"


monthly = df_filtered.groupby("Month").agg(
    Curah_Hujan   = ("Precipitation_Sum", "mean"),
    Suhu_RataRata = ("Temp_Mean",         "mean"),
    Sinar_Matahari= ("Sunshine_Duration", "mean"),
    Kecepatan_Angin=("Windspeed_Max",     "mean"),
).reset_index()

monthly["Bulan"] = monthly["Month"].map(MONTH_NAMES)


def saw(df_m, bobot):
    data = df_m[["Curah_Hujan","Suhu_RataRata","Sinar_Matahari","Kecepatan_Angin"]].values.copy().astype(float)
    # Benefit: Curah Hujan, Sinar Matahari  → dibagi max
    # Cost   : Suhu, Kecepatan Angin        → dibagi dengan nilai / min
    atribut = [1, 0, 1, 0]   # 1=benefit, 0=cost
    norm = np.zeros_like(data)
    for j, att in enumerate(atribut):
        col = data[:, j]
        if att == 1:
            norm[:, j] = col / col.max()
        else:
            norm[:, j] = col.min() / col
    skor = norm @ np.array(bobot)
    return norm, skor

norm_matrix, skor = saw(monthly, [w_prec, w_temp, w_sun, w_wind])

monthly["Skor_SAW"]  = skor
monthly["Ranking"]   = monthly["Skor_SAW"].rank(ascending=False).astype(int)


tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Data Cuaca", "🔢 Matriks SAW", "🏆 Hasil & Ranking", "📈 Visualisasi"
])

# ── Tab 1: Data Cuaca ────────────────────────
with tab1:
    st.subheader("Rata-rata Cuaca per Bulan")
    st.caption(f"Periode {periode}  |  Total data: {len(df_filtered):,} hari")

    display = monthly[["Bulan","Curah_Hujan","Suhu_RataRata","Sinar_Matahari","Kecepatan_Angin"]].copy()
    display.columns = ["Bulan","Curah Hujan (mm)","Suhu Rata-rata (°C)","Sinar Matahari (s)","Kec. Angin (km/h)"]
    st.dataframe(display.set_index("Bulan").style.format("{:.2f}"), use_container_width=True)

    col1, col2, col3, col4 = st.columns(4)
    best_rain = monthly.loc[monthly["Curah_Hujan"].idxmax(), "Bulan"]
    low_temp  = monthly.loc[monthly["Suhu_RataRata"].idxmin(), "Bulan"]
    best_sun  = monthly.loc[monthly["Sinar_Matahari"].idxmax(), "Bulan"]
    low_wind  = monthly.loc[monthly["Kecepatan_Angin"].idxmin(), "Bulan"]
    col1.metric("💧 Curah Hujan Tertinggi", best_rain)
    col2.metric("🌡️ Suhu Terendah", low_temp)
    col3.metric("☀️ Sinar Matahari Terbanyak", best_sun)
    col4.metric("💨 Angin Terendah", low_wind)

# ── Tab 2: Matriks SAW ───────────────────────
with tab2:
    st.subheader("Langkah SAW")

    st.markdown("#### 1. Matriks Keputusan (Nilai Asli)")
    raw_cols = ["Curah_Hujan","Suhu_RataRata","Sinar_Matahari","Kecepatan_Angin"]
    raw_df = monthly.set_index("Bulan")[raw_cols].copy()
    raw_df.columns = ["Curah Hujan (mm)","Suhu (°C)","Sinar Matahari (s)","Kec. Angin (km/h)"]
    st.dataframe(raw_df.style.format("{:.4f}"), use_container_width=True)

    st.markdown("#### 2. Matriks Ternormalisasi")
    norm_df = pd.DataFrame(
        norm_matrix,
        index=monthly["Bulan"],
        columns=["Curah Hujan (Benefit)","Suhu (Cost)","Sinar Matahari (Benefit)","Kec. Angin (Cost)"]
    )
    st.dataframe(norm_df.style.format("{:.4f}").background_gradient(axis=0, cmap="YlGn"), use_container_width=True)

    st.markdown("#### 3. Bobot yang Digunakan")
    bobot_df = pd.DataFrame({
        "Kriteria":["Curah Hujan","Suhu Rata-rata","Sinar Matahari","Kecepatan Angin"],
        "Tipe":["Benefit","Cost","Benefit","Cost"],
        "Bobot":[w_prec, w_temp, w_sun, w_wind]
    })
    st.dataframe(bobot_df.set_index("Kriteria"), use_container_width=True)

    st.markdown("#### 4. Nilai Preferensi (Skor SAW)")
    pref_df = monthly[["Bulan","Skor_SAW"]].copy()
    pref_df.columns = ["Bulan","Nilai Preferensi"]
    st.dataframe(
        pref_df.set_index("Bulan").style.format("{:.4f}").bar(color="#4caf50"),
        use_container_width=True,
    )

# ── Tab 3: Hasil & Ranking ───────────────────
with tab3:
    if not bobot_valid:
        st.warning("Bobot belum valid (total harus 1.0). Atur di sidebar.")
    else:
        ranking_df = monthly[["Ranking","Bulan","Skor_SAW"]].sort_values("Ranking").copy()
        ranking_df.columns = ["Ranking","Bulan","Skor SAW"]

        best   = ranking_df.iloc[0]
        second = ranking_df.iloc[1]
        third  = ranking_df.iloc[2]

        c1, c2, c3 = st.columns(3)
        c1.success(f"🥇 **Terbaik**: {best['Bulan']}\n\nSkor: `{best['Skor SAW']:.4f}`")
        c2.info(f"🥈 **Runner-up**: {second['Bulan']}\n\nSkor: `{second['Skor SAW']:.4f}`")
        c3.warning(f"🥉 **Ketiga**: {third['Bulan']}\n\nSkor: `{third['Skor SAW']:.4f}`")

        st.subheader("Ranking Lengkap Semua Bulan")
        st.dataframe(
            ranking_df.set_index("Ranking").style.format({"Skor SAW": "{:.4f}"}),
            use_container_width=True,
        )

        st.info(
            f"**Kesimpulan:** Berdasarkan analisis SAW dengan data historis {periode}, "
            f"bulan **{best['Bulan']}** merupakan waktu tanam yang paling optimal "
            f"dengan skor preferensi tertinggi sebesar **{best['Skor SAW']:.4f}**."
        )

# ── Tab 4: Visualisasi ───────────────────────
with tab4:
    st.subheader("Grafik Skor SAW per Bulan")
    fig, ax = plt.subplots(figsize=(10, 4))
    colors = ["#4caf50" if r == 1 else "#90caf9" for r in monthly["Ranking"]]
    bars = ax.bar(monthly["Bulan"], monthly["Skor_SAW"], color=colors, edgecolor="white")
    ax.set_ylabel("Skor SAW")
    ax.set_xlabel("Bulan")
    ax.set_ylim(0, monthly["Skor_SAW"].max() * 1.15)
    ax.tick_params(axis="x", rotation=45)
    for bar, val in zip(bars, monthly["Skor_SAW"]):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.005,
                f"{val:.3f}", ha="center", va="bottom", fontsize=8)
    ax.set_title("Skor SAW Penentuan Masa Tanam Optimal")
    plt.tight_layout()
    st.pyplot(fig)

    st.subheader("Distribusi Cuaca Bulanan")
    kriteria_opt = st.selectbox(
        "Pilih kriteria:",
        ["Curah Hujan (mm)","Suhu Rata-rata (°C)","Sinar Matahari (s)","Kecepatan Angin (km/h)"]
    )
    col_map = {
        "Curah Hujan (mm)":       "Curah_Hujan",
        "Suhu Rata-rata (°C)":    "Suhu_RataRata",
        "Sinar Matahari (s)":     "Sinar_Matahari",
        "Kecepatan Angin (km/h)": "Kecepatan_Angin",
    }
    fig2, ax2 = plt.subplots(figsize=(10, 4))
    ax2.plot(monthly["Bulan"], monthly[col_map[kriteria_opt]],
             marker="o", color="#1976d2", linewidth=2)
    ax2.fill_between(monthly["Bulan"], monthly[col_map[kriteria_opt]], alpha=0.15, color="#1976d2")
    ax2.set_title(f"{kriteria_opt} Rata-rata per Bulan")
    ax2.set_ylabel(kriteria_opt)
    ax2.tick_params(axis="x", rotation=45)
    plt.tight_layout()
    st.pyplot(fig2)


st.divider()

