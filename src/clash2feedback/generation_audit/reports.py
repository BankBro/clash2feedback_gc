from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from clash2feedback.generation_audit.gap_analysis import GAP_COLUMNS
from clash2feedback.generation_audit.ligand_validity import LIGAND_VALIDITY_COLUMNS
from clash2feedback.generation_audit.overlap import OVERLAP_COLUMNS
from clash2feedback.generation_audit.taxonomy import FAILURE_TAXONOMY_COLUMNS, REPAIRABILITY_PROXY_COLUMNS


BASE_SELECTION_COLUMNS = [
    "base_sample_id",
    "base_complex_id",
    "base_split",
    "target_id",
    "split_group",
    "num_valid_rgroups",
    "num_single_anchor_rgroups",
    "protein_scope",
    "overlap_tier",
    "external_validity_eligible",
    "selected_for_generation",
    "selection_reason",
]

GENERATION_MANIFEST_COLUMNS = [
    "candidate_id",
    "base_sample_id",
    "base_complex_id",
    "base_split",
    "target_id",
    "split_group",
    "overlap_tier",
    "external_validity_eligible",
    "model_name",
    "checkpoint_name",
    "checkpoint_path",
    "checkpoint_md5",
    "checkpoint_sha256",
    "checkpoint_file_size",
    "seed",
    "n_samples",
    "cuda_device",
    "generation_command",
    "inference_config_json",
    "raw_output_path",
    "standardized_output_path",
    "generation_status",
    "postprocess_stage",
    "postprocess_status",
    "sanitize_flag",
    "relax_flag",
    "readable",
    "ligand_valid",
    "failure_taxonomy",
    "repairability_proxy",
]

MODEL_CLASH_COLUMNS = [
    "candidate_id",
    "base_sample_id",
    "postprocess_stage",
    "receptor_scope",
    "delta_angstrom",
    "num_clash_pairs",
    "num_severe_clash_pairs",
    "total_clash_score",
    "max_clash_depth",
    "mean_clash_depth",
    "delta03_status",
    "delta04_status",
    "delta05_status",
]

VISUAL_QC_COLUMNS = [
    "candidate_id",
    "postprocess_stage",
    "failure_taxonomy",
    "repairability_proxy",
    "raw_output_path",
    "standardized_output_path",
    "visual_qc_status",
    "notes",
]


def empty_dataframe(columns: list[str]) -> pd.DataFrame:
    return pd.DataFrame(columns=columns)


def select_base_pockets(
    audit_df: pd.DataFrame,
    manifest: pd.DataFrame,
    *,
    max_pockets: int,
    preferred_splits: list[str],
    preferred_tiers: list[str],
    phase2_base_report: pd.DataFrame | None = None,
) -> pd.DataFrame:
    manifest_small = manifest.copy()
    manifest_small = manifest_small.rename(columns={"sample_id": "base_sample_id", "complex_id": "base_complex_id"})
    cols = ["base_sample_id", "num_valid_rgroups", "num_single_anchor_rgroups"]
    merged = audit_df.merge(manifest_small[[c for c in cols if c in manifest_small]], on="base_sample_id", how="left")
    if phase2_base_report is not None and not phase2_base_report.empty:
        base_report = phase2_base_report.rename(columns={"sample_id": "base_sample_id", "complex_id": "base_complex_id"})
        extra = ["base_sample_id", "base_clean_pass", "failure_reason"]
        merged = merged.merge(base_report[[c for c in extra if c in base_report]], on="base_sample_id", how="left")
    else:
        merged["base_clean_pass"] = True
        merged["failure_reason"] = ""

    tier_rank = {tier: idx for idx, tier in enumerate(preferred_tiers)}
    split_rank = {split: idx for idx, split in enumerate(preferred_splits)}
    merged["_tier_rank"] = merged["overlap_tier"].map(lambda value: tier_rank.get(str(value), 999))
    merged["_split_rank"] = merged["base_split"].map(lambda value: split_rank.get(str(value), 999))
    eligible = (
        merged["base_split"].isin(preferred_splits)
        & merged["overlap_tier"].isin(preferred_tiers)
        & merged["external_validity_eligible"].astype(bool)
        & merged["base_clean_pass"].fillna(True).astype(bool)
        & (pd.to_numeric(merged.get("num_valid_rgroups", 0), errors="coerce").fillna(0) >= 1)
        & (pd.to_numeric(merged.get("num_single_anchor_rgroups", 0), errors="coerce").fillna(0) >= 1)
    )
    selected_ids = set(
        merged[eligible]
        .sort_values(["_tier_rank", "_split_rank", "base_sample_id"])
        .head(int(max_pockets))["base_sample_id"]
        .tolist()
    )
    rows: list[dict[str, Any]] = []
    for _, row in merged.sort_values(["_tier_rank", "_split_rank", "base_sample_id"]).iterrows():
        selected = str(row["base_sample_id"]) in selected_ids
        rows.append(
            {
                "base_sample_id": row.get("base_sample_id", ""),
                "base_complex_id": row.get("base_complex_id", ""),
                "base_split": row.get("base_split", ""),
                "target_id": row.get("target_id", ""),
                "split_group": row.get("split_group", ""),
                "num_valid_rgroups": int(row.get("num_valid_rgroups") or 0),
                "num_single_anchor_rgroups": int(row.get("num_single_anchor_rgroups") or 0),
                "protein_scope": "pocket10_all_atoms",
                "overlap_tier": row.get("overlap_tier", ""),
                "external_validity_eligible": bool(row.get("external_validity_eligible", False)),
                "selected_for_generation": bool(selected),
                "selection_reason": "selected" if selected else _selection_reject_reason(row, preferred_splits, preferred_tiers),
            }
        )
    return pd.DataFrame(rows, columns=BASE_SELECTION_COLUMNS)


