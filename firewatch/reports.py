"""CSV and ZIP report serialization; no page rendering or model fitting."""

import io
import json
import zipfile
from hashlib import sha256
from importlib.metadata import version

import pandas as pd
import streamlit as st

from firewatch.analysis import FEATURES, LOW_RISK_LABEL, RISK_LABEL_VERSION, AnalysisResult
from firewatch.profiles import AHC_TAB_PROFILE_LABELS, ahc_tab_result
from firewatch.state import APP_VERSION, PIPELINE_VERSION


def csv_bytes(data: pd.DataFrame) -> bytes:
    """Encode a table for Excel-compatible CSV without changing its values."""
    return data.to_csv(index=False).encode("utf-8-sig")


def report_zip(result: AnalysisResult, *, ahc_tab: bool = False) -> bytes:
    """Export all successful models, preserving the existing archive schema."""
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("perbandingan_algoritma.csv", csv_bytes(result.ranking))
        archive.writestr("data_agregasi.csv", csv_bytes(result.prepared.villages))
        archive.writestr("z_score_agregasi.csv", csv_bytes(result.prepared.standardized))
        metadata = {
            "dataset": st.session_state.dataset_name,
            "source_sha256": sha256(st.session_state.dataset_bytes).hexdigest(),
            "pipeline_version": PIPELINE_VERSION,
            "label_version": RISK_LABEL_VERSION,
            "app_version": APP_VERSION,
            "library_versions": {
                name: version(name)
                for name in [
                    "numpy", "pandas", "scipy", "scikit-learn", "spectral-bridges",
                    "faiss-cpu", "streamlit", "altair", "pydeck", "pyarrow",
                    "threadpoolctl", "matplotlib", "seaborn", "shapely",
                ]
            },
            "jumlah_observasi": len(result.prepared.raw),
            "jumlah_kelurahan": len(result.prepared.villages),
            "indikator_model": FEATURES,
            "praproses": (
                "Z-score setiap indikator dihitung terpisah per tahun (ddof=0), "
                "lalu rata-rata antarperiode per kota/kecamatan/kelurahan. "
                "Urutan baris agregasi diurutkan berdasarkan kota, kecamatan, kelurahan. "
                "Kepadatan dan koordinat tidak masuk model."
            ),
            "parameter": {
                "K-Means": {"random_state": 11, "n_init": 10},
                "AHC": {"linkage": "ward"},
                "Spectral Bridges": {"random_state": 549, "n_nodes": 15, "p": 2},
            },
            "pemilihan_k": "Mayoritas tiga metrik; jika semua berbeda, rata-rata peringkat, lalu Silhouette, lalu K terkecil.",
            "peringkat_algoritma": "Rata-rata peringkat tiga metrik, lalu Silhouette tertinggi dan nama algoritma untuk hasil seri.",
            "algoritma_teratas": result.best_name,
            "peringatan": result.prepared.notes,
            "algoritma_gagal": result.failures,
            "label_risiko_rendah": {
                "nama": LOW_RISK_LABEL,
                "keterangan": "Relatif terhadap indikator dataset; bukan kepastian bebas kebakaran atau prediksi kejadian.",
            },
            "models": {},
        }
        if ahc_tab:
            metadata["label_tampilan_ahc"] = {
                f"klaster_{cluster}": label
                for cluster, label in AHC_TAB_PROFILE_LABELS.items()
            }
        for name, model in result.models.items():
            if ahc_tab:
                model = ahc_tab_result(model)
            slug = name.lower().replace(" ", "_").replace("-", "_")
            archive.writestr(f"{slug}/hasil_kelurahan.csv", csv_bytes(model.villages))
            archive.writestr(f"{slug}/profil_klaster.csv", csv_bytes(model.profiles))
            archive.writestr(f"{slug}/pencarian_k.csv", csv_bytes(model.trials))
            metadata["models"][name] = {
                "k": model.k,
                "metrics": model.metrics,
                "metric_winners": model.winners,
                "selection": model.selection,
                "candidate_errors": model.errors,
            }
        archive.writestr("metodologi.json", json.dumps(metadata, ensure_ascii=False, indent=2))
    return output.getvalue()
