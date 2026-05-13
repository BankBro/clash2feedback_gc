from __future__ import annotations

import hashlib
import json
import math
import pickle
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


SCHEMA_VERSION = "phase3_label_provenance_audit_v0_1"
SUPPORTED_SPLIT = "supported_single_rgroup"
S0_EXCLUDED_SPLITS = {"unsupported", "invalid_conformer", "duplicate_removed"}

PHASE4_MASK_SEED_COLUMNS = [
    "case_id",
    "base_sample_id",
    "base_complex_id",
    "base_split",
    "derived_split",
    "oracle_split",
    "injection_mode",
    "difficulty_bin",
    "set_membership_s0",
    "set_membership_s1",
    "set_membership_s2",
    "circularity_risk_level",
    "target_rgroup",
    "target_atom_indices",
    "predicted_dominant_valid_rgroup",
    "top_valid_rgroups_json",
    "target_score_ratio_valid",
    "dominant_ratio_valid_rgroups",
    "failure_type",
    "recommended_action",
    "predicted_equals_oracle",
    "oracle_mask_rgroup",
    "oracle_mask_atom_indices",
    "oracle_keep_atom_indices",
    "oracle_anchor_scaffold_atom_idx",
    "oracle_anchor_rgroup_atom_idx",
    "oracle_anchor_bond_idx",
    "oracle_mask_available",
    "oracle_mask_reason",
    "predicted_mask_rgroup",
    "predicted_mask_atom_indices",
    "predicted_keep_atom_indices",
    "predicted_anchor_scaffold_atom_idx",
    "predicted_anchor_rgroup_atom_idx",
    "predicted_anchor_bond_idx",
    "predicted_mask_available",
    "predicted_mask_reason",
    "random_mask_rgroup",
    "random_mask_atom_indices",
    "random_keep_atom_indices",
    "random_anchor_scaffold_atom_idx",
    "random_anchor_rgroup_atom_idx",
    "random_anchor_bond_idx",
    "random_mask_available",
    "random_mask_policy",
    "random_mask_fallback_reason",
    "random_equals_oracle",
    "random_equals_predicted",
    "old_clash_pairs_json",
    "protein_clash_hot_atoms_json",
    "protein_clash_hot_residues_json",
    "target_num_severe_pairs",
    "non_target_num_severe_pairs",
    "scaffold_num_severe_pairs",
    "num_total_severe_pairs",
    "max_clash_depth",
    "total_clash_score",
    "phase4_0_backend_feasibility_candidate",
    "phase4_1_formal_loop_candidate",
    "phase4_candidate_reason",
    "phase4_exclusion_reason",
]


class Phase3ConflictError(RuntimeError):
    """Raised when a high-risk phase3 data conflict requires manual confirmation."""


@dataclass
class Phase3Result:
    summary: dict[str, Any]
    output_paths: dict[str, Path]
    conflicts: list[dict[str, Any]]


def build_phase3_outputs(config: dict[str, Any], *, repo_root: Path, write_outputs: bool = True) -> Phase3Result:
    paths = _resolve_paths(config, repo_root=repo_root)
    seed = int(config.get("seed", 20260513))
    max_depth = float(config.get("sets", {}).get("max_clash_depth_angstrom", 1.5))

    phase2_manifest = pd.read_parquet(paths["phase2_manifest"])
    if "case_id" not in phase2_manifest.columns:
        raise ValueError(f"phase2 manifest missing case_id: {paths['phase2_manifest']}")

    phase2_supported_report = _read_csv_if_exists(paths["phase2_report_root"] / "supported_single_rgroup_cases.csv")
    phase2_summary = _read_json_if_exists(paths["phase2_report_root"] / "summary.json")
    phase2_5_taxonomy = _read_csv_if_exists(paths["phase2_5_report_root"] / "failure_taxonomy.csv")

    phase2_5_conflicts = _phase2_5_conflicts(phase2_5_taxonomy)
    if phase2_5_conflicts:
        conflict_path = paths["conflict_report"]
        if write_outputs:
            write_conflict_report(conflict_path, phase2_5_conflicts)
        raise Phase3ConflictError(f"high-risk phase2.5 conflict written to {conflict_path}")

    set_flags = phase2_manifest.apply(lambda row: phase2_set_membership(row, max_depth=max_depth), axis=1)
    set_flag_df = pd.DataFrame(list(set_flags), index=phase2_manifest.index)
    audited_manifest = pd.concat([phase2_manifest, set_flag_df], axis=1)

    base_cache: dict[str, dict[str, Any]] = {}
    phase2_sample_cache: dict[str, dict[str, Any]] = {}
    conflicts: list[dict[str, Any]] = []
    seed_rows: list[dict[str, Any]] = []

    s2 = audited_manifest[audited_manifest["set_membership_s2"]].copy()
    for _, row in s2.sort_values("case_id").iterrows():
        base_sample_id = str(row.get("base_sample_id") or "")
        phase2_sample = _load_phase2_sample(row, paths["phase2_benchmark_root"], phase2_sample_cache)
        base_sample = _load_base_sample(base_sample_id, paths["processed_root"], base_cache)
        row_conflicts = _s2_conflicts(row, phase2_sample, base_sample)
        conflicts.extend(row_conflicts)
        if row_conflicts:
            continue
        seed_rows.append(_build_phase4_seed_row(row, phase2_sample, base_sample, seed=seed))

    if conflicts:
        conflict_path = paths["conflict_report"]
        if write_outputs:
            write_conflict_report(conflict_path, conflicts)
        raise Phase3ConflictError(f"high-risk phase3 conflict written to {conflict_path}")

    phase4_mask_seed = pd.DataFrame(seed_rows, columns=PHASE4_MASK_SEED_COLUMNS)
    set_definition_report = build_set_definition_report(audited_manifest)
    construction_report = build_construction_consistency_report(audited_manifest)
    stress_s0 = build_locator_stress_report(audited_manifest, set_column="set_membership_s0", set_name="S0_all_valid_injection_attempts")
    stress_s1 = build_locator_stress_report(audited_manifest, set_column="set_membership_s1", set_name="S1_oracle_target_local_clash_set")
    field_dependency = build_field_dependency_table()
    summary = build_summary(
        phase2_manifest=phase2_manifest,
        audited_manifest=audited_manifest,
        phase4_mask_seed=phase4_mask_seed,
        construction_report=construction_report,
        phase2_supported_report=phase2_supported_report,
        phase2_summary=phase2_summary,
        phase2_5_taxonomy=phase2_5_taxonomy,
        paths=paths,
        seed=seed,
    )

    output_paths = {
        "summary": paths["report_root"] / "summary.json",
        "label_provenance": paths["report_root"] / "phase2_label_provenance_audit.md",
        "circularity_risk": paths["report_root"] / "circularity_risk_audit.md",
        "field_dependency": paths["report_root"] / "field_dependency_table.csv",
        "set_definition": paths["report_root"] / "set_definition_report.csv",
        "construction_consistency": paths["report_root"] / "construction_consistency_report.csv",
        "locator_stress_s0": paths["report_root"] / "locator_stress_report_s0.csv",
        "locator_stress_s1": paths["report_root"] / "locator_stress_report_s1.csv",
        "phase4_mask_seed": paths["report_root"] / "phase4_mask_seed.csv",
        "completion_audit": paths["report_root"] / "phase3_completion_audit.md",
    }
    if write_outputs:
        paths["report_root"].mkdir(parents=True, exist_ok=True)
        _write_json(output_paths["summary"], summary)
        phase4_mask_seed.to_csv(output_paths["phase4_mask_seed"], index=False)
        field_dependency.to_csv(output_paths["field_dependency"], index=False)
        set_definition_report.to_csv(output_paths["set_definition"], index=False)
        construction_report.to_csv(output_paths["construction_consistency"], index=False)
        stress_s0.to_csv(output_paths["locator_stress_s0"], index=False)
        stress_s1.to_csv(output_paths["locator_stress_s1"], index=False)
        output_paths["label_provenance"].write_text(_label_provenance_markdown(summary), encoding="utf-8")
        output_paths["circularity_risk"].write_text(_circularity_markdown(summary), encoding="utf-8")
        output_paths["completion_audit"].write_text(_completion_audit_markdown(summary, output_paths), encoding="utf-8")

    return Phase3Result(summary=summary, output_paths=output_paths, conflicts=[])