def build_summary(
    *,
    config: dict[str, Any],
    overlap_summary: dict[str, Any],
    base_selection: pd.DataFrame,
    generation_manifest: pd.DataFrame,
    ligand_validity: pd.DataFrame,
    failure_taxonomy: pd.DataFrame,
    repairability_proxy: pd.DataFrame,
    blocked_reasons: list[str],
    checkpoint_meta: dict[str, Any] | None = None,
    external_setup: dict[str, Any] | None = None,
) -> dict[str, Any]:
    checkpoint_meta = checkpoint_meta or {}
    external_setup = external_setup or {}
    taxonomy_counts = failure_taxonomy["failure_taxonomy"].value_counts(dropna=False).to_dict() if not failure_taxonomy.empty else {}
    proxy_counts = repairability_proxy["repairability_proxy"].value_counts(dropna=False).to_dict() if not repairability_proxy.empty else {}
    ligand_valid = ligand_validity["ligand_validity_status"].eq("valid") if not ligand_validity.empty else pd.Series(dtype=bool)
    tier_counts = overlap_summary.get("tier_counts", {})
    baseline_cfg = config.get("baseline", {})
    return {
        "schema_version": "phase2_5_v0_1",
        "audit_type": "external_validity_audit",
        "baseline_model": str(baseline_cfg.get("model_name", "DiffSBDD")),
        "baseline_conda_env": str(baseline_cfg.get("conda_env", "")),
        "diffsbdd_repo_commit": str(external_setup.get("external_repo_commit") or checkpoint_meta.get("external_repo_commit") or baseline_cfg.get("external_repo_commit", "")),
        "diffsbdd_expected_repo_commit": str(baseline_cfg.get("external_repo_commit", "")),
        "diffsbdd_env_check_status": str(external_setup.get("env_check_status") or checkpoint_meta.get("env_check_status") or ""),
        "diffsbdd_cuda_available": bool(external_setup.get("cuda_available") or checkpoint_meta.get("cuda_available") or False),
        "checkpoint_name": str(baseline_cfg.get("checkpoint_name", "")),
        "checkpoint_path": str(checkpoint_meta.get("checkpoint_path") or baseline_cfg.get("checkpoint_path", "")),
        "checkpoint_md5": str(checkpoint_meta.get("checkpoint_md5") or _first_nonempty(generation_manifest, "checkpoint_md5")),
        "checkpoint_sha256": str(checkpoint_meta.get("checkpoint_sha256") or _first_nonempty(generation_manifest, "checkpoint_sha256")),
        "checkpoint_file_size": int(checkpoint_meta.get("checkpoint_file_size") or 0),
        "num_base_pockets_selected": int(base_selection["selected_for_generation"].sum()) if "selected_for_generation" in base_selection else 0,
        "num_generated_total": int(generation_manifest["candidate_id"].nunique()) if not generation_manifest.empty else 0,
        "num_readable": int(generation_manifest["readable"].sum()) if "readable" in generation_manifest else 0,
        "num_ligand_valid": int(ligand_valid.sum()) if not ligand_validity.empty else 0,
        "num_ligand_invalid": int((~ligand_valid).sum()) if not ligand_validity.empty else 0,
        "num_rgroup_attributable": int(failure_taxonomy["rgroup_attributable"].sum()) if "rgroup_attributable" in failure_taxonomy else 0,
        "num_with_severe_clash": int((failure_taxonomy["failure_taxonomy"].isin(["single_rgroup_clash", "multi_region_clash", "scaffold_clash", "global_pose_failure", "pocket_mismatch_or_out_of_scope"])).sum()) if "failure_taxonomy" in failure_taxonomy else 0,
        "num_single_rgroup_clash": int(taxonomy_counts.get("single_rgroup_clash", 0)),
        "num_multi_region_clash": int(taxonomy_counts.get("multi_region_clash", 0)),
        "num_scaffold_clash": int(taxonomy_counts.get("scaffold_clash", 0)),
        "num_global_pose_failure": int(taxonomy_counts.get("global_pose_failure", 0)),
        "num_near_miss_contact": int(taxonomy_counts.get("near_miss_contact", 0)),
        "num_local_rgroup_repair_possible": int(proxy_counts.get("local_rgroup_repair_possible", 0)),
        "phase2_coverage_proxy": _coverage_proxy(proxy_counts, generation_manifest),
        "training_overlap_audit_done": True,
        "num_pockets_t0_exact_pair_seen": int(tier_counts.get("T0_exact_pair_seen", 0)),
        "num_pockets_t1_same_target_seen": int(tier_counts.get("T1_same_pocket_or_target_seen", 0)),
        "num_pockets_t3_official_diffsbdd_test": int(tier_counts.get("T3_official_diffsbdd_test", 0)),
        "num_pockets_t4_external_unseen": int(tier_counts.get("T4_external_unseen", 0)),
        "num_pockets_t_unknown": int(tier_counts.get("T_unknown", 0)),
        "external_validity_subset_size": int(overlap_summary.get("external_validity_subset_size", 0)),
        "same_source_debug_subset_size": int(overlap_summary.get("same_source_debug_subset_size", 0)),
        "does_not_train": bool(config.get("constraints", {}).get("do_not_train", True)),
        "does_not_repair": bool(config.get("constraints", {}).get("do_not_repair", True)),
        "does_not_rank_baselines": bool(config.get("constraints", {}).get("do_not_rank_baselines", True)),
        "does_not_modify_phase2_v0_1": bool(config.get("constraints", {}).get("do_not_modify_phase2_v0_1", True)),
        "blocked_reasons": blocked_reasons,
    }


