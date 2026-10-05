"""Split each district's 2022 population by sex, using HAPI's 2020 gender
shares applied to the district's 2022 Stats SA total — same method as the
age-band split in build_district_population.py.

Run from the repo root (after build_district_population.py):
    python src/build_district_population_by_sex.py
"""
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"

RENAMES = {
    "Cacadu": "Sarah Baartman",
    "Eden": "Garden Route",
    "Sisonke": "Harry Gwala",
    "Uthungulu": "King Cetshwayo",
}


def normalize(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def main() -> None:
    hapi_path = RAW / "hdx_hapi_population_global_non_hrp.csv"
    hapi = pd.read_csv(hapi_path, dtype=str, low_memory=False)
    hapi = hapi[(hapi["location_code"] == "ZAF") & (hapi["admin_level"] == "2")]
    hapi["population"] = pd.to_numeric(hapi["population"])

    totals = hapi[(hapi["gender"] == "all") & (hapi["age_range"] == "all")]
    totals = totals[["admin2_code", "admin2_name", "population"]].rename(
        columns={"population": "population_2020"})

    sex = hapi[(hapi["gender"].isin(["f", "m"])) & (hapi["age_range"] == "all")]
    sex = sex[["admin2_code", "gender", "population"]]

    totals["current_name"] = totals["admin2_name"].replace(RENAMES)
    totals["key"] = totals["current_name"].map(normalize)

    district_totals = pd.read_csv(PROCESSED / "district_population_2022.csv")

    merged = totals.merge(
        district_totals[["admin2_code", "display_name", "population_2022"]],
        on="admin2_code", how="inner")
    if len(merged) != len(totals):
        print(f"WARNING: {len(totals) - len(merged)} district(s) didn't match "
              f"district_population_2022.csv")

    sex = sex.merge(totals[["admin2_code", "population_2020"]], on="admin2_code")
    sex["share"] = sex["population"] / sex["population_2020"]

    final = sex.merge(
        merged[["admin2_code", "display_name", "population_2022"]], on="admin2_code")
    final["population_est"] = (final["share"] * final["population_2022"]).round().astype(int)

    pivot = final.pivot(index=["admin2_code", "display_name"],
                         columns="gender", values="population_est").reset_index()
    pivot = pivot.rename(columns={"f": "population_female", "m": "population_male"})
    pivot = pivot.merge(district_totals[["admin2_code", "population_2022"]], on="admin2_code")

    diff = (pivot["population_female"] + pivot["population_male"] - pivot["population_2022"]).abs()
    print(f"Max rounding diff between female+male and district total: {diff.max()}")

    pivot["pct_female"] = (pivot["population_female"] / pivot["population_2022"] * 100).round(1)

    out = PROCESSED / "district_population_2022_by_sex.csv"
    pivot.sort_values("admin2_code").to_csv(out, index=False)
    print(f"Saved {len(pivot)} districts to {out}")
    print(f"\nNational: {pivot['population_female'].sum():,.0f} female, "
          f"{pivot['population_male'].sum():,.0f} male")


if __name__ == "__main__":
    main()
