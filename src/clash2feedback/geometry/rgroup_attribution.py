from __future__ import annotations

from collections import defaultdict
from typing import Any

import numpy as np


def ligand_atom_regions(sample: dict[str, Any]) -> list[str]:
    ligand = sample.get("ligand", {})
    num_atoms = int(ligand.get("num_atoms") or len(ligand.get("elements", [])) or np.asarray(ligand.get("coords")).shape[0])
    masks = sample.get("masks", {})
    scaffold_mask = np.asarray(masks.get("ligand_scaffold_mask", np.zeros(num_atoms, dtype=bool)), dtype=bool)
    rgroup_ids = list(masks.get("ligand_rgroup_id", [None] * num_atoms))
    is_rgroup = np.asarray(masks.get("ligand_is_rgroup", np.zeros(num_atoms, dtype=bool)), dtype=bool)
    valid_rgroups = _valid_rgroup_ids(sample)

    regions: list[str] = []
    for atom_idx in range(num_atoms):
        if atom_idx < scaffold_mask.shape[0] and bool(scaffold_mask[atom_idx]):
            regions.append("scaffold")
            continue
        rgroup_id = rgroup_ids[atom_idx] if atom_idx < len(rgroup_ids) else None
        if rgroup_id:
            regions.append(str(rgroup_id) if str(rgroup_id) in valid_rgroups else "unsupported_rgroup")
            continue
        if atom_idx < is_rgroup.shape[0] and bool(is_rgroup[atom_idx]):
            regions.append("unsupported_rgroup")
        else:
            regions.append("unknown")
    return regions


def ligand_region_warnings(sample: dict[str, Any]) -> list[str]:
    ligand = sample.get("ligand", {})
    num_atoms = int(ligand.get("num_atoms") or len(ligand.get("elements", [])) or np.asarray(ligand.get("coords")).shape[0])
    masks = sample.get("masks", {})
    warnings: list[str] = []
    for key in ("ligand_scaffold_mask", "ligand_is_rgroup", "heavy_atom_mask"):
        if key in masks and len(masks[key]) != num_atoms:
            warnings.append(f"unsupported_mask:{key}_length_mismatch")
    if "ligand_rgroup_id" in masks and len(masks["ligand_rgroup_id"]) != num_atoms:
        warnings.append("unsupported_mask:ligand_rgroup_id_length_mismatch")
    return warnings


