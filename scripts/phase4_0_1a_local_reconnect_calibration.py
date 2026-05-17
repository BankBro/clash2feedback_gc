from __future__ import annotations

import argparse
from pathlib import Path

from clash2feedback.repair.reconnect_calibration import run_phase4_0_1a
from clash2feedback.utils.config import load_yaml_config


def main() -> int:
    parser = argparse.ArgumentParser(description="Run phase 4.0.1a local reconnect calibration in report-only mode.")
    parser.add_argument("--config", default="configs/phase4_0_1a_local_reconnect_calibration.yaml")
    args = parser.parse_args()

    repo_root = Path.cwd()
    config = load_yaml_config(args.config)
    result = run_phase4_0_1a(config, repo_root=repo_root)
    summary = result["summary"]
    print(
        "phase4_0_1a report-only complete: "
        f"{summary.get('status')} "
        f"diffsbdd={summary.get('num_diffsbdd_candidates_reclassified')} "
        f"strict_shadow={summary.get('strict_single_anchor_shadow_reliable_count')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
