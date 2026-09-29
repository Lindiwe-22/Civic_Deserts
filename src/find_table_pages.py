"""Find which pages of the fact sheet actually hold the municipal data table.

Run from the repo root, after inspect_factsheet.py has produced
data/interim/factsheet_raw.txt:
    python src/find_table_pages.py
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_TXT = ROOT / "data" / "interim" / "factsheet_raw.txt"

# A specific district name, unlikely to appear in front matter/boilerplate.
NEEDLE = "Alfred Nzo"


def main() -> None:
    if not RAW_TXT.exists():
        raise SystemExit(f"{RAW_TXT} not found — run inspect_factsheet.py first")

    pages = RAW_TXT.read_text().split("----- PAGE BREAK -----")
    print(f"{len(pages)} pages in extracted text.\n")

    hits = [i for i, p in enumerate(pages) if NEEDLE in p]
    print(f"Pages containing '{NEEDLE}': {[h + 1 for h in hits]}")

    # Also look for pages with a lot of comma-formatted numbers, which is
    # a good signal for a population table (e.g. "1,234,567").
    number_pattern = re.compile(r"\d{1,3}(?:,\d{3})+")
    dense_pages = []
    for i, p in enumerate(pages):
        n = len(number_pattern.findall(p))
        if n >= 10:
            dense_pages.append((i + 1, n))
    print(f"\nPages with 10+ comma-formatted numbers (likely data tables): {dense_pages}")

    if hits:
        i = hits[0]
        print(f"\n--- page {i + 1}, first 40 lines ---")
        print("\n".join(pages[i].splitlines()[:40]))


if __name__ == "__main__":
    main()
