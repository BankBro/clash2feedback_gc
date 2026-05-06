from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from clash2feedback.data.balanced_manifest import make_balanced_selection, write_balanced_outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a target-balanced phase0 subset manifest.")
    parser.add_argument("--manifest", default="data/processed/v0_1/manifest.parquet")
    parser.add_argument("--visual-check", default="reports/phase0/visual_check_list.csv")
    parser.add_argument("--output", default="data/splits/v0_1/phase0_balanced_30.txt")
    parser.add_argument("--summary", default="tmp/20260506/phase0-balanced30-summary.md")
    parser.add_argument("--max-samples", type=int, default=30)
    parser.add_argument("--min-samples", type=int, default=20)
    parser.add_argument("--max-per-target", type=int, default=5)
    parser.add_argument("--seed", type=int, default=20260504)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")
    manifest = pd.read_parquet(manifest_path)

    visual_path = Path(args.visual_check)
    visual_check = pd.read_csv(visual_path) if visual_path.exists() else pd.DataFrame()
    result = make_balanced_selection(
        manifest,
        visual_check,
        max_samples=args.max_samples,
        min_samples=args.min_samples,
        max_per_target=args.max_per_target,
        seed=args.seed,
    )
    write_balanced_outputs(result, output_path=args.output, summary_path=args.summary)
    print(
        "Wrote balanced subset: "
        f"requested_max_samples={result.requested_max_samples}, "
        f"actual_samples={result.actual_samples}, "
        f"max_per_target={result.max_per_target}"
    )


if __name__ == "__main__":
    main()
