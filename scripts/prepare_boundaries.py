"""Build lightweight map assets from the public DPMPTSP Jakarta boundaries.

Run once with --download to refresh the public source. The app uses only the
bundled assets, so no boundary-service request is made for a user's dataset.
"""

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

from shapely import make_valid, union_all
from shapely.geometry import mapping, shape

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "https://gis-dpmptsp.jakarta.go.id/arcgis/rest/services/Hosted/Batas_Administrasi_Kelurahan_DKI_Jakarta/FeatureServer/85"
FIELDS = {"kelurahan": "wadmkd", "kecamatan": "wadmkc", "kota": "wadmkk"}


def rounded(value):
    if isinstance(value, float):
        return round(value, 6)
    if isinstance(value, (list, tuple)):
        return [rounded(v) for v in value]
    if isinstance(value, dict):
        return {k: rounded(v) for k, v in value.items()}
    return value


def feature(geometry, properties):
    return {"type": "Feature", "properties": properties, "geometry": rounded(mapping(geometry))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true")
    args = parser.parse_args()
    source_path = ROOT / ".runtime" / "jakarta_boundaries_source.geojson"
    if args.download:
        params = {"where": "1=1", "outFields": "wadmkd,wadmkc,wadmkk,kdepum,kdcpum,kdpkab", "outSR": 4326, "f": "geojson", "returnGeometry": "true"}
        with urlopen(SOURCE + "/query?" + urlencode(params), timeout=90) as response:
            contents = response.read()
        source_path.parent.mkdir(exist_ok=True)
        source_path.write_bytes(contents)
    source = json.loads(source_path.read_bytes())
    if source.get("error") or source.get("exceededTransferLimit"):
        raise ValueError("Boundary source returned an error or incomplete features.")
    villages, groups, labels = [], {"kota": defaultdict(list), "kecamatan": defaultdict(list)}, []
    for record in source["features"]:
        props = {target: str(record["properties"][field]).strip() for target, field in FIELDS.items()}
        geometry = make_valid(shape(record["geometry"]))
        villages.append(feature(geometry.simplify(.00006, preserve_topology=True), props))
        groups["kota"][(props["kota"],)].append(geometry)
        groups["kecamatan"][(props["kota"], props["kecamatan"])].append(geometry)
    assets = ROOT / "assets" / "boundaries"
    assets.mkdir(parents=True, exist_ok=True)
    collections = {"kelurahan": villages}
    for level, grouped in groups.items():
        collections[level] = []
        for keys, geometries in sorted(grouped.items()):
            merged = union_all(geometries)
            props = dict(zip(["kota", "kecamatan"], keys))
            collections[level].append(feature(merged.simplify(.00008, preserve_topology=True), props))
            if level == "kota":
                # A point on the largest land polygon avoids placing island labels at sea.
                land = max(merged.geoms, key=lambda p: p.area) if merged.geom_type == "MultiPolygon" else merged
                point = land.representative_point()
                name = keys[0].replace("KAB.ADM.KEP.SERIBU", "KEPULAUAN SERIBU").title()
                labels.append({"name": name.replace(" ", "\n", 1), "position": [round(point.x, 6), round(point.y, 6)]})
    province = union_all([shape(v["geometry"]) for v in collections["kota"]])
    collections["provinsi"] = [feature(province, {"provinsi": "DKI Jakarta"})]
    for level, features in collections.items():
        (assets / f"{level}.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": features}, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    (assets / "labels.json").write_text(json.dumps(labels, ensure_ascii=False), encoding="utf-8")
    metadata = {"publisher": "DPMPTSP Provinsi DKI Jakarta", "source": SOURCE, "retrieved_at_utc": datetime.now(timezone.utc).isoformat(), "crs": "EPSG:4326", "counts": {level: len(rows) for level, rows in collections.items()}, "simplification_degrees": {"kelurahan": .00006, "kecamatan": .00008, "kota": .00008}, "note": "Batas untuk visualisasi, disederhanakan dengan menjaga topologi; bukan penetapan batas hukum. Kota dan kecamatan dihasilkan dengan union batas kelurahan."}
    (assets / "source.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"counts": metadata["counts"], "asset_bytes": sum(p.stat().st_size for p in assets.iterdir())}))


if __name__ == "__main__":
    main()
