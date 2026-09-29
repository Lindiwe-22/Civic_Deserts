"""Inspect the Census 2022 Municipal fact sheet PDF before we write a parser.

Uses pdfplumber (pure Python, no Poppler/Xcode needed).

Run from the repo root:
    python src/inspect_factsheet.py
"""
from pathlib import Path

import pdfplumber

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
INTERIM = ROOT / "data" / "interim"


def main() -> None:
    matches = sorted(RAW.glob("*Census_2022_Municipal*.pdf"))
    if not matches:
        raise SystemExit(f"No municipal fact sheet PDF in {RAW}")
    pdf_path = matches[0]
    print(f"Using {pdf_path.name}")

    INTERIM.mkdir(parents=True, exist_ok=True)
    out = INTERIM / "factsheet_raw.txt"

    all_text = []
    found_at = None
    with pdfplumber.open(pdf_path) as pdf:
        print(f"Pages: {len(pdf.pages)}")
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            all_text.append(text)
            if found_at is None and ("Eastern Cape" in text or "Alfred Nzo" in text):
                found_at = i

    out.write_text("\n\n----- PAGE BREAK -----\n\n".join(all_text))
    total_lines = sum(t.count("\n") + 1 for t in all_text)
    print(f"Extracted {total_lines} lines of text to {out}")

    if found_at is not None:
        print(f"\n--- page {found_at + 1}, first 25 lines ---")
        print("\n".join(all_text[found_at].splitlines()[:25]))

        # Also try structured table extraction on that page.
        with pdfplumber.open(pdf_path) as pdf:
            tables = pdf.pages[found_at].extract_tables()
        print(f"\npdfplumber found {len(tables)} table(s) on this page.")
        if tables:
            print("First table, first 5 rows:")
            for row in tables[0][:5]:
                print(row)
    else:
        print("\nNo district name found in text layer — table may be image-based.")
        print("First 20 lines of page 1 instead:")
        print("\n".join(all_text[0].splitlines()[:20]))


if __name__ == "__main__":
    main()
