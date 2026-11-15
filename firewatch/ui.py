"""Reusable native Streamlit presentation components."""

from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st

from firewatch.analysis import (
    FEATURES, FEATURE_LABELS, LOW_RISK_LABEL, RISK_LABEL_VERSION, RISK_ORDER,
    ModelResult, PreparedData,
)
from firewatch.charts import (
    centroid_heatmap, city_label, cluster_distribution, cluster_donut, density_chart,
    indicator_comparison, risk_distribution, risk_donut, village_map,
)
from firewatch.evaluation_ui import show_model_evaluation, show_silhouette_panel
from firewatch.geography import BOUNDARY_SOURCE
from firewatch.profiles import ahc_profile_details, ahc_tab_result
from firewatch.regions import filter_region, region_options
from firewatch.reports import csv_bytes, report_zip  # Preserve existing page imports.
from firewatch.state import cached_figure, dataset_key

RISK_BADGE = {
    "Dominan Bahaya Keduanya": "red",
    "Dominan Bahaya Kelistrikan": "orange",
    "Dominan Bahaya Gas": "yellow",
    LOW_RISK_LABEL: "green",
}
MITIGATION = {
    "Dominan Bahaya Keduanya": "Prioritaskan pendataan dan pemeriksaan kondisi kelistrikan serta perangkat gas di wilayah ini.",
    "Dominan Bahaya Kelistrikan": "Prioritaskan pemeriksaan instalasi, beban steker, stopkontak, dan kondisi kabel oleh petugas yang kompeten.",
    "Dominan Bahaya Gas": "Prioritaskan pemeriksaan kondisi tabung, regulator, selang, dan tata letak kompor oleh petugas yang kompeten.",
    LOW_RISK_LABEL: "Pertahankan pemantauan dan edukasi rutin. Nilai indikator relatif rendah tetap memerlukan upaya pencegahan.",
}


def number(value: float, decimals: int = 0) -> str:
    return f"{value:,.{decimals}f}".replace(",", "_").replace(".", ",").replace("_", ".")


def region_search(options: dict, key: str):
    return st.selectbox(
        "Cari kelurahan / kecamatan", list(options), index=None, key=key,
        placeholder="Ketik sebagian nama wilayah…", accept_new_options=True,
        filter_mode="contains",
        help="Saran berasal dari dataset aktif. Pilih dengan klik atau tombol panah dan Enter. Untuk mencari semua nama yang mengandung kata tertentu, ketik lalu tekan Enter. Hapus pilihan untuk menampilkan semua wilayah.",
    )


def page_header(title: str, subtitle: str, section: str) -> None:
    with st.container(horizontal=True, horizontal_alignment="distribute", vertical_alignment="center"):
        st.caption(f"JAKARTA SIAGA  /  {section.upper()}")
        st.badge("DKI Jakarta", icon=":material/location_on:", color="gray")
    st.title(title)
    st.markdown(f":gray[{subtitle}]")


def footer() -> None:
    st.space("small")
    st.caption("Jakarta Siaga · Penelitian Teknik Informatika, Universitas Tarumanagara · Mario Samuel Budiono")


def risk_legend(villages: pd.DataFrame, compact: bool = False) -> None:
    summary = risk_distribution(villages)
    if compact:
        with st.container(horizontal=True, gap="small"):
            for row in summary.itertuples(index=False):
                if row.jumlah:
                    st.badge(f"{row.kategori} · {row.jumlah}", color=RISK_BADGE[row.interpretasi])
    else:
        composition_legend(summary)


