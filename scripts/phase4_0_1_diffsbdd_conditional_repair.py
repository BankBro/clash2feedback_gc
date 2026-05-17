from __future__ import annotations

import argparse
from pathlib import Path

from clash2feedback.repair.phase4_0_1 import run_phase4_0_1
from clash2feedback.utils.config import load_yaml_config


def main() -> int:
    parser = argparse.ArgumentParser(description="Run phase 4.0.1 DiffSBDD conditional repair.")
    parser.add_argument("--config", default="configs/phase4_0_1_diffsbdd_conditional_repair.yaml")
    parser.add_argument("--mode", choices=["preflight", "formal", "report-only"], default="preflight")
    parser.add_argument("--budget-k", type=int, default=None, help="Optional single candidate budget K.")
    args = parser.parse_args()

    repo_root = Path.cwd()
    config = load_yaml_config(args.config)
    result = run_phase4_0_1(config, repo_root=repo_root, mode=args.mode, budget_k=args.budget_k)
    print(f"phase4_0_1 {args.mode} complete: {result['summary'].get('mode')} {result['summary'].get('candidate_budget_ks')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
