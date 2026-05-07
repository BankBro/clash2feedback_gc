from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

import pandas as pd

from clash2feedback.data.visual_check_assets import generate_visual_check_assets


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate phase0 visual check helper assets.")
    parser.add_argument("--visual-check", default="reports/phase0/visual_check_list.csv")
    parser.add_argument("--manifest", default="data/processed/v0_1/manifest.parquet")
    parser.add_argument("--num-samples", type=int, default=15)
    parser.add_argument("--output-root", default="runs/phase0_visual_check")
    parser.add_argument("--notes", default=f"tmp/{date.today():%Y%m%d}/phase0-visual-check-notes.md")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    visual_path = Path(args.visual_check)
    manifest_path = Path(args.manifest)
    if not visual_path.exists():
        raise FileNotFoundError(f"Visual check list not found: {visual_path}")
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")
    visual_check = pd.read_csv(visual_path)
    manifest = pd.read_parquet(manifest_path)
    assets = generate_visual_check_assets(
        visual_check,
        manifest,
        output_root=args.output_root,
        notes_path=args.notes,
        num_samples=args.num_samples,
    )
    print(f"Wrote visual check assets for {len(assets)} samples to {args.output_root}")
    print(f"Wrote visual check notes to {args.notes}")


if __name__ == "__main__":
    main()
