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
        "processed_path": str(path),
        "load_ok": True,
        "schema_version": sample.get("schema_version"),
        "valid_ligand": bool(sanity.get("valid_ligand")),
        "pocket_nonempty": bool(sanity.get("pocket_nonempty")),
        "scaffold_success": bool(sanity.get("scaffold_success")),
        "num_rgroups": len(sample.get("rgroups", [])),
        "num_valid_rgroups": num_valid_rgroups,
        "num_single_anchor_rgroups": int(sanity.get("num_single_anchor_rgroups") or 0),
        "basic_clash_screen_pass": bool(sanity.get("basic_clash_screen_pass")),
        "phase0_usable": phase0_usable,
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

    summary = {
        "num_manifest_rows": int(len(manifest)),
        "num_checked_samples": int(len(dataset_check)),
        "num_phase0_usable": int(dataset_check.get("phase0_usable", pd.Series(dtype=bool)).sum()),
        "num_failed_cases": int(len(failed_cases)),
        "all_load_ok": bool(dataset_check.get("load_ok", pd.Series(dtype=bool)).all()) if len(dataset_check) else True,
    }
    with (report_path / "summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    visual_check = _visual_check_list(manifest, dataset_check, config or {})
    visual_check.to_csv(report_path / "visual_check_list.csv", index=False)
    _manual_check_template(visual_check).to_csv(report_path / "manual_check_template.csv", index=False)
    return {"dataset_check": dataset_check, "failed_cases": failed_cases}


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


def _visual_check_list(
    manifest: pd.DataFrame,
    dataset_check: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    count = int(config.get("visual_check", {}).get("num_manual_check", 5))
    if "phase0_usable" not in dataset_check.columns or "sample_id" not in dataset_check.columns:
        return pd.DataFrame(columns=["sample_id", "complex_id", "processed_path", "protein_path", "ligand_path"])
    usable_ids = set(dataset_check.loc[dataset_check["phase0_usable"] == True, "sample_id"])  # noqa: E712
    rows = manifest[manifest["sample_id"].isin(usable_ids)].head(count) if "sample_id" in manifest else pd.DataFrame()
    columns = ["sample_id", "complex_id", "processed_path", "protein_path", "ligand_path"]
    if rows.empty:
        return pd.DataFrame(columns=columns)
    return rows[[column for column in columns if column in rows.columns]]


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