def phase2_set_membership(row: pd.Series | dict[str, Any], *, max_depth: float = 1.5) -> dict[str, bool]:
    ligand_valid = _as_bool(_row_value(row, "ligand_valid"))
    ligand_internal = _as_int(_row_value(row, "ligand_internal_severe_clash_count"), default=999999)
    oracle_split = str(_row_value(row, "oracle_split") or "")
    target_severe = _as_int(_row_value(row, "target_num_severe_pairs"), default=0)
    scaffold_severe = _as_int(_row_value(row, "scaffold_num_severe_pairs"), default=999999)
    non_target_severe = _as_int(_row_value(row, "non_target_num_severe_pairs"), default=999999)
    row_max_depth = _as_float(_row_value(row, "max_clash_depth"), default=math.inf)
    s0 = ligand_valid and ligand_internal == 0 and oracle_split not in S0_EXCLUDED_SPLITS
    s1 = (
        ligand_valid
        and ligand_internal == 0
        and target_severe >= 1
        and scaffold_severe == 0
        and non_target_severe == 0
        and row_max_depth <= max_depth
    )
    s2 = oracle_split == SUPPORTED_SPLIT
    return {
        "set_membership_s0": bool(s0),
        "set_membership_s1": bool(s1),
        "set_membership_s2": bool(s2),
    }


def build_mask_bundle(base_sample: dict[str, Any], rgroup_id: str, *, num_ligand_atoms: int | None = None) -> dict[str, Any]:
    rgroup_id = str(rgroup_id or "").strip()
    if not rgroup_id:
        return _empty_mask_bundle(rgroup_id, "missing_rgroup_id")
    rgroup = rgroup_map(base_sample).get(rgroup_id)
    if rgroup is None:
        return _empty_mask_bundle(rgroup_id, "rgroup_not_found_in_processed_sample")
    atom_indices = _int_list(rgroup.get("atom_indices", []))
    if not atom_indices:
        return _empty_mask_bundle(rgroup_id, "rgroup_atom_indices_empty")
    ligand_atoms = int(num_ligand_atoms if num_ligand_atoms is not None else ligand_atom_count(None, base_sample))
    out_of_range = [idx for idx in atom_indices if idx < 0 or idx >= ligand_atoms]
    if out_of_range:
        bundle = _empty_mask_bundle(rgroup_id, "rgroup_atom_indices_out_of_range")
        bundle["atom_indices"] = atom_indices
        return bundle
    edit = sorted(set(atom_indices))
    keep = [idx for idx in range(ligand_atoms) if idx not in set(edit)]
    return {
        "rgroup": rgroup_id,
        "atom_indices": edit,
        "keep_atom_indices": keep,
        "anchor_scaffold_atom_idx": _optional_int(rgroup.get("anchor_scaffold_atom_idx")),
        "anchor_rgroup_atom_idx": _optional_int(rgroup.get("anchor_rgroup_atom_idx")),
        "anchor_bond_idx": _optional_int(rgroup.get("anchor_bond_idx")),
        "available": True,
        "reason": "ok",
    }


