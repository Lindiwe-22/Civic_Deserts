"""For each populated place, find the distance to its nearest amenity of
each class (clinic, school, bank, police), independent of district-level
population weighting. Surfaces within-district gaps a district average
can't see — e.g. a settlement far from amenities that are clustered near
the district's urban core.

Requires the per-class point files in data/interim/, produced by
assign_amenities.py.

Run from the repo root:
    python src/compute_settlement_distances.py
"""
from pathlib import Path

import geopandas as gpd
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
INTERIM = ROOT / "data" / "interim"
PROCESSED = ROOT / "data" / "processed"

METRIC_CRS = "EPSG:2054"  # Hartebeesthoek94 / Lo29, meters
CLASSES = ["clinic", "school", "bank", "police"]


def find_geojson(pattern: str) -> Path:
    matches = sorted(RAW.glob(pattern))
    if not matches:
        raise SystemExit(f"No file matching {pattern} in {RAW}")
    folder = matches[0]
    if folder.is_dir():
        geojsons = sorted(folder.glob("*.geojson"))
        if not geojsons:
            raise SystemExit(f"No .geojson inside {folder}")
        return geojsons[0]
    return folder


def main() -> None:
    places_path = find_geojson("hotosm_zaf_populated_places*")
    places = gpd.read_file(places_path)

    # Exclude Marion Island / Prince Edward Islands: a South African
    # sub-Antarctic research territory (~1,770-2,170 km SE of Cape Town),
    # staffed by ~10-12 researchers, no civilian population. Including it
    # distorts every distance statistic without representing a real
    # "civic desert" in the sense this analysis measures.
    name_col_pre = next((c for c in places.columns if c.lower() == "name"), None)
    if name_col_pre:
        before = len(places)
        places = places[~places[name_col_pre].isin(["Marion Base"])]
        excluded = before - len(places)
        if excluded:
            print(f"Excluded {excluded} place(s) on Marion/Prince Edward Islands "
                  f"(sub-Antarctic research territory, no civilian population)")

    places = places.to_crs(METRIC_CRS)
    places = places.reset_index(drop=True)
    places["place_id"] = places.index

    name_col = next((c for c in places.columns if c.lower() == "name"), None)
    place_col = next((c for c in places.columns if c.lower() == "place"), None)
    keep = ["place_id"] + [c for c in [name_col, place_col] if c] + ["geometry"]
    result = places[keep].copy()
    if name_col and name_col != "name":
        result = result.rename(columns={name_col: "name"})
    if place_col and place_col != "place":
        result = result.rename(columns={place_col: "place"})

    for label in CLASSES:
        path = INTERIM / f"{label}_points.geojson"
        if not path.exists():
            raise SystemExit(f"{path} not found — run assign_amenities.py first")
        amenity = gpd.read_file(path).to_crs(METRIC_CRS)

        nearest = gpd.sjoin_nearest(
            places[["place_id", "geometry"]], amenity[["geometry"]],
            distance_col=f"dist_{label}_m")
        # A place can tie with multiple equally-near amenities; keep one.
        nearest = nearest.drop_duplicates(subset="place_id")
        result = result.merge(
            nearest[["place_id", f"dist_{label}_m"]], on="place_id", how="left")
        result[f"dist_{label}_m"] = result[f"dist_{label}_m"].round(0)
        print(f"{label}: median distance {result[f'dist_{label}_m'].median():,.0f} m, "
              f"max {result[f'dist_{label}_m'].max():,.0f} m")

    result_wgs84 = result.to_crs(4326)
    result_wgs84["lon"] = result_wgs84.geometry.x
    result_wgs84["lat"] = result_wgs84.geometry.y

    out_cols = ["place_id", "name", "place", "lon", "lat"] + [f"dist_{c}_m" for c in CLASSES]
    out_cols = [c for c in out_cols if c in result_wgs84.columns]
    out_df = pd.DataFrame(result_wgs84[out_cols])

    PROCESSED.mkdir(parents=True, exist_ok=True)
    out_path = PROCESSED / "settlement_distances.csv"
    out_df.to_csv(out_path, index=False)
    print(f"\nSaved {len(out_df)} settlements to {out_path}")

    print("\nFurthest-from-any-amenity settlements (max of the four distances):")
    out_df["max_dist_m"] = out_df[[f"dist_{c}_m" for c in CLASSES]].max(axis=1)
    worst = out_df.nlargest(10, "max_dist_m")
    display_cols = [c for c in ["name", "place"] if c in worst.columns] + \
                    [f"dist_{c}_m" for c in CLASSES]
    print(worst[display_cols].to_string(index=False))


if __name__ == "__main__":
    main()
