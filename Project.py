import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import time

st.set_page_config(
    page_title="SPK Masa Tanam - SAW",
    layout="wide",
)

if "hitung_spk" not in st.session_state:
    st.session_state.hitung_spk = False
if "tampilkan_loading" not in st.session_state:
    st.session_state.tampilkan_loading = False
if "last_calculated_params" not in st.session_state:
    st.session_state.last_calculated_params = None

st.sidebar.header("Dataset Cuaca")
uploaded = st.sidebar.file_uploader("Upload data CSV (opsional)", type="csv")

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
    st.error("Dataset 'Indonesia_weather_data.csv' tidak ditemukan.")
    st.stop()

MONTH_NAMES = {
    1:"Januari", 2:"Februari", 3:"Maret", 4:"April",
    5:"Mei", 6:"Juni", 7:"Juli", 8:"Agustus",
    9:"September", 10:"Oktober", 11:"November", 12:"Desember"
}

st.sidebar.header("Parameter SAW")

st.sidebar.subheader("Komoditas")
jenis_tanaman = st.sidebar.selectbox(
    "Pilih Tanaman:",
    ["Padi", "Jagung/Palawija", "Kustom"]
)

nama_kustom = "Kustom"
if jenis_tanaman == "Kustom":
    nama_kustom = st.sidebar.text_input("Nama Tanaman:", value="Kustom")
    with st.sidebar.expander("Pengaturan Sifat Kriteria"):
        opt_prec = st.selectbox("Curah Hujan:", ["Benefit", "Cost"], index=0)
        opt_temp = st.selectbox("Suhu Rata-rata:", ["Benefit", "Cost"], index=1)
        opt_sun = st.selectbox("Sinar Matahari:", ["Benefit", "Cost"], index=0)
        opt_wind = st.selectbox("Kecepatan Angin:", ["Benefit", "Cost"], index=1)
        opt_gust = st.selectbox("Kec. Angin Maks:", ["Benefit", "Cost"], index=1)
        opt_dry = st.selectbox("Hari Kering:", ["Benefit", "Cost"], index=1)
else:
    opt_prec, opt_temp, opt_sun, opt_wind, opt_gust, opt_dry = None, None, None, None, None, None

st.sidebar.subheader("Bobot Kriteria")
w_prec  = st.sidebar.slider("Curah Hujan", 0.0, 1.0, 0.15, 0.05)
w_temp  = st.sidebar.slider("Suhu Rata-rata",  0.0, 1.0, 0.25, 0.05)
w_sun   = st.sidebar.slider("Sinar Matahari", 0.0, 1.0, 0.25, 0.05)
w_wind  = st.sidebar.slider("Kecepatan Angin",  0.0, 1.0, 0.15, 0.05)
w_gust  = st.sidebar.slider("Kec. Angin Maksimum", 0.0, 1.0, 0.10, 0.05)
w_dry   = st.sidebar.slider("Hari Kering", 0.0, 1.0, 0.10, 0.05)

total_w = round(w_prec + w_temp + w_sun + w_wind + w_gust + w_dry, 2)

if total_w == 1.0:
    st.sidebar.success("Total bobot: 1.0 (Valid)")
    bobot_valid = True
    weights_used = [w_prec, w_temp, w_sun, w_wind, w_gust, w_dry]
else:
    st.sidebar.error(f"Total bobot: {total_w} (Harus 1.0)")
    bobot_valid = False
    weights_used = [w_prec, w_temp, w_sun, w_wind, w_gust, w_dry]

w_prec_used, w_temp_used, w_sun_used, w_wind_used, w_gust_used, w_dry_used = weights_used

st.sidebar.subheader("Filter Waktu")
years = sorted(df["Year"].unique())
opsi_tahun = st.sidebar.radio("Rentang Data:", ("Per Tahun", "Rentang Tahun"))

if opsi_tahun == "Per Tahun" :
    pilih_tahun = st.sidebar.selectbox("Tahun:", options= years)
    df_filtered = df[df["Year"] == pilih_tahun].copy()
    periode = str(pilih_tahun)
else:
    year_range = st.sidebar.select_slider("Tahun:", options=years, value=(years[0], years[-1]))
    df_filtered = df[(df["Year"] >= year_range[0]) & (df["Year"] <= year_range[1])].copy()
    periode = f"{year_range[0]}–{year_range[1]}"

st.sidebar.divider()
st.sidebar.subheader("Skenario Kondisi Cuaca")
skenario_cuaca = st.sidebar.selectbox(
    "Pilih Kondisi:",
    ["Normal", "El Niño (Kemarau)", "La Niña (Hujan Lebat)"]
)

