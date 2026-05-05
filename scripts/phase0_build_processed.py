#!/usr/bin/env python
from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from clash2feedback.data.build_processed_dataset import build_processed_dataset
from clash2feedback.utils.config import load_yaml_config, resolve_repo_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build phase 0 processed complexes.")
    parser.add_argument("--config", default="configs/phase0.yaml", help="Path to phase0 yaml config.")
    parser.add_argument("--raw-root", default=None, help="Override raw complex root.")
    parser.add_argument("--processed-root", default=None, help="Override processed output root.")
    parser.add_argument("--report-root", default=None, help="Override report output root.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_yaml_config(resolve_repo_path(args.config, repo_root=REPO_ROOT))
    paths = config.get("paths", {})
    raw_root = resolve_repo_path(args.raw_root or paths.get("raw_root", "data/raw_complexes"), repo_root=REPO_ROOT)
    processed_root = resolve_repo_path(
        args.processed_root or paths.get("processed_root", "data/processed/v0_1"),
        repo_root=REPO_ROOT,
    )
    report_root = resolve_repo_path(args.report_root or paths.get("report_root", "reports/phase0"), repo_root=REPO_ROOT)
    result = build_processed_dataset(raw_root, processed_root, config, report_dir=report_root)
    print(
        "phase0_build_processed complete: "
        f"processed={len(result['manifest'])} failed={len(result['failed_cases'])} "
        f"processed_root={processed_root}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
