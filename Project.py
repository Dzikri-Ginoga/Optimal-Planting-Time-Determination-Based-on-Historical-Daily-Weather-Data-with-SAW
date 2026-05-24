import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import time

st.set_page_config(
    page_title="SCPK – Masa Tanam Optimal",
    page_icon="🌾",
    layout="wide",
)

if "hitung_spk" not in st.session_state:
    st.session_state.hitung_spk = False
if "tampilkan_loading" not in st.session_state:
    st.session_state.tampilkan_loading = False
if "last_calculated_params" not in st.session_state:
    st.session_state.last_calculated_params = None

st.sidebar.header("Data Cuaca")
uploaded = st.sidebar.file_uploader("Upload CSV cuaca (opsional)", type="csv")

@st.cache_data
def load_data(file=None):
    if file is not None:
        df = pd.read_csv(file)
    else:
        df = pd.read_csv("Indonesia_weather_data.csv")

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

st.sidebar.header("Parameter SAW")

st.sidebar.subheader("Pilih Komoditas")
jenis_tanaman = st.sidebar.selectbox(
    "Target Tanam:",
    [
        "Padi (Butuh curah hujan tinggi)",
        "Jagung / Palawija (Rawan busuk jika terlalu basah)",
        "Komoditas Kustom (Tentukan Sendiri)"
    ]
)

nama_kustom = "Komoditas Kustom"
if "Kustom" in jenis_tanaman:
    nama_kustom = st.sidebar.text_input("Nama Komoditas Kustom:", value="Komoditas Kustom")
    with st.sidebar.expander("Sifat Kriteria Kustom", expanded=True):
        opt_prec = st.selectbox("Curah Hujan:", ["Benefit (Lebih tinggi lebih baik)", "Cost (Lebih rendah lebih baik)"], index=0)
        opt_temp = st.selectbox("Suhu Rata-rata:", ["Benefit (Lebih tinggi lebih baik)", "Cost (Lebih rendah lebih baik)"], index=1)
        opt_sun = st.selectbox("Sinar Matahari:", ["Benefit (Lebih tinggi lebih baik)", "Cost (Lebih rendah lebih baik)"], index=0)
        opt_wind = st.selectbox("Kecepatan Angin:", ["Benefit (Lebih tinggi lebih baik)", "Cost (Lebih rendah lebih baik)"], index=1)
        opt_gust = st.selectbox("Kec. Angin Maks:", ["Benefit (Lebih tinggi lebih baik)", "Cost (Lebih rendah lebih baik)"], index=1)
        opt_dry = st.selectbox("Hari Kering:", ["Benefit (Lebih tinggi lebih baik)", "Cost (Lebih rendah lebih baik)"], index=1)
else:
    opt_prec, opt_temp, opt_sun, opt_wind, opt_gust, opt_dry = None, None, None, None, None, None

st.sidebar.subheader("Bobot Kriteria")
st.sidebar.caption("Total bobot harus = 1.0")

w_prec  = st.sidebar.slider("Curah Hujan", 0.0, 1.0, 0.15, 0.05)
w_temp  = st.sidebar.slider("Suhu Rata-rata (Cost)",  0.0, 1.0, 0.25, 0.05)
w_sun   = st.sidebar.slider("Sinar Matahari (Benefit)", 0.0, 1.0, 0.25, 0.05)
w_wind  = st.sidebar.slider("Kecepatan Angin (Cost)",  0.0, 1.0, 0.15, 0.05)
w_gust  = st.sidebar.slider("Kec. Angin Maksimum (Cost)", 0.0, 1.0, 0.10, 0.05)
w_dry   = st.sidebar.slider("Hari Kering", 0.0, 1.0, 0.10, 0.05)

total_w = round(w_prec + w_temp + w_sun + w_wind + w_gust + w_dry, 2)

if total_w == 1.0:
    st.sidebar.success(f"Total bobot = 1.0 (Sesuai)")
    bobot_valid = True
    weights_used = [w_prec, w_temp, w_sun, w_wind, w_gust, w_dry]
else:
    st.sidebar.error(f"Total bobot = {total_w} (Harus = 1.0)")
    st.sidebar.caption("💡 Sesuaikan slider bobot di atas agar berjumlah tepat 1.0 untuk mengaktifkan kembali tombol '🚀 Hitung SPK'.")
    bobot_valid = False
    weights_used = [w_prec, w_temp, w_sun, w_wind, w_gust, w_dry]

