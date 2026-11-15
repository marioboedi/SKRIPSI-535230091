from base64 import b64decode
from hashlib import sha256
import json
from pathlib import Path
from xml.etree import ElementTree

import pandas as pd
import pytest
from streamlit.dataframe_util import convert_arrow_bytes_to_pandas_df
from streamlit.testing.v1 import AppTest

from firewatch.charts import cluster_distribution
from firewatch.palette import cluster_color
from firewatch.ui import number

ROOT = Path(__file__).resolve().parents[1]


def open_app():
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
    assert not app.exception
    return app


def data_key(app):
    return sha256(app.session_state["dataset_bytes"]).hexdigest()[:12]


def composition_elements(app):
    elements = list(app.main)
    start = next(i for i, element in enumerate(elements) if element.type == "subheader" and element.value == "Sebaran klaster dan profil")
    end = next(i for i, element in enumerate(elements) if element.type == "subheader" and element.value == "Hasil per kelurahan")
    return elements[start:end]


def composition_data(app):
    chart = app.get("vega_lite_chart")[0].proto
    spec = json.loads(chart.spec)
    dataset_name = spec["layer"][0]["data"]["name"]
    dataset = next(data for data in chart.datasets if data.name == dataset_name)
    return convert_arrow_bytes_to_pandas_df(dataset.data.data)


def test_all_requested_pages_render():
    app = open_app()
    assert app.title[0].value == "Ikhtisar kerawanan kebakaran"
    assert {m.label: m.value for m in app.metric}["Kelurahan dianalisis"] == "267"
    assert not any("Seribu" in toggle.label for toggle in app.toggle)
    assert any("**1 kelurahan** · 0,4%" == element.value for element in app.markdown)
    for page in ["dataset", "klasterisasi", "faq", "tentang"]:
        app.switch_page(f"app_pages/{page}.py").run()
        assert not app.exception, [error.message for error in app.exception]
        if page == "klasterisasi":
            assert not any("Seribu" in toggle.label for toggle in app.toggle)
            assert any(s.value == "Sebaran klaster dan profil" for s in app.subheader)
            assert any("**1 kelurahan** · 0,4%" == element.value for element in app.markdown)
        if page == "tentang":
            content = "\n".join(element.value for element in app.markdown)
            assert "Dr. Bagus Mulyawan, S.Kom., M.M." in content
            assert "Penelitian membandingkan kualitas pengelompokan tiga algoritma melalui" not in content


def test_dataset_filters_and_empty_result():
    from firewatch.state import DRIVE_URL

    app = open_app().switch_page("app_pages/dataset.py").run()
    assert len(app.link_button) == 1
    assert app.link_button[0].value == "Data Terbaru"
    assert app.link_button[0].proto.url == DRIVE_URL
    assert not app.get("download_button")
    assert len(app.dataframe[0].value) == 534
    key = data_key(app)
    option = next(v for v in app.selectbox(key=f"dataset_search_{key}").options if v.startswith("Kelurahan Angke ·"))
    app.selectbox(key=f"dataset_search_{key}").select(option).run()
    assert len(app.dataframe[0].value) >= 2
    assert app.dataframe[0].value.kelurahan.str.contains("ANGKE").all()
    app.multiselect(key=f"dataset_year_{key}").set_value([2025]).run()
    assert app.dataframe[0].value.tahun.eq(2025).all()
    app.multiselect(key=f"dataset_city_{key}").set_value(["KOTA ADM JAKARTA TIMUR"]).run()
    assert app.dataframe[0].value.empty
    assert app.info and not app.exception


def test_invalid_upload_preserves_active_data():
    app = open_app().switch_page("app_pages/dataset.py").run()
    original = app.session_state["dataset_bytes"]
    app.file_uploader[0].set_value(("rusak.csv", b"foo,bar\n1,2\n", "text/csv")).run()
    assert app.error
    assert "Kolom wajib" in app.error[0].value
    assert app.session_state["dataset_bytes"] == original
    assert app.session_state["dataset_name"] == "2425.csv"
    assert not app.exception


