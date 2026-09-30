"""Join population and amenity counts, compute people-per-amenity, and
rank districts.

Two views per amenity, where a more specific denominator makes sense:
- overall population per amenity (all four classes)
- school-age population (5-19) per school
- older-adult population (65+) per clinic

A composite "desert score" ranks districts by how consistently high their
people-per-amenity ratios are across all four classes (percentile rank,
averaged), so a district doesn't have to be worst-in-class everywhere to
surface, just consistently underserved.

Run from the repo root:
    python src/rank_service_deserts.py
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"

RATIO_COLS = {
    "n_clinic": "people_per_clinic",
    "n_school": "people_per_school",
    "n_bank": "people_per_bank",
    "n_police": "people_per_police",
}


def main() -> None:
    pop = pd.read_csv(PROCESSED / "district_population_2022.csv")
    amenities = pd.read_csv(PROCESSED / "district_amenity_counts.csv")
    by_age = pd.read_csv(PROCESSED / "district_population_2022_by_age.csv")

    df = pop.merge(amenities, on="admin2_code", how="outer", indicator=True)
    mismatched = df[df["_merge"] != "both"]
    if len(mismatched):
        print("WARNING — districts not matched between population and amenities:")
        print(mismatched[["admin2_code", "display_name", "boundary_name"]].to_string(index=False))
    df = df.drop(columns="_merge")

    for count_col, ratio_col in RATIO_COLS.items():
        df[ratio_col] = (df["population_2022"] / df[count_col]).round(0)

    # School-age (5-19) per school
    school_age = by_age[by_age["age_range"].isin(["5-9", "10-14", "15-19"])]
    school_age = school_age.groupby("admin2_code")["population"].sum().rename("population_5_19")
    df = df.merge(school_age, on="admin2_code", how="left")
    df["school_age_per_school"] = (df["population_5_19"] / df["n_school"]).round(0)

    # Older-adult (65+) per clinic
    older = by_age[by_age["age_range"].isin(["65-69", "70-74", "75-79", "80+"])]
    older = older.groupby("admin2_code")["population"].sum().rename("population_65plus")
    df = df.merge(older, on="admin2_code", how="left")
    df["older_adult_per_clinic"] = (df["population_65plus"] / df["n_clinic"]).round(0)

    # Composite desert score: mean percentile rank across the four overall
    # ratios (higher percentile = higher people-per-amenity = more underserved)
    pct_cols = []
    for ratio_col in RATIO_COLS.values():
        pct_col = f"{ratio_col}_pctile"
        df[pct_col] = df[ratio_col].rank(pct=True)
        pct_cols.append(pct_col)
    df["desert_score"] = df[pct_cols].mean(axis=1).round(3)

    df = df.sort_values("desert_score", ascending=False)

    display_cols = ["display_name", "population_2022", "n_clinic", "n_school",
                     "n_bank", "n_police", "people_per_clinic", "people_per_school",
                     "people_per_bank", "people_per_police", "desert_score"]

    print("Top 10 most underserved districts (highest desert_score):")
    print(df[display_cols].head(10).to_string(index=False))

    print("\nTop 10 best-served districts (lowest desert_score):")
    print(df[display_cols].tail(10).sort_values("desert_score").to_string(index=False))

    print("\nSchool-age (5-19) per school — top 5 most stretched:")
    print(df.sort_values("school_age_per_school", ascending=False)
          .head(5)[["display_name", "population_5_19", "n_school", "school_age_per_school"]]
          .to_string(index=False))

    print("\nOlder-adult (65+) per clinic — top 5 most stretched:")
    print(df.sort_values("older_adult_per_clinic", ascending=False)
          .head(5)[["display_name", "population_65plus", "n_clinic", "older_adult_per_clinic"]]
          .to_string(index=False))

    out = PROCESSED / "district_ranking.csv"
    df.sort_values("desert_score", ascending=False).to_csv(out, index=False)
    print(f"\nSaved full ranking ({len(df)} districts) to {out}")


if __name__ == "__main__":
    main()
