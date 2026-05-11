#!/usr/bin/env python
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from clash2feedback.data.phase2_visual_qc import (
    DEFAULT_CANDIDATE_DIRECTIONS,
    DEFAULT_PHASE2_VISUAL_QC_VIEWS,
    PHASE2_VISUAL_QC_VIEWS,
    build_phase2_visual_qc_assets,
    render_phase2_visual_qc_tasks,
    write_phase2_visual_qc_category_index,
    write_phase2_manual_review_template,
    write_phase2_visual_qc_contact_sheets,
    write_phase2_visual_qc_summary,
)
from clash2feedback.utils.files import ensure_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render Phase 2 visual QC images with clear-view camera selection.")
    parser.add_argument("--visual-qc-cases", default="reports/phase2_injection/visual_qc_cases.csv")
    parser.add_argument("--manifest", default="data/benchmarks/clashrepairbench_rg_artificial/v0_1/manifest.parquet")
    parser.add_argument("--benchmark-root", default="data/benchmarks/clashrepairbench_rg_artificial/v0_1")
    parser.add_argument("--processed-root", default="data/processed/v0_1/complexes")
    parser.add_argument("--output-root", default="runs/phase2_visual_qc")
    parser.add_argument("--report-root", default="reports/phase2_visual_qc")
    parser.add_argument("--case-id", action="append", default=None, help="Render one case id. Can be repeated.")
    parser.add_argument("--max-cases", type=int, default=None)
    parser.add_argument("--views", nargs="+", default=list(DEFAULT_PHASE2_VISUAL_QC_VIEWS), choices=list(PHASE2_VISUAL_QC_VIEWS))
    parser.add_argument("--num-clear-views", type=int, default=12)
    parser.add_argument("--candidate-directions", type=int, default=DEFAULT_CANDIDATE_DIRECTIONS)
    parser.add_argument("--chimerax", default="chimerax")
    parser.add_argument("--width", type=int, default=1600)
    parser.add_argument("--height", type=int, default=1200)
    parser.add_argument("--timeout-seconds", type=int, default=240)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-existing", action="store_true", help="Reuse complete existing image groups and render only missing groups.")
    parser.add_argument("--no-contact-sheets", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report_root = ensure_dir(args.report_root)
    assets, tasks = build_phase2_visual_qc_assets(
        visual_qc_cases_path=args.visual_qc_cases,
        manifest_path=args.manifest,
        benchmark_root=args.benchmark_root,
        processed_root=args.processed_root,
        output_root=args.output_root,
        case_ids=args.case_id,
        max_cases=args.max_cases,
        views=args.views,
        num_clear_views=args.num_clear_views,
        candidate_directions=args.candidate_directions,
    )
    render_manifest = render_phase2_visual_qc_tasks(
        tasks,
        chimerax=args.chimerax,
        dry_run=args.dry_run,
        skip_existing=args.skip_existing,
        width=args.width,
        height=args.height,
        timeout_seconds=args.timeout_seconds,
    )
    contact_sheets = (
        render_manifest.head(0)
        if args.dry_run or args.no_contact_sheets
        else write_phase2_visual_qc_contact_sheets(render_manifest)
    )

    assets_path = report_root / "asset_manifest.csv"
    render_path = report_root / "render_manifest.csv"
    sheets_path = report_root / "contact_sheets.csv"
    category_index_path = report_root / "by_category_index.csv"
    summary_path = report_root / "phase2_visual_qc_render_summary.md"
    manual_template_path = report_root / "manual_review_template.csv"

    assets.to_csv(assets_path, index=False)
    render_manifest.to_csv(render_path, index=False)
    contact_sheets.to_csv(sheets_path, index=False)
    write_phase2_visual_qc_category_index(
        asset_manifest=assets,
        output_root=args.output_root,
        report_root=report_root,
    )
    write_phase2_manual_review_template(manual_template_path, assets)
    write_phase2_visual_qc_summary(
        path=summary_path,
        asset_manifest=assets,
        render_manifest=render_manifest,
        contact_sheets=contact_sheets,
        output_root=args.output_root,
        category_index_path=category_index_path,
    )

    status_counts = render_manifest["status"].value_counts().to_dict() if not render_manifest.empty else {}
    print(f"Prepared {len(assets)} phase2 visual QC case(s) under {Path(args.output_root)}")
    print(f"Wrote reports to {report_root}")
    print(f"Render status counts: {status_counts}")
    if not args.dry_run and any(status in {"failed", "timeout", "missing_image"} for status in status_counts):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
