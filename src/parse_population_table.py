"""Parse the Population table (pages 7-13) of the Census 2022 Municipal
fact sheet using word x-positions, not text spacing, since Stats SA uses
a space as the thousands separator (e.g. "450 584") which makes plain
text parsing ambiguous.

Run from the repo root:
    python src/parse_population_table.py
"""
import re
from pathlib import Path

import pdfplumber

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
INTERIM = ROOT / "data" / "interim"

FIRST_PAGE, LAST_PAGE = 7, 13  # 1-indexed, inclusive; Education starts at 14
PROVINCES = {"Eastern Cape", "Free State", "Gauteng", "KwaZulu-Natal", "Limpopo",
             "Mpumalanga", "Northern Cape", "North West", "Western Cape"}


def rows_from_page(page, row_tolerance=3):
    """Group words into rows by vertical proximity (not an exact rounded
    match, since a row's name and numbers can sit on slightly different
    baselines), then order each row by x position."""
    words = sorted(page.extract_words(x_tolerance=2, y_tolerance=2), key=lambda w: w["top"])
    rows = []
    for w in words:
        if rows and w["top"] - rows[-1][-1]["top"] <= row_tolerance:
            rows[-1].append(w)
        else:
            rows.append([w])
    for row in rows:
        yield sorted(row, key=lambda w: w["x0"])


def split_by_gap(words, min_gap=6):
    """Split a list of words (sorted by x0) into groups wherever the
    horizontal gap between consecutive words exceeds min_gap."""
    if not words:
        return []
    groups = [[words[0]]]
    for a, b in zip(words, words[1:]):
        gap = b["x0"] - a["x1"]
        if gap > min_gap:
            groups.append([])
        groups[-1].append(b)
    return groups


def parse_number(tokens):
    text = "".join(t["text"] for t in tokens)
    text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def main() -> None:
    matches = sorted(RAW.glob("*Census_2022_Municipal*.pdf"))
    if not matches:
        raise SystemExit(f"No municipal fact sheet PDF in {RAW}")
    pdf_path = matches[0]

    results = []
    unexpected = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_no in range(FIRST_PAGE, LAST_PAGE + 1):
            page = pdf.pages[page_no - 1]
            for row_words in rows_from_page(page):
                line_text = " ".join(w["text"] for w in row_words)
                if not re.search(r"\d", line_text):
                    continue  # header/label rows with no numbers
                if "Ratio per 100" in line_text or "fact sheet, Report" in line_text:
                    continue  # repeating page header/footer

                # Name = leading words that are not purely numeric/decimal.
                name_words, rest = [], row_words
                for i, w in enumerate(row_words):
                    if re.fullmatch(r"-?[\d,]+", w["text"]):
                        name_words, rest = row_words[:i], row_words[i:]
                        break
                else:
                    continue
                name = " ".join(w["text"] for w in name_words)
                if not name:
                    continue

                groups = split_by_gap(rest)
                # Expect 14 groups: pop11, pop22, <15_11,<15_22, 15-64_11,15-64_22,
                # 65+_11,65+_22, ratio_11,ratio_22, medage_11,medage_22, growth1, growth2
                if len(groups) != 14:
                    unexpected.append((page_no, len(groups), line_text))
                    continue

                pop_2011 = parse_number(groups[0])
                pop_2022 = parse_number(groups[1])

                code = None
                m = re.match(r"^([A-Z]{2,3}\d{3})\s*:\s*(.+)$", name)
                if m:
                    level = "municipality"
                    code, clean_name = m.group(1), m.group(2)
                elif name == "SOUTH AFRICA":
                    level, clean_name = "national", name
                elif name in PROVINCES:
                    level, clean_name = "province", name
                else:
                    level, clean_name = "district_or_metro", name

                results.append({
                    "level": level, "code": code, "name": clean_name,
                    "population_2011": pop_2011, "population_2022": pop_2022,
                    "page": page_no,
                })

    print(f"\n{len(unexpected)} row(s) skipped for unexpected group count:")
    for page_no, n, text in unexpected:
        print(f"  page {page_no}, {n} groups: {text}")

    import pandas as pd
    df = pd.DataFrame(results)
    print(f"\nParsed {len(df)} rows total.")
    print(df["level"].value_counts().to_string())

    dist = df[df["level"] == "district_or_metro"]
    print(f"\nDistrict/metro rows: {len(dist)} (expect 52)")
    print(dist[["name", "population_2022"]].to_string(index=False))

    INTERIM.mkdir(parents=True, exist_ok=True)
    out = INTERIM / "census2022_population_parsed.csv"
    df.to_csv(out, index=False)
    print(f"\nSaved all parsed rows to {out}")


if __name__ == "__main__":
    main()