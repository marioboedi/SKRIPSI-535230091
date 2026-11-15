"""Perbandingan algoritma, hasil model, evaluasi, dan metodologi penelitian."""

import streamlit as st

from firewatch.state import active_analysis, dataset_key
from firewatch.ui import number, page_header, report_zip, show_model

page_header("Hasil klasterisasi", "Tiga pendekatan, satu alur otomatis. Bandingkan kualitas klaster dan telusuri profil setiap kelurahan.", "Klasterisasi")

with st.container(horizontal=True, gap="small"):
    st.badge("Z-score per tahun → rata-rata kelurahan", color="gray", icon=":material/transform:")
    st.badge("Pencarian K otomatis: 2–10", color="gray", icon=":material/hub:")
    st.badge("Parameter penelitian tetap", color="gray", icon=":material/lock:")

result = active_analysis()
for note in result.prepared.notes:
    st.warning(note, icon=":material/info:")
for name, error in result.failures.items():
    st.warning(f"{name} belum tersedia: {error}", icon=":material/warning:")

with st.container(border=True):
    with st.container(horizontal=True, horizontal_alignment="distribute", vertical_alignment="center"):
        st.markdown(f"**:material/verified: {result.best_name}** memiliki peringkat evaluasi terbaik pada dataset ini.")
        ahc_tab = st.session_state.get(f"algorithm_tabs_{dataset_key()}", result.best_name) == "AHC"
        st.download_button("Unduh laporan lengkap", report_zip(result, ahc_tab=ahc_tab), file_name="laporan_jakarta_siaga.zip", mime="application/zip", icon=":material/download:", type="primary", on_click="ignore")
    st.caption(f"{number(len(result.prepared.raw))} observasi → {number(len(result.prepared.villages))} kelurahan · Dataset: {st.session_state.dataset_name}")
    top = result.ranking.iloc[0]
    tied = result.ranking[
        result.ranking.rata_rata_peringkat.eq(top.rata_rata_peringkat)
        & result.ranking.silhouette.eq(top.silhouette)
    ].algoritma.tolist()
    if len(tied) > 1:
        st.caption(f"Peringkat teratas setara: {', '.join(tied)}. Urutan nama algoritma menentukan tampilan pertama ketika hasil evaluasi seri.")
    with st.expander("Bandingkan performa ketiga algoritma", icon=":material/compare_arrows:", on_change="rerun", key=f"comparison_{dataset_key()}") as comparison:
        if comparison.open:
            ranking = result.ranking[["algoritma", "k", "silhouette", "dbi", "chi", "rata_rata_peringkat"]].copy()
            st.dataframe(ranking, hide_index=True, column_config={
                "algoritma": "Algoritma", "k": "K optimal",
                "silhouette": st.column_config.NumberColumn("Silhouette ↑", format="%.4f"),
                "dbi": st.column_config.NumberColumn("DBI ↓", format="%.4f"),
                "chi": st.column_config.NumberColumn("CHI ↑", format="%.4f"),
                "rata_rata_peringkat": st.column_config.NumberColumn("Rata-rata peringkat ↓", format="%.2f"),
            }, alt="Perbandingan metrik final tiga algoritma, diurutkan berdasarkan rata-rata peringkat")
            st.caption("Silhouette Plot untuk masing-masing algoritma tersedia melalui tombol **Silhouette Plot** di bawah nilai Silhouette Score pada tab hasil setiap algoritma.")
            st.caption("Sistem membandingkan peringkat setiap metrik, bukan menjumlahkan skor yang berbeda skala. Rata-rata peringkat paling rendah ditampilkan lebih dahulu; seri diputus dengan Silhouette lebih tinggi, lalu nama algoritma. Ini menunjukkan kualitas pemisahan klaster, bukan akurasi prediksi kejadian kebakaran.")

names = result.ranking.algoritma.tolist()
tabs = st.tabs(names, default=names[0], on_change="rerun", key=f"algorithm_tabs_{dataset_key()}")
for name, tab in zip(names, tabs):
    if tab.open:
        with tab:
            show_model(result.models[name], name == result.best_name, result.prepared, result.models)

with st.expander("Alur analisis dan parameter penelitian", icon=":material/account_tree:", on_change="rerun") as methodology:
    if methodology.open:
        st.markdown("**1. Validasi data.** Hanya CSV yang memenuhi kolom dan pemeriksaan nilai diterima.")
        st.markdown("**2. Standardisasi per tahun.** Setiap indikator memakai Z = (x − μ_tahun) / σ_tahun secara terpisah untuk setiap tahun, dengan simpangan baku populasi (ddof=0). Pada dataset bawaan, standardisasi 2024 dan 2025 dihitung sendiri-sendiri. Indikator yang konstan pada suatu tahun menghasilkan Z=0 pada tahun tersebut.")
        st.markdown("**3. Agregasi.** Setelah standardisasi per tahun, Z-score dirata-ratakan antarperiode per kota, kecamatan, dan kelurahan. Pada dataset bawaan, 534 observasi menjadi 267 kelurahan. Baris hasil diurutkan menurut kota, kecamatan, lalu kelurahan untuk menjaga reproduksibilitas. Kepadatan dan koordinat hanya menjadi informasi hasil.")
        st.markdown("**4. Pencarian K.** Masing-masing metode menguji K=2–10. Silhouette dan CHI dimaksimalkan, DBI diminimalkan. K yang didukung minimal dua metrik dipilih. Jika ketiganya berbeda, gunakan rata-rata peringkat terbaik, lalu Silhouette lebih tinggi, lalu K lebih kecil.")
        st.markdown("**5. Model final.** Model dihitung kembali memakai K terpilih. Tiga metrik final dihitung dari label model final, dan hasil disimpan dalam cache berdasarkan isi dataset.")
        st.markdown("**6. Interpretasi.** Indeks listrik dan gas dihitung dari rata-rata centroid empat dan lima indikator terkait. Ambang >0 menentukan faktor dominan. Nomor klaster diurutkan dari rata-rata centroid sembilan indikator tertinggi untuk memudahkan pembacaan; tidak menyatakan probabilitas kebakaran.")
        st.table({
            "K-Means": "random_state=11 · n_init=10",
            "AHC": "linkage=ward · jarak Euclidean",
            "Spectral Bridges": "random_state=549 · n_nodes=15 · p=2 · paket spectral-bridges asli",
        }, border="horizontal", alt="Parameter tetap yang digunakan oleh tiga algoritma penelitian")
        st.caption("Untuk dataset kecil, kandidat K dibatasi hingga n−1. Spectral Bridges memerlukan minimal 15 kelurahan dengan pola indikator berbeda. K yang gagal atau menghasilkan klaster lebih sedikit dari yang diminta dilaporkan dan dikeluarkan dari pemilihan.")
