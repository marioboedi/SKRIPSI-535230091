"""Check actual model scores all the way to the serialized Streamlit charts."""

import json
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest
from streamlit.dataframe_util import convert_arrow_bytes_to_pandas_df
from streamlit.testing.v1 import AppTest

from firewatch.analysis import METHODS, evaluate, read_dataset, run_analysis
from firewatch.eda import _silhouette_plot, render_silhouette_plot
from firewatch.evaluation_charts import (
    METRIC_DISPLAYS,
    model_metric_curve,
    silhouette_analysis,
)
from firewatch.state import cached_analysis
from firewatch.ui import number

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def analysis():
    return cached_analysis((ROOT / "2425.csv").read_bytes())


def chart_data(element, layer=0):
    """Read a named layered payload sent to the browser."""
    spec = json.loads(element.proto.spec)
    name = spec["layer"][layer].get("data", spec.get("data", {}))["name"]
    dataset = next(data for data in element.proto.datasets if data.name == name)
    return convert_arrow_bytes_to_pandas_df(dataset.data.data)


def chart_title(element):
    title = json.loads(element.proto.spec).get("title", "")
    return title if isinstance(title, str) else title.get("text", "")


def layer_data(chart, layer=0):
    data = chart.layer[layer].data
    return data if isinstance(data, pd.DataFrame) else chart.data


@pytest.mark.parametrize("name", METHODS)
@pytest.mark.parametrize("metric", METRIC_DISPLAYS)
def test_candidate_and_final_chart_values_match_actual_model(analysis, name, metric):
    model = analysis.models[name]
    trials = model.trials.copy(deep=True)
    chart = model_metric_curve(model, metric)
    spec = chart.to_dict()  # Includes Altair schema validation.
    assert name in spec["title"]
    assert spec["layer"][0]["encoding"]["x"]["title"] == "Jumlah klaster (K)"
    assert spec["layer"][0]["encoding"]["y"]["title"] == METRIC_DISPLAYS[metric].axis_title
    data = layer_data(chart)
    np.testing.assert_array_equal(data[metric], trials[metric])
    assert data.loc[data.status.eq("K terpilih"), "k"].tolist() == [model.k]
    assert data.label.tolist() == [f"{value:.4f}" for value in trials[metric]]
    final = layer_data(chart, -1)
    assert final.k.tolist() == [model.k]
    assert final[metric].tolist() == [model.metrics[metric]]
    recalculated = evaluate(analysis.prepared.X, model.villages.klaster.to_numpy())
    assert final[metric].iloc[0] == pytest.approx(recalculated[metric], abs=1e-12)
    pd.testing.assert_frame_equal(model.trials, trials, check_exact=True)


def test_missing_candidates_and_final_scores_are_not_fabricated(analysis):
    model = analysis.models["K-Means"]
    # Presentation must not assume the final rerun has the candidate's score.
    metrics = {**model.metrics, "silhouette": model.metrics["silhouette"] - .01}
    partial = replace(model, trials=model.trials[model.trials.k.ne(4)], metrics=metrics)
    chart = model_metric_curve(partial, "silhouette")
    data = layer_data(chart)
    assert 4 not in data.k.values
    assert data.segmen.nunique() == 2
    assert layer_data(chart, -1).silhouette.iloc[0] == metrics["silhouette"]
    assert data.loc[data.k.eq(model.k), "silhouette"].iloc[0] != metrics["silhouette"]


def test_silhouette_plot_matches_samples_clusters_and_final_score(analysis):
    for model in analysis.models.values():
        samples = silhouette_analysis(analysis.prepared, model)
        assert samples.silhouette.mean() == pytest.approx(
            model.metrics["silhouette"], abs=1e-12,
        )
        assert samples.groupby("klaster").size().to_dict() == (
            model.villages.groupby("klaster").size().to_dict()
        )
        assert samples.groupby("klaster").silhouette.apply(
            lambda values: values.is_monotonic_decreasing
        ).all()

        mean = float(model.metrics["silhouette"])
        fig = _silhouette_plot(samples, mean, model.name, model.k)
        try:
            ax = fig.axes[0]
            expected_labels = [
                f"Klaster {cluster}\n(n={size})"
                for cluster, size in samples.groupby("klaster").size().items()
            ]
            assert [tick.get_text() for tick in ax.get_yticklabels()] == expected_labels
            assert len(ax.get_yticks()) == model.k
            assert any(
                line.get_linestyle() == "--"
                and np.allclose(line.get_xdata(), [mean, mean])
                for line in ax.lines
            )
            assert model.name in ax.get_title()
            assert f"rata-rata = {mean:.4f}" in ax.get_title()
            assert ax.get_xlabel() == "Silhouette Coefficient (s_i)"
            assert ax.get_ylabel() == "Klaster final"
        finally:
            plt.close(fig)

        contents = render_silhouette_plot(samples, mean, model.name, model.k)
        assert contents.startswith(b"\x89PNG\r\n\x1a\n")
        assert len(contents) > 10000
        with pytest.raises(ValueError, match="tidak sama dengan Silhouette Score final"):
            render_silhouette_plot(samples, mean + .01, model.name, model.k)


def test_comparison_expander_keeps_table_and_drops_old_diagnostics():
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
    app.switch_page("app_pages/klasterisasi.py").run()
    key = sha256((ROOT / "2425.csv").read_bytes()).hexdigest()[:12]
    app.session_state[f"comparison_{key}"] = True
    app.run()
    assert not app.exception, [error.message for error in app.exception]
    assert app.dataframe[0].value.columns.tolist() == [
        "algoritma", "k", "silhouette", "dbi", "chi", "rata_rata_peringkat",
    ]
    titles = [chart_title(element) for element in app.get("vega_lite_chart")]
    assert not any(
        marker in title
        for title in titles
        for marker in ("Silhouette Plot", "DBI =", "CHI =")
    )