def test_uploaded_dataset_is_used_across_pages_and_reset():
    app = open_app().switch_page("app_pages/dataset.py").run()
    raw = pd.read_csv(ROOT / "2425.csv")
    uploaded = raw[raw.tahun == 2025].head(32).to_csv(index=False).encode("utf-8")
    app.file_uploader[0].set_value(("uji_32.csv", uploaded, "text/csv")).run()
    assert not app.exception
    assert app.session_state["dataset_name"] == "uji_32.csv"
    assert len(app.dataframe[0].value) == 32
    app.switch_page("app_pages/klasterisasi.py").run()
    assert not app.exception
    assert len(app.dataframe[0].value) == 32
    summary = composition_data(app)
    assert len(summary) == int(app.metric[0].value)
    assert summary.jumlah.sum() == 32
    pd.testing.assert_frame_equal(summary, cluster_distribution(app.dataframe[0].value))
    app.switch_page("app_pages/beranda.py").run()
    assert {m.label: m.value for m in app.metric}["Kelurahan dianalisis"] == "32"
    app.switch_page("app_pages/dataset.py").run()
    app.button(key="reset_dataset").click().run()
    assert app.session_state["dataset_name"] == "2425.csv"
    assert len(app.dataframe[0].value) == 534
    assert not app.exception


def test_each_algorithm_and_nested_result_view():
    app = open_app().switch_page("app_pages/klasterisasi.py").run()
    key = data_key(app)
    for name in ["AHC", "K-Means", "Spectral Bridges"]:
        app.session_state[f"algorithm_tabs_{key}"] = name
        app.run()
        assert not app.exception
        expected_k = {"AHC": "3", "K-Means": "3", "Spectral Bridges": "2"}
        assert app.metric[0].value == expected_k[name]
        assert len(app.dataframe[0].value) == 267
        prefix = f"result_{key}_{name.replace(' ', '_')}"
        for view in ["Profil klaster", "Evaluasi & pemilihan K", "Peta & kelurahan"]:
            app.session_state[f"{prefix}_views"] = view
            app.run()
            assert not app.exception, [error.message for error in app.exception]
            if view == "Evaluasi & pemilihan K":
                assert app.dataframe[0].value.k.tolist() == list(range(2, 11))


def test_result_search_does_not_recluster():
    app = open_app().switch_page("app_pages/klasterisasi.py").run()
    key = data_key(app)
    selected = app.session_state[f"algorithm_tabs_{key}"]
    prefix = f"result_{key}_{selected.replace(' ', '_')}"
    original_k = app.metric[0].value
    option = next(v for v in app.selectbox(key=f"{prefix}_search").options if v.startswith("Kelurahan Ancol ·"))
    app.selectbox(key=f"{prefix}_search").select(option).run()
    assert not app.exception
    assert len(app.dataframe[0].value) == 1
    assert app.dataframe[0].value.iloc[0].kelurahan == "ANCOL"
    assert app.metric[0].value == original_k
    app.multiselect(key=f"{prefix}_cities").set_value(["KOTA ADM JAKARTA BARAT"]).run()
    assert not app.exception
    assert not app.dataframe
    assert app.info


def test_analysis_views_use_cached_models(monkeypatch):
    import firewatch.state as state

    app = open_app().switch_page("app_pages/klasterisasi.py").run()
    key = data_key(app)
    selected = app.session_state[f"algorithm_tabs_{key}"]
    prefix = f"result_{key}_{selected.replace(' ', '_')}"
    original_k = app.metric[0].value
    monkeypatch.setattr(state, "run_analysis", lambda *_: (_ for _ in ()).throw(AssertionError("Interaksi grafik tidak boleh melatih ulang model")))
    app.session_state[f"{prefix}_views"] = "Analisis data"
    app.run()
    for choice in ["Korelasi", "Distribusi", "Antar klaster", "Jumlah & pemisahan"]:
        app.session_state[f"{prefix}_eda_view"] = choice
        app.run()
        assert not app.exception, [error.message for error in app.exception]
        assert app.metric[0].value == original_k
        assert app.get("image")
    app.session_state[f"{prefix}_eda_view"] = "Antar klaster"
    app.run()
    app.selectbox(key=f"{prefix}_eda_feature").select("tabung_rusak").run()
    app.session_state[f"{prefix}_eda_means"] = True
    app.run()
    assert not app.exception, [error.message for error in app.exception]


