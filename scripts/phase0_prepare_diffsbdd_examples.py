#!/usr/bin/env python
from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from clash2feedback.data.prepare_raw_complexes import prepare_diffsbdd_examples
from clash2feedback.utils.config import resolve_repo_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare DiffSBDD official examples for phase 0 smoke.")
    parser.add_argument("--output-root", default="data/raw_complexes", help="Raw complex output root.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing downloaded example files.")
    parser.add_argument("--dry-run", action="store_true", help="Print planned output without downloading files.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_root = resolve_repo_path(args.output_root, repo_root=REPO_ROOT)
    prepared = prepare_diffsbdd_examples(output_root, force=args.force, dry_run=args.dry_run)
    for row in prepared:
        print(
            "prepared_diffsbdd_example "
            f"complex_id={row['complex_id']} protein={row['protein_path']} ligand={row['ligand_path']}"
        )
    print(f"phase0_prepare_diffsbdd_examples complete: prepared={len(prepared)} output_root={output_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
