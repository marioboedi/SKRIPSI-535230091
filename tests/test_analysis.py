from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sklearn.preprocessing import StandardScaler

from firewatch.analysis import (
    CONTEXT, FEATURES, KEYS, DatasetError, build_profiles, choose_k, cluster_membership_summary,
    evaluate, fit_labels, prepare_data, read_dataset, risk_label, run_analysis,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def raw():
    return read_dataset((ROOT / "2425.csv").read_bytes())


@pytest.fixture(scope="module")
def analysis(raw):
    return run_analysis(raw)


def test_standardize_each_year_before_averaging_and_exclude_context(raw):
    prepared = prepare_data(raw)
    assert len(raw) == 534
    assert len(prepared.villages) == 267
    assert prepared.X.shape == (267, 9)
    expected = raw[KEYS].copy()
    means = raw.groupby("tahun")[FEATURES].transform("mean")
    deviations = raw.groupby("tahun")[FEATURES].transform(lambda values: values.std(ddof=0))
    expected[FEATURES] = (raw[FEATURES] - means) / deviations
    expected = expected.groupby(KEYS, as_index=False)[FEATURES].mean()
    np.testing.assert_allclose(prepared.X, expected[FEATURES].to_numpy(), atol=1e-12)
    pooled = raw[KEYS].copy()
    pooled[FEATURES] = StandardScaler().fit_transform(raw[FEATURES])
    pooled = pooled.groupby(KEYS, as_index=False)[FEATURES].mean()
    assert not np.allclose(prepared.X, pooled[FEATURES].to_numpy())
    assert prepared.villages.jumlah_periode.eq(2).all()
    changed = raw.copy()
    changed[CONTEXT] = changed[CONTEXT] * 0.9
    np.testing.assert_allclose(prepare_data(changed).X, prepared.X)


def test_yearly_standardization_is_independent_of_other_year_baselines(raw):
    changed = raw.copy()
    mask = changed.tahun.eq(2025)
    changed.loc[mask, FEATURES] = changed.loc[mask, FEATURES] * 0.8 + 1
    np.testing.assert_allclose(prepare_data(changed).X, prepare_data(raw).X, atol=1e-12)


@pytest.mark.parametrize("name,fixture,optimal_k", [
    ("K-Means", "prompt02_kmeans.csv", 3),
    ("AHC", "prompt02_ahc.csv", 3),
    ("Spectral Bridges", "prompt02_spectral_bridges.csv", 2),
])
def test_all_candidate_metrics_reproduce_prompt02(analysis, name, fixture, optimal_k):
    reference = pd.read_csv(ROOT / "tests" / "fixtures" / fixture)
    model = analysis.models[name]
    assert model.k == optimal_k
    np.testing.assert_array_equal(model.trials.k, reference.k)
    for metric in ["silhouette", "dbi", "chi"]:
        np.testing.assert_allclose(model.trials[metric], reference[metric], rtol=0, atol=0.000050001)


@pytest.mark.parametrize("e,g,label", [
    (0.5, 0.5, "Risiko Rendah"),
    (0.50001, 0.5, "Dominan Bahaya Kelistrikan"),
    (0.5, 0.50001, "Dominan Bahaya Gas"),
    (0.6, 0.6, "Dominan Bahaya Keduanya"),
    (-1.2, -0.7, "Risiko Rendah"),
])
def test_exact_risk_threshold(e, g, label):
    assert risk_label(e, g) == label


def test_majority_vote_and_disagreement_tiebreak():
    trials = pd.DataFrame({"k": [2, 3, 4], "silhouette": [.5, .4, .3], "dbi": [.9, .5, .6], "chi": [100, 300, 200]})
    k, winners, message = choose_k(trials)
    assert k == 3 and winners == {"silhouette": 2, "dbi": 3, "chi": 3}
    assert "2 dari 3" in message
    trials["chi"] = [100, 200, 300]
    k, _, message = choose_k(trials)
    assert k == 3  # mean ordinal ranks: 2.333, 1.667, 2.000
    assert "berbeda" in message


def test_invalid_uploads_do_not_silently_impute(raw):
    with pytest.raises(DatasetError, match="Kolom wajib"):
        read_dataset(b"foo,bar\n1,2\n")
    invalid = raw.copy()
    invalid.loc[0, FEATURES[0]] = np.nan
    with pytest.raises(DatasetError, match="nilai kosong"):
        prepare_data(invalid)
    invalid = raw.copy()
    invalid.loc[0, FEATURES[0]] = 101
    with pytest.raises(DatasetError, match="0 dan 100"):
        prepare_data(invalid)
    with pytest.raises(DatasetError, match="duplikat"):
        prepare_data(pd.concat([raw, raw.iloc[:1]], ignore_index=True))
    with pytest.raises(DatasetError, match="unik"):
        read_dataset(b"tahun,tahun\n2024,2025\n")


def test_semicolon_decimal_csv(raw):
    content = raw.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")
    loaded = read_dataset(content)
    np.testing.assert_allclose(loaded[FEATURES], raw[FEATURES])


def test_missing_period_is_reported(raw):
    prepared = prepare_data(raw.drop(index=0))
    assert len(prepared.villages) == 267
    assert prepared.villages.jumlah_periode.min() == 1
    assert any("1 kelurahan" in note for note in prepared.notes)


def test_all_real_models_and_candidate_search(analysis):
    assert not analysis.failures
    assert set(analysis.models) == {"K-Means", "AHC", "Spectral Bridges"}
    for model in analysis.models.values():
        assert model.trials.k.tolist() == list(range(2, 11))
        assert len(model.villages) == 267
        assert model.villages.klaster.nunique() == model.k
        assert model.profiles.jumlah_kelurahan.sum() == 267
        assert model.villages.interpretasi.notna().all()
        recomputed = evaluate(analysis.prepared.X, model.villages.klaster.to_numpy())
        for metric, score in recomputed.items():
            assert score == pytest.approx(model.metrics[metric], abs=1e-10)
    assert analysis.best_name == analysis.ranking.iloc[0].algoritma


def test_centroids_drive_each_villages_interpretation(analysis):
    for model in analysis.models.values():
        joined = analysis.prepared.standardized.copy()
        joined["klaster"] = model.villages.klaster.to_numpy()
        for _, profile in model.profiles.iterrows():
            expected = joined.loc[joined.klaster == profile.klaster, FEATURES].mean()
            np.testing.assert_allclose(profile[FEATURES].to_numpy(dtype=float), expected.to_numpy())
            members = model.villages[model.villages.klaster == profile.klaster]
            assert members.interpretasi.eq(risk_label(profile.risk_listrik, profile.risk_gas)).all()


def test_ahc_summary_uses_final_memberships_even_after_filtering_and_reordering(analysis):
    model = analysis.models["AHC"]
    original = model.villages.copy(deep=True)
    expected_villages, expected_profiles = build_profiles(analysis.prepared, fit_labels("AHC", model.k, analysis.prepared.X))
    pd.testing.assert_frame_equal(model.villages, expected_villages)
    pd.testing.assert_frame_equal(model.profiles, expected_profiles)
    summary = cluster_membership_summary(model.villages)
    assert len(summary) == model.k == 3
    assert summary.klaster.tolist() == [1, 2, 3]
    assert summary.jumlah.tolist() == [1, 128, 138]
    expected = expected_profiles.set_index("klaster")
    for row in summary.itertuples(index=False):
        assert row.jumlah == expected.loc[row.klaster, "jumlah_kelurahan"]
        assert row.interpretasi == expected.loc[row.klaster, "interpretasi"]
        assert row.persentase == row.jumlah / len(model.villages)
    # Different identifiers and a subset verify that no displayed cluster,
    # count, percentage or interpretation is supplied by a fixed AHC label list.
    changed = model.villages[model.villages.klaster.isin([2, 3])].sample(frac=1, random_state=42).copy()
    changed["klaster"] = changed.klaster.map({2: 17, 3: 4})
    filtered = cluster_membership_summary(changed)
    assert filtered.klaster.tolist() == [4, 17]
    assert filtered.jumlah.tolist() == [138, 128]
    np.testing.assert_allclose(filtered.persentase, np.array([138, 128]) / 266)
    assert filtered.interpretasi.tolist() == ["Risiko Rendah", "Risiko Rendah"]
    pd.testing.assert_frame_equal(model.villages, original)


def test_cluster_summary_rejects_missing_labels_or_mixed_centroid_interpretations(analysis):
    villages = analysis.models["AHC"].villages.copy(deep=True)
    first_member = villages.index[villages.klaster.eq(2)][0]
    villages.loc[first_member, "interpretasi"] = "Dominan Bahaya Gas"
    with pytest.raises(ValueError, match="Satu klaster"):
        cluster_membership_summary(villages)
    villages.loc[first_member, "klaster"] = np.nan
    with pytest.raises(ValueError, match="setiap kelurahan"):
        cluster_membership_summary(villages)


def test_spectral_bridges_reproducibility(analysis):
    from threadpoolctl import threadpool_limits

    model = analysis.models["Spectral Bridges"]
    with threadpool_limits(limits=1):
        labels = fit_labels("Spectral Bridges", model.k, analysis.prepared.X)
    villages, _ = build_profiles(analysis.prepared, labels)
    np.testing.assert_array_equal(villages.klaster, model.villages.klaster)


def test_constant_data_returns_clear_error(raw):
    identical = raw.copy()
    identical[FEATURES] = 1.0
    with pytest.raises(DatasetError, match="pola indikator yang sama"):
        run_analysis(identical)


def test_small_dataset_handles_unavailable_spectral(raw):
    villages = raw[KEYS].drop_duplicates().head(8)
    subset = raw.merge(villages, on=KEYS)
    result = run_analysis(subset)
    assert "Spectral Bridges" in result.failures
    assert set(result.models) == {"K-Means", "AHC"}
    assert result.models["K-Means"].trials.k.max() == 7


def test_report_archive_contains_real_results_and_provenance(analysis, monkeypatch):
    import io
    import json
    import zipfile
    from types import SimpleNamespace

    from firewatch import ui

    monkeypatch.setattr(ui.st, "session_state", SimpleNamespace(dataset_name="2425.csv", dataset_bytes=(ROOT / "2425.csv").read_bytes()))
    with zipfile.ZipFile(io.BytesIO(ui.report_zip(analysis))) as archive:
        assert archive.testzip() is None
        metadata = json.loads(archive.read("metodologi.json"))
        assert metadata["jumlah_kelurahan"] == 267
        assert metadata["library_versions"]["spectral-bridges"] == "1.3.0"
        assert metadata["pipeline_version"] == "1.1.0"
        assert metadata["label_version"] == "2"
        assert metadata["label_risiko_rendah"]["nama"] == "Risiko Rendah"
        assert "terpisah per tahun" in metadata["praproses"]
        assert len(metadata["source_sha256"]) == 64
        for slug, name in [("k_means", "K-Means"), ("ahc", "AHC"), ("spectral_bridges", "Spectral Bridges")]:
            exported = pd.read_csv(io.BytesIO(archive.read(f"{slug}/hasil_kelurahan.csv")))
            assert len(exported) == 267
            assert "Risiko Rendah" in exported.interpretasi.unique()
            assert "Risiko Aman" not in exported.interpretasi.unique()
            np.testing.assert_array_equal(exported.klaster, analysis.models[name].villages.klaster)
            assert len(pd.read_csv(io.BytesIO(archive.read(f"{slug}/pencarian_k.csv")))) == 9


def test_ahc_tab_label_changes_only_copied_interpretations(analysis):
    from firewatch.profiles import ahc_tab_result

    for name, model in analysis.models.items():
        members, profiles = model.villages.copy(deep=True), model.profiles.copy(deep=True)
        view = ahc_tab_result(model)
        if name == "AHC":
            assert view is not model
            assert view.villages.loc[view.villages.klaster.eq(2), "interpretasi"].eq("Dominan Bahaya Keduanya").all()
            assert view.profiles.set_index("klaster").loc[2, "interpretasi"] == "Dominan Bahaya Keduanya"
            assert view.villages.groupby("klaster").size().to_dict() == {1: 1, 2: 128, 3: 138}
            assert view.villages.klaster.eq(2).mean() == 128 / 267
            pd.testing.assert_frame_equal(view.villages.drop(columns="interpretasi"), members.drop(columns="interpretasi"), check_exact=True)
            pd.testing.assert_frame_equal(view.profiles.drop(columns="interpretasi"), profiles.drop(columns="interpretasi"), check_exact=True)
            pd.testing.assert_series_equal(view.villages.loc[view.villages.klaster.ne(2), "interpretasi"], members.loc[members.klaster.ne(2), "interpretasi"])
        else:
            assert view is model
        assert view.metrics == model.metrics
        assert view.k == model.k
        pd.testing.assert_frame_equal(view.trials, model.trials, check_exact=True)
        pd.testing.assert_frame_equal(model.villages, members, check_exact=True)
        pd.testing.assert_frame_equal(model.profiles, profiles, check_exact=True)


def test_ahc_tab_download_updates_only_ahc_profile_labels(analysis, monkeypatch):
    import io
    import json
    import zipfile
    from types import SimpleNamespace
    from firewatch import ui

    monkeypatch.setattr(ui.st, "session_state", SimpleNamespace(dataset_name="2425.csv", dataset_bytes=(ROOT / "2425.csv").read_bytes()))
    with zipfile.ZipFile(io.BytesIO(ui.report_zip(analysis))) as original, zipfile.ZipFile(io.BytesIO(ui.report_zip(analysis, ahc_tab=True))) as updated:
        assert original.namelist() == updated.namelist()
        for path in original.namelist():
            if path == "metodologi.json":
                metadata = json.loads(updated.read(path))
                assert metadata.pop("label_tampilan_ahc") == {"klaster_2": "Dominan Bahaya Keduanya"}
                assert metadata == json.loads(original.read(path))
            elif path in {"ahc/hasil_kelurahan.csv", "ahc/profil_klaster.csv"}:
                before, after = pd.read_csv(io.BytesIO(original.read(path))), pd.read_csv(io.BytesIO(updated.read(path)))
                expected = before.copy(deep=True)
                expected.loc[expected.klaster.eq(2), "interpretasi"] = "Dominan Bahaya Keduanya"
                pd.testing.assert_frame_equal(after, expected, check_exact=True)
            else:
                assert updated.read(path) == original.read(path)
