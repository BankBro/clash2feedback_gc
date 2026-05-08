#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import pickle
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from clash2feedback.geometry.clash import detect_clashes
from clash2feedback.geometry.rgroup_attribution import attribute_clashes_to_rgroups
from clash2feedback.geometry.vdw import get_vdw_radius_table
from clash2feedback.utils.config import load_yaml_config, resolve_repo_path
from clash2feedback.verifier.repair_verifier import verify_repair


CLASH_REPORT_COLUMNS = [
    "sample_id",
    "complex_id",
    "source",
    "receptor_scope",
    "delta_angstrom",
    "num_clash_pairs",
    "num_severe_clash_pairs",
    "total_clash_score",
    "max_clash_depth",
    "dominant_region",
    "dominant_ratio",
    "failure_type",
    "recommended_action",
]
ATTRIBUTION_COLUMNS = [
    "dataset_name",
    "sample_id",
    "receptor_scope",
    "delta_angstrom",
    "dominant_region",
    "dominant_ratio",
    "failure_type",
    "recommended_action",
    "region_scores_json",
    "normalized_region_scores_json",
    "top_regions_json",
]
SENSITIVITY_COLUMNS = [
    "dataset_name",
    "receptor_scope",
    "delta_angstrom",
    "num_samples",
    "num_samples_with_severe_clash",
    "severe_false_positive_rate",
    "median_total_clash_score",
    "max_total_clash_score",
]
FAILURE_TYPE_COLUMNS = ["dataset_name", "receptor_scope", "delta_angstrom", "failure_type", "count"]
VERIFIER_COLUMNS = [
    "sample_id",
    "old_clash_score_before",
    "old_clash_score_after",
    "old_clash_resolved",
    "new_severe_clash_count",
    "no_new_severe_clash",
    "scaffold_rmsd",
    "non_edit_rmsd",
    "geometry_valid",
    "edit_compliance",
    "repair_pass",
    "failure_reasons",
]
UNSUPPORTED_COLUMNS = [
    "dataset_name",
    "sample_id",
    "receptor_scope",
    "delta_angstrom",
    "unsupported_reason",
    "error",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run phase 1 vdW clash detector reports.")
    parser.add_argument("--config", default="configs/phase1_clash_detector.yaml", help="Path to phase1 yaml config.")
    parser.add_argument("--manifest", default=None, help="Override processed manifest parquet path.")
    parser.add_argument("--processed-root", default=None, help="Override processed root.")
    parser.add_argument("--balanced-subset", default=None, help="Override balanced subset txt path.")
    parser.add_argument("--output-root", default=None, help="Override report output root.")
    parser.add_argument("--delta", type=float, default=None, help="Override default delta in Angstrom.")
    parser.add_argument("--scopes", default=None, help="Comma-separated receptor scopes.")
    parser.add_argument("--max-samples", type=int, default=None, help="Optional max samples per dataset.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config_path = resolve_repo_path(args.config, repo_root=REPO_ROOT)
    config = load_yaml_config(config_path)
    inputs = config.get("inputs", {})
    outputs = config.get("outputs", {})
    detector_cfg = config.get("detector", {})
    full_receptor_cfg = config.get("full_receptor", {})

    processed_root = resolve_repo_path(
        args.processed_root or inputs.get("processed_root", "data/processed/v0_1"),
        repo_root=REPO_ROOT,
    )
    manifest_path = resolve_repo_path(
        args.manifest or inputs.get("manifest", processed_root / "manifest.parquet"),
        repo_root=REPO_ROOT,
    )
    balanced_path = resolve_repo_path(
        args.balanced_subset or inputs.get("balanced_subset", "data/splits/v0_1/phase0_balanced_30.txt"),
        repo_root=REPO_ROOT,
    )
    output_root = resolve_repo_path(
        args.output_root or outputs.get("report_root", "reports/phase1_clash_detector"),
        repo_root=REPO_ROOT,
    )
    output_root.mkdir(parents=True, exist_ok=True)

    if not manifest_path.exists():
        print(f"ERROR: manifest parquet not found: {manifest_path}", file=sys.stderr)
        return 2
    if not balanced_path.exists():
        print(f"ERROR: balanced subset txt not found: {balanced_path}", file=sys.stderr)
        return 2

    manifest = pd.read_parquet(manifest_path)
    clean_records, load_errors = _load_records(manifest, processed_root, args.max_samples)
    balanced_ids = _read_sample_ids(balanced_path)
    balanced_manifest = _select_manifest_rows(manifest, balanced_ids)
    balanced_records, balanced_load_errors = _load_records(balanced_manifest, processed_root, args.max_samples)
    load_errors.extend(balanced_load_errors)

    scopes = _scopes(args.scopes, detector_cfg)
    default_delta = float(args.delta if args.delta is not None else detector_cfg.get("delta_angstrom", 0.4))
    delta_sensitivity = [float(value) for value in detector_cfg.get("delta_sensitivity", [0.3, 0.4, 0.5])]
    if default_delta not in delta_sensitivity:
        delta_sensitivity.append(default_delta)
        delta_sensitivity = sorted(delta_sensitivity)

    clean_rows, clean_attrs, clean_unsupported = _run_dataset(
        clean_records,
        "phase0_clean_pool_v0_1",
        scopes,
        [default_delta],
        config,
    )
    balanced_rows, balanced_attrs, balanced_unsupported = _run_dataset(
        balanced_records,
        "phase0_balanced_30_v0_1",
        scopes,
        [default_delta],
        config,
    )
    sensitivity_rows, sensitivity_attrs, sensitivity_unsupported = _run_dataset(
        clean_records + balanced_records,
        "mixed_for_sensitivity",
        scopes,
        delta_sensitivity,
        config,
        dataset_names=["phase0_clean_pool_v0_1"] * len(clean_records)
        + ["phase0_balanced_30_v0_1"] * len(balanced_records),
    )

    verifier_rows, verifier_unsupported = _run_verifier_smoke(
        balanced_records if balanced_records else clean_records,
        config,
    )

    unsupported_rows = (
        clean_unsupported
        + balanced_unsupported
        + sensitivity_unsupported
        + verifier_unsupported
        + load_errors
    )
    clean_df = pd.DataFrame(clean_rows, columns=CLASH_REPORT_COLUMNS)
    balanced_df = pd.DataFrame(balanced_rows, columns=CLASH_REPORT_COLUMNS)
    sensitivity_df = _threshold_sensitivity(pd.DataFrame(sensitivity_rows))
    attribution_df = pd.DataFrame(clean_attrs + balanced_attrs, columns=ATTRIBUTION_COLUMNS)
    failure_counts_df = _failure_type_counts(pd.DataFrame(sensitivity_attrs))
    verifier_df = pd.DataFrame(verifier_rows, columns=VERIFIER_COLUMNS)
    unsupported_df = pd.DataFrame(unsupported_rows, columns=UNSUPPORTED_COLUMNS)

    clean_df.to_csv(output_root / "clean_clash_report.csv", index=False)
    balanced_df.to_csv(output_root / "balanced_clash_report.csv", index=False)
    sensitivity_df.to_csv(output_root / "threshold_sensitivity.csv", index=False)
    attribution_df.to_csv(output_root / "rgroup_attribution_report.csv", index=False)
    failure_counts_df.to_csv(output_root / "failure_type_counts.csv", index=False)
    verifier_df.to_csv(output_root / "verifier_smoke_report.csv", index=False)
    unsupported_df.to_csv(output_root / "unsupported_cases.csv", index=False)
    with (output_root / "vdw_radius_table.json").open("w", encoding="utf-8") as f:
        json.dump(get_vdw_radius_table(), f, ensure_ascii=False, indent=2)

    summary = _summary(
        config,
        clean_df,
        balanced_df,
        verifier_df,
        clean_records,
        balanced_records,
        default_delta,
        delta_sensitivity,
        scopes,
        bool(full_receptor_cfg.get("enabled", False)),
        load_errors,
    )
    with (output_root / "summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(
        "phase1_check_clashes complete: "
        f"clean={len(clean_records)} balanced={len(balanced_records)} report_root={output_root}"
    )
    return 0


def _load_records(manifest: pd.DataFrame, processed_root: Path, max_samples: int | None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    records: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    limited = manifest.head(max_samples) if max_samples is not None else manifest
    for _, row in limited.iterrows():
        row_dict = row.to_dict()
        sample_id = str(row_dict.get("sample_id") or row_dict.get("complex_id") or "")
        try:
            sample_path = _processed_path(row_dict, processed_root)
            with sample_path.open("rb") as f:
                sample = pickle.load(f)
            records.append({"sample": sample, "manifest": row_dict})
        except Exception as exc:
            errors.append(
                {
                    "dataset_name": "",
                    "sample_id": sample_id,
                    "receptor_scope": "",
                    "delta_angstrom": np.nan,
                    "unsupported_reason": "sample_load_failed",
                    "error": str(exc),
                }
            )
    return records, errors


def _processed_path(row: dict[str, Any], processed_root: Path) -> Path:
    value = row.get("processed_path")
    if value not in (None, ""):
        path = Path(str(value))
        if path.exists():
            return path
    sample_id = str(row.get("sample_id") or row.get("complex_id"))
    fallback = processed_root / "complexes" / f"{sample_id}.pkl"
    if fallback.exists():
        return fallback
    raise FileNotFoundError(f"Processed sample not found for {sample_id}: {value or fallback}")


def _read_sample_ids(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _select_manifest_rows(manifest: pd.DataFrame, sample_ids: list[str]) -> pd.DataFrame:
    if not sample_ids:
        return manifest.head(0)
    indexed = manifest.set_index("sample_id", drop=False)
    rows = [indexed.loc[sample_id] for sample_id in sample_ids if sample_id in indexed.index]
    return pd.DataFrame(rows, columns=manifest.columns) if rows else manifest.head(0)


def _scopes(scope_arg: str | None, detector_cfg: dict[str, Any]) -> list[str]:
    if scope_arg:
        return [value.strip() for value in scope_arg.split(",") if value.strip()]
    return [str(value) for value in detector_cfg.get("receptor_scopes", ["phase0_pocket8", "pocket10_all_atoms"])]


def _run_dataset(
    records: list[dict[str, Any]],
    dataset_name: str,
    scopes: list[str],
    deltas: list[float],
    config: dict[str, Any],
    *,
    dataset_names: list[str] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    detector_cfg = config.get("detector", {})
    rows: list[dict[str, Any]] = []
    attrs: list[dict[str, Any]] = []
    unsupported: list[dict[str, Any]] = []
    for record_idx, record in enumerate(records):
        sample = record["sample"]
        manifest_row = record["manifest"]
        current_dataset = dataset_names[record_idx] if dataset_names is not None else dataset_name
        for scope in scopes:
            for delta in deltas:
                try:
                    report = detect_clashes(
                        sample,
                        receptor_scope=scope,
                        delta_angstrom=float(delta),
                        severe_depth_threshold_angstrom=float(detector_cfg.get("severe_depth_threshold_angstrom", 0.4)),
                    )
                    attr = attribute_clashes_to_rgroups(
                        sample,
                        report,
                        alpha=float(detector_cfg.get("rgroup_score_alpha", 0.5)),
                        single_region_threshold=float(detector_cfg.get("single_region_dominant_ratio", 0.7)),
                        ambiguous_threshold=float(detector_cfg.get("ambiguous_region_dominant_ratio", 0.5)),
                    )
                    row = _clash_row(manifest_row, report, attr)
                    row["dataset_name"] = current_dataset
                    rows.append(row)
                    attrs.append(_attr_row(current_dataset, report, attr))
                    for reason in report.get("unsupported_reasons", []):
                        unsupported.append(_unsupported_row(current_dataset, sample, scope, delta, str(reason), ""))
                except Exception as exc:
                    unsupported.append(_unsupported_row(current_dataset, sample, scope, delta, "detector_failed", str(exc)))
    return rows, attrs, unsupported


def _clash_row(manifest_row: dict[str, Any], report: dict[str, Any], attr: dict[str, Any]) -> dict[str, Any]:
    return {
        "sample_id": report.get("sample_id") or manifest_row.get("sample_id"),
        "complex_id": manifest_row.get("complex_id") or report.get("sample_id"),
        "source": manifest_row.get("source"),
        "receptor_scope": report.get("receptor_scope"),
        "delta_angstrom": float(report.get("delta_angstrom") or 0.0),
        "num_clash_pairs": int(report.get("num_clash_pairs") or 0),
        "num_severe_clash_pairs": int(report.get("num_severe_clash_pairs") or 0),
        "total_clash_score": float(report.get("total_clash_score") or 0.0),
        "max_clash_depth": float(report.get("max_clash_depth") or 0.0),
        "dominant_region": attr.get("dominant_region", ""),
        "dominant_ratio": float(attr.get("dominant_ratio") or 0.0),
        "failure_type": attr.get("failure_type", ""),
        "recommended_action": attr.get("recommended_action", ""),
    }


def _attr_row(dataset_name: str, report: dict[str, Any], attr: dict[str, Any]) -> dict[str, Any]:
    return {
        "dataset_name": dataset_name,
        "sample_id": report.get("sample_id"),
        "receptor_scope": report.get("receptor_scope"),
        "delta_angstrom": float(report.get("delta_angstrom") or 0.0),
        "dominant_region": attr.get("dominant_region", ""),
        "dominant_ratio": float(attr.get("dominant_ratio") or 0.0),
        "failure_type": attr.get("failure_type", ""),
        "recommended_action": attr.get("recommended_action", ""),
        "region_scores_json": json.dumps(attr.get("region_scores", {}), ensure_ascii=False, sort_keys=True),
        "normalized_region_scores_json": json.dumps(
            attr.get("normalized_region_scores", {}),
            ensure_ascii=False,
            sort_keys=True,
        ),
        "top_regions_json": json.dumps(attr.get("top_regions", []), ensure_ascii=False),
    }


def _unsupported_row(
    dataset_name: str,
    sample: dict[str, Any],
    scope: str,
    delta: float,
    reason: str,
    error: str,
) -> dict[str, Any]:
    return {
        "dataset_name": dataset_name,
        "sample_id": sample.get("sample_id", ""),
        "receptor_scope": scope,
        "delta_angstrom": float(delta),
        "unsupported_reason": reason,
        "error": error,
    }


def _threshold_sensitivity(rows: pd.DataFrame) -> pd.DataFrame:
    if rows.empty:
        return pd.DataFrame(columns=SENSITIVITY_COLUMNS)
    result_rows: list[dict[str, Any]] = []
    group_cols = ["dataset_name", "receptor_scope", "delta_angstrom"]
    rows = rows.copy()
    rows["dataset_name"] = rows.get("dataset_name", "unknown")
    for key, group in rows.groupby(group_cols, dropna=False):
        dataset_name, scope, delta = key
        num_samples = int(group["sample_id"].nunique())
        num_with_severe = int((group["num_severe_clash_pairs"] > 0).sum())
        result_rows.append(
            {
                "dataset_name": dataset_name,
                "receptor_scope": scope,
                "delta_angstrom": float(delta),
                "num_samples": num_samples,
                "num_samples_with_severe_clash": num_with_severe,
                "severe_false_positive_rate": float(num_with_severe / num_samples) if num_samples else 0.0,
                "median_total_clash_score": float(group["total_clash_score"].median()) if not group.empty else 0.0,
                "max_total_clash_score": float(group["total_clash_score"].max()) if not group.empty else 0.0,
            }
        )
    return pd.DataFrame(result_rows, columns=SENSITIVITY_COLUMNS)


def _failure_type_counts(attrs: pd.DataFrame) -> pd.DataFrame:
    if attrs.empty:
        return pd.DataFrame(columns=FAILURE_TYPE_COLUMNS)
    counts = attrs.groupby(FAILURE_TYPE_COLUMNS[:-1], dropna=False).size().reset_index(name="count")
    return counts[FAILURE_TYPE_COLUMNS]


def _run_verifier_smoke(
    records: list[dict[str, Any]],
    config: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    unsupported: list[dict[str, Any]] = []
    detector_cfg = config.get("detector", {})
    old_scope = str(detector_cfg.get("default_old_scope", "phase0_pocket8"))
    default_delta = float(detector_cfg.get("delta_angstrom", 0.4))
    for record in records:
        sample = record["sample"]
        try:
            coords = np.asarray(sample["ligand"]["coords"], dtype=np.float32)
            result = verify_repair(sample, coords, coords, edit_region=None, config=config)
            rows.append(
                {
                    "sample_id": sample.get("sample_id", ""),
                    "old_clash_score_before": float(result["old_clash_score_before"]),
                    "old_clash_score_after": float(result["old_clash_score_after"]),
                    "old_clash_resolved": bool(result["old_clash_resolved"]),
                    "new_severe_clash_count": int(result["new_severe_clash_count"]),
                    "no_new_severe_clash": bool(result["no_new_severe_clash"]),
                    "scaffold_rmsd": float(result["scaffold_rmsd"]),
                    "non_edit_rmsd": float(result["non_edit_rmsd"]),
                    "geometry_valid": bool(result["geometry_valid"]),
                    "edit_compliance": bool(result["edit_compliance"]),
                    "repair_pass": bool(result["repair_pass"]),
                    "failure_reasons": json.dumps(result["failure_reasons"], ensure_ascii=False),
                }
            )
            for reason in result.get("unsupported_reasons", []):
                unsupported.append(_unsupported_row("verifier_smoke", sample, old_scope, default_delta, str(reason), ""))
        except Exception as exc:
            unsupported.append(_unsupported_row("verifier_smoke", sample, old_scope, default_delta, "verifier_failed", str(exc)))
    return rows, unsupported


def _summary(
    config: dict[str, Any],
    clean_df: pd.DataFrame,
    balanced_df: pd.DataFrame,
    verifier_df: pd.DataFrame,
    clean_records: list[dict[str, Any]],
    balanced_records: list[dict[str, Any]],
    default_delta: float,
    delta_sensitivity: list[float],
    scopes: list[str],
    full_receptor_enabled: bool,
    load_errors: list[dict[str, Any]],
) -> dict[str, Any]:
    detector_cfg = config.get("detector", {})
    old_scope = str(detector_cfg.get("default_old_scope", "phase0_pocket8"))
    new_scope = str(detector_cfg.get("default_new_scope", "pocket10_all_atoms"))
    clean_default = clean_df[
        (clean_df.get("receptor_scope") == old_scope)
        & (clean_df.get("delta_angstrom") == float(default_delta))
    ] if not clean_df.empty else clean_df
    balanced_default = balanced_df[
        (balanced_df.get("receptor_scope") == old_scope)
        & (balanced_df.get("delta_angstrom") == float(default_delta))
    ] if not balanced_df.empty else balanced_df
    return {
        "schema_version": str(config.get("schema_version", "phase1_v0_1")),
        "num_clean_pool_samples": int(len(clean_records)),
        "num_balanced_subset_samples": int(len(balanced_records)),
        "default_delta_angstrom": float(default_delta),
        "delta_sensitivity": [float(value) for value in delta_sensitivity],
        "receptor_scopes": scopes,
        "default_old_scope": old_scope,
        "default_new_scope": new_scope,
        "full_receptor_enabled": bool(full_receptor_enabled),
        "clean_pool_severe_false_positive_count": int((clean_default.get("num_severe_clash_pairs", pd.Series(dtype=int)) > 0).sum()),
        "balanced_subset_severe_false_positive_count": int((balanced_default.get("num_severe_clash_pairs", pd.Series(dtype=int)) > 0).sum()),
        "verifier_smoke_total_count": int(len(verifier_df)),
        "verifier_smoke_pass_count": int(verifier_df.get("repair_pass", pd.Series(dtype=bool)).sum()) if not verifier_df.empty else 0,
        "num_load_errors": int(len(load_errors)),
        "phase1_acceptance_status": "complete" if not load_errors else "incomplete",
    }


if __name__ == "__main__":
    raise SystemExit(main())
