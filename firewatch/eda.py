"""Scientific figures from the active village data and existing cluster labels."""

from io import BytesIO
from threading import RLock

import matplotlib

matplotlib.use("Agg")
import matplotlib.cm as cm
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.colors import ListedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from sklearn.decomposition import PCA

from firewatch.analysis import FEATURES, FEATURE_LABELS, KEYS
from firewatch.palette import CLUSTER_COLORS as PALETTE

_PLOT_LOCK = RLock()
_STYLE = {"font.family": "DejaVu Sans", "font.size": 10, "axes.titlesize": 13, "axes.labelcolor": "#394958", "text.color": "#253342", "axes.spines.top": False, "axes.spines.right": False, "figure.facecolor": "white", "axes.facecolor": "white", "savefig.facecolor": "white"}


def numeric_indicators(data: pd.DataFrame) -> pd.DataFrame:
    """Coerce plot data only; never impute or change the clustering input."""
    return data.reindex(columns=FEATURES).apply(pd.to_numeric, errors="coerce").replace([np.inf, -np.inf], np.nan)


def distribution_summary(data: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for feature, values in numeric_indicators(data).items():
        valid = values.dropna()
        q1, q3 = valid.quantile([.25, .75])
        iqr = q3 - q1
        rows.append({"indikator": FEATURE_LABELS[feature], "n_valid": len(valid), "kosong_tidak_valid": int(values.isna().sum()), "minimum": valid.min(), "median": valid.median(), "rata_rata": valid.mean(), "maksimum": valid.max(), "pencilan_iqr": int(((valid < q1 - 1.5 * iqr) | (valid > q3 + 1.5 * iqr)).sum())})
    return pd.DataFrame(rows)


def cluster_means(data: pd.DataFrame) -> pd.DataFrame:
    numeric = numeric_indicators(data)
    numeric["klaster"] = data.klaster
    return numeric.groupby("klaster", sort=True)[FEATURES].mean()


def cluster_projection(standardized: pd.DataFrame, villages: pd.DataFrame) -> tuple[pd.DataFrame, np.ndarray]:
    # Keyed alignment keeps labels correct even when a displayed dataframe is sorted.
    aligned = standardized[KEYS + FEATURES].merge(villages[KEYS + ["klaster"]], on=KEYS, how="inner", validate="one_to_one")
    numeric = numeric_indicators(aligned)
    valid = numeric.notna().all(axis=1)
    matrix = numeric.loc[valid].to_numpy(dtype=float)
    if len(matrix) < 2 or np.all(np.var(matrix, axis=0) == 0):
        raise ValueError("Proyeksi memerlukan sedikitnya dua kelurahan valid dengan indikator yang bervariasi.")
    pca = PCA(n_components=2, svd_solver="full")
    coordinates = pca.fit_transform(matrix)
    result = aligned.loc[valid, KEYS + ["klaster"]].reset_index(drop=True)
    result[["pc1", "pc2"]] = coordinates
    return result, pca.explained_variance_ratio_


def _cluster_labels(data):
    counts = data.groupby("klaster").size().sort_index()
    labels = {cluster: f"Klaster {cluster} (n={count})" for cluster, count in counts.items()}
    colors = {labels[cluster]: PALETTE[i % len(PALETTE)] for i, cluster in enumerate(counts.index)}
    return labels, colors


def _cluster_rgba(clusters):
    """Map final cluster numbers to RGBA colors with matplotlib.cm.

    A ListedColormap keeps the exact cluster colors used by the maps and the
    other charts, while ScalarMappable supplies matplotlib's RGBA conversion.
    """
    mapper = cm.ScalarMappable(cmap=ListedColormap(PALETTE))
    mapper.set_clim(0, max(len(PALETTE) - 1, 1))
    return {
        int(cluster): mapper.to_rgba((int(cluster) - 1) % len(PALETTE))
        for cluster in clusters
    }


def _correlation(data):
    correlation = numeric_indicators(data).corr(method="pearson", min_periods=3)
    correlation.index = correlation.columns = [FEATURE_LABELS[f] for f in FEATURES]
    fig, ax = plt.subplots(figsize=(10.5, 8.5), layout="constrained")
    if correlation.notna().any().any():
        sns.heatmap(correlation, mask=correlation.isna(), annot=True, fmt=".2f", cmap="vlag", vmin=-1, vmax=1, center=0, square=True, linewidths=.6, cbar_kws={"label": "Korelasi Pearson (r)", "shrink": .8}, ax=ax)
    else:
        ax.text(.5, .5, "Korelasi tidak terdefinisi: indikator konstan atau data valid terlalu sedikit.", ha="center", va="center", wrap=True, transform=ax.transAxes)
        ax.set_axis_off()
    ax.set_title("Korelasi antarindikator kerawanan", pad=18)
    ax.set_xlabel("Indikator (%) rata-rata antarperiode")
    ax.set_ylabel("Indikator (%) rata-rata antarperiode")
    ax.tick_params(axis="x", rotation=40)
    for label in ax.get_xticklabels():
        label.set_ha("right")
    return fig


def _distributions(data):
    numeric = numeric_indicators(data)
    fig = plt.figure(figsize=(12, 11), layout="constrained")
    grid = fig.add_gridspec(6, 3, height_ratios=[3, 1] * 3, hspace=.12, wspace=.08)
    for index, feature in enumerate(FEATURES):
        row, column = divmod(index, 3)
        histogram = fig.add_subplot(grid[2 * row, column])
        box = fig.add_subplot(grid[2 * row + 1, column], sharex=histogram)
        values = numeric[feature].dropna()
        if len(values):
            sns.histplot(x=values, bins="auto", kde=len(values) >= 3 and values.nunique() > 2, color="#497B9D", alpha=.7, ax=histogram)
            sns.boxplot(x=values, color="#C8DCD9", whis=1.5, width=.55, fliersize=2.5, ax=box)
        histogram.set_title(FEATURE_LABELS[feature], loc="left", fontsize=11)
        histogram.set_ylabel("Kelurahan", fontsize=9)
        histogram.set_xlabel("")
        histogram.tick_params(axis="x", labelbottom=False)
        box.set_xlabel("Persentase (%)", fontsize=9)
        box.set_yticks([])
        histogram.grid(axis="y", alpha=.15)
    fig.suptitle("Distribusi sembilan indikator kelurahan", fontsize=17)
    return fig


def _comparison(data, feature):
    if feature not in FEATURES:
        raise ValueError("Indikator tidak tersedia.")
    labels, colors = _cluster_labels(data)
    plot = pd.DataFrame({"nilai": numeric_indicators(data)[feature], "kelompok": data.klaster.map(labels)})
    fig, ax = plt.subplots(figsize=(9, max(4, .55 * len(labels) + 1.5)), layout="constrained")
    sns.boxplot(data=plot, x="nilai", y="kelompok", hue="kelompok", order=list(labels.values()), palette=colors, legend=False, dodge=False, whis=1.5, fliersize=4, ax=ax)
    ax.set_title(f"{FEATURE_LABELS[feature]} per klaster", pad=15)
    ax.set_xlabel("Persentase rata-rata antarperiode (%)")
    ax.set_ylabel("Klaster dan jumlah kelurahan")
    ax.grid(axis="x", alpha=.2)
    return fig


def _indicator_boxplots(data):
    """Compare actual indicator percentages across final clusters.

    The chart reads the model's final memberships and actual village
    percentages. It groups boxes by indicator on the x-axis and colors them by
    cluster; no values are imputed and the clustering result is untouched.
    """
    labels, colors = _cluster_labels(data)
    numeric = numeric_indicators(data)
    plot = numeric[FEATURES].copy()
    plot["klaster"] = data["klaster"].map(labels).to_numpy()
    long = plot.melt(
        id_vars="klaster", var_name="indikator", value_name="nilai",
    ).dropna(subset=["nilai"])
    if long.empty:
        raise ValueError("Tidak ada nilai indikator valid untuk boxplot.")
    category_order = [FEATURE_LABELS[feature] for feature in FEATURES]
    long["indikator"] = pd.Categorical(
        long["indikator"].map(FEATURE_LABELS),
        categories=category_order, ordered=True,
    )
    clusters = list(labels.values())
    width = max(12.5, 7.2 + .9 * len(clusters) + .3 * len(FEATURES))
    fig, ax = plt.subplots(figsize=(width, 6.4), layout="constrained")
    sns.boxplot(
        data=long, x="indikator", y="nilai", hue="klaster",
        order=category_order, hue_order=clusters, palette=colors,
        dodge=True, width=.76, linewidth=.8, fliersize=3.5, whis=1.5, ax=ax,
    )
    ax.set_title("Boxplot distribusi nilai indikator kerawanan", pad=16)
    ax.set_xlabel("Indikator kerawanan")
    ax.set_ylabel("Persentase rata-rata antarperiode (%)")
    ax.grid(axis="y", alpha=.18)
    ax.set_axisbelow(True)
    ax.tick_params(axis="x", rotation=32)
    for label in ax.get_xticklabels():
        label.set_ha("right")
    ax.legend(
        title="Klaster", loc="upper left", bbox_to_anchor=(1.01, 1.0),
        frameon=False, fontsize=8, title_fontsize=9,
    )
    return fig


def _silhouette_plot(samples, mean, algorithm, k):
    """One combined silhouette plot with every final cluster on the y-axis."""
    clusters = sorted(int(cluster) for cluster in samples.klaster.unique())
    if len(clusters) < 2:
        raise ValueError("Silhouette Plot memerlukan sedikitnya dua klaster.")
    values = samples.silhouette.to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("Silhouette Plot memerlukan koefisien yang valid.")
    computed_mean = float(values.mean())
    if not np.isclose(computed_mean, mean, rtol=0, atol=1e-12):
        raise ValueError(
            "Rata-rata Silhouette Plot tidak sama dengan Silhouette Score final."
        )

    colors = _cluster_rgba(clusters)
    fig, ax = plt.subplots(figsize=(9.4, 5.8), layout="constrained")
    lower = 0
    gap = max(2, int(round(len(samples) * .012)))
    positions, tick_labels, handles = [], [], []
    for cluster in clusters:
        cluster_values = samples.loc[
            samples.klaster.eq(cluster), "silhouette"
        ].to_numpy(dtype=float)
        size = len(cluster_values)
        upper = lower + size
        color = colors[cluster]
        ax.fill_betweenx(
            np.arange(lower, upper), 0, cluster_values,
            facecolor=color, edgecolor=color, linewidth=.25, alpha=.9,
        )
        positions.append(lower + (size - 1) / 2)
        tick_labels.append(f"Klaster {cluster}\n(n={size})")
        handles.append(Patch(
            facecolor=color, edgecolor=color,
            label=f"Klaster {cluster} · n={size}",
        ))
        lower = upper + gap

    ax.set_yticks(positions)
    ax.set_yticklabels(tick_labels)
    # Leave a small bottom margin so a singleton first cluster's tick label
    # cannot collide with the x-axis tick labels.
    bottom_pad = max(gap, int(round(len(samples) * .03)))
    ax.set_ylim(-bottom_pad, lower - gap)
    ax.set_xlim(-1, 1)
    ax.set_xlabel("Silhouette Coefficient (s_i)")
    ax.set_ylabel("Klaster final")
    ax.axvline(0, color="#CBD3DC", linewidth=1)
    ax.axvline(mean, color="#253342", linestyle="--", linewidth=1.4)
    ax.grid(axis="x", alpha=.18)
    ax.set_axisbelow(True)
    handles.append(Line2D(
        [0], [0], color="#253342", linestyle="--", linewidth=1.5,
        label=f"Rata-rata · {mean:.4f}",
    ))
    ax.legend(
        handles=handles, title="Klaster", loc="upper left",
        bbox_to_anchor=(1.01, 1.0), frameon=False, fontsize=8,
        title_fontsize=9,
    )
    ax.set_title(
        f"{algorithm} · Silhouette Plot · rata-rata = {mean:.4f} · K={k}",
        pad=14,
    )
    return fig


def _means(data):
    means = cluster_means(data)
    means.index = [f"Klaster {int(k)}" for k in means.index]
    means.columns = [FEATURE_LABELS[f] for f in FEATURES]
    fig, ax = plt.subplots(figsize=(11, max(4.5, .6 * len(means) + 2)), layout="constrained")
    sns.heatmap(means, annot=True, fmt=".1f", cmap="YlOrRd", vmin=0, linewidths=.6, cbar_kws={"label": "Rata-rata indikator (%)"}, ax=ax)
    ax.set_title("Profil rata-rata persentase setiap klaster", pad=16)
    ax.set_xlabel("Indikator")
    ax.set_ylabel("Klaster")
    ax.tick_params(axis="x", rotation=40)
    for label in ax.get_xticklabels():
        label.set_ha("right")
    return fig


def _counts(data):
    counts = data.groupby("klaster").size().sort_index()
    fig, ax = plt.subplots(figsize=(9, 4.5), layout="constrained")
    bars = ax.bar([f"Klaster {k}" for k in counts.index], counts.values, color=PALETTE[:len(counts)], width=.6)
    ax.bar_label(bars, labels=[f"{n}\n({n / len(data):.1%})" for n in counts], padding=5)
    ax.set_ylim(0, max(counts) * 1.25)
    ax.yaxis.get_major_locator().set_params(integer=True)
    ax.set_title("Jumlah kelurahan setiap klaster", pad=16)
    ax.set_xlabel("Klaster")
    ax.set_ylabel("Jumlah kelurahan")
    ax.grid(axis="y", alpha=.15)
    return fig


def _projection(data, standardized):
    projection, variance = cluster_projection(standardized, data)
    labels, colors = _cluster_labels(data)
    projection["kelompok"] = projection.klaster.map(labels)
    fig, ax = plt.subplots(figsize=(9, 6), layout="constrained")
    sns.scatterplot(data=projection, x="pc1", y="pc2", hue="kelompok", hue_order=list(labels.values()), palette=colors, s=48, alpha=.8, edgecolor="white", linewidth=.4, ax=ax)
    ax.set_title("Proyeksi PCA dari sembilan indikator Z-score", pad=16)
    ax.set_xlabel(f"Komponen utama 1 ({variance[0]:.1%} variasi)")
    ax.set_ylabel(f"Komponen utama 2 ({variance[1]:.1%} variasi)")
    ax.legend(title="Klaster hasil model", loc="best", fontsize=9)
    ax.grid(alpha=.15)
    return fig


def render_silhouette_plot(samples: pd.DataFrame, mean: float, algorithm: str, k: int) -> bytes:
    """Return one PNG containing the combined Silhouette Plot for one algorithm."""
    if samples.empty:
        raise ValueError("Tidak ada koefisien Silhouette untuk divisualisasikan.")
    with _PLOT_LOCK, plt.rc_context(_STYLE):
        fig = _silhouette_plot(samples, mean, algorithm, k)
        try:
            output = BytesIO()
            fig.savefig(output, format="png", dpi=170, bbox_inches="tight")
            return output.getvalue()
        finally:
            plt.close(fig)


def render_figure(kind: str, villages: pd.DataFrame, standardized: pd.DataFrame | None = None, feature: str = FEATURES[0]) -> bytes:
    """Return PNG bytes, closing figures and serializing Matplotlib's global state."""
    if villages.empty:
        raise ValueError("Tidak ada kelurahan untuk divisualisasikan.")
    renderers = {
        "correlation": lambda: _correlation(villages),
        "distributions": lambda: _distributions(villages),
        "comparison": lambda: _comparison(villages, feature),
        "means": lambda: _means(villages),
        "counts": lambda: _counts(villages),
        "projection": lambda: _projection(villages, standardized),
        "indicator_boxplots": lambda: _indicator_boxplots(villages),
    }
    if kind not in renderers:
        raise ValueError("Jenis grafik tidak tersedia.")
    if kind == "projection" and standardized is None:
        raise ValueError("Data Z-score diperlukan untuk proyeksi.")
    with _PLOT_LOCK, plt.rc_context(_STYLE):
        fig = renderers[kind]()
        try:
            output = BytesIO()
            fig.savefig(output, format="png", dpi=160, bbox_inches="tight")
            return output.getvalue()
        finally:
            plt.close(fig)
