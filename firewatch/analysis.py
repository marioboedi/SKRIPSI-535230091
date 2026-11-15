"""Reproducible research pipeline, independent from the dashboard UI.

Only the nine percentage indicators enter the models. Each year's observations
receive their own Z-scores BEFORE periods are averaged for each village.
"""

from __future__ import annotations

import csv
import io
import time
import warnings
from collections import Counter
from dataclasses import dataclass
from typing import Callable

import numpy as np
import pandas as pd
from sklearn.cluster import AgglomerativeClustering, KMeans
from sklearn.metrics import (
    calinski_harabasz_score,
    davies_bouldin_score,
    silhouette_score,
)
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

ELECTRICITY = ["steker_menumpuk", "steker_hangus", "stopkontak_kendur", "kabel_rusak"]
GAS = ["tabung_rusak", "selang_longgar", "regulator_rusak", "selang_tertindih", "kompor_berdekatan"]
FEATURES = ELECTRICITY + GAS
KEYS = ["kota", "kecamatan", "kelurahan"]
CONTEXT = ["kepadatan_penduduk", "latitude", "longitude", "elevation"]
REQUIRED = ["tahun", *KEYS, *FEATURES, *CONTEXT]
METHODS = ["K-Means", "AHC", "Spectral Bridges"]
LOW_RISK_LABEL = "Risiko Rendah"
RISK_LABEL_VERSION = "2"
RISK_ORDER = ["Dominan Bahaya Keduanya", "Dominan Bahaya Kelistrikan", "Dominan Bahaya Gas", LOW_RISK_LABEL]
RISK_COLORS = {
    "Dominan Bahaya Keduanya": "#B93642",
    "Dominan Bahaya Kelistrikan": "#EF7548",
    "Dominan Bahaya Gas": "#D9A536",
    LOW_RISK_LABEL: "#348B79",
}
FEATURE_LABELS = {
    "steker_menumpuk": "Steker menumpuk",
    "steker_hangus": "Steker hangus",
    "stopkontak_kendur": "Stopkontak kendur",
    "kabel_rusak": "Kabel rusak",
    "tabung_rusak": "Tabung rusak",
    "selang_longgar": "Selang longgar",
    "regulator_rusak": "Regulator rusak",
    "selang_tertindih": "Selang tertindih",
    "kompor_berdekatan": "Kompor berdekatan",
}
METRIC_DIRECTIONS = {"silhouette": False, "dbi": True, "chi": False}


class DatasetError(ValueError):
    """A dataset problem that can be explained directly to the user."""


@dataclass
class PreparedData:
    raw: pd.DataFrame
    villages: pd.DataFrame
    standardized: pd.DataFrame
    notes: list[str]

    @property
    def X(self) -> np.ndarray:
        return self.standardized[FEATURES].to_numpy(dtype=np.float64)


@dataclass
class ModelResult:
    name: str
    k: int
    metrics: dict[str, float]
    trials: pd.DataFrame
    villages: pd.DataFrame
    profiles: pd.DataFrame
    winners: dict[str, int]
    selection: str
    errors: list[str]
    seconds: float


@dataclass
class AnalysisResult:
    prepared: PreparedData
    models: dict[str, ModelResult]
    ranking: pd.DataFrame
    failures: dict[str, str]

    @property
    def best_name(self) -> str:
        return str(self.ranking.iloc[0]["algoritma"])


def read_dataset(contents: bytes) -> pd.DataFrame:
    if len(contents) > 20 * 1024 * 1024:
        raise DatasetError("Ukuran CSV maksimal 20 MB.")
    if not contents.strip():
        raise DatasetError("File CSV kosong. Pilih file yang berisi data.")
    try:
        text = contents.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = contents.decode("cp1252")
        except UnicodeDecodeError as exc:
            raise DatasetError("Simpan CSV dengan pengodean UTF-8, lalu unggah kembali.") from exc
    try:
        delimiter = csv.Sniffer().sniff(text[:8192], delimiters=",;\t").delimiter
    except csv.Error:
        delimiter = ","
    try:
        headers = next(csv.reader(io.StringIO(text), delimiter=delimiter))
        normalized = [str(h).strip().lower().replace(" ", "_") for h in headers]
        if len(set(normalized)) != len(normalized):
            raise DatasetError("Nama kolom berulang. Setiap kolom harus memiliki nama unik.")
        data = pd.read_csv(io.StringIO(text), sep=delimiter, decimal="," if delimiter == ";" else ".")
    except (pd.errors.ParserError, pd.errors.EmptyDataError, StopIteration) as exc:
        raise DatasetError("Struktur CSV tidak dapat dibaca. Periksa pemisah dan jumlah kolom setiap baris.") from exc
    data.columns = normalized
    return validate_dataset(data)


