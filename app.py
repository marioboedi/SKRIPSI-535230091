"""Run with: python -m streamlit run app.py."""

import streamlit as st

from firewatch.analysis import DatasetError
from firewatch.state import APP_VERSION, ROOT, active_data, initialize_state
from firewatch.ui import footer, number

st.set_page_config(
    page_title="Jakarta Siaga · Kerawanan kebakaran",
    page_icon=str(ROOT / "assets" / "mark.svg"),
    layout="wide",
    initial_sidebar_state="expanded",
)
initialize_state()
st.logo(str(ROOT / "assets" / "logo.svg"), icon_image=str(ROOT / "assets" / "mark.svg"), size="large")

page = st.navigation(
    {
        "DASHBOARD": [
            st.Page("app_pages/beranda.py", title="Beranda", icon=":material/grid_view:", default=True),
            st.Page("app_pages/dataset.py", title="Dataset", icon=":material/database:", url_path="dataset"),
            st.Page("app_pages/klasterisasi.py", title="Klasterisasi", icon=":material/hub:", url_path="klasterisasi"),
        ],
        "INFORMASI": [
            st.Page("app_pages/faq.py", title="FAQ", icon=":material/help:", url_path="faq"),
            st.Page("app_pages/tentang.py", title="Tentang aplikasi", icon=":material/info:", url_path="tentang"),
        ],
    },
    position="sidebar",
    expanded=True,
)

with st.sidebar:
    with st.container(border=True):
        st.caption("DATASET AKTIF")
        st.markdown(f"**:material/description: {st.session_state.dataset_name}**")
        try:
            raw = active_data()
            st.caption(f"{number(len(raw))} observasi · {raw.tahun.nunique()} periode\n\n{number(len(raw[['kota', 'kecamatan', 'kelurahan']].drop_duplicates()))} kelurahan")
            st.badge("Siap dianalisis", color="green", icon=":material/check_circle:")
        except DatasetError as exc:
            st.error(str(exc))
    st.caption("Dikembangkan untuk penelitian\n\n**Teknik Informatika · UNTAR**")
    st.caption(f"Versi {APP_VERSION} · Mitigasi berbasis data")

try:
    page.run()
except DatasetError as exc:
    st.error(str(exc), icon=":material/error:", title="Dataset belum dapat dianalisis")
    st.page_link("app_pages/dataset.py", label="Periksa atau ganti dataset", icon=":material/database:")
footer()
