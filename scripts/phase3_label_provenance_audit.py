#!/usr/bin/env python
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from clash2feedback.feedback.mask_seed import Phase3ConflictError, build_phase3_outputs
from clash2feedback.utils.config import load_yaml_config, resolve_repo_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run phase3 label provenance audit and phase4 mask seed generation.")
    parser.add_argument("--config", default="configs/phase3_label_provenance_audit.yaml")
    parser.add_argument("--phase2-benchmark-root", default=None)
    parser.add_argument("--phase2-manifest", default=None)
    parser.add_argument("--phase2-report-root", default=None)
    parser.add_argument("--processed-root", default=None)
    parser.add_argument("--phase2-5-report-root", default=None)
    parser.add_argument("--report-root", default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config_path = resolve_repo_path(args.config, repo_root=REPO_ROOT)
    config = load_yaml_config(config_path)
    _apply_overrides(config, args)
    try:
        result = build_phase3_outputs(config, repo_root=REPO_ROOT, write_outputs=True)
    except Phase3ConflictError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 3
    summary = result.summary
    print(
        "phase3_label_provenance_audit complete: "
        f"S2={summary['set_counts']['S2_phase2_supported_single_rgroup']} "
        f"mask_seed_rows={summary['phase4_mask_seed']['rows']} "
        f"report_root={config.get('outputs', {}).get('report_root', 'reports/phase3_label_provenance_audit')}"
    )
    return 0


def _apply_overrides(config: dict[str, Any], args: argparse.Namespace) -> None:
    inputs = config.setdefault("inputs", {})
    outputs = config.setdefault("outputs", {})
    overrides = {
        "phase2_benchmark_root": args.phase2_benchmark_root,
        "phase2_manifest": args.phase2_manifest,
        "phase2_report_root": args.phase2_report_root,
        "processed_root": args.processed_root,
        "phase2_5_report_root": args.phase2_5_report_root,
    }
    for key, value in overrides.items():
        if value:
            inputs[key] = value
    if args.report_root:
        outputs["report_root"] = args.report_root


if __name__ == "__main__":
    raise SystemExit(main())
