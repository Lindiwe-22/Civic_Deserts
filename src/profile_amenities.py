"""Profile the HOT amenity layers (health, education, financial services)
and, if present, the general points-of-interest export.

Run from the repo root:
    python src/profile_amenities.py
"""
from pathlib import Path

import geopandas as gpd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"

LAYERS = {
    "health": "hotosm_zaf_health_facilities*",
    "education": "hotosm_zaf_education_facilities*",
    "financial": "hotosm_zaf_financial_services*",
    "points_of_interest (points)": "hotosm_zaf_points_of_interest_points*",
    "points_of_interest (polygons)": "hotosm_zaf_points_of_interest_polygons*",
}

AMENITY_COLS = ["amenity", "healthcare", "shop"]


def find_geojson(pattern: str) -> Path | None:
    matches = sorted(RAW.glob(pattern))
    if not matches:
        return None
    folder = matches[0]
    if folder.is_dir():
        geojsons = sorted(folder.glob("*.geojson"))
        return geojsons[0] if geojsons else None
    return folder if folder.suffix == ".geojson" else None


def main() -> None:
    for label, pattern in LAYERS.items():
        path = find_geojson(pattern)
        if path is None:
            print(f"\n=== {label} === NOT FOUND (pattern: {pattern})")
            continue
        gdf = gpd.read_file(path)
        print(f"\n=== {label} === {path.name}: {len(gdf):,} features, CRS = {gdf.crs}")
        for col in AMENITY_COLS:
            if col in gdf.columns and gdf[col].notna().any():
                print(f"\nCounts by {col}:")
                print(gdf[col].value_counts().head(15).to_string())
        name_col = next((c for c in gdf.columns if c.lower() == "name"), None)
        if name_col:
            n = gdf[name_col].notna().sum()
            print(f"\nname filled: {n:,} / {len(gdf):,} ({n / len(gdf):.0%})")


if __name__ == "__main__":
    main()