def choose_size_matched_random_rgroup(
    base_sample: dict[str, Any],
    *,
    oracle_rgroup_id: str,
    predicted_rgroup_id: str,
    seed: int,
    case_id: str,
) -> tuple[str, str]:
    oracle = rgroup_map(base_sample).get(str(oracle_rgroup_id))
    if oracle is None:
        return "", "oracle_rgroup_missing"
    target_size = rgroup_heavy_atom_count(base_sample, oracle)
    candidates = valid_single_anchor_rgroups(base_sample)
    predicted = str(predicted_rgroup_id or "")
    primary_exclusions = {str(oracle_rgroup_id)}
    if predicted:
        primary_exclusions.add(predicted)
    primary = _rank_random_candidates(candidates, target_size, exclusions=primary_exclusions, seed=seed, case_id=case_id, base_sample=base_sample)
    if primary:
        return str(primary[0].get("rgroup_id")), "primary_exclude_oracle_and_predicted"
    fallback = _rank_random_candidates(candidates, target_size, exclusions={str(oracle_rgroup_id)}, seed=seed, case_id=case_id, base_sample=base_sample)
    if fallback:
        return str(fallback[0].get("rgroup_id")), "fallback_exclude_oracle_only"
    return "", "no_non_oracle_valid_single_anchor_rgroup"


def valid_single_anchor_rgroups(base_sample: dict[str, Any]) -> list[dict[str, Any]]:
    result = []
    for rgroup in base_sample.get("rgroups", []):
        if bool(rgroup.get("is_valid_for_phase0")) and bool(rgroup.get("is_single_anchor")) and _int_list(rgroup.get("atom_indices", [])):
            result.append(rgroup)
    return result


def rgroup_map(base_sample: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(rgroup.get("rgroup_id")): rgroup for rgroup in base_sample.get("rgroups", []) if rgroup.get("rgroup_id")}


def ligand_atom_count(phase2_sample: dict[str, Any] | None, base_sample: dict[str, Any]) -> int:
    if phase2_sample is not None and "failed_ligand_coords" in phase2_sample:
        return int(np.asarray(phase2_sample["failed_ligand_coords"]).shape[0])
    ligand = base_sample.get("ligand", {})
    if ligand.get("num_atoms") is not None:
        return int(ligand.get("num_atoms"))
    return int(len(ligand.get("elements", [])))


def rgroup_heavy_atom_count(base_sample: dict[str, Any], rgroup: dict[str, Any]) -> int:
    heavy = _int_list(rgroup.get("heavy_atom_indices", []))
    if heavy:
        return len(heavy)
    atomic_numbers = [int(value) for value in base_sample.get("ligand", {}).get("atomic_numbers", [])]
    count = 0
    for atom_idx in _int_list(rgroup.get("atom_indices", [])):
        atomic_number = atomic_numbers[atom_idx] if atom_idx < len(atomic_numbers) else 6
        if int(atomic_number) > 1:
            count += 1
    return count


def target_in_top_n(top_valid_rgroups_json: Any, target_rgroup: str, *, n: int) -> bool:
    top = parse_json_list(top_valid_rgroups_json)
    target = str(target_rgroup or "")
    for item in top[:n]:
        if isinstance(item, dict) and str(item.get("region") or "") == target:
            return True
    return False


def parse_json_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if _missing(value):
        return []
    text = str(value).strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def build_set_definition_report(audited_manifest: pd.DataFrame) -> pd.DataFrame:
    rows = [
        {
            "set_name": "S0_all_valid_injection_attempts",
            "count": int(audited_manifest["set_membership_s0"].sum()),
            "definition": "ligand_valid true, ligand_internal_severe_clash_count 0, oracle_split not in unsupported/invalid_conformer/duplicate_removed",
            "phase4_role": "auxiliary_audit_only",
            "construction_consistency_denominator": False,
        },
        {
            "set_name": "S1_oracle_target_local_clash_set",
            "count": int(audited_manifest["set_membership_s1"].sum()),
            "definition": "valid ligand, target severe clash >=1, scaffold and non-target severe clash 0, max_clash_depth <= 1.5, without target_score_ratio_valid gate",
            "phase4_role": "auxiliary_stress_analysis_only",
            "construction_consistency_denominator": False,
        },
        {
            "set_name": "S2_phase2_supported_single_rgroup",
            "count": int(audited_manifest["set_membership_s2"].sum()),
            "definition": "oracle_split == supported_single_rgroup",
            "phase4_role": "primary_phase4_mask_seed_input",
            "construction_consistency_denominator": True,
        },
    ]
    return pd.DataFrame(rows)


def build_construction_consistency_report(audited_manifest: pd.DataFrame) -> pd.DataFrame:
    s2 = audited_manifest[audited_manifest["set_membership_s2"]].copy()
    denominator = int(len(s2))
    predicted_equals = s2.apply(
        lambda row: str(row.get("predicted_dominant_valid_rgroup") or "") == str(row.get("target_rgroup") or ""),
        axis=1,
    )
    top3 = s2.apply(lambda row: target_in_top_n(row.get("top_valid_rgroups_json"), row.get("target_rgroup"), n=3), axis=1)
    rows = [
        _metric_row(
            "construction_consistency_top1_predicted_equals_oracle",
            int(predicted_equals.sum()),
            denominator,
            "S2_phase2_supported_single_rgroup",
            "Top-1 only checks construction consistency on clean local repair substrate, not independent localization accuracy.",
        ),
        _metric_row(
            "construction_consistency_top3_target_in_top_valid_rgroups",
            int(top3.sum()),
            denominator,
            "S2_phase2_supported_single_rgroup",
            "Top-3 only checks whether attribution construction ranks the artificial target in top valid R-groups.",
        ),
    ]
    return pd.DataFrame(rows)


