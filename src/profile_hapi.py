"""Profile the HAPI baseline population files for South Africa.

Run from the repo root:
    python3 src/profile_hapi.py
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
COUNTRY = "ZAF"


def load(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str, low_memory=False)
    # HDX CSVs carry an HXL tag row (values start with "#") under the header.
    df = df[~df["location_code"].fillna("").str.startswith("#")].copy()
    return df


def main() -> None:
    files = sorted(RAW.glob("*hapi_population*.csv"))
    if not files:
        raise SystemExit(f"No HAPI population files in {RAW}")

    frames = []
    for f in files:
        df = load(f)
        n_zaf = (df["location_code"] == COUNTRY).sum()
        print(f"{f.name}: {len(df):,} rows, {df['location_code'].nunique()} countries, "
              f"{n_zaf:,} rows for {COUNTRY}")
        frames.append(df[df["location_code"] == COUNTRY].assign(source_file=f.name))

    za = pd.concat(frames, ignore_index=True)
    if za.empty:
        raise SystemExit(f"\n{COUNTRY} not found in any file.")

    za["population"] = pd.to_numeric(za["population"], errors="coerce")
    print(f"\n=== {COUNTRY} ===")
    print("Columns:", list(za.columns))
    print("\nRows by source file:")
    print(za["source_file"].value_counts().to_string())
    print("\nRows by admin_level:")
    print(za["admin_level"].value_counts(dropna=False).to_string())
    for lvl in ("1", "2"):
        sub = za[za["admin_level"] == lvl]
        col = f"admin{lvl}_code"
        if col in za.columns and not sub.empty:
            print(f"\nDistinct admin{lvl} areas: {sub[col].nunique()}")
    print("\nGender values:", sorted(za["gender"].dropna().unique()))
    print("Age ranges:", sorted(za["age_range"].dropna().unique(), key=lambda s: (len(s), s)))
    print("Reference periods:",
          za[["reference_period_start", "reference_period_end"]].drop_duplicates().to_string(index=False))
    print("Missing population values:", int(za["population"].isna().sum()))

    # Sanity check: total population at each admin level, all genders and ages.
    tot = za[za["gender"].isin(["all", "a"]) & za["age_range"].isin(["all", "All"])]
    if not tot.empty:
        print("\nTotal population by admin_level (gender=all, age=all):")
        print(tot.groupby("admin_level")["population"].sum().to_string())


if __name__ == "__main__":
    main()
