"""Regression coverage for analysis charts, maps, and region search."""

from pathlib import Path
import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

from firewatch.analysis import FEATURES, FEATURE_LABELS, KEYS, RISK_ORDER, build_profiles, fit_labels, prepare_data, read_dataset, run_method
from firewatch.charts import cluster_distribution, cluster_donut, risk_distribution, risk_donut, village_map
from firewatch.eda import _indicator_boxplots, cluster_means, cluster_projection, distribution_summary, numeric_indicators, render_figure
from firewatch.geography import boundary_data
from firewatch.regions import filter_region, region_options

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def prepared():
    return prepare_data(read_dataset((ROOT / "2425.csv").read_bytes()))


@pytest.fixture(scope="module")
def villages(prepared):
    return build_profiles(prepared, fit_labels("K-Means", 3, prepared.X))[0]


def test_suggestions_are_real_unambiguous_and_follow_active_dataset(prepared):
    raw = prepared.raw
    options = region_options(raw)
    assert len(options) == 267 + 44
    for identity in options.values():
        matches = raw
        for field, value in identity.items():
            matches = matches[matches[field].eq(value)]
        assert not matches.empty
    small = raw.head(4)
    assert {tuple(v.values()) for v in region_options(small).values()}.issubset({tuple(v.values()) for v in options.values()})
    village_option = next(label for label in options if label.startswith("Kelurahan Ancol ·"))
    assert filter_region(raw, village_option, options).kelurahan.eq("ANCOL").all()
    district_option = next(label for label in options if label.startswith("Kecamatan Kemayoran ·"))
    expected = raw[raw.kecamatan.eq("KEMAYORAN")]
    pd.testing.assert_frame_equal(filter_region(raw, district_option, options), expected)


def test_partial_case_insensitive_literal_search_and_no_match(prepared):
    raw = prepared.raw
    options = region_options(raw)
    result = filter_region(raw, "  aNgKe ", options)
    assert len(result) >= 2
    assert result.kelurahan.str.contains("ANGKE").all()
    assert filter_region(raw, "zzzz_tidak_ada", options).empty
    assert filter_region(raw, ".*", options).empty  # Literal text, never regex.
    pd.testing.assert_frame_equal(filter_region(raw, None, options), raw)


def test_numeric_plot_data_excludes_invalid_values_without_changing_source(villages):
    source = villages.copy()
    source[FEATURES[0]] = source[FEATURES[0]].astype(object)
    source.loc[0, FEATURES[0]] = "bukan angka"
    source.loc[1, FEATURES[0]] = np.inf
    source.loc[2, FEATURES[0]] = None
    snapshot = source.copy(deep=True)
    numeric = numeric_indicators(source)
    assert numeric[FEATURES[0]].isna().sum() == 3
    summary = distribution_summary(source).iloc[0]
    assert summary.kosong_tidak_valid == 3
    assert summary.n_valid == len(villages) - 3
    pd.testing.assert_frame_equal(source, snapshot)


def test_cluster_means_and_pca_use_correct_labels_when_rows_are_reordered(prepared, villages):
    means = cluster_means(villages)
    pd.testing.assert_frame_equal(means, villages.groupby("klaster")[FEATURES].mean())
    shuffled = villages.sample(frac=1, random_state=23).reset_index(drop=True)
    points, variance = cluster_projection(prepared.standardized, shuffled)
    aligned = points.merge(villages[KEYS + ["klaster"]], on=KEYS, suffixes=("_pca", "_model"), validate="one_to_one")
    assert aligned.klaster_pca.eq(aligned.klaster_model).all()
    assert len(points) == len(villages)
    assert points[["pc1", "pc2"]].notna().all().all()
    assert 0 < variance.sum() <= 1
    constant = prepared.standardized.copy()
    constant[FEATURES] = 0
    with pytest.raises(ValueError, match="bervariasi"):
        cluster_projection(constant, villages)


