from __future__ import annotations

import argparse
from pathlib import Path

from clash2feedback.repair.reconnect_visual_qc import run_phase4_0_1a_visual_qc
from clash2feedback.utils.config import load_yaml_config


def main() -> int:
    parser = argparse.ArgumentParser(description="Run phase 4.0.1a reconnect visual QC closeout rendering.")
    parser.add_argument("--config", default="configs/phase4_0_1a_visual_qc.yaml")
    args = parser.parse_args()

    repo_root = Path.cwd()
    config = load_yaml_config(args.config)
    result = run_phase4_0_1a_visual_qc(config, repo_root=repo_root)
    summary = result["summary"]
    print(
        "phase4_0_1a visual QC complete: "
        f"{summary.get('status')} "
        f"cases={summary.get('sample_count')} "
        f"renders={summary.get('render_status_counts')} "
        f"sheets={summary.get('contact_sheet_status_counts')}"
    )
    return 0 if summary.get("status") == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
