"""Spatially assign populated places and the four amenity classes
(clinics, schools, banks, police) to their district, using the admin2
boundary layer.

Clinics and police can be mapped as either a point node or a building
polygon in OSM (confirmed for clinics: 23 Umgungundlovu + 14 Ugu hospitals/
clinics exist only as polygons in the general POI export, missed entirely
by the points-only health facilities export). So for these two classes we
combine points + polygon centroids from both the dedicated export (where
one exists) and the general POI export, then deduplicate anything within
DEDUP_DISTANCE_M of another match, keeping one.

Run from the repo root:
    python src/assign_amenities.py
"""
from pathlib import Path

import geopandas as gpd
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
INTERIM = ROOT / "data" / "interim"
PROCESSED = ROOT / "data" / "processed"

GDB = RAW / "zaf_admin_boundaries.gdb"
DISTRICT_LAYER = "zaf_admin2"
CODE_COL = "adm2_pcode"
NAME_COL = "adm2_name"

# Metric CRS for South Africa, used only for the proximity-based dedup.
METRIC_CRS = "EPSG:2054"  # Hartebeesthoek94 / Lo29, meters
DEDUP_DISTANCE_M = 50

POI_POINTS_PATTERN = "hotosm_zaf_points_of_interest_points*"
POI_POLYGONS_PATTERN = "hotosm_zaf_points_of_interest_polygons*"


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


def load_districts() -> gpd.GeoDataFrame:
    gdf = gpd.read_file(GDB, layer=DISTRICT_LAYER)
    return gdf[[CODE_COL, NAME_COL, "geometry"]].rename(
        columns={CODE_COL: "admin2_code", NAME_COL: "boundary_name"})


def to_points(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Polygons become their centroid; points stay as-is."""
    gdf = gdf.copy()
    gdf["geometry"] = gdf.geometry.apply(
        lambda g: g.centroid if g.geom_type != "Point" else g)
    return gdf


def dedup_by_proximity(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Drop points within DEDUP_DISTANCE_M of an earlier point (keeps the
    first occurrence — dedicated-export rows are placed before general-POI
    rows by the caller, so a dedicated-export match wins)."""
    if gdf.empty:
        return gdf
    metric = gdf.to_crs(METRIC_CRS)
    keep = []
    kept_geoms = []
    for idx, geom in zip(metric.index, metric.geometry):
        if any(geom.distance(k) < DEDUP_DISTANCE_M for k in kept_geoms):
            continue
        keep.append(idx)
        kept_geoms.append(geom)
    return gdf.loc[keep]


def load_class(label: str, dedicated_pattern: str | None, tag_col: str,
                values: set, include_polygons: bool) -> gpd.GeoDataFrame:
    parts = []

    if dedicated_pattern is not None:
        path = find_geojson(dedicated_pattern)
        gdf = gpd.read_file(path)
        subset = gdf[gdf[tag_col].isin(values)]
        parts.append(to_points(subset))

    if include_polygons:
        poi_points = gpd.read_file(find_geojson(POI_POINTS_PATTERN))
        poi_points = poi_points[poi_points[tag_col].isin(values)]
        parts.append(to_points(poi_points))

        poi_poly = gpd.read_file(find_geojson(POI_POLYGONS_PATTERN))
        poi_poly = poi_poly[poi_poly[tag_col].isin(values)]
        parts.append(to_points(poi_poly))

    combined = pd.concat(parts, ignore_index=True)
    combined = gpd.GeoDataFrame(combined, geometry="geometry", crs=parts[0].crs)
    before = len(combined)
    combined = dedup_by_proximity(combined)
    print(f"{label}: {before} raw matches -> {len(combined)} after dedup")
    return combined


def assign_points(points: gpd.GeoDataFrame, districts: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    if points.crs != districts.crs:
        points = points.to_crs(districts.crs)
    return gpd.sjoin(points, districts[["admin2_code", "geometry"]],
                      how="left", predicate="within")


def main() -> None:
    districts = load_districts()
    print(f"Districts: {len(districts)}")

    places_path = find_geojson("hotosm_zaf_populated_places*")
    places = gpd.read_file(places_path)
    places_joined = assign_points(places, districts)
    print(f"\nPopulated places: {len(places)}, "
          f"unassigned: {places_joined['admin2_code'].isna().sum()}")
    place_counts = places_joined.groupby("admin2_code").size().rename("n_places")

    all_counts = [place_counts]

    classes = [
        ("clinic", "hotosm_zaf_health_facilities*", "amenity", {"clinic", "hospital"}, True),
        ("school", "hotosm_zaf_education_facilities*", "amenity", {"school"}, True),
        ("bank", "hotosm_zaf_financial_services*", "amenity", {"bank", "atm"}, True),
        ("police", None, "amenity", {"police"}, True),
    ]
    INTERIM.mkdir(parents=True, exist_ok=True)
    for label, pattern, tag_col, values, include_polygons in classes:
        gdf = load_class(label, pattern, tag_col, values, include_polygons)
        joined = assign_points(gdf, districts)
        print(f"  unassigned: {joined['admin2_code'].isna().sum()}")
        counts = joined.groupby("admin2_code").size().rename(f"n_{label}")
        all_counts.append(counts)

        # Save the deduplicated point locations for downstream use
        # (e.g. the settlement-to-nearest-amenity distance layer).
        keep_cols = [c for c in ["osm_id", "name", tag_col] if c in gdf.columns] + ["geometry"]
        gdf[keep_cols].to_file(INTERIM / f"{label}_points.geojson", driver="GeoJSON")

    result = districts[["admin2_code", "boundary_name"]].set_index("admin2_code")
    for counts in all_counts:
        result = result.join(counts)
    result = result.fillna(0)
    for col in result.columns:
        if col.startswith("n_"):
            result[col] = result[col].astype(int)

    print("\nDistrict amenity counts:")
    print(result.to_string())

    zero_cols = [c for c in result.columns if c.startswith("n_") and c != "n_places"]
    zero_amenity = result[(result[zero_cols] == 0).any(axis=1)]
    if len(zero_amenity):
        print(f"\nDistricts with ZERO of at least one amenity class ({len(zero_amenity)}):")
        print(zero_amenity.to_string())

    PROCESSED.mkdir(parents=True, exist_ok=True)
    out = PROCESSED / "district_amenity_counts.csv"
    result.to_csv(out)
    print(f"\nSaved to {out}")


if __name__ == "__main__":
    main()
