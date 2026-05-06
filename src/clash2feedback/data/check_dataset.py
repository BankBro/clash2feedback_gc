from __future__ import annotations

import json
import pickle
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from clash2feedback.utils.files import ensure_dir


REQUIRED_TOP_LEVEL_FIELDS = {
    "schema_version",
    "sample_id",
    "complex_id",
    "paths",
    "metadata",
    "protein",
    "ligand",
    "pocket",
    "scaffold",
    "rgroups",
    "masks",
    "sanity",
    "software_versions",
}


def check_processed_sample(sample_path: str | Path, config: dict[str, Any] | None = None) -> dict[str, Any]:
    path = Path(sample_path)
    errors: list[str] = []
    try:
        with path.open("rb") as f:
            sample = pickle.load(f)
    except Exception as exc:
        return {
            "sample_id": path.stem,
            "processed_path": str(path),
            "load_ok": False,
            "phase0_usable": False,
            "errors": f"load_failed:{exc}",
        }

    missing = sorted(REQUIRED_TOP_LEVEL_FIELDS - set(sample))
    if missing:
        errors.append("missing_fields:" + ",".join(missing))

    ligand = sample.get("ligand", {})
    protein = sample.get("protein", {})
    pocket = sample.get("pocket", {})
    masks = sample.get("masks", {})
    sanity = sample.get("sanity", {})
    _check_coord_shape("ligand_coords", ligand.get("coords"), errors)
    _check_coord_shape("protein_coords", protein.get("coords"), errors)
    _check_coord_shape("pocket_coords", pocket.get("coords"), errors)
    ligand_atoms = int(ligand.get("num_atoms") or 0)
    protein_atoms = int(protein.get("num_atoms") or 0)
    if _length(masks.get("ligand_scaffold_mask")) != ligand_atoms:
        errors.append("ligand_scaffold_mask_length_mismatch")
    if _length(masks.get("ligand_is_rgroup")) != ligand_atoms:
        errors.append("ligand_is_rgroup_length_mismatch")
    if _length(masks.get("heavy_atom_mask")) != ligand_atoms:
        errors.append("heavy_atom_mask_length_mismatch")
    if _length(masks.get("pocket_atom_mask")) != protein_atoms:
        errors.append("pocket_atom_mask_length_mismatch")

    num_valid_rgroups = int(sanity.get("num_valid_rgroups") or 0)
    phase0_usable = (
        not errors
        and bool(sanity.get("valid_ligand"))
        and bool(sanity.get("pocket_nonempty"))
        and bool(sanity.get("scaffold_success"))
        and num_valid_rgroups >= int((config or {}).get("rgroup", {}).get("min_valid_rgroups_per_complex", 2))
        and bool(sanity.get("basic_clash_screen_pass"))
    )

    return {
        "sample_id": sample.get("sample_id", path.stem),
        "complex_id": sample.get("complex_id", path.stem),
        "source": sample.get("source"),
        "processed_path": str(path),
        "protein_path": sample.get("paths", {}).get("raw_protein_path"),
        "ligand_path": sample.get("paths", {}).get("raw_ligand_path"),
        "load_ok": True,
        "schema_version": sample.get("schema_version"),
        "valid_ligand": bool(sanity.get("valid_ligand")),
        "pocket_nonempty": bool(sanity.get("pocket_nonempty")),
        "scaffold_success": bool(sanity.get("scaffold_success")),
        "ligand_heavy_atoms": int(ligand.get("num_heavy_atoms") or 0),
        "num_pocket_atoms_6A": int(pocket.get("num_atoms_6A") or 0),
        "num_pocket_atoms_8A": int(pocket.get("num_atoms_8A") or pocket.get("num_pocket_atoms") or 0),
        "min_ligand_protein_distance": _float_or_nan(sanity.get("min_ligand_protein_distance")),
        "num_obvious_clash_pairs": int(sanity.get("num_obvious_clash_pairs") or 0),
        "num_pairs_below_1_0": int(sanity.get("num_pairs_below_1_0") or 0),
        "num_pairs_below_1_2": int(sanity.get("num_pairs_below_1_2") or 0),
        "num_pairs_below_1_5": int(sanity.get("num_pairs_below_1_5") or 0),
        "num_rgroups": len(sample.get("rgroups", [])),
        "num_valid_rgroups": num_valid_rgroups,
        "num_single_anchor_rgroups": int(sanity.get("num_single_anchor_rgroups") or 0),
        "scaffold_num_atoms": int(sample.get("scaffold", {}).get("num_atoms") or 0),
        "basic_clash_screen_pass": bool(sanity.get("basic_clash_screen_pass")),
        "phase0_usable": phase0_usable,
        "split_group": sample.get("metadata", {}).get("split_group"),
        "split_group_source": sample.get("metadata", {}).get("split_group_source"),
        "errors": ";".join(errors),
    }