def validate_dataset(data: pd.DataFrame) -> pd.DataFrame:
    missing = [column for column in REQUIRED if column not in data.columns]
    if missing:
        raise DatasetError("Kolom wajib belum tersedia: " + ", ".join(missing) + ".")
    if data.empty:
        raise DatasetError("Dataset belum berisi baris data.")
    result = data.copy()
    for key in KEYS:
        if result[key].isna().any() or result[key].astype(str).str.strip().eq("").any():
            raise DatasetError(f"Kolom {key} tidak boleh kosong.")
        result[key] = result[key].astype(str).str.strip().str.upper()
    for column in ["tahun", *FEATURES, *CONTEXT]:
        result[column] = pd.to_numeric(result[column], errors="coerce")
        invalid = ~np.isfinite(result[column].to_numpy(dtype=float))
        if invalid.any():
            rows = ", ".join(str(int(n) + 2) for n in np.flatnonzero(invalid)[:5])
            raise DatasetError(f"Kolom {column} berisi nilai kosong / bukan angka pada baris CSV {rows}.")
    for column in FEATURES:
        if not result[column].between(0, 100).all():
            raise DatasetError(f"Persentase pada kolom {column} harus berada di antara 0 dan 100.")
    if not result["tahun"].between(1900, 2200).all() or (result["tahun"] % 1 != 0).any():
        raise DatasetError("Tahun harus berupa bilangan bulat antara 1900 dan 2200.")
    result["tahun"] = result["tahun"].astype(int)
    if (result["kepadatan_penduduk"] < 0).any():
        raise DatasetError("Kepadatan penduduk tidak boleh bernilai negatif.")
    if not result["latitude"].between(-90, 90).all() or not result["longitude"].between(-180, 180).all():
        raise DatasetError("Koordinat tidak valid: latitude −90 sampai 90, longitude −180 sampai 180.")
    if result.duplicated(["tahun", *KEYS]).any():
        raise DatasetError("Terdapat kelurahan dengan tahun yang sama lebih dari sekali. Hapus duplikat sebelum mengunggah.")
    if len(result[KEYS].drop_duplicates()) < 3:
        raise DatasetError("Diperlukan sedikitnya 3 kelurahan berbeda untuk mengevaluasi klaster.")
    return result.reset_index(drop=True)


def prepare_data(raw: pd.DataFrame) -> PreparedData:
    raw = validate_dataset(raw)
    scaled = raw[KEYS].copy()
    scaled[FEATURES] = 0.0
    notes: list[str] = []
    # Periods have different baselines. Pooling years into one scaler changes
    # the geometry and fails to reproduce the PROMPT 02 reference experiments.
    for year, observations in raw.groupby("tahun", sort=True):
        scaled.loc[observations.index, FEATURES] = StandardScaler().fit_transform(observations[FEATURES])
        constant = [FEATURE_LABELS[f] for f in FEATURES if observations[f].nunique() == 1]
        if constant:
            notes.append(f"Indikator konstan pada tahun {year} memiliki Z-score 0: " + ", ".join(constant) + ".")
    # Keep this canonical row order for reproducible seeded initialization.
    standardized = scaled.groupby(KEYS, sort=True, as_index=False)[FEATURES].mean()
    villages = raw.groupby(KEYS, sort=True, as_index=False)[FEATURES + CONTEXT].mean()
    coverage = raw.groupby(KEYS, sort=True).agg(
        jumlah_periode=("tahun", "nunique"),
        periode=("tahun", lambda years: ", ".join(str(y) for y in sorted(years.unique()))),
    ).reset_index()
    villages = villages.merge(coverage, on=KEYS, validate="one_to_one")
    periods = raw["tahun"].nunique()
    incomplete = int((villages["jumlah_periode"] < periods).sum())
    if incomplete:
        notes.append(f"{incomplete} kelurahan tidak memiliki seluruh {periods} periode. Rata-rata memakai periode yang tersedia.")
    if not (raw["latitude"].between(-6.5, -5.0) & raw["longitude"].between(106.2, 107.2)).all():
        notes.append("Sebagian koordinat berada di luar rentang umum DKI Jakarta. Periksa lokasi sebelum menafsirkan peta.")
    if len(villages) < 11:
        notes.append(f"Dataset kecil: pencarian K dibatasi hingga {len(villages) - 1} agar metrik dapat dihitung.")
    return PreparedData(raw, villages, standardized, notes)


