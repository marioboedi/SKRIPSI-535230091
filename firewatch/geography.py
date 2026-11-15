"""Local administrative boundaries, independent of the basemap connection."""

from functools import lru_cache
import json
from pathlib import Path

BOUNDARY_ROOT = Path(__file__).resolve().parents[1] / "assets" / "boundaries"
BOUNDARY_SOURCE = "https://gis-dpmptsp.jakarta.go.id/arcgis/rest/services/Hosted/Batas_Administrasi_Kelurahan_DKI_Jakarta/FeatureServer/85"


@lru_cache(maxsize=6)
def boundary_data(level: str):
    if level not in {"kelurahan", "kecamatan", "kota", "provinsi", "labels"}:
        raise ValueError("Unknown administrative boundary level")
    suffix = "json" if level == "labels" else "geojson"
    return json.loads((BOUNDARY_ROOT / f"{level}.{suffix}").read_text(encoding="utf-8"))
