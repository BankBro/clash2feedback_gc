from __future__ import annotations

import argparse
from pathlib import Path

from clash2feedback.repair.pipeline import run_phase4_0_formal, run_phase4_0_preflight
from clash2feedback.utils.config import load_yaml_config


def main() -> int:
    parser = argparse.ArgumentParser(description="Run phase 4.0 backend feasibility experiments.")
    parser.add_argument("--config", default="configs/phase4_0_backend_feasibility.yaml")
    parser.add_argument(
        "--mode",
        choices=["preflight", "formal"],
        default="preflight",
        help="Run the 5-case preflight or the 40-case formal small-scale audit.",
    )
    args = parser.parse_args()

    repo_root = Path.cwd()
    config = load_yaml_config(args.config)
    if args.mode == "preflight":
        result = run_phase4_0_preflight(config, repo_root=repo_root)
    else:
        result = run_phase4_0_formal(config, repo_root=repo_root)
    print(f"phase4_0 {args.mode} complete: {result['summary_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