w_prec_used, w_temp_used, w_sun_used, w_wind_used, w_gust_used, w_dry_used = weights_used

st.sidebar.subheader("Filter Tahun")
years = sorted(df["Year"].unique())
opsi_tahun = st.sidebar.radio("Pilih Opsi Tahun", ("Per Tahun", "Rentang Tahun"))

if opsi_tahun == "Per Tahun" :
    pilih_tahun = st.sidebar.selectbox("Pilih Tahun", options= years)
    df_filtered = df[df["Year"] == pilih_tahun].copy()
    periode = str(pilih_tahun)
else:
    year_range = st.sidebar.select_slider("Rentang Tahun", options=years, value=(years[0], years[-1]))
    df_filtered = df[(df["Year"] >= year_range[0]) & (df["Year"] <= year_range[1])].copy()
    periode = f"{year_range[0]}–{year_range[1]}"

st.sidebar.divider()
st.sidebar.subheader("Simulasi Anomali Cuaca")
skenario_cuaca = st.sidebar.selectbox(
    "Pilih Kondisi Alam:",
    ["Normal", "El Niño (Kemarau Panjang)", "La Niña (Hujan Lebat)"]
)

current_params = {
    "jenis_tanaman": jenis_tanaman,
    "nama_kustom": nama_kustom,
    "w_prec": w_prec,
    "w_temp": w_temp,
    "w_sun": w_sun,
    "w_wind": w_wind,
    "w_gust": w_gust,
    "w_dry": w_dry,
    "skenario_cuaca": skenario_cuaca,
    "opsi_tahun": opsi_tahun,
    "periode": periode,
    "opt_prec": opt_prec,
    "opt_temp": opt_temp,
    "opt_sun": opt_sun,
    "opt_wind": opt_wind,
    "opt_gust": opt_gust,
    "opt_dry": opt_dry
}

if st.session_state.hitung_spk and st.session_state.last_calculated_params != current_params:
    st.session_state.hitung_spk = False

st.sidebar.divider()
if st.sidebar.button("🚀 Hitung SPK", type="primary", use_container_width=True, disabled=not bobot_valid):
    st.session_state.hitung_spk = True
    st.session_state.tampilkan_loading = True
    st.session_state.last_calculated_params = current_params.copy()

if not st.session_state.hitung_spk and st.session_state.last_calculated_params is not None:
    st.sidebar.warning("⚠️ Parameter berubah! Silakan klik tombol '🚀 Hitung SPK' kembali untuk memperbarui hasil.")

if st.session_state.tampilkan_loading:
    with st.spinner("⏳ Memproses matriks SAW dan Menganalisis AI Insights..."):
        time.sleep(2)
    st.balloons()
    st.toast("✅ Analisis Selesai! Silakan buka Tab 'Hasil & Ranking' untuk melihat rekomendasi.", icon="🏆")
    st.session_state.tampilkan_loading = False

df_filtered["Hari_Kering"] = (df_filtered["Precipitation_Sum"] == 0).astype(int)

monthly = df_filtered.groupby("Month").agg(
    Curah_Hujan   = ("Precipitation_Sum", "mean"),
    Suhu_RataRata = ("Temp_Mean",         "mean"),
    Sinar_Matahari= ("Sunshine_Duration", "mean"),
    Kecepatan_Angin=("Windspeed_Max",     "mean"),
    Kec_Gusts      = ("Windgusts_Max",     "mean"),   
    Hari_Kering    = ("Hari_Kering",       "sum"),
).reset_index()

n_years = len(df_filtered["Year"].unique())
monthly["Hari_Kering"] = monthly["Hari_Kering"] / n_years
monthly["Bulan"] = monthly["Month"].map(MONTH_NAMES)

if skenario_cuaca == "El Niño (Kemarau Panjang)":
    monthly["Curah_Hujan"] *= 0.5   
    monthly["Suhu_RataRata"] += 1.5 
    monthly["Hari_Kering"] *= 1.5   
elif skenario_cuaca == "La Niña (Hujan Lebat)":
    monthly["Curah_Hujan"] *= 1.8   
    monthly["Suhu_RataRata"] -= 1.0 
    monthly["Hari_Kering"] *= 0.3   

