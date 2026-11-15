"""Evaluation data and candidate curves from existing model results.

Silhouette coefficients are computed from the same model input and final
labels as the official score. The combined silhouette visualization is
rendered by :mod:`firewatch.eda`; this module prepares its data without
refitting a model or changing metrics, trials, or memberships.
"""

from dataclasses import dataclass

import altair as alt
import numpy as np
import pandas as pd
from sklearn.metrics import silhouette_samples

from firewatch.analysis import FEATURES, KEYS, ModelResult, PreparedData


@dataclass(frozen=True)
class MetricDisplay:
    title: str
    axis_title: str
    interpretation: str


METRIC_DISPLAYS = {
    "silhouette": MetricDisplay(
        "Silhouette Score ↑",
        "Silhouette Score",
        "Semakin tinggi, semakin baik pemisahan dan kekompakan klaster secara umum. Rentang −1 sampai 1.",
    ),
    "dbi": MetricDisplay(
        "Davies–Bouldin Index (DBI) ↓",
        "Davies–Bouldin Index",
        "Semakin rendah, semakin baik kualitas pemisahan klaster berdasarkan DBI.",
    ),
    "chi": MetricDisplay(
        "Calinski–Harabasz Index (CHI) ↑",
        "Calinski–Harabasz Index",
        "Semakin tinggi, semakin baik perbandingan variasi antar- dan dalam klaster berdasarkan CHI.",
    ),
}


def _aligned_evaluation_data(
    prepared: PreparedData, model: ModelResult
) -> tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    """Join labels to model input by identity, never by displayed row order."""
    merged = prepared.standardized[KEYS + FEATURES].merge(
        model.villages[KEYS + ["klaster"]],
        on=KEYS, how="inner", validate="one_to_one", sort=False,
    )
    if len(merged) != len(prepared.standardized) or len(merged) != len(model.villages):
        raise ValueError("Anggota model tidak cocok dengan data masukan untuk visualisasi evaluasi.")
    if merged[FEATURES].isna().any().any():
        raise ValueError("Visualisasi evaluasi memerlukan seluruh indikator Z-score yang valid.")
    return (
        merged.reset_index(drop=True),
        merged[FEATURES].to_numpy(dtype=np.float64),
        merged["klaster"].to_numpy(),
    )


def silhouette_analysis(prepared: PreparedData, model: ModelResult) -> pd.DataFrame:
    """Actual per-village silhouette coefficients from the model's final labels.

    ``silhouette_samples`` is the definition behind ``silhouette_score``; the
    mean of these values is therefore the final score already shown in the table.
    Each cluster is sorted from the largest coefficient to the smallest.
    """
    merged, matrix, labels = _aligned_evaluation_data(prepared, model)
    if len(np.unique(labels)) < 2:
        raise ValueError("Silhouette memerlukan sedikitnya dua klaster.")
    samples = merged[KEYS + ["klaster"]].copy()
    samples["silhouette"] = silhouette_samples(matrix, labels)
    samples = samples.sort_values(
        ["klaster", "silhouette"], ascending=[True, False]
    ).reset_index(drop=True)
    return samples


def metric_curve(trials: pd.DataFrame, metric: str, k: int, title: str) -> alt.LayerChart:
    """Show every successful K trial; failed/missing K values are not connected."""
    data = trials.sort_values("k").copy()
    data["status"] = np.where(data.k == k, "K terpilih", "Kandidat")
    data["label"] = data[metric].map(lambda value: f"{value:.4f}")
    # Disjoint line segments avoid suggesting that a failed K was evaluated.
    data["segmen"] = data.k.diff().ne(1).cumsum()
    display = METRIC_DISPLAYS[metric]
    base = alt.Chart(data).encode(
        x=alt.X(
            "k:Q", title="Jumlah klaster (K)",
            axis=alt.Axis(values=data.k.tolist(), tickMinStep=1, labelAngle=0),
            scale=alt.Scale(zero=False, padding=20),
        ),
        y=alt.Y(
            f"{metric}:Q", title=display.axis_title,
            scale=alt.Scale(zero=False, padding=25),
        ),
        tooltip=[
            alt.Tooltip("k:O", title="K kandidat"),
            alt.Tooltip(f"{metric}:Q", title=display.axis_title, format=".4f"),
            alt.Tooltip("status:N", title="Status"),
        ],
    )
    line = base.mark_line(color="#CBD3DC", strokeWidth=2).encode(detail="segmen:N")
    dots = base.mark_circle(size=75).encode(
        color=alt.Color(
            "status:N",
            scale=alt.Scale(domain=["K terpilih", "Kandidat"], range=["#C74535", "#9BA8B6"]),
            legend=None,
        ),
    )
    labels = base.mark_text(dy=-13, fontSize=10, color="#253342").encode(text="label:N")
    return (line + dots + labels).properties(title=title, height=240)


def model_metric_curve(model: ModelResult, metric: str) -> alt.LayerChart:
    """Name the algorithm on each exported/standalone candidate chart."""
    display = METRIC_DISPLAYS[metric]
    curve = metric_curve(model.trials, metric, model.k, f"{model.name} · {display.title}")
    final = pd.DataFrame([{
        "k": model.k, metric: model.metrics[metric],
        "algoritma": model.name, "status": "Model final",
    }])
    marker = alt.Chart(final).mark_point(
        shape="diamond", filled=True, size=130, color="#348B79",
    ).encode(
        x="k:Q", y=f"{metric}:Q",
        tooltip=[
            alt.Tooltip("algoritma:N", title="Algoritma"),
            alt.Tooltip("k:O", title="K final"),
            alt.Tooltip(f"{metric}:Q", title=display.axis_title, format=".4f"),
            alt.Tooltip("status:N", title="Sumber"),
        ],
    )
    # Altair hoists shared candidate data to the parent LayerChart. Preserve it
    # explicitly when adding a layer with a different (final-model) dataset.
    return alt.layer(*curve.layer, marker, data=curve.data).properties(
        title=f"{model.name} · {display.title}", height=240,
    )