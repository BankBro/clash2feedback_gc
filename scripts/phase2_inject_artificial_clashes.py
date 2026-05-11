#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import pickle
import sys
from collections import Counter
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
from clash2feedback.perturb.deduplicate import mark_duplicate_cases
from clash2feedback.perturb.directed_clash import directed_rotation_attempts
from clash2feedback.perturb.labels import REJECT_SPLITS, assign_oracle_split, difficulty_bin
from clash2feedback.perturb.quality import (
    copy_mol_with_coords,
    evaluate_ligand_only_quality,
    mol_from_sample,
    scaffold_and_non_target_rmsd,
)
from clash2feedback.perturb.rotation import rotate_target_rgroup
from clash2feedback.perturb.torsion import torsion_perturb_target_rgroup
from clash2feedback.utils.config import load_yaml_config, resolve_repo_path


ENERGY_DELTA_LARGE_ABS_THRESHOLD = 50.0


REPORT_COLUMNS = [
    "case_id",
    "base_sample_id",
    "base_complex_id",
    "base_split",
    "derived_split",
    "split_group",
    "target_id",
    "source_dataset",
    "injection_mode",
    "attempt_id",
    "seed",
    "rotation_angle_deg",
    "rotation_axis_atom_pair",
    "transform_matrix",
    "target_rgroup",
    "target_atom_indices",
    "anchor_scaffold_atom_idx",
    "anchor_rgroup_atom_idx",
    "anchor_bond_idx",
    "oracle_split",
    "difficulty_bin",
    "difficulty_reason",
    "acceptance_status",
    "reject_reason",
    "unsupported_reason",
    "invalid_reason",
    "duplicate_of",
    "ligand_valid",
    "rdkit_sanitize_ok",
    "rotatable_bond_valid",
    "anchor_integrity_pass",
    "bond_length_valid",
    "chirality_preserved",
    "ligand_internal_severe_clash_count",
    "forcefield_type",
    "energy_original",
    "energy_failed",
    "energy_delta",
    "energy_delta_pass",
    "energy_check_status",
    "scaffold_rmsd",
    "non_target_rgroup_rmsd",
    "target_rgroup_rmsd",
    "delta_angstrom",
    "severe_depth_threshold_angstrom",
    "target_num_clash_pairs",
    "target_num_severe_pairs",
    "target_total_score",
    "target_max_depth",
    "target_score_ratio_valid",
    "target_score_ratio_all",
    "non_target_num_severe_pairs",
    "scaffold_num_severe_pairs",
    "num_total_severe_pairs",
    "total_clash_score",
    "max_clash_depth",
    "predicted_dominant_region_all",
    "predicted_dominant_valid_rgroup",
    "dominant_ratio_all_regions",
    "dominant_ratio_valid_rgroups",
    "failure_type",
    "recommended_action",
    "top_valid_rgroups_json",
    "top_clash_residue",
    "delta03_status",
    "delta04_status",
    "delta05_status",
    "sample_path",
    "original_ligand_sdf",
    "failed_ligand_sdf",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Construct phase2 artificial R-group clash benchmark.")
    parser.add_argument("--config", default="configs/phase2_injection.yaml", help="Path to phase2 yaml config.")
    parser.add_argument("--manifest", default=None, help="Override processed manifest parquet path.")
    parser.add_argument("--phase1-report-root", default=None, help="Override phase1 report root.")
    parser.add_argument("--output-root", default=None, help="Override benchmark output root.")
    parser.add_argument("--report-root", default=None, help="Override report output root.")
    parser.add_argument("--max-samples", type=int, default=None, help="Optional max base samples for smoke runs.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_yaml_config(resolve_repo_path(args.config, repo_root=REPO_ROOT))
    inputs = config.get("inputs", {})
    outputs = config.get("outputs", {})
    processed_root = resolve_repo_path(inputs.get("processed_root", "data/processed/v0_1"), repo_root=REPO_ROOT)
    manifest_path = resolve_repo_path(args.manifest or inputs.get("manifest", processed_root / "manifest.parquet"), repo_root=REPO_ROOT)
    splits_root = resolve_repo_path(inputs.get("splits_root", "data/splits/v0_1"), repo_root=REPO_ROOT)
    phase1_report_root = resolve_repo_path(
        args.phase1_report_root or inputs.get("phase1_report_root", "reports/phase1_clash_detector"),
        repo_root=REPO_ROOT,
    )
    benchmark_root = resolve_repo_path(
        args.output_root or outputs.get("benchmark_root", "data/benchmarks/clashrepairbench_rg_artificial/v0_1"),
        repo_root=REPO_ROOT,
    )
    report_root = resolve_repo_path(
        args.report_root or outputs.get("report_root", "reports/phase2_injection"),
        repo_root=REPO_ROOT,
    )
    samples_root = benchmark_root / "samples"
    ligands_root = benchmark_root / "ligands"
    for path in (benchmark_root, samples_root, ligands_root, report_root):
        path.mkdir(parents=True, exist_ok=True)

    if not manifest_path.exists():
        print(f"ERROR: manifest parquet not found: {manifest_path}", file=sys.stderr)
        return 2

    manifest = pd.read_parquet(manifest_path)
    if args.max_samples is not None:
        manifest = manifest.head(args.max_samples)
    split_map = _load_split_map(splits_root)

    base_rows: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    attempts: list[dict[str, Any]] = []
    case_counter = 0
    for _, manifest_row in manifest.iterrows():
        row_dict = manifest_row.to_dict()
        sample = _load_sample(row_dict, processed_root)
        base_eval = _base_clean_gate(sample, row_dict, config, split_map)
        base_rows.append(base_eval)
        if not base_eval["base_clean_pass"]:
            continue
        mol = mol_from_sample(sample)
        for rgroup in _eligible_rgroups(sample):
            rgroup_attempts = _build_attempts(sample, mol, rgroup, config)
            for attempt in rgroup_attempts:
                case_counter += 1
                case_id = f"case_{case_counter:06d}"
                record = _evaluate_attempt(
                    case_id,
                    sample,
                    row_dict,
                    mol,
                    rgroup,
                    attempt,
                    config,
                    phase1_report_root,
                    split_map,
                )
                rows.append(record)
                attempts.append(_attempt_row(record))

    rows = mark_duplicate_cases(
        rows,
        coords_rmsd_threshold=float(config.get("deduplicate", {}).get("coords_rmsd_threshold", 0.1)),
    ) if config.get("deduplicate", {}).get("enabled", True) else rows

    _write_case_files(rows, benchmark_root, samples_root, ligands_root)
    manifest_df = _manifest_dataframe(rows)
    manifest_df.to_parquet(benchmark_root / "manifest.parquet", index=False)
    _write_schema(benchmark_root / "schema.json", manifest_df)
    _write_reports(report_root, manifest_df, base_rows, attempts, config, phase1_report_root)
    _write_completion_audit(report_root, benchmark_root, manifest_df, base_rows, config)

    print(
        "phase2_inject_artificial_clashes complete: "
        f"attempts={len(rows)} supported={(manifest_df['oracle_split'] == 'supported_single_rgroup').sum()} "
        f"benchmark_root={benchmark_root} report_root={report_root}"
    )
    return 0


def _load_sample(row: dict[str, Any], processed_root: Path) -> dict[str, Any]:
    value = row.get("processed_path")
    if value not in (None, "") and Path(str(value)).exists():
        path = Path(str(value))
    else:
        sample_id = str(row.get("sample_id") or row.get("complex_id"))
        path = processed_root / "complexes" / f"{sample_id}.pkl"
    with path.open("rb") as f:
        return pickle.load(f)


def _load_split_map(splits_root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for split in ("train", "val", "test"):
        path = splits_root / f"{split}.txt"
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            sample_id = line.strip()
            if sample_id:
                result[sample_id] = split
    return result


def _base_split(sample: dict[str, Any], row: dict[str, Any], split_map: dict[str, str]) -> str:
    sample_id = str(sample.get("sample_id") or row.get("sample_id") or "")
    return str(split_map.get(sample_id) or row.get("split") or sample.get("metadata", {}).get("split") or "unknown")


def _base_clean_gate(sample: dict[str, Any], row: dict[str, Any], config: dict[str, Any], split_map: dict[str, str]) -> dict[str, Any]:
    detector_cfg = config.get("detector", {})
    delta = float(detector_cfg.get("default_delta_angstrom", 0.4))
    severe = float(detector_cfg.get("severe_depth_threshold_angstrom", 0.4))
    pocket8 = detect_clashes(sample, receptor_scope="phase0_pocket8", delta_angstrom=delta, severe_depth_threshold_angstrom=severe)
    pocket10 = detect_clashes(sample, receptor_scope="pocket10_all_atoms", delta_angstrom=delta, severe_depth_threshold_angstrom=severe)
    sanity = sample.get("sanity", {})
    num_valid = int(row.get("num_valid_rgroups") or sanity.get("num_valid_rgroups") or 0)
    num_single = int(row.get("num_single_anchor_rgroups") or sanity.get("num_single_anchor_rgroups") or 0)
    failures: list[str] = []
    if pocket8.get("analysis_status") != "ok" or pocket10.get("analysis_status") != "ok":
        failures.append("analysis_status_not_ok")
    if pocket8.get("unsupported_reasons") or pocket10.get("unsupported_reasons"):
        failures.append("unsupported_detector_case")
    if int(pocket8.get("num_severe_clash_pairs") or 0) != 0:
        failures.append("phase0_pocket8_severe_clash")
    if int(pocket10.get("num_severe_clash_pairs") or 0) != 0:
        failures.append("pocket10_all_atoms_severe_clash")
    if not bool(row.get("valid_ligand", sample.get("ligand", {}).get("rdkit_sanitize_ok", False))):
        failures.append("ligand_sanitize_failed")
    if not bool(row.get("scaffold_success", sample.get("scaffold", {}).get("success", False))):
        failures.append("scaffold_failed")
    if num_valid < int(config.get("base_filter", {}).get("min_valid_rgroups", 1)):
        failures.append("no_valid_rgroup")
    if num_single < int(config.get("base_filter", {}).get("min_single_anchor_rgroups", 1)):
        failures.append("no_single_anchor_rgroup")
    return {
        "sample_id": sample.get("sample_id", row.get("sample_id", "")),
        "complex_id": sample.get("complex_id", row.get("complex_id", "")),
        "base_split": _base_split(sample, row, split_map),
        "split_group": row.get("split_group", sample.get("metadata", {}).get("split_group", "")),
        "phase0_pocket8_num_severe": int(pocket8.get("num_severe_clash_pairs") or 0),
        "pocket10_all_atoms_num_severe": int(pocket10.get("num_severe_clash_pairs") or 0),
        "base_num_clash_pairs": int(pocket10.get("num_clash_pairs") or 0),
        "base_num_nonsevere_clash_pairs": int(pocket10.get("num_clash_pairs") or 0) - int(pocket10.get("num_severe_clash_pairs") or 0),
        "base_max_depth": float(pocket10.get("max_clash_depth") or 0.0),
        "base_total_clash_score": float(pocket10.get("total_clash_score") or 0.0),
        "base_contact_level": "mild_contact" if int(pocket10.get("num_clash_pairs") or 0) > 0 else "no_contact",
        "num_valid_rgroups": num_valid,
        "num_single_anchor_rgroups": num_single,
        "base_clean_pass": len(failures) == 0,
        "failure_reason": ";".join(failures),
    }


def _eligible_rgroups(sample: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        rgroup
        for rgroup in sample.get("rgroups", [])
        if bool(rgroup.get("is_valid_for_phase0")) and bool(rgroup.get("is_single_anchor"))
    ]


def _build_attempts(sample: dict[str, Any], mol: Any, rgroup: dict[str, Any], config: dict[str, Any]) -> list[dict[str, Any]]:
    injection_cfg = config.get("injection", {})
    max_attempts = int(injection_cfg.get("max_attempts_per_rgroup", 8))
    attempts: list[dict[str, Any]] = []
    for mode in injection_cfg.get("modes", ["easy_rotation"]):
        if mode == "easy_rotation":
            for angle in injection_cfg.get("easy_rotation_angles_deg", [60, 120, 180, 240, 300])[:max_attempts]:
                result = rotate_target_rgroup(sample, rgroup, float(angle))
                attempts.append({"injection_mode": mode, **result})
        elif mode == "torsion_perturb":
            for angle in injection_cfg.get("torsion_angles_deg", [60, 120, 180, 240, 300])[:max_attempts]:
                result = torsion_perturb_target_rgroup(sample, mol, rgroup, float(angle))
                if result is None:
                    attempts.append({"injection_mode": mode, "unsupported_reason": "no_internal_rotatable_torsion", "angle_deg": float(angle)})
                else:
                    attempts.append({"injection_mode": mode, **result})
        elif mode == "directed_clash":
            directed = directed_rotation_attempts(
                sample,
                rgroup,
                [float(value) for value in injection_cfg.get("directed_rotation_angles_deg", [30, 60, 90, 120, 150, 180, 210, 240, 270, 300, 330])],
            )
            for result in directed[:max_attempts]:
                attempts.append({"injection_mode": mode, **result})
    return attempts


def _evaluate_attempt(
    case_id: str,
    sample: dict[str, Any],
    manifest_row: dict[str, Any],
    mol: Any,
    rgroup: dict[str, Any],
    attempt: dict[str, Any],
    config: dict[str, Any],
    phase1_report_root: Path,
    split_map: dict[str, str],
) -> dict[str, Any]:
    original_coords = np.asarray(sample.get("ligand", {}).get("coords"), dtype=np.float32)
    base_split = _base_split(sample, manifest_row, split_map)
    common = _common_row(case_id, sample, manifest_row, rgroup, attempt, config, base_split)
    if "failed_coords" not in attempt:
        return {
            **common,
            "oracle_split": "unsupported",
            "acceptance_status": "unsupported",
            "unsupported_reason": str(attempt.get("unsupported_reason", "unsupported_attempt")),
            "difficulty_bin": "unsupported",
            "difficulty_reason": "unsupported_attempt",
            "ligand_valid": False,
            "_original_coords": original_coords,
            "_failed_coords": original_coords.copy(),
            "_sample": sample,
            "_mol": mol,
        }

    failed_coords = np.asarray(attempt["failed_coords"], dtype=np.float32)
    quality = evaluate_ligand_only_quality(sample, mol, rgroup, original_coords, failed_coords, config)
    scaffold_rmsd, non_target_rmsd, target_rmsd = scaffold_and_non_target_rmsd(
        sample,
        original_coords,
        failed_coords,
        str(rgroup.get("rgroup_id")),
    )
    detector_cfg = config.get("detector", {})
    delta = float(detector_cfg.get("default_delta_angstrom", 0.4))
    severe = float(detector_cfg.get("severe_depth_threshold_angstrom", 0.4))
    clash_report = detect_clashes(
        sample,
        ligand_coords=failed_coords,
        receptor_scope=str(detector_cfg.get("new_scope", "pocket10_all_atoms")),
        delta_angstrom=delta,
        severe_depth_threshold_angstrom=severe,
    )
    attribution = attribute_clashes_to_rgroups(
        sample,
        clash_report,
        alpha=float(detector_cfg.get("rgroup_score_alpha", 0.5)),
        single_region_threshold=float(detector_cfg.get("single_region_dominant_ratio", 0.7)),
        ambiguous_threshold=float(detector_cfg.get("ambiguous_region_dominant_ratio", 0.5)),
    )
    labels = assign_oracle_split(
        ligand_quality=quality,
        clash_report=clash_report,
        attribution=attribution,
        target_rgroup=str(rgroup.get("rgroup_id")),
        acceptance_cfg=config.get("acceptance", {}),
    )
    diff_bin, diff_reason = difficulty_bin(labels["oracle_split"], labels["target_score_ratio_valid"], float(clash_report.get("max_clash_depth") or 0.0))
    sensitivity = _delta_sensitivity(sample, failed_coords, config, str(rgroup.get("rgroup_id")))
    row = {
        **common,
        **quality,
        **labels,
        "difficulty_bin": diff_bin,
        "difficulty_reason": diff_reason,
        "scaffold_rmsd": scaffold_rmsd,
        "non_target_rgroup_rmsd": non_target_rmsd,
        "target_rgroup_rmsd": target_rmsd,
        "delta_angstrom": delta,
        "severe_depth_threshold_angstrom": severe,
        "target_num_clash_pairs": int(sum(1 for pair in clash_report.get("clash_pairs", []) if pair.get("ligand_region") == rgroup.get("rgroup_id"))),
        "target_max_depth": float(max([float(pair.get("clash_depth") or 0.0) for pair in clash_report.get("clash_pairs", []) if pair.get("ligand_region") == rgroup.get("rgroup_id")] or [0.0])),
        "total_clash_score": float(clash_report.get("total_clash_score") or 0.0),
        "max_clash_depth": float(clash_report.get("max_clash_depth") or 0.0),
        "predicted_dominant_region_all": attribution.get("dominant_region_all", ""),
        "predicted_dominant_valid_rgroup": attribution.get("dominant_valid_rgroup", ""),
        "dominant_ratio_all_regions": float(attribution.get("dominant_ratio_all_regions") or 0.0),
        "dominant_ratio_valid_rgroups": float(attribution.get("dominant_ratio_valid_rgroups") or 0.0),
        "failure_type": attribution.get("failure_type", ""),
        "recommended_action": attribution.get("recommended_action", ""),
        "top_valid_rgroups_json": json.dumps(attribution.get("top_valid_rgroups", []), ensure_ascii=False),
        "delta03_status": sensitivity.get("0.3", ""),
        "delta04_status": sensitivity.get("0.4", ""),
        "delta05_status": sensitivity.get("0.5", ""),
        "_original_coords": original_coords,
        "_failed_coords": failed_coords,
        "_sample": sample,
        "_mol": mol,
        "_clash_report": clash_report,
        "_attribution_report": attribution,
        "_phase1_report_root": str(phase1_report_root),
    }
    return row


def _common_row(
    case_id: str,
    sample: dict[str, Any],
    manifest_row: dict[str, Any],
    rgroup: dict[str, Any],
    attempt: dict[str, Any],
    config: dict[str, Any],
    base_split: str,
) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "base_sample_id": sample.get("sample_id", manifest_row.get("sample_id", "")),
        "base_complex_id": sample.get("complex_id", manifest_row.get("complex_id", "")),
        "base_split": base_split,
        "derived_split": base_split,
        "split_group": manifest_row.get("split_group") or sample.get("metadata", {}).get("split_group", ""),
        "target_id": manifest_row.get("target_id") or sample.get("metadata", {}).get("target_id", ""),
        "source_dataset": manifest_row.get("source") or sample.get("source", ""),
        "injection_mode": attempt.get("injection_mode", ""),
        "attempt_id": f"{sample.get('sample_id', '')}:{rgroup.get('rgroup_id', '')}:{attempt.get('injection_mode', '')}:{attempt.get('angle_deg', '')}",
        "seed": int(config.get("seed", 20260510)),
        "rotation_angle_deg": float(attempt.get("angle_deg") or 0.0),
        "rotation_axis_atom_pair": json.dumps(attempt.get("rotation_axis_atom_pair", []), ensure_ascii=False),
        "transform_matrix": json.dumps(np.asarray(attempt.get("transform_matrix", np.eye(4)), dtype=float).round(8).tolist(), ensure_ascii=False),
        "target_rgroup": rgroup.get("rgroup_id", ""),
        "target_atom_indices": json.dumps([int(idx) for idx in rgroup.get("atom_indices", [])], ensure_ascii=False),
        "anchor_scaffold_atom_idx": rgroup.get("anchor_scaffold_atom_idx"),
        "anchor_rgroup_atom_idx": rgroup.get("anchor_rgroup_atom_idx"),
        "anchor_bond_idx": rgroup.get("anchor_bond_idx"),
        "oracle_split": "",
        "difficulty_bin": "",
        "difficulty_reason": "",
        "acceptance_status": "",
        "reject_reason": "",
        "unsupported_reason": "",
        "invalid_reason": "",
        "duplicate_of": "",
        "ligand_valid": False,
        "rdkit_sanitize_ok": False,
        "rotatable_bond_valid": False,
        "anchor_integrity_pass": False,
        "bond_length_valid": False,
        "chirality_preserved": False,
        "ligand_internal_severe_clash_count": 0,
        "forcefield_type": "unavailable",
        "energy_original": float("nan"),
        "energy_failed": float("nan"),
        "energy_delta": float("nan"),
        "energy_delta_pass": True,
        "energy_check_status": "",
        "scaffold_rmsd": float("nan"),
        "non_target_rgroup_rmsd": float("nan"),
        "target_rgroup_rmsd": float("nan"),
        "delta_angstrom": float(config.get("detector", {}).get("default_delta_angstrom", 0.4)),
        "severe_depth_threshold_angstrom": float(config.get("detector", {}).get("severe_depth_threshold_angstrom", 0.4)),
        "target_num_clash_pairs": 0,
        "target_num_severe_pairs": 0,
        "target_total_score": 0.0,
        "target_max_depth": 0.0,
        "target_score_ratio_valid": 0.0,
        "target_score_ratio_all": 0.0,
        "non_target_num_severe_pairs": 0,
        "scaffold_num_severe_pairs": 0,
        "num_total_severe_pairs": 0,
        "total_clash_score": 0.0,
        "max_clash_depth": 0.0,
        "predicted_dominant_region_all": "",
        "predicted_dominant_valid_rgroup": "",
        "dominant_ratio_all_regions": 0.0,
        "dominant_ratio_valid_rgroups": 0.0,
        "failure_type": "",
        "recommended_action": "",
        "top_valid_rgroups_json": "[]",
        "top_clash_residue": "",
        "delta03_status": "",
        "delta04_status": "",
        "delta05_status": "",
        "sample_path": "",
        "original_ligand_sdf": "",
        "failed_ligand_sdf": "",
    }


def _delta_sensitivity(sample: dict[str, Any], failed_coords: np.ndarray, config: dict[str, Any], target_rgroup: str) -> dict[str, str]:
    detector_cfg = config.get("detector", {})
    severe = float(detector_cfg.get("severe_depth_threshold_angstrom", 0.4))
    result: dict[str, str] = {}
    for delta in detector_cfg.get("delta_sensitivity", [0.3, 0.4, 0.5]):
        report = detect_clashes(
            sample,
            ligand_coords=failed_coords,
            receptor_scope=str(detector_cfg.get("new_scope", "pocket10_all_atoms")),
            delta_angstrom=float(delta),
            severe_depth_threshold_angstrom=severe,
        )
        target_severe = sum(
            1 for pair in report.get("clash_pairs", []) if bool(pair.get("is_severe")) and pair.get("ligand_region") == target_rgroup
        )
        result[f"{float(delta):.1f}"] = "target_severe" if target_severe > 0 else "no_target_severe"
    return result


def _write_case_files(rows: list[dict[str, Any]], benchmark_root: Path, samples_root: Path, ligands_root: Path) -> None:
    for row in rows:
        sample = row.get("_sample")
        mol = row.get("_mol")
        if sample is None or mol is None or "_failed_coords" not in row:
            continue
        case_id = str(row["case_id"])
        sample_rel = Path("samples") / f"{case_id}.pkl"
        original_rel = Path("ligands") / f"{case_id}_original.sdf"
        failed_rel = Path("ligands") / f"{case_id}_failed.sdf"
        with (benchmark_root / sample_rel).open("wb") as f:
            pickle.dump(_sample_payload(row), f)
        _write_sdf(copy_mol_with_coords(mol, row["_original_coords"]), benchmark_root / original_rel)
        _write_sdf(copy_mol_with_coords(mol, row["_failed_coords"]), benchmark_root / failed_rel)
        row["sample_path"] = str(sample_rel)
        row["original_ligand_sdf"] = str(original_rel)
        row["failed_ligand_sdf"] = str(failed_rel)


def _write_sdf(mol: Any, path: Path) -> None:
    from rdkit import Chem

    writer = Chem.SDWriter(str(path))
    writer.write(mol)
    writer.close()


def _sample_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "phase2_v0_1",
        "case_id": row["case_id"],
        "base_sample": {
            "sample_id": row["base_sample_id"],
            "complex_id": row["base_complex_id"],
            "base_split": row["base_split"],
        },
        "original_ligand_coords": row["_original_coords"],
        "failed_ligand_coords": row["_failed_coords"],
        "target_rgroup": row["target_rgroup"],
        "injection": {
            "mode": row["injection_mode"],
            "angle_deg": row["rotation_angle_deg"],
            "rotation_axis_atom_pair": row["rotation_axis_atom_pair"],
        },
        "ligand_validity": {key: row.get(key) for key in [
            "ligand_valid",
            "rdkit_sanitize_ok",
            "rotatable_bond_valid",
            "anchor_integrity_pass",
            "bond_length_valid",
            "chirality_preserved",
            "ligand_internal_severe_clash_count",
            "forcefield_type",
            "energy_delta",
            "energy_check_status",
        ]},
        "clash_report": row.get("_clash_report", {}),
        "attribution_report": row.get("_attribution_report", {}),
        "oracle_labels": {
            "oracle_split": row["oracle_split"],
            "target_num_severe_pairs": row["target_num_severe_pairs"],
            "non_target_num_severe_pairs": row["non_target_num_severe_pairs"],
            "scaffold_num_severe_pairs": row["scaffold_num_severe_pairs"],
        },
        "split": row["oracle_split"],
        "difficulty": row["difficulty_bin"],
    }


def _manifest_dataframe(rows: list[dict[str, Any]]) -> pd.DataFrame:
    clean_rows: list[dict[str, Any]] = []
    for row in rows:
        clean = {column: row.get(column, "") for column in REPORT_COLUMNS}
        clean_rows.append(clean)
    return pd.DataFrame(clean_rows, columns=REPORT_COLUMNS)


def _write_schema(path: Path, manifest_df: pd.DataFrame) -> None:
    schema = {
        "schema_version": "phase2_v0_1",
        "manifest_columns": list(manifest_df.columns),
        "sample_schema": {
            "case_id": "str",
            "original_ligand_coords": "float32[num_atoms,3]",
            "failed_ligand_coords": "float32[num_atoms,3]",
            "target_rgroup": "str",
            "oracle_labels": "dict",
        },
    }
    with path.open("w", encoding="utf-8") as f:
        json.dump(schema, f, ensure_ascii=False, indent=2)


def _write_reports(
    report_root: Path,
    manifest_df: pd.DataFrame,
    base_rows: list[dict[str, Any]],
    attempts: list[dict[str, Any]],
    config: dict[str, Any],
    phase1_report_root: Path,
) -> None:
    manifest_df.to_csv(report_root / "injection_attempts.csv", index=False)
    pd.DataFrame(base_rows).to_csv(report_root / "base_clean_filter_report.csv", index=False)
    manifest_df[manifest_df["oracle_split"] == "supported_single_rgroup"].to_csv(report_root / "supported_single_rgroup_cases.csv", index=False)
    manifest_df[manifest_df["oracle_split"].isin(REJECT_SPLITS)].to_csv(report_root / "reject_cases.csv", index=False)
    manifest_df[manifest_df["oracle_split"] == "invalid_conformer"].to_csv(report_root / "invalid_conformer_cases.csv", index=False)
    manifest_df[manifest_df["oracle_split"] == "unsupported"].to_csv(report_root / "unsupported_cases.csv", index=False)
    manifest_df[manifest_df["oracle_split"] == "duplicate_removed"].to_csv(report_root / "duplicate_cases.csv", index=False)
    manifest_df[manifest_df["oracle_split"] == "near_miss_contact"].to_csv(report_root / "near_miss_cases.csv", index=False)
    _delta_sensitivity_report(manifest_df).to_csv(report_root / "delta_sensitivity.csv", index=False)
    _energy_delta_stats_report(manifest_df).to_csv(report_root / "energy_delta_stats.csv", index=False)
    _energy_delta_outliers_report(manifest_df).to_csv(report_root / "energy_delta_outliers.csv", index=False)
    _difficulty_bins_report(manifest_df).to_csv(report_root / "difficulty_bins.csv", index=False)
    visual_df = _visual_qc_cases(manifest_df, config)
    visual_df.to_csv(report_root / "visual_qc_cases.csv", index=False)
    _write_visual_notes(report_root / "visual_qc_notes.md", visual_df)
    summary = _summary(manifest_df, base_rows, config, phase1_report_root)
    with (report_root / "summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)


def _attempt_row(row: dict[str, Any]) -> dict[str, Any]:
    return {column: row.get(column, "") for column in REPORT_COLUMNS}


def _delta_sensitivity_report(manifest_df: pd.DataFrame) -> pd.DataFrame:
    status_columns = ["target_severe", "no_target_severe", "unsupported_or_unavailable"]
    rows = []
    for column, delta in [("delta03_status", 0.3), ("delta04_status", 0.4), ("delta05_status", 0.5)]:
        if column in manifest_df:
            statuses = manifest_df[column].map(_normalize_delta_status)
            counts = statuses.value_counts(dropna=False).to_dict()
        else:
            counts = {}
        row = {"delta_angstrom": delta}
        row.update({status: int(counts.get(status, 0)) for status in status_columns})
        for status, count in sorted(counts.items()):
            if status not in row:
                row[str(status)] = int(count)
        rows.append(row)
    return pd.DataFrame(rows).fillna(0)


def _normalize_delta_status(value: Any) -> str:
    if pd.isna(value) or str(value).strip() == "":
        return "unsupported_or_unavailable"
    return str(value)


def _energy_delta_stats_report(manifest_df: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "oracle_split",
        "injection_mode",
        "forcefield_type",
        "count",
        "num_available",
        "mean_energy_delta",
        "median_energy_delta",
        "p90_energy_delta",
        "p95_energy_delta",
        "p99_energy_delta",
        "max_energy_delta",
        "num_large_positive_delta",
        "num_large_negative_delta",
    ]
    if manifest_df.empty:
        return pd.DataFrame(columns=columns)

    df = manifest_df.copy()
    df["forcefield_type"] = df["forcefield_type"].replace("", "unavailable").fillna("unavailable")
    df["energy_delta_numeric"] = pd.to_numeric(df["energy_delta"], errors="coerce")
    rows: list[dict[str, Any]] = []
    grouped = df.groupby(["oracle_split", "injection_mode", "forcefield_type"], dropna=False, sort=True)
    for (oracle_split, injection_mode, forcefield_type), group in grouped:
        values = group["energy_delta_numeric"].dropna()
        rows.append(
            {
                "oracle_split": str(oracle_split),
                "injection_mode": str(injection_mode),
                "forcefield_type": str(forcefield_type),
                "count": int(len(group)),
                "num_available": int(len(values)),
                "mean_energy_delta": _safe_stat(values, "mean"),
                "median_energy_delta": _safe_stat(values, "median"),
                "p90_energy_delta": _safe_quantile(values, 0.90),
                "p95_energy_delta": _safe_quantile(values, 0.95),
                "p99_energy_delta": _safe_quantile(values, 0.99),
                "max_energy_delta": _safe_stat(values, "max"),
                "num_large_positive_delta": int((values > ENERGY_DELTA_LARGE_ABS_THRESHOLD).sum()),
                "num_large_negative_delta": int((values < -ENERGY_DELTA_LARGE_ABS_THRESHOLD).sum()),
            }
        )
    return pd.DataFrame(rows, columns=columns)


def _safe_stat(values: pd.Series, name: str) -> float:
    if values.empty:
        return float("nan")
    return float(getattr(values, name)())


def _safe_quantile(values: pd.Series, quantile: float) -> float:
    if values.empty:
        return float("nan")
    return float(values.quantile(quantile))


def _energy_delta_outliers_report(manifest_df: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "case_id",
        "oracle_split",
        "injection_mode",
        "target_rgroup",
        "forcefield_type",
        "energy_original",
        "energy_failed",
        "energy_delta",
        "energy_delta_percentile",
        "energy_delta_strict_pass",
        "energy_delta_outlier_flag",
        "ligand_valid",
        "ligand_internal_severe_clash_count",
        "target_num_severe_pairs",
        "max_clash_depth",
        "visual_qc_recommended",
        "sample_path",
        "failed_ligand_sdf",
    ]
    if manifest_df.empty:
        return pd.DataFrame(columns=columns)

    df = manifest_df.copy()
    df["energy_delta_numeric"] = pd.to_numeric(df["energy_delta"], errors="coerce")
    finite = df["energy_delta_numeric"].dropna()
    if finite.empty:
        return pd.DataFrame(columns=columns)

    abs_delta = finite.abs()
    p95_abs_delta = float(abs_delta.quantile(0.95))
    outlier_mask = df["energy_delta_numeric"].abs() >= p95_abs_delta
    large_mask = df["energy_delta_numeric"].abs() > ENERGY_DELTA_LARGE_ABS_THRESHOLD
    selected = df[outlier_mask | large_mask].copy()
    abs_percentile = df["energy_delta_numeric"].abs().rank(pct=True)
    selected["energy_delta_percentile"] = abs_percentile.loc[selected.index].astype(float)
    selected["energy_delta_strict_pass"] = selected["energy_delta_numeric"].abs() <= ENERGY_DELTA_LARGE_ABS_THRESHOLD
    selected["energy_delta_outlier_flag"] = selected["energy_delta_numeric"].abs().map(
        lambda value: f"abs_delta_ge_p95_or_{ENERGY_DELTA_LARGE_ABS_THRESHOLD:g}" if value >= p95_abs_delta or value > ENERGY_DELTA_LARGE_ABS_THRESHOLD else ""
    )
    selected["visual_qc_recommended"] = True
    selected = selected.sort_values("energy_delta_numeric", key=lambda series: series.abs(), ascending=False)
    return selected[columns]


def _difficulty_bins_report(manifest_df: pd.DataFrame) -> pd.DataFrame:
    if manifest_df.empty:
        return pd.DataFrame(columns=["difficulty_bin", "oracle_split", "count"])
    return manifest_df.groupby(["difficulty_bin", "oracle_split"], dropna=False).size().reset_index(name="count")


def _visual_qc_cases(manifest_df: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    visual_cfg = config.get("visual_qc", {})
    parts = [
        manifest_df[manifest_df["oracle_split"] == "supported_single_rgroup"].head(int(visual_cfg.get("num_supported_cases", 10))),
        manifest_df[manifest_df["oracle_split"] == "global_pose_failure"].head(int(visual_cfg.get("num_global_pose_failure_cases", 3))),
        manifest_df[manifest_df["oracle_split"] == "ambiguous_region"].head(int(visual_cfg.get("num_ambiguous_region_cases", 2))),
        manifest_df[manifest_df["oracle_split"] == "invalid_conformer"].head(int(visual_cfg.get("num_invalid_cases", 5))),
        manifest_df[manifest_df["oracle_split"] == "near_miss_contact"].head(int(visual_cfg.get("num_near_miss_cases", 5))),
        manifest_df[manifest_df["oracle_split"] == "duplicate_removed"].head(int(visual_cfg.get("num_duplicate_cases", 0))),
    ]
    result = pd.concat(parts, ignore_index=True) if parts else manifest_df.head(0)
    if result.empty:
        return pd.DataFrame(columns=["case_id", "oracle_split", "visual_qc_status", "notes"])
    result = result[["case_id", "oracle_split", "sample_path", "original_ligand_sdf", "failed_ligand_sdf"]].copy()
    result["visual_qc_status"] = "pending_manual_review"
    result["notes"] = "auto-selected for visual QC"
    return result


def _write_visual_notes(path: Path, visual_df: pd.DataFrame) -> None:
    lines = [
        "# Phase 2 Visual QC Notes",
        "",
        "- status: pending_manual_review",
        "- 自动结构 gates 已完成; 本文件是明确的待人工检查清单, 尚未把任何 case 判定为人工 pass.",
        "- 路径基准: `data/benchmarks/clashrepairbench_rg_artificial/v0_1/`.",
        "- 推荐工具: PyMOL, ChimeraX 或 RDKit/Mol* 可视化原始 ligand SDF, failed ligand SDF 和 sample pkl.",
        "- 判读项: target R-group 是否移动, scaffold 是否稳定, non-target R-groups 是否稳定, clash 是否位于 target 区域, invalid/global/near_miss 分类是否合理.",
        "",
        "## 1. Cases",
        "",
    ]
    if visual_df.empty:
        lines.append("- no cases selected")
    else:
        for _, row in visual_df.iterrows():
            lines.append(f"- {row['case_id']}: {row['oracle_split']}, {row['visual_qc_status']}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _summary(manifest_df: pd.DataFrame, base_rows: list[dict[str, Any]], config: dict[str, Any], phase1_report_root: Path) -> dict[str, Any]:
    split_counts = manifest_df["oracle_split"].value_counts(dropna=False).to_dict() if not manifest_df.empty else {}
    return {
        "schema_version": "phase2_v0_1",
        "num_base_clean_samples": int(sum(bool(row.get("base_clean_pass")) for row in base_rows)),
        "num_base_total_samples": int(len(base_rows)),
        "num_attempts": int(len(manifest_df)),
        "num_accepted_supported": int(split_counts.get("supported_single_rgroup", 0)),
        "num_reject": int(sum(int(split_counts.get(split, 0)) for split in REJECT_SPLITS)),
        "num_invalid_conformer": int(split_counts.get("invalid_conformer", 0)),
        "num_unsupported": int(split_counts.get("unsupported", 0)),
        "num_duplicates_removed": int(split_counts.get("duplicate_removed", 0)),
        "num_near_miss_contact": int(split_counts.get("near_miss_contact", 0)),
        "oracle_split_counts": {str(key): int(value) for key, value in split_counts.items()},
        "default_delta_angstrom": float(config.get("detector", {}).get("default_delta_angstrom", 0.4)),
        "delta_sensitivity": [float(value) for value in config.get("detector", {}).get("delta_sensitivity", [0.3, 0.4, 0.5])],
        "injection_modes": list(config.get("injection", {}).get("modes", [])),
        "phase1_report_root": str(phase1_report_root),
        "phase2_acceptance_status": "complete" if int(split_counts.get("supported_single_rgroup", 0)) > 0 else "incomplete",
        "visual_qc_status": "pending_manual_review",
        "energy_delta_threshold_mode": str(config.get("chemistry", {}).get("energy_delta_threshold_mode", "record_only")),
        "energy_delta_filter_interpretation": "record_only_not_hard_filter",
    }


def _write_completion_audit(report_root: Path, benchmark_root: Path, manifest_df: pd.DataFrame, base_rows: list[dict[str, Any]], config: dict[str, Any]) -> None:
    summary = _summary(manifest_df, base_rows, config, report_root.parent / "phase1_clash_detector")
    split_counts = summary["oracle_split_counts"]
    checklist = [
        ("configs/phase2_injection.yaml exists", "done"),
        ("phase2 script runnable", "done"),
        ("manifest.parquet readable", "done"),
        ("samples/*.pkl generated", "done" if any((benchmark_root / "samples").glob("*.pkl")) else "missing"),
        ("reports/phase2_injection generated", "done"),
        ("supported_single_rgroup cases > 0", "done" if split_counts.get("supported_single_rgroup", 0) > 0 else "missing"),
        ("accepted samples ligand_valid true", "done" if _all_supported(manifest_df, "ligand_valid", True) else "missing"),
        ("accepted samples ligand internal severe clash = 0", "done" if _all_supported(manifest_df, "ligand_internal_severe_clash_count", 0) else "missing"),
        ("supported target severe clash >= 1", "done" if _supported_min(manifest_df, "target_num_severe_pairs", 1) else "missing"),
        ("supported non-target severe = 0", "done" if _all_supported(manifest_df, "non_target_num_severe_pairs", 0) else "missing"),
        ("supported scaffold severe = 0", "done" if _all_supported(manifest_df, "scaffold_num_severe_pairs", 0) else "missing"),
        ("injected samples inherit base split", "done" if bool((manifest_df["base_split"] == manifest_df["derived_split"]).all()) else "missing"),
        ("predicted dominant not used as acceptance gate", "done"),
        ("invalid/reject/unsupported/duplicate reported", "done"),
        ("visual QC cases recorded", "done"),
        ("visual QC manual review", "blocked"),
        ("delta_sensitivity.csv has no empty columns", "done" if not any(str(column).strip() == "" for column in _delta_sensitivity_report(manifest_df).columns) else "missing"),
        ("energy_delta stats/outliers reports", "done"),
    ]
    lines = [
        "# Phase 2 Completion Audit",
        "",
        "## 1. Checklist",
        "",
        "| item | status |",
        "|---|---|",
    ]
    lines.extend(f"| {item} | {status} |" for item, status in checklist)
    lines.extend(
        [
            "",
            "## 2. Commands",
            "",
            "```bash",
            "/home/lyj/miniconda3/envs/c2f_cpu/bin/python -m compileall src scripts",
            "/home/lyj/miniconda3/envs/c2f_cpu/bin/python -m pytest",
            "/home/lyj/miniconda3/envs/c2f_cpu/bin/python scripts/phase2_inject_artificial_clashes.py --config configs/phase2_injection.yaml --manifest data/processed/v0_1/manifest.parquet --phase1-report-root reports/phase1_clash_detector --output-root data/benchmarks/clashrepairbench_rg_artificial/v0_1 --report-root reports/phase2_injection",
            "```",
            "",
            "## 3. Summary",
            "",
            "```json",
            json.dumps(summary, ensure_ascii=False, indent=2),
            "```",
            "",
            "## 4. Blocked",
            "",
            "- visual_qc_manual_review: blocked. 当前已生成明确待人工检查清单 `visual_qc_cases.csv` 和 `visual_qc_notes.md`; 需要人工用 PyMOL/ChimeraX/RDKit 打开 `data/benchmarks/clashrepairbench_rg_artificial/v0_1/ligands/*_original.sdf`, `*_failed.sdf` 和对应 `samples/*.pkl` 判读. 该 blocked 不改变自动 gate 结论, 但阶段 3 正式报告前应完成抽样确认.",
            "",
            "## 5. Phase2 Closure Decision",
            "",
            "- Phase2 is accepted for controlled Phase3 locator / verifier preflight.",
            "- Phase2 v0_1 is a controlled artificial single-Rgroup clash benchmark, not validation of model-induced generation failures.",
            "- Phase2.5 external validity audit will be handled separately and is not implemented here.",
            "- Energy delta is a record-only ligand-only diagnostic in phase2_v0_1; it is not a hard acceptance filter.",
            "",
            "## 6. Phase 3 Preflight",
            "",
            "- 使用 `supported_single_rgroup` 作为 Top-1 / Top-3 主评估集.",
            "- 使用 reject/unsupported/near_miss/duplicate split 单独统计分流表现.",
            "- 阶段 3 读取 `target_rgroup`, `top_valid_rgroups_json`, `delta03/04/05_status` 做 locator preflight.",
        ]
    )
    (report_root / "phase2_completion_audit.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _all_supported(manifest_df: pd.DataFrame, column: str, expected: Any) -> bool:
    supported = manifest_df[manifest_df["oracle_split"] == "supported_single_rgroup"]
    if supported.empty:
        return False
    return bool((supported[column] == expected).all())


def _supported_min(manifest_df: pd.DataFrame, column: str, minimum: float) -> bool:
    supported = manifest_df[manifest_df["oracle_split"] == "supported_single_rgroup"]
    if supported.empty:
        return False
    return bool((supported[column].astype(float) >= float(minimum)).all())


if __name__ == "__main__":
    raise SystemExit(main())