KRITERIA_COLS = ["Curah_Hujan","Suhu_RataRata","Sinar_Matahari","Kecepatan_Angin","Kec_Gusts","Hari_Kering"]

if "Kustom" in jenis_tanaman:
    attr_mapping = {"Benefit (Lebih tinggi lebih baik)": 1, "Cost (Lebih rendah lebih baik)": 0}
    ATRIBUT = [
        attr_mapping[opt_prec],
        attr_mapping[opt_temp],
        attr_mapping[opt_sun],
        attr_mapping[opt_wind],
        attr_mapping[opt_gust],
        attr_mapping[opt_dry]
    ]
    tipe_hujan = "Benefit" if attr_mapping[opt_prec] == 1 else "Cost"
    tipe_suhu = "Benefit" if attr_mapping[opt_temp] == 1 else "Cost"
    tipe_sinar = "Benefit" if attr_mapping[opt_sun] == 1 else "Cost"
    tipe_angin = "Benefit" if attr_mapping[opt_wind] == 1 else "Cost"
    tipe_gust = "Benefit" if attr_mapping[opt_gust] == 1 else "Cost"
    tipe_kering = "Benefit" if attr_mapping[opt_dry] == 1 else "Cost"
elif "Padi" in jenis_tanaman:
    ATRIBUT = [1, 0, 1, 0, 0, 0]
    tipe_hujan = "Benefit"
    tipe_suhu = "Cost"
    tipe_sinar = "Benefit"
    tipe_angin = "Cost"
    tipe_gust = "Cost"
    tipe_kering = "Cost"
elif "Jagung" in jenis_tanaman:
    ATRIBUT = [0, 0, 1, 0, 0, 1]
    tipe_hujan = "Cost"
    tipe_suhu = "Cost"
    tipe_sinar = "Benefit"
    tipe_angin = "Cost"
    tipe_gust = "Cost"
    tipe_kering = "Benefit"

def saw(df_m, bobot):
    data = df_m[KRITERIA_COLS].values.copy().astype(float)
    norm = np.zeros_like(data)
    for j, att in enumerate(ATRIBUT):
        col = data[:, j]
        if att == 1:
            max_val = col.max()
            norm[:, j] = col / max_val if max_val != 0 else 0
        else:
            min_val = col.min()
            with np.errstate(divide='ignore', invalid='ignore'):
                result = np.where(col != 0, min_val / col, 0)
            norm[:, j] = result
    norm = np.nan_to_num(norm, nan=0.0, posinf=0.0, neginf=0.0)
    skor = norm @ np.array(bobot)
    return norm, skor

norm_matrix, skor = saw(monthly, weights_used)

monthly["Skor_SAW"]  = skor
monthly["Ranking"]   = monthly["Skor_SAW"].rank(ascending=False).fillna(0).astype(int)

eval_df = monthly[["Ranking","Bulan","Skor_SAW", "Curah_Hujan", "Suhu_RataRata", "Sinar_Matahari", "Kecepatan_Angin", "Kec_Gusts", "Hari_Kering"]].sort_values("Ranking").copy()
best   = eval_df.iloc[0]
second = eval_df.iloc[1]
third  = eval_df.iloc[2]

hujan_best = best['Curah_Hujan']
suhu_best = best['Suhu_RataRata']
if "Kustom" in jenis_tanaman:
    komoditas_bersih = nama_kustom if nama_kustom and nama_kustom.strip() != "" else "Komoditas Kustom"
elif "Padi" in jenis_tanaman:
    komoditas_bersih = "Padi"
elif "Jagung" in jenis_tanaman:
    komoditas_bersih = "Jagung/Palawija"
else:
    komoditas_bersih = "Komoditas Kustom"

if skenario_cuaca == "Normal":
    kondisi = "iklim yang relatif stabil"
    if komoditas_bersih == "Padi":
        saran = "fokus pada penggenangan petakan sawah yang presisi dan pemupukan urea. Waktu ini sangat optimal untuk pertumbuhan vegetatif padi."
    elif komoditas_bersih == "Jagung/Palawija":
        saran = "pastikan drainase/parit berfungsi baik agar air tidak menggenang dan merusak sistem perakaran jagung."
    else:
        saran = f"melakukan pemeliharaan tanaman secara standar, memantau tingkat kesuburan tanah, serta memastikan kelembapan media tanam berada pada tingkat ideal untuk {komoditas_bersih}."
