"""Ringkasan dataset, peta, dan hasil algoritma berperingkat terbaik."""

import streamlit as st

from firewatch.analysis import FEATURES, FEATURE_LABELS, GAS, ELECTRICITY, LOW_RISK_LABEL, RISK_ORDER
from firewatch.charts import city_distribution, city_label, village_map
from firewatch.geography import BOUNDARY_SOURCE
from firewatch.state import ROOT, active_analysis, active_data
from firewatch.ui import number, page_header, profile_donut, risk_legend

page_header(
    "Ikhtisar kerawanan kebakaran",
    "Kenali pola kerawanan di setiap kelurahan untuk mendukung prioritas mitigasi yang lebih terarah.",
    "Beranda",
)

raw = active_data()
years = sorted(raw.tahun.unique())
with st.container(border=True):
    hero, illustration = st.columns([1.45, 1], gap="large", vertical_alignment="center")
    with hero:
        st.badge("MITIGASI BERBASIS DATA", color="orange", icon=":material/local_fire_department:")
        st.header("Kenali polanya. Tentukan prioritasnya.", anchor=False)
        st.markdown("Sembilan indikator kondisi listrik dan gas. Tiga metode klasterisasi. Satu gambaran untuk memahami kerawanan Jakarta.")
        with st.container(horizontal=True):
            if st.button("Lihat hasil klasterisasi", type="primary", icon=":material/arrow_forward:"):
                st.switch_page("app_pages/klasterisasi.py")
            if st.button("Jelajahi dataset", icon=":material/database:"):
                st.switch_page("app_pages/dataset.py")
    with illustration:
        st.image(str(ROOT / "assets" / "jakarta.svg"), width="stretch", alt="Ilustrasi Monas, bangunan Jakarta, dan titik data yang saling terhubung")

st.caption(f":material/calendar_today: Periode {', '.join(str(y) for y in years)}   ·   {number(len(raw))} observasi   ·   Sumber aktif: {st.session_state.dataset_name}")
analysis = active_analysis()
best = analysis.models[analysis.best_name]
villages = best.villages
attention = int(villages.interpretasi.ne(LOW_RISK_LABEL).sum())

metrics = [
    ("Kelurahan dianalisis", number(len(villages)), ":material/location_city:", "Satu baris hasil per kelurahan setelah rata-rata antarperiode."),
    ("Indikator kerawanan", "9", ":material/electric_bolt:", "Empat indikator kelistrikan dan lima indikator kondisi gas."),
    ("Metode dibandingkan", str(len(analysis.models)), ":material/hub:", "K-Means, AHC Ward, dan Spectral Bridges. Sistem mencari jumlah klaster secara otomatis."),
    ("Perlu perhatian", number(attention), ":material/local_fire_department:", f"Kelurahan dengan indeks centroid listrik atau gas >0 pada hasil {analysis.best_name}."),
]
for col, (label, value, icon, help_text) in zip(st.columns(4, gap="small"), metrics):
    col.metric(label, value, icon=icon, border=True, help=help_text, height="stretch")

with st.container(horizontal=True, horizontal_alignment="distribute", vertical_alignment="center"):
    st.subheader("Gambaran kerawanan wilayah", anchor=False)
    st.badge(f"Hasil utama: {analysis.best_name} · {best.k} klaster", icon=":material/verified:", color="green")

left, right = st.columns([2.15, 1], gap="medium")
with left.container(border=True, height="stretch"):
    st.markdown("**Peta kerawanan kebakaran**")
    st.pydeck_chart(village_map(villages, height=325), height=325, key="home_map", alt="Peta interaktif kelurahan DKI Jakarta yang diwarnai berdasarkan interpretasi kerawanan")
    risk_legend(villages, compact=True)
    st.caption("Garis tebal: provinsi/kota · Garis tipis: kecamatan · Titik: profil kelurahan. Geser atau zoom peta; arahkan penunjuk pada titik untuk rinciannya. Seluruh data Kepulauan Seribu tetap tercakup dalam hasil.")
    st.caption(f"Batas: [DPMPTSP DKI Jakarta]({BOUNDARY_SOURCE}), disederhanakan untuk visualisasi. Batas tersimpan lokal; latar geografis CARTO/OpenStreetMap memerlukan internet.")
