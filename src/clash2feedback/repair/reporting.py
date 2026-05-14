from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


def write_phase4_reports(
    *,
    report_root: str | Path,
    selected_cases: pd.DataFrame,
    model_inventory: list[dict[str, Any]],
    adapter_input_manifest: list[dict[str, Any]],
    candidate_manifest: list[dict[str, Any]],
    verifier_outcome: list[dict[str, Any]],
    summary: dict[str, Any],
    mode: str = "preflight",
) -> dict[str, Path]:
    root = Path(report_root)
    root.mkdir(parents=True, exist_ok=True)
    if mode == "formal":
        paths = {
            "selected_cases": root / "selected_cases.csv",
            "model_inventory": root / "model_inventory.csv",
            "adapter_input_manifest": root / "adapter_input_manifest.csv",
            "candidate_manifest": root / "candidate_manifest.csv",
            "verifier_outcome": root / "verifier_outcome.csv",
            "backend_comparison": root / "backend_comparison.csv",
            "failure_cases": root / "failure_cases.csv",
            "blocked_backends": root / "blocked_backends.md",
            "completion_audit": root / "phase4_0_completion_audit.md",
            "summary": root / "phase4_0_small_scale_summary.json",
        }
        selected_cases.to_csv(paths["selected_cases"], index=False)
    else:
        paths = {
            "selected_cases_preflight": root / "selected_cases_preflight.csv",
            "model_inventory": root / "model_inventory.csv",
            "adapter_input_manifest": root / "adapter_input_manifest.csv",
            "candidate_manifest": root / "candidate_manifest.csv",
            "verifier_outcome": root / "verifier_outcome.csv",
            "backend_preflight_report": root / "backend_preflight_report.md",
            "blocked_backends": root / "blocked_backends.md",
            "summary": root / "phase4_0_preflight_summary.json",
        }
        selected_cases.to_csv(paths["selected_cases_preflight"], index=False)
    _frame(model_inventory).to_csv(paths["model_inventory"], index=False)
    _frame(adapter_input_manifest).to_csv(paths["adapter_input_manifest"], index=False)
    _frame(candidate_manifest).to_csv(paths["candidate_manifest"], index=False)
    _frame(verifier_outcome).to_csv(paths["verifier_outcome"], index=False)
    paths["summary"].write_text(json.dumps(_jsonable(summary), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    paths["blocked_backends"].write_text(_blocked_markdown(model_inventory), encoding="utf-8")
    if mode == "formal":
        _backend_comparison(summary, verifier_outcome).to_csv(paths["backend_comparison"], index=False)
        _failure_cases(verifier_outcome).to_csv(paths["failure_cases"], index=False)
        paths["completion_audit"].write_text(
            _completion_audit_markdown(selected_cases, model_inventory, summary, verifier_outcome),
            encoding="utf-8",
        )
    else:
        paths["backend_preflight_report"].write_text(
            _preflight_markdown(selected_cases, model_inventory, candidate_manifest, verifier_outcome, summary),
            encoding="utf-8",
        )
    return paths


def build_summary(
    *,
    selected_cases: pd.DataFrame,
    model_inventory: list[dict[str, Any]],
    candidate_manifest: list[dict[str, Any]],
    verifier_outcome: list[dict[str, Any]],
    mask_seed_sha256_before: str,
    mask_seed_sha256_after: str,
    mode: str = "preflight",
    expected_case_count: int = 5,
) -> dict[str, Any]:
    candidates = pd.DataFrame(candidate_manifest)
    outcomes = pd.DataFrame(verifier_outcome)
    backends: dict[str, Any] = {}
    if not candidates.empty:
        for backend, group in candidates.groupby("backend_name", dropna=False):
            backend_outcomes = outcomes[outcomes["backend_name"] == backend] if not outcomes.empty else pd.DataFrame()
            attempt_group = group.copy()
            if "attempt_id" in attempt_group:
                attempt_group = attempt_group.drop_duplicates(["backend_name", "attempt_id"])
            sample_success = 0
            if not backend_outcomes.empty:
                by_case = backend_outcomes.groupby("case_id")["reliable_repair_success"].any()
                sample_success = int(by_case.sum())
                reliable_candidate_success = int(backend_outcomes["reliable_repair_success"].sum())
            else:
                reliable_candidate_success = 0
            backends[str(backend)] = {
                "selected_case_denominator": int(selected_cases.shape[0]),
                "candidate_rows": int(group.shape[0]),
                "attempt_rows": int(attempt_group.shape[0]),
                "candidate_count_sum": int(attempt_group["candidate_count"].fillna(0).astype(int).sum()),
                "proposal_count_sum": int(attempt_group["proposal_count"].fillna(0).astype(int).sum()),
                "failure_rows": int((group["failure_reason"].fillna("") != "").sum()),
                "failure_attempts": int((attempt_group["failure_reason"].fillna("") != "").sum()),
                "reliable_candidate_success_count": reliable_candidate_success,
                "sample_reliable_success_count": sample_success,
            }
    schema_suffix = "small_scale_v0_1" if mode == "formal" else "preflight_v0_1"
    return {
        "schema_version": f"phase4_0_backend_feasibility_{schema_suffix}",
        "mode": "formal_40_case" if mode == "formal" else "preflight_only",
        "selected_case_count": int(selected_cases.shape[0]),
        "selected_case_ids": selected_cases["case_id"].astype(str).tolist(),
        "expected_case_count": int(expected_case_count),
        "preflight_expected_case_count": 5,
        "formal_40_case_results_generated": mode == "formal",
        "training_or_finetuning_performed": False,
        "h_clash_used_in_diffsbdd_generation": False,
        "phase4_mask_seed_sha256_before": mask_seed_sha256_before,
        "phase4_mask_seed_sha256_after": mask_seed_sha256_after,
        "phase4_mask_seed_unchanged": mask_seed_sha256_before == mask_seed_sha256_after,
        "blocked_backend_count": int(sum(1 for row in model_inventory if row.get("status") == "blocked")),
        "backend_summary": backends,
    }


def _blocked_markdown(model_inventory: list[dict[str, Any]]) -> str:
    blocked = [row for row in model_inventory if row.get("status") == "blocked"]
    lines = [
        "# Phase 4.0 Blocked Backends",
        "",
        "## 1. Scope",
        "",
        "- 本文件记录当前 phase4.0 inventory 中不可执行或不进入主线的后端.",
        "- 阻塞后端不影响已执行后端进入统一 verifier 分母.",
        "",
        "## 2. Blocked Inventory",
        "",
        "| backend_name | backend_unit | status | blocked_reason |",
        "|---|---|---|---|",
    ]
    if not blocked:
        lines.append("| none | none | ready |  |")
    for row in blocked:
        lines.append(
            f"| {row.get('backend_name', '')} | {row.get('backend_unit', '')} | {row.get('status', '')} | {row.get('blocked_reason', '')} |"
        )
    lines.extend(
        [
            "",
            "## 3. Constraints",
            "",
            "- checkpoint/env 状态以当前 `model_inventory.csv` 为准.",
            "- 未修改 DiffSBDD 或 DiffDec 原始源码.",
            "- 未把 `H_clash` 写入任何生成过程.",
        ]
    )
    return "\n".join(lines) + "\n"


def _preflight_markdown(
    selected_cases: pd.DataFrame,
    model_inventory: list[dict[str, Any]],
    candidate_manifest: list[dict[str, Any]],
    verifier_outcome: list[dict[str, Any]],
    summary: dict[str, Any],
) -> str:
    candidates = pd.DataFrame(candidate_manifest)
    outcomes = pd.DataFrame(verifier_outcome)
    lines = [
        "# Phase 4.0 Backend Feasibility Preflight Report",
        "",
        "## 1. Scope",
        "",
        f"- preflight cases: {selected_cases.shape[0]}.",
        "- mode: preflight_only.",
        "- 40 case 正式小规模实验未生成.",
        "- 本轮只实现规则型固定拓扑局部构象修复和 DiffSBDD CrossDocked full-atom conditional local completion 最小闭环.",
        "- DiffSBDD/DiffDec 原始源码和去噪过程未修改.",
        "- `H_clash` 未进入 DiffSBDD 生成命令.",
        "",
        "## 2. Selected Cases",
        "",
        "| case_id | split | injection_mode | difficulty | oracle_mask_size | selection_reason |",
        "|---|---|---|---|---:|---|",
    ]
    for _, row in selected_cases.iterrows():
        lines.append(
            f"| {row['case_id']} | {row['base_split']} | {row['injection_mode']} | {row['difficulty_bin']} | {int(row['oracle_mask_size'])} | {row['selection_reason']} |"
        )
    lines.extend(["", "## 3. Model Inventory", "", "| backend_name | status | blocked_reason |", "|---|---|---|"])
    for row in model_inventory:
        lines.append(f"| {row.get('backend_name', '')} | {row.get('status', '')} | {row.get('blocked_reason', '')} |")
    lines.extend(["", "## 4. Backend Outcomes", "", "| backend_name | attempts | candidate_rows | failure_attempts | sample_reliable_success_count |", "|---|---:|---:|---:|---:|"])
    for backend, backend_summary in summary.get("backend_summary", {}).items():
        lines.append(
            f"| {backend} | {backend_summary['attempt_rows']} | {backend_summary['candidate_rows']} | {backend_summary['failure_attempts']} | {backend_summary['sample_reliable_success_count']} |"
        )
    reliable_count = int(outcomes["reliable_repair_success"].sum()) if not outcomes.empty and "reliable_repair_success" in outcomes else 0
    lines.extend(
        [
            "",
            "## 5. Verification",
            "",
            f"- candidate manifest rows: {0 if candidates.empty else candidates.shape[0]}.",
            f"- verifier outcome rows: {0 if outcomes.empty else outcomes.shape[0]}.",
            f"- reliable candidate successes: {reliable_count}.",
            f"- phase4_mask_seed unchanged: {summary.get('phase4_mask_seed_unchanged')}.",
        ]
    )
    return "\n".join(lines) + "\n"


def _backend_comparison(summary: dict[str, Any], verifier_outcome: list[dict[str, Any]]) -> pd.DataFrame:
    outcomes = pd.DataFrame(verifier_outcome)
    rows = []
    for backend, backend_summary in summary.get("backend_summary", {}).items():
        backend_outcomes = outcomes[outcomes["backend_name"] == backend] if not outcomes.empty else pd.DataFrame()
        rows.append(
            {
                "backend_name": backend,
                "selected_case_denominator": backend_summary.get("selected_case_denominator", 0),
                "attempt_rows": backend_summary.get("attempt_rows", 0),
                "candidate_rows": backend_summary.get("candidate_rows", 0),
                "proposal_count_sum": backend_summary.get("proposal_count_sum", 0),
                "candidate_count_sum": backend_summary.get("candidate_count_sum", 0),
                "failure_attempts": backend_summary.get("failure_attempts", 0),
                "failure_rows": backend_summary.get("failure_rows", 0),
                "reliable_candidate_success_count": backend_summary.get("reliable_candidate_success_count", 0),
                "sample_reliable_success_count": backend_summary.get("sample_reliable_success_count", 0),
                "candidate_readable_count": int(backend_outcomes["candidate_readable"].sum()) if not backend_outcomes.empty and "candidate_readable" in backend_outcomes else 0,
                "fixed_structure_match_success_count": int(backend_outcomes["fixed_structure_match_success"].sum()) if not backend_outcomes.empty and "fixed_structure_match_success" in backend_outcomes else 0,
                "anchor_integrity_success_count": int(backend_outcomes["anchor_integrity"].sum()) if not backend_outcomes.empty and "anchor_integrity" in backend_outcomes else 0,
            }
        )
    return pd.DataFrame(rows)


def _failure_cases(verifier_outcome: list[dict[str, Any]]) -> pd.DataFrame:
    outcomes = pd.DataFrame(verifier_outcome)
    if outcomes.empty:
        return pd.DataFrame()
    keep_columns = [
        "backend_name",
        "case_id",
        "base_sample_id",
        "attempt_id",
        "candidate_id",
        "candidate_index",
        "candidate_path",
        "candidate_readable",
        "fixed_structure_match_success",
        "anchor_integrity",
        "old_clash_resolved",
        "no_new_severe_clash",
        "reliable_repair_success",
        "failure_stage",
        "failure_reason",
        "verifier_failure_reasons",
    ]
    failure_mask = ~outcomes["reliable_repair_success"].fillna(False).astype(bool)
    existing = [column for column in keep_columns if column in outcomes.columns]
    return outcomes.loc[failure_mask, existing].copy()


def _completion_audit_markdown(
    selected_cases: pd.DataFrame,
    model_inventory: list[dict[str, Any]],
    summary: dict[str, Any],
    verifier_outcome: list[dict[str, Any]],
) -> str:
    outcomes = pd.DataFrame(verifier_outcome)
    reliable_count = int(outcomes["reliable_repair_success"].sum()) if not outcomes.empty and "reliable_repair_success" in outcomes else 0
    lines = [
        "# Phase 4.0 Backend Feasibility Completion Audit",
        "",
        "## 1. Scope",
        "",
        f"- selected cases: {selected_cases.shape[0]}.",
        "- mode: formal_40_case.",
        "- no training or finetuning was performed.",
        "- DiffSBDD/DiffDec original source and denoising loops were not modified.",
        "- `H_clash` was not passed into DiffSBDD or DiffDec generation.",
        "",
        "## 2. Selection",
        "",
        f"- expected case count: {summary.get('expected_case_count')}.",
        f"- selected case count: {summary.get('selected_case_count')}.",
        f"- phase4_mask_seed unchanged: {summary.get('phase4_mask_seed_unchanged')}.",
        "",
        "## 3. Backend Summary",
        "",
        "| backend_name | attempts | candidates | failure_attempts | reliable_candidates | reliable_cases |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for backend, backend_summary in summary.get("backend_summary", {}).items():
        lines.append(
            f"| {backend} | {backend_summary.get('attempt_rows', 0)} | {backend_summary.get('candidate_rows', 0)} | "
            f"{backend_summary.get('failure_attempts', 0)} | {backend_summary.get('reliable_candidate_success_count', 0)} | "
            f"{backend_summary.get('sample_reliable_success_count', 0)} |"
        )
    lines.extend(
        [
            "",
            "## 4. Inventory",
            "",
            "| backend_name | status | blocked_reason |",
            "|---|---|---|",
        ]
    )
    for row in model_inventory:
        lines.append(f"| {row.get('backend_name', '')} | {row.get('status', '')} | {row.get('blocked_reason', '')} |")
    lines.extend(
        [
            "",
            "## 5. Verification",
            "",
            f"- verifier outcome rows: {0 if outcomes.empty else outcomes.shape[0]}.",
            f"- reliable candidate successes: {reliable_count}.",
            "- `backend_comparison.csv` contains backend-level counters.",
            "- `failure_cases.csv` contains non-reliable candidate and attempt rows.",
        ]
    )
    return "\n".join(lines) + "\n"


def _frame(rows: list[dict[str, Any]]) -> pd.DataFrame:
    normalized = []
    for row in rows:
        normalized.append({key: _cell(value) for key, value in row.items()})
    return pd.DataFrame(normalized)


def _cell(value: Any) -> Any:
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(_jsonable(value), ensure_ascii=False, sort_keys=True)
    return value


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if hasattr(value, "item"):
        return value.item()
    return value
