"""Copy downloaded HDX files from the Downloads folder into data/raw/.

Usage (from the repo root in the VS Code terminal):
    python src/ingest_raw.py
    python src/ingest_raw.py --source "D:/some/other/folder"
    python src/ingest_raw.py --force        # overwrite files already in data/raw
"""
import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"

# Patterns are deliberately loose so a typo in a filename (e.g. a missing
# leading "h") still matches.
PATTERNS = [
    "*hapi_population*.csv",
    "zaf_admin_boundaries.gdb",
    "hotosm_zaf_*",
]

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path.home() / "Downloads")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if not args.source.is_dir():
        raise SystemExit(f"Source folder not found: {args.source}")
    RAW.mkdir(parents=True, exist_ok=True)

    found = sorted({p for pat in PATTERNS for p in args.source.glob(pat)})
    if not found:
        raise SystemExit(f"No matching files in {args.source}")

    for src in found:
        dest = RAW / src.name
        if dest.exists() and not args.force:
            print(f"skip   {src.name} (already in data/raw, use --force to overwrite)")
            continue
        if src.is_dir():
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(src, dest)
        else:
            shutil.copy2(src, dest)
        print(f"copied {src.name}")

    print(f"\ndata/raw now holds {len(list(RAW.glob('*')))} file(s).")


if __name__ == "__main__":
    main()