def attribute_clashes_to_rgroups(
    sample: dict[str, Any],
    clash_report: dict[str, Any],
    alpha: float = 0.5,
    single_region_threshold: float = 0.7,
    ambiguous_threshold: float = 0.5,
) -> dict[str, Any]:
    regions = ligand_atom_regions(sample)
    region_sizes = _region_heavy_atom_counts(sample, regions)
    region_scores: dict[str, float] = defaultdict(float)
    for pair in clash_report.get("clash_pairs", []):
        ligand_idx = int(pair["ligand_atom_idx"])
        region = pair.get("ligand_region") or (regions[ligand_idx] if ligand_idx < len(regions) else "unknown")
        depth = float(pair.get("clash_depth") or 0.0)
        if depth > 0.0:
            region_scores[str(region)] += depth * depth

    for region in sorted(set(regions) | set(region_scores)):
        region_scores.setdefault(region, 0.0)

    normalized_region_scores: dict[str, float] = {}
    for region, score in region_scores.items():
        size = max(float(region_sizes.get(region, 1)), 1.0)
        normalized_region_scores[region] = float(score) / (size**float(alpha))

    severe_count = int(clash_report.get("num_severe_clash_pairs") or 0)
    unsupported_reasons = [str(item) for item in clash_report.get("unsupported_reasons", [])]
    top_regions = _top_regions(normalized_region_scores)
    dominant_region_all = top_regions[0]["region"] if top_regions else ""
    total_score = float(sum(score for score in normalized_region_scores.values() if score > 0.0))
    dominant_score_all = float(normalized_region_scores.get(dominant_region_all, 0.0))
    dominant_ratio_all = dominant_score_all / total_score if total_score > 0.0 else 0.0
    valid_rgroup_scores = {
        region: float(score)
        for region, score in normalized_region_scores.items()
        if _is_valid_rgroup_region(region)
    }
    top_valid_rgroups = _top_regions(valid_rgroup_scores)
    dominant_valid_rgroup = top_valid_rgroups[0]["region"] if top_valid_rgroups else ""
    total_valid_score = float(sum(score for score in valid_rgroup_scores.values() if score > 0.0))
    dominant_valid_score = float(valid_rgroup_scores.get(dominant_valid_rgroup, 0.0))
    dominant_ratio_valid = dominant_valid_score / total_valid_score if total_valid_score > 0.0 else 0.0
    num_nonzero_valid_rgroups = _num_scored_rgroups(valid_rgroup_scores)
    scaffold_score = float(normalized_region_scores.get("scaffold", 0.0))
    unsupported_region_score = float(normalized_region_scores.get("unsupported_rgroup", 0.0))
    unknown_region_score = float(normalized_region_scores.get("unknown", 0.0))

    if _has_unsupported_chemistry(unsupported_reasons):
        failure_type = "unsupported_chemistry"
        recommended_action = "reject"
    elif _has_unsupported_analysis(unsupported_reasons):
        failure_type = "unknown_or_unsupported"
        recommended_action = "reject"
    elif severe_count == 0:
        dominant_region_all = ""
        dominant_ratio_all = 0.0
        failure_type = "no_clash"
        recommended_action = "no_repair_needed"
    elif dominant_region_all in {"unsupported_rgroup", "unknown"}:
        failure_type = "unsupported_chemistry" if _has_unsupported_chemistry(unsupported_reasons) else "unknown_or_unsupported"
        recommended_action = "reject"
    elif dominant_region_all == "scaffold":
        failure_type = "scaffold_clash"
        recommended_action = "reject"
    elif _is_valid_rgroup_region(dominant_region_all) and dominant_ratio_all >= float(single_region_threshold):
        failure_type = "single_rgroup_clash"
        recommended_action = "local_rgroup_repair"
    elif _looks_global(normalized_region_scores, dominant_ratio_all, ambiguous_threshold):
        failure_type = "global_pose_failure"
        recommended_action = "full_resampling_or_reject"
    elif dominant_ratio_all >= float(ambiguous_threshold):
        failure_type = "ambiguous_region_clash"
        recommended_action = "reject_or_expand_mask"
    elif _num_scored_rgroups(normalized_region_scores) >= 2:
        failure_type = "multi_region_clash"
        recommended_action = "reject"
    else:
        failure_type = "unknown_or_unsupported"
        recommended_action = "reject"

    return {
        "sample_id": clash_report.get("sample_id") or sample.get("sample_id", ""),
        "region_scores": dict(sorted(region_scores.items())),
        "normalized_region_scores": dict(sorted(normalized_region_scores.items())),
        "dominant_region": dominant_region_all,
        "dominant_ratio": float(dominant_ratio_all),
        "dominant_region_all": dominant_region_all,
        "dominant_ratio_all_regions": float(dominant_ratio_all),
        "dominant_valid_rgroup": dominant_valid_rgroup,
        "dominant_ratio_valid_rgroups": float(dominant_ratio_valid),
        "num_nonzero_valid_rgroups": int(num_nonzero_valid_rgroups),
        "scaffold_score": scaffold_score,
        "unsupported_region_score": unsupported_region_score,
        "unknown_region_score": unknown_region_score,
        "valid_rgroup_scores": dict(sorted(valid_rgroup_scores.items())),
        "all_region_scores": dict(sorted(normalized_region_scores.items())),
        "top_valid_rgroups": top_valid_rgroups,
        "failure_type": failure_type,
        "recommended_action": recommended_action,
        "top_regions": top_regions,
    }


def _valid_rgroup_ids(sample: dict[str, Any]) -> set[str]:
    result: set[str] = set()
    for rgroup in sample.get("rgroups", []):
        rgroup_id = rgroup.get("rgroup_id")
        if rgroup_id and bool(rgroup.get("is_valid_for_phase0", True)):
            result.add(str(rgroup_id))
    return result


def _region_heavy_atom_counts(sample: dict[str, Any], regions: list[str]) -> dict[str, int]:
    ligand = sample.get("ligand", {})
    atomic_numbers = list(ligand.get("atomic_numbers", []))
    if not atomic_numbers:
        atomic_numbers = [6] * len(regions)
    counts: dict[str, int] = defaultdict(int)
    for atom_idx, region in enumerate(regions):
        atomic_number = int(atomic_numbers[atom_idx]) if atom_idx < len(atomic_numbers) else 6
        if atomic_number > 1:
            counts[region] += 1
    return dict(counts)


def _top_regions(scores: dict[str, float]) -> list[dict[str, float | str]]:
    return [
        {"region": region, "score": float(score)}
        for region, score in sorted(scores.items(), key=lambda item: (-item[1], item[0]))
        if float(score) > 0.0
    ]


def _has_unsupported_chemistry(reasons: list[str]) -> bool:
    return any("covalent" in reason or "metal" in reason for reason in reasons)


def _has_unsupported_analysis(reasons: list[str]) -> bool:
    return any(
        reason.startswith("unsupported_")
        or reason.startswith("full_receptor_dynamic_shell")
        or reason.startswith("partial_due_to")
        for reason in reasons
    )


def _is_valid_rgroup_region(region: str) -> bool:
    return region.startswith("R") and region[1:].isdigit()


def _num_scored_rgroups(scores: dict[str, float]) -> int:
    return sum(1 for region, score in scores.items() if _is_valid_rgroup_region(region) and float(score) > 0.0)


def _looks_global(scores: dict[str, float], dominant_ratio: float, ambiguous_threshold: float) -> bool:
    nonzero_regions = [region for region, score in scores.items() if float(score) > 0.0]
    return len(nonzero_regions) >= 4 and dominant_ratio < float(ambiguous_threshold)