def check_processed_dataset(
    processed_root: str | Path,
    manifest_path: str | Path,
    report_dir: str | Path,
    config: dict[str, Any] | None = None,
) -> dict[str, pd.DataFrame]:
    processed_dir = Path(processed_root)
    report_path = ensure_dir(report_dir)
    manifest_file = Path(manifest_path)
    if manifest_file.exists():
        manifest = pd.read_parquet(manifest_file)
        sample_paths = [Path(path) for path in manifest.get("processed_path", [])]
    else:
        manifest = pd.DataFrame()
        sample_paths = sorted((processed_dir / "complexes").glob("*.pkl"))

    rows = [check_processed_sample(path, config=config) for path in sample_paths]
    dataset_check = pd.DataFrame(rows)
    dataset_check.to_csv(report_path / "dataset_check.csv", index=False)

    failed_path = report_path / "failed_cases.csv"
    if failed_path.exists():
        failed_cases = pd.read_csv(failed_path)
    else:
        failed_cases = pd.DataFrame(
            columns=["complex_id", "source", "protein_path", "ligand_path", "failure_reason", "stage", "message"]
        )
        failed_cases.to_csv(failed_path, index=False)

    threshold = _threshold_calibration(manifest, dataset_check, failed_cases)
    threshold.to_csv(report_path / "threshold_calibration.csv", index=False)

    failure_counts = _failure_reason_counts(failed_cases)
    failure_counts.to_csv(report_path / "failure_reason_counts.csv", index=False)

    summary = _summary_dict(manifest, dataset_check, failed_cases, threshold, failure_counts)
    with (report_path / "summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    visual_check = _visual_check_list(manifest, dataset_check, config or {})
    visual_check.to_csv(report_path / "visual_check_list.csv", index=False)
    _manual_check_template(visual_check).to_csv(report_path / "manual_check_template.csv", index=False)
    return {
        "dataset_check": dataset_check,
        "failed_cases": failed_cases,
        "threshold_calibration": threshold,
        "failure_reason_counts": failure_counts,
    }


def _check_coord_shape(name: str, coords: Any, errors: list[str]) -> None:
    if coords is None:
        errors.append(f"{name}_missing")
        return
    array = np.asarray(coords)
    if array.ndim != 2 or array.shape[1] != 3:
        errors.append(f"{name}_shape_invalid")
    if not np.isfinite(array).all():
        errors.append(f"{name}_not_finite")


def _length(value: Any) -> int:
    if value is None:
        return -1
    return len(value)


def _float_or_nan(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


THRESHOLD_COLUMNS = [
    "complex_id",
    "sample_id",
    "source",
    "phase0_usable",
    "failure_reason",
    "ligand_heavy_atoms",
    "num_pocket_atoms_6A",
    "num_pocket_atoms_8A",
    "min_ligand_protein_distance",
    "num_obvious_clash_pairs",
    "num_pairs_below_1_0",
    "num_pairs_below_1_2",
    "num_pairs_below_1_5",
    "num_rgroups",
    "num_valid_rgroups",
    "num_single_anchor_rgroups",
    "scaffold_num_atoms",
    "split_group",
    "split_group_source",
]


def _threshold_calibration(
    manifest: pd.DataFrame,
    dataset_check: pd.DataFrame,
    failed_cases: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    manifest_by_sample = _index_by(manifest, "sample_id")
    for _, check_row in dataset_check.iterrows():
        sample_id = str(check_row.get("sample_id"))
        manifest_row = manifest_by_sample.get(sample_id, {})
        row: dict[str, Any] = {}
        for column in THRESHOLD_COLUMNS:
            row[column] = _first_value(check_row.get(column), manifest_row.get(column))
        row["sample_id"] = sample_id
        row["complex_id"] = _first_value(check_row.get("complex_id"), manifest_row.get("complex_id"), sample_id)
        row["phase0_usable"] = bool(check_row.get("phase0_usable"))
        row["failure_reason"] = _first_value(manifest_row.get("failure_reason"), "")
        rows.append(row)

    for _, failed_row in failed_cases.iterrows():
        row = {column: None for column in THRESHOLD_COLUMNS}
        row.update(
            {
                "complex_id": failed_row.get("complex_id"),
                "sample_id": failed_row.get("complex_id"),
                "source": failed_row.get("source"),
                "phase0_usable": False,
                "failure_reason": failed_row.get("failure_reason"),
            }
        )
        rows.append(row)

    return pd.DataFrame(rows, columns=THRESHOLD_COLUMNS)


def _failure_reason_counts(failed_cases: pd.DataFrame) -> pd.DataFrame:
    if "failure_reason" not in failed_cases.columns or failed_cases.empty:
        return pd.DataFrame(columns=["failure_reason", "count"])
    counts = failed_cases["failure_reason"].fillna("unknown").astype(str).value_counts().reset_index()
    counts.columns = ["failure_reason", "count"]
    return counts


def _summary_dict(
    manifest: pd.DataFrame,
    dataset_check: pd.DataFrame,
    failed_cases: pd.DataFrame,
    threshold: pd.DataFrame,
    failure_counts: pd.DataFrame,
) -> dict[str, Any]:
    usable_count = int(dataset_check.get("phase0_usable", pd.Series(dtype=bool)).sum())
    summary = {
        "num_candidate_complexes": int(len(manifest) + len(failed_cases)),
        "num_manifest_rows": int(len(manifest)),
        "num_checked_samples": int(len(dataset_check)),
        "num_processed": int(len(manifest)),
        "num_failed_cases": int(len(failed_cases)),
        "num_phase0_usable": usable_count,
        "phase0_acceptance_status": "complete" if usable_count >= 20 else "incomplete",
        "all_load_ok": bool(dataset_check.get("load_ok", pd.Series(dtype=bool)).all()) if len(dataset_check) else True,
        "failure_reason_counts": failure_counts.to_dict(orient="records"),
        "distributions": {
            "ligand_heavy_atoms": _numeric_summary(threshold, "ligand_heavy_atoms"),
            "num_pocket_atoms_8A": _numeric_summary(threshold, "num_pocket_atoms_8A"),
            "min_ligand_protein_distance": _numeric_summary(threshold, "min_ligand_protein_distance"),
            "num_obvious_clash_pairs": _numeric_summary(threshold, "num_obvious_clash_pairs"),
            "num_valid_rgroups": _numeric_summary(threshold, "num_valid_rgroups"),
        },
        "split_group_source_counts": _value_counts(threshold, "split_group_source"),
    }
    return summary


def _numeric_summary(df: pd.DataFrame, column: str) -> dict[str, float | int | None]:
    if column not in df.columns:
        return {"count": 0}
    values = pd.to_numeric(df[column], errors="coerce").dropna()
    if values.empty:
        return {"count": 0}
    return {
        "count": int(values.count()),
        "min": float(values.min()),
        "p25": float(values.quantile(0.25)),
        "median": float(values.median()),
        "p75": float(values.quantile(0.75)),
        "max": float(values.max()),
    }


def _value_counts(df: pd.DataFrame, column: str) -> dict[str, int]:
    if column not in df.columns:
        return {}
    return {str(key): int(value) for key, value in df[column].dropna().astype(str).value_counts().items()}


def _index_by(df: pd.DataFrame, column: str) -> dict[str, dict[str, Any]]:
    if column not in df.columns:
        return {}
    return {str(row[column]): row.to_dict() for _, row in df.iterrows()}


def _first_value(*values: Any) -> Any:
    for value in values:
        if value is None:
            continue
        try:
            if pd.isna(value):
                continue
        except (TypeError, ValueError):
            pass
        if value == "":
            continue
        return value
    return None


def _visual_check_list(
    manifest: pd.DataFrame,
    dataset_check: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    min_count = int(config.get("visual_check", {}).get("num_manual_check", 5))
    if "phase0_usable" not in dataset_check.columns or "sample_id" not in dataset_check.columns:
        return pd.DataFrame(columns=VISUAL_CHECK_COLUMNS)
    usable_ids = set(dataset_check.loc[dataset_check["phase0_usable"] == True, "sample_id"])  # noqa: E712
    if "sample_id" not in manifest:
        return pd.DataFrame(columns=VISUAL_CHECK_COLUMNS)
    rows = manifest[manifest["sample_id"].isin(usable_ids)].copy()
    if rows.empty:
        return pd.DataFrame(columns=VISUAL_CHECK_COLUMNS)

    check_by_sample = _index_by(dataset_check, "sample_id")
    for column in [
        "num_pocket_atoms_8A",
        "num_rgroups",
        "num_valid_rgroups",
        "num_single_anchor_rgroups",
        "scaffold_success",
        "basic_clash_screen_pass",
        "min_ligand_protein_distance",
    ]:
        if column not in rows.columns:
            rows[column] = rows["sample_id"].map(lambda sample_id: check_by_sample.get(str(sample_id), {}).get(column))

    rows["recommended_check_priority"] = rows.apply(lambda row: _visual_priority(row, config), axis=1)
    rows["manual_check_status"] = "unchecked"
    rows["manual_notes"] = ""
    rows["_priority_order"] = rows["recommended_check_priority"].map({"high": 0, "medium": 1, "low": 2}).fillna(3)
    rows = rows.sort_values(["_priority_order", "sample_id"]).head(max(min_count, len(rows)))
    return rows[[column for column in VISUAL_CHECK_COLUMNS if column in rows.columns]]


VISUAL_CHECK_COLUMNS = [
    "complex_id",
    "sample_id",
    "source",
    "protein_path",
    "ligand_path",
    "processed_path",
    "num_pocket_atoms_8A",
    "num_rgroups",
    "num_valid_rgroups",
    "num_single_anchor_rgroups",
    "scaffold_success",
    "basic_clash_screen_pass",
    "recommended_check_priority",
    "manual_check_status",
    "manual_notes",
]


def _visual_priority(row: pd.Series, config: dict[str, Any]) -> str:
    min_valid = int(config.get("rgroup", {}).get("min_valid_rgroups_per_complex", 2))
    min_pocket = int(config.get("pocket", {}).get("min_atoms_8A", 50))
    max_pocket = int(config.get("pocket", {}).get("max_atoms_8A", 3000))
    pocket_atoms = _safe_int(row.get("num_pocket_atoms_8A"))
    valid_rgroups = _safe_int(row.get("num_valid_rgroups"))
    min_distance = _float_or_nan(row.get("min_ligand_protein_distance"))
    if (
        valid_rgroups <= min_valid
        or pocket_atoms <= min_pocket + 25
        or pocket_atoms >= max_pocket - 250
        or (np.isfinite(min_distance) and min_distance < 1.6)
    ):
        return "high"
    if valid_rgroups <= min_valid + 1 or (np.isfinite(min_distance) and min_distance < 2.0):
        return "medium"
    return "low"


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _manual_check_template(visual_check: pd.DataFrame) -> pd.DataFrame:
    template = visual_check.copy()
    for column in [
        "ligand_in_pocket_ok",
        "pocket_reasonable_ok",
        "scaffold_reasonable_ok",
        "rgroups_reasonable_ok",
        "anchors_reasonable_ok",
        "notes",
    ]:
        template[column] = ""
    return template
