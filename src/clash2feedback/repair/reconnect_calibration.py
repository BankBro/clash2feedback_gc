from __future__ import annotations

import hashlib
import json
import math
import subprocess
from pathlib import Path
from typing import Any

import pandas as pd

from clash2feedback.repair.fragment_diagnostics import analyze_candidate_fragment
from clash2feedback.repair.phase4_inputs import load_phase4_case_inputs, read_first_mol
from clash2feedback.utils.config import resolve_repo_path
from clash2feedback.verifier.phase4_adapter import RELIABLE_REPAIR_FIELDS


RECONNECT_LABELS = [
    "single_anchor_reconnect_pass",
    "multi_attachment_out_of_scope",
    "invalid_reconnect",
]

REQUIRED_DIFFSBDD_VERIFIER_COLUMNS = [
    "case_id",
    "base_sample_id",
    "candidate_id",
    "candidate_path",
    "candidate_budget_k",
    "backend_name",
    "candidate_readable",
    "ligand_valid",
    "fixed_structure_match_success",
    "anchor_integrity",
    "local_reconnect_pass",
    "local_reconnect_failure_reason",
    "anchor_reconnect_status",
    "anchor_reconnect_reason",
    "anchor_match_success",
    "generated_fragment_connected_to_anchor",
    "generated_fragment_attachment_count",
    "num_anchor_neighbors",
    "num_extra_attachments",
    "floating_fragment_detected",
    "candidate_single_fragment",
    "candidate_total_fragment_count",
    "target_mask_heavy_atom_count",
    "generated_fragment_heavy_atom_count",
    "generated_fragment_size_diff",
    "generated_element_mismatch_count",
    "old_clash_resolved",
    "no_new_severe_clash",
    "scaffold_stable",
    "keep_region_stable",
    "edit_compliance",
    "pocket_retention",
    "reliable_repair_success",
]


class CalibrationConflict(RuntimeError):
    def __init__(self, items: list[dict[str, str]]):
        super().__init__("phase4.0.1a calibration conflict")
        self.items = items