def test_real_boundaries_and_risk_layer_order(villages):
    for level, count in [("provinsi", 1), ("kota", 6), ("kecamatan", 44), ("kelurahan", 267)]:
        geo = boundary_data(level)
        assert geo["type"] == "FeatureCollection"
        assert len(geo["features"]) == count
        assert all(f["geometry"]["type"] in {"Polygon", "MultiPolygon"} for f in geo["features"])
    labels = boundary_data("labels")
    assert len(labels) == 6
    assert all(106 < p["position"][0] < 108 and -7 < p["position"][1] < -5 for p in labels)
    spec = json.loads(village_map(villages, detailed=True, terrain=True).to_json())
    ids = [layer["id"] for layer in spec["layers"]]
    assert ids[-1] == "kelurahan"
    assert {"batas-kota", "batas-kecamatan", "batas-kelurahan", "batas-provinsi", "nama-wilayah"}.issubset(ids)
    assert len(spec["layers"][-1]["data"]) == 267
    assert spec["layers"][-1]["pickable"]
    assert "voyager" in spec["mapStyle"]


def test_small_profile_is_true_proportion_with_all_categories(villages):
    original = villages.copy(deep=True)
    summary = risk_distribution(villages)
    assert summary.interpretasi.tolist() == RISK_ORDER
    np.testing.assert_array_equal(summary.jumlah, [79, 0, 1, 187])
    gas = summary.set_index("interpretasi").loc["Dominan Bahaya Gas"]
    assert gas.persentase == 1 / 267
    assert summary.jumlah.sum() == 267
    assert summary.persentase.sum() == pytest.approx(1)
    chart = risk_donut(villages)
    pd.testing.assert_frame_equal(chart.layer[0].data, summary)
    arc = chart.to_dict()["layer"][0]
    assert arc["encoding"]["theta"]["field"] == "jumlah"
    assert arc["mark"]["padAngle"] == arc["mark"]["cornerRadius"] == 0
    only_gas = risk_distribution(villages[villages.interpretasi.eq("Dominan Bahaya Gas")])
    np.testing.assert_array_equal(only_gas.jumlah, [0, 0, 1, 0])
    np.testing.assert_array_equal(only_gas.persentase, [0, 0, 1, 0])
    pd.testing.assert_frame_equal(villages, original)


def test_island_data_remains_available_and_map_fits_filtered_islands(villages):
    islands = villages[villages.kota.eq("KAB ADM KEP SERIBU")]
    assert len(islands) == 6
    default = json.loads(village_map(villages).to_json())
    assert sum(row["kota"] == "KAB ADM KEP SERIBU" for row in default["layers"][-1]["data"]) == 6
    filtered = json.loads(village_map(islands).to_json())
    assert len(filtered["layers"][-1]["data"]) == 6
    view = filtered["initialViewState"]
    assert view["latitude"] == pytest.approx((islands.latitude.min() + islands.latitude.max()) / 2)
    assert view["longitude"] == pytest.approx((islands.longitude.min() + islands.longitude.max()) / 2)
    assert view["zoom"] < default["initialViewState"]["zoom"]


def test_ahc_cluster_counts_and_colors_remain_distinct_when_risk_profiles_match(prepared):
    model = run_method("AHC", prepared)
    assert model.k == 3
    summary = cluster_distribution(model.villages)
    assert summary.klaster.tolist() == [1, 2, 3]
    assert summary.jumlah.tolist() == [1, 128, 138]
    assert summary.interpretasi.tolist() == ["Dominan Bahaya Gas", "Risiko Rendah", "Risiko Rendah"]
    np.testing.assert_allclose(summary.persentase, np.array([1, 128, 138]) / 267)
    chart = cluster_donut(summary)
    pd.testing.assert_frame_equal(chart.layer[0].data, summary)
    scale = chart.to_dict()["layer"][0]["encoding"]["color"]["scale"]
    assert len(set(scale["range"])) == model.k
    map_spec = json.loads(village_map(model.villages, color_by="klaster").to_json())
    colors = {row["klaster"]: row["color"] for row in map_spec["layers"][-1]["data"]}
    assert len({tuple(c) for c in colors.values()}) == 3
    for k, color in zip(summary.klaster, scale["range"]):
        assert colors[k][:3] == [int(color[i:i + 2], 16) for i in (1, 3, 5)]
    only_last = model.villages[model.villages.klaster.eq(3)]
    single_spec = json.loads(village_map(only_last, color_by="klaster").to_json())
    assert all(row["color"] == colors[3] for row in single_spec["layers"][-1]["data"])
    assert cluster_distribution(only_last).jumlah.tolist() == [138]


