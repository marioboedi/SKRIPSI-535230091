from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from firewatch.analysis import ELECTRICITY, FEATURES, GAS, KEYS, prepare_data, read_dataset, run_method
from firewatch.profiles import ahc_profile_details

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def ahc():
    prepared = prepare_data(read_dataset((ROOT / "2425.csv").read_bytes()))
    return prepared, run_method("AHC", prepared)


def test_actual_centroids_explain_shared_category_and_different_characteristics(ahc):
    prepared, model = ahc
    original_members = model.villages.copy(deep=True)
    original_profiles = model.profiles.copy(deep=True)
    details = ahc_profile_details(prepared, model).set_index("klaster")
    independent = prepared.standardized.merge(model.villages[KEYS + ["klaster"]], on=KEYS, validate="one_to_one").groupby("klaster")[FEATURES].mean()
    pd.testing.assert_frame_equal(details[FEATURES], independent)
    np.testing.assert_allclose(details.risk_listrik, independent[ELECTRICITY].mean(axis=1), rtol=0, atol=1e-12)
    np.testing.assert_allclose(details.risk_gas, independent[GAS].mean(axis=1), rtol=0, atol=1e-12)
    assert details.jumlah_kelurahan.tolist() == [1, 128, 138]
    np.testing.assert_allclose(details.persentase, np.array([1, 128, 138]) / 267)
    assert details.loc[1, "interpretasi"] == "Dominan Bahaya Gas"
    assert details.loc[[2, 3], "interpretasi"].eq("Risiko Rendah").all()
    assert details.loc[[2, 3], ["risk_listrik", "risk_gas"]].le(.5).all().all()
    assert independent.loc[2].gt(0).all()
    assert independent.loc[3].lt(0).all()
    assert details.loc[2, "indikator_di_atas"] == details.loc[3, "indikator_di_bawah"] == len(FEATURES)
    assert details.loc[2, "profil_karakteristik"] != details.loc[3, "profil_karakteristik"]
    assert independent.loc[2, "selang_tertindih"] > .5
    assert details.loc[2, "risk_gas"] < .5  # The category uses the group mean, not one indicator.
    pd.testing.assert_frame_equal(model.villages, original_members)
    pd.testing.assert_frame_equal(model.profiles, original_profiles)


def test_characteristics_follow_identity_keys_when_rows_and_cluster_numbers_change(ahc):
    prepared, model = ahc
    original = ahc_profile_details(prepared, model).set_index("klaster")
    mapping = {1: 8, 2: 14, 3: 2}
    members = model.villages.sample(frac=1, random_state=35).copy()
    members["klaster"] = members.klaster.map(mapping)
    profiles = model.profiles.sample(frac=1, random_state=93).copy()
    profiles["klaster"] = profiles.klaster.map(mapping)
    shuffled = replace(prepared, standardized=prepared.standardized.sample(frac=1, random_state=4))
    actual = ahc_profile_details(shuffled, replace(model, villages=members, profiles=profiles)).set_index("klaster")
    for old, new in mapping.items():
        assert actual.loc[new, "profil_karakteristik"] == original.loc[old, "profil_karakteristik"]
        assert actual.loc[new, "interpretasi"] == original.loc[old, "interpretasi"]
        np.testing.assert_allclose(actual.loc[new, FEATURES].to_numpy(dtype=float), original.loc[old, FEATURES].to_numpy(dtype=float), rtol=0, atol=1e-12)


@pytest.mark.parametrize("corruption", ["swapped_centroids", "reused_risk_label"])
def test_incorrect_profile_mapping_is_detected_instead_of_silently_reused(ahc, corruption):
    prepared, model = ahc
    members, profiles = model.villages.copy(deep=True), model.profiles.copy(deep=True)
    if corruption == "swapped_centroids":
        columns = FEATURES + ["risk_listrik", "risk_gas"]
        profiles.loc[profiles.klaster.isin([2, 3]), columns] = profiles.loc[profiles.klaster.isin([2, 3]), columns].iloc[::-1].to_numpy()
    else:
        members.loc[members.klaster.eq(3), "interpretasi"] = "Dominan Bahaya Gas"
    with pytest.raises(ValueError, match="Centroid AHC|Kategori AHC"):
        ahc_profile_details(prepared, replace(model, villages=members, profiles=profiles))


def test_missing_model_members_are_detected(ahc):
    prepared, model = ahc
    with pytest.raises(ValueError, match="Anggota AHC"):
        ahc_profile_details(prepared, replace(model, villages=model.villages.iloc[1:]))
