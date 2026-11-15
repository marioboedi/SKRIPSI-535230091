"""Auditable AHC characteristics from the actual final cluster memberships."""

from dataclasses import replace

import numpy as np
import pandas as pd

from firewatch.analysis import ELECTRICITY, FEATURES, GAS, KEYS, ModelResult, PreparedData, risk_label

AHC_TAB_PROFILE_LABELS = {2: "Dominan Bahaya Keduanya"}


def ahc_tab_result(model: ModelResult) -> ModelResult:
    """Apply the requested AHC tab label without mutating cached model results."""
    if model.name != "AHC":
        return model
    villages, profiles = model.villages.copy(deep=True), model.profiles.copy(deep=True)
    for data in (villages, profiles):
        for cluster, label in AHC_TAB_PROFILE_LABELS.items():
            data.loc[data.klaster.eq(cluster), "interpretasi"] = label
    return replace(model, villages=villages, profiles=profiles)


def ahc_profile_details(prepared: PreparedData, model: ModelResult) -> pd.DataFrame:
    """Verify the centroid mapping and describe it without changing risk labels.

    Join by village identity, not row position or an assumed cluster numbering.
    Use the complete model memberships so filtering never changes a centroid.
    Z=0 is the annual reference mean; the existing risk cutoff remains 0.5.
    """
    if model.name != "AHC":
        raise ValueError("Pemeriksaan karakteristik ini khusus hasil AHC.")
    joined = prepared.standardized[KEYS + FEATURES].merge(
        model.villages[KEYS + ["klaster", "interpretasi", "risk_listrik", "risk_gas"]],
        on=KEYS, how="outer", validate="one_to_one", indicator=True, sort=False,
    )
    if not joined["_merge"].eq("both").all() or joined.klaster.isna().any():
        raise ValueError("Anggota AHC tidak cocok dengan data masukan model.")
    groups = joined.groupby("klaster", sort=True, observed=True)
    details = groups[FEATURES].mean()
    details["risk_listrik"] = details[ELECTRICITY].mean(axis=1)
    details["risk_gas"] = details[GAS].mean(axis=1)
    details["interpretasi"] = [risk_label(e, g) for e, g in zip(details.risk_listrik, details.risk_gas)]
    details["jumlah_kelurahan"] = groups.size()
    reference = model.profiles.set_index("klaster")
    if not reference.index.is_unique or set(details.index) != set(reference.index) or len(details) != model.k:
        raise ValueError("Nomor klaster AHC tidak cocok dengan profil model final.")
    reference = reference.loc[details.index]
    numeric = FEATURES + ["risk_listrik", "risk_gas"]
    if not np.allclose(details[numeric], reference[numeric], rtol=0, atol=1e-12):
        raise ValueError("Centroid AHC tidak sesuai dengan anggota klaster; periksa pemetaan profil.")
    if not details.interpretasi.eq(reference.interpretasi).all() or not details.jumlah_kelurahan.eq(reference.jumlah_kelurahan).all():
        raise ValueError("Kategori atau jumlah anggota AHC tidak sesuai dengan centroid model final.")
    for column in ["risk_listrik", "risk_gas"]:
        expected = joined.klaster.map(details[column])
        if not np.allclose(joined[column], expected, rtol=0, atol=1e-12):
            raise ValueError("Indeks AHC pada kelurahan tidak sesuai dengan nomor klasternya.")
    if not joined.interpretasi.eq(joined.klaster.map(details.interpretasi)).all():
        raise ValueError("Kategori AHC pada kelurahan tidak sesuai dengan nomor klasternya.")
    details["indikator_di_atas"] = details[FEATURES].gt(0).sum(axis=1)
    details["indikator_di_bawah"] = details[FEATURES].lt(0).sum(axis=1)
    details["indikator_setara"] = details[FEATURES].eq(0).sum(axis=1)
    total = len(FEATURES)

    def describe(row):
        parts = []
        for count, direction in [(row.indikator_di_atas, "di atas"), (row.indikator_di_bawah, "di bawah"), (row.indikator_setara, "setara dengan")]:
            if count:
                parts.append(f"{int(count)}/{total} centroid indikator {direction} rata-rata tahunan")
        return "; ".join(parts)

    details["profil_karakteristik"] = [describe(row) for row in details.itertuples()]
    details["persentase"] = details.jumlah_kelurahan / len(joined)
    return details.reset_index()