def test_integrated_ahc_chart_keeps_every_final_cluster_and_its_profile(prepared):
    model = run_method("AHC", prepared)
    original = model.villages.copy(deep=True)
    summary = risk_distribution(model.villages)
    assert summary.interpretasi.tolist() == RISK_ORDER
    assert summary.interpretasi.is_unique
    assert summary.jumlah.tolist() == [0, 0, 1, 266]
    np.testing.assert_allclose(summary.persentase, np.array([0, 0, 1, 266]) / 267)
    cluster_summary = cluster_distribution(model.villages)
    chart = cluster_donut(cluster_summary)
    counts = chart.layer[0].data
    assert counts.klaster.tolist() == [1, 2, 3]
    assert counts.jumlah.tolist() == [1, 128, 138]
    np.testing.assert_allclose(counts.persentase, np.array([1, 128, 138]) / 267)
    pd.testing.assert_frame_equal(counts, cluster_summary)
    expected_profiles = model.profiles.set_index("klaster")
    for row in counts.itertuples(index=False):
        assert row.jumlah == expected_profiles.loc[row.klaster, "jumlah_kelurahan"]
        assert row.interpretasi == expected_profiles.loc[row.klaster, "interpretasi"]
    arc = chart.to_dict()["layer"][0]
    assert arc["encoding"]["detail"] == {"field": "klaster", "type": "ordinal"}
    assert arc["encoding"]["color"]["scale"]["domain"] == ["Klaster 1", "Klaster 2", "Klaster 3"]
    assert len(set(arc["encoding"]["color"]["scale"]["range"])) == model.k == 3
    assert arc["mark"]["padAngle"] == arc["mark"]["cornerRadius"] == 0
    only_low = model.villages[model.villages.interpretasi.eq("Risiko Rendah")]
    filtered_summary = risk_distribution(only_low)
    assert filtered_summary.jumlah.tolist() == [0, 0, 0, 266]
    assert filtered_summary.persentase.tolist() == [0, 0, 0, 1]
    filtered_chart = cluster_donut(cluster_distribution(only_low))
    assert filtered_chart.layer[0].data.klaster.tolist() == [2, 3]
    np.testing.assert_allclose(filtered_chart.layer[0].data.persentase, np.array([128, 138]) / 266)
    pd.testing.assert_frame_equal(model.villages, original)


@pytest.mark.parametrize("kind", ["correlation", "distributions", "comparison", "means", "counts", "projection", "indicator_boxplots"])
def test_figures_render_actual_model_data_and_close_figures(prepared, villages, kind):
    contents = render_figure(kind, villages, prepared.standardized)
    assert contents.startswith(b"\x89PNG\r\n\x1a\n")
    assert len(contents) > 10000
    assert not plt.get_fignums()


def test_indicator_boxplot_uses_final_clusters_and_actual_indicator_values(villages):
    snapshot = villages.copy(deep=True)
    fig = _indicator_boxplots(villages)
    try:
        ax = fig.axes[0]
        assert ax.get_title() == "Boxplot distribusi nilai indikator kerawanan"
        assert ax.get_xlabel() == "Indikator kerawanan"
        assert ax.get_ylabel() == "Persentase rata-rata antarperiode (%)"
        assert [tick.get_text() for tick in ax.get_xticklabels()] == [
            FEATURE_LABELS[feature] for feature in FEATURES
        ]
        legend = ax.get_legend()
        assert legend is not None
        assert legend.get_title().get_text() == "Klaster"
        expected = [
            f"Klaster {cluster} (n={count})"
            for cluster, count in villages.groupby("klaster").size().sort_index().items()
        ]
        assert [text.get_text() for text in legend.get_texts()] == expected
        assert len({
            tuple(patch.get_facecolor()) for patch in legend.legend_handles
        }) == villages.klaster.nunique()
    finally:
        plt.close(fig)
    pd.testing.assert_frame_equal(villages, snapshot)


def test_constant_indicator_correlation_can_render(villages):
    constant = villages.copy()
    constant[FEATURES] = 1
    assert render_figure("correlation", constant).startswith(b"\x89PNG")
