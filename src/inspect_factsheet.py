"""Inspect the Census 2022 Municipal fact sheet PDF before we write a parser.

Run from the repo root:
    python src/inspect_factsheet.py
"""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
INTERIM = ROOT / "data" / "interim"


def main() -> None:
    matches = sorted(RAW.glob("*Census_2022_Municipal*.pdf"))
    if not matches:
        raise SystemExit(f"No municipal fact sheet PDF in {RAW}")
    pdf = matches[0]
    print(f"Using {pdf.name}")

    subprocess.run(["pdfinfo", str(pdf)], check=True)

    INTERIM.mkdir(parents=True, exist_ok=True)
    out = INTERIM / "factsheet_raw.txt"
    subprocess.run(["pdftotext", "-layout", str(pdf), str(out)], check=True)
    text = out.read_text(errors="replace")
    lines = text.splitlines()
    print(f"\nExtracted {len(lines)} lines of text to {out}")

    # Show the first chunk that mentions a known district, so we can see
    # how the demographics table is laid out on the page.
    for i, line in enumerate(lines):
        if "Eastern Cape" in line or "Alfred Nzo" in line:
            print(f"\n--- lines {i}-{i+15} ---")
            print("\n".join(lines[i:i + 15]))
            break
    else:
        print("\nNo district name found in text layer — table may be image-based.")
        print("First 20 lines instead:")
        print("\n".join(lines[:20]))


if __name__ == "__main__":
    main()