elif skenario_cuaca == "El Niño (Kemarau Panjang)":
    kondisi = "penurunan curah hujan drastis dan anomali suhu panas"
    if komoditas_bersih == "Padi":
        saran = "segera siapkan sistem irigasi sumur bor dan pertimbangkan varietas padi toleran kekeringan (Inpari 42). Jangan biarkan tanah sawah retak terlalu dalam."
    elif komoditas_bersih == "Jagung/Palawija":
        saran = "berikan penyiraman interval untuk menjaga kelembapan, jagung lebih tahan kering namun tetap butuh air saat fase pembungaan (tasseling)."
    else:
        saran = f"mengantisipasi dampak kekeringan dengan mempersiapkan sumber air cadangan, serta mengoptimalkan teknik mulsa untuk menekan penguapan tanah pada lahan {komoditas_bersih}."
else:
    kondisi = "curah hujan ekstrem dan suhu cenderung lebih sejuk"
    if komoditas_bersih == "Padi":
        saran = "waspadai serangan hama wereng dan penyakit hawar daun bakteri (kresek) akibat kelembapan tinggi. Kurangi penggunaan pupuk N berlebih."
    elif komoditas_bersih == "Jagung/Palawija":
        saran = "tinggikan bedengan tanam dan waspadai penyakit bulai jagung. Drainase lahan menjadi prioritas utama agar akar jagung tidak mati lemas."
    else:
        saran = f"memeriksa efektivitas saluran pembuangan air (drainase) agar tidak terjadi genangan air yang berlebih pada lahan {komoditas_bersih}, serta mewaspadai peningkatan risiko hama jamur."
    
teks_ai = f"Berdasarkan metode SAW untuk target komoditas **{komoditas_bersih}** pada skenario **{skenario_cuaca}**, bulan **{best['Bulan']}** adalah opsi tanam paling optimal. Dengan kondisi curah hujan rata-rata {hujan_best:.1f} mm dan suhu {suhu_best:.1f} °C ({kondisi}), disarankan agar petani {saran}"

if "Kustom" in jenis_tanaman:
    desc_crop = f"🌱 **Karakteristik {komoditas_bersih}:** Sifat kriteria dikonfigurasi secara manual oleh pengguna (Curah Hujan: *{tipe_hujan}*, Hari Kering: *{tipe_kering}*). Pastikan keselarasan antara bobot kriteria dan syarat agro-klimatologi komoditas target Anda."
elif "Padi" in jenis_tanaman:
    desc_crop = "🌾 **Karakteristik Tumbuh Padi:** Menyukai curah hujan tinggi (Benefit) untuk menjaga kelembapan sawah basah, durasi sinar matahari yang cukup (Benefit), dan suhu hangat. Kecepatan angin kencang (Cost) dan hari kering yang berkepanjangan (Cost) dihindari karena berisiko merusak bulir tanaman."
elif "Jagung" in jenis_tanaman:
    desc_crop = "🌽 **Karakteristik Tumbuh Jagung:** Menyukai kondisi tanah yang tidak tergenang air (Curah Hujan = Cost) agar sistem perakaran tidak membusuk. Hari kering (Benefit) dan durasi sinar matahari melimpah (Benefit) sangat membantu proses pembungaan dan pengeringan tongkol sebelum panen."

st.title("🌾 Penentuan Masa Tanam Optimal")
st.caption("Metode SAW (Simple Additive Weighting) · Data Historis Cuaca Harian Indonesia")

if not st.session_state.hitung_spk:
    if not bobot_valid:
        st.error("❌ **Error pada Parameter:** Jumlah total bobot kriteria pada sidebar saat ini tidak bernilai 1.0. Harap atur kembali slider bobot agar berjumlah tepat 1.0 untuk mengaktifkan tombol **'🚀 Hitung SPK'**.")
    else:
        st.info("👈 **Selamat Datang!** Silakan atur bobot kriteria dan komoditas tanaman di sidebar, lalu klik **'🚀 Hitung SPK'** untuk memulai analisis penentuan masa tanam optimal.")
        st.caption(desc_crop)
