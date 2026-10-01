"""Plot the desert score as a choropleth across South Africa's 52 districts.

Run from the repo root:
    python src/map_desert_score.py
"""
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
FIGURES = ROOT / "outputs" / "figures"

GDB = RAW / "zaf_admin_boundaries.gdb"
DISTRICT_LAYER = "zaf_admin2"
CODE_COL = "adm2_pcode"


def main() -> None:
    districts = gpd.read_file(GDB, layer=DISTRICT_LAYER)
    districts = districts.rename(columns={CODE_COL: "admin2_code"})

    ranking = pd.read_csv(PROCESSED / "district_ranking.csv")
    merged = districts.merge(ranking, on="admin2_code", how="left")

    missing = merged[merged["desert_score"].isna()]
    if len(missing):
        print(f"WARNING: {len(missing)} district(s) in boundaries but missing a desert_score:")
        print(missing[["admin2_code", "adm2_name"]].to_string(index=False))

    fig, ax = plt.subplots(figsize=(9, 10))
    merged.plot(
        column="desert_score",
        cmap="RdYlGn_r",  # red = underserved, green = well-served
        linewidth=0.4,
        edgecolor="white",
        legend=True,
        legend_kwds={"label": "Desert score (higher = more underserved)", "shrink": 0.6},
        ax=ax,
        missing_kwds={"color": "lightgrey", "label": "No data"},
    )

    # Label the 5 most underserved districts directly on the map.
    # dropna first — nlargest() pads with NaN rows if there aren't enough
    # non-null rows to fill the requested count, rather than excluding them.
    worst5 = merged.dropna(subset=["desert_score"]).nlargest(5, "desert_score")
    for _, row in worst5.iterrows():
        pt = row.geometry.representative_point()
        ax.annotate(row["display_name"], xy=(pt.x, pt.y), fontsize=7,
                    ha="center", color="black",
                    bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.7))

    ax.set_title("Civic Deserts: Service Access Across South African Districts", fontsize=13)
    ax.set_axis_off()

    FIGURES.mkdir(parents=True, exist_ok=True)
    out = FIGURES / "desert_score_choropleth.png"
    plt.tight_layout()
    plt.savefig(out, dpi=200, bbox_inches="tight")
    print(f"Saved map to {out}")
    plt.show()


if __name__ == "__main__":
    main()
