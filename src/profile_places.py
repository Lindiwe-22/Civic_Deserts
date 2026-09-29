"""Profile the HOT South Africa populated places export.

Run from the repo root:
    python src/profile_places.py
"""
from pathlib import Path

import geopandas as gpd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"


def main() -> None:
    matches = sorted(RAW.glob("hotosm_zaf_populated_places*"))
    if not matches:
        raise SystemExit(f"No populated places export in {RAW}")
    folder = matches[0]
    geojsons = sorted(folder.glob("*.geojson")) if folder.is_dir() else [folder]
    if not geojsons:
        raise SystemExit(f"No .geojson file inside {folder}")
    path = geojsons[0]

    gdf = gpd.read_file(path)
    print(f"{path.name}: {len(gdf):,} features, CRS = {gdf.crs}")
    print("Columns:", list(gdf.columns))
    print("\nGeometry types:")
    print(gdf.geom_type.value_counts().to_string())

    place_col = next((c for c in gdf.columns if c.lower() == "place"), None)
    name_col = next((c for c in gdf.columns if c.lower() == "name"), None)
    pop_col = next((c for c in gdf.columns if c.lower() == "population"), None)

    if place_col:
        print(f"\nCounts by {place_col}:")
        print(gdf[place_col].value_counts(dropna=False).to_string())
    if name_col:
        n_named = gdf[name_col].notna().sum()
        print(f"\n{name_col} filled: {n_named:,} / {len(gdf):,} ({n_named / len(gdf):.0%})")
    if pop_col:
        n_pop = gdf[pop_col].notna().sum()
        print(f"{pop_col} filled: {n_pop:,} / {len(gdf):,} ({n_pop / len(gdf):.0%})")
    else:
        print("\nNo population column found.")

    name_lang_cols = [c for c in gdf.columns if c.lower().startswith("name:")]
    if name_lang_cols:
        print("\nName-language columns present:", name_lang_cols)
        for c in name_lang_cols:
            n = gdf[c].notna().sum()
            if n:
                print(f"  {c}: {n:,} filled")

    print("\nSample rows:")
    show_cols = [c for c in [place_col, name_col, pop_col] if c]
    print(gdf[show_cols].head(5).to_string(index=False))


if __name__ == "__main__":
    main()