def build_locator_stress_report(audited_manifest: pd.DataFrame, *, set_column: str, set_name: str) -> pd.DataFrame:
    selected = audited_manifest[audited_manifest[set_column]].copy()
    rows = []
    for _, row in selected.sort_values("case_id").iterrows():
        target = str(row.get("target_rgroup") or "")
        predicted = str(row.get("predicted_dominant_valid_rgroup") or "")
        rows.append(
            {
                "case_id": row.get("case_id", ""),
                "set_name": set_name,
                "oracle_split": row.get("oracle_split", ""),
                "target_rgroup": target,
                "predicted_dominant_valid_rgroup": predicted,
                "predicted_equals_oracle": predicted == target,
                "target_in_top3_valid_rgroups": target_in_top_n(row.get("top_valid_rgroups_json"), target, n=3),
                "target_score_ratio_valid": _as_float(row.get("target_score_ratio_valid"), default=0.0),
                "dominant_ratio_valid_rgroups": _as_float(row.get("dominant_ratio_valid_rgroups"), default=0.0),
                "not_independent_locator_benchmark": True,
                "not_construction_consistency_denominator": set_name != "S2_phase2_supported_single_rgroup",
            }
        )
    return pd.DataFrame(rows)


def build_field_dependency_table() -> pd.DataFrame:
    rows = [
        ("target_rgroup", "phase2 artificial perturbation target", "scripts/phase2_inject_artificial_clashes.py::_common_row", "reference mask source, not unbiased locator truth"),
        ("target_atom_indices", "phase2 target R-group atom_indices", "phase2 manifest plus processed base sample cross-check", "oracle/reference edit mask atoms"),
        ("anchor_scaffold_atom_idx", "phase2 target R-group anchor", "phase2 manifest and processed base sample", "anchor record only, not default free edit mask"),
        ("anchor_rgroup_atom_idx", "phase2 target R-group anchor", "phase2 manifest and processed base sample", "anchor record only"),
        ("anchor_bond_idx", "phase2 target R-group anchor bond", "phase2 manifest and processed base sample", "anchor record only"),
        ("predicted_dominant_valid_rgroup", "attribution-derived dominant valid R-group", "attribute_clashes_to_rgroups().dominant_valid_rgroup", "operational predicted mask policy, not acceptance gate and not ground truth"),
        ("target_score_ratio_valid", "target score divided by attribution valid R-group scores", "perturb.labels.target_score_ratio_valid()", "participates in supported_single_rgroup gate"),
        ("supported_single_rgroup", "detector + attribution + target-dominance filtered split", "perturb.labels.assign_oracle_split()", "clean local repair substrate"),
        ("phase2_5_model_induced_samples", "model-induced audit rows without artificial target_rgroup", "reports/phase2_5_model_induced_audit/failure_taxonomy.csv", "excluded from construction consistency denominator"),
        ("phase4_mask_seed.csv", "S2 phase2 supported cases only", "src/clash2feedback/feedback/mask_seed.py", "phase4 backend feasibility and formal loop seed"),
    ]
    return pd.DataFrame(rows, columns=["field_or_artifact", "definition", "implementation_source", "phase3_interpretation"])


def build_summary(
    *,
    phase2_manifest: pd.DataFrame,
    audited_manifest: pd.DataFrame,
    phase4_mask_seed: pd.DataFrame,
    construction_report: pd.DataFrame,
    phase2_supported_report: pd.DataFrame,
    phase2_summary: dict[str, Any],
    phase2_5_taxonomy: pd.DataFrame,
    paths: dict[str, Path],
    seed: int,
) -> dict[str, Any]:
    s2_count = int(audited_manifest["set_membership_s2"].sum())
    top1 = _metric_by_name(construction_report, "construction_consistency_top1_predicted_equals_oracle")
    top3 = _metric_by_name(construction_report, "construction_consistency_top3_target_in_top_valid_rgroups")
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": "2026-05-13",
        "git": _git_info(paths["repo_root"]),
        "inputs": {key: _relpath(value, paths["repo_root"]) for key, value in paths.items() if key.endswith("root") or key.endswith("manifest")},
        "seed": seed,
        "phase3_scope": "label provenance audit + circularity risk audit + construction consistency check + phase4 mask seed generation",
        "phase3_not_independent_locator_benchmark": True,
        "phase3_does_not_train_generate_or_repair": True,
        "phase2_manifest_rows": int(len(phase2_manifest)),
        "phase2_supported_report_rows": int(len(phase2_supported_report)),
        "phase2_summary_num_accepted_supported": int(phase2_summary.get("num_accepted_supported", 0) or 0),
        "set_counts": {
            "S0_all_valid_injection_attempts": int(audited_manifest["set_membership_s0"].sum()),
            "S1_oracle_target_local_clash_set": int(audited_manifest["set_membership_s1"].sum()),
            "S2_phase2_supported_single_rgroup": s2_count,
        },
        "construction_consistency": {
            "denominator_set": "S2_phase2_supported_single_rgroup",
            "denominator": s2_count,
            "top1_predicted_equals_oracle": top1,
            "top3_target_in_top_valid_rgroups": top3,
            "interpretation": "construction consistency only, not independent localization accuracy",
        },
        "phase4_mask_seed": {
            "rows": int(len(phase4_mask_seed)),
            "backend_feasibility_candidates": int(phase4_mask_seed["phase4_0_backend_feasibility_candidate"].sum()) if not phase4_mask_seed.empty else 0,
            "formal_loop_candidates": int(phase4_mask_seed["phase4_1_formal_loop_candidate"].sum()) if not phase4_mask_seed.empty else 0,
            "predicted_equals_oracle": int(phase4_mask_seed["predicted_equals_oracle"].sum()) if not phase4_mask_seed.empty else 0,
            "random_equals_oracle": int(phase4_mask_seed["random_equals_oracle"].sum()) if not phase4_mask_seed.empty else 0,
            "random_equals_predicted": int(phase4_mask_seed["random_equals_predicted"].sum()) if not phase4_mask_seed.empty else 0,
        },
        "phase2_5_model_induced_audit": {
            "failure_taxonomy_rows": int(len(phase2_5_taxonomy)),
            "has_artificial_target_rgroup_column": bool("target_rgroup" in phase2_5_taxonomy.columns),
            "included_in_construction_consistency_denominator": False,
        },
        "mask_policy": {
            "oracle_mask": "entire target_rgroup R-group atom set",
            "predicted_mask": "entire predicted_dominant_valid_rgroup R-group atom set, operational policy only",
            "random_mask": "same-ligand size-matched valid single-anchor R-group, deterministic seed",
            "anchor_policy": "record only, not default free edit mask",
        },
    }


