"""Shared, session-local dataset and bounded computation caches."""

from hashlib import sha256
from pathlib import Path

import streamlit as st

from firewatch.analysis import AnalysisResult, RISK_LABEL_VERSION, read_dataset, run_analysis

ROOT = Path(__file__).resolve().parents[1]
DRIVE_URL = "https://drive.google.com/uc?export=download&id=12J4vocfVVSWSYdBPMfmMsRDMEY1lKooD"
PIPELINE_VERSION = "1.1.0"
APP_VERSION = "1.3.1"


def initialize_state() -> None:
    if "dataset_bytes" not in st.session_state:
        st.session_state.dataset_bytes = (ROOT / "2425.csv").read_bytes()
        st.session_state.dataset_name = "2425.csv"
    st.session_state.setdefault("upload_nonce", 0)
    st.session_state.setdefault("last_upload", None)
    st.session_state.setdefault("upload_error", None)


@st.cache_data(show_spinner=False, max_entries=8, ttl=3600)
def parsed_data(contents: bytes):
    return read_dataset(contents)


@st.cache_data(show_spinner=False, max_entries=8, ttl=3600)
def cached_analysis(contents: bytes, pipeline_version: str = PIPELINE_VERSION, label_version: str = RISK_LABEL_VERSION) -> AnalysisResult:
    # Label vocabulary is cached with the results, separately from the unchanged
    # numerical pipeline version, so an older cached label cannot reappear.
    return run_analysis(read_dataset(contents))


def active_data():
    return parsed_data(st.session_state.dataset_bytes)


def dataset_key() -> str:
    return sha256(st.session_state.dataset_bytes).hexdigest()[:12]


def activate_dataset(contents: bytes, filename: str) -> None:
    # Commit only after full validation; an invalid upload preserves active data.
    parsed_data(contents)
    st.session_state.dataset_bytes = contents
    st.session_state.dataset_name = filename
    st.session_state.upload_error = None


def reset_dataset() -> None:
    activate_dataset((ROOT / "2425.csv").read_bytes(), "2425.csv")
    st.session_state.upload_nonce += 1
    st.session_state.last_upload = None


def active_analysis() -> AnalysisResult:
    with st.spinner("Menyiapkan hasil tiga metode klasterisasi…", show_time=True):
        return cached_analysis(st.session_state.dataset_bytes, PIPELINE_VERSION, RISK_LABEL_VERSION)


@st.cache_data(show_spinner=False, max_entries=24, ttl=3600)
def cached_figure(kind: str, villages, standardized=None, feature: str = "steker_menumpuk") -> bytes:
    from firewatch.eda import render_figure

    return render_figure(kind, villages, standardized, feature)
