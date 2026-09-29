"""Find where each domain table starts/ends in the fact sheet, and locate
South Africa's 52 admin2 (district/metro) rows within the population table.

Run from the repo root, after inspect_factsheet.py has produced
data/interim/factsheet_raw.txt:
    python src/find_table_bounds.py
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_TXT = ROOT / "data" / "interim" / "factsheet_raw.txt"


def main() -> None:
    if not RAW_TXT.exists():
        raise SystemExit(f"{RAW_TXT} not found — run inspect_factsheet.py first")

    pages = RAW_TXT.read_text().split("----- PAGE BREAK -----")

    # Pages where "SOUTH AFRICA" starts a data row (national total row),
    # marking the start of a new domain table.
    starts = []
    for i, p in enumerate(pages):
        for line in p.splitlines():
            if line.strip().startswith("SOUTH AFRICA") and any(ch.isdigit() for ch in line):
                starts.append(i + 1)
                break
    print(f"Pages where a domain table starts (SOUTH AFRICA total row): {starts}")

    # Print the header context (few lines before the SOUTH AFRICA row) for
    # each such page, so we can identify which domain each table covers.
    for i in [s - 1 for s in starts]:
        lines = pages[i].splitlines()
        for j, line in enumerate(lines):
            if line.strip().startswith("SOUTH AFRICA"):
                print(f"\n--- page {i + 1} header (lines {max(0, j-8)}-{j}) ---")
                print("\n".join(lines[max(0, j-8):j]))
                break


if __name__ == "__main__":
    main()