def composition_legend(summary: pd.DataFrame, *, show_profiles: bool = False) -> None:
    """One responsive legend for profile and cluster compositions.

    Native SVG images retain the exact chart color, including all ten possible
    cluster colors, while native text can wrap independently on narrow screens.
    """
    for row in summary.itertuples(index=False):
        with st.container(horizontal=True, horizontal_alignment="distribute", vertical_alignment="center", gap="small"):
            label = escape(row.kategori)
            color = escape(row.warna, quote=True)
            badge_width = 16 + round(len(row.kategori) * 7)
            badge = f'<svg xmlns="http://www.w3.org/2000/svg" width="{badge_width}" height="22" viewBox="0 0 {badge_width} 22"><rect width="{badge_width}" height="22" rx="4" fill="{color}" fill-opacity="0.13"/><text x="8" y="15.5" fill="{color}" font-family="Inter,Arial,sans-serif" font-size="12" font-weight="500">{label}</text></svg>'
            st.image(badge, width="content", alt=row.kategori)
            st.markdown(f"**{int(row.jumlah)} kelurahan** · {number(row.persentase * 100, 1)}%")
        if show_profiles:
            if hasattr(row, "profil_karakteristik"):
                st.caption(f"Profil kerawanan: {row.interpretasi} · {row.profil_karakteristik}")
                electricity = ("+" if row.risk_listrik > 0 else "") + number(row.risk_listrik, 3)
                gas = ("+" if row.risk_gas > 0 else "") + number(row.risk_gas, 3)
                st.caption(f"Indeks listrik {electricity} · Indeks gas {gas}")
            else:
                st.caption(f"Profil kerawanan: {row.interpretasi}")


def small_slice_note(summary: pd.DataFrame) -> None:
    small = summary.query("jumlah > 0 and persentase < 0.01")
    if not small.empty:
        details = "; ".join(f"{row.kategori}: {row.jumlah} kelurahan ({number(row.persentase * 100, 1)}%)" for row in small.itertuples(index=False))
        st.caption(f"Irisan kecil — {details}. Semua proporsi mengikuti jumlah kelurahan sebenarnya.")


def profile_donut(villages: pd.DataFrame, key: str) -> None:
    st.altair_chart(risk_donut(villages), key=key, alt="Proporsi kelurahan menurut empat interpretasi kerawanan kebakaran")
    risk_legend(villages)
    small_slice_note(risk_distribution(villages))


def dataframe_config() -> dict:
    return {
        "kelurahan": st.column_config.TextColumn("Kelurahan", pinned=True),
        "kecamatan": "Kecamatan",
        "kota": "Wilayah administrasi",
        "tahun": st.column_config.NumberColumn("Tahun", format="%d"),
        "klaster": st.column_config.NumberColumn("Klaster", format="%d"),
        "interpretasi": "Interpretasi kerawanan",
        "risk_listrik": st.column_config.NumberColumn("Indeks listrik (Z)", format="%.3f"),
        "risk_gas": st.column_config.NumberColumn("Indeks gas (Z)", format="%.3f"),
        "kepadatan_penduduk": st.column_config.NumberColumn("Kepadatan (jiwa/km²)", format="localized"),
        "latitude": st.column_config.NumberColumn("Latitude", format="%.6f"),
        "longitude": st.column_config.NumberColumn("Longitude", format="%.6f"),
        "elevation": st.column_config.NumberColumn("Elevasi (m)", format="%.1f"),
        "profil_kepadatan": "Profil kepadatan",
        "periode": "Periode data",
        "jumlah_periode": "Jumlah periode",
        **{feature: st.column_config.NumberColumn(FEATURE_LABELS[feature] + " (%)", format="%.2f%%") for feature in FEATURES},
    }


def results_table(data: pd.DataFrame, key: str) -> None:
    columns = ["kelurahan", "kecamatan", "kota", "klaster", "interpretasi", "risk_listrik", "risk_gas", "kepadatan_penduduk", "profil_kepadatan", "latitude", "longitude", "elevation", "periode", *FEATURES]
    st.dataframe(data[columns], hide_index=True, height=360, column_config=dataframe_config(), key=key, alt="Hasil klaster dan profil kerawanan setiap kelurahan; tabel dapat diurutkan dan diunduh")