def run_phase4_0_1a(config: dict[str, Any], *, repo_root: Path) -> dict[str, Any]:
    report_root = resolve_repo_path(config["outputs"]["report_root"], repo_root=repo_root)
    report_root.mkdir(parents=True, exist_ok=True)
    conflict_report = resolve_repo_path(config["outputs"]["conflict_report"], repo_root=repo_root)
    try:
        return _run_phase4_0_1a(config, repo_root=repo_root, report_root=report_root)
    except CalibrationConflict as exc:
        conflict_report.parent.mkdir(parents=True, exist_ok=True)
        conflict_report.write_text(_conflict_report_markdown(exc.items), encoding="utf-8")
        summary = {
            "schema_version": config.get("schema_version", "phase4_0_1a_local_reconnect_calibration_v0_1"),
            "mode": "report_only_audit_only",
            "status": "blocked_conflict",
            "conflict_report": str(conflict_report),
            "conflict_count": len(exc.items),
        }
        (report_root / "local_reconnect_calibration_summary.json").write_text(
            json.dumps(_jsonable(summary), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return {"summary": summary, "report_paths": {"summary": report_root / "local_reconnect_calibration_summary.json", "conflict_report": conflict_report}}


def _run_phase4_0_1a(config: dict[str, Any], *, repo_root: Path, report_root: Path) -> dict[str, Any]:
    inputs = config.get("inputs", {})
    calibration_cfg = config.get("calibration", {})
    input_paths = {key: resolve_repo_path(value, repo_root=repo_root) for key, value in inputs.items()}
    _validate_input_paths(input_paths)

    diffsbdd_verifier = pd.read_csv(input_paths["phase4_0_1_verifier_outcome"])
    diffsbdd_audit = pd.read_csv(input_paths["phase4_0_1_anchor_reconnect_audit"])
    diffsbdd_manifest = pd.read_csv(input_paths["phase4_0_1_candidate_manifest"])
    phase4_0_verifier = pd.read_csv(input_paths["phase4_0_verifier_outcome"])
    phase4_0_manifest = pd.read_csv(input_paths["phase4_0_candidate_manifest"])
    selected_cases = pd.read_csv(input_paths["phase4_0_1_selected_cases"])
    phase4_0_selected_cases = pd.read_csv(input_paths["phase4_0_selected_cases"])
    budget_curve = pd.read_csv(input_paths["phase4_0_1_budget_curve"])
    backend_comparison = pd.read_csv(input_paths["phase4_0_backend_comparison"])
    phase4_0_1_summary = json.loads(input_paths["phase4_0_1_summary"].read_text(encoding="utf-8"))

    _validate_diffsbdd_schema(diffsbdd_verifier, diffsbdd_audit, diffsbdd_manifest)
    _validate_phase4_0_schema(phase4_0_verifier, phase4_0_manifest)
    _validate_selected_cases(selected_cases, phase4_0_selected_cases)

    case_inputs = load_phase4_case_inputs(
        selected_cases,
        phase2_manifest_path=input_paths["phase2_manifest"],
        phase2_benchmark_root=input_paths["phase2_benchmark_root"],
        processed_root=input_paths["processed_root"],
    )
    case_by_id = {case_input.case_id: case_input for case_input in case_inputs}

    diffsbdd_reclassified = reclassify_diffsbdd_candidates(diffsbdd_verifier)
    rule_positive = build_rule_positive_checks(
        phase4_0_verifier,
        case_by_id=case_by_id,
        calibration_cfg=calibration_cfg,
    )
    clean_positive = build_clean_positive_checks(
        case_inputs,
        calibration_cfg=calibration_cfg,
    )
    synthetic_negative = build_synthetic_negative_checks(clean_positive)
    calibration_cases = pd.concat(
        [
            clean_positive,
            rule_positive,
            synthetic_negative,
        ],
        ignore_index=True,
        sort=False,
    )
    category_counts = reconnect_category_counts(diffsbdd_reclassified, calibration_cases)
    shadow = build_shadow_reliable_analysis(diffsbdd_reclassified)

    summary = build_summary(
        config=config,
        repo_root=repo_root,
        input_paths=input_paths,
        diffsbdd_reclassified=diffsbdd_reclassified,
        clean_positive=clean_positive,
        rule_positive=rule_positive,
        synthetic_negative=synthetic_negative,
        shadow=shadow,
        phase4_0_1_summary=phase4_0_1_summary,
        budget_curve=budget_curve,
        backend_comparison=backend_comparison,
    )

    paths = {
        "summary": report_root / "local_reconnect_calibration_summary.json",
        "calibration_cases": report_root / "local_reconnect_calibration_cases.csv",
        "category_counts": report_root / "local_reconnect_category_counts.csv",
        "diffsbdd_reclassified": report_root / "diffsbdd_reconnect_reclassified.csv",
        "rule_positive": report_root / "rule_positive_reconnect_check.csv",
        "clean_positive": report_root / "clean_positive_reconnect_check.csv",
        "synthetic_negative": report_root / "synthetic_negative_reconnect_check.csv",
        "shadow": report_root / "reconnect_shadow_reliable_analysis.csv",
        "completion_audit": report_root / "phase4_0_1a_completion_audit.md",
        "expt_report": resolve_repo_path(config["outputs"]["expt_report"], repo_root=repo_root),
    }
    paths["summary"].write_text(json.dumps(_jsonable(summary), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    calibration_cases.to_csv(paths["calibration_cases"], index=False)
    category_counts.to_csv(paths["category_counts"], index=False)
    diffsbdd_reclassified.to_csv(paths["diffsbdd_reclassified"], index=False)
    rule_positive.to_csv(paths["rule_positive"], index=False)
    clean_positive.to_csv(paths["clean_positive"], index=False)
    synthetic_negative.to_csv(paths["synthetic_negative"], index=False)
    shadow.to_csv(paths["shadow"], index=False)
    paths["completion_audit"].write_text(completion_audit_markdown(summary, category_counts, shadow), encoding="utf-8")
    paths["expt_report"].parent.mkdir(parents=True, exist_ok=True)
    paths["expt_report"].write_text(expt_report_markdown(summary, category_counts, shadow), encoding="utf-8")
    return {"summary": summary, "report_paths": paths}


def classify_reconnect_row(row: dict[str, Any] | pd.Series) -> dict[str, Any]:
    if _field_present(row, "candidate_readable") and not _as_bool(row.get("candidate_readable"), default=True):
        return _category("invalid_reconnect", "candidate_readable=false")
    if _field_present(row, "candidate_path") and not str(row.get("candidate_path") or "").strip():
        return _category("invalid_reconnect", "candidate_path_empty")
    if _field_present(row, "ligand_valid") and not _as_bool(row.get("ligand_valid"), default=True):
        return _category("invalid_reconnect", "ligand_valid=false")
    if _field_present(row, "fixed_structure_mapping_success_for_diagnostics") and not _as_bool(
        row.get("fixed_structure_mapping_success_for_diagnostics"),
        default=True,
    ):
        return _category("invalid_reconnect", _reason(row, "fixed_structure_mapping_failed"))
    if _field_present(row, "fixed_structure_match_success") and not _as_bool(row.get("fixed_structure_match_success"), default=True):
        return _category("invalid_reconnect", "fixed_structure_match_success=false")
    if _field_present(row, "anchor_match_success") and not _as_bool(row.get("anchor_match_success"), default=True):
        return _category("invalid_reconnect", "anchor_match_success=false")
    if _field_present(row, "generated_fragment_heavy_atom_count") and _as_int(row.get("generated_fragment_heavy_atom_count"), default=1) <= 0:
        return _category("invalid_reconnect", "generated_fragment_empty")
    if _as_bool(row.get("floating_fragment_detected"), default=False):
        return _category("invalid_reconnect", "floating_fragment")
    if _field_present(row, "generated_fragment_connected_to_anchor") and not _as_bool(
        row.get("generated_fragment_connected_to_anchor"),
        default=True,
    ):
        return _category("invalid_reconnect", "not_connected_to_anchor")

    num_extra = _as_int(row.get("num_extra_attachments"), default=0)
    attachment_count = _as_int(row.get("generated_fragment_attachment_count"), default=0)
    if num_extra > 0 or attachment_count > 1:
        if num_extra > 0:
            return _category("multi_attachment_out_of_scope", f"extra_attachments={num_extra}")
        return _category("multi_attachment_out_of_scope", f"generated_fragment_attachment_count={attachment_count}")

    anchor_neighbors = _as_int(row.get("num_anchor_neighbors"), default=-1)
    if (
        _as_bool(row.get("generated_fragment_connected_to_anchor"), default=False)
        and anchor_neighbors == 1
        and num_extra == 0
        and not _as_bool(row.get("floating_fragment_detected"), default=False)
    ):
        return _category("single_anchor_reconnect_pass", "single_anchor_connected")
    return _category("invalid_reconnect", _reason(row, "unclassified_reconnect_failure"))


def reclassify_diffsbdd_candidates(verifier: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in verifier.iterrows():
        item = row.to_dict()
        item["source_group"] = "diffsbdd_candidates"
        item.update(classify_reconnect_row(item))
        item["strict_single_anchor_shadow_reliable"] = bool(
            _as_bool(item.get("reliable_repair_success"), default=False)
            and item["reconnect_category"] == "single_anchor_reconnect_pass"
        )
        item["local_reconnect_original_preserved"] = _as_bool(item.get("local_reconnect_pass"), default=False)
        rows.append(item)
    return pd.DataFrame(rows)


def build_rule_positive_checks(
    verifier: pd.DataFrame,
    *,
    case_by_id: dict[str, Any],
    calibration_cfg: dict[str, Any],
) -> pd.DataFrame:
    backend_name = str(calibration_cfg.get("rule_positive_backend_name", "rule_fixed_topology"))
    rows = verifier[verifier["backend_name"].astype(str) == backend_name].copy()
    if _as_bool(calibration_cfg.get("rule_positive_only_reliable", True), default=True):
        rows = rows[_bool_series(rows, "reliable_repair_success")]
    tolerance = float(calibration_cfg.get("fixed_structure_match_tolerance_angstrom", 0.35))
    candidate_budget_k = int(calibration_cfg.get("rule_positive_candidate_budget_k", 8))
    output = []
    for _, candidate in rows.iterrows():
        case_id = str(candidate["case_id"])
        if case_id not in case_by_id:
            continue
        diagnostics = analyze_candidate_fragment(candidate.to_dict(), case_by_id[case_id], tolerance=tolerance)
        item = candidate.to_dict()
        item.update(diagnostics)
        item["source_group"] = "rule_positive"
        item["candidate_budget_k"] = int(item.get("candidate_budget_k") or candidate_budget_k)
        item.update(classify_reconnect_row(item))
        output.append(item)
    return pd.DataFrame(output)


def build_clean_positive_checks(case_inputs: list[Any], *, calibration_cfg: dict[str, Any]) -> pd.DataFrame:
    tolerance = float(calibration_cfg.get("fixed_structure_match_tolerance_angstrom", 0.35))
    source = str(calibration_cfg.get("clean_positive_source", "original_ligand_sdf"))
    output = []
    for case_input in case_inputs:
        candidate_path = getattr(case_input, source)
        row = {
            "backend_name": "clean_positive",
            "backend_unit": "original_ligand_reconnect_sanity",
            "case_id": case_input.case_id,
            "base_sample_id": case_input.base_sample_id,
            "attempt_id": f"clean_positive:{case_input.case_id}",
            "candidate_id": f"clean_positive:{case_input.case_id}:original",
            "candidate_index": 1,
            "candidate_path": str(candidate_path),
            "candidate_budget_k": 0,
            "candidate_readable": Path(candidate_path).exists(),
            "ligand_valid": False,
        }
        try:
            mol = read_first_mol(candidate_path, sanitize=False)
            row["ligand_valid"] = _ligand_valid(mol)
        except Exception as exc:
            row["candidate_readable"] = False
            row["fragment_diagnostics_status"] = "read_failed"
            row["fragment_diagnostics_reason"] = f"{type(exc).__name__}:{exc}"
        diagnostics = analyze_candidate_fragment(row, case_input, tolerance=tolerance)
        row.update(diagnostics)
        row["fixed_structure_match_success"] = bool(row.get("fixed_structure_mapping_success_for_diagnostics", False))
        row["anchor_integrity"] = bool(row.get("generated_fragment_connected_to_anchor", False))
        row["source_group"] = "clean_positive"
        row.update(classify_reconnect_row(row))
        output.append(row)
    return pd.DataFrame(output)


def build_synthetic_negative_checks(clean_positive: pd.DataFrame) -> pd.DataFrame:
    if clean_positive.empty:
        return pd.DataFrame()
    base = clean_positive.iloc[0].to_dict()
    cases = [
        (
            "disconnected",
            {
                "generated_fragment_connected_to_anchor": False,
                "num_anchor_neighbors": 0,
                "generated_fragment_attachment_count": 0,
                "num_extra_attachments": 0,
                "floating_fragment_detected": False,
                "anchor_reconnect_status": "fail",
                "anchor_reconnect_reason": "not_connected_to_anchor",
                "local_reconnect_pass": False,
                "local_reconnect_failure_reason": "not_connected_to_anchor",
            },
        ),
        (
            "floating",
            {
                "generated_fragment_connected_to_anchor": False,
                "num_anchor_neighbors": 0,
                "generated_fragment_attachment_count": 0,
                "num_extra_attachments": 0,
                "floating_fragment_detected": True,
                "anchor_reconnect_status": "fail",
                "anchor_reconnect_reason": "floating_fragment",
                "local_reconnect_pass": False,
                "local_reconnect_failure_reason": "floating_fragment",
            },
        ),
        (
            "extra_attachment",
            {
                "generated_fragment_connected_to_anchor": True,
                "num_anchor_neighbors": 1,
                "generated_fragment_attachment_count": 2,
                "num_extra_attachments": 1,
                "floating_fragment_detected": False,
                "anchor_reconnect_status": "fail",
                "anchor_reconnect_reason": "extra_attachments=1",
                "local_reconnect_pass": False,
                "local_reconnect_failure_reason": "extra_attachments=1",
            },
        ),
        (
            "missing_anchor",
            {
                "anchor_match_success": False,
                "anchor_candidate_idx": -1,
                "generated_fragment_connected_to_anchor": False,
                "num_anchor_neighbors": 0,
                "generated_fragment_attachment_count": 0,
                "num_extra_attachments": 0,
                "floating_fragment_detected": False,
                "anchor_reconnect_status": "fail",
                "anchor_reconnect_reason": "anchor_not_mapped",
                "local_reconnect_pass": False,
                "local_reconnect_failure_reason": "anchor_not_mapped",
            },
        ),
    ]
    output = []
    for index, (name, updates) in enumerate(cases, start=1):
        row = dict(base)
        row.update(
            {
                "source_group": "synthetic_negative",
                "synthetic_negative_type": name,
                "candidate_id": f"synthetic_negative:{name}",
                "attempt_id": f"synthetic_negative:{name}",
                "candidate_index": index,
                "candidate_readable": True,
                "ligand_valid": True,
                "fixed_structure_match_success": True,
                "fixed_structure_mapping_success_for_diagnostics": True,
                "anchor_match_success": True,
                "anchor_candidate_idx": 0,
                "generated_fragment_heavy_atom_count": max(_as_int(row.get("generated_fragment_heavy_atom_count"), default=1), 1),
            }
        )
        row.update(updates)
        row.update(classify_reconnect_row(row))
        output.append(row)
    return pd.DataFrame(output)


def build_shadow_reliable_analysis(diffsbdd_reclassified: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for budget_k, group in diffsbdd_reclassified.groupby("candidate_budget_k", dropna=False):
        reliable = _bool_series(group, "reliable_repair_success")
        strict = _bool_series(group, "strict_single_anchor_shadow_reliable")
        base = {
            "candidate_budget_k": int(budget_k) if not pd.isna(budget_k) else -1,
            "candidate_count": int(group.shape[0]),
            "reliable_repair_success_count": int(reliable.sum()),
            "strict_single_anchor_shadow_reliable_count": int(strict.sum()),
            "strict_single_anchor_shadow_reliable_rate": _rate(int(strict.sum()), int(group.shape[0])),
        }
        category_counts = group["reconnect_category"].value_counts(dropna=False).to_dict()
        for label in RECONNECT_LABELS:
            base[f"{label}_count"] = int(category_counts.get(label, 0))
        rows.append(base)
    total_reliable = _bool_series(diffsbdd_reclassified, "reliable_repair_success")
    total_strict = _bool_series(diffsbdd_reclassified, "strict_single_anchor_shadow_reliable")
    total = {
        "candidate_budget_k": -1,
        "candidate_count": int(diffsbdd_reclassified.shape[0]),
        "reliable_repair_success_count": int(total_reliable.sum()),
        "strict_single_anchor_shadow_reliable_count": int(total_strict.sum()),
        "strict_single_anchor_shadow_reliable_rate": _rate(int(total_strict.sum()), int(diffsbdd_reclassified.shape[0])),
    }
    category_counts = diffsbdd_reclassified["reconnect_category"].value_counts(dropna=False).to_dict()
    for label in RECONNECT_LABELS:
        total[f"{label}_count"] = int(category_counts.get(label, 0))
    rows.append(total)
    return pd.DataFrame(rows).sort_values("candidate_budget_k").reset_index(drop=True)


def reconnect_category_counts(diffsbdd_reclassified: pd.DataFrame, calibration_cases: pd.DataFrame) -> pd.DataFrame:
    combined = pd.concat(
        [
            diffsbdd_reclassified[["source_group", "candidate_budget_k", "reconnect_category", "reconnect_category_reason", "reliable_repair_success"]],
            calibration_cases[[col for col in ["source_group", "candidate_budget_k", "reconnect_category", "reconnect_category_reason", "reliable_repair_success"] if col in calibration_cases.columns]],
        ],
        ignore_index=True,
        sort=False,
    )
    grouped = (
        combined.groupby(["source_group", "candidate_budget_k", "reconnect_category"], dropna=False)
        .size()
        .reset_index(name="count")
    )
    return grouped.sort_values(["source_group", "candidate_budget_k", "reconnect_category"]).reset_index(drop=True)


def build_summary(
    *,
    config: dict[str, Any],
    repo_root: Path,
    input_paths: dict[str, Path],
    diffsbdd_reclassified: pd.DataFrame,
    clean_positive: pd.DataFrame,
    rule_positive: pd.DataFrame,
    synthetic_negative: pd.DataFrame,
    shadow: pd.DataFrame,
    phase4_0_1_summary: dict[str, Any],
    budget_curve: pd.DataFrame,
    backend_comparison: pd.DataFrame,
) -> dict[str, Any]:
    total_shadow = shadow[shadow["candidate_budget_k"] == -1].iloc[0].to_dict()
    counts = diffsbdd_reclassified["reconnect_category"].value_counts(dropna=False).to_dict()
    recommended = _recommended_use(clean_positive, rule_positive, synthetic_negative)
    return {
        "schema_version": config.get("schema_version", "phase4_0_1a_local_reconnect_calibration_v0_1"),
        "mode": "report_only_audit_only",
        "status": "completed",
        "classification_labels": RECONNECT_LABELS,
        "git_branch": _git_output(repo_root, ["git", "branch", "--show-current"]),
        "git_head": _git_output(repo_root, ["git", "rev-parse", "HEAD"]),
        "git_status_short": _git_output(repo_root, ["git", "status", "--short", "--branch"]),
        "plan_doc_exists": input_paths["phase4_0_1_plan_doc"].exists(),
        "rerun_diffsbdd": False,
        "regenerate_candidates": False,
        "training_or_finetuning_performed": False,
        "diffsbdd_original_denoising_modified": False,
        "h_clash_used_in_diffsbdd_generation": bool(phase4_0_1_summary.get("h_clash_used_in_diffsbdd_generation", False)),
        "modify_reliable_repair_fields": False,
        "local_reconnect_enters_reliable_repair_standard": False,
        "multi_attachment_is_ligand_invalid": False,
        "reliable_repair_fields": RELIABLE_REPAIR_FIELDS,
        "num_diffsbdd_candidates_reclassified": int(diffsbdd_reclassified.shape[0]),
        "num_clean_positive_cases": int(clean_positive.shape[0]),
        "num_rule_positive_cases": int(rule_positive.shape[0]),
        "num_synthetic_negative_cases": int(synthetic_negative.shape[0]),
        "single_anchor_pass_count": int(counts.get("single_anchor_reconnect_pass", 0)),
        "multi_attachment_out_of_scope_count": int(counts.get("multi_attachment_out_of_scope", 0)),
        "invalid_reconnect_count": int(counts.get("invalid_reconnect", 0)),
        "strict_single_anchor_shadow_reliable_count": int(total_shadow["strict_single_anchor_shadow_reliable_count"]),
        "phase4_0_1_budget_rows": int(budget_curve.shape[0]),
        "phase4_0_backend_rows": int(backend_comparison.shape[0]),
        "phase4_mask_seed_sha256": _sha256(input_paths["phase4_mask_seed"]),
        "recommended_use_of_local_reconnect": recommended,
    }


def completion_audit_markdown(summary: dict[str, Any], category_counts: pd.DataFrame, shadow: pd.DataFrame) -> str:
    return "\n".join(
        [
            "# Phase 4.0.1a Local Reconnect Calibration Completion Audit",
            "",
            "## 1. Scope",
            "",
            "- 本阶段为 report-only / audit-only.",
            "- 未重跑 DiffSBDD, 未重新生成候选, 未训练或微调模型.",
            "- 未修改 reliable repair 10 项标准, 未把 local reconnect 加入 reliable repair 标准.",
            "- `multi_attachment_out_of_scope` 只表示超出当前 single-anchor R-group repair 范围, 不等于 ligand invalid.",
            "",
            "## 2. Repository Facts",
            "",
            f"- branch: `{summary.get('git_branch')}`.",
            f"- HEAD: `{summary.get('git_head')}`.",
            f"- plan doc exists: {summary.get('plan_doc_exists')}.",
            f"- phase4_mask_seed_sha256: `{summary.get('phase4_mask_seed_sha256')}`.",
            "",
            "## 3. Calibration Summary",
            "",
            f"- DiffSBDD candidates reclassified: {summary.get('num_diffsbdd_candidates_reclassified')}.",
            f"- clean positive cases: {summary.get('num_clean_positive_cases')}.",
            f"- rule positive cases: {summary.get('num_rule_positive_cases')}.",
            f"- synthetic negative cases: {summary.get('num_synthetic_negative_cases')}.",
            f"- single-anchor pass: {summary.get('single_anchor_pass_count')}.",
            f"- multi-attachment out-of-scope: {summary.get('multi_attachment_out_of_scope_count')}.",
            f"- invalid reconnect: {summary.get('invalid_reconnect_count')}.",
            f"- strict single-anchor shadow reliable count: {summary.get('strict_single_anchor_shadow_reliable_count')}.",
            f"- recommended use: `{summary.get('recommended_use_of_local_reconnect')}`.",
            "",
            "## 4. Shadow Analysis",
            "",
            _markdown_table(shadow),
            "",
            "## 5. Category Counts",
            "",
            _markdown_table(category_counts),
            "",
        ]
    )


def expt_report_markdown(summary: dict[str, Any], category_counts: pd.DataFrame, shadow: pd.DataFrame) -> str:
    return "\n".join(
        [
            "# Phase 4.0.1a Local Reconnect Calibration 临时实验汇报",
            "",
            "> 本文件是临时实验汇报, 不是 final report.",
            "",
            "## 1. 摘要",
            "",
            f"- 本次只做 report-only / audit-only 校准, 状态: `{summary.get('status')}`.",
            f"- DiffSBDD 候选重标注数量: {summary.get('num_diffsbdd_candidates_reclassified')}.",
            f"- reconnect 三分类: single-anchor pass {summary.get('single_anchor_pass_count')}, multi-attachment out-of-scope {summary.get('multi_attachment_out_of_scope_count')}, invalid {summary.get('invalid_reconnect_count')}.",
            f"- shadow reliable count: {summary.get('strict_single_anchor_shadow_reliable_count')}.",
            f"- 建议用途: `{summary.get('recommended_use_of_local_reconnect')}`.",
            "",
            "## 2. 口径",
            "",
            "- `multi_attachment_out_of_scope` 不等于 ligand invalid.",
            "- `reliable_repair_success` 保持阶段 4.0 / 4.0.1 的 10 项标准, 本阶段不回写历史结果.",
            "- `strict_single_anchor_shadow_reliable` 只用于观察后续若加严 single-anchor reconnect 的影响.",
            "",
            "## 3. Shadow Analysis",
            "",
            _markdown_table(shadow),
            "",
            "## 4. Category Counts",
            "",
            _markdown_table(category_counts),
            "",
        ]
    )


def _validate_input_paths(input_paths: dict[str, Path]) -> None:
    conflicts = []
    for name, path in input_paths.items():
        if not path.exists():
            conflicts.append(
                {
                    "conflict_item": f"missing_input:{name}",
                    "plan_statement": "方案要求该输入文件存在并可读取.",
                    "repo_fact": f"文件不存在: {path}",
                    "files": str(path),
                    "impact": "无法执行对应校准或字段恢复.",
                    "recommendation": "先补齐输入文件或调整配置路径.",
                    "needs_manual_confirmation": "yes",
                }
            )
    if conflicts:
        raise CalibrationConflict(conflicts)


def _validate_diffsbdd_schema(verifier: pd.DataFrame, audit: pd.DataFrame, manifest: pd.DataFrame) -> None:
    conflicts = []
    missing = [field for field in REQUIRED_DIFFSBDD_VERIFIER_COLUMNS if field not in verifier.columns]
    if missing:
        conflicts.append(
            {
                "conflict_item": "diffsbdd_verifier_missing_columns",
                "plan_statement": "阶段 4.0.1 verifier outcome 应包含 verifier 10 项字段和 reconnect 诊断字段.",
                "repo_fact": f"缺少字段: {', '.join(missing)}",
                "files": "reports/phase4_0_1_diffsbdd_conditional_repair/diffsbdd_verifier_outcome.csv",
                "impact": "无法无歧义执行三分类或 shadow analysis.",
                "recommendation": "先确认字段来源或修正字段映射.",
                "needs_manual_confirmation": "yes",
            }
        )
    if verifier.shape[0] != audit.shape[0] or verifier.shape[0] != manifest.shape[0]:
        conflicts.append(
            {
                "conflict_item": "phase4_0_1_row_count_mismatch",
                "plan_statement": "候选, verifier 和 anchor reconnect audit 记录数应一致.",
                "repo_fact": f"verifier={verifier.shape[0]}, audit={audit.shape[0]}, manifest={manifest.shape[0]}",
                "files": "phase4_0_1 candidate/verifier/audit CSV",
                "impact": "候选级追踪可能不可靠.",
                "recommendation": "先人工确认是否存在 execution failure 行或缺失候选行.",
                "needs_manual_confirmation": "yes",
            }
        )
    if conflicts:
        raise CalibrationConflict(conflicts)


def _validate_phase4_0_schema(verifier: pd.DataFrame, manifest: pd.DataFrame) -> None:
    required = ["backend_name", "case_id", "candidate_id", "candidate_path", "reliable_repair_success", *RELIABLE_REPAIR_FIELDS]
    missing = [field for field in required if field not in verifier.columns]
    conflicts = []
    if missing:
        conflicts.append(
            {
                "conflict_item": "phase4_0_verifier_missing_columns",
                "plan_statement": "阶段 4.0 verifier outcome 应可提供 rule positive 和 10 项 reliable 字段.",
                "repo_fact": f"缺少字段: {', '.join(missing)}",
                "files": "reports/phase4_0_backend_feasibility/verifier_outcome.csv",
                "impact": "无法构造 rule positive 校准集.",
                "recommendation": "先确认阶段 4.0 字段映射.",
                "needs_manual_confirmation": "yes",
            }
        )
    if manifest.empty:
        conflicts.append(
            {
                "conflict_item": "phase4_0_candidate_manifest_empty",
                "plan_statement": "阶段 4.0 candidate manifest 应存在并可读取.",
                "repo_fact": "candidate_manifest.csv 为空.",
                "files": "reports/phase4_0_backend_feasibility/candidate_manifest.csv",
                "impact": "无法核查候选来源.",
                "recommendation": "先确认阶段 4.0 报告是否完整.",
                "needs_manual_confirmation": "yes",
            }
        )
    if conflicts:
        raise CalibrationConflict(conflicts)


def _validate_selected_cases(selected_cases: pd.DataFrame, phase4_0_selected_cases: pd.DataFrame) -> None:
    current = set(selected_cases["case_id"].astype(str).tolist())
    previous = set(phase4_0_selected_cases["case_id"].astype(str).tolist())
    if current != previous:
        raise CalibrationConflict(
            [
                {
                    "conflict_item": "selected_cases_mismatch",
                    "plan_statement": "阶段 4.0.1a 应复用阶段 4.0 / 4.0.1 的 40 个 selected cases.",
                    "repo_fact": f"case set differs: phase4_0_1={len(current)}, phase4_0={len(previous)}",
                    "files": "phase4_0 selected_cases.csv; phase4_0_1 selected_cases.csv",
                    "impact": "clean / rule positive 与 DiffSBDD candidates 的样本口径不一致.",
                    "recommendation": "人工确认是否允许使用不同 case set.",
                    "needs_manual_confirmation": "yes",
                }
            ]
        )


def _conflict_report_markdown(items: list[dict[str, str]]) -> str:
    lines = [
        "# phase4-0-1a-local-reconnect-calibration conflict report",
        "",
        "## 1. 概述",
        "",
        "执行阶段 4.0.1a report-only 校准前发现方案文档与仓库事实存在冲突或阻塞项. 冲突部分未继续执行.",
        "",
        "## 2. 冲突项",
        "",
    ]
    for index, item in enumerate(items, start=1):
        lines.extend(
            [
                f"### 2.{index}. {item['conflict_item']}",
                "",
                f"- 方案文档表述: {item['plan_statement']}",
                f"- 仓库实际情况: {item['repo_fact']}",
                f"- 涉及文件: {item['files']}",
                f"- 影响范围: {item['impact']}",
                f"- 建议处理方式: {item['recommendation']}",
                f"- 是否需要人工确认: {item['needs_manual_confirmation']}",
                "",
            ]
        )
    return "\n".join(lines)


def _category(label: str, reason: str) -> dict[str, str]:
    return {"reconnect_category": label, "reconnect_category_reason": reason}


def _reason(row: dict[str, Any] | pd.Series, fallback: str) -> str:
    for key in ["local_reconnect_failure_reason", "anchor_reconnect_reason", "fragment_diagnostics_reason", "failure_reason"]:
        value = row.get(key)
        if not _is_missing(value) and str(value).strip():
            return str(value)
    return fallback


def _field_present(row: dict[str, Any] | pd.Series, key: str) -> bool:
    if key not in row:
        return False
    return not _is_missing(row.get(key))


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def _as_bool(value: Any, *, default: bool = False) -> bool:
    if _is_missing(value):
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if isinstance(value, float) and math.isnan(value):
            return default
        return bool(value)
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def _as_int(value: Any, *, default: int = 0) -> int:
    if _is_missing(value):
        return default
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _bool_series(df: pd.DataFrame, column: str) -> pd.Series:
    if column not in df:
        return pd.Series([False] * int(df.shape[0]), index=df.index, dtype=bool)
    return df[column].map(lambda value: _as_bool(value, default=False)).astype(bool)


def _ligand_valid(mol: Any) -> bool:
    from rdkit import Chem

    try:
        copy = Chem.Mol(mol)
        result = Chem.SanitizeMol(copy, catchErrors=True)
        return result == Chem.SanitizeFlags.SANITIZE_NONE
    except Exception:
        return False


def _recommended_use(clean_positive: pd.DataFrame, rule_positive: pd.DataFrame, synthetic_negative: pd.DataFrame) -> str:
    clean_rate = _category_rate(clean_positive, "single_anchor_reconnect_pass")
    rule_rate = _category_rate(rule_positive, "single_anchor_reconnect_pass")
    negative_ok = _synthetic_negative_ok(synthetic_negative)
    if clean_rate >= 0.8 and rule_rate >= 0.8 and negative_ok:
        return "soft_filter"
    if clean_rate >= 0.8 and negative_ok:
        return "diagnostic_only"
    return "blocked_pending_calibration"


def _category_rate(df: pd.DataFrame, label: str) -> float:
    if df.empty or "reconnect_category" not in df:
        return 0.0
    return float((df["reconnect_category"].astype(str) == label).sum() / df.shape[0])


def _synthetic_negative_ok(df: pd.DataFrame) -> bool:
    if df.empty:
        return False
    expected = {
        "disconnected": "invalid_reconnect",
        "floating": "invalid_reconnect",
        "extra_attachment": "multi_attachment_out_of_scope",
        "missing_anchor": "invalid_reconnect",
    }
    for negative_type, expected_label in expected.items():
        rows = df[df.get("synthetic_negative_type", pd.Series(dtype=str)).astype(str) == negative_type]
        if rows.empty or str(rows.iloc[0].get("reconnect_category")) != expected_label:
            return False
    return True


def _rate(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return float("nan")
    return float(numerator / denominator)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_output(repo_root: Path, args: list[str]) -> str:
    try:
        result = subprocess.run(args, cwd=repo_root, check=True, text=True, capture_output=True)
    except Exception as exc:
        return f"unavailable:{type(exc).__name__}"
    return result.stdout.strip()


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    if isinstance(value, tuple):
        return [_jsonable(v) for v in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    try:
        import numpy as np

        if isinstance(value, np.generic):
            return _jsonable(value.item())
    except Exception:
        pass
    return value


def _markdown_table(df: pd.DataFrame) -> str:
    if df.empty:
        return ""
    columns = [str(column) for column in df.columns]
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join(["---"] * len(columns)) + " |",
    ]
    for _, row in df.iterrows():
        values = []
        for column in df.columns:
            value = row[column]
            if _is_missing(value):
                values.append("")
            elif isinstance(value, float):
                if math.isfinite(value) and value.is_integer():
                    values.append(str(int(value)))
                else:
                    values.append(f"{value:.6f}")
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)
