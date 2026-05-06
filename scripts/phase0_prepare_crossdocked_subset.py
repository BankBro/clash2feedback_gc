#!/usr/bin/env python
from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from clash2feedback.data.prepare_raw_complexes import (
    prepare_crossdocked_subset,
    prepare_if3_crossdocked_archive_subset,
)
from clash2feedback.utils.config import resolve_repo_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare a paired CrossDocked subset for phase 0.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--auto-download", action="store_true", help="Fetch paired files from public HF sources.")
    mode.add_argument("--crossdocked-root", default=None, help="Local CrossDocked root with paired files.")
    parser.add_argument("--download-root", default="data/cache/crossdocked_downloads", help="Project-local cache root.")
    parser.add_argument("--output-root", default="data/raw_complexes", help="Raw complex output root.")
    parser.add_argument("--max-candidates", type=int, default=50, help="Maximum paired complexes to prepare.")
    parser.add_argument(
        "--source",
        choices=["thu_test", "if3_archive"],
        default="thu_test",
        help="Public source used by --auto-download.",
    )
    parser.add_argument(
        "--protein-source",
        choices=["pocket10", "full_receptor"],
        default="pocket10",
        help="Use CrossDocked pocket10 PDB or full receptor PDB as protein.pdb.",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite existing prepared files.")
    parser.add_argument("--dry-run", action="store_true", help="Inspect pairing without writing output files.")
    parser.add_argument(
        "--no-prefilter-ligands",
        action="store_true",
        help="Disable ligand-only prefilter before preparing candidates.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_root = resolve_repo_path(args.output_root, repo_root=REPO_ROOT)
    download_root = resolve_repo_path(args.download_root, repo_root=REPO_ROOT)
    crossdocked_root = (
        resolve_repo_path(args.crossdocked_root, repo_root=REPO_ROOT)
        if args.crossdocked_root is not None
        else None
    )
    if args.auto_download and args.source == "if3_archive":
        if args.protein_source != "pocket10":
            raise ValueError("--source if3_archive only supports --protein-source pocket10")
        result = prepare_if3_crossdocked_archive_subset(
            output_root=output_root,
            max_candidates=args.max_candidates,
            download_root=download_root,
            force=args.force,
            dry_run=args.dry_run,
            prefilter_ligands=not args.no_prefilter_ligands,
            tmp_root=REPO_ROOT / "tmp",
        )
    else:
        result = prepare_crossdocked_subset(
            output_root=output_root,
            max_candidates=args.max_candidates,
            download_root=download_root,
            crossdocked_root=crossdocked_root,
            auto_download=bool(args.auto_download),
            protein_source=args.protein_source,
            force=args.force,
            dry_run=args.dry_run,
            prefilter_ligands=not args.no_prefilter_ligands,
            tmp_root=REPO_ROOT / "tmp",
        )
    print(
        "phase0_prepare_crossdocked_subset complete: "
        f"discovered={result['num_discovered_pairs']} prepared={result['num_prepared']} "
        f"skipped_by_prefilter={result['num_skipped_by_prefilter']} output_root={output_root}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
