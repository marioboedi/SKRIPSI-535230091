"""Consistent, accessible Vega charts and a coordinate-based map."""

from html import escape

import altair as alt
import numpy as np
import pandas as pd
import pydeck as pdk

from firewatch.analysis import FEATURES, FEATURE_LABELS, LOW_RISK_LABEL, RISK_COLORS, RISK_ORDER, cluster_membership_summary
from firewatch.evaluation_charts import metric_curve  # Backward-compatible public import.
from firewatch.geography import boundary_data
from firewatch.palette import cluster_color

SHORT_RISK = {
    "Dominan Bahaya Keduanya": "Listrik & gas",
    "Dominan Bahaya Kelistrikan": "Kelistrikan",
    "Dominan Bahaya Gas": "Gas",
    LOW_RISK_LABEL: LOW_RISK_LABEL,
}


def city_label(city: str) -> str:
    return city.replace("KOTA ADM ", "").replace("KAB ADM KEP SERIBU", "KEPULAUAN SERIBU").title()


def risk_scale(short: bool = False) -> alt.Scale:
    return alt.Scale(
        domain=[SHORT_RISK[v] if short else v for v in RISK_ORDER],
        range=[RISK_COLORS[v] for v in RISK_ORDER],
    )


def risk_distribution(villages: pd.DataFrame) -> pd.DataFrame:
    counts = villages.interpretasi.value_counts().reindex(RISK_ORDER, fill_value=0).rename_axis("interpretasi").reset_index(name="jumlah")
    counts["kategori"] = counts.interpretasi.map(SHORT_RISK)
    counts["warna"] = counts.interpretasi.map(RISK_COLORS)
    total = int(counts.jumlah.sum())
    counts["persentase"] = counts.jumlah / total if total else 0.0
    counts["urutan"] = range(len(counts))
    return counts


def risk_donut(villages: pd.DataFrame):
    counts = risk_distribution(villages)
    base = alt.Chart(counts).encode(
        theta=alt.Theta("jumlah:Q", stack=True),
        color=alt.Color("kategori:N", scale=risk_scale(True), legend=None),
        order=alt.Order("urutan:Q"),
        tooltip=[alt.Tooltip("interpretasi:N", title="Profil"), alt.Tooltip("jumlah:Q", title="Kelurahan"), alt.Tooltip("persentase:Q", title="Proporsi", format=".1%")],
    )
    return _donut(base, len(villages))


def cluster_distribution(villages: pd.DataFrame) -> pd.DataFrame:
    counts = cluster_membership_summary(villages)
    counts["kategori"] = counts.klaster.map(lambda k: f"Klaster {int(k)}")
    counts["warna"] = counts.klaster.map(cluster_color)
    return counts


def cluster_donut(counts: pd.DataFrame):
    """Render the shared model-label summary used by the chart and its legend."""
    tooltips = [alt.Tooltip("klaster:O", title="Klaster"), alt.Tooltip("jumlah:Q", title="Kelurahan"), alt.Tooltip("persentase:Q", title="Proporsi", format=".1%"), alt.Tooltip("interpretasi:N", title="Kategori risiko" if "profil_karakteristik" in counts else "Profil kerawanan")]
    if "profil_karakteristik" in counts:
        tooltips.extend([alt.Tooltip("profil_karakteristik:N", title="Karakteristik"), alt.Tooltip("risk_listrik:Q", title="Indeks listrik (Z)", format="+.3f"), alt.Tooltip("risk_gas:Q", title="Indeks gas (Z)", format="+.3f")])
    base = alt.Chart(counts).encode(
        theta=alt.Theta("jumlah:Q", stack=True),
        color=alt.Color("kategori:N", scale=alt.Scale(domain=counts.kategori.tolist(), range=counts.warna.tolist()), legend=None),
        detail=alt.Detail("klaster:O"),
        order=alt.Order("klaster:Q"),
        tooltip=tooltips,
    )
    return _donut(base, int(counts.jumlah.sum()))


def _donut(base: alt.Chart, total: int, height: int = 225):
    # Fixed gaps and rounded ends can erase a true 1/267 slice. Keep the exact
    # stacked angles and communicate small proportions in the external legend.
    ring = base.mark_arc(innerRadius=77, outerRadius=103, cornerRadius=0, padAngle=0, stroke="white", strokeWidth=.5)
    center = alt.Chart(pd.DataFrame({"value": [str(total)], "label": ["kelurahan"]}))
    number = center.mark_text(fontSize=34, fontWeight=700, color="#253342", dy=-8).encode(text="value:N")
    label = center.mark_text(fontSize=12, color="#78838E", dy=21).encode(text="label:N")
    return (ring + number + label).properties(height=height)


