"""Compare HAPI's 2020 district population (baseline) against Stats SA's
2022 Census district population, as a validation check.

Run from the repo root:
    python src/compare_population.py
"""
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
INTERIM = ROOT / "data" / "interim"


def normalize(name: str) -> str:
    """Join key: lowercase, alphanumeric only, no spaces at all — so
    spacing differences between sources (e.g. "O.R.Tambo" vs "O.R. Tambo")
    don't block a match."""
    name = name.lower()
    return re.sub(r"[^a-z0-9]", "", name)


def load_hapi() -> pd.DataFrame:
    path = RAW / "hdx_hapi_population_global_non_hrp.csv"
    df = pd.read_csv(path, dtype=str, low_memory=False)
    df = df[(df["location_code"] == "ZAF") & (df["admin_level"] == "2")]
    df = df[(df["gender"] == "all") & (df["age_range"] == "all")]
    df = df[["admin2_code", "admin2_name"]].copy()
    df["population_2020"] = pd.to_numeric(
        pd.read_csv(path, dtype=str, low_memory=False)
        .loc[df.index, "population"]
    )
    df["key"] = df["admin2_name"].map(normalize)
    return df


def load_stats_sa() -> pd.DataFrame:
    path = INTERIM / "census2022_population_parsed.csv"
    df = pd.read_csv(path)
    df = df[df["level"] == "district_or_metro"].copy()
    df["key"] = df["name"].map(normalize)
    return df[["name", "population_2022", "key"]]


def main() -> None:
    hapi = load_hapi()
    sa = load_stats_sa()

    merged = hapi.merge(sa, on="key", how="outer", indicator=True)
    matched = merged[merged["_merge"] == "both"].copy()
    only_hapi = merged[merged["_merge"] == "left_only"]
    only_sa = merged[merged["_merge"] == "right_only"]

    print(f"HAPI districts: {len(hapi)}, Stats SA districts: {len(sa)}, matched: {len(matched)}")
    if len(only_hapi):
        print("\nIn HAPI but unmatched:")
        print(only_hapi[["admin2_code", "admin2_name"]].to_string(index=False))
    if len(only_sa):
        print("\nIn Stats SA but unmatched:")
        print(only_sa[["name"]].to_string(index=False))

    matched["change"] = matched["population_2022"] - matched["population_2020"]
    matched["pct_change"] = (matched["change"] / matched["population_2020"] * 100).round(1)

    print(f"\nNational: HAPI 2020 total = {hapi['population_2020'].sum():,.0f}, "
          f"Stats SA 2022 total = {sa['population_2022'].sum():,.0f}")

    print("\nDistricts where 2022 population is LOWER than 2020 (check these):")
    shrank = matched[matched["change"] < 0].sort_values("pct_change")
    print(shrank[["admin2_name", "population_2020", "population_2022", "pct_change"]].to_string(index=False)
          if len(shrank) else "  none")

    print("\nDistricts with the largest growth (check for outliers/errors):")
    print(matched.sort_values("pct_change", ascending=False)
          .head(5)[["admin2_name", "population_2020", "population_2022", "pct_change"]]
          .to_string(index=False))

    print(f"\npct_change distribution:\n{matched['pct_change'].describe().to_string()}")

    out = INTERIM / "population_comparison.csv"
    matched[["admin2_code", "admin2_name", "population_2020", "population_2022",
             "change", "pct_change"]].sort_values("admin2_code").to_csv(out, index=False)
    print(f"\nSaved comparison table to {out}")


if __name__ == "__main__":
    main()
