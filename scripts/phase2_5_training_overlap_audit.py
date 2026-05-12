#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from clash2feedback.generation_audit.overlap import build_training_overlap_audit, summarize_overlap
from clash2feedback.utils.config import load_yaml_config, resolve_repo_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run phase 2.5 DiffSBDD/CrossDocked training-overlap audit.")
    parser.add_argument("--config", default="configs/phase2_5_model_induced_audit.yaml")
    parser.add_argument("--manifest", default=None)
    parser.add_argument("--output-root", default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_yaml_config(resolve_repo_path(args.config, repo_root=REPO_ROOT))
    inputs = config.get("inputs", {})
    outputs = config.get("outputs", {})
    manifest_path = resolve_repo_path(args.manifest or inputs.get("manifest", "data/processed/v0_1/manifest.parquet"), repo_root=REPO_ROOT)
    processed_root = resolve_repo_path(inputs.get("processed_root", "data/processed/v0_1"), repo_root=REPO_ROOT)
    splits_root = resolve_repo_path(inputs.get("splits_root", "data/splits/v0_1"), repo_root=REPO_ROOT)
    output_root = resolve_repo_path(args.output_root or outputs.get("report_root", "reports/phase2_5_model_induced_audit"), repo_root=REPO_ROOT)
    output_root.mkdir(parents=True, exist_ok=True)
    if not manifest_path.exists():
        print(f"ERROR: manifest not found: {manifest_path}", file=sys.stderr)
        return 2
    manifest = pd.read_parquet(manifest_path)
    split_files = {
        key: str(resolve_repo_path(value, repo_root=REPO_ROOT))
        for key, value in (config.get("overlap", {}).get("official_split_files", {}) or {}).items()
        if value
    }
    audit_df = build_training_overlap_audit(
        manifest,
        processed_root=processed_root,
        splits_root=splits_root,
        official_split_files=split_files,
    )
    audit_df.to_csv(output_root / "training_overlap_audit.csv", index=False)
    summary = summarize_overlap(audit_df)
    with (output_root / "training_overlap_summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(
        "phase2_5_training_overlap_audit complete: "
        f"pockets={len(audit_df)} external_eligible={summary['external_validity_subset_size']} report_root={output_root}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