with right.container(border=True, height="stretch"):
    st.markdown("**Komposisi profil kerawanan**")
    profile_donut(villages, "home_risk_donut")
    st.caption(f"Interpretasi relatif terhadap dataset. {LOW_RISK_LABEL} bukan kepastian bebas kebakaran.")

region, summary = st.columns([1.2, 1], gap="medium")
with region.container(border=True, height="stretch"):
    st.subheader("Sebaran di wilayah administrasi", anchor=False)
    st.altair_chart(city_distribution(villages), key="home_city_distribution", alt="Jumlah kelurahan dalam setiap kategori kerawanan di enam wilayah administrasi Jakarta")
with summary.container(border=True, height="stretch"):
    st.subheader("Dari data menuju tindakan", anchor=False)
    st.markdown(f"**{number(attention)} kelurahan** memiliki profil klaster dengan indikator listrik atau gas yang menonjol pada hasil **{analysis.best_name}**.")
    st.markdown("**01 · Kenali wilayah**\n\nTelusuri peta dan profil kelurahan untuk memahami pola kerawanan.")
    st.markdown("**02 · Baca faktor yang menonjol**\n\nBandingkan kondisi kelistrikan, gas, dan konteks kepadatan penduduk.")
    st.markdown("**03 · Susun prioritas mitigasi**\n\nGunakan hasil sebagai bahan pendukung pemeriksaan lapangan dan edukasi warga.")
    if st.button("Telusuri profil setiap kelurahan", icon=":material/arrow_forward:", key="home_explore"):
        st.switch_page("app_pages/klasterisasi.py")

st.subheader("Indikator yang digunakan", anchor=False)
st.caption("Semua indikator berikut berupa persentase. Kepadatan penduduk dan koordinat melengkapi profil hasil.")
descriptions = {
    "steker_menumpuk": "Pemakaian steker bertumpuk yang melebihi kapasitas.",
    "steker_hangus": "Kondisi steker listrik yang rusak akibat panas.",
    "stopkontak_kendur": "Kondisi stopkontak yang longgar kerapatannya.",
    "kabel_rusak": "Kondisi fisik kabel listrik yang rusak.",
    "tabung_rusak": "Kondisi tabung gas yang cacat.",
    "selang_longgar": "Alat pengikat selang gas yang kendur.",
    "regulator_rusak": "Kondisi regulator yang rusak.",
    "selang_tertindih": "Kondisi selang gas yang terjepit benda berat.",
    "kompor_berdekatan": "Tata letak dua kompor gas yang berdekatan.",
}
for col, (title, features, icon) in zip(st.columns(2, gap="medium"), [
    ("Kondisi kelistrikan", ELECTRICITY, ":material/electric_bolt:"),
    ("Kondisi gas", GAS, ":material/propane_tank:"),
]):
    with col.container(border=True, height="stretch"):
        st.subheader(title, icon=icon, anchor=False)
        for feature in features:
            st.markdown(f"**{FEATURE_LABELS[feature]}** :gray[· {descriptions[feature]}]")

with st.expander("Latar belakang dan tujuan penelitian", icon=":material/school:"):
    st.markdown("**Klasterisasi Kelurahan Berdasarkan Indikator Kerawanan Kebakaran di DKI Jakarta Menggunakan Metode K-Means, Hierarchical Clustering, dan Spectral Bridges**")
    st.markdown("Penelitian ini mengelompokkan kelurahan berdasarkan indikator kerawanan kebakaran dan membandingkan performa tiga metode dengan Silhouette Score, Davies–Bouldin Index, dan Calinski–Harabasz Index.")
    st.markdown("Integrasi kondisi fisik listrik dan gas dengan konteks kepadatan penduduk menghasilkan profil wilayah yang lebih terperinci. Visualisasi dirancang agar mudah dibaca pengguna nonteknis dan membantu instansi terkait menyusun prioritas mitigasi berbasis data.")