current_params = {
    "jenis_tanaman": jenis_tanaman, "nama_kustom": nama_kustom, "w_prec": w_prec, "w_temp": w_temp,
    "w_sun": w_sun, "w_wind": w_wind, "w_gust": w_gust, "w_dry": w_dry, "skenario_cuaca": skenario_cuaca,
    "opsi_tahun": opsi_tahun, "periode": periode, "opt_prec": opt_prec, "opt_temp": opt_temp,
    "opt_sun": opt_sun, "opt_wind": opt_wind, "opt_gust": opt_gust, "opt_dry": opt_dry
}

if st.session_state.hitung_spk and st.session_state.last_calculated_params != current_params:
    st.session_state.hitung_spk = False

st.sidebar.divider()
if st.sidebar.button("Hitung SPK", type="primary", use_container_width=True, disabled=not bobot_valid):
    st.session_state.hitung_spk = True
    st.session_state.tampilkan_loading = True
    st.session_state.last_calculated_params = current_params.copy()

if not st.session_state.hitung_spk and st.session_state.last_calculated_params is not None:
    st.sidebar.warning("Parameter berubah. Klik 'Hitung SPK' untuk memperbarui data.")

if st.session_state.tampilkan_loading:
    with st.spinner("Memproses perhitungan matriks SAW..."):
        time.sleep(1.5)
    st.toast("Proses perhitungan selesai.")
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

if skenario_cuaca == "El Niño (Kemarau)":
    monthly["Curah_Hujan"] *= 0.5   
    monthly["Suhu_RataRata"] += 1.5 
    monthly["Hari_Kering"] *= 1.5   
elif skenario_cuaca == "La Niña (Hujan Lebat)":
    monthly["Curah_Hujan"] *= 1.8   
    monthly["Suhu_RataRata"] -= 1.0 
    monthly["Hari_Kering"] *= 0.3   

KRITERIA_COLS = ["Curah_Hujan","Suhu_RataRata","Sinar_Matahari","Kecepatan_Angin","Kec_Gusts","Hari_Kering"]

if jenis_tanaman == "Kustom":
    attr_mapping = {"Benefit": 1, "Cost": 0}
    ATRIBUT = [
        attr_mapping[opt_prec], attr_mapping[opt_temp], attr_mapping[opt_sun],
        attr_mapping[opt_wind], attr_mapping[opt_gust], attr_mapping[opt_dry]
    ]
    tipe_hujan, tipe_suhu, tipe_sinar = opt_prec, opt_temp, opt_sun
    tipe_angin, tipe_gust, tipe_kering = opt_wind, opt_gust, opt_dry
elif jenis_tanaman == "Padi":
    ATRIBUT = [1, 0, 1, 0, 0, 0]
    tipe_hujan, tipe_suhu, tipe_sinar = "Benefit", "Cost", "Benefit"
    tipe_angin, tipe_gust, tipe_kering = "Cost", "Cost", "Cost"
elif jenis_tanaman == "Jagung/Palawija":
    ATRIBUT = [0, 0, 1, 0, 0, 1]
    tipe_hujan, tipe_suhu, tipe_sinar = "Cost", "Cost", "Benefit"
    tipe_angin, tipe_gust, tipe_kering = "Cost", "Cost", "Benefit"

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
komoditas_bersih = nama_kustom if jenis_tanaman == "Kustom" else jenis_tanaman

if skenario_cuaca == "Normal":
    kondisi = "iklim yang relatif stabil"
    if komoditas_bersih == "Padi":
        saran = "fokus pada manajemen penggenangan air dan pemupukan standar."
    elif komoditas_bersih == "Jagung/Palawija":
        saran = "pastikan saluran drainase berfungsi agar air tidak menggenangi akar."
    else:
        saran = "lakukan pemeliharaan tanaman sesuai prosedur standar komoditas."
elif skenario_cuaca == "El Niño (Kemarau)":
    kondisi = "curah hujan menurun dan suhu lebih panas"
    if komoditas_bersih == "Padi":
        saran = "persiapkan sistem irigasi pompa dan gunakan varietas toleran kekeringan."
    elif komoditas_bersih == "Jagung/Palawija":
        saran = "atur interval penyiraman berkala untuk menjaga kelembapan tanah."
    else:
        saran = "optimalkan penggunaan sumber air cadangan dan aplikasikan mulsa pelindung."
else:
    kondisi = "curah hujan ekstrem dan suhu relatif sejuk"
    if komoditas_bersih == "Padi":
        saran = "waspadai hama akibat kelembapan tinggi dan sesuaikan takaran pupuk Nitrogen."
    elif komoditas_bersih == "Jagung/Palawija":
        saran = "tinggikan bedengan untuk menghindari pembusukan akar akibat genangan air."
    else:
        saran = "perbaiki sistem pembuangan air di lahan dan awasi potensi penyakit jamur."
    