@pytest.mark.parametrize("name,expected_k", [("AHC", 3), ("K-Means", 3), ("Spectral Bridges", 2)])
def test_unified_summary_matches_actual_memberships_and_profiles_for_every_algorithm(name, expected_k):
    app = open_app().switch_page("app_pages/klasterisasi.py").run()
    key = data_key(app)
    prefix = f"result_{key}_{name.replace(' ', '_')}"
    app.session_state[f"algorithm_tabs_{key}"] = name
    # Returning sessions can still contain this obsolete display preference.
    app.session_state[f"{prefix}_color_mode"] = "Profil kerawanan"
    app.run()
    assert not app.exception
    assert app.metric[0].value == str(expected_k)
    assert sum(s.value == "Sebaran klaster dan profil" for s in app.subheader) == 1
    assert not any(s.value in {"Sebaran klaster", "Sebaran profil"} for s in app.subheader)
    assert not any(getattr(element, "key", None) == f"{prefix}_color_mode" for element in app.main)
    table = app.dataframe[0].value
    expected = cluster_distribution(table)
    actual = composition_data(app)
    pd.testing.assert_frame_equal(actual[expected.columns], expected)
    assert len(actual) == table.klaster.nunique() == expected_k
    assert actual.klaster.is_unique
    assert actual.jumlah.sum() == len(table) == 267
    assert actual.persentase.sum() == pytest.approx(1)
    assert any(c.value == f"{expected_k} klaster · 267 kelurahan" for c in app.caption)

    legend = composition_elements(app)
    labels = [
        ElementTree.fromstring(b64decode(url.split(",", 1)[1])).find("{http://www.w3.org/2000/svg}text").text
        for element in legend if element.type == "image" for url in element.value
        if url.startswith("data:image/svg+xml;base64,")
    ]
    profiles = [element.value for element in legend if element.type == "caption" and element.value.startswith("Profil kerawanan:")]
    quantities = [element.value for element in legend if element.type == "markdown" and " kelurahan** · " in element.value]
    assert labels == actual.kategori.tolist()
    if name == "AHC":
        assert profiles == [f"Profil kerawanan: {row.interpretasi} · {row.profil_karakteristik}" for row in actual.itertuples(index=False)]
        assert actual.set_index("klaster").loc[2, "profil_karakteristik"] != actual.set_index("klaster").loc[3, "profil_karakteristik"]
        assert actual.set_index("klaster").loc[2, "interpretasi"] == "Dominan Bahaya Keduanya"
        assert actual.set_index("klaster").loc[3, "interpretasi"] == "Risiko Rendah"
        assert not any(element.type == "expander" and element.label == "Dasar interpretasi AHC" for element in app.main)
        assert actual.set_index("klaster").loc[2, "jumlah"] == 128
        assert number(actual.set_index("klaster").loc[2, "persentase"] * 100, 1) == "47,9"
    else:
        pd.testing.assert_frame_equal(actual, expected)
        assert profiles == [f"Profil kerawanan: {row.interpretasi}" for row in actual.itertuples(index=False)]
    assert quantities == [f"**{row.jumlah} kelurahan** · {number(row.persentase * 100, 1)}%" for row in actual.itertuples(index=False)]

    spec = json.loads(app.get("vega_lite_chart")[0].proto.spec)
    encoding = spec["layer"][0]["encoding"]
    assert encoding["color"]["scale"]["domain"] == labels
    assert len(set(encoding["color"]["scale"]["range"])) == expected_k
    assert encoding["detail"]["field"] == "klaster"
    assert encoding["color"]["legend"] is None
    tooltip_fields = {"klaster", "jumlah", "persentase", "interpretasi"}
    if name == "AHC":
        tooltip_fields |= {"profil_karakteristik", "risk_listrik", "risk_gas"}
    assert {item["field"] for item in encoding["tooltip"]} == tooltip_fields
    map_spec = json.loads(app.get("deck_gl_json_chart")[0].proto.json)
    for row in map_spec["layers"][-1]["data"]:
        color = cluster_color(row["klaster"])
        assert row["color"][:3] == [int(color[i:i + 2], 16) for i in (1, 3, 5)]
        assert row["interpretasi"] == actual.set_index("klaster").loc[row["klaster"], "interpretasi"]


