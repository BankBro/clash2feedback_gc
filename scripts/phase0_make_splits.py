#!/usr/bin/env python
from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from clash2feedback.data.split_dataset import make_splits_from_manifest
from clash2feedback.utils.config import load_yaml_config, resolve_repo_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Make phase 0 train/val/test splits.")
    parser.add_argument("--config", default="configs/phase0.yaml", help="Path to phase0 yaml config.")
    parser.add_argument("--manifest", default=None, help="Override manifest path.")
    parser.add_argument("--split-root", default=None, help="Override split output root.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_yaml_config(resolve_repo_path(args.config, repo_root=REPO_ROOT))
    paths = config.get("paths", {})
    processed_root = resolve_repo_path(paths.get("processed_root", "data/processed/v0_1"), repo_root=REPO_ROOT)
    manifest = resolve_repo_path(args.manifest or processed_root / "manifest.parquet", repo_root=REPO_ROOT)
    split_root = resolve_repo_path(args.split_root or paths.get("split_root", "data/splits/v0_1"), repo_root=REPO_ROOT)
    report = make_splits_from_manifest(manifest, split_root, config)
    print(f"phase0_make_splits complete: samples={len(report)} split_root={split_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
