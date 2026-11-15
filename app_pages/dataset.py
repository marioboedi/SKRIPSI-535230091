"""Unggah, validasi, pencarian, filter, dan reset dataset aktif."""

from hashlib import sha256

import streamlit as st

from firewatch.analysis import KEYS, REQUIRED, DatasetError
from firewatch.charts import city_label
from firewatch.regions import filter_region, region_options
from firewatch.state import DRIVE_URL, activate_dataset, active_data, dataset_key, reset_dataset
from firewatch.ui import dataframe_config, number, page_header, region_search

page_header("Dataset penelitian", "Jelajahi data awal atau unggah CSV untuk memperbarui seluruh hasil klasterisasi.", "Dataset")

upload_col, download_col = st.columns([1.35, 1], gap="medium")
with upload_col.container(border=True, height="stretch"):
    st.subheader("Gunakan dataset Anda", icon=":material/upload_file:", anchor=False)
    st.caption("Unggah CSV dengan kolom yang sama seperti 2425.csv. Data valid langsung menjadi sumber seluruh halaman.")
    upload = st.file_uploader("Pilih dataset CSV", type=["csv"], max_upload_size=20, key=f"dataset_upload_{st.session_state.upload_nonce}", help="Maksimal 20 MB. Pemisah koma atau titik koma didukung; persentase harus 0–100.")
    if upload is not None:
        contents = upload.getvalue()
        signature = (upload.name, sha256(contents).hexdigest())
        if signature != st.session_state.last_upload:
            try:
                activate_dataset(contents, upload.name)
                st.session_state.last_upload = signature
                st.toast("Dataset aktif diperbarui. Hasil analisis mengikuti data ini.", icon=":material/check_circle:")
                st.rerun()
            except DatasetError as exc:
                st.session_state.upload_error = str(exc)
                st.session_state.last_upload = signature
    if st.session_state.upload_error:
        st.error(st.session_state.upload_error, icon=":material/error:", title="Unggahan perlu diperbaiki")
        st.caption("Dataset aktif sebelumnya tetap tersedia.")

with download_col.container(border=True, height="stretch"):
    st.subheader("Sumber dataset", icon=":material/download:", anchor=False)
    st.markdown("**2425.csv** · Data indikator kelurahan periode 2024 dan 2025.")
    st.caption("Akses data penelitian melalui sumber Google Drive.")
    st.link_button("Data Terbaru", DRIVE_URL, icon=":material/open_in_new:", type="primary")
    st.caption("Akses unduhan Drive mengikuti izin berbagi pemilik file.")
    if st.button("Kembali ke dataset awal", icon=":material/restart_alt:", key="reset_dataset"):
        reset_dataset()
        st.rerun()

raw = active_data()
key = dataset_key()
suggestions = region_options(raw)
st.badge(f"Dataset aktif: {st.session_state.dataset_name}", color="green", icon=":material/check_circle:")
for col, (label, value, icon) in zip(st.columns(4, gap="small"), [
    ("Baris observasi", number(len(raw)), ":material/table_rows:"),
    ("Kelurahan unik", number(len(raw[KEYS].drop_duplicates())), ":material/location_city:"),
    ("Periode tahun", str(raw.tahun.nunique()), ":material/calendar_today:"),
    ("Indikator analisis", "9", ":material/monitoring:"),
]):
    col.metric(label, value, icon=icon, border=True)

st.subheader("Jelajahi data mentah", anchor=False)
with st.container(border=True):
    cols = st.columns([1.3, 1.3, 1], vertical_alignment="bottom")
    with cols[0]:
        query = region_search(suggestions, key=f"dataset_search_{key}")
    with cols[1]:
        cities = st.multiselect("Wilayah administrasi", sorted(raw.kota.unique()), format_func=city_label, placeholder="Semua wilayah", key=f"dataset_city_{key}")
    with cols[2]:
        years = st.multiselect("Periode tahun", sorted(raw.tahun.unique()), placeholder="Semua periode", key=f"dataset_year_{key}")
filtered = filter_region(raw, query, suggestions)
if cities:
    filtered = filtered[filtered.kota.isin(cities)]
if years:
    filtered = filtered[filtered.tahun.isin(years)]

st.caption(f"{number(len(filtered))} dari {number(len(raw))} observasi · Klik judul kolom untuk mengurutkan data. Ekspor CSV tersedia pada menu tabel.")
st.dataframe(filtered, hide_index=True, height=455, column_config=dataframe_config(), key=f"raw_dataset_{key}", alt="Tabel interaktif data mentah berisi periode, wilayah, sembilan persentase indikator, kepadatan, dan koordinat")
if filtered.empty:
    st.info("Tidak ada data yang sesuai dengan pencarian dan filter.", icon=":material/search_off:")
st.caption("Pencarian dan filter di halaman ini hanya membatasi tabel. Analisis selalu memakai seluruh dataset aktif.")

with st.expander("Format CSV dan pemeriksaan data", icon=":material/fact_check:"):
    st.markdown("CSV perlu memuat 17 kolom berikut. Gunakan tabel dataset sebagai acuan format.")
    st.code(",".join(REQUIRED), language=None, wrap_lines=True)
    st.markdown("Nama wilayah harus terisi; tahun dan semua indikator harus berupa angka yang valid. Persentase berada pada rentang 0–100. Satu kombinasi tahun, kota, kecamatan, dan kelurahan hanya boleh muncul sekali. Nilai kosong tidak diisi otomatis.")
    st.markdown("Sembilan indikator distandardisasi menggunakan Z-score **secara terpisah pada setiap tahun**, kemudian dirata-ratakan antarperiode berdasarkan **kota + kecamatan + kelurahan**. Kepadatan, koordinat, elevasi, dan persentase asli dirata-ratakan antarperiode untuk melengkapi profil; hanya sembilan indikator Z-score agregasi masuk ke model.")
    st.caption("Unggahan disimpan dalam sesi aplikasi. Memuat ulang sebagai sesi baru akan kembali memakai dataset bawaan.")