def test_ahc_unified_summary_filters_and_restores_all_clusters_without_retraining(monkeypatch):
    import firewatch.state as state
    from firewatch.analysis import RISK_LABEL_VERSION

    app = open_app().switch_page("app_pages/klasterisasi.py").run()
    key = data_key(app)
    app.session_state[f"algorithm_tabs_{key}"] = "AHC"
    app.run()
    prefix = f"result_{key}_AHC"
    original_results = app.dataframe[0].value.copy(deep=True)
    original_summary = composition_data(app)
    assert original_summary.klaster.tolist() == [1, 2, 3]
    assert original_summary.jumlah.tolist() == [1, 128, 138]
    monkeypatch.setattr(state, "run_analysis", lambda *_: (_ for _ in ()).throw(AssertionError("Filter tidak boleh melatih ulang model")))
    app.multiselect(key=f"{prefix}_risks_{RISK_LABEL_VERSION}").set_value(["Dominan Bahaya Keduanya"]).run()
    assert not app.exception
    assert app.metric[0].value == "3"
    assert len(app.dataframe[0].value) == 128
    summary = composition_data(app)
    expected = cluster_distribution(app.dataframe[0].value)
    pd.testing.assert_frame_equal(summary[expected.columns], expected)
    pd.testing.assert_frame_equal(summary.set_index("klaster")[["risk_listrik", "risk_gas", "profil_karakteristik"]], original_summary.set_index("klaster").loc[[2], ["risk_listrik", "risk_gas", "profil_karakteristik"]])
    assert summary.klaster.tolist() == [2]
    assert summary.jumlah.tolist() == [128]
    assert summary.interpretasi.tolist() == ["Dominan Bahaya Keduanya"]
    assert any(c.value == "1 klaster · 128 kelurahan" for c in app.caption)
    assert any(m.value == "**128 kelurahan** · 100,0%" for m in app.markdown)
    app.multiselect(key=f"{prefix}_risks_{RISK_LABEL_VERSION}").set_value([]).run()
    assert not app.exception
    assert app.metric[0].value == "3"
    pd.testing.assert_frame_equal(app.dataframe[0].value, original_results)
    pd.testing.assert_frame_equal(composition_data(app), original_summary)
    app.session_state[f"{prefix}_views"] = "Profil klaster"
    app.run()
    assert not app.exception
    profiles = app.dataframe[0].value
    assert profiles.klaster.tolist() == [1, 2, 3]
    assert profiles.jumlah_kelurahan.tolist() == [1, 128, 138]
    assert profiles.set_index("klaster").loc[2, "interpretasi"] == "Dominan Bahaya Keduanya"
    assert not any(element.type == "expander" and element.label == "Dasar interpretasi AHC" for element in app.main)


def test_low_risk_label_is_consistent_in_filter_map_table_and_unified_summary():
    from firewatch.analysis import RISK_LABEL_VERSION

    app = open_app().switch_page("app_pages/klasterisasi.py").run()
    key = data_key(app)
    name = app.session_state[f"algorithm_tabs_{key}"]
    prefix = f"result_{key}_{name.replace(' ', '_')}"
    widget = app.multiselect(key=f"{prefix}_risks_{RISK_LABEL_VERSION}")
    assert "Risiko Rendah" in widget.options
    assert "Risiko Aman" not in widget.options
    widget.set_value(["Risiko Rendah"]).run()
    assert not app.exception
    assert len(app.dataframe[0].value) == 187
    assert app.dataframe[0].value.interpretasi.eq("Risiko Rendah").all()
    map_spec = json.loads(app.get("deck_gl_json_chart")[0].proto.json)
    assert all(row["interpretasi"] == "Risiko Rendah" for row in map_spec["layers"][-1]["data"])
    assert any(m.value == "**187 kelurahan** · 100,0%" for m in app.markdown)
    assert any(c.value == "Profil kerawanan: Risiko Rendah" for c in app.caption)
    summary = composition_data(app)
    assert summary.klaster.tolist() == [3]
    assert summary.interpretasi.tolist() == ["Risiko Rendah"]
    assert "Risiko Aman" not in "\n".join(c.value for c in app.caption)


def test_ahc_tab_label_and_download_scope_leave_home_and_other_tabs_unchanged(monkeypatch):
    from firewatch import ui

    contexts = []
    original_report = ui.report_zip

    def tracked_report(result, **options):
        contexts.append(options.get("ahc_tab", False))
        return original_report(result, **options)

    monkeypatch.setattr(ui, "report_zip", tracked_report)
    app = open_app()
    home_distribution = composition_data(app).copy(deep=True)
    home_metrics = [(metric.label, metric.value) for metric in app.metric]
    app.switch_page("app_pages/klasterisasi.py").run()
    key = data_key(app)
    app.session_state[f"algorithm_tabs_{key}"] = "AHC"
    app.run()
    assert not app.exception
    assert contexts[-1] is True
    table = app.dataframe[0].value
    member = int(table.index[table.klaster.eq(2)][0])
    app.selectbox(key=f"result_{key}_AHC_detail").set_value(member).run()
    assert not app.exception
    assert any(m.value == ":red-badge[Dominan Bahaya Keduanya]" for m in app.markdown)
    for name in ["K-Means", "Spectral Bridges"]:
        app.session_state[f"algorithm_tabs_{key}"] = name
        app.run()
        assert not app.exception
        assert contexts[-1] is False
        if name == "Spectral Bridges":
            assert app.dataframe[0].value.loc[app.dataframe[0].value.klaster.eq(2), "interpretasi"].eq("Risiko Rendah").all()
    app.switch_page("app_pages/beranda.py").run()
    assert not app.exception
    pd.testing.assert_frame_equal(composition_data(app), home_distribution, check_exact=True)
    assert [(metric.label, metric.value) for metric in app.metric] == home_metrics
