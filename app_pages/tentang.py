"""Latar belakang aplikasi, profil pengembang, dan pembimbing."""

import streamlit as st

from firewatch.ui import page_header

page_header("Tentang Jakarta Siaga", "Membantu memahami kerawanan kebakaran melalui data yang lebih mudah dibaca.", "Tentang aplikasi")

with st.container(border=True):
    st.badge("PENELITIAN SKRIPSI", icon=":material/school:", color="orange")
    st.header("Pemahaman wilayah yang lebih baik, mitigasi yang lebih terarah.", anchor=False)
    st.markdown("Jakarta Siaga menyajikan hasil pengelompokan kelurahan DKI Jakarta berdasarkan indikator kondisi kelistrikan dan gas. Profil kepadatan penduduk dan peta koordinat melengkapi interpretasi agar hasil penelitian dapat dipahami pengguna nonteknis.")
    st.markdown("**Judul penelitian**")
    st.markdown("Klasterisasi Kelurahan Berdasarkan Indikator Kerawanan Kebakaran di DKI Jakarta Menggunakan Metode K-Means, Hierarchical Clustering, dan Spectral Bridges")

left, right = st.columns(2, gap="medium")
with left.container(border=True, height="stretch"):
    st.subheader("Profil pengembang", icon=":material/person:", anchor=False)
    st.markdown("**Mario Samuel Boediono**")
    st.caption("535230091 · Teknik Informatika")
    st.markdown("Fakultas Teknologi Informasi\n\nUniversitas Tarumanagara (UNTAR)")
    st.markdown("**Email**\n\nmario.535230091@stu.untar.ac.id")
with right.container(border=True, height="stretch"):
    st.subheader("Dosen pembimbing", icon=":material/school:", anchor=False)
    st.markdown("**Dr. Bagus Mulyawan, S.Kom., M.M.**")
    st.caption("Universitas Tarumanagara")

st.subheader("Ruang lingkup aplikasi", anchor=False)
st.markdown("Sembilan indikator fisik menggambarkan kondisi steker, stopkontak, kabel, tabung gas, regulator, selang, dan tata letak kompor. Seluruh analisis dijalankan otomatis dengan parameter penelitian yang tetap. Kepadatan penduduk dan koordinat digunakan untuk menyajikan profil hasil.")
st.caption("Aplikasi ini merupakan sarana pendukung penelitian dan pembacaan indikator kerawanan. Hasil bukan prediksi kejadian kebakaran atau penetapan status resmi wilayah.")