else:
    st.success(f"🥇 **Rekomendasi Utama (Waktu Tanam Paling Optimal)**\n\nBerdasarkan analisis metode SAW untuk target komoditas **{komoditas_bersih}** ({periode}), bulan **{best['Bulan']}** terpilih sebagai opsi tanam terbaik dengan Skor Preferensi tertinggi sebesar **{best['Skor_SAW']:.4f}**.")
    
    st.info(f"🤖 **AI Insights:** {teks_ai}")
    st.caption(desc_crop)
st.divider()

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Data Cuaca", "🏆 Hasil & Ranking", "📈 Visualisasi Analitis", "🔢 Langkah Perhitungan SAW", "👥 Profil Kelompok"
])

with tab1:
    if skenario_cuaca != "Normal":
        st.warning(f"⚠️ Menampilkan data hasil simulasi skenario: **{skenario_cuaca}**")
    
    st.subheader("📊 Rata-rata Cuaca per Bulan")
    display = monthly[["Bulan","Curah_Hujan","Suhu_RataRata","Sinar_Matahari","Kecepatan_Angin","Kec_Gusts","Hari_Kering"]].copy()
    display.columns = ["Bulan","Curah Hujan (mm)","Suhu Rata-rata (°C)","Sinar Matahari (s)","Kec. Angin (km/h)","Kec. Gusts (km/h)","Hari Kering (hari/thn)"]
    st.dataframe(display.set_index("Bulan").style.format("{:.2f}"), use_container_width=True)

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("💧 Curah Hujan Tertinggi",     monthly.loc[monthly["Curah_Hujan"].idxmax(),    "Bulan"])
    col2.metric("🌡️ Suhu Terendah",              monthly.loc[monthly["Suhu_RataRata"].idxmin(),  "Bulan"])
    col3.metric("☀️ Sinar Matahari Terbanyak",   monthly.loc[monthly["Sinar_Matahari"].idxmax(), "Bulan"])
    col4.metric("💨 Angin Terendah",             monthly.loc[monthly["Kecepatan_Angin"].idxmin(),"Bulan"])
    col5.metric("🌪️ Gusts Terendah",             monthly.loc[monthly["Kec_Gusts"].idxmin(),      "Bulan"])
    col6.metric("🏜️ Hari Kering Paling Sedikit", monthly.loc[monthly["Hari_Kering"].idxmin(),    "Bulan"])

    st.divider()
    st.subheader("🔍 Dataset Mentah Harian (Raw Data)")
    st.markdown("Berikut adalah tabel interaktif seluruh dataset cuaca harian yang digunakan. Anda dapat mengurutkan, menyaring, dan mengeksplorasi data di bawah ini.")
    with st.expander("📂 Tampilkan Seluruh Baris Dataset (Indonesia_weather_data.csv)", expanded=False):
        st.dataframe(df, use_container_width=True)