def choose_k(trials: pd.DataFrame) -> tuple[int, dict[str, int], str]:
    """Majority vote; without a majority, lowest mean rank then silhouette/K."""
    if trials.empty:
        raise ValueError("Tidak ada kandidat K yang dapat dievaluasi.")
    ordered = trials.sort_values("k").copy()
    winners = {
        metric: int(ordered.sort_values([metric, "k"], ascending=[ascending, True]).iloc[0]["k"])
        for metric, ascending in METRIC_DIRECTIONS.items()
    }
    votes = Counter(winners.values())
    candidate, count = votes.most_common(1)[0]
    if count >= 2:
        return int(candidate), winners, f"K={candidate} didukung {count} dari 3 metrik evaluasi."
    ranks = pd.DataFrame({
        metric: ordered[metric].rank(method="min", ascending=ascending)
        for metric, ascending in METRIC_DIRECTIONS.items()
    })
    ordered["rata_rata_peringkat"] = ranks.mean(axis=1)
    best = ordered.sort_values(["rata_rata_peringkat", "silhouette", "k"], ascending=[True, False, True]).iloc[0]
    return int(best["k"]), winners, (
        "Ketiga metrik memilih K berbeda. Sistem memilih rata-rata peringkat terbaik; "
        "jika seri, Silhouette lebih tinggi lalu K lebih kecil menjadi pemutus."
    )


def risk_label(electricity: float, gas: float) -> str:
    if electricity > 0.5 and gas > 0.5:
        return "Dominan Bahaya Keduanya"
    if electricity > 0.5:
        return "Dominan Bahaya Kelistrikan"
    if gas > 0.5:
        return "Dominan Bahaya Gas"
    return LOW_RISK_LABEL


def density_label(value: float) -> str:
    # Descriptive app bands, not a statutory risk classification.
    if value > 20000:
        return "Sangat padat"
    if value > 10000:
        return "Padat"
    return "≤ 10.000 jiwa/km²"


def evaluate(X: np.ndarray, labels: np.ndarray) -> dict[str, float]:
    return {
        "silhouette": float(silhouette_score(X, labels)),
        "dbi": float(davies_bouldin_score(X, labels)),
        "chi": float(calinski_harabasz_score(X, labels)),
    }


def model_factory(name: str, k: int, X: np.ndarray):
    if name == "K-Means":
        return KMeans(n_clusters=k, random_state=11, n_init=10)
    if name == "AHC":
        return AgglomerativeClustering(n_clusters=k, linkage="ward")
    if name == "Spectral Bridges":
        if len(X) < 15 or len(np.unique(X, axis=0)) < 15:
            raise ValueError("Spectral Bridges memerlukan minimal 15 kelurahan dengan pola indikator berbeda untuk n_nodes=15.")
        import faiss
        from spectralbridges import SpectralBridges

        # The FAISS runtime may be loaded after threadpool_limits entered.
        # A single worker avoids nested OpenMP oversubscription on tiny data.
        faiss.omp_set_num_threads(1)
        return SpectralBridges(n_clusters=k, n_nodes=15, p=2, random_state=549)
    raise ValueError(f"Algoritma tidak dikenal: {name}")


def fit_labels(name: str, k: int, X: np.ndarray) -> np.ndarray:
    model = model_factory(name, k, X)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=UserWarning)
        if name == "Spectral Bridges":
            model.fit(X)
            labels = model.predict(X)
        else:
            labels = model.fit_predict(X)
    labels = np.asarray(labels, dtype=int)
    if len(np.unique(labels)) != k:
        raise ValueError(f"Hanya {len(np.unique(labels))} klaster terbentuk dari K={k} yang diminta.")
    return labels


