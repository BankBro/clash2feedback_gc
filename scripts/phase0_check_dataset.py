#!/usr/bin/env python
from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from clash2feedback.data.check_dataset import check_processed_dataset
from clash2feedback.utils.config import load_yaml_config, resolve_repo_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check phase 0 processed dataset.")
    parser.add_argument("--config", default="configs/phase0.yaml", help="Path to phase0 yaml config.")
    parser.add_argument("--processed-root", default=None, help="Override processed root.")
    parser.add_argument("--manifest", default=None, help="Override manifest path.")
    parser.add_argument("--report-root", default=None, help="Override report output root.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_yaml_config(resolve_repo_path(args.config, repo_root=REPO_ROOT))
    paths = config.get("paths", {})
    processed_root = resolve_repo_path(
        args.processed_root or paths.get("processed_root", "data/processed/v0_1"),
        repo_root=REPO_ROOT,
    )
    manifest = resolve_repo_path(args.manifest or processed_root / "manifest.parquet", repo_root=REPO_ROOT)
    report_root = resolve_repo_path(args.report_root or paths.get("report_root", "reports/phase0"), repo_root=REPO_ROOT)
    result = check_processed_dataset(processed_root, manifest, report_root, config=config)
    dataset_check = result["dataset_check"]
    usable = int(dataset_check["phase0_usable"].sum()) if "phase0_usable" in dataset_check else 0
    print(
        "phase0_check_dataset complete: "
        f"checked={len(dataset_check)} usable={usable} report_root={report_root}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
