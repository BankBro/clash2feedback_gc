from __future__ import annotations

import argparse
from pathlib import Path

from clash2feedback.data.render_visual_check import (
    CAMERA_MODES,
    DEFAULT_ANGLES,
    DEFAULT_CAMERA_MODE,
    DEFAULT_CANDIDATE_DIRECTIONS,
    DEFAULT_CONTACT_SHEET_COLUMNS,
    DEFAULT_CONTACT_SHEET_ROWS,
    DEFAULT_NUM_CLEAR_VIEWS,
    DEFAULT_VIEWS,
    build_render_tasks,
    render_visual_check_images,
    write_batch_review_markdown,
    write_render_contact_sheets,
    write_render_manifest,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render phase0 visual check images with headless ChimeraX.")
    parser.add_argument("--assets-root", default="runs/phase0_visual_check")
    parser.add_argument("--views", nargs="+", default=list(DEFAULT_VIEWS), choices=list(DEFAULT_VIEWS))
    parser.add_argument("--camera-mode", default=DEFAULT_CAMERA_MODE, choices=list(CAMERA_MODES))
    parser.add_argument("--angles", nargs="+", default=list(DEFAULT_ANGLES), choices=list(DEFAULT_ANGLES), help="Used only with --camera-mode fixed-angles.")
    parser.add_argument("--num-clear-views", type=int, default=DEFAULT_NUM_CLEAR_VIEWS)
    parser.add_argument("--candidate-directions", type=int, default=DEFAULT_CANDIDATE_DIRECTIONS)
    parser.add_argument("--sample-id", action="append", default=None, help="Render only selected sample id. Can be repeated.")
    parser.add_argument("--max-samples", type=int, default=None)
    parser.add_argument("--manifest", default="runs/phase0_visual_check/render_manifest.csv")
    parser.add_argument("--summary", default="tmp/20260507/phase0-visual-render-summary.md")
    parser.add_argument("--chimerax", default="chimerax")
    parser.add_argument("--width", type=int, default=1800)
    parser.add_argument("--height", type=int, default=1400)
    parser.add_argument("--contact-sheet-rows", type=int, default=DEFAULT_CONTACT_SHEET_ROWS)
    parser.add_argument("--contact-sheet-columns", type=int, default=DEFAULT_CONTACT_SHEET_COLUMNS)
    parser.add_argument("--no-contact-sheets", action="store_true")
    parser.add_argument("--timeout-seconds", type=int, default=180)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    tasks = build_render_tasks(
        args.assets_root,
        views=args.views,
        angles=args.angles,
        sample_ids=args.sample_id,
        max_samples=args.max_samples,
        camera_mode=args.camera_mode,
        num_clear_views=args.num_clear_views,
        candidate_directions=args.candidate_directions,
    )
    results = render_visual_check_images(
        tasks,
        chimerax=args.chimerax,
        dry_run=args.dry_run,
        timeout_seconds=args.timeout_seconds,
        width=args.width,
        height=args.height,
    )
    contact_sheets = (
        []
        if args.dry_run or args.no_contact_sheets
        else write_render_contact_sheets(
            results,
            rows=args.contact_sheet_rows,
            columns=args.contact_sheet_columns,
        )
    )
    write_render_manifest(results, args.manifest)
    write_batch_review_markdown(results, args.summary, assets_root=args.assets_root, contact_sheets=contact_sheets)

    status_counts: dict[str, int] = {}
    for row in results:
        status_counts[row.status] = status_counts.get(row.status, 0) + 1
    print(f"Prepared {len(tasks)} render tasks under {Path(args.assets_root)}")
    print(f"Wrote render manifest to {args.manifest}")
    print(f"Wrote render summary to {args.summary}")
    if not args.dry_run and not args.no_contact_sheets:
        print(f"Wrote contact sheets: {sum(1 for row in contact_sheets if row.status == 'written')}")
    print(f"Status counts: {status_counts}")
    if any(row.status in {"failed", "timeout", "missing_image"} for row in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