def test_silhouette_panel_can_switch_between_final_algorithms():
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
    app.switch_page("app_pages/klasterisasi.py").run()
    key = sha256((ROOT / "2425.csv").read_bytes()).hexdigest()[:12]
    initial = app.session_state[f"algorithm_tabs_{key}"]
    prefix = f"result_{key}_{initial.replace(' ', '_')}"
    base_images = len(app.get("image"))
    app.button(key=f"{prefix}_silhouette_button").click().run()
    assert not app.exception, [error.message for error in app.exception]
    assert app.session_state[f"{prefix}_silhouette_open"] is True
    assert len(app.get("image")) == base_images + 1
    selector = app.selectbox(key=f"{prefix}_silhouette_algorithm")
    assert selector.options == list(METHODS)
    assert any(
        "Silhouette Plot per algoritma" in element.value
        for element in app.markdown
    )
    assert any(
        f"**{initial} · K=" in caption.value and "Silhouette Score" in caption.value
        for caption in app.caption
    )

    selector.select("AHC").run()
    assert not app.exception, [error.message for error in app.exception]
    assert any(
        "**AHC · K=" in caption.value and "Silhouette Score" in caption.value
        for caption in app.caption
    )
    assert len(app.get("image")) == base_images + 1
    app.button(key=f"{prefix}_silhouette_close").click().run()
    assert not app.exception
    assert app.session_state[f"{prefix}_silhouette_open"] is False
    assert len(app.get("image")) == base_images


def test_indicator_boxplot_panel_uses_selected_final_algorithm():
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
    app.switch_page("app_pages/klasterisasi.py").run()
    key = sha256((ROOT / "2425.csv").read_bytes()).hexdigest()[:12]
    initial = app.session_state[f"algorithm_tabs_{key}"]
    prefix = f"result_{key}_{initial.replace(' ', '_')}"
    app.session_state[f"{prefix}_views"] = "Analisis data"
    app.session_state[f"{prefix}_eda_view"] = "Korelasi"
    app.run()
    base_images = len(app.get("image"))
    app.session_state[f"{prefix}_eda_view"] = "Distribusi"
    app.run()
    assert not app.exception, [error.message for error in app.exception]
    assert len(app.get("image")) == base_images + 1
    selector = app.selectbox(key=f"{prefix}_indicator_box_algorithm")
    assert selector.options == list(METHODS)
    assert any(
        f"Label klaster final **{initial}**" in caption.value
        for caption in app.caption
    )

    selector.select("AHC").run()
    assert not app.exception, [error.message for error in app.exception]
    assert any(
        "Label klaster final **AHC**" in caption.value
        for caption in app.caption
    )
    assert len(app.get("image")) == base_images + 1


def test_each_algorithm_sends_actual_candidate_and_final_scores_to_browser(analysis, monkeypatch):
    import firewatch.state as state

    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
    app.switch_page("app_pages/klasterisasi.py").run()
    assert not app.exception
    key = sha256(app.session_state["dataset_bytes"]).hexdigest()[:12]
    monkeypatch.setattr(
        state, "run_analysis",
        lambda *_: (_ for _ in ()).throw(AssertionError("Grafik tidak boleh melatih ulang model")),
    )
    for name in METHODS:
        prefix = f"result_{key}_{name.replace(' ', '_')}"
        app.session_state[f"algorithm_tabs_{key}"] = name
        app.session_state[f"{prefix}_views"] = "Evaluasi & pemilihan K"
        app.run()
        assert not app.exception, [error.message for error in app.exception]
        charts = app.get("vega_lite_chart")
        assert len(charts) == 3
        model = analysis.models[name]
        for element, metric in zip(charts, METRIC_DISPLAYS):
            pd.testing.assert_series_equal(chart_data(element)[metric], model.trials[metric], check_names=False)
            assert chart_data(element, -1)[metric].tolist() == [model.metrics[metric]]
        cards = {card.label: card.value for card in app.metric}
        assert cards["Silhouette ↑"] == number(model.metrics["silhouette"], 4)
        assert cards["Davies–Bouldin ↓"] == number(model.metrics["dbi"], 4)
        assert cards["Calinski–Harabasz ↑"] == number(model.metrics["chi"], 4)


def test_comparison_browser_values_follow_uploaded_dataset():
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
    app.switch_page("app_pages/dataset.py").run()
    raw = read_dataset((ROOT / "2425.csv").read_bytes())
    uploaded = raw[raw.tahun.eq(2025)].head(32).to_csv(index=False).encode("utf-8")
    app.file_uploader[0].set_value(("evaluasi_32.csv", uploaded, "text/csv")).run()
    app.switch_page("app_pages/klasterisasi.py").run()
    key = sha256(uploaded).hexdigest()[:12]
    app.session_state[f"comparison_{key}"] = True
    app.run()
    assert not app.exception, [error.message for error in app.exception]
    expected = run_analysis(read_dataset(uploaded))
    table = app.dataframe[0].value.set_index("algoritma")
    for name in expected.ranking.algoritma:
        model = expected.models[name]
        assert table.loc[name, "silhouette"] == model.metrics["silhouette"]
        assert table.loc[name, "dbi"] == model.metrics["dbi"]
        assert table.loc[name, "chi"] == model.metrics["chi"]
    titles = [chart_title(element) for element in app.get("vega_lite_chart")]
    assert not any(
        marker in title
        for title in titles
        for marker in ("Silhouette Plot", "DBI =", "CHI =")
    )