def show_metrics(
    model: ModelResult,
    prepared: PreparedData,
    models: dict[str, ModelResult],
    prefix: str,
) -> None:
    cols = st.columns(4, gap="small")
    cards = [
        ("Klaster optimal", str(model.k), ":material/hub:", "Dipilih otomatis dari kandidat K=2–10 yang valid."),
        ("Silhouette ↑", number(model.metrics["silhouette"], 4), ":material/monitoring:", "Semakin tinggi, semakin jelas pemisahan klaster. Rentang −1 sampai 1."),
        ("Davies–Bouldin ↓", number(model.metrics["dbi"], 4), ":material/compare_arrows:", "Semakin rendah, semakin baik pemisahan dan kekompakan klaster."),
        ("Calinski–Harabasz ↑", number(model.metrics["chi"], 4), ":material/query_stats:", "Semakin tinggi, semakin baik perbandingan variasi antar- dan dalam klaster."),
    ]
    open_key = f"{prefix}_silhouette_open"
    for col, (label, value, icon, help_text) in zip(cols, cards):
        col.metric(label, value, border=True, icon=icon, help=help_text, height="stretch")
    actions = st.columns(4, gap="small")
    with actions[1]:
        if st.button(
            "Silhouette Plot",
            key=f"{prefix}_silhouette_button",
            icon=":material/monitoring:",
            help=(
                "Tampilkan Silhouette Plot untuk algoritma yang dipilih. Grafik memakai "
                "koefisien setiap kelurahan dari label klaster final dan data Z-score "
                "yang sama dengan nilai Silhouette Score."
            ),
            type="secondary",
            width="stretch",
        ):
            st.session_state[open_key] = not st.session_state.get(open_key, False)
    if st.session_state.get(open_key):
        show_silhouette_panel(prepared, models, model.name, prefix, open_key)


def show_village_detail(model: ModelResult, filtered: pd.DataFrame, prefix: str) -> None:
    if filtered.empty:
        return
    st.subheader("Kenali profil kelurahan", anchor=False)
    options = filtered.index.tolist()
    selected = st.selectbox(
        "Pilih kelurahan untuk melihat rincian", options,
        format_func=lambda i: f"{filtered.loc[i, 'kelurahan'].title()} · {filtered.loc[i, 'kecamatan'].title()} · {city_label(filtered.loc[i, 'kota'])}",
        key=f"{prefix}_detail",
    )
    row = filtered.loc[selected]
    with st.container(border=True):
        left, right = st.columns([1, 1.5], gap="large")
        with left:
            st.subheader(row.kelurahan.title(), anchor=False)
            st.caption(f"{row.kecamatan.title()} · {city_label(row.kota)}")
            st.badge(row.interpretasi, color=RISK_BADGE[row.interpretasi])
            st.markdown(MITIGATION[row.interpretasi])
            st.markdown(f"**Klaster {int(row.klaster)}** · {row.periode}")
            st.caption(f"Kepadatan: {number(row.kepadatan_penduduk)} jiwa/km² · {row.profil_kepadatan}\n\nElevasi: {number(row.elevation, 1)} m · Koordinat: {row.latitude:.5f}, {row.longitude:.5f}")
            st.caption(f"Indeks centroid klaster — listrik: {number(row.risk_listrik, 3)} · gas: {number(row.risk_gas, 3)}. Indeks ini berlaku bersama untuk anggota klaster.")
        with right:
            st.altair_chart(indicator_comparison(row, model.villages[FEATURES].mean()), key=f"{prefix}_indicators", alt="Perbandingan sembilan indikator rata-rata kelurahan terpilih dengan rata-rata seluruh kelurahan")