with tab2:
    if not st.session_state.hitung_spk:
        st.info("👈 Silakan atur bobot dan tekan tombol **'🚀 Hitung SPK'** di sidebar untuk melihat hasil perangkingan.")
    elif not bobot_valid:
        st.warning("Bobot belum valid (total harus 1.0). Atur di sidebar.")
    else:
        c1, c2, c3 = st.columns(3)
        c1.success(f"🥇 **Terbaik**: {best['Bulan']}\n\nSkor: `{best['Skor_SAW']:.4f}`")
        c2.info(f"🥈 **Runner-up**: {second['Bulan']}\n\nSkor: `{second['Skor_SAW']:.4f}`")
        c3.warning(f"🥉 **Ketiga**: {third['Bulan']}\n\nSkor: `{third['Skor_SAW']:.4f}`")

        st.subheader("Ranking Lengkap Semua Bulan")
        ranking_display = eval_df[["Ranking","Bulan","Skor_SAW"]].copy()
        ranking_display.columns = ["Ranking","Bulan","Skor SAW"]
        st.dataframe(ranking_display.set_index("Ranking").style.format({"Skor SAW": "{:.4f}"}), use_container_width=True)

        csv_data = ranking_display.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Ekspor Hasil Ranking ke CSV",
            data=csv_data,
            file_name=f"Hasil_Ranking_SAW_{komoditas_bersih.replace('/', '_').replace(' ', '_')}_{periode}.csv",
            mime="text/csv",
            use_container_width=True
        )

        st.divider()
        with st.expander("⚖️ Analisis Perbandingan Head-to-Head (Peringkat 1 vs Peringkat 2)"):
            st.markdown("Berikut adalah perbandingan nilai cuaca rata-rata asli antara bulan terbaik (Juara) dan bulan terbaik kedua (Runner-up) untuk membantu pengambilan keputusan:")
            
            comp_data = {
                "Kriteria": ["Skor SAW", "Curah Hujan (mm)", "Suhu Rata-rata (°C)", "Sinar Matahari (s)", "Kec. Angin (km/h)", "Kec. Gusts (km/h)", "Hari Kering (hari/thn)"],
                f"🥇 Juara ({best['Bulan']})": [
                    f"{best['Skor_SAW']:.4f}", f"{best['Curah_Hujan']:.2f}", f"{best['Suhu_RataRata']:.2f}",
                    f"{best['Sinar_Matahari']:.2f}", f"{best['Kecepatan_Angin']:.2f}", f"{best['Kec_Gusts']:.2f}", f"{best['Hari_Kering']:.2f}"
                ],
                f"🥈 Runner-up ({second['Bulan']})": [
                    f"{second['Skor_SAW']:.4f}", f"{second['Curah_Hujan']:.2f}", f"{second['Suhu_RataRata']:.2f}",
                    f"{second['Sinar_Matahari']:.2f}", f"{second['Kecepatan_Angin']:.2f}", f"{second['Kec_Gusts']:.2f}", f"{second['Hari_Kering']:.2f}"
                ],
                "Selisih": [
                    f"{best['Skor_SAW'] - second['Skor_SAW']:.4f}",
                    f"{best['Curah_Hujan'] - second['Curah_Hujan']:.2f}",
                    f"{best['Suhu_RataRata'] - second['Suhu_RataRata']:.2f}",
                    f"{best['Sinar_Matahari'] - second['Sinar_Matahari']:.2f}",
                    f"{best['Kecepatan_Angin'] - second['Kecepatan_Angin']:.2f}",
                    f"{best['Kec_Gusts'] - second['Kec_Gusts']:.2f}",
                    f"{best['Hari_Kering'] - second['Hari_Kering']:.2f}"
                ]
            }
            comp_df = pd.DataFrame(comp_data)
            st.table(comp_df.set_index("Kriteria"))

with tab3:
    if not st.session_state.hitung_spk:
        st.info("👈 Silakan atur bobot dan tekan tombol **'🚀 Hitung SPK'** di sidebar untuk melihat grafik.")
    else:
        st.subheader("1. Grafik Skor SAW per Bulan")
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
        ax.set_title(f"Skor SAW ({komoditas_bersih}) - {skenario_cuaca}")
        plt.tight_layout()
        st.pyplot(fig)

        st.divider()

        st.subheader("2. Distribusi Cuaca Bulanan")
        kriteria_opt = st.selectbox(
            "Pilih kriteria:", ["Curah Hujan (mm)","Suhu Rata-rata (°C)","Sinar Matahari (s)","Kecepatan Angin (km/h)","Kec. Gusts (km/h)","Hari Kering (hari/thn)"]
        )
        col_map = {
            "Curah Hujan (mm)":         "Curah_Hujan",
            "Suhu Rata-rata (°C)":      "Suhu_RataRata",
            "Sinar Matahari (s)":       "Sinar_Matahari",
            "Kecepatan Angin (km/h)":   "Kecepatan_Angin",
            "Kec. Gusts (km/h)":        "Kec_Gusts",
            "Hari Kering (hari/thn)":   "Hari_Kering",
        }
        fig2, ax2 = plt.subplots(figsize=(10, 4))
        ax2.plot(monthly["Bulan"], monthly[col_map[kriteria_opt]], marker="o", color="#1976d2", linewidth=2)
        ax2.fill_between(monthly["Bulan"], monthly[col_map[kriteria_opt]], alpha=0.15, color="#1976d2")
        ax2.set_title(f"{kriteria_opt} Rata-rata per Bulan")
        ax2.set_ylabel(kriteria_opt)
        ax2.tick_params(axis="x", rotation=45)
        plt.tight_layout()
        st.pyplot(fig2)

        st.divider()
        
        st.subheader("3. Korelasi Curah Hujan vs Suhu Rata-rata")
        fig3, ax3 = plt.subplots(figsize=(10, 4))
        ax3.scatter(monthly["Curah_Hujan"], monthly["Suhu_RataRata"], color="#e91e63", s=100, alpha=0.7)
        for i, txt in enumerate(monthly["Bulan"]):
            ax3.annotate(txt, (monthly["Curah_Hujan"].iloc[i], monthly["Suhu_RataRata"].iloc[i]), 
                         xytext=(5, 5), textcoords="offset points", fontsize=9)
        ax3.set_title("Korelasi Curah Hujan dan Suhu")
        ax3.set_xlabel("Curah Hujan (mm)")
        ax3.set_ylabel("Suhu Rata-rata (°C)")
        plt.tight_layout()
        st.pyplot(fig3)

