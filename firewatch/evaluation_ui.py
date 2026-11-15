"""Streamlit evaluation panels, separate from modeling and other result views."""

import streamlit as st

from firewatch.analysis import ModelResult, PreparedData
from firewatch.evaluation_charts import (
    METRIC_DISPLAYS,
    model_metric_curve,
    silhouette_analysis,
)


def _metric(value: float) -> str:
    return f"{value:.4f}".replace(".", ",")


def show_silhouette_panel(
    prepared: PreparedData,
    models: dict[str, ModelResult],
    initial: str,
    prefix: str,
    open_key: str,
) -> None:
    """Show one combined silhouette plot for the selected final algorithm.

    The selector only chooses which final model's labels are rendered. Each
    chart contains all clusters of that algorithm and never mixes villages or
    labels from another algorithm.
    """
    names = list(models)
    if not names:
        return
    from firewatch.eda import render_silhouette_plot

    with st.container(border=True):
        header = st.columns([4, 1], vertical_alignment="center")
        header[0].markdown("**Silhouette Plot per algoritma**")
        if header[1].button(
            "Tutup",
            key=f"{prefix}_silhouette_close",
            icon=":material/close:",
            type="tertiary",
            width="stretch",
        ):
            st.session_state[open_key] = False
            return
        selected = st.selectbox(
            "Algoritma",
            names,
            index=names.index(initial) if initial in names else 0,
            key=f"{prefix}_silhouette_algorithm",
            help=(
                "Setiap pilihan memakai label klaster final algoritma tersebut. "
                "Anggota dari algoritma lain tidak digabung dalam grafik."
            ),
        )
        model = models[selected]
        with st.spinner("Menyiapkan Silhouette Plot…"):
            samples = silhouette_analysis(prepared, model)
            contents = render_silhouette_plot(
                samples,
                float(model.metrics["silhouette"]),
                model.name,
                model.k,
            )
        st.image(
            contents,
            width="stretch",
            alt=(
                f"{model.name}: Silhouette Plot seluruh klaster final; garis putus-putus "
                f"rata-rata {model.metrics['silhouette']:.4f}"
            ),
        )
        st.caption(
            f"**{model.name} · K={model.k}** · Silhouette Score = "
            f"**{_metric(model.metrics['silhouette'])}**. Setiap batang adalah satu "
            "kelurahan pada hasil klasterisasi final, diurutkan menurun di dalam "
            "klasternya. Warna dan label sumbu Y mengikuti nomor klaster aktual. "
            "Garis putus-putus menunjukkan rata-rata seluruh koefisien dan memakai "
            "nilai yang sama dengan kartu Silhouette Score. Nilai positif berarti "
            "kelurahan lebih dekat ke klasternya sendiri; nilai negatif berarti "
            "cenderung lebih dekat ke klaster lain. Grafik memakai seluruh anggota "
            "model, bukan hasil filter peta."
        )
        st.download_button(
            "Unduh Silhouette Plot PNG",
            contents,
            file_name=f"silhouette_{model.name.lower().replace(' ', '_')}.png",
            mime="image/png",
            icon=":material/download:",
            key=f"{prefix}_silhouette_download",
            on_click="ignore",
        )


def show_model_evaluation(model: ModelResult, prefix: str) -> None:
    """Distinguish the search scores from the separately evaluated final model."""
    st.subheader("Jejak pencarian jumlah klaster", anchor=False)
    st.markdown(model.selection)
    with st.container(horizontal=True):
        for metric, label in [("silhouette", "Silhouette"), ("dbi", "DBI"), ("chi", "CHI")]:
            st.badge(f"Pilihan {label}: K={model.winners[metric]}", color="gray")

    st.caption(
        "Garis dan lingkaran memakai hasil evaluasi kandidat K; lingkaran merah menandai K terpilih. "
        "Wajik hijau memakai skor model final yang dihitung ulang pada K terpilih, "
        "sama dengan kartu ringkasan dan tabel perbandingan. Nilai kandidat dan final dapat berbeda. "
        "Filter peta tidak mengubah metrik."
    )
    # Full-width charts keep nine value labels and long algorithm names readable.
    for metric, display in METRIC_DISPLAYS.items():
        with st.container(border=True):
            st.altair_chart(
                model_metric_curve(model, metric),
                key=f"{prefix}_{metric}_curve",
                alt=f"{model.name}: {display.title} setiap kandidat K dan nilai model final",
            )
            st.caption(
                f"{model.name} · K final={model.k} · "
                f"{display.axis_title} final: {model.metrics[metric]:.4f}. "
                f"{display.interpretation}"
            )

    trials = model.trials.copy()
    trials["status"] = trials.k.map(lambda k: "Terpilih" if k == model.k else "Kandidat")
    st.dataframe(
        trials, hide_index=True,
        column_config={
            "k": "Jumlah klaster",
            "silhouette": st.column_config.NumberColumn("Silhouette ↑", format="%.4f"),
            "dbi": st.column_config.NumberColumn("DBI ↓", format="%.4f"),
            "chi": st.column_config.NumberColumn("CHI ↑", format="%.4f"),
            "waktu_detik": st.column_config.NumberColumn("Waktu (detik)", format="%.4f"),
            "status": "Status",
        },
        alt="Hasil evaluasi seluruh kandidat K; skor model final ditampilkan pada kartu ringkasan",
    )
    st.caption(
        f"Durasi seluruh pencarian dan model final: {model.seconds:.3f} detik. "
        "Durasi dapat berbeda antarperangkat; hasil memakai parameter dan versi pustaka yang tetap."
    )
    if model.errors:
        st.warning(
            "Sebagian kandidat tidak dapat dievaluasi: " + " | ".join(model.errors),
            icon=":material/warning:",
        )