saran_agrikultur = f"Dengan proyeksi curah hujan {hujan_best:.1f} mm dan suhu {suhu_best:.1f} °C ({kondisi}), saran teknis untuk penanaman {komoditas_bersih} adalah {saran}"

if jenis_tanaman == "Kustom":
    desc_crop = "Catatan: Atribut kriteria ditentukan secara manual."
elif jenis_tanaman == "Padi":
    desc_crop = "Catatan: Padi membutuhkan curah hujan yang cukup (Benefit)."
elif jenis_tanaman == "Jagung/Palawija":
    desc_crop = "Catatan: Jagung rentan terhadap genangan air, sehingga curah hujan dihitung sebagai Cost."

st.title("Sistem Pendukung Keputusan Masa Tanam")
st.caption("Implementasi Metode SAW berdasarkan Historis Cuaca Harian")

if not st.session_state.hitung_spk:
    if not bobot_valid:
        st.error("Peringatan: Total bobot kriteria harus 1.0 agar perhitungan dapat dilakukan.")
    else:
        st.info("Silakan atur parameter di panel samping dan klik tombol 'Hitung SPK'.")
        st.caption(desc_crop)
else:
    st.success(f"Hasil Perangkingan: Bulan {best['Bulan']} menjadi alternatif terbaik untuk komoditas {komoditas_bersih} dengan nilai preferensi {best['Skor_SAW']:.4f}.")
    st.info(f"Saran Teknis: {saran_agrikultur}")
    st.caption(desc_crop)
    
st.divider()

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Data", "Hasil Perangkingan", "Visualisasi", "Perhitungan Matriks", "Profil"
])

with tab1:
    if skenario_cuaca != "Normal":
        st.warning(f"Menampilkan data dengan penyesuaian skenario: {skenario_cuaca}")
    
    st.subheader("Rata-rata Cuaca Bulanan")
    display = monthly[["Bulan","Curah_Hujan","Suhu_RataRata","Sinar_Matahari","Kecepatan_Angin","Kec_Gusts","Hari_Kering"]].copy()
    display.columns = ["Bulan","Curah Hujan (mm)","Suhu Rata-rata (°C)","Sinar Matahari (s)","Kec. Angin (km/h)","Kec. Gusts (km/h)","Hari Kering"]
    st.dataframe(display.set_index("Bulan").style.format("{:.2f}"), use_container_width=True)

    st.subheader("Dataset Mentah")
    with st.expander("Lihat Dataset Indonesia_weather_data.csv"):
        st.dataframe(df, use_container_width=True)

with tab2:
    if not st.session_state.hitung_spk:
        st.info("Selesaikan perhitungan untuk melihat hasil.")
    elif not bobot_valid:
        st.warning("Perbaiki nilai bobot terlebih dahulu.")
    else:
        c1, c2, c3 = st.columns(3)
        c1.success(f"Peringkat 1: {best['Bulan']} (Skor: {best['Skor_SAW']:.4f})")
        c2.info(f"Peringkat 2: {second['Bulan']} (Skor: {second['Skor_SAW']:.4f})")
        c3.warning(f"Peringkat 3: {third['Bulan']} (Skor: {third['Skor_SAW']:.4f})")

        st.subheader("Tabel Peringkat")
        ranking_display = eval_df[["Ranking","Bulan","Skor_SAW"]].copy()
        ranking_display.columns = ["Ranking","Bulan","Skor SAW"]
        st.dataframe(ranking_display.set_index("Ranking").style.format({"Skor SAW": "{:.4f}"}), use_container_width=True)

        csv_data = ranking_display.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Ekspor ke CSV",
            data=csv_data,
            file_name=f"Hasil_SAW_{komoditas_bersih.replace('/', '_')}_{periode}.csv",
            mime="text/csv",
            use_container_width=True
        )

        st.divider()
        with st.expander("Perbandingan Data Peringkat 1 dan 2"):
            comp_data = {
                "Kriteria": ["Skor SAW", "Curah Hujan (mm)", "Suhu Rata-rata (°C)", "Sinar Matahari (s)", "Kec. Angin (km/h)", "Kec. Gusts (km/h)", "Hari Kering"],
                f"Peringkat 1 ({best['Bulan']})": [
                    f"{best['Skor_SAW']:.4f}", f"{best['Curah_Hujan']:.2f}", f"{best['Suhu_RataRata']:.2f}",
                    f"{best['Sinar_Matahari']:.2f}", f"{best['Kecepatan_Angin']:.2f}", f"{best['Kec_Gusts']:.2f}", f"{best['Hari_Kering']:.2f}"
                ],
                f"Peringkat 2 ({second['Bulan']})": [
                    f"{second['Skor_SAW']:.4f}", f"{second['Curah_Hujan']:.2f}", f"{second['Suhu_RataRata']:.2f}",
                    f"{second['Sinar_Matahari']:.2f}", f"{second['Kecepatan_Angin']:.2f}", f"{second['Kec_Gusts']:.2f}", f"{second['Hari_Kering']:.2f}"
                ]
            }
            comp_df = pd.DataFrame(comp_data)
            st.table(comp_df.set_index("Kriteria"))