def build_profiles(prepared: PreparedData, labels: np.ndarray) -> tuple[pd.DataFrame, pd.DataFrame]:
    standardized = prepared.standardized.copy()
    standardized["cluster_original"] = labels
    centroids = standardized.groupby("cluster_original")[FEATURES].mean()
    centroids["risk_listrik"] = centroids[ELECTRICITY].mean(axis=1)
    centroids["risk_gas"] = centroids[GAS].mean(axis=1)
    # Stable, readable numbering: highest joint centroid index first.
    centroids["indeks_gabungan"] = centroids[FEATURES].mean(axis=1)
    centroids = centroids.sort_values(["indeks_gabungan", "risk_listrik", "risk_gas"], ascending=False)
    mapping = {int(old): i + 1 for i, old in enumerate(centroids.index)}
    centroids["klaster"] = [mapping[int(old)] for old in centroids.index]
    centroids["interpretasi"] = [risk_label(e, g) for e, g in zip(centroids.risk_listrik, centroids.risk_gas)]
    villages = prepared.villages.copy()
    villages["klaster"] = [mapping[int(label)] for label in labels]
    villages = villages.merge(
        centroids[["klaster", "risk_listrik", "risk_gas", "indeks_gabungan", "interpretasi"]],
        on="klaster", how="left", validate="many_to_one", sort=False,
    )
    villages["profil_kepadatan"] = villages.kepadatan_penduduk.map(density_label)
    profiles = centroids.reset_index(drop=True)
    context = villages.groupby("klaster", as_index=False).agg(
        jumlah_kelurahan=("kelurahan", "size"),
        kepadatan_penduduk=("kepadatan_penduduk", "mean"),
    )
    profiles = profiles.merge(context, on="klaster", validate="one_to_one")
    return villages, profiles


def cluster_membership_summary(villages: pd.DataFrame) -> pd.DataFrame:
    """Summarize final model labels without merging equal risk interpretations.

    The integrated chart and its legend consume these same membership counts.
    Interpretations were joined from the final centroids by build_profiles; they
    are attributes of a cluster, never the key used to identify clusters here.
    """
    if villages[["klaster", "interpretasi"]].isna().any().any():
        raise ValueError("Hasil klaster dan interpretasi harus tersedia untuk setiap kelurahan.")
    groups = villages.groupby("klaster", sort=True, observed=True)
    if groups.interpretasi.nunique().gt(1).any():
        raise ValueError("Satu klaster harus memiliki satu interpretasi dari centroid model final.")
    summary = groups.agg(jumlah=("kelurahan", "size"), interpretasi=("interpretasi", "first")).reset_index()
    summary["persentase"] = summary.jumlah / len(villages) if len(villages) else 0.0
    return summary


def run_method(name: str, prepared: PreparedData) -> ModelResult:
    X = prepared.X
    trials, errors = [], []
    started = time.perf_counter()
    with threadpool_limits(limits=1):
        for k in range(2, min(10, len(X) - 1) + 1):
            start = time.perf_counter()
            try:
                labels = fit_labels(name, k, X)
                metrics = evaluate(X, labels)
                if not all(np.isfinite(list(metrics.values()))):
                    raise ValueError("Metrik evaluasi tidak terdefinisi.")
                trials.append({"k": k, **metrics, "waktu_detik": time.perf_counter() - start})
            except Exception as exc:
                errors.append(f"K={k}: {exc}")
        if not trials:
            raise ValueError(errors[0] if errors else "Seluruh kandidat K gagal.")
        trials_df = pd.DataFrame(trials)
        k, winners, selection = choose_k(trials_df)
        labels = fit_labels(name, k, X)
        metrics = evaluate(X, labels)
    villages, profiles = build_profiles(prepared, labels)
    return ModelResult(name, k, metrics, trials_df, villages, profiles, winners, selection, errors, time.perf_counter() - started)


def rank_models(models: dict[str, ModelResult]) -> pd.DataFrame:
    comparison = pd.DataFrame([
        {"algoritma": name, "k": model.k, **model.metrics}
        for name, model in models.items()
    ])
    for metric, ascending in METRIC_DIRECTIONS.items():
        comparison[f"peringkat_{metric}"] = comparison[metric].rank(method="min", ascending=ascending)
    comparison["rata_rata_peringkat"] = comparison[[f"peringkat_{m}" for m in METRIC_DIRECTIONS]].mean(axis=1)
    return comparison.sort_values(
        ["rata_rata_peringkat", "silhouette", "algoritma"], ascending=[True, False, True]
    ).reset_index(drop=True)


def run_analysis(raw: pd.DataFrame, progress: Callable[[str], None] | None = None) -> AnalysisResult:
    prepared = prepare_data(raw)
    if len(np.unique(prepared.X, axis=0)) < 2:
        raise DatasetError("Semua kelurahan memiliki pola indikator yang sama. Klaster tidak dapat dibentuk.")
    models, failures = {}, {}
    for name in METHODS:
        if progress:
            progress(name)
        try:
            models[name] = run_method(name, prepared)
        except Exception as exc:
            failures[name] = str(exc)
    if not models:
        raise DatasetError("Tidak ada model yang berhasil: " + " | ".join(f"{n}: {e}" for n, e in failures.items()))
    return AnalysisResult(prepared, models, rank_models(models), failures)