with tab4:
    if not st.session_state.hitung_spk:
        st.info("👈 Silakan atur bobot dan tekan tombol **'🚀 Hitung SPK'** di sidebar untuk memproses matriks.")
    else:
        st.subheader("🔢 Langkah Perhitungan SAW")
        
        st.markdown("#### ⚖️ Grafik Distribusi Bobot Kriteria Saat Ini")
        fig_weight, ax_w = plt.subplots(figsize=(6, 3))
        labels = ["Hujan", "Suhu", "Sinar", "Kec. Angin", "Kec. Gusts", "Hari Kering"]
        weights = weights_used
        
        labels_filtered = [l for l, w in zip(labels, weights) if w > 0]
        weights_filtered = [w for w in weights if w > 0]
        colors = ["#4caf50", "#ff9800", "#ffeb3b", "#2196f3", "#9c27b0", "#e91e63"]
        colors_filtered = [c for c, w in zip(colors, weights) if w > 0]
        
        ax_w.pie(weights_filtered, labels=labels_filtered, autopct='%1.1f%%', startangle=140, colors=colors_filtered, textprops={'fontsize': 8})
        ax_w.axis('equal')
        plt.tight_layout()
        st.pyplot(fig_weight)
        st.divider()

        st.markdown("#### 1. Matriks Keputusan (Nilai Asli)")
        raw_df = monthly.set_index("Bulan")[KRITERIA_COLS].copy()
        raw_df.columns = ["Curah Hujan (mm)","Suhu (°C)","Sinar Matahari (s)","Kec. Angin (km/h)","Kec. Gusts (km/h)","Hari Kering (hari/thn)"]
        st.dataframe(raw_df.style.format("{:.4f}"), use_container_width=True)

        st.markdown("#### 2. Matriks Ternormalisasi")
        norm_df = pd.DataFrame(
            norm_matrix, index=monthly["Bulan"],
            columns=[f"Curah Hujan ({tipe_hujan})", f"Suhu ({tipe_suhu})", f"Sinar Matahari ({tipe_sinar})", f"Kec. Angin ({tipe_angin})", f"Kec. Gusts ({tipe_gust})", f"Hari Kering ({tipe_kering})"]
        )
        st.dataframe(norm_df.style.format("{:.4f}").background_gradient(axis=0, cmap="YlGn"), use_container_width=True)

        st.markdown("#### 3. Bobot yang Digunakan")
        bobot_df = pd.DataFrame({
            "Kriteria":["Curah Hujan","Suhu Rata-rata","Sinar Matahari","Kec. Angin","Kec. Gusts","Hari Kering"],
            "Tipe":    [tipe_hujan, tipe_suhu, tipe_sinar, tipe_angin, tipe_gust, tipe_kering],
            "Bobot":   [w_prec, w_temp, w_sun, w_wind, w_gust, w_dry]
        })
        st.dataframe(bobot_df.set_index("Kriteria"), use_container_width=True)

        st.markdown("#### 4. Nilai Preferensi (Skor SAW)")
        pref_df = monthly[["Bulan","Skor_SAW"]].copy()
        pref_df.columns = ["Bulan","Nilai Preferensi"]
        st.dataframe(pref_df.set_index("Bulan").style.format("{:.4f}").bar(color="#4caf50"), use_container_width=True)

with tab5:
    st.subheader("👨‍💻 Tim Pengembang")
    col_prof1, col_prof2 = st.columns(2)
    with col_prof1:
        st.info("**Anggota 1**\n\nNama: M. Dzikri Ginoga\n\nNIM: 123240237")
    with col_prof2:
        st.info("**Anggota 2**\n\nNama: Bintang Shada Kawibya Putra\n\nNIM: 123240247")

st.divider()