def city_distribution(villages: pd.DataFrame):
    data = villages.copy()
    data["wilayah"] = data.kota.map(city_label)
    data["profil"] = data.interpretasi.map(SHORT_RISK)
    counts = data.groupby(["wilayah", "profil"]).size().reset_index(name="jumlah")
    return alt.Chart(counts).mark_bar(cornerRadiusEnd=3, size=18).encode(
        x=alt.X("jumlah:Q", title="Jumlah kelurahan", axis=alt.Axis(tickMinStep=1, grid=True)),
        y=alt.Y("wilayah:N", title=None, sort="-x", axis=alt.Axis(labelLimit=160)),
        color=alt.Color("profil:N", title=None, scale=risk_scale(True), legend=alt.Legend(orient="bottom", columns=2)),
        tooltip=[alt.Tooltip("wilayah:N", title="Wilayah"), alt.Tooltip("profil:N", title="Profil"), alt.Tooltip("jumlah:Q", title="Kelurahan")],
    ).properties(height=255)


def centroid_heatmap(profiles: pd.DataFrame):
    data = profiles.melt(id_vars=["klaster"], value_vars=FEATURES, var_name="indikator", value_name="z_score")
    data["indikator"] = data.indikator.map(FEATURE_LABELS)
    data["klaster"] = "Klaster " + data.klaster.astype(str)
    return alt.Chart(data).mark_rect(cornerRadius=3, stroke="white", strokeWidth=3).encode(
        x=alt.X("indikator:N", title=None, sort=[FEATURE_LABELS[f] for f in FEATURES], axis=alt.Axis(labelAngle=-35, labelLimit=150)),
        y=alt.Y("klaster:N", title=None, sort=None),
        color=alt.Color("z_score:Q", title="Z-score", scale=alt.Scale(scheme="redblue", reverse=True, domainMid=0)),
        tooltip=[alt.Tooltip("klaster:N", title="Klaster"), alt.Tooltip("indikator:N", title="Indikator"), alt.Tooltip("z_score:Q", title="Z-score centroid", format=".3f")],
    ).properties(height=max(160, 35 * len(profiles)))


def density_chart(villages: pd.DataFrame):
    data = villages.copy()
    data["klaster"] = "Klaster " + data.klaster.astype(str)
    return alt.Chart(data).mark_boxplot(extent="min-max", size=23, color="#497B9D").encode(
        y=alt.Y("klaster:N", title=None, sort="ascending"),
        x=alt.X("kepadatan_penduduk:Q", title="Kepadatan penduduk (jiwa/km²)", axis=alt.Axis(format="~s")),
    ).properties(height=max(170, 37 * data.klaster.nunique()))


def indicator_comparison(row: pd.Series, baseline: pd.Series):
    data = pd.DataFrame({
        "indikator": [FEATURE_LABELS[f] for f in FEATURES] * 2,
        "nilai": [float(row[f]) for f in FEATURES] + [float(baseline[f]) for f in FEATURES],
        "cakupan": ["Kelurahan ini"] * 9 + ["Rata-rata seluruh kelurahan"] * 9,
    })
    return alt.Chart(data).mark_bar(cornerRadiusEnd=2).encode(
        y=alt.Y("indikator:N", title=None, sort=[FEATURE_LABELS[f] for f in FEATURES]),
        x=alt.X("nilai:Q", title="Persentase rata-rata antarperiode (%)"),
        yOffset="cakupan:N",
        color=alt.Color("cakupan:N", title=None, scale=alt.Scale(domain=["Kelurahan ini", "Rata-rata seluruh kelurahan"], range=["#C74535", "#C6D1DA"]), legend=alt.Legend(orient="bottom")),
        tooltip=[alt.Tooltip("indikator:N", title="Indikator"), alt.Tooltip("cakupan:N", title="Cakupan"), alt.Tooltip("nilai:Q", title="Persentase", format=".2f")],
    ).properties(height=300)


