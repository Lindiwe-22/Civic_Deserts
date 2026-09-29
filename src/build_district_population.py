"""Build the final district population table for the analysis:
- population totals from Stats SA Census 2022 (more current, directly measured)
- age-band split from HAPI's 2020 baseline, applied as proportions to the
  Stats SA total (so we get current totals with a 5-year age breakdown)

Handles four districts renamed since HAPI's admin boundaries were coded:
  Cacadu -> Sarah Baartman, Eden -> Garden Route,
  Sisonke -> Harry Gwala, Uthungulu -> King Cetshwayo
Output rows use the current name with the old name in parentheses, e.g.
"Sarah Baartman (Cacadu)", so the district is identifiable under either name.

Run from the repo root:
    python src/build_district_population.py
"""
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
INTERIM = ROOT / "data" / "interim"
PROCESSED = ROOT / "data" / "processed"

# old (HAPI/boundary) name -> current (Stats SA) name
RENAMES = {
    "Cacadu": "Sarah Baartman",
    "Eden": "Garden Route",
    "Sisonke": "Harry Gwala",
    "Uthungulu": "King Cetshwayo",
}


def normalize(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def display_name(hapi_name: str, current_name: str) -> str:
    if hapi_name in RENAMES:
        return f"{current_name} ({hapi_name})"
    return current_name


def main() -> None:
    hapi_path = RAW / "hdx_hapi_population_global_non_hrp.csv"
    hapi = pd.read_csv(hapi_path, dtype=str, low_memory=False)
    hapi = hapi[(hapi["location_code"] == "ZAF") & (hapi["admin_level"] == "2")]
    hapi["population"] = pd.to_numeric(hapi["population"])

    # District 2020 totals (gender=all, age_range=all)
    hapi_totals = hapi[(hapi["gender"] == "all") & (hapi["age_range"] == "all")]
    hapi_totals = hapi_totals[["admin2_code", "admin2_name", "population"]].rename(
        columns={"population": "population_2020"})

    # District age-band breakdown (gender=all, real age bands only)
    age_bands = hapi[(hapi["gender"] == "all") & (hapi["age_range"] != "all")].copy()
    age_bands = age_bands[["admin2_code", "admin2_name", "age_range", "population"]]

    sa = pd.read_csv(INTERIM / "census2022_population_parsed.csv")
    sa = sa[sa["level"] == "district_or_metro"][["name", "population_2022"]].copy()
    sa["key"] = sa["name"].map(normalize)

    # Apply renames before joining, so HAPI's old names match Stats SA's current ones
    hapi_totals["current_name"] = hapi_totals["admin2_name"].replace(RENAMES)
    hapi_totals["key"] = hapi_totals["current_name"].map(normalize)
    age_bands["current_name"] = age_bands["admin2_name"].replace(RENAMES)
    age_bands["key"] = age_bands["current_name"].map(normalize)

    merged = hapi_totals.merge(sa, on="key", how="outer", indicator=True)
    unmatched = merged[merged["_merge"] != "both"]
    if len(unmatched):
        print("UNMATCHED after rename — fix before proceeding:")
        print(unmatched[["admin2_code", "admin2_name", "name"]].to_string(index=False))
        raise SystemExit(1)
    print(f"All {len(merged)} districts matched after applying renames.")

    merged["display_name"] = merged.apply(
        lambda r: display_name(r["admin2_name"], r["current_name"]), axis=1)

    # Age-band shares: for each district, each band's share of that
    # district's own 2020 total, then applied to the district's 2022 total.
    age_bands = age_bands.merge(
        hapi_totals[["admin2_code", "population_2020"]], on="admin2_code")
    age_bands["share"] = age_bands["population"] / age_bands["population_2020"]

    final = age_bands.merge(
        merged[["admin2_code", "display_name", "population_2022"]], on="admin2_code")
    final["population_est"] = (final["share"] * final["population_2022"]).round().astype(int)

    out_long = final[["admin2_code", "display_name", "age_range",
                       "population_est"]].sort_values(["admin2_code", "age_range"])
    out_long = out_long.rename(columns={"population_est": "population"})

    # Sanity check: band totals should sum back to the district 2022 total
    check = out_long.groupby("admin2_code")["population"].sum()
    ref = merged.set_index("admin2_code")["population_2022"]
    diff = (check - ref).abs()
    print(f"\nMax rounding diff between summed age bands and district total: {diff.max()}")

    PROCESSED.mkdir(parents=True, exist_ok=True)
    out_path = PROCESSED / "district_population_2022_by_age.csv"
    out_long.to_csv(out_path, index=False)
    print(f"Saved {len(out_long)} rows to {out_path}")

    totals_path = PROCESSED / "district_population_2022.csv"
    merged[["admin2_code", "display_name", "population_2022"]].sort_values(
        "admin2_code").to_csv(totals_path, index=False)
    print(f"Saved {len(merged)} district totals to {totals_path}")


if __name__ == "__main__":
    main()