def show_model(model: ModelResult, recommended: bool, prepared: PreparedData, models: dict[str, ModelResult] | None = None) -> None:
    prefix = f"result_{dataset_key()}_{model.name.replace(' ', '_')}"
    models = models or {model.name: model}
    ahc_details = ahc_profile_details(prepared, model) if model.name == "AHC" else None
    model = ahc_tab_result(model)
    with st.container(horizontal=True, horizontal_alignment="distribute", vertical_alignment="center"):
        st.markdown(f"### {model.name}")
        if recommended:
            st.badge("Peringkat evaluasi terbaik", color="green", icon=":material/verified:")
    show_metrics(model, prepared, models, prefix)
    st.caption(model.selection)
    smallest = int(model.profiles.jumlah_kelurahan.min())
    largest = int(model.profiles.jumlah_kelurahan.max())
    if smallest == 1 or largest / len(model.villages) > .95:
        st.info(
            f"Ukuran klaster tidak seimbang: klaster terkecil {smallest} kelurahan dan terbesar {largest}. "
            "Pola yang sangat berbeda dapat membentuk klaster kecil. Baca profil centroid dan bandingkan metode lain sebelum menafsirkan keseluruhan wilayah.",
            icon=":material/info:",
        )
    views = st.tabs(["Peta & kelurahan", "Profil klaster", "Evaluasi & pemilihan K", "Analisis data"], key=f"{prefix}_views", on_change="rerun")

    if views[0].open:
        with views[0]:
            suggestions = region_options(model.villages)
            with st.container(border=True):
                filters = st.columns([1.25, 1.4, 1.25], vertical_alignment="bottom")
                with filters[0]:
                    search = region_search(suggestions, key=f"{prefix}_search")
                with filters[1]:
                    cities = st.multiselect("Wilayah administrasi", sorted(model.villages.kota.unique()), format_func=city_label, placeholder="Semua wilayah", key=f"{prefix}_cities")
                with filters[2]:
                    risks = st.multiselect("Profil kerawanan", RISK_ORDER, placeholder="Semua profil", key=f"{prefix}_risks_{RISK_LABEL_VERSION}")
            filtered = filter_region(model.villages, search, suggestions)
            if cities:
                filtered = filtered[filtered.kota.isin(cities)]
            if risks:
                filtered = filtered[filtered.interpretasi.isin(risks)]
            st.caption(f"Menampilkan {number(len(filtered))} dari {number(len(model.villages))} kelurahan. Filter hanya mengubah tampilan hasil.")
            if filtered.empty:
                st.info("Tidak ada kelurahan yang cocok. Ubah kata pencarian atau filter.", icon=":material/search_off:")
            else:
                st.caption(f"{model.name} menghasilkan {model.k} klaster dan {model.villages.interpretasi.nunique()} kategori profil kerawanan. Beberapa klaster dapat memiliki profil kerawanan yang sama.")
                map_col, profile_col = st.columns([2.15, 1], gap="medium")
                with map_col.container(border=True, height="stretch"):
                    st.subheader("Peta kerawanan kebakaran", anchor=False)
                    with st.container(horizontal=True):
                        terrain = st.toggle("Tampilan elevasi", key=f"{prefix}_terrain")
                        detailed = st.toggle("Batas kelurahan", key=f"{prefix}_boundaries")
                    st.pydeck_chart(village_map(filtered, height=370, terrain=terrain, detailed=detailed, color_by="klaster"), height=370, key=f"{prefix}_map", alt="Peta klaster kelurahan Jakarta; warna sesuai nomor klaster dan tooltip memuat profil kerawanan")
                    st.caption("Garis tebal: provinsi/kota · Garis tipis: kecamatan/kelurahan. Warna titik mengikuti nomor klaster pada diagram. Geser atau zoom peta dan arahkan penunjuk ke titik untuk melihat klaster dan profil kerawanannya. Tampilan elevasi memakai posisi vertikal sebenarnya dalam meter.")
                    st.caption(f"Batas: [DPMPTSP DKI Jakarta]({BOUNDARY_SOURCE}), disederhanakan untuk visualisasi. Batas tersedia lokal; latar geografis CARTO/OpenStreetMap memerlukan internet.")
                with profile_col.container(border=True, height="stretch"):
                    # One final-label summary drives the chart and every legend
                    # row for all three algorithms, including equal risk profiles.
                    summary = cluster_distribution(filtered)
                    if ahc_details is not None:
                        summary = summary.merge(
                            ahc_details[["klaster", "profil_karakteristik", "risk_listrik", "risk_gas"]],
                            on="klaster", how="left", validate="one_to_one", sort=False,
                        )
                    st.subheader("Sebaran klaster dan profil", anchor=False)
                    st.caption(f"{len(summary)} klaster · {number(int(summary.jumlah.sum()))} kelurahan")
                    st.altair_chart(cluster_donut(summary), key=f"{prefix}_composition", alt=f"Sebaran {len(summary)} klaster {model.name} beserta profil kerawanan, jumlah dan persentase kelurahan; warna sesuai peta")
                    composition_legend(summary, show_profiles=True)
                    profile_source = "Karakteristik berasal dari centroid; kategori mengikuti profil pada hasil AHC." if ahc_details is not None else "Profil kerawanan berasal dari centroid masing-masing klaster."
                    st.caption(f"Menampilkan {len(summary)} dari {model.k} klaster model sesuai filter aktif. Persentase dihitung dari {number(len(filtered))} kelurahan yang ditampilkan. {profile_source}")
                    small_slice_note(summary)
                with st.container(horizontal=True, horizontal_alignment="distribute", vertical_alignment="center"):
                    st.subheader("Hasil per kelurahan", anchor=False)
                    st.download_button("Unduh hasil tampilan", csv_bytes(filtered), file_name=f"hasil_{model.name.lower().replace(' ', '_')}.csv", mime="text/csv", icon=":material/download:", key=f"{prefix}_download", on_click="ignore")
                results_table(filtered, f"{prefix}_table")
                show_village_detail(model, filtered, prefix)
            if model.name == "AHC":
                st.caption("Kategori profil AHC berlaku untuk seluruh kelurahan yang termasuk dalam klaster tersebut.")
            else:
                st.caption(f'"{LOW_RISK_LABEL}" berarti kedua indeks centroid ≤ 0 relatif terhadap dataset. Label ini bukan kepastian bebas kebakaran.')

    if views[1].open:
        with views[1]:
            st.markdown("#### Apa yang membedakan setiap klaster?")
            st.caption("Z-score dihitung terhadap rata-rata indikator pada tahun masing-masing, lalu dirata-ratakan antarperiode. Nilai centroid positif menunjukkan kondisi yang rata-rata berada di atas acuan tahun tersebut.")
            st.altair_chart(centroid_heatmap(model.profiles), key=f"{prefix}_heatmap", alt="Peta panas sembilan centroid indikator Z-score menurut klaster")
            summary = model.profiles[["klaster", "jumlah_kelurahan", "interpretasi", "risk_listrik", "risk_gas", "kepadatan_penduduk"]]
            st.dataframe(summary, hide_index=True, column_config={**dataframe_config(), "jumlah_kelurahan": "Jumlah kelurahan"}, alt="Ringkasan jumlah anggota, indeks centroid, interpretasi dan kepadatan rata-rata setiap klaster")
            st.subheader("Kepadatan penduduk dalam klaster", anchor=False)
            st.altair_chart(density_chart(model.villages), key=f"{prefix}_density", alt="Sebaran kepadatan penduduk untuk setiap klaster, dari minimum sampai maksimum")
            st.caption("Kepadatan hanya untuk profil konteks. Kategori deskriptif aplikasi: ≤10.000 jiwa/km²; padat >10.000–20.000; sangat padat >20.000. Kategori ini bukan klasifikasi resmi kerawanan.")
            st.markdown("#### Cara indeks kerawanan dihitung")
            st.latex(r"Risk_{Listrik}=\frac{1}{4}\sum_{j\in Listrik} Centroid_j\qquad Risk_{Gas}=\frac{1}{5}\sum_{j\in Gas} Centroid_j")
            if model.name == "AHC":
                st.table(model.profiles[["klaster", "interpretasi"]].rename(columns={"klaster": "Klaster", "interpretasi": "Profil kerawanan"}), hide_index=True, alt="Pemetaan profil kerawanan setiap klaster pada hasil AHC")
            else:
                st.table(pd.DataFrame({"Indeks listrik": ["> 0", "≤ 0", "> 0", "≤ 0"], "Indeks gas": ["≤ 0", "> 0", "> 0", "≤ 0"], "Interpretasi": [RISK_ORDER[1], RISK_ORDER[2], RISK_ORDER[0], RISK_ORDER[3]]}), hide_index=True, alt="Aturan interpretasi indeks listrik dan gas pada ambang 0")

    if views[2].open:
        with views[2]:
            show_model_evaluation(model, prefix)

    if views[3].open:
        with views[3]:
            show_data_analysis(model, prepared, prefix, models)