def village_map(villages: pd.DataFrame, height: int = 360, terrain: bool = False, detailed: bool = False, color_by: str = "interpretasi"):
    data = villages.copy()
    for column in ["kelurahan", "kecamatan", "kota", "interpretasi"]:
        data[column] = data[column].map(lambda value: escape(str(value)))
    if color_by == "klaster":
        colors = data.klaster.map(cluster_color)
    elif color_by == "interpretasi":
        colors = data.interpretasi.map(RISK_COLORS)
    else:
        raise ValueError("Warna peta harus berdasarkan klaster atau interpretasi kerawanan.")
    data["color"] = colors.map(lambda color: [int(color[i:i + 2], 16) for i in (1, 3, 5)] + [215])
    data["density_text"] = data.kepadatan_penduduk.map(lambda n: f"{n:,.0f}".replace(",", "."))
    data["listrik_text"] = data.risk_listrik.map(lambda n: f"{n:.2f}")
    data["gas_text"] = data.risk_gas.map(lambda n: f"{n:.2f}")
    data["position"] = list(zip(data.longitude, data.latitude, data.elevation if terrain else np.zeros(len(data))))
    if len(data) == 1:
        latitude, longitude, zoom = float(data.latitude.iloc[0]), float(data.longitude.iloc[0]), 12
    elif not (data.latitude.between(-6.45, -6.05) & data.longitude.between(106.65, 107.1)).any():
        latitude = float((data.latitude.min() + data.latitude.max()) / 2)
        longitude = float((data.longitude.min() + data.longitude.max()) / 2)
        lat_span = max(float(data.latitude.max() - data.latitude.min()), .0001)
        lon_span = max(float(data.longitude.max() - data.longitude.min()), .0001)
        # Keep a filtered extent outside the default mainland view visible,
        # including when Kepulauan Seribu is selected through the city filter.
        zoom = float(np.clip(min(
            np.log2(max(height - 80, 100) * 360 / (512 * lat_span)),
            np.log2(440 * 360 / (512 * lon_span)),
        ), 1, 12))
    else:
        latitude, longitude, zoom = -6.205, 106.835, 10.4
    layers = [pdk.Layer(
        "GeoJsonLayer", data=boundary_data("kota"), id="batas-kota",
        filled=True, stroked=True, get_fill_color=[204, 222, 211, 55],
        get_line_color=[54, 85, 93, 205], line_width_min_pixels=1.8,
        pickable=False,
    ), pdk.Layer(
        "GeoJsonLayer", data=boundary_data("kecamatan"), id="batas-kecamatan",
        filled=False, stroked=True, get_line_color=[89, 115, 119, 155],
        line_width_min_pixels=.8, pickable=False,
    )]
    if detailed:
        layers.append(pdk.Layer(
            "GeoJsonLayer", data=boundary_data("kelurahan"), id="batas-kelurahan",
            filled=False, stroked=True, get_line_color=[111, 130, 131, 125],
            line_width_min_pixels=.55, pickable=False,
        ))
    layers.extend([pdk.Layer(
        "GeoJsonLayer", data=boundary_data("provinsi"), id="batas-provinsi",
        filled=False, stroked=True, get_line_color=[35, 76, 81, 220],
        line_width_min_pixels=2.4, pickable=False,
    ), pdk.Layer(
        "TextLayer", data=boundary_data("labels"), id="nama-wilayah",
        get_position="position", get_text="name", get_size=12,
        get_color=[40, 65, 75, 230], get_outline_color=[255, 255, 255, 235],
        outline_width=3, font_weight="bold", pickable=False,
    )])
    layers.append(pdk.Layer(
        "ScatterplotLayer", data=data, id="kelurahan",
        get_position="position", get_fill_color="color", get_line_color=[255, 255, 255, 240],
        get_radius=125, radius_min_pixels=4, radius_max_pixels=13,
        pickable=True, stroked=True, line_width_min_pixels=1.2, auto_highlight=True,
        parameters={"depthTest": False},
    ))
    return pdk.Deck(
        layers=layers,
        initial_view_state=pdk.ViewState(latitude=latitude, longitude=longitude, zoom=zoom, pitch=35 if terrain else 0),
        map_style="https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json",
        map_provider="carto", height=height,
        tooltip={
            "html": "<b>{kelurahan}</b><br/>{kecamatan}<br/>{kota}<br/><br/>Klaster {klaster} · {interpretasi}<br/>Indeks listrik: {listrik_text} · Gas: {gas_text}<br/>Kepadatan: {density_text} jiwa/km²<br/>Elevasi: {elevation} m",
            "style": {"backgroundColor": "#253342", "color": "white", "fontSize": "12px", "borderRadius": "8px", "padding": "12px"},
        },
    )