def write_conflict_report(path: Path, conflicts: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# 阶段 3 标签溯源与掩码种子冲突报告",
        "",
        "## 1. 冲突项",
        "",
    ]
    for conflict in conflicts:
        lines.extend(
            [
                f"### {conflict.get('conflict_id', 'unknown_conflict')}",
                "",
                f"- 冲突项: {conflict.get('conflict_item', '')}",
                f"- 方案文档表述: {conflict.get('plan_statement', '')}",
                f"- 仓库实际情况: {conflict.get('actual_state', '')}",
                f"- 涉及文件: {conflict.get('files', '')}",
                f"- 影响范围: {conflict.get('impact', '')}",
                f"- 建议处理方式: {conflict.get('recommendation', '')}",
                f"- 是否需要人工确认: {conflict.get('needs_manual_confirmation', True)}",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def _build_phase4_seed_row(row: pd.Series, phase2_sample: dict[str, Any], base_sample: dict[str, Any], *, seed: int) -> dict[str, Any]:
    case_id = str(row.get("case_id") or "")
    target = str(row.get("target_rgroup") or "")
    predicted = str(row.get("predicted_dominant_valid_rgroup") or "")
    num_ligand_atoms = ligand_atom_count(phase2_sample, base_sample)
    oracle = build_mask_bundle(base_sample, target, num_ligand_atoms=num_ligand_atoms)
    predicted_bundle = build_mask_bundle(base_sample, predicted, num_ligand_atoms=num_ligand_atoms)
    random_rgroup, random_reason = choose_size_matched_random_rgroup(
        base_sample,
        oracle_rgroup_id=target,
        predicted_rgroup_id=predicted,
        seed=seed,
        case_id=case_id,
    )
    random_bundle = build_mask_bundle(base_sample, random_rgroup, num_ligand_atoms=num_ligand_atoms)
    old_pairs = list(phase2_sample.get("clash_report", {}).get("clash_pairs", []) or [])
    phase4_0 = bool(oracle["available"])
    phase4_1 = bool(oracle["available"] and predicted_bundle["available"] and random_bundle["available"])
    if phase4_1:
        candidate_reason = "S2 case with oracle, predicted and random masks available"
        exclusion_reason = ""
    elif phase4_0:
        candidate_reason = "S2 case with oracle mask only"
        exclusion_reason = "missing_predicted_or_random_mask"
    else:
        candidate_reason = ""
        exclusion_reason = "missing_oracle_mask"
    return {
        "case_id": case_id,
        "base_sample_id": row.get("base_sample_id", ""),
        "base_complex_id": row.get("base_complex_id", ""),
        "base_split": row.get("base_split", ""),
        "derived_split": row.get("derived_split", ""),
        "oracle_split": row.get("oracle_split", ""),
        "injection_mode": row.get("injection_mode", ""),
        "difficulty_bin": row.get("difficulty_bin", ""),
        "set_membership_s0": _as_bool(row.get("set_membership_s0")),
        "set_membership_s1": _as_bool(row.get("set_membership_s1")),
        "set_membership_s2": _as_bool(row.get("set_membership_s2")),
        "circularity_risk_level": "high",
        "target_rgroup": target,
        "target_atom_indices": _json_list(_int_list_from_json(row.get("target_atom_indices"))),
        "predicted_dominant_valid_rgroup": predicted,
        "top_valid_rgroups_json": row.get("top_valid_rgroups_json", "[]"),
        "target_score_ratio_valid": _as_float(row.get("target_score_ratio_valid"), default=0.0),
        "dominant_ratio_valid_rgroups": _as_float(row.get("dominant_ratio_valid_rgroups"), default=0.0),
        "failure_type": row.get("failure_type", ""),
        "recommended_action": row.get("recommended_action", ""),
        "predicted_equals_oracle": predicted == target,
        "oracle_mask_rgroup": oracle["rgroup"],
        "oracle_mask_atom_indices": _json_list(oracle["atom_indices"]),
        "oracle_keep_atom_indices": _json_list(oracle["keep_atom_indices"]),
        "oracle_anchor_scaffold_atom_idx": oracle["anchor_scaffold_atom_idx"],
        "oracle_anchor_rgroup_atom_idx": oracle["anchor_rgroup_atom_idx"],
        "oracle_anchor_bond_idx": oracle["anchor_bond_idx"],
        "oracle_mask_available": bool(oracle["available"]),
        "oracle_mask_reason": oracle["reason"],
        "predicted_mask_rgroup": predicted_bundle["rgroup"],
        "predicted_mask_atom_indices": _json_list(predicted_bundle["atom_indices"]),
        "predicted_keep_atom_indices": _json_list(predicted_bundle["keep_atom_indices"]),
        "predicted_anchor_scaffold_atom_idx": predicted_bundle["anchor_scaffold_atom_idx"],
        "predicted_anchor_rgroup_atom_idx": predicted_bundle["anchor_rgroup_atom_idx"],
        "predicted_anchor_bond_idx": predicted_bundle["anchor_bond_idx"],
        "predicted_mask_available": bool(predicted_bundle["available"]),
        "predicted_mask_reason": predicted_bundle["reason"],
        "random_mask_rgroup": random_bundle["rgroup"],
        "random_mask_atom_indices": _json_list(random_bundle["atom_indices"]),
        "random_keep_atom_indices": _json_list(random_bundle["keep_atom_indices"]),
        "random_anchor_scaffold_atom_idx": random_bundle["anchor_scaffold_atom_idx"],
        "random_anchor_rgroup_atom_idx": random_bundle["anchor_rgroup_atom_idx"],
        "random_anchor_bond_idx": random_bundle["anchor_bond_idx"],
        "random_mask_available": bool(random_bundle["available"]),
        "random_mask_policy": "size_matched_valid_single_anchor_rgroup",
        "random_mask_fallback_reason": random_reason,
        "random_equals_oracle": random_bundle["rgroup"] == target,
        "random_equals_predicted": random_bundle["rgroup"] == predicted,
        "old_clash_pairs_json": _json_list(old_pairs),
        "protein_clash_hot_atoms_json": _json_list(_protein_hot_atoms(old_pairs)),
        "protein_clash_hot_residues_json": _json_list(_protein_hot_residues(old_pairs)),
        "target_num_severe_pairs": _as_int(row.get("target_num_severe_pairs"), default=0),
        "non_target_num_severe_pairs": _as_int(row.get("non_target_num_severe_pairs"), default=0),
        "scaffold_num_severe_pairs": _as_int(row.get("scaffold_num_severe_pairs"), default=0),
        "num_total_severe_pairs": _as_int(row.get("num_total_severe_pairs"), default=0),
        "max_clash_depth": _as_float(row.get("max_clash_depth"), default=0.0),
        "total_clash_score": _as_float(row.get("total_clash_score"), default=0.0),
        "phase4_0_backend_feasibility_candidate": phase4_0,
        "phase4_1_formal_loop_candidate": phase4_1,
        "phase4_candidate_reason": candidate_reason,
        "phase4_exclusion_reason": exclusion_reason,
    }


def _s2_conflicts(row: pd.Series, phase2_sample: dict[str, Any], base_sample: dict[str, Any]) -> list[dict[str, Any]]:
    conflicts: list[dict[str, Any]] = []
    case_id = str(row.get("case_id") or "")
    target = str(row.get("target_rgroup") or "")
    predicted = str(row.get("predicted_dominant_valid_rgroup") or "")
    num_ligand_atoms = ligand_atom_count(phase2_sample, base_sample)
    oracle = build_mask_bundle(base_sample, target, num_ligand_atoms=num_ligand_atoms)
    if not oracle["available"]:
        conflicts.append(_conflict(case_id, "S2 case cannot recover oracle R-group atom set", oracle["reason"]))
    if oracle["available"] and not _anchor_available(oracle):
        conflicts.append(_conflict(case_id, "S2 case cannot recover oracle anchor", "missing oracle anchor field in processed base sample"))
    target_indices = _int_list_from_json(row.get("target_atom_indices"))
    if oracle["available"] and sorted(target_indices) != sorted(oracle["atom_indices"]):
        conflicts.append(_conflict(case_id, "target_atom_indices mismatch processed R-group atom set", f"manifest={target_indices}, processed={oracle['atom_indices']}"))
    old_pairs = list(phase2_sample.get("clash_report", {}).get("clash_pairs", []) or [])
    if not old_pairs:
        conflicts.append(_conflict(case_id, "S2 case cannot recover old clash evidence", "phase2 sample clash_report.clash_pairs is empty"))
    attribution_predicted = str(phase2_sample.get("attribution_report", {}).get("dominant_valid_rgroup") or "")
    if attribution_predicted != predicted:
        conflicts.append(_conflict(case_id, "predicted_dominant_valid_rgroup does not match phase2 attribution report", f"manifest={predicted}, sample_attribution={attribution_predicted}"))
    return conflicts


def _phase2_5_conflicts(phase2_5_taxonomy: pd.DataFrame) -> list[dict[str, Any]]:
    if phase2_5_taxonomy.empty:
        return []
    if "target_rgroup" not in phase2_5_taxonomy.columns:
        return []
    nonempty = phase2_5_taxonomy["target_rgroup"].dropna().astype(str).str.strip()
    if bool((nonempty != "").any()):
        return [
            {
                "conflict_id": "phase2_5_has_artificial_target_rgroup",
                "conflict_item": "phase2.5 model-induced samples contain target_rgroup values",
                "plan_statement": "阶段 2.5 model-induced samples 没有人工 target_rgroup, 且不得进入阶段 3 construction consistency denominator.",
                "actual_state": "failure_taxonomy.csv contains non-empty target_rgroup values.",
                "files": "reports/phase2_5_model_induced_audit/failure_taxonomy.csv",
                "impact": "Could incorrectly mix model-induced rows into artificial-label construction consistency.",
                "recommendation": "Stop and ask for manual confirmation before using phase2.5 rows.",
                "needs_manual_confirmation": True,
            }
        ]
    return []


def _conflict(case_id: str, item: str, actual_state: str) -> dict[str, Any]:
    return {
        "conflict_id": f"{case_id}:{item}",
        "conflict_item": item,
        "plan_statement": "S2 must recover oracle R-group atoms, anchor, old clash evidence and attribution report from existing phase2/processed data.",
        "actual_state": actual_state,
        "files": "data/benchmarks/clashrepairbench_rg_artificial/v0_1/manifest.parquet; data/benchmarks/clashrepairbench_rg_artificial/v0_1/samples/*.pkl; data/processed/v0_1/complexes/*.pkl",
        "impact": "Phase4 mask seed construction would have ambiguous or non-reproducible reference data.",
        "recommendation": "Stop phase3 execution for this conflict and request manual confirmation.",
        "needs_manual_confirmation": True,
    }


def _rank_random_candidates(
    candidates: list[dict[str, Any]],
    target_size: int,
    *,
    exclusions: set[str],
    seed: int,
    case_id: str,
    base_sample: dict[str, Any],
) -> list[dict[str, Any]]:
    eligible = [rgroup for rgroup in candidates if str(rgroup.get("rgroup_id")) not in exclusions]
    return sorted(
        eligible,
        key=lambda rgroup: (
            abs(rgroup_heavy_atom_count(base_sample, rgroup) - target_size),
            _stable_random_key(seed, case_id, str(rgroup.get("rgroup_id"))),
            str(rgroup.get("rgroup_id")),
        ),
    )


def _stable_random_key(seed: int, case_id: str, rgroup_id: str) -> int:
    payload = f"{seed}:{case_id}:{rgroup_id}".encode("utf-8")
    return int(hashlib.sha256(payload).hexdigest()[:16], 16)


def _metric_row(name: str, numerator: int, denominator: int, set_name: str, interpretation: str) -> dict[str, Any]:
    return {
        "metric_name": name,
        "set_name": set_name,
        "numerator": int(numerator),
        "denominator": int(denominator),
        "value": float(numerator / denominator) if denominator else 0.0,
        "interpretation": interpretation,
        "not_independent_locator_benchmark": True,
    }


def _metric_by_name(report: pd.DataFrame, name: str) -> dict[str, Any]:
    row = report[report["metric_name"] == name].iloc[0]
    return {
        "numerator": int(row["numerator"]),
        "denominator": int(row["denominator"]),
        "value": float(row["value"]),
    }


def _resolve_paths(config: dict[str, Any], *, repo_root: Path) -> dict[str, Path]:
    inputs = config.get("inputs", {})
    outputs = config.get("outputs", {})
    phase2_root = _resolve(inputs.get("phase2_benchmark_root", "data/benchmarks/clashrepairbench_rg_artificial/v0_1"), repo_root)
    return {
        "repo_root": repo_root,
        "phase2_benchmark_root": phase2_root,
        "phase2_manifest": _resolve(inputs.get("phase2_manifest", phase2_root / "manifest.parquet"), repo_root),
        "phase2_report_root": _resolve(inputs.get("phase2_report_root", "reports/phase2_injection"), repo_root),
        "processed_root": _resolve(inputs.get("processed_root", "data/processed/v0_1"), repo_root),
        "phase2_5_report_root": _resolve(inputs.get("phase2_5_report_root", "reports/phase2_5_model_induced_audit"), repo_root),
        "report_root": _resolve(outputs.get("report_root", "reports/phase3_label_provenance_audit"), repo_root),
        "conflict_report": _resolve(outputs.get("conflict_report", "tmp/20260513/phase3-label-provenance-mask-seed-conflict-report.md"), repo_root),
    }


def _resolve(value: str | Path, repo_root: Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (repo_root / path).resolve()


def _load_phase2_sample(row: pd.Series, benchmark_root: Path, cache: dict[str, dict[str, Any]]) -> dict[str, Any]:
    sample_path = benchmark_root / str(row.get("sample_path") or f"samples/{row.get('case_id')}.pkl")
    key = str(sample_path)
    if key not in cache:
        with sample_path.open("rb") as f:
            cache[key] = pickle.load(f)
    return cache[key]


def _load_base_sample(base_sample_id: str, processed_root: Path, cache: dict[str, dict[str, Any]]) -> dict[str, Any]:
    if base_sample_id not in cache:
        path = processed_root / "complexes" / f"{base_sample_id}.pkl"
        with path.open("rb") as f:
            cache[base_sample_id] = pickle.load(f)
    return cache[base_sample_id]


def _read_csv_if_exists(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def _read_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(_jsonable(data), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _label_provenance_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Phase 3 Label Provenance Audit",
        "",
        "## 1. Scope",
        "",
        "- 阶段 3 = label provenance audit + circularity risk audit + construction consistency check + phase4 mask seed generation.",
        "- 阶段 3 不承担 independent locator benchmark 职责.",
        "- `target_rgroup` 是人工扰动标签和参考掩码来源, 不是无偏定位真值.",
        "- `predicted_dominant_valid_rgroup` 是 operational mask policy, 不是 ground truth.",
        "",
        "## 2. Counts",
        "",
        f"- phase2 manifest rows: {summary['phase2_manifest_rows']}",
        f"- S0 rows: {summary['set_counts']['S0_all_valid_injection_attempts']}",
        f"- S1 rows: {summary['set_counts']['S1_oracle_target_local_clash_set']}",
        f"- S2 rows: {summary['set_counts']['S2_phase2_supported_single_rgroup']}",
        f"- phase4 mask seed rows: {summary['phase4_mask_seed']['rows']}",
        "",
        "## 3. Provenance Decisions",
        "",
        "- `target_score_ratio_valid` 来自 attribution-derived valid R-group scores, 并参与 supported gate.",
        "- `supported_single_rgroup` 是 clean local repair substrate.",
        "- phase2.5 model-induced rows 没有进入 construction consistency denominator.",
        "",
    ]
    return "\n".join(lines)


def _circularity_markdown(summary: dict[str, Any]) -> str:
    cc = summary["construction_consistency"]
    lines = [
        "# Phase 3 Circularity Risk Audit",
        "",
        "## 1. Risk Statement",
        "",
        "- S2 使用 detector / attribution / target-dominance gates 过滤, circularity risk level 为 high.",
        "- S2 上的 Top-1 / Top-3 只解释为 construction consistency check.",
        "- S0 / S1 只做辅助审计和压力分析, 不作为阶段 4 主输入.",
        "",
        "## 2. Construction Consistency",
        "",
        f"- denominator set: {cc['denominator_set']}",
        f"- denominator: {cc['denominator']}",
        f"- top1 predicted equals oracle: {cc['top1_predicted_equals_oracle']['numerator']} / {cc['top1_predicted_equals_oracle']['denominator']}",
        f"- top3 target in top valid R-groups: {cc['top3_target_in_top_valid_rgroups']['numerator']} / {cc['top3_target_in_top_valid_rgroups']['denominator']}",
        "",
        "## 3. Phase 4 Mask Policy",
        "",
        "- Oracle mask: target R-group entire atom set.",
        "- Predicted mask: predicted dominant valid R-group entire atom set.",
        "- Random mask: same-ligand size-matched valid single-anchor R-group.",
        "- Anchor is recorded separately and is not added to the free edit mask by default.",
        "",
    ]
    return "\n".join(lines)


def _completion_audit_markdown(summary: dict[str, Any], output_paths: dict[str, Path]) -> str:
    lines = [
        "# Phase 3 Completion Audit",
        "",
        "## 1. Checklist",
        "",
        "| item | status | evidence |",
        "|---|---|---|",
        f"| config loaded | done | `configs/phase3_label_provenance_audit.yaml` |",
        f"| phase4 mask seed generated | done | `{_relpath(output_paths['phase4_mask_seed'], Path.cwd())}` rows={summary['phase4_mask_seed']['rows']} |",
        f"| construction consistency generated | done | `{_relpath(output_paths['construction_consistency'], Path.cwd())}` |",
        f"| phase2.5 excluded from denominator | done | included=false, rows={summary['phase2_5_model_induced_audit']['failure_taxonomy_rows']} |",
        "| no model training | done | phase3 scope is audit and seed generation only |",
        "| no generator call | done | script only reads phase2/processed/phase2.5 reports |",
        "| no molecule repair | done | no repair backend invoked |",
        "| no phase3 final experiment report | done | only audit markdown files generated |",
        "",
        "## 2. Generated Reports",
        "",
    ]
    for key, path in output_paths.items():
        lines.append(f"- {key}: `{_relpath(path, Path.cwd())}`")
    lines.append("")
    return "\n".join(lines)


def _git_info(repo_root: Path) -> dict[str, str]:
    return {
        "status_short": _git(["status", "--short"], repo_root),
        "branch": _git(["branch", "--show-current"], repo_root),
        "head": _git(["rev-parse", "HEAD"], repo_root),
    }


def _git(args: list[str], repo_root: Path) -> str:
    result = subprocess.run(["git", *args], cwd=repo_root, check=False, text=True, capture_output=True)
    return result.stdout.strip()


def _protein_hot_atoms(clash_pairs: list[dict[str, Any]]) -> list[int]:
    atoms = {_as_int(pair.get("protein_atom_idx"), default=-1) for pair in clash_pairs}
    return sorted(idx for idx in atoms if idx >= 0)


def _protein_hot_residues(clash_pairs: list[dict[str, Any]]) -> list[str]:
    residues = {str(pair.get("protein_residue_key") or "") for pair in clash_pairs}
    return sorted(residue for residue in residues if residue)


def _empty_mask_bundle(rgroup_id: str, reason: str) -> dict[str, Any]:
    return {
        "rgroup": rgroup_id,
        "atom_indices": [],
        "keep_atom_indices": [],
        "anchor_scaffold_atom_idx": "",
        "anchor_rgroup_atom_idx": "",
        "anchor_bond_idx": "",
        "available": False,
        "reason": reason,
    }


def _anchor_available(bundle: dict[str, Any]) -> bool:
    return all(bundle.get(key) not in ("", None) for key in ("anchor_scaffold_atom_idx", "anchor_rgroup_atom_idx", "anchor_bond_idx"))


def _row_value(row: pd.Series | dict[str, Any], key: str) -> Any:
    return row.get(key, None)


def _missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    return False


def _as_bool(value: Any) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if _missing(value):
        return False
    text = str(value).strip().lower()
    return text in {"1", "true", "yes", "y"}


def _as_int(value: Any, *, default: int) -> int:
    if _missing(value) or str(value).strip() == "":
        return default
    return int(float(value))


def _as_float(value: Any, *, default: float) -> float:
    if _missing(value) or str(value).strip() == "":
        return default
    return float(value)


def _optional_int(value: Any) -> int | str:
    if _missing(value) or str(value).strip() == "":
        return ""
    return int(float(value))


def _int_list(value: Any) -> list[int]:
    if value is None:
        return []
    return sorted({int(item) for item in list(value)})


def _int_list_from_json(value: Any) -> list[int]:
    if isinstance(value, list):
        return _int_list(value)
    parsed = parse_json_list(value)
    return _int_list(parsed)


def _json_list(value: Any) -> str:
    return json.dumps(_jsonable(value), ensure_ascii=False)


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def _relpath(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)
