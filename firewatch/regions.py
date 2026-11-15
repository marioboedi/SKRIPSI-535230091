"""Dataset-derived, unambiguous region suggestions and literal free-text search."""

import pandas as pd

from firewatch.analysis import KEYS


def region_options(data: pd.DataFrame) -> dict[str, dict[str, str]]:
    regions = data[KEYS].drop_duplicates().sort_values(KEYS)
    choices = {}
    for city, district, village in regions.itertuples(index=False, name=None):
        city_name = city.replace("KOTA ADM ", "").replace("KAB ADM KEP SERIBU", "KEPULAUAN SERIBU").title()
        choices[f"Kelurahan {village.title()} · {district.title()} · {city_name}"] = dict(zip(KEYS, [city, district, village]))
        choices[f"Kecamatan {district.title()} · {city_name}"] = {"kota": city, "kecamatan": district}
    return dict(sorted(choices.items()))


def filter_region(data: pd.DataFrame, query: str | None, options: dict[str, dict[str, str]]) -> pd.DataFrame:
    if not query or not query.strip():
        return data.copy()
    query = query.strip()
    selection = options.get(query)
    if selection is not None:
        mask = pd.Series(True, index=data.index)
        for column, value in selection.items():
            mask &= data[column].eq(value)
    else:
        needle = query.casefold()
        mask = data.kelurahan.str.casefold().str.contains(needle, regex=False) | data.kecamatan.str.casefold().str.contains(needle, regex=False)
    return data.loc[mask].copy()