def write_visual_qc_notes(path: Path, visual_df: pd.DataFrame, blocked_reasons: list[str]) -> None:
    lines = [
        "# Phase 2.5 Visual QC Notes",
        "",
        "- status: pending_manual_review" if not visual_df.empty else "- status: no_generated_cases",
        "- 本文件只记录抽样清单和阻塞状态, 不把自动分类解释为人工 pass.",
    ]
    if blocked_reasons:
        lines.append("- blocked: " + "; ".join(blocked_reasons))
    lines.extend(["", "## 1. Cases", ""])
    if visual_df.empty:
        lines.append("- no cases selected")
    else:
        for _, row in visual_df.iterrows():
            lines.append(f"- {row['candidate_id']}: {row['failure_taxonomy']}, {row['visual_qc_status']}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_phase2_5_audit(path: Path, summary: dict[str, Any], blocked_reasons: list[str]) -> None:
    lines = [
        "# Phase 2.5 Model-Induced Audit",
        "",
        "## 1. Summary",
        "",
        "```json",
        json.dumps(summary, ensure_ascii=False, indent=2),
        "```",
        "",
        "## 2. Boundary",
        "",
        "- 本阶段不训练模型, 不做 repair, 不调参, 不做 baseline ranking.",
        "- generated ligand 没有 oracle `target_rgroup`; predicted dominant R-group 只作为 taxonomy / proxy 信号.",
        "- model-induced samples 不进入阶段 3 Top-1 / Top-3 主评估.",
        "",
        "## 3. Blocked",
        "",
    ]
    if blocked_reasons:
        lines.extend(f"- {reason}" for reason in blocked_reasons)
    else:
        lines.append("- none")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_completion_audit(
    path: Path,
    *,
    checklist: list[tuple[str, str, str]],
    commands: list[str],
    summary: dict[str, Any],
    blocked_reasons: list[str],
    compileall_result: str = "not_recorded_yet",
    pytest_result: str = "not_recorded_yet",
    file_status_lines: list[str] | None = None,
) -> None:
    file_status_lines = file_status_lines or []
    lines = [
        "# Phase 2.5 Completion Audit",
        "",
        "## 1. Checklist",
        "",
        "| item | status | notes |",
        "|---|---|---|",
    ]
    lines.extend(f"| {item} | {status} | {notes} |" for item, status, notes in checklist)
    lines.extend(
        [
            "",
            "## 2. Commands",
            "",
            "```bash",
            *commands,
            "```",
            "",
            "## 3. Verification",
            "",
            f"- compileall: {compileall_result}",
            f"- pytest: {pytest_result}",
            "",
            "## 4. Summary",
            "",
            "```json",
            json.dumps(summary, ensure_ascii=False, indent=2),
            "```",
            "",
            "## 5. Files",
            "",
        ]
    )
    if file_status_lines:
        lines.extend(f"- {line}" for line in file_status_lines)
    else:
        lines.append("- not_recorded")
    lines.extend(
        [
            "",
            "## 6. Blocked",
            "",
        ]
    )
    if blocked_reasons:
        lines.extend(f"- {reason}" for reason in blocked_reasons)
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## 7. Conclusion Boundary",
            "",
            "- 当前报告只对已生成或已阻塞项给出审计结论.",
            "- DiffSBDD/checkpoint/official split 缺失时, external validity 结论必须保守.",
            "- 阶段 3 继续只使用 phase2 `supported_single_rgroup` 主评估集; 阶段 4 才进入 repair loop.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def schema_empty_reports() -> dict[str, pd.DataFrame]:
    return {
        "training_overlap_audit.csv": empty_dataframe(OVERLAP_COLUMNS),
        "base_pocket_selection.csv": empty_dataframe(BASE_SELECTION_COLUMNS),
        "generation_manifest.parquet": empty_dataframe(GENERATION_MANIFEST_COLUMNS),
        "ligand_validity.csv": empty_dataframe(LIGAND_VALIDITY_COLUMNS),
        "model_induced_clash_report.csv": empty_dataframe(MODEL_CLASH_COLUMNS),
        "failure_taxonomy.csv": empty_dataframe(FAILURE_TAXONOMY_COLUMNS),
        "repairability_proxy.csv": empty_dataframe(REPAIRABILITY_PROXY_COLUMNS),
        "artificial_vs_model_induced_gap.csv": empty_dataframe(GAP_COLUMNS),
        "visual_qc_cases.csv": empty_dataframe(VISUAL_QC_COLUMNS),
    }


def _selection_reject_reason(row: pd.Series, preferred_splits: list[str], preferred_tiers: list[str]) -> str:
    if row.get("base_split") not in preferred_splits:
        return "base_split_not_preferred"
    if row.get("overlap_tier") not in preferred_tiers:
        return "overlap_tier_not_preferred"
    if not bool(row.get("external_validity_eligible", False)):
        return "not_external_validity_eligible"
    if not bool(row.get("base_clean_pass", True)):
        return f"base_clean_failed:{row.get('failure_reason', '')}"
    if int(row.get("num_valid_rgroups") or 0) < 1:
        return "no_valid_rgroup"
    if int(row.get("num_single_anchor_rgroups") or 0) < 1:
        return "no_single_anchor_rgroup"
    return "not_selected_due_to_max_pockets"


def _first_nonempty(df: pd.DataFrame, column: str) -> str:
    if column not in df or df.empty:
        return ""
    values = [str(value) for value in df[column].dropna().tolist() if str(value)]
    return values[0] if values else ""


def _coverage_proxy(proxy_counts: dict[str, Any], generation_manifest: pd.DataFrame) -> float:
    total = int(generation_manifest["candidate_id"].nunique()) if not generation_manifest.empty else 0
    if total <= 0:
        return 0.0
    return float(proxy_counts.get("local_rgroup_repair_possible", 0)) / float(total)