with tab3:
    if not st.session_state.hitung_spk:
        st.info("Selesaikan perhitungan untuk melihat grafik.")
    else:
        st.subheader("Grafik Hasil SAW")
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
        ax.set_title(f"Skor Akhir ({komoditas_bersih})")
        plt.tight_layout()
        st.pyplot(fig)

        st.divider()

        st.subheader("Distribusi Kriteria")
        kriteria_opt = st.selectbox(
            "Pilih Atribut:", ["Curah Hujan (mm)","Suhu Rata-rata (°C)","Sinar Matahari (s)","Kecepatan Angin (km/h)","Kec. Gusts (km/h)","Hari Kering"]
        )
        col_map = {
            "Curah Hujan (mm)": "Curah_Hujan", "Suhu Rata-rata (°C)": "Suhu_RataRata",
            "Sinar Matahari (s)": "Sinar_Matahari", "Kecepatan Angin (km/h)": "Kecepatan_Angin",
            "Kec. Gusts (km/h)": "Kec_Gusts", "Hari Kering": "Hari_Kering",
        }
        fig2, ax2 = plt.subplots(figsize=(10, 4))
        ax2.plot(monthly["Bulan"], monthly[col_map[kriteria_opt]], marker="o", color="#1976d2", linewidth=2)
        ax2.fill_between(monthly["Bulan"], monthly[col_map[kriteria_opt]], alpha=0.15, color="#1976d2")
        ax2.set_title(f"Rata-rata {kriteria_opt} per Bulan")
        ax2.set_ylabel(kriteria_opt)
        ax2.tick_params(axis="x", rotation=45)
        plt.tight_layout()
        st.pyplot(fig2)

        st.divider()
        
        st.subheader("Korelasi Curah Hujan dan Suhu")
        fig3, ax3 = plt.subplots(figsize=(10, 4))
        ax3.scatter(monthly["Curah_Hujan"], monthly["Suhu_RataRata"], color="#e91e63", s=100, alpha=0.7)
        for i, txt in enumerate(monthly["Bulan"]):
            ax3.annotate(txt, (monthly["Curah_Hujan"].iloc[i], monthly["Suhu_RataRata"].iloc[i]), 
                         xytext=(5, 5), textcoords="offset points", fontsize=9)
        ax3.set_xlabel("Curah Hujan (mm)")
        ax3.set_ylabel("Suhu Rata-rata (°C)")
        plt.tight_layout()
        st.pyplot(fig3)

with tab4:
    if not st.session_state.hitung_spk:
        st.info("Selesaikan perhitungan untuk melihat detail matriks.")
    else:
        st.subheader("Detail Perhitungan SAW")
        
        st.markdown("#### Proporsi Bobot")
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

        st.markdown("#### 1. Matriks Keputusan")
        raw_df = monthly.set_index("Bulan")[KRITERIA_COLS].copy()
        raw_df.columns = ["Curah Hujan","Suhu","Sinar Matahari","Kec. Angin","Kec. Gusts","Hari Kering"]
        st.dataframe(raw_df.style.format("{:.4f}"), use_container_width=True)

        st.markdown("#### 2. Matriks Normalisasi")
        norm_df = pd.DataFrame(
            norm_matrix, index=monthly["Bulan"],
            columns=[f"Curah Hujan ({tipe_hujan})", f"Suhu ({tipe_suhu})", f"Sinar Matahari ({tipe_sinar})", f"Kec. Angin ({tipe_angin})", f"Kec. Gusts ({tipe_gust})", f"Hari Kering ({tipe_kering})"]
        )
        st.dataframe(norm_df.style.format("{:.4f}").background_gradient(axis=0, cmap="YlGn"), use_container_width=True)

        st.markdown("#### 3. Nilai Preferensi")
        pref_df = monthly[["Bulan","Skor_SAW"]].copy()
        pref_df.columns = ["Bulan","Skor Akhir"]
        st.dataframe(pref_df.set_index("Bulan").style.format("{:.4f}").bar(color="#4caf50"), use_container_width=True)

with tab5:
    st.subheader("Profil Kelompok")
    col_prof1, col_prof2 = st.columns(2)
    with col_prof1:
        st.info("M. Dzikri Ginoga\n\nNIM: 123240237")
    with col_prof2:
        st.info("Bintang Shada Kawibya Putra\n\nNIM: 123240247")

st.divider()