def show_data_analysis(model: ModelResult, prepared: PreparedData, prefix: str, models: dict[str, ModelResult] | None = None) -> None:
    from firewatch.eda import distribution_summary, numeric_indicators

    models = models or {model.name: model}
    st.subheader("Analisis indikator dan kelompok wilayah", anchor=False)
    st.caption(f"Seluruh {len(model.villages)} kelurahan pada dataset aktif · {model.name}, K={model.k}. Grafik persentase memakai rata-rata indikator asli antarperiode. Filter peta tidak membatasi analisis ini.")
    invalid = int(numeric_indicators(model.villages).isna().sum().sum())
    if invalid:
        st.info(f"{invalid} nilai kosong/tidak numerik diabaikan hanya pada grafik terkait, tanpa pengisian otomatis.")
    choice = st.segmented_control("Jenis analisis", ["Korelasi", "Distribusi", "Antar klaster", "Jumlah & pemisahan"], default="Korelasi", required=True, key=f"{prefix}_eda_view")

    def figure(kind: str, description: str, feature: str = FEATURES[0]):
        standardized = prepared.standardized if kind == "projection" else None
        with st.spinner("Menyiapkan grafik…"):
            contents = cached_figure(kind, model.villages, standardized, feature)
        st.image(contents, width="stretch", alt=description)
        st.download_button("Unduh grafik PNG", contents, file_name=f"{model.name.lower().replace(' ', '_')}_{kind}_{feature if kind == 'comparison' else 'indikator'}.png", mime="image/png", icon=":material/download:", on_click="ignore", key=f"{prefix}_eda_download_{kind}")

    if choice == "Korelasi":
        figure("correlation", "Heatmap korelasi Pearson sembilan indikator persentase dengan nilai pada setiap sel")
        st.caption("r mendekati +1: indikator cenderung meningkat bersama; −1: berlawanan; 0: hubungan linear lemah. Sel kosong menunjukkan indikator konstan atau kurang dari tiga pasangan valid. Korelasi tidak menyatakan sebab-akibat.")
    elif choice == "Distribusi":
        figure("distributions", "Histogram, kurva KDE jika data bervariasi, dan boxplot untuk kesembilan indikator persentase")
        st.caption("Batang menunjukkan jumlah kelurahan; kurva memperkirakan bentuk distribusi jika datanya bervariasi. Boxplot menampilkan median dan rentang kuartil. Titik di luar 1,5 × IQR adalah kandidat pencilan, bukan otomatis kesalahan data.")
        st.dataframe(distribution_summary(model.villages), hide_index=True, column_config={"indikator": "Indikator", "n_valid": "Data valid", "kosong_tidak_valid": "Kosong/tidak valid", "minimum": st.column_config.NumberColumn("Minimum (%)", format="%.2f"), "median": st.column_config.NumberColumn("Median (%)", format="%.2f"), "rata_rata": st.column_config.NumberColumn("Rata-rata (%)", format="%.2f"), "maksimum": st.column_config.NumberColumn("Maksimum (%)", format="%.2f"), "pencilan_iqr": "Kandidat pencilan (IQR)"}, alt="Statistik persebaran dan jumlah kandidat pencilan setiap indikator")
        st.subheader("Boxplot distribusi nilai indikator kerawanan", anchor=False)
        algorithm_names = list(models)
        selected = st.selectbox(
            "Algoritma untuk boxplot indikator",
            algorithm_names,
            index=algorithm_names.index(model.name) if model.name in algorithm_names else 0,
            key=f"{prefix}_indicator_box_algorithm",
            help=(
                "Hanya memilih label klaster final untuk visualisasi. Model, tab aktif, "
                "jumlah klaster, dan nilai evaluasi tidak berubah."
            ),
        )
        selected_model = models[selected]
        st.caption(
            f"Label klaster final **{selected_model.name}** (K={selected_model.k}) · "
            f"{len(selected_model.villages)} kelurahan. Warna berbeda menunjukkan klaster; "
            "sumbu X adalah indikator kerawanan dan sumbu Y adalah persentase rata-rata "
            "antarperiode. Nilai diambil dari data indikator aktual, bukan data simulasi."
        )
        with st.spinner("Menyiapkan boxplot indikator…"):
            contents = cached_figure("indicator_boxplots", selected_model.villages)
        st.image(
            contents,
            width="stretch",
            alt=(
                f"Boxplot distribusi sembilan indikator kerawanan menurut klaster final "
                f"{selected_model.name}"
            ),
        )
        st.download_button(
            "Unduh boxplot PNG",
            contents,
            file_name=f"boxplot_indikator_{selected_model.name.lower().replace(' ', '_').replace('-', '_')}.png",
            mime="image/png",
            icon=":material/download:",
            key=f"{prefix}_eda_download_indicator_boxplots_{selected_model.name}",
            on_click="ignore",
        )
        st.caption(
            "Kotak mencakup kuartil pertama sampai ketiga, garis tengah adalah median, "
            "whisker menunjukkan 1,5 × IQR, dan titik di luar whisker adalah kandidat "
            "pencilan. Klaster beranggota satu menghasilkan kotak degenerasi; nilainya "
            "tetap ditampilkan sesuai label final. Boxplot memakai seluruh anggota model "
            "terpilih dan tidak mengubah hasil klasterisasi."
        )
    elif choice == "Antar klaster":
        feature = st.selectbox("Indikator yang dibandingkan", FEATURES, format_func=FEATURE_LABELS.get, key=f"{prefix}_eda_feature")
        figure("comparison", f"Boxplot {FEATURE_LABELS[feature]} pada setiap klaster hasil model", feature)
        st.caption("Garis tengah adalah median; kotak mencakup 50% nilai tengah; titik di luar whisker merupakan kandidat pencilan menurut 1,5 × IQR. n menunjukkan seluruh anggota klaster; nilai kosong diabaikan pada boxplot.")
        with st.expander("Lihat profil rata-rata seluruh indikator", on_change="rerun", key=f"{prefix}_eda_means") as means:
            if means.open:
                figure("means", "Heatmap rata-rata persentase sembilan indikator pada setiap klaster")
                st.caption("Angka adalah rata-rata persentase asli anggota klaster. Profil centroid Z-score untuk interpretasi kerawanan tersedia pada tab Profil klaster.")
    else:
        figure("counts", "Diagram jumlah dan proporsi kelurahan pada setiap klaster")
        st.caption("Jumlah dihitung dari label model final. Perbedaan ukuran membantu mengenali klaster yang sangat kecil atau dominan.")
        try:
            figure("projection", "Scatter plot dua komponen utama data Z-score, diwarnai menurut label klaster model final")
        except ValueError as exc:
            st.info(str(exc))
        st.caption("PCA memproyeksikan sembilan indikator Z-score yang benar-benar masuk ke model menjadi dua dimensi. Persentase pada sumbu adalah variasi yang terwakili. Warna menunjukkan nomor klaster; proyeksi ini tidak mengubah label maupun skor evaluasi dan dapat menyembunyikan pemisahan pada dimensi lain.")
    st.caption("Grafik disimpan sementara menurut isi data dan pilihan analisis. Pergantian grafik memakai hasil model yang sudah tersimpan.")
