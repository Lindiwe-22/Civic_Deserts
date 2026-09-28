"""Check that HAPI South Africa admin2 codes match the admin2 boundary layer.

Run from the repo root:
    python src/check_join.py
"""
from pathlib import Path

import geopandas as gpd
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
GDB = RAW / "zaf_admin_boundaries.gdb"
LAYER = "zaf_admin2"
HAPI = RAW / "hdx_hapi_population_global_non_hrp.csv"


def find_col(cols, *needles):
    for c in cols:
        if all(n in c.lower() for n in needles):
            return c
    return None


def main() -> None:
    gdf = gpd.read_file(GDB, layer=LAYER)
    print(f"Layer {LAYER}: {len(gdf)} features, CRS = {gdf.crs}")
    print("Columns:", [c for c in gdf.columns if c != "geometry"])

    code_col = find_col(gdf.columns, "adm2", "pcode") or find_col(gdf.columns, "pcode")
    name_col = find_col(gdf.columns, "adm2", "en") or find_col(gdf.columns, "name")
    if code_col is None:
        raise SystemExit("\nNo p-code column found. Send me the column list above.")
    print(f"\nUsing code column: {code_col}, name column: {name_col}")

    hapi = pd.read_csv(HAPI, dtype=str, low_memory=False)
    hapi = hapi[hapi["location_code"] == "ZAF"]
    hapi = hapi[hapi["admin_level"] == "2"]
    h = hapi[["admin2_code", "admin2_name"]].drop_duplicates()

    g_codes = set(gdf[code_col].astype(str))
    h_codes = set(h["admin2_code"])
    both = g_codes & h_codes
    print(f"\nHAPI admin2 codes: {len(h_codes)}, boundary codes: {len(g_codes)}, matched: {len(both)}")

    only_h = h[~h["admin2_code"].isin(g_codes)]
    if len(only_h):
        print("\nIn HAPI but not in boundaries:")
        print(only_h.to_string(index=False))
    only_g = gdf[~gdf[code_col].astype(str).isin(h_codes)]
    if len(only_g):
        cols = [code_col] + ([name_col] if name_col else [])
        print("\nIn boundaries but not in HAPI:")
        print(only_g[cols].to_string(index=False))
    if len(both) == len(h_codes) == len(g_codes):
        print("\nAll codes match one-to-one.")


if __name__ == "__main__":
    main()
